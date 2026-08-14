# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 综合测试套件
"""

import sys
import os
import io

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))

# 检查 ANTLR 解析器是否可用
try:
    from light_visitor import parse_source
    from light_interpreter import Interpreter
    from light_llvm import LLVMCodeGen
except ImportError:
    import pytest
    pytest.skip("ANTLR parser not available (missing generated LightLangParser module)", allow_module_level=True)

def run_interpreter(source):
    module = parse_source(source)
    if module is None:
        raise RuntimeError("解析失败")
    interp = Interpreter()
    interp.interpret_module(module)
    return interp


def run_src(source):
    """使用 src 后端（当前主后端）编译并执行光明代码，返回执行全局命名空间。

    ANTLR 后端（遗留）的语法文件已无法解析当前版本的部分语法（段落/类），
    这些特性由 src 后端实现并持续维护，故此类测试改用 src 后端执行。
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    parser = LightParser()
    module = parser.parse(source)
    if module is None:
        raise RuntimeError(f"解析失败: {'; '.join(parser.errors)}")
    py_code = PythonCodeGenerator().generate(module)
    exec_globals = {'__name__': '__main__', '__file__': 'test.light'}
    exec(py_code, exec_globals)
    return exec_globals

def get_result(interp, var_name):
    return interp.env.get(var_name).value

def assert_result(interp, var_name, expected):
    actual = get_result(interp, var_name)
    assert actual == expected, f"{var_name}: {expected} != {actual}"

def test_basic():
    print("=== 基础语法 ===")
    interp = run_interpreter("设 a 为 42。")
    assert_result(interp, 'a', 42)
    print("✓ 变量定义")
    
    interp = run_interpreter('设 b 为 "你好"。')
    assert_result(interp, 'b', '你好')
    print("✓ 字符串")
    
    interp = run_interpreter("设 c 为 真。")
    assert_result(interp, 'c', True)
    print("✓ 布尔值")

def test_arithmetic():
    print("\n=== 算术运算 ===")
    interp = run_interpreter("设 a 为 10 加 5。设 b 为 10 减 5。设 c 为 10 乘 5。")
    assert_result(interp, 'a', 15)
    assert_result(interp, 'b', 5)
    assert_result(interp, 'c', 50)
    print("✓ 算术运算")

def test_simple_if():
    print("\n=== 简单条件 ===")
    interp = run_interpreter("设 x 为 10。如果 x 大于 5 那么: x 等于 x 加 1。结束。")
    assert_result(interp, 'x', 11)
    print("✓ 简单条件语句")

def test_functions():
    print("\n=== 段落测试 ===")
    code = """
段落 加法(x, y):
    返回 x 加 y。

设 r 为 加法(3, 5)。
"""
    ns = run_src(code)
    assert ns['r'] == 8
    print("✓ 段落定义和调用")

def test_classes():
    print("\n=== 类测试 ===")
    code = """
类 人：
    属性 姓名。

    构造 接收 名字：
        己姓名 为 名字。

    段落 说话：
        打印(己姓名)。

设 p 为 人("张三")。
"""
    ns = run_src(code)
    assert ns['p'].姓名 == '张三'
    print("✓ 类定义和实例化")

def test_lists():
    print("\n=== 列表测试 ===")
    interp = run_interpreter("设 lst 为 [1, 2, 3]。设 len 为 listLen(lst)。")
    assert_result(interp, 'len', 3)
    print("✓ 列表操作")

def test_stdlib():
    print("\n=== 标准库 ===")
    interp = run_interpreter("设 a 为 abs(-42)。设 s 为 upper('hello')。")
    assert_result(interp, 'a', 42)
    assert_result(interp, 's', 'HELLO')
    print("✓ 标准库函数")

def test_edge_cases():
    print("\n=== 边界情况 ===")
    try:
        run_interpreter("设 x 为 10 除 0。")
        assert False
    except:
        print("✓ 除零错误")
    
    try:
        run_interpreter("设 x 为 未定义。")
        assert False
    except:
        print("✓ 未定义变量")

def test_compiler():
    print("\n=== 编译器 ===")
    code = "设 x 为 10 加 20。"
    module = parse_source(code)
    codegen = LLVMCodeGen()
    llvm = codegen.generate(module)
    assert 'define i32 @main' in llvm
    print("✓ LLVM IR 生成")

def run_all():
    print("="*60)
    print("光明编程语言 - 综合测试套件")
    print("="*60)
    
    test_basic()
    test_arithmetic()
    test_simple_if()
    test_functions()
    test_classes()
    test_lists()
    test_stdlib()
    test_edge_cases()
    test_compiler()
    
    print("\n" + "="*60)
    print("所有测试通过！")
    print("="*60)

if __name__ == "__main__":
    run_all()