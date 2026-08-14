"""
lightpub P0 桥接模块测试 - 文件系统 + JSON + CSV + 正则表达式 + 日期时间 + 数学运算 + 加密

验证 7 个 P0 包通过 lightpub 加载器导入后功能真实可用（导入→调用→结果验证全链路）。
对应计划 3.1.2：修复 lightpub 桥接测试虚假通过，每个桥接包有 ≥3 个真实功能测试。
"""

import sys
import os
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))


class Test文件系统Bridge(unittest.TestCase):
    """测试 文件系统 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import 文件系统
        cls.mod = 文件系统

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_写入读取(self):
        tmp = tempfile.mktemp(suffix='.txt')
        try:
            self.mod.写入文件(tmp, '你好世界')
            self.assertEqual(self.mod.读取文件(tmp), '你好世界')
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_追加写入(self):
        tmp = tempfile.mktemp(suffix='.txt')
        try:
            self.mod.写入文件(tmp, '第一行')
            self.mod.追加写入(tmp, '第二行')
            self.assertEqual(self.mod.读取文件(tmp), '第一行第二行')
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_文件存在与大小(self):
        tmp = tempfile.mktemp(suffix='.txt')
        try:
            self.assertFalse(self.mod.文件是否存在(tmp))
            self.mod.写入文件(tmp, 'abc')
            self.assertTrue(self.mod.文件是否存在(tmp))
            self.assertEqual(self.mod.文件大小(tmp), 3)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_复制与删除(self):
        src = tempfile.mktemp(suffix='.txt')
        dst = tempfile.mktemp(suffix='.txt')
        try:
            self.mod.写入文件(src, '数据')
            self.mod.复制文件(src, dst)
            self.assertEqual(self.mod.读取文件(dst), '数据')
            self.mod.删除文件(dst)
            self.assertFalse(self.mod.文件是否存在(dst))
        finally:
            for p in (src, dst):
                if os.path.exists(p):
                    os.unlink(p)

    def test_列出目录(self):
        d = tempfile.mkdtemp()
        try:
            self.mod.写入文件(os.path.join(d, 'a.txt'), 'x')
            items = self.mod.列出目录(d)
            self.assertIn('a.txt', items)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_创建临时文件(self):
        tf = self.mod.创建临时文件()
        try:
            self.assertTrue(self.mod.文件是否存在(tf))
        finally:
            if os.path.exists(tf):
                os.unlink(tf)


class TestJSONBridge(unittest.TestCase):
    """测试 JSON 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import JSON
        cls.mod = JSON

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_解析与序列化往返(self):
        data = self.mod.解析JSON('{"a": 1, "b": [1, 2]}')
        self.assertEqual(data['a'], 1)
        self.assertEqual(data['b'], [1, 2])
        s = self.mod.序列化JSON(data)
        self.assertEqual(self.mod.解析JSON(s), data)

    def test_JSON压缩(self):
        self.assertEqual(self.mod.JSON压缩('{"a": 1}'), '{"a":1}')

    def test_JSON美化(self):
        pretty = self.mod.JSON美化({'a': 1})
        self.assertIn('\n', pretty)

    def test_JSON深度相等(self):
        self.assertTrue(self.mod.JSON深度相等({'a': 1}, {'a': 1}))
        self.assertFalse(self.mod.JSON深度相等({'a': 1}, {'a': 2}))

    def test_JSON指针获取(self):
        data = {'a': {'b': 42}}
        self.assertEqual(self.mod.JSON指针获取(data, '/a/b'), 42)

    def test_类型判定(self):
        self.assertTrue(self.mod.是JSON对象({'a': 1}))
        self.assertTrue(self.mod.是JSON数组([1, 2]))
        self.assertTrue(self.mod.是JSON数字(1))
        self.assertTrue(self.mod.是JSON字符串('x'))


class TestCSVBridge(unittest.TestCase):
    """测试 CSV 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import CSV
        cls.mod = CSV

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_解析CSV(self):
        data = self.mod.解析CSV('a,b\n1,2')
        self.assertEqual(data, [['a', 'b'], ['1', '2']])

    def test_序列化CSV(self):
        s = self.mod.序列化CSV([['a', 1], ['b', 2]])
        self.assertEqual(s, 'a,1\nb,2')

    def test_自动检测分隔符(self):
        delim = self.mod.自动检测分隔符('a\tb\tc')
        self.assertEqual(delim, '\t')

    def test_转字典列表(self):
        data = [['a', 'b'], ['1', '2']]
        rows = self.mod.转字典列表(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['a'], '1')
        self.assertEqual(rows[0]['b'], '2')

    def test_获取列(self):
        data = [['a', 'b'], ['1', '2'], ['3', '4']]
        col = self.mod.获取列(data, 0)
        self.assertEqual(col, ['a', '1', '3'])


class Test正则表达式Bridge(unittest.TestCase):
    """测试 正则表达式 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import 正则表达式
        cls.mod = 正则表达式

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_是否匹配(self):
        self.assertTrue(self.mod.是否匹配('^a', 'abc'))
        self.assertFalse(self.mod.是否匹配('^b', 'abc'))

    def test_替换(self):
        self.assertEqual(self.mod.替换(r'\d+', 'abc123def', '#'), 'abc#def')

    def test_搜索(self):
        m = self.mod.搜索(r'\d+', 'a12b3')
        self.assertTrue(m.匹配成功)
        self.assertEqual(m.整体匹配, '12')

    def test_分割(self):
        self.assertEqual(self.mod.分割(r',', 'a,b,c'), ['a', 'b', 'c'])

    def test_转义特殊字符(self):
        self.assertEqual(self.mod.转义特殊字符('a.b'), 'a\\.b')


class Test日期时间Bridge(unittest.TestCase):
    """测试 日期时间 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import 日期时间
        cls.mod = 日期时间

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_当前时间戳(self):
        self.assertGreater(self.mod.当前时间戳(), 0)

    def test_创建与格式化(self):
        dt = self.mod.创建日期时间(2024, 1, 15)
        self.assertEqual(self.mod.格式化时间(dt), '2024-01-15 00:00:00')

    def test_时间戳往返转换(self):
        ts = self.mod.当前时间戳()
        dt = self.mod.时间戳转日期时间(ts)
        # 浮点时间戳转换存在微秒级精度损失，允许 1ms 误差
        self.assertAlmostEqual(self.mod.日期时间转时间戳(dt), ts, delta=0.001)

    def test_闰年(self):
        self.assertTrue(self.mod.是闰年(2024))
        self.assertFalse(self.mod.是闰年(2023))

    def test_时间加天数(self):
        dt = self.mod.创建日期时间(2024, 1, 15)
        self.assertEqual(
            self.mod.格式化时间(self.mod.时间加天数(dt, 10)),
            '2024-01-25 00:00:00')

    def test_解析时间(self):
        dt = self.mod.解析时间('2024-01-15 00:00:00')
        self.assertEqual(self.mod.格式化时间(dt), '2024-01-15 00:00:00')


class Test数学运算Bridge(unittest.TestCase):
    """测试 数学运算 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import 数学运算
        cls.mod = 数学运算

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_平方根(self):
        self.assertEqual(self.mod.平方根(16), 4.0)

    def test_阶乘(self):
        self.assertEqual(self.mod.阶乘(5), 120)

    def test_最大公约数(self):
        self.assertEqual(self.mod.最大公约数(12, 18), 6)

    def test_最小公倍数(self):
        self.assertEqual(self.mod.最小公倍数(4, 6), 12)

    def test_求和与平均值(self):
        self.assertEqual(self.mod.求和([1, 2, 3]), 6)
        self.assertEqual(self.mod.平均值([1, 2, 3]), 2.0)

    def test_幂运算(self):
        self.assertEqual(self.mod.幂运算(2, 10), 1024)

    def test_取模(self):
        self.assertEqual(self.mod.取模(7, 3), 1)


class Test加密Bridge(unittest.TestCase):
    """测试 加密 桥接模块"""

    @classmethod
    def setUpClass(cls):
        from lightpub import 加密
        cls.mod = 加密

    def test_导入(self):
        self.assertIsNotNone(self.mod)

    def test_MD5哈希(self):
        self.assertEqual(
            self.mod.MD5哈希('abc'),
            '900150983cd24fb0d6963f7d28e17f72')

    def test_SHA256哈希(self):
        self.assertEqual(
            self.mod.SHA256哈希('abc'),
            'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_哈希字节(self):
        self.assertEqual(
            self.mod.哈希字节(b'hello'),
            self.mod.SHA256哈希('hello'))

    def test_字节与十六进制互转(self):
        self.assertEqual(self.mod.字节转十六进制(b'\x01\xff'), '01ff')
        self.assertEqual(self.mod.十六进制转字节('01ff'), b'\x01\xff')

    def test_创建HMAC(self):
        h = self.mod.HMAC哈希(b'key', b'data')
        self.assertTrue(len(h) > 0)
        self.assertEqual(h, self.mod.HMAC哈希(b'key', b'data'))

    def test_字节转Base64(self):
        self.assertEqual(self.mod.字节转Base64(b'hello'), 'aGVsbG8=')


if __name__ == '__main__':
    unittest.main(verbosity=2)
