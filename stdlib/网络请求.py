# -*- coding: utf-8 -*-
"""
简单 HTTP 网络请求工具

提供 GET、POST、PUT、DELETE 等常用 HTTP 请求封装。

用法:
    from 标准库.网络请求 import 获取, 发送, 发起请求

示例:
    设 响应 = 获取("https://api.example.com/data")
    打印(响应.状态码)
    打印(响应.文本())
"""

import json as _json
import urllib.request as _request
import urllib.parse as _parse
import urllib.error as _error
from http.client import HTTPResponse as _HTTPResponse
from typing import Optional, Dict, Any, Union


class HTTP响应:
    """HTTP 响应封装类

    Attributes:
        状态码: HTTP 状态码
        头部: 响应头字典
        内容: 原始响应内容（字节）
        编码: 响应编码
    """

    def __init__(self, 响应对象: _HTTPResponse):
        """初始化响应对象

        Args:
            响应对象: urllib 的 HTTPResponse 对象
        """
        self.状态码: int = 响应对象.status
        self.头部: Dict[str, str] = dict(响应对象.getheaders())
        self.内容: bytes = 响应对象.read()
        self.编码: str = 响应对象.headers.get_content_charset() or "utf-8"
        响应对象.close()

    def 文本(self, 编码: Optional[str] = None) -> str:
        """获取响应文本内容

        Args:
            编码: 指定编码，默认使用响应头中的编码或 UTF-8

        Returns:
            解码后的文本字符串
        """
        return self.内容.decode(编码 or self.编码, errors="replace")

    def JSON(self) -> Any:
        """将响应内容解析为 JSON

        Returns:
            JSON 解析后的 Python 对象

        Raises:
            ValueError: 如果响应内容不是有效的 JSON
        """
        return _json.loads(self.文本())

    def 成功(self) -> bool:
        """检查请求是否成功（状态码 200-299）

        Returns:
            如果状态码在 200-299 之间返回 True
        """
        return 200 <= self.状态码 < 300


def _创建请求(
    url: str,
    方法: str = "GET",
    头部: Optional[Dict[str, str]] = None,
    数据: Any = None,
    超时: int = 30
) -> _request.Request:
    """创建 HTTP 请求对象

    Args:
        url: 请求 URL
        方法: HTTP 方法
        头部: 请求头字典
        数据: 请求体数据（字典或字符串）
        超时: 超时时间（秒）

    Returns:
        urllib Request 对象
    """
    if 数据 is not None and isinstance(数据, dict):
        数据 = _parse.urlencode(数据).encode("utf-8")
    elif 数据 is not None and isinstance(数据, str):
        数据 = 数据.encode("utf-8")

    req = _request.Request(url, data=数据, method=方法)

    # 设置默认头部
    req.add_header("User-Agent", "DuanLang-HTTP-Client/1.0")
    req.add_header("Accept", "*/*")

    if 头部:
        for key, value in 头部.items():
            req.add_header(key, value)

    return req


def 发起请求(
    url: str,
    方法: str = "GET",
    头部: Optional[Dict[str, str]] = None,
    数据: Any = None,
    超时: int = 30
) -> HTTP响应:
    """发起 HTTP 请求

    Args:
        url: 请求 URL
        方法: HTTP 方法（GET, POST, PUT, DELETE 等）
        头部: 请求头字典
        数据: 请求体数据
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象

    Raises:
        HTTPError: 如果请求失败（自动包装）
        URLError: 如果 URL 无效
        TimeoutError: 如果请求超时

    示例:
        >>> 响应 = 发起请求("https://api.example.com", "GET")
        >>> 打印(响应.文本())
    """
    try:
        req = _创建请求(url, 方法, 头部, 数据, 超时)
        response = _request.urlopen(req, timeout=超时)
        return HTTP响应(response)
    except _error.HTTPError as e:
        # 即使有 HTTP 错误，也返回响应对象
        return HTTP响应(e)
    except _error.URLError as e:
        raise ConnectionError(f"无法连接到 {url}: {e.reason}")
    except _request.socket.timeout:
        raise TimeoutError(f"请求超时: {url}")


def 获取(url: str, 头部: Optional[Dict[str, str]] = None, 超时: int = 30) -> HTTP响应:
    """发送 GET 请求

    Args:
        url: 请求 URL
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象
    """
    return 发起请求(url, "GET", 头部, None, 超时)


def 发送(
    url: str,
    方法: str = "POST",
    数据: Any = None,
    头部: Optional[Dict[str, str]] = None,
    超时: int = 30,
    是JSON: bool = False
) -> HTTP响应:
    """发送 POST、PUT、PATCH 等请求

    Args:
        url: 请求 URL
        方法: HTTP 方法（POST, PUT, PATCH, DELETE）
        数据: 请求体数据
        头部: 请求头字典
        超时: 超时时间（秒）
        是JSON: 是否以 JSON 格式发送数据

    Returns:
        HTTP响应 对象

    示例:
        >>> 发送("https://api.example.com/data", "POST", {"key": "value"}, 是JSON=True)
    """
    if 是JSON and 数据 is not None:
        if 头部 is None:
            头部 = {}
        头部["Content-Type"] = "application/json"
        数据 = _json.dumps(数据, ensure_ascii=False)

    return 发起请求(url, 方法, 头部, 数据, 超时)


def POST(url: str, 数据: Any = None, 头部: Optional[Dict[str, str]] = None, 超时: int = 30) -> HTTP响应:
    """发送 POST 请求（便捷函数）

    Args:
        url: 请求 URL
        数据: 请求体数据
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象
    """
    return 发送(url, "POST", 数据, 头部, 超时)


def PUT(url: str, 数据: Any = None, 头部: Optional[Dict[str, str]] = None, 超时: int = 30) -> HTTP响应:
    """发送 PUT 请求（便捷函数）

    Args:
        url: 请求 URL
        数据: 请求体数据
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象
    """
    return 发送(url, "PUT", 数据, 头部, 超时)


def 删除(url: str, 头部: Optional[Dict[str, str]] = None, 超时: int = 30) -> HTTP响应:
    """发送 DELETE 请求（便捷函数）

    Args:
        url: 请求 URL
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象
    """
    return 发起请求(url, "DELETE", 头部, None, 超时)


def 获取JSON(url: str, 头部: Optional[Dict[str, str]] = None, 超时: int = 30) -> Any:
    """发送 GET 请求并解析 JSON 响应

    Args:
        url: 请求 URL
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        JSON 解析后的数据

    Raises:
        ValueError: 如果响应不是有效的 JSON
    """
    return 获取(url, 头部, 超时).JSON()


def 发送JSON(
    url: str,
    方法: str = "POST",
    数据: Any = None,
    头部: Optional[Dict[str, str]] = None,
    超时: int = 30
) -> HTTP响应:
    """以 JSON 格式发送请求

    Args:
        url: 请求 URL
        方法: HTTP 方法
        数据: 将被序列化为 JSON 的数据
        头部: 请求头字典
        超时: 超时时间（秒）

    Returns:
        HTTP响应 对象
    """
    return 发送(url, 方法, 数据, 头部, 超时, 是JSON=True)


def 下载文件(url: str, 保存路径: str, 超时: int = 60) -> str:
    """下载文件到本地

    Args:
        url: 文件 URL
        保存路径: 本地保存路径
        超时: 超时时间（秒）

    Returns:
        保存的文件路径

    Raises:
        ConnectionError: 如果下载失败
    """
    try:
        response = 获取(url, 超时=超时)
        with open(保存路径, "wb") as f:
            f.write(response.内容)
        return 保存路径
    except Exception as e:
        raise ConnectionError(f"下载文件失败: {e}")


# ===== 异常类 =====
class 请求错误(Exception):
    """请求错误基类"""
    pass


class 超时错误(请求错误):
    """请求超时错误"""
    pass


class 连接错误(请求错误):
    """连接错误"""
    pass


class HTTP错误(请求错误):
    """HTTP 错误响应"""
    def __init__(self, 状态码: int, 消息: str = ""):
        self.状态码 = 状态码
        self.消息 = 消息
        super().__init__(f"HTTP {状态码}: {消息}")


# ===== 响应类增强（兼容测试） =====
class 响应:
    """HTTP 响应类（兼容直接构造和 urllib 构造）"""

    def __init__(self, 状态码: int = 200, 响应头: Optional[Dict[str, str]] = None,
                 内容: bytes = b'', 请求地址: str = ''):
        self.状态码 = 状态码
        self.头部 = 响应头 or {}
        self.内容 = 内容
        self.请求地址 = 请求地址

    @property
    def 是否成功(self) -> bool:
        """是否成功（状态码 200-299）"""
        return 200 <= self.状态码 < 300

    def 获取头(self, 名称: str, 默认: str = '') -> str:
        """获取响应头"""
        return self.头部.get(名称, 默认) if isinstance(self.头部, dict) else 默认

    @property
    def 文本(self) -> str:
        """获取文本内容"""
        return self.内容.decode('utf-8', errors='replace')

    def JSON(self) -> Any:
        """解析 JSON 响应"""
        return _json.loads(self.文本)

    def 成功(self) -> bool:
        """检查是否成功"""
        return self.是否成功


# ===== URL 工具函数 =====
def 编码URL(文本: str) -> str:
    """URL 编码"""
    return _parse.quote(文本, safe='')


def 解码URL(编码文本: str) -> str:
    """URL 解码"""
    return _parse.unquote(编码文本)


def 解析URL(url: str) -> Dict[str, Any]:
    """解析 URL 为各组成部分"""
    from urllib.parse import urlparse
    解析结果 = urlparse(url)
    return {
        '协议': 解析结果.scheme,
        '主机': 解析结果.hostname or '',
        '端口': 解析结果.port or 80,
        '路径': 解析结果.path,
        '查询': 解析结果.query,
        '片段': 解析结果.fragment,
    }


def 拼接URL(*部分: str) -> str:
    """拼接 URL 路径"""
    from urllib.parse import urljoin
    结果 = 部分[0]
    for p in 部分[1:]:
        结果 = urljoin(结果.rstrip('/') + '/', p.lstrip('/'))
    return 结果


def 解析查询串(查询字符串: str) -> Dict[str, str]:
    """解析查询字符串为字典"""
    from urllib.parse import parse_qs
    结果 = parse_qs(查询字符串)
    return {k: v[0] for k, v in 结果.items()}


def 构建URL(基础URL: str, 参数: Optional[Dict[str, str]] = None) -> str:
    """构建带查询参数的 URL

    Args:
        基础URL: URL 基础地址
        参数: 查询参数字典

    Returns:
        完整的 URL 字符串

    示例:
        >>> 构建URL("https://api.example.com/search", {"q": "段言", "page": "1"})
        'https://api.example.com/search?q=%E6%AE%B5%E8%A8%80&page=1'
    """
    if not 参数:
        return 基础URL

    查询字符串 = _parse.urlencode(参数, encoding="utf-8")
    分隔符 = "&" if "?" in 基础URL else "?"
    return f"{基础URL}{分隔符}{查询字符串}"