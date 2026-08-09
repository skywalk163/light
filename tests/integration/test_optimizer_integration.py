# -*- coding: utf-8 -*-
"""
优化器集成测试

测试优化器是否正确集成到编译器流水线中。
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)

from compiler import LightCompiler, OPTIMIZERS
from ast_nodes import (
    NumberLiteral, BooleanLiteral, IfStatement,
    PrintStatement, BinaryOp,
)


class TestOptimizerIntegration(unittest.TestCase):
    """优化器集成测试"""

    def setUp(self):
        """每个测试前创建编译器实例"""
        self.compiler = LightCompiler()

    def test_dead_code_elimination_applied(self):
        # 测试死代码消除是否生效：if 假条件的代码不应出现在优化后的 AST 中
        # 使用光明语法编写一个包含假条件 if 的程序（使用 0 作为假条件）
        code = '''如果 0 那么打印 "不会执行"。
打印 "会执行"。'''

        # 使用默认优化（optimize=True）
        result = self.compiler.compile(code, optimize=True)
        ast_module = result['ast']

        # 验证 if 语句被消除（优化后没有 IfStatement）
        has_if = any(isinstance(stmt, IfStatement) for stmt in ast_module.statements)
        self.assertFalse(has_if)
        # 验证语句数量减少（原来有 if + print，优化后只剩 print）
        self.assertEqual(len(ast_module.statements), 1)

    def test_constant_folding_applied(self):
        # 测试常量折叠是否生效：常量表达式应该被折叠为字面量
        # 使用光明语法编写一个包含常量表达式的变量声明
        code = '设 x 为 1 加 2 乘 3。'

        # 使用默认优化（optimize=True）
        result = self.compiler.compile(code, optimize=True)
        ast_module = result['ast']

        # 找到变量声明语句
        from ast_nodes import VariableDeclaration
        var_decl = None
        for stmt in ast_module.statements:
            if isinstance(stmt, VariableDeclaration) and stmt.name == 'x':
                var_decl = stmt
                break

        self.assertIsNotNone(var_decl)
        # 常量折叠后，值应该是 NumberLiteral，值为 7（1 + 2*3 = 7）
        self.assertIsInstance(var_decl.value, NumberLiteral)
        self.assertEqual(var_decl.value.value, 7)

    def test_optimize_flag_works(self):
        # 测试 optimize=False 时不进行优化
        # 使用光明语法编写一个包含假条件 if 的程序（使用 0 作为假条件）
        code = '''如果 0 那么打印 "不会执行"。
打印 "会执行"。'''

        # 不优化（optimize=False）
        result_no_opt = self.compiler.compile(code, optimize=False)
        ast_no_opt = result_no_opt['ast']

        # 重置编译器
        self.compiler = LightCompiler()

        # 优化（optimize=True）
        result_opt = self.compiler.compile(code, optimize=True)
        ast_opt = result_opt['ast']

        # 不优化时，应该有 if 语句
        has_if_no_opt = any(isinstance(stmt, IfStatement) for stmt in ast_no_opt.statements)
        self.assertTrue(has_if_no_opt)
        # 不优化时，应该有 2 条语句（if + print）
        self.assertEqual(len(ast_no_opt.statements), 2)

        # 优化时，不应该有 if 语句（被消除）
        has_if_opt = any(isinstance(stmt, IfStatement) for stmt in ast_opt.statements)
        self.assertFalse(has_if_opt)
        # 优化时，应该只有 1 条语句
        self.assertEqual(len(ast_opt.statements), 1)

    def test_optimizers_list_order(self):
        # 测试 OPTIMIZERS 列表的顺序是否正确
        # 顺序应该是：DeadCodeEliminationOptimizer, ConstantFoldingOptimizer, LoopInvariantOptimizer
        from optimizer import (
            DeadCodeEliminationOptimizer,
            ConstantFoldingOptimizer,
            LoopInvariantOptimizer,
        )

        self.assertEqual(len(OPTIMIZERS), 3)
        self.assertEqual(OPTIMIZERS[0], DeadCodeEliminationOptimizer)
        self.assertEqual(OPTIMIZERS[1], ConstantFoldingOptimizer)
        self.assertEqual(OPTIMIZERS[2], LoopInvariantOptimizer)

    def test_optimize_default_true(self):
        # 测试 optimize 参数默认值为 True
        # 不传递 optimize 参数时，应该默认开启优化
        code = '''如果 0 那么打印 "不会执行"。
打印 "会执行"。'''

        # 不传 optimize 参数（使用默认值）
        result = self.compiler.compile(code)
        ast_module = result['ast']

        # 应该有优化效果（没有 if 语句）
        has_if = any(isinstance(stmt, IfStatement) for stmt in ast_module.statements)
        self.assertFalse(has_if)
        # 应该只有 1 条语句
        self.assertEqual(len(ast_module.statements), 1)


if __name__ == '__main__':
    unittest.main()
