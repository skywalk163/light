"""
单元测试框架 — lightpub 桥接模块

基于 Python unittest 库封装，函数名对齐上游 duanpub（段言时期）packages/单元测试框架/源.duan。

上游 duanpub 原始包通过 C FFI 实现自研测试框架，
本桥接模块用 Python unittest 模块替代，提供等价的测试功能。
函数签名与上游 duanpub（段言时期）包保持一致。
"""

import unittest as _unittest
import unittest.mock as _mock
import time as _time
import functools as _functools
import io as _io
import sys as _sys
import types as _types


# =============================================================================
# 测试用例定义
# =============================================================================

class 测试用例:
    """测试用例基类，模拟 unittest.TestCase"""

    def __init__(self, 名称=""):
        self.名称 = 名称
        self._结果 = []
        self._通过 = True

    def 断言等于(self, 预期, 实际, 消息=""):
        """断言两个值相等"""
        try:
            self._通过 = True
            _unittest.TestCase().assertEqual(预期, 实际, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言不等于(self, 预期, 实际, 消息=""):
        """断言两个值不相等"""
        try:
            _unittest.TestCase().assertNotEqual(预期, 实际, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言真(self, 表达式, 消息=""):
        """断言表达式为真"""
        try:
            _unittest.TestCase().assertTrue(表达式, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言假(self, 表达式, 消息=""):
        """断言表达式为假"""
        try:
            _unittest.TestCase().assertFalse(表达式, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言大于(self, a, b, 消息=""):
        """断言 a > b"""
        try:
            _unittest.TestCase().assertGreater(a, b, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言大于等于(self, a, b, 消息=""):
        """断言 a >= b"""
        try:
            _unittest.TestCase().assertGreaterEqual(a, b, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言小于(self, a, b, 消息=""):
        """断言 a < b"""
        try:
            _unittest.TestCase().assertLess(a, b, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言小于等于(self, a, b, 消息=""):
        """断言 a <= b"""
        try:
            _unittest.TestCase().assertLessEqual(a, b, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言包含(self, 容器, 元素, 消息=""):
        """断言容器包含元素"""
        try:
            _unittest.TestCase().assertIn(元素, 容器, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言不包含(self, 容器, 元素, 消息=""):
        """断言容器不包含元素"""
        try:
            _unittest.TestCase().assertNotIn(元素, 容器, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言为None(self, 值, 消息=""):
        """断言值为 None"""
        try:
            _unittest.TestCase().assertIsNone(值, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言不为None(self, 值, 消息=""):
        """断言值不为 None"""
        try:
            _unittest.TestCase().assertIsNotNone(值, 消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise

    def 断言抛出(self, 异常类型, 可调用对象, *参数, **关键字参数):
        """断言调用抛出指定异常"""
        try:
            可调用对象(*参数, **关键字参数)
            self._通过 = False
            msg = "期望抛出异常 " + str(异常类型) + "，但未抛出任何异常"
            self._结果.append(msg)
            raise AssertionError(msg)
        except 异常类型:
            pass
        except AssertionError:
            raise
        except Exception as e:
            self._通过 = False
            msg = "期望抛出异常 " + str(异常类型) + "，但实际抛出了 " + type(e).__name__
            self._结果.append(msg)
            raise AssertionError(msg)

    def 断言几乎相等(self, 预期, 实际, 位数=7, 消息=""):
        """断言浮点数近似相等"""
        try:
            _unittest.TestCase().assertAlmostEqual(预期, 实际, places=位数, msg=消息)
        except AssertionError as e:
            self._通过 = False
            self._结果.append(str(e))
            raise


# =============================================================================
# 测试套件
# =============================================================================

def 创建测试套件():
    """创建测试套件"""
    return _unittest.TestSuite()


def 添加测试用例(套件, 测试用例):
    """向套件添加测试用例"""
    if isinstance(测试用例, type) and issubclass(测试用例, _unittest.TestCase):
        套件.addTest(_unittest.makeSuite(测试用例))
    elif isinstance(测试用例, _unittest.TestCase):
        套件.addTest(测试用例)
    elif isinstance(测试用例, _unittest.TestSuite):
        套件.addTests(测试用例)
    else:
        raise Exception("添加测试用例失败: 不支持的测试用例类型 " + str(type(测试用例)))


def 运行测试套件(套件):
    """运行测试套件，返回 测试结果 对象"""
    结果 = 测试结果()
    try:
        运行器 = _unittest.TextTestRunner(stream=_io.StringIO(), verbosity=0)
        unittest_结果 = 运行器.run(套件)
        结果.总用例数 = unittest_结果.testsRun
        结果.失败数 = len(unittest_结果.failures)
        结果.错误数 = len(unittest_结果.errors)
        结果.通过数 = 结果.总用例数 - 结果.失败数 - 结果.错误数
        for 测试, 回溯 in unittest_结果.failures:
            结果.失败详情.append({"测试": str(测试), "消息": 回溯})
        for 测试, 回溯 in unittest_结果.errors:
            结果.错误详情.append({"测试": str(测试), "消息": 回溯})
    except Exception as e:
        结果.错误详情.append({"测试": "套件运行", "消息": str(e)})
        结果.错误数 += 1
    return 结果


# =============================================================================
# 测试运行器
# =============================================================================

def 创建测试运行器(详细=True):
    """创建测试运行器"""
    verbosity = 2 if 详细 else 1
    return _unittest.TextTestRunner(verbosity=verbosity)


def 运行测试(测试用例类, 详细=True):
    """运行单个测试用例类中的所有测试方法，返回 测试结果 对象"""
    结果 = 测试结果()
    try:
        if isinstance(测试用例类, type):
            套件 = _unittest.TestLoader().loadTestsFromTestCase(测试用例类)
        else:
            套件 = _unittest.TestLoader().loadTestsFromTestCase(测试用例类.__class__)
        运行器 = _unittest.TextTestRunner(stream=_io.StringIO(), verbosity=2 if 详细 else 1)
        unittest_结果 = 运行器.run(套件)
        结果.总用例数 = unittest_结果.testsRun
        结果.失败数 = len(unittest_结果.failures)
        结果.错误数 = len(unittest_结果.errors)
        结果.通过数 = 结果.总用例数 - 结果.失败数 - 结果.错误数
        for 测试, 回溯 in unittest_结果.failures:
            结果.失败详情.append({"测试": str(测试), "消息": 回溯})
        for 测试, 回溯 in unittest_结果.errors:
            结果.错误详情.append({"测试": str(测试), "消息": 回溯})
    except Exception as e:
        结果.错误详情.append({"测试": str(测试用例类), "消息": str(e)})
        结果.错误数 += 1
    return 结果


def 运行所有测试(测试用例列表, 详细=True):
    """运行多个测试用例，返回 测试结果 对象"""
    总结果 = 测试结果()
    for 测试类 in 测试用例列表:
        子结果 = 运行测试(测试类, 详细=详细)
        总结果.总用例数 += 子结果.总用例数
        总结果.通过数 += 子结果.通过数
        总结果.失败数 += 子结果.失败数
        总结果.错误数 += 子结果.错误数
        总结果.失败详情.extend(子结果.失败详情)
        总结果.错误详情.extend(子结果.错误详情)
    return 总结果


def 发现测试(路径=".", 模式="*测试*.py"):
    """自动发现测试，返回测试套件"""
    try:
        加载器 = _unittest.TestLoader()
        套件 = 加载器.discover(路径, pattern=模式)
        return 套件
    except Exception as e:
        raise Exception("发现测试失败: " + str(e))


# =============================================================================
# 测试结果
# =============================================================================

class 测试结果:
    """测试结果"""

    def __init__(self):
        self.总用例数 = 0
        self.通过数 = 0
        self.失败数 = 0
        self.错误数 = 0
        self.失败详情 = []
        self.错误详情 = []

    def 是否全部通过(self):
        """检查是否所有测试通过"""
        return self.失败数 == 0 and self.错误数 == 0

    def 获取摘要(self):
        """获取测试结果摘要文本"""
        if self.是否全部通过():
            return "全部通过: {0} 个测试用例".format(self.总用例数)
        return "通过 {0}/{1}，失败 {2}，错误 {3}".format(
            self.通过数, self.总用例数, self.失败数, self.错误数)

    def 获取报告(self):
        """获取完整测试报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("测试报告")
        lines.append("=" * 60)
        lines.append("总用例数: {0}".format(self.总用例数))
        lines.append("通过数:   {0}".format(self.通过数))
        lines.append("失败数:   {0}".format(self.失败数))
        lines.append("错误数:   {0}".format(self.错误数))
        lines.append("结果:     {0}".format("通过" if self.是否全部通过() else "失败"))
        lines.append("")
        if self.失败详情:
            lines.append("-" * 60)
            lines.append("失败详情:")
            for i, 详情 in enumerate(self.失败详情, 1):
                lines.append("  [{0}] {1}".format(i, 详情.get("测试", "")))
                lines.append("       {0}".format(详情.get("消息", "")))
        if self.错误详情:
            lines.append("-" * 60)
            lines.append("错误详情:")
            for i, 详情 in enumerate(self.错误详情, 1):
                lines.append("  [{0}] {1}".format(i, 详情.get("测试", "")))
                lines.append("       {0}".format(详情.get("消息", "")))
        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# Mock 支持
# =============================================================================

def 创建Mock(规格=None, 名称=None):
    """创建 Mock 对象"""
    return _mock.Mock(spec=规格, name=名称)


class _修补上下文:
    """修补上下文管理器"""

    def __init__(self, 目标, 新值=None):
        self.目标 = 目标
        self.新值 = 新值
        self._patcher = None

    def __enter__(self):
        if self.新值 is not None:
            self._patcher = _mock.patch(self.目标, self.新值)
        else:
            self._patcher = _mock.patch(self.目标)
        return self._patcher.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._patcher is not None:
            return self._patcher.__exit__(exc_type, exc_val, exc_tb)
        return False


def 修补(目标, 新值=None):
    """临时修补对象（上下文管理器）"""
    return _修补上下文(目标, 新值)


class _间谍对象:
    """Spy 对象，记录调用但不改变行为"""

    def __init__(self, 目标):
        self.目标 = 目标
        self.调用记录 = []

    def __getattr__(self, 名称):
        原始方法 = getattr(self.目标, 名称)

        def 记录调用(*args, **kwargs):
            self.调用记录.append({"方法": 名称, "参数": args, "关键字参数": kwargs})
            return 原始方法(*args, **kwargs)

        return 记录调用


def 间谍(目标):
    """创建 Spy 对象，记录调用但不改变行为"""
    return _间谍对象(目标)


# =============================================================================
# 参数化测试
# =============================================================================

def 参数化(参数列表):
    """参数化测试装饰器

    用法:
        @参数化([(1, 2), (3, 4)])
        def 测试加法(self, a, b):
            ...
    """
    def 装饰器(测试函数):
        @_functools.wraps(测试函数)
        def 包装器(self, *args, **kwargs):
            for 参数组 in 参数列表:
                if isinstance(参数组, dict):
                    测试函数(self, **参数组)
                else:
                    测试函数(self, *参数组)
        return 包装器
    return 装饰器


# =============================================================================
# 基准测试
# =============================================================================

def 基准测试(函数, 迭代次数=1000):
    """运行基准测试，返回每次调用的平均耗时（秒）"""
    if not callable(函数):
        raise Exception("基准测试失败: 参数不是可调用对象")
    try:
        开始 = _time.perf_counter()
        for _ in range(迭代次数):
            函数()
        结束 = _time.perf_counter()
        总耗时 = 结束 - 开始
        平均耗时 = 总耗时 / 迭代次数
        return 平均耗时
    except Exception as e:
        raise Exception("基准测试失败: " + str(e))


def 测量执行时间(函数, *参数, **关键字参数):
    """测量函数执行时间（秒）"""
    if not callable(函数):
        raise Exception("测量执行时间失败: 参数不是可调用对象")
    try:
        开始 = _time.perf_counter()
        结果 = 函数(*参数, **关键字参数)
        结束 = _time.perf_counter()
        耗时 = 结束 - 开始
        return {"耗时": 耗时, "结果": 结果}
    except Exception as e:
        raise Exception("测量执行时间失败: " + str(e))