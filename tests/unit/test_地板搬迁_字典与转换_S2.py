# -*- coding: utf-8 -*-
"""地板自举 S2 · D 路：字典组（8 条）+ 转换组（3 条）差分测试。

对跑双方：
  - 光明版：stdlib/内置核心字典.light、stdlib/内置核心转换.light（由导入钩子编译执行）
  - Python 原版：stdlib/builtins.py 里的同名函数（独立载一份副本，不污染模块表）
每条断言「光明版 == Python 原版 == 手写 oracle 期望值」。三方一致才算搬迁等价：
只比「光明 vs builtins」在 builtins 改成转发后会退化成自比（恒真），所以 oracle
期望值必须独立写死在表里。

本轮实测到的两处静默错译（已在 .light 侧规避，判据留在本文件里守住）：
  1) 裸 `映射[键] = 值` 解析报错；写成 `设 映射[键] 为 值` 才生成下标赋值。
  2) 裸 `捕获 值错误:` 被当成「无类型 + 变量名」，生成 `except Exception as 值错误`
     —— 把 TypeError 一起吞掉。必须写 `捕获 (值错误):` 才生成 `except ValueError:`。
     对应判据：test_转整数_类型错误必须穿透 / test_转浮点_类型错误必须穿透。
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
import _light_import_hook  # noqa: E402

_light_import_hook.install([_STDLIB])

光明字典 = importlib.import_module("内置核心字典")
光明转换 = importlib.import_module("内置核心转换")


def _新装地板():
    """把 stdlib/builtins.py 当独立模块载一份，避免污染其他测试的模块表。"""
    spec = importlib.util.spec_from_file_location(
        "_地板副本_D路", os.path.join(_STDLIB, "builtins.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


地板 = _新装地板()


# ── 0. 两个模块必须真的由 .light 加载 ─────────────────────────────────────────
@pytest.mark.parametrize("模块", [光明字典, 光明转换])
def test_模块来源必须是light(模块):
    assert 模块.__light_source__.endswith(".light"), (
        "%s 不是由 .light 加载的：%r" % (模块.__name__, 模块.__light_source__))
    assert 模块.__file__.endswith(".light")


# ══════════════════════════════════════════════════════════════════════════════
# 字典组
# ══════════════════════════════════════════════════════════════════════════════

def test_字典创建_两版都给出独立空字典():
    光 = 光明字典.字典创建()
    原 = 地板.字典创建()
    assert 光 == {}
    assert 原 == {}
    assert type(光) is dict
    assert type(光) is type(原)
    # 每次调用必须是新对象，不能返回共享的模块级字典
    另一个 = 光明字典.字典创建()
    另一个["x"] = 1
    assert 光 == {}
    assert 另一个 == {"x": 1}


# (用例名, 初值, 键, 值, 期望字典)
_设置表 = [
    ("空字典插入", {}, "a", 1, {"a": 1}),
    ("覆盖已有键", {"a": 1, "b": 2}, "a", 99, {"a": 99, "b": 2}),
    ("键为None", {}, None, 1, {None: 1}),
    ("键为0", {}, 0, "零", {0: "零"}),
    ("键为False", {}, False, "假", {False: "假"}),
    ("False覆盖已有的0", {0: "零"}, False, "假", {0: "假"}),
    ("0覆盖已有的False", {False: "假"}, 0, "零", {False: "零"}),
    ("值为None", {}, "k", None, {"k": None}),
    ("值为0", {}, "k", 0, {"k": 0}),
    ("键为元组", {}, (1, 2), "元组", {(1, 2): "元组"}),
]


@pytest.mark.parametrize("名, 初值, 键, 值, 期望", _设置表,
                         ids=[c[0] for c in _设置表])
def test_字典设置(名, 初值, 键, 值, 期望):
    光 = dict(初值)
    原 = dict(初值)
    光id = id(光)
    原id = id(原)

    光返回 = 光明字典.字典设置(光, 键, 值)
    原返回 = 地板.字典设置(原, 键, 值)

    # ① 返回值必须是 None（Python 版无 return）
    assert 光返回 is None, "字典设置 应返回 None，实得 %r" % (光返回,)
    assert 原返回 is None
    # ② 就地改的是调用方那个对象本身
    assert id(光) == 光id, "字典设置 换了新对象，调用方的字典没被改到"
    assert id(原) == 原id
    # ③ 三方一致
    assert 光 == 期望
    assert 原 == 期望
    assert 光 == 原
    # ④ 键的实际存法也要一致（0 与 False 同键时，留下的键对象是先插入的那个）
    assert list(光.keys()) == list(原.keys())
    assert [type(k) for k in 光.keys()] == [type(k) for k in 原.keys()]


def test_字典设置_0与False在dict里是同一个键():
    光 = 光明字典.字典创建()
    光明字典.字典设置(光, 0, "零")
    光明字典.字典设置(光, False, "假")
    原 = 地板.字典创建()
    地板.字典设置(原, 0, "零")
    地板.字典设置(原, False, "假")
    # 只有一个键，且键对象仍是先插入的 0（int），值被后来的 False 覆盖
    assert 光 == {0: "假"}
    assert 光 == 原
    assert list(光.keys()) == [0]
    assert [type(k) for k in 光.keys()] == [int]
    assert 光明字典.字典键列表(光) == 地板.字典键列表(原)


# (用例名, 初值, 待删键, 期望字典)
_删除表 = [
    ("删已有键", {"a": 1, "b": 2}, "a", {"b": 2}),
    ("删不存在的键静默", {"a": 1}, "zzz", {"a": 1}),
    ("空字典删键静默", {}, "x", {}),
    ("删None键", {None: 1, "a": 2}, None, {"a": 2}),
    ("删0会连带删掉False", {0: "零"}, False, {}),
    ("删False会连带删掉0", {False: "假"}, 0, {}),
    ("值为None的键也能删", {"k": None}, "k", {}),
    ("删最后一个键", {"only": 1}, "only", {}),
]


@pytest.mark.parametrize("名, 初值, 键, 期望", _删除表,
                         ids=[c[0] for c in _删除表])
def test_字典删除(名, 初值, 键, 期望):
    光 = dict(初值)
    原 = dict(初值)
    光id = id(光)
    原id = id(原)

    光返回 = 光明字典.字典删除(光, 键)
    原返回 = 地板.字典删除(原, 键)

    assert 光返回 is None, "字典删除 应返回 None，实得 %r" % (光返回,)
    assert 原返回 is None
    assert id(光) == 光id, "字典删除 换了新对象，调用方的字典没被改到"
    assert id(原) == 原id
    assert 光 == 期望
    assert 原 == 期望
    assert 光 == 原


def test_字典删除_连续删同一个键不抛():
    光 = {"a": 1}
    assert 光明字典.字典删除(光, "a") is None
    assert 光明字典.字典删除(光, "a") is None
    assert 光 == {}
    原 = {"a": 1}
    地板.字典删除(原, "a")
    地板.字典删除(原, "a")
    assert 光 == 原


# (用例名, 字典, 期望键, 期望值, 期望项)
_列表表 = [
    ("空字典", {}, [], [], []),
    ("插入序不是字典序", {"b": 1, "a": 2, "c": 3},
     ["b", "a", "c"], [1, 2, 3], [("b", 1), ("a", 2), ("c", 3)]),
    ("值含None", {"x": None, "y": 0},
     ["x", "y"], [None, 0], [("x", None), ("y", 0)]),
    ("混合键类型", {None: 1, 0: 2, "s": 3},
     [None, 0, "s"], [1, 2, 3], [(None, 1), (0, 2), ("s", 3)]),
    ("重复值", {"a": 7, "b": 7}, ["a", "b"], [7, 7], [("a", 7), ("b", 7)]),
]


@pytest.mark.parametrize("名, 映射, 期望键, 期望值, 期望项", _列表表,
                         ids=[c[0] for c in _列表表])
def test_字典键值项列表(名, 映射, 期望键, 期望值, 期望项):
    assert 光明字典.字典键列表(映射) == 期望键
    assert 光明字典.字典值列表(映射) == 期望值
    assert 光明字典.字典项列表(映射) == 期望项
    assert 光明字典.字典键列表(映射) == 地板.字典键列表(映射)
    assert 光明字典.字典值列表(映射) == 地板.字典值列表(映射)
    assert 光明字典.字典项列表(映射) == 地板.字典项列表(映射)
    # 返回的必须是 list（不是 dict_keys 视图），项必须是元组
    assert type(光明字典.字典键列表(映射)) is list
    assert type(光明字典.字典值列表(映射)) is list
    assert [type(项) for 项 in 光明字典.字典项列表(映射)] == [tuple] * len(期望项)


def test_三个列表函数不改动入参():
    映射 = {"a": 1, "b": 2}
    快照 = dict(映射)
    光明字典.字典键列表(映射)
    光明字典.字典值列表(映射)
    光明字典.字典项列表(映射)
    assert 映射 == 快照


def test_超长字典_1000项保持插入序():
    大 = 光明字典.字典创建()
    for i in range(999, -1, -1):          # 倒序插入，插入序 ≠ 排序
        光明字典.字典设置(大, i, i * 2)
    原大 = 地板.字典创建()
    for i in range(999, -1, -1):
        地板.字典设置(原大, i, i * 2)

    期望键 = list(range(999, -1, -1))
    assert len(大) == 1000
    assert 光明字典.字典键列表(大) == 期望键
    assert 光明字典.字典值列表(大) == [i * 2 for i in 期望键]
    assert 光明字典.字典项列表(大) == [(i, i * 2) for i in 期望键]
    assert 光明字典.字典键列表(大) == 地板.字典键列表(原大)
    assert 大 == 原大
    assert 光明字典.字典包含键(大, 999) is True
    assert 光明字典.字典包含键(大, 1000) is False
    assert 光明字典.字典获取(大, 500, "缺") == 1000

    # 再全删一遍，静默删不存在的键也要一致
    for i in range(1000):
        assert 光明字典.字典删除(大, i) is None
    assert 大 == {}
    assert 光明字典.字典删除(大, 0) is None


# (用例名, 字典, 键, 期望)
_包含表 = [
    ("空字典", {}, "a", False),
    ("键存在", {"a": 1}, "a", True),
    ("键不存在", {"a": 1}, "b", False),
    ("值为None时键仍算存在", {"a": None}, "a", True),
    ("None键存在", {None: 1}, None, True),
    ("None键不存在", {"a": 1}, None, False),
    ("0键存在", {0: 1}, 0, True),
    ("用False查0键", {0: 1}, False, True),
    ("用0查False键", {False: 1}, 0, True),
    ("用1查True键", {True: 1}, 1, True),
    ("字符串0不等于数字0", {0: 1}, "0", False),
]


@pytest.mark.parametrize("名, 映射, 键, 期望", _包含表, ids=[c[0] for c in _包含表])
def test_字典包含键(名, 映射, 键, 期望):
    光 = 光明字典.字典包含键(映射, 键)
    原 = 地板.字典包含键(映射, 键)
    assert 光 is 期望, "字典包含键(%r, %r) 应得 %r，实得 %r" % (映射, 键, 期望, 光)
    assert 光 is 原


# (用例名, 字典, 键, 默认值, 期望)
_获取表 = [
    ("空字典走默认值", {}, "a", "默认", "默认"),
    ("键存在", {"a": 1}, "a", "默认", 1),
    ("键不存在走默认值", {"a": 1}, "b", "默认", "默认"),
    # 下面这条专抓「用 or 默认值 错译 .get」：值为 None 必须拿到 None
    ("值为None拿到None而不是默认值", {"a": None}, "a", "默认", None),
    ("值为0拿到0而不是默认值", {"a": 0}, "a", "默认", 0),
    ("值为空串拿到空串", {"a": ""}, "a", "默认", ""),
    ("值为False拿到False", {"a": False}, "a", "默认", False),
    ("值为空列表拿到空列表", {"a": []}, "a", "默认", []),
    ("默认值为None", {}, "a", None, None),
    ("None键", {None: 7}, None, "默认", 7),
    ("用False取0键", {0: "零"}, False, "默认", "零"),
    ("用0取False键", {False: "假"}, 0, "默认", "假"),
    ("键为元组", {(1, 2): "元组"}, (1, 2), "默认", "元组"),
]


@pytest.mark.parametrize("名, 映射, 键, 默认值, 期望", _获取表,
                         ids=[c[0] for c in _获取表])
def test_字典获取(名, 映射, 键, 默认值, 期望):
    光 = 光明字典.字典获取(映射, 键, 默认值)
    原 = 地板.字典获取(映射, 键, 默认值)
    assert 光 == 期望, "字典获取(%r, %r, %r) 应得 %r，实得 %r" % (
        映射, 键, 默认值, 期望, 光)
    assert type(光) is type(期望)
    assert 光 == 原
    assert type(光) is type(原)


def test_字典获取_不改动入参():
    映射 = {"a": 1}
    assert 光明字典.字典获取(映射, "b", "默认") == "默认"
    assert 映射 == {"a": 1}, "字典获取 不该把默认值写回字典（.get 而不是 .setdefault）"


def test_字典获取_默认参数只在Python侧():
    """默认值不在光明侧写默认参数（负数/默认值解析已知不可用），光明段落收满三个参。

    所以：Python 版可以两参调用，光明版必须三参。两者的可调用面差异记在明处。
    """
    assert 地板.字典获取({"a": 1}, "a") == 1
    assert 地板.字典获取({}, "a") is None
    with pytest.raises(TypeError):
        光明字典.字典获取({"a": 1}, "a")


# 不可哈希键：四个吃「键」的函数两版必须同型报错（都是 TypeError）
_不可哈希用例 = [
    ("字典设置", lambda 模块, 映射: 模块.字典设置(映射, [1, 2], "v")),
    ("字典删除", lambda 模块, 映射: 模块.字典删除(映射, [1, 2])),
    ("字典包含键", lambda 模块, 映射: 模块.字典包含键(映射, [1, 2])),
    ("字典获取", lambda 模块, 映射: 模块.字典获取(映射, [1, 2], "默认")),
]


@pytest.mark.parametrize("名, 调用", _不可哈希用例, ids=[c[0] for c in _不可哈希用例])
def test_不可哈希键两版都抛TypeError(名, 调用):
    with pytest.raises(TypeError) as 光信息:
        调用(光明字典, {"a": 1})
    with pytest.raises(TypeError) as 原信息:
        调用(地板, {"a": 1})
    assert type(光信息.value) is type(原信息.value)
    assert str(光信息.value) == str(原信息.value)


def test_不可哈希键的字典未被改动():
    映射 = {"a": 1}
    with pytest.raises(TypeError):
        光明字典.字典设置(映射, {"不可": "哈希"}, 1)
    assert 映射 == {"a": 1}


# ══════════════════════════════════════════════════════════════════════════════
# 转换组
# ══════════════════════════════════════════════════════════════════════════════

# (用例名, 入参, 期望)
_转整数成功表 = [
    ("普通数字串", "42", 42),
    ("前后空白int接受", " 42 ", 42),
    ("制表换行也算空白", "\t42\n", 42),
    ("正号", "+7", 7),
    ("负号", "-7", -7),
    ("下划线分组", "1_000", 1000),
    ("前导零", "007", 7),
    ("零", "0", 0),
    ("负零", "-0", 0),
    ("全角数字", "４２", 42),
    ("阿拉伯印度数字", "٤٢", 42),
    ("天城文数字", "४२", 42),
    ("超长数字串", "9" * 100, int("9" * 100)),
    ("布尔真", True, 1),
    ("布尔假", False, 0),
    ("浮点截断向零", 1.9, 1),
    ("负浮点截断向零", -1.9, -1),
    ("整数原样", 42, 42),
]


@pytest.mark.parametrize("名, 入参, 期望", _转整数成功表,
                         ids=[c[0] for c in _转整数成功表])
def test_转整数_成功(名, 入参, 期望):
    光 = 光明转换.转整数(入参)
    原 = 地板.转整数(入参)
    assert 光 == 期望, "转整数(%r) 应得 %r，实得 %r" % (入参, 期望, 光)
    assert type(光) is int
    assert 光 == 原
    assert type(光) is type(原)


_转整数失败表 = [
    ("十六进制串应失败", "0x10"),
    ("空串", ""),
    ("纯空白", "   "),
    ("小数串转整数应失败", "1.5"),
    ("nan转整数应失败", "nan"),
    ("inf转整数应失败", "inf"),
    ("字母", "abc"),
    ("千分位逗号", "1,000"),
    ("科学计数串", "1e3"),
    ("中文数字", "四十二"),
    ("下划线位置非法", "_1000"),
    ("尾随小数点", "42."),
]


@pytest.mark.parametrize("名, 入参", _转整数失败表, ids=[c[0] for c in _转整数失败表])
def test_转整数_失败消息逐字一致(名, 入参):
    期望消息 = "无法将 '%s' 转换为整数" % (入参,)
    with pytest.raises(RuntimeError) as 光信息:
        光明转换.转整数(入参)
    with pytest.raises(RuntimeError) as 原信息:
        地板.转整数(入参)
    assert str(光信息.value) == 期望消息
    assert str(原信息.value) == 期望消息
    assert type(光信息.value) is RuntimeError


_转浮点成功表 = [
    ("普通数字串", "42", 42.0),
    ("前后空白", " 42 ", 42.0),
    ("正号", "+7", 7.0),
    ("负号", "-7", -7.0),
    ("小数", "1.5", 1.5),
    ("下划线分组", "1_000", 1000.0),
    ("科学计数", "1e3", 1000.0),
    ("负指数", "2.5E-3", 0.0025),
    ("尾随小数点", "42.", 42.0),
    ("前导小数点", ".5", 0.5),
    ("全角数字", "４２", 42.0),
    ("阿拉伯印度数字", "٤٢", 42.0),
    ("超长数字串", "1" * 300, float("1" * 300)),
    ("布尔真", True, 1.0),
    ("布尔假", False, 0.0),
    ("浮点原样", 1.9, 1.9),
    ("整数入参", 42, 42.0),
]


@pytest.mark.parametrize("名, 入参, 期望", _转浮点成功表,
                         ids=[c[0] for c in _转浮点成功表])
def test_转浮点_成功(名, 入参, 期望):
    光 = 光明转换.转浮点(入参)
    原 = 地板.转浮点(入参)
    assert 光 == 期望, "转浮点(%r) 应得 %r，实得 %r" % (入参, 期望, 光)
    assert type(光) is float
    assert 光 == 原
    assert type(光) is type(原)


@pytest.mark.parametrize("入参", ["nan", "NaN", "-nan"])
def test_转浮点_接受nan(入参):
    光 = 光明转换.转浮点(入参)
    原 = 地板.转浮点(入参)
    assert math.isnan(光) is True
    assert math.isnan(原) is True
    assert type(光) is float


@pytest.mark.parametrize("入参, 期望", [("inf", math.inf), ("-inf", -math.inf),
                                       ("Infinity", math.inf)])
def test_转浮点_接受inf(入参, 期望):
    assert 光明转换.转浮点(入参) == 期望
    assert 地板.转浮点(入参) == 期望


_转浮点失败表 = [
    ("十六进制串应失败", "0x10"),
    ("空串", ""),
    ("纯空白", "   "),
    ("字母", "abc"),
    ("千分位逗号", "1,000"),
    ("中文数字", "四十二"),
    ("双小数点", "1.2.3"),
    ("只有符号", "-"),
    ("下划线位置非法", "_1.5"),
]


@pytest.mark.parametrize("名, 入参", _转浮点失败表, ids=[c[0] for c in _转浮点失败表])
def test_转浮点_失败消息逐字一致(名, 入参):
    期望消息 = "无法将 '%s' 转换为浮点数" % (入参,)
    with pytest.raises(RuntimeError) as 光信息:
        光明转换.转浮点(入参)
    with pytest.raises(RuntimeError) as 原信息:
        地板.转浮点(入参)
    assert str(光信息.value) == 期望消息
    assert str(原信息.value) == 期望消息
    assert type(光信息.value) is RuntimeError


# Python 版只 `except ValueError`：TypeError 必须穿透，不许被包成 RuntimeError。
# 这条是「捕获 (值错误)」与「捕获 值错误」的分水岭——后者生成
# `except Exception as 值错误`，会把 TypeError 一起吞掉并改型成 RuntimeError。
_类型错误入参 = [
    ("None", None),
    ("列表", [1]),
    ("字典", {"k": 1}),
    ("元组", (1, 2)),
    ("集合", {1, 2}),
]


@pytest.mark.parametrize("名, 入参", _类型错误入参, ids=[c[0] for c in _类型错误入参])
def test_转整数_类型错误必须穿透(名, 入参):
    with pytest.raises(TypeError) as 光信息:
        光明转换.转整数(入参)
    with pytest.raises(TypeError) as 原信息:
        地板.转整数(入参)
    assert type(光信息.value) is type(原信息.value)
    assert str(光信息.value) == str(原信息.value)
    assert "无法将" not in str(光信息.value), (
        "TypeError 被包成了转换失败消息——说明捕获子句把 Exception 全吞了")


@pytest.mark.parametrize("名, 入参", _类型错误入参, ids=[c[0] for c in _类型错误入参])
def test_转浮点_类型错误必须穿透(名, 入参):
    with pytest.raises(TypeError) as 光信息:
        光明转换.转浮点(入参)
    with pytest.raises(TypeError) as 原信息:
        地板.转浮点(入参)
    assert type(光信息.value) is type(原信息.value)
    assert str(光信息.value) == str(原信息.value)
    assert "无法将" not in str(光信息.value)


class _自定义文本:
    def __str__(self):
        return "自定义的字符串形态"


class _文本形态怪():
    def __str__(self):
        return "／／非ASCII／／"


_转字符串表 = [
    ("None", None, "None"),
    ("布尔真", True, "True"),
    ("布尔假", False, "False"),
    ("整数", 42, "42"),
    ("浮点整值", 1.0, "1.0"),
    ("浮点", 1.5, "1.5"),
    ("负零浮点", -0.0, "-0.0"),
    ("空串", "", ""),
    ("字符串原样", "abc", "abc"),
    ("非ASCII", "中文·全角４２", "中文·全角４２"),
    ("列表", [1, 2], "[1, 2]"),
    ("嵌套字典", {"k": 1}, "{'k': 1}"),
    ("空字典", {}, "{}"),
    ("元组", (1, "a"), "(1, 'a')"),
    ("自定义__str__", _自定义文本(), "自定义的字符串形态"),
    ("自定义__str__非ASCII", _文本形态怪(), "／／非ASCII／／"),
]


@pytest.mark.parametrize("名, 入参, 期望", _转字符串表, ids=[c[0] for c in _转字符串表])
def test_转字符串(名, 入参, 期望):
    光 = 光明转换.转字符串(入参)
    原 = 地板.转字符串(入参)
    assert 光 == 期望, "转字符串(%r) 应得 %r，实得 %r" % (入参, 期望, 光)
    assert type(光) is str
    assert 光 == 原


def test_转字符串_不吞异常():
    """转字符串 里没有 try：__str__ 抛错必须原样冒出来（Python 版就是裸 str()）。"""
    class 会炸的:
        def __str__(self):
            raise ValueError("我就是要炸")

    with pytest.raises(ValueError) as 光信息:
        光明转换.转字符串(会炸的())
    with pytest.raises(ValueError) as 原信息:
        地板.转字符串(会炸的())
    assert str(光信息.value) == "我就是要炸"
    assert str(原信息.value) == str(光信息.value)


# ── 导出面：11 条都必须在模块上取得到 ────────────────────────────────────────
_字典组 = ["字典创建", "字典设置", "字典删除", "字典键列表",
          "字典值列表", "字典项列表", "字典包含键", "字典获取"]
_转换组 = ["转整数", "转浮点", "转字符串"]


@pytest.mark.parametrize("名字", _字典组)
def test_字典组导出齐全(名字):
    assert callable(getattr(光明字典, 名字))


@pytest.mark.parametrize("名字", _转换组)
def test_转换组导出齐全(名字):
    assert callable(getattr(光明转换, 名字))


def test_两个模块的__all__必须是全量():
    """`导出` 必须写在**一行**里。

    实测：多行 `导出` 会各生成一句 `__all__ = [...]`，后一句覆盖前一句，
    于是 `from 模块 import *` 只拿到最后一行那几个名字（stdlib/字符串工具轻量.light
    有 5 行 导出，`__all__` 里只剩最后一行的 4 个，属编译器既有缺陷）。
    本判据锁死本文件的写法，防止有人为了排版把 导出 拆行。
    """
    assert 光明字典.__all__ == _字典组
    assert 光明转换.__all__ == _转换组
