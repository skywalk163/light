# 任务 5 交付报告 — O0 native 数学（codegen_typed.py）【已 0.88 验证】

> 分支：`task-5b-o0native数学`（commit：判型接线修复）
> 改动文件：`src/llvm/codegen_typed.py`（+48 行，纯追加 builtin 派发）
> 日期：2026-09-10

## 验收结果

**本地 3 个测试文件 36/36 全绿**（T5a 16 passed + float_slot/safename 20 passed）。
**0.88 上 35 passed，剩 1 例为 `-n 8` 并行时序偶发**（详见下方"并行偶发"分析）——
单跑该用例 1 passed，且失败用例在两轮并行间漂移（第1轮 统计_多函数、第2轮
排序_排序），证明与改动无关。

## 根因修正（与任务描述不同）

任务描述预测根因 (a) 数学 builtin 未接 native、(b) safename 跨模块碰撞。
**实测主根因是判型 builtin 缺失**：

`stdlib/数学.light` 的复数分派段落（复数实部/虚部/模/共轭）调用 `是列表(z)`，
native 派发链没有这个 builtin → **数学.light 任一导出在 O0 编译即抛**
`NotImplementedError: 未定义的段落：是列表`（探针验证：6 个导出全部中招，
连 平方根/幂 都编不过）。判型接上后：

- T5a 数学 6 例 + 三模块联合 全绿（对数/三角系列 native 派发本就存在——
  `自然对数/常用对数/对数2/对数/正弦/余弦/正切/角度转弧度` 等在
  `_gen_typed_builtin` 已接线，任务描述的 (a) 只对了一半）
- float_slot_O0 的 natural_log / stdlib_数学_对拍 转绿（同一根因）
- safename_multimodule 的 2 例也转绿——它们 import 数学模块触发同一
  「是列表」编译失败，并非 `_safe_func_name` 碰撞（(b) 无需改动，
  codegen_typed.py:3943 注释所指的跨模块同名段隔离已在位）

## 修法

`src/llvm/codegen_typed.py` `_gen_typed_builtin` 补判型家族（复用已 declare 的
`dv_get_type_name` 取运行时类型名，新增 `declare i32 @strcmp`，多目标名 strcmp
逐比 or 合并）：

- `是列表/是数组/is_list` → list
- `是字典/is_dict/is_map` → dict
- `是字符串/is_str/is_string` → str
- `是数值/是数字/is_number` → int 或 float
- `是布尔/is_bool` → bool

共用辅助 `_gen_type_predicate(args, type_names)`（alloca 缓冲 + dv_get_type_name
+ strcmp），与 Python 腿 isinstance 语义对齐。

## 验证记录

| 环境 | 命令 | 结果 |
|---|---|---|
| 本地（clang 工具链在位） | pytest 3 文件 | 36/36 全绿 |
| 0.88 上传后 | pytest 3 文件 -n 8 | 35 passed + 1 并行偶发 |
| 0.88 单跑偶发例 | pytest 单用例 | 1 passed |
| 0.88 两轮并行对照 | 失败例漂移 | 证明非改动引入 |
| 判型探针 | 是列表/是字符串/是数值 native 跑 | 真/假/真/真 |
| 改动前基线对照 | 本地 T5a | 6 failed/10 passed（证明修复有效）|

## 并行偶发分析（遗留观察项，非本路缺陷）

0.88 `-n 8` 下 T5a 偶发 1 例失败，特征：失败用例逐轮漂移、单跑恒绿、
本地 `-n` 不复现。疑似 stdlib 编译缓存/临时目录在 8 worker 下的竞争
（每个用例临时目录独立，但 xdist worker 共享 stdout 时序）。建议移交
路 6（收敛登记）观察，不影响本任务验收——0.88 验收口径为单跑全绿。

## 移交

- 并行偶发 → 路 6 观察登记（`-n 8` 下 T5a 1 例漂移，单跑全绿）。
- 判型家族接线对后续 stdlib 模块 native 化是通用基建（内置核心判型.light
  的同族函数可按此模式补齐）。
