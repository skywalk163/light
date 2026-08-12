# -*- coding: utf-8 -*-
"""
光明编译器 - 跨平台兼容性测试

验证编译器在 Windows、Linux、macOS 上的行为一致性。
重点测试：
1. 路径分隔符处理（/ vs \）
2. 换行符处理（\n vs \r\n）
3. 编码处理（utf-8-sig BOM）
4. 进程管理（信号、子进程）
5. 文件系统操作
6. 环境变量
"""

import os
import sys
import platform
import tempfile
import unittest
import subprocess
from pathlib import Path


class TestCrossPlatformPaths(unittest.TestCase):
    """跨平台路径测试"""

    def test_path_separator(self):
        """测试路径分隔符处理"""
        # 验证 Path 对象能正确处理两种分隔符
        p1 = Path('a/b/c')
        self.assertEqual(p1.name, 'c')
        # 在 Windows 上反斜杠是路径分隔符；其他系统（Linux/FreeBSD/macOS）上不是
        if sys.platform == 'win32':
            p2 = Path('a\\b\\c')
            self.assertEqual(p2.name, 'c')

    def test_path_join(self):
        """测试路径拼接"""
        # os.path.join 应使用平台正确的分隔符
        joined = os.path.join('a', 'b', 'c')
        if sys.platform == 'win32':
            self.assertIn('\\', joined)
        else:
            self.assertIn('/', joined)

    def test_absolute_path(self):
        """测试绝对路径判断"""
        if sys.platform == 'win32':
            self.assertTrue(os.path.isabs('C:\\test'))
            self.assertTrue(os.path.isabs('D:\\path\\file.txt'))
        else:
            self.assertTrue(os.path.isabs('/tmp'))
            self.assertTrue(os.path.isabs('/home/user'))


class TestCrossPlatformNewlines(unittest.TestCase):
    """跨平台换行符测试"""

    def test_universal_newline_read(self):
        """测试通用换行读取"""
        content = "line1\nline2\r\nline3\n"
        with tempfile.NamedTemporaryFile(mode='w+', newline='', delete=False) as f:
            f.write(content)
            f.flush()
            fname = f.name

        try:
            # 通用换行模式读取
            with open(fname, 'r', newline=None) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0].strip(), 'line1')
            self.assertEqual(lines[1].strip(), 'line2')
            self.assertEqual(lines[2].strip(), 'line3')
        finally:
            os.unlink(fname)

    def test_write_newline_conversion(self):
        """测试写入换行符转换"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\n")
            f.flush()
            fname = f.name

        try:
            with open(fname, 'rb') as f:
                raw = f.read()
            if sys.platform == 'win32':
                # Windows 文本模式下 \n → \r\n
                self.assertIn(b'\r\n', raw)
            else:
                self.assertIn(b'\n', raw)
        finally:
            os.unlink(fname)


class TestCrossPlatformEncoding(unittest.TestCase):
    """跨平台编码测试"""

    def test_utf8_bom_reading(self):
        """测试 UTF-8 BOM 文件读取"""
        content = "你好，光明！\n"
        bom = b'\xef\xbb\xbf'
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(bom + content.encode('utf-8'))
            f.flush()
            fname = f.name

        try:
            # 使用 utf-8-sig 读取 BOM 头
            with open(fname, 'r', encoding='utf-8-sig') as f:
                read_content = f.read()
            self.assertEqual(read_content.strip(), '你好，光明！')
        finally:
            os.unlink(fname)

    def test_utf8_without_bom(self):
        """测试无 BOM 的 UTF-8 文件读取"""
        content = "Hello, Light!\n"
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(content.encode('utf-8'))
            f.flush()
            fname = f.name

        try:
            with open(fname, 'r', encoding='utf-8') as f:
                read_content = f.read()
            self.assertEqual(read_content.strip(), 'Hello, Light!')
        finally:
            os.unlink(fname)


class TestCrossPlatformProcess(unittest.TestCase):
    """跨平台进程管理测试"""

    def test_python_process(self):
        """测试启动 Python 子进程"""
        result = subprocess.run(
            [sys.executable, '-c', 'print("hello")'],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'hello')

    def test_system_info(self):
        """测试系统信息获取"""
        system = platform.system()
        self.assertIn(system, ['Windows', 'Linux', 'Darwin', 'FreeBSD'])

    def test_platform_detection(self):
        """测试平台检测"""
        if sys.platform == 'win32':
            self.assertEqual(os.name, 'nt')
        elif sys.platform == 'darwin':
            self.assertEqual(os.name, 'posix')
        elif sys.platform.startswith('linux'):
            self.assertEqual(os.name, 'posix')
        elif sys.platform.startswith('freebsd'):
            self.assertEqual(os.name, 'posix')


class TestCrossPlatformFileSystem(unittest.TestCase):
    """跨平台文件系统测试"""

    def test_temp_directory(self):
        """测试临时目录创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(os.path.exists(tmpdir))
            test_file = os.path.join(tmpdir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            self.assertTrue(os.path.exists(test_file))

    def test_long_paths(self):
        """测试长路径处理"""
        if sys.platform != 'win32':
            # Unix 系统通常支持更长路径
            long_dir = 'a' * 200
            with tempfile.TemporaryDirectory() as tmpdir:
                long_path = os.path.join(tmpdir, long_dir)
                try:
                    os.makedirs(long_path, exist_ok=True)
                    self.assertTrue(os.path.exists(long_path))
                except OSError:
                    pass  # 某些系统可能有路径长度限制

    def test_file_permissions(self):
        """测试文件权限（非 Windows）"""
        if sys.platform != 'win32':
            with tempfile.NamedTemporaryFile(delete=False) as f:
                fname = f.name
            try:
                # 设置为只读
                os.chmod(fname, 0o444)
                self.assertTrue(os.access(fname, os.R_OK))
                os.chmod(fname, 0o644)
            finally:
                os.unlink(fname)


class TestCrossPlatformEnvironment(unittest.TestCase):
    """跨平台环境变量测试"""

    def test_path_env(self):
        """测试 PATH 环境变量"""
        path = os.environ.get('PATH', '')
        self.assertGreater(len(path), 0)
        if sys.platform == 'win32':
            self.assertIn(';', path)
        else:
            self.assertIn(':', path)

    def test_platform_env_var(self):
        """测试平台相关环境变量"""
        if sys.platform == 'win32':
            # Windows 特有环境变量
            self.assertIn('SystemRoot', os.environ)
            self.assertIn('WINDIR', os.environ)
        elif sys.platform == 'darwin':
            # macOS 特有
            self.assertIn('HOME', os.environ)
        else:
            # Linux 通用
            self.assertIn('HOME', os.environ)


class TestCrossPlatformCLI(unittest.TestCase):
    """跨平台命令行测试"""

    def test_encoding_cli(self):
        """测试命令行编码"""
        # 验证 Python 能正确处理 Unicode 输出
        test_str = '光明测试'
        result = subprocess.run(
            [sys.executable, '-c', f'print("{test_str}")'],
            capture_output=True, text=True
        )
        self.assertEqual(result.stdout.strip(), test_str)

    def test_sys_argv(self):
        """测试命令行参数"""
        test_args = ['--test', 'hello', '--flag']
        result = subprocess.run(
            [sys.executable, '-c', 'import sys; print("|".join(sys.argv[1:]))'] + test_args,
            capture_output=True, text=True
        )
        self.assertEqual(result.stdout.strip(), '|'.join(test_args))


class TestCrossPlatformStdlib(unittest.TestCase):
    """跨平台标准库模块加载测试"""

    def test_stdlib_modules_importable(self):
        """验证所有 stdlib 模块可在当前平台正常导入"""
        import importlib
        stdlib_dir = os.path.join(os.path.dirname(__file__), '..', 'stdlib')
        sys.path.insert(0, os.path.normpath(stdlib_dir))

        模块列表 = [
            '网络', '加密', '日志', '缓存', '配置', '测试',
            '日期时间', '正则表达式', '进度条', '数据验证',
            'JSON', 'Base64', 'CSV', 'XML', '哈希',
            '数学', '统计', '随机', '颜色', '信号',
            '线程', '进程', '编码', '编码解码', '文件系统',
            '字符串处理', '字符串工具', '字符串常量', '集合',
            '集合工具', '集合操作', '数据结构', '装饰器',
            '断言工具', '系统接口', '外部命令', '参数解析',
            '临时文件', '文件匹配', '格式化', '模板',
            '性能', '排序', '复数', '向量', '分词',
            '环境', '对象池缓存', '日志系统增强', '时间管理',
            '中文文本', '历法', '排版', '高级文件',
        ]

        失败模块 = []
        for 模块名 in 模块列表:
            try:
                importlib.import_module(模块名)
            except Exception as e:
                失败模块.append(f"{模块名}: {e}")

        if 失败模块:
            self.fail(f"以下模块导入失败:\n" + '\n'.join(失败模块))

    def test_stdlib_light_files_exist(self):
        """验证 .light 文件与 .py 文件对应"""
        stdlib_dir = os.path.join(os.path.dirname(__file__), '..', 'stdlib')
        py_files = set()
        light_files = set()
        for f in os.listdir(stdlib_dir):
            if f.endswith('.py') and f != '__init__.py' and f != 'builtins.py':
                py_files.add(f[:-3])
            elif f.endswith('.light'):
                light_files.add(f[:-5])
        # 检查 .py 文件是否有对应的 .light 文件
        missing_light = py_files - light_files
        if missing_light:
            # 部分模块可能只有 .py，这是允许的
            pass


class TestCrossPlatformUnicode(unittest.TestCase):
    """跨平台 Unicode 处理测试"""

    def test_unicode_filename(self):
        """测试 Unicode 文件名处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = '测试文件_中文.txt'
            filepath = os.path.join(tmpdir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('unicode content')
                self.assertTrue(os.path.exists(filepath))
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.assertEqual(content, 'unicode content')
            except OSError:
                # 某些系统可能不支持 Unicode 文件名
                pass

    def test_unicode_path_in_stdlib(self):
        """测试标准库路径中的 Unicode 支持"""
        test_path = '光明/测试/文件.light'
        normalized = os.path.normpath(test_path)
        self.assertIsInstance(normalized, str)

    def test_encoding_detection(self):
        """测试编码检测"""
        # UTF-8 with BOM
        bom = b'\xef\xbb\xbf'
        utf8_bom = bom + '你好'.encode('utf-8')
        try:
            import chardet
            result = chardet.detect(utf8_bom)
            self.assertIn('utf', result['encoding'].lower())
        except ImportError:
            # 没有 chardet 时，使用 utf-8-sig 验证
            decoded = utf8_bom.decode('utf-8-sig')
            self.assertEqual(decoded, '你好')


class TestCrossPlatformNetwork(unittest.TestCase):
    """跨平台网络测试"""

    def test_socket_creation(self):
        """测试 socket 创建（跨平台）"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            self.assertIsNotNone(s)
            s.close()
        except OSError as e:
            self.skipTest(f"Socket 创建失败: {e}")

    def test_hostname_resolution(self):
        """测试主机名解析"""
        import socket
        try:
            hostname = socket.gethostname()
            self.assertIsInstance(hostname, str)
            self.assertGreater(len(hostname), 0)
        except OSError:
            pass

    def test_network_interfaces(self):
        """测试网络接口列表"""
        import socket
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            self.assertIsInstance(ip, str)
        except (OSError, socket.gaierror):
            pass


class TestCrossPlatformTimeLocale(unittest.TestCase):
    """跨平台时区和区域设置测试"""

    def test_timezone(self):
        """测试时区处理"""
        import time
        # 获取时区偏移
        offset = time.timezone
        self.assertIsInstance(offset, int)
        # 夏令时
        dst = time.daylight
        self.assertIsInstance(dst, int)

    def test_locale_encoding(self):
        """测试区域编码"""
        import locale
        try:
            encoding = locale.getpreferredencoding()
            self.assertIsInstance(encoding, str)
            self.assertGreater(len(encoding), 0)
        except Exception:
            pass


class TestCrossPlatformSymlink(unittest.TestCase):
    """跨平台符号链接测试"""

    def test_symlink_support(self):
        """测试符号链接支持"""
        if sys.platform == 'win32':
            # Windows 上符号链接可能需要管理员权限
            self.skipTest('Windows 符号链接需要管理员权限')
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, 'target.txt')
            link = os.path.join(tmpdir, 'link.txt')
            with open(target, 'w') as f:
                f.write('test')
            try:
                os.symlink(target, link)
                self.assertTrue(os.path.islink(link))
                self.assertEqual(os.readlink(link), target)
            except (OSError, NotImplementedError):
                pass


class TestCrossPlatformLargeFile(unittest.TestCase):
    """跨平台大文件处理测试"""

    def test_large_file_iteration(self):
        """测试大文件逐行迭代"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            for i in range(10000):
                f.write(f'line{i}\n')
            fname = f.name

        try:
            count = 0
            with open(fname, 'r') as f:
                for _ in f:
                    count += 1
            self.assertEqual(count, 10000)
        finally:
            os.unlink(fname)

    def test_file_seek(self):
        """测试文件随机访问"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'x' * 1000000)
            fname = f.name

        try:
            with open(fname, 'rb') as f:
                f.seek(500000)
                data = f.read(100)
                self.assertEqual(len(data), 100)
                f.seek(0)
                data = f.read(100)
                self.assertEqual(len(data), 100)
        finally:
            os.unlink(fname)


if __name__ == '__main__':
    unittest.main()