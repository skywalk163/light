# -*- coding: utf-8 -*-
"""
test_地板搬迁_字符串_S2.py —— 地板自举 S2 / A 路：stdlib/内置核心字符串.light 差分测试

判据：**光明版 vs Python 原版口径逐条对跑**。

oracle（基准）为什么不直接 import stdlib/builtins.py 的同名函数：
    本轮的目的就是把 builtins.py 里那 17 个函数体换成「转发到光明」。一旦接线完成，
    `builtins.字符串反转` 与 `内置核心字符串.字符串反转` 是同一份实现，拿它当基准就成了
    自证（永远相等，测不出任何东西）。所以这里把 builtins.py 搬迁前的 Python 函数体
    **逐字抄成独立的 oracle**（见 _ORACLE，每条都标了对应的 builtins.py 行号），
    光明侧的返回值必须与它逐条相等。搬迁后 builtins.py 变了，oracle 不变，
    差分才仍然有效。

覆盖的边界：空串 / 单字符 / 非 ASCII（中文、emoji）/ 超长（1200 字符）/ 负索引 /
越界切片 / 宽度小于文本长度 / 次数为 0 与负数 / 子串为空串 / 找不到子串（-1）/
错误路径（两版必须抛同一个异常类型）。
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

import 内置核心字符串 as 光明


# ── oracle：stdlib/builtins.py 搬迁前的 Python 函数体，逐字照抄 ──────────────────
# 光明段落不写默认参数（负数/字符默认值在光明侧解析失败），默认值留在 builtins.py 的
# Python 签名里；所以 oracle 这边也一律收满参，由用例显式传 -1 / ' '。

def _o_字符串获取(text, index):            # builtins.py:506
    return text[index]


def _o_截取(text, start, end):             # builtins.py:511
    return text[start:end]


def _o_去除空白(text):                     # builtins.py:542
    return text.strip()


def _o_字符串包含(text, substring):        # builtins.py:559
    return substring in text


def _o_开头(text, prefix):                 # builtins.py:564
    return text.startswith(prefix)


def _o_结尾(text, suffix):                 # builtins.py:569
    return text.endswith(suffix)


def _o_查找子串(text, substring):          # builtins.py:574
    return text.find(substring)


def _o_最后索引(text, substring):          # builtins.py:579
    return text.rfind(substring)


def _o_替换字符串次数(text, old, new, count):   # builtins.py:584
    if count < 0:
        return text.replace(old, new)
    return text.replace(old, new, count)


def _o_截取到末尾(text, start):            # builtins.py:591
    return text[start:]


def _o_字符串计数(text, substring):        # builtins.py:596
    return text.count(substring)


def _o_字符串重复(text, times):            # builtins.py:601
    return text * times


def _o_字符串反转(text):                   # builtins.py:606
    return text[::-1]


def _o_转标题(text):                       # builtins.py:611
    return text.title()


def _o_字符串对齐居中(text, width, fillchar):   # builtins.py:628
    return text.center(width, fillchar)


def _o_字符串对齐左(text, width, fillchar):     # builtins.py:633
    return text.ljust(width, fillchar)


def _o_字符串对齐右(text, width, fillchar):     # builtins.py:638
    return text.rjust(width, fillchar)


_长文 = "甲乙丙" * 400          # 1200 字符，含非 ASCII
_EMOJI = "ab\U0001F600cd"       # 星芒面外字符（4 字节 UTF-8）

# 名字 → (oracle 可调用, [入参 tuple, ...])
_表 = {
    "字符串获取": (_o_字符串获取, [
        ("abc", 0), ("abc", 2), ("abc", -1), ("abc", -3),      # 负索引
        ("a", 0),                                              # 单字符
        ("中文abc", 0), ("中文abc", -1),                        # 非 ASCII
        (_EMOJI, 2),
        (_长文, 0), (_长文, 1199), (_长文, -1),                 # 超长
    ]),
    "截取": (_o_截取, [
        ("abcdef", 1, 3), ("abcdef", 0, 0), ("", 0, 1),         # 空串
        ("abcdef", 0, 100), ("abcdef", -100, 100),              # 越界切片
        ("abcdef", 4, 2),                                       # 起始 > 结束 → ""
        ("abcdef", -3, -1), ("abcdef", -1, -3),                 # 负索引
        ("a", 0, 1),
        ("中文abc", 1, 3), (_EMOJI, 1, 4),
        (_长文, 0, 5), (_长文, 1195, 5000),
    ]),
    "去除空白": (_o_去除空白, [
        ("",), (" ",), ("  x  ",), ("\t\r\n x \n\t",),
        ("x",), ("中文  ",), ("  " + _EMOJI + "  ",),
        ("   " + _长文 + "   ",),
        ("无空白中文",),
    ]),
    "字符串包含": (_o_字符串包含, [
        ("abc", "b"), ("abc", "abc"), ("abc", "z"),              # 找不到
        ("abc", ""), ("", ""), ("", "a"),                        # 子串为空串 / 空串
        ("中文abc", "文"), (_EMOJI, "\U0001F600"),
        (_长文, "甲乙丙甲"), (_长文, "丁"),
    ]),
    "开头": (_o_开头, [
        ("abc", "a"), ("abc", "abc"), ("abc", "b"), ("abc", ""),
        ("", ""), ("", "a"), ("中文abc", "中文"), (_EMOJI, "a"),
        (_长文, "甲乙"), (_长文, "乙"),
    ]),
    "结尾": (_o_结尾, [
        ("abc", "c"), ("abc", "abc"), ("abc", "b"), ("abc", ""),
        ("", ""), ("", "a"), ("中文abc", "bc"), (_EMOJI, "cd"),
        (_长文, "乙丙"), (_长文, "甲"),
    ]),
    "查找子串": (_o_查找子串, [
        ("abcabc", "c"), ("abcabc", "abc"), ("abc", "z"),        # -1
        ("abc", ""), ("", ""), ("", "a"),
        ("中文abc", "abc"), (_EMOJI, "\U0001F600"),
        (_长文, "丙甲"), (_长文, "丁"),
    ]),
    "最后索引": (_o_最后索引, [
        ("abcabc", "c"), ("abcabc", "abc"), ("abc", "z"),        # -1
        ("abc", ""), ("", ""), ("", "a"),
        ("中文abc", "文"), (_EMOJI, "\U0001F600"),
        (_长文, "丙甲"), (_长文, "丁"),
    ]),
    "替换字符串次数": (_o_替换字符串次数, [
        ("aaa", "a", "b", -1),                                   # 次数为负 → 全替换
        ("aaa", "a", "b", -5),
        ("aaa", "a", "b", 0),                                    # 次数为 0 → 原样
        ("aaa", "a", "b", 2), ("aaa", "a", "b", 99),
        ("", "a", "b", -1), ("", "", "x", -1),
        ("abc", "", "-", -1), ("abc", "", "-", 2),               # 旧串为空串
        ("abc", "z", "y", -1),                                   # 找不到
        ("中文中文", "中", "华", -1), ("中文中文", "中", "华", 1),
        (_EMOJI, "\U0001F600", "!", -1),
        (_长文, "甲", "X", 3), (_长文, "甲乙丙", "", -1),
    ]),
    "截取到末尾": (_o_截取到末尾, [
        ("abcdef", 0), ("abcdef", 2), ("abcdef", 6),
        ("abcdef", 99),                                          # 越界 → ""
        ("abcdef", -2), ("abcdef", -100),                        # 负索引
        ("", 0), ("", 5), ("a", 1),
        ("中文abc", 1), (_EMOJI, 2),
        (_长文, 1000), (_长文, -3),
    ]),
    "字符串计数": (_o_字符串计数, [
        ("abcabc", "a"), ("aaa", "aa"),                          # 重叠只算 1 次
        ("abc", "z"),                                            # 0
        ("abc", ""), ("", ""), ("", "a"),                        # 子串为空串
        ("中文中文", "中"), (_EMOJI, "\U0001F600"),
        (_长文, "甲乙丙"), (_长文, "丁"),
    ]),
    "字符串重复": (_o_字符串重复, [
        ("ab", 0),                                               # 次数为 0
        ("ab", -2), ("ab", -1),                                  # 次数为负
        ("ab", 1), ("ab", 3),
        ("", 5), ("", 0),
        ("中", 3), (_EMOJI, 2),
        ("甲乙丙", 400),                                          # 超长产物
    ]),
    "字符串反转": (_o_字符串反转, [
        ("",),                                                   # 空串
        ("a",), ("中",),                                          # 单字符
        ("abcd",), ("ab",),
        ("中文abc",), (_EMOJI,),
        ("a b\tc",),
        (_长文,),                                                 # 超长
    ]),
    "转标题": (_o_转标题, [
        ("",), ("hello world",), ("HELLO WORLD",),
        ("a",), ("a1b c2d",), ("it's ok",),
        ("中文 abc",), (_EMOJI,), ("  x  ",),
        (_长文,),
    ]),
    "字符串对齐居中": (_o_字符串对齐居中, [
        ("ab", 6, "*"), ("ab", 5, "*"),                          # 奇数缺口
        ("ab", 2, "*"), ("ab", 1, "*"), ("ab", 0, "*"),          # 宽度 <= 文本长度
        ("ab", -3, "*"),
        ("", 4, "-"), ("", 0, "-"),
        ("a", 3, " "), ("中文", 6, "·"), (_EMOJI, 9, "."),
        (_长文, 5, "*"), ("甲", 1200, "-"),
    ]),
    "字符串对齐左": (_o_字符串对齐左, [
        ("ab", 5, "-"), ("ab", 2, "-"), ("ab", 1, "-"),          # 宽度 <= 文本长度
        ("ab", -3, "-"),
        ("", 3, "*"), ("", 0, "*"),
        ("a", 2, " "), ("中", 4, " "), (_EMOJI, 9, "."),
        (_长文, 5, "-"), ("甲", 1200, "-"),
    ]),
    "字符串对齐右": (_o_字符串对齐右, [
        ("ab", 5, "-"), ("ab", 2, "-"), ("ab", 1, "-"),          # 宽度 <= 文本长度
        ("ab", -3, "-"),
        ("", 3, "*"), ("", 0, "*"),
        ("a", 2, " "), ("中", 4, " "), (_EMOJI, 9, "."),
        (_长文, 5, "-"), ("甲", 1200, "-"),
    ]),
}


def _展开():
    出 = []
    for 名字 in sorted(_表):
        _, 入参表 = _表[名字]
        for 序, 入参 in enumerate(入参表):
            出.append(pytest.param(名字, 入参, id="%s#%d" % (名字, 序)))
    return 出


@pytest.mark.parametrize("名字, 入参", _展开())
def test_光明版与Python原版逐条等价(名字, 入参):
    oracle, _ = _表[名字]
    实得 = getattr(光明, 名字)(*入参)
    应得 = oracle(*入参)
    assert 实得 == 应得, "%s%r：光明得 %r，Python 原版得 %r" % (名字, 入参, 实得, 应得)


# ── 错误路径：两版必须抛**同一个**异常类型 ────────────────────────────────────
# 期望类型不是我硬编的，是先跑 oracle 实测出来的（见下面第一个 raises），
# 光明侧再按同一个类型断言。
_错误表 = [
    pytest.param("字符串获取", ("", 0), IndexError, id="字符串获取-空串越界"),
    pytest.param("字符串获取", ("abc", 3), IndexError, id="字符串获取-正向越界"),
    pytest.param("字符串获取", ("abc", -4), IndexError, id="字符串获取-负向越界"),
    pytest.param("字符串重复", ("ab", "3"), TypeError, id="字符串重复-次数非整数"),
    pytest.param("字符串对齐左", ("ab", 5, "xy"), TypeError, id="字符串对齐左-填充字符超长"),
    pytest.param("字符串对齐右", ("ab", 5, ""), TypeError, id="字符串对齐右-填充字符为空"),
    pytest.param("字符串对齐居中", ("ab", 5, "xy"), TypeError, id="字符串对齐居中-填充字符超长"),
    pytest.param("截取到末尾", ("abc", "1"), TypeError, id="截取到末尾-起始非整数"),
]


@pytest.mark.parametrize("名字, 入参, 期望异常", _错误表)
def test_错误路径两版抛同一异常类型(名字, 入参, 期望异常):
    oracle, _ = _表[名字]
    with pytest.raises(期望异常):
        oracle(*入参)
    with pytest.raises(期望异常):
        getattr(光明, 名字)(*入参)


def test_跑的确实是light而不是同名py():
    assert getattr(光明, "__light_source__", "").endswith(".light"), (
        "内置核心字符串 不是由 .light 加载的，__light_source__=%r"
        % getattr(光明, "__light_source__", None))
    assert os.path.basename(光明.__light_source__) == "内置核心字符串.light"


def test_十七个段落全部可调用且名字逐字对齐builtins():
    缺 = [名 for 名 in _表 if not callable(getattr(光明, 名, None))]
    assert 缺 == [], "光明模块缺这些段落（门禁做名字咬合，缺一个就红）：%s" % 缺
    assert len(_表) == 17
