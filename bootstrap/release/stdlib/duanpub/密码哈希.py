"""
密码哈希 — duanpub 桥接模块

基于 Python hashlib 库封装，函数名对齐 duanpub/packages/密码哈希/源.duan。

duanpub 原始包通过 C FFI 调用 bcrypt/scrypt 密码哈希库，
本桥接模块用 Python hashlib 的 scrypt + pbkdf2 替代，
提供安全的密码哈希与验证功能。
"""

import hashlib as _hashlib
import os as _os
import base64 as _b64


# =============================================================================
# 常量
# =============================================================================

_算法名称 = 'scrypt'


def 获取算法名称():
    """获取密码哈希算法名称"""
    return _算法名称


# =============================================================================
# 密码哈希
# =============================================================================

def 哈希密码(密码, 盐值=None, 算法='scrypt'):
    """哈希密码，返回包含盐值的哈希字符串

    格式: $algorithm$salt$hash（base64 编码）
    """
    if not 密码:
        raise Exception("哈希密码失败: 密码为空")
    try:
        if isinstance(密码, str):
            密码 = 密码.encode('utf-8')

        if 盐值 is None:
            盐值 = _os.urandom(16)
        elif isinstance(盐值, str):
            盐值 = 盐值.encode('utf-8')

        if 算法 == 'scrypt':
            # 使用 scrypt（如果可用）
            try:
                哈希值 = _hashlib.scrypt(密码, salt=盐值, n=16384, r=8, p=1, dklen=32)
            except (ValueError, AttributeError):
                # scrypt 可能不可用，回退到 pbkdf2
                哈希值 = _hashlib.pbkdf2_hmac('sha256', 密码, 盐值, 100000, dklen=32)
        elif 算法 == 'pbkdf2':
            哈希值 = _hashlib.pbkdf2_hmac('sha256', 密码, 盐值, 100000, dklen=32)
        else:
            raise Exception("哈希密码失败: 不支持的算法 " + 算法)

        salt_b64 = _b64.b64encode(盐值).decode('ascii')
        hash_b64 = _b64.b64encode(哈希值).decode('ascii')
        return f"${算法}${salt_b64}${hash_b64}"
    except Exception as e:
        raise Exception("哈希密码失败: " + str(e))


def 验证密码(密码, 哈希字符串):
    """验证密码与哈希字符串是否匹配"""
    if not 密码:
        raise Exception("验证密码失败: 密码为空")
    if not 哈希字符串:
        raise Exception("验证密码失败: 哈希字符串为空")
    try:
        if isinstance(密码, str):
            密码 = 密码.encode('utf-8')

        # 解析哈希字符串
        parts = 哈希字符串.split('$')
        if len(parts) != 4 or parts[0] != '':
            raise Exception("验证密码失败: 无效的哈希格式")

        算法 = parts[1]
        salt_b64 = parts[2]
        original_hash_b64 = parts[3]

        盐值 = _b64.b64decode(salt_b64)

        # 重新计算哈希
        if 算法 == 'scrypt':
            try:
                新哈希值 = _hashlib.scrypt(密码, salt=盐值, n=16384, r=8, p=1, dklen=32)
            except (ValueError, AttributeError):
                新哈希值 = _hashlib.pbkdf2_hmac('sha256', 密码, 盐值, 100000, dklen=32)
        elif 算法 == 'pbkdf2':
            新哈希值 = _hashlib.pbkdf2_hmac('sha256', 密码, 盐值, 100000, dklen=32)
        else:
            raise Exception("验证密码失败: 不支持的算法 " + 算法)

        new_hash_b64 = _b64.b64encode(新哈希值).decode('ascii')
        return new_hash_b64 == original_hash_b64
    except Exception as e:
        raise Exception("验证密码失败: " + str(e))


def 生成盐值(长度=16):
    """生成密码盐值"""
    if 长度 <= 0:
        raise Exception("生成盐值失败: 长度必须大于0")
    try:
        return _os.urandom(长度)
    except Exception as e:
        raise Exception("生成盐值失败: " + str(e))