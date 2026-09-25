# -*- coding: utf-8 -*-
"""
测试光明代码格式化器（R97 安全子集契约）

R97 起，格式化器只做"绝不改变语义"的空白安全变换：
  - 统一换行符为 \\n；
  - 去除每行行尾空白；
  - 折叠 3+ 连续空行为 2 个；
  - 去除文件首尾多余空行；
  - 确保文件以单个换行结尾。

由于 光明 是缩进敏感语言、块结构由"每行缩进 + 行内 token"决定，
而本格式化器对二者逐行精确保留，因此**产物解析结果与输入必然一致**——
这正是 R97 根除 R96-KI-01（补冒号 / 重排缩进破坏语义）的核心保证。

测试覆盖：
- 空白安全变换（行尾空白、空行折叠、换行规范、末尾换行）
- 幂等性（format(format(x)) == format(x)）
- 不变量：非空前导去空白行序列与缩进在格式化前后完全一致（证明无语义改变）
- check() 仅报告空白 / 空行差异
- 便捷函数 format_code / check_format
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from formatter.light_formatter import LightFormatter, format_code, check_format


# 一条"语义关键"的嵌套闭包代码：任何缩进/冒号改动都会破坏它
NESTED = """# 嵌套段落最小测试
段落 外层(x):
  段落 内层(y):
    返回 x + y
  返回 内层(10)

打印 外层(5)
"""


class TestLightFormatterSafe:
    """测试安全子集的 LightFormatter"""

    def setup_method(self):
        self.fmt = LightFormatter(indent_size=4, max_line_length=80)

    # ------------------------------------------------------------------
    # 行尾空白去除
    # ------------------------------------------------------------------
    def test_trailing_whitespace(self):
        source = "段落 测试():\n    打印(\"hello\")   \n"
        expected = "段落 测试():\n    打印(\"hello\")\n"
        assert self.fmt.format(source) == expected

    # ------------------------------------------------------------------
    # 空行折叠（3+ → 2）
    # ------------------------------------------------------------------
    def test_blank_lines_collapse(self):
        # 源文件含 4 个连续空行，应折叠为 2 个
        source = "段落 函1():\n    打印(1)\n\n\n\n\n段落 函2():\n    打印(2)\n"
        expected = "段落 函1():\n    打印(1)\n\n\n段落 函2():\n    打印(2)\n"
        assert self.fmt.format(source) == expected

    def test_blank_lines_kept_within_two(self):
        # 2 个连续空行应原样保留
        source = "段落 函1():\n    打印(1)\n\n段落 函2():\n    打印(2)\n"
        expected = "段落 函1():\n    打印(1)\n\n段落 函2():\n    打印(2)\n"
        assert self.fmt.format(source) == expected

    # ------------------------------------------------------------------
    # 换行规范（CRLF / CR → LF 内部归一；CRLF 还原由 run_formatter 负责）
    # ------------------------------------------------------------------
    def test_normalize_line_endings(self):
        source = "段落 主():\r\n    打印(1)\r\n"
        out = self.fmt.format(source)
        assert '\r' not in out
        assert out == "段落 主():\n    打印(1)\n"

    # ------------------------------------------------------------------
    # 末尾换行保证
    # ------------------------------------------------------------------
    def test_trailing_newline(self):
        assert self.fmt.format("段落 主():\n    打印(1)") == "段落 主():\n    打印(1)\n"
        # 空文件返回空串
        assert self.fmt.format("") == ""
        assert self.fmt.format("\n\n") == ""

    # ------------------------------------------------------------------
    # 幂等性
    # ------------------------------------------------------------------
    def test_idempotent(self):
        messy = "段落 主():\n    打印(1)   \n\n\n\n"
        once = self.fmt.format(messy)
        twice = self.fmt.format(once)
        assert once == twice

    # ------------------------------------------------------------------
    # 不变量：非空前导去空白行的序列与缩进完全一致（证明无语义改变）
    # ------------------------------------------------------------------
    def _content_lines(self, text):
        """返回 [(缩进宽度, 去尾空白内容), ...] 仅含非空行。"""
        out = []
        for line in text.split('\n'):
            s = line.rstrip()
            if s == '':
                continue
            indent = len(line) - len(line.lstrip())
            out.append((indent, s))
        return out

    def test_invariant_preserves_indent_and_tokens(self):
        # 用嵌套闭包代码验证：格式化前后非空行的(缩进,内容)序列必须逐条相等
        original = NESTED
        formatted = self.fmt.format(original)
        assert self._content_lines(original) == self._content_lines(formatted), (
            "格式化改变了缩进或行内 token —— 这会破坏 光明 的块结构！\n"
            f"原: {self._content_lines(original)}\n格: {self._content_lines(formatted)}"
        )

    def test_no_spurious_colon_on_return(self):
        # R96-KI-01 复现：'返回 x + y' 绝不能被补成 '返回 x + y：'
        formatted = self.fmt.format(NESTED)
        assert "返回 x + y：" not in formatted
        assert "返回 x + y:" not in formatted
        # 原有合法冒号（段落定义行）必须保留
        assert "段落 外层(x):" in formatted
        assert "段落 内层(y):" in formatted

    def test_nested_closure_is_parse_preserving(self):
        # 端到端安全证明：行内容与缩进均保留 ⇒ 解析一致。
        # 这里用不变量断言替代真实编译器调用（避免测试耦合编译器实现）。
        src_lines = self._content_lines(NESTED)
        out_lines = self._content_lines(self.fmt.format(NESTED))
        assert src_lines == out_lines

    # ------------------------------------------------------------------
    # check() 仅报告空白 / 空行差异
    # ------------------------------------------------------------------
    def test_check_reports_only_whitespace(self):
        clean = "段落 主():\n    打印(1)\n"
        assert self.fmt.check(clean) == []
        messy = "段落 主():\n    打印(1)   \n\n\n"
        issues = self.fmt.check(messy)
        assert isinstance(issues, list)
        # 差异只应是行尾空白 / 空行，不应触碰带代码的行内容
        for issue in issues:
            assert issue['original'].rstrip() == issue['formatted'].rstrip(), \
                "check 报告了代码行内容差异，说明格式化改变了语义！"

    # ------------------------------------------------------------------
    # 便捷函数
    # ------------------------------------------------------------------
    def test_format_code_function(self):
        assert "段落 测试()" in format_code("段落 测试():\n    打印(1)\n")

    def test_check_format_function(self):
        assert isinstance(check_format("段落 测试():\n    打印(1)\n"), list)

    # ------------------------------------------------------------------
    # 已合规代码保持不变
    # ------------------------------------------------------------------
    def test_already_clean_unchanged(self):
        clean = "段落 测试():\n    如果 真:\n        打印(\"a\")\n    否则:\n        打印(\"b\")\n"
        assert self.fmt.format(clean) == clean
