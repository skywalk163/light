"""
HTTP客户端 — lightpub 桥接模块 (增强版)

基于 Python requests 库封装，提供全面的 HTTP 客户端功能。
函数名对齐 lightpub/packages/HTTP客户端/源.light。

lightpub 原始包通过 C FFI 实现 TCP/SSL，本桥接模块用 Python requests 替代，
提供等价的 HTTP 客户端功能。函数签名与 lightpub 包保持一致。

支持功能：
- GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS 全部方法
- 超时配置
- Cookie 管理（CookieJar、会话持久）
- 自定义请求头
- 查询参数
- 请求体（JSON、表单、multipart 文件上传）
- 文件上传/下载（流式）
- SSL/TLS 验证选项
- 代理支持
- 重定向跟随（可配置）
- 响应流式读取
- 连接池管理
- 会话管理（持久化 Cookie、会话级请求头）
- 上下文管理器
- 错误处理（超时、连接、HTTP 状态、SSL 错误）
- 异步 HTTP 客户端
"""

import json as _json
import os as _os
from typing import Optional, Any
from urllib.parse import urlencode, urlparse, urlunparse

import requests as _requests
from requests import Session as _Session
from requests.adapters import HTTPAdapter as _HTTPAdapter
from requests.cookies import RequestsCookieJar as _CookieJar
from urllib3.util.retry import Retry as _Retry

# =============================================================================
# 错误类型
# =============================================================================

class HTTP错误(Exception):
    """HTTP 操作基类错误"""
    pass

class 超时错误(HTTP错误):
    """请求超时错误"""
    pass

class 连接错误(HTTP错误):
    """网络连接错误"""
    pass

class HTTP状态错误(HTTP错误):
    """HTTP 状态码错误（如 4xx/5xx）"""
    def __init__(self, 状态码, 消息, 响应=None):
        self.状态码 = 状态码
        self.消息 = 消息
        self.响应 = 响应
        super().__init__(f"HTTP {状态码}: {消息}")

class SSL错误(HTTP错误):
    """SSL/TLS 错误"""
    pass


# =============================================================================
# HTTP 请求/响应数据结构
# =============================================================================

class HTTPRequest:
    """HTTP 请求对象"""
    def __init__(self, method='GET', url='', headers=None, body=None,
                 query=None, follow_redirect=True, timeout=30,
                 verify=True, cert=None, proxies=None, stream=False):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.query = query or {}
        self.follow_redirect = follow_redirect
        self.timeout = timeout
        self.verify = verify
        self.cert = cert
        self.proxies = proxies
        self.stream = stream


class HTTPResponse:
    """HTTP 响应对象"""
    def __init__(self, status=0, status_msg='', headers=None, body='',
                 final_url='', cookies=None, elapsed=0, raw=None):
        self.status = status
        self.status_msg = status_msg
        self.headers = headers or {}
        self.body = body
        self.final_url = final_url
        self.cookies = cookies or {}
        self.elapsed = elapsed
        self._raw = raw

    def json(self):
        """将响应体解析为 JSON"""
        if isinstance(self.body, str):
            return _json.loads(self.body)
        return _json.loads(self.body.decode('utf-8'))

    def iter_content(self, chunk_size=8192):
        """流式读取响应内容（仅当原始请求使用 stream=True 时有效）"""
        if self._raw is not None:
            return self._raw.iter_content(chunk_size=chunk_size)
        raise HTTP错误("响应不是流式模式，请使用 stream=True 发起请求")


# =============================================================================
# 会话管理
# =============================================================================

class 会话:
    """
    持久化 HTTP 会话，自动管理 Cookie 和连接池。

    支持上下文管理器，确保资源释放。

    用法：
        with 会话() as s:
            resp = s.get('http://example.com')
            resp = s.post('http://example.com/api', json={'key': 'value'})
    """

    def __init__(self, headers=None, timeout=30, verify=True,
                 max_retries=0, pool_connections=10, pool_maxsize=10):
        """
        创建会话

        Args:
            headers: 会话级默认请求头
            timeout: 默认超时时间（秒）
            verify: 是否验证 SSL 证书
            max_retries: 最大重试次数（0 表示不重试）
            pool_connections: 连接池大小
            pool_maxsize: 连接池最大连接数
        """
        self._session = _Session()
        self._timeout = timeout
        self._verify = verify

        if headers:
            self._session.headers.update(headers)

        # 配置连接池和重试
        if max_retries > 0:
            retry_strategy = _Retry(
                total=max_retries,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = _HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
            )
            self._session.mount('https://', adapter)
            self._session.mount('http://', adapter)

        # 默认禁止弹跳 SSL 警告
        _requests.packages.urllib3.disable_warnings(
            _requests.packages.urllib3.exceptions.InsecureRequestWarning
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭会话，释放连接池"""
        self._session.close()

    # ---- 请求头管理 ----

    @property
    def headers(self):
        """会话级请求头"""
        return self._session.headers

    @headers.setter
    def headers(self, value):
        self._session.headers = value

    def set_header(self, name, value):
        """设置会话级请求头"""
        self._session.headers[name] = value

    def remove_header(self, name):
        """移除会话级请求头"""
        self._session.headers.pop(name, None)

    # ---- Cookie 管理 ----

    @property
    def cookies(self):
        """会话 CookieJar"""
        return self._session.cookies

    def set_cookie(self, key, value, domain='', path='/'):
        """设置会话 Cookie"""
        self._session.cookies.set(key, value, domain=domain, path=path)

    def get_cookie(self, key):
        """获取会话 Cookie 值"""
        for cookie in self._session.cookies:
            if cookie.name == key:
                return cookie.value
        return None

    def remove_cookie(self, key):
        """移除会话 Cookie"""
        # 遍历所有 domain 和 path 删除匹配的 Cookie
        for cookie in list(self._session.cookies):
            if cookie.name == key:
                try:
                    self._session.cookies.clear(domain=cookie.domain, path=cookie.path, name=key)
                except KeyError:
                    pass

    def clear_cookies(self):
        """清空所有会话 Cookie"""
        self._session.cookies.clear()

    # ---- 代理配置 ----

    def set_proxies(self, proxies):
        """
        设置代理

        Args:
            proxies: 代理字典，如 {'http': 'http://proxy:8080', 'https': 'http://proxy:8080'}
        """
        self._session.proxies.update(proxies)

    def remove_proxies(self):
        """移除代理配置"""
        self._session.proxies.clear()

    # ---- HTTP 方法 ----

    def get(self, url, params=None, headers=None, timeout=None,
            stream=False, verify=None, **kwargs):
        """GET 请求"""
        return self._request('GET', url, params=params, headers=headers,
                             timeout=timeout, stream=stream, verify=verify, **kwargs)

    def post(self, url, data=None, json=None, files=None, headers=None,
             timeout=None, stream=False, verify=None, **kwargs):
        """POST 请求"""
        return self._request('POST', url, data=data, json=json, files=files,
                             headers=headers, timeout=timeout, stream=stream,
                             verify=verify, **kwargs)

    def put(self, url, data=None, json=None, files=None, headers=None,
            timeout=None, stream=False, verify=None, **kwargs):
        """PUT 请求"""
        return self._request('PUT', url, data=data, json=json, files=files,
                             headers=headers, timeout=timeout, stream=stream,
                             verify=verify, **kwargs)

    def delete(self, url, headers=None, timeout=None, stream=False,
               verify=None, **kwargs):
        """DELETE 请求"""
        return self._request('DELETE', url, headers=headers, timeout=timeout,
                             stream=stream, verify=verify, **kwargs)

    def patch(self, url, data=None, json=None, files=None, headers=None,
              timeout=None, stream=False, verify=None, **kwargs):
        """PATCH 请求"""
        return self._request('PATCH', url, data=data, json=json, files=files,
                             headers=headers, timeout=timeout, stream=stream,
                             verify=verify, **kwargs)

    def head(self, url, headers=None, timeout=None, verify=None, **kwargs):
        """HEAD 请求"""
        return self._request('HEAD', url, headers=headers, timeout=timeout,
                             verify=verify, **kwargs)

    def options(self, url, headers=None, timeout=None, verify=None, **kwargs):
        """OPTIONS 请求"""
        return self._request('OPTIONS', url, headers=headers, timeout=timeout,
                             verify=verify, **kwargs)

    def _request(self, method, url, params=None, data=None, json=None,
                 files=None, headers=None, timeout=None, stream=False,
                 verify=None, allow_redirects=None, **kwargs):
        """内部请求执行方法"""
        if timeout is None:
            timeout = self._timeout
        if verify is None:
            verify = self._verify
        if allow_redirects is None:
            allow_redirects = True

        try:
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                files=files,
                headers=headers,
                timeout=timeout,
                stream=stream,
                verify=verify,
                allow_redirects=allow_redirects,
                **kwargs
            )
        except _requests.exceptions.SSLError as e:
            raise SSL错误(f"SSL/TLS 错误: {e}") from e
        except _requests.exceptions.ConnectionError as e:
            raise 连接错误(f"连接失败: {url}") from e
        except _requests.exceptions.Timeout as e:
            raise 超时错误(f"请求超时 ({timeout}s): {url}") from e
        except _requests.exceptions.RequestException as e:
            raise HTTP错误(f"请求失败: {e}") from e

        return self._to_response(resp)

    def _to_response(self, resp):
        """将 requests.Response 转换为 HTTPResponse"""
        body = resp.content
        # 尝试解码为文本
        try:
            body = resp.text
        except Exception:
            pass

        cookies = {}
        for cookie in resp.cookies:
            cookies[cookie.name] = cookie.value

        return HTTPResponse(
            status=resp.status_code,
            status_msg=resp.reason,
            headers=dict(resp.headers),
            body=body,
            final_url=resp.url,
            cookies=cookies,
            elapsed=resp.elapsed.total_seconds(),
            raw=resp if resp.raw else None,
        )


# =============================================================================
# 异步 HTTP 客户端
# =============================================================================

class 异步HTTP客户端:
    """
    基于 asyncio + aiohttp 的异步 HTTP 客户端。

    用法：
        async def main():
            client = 异步HTTP客户端()
            resp = await client.get('http://example.com')
            print(resp.status)
            await client.close()
    """

    def __init__(self, headers=None, timeout=30, verify=True,
                 max_connections=50):
        """
        创建异步 HTTP 客户端

        Args:
            headers: 默认请求头
            timeout: 默认超时时间（秒）
            verify: 是否验证 SSL 证书
            max_connections: 最大连接数
        """
        self._headers = headers or {}
        self._timeout = timeout
        self._verify = verify
        self._max_connections = max_connections
        self._session = None
        self._connector = None

    async def _ensure_session(self):
        """确保 aiohttp 会话已创建"""
        if self._session is None or self._session.closed:
            import aiohttp
            import ssl as _ssl
            conn_kwargs = {}
            if not self._verify:
                ssl_ctx = _ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = _ssl.CERT_NONE
                conn_kwargs['ssl'] = ssl_ctx
            self._connector = aiohttp.TCPConnector(
                limit=self._max_connections,
                **conn_kwargs
            )
            timeout_obj = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                connector=self._connector,
                timeout=timeout_obj,
            )

    async def close(self):
        """关闭异步客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector and not self._connector.closed:
            await self._connector.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get(self, url, params=None, headers=None, timeout=None, **kwargs):
        """异步 GET 请求"""
        return await self._request('GET', url, params=params, headers=headers,
                                   timeout=timeout, **kwargs)

    async def post(self, url, data=None, json=None, headers=None,
                   timeout=None, **kwargs):
        """异步 POST 请求"""
        return await self._request('POST', url, data=data, json=json,
                                   headers=headers, timeout=timeout, **kwargs)

    async def put(self, url, data=None, json=None, headers=None,
                  timeout=None, **kwargs):
        """异步 PUT 请求"""
        return await self._request('PUT', url, data=data, json=json,
                                   headers=headers, timeout=timeout, **kwargs)

    async def delete(self, url, headers=None, timeout=None, **kwargs):
        """异步 DELETE 请求"""
        return await self._request('DELETE', url, headers=headers,
                                   timeout=timeout, **kwargs)

    async def patch(self, url, data=None, json=None, headers=None,
                    timeout=None, **kwargs):
        """异步 PATCH 请求"""
        return await self._request('PATCH', url, data=data, json=json,
                                   headers=headers, timeout=timeout, **kwargs)

    async def head(self, url, headers=None, timeout=None, **kwargs):
        """异步 HEAD 请求"""
        return await self._request('HEAD', url, headers=headers,
                                   timeout=timeout, **kwargs)

    async def options(self, url, headers=None, timeout=None, **kwargs):
        """异步 OPTIONS 请求"""
        return await self._request('OPTIONS', url, headers=headers,
                                   timeout=timeout, **kwargs)

    async def _request(self, method, url, params=None, data=None, json=None,
                       headers=None, timeout=None, **kwargs):
        """内部异步请求执行方法"""
        await self._ensure_session()

        if timeout is not None:
            import aiohttp
            old_timeout = self._session._timeout
            self._session._timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            async with self._session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                **kwargs
            ) as resp:
                body = await resp.read()
                final_url = str(resp.url)
                cookies = {}
                for cookie in resp.cookies:
                    cookies[cookie.key] = cookie.value
                try:
                    body_str = body.decode('utf-8')
                except UnicodeDecodeError:
                    body_str = body.decode('latin-1')

                return HTTPResponse(
                    status=resp.status,
                    status_msg=resp.reason or '',
                    headers=dict(resp.headers),
                    body=body_str,
                    final_url=final_url,
                    cookies=cookies,
                )
        except Exception as e:
            err_str = str(e)
            if 'timeout' in err_str.lower() or 'Timeout' in type(e).__name__:
                raise 超时错误(f"异步请求超时 ({timeout or self._timeout}s): {url}") from e
            if 'connect' in err_str.lower() or 'Connection' in type(e).__name__:
                raise 连接错误(f"异步连接失败: {url}") from e
            raise HTTP错误(f"异步请求失败: {e}") from e


# =============================================================================
# 核心函数（对齐 lightpub 源.light 的 API 设计）
# =============================================================================

_默认会话 = _Session()


def HTTP获取(url, 查询参数=None, 请求头=None, 超时=30, 跟随重定向=True,
             SSL验证=True, 代理=None, 流式=False):
    """HTTP GET 请求，返回 HTTPResponse"""
    return _请求('GET', url, params=查询参数, headers=请求头, timeout=超时,
                 allow_redirects=跟随重定向, verify=SSL验证, proxies=代理,
                 stream=流式)


def HTTP提交(url, 正文=None, JSON=None, 文件=None, 请求头=None, 超时=30,
             内容类型='application/json', 跟随重定向=True, SSL验证=True,
             代理=None, 流式=False):
    """HTTP POST 请求，返回 HTTPResponse"""
    if 请求头 is None:
        请求头 = {}
    if 内容类型 and 'Content-Type' not in 请求头:
        请求头['Content-Type'] = 内容类型
    return _请求('POST', url, data=正文, json=JSON, files=文件,
                 headers=请求头, timeout=超时, allow_redirects=跟随重定向,
                 verify=SSL验证, proxies=代理, stream=流式)


def HTTP更新(url, 正文=None, JSON=None, 文件=None, 请求头=None, 超时=30,
             内容类型='application/json', 跟随重定向=True, SSL验证=True,
             代理=None):
    """HTTP PUT 请求，返回 HTTPResponse"""
    if 请求头 is None:
        请求头 = {}
    if 内容类型 and 'Content-Type' not in 请求头:
        请求头['Content-Type'] = 内容类型
    return _请求('PUT', url, data=正文, json=JSON, files=文件,
                 headers=请求头, timeout=超时, allow_redirects=跟随重定向,
                 verify=SSL验证, proxies=代理)


def HTTP删除(url, 请求头=None, 超时=30, 跟随重定向=True, SSL验证=True,
             代理=None):
    """HTTP DELETE 请求，返回 HTTPResponse"""
    return _请求('DELETE', url, headers=请求头, timeout=超时,
                 allow_redirects=跟随重定向, verify=SSL验证, proxies=代理)


def HTTP修补(url, 正文=None, JSON=None, 文件=None, 请求头=None, 超时=30,
             内容类型='application/json', 跟随重定向=True, SSL验证=True,
             代理=None):
    """HTTP PATCH 请求，返回 HTTPResponse"""
    if 请求头 is None:
        请求头 = {}
    if 内容类型 and 'Content-Type' not in 请求头:
        请求头['Content-Type'] = 内容类型
    return _请求('PATCH', url, data=正文, json=JSON, files=文件,
                 headers=请求头, timeout=超时, allow_redirects=跟随重定向,
                 verify=SSL验证, proxies=代理)


def HTTP头部(url, 请求头=None, 超时=30, 跟随重定向=True, SSL验证=True,
             代理=None):
    """HTTP HEAD 请求，返回 HTTPResponse"""
    return _请求('HEAD', url, headers=请求头, timeout=超时,
                 allow_redirects=跟随重定向, verify=SSL验证, proxies=代理)


def HTTP选项(url, 请求头=None, 超时=30, 跟随重定向=True, SSL验证=True,
             代理=None):
    """HTTP OPTIONS 请求，返回 HTTPResponse"""
    return _请求('OPTIONS', url, headers=请求头, timeout=超时,
                 allow_redirects=跟随重定向, verify=SSL验证, proxies=代理)


# =============================================================================
# 便捷函数
# =============================================================================

def 获取JSON(url, 查询参数=None, 请求头=None, 超时=30):
    """GET 请求并解析 JSON 响应，返回 dict/list。

    非 200 抛 `HTTP状态错误`（带状态码与响应），**不返回 None**：
    把「服务端拒了」和「服务端返回了 JSON null」压成同一个空值，
    调用方无法区分，正是「零静默降级」口径要拦的形态。
    """
    resp = HTTP获取(url, 查询参数=查询参数, 请求头=请求头, 超时=超时)
    if resp.status != 200:
        raise HTTP状态错误(resp.status, f"获取JSON 未拿到 200：{url}", resp)
    return resp.json()


def 发送JSON(url, data, method='POST', 请求头=None, 超时=30):
    """发送 JSON 数据并返回 HTTPResponse"""
    if 请求头 is None:
        请求头 = {}
    请求头['Content-Type'] = 'application/json'
    body = _json.dumps(data, ensure_ascii=False)
    return _请求(method, url, data=body, headers=请求头, timeout=超时)


def 下载文件(url, 文件路径, 请求头=None, 超时=300, SSL验证=True, 代理=None):
    """
    下载文件到指定路径，支持流式下载

    Args:
        url: 下载地址
        文件路径: 保存路径
        请求头: 自定义请求头
        超时: 超时时间（秒）
        SSL验证: 是否验证 SSL 证书
        代理: 代理设置

    Returns:
        bool: 是否下载成功
    """
    try:
        with _requests.get(url, headers=请求头, timeout=超时, stream=True,
                           verify=SSL验证, proxies=代理) as resp:
            resp.raise_for_status()
            with open(文件路径, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception:
        return False


def 上传文件(url, 文件字段, 文件路径, 额外字段=None, 请求头=None, 超时=300,
             SSL验证=True):
    """
    上传文件（multipart/form-data）

    Args:
        url: 上传地址
        文件字段: 文件字段名
        文件路径: 本地文件路径
        额外字段: 额外表单字段字典
        请求头: 自定义请求头
        超时: 超时时间（秒）
        SSL验证: 是否验证 SSL 证书

    Returns:
        HTTPResponse
    """
    files = {}
    if _os.path.isfile(文件路径):
        files[文件字段] = (文件路径, open(文件路径, 'rb'), 'application/octet-stream')
    else:
        raise HTTP错误(f"文件不存在: {文件路径}")

    try:
        resp = _requests.post(url, files=files, data=额外字段,
                              headers=请求头, timeout=超时, verify=SSL验证)
        return _响应转换(resp)
    except Exception as e:
        raise HTTP错误(f"上传文件失败: {e}") from e
    finally:
        for f in files.values():
            if isinstance(f, tuple) and len(f) > 1:
                try:
                    f[1].close()
                except Exception:
                    pass


def 下载文件流(url, 回调函数, 请求头=None, 超时=300, 块大小=8192, SSL验证=True):
    """
    流式下载文件，每块数据调用回调函数

    Args:
        url: 下载地址
        回调函数: 接收数据块的回调，签名 fn(chunk: bytes) -> None
        请求头: 自定义请求头
        超时: 超时时间（秒）
        块大小: 读取块大小
        SSL验证: 是否验证 SSL 证书

    Returns:
        bool: 是否下载成功
    """
    try:
        with _requests.get(url, headers=请求头, timeout=超时, stream=True,
                           verify=SSL验证) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=块大小):
                if chunk:
                    回调函数(chunk)
        return True
    except Exception:
        return False


def URL编码(字符串):
    """URL 编码"""
    from urllib.parse import quote
    return quote(字符串, safe='')


def URL解码(字符串):
    """URL 解码"""
    from urllib.parse import unquote
    return unquote(字符串)


def 拼接URL(base_url, params=None):
    """拼接 URL 和查询参数"""
    if not params:
        return base_url
    query_str = urlencode(params)
    separator = '&' if '?' in base_url else '?'
    return base_url + separator + query_str


# =============================================================================
# 内部实现
# =============================================================================

def _请求(method, url, params=None, data=None, json=None, files=None,
          headers=None, timeout=30, allow_redirects=True, verify=True,
          proxies=None, stream=False, **kwargs):
    """执行 HTTP 请求，返回 HTTPResponse"""
    global _默认会话
    try:
        resp = _默认会话.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            files=files,
            headers=headers,
            timeout=timeout,
            allow_redirects=allow_redirects,
            verify=verify,
            proxies=proxies,
            stream=stream,
            **kwargs
        )
        return _响应转换(resp)
    except _requests.exceptions.SSLError as e:
        raise SSL错误(f"SSL/TLS 错误: {e}") from e
    except _requests.exceptions.ConnectionError as e:
        raise 连接错误(f"连接失败: {url}") from e
    except _requests.exceptions.Timeout as e:
        raise 超时错误(f"请求超时 ({timeout}s): {url}") from e
    except _requests.exceptions.RequestException as e:
        raise HTTP错误(f"请求失败: {e}") from e


def _响应转换(resp):
    """将 requests.Response 转换为 HTTPResponse"""
    body = resp.content
    try:
        body = resp.text
    except Exception:
        pass

    cookies = {}
    for cookie in resp.cookies:
        cookies[cookie.name] = cookie.value

    return HTTPResponse(
        status=resp.status_code,
        status_msg=resp.reason,
        headers=dict(resp.headers),
        body=body,
        final_url=resp.url,
        cookies=cookies,
        elapsed=resp.elapsed.total_seconds(),
        raw=resp if resp.raw else None,
    )


def _构造请求(*args, **kwargs):
    """兼容旧版 _build_request 函数（已弃用）"""
    import warnings
    warnings.warn("_build_request 已弃用，请直接使用 HTTP 请求函数", DeprecationWarning)
    return None


# 为向后兼容保留旧函数名
_build_request = _构造请求
_do_request = _请求


# =============================================================================
# 创建会话快捷函数
# =============================================================================

def 创建会话(headers=None, timeout=30, verify=True, max_retries=0,
             pool_connections=10, pool_maxsize=10):
    """
    创建持久化 HTTP 会话

    Args:
        headers: 会话级默认请求头
        timeout: 默认超时时间（秒）
        verify: 是否验证 SSL 证书
        max_retries: 最大重试次数（0 表示不重试）
        pool_connections: 连接池大小
        pool_maxsize: 连接池最大连接数

    Returns:
        会话对象
    """
    return 会话(headers=headers, timeout=timeout, verify=verify,
                max_retries=max_retries, pool_connections=pool_connections,
                pool_maxsize=pool_maxsize)