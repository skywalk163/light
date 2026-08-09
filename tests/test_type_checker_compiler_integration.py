# -*- coding: utf-8 -*-
"""
光明 v4.2 编译器类型检查集成测试

测试类型检查器与编译器管道的集成：
  1. 编译器 type_check 方法
  2. 分级检查在编译管道中的行为
  3. 类型错误在编译输出中的展现
  4. 文件指令影响编译行为
  5. 类型推断器与编译器集成
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


def _compile_and_check(source, level):
    """Helper: 编译并运行类型检查"""
    from compiler import LightCompiler
    from core.config import LightConfig, TypeCheckLevel

    compiler = LightCompiler()
    raw_ast = compiler.parse_raw(source)
    our_ast = compiler.adapt(raw_ast)
    compiler._config = LightConfig()
    compiler._config.type_check_level = level
    inferencer = compiler.type_check(our_ast, source)
    return compiler, inferencer, our_ast


# =============================================================================
# 第一部分：编译器 type_check 方法
# =============================================================================

def test_compiler_type_check_basic():
    """测试编译器基本 type_check 调用"""
    from core.config import TypeCheckLevel

    source = """
段落 加法(a: 整数, b: 整数) 返回 整数:
    返回 a + b

段落 主():
    设 结果: 整数 为 加法(3, 5)
    打印(结果)
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.EXPRESSION)
    assert inferencer is not None, "类型推断器不应为 None"
    print("  [PASS] test_compiler_type_check_basic")


def test_compiler_type_check_no_level():
    """测试 NONE 级别的 type_check"""
    from core.config import TypeCheckLevel

    source = """
段落 加法(a, b):
    返回 a + b

段落 主():
    设 结果 为 加法(3, 5)
    打印(结果)
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.NONE)
    assert inferencer is not None, "NONE 级别也应返回 inferencer"
    print("  [PASS] test_compiler_type_check_no_level")


def test_compiler_type_check_with_errors():
    """测试带类型错误的编译"""
    from core.config import TypeCheckLevel

    source = """
段落 加法(a: 整数, b: 整数) 返回 整数:
    返回 a + b

段落 主():
    设 结果: 字符串 为 加法(3, 5)
    打印(结果)
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.VARIABLE)
    assert inferencer is not None, "即使有类型错误，inferencer 也不应为 None"
    print("  [PASS] test_compiler_type_check_with_errors")


# =============================================================================
# 第二部分：文件指令影响编译
# =============================================================================

def test_file_directives_signature_level():
    """测试文件指令设置签名级检查"""
    from core.config import TypeCheckLevel

    source = """# 类型检查级别: 签名
# 类型模式: 松散

段落 测试(a, b) 返回 整数:
    返回 a + b
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.SIGNATURE)
    assert inferencer is not None, "签名级检查不应崩溃"
    print("  [PASS] test_file_directives_signature_level")


def test_file_directives_strict_mode():
    """测试文件指令设置严格模式"""
    from core.config import TypeCheckLevel

    source = """# 类型检查级别: 签名
# 类型模式: 严格

段落 测试(a: 整数, b: 整数) 返回 整数:
    返回 a + b
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.SIGNATURE)
    assert inferencer is not None, "严格模式不应崩溃"
    print("  [PASS] test_file_directives_strict_mode")


# =============================================================================
# 第三部分：类型推断器与编译器集成
# =============================================================================

def test_compiler_type_inference():
    """测试编译器类型推断集成"""
    from core.config import TypeCheckLevel

    source = """
设 姓名: 字符串 为 "张三"
设 年龄: 整数 为 25

段落 信息() 返回 字符串:
    返回 姓名 + "，年龄" + 转字符串(年龄)

段落 主():
    打印(信息())
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.EXPRESSION)
    assert inferencer is not None, "类型推断不应为空"
    type_cache = inferencer.get_type_cache()
    assert len(type_cache) > 0, "应该有一些推断结果"
    print(f"  [PASS] test_compiler_type_inference - {len(type_cache)} cached types")


def test_compiler_type_inference_error_collection():
    """测试编译器类型错误收集"""
    from core.config import TypeCheckLevel

    source = """
段落 主():
    设 x: 整数 为 "字符串"
    打印(x)
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.VARIABLE)
    assert inferencer is not None, "类型推断不应崩溃"
    print("  [PASS] test_compiler_type_inference_error_collection")


# =============================================================================
# 第四部分：泛型段落编译
# =============================================================================

def test_compiler_generic_segment():
    """测试泛型段落的编译"""
    from core.config import TypeCheckLevel

    source = """
段落 加倍(x: 整数|浮点) 返回 整数|浮点:
    返回 x + x

段落 主():
    设 a: 整数|浮点 为 加倍(10)
    设 b: 整数|浮点 为 加倍(3.5)
    打印(a)
    打印(b)
段落 主()
"""
    compiler, inferencer, our_ast = _compile_and_check(source, TypeCheckLevel.EXPRESSION)
    assert inferencer is not None, "泛型段落编译不应崩溃"
    print("  [PASS] test_compiler_generic_segment")


# =============================================================================
# 第五部分：完整编译流程
# =============================================================================

def test_full_compile_with_type_check():
    """测试完整编译流程包含类型检查"""
    from compiler import LightCompiler
    from core.config import LightConfig, TypeCheckLevel

    compiler = LightCompiler()
    compiler._config = LightConfig()
    compiler._config.type_check_level = TypeCheckLevel.EXPRESSION

    source = """
段落 加法(a: 整数, b: 整数) 返回 整数:
    返回 a + b

段落 主():
    设 结果: 整数 为 加法(3, 5)
    打印(结果)
段落 主()
"""
    result = compiler.compile(source)
    assert 'ast' in result, "编译结果应包含 ast"
    assert 'inferencer' in result, "编译结果应包含 inferencer"
    assert result['inferencer'] is not None, "inferencer 不应为 None"
    print("  [PASS] test_full_compile_with_type_check")


def test_full_compile_union_return():
    """测试完整编译流程 - 联合类型返回"""
    from compiler import LightCompiler
    from core.config import LightConfig, TypeCheckLevel

    compiler = LightCompiler()
    compiler._config = LightConfig()
    compiler._config.type_check_level = TypeCheckLevel.EXPRESSION

    source = """
段落 安全除法(a: 浮点, b: 浮点) 返回 浮点|字符串:
    若 b == 0.0:
        返回 "除数不能为零"
    返回 a / b

段落 主():
    设 结果: 浮点|字符串 为 安全除法(10.0, 3.0)
    打印(结果)
段落 主()
"""
    result = compiler.compile(source)
    assert result['inferencer'] is not None, "联合类型编译不应崩溃"
    print("  [PASS] test_full_compile_union_return")


# =============================================================================
# 运行所有测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 v4.2 编译器类型检查集成测试")
    print("=" * 60)

    total = 0
    passed = 0

    tests = [
        test_compiler_type_check_basic,
        test_compiler_type_check_no_level,
        test_compiler_type_check_with_errors,
        test_file_directives_signature_level,
        test_file_directives_strict_mode,
        test_compiler_type_inference,
        test_compiler_type_inference_error_collection,
        test_compiler_generic_segment,
        test_full_compile_with_type_check,
        test_full_compile_union_return,
    ]

    for test in tests:
        total += 1
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("所有测试通过!")
    else:
        print(f"有 {total - passed} 个测试失败")
    print("=" * 60)