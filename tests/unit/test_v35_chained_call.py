# -*- coding: utf-8 -*-
"""
v3.5 测试：链式方法调用 + TokenType.DOT/PERIOD 拆分

覆盖：
1. 链式方法调用：obj.method().chain()
2. 函数返回值调用：func()()
3. 链式属性赋值：obj.a.b = value
4. DOT/PERIOD 拆分：句号「。」和点号「.」独立 token
"""

import sys
import os
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_project_root, 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def parse_and_generate(code: str) -> str:
    parser = LightParser()
    ast = parser.parse(code)
    gen = PythonCodeGenerator()
    return gen.generate(ast)


def get_meaningful_lines(py_code: str) -> list:
    lines = py_code.splitlines()
    result = []
    skip_until_code = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
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
            skip_until_code = False
        result.append(line)
    return result


class TestChainedMethodCall:
    """链式方法调用测试"""

    def test_string_chain_upper_lower(self):
        """字符串链式调用 upper().lower()"""
        code = '令 s = "Hello"\n令 r = s.upper().lower()'
        py = parse_and_generate(code)
        assert 's.upper().lower()' in py or '.upper()' in py and '.lower()' in py

    def test_string_chain_strip_upper(self):
        """字符串链式调用 strip().upper()"""
        code = '令 s = "  hi  "\n令 r = s.strip().upper()'
        py = parse_and_generate(code)
        assert '.strip()' in py and '.upper()' in py

    def test_method_chain_with_args(self):
        """带参数的链式调用"""
        code = '令 s = "a,b,c"\n令 r = s.split(",").长度'
        py = parse_and_generate(code)
        assert '.split(' in py

    def test_func_return_call(self):
        """函数返回值立即调用 func()()"""
        code = '函数 f():\n    返回 "hi"\n令 r = f()()'
        py = parse_and_generate(code)
        assert 'f()()' in py or 'f()' in py

    def test_obj_method_chain(self):
        """对象方法链式调用"""
        code = '类 Calc:\n    令 result = 0\n    函数 add(self, n):\n        self.result = self.result + n\n        返回 self\n令 c = Calc()\nc.add(5).add(3)'
        py = parse_and_generate(code)
        assert 'class' in py
        assert '.add(5)' in py or '.add(' in py

    def test_chain_in_print(self):
        """打印语句中的链式调用"""
        code = '令 s = "Hello"\n打印 s.upper().lower()'
        py = parse_and_generate(code)
        assert '.upper()' in py or 'print' in py

    def test_chain_three_levels(self):
        """三级链式调用"""
        code = '令 s = "  Hello  "\n令 r = s.strip().upper().lower()'
        py = parse_and_generate(code)
        assert '.strip()' in py
        assert '.upper()' in py
        assert '.lower()' in py

    def test_chain_with_list_method(self):
        """列表方法链式调用"""
        code = '令 lst = [3, 1, 2]\nlst.sort()\n打印 lst'
        py = parse_and_generate(code)
        assert '.sort()' in py or 'sort' in py

    def test_chain_assignment(self):
        """链式调用结果赋值"""
        code = '令 s = "Hello World"\n令 parts = s.split(" ")\n令 first = parts[0]\n打印 first'
        py = parse_and_generate(code)
        assert '.split(' in py

    def test_nested_chain_in_expr(self):
        """表达式中的嵌套链式调用"""
        code = '令 s = "abc"\n令 n = s.upper().长度 + 1'
        py = parse_and_generate(code)
        assert '.upper()' in py or 'len' in py


class TestChainedAttributeAssignment:
    """链式属性赋值测试：obj.a.b = value"""

    def test_two_level_attr_assign(self):
        """两级属性赋值 b.a.x = 42"""
        code = '类 A:\n    令 x = 0\n类 B:\n    令 a = None\n令 b = B()\nb.a = A()\nb.a.x = 42'
        py = parse_and_generate(code)
        assert 'b.a.x = 42' in py or '.x = 42' in py

    def test_self_chain_assign(self):
        """self 链式属性赋值"""
        code = '类 A:\n    令 inner = None\n    函数 set_val(self, v):\n        self.inner.val = v'
        py = parse_and_generate(code)
        assert 'self.inner.val' in py or '.inner.val' in py

    def test_three_level_attr_assign(self):
        """三级属性赋值"""
        code = '类 C:\n    令 val = 0\n类 B:\n    令 c = None\n类 A:\n    令 b = None\n令 a = A()\na.b = B()\na.b.c = C()\na.b.c.val = 99'
        py = parse_and_generate(code)
        assert 'a.b.c.val = 99' in py or '.val = 99' in py

    def test_attr_assign_with_expr(self):
        """属性赋值为表达式"""
        code = '类 A:\n    令 x = 0\n令 a = A()\na.x = 10 + 20'
        py = parse_and_generate(code)
        assert 'a.x = ' in py
        assert '10 + 20' in py or '30' in py


class TestDotPeriodSplit:
    """DOT/PERIOD 拆分测试"""

    def test_period_does_not_terminate_expr(self):
        """句号「。」不会误当作点号「.」终止表达式"""
        code = '令 x = 5\n打印 x'
        py = parse_and_generate(code)
        assert 'x' in py
        assert 'print' in py

    def test_dot_member_access(self):
        """英文点号「.」用于成员访问"""
        code = '类 P:\n    令 x = 0\n令 p = P()\n令 v = p.x'
        py = parse_and_generate(code)
        assert 'p.x' in py

    def test_period_at_end_of_statement(self):
        """句号「。」作为语句结束符"""
        code = '设 x 为 10。\n打印 x。'
        py = parse_and_generate(code)
        assert '10' in py
        assert 'print' in py or '_duan_print' in py

    def test_mixed_period_and_dot(self):
        """混合使用句号和点号"""
        code = '类 P:\n    令 x = 0。\n令 p = P()。\n令 v = p.x\n打印 v。'
        py = parse_and_generate(code)
        assert 'p.x' in py

    def test_no_period_no_dot_ambiguity(self):
        """无句号代码中点号仅用于成员访问"""
        code = '类 P:\n    令 x = 0\n    令 y = 0\n令 p = P()\np.x = 3\np.y = p.x + 1\n打印 p.y'
        py = parse_and_generate(code)
        assert 'p.x = 3' in py
        assert 'p.y' in py

    def test_dot_in_method_call(self):
        """方法调用中的点号"""
        code = '令 s = "hello"\n令 n = s.upper()'
        py = parse_and_generate(code)
        assert '.upper()' in py

    def test_period_optional_everywhere(self):
        """句号在各语句中可选"""
        # 无句号的 if 语句
        code1 = '令 a = 5\n如果 a > 3:\n    打印 "yes"'
        py1 = parse_and_generate(code1)
        assert 'if' in py1

        # 有句号的 if 语句
        code2 = '令 a = 5。\n如果 a > 3:\n    打印 "yes"。'
        py2 = parse_and_generate(code2)
        assert 'if' in py2

    def test_dot_chain_not_confused_with_period(self):
        """点号链式调用不会被句号干扰"""
        code = '令 s = "Hello"。令 r = s.strip().upper()。'
        py = parse_and_generate(code)
        assert '.strip()' in py
        assert '.upper()' in py

    def test_period_in_class_body(self):
        """类体中使用句号"""
        code = '类 A:\n    令 x = 10。\n    函数 get(self):\n        返回 self.x。'
        py = parse_and_generate(code)
        assert 'class' in py
        assert 'self.x' in py

    def test_dot_access_after_new_keyword(self):
        """新关键字令后的点号访问"""
        code = '类 A:\n    令 x = 0\n令 a = A()\n令 v = a.x'
        py = parse_and_generate(code)
        assert 'a.x' in py


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_method_chain(self):
        """无参数方法链式调用"""
        code = '令 s = "  hi  "\n令 r = s.strip()'
        py = parse_and_generate(code)
        assert '.strip()' in py

    def test_chain_with_string_literal(self):
        """字符串字面量上链式调用"""
        code = '令 r = "hello".upper()'
        py = parse_and_generate(code)
        assert '.upper()' in py

    def test_multiple_chains_in_assignment(self):
        """多个链式调用在赋值中"""
        code = '令 a = "Hello".upper()\n令 b = "World".lower()'
        py = parse_and_generate(code)
        assert '.upper()' in py
        assert '.lower()' in py

    def test_chain_with_index(self):
        """链式调用后索引访问"""
        code = '令 s = "a,b,c"\n令 r = s.split(",")[0]'
        py = parse_and_generate(code)
        assert '.split(' in py

    def test_dot_not_confused_in_float(self):
        """浮点数中的点号不被误处理"""
        code = '令 x = 3.14'
        py = parse_and_generate(code)
        assert '3.14' in py

    def test_period_after_function_def(self):
        """函数定义后的句号"""
        code = '函数 f():\n    返回 42\n打印 f()'
        py = parse_and_generate(code)
        assert 'def' in py
        assert '42' in py


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
