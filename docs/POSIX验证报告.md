# POSIX验证报告

> 测试对象：`wt-A7`（git HEAD `9670e65f2c2b4c0ddb8e565f586d60649d0de3a4`）
> 执行方式：本沙箱为 **Windows 10 (MINGW64)** + **clang 22.1.8 (x86_64-pc-windows-msvc)**。
> **本沙箱没有 Linux 内核**（WSL 被安全策略禁用，Docker 未安装），因此「Linux 内核上的执行面」一律**未运行**，逐条标注；凡有输出都是真跑出来的，没有「应该能」「理论上」。

---

## 0. 环境与 commit

| 项目 | 值（直抄） |
|---|---|
| `uname -a` | `MINGW64_NT-10.0-19045 DESKTOP-6LFQUO8 3.6.9-b4195d69.x86_64 2026-06-06 17:49 UTC x86_64 Msys` |
| `clang --version` | `clang version 22.1.8 (https://github.com/llvm/llvm-project ca7933e47d3a3451d81e72ac174dcb5aa28b59d1)`，`Target: x86_64-pc-windows-msvc` |
| `clang -print-target-triple` | `x86_64-pc-windows-msvc` |
| `python3 --version` | `Python 3.13.14` |
| `which clang` | `/c/Program Files/LLVM/bin/clang` |
| `lld / lld-link` | 已装（`/c/Program Files/LLVM/bin/lld`、`lld-link`） |
| `git rev-parse HEAD` | `9670e65f2c2b4c0ddb8e565f586d60649d0de3a4` |
| `git status --porcelain` | 空（干净；见 §6 说明） |
| pytest | 9.1.1（`python3 -m pytest --version`） |

环境红线：本机 clang 与你 Windows 侧是**同一个版本 22.1.8**，所以凡是「clang 行为」类验证（legacy pass 拒绝、LTO、优化档）在本沙箱测与在你 Windows 上测是等价的；凡是「Linux 运行时」类验证（epoll/poll 执行、POSIX 分支编译、Linux TLS）则**无法在本沙箱进行**。

---

## 1. 一句话结论

**无法给出 Linux 实测等级（沙箱无 Linux 内核）。** 就代码层面而言：`runtime_typed.c` 的 POSIX 分支是**结构完整的真实现**（socket = BSD socket；poller = `poll()`；事件循环 = 真挂起/恢复，非同步退化），**唯一明确缺口是 TLS = 有壳无实现（stub）**；同时实测发现 **Windows LTO 链接存在一个真实缺陷（链接步骤缺 `-fuse-ld=lld`）**，Windows clang 22.1.8 生产路径 12 格全绿、CLI 端到端可用、469 条 assert_quality 门禁通过。若要在 Linux 上给「与 Windows 等价」结论，需要一台 Linux 内核的 runner 重跑 §B/C/E 的 Linux 面。

---

## 2. A~F 六节实测结果

### A. 编译器驱动的 POSIX 分支（`src/llvm/compiler.py`）

**A.1 `find_clang()` 清空 PATH**
- 命令：harness 内 `os.environ['PATH']=''` 后调 `find_clang()`（compiler.py:800）
- 输出：`A.1 PATH清空后 find_clang 返回: C:\Program Files\LLVM\bin\clang.exe`（**未抛 RuntimeError**）
- 结论：候选表（compiler.py:823-827）里 `C:\Program Files\LLVM\bin\clang.exe` 是**硬编码绝对路径、且排在 PATH 探测之前**，清空 PATH 不影响它。Linux 侧同理：`/usr/bin/clang`、`/usr/local/bin/clang`（826-827、874-875）也是硬编码候选——只要 clang 在标准位置，清 PATH **不会**抛 RuntimeError；只有候选路径都不存在时才抛。任务书预期的「清 PATH → RuntimeError」在本实现下不成立，这不是 bug，但影响 §F 的测试手段。

**A.2 `get_link_libs()` 非 Windows 分支 `['-lm']` 够不够**
- 命令：monkeypatch `sys.platform='linux'` 调 `get_link_libs()`；全仓 `grep -rnE "pthread|dlopen|dlsym|dlinfo" src/`
- 输出：`['-lm']`；grep **0 命中**（runtime 与代码生成完全不引用线程/dlopen 符号）
- 结论：当前 runtime 在 Linux glibc 上 `['-lm']` 足够——socket 函数在 libc 里（Linux 不需要 `-lsocket`），且没有任何 pthread/dlopen 调用需要 `-lpthread`/`-ldl`。glibc ≥ 2.34 已把 pthread/libdl 并入 libc 是额外的保险。**Linux 真实链接报错原文未能获得**（本沙箱无 Linux 链接器），此项为代码事实 + glibc 链接语义，非实测。

**A.3 `get_optimization_flags()` 现状 + legacy pass 名实测**
- 命令：`get_optimization_flags(0..3)`（compiler.py:144）；对 `clang -mllvm <legacy> -c ...` 实测
- 输出：
  - `get_optimization_flags(0..3) -> ['-O0'] / ['-O1'] / ['-O2'] / ['-O3']`（另有 -Os/-flto 分支）
  - legacy 名实测（clang 22.1.8）：
    - `clang -mllvm -inline` → rc=1，`clang (LLVM option parsing): Unknown command line argument '-inline'.`
    - `-mem2reg` → rc=1，`Unknown command line argument '-mem2reg'.`
    - `-gvn` → rc=1，`Unknown command line argument '-gvn'.`
    - `-loop-unroll` → rc=1，`Unknown command line argument '-loop-unroll'.`
- 结论：**A7 修复已合入**（优化标志只剩 -O0..-O3），按任务书口径直接进 B 节。关于「哪一版开始拒绝」：这些 legacy PassManager pass 名在 clang 切换默认优化器到新 PassManager（LLVM 14，2022）后不再注册，22.1.8（远超 14）实测一律拒绝；未逐一回溯每个小版本的精确切换点。

**A.4 `-flto` 分支真链接（Windows 侧此前未测）**
- 命令：`compile_light_typed(hello.light, ..., optimize_level=2, lto=True)`
- 输出（现状）：`RuntimeError: 链接失败:\nclang: error: LTO requires -fuse-ld=lld`
- 根因：三个链接步骤（compiler.py:510-511、654-655、1181-1182）在 `if lto:` 时**只加 `-flto`，没加 `-fuse-ld=lld`**；而 `-fuse-ld=lld` 只出现在 `get_optimization_flags()` 的**编译**参数里（compiler.py:190）。Windows 默认链接器不支持 LTO，故整条链接失败。
- 诊断验证（临时补丁，已还原）：在三个链接点补 `if sys.platform=='win32': link_args.append('-fuse-ld=lld')` 后重跑 → `A.4-after-patch: link OK rc=0 stdout='hello lto fixed'`。补丁后 `git checkout -- src/llvm/compiler.py` 已还原。
- 结论：**Windows LTO 是真实缺陷**（建议补丁见 §4 缺陷 #1）。Linux 侧链接步骤同样只有 `-flto`（GNU ld/lld 支持 LTO，预期可链，但本环境**未运行**验证）。

### B. 十二格优化矩阵（核心交付）

说明：本沙箱无 Linux，**12 格跑的是 Windows(_WIN32) 运行时 + clang 22.1.8**，走生产入口 `compile_light_typed(源文件, 产物基名, optimize_level=N)`（不是 `compile_source_typed`+裸 clang），每格「真编译 + 真运行 + 比对 stdout 行序 + 退出码」。全部中间产物在 `tempfile.TemporaryDirectory(prefix='_posix_')` 内，源码树复核无 `_posix_` 残留。结果：**12/12 PASS**（表见 §3），与「Windows 侧已全绿」一致。**Linux 侧这 12 格未运行**——任何一格在 Linux 红都将是新发现，但本环境给不出这个结论。

### C. runtime_typed.c 在 Linux 上到底能不能编

**C.1 `clang -c` 完整输出**
- 命令：`clang -c src/llvm/runtime_typed.c -o <tmp>/_posix_rt.o`（本机默认 Windows 分支）
- 输出：`exit=0`；**0 error、45 warnings，全部 `[-Wdeprecated-declarations]`**（strcpy/strcat 等，UCRT 特有，如 `runtime_typed.c:1042:13: warning: 'strcpy' is deprecated...`）。完整输出已存 `G:/dswork/_posix_verify/logs/c1_runtime_compile.log`。
- **Linux/POSIX 分支编译未运行**：本 clang 无 Linux sysroot，`--target=x86_64-linux-gnu` 会在 `#include <sys/socket.h>/<poll.h>` 处缺头失败（环境缺头，非代码错误）。POSIX 分支头文件集合（`<unistd.h>/<sys/socket.h>/<netinet/in.h>/<arpa/inet.h>/<sys/select.h>/<netdb.h>/<fcntl.h>`，runtime_typed.c:40-46）对 glibc 完备；文件里还留有一段注释说明 `fcntl.h` 在 FreeBSD 上必须显式包含（否则 4 个 undeclared identifier），该问题已修。

**C.2 POSIX 侧实现真伪（代码阅读 + Windows 侧共享逻辑实测）**
- **socket**：真实现。POSIX 分支用 BSD socket API：`socket()/connect()/send()/recv()/close()/fcntl(O_NONBLOCK)`，错误码走 `errno`（runtime_typed.c:4372-4504）。未在 Linux 执行。
- **poller**：真实现，**Linux 走 `poll()`，不是 epoll**。后端选择是编译期宏（runtime_typed.c:4547-4556）：`_WIN32 → WSAPoll`，否则 `DV_POLLER_BACKEND_POLL`（`#include <poll.h>`，等待在 4795 行 `ready = poll(...)`）。**任务书里「Linux 走的是 epoll 还是 select」的 epoll 前提不成立**——代码选的是 poll，select 仅是 `-DDV_POLLER_FORCE_SELECT` 编译期 fallback。未在 Linux 执行。
- **事件循环**：真实现，非同步退化。`dv_scheduler_run_event_loop`（5004-5072）→ `dv_coro_resume`（Duff's device，4148）→ `dv_poller_wait_n`（POSIX 上即 poll）→ 就绪 fd 对应的协程回 run_queue；只有定时器时 `dv_platform_sleep`。挂起/恢复机器是平台无关 C 代码，Windows 上 coro_sleep 用例（源码 3）输出行序 `["开始","sleep前","sleep后","结束"]` 全绿即证明该链路真实工作。POSIX 与 Windows 的唯一差异是等待原语（poll vs WSAPoll）。**「50ms 睡眠在 Linux poll 上真实等待」未运行验证**（无 Linux）。
- **TLS**：**有壳无实现（stub）**。整个 B2-4 TLS 段在 `#ifdef _WIN32` 内（5111-5778，Schannel），非 Windows 分支（5747-5778）提供全套 `dv_tls_*` 桩函数，全部调用 `dv_tls_unsupported()` → 错误文本 `"本平台未实现原生 TLS：当前只有 Windows Schannel 后端（POSIX 待补 mbedTLS）"`，`dv_tls_wrap` 返回 NULL、`dv_tls_handshake/send/recv` 返回 `DV_TLS_ERROR`、`dv_tls_backend()` 返回 `"none"`。结论三选一：**Linux 上 TLS = 有壳无实现**，函数存在（链接不失败）但任何握手调用立即失败；因此也不存在可跑的公网握手（未运行）。

**C.3 Windows 独有 API 依赖清单**（每个都有 POSIX 对应或桩）

| Windows API | 用途 | POSIX 对应 |
|---|---|---|
| `WSAStartup` | winsock 初始化 | 无需（socket 默认可用） |
| `WSAGetLastError` | 错误码 | `errno` |
| `closesocket` | 关套接字 | `close` |
| `ioctlsocket(FIONBIO)` | 非阻塞 | `fcntl(F_GETFL/F_SETFL/O_NONBLOCK)` |
| `WSAPoll` | IO 多路复用 | `poll` |
| Schannel（`AcquireCredentialsHandle`/`CertVerifyCertificateChainPolicy`/`HCERTSTORE`/`Crypt*`） | TLS | **无实现（桩，返回失败）** |
| `_CRT_SECURE_NO_WARNINGS` 体系（strcpy_s 等提示） | MSVC 安全告警 | glibc 无此告警体系 |
| `<winsock2.h>/<windows.h>/<io.h>/<direct.h>`、`_access` | 平台头/函数 | `<unistd.h>/<sys/socket.h>` 等 |

除 TLS 外，POSIX 侧没有「依赖 Windows 独有 API 而编不过」的候选——头文件集合与 API 对应已由 `#ifdef _WIN32/#else` 成对给出，且 45 条 warning 全是 UCRT 专属（Linux 上不会出现）。

### D. CLI 交付路径

- **D.1** 命令：`python3 -m cli.light run <tmp>/cli_hello.light --backend llvm-typed` → 输出 `rc=0 stdout='cli alive'`，stderr 空。`run --backend` 接受 `llvm-typed`（**修复已合入**，非修复前版本），端到端可用。
- **D.2** 命令：`退出(3)` 程序同命令 → 输出 `D.2 rc=3 (期望 3) stdout='准备退出' -> PASS 恰好3`。退出码**恰好 3**，不是 0/1。
- **D.3** 跑完后 `ls -la` 源文件所在目录：只有 `cli_hello.light` 一个文件，**无 .ll/.o/.exe 残留**（cli 的编译产物落在临时目录）。

### E. 全量测试基线（Windows 侧，17 分 40 秒跑完）

**E.1** 命令：`python3 -m pytest tests --ignore=tests/e2e -q -p no:cacheprovider --tb=line`
汇总行（直抄）：
```
16 failed, 4072 passed, 63 skipped, 1 xfailed, 45 warnings, 6 errors, 237 subtests passed in 1060.51s (0:17:40)
```
⚠️ **注意：这是 Windows 基线**。Linux 基线未跑（无内核）。分类（对 16 failed + 6 errors）：

| 类别 | 数量 | 明细（文件:行号） |
|---|---|---|
| 缺可选依赖 | 15 | `tests/test_datetime.py` ×8：`stdlib/日期时间.py:733,741 RuntimeError: 农历转换需要 lunardate 库`；`tests/test_lightpub_bridge.py` ×6 ERROR：`ModuleNotFoundError: No module named 'requests'`；`tests/test_lightpub_doc_importability.py` ×1：`docs/lightpub/HTTP客户端.md:23 导入 → IMPORT_ERR: No module named 'requests'` |
| 沙箱/环境 artifact | 2 | `tests/unit/test_c_backend.py` ×2：`OSError: [safe-delete][SAFE_DELETE_FAIL_CLOSED] ... windows-sandbox-recycle-bin-unavailable`（WorkBuddy 沙箱回收站不可用，测试清理临时目录失败；**非项目缺陷**，Linux 上不会以同样方式失败） |
| 真实失败 | 5 | `tests/test_feature_core_light.py:278,310,323` ×3：`ERR:NameError:name '段' is not defined`（语言/代码生成语义 bug，与平台无关）；`tests/test_process_tree_light.py:201` ×1：`assert 'utf-8' != 'utf-8'`（平台编码探测断言）；`tests/test_pty_light.py:116` ×1：ConPTY 回显 `鍥炲０:hello`（UTF-8 被按 GBK 解码，Windows 专属功能） |

「测试写死 Windows 假设」类：**在 Windows 上它们全部通过**（所以不会出现在失败里），但它们正是 Linux 上会翻转的存量——全仓 `tests/` 有 **76 个文件引用 `.exe`、7 个引用 `ws2_32/WSA*`、10 个引用 `ConPTY/win32/ctypes.windll`**（样例：`tests/test_pty_light.py` 的 ConPTY 用例是 Windows 专属）。这些在真实 Linux runner 上预期会失败或 skip，属于跨平台闸门需要处理的面，但本环境未运行 Linux 无法给出确切清单。

**E.2** 命令：`python3 tools/ci/assert_quality.py --root .`
输出（直抄关键行）：
```
[假测试门禁] 扫描 .：命中 469 条违规
[假测试门禁] 无新增违规。
[假测试门禁] 通过：存量冻结、无新增。
```
与 Windows 侧 469 完全一致。**关于「基线键带 os.sep 导致 Windows 绿 Linux 红」的怀疑：现版本已修复**——工具用 `_posix()` 把键归一成 `/`（assert_quality.py:151-153、229），基线 `violations` 条目的 `file` 字段是 `antlrparser/self_hosted/test_tokenizer.py` 这种正斜杠路径；基线里 12 个反斜杠全部在 `text` 字段（引用的源码内容）里，不在键里。代码注释还点明了历史事故（gitea run 71 因键带分隔符在 FreeBSD runner 上红）。因此预期 Linux 上同为 469（键归一化 + 违规是文本模式扫描、与 OS 无关），但 Linux 侧**未运行**。

**E.3** 整文件 collect error：**0 个**（`grep -cE "ERROR collecting|could not be collected|error during collection"` = 0）。6 个 error 全是测试运行时错误（`requests` 缺失），不是收集错误，不存在「一批用例静默不跑」的情况。

### F. 缺 clang 时的行为

- **F.1** 命令：把 PATH 里含 LLVM 的条目摘除后跑 `pytest tests/test_llvm_net.py tests/test_native_cli.py -q`。输出汇总行（直抄）：`31 passed, 2 skipped in 171.89s (0:02:51)`。
  结论：**没有按预期 skip**——因为 `_find_clang_safely()`（tests/test_llvm_net.py:49-56）有硬编码候选 `C:\Program Files\LLVM\bin\clang.exe`，PATH 摘除后它仍命中。**Windows 上用「摘 PATH」无法模拟缺 clang**（与 A.1 同根因：硬编码绝对路径优先）。`LIGHT_CLANG` 环境变量在当前版本不存在（grep 无命中），任务书给的第二条路也不可用。
- **F.2** 逻辑接线验证：monkeypatch `os.path.exists` 对含 clang 的路径返回 False 模拟真正无 clang → `_find_clang_safely()=None`，`HAS_CLANG_LEG=False`，`skip_no_clang_leg` 条件为 True → **会正确 skip**。
- 结论：skip 逻辑本身正确；在真正无 clang 的 Linux runner 上会按设计 skip（未运行验证），但在 Windows 上被硬编码绝对路径候选挡住，无法用环境手段触发。

---

## 3. 十二格矩阵表

> 生产路径 `compile_light_typed(源, 基名, optimize_level=N)`，真编译+真运行+比对 stdout 行序。**全部为 Windows(_WIN32) 运行时 + clang 22.1.8**；Linux 侧未运行。每格 通过/失败 + 耗时；无失败格，故无报错原文。

| 源码 | O0 | O1 | O2 | O3 |
|---|---|---|---|---|
| hello（期望 `["hello world"]`） | **PASS** 6.45s | **PASS** 4.98s | **PASS** 5.17s | **PASS** 5.85s |
| socket19587（期望 `["-1","socket腿完成"]`） | **PASS** 4.21s | **PASS** 5.68s | **PASS** 5.54s | **PASS** 5.50s |
| coro_sleep（期望 `["开始","sleep前","sleep后","结束"]`） | **PASS** 3.85s | **PASS** 4.95s | **PASS** 5.33s | **PASS** 5.85s |

12/12 全绿，与「Windows 侧 A7 修完后全绿」一致；运行输出均与期望行序逐一相等、退出码 0。

---

## 4. 缺陷清单（按严重度排序）

**#1 [高] Windows LTO 链接必然失败**（影响：`--lto`/`optimize_size` 等走 LTO 的产物在 Windows 上全挂；Linux 未测）
- 现象：`compile_light_typed(..., lto=True)` → `RuntimeError: 链接失败: clang: error: LTO requires -fuse-ld=lld`
- 根因：链接步骤只加 `-flto`；`-fuse-ld=lld` 只在 `get_optimization_flags()` 的编译参数里（compiler.py:190），链接命令没带。Windows 默认链接器不认 LTO。
- 位置：`src/llvm/compiler.py:510-511`（compile_light）、`654-655`（compile_light_typed）、`1181-1182`（compile_light_project）
- 建议补丁（diff 文本，未提交）：
```diff
--- a/src/llvm/compiler.py
+++ b/src/llvm/compiler.py
@@ 三处链接点（compile_light 510-511 / compile_light_typed 654-655 / compile_light_project 1181-1182）同样处理：
     link_args.extend(get_link_libs())
     if lto:
         link_args.append('-flto')
+        if sys.platform == 'win32':
+            link_args.append('-fuse-ld=lld')
```
- 已验证：打上此补丁后 LTO 链接成功（rc=0，`hello lto fixed`），随后 `git checkout --` 还原。

**#2 [中] `find_clang` 硬编码绝对路径优先于 PATH / 环境**（影响：清 PATH 无效；§F「缺 clang→skip」在 Windows 无法用环境手段触发）
- 现象：PATH 清空后 `find_clang()` 仍返回 `C:\Program Files\LLVM\bin\clang.exe`；摘 PATH 跑原生测试 31 passed 而非 skip。
- 根因：候选表（compiler.py:823-827）把 Windows 绝对路径排在 `shutil.which` 探测之前；POSIX 候选 `/usr/bin/clang`、`/usr/local/bin/clang` 同理。
- 位置：`src/llvm/compiler.py:800`（find_clang）、`823-827`、`859-865`、`874-875`；测试侧同源 `tests/test_llvm_net.py:49-56`
- 建议（若想让「缺 clang→skip」可测）：
```diff
--- a/src/llvm/compiler.py
+++ b/src/llvm/compiler.py
@@ find_clang() 内，把 PATH/shutil.which 探测挪到硬编码候选之前，并支持显式覆盖：
+    env_clang = os.environ.get('LIGHT_CLANG')
+    if env_clang and os.path.exists(env_clang):
+        return env_clang
+    found = shutil.which('clang')
+    if found:
+        return found
     # ...再回落硬编码候选列表
```

**#3 [中] POSIX TLS 有壳无实现**（影响：Linux 上任何 TLS 功能立即失败）
- 现象：非 Windows 分支所有 `dv_tls_*` 走 `dv_tls_unsupported()`，错误文本「本平台未实现原生 TLS：当前只有 Windows Schannel 后端（POSIX 待补 mbedTLS）」，返回 NULL/DV_TLS_ERROR；`dv_tls_backend()=="none"`。
- 根因：设计上只有 Schannel 后端，POSIX 未实现 mbedTLS/OpenSSL 后端。
- 位置：`src/llvm/runtime_typed.c:5747-5778`（`#else /* 非 Windows */` 段）
- 建议：按注释计划补 mbedTLS 后端（工作量大，非小 diff）；在此之前，语言层应在 TLS 调用失败时给出可读错误而不是让用户收到裸 `-1`。此项是已知缺口而非回归。

**#4 [低] `test_feature_core_light.py` 3 条真实语义失败**（与平台无关）
- 现象：`映射(…, 平方)` 等调用实际返回 `"ERR:NameError:name '段' is not defined"`，期望 `[1, 4, 9]` 等。
- 位置：`tests/test_feature_core_light.py:278`、`:310`、`:323`
- 根因：未深挖（属语言「段/函数作为值」语义 + 代码生成问题，与 POSIX/clang 无关）；现象已实测固定。

**#5 [低] `test_process_tree_light.py:201` 编码探测断言失败**
- 现象：`assert 'utf-8' != 'utf-8'` 恒假 → 测试必败。测试意图是「默认编码按平台探测而非硬编码 UTF-8」，本机探测返回 `utf-8`。
- 位置：`tests/test_process_tree_light.py:201`
- 根因：未深挖（平台编码探测在 Python 3 环境下返回 utf-8 属正常，断言本身自相矛盾，疑似测试假设 Windows 控制台编码非 utf-8）。

**#6 [低] `test_pty_light.py:116` ConPTY 回显乱码**（Windows 专属）
- 现象：期望 `回声:hello`，实际 `鍥炲０:hello`（UTF-8 输出被按 GBK 解码的 mojibake）。
- 位置：`tests/test_pty_light.py:116`
- 根因：输出捕获编码不匹配；ConPTY 是 Windows 专属，Linux 无此测试面。

**#7 [环境] `test_c_backend.py` 2 条失败 = 沙箱回收站不可用**（非项目缺陷）
- 现象：`OSError: [safe-delete][SAFE_DELETE_FAIL_CLOSED] {"target": "...tests\\_temp_cbackend", "reason": "windows-sandbox-recycle-bin-unavailable"}`
- 位置：`tests/unit/test_c_backend.py`（`test_generate_c_file` / `test_generate_c_file_custom_path`）
- 说明：WorkBuddy Windows 沙箱的 safe-delete 拦截因回收站不可用而失败，测试清理临时目录失败。真实 Linux/CI 环境无此机制。残留目录 `tests/_temp_cbackend/` 已清理。

**#8 [环境] 缺可选依赖导致 15 条失败/error**（非平台问题）
- `lunardate` 未装 → `tests/test_datetime.py` 8 条（`stdlib/日期时间.py:733,741`）
- `requests` 未装 → `tests/test_lightpub_bridge.py` 6 条 ERROR + `test_lightpub_doc_importability.py` 1 条
- 建议：CI 装这两个依赖，或相关测试用 `pytest.importorskip`/skipif 优雅跳过（与 F 节「skip 而不是 error」口径一致）。

---

## 5. 未能验证的东西（以及为什么）

1. **Linux 内核上的任何执行面**：poller(`poll`) 运行时行为、事件循环在 poll 上的真实等待（50ms 睡眠）、POSIX 分支 `clang -c` 编译、Linux LTO 链接、Linux 12 格矩阵、Linux pytest 基线、Linux assert_quality 数字、Linux 上「缺 clang → skip」。原因：本沙箱为 Windows（MINGW64），WSL 被安全策略禁用、Docker 未安装、clang 无 Linux sysroot（`--target=x86_64-linux-gnu` 会在系统头文件处失败，属缺头不是代码错误）。
2. **A.2 的 Linux 真实链接报错原文**（`-lpthread`/`-ldl` 缺省会如何）：本环境无 Linux 链接器；只能给出代码事实（无 pthread/dlopen 引用 → `['-lm']` 足够）。
3. **TLS 公网握手**：即便有 Linux，POSIX TLS 也是 stub（§C.2），不存在可跑的实现。
4. **§E.1 的 Linux 失败集**：Windows 上通过的 76 个 `.exe` 引用文件 / 10 个 ConPTY/win32 文件在 Linux 上预期翻转，但确切清单需真实 Linux runner。
5. **legacy pass 名精确拒绝版本号**：仅确认 22.1.8 拒绝 + 机制（LLVM 14 新 PM 默认化），未逐小版本回溯。

---

## 6. 为定位改过的文件

| 文件 | 改了什么 | 是否已还原 |
|---|---|---|
| `src/llvm/compiler.py` | A.4 LTO 诊断：在 3 个链接点临时加 `if sys.platform=='win32': link_args.append('-fuse-ld=lld')` | ✅ `git checkout -- src/llvm/compiler.py` 已还原；`git status` 干净 |
| `tests/_temp_cbackend/` | 不是改，是 test_c_backend 在沙箱里删不掉的残留目录 | ✅ 已 rm 清理；`git status --porcelain` 为空 |

所有验证中间产物（.ll/.o/.exe、日志）都在 `tempfile.TemporaryDirectory(prefix='_posix_')` 或独立证据目录 `G:/dswork/_posix_verify/`（在 wt-A7 源码树之外）；复核 `find wt-A7 -name '_posix_*'` 为**空**。未 push、未提交任何改动。
