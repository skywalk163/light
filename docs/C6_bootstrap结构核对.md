# C6｜bootstrap 自举编译器结构核对

> 工作包 C §4-C6。仅做**结构核对**（清单 + 对应关系 + 冗余标记），**不实现语言功能**、不改动 `src/`。
> bootstrap/ 共 184 个文件。

## 1. 文件分组清单

| 分组 | 文件 | 性质 |
|---|---|---|
| 自举编译器源（.light） | `lexer.light` `parser.light` `codegen.light` `token.light` `light_ast.light` `compiler.light` `main.light` `bootstrap_level3/4/5/6.light` `bootstrap_v3.light` | 自举实现的各阶段编译器 |
| 编译器驱动 | `module_preprocessor.py` `run_compiler.py` `lexer_handwritten.py` `compile_lexer.py` | 引导/辅助 |
| 生成中间物（*_generated.py） | `level4_generated.py` `level5_generated.py` `level6_generated.py` `level7_generated.py` `level6_out1.py` `level6_out2.py` `level6_test_output.py` | 由 bootstrap 跑出的代码生成产物（**冗余候选**） |
| 多版生成器（*_gen*.py） | `bootstrap_v3_gen.py` `bootstrap_v3_gen2.py` `bootstrap_v3_gen3.py` | 历史/备选生成器（**冗余候选**） |
| 备份/合并物 | `bootstrap_level5_backup.light` `bootstrap_merged.light` | 备份/合并中间态（**冗余候选**） |
| 迁移/转换 | `bootstrap_migrator.py` `convert_to_level6.py` `merge_bootstrap.py` | 版本迁移工具 |
| 校验/发布 | `bootstrap_cycle_verify.py` `verify_bootstrap_cycle.py` `build_bootstrap_release.py` `bootstrap_progress.py` `bootstrap_test_enhancer.py` `add_end_markers.py` | 自举闭环校验/发布 |
| 测试 | `test_bootstrap_*.py` `test_compiler*.py` `test_level*.py` `test_parser_debug.py` `test_new_features.py` `test_token.py` `test_if_chain.light` `test_nested_if.light` `test_simple.light` | 自举层测试 |
| 文档/空目录 | `_缺失功能分析.md` `release/` `test_modules/` | 说明与占位 |

## 2. 与 `src/` 手写编译器的阶段对应（结构级，非 1:1 验证）

| bootstrap 自举模块 | 对应 `src/` 手写模块 |
|---|---|
| `lexer.light` | `src/lexer.py` |
| `parser.light` | `src/parser_core.py` `parser_expr.py` `parser_stmt.py` |
| `codegen.light` | `src/codegen_x64.py` |
| `token.light` | `src/tokens.py` |
| `light_ast.light` | `src/ast_nodes.py` `ast_nodes_v3.py` `ast_unified.py` |
| `compiler.light` | `src/compiler.py` `incremental_compiler.py` |
| `module_preprocessor.py` | `src/`（模块预处理） |
| `run_compiler.py` | `src/compiler.py`（驱动入口） |

> 注意：bootstrap 侧未见与 `src/semantic_analyzer.py` / `semantic_identifier.py` 显式对应的自举文件，语义分析阶段可能仍以手写编译器为主——此判读需语言泳道确认。

## 3. 冗余/重复标记（仅列出，不处理）

- `level4/5/6/7_generated.py`、`level6_out1/out2/test_output.py`：生成中间物，疑似可经重建脚本再生，属结构债务。
- `bootstrap_v3_gen2.py` / `bootstrap_v3_gen3.py`：多版生成器，与 `bootstrap_v3_gen.py` 并存。
- `bootstrap_level5_backup.light` / `bootstrap_merged.light`：备份/合并态。

上述文件是否可清理/合并，**需语言泳道（bootstrap 所有权）评估**，C 只出清单不擅自删。

## 4. R10-6 功能差距（仅盘点，不实现）

> R10-6 要求盘点"哪些语法仍是手动编译器独占"。C 的边界是结构核对，功能差距判定归语言泳道。

- **结构级观察**：bootstrap/ 内含多套 `*_generated.py` 与 `*_gen2/gen3.py` 及 `*_backup.light`，说明自举编译器**尚未收敛为单一干净产物**，存在生成物/多版生成器堆叠——这是 R10-6 差距的**结构表征**，但具体"哪些语法特性尚不能由 bootstrap 自举表达"需语言组逐项核对 `src/` 独占实现。
- **交付物边界**：本报告仅呈现上述清单与对应表；功能差距的逐特性裁决不在 C 范围内。

## 5. 反跑判据

- 核对清单逐条可落文件路径（上表均经 `ls` 实测存在）。
- 未改动任何 `src/` 文件，未实现语言功能；bootstrap/ 文件仅被**列清单**，未被移动或删除。
