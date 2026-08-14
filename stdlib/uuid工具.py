# -*- coding: utf-8 -*-
"""
UUID 生成工具

提供生成各种版本 UUID 的功能，包括 UUID1、UUID4、UUID5 等。

用法:
    from 标准库.uuid工具 import 生成UUID, 生成UUID4, 生成UUID1, 解析UUID

示例:
    设 id = 生成UUID()
    打印(id)
"""

import uuid as _uuid
from typing import Optional


def 生成UUID4() -> str:
    """生成随机 UUID（版本4）

    Returns:
        格式化为标准字符串的 UUID4，例如 "550e8400-e29b-41d4-a716-446655440000"
    """
    return str(_uuid.uuid4())


def 生成UUID1() -> str:
    """生成基于时间的 UUID（版本1）

    Returns:
        格式化为标准字符串的 UUID1

    注意:
        基于主机 MAC 地址和当前时间生成，可能暴露机器的物理位置信息
    """
    return str(_uuid.uuid1())


def 生成UUID5(命名空间: str, 名称: str) -> str:
    """生成基于命名空间和名称的 UUID（版本5，SHA-1 哈希）

    Args:
        命名空间: 命名空间 UUID 字符串，如 "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
        名称: 要哈希的名称字符串

    Returns:
        格式化为标准字符串的 UUID5
    """
    ns = _uuid.UUID(命名空间)
    return str(_uuid.uuid5(ns, 名称))


def 生成UUID3(命名空间: str, 名称: str) -> str:
    """生成基于命名空间和名称的 UUID（版本3，MD5 哈希）

    Args:
        命名空间: 命名空间 UUID 字符串
        名称: 要哈希的名称字符串

    Returns:
        格式化为标准字符串的 UUID3
    """
    ns = _uuid.UUID(命名空间)
    return str(_uuid.uuid3(ns, 名称))


def 生成UUID(版本: int = 4) -> str:
    """生成指定版本的 UUID

    Args:
        版本: UUID 版本号，可选 1, 3, 4, 5，默认为 4

    Returns:
        格式化为标准字符串的 UUID

    Raises:
        ValueError: 如果版本号无效

    示例:
        >>> 生成UUID(4)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    if 版本 == 1:
        return 生成UUID1()
    elif 版本 == 4:
        return 生成UUID4()
    else:
        raise ValueError(f"不支持的 UUID 版本: {版本}，支持: 1, 4")


def 解析UUID(uuid字符串: str) -> dict:
    """解析 UUID 字符串并返回详细信息

    Args:
        uuid字符串: UUID 格式的字符串

    Returns:
        包含 UUID 详细信息的字典:
        - 版本: UUID 版本
        - 变体: UUID 变体
        - 十六进制: 十六进制表示
        - 字节: 字节表示
        - 时间戳: 时间戳（仅 UUID1）
        - 节点: MAC 地址（仅 UUID1）

    Raises:
        ValueError: 如果字符串不是有效的 UUID
    """
    try:
        u = _uuid.UUID(uuid字符串)
        info = {
            "版本": u.version,
            "变体": str(u.variant),
            "十六进制": u.hex,
            "整数值": u.int,
        }
        if u.version == 1:
            info["时间戳"] = u.time
            info["节点"] = u.node
        return info
    except Exception as e:
        raise ValueError(f"无效的 UUID 字符串: {e}")


def 生成批量UUID(数量: int = 10) -> list:
    """批量生成多个 UUID4

    Args:
        数量: 要生成的 UUID 数量，默认为 10

    Returns:
        UUID 字符串列表
    """
    return [生成UUID4() for _ in range(数量)]


def 生成短UUID() -> str:
    """生成短 UUID（取 UUID4 的前 8 位）

    Returns:
        8 位十六进制短 UUID 字符串

    注意:
        短 UUID 碰撞概率较高，仅适用于非关键场景
    """
    return _uuid.uuid4().hex[:8]


def 生成命名UUID(名称: str) -> str:
    """基于 DNS 命名空间的 UUID5

    Args:
        名称: 要生成 UUID 的名称

    Returns:
        UUID5 字符串
    """
    return 生成UUID5("6ba7b810-9dad-11d1-80b4-00c04fd430c8", 名称)


def 生成唯一文件名(后缀: str = "") -> str:
    """生成唯一的文件名

    Args:
        后缀: 文件后缀名，如 ".txt"

    Returns:
        唯一的文件名，如 "550e8400-e29b-41d4-a716-446655440000.txt"
    """
    return f"{生成UUID4()}{后缀}"


def 验证UUID(字符串: str) -> bool:
    """验证字符串是否为有效的 UUID

    Args:
        字符串: 待验证的字符串

    Returns:
        如果是有效的 UUID 返回 True，否则返回 False
    """
    try:
        _uuid.UUID(字符串)
        return True
    except (ValueError, AttributeError):
        return False