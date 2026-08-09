# -*- coding: utf-8 -*-
"""
光明语法解析器单元测试

测试 src/light_parser_v3.py 的语法分析功能
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestParser(unittest.TestCase):
    """语法解析器测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from light_parser_v3 import LightParser
            cls.Parser = LightParser
        except ImportError as e:
            raise unittest.SkipTest(f"Parser 模块不可用: {e}")

    def test_variable_declaration(self):
        """测试变量声明"""
        parser = self.Parser()
        code = '设甲为123。'
        module = parser.parse(code)
        self.assertIsNotNone(module)
        self.assertGreater(len(module.statements), 0)

    def test_implicit_variable_declaration(self):
        """测试隐式变量声明"""
        parser = self.Parser()
        code = '甲等于123。'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_function_definition(self):
        """测试函数定义"""
        parser = self.Parser()
        code = '段落 加一 接收 数：\n    返回 数 加 1'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_if_statement(self):
        """测试条件语句"""
        parser = self.Parser()
        code = '如果 x 大于 0 那么：\n    打印 x'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_foreach_statement(self):
        """测试遍历语句"""
        parser = self.Parser()
        code = '遍历 项 在 列表：\n    打印 项'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_while_statement(self):
        """测试当循环语句"""
        parser = self.Parser()
        code = '当 x 大于 0：\n    x 等于 x 减 1'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_function_call(self):
        """测试函数调用"""
        parser = self.Parser()
        code = '打印 123'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_function_call_with_parens(self):
        """测试带括号函数调用"""
        parser = self.Parser()
        code = '打印(123)'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_list_literal(self):
        """测试列表字面量"""
        parser = self.Parser()
        code = '设列表为[1, 2, 3]。'
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_nested_blocks(self):
        """测试嵌套代码块"""
        parser = self.Parser()
        code = """
如果 x 大于 0 那么：
    如果 y 大于 0 那么：
        打印 "两者都正"
"""
        module = parser.parse(code)
        self.assertIsNotNone(module)

    def test_empty_program(self):
        """测试空程序"""
        parser = self.Parser()
        code = ''
        module = parser.parse(code)
        self.assertIsNotNone(module)


if __name__ == '__main__':
    unittest.main()
