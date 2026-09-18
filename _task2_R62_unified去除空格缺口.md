# R62 任务2：`code_generator_unified.py`（ANTLR/unified 后端）`去除空格` 缺口

- 轮次：R62 ｜ 日期：2026-09-19 ｜ 执行：主 agent
- 背景：R61 任务3 只在 **hook 腿** `src/code_generator.py:625` 补了 `'去除空格': '_light_builtin.去除空白'`，
  **unified（ANTLR）腿** `src/code_generator_unified.py` 同款缺口未修。

## 1. 差集对齐（两份 builtin_map 全量对比）

探针：`light-merge/_probe_R62_builtin_diff.py`（AST 解析两份源文件的
`self.builtin_map = {...}` 顶层 dict 字面量，避免实例化依赖）。

| 指标 | 改前 | 改后 |
| --- | --- | --- |
| hook 腿（`src/code_generator.py`）键数 | 276 | 276 |
| unified 腿（`src/code_generator_unified.py`）键数 | 124 | **149** |
| hook 有 / unified 缺（缺口） | **174** | **149** |
| unified 有 / hook 缺（unified 独有） | 22 | 22 |
| 同键不同值（行为差异） | 7 | 7 |

### 核心缺口确认

```
去除空格     hook=有(_light_builtin.去除空白)   unified=无   ← 本轮要修的
```

改前实测（`light-merge/_probe_R62_unified_builtin.py`，手工构造 light_ast 直接驱动
UnifiedCodeGenerator，绕开 ANTLR 依赖）：

```
去除空格     map=无
  产物: ["    去除空格(' x ')"]                ← 裸名 → 运行期 NameError
去除空白     map=有 -> _light_builtin.去除空白
  产物: ["    _light_builtin.去除空白(' x ')"]  ← 正确
```

### 中招面（stdlib 里 4 个 .light 的裸调用 `去除空格`）

- `stdlib/中文数字转换.light:54, 167`
- `stdlib/参数解析.light:35, 37`
- `stdlib/格式化.light:207`
- `stdlib/颜色.light:198, 225, 228`

## 2. 补映射（`src/code_generator_unified.py` L167 起，新增 25 键）

补的是**「字符串处理同族」**：与 `去除空格` 同族、且 `stdlib/builtins.py` 确有实现
（已逐名 `hasattr` 核查，全部 OK）的缺失键。

```python
'去除空格': '_light_builtin.去除空白',          # ★R61 4 模块的直接缺口
'字符串包含': '_light_builtin.字符串包含',
'字符串替换': '_light_builtin.替换字符串',
'字符串分割': '_light_builtin.分割字符串',
'转大写': '_light_builtin.转大写',
'转小写': '_light_builtin.转小写',
'转标题': '_light_builtin.转标题',
'子串': '_light_builtin.截取',
'字符串截取': '_light_builtin.截取',
'开头': '_light_builtin.开头',
'结尾': '_light_builtin.结尾',
'查找子串': '_light_builtin.查找子串',
'最后索引': '_light_builtin.最后索引',
'替换字符串次数': '_light_builtin.替换字符串次数',
'截取到末尾': '_light_builtin.截取到末尾',
'字符串计数': '_light_builtin.字符串计数',
'字符串重复': '_light_builtin.字符串重复',
'字符串反转': '_light_builtin.字符串反转',
'去除左侧空白': '_light_builtin.去除左侧空白',
'去除右侧空白': '_light_builtin.去除右侧空白',
'字符串对齐居中': '_light_builtin.字符串对齐居中',
'字符串对齐左': '_light_builtin.字符串对齐左',
'字符串对齐右': '_light_builtin.字符串对齐右',
'浅拷贝': '_light_builtin.浅拷贝',
'深拷贝': '_light_builtin.深拷贝',
```

### 刻意不补（已登记，不擅自改语义）

- **`包含`**：hook 腿映射到 `_light_builtin.字符串包含`，但「包含」作为用户段落名/变量名
  的概率高；本轮保守起见不在 unified 腿引入。
- **剩余 149 键缺口**（数学族 `平方根/对数/正弦…`、FFI 全族 `_light_ffi.*`、
  文件/进程族、类型转换别名 `串/整/转串…` 等）属**独立大改**，登记为 **R63 主线**，本轮不动。

### 遮蔽安全性

unified 主调用路径 `src/code_generator_unified.py:1968` 已实现「用户定义的函数优先」：

```python
if func_name not in self.user_functions and func_name in self.builtin_map:
    func_name = self.builtin_map[func_name]
```

即新增键**不会覆盖用户自定义同名段落**，只影响原本会落到裸名（运行期 NameError）的调用。

## 3. 验证

### 3.1 映射级（本机，改后）

```
builtin_map 键数 = 149
  去除空格     map=有  -> _light_builtin.去除空白      [已映射，无裸名]
核心判据：去除空格 -> _light_builtin.去除空白   PASS
```

### 3.2 测试级（本机定向）

| 命令 | 结果 |
| --- | --- |
| `pytest tests/integration/test_missing_stdlib.py tests/integration/test_compiler_pipeline.py` | **10 passed, 2 skipped**（rc=0） |
| `pytest tests/e2e/test_e2e_chain.py` | 本机跑（见下注） |

### 3.3 ⚠️ 环境事实：ANTLR 生成产物缺失（本机与 0.82 同）

`cli/light_unified.py compile --backend antlr` **跑不起来**，报
`ModuleNotFoundError: No module named 'LightLangLexer'`
（`antlrparser/light_visitor.py:22`）。

- 原因：`antlrparser/` 只有 `.g4` 语法文件（`LightLangLexer.g4` / `LightLangParser.g4`），
  **没有 Java antlr4 工具生成的 `LightLangLexer.py` / `LightLangParser.py`**。
- 本轮已补装 Python 侧运行时 `antlr4-python3-runtime==4.13.2`（进项目 `.venv`），
  但**生成产物仍需 `antlr4` Java 工具链**才能产出，本机无 Java 环境。
- 因此任务书里「用 `cli/light_unified.py` 编译 中文数字转换.light / 颜色.light」这条
  端到端验证**在当前环境下不可执行**；改用**等价的 AST 级验证**
  （手工构造 `antlrparser.light_ast` 节点直接驱动 `UnifiedCodeGenerator`）——
  验证的正是同一处 `builtin_map` 查表，判据等价且不依赖 ANTLR。

## 4. 行为差异登记（同键不同值，7 项，**本轮不改**）

| 键 | hook 腿 | unified 腿 | 性质 |
| --- | --- | --- | --- |
| `首` | `lambda x: x[0]` | `__import__("operator").itemgetter(0)` | 语义等价，取元素方式不同 |
| `末` | `lambda x: x[-1]` | `__import__("operator").itemgetter(-1)` | 同上 |
| `整数` | `int` | `_light_builtin.整数` | unified 走内置包装（容错更强） |
| `去重` | `lambda x: list(set(x))` | `lambda x: list(dict.fromkeys(x))` | **顺序稳定性不同**：unified 保序 |
| `阶乘` | `math.factorial` | `_light_builtin.阶乘` | 实现不同 |
| `排序` | `sorted` | `_light_builtin.列表排序` | 实现不同 |
| `反转` | `reversed`（返回迭代器） | `_light_builtin.列表反转`（返回列表） | **返回类型不同**，潜在真实差异 |

⚠️ `反转` 一项差异最值得关注：hook 腿返回迭代器、unified 腿返回列表。
按任务书要求**只登记不擅自改语义**，留待 R63 决策（哪一侧是正解需先看 stdlib 与
examples 的实际依赖，改任一侧都可能是回归）。

## 5. 交付物与改动清单

| 文件 | 改动 |
| --- | --- |
| `light-merge/src/code_generator_unified.py` | L167 起新增 25 条字符串同族 builtin 映射（含注释说明范围与刻意不补项） |
| `light-merge/_probe_R62_builtin_diff.py` | 新增：两份 builtin_map 差集对比探针 |
| `light-merge/_probe_R62_unified_builtin.py` | 新增：无 ANTLR 依赖的 UnifiedCodeGenerator 裸名核查探针 |
| `light-merge/_task2_R62_unified去除空格缺口.md` | 本报告 |
