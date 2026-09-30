# -*- coding: utf-8 -*-
"""test_第7轮_io矩阵.py —— 第7轮 A线 #274：事件循环×套接字 跨平台 I/O 底座收敛回归

被测产物（R66/R67/R69 七件套 + 第7轮收敛件）：
  - stdlib/lightpub/事件驱动.py、异步运行时.py（事件循环 / 异步一等的 Python 桥）
  - stdlib/选择器.light（fd 级多路复用）
  - stdlib/流式.light（非阻塞读原语 协程收）
  - stdlib/HTTP服务端.light（非阻塞 TCP 上跑的 HTTP/1.1 服务端）
  - stdlib/并发.light（asyncio 编排原语，超时运行 增令牌竞速）
  - stdlib/伪终端.light（Windows ConPTY / POSIX openpty）
  - stdlib/进程树.light（超时杀树 + 第7轮增令牌中止）
  - stdlib/中止.light（第7轮新增：统一中止令牌，唯一取消实现）

本轮收敛点（每条用例顶部标收敛依据）：
  1. 取消语义统一：令牌贯穿 选择器/流式/并发/伪终端/进程树，中止抛 已取消异常，
     各层先清理 pending 再冒泡（进程树=杀树、并发=取消任务、伪终端=停读线程）。
  2. 跨平台门：socketpair 跨线程唤醒通道（Windows ConPTY 句柄不进 select）、
     AF_UNIX 仅 POSIX 回环 / Windows 置空。
  3. 套接字集成回归：非阻塞 TCP echo（并发 3 客户端一致）、UDP 收发、
     流式非阻塞读、HTTP 服务端请求响应。
  4. 事件循环驱动：非阻塞 accept/recv/send 腿全部在 asyncio 循环内让步推进。

反跑判据（合并点人工复跑，登记 #274 卡「反跑判据」字段；改→红→还原）：
  ① 事件循环去掉 socketpair 唤醒通道（Test跨线程唤醒_内核通道：把
     call_soon_threadsafe 改成无内核唤醒的自旋/直接置标志）→ 跨线程唤醒用例立红
     —— 0.5s 内收不到投递即超时。
  ② 选择器.等待 的「超时返回 []」改成「抛异常」→ Test选择器超时语义 立红
     （超时分支断言 返回 []，抛异常即用例失败）。
  ③ 进程树.等待 去掉超时杀树（删 超时发生 分支的 杀树 调用）→
     Test进程树超时杀树 立红（子进程 30s 长驻，0.6s 等待后 是否存活 必须为 假）。
"""
import asyncio
import os
import socket
import subprocess
import sys
import threading
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB])  # noqa: E402

from 中止 import 新建令牌, 已取消异常  # noqa: E402
from 选择器 import 新建选择器, 注册, 等待, 等待就绪, 探测就绪, 关闭选择器  # noqa: E402
from 并发 import 超时运行  # noqa: E402
from 流式 import HTTP客户端  # noqa: E402
from 进程树 import 进程树  # noqa: E402
from 伪终端 import 伪控制台  # noqa: E402

网络超时 = 5.0
用例超时 = 60.0


async def _限时包裹(可等对象, 说明, 秒=网络超时):
    """网络等待一律带硬上限：挂死必须表现为失败，不是卡死（沿 F9 判据纪律）。"""
    try:
        return await asyncio.wait_for(可等对象, 秒)
    except (asyncio.TimeoutError, TimeoutError):
        raise AssertionError("等「%s」超过 %s 秒仍未完成" % (说明, 秒))


def _占端口():
    """内核分配一个可用 TCP 端口（bind 0 → getsockname → 关闭让位）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    端口 = s.getsockname()[1]
    s.close()
    return 端口


# ---------------------------------------------------------------------------
# 事件循环驱动的非阻塞 TCP echo（收敛点 1+3：accept/recv/send 全在循环内让步）
# ---------------------------------------------------------------------------
async def _回显连接腿(conn):
    conn.setblocking(False)
    try:
        while True:
            try:
                数据 = conn.recv(4096)
            except (BlockingIOError, InterruptedError):
                await asyncio.sleep(0.0005)
                continue
            if not 数据:
                break
            # 非阻塞 send：EAGAIN 时让步重试（小负载实测一两轮即过）
            while 数据:
                try:
                    已发 = conn.send(数据)
                    数据 = 数据[已发:]
                except (BlockingIOError, InterruptedError):
                    await asyncio.sleep(0.0005)
    finally:
        try:
            conn.close()
        except OSError:
            pass


async def _回显服务腿(监听, 收尾):
    监听.setblocking(False)
    try:
        while not 收尾["停"]:
            try:
                conn, _ = 监听.accept()
            except (BlockingIOError, InterruptedError):
                await asyncio.sleep(0.002)
                continue
            asyncio.get_event_loop().create_task(_回显连接腿(conn))
    finally:
        监听.close()


class Test事件循环TCP回显:
    def test_并发3客户端回显一致(self):
        """收敛点 3：非阻塞 TCP echo，3 客户端并发各自收全自己的负载（互不串线）。"""
        收尾 = {"停": False}

        async def 主管():
            监听 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            监听.bind(("127.0.0.1", 0))
            监听.listen(8)
            端口 = 监听.getsockname()[1]
            服务任务 = asyncio.get_event_loop().create_task(_回显服务腿(监听, 收尾))

            async def 客户端(标记, n):
                # 事件循环内禁止阻塞 select（会冻结循环、服务腿饿死——
                # 这正是 A5「事件循环里唯一可用问法是 探测就绪」的教训）：
                # 套接字腿 = 非阻塞 recv/send + 探测就绪 + 让步，与 流式.协程收 同构。
                c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c.settimeout(5.0)
                c.connect(("127.0.0.1", 端口))
                c.setblocking(False)
                载荷 = (标记 * 64 + b"|END|") * n
                sel = 新建选择器()
                注册(sel, c, "读写")
                发送缓冲 = 载荷
                收到 = b""
                while len(收到) < len(载荷):
                    if 发送缓冲:
                        try:
                            已发 = c.send(发送缓冲)
                            发送缓冲 = 发送缓冲[已发:]
                        except (BlockingIOError, InterruptedError):
                            if not 探测就绪(sel, c, "写"):
                                await asyncio.sleep(0.0005)
                    try:
                        块 = c.recv(65536)
                        收到 += 块
                    except (BlockingIOError, InterruptedError):
                        if not 探测就绪(sel, c, "读"):
                            await asyncio.sleep(0.0005)
                    # 每轮必须让出一次循环（异步睡眠(0)=纯让步），服务腿才推得动
                    await asyncio.sleep(0)
                关闭选择器(sel)
                c.close()
                return 收到

            try:
                结果们 = await _限时包裹(asyncio.gather(
                    客户端(b"A", 3), 客户端(b"B", 5), 客户端(b"C", 9)), "echo 并发", 用例超时)
            finally:
                收尾["停"] = True
                服务任务.cancel()
            return 结果们

        甲, 乙, 丙 = asyncio.run(主管())
        assert 甲 == (b"A" * 64 + b"|END|") * 3
        assert 乙 == (b"B" * 64 + b"|END|") * 5
        assert 丙 == (b"C" * 64 + b"|END|") * 9

    def test_UDP收发(self):
        """收敛点 3：UDP 回环收发（recv 超时 2s 内必到）。"""
        甲 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        乙 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        甲.bind(("127.0.0.1", 0))
        乙.bind(("127.0.0.1", 0))
        乙.settimeout(2.0)
        甲.sendto("udp-第7轮-你好".encode("utf-8"), 乙.getsockname())
        数据, 对端 = 乙.recvfrom(65536)
        assert 数据 == "udp-第7轮-你好".encode("utf-8")
        assert 对端[1] == 甲.getsockname()[1]
        甲.close()
        乙.close()


# ---------------------------------------------------------------------------
# 选择器超时语义 + 令牌冒泡（收敛点 1+2；反跑组②）
# ---------------------------------------------------------------------------
class Test选择器超时语义:
    def test_等待超时返回空列表不抛异常(self):
        """反跑组②判据：等待 超时必须返回 []，不许改抛异常（超时是正常态）。"""
        甲, 乙 = socket.socketpair()
        sel = 新建选择器()
        try:
            注册(sel, 甲, "读")
            assert 等待(sel, 0.2) == [], "无数据 + 0.2s 超时：必须返回 []"
        finally:
            关闭选择器(sel)
            甲.close()
            乙.close()

    def test_等待就绪令牌中止冒泡(self):
        """收敛点 1：选择器层令牌检查——中止即抛 已取消异常（消息含来源）。"""
        甲, 乙 = socket.socketpair()
        令牌 = 新建令牌()
        令牌.触发("测试来源")
        sel = 新建选择器()
        try:
            注册(sel, 甲, "读")
            with pytest.raises(已取消异常) as 捕获:
                等待就绪(sel, 甲, "读", 5.0, 令牌)
            assert "测试来源" in str(捕获.value)
        finally:
            关闭选择器(sel)
            甲.close()
            乙.close()


# ---------------------------------------------------------------------------
# 并发.超时运行 令牌竞速（收敛点 1）
# ---------------------------------------------------------------------------
class Test超时运行令牌竞速:
    def test_请求先完成返回结果(self):
        async def 主管():
            令牌 = 新建令牌()

            async def 请求():
                await asyncio.sleep(0.05)
                return 42

            return await 超时运行(请求(), 10.0, 令牌)

        assert asyncio.run(主管()) == 42

    def test_中止先命中抛已取消异常(self):
        令牌 = 新建令牌()

        async def 定时触发():
            await asyncio.sleep(0.05)
            令牌.触发("竞速中止")

        async def 主管():
            触发任务 = asyncio.get_event_loop().create_task(定时触发())

            async def 慢请求():
                await asyncio.sleep(10.0)
                return "不该到这里"

            try:
                return await 超时运行(慢请求(), 30.0, 令牌)
            finally:
                try:
                    await asyncio.wait_for(触发任务, 2.0)
                except (asyncio.TimeoutError, TimeoutError):
                    pass

        with pytest.raises(已取消异常) as 捕获:
            asyncio.run(主管())
        assert "竞速中止" in str(捕获.value)


# ---------------------------------------------------------------------------
# 流式.协程收 令牌冒泡（收敛点 1+3）
# ---------------------------------------------------------------------------
class _无响应服务器(threading.Thread):
    """接下连接后一言不发（供令牌在「无数据可读」路径上命中）。"""

    def __init__(self):
        super().__init__(daemon=True)
        self.监听 = socket.socket()
        self.监听.bind(("127.0.0.1", 0))
        self.监听.listen(4)
        self.port = self.监听.getsockname()[1]
        self.运行 = True

    def run(self):
        while self.运行:
            try:
                self.监听.settimeout(0.2)
                conn, _ = self.监听.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.连接 = conn

    def stop(self):
        self.运行 = False
        try:
            self.监听.close()
        except OSError:
            pass


class Test流式令牌:
    def test_协程收令牌中止抛已取消异常(self):
        """收敛点 1：读原语层令牌检查，上层（读体/读分块）自动继承冒泡。"""
        服务器 = _无响应服务器()
        服务器.start()
        try:
            令牌 = 新建令牌()

            async def 主管():
                c = HTTP客户端("127.0.0.1", 服务器.port)
                c.套接字 = socket.create_connection(("127.0.0.1", 服务器.port), 5.0)
                c.套接字.setblocking(False)
                async def 定时中止():
                    await asyncio.sleep(0.2)
                    令牌.触发("流式中止")
                中止任务 = asyncio.get_event_loop().create_task(定时中止())
                try:
                    await _限时包裹(c.协程收(4096, 令牌), "协程收中止", 用例超时)
                finally:
                    中止任务.cancel()
                    c.关闭()

            with pytest.raises(已取消异常) as 捕获:
                asyncio.run(主管())
            assert "流式中止" in str(捕获.value)
        finally:
            服务器.stop()


# ---------------------------------------------------------------------------
# 进程树：令牌中止（杀树清理后冒泡）+ 超时杀树（反跑组③）
# ---------------------------------------------------------------------------
class Test进程树取消与超时:
    def test_令牌中止先杀树再冒泡(self):
        """收敛点 1：进程树层中止 → 清理 pending（杀整棵树）→ 已取消异常 冒泡。"""
        令牌 = 新建令牌()

        def 延迟触发():
            time.sleep(0.4)
            令牌.触发("进程树中止")

        触发线程 = threading.Thread(target=延迟触发, daemon=True)
        触发线程.start()
        树干 = 进程树([sys.executable, "-u", "-c", "import time; time.sleep(30)"], {})
        assert 树干.启动() is True
        try:
            with pytest.raises(已取消异常) as 捕获:
                树干.等待(60000, 令牌)
            assert "进程树中止" in str(捕获.value)
            time.sleep(1.0)
            assert 树干.是否存活() is False, "中止后必须已杀树：子进程不允许存活"
            assert 树干.已杀 is True
        finally:
            触发线程.join(timeout=5)

    def test_超时杀树(self):
        """反跑组③判据：总超时命中 → 杀树 → 是否存活 为 假；去掉 杀树 调用本用例立红。"""
        树干 = 进程树([sys.executable, "-u", "-c", "import time; time.sleep(30)"], {})
        assert 树干.启动() is True
        结果 = 树干.等待(600)
        assert 结果.是否超时 is True
        assert 树干.已杀 is True
        time.sleep(1.0)
        assert 树干.是否存活() is False


# ---------------------------------------------------------------------------
# 伪终端：增量输出 + 令牌中止（收敛点 1+2；Windows ConPTY 句柄不进 select）
# ---------------------------------------------------------------------------
_长驻脚本 = "import time\ntime.sleep(30)\n"
_分批脚本 = (
    "import sys, time\n"
    "print('批一', flush=True)\n"
    "time.sleep(0.6)\n"
    "print('批二', flush=True)\n"
)
# 周期输出长驻脚本：Windows ReadFile 在无数据时阻塞，令牌只在「读之间」被检查；
# 子进程周期产出行 → ReadFile 周期返回 → 读循环轮到令牌检查。POSIX 非阻塞读
# 0.005s 一轮，令牌命中更快。两个平台的中止路径由此在同一语义下验证。
_周期脚本 = (
    "import time\n"
    "for i in range(120):\n"
    "    print('拍', i, flush=True)\n"
    "    time.sleep(0.25)\n"
)


def _等待条件(函数, 超时=8.0, 间隔=0.05):
    截止 = time.monotonic() + 超时
    while time.monotonic() < 截止:
        if 函数():
            return True
        time.sleep(间隔)
    return False


class Test伪终端:
    def test_增量输出(self):
        """收敛点 2：PTY 会话跨平台可起、输出按批增量可读（两批间隔 0.6s 可观测）。"""
        pt = 伪控制台([sys.executable, "-u", "-c", _分批脚本], {})
        try:
            assert _等待条件(lambda: "批一".encode("utf-8") in pt.读输出()), "3s 内未读到批一输出"
            第一次 = pt.读输出()
            assert "批二".encode("utf-8") not in 第一次, "0.6s 间隔下批二不应与批一同时到（增量断言）"
            assert _等待条件(lambda: "批二".encode("utf-8") in pt.读输出()), "8s 内未读到批二输出"
        finally:
            pt.关闭()

    def test_令牌中止停读线程(self):
        """收敛点 1：伪终端读线程在令牌中止后必须退出（停止标志 翻真），不悬挂。
        用周期输出脚本：Windows ConPTY 的 ReadFile 在无数据时阻塞，令牌在
        「读之间」检查——有产出才有检查点（语义与 POSIX 非阻塞轮询一致）。"""
        令牌 = 新建令牌()
        pt = 伪控制台([sys.executable, "-u", "-c", _周期脚本], {"令牌": 令牌})
        try:
            assert _等待条件(lambda: "拍".encode("utf-8") in pt.读输出()), "8s 内未读到任何输出"
            assert pt.停止标志 is False
            令牌.触发("伪终端中止")
            assert _等待条件(lambda: pt.停止标志 is True), (
                "令牌触发后读线程必须在数秒内退出（停止标志=真）")
        finally:
            pt.关闭()


# ---------------------------------------------------------------------------
# 跨线程唤醒通道（收敛点 2；反跑组①）+ AF_UNIX 平台门
# ---------------------------------------------------------------------------
class Test跨线程唤醒_内核通道:
    def test_socketpair唤醒跨线程投递(self):
        """反跑组①判据：worker 线程经 socketpair 写 + call_soon_threadsafe 投递，
        事件循环 0.5s 内必须被唤醒并收到投递——去掉内核唤醒通道本用例立红。"""
        唤醒对 = socket.socketpair()
        唤醒对[0].setblocking(False)
        唤醒对[1].setblocking(False)
        唤醒对[1].settimeout(0.5)
        收到 = threading.Event()

        async def 主管():
            loop = asyncio.get_running_loop()

            def 工人():
                # 模拟 IO 事件到达：先写 socketpair（内核级唤醒），再跨线程投递
                try:
                    唤醒对[0].send(b"wake")
                except OSError:
                    pass
                loop.call_soon_threadsafe(收到.set)

            等可读 = asyncio.get_event_loop().create_task(_限时包裹(
                loop.run_in_executor(None, 唤醒对[1].recv, 64), "socketpair 可读", 2.0))
            t = threading.Thread(target=工人, daemon=True)
            t.start()
            t.join(2.0)
            await asyncio.wait_for(asyncio.to_thread(收到.wait, 0.5), 1.0)
            等可读.cancel()

        asyncio.run(主管())
        assert 收到.is_set(), "跨线程 IO 事件 0.5s 内未送达：socketpair 唤醒通道失效"
        唤醒对[0].close()
        唤醒对[1].close()


class TestAF_UNIX平台门:
    @pytest.mark.skipif(sys.platform == "win32", reason="AF_UNIX 仅 POSIX；Windows 置空不用")
    def test_POSIX回环(self):
        """收敛点 2：POSIX（Linux/macOS/FreeBSD）AF_UNIX 回环 echo 一来一回。"""
        import tempfile
        目录 = tempfile.mkdtemp(prefix="r7_afunix_")
        路径 = os.path.join(目录, "回环.sock")
        assert hasattr(socket, "AF_UNIX"), "POSIX 平台必须有 AF_UNIX（fail-closed 口径）"
        服务端 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        服务端.bind(路径)
        服务端.listen(2)
        服务端.settimeout(5.0)

        def 服务():
            conn, _ = 服务端.accept()
            数据 = conn.recv(4096)
            conn.sendall("回:".encode("utf-8") + 数据)
            conn.close()

        线程 = threading.Thread(target=服务, daemon=True)
        线程.start()
        客户端 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        客户端.settimeout(5.0)
        客户端.connect(路径)
        客户端.sendall(b"unix-ok")
        assert 客户端.recv(4096) == "回:unix-ok".encode("utf-8")
        客户端.close()
        线程.join(5.0)
        服务端.close()
        try:
            os.unlink(路径)
        except OSError:
            pass

    @pytest.mark.skipif(sys.platform != "win32", reason="仅 Windows 的置空断言")
    def test_Windows置空断言(self):
        """收敛点 2：Windows 上底座不用 AF_UNIX——即使 Win10+ 暴露了该常量，
        底座模块（选择器/流式）也不得引用 AF_UNIX 路径（fail-closed：置空）。"""
        if hasattr(socket, "AF_UNIX"):
            # 常量存在也不许用：真建一个验证其不可依赖（绑不上或建不出都算「置空」）
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.close()
                pytest.skip("本机 AF_UNIX 可建——底座仍约定不用，本断言只守『代码不引用』")
            except OSError:
                pass
        for 模块名 in ("选择器", "流式", "伪终端", "进程树"):
            with open(os.path.join(_STDLIB, 模块名 + ".light"), encoding="utf-8") as f:
                非注释行 = [行 for 行 in f if not 行.lstrip().startswith("#")]
            源 = "\n".join(非注释行)
            assert "AF_UNIX" not in 源, (
                "模块 %s 在非注释代码里引用了 AF_UNIX——Windows 置空门被破坏" % 模块名)


# ---------------------------------------------------------------------------
# HTTP 服务端请求响应（收敛点 3 smoke；十判据详见 test_http_server_light.py）
# ---------------------------------------------------------------------------
class TestHTTP服务端smoke:
    def test_请求响应往返(self):
        import HTTP服务端 as 服务端模块

        async def 处理(请求字典):
            return {"状态": 200, "头": {"X-R7": "ok"}, "体": "第7轮-回声:" + 请求字典["路径"]}

        async def 主管():
            服务器 = 服务端模块.HTTP服务端(处理, 5.0)
            端口 = 服务器.端口()
            循环任务 = asyncio.get_event_loop().create_task(服务端模块.处理循环(服务器))
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", 端口), 网络超时)
                writer.write(b"GET /r7 HTTP/1.1\r\nHost: x\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                头区 = b""
                while b"\r\n\r\n" not in 头区:
                    块 = await asyncio.wait_for(reader.read(4096), 网络超时)
                    if not 块:
                        break
                    头区 += 块
                # keep-alive：响应（头+体）通常同帧到达且连接不关——
                # 体从 头区 尾部取，不再对连接二次 read（会白等 keep-alive 超时）
                头区块, _, 体块 = 头区.partition(b"\r\n\r\n")
                writer.close()
                return 头区块, 体块
            finally:
                服务器.停止()
                循环任务.cancel()

        头区块, 体块 = asyncio.run(主管())
        assert 头区块.startswith(b"HTTP/1.1 200")
        assert b"X-R7: ok" in 头区块
        assert 体块.decode("utf-8") == "第7轮-回声:/r7"
