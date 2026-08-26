# -*- coding: utf-8 -*-
"""
test_harness_streaming_light.py —— E9-S2 §4 对标清单补齐判据

覆盖三条 partial 的补齐条件（判据落地，不动 JSON 状态字段，状态由 G9 统一改）：
- #6 流式增量消费：编排.带重试对话 优先累加 内容增量（真正的逐块增量），
  通道只给 累积内容 时回退到它；harness 层终于有「>1 块」的覆盖。
- #5 错误分类与单条兜底（重试决策）：带重试对话 按 错误分类.应重试 驱动重试——
  可重试类(超时/连接/HTTP 429/5xx)才重试，不可重试类(解析/工具/4xx/未分类)直接记失败停止。
- #5(2) 报告兜底：写报告带兜底 在 汇总/写盘 任一环节异常时，仍把逐条结果落盘到
  `.partial.json`，不让整份报告因打分/汇总/写盘异常而丢失。

反跑改坏点贴在各用例 docstring；全部用真实行为（输出拼接 / 尝试次数 / 部分报告落盘）判定。
"""
import asyncio
import json
import os
import sys

import pytest

_根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STDLIB = os.path.join(_根目录, "stdlib")
_HARNESS = os.path.join(_根目录, "examples", "harness")
_SRC = os.path.join(_根目录, "src")
for _p in (_STDLIB, _HARNESS, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import _light_import_hook
_light_import_hook.install([_STDLIB, _HARNESS])

from 编排 import 带重试对话
from 评测驱动 import 写报告带兜底


# ---- #6 流式增量消费：mock 通道，逐块给 内容增量（真正的增量，非累积）----
class _增量通道:
    """每条消息吐 3 块：内容增量 = ["你", "好", ""]（最后一块为空收尾）。"""
    def __init__(self, 块列表=None):
        self.块列表 = 块列表 or [
            {"角色": "assistant", "内容增量": "你", "累积内容": "你", "完成原因": "", "结束": False, "用量": {}},
            {"角色": "", "内容增量": "好", "累积内容": "你好", "完成原因": "stop", "结束": False, "用量": {}},
            {"角色": "", "内容增量": "", "累积内容": "你好", "完成原因": "stop", "结束": True, "用量": {}},
        ]

    async def 流式对话2(self, 消息列表):
        for 块 in self.块列表:
            yield 块


class _累积通道:
    """只给 累积内容（不给 内容增量）的退化通道，验证回退路径。"""
    def __init__(self):
        pass

    async def 流式对话2(self, 消息列表):
        yield {"角色": "assistant", "累积内容": "北", "结束": False, "用量": {}}
        yield {"角色": "", "累积内容": "北京", "结束": True, "用量": {}}


class Test流式增量消费:
    """#6 补齐条件：harness 层首次覆盖「>1 块」流式消费，且正确累加增量。"""

    def test_内容增量被逐块累加(self):
        """通道给 内容增量=["你","好",""]，输出应拼成 "你好"。

        反跑改坏点：把 编排.light 带重试对话 的 `设 增量累积 为 增量累积 加上 块["内容增量"]`
        改回 `设 增量累积 为 块["累积内容"]`（只取最后一块的累积内容，且若通道只给增量则取到空），
        本条 `输出 == "你好"` 红（实际拿到 "" 或最后一帧空串）。
        """
        结果 = asyncio.run(带重试对话(_增量通道(), [{"role": "user", "content": "x"}], 3))
        assert 结果["成功"] is True
        assert 结果["输出"] == "你好", "内容增量应被逐块累加为 你好，实际 %r" % 结果["输出"]

    def test_只给累积内容时回退正确(self):
        """退化通道只给 累积内容（无 内容增量），应回退取最后非空累积 = "北京"。"""
        结果 = asyncio.run(带重试对话(_累积通道(), [{"role": "user", "content": "x"}], 3))
        assert 结果["成功"] is True
        assert 结果["输出"] == "北京", "只给累积内容时应回退取到 北京，实际 %r" % 结果["输出"]


# ---- #5 错误分类驱动重试决策 ----
class _故障通道:
    """按 mode 在首块前抛异常：超时→TimeoutError（应重试）；解析→JSONDecodeError（不应重试）。"""
    def __init__(self, mode):
        self.mode = mode

    async def 流式对话2(self, 消息列表):
        if self.mode == "超时":
            raise TimeoutError("timed out")
        if self.mode == "解析":
            raise json.JSONDecodeError("bad json", "", 0)
        yield {"角色": "assistant", "内容增量": "ok", "累积内容": "ok", "结束": True, "用量": {}}


class Test错误分类驱动重试:
    """#5 补齐条件：重试决策由 错误分类.应重试 驱动，而非无脑重试。"""

    def test_可重试类会重试到上限(self):
        """TimeoutError→超时类→应重试：尝试次数应等于 重试次数（默认 3）。

        反跑改坏点：把 编排.light 带重试对话 的 `如果 非 错误分类.应重试(分类结果): 跳出`
        删掉（恢复成「任何异常都重试」），本条仍绿但语义退化；更直接的反跑是把
        `非 错误分类.应重试` 改成永远成立 → 本条 `尝试次数 == 3` 红（实际 1）。
        """
        结果 = asyncio.run(带重试对话(_故障通道("超时"), [{"role": "user", "content": "x"}], 3))
        assert 结果["成功"] is False
        assert 结果["尝试次数"] == 3, "超时类应重试满 3 次，实际 %s" % 结果["尝试次数"]
        assert 结果["错误"] == "可重试错误"

    def test_不可重试类直接记失败不重试(self):
        """JSONDecodeError→解析类→不应重试：尝试次数应为 1，错误分类=解析。

        反跑改坏点：把 带重试对话 的捕获从 `捕获 异常 e:` 改回 `捕获 TimeoutError, ConnectionError:`
        （解析异常不再被接住），本条直接抛异常红（协程向上炸）；或把 应重试 判定删掉
        → `尝试次数 == 1` 红（实际 3）。
        """
        结果 = asyncio.run(带重试对话(_故障通道("解析"), [{"role": "user", "content": "x"}], 3))
        assert 结果["成功"] is False
        assert 结果["尝试次数"] == 1, "解析类不应重试，尝试次数应为 1，实际 %s" % 结果["尝试次数"]
        assert 结果["错误"] == "解析", "解析类应记 解析，实际 %r" % 结果["错误"]


# ---- #5(2) 报告兜底：汇总/写盘异常仍落盘部分报告 ----
class Test报告兜底落盘:
    """#5(2) 补齐条件：汇总或写盘抛异常时，逐条结果仍落盘到 .partial.json。"""

    def test_汇总异常时仍写部分报告(self, tmp_path):
        """结果表含非数值 耗时="坏" → 批量汇总 抛 TypeError；写报告带兜底 应捕获并落
        `.partial.json`（含逐条结果、汇总=空），且返回 空（不崩）。

        反跑改坏点：把 评测驱动.light 写报告带兜底 的 try 去掉（恢复成裸 批量汇总+写盘），
        本条 `报告.partial.json 存在` 红（异常直接炸出、整份报告丢失）。
        """
        结果表 = [{
            "序号": 1, "prompt": "x", "期望答案": "", "打分器": "精确", "输出": "",
            "得分": 0, "耗时": "坏", "尝试次数": 1, "完成轮数": 0, "工具调用次数": 0,
            "错误分类": "", "错误": "", "输入词元": None, "输出词元": None,
        }]
        评测配置 = {"并发上限": 2, "速率上限": 10, "重试次数": 3, "总耗时": 0.5}
        前缀 = str(tmp_path / "报告")
        汇总 = 写报告带兜底(结果表, 评测配置, "mock", 前缀)

        # 主报告(.json)因汇总异常未生成；部分报告必须落盘
        assert 汇总 is None, "汇总异常时应返回 空，实际 %r" % 汇总
        assert not os.path.exists(前缀 + ".json"), "异常时不应写出 主报告.json"
        部分路径 = 前缀 + ".partial.json"
        assert os.path.exists(部分路径), "汇总异常时应落盘 .partial.json"
        部分 = json.load(open(部分路径, encoding="utf-8"))
        # 逐条结果被原样保留（报告不丢数据）
        assert 部分["条目"] == 结果表
        assert 部分["汇总"] is None
        assert 部分["元信息"]["兜底"] is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
