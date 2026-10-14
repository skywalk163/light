"""R147-C：数学/JSON/随机 Tier1 纯 .light 对拍验证。

验证 stdlib 纯 .light 实现与 Python 参考实现语义一致：
  - 数学.light：绝对值/幂/平方根/正弦/余弦/对数/取整/组合数学
  - JSON核心.light：序列化/解析（递归下降）与 Python json 对拍
  - 随机.light：随机整数/随机浮点/随机选择（确定性核心验证）

Tier 2 缺口登记（需 native 原语，不动 src/）：
  - 数学：复数高阶运算（复数指数/对数/平方根/三角族）需 native complex 绑定
  - 数学：高精度运算（decimal 类）需新原语
  - JSON：builtins.py:452/462/468 内部级联（深层解析依赖的内部 builtin 解耦）
  - JSON：XML 互转（JSON转XML/XML转JSON）需 XML 解析器原语
"""
import json as _pyjson
import math as _pymath
import os
import sys
import unittest

_STDLIB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'stdlib')
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)

import _light_import_hook
_light_import_hook.install([_STDLIB])


class TestR147数学Tier1对拍(unittest.TestCase):
    """数学.light 关键函数与 Python math 模块对拍。"""

    @classmethod
    def setUpClass(cls):
        from 数学 import (
            绝对值, 幂, 平方根, 正弦, 余弦, 自然对数, 常用对数,
            向上取整, 向下取整, 四舍五入, 阶乘, 圆周率,
        )
        # 用 staticmethod 包装，避免 self.func() 自动绑定 self
        cls._绝对值 = staticmethod(绝对值)
        cls._幂 = staticmethod(幂)
        cls._平方根 = staticmethod(平方根)
        cls._正弦 = staticmethod(正弦)
        cls._余弦 = staticmethod(余弦)
        cls._自然对数 = staticmethod(自然对数)
        cls._常用对数 = staticmethod(常用对数)
        cls._向上取整 = staticmethod(向上取整)
        cls._向下取整 = staticmethod(向下取整)
        cls._四舍五入 = staticmethod(四舍五入)
        cls._阶乘 = staticmethod(阶乘)
        cls._圆周率 = staticmethod(圆周率)

    def test_绝对值(self):
        self.assertEqual(self._绝对值(-5), 5)
        self.assertEqual(self._绝对值(3), 3)
        self.assertAlmostEqual(self._绝对值(-3.14), 3.14, places=5)

    def test_幂(self):
        self.assertEqual(self._幂(2, 3), 8)
        self.assertAlmostEqual(self._幂(4, 0.5), 2.0, places=5)

    def test_平方根(self):
        self.assertAlmostEqual(self._平方根(16), 4.0, places=5)
        self.assertAlmostEqual(self._平方根(2), _pymath.sqrt(2), places=5)

    def test_正弦余弦(self):
        self.assertAlmostEqual(self._正弦(0), 0.0, places=5)
        self.assertAlmostEqual(self._余弦(0), 1.0, places=5)
        self.assertAlmostEqual(self._正弦(self._圆周率() / 6), 0.5, places=4)

    def test_对数族(self):
        self.assertAlmostEqual(self._自然对数(_pymath.e), 1.0, places=4)
        self.assertAlmostEqual(self._常用对数(100), 2.0, places=4)

    def test_取整族(self):
        self.assertEqual(self._向下取整(3.7), 3)
        self.assertEqual(self._向上取整(3.2), 4)
        self.assertEqual(self._四舍五入(3.7), 4)
        self.assertEqual(self._四舍五入(3.2), 3)

    def test_阶乘(self):
        self.assertEqual(self._阶乘(0), 1)
        self.assertEqual(self._阶乘(5), 120)
        self.assertEqual(self._阶乘(10), 3628800)


class TestR147_JSON_Tier1对拍(unittest.TestCase):
    """JSON核心.light 序列化/解析与 Python json 对拍。"""

    @classmethod
    def setUpClass(cls):
        from JSON核心 import 解析, 序列化, 序列化缩进
        cls._解析 = staticmethod(解析)
        cls._序列化 = staticmethod(序列化)
        cls._序列化缩进 = staticmethod(序列化缩进)

    def test_序列化字典(self):
        obj = {"名": "张三", "年龄": 30, "分数": 95.5}
        light_str = self._序列化(obj)
        py_str = _pyjson.dumps(obj, ensure_ascii=False, separators=(', ', ': '))
        self.assertEqual(self._解析(light_str), obj)
        self.assertEqual(self._解析(py_str), obj)

    def test_序列化列表(self):
        obj = [1, "two", 3.0, True, None, ["nested"]]
        light_str = self._序列化(obj)
        self.assertEqual(self._解析(light_str), obj)

    def test_序列化嵌套(self):
        obj = {"用户": [{"名": "A", "标签": ["x", "y"]}, {"名": "B", "标签": []}]}
        light_str = self._序列化(obj)
        self.assertEqual(self._解析(light_str), obj)

    def test_解析基本类型(self):
        self.assertEqual(self._解析('{"a": 1}'), {"a": 1})
        self.assertEqual(self._解析('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(self._解析('"hello"'), "hello")
        self.assertEqual(self._解析('42'), 42)
        self.assertEqual(self._解析('3.14'), 3.14)
        self.assertEqual(self._解析('true'), True)
        self.assertEqual(self._解析('false'), False)
        self.assertEqual(self._解析('null'), None)

    def test_序列化缩进(self):
        obj = {"a": 1, "b": [2, 3]}
        s = self._序列化缩进(obj, 2)
        self.assertIn('\n', s)
        self.assertEqual(self._解析(s), obj)

    def test_中文保原样(self):
        obj = {"问候": "你好世界", "列表": ["中文", "测试"]}
        s = self._序列化(obj)
        self.assertIn("你好世界", s)
        self.assertEqual(self._解析(s), obj)


class TestR147随机Tier1对拍(unittest.TestCase):
    """随机.light 关键函数行为验证（确定性核心）。"""

    @classmethod
    def setUpClass(cls):
        from 随机 import 随机整数, 随机浮点, 随机选择, 随机0到1
        cls._随机整数 = staticmethod(随机整数)
        cls._随机浮点 = staticmethod(随机浮点)
        cls._随机选择 = staticmethod(随机选择)
        cls._随机0到1 = staticmethod(随机0到1)

    def test_随机整数范围(self):
        for _ in range(100):
            n = self._随机整数(1, 10)
            self.assertTrue(1 <= n <= 10)

    def test_随机浮点范围(self):
        for _ in range(100):
            x = self._随机浮点(0.0, 1.0)
            self.assertTrue(0.0 <= x <= 1.0)

    def test_随机选择从列表(self):
        池 = ["甲", "乙", "丙"]
        for _ in range(50):
            x = self._随机选择(池)
            self.assertIn(x, 池)

    def test_随机0到1在区间内(self):
        for _ in range(50):
            x = self._随机0到1()
            self.assertTrue(0.0 <= x < 1.0)


if __name__ == '__main__':
    unittest.main()
