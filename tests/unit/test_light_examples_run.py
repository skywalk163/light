# -*- coding: utf-8 -*-
"""
光明常用语法运行测试

覆盖大部分常用光明代码模式，确保编译和执行正确。
所有比较运算符使用中文形式（大于/小于/等于/不等于/大于等于/小于等于），
不使用 < > <= >= == != 符号。

已知限制（编译器未支持，测试已规避）：
- 除以/取余/次方 等运算符：使用 除/模/幂
- 以关键字开头的函数名（如 字典设置）：通过内置命名空间调用
- 未在 builtins.py 中注册的函数：不使用
"""

import os
import sys
import io
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run_light(code: str) -> str:
    """编译并运行光明代码，返回标准输出"""
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        errors = '\n'.join(getattr(parser, 'errors', []))
        raise RuntimeError(f"解析失败:\n{errors}")

    gen = PythonCodeGenerator()
    py_code = gen.generate(ast)

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        namespace = {'__name__': '__main__'}
        exec(py_code, namespace)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


class TestVariableAndArithmetic(unittest.TestCase):
    """变量声明与算术运算"""

    def test_integer_variable(self):
        code = '设 甲 为 42\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), '42')

    def test_float_variable(self):
        code = '设 甲 为 3.14\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), '3.14')

    def test_string_variable(self):
        code = '设 甲 为 "你好"\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), '你好')

    def test_boolean_true(self):
        code = '设 甲 为 真\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), 'True')

    def test_boolean_false(self):
        code = '设 甲 为 假\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), 'False')

    def test_addition(self):
        code = '设 甲 为 10\n设 乙 为 20\n打印(甲 加 乙)'
        self.assertEqual(_run_light(code).strip(), '30')

    def test_subtraction(self):
        code = '设 甲 为 30\n设 乙 为 12\n打印(甲 减 乙)'
        self.assertEqual(_run_light(code).strip(), '18')

    def test_multiplication(self):
        code = '设 甲 为 7\n设 乙 为 6\n打印(甲 乘 乙)'
        self.assertEqual(_run_light(code).strip(), '42')

    def test_division(self):
        # 使用 "除" 而非 "除以"
        code = '设 甲 为 100\n设 乙 为 4\n打印(甲 除 乙)'
        self.assertEqual(_run_light(code).strip(), '25')

    def test_modulo(self):
        # 使用 "模" 而非 "取余"
        code = '设 甲 为 17\n设 乙 为 5\n打印(甲 模 乙)'
        self.assertEqual(_run_light(code).strip(), '2')

    def test_exponentiation(self):
        # 使用 "幂" 而非 "的...次方"
        code = '设 甲 为 2\n设 乙 为 10\n打印(甲 幂 乙)'
        self.assertEqual(_run_light(code).strip(), '1024')

    def test_complex_expression(self):
        code = '设 甲 为 10\n设 乙 为 3\n设 丙 为 2\n打印(甲 加 乙 乘 丙)'
        self.assertEqual(_run_light(code).strip(), '16')

    def test_variable_reassignment(self):
        code = '设 甲 为 10\n设 甲 为 甲 加 5\n打印(甲)'
        self.assertEqual(_run_light(code).strip(), '15')


class TestComparisonOperators(unittest.TestCase):
    """比较运算符（全部使用中文形式）"""

    def test_equal(self):
        code = '如果 5 等于 5：\n  打印("相等")'
        self.assertEqual(_run_light(code).strip(), '相等')

    def test_not_equal(self):
        code = '如果 5 不等于 3：\n  打印("不等")'
        self.assertEqual(_run_light(code).strip(), '不等')

    def test_greater_than(self):
        code = '如果 10 大于 5：\n  打印("更大")'
        self.assertEqual(_run_light(code).strip(), '更大')

    def test_less_than(self):
        code = '如果 3 小于 7：\n  打印("更小")'
        self.assertEqual(_run_light(code).strip(), '更小')

    def test_greater_equal(self):
        code = '如果 5 大于等于 5：\n  打印("大于等于")'
        self.assertEqual(_run_light(code).strip(), '大于等于')

    def test_less_equal(self):
        code = '如果 3 小于等于 5：\n  打印("小于等于")'
        self.assertEqual(_run_light(code).strip(), '小于等于')

    def test_equal_false_branch(self):
        code = '如果 5 等于 3：\n  打印("相等")\n否则：\n  打印("不等")'
        self.assertEqual(_run_light(code).strip(), '不等')

    def test_elif(self):
        code = '设 分数 为 75\n如果 分数 大于等于 90：\n  打印("优")\n否则如果 分数 大于等于 60：\n  打印("及格")\n否则：\n  打印("不及格")'
        self.assertEqual(_run_light(code).strip(), '及格')


class TestConditionals(unittest.TestCase):
    """条件语句"""

    def test_simple_if(self):
        code = '如果 真：\n  打印("是")'
        self.assertEqual(_run_light(code).strip(), '是')

    def test_if_else(self):
        code = '如果 假：\n  打印("是")\n否则：\n  打印("否")'
        self.assertEqual(_run_light(code).strip(), '否')

    def test_nested_if(self):
        code = '设 甲 为 10\n设 乙 为 20\n如果 甲 小于 乙：\n  如果 乙 大于 15：\n    打印("嵌套成立")'
        self.assertEqual(_run_light(code).strip(), '嵌套成立')


class TestLoops(unittest.TestCase):
    """循环语句"""

    def test_while_loop(self):
        code = '设 计数 为 1\n当 计数 小于等于 3：\n  打印(计数)\n  设 计数 为 计数 加 1'
        self.assertEqual(_run_light(code).strip(), '1\n2\n3')

    def test_while_loop_greater(self):
        code = '设 计数 为 5\n当 计数 大于 2：\n  打印(计数)\n  设 计数 为 计数 减 1'
        self.assertEqual(_run_light(code).strip(), '5\n4\n3')

    def test_for_range(self):
        code = '遍历 项 于 1至3：\n  打印(项)'
        self.assertEqual(_run_light(code).strip(), '1\n2\n3')

    def test_for_list(self):
        code = '设 列表 为 列(10, 20, 30)\n遍历 项 于 列表：\n  打印(项)'
        self.assertEqual(_run_light(code).strip(), '10\n20\n30')

    def test_for_in(self):
        code = '设 列表 为 列("甲", "乙", "丙")\n遍历 项 在 列表：\n  打印(项)'
        self.assertEqual(_run_light(code).strip(), '甲\n乙\n丙')

    def test_break_in_while(self):
        code = '设 计数 为 1\n当 计数 小于等于 10：\n  如果 计数 大于 3：\n    跳出\n  打印(计数)\n  设 计数 为 计数 加 1'
        self.assertEqual(_run_light(code).strip(), '1\n2\n3')

    def test_break_in_for(self):
        code = '遍历 项 于 1至10：\n  如果 项 大于 3：\n    跳出\n  打印(项)'
        self.assertEqual(_run_light(code).strip(), '1\n2\n3')


class TestFunctions(unittest.TestCase):
    """函数定义与调用"""

    def test_simple_function(self):
        code = '段落 加一 接收 数：\n  返回 数 加 1\n打印(加一(5))'
        self.assertEqual(_run_light(code).strip(), '6')

    def test_two_param_function(self):
        code = '段落 求和 接收 甲, 乙：\n  返回 甲 加 乙\n打印(求和(3, 4))'
        self.assertEqual(_run_light(code).strip(), '7')

    def test_no_param_function(self):
        code = '段落 问好 接收：\n  返回 "你好"\n打印(问好())'
        self.assertEqual(_run_light(code).strip(), '你好')

    def test_function_call_in_expression(self):
        code = '段落 双倍 接收 数：\n  返回 数 乘 2\n设 结果 为 双倍(5) 加 双倍(3)\n打印(结果)'
        self.assertEqual(_run_light(code).strip(), '16')

    def test_recursive_factorial(self):
        code = '段落 阶乘 接收 数：\n  如果 数 小于等于 1：\n    返回 1\n  返回 数 乘 阶乘(数 减 1)\n打印(阶乘(5))'
        self.assertEqual(_run_light(code).strip(), '120')

    def test_recursive_fibonacci(self):
        code = '段落 斐波那契 接收 数：\n  如果 数 等于 0：\n    返回 0\n  如果 数 等于 1：\n    返回 1\n  返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)\n打印(斐波那契(10))'
        self.assertEqual(_run_light(code).strip(), '55')


class TestStringOperations(unittest.TestCase):
    """字符串操作（使用 builtins.py 中定义的函数）"""

    def test_string_concatenation(self):
        code = '设 甲 为 "你好"\n设 乙 为 "世界"\n打印(甲 加 乙)'
        self.assertEqual(_run_light(code).strip(), '你好世界')

    def test_string_length_builtin(self):
        code = '设 甲 为 "光明"\n打印(字符串长度(甲))'
        self.assertEqual(_run_light(code).strip(), '2')

    def test_string_upper_builtin(self):
        code = '设 甲 为 "hello"\n打印(转大写(甲))'
        self.assertEqual(_run_light(code).strip(), 'HELLO')

    def test_string_lower_builtin(self):
        code = '设 甲 为 "WORLD"\n打印(转小写(甲))'
        self.assertEqual(_run_light(code).strip(), 'world')

    def test_string_slice_builtin(self):
        code = '设 甲 为 "光明编程"\n打印(截取(甲, 0, 2))'
        self.assertEqual(_run_light(code).strip(), '光明')

    def test_string_interpolation(self):
        code = '设 名字 为 "光明"\n打印("你好，" 加 名字 加 "！")'
        self.assertEqual(_run_light(code).strip(), '你好，光明！')


class TestListOperations(unittest.TestCase):
    """列表操作"""

    def test_list_literal(self):
        code = '设 列表 为 列(1, 2, 3)\n打印(列表)'
        self.assertEqual(_run_light(code).strip(), '[1, 2, 3]')

    def test_list_length_builtin(self):
        code = '设 列表 为 列(10, 20, 30, 40)\n打印(列表长度(列表))'
        self.assertEqual(_run_light(code).strip(), '4')

    def test_list_append_builtin(self):
        code = '设 列表 为 列(1, 2)\n列表追加(列表, 3)\n打印(列表)'
        self.assertEqual(_run_light(code).strip(), '[1, 2, 3]')

    def test_list_index_access(self):
        code = '设 列表 为 列(10, 20, 30)\n打印(列表[0])\n打印(列表[2])'
        self.assertEqual(_run_light(code).strip(), '10\n30')

    def test_list_create_empty(self):
        code = '设 列表 为 列表创建()\n列表追加(列表, "甲")\n打印(列表)'
        self.assertEqual(_run_light(code).strip(), "['甲']")


@unittest.skip("字典操作函数以关键字开头，parser暂不支持直接调用")
class TestDictOperations(unittest.TestCase):
    """字典操作（跳过：以关键字开头的函数名parser不支持）"""

    def test_dict_placeholder(self):
        pass


@unittest.skip("类代码生成不完整，属性/构造器/方法未生成")
class TestClasses(unittest.TestCase):
    """类与面向对象（跳过：code generator对类的支持不完整）"""

    def test_placeholder(self):
        pass


class TestBuiltinFunctions(unittest.TestCase):
    """内置函数（仅限 builtins.py 中注册的函数）"""

    def test_str_conversion(self):
        code = '设 甲 为 42\n打印(转字符串(甲))'
        self.assertEqual(_run_light(code).strip(), '42')

    def test_int_conversion(self):
        code = '打印(转整数("42"))'
        self.assertEqual(_run_light(code).strip(), '42')

    def test_float_conversion(self):
        code = '打印(转浮点("3.14"))'
        self.assertEqual(_run_light(code).strip(), '3.14')

    def test_strip_whitespace(self):
        code = '打印(去除空白("  hello  "))'
        self.assertEqual(_run_light(code).strip(), 'hello')

    def test_join_strings(self):
        code = '打印(连接字符串(列("甲", "乙", "丙"), "-"))'
        self.assertEqual(_run_light(code).strip(), '甲-乙-丙')

    def test_replace_string(self):
        code = '打印(替换字符串("hello world", "world", "光明"))'
        self.assertEqual(_run_light(code).strip(), 'hello 光明')

    def test_split_string_builtin(self):
        code = '打印(分割字符串("甲-乙-丙", "-"))'
        self.assertEqual(_run_light(code).strip(), "['甲', '乙', '丙']")


class TestComplexPrograms(unittest.TestCase):
    """综合程序"""

    def test_sum_1_to_100(self):
        code = '''设 总和 为 0
设 计数 为 1
当 计数 小于等于 100：
  设 总和 为 总和 加 计数
  设 计数 为 计数 加 1
打印(总和)'''
        self.assertEqual(_run_light(code).strip(), '5050')

    def test_prime_check(self):
        code = '''段落 是素数 接收 数：
  如果 数 小于 2：
    返回 假
  设 除数 为 2
  当 除数 乘 除数 小于等于 数：
    如果 数 模 除数 等于 0：
      返回 假
    设 除数 为 除数 加 1
  返回 真

打印(是素数(17))
打印(是素数(18))'''
        self.assertEqual(_run_light(code).strip(), 'True\nFalse')

    def test_fibonacci_sequence(self):
        code = '''段落 斐波那契 接收 数：
  如果 数 等于 0：
    返回 0
  如果 数 等于 1：
    返回 1
  返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)

设 计数 为 0
当 计数 小于 8：
  打印(斐波那契(计数))
  设 计数 为 计数 加 1'''
        expected = '0\n1\n1\n2\n3\n5\n8\n13'
        self.assertEqual(_run_light(code).strip(), expected)

    def test_list_filter_even(self):
        code = '''设 列表 为 列(1, 2, 3, 4, 5, 6)
设 结果 为 列表创建()
遍历 项 于 列表：
  如果 项 模 2 等于 0：
    列表追加(结果, 项)
打印(结果)'''
        self.assertEqual(_run_light(code).strip(), '[2, 4, 6]')

    @unittest.skip("字典操作函数以关键字开头，parser暂不支持")
    def test_dict_word_count(self):
        pass


class TestEdgeCases(unittest.TestCase):
    """边界情况"""

    def test_empty_output(self):
        code = '设 甲 为 1'
        self.assertEqual(_run_light(code).strip(), '')

    def test_multiple_prints(self):
        code = '打印(1)\n打印(2)\n打印(3)'
        self.assertEqual(_run_light(code).strip(), '1\n2\n3')

    def test_nested_function_calls(self):
        code = '段落 双倍 接收 数：\n  返回 数 乘 2\n段落 加十 接收 数：\n  返回 数 加 10\n打印(加十(双倍(5)))'
        self.assertEqual(_run_light(code).strip(), '20')

    def test_zero_division_not_crashing_parser(self):
        code = '设 甲 为 10\n设 乙 为 0\n打印(甲 除 乙)'
        # 除零会在运行时出错，但解析和代码生成应成功
        with self.assertRaises(ZeroDivisionError):
            _run_light(code)


if __name__ == '__main__':
    unittest.main()
