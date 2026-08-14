"""
迭代器工具 — duanpub 桥接模块

基于 Python itertools 库封装，函数名对齐 duanpub/packages/迭代器工具/源.duan。

duanpub 原始包通过 C FFI 实现懒迭代器，
本桥接模块用 Python itertools 模块替代，提供等价的迭代器工具功能。
"""

import itertools as _itertools
import collections as _collections
import functools as _functools


# =============================================================================
# 核心迭代器操作
# =============================================================================

def 迭代器_映射(func, iterable):
    """对可迭代对象每个元素应用函数，返回迭代器"""
    if not callable(func):
        raise Exception("迭代器_映射失败: 函数不是可调用对象")
    try:
        return map(func, iterable)
    except Exception as e:
        raise Exception("迭代器_映射失败: " + str(e))


def 迭代器_过滤(predicate, iterable):
    """过滤可迭代对象，返回迭代器"""
    try:
        if predicate is None:
            return filter(None, iterable)
        return filter(predicate, iterable)
    except Exception as e:
        raise Exception("迭代器_过滤失败: " + str(e))


def 迭代器_链式(*iterables):
    """链式连接多个可迭代对象"""
    try:
        return _itertools.chain(*iterables)
    except Exception as e:
        raise Exception("迭代器_链式失败: " + str(e))


def 迭代器_压缩(*iterables):
    """压缩多个可迭代对象，返回对应位置元组的迭代器"""
    try:
        return zip(*iterables)
    except Exception as e:
        raise Exception("迭代器_压缩失败: " + str(e))


def 迭代器_计数(start=0, step=1):
    """无限递增计数器"""
    try:
        return _itertools.count(start=start, step=step)
    except Exception as e:
        raise Exception("迭代器_计数失败: " + str(e))


def 迭代器_循环(iterable):
    """无限循环可迭代对象"""
    try:
        return _itertools.cycle(iterable)
    except Exception as e:
        raise Exception("迭代器_循环失败: " + str(e))


def 迭代器_重复(value, times=None):
    """重复返回同一个值"""
    try:
        if times is None:
            return _itertools.repeat(value)
        return _itertools.repeat(value, times)
    except Exception as e:
        raise Exception("迭代器_重复失败: " + str(e))


def 迭代器_分块(iterable, size):
    """将可迭代对象分块为指定大小的子序列"""
    if size < 1:
        raise Exception("迭代器_分块失败: 分块大小必须大于0")
    try:
        it = iter(iterable)
        while True:
            chunk = list(_itertools.islice(it, size))
            if not chunk:
                break
            yield chunk
    except Exception as e:
        raise Exception("迭代器_分块失败: " + str(e))


def 迭代器_窗口(iterable, n):
    """滑动窗口迭代器"""
    if n < 1:
        raise Exception("迭代器_窗口失败: 窗口大小必须大于0")
    try:
        it = iter(iterable)
        window = _collections.deque(_itertools.islice(it, n), maxlen=n)
        if len(window) == n:
            yield tuple(window)
        for item in it:
            window.append(item)
            yield tuple(window)
    except Exception as e:
        raise Exception("迭代器_窗口失败: " + str(e))


def 迭代器_扁平化(iterable):
    """扁平化嵌套可迭代对象"""
    try:
        for item in iterable:
            if hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
                yield from item
            else:
                yield item
    except Exception as e:
        raise Exception("迭代器_扁平化失败: " + str(e))


def 迭代器_枚举(iterable, start=0):
    """枚举可迭代对象，返回 (索引, 值) 对"""
    try:
        return enumerate(iterable, start=start)
    except Exception as e:
        raise Exception("迭代器_枚举失败: " + str(e))


def 迭代器_累计(iterable, func=None):
    """累积迭代"""
    if func is not None and not callable(func):
        raise Exception("迭代器_累计失败: 函数不是可调用对象")
    try:
        if func is None:
            return _itertools.accumulate(iterable)
        return _itertools.accumulate(iterable, func)
    except Exception as e:
        raise Exception("迭代器_累计失败: " + str(e))


def 迭代器_分组(iterable, key=None):
    """按 key 函数分组可迭代对象"""
    try:
        sorted_iter = sorted(iterable, key=key) if key else sorted(iterable)
        return _itertools.groupby(sorted_iter, key=key)
    except Exception as e:
        raise Exception("迭代器_分组失败: " + str(e))


def 迭代器_切片(iterable, start, stop=None, step=1):
    """对可迭代对象进行切片"""
    try:
        if stop is None:
            return _itertools.islice(iterable, start, None, step)
        return _itertools.islice(iterable, start, stop, step)
    except Exception as e:
        raise Exception("迭代器_切片失败: " + str(e))


def 迭代器_排列(iterable, r=None):
    """生成排列"""
    try:
        return _itertools.permutations(iterable, r=r)
    except Exception as e:
        raise Exception("迭代器_排列失败: " + str(e))


def 迭代器_组合(iterable, r):
    """生成组合"""
    try:
        return _itertools.combinations(iterable, r)
    except Exception as e:
        raise Exception("迭代器_组合失败: " + str(e))