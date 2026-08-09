"""Phase 4 测试：类型推断（局部推断/返回类型推断/泛型实例化推断）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ast_nodes import (
    Module, SegmentDefinition, Parameter, ClassDefinition, MethodDefinition,
    ConstructorDefinition, NumberLiteral, StringLiteral, BooleanLiteral,
    Identifier, FunctionCall, NewExpression, VariableDeclaration,
    ReturnStatement, ExpressionStatement, BinaryOp, SegmentName,
    ListLiteral, ListComprehension,
)
from type_inferencer import TypeInferencer
from type_system import (
    NumberType, StringType, BooleanType, ListType, DictType, TupleType,
    FunctionType, ClassType, InterfaceType, TypeVar, AnyType, UnknownType,
    NullType, unify, TypeSubstitution, UnificationError,
    TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL, TYPE_UNKNOWN, TYPE_ANY,
)

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
# 1. 局部类型推断（变量声明自动推断）
# =====================================================================

def test_local_var_infer_from_literal():
    """var 年龄 = 42  → 自动推断为数"""
    decl = VariableDeclaration(name='年龄', value=make_num(42))
    module = Module(statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('年龄')
    assert sym is not None
    assert isinstance(sym.data_type, NumberType), f"应推断为数，得 {sym.data_type}"

register('局部推断-数字字面量', test_local_var_infer_from_literal)


def test_local_var_infer_string():
    """var 名字 = "张三"  → 自动推断为串"""
    decl = VariableDeclaration(name='名字', value=make_str("张三"))
    module = Module(statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('名字')
    assert isinstance(sym.data_type, StringType), f"应推断为串，得 {sym.data_type}"

register('局部推断-字符串字面量', test_local_var_infer_string)


def test_local_var_infer_list():
    """var 数字列表 = [1, 2, 3]  → 自动推断为列表[数]"""
    lst = ListLiteral(elements=[make_num(1), make_num(2), make_num(3)])
    decl = VariableDeclaration(name='数字列表', value=lst)
    module = Module(statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('数字列表')
    assert isinstance(sym.data_type, ListType), f"应推断为列表类型，得 {type(sym.data_type)}"
    assert isinstance(sym.data_type.element_type, NumberType), \
        f"元素类型应为数，得 {sym.data_type.element_type}"

register('局部推断-列表字面量', test_local_var_infer_list)


def test_local_var_infer_from_generic_function():
    """var 结果 = 恒等(42)  → 从泛型函数调用推断返回类型为数"""
    seg = SegmentDefinition(
        name='恒等',
        parameters=[Parameter(name='x', type_annotation='T')],
        body=[ReturnStatement(value=Identifier(name='x'))],
        return_type='T',
        modifiers=[],
        generic_params=['T'],
    )
    call = FunctionCall(name=SegmentName(name='恒等'), arguments=[make_num(42)], type_args=[])
    decl = VariableDeclaration(name='结果', value=call)
    module = Module(segments=[seg], statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('结果')
    assert isinstance(sym.data_type, NumberType), \
        f"应从泛型函数调用推断为数，得 {sym.data_type}"

register('局部推断-泛型函数调用', test_local_var_infer_from_generic_function)


# =====================================================================
# 2. 解构赋值类型推断
# =====================================================================

def test_destructure_tuple():
    """解构 (x, y) = 返回元组的表达式 → x=数, y=串"""
    seg = SegmentDefinition(
        name='配对',
        parameters=[
            Parameter(name='a', type_annotation='数'),
            Parameter(name='b', type_annotation='串'),
        ],
        body=[],
        return_type='(数, 串)',
        modifiers=[],
    )
    call = FunctionCall(name=SegmentName(name='配对'), arguments=[make_num(1), make_str("hi")], type_args=[])
    decl = VariableDeclaration(
        name='',
        value=call,
        destructure_names=['x', 'y'],
    )
    module = Module(segments=[seg], statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym_x = inf.symbol_table.lookup('x')
    sym_y = inf.symbol_table.lookup('y')
    assert sym_x is not None, "x 应被定义"
    assert sym_y is not None, "y 应被定义"
    assert isinstance(sym_x.data_type, NumberType), f"x 应为数，得 {sym_x.data_type}"
    assert isinstance(sym_y.data_type, StringType), f"y 应为串，得 {sym_y.data_type}"

register('解构赋值-元组', test_destructure_tuple)


# =====================================================================
# 3. 函数返回类型推断
# =====================================================================

def test_func_return_inferred_from_literal():
    """无返回类型声明的函数，从返回语句推断返回类型"""
    seg = SegmentDefinition(
        name='返回数',
        parameters=[],
        body=[ReturnStatement(value=make_num(42))],
        return_type=None,  # 无显式声明
        modifiers=[],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('返回数')
    ft = sym.data_type
    assert isinstance(ft, FunctionType), f"应为 FunctionType，得 {type(ft)}"
    assert isinstance(ft.return_type, NumberType), \
        f"应从返回语句推断为数，得 {ft.return_type}"

register('返回推断-字面量', test_func_return_inferred_from_literal)


def test_func_return_inferred_no_return():
    """无返回语句的函数 → 推断返回类型为空"""
    seg = SegmentDefinition(
        name='无返回',
        parameters=[],
        body=[ExpressionStatement(expression=make_num(1))],  # 无 return
        return_type=None,
        modifiers=[],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('无返回')
    ft = sym.data_type
    assert isinstance(ft, FunctionType)
    assert isinstance(ft.return_type, NullType), \
        f"无返回语句函数应推断为 NullType，得 {ft.return_type}"

register('返回推断-无返回语句', test_func_return_inferred_no_return)


def test_func_return_inferred_multi_consistent():
    """多条返回语句类型一致 → 正确推断"""
    seg = SegmentDefinition(
        name='判断',
        parameters=[Parameter(name='x', type_annotation='数')],
        body=[
            ReturnStatement(value=make_str("是")),
            ReturnStatement(value=make_str("否")),
        ],
        return_type=None,
        modifiers=[],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('判断')
    ft = sym.data_type
    assert isinstance(ft.return_type, StringType), \
        f"多条保持一致返回串，得 {ft.return_type}"

register('返回推断-多条一致', test_func_return_inferred_multi_consistent)


def test_func_declared_return_takes_precedence():
    """显式声明的返回类型优先于推断"""
    seg = SegmentDefinition(
        name='声明优先',
        parameters=[],
        body=[ReturnStatement(value=make_num(42))],
        return_type='任意',  # 显式声明为任意
        modifiers=[],
    )
    module = Module(segments=[seg], statements=[])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('声明优先')
    ft = sym.data_type
    assert isinstance(ft.return_type, AnyType), \
        f"显式声明的任意应优先，得 {ft.return_type}"

register('返回推断-声明优先', test_func_declared_return_takes_precedence)


# =====================================================================
# 4. 泛型实例化自动推断
# =====================================================================

def test_generic_new_infer_from_ctor():
    """新 列表(42) → 从构造函数参数推断 T=数"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[], interfaces=[], fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='首个', type_annotation='T')],
            body=[],
        ),
    )
    new_expr = NewExpression(class_name='列表', arguments=[make_num(42)], type_args=[])
    module = Module(classes=[cls], statements=[ExpressionStatement(expression=new_expr)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType), f"应为 ClassType，得 {type(result)}"
    assert result.class_name == '列表'
    assert len(result.type_args) == 1
    assert isinstance(result.type_args[0], NumberType), \
        f"从构造参数 42 应推断 T=数，得 {result.type_args[0]}"

register('泛型实例化-构造函数推断', test_generic_new_infer_from_ctor)


def test_generic_new_infer_multi_params():
    """新 映射(1, "a") → 推断两个类型参数"""
    cls = ClassDefinition(
        name='映射',
        generic_params=['K', 'V'],
        superclasses=[], interfaces=[], fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='映射',
            parameters=[
                Parameter(name='键', type_annotation='K'),
                Parameter(name='值', type_annotation='V'),
            ],
            body=[],
        ),
    )
    new_expr = NewExpression(class_name='映射', arguments=[make_num(1), make_str("a")], type_args=[])
    module = Module(classes=[cls], statements=[ExpressionStatement(expression=new_expr)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType)
    assert result.class_name == '映射'
    assert len(result.type_args) == 2
    assert isinstance(result.type_args[0], NumberType), f"K 应为数，得 {result.type_args[0]}"
    assert isinstance(result.type_args[1], StringType), f"V 应为串，得 {result.type_args[1]}"

register('泛型实例化-多参数推断', test_generic_new_infer_multi_params)


def test_generic_new_explicit_overrides_inference():
    """显式类型参数优先于构造函数推断"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[], interfaces=[], fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='首个', type_annotation='T')],
            body=[],
        ),
    )
    # 显式指定 T=串，但参数为数 → 应使用显式的串
    new_expr = NewExpression(class_name='列表', arguments=[make_num(42)], type_args=['串'])
    module = Module(classes=[cls], statements=[ExpressionStatement(expression=new_expr)])
    inf = TypeInferencer()
    inf.infer(module)

    result = inf._infer_expr(new_expr)
    assert isinstance(result, ClassType)
    assert len(result.type_args) == 1
    assert isinstance(result.type_args[0], StringType), \
        f"显式 T=串 应覆盖构造参数推断，得 {result.type_args[0]}"

register('泛型实例化-显式覆盖', test_generic_new_explicit_overrides_inference)


def test_generic_new_var_decl_chain():
    """var 我的列表 = 新 列表(42) → 变量 我的列表 的类型为 ClassType('列表', [NumberType])"""
    cls = ClassDefinition(
        name='列表',
        generic_params=['T'],
        superclasses=[], interfaces=[], fields=[],
        methods=[],
        constructor=ConstructorDefinition(
            name='列表',
            parameters=[Parameter(name='首个', type_annotation='T')],
            body=[],
        ),
    )
    new_expr = NewExpression(class_name='列表', arguments=[make_num(42)], type_args=[])
    decl = VariableDeclaration(name='我的列表', value=new_expr)
    module = Module(classes=[cls], statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('我的列表')
    assert sym is not None
    assert isinstance(sym.data_type, ClassType), f"应为 ClassType，得 {type(sym.data_type)}"
    assert sym.data_type.class_name == '列表'
    assert isinstance(sym.data_type.type_args[0], NumberType), \
        f"变量类型参数应推断为数，得 {sym.data_type.type_args[0]}"

register('泛型实例化-变量声明链', test_generic_new_var_decl_chain)


# =====================================================================
# 5. 组合测试：全流程
# =====================================================================

def test_full_inference_pipeline():
    """完整流程：泛型函数定义 → 调用 → 变量声明 → 返回推断"""
    seg = SegmentDefinition(
        name='双倍',
        parameters=[Parameter(name='x', type_annotation='T')],
        body=[ReturnStatement(value=BinaryOp(
            left=Identifier(name='x'),
            operator='+',
            right=Identifier(name='x'),
        ))],
        return_type=None,  # 让推断器推断
        modifiers=[],
        generic_params=['T'],
    )
    call = FunctionCall(name=SegmentName(name='双倍'), arguments=[make_num(21)], type_args=[])
    decl = VariableDeclaration(name='结果', value=call)
    module = Module(segments=[seg], statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    # 变量结果应为 数（从调用双倍(21) 推断 T=数, 返回 T=数）
    sym = inf.symbol_table.lookup('结果')
    assert sym is not None
    assert isinstance(sym.data_type, NumberType), \
        f"变量结果应为数，得 {sym.data_type}"

register('组合测试-全流程推断', test_full_inference_pipeline)


# =====================================================================
# 6. 回归测试（确保 Phase 3 不破坏）
# =====================================================================

def test_regular_class_with_annotation():
    """带注解的变量声明仍正常工作"""
    decl = VariableDeclaration(name='年龄', value=make_num(42), type_annotation='数')
    module = Module(statements=[decl])
    inf = TypeInferencer()
    inf.infer(module)

    sym = inf.symbol_table.lookup('年龄')
    assert isinstance(sym.data_type, NumberType)
    assert len(inf.errors) == 0, f"不应有错误，得 {inf.errors}"

register('回归测试-带注解变量', test_regular_class_with_annotation)


# =====================================================================
# 主入口
# =====================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 Phase 4 —— 类型推断 测试")
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