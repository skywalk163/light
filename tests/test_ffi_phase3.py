"""
C FFI 第三阶段测试：枚举/联合体/变长参数/回调/结构体传值/跨平台路径
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError, FFIEnumDef, FFIUnionDef, FFIVarArgsDecl, FFICreateCallback, FFIStructByValue, FFILibraryPath, FFILoadLibrary, FFIStructDef, FFICallbackDef


# =============================================================================
# 测试1：解析 C 枚举定义
# =============================================================================

def test_parse_ffi_enum_def():
    parser = LightParser()
    code = '外部 枚举 颜色 { 红, 绿, 蓝 }。'
    module = parser.parse(code)
    stmts = module.statements
    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, FFIEnumDef)
    assert stmt.name == '颜色'
    assert stmt.values == {'红': 0, '绿': 1, '蓝': 2}


def test_parse_ffi_enum_with_values():
    parser = LightParser()
    code = '外部 枚举 错误码 { 成功 = 0, 失败 = 1, 超时 = 2 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIEnumDef)
    assert stmt.name == '错误码'
    assert stmt.values == {'成功': 0, '失败': 1, '超时': 2}


def test_parse_ffi_enum_with_jump_values():
    parser = LightParser()
    code = '外部 枚举 信号 { SIGINT = 2, SIGKILL = 9, SIGTERM = 15 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert stmt.values == {'SIGINT': 2, 'SIGKILL': 9, 'SIGTERM': 15}


# =============================================================================
# 测试2：解析 C 联合体定义
# =============================================================================

def test_parse_ffi_union_def():
    parser = LightParser()
    code = '外部 联合体 数据 { 整数: 整数, 小数: 小数, 文本: 文本 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIUnionDef)
    assert stmt.name == '数据'
    assert len(stmt.fields) == 3
    assert stmt.fields[0] == {'name': '整数', 'type': '整数'}
    assert stmt.fields[1] == {'name': '小数', 'type': '小数'}
    assert stmt.fields[2] == {'name': '文本', 'type': '文本'}


# =============================================================================
# 测试3：解析变长参数声明
# =============================================================================

def test_parse_ffi_varargs_decl():
    parser = LightParser()
    code = '外部 变长参数 段落 格式化输出 接收 格式: 文本 返回 整数 在 mylib。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIVarArgsDecl)
    assert stmt.name == '格式化输出'
    assert len(stmt.params) == 1
    assert stmt.params[0]['name'] == '格式'
    assert stmt.params[0]['type'] == '文本'
    assert stmt.return_type == '整数'
    assert stmt.library_alias == 'mylib'


def test_parse_ffi_varargs_with_c_name():
    parser = LightParser()
    code = '外部 变长参数 段落 打印 为 "printf" 接收 格式: 文本 返回 整数 在 libc。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIVarArgsDecl)
    assert stmt.name == '打印'
    assert stmt.c_name == 'printf'
    assert stmt.library_alias == 'libc'


# =============================================================================
# 测试4：解析完整 Phase 3 FFI 程序
# =============================================================================

def test_parse_full_phase3_program():
    parser = LightParser()
    code = '加载库 "libm.so" 为 mathlib。\n外部 枚举 颜色 { 红 = 0, 绿 = 1, 蓝 = 2 }。\n外部 联合体 数值 { 整数: 整数, 浮点: 小数 }。\n外部 结构体 点 { x: 小数, y: 小数 }。\n外部 回调 比较器 接收 甲: 整数, 乙: 整数 返回 整数。\n外部 变长参数 段落 格式化 接收 模板: 文本 返回 整数 在 stdlib。\n外部 段落 距离 接收 甲: 小数, 乙: 小数 返回 小数 在 mathlib。'
    module = parser.parse(code)
    stmts = module.statements
    assert len(stmts) == 7
    assert isinstance(stmts[0], FFILoadLibrary)
    assert isinstance(stmts[1], FFIEnumDef)
    assert isinstance(stmts[2], FFIUnionDef)
    assert isinstance(stmts[3], FFIStructDef)
    assert isinstance(stmts[4], FFICallbackDef)
    assert isinstance(stmts[5], FFIVarArgsDecl)
    assert stmts[5].name == '格式化'


# =============================================================================
# 测试5：代码生成 - 枚举
# =============================================================================

def test_codegen_ffi_enum():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 枚举 颜色 { 红 = 0, 绿 = 1, 蓝 = 2 }。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert 'class 颜色:' in py_code or 'class 颜色' in py_code
    assert '红 = 0' in py_code or '红=0' in py_code
    assert '绿 = 1' in py_code or '绿=1' in py_code
    assert '蓝 = 2' in py_code or '蓝=2' in py_code


# =============================================================================
# 测试6：代码生成 - 联合体
# =============================================================================

def test_codegen_ffi_union():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 联合体 数据 { 整: 整数, 浮: 小数 }。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert 'ctypes.Union' in py_code
    assert '_fields_' in py_code


# =============================================================================
# 测试7：代码生成 - 变长参数
# =============================================================================

def test_codegen_ffi_varargs():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 变长参数 段落 打印 为 "printf" 接收 格式: 文本 返回 整数 在 libc。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert 'printf' in py_code
    assert '*args' in py_code


# =============================================================================
# 测试8：运行时 - 枚举
# =============================================================================

def test_runtime_enum():
    from stdlib.FFI import 创建枚举
    enum_type = 创建枚举('颜色', {'红': 0, '绿': 1, '蓝': 2})
    assert enum_type.红 == 0
    assert enum_type.绿 == 1
    assert enum_type.蓝 == 2


# =============================================================================
# 测试9：运行时 - 联合体
# =============================================================================

def test_runtime_union():
    import ctypes
    from stdlib.FFI import 创建联合体
    union_type = 创建联合体('数值', [('整数', ctypes.c_int), ('浮点', ctypes.c_double)])
    assert issubclass(union_type, ctypes.Union)
    instance = union_type()
    instance.整数 = 42
    assert instance.整数 == 42


# =============================================================================
# 测试10：运行时 - 结构体按值传递
# =============================================================================

def test_runtime_struct_by_value():
    import ctypes
    from stdlib.FFI import 创建结构体值
    class Point(ctypes.Structure):
        _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]
    pt = 创建结构体值(Point, x=3.0, y=4.0)
    assert isinstance(pt, Point)
    assert pt.x == 3.0
    assert pt.y == 4.0


# =============================================================================
# 测试11：运行时 - 回调函数
# =============================================================================

def test_runtime_callback():
    import ctypes
    from stdlib.FFI import 创建回调函数
    def my_callback(a, b):
        return a + b
    cb_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)
    cb = 创建回调函数(cb_type, my_callback)
    assert cb is not None
    result = cb(3, 5)
    assert result == 8


# =============================================================================
# 测试12：运行时 - 跨平台库路径
# =============================================================================

def test_runtime_library_path():
    from stdlib.FFI import 解析库路径, 获取平台
    plat = 获取平台()
    assert plat in ('windows', 'linux', 'darwin', 'freebsd')
    path = 解析库路径({'win': 'kernel32.dll', 'linux': 'libc.so.6', 'mac': 'libc.dylib'})
    assert isinstance(path, str)


# =============================================================================
# 测试13：运行时 - 结构体工具函数
# =============================================================================

def test_runtime_struct_tools():
    import ctypes
    from stdlib.FFI import 结构体大小, 结构体转字节, 字节转结构体
    class Point(ctypes.Structure):
        _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]
    size = 结构体大小(Point)
    assert size == 16  # 2 * 8 bytes
    pt = Point(3.0, 4.0)
    data = 结构体转字节(pt)
    assert len(data) == 16
    pt2 = 字节转结构体(data, Point)
    assert pt2.x == 3.0
    assert pt2.y == 4.0


# =============================================================================
# 测试14：运行时 - 查找库
# =============================================================================

def test_runtime_find_library():
    from stdlib.FFI import 查找库
    result = 查找库('c')
    # 在 Windows 上可能返回 None，但至少不抛异常
    if result is not None:
        assert isinstance(result, str)


# =============================================================================
# 测试15：运行时 - 变长参数调用
# =============================================================================

def test_runtime_varargs_call():
    import ctypes
    from stdlib.FFI import 加载库, 声明函数, 变长参数调用
    # 加载 libc / msvcrt
    if sys.platform == 'win32':
        libc = ctypes.CDLL('msvcrt')
    elif sys.platform.startswith('freebsd'):
        libc = ctypes.CDLL('libc.so')
    else:
        libc = ctypes.CDLL('libc.so.6')
    from stdlib.FFI import _ffi_manager
    _ffi_manager._libraries['testlib'] = type('FakeLib', (), {'_handle': libc, 'get_function': lambda self, name: getattr(libc, name)})()
    result = 变长参数调用('testlib', 'sprintf', [ctypes.create_string_buffer(100), b'%d'], [42])
    # sprintf returns number of chars written
    assert result > 0


# =============================================================================
# 测试16：解析 - 枚举定义后解析其他语句
# =============================================================================

def test_parse_enum_then_function():
    parser = LightParser()
    code = '外部 枚举 状态 { 激活, 停用 }。外部 段落 获取状态 返回 整数 在 lib。'
    module = parser.parse(code)
    assert len(module.statements) == 2
    assert isinstance(module.statements[0], FFIEnumDef)
    assert module.statements[0].name == '状态'


# =============================================================================
# 测试17：解析 - 联合体定义后解析结构体
# =============================================================================

def test_parse_union_then_struct():
    parser = LightParser()
    code = '外部 联合体 值 { i: 整数, d: 小数 }。外部 结构体 包装器 { 标签: 整数, 值: 值 }。'
    module = parser.parse(code)
    assert len(module.statements) == 2
    assert isinstance(module.statements[0], FFIUnionDef)
    assert isinstance(module.statements[1], FFIStructDef)


# =============================================================================
# 测试18：运行时 - 取地址增强
# =============================================================================

def test_runtime_address_of_enhanced():
    import ctypes
    from stdlib.FFI import 取地址增强
    val = ctypes.c_int(42)
    ptr = 取地址增强(val)
    assert ptr is not None
    assert ptr.contents.value == 42


# =============================================================================
# 测试19：AST 节点兼容性
# =============================================================================

def test_new_ffi_ast_nodes_phase3():
    import ast_nodes as old_ast
    # 测试旧 AST 中有新节点
    assert hasattr(old_ast, 'FFIEnumDef')
    assert hasattr(old_ast, 'FFIUnionDef')
    assert hasattr(old_ast, 'FFICreateCallback')
    assert hasattr(old_ast, 'FFIVarArgsDecl')
    assert hasattr(old_ast, 'FFIStructByValue')
    assert hasattr(old_ast, 'FFILibraryPath')
    # 测试可实例化
    enum_def = old_ast.FFIEnumDef(name='测试', values={'甲': 0, '乙': 1})
    assert enum_def.name == '测试'
    union_def = old_ast.FFIUnionDef(name='测试', fields=[{'name': 'a', 'type': '整数'}])
    assert union_def.name == '测试'
    varargs = old_ast.FFIVarArgsDecl(name='测试', params=[], library_alias='lib')
    assert varargs.name == '测试'


# =============================================================================
# 测试20：LLVM 后端兼容性
# =============================================================================

def test_llvm_phase3_ast():
    import ast_nodes as old_ast
    from llvm.codegen import LLVMCodeGen
    gen = LLVMCodeGen()
    # 测试新版 FFI 节点可以被 LLVM 后端收集
    stmt = old_ast.FFIEnumDef(name='颜色', values={'红': 0})
    gen._collect_statement(stmt)
    assert len(gen._module_statements) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])