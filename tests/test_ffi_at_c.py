"""
@C 语法标记测试：光明 C FFI 的独立语法标记方案

@C 作为独立语法标记，与 外部 关键字并行，提供更简洁的FFI声明方式。
语法：
  @C 段落 函数名 接收 参数... 返回 类型 在 库别名。
  @C 结构体 名称 { 字段: 类型, ... }。
  @C 枚举 名称 { 成员 = 值, ... }。
  @C 加载库 "libxxx" 为 别名。
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from light_parser_v3 import (
    FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef,
    FFIEnumDef, FFIUnionDef, FFIVarArgsDecl,
    FFITypedefDef, FFIBitfieldDef, FFIFuncPtrDef,
    FFIDebugConfig, FFIPreprocessorDef
)


# =============================================================================
# 测试1：@C 加载库
# =============================================================================

def test_at_c_load_library():
    parser = LightParser()
    code = '@C 加载库 "libm.so" 为 数学库。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFILoadLibrary)]
    assert len(stmts) == 1
    assert stmts[0].library_path == 'libm.so'
    assert stmts[0].alias == '数学库'


# =============================================================================
# 测试2：@C 段落（函数声明）
# =============================================================================

def test_at_c_function_decl():
    parser = LightParser()
    code = '@C 段落 正弦 接收 甲: 小数 返回 小数 在 数学库。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIFunctionDecl)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '正弦'
    assert stmt.return_type == '小数'
    assert stmt.library_alias == '数学库'
    assert stmt.params[0]['name'] == '甲'
    assert stmt.params[0]['type'] == '小数'


def test_at_c_function_with_c_name():
    parser = LightParser()
    code = '@C 段落 平方根 为 "sqrt" 接收 甲: 小数 返回 小数 在 数学库。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIFunctionDecl)]
    stmt = stmts[0]
    assert stmt.name == '平方根'
    assert stmt.c_name == 'sqrt'


# =============================================================================
# 测试3：@C 结构体
# =============================================================================

def test_at_c_struct_def():
    parser = LightParser()
    code = '@C 结构体 点 { 甲: 整数, 乙: 整数 }。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIStructDef)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '点'
    assert len(stmt.fields) == 2
    assert stmt.fields[0]['name'] == '甲'
    assert stmt.fields[0]['type'] == '整数'


# =============================================================================
# 测试4：@C 回调
# =============================================================================

def test_at_c_callback_def():
    parser = LightParser()
    code = '@C 回调 比较器 接收 甲: 整数, 乙: 整数 返回 整数。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFICallbackDef)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '比较器'
    assert stmt.return_type == '整数'
    assert len(stmt.params) == 2


# =============================================================================
# 测试5：@C 枚举
# =============================================================================

def test_at_c_enum_def():
    parser = LightParser()
    code = '@C 枚举 颜色 { 红 = 0, 绿 = 1, 蓝 = 2 }。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIEnumDef)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '颜色'
    assert stmt.values == {'红': 0, '绿': 1, '蓝': 2}


def test_at_c_enum_auto_values():
    parser = LightParser()
    code = '@C 枚举 状态 { 激活, 停用 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIEnumDef)
    assert stmt.values == {'激活': 0, '停用': 1}


# =============================================================================
# 测试6：@C 联合体
# =============================================================================

def test_at_c_union_def():
    parser = LightParser()
    code = '@C 联合体 数据 { 整数: 整数, 小数: 小数 }。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIUnionDef)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '数据'
    assert len(stmt.fields) == 2


# =============================================================================
# 测试7：@C 变长参数
# =============================================================================

def test_at_c_varargs_decl():
    parser = LightParser()
    code = '@C 变长参数 段落 打印 为 "printf" 接收 格式: 文本 返回 整数 在 libc。'
    module = parser.parse(code)
    stmts = [s for s in module.statements if isinstance(s, FFIVarArgsDecl)]
    assert len(stmts) == 1
    stmt = stmts[0]
    assert stmt.name == '打印'
    assert stmt.c_name == 'printf'
    assert stmt.library_alias == 'libc'


# =============================================================================
# 测试8：@C 类型别名
# =============================================================================

def test_at_c_typedef():
    parser = LightParser()
    code = '@C 类型别名 尺寸 为 整数。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFITypedefDef)
    assert stmt.name == '尺寸'
    assert stmt.base_type == '整数'


# =============================================================================
# 测试9：@C 位域
# =============================================================================

def test_at_c_bitfield():
    parser = LightParser()
    code = '@C 位域 标志 : 整数 { 读: 1, 写: 1, 执行: 1 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIBitfieldDef)
    assert stmt.name == '标志'
    assert len(stmt.fields) == 3


# =============================================================================
# 测试10：@C 函数指针
# =============================================================================

def test_at_c_funcptr():
    parser = LightParser()
    code = '@C 函数指针 比较器 接收 甲: 整数, 乙: 整数 返回 整数。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIFuncPtrDef)
    assert stmt.name == '比较器'
    assert stmt.return_type == '整数'


# =============================================================================
# 测试11：@C 调试配置
# =============================================================================

def test_at_c_debug():
    parser = LightParser()
    code = '@C 调试 { 开启, 记录调用, 记录类型 }。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIDebugConfig)
    assert stmt.enabled == True
    assert stmt.log_calls == True
    assert stmt.log_types == True


# =============================================================================
# 测试12：@C 预处理器宏
# =============================================================================

def test_at_c_preprocessor():
    parser = LightParser()
    code = '@C 宏 缓冲区大小 为 1024。'
    module = parser.parse(code)
    stmt = module.statements[0]
    assert isinstance(stmt, FFIPreprocessorDef)
    assert stmt.name == '缓冲区大小'
    assert stmt.value == '1024'


# =============================================================================
# 测试13：@C 与 外部 混合使用
# =============================================================================

def test_at_c_mixed_with_external():
    parser = LightParser()
    code = (
        '外部 枚举 颜色 { 红 = 0, 绿 = 1 }。\n'
        '@C 结构体 点 { x: 小数, y: 小数 }。\n'
        '@C 段落 正弦 接收 甲: 小数 返回 小数 在 数学库。\n'
        '外部 段落 余弦 接收 甲: 小数 返回 小数 在 数学库。'
    )
    module = parser.parse(code)
    assert len(module.statements) == 4
    assert isinstance(module.statements[0], FFIEnumDef)
    assert isinstance(module.statements[1], FFIStructDef)
    assert isinstance(module.statements[2], FFIFunctionDecl)
    assert isinstance(module.statements[3], FFIFunctionDecl)


# =============================================================================
# 测试14：@C 不干扰 @抽象 装饰器
# =============================================================================

def test_at_c_does_not_break_decorator():
    """验证 @C 不干扰 @抽象 装饰器"""
    parser = LightParser()
    code = (
        '类 测试类：\n'
        '    @抽象 标注 段落 计算 接收 甲：整数 返回 整数：\n'
        '        返回 甲。\n'
    )
    module = parser.parse(code)
    assert len(module.statements) == 1


# =============================================================================
# 测试15：@C 完整程序
# =============================================================================

def test_at_c_full_program():
    parser = LightParser()
    code = (
        '@C 加载库 "libm.so" 为 数学库。\n'
        '@C 枚举 颜色 { 红 = 0, 绿 = 1, 蓝 = 2 }。\n'
        '@C 结构体 点 { x: 小数, y: 小数 }。\n'
        '@C 段落 正弦 接收 甲: 小数 返回 小数 在 数学库。\n'
        '@C 段落 绝对值 为 "fabs" 接收 甲: 小数 返回 小数 在 数学库。'
    )
    module = parser.parse(code)
    assert len(module.statements) == 5
    assert isinstance(module.statements[0], FFILoadLibrary)
    assert isinstance(module.statements[1], FFIEnumDef)
    assert isinstance(module.statements[2], FFIStructDef)
    assert isinstance(module.statements[3], FFIFunctionDecl)
    assert isinstance(module.statements[4], FFIFunctionDecl)


# =============================================================================
# 测试16：代码生成 - @C 语法
# =============================================================================

def test_codegen_at_c_struct():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '@C 结构体 点 { 甲: 整数, 乙: 整数 }。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'class 点(ctypes.Structure)' in result
    assert '_fields_' in result


def test_codegen_at_c_function():
    from code_generator import PythonCodeGenerator
    parser = LightParser()
    code = '@C 段落 正弦 接收 甲: 小数 返回 小数 在 数学库。'
    module = parser.parse(code)
    gen = PythonCodeGenerator()
    result = gen.generate(module)
    assert 'ctypes.c_double' in result
    assert 'def 正弦(' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])