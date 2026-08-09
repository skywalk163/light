"""
Socket — lightpub 桥接模块

基于 Python socket 库封装，函数名对齐 lightpub/packages/Socket/源.light。

lightpub 原始包通过 C FFI 直接调用 BSD Socket / WinSock2 API，
本桥接模块用 Python socket 模块替代，提供等价的 TCP/UDP 通信功能。
"""

import socket as _socket
import select as _select


# =============================================================================
# 常量（对齐 lightpub 源.light）
# =============================================================================

AF_INET = _socket.AF_INET
try:
    AF_UNIX = _socket.AF_UNIX
except AttributeError:
    AF_UNIX = AF_INET  # Windows 不支持 AF_UNIX
SOCK_STREAM = _socket.SOCK_STREAM
SOCK_DGRAM = _socket.SOCK_DGRAM


# =============================================================================
# 数据结构
# =============================================================================

class SocketHandle:
    """Socket 句柄"""
    def __init__(self, sock, domain=AF_INET, sock_type=SOCK_STREAM):
        self.句柄 = sock
        self.域 = domain
        self.类型 = sock_type
        self.已绑定 = False
        self.已监听 = False
        self.已连接 = False

    def fileno(self):
        return self.句柄.fileno() if self.句柄 else -1


class TCPConnection:
    """TCP 连接"""
    def __init__(self, sock, local_addr='', local_port=0, remote_addr='', remote_port=0):
        self.sock = sock
        self.本地地址 = local_addr
        self.本地端口 = local_port
        self.远程地址 = remote_addr
        self.远程端口 = remote_port


class UDPPacket:
    """UDP 数据包"""
    def __init__(self, data='', src_addr='', src_port=0):
        self.数据 = data
        self.来源地址 = src_addr
        self.来源端口 = src_port


class AcceptResult:
    """接受连接结果"""
    def __init__(self, connection=None, success=False, error_msg=''):
        self.连接 = connection
        self.成功 = success
        self.错误信息 = error_msg


class SelectResult:
    """select 结果"""
    def __init__(self, readable=None, writable=None):
        self.可读 = readable or []
        self.可写 = writable or []


# =============================================================================
# TCP 服务器函数
# =============================================================================

def 创建TCPSocket():
    """创建 TCP Socket，返回 SocketHandle"""
    try:
        sock = _socket.socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        return SocketHandle(sock, AF_INET, SOCK_STREAM)
    except Exception as e:
        raise Exception("创建TCPSocket失败: " + str(e))


def 绑定(sock, 地址, 端口):
    """绑定地址端口，返回 True/False"""
    if not sock or not sock.句柄:
        raise Exception("绑定失败: sock为空")
    if 端口 < 0 or 端口 > 65535:
        raise Exception("绑定失败: 端口号必须在0-65535之间")
    try:
        sock.句柄.bind((地址, 端口))
        sock.已绑定 = True
        return True
    except Exception as e:
        return False


def 监听(sock, backlog=10):
    """开始监听"""
    if not sock or not sock.句柄:
        raise Exception("监听失败: sock为空")
    if not sock.已绑定:
        raise Exception("监听失败: sock尚未绑定")
    sock.句柄.listen(backlog)
    sock.已监听 = True


def 接受(sock):
    """接受新连接，返回 AcceptResult"""
    if not sock or not sock.句柄:
        raise Exception("接受失败: sock为空")
    try:
        conn, addr = sock.句柄.accept()
        new_sock = SocketHandle(conn, sock.域, sock.类型)
        new_sock.已绑定 = True
        new_sock.已连接 = True
        connection = TCPConnection(new_sock, remote_addr=addr[0], remote_port=addr[1])
        return AcceptResult(connection, True, "")
    except Exception as e:
        return AcceptResult(None, False, str(e))


# =============================================================================
# TCP 客户端函数
# =============================================================================

def 连接TCP(host, port):
    """主动连接到 TCP 服务器，返回 TCPConnection"""
    if not host:
        raise Exception("连接TCP失败: host为空")
    if port < 1 or port > 65535:
        raise Exception("连接TCP失败: 端口号必须在1-65535之间")
    try:
        sock = _socket.socket(AF_INET, SOCK_STREAM)
        sock.connect((host, port))
        local_addr, local_port = sock.getsockname()
        sh = SocketHandle(sock, AF_INET, SOCK_STREAM)
        sh.已绑定 = True
        sh.已连接 = True
        return TCPConnection(sh, local_addr, local_port, host, port)
    except Exception as e:
        raise Exception("连接TCP失败: " + str(e))


# =============================================================================
# TCP 通信函数
# =============================================================================

def 发送(连接, 数据):
    """发送数据，返回发送字节数"""
    if not 连接 or not 连接.sock or not 连接.sock.句柄:
        raise Exception("发送失败: 连接为空")
    if not 连接.sock.已连接:
        raise Exception("发送失败: sock未连接")
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return 连接.sock.句柄.send(数据)


def 接收(连接, 最大长度):
    """接收数据，返回字符串"""
    if not 连接 or not 连接.sock or not 连接.sock.句柄:
        raise Exception("接收失败: 连接为空")
    if 最大长度 <= 0:
        raise Exception("接收失败: 最大长度必须大于0")
    data = 连接.sock.句柄.recv(最大长度)
    try:
        return data.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return data


def 关闭连接(连接):
    """关闭 TCP 连接"""
    if not 连接:
        return
    if 连接.sock and 连接.sock.句柄:
        try:
            连接.sock.句柄.close()
        except Exception:
            pass
        连接.sock.句柄 = None
        连接.sock.已连接 = False


def 设置非阻塞(sock, nonblocking=True):
    """设置非阻塞模式"""
    if not sock or not sock.句柄:
        raise Exception("设置非阻塞失败: sock为空")
    sock.句柄.setblocking(not nonblocking)


# =============================================================================
# UDP 函数
# =============================================================================

def 创建UDPSocket():
    """创建 UDP Socket"""
    try:
        sock = _socket.socket(AF_INET, SOCK_DGRAM)
        return SocketHandle(sock, AF_INET, SOCK_DGRAM)
    except Exception as e:
        raise Exception("创建UDPSocket失败: " + str(e))


def 绑定UDP(sock, 地址, 端口):
    """绑定 UDP 地址端口"""
    if not sock or not sock.句柄:
        raise Exception("绑定UDP失败: sock为空")
    try:
        sock.句柄.bind((地址, 端口))
        sock.已绑定 = True
        return True
    except Exception:
        return False


def 发送UDP(sock, 数据, host, port):
    """发送 UDP 数据包"""
    if not sock or not sock.句柄:
        raise Exception("发送UDP失败: sock为空")
    if isinstance(数据, str):
        数据 = 数据.encode('utf-8')
    return sock.句柄.sendto(数据, (host, port))


def 接收UDP(sock, 最大长度):
    """接收 UDP 数据包，返回 UDPPacket"""
    if not sock or not sock.句柄:
        raise Exception("接收UDP失败: sock为空")
    data, addr = sock.句柄.recvfrom(最大长度)
    try:
        data = data.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        pass
    return UDPPacket(data, addr[0], addr[1])


# =============================================================================
# 工具函数
# =============================================================================

def 获取本地地址(sock):
    """获取本地地址和端口"""
    if not sock or not sock.句柄:
        raise Exception("获取本地地址失败: sock为空")
    addr, port = sock.句柄.getsockname()
    return (addr, port)


def 获取远程地址(sock):
    """获取远程地址和端口"""
    if not sock or not sock.句柄:
        raise Exception("获取远程地址失败: sock为空")
    try:
        addr, port = sock.句柄.getpeername()
        return (addr, port)
    except Exception:
        return ("", 0)


def select读写(可读列表, 可写列表, 超时秒):
    """select 多路复用"""
    read_fds = [s.句柄 if hasattr(s, '句柄') else s for s in (可读列表 or [])]
    write_fds = [s.句柄 if hasattr(s, '句柄') else s for s in (可写列表 or [])]
    if not read_fds and not write_fds:
        raise Exception("select读写失败: 可读列表和可写列表不能同时为空")
    r, w, _ = _select.select(read_fds, write_fds, [], 超时秒)
    return SelectResult(r, w)


def 获取错误信息(sock):
    """获取 sock 最后错误信息"""
    if not sock or not sock.句柄:
        return "sock已关闭"
    return str(sock.句柄.getsockopt(_socket.SOL_SOCKET, _socket.SO_ERROR))


def 将主机名转为IP(主机名):
    """将主机名转为 IP 地址字符串"""
    if not 主机名:
        raise Exception("将主机名转为IP失败: 主机名为空")
    try:
        return _socket.gethostbyname(主机名)
    except Exception:
        raise Exception("将主机名转为IP失败: 无法解析主机名 " + 主机名)


def 解析IP地址(ip):
    """解析 IP 地址为整数"""
    if not ip:
        raise Exception("解析IP地址失败: ip为空")
    try:
        return _socket.inet_aton(ip)
    except Exception:
        raise Exception("解析IP地址失败: 无效的IP地址 " + ip)


def 主机转网络字节序(host):
    """主机字节序转网络字节序"""
    return _socket.htonl(host)


def 网络转主机字节序(net):
    """网络字节序转主机字节序"""
    return _socket.ntohl(net)


def sock有效(sock):
    """判断 sock 是否有效"""
    if not sock:
        return False
    return sock.句柄 is not None


def 连接有效(连接):
    """判断连接是否有效"""
    if not 连接 or not 连接.sock:
        return False
    return sock有效(连接.sock)


def 关闭Socket(sock):
    """关闭 Socket"""
    if not sock:
        return
    if sock.句柄:
        try:
            sock.句柄.close()
        except Exception:
            pass
        sock.句柄 = None
        sock.已绑定 = False
        sock.已监听 = False
        sock.已连接 = False
