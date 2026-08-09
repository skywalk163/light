"""
光明（Light）词法分析器测试

验证决策29的三层分词机制：
1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
3. 元数驱动参数收集
"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from tokens import Token, TokenType


def test_basic_keywords():
    """测试基本关键字识别"""
    lexer = Lexer()
    
    # 测试赋值关键字"设"（旧"定义"已迁移为"设"）
    tokens = lexer.tokenize("设甲为三。")
    print("测试1: 设甲为三。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")
    
    assert tokens[0].type == TokenType.KEYWORD
    assert tokens[0].value == "设"
    print("  [OK] '设' 被正确识别为关键字")
    
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].value == "甲"
    print("  [OK] '甲' 被正确识别为标识符")
    
    print()


def test_no_space_separation():
    """测试无空格分词"""
    lexer = Lexer()
    
    # 核心测试：甲加1 应该分为 [甲] [加] [1]
    tokens = lexer.tokenize("甲加1。")
    print("测试2: 甲加1。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")
    
    assert len([t for t in tokens if t.type != TokenType.EOF and t.type not in (TokenType.NEWLINE,)]) == 4, \
        f"期望4个token（标识符、关键字、数字、句号），得到 {len(tokens)}"
    
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "甲"
    print("  [OK] '甲' 被正确分离")
    
    assert tokens[1].type == TokenType.KEYWORD
    assert tokens[1].value == "加"
    print("  [OK] '加' 被正确识别为关键字")
    
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].value == 1
    print("  [OK] '1' 被正确识别为数字")
    
    print()


def test_keyword_priority():
    """测试关键字优先匹配"""
    lexer = Lexer()
    
    # 定义甲 → [定义] [甲]
    tokens = lexer.tokenize("定义甲。")
    print("测试3: 定义甲。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")
    
    assert tokens[0].type == TokenType.KEYWORD
    assert tokens[0].value == "定义"
    print("  [OK] '定义' 被正确识别（双字关键字优先匹配）")
    
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].value == "甲"
    print("  [OK] '甲' 被正确分离")
    
    print()


def test_if_statement():
    """测试条件语句"""
    lexer = Lexer()
    
    # 如果甲大于乙那么打印甲。
    tokens = lexer.tokenize("如果甲大于乙那么打印甲。")
    print("测试4: 如果甲大于乙那么打印甲。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    # 验证关键字序列
    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")
    
    assert "如果" in keywords, "应该识别到 '如果'"
    assert "大于" in keywords, "应该识别到 '大于'"
    assert "那么" in keywords, "应该识别到 '那么'"
    assert "打印" in keywords, "应该识别到 '打印'"
    print("  [OK] 所有关键字被正确识别")
    
    print()


def test_multiple_keywords():
    """测试多个连续关键字"""
    lexer = Lexer()
    
    # 遍历列表映射筛选
    tokens = lexer.tokenize("遍历列表映射筛选")
    print("测试5: 遍历列表映射筛选")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")
    
    # 注意："列表"不是关键字，应该作为标识符
    assert "遍历" in keywords
    assert "映射" in keywords
    assert "筛选" in keywords
    print("  [OK] 多个关键字被正确识别")
    
    print()


def test_chinese_numbers():
    """测试中文数字"""
    lexer = Lexer()
    
    # 甲加三
    tokens = lexer.tokenize("甲加三。")
    print("测试6: 甲加三。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "甲"
    print("  [OK] '甲' 被正确识别")
    
    assert tokens[1].type == TokenType.KEYWORD
    assert tokens[1].value == "加"
    print("  [OK] '加' 被正确识别")
    
    assert tokens[2].type == TokenType.CHINESE_NUM
    assert tokens[2].value == 3
    print("  [OK] '三' 被识别为中文数字")
    
    print()


def test_symbols():
    """测试符号识别"""
    lexer = Lexer()
    
    # 甲，乙，丙。
    tokens = lexer.tokenize("甲，乙，丙。")
    print("测试7: 甲，乙，丙。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    commas = [t for t in tokens if t.type == TokenType.COMMA]
    assert len(commas) == 2, "应该有2个逗号"
    print("  [OK] 逗号被正确识别")
    
    dots = [t for t in tokens if t.type == TokenType.PERIOD]
    assert len(dots) == 1, "应该有1个句号"
    print("  [OK] 句号被正确识别")
    
    print()


def test_complex_expression():
    """测试复杂表达式"""
    lexer = Lexer()
    
    # 设甲为三加五。
    tokens = lexer.tokenize("设甲为三加五。")
    print("测试8: 设甲为三加五。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")
    
    assert "设" in keywords
    assert "为" in keywords
    assert "加" in keywords
    print("  [OK] 复杂表达式被正确解析")
    
    print()


def test_indentation():
    """测试缩进处理"""
    lexer = Lexer()
    
    source = """如果甲大于乙：
    打印甲。
否则：
    打印乙。"""
    
    tokens = lexer.tokenize(source)
    print("测试9: 缩进处理")
    for tok in tokens:
        if tok.type not in (TokenType.EOF, TokenType.NEWLINE):
            print(f"  {tok}")
    
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    
    print(f"  INDENT 数量: {len(indents)}")
    print(f"  DEDENT 数量: {len(dedents)}")
    
    print()


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("光明词法分析器测试")
    print("=" * 60)
    print()
    
    try:
        test_basic_keywords()
        test_no_space_separation()
        test_keyword_priority()
        test_if_statement()
        test_multiple_keywords()
        test_chinese_numbers()
        test_symbols()
        test_complex_expression()
        test_indentation()
        
        print("=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"✗ 测试失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
