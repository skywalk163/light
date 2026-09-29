# -*- coding: utf-8 -*-
"""L-023 行尾运算符续行回归（R100 路 B 重裁定）。

裁定沿革
--------
LP-D-006（第一版）：parser 层 `_skip_implicit_continuation` 实现续行时吞掉
续行行 INDENT、打断块结构，遂裁定「报错优先」——行尾运算符续行编译期报错。

R100 路 B（第二版，现行）：改为**词法层软续行**——行尾是二元运算符时不发射
NEWLINE，续行行前导缩进不参与层级计算（不发 INDENT/DEINDENT）。
块结构从原理上不可能被打断，第一版裁定的缺陷前提被消除，
故恢复与 Python 隐式续行一致的语义：**续行合法**。

反跑判据
--------
· 撤掉 lexer.py 换行发射处的 `_line_ends_with_binary_op` 软续行分支 →
  用例 1（行尾加号续行）重新报语法错变红。
"""
import io
import os
import sys
import types
import contextlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from parser_core import ParseError  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _run(source: str) -> str:
    module = LightParser().parse(source)
    py_code = PythonCodeGenerator().generate(module, is_main=False)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd006>', 'exec'), namespace)
    return buf.getvalue()


class Test行尾续行合法:
    def test_行尾加号续行_跨行拼接正确(self):
        """LP-D-006 第一版的原始缺陷形态：续行后后续语句必须留在函数体内。"""
        src = (
            "段落 主:\n"
            "  设 负载 为 \"a\" +\n"
            "        \"b\" +\n"
            "        \"c\"\n"
            "  打印 负载\n"
            "\n"
            "主()\n"
        )
        assert _run(src).strip() == 'abc'

    def test_行尾加上续行(self):
        src = (
            "段落 主:\n"
            "  返回 \"a\" 加上\n"
            "  \"b\"\n"
            "\n"
            "打印 主()\n"
        )
        assert _run(src).strip() == 'ab'

    def test_续行后续语句不漂移(self):
        """原缺陷：续行吞 INDENT 后续语句被顶出函数体、变量未绑定。"""
        src = (
            "段落 主:\n"
            "  设 负载 为 \"a\" +\n"
            "        \"b\"\n"
            "  打印 负载\n"
            "  打印 \"尾部\"\n"
            "\n"
            "主()\n"
        )
        assert _run(src).splitlines() == ['ab', '尾部']

    def test_三段连加续行(self):
        src = (
            "段落 主:\n"
            "  返回 1 加上\n"
            "  2 加上\n"
            "  3\n"
            "\n"
            "打印 主()\n"
        )
        assert _run(src).strip() == '6'

    def test_续行行间空行注释不中断(self):
        src = (
            "段落 主:\n"
            "  返回 \"a\" 加上\n"
            "  # 注释行\n"
            "\n"
            "  \"b\"\n"
            "\n"
            "打印 主()\n"
        )
        assert _run(src).strip() == 'ab'


class Test对照_合法写法不受影响:
    def test_分步拼接仍正常(self):
        src = (
            "段落 主:\n"
            "  设 串 为 \"a\"\n"
            "  设 串 为 串 + \"b\"\n"
            "  设 串 为 串 + \"c\"\n"
            "  打印 串\n"
            "\n"
            "主()\n"
        )
        assert _run(src).strip() == 'abc'

    def test_括号内跨行仍正常(self):
        src = (
            "段落 主:\n"
            "  设 表 为 [\"甲\": 1,\n"
            "        \"乙\": 2]\n"
            "  打印 字符串(表[\"乙\"])\n"
            "\n"
            "主()\n"
        )
        assert _run(src).strip() == '2'

    def test_括号内行尾加号续行仍正常(self):
        src = (
            "段落 主:\n"
            "  设 串 为 (\"a\" +\n"
            "        \"b\")\n"
            "  打印 串\n"
            "\n"
            "主()\n"
        )
        assert _run(src).strip() == 'ab'

    def test_单行表达式不受影响(self):
        src = "段落 主:\n  设 串 为 \"a\" + \"b\" + \"c\"\n  打印 串\n\n主()\n"
        assert _run(src).strip() == 'abc'

    def test_无运算符行尾仍是语句边界(self):
        """行尾没有运算符时不得吞并下一行（软续行只由运算符触发）。"""
        src = (
            "段落 主:\n"
            "  设 甲 为 1\n"
            "  设 乙 为 2\n"
            "  打印 甲\n"
            "  打印 乙\n"
            "\n"
            "主()\n"
        )
        assert _run(src).splitlines() == ['1', '2']
