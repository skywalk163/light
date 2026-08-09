# -*- coding: utf-8 -*-
"""
光明标准库 - 复数运算模块

提供复数运算功能。
"""

import math
from typing import Tuple, Union


class 复数:
    """复数类，表示 a + bi 形式的复数"""

    def __init__(self, 实部: float = 0.0, 虚部: float = 0.0):
        """
        创建复数

        参数:
            实部: 实部
            虚部: 虚部
        """
        self._实部 = 实部
        self._虚部 = 虚部

    @property
    def 实部(self) -> float:
        """获取实部"""
        return self._实部

    @property
    def 虚部(self) -> float:
        """获取虚部"""
        return self._虚部

    def 共轭(self) -> '复数':
        """返回共轭复数"""
        return 复数(self._实部, -self._虚部)

    def 模(self) -> float:
        """计算模（绝对值）"""
        return math.sqrt(self._实部 ** 2 + self._虚部 ** 2)

    def 幅角(self) -> float:
        """计算幅角（弧度）"""
        return math.atan2(self._虚部, self._实部)

    def 极坐标(self) -> Tuple[float, float]:
        """
        转换为极坐标形式

        返回:
            (模, 幅角) 元组
        """
        return (self.模(), self.幅角())

    def __add__(self, other):
        if isinstance(other, 复数):
            return 复数(self._实部 + other._实部, self._虚部 + other._虚部)
        return 复数(self._实部 + other, self._虚部)

    def __sub__(self, other):
        if isinstance(other, 复数):
            return 复数(self._实部 - other._实部, self._虚部 - other._虚部)
        return 复数(self._实部 - other, self._虚部)

    def __mul__(self, other):
        if isinstance(other, 复数):
            实 = self._实部 * other._实部 - self._虚部 * other._虚部
            虚 = self._实部 * other._虚部 + self._虚部 * other._实部
            return 复数(实, 虚)
        return 复数(self._实部 * other, self._虚部 * other)

    def __truediv__(self, other):
        if isinstance(other, 复数):
            分母 = other._实部 ** 2 + other._虚部 ** 2
            实 = (self._实部 * other._实部 + self._虚部 * other._虚部) / 分母
            虚 = (self._虚部 * other._实部 - self._实部 * other._虚部) / 分母
            return 复数(实, 虚)
        return 复数(self._实部 / other, self._虚部 / other)

    def __neg__(self):
        return 复数(-self._实部, -self._虚部)

    def __eq__(self, other):
        if isinstance(other, 复数):
            return self._实部 == other._实部 and self._虚部 == other._虚部
        return self._虚部 == 0 and self._实部 == other

    def __abs__(self):
        return self.模()

    def __str__(self) -> str:
        if self._虚部 >= 0:
            return f"{self._实部}+{self._虚部}i"
        return f"{self._实部}{self._虚部}i"

    def __repr__(self) -> str:
        return f"复数({self._实部}, {self._虚部})"

    def __hash__(self):
        return hash((self._实部, self._虚部))

    def __pow__(self, n: int) -> '复数':
        """复数的整数次幂"""
        模 = self.模()
        幅角 = self.幅角()
        新模 = 模 ** n
        新幅角 = 幅角 * n
        return 复数(新模 * math.cos(新幅角), 新模 * math.sin(新幅角))


def 创建复数(实部: float = 0.0, 虚部: float = 0.0) -> 复数:
    """创建复数"""
    return 复数(实部, 虚部)


def 极坐标转复数(模: float, 幅角: float) -> 复数:
    """
    极坐标转复数

    参数:
        模: 模长
        幅角: 幅角（弧度）

    返回:
        复数
    """
    return 复数(模 * math.cos(幅角), 模 * math.sin(幅角))


def 复数加法(z1: 复数, z2: 复数) -> 复数:
    """复数加法"""
    return z1 + z2


def 复数减法(z1: 复数, z2: 复数) -> 复数:
    """复数减法"""
    return z1 - z2


def 复数乘法(z1: 复数, z2: 复数) -> 复数:
    """复数乘法"""
    return z1 * z2


def 复数除法(z1: 复数, z2: 复数) -> 复数:
    """复数除法"""
    return z1 / z2


def 复数模(z: 复数) -> float:
    """计算复数模"""
    return z.模()


def 复数幅角(z: 复数) -> float:
    """计算复数幅角"""
    return z.幅角()


def 复数共轭(z: 复数) -> 复数:
    """计算共轭复数"""
    return z.共轭()


def 复数幂(z: 复数, n: int) -> 复数:
    """复数幂运算"""
    return z ** n


def 复数相等(z1: 复数, z2: 复数) -> bool:
    """判断两个复数是否相等"""
    return z1 == z2


__all__ = [
    '复数', '创建复数', '极坐标转复数',
    '复数加法', '复数减法', '复数乘法', '复数除法',
    '复数模', '复数幅角', '复数共轭', '复数幂', '复数相等',
]