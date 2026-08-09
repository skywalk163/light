# -*- coding: utf-8 -*-
"""
光明标准库 - 列表工具模块（Python 实现）

与 列表工具.light 保持接口一致。
"""

from typing import List, Any, Optional


def 求和(列表: List[float]) -> float:
    """列表求和"""
    总和 = 0.0
    for 元素 in 列表:
        总和 += 元素
    return 总和


def 最大值(列表: List[Any]) -> Any:
    """列表最大值"""
    if not 列表:
        raise ValueError("列表为空")
    return max(列表)


def 最小值(列表: List[Any]) -> Any:
    """列表最小值"""
    if not 列表:
        raise ValueError("列表为空")
    return min(列表)


def 平均值(列表: List[float]) -> float:
    """列表平均值"""
    if not 列表:
        return 0.0
    return sum(列表) / len(列表)


def 反转列表(列表: List[Any]) -> List[Any]:
    """反转列表"""
    return list(reversed(列表))


def 包含(列表: List[Any], 元素: Any) -> bool:
    """判断列表是否包含元素"""
    return 元素 in 列表


def 查找索引(列表: List[Any], 元素: Any) -> int:
    """查找元素在列表中的索引"""
    try:
        return 列表.index(元素)
    except ValueError:
        return -1


def 计数(列表: List[Any], 元素: Any) -> int:
    """计数元素在列表中出现的次数"""
    return 列表.count(元素)


def 连接(列表甲: List[Any], 列表乙: List[Any]) -> List[Any]:
    """连接两个列表"""
    return 列表甲 + 列表乙


def 范围(起始: int, 结束: int) -> List[int]:
    """生成范围列表"""
    return list(range(起始, 结束))


__all__ = [
    '求和', '最大值', '最小值', '平均值',
    '反转列表', '包含', '查找索引', '计数',
    '连接', '范围',
]