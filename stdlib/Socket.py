# -*- coding: utf-8 -*-
"""
光明标准库 - Socket 网络通信模块（顶层路由）

## 为什么存在这个文件（R155 立项，L-215）

`导入 Socket` 在 Windows 上失败、在 FreeBSD 上成功，属**平台特有的路由误判**：

`src/code_generator.py::_resolve_lightpub_import` 对 P1/P2 包有“根目录同名优先”
规则，靠 `_stdlib_root_has(name)` 探测 `stdlib/<name>.py|.light` 是否存在。
但 `Socket` 的实现在 `stdlib/lightpub/Socket.py`，根目录**没有** `Socket.py`
（只有小写的 `socket.light`，那是另一套东西）。

- FreeBSD：文件名严格区分大小写 ⇒ `Socket.light` 不存在 ⇒ 判定 False
  ⇒ 正确路由到 `stdlib.lightpub.Socket` ⇒ 测试通过；
- Windows：文件系统**大小写不敏感** ⇒ `Socket.light` 命中了 `socket.light`
  ⇒ 误判为 True ⇒ 返回裸名 `Socket` ⇒ `import Socket` 找不到 ⇒ 测试红。

即：`docs/lightpub/Socket.md` 里 `导入 Socket` / `导入 标准Socket` 两个光明围栏
在 Windows 上是**谎言**（文档承诺“这样写就能用”，实际导不进）。

本文件是顶层路由：让 `Socket` 这个名字在根目录真实存在，两个平台都走
`import Socket` ⇒ 拿到本模块。这样路由判断不再依赖文件系统的大小写行为。

## 实现方式：re-export，不复制

函数体一律 re-export `stdlib/lightpub/Socket.py` 的**同一份实现**，不在此处
复制代码 —— 复制会让两个实现随时间长歪（lightpub 那边改了、这边忘了跟），
而“单一实现源”是本仓既有纪律（见 `tools/lightpub_importability.py` 的单点原则）。

## 与 `socket.light` 的关系

不冲突、也不互相替代：

| 名字 | 位置 | 性质 |
|---|---|---|
| `socket.light` | `stdlib/socket.light` | 纯光明模块（原生腿可用，走 C 原语） |
| `Socket`（本文件） | `stdlib/Socket.py` | lightpub 桥接包的顶层路由（Python 腿） |

两者扩展名不同，在大小写不敏感的文件系统上也能共存。
"""

import os as _os
import sys as _sys

# 确保 stdlib 可导入（本文件就在 stdlib/ 下，其父目录需在 path 上）
_STDLIB_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _STDLIB_DIR not in _sys.path:
    _sys.path.append(_STDLIB_DIR)

from lightpub.Socket import (  # noqa: E402
    AF_INET,
    AF_UNIX,
    SOCK_STREAM,
    SOCK_DGRAM,
    # 创建 / 绑定 / 监听 / 接受
    创建TCPSocket,
    创建UDPSocket,
    绑定,
    绑定UDP,
    监听,
    接受,
    # 连接 / 收发
    连接TCP,
    发送,
    发送UDP,
    接收,
    接收UDP,
    关闭连接,
    关闭Socket,
    # 配置 / 查询
    设置非阻塞,
    获取本地地址,
    获取远程地址,
    获取错误信息,
    sock有效,
    连接有效,
    # 事件多路复用
    select读写,
    # 地址解析
    将主机名转为IP,
    解析IP地址,
    主机转网络字节序,
    网络转主机字节序,
)

__all__ = [
    "AF_INET", "AF_UNIX", "SOCK_STREAM", "SOCK_DGRAM",
    "创建TCPSocket", "创建UDPSocket", "绑定", "绑定UDP", "监听", "接受",
    "连接TCP", "发送", "发送UDP", "接收", "接收UDP",
    "关闭连接", "关闭Socket",
    "设置非阻塞", "获取本地地址", "获取远程地址", "获取错误信息",
    "sock有效", "连接有效", "select读写",
    "将主机名转为IP", "解析IP地址", "主机转网络字节序", "网络转主机字节序",
]
