"""
光明 C FFI 第二阶段测试：指针、数组、错误处理
"""

import sys
import os
import ctypes
import platform

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from light_parser_v3 import LightParser, FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef
from light_parser_v3 import FFIPointerType, FFIArrayType, FFIAddressOf, FFIDereference
from light_parser_v3 import FFIPointerOffset, FFISetPointerValue, FFIAllocMemory, FFIFreeMemory
from light_parser_v3 import FFICreateArray, FFISetArrayElement, FFIGetLastError, FFIGetErrno, FFISetErrno, FFITryCatch
from code_generator import PythonCodeGenerator


# =============================================================================
# 测试 1: 解析器 - 指针/数组/错误处理语法
# =============================================================================

def test_parse_ffi_try_catch():
    """测试解析 FFI try-catch"""
    code = '尝试：\n设 结果 为 正弦(1.0)。\n捕获 外部错误 为 甲：\n打印("错误：" + 甲)。\n。\n'
    parser = LightParser()
    module = parser.parse(code)
    # 应该解析为 TryStmt
    assert len(module.statements) > 0
    print("  [OK] 解析 FFI try-catch")


def test_parse_pointer_operations():
    """测试解析指针操作语法"""
    code = '设 甲 为 取地址(乙)。\n设 丙 为 解引用(甲)。\n'
    parser = LightParser()
    module = parser.parse(code)
    assert len(module.statements) == 2
    print("  [OK] 解析指针操作")


def test_parse_array_operations():
    """测试解析数组操作语法"""
    code = '设 数组 为 创建数组(整数, 5)。\n设置数组(数组, 0, 42)。\n'
    parser = LightParser()
    module = parser.parse(code)
    assert len(module.statements) == 2
    print("  [OK] 解析数组操作")


def test_parse_memory_operations():
    """测试解析内存操作语法"""
    code = '设 内存 为 分配内存(1024)。\n释放内存(内存)。\n'
    parser = LightParser()
    module = parser.parse(code)
    assert len(module.statements) == 2
    print("  [OK] 解析内存操作")


def test_parse_error_operations():
    """测试解析错误操作语法"""
    code = '设 错误码 为 系统错误码()。\n设系统错误码(0)。\n设 错误 为 FFI错误()。\n'
    parser = LightParser()
    module = parser.parse(code)
    assert len(module.statements) == 3
    print("  [OK] 解析错误操作")


# =============================================================================
# 测试 2: 代码生成 - 指针/数组/错误处理
# =============================================================================

def test_codegen_pointer_ops():
    """测试代码生成指针操作"""
    code = '设 甲 为 取地址(乙)。\n设 丙 为 解引用(甲)。\n'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert '_light_ffi.取地址' in result
    assert '_light_ffi.解引用' in result
    print("  [OK] 代码生成指针操作")


def test_codegen_array_ops():
    """测试代码生成数组操作"""
    code = '设 数组 为 创建数组(整数, 5)。\n'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert '_light_ffi.创建数组' in result
    print("  [OK] 代码生成数组操作")


def test_codegen_error_ops():
    """测试代码生成错误操作"""
    code = '设 错误码 为 系统错误码()。\n'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert '_light_ffi.获取系统错误码' in result
    print("  [OK] 代码生成错误操作")


def test_codegen_ffi_try_catch():
    """测试代码生成 FFI try-catch"""
    code = '尝试：\n设 结果 为 正弦(1.0)。\n捕获 外部错误 为 甲：\n打印("错误：" + 甲)。\n。\n'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'ctypes.ArgumentError' in result or 'try:' in result
    print("  [OK] 代码生成 FFI try-catch")


# =============================================================================
# 测试 3: 运行时 - 指针操作
# =============================================================================

def test_runtime_pointer_ops():
    """测试运行时指针操作"""
    from stdlib.FFI import 取地址, 解引用, 设指针值, 创建数组

    # 创建整数变量并取地址
    arr = 创建数组('整数', 1)
    arr[0] = 42
    ptr = 取地址(arr)
    assert ptr is not None

    # 解引用
    val = 解引用(arr)
    assert val == 42

    print("  [OK] 运行时指针操作")


def test_runtime_pointer_value():
    """测试运行时设指针值"""
    from stdlib.FFI import 设指针值, 创建数组

    arr = 创建数组('整数', 1)
    设指针值(arr, 100)
    assert arr[0] == 100

    print("  [OK] 运行时设指针值")


# =============================================================================
# 测试 4: 运行时 - 数组操作
# =============================================================================

def test_runtime_array_ops():
    """测试运行时数组操作"""
    from stdlib.FFI import 创建数组, 设置数组

    # 创建整数数组
    arr = 创建数组('整数', 10)
    assert len(arr) == 10

    # 设置数组值
    设置数组(arr, 0, 10)
    设置数组(arr, 5, 50)
    assert arr[0] == 10
    assert arr[5] == 50

    # 创建小数数组
    arr2 = 创建数组('小数', 5)
    设置数组(arr2, 0, 3.14)
    assert abs(arr2[0] - 3.14) < 0.001

    print("  [OK] 运行时数组操作")


# =============================================================================
# 测试 5: 运行时 - 内存操作
# =============================================================================

def test_runtime_memory_ops():
    """测试运行时内存操作"""
    from stdlib.FFI import 分配内存, 释放内存, 设指针值

    mem = 分配内存(256)
    assert mem is not None
    assert len(mem) == 256

    释放内存(mem)
    print("  [OK] 运行时内存操作")


# =============================================================================
# 测试 6: 运行时 - 错误处理
# =============================================================================

def test_runtime_errno():
    """测试运行时 errno 操作"""
    from stdlib.FFI import 获取系统错误码, 设系统错误码

    设系统错误码(0)
    assert 获取系统错误码() == 0

    设系统错误码(22)  # EINVAL
    assert 获取系统错误码() == 22

    设系统错误码(0)
    print("  [OK] 运行时 errno 操作")


def test_runtime_ffi_error():
    """测试运行时 FFI 错误获取"""
    from stdlib.FFI import 获取FFI错误, _set_ffi_error

    _set_ffi_error("测试错误")
    assert 获取FFI错误() == "测试错误"

    _set_ffi_error(None)
    assert 获取FFI错误() == ''
    print("  [OK] 运行时 FFI 错误获取")


# =============================================================================
# 测试 7: 物理库测试 - 完整流程
# =============================================================================

def test_ffi_full_workflow():
    """测试完整的 FFI 工作流：加载库→声明函数→调用→错误处理"""
    from stdlib.FFI import _ffi_manager, 获取类型, 获取系统错误码, 设系统错误码

    # 加载系统数学库
    if platform.system() == 'Windows':
        lib_path = 'msvcrt'
    elif platform.system() == 'Darwin':
        lib_path = 'libSystem.dylib'
    elif platform.system() == 'FreeBSD':
        lib_path = 'libm.so'
    else:
        lib_path = 'libm.so.6'

    lib = _ffi_manager.load_library(lib_path, '测试库')
    assert lib is not None

    # 声明 sqrt 函数
    lib.declare_function('sqrt', [ctypes.c_double], ctypes.c_double)
    func = lib.get_function('sqrt')
    result = func(16.0)
    assert abs(result - 4.0) < 0.001

    # 错误处理：传入无效参数
    设系统错误码(0)
    try:
        func(-1.0)  # sqrt 负数
    except:
        pass

    _ffi_manager.close_all()
    print("  [OK] 完整 FFI 工作流")


# =============================================================================
# 测试 8: AST 节点测试
# =============================================================================

def test_new_ffi_ast_nodes():
    """测试新的 FFI AST 节点"""
    from ast_nodes_v3 import FFIPointerType, FFIArrayType, FFIAddressOf, FFIDereference
    from ast_nodes_v3 import FFIPointerOffset, FFISetPointerValue, FFIAllocMemory, FFIFreeMemory
    from ast_nodes_v3 import FFICreateArray, FFISetArrayElement, FFIGetLastError, FFIGetErrno, FFISetErrno, FFITryCatch

    # 指针类型
    p = FFIPointerType('整数')
    assert p.base_type == '整数'
    assert '指针' in repr(p)

    # 数组类型
    a = FFIArrayType('整数', 5)
    assert a.base_type == '整数'
    assert a.size == 5

    # 错误节点
    e = FFIGetLastError()
    assert '获取FFI错误' in repr(e)

    err = FFIGetErrno()
    assert '获取系统错误码' in repr(err)

    set_err = FFISetErrno(0)
    assert '设系统错误码' in repr(set_err)

    # FFI try-catch
    tc = FFITryCatch([], '错误', [])
    assert tc.error_var == '错误'
    assert 'FFITryCatch' in repr(tc)

    print("  [OK] 新 FFI AST 节点")


# =============================================================================
# 运行全部测试
# =============================================================================

if __name__ == '__main__':
    print("=== 光明 C FFI 第二阶段测试：指针/数组/错误处理 ===\n")

    print("【解析器测试】")
    test_parse_ffi_try_catch()
    test_parse_pointer_operations()
    test_parse_array_operations()
    test_parse_memory_operations()
    test_parse_error_operations()

    print("\n【代码生成测试】")
    test_codegen_pointer_ops()
    test_codegen_array_ops()
    test_codegen_error_ops()
    test_codegen_ffi_try_catch()

    print("\n【运行时 - 指针操作】")
    test_runtime_pointer_ops()
    test_runtime_pointer_value()

    print("\n【运行时 - 数组操作】")
    test_runtime_array_ops()

    print("\n【运行时 - 内存操作】")
    test_runtime_memory_ops()

    print("\n【运行时 - 错误处理】")
    test_runtime_errno()
    test_runtime_ffi_error()

    print("\n【综合测试】")
    test_ffi_full_workflow()

    print("\n【AST 节点测试】")
    test_new_ffi_ast_nodes()

    print("\n=== 全部测试通过 ===")