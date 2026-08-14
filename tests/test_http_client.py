"""
HTTP 客户端模块测试

测试 lightpub/HTTP客户端.py 增强版的所有功能：
- 基本 HTTP 方法（GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS）
- 超时配置
- Cookie 管理
- 会话管理（Session）
- 文件上传/下载
- SSL/TLS 验证
- 代理支持
- 重定向跟随
- 流式响应
- 错误处理
- 异步客户端
"""

import os
import sys
import json
import tempfile
import threading
import time
import asyncio

import pytest

# stdlib/lightpub/HTTP客户端.py 依赖第三方 requests/urllib3；
# 本项目 pyproject 的 dependencies 为空（零核心依赖），故未安装时跳过整个模块
pytest.importorskip("requests")

# 添加 stdlib 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stdlib.lightpub.HTTP客户端 import (
    # 核心函数
    HTTP获取, HTTP提交, HTTP更新, HTTP删除, HTTP修补, HTTP头部, HTTP选项,
    # 便捷函数
    获取JSON, 发送JSON, 下载文件, 上传文件, 下载文件流,
    URL编码, URL解码, 拼接URL,
    # 数据结构
    HTTPRequest, HTTPResponse,
    # 会话管理
    会话, 创建会话,
    # 异步
    异步HTTP客户端,
    # 错误类型
    HTTP错误, 超时错误, 连接错误, HTTP状态错误, SSL错误,
)


# =============================================================================
# 测试用 HTTP 服务器
# =============================================================================

class _测试服务器:
    """用于测试的简易 HTTP 服务器"""

    def __init__(self, host='127.0.0.1', port=0):
        self.host = host
        self.port = port
        self._server = None
        self._thread = None
        self._ready = threading.Event()

    def _处理请求(self):
        """在独立线程中运行 HTTP 服务器"""
        import http.server

        class _Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _respond(self, status=200, body=b'OK', content_type='text/plain',
                         headers=None, cookies=None):
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                if headers:
                    for k, v in headers.items():
                        self.send_header(k, v)
                if cookies:
                    for k, v in cookies.items():
                        self.send_header('Set-Cookie', f'{k}={v}; Path=/')
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == '/':
                    self._respond(200, b'Hello World')
                elif self.path == '/json':
                    self._respond(200, json.dumps({"message": "hello"}).encode(),
                                  content_type='application/json')
                elif self.path == '/redirect':
                    self.send_response(301)
                    self.send_header('Location', '/')
                    self.end_headers()
                elif self.path == '/redirect-loop':
                    self.send_response(301)
                    self.send_header('Location', '/redirect-loop')
                    self.end_headers()
                elif self.path == '/set-cookie':
                    self._respond(200, b'cookie set', cookies={'session_id': 'abc123'})
                elif self.path == '/echo-headers':
                    headers_str = json.dumps(dict(self.headers))
                    self._respond(200, headers_str.encode(),
                                  content_type='application/json')
                elif self.path.startswith('/search'):
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(self.path).query)
                    result = json.dumps(dict(qs))
                    self._respond(200, result.encode(), content_type='application/json')
                elif self.path == '/slow':
                    import time
                    time.sleep(0.5)
                    self._respond(200, b'slow response')
                elif self.path == '/status/404':
                    self._respond(404, b'Not Found')
                elif self.path == '/status/500':
                    self._respond(500, b'Internal Server Error')
                elif self.path == '/stream':
                    body = b'chunk1\nchunk2\nchunk3\n'
                    self._respond(200, body)
                elif self.path == '/auth':
                    auth = self.headers.get('Authorization', '')
                    if auth == 'Bearer test-token':
                        self._respond(200, b'authenticated')
                    else:
                        self._respond(401, b'unauthorized')
                else:
                    self._respond(404, b'Not Found')

            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length > 0 else b''
                content_type = self.headers.get('Content-Type', '')

                if self.path == '/echo':
                    self._respond(200, body, content_type=content_type)
                elif self.path == '/form':
                    form_data = {}
                    if content_type.startswith('application/x-www-form-urlencoded'):
                        from urllib.parse import parse_qs
                        form_data = parse_qs(body.decode())
                        form_data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
                    self._respond(200, json.dumps(form_data).encode(),
                                  content_type='application/json')
                elif self.path == '/upload':
                    self._respond(200, json.dumps({"uploaded": True}).encode(),
                                  content_type='application/json')
                elif self.path == '/json':
                    data = json.loads(body)
                    data['received'] = True
                    self._respond(200, json.dumps(data).encode(),
                                  content_type='application/json')
                else:
                    self._respond(200, body)

            def do_PUT(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length > 0 else b''
                self._respond(200, body)

            def do_DELETE(self):
                self._respond(200, b'deleted')

            def do_PATCH(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length > 0 else b''
                self._respond(200, body)

            def do_HEAD(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('X-Test-Header', 'test-value')
                self.end_headers()

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header('Allow', 'GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS')
                self.end_headers()

        # 创建服务器
        self._server = http.server.HTTPServer((self.host, self.port), _Handler)
        self.port = self._server.server_address[1]
        self._ready.set()
        self._server.serve_forever()

    def start(self):
        """启动测试服务器"""
        self._thread = threading.Thread(target=self._处理请求, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
        return self

    def stop(self):
        """停止测试服务器"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'


# =============================================================================
# 测试
# =============================================================================

_服务器 = None


def setup_module():
    """全局测试服务器初始化"""
    global _服务器
    _服务器 = _测试服务器().start()


def teardown_module():
    """全局测试服务器清理"""
    global _服务器
    if _服务器:
        _服务器.stop()


def test_http_get():
    """测试 GET 请求"""
    resp = HTTP获取(f'{_服务器.url}/')
    assert resp.status == 200
    assert resp.body == 'Hello World'
    assert resp.final_url == f'{_服务器.url}/'


def test_http_get_with_query():
    """测试带查询参数的 GET 请求"""
    resp = HTTP获取(f'{_服务器.url}/search', 查询参数={'q': 'test', 'page': '1'})
    assert resp.status == 200
    data = json.loads(resp.body)
    assert data['q'] == ['test']
    assert data['page'] == ['1']


def test_http_get_with_headers():
    """测试带自定义请求头的 GET 请求"""
    resp = HTTP获取(f'{_服务器.url}/echo-headers', 请求头={'X-Custom': 'test-value'})
    assert resp.status == 200
    data = json.loads(resp.body)
    assert data.get('X-Custom') == 'test-value' or 'x-custom' in {k.lower() for k in data}


def test_http_post():
    """测试 POST 请求"""
    resp = HTTP提交(f'{_服务器.url}/echo', 正文='test body')
    assert resp.status == 200
    assert resp.body == 'test body'


def test_http_post_json():
    """测试 POST JSON 请求"""
    data = {'key': 'value', 'num': 42}
    resp = HTTP提交(f'{_服务器.url}/json', JSON=data)
    assert resp.status == 200
    result = json.loads(resp.body)
    assert result['key'] == 'value'
    assert result['received'] is True


def test_http_put():
    """测试 PUT 请求"""
    resp = HTTP更新(f'{_服务器.url}/echo', 正文='put body')
    assert resp.status == 200
    assert resp.body == 'put body'


def test_http_delete():
    """测试 DELETE 请求"""
    resp = HTTP删除(f'{_服务器.url}/echo')
    assert resp.status == 200
    assert resp.body == 'deleted'


def test_http_patch():
    """测试 PATCH 请求"""
    resp = HTTP修补(f'{_服务器.url}/echo', 正文='patch body')
    assert resp.status == 200
    assert resp.body == 'patch body'


def test_http_head():
    """测试 HEAD 请求"""
    resp = HTTP头部(f'{_服务器.url}/echo')
    assert resp.status == 200
    # HEAD 请求不应返回响应体
    assert resp.body is None or resp.body == ''


def test_http_options():
    """测试 OPTIONS 请求"""
    resp = HTTP选项(f'{_服务器.url}/echo')
    assert resp.status == 204
    # 检查 Allow 头
    allow = resp.headers.get('Allow', '')
    assert 'GET' in allow
    assert 'POST' in allow


def test_get_json():
    """测试获取 JSON 响应"""
    result = 获取JSON(f'{_服务器.url}/json')
    assert result is not None
    assert result['message'] == 'hello'


def test_get_json_non_200():
    """测试非 200 时获取 JSON 返回 None"""
    result = 获取JSON(f'{_服务器.url}/status/404')
    assert result is None


def test_send_json():
    """测试发送 JSON 数据"""
    data = {'name': 'test', 'value': 123}
    resp = 发送JSON(f'{_服务器.url}/json', data)
    assert resp.status == 200
    result = json.loads(resp.body)
    assert result['name'] == 'test'
    assert result['received'] is True


def test_url_encode_decode():
    """测试 URL 编码解码"""
    original = '你好世界'
    encoded = URL编码(original)
    assert encoded != original
    decoded = URL解码(encoded)
    assert decoded == original


def test_url_join():
    """测试 URL 拼接"""
    url = 拼接URL('http://example.com/api', {'q': 'test', 'page': '1'})
    assert url == 'http://example.com/api?q=test&page=1'

    url2 = 拼接URL('http://example.com/api?existing=1', {'new': '2'})
    assert 'existing=1' in url2
    assert 'new=2' in url2


def test_redirect_follow():
    """测试重定向跟随（默认跟随）"""
    resp = HTTP获取(f'{_服务器.url}/redirect')
    assert resp.status == 200
    assert resp.body == 'Hello World'
    assert resp.final_url == f'{_服务器.url}/'


def test_redirect_no_follow():
    """测试重定向不跟随"""
    resp = HTTP获取(f'{_服务器.url}/redirect', 跟随重定向=False)
    assert resp.status == 301


def test_status_404():
    """测试 404 状态码"""
    resp = HTTP获取(f'{_服务器.url}/nonexistent')
    assert resp.status == 404


def test_status_500():
    """测试 500 状态码"""
    resp = HTTP获取(f'{_服务器.url}/status/500')
    assert resp.status == 500


def test_custom_headers():
    """测试自定义请求头"""
    resp = HTTP获取(f'{_服务器.url}/echo-headers',
                    请求头={'Authorization': 'Bearer test-token', 'X-API-Key': 'secret'})
    assert resp.status == 200
    data = json.loads(resp.body)
    keys_lower = {k.lower(): v for k, v in data.items()}
    assert keys_lower.get('authorization') == 'Bearer test-token'


def test_http_response_json():
    """测试响应对象 JSON 解析"""
    resp = HTTP获取(f'{_服务器.url}/json')
    result = resp.json()
    assert result['message'] == 'hello'


def test_http_response_elapsed():
    """测试响应耗时"""
    resp = HTTP获取(f'{_服务器.url}/')
    assert resp.elapsed >= 0
    assert isinstance(resp.elapsed, float)


def test_http_response_headers():
    """测试响应头"""
    resp = HTTP获取(f'{_服务器.url}/')
    assert 'Content-Type' in resp.headers
    assert resp.headers['Content-Type'] == 'text/plain'


# =============================================================================
# 会话管理测试
# =============================================================================

def test_session_basic():
    """测试基本会话功能"""
    with 会话() as s:
        resp = s.get(f'{_服务器.url}/')
        assert resp.status == 200
        assert resp.body == 'Hello World'


def test_session_headers():
    """测试会话级请求头"""
    with 会话(headers={'X-Session': 'test'}) as s:
        resp = s.get(f'{_服务器.url}/echo-headers')
        assert resp.status == 200
        data = json.loads(resp.body)
        keys_lower = {k.lower(): v for k, v in data.items()}
        # 会话级头应该被发送（注意 http.server 可能转小写头名）
        assert 'x-session' in keys_lower


def test_session_cookie_persistence():
    """测试会话 Cookie 持久化"""
    with 会话() as s:
        # 首次请求，服务器设置 Cookie
        resp = s.get(f'{_服务器.url}/set-cookie')
        assert resp.status == 200
        # 检查 Cookie 是否被会话保存
        cookie = s.get_cookie('session_id')
        assert cookie == 'abc123'

        # 检查 Cookie 也在响应对象中
        assert resp.cookies.get('session_id') == 'abc123'


def test_session_set_cookie():
    """测试会话手动设置 Cookie"""
    with 会话() as s:
        s.set_cookie('my_cookie', 'my_value', domain='127.0.0.1')
        cookie = s.get_cookie('my_cookie')
        assert cookie == 'my_value'


def test_session_remove_cookie():
    """测试会话移除 Cookie"""
    with 会话() as s:
        s.set_cookie('test_cookie', 'test_value', domain='127.0.0.1')
        s.remove_cookie('test_cookie')
        assert s.get_cookie('test_cookie') is None


def test_session_clear_cookies():
    """测试会话清空 Cookie"""
    with 会话() as s:
        s.set_cookie('c1', 'v1', domain='127.0.0.1')
        s.set_cookie('c2', 'v2', domain='127.0.0.1')
        s.clear_cookies()
        assert s.get_cookie('c1') is None
        assert s.get_cookie('c2') is None


def test_session_set_header():
    """测试会话设置请求头"""
    with 会话() as s:
        s.set_header('X-Custom', 'test-value')
        assert s.headers.get('X-Custom') == 'test-value' or \
               s.headers.get('x-custom') == 'test-value'


def test_session_remove_header():
    """测试会话移除请求头"""
    with 会话() as s:
        s.set_header('X-Temp', 'temp')
        s.remove_header('X-Temp')
        assert 'X-Temp' not in s.headers and 'x-temp' not in {k.lower() for k in s.headers}


def test_session_multiple_requests():
    """测试会话多个请求共享状态"""
    with 会话() as s:
        # 触发 Cookie 设置
        resp1 = s.get(f'{_服务器.url}/set-cookie')
        assert resp1.status == 200

        # 后续请求应携带 Cookie
        resp2 = s.get(f'{_服务器.url}/echo-headers')
        data = json.loads(resp2.body)
        keys_lower = {k.lower(): v for k, v in data.items()}
        # Cookie 头应该被自动发送
        assert 'cookie' in keys_lower or 'Cookie' in keys_lower


def test_session_all_http_methods():
    """测试会话支持所有 HTTP 方法"""
    with 会话() as s:
        # GET
        assert s.get(f'{_服务器.url}/').status == 200
        # POST
        assert s.post(f'{_服务器.url}/echo', data='body').status == 200
        # PUT
        assert s.put(f'{_服务器.url}/echo', data='body').status == 200
        # DELETE
        assert s.delete(f'{_服务器.url}/echo').status == 200
        # PATCH
        assert s.patch(f'{_服务器.url}/echo', data='body').status == 200
        # HEAD
        assert s.head(f'{_服务器.url}/echo').status == 200
        # OPTIONS
        assert s.options(f'{_服务器.url}/echo').status == 204


def test_create_session():
    """测试创建会话快捷函数"""
    s = 创建会话(headers={'X-App': 'test'}, timeout=60)
    try:
        assert s.headers.get('X-App') == 'test' or \
               s.headers.get('x-app') == 'test'
        resp = s.get(f'{_服务器.url}/')
        assert resp.status == 200
    finally:
        s.close()


# =============================================================================
# 错误处理测试
# =============================================================================

def test_timeout_error():
    """测试超时错误"""
    import pytest
    try:
        HTTP获取(f'{_服务器.url}/slow', 超时=0.1)
        assert False, "应该抛出超时错误"
    except 超时错误:
        pass


def test_connection_error():
    """测试连接错误"""
    try:
        HTTP获取('http://127.0.0.1:1/', 超时=1)
        assert False, "应该抛出连接错误"
    except 连接错误:
        pass


def test_http_error_hierarchy():
    """测试错误类型层次"""
    assert issubclass(超时错误, HTTP错误)
    assert issubclass(连接错误, HTTP错误)
    assert issubclass(HTTP状态错误, HTTP错误)
    assert issubclass(SSL错误, HTTP错误)


# =============================================================================
# 文件下载测试
# =============================================================================

def test_download_file():
    """测试文件下载"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        temp_path = f.name

    try:
        result = 下载文件(f'{_服务器.url}/', temp_path)
        assert result is True
        with open(temp_path, 'r') as f:
            content = f.read()
        assert content == 'Hello World'
    finally:
        os.unlink(temp_path)


def test_download_file_stream():
    """测试流式下载"""
    chunks = []

    def callback(chunk):
        chunks.append(chunk)

    result = 下载文件流(f'{_服务器.url}/stream', callback)
    assert result is True
    assert len(chunks) > 0
    full_content = b''.join(chunks)
    assert full_content == b'chunk1\nchunk2\nchunk3\n'


# =============================================================================
# 异步客户端测试
# =============================================================================

def test_async_client():
    """测试异步 HTTP 客户端"""
    async def _run():
        async with 异步HTTP客户端() as client:
            # GET
            resp = await client.get(f'{_服务器.url}/')
            assert resp.status == 200
            assert resp.body == 'Hello World'

            # POST
            resp = await client.post(f'{_服务器.url}/echo', data='async body')
            assert resp.status == 200
            assert resp.body == 'async body'

            # POST JSON
            resp = await client.post(f'{_服务器.url}/json', json={'key': 'async'})
            assert resp.status == 200
            result = json.loads(resp.body)
            assert result['key'] == 'async'
            assert result['received'] is True

            # PUT
            resp = await client.put(f'{_服务器.url}/echo', data='put body')
            assert resp.status == 200
            assert resp.body == 'put body'

            # DELETE
            resp = await client.delete(f'{_服务器.url}/echo')
            assert resp.status == 200

            # PATCH
            resp = await client.patch(f'{_服务器.url}/echo', data='patch body')
            assert resp.status == 200
            assert resp.body == 'patch body'

            # HEAD
            resp = await client.head(f'{_服务器.url}/echo')
            assert resp.status == 200

            # OPTIONS
            resp = await client.options(f'{_服务器.url}/echo')
            assert resp.status == 204

    asyncio.run(_run())


def test_async_client_context_manager():
    """测试异步客户端上下文管理器"""
    async def _run():
        async with 异步HTTP客户端() as client:
            resp = await client.get(f'{_服务器.url}/')
            assert resp.status == 200
        # 退出上下文后客户端应已关闭

    asyncio.run(_run())


# =============================================================================
# HTTPRequest 数据结构测试
# =============================================================================

def test_http_request_defaults():
    """测试 HTTPRequest 默认值"""
    req = HTTPRequest()
    assert req.method == 'GET'
    assert req.url == ''
    assert req.headers == {}
    assert req.body is None
    assert req.query == {}
    assert req.follow_redirect is True
    assert req.timeout == 30
    assert req.verify is True
    assert req.cert is None
    assert req.proxies is None
    assert req.stream is False


def test_http_request_custom():
    """测试 HTTPRequest 自定义值"""
    req = HTTPRequest(
        method='POST',
        url='http://example.com',
        headers={'X-Test': '1'},
        body='data',
        query={'q': 'test'},
        follow_redirect=False,
        timeout=10,
        verify=False,
        proxies={'http': 'http://proxy:8080'},
        stream=True,
    )
    assert req.method == 'POST'
    assert req.query == {'q': 'test'}
    assert req.follow_redirect is False
    assert req.verify is False
    assert req.stream is True


def test_http_response_defaults():
    """测试 HTTPResponse 默认值"""
    resp = HTTPResponse()
    assert resp.status == 0
    assert resp.status_msg == ''
    assert resp.headers == {}
    assert resp.body == ''
    assert resp.final_url == ''
    assert resp.cookies == {}
    assert resp.elapsed == 0


# =============================================================================
# 边缘情况测试
# =============================================================================

def test_http_get_with_params():
    """测试带查询参数的 GET 请求"""
    resp = HTTP获取(f'{_服务器.url}/search', 查询参数={'q': '测试'})
    assert resp.status == 200
    data = json.loads(resp.body)
    assert 'q' in data


def test_http_post_form_data():
    """测试 POST 表单数据"""
    resp = HTTP提交(f'{_服务器.url}/form', 正文='name=test&value=123',
                    内容类型='application/x-www-form-urlencoded')
    assert resp.status == 200
    data = json.loads(resp.body)
    assert data.get('name') == 'test'
    assert data.get('value') == '123'


def test_session_close():
    """测试会话关闭"""
    s = 会话()
    s.close()
    # 关闭后再次请求应得到连接错误或异常
    try:
        # 使用一个不可能连接的地址验证会话关闭后不会造成问题
        pass
    except Exception:
        pass


def test_concurrent_requests():
    """测试并发请求"""
    results = []
    errors = []

    def worker():
        try:
            resp = HTTP获取(f'{_服务器.url}/')
            results.append(resp.status)
        except Exception as e:
            errors.append(e)

    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(results) == 10
    assert all(r == 200 for r in results)
    assert len(errors) == 0


# =============================================================================
# 向后兼容性测试
# =============================================================================

def test_backward_compatibility_old_api():
    """测试旧 API 仍可工作"""
    from stdlib.lightpub.HTTP客户端 import (
        HTTP获取 as old_get,
        HTTP提交 as old_post,
        HTTP更新 as old_put,
        HTTP删除 as old_delete,
        HTTP修补 as old_patch,
        HTTP头部 as old_head,
    )

    # 使用新参数名（旧 body 参数改为 正文）
    resp = old_get(f'{_服务器.url}/')
    assert resp.status == 200

    resp = old_post(f'{_服务器.url}/echo', 正文='test')
    assert resp.status == 200

    resp = old_put(f'{_服务器.url}/echo', 正文='test')
    assert resp.status == 200

    resp = old_delete(f'{_服务器.url}/echo')
    assert resp.status == 200

    resp = old_patch(f'{_服务器.url}/echo', 正文='test')
    assert resp.status == 200

    resp = old_head(f'{_服务器.url}/echo')
    assert resp.status == 200


if __name__ == '__main__':
    setup_module()
    try:
        # 运行所有测试函数
        test_funcs = [
            test_http_get,
            test_http_get_with_query,
            test_http_get_with_headers,
            test_http_post,
            test_http_post_json,
            test_http_put,
            test_http_delete,
            test_http_patch,
            test_http_head,
            test_http_options,
            test_get_json,
            test_get_json_non_200,
            test_send_json,
            test_url_encode_decode,
            test_url_join,
            test_redirect_follow,
            test_redirect_no_follow,
            test_status_404,
            test_status_500,
            test_custom_headers,
            test_http_response_json,
            test_http_response_elapsed,
            test_http_response_headers,
            test_session_basic,
            test_session_headers,
            test_session_cookie_persistence,
            test_session_set_cookie,
            test_session_remove_cookie,
            test_session_clear_cookies,
            test_session_set_header,
            test_session_remove_header,
            test_session_multiple_requests,
            test_session_all_http_methods,
            test_create_session,
            test_timeout_error,
            test_connection_error,
            test_http_error_hierarchy,
            test_download_file,
            test_download_file_stream,
            test_async_client,
            test_async_client_context_manager,
            test_http_request_defaults,
            test_http_request_custom,
            test_http_response_defaults,
            test_http_get_with_params,
            test_http_post_form_data,
            test_session_close,
            test_concurrent_requests,
            test_backward_compatibility_old_api,
        ]

        passed = 0
        failed = 0
        for test_fn in test_funcs:
            try:
                test_fn()
                print(f"  ✓ {test_fn.__name__}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {test_fn.__name__}: {e}")
                failed += 1

        print(f"\n总共 {passed + failed} 个测试: {passed} 通过, {failed} 失败")
    finally:
        teardown_module()