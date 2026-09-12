# 任务4（语法便利+错误提示）交付报告 —— L-080 切片下标报错 + L-081 尾随逗号 + L-067 全局声明

> 日期：2026-09-12 ｜ 任务书：`光明语言改进_并行任务书.md` 任务4 ｜ 目标仓库：`G:\dswork\duan-light-merge\light-merge`
> 验证仓库：`G:\dswork\duan-light-merge\lightharness` ｜ 后端：`light run` 默认 SRC（`light_parser_v3` + `PythonCodeGenerator`）
> 基线：`ab57e2b4`（docs(task-net-native)）｜ 本路改动：见文末「改动文件清单」

---

## 0. 结论摘要

| 缺陷 | 现象 | 修复方式 | 验收状态 |
|---|---|---|---|
| L-080 | float 作切片下标报 Python 英文异常，光明提示与根因无关 | 运行时切片下标检查（builtins 真身 + 生成器包装 + 注入兜底） | ✅ 报错文案与任务书原文逐字一致，指向源码行 |
| L-081 | 字典/列表字面量尾随逗号报「意外的标记: ]」 | 解析器放行尾随逗号（对齐列表/花括号分支） | ✅ 带尾随逗号字典/列表均正常解析 |
| L-067 | 段落内重绑模块级变量静默建局部，新手不知需 `全局 X;` 声明 | 文档化（LANGUAGE_EXTENSIONS.md 追加 2.2.1 全局声明） | ✅ 文档已补充（任务书允许「提示或文档」二选一） |

---

## 1. L-080 浮点除法结果作切片下标报错误导

### 1.1 缺陷根因

`(长*70)/100 = 14000.0` 为 float。`结果[0:头部长]` 切片下标为 float 时，Python 原生抛：

```
slice indices must be integers or None or have an __index__ method
```

光明 `enhanced_errors`/错误格式化把该异常按通用类型不匹配包装，提示「光明中文本和数字不能直接进行运算」——与真实根因（切片下标必须是整数）无关，误导排查。

运行路径确认：`light run` 默认走 **SRC 后端**（`cli/light.py::_compile_src` → `light_parser_v3.LightParser` + `code_generator.PythonCodeGenerator`）；lightharness 运行时加载 `<脚本目录>/stdlib/builtins.py` 自包含 stdlib（不依赖 light-merge 的 stdlib 安装）。

### 1.2 修复点

三层（防御性叠加，保证各运行环境都生效）：

1. **`stdlib/builtins.py` 真身**（light-merge 与 lightharness 两处同名新增，`def 转浮点` 前）：

   ```python
   def 切片下标检查(v):
       """L-080：切片下标必须是整数；非 int 给出明确中文错误（替代 Python 原生 slice indices 报错误导）"""
       if isinstance(v, bool) or isinstance(v, int):
           return v
       if isinstance(v, float):
           名 = '浮点数'
       elif v is None:
           名 = '空值'
       elif isinstance(v, str):
           名 = '文本'
       elif isinstance(v, list):
           名 = '列表'
       elif isinstance(v, dict):
           名 = '字典'
       else:
           名 = type(v).__name__
       raise TypeError('切片下标必须是整数，实际为' + 名 + ' ' + str(v) + '，请用 整数() 转换')
   ```

   错误文案与任务书原文逐字一致：「切片下标必须是整数，实际为浮点数 14000.0，请用 整数() 转换」。

2. **`src/code_generator.py` 切片分支包装**（IndexAccess/SliceExpr 分支）：`start`/`stop`/`step` 均包 `_light_builtin.切片下标检查(...)`，运行时先检查再进原生切片。

3. **注入头兜底**（两处：`import types` 分支 与 `else` 分支的 `_light_builtin.转浮点 = float` 之后各加一行）：
   `_light_builtin.切片下标检查 = lambda v: v`
   —— 防止运行环境缺失 stdlib 真身时生成代码 AttributeError；有真身时真身生效，无真身时退化为不检查（行为与修复前一致）。

### 1.3 最小复现

`lightharness/examples/_repro_L080.light`（修复形态 rc=0，头部长=14000 切片长度=14000）。

失败形态（临时文件验证后已删，报告附源码）：

```光明
段落 主:
  设 长 为 20000
  设 结果 为 ""
  设 i 为 0
  当 i 小于 长:
    结果 为 结果 + "x"
    i 为 i + 1
  设 头部长 为 (长*70)/100
  设 头 为 结果[0:头部长]
  写 转字符串(长度(头))
主()
```

### 1.4 验证结果

失败形态实测输出（修复后）：

```
类型错误：切片下标必须是整数，实际为浮点数 14000.0，请用 整数() 转换（G:\dswork\duan-light-merge\lightharness\examples\_tmp_L080_fail.light:11）
（Python 原始错误：切片下标必须是整数，实际为浮点数 14000.0，请用 整数() 转换）
```

- ✅ 中文明确错误，文案与任务书期望逐字一致；
- ✅ 指向光明源码行（`文件:11`，定位到调用链顶层 `主()` 调用行；行号由既有 L-061 映射机制给出，错误消息正文精确说明根因与绕法）。

---

## 2. L-081 字典/列表字面量不支持尾随逗号

### 2.1 缺陷根因

`light-merge/src/parser_expr.py::_parse_list_literal` 方括号字典分支：

```python
entries = [(first_expr, value_expr)]
while self._match(TokenType.COMMA):
    self._consume(TokenType.COMMA)
    while ... 跳过 NEWLINE/INDENT/DEDENT ...
    key = self._parse_comparison()      # ← 尾随逗号时，这里直接遇到 RBRACKET
    self._consume(TokenType.COLON)      # ← 报「意外的标记: ]」
```

逗号后**无条件解析 key**，未处理「`,` 后直接 `]`」的尾随逗号 → `_parse_comparison()` 遇 `]` 报「意外的标记: ]」，报错定位在 `]` 而非逗号，误导排查。

对照确认（同文件/同文件其他分支均已支持）：
- 方括号**列表**元素循环（`elements` 循环）：`if self._match(TokenType.RBRACKET): break` ✅ 已有；
- 花括号字典/集合（`_parse_dict_literal`）：`RBRACE` break ✅ 已有；
- **仅方括号字典分支缺失** —— 本次补上。

### 2.2 修复点

`src/parser_expr.py` 方括号字典分支，逗号后跳过换行/缩进之后、解析 key 之前加：

```python
# L-081：尾随逗号（"," 后直接 "]"）与 Python/JS 一致放行；
# 与方括号列表、花括号字典/集合的尾随逗号处理对齐。
if self._match(TokenType.RBRACKET):
    break
```

### 2.3 最小复现

`lightharness/examples/_repro_L081.light` —— 已改写为**修复形态**（任务书验收第 5 条：L-081 绕法「末尾不加逗号」恢复为带逗号）：

```光明
段落 主:
  设 甲 为 [
    "x": 1,
    "y": 2,
  ]
  设 乙 为 [1, 2, 3,]
  写 "复现L-081（修复形态 rc=0）：尾随逗号可解析，甲y=" + 转字符串(甲["y"]) + " 乙末=" + 转字符串(乙[2])
主()
```

### 2.4 验证结果

```
复现L-081（修复形态 rc=0）：尾随逗号可解析，甲y=2 乙末=3
```

✅ 带尾随逗号的字典/列表均 rc=0；绕法（原先在 lightharness 源码中刻意不加末尾逗号）可恢复为带逗号写法。

---

## 3. L-067 段落内重绑模块级变量须 `全局` 声明

### 3.1 缺陷根因

模块级 `设 X 为 ""` 后，段落内直接 `设 X 为 值` 不会透出模块作用域——编译器不发射 `global X`，重绑变成段落局部变量，段落外读 `X` 仍是初值（静默失败）。新手不知需 `全局 X;` 声明。这是 Python 原生语义（函数内赋值即建局部），光明忠实继承。

### 3.2 修复点（文档化方案）

任务书允许「编译提示 或 文档化」二选一（并指明 L-065 已在 `LANGUAGE_EXTENSIONS.md` 补充导入绑定语义，可追加全局声明说明）。本路选**文档化**（不碰解析器/生成器，零回归风险，成本低）。

`light-merge/docs/LANGUAGE_EXTENSIONS.md` 在 `### 2.2 模块导入` 与 `### 2.3 标准库导入` 之间新增 `### 2.2.1 全局声明（段落内重绑模块级变量）`，内容含：

- 约定解读（模块级变量属模块作用域；段落内直接 `设 X 为 值` 静默建局部）；
- 正确写法示例（`全局 X` 声明后重绑透出）；
- 错误写法示例（漏 `全局` 静默失败）；
- 判定提示（「段落内改了变量、段落外没变」先查是否漏 `全局`；多变量 `全局 X, Y, Z`）。

### 3.3 验证结果

✅ 文档小节已追加（锚点 `### 2.3 标准库导入` 之前），检索 `2.2.1 全局声明` 可定位。

---

## 4. lightharness 全量 CI 说明

`python scripts\ci_test.py`（含 `$env:LIGHT_MERGE` 指向 light-merge）首跑 540s 结果为 4 failed / 233 passed，4 项逐一归因：

| 失败项 | 归因 | 处理 |
|---|---|---|
| `_tmp_L080_fail.light` | **本路临时复现文件**残留在 examples/ 被 CI 扫描（期望 rc=0 而临时文件是失败形态 rc=1） | ✅ 已删除临时文件 |
| `test_CLI命令面.light` | 独立复跑 rc=0（CI 高负载偶发；`test_审批` 同因，失败项为「耗时 < 1.5s」时序断言） | 与并行任务中间态/偶发相关，非本路改动引入 |
| `test_审批.light` | 独立复跑 rc=0（同上偶发/时序） | 同上 |
| `test_修复_LLM.light` | 稳定 rc=1：`cannot import name '拷贝内容块表' from '消息'` —— lightharness 工作树中 `src/消息.light` 正被**并行任务2**（L-082/L-083 拷贝原语）改写（删除 `拷贝内容块表` 绕法、切换 `深拷贝` 原语），为并行任务的**进行中中间态**，非本路改动引入 | 由任务2 完成后自洽；路M 收口统一验证全绿 |

本路改动与并行任务改动域互斥（parser_expr / code_generator 切片分支 / builtins 切片下标检查 / 文档 2.2.1 均未触碰并行任务文件）；本路相关验证（`_repro_L080`、`_repro_L081`、失败形态报错）全部通过。**全量 CI 全绿由路M 在 5 路完成后统一收口确认**（任务书「路M」节约定）。

---

## 5. 反跑判据（改回修复 → 复现红）

> 原则：把修复改回缺陷态，对应复现文件必须变红（rc≠0 / 报错现象重现），否则判据不成立。

| 缺陷 | 改回动作 | 预期红（缺陷态） | 当前绿（修复态） |
|---|---|---|---|
| L-080 | 把 `stdlib/builtins.py` 中 `def 切片下标检查(v)` 的检查体改回 `return v`（或把 code_generator 注入兜底改回 `lambda v: v` 且删除真身注册） | `_repro_L080.light` 失败形态下：`结果[0:头部长]` 抛 Python 原生 `slice indices must be integers or None or have an __index__ method`，光明提示「文本和数字不能直接进行运算」与根因无关（误导提示重现） | rc=0：`头部长=14000 切片长度=14000` |
| L-081 | 删除 `parser_expr.py` 方括号字典分支的 `if self._match(TokenType.RBRACKET): break` | `_repro_L081.light`（带尾随逗号）报「意外的标记: ]」（报错定位在 `]` 而非逗号） | rc=0：尾随逗号可解析 |
| L-067 | 删除 `LANGUAGE_EXTENSIONS.md` 的 `### 2.2.1 全局声明` 小节 | 文档检索 `2.2.1 全局声明` 无结果；新手无从获知 `全局 X;` 声明约定（L-067 现象重现） | 小节存在，含正反示例与判定提示 |

复现文件即判据载体：`examples/_repro_L080.light`（修复态绿）、`examples/_repro_L081.light`（修复态绿）。改回动作按上表执行后运行 `python 运行.py examples/_repro_L0XX.light` 必须变红。

---

## 6. 改动文件清单（本路，均未提交前状态）

| 文件 | 改动 |
|---|---|
| `light-merge/src/parser_expr.py` | L-081：方括号字典分支尾随逗号放行（RBRACKET break） |
| `light-merge/src/code_generator.py` | L-080：切片 start/stop/step 包 `_light_builtin.切片下标检查`；注入头两处兜底 `lambda v: v` |
| `light-merge/stdlib/builtins.py` | L-080：新增 `切片下标检查` 真身（`def 转浮点` 前） |
| `light-merge/docs/LANGUAGE_EXTENSIONS.md` | L-067：新增 `### 2.2.1 全局声明（段落内重绑模块级变量）` |
| `lightharness/stdlib/builtins.py` | L-080：同名真身（验证侧自包含 stdlib） |
| `lightharness/examples/_repro_L081.light` | L-081：改写为修复形态（带尾随逗号字典+列表），rc=0 |

> 注：本路未提交 git（等待任务书各路收口统一合入）；lightharness 工作树存在并行任务（任务2 拷贝原语）的进行中改动，与本次改动域互斥、无冲突。
