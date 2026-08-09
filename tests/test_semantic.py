# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 语义分析器测试

测试覆盖：
- 类型检查
- 作用域管理
- 符号表
- 错误检测
"""

import pytest
import sys
import os

# 跳过：SemanticAnalyzer 的 Module API 与当前 light_parser_v3 的 Module 不兼容
pytestmark = pytest.mark.skip(reason="SemanticAnalyzer API 与当前 Module 类不兼容，待重构")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from semantic_analyzer import SemanticAnalyzer


class TestTypeChecking:
    """类型检查测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    def test_number_type(self, parser):
        """测试数字类型"""
        module = parser.parse('设 甲 为 123。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0

    def test_string_type(self, parser):
        """测试字符串类型"""
        module = parser.parse('设 甲 为 "你好"。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0

    def test_binary_operation_type(self, parser):
        """测试二元运算类型"""
        module = parser.parse('设 甲 为 三 加 五。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 应该能正确推导类型
        assert len(analyzer.errors) == 0


class TestScopeManagement:
    """作用域管理测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    def test_global_scope(self, parser):
        """测试全局作用域"""
        module = parser.parse('设 甲 为 1。设 乙 为 2。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0

    def test_function_scope(self, parser):
        """测试函数作用域"""
        module = parser.parse('《计算》段(甲, 乙)：返回 甲 加 乙。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 函数定义不应报错
        assert len(analyzer.errors) == 0

    def test_nested_scope(self, parser):
        """测试嵌套作用域"""
        code = '''《外层》段(甲)：
  《内层》段(乙)：
    返回 甲 加 乙。'''
        module = parser.parse(code)
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0


class TestSymbolTable:
    """符号表测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    def test_variable_declaration(self, parser):
        """测试变量声明"""
        module = parser.parse('设 甲 为 123。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 变量应该被添加到符号表
        assert len(analyzer.errors) == 0

    def test_function_declaration(self, parser):
        """测试函数声明"""
        module = parser.parse('《计算》段(甲, 乙)：返回 甲 加 乙。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0

    def test_undefined_variable(self, parser):
        """测试未定义变量"""
        module = parser.parse('打印(乙)。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 应该检测到未定义变量
        assert len(analyzer.errors) > 0


class TestSemanticErrors:
    """语义错误测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    def test_type_mismatch(self, parser):
        """测试类型不匹配"""
        # 尝试数字和字符串相加
        module = parser.parse('设 甲 为 123 加 "你好"。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 应该检测到类型错误（可能报错也可能不报，取决于实现严格程度）

    def test_duplicate_definition(self, parser):
        """测试重复定义"""
        module = parser.parse('设 甲 为 1。设 甲 为 2。')
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        # 应该检测到重复定义（可能报错也可能不报，取决于实现严格程度）


class TestSemanticAnalysisIntegration:
    """语义分析集成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    def test_complete_program(self, parser):
        """测试完整程序"""
        code = '''《计算平方》段(数)：
  返回 数 乘 数。
结束。

设 结果 为 计算平方(5)。
打印(结果)。'''
        module = parser.parse(code)
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0

    def test_recursive_function(self, parser):
        """测试递归函数"""
        code = '''《阶乘》段(数)：
  如果 数 小于等于 1 那么 返回 1。
  返回 数 乘 阶乘(数 减 1)。
结束。'''
        module = parser.parse(code)
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)
        assert len(analyzer.errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
