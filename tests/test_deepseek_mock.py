# -*- coding: utf-8 -*-
"""
test_deepseek_mock.py —— M4 的**离线判绿点**：一个会读请求体的 mock DeepSeek。

为什么要新写一个 mock（而不是复用 test_agent_loop_light.py 的回放服务器）
------------------------------------------------------------------------
tests/test_agent_loop_light.py 的 FakeLoopServer 按「第几次请求」取用录制好的
SSE 字节，**完全不看请求内容**。所以第二轮那套 tool_call 测试证明的只是
「我们能收」，从没证明「我们发对了」。而实际情况是：改动前
stdlib/大模型客户端.light 的请求体里**没有 tools 字段**——工具注册表只活在本地，
从来没告诉过模型。对真实 DeepSeek，模型永远不会返回 finish_reason=="tool_calls"，
整条工具链在协议层就是断的，而离线测试一路全绿。

本文件是那个洞的判据：MockDeepSeek **先解析请求体并断言**，不合规就回 400 +
明确原因，让测试红在「我们发错了」这一侧。它必须在任何机器上都能跑（无 skip、
无网络、无 API key）。真连 DeepSeek 那条在 tests/test_llm_client_light.py::TestRealAPI，
只负责证明「真实模型接受我们的 tools 声明」，不负责证明功能。
"""
import json
import os
import socket
import sys
import threading
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 代理循环 import 代理循环


WEATHER_SCHEMA = {
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
}


# ---------------------------------------------------------------- SSE 帧构造
def _sse(obj):
    return b"data: " + json.dumps(obj).encode("utf-8") + b"\r\n\r\n"


def _body_200(chunks):
    body = b"".join(chunks)
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    )


def _body_400(reason):
    # ensure_ascii=False：真实 API 的错误体是 UTF-8 原文，不是 \uXXXX 转义。
    # 用默认的 ensure_ascii=True 会让「错误原因能不能被人读懂」这件事在测试里
    # 假通过（断言中文子串永远匹配不上）。
    body = json.dumps(
        {"error": {"message": reason, "type": "mock_protocol_violation"}},
        ensure_ascii=False,
    ).encode("utf-8")
    return (
        b"HTTP/1.1 400 Bad Request\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    )


def _delta(delta, finish):
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


def _tool_delta(name=None, args=None, tc_id=None, finish=None):
    """与真实 DeepSeek 一致：缺席的 key 直接不出现（不许填 null/空串）。"""
    fn = {}
    if name is not None:
        fn["name"] = name
    if args is not None:
        fn["arguments"] = args
    tcc = {"index": 0, "function": fn}
    if tc_id is not None:
        tcc["id"] = tc_id
    return {"choices": [{"index": 0, "delta": {"tool_calls": [tcc]}, "finish_reason": finish}]}


SERVER_TOOL_CALL_ID = "call_mock_7f3a"


def _resp_tool_calls():
    """第一轮：模型决定调工具。arguments 故意切在 JSON 中间，考验分片累积。"""
    return _body_200([
        _sse(_tool_delta(name="get_weather", tc_id=SERVER_TOOL_CALL_ID)),
        _sse(_tool_delta(args='{"city"')),
        _sse(_tool_delta(args=':"BJ"}')),
        _sse(_delta({}, "tool_calls")),
        b"data: [DONE]\r\n\r\n",
    ])


def _resp_final_text():
    """第二轮：模型看过工具结果后给最终答复。"""
    return _body_200([
        _sse(_delta({"role": "assistant", "content": "北京"}, None)),
        _sse(_delta({"content": "今天晴天"}, None)),
        _sse(_delta({}, "stop")),
        b"data: [DONE]\r\n\r\n",
    ])


# ---------------------------------------------------------------- 请求体校验
def 校验请求体(payload, 需要工具):
    """返回违规原因字符串；合规返回 None。

    这里检查的是「我们发出去的东西模型端能不能接受」，不是「我们收得对不对」。
    每一条都对应一个真实会导致 4xx 的写法。
    """
    if not isinstance(payload, dict):
        return "请求体不是 JSON 对象"
    for 必需 in ("messages", "model", "stream"):
        if 必需 not in payload:
            return "缺少必需字段 %s" % 必需
    if not isinstance(payload["messages"], list) or not payload["messages"]:
        return "messages 必须是非空数组"

    if "tools" in payload:
        tools = payload["tools"]
        if not isinstance(tools, list) or not tools:
            # 这条不是吹毛求疵：部分 OpenAI 兼容服务端对 "tools": [] 直接 400，
            # 而这个 400 极难归因。所以宁可在 mock 里先拦。
            return "tools 存在但不是非空数组（工具表为空时该字段应整体不出现，不许发空数组）"
        for i, t in enumerate(tools):
            if t.get("type") != "function":
                return "tools[%d].type 必须是 'function'" % i
            fn = t.get("function")
            if not isinstance(fn, dict):
                return "tools[%d].function 缺失或不是对象" % i
            for k in ("name", "description", "parameters"):
                if k not in fn:
                    return "tools[%d].function 缺少 %s" % (i, k)
            name = fn["name"]
            if not isinstance(name, str) or not name:
                return "tools[%d].function.name 必须是非空字符串" % i
            try:
                name.encode("ascii")
            except UnicodeEncodeError:
                return "tools[%d].function.name 含非 ASCII 字符: %r（服务端只接受 ASCII 函数名）" % (i, name)
            if not isinstance(fn["parameters"], dict):
                return "tools[%d].function.parameters 必须是 JSON Schema 对象" % i
        if payload.get("tool_choice") not in ("auto", "none", "required"):
            return "带 tools 时 tool_choice 必须是 auto/none/required，实际: %r" % (payload.get("tool_choice"),)
    elif 需要工具:
        return "请求体里没有 tools 字段——模型无从知道有哪些工具可用，永远不会返回 tool_calls"

    # assistant.tool_calls[].id 必须与随后的 tool 消息 tool_call_id 一一对应，
    # 否则真实 DeepSeek 第二轮直接拒（invalid tool_call_id）。
    已下发 = []
    for m in payload["messages"]:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            已下发 = [tc.get("id") for tc in m["tool_calls"]]
        if m.get("role") == "tool":
            if "tool_call_id" not in m:
                return "tool 角色消息缺少 tool_call_id"
            if m["tool_call_id"] not in 已下发:
                return "tool 消息的 tool_call_id=%r 对不上前面 assistant.tool_calls 里的 %r" % (
                    m["tool_call_id"], 已下发)
    return None


class MockDeepSeek(threading.Thread):
    """会解析并断言请求体的 mock；不合规就回 400 + 原因。"""

    def __init__(self, responses, 需要工具=True):
        super().__init__(daemon=True)
        self.responses = responses
        self.需要工具 = 需要工具
        self.payloads = []      # 逐次请求解析后的 JSON
        self.headers = []       # 逐次请求的头（用于断言 Authorization 等）
        self.violations = []    # 被判违规的 (第几次, 原因)
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 端口一律由内核分配（协作规程 §3）：CI 上 pytest -n auto 会把同文件用例
        # 打散到多个 worker，写死端口就是自己撞自己。
        self.srv.bind(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.srv.listen(8)

    @property
    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def _read_request(self, conn):
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return None, None
            buf += chunk
        head, _, rest = buf.partition(b"\r\n\r\n")
        头 = {}
        for line in head.split(b"\r\n")[1:]:
            if b":" in line:
                k, _, v = line.partition(b":")
                头[k.strip().decode("latin-1").lower()] = v.strip().decode("latin-1")
        clen = int(头.get("content-length", "0"))
        while len(rest) < clen:
            chunk = conn.recv(4096)
            if not chunk:
                break
            rest += chunk
        return 头, rest[:clen]

    def run(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            try:
                头, body = self._read_request(conn)
                if 头 is None:
                    continue
                idx = len(self.payloads)
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception as e:              # noqa: BLE001 - mock 边界
                    payload = {"_解析失败": str(e)}
                self.payloads.append(payload)
                self.headers.append(头)
                原因 = 校验请求体(payload, self.需要工具)
                if 原因 is not None:
                    self.violations.append((idx, 原因))
                    conn.sendall(_body_400(原因))
                else:
                    conn.sendall(self.responses[idx % len(self.responses)])
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass


@pytest.fixture
def mock_deepseek():
    servers = []

    def _make(responses, 需要工具=True):
        s = MockDeepSeek(responses, 需要工具=需要工具)
        s.start()
        time.sleep(0.05)
        servers.append(s)
        return s

    yield _make
    for s in servers:
        try:
            s.srv.close()
        except OSError:
            pass


def _agent(服务器, 最大轮数=4):
    a = 代理循环(服务器.base_url, "deepseek-chat", "sk-mock-not-a-real-key",
              最大轮数值=最大轮数, 消息上限值=20)
    a.重试次数 = 1   # 不要在协议错误上退避重试，测试要立刻看到 400
    return a


# ======================================================== tools 字段的有/无
class Test工具声明下发:
    def test_无工具时tools字段整体不出现(self, mock_deepseek):
        s = mock_deepseek([_resp_final_text()], 需要工具=False)
        a = _agent(s)
        回复 = a.运行("你好")
        assert 回复 == "北京今天晴天"
        assert len(s.payloads) == 1
        # 不许发 "tools": []（部分兼容服务端直接 400），必须整个键都不出现
        assert "tools" not in s.payloads[0]
        assert "tool_choice" not in s.payloads[0]
        assert s.violations == []

    def test_注册工具后载荷形状与注册的schema深度相等(self, mock_deepseek):
        s = mock_deepseek([_resp_tool_calls(), _resp_final_text()])
        a = _agent(s)
        a.注册工具("get_weather", "查询某城市天气", WEATHER_SCHEMA, lambda p: "晴天")
        a.运行("北京天气")
        assert s.violations == []
        tools = s.payloads[0]["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        fn = tools[0]["function"]
        assert fn["name"] == "get_weather"
        assert fn["description"] == "查询某城市天气"
        # 深度相等：注册时给的 JSON Schema 必须原样到达模型端，不许被改形状
        assert fn["parameters"] == WEATHER_SCHEMA
        assert s.payloads[0]["tool_choice"] == "auto"

    def test_多工具按注册顺序下发(self, mock_deepseek):
        s = mock_deepseek([_resp_final_text()])
        a = _agent(s)
        a.注册工具("read_file", "读文件", {"type": "object", "properties": {}}, lambda p: "")
        a.注册工具("get_weather", "查天气", WEATHER_SCHEMA, lambda p: "晴天")
        a.运行("你好")
        名字们 = [t["function"]["name"] for t in s.payloads[0]["tools"]]
        assert 名字们 == ["read_file", "get_weather"]


# ======================================================== 反向控制：mock 真的在判
class Test判据本身有效:
    """如果 mock 不会因为「少了 tools」而红，那它就等于没判。这一组证明它会红。"""

    def test_需要工具但未注册时服务端回400且说明原因(self, mock_deepseek):
        s = mock_deepseek([_resp_tool_calls()], 需要工具=True)
        a = _agent(s)   # 故意不注册任何工具
        with pytest.raises(Exception) as ei:
            a.运行("北京天气")
        assert ei.type.__name__ == "HTTP错误"
        assert ei.value.状态 == 400
        assert "没有 tools 字段" in str(ei.value.正文)
        assert len(s.violations) == 1

    def test_中文工具名在注册时就被拦下(self):
        # 这条不需要服务器：注册那一刻就该炸。中文函数名会被原样送进
        # tools[].function.name，真实服务端只接受 ASCII —— 让它在本地先响亮失败。
        a = 代理循环("http://127.0.0.1:1", "deepseek-chat", "sk-mock",
                 最大轮数值=1, 消息上限值=5)
        with pytest.raises(Exception) as ei:
            a.注册工具("执行命令", "跑一条命令", {"type": "object", "properties": {}}, lambda p: "")
        assert ei.type.__name__ == "工具注册错误"
        assert "run_shell" in str(ei.value)   # 报错要给出可照抄的正确写法


# ======================================================== 完整两轮往返
class Test完整tool_call往返:
    def test_两轮往返协议正确(self, mock_deepseek):
        s = mock_deepseek([_resp_tool_calls(), _resp_final_text()])
        a = _agent(s)
        被调用 = []

        def 天气(参数):
            被调用.append(参数)
            return "晴天 26 度"

        a.注册工具("get_weather", "查询某城市天气", WEATHER_SCHEMA, 天气)
        回复 = a.运行("北京天气怎么样")

        # 1) 工具真的被执行，且参数是分片拼回来的完整 JSON
        assert 被调用 == [{"city": "BJ"}]
        # 2) 最终回复来自第二轮
        assert 回复 == "北京今天晴天"
        # 3) 服务端视角：恰好两次请求，零违规
        assert len(s.payloads) == 2
        assert s.violations == []
        # 4) 第二轮请求体的角色序列（这是模型真正看到的东西）
        角色们 = [m["role"] for m in s.payloads[1]["messages"]]
        assert 角色们 == ["user", "assistant", "tool"]
        # 5) 服务端下发的 tool_call id 必须被原样回带
        assistant消息 = s.payloads[1]["messages"][1]
        assert [tc["id"] for tc in assistant消息["tool_calls"]] == [SERVER_TOOL_CALL_ID]
        tool消息 = s.payloads[1]["messages"][2]
        assert tool消息["tool_call_id"] == SERVER_TOOL_CALL_ID
        assert tool消息["name"] == "get_weather"
        assert "晴天 26 度" in tool消息["content"]
        # 6) 第二轮仍要带着 tools（模型可能还想再调一次）
        assert "tools" in s.payloads[1]

    def test_Authorization头带上且不是空Bearer(self, mock_deepseek):
        s = mock_deepseek([_resp_final_text()], 需要工具=False)
        a = _agent(s)
        a.运行("你好")
        auth = s.headers[0]["authorization"]
        assert auth.startswith("Bearer ")
        assert auth != "Bearer "


# ======================================================== 可选参数透传
class Test参数透传:
    def test_未配置时可选参数整体不出现(self, mock_deepseek):
        s = mock_deepseek([_resp_final_text()], 需要工具=False)
        a = _agent(s)
        a.运行("你好")
        p = s.payloads[0]
        # 默认值归服务端。客户端替它拍一个数会让「没配置」和「配成这个值」不可区分。
        assert "temperature" not in p
        assert "max_tokens" not in p
        assert "top_p" not in p

    def test_配置后原样透传(self, mock_deepseek):
        s = mock_deepseek([_resp_final_text()], 需要工具=False)
        a = _agent(s)
        a.配置模型参数({"temperature": 0.2, "max_tokens": 512})
        a.运行("你好")
        p = s.payloads[0]
        assert p["temperature"] == 0.2
        assert p["max_tokens"] == 512
        assert "top_p" not in p
