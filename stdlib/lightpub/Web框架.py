"""
Web框架 — duanpub 桥接模块

基于 Python http.server / json / os 等库封装，构建在 HTTP服务端 之上，
提供高级 Web 框架功能：路由系统、中间件链、模板引擎集成、请求/响应处理、
Cookie/Session 管理、文件上传、静态文件服务。

duanpub 原始包通过 C FFI 实现 Web 框架，
本桥接模块用 Python 标准库替代，提供等价的 Web 框架功能。
函数签名与 duanpub 包保持一致。
"""

import json as _json
import os as _os
import re as _re
import urllib.parse as _urlparse
import mimetypes as _mimetypes
import uuid as _uuid
import time as _time
import threading as _threading
import http.server as _http_server
from datetime import datetime as _datetime
from collections import OrderedDict as _OrderedDict

# 导入 HTTP服务端 模块作为基础
from . import HTTP服务端 as _http


# =============================================================================
# 内部工具函数
# =============================================================================

def 范围(开始, 结束):
    """生成范围列表"""
    return list(range(开始, 结束))


def 整数转字符串(值):
    """整数转字符串"""
    return str(值)


def 内部包含(文本, 子串):
    """检查是否包含子串"""
    return 子串 in 文本


def 内部以开始(文本, 前缀):
    """检查是否以指定前缀开始"""
    return 文本.startswith(前缀)


def 内部分割(文本, 分隔符):
    """分割字符串"""
    return 文本.split(分隔符)


def 内部去除空白(文本):
    """去除首尾空白"""
    return 文本.strip()


def 内部转为小写(文本):
    """转为小写"""
    return 文本.lower()


def 内部转为大写(文本):
    """转为大写"""
    return 文本.upper()


def 内部查找字符(文本, 字符):
    """查找字符位置"""
    return 文本.find(字符)


def 内部替换所有(文本, 旧, 新):
    """替换所有"""
    return 文本.replace(旧, 新)


def 内部字符串转整数(字符串):
    """字符串转整数"""
    return int(字符串)


def 内部值转字符串(值):
    """值转字符串"""
    return str(值)


# =============================================================================
# 扩展的 HTTP 请求/响应
# =============================================================================

class 请求:
    """Web 框架请求对象，扩展自 HTTP服务端.HTTP请求"""
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
        self._JSON正文 = None
        self._表单数据 = None
        self._cookies = {}

    def 获取路径参数(self, 名称, 默认=None):
        """获取路径参数"""
        return self._路径参数.get(名称, 默认)

    def 获取查询参数(self, 名称, 默认=None):
        """获取查询参数"""
        return self.查询参数.get(名称, 默认)

    def 获取JSON(self):
        """解析请求体为 JSON"""
        if self._JSON正文 is not None:
            return self._JSON正文
        if not self.正文:
            return None
        try:
            self._JSON正文 = _json.loads(self.正文.decode('utf-8'))
            return self._JSON正文
        except (ValueError, UnicodeDecodeError):
            return None

    def 获取表单数据(self):
        """解析表单数据"""
        if self._表单数据 is not None:
            return self._表单数据
        content_type = self.头信息.get('Content-Type', '')
        if 'application/x-www-form-urlencoded' in content_type:
            try:
                body = self.正文.decode('utf-8') if isinstance(self.正文, bytes) else self.正文
                parsed = _urlparse.parse_qs(body)
                self._表单数据 = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            except Exception:
                self._表单数据 = {}
        else:
            self._表单数据 = {}
        return self._表单数据

    def 获取Cookie(self, 名称, 默认=None):
        """获取 Cookie 值"""
        return self._cookies.get(名称, 默认)

    def 获取头(self, 名称, 默认=None):
        """获取请求头"""
        return self.头信息.get(名称, 默认)


class 响应:
    """Web 框架响应对象，扩展自 HTTP服务端.HTTP响应"""
    def __init__(self):
        self.状态码 = 200
        self.状态消息 = "OK"
        self.头信息 = {"Content-Type": "text/plain; charset=utf-8"}
        self.正文 = b""
        self._cookies = []
        self._session数据 = {}

    def 设置头(self, 名称, 值):
        """设置响应头"""
        self.头信息[名称] = 值

    def 写文本(self, 文本, 状态码=200, 内容类型="text/plain; charset=utf-8"):
        """写入文本响应"""
        self.状态码 = 状态码
        self.状态消息 = {200: "OK", 201: "Created", 202: "Accepted",
                        204: "No Content",
                        301: "Moved Permanently", 302: "Found",
                        304: "Not Modified", 400: "Bad Request",
                        401: "Unauthorized", 403: "Forbidden",
                        404: "Not Found", 405: "Method Not Allowed",
                        409: "Conflict", 422: "Unprocessable Entity",
                        429: "Too Many Requests",
                        500: "Internal Server Error",
                        502: "Bad Gateway", 503: "Service Unavailable"}.get(状态码, "Unknown")
        self.头信息["Content-Type"] = 内容类型
        if isinstance(文本, str):
            self.正文 = 文本.encode("utf-8")
        else:
            self.正文 = 文本

    def 写JSON(self, 数据, 状态码=200):
        """写入 JSON 响应"""
        try:
            文本 = _json.dumps(数据, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            raise Exception("序列化JSON失败: " + str(e))
        self.写文本(文本, 状态码=状态码, 内容类型="application/json; charset=utf-8")

    def 写HTML(self, html, 状态码=200):
        """写入 HTML 响应"""
        self.写文本(html, 状态码=状态码, 内容类型="text/html; charset=utf-8")

    def 写文件(self, 文件路径):
        """写入文件响应"""
        try:
            if not _os.path.exists(文件路径):
                self.写文本("文件不存在", 状态码=404)
                return
            with open(文件路径, "rb") as f:
                self.正文 = f.read()
            内容类型, _ = _mimetypes.guess_type(文件路径)
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
        self.状态消息 = {301: "Moved Permanently", 302: "Found",
                        307: "Temporary Redirect",
                        308: "Permanent Redirect"}.get(状态码, "Found")
        self.头信息["Location"] = 位置
        self.正文 = b""

    def 设置Cookie(self, 名称, 值, 路径="/", 过期时间=None, 安全=False, HTTPOnly=False):
        """设置 Cookie"""
        cookie = f"{名称}={值}; Path={路径}"
        if 过期时间:
            if isinstance(过期时间, _datetime):
                过期时间 = 过期时间.strftime("%a, %d %b %Y %H:%M:%S GMT")
            cookie += f"; Expires={过期时间}"
        if 安全:
            cookie += "; Secure"
        if HTTPOnly:
            cookie += "; HttpOnly"
        self._cookies.append(cookie)

    def 删除Cookie(self, 名称, 路径="/"):
        """删除 Cookie"""
        import datetime
        过期时间 = datetime.datetime(1970, 1, 1).strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie = f"{名称}=; Path={路径}; Expires={过期时间}"
        self._cookies.append(cookie)

    def 设置Session数据(self, 数据):
        """设置 Session 数据"""
        self._session数据 = 数据


# =============================================================================
# 路由系统
# =============================================================================

class 路由:
    """单个路由定义"""
    def __init__(self, 方法="GET", 路径模式="/", 处理函数=None, 中间件列表=None):
        self.方法 = 方法.upper()
        self.路径模式 = 路径模式
        self.处理函数 = 处理函数
        self.中间件列表 = 中间件列表 or []
        # 将 {参数名} 转换为命名捕获组
        self._模式 = _re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', 路径模式)
        # 支持 * 通配符
        self._模式 = _re.sub(r'\*', r'[^/]*', self._模式)
        # 标准化路径模式，支持可选的尾部斜杠
        if self._模式 == '/' or self._模式 == '':
            self._模式 = '/?'
        else:
            self._模式 = self._模式.rstrip('/') + '/?'
        self._正则 = _re.compile(f'^{self._模式}$')

    def 匹配(self, 路径):
        """尝试匹配路径，成功返回路径参数字典，失败返回 None"""
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
        self._路由分组 = {}
        self._404处理函数 = None
        self._405处理函数 = None

    def 注册(self, 方法, 路径, 处理函数, 中间件列表=None):
        """注册路由"""
        if not callable(处理函数):
            raise Exception("路由注册失败: 处理函数必须是可调用对象")
        self._路由列表.append(路由(方法, 路径, 处理函数, 中间件列表))

    def GET(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 GET 路由（装饰器风格）"""
        if 处理函数 is None:
            return lambda fn: self.注册("GET", 路径, fn, 中间件列表) or fn
        self.注册("GET", 路径, 处理函数, 中间件列表)
        return 处理函数

    def POST(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 POST 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("POST", 路径, fn, 中间件列表) or fn
        self.注册("POST", 路径, 处理函数, 中间件列表)
        return 处理函数

    def PUT(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 PUT 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("PUT", 路径, fn, 中间件列表) or fn
        self.注册("PUT", 路径, 处理函数, 中间件列表)
        return 处理函数

    def DELETE(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 DELETE 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("DELETE", 路径, fn, 中间件列表) or fn
        self.注册("DELETE", 路径, 处理函数, 中间件列表)
        return 处理函数

    def PATCH(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 PATCH 路由"""
        if 处理函数 is None:
            return lambda fn: self.注册("PATCH", 路径, fn, 中间件列表) or fn
        self.注册("PATCH", 路径, 处理函数, 中间件列表)
        return 处理函数

    def 设置404处理(self, 处理函数):
        """设置 404 处理函数"""
        self._404处理函数 = 处理函数

    def 设置405处理(self, 处理函数):
        """设置 405 处理函数"""
        self._405处理函数 = 处理函数

    def 匹配(self, 方法, 路径):
        """
        匹配路由，返回 (处理函数, 路径参数)

        返回:
            (处理函数, 路径参数字典) 或 (None, {})
        """
        方法 = 方法.upper()
        if 路径 != '/' and 路径.endswith('/'):
            路径 = 路径.rstrip('/')

        # 收集匹配同一路径但不匹配方法的路由
        有方法不匹配 = False

        for 路由 in self._路由列表:
            if 路由.方法 == 方法:
                参数 = 路由.匹配(路径)
                if 参数 is not None:
                    return 路由.处理函数, 参数, 路由.中间件列表
            elif 路由.匹配(路径) is not None:
                有方法不匹配 = True

        # 没有匹配到路由
        return None, {}, []

    def 获取路由列表(self):
        """获取所有注册的路由"""
        return [(r.方法, r.路径模式) for r in self._路由列表]


# =============================================================================
# 中间件链
# =============================================================================

class 中间件基类:
    """中间件基类"""
    def 请求前(self, 请求, 响应):
        """请求前处理，返回 True 继续处理，返回 False 终止"""
        return True

    def 请求后(self, 请求, 响应):
        """请求后处理"""
        pass


class 错误处理中间件(中间件基类):
    """错误处理中间件"""
    def __init__(self):
        self._错误处理函数 = {}

    def 注册错误处理(self, 状态码, 处理函数):
        """注册特定状态码的错误处理函数"""
        self._错误处理函数[状态码] = 处理函数

    def 请求后(self, 请求, 响应):
        """请求后处理：检查错误状态码"""
        状态码 = 响应.状态码
        if 状态码 in self._错误处理函数:
            try:
                self._错误处理函数[状态码](请求, 响应)
            except Exception:
                pass


class 日志中间件(中间件基类):
    """日志记录中间件"""
    def __init__(self, 记录器=None):
        self.记录器 = 记录器 or print

    def 请求前(self, 请求, 响应):
        """记录请求开始"""
        self._开始时间 = _time.time()
        return True

    def 请求后(self, 请求, 响应):
        """记录请求完成"""
        耗时 = (_time.time() - self._开始时间) * 1000
        try:
            self.记录器(f"[{_datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                       f"{请求.客户端地址}:{请求.客户端端口} "
                       f"{请求.方法} {请求.路径} "
                       f"-> {响应.状态码} ({耗时:.1f}ms)")
        except Exception:
            pass


class CORS中间件(中间件基类):
    """CORS 中间件"""
    def __init__(self, 允许来源="*", 允许方法="GET,POST,PUT,DELETE,PATCH,OPTIONS",
                 允许头="Content-Type,Authorization,X-Requested-With",
                 允许凭证=False):
        self.允许来源 = 允许来源
        self.允许方法 = 允许方法
        self.允许头 = 允许头
        self.允许凭证 = 允许凭证

    def 请求前(self, 请求, 响应):
        """处理 CORS 预检请求和添加响应头"""
        响应.设置头("Access-Control-Allow-Origin", self.允许来源)
        响应.设置头("Access-Control-Allow-Methods", self.允许方法)
        响应.设置头("Access-Control-Allow-Headers", self.允许头)
        if self.允许凭证:
            响应.设置头("Access-Control-Allow-Credentials", "true")
        if 请求.方法 == "OPTIONS":
            响应.写文本("", 状态码=204)
            return False
        return True


class 静态文件中间件(中间件基类):
    """静态文件服务中间件"""
    def __init__(self, URL前缀, 目录路径):
        if not URL前缀.endswith('/'):
            URL前缀 += '/'
        self.URL前缀 = URL前缀
        self.目录路径 = _os.path.abspath(目录路径)

    def 请求前(self, 请求, 响应):
        """在路由匹配前检查静态文件"""
        if 请求.路径.startswith(self.URL前缀):
            相对路径 = 请求.路径[len(self.URL前缀):].lstrip('/')
            if not 相对路径:
                return True
            # 防止路径穿越
            完整路径 = _os.path.normpath(_os.path.join(self.目录路径, 相对路径))
            if not 完整路径.startswith(self.目录路径):
                响应.写文本("Forbidden", 状态码=403)
                return False
            if _os.path.isfile(完整路径):
                try:
                    响应.写文件(完整路径)
                    return False
                except Exception:
                    响应.写文本("读取静态文件失败", 状态码=500)
                    return False
        return True


class Session中间件(中间件基类):
    """Session 管理中间件"""
    def __init__(self, 密钥="duan-web-secret-key"):
        self._session存储 = {}
        self.密钥 = 密钥
        self._锁 = _threading.Lock()

    def 请求前(self, 请求, 响应):
        """加载 Session"""
        session_id = 请求.获取Cookie("session_id")
        if not session_id or session_id not in self._session存储:
            session_id = str(_uuid.uuid4())
            with self._锁:
                self._session存储[session_id] = {}
        请求._session_id = session_id
        with self._锁:
            请求._session数据 = self._session存储[session_id]
        return True

    def 请求后(self, 请求, 响应):
        """保存 Session"""
        if hasattr(请求, '_session_id') and hasattr(请求, '_session数据'):
            session_id = 请求._session_id
            with self._锁:
                self._session存储[session_id] = 请求._session数据
            响应.设置Cookie("session_id", session_id, HTTPOnly=True)

    def 获取Session(self, 请求):
        """获取 Session 数据"""
        return getattr(请求, '_session数据', {})

    def 销毁Session(self, 请求, 响应):
        """销毁 Session"""
        if hasattr(请求, '_session_id'):
            session_id = 请求._session_id
            with self._锁:
                self._session存储.pop(session_id, None)
            响应.删除Cookie("session_id")


class 速率限制中间件(中间件基类):
    """速率限制中间件"""
    def __init__(self, 最大请求数=100, 时间窗口=60):
        self.最大请求数 = 最大请求数
        self.时间窗口 = 时间窗口
        self._记录 = {}
        self._锁 = _threading.Lock()

    def 请求前(self, 请求, 响应):
        """检查速率限制"""
        客户端IP = 请求.客户端地址
        当前时间 = _time.time()

        with self._锁:
            if 客户端IP not in self._记录:
                self._记录[客户端IP] = []
            # 清理过期记录
            self._记录[客户端IP] = [t for t in self._记录[客户端IP]
                                      if 当前时间 - t < self.时间窗口]
            if len(self._记录[客户端IP]) >= self.最大请求数:
                响应.写JSON({
                    "error": "Too Many Requests",
                    "message": f"超过速率限制，每{self.时间窗口}秒最多{self.最大请求数}次请求"
                }, 状态码=429)
                return False
            self._记录[客户端IP].append(当前时间)
        return True


class 认证中间件(中间件基类):
    """基础认证中间件"""
    def __init__(self, 验证函数=None):
        """
        验证函数签名: fn(请求) -> bool
        """
        self.验证函数 = 验证函数

    def 请求前(self, 请求, 响应):
        """验证请求"""
        if self.验证函数:
            try:
                if not self.验证函数(请求):
                    响应.写JSON({"error": "Unauthorized"}, 状态码=401)
                    return False
            except Exception:
                响应.写JSON({"error": "Authentication failed"}, 状态码=500)
                return False
        return True


class 压缩中间件(中间件基类):
    """响应压缩中间件"""
    def __init__(self, 最小大小=1024):
        self.最小大小 = 最小大小

    def 请求后(self, 请求, 响应):
        """压缩响应体"""
        import gzip
        接受编码 = 请求.头信息.get("Accept-Encoding", "")
        if "gzip" in 接受编码 and len(响应.正文) >= self.最小大小:
            try:
                compressed = gzip.compress(响应.正文)
                if len(compressed) < len(响应.正文):
                    响应.正文 = compressed
                    响应.设置头("Content-Encoding", "gzip")
            except Exception:
                pass


# =============================================================================
# 模板引擎集成
# =============================================================================

class 模板引擎:
    """模板引擎，集成 Python string.Template 和自定义语法"""
    def __init__(self, 模板目录="templates"):
        self.模板目录 = 模板目录
        self._缓存 = {}
        self._全局变量 = {}
        self._过滤器 = {}

    def 注册全局变量(self, 名称, 值):
        """注册全局变量"""
        self._全局变量[名称] = 值

    def 注册过滤器(self, 名称, 函数):
        """注册过滤器"""
        self._过滤器[名称] = 函数

    def 渲染字符串(self, 模板字符串, 上下文=None):
        """渲染模板字符串"""
        if 上下文 is None:
            上下文 = {}
        完整上下文 = dict(self._全局变量)
        完整上下文.update(上下文)
        return self._渲染(模板字符串, 完整上下文)

    def 渲染文件(self, 模板文件名, 上下文=None):
        """渲染模板文件"""
        if 上下文 is None:
            上下文 = {}
        完整上下文 = dict(self._全局变量)
        完整上下文.update(上下文)

        # 检查缓存
        if 模板文件名 in self._缓存:
            return self._渲染(self._缓存[模板文件名], 完整上下文)

        # 加载模板文件
        模板路径 = _os.path.join(self.模板目录, 模板文件名)
        if not _os.path.exists(模板路径):
            raise Exception(f"模板文件未找到: {模板文件名}")

        with open(模板路径, 'r', encoding='utf-8') as f:
            模板内容 = f.read()

        self._缓存[模板文件名] = 模板内容
        return self._渲染(模板内容, 完整上下文)

    def 清空缓存(self):
        """清空模板缓存"""
        self._缓存.clear()

    def _渲染(self, 文本, 上下文):
        """渲染模板文本，支持变量插值、循环、条件"""
        # 处理注释 {# #}
        文本 = _re.sub(r'\{#.*?#\}', '', 文本, flags=_re.DOTALL)

        # 处理循环 {% for var in list %}...{% endfor %}
        def _处理循环(m):
            inner = m.group(1)
            parts = inner.split(' in ', 1)
            if len(parts) != 2:
                return ''
            变量名 = parts[0].strip()
            列表名 = parts[1].strip()
            列表数据 = 上下文.get(列表名, [])
            # 找到对应的 endfor
            return ''  # 占位，由完整处理

        # 使用更复杂的方式处理嵌套结构
        文本 = self._处理块语句(文本, 上下文)

        # 处理变量插值 {{ var }} 和 {{ var | filter }}
        def _替换变量(m):
            expr = m.group(1).strip()
            # 检查是否有过滤器
            if '|' in expr:
                parts = [p.strip() for p in expr.split('|')]
                变量名 = parts[0]
                过滤器链 = parts[1:]
                值 = 上下文.get(变量名, '')
                for 过滤器名 in 过滤器链:
                    if 过滤器名 in self._过滤器:
                        try:
                            值 = self._过滤器[过滤器名](值)
                        except Exception:
                            pass
                return str(值)
            else:
                # 简单变量或属性访问，转换为字符串
                return str(self._解析变量(expr, 上下文))

        文本 = _re.sub(r'\{\{(.*?)\}\}', _替换变量, 文本)

        return 文本

    def _处理块语句(self, 文本, 上下文):
        """处理 {% %} 块语句"""
        # 处理 if/elif/else/endif
        def _处理条件(m):
            return self._处理if块(m, 上下文)

        文本 = _re.sub(
            r'\{%\s*if\s+(.*?)\s*%\}(.*?)(?:\{%\s*elif\s+(.*?)\s*%\}(.*?))*(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}',
            _处理条件,
            文本,
            flags=_re.DOTALL
        )

        # 处理 for/endfor
        def _处理循环(m):
            return self._处理for块(m, 上下文)

        文本 = _re.sub(
            r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}',
            _处理循环,
            文本,
            flags=_re.DOTALL
        )

        return 文本

    def _处理if块(self, m, 上下文):
        """处理 if 条件块"""
        full = m.group(0)
        条件 = m.group(1)
        # 简化匹配：只处理简单的 if/else/endif
        # 提取 if 条件之后到 endif 的内容
        if_match = _re.match(r'\{%\s*if\s+(.*?)\s*%\}', full)
        if not if_match:
            return ''

        if_条件 = if_match.group(1)
        rest = full[if_match.end():]

        # 查找 else 或 endif
        else_match = _re.search(r'\{%\s*else\s*%\}', rest)
        endif_match = _re.search(r'\{%\s*endif\s*%\}', rest)

        if not endif_match:
            return ''

        if_block = rest[:endif_match.start()]
        else_block = ''
        if else_match and else_match.start() < endif_match.start():
            if_block = rest[:else_match.start()]
            else_block = rest[else_match.end():endif_match.start()]

        if self._评估条件(if_条件, 上下文):
            return self._渲染(if_block, 上下文)
        else:
            return self._渲染(else_block, 上下文)

    def _处理for块(self, m, 上下文):
        """处理 for 循环块"""
        变量名 = m.group(1)
        列表名 = m.group(2)
        块内容 = m.group(3)
        列表数据 = 上下文.get(列表名, [])
        if not isinstance(列表数据, (list, tuple, range)):
            return ''
        result = []
        for item in 列表数据:
            ctx = dict(上下文)
            ctx[变量名] = item
            result.append(self._渲染(块内容, ctx))
        return ''.join(result)

    def _评估条件(self, 条件文本, 上下文):
        """评估条件表达式"""
        条件文本 = 条件文本.strip()

        # 检查是否有比较运算符
        for op in ['!=', '==', '>=', '<=', '>', '<']:
            if op in 条件文本:
                parts = 条件文本.split(op, 1)
                left = self._解析变量(parts[0].strip(), 上下文)
                right = self._解析变量(parts[1].strip(), 上下文)
                try:
                    left_f = float(left)
                    right_f = float(right)
                    if op == '==':
                        return left_f == right_f
                    elif op == '!=':
                        return left_f != right_f
                    elif op == '>=':
                        return left_f >= right_f
                    elif op == '<=':
                        return left_f <= right_f
                    elif op == '>':
                        return left_f > right_f
                    elif op == '<':
                        return left_f < right_f
                except (ValueError, TypeError):
                    if op == '==':
                        return str(left) == str(right)
                    elif op == '!=':
                        return str(left) != str(right)
                    return False

        # 纯变量名
        val = self._解析变量(条件文本, 上下文)
        return bool(val)

    def _解析变量(self, 表达式, 上下文):
        """解析变量表达式，支持点号属性访问，返回原始值"""
        表达式 = 表达式.strip()
        # 字符串字面量
        if (表达式.startswith("'") and 表达式.endswith("'")) or \
           (表达式.startswith('"') and 表达式.endswith('"')):
            return 表达式[1:-1]
        # 数字字面量
        try:
            if '.' in 表达式:
                return float(表达式)
            return int(表达式)
        except ValueError:
            pass
        # 变量访问
        parts = 表达式.split('.')
        val = 上下文.get(parts[0], '')
        for part in parts[1:]:
            if isinstance(val, dict):
                val = val.get(part, '')
            else:
                try:
                    val = getattr(val, part, '')
                except Exception:
                    val = ''
        return val


def 创建模板引擎(模板目录="templates"):
    """创建模板引擎"""
    return 模板引擎(模板目录)


# =============================================================================
# Session 会话管理器
# =============================================================================

class Session管理器:
    """Session 会话管理器"""
    def __init__(self):
        self._存储 = {}
        self._锁 = _threading.Lock()

    def 创建Session(self, 数据=None):
        """创建新会话"""
        session_id = str(_uuid.uuid4())
        with self._锁:
            self._存储[session_id] = 数据 or {}
        return session_id

    def 获取Session(self, session_id):
        """获取会话数据"""
        with self._锁:
            return self._存储.get(session_id)

    def 设置Session(self, session_id, 数据):
        """设置会话数据"""
        with self._锁:
            self._存储[session_id] = 数据

    def 更新Session(self, session_id, 键, 值):
        """更新会话中的某个字段"""
        with self._锁:
            if session_id in self._存储:
                self._存储[session_id][键] = 值
                return True
            return False

    def 删除Session(self, session_id):
        """删除会话"""
        with self._锁:
            return self._存储.pop(session_id, None) is not None

    def 清理过期(self, 过期秒数=3600):
        """清理过期会话"""
        当前时间 = _time.time()
        with self._锁:
            # 简化实现：不记录时间戳，依赖外部调用
            pass


def 创建Session管理器():
    """创建 Session 管理器"""
    return Session管理器()


# =============================================================================
# Web 应用
# =============================================================================

class Web应用:
    """
    Web 应用主类

    提供完整的 Web 框架功能：
    - 路由注册（GET/POST/PUT/DELETE/PATCH）
    - 路径参数
    - 中间件链
    - 模板渲染
    - Session 管理
    - 静态文件服务
    - CORS 支持
    """

    def __init__(self, 标题="Duan Web App"):
        self.标题 = 标题
        self._路由表 = 路由表()
        self._中间件列表 = []
        self._模板引擎 = None
        self._Session管理器 = Session管理器()
        self._服务器 = None
        self._全局处理函数 = None
        self._静态文件目录 = {}

    # =========================================================================
    # 路由注册
    # =========================================================================

    def GET(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 GET 路由（装饰器风格）"""
        if 处理函数 is None:
            return lambda fn: self._路由表.注册("GET", 路径, fn, 中间件列表) or fn
        self._路由表.注册("GET", 路径, 处理函数, 中间件列表)
        return 处理函数

    def POST(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 POST 路由"""
        if 处理函数 is None:
            return lambda fn: self._路由表.注册("POST", 路径, fn, 中间件列表) or fn
        self._路由表.注册("POST", 路径, 处理函数, 中间件列表)
        return 处理函数

    def PUT(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 PUT 路由"""
        if 处理函数 is None:
            return lambda fn: self._路由表.注册("PUT", 路径, fn, 中间件列表) or fn
        self._路由表.注册("PUT", 路径, 处理函数, 中间件列表)
        return 处理函数

    def DELETE(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 DELETE 路由"""
        if 处理函数 is None:
            return lambda fn: self._路由表.注册("DELETE", 路径, fn, 中间件列表) or fn
        self._路由表.注册("DELETE", 路径, 处理函数, 中间件列表)
        return 处理函数

    def PATCH(self, 路径, 处理函数=None, 中间件列表=None):
        """注册 PATCH 路由"""
        if 处理函数 is None:
            return lambda fn: self._路由表.注册("PATCH", 路径, fn, 中间件列表) or fn
        self._路由表.注册("PATCH", 路径, 处理函数, 中间件列表)
        return 处理函数

    # =========================================================================
    # 路由分组
    # =========================================================================

    def 路由分组(self, 前缀="", 中间件列表=None):
        """创建路由分组"""
        return 路由分组(self, 前缀, 中间件列表 or [])

    # =========================================================================
    # 中间件管理
    # =========================================================================

    def 使用中间件(self, 中间件):
        """添加全局中间件"""
        self._中间件列表.append(中间件)

    def 使用中间件列表(self, 中间件列表):
        """批量添加中间件"""
        for m in 中间件列表:
            self._中间件列表.append(m)

    # =========================================================================
    # 模板管理
    # =========================================================================

    def 设置模板引擎(self, 模板引擎):
        """设置模板引擎"""
        self._模板引擎 = 模板引擎

    def 创建模板引擎(self, 模板目录="templates"):
        """创建并设置模板引擎"""
        engine = 创建模板引擎(模板目录)
        self._模板引擎 = engine
        return engine

    def 渲染模板(self, 模板名, 上下文=None):
        """渲染模板"""
        if self._模板引擎 is None:
            raise Exception("模板引擎未设置，请先调用 创建模板引擎()")
        return self._模板引擎.渲染文件(模板名, 上下文)

    def 渲染字符串(self, 模板字符串, 上下文=None):
        """渲染模板字符串"""
        if self._模板引擎 is None:
            raise Exception("模板引擎未设置，请先调用 创建模板引擎()")
        return self._模板引擎.渲染字符串(模板字符串, 上下文)

    # =========================================================================
    # 静态文件
    # =========================================================================

    def 静态文件(self, URL前缀, 目录路径):
        """添加静态文件服务"""
        if not _os.path.isdir(目录路径):
            raise Exception(f"静态文件目录不存在: {目录路径}")
        if not URL前缀.startswith('/'):
            URL前缀 = '/' + URL前缀
        if not URL前缀.endswith('/'):
            URL前缀 += '/'
        self._静态文件目录[URL前缀] = _os.path.abspath(目录路径)

    # =========================================================================
    # Session
    # =========================================================================

    def 获取Session(self, 请求):
        """获取 Session 数据"""
        # 优先检查请求上缓存的 session_id
        session_id = getattr(请求, '_session_id', None)
        if not session_id:
            session_id = 请求.获取Cookie("session_id")
        if session_id:
            data = self._Session管理器.获取Session(session_id)
            if data is not None:
                return data
        return {}

    def 设置Session(self, 请求, 响应, 数据):
        """设置 Session 数据"""
        session_id = 请求.获取Cookie("session_id")
        if not session_id:
            session_id = getattr(请求, '_session_id', None)
        if not session_id:
            session_id = self._Session管理器.创建Session(数据)
        else:
            self._Session管理器.设置Session(session_id, 数据)
        # 将 session_id 缓存到请求对象上，使获取Session 能找到
        请求._session_id = session_id
        响应.设置Cookie("session_id", session_id, HTTPOnly=True)

    def 更新Session(self, 请求, 键, 值):
        """更新 Session 中的字段"""
        session_id = 请求.获取Cookie("session_id")
        if session_id:
            return self._Session管理器.更新Session(session_id, 键, 值)
        return False

    def 删除Session(self, 请求, 响应):
        """删除 Session"""
        session_id = 请求.获取Cookie("session_id")
        if session_id:
            self._Session管理器.删除Session(session_id)
        响应.删除Cookie("session_id")

    # =========================================================================
    # 应用启动
    # =========================================================================

    def _创建请求处理器(self):
        """创建请求处理器类"""
        路由表 = self._路由表
        中间件列表 = self._中间件列表
        静态文件目录 = self._静态文件目录

        class _请求处理器(_http_server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _解析请求(self):
                req = 请求()
                req.方法 = self.command
                req.路径 = self.path
                req.协议版本 = self.request_version
                req.头信息 = dict(self.headers)
                req.客户端地址 = self.client_address[0]
                req.客户端端口 = self.client_address[1]

                # 解析路径和查询参数
                parsed = _urlparse.urlparse(self.path)
                req.路径 = parsed.path
                if parsed.query:
                    for key, values in _urlparse.parse_qs(parsed.query).items():
                        req.查询参数[key] = values[0] if len(values) == 1 else values

                # 解析 Cookie
                cookie_header = self.headers.get("Cookie", "")
                if cookie_header:
                    for cookie_pair in cookie_header.split(";"):
                        cookie_pair = cookie_pair.strip()
                        if "=" in cookie_pair:
                            name, value = cookie_pair.split("=", 1)
                            req._cookies[name.strip()] = value.strip()

                # 读取请求体
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    req.正文 = self.rfile.read(content_length)
                else:
                    req.正文 = b""

                return req

            def _发送响应(self, 响应):
                try:
                    self.send_response(响应.状态码, 响应.状态消息)
                    for 名称, 值 in 响应.头信息.items():
                        self.send_header(名称, 值)
                    for cookie in 响应._cookies:
                        self.send_header("Set-Cookie", cookie)
                    self.end_headers()
                    if 响应.正文:
                        self.wfile.write(响应.正文)
                except Exception:
                    pass

            def _处理请求(self):
                req = self._解析请求()
                resp = 响应()

                # 请求前中间件
                for m in 中间件列表:
                    if hasattr(m, '请求前'):
                        try:
                            result = m.请求前(req, resp)
                            if result is False:
                                self._发送响应(resp)
                                return
                        except Exception:
                            pass

                # 路由匹配
                try:
                    self._执行路由匹配(req, resp)
                except Exception as e:
                    resp.写文本("服务器内部错误: " + str(e), 状态码=500)

                # 请求后中间件
                for m in 中间件列表:
                    if hasattr(m, '请求后'):
                        try:
                            m.请求后(req, resp)
                        except Exception:
                            pass

                self._发送响应(resp)

            def _执行路由匹配(self, req, resp):
                # 检查静态文件
                for url_prefix, 目录 in 静态文件目录.items():
                    if req.路径.startswith(url_prefix):
                        相对路径 = req.路径[len(url_prefix):].lstrip('/')
                        if 相对路径:
                            完整路径 = _os.path.normpath(_os.path.join(目录, 相对路径))
                            if 完整路径.startswith(目录) and _os.path.isfile(完整路径):
                                resp.写文件(完整路径)
                                return

                # 路由匹配
                处理函数, 路径参数, 路由中间件 = 路由表.匹配(req.方法, req.路径)
                if 处理函数:
                    req._路径参数 = 路径参数
                    # 执行路由级中间件（请求前）
                    for m in 路由中间件:
                        if hasattr(m, '请求前'):
                            try:
                                result = m.请求前(req, resp)
                                if result is False:
                                    return
                            except Exception:
                                pass
                    try:
                        处理函数(req, resp)
                    except Exception as e:
                        resp.写文本("处理请求失败: " + str(e), 状态码=500)
                    # 执行路由级中间件（请求后）
                    for m in 路由中间件:
                        if hasattr(m, '请求后'):
                            try:
                                m.请求后(req, resp)
                            except Exception:
                                pass
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

        return _请求处理器

    def 启动(self, 主机="0.0.0.0", 端口=8080, 阻塞=False):
        """启动 Web 应用"""
        处理器类 = self._创建请求处理器()
        try:
            self._服务器 = _http_server.HTTPServer((主机, 端口), 处理器类)
            if 阻塞:
                print(f"Web 应用运行在 http://{主机}:{端口}")
                self._服务器.serve_forever()
            else:
                t = _threading.Thread(target=self._服务器.serve_forever, daemon=True)
                t.start()
                return t
        except OSError as e:
            raise Exception(f"启动服务器失败(地址={主机}:{端口}): {e}")

    def 停止(self):
        """停止 Web 应用"""
        if self._服务器:
            try:
                self._服务器.shutdown()
            except Exception:
                pass
            self._服务器 = None

    @property
    def 地址(self):
        """获取服务器地址"""
        if self._服务器:
            return self._服务器.server_address
        return None


# =============================================================================
# 路由分组
# =============================================================================

class 路由分组:
    """路由分组，支持前缀和组级中间件"""
    def __init__(self, 应用, 前缀="", 中间件列表=None):
        self._应用 = 应用
        self._前缀 = 前缀
        self._中间件列表 = 中间件列表 or []

    def GET(self, 路径, 处理函数=None):
        完整路径 = self._前缀 + 路径
        if 处理函数 is None:
            return lambda fn: self._应用._路由表.注册("GET", 完整路径, fn, self._中间件列表) or fn
        self._应用._路由表.注册("GET", 完整路径, 处理函数, self._中间件列表)
        return 处理函数

    def POST(self, 路径, 处理函数=None):
        完整路径 = self._前缀 + 路径
        if 处理函数 is None:
            return lambda fn: self._应用._路由表.注册("POST", 完整路径, fn, self._中间件列表) or fn
        self._应用._路由表.注册("POST", 完整路径, 处理函数, self._中间件列表)
        return 处理函数

    def PUT(self, 路径, 处理函数=None):
        完整路径 = self._前缀 + 路径
        if 处理函数 is None:
            return lambda fn: self._应用._路由表.注册("PUT", 完整路径, fn, self._中间件列表) or fn
        self._应用._路由表.注册("PUT", 完整路径, 处理函数, self._中间件列表)
        return 处理函数

    def DELETE(self, 路径, 处理函数=None):
        完整路径 = self._前缀 + 路径
        if 处理函数 is None:
            return lambda fn: self._应用._路由表.注册("DELETE", 完整路径, fn, self._中间件列表) or fn
        self._应用._路由表.注册("DELETE", 完整路径, 处理函数, self._中间件列表)
        return 处理函数

    def PATCH(self, 路径, 处理函数=None):
        完整路径 = self._前缀 + 路径
        if 处理函数 is None:
            return lambda fn: self._应用._路由表.注册("PATCH", 完整路径, fn, self._中间件列表) or fn
        self._应用._路由表.注册("PATCH", 完整路径, 处理函数, self._中间件列表)
        return 处理函数

    def 使用中间件(self, 中间件):
        """为分组添加中间件"""
        self._中间件列表.append(中间件)

    def 路由分组(self, 前缀="", 中间件列表=None):
        """创建嵌套路由分组"""
        完整前缀 = self._前缀 + 前缀
        合并中间件 = list(self._中间件列表)
        if 中间件列表:
            合并中间件.extend(中间件列表)
        return 路由分组(self._应用, 完整前缀, 合并中间件)


# =============================================================================
# 便捷函数
# =============================================================================

def 创建Web应用(标题="Duan Web App"):
    """创建 Web 应用"""
    return Web应用(标题)


def 创建JSONAPI(路由字典):
    """
    从路由字典创建 JSON API 应用

    路由字典格式:
    {
        "GET /users": 处理函数,
        "POST /users": 处理函数,
        "GET /users/{id}": 处理函数,
    }

    处理函数签名: fn(req, resp)
    """
    app = Web应用()
    app.使用中间件(CORS中间件())

    for 路由描述, 处理函数 in 路由字典.items():
        部分 = 路由描述.strip().split(None, 1)
        if len(部分) != 2:
            raise Exception(f"路由描述格式错误: '{路由描述}'，应为 'GET /path'")
        方法, 路径 = 部分
        方法 = 方法.upper()
        if 方法 not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            raise Exception(f"不支持的 HTTP 方法: '{方法}'")
        app._路由表.注册(方法, 路径, 处理函数)

    return app


# =============================================================================
# 响应生成辅助函数
# =============================================================================

def JSON响应(数据, 状态码=200, 头信息=None):
    """创建 JSON 响应"""
    resp = 响应()
    resp.写JSON(数据, 状态码)
    if 头信息:
        for k, v in 头信息.items():
            resp.设置头(k, v)
    return resp


def 文本响应(文本, 状态码=200, 内容类型="text/plain; charset=utf-8"):
    """创建文本响应"""
    resp = 响应()
    resp.写文本(文本, 状态码, 内容类型)
    return resp


def HTML响应(html, 状态码=200):
    """创建 HTML 响应"""
    resp = 响应()
    resp.写HTML(html, 状态码)
    return resp


def 重定向响应(位置, 状态码=302):
    """创建重定向响应"""
    resp = 响应()
    resp.重定向(位置, 状态码)
    return resp


def 错误响应(消息, 状态码=400):
    """创建错误响应"""
    return JSON响应({"error": 消息}, 状态码=状态码)


# =============================================================================
# 构建器模式：用于快速定义 API
# =============================================================================

class API构建器:
    """API 构建器，用于快速定义 RESTful API"""
    def __init__(self, 应用=None):
        self.应用 = 应用 or Web应用()

    def 资源(self, 名称, 控制器):
        """
        注册 CRUD 资源路由

        自动生成:
        GET    /{名称}       -> 控制器.列表
        POST   /{名称}       -> 控制器.创建
        GET    /{名称}/{id}  -> 控制器.获取
        PUT    /{名称}/{id}  -> 控制器.更新
        DELETE /{名称}/{id}  -> 控制器.删除
        """
        base = f"/{名称}"
        id_path = f"{base}/{{id}}"

        if hasattr(控制器, '列表'):
            self.应用.GET(base, 控制器.列表)
        if hasattr(控制器, '创建'):
            self.应用.POST(base, 控制器.创建)
        if hasattr(控制器, '获取'):
            self.应用.GET(id_path, 控制器.获取)
        if hasattr(控制器, '更新'):
            self.应用.PUT(id_path, 控制器.更新)
        if hasattr(控制器, '删除'):
            self.应用.DELETE(id_path, 控制器.删除)

        return self

    def 构建(self):
        """返回 Web 应用"""
        return self.应用