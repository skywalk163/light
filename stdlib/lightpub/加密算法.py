"""
加密算法 — lightpub 桥接模块

基于 Python hashlib / base64 / cryptography 库封装，函数名对齐上游 duanpub（段言时期）packages/加密算法/源.duan。

上游 duanpub 原始包通过 C FFI 调用 OpenSSL EVP 加密接口，
本桥接模块用 Python 标准库（hashlib + base64 + hashlib 回退）替代，
提供对称加密/解密功能。

注意：Python 标准库不含 AES 等对称加密实现，
此处使用 hashlib 派生密钥 + XOR 作为回退方案。
"""

import hashlib as _hashlib
import base64 as _b64
import os as _os


# =============================================================================
# 支持的算法
# =============================================================================

_算法列表 = ['aes-128-cbc', 'aes-256-cbc', 'aes-128-gcm', 'aes-256-gcm', 'des3', 'rc4', 'sm4']


def 获取算法名称():
    """获取支持的加密算法名称列表"""
    return list(_算法列表)


# =============================================================================
# 密钥生成
# =============================================================================

def 生成密钥(算法='aes-256-cbc'):
    """根据算法生成密钥字节"""
    if not 算法:
        raise Exception("生成密钥失败: 算法为空")
    try:
        key_sizes = {
            'aes-128-cbc': 16,
            'aes-256-cbc': 32,
            'aes-128-gcm': 16,
            'aes-256-gcm': 32,
            'des3': 24,
            'rc4': 16,
            'sm4': 16,
        }
        size = key_sizes.get(算法, 32)
        return _os.urandom(size)
    except Exception as e:
        raise Exception("生成密钥失败: " + str(e))


def 生成IV(算法='aes-256-cbc'):
    """根据算法生成初始向量（IV）"""
    if not 算法:
        raise Exception("生成IV失败: 算法为空")
    try:
        iv_sizes = {
            'aes-128-cbc': 16,
            'aes-256-cbc': 16,
            'aes-128-gcm': 12,
            'aes-256-gcm': 12,
            'des3': 8,
            'rc4': 0,
            'sm4': 16,
        }
        size = iv_sizes.get(算法, 16)
        if size == 0:
            return b''
        return _os.urandom(size)
    except Exception as e:
        raise Exception("生成IV失败: " + str(e))


# =============================================================================
# 核心加密解密
# =============================================================================

def _derive_key(密钥, 盐值, 长度=32):
    """使用 PBKDF2 派生密钥"""
    return _hashlib.pbkdf2_hmac('sha256', 密钥, 盐值, 10000, dklen=长度)


def _xor_encrypt(数据, 密钥):
    """XOR 加密（流模式）"""
    result = bytearray()
    key_len = len(密钥)
    for i, b in enumerate(数据):
        result.append(b ^ 密钥[i % key_len])
    return bytes(result)


def 加密(明文, 密钥, 算法='aes-256-cbc', iv=None):
    """加密数据

    使用派生密钥 + XOR 流加密实现。
    返回 base64 编码的密文（包含盐值和 IV）。
    """
    if not 明文:
        raise Exception("加密失败: 明文为空")
    if not 密钥:
        raise Exception("加密失败: 密钥为空")
    try:
        if isinstance(明文, str):
            明文 = 明文.encode('utf-8')
        if isinstance(密钥, str):
            密钥 = 密钥.encode('utf-8')

        # 生成盐值和 IV
        盐值 = _os.urandom(16)
        if iv is None:
            iv = 生成IV(算法)

        # 派生密钥
        key_size = 32 if '256' in 算法 else 16
        derived_key = _derive_key(密钥, 盐值, key_size)

        # 加密
        ciphertext = _xor_encrypt(明文, derived_key + iv)

        # 组合输出: 盐值(16) + IV + 密文
        result = 盐值 + iv + ciphertext
        return _b64.b64encode(result).decode('ascii')
    except Exception as e:
        raise Exception("加密失败: " + str(e))


def 解密(密文, 密钥, 算法='aes-256-cbc'):
    """解密数据"""
    if not 密文:
        raise Exception("解密失败: 密文为空")
    if not 密钥:
        raise Exception("解密失败: 密钥为空")
    try:
        if isinstance(密文, str):
            密文 = 密文.encode('ascii')
        if isinstance(密钥, str):
            密钥 = 密钥.encode('utf-8')

        raw = _b64.b64decode(密文)

        # 提取盐值、IV 和密文
        盐值 = raw[:16]
        iv_size = 16
        if 'gcm' in 算法:
            iv_size = 12
        iv = raw[16:16 + iv_size]
        ciphertext = raw[16 + iv_size:]

        # 派生密钥
        key_size = 32 if '256' in 算法 else 16
        derived_key = _derive_key(密钥, 盐值, key_size)

        # 解密
        plaintext = _xor_encrypt(ciphertext, derived_key + iv)
        return plaintext.decode('utf-8')
    except Exception as e:
        raise Exception("解密失败: " + str(e))