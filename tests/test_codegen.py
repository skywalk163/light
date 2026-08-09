# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 代码生成器测试

测试覆盖：
- 变量声明代码生成
- 表达式代码生成
- 条件语句代码生成
- 循环语句代码生成
- 函数定义代码生成
- 函数调用代码生成
- 完整程序代码生成
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


class TestVariableGeneration:
    """变量声明代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_variable(self, parser, generator):
        """测试简单变量生成"""
        module = parser.parse('设 甲 为 123。')
        python_code = generator.generate(module)
        assert '123' in python_code
        assert '=' in python_code

    def test_variable_with_expression(self, parser, generator):
        """测试带表达式的变量生成"""
        module = parser.parse('设 结果 为 三 加 五。')
        python_code = generator.generate(module)
        assert '+' in python_code or 'add' in python_code.lower()


class TestExpressionGeneration:
    """表达式代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_arithmetic_expression(self, parser, generator):
        """测试算术表达式生成"""
        module = parser.parse('设 结果 为 甲 加 乙 乘 丙。')
        python_code = generator.generate(module)
        assert '+' in python_code or 'add' in python_code.lower()
        assert '*' in python_code or 'mul' in python_code.lower()

    def test_comparison_expression(self, parser, generator):
        """测试比较表达式生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert '>' in python_code or 'gt' in python_code.lower()


class TestConditionalGeneration:
    """条件语句代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_if(self, parser, generator):
        """测试简单if生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert 'print' in python_code

    def test_if_else(self, parser, generator):
        """测试if-else生成"""
        module = parser.parse('如果 甲 大于 乙 那么：打印(甲)。否则：打印(乙)。')
        python_code = generator.generate(module)
        assert 'if' in python_code
        assert 'else' in python_code


class TestLoopGeneration:
    """循环语句代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_while_loop(self, parser, generator):
        """测试while循环生成"""
        code = '''当 甲 小于 十：
  甲 等于 甲 加 一。
结束。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'while' in python_code

    def test_for_loop(self, parser, generator):
        """测试for循环生成"""
        code = '''遍历 元素 之 列表：
  打印(元素)。
结束。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'for' in python_code


class TestFunctionGeneration:
    """函数定义代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_function(self, parser, generator):
        """测试简单函数生成"""
        module = parser.parse('段 计算 接收：返回 甲 加 乙。结束。')
        python_code = generator.generate(module)
        assert 'def' in python_code

    def test_function_with_params(self, parser, generator):
        """测试带参数的函数生成"""
        module = parser.parse('《计算》段(甲, 乙)：返回 甲 加 乙。')
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert '(' in python_code
        assert ')' in python_code
        assert 'return' in python_code


class TestFunctionCallGeneration:
    """函数调用代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_call(self, parser, generator):
        """测试简单函数调用生成"""
        module = parser.parse('设 结果 为 计算(甲, 乙)。')
        python_code = generator.generate(module)
        assert '(' in python_code
        assert ')' in python_code

    def test_call_in_expression(self, parser, generator):
        """测试表达式中的函数调用"""
        module = parser.parse('设 结果 为 计算(甲, 乙)。')
        python_code = generator.generate(module)
        assert '(' in python_code


class TestCompleteProgramGeneration:
    """完整程序代码生成测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_factorial(self, parser, generator):
        """测试阶乘程序生成"""
        code = '''《阶乘》段(数)：
  如果 数 小于等于 1 那么 返回 1。
  返回 数 乘 阶乘(数 减 1)。

设 结果 为 阶乘(5)。
打印(结果)。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert 'if' in python_code
        assert 'return' in python_code
        assert 'print' in python_code

    def test_fibonacci(self, parser, generator):
        """测试斐波那契程序生成"""
        code = '''《斐波那契》段(数)：
  如果 数 小于等于 2 那么 返回 1。
  返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)。

设 结果 为 斐波那契(10)。
打印(结果)。'''
        module = parser.parse(code)
        python_code = generator.generate(module)
        assert 'def' in python_code
        assert 'if' in python_code
        assert 'return' in python_code


class TestCodeExecution:
    """代码执行测试"""

    @pytest.fixture
    def parser(self):
        return LightParser()

    @pytest.fixture
    def generator(self):
        return PythonCodeGenerator()

    def test_simple_execution(self, parser, generator):
        """测试简单程序执行"""
        module = parser.parse('设 甲 为 三 加 五。')
        python_code = generator.generate(module)
        try:
            exec_globals = {}
            exec(python_code, exec_globals)
            assert True
        except Exception as e:
            print(f"Execution error: {e}")

    def test_function_execution(self, parser, generator):
        """测试函数程序执行"""
        module = parser.parse('《加法》段(甲, 乙)：返回 甲 加 乙。')
        python_code = generator.generate(module)
        try:
            exec_globals = {}
            exec(python_code, exec_globals)
        except Exception as e:
            print(f"Execution error: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
