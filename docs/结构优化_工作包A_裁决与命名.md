# 结构优化 · 工作包A 裁决与命名规范（第11轮）

> 原则：**无测量，不结论；无同合同证据，不授权。** 所有裁决基于 `_taskA1_matrix.json`（引用矩阵，94/103 模块实测）
> 与「被引用方不得删除」红线。本文件是持久决策，交付报告另附反跑判据实测与移交清单。

---

## A3 重复实现族裁决表

| 家族 | 成员（行数） | 实测被引用 | 裁决 | 理由 / 动作 |
|---|---|---|---|---|
| 错误体系 | `errors.py`(786)、`enhanced_errors.py`、`error_formatter.py`(535) | errors←{compiler,repl.core}；enhanced_errors←{cli.light}；error_formatter←**{tests/unit/test_error_formatter.py}** | **非重复，各司其职；保留** | errors 为核心管道；enhanced_errors 仅 CLI 增强显示；error_formatter 被单测引用 |
| 类型系统 | `type_checker.py`(1227)、`type_inferencer.py`(2126)、`type_system.py`(1418) | type_checker←{compiler,llvm.compiler}；type_inferencer←{code_generator_unified,compiler,llvm.compiler}；type_system 被前两者 import | **分层非重复；保留** | type_system 是共享基础类型，checker/inferencer 是两个消费端；合并破坏两套语义 |
| 解析器 | `light_parser_v3.py`、`parser_core.py`、`parser_expr.py`、`parser_stmt.py`、`arity_parser.py`、`elastic_syntax.py` | light_parser_v3←~20 模块（主 parser）；parser_core/expr/stmt 被其消费；arity_parser←{tests/test_advanced_semantic.py}；elastic_syntax←{e2e 测试描述} | **核心链保留；arity_parser/elastic_syntax 实验性，因 test/e2e 引用保留并标注** | arity_parser、elastic_syntax 无 src/cli 引用，但 tests/e2e 涉及，属只读依赖，不可归档 |
| AST | `ast_nodes.py`(858)、`ast_nodes_v3.py`(1202)、`ast_unified.py`(451) | ast_nodes←14 模块（codegen+optimizers+type_inferencer）；ast_nodes_v3←{parser 链+code_generator+compiler}；ast_unified←死链+semantic_analyzer | **两层设计非重复；ast_unified 因 tests/conftest→semantic_analyzer 保留** | ast_nodes_v3=解析产物层、ast_nodes=codegen/优化核心层，语义分层 |
| 代码生成 | `code_generator.py`(4546)、`code_generator_unified.py`(1649)、`codegen_x64.py`(死链) | code_generator←12 模块；code_generator_unified←{cli.light,cli.light_unified,repl.executor}；codegen_x64→已归档 | **前两者并行入口，保留并标注「unified≠旧」**；codegen_x64 已归档(A2) | 见 A4 命名权威映射 |
| 单文件 vs 包 | `formatter.py` vs `formatter/`；`linter.py` vs `linter/`；`templates.py` vs `templates/` | `import formatter/templates/linter` 均解析到**包**；单文件被同名包遮蔽、0 引用 | **单文件 `linter.py` 归档(A3)**；formatter/templates 单文件被包遮蔽；CLI 的 `run_formatter`/`create_project` 实际 ImportError（既有断链）→ **保留 + 出协调项，不单边合** | 包遮蔽+分歧实现=高风险，强制合并触碰 CLI/语言缺陷边界，交主线裁决 |

**结论（A3）**：本族多数为**分层/并行实现而非可删重复**；仅 `src/linter.py` 是真死壳（已归档）。formatter/templates 单文件 vs 包的存在性差异已文档化并列为协调项。

---

## A4 命名权威映射（文档化现状；不批量改 120 处引用）

| 现名 | 是否权威实现 | 权威名 | 处置 |
|---|---|---|---|
| `light_parser_v3.py` | **是**（主 parser，~120 引用） | `parser.py`（理想） | 现实：保留现名，文档标注为**权威主解析器**；`v3` 后缀是历史迭代层名，非「旧版」。不新增空壳 `parser.py` |
| `ast_nodes_v3.py` | 是（解析产物 AST 层） | `parser_ast.py`（理想） | 与 `ast_nodes.py`（核心 AST 层）分层明确；文档标注两层职责 |
| `code_generator_unified.py` | 是（并行代码生成入口） | — | `unified` 是**命名如实**（统一生成器），非误导；保留 |

> 建议：后续如需统一，在 `docs/项目结构说明.md` 增加「权威名」列；本轮为控制 120 处引用风险，**不批量改名**（符合任务书 A4「或文档化现状」授权）。

---

## A6 CLI 入口职责矩阵（实测 `--help` rc=0）

| 入口 | 职责 | 说明 |
|---|---|---|
| `cli/light.py` | **主入口 / 富 CLI**（21 子命令：run/harness/compile/ast/tokens/check/type-check/init/pkg/ai/test/fmt/doc/profile/install/publish/repl/tutorial/py2light/feedback） | 推荐入口 |
| `cli/light_unified.py` | 单文件编译前端（`--backend {antlr,src}`，`-o/--run/--ast`） | 与 `light.py compile` 职责重叠，建议归并 |
| `cli/lightc.py` | 精简编译入口（`-o/--run/--tokens/--ast`） | 与 `light_unified` 重叠；**R10-1：输入即崩**（`SemanticAnalyzer()` 缺 `module` 参数）→ 语言缺陷，非本包 |
| `cli/tutorial.py` | 教程驱动 | 独立 |

**统一建议**：以 `light.py` 为唯一主入口，`light_unified`/`lightc` 收敛为 `light.py` 子命令的瘦封装；帮助文案与参数风格统一。**本轮仅文档化，不改码**（改码属 CLI 重构，超出结构优化边界）。

---

## A7 超大文件拆分方案（可选）

| 文件 | 行数 | 建议 |
|---|---|---|
| `parser_stmt.py` | 6045 | **不建议本轮拆**：纯搬移+内部导入调整对 6k 行递归下降解析器风险高；无行为证明手段；收益 < 风险 |
| `code_generator.py` | 4546 | 同上 |

**留档理由**：两文件是声明式「归组分段」的解析/生成主体，段内强耦合；拆分需配套对应定向测试整组抽取与逐文件 revert 对照，届时可单独立包进行，不混入本轮结构优化（本轮核心是去重/孤儿/命名/归档，已完成）。