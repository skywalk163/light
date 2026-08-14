"""
段言标准库 - 编码与哈希模块

提供 Base64 编解码、MD5/SHA 哈希、Hex 编解码等功能

用法：
    从《编码》导入《Base64编码》，《MD5哈希》。
    设 结果 为 Base64编码 "你好世界"。
"""

import base64
import hashlib
from typing import Union, Optional


# =============================================================================
# Base64 编解码
# =============================================================================

def Base64编码(数据: Union[str, bytes]) -> str:
    """
    Base64 编码

    参数:
        数据: 待编码的字符串或字节数据

    返回:
        Base64 编码后的字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return base64.b64encode(数据).decode('ascii')


def Base64解码(数据: str) -> str:
    """
    Base64 解码

    参数:
        数据: Base64 编码的字符串

    返回:
        解码后的原始字符串
    """
    try:
        return base64.b64decode(数据).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Base64 解码失败: {e}")


# =============================================================================
# Hex 编解码
# =============================================================================

def Hex编码(数据: Union[str, bytes]) -> str:
    """
    Hex（十六进制）编码

    参数:
        数据: 待编码的字符串或字节数据

    返回:
        十六进制字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return 数据.hex()


def Hex解码(数据: str) -> str:
    """
    Hex（十六进制）解码

    参数:
        数据: 十六进制字符串

    返回:
        解码后的原始字符串
    """
    try:
        return bytes.fromhex(数据).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Hex 解码失败: {e}")


# =============================================================================
# MD5 / SHA 哈希
# =============================================================================

def MD5哈希(数据: Union[str, bytes]) -> str:
    """
    计算 MD5 哈希值

    参数:
        数据: 待哈希的字符串或字节数据

    返回:
        32 位小写十六进制哈希字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return hashlib.md5(数据).hexdigest()


def SHA1哈希(数据: Union[str, bytes]) -> str:
    """
    计算 SHA-1 哈希值

    参数:
        数据: 待哈希的字符串或字节数据

    返回:
        40 位小写十六进制哈希字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return hashlib.sha1(数据).hexdigest()


def SHA256哈希(数据: Union[str, bytes]) -> str:
    """
    计算 SHA-256 哈希值

    参数:
        数据: 待哈希的字符串或字节数据

    返回:
        64 位小写十六进制哈希字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return hashlib.sha256(数据).hexdigest()


def SHA512哈希(数据: Union[str, bytes]) -> str:
    """
    计算 SHA-512 哈希值

    参数:
        数据: 待哈希的字符串或字节数据

    返回:
        128 位小写十六进制哈希字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return hashlib.sha512(数据).hexdigest()


# =============================================================================
# 字节与字符串转换
# =============================================================================

def 字符串转字节(文本: str, 编码: str = 'utf-8') -> bytes:
    """字符串转字节数组"""
    return 文本.encode(编码)


def 字节转字符串(字节: bytes, 编码: str = 'utf-8') -> str:
    """字节数组转字符串"""
    return 字节.decode(编码)


def 字节长度(数据: bytes) -> int:
    """获取字节数组长度"""
    return len(数据)


__all__ = [
    'Base64编码', 'Base64解码',
    'Hex编码', 'Hex解码',
    'MD5哈希', 'SHA1哈希', 'SHA256哈希', 'SHA512哈希',
    '字符串转字节', '字节转字符串', '字节长度',
]