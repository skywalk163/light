# -*- coding: utf-8 -*-
"""
段言（Duan）Level 6 词法分析器测试 - 纯缩进语法

验证 Level 6 核心特性：通过缩进层级生成 INDENT/DEDENT token，
块结构不再依赖「结束」关键字。

基于设计规格：docs/superpowers/specs/2026-07-01-level6-type-annotation-design.md
  第四章「纯缩进语法」
"""

import sys
import os

# 添加 src 目录到路径（与 tests/test_lexer.py 一致的导入模式）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from tokens import Token, TokenType


def _tokenize(src):
    """便捷分词辅助：返回去除 EOF 的 token 列表。"""
    return [t for t in Lexer().tokenize(src) if t.type != TokenType.EOF]


def _indent_dedent_sequence(src):
    """提取 INDENT/DEDENT token 的 (类型, 值) 序列。"""
    return [
        (t.type, t.value)
        for t in Lexer().tokenize(src)
        if t.type in (TokenType.INDENT, TokenType.DEDENT)
    ]


# =============================================================================
# T11: 纯缩进语法（INDENT / DEDENT token 生成）
# =============================================================================

def test_simple_if_block_indent():
    """简单 if 块：缩进进入块（INDENT），缩进回退退出块（DEDENT）。

    如果x大于0：
        打印x
    """
    src = "如果x大于0：\n    打印x"
    tokens = _tokenize(src)

    # 验证存在 COLON 标记块开始
    colon_tokens = [t for t in tokens if t.type == TokenType.COLON]
    assert len(colon_tokens) == 1

    # 验证 INDENT / DEDENT 各一个
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 4),
        (TokenType.DEDENT, 0),
    ]

    # 验证 INDENT 之后是块体内容「打印x」
    indent_idx = next(i for i, t in enumerate(tokens) if t.type == TokenType.INDENT)
    assert tokens[indent_idx + 1].type == TokenType.KEYWORD
    assert tokens[indent_idx + 1].value == '打印'
    assert tokens[indent_idx + 2].type == TokenType.IDENTIFIER
    assert tokens[indent_idx + 2].value == 'x'


def test_for_loop_block_indent():
    """循环块（遍历）：缩进进入块体，DEDENT 退出。

    遍历i从1到10：
        打印i
    """
    src = "遍历i从1到10：\n    打印i"
    tokens = _tokenize(src)

    # 验证 INDENT / DEDENT 序列
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 4),
        (TokenType.DEDENT, 0),
    ]

    # 验证块体内容
    indent_idx = next(i for i, t in enumerate(tokens) if t.type == TokenType.INDENT)
    assert tokens[indent_idx + 1].type == TokenType.KEYWORD
    assert tokens[indent_idx + 1].value == '打印'


def test_nested_blocks_if_inside_for():
    """嵌套块：if 块在 for 块内部，应生成两层 INDENT 和两层 DEDENT。

    遍历i从1到10：
        如果i大于5：
            打印i
    """
    src = "遍历i从1到10：\n    如果i大于5：\n        打印i"
    tokens = _tokenize(src)

    # 验证两层 INDENT + 两层 DEDENT
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 4),   # 进入外层 for 块
        (TokenType.INDENT, 8),   # 进入内层 if 块
        (TokenType.DEDENT, 4),   # 退出内层 if 块
        (TokenType.DEDENT, 0),   # 退出外层 for 块
    ]

    # 验证内层块体在第二个 INDENT 之后
    indent_indices = [i for i, t in enumerate(tokens) if t.type == TokenType.INDENT]
    inner_indent_idx = indent_indices[1]
    assert tokens[inner_indent_idx + 1].type == TokenType.KEYWORD
    assert tokens[inner_indent_idx + 1].value == '打印'


def test_mixed_indent_and_explicit_end():
    """混合缩进 + 显式「结束」关键字（向后兼容）。

    如果x大于0：
        打印x
    结束

    纯缩进生成 DEDENT 退出块，「结束」作为 IDENTIFIER 保留兼容。
    """
    src = "如果x大于0：\n    打印x\n结束"
    tokens = _tokenize(src)

    # 验证 DEDENT 在「结束」之前生成（缩进回退到 0）
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 4),
        (TokenType.DEDENT, 0),
    ]

    # 验证「结束」出现在 DEDENT 之后，作为 IDENTIFIER
    dedent_idx = next(i for i, t in enumerate(tokens) if t.type == TokenType.DEDENT)
    end_token = tokens[dedent_idx + 1]
    assert end_token.type == TokenType.IDENTIFIER
    assert end_token.value == '结束'


def test_dedent_after_multiple_nested_blocks():
    """多层嵌套块退出时连续生成多个 DEDENT。

    如果a：
        如果b：
            打印a
        打印b
    打印c

    缩进层级 0 → 4 → 8 → 4 → 0，对应 INDENT(4) INDENT(8) DEDENT(4) DEDENT(0)。
    """
    src = "如果a：\n    如果b：\n        打印a\n    打印b\n打印c"
    tokens = _tokenize(src)

    # 验证完整 INDENT/DEDENT 序列
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 4),   # 进入第一层
        (TokenType.INDENT, 8),   # 进入第二层
        (TokenType.DEDENT, 4),   # 退出第二层（回到第一层）
        (TokenType.DEDENT, 0),   # 退出第一层（回到顶层）
    ]

    # 验证各层块体内容
    # 第二层块体：打印a（在 INDENT(8) 之后）
    indent_indices = [i for i, t in enumerate(tokens) if t.type == TokenType.INDENT]
    second_indent_idx = indent_indices[1]
    assert tokens[second_indent_idx + 1].value == '打印a' or (
        tokens[second_indent_idx + 1].value == '打印' and
        tokens[second_indent_idx + 2].value == 'a'
    )

    # 顶层最后一条语句：打印c（在最后一个 DEDENT 之后）
    dedent_indices = [i for i, t in enumerate(tokens) if t.type == TokenType.DEDENT]
    last_dedent_idx = dedent_indices[-1]
    after_dedent = tokens[last_dedent_idx + 1]
    assert after_dedent.type == TokenType.KEYWORD
    assert after_dedent.value == '打印'


def test_indent_values_track_nesting_depth():
    """INDENT 值反映实际缩进空格数，DEDENT 值反映回到的层级。

    使用不同缩进宽度（2 空格）验证非 4 空格缩进也正确工作。
    """
    src = "如果a：\n  如果b：\n    打印a"
    seq = _indent_dedent_sequence(src)
    assert seq == [
        (TokenType.INDENT, 2),   # 2 空格缩进
        (TokenType.INDENT, 4),   # 4 空格缩进
        (TokenType.DEDENT, 2),   # 回到 2 空格层级
        (TokenType.DEDENT, 0),   # 回到 0 空格层级
    ]
