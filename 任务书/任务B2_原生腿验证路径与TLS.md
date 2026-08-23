# 任务 B2｜原生腿：让"代码在但零验证"变成"本机可真跑" + TLS 与 HTTP 原语

> **任务编号**：B2　**优先级**：P0（测试基建）+ P1（TLS/HTTP）　**依赖**：无（与 A2/C2/D2 零重叠）
> **仓库**：`g:\dswork\duan-light-merge\light-merge`，主分支 `main`（HEAD `e27277c2`）
> **工作树**：`../wt-B2`，分支 `task-B2`　**端口段**：19100–19199
> **⚠️ 开工前必读**：`任务书/协作规程.md` + `任务书/第二轮总纲与规程增补.md`

---

## 0. 先说清楚上一轮的成果和问题

**你上一轮交的 C 运行时是真代码，不是壳**（我逐行核实过）：

- `src/llvm/runtime_typed.c:35/38` 引入 `<sys/socket.h>` / `<sys/select.h>`，`:4369-4370` `WSAStartup`
- socket 原语 `:4361-4517`：`dv_socket_create/connect/bind/listen/accept/send/recv/close/shutdown`、`dv_socket_set_nonblocking`（`:4487-4497`，Win `ioctlsocket FIONBIO` / POSIX `O_NONBLOCK`）、`dv_socket_last_error`、`dv_socket_get_peer_addr`
- poller `:4520-4628`：`LightPoller` 基于 **select**，上限 `DV_POLLER_MAX 256`
- **IO 等待队列真接进了调度器** `:4630-4805`：`LightIOWait` 链表 `:4635`、`dv_coro_await_io` `:4668`、定时器有序链表 `:4643-4710`、事件循环 `dv_scheduler_run_event_loop` `:4752-4805`（跑就绪队列 → 处理到期定时器 → 算 poll 超时 → `dv_poller_wait` → 把就绪 fd 的协程摘回 `g_scheduler.run_queue`）
- IR 侧声明与调用落地：`src/llvm/codegen_typed.py:428-448`、`:1575-1769`，`:3186-3193` 把 `睡眠`/`await_io` 标为协程 yield 点

**问题只有一个，但很致命：这些在本机从未被真验证过一次。**

`tests/test_llvm_net.py` 10 条全部失败，根因同一个：`ModuleNotFoundError: No module named 'llvmlite'`。`:71-78` 的 `skip_no_compiler` 只检查 clang / MSVC，**漏判 llvmlite**；本机有 MSVC 无 clang → `HAS_COMPILER=True` 不 skip → MCJIT 腿（`:157-223` runner 脚本 `import llvmlite.binding`）必挂。

**唯一的正面证据**：DLL 编译环节是成功的（否则报的会是「runtime DLL 不可用」而不是 llvmlite 缺失），说明 `runtime_typed.c` 在 MSVC 下能编过。socket 行为本身：**零验证**。

---

## B2-1 【P0】修测试 skip 判据：不许再用"假红"掩盖"零覆盖"

**要做的**
1. `tests/test_llvm_net.py:71-78` 的 skip 条件补上 llvmlite 探测。**判据要按腿分**：clang 腿只需 clang，MCJIT 腿需 llvmlite + MSVC。缺哪条腿 skip 哪条，不是一刀切全 skip。
2. skip 的 reason 文案必须写清楚**缺什么、装了会验证到什么**，例如 `跳过：缺 llvmlite，socket 端到端行为未验证（B1/B2/B3 全部）`。这条文案会进主线的 skip 掩盖分析表。
3. 顺手修同类债务：`tests/e2e/test_llvm_pipeline.py:41-75` 断言 `returncode in [0,1]`——**成败都算通过**，这是假门禁，必须改成真判据。另：原生端到端 24 例硬依赖本机 clang 时应 **skip 而非 error**。

**验收**：本机（有 MSVC、无 clang、无 llvmlite）跑 `pytest tests/test_llvm_net.py` → **0 failed，10 skipped，reason 逐条说明掩盖了什么**。

## B2-2 【P0】给原生腿开一条本机能真跑的验证路径

现在等于没有。三条候选，**你评估后选一条落地，并在报告里写明为什么不选另两条**：

- **a) 装 llvmlite**：最快。口径澄清——项目既定口径「本机装第三方库导致的转绿不算修好」针对的是**被测对象的依赖**；llvmlite 属**工具链**，允许装。但**必须同时完成 B2-1**，否则下次换机器又是一片假红。
- **b) 装 clang / 用已有 MSVC 直编**：把 IR 落盘成 `.ll`，`clang -c` 或 `llc` 编成 obj 再和 `runtime_typed.obj` 链接。绕过 llvmlite，链路更接近真实发布形态。
- **c) 纯 C 层单元测试**：直接写 C 测试程序调 `dv_socket_*` / `dv_poller_*` / `dv_scheduler_run_event_loop`，MSVC 编译执行。**这条不能替代 a/b**（它不验证 IR 生成），但它能立刻给 socket 层一个真绿，建议**无论选 a 还是 b 都额外做 c**。

**验收**：至少要有一条命令，在本机跑出「光明源码 → 原生二进制 → 与真 Python echo server 收发 → stdout 比对通过」的真绿。这是 M3 里程碑的定义。

## B2-3 【P1】poller 从 select 升级

**证据**：`:4604/4606` 用 `select` + `FD_SET/FD_ISSET`，`DV_POLLER_MAX 256`。没有 poll/epoll/kqueue。

**要做的**
- Windows：`WSAPoll`（Vista+）；POSIX：`poll`。**epoll/kqueue 本轮不做**（先把 FD_SETSIZE 这个硬上限拆掉，再谈 O(1) 就绪通知）。
- 保留 select 作为 fallback，用编译期宏切换，**不要运行期动态选择**（会引入难查的平台差异）。
- 上限从编译期常量改为可增长，或至少把 256 提到一个有依据的值并在超限时**明确报错**而不是静默丢 fd。**静默丢 fd 是本项目最高优先级缺陷类型**，务必检查现有代码有没有这个行为。

## B2-4 【P1】原生 TLS：原生腿的硬阻断

**现状**：`runtime_typed.c` 里 `ssl|tls|schannel|openssl|mbedtls` 零匹配。原生腿要连 `https://api.deepseek.com` 一行都没有。

**要做的**（范围克制，本轮只求"能握手能收发"）
- 接口层先定：`dv_tls_wrap(fd)` / `dv_tls_handshake` / `dv_tls_send` / `dv_tls_recv` / `dv_tls_free`，语义与 `dv_socket_*` 对齐，**并且要能和 `dv_coro_await_io` 协作**（握手过程中的 WANT_READ/WANT_WRITE 要挂回 IO 等待队列，不许阻塞整个事件循环——这是最容易写错的地方）。
- 实现选一条：**Windows Schannel**（无第三方依赖，与"不装库"口径最合）或 **mbedTLS**（跨平台、代码量小、可 vendored）。**不建议 OpenSSL**（Windows 上分发成本高）。选择理由写进报告。
- 证书校验**必须默认开启**。提供关闭开关也必须默认关（即默认校验），且关闭时在 stderr 打醒目告警。**不许为了让测试通过而默认跳过校验**——这是安全红线。

**测试**：本地起一个自签证书的 TLS echo server（Python `ssl` 起，端口段 19100–19199），验证握手 + 收发 + **证书校验失败时确实失败**（正负两例都要）。

## B2-5 【P2】原生 HTTP/1.1 与 chunked

只在 B2-2/B2-3/B2-4 都落地后再开。要做就做**在 C 层还是在 `.light` 层**这个决策——注意 C2 已经用 `.light` 写了 HTTP/1.1 与 chunked 解码（`stdlib/流式.light:131-201`），**原生腿的正解可能是"让 LLVM 后端支持足够的字符串/字典能力，直接复用那份 `.light`"，而不是在 C 里重写一遍**。本轮请给出这个判断并列出"复用 `.light` 还差哪些语言特性"（与 A2-1 产出的「原生后端未支持语句清单」对齐）。

---

## 交付要求

1. **可改**：`src/llvm/runtime_typed.c`、`src/llvm/codegen_typed.py`（**仅内置函数注册段与外部函数声明段**）、`src/llvm/compiler.py`（**仅链接标志**）、`tests/test_llvm_net.py`、`tests/e2e/test_llvm_pipeline.py`、新建 `tests/test_llvm_tls.py` 与 C 层测试文件。
   **不许碰**：`src/lexer.py`、`src/parser_*.py`、`src/code_generator.py`、`stdlib/` 全部、`c_backend.py`、`src/llvm/codegen_typed.py` 的语句分派段（A2 的地盘）。
2. **定向测试**：`tests/test_llvm_*.py`、`tests/unit/test_ir_verify.py`、`tests/e2e/test_llvm_pipeline.py`、你新建的那些。**不许跑全量**。
3. **构建产物必须清理**：上一轮你的测试在仓库里留下了 `runtime_typed.obj`、`tests/_taskB_runtime.def`、`tests/_taskB_runtime.dll`。本轮临时文件前缀 `_taskB2_`，**收尾工作树只留最终交付物**，并在报告里列出"我的测试会生成哪些产物、清理命令是什么"（主线要照这个清）。
4. **上一轮报告里「工作树在涉及的 N 个文件上是干净的」这种说法不成立**——第一轮核实时发现 `积木库/blocks_v5/音乐/纯四度.light` 被清成 0 字节。本轮请用 `git status --porcelain` 全量输出落盘后逐行确认，**不要只看自己改的文件**。
5. **PowerShell 5.1**：中文输出落盘再读；不支持 `&&` 与 heredoc。
6. 提交一律逐路径 `git add` 白名单，**绝不用 `-A`**（你的 worktree 上一轮出现过积木库半检出，`-A` 会提交 3044 个文件的删除）。

## 移交清单

格式 `原生腿写不出什么 → 临时绕法 → 期望能力`。本轮特别需要：**"复用 `stdlib/流式.light` 还差哪些 LLVM 后端语言特性"** 的清单（B2-5），它和 A2-1 的清单合起来就是原生腿路线图。
