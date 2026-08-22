# B2-5: HTTP/1.1 决策分析

## 结论：不在 C 层重写 HTTP/1.1，应让 LLVM 后端补齐语言特性后直接复用 `stdlib/流式.light`

### 1. 现状

**C2 已交付的 `.light` 层 HTTP/1.1**（`stdlib/流式.light`，267 行）：
- 完整 HTTP/1.1 客户端：构造请求 → 发送 → 读响应头 → 按块/按行读响应体
- 支持 Content-Length、Transfer-Encoding: chunked、连接关闭三种体读取模式
- chunked 解码、行切分、增量 UTF-8 解码全部在 `.light` 层实现
- 依赖 Python stdlib（`导入 socket`、`导入 codecs`）

**B2 交付的 C 层原语**（`runtime_typed.c`）：
- `dv_socket_create/connect/bind/listen/accept/send/recv/close/shutdown`
- `dv_socket_set_nonblocking/last_error/get_peer_addr`
- WSAPoll/poll 多路复用器（动态扩容，不静默丢 fd）
- Schannel TLS（`dv_tls_wrap/handshake/send/recv/free`，握手挂回 IO 等待队列）
- 协程事件循环（`dv_coro_await_io/sleep`，`dv_scheduler_run_event_loop`）

### 2. 为什么不在 C 层重写

| 维度 | C 层重写 | 复用 `.light` |
|------|---------|-------------|
| 代码量 | ~500 行 C（含 chunked、行切分、头解析） | 0 行（已有 267 行 .light） |
| 可维护性 | C 代码改协议要重编译分发 | `.light` 改完即生效 |
| 可测试性 | 需另写 C 测试 | C2 已有 .light 测试 |
| 与 Python 腿一致 | 两份 HTTP 实现，行为可能分叉 | 一份代码两条腿跑 |
| 已有能力 | C 层只有 socket 字节收发 | `.light` 已有完整协议逻辑 |

**C 层的职责边界**：提供原语（socket/TLS/poller/事件循环），不实现应用层协议。这与 `dv_socket_*` 的设计口径一致——它不解析 HTTP，只搬字节。

### 3. 复用 `流式.light` 还差哪些 LLVM 后端语言特性

逐条对照 `流式.light` 用到的语法与 LLVM codegen（`codegen_typed.py`）的现有支持：

#### 3.1 阻断级（不补就跑不了）

| # | 特性 | `流式.light` 用法 | LLVM 后端现状 | 补法 |
|---|------|------------------|-------------|------|
| G1 | **yield / 生成器** | `生成 块数据`（行 75/78/86/93/114/119/201）；`遍历 块 之 己.read_body()` 消费生成器 | **零支持**。codegen 无 YieldStatement 分派，无生成器状态机 | codegen 新增 yield 语句分派：生成协程状态机 ret + resume 点；runtime 加生成器 LightValue 子类型 |
| G2 | **bytes 类型** | `b""`、`b" HTTP/1.1\r\n"`、`b"\r\n\r\n"`（行 36/132/136/140/146/154/164/166/180/190 等）；bytes 拼接 `缓冲 加上 块` | **零支持**。LightValue 只有 type=3 (STR)，无 bytes 类型。`b""` 前缀语法 lexer 能吃但 codegen 当普通字符串处理，二进制安全无保障 | 方案 A：LightValue 加 type=9 (BYTES)，runtime 加 dv_bytes_* 系列函数；方案 B（轻量）：STR 内部存原始字节 + 长度，`b""` 只影响 `.encode()` 方法是否跳过。推荐 B——HTTP 场景 bytes 本质是「不解释的字符串」 |
| G3 | **切片 `[start:end]`** | `缓冲[0:分隔]`、`缓冲[分隔 加上 4:]`、`行缓冲[起点:i]`、`行[0:ln 减去 1]`、`缓冲[行尾 加上 2:]`（行 127/167/168/190/191/199/200/110/113/118 等） | **零支持**。`_gen_typed_index_access`（:2415-2442）只处理单个整数索引，不识别 `start:end` 语法 | parser 已有 SliceExpr 节点（C2 走 Python 解释器能跑）；codegen 的 IndexAccess 分派里加 `isinstance(expr.index, ast.Slice)` 分支，调 `dv_str_slice` / `dv_list_slice` |

#### 3.2 高优先级（不补就跑不了完整 HTTP）

| # | 特性 | `流式.light` 用法 | LLVM 后端现状 | 补法 |
|---|------|------------------|-------------|------|
| G4 | **`导入 socket`** | `导入 socket`（行 12），`socket.socket()`、`socket.AF_INET`、`socket.SOCK_STREAM`（行 52） | codegen 的 ImportStatement 分派（:686-745）只处理 `.light` 模块导入，不处理 Python stdlib | 在 runtime 加 `dv_socket_module` 虚拟模块：`socket.socket()` → `dv_socket_create(AF_INET, SOCK_STREAM)`，`socket.AF_INET` → 常量，等。或在 codegen 层把 `导入 socket` 翻译为对 `dv_socket_*` 的直接调用 |
| G5 | **`.encode("utf-8")` 方法** | `方法.encode("utf-8")`、`路径.encode("utf-8")`、`键.encode("utf-8")`、`头[键].encode("utf-8")`、`主机值.encode("utf-8")`（行 133-148） | **未注册**。codegen 的方法分派表无 `encode` | runtime 加 `dv_str_encode(LightValue* result, LightValue* str, const char* encoding)`；codegen 注册 `编码` / `encode` 方法 |
| G6 | **`.recv()` / `.sendall()` / `.settimeout()` / `.close()` 方法** | `s.recv(大小)`、`s.sendall(req)`、`s.settimeout(己.超时连接)`、`s.close()`（行 53/63/157/207/216） | 这些是 Python socket 对象的方法。LLVM 后端没有 Python socket 对象，只有 `int fd` | 需要把 `流式.light` 的 `socket.socket()` 调用替换为 `dv_socket_create()` + `dv_socket_connect()`，或提供 socket 对象封装（LightValue type=6 OBJ，方法表映射到 dv_socket_*） |
| G7 | **`codecs.getincrementaldecoder("utf-8")()`** | `codecs.getincrementaldecoder("utf-8")()`、`解码器.decode(块, 假)`（行 99/102） | **零支持**。codecs 是 Python stdlib | runtime 加 `dv_utf8_incremental_decoder` 结构体 + `dv_utf8_decode_incremental()` 函数；或简化为 `dv_str_decode(result, bytes, encoding)` 一次性解码（牺牲增量能力，但 HTTP 场景一般可接受） |

#### 3.3 中优先级（有 workaround 但影响正确性/可维护性）

| # | 特性 | `流式.light` 用法 | LLVM 后端现状 | 补法 |
|---|------|------------------|-------------|------|
| G8 | **try-except-else（`否则`子句）** | `尝试: ... 捕获 异常 e: ... 否则: ...`（行 54-69/62-69/206-210） | codegen 的 TryStatement 分派（:2196+）需确认是否处理 `否则` 子句。Python 语义：else 块在 try 无异常时执行 | 检查 `_gen_typed_try` 是否生成 else 块的 IR；如未处理，加一个 `else_bb` 基本块，在无异常跳转时进入 |
| G9 | **类继承 `继承 Exception`** | `类 连接错误 继承 Exception:`、`类 HTTP错误 继承 Exception:`（行 16/20/24） | codegen 的类生成（:3467+）需确认是否处理 `继承` 基类 | 如未处理：codegen 在生成类方法表时，把基类方法追加到子类方法表（单继承 vtable 拼接） |
| G10 | **`父.构造()` 超类调用** | `父.构造(消息)`、`父.构造("HTTP 状态 " 加上 ...)`（行 18/22/26） | 需确认 codegen 是否支持 `父` 标识符 | 如未处理：codegen 把 `父.方法()` 翻译为对基类方法函数的直接调用（单继承下基类方法地址已知） |
| G11 | **`e.args` 异常属性** | `e.args`、`a[0]`（行 222-224） | 需确认 Exception 对象在 LLVM 后端是否有 `args` 属性 | runtime 的异常 LightValue 需带 args 列表；codegen 的 PropertyAccess 需能从异常对象取 args |

#### 3.4 低优先级（已有支持或容易绕开）

| # | 特性 | 状态 |
|---|------|------|
| 字符串拼接 `加上` | ✅ 已支持（BinaryOp） |
| `转字符串()` | ✅ 已支持 |
| `长()` | ✅ 已支持 |
| `查找()` / `find()` | ✅ 已支持（`dv_str_find`） |
| `分割()` / `split()` | ✅ 已支持（`dv_str_split`） |
| `去除空格()` / `strip()` | ✅ 已注册（:1471） |
| `遍历 键 之 头`（dict 遍历） | 需确认 ForeachStatement 对 dict 的支持 |
| 字符串索引 `行缓冲[i]` | ✅ 已支持（`dv_str_get`） |
| `当`/`跳出`/`跳过` | ✅ 已支持 |
| `新建` 类实例化 | ✅ 已支持 |
| `抛出` | ✅ 已支持 |
| `己.属性` | ✅ 已支持 |

### 4. 路线图建议

**阶段 1（最小可用）：C 层加 HTTP 收发原语 + `.light` 适配**
- C 层不加 HTTP 协议逻辑，只加 `dv_http_parse_status_line` / `dv_http_parse_headers` / `dv_http_chunked_decode` 等辅助函数（纯解析，不碰 IO）
- `流式.light` 的 socket 调用改为 `dv_socket_*` 封装（通过 `导入 socket` 虚拟模块映射）
- 绕开 yield：把 `read_body` 改为回调式或列表式（收完再返回，牺牲流式）

**阶段 2（流式能力）：补 yield + 切片**
- codegen 加 yield 语句 → 协程状态机扩展
- IndexAccess 加 slice 分支
- `流式.light` 可直接复用，无需改动

**阶段 3（完整复用）：补 bytes + encode + codecs**
- LightValue 加 bytes 支持
- 注册 `.encode()` 方法
- 提供 `codecs.getincrementaldecoder` 的 native 等价物

### 5. 移交清单

格式：`原生腿写不出什么 → 临时绕法 → 期望能力`

| 原生腿写不出什么 | 临时绕法 | 期望能力 |
|----------------|---------|---------|
| `生成` (yield) | 回调式或收完再返回 | yield + 生成器遍历 |
| `b""` bytes 字面量 | 用字符串代替（二进制不安全） | bytes 类型或二进制安全字符串 |
| `缓冲[0:分隔]` 切片 | 手写循环逐字符拷贝 | `[start:end]` 切片语法 |
| `导入 socket` | C 层已有 `dv_socket_*`，需虚拟模块映射 | `导入 socket` 自动映射到 native socket |
| `.encode("utf-8")` | C 屽 `dv_str_encode` 函数 | `.encode()` 方法注册 |
| `codecs.getincrementaldecoder` | 一次性解码 | 增量 UTF-8 解码器 |
| `s.recv()` / `s.sendall()` | `dv_socket_recv` / `dv_socket_send` | socket 对象方法封装 |
