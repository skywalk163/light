# -*- coding: utf-8 -*-
"""test_distributed_eval_light.py —— 第九轮 S2：master/worker 最小闭环（5 项 done 判据）

被测产物：
  - stdlib/分布式/调度核心.light（调度器：注册/领任务/交结果/心跳/注销 + 幂等 + 结果汇聚）
  - stdlib/分布式/节点核心.light（worker：注册→领→执行→交 + 独立心跳协程）
  - stdlib/并发.light（有界异步队列=背压 / 滑动窗口=限流，E9-S2 从 队列.py 提升，纯光明）
  - stdlib/分布式/节点网络.py    （系统边界：socket/json/单调时钟/随机标识/事件）—— 不被扫

判据达成方式（每条都有可复跑反跑，见 任务书/分布式判据清单.json）：
  分发     —— test_分发与结果汇聚：真起 1 master + 3 worker 子进程，1200 条，
            断言 3 节点各处理 > 0 且三者之和 == 总数（区分「真分给三节点」与「一节点假装」）。
  结果汇聚 —— test_分发与结果汇聚：报告含全部 1200 条、无重复 任务ID、无静默丢条。
  重派     —— test_重派与心跳_杀节点后重派且无静默丢条：kill 一个 worker，其已领未完成条目
            被重派，最终仍只计一次分、条数完整。
  心跳     —— test_重派与心跳…：停心跳后 master 把「被杀的那个节点」标失联（身份级）；另见 test_心跳独立于执行…
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
import 调度核心 as 主控模块  # noqa: E402
import 节点核心 as 工模块  # noqa: E402
from HTTP服务端 import HTTP服务端, 处理循环  # noqa: E402
from 调度核心 import 主控处理器, 主控实例  # noqa: E402
from 并发 import 有界队列类, 滑动窗口类  # noqa: E402

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
    import 调度核心 as M
    asyncio.run(M.主(端口文件, 状态文件, 报告文件, 任务文件, 容量, 心跳超时))


def _工进程(端口, 序号, 并发度, 心跳间隔, 身份目录=None, 慢秒=0):
    _安装()
    if 身份目录:
        os.environ["DUAN_NODE_ID_DIR"] = 身份目录
    if 慢秒:
        os.environ["DUAN_SLOW_SECS"] = str(慢秒)
    import 节点核心 as W
    asyncio.run(W.主(端口, 序号, 并发度, 心跳间隔))


def _生成任务文件(路径, 数量):
    条目 = [{"序号": i, "prompt": "q%d" % i, "期望": "a%d" % i} for i in range(数量)]
    写文本(路径, 序列化JSON({"条目": 条目}))


# R90：15.0 → 30.0。全量 `-n auto` 负载下，主控（master）启动 + 写出端口文件
# 实测可能超过 15s（R89 全量里 3 条 distributed_eval 红共用同一签名
# 「主控未在 15.0 秒内写出端口」；孤立跑与单文件负载跑都绿）。
# 只放宽「等多久」，不碰断言语义：用例仍要求结果不丢条、心跳不被误标失联。
# 标记：R90-PORTWINDOW
def _等端口(端口文件, 上限=30.0):
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


def _等失联(状态文件, 被杀节点ID, 上限):
    """轮询等待 master 把「被杀节点」标进 失联节点。

    心跳失联是**监控循环里的异步判定**（`现在 - 最后心跳 > 心跳超时` → 标失联），
    与「任务何时全部汇聚」存在赛跑：若剩余任务在心跳超时窗口内就跑完，监控循环的
    完成条件先成立并退出，失联就永远来不及标记。R57 任务2 实测（0.82 / py3.12）
    kill→报告完成约 1.0~1.5s，与默认 1.5s 心跳窗口正面相撞 → 约 30% 假红。
    这里显式轮询该标记（超时=心跳超时×2 才放弃），配合调用方缩短心跳窗口，
    把「谁先谁后」的赛跑消掉；**不放宽任何断言**。
    """
    截止 = time.time() + 上限
    数据 = {}
    while time.time() < 截止:
        if os.path.isfile(状态文件):
            内容 = 读文本(状态文件).strip()
            if 内容:
                try:
                    数据 = 解析JSON(内容)
                except Exception:
                    数据 = {}
                if 被杀节点ID in 数据.get("失联节点", []):
                    return 数据
        time.sleep(0.05)
    return 数据


def _跑集群(任务数, 杀=None, 容量=None, 心跳超时=1.5, 并发度=4, 慢秒=0, 心跳间隔=0.3):
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
        workers = [ctx.Process(target=_工进程,
                               args=(端口, i, 并发度, 心跳间隔, 身份目录, 慢秒))
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
        if 已杀 and 被杀节点ID:
            # 杀节点场景：显式轮询等待「被杀节点进 失联节点」，避免心跳标记与任务
            # 汇聚赛跑（R57 任务2，详见 _等失联 docstring）。超时=心跳超时×2。
            状态 = _等失联(状态文件, 被杀节点ID, 心跳超时 * 2)
        elif os.path.isfile(状态文件):
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
      分发 —— 把 调度核心.light 的「主控处理器」里 领任务 分派（把任务从队列交给 worker 的那句）
              改成直接返回 空（不真分），`和 == 1200` / `每节点 各 > 0` 立即立红。
      结果汇聚 —— 把 调度核心.light 监控循环里写报告的 `写文本(己.报告文件, ...)` 删掉，
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
      重派 —— 把 调度核心.light 监控循环里「重派在跑任务」那段（出队重派 + pop 在跑）删掉，
              杀节点后该 worker 在跑的任务永远不回队列，`len(条目) == 1200` 立红（静默丢条）。
      心跳 —— 把 调度核心.light 监控循环里「现在 - 最后心跳 > 心跳超时 → 标失联」那句注释掉，
              杀节点后 失联节点 恒为空，`被杀节点ID in 失联` 立红（只断「发过心跳」假绿）。

    时序（R57 任务2：消除 flaky，非放宽断言）：
      心跳标记是监控循环里的**异步判定**，与「任务全部汇聚」赛跑。0.82（py3.12）
      实测 kill→报告完成约 1.0~1.5s，与默认 1.5s 心跳窗口正面相撞 → 约 30% 假红
      （失联来不及标、监控循环已因完成而退出）。这里给本用例显式指定
      心跳间隔=0.05 / 心跳超时=0.5：
        · 心跳超时 0.5s << kill→报告 1.0s+，标记必然先于完成（余量 ≈2x）；
        · 心跳间隔 0.05s << 心跳超时 0.5s（余量 10x），存活 worker 不会被误标；
      再配合 _跑集群 内 _等失联 轮询兜底。全部原断言保留（重派 1200 条 / 无重复计分 /
      心跳失联恰 1 个 / 被杀节点 ID 在失联中），未 deselect、未放宽。
    """
    报告, 状态, 已杀, 被杀节点ID = _跑集群(1200, 杀=1, 心跳间隔=0.05, 心跳超时=0.5)
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
# 判据 心跳（返工单 §1.1）：独立心跳协程——worker 执行耗时 > 心跳超时 的任务期间
#           不被 master 标失联，结果必须被正常接受
# ===========================================================================
def test_心跳独立于执行_长任务期间不被标失联():
    """worker 的 执行 桩被 DUAN_SLOW_SECS 拉慢到 3s/条（> 心跳超时 1.5s），
    独立心跳协程仍按 心跳间隔(0.3s) 周期上报 → master 不失联、结果全被接受。

    反跑（返工单 §1.1 要求）：把 节点核心.light 里「设 心跳任务 为 创建任务(己.心跳循环())」
    这一句注释掉（独立心跳协程不启动），长任务执行期间 worker 无心跳 →
    master 在 心跳超时 后将其标失联 → 本测试 `失联 == []` 立即立红。
    这区分了「独立心跳」与「搭任务完成便车的心跳」——后者在桩的时间尺度下测不出来
    （桩执行是微秒级，交完结果立刻发心跳，永远不会超时；真 harness 秒级执行才暴露）。
    """
    报告, 状态, _已杀, _被杀节点ID = _跑集群(6, 慢秒=3)
    # 结果被正常接受：全部 6 条（每条执行 3s，期间心跳独立保活，master 未踢人）
    assert len(报告["条目"]) == 6, "心跳独立：长任务期间结果应全部被接受，实际 %d" % len(报告["条目"])
    assert len(set(报告["条目"].keys())) == 6, "心跳独立：不应有重复计分"
    # 执行耗时 > 心跳超时 期间未被标失联
    失联 = 状态.get("失联节点", [])
    assert 失联 == [], "心跳独立：长任务期间 worker 不应被标失联，实际失联=%r" % (失联,)


# ===========================================================================
# 判据 幂等：同一条目被两个 worker 都跑完，报告里只出现一次（进程内真 RPC）
# ===========================================================================
def test_幂等_同任务重复上报只计一次():
    """进程内真起 master（HTTP 服务端 + 真实 JSON-RPC），两个 worker 经 RPC 注册；
    同一任务被重复上报时只计一次分、并记账去重。

    反跑：把 调度核心.light 处理交结果 里「重复上报→去重记账（已接受=false、去重数+1）」那句
          改成 `已接受=true`（不记账），本断言 `len(结果表) == 1` / `去重数 == 1` 立红
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
            await 主控实例.配置(状态文件, 报告文件, 任务文件, 200, 1.5)
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
            assert 主控实例.去重数 == 1, "重复上报应恰记账一次（去重数==1）"
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

    反跑：把 并发.light 有界队列类.入队 里的 `等待 信号量获取(己.槽信号量)` 删掉
          （满即不再挂起，直接追加），本断言 `not 挡住.done()` 立红
          （生产者不再被挡，而变成丢背压语义直进）。
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

    反跑：把 并发.light 滑动窗口类._剔除过期 里的过期剔除 当 循环删掉，本断言
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



# ===========================================================================
# R123-B1：节点网络 标识生成/判型（此前零覆盖）—— 正例 + 反例
#
# 背景：`节点网络.light` 有 10 处 `截取` 按旧 (起始,长度) 传参，而 `截取` 的真语义是
#   `[起始:结束]`（证据：stdlib/内置核心字符串.light:14-15、stdlib/builtins.py:561），
#   导致 生成节点ID() 恒 'N0'、生成幂等键() 恒 'I'、是节点ID/是任务ID/是幂等键 恒 假、
#   常量比较('abc','abc') 抛 `ord() expected a character, but string of length 0 found`。
#   R122-D 实测：原生腿独立编译真跑与 Python 腿逐项一致 ⇒ 缺陷在 `.light` 真身。
#
# 本组用 **同一份 `节点网络.light`** 与 **契约真源 `节点网络.py`** 双腿对拍：
#   转译腿 —— 把 `.light` 复制到只含它的临时目录 ⇒ `_light_import_hook` 必然加载
#     `.light`（该目录没有同名 `.py`，`find_spec` 不让位给 .py）；fixture 会断言
#     载入形态是 `LightLoader` + `__file__` 以 `.light` 结尾，载不到就整组失效（不假绿）。
#   契约真源 —— `stdlib/分布式/节点网络.py` 按路径直载，不装钩子、不动 sys.modules。
#   随机生成器（节点ID/幂等键/任务ID/令牌）只比**线协议形态**与**自洽判定**：`.py` 用
#   `os.urandom`、`.light` 用 MT19937（文件头已登记的非 CSPRNG 偏离），逐值必然不同，
#   拿它判红或判绿都是假证据。
#
# 反跑锚：把 §B1 里任一处 `截取(x, 起, 起 + 1)` 改回 `截取(x, 起, 1)`，对应的形态断言
#   立刻变红（生成节点ID() 会退回 'N0'）；把 常量比较 的逐字符 `截取` 改回旧写法，
#   `常量比较('abc','abc')` 会抛 TypeError 而非返回 True。
# ===========================================================================
import importlib as _importlib
import importlib.util as _ilu
import re as _re

_节点ID形 = _re.compile(r"^N[0-9A-F]{8}$")
_任务ID形 = _re.compile(r"^T[0-9]{8}-[0-9A-F]{12}$")
_幂等键形 = _re.compile(r"^I[0-9A-F]{16}$")
_令牌形 = _re.compile(r"^[0-9A-F]{24}$")
_节点网络py真源 = os.path.join(_分布式, "节点网络.py")


@pytest.fixture(scope="module")
def 契约真源():
    """`树协议契约真源`：按路径直载 节点网络.py（`.light` 是它的光明侧镜像）。"""
    spec = _ilu.spec_from_file_location("_r123_节点网络契约真源", _节点网络py真源)
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def 光腿(tmp_path_factory):
    """转译腿：真加载 `节点网络.light`（复制到只含它的临时目录再 import）。"""
    d = tmp_path_factory.mktemp("r123b_节点网络")
    shutil.copyfile(os.path.join(_分布式, "节点网络.light"), os.path.join(d, "节点网络.light"))
    找器 = _light_import_hook.install([str(d)])
    # `install` 只做追加，而本模块级 install 已把 [_STDLIB, _分布式] 排在前面；
    # 必须把临时目录**提到最前**，否则 分布式/ 里那份「非纯光明 + 有同名 .py」
    # 会先命中并让位给 .py（翻面模拟就失灵了）。
    try:
        找器.search_paths.remove(str(d))
    except ValueError:
        pass
    找器.search_paths.insert(0, str(d))
    原模块 = sys.modules.get("节点网络")
    sys.modules.pop("节点网络", None)
    try:
        m = _importlib.import_module("节点网络")
        assert type(getattr(m, "__loader__", None)).__name__ == "LightLoader", \
            "节点网络 未走 .light（钩子未接管），本组用例无效 —— 不许当绿"
        assert str(getattr(m, "__file__", "")).endswith(".light"), "节点网络 未走 .light"
        yield m
    finally:
        try:
            找器.search_paths.remove(str(d))
        except ValueError:
            pass
        if 原模块 is not None:
            sys.modules["节点网络"] = 原模块
        else:
            sys.modules.pop("节点网络", None)


# ---------------------------------------------------------------------------
# 生成器：线协议形态
# ---------------------------------------------------------------------------
def _过A1缺口(光腿, 名):
    """调用生成器；若只差 A1 的 `时间格式化` 转译腿映射，按 xfail 登记（待修清单）。

    ⚠️ 这是**已知阻塞**，不是绿：A1（R123-A 线）负责在 `src/code_generator.py` 补
    `'时间格式化': '_light_builtin.格式化时间'` 一类映射。A1 落地后本分支不再触发，
    测试自动变成真断言（无需改本文件）。
    """
    try:
        return getattr(光腿, 名)()
    except NameError as e:
        if "时间格式化" in str(e):
            pytest.xfail(
                "A1 缺口（跨腿内建名一致性）：`节点网络.light:110` 调 `时间格式化`，"
                "原生腿有内建、转译腿零映射 ⇒ Python 腿 NameError。"
                "待 A1 在 src/code_generator.py 补映射后自动转绿。")
        raise


def test_生成节点ID_线协议形态(光腿):
    v = 光腿.生成节点ID()
    assert _节点ID形.match(v), "生成节点ID() 应为 N + 8 位十六进制，实得 %r" % (v,)
    assert 光腿.是节点ID(v) is True, "自产节点ID 必须过自家 是节点ID()"


def test_生成幂等键_线协议形态(光腿):
    v = 光腿.生成幂等键()
    assert _幂等键形.match(v), "生成幂等键() 应为 I + 16 位十六进制，实得 %r" % (v,)
    assert 光腿.是幂等键(v) is True, "自产幂等键 必须过自家 是幂等键()"


def test_生成任务ID_线协议形态(光腿):
    v = _过A1缺口(光腿, "生成任务ID")
    assert _任务ID形.match(v), "生成任务ID() 应为 T + 8 位数字 - 12 位十六进制，实得 %r" % (v,)
    assert 光腿.是任务ID(v) is True, "自产任务ID 必须过自家 是任务ID()"


def test_生成令牌_线协议形态(光腿):
    v = 光腿.生成令牌()
    assert _令牌形.match(v), "生成令牌() 应为 24 位十六进制，实得 %r" % (v,)


# ---------------------------------------------------------------------------
# 判型/比较：正例 + 反例（反例含「长度对但字符错」这档，专抓把长度当结束的旧写法）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("文本,期望", [
    ("N12345678", True),          # 正例
    ("N00000000", True),          # 正例：全 0 也是合法十六进制
    ("N1234567", False),          # 反例：长度 8
    ("N123456789", False),        # 反例：长度 10
    ("n12345678", False),         # 反例：小写
    ("N1234567G", False),         # 反例：末位非十六进制
    ("N1234567-", False),         # 反例：末位是符号
    ("T12345678", False),         # 反例：前缀错
    ("", False),                  # 反例：空串
])
def test_是节点ID_正反例(光腿, 文本, 期望):
    assert 光腿.是节点ID(文本) is 期望, "是节点ID(%r) 应为 %r" % (文本, 期望)


@pytest.mark.parametrize("值,期望", [(None, False), (12345678, False), ([], False)])
def test_是节点ID_非字符串安全为假(光腿, 值, 期望):
    assert 光腿.是节点ID(值) is 期望, "非字符串输入必须安全返回 假，不许抛"


@pytest.mark.parametrize("文本,期望", [
    ("T12345678-ABCDEF012345", True),     # 正例
    ("T00000000-000000000000", True),     # 正例
    ("T1234567X-ABCDEF012345", False),    # 反例：第 9 位非数字
    ("T12345678XABCDEF012345", False),    # 反例：缺分隔符
    ("T12345678_ABCDEF012345", False),    # 反例：分隔符是下划线
    ("T12345678-ABCDEF01234", False),     # 反例：末段 11 位
    ("T12345678-ABCDEF0123456", False),   # 反例：末段 13 位
    ("T12345678-abcdef012345", False),    # 反例：末段小写
    ("N12345678-ABCDEF012345", False),    # 反例：前缀错
    ("", False),
])
def test_是任务ID_正反例(光腿, 文本, 期望):
    assert 光腿.是任务ID(文本) is 期望, "是任务ID(%r) 应为 %r" % (文本, 期望)


@pytest.mark.parametrize("值,期望", [(None, False), (1, False)])
def test_是任务ID_非字符串安全为假(光腿, 值, 期望):
    assert 光腿.是任务ID(值) is 期望


@pytest.mark.parametrize("文本,期望", [
    ("I0123456789ABCDEF", True),          # 正例
    ("I0123456789ABCDE", False),          # 反例：15 位
    ("I0123456789ABCDEF0", False),        # 反例：17 位
    ("X0123456789ABCDEF", False),         # 反例：前缀错
    ("i0123456789abcdef", False),         # 反例：小写
    ("", False),
])
def test_是幂等键_正反例(光腿, 文本, 期望):
    assert 光腿.是幂等键(文本) is 期望, "是幂等键(%r) 应为 %r" % (文本, 期望)


@pytest.mark.parametrize("甲,乙,期望", [
    ("abc", "abc", True),
    ("Token-A", "Token-A", True),
    ("T", "T", True),
    ("", "", True),            # 两侧同为空串：等长且无字符差异 ⇒ 真（与 hmac.compare_digest 一致）
    ("abc", "abd", False),     # 反例：同长不同末位（旧写法在这里抛 TypeError 而非返回假）
    ("abc", "abcd", False),    # 反例：长度不同
    ("", "a", False),          # 反例：一侧空
    (None, None, False),       # 反例：非字符串安全返回假
    (123, 123, False),         # 反例：非字符串安全返回假
])
def test_常量比较_正反例(光腿, 甲, 乙, 期望):
    assert 光腿.常量比较(甲, 乙) is 期望, "常量比较(%r, %r) 应为 %r" % (甲, 乙, 期望)


@pytest.mark.parametrize("头字典,名,缺省,期望", [
    ({"X-Auth-Token": "T1"}, "x-auth-token", "", "T1"),
    ({"Content-Length": "7"}, "content-length", "", "7"),
    ({"A": "1", "B": "2"}, "B", "", "2"),
    ({}, "x-auth-token", "D", "D"),
])
def test_取头值_大小写不敏感(光腿, 头字典, 名, 缺省, 期望):
    assert 光腿.取头值(头字典, 名, 缺省) == 期望


def test_转整数_宽松语义(光腿):
    assert 光腿.转整数("42") == 42
    assert 光腿.转整数("-5") == -5
    assert 光腿.转整数("x", 7) == 7, "转不动要给缺省，不许抛"


# ---------------------------------------------------------------------------
# 双腿逐值对拍（判型/比较/取头值/转换——全是确定性函数，必须逐值相等）
# ---------------------------------------------------------------------------
def _对拍用例():
    return [
        ("是节点ID('N12345678')", lambda m: m.是节点ID("N12345678")),
        ("是节点ID('N1234567')", lambda m: m.是节点ID("N1234567")),
        ("是节点ID('N1234567G')", lambda m: m.是节点ID("N1234567G")),
        ("是节点ID('n12345678')", lambda m: m.是节点ID("n12345678")),
        ("是节点ID('')", lambda m: m.是节点ID("")),
        ("是节点ID(None)", lambda m: m.是节点ID(None)),
        ("是节点ID(12345678)", lambda m: m.是节点ID(12345678)),
        ("是任务ID(合法)", lambda m: m.是任务ID("T12345678-ABCDEF012345")),
        ("是任务ID(第9位非数字)", lambda m: m.是任务ID("T1234567X-ABCDEF012345")),
        ("是任务ID(末段短一位)", lambda m: m.是任务ID("T12345678-ABCDEF01234")),
        ("是任务ID(末段小写)", lambda m: m.是任务ID("T12345678-abcdef012345")),
        ("是任务ID(缺分隔符)", lambda m: m.是任务ID("T12345678_ABCDEF012345")),
        ("是任务ID(None)", lambda m: m.是任务ID(None)),
        ("是幂等键(合法)", lambda m: m.是幂等键("I0123456789ABCDEF")),
        ("是幂等键(短一位)", lambda m: m.是幂等键("I0123456789ABCDE")),
        ("是幂等键(前缀错)", lambda m: m.是幂等键("X0123456789ABCDEF")),
        ("是幂等键(None)", lambda m: m.是幂等键(None)),
        ("常量比较(abc,abc)", lambda m: m.常量比较("abc", "abc")),
        ("常量比较(abc,abd)", lambda m: m.常量比较("abc", "abd")),
        ("常量比较(abc,abcd)", lambda m: m.常量比较("abc", "abcd")),
        ("常量比较('','')", lambda m: m.常量比较("", "")),
        ("常量比较('','a')", lambda m: m.常量比较("", "a")),
        ("常量比较(None,None)", lambda m: m.常量比较(None, None)),
        ("常量比较(Token-A,Token-A)", lambda m: m.常量比较("Token-A", "Token-A")),
        ("常量比较(Token-A,Token-B)", lambda m: m.常量比较("Token-A", "Token-B")),
        ("取头值(命中)", lambda m: m.取头值({"X-Auth-Token": "T1"}, "x-auth-token")),
        ("取头值(缺省)", lambda m: m.取头值({}, "x-auth-token", "D")),
        ("取头值(Content-Length)", lambda m: m.取头值({"Content-Length": "7"}, "content-length")),
        ("转整数('42')", lambda m: m.转整数("42")),
        ("转整数('x',7)", lambda m: m.转整数("x", 7)),
        ("转字符串(8080)", lambda m: m.转字符串(8080)),
    ]


def test_双腿对拍_确定性函数逐值一致(光腿, 契约真源):
    """`.light`（真加载）与 `.py`（契约真源）在确定性函数上必须逐值逐类型相等。"""
    不符 = []
    for 标题, fn in _对拍用例():
        a = fn(光腿)
        b = fn(契约真源)
        if type(a) is not type(b) or a != b:
            不符.append("%s：.light=%r ／ .py=%r" % (标题, a, b))
    assert not 不符, "双腿不等价（%d 项）：\n  %s" % (len(不符), "\n  ".join(不符))


def test_双腿对拍_随机生成器线协议形态一致(光腿, 契约真源):
    """随机量不逐值比，但**线协议形态**必须一致（两腿都得产出合法 ID）。"""
    for 名, 形 in (("生成节点ID", _节点ID形), ("生成幂等键", _幂等键形),
                   ("生成任务ID", _任务ID形), ("生成令牌", _令牌形)):
        for 腿, m in (("转译腿", 光腿), ("契约真源", 契约真源)):
            v = _过A1缺口(m, 名) if 腿 == "转译腿" else getattr(m, 名)()
            assert 形.match(v), "%s 的 %s() 形态不符线协议：%r" % (腿, 名, v)
