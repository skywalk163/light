# -*- coding: utf-8 -*-
"""
test_地板搬迁_JSON_S2.py —— 「地板搬迁」等价性判据：stdlib/builtins.py 的
解析JSON / 序列化JSON / 美化JSON 转发到 stdlib/JSON.light 后，行为必须与搬迁前的
Python 实现**完全等价**（逐字符 / 逐值 + 类型 + 异常类型）。

oracle 口径（硬要求）：本文件内联一份**搬迁前 builtins.py 的 Python 实现副本**
（见 _oracle_* 三个函数，逐字对照 stdlib/builtins.py:413/421/431），
**不从 builtins 导入**——否则转发改完后就是自己跟自己比，测试永远绿。

被测侧：经光明导入钩子加载 stdlib/JSON.light（引导方式照抄 tests/test_json_core_light.py:20-29）。

本轮（S2 修复后）全部用例都是**正向等价断言**，不再有「差异锁定」用例。
唯一不逐字相等的是异常**消息尾部**：CPython 的 json 报 "Expecting ':' delimiter: line 1 column 5 (char 4)"，
光明报中文描述且无行列号；本文件按「异常类型 + 消息前缀」这两项契约断言（见 §3 注释）。
"""
import os
import sys

# 注意：json 必须在把 stdlib 塞进 sys.path 之前导入。
# stdlib 下存在 JSON.light，Windows 文件名大小写不敏感，先装 sys.path 会让
# `import json` 有被 JSON.light 劫持的风险（见 _light_import_hook._exists_exact 的注释）。
import json

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_REPO, "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402

_light_import_hook.install([_STDLIB])

# 被测侧：光明实现（JSON.light -> JSON核心.light）
from JSON import 解析JSON as L解析JSON, 序列化JSON as L序列化JSON, 美化JSON as L美化JSON  # noqa: E402


def test_被测侧确实来自光明文件():
    """守卫：若 import JSON 落到某个 .py 上，本轮所有对拍都失去意义。"""
    import JSON as _mod
    路径 = getattr(_mod, "__file__", "") or ""
    assert 路径.endswith("JSON.light"), "被测模块不是 JSON.light，实际=%r" % (路径,)


# =============================================================================
# oracle：搬迁前 stdlib/builtins.py 的 Python 实现内联副本（只读参照，不许改成导入）
# =============================================================================

def _oracle_解析JSON(text):
    """builtins.py:413 原文副本。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


def _oracle_序列化JSON(value, 缩进=None):
    """builtins.py:421 原文副本。"""
    try:
        if 缩进 is not None:
            return json.dumps(value, ensure_ascii=False, indent=缩进)
        return json.dumps(value, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"JSON 序列化失败: {e}")


def _oracle_美化JSON(value):
    """builtins.py:431 原文副本。"""
    return _oracle_序列化JSON(value, 缩进=2)


# =============================================================================
# 工具
# =============================================================================

def _a(x):
    """ASCII 安全的 repr：控制台是 GBK，失败信息里若含 emoji 会 UnicodeEncodeError。"""
    return repr(x).encode("unicode_escape").decode("ascii")


def _同值同型(py值, 光明值, 路径="$"):
    """递归比较「值相等且类型相同」。返回 None 表示一致，否则返回差异描述。

    必须比类型：1 == 1.0、True == 1 在 Python 里都成立，只用 == 会漏判。
    """
    if type(py值) is not type(光明值):
        return "%s 类型不同: py=%s 光明=%s (py值=%s 光明值=%s)" % (
            路径, type(py值).__name__, type(光明值).__name__, _a(py值), _a(光明值))
    if isinstance(py值, dict):
        if list(py值.keys()) != list(光明值.keys()):
            return "%s 键序/键集不同: py=%s 光明=%s" % (路径, _a(list(py值.keys())), _a(list(光明值.keys())))
        for k in py值:
            子 = _同值同型(py值[k], 光明值[k], "%s[%s]" % (路径, _a(k)))
            if 子:
                return 子
        return None
    if isinstance(py值, list):
        if len(py值) != len(光明值):
            return "%s 长度不同: py=%d 光明=%d" % (路径, len(py值), len(光明值))
        for i, (x, y) in enumerate(zip(py值, 光明值)):
            子 = _同值同型(x, y, "%s[%d]" % (路径, i))
            if 子:
                return 子
        return None
    if py值 != 光明值:
        # NaN 自己不等于自己：两侧都是 NaN 视为一致
        if isinstance(py值, float) and py值 != py值 and 光明值 != 光明值:
            return None
        return "%s 值不同: py=%s 光明=%s" % (路径, _a(py值), _a(光明值))
    return None


# =============================================================================
# 样本
# =============================================================================

# U+0000..U+001F 全 32 个控制字符逐个对拍（json.dumps：0x08/09/0a/0c/0d 用短转义，其余 \u00xx）
控制符样本 = [("ctrl_%02x" % i, {"k": "a" + chr(i) + "b"}) for i in range(32)]

基础样本 = [
    ("空字典", {}),
    ("空列表", []),
    ("嵌套", {"a": [1, {"b": [2, 3]}], "c": {"d": {}}}),
    ("深嵌套", {"a": {"b": {"c": [1, [2, {"d": "e"}]]}}, "f": [], "g": {}}),
    ("中文", {"名字": "张三", "句子": "今天天气真好，适合写代码。"}),
    ("None", None),
    ("True", True),
    ("False", False),
    ("布尔在容器里", {"t": True, "f": False, "n": None}),
    ("int", 42),
    ("负int", -42),
    ("零", 0),
    ("大整数", 123456789012345678901234567890),
    ("负大整数", -9876543210123456789),
    ("float", 3.14),
    ("负float", -0.5),
    ("float_0_1", 0.1),
    ("float_0_0", 0.0),
    ("float_负0_0", -0.0),
    ("float_1_0", 1.0),
    ("float_1e20", 1e20),
    ("float_1e-7", 1e-07),
    ("float_负科学计数", -3.14e-2),
    ("float_大科学计数", 1.5e10),
    ("inf", float("inf")),
    ("负inf", float("-inf")),
    ("nan", float("nan")),
    ("inf在容器里", {"a": float("inf"), "b": float("-inf"), "c": float("nan")}),
    ("双引号", {"k": 'a"b"c'}),
    ("反斜杠", {"k": "a\\b\\\\c"}),
    ("换行", {"k": "line1\nline2"}),
    ("制表", {"k": "a\tb"}),
    ("回车", {"k": "a\rb"}),
    ("退格", {"k": "a\bb"}),
    ("换页", {"k": "a\fb"}),
    ("五个有名控制符", {"k": "\b\t\n\f\r"}),
    ("换行制表回车混合", {"k": "a\nb\tc\rd"}),
    ("空字符串键值", {"": ""}),
    ("空字符串值", {"k": ""}),
    ("emoji", {"e": "\U0001f600", "多个": "\U0001f600\U0001f680"}),
    ("emoji裸值", "\U0001f600"),
    ("DEL_0x7f", {"k": "\x7f"}),
    ("非ASCII_0x80", {"k": "\x80"}),
    ("中文键", {"中文键": "中文值"}),
    ("混合列表", [None, True, False, "文本", 42, 3.14, {"k": [1, "二", None]}]),
    ("裸字符串", "裸字符串"),
    ("三层列表", [[[1]]]),
    ("键含转义", {'a"b\\c\nd': 1}),
    ("多键紧凑分隔符", {"a": 1, "b": 2, "c": 3}),
    ("多元素数组", [1, 2, 3]),
    # tuple 当数组（json 口径）
    ("元组值", {"k": (1, 2)}),
    ("裸元组", (1, 2)),
    ("嵌套元组", [(1, (2, 3))]),
    ("空元组", ()),
    # 非字符串键（json 口径：转成字符串键）
    ("int键", {1: 2}),
    ("负int键", {-3: 4}),
    ("None键", {None: 1}),
    ("True键", {True: 1}),
    ("False键", {False: 1}),
    ("float键", {2.5: 1}),
    ("inf键", {float("inf"): 1}),
    ("混合键", {"s": 1, 2: 3, None: 4, True: 5, 6.5: 7}),
]

序列化样本 = 基础样本 + 控制符样本
序列化样本_ID = [名 for 名, _ in 序列化样本]


# =============================================================================
# 1. 序列化：紧凑 / 缩进 0,1,2,4,8 / 美化，逐字符等价
# =============================================================================

@pytest.mark.parametrize("名,值", 序列化样本, ids=序列化样本_ID)
def test_序列化_紧凑_逐字符等价(名, 值):
    py = _oracle_序列化JSON(值)
    光明 = L序列化JSON(值)
    assert 光明 == py, (
        "序列化(紧凑) 样本[%s] 不等价\n  py   =%s\n  光明 =%s" % (名, _a(py), _a(光明)))


@pytest.mark.parametrize("缩进", [0, 1, 2, 4, 8])
@pytest.mark.parametrize("名,值", 序列化样本, ids=序列化样本_ID)
def test_序列化_缩进_逐字符等价(名, 值, 缩进):
    """含 缩进=0：py 侧走 `if 缩进 is not None` → indent=0（换行但零缩进），不是紧凑。"""
    py = _oracle_序列化JSON(值, 缩进)
    光明 = L序列化JSON(值, 缩进)
    assert 光明 == py, (
        "序列化(缩进=%d) 样本[%s] 不等价\n  py   =%s\n  光明 =%s" % (缩进, 名, _a(py), _a(光明)))


@pytest.mark.parametrize("名,值", 序列化样本, ids=序列化样本_ID)
def test_美化_逐字符等价(名, 值):
    py = _oracle_美化JSON(值)
    光明 = L美化JSON(值)
    assert 光明 == py, (
        "美化JSON 样本[%s] 不等价\n  py   =%s\n  光明 =%s" % (名, _a(py), _a(光明)))


@pytest.mark.parametrize("名,值", 序列化样本, ids=序列化样本_ID)
def test_美化_等于缩进2(名, 值):
    """美化JSON(v) 必须等于 序列化JSON(v, 2)（builtins.py:433 的语义）。"""
    assert L美化JSON(值) == L序列化JSON(值, 2), "样本[%s] 美化 != 缩进2" % 名


def test_序列化_分隔符口径_紧凑用逗号空格():
    """json.dumps 紧凑态 item 分隔符是 ", "、键值分隔符是 ": "；这是最容易分叉的一处。"""
    值 = {"a": 1, "b": [1, 2]}
    py = _oracle_序列化JSON(值)
    assert py == '{"a": 1, "b": [1, 2]}', "oracle 自身跑偏: %s" % _a(py)
    assert L序列化JSON(值) == py, (
        "紧凑分隔符不等价\n  py   =%s\n  光明 =%s" % (_a(py), _a(L序列化JSON(值))))


def test_序列化_分隔符口径_缩进态无逗号空格():
    """带 indent 时 json.dumps 的 item 分隔符退化成 ","（后面跟换行），不再是 ", "。"""
    值 = {"a": 1, "b": [1, 2]}
    py = _oracle_序列化JSON(值, 2)
    assert ", " not in py, "oracle 自身跑偏（缩进态不该出现 ', '）: %s" % _a(py)
    光明 = L序列化JSON(值, 2)
    assert ", " not in 光明, "光明缩进态出现了 ', ' 分隔符: %s" % _a(光明)
    assert 光明 == py, "缩进分隔符不等价\n  py   =%s\n  光明 =%s" % (_a(py), _a(光明))


def test_序列化_缩进0是换行零缩进而非紧凑():
    """缩进=0 的正向口径断言（搬迁前 py 行为：有换行、零缩进）。"""
    值 = {"a": 1, "b": [1, 2]}
    py = _oracle_序列化JSON(值, 0)
    assert py == '{\n"a": 1,\n"b": [\n1,\n2\n]\n}', "oracle 自身跑偏: %s" % _a(py)
    assert L序列化JSON(值, 0) == py, (
        "缩进=0 不等价\n  py   =%s\n  光明 =%s" % (_a(py), _a(L序列化JSON(值, 0))))


def test_序列化_缩进空是紧凑():
    值 = {"a": 1, "b": [1, 2]}
    assert L序列化JSON(值) == '{"a": 1, "b": [1, 2]}'
    assert L序列化JSON(值) == _oracle_序列化JSON(值)


def test_序列化_中文不转义():
    """ensure_ascii=False：中文必须原样，不许 \\uXXXX。"""
    值 = {"名字": "张三"}
    光明 = L序列化JSON(值)
    assert "\\u" not in 光明, "中文被转义成 \\uXXXX: %s" % _a(光明)
    assert 光明 == _oracle_序列化JSON(值)
    assert "张三" in 光明


def test_序列化_emoji不转义():
    值 = {"e": "\U0001f600"}
    光明 = L序列化JSON(值)
    assert "\\u" not in 光明, "emoji 被转义: %s" % _a(光明)
    assert 光明 == _oracle_序列化JSON(值)
    assert "\U0001f600" in 光明


@pytest.mark.parametrize("名,值,期望", [
    ("退格", {"k": "\x08"}, '{"k": "\\b"}'),
    ("制表", {"k": "\x09"}, '{"k": "\\t"}'),
    ("换行", {"k": "\x0a"}, '{"k": "\\n"}'),
    ("换页", {"k": "\x0c"}, '{"k": "\\f"}'),
    ("回车", {"k": "\x0d"}, '{"k": "\\r"}'),
    ("0x00", {"k": "\x00"}, '{"k": "\\u0000"}'),
    ("0x01", {"k": "\x01"}, '{"k": "\\u0001"}'),
    ("0x0b", {"k": "\x0b"}, '{"k": "\\u000b"}'),
    ("0x1f", {"k": "\x1f"}, '{"k": "\\u001f"}'),
], ids=["\\b", "\\t", "\\n", "\\f", "\\r", "0x00", "0x01", "0x0b", "0x1f"])
def test_序列化_控制符转义形态(名, 值, 期望):
    """短转义 vs \\u00xx 的分工必须与 json.dumps 一字不差。"""
    py = _oracle_序列化JSON(值)
    assert py == 期望, "oracle 自身跑偏: %s" % _a(py)
    assert L序列化JSON(值) == 期望, "光明产出 %s" % _a(L序列化JSON(值))


@pytest.mark.parametrize("名,值,期望", [
    ("集合", {1, 2}, "set"),
    ("bytes", b"ab", "bytes"),
    ("嵌套集合", {"a": [{1, 2}]}, "set"),
    ("元组键", {(1, 2): 1}, "tuple"),
], ids=["集合", "bytes", "嵌套集合", "元组键"])
def test_序列化_不可序列化类型两侧都抛RuntimeError(名, 值, 期望):
    """py 抛 RuntimeError('JSON 序列化失败: ...')；光明必须同类型同前缀（不许静默降级）。"""
    with pytest.raises(RuntimeError) as py信息:
        _oracle_序列化JSON(值)
    assert type(py信息.value) is RuntimeError
    assert str(py信息.value).startswith("JSON 序列化失败: ")

    with pytest.raises(RuntimeError) as 光明信息:
        L序列化JSON(值)
    assert type(光明信息.value) is RuntimeError, (
        "样本[%s] 光明侧异常类型是 %s，不是 RuntimeError" % (名, type(光明信息.value).__name__))
    assert str(光明信息.value).startswith("JSON 序列化失败: "), (
        "样本[%s] 光明侧消息前缀不符: %s" % (名, _a(str(光明信息.value))))
    assert 期望 in str(光明信息.value), (
        "样本[%s] 光明侧消息未点出类型 %s: %s" % (名, 期望, _a(str(光明信息.value))))


def test_序列化_自定义对象也抛():
    class 某类:
        pass
    with pytest.raises(RuntimeError):
        _oracle_序列化JSON(某类())
    with pytest.raises(RuntimeError) as 信息:
        L序列化JSON(某类())
    assert type(信息.value) is RuntimeError
    assert str(信息.value).startswith("JSON 序列化失败: ")


@pytest.mark.parametrize("名,值,期望", [
    ("元组当数组", {"k": (1, 2)}, '{"k": [1, 2]}'),
    ("裸元组", (1, 2), "[1, 2]"),
    ("空元组", (), "[]"),
], ids=["元组当数组", "裸元组", "空元组"])
def test_序列化_元组当数组(名, 值, 期望):
    assert _oracle_序列化JSON(值) == 期望, "oracle 自身跑偏"
    assert L序列化JSON(值) == 期望, "光明产出 %s" % _a(L序列化JSON(值))


@pytest.mark.parametrize("名,值,期望", [
    ("int键", {1: 2}, '{"1": 2}'),
    ("None键", {None: 1}, '{"null": 1}'),
    ("True键", {True: 1}, '{"true": 1}'),
    ("False键", {False: 1}, '{"false": 1}'),
    ("float键", {2.5: 1}, '{"2.5": 1}'),
    ("inf键", {float("inf"): 1}, '{"Infinity": 1}'),
], ids=["int键", "None键", "True键", "False键", "float键", "inf键"])
def test_序列化_非字符串键转字符串(名, 值, 期望):
    assert _oracle_序列化JSON(值) == 期望, "oracle 自身跑偏: %s" % _a(_oracle_序列化JSON(值))
    assert L序列化JSON(值) == 期望, "光明产出 %s" % _a(L序列化JSON(值))


@pytest.mark.parametrize("名,值,期望", [
    ("inf", float("inf"), "Infinity"),
    ("负inf", float("-inf"), "-Infinity"),
    ("nan", float("nan"), "NaN"),
], ids=["inf", "-inf", "nan"])
def test_序列化_特殊浮点字面量(名, 值, 期望):
    assert _oracle_序列化JSON(值) == 期望, "oracle 自身跑偏"
    assert L序列化JSON(值) == 期望, "光明产出 %s" % _a(L序列化JSON(值))


# =============================================================================
# 2. 解析：合法输入，值相等且类型相同
# =============================================================================

解析样本 = [
    ("空对象", "{}"),
    ("空数组", "[]"),
    ("简单对象", '{"a":1}'),
    ("对象带数组", '{"a": 1, "b": [1,2,3]}'),
    ("嵌套对象", '{"a":{"b":{"c":[1,2,{"d":null}]}}}'),
    ("字符串", '"字符串"'),
    ("空字符串", '""'),
    ("int_1", "1"),
    ("int_0", "0"),
    ("int_负", "-1"),
    ("int_负零", "-0"),
    ("int_大", "123456789012345678901234567890"),
    ("float_1_5", "1.5"),
    ("float_负", "-3.14"),
    ("float_0_1", "0.1"),
    ("科学计数_e", "1e3"),
    ("科学计数_E", "1E3"),
    ("科学计数_负指数", "1.5e-3"),
    ("科学计数_正号指数", "-2.5E+4"),
    ("科学计数_1e20", "1e20"),
    ("科学计数_1e-7", "1e-7"),
    ("科学计数_0e0", "0e0"),
    ("true", "true"),
    ("false", "false"),
    ("null", "null"),
    ("前后空白", '   {"a" : 1}   '),
    ("内部换行制表空白", '{\n\t"a" :\r\n 1\n}'),
    ("转义_引号", '"\\""'),
    ("转义_反斜杠", '"\\\\"'),
    ("转义_斜杠", '"\\/"'),
    ("转义_换行制表回车", '"a\\nb\\tc\\rd"'),
    ("转义_退格", '"a\\bb"'),
    ("转义_换页", '"a\\fb"'),
    ("转义_五个有名", '"\\b\\t\\n\\f\\r"'),
    ("转义_u中文", '"\\u00e9\\u4e2d\\u6587"'),
    ("转义_u控制符", '"\\u0000\\u001f"'),
    ("转义_u大写A", '"\\u0041"'),
    ("代理对_emoji", '"\\ud83d\\ude00"'),
    ("代理对_两个", '"\\ud83d\\ude00\\ud83d\\ude80"'),
    ("代理对_夹在文本里", '"a\\ud83d\\ude00b"'),
    ("中文键值", '{"中文键":"中文值"}'),
    ("emoji原样", '{"e":"\U0001f600"}'),
    ("混合数组", '[1, 2.0, "3", true, null]'),
    ("布尔在对象里", '{"t":true,"f":false,"n":null}'),
    ("尾随换行", '{"a":1}\n'),
    ("尾随空白", '{"a":1}   \t\r\n'),
    ("深数组", "[[[1]]]"),
    ("空白对象体", "{   }"),
    ("空白数组体", "[   ]"),
]
解析样本_ID = [名 for 名, _ in 解析样本]


@pytest.mark.parametrize("名,文本", 解析样本, ids=解析样本_ID)
def test_解析_合法输入_同值同型(名, 文本):
    py = _oracle_解析JSON(文本)
    光明 = L解析JSON(文本)
    差 = _同值同型(py, 光明)
    assert 差 is None, "解析 样本[%s] 输入=%s 不等价：%s" % (名, _a(文本), 差)


@pytest.mark.parametrize("文本,期望类型", [
    ("1", int),
    ("-1", int),
    ("0", int),
    ("123456789012345678901234567890", int),
    ("1.0", float),
    ("1.5", float),
    ("1e3", float),
    ("1E3", float),
    ("-2.5E+4", float),
    ("true", bool),
    ("false", bool),
], ids=["1", "-1", "0", "大整数", "1.0", "1.5", "1e3", "1E3", "-2.5E+4", "true", "false"])
def test_解析_标量类型不许漂移(文本, 期望类型):
    """1 必须是 int 不是 float；1e3 必须是 float。两侧都要对，且与期望一致。"""
    py = _oracle_解析JSON(文本)
    光明 = L解析JSON(文本)
    assert type(py) is 期望类型, "oracle 自身跑偏: %s -> %s" % (文本, type(py).__name__)
    assert type(光明) is 期望类型, (
        "光明解析 %s 类型漂移: 期望 %s，实际 %s（值=%s）"
        % (文本, 期望类型.__name__, type(光明).__name__, _a(光明)))
    assert 光明 == py, "光明解析 %s 值不同: py=%s 光明=%s" % (文本, _a(py), _a(光明))


def test_解析_u转义还原为实际字符():
    文本 = '"\\u00e9\\u4e2d\\u6587"'
    光明 = L解析JSON(文本)
    assert 光明 == "é中文", "\\u 转义未正确还原: %s" % _a(光明)
    assert 光明 == _oracle_解析JSON(文本)


def test_解析_代理对合成单码点():
    """\\ud83d\\ude00 必须合成 U+1F600（长度 1），不是两个孤立代理。"""
    文本 = '"\\ud83d\\ude00"'
    py = _oracle_解析JSON(文本)
    光明 = L解析JSON(文本)
    assert py == "\U0001f600", "oracle 自身跑偏: %s" % _a(py)
    assert len(光明) == 1, "光明侧长度 %d（%s），代理对没合成" % (len(光明), _a(光明))
    assert ord(光明[0]) == 0x1F600, "光明侧码点 %s" % _a(光明)
    assert 光明 == py


def test_解析_代理对与普通字符混排():
    文本 = '"a\\ud83d\\ude00b\\u4e2d"'
    py = _oracle_解析JSON(文本)
    光明 = L解析JSON(文本)
    assert 光明 == py == "a\U0001f600b中", _a(光明)
    assert len(光明) == 4


@pytest.mark.parametrize("名,文本,期望", [
    ("退格", '"a\\bb"', "a\x08b"),
    ("换页", '"a\\fb"', "a\x0cb"),
], ids=["\\b", "\\f"])
def test_解析_bf转义还原为控制字符(名, 文本, 期望):
    py = _oracle_解析JSON(文本)
    光明 = L解析JSON(文本)
    assert py == 期望, "oracle 自身跑偏: %s" % _a(py)
    assert 光明 == 期望, "光明侧得到 %s" % _a(光明)


def test_往返_解析后再序列化与oracle一致():
    """round-trip：光明 解析 -> 光明 序列化 三形态，与 oracle 对同一对象的输出逐字符相等。"""
    文本 = '{"a": 1, "b": [1, 2, {"c": "中文"}], "d": null, "e": true, "f": 1.5}'
    光明值 = L解析JSON(文本)
    py值 = _oracle_解析JSON(文本)
    assert _同值同型(py值, 光明值) is None
    assert L序列化JSON(光明值) == _oracle_序列化JSON(py值)
    assert L序列化JSON(光明值, 2) == _oracle_序列化JSON(py值, 2)
    assert L美化JSON(光明值) == _oracle_美化JSON(py值)


@pytest.mark.parametrize("名,值", 基础样本, ids=[名 for 名, _ in 基础样本])
def test_往返_双向(名, 值):
    """双向 round-trip：
    1) 光明序列化的产物必须能被 json.loads 读回，且与 oracle 读回同值同型；
    2) json.dumps 的产物必须能被光明解析，且与 oracle 解析同值同型。
    """
    # inf/nan 的字面量（Infinity/NaN）不是标准 JSON，但 json.loads 认；光明解析按标准拒绝，
    # 这与 py 侧 json.loads 的宽松扩展不同——此处只对「标准 JSON 能表达的样本」做往返。
    有非有限浮点 = "inf" in 名 or "nan" in 名
    紧凑 = L序列化JSON(值)
    if not 有非有限浮点:
        差 = _同值同型(json.loads(_oracle_序列化JSON(值)), json.loads(紧凑))
        assert 差 is None, "样本[%s] 光明产物被 json 读回后不一致：%s" % (名, 差)
        标准 = _oracle_序列化JSON(值)
        差2 = _同值同型(_oracle_解析JSON(标准), L解析JSON(标准))
        assert 差2 is None, "样本[%s] 光明解析 json.dumps 产物后不一致：%s" % (名, 差2)
    # 缩进态产物同样必须是合法 JSON
    美 = L美化JSON(值)
    if not 有非有限浮点:
        assert json.loads(美) == json.loads(_oracle_美化JSON(值)), "样本[%s] 美化产物读回不一致" % 名


@pytest.mark.parametrize("名,值", 控制符样本, ids=[名 for 名, _ in 控制符样本])
def test_往返_控制符产物是合法JSON(名, 值):
    """32 个控制字符：光明产物必须能被标准 json 读回成原值（旧实现产出裸控制符，读不回来）。"""
    紧凑 = L序列化JSON(值)
    读回 = json.loads(紧凑)
    assert 读回 == 值, "样本[%s] 读回不等: %s -> %s" % (名, _a(紧凑), _a(读回))
    # 光明自己也要能读回
    assert L解析JSON(紧凑) == 值, "样本[%s] 光明自解析不等" % 名


# =============================================================================
# 3. 解析：非法输入的异常口径
#    契约：两侧都抛 RuntimeError（type 完全相同），消息都以 "JSON 解析失败: " 开头。
#    消息尾部不比：py 尾部是 CPython 扫描器的英文 + 行列号，光明是中文描述——
#    这是唯一无法逐字对齐的项（要对齐就得复刻 CPython 的错误串，无意义），已在交付报告登记。
# =============================================================================

非法样本 = [
    ("左花括号", "{", "对象键必须是双引号字符串"),
    ("对象缺冒号", '{"a"}', "对象缺少冒号"),
    ("数组尾逗号", "[1,]", "非法字符 ']'"),
    ("tru", "tru", "期望 true"),
    ("空串", "", "非法字符 ''"),
    ("对象尾逗号", '{"a":1,}', "对象键必须是双引号字符串"),
    ("单引号键", "{'a':1}", "对象键必须是双引号字符串"),
    ("数组缺逗号", "[1 2]", "数组缺少逗号或右方括号"),
    ("值位为空", '{"a":}', "非法字符 '}'"),
    ("对象后有垃圾", '{"a":1} xyz', "尾部多余内容 'x'"),
    ("两个数组相连", "[1][2]", "尾部多余内容 '['"),
    ("前导零", "01", "尾部多余内容 '1'"),
    ("负前导零", "-01", "尾部多余内容 '1'"),
    ("双零", "00", "尾部多余内容 '0'"),
    ("两个小数点", "0.1.2", "尾部多余内容 '.'"),
    ("nul", "nul", "期望 null"),
    ("truex", "truex", "尾部多余内容 'x'"),
    ("nullx", "nullx", "尾部多余内容 'x'"),
    ("加号开头", "+1", "非法字符 '+'"),
    ("小数点开头", ".5", "非法字符 '.'"),
    ("双负号", "--1", "数字缺少整数部分"),
    ("小数点后无数字", "1.", "小数点后缺少数字"),
    ("指数后无数字", "1e", "指数缺少数字"),
    ("指数符号后无数字", "1e+", "指数缺少数字"),
    ("字符串未闭合", '"未闭合', "字符串未闭合"),
    ("左方括号", "[", "非法字符 ''"),
    ("非法转义", '"\\q"', "非法转义 \\q"),
    ("字符串内裸换行", '"a\nb"', "字符串内出现未转义控制字符"),
    ("u转义位数不足", '"\\u12"', "无效 \\u 转义"),
    ("对象键后缺冒号", '{"a" 1}', "对象缺少冒号"),
    ("数组只有逗号", "[,]", "非法字符 ','"),
    ("对象只有逗号", "{,}", "对象键必须是双引号字符串"),
]
非法样本_ID = [名 for 名, _, _ in 非法样本]


@pytest.mark.parametrize("名,文本,光明消息尾", 非法样本, ids=非法样本_ID)
def test_解析_非法输入_两侧同类型同前缀(名, 文本, 光明消息尾):
    """两侧都必须抛 RuntimeError（不许静默返回值，也不许是别的异常类型）。"""
    with pytest.raises(RuntimeError) as py信息:
        _oracle_解析JSON(文本)
    assert type(py信息.value) is RuntimeError, (
        "oracle 侧类型变了: %s" % type(py信息.value).__name__)
    assert str(py信息.value).startswith("JSON 解析失败: "), (
        "oracle 异常消息形态变了: %s" % _a(str(py信息.value)))

    with pytest.raises(RuntimeError) as 光明信息:
        L解析JSON(文本)
    assert type(光明信息.value) is RuntimeError, (
        "样本[%s] 输入=%s 光明侧异常类型是 %s，不是 RuntimeError"
        % (名, _a(文本), type(光明信息.value).__name__))
    assert str(光明信息.value).startswith("JSON 解析失败: "), (
        "样本[%s] 光明侧消息前缀不符: %s" % (名, _a(str(光明信息.value))))
    assert str(光明信息.value) == "JSON 解析失败: " + 光明消息尾, (
        "样本[%s] 光明侧消息尾变了\n  期望=%s\n  实际=%s"
        % (名, _a("JSON 解析失败: " + 光明消息尾), _a(str(光明信息.value))))


@pytest.mark.parametrize("名,文本", [
    ("对象后有垃圾", '{"a":1} xyz'),
    ("两个数组相连", "[1][2]"),
    ("前导零", "01"),
], ids=["对象后有垃圾", "两个数组相连", "前导零"])
def test_解析_尾部垃圾必须报错(名, 文本):
    """旧实现在这三条上静默丢弃尾部内容并返回第一个值；现在必须与 py 一样报错。"""
    with pytest.raises(RuntimeError) as py信息:
        _oracle_解析JSON(文本)
    assert "Extra data" in str(py信息.value), "oracle 侧变了: %s" % _a(str(py信息.value))
    with pytest.raises(RuntimeError):
        L解析JSON(文本)


@pytest.mark.parametrize("名,文本", [("NaN", "NaN"), ("Infinity", "Infinity"),
                                     ("负Infinity", "-Infinity")],
                         ids=["NaN", "Infinity", "-Infinity"])
def test_解析_非标准字面量_py宽松光明严格(名, 文本):
    """已知且有意保留的口径差：json.loads 接受 NaN/Infinity（CPython 私有扩展），
    光明按 RFC 8259 拒绝。两侧都不静默出错值：py 得 float，光明抛 RuntimeError。
    """
    py = _oracle_解析JSON(文本)
    assert isinstance(py, float)
    with pytest.raises(RuntimeError) as 信息:
        L解析JSON(文本)
    assert str(信息.value).startswith("JSON 解析失败: "), _a(str(信息.value))
