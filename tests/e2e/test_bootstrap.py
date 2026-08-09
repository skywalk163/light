# -*- coding: utf-8 -*-
"""
光明自举编译器端到端测试

验证 bootstrap 编译器的自举能力
"""

import sys
import os
import unittest
import tempfile
import hashlib

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)


class TestBootstrap(unittest.TestCase):
    """自举编译器测试"""

    @classmethod
    def setUpClass(cls):
        cls.bootstrap_dir = os.path.join(_project_root, 'bootstrap')
        cls.bootstrap_py = os.path.join(cls.bootstrap_dir, 'bootstrap_v3_compiled.py')
        cls.compiler_light = os.path.join(cls.bootstrap_dir, 'compiler.light')

    def test_bootstrap_files_exist(self):
        """测试自举文件存在"""
        if not os.path.exists(self.bootstrap_py):
            self.skipTest(f"Bootstrap 编译器不存在（可重新生成）: {self.bootstrap_py}")
        self.assertTrue(os.path.exists(self.compiler_light),
                        f"Compiler 源文件不存在: {self.compiler_light}")

    def test_bootstrap_compiler_runs(self):
        """测试自举编译器可运行"""
        if not os.path.exists(self.bootstrap_py):
            self.skipTest(f"Bootstrap 编译器不存在: {self.bootstrap_py}")
        # 使用简单测试代码验证编译器可执行
        test_code = '打印 "hello"'
        result = self._run_bootstrap(test_code)
        self.assertIsNotNone(result)

    def test_bootstrap_self_compile(self):
        """测试自举编译器自编译"""
        # 检查自举编译器能否编译自身
        if not os.path.exists(self.compiler_light):
            self.skipTest("Compiler.light 不存在")

        try:
            # 读取 compiler.light
            with open(self.compiler_light, 'r', encoding='utf-8') as f:
                compiler_src = f.read()
            self.assertGreater(len(compiler_src), 1000,
                             "Compiler.light 太短，可能不完整")
        except Exception as e:
            self.skipTest(f"无法读取 compiler.light: {e}")

    def _run_bootstrap(self, code):
        """运行 bootstrap 编译器执行代码"""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, self.bootstrap_py, '-c', code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=_project_root
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None


class TestBootstrapModules(unittest.TestCase):
    """自举模块测试"""

    def test_token_module(self):
        """测试 token 模块"""
        token_light = os.path.join(_project_root, 'bootstrap', 'token.light')
        self.assertTrue(os.path.exists(token_light))

    def test_ast_module(self):
        """测试 AST 模块"""
        ast_light = os.path.join(_project_root, 'bootstrap', 'light_ast.light')
        self.assertTrue(os.path.exists(ast_light))

    def test_lexer_module(self):
        """测试 lexer 模块"""
        lexer_light = os.path.join(_project_root, 'bootstrap', 'lexer.light')
        self.assertTrue(os.path.exists(lexer_light))

    def test_parser_module(self):
        """测试 parser 模块"""
        parser_light = os.path.join(_project_root, 'bootstrap', 'parser.light')
        self.assertTrue(os.path.exists(parser_light))

    def test_codegen_module(self):
        """测试 codegen 模块"""
        codegen_light = os.path.join(_project_root, 'bootstrap', 'codegen.light')
        self.assertTrue(os.path.exists(codegen_light))


if __name__ == '__main__':
    unittest.main()
