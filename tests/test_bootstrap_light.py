# -*- coding: utf-8 -*-
"""
test_bootstrap_light.py —— C2-3 新写的 5 个纯光明自举模块测试
覆盖：断言工具 / 字符串工具 / 数据结构 / JSON编解码 / 日期时间。
"""
import os
import sys
import time as _t
from datetime import datetime as _dt, timezone as _tz

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 断言工具 import 断言真, 断言假, 断言等于, 断言不为空
from 字符串工具 import (
    转大写, 转小写, 首字母大写, 反转字符串, 分割字符串, 连接字符串,
    子串查找, 以子串开头, 以子串结尾, 替换多个空白, 英文分词, 字符计数,
    左填充, 重复字符串,
)
from 数据结构 import 栈, 队列, 双端队列, 优先队列
from 数据结构 import 创建栈, 入栈, 出栈, 栈是否为空, 栈大小
from JSON编解码 import 编码, 解码
from 日期时间 import 两个数字, 格式化当前时间, 获取年份, 当前时间戳


class Test断言工具:
    def test_pass(self):
        断言真(1 == 1)
        断言假(1 != 1)
        断言等于(1 + 1, 2)
        断言不为空([1, 2])

    def test_fail_raises(self):
        with pytest.raises(Exception):
            断言真(1 == 2)
        with pytest.raises(Exception):
            断言等于("a", "b")


class Test字符串工具:
    def test_case(self):
        assert 转大写("abc") == "ABC"
        assert 转小写("ABC") == "abc"
        assert 首字母大写("hello world") == "Hello world"

    def test_reverse_slice(self):
        assert 反转字符串("abc") == "cba"
        assert 分割字符串("a,b,c", ",") == ["a", "b", "c"]
        assert 连接字符串(["x", "y"], "-") == "x-y"

    def test_search(self):
        assert 子串查找("hello", "ll") == 2
        assert 子串查找("hello", "zz") == -1
        assert 以子串开头("hello", "he") is True
        assert 以子串结尾("hello", "lo") is True
        assert 字符计数("aba", "a") == 2

    def test_misc(self):
        assert 左填充("7", 3, "0") == "007"
        assert 重复字符串("ab", 3) == "ababab"
        assert 替换多个空白("a  b\tc", " ") == "a b c"
        assert 英文分词("hello world, foo") == ["hello", "world", "foo"]


class Test数据结构:
    def test_stack(self):
        s = 栈()
        s.压入(1)
        s.压入(2)
        # codegen 将 弹出/清空 译为 pop/clear，测试走编译后属性名
        assert s.pop() == 2
        assert s.顶部() == 1
        assert s.空() is False
        assert s.大小() == 1

    def test_queue(self):
        q = 队列()
        q.入队("a")
        q.入队("b")
        assert q.出队() == "a"
        assert q.队首() == "b"

    def test_deque(self):
        d = 双端队列()
        d.右入队(1)
        d.左入队(0)
        d.右入队(2)
        assert d.左出队() == 0
        assert d.右出队() == 2

    def test_priority_queue(self):
        pq = 优先队列()
        pq.入队(3, "c")
        pq.入队(1, "a")
        pq.入队(2, "b")
        assert pq.出队() == "a"
        assert pq.出队() == "b"

    def test_list_helpers(self):
        st = 创建栈()
        assert 栈是否为空(st) is True
        入栈(st, 5)
        入栈(st, 9)
        assert 栈大小(st) == 2
        assert 出栈(st) == 9


class TestJSON编解码:
    def test_encode_basic(self):
        assert 编码("hi") == '"hi"'
        assert 编码(None) == "null"
        assert 编码(True) == "true"
        assert 编码([1, "a", None]) == '[1, "a", null]'

    def test_decode_basic(self):
        assert 解码('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}
        assert 解码("[1, 2, 3]") == [1, 2, 3]
        assert 解码("null") is None
        assert 解码("true") is True
        assert 解码("false") is False

    def test_escape(self):
        assert 解码('"a\\nb\\tc"') == "a\nb\tc"
        assert 解码('"\\u4f60\\u597d"') == "你好"
        assert 编码("行\n你好") == '"行\\n你好"'

    def test_roundtrip(self):
        obj = {"name": "值", "nums": [1, 2.5, 3], "ok": True, "none": None, "nested": {"k": "v"}}
        text = 编码(obj)
        back = 解码(text)
        assert back == obj

    def test_number_types(self):
        assert 解码("1") == 1
        assert 解码("-2") == -2
        assert 解码("3.5") == 3.5
        assert isinstance(解码("42"), int)
        assert isinstance(解码("4.25"), float)


class Test日期时间:
    def test_pad(self):
        assert 两个数字(5) == "05"
        assert 两个数字(12) == "12"

    def test_year(self):
        now = 当前时间戳()
        assert 获取年份(now) == _dt.now(_tz.utc).astimezone().year

    def test_format_shape(self):
        s = 格式化当前时间(当前时间戳())
        # YYYY-MM-DD HH:MM:SS 共 19 字符
        assert len(s) == 19
        assert s[4] == "-" and s[7] == "-" and s[10] == " " and s[13] == ":" and s[16] == ":"