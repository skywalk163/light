# -*- coding: utf-8 -*-
"""
光明类型系统 v4.3 单元测试

测试泛型类型、联合类型、模式匹配等新特性
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestUnionType(unittest.TestCase):
    """联合类型测试（type_system.py 高级类型系统）"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeSubstitution, UnificationError, unify, TypeParser,
                UnionType, NumberType, StringType, BooleanType,
                NullType, AnyType, UnknownType, TypeVar,
                OptionalTypeWrapper, ListType, DictType,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL,
                TYPE_ANY, TYPE_UNKNOWN,
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
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
            cls.TYPE_ANY = TYPE_ANY
            cls.TYPE_UNKNOWN = TYPE_UNKNOWN
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_union_creation(self):
        """创建联合类型：整数|字符串"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertEqual(str(t), "数|串")

    def test_union_three_types(self):
        """创建联合类型：整数|字符串|布尔"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING, self.TYPE_BOOLEAN])
        self.assertEqual(str(t), "数|串|布尔")

    def test_union_auto_flatten(self):
        """联合类型自动扁平化"""
        inner = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        outer = self.UnionType([inner, self.TYPE_BOOLEAN])
        self.assertEqual(len(outer.types), 3)
        self.assertEqual(str(outer), "数|串|布尔")

    def test_union_subtype(self):
        """联合类型的子类型关系"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(t))
        self.assertTrue(self.TYPE_STRING.is_subtype_of(t))
        self.assertFalse(self.TYPE_BOOLEAN.is_subtype_of(t))

    def test_union_subtype_union(self):
        """联合类型之间的子类型关系"""
        t1 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        t2 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING, self.TYPE_BOOLEAN])
        self.assertTrue(t1.is_subtype_of(t2))
        self.assertFalse(t2.is_subtype_of(t1))

    def test_union_subtype_any(self):
        """联合类型是 Any 的子类型"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(t.is_subtype_of(self.TYPE_ANY))

    def test_union_collect_type_vars(self):
        """联合类型收集类型变量"""
        t = self.UnionType([self.TypeVar('T'), self.TypeVar('U')])
        tvars = t.collect_type_vars()
        self.assertEqual(len(tvars), 2)

    def test_union_apply_substitution(self):
        """联合类型应用替换"""
        t = self.UnionType([self.TypeVar('T'), self.TYPE_STRING])
        subs = self.TypeSubstitution({'T': self.TYPE_NUMBER})
        result = t.apply_substitution(subs)
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 2)
        self.assertEqual(str(result.types[0]), "数")
        self.assertEqual(str(result.types[1]), "串")

    def test_union_unify_same(self):
        """合一两个相同联合类型"""
        t1 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        t2 = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        try:
            subs = self.unify(t1, t2)
            self.assertIsNotNone(subs)
        except self.UnificationError:
            self.fail("应能合一")

    def test_union_unify_with_type_var(self):
        """联合类型与类型变量合一"""
        # T|数 与 数 合一：T 绑定为 数
        t = self.UnionType([self.TypeVar('T'), self.TYPE_NUMBER])
        actual = self.TYPE_NUMBER
        try:
            subs = self.unify(t, actual)
            # T 应被绑定为数
            self.assertIn('T', subs)
            self.assertEqual(str(subs['T']), "数")
        except self.UnificationError:
            self.fail("应能合一")

    def test_union_contains_type(self):
        """联合类型包含检查"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertTrue(t.contains_type(self.TYPE_NUMBER))
        self.assertTrue(t.contains_type(self.TYPE_STRING))
        self.assertFalse(t.contains_type(self.TYPE_BOOLEAN))

    def test_union_with_null_optional(self):
        """联合类型包含空类型时转为 OptionalType"""
        parser = self.TypeParser()
        # 使用 TypeParser 解析整数|空
        result = parser.parse("数|空")
        # 应该解析为 OptionalTypeWrapper
        self.assertIsInstance(result, self.OptionalTypeWrapper)
        self.assertEqual(str(result.inner_type), "数")


class TestTypeParserUnion(unittest.TestCase):
    """TypeParser 联合类型解析测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                TypeParser, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                ListType, DictType,
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
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_parse_union_basic(self):
        """解析基本联合类型：数|串"""
        parser = self.TypeParser()
        result = parser.parse("数|串")
        self.assertIsInstance(result, self.UnionType)

    def test_parse_union_three(self):
        """解析三成员联合类型：数|串|布尔"""
        parser = self.TypeParser()
        result = parser.parse("数|串|布尔")
        self.assertIsInstance(result, self.UnionType)
        self.assertEqual(len(result.types), 3)

    def test_parse_union_optional(self):
        """解析可空类型：数|空"""
        parser = self.TypeParser()
        result = parser.parse("数|空")
        self.assertIsInstance(result, self.OptionalTypeWrapper)

    def test_parse_union_complex(self):
        """解析复杂联合类型：列表[数]|串"""
        parser = self.TypeParser()
        result = parser.parse("列表[数]|串")
        self.assertIsInstance(result, self.UnionType)


class TestTypeCheckerGeneric(unittest.TestCase):
    """type_checker.py 泛型类型支持测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_checker import (
                parse_type_annotation, TypeVarType, GenericTypeInstance,
                ListType, DictType, PrimitiveType, AnyType,
                UnionType, OptionalType, FunctionType,
                TYPE_INT, TYPE_STRING, TYPE_BOOL, TYPE_NONE, TYPE_ANY,
            )
            cls.parse_type_annotation = staticmethod(parse_type_annotation)
            cls.TypeVarType = TypeVarType
            cls.GenericTypeInstance = GenericTypeInstance
            cls.ListType = ListType
            cls.DictType = DictType
            cls.PrimitiveType = PrimitiveType
            cls.AnyType = AnyType
            cls.UnionType = UnionType
            cls.OptionalType = OptionalType
            cls.FunctionType = FunctionType
            cls.TYPE_INT = TYPE_INT
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOL = TYPE_BOOL
            cls.TYPE_NONE = TYPE_NONE
            cls.TYPE_ANY = TYPE_ANY
        except ImportError as e:
            raise unittest.SkipTest(f"TypeChecker 模块不可用: {e}")

    def test_parse_type_var_T(self):
        """解析类型变量 T"""
        t = self.parse_type_annotation("T")
        self.assertIsInstance(t, self.TypeVarType)
        self.assertEqual(t.name, "T")

    def test_parse_type_var_K(self):
        """解析类型变量 K"""
        t = self.parse_type_annotation("K")
        self.assertIsInstance(t, self.TypeVarType)
        self.assertEqual(t.name, "K")

    def test_parse_type_var_Key(self):
        """解析类型变量 Key"""
        t = self.parse_type_annotation("Key")
        self.assertIsInstance(t, self.TypeVarType)
        self.assertEqual(t.name, "Key")

    def test_parse_generic_list_T(self):
        """解析泛型 列表<T>"""
        t = self.parse_type_annotation("列表<T>")
        self.assertIsInstance(t, self.ListType)
        self.assertIsInstance(t.element_type, self.TypeVarType)
        self.assertEqual(t.element_type.name, "T")

    def test_parse_generic_dict_KV(self):
        """解析泛型 字典<K, V>"""
        t = self.parse_type_annotation("字典<K, V>")
        self.assertIsInstance(t, self.DictType)
        self.assertIsInstance(t.key_type, self.TypeVarType)
        self.assertEqual(t.key_type.name, "K")
        self.assertIsInstance(t.value_type, self.TypeVarType)
        self.assertEqual(t.value_type.name, "V")

    def test_parse_list_concrete(self):
        """解析具体列表类型：列表<整数>"""
        t = self.parse_type_annotation("列表<整数>")
        self.assertIsInstance(t, self.ListType)

    def test_parse_dict_concrete(self):
        """解析具体字典类型：字典<字符串, 整数>"""
        t = self.parse_type_annotation("字典<字符串, 整数>")
        self.assertIsInstance(t, self.DictType)

    def test_parse_union_with_generic(self):
        """解析联合类型：整数|字符串"""
        t = self.parse_type_annotation("整数|字符串")
        self.assertIsInstance(t, self.UnionType)

    def test_generic_type_compatible_self(self):
        """泛型类型自兼容性"""
        t1 = self.parse_type_annotation("列表<T>")
        t2 = self.parse_type_annotation("列表<T>")
        self.assertTrue(t1.is_compatible(t2))

    def test_generic_type_compatible_concrete(self):
        """泛型类型与具体类型兼容"""
        t1 = self.parse_type_annotation("列表<T>")
        t2 = self.parse_type_annotation("列表<整数>")
        # T 应与任何类型兼容
        self.assertTrue(t1.is_compatible(t2))

    def test_type_var_compatible_any(self):
        """类型变量与任何类型兼容"""
        t = self.TypeVarType("T")
        self.assertTrue(t.is_compatible(self.TYPE_INT))
        self.assertTrue(t.is_compatible(self.TYPE_STRING))
        self.assertTrue(t.is_compatible(self.TYPE_ANY))


class TestPatternMatching(unittest.TestCase):
    """模式匹配增强测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            from type_system import (
                EnumType, UnionType, NumberType, StringType,
                BooleanType, NullType, OptionalTypeWrapper,
                TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL,
            )
            cls.TypeInferencer = TypeInferencer
            cls.EnumType = EnumType
            cls.UnionType = UnionType
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.OptionalTypeWrapper = OptionalTypeWrapper
            cls.TYPE_NUMBER = TYPE_NUMBER
            cls.TYPE_STRING = TYPE_STRING
            cls.TYPE_BOOLEAN = TYPE_BOOLEAN
            cls.TYPE_NULL = TYPE_NULL
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_enum_type_creation(self):
        """创建枚举类型并验证变体"""
        enum = self.EnumType(
            enum_name="选项",
            variants={
                "成功": [self.TYPE_NUMBER],
                "失败": [self.TYPE_STRING],
            }
        )
        self.assertEqual(enum.enum_name, "选项")
        self.assertTrue(enum.has_variant("成功"))
        self.assertTrue(enum.has_variant("失败"))
        self.assertFalse(enum.has_variant("未知"))

    def test_enum_variant_field_types(self):
        """获取枚举变体的字段类型"""
        enum = self.EnumType(
            enum_name="结果",
            variants={
                "数值": [self.TYPE_NUMBER, self.TYPE_STRING],
                "空": [],
            }
        )
        fields = enum.get_variant_types("数值")
        self.assertIsNotNone(fields)
        self.assertEqual(len(fields), 2)
        self.assertEqual(str(fields[0]), "数")
        self.assertEqual(str(fields[1]), "串")

        empty_fields = enum.get_variant_types("空")
        self.assertEqual(len(empty_fields), 0)

    def test_enum_exhaustive_check(self):
        """枚举穷尽性检查"""
        enum = self.EnumType(
            enum_name="颜色",
            variants={
                "红": [],
                "绿": [],
                "蓝": [],
            }
        )
        # 匹配了红和绿，蓝未匹配
        # 这里测试 EnumType 的 _enum_exhaustive_variants 方法
        unmatched = enum._enum_exhaustive_variants({"红", "绿"})
        self.assertEqual(unmatched, "蓝")

        # 全部匹配
        all_matched = enum._enum_exhaustive_variants({"红", "绿", "蓝"})
        self.assertIsNone(all_matched)

    def test_union_type_creation(self):
        """创建联合类型并验证"""
        t = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        self.assertEqual(len(t.types), 2)
        self.assertTrue(t.contains_type(self.TYPE_NUMBER))
        self.assertTrue(t.contains_type(self.TYPE_STRING))

    def test_type_narrowing_union(self):
        """联合类型类型缩小验证"""
        # 联合类型 数|串
        union = self.UnionType([self.TYPE_NUMBER, self.TYPE_STRING])
        # 数 是联合类型的子类型
        self.assertTrue(self.TYPE_NUMBER.is_subtype_of(union))
        # 布尔 不是联合类型的子类型
        self.assertFalse(self.TYPE_BOOLEAN.is_subtype_of(union))


if __name__ == '__main__':
    unittest.main()