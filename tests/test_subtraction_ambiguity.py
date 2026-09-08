# -*- coding: utf-8 -*-
"""
任务 B：P1 减法运算符歧义 + P2 缩进规范增强

P1（减法歧义，src/parser_expr.py / src/parser_core.py / src/lexer.py）：
  - `a-1`（无空格）中的 `-` 必须被解析为 二元减法（BinaryOp），而不是一元负号。
    边界样式 `a-1` / `a - 1` / `a- 1` / `a -1` 四种写法都必须输出 4。
  - 行首 `-1` 仍为 一元负号：`打印(-1)` 输出 -1。
  - 函数实参 `加一(-1)` 中的 `-1` 为一元负号，输出 0。

P2（缩进规范增强，src/lexer.py）：
  - 行首缩进同时混用 Tab 与空格 → 抛出 LexerError（信息含「缩进混合了 Tab 和空格」）。
  - 缩进层级直接跳变超过一个层级（如 0→12）→ 通过 lexer.warnings 记录告警，不阻断解析。
"""

import sys
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator
from lexer import Lexer, LexerError


def _run(src: str) -> str:
    """编译并执行光明源码，返回 stdout（strip 后）。失败返回 ERR:类型:信息。"""
    parser = LightParser()
    module = parser.parse(src)
    gen = PythonCodeGenerator()
    code = gen.generate(module)
    local_ns = {}
    global_ns = {}
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, global_ns, local_ns)
    except Exception as e:
        return f"ERR:{type(e).__name__}:{e}"
    return stdout.getvalue().strip()


def _lexer_warnings(src: str):
    """分词后返回 lexer.warnings 列表（每次 tokenize 调用自动重置）。"""
    lexer = Lexer()
    lexer.tokenize(src)
    return list(lexer.warnings)


# =============================================================================
# P1：减法运算符歧义（`-` 应为二元减法而非一元负号）
# =============================================================================

def test_subtraction_no_space_a_minus_1():
    """`a-1` 无空格：应解析为二元减法，输出 4。"""
    assert _run('设 a 为 5。\n打印(a-1)') == '4'


def test_subtraction_spaces_both_sides():
    """`a - 1`：标准空格写法，输出 4。"""
    assert _run('设 a 为 5。\n打印(a - 1)') == '4'


def test_subtraction_space_after_minus():
    """`a- 1`：减号后带空格，输出 4。"""
    assert _run('设 a 为 5。\n打印(a- 1)') == '4'


def test_subtraction_space_before_minus():
    """`a -1`：减号前带空格，输出 4。"""
    assert _run('设 a 为 5。\n打印(a -1)') == '4'


def test_unary_minus_line_start():
    """行首 `-1` 仍为 一元负号：`打印(-1)` 输出 -1。"""
    assert _run('打印(-1)') == '-1'


def test_unary_minus_function_argument():
    """函数实参 `加一(-1)` 中的 `-1` 为一元负号：-1 + 1 = 0。"""
    assert _run('段落 加一(x):\n    返回 x 加 1\n\n打印 加一(-1)') == '0'


# =============================================================================
# P2：缩进规范增强
# =============================================================================

def test_mixed_tab_space_indent_raises_lexer_error():
    """行首缩进同时混用 Tab 与空格 → 抛出 LexerError（信息含「缩进混合了 Tab 和空格」）。"""
    src = "如果x大于0：\n\t    打印x"
    raised = False
    try:
        Lexer().tokenize(src)
    except LexerError as e:
        raised = True
        assert '缩进混合了 Tab 和空格' in str(e), f"错误信息不符: {e}"
    assert raised, '应当抛出 LexerError'


def test_indent_jump_emits_warning():
    """缩进从 0 直接跳变到 12（12 > 4）→ 记录告警，且不阻断解析。"""
    src = "如果x大于0：\n            打印x"
    warnings = _lexer_warnings(src)
    assert any('直接跳变到 12' in w for w in warnings), \
        f"未检测到缩进跳变告警: {warnings}"


def test_no_warning_on_single_level_indent():
    """正常单层级缩进（0→4）不产生缩进跳变告警。"""
    src = "如果x大于0：\n    打印x"
    warnings = _lexer_warnings(src)
    assert all('直接跳变' not in w for w in warnings), \
        f"不应出现缩进跳变告警: {warnings}"