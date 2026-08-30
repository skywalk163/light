# 工作包 A：核心编译器 Python 源码层 —— 去重 / 死代码 / 命名 / 结构

> 分发给 **Agent A** 的独立任务书。本文件自包含，不依赖总纲以外的其他文件；与总纲冲突处以此文件为准。
> **声明**：使用性能优化流程——**无测量，不结论；无同合同证据，不授权。** 本包是「结构优化」类任务，
> 不改变任何公开语法 / 行为语义；所有删除、合并、改名都必须先有引用证据、再动手、再回归。

---

## 1. 目标

在不改变 Light 语言行为的前提下，把核心编译器 Python 源码层（`src/` + `cli/` + 根级编译器脚本）
从「10 轮迭代堆叠态」整理成「单一权威实现 + 无死代码 + 命名如实 + 结构清晰」的状态。

具体收益点（均有本轮已核实证据，见 §3）：消灭孤儿模块与死链路、裁决重复实现族、纠正误导性命名、
拆分超大文件（可选）、归档根级散落脚本、梳理 CLI 入口职责。

---

## 2. 文件所有权

- **写（唯一所有权）**：
  - `src/**`（含子包：core / formatter / linter / llvm / migration / optimizer / repl / templates）
  - `cli/**`
  - `antlrparser/**`（仅做「使用情况裁决」：仍被引用则保留并标注；确认废弃则连同引用一起处理，需先出方案）
  - 根级编译器脚本（甄别后归档 / 删除 / 保留）：`c_backend.py`、`llvm_backend.py`、`light6.py`、`simple_compiler.py`、`build_exe.py`、`verify_bootstrap.py`、`bench_type_infer.py`、`profile_type_infer.py`、`benchmark.py`、`test_import_diag.py`
- **只读（验证用，禁止改动）**：`tests/**`、`stdlib/**`、`bootstrap/**`、`pyproject.toml`
- **协调约束**：如需删除被 `tests/**` 引用的模块（如 `incremental_compiler`）、或需修改 `pyproject.toml`
  的打包排除项，只出「一行方案」写进交付说明，由主线统一协调，**禁止单边改他人文件**。

---

## 3. 现状证据（2026-08-28 已核实）

### 3.1 规模
- `src/` 共 105 个 `.py`，约 63,113 行。
- 超大文件（结构优化重点候选）：`parser_stmt.py` 6045 行、`code_generator.py` 4546 行、
  `llvm/codegen_typed.py` 3916 行、`parser_expr.py` 2889 行、`lexer.py` 2776 行、
  `type_inferencer.py` 2126 行、`package_installer.py` 1960 行、`code_generator_unified.py` 1649 行。
- `cli/` 6 个文件：`light.py`、`light_unified.py`、`lightc.py`、`tutorial.py`（+ `tutorial_30min.light`）。

### 3.2 孤儿模块（0 外部引用，仅自引用）
| 文件 | 行数 | 证据 |
|---|---|---|
| `src/ffi_go.py` | 1936 | 全仓 import 扫描：0 处外部引用（仅自身） |
| `src/ffi_rust.py` | ~460 | 全仓 import 扫描：0 处外部引用（仅自身） |

### 3.3 遗留死链路（彼此引用闭环 + 已被打包排除）
- `src/ir.py`（646）→ `src/codegen_x64.py`（542）→ `src/linker.py`（475）→ `src/ast_unified.py`（451）相互引用。
- `pyproject.toml` 的 `setuptools.packages.find.exclude` 已排除 `**/ir.py`、`**/codegen_x64.py`、`**/linker.py`。
- `ast_unified` 还被 `src/semantic_analyzer.py` 引用 → 需先裁决 `semantic_analyzer.py` 本身是否被核心链路消费，
  再决定整条链的处置（归档到 `tools/archive/` 或删除，**不直接 rm**，先确认无任何运行期引用）。

### 3.4 疑似孤儿（仅测试 / 工具引用，不属核心链路）
| 文件 | 引用方 |
|---|---|
| `src/incremental_compiler.py`（557） | 仅 `test_incremental_compiler.py`、`test_llvm_optimizer.py` |
| `src/semantic_identifier.py` | 仅 `coverage_report.py`、`test_advanced_semantic.py`、`verify.py` |

> 处置：这两类由 A 出「一行方案」，与 B 协调（测试文件属 B 所有权），不单边删。

### 3.5 命名误导（实际是权威实现，却顶着 v3/unified 后缀）
| 文件 | 引用数 | 结论 |
|---|---|---|
| `src/light_parser_v3.py` | 120 处 | 是主 parser，不是「v3 旧版」 |
| `src/ast_nodes_v3.py` | 15 处 | 是主 AST 节点定义 |
| `src/code_generator_unified.py` | 16 处 | 是主代码生成入口之一 |

> 处置方向（可选、需谨慎）：建立 `src/parser.py` / `src/ast_nodes.py`（或文档化别名）作为权威名，
> 旧名保留为 re-export 兼容层；或用 `docs/` 标注命名现状 + `__init__.py` 统一导出，避免大改 120 处引用。

### 3.6 重复实现族（需逐一裁决，不改行为）
- **错误体系**：`src/errors.py`（786）、`src/enhanced_errors.py`（仅 `cli/light.py` 引用）、`src/error_formatter.py`（535）
- **类型系统**：`src/type_checker.py`（1227）、`src/type_inferencer.py`（2126）、`src/type_system.py`（1418）
- **解析器**：`src/parser_core.py`、`src/parser_expr.py`、`src/parser_stmt.py`、`src/light_parser_v3.py`、`src/arity_parser.py`、`src/elastic_syntax.py`
- **AST**：`src/ast_nodes.py`（858）、`src/ast_nodes_v3.py`（1202）、`src/ast_unified.py`（451，死链）
- **代码生成**：`src/code_generator.py`（4546）、`src/code_generator_unified.py`（1649）、`src/codegen_x64.py`（死链）
- **单文件 vs 包并存**：`src/formatter.py` vs `src/formatter/`；`src/linter.py` vs `src/linter/`；`src/templates.py` vs `src/templates/`
- **REPL 归属**：`src/repl/`（6 文件）与 `tools/repl.py`、`tools/repl_v3.py`（tools 属 B，A 只负责 src/repl/ 内部）

### 3.7 根级散落编译器脚本
`c_backend.py`（29746）、`profile_type_infer.py`（30176）、`light6.py`（17248）、`bench_type_infer.py`（13406）、
`verify_bootstrap.py`（12074）、`benchmark.py`（10347）、`llvm_backend.py`（7769）、`build_exe.py`（6154）、
`simple_compiler.py`（4994）、`test_import_diag.py`（1894）。
> 需逐一甄别：是被 `src/` 或 `tools/` 运行期引用的真工具，还是历史遗留实验脚本。真工具迁入 `tools/` 并文档化；
> 遗留脚本统一归档 `tools/archive/`（保留历史）或按反跑判据删除。

### 3.8 CLI 入口职责
`cli/light.py`（含 `enhanced_errors` 引用）、`cli/light_unified.py`、`cli/lightc.py`、`cli/tutorial.py`。
已知第 10 轮 R10-1：`lightc.py` 对任何输入必崩（`SemanticAnalyzer()` 少传 `module` 参数），说明 CLI 入口缺乏真跑覆盖。
> 本轮 A 只梳理**职责与结构**（谁是主入口、各自命令行协议、帮助文案、参数一致性），不修语言缺陷（R10-1 的崩溃修复不在本包，除非顺带且带反跑）。

---

## 4. 任务清单（每项必须带反跑判据）

| # | 任务 | 反跑判据（改哪一行立红 → 复位绿） | 边界 |
|---|---|---|---|
| A1 | **建立引用矩阵与死代码清单**：写一次性扫描脚本（放临时目录，不写盘进仓库），对 `src/`+`cli/` 全部模块输出「谁 import 谁」，产出 105 个模块的引用矩阵 + 孤儿/死链/单引用清单，存档为基线 | 脚本对已知 3.2/3.3 的模块应复现 0 引用结论；改错模块名矩阵变化 | 只扫描不改码 |
| A2 | **处置孤儿模块**：`ffi_go.py`、`ffi_rust.py` 移入 `tools/archive/` 或删除；连同 `ir.py`/`linker.py`/`codegen_x64.py`/`ast_unified.py` 死链（先裁决 `semantic_analyzer`） | 删除后 `python -c "import light_parser_v3"` 及关键 CLI 路径仍可导入运行；恢复文件后立红消失 | 不碰被 tests 引用的模块 |
| A3 | **裁决重复实现族**：对 §3.6 各家族输出「权威实现 / 合并建议 / 保留理由」逐条裁决，能合并的合并（导出别名兼容），不能合并的文档化差异 | 合并后对应定向测试全绿；恢复旧实现（revert）应让测试仍在绿（证明合并未引入行为依赖）或立红（证明有依赖需保留） | 不改公开语法语义 |
| A4 | **命名规范化**：为 `light_parser_v3`/`ast_nodes_v3`/`code_generator_unified` 建立权威名 + re-export 兼容层（或文档化现状） | 新旧名均可导入且行为一致；去掉兼容层立红 | 不批量改 120 处引用 |
| A5 | **根级脚本甄别归档**：§3.7 逐一判定真工具/遗留，真工具迁 `tools/` 并补一行文档说明，遗留归档 | 每个被迁移脚本的调用方（若有）仍可运行；无调用方的归档后全仓 grep 无引用 | 不删除有运行期引用的 |
| A6 | **CLI 入口职责梳理**：输出 `cli/` 四入口职责矩阵 + 统一建议（主入口、协议、帮助文案、参数一致性），可落地的最小改动（如帮助文案统一）直接做 | 改后 `python cli/light.py --help` 等各入口 rc=0 且输出符合文档 | 语言缺陷修复不在本包 |
| A7 | **超大文件拆分（可选，先出方案）**：`parser_stmt.py`(6045)/`code_generator.py`(4546) 按语句族/职责拆分子模块，仅限纯搬移 + 内部导入调整 | 拆分后定向测试全绿；逐文件 revert 对照测试仍绿或立红定位 | 若方案风险高于收益，明确写「不建议本轮拆」，留档理由 |

---

## 5. 验证与交付

- **定向测试范围**（由你自定，覆盖改动面）：parser/codegen/lexer/type/compiler 相关 unit 测试、
  `tests/test_*.py` 中与 `src` 强相关的子集 + 你新增的真跑用例；**禁止跑全量**。
- **交付格式**：
  1. 改了哪些文件（逐个 + 一句意图）
  2. 定向测试结果（跑了哪些，输出落盘）
  3. 引用矩阵与死代码清单（A1 产物）
  4. 重复族裁决表（A3 产物）
  5. 每个删除/合并/改名的反跑判据实测（改哪一行立红 → 复位绿）
  6. 需要主线协调的跨包项（改 pyproject 排除项 / 删 tests 引用的模块）
  7. 已知未完成 / 未实测项
- **完成判据**：`src/`+`cli/` 无孤儿模块、无未裁决的重复族、命名有权威定义、根级脚本已归档，
  且全部改动用定向测试证明行为不变。
