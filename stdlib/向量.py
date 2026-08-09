# -*- coding: utf-8 -*-
"""
光明标准库 - 向量和矩阵运算模块

提供向量和矩阵的基本运算功能。
"""

import math
from typing import List, Tuple, Union


class 向量:
    """向量类"""

    def __init__(self, *分量: float):
        """
        创建向量

        参数:
            *分量: 向量的分量值

        示例:
            向量(1, 2, 3)  # 三维向量 (1, 2, 3)
        """
        self._数据 = list(分量)

    @property
    def 维度(self) -> int:
        """获取向量维度"""
        return len(self._数据)

    @property
    def 数据(self) -> List[float]:
        """获取向量数据"""
        return list(self._数据)

    def 获取(self, 索引: int) -> float:
        """获取指定索引的分量"""
        return self._数据[索引]

    def 设置(self, 索引: int, 值: float):
        """设置指定索引的分量"""
        self._数据[索引] = 值

    def 模(self) -> float:
        """计算向量的模（长度）"""
        return math.sqrt(sum(x ** 2 for x in self._数据))

    def 归一化(self) -> '向量':
        """返回单位向量"""
        模 = self.模()
        if 模 == 0:
            raise RuntimeError("零向量不能归一化")
        return 向量(*[x / 模 for x in self._数据])

    def 点积(self, other: '向量') -> float:
        """
        计算点积

        参数:
            other: 另一个向量

        返回:
            点积结果
        """
        if self.维度 != other.维度:
            raise RuntimeError(f"向量维度不匹配: {self.维度} vs {other.维度}")
        return sum(a * b for a, b in zip(self._数据, other._数据))

    def 叉积(self, other: '向量') -> '向量':
        """
        计算叉积（仅三维向量）

        参数:
            other: 另一个三维向量

        返回:
            叉积结果向量
        """
        if self.维度 != 3 or other.维度 != 3:
            raise RuntimeError("叉积仅支持三维向量")
        a1, a2, a3 = self._数据
        b1, b2, b3 = other._数据
        return 向量(a2 * b3 - a3 * b2, a3 * b1 - a1 * b3, a1 * b2 - a2 * b1)

    def 夹角(self, other: '向量') -> float:
        """
        计算两个向量之间的夹角（弧度）

        参数:
            other: 另一个向量

        返回:
            夹角弧度
        """
        点积 = self.点积(other)
        模积 = self.模() * other.模()
        if 模积 == 0:
            raise RuntimeError("零向量不能计算夹角")
        return math.acos(max(-1, min(1, 点积 / 模积)))

    def 投影(self, other: '向量') -> '向量':
        """
        计算向量在另一个向量上的投影

        参数:
            other: 目标向量

        返回:
            投影向量
        """
        模平方 = other.模() ** 2
        if 模平方 == 0:
            raise RuntimeError("零向量不能计算投影")
        系数 = self.点积(other) / 模平方
        return 向量(*[系数 * x for x in other._数据])

    def __add__(self, other):
        if isinstance(other, 向量):
            if self.维度 != other.维度:
                raise RuntimeError("向量维度不匹配")
            return 向量(*[a + b for a, b in zip(self._data, other._data)])
        return 向量(*[x + other for x in self._data])

    def __sub__(self, other):
        if isinstance(other, 向量):
            if self.维度 != other.维度:
                raise RuntimeError("向量维度不匹配")
            return 向量(*[a - b for a, b in zip(self._data, other._data)])
        return 向量(*[x - other for x in self._data])

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return 向量(*[x * other for x in self._data])
        if isinstance(other, 向量):
            return self.点积(other)
        raise TypeError(f"不支持的乘法类型: {type(other)}")

    def __neg__(self):
        return 向量(*[-x for x in self._data])

    def __eq__(self, other):
        if isinstance(other, 向量):
            return self._data == other._data
        return False

    def __str__(self) -> str:
        return f"向量({', '.join(str(x) for x in self._data)})"

    def __repr__(self) -> str:
        return f"向量({', '.join(str(x) for x in self._data)})"

    def __len__(self) -> int:
        return self.维度

    def __getitem__(self, 索引: int) -> float:
        return self._data[索引]

    def __setitem__(self, 索引: int, 值: float):
        self._data[索引] = 值


class 矩阵:
    """矩阵类"""

    def __init__(self, 数据: List[List[float]]):
        """
        创建矩阵

        参数:
            数据: 二维列表，每行长度相同

        示例:
            矩阵([[1, 2], [3, 4]])  # 2x2 矩阵
        """
        if not 数据 or not 数据[0]:
            raise RuntimeError("矩阵不能为空")
        行数 = len(数据)
        列数 = len(数据[0])
        for 行 in 数据:
            if len(行) != 列数:
                raise RuntimeError("矩阵各行长度必须相同")
        self._数据 = [list(行) for 行 in 数据]
        self._行数 = 行数
        self._列数 = 列数

    @property
    def 行数(self) -> int:
        """获取行数"""
        return self._行数

    @property
    def 列数(self) -> int:
        """获取列数"""
        return self._列数

    @property
    def 形状(self) -> Tuple[int, int]:
        """获取矩阵形状 (行数, 列数)"""
        return (self._行数, self._列数)

    def 获取(self, 行: int, 列: int) -> float:
        """获取指定位置的元素"""
        return self._数据[行][列]

    def 设置(self, 行: int, 列: int, 值: float):
        """设置指定位置的元素"""
        self._数据[行][列] = 值

    def 获取行(self, 行: int) -> 向量:
        """获取指定行作为向量"""
        return 向量(*self._数据[行])

    def 获取列(self, 列: int) -> 向量:
        """获取指定列作为向量"""
        return 向量(*[self._数据[行][列] for 行 in range(self._行数)])

    def 转置(self) -> '矩阵':
        """转置矩阵"""
        新数据 = [[self._数据[行][列] for 行 in range(self._行数)] for 列 in range(self._列数)]
        return 矩阵(新数据)

    def 行列式(self) -> float:
        """计算行列式（仅方形矩阵）"""
        if self._行数 != self._列数:
            raise RuntimeError("行列式仅适用于方形矩阵")
        if self._行数 == 1:
            return self._数据[0][0]
        if self._行数 == 2:
            return self._数据[0][0] * self._数据[1][1] - self._数据[0][1] * self._数据[1][0]

        # 递归展开
        结果 = 0.0
        for j in range(self._列数):
            子矩阵 = [[self._data[i][k] for k in range(self._列数) if k != j] for i in range(1, self._行数)]
            结果 += ((-1) ** j) * self._数据[0][j] * 矩阵(子矩阵).行列式()
        return 结果

    def 逆矩阵(self) -> '矩阵':
        """计算逆矩阵（仅方形矩阵）"""
        if self._行数 != self._列数:
            raise RuntimeError("逆矩阵仅适用于方形矩阵")

        det = self.行列式()
        if det == 0:
            raise RuntimeError("矩阵不可逆（行列式为0）")

        n = self._行数
        # 伴随矩阵法
        伴随 = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                子矩阵 = [[self._data[r][c] for c in range(n) if c != j] for r in range(n) if r != i]
                伴随[j][i] = ((-1) ** (i + j)) * 矩阵(子矩阵).行列式()

        return 矩阵(伴随) * (1.0 / det)

    def __add__(self, other):
        if isinstance(other, 矩阵):
            if self.形状 != other.形状:
                raise RuntimeError(f"矩阵形状不匹配: {self.形状} vs {other.形状}")
            新数据 = [[self._data[i][j] + other._data[i][j] for j in range(self._列数)] for i in range(self._行数)]
            return 矩阵(新数据)
        raise TypeError(f"不支持的加法类型: {type(other)}")

    def __sub__(self, other):
        if isinstance(other, 矩阵):
            if self.形状 != other.形状:
                raise RuntimeError(f"矩阵形状不匹配: {self.形状} vs {other.形状}")
            新数据 = [[self._data[i][j] - other._data[i][j] for j in range(self._列数)] for i in range(self._行数)]
            return 矩阵(新数据)
        raise TypeError(f"不支持的减法类型: {type(other)}")

    def __mul__(self, other):
        """矩阵乘法或标量乘法"""
        if isinstance(other, (int, float)):
            新数据 = [[x * other for x in 行] for 行 in self._data]
            return 矩阵(新数据)
        if isinstance(other, 矩阵):
            if self._列数 != other._行数:
                raise RuntimeError(f"矩阵乘法维度不匹配: {self.形状} x {other.形状}")
            新数据 = [[0.0] * other._列数 for _ in range(self._行数)]
            for i in range(self._行数):
                for j in range(other._列数):
                    for k in range(self._列数):
                        新数据[i][j] += self._data[i][k] * other._data[k][j]
            return 矩阵(新数据)
        if isinstance(other, 向量):
            if self._列数 != other.维度:
                raise RuntimeError(f"矩阵向量乘法维度不匹配")
            结果 = [0.0] * self._行数
            for i in range(self._行数):
                for j in range(self._列数):
                    结果[i] += self._data[i][j] * other[j]
            return 向量(*结果)
        raise TypeError(f"不支持的乘法类型: {type(other)}")

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return self.__mul__(other)
        raise TypeError(f"不支持的乘法类型: {type(other)}")

    def __neg__(self):
        return 矩阵([[-x for x in 行] for 行 in self._data])

    def __eq__(self, other):
        if isinstance(other, 矩阵):
            return self._data == other._data
        return False

    def __str__(self) -> str:
        return '\n'.join(['[' + ', '.join(f'{x:8.3f}' for x in 行) + ']' for 行 in self._data])

    def __repr__(self) -> str:
        return f"矩阵({self._data})"


def 创建向量(*分量: float) -> 向量:
    """创建向量"""
    return 向量(*分量)


def 零向量(维度: int) -> 向量:
    """创建零向量"""
    return 向量(*[0.0] * 维度)


def 单位向量(维度: int, 索引: int) -> 向量:
    """
    创建单位向量（第 索引 个分量为1，其余为0）

    参数:
        维度: 向量维度
        索引: 非零分量的索引

    返回:
        单位向量
    """
    数据 = [0.0] * 维度
    数据[索引] = 1.0
    return 向量(*数据)


def 创建矩阵(数据: List[List[float]]) -> 矩阵:
    """创建矩阵"""
    return 矩阵(数据)


def 零矩阵(行数: int, 列数: int) -> 矩阵:
    """创建零矩阵"""
    return 矩阵([[0.0] * 列数 for _ in range(行数)])


def 单位矩阵(阶数: int) -> 矩阵:
    """创建单位矩阵"""
    return 矩阵([[1.0 if i == j else 0.0 for j in range(阶数)] for i in range(阶数)])


def 向量加法(v1: 向量, v2: 向量) -> 向量:
    """向量加法"""
    return v1 + v2


def 向量减法(v1: 向量, v2: 向量) -> 向量:
    """向量减法"""
    return v1 - v2


def 向量点积(v1: 向量, v2: 向量) -> float:
    """向量点积"""
    return v1.点积(v2)


def 向量叉积(v1: 向量, v2: 向量) -> 向量:
    """向量叉积（仅三维）"""
    return v1.叉积(v2)


def 向量模(v: 向量) -> float:
    """向量模"""
    return v.模()


def 向量夹角(v1: 向量, v2: 向量) -> float:
    """向量夹角（弧度）"""
    return v1.夹角(v2)


def 矩阵加法(m1: 矩阵, m2: 矩阵) -> 矩阵:
    """矩阵加法"""
    return m1 + m2


def 矩阵乘法(m1: 矩阵, m2: 矩阵) -> 矩阵:
    """矩阵乘法"""
    return m1 * m2


def 矩阵转置(m: 矩阵) -> 矩阵:
    """矩阵转置"""
    return m.转置()


def 矩阵行列式(m: 矩阵) -> float:
    """矩阵行列式"""
    return m.行列式()


def 矩阵逆矩阵(m: 矩阵) -> 矩阵:
    """矩阵逆矩阵"""
    return m.逆矩阵()


__all__ = [
    '向量', '矩阵',
    '创建向量', '零向量', '单位向量',
    '创建矩阵', '零矩阵', '单位矩阵',
    '向量加法', '向量减法', '向量点积', '向量叉积',
    '向量模', '向量夹角',
    '矩阵加法', '矩阵乘法', '矩阵转置',
    '矩阵行列式', '矩阵逆矩阵',
]