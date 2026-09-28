# -*- coding: utf-8 -*-
"""
LP-D-001 回归测试：字符串花括号转义归一。

约束（来自 lightplugin/语言缺陷反馈.md LP-D-001）：
- \\{ 产物为 {，}} 产物为 }，\\} 产物为 }，{{ 产物为 {；不残留反斜杠/双花括号。
- {变量} 插值特性保持不变。
- 三后端意识：这里对 transpile 腿（PythonCodeGenerator）做端到端运行验证。
"""
import io
import sys
import os
import contextlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run(source):
    """编译光明源码并执行，返回标准输出文本。"""
    parser = LightParser()
    module = parser.parse(source)
    py = PythonCodeGenerator().generate(module)
    buf = io.StringIO()
    g = {'__name__': '__main__'}
    with contextlib.redirect_stdout(buf):
        exec(compile(py, '<lpd001>', 'exec'), g, g)
    return buf.getvalue()


class TestLpd001BraceEscape:
    def test_backslash_escape_normalizes(self):
        out = _run('设 s 为 "a\\{x\\}"。\n打印 s。\n')
        assert out.strip() == 'a{x}', repr(out)

    def test_double_brace_normalizes(self):
        out = _run('设 s 为 "a{{x}}"。\n打印 s。\n')
        assert out.strip() == 'a{x}', repr(out)

    def test_closing_brace_escapes(self):
        out = _run('设 s 为 "a\\}b"。\n打印 s。\n')
        assert out.strip() == 'a}b', repr(out)
        out = _run('设 s 为 "a}}b"。\n打印 s。\n')
        assert out.strip() == 'a}b', repr(out)

    def test_interpolation_unchanged(self):
        out = _run('设 名字 为 "小明"。\n设 s 为 "你好 {名字}"。\n打印 s。\n')
        assert out.strip() == '你好 小明', repr(out)

    def test_mixed_interpolation_and_literal_brace(self):
        # 插值 + 转义字面花括号同串
        out = _run(
            '设 名字 为 "小明"。\n'
            '设 s 为 "嗨 {名字} 段\\{x\\}尾"。\n'
            '打印 s。\n'
        )
        assert out.strip() == '嗨 小明 段{x}尾', repr(out)

    def test_css_literal(self):
        out = _run('设 s 为 "body\\{color:red\\}"。\n打印 s。\n')
        assert out.strip() == 'body{color:red}', repr(out)


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
