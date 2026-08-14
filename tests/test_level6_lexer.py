# -*- coding: utf-8 -*-
"""
段言（Duan）Level 6 词法分析器测试 - 无空格分词

验证 Level 6 核心特性：最长前缀匹配（longest-prefix matching），
使语句内关键字与标识符紧密相连时仍能正确拆分。

基于设计规格：docs/superpowers/specs/2026-07-01-level6-type-annotation-design.md
  第二章「无空格分词」
"""

import sys
import os

# 添加 src 目录到路径（与 tests/test_lexer.py 一致的导入模式）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from lexer import Lexer
from tokens import Token, TokenType


def _tokenize(src):
    """便捷分词辅助：返回去除 EOF 的 token 列表。"""
    return [t for t in Lexer().tokenize(src) if t.type != TokenType.EOF]


def _types_and_values(src):
    """返回 [(TokenType, value), ...] 列表（去除 EOF / NEWLINE）。"""
    return [
        (t.type, t.value)
        for t in Lexer().tokenize(src)
        if t.type not in (TokenType.EOF, TokenType.NEWLINE)
    ]


# =============================================================================
# T10: 无空格分词（最长前缀匹配）
# =============================================================================

def test_no_space_assignment():
    """设x为10 → 设(KEYWORD) + x(IDENTIFIER) + 为(KEYWORD) + 10(NUMBER)

    关键字「设」「为」与标识符「x」、数字「10」之间无空格，
    通过最长前缀匹配自动拆分。
    """
    pairs = _types_and_values("设x为10")
    assert pairs == [
        (TokenType.KEYWORD, '设'),
        (TokenType.IDENTIFIER, 'x'),
        (TokenType.KEYWORD, '为'),
        (TokenType.NUMBER, 10),
    ]


def test_no_space_if_condition():
    """如果x大于0 → 如果(KEYWORD) + x(IDENTIFIER) + 大于(KEYWORD) + 0(NUMBER)

    双字关键字「如果」「大于」在无空格语句中被正确识别。
    """
    pairs = _types_and_values("如果x大于0")
    assert pairs == [
        (TokenType.KEYWORD, '如果'),
        (TokenType.IDENTIFIER, 'x'),
        (TokenType.KEYWORD, '大于'),
        (TokenType.NUMBER, 0),
    ]


def test_no_space_loop_with_range():
    """循环i从1到10 → 从(KEYWORD) + 1(NUMBER) + 到(KEYWORD) + 10(NUMBER) 正确拆分

    注意：「循环」不是关键字（不在 ALL_KEYWORDS / VERB_ARITY 中），因此
    「循环i」被合并为单个 IDENTIFIER。核心验证点是范围关键字「从」「到」
    和数字在无空格情况下仍被最长前缀匹配正确拆出。
    """
    pairs = _types_and_values("循环i从1到10")
    # 「循环i」作为单个标识符（循环非关键字）
    assert pairs[0] == (TokenType.IDENTIFIER, '循环i')
    # 范围关键字与数字正确拆分
    assert (TokenType.KEYWORD, '从') in pairs
    assert (TokenType.KEYWORD, '到') in pairs
    assert (TokenType.NUMBER, 1) in pairs
    assert (TokenType.NUMBER, 10) in pairs
    # 验证完整顺序
    assert pairs == [
        (TokenType.IDENTIFIER, '循环i'),
        (TokenType.KEYWORD, '从'),
        (TokenType.NUMBER, 1),
        (TokenType.KEYWORD, '到'),
        (TokenType.NUMBER, 10),
    ]


def test_no_space_traverse_with_range():
    """遍历i从1到10 → 遍历(KW) + i(ID) + 从(KW) + 1(NUM) + 到(KW) + 10(NUM)

    「遍历」是关键字，因此与标识符「i」正确分离，
    完整演示无空格分词对关键字 + 标识符 + 范围的拆分能力。
    """
    pairs = _types_and_values("遍历i从1到10")
    assert pairs == [
        (TokenType.KEYWORD, '遍历'),
        (TokenType.IDENTIFIER, 'i'),
        (TokenType.KEYWORD, '从'),
        (TokenType.NUMBER, 1),
        (TokenType.KEYWORD, '到'),
        (TokenType.NUMBER, 10),
    ]


def test_mixed_space_and_no_space():
    """设 x 为10 → 设(KW) + x(ID) + 为(KW) + 10(NUM)

    混合空格/无空格写法（向后兼容）：「设」「为」前有空格，
    「为10」无空格，仍能正确分词。
    """
    pairs = _types_and_values("设 x 为10")
    assert pairs == [
        (TokenType.KEYWORD, '设'),
        (TokenType.IDENTIFIER, 'x'),
        (TokenType.KEYWORD, '为'),
        (TokenType.NUMBER, 10),
    ]


def test_string_after_keyword_no_space():
    """打印"你好" → 打印(KEYWORD) + "你好"(STRING)

    关键字后紧跟字符串字面量（无空格），应正确识别。
    """
    pairs = _types_and_values('打印"你好"')
    assert pairs == [
        (TokenType.KEYWORD, '打印'),
        (TokenType.STRING, '你好'),
    ]


@pytest.mark.skip(reason="反引号转义机制尚未实现（Level 6 规格第2.3节），当前词法分析器对 '`' 抛出 LexerError")
def test_backtick_escape():
    """`设x为10` → 单个 IDENTIFIER（反引号转义）

    Level 6 规格第2.3节：反引号包裹的内容强制作为标识符，
    用于需要用关键字做变量名的场景。此特性尚未实现。
    """
    tokens = _tokenize("`设x为10`")
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == '设x为10'
