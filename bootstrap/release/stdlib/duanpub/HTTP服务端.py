"""
HTTP服务端 — duanpub 桥接模块

基于 Python http.server 模块封装，提供中文名 API 用于创建 HTTP 服务端。

duanpub 原始包通过 C FFI 实现 HTTP 服务器，本桥接模块用 Python http.server 替代，
提供等价的 HTTP 服务端功能。函数签名与 duanpub 包保持一致。

支持功能：
- 路由注册（GET/POST/PUT/DELETE/PATCH）
- 路径参数提取（如 /users/{id}）
- 静态文件服务
- CORS 中间件
- 访问日志中间件
- JSON/HTML/文本/文件响应
- Cookie 设置
- 重定向
"""

import http.server
import json as _json
import os
import re
import urllib.parse
import threading
import mimetypes
from datetime import datetime


# =============================================================================
# HTTP 请求/响应
# =============================================================================

class HTTP请求:
    """HTTP 请求对象"""
    def __init__(self):
        self.方法 = ""
        self.路径 = ""
        self.协议版本 = ""
        self.头信息 = {}
        self.查询参数 = {}
        self.正文 = b""
        self.客户端地址 = ""
        self.客户端端口 = 0
        self._路径参数 = {}


class HTTP响应:
    """HTTP 响应对象"""
    def __init__(self):
        self.状态码 = 200
        self.状态消息 = "OK"
        self.头信息 = {"Content-Type": "text/plain; charset=utf-8"}
        self.正文 = b""
        self._cookies = []

    def 设置头(self, 名称, 值):
        """设置响应头"""
        self.头信息[名称] = 值

    def 写文本(self, 文本, 状态码=200, 内容类型="text/plain; charset=utf-8"):
        """写入文本响应"""
        self.状态码 = 状态码
        self.状态消息 = {200: "OK", 201: "Created", 204: "No Content",
                        301: "Moved Permanently", 302: "Found",
                        304: "Not Modified", 400: "Bad Request",
                        401: "Unauthorized", 403: "Forbidden",
                        404: "Not Found", 405: "Method Not Allowed",
                        409: "Conflict", 500: "Internal Server Error",
                        502: "Bad Gateway", 503: "Service Unavailable"}.get(状态码, "Unknown")
        self.头信息["Content-Type"] = 内容类型
        if isinstance(文本, str):
            self.正文 = 文本.encode("utf-8")
        else:
            self.正文 = 文本

    def 写JSON(self, 数据, 状态码=200):
        """写入 JSON 响应"""
        try:
            文本 = _json.dumps(数据, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise Exception("序列化JSON失败: " + str(e))
        self.写文本(文本, 状态码=状态码, 内容类型="application/json; charset=utf-8")

    def 写HTML(self, html, 状态码=200):
        """写入 HTML 响应"""
        self.写文本(html, 状态码=状态码, 内容类型="text/html; charset=utf-8")

    def 写文件(self, 文件路径):
        """写入文件响应"""
        try:
            if not os.path.exists(文件路径):
                self.写文本("文件不存在", 状态码=404)
                return
            with open(文件路径, "rb") as f:
                self.正文 = f.read()
            内容类型, _ = mimetypes.guess_type(文件路径)
            if 内容类型 is None:
                内容类型 = "application/octet-stream"
            self.头信息["Content-Type"] = 内容类型
            self.状态码 = 200
            self.状态消息 = "OK"
        except IOError as e:
            self.写文本("读取文件失败: " + str(e), 状态码=500)

    def 重定向(self, 位置, 状态码=302):
        """重定向"""
        self.状态码 = 状态码
        self.状态消息 = {301: "Moved Permanently", 302: "Found", 307: "Temporary Redirect", 308: "Permanent Redirect"}.get(状态码, "Found")
        self.头信息["Location"] = 位置
        self.正文 = b""

    def 设置Cookie(self, 名称, 值, 路径="/", 过期时间=None, 安全=False, HTTPOnly=False):
        """设置 Cookie"""
        cookie = f"{名称}={值}; Path={路径}"
        if 过期时间:
            if isinstance(过期时间, datetime):
                过期时间 = 过期时间.strftime("%a, %d %b %Y %H:%M:%S GMT")
            cookie += f"; Expires={过期时间}"
        if 安全:
            cookie += "; Secure"
        if HTTPOnly:
            cookie += "; HttpOnly"
        self._cookies.append(cookie)


# =============================================================================
# 路由
# =============================================================================

class 路由:
    """单个路由定义"""
    def __init__(self, 方法="GET", 路径模式="/", 处理函数=None):
        self.方法 = 方法.upper()
        self.路径模式 = 路径模式
        self.处理函数 = 处理函数
        # 将 {参数名} 转换为命名捕获组
        self._模式 = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', 路径模式)
        # 标准化路径模式，支持可选的尾部斜杠
        if self._模式 == '/' or self._模式 == '':
            self._模式 = '/?'  # 根路径：匹配 "/" 或 ""
        else:
            self._模式 = self._模式.rstrip('/') + '/?'
        self._正则 = re.compile(f'^{self._模式}$')

    def 匹配(self, 路径):
        """尝试匹配路径，成功返回路径参数字典，失败返回 None"""
        # 标准化路径：去除尾部斜杠（根路径除外）
        if 路径 != '/' and 路径.endswith('/'):
            路径 = 路径.rstrip('/')
        m = self._正则.match(路径)
        if m:
            return m.groupdict()
        return None


class 路由表:
    """路由表，管理路由注册和匹配"""
    def __init__(self):
        self._路由列表 = []

    def 注册(self, 方法, 路径, 处理函数):
        """注册路由"""
        if not callable(处理函数):
            raise Exception("路由注册失败: 处理函数必须是可调用对象")
        self._路由列表.append(路由(方法, 路径, 处理函数))

    def GET(self, 路径, 处理函数=None):
        """
        注册 GET 路由（装饰器风格）

        支持两种用法:
        - 直接调用: 路由表.GET("/path", 处理函数)
        - 装饰器:   @路由表.GET("/path")
        """
        if 处理函数 is None:
            return lambda fn: self.注册("GET", 路径, fn) or fn
        self.注册("GET", 路径, 处理函数)
        return 处理函数

    def POST(self, 路径, 处理函数=None):
        """注册 POST 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("POST", 路径, fn) or fn
        self.注册("POST", 路径, 处理函数)
        return 处理函数

    def PUT(self, 路径, 处理函数=None):
        """注册 PUT 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("PUT", 路径, fn) or fn
        self.注册("PUT", 路径, 处理函数)
        return 处理函数

    def DELETE(self, 路径, 处理函数=None):
        """注册 DELETE 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("DELETE", 路径, fn) or fn
        self.注册("DELETE", 路径, 处理函数)
        return 处理函数

    def PATCH(self, 路径, 处理函数=None):
        """注册 PATCH 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("PATCH", 路径, fn) or fn
        self.注册("PATCH", 路径, 处理函数)
        return 处理函数

    def 匹配(self, 方法, 路径):
        """
        匹配路由，返回 (处理函数, 路径参数)

        返回:
            (处理函数, 路径参数字典) 或 (None, {})
        """
        方法 = 方法.upper()
        # 标准化路径
        if 路径 != '/' and 路径.endswith('/'):
            路径 = 路径.rstrip('/')
        for 路由 in self._路由列表:
            if 路由.方法 == 方法:
                参数 = 路由.匹配(路径)
                if 参数 is not None:
                    return 路由.处理函数, 参数
        return None, {}


# =============================================================================
# 内部：HTTP 请求处理器
# =============================================================================

class _请求处理器(http.server.BaseHTTPRequestHandler):
    """内部请求处理器，将 HTTP 请求路由到注册的处理函数"""

    # 禁用默认的日志输出（由中间件控制）
    def log_message(self, format, *args):
        pass

    def _解析请求(self):
        """将原始请求解析为 HTTP请求 对象"""
        req = HTTP请求()
        req.方法 = self.command
        req.路径 = self.path
        req.协议版本 = self.request_version
        req.头信息 = dict(self.headers)
        req.客户端地址 = self.client_address[0]
        req.客户端端口 = self.client_address[1]

        # 解析路径和查询参数
        parsed = urllib.parse.urlparse(self.path)
        req.路径 = parsed.path
        if parsed.query:
            for key, values in urllib.parse.parse_qs(parsed.query).items():
                req.查询参数[key] = values[0] if len(values) == 1 else values

        # 读取请求体
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            req.正文 = self.rfile.read(content_length)
        else:
            req.正文 = b""

        return req

    def _发送响应(self, 响应):
        """发送 HTTP响应 对象到客户端"""
        try:
            # 设置状态码
            self.send_response(响应.状态码, 响应.状态消息)

            # 设置响应头
            for 名称, 值 in 响应.头信息.items():
                self.send_header(名称, 值)

            # 设置 Cookie
            for cookie in 响应._cookies:
                self.send_header("Set-Cookie", cookie)

            self.end_headers()

            # 发送正文
            if 响应.正文:
                self.wfile.write(响应.正文)
        except Exception:
            pass

    def _处理请求(self):
        """处理单个请求：路由匹配 -> 中间件 -> 处理函数"""
        # 中间件处理前
        try:
            # 获取服务器实例
            server = self.server
            if not hasattr(server, '_中间件列表'):
                server._中间件列表 = []
            if not hasattr(server, '_路由表'):
                server._路由表 = 路由表()
            if not hasattr(server, '_静态文件目录'):
                server._静态文件目录 = {}
            if not hasattr(server, '_全局处理函数'):
                server._全局处理函数 = None
        except AttributeError:
            server._中间件列表 = []
            server._路由表 = 路由表()
            server._静态文件目录 = {}
            server._全局处理函数 = None

        # 解析请求
        req = self._解析请求()
        resp = HTTP响应()

        # 运行请求前中间件
        for 中间件 in server._中间件列表:
            if hasattr(中间件, '请求前'):
                try:
                    result = 中间件.请求前(req, resp)
                    if result is False:
                        self._发送响应(resp)
                        return
                except Exception:
                    pass

        # 路由匹配
        try:
            # 1. 检查是否匹配静态文件
            if hasattr(server, '_静态文件目录') and server._静态文件目录:
                for url_prefix, 目录 in server._静态文件目录.items():
                    if req.路径.startswith(url_prefix):
                        相对路径 = req.路径[len(url_prefix):].lstrip('/')
                        完整路径 = os.path.join(目录, 相对路径)
                        if os.path.isfile(完整路径):
                            resp.写文件(完整路径)
                            break
                else:
                    # 没有匹配到静态文件，继续路由匹配
                    self._执行路由匹配(req, resp, server)
            else:
                self._执行路由匹配(req, resp, server)
        except Exception as e:
            resp.写文本("服务器内部错误: " + str(e), 状态码=500)

        # 运行请求后中间件
        for 中间件 in server._中间件列表:
            if hasattr(中间件, '请求后'):
                try:
                    中间件.请求后(req, resp)
                except Exception:
                    pass

        self._发送响应(resp)

    def _执行路由匹配(self, req, resp, server):
        """执行路由匹配并调用处理函数"""
        # 检查是否有全局处理函数
        if server._全局处理函数:
            try:
                server._全局处理函数(req, resp)
            except Exception as e:
                resp.写文本("处理请求失败: " + str(e), 状态码=500)
            return

        # 标准路由匹配
        处理函数, 路径参数 = server._路由表.匹配(req.方法, req.路径)
        if 处理函数:
            req._路径参数 = 路径参数
            try:
                处理函数(req, resp)
            except Exception as e:
                resp.写文本("处理请求失败: " + str(e), 状态码=500)
        else:
            resp.写文本(f"未找到路由: {req.方法} {req.路径}", 状态码=404)

    def do_GET(self):
        self._处理请求()

    def do_POST(self):
        self._处理请求()

    def do_PUT(self):
        self._处理请求()

    def do_DELETE(self):
        self._处理请求()

    def do_PATCH(self):
        self._处理请求()

    def do_HEAD(self):
        self._处理请求()

    def do_OPTIONS(self):
        self._处理请求()


# =============================================================================
# 服务器
# =============================================================================

def 创建服务器(主机="0.0.0.0", 端口=8080):
    """
    创建 HTTP 服务器

    Args:
        主机: 绑定地址，默认 "0.0.0.0"（所有接口）
        端口: 监听端口，默认 8080

    Returns:
        HTTPServer 实例
    """
    try:
        server = http.server.HTTPServer((主机, 端口), _请求处理器)
        server._路由表 = 路由表()
        server._中间件列表 = []
        server._静态文件目录 = {}
        server._全局处理函数 = None
        server._运行中 = False
        return server
    except OSError as e:
        raise Exception(f"创建服务器失败(地址={主机}:{端口}): {e}")


def 添加路由(服务器, 方法, 路径, 处理函数):
    """
    添加路由

    Args:
        服务器: 由 创建服务器 返回的服务器实例
        方法: HTTP 方法（GET/POST/PUT/DELETE/PATCH）
        路径: 路径模式，支持 {参数名} 占位符
        处理函数: 处理函数，签名 fn(req, resp)
    """
    if not hasattr(服务器, '_路由表'):
        服务器._路由表 = 路由表()
    服务器._路由表.注册(方法, 路径, 处理函数)


def 添加静态文件(服务器, URL前缀, 目录路径):
    """
    添加静态文件服务

    Args:
        服务器: 由 创建服务器 返回的服务器实例
        URL前缀: URL 前缀，如 /static
        目录路径: 本地文件系统目录路径
    """
    if not os.path.isdir(目录路径):
        raise Exception(f"添加静态文件失败: 目录不存在 {目录路径}")
    if not hasattr(服务器, '_静态文件目录'):
        服务器._静态文件目录 = {}
    if not URL前缀.endswith('/'):
        URL前缀 += '/'
    服务器._静态文件目录[URL前缀] = 目录路径


def 启动服务器(服务器, 阻塞=True):
    """
    启动服务器

    Args:
        服务器: 由 创建服务器 返回的服务器实例
        阻塞: 是否阻塞当前线程，默认为 True

    Returns:
        阻塞模式下返回 None；非阻塞模式下返回线程对象
    """
    try:
        if 阻塞:
            服务器._运行中 = True
            服务器.serve_forever()
        else:
            t = threading.Thread(target=服务器.serve_forever, daemon=True)
            服务器._运行中 = True
            t.start()
            return t
    except Exception as e:
        raise Exception(f"启动服务器失败: {e}")


def 停止服务器(服务器):
    """停止服务器"""
    try:
        服务器._运行中 = False
        服务器.shutdown()
    except Exception as e:
        raise Exception(f"停止服务器失败: {e}")


# =============================================================================
# 中间件
# =============================================================================

class _CORS中间件:
    """CORS 中间件"""
    def __init__(self, 允许来源="*", 允许方法="GET,POST,PUT,DELETE,OPTIONS", 允许头="Content-Type"):
        self.允许来源 = 允许来源
        self.允许方法 = 允许方法
        self.允许头 = 允许头

    def 请求前(self, req, resp):
        """处理 CORS 预检请求和添加响应头"""
        resp.设置头("Access-Control-Allow-Origin", self.允许来源)
        resp.设置头("Access-Control-Allow-Methods", self.允许方法)
        resp.设置头("Access-Control-Allow-Headers", self.允许头)
        if req.方法 == "OPTIONS":
            resp.写文本("", 状态码=204)
            return False
        return True


class _日志中间件:
    """访问日志中间件"""
    def 请求后(self, req, resp):
        """记录访问日志"""
        try:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{req.客户端地址}:{req.客户端端口} "
                  f"{req.方法} {req.路径} "
                  f"-> {resp.状态码}")
        except Exception:
            pass


class _静态文件中间件:
    """静态文件中间件"""
    def __init__(self, URL前缀, 目录路径):
        self.URL前缀 = URL前缀
        self.目录路径 = 目录路径

    def 请求前(self, req, resp):
        """在路由匹配前检查静态文件"""
        if req.路径.startswith(self.URL前缀):
            相对路径 = req.路径[len(self.URL前缀):].lstrip('/')
            完整路径 = os.path.join(self.目录路径, 相对路径)
            if os.path.isfile(完整路径):
                try:
                    resp.写文件(完整路径)
                    return False
                except Exception:
                    resp.写文本("读取静态文件失败", 状态码=500)
                    return False
        return True


def 创建CORS中间件(允许来源="*", 允许方法="GET,POST,PUT,DELETE,OPTIONS", 允许头="Content-Type"):
    """
    创建 CORS 中间件

    Args:
        允许来源: 允许的跨域来源，默认 "*"
        允许方法: 允许的 HTTP 方法
        允许头: 允许的自定义头

    Returns:
        CORS 中间件对象
    """
    return _CORS中间件(允许来源, 允许方法, 允许头)


def 创建日志中间件():
    """
    创建访问日志中间件

    Returns:
        日志中间件对象
    """
    return _日志中间件()


def 创建静态文件中间件(URL前缀, 目录路径):
    """
    创建静态文件中间件

    Args:
        URL前缀: URL 前缀，如 /static
        目录路径: 本地文件系统目录路径

    Returns:
        静态文件中间件对象
    """
    return _静态文件中间件(URL前缀, 目录路径)


# =============================================================================
# 快捷服务器创建
# =============================================================================

def 创建Web应用(主机="0.0.0.0", 端口=8080):
    """
    创建完整的 Web 应用（含路由、中间件支持）

    返回的 Web 应用对象支持以下方法：
    - GET/POST/PUT/DELETE/PATCH(路径, 处理函数)：注册路由
    - 使用中间件(中间件)：添加中间件
    - 静态文件(URL前缀, 目录路径)：添加静态文件服务
    - 启动(阻塞=True)：启动服务器
    - 停止()：停止服务器

    Args:
        主机: 绑定地址，默认 "0.0.0.0"
        端口: 监听端口，默认 8080

    Returns:
        Web 应用对象
    """
    server = 创建服务器(主机, 端口)

    class _Web应用:
        def __init__(self, 服务器):
            self._服务器 = 服务器

        def GET(self, 路径, 处理函数=None):
            """
            注册 GET 路由（装饰器风格）

            支持两种用法:
            - 直接调用: app.GET("/path", 处理函数)
            - 装饰器:   @app.GET("/path")
            """
            if 处理函数 is None:
                return lambda fn: self._服务器._路由表.GET(路径, fn) or fn
            self._服务器._路由表.GET(路径, 处理函数)
            return 处理函数

        def POST(self, 路径, 处理函数=None):
            """注册 POST 路由"""
            if 处理函数 is None:
                return lambda fn: self._服务器._路由表.POST(路径, fn) or fn
            self._服务器._路由表.POST(路径, 处理函数)
            return 处理函数

        def PUT(self, 路径, 处理函数=None):
            """注册 PUT 路由"""
            if 处理函数 is None:
                return lambda fn: self._服务器._路由表.PUT(路径, fn) or fn
            self._服务器._路由表.PUT(路径, 处理函数)
            return 处理函数

        def DELETE(self, 路径, 处理函数=None):
            """注册 DELETE 路由"""
            if 处理函数 is None:
                return lambda fn: self._服务器._路由表.DELETE(路径, fn) or fn
            self._服务器._路由表.DELETE(路径, 处理函数)
            return 处理函数

        def PATCH(self, 路径, 处理函数=None):
            """注册 PATCH 路由"""
            if 处理函数 is None:
                return lambda fn: self._服务器._路由表.PATCH(路径, fn) or fn
            self._服务器._路由表.PATCH(路径, 处理函数)
            return 处理函数

        def 使用中间件(self, 中间件):
            self._服务器._中间件列表.append(中间件)

        def 静态文件(self, URL前缀, 目录路径):
            添加静态文件(self._服务器, URL前缀, 目录路径)

        def 启动(self, 阻塞=True):
            return 启动服务器(self._服务器, 阻塞=阻塞)

        def 停止(self):
            停止服务器(self._服务器)

        @property
        def 地址(self):
            return self._服务器.server_address

    return _Web应用(server)


def 运行简单服务器(处理函数, 主机="0.0.0.0", 端口=8080):
    """
    运行一个简单的 HTTP 服务器，所有请求由同一函数处理

    处理函数签名: fn(req, resp)
    其中 req 是 HTTP请求 对象，resp 是 HTTP响应 对象

    Args:
        处理函数: 请求处理函数
        主机: 绑定地址，默认 "0.0.0.0"
        端口: 监听端口，默认 8080
    """
    try:
        server = http.server.HTTPServer((主机, 端口), _请求处理器)
        server._路由表 = 路由表()
        server._中间件列表 = []
        server._静态文件目录 = {}
        server._全局处理函数 = 处理函数
        server._运行中 = True
        print(f"服务器运行在 http://{主机}:{端口}")
        server.serve_forever()
    except OSError as e:
        raise Exception(f"启动简单服务器失败(地址={主机}:{端口}): {e}")
    except KeyboardInterrupt:
        server.shutdown()


def 创建JSONAPI服务器(路由字典, 主机="0.0.0.0", 端口=8080):
    """
    创建 JSON API 服务器

    路由字典格式:
    {
        "GET /users": 处理函数,
        "POST /users": 处理函数,
        "GET /users/{id}": 处理函数,
        "PUT /users/{id}": 处理函数,
        "DELETE /users/{id}": 处理函数,
    }

    处理函数签名: fn(req, resp)
    其中 req 是 HTTP请求 对象，resp 是 HTTP响应 对象

    返回的服务器默认开启 CORS 和日志中间件

    Args:
        路由字典: 路由配置字典
        主机: 绑定地址，默认 "0.0.0.0"
        端口: 监听端口，默认 8080

    Returns:
        Web 应用对象
    """
    app = 创建Web应用(主机, 端口)
    app.使用中间件(创建CORS中间件())
    app.使用中间件(创建日志中间件())

    for 路由描述, 处理函数 in 路由字典.items():
        部分 = 路由描述.strip().split(None, 1)
        if len(部分) != 2:
            raise Exception(f"路由描述格式错误: '{路由描述}'，应为 'GET /path'")
        方法, 路径 = 部分
        方法 = 方法.upper()
        if 方法 not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            raise Exception(f"不支持的 HTTP 方法: '{方法}'")
        app._服务器._路由表.注册(方法, 路径, 处理函数)

    return app