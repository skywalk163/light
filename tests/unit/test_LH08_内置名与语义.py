# -*- coding: utf-8 -*-
"""T-0197 · LH08 内置层对拍七条验收。

七条缺陷（LH-02/03/04/07/08/11/14）各一个独立用例，全部跑在 legacy 后端
（LightParser + PythonCodeGenerator，与 tests/test_lpd_016_判型族.py 同 harness）。
每条用例只断言该条自己的口径；存量回归项（是空语义/范围长度/不传 key 的排序）
一并钉死，防止修复时把老行为改坏。
"""
import contextlib
import io
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _run(src: str) -> str:
    module = LightParser().parse(src)
    py = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
        module, is_main=True)
    buf = io.StringIO()
    g = {'__name__': '__main__', '__file__': os.path.join(_ROOT, 'tests', 'lh08.light')}
    with contextlib.redirect_stdout(buf):
        exec(compile(py, '<lh08>', 'exec'), g, g)
    return buf.getvalue()


def _lines(src: str):
    return [ln.strip() for ln in _run(src).strip().splitlines()]


def _src(body: str) -> str:
    """把用例体包进 段落 主 并调用。"""
    return "段落 主:\n" + body + "\n\n主()\n"


# ── 1. LH-08：是数字 = 数字值 或 单个数字字符 ─────────────────────────────
_C1 = _src(
    "  打印 是数字(\"1\")\n"
    "  打印 是数字(1)\n"
    "  打印 是数字(\"x\")\n"
)

# ── 2. LH-07：试转整数 不抛异常，转不了返回默认 ──────────────────────────
_C2 = _src(
    "  打印 试转整数(\"x\") == 空\n"
    "  打印 试转整数(\"-3\") == -3\n"
    "  打印 试转整数(\"12 \") == 12\n"
)

# ── 3. LH-02：皆空 宽口径；是空 语义不许改 ───────────────────────────────
_C3 = _src(
    "  打印 皆空([])\n"
    "  打印 皆空({})\n"
    "  打印 是空(\"\")\n"
)

# ── 4. LH-03：字典取值 缺键/空值都回落默认；字典获取 仍区分 ──────────────
_C4 = _src(
    "  设 典 为 {\"owner\": 空}\n"
    "  打印 字典取值(典, \"owner\", \"无主\") == \"无主\"\n"
    "  打印 字典获取(典, \"owner\", \"无主\") == 空\n"
)

# ── 5. LH-11：去空白 别名真实可用；反转 返回列表；范围 长度回归 ──────────
_C5 = _src(
    "  打印 去空白(\"  a  \") == \"a\"\n"
    "  打印 是列表(反转([1, 2]))\n"
    "  打印 长(范围(1, 5)) == 4\n"
)

# ── 6. LH-14：字节长度 按 UTF-8 真实字节数 ──────────────────────────────
_C6 = _src(
    "  打印 字节长度(\"中文\") == 6\n"
    "  打印 字节长度(\"abc\") == 3\n"
)

# ── 7. LH-04：排序列表 收段落 key；不传 key 行为不变 ──────────────────────
_C7 = (
    "段落 取编号(卡):\n"
    "  返回 卡[\"n\"]\n"
    "段落 主:\n"
    "  设 结果 为 排序列表([{\"n\": 3}, {\"n\": 1}], 假, 取编号)\n"
    "  打印 结果[0] == {\"n\": 1}\n"
    "  打印 结果[1] == {\"n\": 3}\n"
    "  打印 排序列表([3, 1]) == [1, 3]\n"
    "\n"
    "主()\n"
)


class TestLH08是数字:
    def test_three_way(self):
        out = _lines(_C1)
        assert out[0] == 'True', out   # 单数字字符
        assert out[1] == 'True', out   # 数字值
        assert out[2] == 'False', out  # 非数字字符


class TestLH07试转整数:
    def test_no_throw_and_default(self):
        out = _lines(_C2)
        assert out[0] == 'True', out    # 转不了 -> 空
        assert out[1] == 'True', out    # "-3" -> -3
        assert out[2] == 'True', out    # "12 " -> 12（前导/尾随空白）


class TestLH02皆空:
    def test_wide_empty_but_empty_unchanged(self):
        out = _lines(_C3)
        assert out[0] == 'True', out   # 空列表
        assert out[1] == 'True', out   # 空字典
        assert out[2] == 'True', out   # 是空("") 仍为真


class TestLH03字典取值:
    def test_missing_or_null_falls_back_but_get_keeps_python(self):
        out = _lines(_C4)
        assert out[0] == 'True', out   # 值为空 -> 默认
        assert out[1] == 'True', out   # 字典获取 仍返回 空


class TestLH11去空白反转:
    def test_alias_real_and_reversed_is_list(self):
        out = _lines(_C5)
        assert out[0] == 'True', out   # 去空白("  a  ") == "a"
        assert out[1] == 'True', out   # 是列表(反转([1,2]))
        assert out[2] == 'True', out   # 长(范围(1,5)) == 4 回归


class TestLH14字节长度:
    def test_utf8_byte_count(self):
        out = _lines(_C6)
        assert out[0] == 'True', out   # "中文" -> 6 字节
        assert out[1] == 'True', out   # "abc" -> 3 字节


class TestLH04排序key:
    def test_key_para_and_no_key_unchanged(self):
        out = _lines(_C7)
        assert out[0] == 'True', out   # 首项 {"n":1}
        assert out[1] == 'True', out   # 次项 {"n":3}
        assert out[2] == 'True', out   # 不传 key：[3,1] -> [1,3]


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
