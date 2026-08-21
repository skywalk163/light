# -*- coding: utf-8 -*-
"""
任务D：事件总线（纯光明实现）定向测试
覆盖：多监听者顺序、中止传播、一次性、通配/命名空间、错误隔离、
      取消令牌传播、重复取消订阅幂等。
"""
import os
import sys

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 事件总线 import 事件总线, 取消令牌, 中止符号


# 语言缺陷记录：某些由特定前缀合成的标识符（句柄* / 处理器* / 取消*）作为
# 「己.X 为 Y 或 己.X[k] 为 Y」的左值时，codegen 会误编成 `==`（比较而非赋值）。
# 本测试全部避开这类命名，且把该缺陷登记进移交清单交回任务 A。


def _新总线():
    return 事件总线()


class Test顺序与中止:
    def test_多监听者按注册顺序执行(self):
        b = _新总线()
        次序 = []
        b.订阅("甲", lambda e, p: 次序.append("一"))
        b.订阅("甲", lambda e, p: 次序.append("二"))
        b.发布("甲", None)
        assert 次序 == ["一", "二"]

    def test_载荷传递(self):
        b = _新总线()
        载荷箱 = []
        b.订阅("甲", lambda e, p: 载荷箱.append(p))
        b.发布("甲", {"值": 7})
        assert 载荷箱 == [{"值": 7}]

    def test_中止符号可中止后续传播(self):
        b = _新总线()
        次序 = []
        b.订阅("甲", lambda e, p: 次序.append("前"))
        b.订阅("甲", lambda e, p: (次序.append("拦"), 中止符号)[1])
        b.订阅("甲", lambda e, p: 次序.append("后"))
        结果 = b.发布("甲", None)
        assert 次序 == ["前", "拦"]
        assert 结果.已中止 is True


class Test一次性:
    def test_一次性监听只触发一次(self):
        b = _新总线()
        次数 = []
        b.订阅一次("甲", lambda e, p: 次数.append(p))
        b.发布("甲", 1)
        b.发布("甲", 2)
        assert 次数 == [1]

    def test_非一次性监听持续触发(self):
        b = _新总线()
        次数 = []
        b.订阅("甲", lambda e, p: 次数.append(p))
        b.发布("甲", 1)
        b.发布("甲", 2)
        assert 次数 == [1, 2]


class Test通配与命名空间:
    def test_前缀通配匹配命名空间(self):
        b = _新总线()
        收集 = []
        b.订阅("工具:*", lambda e, p: 收集.append(e))
        b.发布("工具:调用-开始", 1)
        b.发布("工具:调用-结束", 2)
        b.发布("配线:甲", 3)  # 不匹配
        assert 收集 == ["工具:调用-开始", "工具:调用-结束"]

    def test_精确订阅不误匹配(self):
        b = _新总线()
        收集 = []
        b.订阅("工具:甲", lambda e, p: 收集.append(e))
        b.发布("工具:甲", 1)
        b.发布("工具:乙", 2)
        assert 收集 == ["工具:甲"]


class Test错误隔离:
    def test_单个监听者抛异常不影响其它且被上报(self):
        b = _新总线()
        次数 = []

        def 出错_handler(e, p):
            raise ValueError("某错误")

        b.订阅("甲", 出错_handler)
        b.订阅("甲", lambda e, p: 次数.append(p))
        结果 = b.发布("甲", 9)
        assert 次数 == [9]
        assert len(结果.错误表) == 1
        assert isinstance(结果.错误表[0], ValueError)
        # 命中数只统计成功执行
        assert 结果.命中数 == 1


class Test取消订阅:
    def test_取消订阅后不再触发(self):
        b = _新总线()
        收集 = []
        句柄 = b.订阅("甲", lambda e, p: 收集.append(p))
        b.发布("甲", 1)
        assert b.取消订阅(句柄) is True
        b.发布("甲", 2)
        assert 收集 == [1]

    def test_重复取消订阅幂等(self):
        b = _新总线()
        句柄 = b.订阅("甲", lambda e, p: None)
        assert b.取消订阅(句柄) is True
        assert b.取消订阅(句柄) is False
        assert b.取消订阅(99999) is False


class Test取消令牌:
    def test_注册取消处理器并触发(self):
        t = 取消令牌()
        触发 = []
        t.注册取消处理器(lambda: 触发.append("甲"))
        assert t.已取消 is False
        assert t.取消() is True
        assert t.已取消 is True
        assert 触发 == ["甲"]

    def test_取消调用幂等(self):
        t = 取消令牌()
        assert t.取消() is True
        assert t.取消() is False

    def test_取消处理器抛异常被隔离收集(self):
        t = 取消令牌()

        def 崩():
            raise RuntimeError("坏了")

        t.注册取消处理器(崩)
        t.注册取消处理器(lambda: None)
        assert t.取消() is True
        assert len(t.错误集) == 1
        assert isinstance(t.错误集[0], RuntimeError)