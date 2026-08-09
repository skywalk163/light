#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明编程语言 - 边界测试套件

测试覆盖边界/极端情况：
- 零值、空值、负值、大数值
- 空函数体、空类体
- 深层嵌套、复杂表达式
- 列表/字符串/布尔运算边界
- 循环控制边界（break/continue在特殊位置）
"""

import sys
import os
import io
import unittest
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def compile_and_run(light_code):
    """
    编译并执行光明代码，返回捕获的输出
    
    使用 src/ 目录下手写解析器 + 代码生成器
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    
    parser = LightParser()
    module = parser.parse(light_code)
    
    generator = PythonCodeGenerator()
    python_code = generator.generate(module)
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        # 创建包含内置函数的全局环境
        import types
        _light_builtin = types.ModuleType('_light_builtin')
        _light_builtin.打印 = print
        _light_builtin.列表创建 = list
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串长度 = len
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.转整数 = int
        _light_builtin.转浮点 = float
        _light_builtin.转字符串 = str
        _light_builtin.列表长度 = len
        _light_builtin.列表获取 = lambda lst, i: lst[i] if 0 <= i < len(lst) else None
        _light_builtin.列表排序 = lambda lst: sorted(lst)
        _light_builtin.列表反转 = lambda lst: list(reversed(lst))
        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
        _light_builtin.文件存在 = lambda path: os.path.isfile(path)
        
        exec(python_code, {'_light_builtin': _light_builtin, 'os': os})
    except Exception as e:
        sys.stdout = old_stdout
        raise RuntimeError(f"执行错误: {e}\n生成的Python代码:\n{python_code}") from e
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


class TestEdgeCasesValues(unittest.TestCase):
    """值边界测试"""
    
    def test_zero_integer(self):
        """零值"""
        code = """
设 甲 为 0。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("0", output)
    
    def test_negative_number(self):
        """负数"""
        code = """
设 甲 为 -1。
打印 甲。
设 乙 为 -100。
打印 乙。
"""
        output = compile_and_run(code)
        self.assertIn("-1", output)
        self.assertIn("-100", output)
    
    def test_large_number(self):
        """大数值"""
        code = """
设 甲 为 999999。
打印 甲。
设 乙 为 1000000。
打印 乙。
"""
        output = compile_and_run(code)
        self.assertIn("999999", output)
        self.assertIn("1000000", output)
    
    def test_floating_point(self):
        """浮点数"""
        code = """
设 甲 为 3.14。
打印 甲。
设 乙 为 0.5。
打印 乙。
"""
        output = compile_and_run(code)
        self.assertIn("3.14", output)
        self.assertIn("0.5", output)
    
    def test_empty_string(self):
        """空字符串"""
        code = """
设 甲 为 ""。
打印 甲。
设 乙 为 ""。
设 丙 为 乙 加 "x"。
打印 丙。
"""
        output = compile_and_run(code)
        self.assertIn("x", output)
    
    def test_boolean_values(self):
        """布尔值真/假"""
        code = """
设 甲 为 真。
设 乙 为 假。
如果 甲：
  打印 "真分支"。
结束。
如果 乙：
  打印 "不应执行"。
否则：
  打印 "假分支"。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("真分支", output)
        self.assertIn("假分支", output)


class TestEdgeCasesFunctions(unittest.TestCase):
    """函数边界测试"""
    
    def test_function_no_params(self):
        """无参数函数"""
        code = """
段落  sayHello：
  打印 "hello"。
结束。

sayHello()。
"""
        output = compile_and_run(code)
        self.assertIn("hello", output)
    
    def test_function_no_return(self):
        """无返回值的函数"""
        code = """
段落  log：
  打印 "logged"。
结束。

log。
"""
        output = compile_and_run(code)
        self.assertIn("logged", output)
    
    def test_nested_function_calls_deep(self):
        """多层嵌套函数调用"""
        code = """
段落 三倍 接收 数值：
  返回 数值 乘 3。
结束。

设 甲 为 1。
设 甲 为 三倍(三倍(三倍(甲)))。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("27", output)
    
    def test_deep_recursion(self):
        """深层递归（递归深度10）"""
        code = """
段落 累计 接收 数值：
  如果 数值 小于等于 0：
    返回 0。
  结束。
  返回 数值 加 累计(数值 减 1)。
结束。

打印 累计(10)。
"""
        output = compile_and_run(code)
        self.assertIn("55", output)
    
    def test_multiple_params_with_arithmetic(self):
        """多参数加复杂运算"""
        code = """
段落 复杂运算 接收 甲, 乙, 丙：
  返回 甲 乘 乙 加 丙 除 2。
结束。

打印 复杂运算(3, 4, 10)。
"""
        output = compile_and_run(code)
        # 标准数学优先级：先乘除后加减
        # 3 * 4 + 10 / 2 = 12 + 5 = 17
        self.assertIn("17", output)


class TestEdgeCasesControlFlow(unittest.TestCase):
    """控制流边界测试"""
    
    def test_if_no_else(self):
        """无else的if"""
        code = """
设 甲 为 1。
如果 甲 大于 0：
  打印 "正数"。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("正数", output)
    
    def test_nested_if_three_levels(self):
        """三层嵌套if"""
        code = """
设 甲 为 1。
设 乙 为 2。
设 丙 为 3。
如果 甲 大于 0：
  如果 乙 大于 1：
    如果 丙 大于 2：
      打印 "三层都满足"。
    结束。
  结束。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("三层都满足", output)
    
    def test_nested_while_loops(self):
        """嵌套while循环"""
        code = """
设 甲 为 0。
设 结果 为 ""。
当 甲 小于 2：
  设 乙 为 0。
  当 乙 小于 2：
    打印 甲。
    打印 乙。
    设 乙 为 乙 加 1。
  结束。
  设 甲 为 甲 加 1。
结束。
"""
        output = compile_and_run(code)
        for i in range(2):
            for j in range(2):
                self.assertIn(str(i), output)
                self.assertIn(str(j), output)
    
    def test_break_inside_nested_loop(self):
        """嵌套循环中break"""
        code = """
设 甲 为 0。
设 结果 为 0。
当 甲 小于 5：
  设 乙 为 0。
  当 乙 小于 5：
    设 结果 为 乙。
    如果 乙 大于 2：
      跳出。
    结束。
    设 乙 为 乙 加 1。
  结束。
  设 甲 为 甲 加 1。
结束。
打印 结果。
"""
        output = compile_and_run(code)
        self.assertIn("3", output)
    
    def test_continue_skip_middle(self):
        """跳过中间项"""
        code = """
设 总和 为 0。
设 计数 为 0。
当 计数 小于 5：
  设 计数 为 计数 加 1。
  如果 计数 等于 3：
    跳过。
  结束。
  设 总和 为 总和 加 计数。
结束。
打印 总和。
"""
        output = compile_and_run(code)
        # 1 + 2 + 4 + 5 = 12
        self.assertIn("12", output)
    
    def test_foreach_empty_list(self):
        """遍历空列表"""
        code = """
设 列表 为 []。
设 计数 为 0。
遍历 项 之 列表：
  设 计数 为 计数 加 1。
结束。
打印 计数。
"""
        output = compile_and_run(code)
        self.assertIn("0", output)
    
    def test_foreach_single_element(self):
        """遍历单元素列表"""
        code = """
设 列表 为 ["唯一"]。
遍历 项 之 列表：
  打印 项。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("唯一", output)


class TestEdgeCasesLists(unittest.TestCase):
    """列表操作边界测试"""
    
    def test_empty_list(self):
        """空列表创建"""
        code = """
设 甲 为 []。
打印 "ok"。
"""
        output = compile_and_run(code)
        self.assertIn("ok", output)
    
    def test_list_index_access_first(self):
        """列表索引访问"""
        code = """
设 甲 为 [10, 20, 30]。
打印 甲[0]。
打印 甲[1]。
打印 甲[2]。
"""
        output = compile_and_run(code)
        self.assertIn("10", output)
        self.assertIn("20", output)
        self.assertIn("30", output)
    
    def test_list_with_different_types(self):
        """混合类型列表"""
        code = """
设 甲 为 [1, "a", 真]。
打印 甲[0]。
打印 甲[1]。
"""
        output = compile_and_run(code)
        self.assertIn("1", output)
        self.assertIn("a", output)


class TestEdgeCasesClasses(unittest.TestCase):
    """类边界测试"""
    
    def test_empty_class(self):
        """空类"""
        code = """
类 空类：
结束。

设 实例 为 新建 空类。
打印 "ok"。
"""
        output = compile_and_run(code)
        self.assertIn("ok", output)
    
    def test_class_only_constructor(self):
        """仅构造函数类"""
        code = """
类 人：
  属性 名称。
  
  构造 接收 名称：
    己名称 为 名称。
  结束。
结束。

设 某人 为 新建 人 "张三"。
打印 "ok"。
"""
        output = compile_and_run(code)
        self.assertIn("ok", output)
    
    def test_class_inheritance_chain(self):
        """继承链：动物 -> 哺乳动物 -> 狗"""
        code = """
类 动物：
  段落 叫声：
    打印 "动物叫声"。
  结束。
结束。

类 哺乳动物 继承 动物：
  段落 叫声：
    打印 "哺乳动物叫声"。
  结束。
结束。

类 狗 继承 哺乳动物：
  段落 叫声：
    打印 "汪汪"。
  结束。
结束。

设 小狗 为 新建 狗。
小狗.叫声()。
"""
        output = compile_and_run(code)
        self.assertIn("汪汪", output)
    
    def test_class_with_multiple_methods(self):
        """多方法类"""
        code = """
类 计算器：
  属性 初始值。
  
  构造 接收 初始值：
    己初始值 为 初始值。
  结束。
  
  段落 加 接收 数值：
    返回 己初始值 加 数值。
  结束。
  
  段落 减 接收 数值：
    返回 己初始值 减 数值。
  结束。
  
  段落 乘 接收 数值：
    返回 己初始值 乘 数值。
  结束。
结束。

设 计算 为 新建 计算器 10。
打印 计算.加(5)。
打印 计算.减(3)。
打印 计算.乘(4)。
"""
        output = compile_and_run(code)
        self.assertIn("15", output)
        self.assertIn("7", output)
        self.assertIn("40", output)


class TestEdgeCasesExpressions(unittest.TestCase):
    """表达式边界测试"""
    
    def test_complex_arithmetic(self):
        """复杂算术表达式"""
        code = """
# 标准数学优先级：先乘除后加减
# 1 + 2 * 3 - 4 / 2 = 1 + 6 - 2 = 5.0
设 甲 为 1 加 2 乘 3 减 4 除 2。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("5.0", output)
    
    def test_comparison_chain(self):
        """比较链"""
        code = """
设 甲 为 5。
如果 甲 大于 3：
  如果 甲 小于 10：
    打印 "在范围内"。
  结束。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("在范围内", output)
    
    def test_equality_comparison(self):
        """相等/不等比较"""
        code = """
设 甲 为 5。
设 乙 为 5。
如果 甲 等于 乙：
  打印 "相等"。
结束。
设 丙 为 6。
如果 甲 不等于 丙：
  打印 "不等"。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("相等", output)
        self.assertIn("不等", output)
    
    def test_greater_equal(self):
        """大于等于/小于等于"""
        code = """
设 甲 为 5。
如果 甲 大于等于 5：
  打印 ">=5"。
结束。
如果 甲 小于等于 5：
  打印 "<=5"。
结束。
设 乙 为 6。
如果 乙 大于等于 5：
  打印 ">=5-2"。
结束。
设 丙 为 4。
如果 丙 小于等于 5：
  打印 "<=5-2"。
结束。
"""
        output = compile_and_run(code)
        self.assertIn(">=5", output)
        self.assertIn("<=5", output)
        self.assertIn(">=5-2", output)
        self.assertIn("<=5-2", output)
    
    def test_string_containing_keywords(self):
        """包含关键字内容的字符串"""
        code = """
设 甲 为 "如果 当 段落 类 结束 返回"。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("如果 当 段落 类 结束 返回", output)
    
    def test_unicode_chinese_strings(self):
        """中文字符串"""
        code = """
设 甲 为 "你好世界！光明编程语言 v1.6"。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("你好世界！光明编程语言 v1.6", output)
    
    def test_mixed_type_expression(self):
        """混合运算"""
        code = """
设 甲 为 10。
设 乙 为 3。
设 丙 为 甲 加 乙 乘 2。
打印 丙。
"""
        output = compile_and_run(code)
        # 10 + 3*2 = 16
        self.assertIn("16", output)


class TestEdgeCasesNull(unittest.TestCase):
    """空值边界测试"""
    
    def test_null_literal(self):
        """空值字面量"""
        code = """
设 甲 为 空。
打印 "空值测试"。
"""
        output = compile_and_run(code)
        self.assertIn("空值测试", output)


class TestCompoundAssignment(unittest.TestCase):
    """复合赋值测试"""
    
    def test_add_assign(self):
        """加等于"""
        code = """
设 甲 为 10。
甲 加上 5。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("15", output)
    
    def test_subtract_assign(self):
        """减等于"""
        code = """
设 甲 为 10。
甲 减去 3。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("7", output)
    
    def test_multiply_assign(self):
        """乘等于"""
        code = """
设 甲 为 6。
甲 乘以 3。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("18", output)
    
    def test_divide_assign(self):
        """除等于"""
        code = """
设 甲 为 20。
甲 除以 4。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("5.0", output)
    
    def test_compound_chain(self):
        """链式复合赋值"""
        code = """
设 甲 为 10。
甲 加上 5。
甲 乘以 2。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("30", output)
    
    def test_compound_with_var(self):
        """复合赋值中引用其他变量"""
        code = """
设 甲 为 5。
设 乙 为 10。
甲 加上 乙。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("15", output)


class TestDestructuringAssignment(unittest.TestCase):
    """解构赋值测试"""
    
    def test_destructure_list(self):
        """解构列表"""
        code = """
设 (甲, 乙) 为 [10, 20]。
设 丙 为 甲 加 乙。
打印 丙。
"""
        output = compile_and_run(code)
        self.assertIn("30", output)
    
    def test_destructure_three_vars(self):
        """解构三个变量"""
        code = """
设 (甲, 乙, 丙) 为 [1, 2, 3]。
设 总和 为 甲 加 乙 加 丙。
打印 总和。
"""
        output = compile_and_run(code)
        self.assertIn("6", output)


class TestImportExport(unittest.TestCase):
    """导入导出测试"""
    
    def test_import_module(self):
        """导入模块"""
        code = """
导入 math。
打印 "导入成功"。
"""
        output = compile_and_run(code)
        self.assertIn("导入成功", output)


class TestTryExcept(unittest.TestCase):
    """异常处理测试"""
    
    def test_try_no_exception(self):
        """尝试无异常"""
        code = """
尝试：
  设 甲 为 1。
  打印 甲。
捕获：
  打印 "不应执行"。
结束。
"""
        output = compile_and_run(code)
        self.assertIn("1", output)
        self.assertNotIn("不应执行", output)


class TestComments(unittest.TestCase):
    """注释测试"""
    
    def test_line_comment(self):
        """行注释 #"""
        code = """
# 这是一行注释
设 甲 为 42。
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("42", output)
    
    def test_inline_comment(self):
        """行内多注释"""
        code = """
# 注释1
# 注释2
设 甲 为 100。
# 注释3
打印 甲。
"""
        output = compile_and_run(code)
        self.assertIn("100", output)


class TestAdditionalEdgeCases(unittest.TestCase):
    """其他边界情况测试"""
    
    def test_very_long_identifier(self):
        """超长中文标识符"""
        code = """
设 这是一个非常长的变量名称用于测试边界情况 为 999。
打印 这是一个非常长的变量名称用于测试边界情况。
"""
        output = compile_and_run(code)
        self.assertIn("999", output)
    
    def test_many_variables(self):
        """大量变量"""
        code = """
设 甲 为 1。
设 乙 为 2。
设 丙 为 3。
打印 甲 加 乙 加 丙。
"""
        output = compile_and_run(code)
        self.assertIn("6", output)
    
    def test_print_multiple_values(self):
        """打印多个值"""
        code = """
设 甲 为 10。
设 乙 为 20。
打印 甲。
打印 乙。
"""
        output = compile_and_run(code)
        self.assertIn("10", output)
        self.assertIn("20", output)


if __name__ == '__main__':
    print("=" * 70)
    print("光明编程语言 - 边界测试套件")
    print("=" * 70)
    
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print(f"测试结果: {result.testsRun} 运行, {len(result.errors)} 错误, {len(result.failures)} 失败")
    print("=" * 70)
    
    sys.exit(0 if result.wasSuccessful() else 1)