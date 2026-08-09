"""测试列表和字典的编译能力"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_visitor import parse_source
from light_llvm import LLVMCodeGen


def test_list_compile():
    """测试列表编译"""
    print("=" * 70)
    print("测试：列表编译")
    print("=" * 70)

    # 列表字面量和索引访问
    code = '''
《主段》段():
  定义arr等于【10, 20, 30, 40, 50】。
  定义len等于arr之长度。
  定义first等于arr[0]。
  定义last等于arr[4]。
  打印(len)。
  打印(first)。
  打印(last)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print("   ✓ 列表编译成功")
        with open("test_list.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_list.ll")
        
        # 显示部分IR
        print("\n   --- 生成的关键IR代码 ---")
        lines = ir.split('\n')
        for line in lines[:60]:
            print(f"   {line}")
    except Exception as e:
        print(f"   ✗ 列表编译失败: {e}")
        import traceback
        traceback.print_exc()


def test_dict_compile():
    """测试字典编译"""
    print("\n" + "=" * 70)
    print("测试：字典编译")
    print("=" * 70)

    code = '''
《主段》段():
  定义person等于_典(
    "姓名", "张三",
    "年龄", 25,
    "成绩", 95
  )。
  定义name等于person["姓名"]。
  定义age等于person["年龄"]。
  打印(name)。
  打印(age)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print("   ✓ 字典编译成功")
        with open("test_dict.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_dict.ll")
    except Exception as e:
        print(f"   ✗ 字典编译失败: {e}")
        import traceback
        traceback.print_exc()


def test_list_operations():
    """测试列表操作"""
    print("\n" + "=" * 70)
    print("测试：列表操作")
    print("=" * 70)

    code = '''
《主段》段():
  定义arr等于【】。
  listAppend(arr, 10)。
  listAppend(arr, 20)。
  listAppend(arr, 30)。
  定义len等于arr之长度。
  打印(len)。
  定义sum等于arr[0]加arr[1]加arr[2]。
  打印(sum)。
结束。
'''
    try:
        module = parse_source(code)
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        print("   ✓ 列表操作编译成功")
        with open("test_list_ops.ll", "w", encoding="utf-8") as f:
            f.write(ir)
        print("   IR已保存到 test_list_ops.ll")
    except Exception as e:
        print(f"   ✗ 列表操作编译失败: {e}")
        import traceback
        traceback.print_exc()


def show_progress():
    """显示编译能力进展"""
    print("\n" + "=" * 70)
    print("光明编译能力进展")
    print("=" * 70)
    print("""
【已支持】
  ✓ 整数运算
  ✓ 浮点数运算 (double)
  ✓ 变量定义与赋值
  ✓ 函数定义与调用
  ✓ 条件语句 (如果...那么...否则)
  ✓ 循环语句 (当...)
  ✓ 数学函数 (sin, cos, tan, sqrt, pow, exp, log)
  ✓ 字符串操作
  ✓ 列表字面量【新增】
  ✓ 列表索引访问【新增】
  ✓ 列表长度【新增】
  ✓ 列表操作函数【新增】
  ✓ 字典字面量【新增】
  ✓ 字典属性访问【新增】

【待完善】
  ✗ 完整的运行时库实现 (C语言)
  ✗ 编译为独立可执行文件
  ✗ 垃圾回收
  ✗ 类型系统

【编译流程】
  光明源代码 (.light)
       ↓
    解析器 (ANTLR)
       ↓
   AST 抽象语法树
       ↓
  LLVM IR (.ll)
       ↓
  Clang + 运行时库
       ↓
  原生可执行文件 (.exe)
""")
    print("=" * 70)


if __name__ == '__main__':
    test_list_compile()
    test_dict_compile()
    test_list_operations()
    show_progress()