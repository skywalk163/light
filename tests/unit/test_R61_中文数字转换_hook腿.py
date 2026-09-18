# -*- coding: utf-8 -*-
"""R61 任务3 · `中文数字转换.light` 裸名 `去除空格` hook 腿缺口收口（双腿双跑）。

背景
----
`stdlib/中文数字转换.light` 是「零导入」纯光明模块，函数体里调**裸名** `去除空格`
（`stdlib/字符串处理.py:51` 的公开函数，实现即 `s.strip()`）。原生腿早把它与
`去除空白`/`trim`/`strip` 收在同一族（`src/llvm/codegen_typed.py:2655`），但 Python 腿的
`builtin_map`（`src/code_generator.py`）只登记了 `去除空白`，于是 Python import hook
编译出的产物里 `去除空格(...)` 仍是裸名 → 函数一被调用就 `NameError`。
R60 只登记未修（见 `_task3_R60_地板导出与截取族修复.md` §3.3），R61 任务3 补同族映射收口。

同时中招的还有 `stdlib/颜色.light`、`stdlib/格式化.light`、`stdlib/参数解析.light`
共 3 个同款纯光明模块的裸调用点。

用例口径
--------
- **hook 腿**：走 `stdlib/_light_import_hook.py`，把 `.light` 就地编译成 Python 执行，
  与同名 `.py` 参考实现逐值对拍；输入含**首尾空格**（正是 `去除空格` 的作用点）与小数。
  先断言 `__file__` 以 `.light` 结尾，确保跑的真是纯光明实现而不是被 `.py` 顶替。
- **原生腿**：LLVM O0 子进程跑同一组输入，对拍同一份 `.py` 参考实现
  （runner 复用 `tests/unit/test_原生腿_R11B_中文工具.py`，不另造一份）。

判据：两腿都不再 `NameError`，且逐值与 `.py` 参考一致。
"""
import importlib
import importlib.util
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_STDLIB = os.path.join(_ROOT, "stdlib")
for _p in (_ROOT, os.path.join(_ROOT, "src"), _STDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

# 用例：首尾空格触发 去除空格；小数段钉 R60 修好的 `截取` end 语义不回归。
_整数用例 = [
    ("  一百二十三  ", 123),
    ("十二", 12),
    ("  零十二  ", 12),
    ("一万零五", 10005),
]
_浮点用例 = [
    (" 三点一四 ", 3.14),
    ("一百零二点五", 102.5),
    ("零点三", 0.3),
]


def _load_py_ref():
    """同名 .py 参考实现（绕过钩子，拿 Python 原版口径）。"""
    spec = importlib.util.spec_from_file_location(
        "_r61_ref_中文数字转换", os.path.join(_STDLIB, "中文数字转换.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_参考 = _load_py_ref()


@pytest.fixture(scope="module")
def hook腿():
    """Python import hook 腿的 .light 真实现。"""
    _light_import_hook.install([_STDLIB])
    mod = sys.modules.get("中文数字转换")
    if mod is None or not str(getattr(mod, "__file__", "")).endswith(".light"):
        sys.modules.pop("中文数字转换", None)
        mod = importlib.import_module("中文数字转换")
    assert str(mod.__file__).endswith(".light"), f"未走 hook 腿: {mod.__file__}"
    return mod


@pytest.mark.parametrize("中文串, 期望", _整数用例)
def test_hook腿_中文转阿拉伯数字_含首尾空格不NameError(hook腿, 中文串, 期望):
    光 = hook腿.中文转阿拉伯数字(中文串)
    assert 光 == 期望
    assert 光 == _参考.中文转阿拉伯数字(中文串)


@pytest.mark.parametrize("中文串, 期望", _浮点用例)
def test_hook腿_中文转浮点数_含首尾空格不NameError(hook腿, 中文串, 期望):
    光 = hook腿.中文转浮点数(中文串)
    assert abs(光 - 期望) < 1e-9
    assert 光 == _参考.中文转浮点数(中文串)


# ── 原生腿：复用 R11B 的 O0 子进程 runner ─────────────────────────────────

def _load_native_runner():
    p = os.path.join(_HERE, "test_原生腿_R11B_中文工具.py")
    spec = importlib.util.spec_from_file_location("_r61_native_runner", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_原生 = _load_native_runner()
pytestmark = list(_原生.pytestmark)


def test_原生腿_中文数字转换_含首尾空格_对拍():
    src = """从 中文数字转换 导入 中文转阿拉伯数字 中文转浮点数
段落 主:
  输出("A0=" 加上 转字符串(中文转阿拉伯数字("  一百二十三  ")))
  输出("A1=" 加上 转字符串(中文转阿拉伯数字("十二")))
  输出("A2=" 加上 转字符串(中文转阿拉伯数字("  零十二  ")))
  输出("A3=" 加上 转字符串(中文转阿拉伯数字("一万零五")))
  输出("B0=" 加上 转字符串(中文转浮点数(" 三点一四 ")))
  输出("B1=" 加上 转字符串(中文转浮点数("一百零二点五")))
  输出("B2=" 加上 转字符串(中文转浮点数("零点三")))
"""
    out = _原生._native_run(src)
    for i, (s, 期望) in enumerate(_整数用例):
        assert int(out[f"A{i}"]) == 期望 == _参考.中文转阿拉伯数字(s), f"原生腿 中文转阿拉伯数字[{s}]"
    for i, (s, 期望) in enumerate(_浮点用例):
        assert abs(float(out[f"B{i}"]) - 期望) <= 1e-4, f"原生腿 中文转浮点数[{s}]"
        assert abs(float(out[f"B{i}"]) - _参考.中文转浮点数(s)) <= 1e-4, f"原生腿对拍[{s}]"