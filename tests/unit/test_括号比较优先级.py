# -*- coding: utf-8 -*-
"""T-0529 判据：`(A 或 B)` / `(A 且 B)` 这类括号组作为**比较左操作数**时不能丢括号。

背景
----
R225（T-0445）把二元链改成「左撇链拆开 + 迭代折叠」（`_fold_binary_spine`），
堆栈深度与链长解耦；但折叠时 `need_parens` 只给**整个节点**加了外层括号：

    如果 (甲 或 乙) == 假      ->    生成  (甲 or 乙 == False)      ✗

Python 按自己的优先级把它重读成 `甲 or (乙 == False)`，条件静默反了 ——
不报错、不抛异常，守卫直接失效。递归基线（`_generate_binary_chain_recursive`）
没有这个问题：它的左操作数已由 `_generate_expr` 带好括号，所以这属于迭代路径
独有的回归，不是「光明一直如此」。

判据口径
--------
只断**可观察输出**（把程序真跑一遍看它走哪条分支），不断言生成代码的文本形态——
文本里多一层少一层括号都是合法实现细节，语义才对是硬要求。每条用例都选成
「按正确答案走 A 分支、按错误优先级走 B 分支」，判错必现。
"""
import contextlib
import io
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _编译并运行(源代码):
    """用权威 src 后端编译并执行，返回程序打印出来的所有行。"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    module = LightParser().parse(源代码)
    assert module is not None, "解析失败"
    py = PythonCodeGenerator().generate(module)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(py, "<t0529>", "exec"), {"__name__": "__main__"})
    return out.getvalue().replace("\r\n", "\n").strip().split("\n")


def _分支(条件表达式):
    """跑一条 `如果 <条件表达式>:` 的最小程序，返回走了哪一支（`对` / `否则`）。"""
    源 = "如果 %s:\n  打印(\"对\")\n否则:\n  打印(\"否则\")\n" % 条件表达式
    return _编译并运行(源)[-1]


# 期望值按**光明语法**（括号先结合、再比较）算，与 Python 自己的优先级一致：
#   (真 或 假) == 假   ->  真 == 假  ->  False  ->  走 否则
#   (真 或 真) == 假   ->  真 == 假  ->  False  ->  走 否则
#   (假 且 真) == 假   ->  假 == 假  ->  True   ->  走 对
#   (真 且 假) == 假   ->  假 == 假  ->  True   ->  走 对
@pytest.mark.parametrize("条件表达式, 期望", [
    ("(真 或 假) == 假", "否则"),
    ("(真 或 真) == 假", "否则"),
    ("(假 且 真) == 假", "对"),
    ("(真 且 假) == 假", "对"),
    # 只多一层括号不能改变结论（同一处括号组路径）
    ("((真 或 假) == 假)", "否则"),
    # 与 `== 真` / `!= 假` 的组合同样要保括号
    ("(真 或 假) != 假", "对"),
    # 同优先级比较（Python 链式比较语义不同）：(1 == 2) == 假 必须整体成组
    ("(1 == 2) == 假", "对"),
    # (真 或 假) 后面接乘法：低优先级左操作数必须成组
    ("((真 或 假) + 0) == 0", "否则"),
])
def test_括号组作比较左操作数_语义不反转(条件表达式, 期望):
    assert _分支(条件表达式) == 期望, (
        f"`如果 {条件表达式}:` 走错了分支：期望 {期望}。"
        "多半个 `==` 括号组被摊平成了 `甲 or (乙 == 假)`（T-0529 的迭代折叠丢括号）。"
    )


def test_先赋值再比较_对照(  ):
    """对照组：先把括号组赋给变量再比较，两版都对——用来区分「算术错了」与「括号丢了」。"""
    源 = '设 组 为 (真 或 假)\n如果 组 == 假:\n  打印("对")\n否则:\n  打印("否则")\n'
    assert _编译并运行(源)[-1] == "否则"


def test_无括号的普通逻辑与算术链不变():
    """不带括号组的普通形态不能被这次修复改坏（防止把 or/and 的结合性一起翻掉）。"""
    assert _分支("真 或 假") == "对"
    assert _分支("真 且 假") == "否则"
    assert _编译并运行('设 甲 为 1 + 2 * 3\n打印(甲)\n')[-1] == "7"
    assert _编译并运行('设 甲 为 (1 + 2) * 3\n打印(甲)\n')[-1] == "9"
    assert _编译并运行('设 甲 为 1 - 2 - 3\n打印(甲)\n')[-1] == "-4"
