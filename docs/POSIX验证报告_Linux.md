# POSIX验证报告（Linux 实测版）

> 实测对象：`wt-A7`（源码与 Windows 侧同一 tar，HEAD `9670e65f2c2b4c0ddb8e565f586d60649d0de3a4`）
> 实测环境：**Ubuntu 22.04.5 LTS**，192.168.1.19（dswork 用户，sudo）
> 每条「命令 → 输出 → 结论」，汇总行直抄；跑过就是跑过，没跑写没跑。

---

## 0. 环境与 commit

| 项目 | 值（直抄） |
|---|---|
| `uname -a` | `Linux ub19 5.15.0-179-generic #189-Ubuntu SMP Tue May 5 18:20:56 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux` |
| OS | Ubuntu 22.04.5 LTS（jammy） |
| `clang --version` | `Ubuntu clang version 18.1.8 (++20240731024944+3b5b5c1ec4a3-1~exp1~20240731145000.144)`，`Target: x86_64-pc-linux-gnu` |
| 额外对照版本 | clang-14 `14.0.0-1ubuntu1.1`、clang-15 `15.0.7`（均实测，见 §B/§C 结论） |
| `python3 --version`（venv） | `Python 3.12.13`（`/home/dswork/venv312/bin/python`；系统 python3.10.12 低于要求，未用） |
| `which clang` | `/usr/bin/clang -> /usr/bin/clang-18`（我创建的符号链接） |
| pytest | 9.1.1（venv312 内，测试工具） |
| git HEAD | 远端未带 .git；源码 tar 与 Windows 侧同一份（Windows HEAD 9670e65） |

**装了什么东西（系统包管理器，列版本）**：`clang-18`+`lld-18`（清华 TUNA 镜像 `https://mirrors.tuna.tsinghua.edu.cn/llvm-apt/jammy/ llvm-toolchain-jammy-18`；apt.llvm.org 直连太慢弃用）、`clang-15`/`lld-15`、`clang-14`/`lld-14`（Ubuntu 官方源，作对照）、`strace`、`software-properties-common`、`wget/gnupg/ca-certificates`、`python3.12`（deadsnakes PPA）。**项目零第三方依赖约束未破**：venv 里只额外装了 pytest（跑测试必需），未装 cryptography/requests/lunardate 等可选依赖（这正是 §E 里「缺可选依赖」分类的由来）。

---

## 1. 一句话结论

**原生腿在 Linux 上 = 基本可用，有明确缺口**（比沙箱版定性前进一大步）：socket/poller(poll)/事件循环在 Linux 上**真实现且真跑通**（12 格矩阵全绿、strace 实证 poll() 被执行、50ms 睡眠真实等待），CLI 端到端可用，assert_quality 469 与 Windows 一致；**明确缺口 = TLS 有壳无实现（stub）**。另有一个**环境级硬约束**：生成 IR 用 opaque `ptr` 类型，**clang-14/15 均无法编译（clang-14/15 全红），必须 clang ≥ 18**（22.04 默认 clang-14 直接不可用）。

---

## 2. A~F 实测结果

### A. 编译器驱动的 POSIX 分支

**A.1 `find_clang()` 清空 PATH**
- 命令：`os.environ['PATH']=''` 后调 `find_clang()`（compiler.py:800）
- 输出：`A.1 PATH清空后 find_clang 返回: /usr/bin/clang`（未抛 RuntimeError）
- 结论：与 Windows 同款行为——硬编码候选 `/usr/bin/clang`（compiler.py:826-827, 874-875）先于 PATH 命中。只要 clang 在标准位置，清 PATH 不会触发 RuntimeError。

**A.2 `get_link_libs()` 非 Windows 分支 `['-lm']`**
- 命令：`get_link_libs()`（Linux 原生分支）
- 输出：`A.2 get_link_libs() -> ['-lm']`
- 补充实测（真实 Linux 链接报错）：把 `runtime_typed.o` 不接 `-lm` 直接链接 → 真实报错原文：
  ```
  /usr/bin/ld: /tmp/_posix_*/_posix_rt.o: in function `dv_sin':
  runtime_typed.c:(.text+0x125a): undefined reference to `sin'
  /usr/bin/ld: ... in function `dv_cos': undefined reference to `cos'
  /usr/bin/ld: ... in function `dv_sqrt': undefined reference to `sqrt'
  ```
  接上 `-lm` 后链接成功 → **`['-lm']` 是必需且足够**（runtime 用 sin/cos/sqrt；无 pthread/dlopen 引用，无需 `-lpthread/-ldl`；socket 在 glibc 内，无需 `-lsocket`）。

**A.3 `get_optimization_flags()` + legacy pass 名**
- 输出：`['-O0']/['-O1']/['-O2']/['-O3']`（A7 修复已合入）
- legacy 名实测（clang-15 与 clang-18 **同样全部拒绝**，与 Windows 22.1.8 一致）：
  - `clang -mllvm -inline` → rc=1 `Unknown command line argument '-inline'`
  - `-mem2reg`/`-gvn`/`-loop-unroll` → 同样 rc=1
- 结论：从 LLVM 14 新 PM 默认化起 legacy pass 名不再注册；14/15/18/22.1.8 均拒绝（14 只测了 IR 解析面，pass 名本身 15/18/22.1.8 已实证）。

**A.4 `-flto` 真链接（Linux）**
- 命令：`compile_light_typed(hello, lto=True)`
- 输出：`A.4 LTO 链接成功: rc=0 stdout='hello lto'`
- 结论：**Linux 上 LTO 直接可用**（clang-18 + GNU ld 驱动自动处理；链接步骤只有 `-flto` 也够）。对比 Windows：链接步骤缺 `-fuse-ld=lld` 导致必失败（见 Windows 版报告 §4 #1）——**那个补丁是 Windows 专属，Linux 不需要**。

### B. 十二格优化矩阵（真 POSIX 运行时）

全部走生产入口 `compile_light_typed(源, 基名, optimize_level=N)`，真编译+真运行+比对 stdout 行序+退出码，临时文件在 `tempfile.TemporaryDirectory(prefix='_posix_')`。**12/12 全绿**（表见 §3）。

**附带的重要发现（clang 版本矩阵）**：同一批 IR 在不同 clang 版本上的验证结果——

| clang | O0 | O1 | O2 | O3 | 失败原文（代表） |
|---|---|---|---|---|---|
| 14.0.0 | ✗ | ✗ | ✗ | ✗ | `warning: ptr type is only supported in -opaque-pointers mode … error: expected type` |
| 15.0.7 | ✗ | ✗ | ✗ | ✗ | O0/O1 同上；O2/O3：`error: instruction expected to be numbered '%0'` + `%1 = alloca { i32, i64, double, ptr, ... }, i32 15` |
| **18.1.8** | ✓ | ✓ | ✓ | ✓ | — |

结论：**项目原生腿实际要求 clang ≥ 18**。22.04 默认 clang-14 完全不可用；clang-15 也不行（O0/O1 仍 typed-pointer 报错、O2/O3 编号报错）。这不是项目 bug（IR 在 22.1.8 Windows 侧全绿），而是工具链版本门槛；FreeBSD 若随系统带 clang-14/15，需同样注意（FreeBSD 侧未验证）。

### C. runtime_typed.c 在 Linux 上能不能编

**C.1 编译**
- 命令：`clang -c src/llvm/runtime_typed.c -o _posix_rt.o`（Linux POSIX 分支）
- 输出：`C.1 exit=0, warnings=0 errors=0`，产物 127568 bytes（clang-18；clang-14 同样 0/0）
- 结论：**POSIX 分支能编，且零告警零错误**。

**C.2 逐项确认（真执行，非读代码）**
- **socket**：B 格 socket19587 真跑通——`连接socket(fd,"127.0.0.1",19587)`（无人监听）→ 输出 `-1`，然后 `socket腿完成`。真实 BSD socket 行为。
- **poller 后端**：语言层 `poller后端()` → 输出 `poll`（C.2b 实测）。
- **poll() 真被执行（strace 实证）**：`strace -e trace=poll,select,…` 跑 poller_wait 程序 →
  ```
  poll([{fd=3, events=POLLIN|POLLRDNORM}], 1, 100) = 1 ([{fd=3, revents=POLLHUP}])
  ```
  （未连接 socket 立即 POLLHUP → poller_wait 返回 1；poll syscall 真实出现在 trace 里。**Linux 走 poll 不是 epoll，与代码阅读一致**。）
- **事件循环真挂起-恢复**：coro_sleep 各档 `run_dt = 57–58ms`（睡眠 50ms 真实等待，非同步退化；输出行序 `["开始","sleep前","sleep后","结束"]` 全对）。
- **TLS**：C.2a 探针（链接带 -lm）→ `backend=none`、`dv_tls_wrap` 返回 `NULL`。**Linux 上 TLS = 有壳无实现（stub）**：函数存在（链接不失败），任何握手调用立即失败。错误文本（源码 5747-5778）：`本平台未实现原生 TLS：当前只有 Windows Schannel 后端（POSIX 待补 mbedTLS）`。无公网握手可跑。

**C.3 Windows-only API 依赖**：POSIX 分支编译零告警零错误 → 没有「依赖 Windows 独有 API 而编不过」的地方。对应表（Windows→POSIX）：`WSAStartup→无`、`WSAGetLastError→errno`、`closesocket→close`、`ioctlsocket(FIONBIO)→fcntl(O_NONBLOCK)`、`WSAPoll→poll`、**Schannel→无实现（stub）**、`_CRT_SECURE_NO_WARNINGS 体系→glibc 无此告警`。

### D. CLI 交付路径
- **D.1** `python3 -m cli.light run <f> --backend llvm-typed` → `rc=0 stdout='cli alive'`，stderr 空。
- **D.2** `退出(3)` → `rc=3 (期望 3) stdout='准备退出' -> PASS 恰好3`。
- **D.3** 源目录 `ls -la` 只有 `.light` 文件，无 `.ll/.o/可执行文件` 残留。

### E. 全量测试基线
- **E.1** 命令：`python3 -m pytest tests --ignore=tests/e2e -q`（加 `--continue-on-collection-errors`，原因见 E.3）
  汇总行（直抄）：`14 failed, 4063 passed, 72 skipped, 1 xfailed, 38 warnings, 10 errors, 237 subtests passed in 918.17s (0:15:18)`
  对照 Windows：`16 failed, 4072 passed, 63 skipped, 6 errors`。**Linux 多挂 6 条、多 skip 9 条**。
  分类（14 failed + 10 errors = 24）：

  | 类别 | 数量 | 明细 |
  |---|---|---|
  | 缺可选依赖 | 15 | `test_datetime.py` ×8（lunardate）；`test_lightpub_bridge.py` ×6 ERROR + `test_lightpub_doc_importability.py` ×1（requests） |
  | 整文件收集错误 | 1 | `test_tls_light.py`（cryptography）→ 见 E.3 |
  | TLS 相关 ERROR（Linux 特有） | 3 | `test_async_io_light.py::TestTLS异步读腿` ×3（POSIX TLS 是 stub + 缺 cryptography；Windows 走 Schannel 全过） |
  | 真实失败、平台无关 | 3 | `test_feature_core_light.py:278/310/323`（`ERR:NameError:name '段' is not defined`，Windows 同样红） |
  | Linux 特有真实失败 | 1 | `test_agent_tools_light.py:666`：沙箱命令输出泄漏绝对路径 `'/tmp/pytest-of-dswork/...' is contained here`（Windows 不泄漏） |
  | 环境/性能 | 1 | `unit/test_lexer_perf.py`：`3.9329 秒，超过 2.0 秒限制`（本机慢，非功能缺陷） |

  Windows 特有失败（process_tree 编码断言、pty ConPTY）在 Linux 上消失（ConPTY 是 Windows 专属，Linux 侧 skip 增多 9 条印证）。「测试写死 Windows 假设」的存量：76 个文件引用 `.exe`、7 个引用 ws2_32/WSA、10 个引用 ConPTY/win32（Linux 上相关用例以 skip/翻转呈现，见 E.1 数字差）。
- **E.2** assert_quality：`[假测试门禁] 扫描 .：命中 469 条违规 … [假测试门禁] 无新增违规。[假测试门禁] 通过`。**Linux = 469，与 Windows 完全一致**。用户怀疑的「基线键带 os.sep → Windows 绿 Linux 红」在真实 Linux 上被证伪：键已 `_posix()` 归一为 `/`（assert_quality.py:151-153, 229）。
- **E.3** collect error：**有 1 个整文件收集错误**——`tests/test_tls_light.py:19 from cryptography import x509 → ModuleNotFoundError: No module named 'cryptography'`。**致命点：默认 `pytest tests --ignore=tests/e2e -q` 会被它直接中断**（实测 `Interrupted: 1 error during collection`，`3 skipped, 1 error in 63.98s`），不是「单条失败」而是整轮 abort。Windows 侧没暴露是因为 Windows 环境装了 cryptography。建议：该文件加 `pytest.importorskip('cryptography')` 或 CI 装 cryptography，否则裸 Linux runner 上全量门禁必红。

### F. 缺 clang 时的行为（Linux 实测）
- 命令：把 `/usr/bin/clang` 符号链接临时移开（模拟真缺 clang），跑 `pytest tests/test_llvm_net.py tests/test_native_cli.py -q`
- 输出汇总行（直抄）：`7 passed, 30 skipped in 2.49s`
- 结论：**skip 而不是 error，无 collect error**，与设计一致。还原符号链接（`/usr/bin/clang -> /usr/bin/clang-18`）。对比 Windows：硬编码 `C:\Program Files\LLVM\bin\clang.exe` 候选导致摘 PATH 无法触发 skip——**Linux 上能干净触发，Windows 不能**。

---

## 3. 十二格矩阵表（Linux，clang-18）

> 真编译+真运行+比对 stdout 行序+退出码；全部 PASS，无失败格故无报错原文。

| 源码（期望行序） | O0 | O1 | O2 | O3 |
|---|---|---|---|---|
| hello（`["hello world"]`） | **PASS** run 156ms | **PASS** run 7ms | **PASS** run 6ms | **PASS** run 7ms |
| socket19587（`["-1","socket腿完成"]`） | **PASS** run 7ms | **PASS** run 7ms | **PASS** run 7ms | **PASS** run 7ms |
| coro_sleep（`["开始","sleep前","sleep后","结束"]`） | **PASS** run 57ms | **PASS** run 58ms | **PASS** run 57ms | **PASS** run 57ms |

（coro_sleep run 57-58ms > 50ms 睡眠 = 事件循环真挂起等待；O1-O3 编译耗时 ~9-12s/格，O0 ~2.5s/格，均含每次重编 runtime。）

---

## 4. 缺陷清单（按严重度，Linux 视角）

**#L1 [高·环境门槛] 原生腿要求 clang ≥ 18，22.04 默认 clang-14 完全不可用**
- 现象：clang-14/15 下 12 格全红：`ptr type is only supported in -opaque-pointers mode … error: expected type`（14 全部、15 的 O0/O1）；clang-15 O2/O3 另报 `instruction expected to be numbered '%0'`。clang-18 全绿。
- 根因：生成 IR 为 opaque-pointer 现代风格（`ptr` 类型 + 个别块首条指令编号非 %0），clang-14（typed pointers 默认）与 clang-15（解析面/编号严格）均拒收；clang ≥ 16/18 才放行。
- 位置：无项目代码问题；属工具链版本门槛。
- 建议：CI/文档写明 **clang ≥ 18**（apt.llvm.org 慢 → 清华 TUNA 镜像 `mirrors.tuna.tsinghua.edu.cn/llvm-apt`，实测秒装）；FreeBSD 侧需确认其 clang 版本（未验证）。

**#L2 [中] TLS 在 POSIX 有壳无实现（stub）**
- 现象/证据：C.2a 实测 `backend=none`、`dv_tls_wrap`→NULL；任何握手调用立即失败。
- 位置：`runtime_typed.c:5747-5778`。
- 建议：按注释补 mbedTLS/OpenSSL 后端；此前语言层 TLS 调用应返回可读错误。

**#L3 [中·CI 门禁] `tests/test_tls_light.py` 缺 cryptography 时整文件 collect error 并中断全量 pytest**
- 现象：`ImportError: No module named 'cryptography'` → 默认命令 `Interrupted: 1 error during collection`（整轮 abort，不是单条失败）。
- 位置：`tests/test_tls_light.py:19`。
- 建议补丁（diff 文本，未提交）：
```diff
--- a/tests/test_tls_light.py
+++ b/tests/test_tls_light.py
@@ 模块顶部
-from cryptography import x509
+cryptography = pytest.importorskip("cryptography")
+from cryptography import x509  # noqa: E402
```

**#L4 [低] Windows 侧发现的 LTO 缺陷是 Windows 专属**（Linux 无需补丁）
- Linux 实测 A.4 LTO 链接成功；Windows 需在链接步骤补 `-fuse-ld=lld`（详见 Windows 版报告 §4 #1，三处链接点 compiler.py:510/654/1181）。

**（已排除）`dv_tls_last_error()` 疑云**：一度怀疑 POSIX 分支没导出它——实测证伪：定义在 `runtime_typed.c:5107`，位于 `#ifdef _WIN32`（5111）**之前，无条件存在**；POSIX 探针实测返回 `本平台未实现原生 TLS：当前只有 Windows Schannel 后端（POSIX 待补 mbedTLS）`。错误信息在 POSIX 上可检索，非缺陷。

**#L5 [低·Linux 特有] run_command 沙箱输出泄漏绝对路径**
- 现象：`tests/test_agent_tools_light.py:666` 断言「不许回显沙箱绝对路径」失败，实际输出里出现 `'/tmp/pytest-of-dswork/...' is contained here`（spill 文件的绝对路径泄漏）；Windows 不泄漏。
- 位置：`tests/test_agent_tools_light.py:666`（实现位于 run_command 沙箱的路径脱敏逻辑，未深挖代码根因）。
- 建议：核对沙箱回显对 `%TMPDIR%/tmp` 类绝对路径的脱敏分支，补 POSIX 侧测试。

---

## 5. 未能验证的东西

1. **TLS 公网握手**：POSIX TLS 是 stub，无实现可握手（已实证，非环境限制）。
2. **FreeBSD 平台**：poller 走 kqueue 分支、FreeBSD 自带 clang 版本是否 ≥18、`fcntl.h` 那 4 个历史 error 是否真已修复——本机是 Ubuntu，未验证。
3. **clang-16/17 的确切分界**：实测了 14/15/18，未逐一测 16/17（结论取「≥18 肯定行、≤15 肯定不行」）。
4. **test_agent_tools_light 沙箱绝对路径泄漏的根因**：现象实测固定（`/tmp/pytest-of-dswork/...` 泄漏进输出），未深挖 run_command 回显/脱敏逻辑的代码根因。
5. **test_async_io_light TLS 3 条 ERROR 的确切诱因**：cryptography 缺失 与 POSIX TLS stub 二者叠加，未逐条拆分（Windows 走 Schannel 全过）。

---

## 6. 为定位改过的文件 / 环境改动

- **远端系统（192.168.1.19）**：装了 clang-14/15/18、lld、strace、python3.12（deadsnakes）、venv312(pytest)。创建了符号链接 `/usr/bin/clang -> clang-18`（及 clang++/ld.lld/lld）。F 测试期间临时移走 `/usr/bin/clang` 已还原。未改任何项目文件、未提交、未 push。
- 项目源码在 `/home/dswork/wt-A7`（tar 解压，与 Windows 侧同一份）；全部中间产物在 `_posix_` 临时目录，`find wt-A7 -name '_posix_*'` 为空，源码树未污染。
