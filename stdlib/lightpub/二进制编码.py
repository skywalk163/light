"""
二进制编码 — duanpub 桥接模块

基于 Python base64 / binascii / urllib.parse 库封装，
函数名对齐 duanpub/packages/二进制编码/源.duan。

duanpub 原始包通过 C FFI 实现编码/解码，
本桥接模块用 Python 标准库替代，提供等价的 Base64/Base32/Hex/URL/百分号编码功能。
"""

import base64 as _base64
import binascii as _binascii
import urllib.parse as _urlparse


# =============================================================================
# 字节/字符串转换
# =============================================================================

def 字符串转字节(文本, 编码='utf-8'):
    """将字符串转为字节数组"""
    if not isinstance(文本, str):
        raise Exception("字符串转字节失败: 输入不是字符串")
    try:
        return 文本.encode(编码)
    except UnicodeEncodeError as e:
        raise Exception("字符串转字节失败: " + str(e))


def 字节转字符串(数据, 编码='utf-8'):
    """将字节数组转为字符串"""
    if not isinstance(数据, (bytes, bytearray)):
        raise Exception("字节转字符串失败: 输入不是字节数组")
    try:
        return 数据.decode(编码)
    except UnicodeDecodeError as e:
        raise Exception("字节转字符串失败: " + str(e))


# =============================================================================
# 十六进制字符判断
# =============================================================================

def 是十六进制字符(ch):
    """判断字符是否为十六进制字符(0-9, a-f, A-F)"""
    if len(ch) != 1:
        return False
    return ch in '0123456789abcdefABCDEF'


def 十六进制值(ch):
    """获取十六进制字符对应的数值"""
    if len(ch) != 1:
        raise Exception("十六进制值失败: 输入不是单个字符")
    if ch in '0123456789':
        return ord(ch) - ord('0')
    elif ch in 'abcdef':
        return ord(ch) - ord('a') + 10
    elif ch in 'ABCDEF':
        return ord(ch) - ord('A') + 10
    raise Exception("十六进制值失败: 不是有效的十六进制字符 " + ch)


def 是空白字符(ch):
    """判断字符是否为空白字符"""
    if len(ch) != 1:
        return False
    return ch in ' \t\n\r\f\v'


def 是URL安全字符(ch):
    """判断字符是否为URL安全字符"""
    if len(ch) != 1:
        return False
    return ch.isalnum() or ch in '-_.~'


# =============================================================================
# 字节/十六进制转换
# =============================================================================

def 字节转十六进制(数据):
    """将字节转为十六进制小写字符串"""
    try:
        return _binascii.hexlify(数据).decode('ascii')
    except (TypeError, binascii.Error) as e:
        raise Exception("字节转十六进制失败: " + str(e))


def 字节转十六进制大写(数据):
    """将字节转为十六进制大写字符串"""
    try:
        return _binascii.hexlify(数据).decode('ascii').upper()
    except (TypeError, binascii.Error) as e:
        raise Exception("字节转十六进制大写失败: " + str(e))


# =============================================================================
# Base64 编码/解码
# =============================================================================

def Base64编码(数据):
    """Base64 编码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _base64.b64encode(数据)
    except Exception as e:
        raise Exception("Base64编码失败: " + str(e))


def Base64编码字符串(数据):
    """Base64 编码，返回字符串"""
    return Base64编码(数据).decode('ascii')


def Base64解码(数据):
    """Base64 解码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('ascii')
    try:
        return _base64.b64decode(数据)
    except Exception as e:
        raise Exception("Base64解码失败: " + str(e))


def Base64解码为字符串(数据, 编码='utf-8'):
    """Base64 解码为字符串"""
    return Base64解码(数据).decode(编码)


def Base64URL编码(数据):
    """Base64 URL-safe 编码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _base64.urlsafe_b64encode(数据)
    except Exception as e:
        raise Exception("Base64URL编码失败: " + str(e))


def Base64URL解码(数据):
    """Base64 URL-safe 解码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('ascii')
    try:
        return _base64.urlsafe_b64decode(数据)
    except Exception as e:
        raise Exception("Base64URL解码失败: " + str(e))


# =============================================================================
# Base32 编码/解码
# =============================================================================

def Base32编码(数据):
    """Base32 编码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _base64.b32encode(数据)
    except Exception as e:
        raise Exception("Base32编码失败: " + str(e))


def Base32编码字符串(数据):
    """Base32 编码，返回字符串"""
    return Base32编码(数据).decode('ascii')


def Base32解码(数据):
    """Base32 解码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('ascii')
    try:
        return _base64.b32decode(数据)
    except Exception as e:
        raise Exception("Base32解码失败: " + str(e))


def Base32解码为字符串(数据, 编码='utf-8'):
    """Base32 解码为字符串"""
    return Base32解码(数据).decode(编码)


# =============================================================================
# Hex 编码/解码
# =============================================================================

def Hex编码(数据):
    """Hex 编码（小写），返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _binascii.hexlify(数据)
    except Exception as e:
        raise Exception("Hex编码失败: " + str(e))


def Hex编码大写(数据):
    """Hex 编码（大写），返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    try:
        return _binascii.hexlify(数据).upper()
    except Exception as e:
        raise Exception("Hex编码大写失败: " + str(e))


def Hex解码(数据):
    """Hex 解码，返回字节"""
    if isinstance(数据, str):
        数据 = 数据.encode('ascii')
    try:
        return _binascii.unhexlify(数据)
    except Exception as e:
        raise Exception("Hex解码失败: " + str(e))


# =============================================================================
# URL 编码/解码
# =============================================================================

def URL编码(字符串, safe=''):
    """URL 编码"""
    try:
        return _urlparse.quote(字符串, safe=safe)
    except Exception as e:
        raise Exception("URL编码失败: " + str(e))


def URL解码(字符串):
    """URL 解码"""
    try:
        return _urlparse.unquote(字符串)
    except Exception as e:
        raise Exception("URL解码失败: " + str(e))


def URL编码查询(参数字典):
    """URL 查询参数编码"""
    try:
        return _urlparse.urlencode(参数字典)
    except Exception as e:
        raise Exception("URL编码查询失败: " + str(e))


def URL解码查询(查询字符串):
    """URL 查询参数解码，返回字典"""
    try:
        parsed = _urlparse.parse_qs(查询字符串)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    except Exception as e:
        raise Exception("URL解码查询失败: " + str(e))


# =============================================================================
# 百分号编码
# =============================================================================

def 百分号编码(数据, safe=''):
    """百分号编码（同 URL编码）"""
    if isinstance(数据, bytes):
        数据 = 数据.decode('latin-1')
    return URL编码(数据, safe=safe)


def 百分号解码(字符串):
    """百分号解码（同 URL解码）"""
    return URL解码(字符串)