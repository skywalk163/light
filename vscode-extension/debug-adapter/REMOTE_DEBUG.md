# 光明调试器 · 远程调试（DAP over TCP）

光明调试适配器（`light_debug_adapter.py`）实现 VS Code 的 **Debug Adapter Protocol (DAP)**。
本文件说明如何在 **本地（stdio）** 与 **远程（TCP）** 两种模式下调试光明程序。

---

## 1. 传输模式

| 模式 | 触发方式 | 说明 |
|------|----------|------|
| `stdio`（默认） | 不指定 `--port`，或 `--mode stdio` | DAP 消息走进程的标准输入/输出，供同机 VS Code 使用 |
| `tcp` | `--port N`（N>0），或 `--mode tcp` | 适配器作为 **TCP 服务端** 监听 `host:port`，远程 DAP 客户端连接 |

配置优先级：**显式 `--host/--port/--mode` > 环境变量 `LIGHT_DEBUG_*` > 默认值**。

```bash
# 本地默认（stdio）
python vscode-extension/debug-adapter/light_debug_adapter.py

# TCP 模式（适配器的机器上执行）
python vscode-extension/debug-adapter/light_debug_adapter.py --host 0.0.0.0 --port 5678

# 等价的环境变量写法
LIGHT_DEBUG_HOST=0.0.0.0 LIGHT_DEBUG_PORT=5678 \
  python vscode-extension/debug-adapter/light_debug_adapter.py
```

> 默认 `host` 为 `127.0.0.1`，`port` 为 `0`（即 stdio）。远程调试须显式监听 `0.0.0.0`（或具体网卡 IP）并给出端口。

---

## 2. 本地调试（stdio，VS Code Run & Debug）

`package.json` 已声明 `light` 调试类型，可直接在 VS Code 中使用：

1. 打开一个 `.light` 文件。
2. 切换至「运行和调试」面板 → 「创建 launch.json」→ 选择 **光明 (Light) 调试器**。
   生成的 `.vscode/launch.json` 形如：

   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "type": "light",
         "request": "launch",
         "name": "光明: 启动调试",
         "program": "${file}"
       }
     ]
   }
   ```
3. 按 `F5` 启动。VS Code 会以 stdio 方式拉起适配器，命中断点/单步时通过 DAP 通信。

---

## 3. 远程调试（TCP）

典型场景：光明程序运行在 **远程/容器/另一台机器** 上，本机 VS Code（或任意 DAP 客户端）通过网络连接调试。

### 3.1 在目标机上启动适配器（TCP 服务端）

```bash
# 在远程机（程序所在机器）执行
cd /path/to/light
python vscode-extension/debug-adapter/light_debug_adapter.py \
  --host 0.0.0.0 --port 5678
# 日志：监听 DAP TCP 0.0.0.0:5678 ...（等待客户端连接）
```

适配器启动后 **阻塞等待** 一个 DAP 客户端连接；连接建立后，客户端发送 `initialize` / `launch` 等请求即可调试。

### 3.2 本机连接（DAP over TCP）

连接方式任选其一：

- **方式 A — 通用 DAP TCP 客户端**：用任意支持 DAP-over-TCP 的工具（如 `vscode` 的 `attach` 配置、[vscode-debug-adapter](https://github.com/microsoft/vscode-debugadapter) 的 `DebugClient`、或自写 socket 客户端）连接 `目标机IP:5678`。DAP 帧格式与 stdio 完全一致（`Content-Length: N\r\n\r\n<JSON>`），仅传输通道换成 socket。
- **方式 B — SSH 端口转发（推荐，更安全）**：不必把 5678 暴露公网：

  ```bash
  # 本机执行：把远程 5678 映射到本机 5678
  ssh -N -L 5678:127.0.0.1:5678 user@远程机IP
  ```
  然后本机 DAP 客户端连接 `127.0.0.1:5678`。

### 3.3 launch 请求示例（DAP JSON）

客户端连接后，按标准 DAP 顺序发送（TCP 与 stdio 相同）：

```jsonc
// 1) initialize
{"type":"request","seq":1,"command":"initialize",
 "arguments":{"clientID":"remote","adapterID":"light","linesStartAt1":true,"columnsStartAt1":true}}
// 2) configurationDone
{"type":"request","seq":2,"command":"configurationDone","arguments":{}}
// 3) launch —— program 为远程机上的 .light 绝对路径
{"type":"request","seq":3,"command":"launch",
 "arguments":{"program":"/path/to/remote/examples/basic.light"}}
// 之后可发送 setBreakpoints / continue / next / stepIn / pause / disconnect
```

调试过程中的 `output`（程序打印）、`stopped`（命中断点）、`terminated` 等事件均由适配器经同一 TCP 连接回传。

---

## 4. 已知限制 / 后续工作

- **`launch.json` 中的 `tcpPort` 目前仅作配置声明**：真正的 TCP 模式须在目标机上**手动**以 `--host/--port` 启动适配器，再用 DAP 客户端连接（见 §3）。尚不支持由 VS Code 一键 `attach` 到远程适配器（需要再补充 `attach` 请求处理与调试配置解析）。
- **`stdio` 模式仅限同机**：跨网络必须使用 TCP。
- **安全性**：`--host 0.0.0.0` 会把调试端口暴露给所有网络接口，任何能连上该端口的客户端都能控制程序执行。**生产/公网环境务必配合防火墙或 SSH 隧道（§3.2 方式 B）**，不要直接暴露。

---

## 5. 实现要点（给维护者）

- 传输层抽象为 `StdioTransport` / `TcpTransport`，统一实现 `read_message()` / `write_message()`。
- DAP 帧写出的关键修复：整帧以**字节**经 `sys.stdout.buffer.write` 写出，避免 Windows 下 `\n`→`\r\n` 把 `\r\n\r\n` 变成 `\r\r\n\r\r\n` 破坏帧边界。
- DAP 输出通道在 `run_debug_adapter()` 启动时捕获真实 `sys.stdout` 到模块级 `_DAP_OUT`，避免 `_run_program` 把 `sys.stdout` 替换为 `LightOutputCapture` 后，DAP 消息被误当成程序输出导致递归/损坏（该问题仅影响 stdio 模式；TCP 走 socket 天然免疫）。
- 标准输入读取使用 `sys.stdin.buffer.read1()`，避免管道上 `read(4096)` 为凑满字节数而阻塞卡死。
