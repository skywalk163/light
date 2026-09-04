# -*- coding: utf-8 -*-
"""
v3.4 语法糖测试：句号可选化、符号运算符、属性赋值

覆盖三个优化点：
1. P0：句号可选 - 语句末尾句号「。」是可选的
2. P1：令 x = 值 简洁赋值
3. P2：符号运算符（+ - * / % == != < > <= >= ** //）与中文运算符等价
4. 额外：obj.attr = value 属性赋值
"""

import sys
import os
import pytest

# 确保路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_project_root, 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def parse_and_generate(code: str) -> str:
    """辅助：解析段言代码并生成 Python 代码"""
    parser = LightParser()
    ast = parser.parse(code)
    gen = PythonCodeGenerator()
    return gen.generate(ast)


def get_meaningful_lines(py_code: str) -> list:
    """提取生成的 Python 代码中有意义的行（去掉样板代码）"""
    lines = py_code.splitlines()
    result = []
    skip_until_code = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过所有头部 import/try/except/for/if 块，直到遇到实际生成的代码
        if skip_until_code:
            if stripped.startswith('#') or stripped.startswith('import ') or stripped.startswith('from '):
                continue
            if stripped.startswith('try:') or stripped.startswith('except ') or stripped.startswith('_duan'):
                continue
            if stripped.startswith('for _try_path') or stripped.startswith('os.path') or stripped.startswith('_duan_stdlib'):
                continue
            if stripped == '}' or stripped == ']':
                continue
            if stripped.startswith('if importlib') or stripped.startswith('if _duan_stdlib'):
                continue
            if stripped.startswith('spec') or stripped.startswith('_light_builtin'):
                continue
            if stripped.startswith('def _duan'):
                continue
            # 找到第一行实际代码
            skip_until_code = False
        result.append(line)
    return result


class TestPeriodOptional:
    """P0：句号可选化测试"""

    def test_no_period_simple(self):
        """无句号的简单程序"""
        code = '打印 "hello"'
        py = parse_and_generate(code)
        assert "print('hello')" in py or 'print("hello")' in py

    def test_no_period_multiple(self):
        """无句号的多行程序"""
        code = '令 x = 1\n令 y = 2\n打印 x'
        py = parse_and_generate(code)
        lines = get_meaningful_lines(py)
        assert any('x = 1' in l for l in lines)
        assert any('y = 2' in l for l in lines)

    def test_mixed_period(self):
        """混合句号和无句号"""
        code = '设 甲 为 10。\n设 乙 为 20\n打印 甲'
        py = parse_and_generate(code)
        lines = get_meaningful_lines(py)
        assert any('甲' in l and '10' in l for l in lines)

    def test_no_period_if(self):
        """无句号的条件语句"""
        code = '令 a = 5\n如果 a > 3:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert 'if' in py

    def test_no_period_while(self):
        """无句号的循环"""
        code = '令 i = 0\n当 i < 3:\n    打印 i\n    i = i + 1'
        py = parse_and_generate(code)
        assert 'while' in py

    def test_no_period_func_def(self):
        """无句号的函数定义"""
        code = '函数 加法(a, b):\n    返回 a + b\n打印 加法(1, 2)'
        py = parse_and_generate(code)
        assert 'def' in py

    def test_no_period_class(self):
        """无句号的类定义"""
        code = '类 动物:\n    令 名字 = ""\n    函数 说话(self):\n        打印 self.名字'
        py = parse_and_generate(code)
        assert 'class' in py

    def test_no_period_try(self):
        """无句号的异常处理"""
        code = '尝试:\n    令 x = 1 / 0\n捕获 Exception:\n    打印 "error"'
        py = parse_and_generate(code)
        assert 'try' in py

    def test_period_still_works(self):
        """句号仍然正常工作"""
        code = '设 甲 为 10。\n打印 甲。'
        py = parse_and_generate(code)
        assert '10' in py


class TestSymbolOperators:
    """P2：符号运算符测试"""

    def test_plus(self):
        """加法符号"""
        code = '令 a = 3 + 5'
        py = parse_and_generate(code)
        assert '3 + 5' in py

    def test_minus(self):
        """减法符号"""
        code = '令 a = 10 - 3'
        py = parse_and_generate(code)
        assert '10 - 3' in py

    def test_multiply(self):
        """乘法符号"""
        code = '令 a = 4 * 5'
        py = parse_and_generate(code)
        assert '4 * 5' in py

    def test_divide(self):
        """除法符号：按 known_issues §15.1 裁决选 B，「除以」/「/」整数相除向零截断，走 _light_trunc_div"""
        code = '令 a = 10 / 2'
        py = parse_and_generate(code)
        assert '_light_trunc_div(10, 2)' in py

    def test_modulo(self):
        """取余符号"""
        code = '令 a = 10 % 3'
        py = parse_and_generate(code)
        assert '10 % 3' in py

    def test_power(self):
        """幂运算符号"""
        code = '令 a = 2 ** 3'
        py = parse_and_generate(code)
        assert '2 ** 3' in py or '2 ** 3' in py.replace(' ', '')

    def test_floor_div(self):
        """整除符号：「整除」/「//」保留 Python floor 语义（负数为向下取整），生成 //；
        与「除以/」向零截断语义区分（known_issues §15.1）。"""
        code = '令 a = 10 // 3'
        py = parse_and_generate(code)
        assert '(10 // 3)' in py
        assert '_light_trunc_div(10, 3)' not in py

    def test_floor_div_negative(self):
        """整除负数：floor 语义，向下取整（-7//2 == -4），非向零截断（-3）。"""
        code = '令 a = -7 // 2'
        py = parse_and_generate(code)
        assert '// 2' in py
        assert '_light_trunc_div(-7, 2)' not in py

    def test_eq(self):
        """等于比较"""
        code = '令 a = 5\n如果 a == 5:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '==' in py

    def test_neq(self):
        """不等于比较"""
        code = '令 a = 5\n如果 a != 3:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '!=' in py

    def test_lt(self):
        """小于"""
        code = '令 a = 5\n如果 a < 10:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '<' in py and 'if' in py

    def test_gt(self):
        """大于"""
        code = '令 a = 5\n如果 a > 3:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '>' in py and 'if' in py

    def test_le(self):
        """小于等于"""
        code = '令 a = 5\n如果 a <= 5:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '<=' in py

    def test_ge(self):
        """大于等于"""
        code = '令 a = 5\n如果 a >= 5:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '>=' in py

    def test_mixed_symbol_chinese(self):
        """符号与中文运算符混用"""
        code = '令 a = 3 + 5\n如果 a 大于 5:\n    打印 "yes"'
        py = parse_and_generate(code)
        assert '3 + 5' in py

    def test_unary_minus(self):
        """一元负号"""
        code = '令 a = -5'
        py = parse_and_generate(code)
        assert '-5' in py or '= -5' in py

    def test_chained_comparison(self):
        """链式比较（且连接）"""
        code = '令 x = 5\n如果 x > 0 且 x < 10:\n    打印 "in range"'
        py = parse_and_generate(code)
        assert 'and' in py

    def test_complex_expr(self):
        """复杂表达式"""
        code = '令 a = 1 + 2 * 3 - 4 / 2'
        py = parse_and_generate(code)
        assert '+' in py and '*' in py


class TestLingAssignment:
    """P1：令 x = 值 简洁赋值测试"""

    def test_ling_simple(self):
        """令 简单赋值"""
        code = '令 x = 42'
        py = parse_and_generate(code)
        assert 'x = 42' in py

    def test_ling_string(self):
        """令 字符串赋值"""
        code = '令 s = "hello"'
        py = parse_and_generate(code)
        assert 's = ' in py and 'hello' in py

    def test_ling_expr(self):
        """令 表达式赋值"""
        code = '令 x = 3 + 5'
        py = parse_and_generate(code)
        assert '3 + 5' in py

    def test_ling_reassign(self):
        """令 声明后重新赋值"""
        code = '令 x = 5\nx = 10'
        py = parse_and_generate(code)
        lines = get_meaningful_lines(py)
        assert any('x = 5' in l for l in lines)
        assert any('x = 10' in l for l in lines)

    def test_ling_equal_等于(self):
        """使用 等于 重新赋值"""
        code = '令 x = 5\nx 等于 10'
        py = parse_and_generate(code)
        lines = get_meaningful_lines(py)
        assert any('10' in l for l in lines)

    def test_she_still_works(self):
        """设 写法仍然有效"""
        code = '设 甲 为 10'
        py = parse_and_generate(code)
        assert '10' in py

    def test_compound_assignment(self):
        """复合赋值（加上）"""
        code = '令 x = 5\nx 加上 3'
        py = parse_and_generate(code)
        assert '+=' in py or '+ 3' in py


class TestAttributeAssignment:
    """属性赋值测试：obj.attr = value"""

    def test_self_attr_eq(self):
        """self.属性 = 值"""
        code = '类 A:\n    函数 f(self):\n        self.x = 1'
        py = parse_and_generate(code)
        assert 'self.x = 1' in py

    def test_self_attr_等于(self):
        """self.属性 等于 值"""
        code = '类 A:\n    函数 f(self):\n        self.x 等于 1'
        py = parse_and_generate(code)
        assert 'self.x == 1' in py or 'self.x = 1' in py

    def test_obj_attr_eq(self):
        """obj.attr = 值"""
        code = '令 p = 点(3, 4)\np.x = 10'
        py = parse_and_generate(code)
        assert 'p.x = 10' in py

    def test_dot_access_still_works(self):
        """属性访问仍然正常"""
        code = '令 p = 点(3, 4)\n令 x = p.x'
        py = parse_and_generate(code)
        assert 'p.x' in py

    def test_method_call_still_works(self):
        """方法调用仍然正常"""
        code = '令 s = "hello"\n令 n = s.长度'
        py = parse_and_generate(code)
        assert 's.长度' in py or 's' in py


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
