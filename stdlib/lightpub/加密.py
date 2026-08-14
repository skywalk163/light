"""
加密 — duanpub 桥接模块

基于 Python hashlib / hmac 库封装，函数名对齐 duanpub/packages/哈希/源.duan。

duanpub 原始包通过 C FFI 调用 OpenSSL/crypto 库，
本桥接模块用 Python hashlib/hmac 模块替代，提供等价的哈希与 HMAC 功能。
"""

import hashlib as _hashlib
import hmac as _hmac


# =============================================================================
# 数据结构（对齐 duanpub 源.duan 的结构体定义）
# =============================================================================

class 哈希上下文:
    """哈希上下文，封装 hashlib 的哈希对象"""
    def __init__(self, 算法='', 摘要大小=0):
        self.算法 = 算法
        self.摘要大小 = 摘要大小
        self._ctx = None


class HMAC上下文:
    """HMAC 上下文，封装 hmac 对象"""
    def __init__(self, 算法=''):
        self.算法 = 算法
        self._ctx = None


# =============================================================================
# 支持的算法
# =============================================================================

def 获取所有算法():
    """获取所有可用的哈希算法名称列表"""
    return sorted(_hashlib.algorithms_available)


def 获取算法名称(算法):
    """获取算法标准名称"""
    try:
        h = _hashlib.new(算法)
        return h.name
    except ValueError:
        return ''


def 获取算法摘要大小(算法):
    """获取算法摘要大小（字节）"""
    try:
        h = _hashlib.new(算法)
        return h.digest_size
    except ValueError as e:
        raise Exception("获取算法摘要大小失败: " + str(e))


# =============================================================================
# 哈希上下文操作（对齐 duanpub 源.duan）
# =============================================================================

def 创建哈希(算法):
    """创建哈希上下文，返回 哈希上下文 对象"""
    if not 算法:
        raise Exception("创建哈希失败: 算法为空")
    try:
        h = _hashlib.new(算法)
        ctx = 哈希上下文(算法=h.name, 摘要大小=h.digest_size)
        ctx._ctx = h
        return ctx
    except ValueError as e:
        raise Exception("创建哈希失败: " + str(e))


def 哈希上下文更新(ctx, 数据):
    """更新哈希上下文（追加数据）"""
    if not ctx or not ctx._ctx:
        raise Exception("哈希上下文更新失败: 无效的上下文")
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    ctx._ctx.update(数据)


def 哈希上下文完成(ctx):
    """完成哈希计算，返回十六进制摘要字符串"""
    if not ctx or not ctx._ctx:
        raise Exception("哈希上下文完成失败: 无效的上下文")
    return ctx._ctx.hexdigest()


def 哈希上下文完成字节(ctx):
    """完成哈希计算，返回字节摘要"""
    if not ctx or not ctx._ctx:
        raise Exception("哈希上下文完成字节失败: 无效的上下文")
    return ctx._ctx.digest()


def 哈希上下文重置(ctx):
    """重置哈希上下文"""
    if not ctx:
        raise Exception("哈希上下文重置失败: 无效的上下文")
    try:
        ctx._ctx = _hashlib.new(ctx.算法)
    except ValueError as e:
        raise Exception("哈希上下文重置失败: " + str(e))


def 哈希上下文释放(ctx):
    """释放哈希上下文"""
    if ctx:
        ctx._ctx = None


# =============================================================================
# 一次性哈希函数
# =============================================================================

def 哈希(数据, 算法='sha256'):
    """计算字符串哈希，返回十六进制摘要"""
    if not 算法:
        raise Exception("哈希失败: 算法为空")
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _hashlib.new(算法, 数据).hexdigest()
    except ValueError as e:
        raise Exception("哈希失败: " + str(e))


def 哈希字节(数据, 算法='sha256'):
    """计算字节哈希，返回十六进制摘要"""
    if not 算法:
        raise Exception("哈希字节失败: 算法为空")
    try:
        return _hashlib.new(算法, 数据).hexdigest()
    except ValueError as e:
        raise Exception("哈希字节失败: " + str(e))


def MD5哈希(数据):
    """计算 MD5 哈希，返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _hashlib.md5(数据).hexdigest()


def SHA1哈希(数据):
    """计算 SHA1 哈希，返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _hashlib.sha1(数据).hexdigest()


def SHA256哈希(数据):
    """计算 SHA256 哈希，返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _hashlib.sha256(数据).hexdigest()


def SHA512哈希(数据):
    """计算 SHA512 哈希，返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _hashlib.sha512(数据).hexdigest()


def SHA3_256哈希(数据):
    """计算 SHA3-256 哈希，返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _hashlib.sha3_256(数据).hexdigest()


def BLAKE3哈希(数据):
    """计算 BLAKE3 哈希（回退到 blake2b），返回十六进制摘要"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    # Python 标准库 hashlib 不含 blake3，回退到 blake2b
    try:
        return _hashlib.blake2b(数据).hexdigest()
    except (ValueError, AttributeError) as e:
        raise Exception("BLAKE3哈希失败: " + str(e))


# =============================================================================
# 文件哈希
# =============================================================================

def 文件哈希(文件路径, 算法='sha256'):
    """计算文件哈希，返回十六进制摘要"""
    if not 文件路径:
        raise Exception("文件哈希失败: 文件路径为空")
    try:
        h = _hashlib.new(算法)
    except ValueError as e:
        raise Exception("文件哈希失败: " + str(e))
    try:
        with open(文件路径, 'rb') as f:
            while True:
                块 = f.read(8192)
                if not 块:
                    break
                h.update(块)
        return h.hexdigest()
    except FileNotFoundError:
        raise Exception("文件哈希失败: 文件不存在 " + 文件路径)
    except OSError as e:
        raise Exception("文件哈希失败: " + str(e))


def 文件哈希字节(文件路径, 算法='sha256'):
    """计算文件哈希，返回字节摘要"""
    if not 文件路径:
        raise Exception("文件哈希字节失败: 文件路径为空")
    try:
        h = _hashlib.new(算法)
    except ValueError as e:
        raise Exception("文件哈希字节失败: " + str(e))
    try:
        with open(文件路径, 'rb') as f:
            while True:
                块 = f.read(8192)
                if not 块:
                    break
                h.update(块)
        return h.digest()
    except FileNotFoundError:
        raise Exception("文件哈希字节失败: 文件不存在 " + 文件路径)
    except OSError as e:
        raise Exception("文件哈希字节失败: " + str(e))


# =============================================================================
# HMAC
# =============================================================================

def 创建HMAC(密钥, 算法='sha256'):
    """创建 HMAC 上下文，返回 HMAC上下文 对象"""
    if not 密钥:
        raise Exception("创建HMAC失败: 密钥为空")
    if isinstance(密钥, str):
        密钥 = 密钥.encode('utf-8')
    try:
        哈希函数 = getattr(_hashlib, 算法, None)
        if 哈希函数 is None:
            raise ValueError("不支持的算法: " + 算法)
        ctx = HMAC上下文(算法=算法)
        ctx._ctx = _hmac.new(密钥, digestmod=哈希函数)
        return ctx
    except (ValueError, TypeError) as e:
        raise Exception("创建HMAC失败: " + str(e))


def hmac_ctx更新(ctx, 数据):
    """更新 HMAC 上下文"""
    if not ctx or not ctx._ctx:
        raise Exception("hmac_ctx更新失败: 无效的上下文")
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    ctx._ctx.update(数据)


def hmac_ctx完成(ctx):
    """完成 HMAC 计算，返回十六进制摘要"""
    if not ctx or not ctx._ctx:
        raise Exception("hmac_ctx完成失败: 无效的上下文")
    return ctx._ctx.hexdigest()


def hmac_ctx完成字节(ctx):
    """完成 HMAC 计算，返回字节摘要"""
    if not ctx or not ctx._ctx:
        raise Exception("hmac_ctx完成字节失败: 无效的上下文")
    return ctx._ctx.digest()


def hmac_ctx重置(ctx):
    """重置 HMAC 上下文"""
    if not ctx:
        raise Exception("hmac_ctx重置失败: 无效的上下文")
    ctx._ctx = None


def hmac_ctx释放(ctx):
    """释放 HMAC 上下文"""
    if ctx:
        ctx._ctx = None


def HMAC哈希(密钥, 数据, 算法='sha256'):
    """一次性计算 HMAC，返回十六进制摘要"""
    if isinstance(密钥, str):
        密钥 = 密钥.encode('utf-8')
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        哈希函数 = getattr(_hashlib, 算法, None)
        if 哈希函数 is None:
            raise ValueError("不支持的算法: " + 算法)
        return _hmac.new(密钥, 数据, 哈希函数).hexdigest()
    except (ValueError, TypeError) as e:
        raise Exception("HMAC哈希失败: " + str(e))


def HMAC哈希字节(密钥, 数据, 算法='sha256'):
    """一次性计算 HMAC，返回字节摘要"""
    if isinstance(密钥, str):
        密钥 = 密钥.encode('utf-8')
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        哈希函数 = getattr(_hashlib, 算法, None)
        if 哈希函数 is None:
            raise ValueError("不支持的算法: " + 算法)
        return _hmac.new(密钥, 数据, 哈希函数).digest()
    except (ValueError, TypeError) as e:
        raise Exception("HMAC哈希字节失败: " + str(e))


# =============================================================================
# 工具函数
# =============================================================================

def 字节转十六进制(数据):
    """字节转十六进制字符串"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return 数据.hex()


def 十六进制转字节(十六进制字符串):
    """十六进制字符串转字节"""
    if not 十六进制字符串:
        raise Exception("十六进制转字节失败: 字符串为空")
    try:
        return bytes.fromhex(十六进制字符串)
    except ValueError as e:
        raise Exception("十六进制转字节失败: " + str(e))


def 字节转Base64(数据):
    """字节转 Base64 字符串"""
    import base64 as _b64
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return _b64.b64encode(数据).decode('ascii')


def 哈希相等(哈希1, 哈希2):
    """安全比较两个哈希值（防时序攻击）"""
    if isinstance(哈希1, str):
        哈希1 = 哈希1.encode('utf-8')
    if isinstance(哈希2, str):
        哈希2 = 哈希2.encode('utf-8')
    return _hmac.compare_digest(哈希1, 哈希2)
