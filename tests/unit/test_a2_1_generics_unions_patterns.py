# -*- coding: utf-8 -*-
"""
A2.1 综合测试：泛型类型、联合类型和模式匹配

测试范围：
  1. 泛型类型：TypeVar、泛型实例化、泛化/实例化、类型变量替换
  2. 联合类型：创建、子类型、合一、类型缩小、穷尽性检查
  3. 模式匹配：枚举匹配、联合类型匹配、穷尽性检查、类型守卫

对应计划：A2.1 泛型/联合类型/模式匹配实现
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


# =============================================================================
# 第一部分：泛型类型测试
# =============================================================================

class TestGenericsTypeVar(unittest.TestCase):
    """泛型类型变量测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeVar, TypeSubstitution, UnificationError, unify,
                NumberType, StringType, BooleanType, NullType,
                AnyType, UnknownType, ListType, DictType, TupleType,
                FunctionType, TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.UnificationError = UnificationError
            cls.unify = staticmethod(unify)
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.AnyType = AnyType
            cls.UnknownType = UnknownType
            cls.ListType = ListType
            cls.DictType = DictType
            cls.TupleType = TupleType
            cls.FunctionType = FunctionType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_type_var_creation(self):
        """创建类型变量 T"""
        T = self.TypeVar('T')
        self.assertEqual(T.name, 'T')
        self.assertIsNone(T.constraint)

    def test_type_var_with_constraint(self):
        """创建带约束的类型变量 T<:数"""
        T = self.TypeVar('T', self.TYPE_NUMBER)
        self.assertEqual(T.name, 'T')
        self.assertIsNotNone(T.constraint)
        self.assertEqual(str(T.constraint), "数")

    def test_type_var_equality(self):
        """同名类型变量相等"""
        T1 = self.TypeVar('T')
        T2 = self.TypeVar('T')
        self.assertEqual(T1, T2)

    def test_type_var_inequality(self):
        """不同名类型变量不等"""
        T = self.TypeVar('T')
        U = self.TypeVar('U')
        self.assertNotEqual(T, U)

    def test_type_var_hashable(self):
        """类型变量支持集合操作"""
        s = {self.TypeVar('T'), self.TypeVar('T'), self.TypeVar('U')}
        self.assertEqual(len(s), 2)

    def test_type_var_subtype_same(self):
        """相同类型变量是子类型"""
        T = self.TypeVar('T')
        self.assertTrue(T.is_subtype_of(T))

    def test_type_var_subtype_any(self):
        """类型变量是 Any 的子类型"""
        T = self.TypeVar('T')
        self.assertTrue(T.is_subtype_of(self.TYPE_ANY))

    def test_type_var_subtype_constraint(self):
        """带约束的类型变量是约束的子类型"""
        T = self.TypeVar('T', self.TYPE_NUMBER)
        self.assertTrue(T.is_subtype_of(self.TYPE_NUMBER))

    def test_type_var_collect(self):
        """收集类型变量"""
        T = self.TypeVar('T')
        tvars = T.collect_type_vars()
        self.assertEqual(len(tvars), 1)
        self.assertEqual(list(tvars)[0].name, 'T')

    def test_type_var_substitution(self):
        """类型变量替换"""
        T = self.TypeVar('T')
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        result = T.apply_substitution(subs)
        self.assertEqual(str(result), "数")

    def test_type_var_no_substitution(self):
        """无替换时不改变"""
        T = self.TypeVar('T')
        result = T.apply_substitution(None)
        self.assertIs(result, T)

    def test_type_var_substitution_unknown(self):
        """未绑定的类型变量不被替换"""
        T = self.TypeVar('T')
        U = self.TypeVar('U')
        subs = self.TypeSubstitution({'U': self.TYPE_NUMBER})
        result = T.apply_substitution(subs)
        self.assertIsInstance(result, self.TypeVar)
        self.assertEqual(result.name, 'T')

    def test_unify_type_var_with_number(self):
        """合一 T 与 数 → T 绑定为 数"""
        T = self.TypeVar('T')
        subs = self.unify(T, self.TYPE_NUMBER)
        self.assertIn('T', subs)
        self.assertEqual(str(subs['T']), "数")

    def test_unify_number_with_type_var(self):
        """合一 数 与 T → T 绑定为 数"""
        T = self.TypeVar('T')
        subs = self.unify(self.TYPE_NUMBER, T)
        self.assertIn('T', subs)
        self.assertEqual(str(subs['T']), "数")

    def test_unify_type_var_with_self(self):
        """合一 T 与 T → 空替换"""
        T = self.TypeVar('T')
        subs = self.unify(T, T)
        self.assertIsNotNone(subs)

    def test_unify_type_var_with_unknown(self):
        """合一 T 与 未知 → 空替换（未知类型通配）"""
        T = self.TypeVar('T')
        subs = self.unify(T, self.TYPE_UNKNOWN)
        self.assertIsNotNone(subs)

    def test_unify_occurs_check(self):
        """发生检查：T 不能出现在 List[T] 内部"""
        T = self.TypeVar('T')
        list_t = self.ListType(T)
        with self.assertRaises(self.UnificationError):
            self.unify(T, list_t)

    def test_unify_occurs_check_ok(self):
        """非递归：T 与 List[U] 合一，T 不在 List[U] 内部（U ≠ T）"""
        T = self.TypeVar('T')
        U = self.TypeVar('U')
        list_u = self.ListType(U)
        try:
            subs = self.unify(T, list_u)
            self.assertIn('T', subs)
        except self.UnificationError:
            self.fail("T 与 List[U] 应能合一")


class TestGenericsGenericInstance(unittest.TestCase):
    """泛型类型实例测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeVar, TypeSubstitution, UnificationError, unify,
                GenericTypeInstance, GenericTypeDef,
                NumberType, StringType, ListType, DictType, TupleType,
                FunctionType, TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.UnificationError = UnificationError
            cls.unify = staticmethod(unify)
            cls.GenericTypeInstance = GenericTypeInstance
            cls.GenericTypeDef = GenericTypeDef
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.ListType = ListType
            cls.DictType = DictType
            cls.TupleType = TupleType
            cls.FunctionType = FunctionType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_generic_instance_creation(self):
        """创建泛型实例 列表[数]"""
        inst = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        self.assertEqual(inst.base_name, '列表')
        self.assertEqual(len(inst.type_args), 1)
        self.assertEqual(str(inst.type_args[0]), "数")

    def test_generic_instance_two_args(self):
        """创建泛型实例 映射[串, 数]"""
        inst = self.GenericTypeInstance('映射', [self.TYPE_STRING, self.TYPE_NUMBER])
        self.assertEqual(len(inst.type_args), 2)
        self.assertEqual(str(inst), "映射[串, 数]")

    def test_generic_instance_repr(self):
        """泛型实例字符串表示"""
        inst = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        self.assertEqual(str(inst), "列表[数]")

    def test_generic_instance_no_args(self):
        """无类型参数的泛型实例"""
        inst = self.GenericTypeInstance('列表', [])
        self.assertEqual(str(inst), "列表")

    def test_generic_instance_subtype(self):
        """泛型实例子类型关系"""
        a = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        b = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        self.assertTrue(a.is_subtype_of(b))

    def test_generic_instance_subtype_different_base(self):
        """不同基名的泛型实例不是子类型"""
        a = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        b = self.GenericTypeInstance('映射', [self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertFalse(a.is_subtype_of(b))

    def test_generic_instance_collect_type_vars(self):
        """泛型实例收集类型变量"""
        T = self.TypeVar('T')
        inst = self.GenericTypeInstance('列表', [T])
        tvars = inst.collect_type_vars()
        self.assertEqual(len(tvars), 1)
        self.assertEqual(list(tvars)[0].name, 'T')

    def test_generic_instance_substitution(self):
        """泛型实例应用类型变量替换"""
        T = self.TypeVar('T')
        inst = self.GenericTypeInstance('列表', [T])
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        result = inst.apply_substitution(subs)
        self.assertIsInstance(result, self.GenericTypeInstance)
        self.assertEqual(str(result.type_args[0]), "数")

    def test_generic_instance_unify_same(self):
        """合一两个相同泛型实例"""
        a = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        b = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        try:
            subs = self.unify(a, b)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同泛型实例应能合一")

    def test_generic_instance_unify_with_type_var(self):
        """合一泛型实例与类型变量"""
        T = self.TypeVar('T')
        inst = self.GenericTypeInstance('列表', [T])
        actual = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        try:
            subs = self.unify(inst, actual)
            self.assertIn('T', subs)
            self.assertEqual(str(subs['T']), "数")
        except self.UnificationError:
            self.fail("应能合一")

    def test_generic_instance_unify_with_list(self):
        """泛型实例 列表[数] 与 ListType(数) 合一"""
        inst = self.GenericTypeInstance('列表', [self.TYPE_NUMBER])
        lst = self.ListType(self.TYPE_NUMBER)
        try:
            subs = self.unify(inst, lst)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("列表[数] 与 ListType(数) 应能合一")

    def test_generic_instance_unify_with_dict(self):
        """泛型实例 映射[串, 数] 与 DictType(串, 数) 合一"""
        inst = self.GenericTypeInstance('映射', [self.TYPE_STRING, self.TYPE_NUMBER])
        dct = self.DictType(self.TYPE_STRING, self.TYPE_NUMBER)
        try:
            subs = self.unify(inst, dct)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("映射[串, 数] 与 DictType(串, 数) 应能合一")

    def test_generic_def_creation(self):
        """创建泛型定义 列表<T>"""
        T = self.TypeVar('T')
        gen_def = self.GenericTypeDef('列表', ['T'])
        self.assertEqual(gen_def.base_name, '列表')
        self.assertEqual(gen_def.param_names, ['T'])

    def test_generic_def_collect(self):
        """泛型定义收集类型变量"""
        gen_def = self.GenericTypeDef('列表', ['T', 'U'])
        tvars = gen_def.collect_type_vars()
        self.assertEqual(len(tvars), 2)


class TestGenericsInference(unittest.TestCase):
    """泛型类型推断测试（HM 风格泛化/实例化）"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                TypeVar, TypeSubstitution, unify, FunctionType,
                NumberType, StringType, BooleanType, NullType,
                ListType, DictType, AnyType, UnknownType,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            from ast_nodes import (
                Module, SegmentDefinition, Parameter,
                VariableDeclaration, NumberLiteral, StringLiteral,
                BooleanLiteral, NullLiteral, Identifier,
                BinaryOp, FunctionCall, ExpressionStatement,
                ReturnStatement, ListLiteral,
            )
            cls.TypeInferencer = TypeInferencer
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.unify = staticmethod(unify)
            cls.FunctionType = FunctionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.ListType = ListType
            cls.DictType = DictType
            cls.AnyType = AnyType
            cls.UnknownType = UnknownType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
            # AST 节点
            cls.Module = Module
            cls.SegmentDefinition = SegmentDefinition
            cls.Parameter = Parameter
            cls.VariableDeclaration = VariableDeclaration
            cls.NumberLiteral = NumberLiteral
            cls.StringLiteral = StringLiteral
            cls.BooleanLiteral = BooleanLiteral
            cls.NullLiteral = NullLiteral
            cls.Identifier = Identifier
            cls.BinaryOp = BinaryOp
            cls.FunctionCall = FunctionCall
            cls.ExpressionStatement = ExpressionStatement
            cls.ReturnStatement = ReturnStatement
            cls.ListLiteral = ListLiteral
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_generic_identity_function(self):
        """泛型恒等函数：段 id(x) 返回 x  → 推断为 T -> T"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='id',
                    parameters=[self.Parameter(name='x')],
                    body=[
                        self.ReturnStatement(value=self.Identifier(name='x')),
                    ],
                ),
            ],
        )
        inf.infer(module)
        # 检查是否有错误
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        # 检查推断结果
        sym = inf.symbol_table.lookup('id')
        self.assertIsNotNone(sym)
        ft = sym.data_type
        self.assertIsInstance(ft, self.FunctionType)
        self.assertEqual(len(ft.param_types), 1)
        # 参数和返回类型应对应（都是 T）
        self.assertEqual(str(ft.param_types[0]), str(ft.return_type))

    def test_generic_first_of_pair(self):
        """泛型取第一个：段 first(x, y) 返回 x  → 推断为 (T, U) -> T"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='first',
                    parameters=[self.Parameter(name='x'), self.Parameter(name='y')],
                    body=[
                        self.ReturnStatement(value=self.Identifier(name='x')),
                    ],
                ),
            ],
        )
        inf.infer(module)
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        sym = inf.symbol_table.lookup('first')
        self.assertIsNotNone(sym)
        ft = sym.data_type
        self.assertIsInstance(ft, self.FunctionType)
        self.assertEqual(len(ft.param_types), 2)
        # 返回类型与第一个参数类型一致
        self.assertEqual(str(ft.return_type), str(ft.param_types[0]))

    def test_generic_instantiation_multiple_calls(self):
        """泛型函数多次调用，各调用点独立实例化"""
        # 验证：段 id(x) 返回 x 被推断为泛型 T -> T
        # 然后 id(1) 和 id("hello") 分别实例化为 数 -> 数 和 串 -> 串
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='id',
                    parameters=[self.Parameter(name='x')],
                    body=[
                        self.ReturnStatement(value=self.Identifier(name='x')),
                    ],
                ),
            ],
            statements=[
                self.VariableDeclaration(
                    name='a',
                    value=self.FunctionCall(
                        name=self.Identifier(name='id'),
                        arguments=[self.NumberLiteral(value=1)],
                    ),
                ),
                self.VariableDeclaration(
                    name='b',
                    value=self.FunctionCall(
                        name=self.Identifier(name='id'),
                        arguments=[self.StringLiteral(value='hello')],
                    ),
                ),
            ],
        )
        inf.infer(module)
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        # 检查变量 'a' 的类型（应为数）
        sym_a = inf.symbol_table.lookup('a')
        self.assertIsNotNone(sym_a)
        self.assertEqual(str(sym_a.data_type), "数")
        # 检查变量 'b' 的类型（应为串）
        sym_b = inf.symbol_table.lookup('b')
        self.assertIsNotNone(sym_b)
        self.assertEqual(str(sym_b.data_type), "串")

    def test_generic_list_first(self):
        """泛型列表处理：段 first_item(lst) 返回 lst[0]"""
        inf = self.TypeInferencer()
        # TODO: 待列表索引表达式实现后，补充此测试
        # 当前跳过，因为索引访问需要更完整的 AST 支持
        pass

    def test_generic_segment_def_recorded(self):
        """泛型段定义被记录在 generic_segment_defs 中"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='id',
                    parameters=[self.Parameter(name='x')],
                    body=[
                        self.ReturnStatement(value=self.Identifier(name='x')),
                    ],
                ),
            ],
        )
        inf.infer(module)
        # 段 id 应被记录为泛型段
        self.assertIn('id', inf.generic_segment_defs)


# =============================================================================
# 第二部分：联合类型测试
# =============================================================================

class TestUnionTypeAdvanced(unittest.TestCase):
    """联合类型高级测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeSubstitution, UnificationError, unify, TypeParser,
                UnionType, NumberType, StringType, BooleanType,
                NullType, AnyType, UnknownType, TypeVar,
                OptionalTypeWrapper, ListType, DictType, SetType,
                TupleType, FunctionType, FutureType,
                GenericTypeInstance, ClassType, InterfaceType, EnumType,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.AnyType = AnyType
            cls.UnknownType = UnknownType
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.UnificationError = UnificationError
            cls.unify = staticmethod(unify)
            cls.TypeParser = TypeParser
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.ListType = ListType
            cls.DictType = DictType
            cls.SetType = SetType
            cls.TupleType = TupleType
            cls.FunctionType = FunctionType
            cls.FutureType = FutureType
            cls.GenericTypeInstance = GenericTypeInstance
            cls.ClassType = ClassType
            cls.InterfaceType = InterfaceType
            cls.EnumType = EnumType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_union_complex_nested(self):
        """复杂嵌套联合类型自动扁平化"""
        inner = self.UnionType([self.TYPE_NUMBER, self.UnionType([self.TYPE_STRING, self.TYPE_BOOLEAN])])
        self.assertEqual(len(inner.types), 3)

    def test_union_subtype_single(self):
        """单个类型是联合类型的子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING, self.TYPE_BOOLEAN])
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(t))
        self.assertTrue(self.TYPE_STRING.is_subtype_of(t))
        self.assertTrue(self.TYPE_BOOLEAN.is_subtype_of(t))

    def test_union_not_subtype(self):
        """不在联合中的类型不是子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertFalse(self.TYPE_BOOLEAN.is_subtype_of(t))
        self.assertFalse(self.TYPE_NULL.is_subtype_of(t))

    def test_union_subtype_union_all(self):
        """联合类型 A 是联合类型 B 的子类型（A 的所有成员都在 B 中）"""
        a = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        b = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING, self.TYPE_BOOLEAN])
        self.assertTrue(a.is_subtype_of(b))
        self.assertFalse(b.is_subtype_of(a))

    def test_union_subtype_any(self):
        """联合类型是 Any 的子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(t.is_subtype_of(self.TYPE_ANY))

    def test_union_subtype_unknown(self):
        """联合类型不是 Unknown 的子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        # Unknown.is_subtype_of 返回 True（渐进式类型），但反过来不成立
        # 这里测试联合类型对 Unknown 的 is_subtype_of
        result = t.is_subtype_of(self.TYPE_UNKNOWN)
        # UnknownType 不是联合类型，且 _type_id != ANY，所以返回 False
        self.assertFalse(result)

    def test_union_contains_type(self):
        """联合类型包含检查"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(t.contains_type(self.TYPE_NUMBER))
        self.assertTrue(t.contains_type(self.TYPE_STRING))
        self.assertFalse(t.contains_type(self.TYPE_BOOLEAN))
        self.assertFalse(t.contains_type(self.TYPE_NULL))

    def test_union_contains_type_var(self):
        """联合类型包含类型变量"""
        t = self.UnionType([self.TypeVar('T'), self.TYPE_STRING])
        self.assertTrue(t.contains_type(self.TypeVar('T')))
        self.assertFalse(t.contains_type(self.TypeVar('U')))

    def test_union_apply_substitution(self):
        """联合类型应用类型变量替换"""
        T = self.TypeVar('T')
        U = self.TypeVar('U')
        t = self.UnionType([T, U])
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER, 'U': self.TYPE_STRING})
        result = t.apply_substitution(subs)
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 2)
        self.assertEqual(str(result.types[0]), "数")
        self.assertEqual(str(result.types[1]), "串")

    def test_union_apply_substitution_partial(self):
        """联合类型部分替换"""
        T = self.TypeVar('T')
        t = self.UnionType([T, self.TYPE_STRING])
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        result = t.apply_substitution(subs)
        self.assertEqual(str(result.types[0]), "数")
        self.assertEqual(str(result.types[1]), "串")

    def test_union_collect_type_vars_empty(self):
        """无类型变量的联合类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        tvars = t.collect_type_vars()
        self.assertEqual(len(tvars), 0)

    def test_union_unify_both_union(self):
        """合一两个联合类型"""
        t1 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        t2 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同联合类型应能合一")

    def test_union_unify_with_type_var(self):
        """联合类型（含类型变量）与具体类型合一"""
        T = self.TypeVar('T')
        t = self.UnionType([T, self.TYPE_NUMBER])
        try:
            subs = self.unify(t, self.TYPE_NUMBER)
            # T 应绑定为 数
            self.assertIn('T', subs)
            self.assertEqual(str(subs['T']), "数")
        except self.UnificationError:
            self.fail("应能合一")

    def test_union_unify_type_with_union(self):
        """具体类型与联合类型合一"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        try:
            subs = self.unify(self.TYPE_NUMBER, t)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("数 与 数|串 应能合一")

    def test_union_unify_type_not_in_union(self):
        """不在联合中的类型合一失败"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        with self.assertRaises(self.UnificationError):
            self.unify(self.TYPE_BOOLEAN, t)

    def test_union_with_list(self):
        """联合类型包含列表"""
        list_num = self.ListType(self.TYPE_NUMBER)
        t = self.UnionType([list_num, self.TYPE_STRING])
        self.assertTrue(list_num.is_subtype_of(t))
        self.assertTrue(self.TYPE_STRING.is_subtype_of(t))
        self.assertFalse(self.TYPE_NUMBER.is_subtype_of(t))

    def test_union_optional_behavior(self):
        """联合类型中 数|空 等价于 OptionalType"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_NULL])
        opt = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        # 子类型双向检查
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(t))
        self.assertTrue(self.TYPE_NULL.is_subtype_of(t))
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(opt))
        self.assertTrue(self.TYPE_NULL.is_subtype_of(opt))

    def test_union_resolve_type_vars(self):
        """联合类型解析类型变量"""
        T = self.TypeVar('T')
        t = self.UnionType([T, self.TYPE_STRING])
        # resolve_type_vars 应返回自身（TypeVar 不解析）
        result = t.resolve_type_vars()
        self.assertIsInstance(result, self.UnionType)

    def test_union_with_function_type(self):
        """联合类型包含函数类型：(数)->串|数"""
        ft = self.FunctionType([self.TYPE_NUMBER], self.TYPE_STRING)
        t = self.UnionType([ft, self.TYPE_NUMBER])
        self.assertTrue(ft.is_subtype_of(t))
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(t))

    def test_union_parser_basic(self):
        """TypeParser 解析联合类型：数|串|布尔"""
        parser = self.TypeParser()
        result = parser.parse("数|串|布尔")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 3)

    def test_union_parser_with_list(self):
        """TypeParser 解析复杂联合：列表[数]|串"""
        parser = self.TypeParser()
        result = parser.parse("列表[数]|串")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 2)
        self.assertIsInstance(result.types[0], self.ListType)
        self.assertEqual(str(result.types[0].element_type), "数")
        self.assertEqual(str(result.types[1]), "串")

    def test_union_parser_optional(self):
        """TypeParser 解析可空类型：数|空 → OptionalType"""
        parser = self.TypeParser()
        result = parser.parse("数|空")
        self.assertIsInstance(result, self.OptionalTypeWrapper)
        self.assertEqual(str(result.inner_type), "数")

    def test_union_parser_three_types(self):
        """TypeParser 解析三成员联合：数|串|布尔"""
        parser = self.TypeParser()
        result = parser.parse("数|串|布尔")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 3)

    def test_union_subtype_identity(self):
        """联合类型自反子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(t.is_subtype_of(t))


# =============================================================================
# 第三部分：模式匹配测试
# =============================================================================

class TestPatternMatchingAdvanced(unittest.TestCase):
    """模式匹配高级测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                EnumType, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                TypeVar, TypeSubstitution, unify,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.EnumType = EnumType
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.unify = staticmethod(unify)
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_enum_empty_variants(self):
        """创建无字段枚举变体"""
        enum = self.EnumType(
            enum_name="颜色",
            variants={
                "红": [],
                "绿": [],
                "蓝": [],
            }
        )
        self.assertEqual(enum.enum_name, "颜色")
        self.assertTrue(enum.has_variant("红"))
        self.assertTrue(enum.has_variant("绿"))
        self.assertTrue(enum.has_variant("蓝"))

    def test_enum_with_fields(self):
        """创建带字段的枚举变体"""
        enum = self.EnumType(
            enum_name="结果",
            variants={
                "成功": [self.TYPE_NUMBER],
                "失败": [self.TYPE_STRING],
                "等待": [],
            }
        )
        self.assertTrue(enum.has_variant("成功"))
        fields = enum.get_variant_types("成功")
        self.assertIsNotNone(fields)
        self.assertEqual(len(fields), 1)
        self.assertEqual(str(fields[0]), "数")

    def test_enum_multiple_fields(self):
        """创建多字段枚举变体"""
        enum = self.EnumType(
            enum_name="事件",
            variants={
                "点击": [self.TYPE_NUMBER, self.TYPE_NUMBER],
                "按键": [self.TYPE_STRING],
                "关闭": [],
            }
        )
        fields = enum.get_variant_types("点击")
        self.assertEqual(len(fields), 2)
        self.assertEqual(str(fields[0]), "数")
        self.assertEqual(str(fields[1]), "数")

    def test_enum_exhaustive_all_matched(self):
        """枚举穷尽性检查：全部匹配"""
        enum = self.EnumType(
            enum_name="状态",
            variants={
                "开": [],
                "关": [],
            }
        )
        unmatched = enum._enum_exhaustive_variants({"开", "关"})
        self.assertIsNone(unmatched)

    def test_enum_exhaustive_missing_one(self):
        """枚举穷尽性检查：少匹配一个"""
        enum = self.EnumType(
            enum_name="颜色",
            variants={
                "红": [],
                "绿": [],
                "蓝": [],
            }
        )
        unmatched = enum._enum_exhaustive_variants({"红", "绿"})
        self.assertEqual(unmatched, "蓝")

    def test_enum_exhaustive_all_missing(self):
        """枚举穷尽性检查：全未匹配"""
        enum = self.EnumType(
            enum_name="方向",
            variants={
                "上": [],
                "下": [],
                "左": [],
                "右": [],
            }
        )
        unmatched = enum._enum_exhaustive_variants(set())
        self.assertEqual(unmatched, "上")

    def test_enum_generic_params(self):
        """枚举泛型参数"""
        enum = self.EnumType(
            enum_name="选项",
            variants={
                "有": [self.TypeVar('T')],
                "无": [],
            },
            generic_params=['T'],
        )
        self.assertEqual(enum.generic_params, ['T'])
        tvars = enum.collect_type_vars()
        self.assertEqual(len(tvars), 1)

    def test_enum_variant_not_found(self):
        """获取不存在的变体返回 None"""
        enum = self.EnumType(
            enum_name="状态",
            variants={
                "开": [],
                "关": [],
            }
        )
        self.assertIsNone(enum.get_variant_types("未知"))

    def test_union_type_narrowing(self):
        """联合类型类型缩小：数|串 → 检查类型是否在联合中"""
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(union))
        self.assertTrue(self.TYPE_STRING.is_subtype_of(union))
        self.assertFalse(self.TYPE_BOOLEAN.is_subtype_of(union))

    def test_union_type_narrowing_with_null(self):
        """联合类型包含空类型：数|空"""
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_NULL])
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(union))
        self.assertTrue(self.TYPE_NULL.is_subtype_of(union))
        self.assertFalse(self.TYPE_STRING.is_subtype_of(union))

    def test_union_type_narrowing_complex(self):
        """复杂联合类型类型缩小：列表[数]|串|布尔"""
        from type_system import ListType
        list_num = ListType(self.TYPE_NUMBER)
        union = self.UnionType([list_num, self.TYPE_STRING, self.TYPE_BOOLEAN])
        self.assertTrue(list_num.is_subtype_of(union))
        self.assertTrue(self.TYPE_STRING.is_subtype_of(union))
        self.assertTrue(self.TYPE_BOOLEAN.is_subtype_of(union))
        self.assertFalse(self.TYPE_NUMBER.is_subtype_of(union))


class TestMatchStatementInference(unittest.TestCase):
    """模式匹配语句类型推断测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                EnumType, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                TypeVar, TypeSubstitution, unify,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            from ast_nodes import (
                Module, SegmentDefinition, Parameter,
                VariableDeclaration, NumberLiteral, StringLiteral,
                BooleanLiteral, NullLiteral, Identifier,
                FunctionCall, ExpressionStatement, ReturnStatement,
                MatchStatement, MatchCase, MatchPattern,
            )
            cls.TypeInferencer = TypeInferencer
            cls.EnumType = EnumType
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.unify = staticmethod(unify)
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
            # AST 节点
            cls.Module = Module
            cls.SegmentDefinition = SegmentDefinition
            cls.Parameter = Parameter
            cls.VariableDeclaration = VariableDeclaration
            cls.NumberLiteral = NumberLiteral
            cls.StringLiteral = StringLiteral
            cls.BooleanLiteral = BooleanLiteral
            cls.NullLiteral = NullLiteral
            cls.Identifier = Identifier
            cls.FunctionCall = FunctionCall
            cls.ExpressionStatement = ExpressionStatement
            cls.ReturnStatement = ReturnStatement
            cls.MatchStatement = MatchStatement
            cls.MatchCase = MatchCase
            cls.MatchPattern = MatchPattern
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_match_statement_ast_creation(self):
        """创建模式匹配 AST 节点"""
        pattern = self.MatchPattern(kind='wildcard')
        case = self.MatchCase(
            pattern=pattern,
            body=[self.ExpressionStatement(
                expression=self.NumberLiteral(value=0)
            )],
        )
        match_stmt = self.MatchStatement(
            subject=self.Identifier(name='x'),
            cases=[case],
        )
        self.assertIsNotNone(match_stmt)
        self.assertEqual(len(match_stmt.cases), 1)
        self.assertEqual(match_stmt.cases[0].pattern.kind, 'wildcard')

    def test_match_statement_number_pattern(self):
        """模式匹配数字模式"""
        pattern = self.MatchPattern(kind='number', value=self.NumberLiteral(value=1))
        self.assertEqual(pattern.kind, 'number')
        self.assertIsNotNone(pattern.value)

    def test_match_statement_string_pattern(self):
        """模式匹配字符串模式"""
        pattern = self.MatchPattern(kind='string', value=self.StringLiteral(value='hello'))
        self.assertEqual(pattern.kind, 'string')

    def test_match_statement_variable_pattern(self):
        """模式匹配变量绑定模式"""
        pattern = self.MatchPattern(kind='variable', binding='value')
        self.assertEqual(pattern.kind, 'variable')
        self.assertEqual(pattern.binding, 'value')

    def test_match_statement_type_check_pattern(self):
        """模式匹配类型检查模式"""
        pattern = self.MatchPattern(kind='type_check', type_name='数', binding='n')
        self.assertEqual(pattern.kind, 'type_check')
        self.assertEqual(pattern.type_name, '数')
        self.assertEqual(pattern.binding, 'n')

    def test_match_statement_multiple_cases(self):
        """模式匹配多个分支"""
        cases = [
            self.MatchCase(
                pattern=self.MatchPattern(kind='number', value=self.NumberLiteral(value=1)),
                body=[self.ExpressionStatement(expression=self.StringLiteral(value='one'))],
            ),
            self.MatchCase(
                pattern=self.MatchPattern(kind='number', value=self.NumberLiteral(value=2)),
                body=[self.ExpressionStatement(expression=self.StringLiteral(value='two'))],
            ),
            self.MatchCase(
                pattern=self.MatchPattern(kind='wildcard'),
                body=[self.ExpressionStatement(expression=self.StringLiteral(value='other'))],
            ),
        ]
        match_stmt = self.MatchStatement(
            subject=self.Identifier(name='x'),
            cases=cases,
        )
        self.assertEqual(len(match_stmt.cases), 3)

    def test_match_statement_with_guard(self):
        """模式匹配带守卫条件"""
        case = self.MatchCase(
            pattern=self.MatchPattern(kind='variable', binding='n'),
            guard=self.FunctionCall(
                name=self.Identifier(name='是整数'),
                arguments=[self.Identifier(name='n')],
            ),
            body=[self.ExpressionStatement(expression=self.NumberLiteral(value=0))],
        )
        self.assertIsNotNone(case.guard)

    def test_enum_match_exhaustive_via_inferencer(self):
        """通过类型推断器验证枚举匹配穷尽性"""
        # 创建枚举类型
        enum = self.EnumType(
            enum_name="颜色",
            variants={
                "红": [],
                "绿": [],
                "蓝": [],
            }
        )
        # 验证穷尽性：匹配了红和绿，蓝未匹配
        unmatched = enum._enum_exhaustive_variants({"红", "绿"})
        self.assertEqual(unmatched, "蓝")
        # 全部匹配
        all_matched = enum._enum_exhaustive_variants({"红", "绿", "蓝"})
        self.assertIsNone(all_matched)


# =============================================================================
# 第四部分：端到端集成测试（解析 → 类型推断 → 代码生成）
# =============================================================================

class TestEndToEndGenerics(unittest.TestCase):
    """泛型端到端集成测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                FunctionType, TypeVar, TypeSubstitution,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            from ast_nodes import (
                Module, SegmentDefinition, Parameter,
                VariableDeclaration, NumberLiteral, StringLiteral,
                Identifier, BinaryOp, FunctionCall,
                ExpressionStatement, ReturnStatement,
            )
            cls.TypeInferencer = TypeInferencer
            cls.FunctionType = FunctionType
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
            # AST
            cls.Module = Module
            cls.SegmentDefinition = SegmentDefinition
            cls.Parameter = Parameter
            cls.VariableDeclaration = VariableDeclaration
            cls.NumberLiteral = NumberLiteral
            cls.StringLiteral = StringLiteral
            cls.Identifier = Identifier
            cls.BinaryOp = BinaryOp
            cls.FunctionCall = FunctionCall
            cls.ExpressionStatement = ExpressionStatement
            cls.ReturnStatement = ReturnStatement
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_generic_swap_pair(self):
        """泛型交换：段 swap(x, y) 返回 (y, x)  → 推断为 (T, U) -> (U, T)"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='swap',
                    parameters=[self.Parameter(name='x'), self.Parameter(name='y')],
                    body=[
                        self.ReturnStatement(
                            value=self.FunctionCall(
                                name=self.Identifier(name='建'),
                                arguments=[self.Identifier(name='y'), self.Identifier(name='x')],
                            ),
                        ),
                    ],
                ),
            ],
        )
        inf.infer(module)
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        sym = inf.symbol_table.lookup('swap')
        self.assertIsNotNone(sym)
        ft = sym.data_type
        self.assertIsInstance(ft, self.FunctionType)
        self.assertEqual(len(ft.param_types), 2)
        # 第一个参数类型应与第二个参数类型不同（泛型 T 和 U）
        self.assertNotEqual(str(ft.param_types[0]), str(ft.param_types[1]))

    def test_generic_apply_twice(self):
        """泛型函数两次调用得到不同具体类型"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='id',
                    parameters=[self.Parameter(name='x')],
                    body=[self.ReturnStatement(value=self.Identifier(name='x'))],
                ),
            ],
            statements=[
                self.VariableDeclaration(
                    name='a',
                    value=self.FunctionCall(
                        name=self.Identifier(name='id'),
                        arguments=[self.NumberLiteral(value=42)],
                    ),
                ),
                self.VariableDeclaration(
                    name='b',
                    value=self.FunctionCall(
                        name=self.Identifier(name='id'),
                        arguments=[self.StringLiteral(value='world')],
                    ),
                ),
            ],
        )
        inf.infer(module)
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        # 验证 a 是数，b 是串
        sym_a = inf.symbol_table.lookup('a')
        sym_b = inf.symbol_table.lookup('b')
        self.assertIsNotNone(sym_a)
        self.assertIsNotNone(sym_b)
        self.assertEqual(str(sym_a.data_type), "数")
        self.assertEqual(str(sym_b.data_type), "串")

    def test_generic_constant_function(self):
        """泛型常量函数：段 const(x, y) 返回 x  → 推断为 (T, U) -> T"""
        inf = self.TypeInferencer()
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='const',
                    parameters=[self.Parameter(name='x'), self.Parameter(name='y')],
                    body=[self.ReturnStatement(value=self.Identifier(name='x'))],
                ),
            ],
        )
        inf.infer(module)
        self.assertEqual(len(inf.errors), 0, f"推断错误: {inf.errors}")
        sym = inf.symbol_table.lookup('const')
        ft = sym.data_type
        # 返回类型 = 第一个参数类型
        self.assertEqual(str(ft.return_type), str(ft.param_types[0]))


class TestEndToEndUnions(unittest.TestCase):
    """联合类型端到端测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeParser, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                ListType, DictType, TypeVar,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.TypeParser = TypeParser
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.ListType = ListType
            cls.DictType = DictType
            cls.TypeVar = TypeVar
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_parse_union_function_type(self):
        """解析联合类型函数签名：(数|串) -> 布尔"""
        parser = self.TypeParser()
        result = parser.parse("(数|串) -> 布尔")
        from type_system import FunctionType
        self.assertIsInstance(result, FunctionType)
        self.assertEqual(len(result.param_types), 1)
        self.assertIsInstance(result.param_types[0], self.UnionType)
        self.assertEqual(str(result.return_type), "布尔")

    def test_parse_union_complex_generic(self):
        """解析复杂联合类型：列表[数]|字典[串, 数]"""
        parser = self.TypeParser()
        result = parser.parse("列表[数]|字典[串, 数]")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 2)
        self.assertIsInstance(result.types[0], self.ListType)
        self.assertIsInstance(result.types[1], self.DictType)

    def test_parse_union_three_way(self):
        """解析三成员联合：数|串|布尔"""
        parser = self.TypeParser()
        result = parser.parse("数|串|布尔")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 3)

    def test_parse_union_with_generic_instance(self):
        """解析联合类型中的泛型实例：列表[T]|空"""
        parser = self.TypeParser()
        result = parser.parse("列表[T]|空")
        # 列表[T]|空 只有两个成员，且包含空 → 可能转为 OptionalType
        self.assertIsInstance(result, (self.UnionType, self.OptionalTypeWrapper))

    def test_union_subtype_of_optional(self):
        """数|空 是 OptionalType(数) 的子类型"""
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_NULL])
        opt = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        self.assertTrue(union.is_subtype_of(opt))


class TestEndToEndPatternMatching(unittest.TestCase):
    """模式匹配端到端测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                EnumType, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                TypeVar, TypeSubstitution,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            from ast_nodes import (
                Module, SegmentDefinition, Parameter,
                VariableDeclaration, NumberLiteral, StringLiteral,
                BooleanLiteral, NullLiteral, Identifier,
                FunctionCall, ExpressionStatement, ReturnStatement,
                MatchStatement, MatchCase, MatchPattern,
            )
            cls.TypeInferencer = TypeInferencer
            cls.EnumType = EnumType
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.TypeVar = TypeVar
            cls.TypeSubstitution = TypeSubstitution
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
            cls.Module = Module
            cls.SegmentDefinition = SegmentDefinition
            cls.Parameter = Parameter
            cls.VariableDeclaration = VariableDeclaration
            cls.NumberLiteral = NumberLiteral
            cls.StringLiteral = StringLiteral
            cls.BooleanLiteral = BooleanLiteral
            cls.NullLiteral = NullLiteral
            cls.Identifier = Identifier
            cls.FunctionCall = FunctionCall
            cls.ExpressionStatement = ExpressionStatement
            cls.ReturnStatement = ReturnStatement
            cls.MatchStatement = MatchStatement
            cls.MatchCase = MatchCase
            cls.MatchPattern = MatchPattern
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_enum_match_in_function(self):
        """枚举匹配在函数中的类型推断"""
        inf = self.TypeInferencer()
        # 创建带匹配的段
        module = self.Module(
            segments=[
                self.SegmentDefinition(
                    name='测试',
                    parameters=[self.Parameter(name='x')],
                    body=[
                        self.ExpressionStatement(
                            expression=self.FunctionCall(
                                name=self.Identifier(name='打印'),
                                arguments=[self.Identifier(name='x')],
                            ),
                        ),
                    ],
                ),
            ],
            # 将枚举定义放入模块，由 infer 自动注册
            enums=[
                type('EnumDef', (), {
                    'name': '选项',
                    'variants': [
                        type('Variant', (), {'name': '是', 'fields': []}),
                        type('Variant', (), {'name': '否', 'fields': []}),
                    ],
                })(),
            ],
        )
        inf.infer(module)
        # 验证没有错误（枚举已注册）
        self.assertIn('选项', inf.enum_defs)

    def test_match_pattern_construction(self):
        """构建各种匹配模式"""
        patterns = [
            self.MatchPattern(kind='wildcard'),
            self.MatchPattern(kind='number', value=self.NumberLiteral(value=1)),
            self.MatchPattern(kind='string', value=self.StringLiteral(value='hello')),
            self.MatchPattern(kind='variable', binding='x'),
            self.MatchPattern(kind='type_check', type_name='数', binding='n'),
            self.MatchPattern(kind='bool', value=True),
            self.MatchPattern(kind='null'),
        ]
        for p in patterns:
            self.assertIsNotNone(p.kind)

    def test_match_case_with_multiple_body(self):
        """匹配分支包含多条语句"""
        case = self.MatchCase(
            pattern=self.MatchPattern(kind='wildcard'),
            body=[
                self.VariableDeclaration(
                    name='tmp',
                    value=self.NumberLiteral(value=0),
                ),
                self.ExpressionStatement(
                    expression=self.Identifier(name='tmp'),
                ),
            ],
        )
        self.assertEqual(len(case.body), 2)


# =============================================================================
# 第五部分：类型系统完整性测试
# =============================================================================

class TestTypeSystemIntegration(unittest.TestCase):
    """类型系统完整性测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                Type, TypeSubstitution, UnificationError, unify, TypeParser,
                NumberType, StringType, BooleanType, NullType,
                AnyType, UnknownType, TypeVar,
                UnionType, OptionalTypeWrapper,
                ListType, DictType, TupleType, SetType,
                FunctionType, FutureType,
                GenericTypeInstance, GenericTypeDef,
                ClassType, InterfaceType, EnumType,
                TypeSymbolTable, TypedSymbol,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN,
                TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            cls.Type = Type
            cls.TypeSubstitution = TypeSubstitution
            cls.UnificationError = UnificationError
            cls.unify = staticmethod(unify)
            cls.TypeParser = TypeParser
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.AnyType = AnyType
            cls.UnknownType = UnknownType
            cls.TypeVar = TypeVar
            cls.UnionType = UnionType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.ListType = ListType
            cls.DictType = DictType
            cls.TupleType = TupleType
            cls.SetType = SetType
            cls.FunctionType = FunctionType
            cls.FutureType = FutureType
            cls.GenericTypeInstance = GenericTypeInstance
            cls.GenericTypeDef = GenericTypeDef
            cls.ClassType = ClassType
            cls.InterfaceType = InterfaceType
            cls.EnumType = EnumType
            cls.TypeSymbolTable = TypeSymbolTable
            cls.TypedSymbol = TypedSymbol
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_substitution_clone_independence(self):
        """替换克隆的独立性"""
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        clone = subs.clone()
        clone.bind('U', self.TYPE_STRING)
        # 原替换不应包含 U
        self.assertNotIn('U', subs)
        # 克隆应包含 T 和 U
        self.assertIn('U', clone)
        self.assertIn('T', clone)

    def test_substitution_compose(self):
        """替换组合"""
        s1 = self.TypeSubstitution({'T': self.TypeVar('U')})
        s2 = self.TypeSubstitution({'U': self.TYPE_NUMBER})
        composed = s1.compose(s2)
        # T 应解析为 数（先应用 s2 将 U→数，再应用 s1 将 T→U）
        self.assertIn('T', composed)
        self.assertEqual(str(composed['T']), "数")
        self.assertIn('U', composed)

    def test_substitution_bool(self):
        """替换的布尔值"""
        empty = self.TypeSubstitution()
        self.assertFalse(empty)
        non_empty = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        self.assertTrue(non_empty)

    def test_type_parser_function_type(self):
        """解析函数类型：(数, 串) -> 布尔"""
        parser = self.TypeParser()
        result = parser.parse("(数, 串) -> 布尔")
        self.assertIsInstance(result, self.FunctionType)
        self.assertEqual(len(result.param_types), 2)
        self.assertEqual(str(result.param_types[0]), "数")
        self.assertEqual(str(result.param_types[1]), "串")
        self.assertEqual(str(result.return_type), "布尔")

    def test_type_parser_generic_type_var(self):
        """解析泛型类型变量：T"""
        parser = self.TypeParser()
        result = parser.parse("T")
        self.assertIsInstance(result, self.TypeVar)
        self.assertEqual(result.name, "T")

    def test_type_parser_generic_list_with_tvar(self):
        """解析泛型列表：列表[T]"""
        parser = self.TypeParser()
        result = parser.parse("列表[T]")
        self.assertIsInstance(result, self.ListType)
        self.assertIsInstance(result.element_type, self.TypeVar)
        self.assertEqual(result.element_type.name, "T")

    def test_type_parser_complex_nested(self):
        """解析嵌套泛型：列表[列表[数]]"""
        parser = self.TypeParser()
        result = parser.parse("列表[列表[数]]")
        self.assertIsInstance(result, self.ListType)
        self.assertIsInstance(result.element_type, self.ListType)
        self.assertEqual(str(result.element_type.element_type), "数")

    def test_type_parser_dict_with_tvar(self):
        """解析泛型字典：字典[K, V]"""
        parser = self.TypeParser()
        result = parser.parse("字典[K, V]")
        self.assertIsInstance(result, self.DictType)
        self.assertIsInstance(result.key_type, self.TypeVar)
        self.assertEqual(result.key_type.name, "K")
        self.assertIsInstance(result.value_type, self.TypeVar)
        self.assertEqual(result.value_type.name, "V")

    def test_type_parser_optional_wrapper(self):
        """解析可空类型包装：数|空"""
        parser = self.TypeParser()
        result = parser.parse("数|空")
        self.assertIsInstance(result, self.OptionalTypeWrapper)

    def test_type_parser_tuple(self):
        """解析元组类型：(数, 串, 布尔)"""
        parser = self.TypeParser()
        result = parser.parse("(数, 串, 布尔)")
        self.assertIsInstance(result, self.TupleType)
        self.assertEqual(len(result.element_types), 3)

    def test_type_symtable_scope(self):
        """符号表作用域管理"""
        table = self.TypeSymbolTable()
        table.define('x', 'variable', self.TYPE_NUMBER)
        self.assertIsNotNone(table.lookup('x'))
        table.enter_scope()
        table.define('y', 'variable', self.TYPE_STRING)
        self.assertIsNotNone(table.lookup('x'))  # 外层可见
        self.assertIsNotNone(table.lookup('y'))  # 内层可见
        table.exit_scope()
        self.assertIsNotNone(table.lookup('x'))  # 外层仍可见
        # 内层变量退出后不可见

    def test_type_symtable_generic_param(self):
        """符号表泛型参数管理"""
        table = self.TypeSymbolTable()
        table.define_generic_param('T', self.TYPE_NUMBER)
        resolved = table.resolve_type_param('T')
        self.assertIsNotNone(resolved)
        self.assertIsInstance(resolved, self.TypeVar)
        self.assertEqual(resolved.name, 'T')

    def test_type_symtable_global_index(self):
        """符号表全局索引"""
        table = self.TypeSymbolTable()
        table.define('add', 'function', self.FunctionType([self.TYPE_NUMBER, self.TYPE_NUMBER], self.TYPE_NUMBER))
        table.define('Person', 'class', self.ClassType('Person'))
        # 全局索引应包含两者
        self.assertIsNotNone(table.lookup('add'))
        self.assertIsNotNone(table.lookup('Person'))

    def test_unify_tuple(self):
        """合一元组类型"""
        t1 = self.TupleType([self.TYPE_NUMBER, self.TYPE_STRING])
        t2 = self.TupleType([self.TYPE_NUMBER, self.TYPE_STRING])
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同元组应能合一")

    def test_unify_tuple_mismatch_length(self):
        """合一不同长度的元组失败"""
        t1 = self.TupleType([self.TYPE_NUMBER, self.TYPE_STRING])
        t2 = self.TupleType([self.TYPE_NUMBER])
        with self.assertRaises(self.UnificationError):
            self.unify(t1, t2)

    def test_unify_function(self):
        """合一函数类型"""
        t1 = self.FunctionType([self.TYPE_NUMBER], self.TYPE_STRING)
        t2 = self.FunctionType([self.TYPE_NUMBER], self.TYPE_STRING)
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同函数类型应能合一")

    def test_unify_function_mismatch_params(self):
        """合一参数数量不同的函数类型失败"""
        t1 = self.FunctionType([self.TYPE_NUMBER, self.TYPE_STRING], self.TYPE_BOOLEAN)
        t2 = self.FunctionType([self.TYPE_NUMBER], self.TYPE_BOOLEAN)
        with self.assertRaises(self.UnificationError):
            self.unify(t1, t2)

    def test_unify_optional_same(self):
        """合一相同可空类型"""
        t1 = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        t2 = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同可空类型应能合一")

    def test_unify_future_same(self):
        """合一相同 Future 类型"""
        t1 = self.FutureType(self.TYPE_NUMBER)
        t2 = self.FutureType(self.TYPE_NUMBER)
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同 Future 类型应能合一")

    def test_unify_set_same(self):
        """合一相同集合类型"""
        t1 = self.SetType(self.TYPE_NUMBER)
        t2 = self.SetType(self.TYPE_NUMBER)
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同集合类型应能合一")

    def test_unify_class_same(self):
        """合一相同类类型"""
        t1 = self.ClassType('Person')
        t2 = self.ClassType('Person')
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同类类型应能合一")

    def test_unify_class_mismatch(self):
        """合一不同类类型失败"""
        t1 = self.ClassType('Person')
        t2 = self.ClassType('Animal')
        with self.assertRaises(self.UnificationError):
            self.unify(t1, t2)

    def test_unify_interface_same(self):
        """合一相同接口类型"""
        t1 = self.InterfaceType('可比较')
        t2 = self.InterfaceType('可比较')
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同接口类型应能合一")

    def test_unify_enum_same(self):
        """合一相同枚举类型"""
        t1 = self.EnumType(enum_name='颜色')
        t2 = self.EnumType(enum_name='颜色')
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("相同枚举类型应能合一")

    def test_unify_null_with_any(self):
        """空类型与任意类型合一"""
        subs = self.unify(self.TYPE_NULL, self.TYPE_ANY)
        self.assertIsNotNone(subs)

    def test_unify_null_with_optional(self):
        """空类型与可空类型合一"""
        opt = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        subs = self.unify(self.TYPE_NULL, opt)
        self.assertIsNotNone(subs)


# =============================================================================
# 第五部分：类型守卫与类型缩小测试
# =============================================================================

class TestTypeGuard(unittest.TestCase):
    """类型守卫测试（类型缩小在条件分支中的行为）"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                UnionType, NumberType, StringType, BooleanType, NullType,
                OptionalTypeWrapper, ListType, DictType,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
            )
            from ast_nodes import (
                Identifier, FunctionCall, IfStatement, ExpressionStatement,
                NumberLiteral, VariableDeclaration,
            )
            cls.TypeInferencer = TypeInferencer
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.ListType = ListType
            cls.DictType = DictType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
            cls.Identifier = Identifier
            cls.FunctionCall = FunctionCall
            cls.IfStatement = IfStatement
            cls.ExpressionStatement = ExpressionStatement
            cls.NumberLiteral = NumberLiteral
            cls.VariableDeclaration = VariableDeclaration
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def setUp(self):
        self.inf = self.TypeInferencer()

    def _make_guard_call(self, func_name: str, var_name: str):
        """构造类型守卫函数调用 AST 节点"""
        return self.FunctionCall(
            name=self.Identifier(name=func_name),
            arguments=[self.Identifier(name=var_name)],
        )

    def test_detect_type_guard_integer(self):
        """检测 是整数(x) 类型守卫"""
        inf = self.inf
        # 注册变量 x 为 数|串
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是整数', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result, "应能检测到类型守卫")
        var_name, then_type, else_type = result
        self.assertEqual(var_name, 'x')
        self.assertEqual(str(then_type), '数')
        # else 分支排除 数，剩下 串
        self.assertEqual(str(else_type), '串')

    def test_detect_type_guard_string(self):
        """检测 是字符串(x) 类型守卫"""
        inf = self.inf
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是字符串', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertEqual(var_name, 'x')
        self.assertEqual(str(then_type), '串')
        # else 分支应排除串，剩下 数
        self.assertEqual(str(else_type), '数')

    def test_detect_type_guard_boolean(self):
        """检测 是布尔(x) 类型守卫"""
        inf = self.inf
        union = self.UnionType([self.TYPE_BOOLEAN, self.TYPE_NUMBER])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是布尔', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertEqual(str(then_type), '布尔')
        self.assertEqual(str(else_type), '数')

    def test_detect_type_guard_list(self):
        """检测 是列表(x) 类型守卫"""
        inf = self.inf
        # 使用无元素类型的 ListType() 以匹配守卫中的 ListType()
        union = self.UnionType([
            self.ListType(),
            self.TYPE_STRING,
        ])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是列表', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertIsInstance(then_type, self.ListType)
        self.assertEqual(str(else_type), '串')

    def test_detect_type_guard_null(self):
        """检测 是空(x) 类型守卫"""
        inf = self.inf
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_NULL])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是空', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertEqual(str(then_type), '空')
        self.assertEqual(str(else_type), '数')

    def test_detect_type_guard_else_optional(self):
        """可空类型缩小：else 分支为 NullType"""
        inf = self.inf
        opt = self.OptionalTypeWrapper(self.TYPE_NUMBER)
        inf.symbol_table.define('x', 'variable', opt)

        guard_call = self._make_guard_call('是整数', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        # then 分支缩小为数，else 分支缩小为空
        self.assertEqual(str(then_type), '数')
        self.assertEqual(str(else_type), '空')

    def test_detect_type_guard_non_union(self):
        """非联合类型的类型守卫：then 分支缩小，else 分支保持原类型"""
        inf = self.inf
        inf.symbol_table.define('x', 'variable', self.TYPE_NUMBER)

        guard_call = self._make_guard_call('是整数', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertEqual(str(then_type), '数')
        self.assertEqual(str(else_type), '数')

    def test_detect_type_guard_not_a_guard_func(self):
        """非守卫函数调用不应触发类型守卫"""
        inf = self.inf
        inf.symbol_table.define('x', 'variable', self.TYPE_NUMBER)

        # 使用非守卫函数
        guard_call = self._make_guard_call('打印', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNone(result, "非守卫函数不应触发类型守卫")

    def test_detect_type_guard_not_a_call(self):
        """非函数调用表达式不应触发类型守卫"""
        inf = self.inf
        inf.symbol_table.define('x', 'variable', self.TYPE_NUMBER)

        # 使用标识符，不是函数调用
        result = inf._detect_type_guard(self.Identifier(name='x'))

        self.assertIsNone(result, "非函数调用不应触发类型守卫")

    def test_detect_type_guard_no_args(self):
        """无参数的类型守卫调用不应触发"""
        inf = self.inf
        inf.symbol_table.define('x', 'variable', self.TYPE_NUMBER)

        # 无参数的函数调用
        guard_call = self.FunctionCall(
            name=self.Identifier(name='是整数'),
            arguments=[],
        )
        result = inf._detect_type_guard(guard_call)

        self.assertIsNone(result, "无参数的类型守卫调用不应触发")

    def test_type_guard_float(self):
        """检测 是浮点(x) 类型守卫"""
        inf = self.inf
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        inf.symbol_table.define('x', 'variable', union)

        guard_call = self._make_guard_call('是浮点', 'x')
        result = inf._detect_type_guard(guard_call)

        self.assertIsNotNone(result)
        var_name, then_type, else_type = result
        self.assertEqual(str(then_type), '数')
        self.assertEqual(str(else_type), '串')

    def test_type_guard_if_statement_flow(self):
        """完整 if 语句类型守卫流程：then 分支中类型缩小"""
        inf = self.inf
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        inf.symbol_table.define('x', 'variable', union)

        # 构造: 如果 是整数(x) { 显示(x) } 否则 { 显示(x) }
        if_stmt = self.IfStatement(
            condition=self._make_guard_call('是整数', 'x'),
            then_body=[
                self.ExpressionStatement(
                    expression=self.Identifier(name='x')
                ),
            ],
            else_body=[
                self.ExpressionStatement(
                    expression=self.Identifier(name='x')
                ),
            ],
        )

        # 推断 if 语句
        inf._infer_if_stmt(if_stmt)

        # 退出 if 语句后，外层作用域中 x 应保持原类型
        symbol = inf.symbol_table.lookup('x')
        self.assertIsNotNone(symbol)
        self.assertIsInstance(symbol.data_type, self.UnionType)
        # 注意：由于 enter_scope/exit_scope，我们在外层无法直接验证 then 分支的类型
        # 但可以通过验证函数没有报错来确认流程正常
        self.assertEqual(len(inf.errors), 0, f"类型守卫流程不应产生错误: {inf.errors}")


# =============================================================================
# 第六部分：类型别名测试
# =============================================================================

class TestTypeAlias(unittest.TestCase):
    """类型别名测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                TypeParser, ListType, DictType, NumberType, StringType,
                OptionalTypeWrapper, UnionType,
                TYPE_NUMBER, TYPE_STRING,
            )
            from ast_nodes import (
                TypeAlias, Module,
            )
            cls.TypeInferencer = TypeInferencer
            cls.TypeParser = TypeParser
            cls.ListType = ListType
            cls.DictType = DictType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.UnionType = UnionType
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TypeAlias = TypeAlias
            cls.Module = Module
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def setUp(self):
        self.inf = self.TypeInferencer()

    def test_type_alias_ast_node(self):
        """TypeAlias AST 节点创建"""
        alias = self.TypeAlias(name='数字列表', target_type='列表[数]')
        self.assertEqual(alias.name, '数字列表')
        self.assertEqual(alias.target_type, '列表[数]')
        self.assertEqual(alias.generic_params, [])

    def test_type_alias_ast_node_with_generic_params(self):
        """TypeAlias AST 节点带泛型参数"""
        alias = self.TypeAlias(
            name='映射',
            target_type='字典[K, V]',
            generic_params=['K', 'V'],
        )
        self.assertEqual(alias.name, '映射')
        self.assertEqual(alias.target_type, '字典[K, V]')
        self.assertEqual(alias.generic_params, ['K', 'V'])

    def test_register_type_alias_via_module(self):
        """通过模块注册类型别名"""
        module = self.Module(name='test')
        module.type_aliases = [
            self.TypeAlias(name='数字列表', target_type='列表[数]'),
        ]
        self.inf._register_type_aliases(module)

        self.assertIn('数字列表', self.inf.type_aliases)
        self.assertEqual(self.inf.type_aliases['数字列表'], '列表[数]')

    def test_register_type_alias_via_statements(self):
        """通过模块语句注册类型别名"""
        module = self.Module(name='test')
        module.statements = [
            self.TypeAlias(name='数字列表', target_type='列表[数]'),
        ]
        self.inf._register_type_aliases(module)

        self.assertIn('数字列表', self.inf.type_aliases)
        self.assertEqual(self.inf.type_aliases['数字列表'], '列表[数]')

    def test_resolve_type_alias_direct(self):
        """直接解析类型别名引用"""
        self.inf.type_aliases['数字列表'] = '列表[数]'

        resolved = self.inf._resolve_type_alias('数字列表')
        self.assertEqual(resolved, '列表[数]')

    def test_resolve_type_alias_non_alias(self):
        """非别名的类型字符串保持不变"""
        resolved = self.inf._resolve_type_alias('数')
        self.assertEqual(resolved, '数')

        resolved = self.inf._resolve_type_alias('列表[数]')
        self.assertEqual(resolved, '列表[数]')

    def test_resolve_type_alias_recursive(self):
        """递归解析类型别名"""
        self.inf.type_aliases['数字列表'] = '数字列表内部'
        self.inf.type_aliases['数字列表内部'] = '列表[数]'

        resolved = self.inf._resolve_type_alias('数字列表')
        self.assertEqual(resolved, '列表[数]')

    def test_resolve_type_alias_chain(self):
        """多级类型别名链式解析"""
        self.inf.type_aliases['坐标'] = '点'
        self.inf.type_aliases['点'] = '元组[数, 数]'

        resolved = self.inf._resolve_type_alias('坐标')
        self.assertEqual(resolved, '元组[数, 数]')

    def test_resolve_type_alias_in_generic(self):
        """泛型参数中的类型别名解析"""
        self.inf.type_aliases['数字列表'] = '列表[数]'

        resolved = self.inf._resolve_type_alias('可选[数字列表]')
        self.assertEqual(resolved, '可选[列表[数]]')

    def test_type_alias_parse_type_string(self):
        """通过类型别名解析类型字符串"""
        self.inf.type_aliases['数字列表'] = '列表[数]'

        result = self.inf._parse_type_string('数字列表')
        self.assertIsInstance(result, self.ListType)
        self.assertEqual(str(result.element_type), '数')

    def test_type_alias_parse_nested_alias(self):
        """嵌套类型别名解析"""
        self.inf.type_aliases['数字列表'] = '列表[数]'
        self.inf.type_aliases['数字列表可选'] = '数字列表|空'

        result = self.inf._parse_type_string('数字列表可选')
        self.assertIsInstance(result, self.OptionalTypeWrapper)

    def test_type_alias_empty(self):
        """空类型字符串的别名解析"""
        resolved = self.inf._resolve_type_alias('')
        self.assertEqual(resolved, '')

        resolved = self.inf._resolve_type_alias(None)
        self.assertEqual(resolved, None)

    def test_type_alias_clear_on_register(self):
        """注册新模块时清空之前的别名"""
        # 先注册一些别名
        self.inf.type_aliases['旧别名'] = '数'

        # 注册新模块
        module = self.Module(name='test')
        module.type_aliases = [
            self.TypeAlias(name='新别名', target_type='串'),
        ]
        self.inf._register_type_aliases(module)

        # 旧别名应被清空
        self.assertNotIn('旧别名', self.inf.type_aliases)
        # 新别名应存在
        self.assertIn('新别名', self.inf.type_aliases)


if __name__ == '__main__':
    unittest.main(verbosity=2)