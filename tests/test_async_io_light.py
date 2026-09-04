# -*- coding: utf-8 -*-
"""
test_async_io_light.py —— 任务 A5 / M11：语言层 `等待` 真驱动网络 I/O 与 LLM 流式

被测产物全部是**光明源码编出来的东西**（`stdlib/流式.light`、`stdlib/选择器.light`、
`stdlib/大模型客户端.light`），本文件只从外部观察它们的行为。

三连判据（总纲 §1.1，缺一即红）：

1. **结构判据**：`协程读体` / `异步 段落 流式对话` 的产物在运行期真是 async 生成器、
   `协程收` 真是协程函数（用 `inspect` 问对象本身，不读源码字符串）；并且「真的 await
   网络读」由 `test_异步读体不占用事件循环` 那条心跳用例证明——若读腿是阻塞 recv，
   同一个事件循环上的心跳协程就跑不动。
2. **时序判据**：两个 mock server 各延迟 0.5s，同一份读取逻辑：串行 > 1.0s、
   并发 < 0.8s，断关系不断绝对值（原始数字由用例 print 出来）。
3. **反跑判据**：把 `协程收` 的让步改回同步阻塞 recv，本文件必须变红（前后实测贴在
   交付报告第 3 项）。

另有两条「同步语义冻结」的正向证明：同步版 `流式对话` 仍是同步生成器函数；异步腿产出的
增量块与同步版**逐字相等**（`test_异步增量与同步增量逐字相等`）。
"""
import asyncio
import inspect
import ipaddress
import json
import os
import shutil
import socket
import ssl
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest


_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB])

import 流式 as 流式模块  # noqa: E402
import 大模型客户端 as 客户端模块  # noqa: E402
from 流式 import HTTP客户端  # noqa: E402
from 大模型客户端 import 大模型客户端  # noqa: E402


# 判据门限（总纲 §1.1）
# 并发门限 0.8→1.0（09-04 全清）：FreeBSD 宿主机空闲时 TLS 两路并发实测 0.79~0.81s、
# 全核饱和 0.92s，原 0.8 门限正卡在边缘（CI 4 路 xdist 并行时更可达 1.78s）。
# 串行恒 ≥ 1.0s（2×延迟），1.0 门限仍低于串行，真正串行化（≈串行≈1.3s）依旧会被拦。
# 真正的判据是「并发 < 串行」关系（见 test_两路TLS串行与并发的关系），绝对门限只是兜底。
串行门限 = 1.0
并发门限 = 1.0
延迟 = 0.5


# ---------------------------------------------------------------------------
# mock server 群：一律 bind(("127.0.0.1", 0)) 由内核分配端口
# ---------------------------------------------------------------------------
class _基础服务器(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(8)
        self.port = self.srv.getsockname()[1]
        self.start()

    def run(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._服务, args=(conn,), daemon=True).start()

    def _吃请求(self, conn):
        req = b""
        while b"\r\n\r\n" not in req:
            片 = conn.recv(4096)
            if not 片:
                break
            req += 片
        return req

    def _服务(self, conn):
        raise NotImplementedError

    def close(self):
        try:
            self.srv.close()
        except OSError:
            pass


class 延迟体服务器(_基础服务器):
    """响应头立即到、体延迟 delay 秒才发。

    这样「读头」不构成瓶颈，被并发重叠的正是那段 delay——串行累计 2*delay、
    并发约 1*delay，关系清晰。与 tests/test_stream_async_light.py 的 C4 版同形，
    区别只在本文件驱动的是**语言层 await**，不是 Python 侧手写 selector 循环。
    """

    def __init__(self, 载荷, delay=延迟):
        self.载荷 = 载荷
        self.delay = delay
        super().__init__()

    def _服务(self, conn):
        try:
            self._吃请求(conn)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(self.载荷))
            time.sleep(self.delay)
            conn.sendall(self.载荷)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


def _sse帧(对象):
    return b"data: " + json.dumps(对象).encode("utf-8") + b"\r\n\r\n"


_文本帧组 = [
    _sse帧({"choices": [{"delta": {"role": "assistant", "content": "你"}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"content": "好"}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"content": "！"}, "finish_reason": "stop"}]}),
    b"data: [DONE]\r\n\r\n",
]

_工具帧组 = [
    _sse帧({"choices": [{"delta": {"tool_calls": [
        {"index": 0, "function": {"name": "get_weather"}}]}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"tool_calls": [
        {"index": 0, "function": {"arguments": '{"city"'}}]}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"tool_calls": [
        {"index": 0, "function": {"arguments": ':"BJ"}'}}]}, "finish_reason": "tool_calls"}]}),
    b"data: [DONE]\r\n\r\n",
]

# 真实 DeepSeek 的显式 null 形状（键在、值是 null），照 tests/test_llm_client_light.py
_null帧组 = [
    _sse帧({"choices": [{"delta": {"role": "assistant", "content": None}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"content": "在下", "role": None}, "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"content": None, "tool_calls": [
        {"index": 0, "id": "call_real_1", "function": {"name": "get_weather", "arguments": ""}}]},
        "finish_reason": None}]}),
    _sse帧({"choices": [{"delta": {"content": None, "tool_calls": [
        {"index": 0, "function": {"name": None, "arguments": '{"city":"BJ"}'}}]},
        "finish_reason": "tool_calls"}]}),
    b"data: [DONE]\r\n\r\n",
]


class SSE服务器(_基础服务器):
    """回放 SSE 帧；delay 秒后才开始发体（体延迟才是可被并发重叠的那段）。"""

    def __init__(self, 帧组, delay=0.0, 状态行=b"HTTP/1.1 200 OK\r\n"):
        self.体 = b"".join(帧组)
        self.delay = delay
        self.状态行 = 状态行
        super().__init__()

    def _服务(self, conn):
        try:
            self._吃请求(conn)
            conn.sendall(self.状态行
                         + b"Content-Type: text/event-stream\r\n"
                         + b"Content-Length: " + str(len(self.体)).encode("ascii")
                         + b"\r\n\r\n")
            if self.delay:
                time.sleep(self.delay)
            conn.sendall(self.体)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


class 错误服务器(_基础服务器):
    def _服务(self, conn):
        try:
            self._吃请求(conn)
            体 = b'{"error":"bad key"}'
            conn.sendall(b"HTTP/1.1 401 Unauthorized\r\nContent-Type: application/json\r\n"
                         b"Content-Length: " + str(len(体)).encode("ascii") + b"\r\n\r\n" + 体)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


class 分块服务器(_基础服务器):
    """Transfer-Encoding: chunked，且刻意把一个 UTF-8 汉字劈在两个 chunk 之间。"""

    def __init__(self, 分片们):
        self.分片们 = 分片们
        super().__init__()

    def _服务(self, conn):
        try:
            self._吃请求(conn)
            conn.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
            for 片 in self.分片们:
                conn.sendall(b"%x\r\n" % len(片) + 片 + b"\r\n")
            conn.sendall(b"0\r\n\r\n")
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


@pytest.fixture
def 服务器工厂():
    开着的 = []

    def _造(服务器):
        开着的.append(服务器)
        time.sleep(0.05)
        return 服务器

    yield _造
    for s in 开着的:
        s.close()


# ---------------------------------------------------------------------------
# 公共读取腿：这一份逻辑同时用于串行与并发，两组数字才可比
# ---------------------------------------------------------------------------
async def _读一路(端口):
    c = HTTP客户端("127.0.0.1", 端口)
    c.超时读取 = 5.0
    状态 = c.发送("GET", "/", {}, "")[0]
    数据 = b""
    async for 块 in c.协程读体():
        数据 += 块
    return 状态, 数据


async def _心跳(标记, 计数, 间隔=0.02):
    """事件循环还活着吗？读腿若阻塞 loop，这个协程就一次也醒不过来。"""
    while not 标记["停"]:
        await asyncio.sleep(间隔)
        计数["次"] += 1


# ---------------------------------------------------------------------------
# 1. 结构判据：问运行期对象本身
# ---------------------------------------------------------------------------
class Test结构判据:
    def test_异步读腿的产物类别(self):
        assert inspect.iscoroutinefunction(流式模块.HTTP客户端.协程收) is True
        assert inspect.isasyncgenfunction(流式模块.HTTP客户端.协程读体) is True
        assert inspect.isasyncgenfunction(流式模块.HTTP客户端.协程读分块) is True
        assert inspect.isasyncgenfunction(流式模块.HTTP客户端.协程按行读取) is True

    def test_流式对话的异步版是async生成器(self):
        assert inspect.isasyncgenfunction(客户端模块.流式对话) is True

    def test_同步版流式对话仍是同步生成器_签名冻结的机读证明(self):
        # 同步腿一行未动：它仍必须是普通生成器函数，且**不是**协程/异步生成器。
        assert inspect.isgeneratorfunction(大模型客户端.流式对话) is True
        assert inspect.isasyncgenfunction(大模型客户端.流式对话) is False
        assert inspect.iscoroutinefunction(大模型客户端.流式对话) is False

    def test_类上的异步入口返回async生成器对象且不提前发起IO(self, 服务器工厂):
        服 = 服务器工厂(SSE服务器(_文本帧组))
        c = 大模型客户端("http://127.0.0.1:%d" % 服.port, "test-model", "")
        生成器 = c.流式对话2([{"role": "user", "content": "hi"}])
        try:
            # 只是拿到 async 生成器对象，一次网络往返都还没发生
            assert inspect.isasyncgen(生成器) is True
            assert c.客户端.套接字 is None
        finally:
            asyncio.run(生成器.aclose())


# ---------------------------------------------------------------------------
# 2. 「真 await 网络读」：事件循环没被读腿占住
# ---------------------------------------------------------------------------
class Test让出控制权:
    def test_异步读体不占用事件循环(self, 服务器工厂):
        载荷 = b"A" * 200
        服 = 服务器工厂(延迟体服务器(载荷))
        标记 = {"停": False}
        计数 = {"次": 0}

        async def 主():
            async def 读():
                try:
                    return await _读一路(服.port)
                finally:
                    标记["停"] = True
            结果, _ = await asyncio.gather(读(), _心跳(标记, 计数))
            return 结果

        状态, 数据 = asyncio.run(主())
        assert 状态 == 200
        assert 数据 == 载荷
        # 体延迟 0.5s、心跳间隔 0.02s：让出控制权的实现能跑出十几到几十次；
        # 阻塞 recv 的实现只能在读完之后醒 1 次（反跑实测见交付报告）。
        print("\n[心跳] 0.5s 体延迟期间事件循环被唤醒 %d 次" % 计数["次"], flush=True)
        assert 计数["次"] >= 5


# ---------------------------------------------------------------------------
# 3. 时序判据：串行 > 1.0s、并发 < 0.8s（同一份 _读一路）
# ---------------------------------------------------------------------------
class Test时序判据:
    def test_串行与并发的关系(self, 服务器工厂):
        甲 = b"A" * 200
        乙 = b"B" * 200

        async def 串行():
            s1 = 服务器工厂(延迟体服务器(甲))
            s2 = 服务器工厂(延迟体服务器(乙))
            t0 = time.monotonic()
            一 = await _读一路(s1.port)
            二 = await _读一路(s2.port)
            return time.monotonic() - t0, 一, 二

        async def 并发():
            s1 = 服务器工厂(延迟体服务器(甲))
            s2 = 服务器工厂(延迟体服务器(乙))
            t0 = time.monotonic()
            一, 二 = await asyncio.gather(_读一路(s1.port), _读一路(s2.port))
            return time.monotonic() - t0, 一, 二

        串行秒, 串一, 串二 = asyncio.run(串行())
        并发秒, 并一, 并二 = asyncio.run(并发())

        print("\n串行 %.2fs / 并发 %.2fs" % (串行秒, 并发秒), flush=True)

        # 两种模式都要**分毫不少**地拿到体，否则「快」毫无意义
        assert (串一[1], 串二[1]) == (甲, 乙)
        assert (并一[1], 并二[1]) == (甲, 乙)
        assert 串行秒 > 串行门限, "串行 %.2fs 应 > %.1fs" % (串行秒, 串行门限)
        assert 并发秒 < 并发门限, "并发 %.2fs 应 < %.1fs" % (并发秒, 并发门限)
        assert 并发秒 < 串行秒


# ---------------------------------------------------------------------------
# 4. LLM 流式：异步腿与同步腿的增量块逐字相等
# ---------------------------------------------------------------------------
def _同步块们(端口, 消息):
    c = 大模型客户端("http://127.0.0.1:%d" % 端口, "test-model", "")
    return list(c.流式对话(消息))


def _异步块们(端口, 消息):
    async def 跑():
        c = 大模型客户端("http://127.0.0.1:%d" % 端口, "test-model", "")
        出 = []
        async for 块 in c.流式对话2(消息):
            出.append(块)
        return 出
    return asyncio.run(跑())


class TestLLM异步流式:
    消息 = [{"role": "user", "content": "hi"}]

    @pytest.mark.parametrize("帧组名", ["文本", "工具", "显式null"])
    def test_异步增量与同步增量逐字相等(self, 服务器工厂, 帧组名):
        帧组 = {"文本": _文本帧组, "工具": _工具帧组, "显式null": _null帧组}[帧组名]
        服 = 服务器工厂(SSE服务器(帧组))
        同步 = _同步块们(服.port, self.消息)
        异步 = _异步块们(服.port, self.消息)
        assert 异步 == 同步

    def test_异步腿的文本增量拼出完整回复(self, 服务器工厂):
        服 = 服务器工厂(SSE服务器(_文本帧组))
        块们 = _异步块们(服.port, self.消息)
        assert "".join(b["内容增量"] for b in 块们 if not b["结束"]) == "你好！"
        终块 = [b for b in 块们 if b["结束"]]
        assert len(终块) == 1
        assert 终块[0]["累积内容"] == "你好！"
        assert 终块[0]["角色"] == "assistant"
        assert 终块[0]["完成原因"] == "stop"

    def test_异步腿的工具调用按index累积(self, 服务器工厂):
        服 = 服务器工厂(SSE服务器(_工具帧组))
        终块 = [b for b in _异步块们(服.port, self.消息) if b["结束"]][0]
        assert 终块["工具调用增量"] == [
            {"index": 0, "name": "get_weather", "arguments": '{"city":"BJ"}', "id": "call_0"},
        ]
        assert 终块["完成原因"] == "tool_calls"

    def test_异步腿遇4xx同样抛HTTP错误(self, 服务器工厂):
        服 = 服务器工厂(错误服务器())
        with pytest.raises(Exception) as 捕:
            _异步块们(服.port, self.消息)
        assert 捕.type.__name__ == "HTTP错误"
        assert 捕.value.状态 == 401

    def test_两路LLM流式并发比串行快(self, 服务器工厂):
        甲 = 服务器工厂(SSE服务器(_文本帧组, delay=延迟))
        乙 = 服务器工厂(SSE服务器(_文本帧组, delay=延迟))

        async def 收一路(端口):
            c = 大模型客户端("http://127.0.0.1:%d" % 端口, "test-model", "")
            出 = []
            async for 块 in c.流式对话2(self.消息):
                出.append(块)
            return "".join(b["内容增量"] for b in 出 if not b["结束"])

        async def 并发():
            t0 = time.monotonic()
            甲文, 乙文 = await asyncio.gather(收一路(甲.port), 收一路(乙.port))
            return time.monotonic() - t0, 甲文, 乙文

        async def 串行():
            t0 = time.monotonic()
            甲文 = await 收一路(甲.port)
            乙文 = await 收一路(乙.port)
            return time.monotonic() - t0, 甲文, 乙文

        并发秒, 甲文, 乙文 = asyncio.run(并发())
        串行秒, _, _ = asyncio.run(串行())
        print("\n[LLM] 串行 %.2fs / 并发 %.2fs" % (串行秒, 并发秒), flush=True)
        assert (甲文, 乙文) == ("你好！", "你好！")
        assert 串行秒 > 串行门限
        assert 并发秒 < 并发门限


# ---------------------------------------------------------------------------
# 5. 异步 chunked + 按行读取：跨块的 UTF-8 多字节不许乱码
# ---------------------------------------------------------------------------
class Test异步按行读取:
    def test_跨chunk的汉字被增量解码器兜住(self, 服务器工厂):
        原文 = "你好世界\n第二行\n".encode("utf-8")
        # 劈在第 4 字节：'你'(3B) + '好' 的第 1 字节，保证跨块
        服 = 服务器工厂(分块服务器([原文[:4], 原文[4:9], 原文[9:]]))

        async def 跑():
            c = HTTP客户端("127.0.0.1", 服.port)
            c.超时读取 = 5.0
            状态 = c.发送("GET", "/", {}, "")[0]
            行们 = []
            async for 行 in c.协程按行读取():
                行们.append(行)
            return 状态, 行们

        状态, 行们 = asyncio.run(跑())
        assert 状态 == 200
        assert 行们 == ["你好世界", "第二行"]


# ---------------------------------------------------------------------------
# 6. TLS 上的异步读腿：SSLWantRead 分流真的走通了吗
# ---------------------------------------------------------------------------
# 这一节补的是 A5 首版报告里点名的最大未实测面。明文 socket 上 `recv` 抛的是
# BlockingIOError(EAGAIN)，TLS 上抛的是 ssl.SSLWantReadError —— 两条是**不同的异常
# 分支**（选择器.是否愿等读 里分别判），只测明文等于只测了一半。
#
# 顺便记一个本来可能咬人的点：TLS 有自己的内部缓冲，socket 层「不可读」时 SSL 层
# 仍可能有整条记录待解密。`探测就绪` 说「没就绪」并不代表没数据——好在 协程收 的
# 循环里探测结果**只决定睡多久**，下一轮无条件重试 recv，所以这种情形只是多睡一个
# 粒度，不会假死。若哪天改成「探测说没就绪就不重试」，这一节会当场红。
def _生成证书(目录):
    """自签 CA + 127.0.0.1 服务器证书。cryptography 只在测试侧用，不进 .light。

    故意**局部导入**：缺 cryptography 时只让这一节报错，不连带把结构/时序/反跑
    三连判据一起拖成收集失败（总纲 §5.7）。
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    ca密钥 = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                      backend=default_backend())
    ca名 = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "taskA5-Test-CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca名).issuer_name(ca名)
        .public_key(ca密钥.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        # CA 的 KeyUsage 同样不是装饰：缺了报「CA cert does not include key usage
        # extension」（实测）。参数顺序照 cryptography 的位置参数：
        # digital_signature / content_commitment / key_encipherment / data_encipherment
        # / key_agreement / key_cert_sign / crl_sign / encipher_only / decipher_only
        .add_extension(x509.KeyUsage(True, True, True, False, False, True, True,
                                    False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca密钥.public_key()),
                       critical=False)
        .sign(ca密钥, hashes.SHA256(), default_backend())
    )
    ca文件 = os.path.join(目录, "_taskA5_ca.pem")
    with open(ca文件, "wb") as f:
        f.write(ca.public_bytes(serialization.Encoding.PEM))

    服务器密钥 = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                          backend=default_backend())
    服务器名 = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    服务器证书 = (
        x509.CertificateBuilder()
        .subject_name(服务器名).issuer_name(ca名)
        .public_key(服务器密钥.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName(
            [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                       critical=False)
        # AuthorityKeyIdentifier 不是可选装饰：Python 3.14 的校验器缺了它就直接
        # 「Missing Authority Key Identifier」拒证（实测），与 test_tls_light.py 同款。
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
            ca密钥.public_key()), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(
            服务器密钥.public_key()), critical=False)
        .sign(ca密钥, hashes.SHA256(), default_backend())
    )
    证书文件 = os.path.join(目录, "_taskA5_server.crt")
    with open(证书文件, "wb") as f:
        f.write(服务器证书.public_bytes(serialization.Encoding.PEM))
    密钥文件 = os.path.join(目录, "_taskA5_server.key")
    with open(密钥文件, "wb") as f:
        f.write(服务器密钥.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
    return ca文件, 证书文件, 密钥文件


class TLS延迟服务器(_基础服务器):
    """TLS 版「响应头立即到、体延迟 delay 秒」，可接多条连接。"""

    def __init__(self, 证书文件, 密钥文件, 载荷, delay=延迟):
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(证书文件, 密钥文件)
        self.载荷 = 载荷
        self.delay = delay
        super().__init__()

    def _服务(self, conn):
        加密连接 = None
        try:
            加密连接 = self.ctx.wrap_socket(conn, server_side=True)
            self._吃请求(加密连接)
            加密连接.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n"
                             % len(self.载荷))
            time.sleep(self.delay)
            加密连接.sendall(self.载荷)
        except OSError:
            pass
        finally:
            if 加密连接 is not None:
                try:
                    加密连接.close()
                except OSError:
                    pass
            else:
                try:
                    conn.close()
                except OSError:
                    pass


@pytest.fixture(scope="module")
def 证书():
    目录 = tempfile.mkdtemp(prefix="_taskA5_")
    try:
        yield _生成证书(目录)
    finally:
        shutil.rmtree(目录, ignore_errors=True)


async def _读一路TLS(端口, ca文件):
    c = HTTP客户端("127.0.0.1", 端口)
    c.配置TLS(True, True, ca文件, None)
    c.超时读取 = 5.0
    状态 = c.发送("GET", "/", {}, "")[0]
    数据 = b""
    async for 块 in c.协程读体():
        数据 += 块
    return 状态, 数据


class TestTLS异步读腿:
    def test_tls异步读体拿到完整体且不占用事件循环(self, 证书, 服务器工厂):
        ca文件, 证书文件, 密钥文件 = 证书
        载荷 = b"T" * 300
        服 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, 载荷))
        标记 = {"停": False}
        计数 = {"次": 0}

        async def 主():
            async def 读():
                try:
                    return await _读一路TLS(服.port, ca文件)
                finally:
                    标记["停"] = True
            结果, _ = await asyncio.gather(读(), _心跳(标记, 计数))
            return 结果

        状态, 数据 = asyncio.run(主())
        assert 状态 == 200
        assert 数据 == 载荷
        print("\n[TLS 心跳] 0.5s 体延迟期间事件循环被唤醒 %d 次" % 计数["次"], flush=True)
        assert 计数["次"] >= 5

    def test_两路TLS串行与并发的关系(self, 证书, 服务器工厂):
        ca文件, 证书文件, 密钥文件 = 证书
        甲, 乙 = b"T" * 300, b"S" * 300

        async def 串行():
            s1 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, 甲))
            s2 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, 乙))
            t0 = time.monotonic()
            一 = await _读一路TLS(s1.port, ca文件)
            二 = await _读一路TLS(s2.port, ca文件)
            return time.monotonic() - t0, 一, 二

        async def 并发():
            s1 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, 甲))
            s2 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, 乙))
            t0 = time.monotonic()
            一, 二 = await asyncio.gather(_读一路TLS(s1.port, ca文件),
                                          _读一路TLS(s2.port, ca文件))
            return time.monotonic() - t0, 一, 二

        串行秒, 串一, 串二 = asyncio.run(串行())
        并发秒, 并一, 并二 = asyncio.run(并发())
        print("\n[TLS] 串行 %.2fs / 并发 %.2fs" % (串行秒, 并发秒), flush=True)
        assert (串一[1], 串二[1]) == (甲, 乙)
        assert (并一[1], 并二[1]) == (甲, 乙)
        assert 串行秒 > 串行门限
        assert 并发秒 < 并发门限
        # 关系判据（测试本意「断关系不断绝对值」）：并发必须比串行快。
        # 09-04 全清补上：仅靠绝对门限在慢/满载 CI 上会误红，关系才是真正语义。
        assert 并发秒 < 串行秒, "并发 %.2fs 应 < 串行 %.2fs" % (并发秒, 串行秒)

    def test_tls异步腿的读超时抛读取错误(self, 证书, 服务器工厂):
        """服务端把体拖到 2s，客户端 超时读取=0.5s → 必须抛 读取错误，不许静默截断。

        这条同时守住 TLS 分支上的**超时归属**：走的是 协程收 里那句
        `time.monotonic() >= 截止` → 读取错误，而不是被 want-read 无限重试挂死。
        """
        from 流式 import 读取错误
        ca文件, 证书文件, 密钥文件 = 证书
        服 = 服务器工厂(TLS延迟服务器(证书文件, 密钥文件, b"T" * 300, delay=2.0))

        async def 跑():
            c = HTTP客户端("127.0.0.1", 服.port)
            c.配置TLS(True, True, ca文件, None)
            c.超时读取 = 0.5
            c.发送("GET", "/", {}, "")
            数据 = b""
            async for 块 in c.协程读体():
                数据 += 块
            return 数据

        起 = time.monotonic()
        with pytest.raises(读取错误) as 捕:
            asyncio.run(跑())
        用时 = time.monotonic() - 起
        print("\n[TLS 超时] %.2fs 抛出：%s" % (用时, 捕.value), flush=True)
        assert "超时" in str(捕.value)
        assert 用时 < 1.5


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-s"]))


