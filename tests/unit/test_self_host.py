# -*- coding: utf-8 -*-
"""
test_self_host.py - 自举编译器自托管验证测试

验证内容：
1. 使用 src/ 中的 Lexer/LightParser/PythonCodeGenerator 解析 bootstrap_v3.duan
2. 验证解析结果是否为有效的 Module AST
3. 生成 Python 代码并验证语法正确性
4. 报告统计信息
"""

import pytest
import sys
import os
import traceback

# 添加 src/ 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lexer import Lexer, LexerError
from light_parser_v3 import LightParser, ParseError, Module
from code_generator import PythonCodeGenerator, CodeGenError

BOOTSTRAP_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'bootstrap', 'bootstrap_v3.duan'
)


def _read_bootstrap():
    """读取 bootstrap_v3.duan 文件内容"""
    assert os.path.exists(BOOTSTRAP_FILE), f"Bootstrap file not found: {BOOTSTRAP_FILE}"
    with open(BOOTSTRAP_FILE, 'r', encoding='utf-8') as f:
        source = f.read()
    return source


class TestSelfHostLexer:
    """自举编译器词法分析验证"""

    def test_lexer_can_tokenize(self):
        """测试词法分析器能成功分析 bootstrap_v3.duan"""
        source = _read_bootstrap()
        lexer = Lexer()
        try:
            tokens = lexer.tokenize(source)
        except LexerError as e:
            pytest.fail(f"词法分析失败: {e}")

        assert tokens is not None, "词法分析返回 None"
        assert len(tokens) > 0, "令牌列表为空"
        print(f"\n词法分析成功: {len(tokens)} 个令牌")


class TestSelfHostParser:
    """自举编译器解析验证"""

    def test_parser_can_parse(self):
        """测试解析器能成功解析 bootstrap_v3.duan"""
        source = _read_bootstrap()
        parser = LightParser()
        try:
            module = parser.parse(source)
        except ParseError as e:
            pytest.fail(f"解析失败: {e}")

        assert module is not None, "解析返回 None"
        assert isinstance(module, Module), f"返回类型不是 Module: {type(module)}"
        print(f"\n解析成功: Module AST 节点")

    def test_parse_result_is_module(self):
        """验证解析结果是一个有效的 Module 对象"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        assert hasattr(module, 'statements'), "Module 缺少 statements 属性"
        assert len(module.statements) > 0, "Module statements 为空"


class TestSelfHostCodegen:
    """自举编译器代码生成验证"""

    def test_codegen_generates_valid_python(self):
        """测试代码生成器能生成有效的 Python 代码"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        try:
            py_code = generator.generate(module)
        except CodeGenError as e:
            pytest.fail(f"代码生成失败: {e}")

        assert py_code is not None, "代码生成返回 None"
        assert len(py_code) > 0, "生成的代码为空"
        assert 'def ' in py_code, "生成的代码未包含函数定义"
        print(f"\n代码生成成功: {len(py_code)} 字符")

    def test_generated_code_is_syntactically_valid(self):
        """验证生成的 Python 代码语法正确"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        try:
            compile(py_code, '<string>', 'exec')
        except SyntaxError as e:
            # 显示错误附近的代码行
            lines = py_code.splitlines()
            if e.lineno and 1 <= e.lineno <= len(lines):
                context = '\n'.join(lines[max(0, e.lineno - 3):e.lineno + 2])
                pytest.fail(
                    f"生成的 Python 代码语法错误 (行 {e.lineno}): {e.msg}\n"
                    f"附近代码:\n{context}"
                )
            else:
                pytest.fail(f"生成的 Python 代码语法错误: {e}")

    def test_codegen_output_contains_expected_patterns(self):
        """验证生成的代码包含预期的模式"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 检查关键函数定义
        assert 'def ' in py_code, "缺少函数定义"
        assert '词法分析' in py_code or 'lexer' in py_code.lower(), "缺少词法分析相关代码"
        assert 'parse' in py_code.lower(), "缺少解析相关代码"


class TestSelfHostPipeline:
    """自举编译器完整流水线验证"""

    def test_full_pipeline(self):
        """测试完整词法→解析→代码生成流水线"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 验证语法
        compile(py_code, '<string>', 'exec')

        # 统计信息
        func_count = py_code.count('def ')
        line_count = len(py_code.splitlines())
        print(f"\n--- 自举编译器统计 ---")
        print(f"源码行数: {len(source.splitlines())}")
        print(f"生成的 Python 行数: {line_count}")
        print(f"生成的函数数量: {func_count}")
        print(f"生成代码长度: {len(py_code)} 字符")
        print(f"语法验证: 通过")
        print(f"----------------------")

    def test_functions_count(self):
        """验证 bootstrap_v3.duan 中的函数数量"""
        source = _read_bootstrap()
        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 计算源码中的段落数
        source_func_count = source.count('\n段落 ')
        # 计算生成的 Python 函数数
        py_func_count = py_code.count('def ')

        print(f"\n源码段落数: {source_func_count}")
        print(f"生成的 Python 函数数: {py_func_count}")
        assert source_func_count > 0, "源码中未找到段落定义"
        assert py_func_count > 0, "生成的代码中未找到函数定义"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])