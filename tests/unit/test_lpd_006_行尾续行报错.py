# -*- coding: utf-8 -*-
"""LP-D-006 回归：行尾运算符续行编译期报错（LP-D 批次 路2）。

缺陷回顾
--------
`设 负载 为 "a" +\\n "b" +\\n "c"` 编译器不报语法错，但解析器吞掉续行行的
INDENT，段落体块结构被打断：赋值留在函数体内、后续 `打印 负载` 被顶到
模块层执行 → `name '负载' is not defined`，且报错行号漂到无关后继行。

修复口径（任务书 路2 验收 1，口径裁定「报错优先」）
------------------------------------------------
行尾运算符续行在编译期（解析层）直接报语法错，定位到行尾运算符所在行：
「不支持用行尾运算符续行…请改用分步赋值或把表达式包进括号」。
分步拼接与括号内跨行不受影响（对照用例必须通过）。

反跑判据
--------
· 撤掉 parser_expr.py `_skip_implicit_continuation` 的深度 0 拦截 →
  用例 1 变红（静默通过、变量未绑定）。
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


class Test行尾续行报错:
    def test_行尾加号续行_编译期报错定位准确(self):
        src = (
            "段落 主:\n"
            "  设 负载 为 \"a\" +\n"
            "        \"b\" +\n"
            "        \"c\"\n"
            "  打印 负载\n"
            "\n"
            "主()\n"
        )
        with pytest.raises(ParseError) as ei:
            LightParser().parse(src)
        msg = str(ei.value)
        assert '不支持用行尾运算符' in msg
        assert '第 2 行' in msg          # 行尾运算符所在行（源码行 2）
        assert '分步赋值' in msg          # 指路：分步或括号
        assert '括号' in msg

    def test_行尾加上续行_同样报错(self):
        src = "返回 \"a\" 加上\n\"b\"\n"
        with pytest.raises(ParseError) as ei:
            LightParser().parse(src)
        assert '不支持用行尾运算符' in str(ei.value)

    def test_不再静默丢绑定(self):
        """老缺陷形态回归哨兵：修复前该源码解析成功但 负载 未绑定到正文。"""
        src = (
            "段落 主:\n"
            "  设 负载 为 \"a\" +\n"
            "        \"b\"\n"
            "  打印 负载\n"
            "\n"
            "主()\n"
        )
        with pytest.raises(ParseError):
            LightParser().parse(src)


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
        """括号深度 > 0 的跨行表达式是合法语法（L-023 括号腿），必须保留。"""
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
