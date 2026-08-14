# -*- coding: utf-8 -*-
"""
数学统计工具

提供均值、中位数、众数、标准差、方差等常用统计函数。

用法:
    from 标准库.数学统计 import 均值, 中位数, 众数, 标准差, 方差

示例:
    设 数据 = [1, 2, 3, 4, 5, 5, 6, 7, 8, 9]
    打印(均值(数据))
    打印(中位数(数据))
    打印(众数(数据))
"""

import math as _math
from collections import Counter as _Counter
from typing import List, Optional, Union, Tuple

数值类型 = Union[int, float]


def 均值(数据: List[数值类型]) -> float:
    """计算算术平均数

    Args:
        数据: 数值列表

    Returns:
        算术平均数

    Raises:
        ValueError: 如果数据为空
    """
    if not 数据:
        raise ValueError("数据列表不能为空")
    return sum(数据) / len(数据)


def 中位数(数据: List[数值类型]) -> float:
    """计算中位数

    Args:
        数据: 数值列表

    Returns:
        中位数

    Raises:
        ValueError: 如果数据为空
    """
    if not 数据:
        raise ValueError("数据列表不能为空")

    排序数据 = sorted(数据)
    n = len(排序数据)

    if n % 2 == 1:
        return float(排序数据[n // 2])
    else:
        return (排序数据[n // 2 - 1] + 排序数据[n // 2]) / 2


def 众数(数据: List[数值类型]) -> List[数值类型]:
    """计算众数（出现次数最多的值）

    Args:
        数据: 数值列表

    Returns:
        众数列表（可能有多个众数）

    Raises:
        ValueError: 如果数据为空
    """
    if not 数据:
        raise ValueError("数据列表不能为空")

    计数 = _Counter(数据)
    最大次数 = max(计数.values())

    return [值 for 值, 次数 in 计数.items() if 次数 == 最大次数]


def 众数单个(数据: List[数值类型]) -> Optional[数值类型]:
    """计算单个众数（出现次数最多的值，只返回第一个）

    Args:
        数据: 数值列表

    Returns:
        众数值，如果数据为空则返回 None
    """
    try:
        modes = 众数(数据)
        return modes[0] if modes else None
    except ValueError:
        return None


def 方差(数据: List[数值类型], 总体: bool = False) -> float:
    """计算方差

    Args:
        数据: 数值列表
        总体: 是否计算总体方差（默认 False，计算样本方差）

    Returns:
        方差值

    Raises:
        ValueError: 如果数据不足
    """
    if not 数据:
        raise ValueError("数据列表不能为空")
    if len(数据) < 2:
        raise ValueError("至少需要两个数据点")

    平均值 = 均值(数据)
    平方差和 = sum((x - 平均值) ** 2 for x in 数据)

    if 总体:
        return 平方差和 / len(数据)
    else:
        return 平方差和 / (len(数据) - 1)


def 标准差(数据: List[数值类型], 总体: bool = False) -> float:
    """计算标准差

    Args:
        数据: 数值列表
        总体: 是否计算总体标准差（默认 False，计算样本标准差）

    Returns:
        标准差
    """
    return _math.sqrt(方差(数据, 总体))


def 极差(数据: List[数值类型]) -> float:
    """计算极差（最大值与最小值的差）

    Args:
        数据: 数值列表

    Returns:
        极差值

    Raises:
        ValueError: 如果数据为空
    """
    if not 数据:
        raise ValueError("数据列表不能为空")
    return max(数据) - min(数据)


def 四分位数(数据: List[数值类型]) -> Tuple[float, float, float]:
    """计算四分位数

    Args:
        数据: 数值列表

    Returns:
        (Q1, Q2, Q3) 元组，分别表示第一、第二（中位数）、第三四分位数
    """
    if not 数据:
        raise ValueError("数据列表不能为空")

    排序数据 = sorted(数据)
    n = len(排序数据)

    def 分位数(数据, 位置):
        # 线性插值计算分位数
        idx = 位置 * (len(数据) - 1)
        整数部分 = int(idx)
        小数部分 = idx - 整数部分
        if 整数部分 + 1 < len(数据):
            return 数据[整数部分] * (1 - 小数部分) + 数据[整数部分 + 1] * 小数部分
        return float(数据[整数部分])

    q1 = 分位数(排序数据, 0.25)
    q2 = 分位数(排序数据, 0.5)
    q3 = 分位数(排序数据, 0.75)

    return (q1, q2, q3)


def 偏度(数据: List[数值类型]) -> float:
    """计算偏度（衡量数据分布对称性）

    Args:
        数据: 数值列表

    Returns:
        偏度值

    Raises:
        ValueError: 如果数据不足
    """
    if len(数据) < 3:
        raise ValueError("至少需要三个数据点")

    平均值 = 均值(数据)
    n = len(数据)
    标准差_ = 标准差(数据)

    if 标准差_ == 0:
        return 0.0

    三次矩 = sum((x - 平均值) ** 3 for x in 数据) / n
    return 三次矩 / (标准差_ ** 3)


def 峰度(数据: List[数值类型]) -> float:
    """计算峰度（衡量数据分布尖峰程度）

    Args:
        数据: 数值列表

    Returns:
        峰度值（超额峰度，正态分布为 0）

    Raises:
        ValueError: 如果数据不足
    """
    if len(数据) < 4:
        raise ValueError("至少需要四个数据点")

    平均值 = 均值(数据)
    n = len(数据)
    标准差_ = 标准差(数据)

    if 标准差_ == 0:
        return 0.0

    四次矩 = sum((x - 平均值) ** 4 for x in 数据) / n
    return 四次矩 / (标准差_ ** 4) - 3


def 变异系数(数据: List[数值类型]) -> float:
    """计算变异系数（标准差与均值的比值）

    Args:
        数据: 数值列表

    Returns:
        变异系数

    Raises:
        ValueError: 如果均值为 0
    """
    平均值 = 均值(数据)
    if 平均值 == 0:
        raise ValueError("均值为 0，无法计算变异系数")

    return 标准差(数据) / 平均值


def 协方差(数据1: List[数值类型], 数据2: List[数值类型]) -> float:
    """计算两个数据集的协方差

    Args:
        数据1: 第一个数值列表
        数据2: 第二个数值列表

    Returns:
        协方差值

    Raises:
        ValueError: 如果数据长度不同或不足
    """
    if len(数据1) != len(数据2):
        raise ValueError("两个数据集长度必须相同")
    if len(数据1) < 2:
        raise ValueError("至少需要两个数据点")

    均值1 = 均值(数据1)
    均值2 = 均值(数据2)
    n = len(数据1)

    return sum((x - 均值1) * (y - 均值2) for x, y in zip(数据1, 数据2)) / (n - 1)


def 相关系数(数据1: List[数值类型], 数据2: List[数值类型]) -> float:
    """计算皮尔逊相关系数

    Args:
        数据1: 第一个数值列表
        数据2: 第二个数值列表

    Returns:
        相关系数，范围 -1 到 1
    """
    协方差_ = 协方差(数据1, 数据2)
    标准差1 = 标准差(数据1)
    标准差2 = 标准差(数据2)

    if 标准差1 == 0 or 标准差2 == 0:
        return 0.0

    return 协方差_ / (标准差1 * 标准差2)


def 频率分布(数据: List[数值类型], 组数: Optional[int] = None) -> List[Tuple[float, float, int]]:
    """计算频率分布

    Args:
        数据: 数值列表
        组数: 分组数量，默认为自动计算（使用 Sturges 公式）

    Returns:
        [(下限, 上限, 频数), ...] 列表
    """
    if not 数据:
        return []

    if 组数 is None:
        组数 = max(1, round(1 + 3.322 * _math.log10(len(数据))))

    最小值 = min(数据)
    最大值 = max(数据)
    组距 = (最大值 - 最小值) / 组数 if 组数 > 1 else 1

    if 组距 == 0:
        组距 = 1

    分组 = []
    for i in range(组数):
        下限 = 最小值 + i * 组距
        上限 = 下限 + 组距
        频数 = sum(1 for x in 数据 if 下限 <= x < 上限) if i < 组数 - 1 else sum(1 for x in 数据 if 下限 <= x <= 上限)
        分组.append((round(下限, 4), round(上限, 4), 频数))

    return 分组


def 数据汇总(数据: List[数值类型]) -> dict:
    """对数据进行全面汇总统计

    Args:
        数据: 数值列表

    Returns:
        包含各项统计指标的字典
    """
    if not 数据:
        return {"错误": "数据为空"}

    try:
        q1, q2, q3 = 四分位数(数据)
        汇总 = {
            "数量": len(数据),
            "均值": round(均值(数据), 4),
            "中位数": round(q2, 4),
            "众数": 众数单个(数据),
            "标准差": round(标准差(数据), 4),
            "方差": round(方差(数据), 4),
            "极差": round(极差(数据), 4),
            "最小值": min(数据),
            "最大值": max(数据),
            "Q1": round(q1, 4),
            "Q3": round(q3, 4),
            "四分位距": round(q3 - q1, 4),
            "偏度": round(偏度(数据), 4),
            "峰度": round(峰度(数据), 4),
            "变异系数": round(变异系数(数据), 4),
        }
        # 修复均值四舍五入
        汇总["均值"] = round(均值(数据), 4)
        return 汇总
    except Exception as e:
        return {"错误": str(e)}


def 加权均值(数据: List[数值类型], 权重: List[数值类型]) -> float:
    """计算加权平均数

    Args:
        数据: 数值列表
        权重: 权重列表

    Returns:
        加权平均数

    Raises:
        ValueError: 如果数据长度不同或权重为空
    """
    if len(数据) != len(权重):
        raise ValueError("数据和权重长度必须相同")
    if not 数据:
        raise ValueError("数据列表不能为空")

    权重和 = sum(权重)
    if 权重和 == 0:
        raise ValueError("权重和不能为 0")

    return sum(x * w for x, w in zip(数据, 权重)) / 权重和