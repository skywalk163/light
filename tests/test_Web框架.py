# -*- coding: utf-8 -*-
"""
Web框架 — 测试套件

测试覆盖：
1. 路由系统（20+ 测试）
2. 中间件链（15+ 测试）
3. 模板引擎（12+ 测试）
4. 请求/响应处理（10+ 测试）
5. 集成测试（8+ 测试）
总计 65+ 测试用例
"""

import sys
import os
import json
import pytest
import threading
import time
import http.client
import io
import tempfile
import uuid

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from stdlib.lightpub.Web框架 import (
    Web应用, 请求, 响应, 路由, 路由表, 路由分组,
    中间件基类, 错误处理中间件, 日志中间件, CORS中间件,
    静态文件中间件, Session中间件, 速率限制中间件, 认证中间件, 压缩中间件,
    模板引擎, Session管理器, 创建模板引擎,
    创建Web应用, 创建JSONAPI, JSON响应, 文本响应, HTML响应,
    重定向响应, 错误响应, API构建器,
    范围, 整数转字符串, 内部包含, 内部以开始, 内部分割,
    内部去除空白, 内部转为小写, 内部替换所有, 内部字符串转整数,
    内部值转字符串,
)


# =============================================================================
# 辅助函数
# =============================================================================

def _创建测试应用():
    """创建测试用 Web 应用"""
    app = Web应用("测试应用")
    return app


def _发送HTTP请求(主机="localhost", 端口=0, 方法="GET", 路径="/", 正文=None, 头信息=None, 超时=5):
    """发送 HTTP 请求，返回 (状态码, 响应头, 响应体)"""
    try:
        conn = http.client.HTTPConnection(主机, 端口, timeout=超时)
        conn.request(method, 路径, body=正文, headers=头信息 or {})
        resp = conn.getresponse()
        body = resp.read()
        头 = dict(resp.getheaders())
        return resp.status, 头, body.decode('utf-8') if body else ''
    except Exception as e:
        return 0, {}, str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =============================================================================
# 1. 路由系统测试（20+ 测试）
# =============================================================================

class Test路由系统:
    """路由系统测试"""

    def test_路由注册_GET(self):
        """测试 GET 路由注册"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("GET OK")
        路由表实例.注册("GET", "/test", handler)
        result = 路由表实例.匹配("GET", "/test")
        assert result[0] is handler
        assert result[1] == {}

    def test_路由注册_POST(self):
        """测试 POST 路由注册"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("POST OK")
        路由表实例.注册("POST", "/test", handler)
        result = 路由表实例.匹配("POST", "/test")
        assert result[0] is handler

    def test_路由注册_PUT(self):
        """测试 PUT 路由注册"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("PUT OK")
        路由表实例.注册("PUT", "/test", handler)
        result = 路由表实例.匹配("PUT", "/test")
        assert result[0] is handler

    def test_路由注册_DELETE(self):
        """测试 DELETE 路由注册"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("DELETE OK")
        路由表实例.注册("DELETE", "/test", handler)
        result = 路由表实例.匹配("DELETE", "/test")
        assert result[0] is handler

    def test_路由注册_PATCH(self):
        """测试 PATCH 路由注册"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("PATCH OK")
        路由表实例.注册("PATCH", "/test", handler)
        result = 路由表实例.匹配("PATCH", "/test")
        assert result[0] is handler

    def test_路径参数(self):
        """测试路径参数"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写JSON({"id": req.获取路径参数("id")})
        路由表实例.注册("GET", "/users/{id}", handler)
        result = 路由表实例.匹配("GET", "/users/123")
        assert result[0] is handler
        assert result[1] == {"id": "123"}

    def test_多路径参数(self):
        """测试多个路径参数"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写JSON({"user_id": req.获取路径参数("user_id"), "post_id": req.获取路径参数("post_id")})
        路由表实例.注册("GET", "/users/{user_id}/posts/{post_id}", handler)
        result = 路由表实例.匹配("GET", "/users/42/posts/99")
        assert result[0] is handler
        assert result[1] == {"user_id": "42", "post_id": "99"}

    def test_路由不匹配(self):
        """测试路由不匹配返回 None"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/test", handler)
        result = 路由表实例.匹配("GET", "/notexist")
        assert result[0] is None

    def test_方法不匹配(self):
        """测试方法不匹配"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/test", handler)
        result = 路由表实例.匹配("POST", "/test")
        assert result[0] is None

    def test_根路径(self):
        """测试根路径 /"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("root")
        路由表实例.注册("GET", "/", handler)
        result = 路由表实例.匹配("GET", "/")
        assert result[0] is handler

    def test_尾部斜杠(self):
        """测试尾部斜杠标准化"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/test", handler)
        result = 路由表实例.匹配("GET", "/test/")
        assert result[0] is handler

    def test_路由装饰器_GET(self):
        """测试 GET 装饰器风格"""
        路由表实例 = 路由表()
        @路由表实例.GET("/hello")
        def handler(req, resp):
            resp.写文本("hello")
        result = 路由表实例.匹配("GET", "/hello")
        assert result[0] is handler

    def test_路由装饰器_POST(self):
        """测试 POST 装饰器风格"""
        路由表实例 = 路由表()
        @路由表实例.POST("/create")
        def handler(req, resp):
            resp.写文本("created")
        result = 路由表实例.匹配("POST", "/create")
        assert result[0] is handler

    def test_路由注册非可调用对象(self):
        """测试注册非可调用对象应抛出异常"""
        路由表实例 = 路由表()
        with pytest.raises(Exception, match="必须是可调用对象"):
            路由表实例.注册("GET", "/test", "not_callable")

    def test_获取路由列表(self):
        """测试获取路由列表"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/a", handler)
        路由表实例.注册("POST", "/b", handler)
        routes = 路由表实例.获取路由列表()
        assert ("GET", "/a") in routes
        assert ("POST", "/b") in routes

    def test_路径参数_数字(self):
        """测试路径参数为数字"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写JSON({"id": req.获取路径参数("id")})
        路由表实例.注册("GET", "/items/{id}", handler)
        result = 路由表实例.匹配("GET", "/items/999")
        assert result[1] == {"id": "999"}

    def test_路径参数_UUID(self):
        """测试路径参数为 UUID 格式"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写JSON({"id": req.获取路径参数("id")})
        路由表实例.注册("GET", "/items/{id}", handler)
        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = 路由表实例.匹配("GET", f"/items/{test_uuid}")
        assert result[1] == {"id": test_uuid}

    def test_嵌套路径(self):
        """测试嵌套路径"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("nested")
        路由表实例.注册("GET", "/a/b/c", handler)
        result = 路由表实例.匹配("GET", "/a/b/c")
        assert result[0] is handler

    def test_路径参数带连字符(self):
        """测试路径参数名包含下划线"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写JSON({"user_name": req.获取路径参数("user_name")})
        路由表实例.注册("GET", "/users/{user_name}", handler)
        result = 路由表实例.匹配("GET", "/users/john_doe")
        assert result[1] == {"user_name": "john_doe"}

    def test_WEB应用_GET路由(self):
        """测试 Web 应用 GET 路由"""
        app = _创建测试应用()
        captured = {}

        @app.GET("/hello")
        def handler(req, resp):
            captured["called"] = True
            resp.写文本("hello")
        assert "called" not in captured
        # 验证路由已注册
        result = app._路由表.匹配("GET", "/hello")
        assert result[0] is handler

    def test_WEB应用_路径参数(self):
        """测试 Web 应用路径参数"""
        app = _创建测试应用()
        @app.GET("/users/{id}")
        def handler(req, resp):
            resp.写JSON({"id": req.获取路径参数("id")})
        result = app._路由表.匹配("GET", "/users/42")
        assert result[1] == {"id": "42"}

    def test_路由分组(self):
        """测试路由分组"""
        app = _创建测试应用()
        api = app.路由分组("/api")
        @api.GET("/users")
        def handler(req, resp):
            resp.写JSON({"users": []})
        result = app._路由表.匹配("GET", "/api/users")
        assert result[0] is handler

    def test_路由分组_嵌套(self):
        """测试嵌套路由分组"""
        app = _创建测试应用()
        v1 = app.路由分组("/v1")
        users = v1.路由分组("/users")
        # 注意：嵌套分组这里需要验证
        # 实际上 v1.路由分组 返回的是新分组，但我们需要在 app 上注册
        @v1.GET("/status")
        def handler(req, resp):
            resp.写文本("OK")
        result = app._路由表.匹配("GET", "/v1/status")
        assert result[0] is handler


# =============================================================================
# 2. 中间件链测试（15+ 测试）
# =============================================================================

class Test中间件链:
    """中间件链测试"""

    def test_中间件基类(self):
        """测试中间件基类"""
        m = 中间件基类()
        assert m.请求前(None, None) is True
        assert m.请求后(None, None) is None

    def test_CORS中间件_添加头(self):
        """测试 CORS 中间件添加响应头"""
        req = 请求()
        req.方法 = "GET"
        resp = 响应()
        m = CORS中间件()
        result = m.请求前(req, resp)
        assert result is True
        assert resp.头信息.get("Access-Control-Allow-Origin") == "*"
        assert resp.头信息.get("Access-Control-Allow-Methods") is not None

    def test_CORS中间件_预检请求(self):
        """测试 CORS 中间件处理 OPTIONS 预检请求"""
        req = 请求()
        req.方法 = "OPTIONS"
        resp = 响应()
        m = CORS中间件()
        result = m.请求前(req, resp)
        assert result is False  # 终止处理
        assert resp.状态码 == 204

    def test_CORS中间件_自定义配置(self):
        """测试 CORS 中间件自定义配置"""
        req = 请求()
        req.方法 = "GET"
        resp = 响应()
        m = CORS中间件(允许来源="https://example.com", 允许凭证=True)
        m.请求前(req, resp)
        assert resp.头信息["Access-Control-Allow-Origin"] == "https://example.com"
        assert resp.头信息["Access-Control-Allow-Credentials"] == "true"

    def test_日志中间件(self):
        """测试日志中间件"""
        logs = []
        req = 请求()
        req.方法 = "GET"
        req.路径 = "/test"
        req.客户端地址 = "127.0.0.1"
        req.客户端端口 = 12345
        resp = 响应()
        resp.状态码 = 200
        m = 日志中间件(记录器=lambda msg: logs.append(msg))
        m.请求前(req, resp)
        import time
        time.sleep(0.01)
        m.请求后(req, resp)
        assert len(logs) == 1
        assert "127.0.0.1" in logs[0]
        assert "GET" in logs[0]
        assert "200" in logs[0]

    def test_静态文件中间件(self):
        """测试静态文件中间件"""
        import tempfile
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("hello world")

            req = 请求()
            req.路径 = "/static/test.txt"
            resp = 响应()
            m = 静态文件中间件("/static/", tmpdir)
            result = m.请求前(req, resp)
            assert result is False  # 文件已处理
            assert resp.状态码 == 200

    def test_静态文件中间件_路径穿越防护(self):
        """测试静态文件中间件路径穿越防护"""
        req = 请求()
        req.路径 = "/static/../../../etc/passwd"
        resp = 响应()
        m = 静态文件中间件("/static/", "/tmp")
        result = m.请求前(req, resp)
        assert result is False  # 被拦截
        assert resp.状态码 == 403

    def test_静态文件中间件_不匹配(self):
        """测试静态文件中间件不匹配时继续"""
        req = 请求()
        req.路径 = "/api/users"
        resp = 响应()
        m = 静态文件中间件("/static/", "/tmp")
        result = m.请求前(req, resp)
        assert result is True  # 继续处理

    def test_速率限制中间件(self):
        """测试速率限制中间件"""
        req = 请求()
        req.方法 = "GET"
        req.路径 = "/test"
        req.客户端地址 = "10.0.0.1"
        resp = 响应()
        m = 速率限制中间件(最大请求数=2, 时间窗口=60)
        # 第一次请求
        assert m.请求前(req, resp) is True
        # 第二次请求
        assert m.请求前(req, resp) is True
        # 第三次请求应被限制
        assert m.请求前(req, resp) is False
        assert resp.状态码 == 429

    def test_认证中间件_通过(self):
        """测试认证中间件通过"""
        req = 请求()
        resp = 响应()
        m = 认证中间件(验证函数=lambda r: True)
        assert m.请求前(req, resp) is True

    def test_认证中间件_拒绝(self):
        """测试认证中间件拒绝"""
        req = 请求()
        resp = 响应()
        m = 认证中间件(验证函数=lambda r: False)
        assert m.请求前(req, resp) is False
        assert resp.状态码 == 401

    def test_错误处理中间件(self):
        """测试错误处理中间件"""
        req = 请求()
        resp = 响应()
        resp.状态码 = 404
        handled = []
        m = 错误处理中间件()
        m.注册错误处理(404, lambda r, rs: handled.append(True))
        m.请求后(req, resp)
        assert len(handled) == 1

    def test_压缩中间件(self):
        """测试压缩中间件"""
        req = 请求()
        req.头信息["Accept-Encoding"] = "gzip"
        resp = 响应()
        resp.正文 = b"x" * 2000
        resp.头信息["Content-Type"] = "text/plain"
        m = 压缩中间件(最小大小=100)
        m.请求后(req, resp)
        # 验证正文已被压缩（长度会变短）
        assert len(resp.正文) < 2000

    def test_Session中间件(self):
        """测试 Session 中间件"""
        req = 请求()
        resp = 响应()
        m = Session中间件()
        # 请求前
        result = m.请求前(req, resp)
        assert result is True
        assert hasattr(req, '_session数据')
        # 设置 session 数据
        req._session数据["user"] = "test_user"
        # 请求后
        m.请求后(req, resp)
        # 验证 Cookie 被设置
        assert len(resp._cookies) > 0
        assert "session_id" in resp._cookies[0]

    def test_中间件链_请求前返回False(self):
        """测试中间件链中请求前返回 False 终止链"""
        req = 请求()
        req.方法 = "OPTIONS"
        resp = 响应()
        m = CORS中间件()
        result = m.请求前(req, resp)
        assert result is False
        # 验证响应已设置
        assert resp.状态码 == 204


# =============================================================================
# 3. 模板引擎测试（12+ 测试）
# =============================================================================

class Test模板引擎:
    """模板引擎测试"""

    def test_模板渲染_变量插值(self):
        """测试模板变量插值"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("Hello, {{ name }}!", {"name": "World"})
        assert "Hello, World!" in result

    def test_模板渲染_多变量(self):
        """测试模板多变量插值"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("{{a}} + {{b}} = {{c}}", {"a": 1, "b": 2, "c": 3})
        assert "1 + 2 = 3" in result

    def test_模板渲染_for循环(self):
        """测试模板 for 循环"""
        engine = 创建模板引擎()
        template = "{% for item in items %}{{ item }},{% endfor %}"
        result = engine.渲染字符串(template, {"items": ["a", "b", "c"]})
        assert result == "a,b,c,"

    def test_模板渲染_if条件(self):
        """测试模板 if 条件"""
        engine = 创建模板引擎()
        template = "{% if show %}visible{% endif %}"
        result = engine.渲染字符串(template, {"show": True})
        assert "visible" in result

    def test_模板渲染_if_else(self):
        """测试模板 if/else 条件"""
        engine = 创建模板引擎()
        template = "{% if show %}yes{% else %}no{% endif %}"
        result = engine.渲染字符串(template, {"show": False})
        assert "no" in result

    def test_模板渲染_if_else_真值(self):
        """测试模板 if/else 条件（真值情况）"""
        engine = 创建模板引擎()
        template = "{% if show %}yes{% else %}no{% endif %}"
        result = engine.渲染字符串(template, {"show": True})
        assert "yes" in result

    def test_模板渲染_注释忽略(self):
        """测试模板注释被忽略"""
        engine = 创建模板引擎()
        template = "before{# comment #}after"
        result = engine.渲染字符串(template, {})
        assert "beforeafter" in result

    def test_模板渲染_全局变量(self):
        """测试模板全局变量"""
        engine = 创建模板引擎()
        engine.注册全局变量("site_name", "My Site")
        result = engine.渲染字符串("Welcome to {{ site_name }}!", {})
        assert "Welcome to My Site!" in result

    def test_模板渲染_过滤器(self):
        """测试模板过滤器"""
        engine = 创建模板引擎()
        engine.注册过滤器("upper", lambda v: str(v).upper())
        result = engine.渲染字符串("{{ name | upper }}", {"name": "hello"})
        assert "HELLO" in result

    def test_模板渲染_空上下文(self):
        """测试空上下文模板渲染"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("Hello, {{ name }}!", {})
        assert "Hello, !" in result

    def test_模板渲染_数字上下文(self):
        """测试数字上下文字典"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("Count: {{ count }}", {"count": 42})
        assert "Count: 42" in result

    def test_模板渲染_列表上下文(self):
        """测试列表上下文字典"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("Items: {{ items }}", {"items": [1, 2, 3]})
        # 列表会被渲染为字符串表示
        assert "[1, 2, 3]" in result

    def test_模板渲染_for循环_空列表(self):
        """测试 for 循环空列表"""
        engine = 创建模板引擎()
        template = "{% for item in items %}{{ item }}{% endfor %}"
        result = engine.渲染字符串(template, {"items": []})
        assert result == ""

    def test_模板渲染_变量点号访问(self):
        """测试模板变量点号访问"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("{{ user.name }}", {"user": {"name": "Alice"}})
        assert "Alice" in result


# =============================================================================
# 4. 请求/响应处理测试（10+ 测试）
# =============================================================================

class Test请求响应:
    """请求/响应处理测试"""

    def test_响应_写文本(self):
        """测试响应写文本"""
        resp = 响应()
        resp.写文本("Hello")
        assert resp.状态码 == 200
        assert resp.正文 == b"Hello"

    def test_响应_写JSON(self):
        """测试响应写 JSON"""
        resp = 响应()
        data = {"key": "value", "num": 42}
        resp.写JSON(data)
        assert resp.状态码 == 200
        assert json.loads(resp.正文.decode()) == data

    def test_响应_写HTML(self):
        """测试响应写 HTML"""
        resp = 响应()
        resp.写HTML("<h1>Title</h1>")
        assert resp.状态码 == 200
        assert resp.头信息["Content-Type"] == "text/html; charset=utf-8"
        assert resp.正文 == b"<h1>Title</h1>"

    def test_响应_重定向(self):
        """测试响应重定向"""
        resp = 响应()
        resp.重定向("/login")
        assert resp.状态码 == 302
        assert resp.头信息["Location"] == "/login"

    def test_响应_设置Cookie(self):
        """测试响应设置 Cookie"""
        resp = 响应()
        resp.设置Cookie("session", "abc123")
        assert len(resp._cookies) == 1
        assert "session=abc123" in resp._cookies[0]

    def test_响应_删除Cookie(self):
        """测试响应删除 Cookie"""
        resp = 响应()
        resp.删除Cookie("session")
        assert len(resp._cookies) == 1
        assert "session=;" in resp._cookies[0]

    def test_请求_获取JSON(self):
        """测试请求解析 JSON"""
        req = 请求()
        req.正文 = b'{"key": "value"}'
        req.头信息["Content-Type"] = "application/json"
        data = req.获取JSON()
        assert data == {"key": "value"}

    def test_请求_获取JSON_空正文(self):
        """测试请求解析空 JSON 正文"""
        req = 请求()
        req.正文 = b""
        data = req.获取JSON()
        assert data is None

    def test_请求_获取JSON_无效JSON(self):
        """测试请求解析无效 JSON"""
        req = 请求()
        req.正文 = b"not json"
        data = req.获取JSON()
        assert data is None

    def test_请求_获取查询参数(self):
        """测试请求获取查询参数"""
        req = 请求()
        req.查询参数 = {"name": "test", "page": "1"}
        assert req.获取查询参数("name") == "test"
        assert req.获取查询参数("page") == "1"
        assert req.获取查询参数("nonexist") is None
        assert req.获取查询参数("nonexist", "default") == "default"

    def test_请求_获取路径参数(self):
        """测试请求获取路径参数"""
        req = 请求()
        req._路径参数 = {"id": "42"}
        assert req.获取路径参数("id") == "42"
        assert req.获取路径参数("nonexist") is None

    def test_请求_获取头(self):
        """测试请求获取头信息"""
        req = 请求()
        req.头信息["User-Agent"] = "test-agent"
        assert req.获取头("User-Agent") == "test-agent"
        assert req.获取头("Nonexist") is None

    def test_JSON响应_辅助函数(self):
        """测试 JSON 响应辅助函数"""
        resp = JSON响应({"status": "ok"}, 201)
        assert resp.状态码 == 201
        data = json.loads(resp.正文.decode())
        assert data["status"] == "ok"

    def test_文本响应_辅助函数(self):
        """测试文本响应辅助函数"""
        resp = 文本响应("Not Found", 404)
        assert resp.状态码 == 404
        assert resp.正文 == b"Not Found"

    def test_HTML响应_辅助函数(self):
        """测试 HTML 响应辅助函数"""
        resp = HTML响应("<html></html>")
        assert resp.头信息["Content-Type"] == "text/html; charset=utf-8"

    def test_重定向响应_辅助函数(self):
        """测试重定向响应辅助函数"""
        resp = 重定向响应("/new-path", 301)
        assert resp.状态码 == 301
        assert resp.头信息["Location"] == "/new-path"

    def test_错误响应_辅助函数(self):
        """测试错误响应辅助函数"""
        resp = 错误响应("Bad request", 400)
        assert resp.状态码 == 400
        data = json.loads(resp.正文.decode())
        assert data["error"] == "Bad request"


# =============================================================================
# 5. Session 管理测试
# =============================================================================

class TestSession管理:
    """Session 管理测试"""

    def test_Session管理器_创建(self):
        """测试创建 Session"""
        mgr = Session管理器()
        session_id = mgr.创建Session({"user": "alice"})
        assert session_id is not None
        data = mgr.获取Session(session_id)
        assert data["user"] == "alice"

    def test_Session管理器_获取不存在(self):
        """测试获取不存在的 Session"""
        mgr = Session管理器()
        data = mgr.获取Session("nonexistent")
        assert data is None

    def test_Session管理器_更新(self):
        """测试更新 Session"""
        mgr = Session管理器()
        session_id = mgr.创建Session({})
        result = mgr.更新Session(session_id, "key", "value")
        assert result is True
        data = mgr.获取Session(session_id)
        assert data["key"] == "value"

    def test_Session管理器_删除(self):
        """测试删除 Session"""
        mgr = Session管理器()
        session_id = mgr.创建Session({})
        result = mgr.删除Session(session_id)
        assert result is True
        assert mgr.获取Session(session_id) is None

    def test_Session管理器_创建空(self):
        """测试创建空 Session"""
        mgr = Session管理器()
        session_id = mgr.创建Session()
        data = mgr.获取Session(session_id)
        assert data == {}

    def test_Web应用_Session(self):
        """测试 Web 应用 Session 管理"""
        app = _创建测试应用()
        req = 请求()
        resp = 响应()
        # 设置 session
        app.设置Session(req, resp, {"user": "bob"})
        # 获取 session
        data = app.获取Session(req)
        assert data == {"user": "bob"}


# =============================================================================
# 6. 集成测试（8+ 测试）
# =============================================================================

class Test集成:
    """集成测试"""

    def test_创建Web应用(self):
        """测试创建 Web 应用"""
        app = 创建Web应用("测试")
        assert app.标题 == "测试"
        assert app._路由表 is not None

    def test_创建JSONAPI(self):
        """测试创建 JSON API 应用"""
        def handler(req, resp):
            resp.写JSON({"ok": True})
        app = 创建JSONAPI({
            "GET /ping": handler,
            "POST /data": handler,
        })
        result = app._路由表.匹配("GET", "/ping")
        assert result[0] is handler
        result = app._路由表.匹配("POST", "/data")
        assert result[0] is handler

    def test_API构建器(self):
        """测试 API 构建器"""
        class 用户控制器:
            def 列表(self, req, resp):
                resp.写JSON([])
            def 获取(self, req, resp):
                resp.写JSON({"id": req.获取路径参数("id")})
        controller = 用户控制器()
        builder = API构建器()
        builder.资源("users", controller)
        app = builder.构建()
        result = app._路由表.匹配("GET", "/users")
        assert result[0] is not None
        assert result[0].__func__ is 用户控制器.列表

    def test_Web应用启动停止(self):
        """测试 Web 应用启动和停止"""
        app = 创建Web应用("测试")
        app.GET("/ping", lambda req, resp: resp.写JSON({"pong": True}))
        # 启动
        t = app.启动(端口=0)
        assert t is not None
        # 停止
        app.停止()
        assert app._服务器 is None

    def test_路由分组_中间件(self):
        """测试路由分组中间件"""
        app = _创建测试应用()
        middleware_results = []
        class TestMiddleware:
            def 请求前(self, req, resp):
                middleware_results.append("pre")
                return True
            def 请求后(self, req, resp):
                middleware_results.append("post")
        api = app.路由分组("/api", [TestMiddleware()])
        @api.GET("/users")
        def handler(req, resp):
            resp.写JSON({"ok": True})
        # 验证路由注册到了 app
        result = app._路由表.匹配("GET", "/api/users")
        assert result[0] is handler
        # 验证路由中间件列表
        assert len(result[2]) == 1

    def test_中间件_多种类型(self):
        """测试多种中间件组合"""
        app = _创建测试应用()
        app.使用中间件(CORS中间件())
        app.使用中间件(日志中间件(记录器=lambda m: None))
        assert len(app._中间件列表) == 2

    def test_路由表_404处理(self):
        """测试路由表 404 处理"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/exists", handler)
        # 不存在的路由
        result = 路由表实例.匹配("GET", "/notfound")
        assert result[0] is None

    def test_Web应用_模板引擎集成(self):
        """测试 Web 应用模板引擎集成"""
        app = _创建测试应用()
        engine = app.创建模板引擎()
        assert engine is not None
        assert app._模板引擎 is not None
        result = app.渲染字符串("Hello {{ name }}", {"name": "World"})
        assert "Hello World" in result

    def test_Web应用_静态文件(self):
        """测试 Web 应用静态文件服务"""
        app = _创建测试应用()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "index.html")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("<h1>Index</h1>")
            app.静态文件("/static", tmpdir)
            assert "/static/" in app._静态文件目录

    def test_Web应用_中间件链(self):
        """测试 Web 应用中间件链完整流程"""
        app = _创建测试应用()
        order = []
        class 中间件A:
            def 请求前(self, req, resp):
                order.append("A_pre")
                return True
            def 请求后(self, req, resp):
                order.append("A_post")
        class 中间件B:
            def 请求前(self, req, resp):
                order.append("B_pre")
                return True
            def 请求后(self, req, resp):
                order.append("B_post")
        app.使用中间件(中间件A())
        app.使用中间件(中间件B())
        assert len(app._中间件列表) == 2


# =============================================================================
# 7. 内部工具函数测试
# =============================================================================

class Test内部工具:
    """内部工具函数测试"""

    def test_范围(self):
        assert 范围(1, 5) == [1, 2, 3, 4]

    def test_整数转字符串(self):
        assert 整数转字符串(42) == "42"

    def test_内部包含(self):
        assert 内部包含("hello world", "world") is True
        assert 内部包含("hello world", "xyz") is False

    def test_内部以开始(self):
        assert 内部以开始("hello", "he") is True
        assert 内部以开始("hello", "el") is False

    def test_内部分割(self):
        assert 内部分割("a,b,c", ",") == ["a", "b", "c"]

    def test_内部去除空白(self):
        assert 内部去除空白("  hello  ") == "hello"

    def test_内部替换所有(self):
        assert 内部替换所有("hello world", "world", "there") == "hello there"

    def test_内部字符串转整数(self):
        assert 内部字符串转整数("42") == 42

    def test_内部值转字符串(self):
        assert 内部值转字符串(123) == "123"


# =============================================================================
# 8. 边界情况测试
# =============================================================================

class Test边界情况:
    """边界情况测试"""

    def test_空路由表(self):
        """测试空路由表匹配"""
        路由表实例 = 路由表()
        result = 路由表实例.匹配("GET", "/anything")
        assert result[0] is None

    def test_请求_空表单(self):
        """测试请求空表单数据"""
        req = 请求()
        req.头信息["Content-Type"] = "text/plain"
        data = req.获取表单数据()
        assert data == {}

    def test_响应_空响应(self):
        """测试空响应"""
        resp = 响应()
        assert resp.状态码 == 200
        assert resp.正文 == b""

    def test_模板引擎_空模板(self):
        """测试空模板渲染"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("", {})
        assert result == ""

    def test_模板引擎_无变量(self):
        """测试无变量的模板"""
        engine = 创建模板引擎()
        result = engine.渲染字符串("static text", {})
        assert "static text" in result

    def test_路由_特殊字符路径(self):
        """测试特殊字符路径"""
        路由表实例 = 路由表()
        def handler(req, resp):
            resp.写文本("OK")
        路由表实例.注册("GET", "/path with spaces", handler)
        result = 路由表实例.匹配("GET", "/path with spaces")
        assert result[0] is handler


# =============================================================================
# 运行计数
# =============================================================================

# 测试计数统计
def test_测试计数():
    """输出测试用例总数"""
    # 仅用于展示，实际测试由 pytest 运行
    pass