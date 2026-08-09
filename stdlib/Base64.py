# -*- coding: utf-8 -*-
"""
光明标准库 - Base64 编解码模块

提供 Base64 编码和解码功能。
"""

import base64
from typing import Union


def Base64编码(数据: Union[str, bytes], 编码: str = 'utf-8') -> str:
    """
    将字符串或字节数据编码为 Base64 字符串

    参数:
        数据: 要编码的字符串或字节数据
        编码: 字符串编码方式（默认 utf-8）

    返回:
        Base64 编码字符串

    示例:
        Base64编码('hello')  # 'aGVsbG8='
    """
    if isinstance(数据, str):
        数据 = 数据.encode(编码)
    return base64.b64encode(数据).decode('ascii')


def Base64解码(数据: str, 编码: str = 'utf-8') -> str:
    """
    将 Base64 字符串解码为原始字符串

    参数:
        数据: Base64 编码字符串
        编码: 解码后的字符串编码（默认 utf-8）

    返回:
        解码后的字符串

    示例:
        Base64解码('aGVsbG8=')  # 'hello'
    """
    try:
        return base64.b64decode(数据).decode(编码)
    except Exception as e:
        raise RuntimeError(f"Base64 解码失败: {e}")


def Base64编码字节(数据: bytes) -> bytes:
    """
    将字节数据编码为 Base64 字节

    参数:
        数据: 字节数据

    返回:
        Base64 编码字节
    """
    return base64.b64encode(数据)


def Base64解码字节(数据: Union[str, bytes]) -> bytes:
    """
    将 Base64 数据解码为字节

    参数:
        数据: Base64 编码字符串或字节

    返回:
        解码后的字节
    """
    if isinstance(数据, str):
        数据 = 数据.encode('ascii')
    return base64.b64decode(数据)


def Base64URL编码(数据: Union[str, bytes], 编码: str = 'utf-8') -> str:
    """
    URL 安全的 Base64 编码（使用 - 和 _ 替代 + 和 /）

    参数:
        数据: 要编码的字符串或字节数据
        编码: 字符串编码方式（默认 utf-8）

    返回:
        URL 安全的 Base64 编码字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode(编码)
    return base64.urlsafe_b64encode(数据).decode('ascii')


def Base64URL解码(数据: str, 编码: str = 'utf-8') -> str:
    """
    URL 安全的 Base64 解码

    参数:
        数据: URL 安全的 Base64 编码字符串
        编码: 解码后的字符串编码（默认 utf-8）

    返回:
        解码后的字符串
    """
    try:
        return base64.urlsafe_b64decode(数据).decode(编码)
    except Exception as e:
        raise RuntimeError(f"Base64 URL 解码失败: {e}")


def Base16编码(数据: Union[str, bytes], 编码: str = 'utf-8') -> str:
    """
    Base16（十六进制）编码

    参数:
        数据: 要编码的字符串或字节数据
        编码: 字符串编码方式

    返回:
        Base16 编码字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode(编码)
    return base64.b16encode(数据).decode('ascii')


def Base16解码(数据: str, 编码: str = 'utf-8') -> str:
    """
    Base16（十六进制）解码

    参数:
        数据: Base16 编码字符串
        编码: 解码后的字符串编码

    返回:
        解码后的字符串
    """
    try:
        return base64.b16decode(数据.upper()).decode(编码)
    except Exception as e:
        raise RuntimeError(f"Base16 解码失败: {e}")


def Base32编码(数据: Union[str, bytes], 编码: str = 'utf-8') -> str:
    """
    Base32 编码

    参数:
        数据: 要编码的字符串或字节数据
        编码: 字符串编码方式

    返回:
        Base32 编码字符串
    """
    if isinstance(数据, str):
        数据 = 数据.encode(编码)
    return base64.b32encode(数据).decode('ascii')


def Base32解码(数据: str, 编码: str = 'utf-8') -> str:
    """
    Base32 解码

    参数:
        数据: Base32 编码字符串
        编码: 解码后的字符串编码

    返回:
        解码后的字符串
    """
    try:
        return base64.b32decode(数据).decode(编码)
    except Exception as e:
        raise RuntimeError(f"Base32 解码失败: {e}")


def Base64验证(数据: str) -> bool:
    """
    验证字符串是否为有效的 Base64 编码

    参数:
        数据: 待验证的字符串

    返回:
        是否为有效 Base64
    """
    try:
        base64.b64decode(数据, validate=True)
        return True
    except Exception:
        return False


def Base64编码文件(输入文件: str, 输出文件: str = None) -> str:
    """
    将文件编码为 Base64 字符串

    参数:
        输入文件: 输入文件路径
        输出文件: 输出文件路径（可选）

    返回:
        Base64 编码字符串
    """
    with open(输入文件, 'rb') as f:
        数据 = f.read()
    结果 = base64.b64encode(数据).decode('ascii')
    if 输出文件:
        with open(输出文件, 'w', encoding='ascii') as f:
            f.write(结果)
    return 结果


def Base64解码文件(输入文件: str, 输出文件: str):
    """
    将 Base64 编码文件解码为原始文件

    参数:
        输入文件: Base64 编码文件路径
        输出文件: 输出文件路径
    """
    with open(输入文件, 'r', encoding='ascii') as f:
        数据 = f.read()
    解码数据 = base64.b64decode(数据)
    with open(输出文件, 'wb') as f:
        f.write(解码数据)


__all__ = [
    'Base64编码', 'Base64解码',
    'Base64编码字节', 'Base64解码字节',
    'Base64URL编码', 'Base64URL解码',
    'Base16编码', 'Base16解码',
    'Base32编码', 'Base32解码',
    'Base64验证',
    'Base64编码文件', 'Base64解码文件',
]