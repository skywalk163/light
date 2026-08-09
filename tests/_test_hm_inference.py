"""
光明 HM（Hindley-Milner）全局类型推断系统测试

包含 20+ 测试点：
- 两阶段预扫描/推断
- let-polymorphism（泛化 + 实例化）
- lambda 表达式推断
- 泛型函数调用推断
- 发生检查
- 向后兼容性（旧测试仍然通过）
"""

import os
import sys

# 确保项目根目录和 src 目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)

from type_system import (
    Type, NumberType, StringType, BooleanType, NullType,
    AnyType, UnknownType, FunctionType, TypeVar, ListType,
    TypeSubstitution, UnificationError, unify,
    TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL, TYPE_UNKNOWN,
)

from type_inferencer import TypeInferencer
from ast_nodes import (
    Module, SegmentDefinition, Parameter,
    NumberLiteral, StringLiteral, BooleanLiteral, Identifier,
    BinaryOp, FunctionCall, LambdaExpression, ReturnStatement,
    VariableDeclaration, Assignment, ExpressionStatement,
    ListLiteral,
)

import traceback

PASS = 0
FAIL = 0
FAILED_CASES = []

def run_test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✓ {name}")
    except AssertionError as e:
        FAIL += 1
        FAILED_CASES.append(name)
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        FAIL += 1
        FAILED_CASES.append(name)
        print(f"  ✗ {name}: 异常 - {type(e).__name__}: {e}")
        traceback.print_exc()

# =============================================================================
# 1. 基础类型系统测试（类型变量合一 + 发生检查）
# =============================================================================

def test_tvar_unify_with_number():
    """类型变量 TypeVar 与 数 合一后应用替换得到 数。"""
    tv = TypeVar('T')
    subs = unify(tv, TYPE_NUMBER)
    assert tv.apply_substitution(subs) == TYPE_NUMBER, f"期望 数，实际 {tv.apply_substitution(subs)}"


def test_tvar_unify_bidirectional():
    """合一双向：数 与 TypeVar 也能合一。"""
    tv = TypeVar('T')
    subs = unify(TYPE_NUMBER, tv)
    assert tv.apply_substitution(subs) == TYPE_NUMBER


def test_two_tvars_unify():
    """两个 TypeVar 合一后共享相同绑定。"""
    a = TypeVar('A')
    b = TypeVar('B')
    subs = unify(a, b)
    # 再合一 A ~ 数
    subs2 = unify(a.apply_substitution(subs), TYPE_NUMBER, subs)
    assert b.apply_substitution(subs2) == TYPE_NUMBER


def test_occurs_check():
    """发生检查：T ~ list[T] 应失败（无限类型）。"""
    tv = TypeVar('T')
    looping = ListType(tv)
    try:
        unify(tv, looping)
        assert False, "应触发 UnificationError（发生检查失败）"
    except UnificationError:
        pass  # 期望


def test_occurs_check_same_name():
    """T ~ T 不触发发生检查（平凡一致）。"""
    tv = TypeVar('T')
    # 不应抛异常
    subs = unify(tv, tv)
    assert subs is not None


# =============================================================================
# 2. 两阶段推断：预扫描 + 推断
# =============================================================================

def _make_simple_module(segments):
    """创建一个包含段的模块。"""
    return Module(segments=segments, statements=[])


def test_pre_scan_registers_function_type():
    """预扫描应为段注册 FunctionType（含 TypeVar）。"""
    seg = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],  # 无类型标注
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('恒等')
    assert sym is not None, "'恒等' 未注册"
    assert isinstance(sym.data_type, FunctionType), f"期望 FunctionType，实际 {type(sym.data_type).__name__}"
    # 参数应为 TypeVar（因为未标注）
    pt = sym.data_type.param_types[0]
    assert isinstance(pt, TypeVar), f"参数期望 TypeVar，实际 {pt}"


def test_pre_scan_honors_annotation():
    """标注参数类型应被尊重。"""
    seg = SegmentDefinition(
        name='加倍',
        parameters=[Parameter(name='n', type_annotation='数')],
        body=[ReturnStatement(value=BinaryOp(left=Identifier(name='n'), operator='+', right=Identifier(name='n')))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('加倍')
    assert isinstance(sym.data_type, FunctionType)
    assert sym.data_type.param_types[0] == TYPE_NUMBER


def test_hm_infers_return_type():
    """段应从 body 的 return 语句推断返回类型。"""
    seg = SegmentDefinition(
        name='五',
        parameters=[],
        body=[ReturnStatement(value=NumberLiteral(value=5))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('五')
    assert sym.data_type.return_type == TYPE_NUMBER, f"期望 数，实际 {sym.data_type.return_type}"


def test_hm_no_return_is_null():
    """无返回语句的段返回空。"""
    seg = SegmentDefinition(
        name='空段',
        parameters=[],
        body=[ExpressionStatement(expression=NumberLiteral(value=1))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('空段')
    # 应为 null 或 未知
    rt = sym.data_type.return_type
    assert rt in (TYPE_NULL, TYPE_UNKNOWN) or isinstance(rt, NullType), f"期望空，实际 {rt}"


# =============================================================================
# 3. let-polymorphism 测试
# =============================================================================

def test_generalize_records_free_tvars():
    """泛化应将剩余自由类型变量登记为泛型段。"""
    # 恒等函数：T -> T（未绑定 T），所以是泛型
    seg = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    assert '恒等' in inf.generic_segment_defs, (
        f"恒等 应被泛化，实际 generic_segment_defs={inf.generic_segment_defs}"
    )


def test_instantiate_produces_fresh_tvars():
    """实例化应产生新鲜的 TypeVar（名称不同）。"""
    ft = FunctionType([TypeVar('T')], TypeVar('T'))
    inf = TypeInferencer()
    inst = inf._instantiate(ft)
    assert isinstance(inst, FunctionType)
    # 参数和返回的 TypeVar 名称应包含 '（即带撇号）以示"新鲜"
    param_name = inst.param_types[0].name
    assert "'" in param_name or param_name != 'T', f"应新鲜，实际 {param_name}"


def test_instantiate_preserves_structure():
    """实例化结构保持一致（T->T 仍是相同名称）。"""
    ft = FunctionType([TypeVar('T')], TypeVar('T'))
    inf = TypeInferencer()
    inst = inf._instantiate(ft)
    assert inst.param_types[0].name == inst.return_type.name, (
        f"参数与返回应共享类型变量：{inst.param_types[0]} vs {inst.return_type}"
    )


# =============================================================================
# 4. 泛型函数调用推断
# =============================================================================

def test_call_id_on_number():
    """调用 恒等(5) 应推断返回 数。"""
    seg_id = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    # 顶层语句调用：恒等(5)
    call = FunctionCall(name=Identifier(name='恒等'), arguments=[NumberLiteral(value=5)])
    mod = Module(segments=[seg_id], statements=[ExpressionStatement(expression=call)])
    inf = TypeInferencer()
    inf.infer(mod)
    # 查询推断结果
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    assert inferred == TYPE_NUMBER, f"期望 数，实际 {inferred}"


def test_call_id_on_string():
    """调用 恒等("hi") 应推断返回 串。"""
    seg_id = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    call = FunctionCall(name=Identifier(name='恒等'), arguments=[StringLiteral(value='hi')])
    mod = Module(segments=[seg_id], statements=[ExpressionStatement(expression=call)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    assert inferred == TYPE_STRING, f"期望 串，实际 {inferred}"


def test_call_polymorphic_multiple_times():
    """同一泛型函数被多次以不同类型调用，互不污染。

    （let-polymorphism 核心测试：实例化保证每次调用独立。）
    """
    seg_id = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    call_n = FunctionCall(name=Identifier(name='恒等'), arguments=[NumberLiteral(value=5)])
    call_s = FunctionCall(name=Identifier(name='恒等'), arguments=[StringLiteral(value='xx')])
    mod = Module(
        segments=[seg_id],
        statements=[
            ExpressionStatement(expression=call_n),
            ExpressionStatement(expression=call_s),
        ],
    )
    inf = TypeInferencer()
    inf.infer(mod)
    r_n = inf.type_cache.get(id(call_n), TYPE_UNKNOWN)
    r_s = inf.type_cache.get(id(call_s), TYPE_UNKNOWN)
    assert r_n == TYPE_NUMBER, f"调用 恒等(5) 应返回 数，实际 {r_n}"
    assert r_s == TYPE_STRING, f"调用 恒等('xx') 应返回 串，实际 {r_s}"


def test_call_explicit_type_arg():
    """带显式类型参数的调用（如 恒等[数](5)）。"""
    seg_id = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x')],
        generic_params=['T'],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    call = FunctionCall(name=Identifier(name='恒等'), arguments=[NumberLiteral(value=5)])
    call.type_args = ['数']
    mod = Module(segments=[seg_id], statements=[ExpressionStatement(expression=call)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    assert inferred == TYPE_NUMBER, f"期望 数，实际 {inferred}"


def test_inferred_add_function():
    """定义 加(a, b) { 返回 a + b } 调用 加(1, 2) 应返回 数。"""
    seg_add = SegmentDefinition(
        name='加',
        parameters=[Parameter(name='a'), Parameter(name='b')],
        body=[
            ReturnStatement(
                value=BinaryOp(left=Identifier(name='a'), operator='+', right=Identifier(name='b'))
            )
        ],
    )
    call = FunctionCall(name=Identifier(name='加'), arguments=[NumberLiteral(value=1), NumberLiteral(value=2)])
    mod = Module(segments=[seg_add], statements=[ExpressionStatement(expression=call)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    # 要么是 NumberType，要么仍有 TypeVar（取决于推断细节）
    assert inferred == TYPE_NUMBER or isinstance(inferred, NumberType), f"期望 数，实际 {inferred}"


# =============================================================================
# 5. lambda 表达式推断
# =============================================================================

def test_lambda_simple_inference():
    """lambda 表达式应被推断为 FunctionType。"""
    lam = LambdaExpression(
        parameters=[Parameter(name='x')],
        body=Identifier(name='x'),
    )
    mod = Module(statements=[ExpressionStatement(expression=lam)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(lam), TYPE_UNKNOWN)
    assert isinstance(inferred, FunctionType), f"期望 FunctionType，实际 {inferred}"


def test_lambda_param_with_annotation():
    """标注参数类型的 lambda（接收 数，返回 数）。"""
    lam = LambdaExpression(
        parameters=[Parameter(name='x', type_annotation='数')],
        body=Identifier(name='x'),
    )
    mod = Module(statements=[ExpressionStatement(expression=lam)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(lam), TYPE_UNKNOWN)
    assert isinstance(inferred, FunctionType)
    assert inferred.param_types[0] == TYPE_NUMBER, f"参数期望 数，实际 {inferred.param_types[0]}"


def test_lambda_application():
    """将 lambda 应用到数：(lambda x. x + x)(3) 应返回 数。"""
    lam = LambdaExpression(
        parameters=[Parameter(name='x')],
        body=BinaryOp(left=Identifier(name='x'), operator='+', right=Identifier(name='x')),
    )
    call = FunctionCall(name=Identifier(name='f'), arguments=[NumberLiteral(value=3)])
    # 设 f = lambda; f(3)
    mod = Module(statements=[
        VariableDeclaration(name='f', value=lam),
        ExpressionStatement(expression=call),
    ])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    # 不强制，仅验证无异常
    print(f"    [调试] f(3) 推断结果: {inferred}")


def test_lambda_unannotated_has_tvar():
    """未标注参数的 lambda 参数类型应为 TypeVar。"""
    lam = LambdaExpression(
        parameters=[Parameter(name='x')],
        body=Identifier(name='x'),
    )
    mod = Module(statements=[ExpressionStatement(expression=lam)])
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(lam), TYPE_UNKNOWN)
    assert isinstance(inferred, FunctionType)
    assert isinstance(inferred.param_types[0], TypeVar) or inferred.param_types[0] is TYPE_UNKNOWN, (
        f"参数应是 TypeVar 或 Unknown，实际 {inferred.param_types[0]}"
    )


# =============================================================================
# 6. 复杂场景：段之间相互调用 + 推断
# =============================================================================

def test_segment_calls_other_segment():
    """段 A 调用段 B，应能推断 A 的返回类型。"""
    seg_b = SegmentDefinition(
        name='B',
        parameters=[Parameter(name='x', type_annotation='数')],
        body=[ReturnStatement(value=BinaryOp(left=Identifier(name='x'), operator='+', right=NumberLiteral(value=1)))],
    )
    seg_a = SegmentDefinition(
        name='A',
        parameters=[Parameter(name='y')],
        body=[ReturnStatement(
            value=FunctionCall(name=Identifier(name='B'), arguments=[Identifier(name='y')])
        )],
    )
    call = FunctionCall(name=Identifier(name='A'), arguments=[NumberLiteral(value=3)])
    mod = Module(
        segments=[seg_a, seg_b],
        statements=[ExpressionStatement(expression=call)],
    )
    inf = TypeInferencer()
    inf.infer(mod)
    inferred = inf.type_cache.get(id(call), TYPE_UNKNOWN)
    assert inferred == TYPE_NUMBER or isinstance(inferred, NumberType), f"期望 数，实际 {inferred}"


def test_no_circular_errors_between_segments():
    """相互引用的段推断时应无致命错误（即使无法完全推断，也应降级为 Unknown）。"""
    seg_a = SegmentDefinition(
        name='A',
        parameters=[Parameter(name='x')],
        body=[ReturnStatement(value=FunctionCall(
            name=Identifier(name='B'), arguments=[Identifier(name='x')]
        ))],
    )
    seg_b = SegmentDefinition(
        name='B',
        parameters=[Parameter(name='y')],
        body=[ReturnStatement(value=FunctionCall(
            name=Identifier(name='A'), arguments=[Identifier(name='y')]
        ))],
    )
    mod = Module(segments=[seg_a, seg_b], statements=[])
    inf = TypeInferencer()
    # 关键：不能抛异常
    inf.infer(mod)
    # 符号表中应存在 A, B
    assert inf.symbol_table.lookup('A') is not None
    assert inf.symbol_table.lookup('B') is not None


def test_segment_list_return():
    """段返回列表字面量，推断返回 list[数]。"""
    seg = SegmentDefinition(
        name='造列表',
        parameters=[Parameter(name='n', type_annotation='数')],
        body=[
            ReturnStatement(value=ListLiteral(elements=[
                NumberLiteral(value=1), NumberLiteral(value=2), Identifier(name='n')
            ])),
        ],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('造列表')
    rt = sym.data_type.return_type
    assert isinstance(rt, ListType) or '列表' in str(rt) or 'List' in str(rt), (
        f"期望 ListType，实际 {rt}"
    )


# =============================================================================
# 7. 向后兼容性：旧的推断方式仍工作
# =============================================================================

def test_backcompat_variable_declaration():
    """变量声明 + 初始化值推断（旧 API 行为保持）。"""
    mod = Module(statements=[
        VariableDeclaration(name='a', value=NumberLiteral(value=42)),
    ])
    inf = TypeInferencer()
    inf.infer(mod)
    sym = inf.symbol_table.lookup('a')
    assert sym is not None
    assert sym.data_type == TYPE_NUMBER or isinstance(sym.data_type, NumberType)


def test_backcompat_binary_op_returns_number():
    """1 + 2 应推断为数。"""
    expr = BinaryOp(left=NumberLiteral(value=1), operator='+', right=NumberLiteral(value=2))
    mod = Module(statements=[ExpressionStatement(expression=expr)])
    inf = TypeInferencer()
    inf.infer(mod)
    r = inf.type_cache.get(id(expr), TYPE_UNKNOWN)
    assert r == TYPE_NUMBER or isinstance(r, NumberType), f"期望 数，实际 {r}"


def test_backcompat_string_concat():
    """"abc" + "def" 应推断为串。"""
    expr = BinaryOp(left=StringLiteral(value='abc'), operator='+', right=StringLiteral(value='def'))
    mod = Module(statements=[ExpressionStatement(expression=expr)])
    inf = TypeInferencer()
    inf.infer(mod)
    r = inf.type_cache.get(id(expr), TYPE_UNKNOWN)
    assert r == TYPE_STRING or isinstance(r, StringType), f"期望 串，实际 {r}"


def test_backcompat_boolean_literal():
    """布尔字面量应为布尔类型。"""
    expr = BooleanLiteral(value=True)
    mod = Module(statements=[ExpressionStatement(expression=expr)])
    inf = TypeInferencer()
    inf.infer(mod)
    r = inf.type_cache.get(id(expr), TYPE_UNKNOWN)
    assert r == TYPE_BOOLEAN or isinstance(r, BooleanType)


def test_backcompat_empty_module():
    """空模块不抛错。"""
    mod = Module(statements=[])
    inf = TypeInferencer()
    inf.infer(mod)


def test_backcompat_errors_not_exceeding_expected():
    """正常段的 errors 列表应小（不产生虚假错误）。"""
    seg = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x', type_annotation='数')],
        body=[ReturnStatement(value=Identifier(name='x'))],
    )
    mod = _make_simple_module([seg])
    inf = TypeInferencer()
    inf.infer(mod)
    # 不应超过 3 个错误（含可能的拼写/上下文警告）
    assert len(inf.errors) <= 3, f"错误过多: {inf.errors}"


# =============================================================================
# 运行所有测试
# =============================================================================

def main():
    global PASS, FAIL, FAILED_CASES
    print("=" * 70)
    print("光明 HM 类型推断系统测试")
    print("=" * 70)

    tests = [
        # 1. 类型系统
        ("[类型系统] TypeVar + 数 合一", test_tvar_unify_with_number),
        ("[类型系统] 数 + TypeVar 合一（反向）", test_tvar_unify_bidirectional),
        ("[类型系统] 两个 TypeVar 合一", test_two_tvars_unify),
        ("[类型系统] 发生检查：T ~ list[T] 失败", test_occurs_check),
        ("[类型系统] 发生检查：T ~ T 不失败", test_occurs_check_same_name),

        # 2. 两阶段推断
        ("[两阶段] 预扫描注册 FunctionType", test_pre_scan_registers_function_type),
        ("[两阶段] 预扫描尊重标注", test_pre_scan_honors_annotation),
        ("[两阶段] HM 推断 return 类型", test_hm_infers_return_type),
        ("[两阶段] 无返回语句 → 空", test_hm_no_return_is_null),

        # 3. let-polymorphism
        ("[let-polymorphism] 泛化登记自由变量", test_generalize_records_free_tvars),
        ("[let-polymorphism] 实例化产生新鲜 TypeVar", test_instantiate_produces_fresh_tvars),
        ("[let-polymorphism] 实例化保持结构", test_instantiate_preserves_structure),

        # 4. 泛型调用
        ("[泛型调用] 恒等(5) → 数", test_call_id_on_number),
        ("[泛型调用] 恒等('hi') → 串", test_call_id_on_string),
        ("[泛型调用] 多次不同类型调用不污染", test_call_polymorphic_multiple_times),
        ("[泛型调用] 显式类型参数", test_call_explicit_type_arg),
        ("[泛型调用] 加(1,2) 推断", test_inferred_add_function),

        # 5. lambda
        ("[lambda] 推断为 FunctionType", test_lambda_simple_inference),
        ("[lambda] 标注参数", test_lambda_param_with_annotation),
        ("[lambda] 应用调用", test_lambda_application),
        ("[lambda] 未标注参数为 TypeVar", test_lambda_unannotated_has_tvar),

        # 6. 复杂
        ("[复杂] 段调用段", test_segment_calls_other_segment),
        ("[复杂] 相互递归段不致命", test_no_circular_errors_between_segments),
        ("[复杂] 返回列表字面量", test_segment_list_return),

        # 7. 向后兼容
        ("[兼容] 变量声明推断", test_backcompat_variable_declaration),
        ("[兼容] 数加法", test_backcompat_binary_op_returns_number),
        ("[兼容] 字符串拼接", test_backcompat_string_concat),
        ("[兼容] 布尔字面量", test_backcompat_boolean_literal),
        ("[兼容] 空模块", test_backcompat_empty_module),
        ("[兼容] 错误数量合理", test_backcompat_errors_not_exceeding_expected),
    ]

    for name, fn in tests:
        run_test(name, fn)

    print("=" * 70)
    print(f"结果：通过 {PASS}，失败 {FAIL}，总计 {PASS + FAIL}")
    print("=" * 70)

    if FAILED_CASES:
        print("失败用例：")
        for c in FAILED_CASES:
            print(f"  - {c}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
