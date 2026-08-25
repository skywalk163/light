# -*- coding: utf-8 -*-
"""分布式节点网络边界（Python 实现，被光明模块包装）。

本文件是「系统边界」集中点，对上只暴露纯中文函数名；光明侧只做 `从 节点网络 导入 …`。
本文件不被 tools/ci/python_direct_calls.py 扫描（它只扫 .light）——**这是边界收口的
结果不是目的**：下列每一项都是光明语言当前无法用纯 .light 表达的系统原语
（外发任务 §4.5 要的「哪几行、为什么是真边界、期望的中文内置名」），逐项登记如下：

- `socket`（open_connection/网络收发）：进程间通信绕不开内核 socket；光明无 socket 原语。
  期望内置：无（网络传输整层待光明化，见交付报告 §1.2 偏离登记）。
- `json`（解析/序列化）：线协议（JSON-RPC 2.0）编解码；光明无 JSON 原语。
  期望内置：解析JSON / 序列化JSON（已在 stdlib/builtins.py 有实现，此处走转发）。
- `time.monotonic`（单调时钟）：心跳超时/请求硬超时的截止时刻，墙钟会被校时拨回。
  期望内置：单调时钟()（已在 任务书/缺失内置清单.json 立项）。
- `os.urandom`（随机标识）：节点ID/任务ID/幂等键/会话令牌 的生成底座，必须 CSPRNG。
  期望内置：随机字节()（已在 任务书/缺失内置清单.json 立项）。
- `hmac.compare_digest`（常量时间比较）：X-Auth-Token 校验，防时序侧信道。
  期望内置：常量时间比较()（S2 返工已立项，见 任务书/缺失内置清单.json）。
- `asyncio`（事件循环/Lock/Event/gather/wait_for）：异步并发原语；光明侧经
  stdlib/并发.light 与 E9 原语表达，本文件只在最底层桥接。
- `os.environ`（环境变量）：配置注入（DUAN_NODE_ID_DIR 等）。
  期望内置：环境枚举()（已在 任务书/缺失内置清单.json 立项）。

**注意**：`客户端类`（:177 起）**不是系统边界**——它是手写的完整 HTTP/1.1 + JSON-RPC
客户端（建连/拼请求行/解析 Content-Length），是 S2 的现实取舍（全仓无光明 HTTP 客户端），
已登记为一条「传输层偏离 + 客户端侧待光明化」欠账（交付报告 §1.2 / §7），S3 消除。
"""
import asyncio
import hmac
import json
import os
import re
import time


class 节点错误(Exception):
    """worker 侧 RPC 失败（连接断 / 读超时 / 非法响应）。"""


def 解析(文本或字节):
    if isinstance(文本或字节, (bytes, bytearray)):
        文本或字节 = 文本或字节.decode("utf-8", "replace")
    return json.loads(文本或字节)


def 序列化(字典):
    return json.dumps(字典, ensure_ascii=False)


def 单调():
    """单调时钟（超时/心跳判死用，不受系统调时间影响）。对应缺失内置 单调时钟()。"""
    return time.monotonic()


def 墙钟():
    """墙钟（仅用于 注册时间 这类展示字段，绝不用于超时判死）。"""
    return time.time()


def _随机十六进制(位数):
    字节数 = (位数 + 1) // 2
    原始 = os.urandom(字节数)
    十六进制串 = "".join("%02X" % b for b in 原始)
    return 十六进制串[:位数]


def 生成任务ID():
    # 线协议：T + 8 位时间戳(YYMMDDHH) + "-" + 12 位十六进制
    时间戳 = time.strftime("%y%m%d%H", time.localtime())
    return "T" + 时间戳 + "-" + _随机十六进制(12)


def 生成幂等键():
    # 线协议：I + 16 位十六进制；每次派发换新键，去重按 任务ID
    return "I" + _随机十六进制(16)


def 生成节点ID():
    # 线协议：N + 8 位十六进制
    return "N" + _随机十六进制(8)


def 生成令牌():
    """master 签发的短期会话令牌（S2 起 X-Auth-Token 强制）。"""
    return _随机十六进制(24)


def 常量比较(甲, 乙):
    """常量时间比较（防计时侧信道）；任一为 None 也安全返回 False。"""
    if not isinstance(甲, str) or not isinstance(乙, str):
        return False
    return hmac.compare_digest(甲, 乙)


_节点ID模式 = re.compile(r"^N[0-9A-F]{8}$")
_任务ID模式 = re.compile(r"^T[0-9]{8}-[0-9A-F]{12}$")
_幂等键模式 = re.compile(r"^I[0-9A-F]{16}$")


def 是节点ID(文本):
    return isinstance(文本, str) and _节点ID模式.match(文本) is not None


def 是任务ID(文本):
    return isinstance(文本, str) and _任务ID模式.match(文本) is not None


def 是幂等键(文本):
    return isinstance(文本, str) and _幂等键模式.match(文本) is not None


def 取头值(头字典, 名, 缺省=""):
    """大小写不敏感取 HTTP 头值（S2 X-Auth-Token 用）。"""
    目标 = 名.lower()
    for 键 in 头字典:
        if 键.lower() == 目标:
            return 头字典[键]
    return 缺省


def 新建事件():
    """asyncio.Event 包装（光明侧无 asyncio 直调）。"""
    return asyncio.Event()


def 事件设置(事件):
    事件.set()


async def 等待事件(事件):
    await 事件.wait()


def 取环境(名, 缺省=""):
    return os.environ.get(名, 缺省)


def 文件存在(路径):
    return os.path.exists(路径)


def 读文本(路径):
    try:
        with open(路径, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def 写文本(路径, 文本):
    with open(路径, "w", encoding="utf-8") as f:
        f.write(文本)


def 追加文本(路径, 文本):
    """诊断用：追加一行到日志（不扫 python_direct_calls）。"""
    try:
        with open(路径, "a", encoding="utf-8") as f:
            f.write(文本 + "\n")
    except OSError:
        pass


def 写JSON(路径, 字典):
    with open(路径, "w", encoding="utf-8") as f:
        json.dump(字典, f, ensure_ascii=False, indent=2)


def 转整数(文本, 缺省=0):
    try:
        return int(文本)
    except (ValueError, TypeError):
        return 缺省


def 转字符串(值, 缺省=""):
    """int/等类型 → str（写端口文件等用）。与 转整数 一对，边界收口于此 .py。"""
    try:
        return str(值)
    except (ValueError, TypeError):
        return 缺省


async def 并发等待(任务表):
    """等一组协程/任务全部完成（等价 asyncio.gather）。光明侧无 asyncio 直调。"""
    return await asyncio.gather(*任务表)


class 客户端类:
    """纯 Python 的 JSON-RPC over HTTP/1.1 客户端，keep-alive 复用连接，自带硬超时。

    每个 await 都过 asyncio.wait_for（默认 10s），符合「每个等网络的 await 都套硬超时」
    的红线——挂死的红不可诊断（gitea run 99 的教训）。连接断开自动重连一次。
    """

    def __init__(self, 主机, 端口, 超时=10.0, 令牌=""):
        self.主机 = 主机
        self.端口 = 端口
        self.超时 = 超时
        self.令牌 = 令牌
        self._读取器 = None
        self._写入器 = None
        self._下一个编号 = 1
        # keep-alive 单连接串行化锁：独立心跳协程与 领任务/交结果 主循环并发时，
        # 两个协程交替写同一 socket 会帧错乱（响应 A 读成响应 B）。
        self._锁 = asyncio.Lock()

    def 带令牌(self, 令牌):
        self.令牌 = 令牌

    async def _确保连接(self):
        if self._读取器 is None or self._读取器.at_eof():
            if self._写入器 is not None:
                try:
                    self._写入器.close()
                except Exception:
                    pass
                self._写入器 = None
                self._读取器 = None
            self._读取器, self._写入器 = await asyncio.wait_for(
                asyncio.open_connection(self.主机, self.端口), self.超时)

    async def 请求(self, 方法, 参数):
        async with self._锁:
            编号 = self._下一个编号
            self._下一个编号 += 1
            载荷 = {"jsonrpc": "2.0", "方法": 方法, "参数": 参数, "id": 编号}
            体 = 序列化(载荷).encode("utf-8")
            令牌头 = ""
            if self.令牌:
                令牌头 = "X-Auth-Token: %s\r\n" % self.令牌
            请求行 = (
                "POST /rpc HTTP/1.1\r\n"
                "Host: %s\r\n"
                "Content-Type: application/json; charset=utf-8\r\n"
                "%s"
                "Content-Length: %d\r\n"
                "Connection: keep-alive\r\n\r\n" % (self.主机, 令牌头, len(体))
            ).encode("utf-8") + 体
            await self._发送(请求行)
            return await self._读响应()

    async def _发送(self, 请求行):
        try:
            self._写入器.write(请求行)
            await asyncio.wait_for(self._写入器.drain(), self.超时)
        except Exception:
            self._读取器 = None
            self._写入器 = None
            await self._确保连接()
            self._写入器.write(请求行)
            await asyncio.wait_for(self._写入器.drain(), self.超时)

    async def _读响应(self):
        缓冲 = b""
        while b"\r\n\r\n" not in 缓冲:
            块 = await asyncio.wait_for(self._读取器.read(4096), self.超时)
            if not 块:
                raise 节点错误("连接被对端关闭")
            缓冲 += 块
        分隔 = 缓冲.find(b"\r\n\r\n")
        头区块 = 缓冲[:分隔]
        剩余 = 缓冲[分隔 + 4:]
        行们 = 头区块.decode("utf-8", "replace").split("\r\n")
        头字典 = {}
        for 行 in 行们[1:]:
            if ":" in 行:
                名, 值 = 行.split(":", 1)
                头字典[名.strip().lower()] = 值.strip()
        内容长度 = int(头字典.get("content-length", "0"))
        while len(剩余) < 内容长度:
            块 = await asyncio.wait_for(self._读取器.read(4096), self.超时)
            if not 块:
                break
            剩余 += 块
        return 解析(剩余[:内容长度])

    def 关闭(self):
        if self._写入器 is not None:
            try:
                self._写入器.close()
            except Exception:
                pass


def 客户端(主机, 端口, 超时=10.0):
    return 客户端类(主机, 端口, 超时)
