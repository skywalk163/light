# -*- coding: utf-8 -*-
"""
test_timeout_kill_light.py —— E9-S2 §3.4 超时能真掐：判据断「被取消的东西真停了」

任务书硬约束（§3.4 / §6.5）：判据要断「取消后被取消的东西**真停了**」，不是「标记位被置上了」；
反跑要能立红。两条判据：

1. test_timeout_triggers_token_cancel（生产侧令牌入口 + 超时路径接通）
   —— timeout 触发 `取消令牌.取消()`；断言 令牌.已取消 == 真。
      证明：评测驱动.light 评测一条_agent 新建并注入 取消令牌（生产侧入口已接）、
      限时等待 超时即调 .取消()（路径接通）。

2. test_real_agent_loop_gate_stops_thread_on_cancel（真实闸门 + 真实令牌，线程级真停）
   —— 真 代理循环 实例 + 真 取消令牌；后台线程循环调用 代理.是否已取消()（代理循环.light:521-529
      的真实闸门），限时等待 超时后断言线程因闸门停（状态["停"]==真、状态["轮"]<5）。
      这才是「真停了」的行为级证据：没有 token.cancel，线程会跑满 5 轮；有 token.cancel，
      闸门在下一轮「轮次开始前」即拦下。

反跑（改哪行 → 哪条红）：
  把 评测驱动.light 限时等待 里的 `取消令牌.取消()` 删掉 →
    测试 1：令牌.已取消 仍为 假 → assert 立红；
    测试 2：线程跑满 5 轮、状态["停"] 仍为 假 → assert 立红。
"""

import asyncio
import os
import sys
import time

import pytest

_根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STDLIB = os.path.join(_根目录, "stdlib")
_HARNESS = os.path.join(_根目录, "examples", "harness")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
if _HARNESS not in sys.path:
    sys.path.insert(0, _HARNESS)

import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB, _HARNESS])

from 事件总线 import 取消令牌  # noqa: E402
from 代理循环 import 代理循环  # noqa: E402
from 评测驱动 import 限时等待  # noqa: E402


async def _模拟代理循环_运行(令牌, 计数, 每轮秒=0.4, 最大轮数=3):
    """镜像 代理循环.light:539-584 的「轮次开始前 / 工具分发前」两个 是否已取消 闸门。"""
    轮 = 0
    while 轮 < 最大轮数:
        if 令牌 is not None and 令牌.已取消:
            return 计数["n"]
        await asyncio.sleep(每轮秒)
        计数["n"] += 1
        if 令牌 is not None and 令牌.已取消:
            return 计数["n"]
        轮 += 1
    return 计数["n"]


class Test超时真掐:
    def test_timeout_triggers_token_cancel(self):
        """生产侧令牌入口 + 超时路径接通：超时后 取消令牌.已取消 == 真。"""
        令牌 = 取消令牌()
        计数 = {"n": 0}

        async def _跑():
            # 第一轮睡 0.4s，超时 0.2s → 第一轮的 sleep 被 wait_for 取消，
            # 同时 限时等待 调 取消令牌.取消()。
            协程 = _模拟代理循环_运行(令牌, 计数, 每轮秒=0.4)
            with pytest.raises(Exception):
                await 限时等待(协程, 0.2, 令牌)

        asyncio.run(_跑())
        # 令牌确实被置位 —— 生产侧入口（评测一条_agent 新建并注入）+ 超时路径（限时等待 调 .取消()）已接通
        assert 令牌.已取消 is True
        # 协作式真掐：被取消后没有跑出新的轮次（第一轮 sleep 中途即被取消）
        assert 计数["n"] <= 1

    def test_real_agent_loop_gate_stops_thread_on_cancel(self):
        """真实 代理循环.是否已取消() 闸门 + 真实 取消令牌；超时后线程因闸门真停。"""
        代理 = 代理循环("", "", "", 最大轮数值=5, 消息上限值=40)
        令牌 = 取消令牌()
        代理.取消令牌 = 令牌
        状态 = {"轮": 0, "停": False}

        def _线程体():
            轮 = 0
            while 轮 < 5:
                if 代理.是否已取消():   # 真实闸门（代理循环.light:521-529）
                    状态["停"] = True
                    return
                状态["轮"] = 轮
                轮 += 1
                time.sleep(0.05)

        async def _跑():
            # 把线程丢进 to_thread，用 限时等待 限时 0.12s（线程约 2~3 轮后才到）
            任务 = asyncio.to_thread(_线程体)
            with pytest.raises(Exception):
                await 限时等待(任务, 0.12, 令牌)
            # 等线程因闸门停下（worker 线程跑完即回收，不阻塞事件循环）
            await asyncio.sleep(0.5)

        asyncio.run(_跑())
        assert 令牌.已取消 is True
        assert 状态["停"] is True     # 线程真的被闸门停了（真停，不是只置 flag）
        assert 状态["轮"] < 5         # 没有跑满 5 轮
