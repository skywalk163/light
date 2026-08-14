"""
段言标准库 - 哈希与加密模块

提供哈希计算、Base64 编解码等功能。
"""

import hashlib
import base64
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
    计算 HMAC-SHA256
    
    参数:
        key: 密钥
        text: 输入字符串
        encoding: 编码方式
    
    返回:
        64 位小写十六进制哈希字符串
    """
    h = hashlib.pbkdf2_hmac('sha256', text.encode(encoding), key.encode(encoding), 1)
    return h.hex()


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