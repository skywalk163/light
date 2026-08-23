# 任务 B｜原生 runtime 的网络、非阻塞 IO 与事件循环

> **任务编号**：B　**优先级**：P0（原生优先口径下的核心工程）　**依赖**：无，可与 A/C/D 并行
> **仓库**：`g:\dswork\duan-light-merge\light-merge`，主分支 `main`
> **⚠️ 开工前必读 `任务书/协作规程.md`**——四路 agent 同机并行，你必须在自己的 git worktree（`../wt-B`，分支 `task-B`）里作业，且**不许跑全量测试**。你的 socket 测试端口段是 **19100–19199**。规程优先于本文任何冲突表述。
> **背景**：我们要用「光明（Light）」这门中文编程语言**原生编译成二进制**来承载一个 agent 框架。agent 框架的本质是「一根网络长连接 + 一堆子进程 + 一个事件循环把它们缝起来」。原生 runtime 目前**一行网络代码都没有**。这是通往北极星路上最贵的一块地基，交给你。

---

## 0. 现状（已核实，不要重新调查这部分）

**主战场文件**：`src/llvm/runtime_typed.c`，**4344 行**，约 228 个导出函数。它服务于 LLVM 后端（`src/llvm/codegen_typed.py`，3372 行），不服务于 `c_backend.py`（那是另一条死路，别管它）。

**已经有的（可以直接用，不要重写）**
- 单一 tagged 值类型 `LightValue`（`:37-52`）：`{ int type; int64_t i64; double f64; char* str; int boolean; int list_size; int list_capacity; LightValue** list_data; }`，type 枚举 `0=NULL 1=INT 2=FLOAT 3=STR 4=LIST 5=BOOL 6=OBJ 7=DICT 8=REF`。参数一律传指针以避开 C/LLVM 结构体 ABI 差异（`:10` 注释）
- 值构造/销毁/复制/类型转换（`:94 / :164 / :245`）
- 算术与数学（`:309 / :425 / :542`）、比较与字符串（`:777 / :857 / :1036`）
- **列表（`:1223`）与字典（`:1637`，键值对平铺在 `list_data`）——原生复杂类型已经落地，不是 `PyObject*`**
- 时间（`:1853`）、文件操作（`:1870 / :1982`）、系统操作（`:2545`）
- 异常 try/catch/throw（`:2659`）+ 异常类体系（`:2783`）
- 类/对象（`:3104`）、类元信息（`:3258`）、接口系统（`:3427`）、运算符重载（`:3865`）、isinstance（`:3925`）
- **协程/异步（`:4006`）**：`LightCoroutine`（`:4027-4043`）、`LightFuture`（`:4045-4053`）、`LightScheduler{ run_queue, all_coros, num_coros }`（`:4056-4063`）+ 全局单例 `g_scheduler`（`:4063`）、`dv_scheduler_run()` 单线程取队首（`:4233-4243`）、`dv_coro_await`（`:4186`）、`dv_coro_run_to_completion`（`:4246`）。恢复机制是 **Duff's device + `resume_point`**（`:4019`），上限 `DV_MAX_COROUTINES 256`（`:4024`）
- 目标平台：win32 / linux / darwin × x86_64 / aarch64（`codegen_typed.py:17-29, 84-87`）
- **真端到端测试范式已存在**，照抄它：`tests/test_llvm_exception.py`（12 例）与 `tests/test_llvm_async.py`（12 例）都是 `compile_source_typed` → `clang -O2 -o exe ir runtime_typed.c` → 运行 → 比对 stdout（见 `test_llvm_exception.py:8, 27-48`）

**完全没有的（你要补的）**
- 头文件只有 stdio/stdlib/string/stdint/time/math/sys-stat/ctype/errno + Windows 下 windows.h/io.h/direct.h（`:13-31`）
- 全文件 `epoll | kqueue | io_uring | pthread | CreateThread | WSA | sys/socket` **零匹配**
- 全文件 `select | poll | WSAPoll | nonblock | O_NONBLOCK | FIONBIO` **零匹配**
- 也就是说：**无 socket、无 IO 多路复用、无线程、无非阻塞 IO**
- 调度器是**纯协作式**：协程只能靠主动 yield 切换，**不能被"socket 可读"唤醒**

> ⚠️ 一个必须先摆正的认知：v1 分析文档说"原生 list/dict 仍是 `PyObject*`（`c_backend.py:22-23`）"，**这是错的**。那张 `PY_TYPE_TO_C` 表是**零引用死代码**，`c_backend.py` 也不是原生主路线。你的战场只有 `src/llvm/`。别去修 `c_backend.py`。

---

## 1. 任务分解

### B1 socket 原语（先做这个）

在 `runtime_typed.c` 末尾新开一个「网络」分区，实现 socket 族，全部走 `LightValue*` 出入参约定（与既有函数一致）。

最小函数集（命名沿用 `dv_` 前缀惯例，与既有导出保持一致）：
- `dv_socket_create(域, 类型)` → fd（`LightValue* INT`）
- `dv_socket_connect(fd, 主机, 端口)`、`dv_socket_bind`、`dv_socket_listen`、`dv_socket_accept`
- `dv_socket_send(fd, 数据)`、`dv_socket_recv(fd, 最大字节)` → `LightValue* STR`
- `dv_socket_close(fd)`、`dv_socket_shutdown(fd, 方向)`
- `dv_socket_set_nonblocking(fd, 开关)`
- `dv_socket_last_error()` → 错误码 + 可读消息

**跨平台要求**
- POSIX：`sys/socket.h` / `netinet/in.h` / `arpa/inet.h` / `netdb.h` / `fcntl.h`（`O_NONBLOCK`）/ `unistd.h`
- Windows：`winsock2.h` / `ws2tcpip.h`，需 `WSAStartup`/`WSACleanup`（建议在 `__light_init()` 里做一次，`codegen.py:123` 是该函数的生成点）、`ioctlsocket(FIONBIO)`、链接 `ws2_32`
- **链接标志要同步**：`clang` 调用处需要在 Windows 下加 `-lws2_32`。检查 `src/llvm/compiler.py` 的 clang 命令行构造并加上

**错误处理约定**：失败返回 `LightValue*` 的错误值还是抛光明异常？**必须与既有异常体系（`:2659` try/catch、`:2783` 异常类）保持一致**——建议网络错误抛 `IO错误`/`网络错误` 光明异常，这样上层 `.light` 代码能 `尝试/捕获`。选定后写进注释。

**验收**：新建 `tests/test_llvm_net.py`，照抄 `test_llvm_exception.py` 的端到端范式。用例：原生二进制向 `127.0.0.1` 上一个测试用 TCP echo server（用 Python 在测试里 `threading` 起一个）发 `hello`，收回 `hello`，打印。**必须真编译真运行真比对 stdout。**

---

### B2 IO 多路复用抽象层

在 socket 之上做一层**平台无关的 poller 抽象**，不要把 epoll/kqueue 的差异漏到上层。

- 内部结构 `LightPoller`，接口约 4 个：`创建 / 注册(fd, 读|写) / 注销(fd) / 等待(超时毫秒) → 就绪事件列表`
- 平台后端优先级：Linux `epoll` → macOS/BSD `kqueue` → Windows `WSAPoll`（**不要一上手就搞 IOCP**，WSAPoll 语义与 poll 接近，够用且能先跑通）
- **允许并鼓励**先落一个 `select` 的通用兜底实现（`select` 三平台都有），把上层 B3 先跑通，再逐平台换成 epoll/kqueue/WSAPoll。这样 B3 不会被 B2 阻塞。
- io_uring **不做**，收益/复杂度比不合适，登记为后续。

**验收**：`tests/test_llvm_net.py` 增加用例——两个 socket，只有一个有数据，`等待` 只返回那一个的 fd。

---

### B3 调度器接 IO 唤醒（本任务的核心价值）

把 `g_scheduler`（`:4056-4063`）从纯协作式升级成真事件循环。

**要改的**
1. `LightScheduler` 增加 **IO 等待队列**：`{ fd, 关注事件, 挂起的协程 }` 的集合 + 一个 `LightPoller` 实例
2. `dv_scheduler_run()`（`:4233-4243`）主循环改成标准事件循环形态：
   ```
   while (有可运行协程 || 有IO等待协程 || 有定时器):
       跑完 run_queue 里所有就绪协程
       计算下一个定时器到期时间 → 作为 poller 等待超时
       poller.等待(超时) → 就绪 fd → 把对应协程从 IO 等待队列移回 run_queue
       处理到期定时器
   ```
3. 新增 `dv_coro_await_io(fd, 事件)`：让当前协程挂起并登记到 IO 等待队列（与既有 `dv_coro_await`（`:4186`）语义对齐，只是唤醒条件不同）
4. 新增定时器：`dv_coro_sleep(毫秒)`——agent loop 的重试退避、超时都要它
5. **`DV_MAX_COROUTINES 256`（`:4024`）这个硬上限要处理**。一个 agent 框架并发跑几十个 tool call + 子 agent 很容易撞上。改成动态增长，或至少提到 4096 并在超限时抛明确的光明异常（**不许静默截断**）。

**Duff's device 的约束要写清**：现有恢复机制是 `resume_point` + switch（`:4019`），这意味着**协程栈上的局部变量在挂起点之后不保活**——`codegen_typed.py:2781-2999` 的 await 点预扫描应该已经在处理这个（把跨挂起点的局部提升到协程结构体）。你新增 IO 挂起点时，**必须确认这套提升逻辑同样覆盖 `await_io` 和 `sleep`**，否则会出现"await 之后变量变垃圾值"的隐蔽 bug。这是本任务最容易出错的地方，请专门写一个用例：`await_io` 前后读同一个局部变量，值必须一致。

**验收**：一个 `.light` 程序，两个异步段落各自连一个 echo server 并等待响应，事件循环并发驱动，两者响应顺序由 server 的返回延迟决定（不是由代码顺序决定）。原生二进制跑通。

---

### B4 codegen 侧内置函数注册

`src/llvm/codegen_typed.py` 里需要把 B1–B3 的新 C 函数注册为可从光明调用的内置（照现有内置的注册方式办，`declare` 生成点见 `src/llvm/codegen.py:926`）。

**只改注册段，不要改这个文件的其它逻辑**（AST/语句生成是任务 A 的地盘）。

---

### B5（P1，做完 B1–B4 再考虑）原生线程

`pthread`/`CreateThread` 封装，让 CPU 密集工作不阻塞事件循环。**优先级低于 B1–B4，如果时间不够就登记移交，别半途而废地留一个不完整的线程实现——那比没有更危险。**

---

## 2. 交付要求

1. **只改这些文件**：`src/llvm/runtime_typed.c`、`src/llvm/codegen_typed.py`（**仅内置函数注册段**）、`src/llvm/compiler.py`（**仅 clang 链接标志**）、`tests/test_llvm_net.py`（新建）。
   **明确不许动**：`src/lexer.py`、`src/parser_*.py`、`src/code_generator.py`（任务 A 的地盘）、`stdlib/`（任务 C/D 的地盘）、`c_backend.py`（死路）。
2. **每个子任务一个真跑端到端测试**，范式照抄 `tests/test_llvm_exception.py:27-48`（IR → clang → exe → 比对 stdout）。**纯字符串断言不算验收**。
3. **无 clang 环境要优雅 skip**。现存 `test_llvm_exception.py`/`test_llvm_async.py` 的 `find_clang()` 失败会抛 `RuntimeError` 导致 error 而非 skip——**你的新测试不要复制这个毛病**，用 `pytest.mark.skipif`。
4. **跨平台**：你可能只能在 Windows 上实测（本机是 Win10 + PowerShell 5.1）。**POSIX 分支写完但没实测就明确标注"未实测"**，不许声称跨平台通过。
5. **回归验证：只跑定向测试，不跑全量**（详见 `协作规程.md` §2）。
   - 老协议「`git stash push` 跑两遍全量」**已作废，不要执行**——四个 agent 同机作业时 stash 栈是共享的，会互相摧毁
   - 你要跑的：`tests/test_llvm_*.py`、`tests/unit/test_ir_verify.py`、`tests/e2e/test_llvm_pipeline.py`，加你新建的 `tests/test_llvm_net.py`
   - **全量回归由主线在独占机器时统一跑**并出「红转绿 / 新增打红」两份名单。别抢这个活
   - **端口写死在 19100–19199 段**。绑定前先探测可用，占用则报错退出，**不许自动往上加一个端口重试**（会漂到任务 C 的段里）
   - 临时文件一律加 `_taskB_` 前缀，收尾删干净
   - **你和任务 A 都会碰 `src/llvm/codegen_typed.py`**——这是唯一重叠点。你只动**内置函数注册段**，A 只动语句分派段。改动集中成独立 commit，合并时好挑
6. **本机装第三方库导致的转绿不算修好。**
7. **PowerShell**：中文输出落盘再读（直读乱码，乱码只在显示层）；不支持 `&&` 与 heredoc。

## 3. 移交清单（发现但不要动）

- 根目录 `llvm_backend.py` 名不副实：不生成 IR，只是"找 clang 编译 C 文件"的包装（`:27-50, 131-138`），与 `c_backend.编译C到原生`（`:728-784`）重复
- **两条 LLVM 路径并存**：`src/llvm/`（主力）与 `antlrparser/llvm_codegen.py`（旧，i8* 字符串类型系统），`src/compiler.py:1510-1528` 走旧路径而 `cli/light.py` 走新路径。需主线裁定权威
- `tests/e2e/test_llvm_pipeline.py:41-75` 的 `test_simple_ir_generation` 断言 `returncode in [0, 1]`——**成功和失败都算通过**，是无效测试
- `--target wasm`（`cli/light_unified.py:1056`）参数存在但 `compile_with_src:365-407` 只特判 `llvm`，wasm/js **静默生成 `.py`**
- `light6.py` help 自称 `light7`，但 `pyproject.toml:67-69` 无 `light7` 入口，安装用户拿不到 `--c/--native`
