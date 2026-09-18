# R62 任务3：`段落 名 接收 参数` 语法废弃现代化（tests/ 阶段一）

- 轮次：R62 ｜ 日期：2026-09-19 ｜ 执行：主 agent
- 触发：`src/parser_stmt.py:3697-3704` 遇 `接收` 即发
  `DeprecationWarning: 语法「段落 名 接收 参数」已废弃，请改用「函数 名(参数)」或「段落 名(参数)」…`
  R61 全量输出 **53617 warnings**，其中 tests/ 源串 209 处 / 48 文件（任务书口径）为阶段一范围。

## 1. 等价性确认（第一步，必做——结论：只能替换 SAFE 形态）

依据 `light-merge/src/parser_stmt.py:3587-3864`。两条分支**共用同一段尾部**
（L3827-3864：返回类型 `返回 X` / `-> X` → 消耗 `。` → 冒号 → 体 → DEDENT/`结束`），
所以「返回类型」与「段落体」两分支完全一致；差异只在 **params 解析**：

| 能力 | 括号分支 L3641-3696 | 接收分支 L3697-3825 | 能否机械替换 |
| --- | --- | --- | --- |
| 纯参数 `a, b` | ✅ | ✅ | ✅ **SAFE** |
| 内嵌类型 `a: 整数` | ✅ | ✅ | ✅ **SAFE** |
| 空参数 `接收:` | ✅（遇 RPAREN 直接退出，params=[]） | ✅ | ✅ **SAFE** |
| 括号外类型 `(a):整数` | ✅（括号分支独有） | ❌ | — |
| `*args` / `**kwargs` | ❌（无 STAR 分支，遇 `*` 直接 `break` 后 `consume(RPAREN)` 出错） | ✅ | ⛔ **STAR** |
| 默认值 `a 等于 5` / `a = 5` | ❌（`等于` 不在 `_stmt_keywords_paren` 里，会被**当成参数名吞掉**） | ✅ | ⛔ **DEFAULT** |
| 空格式类型 `a 整数` | ❌（类型名被当成第二个参数） | ✅（需 `BUILTIN_TYPES` 判定） | ⛔ **SPTYPE** |
| FFI `a 为 整数` | ❌ | ✅ | ⛔ **SPTYPE** |
| 匿名闭包 `段落 接收 x:` | 另一条路（L-022 表达式形态，无段名） | — | ⛔ **ANON** |

**结论：`段落 X 接收 a, b:` → `段落 X(a, b):` 仅在 SAFE 形态下等价；
DEFAULT / STAR / SPTYPE / ANON 一律不机械替换。**

另：**FFI 声明**（`外部 函数/段落/回调 … 接收 … 返回 T 在 库。`）走的是
`parser_stmt.py:5989+ _parse_external → _parse_ffi_function_decl/_parse_ffi_callback_def`
**另一条解析链**，既不发本轮要清的警告，也不支持括号式参数 → **整类不动**。

## 2. 改动规模（实测）

| 项 | 数量 |
| --- | --- |
| 改动行 | **287** |
| 涉及文件 | **46** |
| 形态：`段落/函数/段 名 接收 …` → `名(…)` | 249 |
| 形态：裸段名（类构造器 `构造` / `构`）`构造 接收 …` → `构造(…)` | 38 |

git 自证：`git diff --numstat tests/` → **46 files changed, 287 insertions(+), 287 deletions(-)**
（严格 1:1 行替换，无整文件改写）。

## 3. ⛔ 禁改项核对

| 禁改项 | 处理方式 | 核对结果 |
| --- | --- | --- |
| 匿名闭包 `段落 接收 参数:`（无段名，L-022） | `ANON_RE` 单独识别并跳过 | 2 处保留（`tests/unit/test_L041_L053_L059_L060_L063.py:222,224`）✅ |
| 断言/期望输出文本里的旧式串 | 命中前导含 `assert` / `in '"` / `#` / `期望` → 跳过 | `test_agent_tools_light.py:123`、`test_codegen_safename_multimodule_O0.py:181,182,197` 等保留 ✅ |
| Python 注释/文档里的旧式示例 | 同上 | 保留 ✅ |
| FFI 声明（`外部` / `@C` / `变长参数` / `函数指针` / `结构体` …） | `FFI_RE` 整行跳过 | 54 行保留 ✅ |
| 迁移测试本体（`tests/test_migration.py` 测的就是旧式→新式转换） | 源串必须保持旧式 | `test_migration.py:97,98` 保留 ✅ |

## 4. 保留清单（15 处，非 FFI 非断言，逐条原因）

| 位置 | 形态 | 保留原因 |
| --- | --- | --- |
| `tests/test_frontend_blockers_run.py:286,304` | `端口 等于 443` / `次数：整数 等于 3` | DEFAULT（括号分支会把 `等于` 当参数名） |
| `tests/unit/test_codegen_method_syntax_O0.py:85` | `甲 = -1` | DEFAULT |
| `tests/unit/test_codegen_ref_dict_O0.py:109` | `*列表们` | STAR |
| `tests/unit/test_c_backend.py:391,506,509,528` | `n 整数` / `a 整数, b 整数` | SPTYPE（空格式类型） |
| `tests/test_parser.py:166` | `接收 甲 乙：` | SPTYPE（多 token 段名/参数有歧义） |
| `tests/e2e/test_parser_fuzz.py:214` | `'段落 函数 接收'` | fuzz 输入，无参数无冒号，语义待定 |
| `tests/test_generics_c3.py:4`、`tests/test_modern_features.py:7` | 文档注释 | 注释 |
| `tests/test_migration.py:97,98` | 迁移测试本体 | 禁改 |

## 5. 逐文件验证

- **本机定向**（改动涉及的 46 个文件全跑）：
  `1320 passed, 9 skipped, 2 xfailed` —— 1 例
  `tests/unit/test_原生腿_R13C_对拍扩展.py::test_空串边界族` 报
  `NativeImportError: 模块 '正则表达式' 是 decl 0 空壳（实现在同名 .py）`，
  **单独复跑为绿**（`1 passed`），且同一文件在不同批次的失败用例各不相同
  （本次 `test_空串边界族`，上一批 `test_字符串相似度`/`test_去除所有空白与组合`）→
  判定为 **xdist 并行 + LLVM 模块缓存争用导致的抖动**，与本次改动无关
  （改动只把 `段落 b1 接收 b:` 换成 `段落 b1(b):`）。
- **回滚对照**：`git stash` 后跑同两文件 → `40 passed, 1 skipped, 2 xfailed`（0 红），
  与改动后一致，确认无回归。
- **0.82 全量**：见任务4 收口报告。

### 工程护栏（两道，都触发过）

1. **Python 语法自证**：改写后整文件 `compile()` 不过就整文件放弃。
   首轮正是靠它抓到 bug——参数名字字符集没排除 `'`/`"`，
   `tests/test_migration.py:98` 被写成 `source = "段 添加(a, b")` （结尾引号被参数名吞掉）。
   已修：字符集排除 `' " \`。
2. **CRLF 保持**：读文件用 `io.open(newline="")`，否则 `read_text()` 把 CRLF 统一成 LF，
   写回后整文件变 LF → 巨大假 diff。

### 另一个漏网修复

`.light` 源串里的 `\n` 换行转义使 `段落` 前一字符是 `n`，
lookbehind 无法表达「前两字符是 `\n`」→ 首轮漏改
`tests/unit/test_light_examples_run.py:392`。改为**捕获组**前导边界（允许 `\n`/`\t`/`\r` 转义对）后补改。

## 6. stdlib/ 规模登记（本轮不动，登记为 R63 主线）

| 目录 | `接收` 出现行数 | 其中「段落/函数/段 名 接收」形态 |
| --- | --- | --- |
| `stdlib/*.light` | **1668** | **1651** |
| `examples/` | 398 | — |
| `stdlib_v3/` | 27 | — |
| `benchmarks/` | 14 | — |

即：tests/ 阶段一清掉的 287 处只占 `stdlib` 单仓的 **17%**；
R61 全量 53617 warnings 的大头来自 stdlib（每份 stdlib 被每个测试重复编译）。

⚠️ **下轮风险提示（R63 注意）**：
1. stdlib 改 `接收` → 括号式会**切换编译路径**（memory 已记：给 .light 补 import 会切换路径，
   语法改写同理），必须对该依赖链上所有测试定向回归；
2. 必须遵守**魔数护栏**：改任一 `stdlib/*.light`，首两行之外不得出现「纯光明实现」字样；
3. stdlib 里存在 `外部 … 接收`（FFI 链）与 DEFAULT/STAR/SPTYPE 形态，同样不可机械替换；
4. 建议按「模块 × 依赖闭包」分批推进，每批单独跑定向 + 一次全量兜底。

## 7. 交付物与改动清单

| 文件 | 改动 |
| --- | --- |
| `light-merge/tests/**`（46 个文件，287 行） | 旧式 `接收` → 括号式参数（仅 SAFE 形态） |
| `light-merge/_probe_R62_接收扫描.py` | 新增：形态扫描与分类探针 |
| `light-merge/_任务3_R62_应用.py` | 新增：批量现代化器（含语法自证 + CRLF 保持 + 禁改项判定） |
| `light-merge/_task3_R62_接收语法现代化.md` | 本报告 |
