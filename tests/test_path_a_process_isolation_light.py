# -*- coding: utf-8 -*-
"""
test_path_a_process_isolation_light.py —— E9-S2 收口：Path A 进程隔离 SIGKILL 锚点

协作式 限时等待（超时运行=wait_for）只能取消 await，掐不掉已起跑的同步阻塞。
Path A 把危险操作放进独立子进程，超时后由 进程树 硬杀整棵树（POSIX SIGKILL /
Windows taskkill /F /T）。本测试锚定「超时真杀」：跨平台同跑（FreeBSD CI + Windows）。

关于 Windows 本机启动延迟的关键修正（2026-08-26 实测）：
  `python -c ...` 在本机冷启动约需 ~1.4s（解释器加载 site 等）。若把 超时秒
  设成 0.2、命令只睡 0.3，则 0.2s 超时在解释器尚未起完时就触发 杀树，taskkill
  打到进程瞬态上返回 rc=255（未能终止），命令随后跑完写出 DONE → 误判「未真杀」。
  本测试改用「长睡 + 大于启动耗时的超时」：超时 3.0s、命令睡 8s，保证超时触发时
  子进程已完全进入 sleep 且仍存活，taskkill 才能稳定命中（已实测 rc=0 真杀）。
  如需反跑假杀，把 超时秒 调到 > 命令时长即可（见 test_不过杀_命令正常完成并写DONE）。
"""
import asyncio
import os
import sys
import tempfile
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
_根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_根目录, "examples", "harness")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
if _HARNESS not in sys.path:
    sys.path.insert(0, _HARNESS)
import _light_import_hook
_light_import_hook.install([_STDLIB, _HARNESS])

from 编排 import 限时运行进程


def _唯一出口标记():
    # 每个用例独立文件名，避免上一轮遗留文件导致假阳性
    戳 = int(time.time() * 1000)
    return os.path.join(tempfile.gettempdir(), "patha_done_%d_%d.txt" % (os.getpid(), 戳))


def test_限时运行进程_超时硬杀挂起命令():
    # 长睡(8s) + 超时(3.0s)：超时触发时子进程已完全进 sleep 且存活，
    # taskkill /F /T 稳定命中 → 进程被真杀，DONE 永不被写。
    出口标记 = _唯一出口标记()
    assert not os.path.exists(出口标记), "前置：出口标记不应存在"
    命令 = [sys.executable, "-c",
            "import time,os; time.sleep(8); open(%r,'w').write('DONE')" % 出口标记]
    结果 = asyncio.run(限时运行进程(命令, 3.0))
    assert 结果.是否超时 is True, "超时未触发硬杀（是否超时 应为真）"
    # 关键证据：进程被真 SIGKILL，DONE 永不被写（若没真杀，8s 后命令写完 → 文件存在 → 本条红）
    assert not os.path.exists(出口标记), "进程未被真 SIGKILL：DONE 已写出"


def test_限时运行进程_未超时正常返回():
    # 轻量命令：stdout 直接打出 hello-path-a，超时给足 5.0s（>> 1.4s 启动耗时）→ 正常完成
    命令 = [sys.executable, "-c", "import sys; sys.stdout.write('hello-path-a')"]
    结果 = asyncio.run(限时运行进程(命令, 5.0))
    assert 结果.是否超时 is False, "足够长的超时不应触发超时"
    assert "hello-path-a" in 结果.标准输出, "正常命令应输出被采集"


def test_限时运行进程_不过杀_命令正常完成并写DONE():
    # 阳性对照（反跑安全网）：同样会写 DONE 的命令，给足超时使其正常跑完。
    # 若 harness 在「未超时」时也误杀，本条会红 —— 证明 harness 只真杀真超时。
    出口标记 = _唯一出口标记()
    命令 = [sys.executable, "-c",
            "import time,os; time.sleep(0.3); open(%r,'w').write('DONE')" % 出口标记]
    结果 = asyncio.run(限时运行进程(命令, 5.0))
    assert 结果.是否超时 is False, "超时给足时不应触发硬杀"
    assert os.path.exists(出口标记), "未超时情况下命令应正常跑完并写出 DONE（否则 harness 误杀）"
    assert "DONE" == open(出口标记, "r").read(), "出口标记内容应为 DONE"
