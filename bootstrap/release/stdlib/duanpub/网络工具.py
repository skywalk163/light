"""
网络工具 — duanpub 桥接模块

基于 Python ipaddress / socket 库封装，函数名对齐 duanpub/packages/网络工具/源.duan。

duanpub 原始包通过 C FFI 直接调用系统网络 API，
本桥接模块用 Python ipaddress/socket 模块替代，提供等价的网络工具功能。
"""

import ipaddress as _ipaddress
import socket as _socket
import struct as _struct
import subprocess as _subprocess
import time as _time
import re as _re


# =============================================================================
# 内部函数（跳过）
# =============================================================================

# 内部2的幂 - 内部辅助函数，跳过
# 内部获取掩码整数 - 内部辅助函数，跳过
# 内部包含 - 内部辅助函数，跳过
# 内部分割 - 内部辅助函数，跳过
# 内部是否全数字 - 内部辅助函数，跳过
# 内部字符串转整数 - 内部辅助函数，跳过
# 内部整数转字符串 - 内部辅助函数，跳过


# =============================================================================
# IP地址解析与转换
# =============================================================================

def 解析IPv4(地址字符串):
    """解析IPv4地址为整数"""
    if not 地址字符串:
        raise Exception("解析IPv4失败: 地址为空")
    try:
        return _struct.unpack('!I', _socket.inet_aton(地址字符串))[0]
    except Exception as e:
        raise Exception("解析IPv4失败: " + str(e))


def 地址转字符串(地址):
    """将IP地址对象转为字符串"""
    return str(地址)


def 地址转整数(地址):
    """将IP地址字符串转为整数"""
    if not 地址:
        raise Exception("地址转整数失败: 地址为空")
    try:
        return int(_ipaddress.ip_address(地址))
    except Exception as e:
        raise Exception("地址转整数失败: " + str(e))


def 整数转地址(整数):
    """将整数转为IP地址字符串"""
    try:
        return str(_ipaddress.ip_address(整数))
    except Exception as e:
        raise Exception("整数转地址失败: " + str(e))


def 验证IPv4(地址):
    """验证是否为有效的IPv4地址"""
    if not 地址:
        return False
    try:
        _ipaddress.IPv4Address(地址)
        return True
    except Exception:
        return False


def 验证IPv6(地址):
    """验证是否为有效的IPv6地址"""
    if not 地址:
        return False
    try:
        _ipaddress.IPv6Address(地址)
        return True
    except Exception:
        return False


def 获取本地IP列表():
    """获取本地所有IP地址列表"""
    结果 = []
    try:
        hostname = _socket.gethostname()
        for info in _socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if addr not in 结果:
                结果.append(addr)
    except Exception:
        pass
    # 兜底：获取所有网络接口的IP
    if not 结果:
        try:
            import psutil as _psutil
            for name, addrs in _psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == _socket.AF_INET:
                        结果.append(addr.address)
        except ImportError:
            pass
    return 结果


def 是私有IP(地址):
    """判断是否为私有IP地址"""
    if not 地址:
        return False
    try:
        ip = _ipaddress.ip_address(地址)
        return ip.is_private
    except Exception:
        return False


def 是回环IP(地址):
    """判断是否为回环IP地址"""
    if not 地址:
        return False
    try:
        ip = _ipaddress.ip_address(地址)
        return ip.is_loopback
    except Exception:
        return False


def 是广播IP(地址):
    """判断是否为广播IP地址"""
    if not 地址:
        return False
    try:
        ip = _ipaddress.ip_address(地址)
        return ip.is_multicast  # 简化：广播地址不易判断
    except Exception:
        return False


def 是组播IP(地址):
    """判断是否为组播IP地址"""
    if not 地址:
        return False
    try:
        ip = _ipaddress.ip_address(地址)
        return ip.is_multicast
    except Exception:
        return False


# =============================================================================
# 子网计算
# =============================================================================

def 创建子网(地址, 前缀长度):
    """创建子网，返回子网对象"""
    if not 地址:
        raise Exception("创建子网失败: 地址为空")
    try:
        return _ipaddress.ip_network(f'{地址}/{前缀长度}', strict=False)
    except Exception as e:
        raise Exception("创建子网失败: " + str(e))


def 解析CIDR(CIDR字符串):
    """解析CIDR表示法，返回(网络地址, 前缀长度)"""
    if not CIDR字符串:
        raise Exception("解析CIDR失败: CIDR字符串为空")
    try:
        网络 = _ipaddress.ip_network(CIDR字符串, strict=False)
        return (str(网络.network_address), 网络.prefixlen)
    except Exception as e:
        raise Exception("解析CIDR失败: " + str(e))


def 子网包含IP(子网, IP地址):
    """判断子网是否包含指定IP"""
    if not 子网 or not IP地址:
        return False
    try:
        return IP地址 in 子网
    except Exception:
        try:
            return _ipaddress.ip_address(IP地址) in 子网
        except Exception:
            return False


def 子网分割(子网, 子网前缀长度):
    """将子网分割为更小的子网，返回子网列表"""
    if not 子网:
        raise Exception("子网分割失败: 子网为空")
    try:
        return list(子网.subnets(new_prefix=子网前缀长度))
    except Exception as e:
        raise Exception("子网分割失败: " + str(e))


def 获取子网掩码(子网):
    """获取子网掩码字符串"""
    if not 子网:
        raise Exception("获取子网掩码失败: 子网为空")
    return str(子网.netmask)


def 前缀长度到掩码(前缀长度):
    """将前缀长度转换为子网掩码字符串"""
    try:
        return str(_ipaddress.IPv4Network((0, 前缀长度), strict=False).netmask)
    except Exception as e:
        raise Exception("前缀长度到掩码失败: " + str(e))


def 掩码到前缀长度(掩码):
    """将子网掩码转换为前缀长度"""
    if not 掩码:
        raise Exception("掩码到前缀长度失败: 掩码为空")
    try:
        return _ipaddress.IPv4Network(f'0.0.0.0/{掩码}', strict=False).prefixlen
    except Exception as e:
        raise Exception("掩码到前缀长度失败: " + str(e))


# =============================================================================
# 端口扫描
# =============================================================================

def 扫描端口(主机, 端口, 超时秒=1):
    """扫描单个端口是否开放，返回True/False"""
    if not 主机:
        raise Exception("扫描端口失败: 主机为空")
    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(超时秒)
        result = sock.connect_ex((主机, 端口))
        sock.close()
        return result == 0
    except Exception:
        return False


def 扫描端口范围(主机, 起始端口, 结束端口, 超时秒=1):
    """扫描端口范围，返回开放端口列表"""
    if not 主机:
        raise Exception("扫描端口范围失败: 主机为空")
    开放端口 = []
    for port in range(起始端口, 结束端口 + 1):
        try:
            sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            sock.settimeout(超时秒)
            result = sock.connect_ex((主机, port))
            sock.close()
            if result == 0:
                开放端口.append(port)
        except Exception:
            continue
    return 开放端口


def 扫描常用端口(主机, 超时秒=1):
    """扫描常用服务端口，返回{端口: 服务名}字典"""
    if not 主机:
        raise Exception("扫描常用端口失败: 主机为空")
    常用端口 = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 445: 'SMB',
        993: 'IMAPS', 995: 'POP3S', 1433: 'MSSQL', 1521: 'Oracle',
        3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL', 6379: 'Redis',
        8080: 'HTTP-Proxy', 8443: 'HTTPS-Alt', 27017: 'MongoDB',
    }
    结果 = {}
    for port, name in 常用端口.items():
        if 扫描端口(主机, port, 超时秒):
            结果[port] = name
    return 结果


def 获取常用服务名称(端口):
    """获取常用端口对应的服务名称"""
    服务映射 = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 445: 'SMB',
        993: 'IMAPS', 995: 'POP3S', 1433: 'MSSQL', 1521: 'Oracle',
        3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL', 6379: 'Redis',
        8080: 'HTTP-Proxy', 8443: 'HTTPS-Alt', 27017: 'MongoDB',
    }
    return 服务映射.get(端口, '')


# =============================================================================
# Ping 与网络测试
# =============================================================================

def Ping主机(主机, 超时秒=2):
    """Ping主机，返回是否可达（布尔）"""
    if not 主机:
        raise Exception("Ping主机失败: 主机为空")
    try:
        import platform as _platform
        param = '-n' if _platform.system().lower() == 'windows' else '-c'
        result = _subprocess.run(
            ['ping', param, '1', '-w', str(int(超时秒 * 1000)), 主机],
            capture_output=True, text=True, timeout=超时秒 + 2
        )
        return result.returncode == 0
    except Exception:
        return False


def Ping主机多次(主机, 次数=4, 超时秒=2):
    """Ping主机多次，返回(成功次数, 平均延迟)"""
    if not 主机:
        raise Exception("Ping主机多次失败: 主机为空")
    成功次数 = 0
    总延迟 = 0.0
    for i in range(次数):
        try:
            start = _time.time()
            if Ping主机(主机, 超时秒):
                成功次数 += 1
                总延迟 += (_time.time() - start) * 1000
        except Exception:
            continue
    平均延迟 = 总延迟 / 成功次数 if 成功次数 > 0 else 0.0
    return (成功次数, 平均延迟)


def 获取主机名(主机=None):
    """获取主机名或IP对应的主机名"""
    try:
        if 主机:
            return _socket.gethostbyaddr(主机)[0]
        return _socket.gethostname()
    except Exception as e:
        raise Exception("获取主机名失败: " + str(e))


def 获取主机名地址(主机名):
    """获取主机名对应的IP地址"""
    if not 主机名:
        raise Exception("获取主机名地址失败: 主机名为空")
    try:
        return _socket.gethostbyname(主机名)
    except Exception as e:
        raise Exception("获取主机名地址失败: " + str(e))


def 检查网络连通性(主机='8.8.8.8', 超时秒=3):
    """检查网络连通性，返回True/False"""
    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(超时秒)
        result = sock.connect_ex((主机, 53))
        sock.close()
        return result == 0
    except Exception:
        return False


def Traceroute追踪(主机, 最大跳数=30, 超时秒=3):
    """Traceroute追踪路由，返回跳数列表"""
    if not 主机:
        raise Exception("Traceroute追踪失败: 主机为空")
    结果 = []
    try:
        dest_ip = _socket.gethostbyname(主机)
        for ttl in range(1, 最大跳数 + 1):
            recv_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_RAW, _socket.IPPROTO_ICMP)
            send_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM, _socket.IPPROTO_UDP)
            recv_sock.settimeout(超时秒)
            send_sock.setsockopt(_socket.IPPROTO_IP, _socket.IP_TTL, ttl)
            recv_sock.bind(('', 0))
            port = 33434 + ttl
            start = _time.time()
            send_sock.sendto(b'', (dest_ip, port))
            hop_addr = ''
            try:
                data, addr = recv_sock.recvfrom(512)
                elapsed = (_time.time() - start) * 1000
                hop_addr = addr[0] if addr else '*'
                结果.append({'跳数': ttl, '地址': hop_addr, '延迟': round(elapsed, 1)})
            except _socket.timeout:
                结果.append({'跳数': ttl, '地址': '*', '延迟': 0})
            finally:
                recv_sock.close()
                send_sock.close()
            if hop_addr == dest_ip:
                break
    except Exception:
        pass
    return 结果