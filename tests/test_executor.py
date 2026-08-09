#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 执行引擎测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))

import unittest
from io import StringIO

# 尝试导入 REPL 执行引擎
try:
    from repl.executor import Executor, Environment
    EXECUTOR_AVAILABLE = True
except ImportError as e:
    EXECUTOR_AVAILABLE = False
    EXECUTOR_IMPORT_ERROR = str(e)


class TestExecutor(unittest.TestCase):
    """光明执行引擎测试"""

    def setUp(self):
        """每个测试前的准备工作"""
        if not EXECUTOR_AVAILABLE:
            self.skipTest(f"执行引擎未实现: {EXECUTOR_IMPORT_ERROR}")
        self.executor = Executor()

    def test_simple_expression(self):
        """测试简单表达式：先定义后使用"""
        # 先定义变量
        self.executor.execute("设 甲 为 5。")
        # 然后使用变量进行运算
        result = self.executor.execute("甲 加 3")
        self.assertEqual(result, 8)

    def test_variable_declaration(self):
        """测试变量声明：设 甲 为 3。"""
        self.executor.execute("设 甲 为 3。")
        result = self.executor.execute("甲")
        self.assertEqual(result, 3)

    def test_function_call(self):
        """测试函数调用：打印(甲)。"""
        self.executor.execute("设 甲 为 3。")
        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = captured = StringIO()
        try:
            self.executor.execute("打印(甲)。")
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("3", output)

    def test_paragraph_definition(self):
        """测试段落定义（单行形式）"""
        # 单行段落定义
        self.executor.execute("段落 平方(数值): 返回 数值 * 数值。")
        result = self.executor.execute("平方(5)")
        self.assertEqual(result, 25)

    def test_complexity_detection(self):
        """测试复杂度判断"""
        # 简单表达式
        self.assertTrue(self.executor._is_simple("甲 加 5"))
        self.assertTrue(self.executor._is_simple("打印(1)。"))
        self.assertTrue(self.executor._is_simple("[1, 2, 3]"))

        # 复杂代码块
        self.assertFalse(self.executor._is_simple("设 甲 为 3。"))
        self.assertFalse(self.executor._is_simple("段落 测试: 结束。"))
        self.assertFalse(self.executor._is_simple("如果 甲 > 0: 结束。"))

    def test_mixed_execution(self):
        """测试混合执行模式"""
        # 先定义变量（复杂代码，编译执行）
        self.executor.execute("设 数字 为 10。")
        # 然后使用变量（简单表达式，解释执行）
        result = self.executor.execute("数字 加 5")
        self.assertEqual(result, 15)

    def test_environment_isolation(self):
        """测试环境隔离"""
        env1 = Environment()
        env2 = Environment()

        env1.set("甲", 100)
        env2.set("甲", 200)

        self.assertEqual(env1.get("甲"), 100)
        self.assertEqual(env2.get("甲"), 200)

    def test_builtin_functions(self):
        """测试内置函数"""
        # 长
        result = self.executor.execute("长([1, 2, 3])")
        self.assertEqual(result, 3)

        # 首
        result = self.executor.execute("首([1, 2, 3])")
        self.assertEqual(result, 1)

        # 末
        result = self.executor.execute("末([1, 2, 3])")
        self.assertEqual(result, 3)

        # 排序
        result = self.executor.execute("排序([3, 1, 2])")
        self.assertEqual(result, [1, 2, 3])

        # 求和
        result = self.executor.execute("求和([1, 2, 3, 4])")
        self.assertEqual(result, 10)

    def test_arithmetic_operations(self):
        """测试算术运算"""
        result = self.executor.execute("3 加 5")
        self.assertEqual(result, 8)

        result = self.executor.execute("10 减 3")
        self.assertEqual(result, 7)

        result = self.executor.execute("4 乘 5")
        self.assertEqual(result, 20)

        result = self.executor.execute("20 除 4")
        self.assertEqual(result, 5)

    def test_reset(self):
        """测试重置环境"""
        self.executor.execute("设 甲 为 100。")
        self.assertTrue(self.executor.has_function("甲") or self.executor.env.get("甲") == 100)

        self.executor.reset()
        # 重置后环境应该为空
        result = self.executor.execute("甲")
        self.assertIsNone(result)


class TestEnvironment(unittest.TestCase):
    """环境测试"""

    def test_basic_operations(self):
        """测试基本操作"""
        env = Environment()

        # 设置和获取
        env.set("名字", "光明")
        self.assertEqual(env.get("名字"), "光明")

        # 检查存在
        self.assertTrue(env.has("名字"))
        self.assertFalse(env.has("不存在"))

        # 更新
        env.set("名字", "新光明")
        self.assertEqual(env.get("名字"), "新光明")

    def test_function_storage(self):
        """测试函数存储"""
        env = Environment()

        def test_func():
            return 42

        env.set_function("获取答案", test_func)
        self.assertTrue(env.has_function("获取答案"))


def run_all_tests():
    """运行所有测试"""
    print("=== 光明 REPL 执行引擎测试 ===\n")

    if not EXECUTOR_AVAILABLE:
        print(f"⚠️  执行引擎未实现: {EXECUTOR_IMPORT_ERROR}")
        print("\n请先实现 src/repl/executor.py")
        return False

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExecutor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEnvironment))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n=== 测试统计 ===")
    print(f"运行测试数: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ 所有执行引擎测试通过")
    else:
        print("\n❌ 部分测试失败")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)