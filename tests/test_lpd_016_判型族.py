# -*- coding: utf-8 -*-
"""判型族名实对齐回归（T-0197 · LH-08 反转版）。

沿革
--------------------------------------------------------------------
- LP-D-016（旧）：用户关键字 `是数字` = 是数值（int/float，排 bool），字符判定走
  `是数字符`。该裁决把 `是数字("7")` 固化为 False。
- T-0197 · LH-08（P0 命名层不兼容变更，2026-10-29）：推翻 LP-D-016。用户关键字
  `是数字` 改回宽松谓词——int/float（排 bool）**或** 单个数字字符（str.isdigit，
  len==1 守卫）为真；`是数字符` 是 `是数字` 的等价别名；判「值是否为数值类型」专用
  `是数值`。于是 `是数字("7")` 由 False 翻转为 True，`是数字(1)`/`是数字("1")` 为真、
  `是数字("x")` 为假。本套随此反转更新，迁移口径见仓库 CHANGELOG。

反跑判据
--------------------------------------------------------------------
· 删掉 builtin_map 的 `是数字符` → 用例 5/6/7 变红（NameError）；
· 把 builtin_map 的 `是数字` 目标从 `是数字` 改回 `是数值` → 用例 1c 变红。
"""
import contextlib
import io
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _run(src: str) -> str:
    """用 legacy 后端编译并整段执行（产物自带 _light_builtin 引导），返回 stdout。"""
    module = LightParser().parse(src)
    py = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
        module, is_main=True)
    buf = io.StringIO()
    g = {'__name__': '__main__', '__file__': os.path.join(_ROOT, 'tests', 'lpd016.light')}
    with contextlib.redirect_stdout(buf):
        exec(compile(py, '<lpd016>', 'exec'), g, g)
    return buf.getvalue()


def _lines(src: str):
    return [ln.strip() for ln in _run(src).strip().splitlines()]


# 用例 1~4：`是数字` = 是数值（int/float，排除 bool）—— 现状固化，不许回退成字符判定。
_NUMERIC = (
    "段落 主:\n"
    "  打印 是数字(7)\n"
    "  打印 是数字(3.14)\n"
    "  打印 是数字(\"7\")\n"
    "  打印 是数字(真)\n"
    "  打印 是数字(空)\n"
    "\n"
    "主()\n"
)

# 用例 5~7：`是数字符` = str.isdigit 字符判定 —— 修复前 NameError（红），修复后通过（绿）。
_CHAR_DIGIT = (
    "段落 主:\n"
    "  打印 是数字符(\"7\")\n"
    "  打印 是数字符(\"a\")\n"
    "  打印 是数字符(\"7a\")\n"
    "\n"
    "主()\n"
)


class Test是数字_宽松谓词:
    def test_int_float_digitchar_true_bool_none_false(self):
        out = _lines(_NUMERIC)
        assert out[0] == 'True', out    # 整数
        assert out[1] == 'True', out    # 浮点
        assert out[2] == 'True', out   # 单数字字符（T-0197 由旧 False 翻转）
        assert out[3] == 'False', out   # bool 排除
        assert out[4] == 'False', out   # 空不是数字


class Test是数字符_字符判定:
    def test_digit_string_true_letter_and_mixed_false(self):
        out = _lines(_CHAR_DIGIT)
        assert out[0] == 'True', out    # "7" 全数字字符
        assert out[1] == 'False', out   # "a" 非数字
        assert out[2] == 'False', out   # "7a" 不全是数字字符

    def test_是数字符_映射到是数字实现(self):
        # 守卫：确认 builtin_map 把 `是数字符` 指向 Python 侧已有的 str.isdigit 真身
        # `_light_builtin.是数字`，而不是新造空壳。
        module = LightParser().parse('段落 主:\n  打印 是数字符("7")\n主()\n')
        py = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
            module, is_main=True)
        assert '_light_builtin.是数字(' in py, py
        assert '是数字符(' not in py, py  # 关键字已被映射，不再裸发射


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
