# -*- coding: utf-8 -*-
"""分布式 S2 的队列原语（Python 边界，被光明包装）。

为什么在 分布式/ 下自己实现，而不是改 stdlib/并发.light：
  外发任务_分布式S2.md §7.2 裁决——背压满了 = 等（阻塞生产者），不是抛；且 F9 **不许改
  stdlib/并发.light**（改需求走 E9 移交）。全仓唯一带容量上界的原语是
  stdlib/线程.py:257 线程安全队列（queue.Queue，同步），没有异步有界队列。
  所以这里在 分布式/ 下实现最小有界异步队列 + 滑动窗口限流，二者都只借 Python 标准库，
  对上是中文函数名；本文件不被 tools/ci/python_direct_calls.py 扫描（只扫 .light）。

背压语义（§7.2）：有界队列满时 入队 用 `await put` 阻塞生产者，把上游速率压下来——
  不是抛异常（抛等于把背压变成丢条，与「无静默丢条」冲突）。反跑见
  tests/test_distributed_eval_light.py:test_背压_满后生产者被挡住。
限流语义：滑动窗口 = 滚动时间窗（旧事件过期滑出），与「分批计数」（固定窗口/批次）可区分——
  见 §限流 判据与 tests/test_distributed_eval_light.py:test_限流_滑动窗口与分批不同。
"""
import asyncio
import time


class 有界队列类:
    """最小有界异步队列：满时 入队 阻塞生产者（背压 = 等）。

    底层 asyncio.Queue(maxsize=容量)；`await put` 在满时挂起直到有空位，
    这正是判据要的「灌满之后生产者真被挡住」。
    """

    def __init__(self, 容量):
        self.容量 = 容量
        self._队列 = asyncio.Queue(maxsize=容量)

    async def 入队(self, 项):
        # 满则阻塞生产者（背压语义）。反跑：把这一行换成 self._队列.put_nowait(项)
        # → 满时抛 QueueFull，tests 里「生产者被挡住」的断言立红。
        await self._队列.put(项)

    def 试着入队(self, 项):
        # 非阻塞对照：满则抛 asyncio.QueueFull（仅供反跑对照，正常路径不用）。
        self._队列.put_nowait(项)

    async def 出队(self):
        return await self._队列.get()

    def 大小(self):
        return self._队列.qsize()

    def 是否满(self):
        return self._队列.full()

    def 是否空(self):
        return self._队列.empty()


class 滑动窗口类:
    """滑动窗口限流：在最近 窗口秒 内的事件数不超过 上限。

    与「分批」的本质区别：分批是「每批 N 个、批满即停、下一批重新计数」，
    旧事件不会因时间流逝而滑出；滑动窗口是滚动的——超过窗口的旧事件过期剔除，
    因此「窗口滑过后又能放行新事件」。判据要能区分二者，见 test_限流_滑动窗口与分批不同。
    """

    def __init__(self, 上限, 窗口秒):
        self.上限 = 上限
        self.窗口 = 窗口秒
        self.事件 = []

    def _剔除过期(self, 现在):
        # 反跑：删掉这个循环 → 事件只增不减，数量永不衰减，限流退化为累加计数，
        # test_限流 里「窗口滑过应放行」的断言立红。
        下限 = 现在 - self.窗口
        while self.事件 and self.事件[0] < 下限:
            self.事件.pop(0)

    def 记录(self, 现在):
        self.事件.append(现在)

    def 数量(self, 现在):
        self._剔除过期(现在)
        return len(self.事件)

    def 是否放行(self, 现在):
        return self.数量(现在) < self.上限
