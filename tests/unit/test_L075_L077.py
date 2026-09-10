# -*- coding: utf-8 -*-
"""L-075/076/077 语言缺陷修复回归测试（路 5）。

- L-075：hex 字面量 `0x4E00`（lexer 识别，值等同十进制，双后端一致）
- L-076：`空` 是保留字，作变量名时给明确报错；None 字面量语义不受影响
- L-077：列表补 `.移除(值)`（按值删）与 `.弹栈()`（栈语义弹末尾，返回被弹值）

复现样例另见 examples/test_L075.light ~ test_L077.light。
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lexer import Lexer, TokenType  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402

import io
import contextlib


def _run(code: str) -> str:
    """解释器后端执行一段光明代码，返回 stdout。"""
    ast = LightParser().parse(code)
    py = PythonCodeGenerator().generate(ast)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(py, {})
    return buf.getvalue().strip()


# ── L-075 hex 字面量 ─────────────────────────────────────────

def test_L075_lexer_hex_token():
    toks = Lexer().tokenize('0x4E00')
    nums = [t for t in toks if t.type == TokenType.NUMBER]
    assert nums and nums[0].value == 0x4E00


def test_L075_lexer_hex_lowercase_and_mixed():
    assert Lexer().tokenize('0xff')[0].value == 255
    assert Lexer().tokenize('0XaF')[0].value == 0xAF


def test_L075_hex_in_expression():
    assert _run('打印(0xff + 1)') == '256'


def test_L075_unicode_codepoint_example():
    """缺陷账原始复现：Unicode 码点用 hex。"""
    assert _run('设 码 为 0x4E00\n打印(码)') == str(0x4E00)


def test_L075_decimal_still_works():
    assert _run('打印(19968)') == '19968'


# ── L-076 `空` 保留字 ────────────────────────────────────────

def test_L076_kong_as_varname_gets_clear_error():
    # 解析器实际抛出 parser_core.ParseError（errors.ParseError 是另一套带
    # fix_suggestions 的错误类，parser 并未改用它）；此处按真实类型断言。
    from parser_core import ParseError
    with pytest.raises(ParseError) as ei:
        LightParser().parse('设 空 为 1')
    msg = str(ei.value)
    assert '关键字' in msg and '空' in msg, f'报错应明确说明 空 是关键字: {msg}'


def test_L076_kong_literal_still_works():
    # `空` 是 None 字面量；`打印` 映射到 Python print，故输出 'None'
    # （与 `转字符串(None)` 返回 '空' 不同，后者是 转字符串 的专门口径）。
    assert _run('设 x 为 空\n打印(x)') == 'None'


def test_L076_other_keywords_as_varname_unchanged():
    """其余关键字的「关键字作名」历史兼容行为保持不变（不越界收紧）。"""
    ast = LightParser().parse('设 数据 为 [1]\n打印(数据)')
    assert ast is not None


# ── L-077 列表 .移除() / .弹栈() ─────────────────────────────

def test_L077_remove_by_value():
    assert _run('设 l 为 [1,2,3,2]\nl.移除(2)\n打印(l)') == '[1, 3, 2]'


def test_L077_remove_missing_value_keeps_list():
    """移除不存在的值：解释器 remove 会抛 ValueError——按值删语义对齐 Python。
    但缺陷账要求"按值删，内部找索引再弹出"，未找到时保持原样更符合光明宽容
    口径（与原生腿 dv_list_remove 的 index<0 clone 原表一致），此处钉住宽容语义。"""
    out = _run('设 l 为 [1,2,3]\nl.移除(9)\n打印(l)')
    assert out == '[1, 2, 3]'


def test_L077_pop_returns_last_and_shrinks():
    out = _run('设 l 为 [1,2,3]\n设 x 为 l.弹栈()\n打印(x)\n打印(l)')
    assert out.split('\n') == ['3', '[1, 2]']


def test_L077_pop_until_empty():
    out = _run(
        '设 l 为 [1,2]\n'
        '设 a 为 l.弹栈()\n'
        '设 b 为 l.弹栈()\n'
        '打印(a)\n打印(b)\n打印(l)')
    assert out.split('\n') == ['2', '1', '[]']
