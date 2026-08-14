# Socket API

> 模块路径：`stdlib/Socket.py`
> 导入方式：`从 Socket 导入 函数名` 或 `导入 Socket`

---

## 函数列表

| 函数 | 说明 |
|------|------|
| `创建TCPSocket()` | 创建 TCP Socket，返回 SocketHandle |
| `绑定(sock, 地址, 端口)` | 绑定地址端口，返回 True/False |
| `监听(sock, backlog)` | 开始监听 |
| `接受(sock)` | 接受新连接，返回 AcceptResult |
| `连接TCP(host, port)` | 主动连接到 TCP 服务器，返回 TCPConnection |
| `发送(连接, 数据)` | 发送数据，返回发送字节数 |
| `接收(连接, 最大长度)` | 接收数据，返回字符串 |
| `关闭连接(连接)` | 关闭 TCP 连接 |
| `设置非阻塞(sock, nonblocking)` | 设置非阻塞模式 |
| `创建UDPSocket()` | 创建 UDP Socket |
| `绑定UDP(sock, 地址, 端口)` | 绑定 UDP 地址端口 |
| `发送UDP(sock, 数据, host, port)` | 发送 UDP 数据包 |
| `接收UDP(sock, 最大长度)` | 接收 UDP 数据包，返回 UDPPacket |
| `获取本地地址(sock)` | 获取本地地址和端口 |
| `获取远程地址(sock)` | 获取远程地址和端口 |
| `select读写(可读列表, 可写列表, 超时秒)` | select 多路复用 |
| `获取错误信息(sock)` | 获取 sock 最后错误信息 |
| `将主机名转为IP(主机名)` | 将主机名转为 IP 地址字符串 |
| `解析IP地址(ip)` | 解析 IP 地址为整数 |
| `主机转网络字节序(host)` | 主机字节序转网络字节序 |
| `网络转主机字节序(net)` | 网络字节序转主机字节序 |
| `sock有效(sock)` | 判断 sock 是否有效 |
| `连接有效(连接)` | 判断连接是否有效 |
| `关闭Socket(sock)` | 关闭 Socket |
| `__init__(self, sock, domain, sock_type)` |  |
| `fileno(self)` |  |
| `__init__(self, sock, local_addr, local_port, remote_addr, remote_port)` |  |
| `__init__(self, data, src_addr, src_port)` |  |
| `__init__(self, connection, success, error_msg)` |  |
| `__init__(self, readable, writable)` |  |

---

## 函数详情

### `创建TCPSocket()`

创建 TCP Socket，返回 SocketHandle

**参数：**

无参数。

---

### `绑定(sock, 地址, 端口)`

绑定地址端口，返回 True/False

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `地址` | `None` |  |
| `端口` | `None` |  |

---

### `监听(sock, backlog = 10)`

开始监听

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `backlog` | `None` | （默认：10） |

---

### `接受(sock)`

接受新连接，返回 AcceptResult

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `连接TCP(host, port)`

主动连接到 TCP 服务器，返回 TCPConnection

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `host` | `None` |  |
| `port` | `None` |  |

---

### `发送(连接, 数据)`

发送数据，返回发送字节数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `连接` | `None` |  |
| `数据` | `None` |  |

---

### `接收(连接, 最大长度)`

接收数据，返回字符串

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `连接` | `None` |  |
| `最大长度` | `None` |  |

---

### `关闭连接(连接)`

关闭 TCP 连接

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `连接` | `None` |  |

---

### `设置非阻塞(sock, nonblocking = True)`

设置非阻塞模式

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `nonblocking` | `None` | （默认：True） |

---

### `创建UDPSocket()`

创建 UDP Socket

**参数：**

无参数。

---

### `绑定UDP(sock, 地址, 端口)`

绑定 UDP 地址端口

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `地址` | `None` |  |
| `端口` | `None` |  |

---

### `发送UDP(sock, 数据, host, port)`

发送 UDP 数据包

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `数据` | `None` |  |
| `host` | `None` |  |
| `port` | `None` |  |

---

### `接收UDP(sock, 最大长度)`

接收 UDP 数据包，返回 UDPPacket

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |
| `最大长度` | `None` |  |

---

### `获取本地地址(sock)`

获取本地地址和端口

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `获取远程地址(sock)`

获取远程地址和端口

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `select读写(可读列表, 可写列表, 超时秒)`

select 多路复用

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `可读列表` | `None` |  |
| `可写列表` | `None` |  |
| `超时秒` | `None` |  |

---

### `获取错误信息(sock)`

获取 sock 最后错误信息

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `将主机名转为IP(主机名)`

将主机名转为 IP 地址字符串

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `主机名` | `None` |  |

---

### `解析IP地址(ip)`

解析 IP 地址为整数

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `ip` | `None` |  |

---

### `主机转网络字节序(host)`

主机字节序转网络字节序

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `host` | `None` |  |

---

### `网络转主机字节序(net)`

网络字节序转主机字节序

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `net` | `None` |  |

---

### `sock有效(sock)`

判断 sock 是否有效

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `连接有效(连接)`

判断连接是否有效

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `连接` | `None` |  |

---

### `关闭Socket(sock)`

关闭 Socket

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sock` | `None` |  |

---

### `__init__(self, sock, domain = AF_INET, sock_type = SOCK_STREAM)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `sock` | `None` |  |
| `domain` | `None` | （默认：AF_INET） |
| `sock_type` | `None` | （默认：SOCK_STREAM） |

---

### `fileno(self)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |

---

### `__init__(self, sock, local_addr = '', local_port = 0, remote_addr = '', remote_port = 0)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `sock` | `None` |  |
| `local_addr` | `None` | （默认：''） |
| `local_port` | `None` | （默认：0） |
| `remote_addr` | `None` | （默认：''） |
| `remote_port` | `None` | （默认：0） |

---

### `__init__(self, data = '', src_addr = '', src_port = 0)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `data` | `None` | （默认：''） |
| `src_addr` | `None` | （默认：''） |
| `src_port` | `None` | （默认：0） |

---

### `__init__(self, connection = None, success = False, error_msg = '')`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `connection` | `None` | （默认：None） |
| `success` | `None` | （默认：False） |
| `error_msg` | `None` | （默认：''） |

---

### `__init__(self, readable = None, writable = None)`

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `self` | `None` |  |
| `readable` | `None` | （默认：None） |
| `writable` | `None` | （默认：None） |

---

## 常量

| 常量名 | 值 |
|--------|-----|
| `AF_INET` | `_socket.AF_INET` |
| `SOCK_STREAM` | `_socket.SOCK_STREAM` |
| `SOCK_DGRAM` | `_socket.SOCK_DGRAM` |
| `AF_UNIX` | `_socket.AF_UNIX` |
| `data` | `连接.sock.句柄.recv(最大长度)` |
| `read_fds` | `[s.句柄 if hasattr(s, '句柄') else s for s in 可读列表 or []]` |
| `write_fds` | `[s.句柄 if hasattr(s, '句柄') else s for s in 可写列表 or []]` |
| `AF_UNIX` | `AF_INET` |
| `sock` | `_socket.socket(AF_INET, SOCK_STREAM)` |
| `new_sock` | `SocketHandle(conn, sock.域, sock.类型)` |
| `connection` | `TCPConnection(new_sock, remote_addr=addr[0], remote_port=addr[1])` |
| `sock` | `_socket.socket(AF_INET, SOCK_STREAM)` |
| `sh` | `SocketHandle(sock, AF_INET, SOCK_STREAM)` |
| `数据` | `数据.encode('utf-8')` |
| `sock` | `_socket.socket(AF_INET, SOCK_DGRAM)` |
| `数据` | `数据.encode('utf-8')` |
| `data` | `data.decode('utf-8')` |
