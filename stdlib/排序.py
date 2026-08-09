# -*- coding: utf-8 -*-
"""
光明标准库 - 排序算法模块

提供多种排序算法实现，包括快速排序、归并排序等。
"""

import random
from typing import List, Any, Callable, Optional


def 快速排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    快速排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表

    示例:
        快速排序([3, 1, 4, 1, 5])  # [1, 1, 3, 4, 5]
    """
    if len(数据) <= 1:
        return list(数据)

    def _排序(列表):
        if len(列表) <= 1:
            return 列表
        基准 = 列表[len(列表) // 2]
        左 = [x for x in 列表 if _比较(x, 基准) < 0]
        中 = [x for x in 列表 if _比较(x, 基准) == 0]
        右 = [x for x in 列表 if _比较(x, 基准) > 0]
        if 反向:
            return _排序(右) + 中 + _排序(左)
        return _排序(左) + 中 + _排序(右)

    def _比较(a, b):
        if 键:
            a, b = 键(a), 键(b)
        if a < b:
            return -1
        elif a > b:
            return 1
        return 0

    return _排序(list(数据))


def 归并排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    归并排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表
    """
    if len(数据) <= 1:
        return list(数据)

    def _比较(a, b):
        if 键:
            a, b = 键(a), 键(b)
        if 反向:
            return a > b
        return a < b

    def _归并(左, 右):
        结果 = []
        i = j = 0
        while i < len(左) and j < len(右):
            if _比较(左[i], 右[j]):
                结果.append(左[i])
                i += 1
            else:
                结果.append(右[j])
                j += 1
        结果.extend(左[i:])
        结果.extend(右[j:])
        return 结果

    def _排序(列表):
        if len(列表) <= 1:
            return 列表
        中 = len(列表) // 2
        左 = _排序(列表[:中])
        右 = _排序(列表[中:])
        return _归并(左, 右)

    return _排序(list(数据))


def 冒泡排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    冒泡排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表
    """
    结果 = list(数据)
    n = len(结果)

    def _比较(a, b):
        if 键:
            a, b = 键(a), 键(b)
        if 反向:
            return a < b
        return a > b

    for i in range(n):
        for j in range(0, n - i - 1):
            if _比较(结果[j], 结果[j + 1]):
                结果[j], 结果[j + 1] = 结果[j + 1], 结果[j]

    return 结果


def 插入排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    插入排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表
    """
    结果 = list(数据)

    def _比较(a, b):
        if 键:
            a, b = 键(a), 键(b)
        if 反向:
            return a < b
        return a > b

    for i in range(1, len(结果)):
        当前 = 结果[i]
        j = i - 1
        while j >= 0 and _比较(结果[j], 当前):
            结果[j + 1] = 结果[j]
            j -= 1
        结果[j + 1] = 当前

    return 结果


def 选择排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    选择排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表
    """
    结果 = list(数据)

    def _比较(a, b):
        if 键:
            a, b = 键(a), 键(b)
        if 反向:
            return a > b
        return a < b

    for i in range(len(结果)):
        索引 = i
        for j in range(i + 1, len(结果)):
            if _比较(结果[j], 结果[索引]):
                索引 = j
        结果[i], 结果[索引] = 结果[索引], 结果[i]

    return 结果


def 堆排序(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    堆排序

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）

    返回:
        排序后的新列表
    """
    import heapq

    结果 = list(数据)
    if 键 is not None:
        if 反向:
            heapq.heapify([(-键(x), x) for x in 结果])
            return [heapq.heappop([(-键(x), x) for x in 结果])[1] for _ in range(len(结果))]
        else:
            heapq.heapify([(键(x), x) for x in 结果])
            return [heapq.heappop([(键(x), x) for x in 结果])[1] for _ in range(len(结果))]
    else:
        heapq.heapify(结果)
        return [heapq.heappop(结果) for _ in range(len(结果))]


def 排序(数据: List[Any], 键: Callable = None, 反向: bool = False, 算法: str = '快速') -> List[Any]:
    """
    通用排序函数（默认使用快速排序）

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列（默认升序）
        算法: 排序算法：'快速', '归并', '冒泡', '插入', '选择', '堆'

    返回:
        排序后的新列表
    """
    算法映射 = {
        '快速': 快速排序,
        '归并': 归并排序,
        '冒泡': 冒泡排序,
        '插入': 插入排序,
        '选择': 选择排序,
        '堆': 堆排序,
    }
    排序函数 = 算法映射.get(算法)
    if 排序函数 is None:
        raise ValueError(f"不支持的排序算法: '{算法}'，可选: {', '.join(算法映射.keys())}")
    return 排序函数(数据, 键=键, 反向=反向)


def 排序稳定(数据: List[Any], 键: Callable = None, 反向: bool = False) -> List[Any]:
    """
    稳定排序（使用归并排序）

    参数:
        数据: 待排序列表
        键: 排序键函数（可选）
        反向: 是否降序排列

    返回:
        排序后的新列表
    """
    return 归并排序(数据, 键=键, 反向=反向)


def 排序检查(数据: List[Any], 键: Callable = None, 反向: bool = False) -> bool:
    """
    检查列表是否已排序

    参数:
        数据: 待检查的列表
        键: 键函数（可选）
        反向: 是否检查降序

    返回:
        是否已排序
    """
    if len(数据) <= 1:
        return True

    for i in range(len(数据) - 1):
        if 键:
            if 反向:
                if 键(数据[i]) < 键(数据[i + 1]):
                    return False
            else:
                if 键(数据[i]) > 键(数据[i + 1]):
                    return False
        else:
            if 反向:
                if 数据[i] < 数据[i + 1]:
                    return False
            else:
                if 数据[i] > 数据[i + 1]:
                    return False
    return True


__all__ = [
    '快速排序', '归并排序', '冒泡排序', '插入排序', '选择排序', '堆排序',
    '排序', '排序稳定', '排序检查',
]