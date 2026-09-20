# R77 任务 A 完成报告 —— ANTLR 腿 FFI 跨腿缺口收口

> 完成时间：2026-09-20 ｜ 仓库：`light-merge` ｜ 分支 HEAD：`fa549235`
> 上游锚点：R76 合流（LM `fa549235`），0.82 全量门 7928 用例 / 失败 0

---

## 1. 目标与结论

| 项 | 目标 | 实测 |
|---|---|---|
| ANTLR 腿 examples 通过率 | 39/42 → **42/42** | ✅ **42/42**（`antlr_leg_smoke.py --strict` rc=0） |
| 三个 FFI 示例可解析 | 全绿 | ✅ 全绿，AST 字段完整 |
| 三个 FFI 示例可编译（`--backend antlr`） | 产出可运行 Python | ✅ 三份产物 `py_compile` 通过 |
| FFI 代码发射与 src 后端同口径 | 逐行对齐 | ✅ FFI 段落逐行一致 |
| 0.82 全量门新增红 = 0 | 新增红 0 | ⚠️ **未完成**（见 §6） |

**核心结论：解析腿 + codegen 腿双缺口已全部关闭，三个 FFI 示例在 ANTLR 腿下解析、编译均通过，ANTLR 腿 examples 通过率达到 42/42。**

---

## 2. 根因修正（重要）

计划书 §1.A 写的根因是「`src/code_generator_unified.py` 不发射 FFI 代码，FFI 全族 35 键未移植」。

**实测根因比计划书描述更靠前一层**：

1. **第一道阻塞在解析层，不在 codegen。**
   `antlrparser/LightLangLexer.g4` / `LightLangParser.g4` **完全没有 FFI 词族** —— `加载库`/`外部`/`结构体`/`回调`/`枚举`/`联合体`/`变长参数` 七个关键字全缺，首错落在 `examples/ffi_comprehensive.light` 第 4 行第 4 列。
   `antlrparser/light_ast.py` 同样**没有任何 FFI AST 节点**。

2. **codegen 缺口确实存在**，但它是第二道：即便解析通过，`code_generator_unified.py` 也不发射任何 ctypes 绑定（`import ctypes`、`_light_ffi` guarded import、`_ffi_type_map` 全缺）。

3. 因此 A 路实际是**解析腿 + codegen 腿双缺口**，改动面大于计划书预估。

---

## 3. 改动清单

### 3.1 词法/语法层（`antlrparser/`）

| 文件 | 改动 |
|---|---|
| `LightLangLexer.g4` | 新增 7 个词法规则：`K_LOAD_LIBRARY`(`加载库`)、`K_EXTERN`(`外部`)、`K_STRUCT`(`结构体`)、`K_CALLBACK`(`回调`)、`K_ENUM`(`枚举`)、`K_UNION`(`联合体`)、`K_VARARGS`(`变长参数`)。长词在前避免部分匹配 |
| `LightLangParser.g4` | `definition` 增加 6 个 FFI 分支；新增 13 条规则：`ffiLoadLibrary` / `ffiFunctionDecl` / `ffiParamList` / `ffiParam` / `ffiLibraryAlias` / `ffiStructDef`（结构体与联合体共用，靠 `K_UNION` 判别）/ `ffiFieldList` / `ffiField` / `ffiCallbackDef` / `ffiEnumDef` / `ffiEnumMemberList` / `ffiEnumMember` / `ffiVarArgsDecl` |
| `light_parser/*`（7 个产物） | 用 `scripts/generate_antlr_parser.py` 重新生成，rc=0（自动下载便携 JRE 17 + 复用缓存 antlr-4.13.2 jar） |

### 3.2 分词器（`antlrparser/light_tokenizer.py`）

| 改动 | 说明 |
|---|---|
| `KEYWORDS` 补 7 个 FFI 词 | `'变长参数', '加载库', '结构体', '联合体', '回调', '枚举', '外部'`，长词在前 |
| `KEYWORD_TOKEN_MAP` 补映射 | 7 词 → 对应 token 名 |
| `_scan_user_names` 增加 FFI 声明名扫描 | **允许关键字形名**（`外部 段落 幂 为 "pow"` 中 `幂` 是光明侧绑定名，C 侧真名在字符串里）。src 后端同样把 `幂` 判为 IDENTIFIER，此处对齐 |
| 新增 `_ffi_decl_name_at` | 支持 1 字关键字形声明名（`_longest_user_name_at` 有 ≥2 字约束，不适用） |
| 调用点识别 | 仅在 ① 紧跟 `外部`/`段落`（声明处）或 ② 后随 `(`（调用处 `幂(2.0, 10.0)`）时生效，避免过度放宽 |
| `_synthesize_statement_periods` 丢弃冗余句号 | v3 允许块末另起一行只写 `。`（3 个 FFI 示例均如此），上一行已被补过 PERIOD，再保留会得到连续两个 PERIOD → 「多余的 '。'」。仅当该句号是其所在行唯一 token 时丢弃 |
| `/` 由 `PATH_SEP` 改判 `DIVIDE` | 原映射使 `3.14159 / 180.0` 的除号变成路径分隔符。已核查全仓 `examples/`+`stdlib/` **无任何** import 路径用 `/`（全用空格或《》），改动无回归面 |

### 3.3 AST 层（`antlrparser/light_ast.py`）

- 新增 7 个 FFI 节点：`FFILoadLibrary` / `FFIFunctionDecl` / `FFIStructDef` / `FFIUnionDef` / `FFICallbackDef` / `FFIEnumDef` / `FFIVarArgsDecl`，**字段名与 `src/ast_nodes_v3.py` 同名节点逐字对齐**，使 unified codegen 基于类型名的分派可直接复用。
- `Module` 新增 `ffi_decls`（按源序收集 FFI 声明）。
- `Module` 补 `statements` 字段 —— **顺带修掉一个既有潜在缺陷**：`visitProgram` 一直会 `module.statements.append(...)`，但 dataclass 从未定义该字段；因 FFI 行此前提前报错、程序走不到那里而从未暴露。

### 3.4 访问器（`antlrparser/light_visitor.py`、`visitor_decl.py`）

- 导入 7 个 FFI 节点；`visitProgram` 增加 FFI 声明收集分支。
- `visitDefinition` 增加 6 个 FFI 分派。
- 新增 6 个 `visitFfi*` 方法 + 3 个辅助（`_unquote_string` / `_as_node_list` / `_ffi_visit_params` / `_ffi_visit_fields`）。
- `_as_node_list`：ANTLR 对「同类型 token 出现一次」返回单节点、多次返回 list，统一成 list 避免调用点区分两种形态。

### 3.5 代码生成（`src/code_generator_unified.py`）

| 改动 | 说明 |
|---|---|
| 头部补 `import ctypes` | 对齐 `code_generator.py:1160` |
| 补 `_light_ffi` guarded import | 对齐 `code_generator.py:1215-1225`：尽量导入，失败降级 `_LightFFIUnavailable` 占位，并置 `_light_ffi_available` 特征位 |
| `generate()` 初始化 `_ffi_user_types` | FFI 用户自定义类型注册表 |
| `generate()` 发射 `module.ffi_decls` | **在段落定义之前**发射 —— 段落体会调用这些外部函数包装器 |
| 新增 `_ffi_type_map` + `_get_ffi_type` | 与 `code_generator.py:5190` 同表 |
| 新增 7 个发射方法 | `_generate_ffi_decl`(分派) / `_generate_ffi_load_library` / `_generate_ffi_function_decl` / `_generate_ffi_struct_def`(结构体+联合体) / `_generate_ffi_enum_def` / `_generate_ffi_callback_def` / `_generate_ffi_varargs_decl` |

---

## 4. 验证证据

### 4.1 解析层冒烟（`scripts/antlr_leg_smoke.py`）

```
改前：ANTLR 腿解析冒烟：39/42 通过（37.4s）
      失败归类 其它: 3
      examples/ffi_comprehensive.light | FAIL | 第4行, 第4列: 语法错误…
      examples/ffi_math.light          | FAIL | 第4行, 第4列: 语法错误…
      examples/ffi_system.light        | FAIL | 第8行, 第4列: 语法错误…

改后：ANTLR 腿解析冒烟：42/42 通过（29.4s）   rc=0（--strict）
      矩阵已落盘：reports/antlr腿_冒烟_2026-09-20-180933.md
```

### 4.2 FFI 示例 AST 完整性

三个示例全部 `OK`，`ffi_decls` 字段完整：

```
examples/ffi_math.light -> OK
     ffi_decls: [FFILoadLibrary, FFIFunctionDecl × 5]
     segments : ['三角计算', '主程序']
        FFILoadLibrary  数学库  ← libm.so.6
        FFIFunctionDecl 正弦  [{'name':'甲','type':'小数'}] 返回 小数 在 数学库 C名 sin
        FFIFunctionDecl 余弦  … cos
        FFIFunctionDecl 平方根 … sqrt
        FFIFunctionDecl 绝对值 … fabs
        FFIFunctionDecl 幂    [{'name':'底','type':'小数'}, {'name':'指数','type':'小数'}] … pow

examples/ffi_system.light        -> OK  （系统库 ← libc.so.6；获取时间 ← time）
examples/ffi_comprehensive.light -> OK  （系统库 ← libc.so.6；获取时间 ← time）
```

### 4.3 编译产物（`cli/light_unified.py --backend antlr`）

三个示例均 `[成功] 已生成`，产物 `py_compile` 全部通过。产物 FFI 段落：

```python
数学库 = ctypes.CDLL('libm.so.6')
_正弦_ffi = 数学库.sin
_正弦_ffi.argtypes = [ctypes.c_double]
_正弦_ffi.restype = ctypes.c_double
def 正弦(甲):
    _result = _正弦_ffi(甲)
    return _result
...
_幂_ffi = 数学库.pow
_幂_ffi.argtypes = [ctypes.c_double, ctypes.c_double]
_幂_ffi.restype = ctypes.c_double
def 幂(底, 指数):
    _result = _幂_ffi(底, 指数)
    return _result
```

### 4.4 与 src 后端同口径核对

`--backend src` 编译同一文件，FFI 段落**逐行一致**（`数学库 = ctypes.CDLL('libm.so.6')` / `_正弦_ffi = 数学库.sin` / `argtypes` / `restype` / 包装函数签名全同）。

### 4.5 定向回归

```
pytest tests/test_ffi*.py（6 个文件）
  → 178 passed in 6.44s   rc=0
```

---

## 5. 已确认的既有失败（非本轮引入）

`tests/e2e/test_e2e_chain.py::test_duan_run[L3_domain/all_in_one_L3_demo.light]`

- 报错：`all_in_one_L3_demo.light` 行 47 列 12 —— 「遍历循环期望'在'、'之'、'于'、'中的'、'为'或'之为'，但得到「:」」。
- **已用 `git stash` 把我的全部改动（`antlrparser/` + `src/code_generator_unified.py`）暂存后复跑，失败现象完全一致** → 判定为**改动前既有失败**，与本轮无关。
- 该文件不属 FFI，失败点在遍历循环语法，与 A 路改动面无交集。

---

## 6. 未完成项与风险（须交接）

| 项 | 状态 |
|---|---|
| **0.82 全量门** | ❌ **未跑**。「新增红 = 0」判据**未验证**。这是 A 路验收的硬缺口 |
| `tests/` 全量回归（含 `tests/integration/`） | ⚠️ 后台跑到 33% 时被会话中断，**未见完整结果**；日志 `_tmp_r77a_logs/pytest_tests.log` |
| `tests/unit/` | ❌ 未跑 |
| CRLF 保持 | ⚠️ 未逐项核对。`.g4` / `.py` 改动经 `git stash pop` 提示过 whitespace 警告，**合流前须确认 `.light` 文件未被动**（本轮未改任何 `.light`） |
| 临时残留 | ⚠️ 未清理：`_tmp_r77a_probe.py`、`_tmp_r77a_logs/`、`_tmp_r77a_pytest/`、`reports/antlr腿_冒烟_*.md`（2 份）、`antlrparser/light_parser/__pycache__/` |

**风险提示**

1. `/` 由 `PATH_SEP` 改判 `DIVIDE`：已核查 `examples/`+`stdlib/` 无 import 路径用 `/`，但**未跑全量门**，若有测试断言 `/` 为 `PATH_SEP` 则会被打破（R75-A 事故同型风险，计划书 §1.C 特别点名的「改掉断言旧式源文本的测试」）。
2. `light_parser/` 7 个生成产物已变更，回退需连同 `.g4` 一并还原。
3. `Module.statements` 补齐属顺带修复，理论上会改变「顶层语句此前被静默丢弃」的行为 —— 需全量门确认无回归。

---

## 7. 建议的下一步

1. **跑 0.82 全量门**，按 `新增红 = 本轮失败 − 基线失败` 核验；若 `/` 改判或 `Module.statements` 引发红，按最小回退面处理。
2. 补跑 `tests/` 全量 + `tests/unit/`，确认 §5 之外无新增红。
3. 清理临时残留（`_tmp_r77a_*`、冒烟报告、`__pycache__`）。
4. 核对 CRLF：确认本轮未触碰任何 `.light` 文件。
5. 合流：`git add -u` + 显式文件（**绝不 `git add .`**），由主 agent 统一 commit/push。

---

## 附：本轮改动文件清单

```
antlrparser/LightLangLexer.g4              （词法：+7 FFI 关键字）
antlrparser/LightLangParser.g4             （语法：+6 分支 +13 规则）
antlrparser/light_parser/LightLangLexer.py         ┐
antlrparser/light_parser/LightLangLexer.interp     │
antlrparser/light_parser/LightLangLexer.tokens     │
antlrparser/light_parser/LightLangParser.py        │ 生成产物
antlrparser/light_parser/LightLangParser.interp    │ （脚本重建）
antlrparser/light_parser/LightLangParser.tokens    │
antlrparser/light_parser/LightLangParserVisitor.py ┘
antlrparser/light_tokenizer.py             （FFI 词表 + 声明名扫描 + 句号去重 + / 改判）
antlrparser/light_ast.py                   （+7 FFI 节点；Module +ffi_decls +statements）
antlrparser/light_visitor.py               （导入 FFI 节点）
antlrparser/visitor_decl.py                （visitProgram 收集 + visitDefinition 分派 + 6 个 visitFfi*）
src/code_generator_unified.py              （ctypes + _light_ffi import + 7 个发射方法）
```

**未改动**：任何 `.light` 文件、`src/` 下除 `code_generator_unified.py` 外的文件、B/C 路文件面。
