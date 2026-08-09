"""
光明标准库 - 随机模块

提供随机数生成和随机选择功能，包括：
- 随机数生成（整数、浮点数）
- 随机选择（单个、多个）
- 随机打乱
- 随机采样
"""

import random
import hashlib
from typing import List, Any, Optional


def 设置随机种子(种子: int):
    """设置随机种子"""
    random.seed(种子)


def 获取随机种子():
    """获取当前随机种子状态"""
    return random.getstate()


def 设置随机状态(状态):
    """设置随机状态"""
    random.setstate(状态)


def 随机整数(最小值: int = 0, 最大值: int = 100):
    """生成指定范围内的随机整数 [最小值, 最大值]"""
    return random.randint(最小值, 最大值)


def 随机浮点数(最小值: float = 0.0, 最大值: float = 1.0):
    """生成指定范围内的随机浮点数 [最小值, 最大值)"""
    return random.uniform(最小值, 最大值)


def 随机0到1():
    """生成0到1之间的随机浮点数 [0.0, 1.0)"""
    return random.random()


def 随机正态分布(均值: float = 0.0, 标准差: float = 1.0):
    """生成正态分布的随机数"""
    return random.normalvariate(均值, 标准差)


def 随机指数分布(均值: float = 1.0):
    """生成指数分布的随机数"""
    return random.expovariate(1.0 / 均值)


def 随机对数正态分布(均值: float = 0.0, 标准差: float = 1.0):
    """生成对数正态分布的随机数"""
    return random.lognormvariate(均值, 标准差)


def 随机伽马分布(形状: float, 尺度: float = 1.0):
    """生成伽马分布的随机数"""
    return random.gammavariate(形状, 尺度)


def 随机贝塔分布(alpha: float, beta: float):
    """生成贝塔分布的随机数"""
    return random.betavariate(alpha, beta)


def 随机三角分布(低: float, 高: float, 众数: float):
    """生成三角分布的随机数"""
    return random.triangular(低, 高, 众数)


def 随机选择(序列: List[Any]):
    """从序列中随机选择一个元素"""
    return random.choice(序列)


def 随机选择多个(序列: List[Any], 数量: int):
    """从序列中随机选择多个元素（可重复）"""
    return random.choices(序列, k=数量)


def 随机采样(序列: List[Any], 数量: int):
    """从序列中随机采样（不重复）"""
    return random.sample(序列, 数量)


def 随机打乱(序列: List[Any]):
    """随机打乱序列（原地修改）"""
    random.shuffle(序列)
    return 序列


def 随机打乱副本(序列: List[Any]):
    """随机打乱序列的副本（不修改原序列）"""
    副本 = 序列.copy()
    random.shuffle(副本)
    return 副本


def 随机布尔():
    """生成随机布尔值"""
    return random.choice([True, False])


def 随机字符(字符集: str = 'abcdefghijklmnopqrstuvwxyz'):
    """从指定字符集中随机选择一个字符"""
    return random.choice(字符集)


def 随机字符串(长度: int, 字符集: str = 'abcdefghijklmnopqrstuvwxyz'):
    """生成指定长度的随机字符串"""
    return ''.join(random.choice(字符集) for _ in range(长度))


def 随机大写字母():
    """生成随机大写字母"""
    return random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')


def 随机小写字母():
    """生成随机小写字母"""
    return random.choice('abcdefghijklmnopqrstuvwxyz')


def 随机数字():
    """生成随机数字字符"""
    return random.choice('0123456789')


def 随机字母数字():
    """生成随机字母或数字"""
    return random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')


def 随机十六进制(长度: int):
    """生成指定长度的随机十六进制字符串"""
    return ''.join(random.choice('0123456789abcdef') for _ in range(长度))


def 随机UUID():
    """生成随机UUID"""
    import uuid
    return str(uuid.uuid4())


def 随机颜色十六进制():
    """生成随机颜色的十六进制表示"""
    return f'#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}'


def 随机RGB():
    """生成随机RGB颜色值"""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def 随机概率(概率: float):
    """按概率返回True"""
    return random.random() < 概率


def 随机权重选择(序列: List[Any], 权重: List[float]):
    """按权重随机选择一个元素"""
    return random.choices(序列, weights=权重, k=1)[0]


def 随机权重选择多个(序列: List[Any], 权重: List[float], 数量: int):
    """按权重随机选择多个元素"""
    return random.choices(序列, weights=权重, k=数量)


def 随机范围采样(最小值: int, 最大值: int, 数量: int):
    """从范围中随机采样（不重复）"""
    return random.sample(range(最小值, 最大值 + 1), 数量)


def 随机打乱字典项(字典: dict):
    """随机打乱字典的键值对顺序"""
    项列表 = list(字典.items())
    random.shuffle(项列表)
    return dict(项列表)


def 基于哈希的随机(输入值: Any, 最大值: int = 100):
    """基于输入值的哈希生成确定性随机数"""
    哈希值 = int(hashlib.md5(str(输入值).encode()).hexdigest(), 16)
    return 哈希值 % (最大值 + 1)


__all__ = [
    '设置随机种子', '获取随机种子', '设置随机状态',
    '随机整数', '随机浮点数', '随机0到1',
    '随机正态分布', '随机指数分布', '随机对数正态分布',
    '随机伽马分布', '随机贝塔分布', '随机三角分布',
    '随机选择', '随机选择多个', '随机采样',
    '随机打乱', '随机打乱副本', '随机布尔',
    '随机字符', '随机字符串', '随机大写字母',
    '随机小写字母', '随机数字', '随机字母数字',
    '随机十六进制', '随机UUID', '随机颜色十六进制',
    '随机RGB', '随机概率', '随机权重选择',
    '随机权重选择多个', '随机范围采样', '随机打乱字典项',
    '基于哈希的随机'
]