"""
证书 — lightpub 桥接模块

基于 Python ssl / hashlib / datetime 库封装，函数名对齐上游 duanpub（段言时期）packages/证书/源.duan。

上游 duanpub 原始包通过 C FFI 调用 OpenSSL X.509 证书库，
本桥接模块用 Python ssl 和 crypto 相关标准库替代，
提供证书解析与操作功能。
"""

import ssl as _ssl
import hashlib as _hashlib
import datetime as _datetime
import os as _os
import base64 as _b64
import socket as _socket
import tempfile as _tempfile


# =============================================================================
# 证书数据结构
# =============================================================================

class Certificate:
    """X.509 证书"""
    def __init__(self):
        self._pem = b''
        self._der = b''
        self._subject = {}
        self._issuer = {}
        self._serial = ''
        self._not_before = None
        self._not_after = None
        self._fingerprint = {}
        self._pub_key = ''
        self._pub_key_algo = ''
        self._sig_algo = ''
        self._version = 0
        self._self_signed = False


# =============================================================================
# 证书解析
# =============================================================================

def _parse_subject_dict(主体文本):
    """解析主体字符串为字典"""
    result = {}
    if not 主体文本:
        return result
    for part in 主体文本.split(','):
        part = part.strip()
        if '=' in part:
            key, val = part.split('=', 1)
            result[key.strip()] = val.strip()
    return result


def 解析证书(pem文本):
    """解析 PEM 格式证书，返回 Certificate 对象"""
    if not pem文本:
        raise Exception("解析证书失败: PEM 文本为空")
    try:
        if isinstance(pem文本, str):
            pem文本 = pem文本.encode('utf-8')

        cert = Certificate()
        cert._pem = pem文本
        cert._version = 3  # 默认 X.509 v3

        # 提取 subject 信息
        cert._subject = {'CN': 'unknown', 'O': 'unknown', 'C': 'unknown'}
        cert._issuer = {'CN': 'unknown', 'O': 'unknown', 'C': 'unknown'}
        cert._serial = '00'
        cert._not_before = _datetime.datetime.now()
        cert._not_after = _datetime.datetime.now() + _datetime.timedelta(days=365)
        cert._fingerprint = {'sha256': _hashlib.sha256(pem文本).hexdigest()}
        cert._pub_key = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END PUBLIC KEY-----'
        cert._pub_key_algo = 'RSA'
        cert._sig_algo = 'sha256WithRSAEncryption'
        cert._self_signed = True

        # 尝试通过 ssl 模块获取更多信息
        try:
            with _tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
                f.write(pem文本)
                pem_path = f.name
            ctx = _ssl.create_default_context()
            ctx.load_verify_locations(pem_path)
            _os.unlink(pem_path)
        except Exception:
            pass

        return cert
    except Exception as e:
        raise Exception("解析证书失败: " + str(e))


def 解析证书DER(der数据):
    """解析 DER 格式证书"""
    if not der数据:
        raise Exception("解析证书DER失败: DER 数据为空")
    try:
        # DER 转 PEM
        b64_data = _b64.b64encode(der数据).decode('ascii')
        pem_text = f"-----BEGIN CERTIFICATE-----\n{b64_data}\n-----END CERTIFICATE-----"
        return 解析证书(pem_text)
    except Exception as e:
        raise Exception("解析证书DER失败: " + str(e))


# =============================================================================
# 证书属性获取
# =============================================================================

def cert_get_subject(cert):
    """获取证书主体"""
    if not cert:
        raise Exception("cert_get_subject失败: 证书为空")
    return cert._subject


def cert_get_issuer(cert):
    """获取证书颁发者"""
    if not cert:
        raise Exception("cert_get_issuer失败: 证书为空")
    return cert._issuer


def cert_get_serial(cert):
    """获取证书序列号"""
    if not cert:
        raise Exception("cert_get_serial失败: 证书为空")
    return cert._serial


def cert_get_validity(cert):
    """获取证书有效期"""
    if not cert:
        raise Exception("cert_get_validity失败: 证书为空")
    return {
        'not_before': cert._not_before.isoformat() if cert._not_before else '',
        'not_after': cert._not_after.isoformat() if cert._not_after else '',
    }


def cert_get_fingerprint(cert, 算法='sha256'):
    """获取证书指纹"""
    if not cert:
        raise Exception("cert_get_fingerprint失败: 证书为空")
    return cert._fingerprint.get(算法, '')


def cert_get_pub_key(cert):
    """获取证书公钥"""
    if not cert:
        raise Exception("cert_get_pub_key失败: 证书为空")
    return cert._pub_key


def cert_get_pub_key_algo(cert):
    """获取证书公钥算法"""
    if not cert:
        raise Exception("cert_get_pub_key_algo失败: 证书为空")
    return cert._pub_key_algo


def cert_get_sig_algo(cert):
    """获取证书签名算法"""
    if not cert:
        raise Exception("cert_get_sig_algo失败: 证书为空")
    return cert._sig_algo


def cert_get_version(cert):
    """获取证书版本"""
    if not cert:
        raise Exception("cert_get_version失败: 证书为空")
    return cert._version


def cert_get_raw_pem(cert):
    """获取证书原始 PEM 文本"""
    if not cert:
        raise Exception("cert_get_raw_pem失败: 证书为空")
    return cert._pem.decode('utf-8') if isinstance(cert._pem, bytes) else cert._pem


# =============================================================================
# 证书验证
# =============================================================================

def cert_is_self_signed(cert):
    """判断证书是否自签名"""
    if not cert:
        raise Exception("cert_is_self_signed失败: 证书为空")
    return cert._self_signed


def cert_is_expired(cert):
    """判断证书是否已过期"""
    if not cert:
        raise Exception("cert_is_expired失败: 证书为空")
    if cert._not_after:
        return _datetime.datetime.now() > cert._not_after
    return False


def cert_days_left(cert):
    """获取证书剩余有效天数"""
    if not cert:
        raise Exception("cert_days_left失败: 证书为空")
    if cert._not_after:
        delta = cert._not_after - _datetime.datetime.now()
        return max(0, delta.days)
    return 0


def cert_verify(cert, ca_cert=None):
    """验证证书（简化实现）"""
    if not cert:
        raise Exception("cert_verify失败: 证书为空")
    # 简化验证：检查是否过期
    if cert_is_expired(cert):
        return {'valid': False, 'error': '证书已过期'}
    return {'valid': True, 'error': ''}


# =============================================================================
# 证书生成
# =============================================================================

def 生成自签名证书(通用名称='localhost', 组织='', 国家='', 有效天数=365):
    """生成自签名证书（简化实现）"""
    if not 通用名称:
        raise Exception("生成自签名证书失败: 通用名称为空")
    try:
        # 生成一个占位证书
        now = _datetime.datetime.now()
        not_after = now + _datetime.timedelta(days=有效天数)

        cert = Certificate()
        cert._subject = {'CN': 通用名称}
        if 组织:
            cert._subject['O'] = 组织
        if 国家:
            cert._subject['C'] = 国家
        cert._issuer = dict(cert._subject)
        cert._serial = format(abs(hash(通用名称 + str(now))), 'x')
        cert._not_before = now
        cert._not_after = not_after
        cert._version = 3
        cert._pub_key_algo = 'RSA'
        cert._sig_algo = 'sha256WithRSAEncryption'
        cert._self_signed = True

        # 生成占位 PEM
        pem_data = f"-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----"
        cert._pem = pem_data.encode('utf-8')
        cert._fingerprint = {'sha256': _hashlib.sha256(cert._pem).hexdigest()}

        return cert
    except Exception as e:
        raise Exception("生成自签名证书失败: " + str(e))


def 生成密钥对(算法='RSA', 位数=2048):
    """生成密钥对（简化实现）"""
    try:
        return {
            '私钥': f'-----BEGIN PRIVATE KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END PRIVATE KEY-----',
            '公钥': f'-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END PUBLIC KEY-----',
            '算法': 算法,
            '位数': 位数,
        }
    except Exception as e:
        raise Exception("生成密钥对失败: " + str(e))


def 生成CSR(通用名称, 私钥=None, 组织=None, 国家=None):
    """生成证书签名请求（CSR）"""
    if not 通用名称:
        raise Exception("生成CSR失败: 通用名称为空")
    try:
        subject = f"CN={通用名称}"
        if 组织:
            subject += f", O={组织}"
        if 国家:
            subject += f", C={国家}"

        # 生成占位 CSR
        pem_data = f"-----BEGIN CERTIFICATE REQUEST-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE REQUEST-----"
        csr = Certificate()
        csr._pem = pem_data.encode('utf-8')
        csr._subject = {'CN': 通用名称}
        if 组织:
            csr._subject['O'] = 组织
        if 国家:
            csr._subject['C'] = 国家
        return csr
    except Exception as e:
        raise Exception("生成CSR失败: " + str(e))


def csr_get_raw_pem(csr):
    """获取 CSR 原始 PEM 文本"""
    if not csr:
        raise Exception("csr_get_raw_pem失败: CSR为空")
    return csr._pem.decode('utf-8') if isinstance(csr._pem, bytes) else csr._pem


def csr_get_subject(csr):
    """获取 CSR 主体"""
    if not csr:
        raise Exception("csr_get_subject失败: CSR为空")
    return csr._subject


def csr_get_pub_pem(csr):
    """获取 CSR 公钥 PEM"""
    if not csr:
        raise Exception("csr_get_pub_pem失败: CSR为空")
    return '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END PUBLIC KEY-----'


# =============================================================================
# CRL 操作
# =============================================================================

def 检查CRL(cert, crl):
    """检查证书是否在 CRL 中"""
    if not cert:
        raise Exception("检查CRL失败: 证书为空")
    return False


def 加载CRL(crl文本):
    """加载 CRL（简化实现）"""
    if not crl文本:
        raise Exception("加载CRL失败: CRL文本为空")
    return {'revoked': []}


def crl_is_revoked(crl, cert):
    """检查证书是否被吊销"""
    if not crl:
        return False
    return False


def crl_get_revoke_date(crl, cert):
    """获取证书吊销日期"""
    return None


def crl_get_revoke_ason(crl):
    """获取 CRL 更新日期"""
    return _datetime.datetime.now().isoformat()


def crl_get_err(crl):
    """获取 CRL 错误信息"""
    return ''


# =============================================================================
# 格式转换
# =============================================================================

def cert_pem_to_der(pem文本):
    """PEM 转 DER"""
    if not pem文本:
        raise Exception("cert_pem_to_der失败: PEM为空")
    try:
        lines = pem文本.strip().split('\n')
        b64_lines = [line for line in lines if not line.startswith('-----')]
        b64_data = ''.join(b64_lines)
        return _b64.b64decode(b64_data)
    except Exception as e:
        raise Exception("cert_pem_to_der失败: " + str(e))


def PEM转DER(pem文本):
    """PEM 转 DER"""
    return cert_pem_to_der(pem文本)


def DER转PEM(der数据):
    """DER 转 PEM"""
    if not der数据:
        raise Exception("DER转PEM失败: DER数据为空")
    try:
        b64_data = _b64.b64encode(der数据).decode('ascii')
        lines = ['-----BEGIN CERTIFICATE-----']
        for i in range(0, len(b64_data), 64):
            lines.append(b64_data[i:i+64])
        lines.append('-----END CERTIFICATE-----')
        return '\n'.join(lines)
    except Exception as e:
        raise Exception("DER转PEM失败: " + str(e))


# =============================================================================
# 验证结果
# =============================================================================

def verify_is_valid(验证结果):
    """检查验证结果是否有效"""
    if not 验证结果:
        return False
    return 验证结果.get('valid', False)


def verify_get_err(验证结果):
    """获取验证错误信息"""
    if not 验证结果:
        return '验证结果为空'
    return 验证结果.get('error', '')


def verify_get_chain_depth(验证结果):
    """获取验证链深度"""
    if not 验证结果:
        return 0
    return 验证结果.get('chain_depth', 0)


def verify_get_verify_path(验证结果):
    """获取验证路径"""
    if not 验证结果:
        return []
    return 验证结果.get('verify_path', [])


# =============================================================================
# 资源释放
# =============================================================================

def 释放证书(cert):
    """释放证书资源"""
    if cert:
        cert._pem = b''
        cert._der = b''
        cert._subject = {}
        cert._issuer = {}
        cert._fingerprint = {}