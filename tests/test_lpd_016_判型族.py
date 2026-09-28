# -*- coding: utf-8 -*-
"""LP-D-016 回归：判型族名实对齐 —— `是数字`=是数值(int/float)，`是数字符`=str.isdigit 字符判定。

缺陷回顾（lightplugin/语言缺陷反馈.md LP-D-016，team lead 亲测复现）
--------------------------------------------------------------------
1. 光明关键字 `是数字` 的实际语义是「值是否为 int/float 数值类型（排除 bool）」：
   `是数字(7)`→真、`是数字(3.14)`→真、`是数字("7")`→假、`是数字(真)`→假。
   但 `stdlib/内置核心判型.light` 里名为 `是数字` 的段落实现的是 `str.isdigit` 字符判定，
   注释与用户侧关键字**名实相反**——插件作者读注释会把守卫写反，且静默不报错。
2. `stdlib/builtins.py:945-947` 的 docstring 承诺「光明关键字 `是数字符` 映射到 `是数字`
   (str.isdigit)」，但 legacy 后端 `src/code_generator.py` 的 builtin_map 里**根本没注册**
   `是数字符`，于是 `是数字符("7")` 直接 `NameError: name '是数字符' is not defined`。

修复决策（不破坏现有插件）
--------------------------------------------------------------------
保持用户侧关键字 `是数字` = 是数值（int/float，排 bool）——这是 12 个插件已经在用的语义，
不动；新增关键字 `是数字符` = str.isdigit 字符判定，映射到 Python 侧已有的 `_light_builtin.是数字`
（即 `内置核心判型.是数字` 段落，str.isdigit）。不动 `内置核心判型.light` 里的段落名
`是数字`——它被差分测试 tests/unit/test_地板搬迁_判型_S2.py 直接按名引用，改名会破差分校验。

反跑判据
--------------------------------------------------------------------
· 把 code_generator.py builtin_map 里新增的 `是数字符` 一行删掉 → 本套用例 5/6/7 变红
  （NameError: name '是数字符' is not defined）；
· 把 builtin_map 里 `是数字` 的目标从 `是数值` 改回 `是数字` → 用例 1/3/4 变红。
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


class Test是数字_数值语义:
    def test_int_float_true_string_bool_none_false(self):
        out = _lines(_NUMERIC)
        assert out[0] == 'True', out    # 整数
        assert out[1] == 'True', out    # 浮点
        assert out[2] == 'False', out   # 字符串不是数值
        assert out[3] == 'False', out   # bool 排除
        assert out[4] == 'False', out   # 空不是数值


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
