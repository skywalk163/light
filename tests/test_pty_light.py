# -*- coding: utf-8 -*-
"""
任务D2-3：伪终端（纯光明实现）定向测试

覆盖（Windows 实测侧）：
  - ConPTY 能起一个 PTY、跑一条命令、读到带 ANSI 转义的原始输出
  - 能设窗口大小（ResizePseudoConsole 不炸）
  - 写输入路径不崩（写 stdin）
  - 优雅关闭：长驻进程被干净终止，关闭后 是否存活 为假
  - 平台缺失时明确报错（伪控制台错误 类存在，不静默降级管道模式）

进程隔离红线：本文件绝不按进程名杀进程；只对自己 spawn 的 伪控制台 实例
调用 关闭()/TerminateProcess。

skip 掩盖分析（每条 skip 写明掩盖了什么）：
  - Windows 上 skip POSIX 分支用例：掩盖了 openpty/forkpty/setsid/ioctl
    TIOCSWINSZ 这条 POSIX 真机路径从未跑过（本机无 WSL 发行版、无 Docker，
    系统级工具被安全策略禁用）。
  - POSIX 上 skip Windows 分支用例：掩盖了 ConPTY（CreatePseudoConsole +
    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE + STARTUPINFOEXW）路径从未在
    POSIX 上跑过——它只在这台 Windows 上验证过。
"""
import os
import sys
import time

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 伪终端 import 伪控制台, 伪控制台错误

_ANSI脚本 = 'import sys\nprint("\\x1b[31m红\\x1b[0m")\n'
_长驻脚本 = 'import time\ntime.sleep(30)\n'
_回显脚本 = 'import sys\nline = sys.stdin.readline()\nprint("回声:" + line.strip())\n'


def _等待输出(pt, 子串, 超时=8.0):
    """轮询读输出直到包含子串（或超时），返回最终输出。"""
    截止 = time.time() + 超时
    while time.time() < 截止:
        输出 = pt.读输出()
        if 子串 in 输出:
            return 输出
        time.sleep(0.05)
    return pt.读输出()


def _等退出(pt, 超时=8.0):
    截止 = time.time() + 超时
    while time.time() < 截止:
        if not pt.是否存活():
            return True
        time.sleep(0.05)
    return pt.是否存活() is False


# ============================================================
# Windows：ConPTY 实测分支
# ============================================================
class TestWindowsConPTY:
    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="ConPTY 仅 Windows（Win10 1809+）。POSIX 上跳过掩盖了："
               "CreatePseudoConsole/PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE/"
               "STARTUPINFOEXW 路径从未在 POSIX 上跑过。",
    )
    def test_启动命令读到带ANSI的输出(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _ANSI脚本], {})
        try:
            输出 = _等待输出(pt, b"\x1b[31m")
            assert b"\x1b[31m" in 输出, 输出
            assert b"\x1b[0m" in 输出, 输出
            # 命令自然退出后 是否存活 应变假
            assert _等退出(pt), "python 短命令应在数秒内退出"
        finally:
            pt.关闭()

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="ConPTY 仅 Windows。POSIX 上跳过掩盖了：ResizePseudoConsole 路径"
               "从未在 POSIX 上跑过（POSIX 用 ioctl TIOCSWINSZ）。",
    )
    def test_设窗口大小不炸(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _长驻脚本], {})
        try:
            time.sleep(0.8)
            # 反复改尺寸（含常见 80x24 / 120x30），ConPTY 应返回 S_OK
            pt.设窗口大小(80, 24)
            pt.设窗口大小(120, 30)
            pt.设窗口大小(100, 40)
            assert pt.是否存活(), "改尺寸不应把子进程搞死"
        finally:
            pt.关闭()

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="ConPTY 仅 Windows。POSIX 上跳过掩盖了：WriteFile 到 ConPTY 输入"
               "管道（配合 STARTF_USESTDHANDLES）的路径从未在 POSIX 上跑过。",
    )
    def test_写输入不崩(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _回显脚本], {})
        try:
            time.sleep(0.8)
            # 写 stdin：ConPTY 控制台输入按 \r\n 换行
            assert pt.写输入(b"hello\r\n") is True
            输出 = _等待输出(pt, "回声:".encode("gbk", "replace"))
            # 子进程 stdout 是控制台 → 本机 cp936 编码；解码后断言回显
            文本 = 输出.decode("gbk", "replace")
            assert "回声:hello" in 文本, 文本
        finally:
            pt.关闭()

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="ConPTY 仅 Windows。POSIX 上跳过掩盖了：优雅关闭（关输入写端→"
               "宽限→TerminateProcess→ClosePseudoConsole）路径从未在 POSIX 上跑过。",
    )
    def test_优雅关闭长驻进程(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _长驻脚本], {})
        time.sleep(0.8)
        assert pt.是否存活(), "长驻 python 应还活着"
        pt.关闭()
        # 关闭后不再存活（宽限 2s 内 TerminateProcess 兜底）
        assert not pt.是否存活(), "关闭后子进程应已被终止"
        # 幂等：再关一次不炸
        pt.关闭()

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="ConPTY 仅 Windows。POSIX 上跳过掩盖了：平台缺失报错路径只在"
               "Windows 侧定义（伪控制台错误）。",
    )
    def test_平台缺失明确报错类存在(self):
        # 现代 Win10/11 上 CreatePseudoConsole 存在，正常路径不抛；
        # 这里钉住"报错类型存在且可实例化"（旧系统分支见 伪终端.light 注释）
        错误 = 伪控制台错误("本平台需 Win10 1809+")
        assert "1809" in str(错误)


# ============================================================
# POSIX：openpty/forkpty 分支（Windows 上 skip，交 Linux 真机跑）
# ============================================================
class TestPOSIXOpenPTY:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="本机无 WSL/Docker（系统级工具被安全策略禁用），openpty/forkpty/"
               "setsid 真机路径从未跑过。此用例在 POSIX 上验证：起 PTY、跑命令、"
               "读 ANSI 输出、自然退出。",
    )
    def test_启动命令读到带ANSI的输出(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _ANSI脚本], {})
        try:
            输出 = _等待输出(pt, b"\x1b[31m")
            assert b"\x1b[31m" in 输出, 输出
            assert b"\x1b[0m" in 输出, 输出
            assert _等退出(pt)
        finally:
            pt.关闭()

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="本机无 WSL/Docker，ioctl(TIOCSWINSZ) 设窗口路径从未实测。"
               "此用例在 POSIX 上验证：设窗口大小不炸、子进程不被搞死。",
    )
    def test_设窗口大小不炸(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _长驻脚本], {})
        try:
            time.sleep(0.8)
            pt.设窗口大小(80, 24)
            pt.设窗口大小(120, 30)
            assert pt.是否存活()
        finally:
            pt.关闭()

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="本机无 WSL/Docker，POSIX 优雅关闭（关 master→宽限→SIGTERM→"
               "SIGKILL）从未实测。此用例在 POSIX 上验证：长驻子进程被干净终止。",
    )
    def test_优雅关闭长驻进程(self):
        pt = 伪控制台([sys.executable, "-u", "-c", _长驻脚本], {})
        time.sleep(0.8)
        assert pt.是否存活()
        pt.关闭()
        assert not pt.是否存活(), "关闭后子进程应已被终止"
        pt.关闭()  # 幂等
