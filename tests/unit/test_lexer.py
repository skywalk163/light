# -*- coding: utf-8 -*-
"""
光明词法分析器单元测试

测试 src/lexer.py 的词法分析功能
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestLexer(unittest.TestCase):
    """词法分析器测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from lexer import Lexer
            from tokens import TokenType
            cls.Lexer = Lexer
            cls.TokenType = TokenType
        except ImportError as e:
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def test_simple_tokenize(self):
        """测试简单语句词法分析"""
        lexer = self.Lexer('设甲为三。')
        tokens = lexer.tokenize()
        self.assertGreater(len(tokens), 0)
        # 验证生成了预期的 token 类型
        token_types = [t.type for t in tokens]
        self.assertIn(self.TokenType.KEYWORD, token_types)
        self.assertIn(self.TokenType.IDENTIFIER, token_types)
        self.assertIn(self.TokenType.CHINESE_NUM, token_types)
        # 验证关键字值
        token_values = [t.value for t in tokens if t.type == self.TokenType.KEYWORD]
        self.assertIn('设', token_values)
        self.assertIn('为', token_values)

    def test_number_literal(self):
        """测试数字字面量"""
        lexer = self.Lexer('打印 123')
        tokens = lexer.tokenize()
        number_tokens = [t for t in tokens if t.type == self.TokenType.NUMBER]
        self.assertGreater(len(number_tokens), 0)
        self.assertEqual(number_tokens[0].value, 123)

    def test_string_literal(self):
        """测试字符串字面量"""
        lexer = self.Lexer('打印"你好"。')
        tokens = lexer.tokenize()
        string_tokens = [t for t in tokens if t.type == self.TokenType.STRING]
        self.assertGreater(len(string_tokens), 0)
        self.assertIn('你好', [t.value for t in string_tokens])

    def test_chinese_number(self):
        """测试中文数字"""
        lexer = self.Lexer('三加五')
        tokens = lexer.tokenize()
        cn_num_tokens = [t for t in tokens if t.type == self.TokenType.CHINESE_NUM]
        self.assertEqual(len(cn_num_tokens), 2)

    def test_arithmetic_operator_compound_words(self):
        """测试算术运算符复合词不拆分（v4.2 修复）
        "加法"、"减法"、"乘法"、"除法" 应整体识别为标识符，不拆分为关键字+字
        """
        test_cases = [
            ('加法(a, b)', '加法 应整体识别'),
            ('减法(a, b)', '减法 应整体识别'),
            ('乘法(a, b)', '乘法 应整体识别'),
            ('除法(a, b)', '除法 应整体识别'),
        ]
        for code, description in test_cases:
            with self.subTest(code=code, desc=description):
                lexer = self.Lexer(code)
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                # 第一个 token 应该是完整的标识符，不是关键字
                first_token = tokens[0]
                self.assertEqual(first_token.type, self.TokenType.IDENTIFIER,
                               f"{description}: 期望 IDENTIFIER，实际 {first_token.type}: {first_token.value}")

    def test_arithmetic_operator_mid_expression(self):
        """测试算术运算符在表达式中应识别为关键字
        "甲加乙" → [甲][加][乙]，"加" 应识别为关键字
        """
        test_cases = [
            ('甲加乙', ['甲', '加', '乙']),
            ('甲减乙', ['甲', '减', '乙']),
            ('甲乘乙', ['甲', '乘', '乙']),
            ('甲除乙', ['甲', '除', '乙']),
        ]
        for code, expected_values in test_cases:
            with self.subTest(code=code):
                lexer = self.Lexer(code)
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                # 应该有三个 token：标识符、关键字、标识符
                self.assertEqual(len(tokens), 3, f"{code} 应产生3个token，实际 {len(tokens)}")
                self.assertEqual(tokens[0].type, self.TokenType.IDENTIFIER)
                self.assertEqual(tokens[0].value, expected_values[0])
                self.assertEqual(tokens[1].type, self.TokenType.KEYWORD)
                self.assertEqual(tokens[1].value, expected_values[1])
                self.assertEqual(tokens[2].type, self.TokenType.IDENTIFIER)
                self.assertEqual(tokens[2].value, expected_values[2])

    def test_arithmetic_compound_keywords(self):
        """测试双字算术运算符关键字（加上、减去、乘以、除以）"""
        test_cases = [
            ('加上', '加上'),
            ('减去', '减去'),
            ('乘以', '乘以'),
            ('除以', '除以'),
        ]
        for keyword, expected in test_cases:
            with self.subTest(keyword=keyword):
                lexer = self.Lexer(keyword + ' a b')
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                keyword_tokens = [t for t in tokens if t.type == self.TokenType.KEYWORD and t.value == expected]
                self.assertGreater(len(keyword_tokens), 0,
                                 f"关键字 {keyword} 未被正确识别")

    def test_list_literal(self):
        """测试列表字面量"""
        lexer = self.Lexer('设列表为[1, 2, 3]。')
        tokens = lexer.tokenize()
        token_types = [t.type for t in tokens]
        self.assertIn(self.TokenType.LBRACKET, token_types)
        self.assertIn(self.TokenType.RBRACKET, token_types)

    def test_keywords(self):
        """测试关键字识别"""
        test_cases = [
            ('如果', '如果'),
            ('那么', '那么'),
            ('否则', '否则'),
            ('遍历', '遍历'),
            ('返回', '返回'),
            ('打印', '打印'),
        ]
        for keyword, expected in test_cases:
            with self.subTest(keyword=keyword):
                lexer = self.Lexer(keyword + ' x')
                tokens = lexer.tokenize()
                keyword_tokens = [t for t in tokens if t.type == self.TokenType.KEYWORD and t.value == expected]
                self.assertGreater(len(keyword_tokens), 0,
                                 f"关键字 {keyword} 未被正确识别")

    def test_compact_ascii_operator(self):
        """测试 ASCII 标识符后紧跟运算符动词的紧凑写法（n减1）"""
        # 运算符动词（减/等于）不在 ALL_KEYWORDS，只在 VERB_ARITY，
        # 之前会被误并进 ASCII 标识符（n减 → 单个标识符），现已修复
        lexer = self.Lexer('n减1')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'n'),
             (self.TokenType.KEYWORD, '减'),
             (self.TokenType.NUMBER, 1)],
        )
        # 紧凑范围表达式：left至right 不再被并成单个标识符
        lexer = self.Lexer('left至right')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'left'),
             (self.TokenType.KEYWORD, '至'),
             (self.TokenType.IDENTIFIER, 'right')],
        )
        # 合法复合标识符仍应整体合并（evennum集）
        lexer = self.Lexer('evennum集')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'evennum集')],
        )

    def test_eof_token(self):
        """测试 EOF token"""
        lexer = self.Lexer('x')
        tokens = lexer.tokenize()
        self.assertEqual(tokens[-1].type, self.TokenType.EOF)

    def test_empty_source(self):
        """测试空源文件"""
        lexer = self.Lexer('')
        tokens = lexer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, self.TokenType.EOF)


if __name__ == '__main__':
    unittest.main()
