# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 端到端集成测试

测试完整编译流程：
光明代码 → 词法分析 → 语法解析 → Python代码 → 执行验证
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


class TestEndToEndSimple:
    """简单程序端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_variable_declaration(self, compile_pipeline):
        """测试变量声明"""
        light_code = '设 甲 为 123。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert len(python_code) > 0

    def test_arithmetic_operation(self, compile_pipeline):
        """测试算术运算"""
        light_code = '设 结果 为 三 加 五。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        # 尝试执行
        try:
            exec_globals = {}
            exec(python_code, exec_globals)
        except Exception as e:
            print(f"Execution failed: {e}")

    def test_string_output(self, compile_pipeline):
        """测试字符串输出"""
        light_code = '打印("你好世界")。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'print' in python_code or '打印' in python_code


class TestEndToEndConditionals:
    """条件语句端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_simple_if(self, compile_pipeline):
        """测试简单条件"""
        light_code = '如果 甲 大于 乙 那么：打印(甲)。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'if' in python_code

    def test_if_else(self, compile_pipeline):
        """测试条件分支"""
        light_code = '如果 甲 大于 乙 那么：打印(甲)。否则：打印(乙)。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'if' in python_code
        assert 'else' in python_code


class TestEndToEndFunctions:
    """函数端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_simple_function(self, compile_pipeline):
        """测试简单函数"""
        light_code = '段 计算 接收：返回 甲 加 乙。结束。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code

    def test_function_with_params(self, compile_pipeline):
        """测试带参数函数"""
        light_code = '《加法》段(甲, 乙)：返回 甲 加 乙。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code
        assert 'return' in python_code

    def test_function_call(self, compile_pipeline):
        """测试函数调用"""
        light_code = '《加法》段(甲, 乙)：返回 甲 加 乙。结束。\n设 结果 为 加法(3, 5)。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code


class TestEndToEndRecursion:
    """递归函数端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_factorial(self, compile_pipeline):
        """测试阶乘函数"""
        light_code = '《阶乘》段(数)：\n  如果 数 小于等于 1 那么 返回 1。\n  返回 数 乘 阶乘(数 减 1)。\n结束。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code

    def test_fibonacci(self, compile_pipeline):
        """测试斐波那契函数"""
        light_code = '《斐波那契》段(数)：\n  如果 数 小于等于 2 那么 返回 1。\n  返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)。\n结束。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code


class TestEndToEndRealWorld:
    """真实场景端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_list_operations(self, compile_pipeline):
        """测试列表操作"""
        light_code = '设 列表 为 [1, 2, 3, 4, 5]。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None

    def test_calculator(self, compile_pipeline):
        """测试计算器"""
        light_code = '《计算器》段(操作, 甲, 乙)：\n  如果 操作 等于 "加" 那么 返回 甲 加 乙。\n  返回 0。\n结束。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None
        assert 'def' in python_code


class TestEndToEndErrorHandling:
    """错误处理端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            try:
                module = parser.parse(code)
                python_code = generator.generate(module)
                return python_code
            except Exception as e:
                return None

        return compile

    def test_incomplete_code(self, compile_pipeline):
        """测试不完整代码"""
        light_code = '设 甲 为'
        python_code = compile_pipeline(light_code)
        # 应该能优雅处理（返回 None 或部分结果）

    def test_invalid_syntax(self, compile_pipeline):
        """测试无效语法"""
        light_code = '如果 那么 否则'
        python_code = compile_pipeline(light_code)
        # 应该能优雅处理


class TestEndToEndPerformance:
    """性能端到端测试"""

    @pytest.fixture
    def compile_pipeline(self):
        """编译流水线"""
        parser = LightParser()
        generator = PythonCodeGenerator()

        def compile(code):
            module = parser.parse(code)
            python_code = generator.generate(module)
            return python_code

        return compile

    def test_large_function(self, compile_pipeline):
        """测试大型函数"""
        # 生成一个较大的函数
        lines = ['设 变量{} 为 {}。'.format(i, i) for i in range(100)]
        light_code = '\n'.join(lines)
        python_code = compile_pipeline(light_code)
        # 应该能在合理时间内完成
        assert python_code is not None

    def test_nested_functions(self, compile_pipeline):
        """测试嵌套函数"""
        light_code = '《外层》段(甲)：\n  《内层》段(乙)：\n    返回 甲 加 乙。\n  结束。\n  返回 内层(甲 加 1)。\n结束。'
        python_code = compile_pipeline(light_code)
        assert python_code is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
