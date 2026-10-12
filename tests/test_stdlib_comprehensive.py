# -*- coding: utf-8 -*-
"""
光明标准库 - 全面测试

测试所有标准库模块的基本功能，确保跨平台兼容性。
"""

import os
import sys
import unittest
from pathlib import Path

# 添加 stdlib 路径
stdlib_path = os.path.join(os.path.dirname(__file__), '..', 'stdlib')
sys.path.insert(0, stdlib_path)


class TestStdlibBase64(unittest.TestCase):
    """测试 Base64 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import Base64
            self.assertTrue(hasattr(Base64, 'Base64编码'))
        except ImportError:
            self.fail("Base64 模块导入失败")


class TestStdlibCSV(unittest.TestCase):
    """测试 CSV 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import CSV
            self.assertTrue(hasattr(CSV, 'CSV读取'))
        except ImportError:
            self.fail("CSV 模块导入失败")


class TestStdlibHTTP(unittest.TestCase):
    """测试 HTTP 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import HTTP
            self.assertTrue(hasattr(HTTP, 'HTTP获取'))
        except ImportError:
            self.fail("HTTP 模块导入失败")


class TestStdlib网络(unittest.TestCase):
    """测试 网络 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 网络
            self.assertTrue(hasattr(网络, 'URL解析'))
        except ImportError:
            self.fail("网络 模块导入失败")


class TestStdlib颜色(unittest.TestCase):
    """测试 颜色 模块（纯光明 .light 实现，R142-B 起不再依赖同名 .py）

    R142-B oracle 改造：原用例 `import 颜色` 直引 stdlib/颜色.py 做存在性断言；
    颜色.py 已按三腿对拍证据删除（原生腿 == 钩子腿 == .py oracle == colorsys 语义，
    0.82 逐行一致），改为经 _light_import_hook 加载 颜色.light（src 后端执行）。
    下方期望值取自 0.82 三腿对拍的一致输出，不是照抄 .py 输出。
    """

    def test_导入与对拍(self):
        """import 颜色 必须解析到 颜色.light，且关键导出值与内联期望一致。"""
        import _light_import_hook
        _light_import_hook.install([os.path.abspath(stdlib_path)])
        saved = sys.modules.pop('颜色', None)
        try:
            import 颜色
            源 = str(getattr(颜色, '__file__', '')).replace('\\', '/')
            self.assertTrue(源.endswith('/颜色.light'),
                            'import 颜色 应解析到 颜色.light（纯光明实现），实际 %s' % 源)
            self.assertEqual(list(颜色.RGB解析('#FF0000')), [255, 0, 0])
            self.assertEqual(list(颜色.RGB解析('#F00')), [255, 0, 0])
            self.assertEqual(list(颜色.RGB解析('rgb(10, 20, 30)')), [10, 20, 30])
            self.assertEqual(list(颜色.RGB解析('10,20,30')), [10, 20, 30])
            self.assertEqual(颜色.RGB转十六进制(255, 0, 0), '#FF0000')
            self.assertEqual(颜色.RGB转十六进制(16, 32, 255), '#1020FF')
            self.assertEqual(list(颜色.十六进制转RGB('#00FF00')), [0, 255, 0])
            self.assertEqual(颜色.颜色混合('#FF0000', '#0000FF', 0.5), '#7F007F')
            self.assertAlmostEqual(颜色.颜色亮度('#FF0000'), 0.299, places=4)
            self.assertEqual(颜色.颜色反转('#FF0000'), '#00FFFF')
            self.assertEqual(颜色.颜色变亮('#000000', 0.2), '#333333')
            self.assertEqual(颜色.颜色变暗('#FFFFFF', 0.2), '#CCCCCC')
            self.assertEqual(颜色.颜色透明('#FF0000', 0.5), 'rgba(255, 0, 0, 0.5)')
            self.assertEqual(颜色.获取颜色名称('#FF0000'), '红色')
            self.assertEqual(颜色.获取颜色名称('#123456'), '未知')
            self.assertEqual(list(颜色.RGB转HSV(255, 0, 0)), [0, 100, 100])
            self.assertEqual(list(颜色.HSV转RGB(0, 100, 100)), [255, 0, 0])
            self.assertEqual(list(颜色.RGB转HSL(255, 0, 0)), [0, 100, 50])
            self.assertEqual(list(颜色.HSL转RGB(0, 100, 50)), [255, 0, 0])
        finally:
            if saved is not None:
                sys.modules['颜色'] = saved
            else:
                sys.modules.pop('颜色', None)


class TestStdlib进程(unittest.TestCase):
    """测试 进程 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 进程
            self.assertTrue(hasattr(进程, '当前进程PID'))
        except ImportError:
            self.fail("进程 模块导入失败")


class TestStdlib环境(unittest.TestCase):
    """测试 环境 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 环境
            self.assertTrue(hasattr(环境, '获取环境变量'))
        except ImportError:
            self.fail("环境 模块导入失败")


class TestStdlib信号(unittest.TestCase):
    """测试 信号 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 信号
            self.assertTrue(hasattr(信号, '注册信号处理器'))
        except ImportError:
            self.fail("信号 模块导入失败")


class TestStdlib线程(unittest.TestCase):
    """测试 线程 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 线程
            self.assertTrue(hasattr(线程, '创建线程'))
        except ImportError:
            self.fail("线程 模块导入失败")


class TestStdlib测试(unittest.TestCase):
    """测试 测试 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 测试
            self.assertTrue(hasattr(测试, '测试用例'))
        except ImportError:
            self.fail("测试 模块导入失败")


class TestStdlib性能(unittest.TestCase):
    """测试 性能 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 性能
            self.assertTrue(hasattr(性能, '计时器'))
        except ImportError:
            self.fail("性能 模块导入失败")


class TestStdlib日志(unittest.TestCase):
    """测试 日志 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 日志
            self.assertTrue(hasattr(日志, '日志记录'))
        except ImportError:
            self.fail("日志 模块导入失败")


class TestStdlib配置(unittest.TestCase):
    """测试 配置 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 配置
            self.assertTrue(hasattr(配置, '读取配置'))
        except ImportError:
            self.fail("配置 模块导入失败")


class TestStdlib统计(unittest.TestCase):
    """测试 统计 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 统计
            self.assertTrue(hasattr(统计, '均值'))
        except ImportError:
            self.fail("统计 模块导入失败")


class TestStdlib随机(unittest.TestCase):
    """测试 随机 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 随机
            self.assertTrue(hasattr(随机, '随机整数'))
        except ImportError:
            self.fail("随机 模块导入失败")


class TestStdlib复数(unittest.TestCase):
    """测试 复数 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 复数
            self.assertTrue(hasattr(复数, '创建复数'))
        except ImportError:
            self.fail("复数 模块导入失败")


class TestStdlib向量(unittest.TestCase):
    """测试 向量 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 向量
            self.assertTrue(hasattr(向量, '创建向量'))
        except ImportError:
            self.fail("向量 模块导入失败")


class TestStdlib排序(unittest.TestCase):
    """测试 排序 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 排序
            self.assertTrue(hasattr(排序, '快速排序'))
        except ImportError:
            self.fail("排序 模块导入失败")


class TestStdlib分词(unittest.TestCase):
    """测试 分词 模块"""

    def test_import(self):
        """测试模块可导入"""
        try:
            import 分词
            self.assertTrue(hasattr(分词, '分词'))
        except ImportError:
            self.fail("分词 模块导入失败")


class TestStdlib格式化(unittest.TestCase):
    """测试 格式化 模块（纯光明 .light 实现，R142-B 起不再依赖同名 .py）

    R142-B oracle 改造：原用例 `import 格式化` 直引 stdlib/格式化.py 做存在性断言；
    格式化.py 已按三腿对拍证据删除（原生腿 == 钩子腿 == .py oracle，0.82 逐行一致），
    改为经 _light_import_hook 加载 格式化.light（src 后端执行）。
    下方期望值取自本地三腿对拍一致输出（钩子腿=.light 真实输出 == .py oracle），
    不是照抄 .py 输出。
    """

    def test_导入与对拍(self):
        """import 格式化 必须解析到 格式化.light，且关键导出值与内联期望一致。"""
        import _light_import_hook
        _light_import_hook.install([os.path.abspath(stdlib_path)])
        saved = sys.modules.pop('格式化', None)
        try:
            import 格式化
            源 = str(getattr(格式化, '__file__', '')).replace('\\', '/')
            self.assertTrue(源.endswith('/格式化.light'),
                            'import 格式化 应解析到 格式化.light（纯光明实现），实际 %s' % 源)
            self.assertEqual(格式化.文本左对齐("hi", 5, "."), 'hi...')
            self.assertEqual(格式化.文本居中("hi", 8), '   hi   ')
            self.assertEqual(格式化.文本右对齐("hi", 5, "0"), '000hi')
            self.assertEqual(格式化.文本填充("x", 4, "*", "右"), '***x')
            self.assertEqual(格式化.文本填充("x", 4, "*", "左"), 'x***')
            self.assertEqual(格式化.文本填充零(42, 5), '00042')
            self.assertEqual(格式化.文本填充零(7, 2), '07')
            self.assertEqual(格式化.文本缩进("a\nb", 2, ">"), '>>a\n>>b')
            self.assertEqual(格式化.文本去除缩进("    a\n    b"), 'a\nb')
            self.assertEqual(格式化.文本去除缩进("  x\n    y"), 'x\n  y')
            换行们 = 格式化.文本换行("The quick brown fox", 10)
            self.assertEqual(len(换行们), 2)
            self.assertEqual(换行们[0], 'The quick')
            self.assertEqual(换行们[1], 'brown fox')
            self.assertEqual(格式化.文本截断("hello world", 8), 'hello...')
            self.assertEqual(格式化.文本截断("hi", 8), 'hi')
            self.assertEqual(格式化.文本分隔线("=", 6), '======')
            self.assertEqual(格式化.文本表格([["甲", "1"], ["乙乙", "22"]], ["名", "值"]),
                             '名  | 值 \n-- | --\n甲  | 1 \n乙乙 | 22')
            self.assertEqual(格式化.文本去除空白("  a\nb   c "), 'a b c')
            self.assertEqual(格式化.文本填充段落("The quick brown fox", 10),
                             'The quick\nbrown fox')
        finally:
            if saved is not None:
                sys.modules['格式化'] = saved
            else:
                sys.modules.pop('格式化', None)


class TestStdlib模板(unittest.TestCase):
    """测试 模板 模块（纯光明 .light 实现，R143-B 起不再依赖同名 .py）

    R143-B oracle 改造：原用例 `import 模板` 直引 stdlib/模板.py 做存在性断言；
    模板.py 已按三腿对拍证据删除（原生腿 == 钩子腿 == .py oracle，逐行一致），
    改为经 _light_import_hook 加载 模板.light（src 后端执行）。
    下方期望值取自本地三腿对拍一致输出，不是照抄 .py 输出。
    """

    def test_导入与对拍(self):
        """import 模板 必须解析到 模板.light，且关键导出值与内联期望一致。"""
        import _light_import_hook
        _light_import_hook.install([os.path.abspath(stdlib_path)])
        saved = sys.modules.pop('模板', None)
        try:
            import 模板
            源 = str(getattr(模板, '__file__', '')).replace('\\', '/')
            self.assertTrue(源.endswith('/模板.light'),
                            'import 模板 应解析到 模板.light（纯光明实现），实际 %s' % 源)
            数据们 = [{"名": "甲", "年": 20}, {"名": "乙", "年": 30}]
            self.assertEqual(模板.模板循环("[{{item.名}}={{item.年}}]", 数据们),
                             '[甲=20][乙=30]')
            self.assertEqual(模板.模板循环("[{{item}}]", ["x", "y"]), '[x][y]')
            # 空 dict 项点号路径无值保留占位符（.py oracle 同语义，不做递归展开）
            self.assertEqual(模板.模板循环("[{{item.名}}]", [{}]), '[{{item.名}}]')
            # 嵌套 dict：`.py` oracle 只做顶层键包替换，`{{item.信息.名}}` 不递归展开
            self.assertEqual(
                模板.模板循环("{{item.信息.名}}", [{"信息": {"名": "甲"}}]),
                '{{item.信息.名}}')
            self.assertEqual(模板.模板变量替换("A{{x}}B", {"x": "Y"}), 'AYB')
            self.assertEqual(模板.模板条件("v={{v}}", True, {"v": 1}, {"v": 2}), 'v=1')
            self.assertEqual(模板.模板条件("v={{v}}", False, {"v": 1}, {"v": 2}), 'v=2')
            self.assertEqual(模板.渲染模板("hi {{n}}", {"n": "L"}), 'hi L')
        finally:
            if saved is not None:
                sys.modules['模板'] = saved
            else:
                sys.modules.pop('模板', None)


class TestStdlibAllModules(unittest.TestCase):
    """测试所有模块通过 __init__.py 统一导入"""

    def test_stdlib_init(self):
        """测试标准库 __init__ 导入"""
        try:
            import stdlib
            # 验证关键函数存在
            self.assertTrue(hasattr(stdlib, 'Base64编码'))
            self.assertTrue(hasattr(stdlib, '当前进程PID'))
            self.assertTrue(hasattr(stdlib, '快速排序'))
        except ImportError as e:
            self.fail(f"stdlib 导入失败: {e}")


class TestStdlibCrossPlatform(unittest.TestCase):
    """跨平台标准库功能测试"""

    def test_environment(self):
        """测试环境变量操作"""
        import 环境
        # 获取 PATH 环境变量
        path = 环境.获取环境变量('PATH')
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 0)

    def test_process_pid(self):
        """测试进程 PID 获取"""
        import 进程
        pid = 进程.当前进程PID()
        self.assertGreater(pid, 0)

    def test_random(self):
        """测试随机数生成"""
        import 随机
        r1 = 随机.随机整数(1, 100)
        self.assertGreaterEqual(r1, 1)
        self.assertLessEqual(r1, 100)


if __name__ == '__main__':
    unittest.main()