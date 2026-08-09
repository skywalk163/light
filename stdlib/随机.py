# -*- coding: utf-8 -*-
"""
光明标准库 - 随机数生成模块

提供随机数生成、列表洗牌、抽样等功能。
"""

import random
import secrets
from typing import List, Any, Optional


def 随机整数(最小: int, 最大: int) -> int:
    """
    生成指定范围内的随机整数（包含两端）

    参数:
        最小: 最小值（包含）
        最大: 最大值（包含）

    返回:
        随机整数

    示例:
        随机整数(1, 100)  # 1 到 100 之间的随机整数
    """
    return random.randint(最小, 最大)


def 随机浮点(最小: float = 0.0, 最大: float = 1.0) -> float:
    """
    生成指定范围内的随机浮点数

    参数:
        最小: 最小值（默认 0.0）
        最大: 最大值（默认 1.0）

    返回:
        随机浮点数
    """
    return random.uniform(最小, 最大)


def 随机选择(列表: List[Any]) -> Any:
    """
    从列表中随机选择一个元素

    参数:
        列表: 源列表

    返回:
        随机选中的元素，列表为空返回 None
    """
    if not 列表:
        return None
    return random.choice(列表)


def 随机选择权重(列表: List[Any], 权重: List[float] = None, k: int = 1):
    """
    按权重随机选择

    参数:
        列表: 源列表
        权重: 权重列表（长度与源列表相同）
        k: 选择数量

    返回:
        k=1 时返回单个元素，k>1 时返回元素列表
    """
    if not 列表:
        return [] if k > 1 else None
    result = random.choices(列表, weights=权重, k=k)
    return result[0] if k == 1 else result


def 随机洗牌(列表: List[Any]) -> List[Any]:
    """
    打乱列表顺序（返回新列表，不修改原列表）

    参数:
        列表: 源列表

    返回:
        打乱后的新列表
    """
    结果 = list(列表)
    random.shuffle(结果)
    return 结果


def 随机抽样(列表: List[Any], k: int) -> List[Any]:
    """
    从列表中随机抽取 k 个不重复元素

    参数:
        列表: 源列表
        k: 抽取数量

    返回:
        抽取的元素列表
    """
    if k > len(列表):
        raise RuntimeError(f"抽样数量 ({k}) 不能超过列表长度 ({len(列表)})")
    return random.sample(列表, k)


def 随机布尔() -> bool:
    """生成随机布尔值"""
    return random.choice([True, False])


def 随机字节(k: int) -> bytes:
    """
    生成随机字节

    参数:
        k: 字节数

    返回:
        随机字节数据
    """
    return random.randbytes(k)


def 随机范围(起始: int, 结束: int, 步长: int = 1) -> int:
    """
    从指定范围内随机选择一个整数

    参数:
        起始: 起始值（包含）
        结束: 结束值（不包含）
        步长: 步长

    返回:
        随机整数
    """
    return random.randrange(起始, 结束, 步长)


def 随机种子(种子: int = None):
    """
    设置随机数种子

    参数:
        种子: 种子值，None 使用系统时间
    """
    random.seed(种子)


# 别名：测试期望的 API 名称
设置随机种子 = 随机种子
随机浮点数 = 随机浮点
随机采样 = 随机抽样
随机打乱副本 = 随机洗牌
随机权重选择 = 随机选择权重


def 随机0到1() -> float:
    """生成 [0, 1) 之间的随机浮点数"""
    return random.random()


def 随机选择多个(列表: List[Any], k: int) -> List[Any]:
    """
    从列表中随机选择 k 个元素（可重复）

    参数:
        列表: 源列表
        k: 选择数量

    返回:
        选中的元素列表
    """
    return random.choices(列表, k=k)


def 随机打乱(列表: List[Any]):
    """
    打乱列表顺序（原地修改）

    参数:
        列表: 待打乱的列表
    """
    random.shuffle(列表)


def 随机字符串(长度: int = 16) -> str:
    """
    生成随机字符串

    参数:
        长度: 字符串长度

    返回:
        随机字符串
    """
    import string
    字符集 = string.ascii_letters + string.digits
    return ''.join(random.choice(字符集) for _ in range(长度))


def 随机字母数字() -> str:
    """
    生成随机字母数字字符

    返回:
        单个随机字母数字字符
    """
    import string
    return random.choice(string.ascii_letters + string.digits)


def 随机UUID() -> str:
    """
    生成随机 UUID 字符串

    返回:
        UUID 字符串（36 字符）
    """
    import uuid
    return str(uuid.uuid4())


def 安全随机整数(最小: int, 最大: int) -> int:
    """
    生成密码学安全的随机整数

    参数:
        最小: 最小值（包含）
        最大: 最大值（包含）

    返回:
        安全随机整数
    """
    return secrets.randbelow(最大 - 最小 + 1) + 最小


def 安全随机令牌(nbytes: int = 32) -> str:
    """
    生成密码学安全的随机令牌（十六进制字符串）

    参数:
        nbytes: 字节数（默认 32）

    返回:
        十六进制字符串
    """
    return secrets.token_hex(nbytes)


def 安全随机URL令牌(nbytes: int = 32) -> str:
    """
    生成 URL 安全的随机令牌

    参数:
        nbytes: 字节数

    返回:
        URL 安全的 Base64 字符串
    """
    return secrets.token_urlsafe(nbytes)


def 正态分布(均值: float = 0.0, 标准差: float = 1.0) -> float:
    """
    生成正态分布随机数

    参数:
        均值: 分布均值（默认 0）
        标准差: 分布标准差（默认 1）

    返回:
        正态分布随机数
    """
    return random.gauss(均值, 标准差)


def 均匀分布(最小: float = 0.0, 最大: float = 1.0) -> float:
    """
    生成均匀分布随机数

    参数:
        最小: 最小值（默认 0）
        最大: 最大值（默认 1）

    返回:
        均匀分布随机数
    """
    return random.uniform(最小, 最大)


def 随机密码(长度: int = 16) -> str:
    """
    生成随机密码（包含大小写字母、数字和特殊字符）

    参数:
        长度: 密码长度（默认 16）

    返回:
        随机密码字符串
    """
    import string as _string
    字符集 = _string.ascii_letters + _string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(字符集) for _ in range(长度))


__all__ = [
    '随机整数', '随机浮点', '随机选择', '随机选择权重',
    '随机洗牌', '随机抽样', '随机布尔', '随机字节',
    '随机范围', '随机种子',
    '安全随机整数', '安全随机令牌', '安全随机URL令牌',
    '正态分布', '均匀分布', '随机密码',
    # 别名
    '设置随机种子', '随机浮点数', '随机采样', '随机打乱副本', '随机权重选择',
    # 新增函数
    '随机0到1', '随机选择多个', '随机打乱', '随机字符串', '随机字母数字', '随机UUID',
]