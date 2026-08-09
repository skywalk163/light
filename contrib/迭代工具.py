"""
光明标准库 - 迭代工具模块

提供迭代器工具功能，包括：
- 计数器
- 分组
- 排列组合迭代
- 无限迭代器
"""

import itertools
from typing import List, Any, Dict, Iterable, Tuple


def 计数器(可迭代对象: Iterable[Any]):
    """统计可迭代对象中元素出现的次数"""
    from collections import Counter
    return Counter(可迭代对象)


def 分组(可迭代对象: Iterable[Any], 键函数=None):
    """按键函数分组可迭代对象"""
    if 键函数 is None:
        键函数 = lambda x: x
    
    结果 = {}
    for 元素 in 可迭代对象:
        键 = 键函数(元素)
        if 键 not in 结果:
            结果[键] = []
        结果[键].append(元素)
    return 结果


def 分组字典(可迭代对象: Iterable[Tuple[Any, Any]]):
    """按键分组键值对可迭代对象"""
    结果 = {}
    for 键, 值 in 可迭代对象:
        if 键 not in 结果:
            结果[键] = []
        结果[键].append(值)
    return 结果


def 排列(可迭代对象: Iterable[Any], 长度: int):
    """生成排列"""
    return list(itertools.permutations(可迭代对象, 长度))


def 组合(可迭代对象: Iterable[Any], 长度: int):
    """生成组合"""
    return list(itertools.combinations(可迭代对象, 长度))


def 组合带重复(可迭代对象: Iterable[Any], 长度: int):
    """生成带重复的组合"""
    return list(itertools.combinations_with_replacement(可迭代对象, 长度))


def 笛卡尔积(*可迭代对象列表):
    """生成笛卡尔积"""
    return list(itertools.product(*可迭代对象列表))


def 链(可迭代对象列表: Iterable[Iterable[Any]]):
    """连接多个可迭代对象"""
    return itertools.chain(*可迭代对象列表)


def 链到列表(可迭代对象列表: Iterable[Iterable[Any]]):
    """连接多个可迭代对象并转换为列表"""
    return list(itertools.chain(*可迭代对象列表))


def 重复(元素: Any, 次数: int = None):
    """重复元素指定次数或无限次"""
    if 次数 is None:
        return itertools.repeat(元素)
    return itertools.repeat(元素, 次数)


def 重复到列表(元素: Any, 次数: int):
    """重复元素指定次数并转换为列表"""
    return list(itertools.repeat(元素, 次数))


def 计数(起始: int = 0, 步长: int = 1):
    """无限计数"""
    return itertools.count(起始, 步长)


def 计数到列表(起始: int = 0, 步长: int = 1, 数量: int = 10):
    """计数指定数量并转换为列表"""
    return list(itertools.islice(itertools.count(起始, 步长), 数量))


def 循环(可迭代对象: Iterable[Any]):
    """无限循环可迭代对象"""
    return itertools.cycle(可迭代对象)


def 循环到列表(可迭代对象: Iterable[Any], 数量: int):
    """循环可迭代对象指定次数并转换为列表"""
    return list(itertools.islice(itertools.cycle(可迭代对象), 数量))


def 压缩(*可迭代对象列表):
    """压缩多个可迭代对象"""
    return list(zip(*可迭代对象列表))


def 枚举(可迭代对象: Iterable[Any], 起始: int = 0):
    """枚举可迭代对象"""
    return list(itertools.islice(enumerate(可迭代对象, 起始), None))


def 累积(可迭代对象: Iterable[Any], 函数=None):
    """累积计算"""
    if 函数 is None:
        函数 = lambda x, y: x + y
    return list(itertools.accumulate(可迭代对象, 函数))


def 累积和(可迭代对象: Iterable[Any]):
    """累积求和"""
    return list(itertools.accumulate(可迭代对象))


def 累积积(可迭代对象: Iterable[Any]):
    """累积求积"""
    import operator
    return list(itertools.accumulate(可迭代对象, operator.mul))


def 分组相邻(可迭代对象: Iterable[Any], 大小: int):
    """按指定大小分组相邻元素"""
    迭代器 = iter(可迭代对象)
    return list(iter(lambda: list(itertools.islice(迭代器, 大小)), []))


def 滑动窗口(可迭代对象: Iterable[Any], 窗口大小: int):
    """生成滑动窗口"""
    迭代器 = iter(可迭代对象)
    窗口 = list(itertools.islice(迭代器, 窗口大小))
    if len(窗口) == 窗口大小:
        yield tuple(窗口)
    for 元素 in 迭代器:
        窗口 = 窗口[1:] + [元素]
        yield tuple(窗口)


def 滑动窗口到列表(可迭代对象: Iterable[Any], 窗口大小: int):
    """生成滑动窗口并转换为列表"""
    return list(滑动窗口(可迭代对象, 窗口大小))


def 成对(可迭代对象: Iterable[Any]):
    """生成相邻元素对"""
    return list(itertools.pairwise(可迭代对象))


def 去重(可迭代对象: Iterable[Any], 键函数=None):
    """去除重复元素"""
    已见 = set()
    for 元素 in 可迭代对象:
        键 = 键函数(元素) if 键函数 else 元素
        if 键 not in 已见:
            已见.add(键)
            yield 元素


def 去重到列表(可迭代对象: Iterable[Any], 键函数=None):
    """去除重复元素并转换为列表"""
    return list(去重(可迭代对象, 键函数))


def 筛选(可迭代对象: Iterable[Any], 条件函数):
    """筛选满足条件的元素"""
    return list(filter(条件函数, 可迭代对象))


def 映射(可迭代对象: Iterable[Any], 函数):
    """映射函数到可迭代对象"""
    return list(map(函数, 可迭代对象))


def 过滤假值(可迭代对象: Iterable[Any]):
    """过滤假值（False, None, 0, '', [], {}）"""
    return list(filter(None, 可迭代对象))


def 枚举带索引(可迭代对象: Iterable[Any], 起始: int = 0):
    """枚举带索引"""
    return list(enumerate(可迭代对象, 起始))


def 反转(可迭代对象: Iterable[Any]):
    """反转可迭代对象"""
    return list(reversed(可迭代对象))


def 切片(可迭代对象: Iterable[Any], 开始=None, 结束=None, 步长=None):
    """切片可迭代对象"""
    return list(itertools.islice(可迭代对象, 开始, 结束, 步长))


def 最大N个(可迭代对象: Iterable[Any], N: int, 键函数=None):
    """获取最大的N个元素"""
    return list(itertools.islice(itertools.heapq.nlargest(N, 可迭代对象, 键函数), N))


def 最小N个(可迭代对象: Iterable[Any], N: int, 键函数=None):
    """获取最小的N个元素"""
    return list(itertools.islice(itertools.heapq.nsmallest(N, 可迭代对象, 键函数), N))


def 排列数(数量: int, 选取: int):
    """计算排列数"""
    from math import factorial
    return factorial(数量) // factorial(数量 - 选取)


def 组合数(数量: int, 选取: int):
    """计算组合数"""
    from math import factorial
    if 选取 > 数量 - 选取:
        选取 = 数量 - 选取
    result = 1
    for i in range(选取):
        result = result * (数量 - i) // (i + 1)
    return result


__all__ = [
    '计数器', '分组', '分组字典',
    '排列', '组合', '组合带重复', '笛卡尔积',
    '链', '链到列表', '重复', '重复到列表',
    '计数', '计数到列表', '循环', '循环到列表',
    '压缩', '枚举', '累积', '累积和', '累积积',
    '分组相邻', '滑动窗口', '滑动窗口到列表', '成对',
    '去重', '去重到列表', '筛选', '映射', '过滤假值',
    '枚举带索引', '反转', '切片',
    '最大N个', '最小N个', '排列数', '组合数'
]