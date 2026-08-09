"""Phase 2 测试：泛型段落（函数）和泛型类"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ast_nodes import (
    Module, SegmentDefinition, Parameter, ClassDefinition, MethodDefinition,
    ConstructorDefinition, NumberLiteral, StringLiteral, BooleanLiteral,
    Identifier, FunctionCall, NewExpression, VariableDeclaration,
    ReturnStatement, ExpressionStatement, BinaryOp, SegmentName
)
from type_inferencer import TypeInferencer
from type_system import (
    NumberType, StringType, BooleanType, ListType, DictType, FunctionType,
    ClassType, TypeVar, AnyType, UnknownType, unify, TypeSubstitution,
    UnificationError
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
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ✗ {name}: {type(e).__name__}: {e}")

# =====================================================================
# 1. 泛型段落（函数）测试
# =====================================================================

def test_generic_segment_simple_map():
    """段落 映射<T>(元素): T, 函数: T->T -> T   调用时自动推断 T=数"""
    # 定义：映射<T>(元素: T, 函数: T->T) -> T
    seg = SegmentDefinition(
        name='映射',
        parameters=[
            Parameter(name='元素', type_annotation='T'),
            Parameter(name='函数', type_annotation='(T) -> T'),
        ],
        body=[],
        return_type='T',
        modifiers=[],
        generic_params=['T'],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    # 检查泛型段落注册
    assert '映射' in inf.generic_segment_defs, "映射应注册为泛型段落"
    assert inf.generic_segment_defs['映射'] == ['T']

    # 检查函数类型
    sym = inf.symbol_table.lookup('映射')
    assert sym is not None, "'映射' 符号应存在"
    ft = sym.data_type
    assert isinstance(ft, FunctionType), f"应为 FunctionType，实际 {type(ft).__name__}"
    assert len(ft.param_types) == 2
    # 第一个参数应为 TypeVar T
    assert isinstance(ft.param_types[0], TypeVar), f"参数1应为 TypeVar，得 {ft.param_types[0]}"
    assert ft.param_types[0].name == 'T'
    # 返回类型也是 T
    assert isinstance(ft.return_type, TypeVar), f"返回类型应为 TypeVar，得 {ft.return_type}"
    assert ft.return_type.name == 'T'

    # 模拟调用：映射(5, x->x)  应推断出 T=数 → 返回数
    # 直接测试函数签名的合一
    sig_t = ft.param_types[0]  # T
    concrete = NumberType()
    subs = unify(sig_t, concrete)
    resolved_return = ft.return_type.apply_substitution(subs)
    assert isinstance(resolved_return, NumberType), f"合一后返回应为数，得 {resolved_return}"


register('泛型段落-映射函数基本定义', test_generic_segment_simple_map)


def test_generic_segment_call_inference():
    """泛型段落调用：通过参数类型自动推断 T"""
    seg = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x', type_annotation='T')],
        body=[ReturnStatement(value=Identifier(name='x'))],
        return_type='T',
        modifiers=[],
        generic_params=['T'],
    )

    # 调用：恒等(42) → 应返回 数
    call1 = FunctionCall(
        name=SegmentName(name='恒等'),
        arguments=[make_num(42)],
        type_args=[],
    )

    module = Module(segments=[seg], statements=[ExpressionStatement(expression=call1)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(call1)
    assert isinstance(result, NumberType), f"调用恒等(42) 应返回数，得 {result}"

    # 调用：恒等("hello") → 应返回 串
    call2 = FunctionCall(
        name=SegmentName(name='恒等'),
        arguments=[make_str("hello")],
        type_args=[],
    )
    result2 = inf._infer_expr(call2)
    assert isinstance(result2, StringType), f"调用恒等('hello') 应返回串，得 {result2}"


register('泛型段落-调用时类型参数推断', test_generic_segment_call_inference)


def test_generic_segment_explicit_type_args():
    """泛型段落显式类型参数：映射[数](...)"""
    seg = SegmentDefinition(
        name='映射',
        parameters=[
            Parameter(name='元素', type_annotation='T'),
            Parameter(name='变换', type_annotation='(T) -> T'),
        ],
        body=[],
        return_type='T',
        modifiers=[],
        generic_params=['T'],
    )

    # 显式指定 T=数
    call = FunctionCall(
        name=SegmentName(name='映射'),
        arguments=[make_num(5), make_num(10)],  # 简化的参数
        type_args=['数'],
    )

    module = Module(segments=[seg], statements=[ExpressionStatement(expression=call)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(call)
    # 显式类型参数应被应用：T→数，返回 T→数
    assert isinstance(result, NumberType), f"显式指定 T=数 后应返回数，得 {result}"


register('泛型段落-显式类型参数', test_generic_segment_explicit_type_args)


def test_generic_segment_two_type_params():
    """双类型参数泛型段落：配对<A, B> 接收 第一个: A, 第二个: B -> 元组(A, B)"""
    seg = SegmentDefinition(
        name='配对',
        parameters=[
            Parameter(name='第一个', type_annotation='A'),
            Parameter(name='第二个', type_annotation='B'),
        ],
        body=[],
        return_type='(A, B)',
        modifiers=[],
        generic_params=['A', 'B'],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert inf.generic_segment_defs['配对'] == ['A', 'B']
    sym = inf.symbol_table.lookup('配对')
    ft = sym.data_type
    # 测试显式类型参数调用：配对[数, 串](1, "hi")
    call = FunctionCall(
        name=SegmentName(name='配对'),
        arguments=[make_num(1), make_str("hi")],
        type_args=['数', '串'],
    )
    # 加入到模块语句
    module2 = Module(segments=[seg], statements=[ExpressionStatement(expression=call)])
    inf2 = TypeInferencer()
    inf2.infer(module2)
    result = inf2._infer_expr(call)
    # 返回 (数, 串) = TupleType
    from type_system import TupleType
    assert isinstance(result, TupleType), f"应返回元组类型，得 {result}"
    assert len(result.element_types) == 2
    assert isinstance(result.element_types[0], NumberType)
    assert isinstance(result.element_types[1], StringType)


register('泛型段落-多类型参数', test_generic_segment_two_type_params)


# =====================================================================
# 2. 泛型类测试
# =====================================================================

def test_generic_class_definition_registered():
    """类 列表<T> 被正确注册为泛型类"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[MethodDefinition(
            name='长度',
            parameters=[],
            body=[],
            return_type='数',
            is_static=False,
        )],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='初始', type_annotation='列表[T]')],
            body=[],
        ),
    )
    module = Module(classes=[cls], segments=[], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert '列表' in inf.generic_class_defs, "列表应注册为泛型类"
    assert inf.generic_class_defs['列表'] == ['T']


register('泛型类-定义注册', test_generic_class_definition_registered)


def test_generic_class_explicit_type_args():
    """新 列表[数](空) → 应返回 列表[数]"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='内容', type_annotation='T')],
            body=[],
        ),
    )
    # 新 列表[数](123)
    new_expr = NewExpression(class_name='列表', arguments=[make_num(123)], type_args=['数'])

    module = Module(classes=[cls], segments=[], statements=[ExpressionStatement(expression=new_expr)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType), f"应返回 ClassType，得 {result}"
    assert result.class_name == '列表'
    assert len(result.type_args) == 1
    assert isinstance(result.type_args[0], NumberType), f"类型参数应为数，得 {result.type_args[0]}"


register('泛型类-显式类型参数实例化', test_generic_class_explicit_type_args)


def test_generic_class_infer_type_args_from_ctor():
    """新 列表(5) → 从构造函数参数推断 T=数"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='首个', type_annotation='T')],
            body=[],
        ),
    )
    new_expr = NewExpression(class_name='列表', arguments=[make_num(42)], type_args=[])
    module = Module(classes=[cls], segments=[], statements=[ExpressionStatement(expression=new_expr)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType)
    assert result.class_name == '列表'
    # T 应被推断为数
    assert len(result.type_args) == 1
    assert isinstance(result.type_args[0], NumberType), \
        f"从构造函数参数 42 应推断 T=数，实际 {result.type_args[0]}"


register('泛型类-构造函数推断类型参数', test_generic_class_infer_type_args_from_ctor)


def test_generic_class_method_substitution():
    """列表[数] 的 添加(元素: T) 方法 → 参数类型应为数"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[MethodDefinition(
            name='添加',
            parameters=[Parameter(name='元素', type_annotation='T')],
            body=[],
            return_type='空',
            is_static=False,
        )],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[],
            body=[],
        ),
    )
    # 新 列表[数]()
    new_expr = NewExpression(class_name='列表', arguments=[], type_args=['数'])

    module = Module(classes=[cls], segments=[], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    # 获取实例类型
    instance_type = inf._infer_expr(new_expr)
    assert isinstance(instance_type, ClassType)
    assert instance_type.class_name == '列表'

    # 属性访问：列表[数]之添加  应返回 FunctionType(param_types=[数], return=空)
    from ast_nodes import PropertyAccess
    access = PropertyAccess(obj=new_expr, property_name='添加')
    method_type = inf._infer_expr(access)

    assert isinstance(method_type, FunctionType), f"方法应返回 FunctionType，得 {type(method_type).__name__}: {method_type}"
    assert len(method_type.param_types) == 1
    assert isinstance(method_type.param_types[0], NumberType), \
        f"方法参数经替换后应为数，实际 {method_type.param_types[0]}"


register('泛型类-方法调用类型替换', test_generic_class_method_substitution)


def test_generic_class_method_call_typecheck():
    """调用 列表[数]之添加(5) → 参数类型一致；添加("hi") → 参数类型不匹配"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[MethodDefinition(
            name='添加',
            parameters=[Parameter(name='元素', type_annotation='T')],
            body=[],
            return_type='空',
            is_static=False,
        )],
        constructor=ConstructorDefinition(name='列表', parameters=[], body=[]),
    )
    # 新 列表[数]()
    new_expr = NewExpression(class_name='列表', arguments=[], type_args=['数'])

    module = Module(classes=[cls], segments=[], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    # 访问添加方法
    from ast_nodes import PropertyAccess
    access = PropertyAccess(obj=new_expr, property_name='添加')
    method_type = inf._infer_expr(access)

    # 手动验证：用类型系统 unify 测试参数
    # 调用 添加(5)：形参 T→数，实参数 → 应合一成功
    try:
        subs = unify(method_type.param_types[0], NumberType())
        ok_valid = True
    except UnificationError:
        ok_valid = False
    assert ok_valid, "列表[数]之添加(5) 应通过类型检查"

    # 调用 添加("hi")：形参数，实参串 → 应合一失败
    try:
        unify(method_type.param_types[0], StringType())
        ok_invalid_should_fail = False
    except UnificationError:
        ok_invalid_should_fail = True
    assert ok_invalid_should_fail, "列表[数]之添加('hi') 应触发类型错误"


register('泛型类-方法调用参数类型检查', test_generic_class_method_call_typecheck)


# =====================================================================
# 3. 组合测试：泛型函数 + 泛型类
# =====================================================================

def test_combo_generic_function_with_generic_class():
    """段落 映射<T>(列表): 列表[T], 函数: T->T -> 列表[T]"""
    seg = SegmentDefinition(
        name='映射',
        parameters=[
            Parameter(name='列表', type_annotation='列表[T]'),
            Parameter(name='函数', type_annotation='(T) -> T'),
        ],
        body=[],
        return_type='列表[T]',
        modifiers=[],
        generic_params=['T'],
    )
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(name='列表', parameters=[], body=[]),
    )

    # 先验证签名
    module = Module(classes=[cls], segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('映射')
    ft = sym.data_type
    assert isinstance(ft, FunctionType)

    # 参数1：列表[T] —— 检查内部有 T 类型变量
    p1 = ft.param_types[0]
    def _find_T(t: object) -> bool:
        if isinstance(t, TypeVar) and t.name == 'T':
            return True
        if hasattr(t, 'element_type') and t.element_type is not None:
            return _find_T(t.element_type)
        if hasattr(t, 'type_args') and t.type_args:
            return any(_find_T(x) for x in t.type_args)
        return False
    assert _find_T(p1), f"参数1应包含 T 类型变量，得 {p1}"

    # 返回：列表[T]
    ret = ft.return_type
    assert _find_T(ret), f"返回类型应包含 T 类型变量，得 {ret}"

    # 调用：映射(新 列表[数](), 某函数) → T 被推断为数 → 返回 列表[数]
    new_list = NewExpression(class_name='列表', arguments=[], type_args=['数'])
    call = FunctionCall(
        name=SegmentName(name='映射'),
        arguments=[new_list, make_num(1)],  # 简化
        type_args=[],
    )

    module2 = Module(classes=[cls], segments=[seg], statements=[ExpressionStatement(expression=call)])
    inf2 = TypeInferencer()
    inf2.infer(module2)

    # 直接基于签名测试合一（而不是调用完整表达式，因为简化的参数）
    sig_p1 = ft.param_types[0]  # 列表[T] (ListType[TypeVar(T)])
    concrete_p1 = ListType(NumberType())  # 列表[数]
    subs = unify(sig_p1, concrete_p1)
    resolved_return = ft.return_type.apply_substitution(subs)
    # resolved_return 应为 列表[数]
    def _find_NumberType(t: object) -> bool:
        if isinstance(t, NumberType):
            return True
        if hasattr(t, 'element_type') and t.element_type is not None:
            return _find_NumberType(t.element_type)
        if hasattr(t, 'type_args') and t.type_args:
            return any(_find_NumberType(x) for x in t.type_args)
        return False
    assert _find_NumberType(resolved_return), \
        f"映射被调用为 列表[数] 时，返回的元素类型应为数，实际 {resolved_return}"


register('组合测试-泛型函数与泛型类', test_combo_generic_function_with_generic_class)


# =====================================================================
# 4. 非泛型回归测试（确保 Phase 1 不破坏）
# =====================================================================

def test_regular_segment_still_works():
    """非泛型段落不应被误识别为泛型"""
    seg = SegmentDefinition(
        name='加1',
        parameters=[Parameter(name='x', type_annotation='数')],
        body=[],
        return_type='数',
        modifiers=[],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    assert '加1' not in inf.generic_segment_defs, "非泛型段落不应出现在 generic_segment_defs 中"
    sym = inf.symbol_table.lookup('加1')
    assert isinstance(sym.data_type, FunctionType)
    assert isinstance(sym.data_type.param_types[0], NumberType)
    assert isinstance(sym.data_type.return_type, NumberType)


register('回归测试-普通段落', test_regular_segment_still_works)


def test_regular_class_still_works():
    """普通类（非泛型）注册和实例化"""
    cls = ClassDefinition(
        name='点',
        generic_params=[],
        superclasses=[],
        interfaces=[],
        fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='点',
            parameters=[
                Parameter(name='x', type_annotation='数'),
                Parameter(name='y', type_annotation='数'),
            ],
            body=[],
        ),
    )
    module = Module(classes=[cls], segments=[], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    # 普通类不应出现在泛型类注册表
    assert '点' not in inf.generic_class_defs

    new_expr = NewExpression(class_name='点', arguments=[make_num(1), make_num(2)], type_args=[])
    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType) and result.class_name == '点'
    assert len(result.type_args) == 0, "普通类实例化不应该有类型参数"


register('回归测试-普通类', test_regular_class_still_works)


# =====================================================================
# 主入口
# =====================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 Phase 2 —— 泛型段落 & 泛型类 测试")
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
