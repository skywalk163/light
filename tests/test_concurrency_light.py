# -*- coding: utf-8 -*-
"""
test_concurrency_light.py —— 并发编排原语行为判据（C5）

覆盖 M13：
- C5-1 `异步信号量(初值)`：并发 N 路实际同时通过数 ≤ 初值，用共享计数器证明；事件循环可继续运转
- C5-2 `速率限制(每秒次数)`：同样时间窗口内放行次数 ≤ 上限（时序可证）
- C5-3 `任务池(并发上限)`：M 任务、最多 N 路并行、全部收拢且顺序 = 提交顺序
- C5-4 `限时(秒)`：超时中断不卡死事件循环（超时后事件循环仍能跑新任务）
- C5-5 `先到先得`：竞速取首个完成（返回最先完成的那个，而不是输入顺序的第一个）

反跑改坏点分别贴在对应用例 docstring；全部用真实行为（共享计数器峰值 / 时序 /
返回值 / 是否抛出超时异常）判定，不断字符串、不上界断。
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

from 并发 import (
    任务池,
    异步信号量,
    信号量获取,
    信号量释放,
    速率限制,
    等待令牌,
    先到先得,
    超时运行,
)
from 重试 import 重试


# ---------------------------------------------------------------------------
# C5-1 异步信号量：共享计数器证明并发上限
# ---------------------------------------------------------------------------
class TestSemaphoreLimit:
    def _run_with_semaphore(self, 初值):
        计数器 = {"当前": 0, "峰值": 0}

        async def 工人(n):
            计数器["当前"] += 1
            if 计数器["当前"] > 计数器["峰值"]:
                计数器["峰值"] = 计数器["当前"]
            await asyncio.sleep(0.05)
            计数器["当前"] -= 1
            return n

        async def 主管():
            s = 异步信号量(初值)
            await asyncio.gather(*(受控(s, 工人, i) for i in range(6)))

        async def 受控(s, 工人, i):
            await 信号量获取(s)
            try:
                return await 工人(i)
            finally:
                信号量释放(s)

        asyncio.run(主管())
        return 计数器["峰值"]

    def test_semaphore_limits_peak_concurrency(self):
        # 反跑改坏点：去掉 信号量获取/释放 → 峰值逼近 6（>2）→ 本条红
        峰值 = self._run_with_semaphore(2)
        assert 峰值 <= 2, f"信号量(2) 下 6 路并发峰值应为 ≤2，实际 {峰值}"

    def test_semaphore_actually_limits_when_pressure_high(self):
        # 证明它确实在限流（而非碰巧没并发）：6 路都 sleep，无限制时峰值必为 6
        峰值 = self._run_with_semaphore(2)
        assert 峰值 == 2, f"信号量(2) 下 6 路带 sleep 的任务峰值应恰为 2，实际 {峰值}"

    def test_semaphore_loop_still_alive_after_contention(self):
        # 信号量等待不阻塞事件循环：竞争期间另一无关协程仍能按期完成
        done = []

        async def 秒表(等待秒):
            await asyncio.sleep(等待秒)
            done.append(等待秒)

        async def 主管():
            s = 异步信号量(1)
            时钟任务 = asyncio.ensure_future(秒表(0.05))
            # 抢信号量耗掉 0.3s，期间时钟任务应早已跑完
            await 信号量获取(s)
            await asyncio.sleep(0.3)
            信号量释放(s)
            await 时钟任务

        asyncio.run(主管())
        # 时钟任务在等待区还锁着时已自行完成 —— 事件循环未被信号量等待卡住
        assert done == [0.05]


# ---------------------------------------------------------------------------
# C5-2 速率限制：时序可证
# ---------------------------------------------------------------------------
class TestRateLimiter:
    def test_three_tokens_paced_over_two_intervals(self):
        # 每秒 10 次 → 间隔 0.1s，取 3 个令牌耗时约 ≥2*0.1=0.2s
        # 反跑改坏点：把节流改成直接放行 → 耗时趋近 0 → 本条红
        限制器 = 速率限制(10)
        t0 = time.monotonic()

        async def 取令牌():
            await 等待令牌(限制器)

        asyncio.run(取令牌())
        asyncio.run(取令牌())
        asyncio.run(取令牌())
        耗时 = time.monotonic() - t0
        assert 耗时 >= 0.18, f"10/s 取 3 令牌应耗 ≥0.18s（需 2 个间隔），实际 {耗时:.3f}s"

    def test_first_token_is_immediate(self):
        # 首个令牌不加间隔（上次放行=0，目标<=现在），立即放行
        限制器 = 速率限制(1)
        t0 = time.monotonic()
        asyncio.run(等待令牌(限制器))
        assert time.monotonic() - t0 < 0.05


# ---------------------------------------------------------------------------
# C5-3 任务池：顺序 + 并发上限
# ---------------------------------------------------------------------------
class TestTaskPool:
    def test_results_in_submission_order(self):
        def 造任务(i):
            async def 干():
                await asyncio.sleep(0.001 * i)
                return i * 10
            return 干

        async def 主管():
            return await 任务池([造任务(0), 造任务(1), 造任务(2)], 2)

        assert asyncio.run(主管()) == [0, 10, 20]

    def test_pool_respects_concurrency_cap(self):
        # 反跑改坏点：任务池不装信号量 → 峰值冲到任务总数 → 红
        计数器 = {"当前": 0, "峰值": 0}

        def 造干(n):
            async def 干():
                计数器["当前"] += 1
                if 计数器["当前"] > 计数器["峰值"]:
                    计数器["峰值"] = 计数器["当前"]
                await asyncio.sleep(0.03)
                计数器["当前"] -= 1
                return n
            return 干

        async def 主管():
            return await 任务池([造干(i) for i in range(4)], 2)

        asyncio.run(主管())
        assert 计数器["峰值"] <= 2, f"任务池(2) 下 4 任务并发峰值应 ≤2，实际 {计数器['峰值']}"


# ---------------------------------------------------------------------------
# C5-4 限时 / C5-5 先到先得
# ---------------------------------------------------------------------------
class TestBoundedAndRace:
    def test_timeout_raises_and_loop_not_dead(self):
        # 反跑改坏点：取消超时 → 永远睡下去 → 本条饿死（红/挂起）
        async def 永不完成():
            await asyncio.sleep(30)

        async def 主管():
            结果 = {}
            try:
                await 超时运行(永不完成(), 0.1)
                结果["抛"] = False
            except Exception:
                结果["抛"] = True
            # 超时后事件循环仍活着：还能跑一个 0.02s 的新任务
            结果["还活着"] = await 超时运行(asyncio.sleep(0.02), 1.0)
            return 结果

        结果 = asyncio.run(主管())
        assert 结果["抛"] is True, "永不完成的协程被限时 0.1s 后应抛超时异常"
        assert 结果["还活着"] is None, "超时返回后事件循环仍能调度新任务"

    def test_timeout_elapsed_is_bounded(self):
        async def 永不完成():
            await asyncio.sleep(30)

        async def 主管():
            t0 = time.monotonic()
            try:
                await 超时运行(永不完成(), 0.1)
            except Exception:
                pass
            return time.monotonic() - t0

        耗时 = asyncio.run(主管())
        assert 0.05 <= 耗时 < 1.0, f"限时 0.1s 应在此附近返回，实际 {耗时:.3f}s"

    def test_first_completed_wins(self):
        # 反跑改坏点：改成取输入顺序第一个 → 返回"慢" → 红
        async def 慢():
            await asyncio.sleep(0.3)
            return "慢"

        async def 快():
            await asyncio.sleep(0.01)
            return "快"

        async def 主管():
            return await 先到先得([慢(), 快()])

        assert asyncio.run(主管()) == "快", "先到先得 应返回最先完成（快）的任务结果"


# ---------------------------------------------------------------------------
# C5-6 重试：可重试次数 / 不可重试即败（计数器断调用次数）
# ---------------------------------------------------------------------------
class TestRetry:
    def test_retriable_success_after_retries(self):
        # 反跑改坏点：把 重试 改成不循环（只调一次）→ 第 1 次抛错 → 红
        计数器 = {"n": 0}

        async def 先败后成():
            计数器["n"] += 1
            if 计数器["n"] < 3:
                raise ValueError("再试一次")
            return "成功"

        async def 主管():
            return await 重试(先败后成, 5, [ValueError], 0.001, 0.05)

        assert asyncio.run(主管()) == "成功"
        assert 计数器["n"] == 3, f"可重试错误应重试到第 3 次成功，实际调用 {计数器['n']} 次"

    def test_non_retriable_fails_immediately(self):
        # 不可重试错误类型（不在可重试列表）必须立刻抛，不重试
        # 反跑改坏点：让 重试 元视所有错误都可重试 → 这里会重试 → 调用次数 > 1 → 红
        计数器 = {"n": 0}

        async def 抛关键错误():
            计数器["n"] += 1
            raise KeyError("不该重试")

        async def 主管():
            try:
                await 重试(抛关键错误, 5, [ValueError], 0.001, 0.05)
                return "未抛出"
            except KeyError:
                return "KeyError-抛出"

        assert asyncio.run(主管()) == "KeyError-抛出"
        assert 计数器["n"] == 1, f"不可重试错误应立即失败只调 1 次，实际 {计数器['n']} 次"

    def test_retries_exhausted_raises(self):
        # 超过重试次数后抛出最后一次异常
        # 反跑改坏点：把上限判断去掉 → 无限重试或永不抛 → 红/挂起
        计数器 = {"n": 0}

        async def 一直失败():
            计数器["n"] += 1
            raise ValueError("永不成功")

        async def 主管():
            try:
                await 重试(一直失败, 3, [ValueError], 0.001, 0.05)
                return "成功"
            except ValueError:
                return f"耗尽:{计数器['n']}"

        assert asyncio.run(主管()) == "耗尽:3", f"重试 3 次应耗尽并抛错，实际 {计数器['n']}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))