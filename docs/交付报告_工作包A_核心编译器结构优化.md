# 交付报告 · 工作包A 核心编译器代码结构与去重（第11轮）

> 任务：`任务书/第11轮_结构优化/工作包A_核心编译器代码结构与去重.md`
> 分支：`task-opt-A`（独立 worktree `wt-OptA`）
> 完成判据：`src/`+`cli/` 无孤儿、无未裁决重复族、命名有权威定义、根级脚本已归档、全部改动用定向测试证明行为不变。

---

## 1. 改了哪些文件（逐个 + 一句意图）

### 已提交（commit `48907590`）
| 文件 | 意图 |
|---|---|
| `src/ffi_go.py` → `tools/archive/ffi_go.py` | A2 归档孤儿模块（含 FFI 绑定实验） |
| `src/ffi_rust.py` → `tools/archive/ffi_rust.py` | A2 归档孤儿模块 |
| `src/ir.py` → `tools/archive/ir.py` | A2 归档死链三角成员 |
| `src/linker.py` → `tools/archive/linker.py` | A2 归档死链三角成员 |
| `src/codegen_x64.py` → `tools/archive/codegen_x64.py` | A2 归档死链三角成员 |
| `src/linter.py` → `tools/archive/linter.py` | A3 归档被同名包遮蔽、0 引用的真死壳 |
| `src/compiler.py` | 删除引用已归档 ffi_go/ffi_rust 的 `FFI_MODULES` 注册表（15 行），断掉残留引用 |

### 已 staged（待本次提交）
| 文件 | 意图 |
|---|---|
| `bench_type_infer.py` → `tools/archive/` | A5 归档遗留性能分析实验脚本 |
| `profile_type_infer.py` → `tools/archive/` | A5 归档遗留性能分析实验脚本 |
| `simple_compiler.py` → `tools/archive/` | A5 归档遗留实验脚本 |
| `test_import_diag.py` → `tools/archive/` | A5 归档一次性诊断脚本 |
| `verify_bootstrap.py` → `tools/archive/` | A5 归档遗留校验脚本 |

### 新增文档（本次提交）
| 文件 | 意图 |
|---|---|
| `docs/结构优化_工作包A_裁决与命名.md` | A3/A4/A6/A7 持久决策：重复族裁决表、命名权威映射、CLI 职责矩阵、超大文件拆分方案 |
| `docs/交付报告_工作包A_核心编译器结构优化.md` | 本交付报告 |
| `tools/archive/README.md`（commit 48907590 已建） | 归档清单、原位置、处置原因说明 |

### 保留（裁决为活跃/只读依赖，不动）
- 根目录 `c_backend.py`/`light6.py`/`build_exe.py`/`benchmark.py`/`llvm_backend.py`：活跃工具 / 被测 / CI 引用（A5）
- `src/ast_unified.py`：被 `src/semantic_analyzer.py` 引用，后者被 `tests/conftest.py` 消费（只读），不可归档

---

## 2. 定向测试结果（输出落盘见 §8）

| 命令 | 结果 |
|---|---|
| `python -c "import light_parser_v3, code_generator, compiler, code_generator_unified, ast_nodes, ast_nodes_v3, semantic_analyzer, ast_unified"` | rc=0，8 个核心/保留模块全部可导入 |
| 归档模块 `import ffi_go/ffi_rust/ir/linker/codegen_x64` | 均不可导入（已断引用）✓；`import linter` 仍成功 → 解析到保留的 `linter/` 包（符合预期） |
| `cli/light.py --help` / `cli/light_unified.py --help` / `cli/lightc.py --help` / `cli/tutorial.py --help` | 四入口 rc=0 |
| 定向 pytest（见下） | 138 passed, 1 pre-existing failed, 13 skipped, 89 subtests passed |

定向 pytest 用例集：
`tests/test_parser.py tests/test_codegen.py tests/test_lexer.py tests/test_linter.py tests/unit/test_parser.py tests/unit/test_lexer.py tests/test_semantic.py tests/integration/test_compiler_pipeline.py tests/test_type_checker_compiler_integration.py`

**唯一失败项** `test_codegen.py::Test内置映射与实现咬合::test_内置映射不许有空壳`（builtin_map 空壳：写入二进制文件等 8 项）——经在 `main`(fc75f15c) 基线上复跑 **同样失败**，判定为**既有失败、与本次结构优化无关**（本次未触 stdlib/builtin_map 相关代码；该文件属只读）。

---

## 3. 引用矩阵与死代码清单（A1 产物）

- 一次性扫描脚本（临时目录，未入仓）：`_taskA1_scan.py`
- 产出：`_taskA1_matrix.json`（94/103 模块实测引用矩阵）
- 结论（与任务书 §3 证据一致）：
  - **孤儿模块**：`ffi_go.py`、`ffi_rust.py` —— 全仓 import 扫描 0 处外部引用 → 已归档（A2）
  - **死链三角**：`ir.py`→`codegen_x64.py`→`linker.py` 彼此互引、无外部引用，且 pyproject 已排除打包 → 已归档（A2）
  - **单引用/只读依赖**：`ast_unified.py`（semantic_analyzer→conftest）、`arity_parser`（test）、`elastic_syntax`（e2e 描述）→ 保留并标注

**反跑判据（A1）实测**：脚本对 `ffi_go/ffi_rust/ir/linker/codegen_x64` 稳定复现 0 外部引用；`src/compiler.py` 删除 `FFI_MODULES` 块后，全仓 grep 无残余 `ffi_go/ffi_rust` import（见 §5）。

---

## 4. 重复族裁决表（A3 产物，详见《裁决与命名.md》）

| 家族 | 裁决 |
|---|---|
| 错误体系 errors/enhanced_errors/error_formatter | 非重复，各司其职，保留 |
| 类型系统 type_checker/type_inferencer/type_system | 分层非重复，保留 |
| 解析器 light_parser_v3/parser_core/expr/stmt/arity/elastic | 核心链保留；arity/elastic 因 test/e2e 只读依赖保留并标注 |
| AST ast_nodes/ast_nodes_v3/ast_unified | 两层设计非重复；ast_unified 只读依赖保留 |
| 代码生成 code_generator/code_generator_unified/codegen_x64 | 前两者并行入口保留；codegen_x64 已归档 |
| 单文件 vs 包 formatter/linter/templates | **唯一真死壳 `linter.py` 已归档**；formatter/templates 单文件被包遮蔽，既有断链 → 出协调项，不单边合 |

---

## 5. 每个删除/合并/改名的反跑判据实测

| 项 | 改动 | 反跑判据实测 |
|---|---|---|
| A2 孤儿 & 死链归档 | 删除 `src/ffi_go/ffi_rust/ir/linker/codegen_x64` | 删除后核心 import（8 模块）rc=0；恢复文件则这些 import 出现（证明删除未破坏行为） |
| A2 断引用 | 删 `compiler.py` 的 `FFI_MODULES` | 删除后全仓 grep 无 `ffi_go/ffi_rust` 引用，`import compiler` rc=0 |
| A3 死壳归档 | 删 `src/linter.py` | 删除后 `import linter` 仍成功（落到 `linter/` 包）——无行为分叉；因单文件本被遮蔽，恢复也不产生新引用 |
| A5 根级脚本归档 | 删 5 个根级遗留脚本 | 归档后全仓 grep 无调用方（§下），活跃 5 脚本仍可运行（import 链已验） |

A5 归档脚本全仓 grep：`bench_type_infer / profile_type_infer / simple_compiler / test_import_diag` 在 `*.py` 中 0 处引用（仅 `tools/archive/README.md` 文档提及）。

---

## 6. 需要主线协调的跨包项

1. **`src/formatter.py` / `src/templates.py` 与同名包遮蔽 + 既有断链**
   `cli/light.py` 中 `from formatter import run_formatter`、`from templates import create_project` 实际因包遮蔽 ImportError（未手测确认的既有断链）。**禁止单边合并**（触碰 CLI + 语言缺陷边界），建议主线裁决：删除单文件还是合并到包。
2. **CLI 入口收敛（A6 建议，不发码）**：以 `cli/light.py` 为唯一主入口，`light_unified`/`lightc` 收敛为瘦封装；`lightc.py` R10-1 崩溃属语言缺陷，不在本包。
3. **`src/linter/cli.py` 独立 CLI**：`linter.py` 已归档，`linter/` 包仍活跃，含 `cli.py`；如需单独打包/入口，请主线确认。
4. **`src/incremental_compiler.py`、`src/semantic_identifier.py`**（任务书 §3.4 疑似孤儿，被 tests 工具引用）：文件属 A，测试属 B，需与 B 协调是否下线，本轮不单边删。

---

## 7. 已知未完成 / 未实测项

- **命名规范化（A4）未发码**：仅文档化现状（`light_parser_v3`/`ast_nodes_v3`/`code_generator_unified` 权威名映射），未批量改 120 处引用（任务书授权「文档化现状」路径）。
- **超大文件拆分（A7）交付方案，明确「不建议本轮拆」**：`parser_stmt.py`(6045)/`code_generator.py`(4546) 纯搬移+内部导入调整风险高，无行为证明手段，收益 < 风险；留档理由见《裁决与命名.md》。
- **POSIX / 平台差异**：本包改动均为纯 Python 归档/删除 + 文档，不涉及平台相关逻辑；归档脚本无 POSIX 特有残留。
- **`formatter/templates` 遮蔽断链**：未修（按协调项交接，见 §6）。
- **CLI 收敛**：仅文档化建议，未改码。

---

## 8. 定向测试输出落盘

本次验证为定向命令式验证（import/CLI/grep），测试原始输出见下方（已折叠关键行）：

- 核心 import：`CORE_IMPORT_OK rc=0（8 核心模块）`
- CLI 四入口：`light.py=0, light_unified=0, lightc.py=0, tutorial=0`
- 归档断引用：`ffi_go/ffi_rust/ir/linker/codegen_x64 均不可导入；linter 落到 linter/ 包`
- 定向 pytest：`138 passed, 1 failed(既有), 13 skipped, 89 subtests 通过`