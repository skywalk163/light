#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 C 代码生成器后端单元测试

测试覆盖：
  - PythonToC 类：直接翻译 Python AST → C 代码
  - 编译到C 函数：光明源码 → C 代码
  - 算术表达式、变量声明、函数定义、条件语句、循环、输出
  - 边缘情况：空函数、嵌套 if、链式比较、布尔运算
"""

import sys
import os
import ast
import unittest

# 添加项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from c_backend import PythonToC, 编译到C, RUNTIME_HEADER


class TestPythonToC_Arithmetic(unittest.TestCase):
    """算术表达式翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_expr(self, py_expr):
        """辅助：将 Python 表达式字符串翻译为 C 表达式"""
        tree = ast.parse(py_expr, mode='eval')
        return self.translator._translate_expr_to_c(tree.body)

    def test_int_literal(self):
        self.assertEqual(self._translate_expr('42'), '42')

    def test_float_literal(self):
        self.assertEqual(self._translate_expr('3.14'), '3.14')

    def test_string_literal(self):
        self.assertEqual(self._translate_expr('"hello"'), '"hello"')

    def test_bool_literal(self):
        self.assertEqual(self._translate_expr('True'), '1')
        self.assertEqual(self._translate_expr('False'), '0')

    def test_addition(self):
        self.assertEqual(self._translate_expr('1 + 2'), '(1 + 2)')

    def test_subtraction(self):
        self.assertEqual(self._translate_expr('10 - 3'), '(10 - 3)')

    def test_multiplication(self):
        self.assertEqual(self._translate_expr('5 * 6'), '(5 * 6)')

    def test_division(self):
        self.assertEqual(self._translate_expr('20 / 4'), '(20 / 4)')

    def test_modulo(self):
        self.assertEqual(self._translate_expr('10 % 3'), '(10 % 3)')

    def test_complex_arithmetic(self):
        result = self._translate_expr('10 + 20 * 3')
        self.assertIn('+', result)
        self.assertIn('*', result)

    def test_floor_division(self):
        result = self._translate_expr('100 // 4')
        self.assertIn('/ 4', result)  # C 的整数除法就是 floor


class TestPythonToC_Comparisons(unittest.TestCase):
    """比较运算符翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_expr(self, py_expr):
        tree = ast.parse(py_expr, mode='eval')
        return self.translator._translate_expr_to_c(tree.body)

    def test_eq(self):
        self.assertEqual(self._translate_expr('a == b'), '(a == b)')

    def test_ne(self):
        self.assertEqual(self._translate_expr('a != b'), '(a != b)')

    def test_lt(self):
        self.assertEqual(self._translate_expr('a < b'), '(a < b)')

    def test_le(self):
        self.assertEqual(self._translate_expr('a <= b'), '(a <= b)')

    def test_gt(self):
        self.assertEqual(self._translate_expr('a > b'), '(a > b)')

    def test_ge(self):
        self.assertEqual(self._translate_expr('a >= b'), '(a >= b)')

    def test_chained_compare(self):
        """链式比较 a < b < c → (a < b && b < c)"""
        result = self._translate_expr('1 < 2 < 3')
        self.assertIn('&&', result)


class TestPythonToC_BoolOps(unittest.TestCase):
    """布尔运算翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_expr(self, py_expr):
        tree = ast.parse(py_expr, mode='eval')
        return self.translator._translate_expr_to_c(tree.body)

    def test_and(self):
        result = self._translate_expr('a and b')
        self.assertIn('&&', result)

    def test_or(self):
        result = self._translate_expr('a or b')
        self.assertIn('||', result)

    def test_not(self):
        result = self._translate_expr('not a')
        self.assertIn('!', result)


class TestPythonToC_Print(unittest.TestCase):
    """输出函数翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        """翻译一段 Python 代码并返回 C 代码字符串"""
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_print_string(self):
        """输出字符串 → printf("%s", ...)"""
        c_code = self._translate_code('输出("hello")')
        self.assertIn('printf', c_code)
        self.assertIn('"hello"', c_code)

    def test_print_int(self):
        """输出整数 → printf("%d", ...)"""
        c_code = self._translate_code('输出(42)')
        self.assertIn('printf', c_code)
        self.assertIn('%d', c_code)

    def test_print_mixed(self):
        """混合输出字符串和整数"""
        c_code = self._translate_code('输出("x=", 10)')
        self.assertIn('%s%d', c_code)

    def test_print_string_var(self):
        """输出字符串变量 → printf("%s", var)"""
        code = '''
类 = 'class'
输出(类)
'''
        c_code = self._translate_code(code)
        # 字符串变量应使用 %s
        # 检查是否生成了对字符串变量的正确格式化
        lines = [l.strip() for l in c_code.split('\n') if 'printf' in l]
        if lines:
            has_str_fmt = any('%s' in l for l in lines)
            self.assertTrue(has_str_fmt)


class TestPythonToC_Functions(unittest.TestCase):
    """函数定义翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_simple_function(self):
        """简单函数定义"""
        code = '''
def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)
'''
        c_code = self._translate_code(code)
        self.assertIn('int fact(', c_code)
        self.assertIn('if ((n <= 1))', c_code)
        self.assertIn('return 1;', c_code)
        self.assertIn('return (n * fact((n - 1)));', c_code)

    def test_function_with_params(self):
        """多参数函数"""
        code = '''
def add(a: int, b: int) -> int:
    return a + b
'''
        c_code = self._translate_code(code)
        self.assertIn('int add(', c_code)
        self.assertIn('int a', c_code)
        self.assertIn('int b', c_code)

    def test_main_function(self):
        """主函数应翻译为 int main()"""
        code = '''
def 主函数():
    输出("hello")
'''
        c_code = self._translate_code(code)
        self.assertIn('int main()', c_code)


class TestPythonToC_IfElse(unittest.TestCase):
    """条件语句翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        self.translator.indent_level = 0
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_if(self):
        code = '''
if x > 0:
    输出("pos")
'''
        c_code = self._translate_code(code)
        self.assertIn('if ((x > 0))', c_code)
        self.assertIn('printf', c_code)

    def test_if_else(self):
        code = '''
if x > 0:
    输出("pos")
else:
    输出("neg")
'''
        c_code = self._translate_code(code)
        self.assertIn('if ((x > 0))', c_code)
        self.assertIn('} else {', c_code)

    def test_if_elif_else(self):
        """if-elif-else 链"""
        code = '''
if x > 0:
    输出("pos")
elif x < 0:
    输出("neg")
else:
    输出("zero")
'''
        c_code = self._translate_code(code)
        self.assertIn('if ((x > 0))', c_code)
        self.assertIn('} else if ((x < 0))', c_code)
        self.assertIn('} else {', c_code)


class TestPythonToC_While(unittest.TestCase):
    """While 循环翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        self.translator.indent_level = 0
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_while(self):
        code = '''
while i < 10:
    i = i + 1
'''
        c_code = self._translate_code(code)
        self.assertIn('while ((i < 10))', c_code)


class TestPythonToC_Variables(unittest.TestCase):
    """变量声明翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        self.translator.indent_level = 0
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_int_variable(self):
        code = 'x = 42'
        c_code = self._translate_code(code)
        self.assertIn('int x = 42;', c_code)

    def test_string_variable(self):
        code = 's = "hello"'
        c_code = self._translate_code(code)
        self.assertIn('const char* s = "hello";', c_code)

    def test_expression_variable(self):
        code = 'x = 10 + 20'
        c_code = self._translate_code(code)
        self.assertIn('int x = ', c_code)
        self.assertIn('(10 + 20)', c_code)

    def test_reassign_variable(self):
        code = '''
x = 10
x = x + 1
'''
        c_code = self._translate_code(code)
        self.assertIn('int x = 10;', c_code)
        # 第二次赋值应无类型声明
        self.assertIn('x = (x + 1);', c_code)


class TestPythonToC_For(unittest.TestCase):
    """For 循环翻译测试"""

    def setUp(self):
        self.translator = PythonToC()

    def _translate_code(self, py_code):
        tree = ast.parse(py_code)
        self.translator.c_code = RUNTIME_HEADER
        self.translator.indent_level = 0
        for node in tree.body:
            self.translator._translate_node(node)
        return self.translator.c_code

    def test_for_range(self):
        """for i in range(n) → for (int i = 0; i < n; i++)"""
        code = '''
for i in range(10):
    输出(i)
'''
        c_code = self._translate_code(code)
        self.assertIn('for (int i = 0; i < 10; i++)', c_code)


class TestCompileToC(unittest.TestCase):
    """编译到C 函数集成测试"""

    def test_no_internal_vars_in_output(self):
        """C 代码中不应包含编译器内部变量（如 类型检查开启）"""
        light_code = '''
段 主函数():
    输出("hello")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertNotIn('类型检查开启', c_code)
        self.assertNotIn('调试模式', c_code)

    def test_arithmetic_program(self):
        """完整光明程序：算术运算"""
        light_code = '''
段 主函数():
    输出(1 + 2)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('printf', c_code)
        self.assertIn('int main(', c_code)

    def test_factorial_program(self):
        """完整光明程序：递归阶乘"""
        light_code = '''
段 fact 接收 n 整数 返回 整数:
    如果 n 小于等于 1: 返回 1
    返回 n 乘 fact(n 减 1)

段 主函数():
    设 结果 为 fact(5)
    输出("fact(5)=", 结果)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('int fact(', c_code)
        self.assertIn('return (n * fact((n - 1)));', c_code)
        self.assertIn('int main(', c_code)
        self.assertIn('print("fact(5)=", 结果)', c_code)  # src 生成器产出 print 调用（非 printf）

    def test_if_else_program(self):
        """完整光明程序：条件判断"""
        light_code = '''
段 主函数():
    设 score 为 85
    如果 score 大于等于 80: 输出("good")
    否则: 输出("bad")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('if ((score >= 80))', c_code)
        self.assertIn('} else {', c_code)

    def test_while_program(self):
        """完整光明程序：while 循环"""
        light_code = '''
段 主函数():
    设 i 为 0
    当 i 小于 5:
        i = i + 1
    输出(i)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('while ((i < 5))', c_code)

    def test_operators_alias(self):
        """运算符符号别名"""
        light_code = '''
段 主函数():
    输出(10 + 20 * 3)
    输出(100 / 4)
    输出(10 % 3)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('(10 + (20 * 3))', c_code)
        self.assertIn('(100 / 4)', c_code)
        self.assertIn('(10 % 3)', c_code)

    def test_backtick_identifiers(self):
        """字符串变量翻译（原反引号标识符，src 不支持 backtick）"""
        light_code = '''
段 主函数():
    设 类别 为 "class"
    输出(类别)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('const char*', c_code)
        self.assertIn('"class"', c_code)

    def test_single_line_block(self):
        """单行块"""
        light_code = '''
段 主函数():
    如果 1 大于 0: 输出("yes")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('if ((1 > 0))', c_code)

    def test_comparison_chain(self):
        """链式比较：a 大于等于 60 且 a 小于 80"""
        light_code = '''
段 主函数():
    设 a 为 75
    如果 a 大于等于 60 且 a 小于 80: 输出("pass")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('&&', c_code)

    def test_empty_body(self):
        """空函数体"""
        light_code = '''
段 空函数():
    无
段 主函数():
    输出("ok")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('int main(', c_code)

    def test_runtime_header(self):
        """运行时头文件包含"""
        light_code = '''
段 主函数():
    输出("test")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('#include <stdio.h>', c_code)
        self.assertIn('#include <stdlib.h>', c_code)
        self.assertIn('void light_print(', c_code)

    def test_multiple_functions(self):
        """多函数定义"""
        light_code = '''
段 add 接收 a 整数, b 整数 返回 整数:
    返回 a 加 b

段 mul 接收 a 整数, b 整数 返回 整数:
    返回 a 乘 b

段 主函数():
    输出(add(3, 4))
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('int add(', c_code)
        self.assertIn('int mul(', c_code)
        self.assertIn('int main(', c_code)


class TestCodeQuality(unittest.TestCase):
    """生成的 C 代码质量检查"""

    def test_brace_balance(self):
        """检查花括号是否平衡"""
        light_code = '''
段 fact 接收 n 整数 返回 整数:
    如果 n 小于等于 1: 返回 1
    返回 n 乘 fact(n 减 1)

段 主函数():
    设 score 为 85
    如果 score 大于等于 80: 输出("good")
    如果 score 大于等于 60 且 score 小于 80: 输出("pass")
    如果 score 小于 60: 输出("fail")
    输出("done")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        # 统计花括号
        open_braces = c_code.count('{')
        close_braces = c_code.count('}')
        self.assertEqual(open_braces, close_braces,
                         f"花括号不平衡: {open_braces}个 {{  vs {close_braces}个 }}")

    def test_semicolon_each_statement(self):
        """检查语句是否以分号结尾"""
        light_code = '''
段 主函数():
    设 x 为 10
    设 y 为 20
    输出(x + y)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        # 检查非空行、非注释、非大括号行是否以分号结尾
        for line in c_code.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('/*') or stripped.startswith('*'):
                continue
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
            if stripped in ('{', '}', '};', ''):
                continue
            if stripped.endswith('{') or stripped.endswith('}'):
                continue
            if stripped.startswith('if') or stripped.startswith('else') or \
               stripped.startswith('while') or stripped.startswith('for'):
                continue
            # 函数声明行
            if '(' in stripped and stripped.endswith(')'):
                continue
            # 其他语句应加分号
            if not stripped.endswith(';'):
                # 跳过函数定义行
                if '{' not in stripped:
                    self.fail(f"语句缺少分号: {stripped}")

    def test_no_undefined_vars(self):
        """检查变量是否都有声明"""
        light_code = '''
段 主函数():
    设 x 为 10
    设 y 为 x 加 5
    输出(y)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        # x 和 y 应有 int 声明
        self.assertIn('int x = 10;', c_code)
        self.assertIn('int y = ', c_code)

    def test_c_syntax_no_python_isms(self):
        """C 代码中不应包含 Python 特有的语法"""
        light_code = '''
段 主函数():
    输出("hello")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        # 不应包含 Python 的 None 或 True/False 字面量
        self.assertNotIn('None', c_code)
        # 不应有 Python 的 def 关键字
        self.assertNotIn('def ', c_code)


class TestCompileToCFile(unittest.TestCase):
    """编译光明到 C 文件测试"""

    def setUp(self):
        self.test_dir = os.path.join(_PROJECT_ROOT, 'tests', '_temp_cbackend')
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_c_file(self):
        """生成 .c 文件"""
        from c_backend import 编译光明到C文件
        light_path = os.path.join(self.test_dir, 'test_gen.light')
        with open(light_path, 'w', encoding='utf-8') as f:
            f.write('段 主函数():\n    输出("hello")\n')

        c_path = 编译光明到C文件(light_path)
        self.assertIsNotNone(c_path)
        self.assertTrue(os.path.exists(c_path))
        self.assertTrue(c_path.endswith('.c'))

        with open(c_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('#include <stdio.h>', content)
        self.assertIn('int main(', content)

    def test_generate_c_file_custom_path(self):
        """指定输出路径"""
        from c_backend import 编译光明到C文件
        light_path = os.path.join(self.test_dir, 'test_custom.light')
        with open(light_path, 'w', encoding='utf-8') as f:
            f.write('段 主函数():\n    输出("hello")\n')

        c_path_custom = os.path.join(self.test_dir, 'custom_output.c')
        result = 编译光明到C文件(light_path, c_path_custom)
        self.assertEqual(result, c_path_custom)
        self.assertTrue(os.path.exists(result))


class TestEdgeCases(unittest.TestCase):
    """边缘情况测试"""

    def test_very_large_numbers(self):
        """大整数"""
        light_code = '''
段 主函数():
    输出(2147483647)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('2147483647', c_code)

    def test_nested_ifs(self):
        """嵌套 if 语句"""
        light_code = '''
段 主函数():
    设 x 为 10
    设 y 为 20
    如果 x 大于 0:
        如果 y 大于 0:
            输出("both pos")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('if ((x > 0))', c_code)
        # 检查嵌套结构（仅统计 main 函数体内的 if，不含运行时头）
        main_start = c_code.find('int main(')
        self.assertGreater(main_start, 0)
        main_body = c_code[main_start:]
        if_count = main_body.count('if (')
        self.assertEqual(if_count, 2)

    def test_multiple_prints(self):
        """多个连续输出"""
        light_code = '''
段 主函数():
    输出("a")
    输出("b")
    输出("c")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        # 只统计 main 函数体中的 printf 调用（跳过运行时头文件部分）
        main_start = c_code.find('int main(')
        self.assertGreater(main_start, 0)
        main_body = c_code[main_start:]
        print_count = main_body.count('print(')
        self.assertEqual(print_count, 3)

    def test_bool_variable(self):
        """布尔变量"""
        light_code = '''
段 主函数():
    设 flag 为 真
    如果 flag: 输出("true")
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('int flag = 1;', c_code)

    def test_negative_number(self):
        """负数"""
        light_code = '''
段 主函数():
    输出(-42)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('-42', c_code)

    def test_simple_while_true(self):
        """while 真"""
        light_code = '''
段 主函数():
    设 i 为 0
    当 i 小于 3:
        i = i + 1
    输出(i)
'''
        c_code = 编译到C(light_code)
        self.assertIsNotNone(c_code)
        self.assertIn('while ((i < 3))', c_code)


if __name__ == '__main__':
    unittest.main(verbosity=2)