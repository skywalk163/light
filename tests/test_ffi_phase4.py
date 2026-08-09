"""
C FFI 第四阶段测试：typedef/位域/函数指针/回调生命周期/调试/预处理器
"""
import sys
import os
import ctypes
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from light_parser_v3 import FFITypedefDef, FFIBitfieldDef, FFIFuncPtrDef, FFIDebugConfig, FFIPreprocessorDef


# =============================================================================
# 测试1：解析 C 类型别名
# =============================================================================

def test_parse_ffi_typedef():
    parser = LightParser()
    code = '外部 类型别名 尺寸 为 整数。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFITypedefDef)
    assert stmt.name == '尺寸'
    assert stmt.base_type == '整数'


def test_parse_ffi_typedef_simple():
    parser = LightParser()
    code = '外部 类型别名 标签。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFITypedefDef)
    assert stmt.name == '标签'
    assert stmt.base_type == '标签'


# =============================================================================
# 测试2：解析 C 位域定义
# =============================================================================

def test_parse_ffi_bitfield():
    parser = LightParser()
    code = '外部 位域 标志 : 整数 { 读: 1, 写: 1, 执行: 1 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIBitfieldDef)
    assert stmt.name == '标志'
    assert stmt.base_type == '整数'
    assert len(stmt.fields) == 3
    assert stmt.fields[0] == {'name': '读', 'bits': 1}
    assert stmt.fields[1] == {'name': '写', 'bits': 1}
    assert stmt.fields[2] == {'name': '执行', 'bits': 1}


def test_parse_ffi_bitfield_multi_bit():
    parser = LightParser()
    code = '外部 位域 寄存器 : 整数 { 模式: 2, 启用: 1, 速率: 3 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert stmt.fields[0] == {'name': '模式', 'bits': 2}
    assert stmt.fields[2] == {'name': '速率', 'bits': 3}


# =============================================================================
# 测试3：解析 C 函数指针
# =============================================================================

def test_parse_ffi_funcptr():
    parser = LightParser()
    code = '外部 函数指针 比较器 接收 甲: 整数, 乙: 整数 返回 整数。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIFuncPtrDef)
    assert stmt.name == '比较器'
    assert len(stmt.params) == 2
    assert stmt.params[0] == {'name': '甲', 'type': '整数'}
    assert stmt.return_type == '整数'


def test_parse_ffi_funcptr_void():
    parser = LightParser()
    code = '外部 函数指针 回调 接收 文本。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIFuncPtrDef)
    assert stmt.name == '回调'
    assert len(stmt.params) == 1
    assert stmt.params[0]['name'] == '文本'


# =============================================================================
# 测试4：解析 FFI 调试配置
# =============================================================================

def test_parse_ffi_debug():
    parser = LightParser()
    code = '外部 调试 { 开启, 记录调用, 记录类型, 追踪内存 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIDebugConfig)
    assert stmt.enabled == True
    assert stmt.log_calls == True
    assert stmt.log_types == True
    assert stmt.trace_memory == True


def test_parse_ffi_debug_disabled():
    parser = LightParser()
    code = '外部 调试 { 关闭 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert stmt.enabled == False


# =============================================================================
# 测试5：解析 C 预处理器宏
# =============================================================================

def test_parse_ffi_preprocessor():
    parser = LightParser()
    code = '外部 宏 缓冲区大小 为 1024。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIPreprocessorDef)
    assert stmt.name == '缓冲区大小'
    assert stmt.value == '1024'


def test_parse_ffi_preprocessor_string():
    parser = LightParser()
    code = '外部 宏 版本 为 "1.0.0"。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert stmt.value == '1.0.0'


# =============================================================================
# 测试6：解析完整 Phase 4 程序
# =============================================================================

def test_parse_full_phase4_program():
    parser = LightParser()
    code = (
        '外部 类型别名 尺寸 为 整数。\n'
        '外部 位域 标志 : 整数 { 读: 1, 写: 1 }。\n'
        '外部 函数指针 回调 接收 整数 返回 无。\n'
        '外部 调试 { 开启, 记录调用 }。\n'
        '外部 宏 最大连接 为 100。'
    )
    module = parser.parse(code)
    assert len(module.statements) == 5
    assert isinstance(module.statements[0], FFITypedefDef)
    assert isinstance(module.statements[1], FFIBitfieldDef)
    assert isinstance(module.statements[2], FFIFuncPtrDef)
    assert isinstance(module.statements[3], FFIDebugConfig)
    assert isinstance(module.statements[4], FFIPreprocessorDef)


# =============================================================================
# 测试7：代码生成 - typedef
# =============================================================================

def test_codegen_ffi_typedef():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 类型别名 尺寸 为 整数。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert '尺寸' in py_code
    assert 'ctypes' in py_code


# =============================================================================
# 测试8：代码生成 - 位域
# =============================================================================

def test_codegen_ffi_bitfield():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 位域 标志 : 整数 { 读: 1, 写: 1 }。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert '_fields_' in py_code
    assert '标志' in py_code


# =============================================================================
# 测试9：代码生成 - 函数指针
# =============================================================================

def test_codegen_ffi_funcptr():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 函数指针 比较器 接收 甲: 整数, 乙: 整数 返回 整数。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert 'CFUNCTYPE' in py_code
    assert '比较器' in py_code


# =============================================================================
# 测试10：代码生成 - 调试
# =============================================================================

def test_codegen_ffi_debug():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 调试 { 开启, 记录调用 }。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert 'set_debug' in py_code
    assert 'enabled=True' in py_code


# =============================================================================
# 测试11：代码生成 - 预处理器
# =============================================================================

def test_codegen_ffi_preprocessor():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '外部 宏 缓冲区大小 为 1024。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    assert '定义宏' in py_code
    assert '1024' in py_code


# =============================================================================
# 测试12：运行时 - 回调生命周期
# =============================================================================

def test_runtime_callback_registry():
    from stdlib.FFI import 注册回调, 注销回调, 获取回调, 列出回调, 清理回调
    清理回调()
    key = 注册回调('测试回调', lambda x: x + 1)
    assert key.startswith('测试回调_')
    assert 获取回调(key) is not None
    assert 获取回调(key)(5) == 6
    assert len(列出回调()) == 1
    assert 注销回调(key) == True
    assert 注销回调(key) == False
    assert 获取回调(key) is None


# =============================================================================
# 测试13：运行时 - 调试系统
# =============================================================================

def test_runtime_debug_system():
    from stdlib.FFI import 启用调试, 禁用调试, 获取日志, 清空日志, 设置调试
    清空日志()
    启用调试()
    logs = 获取日志()
    assert any('调试已启用' in l for l in logs)
    禁用调试()
    logs = 获取日志()
    assert any('调试已禁用' in l for l in logs)
    清空日志()
    assert 获取日志() == []


# =============================================================================
# 测试14：运行时 - 位域操作
# =============================================================================

def test_runtime_bitfield():
    from stdlib.FFI import 位域设置, 位域获取
    class Flags(ctypes.Structure):
        _fields_ = [('读', ctypes.c_int, 1), ('写', ctypes.c_int, 1)]
    flags = Flags()
    位域设置(flags, '读', 0)
    位域设置(flags, '写', 1)
    assert 位域获取(flags, '读') == 0
    # 1-bit signed field: 1 = -1 in two's complement
    assert 位域获取(flags, '写') in (-1, 1)


# =============================================================================
# 测试15：运行时 - 预处理器宏
# =============================================================================

def test_runtime_macro():
    from stdlib.FFI import 定义宏, 获取宏, 列出宏, 清理宏
    清理宏()
    定义宏('缓冲区大小', '1024')
    定义宏('版本', '1.0.0')
    assert 获取宏('缓冲区大小') == '1024'
    assert 获取宏('版本') == '1.0.0'
    assert len(列出宏()) == 2
    assert 获取宏('不存在') is None
    清理宏()
    assert 获取宏('缓冲区大小') is None


# =============================================================================
# 测试16：运行时 - 函数指针
# =============================================================================

def test_runtime_funcptr():
    from stdlib.FFI import 创建函数指针
    cb_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)
    ptr_type = 创建函数指针(cb_type)
    assert ptr_type == cb_type


# =============================================================================
# 测试17：运行时 - 类型别名
# =============================================================================

def test_runtime_typedef():
    from stdlib.FFI import 创建类型别名
    result = 创建类型别名('尺寸', ctypes.c_int)
    assert result == ctypes.c_int


# =============================================================================
# 测试18：AST 节点兼容性
# =============================================================================

def test_new_ffi_ast_nodes_phase4():
    import ast_nodes as old_ast
    assert hasattr(old_ast, 'FFITypedefDef')
    assert hasattr(old_ast, 'FFIBitfieldDef')
    assert hasattr(old_ast, 'FFIFuncPtrDef')
    assert hasattr(old_ast, 'FFIDebugConfig')
    assert hasattr(old_ast, 'FFIPreprocessorDef')
    td = old_ast.FFITypedefDef(name='测试', base_type='整数')
    assert td.name == '测试'
    bf = old_ast.FFIBitfieldDef(name='测试', base_type='整数', fields=[{'name': 'a', 'bits': 1}])
    assert len(bf.fields) == 1
    fp = old_ast.FFIFuncPtrDef(name='测试', params=[{'name': 'a', 'type': '整数'}], return_type='整数')
    assert fp.name == '测试'
    dc = old_ast.FFIDebugConfig(enabled=True, log_calls=True)
    assert dc.enabled == True
    pp = old_ast.FFIPreprocessorDef(name='测试', value='1024')
    assert pp.value == '1024'


# =============================================================================
# 测试19：LLVM 后端兼容性
# =============================================================================

def test_llvm_phase4_ast():
    import ast_nodes as old_ast
    from llvm.codegen import LLVMCodeGen
    gen = LLVMCodeGen()
    stmt = old_ast.FFITypedefDef(name='尺寸', base_type='整数')
    gen._collect_statement(stmt)
    assert len(gen._module_statements) > 0


# =============================================================================
# 测试20：回调内存安全 - 注册多个回调
# =============================================================================

def test_runtime_callback_memory_safety():
    from stdlib.FFI import 注册回调, 获取回调, 列出回调, 清理回调
    清理回调()
    keys = []
    for i in range(10):
        key = 注册回调(f'回调{i}', lambda x, i=i: x + i)
        keys.append(key)
    assert len(列出回调()) == 10
    for key in keys:
        assert 获取回调(key) is not None
    清理回调()


# =============================================================================
# 测试21：调试日志记录
# =============================================================================

def test_runtime_debug_log():
    from stdlib.FFI import 设置调试, 获取日志, 清空日志, _debug_log_call
    清空日志()
    设置调试(enabled=True, log_calls=True)
    _debug_log_call('测试函数', (1, 'hello'), 42)
    logs = 获取日志()
    assert any('测试函数' in l for l in logs)
    assert any('42' in l for l in logs)
    清空日志()


# =============================================================================
# 测试22：解析位域后跟其他语句
# =============================================================================

def test_parse_bitfield_then_typedef():
    parser = LightParser()
    code = '外部 位域 标志 : 整数 { 读: 1 }。外部 类型别名 尺寸 为 整数。'
    module = parser.parse(code)
    assert len(module.statements) == 2
    assert isinstance(module.statements[0], FFIBitfieldDef)
    assert isinstance(module.statements[1], FFITypedefDef)


# =============================================================================
# 测试23：解析函数指针后跟枚举
# =============================================================================

def test_parse_funcptr_then_enum():
    from light_parser_v3 import FFIEnumDef
    parser = LightParser()
    code = '外部 函数指针 回调 接收 整数。外部 枚举 状态 { 开, 关 }。'
    module = parser.parse(code)
    assert len(module.statements) == 2
    assert isinstance(module.statements[0], FFIFuncPtrDef)
    assert isinstance(module.statements[1], FFIEnumDef)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])