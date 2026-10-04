# R114 · 原生（LLVM）后端能力缺口收口报告

> 仓库：light-merge ｜ 日期：2026-10-04
> 红线单：**#LM-RED-ScopeDeclStmt**（原生后端不支持 `全局` / ScopeDeclStmt）
> 结论：**销账**。附带发现并修掉第二层缺口 S2（全局**容器**原地修改失效）。

---

## 一、定性

不是逻辑回归，是原生后端长期存在的能力盲区，被更早的 `UnboundLocalError` 掩盖：

- 失败**仅因 `全局` 这一行**——去掉即通过（Python/转译后端、import 路径、自举率全正常）。
- 根因不在「`_gen_statement` 少一个分支」，而在**三层链条**各断一处：

| 层 | 位置 | 断的表现 |
|----|------|---------|
| L1 适配层转换器 | `compiler.AstAdapter._node_converters` | 无 `ScopeDeclStmt` 转换器 → 降级成 `<unknown:ScopeDeclStmt>` 伪装标识符 |
| L2 语句流白名单 | `compiler.AstAdapter._to_list_stmts` | legacy 节点没进白名单 → 语句被包成 `ExpressionStatement`，分派永远匹配不到 |
| L3 后端分派 | `codegen_typed._gen_statement` | 无分支 → 链尾兜底抛「暂不支持语句类型 ScopeDeclStmt」 |

只补 L3 不够：L2 这层 R10-11b 的 `生成` 已经踩过一次（同一个白名单），本次是第二次。

---

## 二、语义对齐（先定死再写码）

| 后端 | `全局 X` 的落地 | 依据 |
|------|----------------|------|
| 转译（Python） | `global X`：段落内读写模块级变量 | `code_generator.py:2025` |
| 原生（LLVM） | 把 X 挂进 `_globals` → 读写改走模块级槽 `@__var_X` | `get_var` / `set_var` **本来就是 globals 优先** |

**一个必须知道的差异（实测，别误判）**：模块级**已经**声明过的变量，原生腿即使不写 `全局`
也照样写回全局槽（LLVM 语义：模块级变量是编译期分配的内存），而 Python 会当成局部。
`全局` 真正不可替代的场景是**模块级没有同名声明**时——它把名字抬成模块级槽，使跨段落可见
（对应 Python 里 `global X` + `X = 1` 在模块级创建 X）。专项测试专门盯这一条，不盯
「写了跟没写一样」的那条。

拒绝口径（与转译腿一致，不静默降级）：模块级写 `全局` → 「只能写在段落体内」；
`外层`（nonlocal）→ 因嵌套段落本就不支持，如实报真正拦下它的那一层。

---

## 三、第二层缺口 S2：全局容器的原地修改不生效

销账过程中实测撞出，此前被 ScopeDeclStmt 挡着、从未暴露：

```
设 表 为 新建字典()
段落 填(): 全局 表。  字典设置(表, "你", "ni")
→ 打印 字典获取(表, "你", "MISS")   # 期望 ni，实际 MISS
```

- 局部表：`字典设置` **生效**（`get_var` 登记了 `_dv_ssa_to_slot`，`_store_dv` 复用真槽）。
- 全局表：**不生效**——`get_var` 的 globals 分支 `load` 出一个 SSA 副本，没登记槽位，
  `_store_dv` 于是另开临时槽，`dv_dict_set` 改的是副本，写不回全局。

**修法**：`get_var` 全局分支把 `@__var_X` 本身登记为该 SSA 的槽位。
一处改动覆盖全部原地修改类 builtin（`字典设置` / `列表追加` / `列表设置` / `删除` …），
不是只给 `字典设置` 打补丁。

---

## 四、改动清单

| 文件 | 改动 |
|------|------|
| `src/ast_nodes.py` | 新增 `ScopeDeclaration(names, kind)` 节点（`AST_TYPE_ID_SCOPE_DECLARATION = 105`） |
| `src/compiler.py` | AstAdapter 注册 `ScopeDeclStmt` 转换器（透传 `lineno`）；`_to_list_stmts` 白名单加 `ast.ScopeDeclaration` |
| `src/llvm/codegen_typed.py` | `_gen_statement` 加分支 + 新增 `_gen_typed_scope_decl`；**S2**：`get_var` 全局分支登记 `_dv_ssa_to_slot` |
| `scripts/gen_llvm_capability_matrix.py` | **新增**：能力矩阵生成器（三层扫描 + 实测，产出 md/json） |
| `docs/llvm_backend_capability_matrix.{md,json}` | **新增**：32 条语句 × 三层证据 × 实测，20 支持 / 11 缺口 |
| `tests/unit/test_llvm_scope_decl.py` | **新增**：IR 级 4 条 + 拒绝 2 条 + 静态白名单护栏 + clang 真跑对拍 |
| `tests/unit/test_llvm_capability_matrix.py` | **新增**：矩阵门禁（不许退 / 不许吹牛 / 不许漏登记） |
| `tests/unit/test_llvm_stmt_coverage.py` | `全局` 从拒绝用例移入支持用例（正跑 4 + 反跑 7） |
| `tests/unit/test_原生腿_R11B_中文工具.py` | 移除两处 `xfail`（实测 xpass，说明修复生效） |
| `tests/unit/test_native_leg_capability.py` | 硬编码清单加 `ScopeDeclaration`（双向咬合要求） |
| `docs/原生腿能力边界.md` §1.1 | 登记 `ScopeDeclaration` |
| `docs/known_issues.md` §9 | 清单与实测分桶同步（未支持 9→8、能编 17→18、拒绝 5→4），新增 §9.3.1 语义说明 |
| `docs/原生腿能力清单.json` | 重生成（statement_nodes 17→18） |

**未动**（守红线）：`stdlib/拼音转换.light`、`stdlib/中文分词.light` 的**首行魔数**没补，
两模块维持休眠态——实测休眠态不影响原生腿（R11B 直接 xpass），翻魔数属独立决策。

---

## 五、验证证据

| 判据 | 结果 |
|------|------|
| 最小用例 IR（4 组） | 编得过，IR 含 `@__var_* = global`，无 `<unknown` 残留 |
| clang 真跑语义对拍 | `全局` 抬出的槽跨段落可见 → `2`；对照组（模块级已声明、不写 `全局`）同为 `2`，反证 LLVM 语义差异 |
| **真实 stdlib 模块** | `中文分词.light`（4 处 `全局`）原生腿 O0 编译 + 运行，与 `.py` 黄金实现 **ALL PASS**（含 `添加自定义词` 后跨段落生效） |
| R11B 全量 7 用例 | **7 passed**（含原 xfail 的 中文分词 / 拼音转换） |
| S2 诊断 4 组 | 局部/全局、跨段落/同段落，四种组合全 `ni` |
| 门禁反向验证 | 临时摘掉 `_gen_statement` 的 ScopeDeclaration 分支 → 能力矩阵门禁**立刻红**，并指名「L3分派=无」 |
| 定向回归 | 121 passed（scope_decl / stmt_coverage / capability_matrix / native_leg_capability / ci_gates ×2） |
| 本机全量 | **8425 passed** / 83 skipped / 12 xfailed / 2 xpassed，4 条红**逐条定性**（下表） |
| **0.82 权威门禁** | **门 PASS ✅**：8131 passed / 81 skipped / 11 xfailed，**失败 0**，对比基线 **新增红 0**（`082全量回归.py all`，基线 `082_lightmerge基线_2026-10-05-010749.json`） |

### 全量 4 红的定性（不许糊过去）

| 用例 | 判定 | 处置 |
|------|------|------|
| `test_llvm_c3_expr.py::…[全局声明]` | **本次相关** | 模块级 `全局` 的拒绝文案里没有 `ScopeDeclStmt` 类型名，违反 C3-4「自报家门」口径 → **改源码文案**（补类型名），已绿 |
| `test_llvm_optimizer.py::test_池大小等于真实用量而不是2048` | **本次相关（且是改善）** | `__light_init` 临时槽池 9→**7**：全局槽被复用后不再各开临时槽（省 96B/帧）。这是 S2 修法的必然结果 → 更新钉死期望值并注明「改回 9 前先确认全局槽登记没被删」，已绿 |
| `test_http_client.py::test_connection_error` | **既有环境红，与本次无关** | `git stash` 到改动前基线复跑**同样红**（连 `127.0.0.1:1` 超时，本机/沙箱网络限制） |
| `test_T6B_…::test_时间管理_睡眠计时冒烟` | **flaky** | 隔离复跑（改动后）**绿**；全量 `-n 4` 并发下时序抖动 |

---

## 六、能力矩阵（L1）与门禁（L3）

`scripts/gen_llvm_capability_matrix.py` 自动扫三处代码 + 真跑 `compile_source_typed`，
产出 `docs/llvm_backend_capability_matrix.{md,json}`。**断在哪层就报哪层**，不再整片写成
一句「覆盖有限」。

当前：语句类型 **32**｜已支持 **20**｜缺口 **11**｜三层齐备但实测编不过 **0**。

缺口分桶：
- `gap:adapter`（8）：`AssertStmt`、`RunAsyncStmt`、`TypeCheckToggleStmt`、
  `ParallelBlockStmt`、`DecoratorDefinition`、`IndexedCompoundAssignment`、
  `FFIFunctionDecl`、`FFIVarArgsDecl`
- `gap:codegen`（3）：`MatchStmt`、`WithStmt`、`DestructuringAssignment`

门禁 `tests/unit/test_llvm_capability_matrix.py` 三条：
1. **不许退**：矩阵记 `supported` 的，重新扫代码必须仍是 supported（回退即红，已反向验证）；
2. **不许吹牛**：矩阵说支持且当时实测 ok 的，现在真编一次必须还 ok；
3. **不许漏登记**：代码里新出现的 v3 语句类必须进矩阵。

改了 codegen / 适配层之后跑一次 `python scripts/gen_llvm_capability_matrix.py` 即可。

---

## 七、后续（按优先级）

1. **解除两模块休眠**（补首行魔数）——本次守红线未动。翻魔数会让 Python 后端、
   自举率、R11B 三处同时切到真身，应作为独立决策单独跑一次门禁。
2. **按矩阵补缺口**——`AssertStmt`（断言，最常用）、`WithStmt`、`DestructuringAssignment`
   是三条性价比最高的（三层里只差 codegen 一层）。
3. **长期指标**：把「stdlib 模块的 LLVM 就绪度」（多少模块能被原生腿直接编译）像自举率
   一样量化追踪。
