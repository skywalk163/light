# -*- coding: utf-8 -*-
"""test_distributed_eval_light.py —— 第九轮 S2：master/worker 最小闭环（5 项 done 判据）

被测产物：
  - stdlib/分布式/master.light  （调度器：注册/领任务/交结果/心跳/注销 + 幂等 + 结果汇聚）
  - stdlib/分布式/worker.light  （worker：注册→领→执行→交 + 心跳）
  - stdlib/分布式/队列.py        （有界异步队列=背压 / 滑动窗口=限流）
  - stdlib/分布式/节点网络.py    （系统边界：socket/json/单调时钟/随机标识/事件）—— 不被扫

判据达成方式（每条都有可复跑反跑，见 任务书/分布式判据清单.json）：
  分发     —— test_分发与结果汇聚：真起 1 master + 3 worker 子进程，1200 条，
            断言 3 节点各处理 > 0 且三者之和 == 总数（区分「真分给三节点」与「一节点假装」）。
  结果汇聚 —— test_分发与结果汇聚：报告含全部 1200 条、无重复 任务ID、无静默丢条。
  重派     —— test_重派与心跳_杀节点后重派且无静默丢条：kill 一个 worker，其已领未完成条目
            被重派，最终仍只计一次分、条数完整。
  心跳     —— test_重派与心跳…：停心跳后 master 在超时窗口内把该 worker 标为失联（失联节点 >= 1）。
  幂等     —— test_幂等_同任务重复上报只计一次：进程内真起 master + 真实 RPC，同任务重复上报
            只计一次分（去重记账）。

实测平台：本机 Windows（任务书 §1 明示 CI 只有一个 FreeBSD runner，本机全绿不构成 CI 绿的证据；
所有与平台相关的结论在 交付报告 里标明「实测平台=Windows」）。每个等网络的 await 都套硬超时，
并加 faulthandler 看门狗——挂死的红不可诊断（gitea run 99 教训）。
"""
import asyncio
import faulthandler
import json
import multiprocessing
import os
import shutil
import sys
import tempfile
import time

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STDLIB = os.path.join(_REPO, "stdlib")
_分布式 = os.path.join(_STDLIB, "分布式")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
if _分布式 not in sys.path:
    sys.path.insert(0, _分布式)
import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB, _分布式])  # noqa: E402

from 节点网络 import (  # noqa: E402
    客户端 as 客户端工厂,
    解析 as 解析JSON,
    序列化 as 序列化JSON,
    写文本,
    读文本,
    转字符串,
)
import master as 主控模块  # noqa: E402
import worker as 工模块  # noqa: E402
from HTTP服务端 import HTTP服务端, 处理循环  # noqa: E402
from master import 主控处理器, 主控实例  # noqa: E402
from 队列 import 有界队列类, 滑动窗口类  # noqa: E402

网络超时 = 5.0
用例超时 = 90.0
超时异常 = (asyncio.TimeoutError, TimeoutError)


async def 限时(可等对象, 说明, 秒=网络超时):
    """给一次网络等待套硬上限：超时转成断言失败（带说明），不许静静地等下去。"""
    try:
        return await asyncio.wait_for(可等对象, 秒)
    except 超时异常:
        raise AssertionError(
            "等「%s」超过 %s 秒仍未完成 —— 挂死必须表现为失败，不是卡死" % (说明, 秒))


# ---------------------------------------------------------------------------
# 多进程集群（同机多进程，不是线程；§7 口径 4）—— 区分「真分三节点」与「假分」
# ---------------------------------------------------------------------------
def _安装():
    if _STDLIB not in sys.path:
        sys.path.insert(0, _STDLIB)
    import _light_import_hook
    _light_import_hook.install([_STDLIB, _分布式])


def _主进程(端口文件, 状态文件, 报告文件, 任务文件, 容量, 心跳超时):
    _安装()
    import master as M
    asyncio.run(M.主(端口文件, 状态文件, 报告文件, 任务文件, 容量, 心跳超时))


def _工进程(端口, 序号, 并发度, 心跳间隔, 身份目录=None):
    _安装()
    if 身份目录:
        os.environ["DUAN_NODE_ID_DIR"] = 身份目录
    import worker as W
    asyncio.run(W.主(端口, 序号, 并发度, 心跳间隔))


def _生成任务文件(路径, 数量):
    条目 = [{"序号": i, "prompt": "q%d" % i, "期望": "a%d" % i} for i in range(数量)]
    写文本(路径, 序列化JSON({"条目": 条目}))


def _等端口(端口文件, 上限=15.0):
    截止 = time.time() + 上限
    while time.time() < 截止:
        if os.path.isfile(端口文件):
            内容 = 读文本(端口文件).strip()
            if 内容:
                return int(内容)
        time.sleep(0.05)
    raise AssertionError("主控未在 %s 秒内写出端口" % 上限)


def _等进度(状态文件, 阈值, 上限=用例超时):
    截止 = time.time() + 上限
    while time.time() < 截止:
        if os.path.isfile(状态文件):
            内容 = 读文本(状态文件).strip()
            if 内容:
                数据 = 解析JSON(内容)
                if 数据.get("已汇聚", 0) >= 阈值:
                    return
        time.sleep(0.1)
    raise AssertionError("集群未在 %s 秒内达到进度阈值 %s" % (上限, 阈值))


def _等报告(报告文件, 总数, 上限=用例超时):
    截止 = time.time() + 上限
    while time.time() < 截止:
        if os.path.isfile(报告文件):
            内容 = 读文本(报告文件).strip()
            if 内容:
                数据 = 解析JSON(内容)
                if 数据.get("完成", 0) == 总数:
                    return 数据
        time.sleep(0.1)
    raise AssertionError("主控未在 %s 秒内汇聚全部 %d 条" % (上限, 总数))


def _跑集群(任务数, 杀=None, 容量=None, 心跳超时=1.5, 并发度=4):
    tmp = tempfile.mkdtemp(prefix="dist_eval_")
    m = None
    workers = []
    try:
        任务文件 = os.path.join(tmp, "任务.json")
        端口文件 = os.path.join(tmp, "port.txt")
        状态文件 = os.path.join(tmp, "state.json")
        报告文件 = os.path.join(tmp, "report.json")
        身份目录 = os.path.join(tmp, "节点身份")
        os.makedirs(身份目录, exist_ok=True)
        _生成任务文件(任务文件, 任务数)
        实际容量 = 容量 if 容量 is not None else 任务数
        ctx = multiprocessing.get_context("spawn")
        m = ctx.Process(target=_主进程,
                        args=(端口文件, 状态文件, 报告文件, 任务文件, 实际容量, 心跳超时))
        m.start()
        端口 = _等端口(端口文件)
        workers = [ctx.Process(target=_工进程, args=(端口, i, 并发度, 0.3, 身份目录))
                   for i in range(3)]
        for w in workers:
            w.start()
        已杀 = False
        被杀节点ID = None
        if 杀 is not None and 杀 < len(workers):
            _等进度(状态文件, 任务数 * 0.15)
            workers[杀].terminate()
            workers[杀].join(timeout=5)
            已杀 = True
            # worker 注册后把自己的 节点ID 写进 节点<序号>.txt（身份级断言用）
            身份文件 = os.path.join(身份目录, "节点%d.txt" % 杀)
            for _ in range(50):
                if os.path.isfile(身份文件):
                    被杀节点ID = 读文本(身份文件).strip()
                    if 被杀节点ID:
                        break
                time.sleep(0.1)
            assert 被杀节点ID, "测试自身：被杀 worker#%d 未写出节点ID（身份断言无从谈起）" % 杀
        报告 = _等报告(报告文件, 任务数)
        状态 = {}
        if os.path.isfile(状态文件):
            状态 = 解析JSON(读文本(状态文件))
        return 报告, 状态, 已杀, 被杀节点ID
    finally:
        # 不论成功失败都必须回收子进程：否则孤儿进程会占着端口/继承的管道，
        # 让上层 shell（尤其 `| tail`）永远等不到 EOF，表现为「挂死」。第九轮 S2 实测教训。
        for w in workers:
            try:
                if w.is_alive():
                    w.terminate()
            except Exception:
                pass
            try:
                w.join(timeout=5)
            except Exception:
                pass
        if m is not None:
            try:
                if m.is_alive():
                    m.terminate()
            except Exception:
                pass
            try:
                m.join(timeout=5)
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# 判据 分发 + 结果汇聚：3 节点 × 1200 条，真分、条数完整、无重复计分、无静默丢条
# ===========================================================================
def test_分发与结果汇聚():
    """真起 3 个 worker 子进程跑 1200 条。

    分发：断言 3 个节点都领到任务（各 > 0）且三者处理之和 == 1200——
          这把「真分给三个节点」与「一个节点跑完假装分了」区分开。
    结果汇聚：断言报告含全部 1200 条、无重复 任务ID、无静默丢条。

    反跑（改哪一行→哪条断言红，见 任务书/分布式判据清单.json）：
      分发 —— 把 master.light 的「主控处理器」里 领任务 分派（把任务从队列交给 worker 的那句）
              改成直接返回 空（不真分），`和 == 1200` / `每节点 各 > 0` 立即立红。
      结果汇聚 —— 把 master.light 监控循环里写报告的 `写文本(己.报告文件, ...)` 删掉，
              或把 `长(己.结果表) == 己.总数` 这个完成条件注释掉，
              `len(条目) == 1200` / `len(set(条目.keys())) == 1200` 立红。
    """
    报告, _状态, _已杀, _被杀节点ID = _跑集群(1200)
    条目 = 报告["条目"]
    assert len(条目) == 1200, "结果汇聚：报告应含全部 1200 条，实际 %d" % len(条目)
    # 无静默丢条：每个 任务ID 恰出现一次（幂等去重不丢、不重复）
    assert len(set(条目.keys())) == 1200, "结果汇聚：存在重复 任务ID（去重异常）"
    # 分发：三节点都要 > 0 且三者之和 == 总数
    每节点 = 报告["每节点"]
    assert len(每节点) == 3, "分发：应有 3 个节点各领到任务，实际 %d 个" % len(每节点)
    for 节点ID, 计数 in 每节点.items():
        assert 计数 > 0, "分发：节点 %s 处理条数为 0（不是真分给三节点）" % 节点ID
    和 = sum(每节点.values())
    assert 和 == 1200, "分发：三节点处理之和 %d 应等于总数 1200" % 和


# ===========================================================================
# 判据 重派 + 心跳：kill 一个 worker，其已领未完成条目重派、最终只计一次分；
#           停止心跳后 master 在超时窗口内标其失联
# ===========================================================================
def test_重派与心跳_杀节点后重派且无静默丢条():
    """kill 掉 worker #1，master 应：① 在心跳超时窗口内标其失联；② 把其已领未完成条目重派；
    ③ 最终报告仍完整、且只计一次分（无重复计分）。

    反跑：
      重派 —— 把 master.light 监控循环里「重派在跑任务」那段（出队重派 + pop 在跑）删掉，
              杀节点后该 worker 在跑的任务永远不回队列，`len(条目) == 1200` 立红（静默丢条）。
      心跳 —— 把 master.light 监控循环里「现在 - 最后心跳 > 心跳超时 → 标失联」那句注释掉，
              杀节点后 失联节点 恒为空，`len(失联) >= 1` 立红（只断「发过心跳」假绿）。
    """
    报告, 状态, 已杀, 被杀节点ID = _跑集群(1200, 杀=1)
    assert 已杀, "测试自身：未能 kill 掉 worker（集群编排异常）"
    # 重派：杀节点后最终报告仍含全部 1200 条（无静默丢条）
    assert len(报告["条目"]) == 1200, "重派：最终报告应仍含全部 1200 条，实际 %d" % len(报告["条目"])
    assert len(set(报告["条目"].keys())) == 1200, "重派：重派不应造成重复计分"
    # 心跳：停止心跳后 master 在超时窗口内把「被杀的那个节点」标成失联——身份级断言，
    # 不是「失联非空」这种集合非空即恒真的下界断言（assert_quality 门禁会拦后者）。
    失联 = 状态.get("失联节点", [])
    assert len(失联) == 1, ("心跳：失联应恰为被杀节点 1 个，实际 %r" % 失联)
    assert 被杀节点ID in 失联, ("心跳：被杀节点 %s 应被 master 标为失联，实际失联=%r"
                                  % (被杀节点ID, 失联))


# ===========================================================================
# 判据 幂等：同一条目被两个 worker 都跑完，报告里只出现一次（进程内真 RPC）
# ===========================================================================
def test_幂等_同任务重复上报只计一次():
    """进程内真起 master（HTTP 服务端 + 真实 JSON-RPC），两个 worker 经 RPC 注册；
    同一任务被重复上报时只计一次分、并记账去重。

    反跑：把 master.light 处理交结果 里「重复上报→去重记账（已接受=false、去重数+1）」那句
          改成 `已接受=true`（不记账），本断言 `len(结果表) == 1` / `去重数 >= 1` 立红
          （报告里出现两次、去重数仍为 0）。
    """
    tmp = tempfile.mkdtemp(prefix="dist_idem_")
    try:
        任务文件 = os.path.join(tmp, "任务.json")
        状态文件 = os.path.join(tmp, "state.json")
        报告文件 = os.path.join(tmp, "report.json")
        _生成任务文件(任务文件, 1)
        端口文件 = os.path.join(tmp, "port.txt")

        async def 主体():
            await 主控实例.配置(状态文件, 报告文件, 任务文件, 200, 1.5, 30.0)
            await 主控实例.入队全部()
            服务端 = HTTP服务端(主控处理器, 5.0)
            写文本(端口文件, 转字符串(服务端.端口()))
            循环任务 = asyncio.create_task(处理循环(服务端))
            监控任务 = asyncio.create_task(主控实例.监控循环())
            端口 = 服务端.端口()
            # worker A 注册
            cA = 客户端工厂("127.0.0.1", 端口, 网络超时)
            rA = await 限时(cA.请求("注册", {"节点ID": "NAAAAAA01", "并发度": 1, "协议版本": "1.0"}),
                            "A 注册")
            tokA = rA["结果"]["会话令牌"]
            cA.带令牌(tokA)
            # worker B 注册
            cB = 客户端工厂("127.0.0.1", 端口, 网络超时)
            rB = await 限时(cB.请求("注册", {"节点ID": "NBBBBBB02", "并发度": 1, "协议版本": "1.0"}),
                            "B 注册")
            tokB = rB["结果"]["会话令牌"]
            cB.带令牌(tokB)
            # A 领任务
            lA = await 限时(cA.请求("领任务", {"节点ID": "NAAAAAA01", "在跑任务": []}),
                            "A 领任务")
            任务 = lA["结果"]["任务"]
            assert isinstance(任务, dict) and "任务ID" in 任务 and "幂等键" in 任务, \
                "领任务应返回带 任务ID/幂等键 的任务对象，实际 %r" % (任务,)
            T = 任务["任务ID"]
            I = 任务["幂等键"]
            结果体 = {"输出": "o", "得分": 1, "耗时": 0.0, "尝试次数": 1,
                       "错误分类": "", "错误": ""}
            # 首次上报（应接受）
            f1 = await 限时(cA.请求("交结果", {"节点ID": "NAAAAAA01", "任务ID": T,
                                              "幂等键": I, "结果": 结果体}), "A 首次交结果")
            assert f1["结果"]["已接受"] is True, "首次上报应被接受（已接受=true）"
            # 重复上报（同 任务ID、同 幂等键 → 去重）
            f2 = await 限时(cA.请求("交结果", {"节点ID": "NAAAAAA01", "任务ID": T,
                                              "幂等键": I, "结果": 结果体}), "A 重复交结果")
            assert f2["结果"]["已接受"] is False, "重复上报应被去重（已接受=false）"
            assert 主控实例.去重数 >= 1, "重复上报应被记账（去重数>=1）"
            # 关键断言：结果表只含一次（只计一次分）
            assert len(主控实例.结果表) == 1, "同任务重复上报后结果表应只计一次，实际 %d" % len(主控实例.结果表)
            服务端.停止()
            循环任务.cancel()
            监控任务.cancel()
            try:
                await 循环任务
            except BaseException:
                pass
            try:
                await 监控任务
            except BaseException:
                pass

        faulthandler.dump_traceback_later(用例超时 + 30.0, exit=True)
        try:
            asyncio.run(主体())
        finally:
            faulthandler.cancel_dump_traceback_later()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# 背压（S2 → partial，判据见 任务书/分布式判据清单.json「备注」）：有界队列满=等
# ===========================================================================
def test_背压_满后生产者被挡住():
    """有界队列（容量 2）灌满后，第三个 入队 必须被阻塞（不是抛、不是偷偷多进）。

    反跑：把 队列.py 有界队列类.入队 里的 `await self._队列.put(项)` 改成
          `self._队列.put_nowait(项)`（满即抛），本断言 `not 挡住.done()` 立红
          （生产者不再被挡，而变成抛异常丢条）。
    """

    async def 主体():
        q = 有界队列类(2)
        await q.入队("a")
        await q.入队("b")
        assert q.是否满(), "灌 2 条后队列应满"
        # 满队时第三个入队在独立任务里，不应立刻完成（被背压挡住）
        挡住 = asyncio.create_task(q.入队("c"))
        await asyncio.sleep(0.2)
        assert not 挡住.done(), "背压：队列满后生产者应被挡住（入队未完成）"
        assert q.大小() == 2, "背压：满队不应偷偷多进一条"
        出 = await q.出队()
        await 挡住  # 消费者取走一个后，被挡的生产者才补进
        assert q.大小() == 2, "背压：消费者取走一个后生产者才补进，大小应回到 2"

    asyncio.run(主体())


# ===========================================================================
# 限流（S2 → partial）：滑动窗口与分批可区分（滚动过期）
# ===========================================================================
def test_限流_滑动窗口与分批不同():
    """滑动窗口（上限 3、窗口 1.0s）：t=0 记 3 条→满；窗口滑过（t=1.1）旧事件过期→放行新事件。
    这与「分批计数」（旧事件永不因时间流逝滑出）本质不同。

    反跑：把 队列.py 滑动窗口类._剔除过期 里的过期剔除循环删掉，本断言
          `窗.数量(1.1) == 0` / `窗.是否放行(1.1)` 立红（限流退化成累加计数，与分批无异）。
    """
    窗 = 滑动窗口类(3, 1.0)
    窗.记录(0.0)
    窗.记录(0.0)
    窗.记录(0.0)
    assert 窗.数量(0.0) == 3, "窗口内 3 条应计满"
    assert not 窗.是否放行(0.0), "满窗不应放行"
    # 窗口滑过：t=1.1 时 t=0 的事件已过期 → 数量衰减为 0、可放行（与分批不同）
    assert 窗.数量(1.1) == 0, "限流：滑动窗口应剔除过期事件，数量应衰减为 0"
    assert 窗.是否放行(1.1), "限流：过期事件剔除后新事件应被放行（与固定分批不同）"
