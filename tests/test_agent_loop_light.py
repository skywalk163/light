# -*- coding: utf-8 -*-
"""
test_agent_loop_light.py —— stdlib/代理循环.light 的 agent 循环离线测试

本地 fake HTTP/SSE 服务器（bind 端口 0，由内核分配空闲端口；见
FakeLoopServer.__init__ 里为什么不再用写死的 19255）按"调用轮次序"回放录制好的 SSE 响应。


覆盖：
  1. 单次 tool_calls 往返：助手先回工具调用 → 工具被执行 → 结果作为 tool 消息
     追加 → 下一轮助手回 stop → 得到最终回复；工具被正确调用一次。
  2. 参数校验失败会喂回模型：响应序列 [参数非法, 工具调用, stop]，非法那次不进
     工具实现，最终工具仍被正确调用，且存在一条"工具调用失败"的 tool 消息。
  3. 最大轮数生效：模型每轮都回 tool_calls，循环在 最大轮数 轮后收敛、不再崩溃。
  4. 事件按序发出：请求开始/增量到达/工具调用/轮次结束 均被事件总线广播。
"""
import os
import socket
import sys
import threading
import time
import json

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 代理循环 import 代理循环, 会话
from 事件总线 import 取消令牌




def _sse_frame(obj):
    return b"data: " + json.dumps(obj).encode("utf-8") + b"\r\n\r\n"


def _resp_200_event_stream(chunks):
    body = b"".join(chunks)
    head = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n"
    )
    return head + body


def _frame(delta, finish):
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


def _tool_frame(name_fragment=None, args_fragment=None):
    # 与真实 DeepSeek SSE 一致：缺席的 key 直接不出现（绝不能填 null/空串）
    tcc = {"index": 0, "function": {}}
    if name_fragment is not None:
        tcc["function"]["name"] = name_fragment
    if args_fragment is not None:
        tcc["function"]["arguments"] = args_fragment
    return {"choices": [{"index": 0, "delta": {"tool_calls": [tcc]}, "finish_reason": None}]}


# 三类录制响应（按"第几次请求"取用）
def _resp_valid_tool_call():
    return _resp_200_event_stream([
        _sse_frame(_tool_frame("get_weather")),
        _sse_frame(_tool_frame(None, '{"city":"BJ"}')),
        _sse_frame(_frame({}, "tool_calls")),
        b"data: [DONE]\r\n\r\n",
    ])


def _resp_invalid_tool_call():
    return _resp_200_event_stream([
        _sse_frame(_tool_frame("get_weather")),
        _sse_frame(_tool_frame(None, '{"city": 123}')),
        _sse_frame(_frame({}, "tool_calls")),
        b"data: [DONE]\r\n\r\n",
    ])


def _resp_stop():
    return _resp_200_event_stream([
        _sse_frame(_frame({"role": "assistant", "content": "今日"}, None)),
        _sse_frame(_frame({"content": "北京晴天"}, None)),
        _sse_frame(_frame({}, "stop")),
        b"data: [DONE]\r\n\r\n",
    ])


class FakeLoopServer(threading.Thread):
    """回放服务器：循环 accept；每收到一次请求按序号取 responses[idx]。"""

    def __init__(self, responses):
        super().__init__(daemon=True)
        self.responses = responses
        self.request_count = 0
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 端口 0 = 由内核分配空闲端口。原先 bind 写死的 19255，在 CI 的
        # pytest -n auto（xdist 默认 --dist=load）下同文件用例被打散到多个 worker
        # 并发 bind 同一端口，一个赢其余全 EADDRINUSE（run #65 上 4 条红了 3 条）。
        # 详细缘由见 tests/test_llm_client_light.py 的 FakeServer.__init__。
        self.srv.bind(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.srv.listen(8)


    def run(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            try:
                req = b""
                while b"\r\n\r\n" not in req:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    req += chunk
                # 读 body（按 Content-Length）
                head, sep, _ = req.partition(b"\r\n\r\n")
                if sep:
                    clen = 0
                    for line in head.split(b"\r\n"):
                        if line.lower().startswith(b"content-length:"):
                            clen = int(line.split(b":")[1].strip())
                    while len(req) < len(head) + 4 + clen:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        req += chunk
                idx = self.request_count
                self.request_count += 1
                resp = self.responses[idx % len(self.responses)]
                conn.sendall(resp)
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass


@pytest.fixture
def loop_server():
    servers = []

    def _make(responses):
        s = FakeLoopServer(responses)
        s.start()
        time.sleep(0.2)
        servers.append(s)
        return s

    yield _make
    for s in servers:
        try:
            s.srv.close()
        except OSError:
            pass


WEATHER_SCHEMA = {
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
}


def _make_agent(服务器, events=None):
    agent = 代理循环(
        "http://127.0.0.1:%d" % 服务器.port,
        "test-model",
        "",
        最大轮数值=6,
        消息上限值=20,
    )
    calls = []
    agent.注册工具("get_weather", "查询某城市天气", WEATHER_SCHEMA, lambda p: "晴天")
    if events is not None:
        for evt in ("请求开始", "增量到达", "工具调用", "轮次结束"):
            agent.订阅(evt, lambda e, payload, n=evt: events.append(n))
    return agent, calls


class TestToolCallRoundtrip:
    def test_tool_called_and_final_reply(self, loop_server):
        s = loop_server([_resp_valid_tool_call(), _resp_stop()])
        agent, calls = _make_agent(s)
        reply = agent.运行("今天北京天气怎么样")
        assert reply == "今日北京晴天"
        # 会话应结束为 stop，工具调用被正确执行过一次
        msgs = agent.会话列表()
        roles = [m["role"] for m in msgs]
        assert roles == ["user", "assistant", "tool", "assistant"]
        # 工具调用的参数被正确解析并执行
        tool_msg = msgs[2]
        assert tool_msg["name"] == "get_weather"
        assert "晴天" in tool_msg["content"]
        # C2 回归：tool 消息的 tool_call_id 必须能对上 assistant.tool_calls[].id，
        # 否则真实 DeepSeek 第二轮会拒（invalid tool_call_id）。离线帧不带服务端 id，
        # 走 call_<index> 兜底，仍须一致。
        assistant_msg = msgs[1]
        assistant_ids = [tc["id"] for tc in assistant_msg["tool_calls"]]
        assert assistant_ids == ["call_0"]
        assert tool_msg["tool_call_id"] in assistant_ids


class TestValidationRetry:
    def test_invalid_args_fed_back_then_ok(self, loop_server):
        # 第一轮参数非法（city 是数字，schema 要求 string）→ 不进工具实现；
        # 第二轮合法 → 工具执行；第三轮 stop。
        s = loop_server([_resp_invalid_tool_call(), _resp_valid_tool_call(), _resp_stop()])
        agent, calls = _make_agent(s)
        reply = agent.运行("查北京天气")
        assert reply == "今日北京晴天"
        msgs = agent.会话列表()
        toolbar = [m for m in msgs if m["role"] == "tool"]
        # 至少有一条校验失败信息，且最终仍有一条执行成功的 tool 消息
        fail_msgs = [m for m in toolbar if "工具调用失败" in m["content"]]
        assert len(fail_msgs) == 1
        ok_msgs = [m for m in toolbar if "晴天" in m["content"]]
        assert len(ok_msgs) == 1


class TestMaxRounds:
    def test_terminates_after_max_rounds(self, loop_server):
        # 模型每次都回 tool_calls（循环永不自然 stop）→ 必须在 最大轮数 轮后收敛
        s = loop_server([_resp_valid_tool_call()])
        agent = 代理循环(
            "http://127.0.0.1:%d" % s.port,
            "test-model",
            "",
            最大轮数值=3,
            消息上限值=20,
        )
        agent.注册工具("get_weather", "查询天气", WEATHER_SCHEMA, lambda p: "晴天")
        events = []
        # A3-7 回归：这里以前写的是 `lambda payload: ...`（一参）。事件总线以
        # `处理器(事件名, 载荷)` 两参调用，于是每次发布都抛 TypeError 并被错误
        # 隔离吞掉，events 恒为空 —— 下面那条断言曾经是 `<= 3`，在空集合上恒真，
        # 整条用例**空转通过**。现在两处都修了：签名改两参，断言改等值。
        agent.订阅("轮次结束", lambda 事件名, payload: events.append(payload["轮次"]))
        # 不应抛出（网络层正常，只是轮数耗尽），运行正常返回
        agent.运行("无限工具")
        # 等值断言：模型每轮都回 tool_calls，所以恰好跑满 3 轮，轮次编号 0/1/2。
        # 不许再用 `<=` 这类上界断言——集合为空时它恒真，是假绿的常见形态。
        assert events == [0, 1, 2]


class TestHandlerSignatureGuard:
    """A3-7：订阅时就拦下签名不匹配，而不是发布时被错误隔离吞掉。"""

    def test_one_arg_handler_rejected_at_subscribe(self, loop_server):
        s = loop_server([_resp_stop()])
        agent, _ = _make_agent(s)
        with pytest.raises(Exception) as ei:
            agent.订阅("轮次结束", lambda payload: None)
        assert ei.type.__name__ == "处理器签名错误"
        # 报错必须说清正确写法，否则改错的人只会把 lambda 再猜一遍
        assert "两个位置实参" in str(ei.value)

    def test_two_arg_handler_accepted_and_really_called(self, loop_server):
        s = loop_server([_resp_stop()])
        agent, _ = _make_agent(s)
        收到 = []
        agent.订阅("轮次结束", lambda 事件名, 载荷: 收到.append(事件名))
        agent.运行("你好")
        # 正向断言：真的收到了事件（而不是"没报错就算过"）
        assert 收到 == ["轮次结束"]

    def test_isolated_handler_error_is_reported_to_stderr(self, loop_server, capfd):
        """错误隔离保留，但不许沉默：被隔离的异常必须出现在 stderr。"""
        s = loop_server([_resp_stop()])
        agent, _ = _make_agent(s)

        def 会炸的处理器(事件名, 载荷):
            raise RuntimeError("_taskA3_故意炸")

        agent.订阅("轮次结束", 会炸的处理器)
        agent.运行("你好")
        err = capfd.readouterr().err
        assert "_taskA3_故意炸" in err
        assert "[事件总线]" in err



class TestEventOrder:
    def test_events_broadcast_in_order(self, loop_server):
        s = loop_server([_resp_valid_tool_call(), _resp_stop()])
        events = []
        agent, _ = _make_agent(s, events)
        agent.运行("北京天气")
        # 事件类型按首轮 tool → 次轮 stop 的顺序出现
        assert events[0] == "请求开始"
        assert "工具调用" in events
        assert "增量到达" in events
        assert events.count("轮次结束") == 2
        assert "请求开始" in events[events.index("轮次结束") + 1:]


# ==================================================== A3-4：退避是真指数
class Test退避:
    def test_退避序列是指数且封顶(self, loop_server):
        s = loop_server([_resp_stop()])
        agent, _ = _make_agent(s)
        assert [agent.退避秒(n) for n in (1, 2, 3, 4, 5, 6, 7)] == [
            0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 8.0
        ]
        # 改动前是 0.2 * 尝试次数（线性 0.2/0.4/0.6…），而文件头与
        # 自测报告_任务C2.md 都自称「指数退避」。这条断言把口径钉死。

    def test_网络失败时按指数序列真睡了(self):
        # 指向一个必然连不上的端口（127.0.0.1:1），每轮都失败 → 走满重试
        agent = 代理循环("http://127.0.0.1:1", "test-model", "",
                     最大轮数值=2, 消息上限值=20)
        agent.重试次数 = 4
        睡了 = []
        # 睡眠收敛到单点（己.睡眠），所以能在实例上替掉，不必真等 1.4 秒
        agent.睡眠 = lambda 秒: 睡了.append(秒)
        with pytest.raises(Exception):
            agent.运行("你好")
        # 重试 4 次 = 失败 3 次后各睡一次，第 4 次直接抛
        assert 睡了 == [0.2, 0.4, 0.8]


# ==================================================== A3-6：token 预算截断
def _会话(消息们):
    c = 会话()
    for m in 消息们:
        c.追加原始(m)
    return c


class Test词元预算截断:
    def test_不启用时返回0且不动历史(self):
        c = _会话([{"role": "user", "content": "甲"}])
        assert c.按预算截断(0) == 0
        assert len(c.列表()) == 1

    def test_压到预算以内且保留前导system(self):
        消息们 = [{"role": "system", "content": "你是助手"}]
        for i in range(30):
            消息们.append({"role": "user", "content": "问题%d " % i + "填充" * 50})
        c = _会话(消息们)
        用量 = c.按预算截断(400)
        剩下 = c.列表()
        assert 用量 <= 400
        assert 剩下[0]["role"] == "system"        # system 永远保留
        assert len(剩下) < len(消息们)             # 真的截了
        # 保留的是**最新**的，不是最早的
        assert "问题29" in 剩下[-1]["content"]

    def test_绝不切开tool_calls与其配对的tool消息(self):
        消息们 = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "旧问题" + "填" * 200},
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "call_0", "type": "function",
                             "function": {"name": "f", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_0", "name": "f",
             "content": "工具结果" + "填" * 200},
            {"role": "user", "content": "新问题"},
        ]
        # 逐个预算档位都扫一遍：任何档位下都不许出现「孤儿 tool」或
        # 「有 tool_calls 却没有对应 tool 结果」——这两种都会让服务端直接 400。
        for 预算 in range(40, 600, 20):
            c = _会话([dict(m) for m in 消息们])
            c.按预算截断(预算)
            剩下 = c.列表()
            已声明 = set()
            for m in 剩下:
                if m["role"] == "assistant" and m.get("tool_calls"):
                    已声明 = {tc["id"] for tc in m["tool_calls"]}
                if m["role"] == "tool":
                    assert m["tool_call_id"] in 已声明, (
                        "预算=%d 时出现了孤儿 tool 消息：%r" % (预算, 剩下))
            # 反向：assistant 声明了工具调用，就必须能看到对应的 tool 结果
            for i, m in enumerate(剩下):
                if m["role"] == "assistant" and m.get("tool_calls"):
                    后续 = [x for x in 剩下[i + 1:] if x["role"] == "tool"]
                    落地 = {x["tool_call_id"] for x in 后续}
                    assert {tc["id"] for tc in m["tool_calls"]} <= 落地, (
                        "预算=%d 时 assistant.tool_calls 与它的 tool 结果被切开了：%r"
                        % (预算, 剩下))

    def test_单条超预算时截内容并留标记(self):
        c = _会话([{"role": "user", "content": "很长" * 2000}])
        c.按预算截断(100)
        剩下 = c.列表()
        # 不许静默丢整条：「模型看不到自己刚读的文件」比「看到被截断的文件」难查一百倍
        assert len(剩下) == 1
        assert "已截断" in 剩下[0]["content"]
        assert len(剩下[0]["content"]) < len("很长" * 2000)

    def test_可注入真tokenizer(self):
        c = _会话([{"role": "user", "content": "甲"}, {"role": "user", "content": "乙"}])
        c.估算器 = lambda 消息体: 100     # 每条恒定 100
        assert c.估算总量() == 200
        c.按预算截断(150)
        assert len(c.列表()) == 1        # 只装得下一条


# ==================================================== A3-5：取消令牌接入
class Test取消令牌:
    def test_令牌置位后不再发起新一轮(self, loop_server):
        # 模型每轮都回 tool_calls（永不自然停），最大轮数给足；靠取消收敛
        s = loop_server([_resp_valid_tool_call()])
        agent = 代理循环("http://127.0.0.1:%d" % s.port, "test-model", "",
                     最大轮数值=8, 消息上限值=20)
        令牌 = 取消令牌()
        agent.取消令牌 = 令牌
        轮次 = []
        agent.订阅("请求开始", lambda 事件名, 载荷: 轮次.append(载荷["轮次"]))

        def 天气(参数):
            令牌.取消()          # 工具执行中收到中断
            return "晴天"

        agent.注册工具("get_weather", "查天气", WEATHER_SCHEMA, 天气)
        agent.运行("北京天气")
        # 第 0 轮发出，工具里取消 → 不再有第 1 轮。等值断言，不用上界。
        assert 轮次 == [0]

    def test_未挂令牌时行为不变(self, loop_server):
        s = loop_server([_resp_valid_tool_call(), _resp_stop()])
        agent, _ = _make_agent(s)
        assert agent.运行("北京天气") == "今日北京晴天"
