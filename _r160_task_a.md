# R160-A 任务文本 —— L-219 必修：原生协程「self 绑定 + 恢复分派」两子缺陷修复

> 全文与「铁律」以 `_R160_并行任务书.md` 为权威（先 Read 整篇）。本文件是被派单代理读的那一份，自包含。
> 工作目录：`G:\dswork\duan-light-merge\light-merge`。**不 commit / 不 push / 不做任何 git 写操作。**
> **你是 R160 关键路径与唯一改 `src/llvm` 的线**：B/C/D 都依赖你交付的协程运行时。连带面评估先行，IR 实证 + SIGSEGV 前后是硬判据。

## 背景（一手坐实）

R159-A 修 L-216（`compiler.py:1141` 补传 `modifiers`、恢复 `is_async`）后，原生协程路径首次真实启用，暴露出此前 `is_async` 恒假时被掩盖的 latent bug 家族 **L-219**（缺陷账 §十九 已立号未修）。**L-219 含两个本轮必须一并修的子缺陷**：

- **子缺陷①（恢复分派 / L1 门红）**：顶层协程在 `睡眠`(await) 后恢复时**跳过后续语句**。
  实证 = L1 0.82 全量门 `tests/test_native_cli.py::Test优化档矩阵::test_四档产物真跑[协程-0]`
  `AssertionError: 协程 O0 输出不符: ['开始','sleep前','结束']`，期望含 `'sleep后'`。
  归因：**Duff 装置 switch 状态机 resume 偏移 / `_count_await_in_node` 递归覆盖家族**。
- **子缺陷②（self 绑定 / SIGSEGV）**：原生分布式 worker **心跳协程**体取 `己`（self）为**空** → `己.X` 空取下标 → **SIGSEGV**。
  实证 = A+B 共存态下 `从 节点 导入 主` 驱动注册后 **2.0s rc=-11、0 心跳**（C 线段②三次独立执行签名一致）；纯 HEAD 树（无协程）驱动可存活 3600s。

## 你的任务

把 L-219 两个子缺陷都修到**可判绿**：修后分布式 worker 能跨过注册、发心跳、领任务>0；`test_四档产物真跑[协程-0]` 输出恢复 `['开始','sleep前','sleep后','结束']`。

### 做法要点

1. **先做连带面评估（写进报告）**，再动刀：
   - `_count_await_in_node`（`codegen_typed.py:8350` 区）递归覆盖——逐个核 `TryStatement/MatchStatement/WithStatement/YieldStatement/ThrowStatement/PrintStatement/DeferStatement/AsyncScope/RunAsyncStmt` + 各 comprehension/lambda；结论二选一（补齐递归 / 论证某类可接受并逐类给理由）。
   - `_gen_typed_try`（`codegen_typed.py:5156` 区）内联 `setjmp` 与协程 switch 重入：R159-A 已证「不兼容需编译期拒绝」假设不成立、兜底拒绝非必要——**沿用该结论，除非你复测发现新崩点才升级处置并在报告显著标注**。
   - 协程 suspend/resume 时临时值/绑定帧存活：`己` 绑定为何丢失属本家族，修 self 绑定时必须顺带核对 resume 后局部/参数取回（`dv_coro_get_local/get_arg`）。
2. **子缺陷①**：用**顶层协程探针**（非方法体，隔离 self 因素）把恢复分派偏移定位到行；读通 `_count_await_in_node` / resume switch 发射，补正确。
3. **子缺陷②**：从 `创建任务`/协程创建路径查 self/参数帧如何进入协程 alloca；修到心跳协程 `己` 非空。

### 落点（只动这些）

- `src/llvm/codegen_typed.py`（主）；`src/llvm/runtime_typed.c`（仅实证必要）；`src/llvm/compiler.py`（仅实证必要）。
- 新建回归门 `tests/unit/test_R160_L219_协程恢复.py`：覆盖 §连带评估列出的每类表达式的协程恢复 + self 绑定 + 反跑。
- scratch：`_r160_scratch/a_*`。

### 必跑 + 验收判据（硬）

1. IR 实证 before/after：`dv_coro_create`/`dv_coro_await` 调用点、switch `resume__coro*` 臂——改前/改后贴证据（**只凭行为绿不算**）。
2. 本机：`test_四档产物真跑[协程-0]` **转绿** + `pytest .venv/Scripts/python.exe tests/unit/test_R160_L219_协程恢复.py` 全绿。
3. 0.82（`ai` 账号）：L3 联跑——**改前复现 SIGSEGV rc=-11、改后心跳发出 + 领任务>0**；两态都要有输出留证。
4. 0.86 Linux 复验红线转绿。
5. 反跑（有牙）：任子缺陷回退 → `sleep后` 丢失 / SIGSEGV 复现；贴命令 + 输出。

### 禁令

- 不 commit / 不 push / 不做 git 写；只动上列落点；禁 `git add .`（须逐文件）。
- 修法**最小侵入**，禁为凑绿改测试期望或改 `test_native_cli.py` 既有断言。
- 禁擅自扩大 `_gen_typed_try`/调度器重构；发现任务书外问题只登记进报告「新发现」，L 编号从 **L-220** 起（立号前先 grep）。

## 完成回传

- 交付 `_R160_A线交付报告.md`（落盘工作目录根），含：连带面评估、IR before/after、两子缺陷修法、SIGSEGV 改前/改后、0.82/0.86 判绿、反跑证据、新发现。
- 完成后 **SendMessage 给 main**（附报告路径 + test 输出文件路径 + 一句话结论）；阻塞也发（原因）。
- **铁律全文见 `_R160_并行任务书.md` §六，必须整篇 Read 后逐条遵守**（判绿以 0.82/0.86 远端为准，本机只初筛）。
