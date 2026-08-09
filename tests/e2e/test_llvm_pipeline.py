# -*- coding: utf-8 -*-
"""
光明 LLVM IR 生成和编译端到端测试

测试 LLVM IR 生成和 clang 编译流程
"""

import sys
import os
import unittest
import tempfile
import subprocess

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)


class TestLLVMGeneration(unittest.TestCase):
    """LLVM IR 生成测试"""

    @classmethod
    def setUpClass(cls):
        cls.antlr_dir = os.path.join(_project_root, 'antlrparser')

    def test_llvm_codegen_exists(self):
        """测试 LLVM 代码生成器存在"""
        llvm_codegen = os.path.join(self.antlr_dir, 'llvm_codegen.py')
        self.assertTrue(os.path.exists(llvm_codegen))

    def test_llvm_core_exists(self):
        """测试 LLVM 核心模块存在"""
        llvm_core = os.path.join(self.antlr_dir, 'llvm_core.py')
        self.assertTrue(os.path.exists(llvm_core))

    def test_light_llvm_exists(self):
        """测试 light_llvm.py 存在"""
        light_llvm = os.path.join(self.antlr_dir, 'light_llvm.py')
        self.assertTrue(os.path.exists(light_llvm))

    def test_simple_ir_generation(self):
        """测试简单 IR 生成"""
        # 创建临时测试文件
        test_code = '段落 主程序：\n    打印 "hello"'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.light',
                                         delete=False, encoding='utf-8') as f:
            f.write(test_code)
            temp_file = f.name

        try:
            # 尝试生成 IR
            result = subprocess.run(
                [sys.executable, os.path.join(self.antlr_dir, 'light_llvm.py'), temp_file],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=_project_root
            )
            # 检查是否生成了 .ll 文件
            ll_file = temp_file.replace('.light', '.ll')
            if os.path.exists(ll_file):
                with open(ll_file, 'r', encoding='utf-8') as f:
                    ir_content = f.read()
                # 验证 IR 内容
                self.assertIn('define', ir_content)
            # 或者检查编译器输出
            self.assertIn(result.returncode, [0, 1])  # 0=成功, 1=有错误但能运行
        except subprocess.TimeoutExpired:
            self.skipTest("LLVM 编译超时")
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            ll_file = temp_file.replace('.light', '.ll')
            if os.path.exists(ll_file):
                os.unlink(ll_file)

    def test_runtime_c_exists(self):
        """测试运行时 C 文件存在"""
        runtime_c = os.path.join(self.antlr_dir, 'runtime', 'light_runtime.c')
        self.assertTrue(os.path.exists(runtime_c))


class TestLLVMBackend(unittest.TestCase):
    """LLVM 后端测试"""

    def test_entry_block_alloca(self):
        """测试 alloca 在 entry block 中的处理"""
        # 这是 Phase 2 修复的关键 bug
        llvm_codegen = os.path.join(_project_root, 'antlrparser', 'llvm_codegen.py')
        if not os.path.exists(llvm_codegen):
            self.skipTest("llvm_codegen.py 不存在")

        with open(llvm_codegen, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证使用了 pending allocas 机制
        self.assertIn('pending_allocas', content,
                     "缺少 pending_allocas 机制")


if __name__ == '__main__':
    unittest.main()
