# -*- coding: utf-8 -*-
"""examples/harness/真实通道.light 的行为测试 —— 零发网，本地假 DeepSeek。

为什么需要这份：第五轮 D5 的真实链路是「临时通道 + 临时驱动、跑完即删」，
于是它踩到的两个形态一条都没被判据钉住，第六轮复跑时又原样踩了一遍：

1. `[WinError 10038] 在一个非套接字上尝试了一个操作`
   —— 一个 `大模型客户端` = 一条 socket；驱动把同一个通道对象交给 N 个并发协程，
   多个请求同时读写同一条连接就崩。mock 桩没有连接，永远看不见这个形态。
   真实通道.light 的对策：**每次 流式对话2 新建一个客户端**。
2. `HTTP 401 Authentication Fails (auth header format should be Bearer sk-...)`
   —— 「密钥留空则从 DEEPSEEK_API_KEY 取」这条承诺因为 codegen 把
   `设 密钥 为 …`（参数名与类属性同名）发成 `self.密钥 = …` 而从未生效
   （已修，见 src/code_generator.py:_generate_var_decl 的「是类属性」判据）。

本文件用本地多线程假服务器覆盖这两条：并发 2 不许崩、每条请求各占一条连接、
Authorization 必须是非空 Bearer。整进程跑真驱动，判据断行为不断实现。
"""
import json
import os
import socketserver
import subprocess
import sys
import threading
import time

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_评测驱动 = os.path.join(_PROJECT, "examples", "harness", "评测驱动.light")

_SSE = (
    b'data: {"choices":[{"delta":{"role":"assistant","content":"\\u5317\\u4eac"},'
    b'"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}\n\n'
    b'data: [DONE]\n\n'
)


class _假DeepSeek(socketserver.ThreadingTCPServer):
    """多线程假 DeepSeek：每条连接一个线程，记录连接数与收到的 Authorization。"""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, 每请求延迟=0.0):
        self.每请求延迟 = 每请求延迟
        self.锁 = threading.Lock()
        self.连接数 = 0
        self.鉴权头们 = []
        super().__init__(("127.0.0.1", 0), _处理器)

    @property
    def port(self):
        return self.server_address[1]


class _处理器(socketserver.BaseRequestHandler):
    def handle(self):
        数据 = b""
        while b"\r\n\r\n" not in 数据:
            片 = self.request.recv(4096)
            if not 片:
                return
            数据 += 片
        头部, _, 余 = 数据.partition(b"\r\n\r\n")
        行们 = 头部.decode("utf-8", "replace").split("\r\n")
        头表 = {}
        for 行 in 行们[1:]:
            if ":" in 行:
                k, v = 行.split(":", 1)
                头表[k.strip().lower()] = v.strip()
        待收 = int(头表.get("content-length", "0"))
        while len(余) < 待收:
            片 = self.request.recv(4096)
            if not 片:
                break
            余 += 片
        with self.server.锁:
            self.server.连接数 += 1
            self.server.鉴权头们.append(头表.get("authorization", ""))
        # 延迟**必须放在响应体中段**，不能放在响应头之前。
        # stdlib/大模型客户端.light:315-318 写明的诚实边界：连接/握手/发请求/读响应头
        # 走的是同步 发送()，在事件循环里是阻塞的；唯一的 await 点在**流式体读取**
        # （协程读体）。把延迟放在头之前，6 条请求会被那段阻塞排成串行——实测并发 3
        # 与串行只差 2.62s vs 2.79s，量出来的是「阻塞段不并发」而不是「并发失效」。
        头 = (b"HTTP/1.1 200 OK\r\n"
              b"Content-Type: text/event-stream\r\n"
              b"Content-Length: " + str(len(_SSE)).encode("ascii") + b"\r\n\r\n")
        切点 = len(_SSE) // 2
        self.request.sendall(头 + _SSE[:切点])
        if self.server.每请求延迟:
            time.sleep(self.server.每请求延迟)
        self.request.sendall(_SSE[切点:])




def _起服务器(每请求延迟=0.0):
    服 = _假DeepSeek(每请求延迟)
    线程 = threading.Thread(target=服.serve_forever, daemon=True)
    线程.start()
    return 服


def _跑真实通道(服, 报告目录, 并发, 超时=180):
    环境 = {
        **os.environ,
        "HARNESS_CHANNEL": "real",
        "HARNESS_REPORT": os.path.join(str(报告目录), "评测报告"),
        "HARNESS_CONCURRENCY": str(并发),
        "HARNESS_RATE": "1000",
        "HARNESS_RETRIES": "1",
        # 端点指向本地假服务器：real 通道走通但一个字节都不出机器
        "DEEPSEEK_BASE_URL": "http://127.0.0.1:%d" % 服.port,
        "DEEPSEEK_MODEL": "fake-model",
        "DEEPSEEK_API_KEY": "sk-fake-key-for-test",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    结果 = subprocess.run(
        [sys.executable, "-m", "cli.light_unified", "run", _评测驱动],
        cwd=_PROJECT, env=环境, capture_output=True, timeout=超时,
    )
    报告路径 = os.path.join(str(报告目录), "评测报告.json")
    return 结果.returncode, 报告路径, 结果.stdout + 结果.stderr


def _读报告(路径):
    with open(路径, encoding="utf-8") as fh:
        return json.load(fh)


def _文本(字节串):
    return 字节串.decode("utf-8", errors="replace")


class Test真实通道:
    def test_并发跑通且每条请求各占一条连接(self, tmp_path):
        """并发 2 跑 6 条：不许崩，且服务端应看到 6 条独立连接。

        共享一个客户端时这里是 `[WinError 10038]`（rc!=0、无报告）；
        连接数 < 6 说明有请求复用了同一条 socket，那正是崩溃的前提。
        """
        服 = _起服务器()
        try:
            rc, 报告路径, 输出 = _跑真实通道(服, tmp_path, 并发=2)
            assert rc == 0, "real 通道并发跑失败\n%s" % _文本(输出)
            报告 = _读报告(报告路径)
            assert 报告["元信息"]["通道"] == "real"
            assert 报告["元信息"]["并发上限"] == 2
            assert 服.连接数 == 6, "6 条评测应各建一条连接，实际 %d" % 服.连接数
        finally:
            服.shutdown()
            服.server_close()

    def test_鉴权头是非空Bearer(self, tmp_path):
        """key 走环境变量时 Authorization 必须真带上 key。

        codegen 那个 `设 密钥 为 …` → `self.密钥 = …` 的错编会让这里收到
        裸 "Bearer "（真实 DeepSeek 回 401）。
        """
        服 = _起服务器()
        try:
            rc, _, 输出 = _跑真实通道(服, tmp_path, 并发=1)
            assert rc == 0, _文本(输出)
            assert 服.鉴权头们 == ["Bearer sk-fake-key-for-test"] * 6, 服.鉴权头们
        finally:
            服.shutdown()
            服.server_close()

    def test_并发比串行快(self, tmp_path):
        """每请求 0.3s 延迟：并发 3 的总耗时必须明显低于串行，否则并发是假的。"""
        服并 = _起服务器(每请求延迟=0.3)
        try:
            rc并, 报告并, 输出并 = _跑真实通道(服并, tmp_path / "并", 并发=3)
            assert rc并 == 0, _文本(输出并)
            并发耗时 = _读报告(报告并)["元信息"]["总耗时"]
        finally:
            服并.shutdown()
            服并.server_close()

        服串 = _起服务器(每请求延迟=0.3)
        try:
            rc串, 报告串, 输出串 = _跑真实通道(服串, tmp_path / "串", 并发=1)
            assert rc串 == 0, _文本(输出串)
            串行耗时 = _读报告(报告串)["元信息"]["总耗时"]
        finally:
            服串.shutdown()
            服串.server_close()

        assert 并发耗时 * 1.5 < 串行耗时, (
            "并发 3 应明显快于串行：并发 %.2fs / 串行 %.2fs" % (并发耗时, 串行耗时))
