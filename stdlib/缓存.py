# -*- coding: utf-8 -*-
"""
光明标准库 - 缓存模块

提供便捷的缓存操作函数，底层复用 对象池缓存 模块的 LRU缓存、简单缓存等类。
"""

from 对象池缓存 import (
    LRU缓存,
    简单缓存,
    内存缓存,
    定时缓存,
    二级缓存,
    缓存装饰器,
    LRU缓存装饰器,
    记忆化,
    创建LRU缓存,
    创建简单缓存,
    创建定时缓存,
    创建缓存,
    设置缓存,
    获取缓存,
    清除缓存,
)
from typing import Any, Callable, Optional


class 缓存管理器:
    """统一的缓存管理器"""

    def __init__(self, 类型: str = 'lru', **参数):
        """
        初始化缓存管理器

        参数:
            类型: 缓存类型 ('lru', 'simple', 'memory', 'timed')
            **参数: 传递给具体缓存构造函数的参数
        """
        if 类型 == 'lru':
            self._缓存 = LRU缓存(**参数)
        elif 类型 == 'simple':
            self._缓存 = 简单缓存(**参数)
        elif 类型 == 'memory':
            self._缓存 = 内存缓存(**参数)
        elif 类型 == 'timed':
            self._缓存 = 定时缓存(**参数)
        else:
            raise ValueError(f"不支持的缓存类型: {类型}")

    def 获取(self, 键: Any, 默认值: Any = None) -> Any:
        """获取缓存值"""
        return self._缓存.获取(键, 默认值)

    def 设置(self, 键: Any, 值: Any):
        """设置缓存值"""
        self._缓存.设置(键, 值)

    def 删除(self, 键: Any) -> bool:
        """删除缓存项"""
        return self._缓存.删除(键)

    def 包含(self, 键: Any) -> bool:
        """检查是否包含键"""
        return self._缓存.包含(键)

    def 清空(self):
        """清空缓存"""
        self._缓存.清空()

    def 大小(self) -> int:
        """获取缓存大小"""
        return self._缓存.大小()