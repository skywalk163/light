# -*- coding: utf-8 -*-
"""
test_posix_timeout_light.py —— E9-S2 收口：POSIX 超时真掐路径 实测锚点

§9 已知项「超时真掐 POSIX 强杀路径未实测」分两层：

- 已实现的 Hybrid 协作式闸门（`限时等待` → `超时运行`=wait_for + `取消令牌.取消()`）：
  不依赖 OS 信号，跨平台一致。本测试锚定它的两条支柱原语：
    1) stdlib/并发.light `超时运行`：超时会取消挂起协程、在时限内返回；
    2) stdlib/事件总线.light `取消令牌`：`.取消()` 把 `已取消` 置真、触发注册的处理器。
  该逻辑在 FreeBSD CI runner 上与 Windows 同跑，即构成 POSIX 实测锚点。
- Path A 进程隔离（SIGKILL，针对完全不 await 的死阻塞，如挂死挂载的 `open`）：
  **尚未实现**，属设计 deferred，不在此轮范围，本测试不覆盖（也不伪造）。
"""
import asyncio
import os
import sys
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 并发 import 超时运行
from 事件总线 import 取消令牌


def test_超时运行_在时限内掐断挂起协程():
    # 反跑改坏点：把 超时运行 里的 wait_for 去掉 → 慢协程跑满 5s → 本条红
    async def 慢():
        await asyncio.sleep(5)
    t0 = time.monotonic()
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(超时运行(慢(), 0.1))
    dt = time.monotonic() - t0
    assert dt < 1.0, f"超时未在 ~0.1s 内返回，实际 {dt:.2f}s（Hybrid 协作式真掐失效）"


def test_取消令牌_取消后置已取消并触发处理器():
    # 协作式闸门的入口：超时后 限时等待 调 取消令牌.取消()，下游轮次/工具分发点
    # 查 已取消 即停。本测试锚定这个令牌本身的语义。
    令牌 = 取消令牌()
    assert not 令牌.已取消, "初始应为未取消"
    触发 = []
    令牌.注册取消处理器(lambda: 触发.append(1))
    assert 令牌.取消() is True, "首次 取消() 应返回 真"
    assert 令牌.已取消, "取消后 已取消 应为真（协作式闸门入口）"
    assert 触发 == [1], "注册的处理器应在取消时触发"
    assert 令牌.取消() is False, "重复 取消() 应幂等返回 假（防重复触发）"
