# -*- coding: utf-8 -*-
"""
test_llm_client_light.py —— stdlib/大模型客户端.light 的 OpenAI 兼容 LLM 客户端测试

离线部分：本地 fake HTTP/SSE 服务器（bind 端口 0，由内核分配空闲端口；见
FakeServer.__init__ 里为什么不再用写死的 19250），回放录制好的 SSE 字节。

覆盖：流式文本增量组装、流式 tool_calls（index 分组、name 只首片、arguments 逐片拼接）、
     非流式对话、HTTP 4xx 错误。
真实 API 部分：仅当环境变量 DEEPSEEK_API_KEY 存在时执行（否则 skip），
     key 只从环境变量读取，绝不打印。
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

from 大模型客户端 import 大模型客户端


def _resp_200_event_stream(chunks):
    """把 SSE 事件块拼成带 Content-Length 的 200 text/event-stream 响应。"""
    body = b"".join(chunks)
    head = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n"
    )
    return head + body


def _sse_frame(obj):
    return b"data: " + json.dumps(obj).encode("utf-8") + b"\r\n\r\n"


class FakeServer(threading.Thread):
    """按录制模式回放响应的本地服务器；循环 accept，可服务多次连接。"""

    def __init__(self, mode):
        super().__init__(daemon=True)
        self.mode = mode
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 端口 0 = 由内核分配一个当前空闲端口。
        #
        # 原先是 bind 到写死的 19250。那条「端口写死、不许 +1 重试」的口径出自
        # 任务书/协作规程.md，理由是当年四路 agent 同机各自 worktree 并行开发，
        # +1 会漂进别人的端口段；合并到单一主干后这个理由不再成立。
        # 而 CI 现在跑 pytest -n auto（xdist 默认 --dist=load），同文件的用例被
        # 打散到多个 worker 并发执行，每条用例都去 bind 同一个 19250 —— 一个赢、
        # 其余全报 EADDRINUSE（run #65 上 6 条里红了 5 条）。SO_REUSEADDR 只覆盖
        # TIME_WAIT 残留，覆盖不了「另一个活着的 listener」。
        #
        # 内核分配既不是「随机取」也不是「+1 重试」，冲突在原理上不存在。
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
                conn.sendall(self._response())
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _response(self):
        m = self.mode
        if m == "stream_text":
            body = b"".join([
                _sse_frame({"choices": [{"delta": {"role": "assistant", "content": "你"}, "finish_reason": None}]}),
                _sse_frame({"choices": [{"delta": {"content": "好"}, "finish_reason": None}]}),
                _sse_frame({"choices": [{"delta": {"content": "！"}, "finish_reason": "stop"}]}),
                b"data: [DONE]\r\n\r\n",
            ])
            return _resp_200_event_stream([body])
        if m == "stream_tool":
            body = b"".join([
                _sse_frame({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "get_weather"}}]}, "finish_reason": None}]}),
                _sse_frame({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"city"'}}]}, "finish_reason": None}]}),
                _sse_frame({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ':"BJ"}'}}]}, "finish_reason": "tool_calls"}]}),
                b"data: [DONE]\r\n\r\n",
            ])
            return _resp_200_event_stream([body])
        if m == "nonstream":
            payload = {"choices": [{"message": {"role": "assistant", "content": "非流式回复"}}]}
            body = json.dumps(payload).encode("utf-8")
            return (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
            )
        if m == "httperr":
            body = b'{"error":"bad key"}'
            return (
                b"HTTP/1.1 401 Unauthorized\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
            )
        return b"HTTP/1.1 400 Bad Request\r\n\r\n"


@pytest.fixture
def fake_server():
    servers = []

    def _make(mode):
        s = FakeServer(mode)
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


def _client(服务器):
    return 大模型客户端("http://127.0.0.1:%d" % 服务器.port, "test-model", "")


class TestStreaming:
    def test_text_increments_assembled(self, fake_server):
        c = _client(fake_server("stream_text"))
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        contents = [b["内容增量"] for b in blocks if not b["结束"]]
        assert "".join(contents) == "你好！"

    def test_final_block_carries_full_state(self, fake_server):
        c = _client(fake_server("stream_text"))
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        final = [b for b in blocks if b["结束"]]
        assert len(final) == 1
        assert final[0]["累积内容"] == "你好！"
        assert final[0]["角色"] == "assistant"
        assert final[0]["完成原因"] == "stop"

    def test_tool_calls_index_grouped(self, fake_server):
        c = _client(fake_server("stream_tool"))
        blocks = list(c.流式对话([{"role": "user", "content": "天气"}]))
        final = [b for b in blocks if b["结束"]][0]
        tc = final["工具调用增量"]
        assert len(tc) == 1
        assert tc[0]["name"] == "get_weather"
        assert tc[0]["arguments"] == '{"city":"BJ"}'

    def test_done_sentinel_terminates(self, fake_server):
        c = _client(fake_server("stream_text"))
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        # [DONE] 之后不会再产出内容块
        assert all(b["内容增量"] != "[DONE]" for b in blocks)


class TestNonStreaming:
    def test_message_returned(self, fake_server):
        c = _client(fake_server("nonstream"))
        msg = c.对话([{"role": "user", "content": "hi"}])
        assert msg["content"] == "非流式回复"
        assert msg["role"] == "assistant"


class TestHTTPError:
    def test_raises_with_status(self, fake_server):
        c = _client(fake_server("httperr"))
        with pytest.raises(Exception) as ei:
            c.对话([{"role": "user", "content": "hi"}])
        assert ei.type.__name__ == "HTTP错误"
        assert ei.value.状态 == 401



# ---- 真实 API（无 key 时 skip，key 仅从环境变量读取）----
#
# ⚠️ skip 掩盖分析（交付报告第 5 项要求逐条写明）：
# 这三条 skip 掩盖的**只是**「真实 DeepSeek 对我们的 tools 声明与 SSE 分帧的
# 接受度」——也就是「对方认不认」。**不掩盖 tool_call 功能本身**：功能由
# tests/test_deepseek_mock.py 守（那个 mock 会解析并断言请求体，无 skip、
# 任何机器上都必须绿）。
# 这条区分很重要：第二轮就是因为把「无 key 则 skip」当成了功能验证的替代，
# 才让「请求体里没有 tools」这个协议断点藏了整整一轮。
@pytest.mark.skipif(not os.getenv("DEEPSEEK_API_KEY"), reason="未设置 DEEPSEEK_API_KEY")
class TestRealAPI:
    def test_stream_chat(self):
        c = 大模型客户端("https://api.deepseek.com", "deepseek-chat", os.getenv("DEEPSEEK_API_KEY"))
        blocks = list(c.流式对话([{"role": "user", "content": "只回复两个字：你好"}]))
        joined = "".join(b["内容增量"] for b in blocks if not b["结束"])
        assert joined != ""

    def test_nonstream_chat(self):
        c = 大模型客户端("https://api.deepseek.com", "deepseek-chat", os.getenv("DEEPSEEK_API_KEY"))
        msg = c.对话([{"role": "user", "content": "只回复两个字：你好"}])
        assert msg.get("content", "") != ""

    def test_真实模型接受tools声明并返回tool_calls(self):
        """M4 在线轨：证明真实 DeepSeek 认我们发的 tools。

        产物落盘到 第三轮留档/M4_在线往返实录.txt（key 打码，只留后 4 位），
        供人工核对请求/响应原文。
        """
        key = os.getenv("DEEPSEEK_API_KEY")
        c = 大模型客户端("https://api.deepseek.com", "deepseek-chat", key)
        工具声明 = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的当前天气",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "城市名"}},
                    "required": ["city"],
                },
            },
        }]
        c.配置工具(工具声明, "auto")
        blocks = list(c.流式对话([
            {"role": "user", "content": "北京现在天气怎么样？请调用 get_weather 工具查询。"},
        ]))
        终块 = [b for b in blocks if b["结束"]][0]
        调用 = 终块["工具调用增量"]
        assert 调用, "真实模型没有返回 tool_calls —— 说明它没有接受我们发的 tools 声明"
        assert 调用[0]["name"] == "get_weather"
        参数 = json.loads(调用[0]["arguments"])
        assert "city" in 参数

        留档目录 = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "第三轮留档")
        if os.path.isdir(留档目录):
            打码 = "***" + (key[-4:] if key and len(key) >= 4 else "")
            with open(os.path.join(留档目录, "M4_在线往返实录.txt"), "w", encoding="utf-8") as fh:
                fh.write("DEEPSEEK_API_KEY（已打码）: %s\n" % 打码)
                fh.write("下发的 tools 声明:\n%s\n\n" % json.dumps(工具声明, ensure_ascii=False, indent=2))
                fh.write("聚合后的 tool_calls:\n%s\n\n" % json.dumps(调用, ensure_ascii=False, indent=2))
                fh.write("finish_reason: %s\n" % 终块["完成原因"])

