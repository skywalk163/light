# -*- coding: utf-8 -*-
"""test_地板搬迁_连接字符串_S2.py —— 「地板搬迁」等价性判据：
stdlib/builtins.py:533 的 `连接字符串`（函数体就一句 `return separator.join(parts)`）
要转发到 stdlib/字符串工具轻量.light:74 的 `连接字符串`，那么光明侧必须与
CPython 的 `separator.join(parts)` 等价：返回值逐字相同、异常**类型**相同、
异常**消息逐字相同**。

oracle 口径（硬要求）
=====================
本文件的 oracle 就是**内联的 `separator.join(parts)`**——它本身就是等价目标。
**不许** `from builtins import 连接字符串` 再自比：转发做完后那就是自己跟自己比，
测试永远绿。

被测侧：经光明导入钩子加载 stdlib/字符串工具轻量.light（引导方式照抄
tests/unit/test_地板搬迁_求和_S2.py:58-66）。`test_被测侧确实来自光明文件` /
`test_被测函数的字节码来自光明文件` 是守卫：若 `import 字符串工具轻量` 落到
别的 .py 上、或名字被内置 `str.join` 顶掉，本轮所有对拍都失去意义。

===============================================================================
搬迁前的旧行为（这次收严要打掉的东西）
===============================================================================
旧的光明版对每个元素做 `转字符串(列表们[i])`，于是

    连接字符串([1, 2], "-")   Python 侧 → TypeError
                              光明 侧   → "1-2"

即把类型错误变成静默拼接。主线已裁决：**收严光明侧**，与 `str.join` 对齐。

===============================================================================
CPython 3.14.7 实测的真实异常（本文件断言就按这些逐字对齐）
===============================================================================
    "-".join([1, "a", "b"])     TypeError: sequence item 0: expected str instance, int found
    "-".join(["a", 1, "b"])     TypeError: sequence item 1: expected str instance, int found
    "-".join(["a", "b", 1])     TypeError: sequence item 2: expected str instance, int found
    "-".join(["a", 1.5])        TypeError: sequence item 1: expected str instance, float found
    "-".join(["a", True])       TypeError: sequence item 1: expected str instance, bool found
    "-".join(["a", None])       TypeError: sequence item 1: expected str instance, NoneType found
    "-".join(["a", [1]])        TypeError: sequence item 1: expected str instance, list found
    "-".join(["a", {}])         TypeError: sequence item 1: expected str instance, dict found
    "-".join(["a", b"x"])       TypeError: sequence item 1: expected str instance, bytes found
    "-".join(["a"]*100+[None])  TypeError: sequence item 100: expected str instance, NoneType found
    "-".join(["a", 1, None])    TypeError: sequence item 1: expected str instance, int found   ← 只报第一个
    "-".join([1, "a", None])    TypeError: sequence item 0: expected str instance, int found   ← 只报第一个
类型名就是 `type(x).__name__`；下标是**第一个**非法元素的下标（实测确认）。

`连接符` 本身不是 str 时（`separator.join(parts)` 的属性查找先失败）：
    (5).join(["a","b"])         AttributeError: 'int' object has no attribute 'join'
    None.join(["a","b"])        AttributeError: 'NoneType' object has no attribute 'join'
    (5).join([])                AttributeError: 'int' object has no attribute 'join'   ← 空列表也抛
光明侧照抄了这条（含「先于元素检查」这个次序）。**唯一的例外是 bytes**，见文末
「已知不等价」——bytes 有自己的 join，CPython 走 bytes.join 抛 TypeError。

禁止假绿：本文件没有上下界断言、没有 try/except 吞断言、没有 skip、不装任何包。
"""
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_REPO, "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402

_light_import_hook.install([_STDLIB])

import 字符串工具轻量 as _光明字符串工具  # noqa: E402

L连接字符串 = _光明字符串工具.连接字符串


# =============================================================================
# §0 守卫：被测侧必须真的是光明文件里那一份
# =============================================================================

def test_被测侧确实来自光明文件():
    路径 = getattr(_光明字符串工具, "__file__", "") or ""
    assert 路径.endswith("字符串工具轻量.light"), (
        "被测模块不是 字符串工具轻量.light，实际=%r" % (路径,))


def test_被测函数的字节码来自光明文件():
    """防「钩子失效 / 内置名映射」把 连接字符串 变成 str.join 或同名 .py 里的函数。"""
    assert L连接字符串 is not str.join
    文件 = getattr(getattr(L连接字符串, "__code__", None), "co_filename", "")
    assert 文件.endswith("字符串工具轻量.light"), (
        "连接字符串 的字节码不是从 字符串工具轻量.light 编出来的：%r" % (文件,))


# =============================================================================
# §1 对拍工具：值要逐字相同（用 repr 比），异常要类型 + 消息都相同
# =============================================================================

def 神谕(列表们, 连接符):
    """oracle：内联的 `separator.join(parts)`，就是等价目标本身。"""
    return 连接符.join(列表们)


def 跑(函数, 列表们, 连接符):
    try:
        return ("值", repr(函数(列表们, 连接符)))
    except BaseException as e:                      # noqa: BLE001 - 要比异常类型，必须全抓
        return ("异常", type(e), str(e))


def 断言等价(列表们, 连接符):
    光明 = 跑(L连接字符串, list(列表们), 连接符)
    神 = 跑(神谕, list(列表们), 连接符)
    assert 光明[0] == 神[0], (
        "一侧给值一侧抛异常：列表=%r 连接符=%r 光明=%r oracle=%r"
        % (列表们, 连接符, 光明, 神))
    if 光明[0] == "异常":
        assert 光明[1] is 神[1], (
            "异常类型不同：列表=%r 连接符=%r 光明=%s oracle=%s"
            % (列表们, 连接符, 光明[1].__name__, 神[1].__name__))
        assert 光明[2] == 神[2], (
            "异常消息不同：列表=%r 连接符=%r\n  光明=%r\n  oracle=%r"
            % (列表们, 连接符, 光明[2], 神[2]))
        return
    assert 光明[1] == 神[1], (
        "返回值不同：列表=%r 连接符=%r 光明=%s oracle=%s"
        % (列表们, 连接符, 光明[1], 神[1]))


class 字符串子类(str):
    """CPython 的 join 用 PyUnicode_Check（收子类），光明侧用 isinstance 才对得上。"""


# =============================================================================
# §2 合法样本：空 / 单 / 多 / 空串元素 / 空连接符 / 多字符连接符 / 中文 / emoji /
#              含换行制表 / 很长的列表 / str 子类
# =============================================================================

_长列表 = ["x%d" % i for i in range(1000)]

合法样本 = [
    ("空列表_空连接符", [], ""),
    ("空列表_有连接符", [], "-"),
    ("单元素", ["a"], "-"),
    ("单元素_空串", [""], "-"),
    ("单元素_空连接符", ["a"], ""),
    ("多元素", ["a", "b", "c"], "-"),
    ("多元素_空连接符", ["a", "b", "c"], ""),
    ("空串元素在首", ["", "a", "b"], "-"),
    ("空串元素在中", ["a", "", "b"], "-"),
    ("空串元素在尾", ["a", "b", ""], "-"),
    ("全空串元素", ["", "", ""], "-"),
    ("全空串元素_空连接符", ["", "", ""], ""),
    ("多字符连接符", ["a", "b"], "-->"),
    ("连接符是空白", ["a", "b"], " "),
    ("连接符含换行", ["a", "b"], "\n"),
    ("连接符含制表", ["a", "b"], "\t"),
    ("连接符是中文", ["a", "b"], "\u3001"),
    ("连接符是emoji", ["a", "b"], "\U0001f680"),
    ("中文元素", ["\u4e2d\u6587", "\u6d4b\u8bd5"], "\uff0c"),
    ("中文元素_中文连接符", ["\u7532", "\u4e59", "\u4e19"], "\u4e0e"),
    ("emoji元素", ["\U0001f600", "\U0001f601"], "-"),
    ("emoji元素_emoji连接符", ["\U0001f600", "\U0001f601"], "\U0001f602"),
    ("代理对边界字符", ["\U00010000", "\uffff", "\x00"], "-"),
    ("元素含换行", ["a\nb", "c\nd"], "-"),
    ("元素含制表", ["a\tb", "c\td"], "-"),
    ("元素含回车换行", ["a\r\nb", "c"], "-"),
    ("元素含反斜杠", ["a\\b", "c"], "\\"),
    ("元素含引号", ['a"b', "c'd"], "-"),
    ("元素含chr8与chr12", ["a" + chr(8), chr(12) + "b"], "-"),   # 光明串里没有 \b / \f 转义
    ("很长的列表_1000", _长列表, ","),
    ("很长的列表_空连接符", _长列表, ""),
    ("很长的列表_多字符连接符", _长列表, "<->"),
    ("很长的全空串_1000", [""] * 1000, "-"),
    ("str子类元素", ["a", 字符串子类("b")], "-"),
    ("str子类元素全是", [字符串子类("a"), 字符串子类("b")], "-"),
    ("str子类作连接符", ["a", "b"], 字符串子类("-")),
]


@pytest.mark.parametrize("名字,列表们,连接符", 合法样本, ids=[名 for 名, _, _ in 合法样本])
def test_合法样本逐字等价(名字, 列表们, 连接符):
    断言等价(列表们, 连接符)


def test_返回值类型是str而不是子类():
    """`str 子类` 元素参与拼接后，CPython 与光明都必须回**普通 str**。"""
    光 = L连接字符串([字符串子类("a"), 字符串子类("b")], "-")
    神 = 神谕([字符串子类("a"), 字符串子类("b")], "-")
    assert type(光) is str, "光明侧回了 %s" % (type(光).__name__,)
    assert type(神) is str
    assert 光 == 神 == "a-b"


def test_不修改入参列表():
    数据 = ["a", "b", "c"]
    副本 = list(数据)
    L连接字符串(数据, "-")
    assert 数据 == 副本


# =============================================================================
# §3 必须抛 TypeError 的样本：int / float / bool / None / list / dict / bytes，
#    每种类型都在首 / 中 / 尾三个位置各测一遍（下标出现在消息里）
# =============================================================================

_非法值 = [
    ("int", 1),
    ("int零", 0),
    ("int负", -7),
    ("大整数", 2 ** 100),
    ("float", 1.5),
    ("floatNaN", float("nan")),
    ("bool真", True),
    ("bool假", False),
    ("None", None),
    ("空列表值", []),
    ("列表值", [1, 2]),
    ("空字典值", {}),
    ("字典值", {"a": 1}),
    ("bytes", b"x"),
    ("空bytes", b""),
    ("bytearray", bytearray(b"x")),
    ("元组", (1,)),
    ("集合", {1}),
    ("对象", object()),
]

非法样本 = []
for _名, _值 in _非法值:
    非法样本.append(("%s在首" % _名, [_值, "a", "b"], "-"))
    非法样本.append(("%s在中" % _名, ["a", _值, "b"], "-"))
    非法样本.append(("%s在尾" % _名, ["a", "b", _值], "-"))
    非法样本.append(("%s独占" % _名, [_值], "-"))

# 下标要真的走到两位数 / 三位数，防「下标恒为 0」这种错译混过去
非法样本 += [
    ("下标10", ["a"] * 10 + [1], "-"),
    ("下标99", ["a"] * 99 + [None], "-"),
    ("下标100", ["a"] * 100 + [1.5], "-"),
    ("下标999", ["a"] * 999 + [b"x"], "-"),
    ("下标1_空连接符", ["a", 1], ""),
    ("下标2_多字符连接符", ["a", "b", None], "-->"),
    ("中文元素后非法", ["\u4e2d\u6587", 1], "\uff0c"),
    ("emoji元素后非法", ["\U0001f600", None], "-"),
]

# 多个非法元素：CPython 报**第一个**非法元素的下标（实测）
混合非法样本 = [
    ("首尾都非法_首先报", [1, "a", None], "-"),
    ("中尾都非法_中先报", ["a", 1, None], "-"),
    ("首中都非法_首先报", [None, 1, "a"], "-"),
    ("三个都非法", [1, None, {}], "-"),
    ("全是非法", [1, 2, 3], "-"),
    ("类型不同的两个非法", ["a", 1.5, [1]], "-"),
    ("第5与第2非法_第2先报", ["a", None, "b", "c", 1], "-"),
    ("长列表里两个非法", ["a"] * 50 + [1] + ["b"] * 50 + [None], "-"),
]


@pytest.mark.parametrize("名字,列表们,连接符", 非法样本, ids=[名 for 名, _, _ in 非法样本])
def test_非str元素抛TypeError且消息逐字对齐(名字, 列表们, 连接符):
    断言等价(列表们, 连接符)


@pytest.mark.parametrize("名字,列表们,连接符", 混合非法样本, ids=[名 for 名, _, _ in 混合非法样本])
def test_多个非法元素只报第一个(名字, 列表们, 连接符):
    断言等价(列表们, 连接符)


@pytest.mark.parametrize("名字,列表们,连接符",
                         非法样本 + 混合非法样本,
                         ids=[名 for 名, _, _ in 非法样本 + 混合非法样本])
def test_异常类型钉死是TypeError本身(名字, 列表们, 连接符):
    """`type(e) is TypeError`——不是 isinstance：子类（比如自定义的 XxxTypeError）不算过。"""
    with pytest.raises(BaseException) as 光信息:
        L连接字符串(list(列表们), 连接符)
    assert type(光信息.value) is TypeError, (
        "光明侧抛的是 %s：%s" % (type(光信息.value).__name__, 光信息.value))
    with pytest.raises(BaseException) as 神信息:
        神谕(list(列表们), 连接符)
    assert type(神信息.value) is TypeError
    assert str(光信息.value) == str(神信息.value)


# 逐字取证：把几条消息的**字面量**写进断言，便于人读报告时对得上，
# 也防「两侧一起错成同一个错消息」（oracle 是 CPython 本身，这里再钉一次字面量）。
@pytest.mark.parametrize("列表们,连接符,消息", [
    ([1, "a", "b"], "-", "sequence item 0: expected str instance, int found"),
    (["a", 1, "b"], "-", "sequence item 1: expected str instance, int found"),
    (["a", "b", 1], "-", "sequence item 2: expected str instance, int found"),
    (["a", 1.5], "-", "sequence item 1: expected str instance, float found"),
    (["a", True], "-", "sequence item 1: expected str instance, bool found"),
    (["a", None], "-", "sequence item 1: expected str instance, NoneType found"),
    (["a", [1]], "-", "sequence item 1: expected str instance, list found"),
    (["a", {}], "-", "sequence item 1: expected str instance, dict found"),
    (["a", b"x"], "-", "sequence item 1: expected str instance, bytes found"),
    (["a", bytearray(b"x")], "-", "sequence item 1: expected str instance, bytearray found"),
    (["a", (1,)], "-", "sequence item 1: expected str instance, tuple found"),
    (["a", {1}], "-", "sequence item 1: expected str instance, set found"),
    (["a"] * 10 + [1], "-", "sequence item 10: expected str instance, int found"),
    (["a"] * 100 + [None], "-", "sequence item 100: expected str instance, NoneType found"),
    (["a", 1, None], "-", "sequence item 1: expected str instance, int found"),
    ([1, "a", None], "-", "sequence item 0: expected str instance, int found"),
], ids=[
    "int在首", "int在中", "int在尾", "float", "bool", "None", "list", "dict",
    "bytes", "bytearray", "tuple", "set", "下标10", "下标100",
    "混合int先报int", "混合首位先报首位",
])
def test_消息字面量逐字取证(列表们, 连接符, 消息):
    with pytest.raises(BaseException) as 光信息:
        L连接字符串(list(列表们), 连接符)
    assert type(光信息.value) is TypeError
    assert str(光信息.value) == 消息
    with pytest.raises(BaseException) as 神信息:
        神谕(list(列表们), 连接符)
    assert str(神信息.value) == 消息


def test_自定义类的类型名取的是类名():
    class 甲类:
        pass

    with pytest.raises(BaseException) as 光信息:
        L连接字符串(["a", 甲类()], "-")
    assert type(光信息.value) is TypeError
    assert str(光信息.value) == "sequence item 1: expected str instance, 甲类 found"
    with pytest.raises(BaseException) as 神信息:
        神谕(["a", 甲类()], "-")
    assert str(神信息.value) == str(光信息.value)


def test_非法元素在前时不产出任何部分结果():
    """收严后不许「先拼一半再抛」——抛异常时函数没有返回值，这里只能验「确实抛了」。"""
    with pytest.raises(BaseException) as 信息:
        L连接字符串([1, "a"], "-")
    assert type(信息.value) is TypeError


# =============================================================================
# §4 连接符 不是 str：对齐 `separator.join(parts)` 的 AttributeError
# =============================================================================

连接符非str样本 = [
    ("int", 5, ["a", "b"]),
    ("int_空列表", 5, []),
    ("int_单元素", 5, ["a"]),
    ("int_元素也非法", 5, ["a", 1]),        # 连接符先报，元素错不露头
    ("float", 1.5, ["a", "b"]),
    ("bool", True, ["a", "b"]),
    ("None", None, ["a", "b"]),
    ("列表", ["-"], ["a", "b"]),
    ("字典", {}, ["a", "b"]),
    ("元组", ("-",), ["a", "b"]),
    ("对象", object(), ["a", "b"]),
]


@pytest.mark.parametrize("名字,连接符,列表们", 连接符非str样本,
                         ids=[名 for 名, _, _ in 连接符非str样本])
def test_连接符不是str抛AttributeError(名字, 连接符, 列表们):
    断言等价(列表们, 连接符)


def test_连接符非str的消息字面量():
    with pytest.raises(BaseException) as 信息:
        L连接字符串(["a", "b"], 5)
    assert type(信息.value) is AttributeError
    assert str(信息.value) == "'int' object has no attribute 'join'"


def test_连接符检查先于元素检查():
    """`separator.join(parts)` 的属性查找发生在最前面：空列表 + 非 str 连接符也抛。"""
    断言等价([], 5)
    断言等价(["a", 1], 5)          # 元素也非法，但报的是连接符那条


# =============================================================================
# §5 默认参数：光明侧给了 `连接符 = ""`，与 builtins.py 的 `separator: str = ''` 一致
# =============================================================================

def test_连接符默认值是空串():
    assert L连接字符串(["a", "b", "c"]) == "abc"
    assert L连接字符串(["a", "b", "c"]) == "".join(["a", "b", "c"])
    assert L连接字符串([]) == ""
    assert L连接字符串(["a"]) == "a"


def test_默认参数下也照样收严():
    with pytest.raises(BaseException) as 信息:
        L连接字符串(["a", 1])
    assert type(信息.value) is TypeError
    assert str(信息.value) == "sequence item 1: expected str instance, int found"


def test_默认值在函数对象上就是空串():
    """从 __defaults__ 直接读，防「默认值被写成 None 再在体内兜底」这种伪默认。"""
    assert L连接字符串.__defaults__ == ("",)


# =============================================================================
# §6 已知不等价（如实记录，不假装等价；两处差异都钉死在断言里，
#    任一侧行为变了这些用例就会红）
# =============================================================================

def test_已知不等价_连接符是bytes():
    """bytes 有自己的 join：CPython 走 bytes.join 抛 TypeError（消息也不同），
    光明侧只认 str，抛 AttributeError。

    这条不是「漏了检查」，是光明侧刻意只对齐 str.join 的口径；要对齐 bytes.join
    得在光明里再复刻一套 bytes 语义，超出 `连接字符串` 的契约（builtins.py 的
    类型标注是 `separator: str`）。
    """
    with pytest.raises(BaseException) as 光信息:
        L连接字符串(["a", "b"], b"-")
    assert type(光信息.value) is AttributeError
    assert str(光信息.value) == "'bytes' object has no attribute 'join'"
    with pytest.raises(BaseException) as 神信息:
        神谕(["a", "b"], b"-")
    assert type(神信息.value) is TypeError
    assert str(神信息.value) == "sequence item 0: expected a bytes-like object, str found"


@pytest.mark.parametrize("名字,列表们,光明消息", [
    ("None", None, "object of type 'NoneType' has no len()"),
    ("int", 5, "object of type 'int' has no len()"),
], ids=["parts是None", "parts是int"])
def test_已知不等价_parts不可迭代时消息不同(名字, 列表们, 光明消息):
    """两侧**都抛 TypeError**（类型对齐），但消息不同：
    光明侧是 `长(列表们)` 先炸，CPython 是 `can only join an iterable`。
    光明侧拿不到「先判可迭代」的原语（那要 iter()/Sequence 协议），
    只好停在这里；类型对齐、消息不对齐，如实记录。
    """
    with pytest.raises(BaseException) as 光信息:
        L连接字符串(列表们, "-")
    with pytest.raises(BaseException) as 神信息:
        神谕(列表们, "-")
    assert type(光信息.value) is TypeError
    assert type(神信息.value) is TypeError
    assert str(光信息.value) == 光明消息
    assert str(神信息.value) == "can only join an iterable"


def test_已知不等价_parts是字典():
    """`str.join` 迭代字典拿到的是键，光明侧按下标取 → KeyError。
    契约要求 parts 是 list，这条只做记账，防将来有人以为它等价。
    """
    with pytest.raises(BaseException) as 光信息:
        L连接字符串({"a": 1, "b": 2}, "-")
    assert type(光信息.value) is KeyError
    assert 神谕({"a": 1, "b": 2}, "-") == "a-b"


@pytest.mark.parametrize("名字,列表们", [
    ("字符串当parts", "abc"),
    ("元组当parts", ("a", "b")),
], ids=["parts是str", "parts是tuple"])
def test_可按下标取的可迭代对象仍然等价(名字, 列表们):
    """str / tuple 支持 len + 下标，光明侧的循环照样走通，与 oracle 相同。"""
    断言等价(列表们, "-")


def test_已知不等价_生成器当parts():
    """生成器没有 len：光明侧 TypeError，CPython 正常连接。同样只做记账。"""
    with pytest.raises(BaseException) as 光信息:
        L连接字符串((c for c in "abc"), "-")
    assert type(光信息.value) is TypeError
    assert str(光信息.value) == "object of type 'generator' has no len()"
    assert 神谕((c for c in "abc"), "-") == "a-b-c"
