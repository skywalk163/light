# Socket

> TCP/UDP/Unix域套接字，阻塞与非阻塞模式

## 包信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 分类 | 网络通信 |
| 优先级 | 🔶 高频包（需新建桥接） |
| 公开函数 | 22 |
| FFI 声明 | 19 |
| 备注 | 需新建，基于 socket |

**关键词:** Socket, TCP, UDP, 网络, 套接字

## 导入方式

```duan
导入 Socket
```

或

```duan
导入 标准Socket
```

## 函数列表

共 22 个公开函数

> Socket — duanpub 桥接模块
> 
> 基于 Python socket 库封装，函数名对齐 duanpub/packages/Socket/源.duan。
> 
> duanpub 原始包通过 C FFI 直接调用 BSD Socket / WinSock2 API，
> 本桥接模块用 Python socket 模块替代，提供等价的 TCP/UDP 通信功能。

### 创建TCPSocket:

*暂无详细文档*

### 绑定(sock,地址,端口):

*暂无详细文档*

### 监听(sock,backlog):

*暂无详细文档*

### 接受(sock):

*暂无详细文档*

### 连接TCP(host,port):

*暂无详细文档*

### 发送(连接,数据):

*暂无详细文档*

### 接收(连接,最大长度):

*暂无详细文档*

### 设置非阻塞(sock,nonblocking):

*暂无详细文档*

### 创建UDPSocket:

*暂无详细文档*

### 绑定UDP(sock,地址,端口):

*暂无详细文档*

### 发送UDP(sock,数据,host,port):

*暂无详细文档*

### 接收UDP(sock,最大长度):

*暂无详细文档*

### 获取本地地址(sock):

*暂无详细文档*

### 获取远程地址(sock):

*暂无详细文档*

### select读写(可读列表,可写列表,超时秒):

*暂无详细文档*

### 获取错误信息(sock):

*暂无详细文档*

### 将主机名转为IP(主机名):

*暂无详细文档*

### 解析IP地址(ip):

*暂无详细文档*

### 主机转网络字节序(host):

*暂无详细文档*

### 网络转主机字节序(net):

*暂无详细文档*

### sock有效(sock):

*暂无详细文档*

### 连接有效(连接):

*暂无详细文档*
