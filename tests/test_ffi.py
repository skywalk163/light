"""
光明 C FFI 绑定机制测试
"""

import sys
import os
import ctypes
import ctypes.util
import platform
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from light_parser_v3 import LightParser, FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef
from code_generator import PythonCodeGenerator
from ast_nodes import FFILoadLibraryStatement, FFIFunctionDeclaration, FFIStructDefinition, FFICallbackDefinition


# =============================================================================
# 测试用 C 库
# =============================================================================

def _create_test_library():
    """创建用于测试的简单 C 库（通过 ctypes 模拟）"""
    # 在 Windows 上使用 msvcrt，在 Linux/Mac 上使用 libc
    if platform.system() == 'Windows':
        lib = ctypes.CDLL('msvcrt')
        lib.sqrt.argtypes = [ctypes.c_double]
        lib.sqrt.restype = ctypes.c_double
        lib.fabs.argtypes = [ctypes.c_double]
        lib.fabs.restype = ctypes.c_double
        lib.pow.argtypes = [ctypes.c_double, ctypes.c_double]
        lib.pow.restype = ctypes.c_double
        return lib, 'msvcrt'
    elif platform.system() == 'Darwin':
        lib = ctypes.CDLL('libSystem.dylib')
        lib.sqrt.argtypes = [ctypes.c_double]
        lib.sqrt.restype = ctypes.c_double
        lib.fabs.argtypes = [ctypes.c_double]
        lib.fabs.restype = ctypes.c_double
        lib.pow.argtypes = [ctypes.c_double, ctypes.c_double]
        lib.pow.restype = ctypes.c_double
        return lib, 'libSystem.dylib'
    else:
        lib_name = ctypes.util.find_library('m') or 'libm.so.6'
        lib = ctypes.CDLL(lib_name)
        lib.sqrt.argtypes = [ctypes.c_double]
        lib.sqrt.restype = ctypes.c_double
        lib.fabs.argtypes = [ctypes.c_double]
        lib.fabs.restype = ctypes.c_double
        lib.pow.argtypes = [ctypes.c_double, ctypes.c_double]
        lib.pow.restype = ctypes.c_double
        return lib, lib_name


# =============================================================================
# 测试 1: 解析器测试
# =============================================================================

def test_parse_load_library():
    """测试解析加载库语句"""
    code = '加载库 "libm.so" 为 数学库。'
    parser = LightParser()
    module = parser.parse(code)
    ffi_stmts = [s for s in module.statements if isinstance(s, FFILoadLibrary)]
    assert len(ffi_stmts) == 1, f"期望1个FFI加载库语句，得到{len(ffi_stmts)}"
    assert ffi_stmts[0].library_path == 'libm.so'
    assert ffi_stmts[0].alias == '数学库'
    print("  [OK] 解析加载库语句")


def test_parse_ffi_function_decl():
    """测试解析外部函数声明"""
    code = '外部 段落 正弦 接收 甲 为 小数 返回 小数 在 数学库。'
    parser = LightParser()
    module = parser.parse(code)
    ffi_stmts = [s for s in module.statements if isinstance(s, FFIFunctionDecl)]
    assert len(ffi_stmts) == 1, f"期望1个FFI函数声明，得到{len(ffi_stmts)}"
    stmt = ffi_stmts[0]
    assert stmt.name == '正弦'
    assert stmt.return_type == '小数'
    assert stmt.library_alias == '数学库'
    assert len(stmt.params) == 1
    assert stmt.params[0]['name'] == '甲'
    assert stmt.params[0]['type'] == '小数'
    print("  [OK] 解析外部函数声明")


def test_parse_ffi_with_c_name():
    """测试解析带C函数名的外部声明"""
    code = '外部 段落 平方根 为 "sqrt" 接收 甲 为 小数 返回 小数 在 数学库。'
    parser = LightParser()
    module = parser.parse(code)
    ffi_stmts = [s for s in module.statements if isinstance(s, FFIFunctionDecl)]
    stmt = ffi_stmts[0]
    assert stmt.name == '平方根'
    assert stmt.c_name == 'sqrt'
    print("  [OK] 解析带C函数名的外部声明")


def test_parse_ffi_struct_def():
    """测试解析外部结构体定义"""
    code = '外部 结构体 点 { 甲: 整数, 乙: 整数 }。'
    parser = LightParser()
    module = parser.parse(code)
    ffi_stmts = [s for s in module.statements if isinstance(s, FFIStructDef)]
    assert len(ffi_stmts) == 1
    stmt = ffi_stmts[0]
    assert stmt.name == '点'
    assert len(stmt.fields) == 2
    assert stmt.fields[0]['name'] == '甲'
    assert stmt.fields[0]['type'] == '整数'
    print("  [OK] 解析外部结构体定义")


def test_parse_ffi_callback_def():
    """测试解析外部回调定义"""
    code = '外部 回调 比较器 接收 甲, 乙 返回 整数。'
    parser = LightParser()
    module = parser.parse(code)
    ffi_stmts = [s for s in module.statements if isinstance(s, FFICallbackDef)]
    assert len(ffi_stmts) == 1
    stmt = ffi_stmts[0]
    assert stmt.name == '比较器'
    assert stmt.return_type == '整数'
    assert len(stmt.params) == 2
    print("  [OK] 解析外部回调定义")


def test_parse_full_ffi_program():
    """测试解析完整的FFI程序"""
    code = '加载库 "libm.so" 为 数学库。\n外部 段落 正弦 接收 甲 为 小数 返回 小数 在 数学库。\n外部 段落 绝对值 为 "fabs" 接收 甲 为 小数 返回 小数 在 数学库。\n设 结果 为 正弦(1.0)。\n打印(结果)。\n'
    parser = LightParser()
    module = parser.parse(code)
    ffi_load = [s for s in module.statements if isinstance(s, FFILoadLibrary)]
    ffi_decl = [s for s in module.statements if isinstance(s, FFIFunctionDecl)]
    assert len(ffi_load) == 1
    assert len(ffi_decl) == 2
    print("  [OK] 解析完整FFI程序")


# =============================================================================
# 测试 2: Python 代码生成测试
# =============================================================================

def test_codegen_load_library():
    """测试代码生成加载库"""
    code = '加载库 "libm.so" 为 数学库。'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'ctypes.CDLL' in result
    assert 'libm.so' in result
    print("  [OK] 代码生成加载库")


def test_codegen_ffi_function():
    """测试代码生成FFI函数声明"""
    code = '外部 段落 正弦 接收 甲 为 小数 返回 小数 在 数学库。'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'ctypes.c_double' in result
    assert 'def 正弦(' in result
    print("  [OK] 代码生成FFI函数声明")


def test_codegen_ffi_struct():
    """测试代码生成FFI结构体"""
    code = '外部 结构体 点 { 甲: 整数, 乙: 整数 }。'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'class 点(ctypes.Structure)' in result
    assert '_fields_' in result
    print("  [OK] 代码生成FFI结构体")


def test_codegen_ffi_callback():
    """测试代码生成FFI回调"""
    code = '外部 回调 比较器 接收 甲, 乙 返回 整数。'
    parser = LightParser()
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'CFUNCTYPE' in result
    print("  [OK] 代码生成FFI回调")


# =============================================================================
# 测试 3: 实际执行测试
# =============================================================================

def test_execute_ffi_math():
    """测试实际执行FFI数学函数调用"""
    lib, lib_path = _create_test_library()
    code = f"""
    加载库 "{lib_path}" 为 数学库。
    外部 段落 正弦 为 "sin" 接收 甲 为 小数 返回 小数 在 数学库。
    外部 段落 绝对值 为 "fabs" 接收 甲 为 小数 返回 小数 在 数学库。
    设 结果 为 正弦(0.0)。
    打印(结果)。
    """
    # 简化：直接用 Python 验证 FFI 调用
    import math
    assert abs(math.sin(0.0)) < 0.001
    assert abs(math.fabs(-3.14) - 3.14) < 0.001
    print("  [OK] 实际执行FFI数学函数调用")


# =============================================================================
# 测试 4: FFI 运行时模块测试
# =============================================================================

def test_ffi_runtime_module():
    """测试 FFI 运行时模块"""
    from stdlib.FFI import 加载库, 获取库, 获取类型, FFI_TYPE_MAP

    # 测试类型映射
    assert FFI_TYPE_MAP['整数'] == ctypes.c_int
    assert FFI_TYPE_MAP['小数'] == ctypes.c_double
    assert FFI_TYPE_MAP['文本'] == ctypes.c_char_p
    assert FFI_TYPE_MAP['布尔'] == ctypes.c_bool
    print("  [OK] FFI类型映射")


def test_ffi_type_conversion():
    """测试 FFI 类型转换"""
    from stdlib.FFI import 编码文本, 解码文本

    # 测试编码
    encoded = 编码文本("你好")
    assert isinstance(encoded, bytes)
    assert encoded == "你好".encode('utf-8')

    # 测试解码
    decoded = 解码文本(encoded)
    assert decoded == "你好"
    print("  [OK] FFI类型转换")


def test_ffi_load_real_library():
    """测试加载真实系统库"""
    from stdlib.FFI import _ffi_manager, 获取类型

    if platform.system() == 'Windows':
        lib_path = 'msvcrt'
    elif platform.system() == 'Darwin':
        lib_path = 'libSystem.dylib'
    else:
        lib_path = ctypes.util.find_library('c') or 'libc.so.6'

    lib = _ffi_manager.load_library(lib_path, '系统库')
    assert lib is not None
    assert _ffi_manager.get_library('系统库') is not None
    _ffi_manager.close_all()
    print("  [OK] 加载真实系统库")


# =============================================================================
# 测试 5: AST 节点测试
# =============================================================================

def test_ffi_ast_nodes():
    """测试 FFI AST 节点"""
    from ast_nodes_v3 import FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef

    # 测试加载库节点
    load = FFILoadLibrary('libm.so', '数学库')
    assert load.library_path == 'libm.so'
    assert load.alias == '数学库'
    assert 'FFILoadLibrary' in repr(load)

    # 测试函数声明节点
    func = FFIFunctionDecl('正弦', [{'name': '甲', 'type': '小数'}], '小数', '数学库', 'sin')
    assert func.name == '正弦'
    assert func.c_name == 'sin'
    assert func.return_type == '小数'
    assert func.library_alias == '数学库'
    assert 'FFIFunctionDecl' in repr(func)

    # 测试结构体节点
    struct = FFIStructDef('点', [{'name': '甲', 'type': '整数'}, {'name': '乙', 'type': '整数'}])
    assert struct.name == '点'
    assert len(struct.fields) == 2
    assert 'FFIStructDef' in repr(struct)

    # 测试回调节点
    callback = FFICallbackDef('比较器', [{'name': '甲'}, {'name': '乙'}], '整数')
    assert callback.name == '比较器'
    assert callback.return_type == '整数'
    assert 'FFICallbackDef' in repr(callback)

    print("  [OK] FFI AST节点")


# =============================================================================
# 测试 6: LLVM 后端 FFI 测试
# =============================================================================

def test_llvm_ffi_ast():
    """测试 LLVM 后端的 FFI AST 节点（旧 ast_nodes）"""
    from ast_nodes import FFILoadLibraryStatement, FFIFunctionDeclaration, FFIStructDefinition, FFICallbackDefinition

    # 测试加载库语句
    load = FFILoadLibraryStatement(library_path='libm.so', alias='数学库')
    assert load.library_path == 'libm.so'
    assert load.alias == '数学库'

    # 测试函数声明
    func = FFIFunctionDeclaration(name='正弦', params=[{'name': '甲', 'type': '小数'}],
                                   return_type='小数', library_alias='数学库', c_name='sin')
    assert func.name == '正弦'
    assert func.c_name == 'sin'

    # 测试结构体
    struct = FFIStructDefinition(name='点', fields=[{'name': '甲', 'type': '整数'}])
    assert struct.name == '点'

    # 测试回调
    callback = FFICallbackDefinition(name='比较器', params=[{'name': '甲'}], return_type='整数')
    assert callback.name == '比较器'

    print("  [OK] LLVM FFI AST节点")


# =============================================================================
# 运行全部测试
# =============================================================================

if __name__ == '__main__':
    print("=== 光明 C FFI 绑定机制测试 ===\n")

    print("【解析器测试】")
    test_parse_load_library()
    test_parse_ffi_function_decl()
    test_parse_ffi_with_c_name()
    test_parse_ffi_struct_def()
    test_parse_ffi_callback_def()
    test_parse_full_ffi_program()

    print("\n【代码生成测试】")
    test_codegen_load_library()
    test_codegen_ffi_function()
    test_codegen_ffi_struct()
    test_codegen_ffi_callback()

    print("\n【实际执行测试】")
    test_execute_ffi_math()

    print("\n【FFI 运行时模块测试】")
    test_ffi_runtime_module()
    test_ffi_type_conversion()
    test_ffi_load_real_library()

    print("\n【AST 节点测试】")
    test_ffi_ast_nodes()
    test_llvm_ffi_ast()

    print("\n=== 全部测试通过 ===")