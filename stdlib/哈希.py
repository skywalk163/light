"""
光明标准库 - 哈希与加密模块

提供哈希计算、Base64 编解码等功能。
"""

import hashlib
import base64
import hmac
from typing import Optional


def MD5(text: str, encoding: str = 'utf-8') -> str:
    """
    计算字符串的 MD5 哈希值
    
    参数:
        text: 输入字符串
        encoding: 编码方式（默认 utf-8）
    
    返回:
        32 位小写十六进制哈希字符串
    """
    return hashlib.md5(text.encode(encoding)).hexdigest()


def SHA1(text: str, encoding: str = 'utf-8') -> str:
    """
    计算字符串的 SHA-1 哈希值
    
    参数:
        text: 输入字符串
        encoding: 编码方式
    
    返回:
        40 位小写十六进制哈希字符串
    """
    return hashlib.sha1(text.encode(encoding)).hexdigest()


def SHA256(text: str, encoding: str = 'utf-8') -> str:
    """
    计算字符串的 SHA-256 哈希值
    
    参数:
        text: 输入字符串
        encoding: 编码方式
    
    返回:
        64 位小写十六进制哈希字符串
    """
    return hashlib.sha256(text.encode(encoding)).hexdigest()


def SHA512(text: str, encoding: str = 'utf-8') -> str:
    """
    计算字符串的 SHA-512 哈希值
    
    参数:
        text: 输入字符串
        encoding: 编码方式
    
    返回:
        128 位小写十六进制哈希字符串
    """
    return hashlib.sha512(text.encode(encoding)).hexdigest()


def HMAC_SHA256(key: str, text: str, encoding: str = 'utf-8') -> str:
    """
    计算 HMAC-SHA256（RFC 2104 标准实现）

    L-095 修复：旧实现为单轮 PBKDF2（hashlib.pbkdf2_hmac(..., 1)），密钥未走
    ipad/opad 内层处理，与标准 HMAC-SHA256 不一致，无法与外部系统对拍。
    现改为 Python 标准库 hmac.new(key, msg, hashlib.sha256)，输出与
    RFC 4231 / openssl dgst -sha256 -hmac 完全一致。
    """
    return hmac.new(
        key.encode(encoding), text.encode(encoding), hashlib.sha256
    ).hexdigest()


def Base64编码(text: str, encoding: str = 'utf-8') -> str:
    """
    Base64 编码
    
    参数:
        text: 输入字符串
        encoding: 编码方式
    
    返回:
        Base64 编码字符串
    """
    return base64.b64encode(text.encode(encoding)).decode('ascii')


def Base64解码(text: str, encoding: str = 'utf-8') -> str:
    """
    Base64 解码
    
    参数:
        text: Base64 编码字符串
        encoding: 解码后编码方式
    
    返回:
        解码后的字符串
    """
    try:
        return base64.b64decode(text).decode(encoding)
    except Exception as e:
        raise RuntimeError(f"Base64 解码失败: {e}")


def Base64URL编码(text: str, encoding: str = 'utf-8') -> str:
    """
    Base64 URL 安全编码（替换 +/ 为 -_）
    
    参数:
        text: 输入字符串
    
    返回:
        URL 安全的 Base64 编码字符串
    """
    return base64.urlsafe_b64encode(text.encode(encoding)).decode('ascii').rstrip('=')


def Base64URL解码(text: str, encoding: str = 'utf-8') -> str:
    """
    Base64 URL 安全解码
    
    参数:
        text: URL 安全的 Base64 编码字符串
    
    返回:
        解码后的字符串
    """
    try:
        # 补全缺失的填充
        padding = 4 - len(text) % 4
        if padding != 4:
            text += '=' * padding
        return base64.urlsafe_b64decode(text).decode(encoding)
    except Exception as e:
        raise RuntimeError(f"Base64 URL 解码失败: {e}")


__all__ = [
    'MD5', 'SHA1', 'SHA256', 'SHA512',
    'HMAC_SHA256',
    'Base64编码', 'Base64解码',
    'Base64URL编码', 'Base64URL解码',
]