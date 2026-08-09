"""Phase 3 测试：接口定义类型检查 + 类实现接口验证 + 接口作为泛型约束"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ast_nodes import (
    Module, SegmentDefinition, Parameter, ClassDefinition, MethodDefinition,
    ConstructorDefinition, NumberLiteral, StringLiteral, BooleanLiteral,
    Identifier, FunctionCall, NewExpression, VariableDeclaration,
    ReturnStatement, ExpressionStatement, BinaryOp, SegmentName,
    InterfaceDefinition, InterfaceMethod, TraitDefinition,
    TraitMethodSignature, TraitImplementation,
)
from type_inferencer import TypeInferencer
from type_system import (
    NumberType, StringType, BooleanType, ListType, DictType, FunctionType,
    ClassType, InterfaceType, TypeVar, AnyType, UnknownType, unify,
    TypeSubstitution, UnificationError, TYPE_NUMBER, TYPE_STRING,
    TYPE_BOOLEAN, TYPE_NULL, TYPE_UNKNOWN, TYPE_ANY,
)

# 帮助函数
def make_num(val: float): return NumberLiteral(value=val)
def make_str(val: str): return StringLiteral(value=val)
def make_id(name: str): return Identifier(name=name)

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

# =====================================================================
# 1. 接口定义类型检查
# =====================================================================

def test_interface_definition_registration():
    """接口定义 '可比较' 被正确注册到 trait_defs"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='任意'),
            ], return_type='数'),
        ],
    )
    module = Module(trait_defs=[iface], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert '可比较' in inf.trait_defs, "可比较 应注册到 trait_defs"
    assert isinstance(inf.trait_defs['可比较'], InterfaceType)
    assert '比大小' in inf.trait_defs['可比较'].methods
    assert inf.trait_defs['可比较'].interface_name == '可比较'

register('接口定义-注册到 trait_defs', test_interface_definition_registration)


def test_interface_definition_duplicate_methods():
    """接口定义中重复方法名应触发错误"""
    iface = TraitDefinition(
        name='有重复',
        methods=[
            TraitMethodSignature(name='方法1', parameters=[], return_type='数'),
            TraitMethodSignature(name='方法1', parameters=[], return_type='串'),  # 同名方法
        ],
    )
    module = Module(trait_defs=[iface], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    has_dup_error = any('重复' in err and '方法1' in err for err in inf.errors)
    assert has_dup_error, f"应检测到重复方法错误，但未找到。错误列表：{inf.errors}"

register('接口定义-重复方法检测', test_interface_definition_duplicate_methods)


def test_interface_definition_method_signature_preserved():
    """接口方法签名中的参数和返回类型被正确保存"""
    iface = TraitDefinition(
        name='可迭代',
        methods=[
            TraitMethodSignature(name='下一个', parameters=[
                Parameter(name='默认', type_annotation='串'),
            ], return_type='串'),
        ],
    )
    module = Module(trait_defs=[iface], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    ft = inf.trait_defs['可迭代'].methods['下一个']
    assert len(ft.param_types) == 1
    assert isinstance(ft.param_types[0], StringType), f"参数应为串，得 {ft.param_types[0]}"
    assert isinstance(ft.return_type, StringType), f"返回应为串，得 {ft.return_type}"

register('接口定义-方法签名保存', test_interface_definition_method_signature_preserved)


# =====================================================================
# 2. 类实现接口验证
# =====================================================================

def test_class_implements_interface_success():
    """类完整实现接口所有方法 → 无错误"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='任意'),
            ], return_type='数'),
        ],
    )
    cls = ClassDefinition(
        name='整数',
        interfaces=['可比较'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[MethodDefinition(
            name='比大小',
            parameters=[Parameter(name='其他', type_annotation='任意')],
            body=[ReturnStatement(value=NumberLiteral(value=0))],
            return_type='数',
        )],
        constructor=ConstructorDefinition(name='整数', parameters=[], body=[]),
    )
    module = Module(trait_defs=[iface], classes=[cls], trait_impls=[], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert len(inf.errors) == 0, f"完整实现不应有错误，得 {inf.errors}"
    # 验证 ClassType 记录接口实现
    sym = inf.symbol_table.lookup('整数')
    assert sym is not None
    ct = sym.data_type
    assert isinstance(ct, ClassType)
    assert len(ct.implements_interfaces) == 1
    assert ct.implements_interfaces[0].interface_name == '可比较'

register('类实现接口-完整实现', test_class_implements_interface_success)


def test_class_implements_interface_missing_method():
    """类未实现接口的所有方法 → 应有错误"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='任意'),
            ], return_type='数'),
        ],
    )
    cls = ClassDefinition(
        name='整数',
        interfaces=['可比较'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[],  # 缺少 '比大小' 方法
        constructor=ConstructorDefinition(name='整数', parameters=[], body=[]),
    )
    module = Module(trait_defs=[iface], classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    has_missing_error = any('未实现' in err and '比大小' in err for err in inf.errors)
    assert has_missing_error, f"应检测到缺少方法错误，得 {inf.errors}"

register('类实现接口-缺少方法', test_class_implements_interface_missing_method)


def test_class_implements_interface_wrong_param_count():
    """类方法参数数量与接口签名不匹配 → 应有错误"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='任意'),
            ], return_type='数'),
        ],
    )
    cls = ClassDefinition(
        name='整数',
        interfaces=['可比较'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[MethodDefinition(
            name='比大小',
            parameters=[],  # 应为 1 个参数，实际 0 个
            body=[],
            return_type='数',
        )],
        constructor=ConstructorDefinition(name='整数', parameters=[], body=[]),
    )
    module = Module(trait_defs=[iface], classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    has_param_error = any('参数数量不匹配' in err for err in inf.errors)
    assert has_param_error, f"应检测到参数数量错误，得 {inf.errors}"

register('类实现接口-参数数量不匹配', test_class_implements_interface_wrong_param_count)


def test_class_implements_interface_wrong_return_type():
    """类方法返回类型与接口签名不匹配 → 应有错误"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='任意'),
            ], return_type='数'),
        ],
    )
    cls = ClassDefinition(
        name='整数',
        interfaces=['可比较'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[MethodDefinition(
            name='比大小',
            parameters=[Parameter(name='其他', type_annotation='任意')],
            body=[],
            return_type='串',  # 接口要求返回数，实际返回串
        )],
        constructor=ConstructorDefinition(name='整数', parameters=[], body=[]),
    )
    module = Module(trait_defs=[iface], classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    has_return_error = any('返回类型不匹配' in err for err in inf.errors)
    assert has_return_error, f"应检测到返回类型不匹配错误，得 {inf.errors}"

register('类实现接口-返回类型不匹配', test_class_implements_interface_wrong_return_type)


def test_class_implements_interface_undefined_name():
    """类声明的接口未定义 → 应有错误"""
    cls = ClassDefinition(
        name='整数',
        interfaces=['不存在的接口'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(name='整数', parameters=[], body=[]),
    )
    module = Module(classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    has_undef_error = any('未定义' in err for err in inf.errors)
    assert has_undef_error, f"应检测到未定义接口错误，得 {inf.errors}"

register('类实现接口-接口未定义', test_class_implements_interface_undefined_name)


# =====================================================================
# 3. 接口作为泛型约束
# =====================================================================

def test_generic_constraint_typevar_creation():
    """类型变量 T 带接口约束 → TypeVar 的 constraint 正确设置"""
    iface = InterfaceType(interface_name='可比较', methods={
        '比大小': FunctionType([TYPE_ANY], TYPE_NUMBER),
    })
    tv = TypeVar('T', constraint=iface)
    assert tv.constraint is not None
    assert tv.constraint.interface_name == '可比较'
    assert repr(tv) == 'T<:可比较'

register('泛型约束-TypeVar 创建', test_generic_constraint_typevar_creation)


def test_generic_constraint_class_satisfies():
    """类实现了接口 → 在合一中通过约束检查"""
    iface = InterfaceType(interface_name='可比较', methods={
        '比大小': FunctionType([TYPE_ANY], TYPE_NUMBER),
    })
    # 创建 TypeVar 带约束
    tv = TypeVar('T', constraint=iface)

    # 创建类类型，实现接口
    ct = ClassType('整数', implements_interfaces=[iface])

    # 合一 T ~ 整数 → 应成功（整数实现了可比较）
    try:
        subs = unify(tv, ct)
        ok = True
    except UnificationError as e:
        ok = False
        print(f"合一失败: {e}")
    assert ok, "实现了接口的类应与约束型 TypeVar 合一成功"

    # 验证绑定
    assert subs['T'].class_name == '整数', f"应绑定到整数，得 {subs['T']}"

register('泛型约束-类满足约束', test_generic_constraint_class_satisfies)


def test_generic_constraint_class_does_not_satisfy():
    """类未实现接口 → 在合一中应失败"""
    iface = InterfaceType(interface_name='可比较', methods={
        '比大小': FunctionType([TYPE_ANY], TYPE_NUMBER),
    })
    tv = TypeVar('T', constraint=iface)

    # 创建类类型，未实现接口
    ct = ClassType('字符串')

    # 合一 T ~ 字符串 → 应失败
    try:
        subs = unify(tv, ct)
        ok = False
    except UnificationError:
        ok = True
    assert ok, "未实现接口的类应与约束型 TypeVar 合一失败"

register('泛型约束-类不满足约束', test_generic_constraint_class_does_not_satisfy)


def test_generic_constraint_generic_parameter_interface():
    """约束 T 实现 接口 在泛型函数中工作"""
    iface_type = InterfaceType(interface_name='可显示', methods={
        '显示': FunctionType([], TYPE_STRING),
    })

    # 模拟一个约束型参数
    tv = TypeVar('T', constraint=iface_type)
    ft = FunctionType([tv], tv)  # 恒等函数：T -> T

    # 创建类类型，实现了可显示接口
    ct = ClassType('用户', implements_interfaces=[iface_type])

    # 合一形参 T 与实参 用户 → 应成功，返回值应为 用户
    subs = unify(ft.param_types[0], ct)
    resolved = ft.return_type.apply_substitution(subs)
    assert isinstance(resolved, ClassType)
    assert resolved.class_name == '用户'

register('泛型约束-泛型函数约束接口', test_generic_constraint_generic_parameter_interface)


def test_generic_class_constrained_type_param():
    """泛型类的类型参数带接口约束"""
    iface_type = InterfaceType(interface_name='可比较', methods={
        '比大小': FunctionType([TYPE_ANY], TYPE_NUMBER),
    })

    # 模拟一个泛型类定义：类 有序列表<T:可比较>
    # T 受可比较约束
    inf = TypeInferencer()
    # 在作用域中注册带约束的泛型参数
    inf.symbol_table.define_generic_param('T', constraint=iface_type)

    # 解析 T → 应得到 TypeVar with constraint
    t_resolved = inf._parse_type_string('T')
    assert isinstance(t_resolved, TypeVar)
    assert t_resolved.name == 'T'
    assert t_resolved.constraint is not None
    assert t_resolved.constraint.interface_name == '可比较'

register('泛型约束-泛型类参数约束', test_generic_class_constrained_type_param)


# =====================================================================
# 4. 组合测试：完整流程
# =====================================================================

def test_complete_interface_flow():
    """完整流程：定义接口 → 定义类实现接口 → 泛型约束 → 实例类型检查"""
    iface = TraitDefinition(
        name='可比较',
        methods=[
            TraitMethodSignature(name='比大小', parameters=[
                Parameter(name='其他', type_annotation='数'),
            ], return_type='布尔'),
        ],
    )
    cls = ClassDefinition(
        name='向量',
        interfaces=['可比较'],
        generic_params=[],
        superclasses=[],
        fields=[],
        methods=[MethodDefinition(
            name='比大小',
            parameters=[Parameter(name='其他', type_annotation='数')],
            body=[ReturnStatement(value=BooleanLiteral(value=True))],
            return_type='布尔',
        )],
        constructor=ConstructorDefinition(
            name='向量',
            parameters=[Parameter(name='x', type_annotation='数'),
                       Parameter(name='y', type_annotation='数')],
            body=[],
        ),
    )
    module = Module(trait_defs=[iface], classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    # 无错误
    assert len(inf.errors) == 0, f"完整流程不应有错误，得 {inf.errors}"

    # 接口已注册
    assert '可比较' in inf.trait_defs

    # ClassType 记录接口实现
    sym = inf.symbol_table.lookup('向量')
    ct = sym.data_type
    assert isinstance(ct, ClassType)
    assert ct.implements_interfaces[0].interface_name == '可比较'

    # ClassType.is_subtype_of(InterfaceType) 应返回 True
    assert ct.is_subtype_of(inf.trait_defs['可比较']), \
        "向量实现了可比较，应为其子类型"

register('组合测试-完整流程', test_complete_interface_flow)


# =====================================================================
# 5. 非泛型回归测试（确保 Phase 1+2 不破坏）
# =====================================================================

def test_regular_class_without_interface():
    """普通类（不声明接口）应正常工作"""
    cls = ClassDefinition(
        name='点',
        generic_params=[],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='点',
            parameters=[Parameter(name='x', type_annotation='数')],
            body=[],
        ),
    )
    module = Module(classes=[cls], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert len(inf.errors) == 0, f"普通类不应有错误，得 {inf.errors}"
    new_expr = NewExpression(class_name='点', arguments=[make_num(1)], type_args=[])
    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType)
    assert result.class_name == '点'
    assert len(result.implements_interfaces) == 0, "普通类不应有任何接口实现"

register('回归测试-普通类无接口', test_regular_class_without_interface)


# =====================================================================
# 主入口
# =====================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 Phase 3 —— 接口与实现验证 测试")
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