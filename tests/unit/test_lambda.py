# -*- coding: utf-8 -*-
"""R129-C（M2）· lambda 语法糖测试：`匿名(x): 表达式`

背景（known_issues G2）：AI 写光明代码时第一反应常写 `匿名(x): x + 1`，
此前解析器在 `:` 处报「无法识别的语法元素」。R129-C 在 `parser_expr.py`
的冒号风格匿名函数通道（R70-A/L-173）上新增 `匿名` 引导词，与既有
`函数(x): 表达式` 同义，产出 `LambdaExpression`。

范围：**单表达式** lambda，不支持多行体（多行体继续用命名段落）。
`匿名` 刻意不升关键字，用「值==匿名 且 后随 `(`」前视守卫识别，
不命中即回退为普通标识符——本文件末两条用例专门守这条回退路径。

判据（R129 任务书 §4.2，均为实跑核对）：
  · 条件映射([{"年龄":3},{"年龄":1}], 匿名(x): x["年龄"]) -> [3, 1]
  · 分组([1,2,3,4], 匿名(x): x % 2)                      -> {1: [1, 3], 0: [2, 4]}
  · 条件映射([1,2,3], 匿名(x): x*2)                       -> [2, 4, 6]
"""
import io
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _run_light(code: str) -> str:
    """解析 → 生成 Python → exec，返回标准输出（strip 后）。

    给 exec 命名空间注入 `__file__`，让生成头部的 stdlib 路径探测
    （`dirname(__file__)/stdlib`）稳定落到仓根 stdlib，与 cwd 无关。
    """
    ast = LightParser().parse(code)
    py_code = PythonCodeGenerator().generate(ast)
    namespace = {
        "__name__": "__main__",
        "__file__": os.path.join(_ROOT, "_r129_lambda_probe.py"),
    }
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(py_code, "<r129-lambda>", "exec"), namespace)
        return sys.stdout.getvalue().strip()
    finally:
        sys.stdout = old_stdout


# ── §4.2 三条硬判据（实跑基准）────────────────────────────────────────────────
def test_条件映射_匿名取字典键():
    """条件映射 + 匿名(x): x["年龄"] → 列表 [3, 1]（实跑形态）。"""
    code = (
        "从 集合操作 导入 条件映射\n"
        "打印(条件映射([{\"年龄\":3},{\"年龄\":1}], 匿名(x): x[\"年龄\"]))"
    )
    assert _run_light(code) == "[3, 1]"


def test_分组_匿名奇偶():
    """分组 + 匿名(x): x % 2 → {1: [1, 3], 0: [2, 4]}（键函数真实生效）。"""
    code = (
        "从 集合操作 导入 分组\n"
        "打印(分组([1,2,3,4], 匿名(x): x % 2))"
    )
    assert _run_light(code) == "{1: [1, 3], 0: [2, 4]}"


def test_条件映射_匿名乘二():
    """条件映射 + 匿名(x): x*2 → [2, 4, 6]。"""
    code = (
        "从 集合操作 导入 条件映射\n"
        "打印(条件映射([1,2,3], 匿名(x): x*2))"
    )
    assert _run_light(code) == "[2, 4, 6]"


# ── 赋值 / 参数形态 ──────────────────────────────────────────────────────────
def test_匿名赋值后调用_单参数():
    """`设 翻倍 为 匿名(x): x * 2` 后 `翻倍(21)` → 42。"""
    code = "设 翻倍 为 匿名(x): x * 2\n打印(翻倍(21))"
    assert _run_light(code) == "42"


def test_匿名_双参数():
    """双参数匿名 `匿名(x, y): x 加 y` → 7。"""
    code = "设 求和 为 匿名(x, y): x 加 y\n打印(求和(3, 4))"
    assert _run_light(code) == "7"


def test_匿名_零参数():
    """零参数匿名 `匿名(): 42` → 42。"""
    code = "设 常量 为 匿名(): 42\n打印(常量())"
    assert _run_light(code) == "42"


def test_匿名_体内算术表达式():
    """体内为复合表达式 `匿名(x): x * 2 加 1` → 7。"""
    code = "设 变换 为 匿名(x): x * 2 加 1\n打印(变换(3))"
    assert _run_light(code) == "7"


def test_匿名_体内下标取值():
    """体内含下标 `匿名(记录): 记录[\"分数\"]` → 95。"""
    code = "设 取值 为 匿名(记录): 记录[\"分数\"]\n打印(取值({\"分数\": 95}))"
    assert _run_light(code) == "95"


def test_匿名_直接内联为实参():
    """不先赋值、直接内联进调用实参 → [10, 20, 30]。"""
    code = (
        "从 集合操作 导入 条件映射\n"
        "打印(条件映射([1,2,3], 匿名(x): x * 10))"
    )
    assert _run_light(code) == "[10, 20, 30]"


# ── 与 `函数(x):` 引导词等价 ────────────────────────────────────────────────
def test_匿名与函数引导词结果一致():
    """同一表达式，`匿名(x):` 与 `函数(x):` 产出相同结果。"""
    head = "从 集合操作 导入 条件映射\n"
    via_anon = _run_light(head + "打印(条件映射([1,2,3], 匿名(x): x * 2))")
    via_fn = _run_light(head + "打印(条件映射([1,2,3], 函数(x): x * 2))")
    assert via_anon == via_fn == "[2, 4, 6]"


# ── 前视守卫回退护栏：`匿名` 仍是合法普通标识符 ─────────────────────────────
def test_匿名可作普通变量名():
    """`匿名` 未构成 `匿名(…) :` 形状时，退回普通标识符（变量名）→ 5。"""
    code = "设 匿名 为 5\n打印(匿名)"
    assert _run_light(code) == "5"


def test_匿名可作命名段落并正常调用():
    """用户自定义 `段落 匿名(x):` 后调用 `匿名(5)`，不被语法糖截胡 → 9。"""
    code = "段落 匿名(x):\n  返回 x 加 4\n打印(匿名(5))"
    assert _run_light(code) == "9"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))