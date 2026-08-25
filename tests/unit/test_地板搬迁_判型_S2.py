# -*- coding: utf-8 -*-
"""地板搬迁差分测试（第九轮 S2 · B 路判型组）：`stdlib/内置核心判型.light` vs Python 原版。

被测对象是 `stdlib/内置核心判型.light` 的 9 个段落，对齐 `stdlib/builtins.py:746-788`
的 9 个 Python 版判型函数（是整数/是浮点/是字符串/是列表/是字典/是空/是字母/是数字/是空白）。

为什么写成差分测试而不是各写一堆期望值：
  搬迁类改动的风险不是「新实现有 bug」，而是「新实现的口径悄悄变宽或变窄」。
  逐条对跑同一个输入矩阵，是唯一能把「口径漂移」暴露成具体某条参数红的做法。

三条口径分水岭（每条都有专门的用例，改坏任一条都会有具体断言红）：
  1. `是整数` 用的是 isinstance 口径，不是 `type(值) == int`。
     `class 我的整数(int)` 的实例 isinstance 为真、type 相等为假 —— 参数 id `intsub`
     就是抓「用 类型(值) == 类型(1) 冒充 isinstance」这种错译的。
  2. `是整数` 必须先短路 bool：`True` 在 Python 里 isinstance(_, int) 为真，
     Python 版靠 `and not isinstance(值, bool)` 排除，光明版靠两段式排除。
  3. `是空` 的光明版写 `类型(值) == 类型(空)`，等价于 `值 is None` 而**不等价于**
     `值 == 空`：`test_是空不许退化成相等比较` 用一个 `__eq__` 恒返回 True 的对象
     把这两者分开 —— 那种对象 `== None` 为真，但它不是 None。

另有一条锚：`test_Python原版口径与本文件的oracle表一致` 直接加载 `stdlib/builtins.py`
比对本文件内联的 oracle。这样即使日后 builtins.py 被接线到光明实现（分子计入
tools/ci/floor_bootstrap.py 的地板自举率），本文件的 oracle 仍是独立的第三方口径，
差分测试不会退化成「自己和自己比」的同义反复。
"""
import importlib
import importlib.util
import math
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402  （必须在 sys.path 就位之后）

_light_import_hook.install([_STDLIB])

光明 = importlib.import_module("内置核心判型")


# ── oracle 表：逐字抄自 stdlib/builtins.py:746-788 ────────────────────────────
# 内联而不是 import：见模块 docstring 最后一段（防止接线后自己和自己比）。
def _oracle_是整数(值):
    return isinstance(值, int) and not isinstance(值, bool)


def _oracle_是浮点(值):
    return isinstance(值, float)


def _oracle_是字符串(值):
    return isinstance(值, str)


def _oracle_是列表(值):
    return isinstance(值, list)


def _oracle_是字典(值):
    return isinstance(值, dict)


def _oracle_是空(值):
    return 值 is None


def _oracle_是字母(字符):
    return str.isalpha(字符)


def _oracle_是数字(字符):
    return str.isdigit(字符)


def _oracle_是空白(字符):
    return str.isspace(字符)


判型段落 = {
    "是整数": _oracle_是整数,
    "是浮点": _oracle_是浮点,
    "是字符串": _oracle_是字符串,
    "是列表": _oracle_是列表,
    "是字典": _oracle_是字典,
    "是空": _oracle_是空,
}

字符段落 = {
    "是字母": _oracle_是字母,
    "是数字": _oracle_是数字,
    "是空白": _oracle_是空白,
}


class 我的整数(int):
    """isinstance(x, int) 为真、type(x) == int 为假 —— 判型口径的分水岭之一。"""


class 相等恒真:
    """`__eq__` 恒返回 True：`x == None` 为真，但 x 不是 None。"""

    def __eq__(self, 其他):
        return True

    def __hash__(self):
        return 0


# ── 输入矩阵（6 个判型段落每个都跑全矩阵）─────────────────────────────────────
输入矩阵 = [
    ("int_0", 0),
    ("int_1", 1),
    ("int_neg1", -1),
    ("bool_True", True),
    ("bool_False", False),
    ("float_1_5", 1.5),
    ("float_nan", float("nan")),
    ("float_inf", float("inf")),
    ("str_empty", ""),
    ("str_a", "a"),
    ("str_cjk", "中"),
    ("list_empty", []),
    ("list_one", [1]),
    ("dict_empty", {}),
    ("dict_one", {"k": 1}),
    ("none", None),
    ("tuple_1_2", (1, 2)),
    ("set_empty", set()),
    ("bytes_x", b"x"),
    ("int_subclass", 我的整数(7)),
    ("eq_always_true", 相等恒真()),
]

字符矩阵 = [
    ("chr_a", "a"),
    ("chr_1", "1"),
    ("chr_space", " "),
    ("chr_tab", "\t"),
    ("chr_empty", ""),
    ("str_ab", "ab"),
    ("str_a1", "a1"),
    ("chr_cjk", "中"),
    ("chr_vulgar_half", "\u00bd"),      # ½：isdigit False / isnumeric True
    ("chr_roman_four", "\u2163"),       # Ⅳ：isdigit False / isnumeric True
    ("chr_superscript_2", "\u00b2"),    # ²：isdigit True / isdecimal False
    ("chr_arabic_indic_5", "\u0665"),   # ٥：isdigit True
]

非字符串入参 = [
    ("arg_int", 1),
    ("arg_none", None),
    ("arg_list", ["a"]),
]


def test_被测模块由light加载():
    """搬迁的前提：跑的必须是 .light，不是隔壁某个 .py。"""
    assert getattr(光明, "__light_source__", "").endswith(".light")
    assert os.path.basename(光明.__light_source__) == "内置核心判型.light"
    assert getattr(光明, "__file__", "").endswith(".light")


def test_九个段落全部导出且可调用():
    缺 = [名 for 名 in list(判型段落) + list(字符段落) if not callable(getattr(光明, 名, None))]
    assert 缺 == [], "内置核心判型.light 没导出/没定义这些段落：%s" % 缺


@pytest.mark.parametrize("标签,值", 输入矩阵, ids=[t for t, _ in 输入矩阵])
@pytest.mark.parametrize("名字", sorted(判型段落))
def test_判型口径与Python原版逐条一致(名字, 标签, 值):
    原版 = 判型段落[名字]
    期望 = 原版(值)
    实得 = getattr(光明, 名字)(值)
    assert 实得 == 期望, (
        "%s(%s) 口径不一致：Python 原版 %r，光明版 %r" % (名字, 标签, 期望, 实得))
    assert isinstance(实得, bool), (
        "%s(%s) 返回 %r（%s），判型段落必须返回 bool"
        % (名字, 标签, 实得, type(实得).__name__))


@pytest.mark.parametrize("标签,值", 字符矩阵, ids=[t for t, _ in 字符矩阵])
@pytest.mark.parametrize("名字", sorted(字符段落))
def test_字符判型口径与Python原版逐条一致(名字, 标签, 值):
    原版 = 字符段落[名字]
    期望 = 原版(值)
    实得 = getattr(光明, 名字)(值)
    assert 实得 == 期望, (
        "%s(%r) 口径不一致：Python 原版 %r，光明版 %r" % (名字, 值, 期望, 实得))


@pytest.mark.parametrize("标签,值", 非字符串入参, ids=[t for t, _ in 非字符串入参])
@pytest.mark.parametrize("名字", sorted(字符段落))
def test_字符判型对非字符串入参抛同型异常(名字, 标签, 值):
    """`str.isalpha(1)` 抛 TypeError。

    光明版必须写 `str.isalpha(字符)` 这种类方法形态；写成 `字符.isalpha()` 的话
    非 str 入参会抛 AttributeError —— 那是把错误口径改写掉（调用方 except TypeError
    再也接不住），本条把它钉死。
    """
    原版 = 字符段落[名字]
    with pytest.raises(TypeError) as 原版异常:
        原版(值)
    with pytest.raises(TypeError) as 光明异常:
        getattr(光明, 名字)(值)
    assert type(光明异常.value) is type(原版异常.value), (
        "%s(%r)：Python 原版抛 %s，光明版抛 %s（异常型别不同就是改写了错误口径）"
        % (名字, 值, type(原版异常.value).__name__, type(光明异常.value).__name__))


def test_是整数走isinstance口径而不是类型相等():
    """int 子类实例：isinstance 为真、`type(x) == int` 为假。

    这是本组最关键的一条 —— 把 `是整数` 错译成 `类型(值) == 类型(1)` 时，
    全矩阵里只有这条会红。
    """
    x = 我的整数(7)
    assert isinstance(x, int), "前提不成立：我的整数 应当是 int 的子类"
    assert type(x) is not int, "前提不成立：我的整数 的实例 type 不应等于 int"
    assert _oracle_是整数(x) is True, "Python 原版对 int 子类应为 True"
    assert 光明.是整数(x) is True, (
        "光明版对 int 子类判 False —— 它用的是「类型相等」而不是 isinstance，"
        "口径比 Python 原版窄")


def test_是整数必须先短路bool():
    """bool 是 int 的子类；两版都必须把 True/False 判为「不是整数」。"""
    assert 光明.是整数(True) is False
    assert 光明.是整数(False) is False
    assert 光明.是整数(1) is True
    assert 光明.是整数(0) is True
    assert 光明.是整数(1.5) is False


def test_是空不许退化成相等比较():
    """`__eq__` 恒真的对象不许被判成空。

    `值 is None` 与 `值 == None` 的分水岭：光明版写的是 `类型(值) == 类型(空)`
    （类型判断），所以这个对象判 False；一旦被改成 `返回 值 == 空`，它会判 True。
    """
    哨 = 相等恒真()
    assert (哨 == None) is True, "前提不成立：相等恒真.__eq__ 应当恒返回 True"  # noqa: E711
    assert _oracle_是空(哨) is False, "Python 原版用的是 is，不该判成空"
    assert 光明.是空(哨) is False, (
        "光明版把 __eq__ 恒真的对象判成了空 —— 它走的是 `== 空` 而不是类型判断，"
        "口径比 Python 原版宽")
    assert 光明.是空(None) is True


@pytest.mark.parametrize("标签,值", [
    ("int_0", 0), ("str_empty", ""), ("list_empty", []), ("dict_empty", {}),
    ("bool_False", False), ("float_nan", float("nan")), ("set_empty", set()),
], ids=lambda p: p if isinstance(p, str) else repr(p))
def test_是空只认None不认假值(标签, 值):
    """Python 的 `is None` 不是「假值判断」：0/""/[]/{}/False 都不是空。"""
    assert _oracle_是空(值) is False
    assert 光明.是空(值) is False


def test_浮点特值不被判成整数或字符串():
    """nan/inf 是 float：是浮点为真，是整数/是字符串为假（两版一致）。"""
    for 值 in (float("nan"), float("inf"), float("-inf")):
        assert 光明.是浮点(值) is True
        assert 光明.是整数(值) is False
        assert 光明.是字符串(值) is False
    assert math.isnan(float("nan")), "前提：nan 判定可用"


# ── 口径锚：本文件的 oracle 必须真等于 stdlib/builtins.py 现有 Python 版 ────────
def _新装地板():
    """把 stdlib/builtins.py 当独立模块载一份（同 tests/test_pure_light_hook.py:221），
    避免污染 sys.modules 里的真 builtins。"""
    spec = importlib.util.spec_from_file_location(
        "_地板副本_判型S2", os.path.join(_STDLIB, "builtins.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("标签,值", 输入矩阵, ids=[t for t, _ in 输入矩阵])
@pytest.mark.parametrize("名字", sorted(判型段落))
def test_Python原版口径与本文件的oracle表一致(名字, 标签, 值):
    """防 oracle 腐烂：builtins.py 改了口径而本文件没跟上时，这里红。"""
    地板 = _新装地板()
    assert getattr(地板, 名字)(值) == 判型段落[名字](值), (
        "stdlib/builtins.py 的 %s 与本文件 oracle 在 %s 上已分叉，先对齐 oracle"
        % (名字, 标签))


@pytest.mark.parametrize("标签,值", 字符矩阵, ids=[t for t, _ in 字符矩阵])
@pytest.mark.parametrize("名字", sorted(字符段落))
def test_Python原版字符判型与本文件的oracle表一致(名字, 标签, 值):
    地板 = _新装地板()
    assert getattr(地板, 名字)(值) == 字符段落[名字](值), (
        "stdlib/builtins.py 的 %s 与本文件 oracle 在 %r 上已分叉" % (名字, 值))
