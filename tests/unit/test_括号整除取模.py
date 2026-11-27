# -*- coding: utf-8 -*-
"""T-0537 判据：`(x + y) // z` / `(x + y) % z` 及多层括号形态不得静默丢运算。

背景
----
T-0520 实测（hall 消息 fb98-1795705321818526）报告括号内含加法的表达式后接
`//` / `%` 会被丢运算：`(4 + 1) // 2` → 4（应 2）、`(0 + 10 + 1) // 2` → 10
（应 5）。根因在 `src/code_generator.py` 的二元链迭代折叠 `_fold_binary_spine`：
旧实现只给「整个节点」加括号，低优先级左操作数会被 Python 按自身优先级重读。

T-0529 修了 `_fold_binary_spine` 的左括号（比较/逻辑混排），顺带让卡面三条基础
样例在 main 上恢复正确；但同一修复依赖的 `_is_fully_parenthesized` 助手存在
**误判**：它只检查「某个括号对恰在末位闭合」，不要求最外层那一对从串首开始，
于是 `a + (b + c)` 被误判为「已完整加括号」。结果多层括号形态仍然丢运算：

    ((a + (b + c)) // a)   →   ((a + (b + c) // a))   ✗  Python 读成 a + ((b+c)//a)

T-0537 修 `_is_fully_parenthesized` 补上「串首必须是 `(`」这一必要条件。本文件
把两类形态都钉死：卡面基础样例（防回归）+ 多层括号样例（反证有效，退 HEAD 转红）。

判据口径
--------
只断**可观察输出**：把程序真跑一遍看打印值，不断言生成代码的文本形态。每条
用例都走权威 src 后端（LightParser + PythonCodeGenerator）编译并 exec，与
tests/unit/test_括号比较优先级.py 同一条管线。
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
    """用权威 src 后端编译并执行，返回程序打印出来的所有非空行。"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    module = LightParser().parse(源代码)
    assert module is not None, "解析失败"
    py = PythonCodeGenerator().generate(module)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(py, "<t0537>", "exec"), {"__name__": "__main__"})
    return [ln for ln in out.getvalue().replace("\r\n", "\n").strip().split("\n") if ln]


def _求值(表达式, 前置="", 后缀=""):
    """把 `打印(<表达式>)` 编成最小程序运行，返回输出末行。"""
    源 = 前置 + "打印(%s)\n" % 表达式 + 后缀
    return _编译并运行(源)[-1]


# ── 1. 卡面基础样例（T-0520 实测，T-0529 后已正确，防回归） ──────────────
@pytest.mark.parametrize("表达式, 期望", [
    ("(4 + 1) // 2", "2"),
    ("(0 + 10 + 1) // 2", "5"),
    ("(100 + 50) % 4294967296", "150"),
    ("(100 + 50) % 7", "3"),
    ("(9 - 3) // 2", "3"),
    ("(9 - 3) % 5", "1"),
])
def test_卡面基础样例(表达式, 期望):
    assert _求值(表达式) == 期望, f"`{表达式}` 结果错误"


# ── 2. 多层括号 + 整除/取模（T-0537 真正修的形态，退 HEAD 必红） ──────────
# a=7, b=3, c=2。每条都选成「正确值与错误优先级下的值不同」，判错必现。
_前置 = "设 a 为 7\n设 b 为 3\n设 c 为 2\n"
@pytest.mark.parametrize("表达式, 期望", [
    ("(a + (b + c)) // a", "1"),     # 正确 12//7=1；丢括号变 a+((b+c)//a)=7
    ("(a + (b + c)) % a", "5"),      # 正确 12%7=5；丢括号变 a+((b+c)%a)=12
    ("(a + (b - c)) // a", "1"),     # 正确 8//7=1；丢括号变 7
    ("(a + (b - c)) % a", "1"),      # 正确 8%7=1；丢括号变 8
    ("(a - (b + c)) // a", "0"),     # 正确 2//7=0；丢括号变 7
    ("(a - (b - c)) // a", "0"),     # 正确 6//7=0；丢括号变 7
    ("(a + (b * c)) // a", "1"),     # 正确 13//7=1；丢括号变 7
    ("(a + (b * c)) % a", "6"),      # 正确 13%7=6；丢括号变 13
    ("(a + (b // c)) // a", "1"),    # 正确 8//7=1；丢括号变 7
    ("(a + (b % c)) % a", "1"),      # 正确 8%7=1；丢括号变 8
    ("((a + b) + c) // a", "1"),     # 连续加法后整除：12//7=1，丢括号变 7
    ("((a + b) + c) % a", "5"),      # 连续加法后取模：12%7=5，丢括号变 12
])
def test_多层括号整除取模不丢运算(表达式, 期望):
    assert _求值(表达式, 前置=_前置) == 期望, (
        f"`{表达式}` 结果错误：多层括号的左操作数被重读，// 或 % 落到内层。")


# ── 3. 与乘法/比较混排 + 拆中间变量等价性 ──────────────────────────────
def test_与乘法混排仍然正确():
    assert _求值("(a + (b + c)) * a", 前置=_前置) == "84"   # (7+5)*7
    assert _求值("(a - (b + c)) * a", 前置=_前置) == "14"   # (7-5)*7


def test_与比较混排仍然正确():
    assert _求值("(a + (b + c)) // a == 1", 前置=_前置) == "True"
    assert _求值("(a + (b + c)) % a == 5", 前置=_前置) == "True"


def test_拆成中间变量写法等价():
    """拆成中间变量是 T-0520 的规避写法，两版都必须正确且与括号写法等价。"""
    括号版 = _求值("(a + (b + c)) // a", 前置=_前置)
    中间变量版 = _编译并运行(
        _前置 + "设 和 为 a + (b + c)\n打印(和 // a)\n")[-1]
    assert 括号版 == 中间变量版 == "1"
    括号版2 = _求值("(a + (b + c)) % a", 前置=_前置)
    中间变量版2 = _编译并运行(
        _前置 + "设 和 为 a + (b + c)\n打印(和 % a)\n")[-1]
    assert 括号版2 == 中间变量版2 == "5"


def test_右操作数为括号不受影响():
    """`a // (b + c)` 的括号在右边，T-0529/T-0537 都不该改坏它。"""
    assert _求值("a // (b + c)", 前置=_前置) == "1"   # 7//5
    assert _求值("a % (b + c)", 前置=_前置) == "2"    # 7%5
