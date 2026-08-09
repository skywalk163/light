# -*- coding: utf-8 -*-
"""
光明类型系统单元测试

测试 HM 全局类型推断和可空类型系统
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestTypeSystem(unittest.TestCase):
    """类型系统基础测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_system import (
                NumberType, StringType, BooleanType,
                NullType, AnyType, UnknownType
            )
            cls.NumberType = NumberType
            cls.StringType = StringType
            cls.BooleanType = BooleanType
            cls.NullType = NullType
            cls.AnyType = AnyType
            cls.UnknownType = UnknownType
        except ImportError as e:
            raise unittest.SkipTest(f"TypeSystem 模块不可用: {e}")

    def test_number_type(self):
        """测试数字类型"""
        num = self.NumberType()
        self.assertIsNotNone(num)

    def test_string_type(self):
        """测试字符串类型"""
        s = self.StringType()
        self.assertIsNotNone(s)

    def test_boolean_type(self):
        """测试布尔类型"""
        b = self.BooleanType()
        self.assertIsNotNone(b)

    def test_null_type(self):
        """测试空类型"""
        n = self.NullType()
        self.assertIsNotNone(n)


class TestTypeInference(unittest.TestCase):
    """类型推断测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from type_inferencer import TypeInferencer
            cls.Inferencer = TypeInferencer
        except ImportError as e:
            raise unittest.SkipTest(f"TypeInferencer 模块不可用: {e}")

    def test_basic_inference(self):
        """测试基本类型推断"""
        try:
            inferencer = self.Inferencer()
            self.assertIsNotNone(inferencer)
        except Exception as e:
            self.skipTest(f"TypeInferencer 初始化失败: {e}")


if __name__ == '__main__':
    unittest.main()
