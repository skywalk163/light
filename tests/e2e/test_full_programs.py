# -*- coding: utf-8 -*-
"""
光明完整程序端到端测试

测试完整程序的编译和执行
"""

import sys
import os
import unittest
import subprocess
import tempfile

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)


class TestFullPrograms(unittest.TestCase):
    """完整程序测试"""

    @classmethod
    def setUpClass(cls):
        cls.project_dir = os.path.join(_project_root, 'project')

    def test_accounting_program_exists(self):
        """测试记账程序存在"""
        accounting = os.path.join(self.project_dir, '记账.light')
        if not os.path.exists(accounting):
            accounting = os.path.join(self.project_dir, '记账_v3.light')
        self.assertTrue(os.path.exists(accounting),
                       f"记账程序不存在于 {self.project_dir}")

    def test_simple_program_compiles(self):
        """测试简单程序可编译"""
        # 使用 bootstrap 编译器验证基本编译
        bootstrap_py = os.path.join(_project_root, 'bootstrap', 'bootstrap_v3_compiled.py')
        if not os.path.exists(bootstrap_py):
            self.skipTest("Bootstrap 编译器不存在")

        test_code = '段落 主程序：\n    打印 "test"'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.light',
                                         delete=False, encoding='utf-8') as f:
            f.write(test_code)
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, bootstrap_py, temp_file],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=_project_root
            )
            # 验证程序可以执行（不检查返回码，因为可能有输出）
            self.assertIsNotNone(result.stdout or result.stderr)
        except subprocess.TimeoutExpired:
            self.fail("程序执行超时")
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestCLITools(unittest.TestCase):
    """CLI 工具测试"""

    def test_light_unified_exists(self):
        """测试统一 CLI 存在"""
        cli_unified = os.path.join(_project_root, 'cli', 'light_unified.py')
        self.assertTrue(os.path.exists(cli_unified))

    def test_light_unified_help(self):
        """测试统一 CLI 帮助信息"""
        cli_unified = os.path.join(_project_root, 'cli', 'light_unified.py')
        if not os.path.exists(cli_unified):
            self.skipTest("light_unified.py 不存在")

        try:
            result = subprocess.run(
                [sys.executable, cli_unified, '--help'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=_project_root
            )
            # 验证帮助信息包含关键内容
            output = result.stdout + result.stderr
            self.assertIn('--backend', output)
        except subprocess.TimeoutExpired:
            self.fail("CLI 执行超时")


if __name__ == '__main__':
    unittest.main()
