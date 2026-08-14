"""
段言标准库 - 集合操作模块

提供列表/集合操作函数：去重、合并、排序、过滤等
"""

from typing import Any, Callable, List, Optional
import random


def 去重(items: List[Any]) -> List[Any]:
    """去除重复元素（保持顺序）"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def 合并(*lists: List[Any]) -> List[Any]:
    """合并多个列表"""
    result = []
    for lst in lists:
        result.extend(lst)
    return result


def 交集(甲: List[Any], 乙: List[Any]) -> List[Any]:
    """两个列表的交集（保持顺序）"""
    set_乙 = set(乙)
    return [item for item in 甲 if item in set_乙]


def 差集(甲: List[Any], 乙: List[Any]) -> List[Any]:
    """甲有而乙没有的元素（保持顺序）"""
    set_乙 = set(乙)
    return [item for item in 甲 if item not in set_乙]


def 补集(甲: List[Any], 乙: List[Any]) -> List[Any]:
    """对称差集：出现于甲或乙但不同时出现"""
    set_甲, set_乙 = set(甲), set(乙)
    return list(set_甲 ^ set_乙)


def 分组(items: List[Any], key_func) -> dict:
    """按指定函数分组"""
    result = {}
    for item in items:
        key = key_func(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


def 排序(items: List[Any], 反转: bool = False) -> List[Any]:
    """排序列表"""
    return sorted(items, reverse=反转)


def 反转顺序(items: List[Any]) -> List[Any]:
    """反转列表顺序"""
    return list(reversed(items))


def 打乱(items: List[Any]) -> List[Any]:
    """随机打乱列表"""
    result = list(items)
    random.shuffle(result)
    return result


def 扁平(items: List[Any]) -> List[Any]:
    """扁平化嵌套列表（一层）"""
    result = []
    for item in items:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result


def 取部分(items: List[Any], 开始: int, 结束: Optional[int] = None) -> List[Any]:
    """取列表部分元素（切片）"""
    return items[开始:结束]


def 条件过滤(items: List[Any], predicate) -> List[Any]:
    """按条件过滤"""
    return [item for item in items if predicate(item)]


def 条件映射(items: List[Any], mapper) -> List[Any]:
    """按函数映射"""
    return [mapper(item) for item in items]