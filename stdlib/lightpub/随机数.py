"""
随机数 — duanpub 桥接模块

基于 Python random 库封装，函数名对齐 duanpub/packages/随机数/源.duan。

duanpub 原始包通过 C FFI 直接调用操作系统随机数 API，
本桥接模块用 Python random 模块替代，提供等价的随机数生成功能。
"""

import random as _random
import math as _math


# =============================================================================
# 种子管理
# =============================================================================

def 设置种子(种子=None):
    """设置随机数生成器的种子"""
    try:
        _random.seed(种子)
        return True
    except Exception as e:
        raise Exception("设置种子失败: " + str(e))


# =============================================================================
# 基本随机数
# =============================================================================

def 随机整数(最小值, 最大值):
    """生成指定范围内的随机整数，包含两端"""
    if 最小值 > 最大值:
        raise Exception("随机整数失败: 最小值大于最大值")
    try:
        return _random.randint(最小值, 最大值)
    except Exception as e:
        raise Exception("随机整数失败: " + str(e))


def 随机浮点数(最小值=0.0, 最大值=1.0):
    """生成指定范围内的随机浮点数"""
    if 最小值 > 最大值:
        raise Exception("随机浮点数失败: 最小值大于最大值")
    try:
        return _random.uniform(最小值, 最大值)
    except Exception as e:
        raise Exception("随机浮点数失败: " + str(e))


# =============================================================================
# 随机选择与打乱
# =============================================================================

def 随机选择(序列):
    """从序列中随机选择一个元素"""
    if not 序列:
        raise Exception("随机选择失败: 序列为空")
    try:
        return _random.choice(序列)
    except IndexError:
        raise Exception("随机选择失败: 序列为空")
    except Exception as e:
        raise Exception("随机选择失败: " + str(e))


def 随机打乱(序列):
    """随机打乱序列（原地操作）"""
    if not 序列:
        return 序列
    try:
        _random.shuffle(序列)
        return 序列
    except Exception as e:
        raise Exception("随机打乱失败: " + str(e))


# =============================================================================
# 随机采样
# =============================================================================

def 均匀采样(总体, 样本数):
    """从总体中均匀随机采样（无放回）"""
    if not 总体:
        raise Exception("均匀采样失败: 总体为空")
    if 样本数 > len(总体):
        raise Exception("均匀采样失败: 样本数超过总体大小")
    try:
        return _random.sample(总体, 样本数)
    except Exception as e:
        raise Exception("均匀采样失败: " + str(e))


def 正态采样(均值=0.0, 标准差=1.0):
    """从正态分布中采样一个随机数"""
    if 标准差 < 0:
        raise Exception("正态采样失败: 标准差不能为负数")
    try:
        return _random.gauss(均值, 标准差)
    except Exception as e:
        raise Exception("正态采样失败: " + str(e))