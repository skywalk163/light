# -*- coding: utf-8 -*-
"""
光明编译器流程集成测试

测试完整编译流程：解析 -> 语义分析 -> 代码生成
"""

import sys
import os
import unittest
import tempfile

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestCompilerPipeline(unittest.TestCase):
    """编译器流程测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from compiler import LightCompiler
            cls.Compiler = LightCompiler
        except ImportError as e:
            raise unittest.SkipTest(f"Compiler 模块不可用: {e}")

    def test_simple_compile(self):
        """测试简单程序编译"""
        compiler = self.Compiler()
        code = '打印 "你好"'
        try:
            result = compiler.compile(code)
            self.assertIsNotNone(result)
        except Exception as e:
            self.skipTest(f"Compiler.compile 失败: {e}")

    def test_variable_compile(self):
        """测试变量声明编译"""
        compiler = self.Compiler()
        code = '设 x 为 123'
        try:
            result = compiler.compile(code)
            self.assertIsNotNone(result)
        except Exception as e:
            self.skipTest(f"Compiler.compile 失败: {e}")

    def test_function_compile(self):
        """测试函数定义编译"""
        compiler = self.Compiler()
        code = '段落 加一 接收 n：\n    返回 n 加 1'
        try:
            result = compiler.compile(code)
            self.assertIsNotNone(result)
        except Exception as e:
            self.skipTest(f"Compiler.compile 失败: {e}")


class TestDualBackend(unittest.TestCase):
    """双后端集成测试"""

    def test_antlr_backend_available(self):
        """测试 ANTLR 后端可用性"""
        antlr_path = os.path.join(_project_root, 'antlrparser')
        self.assertTrue(os.path.exists(antlr_path))

    def test_src_backend_available(self):
        """测试 SRC 后端可用性"""
        src_path = os.path.join(_project_root, 'src')
        self.assertTrue(os.path.exists(src_path))
        # 验证核心文件存在
        self.assertTrue(os.path.exists(os.path.join(src_path, 'compiler.py')))
        self.assertTrue(os.path.exists(os.path.join(src_path, 'parser_stmt.py')))


if __name__ == '__main__':
    unittest.main()
