# -*- coding: utf-8 -*-
"""
test_llm_client_light.py —— stdlib/大模型客户端.light 的 OpenAI 兼容 LLM 客户端测试

离线部分：本地 fake HTTP/SSE 服务器（端口固定 19250，属 19200-19299 范围；
绑定前检查占用，被占用直接失败，不做 +1 自动重试），回放录制好的 SSE 字节。
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

FAKE_PORT = 19250


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
        try:
            self.srv.bind(("127.0.0.1", FAKE_PORT))
        except OSError as e:
            pytest.fail("fake server 端口 %d 被占用（不做 +1 重试）: %s" % (FAKE_PORT, e))
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


def _client():
    return 大模型客户端("http://127.0.0.1:%d" % FAKE_PORT, "test-model", "")


class TestStreaming:
    def test_text_increments_assembled(self, fake_server):
        fake_server("stream_text")
        c = _client()
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        contents = [b["内容增量"] for b in blocks if not b["结束"]]
        assert "".join(contents) == "你好！"

    def test_final_block_carries_full_state(self, fake_server):
        fake_server("stream_text")
        c = _client()
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        final = [b for b in blocks if b["结束"]]
        assert len(final) == 1
        assert final[0]["累积内容"] == "你好！"
        assert final[0]["角色"] == "assistant"
        assert final[0]["完成原因"] == "stop"

    def test_tool_calls_index_grouped(self, fake_server):
        fake_server("stream_tool")
        c = _client()
        blocks = list(c.流式对话([{"role": "user", "content": "天气"}]))
        final = [b for b in blocks if b["结束"]][0]
        tc = final["工具调用增量"]
        assert len(tc) == 1
        assert tc[0]["name"] == "get_weather"
        assert tc[0]["arguments"] == '{"city":"BJ"}'

    def test_done_sentinel_terminates(self, fake_server):
        fake_server("stream_text")
        c = _client()
        blocks = list(c.流式对话([{"role": "user", "content": "hi"}]))
        # [DONE] 之后不会再产出内容块
        assert all(b["内容增量"] != "[DONE]" for b in blocks)


class TestNonStreaming:
    def test_message_returned(self, fake_server):
        fake_server("nonstream")
        c = _client()
        msg = c.对话([{"role": "user", "content": "hi"}])
        assert msg["content"] == "非流式回复"
        assert msg["role"] == "assistant"


class TestHTTPError:
    def test_raises_with_status(self, fake_server):
        fake_server("httperr")
        c = _client()
        with pytest.raises(Exception) as ei:
            c.对话([{"role": "user", "content": "hi"}])
        assert ei.type.__name__ == "HTTP错误"
        assert ei.value.状态 == 401


# ---- 真实 API（无 key 时 skip，key 仅从环境变量读取）----
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
