# -*- coding: utf-8 -*-
"""
test_stream_light.py —— 流式传输层 + 选择器（C4 独占文件）

覆盖：
- C4-1：选择器.light 的 fd 级多路复用（空→含 fd→注销后不再返回）
- C4-2：TLS want-read / want-write 分离判定（是否愿等读/是否愿等写）
- 流式 HTTP/1.1 往返：content-length / chunked / 连接关闭三种体读取
- 非阻塞读原语：发送后套接字为非阻塞（getblocking），裸 recv 立即抛 EAGAIN

全部用真实行为断产物（时序、副作用、返回值），不 grep 源码字符串。
"""
import errno
import os
import socket
import ssl
import sys
import threading
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 选择器 import 新建选择器, 注册, 注销, 等待, 关闭选择器, 是否愿等读, 是否愿等写
from 流式 import HTTP客户端, 读取错误


# ---------------------------------------------------------------------------
# C4-1：选择器 fd 级多路复用
# ---------------------------------------------------------------------------
class TestSelector:
    def test_read_empty_then_flags_ready(self):
        a, b = socket.socketpair()
        sel = 新建选择器()
        try:
            注册(sel, a, "读")
            # 未写入：等待 0.05 返回空列表（不是抛异常）
            assert 等待(sel, 0.05) == []
            b.sendall(b"x")
            ready = 等待(sel, 1.0)
            assert a.fileno() in ready
        finally:
            关闭选择器(sel)
            a.close()
            b.close()

    def test_unregister_no_longer_flagged(self):
        a, b = socket.socketpair()
        sel = 新建选择器()
        try:
            注册(sel, a, "读")
            b.sendall(b"x")
            assert 等待(sel, 0.5)  # 至少非空
            注销(sel, a)
            # 注销后不再返回该 fd
            assert 等待(sel, 0.05) == []
        finally:
            关闭选择器(sel)
            a.close()
            b.close()

    def test_write_event_flags_ready(self):
        a, b = socket.socketpair()
        sel = 新建选择器()
        try:
            注册(sel, a, "写")  # 空读缓冲的 socketpair 总是可写
            assert 等待(sel, 1.0)  # 写就绪应命中
        finally:
            关闭选择器(sel)
            a.close()
            b.close()


# ---------------------------------------------------------------------------
# C4-2：TLS want-read / want-write 分离
# ---------------------------------------------------------------------------
class TestTLSWantSeparation:
    def test_want_read_vs_want_write_mapped_correctly(self):
        wr = ssl.SSLWantReadError()
        ww = ssl.SSLWantWriteError()
        # want-read → 愿等读，不愿等写
        assert 是否愿等读(wr) is True
        assert 是否愿等写(wr) is False
        # want-write → 愿等写，不愿等读
        assert 是否愿等写(ww) is True
        assert 是否愿等读(ww) is False

    def test_plain_eagain_maps_to_read(self):
        e = BlockingIOError(errno.EAGAIN, "would block")
        e.errno = errno.EAGAIN
        assert 是否愿等读(e) is True
        # F9 S2 改判：裸 socket 的 EAGAIN 在**写**路径上同样是「缓冲满，等可写」——
        # 原断言写的是 False，那正是 HTTP服务端.light 的 发送字节 把一次正常的
        # 「稍后再发」当成致命 连接中断 的来源。两侧都判真、由调用点自己决定问哪一边
        # （流式.light:273/377 先问读，EAGAIN 在那里仍然走「等读」，语义未变）。
        assert 是否愿等写(e) is True



# ---------------------------------------------------------------------------
# 流式 HTTP/1.1 往返：真实 mock server（真 HTTP 分帧，不是伪造字节流）
# ---------------------------------------------------------------------------
class MockHTTP:
    """多连接 HTTP/1.1 服务：body_mode ∈ cl/chunked/close/headers_first。"""

    def __init__(self, body, body_mode="cl", status=200, headers_first=False, req_hdr=False):
        self.body = body
        self.body_mode = body_mode
        self.status = status
        self.headers_first = headers_first
        self.req_hdr = req_hdr
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(32)
        self.port = self.srv.getsockname()[1]
        self._serve_n = 8
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        for _ in range(self._serve_n):
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handler, args=(conn,), daemon=True).start()

    def _handler(self, conn):
        try:
            _req = conn.recv(4096)
        except OSError:
            conn.close()
            return
        body = self.body
        if self.body_mode == "cl":
            hdr = (b"HTTP/1.1 %d OK\r\nContent-Length: %d\r\n\r\n" % (self.status, len(body)))
        elif self.body_mode == "chunked":
            hdr = (b"HTTP/1.1 %d OK\r\nTransfer-Encoding: chunked\r\n\r\n"
                   b"%x\r\n" % (self.status, len(body)))
        else:  # close
            hdr = b"HTTP/1.1 %d OK\r\nConnection: close\r\n\r\n" % self.status
        try:
            conn.sendall(hdr)
        except OSError:
            conn.close()
            return
        if self.headers_first:
            time.sleep(0.3)  # 制造「头已到、体未到」的非阻塞窗口
        if self.body_mode == "chunked":
            try:
                conn.sendall(body + b"\r\n0\r\n\r\n")
            except OSError:
                pass
        else:
            try:
                conn.sendall(body)
            except OSError:
                pass
        try:
            conn.close()
        except OSError:
            pass


def collect(c):
    """用 流式.read_body 收集全部体字节。"""
    return b"".join(c.read_body())


class TestStreamRoundTrip:
    def _start(self, body, mode, headers_first=False):
        m = MockHTTP(body, mode, headers_first=headers_first)
        return m

    def test_content_length_body(self):
        m = MockHTTP(b"hello world payload", "cl")
        c = HTTP客户端("127.0.0.1", m.port)
        hdr = c.发送("GET", "/", {}, "")
        assert hdr[0] == 200
        assert collect(c) == b"hello world payload"
        m.srv.close()

    def test_chunked_body(self):
        m = MockHTTP(b"chunked payload here", "chunked")
        c = HTTP客户端("127.0.0.1", m.port)
        hdr = c.发送("GET", "/", {}, "")
        assert hdr[0] == 200
        assert collect(c) == b"chunked payload here"
        m.srv.close()

    def test_connection_close_body(self):
        m = MockHTTP(b"close-delimited body", "close")
        c = HTTP客户端("127.0.0.1", m.port)
        hdr = c.发送("GET", "/", {}, "")
        assert hdr[0] == 200
        assert collect(c) == b"close-delimited body"
        m.srv.close()

    def test_after_send_socket_is_nonblocking(self):
        """C4-2 结构/行为判据：连接建立后读原语走非阻塞路径。"""
        m = MockHTTP(b"stream", "cl", headers_first=True)
        c = HTTP客户端("127.0.0.1", m.port)
        c.超时读取 = 3.0
        c.发送("GET", "/", {}, "")
        assert c.套接字.getblocking() is False
        m.srv.close()

    def test_naked_recv_raises_eagain_quickly(self):
        """非阻塞读原语：对未就绪套接字裸 recv 立即抛 EAGAIN（不阻塞、不吞）。"""
        m = MockHTTP(b"stream", "cl", headers_first=True)
        c = HTTP客户端("127.0.0.1", m.port)
        c.超时读取 = 3.0
        c.发送("GET", "/", {}, "")
        s = c.套接字
        t0 = time.monotonic()
        with pytest.raises(OSError) as ei:
            s.recv(1)  # 头已读尽、体未到 → 非阻塞立即 EAGAIN
        elapsed = time.monotonic() - t0
        assert ei.value.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
        assert elapsed < 0.2, f"裸 recv 应立刻 EAGAIN，却花了 {elapsed:.3f}s"
        m.srv.close()

    def test_selector_read_of_live_client_fd(self):
        """把活客户端的套接字注册进新的选择器，等就绪后能读到体 —— 证明 fd 多路复用可用。"""
        m = MockHTTP(b"selector-able", "cl", headers_first=True)
        c = HTTP客户端("127.0.0.1", m.port)
        c.超时读取 = 3.0
        c.发送("GET", "/", {}, "")
        sel = 新建选择器()
        try:
            注册(sel, c.套接字, "读")
            ready = 等待(sel, 1.0)
            assert c.套接字.fileno() in ready
        finally:
            关闭选择器(sel)
        m.srv.close()


# ---------------------------------------------------------------------------
# 合并期补的两条（第四轮 C4 只读复核的 P1-1 / P1-2，由主线在合并点补齐）
# ---------------------------------------------------------------------------
class TestReadContractAtMerge:
    """守 `收` 的两条容易被悄悄改坏的语义。

    这两条不是 C4 交付漏做，是复核时发现「实现是对的但无人看守」：
    - P1-1：`收` 的错误契约是「所有异常都包成 读取错误」（总纲 §4.2 冻结）。
      原实现 `是否愿等读` 里直接取 `e.errno`，遇到没有 errno 的异常
      （SSL socket unwrap 后 recv 抛 ValueError；套接字置空后再调 收 抛 AttributeError）
      会让 AttributeError 从 except 内部逃出去，绕开 读取错误。
    - P1-2：超时语义从 `settimeout` 改成了「选择器累计等待」，
      `截止/剩余` 的计算一处符号写错就会变成永等 —— 全 tests 原来一条都没断过它。
    """

    def test_无errno的异常不被误判成可等待(self):
        """P1-1：没有 errno 的异常必须安静地返回假，让调用方走到 抛 读取错误 那一支。"""
        # 修前这三行会抛 AttributeError: 'ValueError' object has no attribute 'errno'
        assert 是否愿等读(ValueError("boom")) is False
        assert 是否愿等写(ValueError("boom")) is False
        assert 是否愿等读(AttributeError("套接字已置空")) is False
        assert 是否愿等写(AttributeError("套接字已置空")) is False
        # 真正该被判可等待的仍然可等待（防止一刀切成假）
        assert 是否愿等读(ssl.SSLWantReadError()) is True
        assert 是否愿等写(ssl.SSLWantWriteError()) is True

    def test_读超时抛读取错误且不永等(self):
        """P1-2：头到了体永远不来时，收 必须在 超时读取 附近抛 读取错误，不许永等。"""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(4)
        port = srv.getsockname()[1]
        held = []

        def serve():
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            held.append(conn)
            try:
                conn.recv(4096)
                # 声明有 16 字节体，但一个字节都不发 —— 制造纯超时场景
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\n")
            except OSError:
                return
            time.sleep(3.0)

        threading.Thread(target=serve, daemon=True).start()
        try:
            c = HTTP客户端("127.0.0.1", port)
            c.超时读取 = 0.4
            hdr = c.发送("GET", "/", {}, "")
            assert hdr[0] == 200
            t0 = time.monotonic()
            with pytest.raises(读取错误):
                c.收(4096)
            elapsed = time.monotonic() - t0
            # 下界防「立刻抛」（那说明根本没等），上界防「永等」
            assert 0.3 < elapsed < 2.0, f"超时应在 0.4s 附近生效，实际 {elapsed:.3f}s"
        finally:
            srv.close()
            for conn in held:
                try:
                    conn.close()
                except OSError:
                    pass


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))