# -*- coding: utf-8 -*-
"""
test_stream_async_light.py —— 任务 C4-3：M7 三重判据（本轮硬目标）

同一份用例跑两种「等数据」模式，断的是关系而不是单个绝对值（慢机器上绝对
值会飘）：
  1. 结构判据：连接建立后读路径必须是非阻塞（getblocking()==False），
     说明「等数据」只能交给选择器——用「实现里能观察到的行为」断，不用
     grep 源码字符串（任务书 §4.3 允许行为判据）。
  2. 时序判据：两个 mock server 各在响应前 sleep(0.5)；同一份请求/收集逻辑：
       - 串行做两条 → 总耗时 > 1.0s
       - 选择器同时等两个 fd → 总耗时 < 0.8s
     断言的是两者关系与上述门限。
  3. 反跑判据：把非阻塞那一步改回阻塞，本用例必须变红（交付报告贴前后实测）。

全部用真实行为断产物（时序、副作用、返回值），不 grep 源码字符串。
"""
import os
import selectors
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

from 流式 import HTTP客户端


# ---------------------------------------------------------------------------
# mock server：收到请求后 头 立即返回，体 延迟 0.5s 才到。
# 这样「读头」不构成并发瓶颈，真正被选择的「等体」才是满 0.5s 的关键路径，
# 串行累计 ≥ 1.0s、并发（两个 fd 同时就绪）≈ 0.5s，关系清晰可断。
# ---------------------------------------------------------------------------
class DelayedBodyServer:
    def __init__(self, payload, delay=0.5):
        self.payload = payload
        self.delay = delay
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(16)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handler, args=(conn,), daemon=True).start()

    def _handler(self, conn):
        try:
            conn.recv(4096)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(self.payload))
            time.sleep(self.delay)
            conn.sendall(self.payload)
            conn.close()
        except OSError:
            try:
                conn.close()
            except OSError:
                pass

    def close(self):
        try:
            self.srv.close()
        except OSError:
            pass


# ---- 串行：一条「请求→读完整体」结束后才做另一条。每个 mock server 在
#      收到请求后 body 延迟 delay 秒，故两条各满 delay，累计 ~2*delay。----
def run_serial(delay):
    p1 = b"A" * 200
    p2 = b"B" * 200
    t0 = time.monotonic()
    s1 = DelayedBodyServer(p1, delay=delay)
    c1 = HTTP客户端("127.0.0.1", s1.port)
    c1.超时读取 = 5.0
    try:
        assert c1.发送("GET", "/", {}, "")[0] == 200  # 头即到，体延迟中
        d1 = b"".join(c1.read_body())                  # 满 delay 才拿完体
    finally:
        c1.关闭(); s1.close()
    s2 = DelayedBodyServer(p2, delay=delay)            # 第 2 条现在才开始
    c2 = HTTP客户端("127.0.0.1", s2.port)
    c2.超时读取 = 5.0
    try:
        assert c2.发送("GET", "/", {}, "")[0] == 200
        d2 = b"".join(c2.read_body())                  # 又满 delay
    finally:
        c2.关闭(); s2.close()
    elapsed = time.monotonic() - t0
    return elapsed, d1, d2


# ---- 并发：两个连接同时建好、同时等体；用一个选择器同时等两个 fd，
#      谁就绪读谁（两段 delay 并行重叠，累计 ~delay）。----
def run_concurrent(delay):
    p1 = b"A" * 200
    p2 = b"B" * 200
    s1 = DelayedBodyServer(p1, delay=delay)
    s2 = DelayedBodyServer(p2, delay=delay)
    c1 = HTTP客户端("127.0.0.1", s1.port)
    c2 = HTTP客户端("127.0.0.1", s2.port)
    c1.超时读取 = 5.0
    c2.超时读取 = 5.0
    sel = selectors.DefaultSelector()
    buf = {c1: b"", c2: b""}
    expect = {c1: p1, c2: p2}
    done = set()
    try:
        # 头 即到不构成瓶颈；两 body 的 delay 在此并行开始
        assert c1.发送("GET", "/", {}, "")[0] == 200
        assert c2.发送("GET", "/", {}, "")[0] == 200
        sel.register(c1.套接字, selectors.EVENT_READ, c1)
        sel.register(c2.套接字, selectors.EVENT_READ, c2)
        t0 = time.monotonic()
        while len(done) < 2:
            for key, _ in sel.select(0.6):
                cc = key.data
                if id(cc) in done:
                    continue
                try:
                    chunk = cc.收(4096)
                except Exception:
                    chunk = b""
                if chunk:
                    buf[cc] += chunk
                if len(buf[cc]) >= len(expect[cc]) or not chunk:
                    done.add(id(cc))
        elapsed = time.monotonic() - t0
    finally:
        sel.close()
        c1.关闭(); c2.关闭()
        s1.close(); s2.close()
    return elapsed, buf[c1], buf[c2]


class TestM7Triples:
    # 门限（任务书 §4.3）：串行 > 1.0s、并发 < 0.8s
    SERIAL_GATE = 1.0
    CONCURRENT_MAX = 0.8

    def _pair(self, delay):
        p1 = b"A" * 200
        p2 = b"B" * 200
        s1 = DelayedBodyServer(p1, delay=delay)
        s2 = DelayedBodyServer(p2, delay=delay)
        c1 = HTTP客户端("127.0.0.1", s1.port)
        c2 = HTTP客户端("127.0.0.1", s2.port)
        c1.超时读取 = 5.0
        c2.超时读取 = 5.0
        # 头 立即可回，两个连接都在这里完成握手与读头（不阻塞）
        assert c1.发送("GET", "/", {}, "")[0] == 200
        assert c2.发送("GET", "/", {}, "")[0] == 200
        # 记期待体长，供并发读判断完成
        c1._expect = p1
        c2._expect = p2
        return s1, s2, c1, c2

    # ---- 结构判据：读路径是非阻塞的（行为可观察，不用 grep 源码）----
    def test_read_path_is_nonblocking(self):
        s1, s2, c1, c2 = self._pair(0.5)
        try:
            assert c1.套接字.getblocking() is False, "发送后套接字应已转非阻塞"
            assert c2.套接字.getblocking() is False
        finally:
            for c in (c1, c2):
                c.关闭()
            s1.close(); s2.close()

    # ---- 时序判据 + 反跑前置：串行 >1.0s、并发 <0.8s 且并发 < 串行 ----
    def test_serial_vs_concurrent_timing(self):
        s_el, sd1, sd2 = run_serial(0.5)
        # 行为正确性：两模式拿到的体都分毫不少
        assert sd1 == b"A" * 200 and sd2 == b"B" * 200
        # 串行应 > 1.0s（两条各满 0.5s 的等待逐条累计）
        assert s_el > self.SERIAL_GATE, (
            f"串行总耗时 {s_el:.2f}s 应 > {self.SERIAL_GATE}s"
        )

        # 并发：同一份 body 收集逻辑，用选择器同时等两个 fd
        cn_el, cd1, cd2 = run_concurrent(0.5)
        assert cd1 == b"A" * 200 and cd2 == b"B" * 200
        assert cn_el < self.CONCURRENT_MAX, (
            f"并发总耗时 {cn_el:.2f}s 应 < {self.CONCURRENT_MAX}s"
        )
        # 关系优先：并发必须显著快于串行（两个 fd 被同时等待）
        assert cn_el < s_el, (
            f"并发 {cn_el:.2f}s 应 < 串行 {s_el:.2f}s，才能证明多路复用"
        )
        print(f"\n串行 {s_el:.2f}s / 并发 {cn_el:.2f}s", flush=True)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-s"]))