# -*- coding: utf-8 -*-
"""
光明标准库 - 统计函数模块

提供统计计算功能，包括均值、中位数、标准差等。
"""

import statistics
import math
from typing import List, Dict, Any, Optional


def 均值(数据: List[float]) -> float:
    """
    计算算术平均值

    参数:
        数据: 数值列表

    返回:
        平均值

    示例:
        均值([1, 2, 3, 4, 5])  # 3.0
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.mean(数据)


def 中位数(数据: List[float]) -> float:
    """
    计算中位数

    参数:
        数据: 数值列表

    返回:
        中位数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.median(数据)


def 众数(数据: list) -> Any:
    """
    计算众数（出现频率最高的值）

    参数:
        数据: 数据列表

    返回:
        众数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    try:
        return statistics.mode(数据)
    except statistics.StatisticsError:
        raise RuntimeError("无法确定众数（多个值出现次数相同）")


def 多众数(数据: list) -> List[Any]:
    """
    计算多个众数（所有出现频率最高的值）

    参数:
        数据: 数据列表

    返回:
        众数列表
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    try:
        return statistics.multimode(数据)
    except Exception as e:
        raise RuntimeError(f"计算多众数失败: {e}")


def 标准差(数据: List[float]) -> float:
    """
    计算总体标准差

    参数:
        数据: 数值列表

    返回:
        标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pstdev(数据)


def 样本标准差(数据: List[float]) -> float:
    """
    计算样本标准差（分母 n-1）

    参数:
        数据: 数值列表

    返回:
        样本标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.stdev(数据)


def 方差(数据: List[float]) -> float:
    """
    计算总体方差

    参数:
        数据: 数值列表

    返回:
        方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pvariance(数据)


def 样本方差(数据: List[float]) -> float:
    """
    计算样本方差（分母 n-1）

    参数:
        数据: 数值列表

    返回:
        样本方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.variance(数据)


def 最小值(数据: List[float]) -> float:
    """计算最小值"""
    if not 数据:
        raise RuntimeError("数据列表为空")
    return min(数据)


def 最大值(数据: List[float]) -> float:
    """计算最大值"""
    if not 数据:
        raise RuntimeError("数据列表为空")
    return max(数据)


def 极差(数据: List[float]) -> float:
    """
    计算极差（最大值 - 最小值）

    参数:
        数据: 数值列表

    返回:
        极差
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return max(数据) - min(数据)


def 求和(数据: List[float]) -> float:
    """计算总和"""
    return sum(数据)


def 四分位数(数据: List[float]) -> Dict[str, float]:
    """
    计算四分位数

    参数:
        数据: 数值列表

    返回:
        {'Q1': 下四分位数, 'Q2': 中位数, 'Q3': 上四分位数}
    """
    if len(数据) < 4:
        raise RuntimeError("数据点太少（至少需要4个）")
    排序数据 = sorted(数据)
    n = len(排序数据)
    return {
        'Q1': statistics.median(排序数据[:n // 2]),
        'Q2': statistics.median(排序数据),
        'Q3': statistics.median(排序数据[(n + 1) // 2:]),
    }


def 百分位数(数据: List[float], 百分位: float) -> float:
    """
    计算百分位数

    参数:
        数据: 数值列表
        百分位: 百分位 (0-100)

    返回:
        百分位数值
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    if 百分位 < 0 or 百分位 > 100:
        raise RuntimeError("百分位必须在 0-100 之间")
    排序数据 = sorted(数据)
    k = (len(排序数据) - 1) * 百分位 / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return 排序数据[int(k)]
    return 排序数据[f] * (c - k) + 排序数据[c] * (k - f)


def 协方差(数据1: List[float], 数据2: List[float]) -> float:
    """
    计算样本协方差

    参数:
        数据1: 第一组数据
        数据2: 第二组数据

    返回:
        协方差
    """
    if len(数据1) != len(数据2):
        raise RuntimeError("两组数据长度必须相同")
    if len(数据1) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.covariance(数据1, 数据2)


def 相关系数(数据1: List[float], 数据2: List[float]) -> float:
    """
    计算皮尔逊相关系数

    参数:
        数据1: 第一组数据
        数据2: 第二组数据

    返回:
        相关系数 (-1 到 1)
    """
    if len(数据1) != len(数据2):
        raise RuntimeError("两组数据长度必须相同")
    if len(数据1) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    try:
        return statistics.correlation(数据1, 数据2)
    except Exception as e:
        raise RuntimeError(f"计算相关系数失败: {e}")


def 线性回归(数据1: List[float], 数据2: List[float]) -> Dict[str, float]:
    """
    计算线性回归（斜率、截距）

    参数:
        数据1: X 值
        数据2: Y 值

    返回:
        {'斜率': slope, '截距': intercept}
    """
    if len(数据1) != len(数据2):
        raise RuntimeError("两组数据长度必须相同")
    if len(数据1) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    try:
        slope, intercept = statistics.linear_regression(数据1, 数据2)
        return {'斜率': slope, '截距': intercept}
    except Exception as e:
        raise RuntimeError(f"计算线性回归失败: {e}")


def 累积和(数据: List[float]) -> List[float]:
    """
    计算累积和

    参数:
        数据: 数值列表

    返回:
        累积和列表
    """
    结果 = []
    总计 = 0.0
    for v in 数据:
        总计 += v
        结果.append(总计)
    return 结果


def 频率分布(数据: list) -> Dict[Any, int]:
    """
    计算频率分布

    参数:
        数据: 数据列表

    返回:
        {值: 出现次数} 字典
    """
    频率 = {}
    for v in 数据:
        频率[v] = 频率.get(v, 0) + 1
    return 频率


def 标准化(数据: List[float]) -> List[float]:
    """
    标准化数据（Z-score）

    参数:
        数据: 数值列表

    返回:
        标准化后的数据列表
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    平均 = statistics.mean(数据)
    标准 = statistics.pstdev(数据)
    if 标准 == 0:
        return [0.0] * len(数据)
    return [(x - 平均) / 标准 for x in 数据]


__all__ = [
    '均值', '中位数', '众数', '多众数',
    '标准差', '样本标准差', '方差', '样本方差',
    '最小值', '最大值', '极差', '求和',
    '四分位数', '百分位数',
    '协方差', '相关系数', '线性回归',
    '累积和', '频率分布', '标准化',
]