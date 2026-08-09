"""
光明标准库 - 数据验证模块

提供数据类型判断、范围检查、格式验证等功能。
"""

import re
from typing import Any, Callable, List, Union

Number = Union[int, float]


def 是整数(值: Any) -> bool:
    """
    判断值是否为整数

    参数:
        值: 要判断的值

    返回:
        True 如果是整数
    """
    return isinstance(值, int) and not isinstance(值, bool)


def 是浮点(值: Any) -> bool:
    """
    判断值是否为浮点数

    参数:
        值: 要判断的值

    返回:
        True 如果是浮点数
    """
    return isinstance(值, float)


def 是字符串(值: Any) -> bool:
    """
    判断值是否为字符串

    参数:
        值: 要判断的值

    返回:
        True 如果是字符串
    """
    return isinstance(值, str)


def 是列表(值: Any) -> bool:
    """
    判断值是否为列表

    参数:
        值: 要判断的值

    返回:
        True 如果是列表
    """
    return isinstance(值, list)


def 是字典(值: Any) -> bool:
    """
    判断值是否为字典

    参数:
        值: 要判断的值

    返回:
        True 如果是字典
    """
    return isinstance(值, dict)


def 是数字(值: Any) -> bool:
    """
    判断值是否为数字（整数或浮点数）

    参数:
        值: 要判断的值

    返回:
        True 如果是整数或浮点数
    """
    return isinstance(值, (int, float)) and not isinstance(值, bool)


def 在范围内(值: Number, 最小: Number, 最大: Number) -> bool:
    """
    判断数值是否在范围内（闭区间）

    参数:
        值: 要检查的数值
        最小: 范围最小值
        最大: 范围最大值

    返回:
        True 如果 最小 <= 值 <= 最大
    """
    return 最小 <= 值 <= 最大


def 字符串非空(值: Any) -> bool:
    """
    判断字符串是否非空

    参数:
        值: 要判断的值

    返回:
        True 如果是非空字符串
    """
    return isinstance(值, str) and len(值) > 0


def 列表非空(值: Any) -> bool:
    """
    判断列表是否非空

    参数:
        值: 要判断的值

    返回:
        True 如果是非空列表
    """
    return isinstance(值, list) and len(值) > 0


def 是邮箱(值: str) -> bool:
    """
    简单邮箱格式验证

    参数:
        值: 要验证的字符串

    返回:
        True 如果符合邮箱格式
    """
    if not isinstance(值, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, 值))


def 是网址(值: str) -> bool:
    """
    简单URL格式验证

    参数:
        值: 要验证的字符串

    返回:
        True 如果符合URL格式
    """
    if not isinstance(值, str):
        return False
    pattern = r'^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=]+'
    return bool(re.match(pattern, 值))


def 长度在范围(值: Any, 最小: int, 最大: int) -> bool:
    """
    检查字符串或列表的长度是否在范围内（闭区间）

    参数:
        值: 要检查的字符串或列表
        最小: 最小长度
        最大: 最大长度

    返回:
        True 如果 最小 <= len(值) <= 最大
    """
    try:
        长度 = len(值)
    except TypeError:
        return False
    return 最小 <= 长度 <= 最大


def 验证规则(值: Any, 规则列表: List[Callable]) -> dict:
    """
    对值应用多个验证规则

    参数:
        值: 要验证的值
        规则列表: 验证函数列表，每个函数接受一个值并返回 bool

    返回:
        {'通过': bool, '失败规则': list} - 整体是否通过及失败的规则索引列表
    """
    失败规则 = []
    for 索引, 规则 in enumerate(规则列表):
        try:
            if not 规则(值):
                失败规则.append(索引)
        except Exception:
            失败规则.append(索引)
    return {
        '通过': len(失败规则) == 0,
        '失败规则': 失败规则,
    }


__all__ = [
    '是整数', '是浮点', '是字符串', '是列表', '是字典', '是数字',
    '在范围内', '字符串非空', '列表非空',
    '是邮箱', '是网址',
    '长度在范围', '验证规则',
]
