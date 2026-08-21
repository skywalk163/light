"""
光明标准库完整测试用例

测试所有标准库模块的功能
"""

import os
import sys
import tempfile
import unittest
import importlib.util

stdlib_path = os.path.join(os.path.dirname(__file__), '..', 'stdlib')
sys.path.insert(0, stdlib_path)

import importlib
import builtins as python_builtins

spec = importlib.util.spec_from_file_location('light_builtins', os.path.join(stdlib_path, 'builtins.py'))
light_builtins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(light_builtins)


class TestBuiltins(unittest.TestCase):
    """测试内置函数"""

    def test_string_tools(self):
        """测试字符串工具函数"""
        s = 'Hello World'
        self.assertTrue(light_builtins.开头(s, 'Hello'))
        self.assertTrue(light_builtins.结尾(s, 'World'))
        self.assertTrue(light_builtins.字符串包含(s, 'lo'))
        self.assertEqual(light_builtins.查找子串(s, 'World'), 6)
        self.assertEqual(light_builtins.替换字符串次数('aaa', 'a', 'b', 2), 'bba')
        self.assertEqual(light_builtins.截取到末尾(s, 6), 'World')
        self.assertEqual(light_builtins.字符串计数('aaa', 'a'), 3)
        self.assertEqual(light_builtins.字符串重复('ab', 3), 'ababab')
        self.assertEqual(light_builtins.字符串反转(s), 'dlroW olleH')
        self.assertEqual(light_builtins.转标题('hello world'), 'Hello World')
        self.assertEqual(light_builtins.去除左侧空白('  abc'), 'abc')
        self.assertEqual(light_builtins.去除右侧空白('abc  '), 'abc')

    def test_string_alignment(self):
        """测试字符串对齐函数"""
        s = 'abc'
        self.assertEqual(light_builtins.字符串对齐居中(s, 7), '  abc  ')
        self.assertEqual(light_builtins.字符串对齐左(s, 7), 'abc    ')
        self.assertEqual(light_builtins.字符串对齐右(s, 7), '    abc')


class TestMath(unittest.TestCase):
    """测试数学模块"""

    def test_hyperbolic(self):
        """测试双曲函数"""
        from 数学 import 双曲正弦, 双曲余弦, 双曲正切
        from 数学 import 反双曲正弦, 反双曲余弦, 反双曲正切
        
        self.assertAlmostEqual(双曲正弦(0), 0)
        self.assertAlmostEqual(双曲余弦(0), 1)
        self.assertAlmostEqual(双曲正切(0), 0)

    def test_inverse_trig(self):
        """测试反三角函数"""
        from 数学 import 反正弦, 反余弦, 反正切
        
        self.assertAlmostEqual(反正弦(0), 0)
        self.assertAlmostEqual(反余弦(1), 0)
        self.assertAlmostEqual(反正切(0), 0)

    def test_complex(self):
        """测试复数运算"""
        from 数学 import 复数实部, 复数虚部, 复数模, 复数共轭
        
        z = complex(3, 4)
        self.assertEqual(复数实部(z), 3)
        self.assertEqual(复数虚部(z), 4)
        self.assertEqual(复数模(z), 5)
        self.assertEqual(复数共轭(z), complex(3, -4))

    def test_combinatorics(self):
        """测试组合数学"""
        from 数学 import 排列, 组合, 双阶乘
        
        self.assertEqual(排列(5, 2), 20)
        self.assertEqual(组合(5, 2), 10)
        self.assertEqual(双阶乘(5), 15)

    def test_constants(self):
        """测试数学常量"""
        from 数学 import 圆周率, 自然常数, 黄金比例
        
        self.assertAlmostEqual(圆周率(), 3.14159, places=4)
        self.assertAlmostEqual(自然常数(), 2.71828, places=4)
        self.assertAlmostEqual(黄金比例(), 1.61803, places=4)


class TestStringProcessing(unittest.TestCase):
    """测试字符串处理模块"""

    def test_formatting(self):
        """测试字符串格式化"""
        from 字符串处理 import 格式化, 格式化字典, 格式化为百分比
        
        self.assertEqual(格式化('Hello {}', 'World'), 'Hello World')
        self.assertEqual(格式化字典('Hello {name}', name='World'), 'Hello World')
        self.assertEqual(格式化为百分比(0.5), '50.00%')

    def test_encoding(self):
        """测试编码解码"""
        from 字符串处理 import Base64编码, Base64解码, URL编码, URL解码
        
        s = 'hello'
        encoded = Base64编码(s)
        self.assertEqual(Base64解码(encoded), s)
        
        url_encoded = URL编码('hello world')
        self.assertEqual(URL解码(url_encoded), 'hello world')

    def test_validation(self):
        """测试字符串验证"""
        from 字符串处理 import 是否字母, 是否数字, 是否空白
        
        self.assertTrue(是否字母('abc'))
        self.assertTrue(是否数字('123'))
        self.assertTrue(是否空白('   '))


class TestFileSystem(unittest.TestCase):
    """测试文件系统模块"""

    def setUp(self):
        """设置临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_file_operations(self):
        """测试文件操作"""
        from 文件系统 import 读取文件, 写入文件, 文件存在, 删除文件
        from 文件系统 import 文件大小, 创建临时文件, 删除临时文件
        
        test_file = os.path.join(self.temp_dir, 'test.txt')
        写入文件(test_file, 'hello')
        self.assertTrue(文件存在(test_file))
        self.assertEqual(读取文件(test_file), 'hello')
        self.assertEqual(文件大小(test_file), 5)
        删除文件(test_file)
        self.assertFalse(文件存在(test_file))

    def test_directory_operations(self):
        """测试目录操作"""
        from 文件系统 import 创建目录, 目录存在, 删除目录, 遍历目录
        
        test_dir = os.path.join(self.temp_dir, 'subdir')
        创建目录(test_dir)
        self.assertTrue(目录存在(test_dir))
        
        file1 = os.path.join(test_dir, 'file1.txt')
        file2 = os.path.join(test_dir, 'file2.txt')
        with open(file1, 'w') as f:
            f.write('1')
        with open(file2, 'w') as f:
            f.write('2')
        
        files = 遍历目录(test_dir)
        self.assertEqual(len(files), 2)

    def test_path_operations(self):
        """测试路径操作"""
        from 文件系统 import 路径连接, 绝对路径, 规范化路径, 获取文件名
        
        path = 路径连接('a', 'b', 'c.txt')
        self.assertEqual(获取文件名(path), 'c.txt')


class TestLogging(unittest.TestCase):
    """测试日志模块"""

    def test_basic_logging(self):
        """测试基本日志功能"""
        from 日志 import 调试, 信息, 警告, 错误, 致命
        from 日志 import 设置级别, 获取级别, 启用控制台输出
        
        设置级别('调试')
        self.assertEqual(获取级别(), '调试')
        
        调试('调试消息')
        信息('信息消息')
        警告('警告消息')
        错误('错误消息')
        致命('致命消息')

    def test_log_rotation(self):
        """测试日志轮转"""
        from 日志 import 设置日志轮转
        import os
        
        # 修复：固定文件名会在多 agent 并行时撞车，改用 mkstemp 唯一名
        import tempfile
        fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='_taskC_logrot_')
        os.close(fd)
        
        try:
            with open(temp_file, 'w') as f:
                f.write('test')
            设置日志轮转(temp_file, 最大大小=100, 备份数量=2)
            self.assertTrue(os.path.exists(temp_file))
        finally:
            import time
            time.sleep(0.1)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def test_context_logging(self):
        """测试上下文日志"""
        from 日志 import 信息上下文
        
        信息上下文('测试', 用户='test', 操作='login')


class TestJSON(unittest.TestCase):
    """测试JSON模块"""

    def test_json_basic(self):
        """测试基本JSON操作"""
        from JSON import 解析JSON, 序列化JSON, 美化JSON
        
        data = {'name': '光明', 'version': 1}
        json_str = 序列化JSON(data)
        parsed = 解析JSON(json_str)
        self.assertEqual(parsed, data)
        
        pretty = 美化JSON(data)
        self.assertIn('\n', pretty)

    def test_json_validation(self):
        """测试JSON验证"""
        from JSON import 验证JSON
        
        self.assertTrue(验证JSON('{"a": 1}'))
        self.assertFalse(验证JSON('{"a": 1'))

    def test_json_schema(self):
        """测试JSON Schema验证"""
        from JSON import JSONSchema验证
        
        schema = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
        self.assertTrue(JSONSchema验证({'name': '光明'}, schema))
        self.assertFalse(JSONSchema验证({'name': 123}, schema))

    def test_json_merge(self):
        """测试JSON合并"""
        from JSON import JSON合并, JSON深合并
        
        base = {'a': 1, 'b': {'c': 2}}
        other = {'a': 10, 'b': {'d': 3}}
        
        merged = JSON合并(base, other)
        self.assertEqual(merged['a'], 10)
        
        deep_merged = JSON深合并(base, other)
        self.assertEqual(deep_merged['b']['c'], 2)
        self.assertEqual(deep_merged['b']['d'], 3)

    def test_json_extract(self):
        """测试JSON提取值"""
        from JSON import JSON提取值
        
        data = {'a': {'b': {'c': 1}}}
        self.assertEqual(JSON提取值(data, 'a.b.c'), 1)
        self.assertEqual(JSON提取值(data, 'a.x', 0), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)