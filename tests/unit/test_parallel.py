# -*- coding: utf-8 -*-
"""R99 路 B · 轻量并发原语验收（LP-D-012）

任务书口径（R99_并发开发任务分发书 · 路 B，方案一块语法）
----------------------------------------------------------
1. 两个 sleep 任务并行，总耗时 ≈ max 而非 sum；
2. 一个任务抛错，块结束 re-raise；
3. 空并行块；
4. 并行块里访问模块级状态（线程安全「不保证」口径）。

红线：
- 不做真异步/事件循环——光明是同步语义，线程池（ThreadPoolExecutor）够了；
- `并行` 刻意不进关键字表：词法层 `并` 是既有关键字（管道连接符），
  `并行上限`/`打印并行` 等复合名切词不能被波及，语句头只劫持
  「并+行+冒号」三连形态（见 parser_stmt._parse_statement_inner 注释）。
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402

# 单任务 sleep 时长选取理由（与任务书验收口径一致）：
# 0.2s × 2 并行 ≈ 0.2s、串行 ≈ 0.4s，两区间不重叠，且总耗时秒级。
睡 = 0.2

_头部 = (
    "从 线程 导入 线程休眠\n"
    "\n"
    f"段落 长任务A(参数):\n"
    f"  线程休眠({睡})\n"
    "  返回 \"A:\" + 参数\n"
    "\n"
    f"段落 长任务B(参数):\n"
    f"  线程休眠({睡})\n"
    "  返回 \"B:\" + 参数\n"
    "\n"
    f"段落 会炸(参数):\n"
    f"  线程休眠({睡})\n"
    "  抛出 新建 错误(\"并行炸:\" + 参数)\n"
    "  返回 0\n"
    "\n"
)


def _compile(主体: str):
    """编译并执行，返回（全局命名空间，主段落引用）。"""
    module = LightParser().parse(_头部 + 主体)
    py_code = PythonCodeGenerator().generate(module)
    ns = {}
    exec(py_code, ns)
    return ns, ns["主"]


class Test路B_验收四用例:
    def test_1_两任务并行_耗时近max非sum(self):
        """任务书硬判据：两个 0.2s 任务并行总耗时 < 0.35s（串行 0.4s+）。"""
        _, 主 = _compile(
            "段落 主():\n"
            "  并行:\n"
            "    任务A 为 长任务A(\"甲\")\n"
            "    任务B 为 长任务B(\"乙\")\n"
            "  返回 任务A + \";\" + 任务B\n"
        )
        t0 = time.monotonic()
        结果 = 主()
        耗时 = time.monotonic() - t0
        assert 结果 == "A:甲;B:乙"
        assert 耗时 < 0.35, f"并行耗时 {耗时:.3f}s，接近串行 sum（>0.35s）说明没真并行"

    def test_2_任务抛错_块结束reraise(self):
        """一个任务抛错，块结束处 re-raise，可被 尝试/捕获 兜住（与路 A 配合）。"""
        _, 主 = _compile(
            "段落 主():\n"
            "  尝试:\n"
            "    并行:\n"
            "      任务A 为 长任务A(\"甲\")\n"
            "      任务B 为 会炸(\"乙\")\n"
            "    返回 \"没兜住\"\n"
            "  捕获 错误 e:\n"
            "    返回 \"兜住: \" + 字符串(e)\n"
        )
        assert 主() == "兜住: 并行炸:乙"

    def test_3_空并行块(self):
        """空块合法，编译为 no-op，不影响后续语句。"""
        _, 主 = _compile(
            "段落 主():\n"
            "  并行:\n"
            "  设 甲 为 \"空块后照常\"\n"
            "  返回 甲\n"
        )
        assert 主() == "空块后照常"

    def test_4_模块级状态_不保证口径但可访问(self):
        """并行块内可访问模块级/闭包状态；线程安全由用户自己加锁（文档口径）。"""
        _, 主 = _compile(
            "段落 记一笔(表, 值):\n"
            "  线程休眠(0.05)\n"
            "  列表追加(表, 值)\n"
            "  返回 0\n"
            "\n"
            "段落 主():\n"
            "  设 表 为 []\n"
            "  并行:\n"
            "    甲 为 记一笔(表, \"x\")\n"
            "    乙 为 记一笔(表, \"y\")\n"
            "  返回 长度(表)\n"
        )
        assert 主() == 2  # 两个任务都写进去了（顺序不保证，条数保证）


class Test路B_零破坏与stdlib:
    def test_并行作标识符_存量用法不回退(self):
        """`设 并行上限 为 4`、`打印并行(...)` 等存量写法必须原样保留。"""
        src = (
            "段落 打印并行(载荷):\n"
            "  返回 \"并:\" + 载荷\n"
            "\n"
            "段落 主():\n"
            "  设 并行上限 为 4\n"
            "  设 报告 为 打印并行(\"测试\")\n"
            "  返回 并行上限\n"
        )
        module = LightParser().parse(src)
        py_code = PythonCodeGenerator().generate(module)
        ns = {}
        exec(py_code, ns)
        assert ns["主"]() == 4

    def test_非冒号形态的并行语句头不被劫持(self):
        """语句头 `并行上限` 没有「并+行+冒号」三连，必须走原路径不报并行块错误。"""
        src = (
            "段落 主():\n"
            "  设 并行上限 为 4\n"
            "  返回 并行上限\n"
        )
        LightParser().parse(src)  # 不应抛

    def test_stdlib_等待_封装(self):
        """stdlib/线程 的 等待(列表)：并发执行别名入口，任一抛错按序 re-raise。"""
        from 线程 import 等待
        结果 = 等待([lambda: 1, lambda: "二", lambda: [3]])
        assert 结果 == [1, "二", [3]]
        with pytest.raises(Exception):
            等待([lambda: 1, (_ for _ in ()).throw(RuntimeError("炸"))])
