"""
HTTP客户端 — duanpub 桥接模块

基于 Python requests 库封装，函数名对齐 duanpub/packages/HTTP客户端/源.duan。

duanpub 原始包通过 C FFI 实现 TCP/SSL，本桥接模块用 Python requests 替代，
提供等价的 HTTP 客户端功能。函数签名与 duanpub 包保持一致。
"""

import urllib.request
import urllib.error
import urllib.parse
import json as _json
import ssl as _ssl


# =============================================================================
# HTTP 请求/响应数据结构
# =============================================================================

class HTTPRequest:
    """HTTP 请求对象"""
    def __init__(self, method='GET', url='', headers=None, body=None,
                 query=None, follow_redirect=True, timeout=30):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.query = query or {}
        self.follow_redirect = follow_redirect
        self.timeout = timeout


class HTTPResponse:
    """HTTP 响应对象"""
    def __init__(self, status=0, status_msg='', headers=None, body='',
                 final_url='', cookies=None):
        self.status = status
        self.status_msg = status_msg
        self.headers = headers or {}
        self.body = body
        self.final_url = final_url
        self.cookies = cookies or {}


# =============================================================================
# 核心函数（对齐 duanpub 源.duan 的 API 设计）
# =============================================================================

def HTTP获取(url, headers=None, timeout=30):
    """HTTP GET 请求，返回 HTTPResponse"""
    return _do_request('GET', url, headers=headers, timeout=timeout)


def HTTP提交(url, body=None, headers=None, timeout=30, content_type='application/json'):
    """HTTP POST 请求，返回 HTTPResponse"""
    if headers is None:
        headers = {}
    if content_type and 'Content-Type' not in headers:
        headers['Content-Type'] = content_type
    return _do_request('POST', url, body=body, headers=headers, timeout=timeout)


def HTTP更新(url, body=None, headers=None, timeout=30, content_type='application/json'):
    """HTTP PUT 请求，返回 HTTPResponse"""
    if headers is None:
        headers = {}
    if content_type and 'Content-Type' not in headers:
        headers['Content-Type'] = content_type
    return _do_request('PUT', url, body=body, headers=headers, timeout=timeout)


def HTTP删除(url, headers=None, timeout=30):
    """HTTP DELETE 请求，返回 HTTPResponse"""
    return _do_request('DELETE', url, headers=headers, timeout=timeout)


def HTTP修补(url, body=None, headers=None, timeout=30, content_type='application/json'):
    """HTTP PATCH 请求，返回 HTTPResponse"""
    if headers is None:
        headers = {}
    if content_type and 'Content-Type' not in headers:
        headers['Content-Type'] = content_type
    return _do_request('PATCH', url, body=body, headers=headers, timeout=timeout)


def HTTP头部(url, headers=None, timeout=30):
    """HTTP HEAD 请求，返回 HTTPResponse"""
    return _do_request('HEAD', url, headers=headers, timeout=timeout)


# =============================================================================
# 便捷函数
# =============================================================================

def 获取JSON(url, headers=None, timeout=30):
    """GET 请求并解析 JSON 响应，返回 dict/list"""
    resp = HTTP获取(url, headers=headers, timeout=timeout)
    if resp.status == 200:
        return _json.loads(resp.body)
    return None


def 发送JSON(url, data, method='POST', headers=None, timeout=30):
    """发送 JSON 数据并返回 HTTPResponse"""
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    body = _json.dumps(data, ensure_ascii=False)
    return _do_request(method, url, body=body, headers=headers, timeout=timeout)


def 下载文件(url, 文件路径, headers=None, timeout=300):
    """下载文件到指定路径，返回 True/False"""
    try:
        req = _build_request('GET', url, headers=headers)
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            with open(文件路径, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except Exception:
        return False


def URL编码(字符串):
    """URL 编码"""
    return urllib.parse.quote(字符串, safe='')


def URL解码(字符串):
    """URL 解码"""
    return urllib.parse.unquote(字符串)


def 拼接URL(base_url, params=None):
    """拼接 URL 和查询参数"""
    if not params:
        return base_url
    query_str = urllib.parse.urlencode(params)
    separator = '&' if '?' in base_url else '?'
    return base_url + separator + query_str


# =============================================================================
# 内部实现
# =============================================================================

def _build_request(method, url, body=None, headers=None):
    """构建 urllib Request 对象"""
    if headers is None:
        headers = {}
    if body is not None and isinstance(body, str):
        body = body.encode('utf-8')
    return urllib.request.Request(url, data=body, method=method, headers=headers)


def _do_request(method, url, body=None, headers=None, timeout=30):
    """执行 HTTP 请求，返回 HTTPResponse"""
    try:
        req = _build_request(method, url, body=body, headers=headers)
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_body = resp.read()
            if isinstance(resp_body, bytes):
                try:
                    resp_body = resp_body.decode('utf-8')
                except UnicodeDecodeError:
                    resp_body = resp_body.decode('latin-1')

            resp_headers = dict(resp.headers)
            return HTTPResponse(
                status=resp.status,
                status_msg=resp.reason,
                headers=resp_headers,
                body=resp_body,
                final_url=resp.url,
            )
    except urllib.error.HTTPError as e:
        resp_body = ''
        try:
            resp_body = e.read().decode('utf-8')
        except Exception:
            pass
        return HTTPResponse(
            status=e.code,
            status_msg=e.reason,
            headers=dict(e.headers) if e.headers else {},
            body=resp_body,
            final_url=url,
        )
    except Exception as e:
        return HTTPResponse(
            status=0,
            status_msg=str(e),
            body='',
            final_url=url,
        )
