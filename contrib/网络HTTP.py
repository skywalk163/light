"""
光明标准库 - 网络HTTP模块

提供 HTTP 客户端函数
"""

import urllib.request
import urllib.parse
import json
from typing import Any, Dict, Optional, Union


def HTTP获取(url: str, 超时: int = 30) -> str:
    """GET 请求"""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=超时) as resp:
        return resp.read().decode('utf-8')


def HTTP发送(url: str, 方法: str = 'POST', 数据=None, 头: Optional[Dict[str, str]] = None) -> str:
    """发送 HTTP 请求（POST/PUT/PATCH/DELETE）"""
    if isinstance(数据, dict):
        data_bytes = json.dumps(数据).encode('utf-8')
    elif isinstance(数据, str):
        data_bytes = 数据.encode('utf-8')
    else:
        data_bytes = 数据

    req = urllib.request.Request(url, data=data_bytes, method=方法.upper())
    if 头:
        for key, value in 头.items():
            req.add_header(key, value)
    if data_bytes and 'Content-Type' not in (头 or {}):
        req.add_header('Content-Type', 'application/json')

    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')


def HTTP解析JSON(url: str, 超时: int = 30) -> Any:
    """GET 请求并解析 JSON 响应"""
    text = HTTP获取(url, 超时)
    return json.loads(text)


def 编码网址(s: str) -> str:
    """URL 编码"""
    return urllib.parse.quote(s)


def 解码网址(s: str) -> str:
    """URL 解码"""
    return urllib.parse.unquote(s)