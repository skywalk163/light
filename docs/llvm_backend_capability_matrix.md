# 原生（LLVM）后端能力矩阵

> 由 `scripts/gen_llvm_capability_matrix.py` 自动生成，**不要手改**——
> 改了 codegen / 适配层之后跑一次生成脚本，门禁 `tests/unit/test_llvm_capability_matrix.py`
> 会拿本矩阵与代码双向对咬（代码支持了矩阵没更新会红，矩阵说支持代码其实不支也会红）。

## 口径

一条语句要真被原生腿支持，得过三层，断在哪层就报哪层：

| 层 | 位置 | 断了会怎样 |
|----|------|-----------|
| L1 适配层转换器 | `compiler.AstAdapter._node_converters` | 被包成 `<unknown:XXX>` 伪装标识符，后端永远认不出 |
| L2 语句流白名单 | `compiler.AstAdapter._to_list_stmts` | 语句被包成 ExpressionStatement，分派链匹配不到 |
| L3 后端分派 | `codegen_typed._gen_statement` | 链尾兜底抛「暂不支持」 |

外加一列**实测**：真跑 `compile_source_typed`。三层都过但实测编不过 → `broken`；
三层看着缺却编过了 → `supported(?)`（说明扫描口径漏了，要人来看，不许装作没事）。

## 汇总

- 语句类型总数：**32**
- 已支持：**25**
- 缺口：**6**
- 三层齐备但实测编不过：`0`

## 矩阵

| v3 语句类 | 写法 | L1 转换器 | legacy 落点 | L2 白名单 | L3 分派 | 实测 | 状态 |
|---|---|---|---|---|---|---|---|
| `AssertStmt` | 断言 … | 有 | `AssertStmt` | 有 | 有 | ✅ 10173 字符 | `supported` |
| `Assignment` | X 为 值。 | 有 | `Assignment` | 有 | 有 | ✅ 9796 字符 | `supported` |
| `AsyncScope` | 异步 作用域 | 有 | `AsyncScope` | 有 | 有 | — 无自动用例 | `supported` |
| `BreakStmt` | 跳出 | 有 | `BreakStatement` | 有 | 有 | ✅ 10010 字符 | `supported` |
| `ClassDefinition` | 类 名： | 有 | `ClassDefinition` | 有 | **无** | ✅ 13051 字符 | `supported(upstream)` |
| `CompoundAssignment` | X 加 值。 | 有 | `CompoundAssignment` | 有 | 有 | ✅ 10160 字符 | `supported` |
| `ContinueStmt` | 继续 | 有 | `ContinueStatement` | 有 | 有 | ✅ 10048 字符 | `supported` |
| `DecoratorDefinition` | @装饰器 | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `DestructuringAssignment` | 设 [a, b] 为 X | 有 | `DestructuringAssignment` | 有 | 有 | ✅ 13220 字符 | `supported` |
| `ExportStmt` | 导出 … | 有 | `ExportStatement` | 有 | **无** | ✅ 9002 字符 | `supported(upstream)` |
| `FFIFunctionDecl` | 外部函数声明 | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `FFIVarArgsDecl` | 可变参数声明 | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `ForeachStmt` | 遍历 X 于 …： | 有 | `ForeachStatement` | 有 | 有 | ✅ 13038 字符 | `supported` |
| `IfStmt` | 如果 …： | 有 | `IfStatement` | 有 | 有 | ✅ 10793 字符 | `supported` |
| `ImportStmt` | 从 M 导入 … | 有 | `ImportStatement` | 有 | 有 | — 无自动用例 | `supported(upstream)` |
| `IndexedAssignment` | X[0] 为 值 | 有 | `Assignment` | 有 | 有 | — 无自动用例 | `supported` |
| `IndexedCompoundAssignment` | X[0] 加 值 | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `InterfaceDefinition` | 接口 名： | 有 | `InterfaceDefinition` | 有 | **无** | — 无自动用例 | `supported(upstream)` |
| `MatchStmt` | 匹配 …：情况 …： | 有 | `MatchStatement` | 有 | 有 | ✅ 12495 字符 | `supported` |
| `ParallelBlockStmt` | 并行 { … } | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `PassStmt` | pass（空语句） | 有 | `—` | **无** | **无** | — 无自动用例 | `n/a(no-op)` |
| `ReturnStmt` | 返回 … | 有 | `ReturnStatement` | 有 | 有 | ✅ 10077 字符 | `supported` |
| `RunAsyncStmt` | 异步 运行 主()。 | 有 | `RunAsyncStmt` | 有 | 有 | — 无自动用例 | `supported` |
| `ScopeDeclStmt` | 全局 X。/ 外层 X。 | 有 | `ScopeDeclaration` | 有 | 有 | ✅ 11041 字符 | `supported` |
| `SelfAssignment` | 己.X 为 值 | 有 | `Assignment` | 有 | 有 | — 无自动用例 | `supported` |
| `ThrowStmt` | 抛出 … | 有 | `ThrowStatement` | 有 | 有 | ✅ 9048 字符 | `supported` |
| `TryStmt` | 尝试 / 捕获 | 有 | `TryStatement` | 有 | 有 | ✅ 10067 字符 | `supported` |
| `TypeCheckToggleStmt` | 类型检查开关 | **无** | `—` | **无** | **无** | — 无自动用例 | `gap:adapter` |
| `VarDecl` | 设 X 为 值。 | 有 | `VariableDeclaration` | 有 | 有 | ✅ 9402 字符 | `supported` |
| `WhileStmt` | 当 …： | 有 | `WhileStatement` | 有 | 有 | ✅ 11339 字符 | `supported` |
| `WithStmt` | 使用 … 为 X： | 有 | `WithStatement` | 有 | 有 | ✅ 11766 字符 | `supported` |
| `YieldStmt` | 生成 … | 有 | `YieldStatement` | 有 | 有 | ✅ 14594 字符 | `supported` |

## 缺口清单（按层归类）

- **gap:adapter**（6）：`DecoratorDefinition`、`FFIFunctionDecl`、`FFIVarArgsDecl`、`IndexedCompoundAssignment`、`ParallelBlockStmt`、`TypeCheckToggleStmt`

## 与既有清单的分工

- `docs/原生腿能力清单.json`：只登记**已支持**的（内置函数 / 运行时符号 / 节点），单向清单。
- 本矩阵：**全部**语句类型 × 三层证据 × 实测，缺口要可点名、可归层。
