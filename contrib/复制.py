"""
光明标准库 - 复制模块

封装 copy 模块，提供对象的浅复制和深复制功能。
"""

import copy
from typing import Any


def 浅复制(对象: Any) -> Any:
    """
    浅复制对象
    
    参数:
        对象: 要复制的对象
    
    返回:
        浅复制的新对象
    """
    return copy.copy(对象)


def 深复制(对象: Any, 备忘录: dict = None) -> Any:
    """
    深复制对象
    
    参数:
        对象: 要复制的对象
        备忘录: 复制备忘录字典（用于避免循环引用）
    
    返回:
        深复制的新对象
    """
    return copy.deepcopy(对象, 备忘录)


def 复制(对象: Any, 深: bool = False) -> Any:
    """
    复制对象（便捷函数）
    
    参数:
        对象: 要复制的对象
        深: 是否深复制
    
    返回:
        复制的新对象
    """
    if 深:
        return 深复制(对象)
    return 浅复制(对象)


__all__ = [
    '浅复制',
    '深复制',
    '复制',
]
