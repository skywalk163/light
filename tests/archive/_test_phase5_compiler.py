"""Phase 5 测试：完整语言解析器（源码 → tokens → AST → 类型检查）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from compiler import DuanCompiler, compile_source, parse_source, tokenize_source

TESTS = []
PASS = []
FAIL = []

def register(name, fn):
    TESTS.append((name, fn))

def run(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✓ {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        import traceback
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ✗ {name}: {type(e).__name__}: {e}")
        traceback.print_exc()


# 便捷：编译 + 断言
def compile_and_check(src, var_name=None, expected_type_str=None, expect_errors=False):
    c = DuanCompiler()
    c.compile(src)
    if not expect_errors:
        assert len(c.errors) == 0, f"期望无错误，但得到: {c.errors}"
    if var_name is not None:
        sym = c._inferencer.symbol_table.lookup(var_name)
        assert sym is not None, f"变量 '{var_name}' 未定义"
        if expected_type_str:
            assert str(sym.data_type) == expected_type_str or expected_type_str in str(sym.data_type), \
                f"期望 {expected_type_str}, 实际 {sym.data_type}"
    return c


# =============================================================================
# 1. 词法分析（tokens）
# =============================================================================

def test_tokenize_number():
    tokens = tokenize_source('三')
    assert len(tokens) > 0
    print(f"   [{len(tokens)} tokens]")

def test_tokenize_complex():
    tokens = tokenize_source('设甲为一加五。')
    assert len(tokens) > 0
    print(f"   [{len(tokens)} tokens]")

register('词法-数字', test_tokenize_number)
register('词法-复杂语句', test_tokenize_complex)


# =============================================================================
# 2. 变量声明和字面量
# =============================================================================

def test_var_number():
    c = compile_and_check('设甲为三。', '甲', '数')
    assert '数' in str(c._inferencer.symbol_table.lookup('甲').data_type)
register('变量-数字字面量', test_var_number)


def test_var_arithmetic():
    c = compile_and_check('设和为一加五。', '和', '数')
register('变量-加法运算', test_var_arithmetic)


def test_var_list():
    c = compile_and_check('设列表为[一, 二, 三]。', '列表', '列表')
    assert '列表' in str(c._inferencer.symbol_table.lookup('列表').data_type)
register('变量-列表字面量', test_var_list)


def test_var_multiple_declarations():
    c = DuanCompiler()
    c.compile('设甲为三。设乙为五加一。设丙为甲加乙。')
    assert len(c.errors) == 0, f"错误: {c.errors}"
    sym = c._inferencer.symbol_table.lookup('丙')
    assert sym is not None
register('变量-多个声明', test_var_multiple_declarations)


# =============================================================================
# 3. 段落定义和调用
# =============================================================================

def test_paragraph_call():
    c = DuanCompiler()
    c.compile('打印(三)。')
    assert len(c.errors) == 0
register('段落-调用', test_paragraph_call)


def test_paragraph_def_and_call():
    c = DuanCompiler()
    c.compile('段落 倍(值)  设结果为值乘二。 返回结果。 结束。')
    # 检查段落被注册
    sym = c._inferencer.symbol_table.lookup('倍')
    assert sym is not None, "'倍' 段落应已注册"
register('段落-定义', test_paragraph_def_and_call)


# =============================================================================
# 4. 条件和循环
# =============================================================================

def test_if_stmt():
    c = DuanCompiler()
    c.compile('如果甲大于零那么: 打印(甲)。 结束。')
    assert len(c.errors) == 0
register('语句-条件', test_if_stmt)


def test_foreach_stmt():
    c = DuanCompiler()
    c.compile('遍历项在列表: 打印(项)。 结束。')
    assert len(c.errors) == 0
register('语句-遍历', test_foreach_stmt)


def test_while_stmt():
    c = DuanCompiler()
    c.compile('当甲大于零: 打印(甲)。 结束。')
    assert len(c.errors) == 0
register('语句-当循环', test_while_stmt)


# =============================================================================
# 5. 端到端完整流程
# =============================================================================

def test_end_to_end_compile():
    """完整端到端：源码 → tokens → AST → 类型检查"""
    c = DuanCompiler()
    result = c.compile('设甲为三。设乙为甲加一。')

    # 验证每个阶段都产生输出
    assert result['tokens'] is not None and len(result['tokens']) > 0, "应该有 tokens"
    assert result['ast'] is not None, "应该有 AST"
    assert result['ast_raw'] is not None, "应该有原始 AST"
    assert result['inferencer'] is not None, "应该有类型推断器"

    # 验证类型
    sym = c._inferencer.symbol_table.lookup('甲')
    assert sym is not None
    assert '数' in str(sym.data_type)
    sym2 = c._inferencer.symbol_table.lookup('乙')
    assert sym2 is not None
    assert '数' in str(sym2.data_type)
register('完整-端到端编译', test_end_to_end_compile)


def test_parse_only():
    """parse_source 便捷函数"""
    module = parse_source('设甲为三。')
    assert module is not None
    assert len(module.statements) > 0
register('便捷-只解析', test_parse_only)


def test_compile_source_function():
    """compile_source 便捷函数"""
    c = compile_source('设甲为三。')
    assert not c.has_errors
register('便捷-compile_source', test_compile_source_function)


# =============================================================================
# 主入口
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 Phase 5 —— 完整语言解析器测试")
    print("  源码 → 词法 → 语法 → AST适配 → 类型检查")
    print("=" * 60)
    print()
    for name, fn in TESTS:
        run(name, fn)
    print()
    print("=" * 60)
    print(f"总测试数: {len(TESTS)}   通过: {len(PASS)}   失败: {len(FAIL)}")
    print("=" * 60)
    if FAIL:
        print("\n失败详情:")
        for n, e in FAIL:
            print(f"  - {n}: {e}")
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过!")
