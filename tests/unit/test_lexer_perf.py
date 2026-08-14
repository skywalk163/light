# -*- coding: utf-8 -*-
"""
光明词法分析器性能测试

测试词法分析器的性能表现
"""

import sys
import os
import time
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


def generate_test_code(num_lines: int = 10000) -> str:
    """生成指定行数的测试代码

    Args:
        num_lines: 生成的代码行数

    Returns:
        生成的测试代码字符串
    """
    lines = []
    templates = [
        "设甲为三。",
        "设乙为五。",
        "打印 甲 加 乙。",
        "如果 甲 大于 乙：",
        "    打印 甲。",
        "否则：",
        "    打印 乙。",
        "遍历 从 一 至 十：",
        "    打印 当前数。",
        "《计算阶乘》段 数：",
        "    如果 数 小于等于 一：",
        "        返回 一。",
        "    返回 数 乘 计算阶乘 数减一。",
        "设列表为[一, 二, 三, 四, 五]。",
        "设字典为《键一》: 100, 《键二》: 200。",
        "打印\"你好，世界！\"。",
        "设 结果 为 甲 加 乙 乘 三。",
    ]

    for i in range(num_lines):
        template = templates[i % len(templates)]
        lines.append(template)

    return '\n'.join(lines)


class TestLexerPerformance(unittest.TestCase):
    """词法分析器性能测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from lexer import Lexer
            cls.Lexer = Lexer
        except ImportError as e:
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def test_lexer_performance_10000_lines(self):
        """测试 10000 行代码词法分析性能

        perf 预算（秒）可通过环境变量 LEXER_PERF_LIMIT 覆盖，默认 2.0：
        - 本地开发（快速机器）保持严格 2.0s 预算，方便第一时间发现回退；
        - CI 在较慢的 runner（如 FreeBSD host）上通过 LEXER_PERF_LIMIT 放宽到实测值+余量，
          避免平台差异误伤合入门禁，同时仍能在严重回退（如 O(n^2)）时失败。
        """
        test_code = generate_test_code(10000)
        lexer = self.Lexer(test_code)

        start_time = time.perf_counter()
        tokens = lexer.tokenize()
        end_time = time.perf_counter()

        elapsed = end_time - start_time

        limit = float(os.environ.get("LEXER_PERF_LIMIT", "2.0"))

        self.assertGreater(len(tokens), 0, "词法分析未生成任何 token")
        self.assertLess(elapsed, limit,
                        f"词法分析耗时 {elapsed:.4f} 秒，超过 {limit:.1f} 秒限制")

        print(f"\n[性能测试] 10000 行代码词法分析耗时: {elapsed:.4f} 秒")
        print(f"[性能测试] 生成 Token 数量: {len(tokens)}")
        print(f"[性能测试] 每秒处理行数: {10000 / elapsed:.0f} 行/秒")

    def test_lexer_correctness_smoke(self):
        """性能测试前的正确性冒烟测试"""
        test_code = "设甲为三。打印 甲 加 五。"
        lexer = self.Lexer(test_code)
        tokens = lexer.tokenize()

        token_values = [t.value for t in tokens]

        self.assertIn('设', token_values)
        self.assertIn('为', token_values)
        self.assertIn(3, token_values)
        self.assertIn('打印', token_values)
        self.assertIn('加', token_values)
        self.assertIn(5, token_values)


if __name__ == '__main__':
    unittest.main(verbosity=2)
