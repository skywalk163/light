"""
光明标准库 - 网络请求模块

提供HTTP网络请求功能，包括：
- GET/POST请求
- 请求头设置
- 超时控制
- 文件下载
- 响应解析
"""

import urllib.request
import urllib.parse
import urllib.error
import http.client
import json
import os
from typing import Optional, Dict, Any, Tuple, Callable


class 响应:
    """HTTP响应对象"""
    
    def __init__(self, 状态码: int, 响应头: dict, 内容: bytes, 请求地址: str, 重定向历史: list = None):
        self._状态码 = 状态码
        self._响应头 = 响应头
        self._内容 = 内容
        self._请求地址 = 请求地址
        self._重定向历史 = 重定向历史 or []
    
    @property
    def 状态码(self) -> int:
        return self._状态码
    
    @property
    def 是否成功(self) -> bool:
        return 200 <= self._状态码 < 300
    
    @property
    def 响应头(self) -> dict:
        return self._响应头
    
    @property
    def 内容(self) -> bytes:
        return self._内容
    
    @property
    def 文本(self) -> str:
        return self._内容.decode('utf-8', errors='replace')
    
    @property
    def 请求地址(self) -> str:
        return self._请求地址
    
    @property
    def 重定向历史(self) -> list:
        return self._重定向历史
    
    def JSON(self) -> Any:
        """解析响应内容为JSON"""
        return json.loads(self.文本)
    
    def 保存到文件(self, 文件路径: str):
        """保存响应内容到文件"""
        with open(文件路径, 'wb') as f:
            f.write(self._内容)
    
    def 获取头(self, 名称: str, 默认值: str = None) -> Optional[str]:
        """获取响应头"""
        return self._响应头.get(名称.lower(), 默认值)
    
    def __repr__(self) -> str:
        return f'<响应 {self._状态码}>'


class 请求错误(Exception):
    """请求错误"""
    def __init__(self, 消息: str, 原因: Exception = None):
        super().__init__(消息)
        self.原因 = 原因


class 超时错误(请求错误):
    """请求超时"""
    pass


class 连接错误(请求错误):
    """连接错误"""
    pass


class HTTP错误(请求错误):
    """HTTP错误"""
    def __init__(self, 消息: str, 状态码: int, 响应: 响应 = None):
        super().__init__(消息)
        self.状态码 = 状态码
        self.响应 = 响应


def _构建URL(地址: str, 参数: dict = None) -> str:
    """构建带查询参数的URL"""
    if 参数 is None or not 参数:
        return 地址
    查询串 = urllib.parse.urlencode(参数)
    分隔符 = '&' if '?' in 地址 else '?'
    return f'{地址}{分隔符}{查询串}'


def _响应头转字典(响应头) -> dict:
    """将响应头转换为字典"""
    结果 = {}
    for 键, 值 in 响应头.items():
        结果[键.lower()] = 值
    return 结果


def GET请求(
    地址: str,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    编码: str = 'utf-8',
    跟随重定向: bool = True,
    验证SSL: bool = True
) -> 响应:
    """发送GET请求
    
    参数:
        地址: 请求URL
        参数: URL查询参数
        请求头: 请求头字典
        超时: 超时时间（秒）
        编码: 响应文本编码
        跟随重定向: 是否跟随重定向
        验证SSL: 是否验证SSL证书
    
    返回:
        响应对象
    """
    完整地址 = _构建URL(地址, 参数)
    
    try:
        req = urllib.request.Request(完整地址, method='GET')
        
        if 请求头:
            for 键, 值 in 请求头.items():
                req.add_header(键, 值)
        
        上下文 = None
        if not 验证SSL:
            import ssl
            上下文 = ssl._create_unverified_context()
        
        响应 = urllib.request.urlopen(req, timeout=超时, context=上下文)
        
        内容 = 响应.read()
        响应头 = _响应头转字典(响应.headers)
        
        return 响应(
            状态码=响应.status,
            响应头=响应头,
            内容=内容,
            请求地址=响应.geturl()
        )
    
    except urllib.error.HTTPError as e:
        内容 = e.read() if hasattr(e, 'read') else b''
        响应头 = _响应头转字典(e.headers) if e.headers else {}
        响应对象 = 响应(
            状态码=e.code,
            响应头=响应头,
            内容=内容,
            请求地址=完整地址
        )
        raise HTTP错误(f'HTTP错误: {e.code}', e.code, 响应对象)
    
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise 超时错误(f'请求超时: {e.reason}', e.reason)
        raise 连接错误(f'连接错误: {e.reason}', e.reason)
    
    except TimeoutError as e:
        raise 超时错误(f'请求超时: {e}', e)
    
    except Exception as e:
        raise 请求错误(f'请求失败: {e}', e)


def POST请求(
    地址: str,
    数据: Any = None,
    JSON数据: Any = None,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    编码: str = 'utf-8',
    跟随重定向: bool = True,
    验证SSL: bool = True
) -> 响应:
    """发送POST请求
    
    参数:
        地址: 请求URL
        数据: 表单数据（dict或bytes）
        JSON数据: JSON数据（自动序列化为JSON）
        参数: URL查询参数
        请求头: 请求头字典
        超时: 超时时间（秒）
        编码: 请求/响应编码
        跟随重定向: 是否跟随重定向
        验证SSL: 是否验证SSL证书
    
    返回:
        响应对象
    """
    完整地址 = _构建URL(地址, 参数)
    
    try:
        req = urllib.request.Request(完整地址, method='POST')
        
        最终请求头 = dict(请求头 or {})
        
        if JSON数据 is not None:
            请求体 = json.dumps(JSON数据, ensure_ascii=False).encode(编码)
            最终请求头.setdefault('Content-Type', 'application/json; charset=' + 编码)
        elif 数据 is not None:
            if isinstance(数据, dict):
                请求体 = urllib.parse.urlencode(数据).encode(编码)
                最终请求头.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=' + 编码)
            elif isinstance(数据, str):
                请求体 = 数据.encode(编码)
            else:
                请求体 = 数据
        else:
            请求体 = b''
        
        for 键, 值 in 最终请求头.items():
            req.add_header(键, 值)
        
        上下文 = None
        if not 验证SSL:
            import ssl
            上下文 = ssl._create_unverified_context()
        
        响应 = urllib.request.urlopen(req, data=请求体, timeout=超时, context=上下文)
        
        内容 = 响应.read()
        响应头 = _响应头转字典(响应.headers)
        
        return 响应(
            状态码=响应.status,
            响应头=响应头,
            内容=内容,
            请求地址=响应.geturl()
        )
    
    except urllib.error.HTTPError as e:
        内容 = e.read() if hasattr(e, 'read') else b''
        响应头 = _响应头转字典(e.headers) if e.headers else {}
        响应对象 = 响应(
            状态码=e.code,
            响应头=响应头,
            内容=内容,
            请求地址=完整地址
        )
        raise HTTP错误(f'HTTP错误: {e.code}', e.code, 响应对象)
    
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise 超时错误(f'请求超时: {e.reason}', e.reason)
        raise 连接错误(f'连接错误: {e.reason}', e.reason)
    
    except TimeoutError as e:
        raise 超时错误(f'请求超时: {e}', e)
    
    except Exception as e:
        raise 请求错误(f'请求失败: {e}', e)


def PUT请求(
    地址: str,
    数据: Any = None,
    JSON数据: Any = None,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    验证SSL: bool = True
) -> 响应:
    """发送PUT请求"""
    return _通用请求('PUT', 地址, 数据, JSON数据, 参数, 请求头, 超时, 验证SSL)


def DELETE请求(
    地址: str,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    验证SSL: bool = True
) -> 响应:
    """发送DELETE请求"""
    return _通用请求('DELETE', 地址, None, None, 参数, 请求头, 超时, 验证SSL)


def PATCH请求(
    地址: str,
    数据: Any = None,
    JSON数据: Any = None,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    验证SSL: bool = True
) -> 响应:
    """发送PATCH请求"""
    return _通用请求('PATCH', 地址, 数据, JSON数据, 参数, 请求头, 超时, 验证SSL)


def HEAD请求(
    地址: str,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    验证SSL: bool = True
) -> 响应:
    """发送HEAD请求"""
    return _通用请求('HEAD', 地址, None, None, 参数, 请求头, 超时, 验证SSL)


def OPTIONS请求(
    地址: str,
    参数: dict = None,
    请求头: dict = None,
    超时: float = None,
    验证SSL: bool = True
) -> 响应:
    """发送OPTIONS请求"""
    return _通用请求('OPTIONS', 地址, None, None, 参数, 请求头, 超时, 验证SSL)


def _通用请求(
    方法: str,
    地址: str,
    数据: Any,
    JSON数据: Any,
    参数: dict,
    请求头: dict,
    超时: float,
    验证SSL: bool
) -> 响应:
    """通用请求函数"""
    完整地址 = _构建URL(地址, 参数)
    
    try:
        req = urllib.request.Request(完整地址, method=方法)
        
        最终请求头 = dict(请求头 or {})
        
        if JSON数据 is not None:
            请求体 = json.dumps(JSON数据, ensure_ascii=False).encode('utf-8')
            最终请求头.setdefault('Content-Type', 'application/json; charset=utf-8')
        elif 数据 is not None:
            if isinstance(数据, dict):
                请求体 = urllib.parse.urlencode(数据).encode('utf-8')
                最终请求头.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
            elif isinstance(数据, str):
                请求体 = 数据.encode('utf-8')
            else:
                请求体 = 数据
        else:
            请求体 = b''
        
        for 键, 值 in 最终请求头.items():
            req.add_header(键, 值)
        
        上下文 = None
        if not 验证SSL:
            import ssl
            上下文 = ssl._create_unverified_context()
        
        响应 = urllib.request.urlopen(req, data=请求体 if 请求体 else None, timeout=超时, context=上下文)
        
        内容 = 响应.read()
        响应头 = _响应头转字典(响应.headers)
        
        return 响应(
            状态码=响应.status,
            响应头=响应头,
            内容=内容,
            请求地址=响应.geturl()
        )
    
    except urllib.error.HTTPError as e:
        内容 = e.read() if hasattr(e, 'read') else b''
        响应头 = _响应头转字典(e.headers) if e.headers else {}
        响应对象 = 响应(
            状态码=e.code,
            响应头=响应头,
            内容=内容,
            请求地址=完整地址
        )
        raise HTTP错误(f'HTTP错误: {e.code}', e.code, 响应对象)
    
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise 超时错误(f'请求超时: {e.reason}', e.reason)
        raise 连接错误(f'连接错误: {e.reason}', e.reason)
    
    except TimeoutError as e:
        raise 超时错误(f'请求超时: {e}', e)
    
    except Exception as e:
        raise 请求错误(f'请求失败: {e}', e)


def 下载文件(
    地址: str,
    保存路径: str,
    请求头: dict = None,
    超时: float = None,
    进度回调: Callable[[int, int], None] = None,
    验证SSL: bool = True
) -> str:
    """下载文件
    
    参数:
        地址: 文件URL
        保存路径: 保存路径
        请求头: 请求头
        超时: 超时时间
        进度回调: 进度回调函数(已下载字节数, 总字节数)
        验证SSL: 是否验证SSL证书
    
    返回:
        保存路径
    """
    完整地址 = 地址
    
    try:
        req = urllib.request.Request(完整地址, method='GET')
        
        if 请求头:
            for 键, 值 in 请求头.items():
                req.add_header(键, 值)
        
        上下文 = None
        if not 验证SSL:
            import ssl
            上下文 = ssl._create_unverified_context()
        
        响应 = urllib.request.urlopen(req, timeout=超时, context=上下文)
        
        总大小 = int(响应.headers.get('Content-Length', 0))
        已下载 = 0
        
        os.makedirs(os.path.dirname(os.path.abspath(保存路径)) or '.', exist_ok=True)
        
        with open(保存路径, 'wb') as f:
            while True:
                块 = 响应.read(8192)
                if not 块:
                    break
                f.write(块)
                已下载 += len(块)
                if 进度回调:
                    try:
                        进度回调(已下载, 总大小)
                    except:
                        pass
        
        return 保存路径
    
    except urllib.error.HTTPError as e:
        raise HTTP错误(f'下载失败，HTTP错误: {e.code}', e.code)
    
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise 超时错误(f'下载超时: {e.reason}', e.reason)
        raise 连接错误(f'下载连接错误: {e.reason}', e.reason)
    
    except Exception as e:
        raise 请求错误(f'下载失败: {e}', e)


class 会话:
    """HTTP会话（保持Cookie和连接）"""
    
    def __init__(self):
        self._Cookie处理器 = urllib.request.HTTPCookieProcessor()
        self._Opener = urllib.request.build_opener(self._Cookie处理器)
        self._默认请求头 = {}
        self._超时 = None
    
    def 设置请求头(self, 请求头: dict):
        """设置默认请求头"""
        self._默认请求头.update(请求头)
    
    def 设置超时(self, 超时: float):
        """设置默认超时"""
        self._超时 = 超时
    
    def GET(self, 地址: str, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """GET请求"""
        return self._请求('GET', 地址, None, None, 参数, 请求头, 超时)
    
    def POST(self, 地址: str, 数据: Any = None, JSON数据: Any = None, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """POST请求"""
        return self._请求('POST', 地址, 数据, JSON数据, 参数, 请求头, 超时)
    
    def PUT(self, 地址: str, 数据: Any = None, JSON数据: Any = None, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """PUT请求"""
        return self._请求('PUT', 地址, 数据, JSON数据, 参数, 请求头, 超时)
    
    def DELETE(self, 地址: str, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """DELETE请求"""
        return self._请求('DELETE', 地址, None, None, 参数, 请求头, 超时)
    
    def PATCH(self, 地址: str, 数据: Any = None, JSON数据: Any = None, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """PATCH请求"""
        return self._请求('PATCH', 地址, 数据, JSON数据, 参数, 请求头, 超时)
    
    def HEAD(self, 地址: str, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """HEAD请求"""
        return self._请求('HEAD', 地址, None, None, 参数, 请求头, 超时)
    
    def OPTIONS(self, 地址: str, 参数: dict = None, 请求头: dict = None, 超时: float = None) -> 响应:
        """OPTIONS请求"""
        return self._请求('OPTIONS', 地址, None, None, 参数, 请求头, 超时)
    
    def _请求(self, 方法: str, 地址: str, 数据: Any, JSON数据: Any, 参数: dict, 请求头: dict, 超时: float) -> 响应:
        完整地址 = _构建URL(地址, 参数)
        实际超时 = 超时 if 超时 is not None else self._超时
        
        try:
            req = urllib.request.Request(完整地址, method=方法)
            
            最终请求头 = dict(self._默认请求头)
            if 请求头:
                最终请求头.update(请求头)
            
            if JSON数据 is not None:
                请求体 = json.dumps(JSON数据, ensure_ascii=False).encode('utf-8')
                最终请求头.setdefault('Content-Type', 'application/json; charset=utf-8')
            elif 数据 is not None:
                if isinstance(数据, dict):
                    请求体 = urllib.parse.urlencode(数据).encode('utf-8')
                    最终请求头.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
                elif isinstance(数据, str):
                    请求体 = 数据.encode('utf-8')
                else:
                    请求体 = 数据
            else:
                请求体 = b''
            
            for 键, 值 in 最终请求头.items():
                req.add_header(键, 值)
            
            响应 = self._Opener.open(req, data=请求体 if 请求体 else None, timeout=实际超时)
            
            内容 = 响应.read()
            响应头 = _响应头转字典(响应.headers)
            
            return 响应(
                状态码=响应.status,
                响应头=响应头,
                内容=内容,
                请求地址=响应.geturl()
            )
        
        except urllib.error.HTTPError as e:
            内容 = e.read() if hasattr(e, 'read') else b''
            响应头 = _响应头转字典(e.headers) if e.headers else {}
            响应对象 = 响应(
                状态码=e.code,
                响应头=响应头,
                内容=内容,
                请求地址=完整地址
            )
            raise HTTP错误(f'HTTP错误: {e.code}', e.code, 响应对象)
        
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise 超时错误(f'请求超时: {e.reason}', e.reason)
            raise 连接错误(f'连接错误: {e.reason}', e.reason)
        
        except TimeoutError as e:
            raise 超时错误(f'请求超时: {e}', e)
        
        except Exception as e:
            raise 请求错误(f'请求失败: {e}', e)


def 编码URL(文本: str, 编码: str = 'utf-8') -> str:
    """URL编码"""
    return urllib.parse.quote(文本, encoding=编码)


def 解码URL(文本: str, 编码: str = 'utf-8') -> str:
    """URL解码"""
    return urllib.parse.unquote(文本, encoding=编码)


def 解析URL(地址: str) -> dict:
    """解析URL"""
    结果 = urllib.parse.urlparse(地址)
    return {
        '协议': 结果.scheme,
        '主机': 结果.hostname,
        '端口': 结果.port,
        '路径': 结果.path,
        '参数': 结果.params,
        '查询': 结果.query,
        '片段': 结果.fragment,
        '用户名': 结果.username,
        '密码': 结果.password
    }


def 拼接URL(基础: str, *片段: str) -> str:
    """拼接URL片段"""
    return urllib.parse.urljoin(基础, '/'.join(片段))


def 解析查询串(查询串: str) -> dict:
    """解析查询字符串"""
    结果 = urllib.parse.parse_qs(查询串)
    return {k: v[0] if len(v) == 1 else v for k, v in 结果.items()}


__all__ = [
    '响应', '请求错误', '超时错误', '连接错误', 'HTTP错误',
    'GET请求', 'POST请求', 'PUT请求', 'DELETE请求', 'PATCH请求',
    'HEAD请求', 'OPTIONS请求',
    '下载文件', '会话',
    '编码URL', '解码URL', '解析URL', '拼接URL', '解析查询串'
]