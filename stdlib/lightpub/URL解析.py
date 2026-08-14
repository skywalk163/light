"""
URL解析 — duanpub 桥接模块

基于 Python urllib.parse 库封装，函数名对齐 duanpub/packages/URL解析/源.duan。

duanpub 原始包通过 C FFI 实现 URL 解析功能，
本桥接模块用 Python urllib.parse 标准库替代，提供等价的 URL 解析与构建功能。
"""

import urllib.parse as _urlparse


# =============================================================================
# 数据结构
# =============================================================================

class _ParsedURL:
    """解析后的 URL 对象"""
    def __init__(self, scheme='', netloc='', path='', params='',
                 query='', fragment='', hostname='', port=None,
                 username='', password=''):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password


# =============================================================================
# URL 解析
# =============================================================================

def 解析URL(url):
    """
    解析 URL 字符串，返回 ParsedURL 对象。
    包含 scheme, netloc, path, params, query, fragment, hostname, port, username, password
    """
    if not url:
        raise Exception("解析URL失败: URL 为空")
    try:
        parsed = _urlparse.urlparse(url)
        return _ParsedURL(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=parsed.path,
            params=parsed.params,
            query=parsed.query,
            fragment=parsed.fragment,
            hostname=parsed.hostname or '',
            port=parsed.port,
            username=parsed.username or '',
            password=parsed.password or '',
        )
    except Exception as e:
        raise Exception("解析URL失败: " + str(e))


# =============================================================================
# URL 构建
# =============================================================================

def 构建URL(scheme='', hostname='', port=None, path='', params='',
            query='', fragment='', username='', password=''):
    """构建 URL 字符串"""
    try:
        # 构建 netloc
        netloc = hostname
        if port is not None:
            netloc = f"{hostname}:{port}"

        # 构建完整 URL
        result = _urlparse.urlunparse((
            scheme,
            netloc,
            path,
            params,
            query,
            fragment
        ))
        return result
    except Exception as e:
        raise Exception("构建URL失败: " + str(e))


# =============================================================================
# 查询参数编码/解码
# =============================================================================

def 编码查询参数(params, doseq=False):
    """将字典编码为查询参数字符串"""
    if not params:
        return ''
    try:
        return _urlparse.urlencode(params, doseq=doseq)
    except Exception as e:
        raise Exception("编码查询参数失败: " + str(e))


def 解析查询参数(query_string, keep_blank_values=False):
    """解析查询参数字符串为字典"""
    if not query_string:
        return {}
    try:
        parsed = _urlparse.parse_qs(query_string, keep_blank_values=keep_blank_values)
        # 简化：单值列表转字符串
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    except Exception as e:
        raise Exception("解析查询参数失败: " + str(e))


# =============================================================================
# 便捷函数
# =============================================================================

def URL拼接(base, *components):
    """拼接 URL 路径"""
    try:
        return _urlparse.urljoin(base, '/'.join(components))
    except Exception as e:
        raise Exception("URL拼接失败: " + str(e))


def 获取URL参数(url, param_name, default=None):
    """从 URL 中获取指定查询参数的值"""
    parsed = 解析URL(url)
    params = 解析查询参数(parsed.query)
    return params.get(param_name, default)


def 添加URL参数(url, **params):
    """向 URL 添加查询参数"""
    if '?' in url:
        base, existing_query = url.split('?', 1)
        existing_params = 解析查询参数(existing_query)
        existing_params.update(params)
        return base + '?' + 编码查询参数(existing_params)
    else:
        return url + '?' + 编码查询参数(params)