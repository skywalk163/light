# -*- coding: utf-8 -*-
"""
光明标准库集成测试

测试 src 编译器 + Python 后端的标准库函数
"""

import sys
import os
import unittest
import tempfile

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestStdlibList(unittest.TestCase):
    """列表操作标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_list_append(self):
        """测试列表追加"""
        code = '设 列表 为 [1, 2, 3]。\n列表追加(列表, 4)。\n打印 列表。'
        output = self._run_code(code)
        self.assertIn('4', output)

    def test_list_length(self):
        """测试列表长度"""
        code = '设 列表 为 [1, 2, 3, 4, 5]。\n打印 列表长度(列表)。'
        output = self._run_code(code)
        self.assertEqual(output, '5')

    def test_list_contains(self):
        """测试列表包含"""
        code = '设 列表 为 [1, 2, 3]。\n打印 列表包含(列表, 2)。'
        output = self._run_code(code)
        self.assertIn('True', output)

    def test_list_sort(self):
        """测试列表排序"""
        code = '设 列表 为 [3, 1, 2]。\n列表排序(列表)。\n打印 列表。'
        output = self._run_code(code)
        self.assertIn('[1, 2, 3]', output)

    def test_list_reverse(self):
        """测试列表反转"""
        code = '设 列表 为 [1, 2, 3]。\n列表反转(列表)。\n打印 列表。'
        output = self._run_code(code)
        self.assertIn('[3, 2, 1]', output)

    def test_list_pop(self):
        """测试列表弹出"""
        code = '设 列表 为 [1, 2, 3]。\n设 x 为 列表弹出(列表)。\n打印 x。'
        output = self._run_code(code)
        self.assertEqual(output, '3')


class TestStdlibString(unittest.TestCase):
    """字符串处理标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_string_length(self):
        """测试字符串长度"""
        code = '设 s 为 "你好世界"。\n打印 字符串长度(s)。'
        output = self._run_code(code)
        self.assertEqual(output, '4')

    def test_string_substring(self):
        """测试字符串截取"""
        code = '设 s 为 "你好世界"。\n打印 截取(s, 0, 2)。'
        output = self._run_code(code)
        self.assertEqual(output, '你好')

    def test_string_replace(self):
        """测试字符串替换"""
        code = '设 s 为 "你好世界"。\n打印 替换字符串(s, "世界", "光明")。'
        output = self._run_code(code)
        self.assertEqual(output, '你好光明')

    def test_string_split(self):
        """测试字符串分割"""
        code = '设 s 为 "a,b,c"。\n设 parts 为 分割字符串(s, ",")。\n打印 列表长度(parts)。'
        output = self._run_code(code)
        self.assertEqual(output, '3')

    def test_string_strip(self):
        """测试去除空白"""
        code = '设 s 为 "  你好  "。\n打印 去除空白(s)。'
        output = self._run_code(code)
        self.assertEqual(output, '你好')


class TestStdlibMath(unittest.TestCase):
    """数学标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_factorial(self):
        """测试阶乘"""
        code = '打印 阶乘(5)。'
        output = self._run_code(code)
        self.assertEqual(output, '120')

    def test_sum(self):
        """测试求和"""
        code = '设 列表 为 [1, 2, 3, 4, 5]。\n打印 求和(列表)。'
        output = self._run_code(code)
        self.assertEqual(output, '15')

    def test_average(self):
        """测试平均数"""
        code = '设 列表 为 [1, 2, 3, 4]。\n打印 平均数(列表)。'
        output = self._run_code(code)
        self.assertEqual(float(output), 2.5)

    def test_random_int(self):
        """测试随机整数"""
        code = '设 x 为 随机整数(1, 10)。\n打印 x 大于等于 1 且 x 小于等于 10。'
        output = self._run_code(code)
        self.assertIn('True', output)

    def test_pi(self):
        """测试圆周率"""
        code = '打印 圆周率()。'
        output = self._run_code(code)
        self.assertIn('3.14', output)


class TestStdlibFile(unittest.TestCase):
    """文件 I/O 标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_write_and_read_file(self):
        """测试写入和读取文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            tmp_path = f.name
        
        try:
            safe_path = tmp_path.replace('\\', '/')
            code = f'写入文件("{safe_path}", "hello world")。\n设 内容 为 读取文件("{safe_path}")。\n打印 内容。'
            output = self._run_code(code)
            self.assertEqual(output, 'hello world')
        finally:
            os.unlink(tmp_path)

    def test_file_exists(self):
        """测试文件存在判断"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('test')
            tmp_path = f.name
        
        try:
            safe_path = tmp_path.replace('\\', '/')
            code = f'打印 文件存在("{safe_path}")。'
            output = self._run_code(code)
            self.assertIn('True', output)
        finally:
            os.unlink(tmp_path)

    def test_file_not_exists(self):
        """测试不存在的文件"""
        code = '打印 文件存在("/nonexistent/file_12345.txt")。'
        output = self._run_code(code)
        self.assertIn('False', output)


class TestStdlibDict(unittest.TestCase):
    """字典操作标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_dict_get(self):
        """测试字典获取"""
        code = '设 d 为 字典创建()。\n字典设置(d, "a", 1)。\n打印 字典获取(d, "a")。'
        output = self._run_code(code)
        self.assertEqual(output, '1')

    def test_dict_keys(self):
        """测试字典键列表"""
        code = '设 d 为 字典创建()。\n字典设置(d, "a", 1)。\n字典设置(d, "b", 2)。\n打印 列表长度(字典键列表(d))。'
        output = self._run_code(code)
        self.assertEqual(output, '2')

    def test_dict_contains_key(self):
        """测试字典包含键"""
        code = '设 d 为 字典创建()。\n字典设置(d, "a", 1)。\n打印 字典包含键(d, "a")。'
        output = self._run_code(code)
        self.assertIn('True', output)


class TestStdlibTypeCheck(unittest.TestCase):
    """类型检查标准库测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_is_string(self):
        """测试是字符串"""
        code = '打印 是字符串("hello")。'
        output = self._run_code(code)
        self.assertIn('True', output)

    def test_is_list(self):
        """测试是列表"""
        code = '打印 是列表([1, 2, 3])。'
        output = self._run_code(code)
        self.assertIn('True', output)


class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"编译器模块不可用: {e}")

    def _run_code(self, code):
        """运行光明代码并返回输出"""
        from code_generator_unified import UnifiedCodeGenerator

        compiler = self.Compiler()
        result = compiler.compile(code)
        module = result.get('ast')
        generator = UnifiedCodeGenerator()
        py_code = generator.generate(module)

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(py_code, {})
        return buf.getvalue().strip()

    def test_try_catch(self):
        """测试 try-catch 基本功能"""
        code = '尝试：\n    打印 1。\n捕获 e：\n    打印 e。'
        output = self._run_code(code)
        self.assertEqual(output, '1')

    def test_try_catch_finally(self):
        """测试 try-catch-finally"""
        code = '尝试：\n    打印 1。\n捕获 e：\n    打印 0。\n最终：\n    打印 2。'
        output = self._run_code(code)
        self.assertEqual(output, '1\n2')

    def test_throw_catch(self):
        """测试抛出异常并捕获"""
        code = '尝试：\n    抛出 "测试错误"。\n捕获 e：\n    打印 e。'
        output = self._run_code(code)
        self.assertEqual(output, '测试错误')

    def test_try_only(self):
        """测试只有 try 块（无 catch）"""
        code = '尝试：\n    打印 1。'
        output = self._run_code(code)
        self.assertEqual(output, '1')


if __name__ == '__main__':
    unittest.main()
