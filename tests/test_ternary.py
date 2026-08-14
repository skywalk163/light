"""测试三元条件表达式

说明：原文件为模块级脚本（无 pytest 测试函数），pytest 收集 0 个测试，
属「虚假通过」（D04 测试可信度债务）。已迁移为真正的 pytest 参数化测试，
使用 src 后端（当前主后端）执行，覆盖与旧脚本完全相同的用例。
"""

import sys
import os
import io
from contextlib import redirect_stdout

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def run_light(code: str) -> str:
    """使用 src 后端解析并执行光明代码，返回输出"""
    parser = LightParser()
    module = parser.parse(code)
    if not module:
        raise AssertionError(f"Parse failed: {parser.errors}")

    gen = PythonCodeGenerator()
    py_code = gen.generate(module)

    f = io.StringIO()
    with redirect_stdout(f):
        exec(py_code, {'__name__': '__main__', '__file__': 'test.light'})
    return f.getvalue().strip()


TERNARY_TESTS = [
    ("设 甲 为 如果 1 小于 2 那么 10 否则 20。打印 甲。", "10"),
    ("设 甲 为 如果 1 大于 2 那么 10 否则 20。打印 甲。", "20"),
    ('打印 如果 真 那么 "是" 否则 "否"。', "是"),
    ('打印 如果 假 那么 "是" 否则 "否"。', "否"),
    ("设 甲 为 10。打印 如果 甲 大于 5 那么 30 否则 40。", "30"),
    ("设 甲 为 2。打印 如果 甲 大于 5 那么 30 否则 40。", "40"),
    ("打印 如果 3 大于 1 那么 100 否则 200。", "100"),
    ("设 结果 为 如果 1 等于 1 那么 42 否则 0。打印 结果。", "42"),
    # 没有否则分支（应返回空值）
    ('打印 如果 假 那么 "条件成立"。', "None"),
    # 三元表达式作为函数参数
    ("打印 如果 5 大于 3 那么 1 否则 2。", "1"),
    # 嵌套三元表达式
    ("设 甲 为 5。打印 如果 甲 大于 10 那么 100 否则 如果 甲 大于 0 那么 50 否则 0。", "50"),
    ("设 甲 为 -1。打印 如果 甲 大于 10 那么 100 否则 如果 甲 大于 0 那么 50 否则 0。", "0"),
    # 更复杂的三元表达式（包含运算）
    ("设 甲 为 6。打印 如果 甲 大于 5 那么 甲 乘 2 否则 甲 除 2。", "12"),
    ("设 甲 为 2。打印 如果 甲 大于 5 那么 甲 乘 2 否则 甲 除 2。", "1.0"),
]



@pytest.mark.parametrize("code,expected", TERNARY_TESTS,
                         ids=[f"case_{i}" for i in range(len(TERNARY_TESTS))])
def test_ternary_expression(code, expected):
    """三元条件表达式求值"""
    result = run_light(code)
    assert result == str(expected), f"期望: {expected}, 实际: {result}"
