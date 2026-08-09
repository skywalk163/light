# -*- coding: utf-8 -*-
"""
光明标准库 - 网络工具模块

提供网络相关工具函数，包括 URL 解析、IP 地址检查、端口检查等。
"""

import socket
import urllib.parse
import ipaddress
from typing import Optional, List, Tuple


def URL解析(url: str) -> dict:
    """
    解析 URL 为各组成部分

    参数:
        url: 完整 URL 字符串

    返回:
        包含各组成部分的字典

    示例:
        URL解析('https://example.com:8080/path?a=1#top')
    """
    解析结果 = urllib.parse.urlparse(url)
    return {
        '协议': 解析结果.scheme,
        '主机': 解析结果.hostname,
        '端口': 解析结果.port,
        '路径': 解析结果.path,
        '查询': 解析结果.query,
        '片段': 解析结果.fragment,
        '用户名': 解析结果.username,
        '密码': 解析结果.password,
    }


def URL编码(字符串: str) -> str:
    """URL 编码字符串"""
    return urllib.parse.quote(字符串)


def URL解码(字符串: str) -> str:
    """URL 解码字符串"""
    return urllib.parse.unquote(字符串)


def URL拼接(基础URL: str, 相对路径: str) -> str:
    """拼接基础 URL 和相对路径"""
    return urllib.parse.urljoin(基础URL, 相对路径)


def URL构建查询(参数: dict) -> str:
    """构建 URL 查询参数字符串"""
    return urllib.parse.urlencode(参数)


def URL解析查询(查询字符串: str) -> dict:
    """解析 URL 查询参数字符串为字典"""
    return dict(urllib.parse.parse_qsl(查询字符串))


def IP地址检查(地址: str) -> bool:
    """
    检查字符串是否为有效的 IP 地址

    参数:
        地址: IP 地址字符串

    返回:
        是否为有效 IP 地址
    """
    try:
        ipaddress.ip_address(地址)
        return True
    except ValueError:
        return False


def IPv4地址检查(地址: str) -> bool:
    """
    检查字符串是否为有效的 IPv4 地址

    参数:
        地址: IPv4 地址字符串

    返回:
        是否为有效 IPv4 地址
    """
    try:
        ipaddress.IPv4Address(地址)
        return True
    except ValueError:
        return False


def IPv6地址检查(地址: str) -> bool:
    """
    检查字符串是否为有效的 IPv6 地址

    参数:
        地址: IPv6 地址字符串

    返回:
        是否为有效 IPv6 地址
    """
    try:
        ipaddress.IPv6Address(地址)
        return True
    except ValueError:
        return False


def IP地址类型(地址: str) -> str:
    """
    返回 IP 地址类型

    参数:
        地址: IP 地址字符串

    返回:
        地址类型（'IPv4', 'IPv6', '无效'）
    """
    try:
        ip = ipaddress.ip_address(地址)
        return 'IPv4' if isinstance(ip, ipaddress.IPv4Address) else 'IPv6'
    except ValueError:
        return '无效'


def IP地址信息(地址: str) -> dict:
    """
    获取 IP 地址的详细信息

    参数:
        地址: IP 地址字符串

    返回:
        包含地址类型、是否为私有地址等信息的字典
    """
    try:
        ip = ipaddress.ip_address(地址)
        return {
            '有效': True,
            '类型': 'IPv4' if isinstance(ip, ipaddress.IPv4Address) else 'IPv6',
            '版本': ip.version,
            '压缩格式': str(ip),
            '是否为私有': ip.is_private if hasattr(ip, 'is_private') else False,
            '是否为环回': ip.is_loopback if hasattr(ip, 'is_loopback') else False,
            '是否为多播': ip.is_multicast if hasattr(ip, 'is_multicast') else False,
            '是否为全局': ip.is_global if hasattr(ip, 'is_global') else False,
        }
    except ValueError:
        return {'有效': False, '类型': '无效'}


def 端口检查(主机: str, 端口: int, 超时: float = 3.0) -> bool:
    """
    检查指定主机的端口是否开放

    参数:
        主机: 主机名或 IP 地址
        端口: 端口号
        超时: 超时秒数（默认3）

    返回:
        端口是否开放
    """
    try:
        with socket.create_connection((主机, 端口), timeout=超时):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def 端口扫描(主机: str, 起始端口: int, 结束端口: int, 超时: float = 1.0) -> List[int]:
    """
    扫描指定范围内的开放端口

    参数:
        主机: 主机名或 IP 地址
        起始端口: 起始端口号
        结束端口: 结束端口号（包含）
        超时: 单个端口超时秒数

    返回:
        开放端口列表
    """
    开放端口 = []
    for 端口 in range(起始端口, 结束端口 + 1):
        if 端口检查(主机, 端口, 超时):
            开放端口.append(端口)
    return 开放端口


def 主机名解析(主机名: str) -> Optional[str]:
    """
    解析主机名为 IP 地址

    参数:
        主机名: 主机名（如 'example.com'）

    返回:
        IP 地址字符串，失败返回 None
    """
    try:
        return socket.gethostbyname(主机名)
    except socket.gaierror:
        return None


def 主机名解析全部(主机名: str) -> List[str]:
    """
    解析主机名为所有 IP 地址

    参数:
        主机名: 主机名

    返回:
        IP 地址列表
    """
    try:
        info = socket.getaddrinfo(主机名, None)
        return list(set(addr[4][0] for addr in info))
    except socket.gaierror:
        return []


def 反向DNS(IP地址: str) -> Optional[str]:
    """
    反向 DNS 解析：IP 地址转主机名

    参数:
        IP地址: IP 地址字符串

    返回:
        主机名，失败返回 None
    """
    try:
        主机名, _, _ = socket.gethostbyaddr(IP地址)
        return 主机名
    except (socket.herror, socket.gaierror):
        return None


def 本机主机名() -> str:
    """获取本机主机名"""
    return socket.gethostname()


def 本机IP地址() -> List[str]:
    """
    获取本机所有 IP 地址

    返回:
        IP 地址列表
    """
    try:
        主机名 = socket.gethostname()
        info = socket.getaddrinfo(主机名, None)
        IP集合 = set()
        for addr in info:
            IP = addr[4][0]
            if not IP.startswith('127.'):
                IP集合.add(IP)
        return list(IP集合)
    except Exception:
        return []


def 网络字节序转整数(数据: bytes) -> int:
    """网络字节序字节数据转整数"""
    return int.from_bytes(数据, byteorder='big')


def 整数转网络字节序(值: int, 长度: int = 4) -> bytes:
    """整数转网络字节序字节数据"""
    return 值.to_bytes(长度, byteorder='big')


__all__ = [
    'URL解析', 'URL编码', 'URL解码', 'URL拼接',
    'URL构建查询', 'URL解析查询',
    'IP地址检查', 'IPv4地址检查', 'IPv6地址检查',
    'IP地址类型', 'IP地址信息',
    '端口检查', '端口扫描',
    '主机名解析', '主机名解析全部', '反向DNS',
    '本机主机名', '本机IP地址',
    '网络字节序转整数', '整数转网络字节序',
]