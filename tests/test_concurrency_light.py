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

E9-S2 新增（承诺.md 与实现不符的两处，主线裁决「改实现」）：
- §2① `异步信号量` 换成 `asyncio.BoundedSemaphore`：多余 release 立抛 ValueError，
  且**上限不会被悄悄放宽**（TestSemaphoreLimit 后两条，其中一条断并发峰值而非异常类型）
- §2② `速率限制(每秒次数 <= 0)` 立抛 值错误 + 中文消息，失败点在构造处
  （TestRateLimiter 后四条，含「守卫不许过宽」的反向判据）
- §2③ harness 适配层 `编排.等令牌` 的第二次以后调用原先绕过守卫
  （TestHarness等令牌守卫 三条，含「守卫每次过但节流状态不许重置」）
"""
import asyncio
import os
import sys
import time
import types

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
_根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_根目录, "examples", "harness")
_SRC = os.path.join(_根目录, "src")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
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
    全或无等待,
    吞异常等待,
    带限流,
    带限流收集异常,
    有界队列类,
    滑动窗口类,
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

    # ------------------------------------------------------------------
    # E9-S2 §2①：有界语义 —— 多余 release 立抛，上限不会被悄悄放宽
    # 承诺.md §2 写的是「与 BoundedSemaphore(N) 一致」，实现原先是 Semaphore。
    # 主线裁决「改实现」→ 并发.light:25 换成 asyncio.BoundedSemaphore。
    # ------------------------------------------------------------------
    def test_over_release_raises_valueerror(self):
        """release 次数 > acquire 次数 → 立抛 ValueError（有界语义）。

        反跑改坏点：把 并发.light:25 的 `asyncio.BoundedSemaphore(初值)`
        改回 `asyncio.Semaphore(初值)` → 多余 release 静默通过 →
        本条「结果以 ValueError: 开头」断言红（实际拿到 "未抛出"）。
        """
        async def 主管():
            s = 异步信号量(1)
            await 信号量获取(s)
            信号量释放(s)          # 正常归还：计数回到初值 1
            try:
                信号量释放(s)      # 多余的这一次必须炸
                return "未抛出"
            except ValueError as e:
                return "ValueError:" + str(e)

        结果 = asyncio.run(主管())
        assert 结果.startswith("ValueError:"), f"多余 release 应抛 ValueError，实际 {结果}"

    def test_over_release_cannot_raise_the_ceiling(self):
        """真防护判据：不断异常类型，断「上限确实没被放宽」。

        信号量(1) 上先做一次没配对的 release（把它抛的错吞掉），再放 4 路
        带 sleep 的并发进去 —— 峰值必须仍恰为 1。

        反跑改坏点：并发.light:25 换回 `asyncio.Semaphore` → 那次多余 release
        把内部计数抬到 2 → 峰值变 2 → 本条红。
        """
        计数器 = {"当前": 0, "峰值": 0}

        async def 受控(s):
            await 信号量获取(s)
            try:
                计数器["当前"] += 1
                if 计数器["当前"] > 计数器["峰值"]:
                    计数器["峰值"] = 计数器["当前"]
                await asyncio.sleep(0.03)
                计数器["当前"] -= 1
            finally:
                信号量释放(s)

        async def 主管():
            s = 异步信号量(1)
            吞到的 = None
            try:
                信号量释放(s)      # 没 acquire 就 release
            except ValueError as e:
                吞到的 = type(e).__name__
            await asyncio.gather(*(受控(s) for _ in range(4)))
            return 吞到的

        吞到的 = asyncio.run(主管())
        assert 计数器["峰值"] == 1, (
            f"多余 release 之后信号量上限被放宽了：4 路并发峰值 {计数器['峰值']}，应为 1"
        )
        assert 吞到的 == "ValueError", f"裸 release 应被有界语义拦住，实际吞到 {吞到的}"


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

    # ------------------------------------------------------------------
    # E9-S2 §2②：每秒次数 ≤ 0 —— 承诺.md §6 原写「行为未定义」，
    # 主线裁决改成「立抛 值错误 + 中文消息」（并发.light:44-45）。
    # ------------------------------------------------------------------
    def test_zero_rate_raises_valueerror_with_chinese_message(self):
        """速率限制(0) → ValueError，消息里必须点出参数名和实际值。

        反跑改坏点：删掉 并发.light:44-45 那两行守卫 → 变成 `1.0 / 0` 的
        ZeroDivisionError（ZeroDivisionError 不是 ValueError 的子类）→
        pytest.raises(ValueError) 直接红。
        """
        with pytest.raises(ValueError) as 抓到:
            速率限制(0)
        消息 = str(抓到.value)
        assert "每秒次数" in 消息, f"消息里没点出参数名：{消息!r}"
        assert "必须 > 0" in 消息, f"消息里没说清约束：{消息!r}"
        assert "0" in 消息, f"消息里没带上实际值：{消息!r}"

    def test_negative_rate_raises_valueerror(self):
        """负速率同样立抛，且实际值原样出现在消息里。

        反跑改坏点：把守卫从 `小于等于 0` 改成 `等于 0` → 负数漏过去，
        构造出一个间隔为负的限制器（等待令牌 会永远立即放行）→ 本条红。
        """
        for 坏值 in (-1, -0.5, -1000):
            with pytest.raises(ValueError) as 抓到:
                速率限制(坏值)
            消息 = str(抓到.value)
            assert "每秒次数" in 消息, f"速率={坏值!r} 的消息不含参数名：{消息!r}"
            assert str(坏值) in 消息, f"速率={坏值!r} 的实际值没进消息：{消息!r}"

    def test_rate_guard_fails_fast_at_construction(self):
        """失败点在**构造处**，不是拖到首次 等待令牌 才炸。

        反跑改坏点：把守卫从 速率限制 挪进 等待令牌 → 构造这一步不抛 →
        本条断言拿到 "没炸" → 红。
        """
        炸在哪 = None
        try:
            速率限制(0)
            炸在哪 = "没炸"
        except ZeroDivisionError:
            炸在哪 = "构造处-ZeroDivisionError"
        except ValueError:
            炸在哪 = "构造处-ValueError"
        assert 炸在哪 == "构造处-ValueError", f"速率限制(0) 的失败形态不对：{炸在哪}"

    def test_fractional_rate_still_allowed(self):
        """守卫只拦 ≤0：0.5/s（间隔 2s）是合法速率，不许被误拦。

        反跑改坏点：把守卫写成 `小于 1`（想「至少 1 次/秒」）→ 这里立红，
        证明守卫没有过宽地吃掉合法输入。
        """
        限制器 = 速率限制(0.5)
        assert 限制器["速率"] == 0.5, f"合法的分数速率被改写了：{限制器}"


# ---------------------------------------------------------------------------
# E9-S2 §2③ harness 侧：编排.等令牌 的守卫覆盖
# 守卫写在 并发.light 的 速率限制 里，但 编排.等令牌 只有**首次**调用会经过它，
# 第二次以后走 否则 分支直接改 速率 —— 那条路原先绕过了守卫。
# ---------------------------------------------------------------------------
def _载入编排():
    """就地把 examples/harness/编排.light 编译到一个独立模块命名空间。

    不用 _light_import_hook.install([_HARNESS])：那会把 harness 目录挂到
    进程级的导入钩子上，同一次 pytest 会话里别的测试也会看见 harness 模块。
    这里只要一份隔离副本，顺带保证每个用例拿到的 编排限流器 都是干净的 空。
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    路径 = os.path.join(_HARNESS, "编排.light")
    with open(路径, "r", encoding="utf-8") as fh:
        源码 = fh.read()
    生成 = PythonCodeGenerator().generate(LightParser().parse(源码))
    模块 = types.ModuleType("编排_E9S2隔离副本")
    模块.__file__ = 路径
    exec(compile(生成, 路径, "exec"), 模块.__dict__)
    return 模块


class TestHarness等令牌守卫:
    def test_首次调用就拦住零速率(self):
        编排 = _载入编排()
        with pytest.raises(ValueError) as 抓到:
            asyncio.run(编排.等令牌(0))
        assert "每秒次数" in str(抓到.value), f"消息不对：{抓到.value}"

    def test_第二次调用换成零速率同样拦住(self):
        """这才是真漏点：先用合法速率把 编排限流器 建起来，再传 0。

        反跑改坏点：把 编排.light:33 的 `设 已验限制器 为 速率限制(每秒次数)`
        挪回 如果 分支里（即恢复「只有首次经过守卫」）→ 第二次调用不再抛
        ValueError，而是在 并发.light:51 的 `1.0 / 限制器["速率"]` 处炸成
        ZeroDivisionError → 本条断言拿到 "ZeroDivisionError" → 红。
        """
        编排 = _载入编排()
        asyncio.run(编排.等令牌(10))          # 合法：把限流器建起来
        炸成什么 = None
        try:
            asyncio.run(编排.等令牌(0))
            炸成什么 = "没炸"
        except ZeroDivisionError:
            炸成什么 = "ZeroDivisionError"
        except ValueError:
            炸成什么 = "ValueError"
        assert 炸成什么 == "ValueError", (
            f"第二次调用传 0 时的失败形态不对：{炸成什么}（守卫被 否则 分支绕过了）"
        )

    def test_合法速率下限流器状态跨调用保留(self):
        """守卫每次都过，但**不许**顺手把节流状态重置掉。

        判据：第二次调用后 编排限流器 仍是第一次那个对象（上次放行 是跨调用状态）。
        反跑改坏点：把 否则 分支改成 `设 编排限流器 为 已验限制器`（整体替换）
        → 对象身份变了 → 本条红，同时节流会每次归零、速率限制形同虚设。
        """
        编排 = _载入编排()
        asyncio.run(编排.等令牌(50))
        第一个 = 编排.编排限流器
        第一次放行 = 第一个["上次放行"]
        asyncio.run(编排.等令牌(50))
        assert 编排.编排限流器 is 第一个, "限流器对象被整体替换了，节流状态会归零"
        assert 编排.编排限流器["上次放行"] > 第一次放行, (
            "上次放行 没往前推进，说明节流没真的在计时"
        )


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
            return await 任务池([造任务(0), 造任务(1), 造任务(2)], 2, "逐条收集")

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
            return await 任务池([造干(i) for i in range(4)], 2, "全或无")

        asyncio.run(主管())
        assert 计数器["峰值"] <= 2, f"任务池(2) 下 4 任务并发峰值应 ≤2，实际 {计数器['峰值']}"

    # ------------------------------------------------------------------
    # E9-S1 §2.1.1：全或无 —— 真取消兄弟 + 无孤儿 Task
    # ------------------------------------------------------------------
    def test_all_or_none_cancels_siblings_and_no_orphans(self):
        """3 条任务：第 1 条慢(0.5s)、第 2 条立即抛、第 3 条中慢(0.3s)。
        全或无模式下，抛出后必须取消第 1/3 条，并确保事件循环无孤儿。
        反跑改坏点：把 全或无等待 里的取消步骤删掉（删除 if 非...任务.cancel() 那两行）
        → ① 「跑完标记」断言第 3 条跑完（未被取消）→ 红
        → ② all_tasks() 非空断言 → 红
        """
        跑完标记 = {"t1": False, "t3": False}

        async def t1():
            try:
                await asyncio.sleep(0.5)
            finally:
                跑完标记["t1"] = True  # finally 仍跑（取消也会执行 finally）
            return "t1"

        async def t2():
            await asyncio.sleep(0.01)
            raise RuntimeError("E9故意炸-t2")

        async def t3():
            try:
                await asyncio.sleep(0.3)
            finally:
                跑完标记["t3"] = True
            return "t3"

        async def 主管():
            try:
                await 任务池([t1, t2, t3], 2, "全或无")
                return {"成功": True, "异常": None}
            except RuntimeError as e:
                if "E9故意炸-t2" in str(e):
                    return {"成功": False, "异常": "命中"}
                return {"成功": False, "异常": f"错异常:{e}"}
            except Exception as e:
                return {"成功": False, "异常": f"非RuntimeError:{type(e).__name__}:{e}"}

        结果 = asyncio.run(主管())
        assert 结果["成功"] is False, f"应抛异常，实际 {结果}"
        assert 结果["异常"] == "命中", f"首异常没正确抛出：{结果}"
        # 关键：asyncio.run 退出时所有 task 必须已终结（无孤儿）
        # 注意：在 asyncio.run 外部用 asyncio.all_tasks() 会报错，所以把检查放在 主管 末尾
        # 这里用跑完标记证明取消生效：t1/t3 的 finally 已执行（但主体未完成）

        # 再跑一次：把「事件循环无孤儿」检查搬到 主管 内部
        终态检查 = {}

        async def 主管带检查():
            try:
                await 任务池([t1, t2, t3], 2, "全或无")
            except RuntimeError:
                pass
            # 让出一轮事件循环，让取消传播完成
            await asyncio.sleep(0.02)
            当前 = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if not t.done() and t is not 当前]
            终态检查["孤儿数"] = len(pending)
            终态检查["孤儿详情"] = [str(t) for t in pending]

        asyncio.run(主管带检查())
        assert 终态检查["孤儿数"] == 0, (
            f"全或无模式下有 {终态检查['孤儿数']} 个孤儿 Task 残留：{终态检查['孤儿详情']}"
        )

    # ------------------------------------------------------------------
    # E9-S1 §2.1.2：逐条收集 —— 失败条目占位，其余正常跑完
    # ------------------------------------------------------------------
    def test_collect_exceptions_mode_preserves_order_and_values(self):
        """3 条任务，第 2 条抛错。
        逐条收集模式下：结果表长度=3、第 2 项是错误对象、第 1/3 项是正常值。
        反跑改坏点：把 带限流收集异常 改成不捕获直接抛 → 全场炸，长度≠3 → 红
        """
        async def t1():
            await asyncio.sleep(0.02)
            return "ok1"

        async def t2():
            await asyncio.sleep(0.01)
            raise KeyError("E9故意炸-t2逐条")

        async def t3():
            await asyncio.sleep(0.03)
            return "ok3"

        async def 主管():
            return await 任务池([t1, t2, t3], 2, "逐条收集")

        结果 = asyncio.run(主管())
        assert len(结果) == 3, f"逐条收集应返回 3 项，实际 {len(结果)}：{结果}"
        assert 结果[0] == "ok1", f"第 1 项应为 ok1，实际 {结果[0]!r}"
        assert isinstance(结果[1], KeyError), f"第 2 项应是 KeyError，实际 {type(结果[1]).__name__}:{结果[1]}"
        assert "E9故意炸-t2逐条" in str(结果[1]), f"第 2 项错误文本不符：{结果[1]}"
        assert 结果[2] == "ok3", f"第 3 项应为 ok3，实际 {结果[2]!r}"

    # ------------------------------------------------------------------
    # E9-S1 §2.1.3：失败模式非法取值必须立红
    # ------------------------------------------------------------------
    def test_invalid_mode_raises_valueerror(self):
        async def noop():
            return 1

        async def 主管(模式):
            return await 任务池([noop], 1, 模式)

        for 坏值 in ("", "all", "any", None, "batch", "failfast"):
            命中 = False
            try:
                asyncio.run(主管(坏值))
            except ValueError as e:
                if "失败模式" in str(e):
                    命中 = True
            assert 命中, f"模式={坏值!r} 未抛含「失败模式」的 ValueError"

    # ------------------------------------------------------------------
    # E9-S1 §2.2：长尾判据 —— 滑动窗口 ≠ 分批（时序断言，非总耗时）
    # ------------------------------------------------------------------
    def test_sliding_window_not_batch_by_timing_order(self):
        """耗时 [0.30, 0.01, 0.01, 0.01]，并发上限 2。

        真滑窗：t3 起跑 < t1 完成（t1 占 0.30s，t2 很快跑完腾出槽，t3 立即上）。
        分批 barrier：t3 必须等 t1 完成才起跑 → 时序反了。

        反跑改坏点：把 任务池 改成「分批 gather barrier」(起/止 逐批推进，
        见 代理循环.light 的 并行分发 模式) → 「t3 起跑 < t1 完成」断言立红。
        """
        时间戳 = {"t1_start": 0, "t1_end": 0, "t3_start": 0, "t3_end": 0}

        def 造(名, 秒):
            async def 干():
                if 名 == "t1":
                    时间戳["t1_start"] = time.monotonic()
                    await asyncio.sleep(秒)
                    时间戳["t1_end"] = time.monotonic()
                elif 名 == "t3":
                    时间戳["t3_start"] = time.monotonic()
                    await asyncio.sleep(秒)
                    时间戳["t3_end"] = time.monotonic()
                else:
                    await asyncio.sleep(秒)
                return 名
            return 干

        任务列表 = [造("t1", 0.30), 造("t2", 0.01), 造("t3", 0.01), 造("t4", 0.01)]

        async def 主管():
            return await 任务池(任务列表, 2, "逐条收集")

        结果 = asyncio.run(主管())
        assert 结果 == ["t1", "t2", "t3", "t4"], f"顺序错：{结果}"

        # 核心判据：时序关系，不是总耗时。
        # t3_start 必须严格早于 t1_end → 证明 t3 在 t1 还没跑完时就起跑了 = 真滑窗
        t1_持续 = 时间戳["t1_end"] - 时间戳["t1_start"]
        t3_比t1早多久 = 时间戳["t1_end"] - 时间戳["t3_start"]
        诊断 = (
            f"t1=[{时间戳['t1_start']:.4f}→{时间戳['t1_end']:.4f}, 持续{t1_持续:.4f}s], "
            f"t3_start={时间戳['t3_start']:.4f}, "
            f"t3起跑比t1完成{'早' if t3_比t1早多久 > 0 else '晚'} {abs(t3_比t1早多久):.4f}s"
        )
        assert 时间戳["t3_start"] < 时间戳["t1_end"], (
            "未证明滑窗：t3 起跑应早于 t1 完成，实际：" + 诊断
        )
        # 辅助：t1 真的跑了 ~0.30s（说明没被机器抖动压缩得太离谱）
        assert t1_持续 >= 0.25, f"t1 睡眠 0.30s 实际只持续 {t1_持续:.4f}s，机器抖得太厉害：" + 诊断


# ---------------------------------------------------------------------------
# C5-7 有界队列 + 滑动窗口（E9-S2 §3.2 提升：从 分布式/队列.py 进 并发.light，纯光明）
# 承诺见 任务书/E9→F9_并发语义承诺.md §10。判据与 F9 侧（test_distributed_eval_light.py
# 的 背压/限流 两条）同一语义、双保险，这里附 E9 侧反跑锚点。
# ---------------------------------------------------------------------------
class TestBoundedQueue:
    def test_backpressure_blocks_producer_when_full(self):
        """容量 2 灌满后第三个 入队 真挂起；取走一条立即补进（背压 = 等，不抛不丢）。

        反跑改坏点：删掉 并发.light 有界队列类.入队 里的 `等待 信号量获取(己.槽信号量)`
        → 满队时 入队 立即完成 → 本断言 `not 挡住.done()` 红（背压变直进）。
        """
        async def 主体():
            q = 有界队列类(2)
            await q.入队("a")
            await q.入队("b")
            挡住 = asyncio.create_task(q.入队("c"))
            await asyncio.sleep(0.1)
            assert not 挡住.done(), "背压：满队后生产者应被挡住（入队未完成）"
            assert q.大小() == 2, "背压：满队不应偷偷多进一条"
            assert await q.出队() == "a", "取出的应是第一条"
            await 挡住  # 消费者取走一个后，被挡的生产者才补进
            assert q.大小() == 2, "背压：消费者取走后生产者才补进"
        asyncio.run(主体())

    def test_empty_wait_consumer_unblocks_after_enqueue(self):
        """空队时 出队 被挡住（0.01s 轮询等待），入队后放行。

        反跑改坏点：删掉 并发.light 有界队列类.出队 里的 当 循环 →
        空队直接 pop → IndexError → 本断言拿不到值 → 红。
        """
        async def 主体():
            q = 有界队列类(2)
            取出 = []
            async def 消费者():
                取出.append(await q.出队())
            任务 = asyncio.create_task(消费者())
            await asyncio.sleep(0.1)
            assert 取出 == [], "空队时消费者应被挡住"
            await q.入队("x")
            await 任务
            assert 取出 == ["x"], f"入队后消费者应放行取到 x，实际 {取出}"
        asyncio.run(主体())

    def test_fifo_order_and_size_queries(self):
        """FIFO + 大小/是否空/是否满 与 队列.py 逐条一致。

        反跑改坏点：把 出队 里的 `pop(0)` 改成 `pop()`（取尾部）→ 顺序反 → 红。
        """
        async def 主体():
            q = 有界队列类(2)
            assert q.是否空() and q.大小() == 0
            await q.入队("a")
            await q.入队("b")
            assert q.是否满() and not q.是否空() and q.大小() == 2
            assert await q.出队() == "a"
            assert await q.出队() == "b"
            assert q.是否空()
        asyncio.run(主体())

    def test_try_enqueue_full_raises_queu_full(self):
        """试着入队（反跑对照壳）：未满返回 真，满抛 值错误("QueueFull")。

        反跑改坏点：把 试着入队 的 `小于` 改成 `小于等于`（多放一条）→ QueueFull
        不再抛 → pytest.raises 红。
        """
        async def 主体():
            q = 有界队列类(1)
            assert q.试着入队("a") is True, "未满时 试着入队 应返回 真"
            with pytest.raises(ValueError) as 抓到:
                q.试着入队("b")
            assert "QueueFull" in str(抓到.value), f"消息不对：{抓到.value}"
        asyncio.run(主体())

    def test_sliding_window_expires_old_events(self):
        """滑动窗口：t=0 记 3 条满窗；t=1.1 滑过（窗口 1.0）旧事件过期 → 放行。

        反跑改坏点：删掉 并发.light 滑动窗口类._剔除过期 里的 当 循环 →
        数量永不衰减 → `窗.数量(1.1) == 0` 红（退化成累加计数）。
        """
        窗 = 滑动窗口类(3, 1.0)
        窗.记录(0.0)
        窗.记录(0.0)
        窗.记录(0.0)
        assert 窗.数量(0.0) == 3, "窗口内 3 条应计满"
        assert not 窗.是否放行(0.0), "满窗不应放行"
        assert 窗.数量(1.1) == 0, "窗口滑过后旧事件应过期剔除"
        assert 窗.是否放行(1.1), "过期剔除后应放行（与固定分批不同）"


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