"""测试光明编译能力"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_visitor import parse_source
from light_llvm import LLVMCodeGen


def test_basic_compile():
    """测试基础编译"""
    print("=" * 70)
    print("测试：基础编译能力")
    print("=" * 70)

    # 简单算术运算 - 使用正确的光明语法
    code1 = '''
《主段》段():
  定义x等于10。
  定义y等于20。
  定义z等于x加y。
  打印(z)。
结束。
'''
    print("\n1. 简单算术运算")
    try:
        module = parse_source(code1)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print(f"   ✓ 编译成功，IR长度: {len(ir)} 字符")
        # 保存IR
        with open("test_basic.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_basic.ll")
    except Exception as e:
        print(f"   ✗ 编译失败: {e}")


def test_function_compile():
    """测试函数编译"""
    print("\n2. 函数定义与调用")
    code = '''
《计算段》段(a, b):
  定义c等于a乘b。
  返回c。
结束。

《主段》段():
  定义x等于10。
  定义y等于20。
  定义z等于《计算段》(x, y)。
  打印(z)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print(f"   ✓ 函数编译成功")
        with open("test_func.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_func.ll")
    except Exception as e:
        print(f"   ✗ 函数编译失败: {e}")


def test_loop_compile():
    """测试循环编译"""
    print("\n3. 循环语句")
    code = '''
《主段》段():
  定义sum等于0。
  定义i等于0。
  当i小于100：
    sum等于sum加i。
    i等于i加1。
  结束。
  打印(sum)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print(f"   ✓ 循环编译成功")
        with open("test_loop.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_loop.ll")
    except Exception as e:
        print(f"   ✗ 循环编译失败: {e}")


def test_float_compile():
    """测试浮点数编译"""
    print("\n4. 浮点数运算")
    code = '''
《主段》段():
  定义pi等于3.14159。
  定义r等于2.0。
  定义area等于pi乘r乘r。
  打印(area)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print(f"   ✓ 浮点数编译成功")
        with open("test_float.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_float.ll")
    except Exception as e:
        print(f"   ✗ 浮点数编译失败: {e}")


def test_if_compile():
    """测试条件语句"""
    print("\n5. 条件语句")
    code = '''
《主段》段():
  定义x等于10。
  如果x大于5那么：
    打印(1)。
  否则：
    打印(0)。
  结束。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print(f"   ✓ 条件语句编译成功")
        with open("test_if.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_if.ll")
    except Exception as e:
        print(f"   ✗ 条件语句编译失败: {e}")


def show_capabilities():
    """显示编译能力"""
    print("\n" + "=" * 70)
    print("光明编译能力总结")
    print("=" * 70)
    print("""
【已支持】
  ✓ 整数运算 (加、减、乘、除、模)
  ✓ 浮点数运算 (双精度 double)
  ✓ 变量定义与赋值
  ✓ 函数定义与调用
  ✓ 条件语句 (如果...那么...否则)
  ✓ 循环语句 (当...)
  ✓ 数学函数 (sin, cos, tan, sqrt, pow, exp, log)
  ✓ 字符串操作 (strlen, strcmp, strstr)
  ✓ 打印输出 (printf)

【待完善】
  ✗ 列表/数组操作
  ✗ 典/字典操作
  ✗ 模块导入
  ✗ 高级类型系统
  ✗ 闭包和 lambda

【编译流程】
  光明源代码 → AST → LLVM IR → 原生机器码 (.exe)
""")
    print("=" * 70)


if __name__ == '__main__':
    test_basic_compile()
    test_function_compile()
    test_loop_compile()
    test_float_compile()
    test_if_compile()
    show_capabilities()