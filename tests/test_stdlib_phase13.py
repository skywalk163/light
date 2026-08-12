"""
第十三阶段测试用例 - 补全标准库
"""
import sys
sys.path.insert(0, 'c:/traework/light/stdlib')

import unittest
import os
import tempfile


class 测试临时文件模块(unittest.TestCase):
    """测试临时文件模块"""
    
    def test_创建临时文件路径(self):
        from 临时文件 import 创建临时文件路径
        路径 = 创建临时文件路径(后缀='.txt')
        self.assertTrue(os.path.exists(路径))
        self.assertTrue(路径.endswith('.txt'))
        os.remove(路径)
    
    def test_创建临时目录(self):
        from 临时文件 import 创建临时目录
        目录 = 创建临时目录(前缀='test_')
        self.assertTrue(os.path.isdir(目录))
        self.assertIn('test_', os.path.basename(目录))
        os.rmdir(目录)
    
    def test_获取临时目录(self):
        from 临时文件 import 获取临时目录
        目录 = 获取临时目录()
        self.assertTrue(os.path.isdir(目录))
    
    def test_获取临时目录前缀(self):
        from 临时文件 import 获取临时目录前缀
        前缀 = 获取临时目录前缀()
        self.assertIsInstance(前缀, str)
    
    def test_临时文件上下文(self):
        from 临时文件 import 临时文件
        with 临时文件(后缀='.tmp') as 路径:
            self.assertTrue(os.path.exists(路径))
            with open(路径, 'w') as f:
                f.write('test')
        self.assertFalse(os.path.exists(路径))
    
    def test_临时目录上下文(self):
        from 临时文件 import 临时目录
        with 临时目录() as 目录:
            self.assertTrue(os.path.isdir(目录))
            文件路径 = os.path.join(目录, 'test.txt')
            with open(文件路径, 'w') as f:
                f.write('test')
            self.assertTrue(os.path.exists(文件路径))
        self.assertFalse(os.path.exists(目录))
    
    def test_安全文件名(self):
        from 临时文件 import 安全文件名
        self.assertEqual(安全文件名('test.txt'), 'test.txt')
        self.assertNotIn('/', 安全文件名('a/b/c.txt'))
        self.assertNotIn('\\', 安全文件名('a\\b\\c.txt'))


class 测试系统接口模块(unittest.TestCase):
    """测试系统接口模块"""
    
    def test_获取环境变量(self):
        from 系统接口 import 获取环境变量, 设置环境变量
        设置环境变量('TEST_VAR', 'hello')
        self.assertEqual(获取环境变量('TEST_VAR'), 'hello')
        self.assertIsNone(获取环境变量('NONEXISTENT_VAR_12345'))
    
    def test_环境变量存在(self):
        from 系统接口 import 环境变量存在, 设置环境变量
        设置环境变量('TEST_EXIST', 'yes')
        self.assertTrue(环境变量存在('TEST_EXIST'))
        self.assertFalse(环境变量存在('NONEXISTENT_VAR_99999'))
    
    def test_当前工作目录(self):
        from 系统接口 import 当前工作目录
        目录 = 当前工作目录()
        self.assertTrue(os.path.isdir(目录))
    
    def test_连接路径(self):
        from 系统接口 import 连接路径
        路径 = 连接路径('a', 'b', 'c.txt')
        self.assertIn('a', 路径)
        self.assertIn('b', 路径)
        self.assertIn('c.txt', 路径)
    
    def test_取文件名(self):
        from 系统接口 import 取文件名
        self.assertEqual(取文件名('/a/b/c.txt'), 'c.txt')
    
    def test_进程ID(self):
        from 系统接口 import 进程ID
        pid = 进程ID()
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)
    
    def test_获取命令行参数(self):
        from 系统接口 import 获取命令行参数
        args = 获取命令行参数()
        self.assertIsInstance(args, list)
    
    def test_操作系统(self):
        from 系统接口 import 操作系统
        os_name = 操作系统()
        self.assertIsInstance(os_name, str)
        self.assertIn(os_name, ['Windows', 'Linux', 'Darwin', 'FreeBSD'])
    
    def test_CPU核心数(self):
        from 系统接口 import CPU核心数
        cores = CPU核心数()
        self.assertIsInstance(cores, int)
        self.assertGreater(cores, 0)
    
    def test_路径分隔符(self):
        from 系统接口 import 路径分隔符
        sep = 路径分隔符()
        self.assertIn(sep, ['/', '\\'])


class 测试外部命令模块(unittest.TestCase):
    """测试外部命令模块"""
    
    def test_执行命令(self):
        from 外部命令 import 执行命令
        结果 = 执行命令('echo hello')
        self.assertIsInstance(结果.返回码, int)
    
    def test_执行命令并获取输出(self):
        from 外部命令 import 执行命令并获取输出
        输出 = 执行命令并获取输出('echo test_output')
        self.assertIn('test_output', 输出)
    
    def test_命令是否成功(self):
        from 外部命令 import 命令是否成功
        self.assertTrue(命令是否成功('echo test'))
    
    def test_管道执行(self):
        from 外部命令 import 管道执行
        import platform
        if platform.system() == 'Windows':
            结果 = 管道执行(['echo line1', 'findstr line'])
        else:
            结果 = 管道执行(['echo line1', 'grep line'])
        self.assertIsInstance(结果.返回码, int)
    
    def test_命令存在(self):
        from 外部命令 import 命令存在
        import platform
        if platform.system() == 'Windows':
            self.assertTrue(命令存在('cmd'))
        else:
            self.assertTrue(命令存在('echo'))


class 测试参数解析模块(unittest.TestCase):
    """测试参数解析模块"""
    
    def test_简单解析(self):
        from 参数解析 import 参数解析器
        解析器 = 参数解析器(描述='测试程序')
        解析器.添加位置参数('文件', 描述='输入文件')
        解析器.添加参数('--输出', 短名称='-o', 描述='输出文件')
        结果 = 解析器.解析(['input.txt', '-o', 'output.txt'])
        self.assertEqual(结果['文件'], 'input.txt')
        self.assertEqual(结果['输出'], 'output.txt')
    
    def test_标志参数(self):
        from 参数解析 import 参数解析器
        解析器 = 参数解析器()
        解析器.添加参数('--verbose', 短名称='-v', 标志=True, 描述='详细输出')
        结果 = 解析器.解析(['-v'])
        self.assertTrue(结果['verbose'])
    
    def test_默认值(self):
        from 参数解析 import 参数解析器
        解析器 = 参数解析器()
        解析器.添加参数('--count', 类型=int, 默认值=10, 描述='数量')
        结果 = 解析器.解析([])
        self.assertEqual(结果['count'], 10)
    
    def test_帮助文本(self):
        from 参数解析 import 参数解析器
        解析器 = 参数解析器(描述='测试')
        解析器.添加位置参数('文件')
        帮助 = 解析器.帮助文本()
        self.assertIn('测试', 帮助)
    
    def test_简单解析函数(self):
        from 参数解析 import 简单解析
        定义 = [
            {'名称': '文件', '描述': '输入文件'},
            {'名称': '--输出', '短名称': '-o', '描述': '输出文件'},
        ]
        结果 = 简单解析(定义, ['data.txt', '-o', 'out.txt'])
        self.assertEqual(结果['文件'], 'data.txt')
        self.assertEqual(结果['输出'], 'out.txt')


class 测试美化输出模块(unittest.TestCase):
    """测试美化输出模块"""
    
    def test_美化输出(self):
        from 美化输出 import 美化输出
        数据 = {'a': 1, 'b': [1, 2, 3], 'c': {'d': 4}}
        结果 = 美化输出(数据)
        self.assertIsInstance(结果, str)
        self.assertIn('a', 结果)
    
    def test_美化JSON(self):
        from 美化输出 import 美化JSON
        数据 = {'name': 'test', 'value': 123}
        结果 = 美化JSON(数据, 缩进=2)
        self.assertIn('name', 结果)
        self.assertIn('test', 结果)
    
    def test_格式化表格(self):
        from 美化输出 import 格式化表格
        数据 = [['张三', 20, 'A'], ['李四', 25, 'B']]
        结果 = 格式化表格(数据, ['姓名', '年龄', '等级'])
        self.assertIn('张三', 结果)
        self.assertIn('姓名', 结果)


class 测试复制模块(unittest.TestCase):
    """测试复制模块"""
    
    def test_浅复制(self):
        from 复制 import 浅复制
        原数据 = [1, 2, [3, 4]]
        副本 = 浅复制(原数据)
        self.assertEqual(副本, 原数据)
        副本[0] = 100
        self.assertNotEqual(副本[0], 原数据[0])
        副本[2][0] = 999
        self.assertEqual(原数据[2][0], 999)
    
    def test_深复制(self):
        from 复制 import 深复制
        原数据 = [1, 2, [3, 4]]
        副本 = 深复制(原数据)
        self.assertEqual(副本, 原数据)
        副本[2][0] = 999
        self.assertNotEqual(原数据[2][0], 999)
    
    def test_复制函数(self):
        from 复制 import 复制
        数据 = [1, 2, 3]
        浅 = 复制(数据, 深=False)
        深 = 复制(数据, 深=True)
        self.assertEqual(浅, 数据)
        self.assertEqual(深, 数据)


class 测试文件匹配模块(unittest.TestCase):
    """测试文件匹配模块"""
    
    def test_名称匹配(self):
        from 文件匹配 import 名称匹配
        self.assertTrue(名称匹配('test.txt', '*.txt'))
        self.assertFalse(名称匹配('test.py', '*.txt'))
    
    def test_名称匹配忽略大小写(self):
        from 文件匹配 import 名称匹配忽略大小写
        self.assertTrue(名称匹配忽略大小写('Test.TXT', '*.txt'))
        self.assertTrue(名称匹配忽略大小写('test.py', '*.PY'))
    
    def test_过滤列表(self):
        from 文件匹配 import 过滤列表
        文件列表 = ['a.txt', 'b.py', 'c.txt', 'd.js']
        结果 = 过滤列表(文件列表, '*.txt')
        self.assertEqual(len(结果), 2)
        self.assertIn('a.txt', 结果)
        self.assertIn('c.txt', 结果)
    
    def test_匹配文件(self):
        from 文件匹配 import 匹配文件
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                with open(os.path.join(tmpdir, f'file{i}.txt'), 'w') as f:
                    f.write('test')
            结果 = 匹配文件('*.txt', 递归=False, 目录=tmpdir)
            self.assertEqual(len(结果), 3)
    
    def test_转义元字符(self):
        from 文件匹配 import 转义元字符
        结果 = 转义元字符('test.txt')
        self.assertIsInstance(结果, str)


class 测试对象序列化模块(unittest.TestCase):
    """测试对象序列化模块"""
    
    def test_序列化反序列化(self):
        from 对象序列化 import 序列化, 反序列化
        数据 = {'a': 1, 'b': [1, 2, 3], 'c': 'hello'}
        字节数据 = 序列化(数据)
        self.assertIsInstance(字节数据, bytes)
        恢复 = 反序列化(字节数据)
        self.assertEqual(恢复, 数据)
    
    def test_保存到文件从文件加载(self):
        from 对象序列化 import 保存到文件, 从文件加载
        import tempfile
        数据 = {'key': 'value', 'num': 42}
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            路径 = f.name
        try:
            保存到文件(数据, 路径)
            恢复 = 从文件加载(路径)
            self.assertEqual(恢复, 数据)
        finally:
            os.unlink(路径)
    
    def test_序列化为字符串(self):
        from 对象序列化 import 序列化为字符串, 从字符串反序列化
        数据 = [1, 2, 3, {'a': 'b'}]
        字符串 = 序列化为字符串(数据)
        self.assertIsInstance(字符串, str)
        恢复 = 从字符串反序列化(字符串)
        self.assertEqual(恢复, 数据)
    
    def test_JSON序列化(self):
        from 对象序列化 import JSON序列化, JSON反序列化
        数据 = {'name': 'test', 'numbers': [1, 2, 3]}
        json_str = JSON序列化(数据)
        self.assertIsInstance(json_str, str)
        恢复 = JSON反序列化(json_str)
        self.assertEqual(恢复, 数据)


class 测试枚举模块(unittest.TestCase):
    """测试枚举模块"""
    
    def test_创建枚举(self):
        from 枚举 import 创建枚举
        颜色 = 创建枚举('颜色', {'红色': 1, '绿色': 2, '蓝色': 3})
        self.assertEqual(颜色.红色.value, 1)
        self.assertEqual(颜色.绿色.value, 2)
    
    def test_创建整数枚举(self):
        from 枚举 import 创建整数枚举
        状态 = 创建整数枚举('状态', ['未开始', '进行中', '已完成'], 起始值=1)
        self.assertEqual(状态.未开始.value, 1)
        self.assertEqual(状态.进行中.value, 2)
        self.assertEqual(状态.已完成.value, 3)
    
    def test_枚举所有成员(self):
        from 枚举 import 创建枚举
        颜色 = 创建枚举('颜色', {'红': 1, '绿': 2, '蓝': 3})
        成员 = 颜色.所有成员()
        self.assertEqual(len(成员), 3)
    
    def test_枚举所有名称(self):
        from 枚举 import 创建枚举
        颜色 = 创建枚举('颜色', {'红': 1, '绿': 2, '蓝': 3})
        名称 = 颜色.所有名称()
        self.assertIn('红', 名称)
        self.assertIn('绿', 名称)
    
    def test_从值获取(self):
        from 枚举 import 创建枚举
        颜色 = 创建枚举('颜色', {'红': 1, '绿': 2})
        成员 = 颜色.从值获取(1)
        self.assertEqual(成员.name, '红')
    
    def test_包含值(self):
        from 枚举 import 创建枚举
        颜色 = 创建枚举('颜色', {'红': 1, '绿': 2})
        self.assertTrue(颜色.包含值(1))
        self.assertFalse(颜色.包含值(999))


class 测试文本差异模块(unittest.TestCase):
    """测试文本差异模块"""
    
    def test_比较文本(self):
        from 文本差异 import 比较文本
        文本1 = 'hello\nworld\n'
        文本2 = 'hello\npython\n'
        差异 = 比较文本(文本1, 文本2)
        self.assertIsInstance(差异, list)
    
    def test_差异字符串(self):
        from 文本差异 import 差异字符串
        文本1 = 'a\nb\nc\n'
        文本2 = 'a\nb\nd\n'
        结果 = 差异字符串(文本1, 文本2)
        self.assertIsInstance(结果, str)
    
    def test_相似度(self):
        from 文本差异 import 相似度
        self.assertAlmostEqual(相似度('hello', 'hello'), 1.0)
        self.assertLess(相似度('hello', 'world'), 0.5)
    
    def test_查找最相似(self):
        from 文本差异 import 查找最相似
        候选 = ['apple', 'banana', 'orange', 'app']
        结果 = 查找最相似('appel', 候选, 阈值=0.5)
        self.assertGreater(len(结果), 0)
    
    def test_快速比较(self):
        from 文本差异 import 快速比较
        文本1 = 'line1\nline2\nline3\n'
        文本2 = 'line1\nline2\nline4\n'
        结果 = 快速比较(文本1, 文本2)
        self.assertIn('相似度', 结果)
        self.assertIn('原文件行数', 结果)
        self.assertIn('新文件行数', 结果)


class 测试压缩模块(unittest.TestCase):
    """测试压缩模块"""
    
    def test_ZIP压缩解压(self):
        from 压缩 import 创建ZIP, 解压ZIP, 是ZIP文件, 列出ZIP内容
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            源目录 = os.path.join(tmpdir, 'src')
            os.makedirs(源目录)
            with open(os.path.join(源目录, 'a.txt'), 'w') as f:
                f.write('hello')
            with open(os.path.join(源目录, 'b.txt'), 'w') as f:
                f.write('world')
            
            zip路径 = os.path.join(tmpdir, 'test.zip')
            创建ZIP(源目录, zip路径, 包含目录名=False)
            
            self.assertTrue(是ZIP文件(zip路径))
            
            内容 = 列出ZIP内容(zip路径)
            self.assertEqual(len(内容), 2)
            
            输出目录 = os.path.join(tmpdir, 'out')
            os.makedirs(输出目录)
            解压ZIP(zip路径, 输出目录)
            
            self.assertTrue(os.path.exists(os.path.join(输出目录, 'a.txt')))
    
    def test_内存压缩解压(self):
        from 压缩 import 内存压缩, 内存解压
        数据 = b'hello world ' * 100
        压缩后 = 内存压缩(数据)
        self.assertLess(len(压缩后), len(数据))
        解压后 = 内存解压(压缩后)
        self.assertEqual(解压后, 数据)
    
    def test_GZIP字符串(self):
        from 压缩 import GZIP压缩字符串, GZIP解压字符串
        文本 = '测试文本 ' * 50
        压缩后 = GZIP压缩字符串(文本)
        self.assertIsInstance(压缩后, bytes)
        解压后 = GZIP解压字符串(压缩后)
        self.assertEqual(解压后, 文本)
    
    def test_CRC32(self):
        from 压缩 import CRC32
        结果 = CRC32(b'hello')
        self.assertIsInstance(结果, int)
        self.assertGreater(结果, 0)


class 测试高级文件模块(unittest.TestCase):
    """测试高级文件模块"""
    
    def test_复制文件(self):
        from 高级文件 import 复制文件
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            源文件 = os.path.join(tmpdir, 'src.txt')
            目标文件 = os.path.join(tmpdir, 'dst.txt')
            with open(源文件, 'w') as f:
                f.write('test content')
            
            复制文件(源文件, 目标文件)
            self.assertTrue(os.path.exists(目标文件))
            with open(目标文件) as f:
                self.assertEqual(f.read(), 'test content')
    
    def test_磁盘使用情况(self):
        from 高级文件 import 磁盘使用情况
        结果 = 磁盘使用情况('.')
        self.assertIn('总空间', 结果)
        self.assertIn('已用空间', 结果)
        self.assertIn('可用空间', 结果)
        self.assertGreater(结果['总空间'], 0)
    
    def test_目录大小(self):
        from 高级文件 import 目录大小
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                with open(os.path.join(tmpdir, f'file{i}.txt'), 'w') as f:
                    f.write('x' * 100)
            大小 = 目录大小(tmpdir)
            self.assertEqual(大小, 500)
    
    def test_命令存在(self):
        from 高级文件 import 命令存在
        import platform
        if platform.system() == 'Windows':
            self.assertTrue(命令存在('cmd'))
        else:
            self.assertTrue(命令存在('ls'))
    
    def test_文件树(self):
        from 高级文件 import 文件树
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'subdir'))
            with open(os.path.join(tmpdir, 'a.txt'), 'w') as f:
                f.write('test')
            结果 = 文件树(tmpdir, 显示大小=True)
            self.assertIsInstance(结果, str)
            self.assertIn('a.txt', 结果)


class 测试字符串常量模块(unittest.TestCase):
    """测试字符串常量模块"""
    
    def test_常量值(self):
        from 字符串常量 import 小写字母, 大写字母, 数字, 标点符号
        self.assertEqual(小写字母, 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(大写字母, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.assertEqual(数字, '0123456789')
        self.assertIn(',', 标点符号)
    
    def test_是字母数字(self):
        from 字符串常量 import 是字母, 是数字, 是字母数字
        self.assertTrue(是字母('a'))
        self.assertFalse(是字母('1'))
        self.assertTrue(是数字('9'))
        self.assertFalse(是数字('a'))
        self.assertTrue(是字母数字('z'))
        self.assertTrue(是字母数字('5'))
    
    def test_大小写转换(self):
        from 字符串常量 import 全大写, 全小写, 首字母大写, 交换大小写
        self.assertEqual(全大写('hello'), 'HELLO')
        self.assertEqual(全小写('WORLD'), 'world')
        self.assertEqual(首字母大写('hello'), 'Hello')
        self.assertEqual(交换大小写('Hello'), 'hELLO')
    
    def test_去除空白(self):
        from 字符串常量 import 去除两端空白, 去除左端空白, 去除右端空白
        self.assertEqual(去除两端空白('  hi  '), 'hi')
        self.assertEqual(去除左端空白('  hi'), 'hi')
        self.assertEqual(去除右端空白('hi  '), 'hi')
    
    def test_分割连接(self):
        from 字符串常量 import 分割, 连接
        self.assertEqual(分割('a,b,c', ','), ['a', 'b', 'c'])
        self.assertEqual(连接('-', ['a', 'b', 'c']), 'a-b-c')
    
    def test_查找包含(self):
        from 字符串常量 import 查找, 包含, 以开头, 以结尾
        self.assertEqual(查找('hello world', 'world'), 6)
        self.assertEqual(查找('hello', 'xyz'), -1)
        self.assertTrue(包含('hello world', 'world'))
        self.assertTrue(以开头('hello', 'he'))
        self.assertTrue(以结尾('hello.py', '.py'))
    
    def test_替换(self):
        from 字符串常量 import 替换
        self.assertEqual(替换('hello world', 'world', 'python'), 'hello python')
    
    def test_对齐填充(self):
        from 字符串常量 import 居中填充, 左对齐, 右对齐, 补零
        self.assertEqual(左对齐('hi', 5), 'hi   ')
        self.assertEqual(右对齐('hi', 5), '   hi')
        self.assertEqual(len(居中填充('hi', 5)), 5)
        self.assertIn('hi', 居中填充('hi', 5))
        self.assertEqual(补零('42', 5), '00042')


class 测试函数工具模块(unittest.TestCase):
    """测试函数工具模块"""
    
    def test_偏函数(self):
        from 函数工具 import 偏函数
        def 加(a, b):
            return a + b
        加5 = 偏函数(加, 5)
        self.assertEqual(加5(3), 8)
        self.assertEqual(加5(10), 15)
    
    def test_归约(self):
        from 函数工具 import 归约
        def 加(a, b):
            return a + b
        self.assertEqual(归约(加, [1, 2, 3, 4, 5]), 15)
        self.assertEqual(归约(加, [1, 2, 3], 10), 16)
    
    def test_求和求积(self):
        from 函数工具 import 求和, 求积
        self.assertEqual(求和([1, 2, 3, 4]), 10)
        self.assertEqual(求积([1, 2, 3, 4]), 24)
    
    def test_最大值最小值(self):
        from 函数工具 import 最大值, 最小值
        self.assertEqual(最大值([3, 1, 4, 1, 5]), 5)
        self.assertEqual(最小值([3, 1, 4, 1, 5]), 1)
    
    def test_全部为真任一为真(self):
        from 函数工具 import 全部为真, 任一为真
        self.assertTrue(全部为真([True, True, True]))
        self.assertFalse(全部为真([True, False, True]))
        self.assertTrue(任一为真([False, False, True]))
        self.assertFalse(任一为真([False, False, False]))
    
    def test_累积(self):
        from 函数工具 import 累积
        def 加(a, b):
            return a + b
        结果 = 累积(加, [1, 2, 3, 4])
        self.assertEqual(结果, [1, 3, 6, 10])
    
    def test_管道(self):
        from 函数工具 import 管道
        def 加1(x):
            return x + 1
        def 乘2(x):
            return x * 2
        结果 = 管道(5, [加1, 乘2])
        self.assertEqual(结果, 12)
    
    def test_组合(self):
        from 函数工具 import 组合
        def 加1(x):
            return x + 1
        def 乘2(x):
            return x * 2
        组合函数 = 组合([加1, 乘2])
        self.assertEqual(组合函数(5), 11)


class 测试集合工具模块(unittest.TestCase):
    """测试集合工具模块"""
    
    def test_计数器(self):
        from 集合工具 import 计数器
        c = 计数器(['a', 'b', 'a', 'c', 'b', 'a'])
        self.assertEqual(c['a'], 3)
        self.assertEqual(c['b'], 2)
        self.assertEqual(c['c'], 1)
    
    def test_计数器最常见(self):
        from 集合工具 import 计数器
        c = 计数器(['a', 'b', 'a', 'c', 'b', 'a'])
        常见 = c.最常见(2)
        self.assertEqual(len(常见), 2)
        self.assertEqual(常见[0][0], 'a')
    
    def test_默认字典(self):
        from 集合工具 import 默认字典
        d = 默认字典(int)
        self.assertEqual(d['不存在的键'], 0)
        d['测试'] += 1
        self.assertEqual(d['测试'], 1)
    
    def test_默认字典列表(self):
        from 集合工具 import 默认字典
        d = 默认字典(list)
        d['键'].append(1)
        d['键'].append(2)
        self.assertEqual(d['键'], [1, 2])
    
    def test_有序字典(self):
        from 集合工具 import 有序字典
        d = 有序字典()
        d['b'] = 2
        d['a'] = 1
        d['c'] = 3
        键列表 = list(d.keys())
        self.assertEqual(键列表, ['b', 'a', 'c'])
    
    def test_双端队列(self):
        from 集合工具 import 双端队列
        dq = 双端队列([1, 2, 3])
        dq.右入队(4)
        self.assertEqual(dq.右出队(), 4)
        dq.左入队(0)
        self.assertEqual(dq.左出队(), 0)
    
    def test_命名元组(self):
        from 集合工具 import 命名元组
        点 = 命名元组('点', ['x', 'y'])
        p = 点(3, 4)
        self.assertEqual(p.x, 3)
        self.assertEqual(p.y, 4)
    
    def test_统计频率(self):
        from 集合工具 import 统计频率
        结果 = 统计频率(['a', 'b', 'a', 'c', 'b', 'a'])
        self.assertEqual(结果['a'], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
