# R159-A 任务文本 —— L-216：多模块编译路径丢弃 `异步` 修饰符（`src/llvm` 深水）

> 全文与「铁律」以 `_R159_并行任务书.md` 为权威（**先 Read 整篇**）。本文件是被派单代理读的那一份，自包含。
> 工作目录：`G:\dswork\duan-light-merge\light-merge`。**不 commit / 不 push / 不做任何 git 写操作。**

## 你的任务

修复 L-216：`compile_modules_typed` 段落生成循环**不传 `modifiers`**，导致任何带 import 的（多模块）
原生腿程序，其全部 `异步` 段按普通函数编译——无协程状态机、`创建任务` 实参立即求值、
模块级 `异步 运行` 双执行。后果：原生分布式 worker 的**领任务循环不可达**（实测领任务=0/12874）。

**判据核心是 IR 实证，不是行为绿**——本缺陷的假绿形态正是「看起来能跑但协程根本没生成」。

## 先读（必须读完再动手）

1. `_R159_并行任务书.md`（整篇；重点 §一1.1、§四 A 线、§五 独占矩阵、§六 铁律）
2. `src/llvm/compiler.py:1120-1155`（`compile_modules_typed` 段落生成循环）
3. `src/llvm/codegen_typed.py:1240-1260`（**单模块路径**的正确写法）、`:89`、`:5455-5465`、`:7719-7730`
4. `src/llvm/codegen_typed.py:8340-8430`（`_count_await_in_node` 全部递归分支）
5. `src/llvm/codegen_typed.py:5156-5240`（`_gen_typed_try` 的 setjmp 实现）
6. `src/ast_nodes.py`（语句/表达式类清单，用于连带面穷举）

## 现状要点（起草时已核实，请亲自复核）

- 病灶：`compiler.py:1141`
  ```python
  codegen._gen_typed_segment(seg_name, params, body, module_name=mod_name, reg_key=reg_key)
  ```
  不传 `modifiers`；单模块路径 `codegen_typed.py:1252-1253` 是
  `modifiers = self._segment_modifiers.get(reg_key, [])` 后传入。`_segment_modifiers`
  在 `:89` 初始化、`:5460-5462` 收集——**收集了但多模块生成侧从没用**。
- 溯源：pre-R130（`8155d638e~1:1081`）即缺失，R144 image（`988c91a57:1093`）同样——
  **不是本轮回归**，R144-era 压测跑的就是直接调用语义（同口径）。
- 实测症状（R158-C）：领任务=0/12874、`节点ID="N"`（`随机十六进制(8)` 类方法上下文返空）、
  顶层段探针正常（`"NAD27A43C"`）。

## 做法要点（顺序不可颠倒）

1. **连带面评估先行（结论进报告，再动修）**：
   - **`_count_await_in_node` 缺口穷举**：对照 `src/ast_nodes.py` 逐类核对。已知未覆盖：
     `TryStatement`（try_body/catch_clauses/catch_body/finally_body）、`MatchStatement`、
     `WithStatement`、`YieldStatement`、`ThrowStatement`、`PrintStatement`、`DeferStatement`、
     `AsyncScope`、`RunAsyncStmt`，以及 `ListComprehension/DictComprehension/LambdaExpression` 等表达式容器。
     结论二选一：(i) **补齐递归**（推荐按「有 body/子节点列表的节点统一递归」写，避免逐类漏）；
     (ii) 逐类论证可接受并写明风险（**不许笼统「不影响」**）。
   - **`_gen_typed_try` × 协程兼容性**：写 try-in-coroutine 探针（try 内有 `等待`/`睡眠` + catch），
     记录实际行为。结论三选一：(i) 改造为协程安全形态（超工作量则登记不修）；
     (ii) **编译期响亮拒绝**（异步段内 try → 明确报错，**这是兜底底线：宁可报错不许崩**）；
     (iii) 论证组合不可达并写明前提。
2. **修 modifiers**：`compiler.py:1141` 按单模块路径同口径传
   `modifiers=codegen._segment_modifiers.get(reg_key, [])`。若评估要求补齐 `_count_await_in_node`，同批完成。
3. **IR 实证**：构造**多模块**异步探针（主模块 import 一个含 `异步 段` 的模块 + `创建任务` + `等待`），
   dump IR：修复前 `dv_coro_create`/`dv_coro_await` **0 次**、无 switch case-range；
   修复后 **>0 次**、switch 存在、`main()` 无双执行。
4. **行为实证**：分布式 worker 实跑（mini-master 在位）——**领任务 > 0**、**节点 ID 正常**（`"N"`+8 位十六进制）、
   无双执行。0.82 窗口排不上可用 0.86（写明），收口联合 E2E 兜底。
5. **回归**：`test_native_leg_capability.py` + 既有异步回归（`tests/unit/test_R119*`/`test_R156*`/
   `test_原生腿_*` 协程相关）+ 双 gen `--check` RC=0。
6. **反跑锚点**：临时改回「不传 modifiers」→ IR 协程消失 + 领任务=0 复现；恢复后全绿。**跑完恢复，不留痕**。

## 必跑

L0 本机（探针 + 定向 + 双 gen）→ L2 0.86 平台批 → 收口 L1 全量门由主 agent 统一跑（**你不许自行触发 0.82 全量门**）。

## 禁令

- 不许把 `is_async` 判定改成「猜」（`modifiers` 是唯一真源）。
- 不许为绿而绕过 IR 实证；不许只凭行为绿声称修复。
- 不许动 `src/llvm/runtime_typed.c`（D 线文件）、`stdlib/**`、`tests/unit/test_原生腿_*`（D 线范围）。
- 不许扩 scope 到 `_gen_typed_try` 的全面改造（只做评估 + 兜底拒绝）。
- 行尾：改 `compiler.py`/`codegen_typed.py` 保持文件既有行尾（git autocrlf 会归一，报告写明字节级自检结果）。

## 交付

写 `_R159_A线交付报告.md`：连带面评估结论**逐类表** / IR 前后对照摘录（`dv_coro_create` 计数 + switch 证据）/
领任务与节点 ID 实测（含机器与命令）/ 反跑证据 / 新发现问题（含需立号的，从 L-219 起，先 grep 确认未用）。
**完成后用 SendMessage 给 main 发结构化汇报（含真实命令与退出码；没跑过的写「未跑」）。**
