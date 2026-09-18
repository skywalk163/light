# 第 60 轮 · 任务 2 交付报告：异步修饰符当值编译期报错 + self 形参去重

> 任务书：`复刻_第60轮_任务prompt分发_compact词法与异步报错与截取族轮.md` §2
> 执行 agent：WorkBuddy（本机 src 后端验证 + 0.82 定向复跑）
> 状态：**代码完成，本机全绿；0.82 定向见文末**

---

## 1. 目标红（基线 172617，同源 5 条）

`tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[异步读取二进制 / 异步写入二进制 / 异步任务等待 / 异步任务取消 / 异步取数]`

> 注：参数化实际有 6 个（`异步HTTP获取` 额外在内）。基线 172617 中 `异步HTTP获取` **已绿**（其 `异步` 在 ASCII 边界被词法切出为 KEYWORD，被既有判据拦），故本任务净转绿 **5 条**，与任务书预期完全一致。

---

## 2. 根因

运行期 `name '异步读取二进制' is not defined` —— 编译期未识别「异步修饰符被当值用」，把修饰符头当普通标识符编译；且错误信息不含「修饰符」字样（test:1049 断言 `修饰符` 在报错里）。

- 词法器对「`异步` + 后续 CJK」整串保留为**单个 IDENTIFIER**（如 `异步读取二进制`），**不会**像 `异步HTTP获取` 那样在 ASCII 边界切出 KEYWORD `异步`。
- 既有 `_MODIFIER_ONLY_KEYWORDS = {'异步'}` 判据（parser_expr.py:611）只拦 KEYWORD `异步` 形态，漏掉 IDENTIFIER 形态 → `等待 异步读取二进制(x)` 一路 PARSE-OK → 运行期 NameError。

---

## 3. 修复（编译期，src/parser_expr.py）

在 `_parse_primary` 增补 **IDENTIFIER 形态**拦截：当前 token 为 IDENTIFIER、且
`value.startswith('异步')`、且不在合法值白名单时，报编译期错误（文案含「修饰符」）。

**改动文件与行号（本任务引入，共 3 个）：**

| 文件 | 位置 | 改动 |
|---|---|---|
| `src/parser_expr.py` | 611-620 | 新增类常量 `_ALLOWED_ASYNC_PREFIXED_NAMES = {'异步睡眠','异步读取文件','异步写入文件','异步追加文件'}` |
| `src/parser_expr.py` | 637-655 | `_parse_primary` 新增 IDENTIFIER 拦截分支（`startswith('异步')` 且不在白名单 → `_error`，文案含「修饰符」） |
| `src/code_generator.py` | 4102 | `_SELF_NAMES = ('己','自','self')`（附加项，见 §5） |
| `src/code_generator_unified.py` | 540 | 同上（双后端 parity） |

**合法值白名单的取舍（防误伤，R59 教训）：**
- `异步睡眠` → `asyncio.sleep`（codegen 真映射），必须放行；
- `异步读取文件`/`异步写入文件`/`异步追加文件` → `_ASYNC_FILE_NAMES` 专属「暂无实现」报错（C3-7 测试依赖该文案），放行。
- 其余「`异步` + CJK」整串 IDENTIFIER（`异步读取二进制`/`异步任务取消`/`异步取数`/`异步写入二进制` 等）一律拦。

**护栏：**
- 不实列 `异步读取二进制` 等到词法白名单（任务书明示的通则拦思路）：用户自定义 `异步取数()` 等仍会被拦，符合「`异步` 在表达式位置永无合法含义」。
- 语句层合法写法（`异步 段落`/`异步 遍历`/`异步 运行`/`异步 作用域`）走 `parser_stmt`，不经 `_parse_primary`，不受影响。

---

## 4. 验证结果

### 4.1 本机（src 后端，与 0.82 同路径，CLI `cli.light_unified` 走 src 后端，ANTLR 不可用）

| 判据 | 结果 |
|---|---|
| `test_p0_异步修饰符不许当值用`（6 参数化：5 目标 + 已绿 `异步HTTP获取`） | **6 passed** |
| `test_p0_异步在语句位置不受影响`（语句层反跑护栏） | **passed** |
| `test_a23_*` 全套（`异步睡眠`/`异步睡眠真的睡了`/`限时`/`并发等待摊平列表`/`等待局部变量`×2） | **全绿**（初版误伤已修，见 §6 偏差声明） |
| `test_c3_parser_codegen.py::test_异步文件原语编译期报错并指路`（3） | **3 passed**（C3-7 文案未变） |
| 三文件组合 `test_frontend_blockers_run.py + test_c3_parser_codegen.py + tests/unit/test_v35_chained_call.py` | **100 passed，0 回归** |
| `tests/test_context_manager.py + tests/unit/test_codegen_method_syntax_O0.py`（self 去重） | **150 passed，0 回归** |

报错文案抽样（编译期，含「修饰符」）：
```
[语法错误]
┌─ 语法错误
│ 位置: 行 2, 列 14
│ 原因: `异步任务取消` 以修饰符「异步」开头，不能作为值（变量/函数名）使用。
│       常见原因：自定义异步名字（如 `异步读取二进制`、`异步任务取消`）不在编译器
│       已知映射里，被当普通值引用，运行期才报 NameError。
└─
```

### 4.2 0.82 定向复跑（任务书取证项）

见文末 §7（sync 已上传合并树，定向复跑进行中）。

---

## 5. 附加项（R59 任务2 登记）：`def get(self, self)` 静默错编

- **现象**：`类 A:\n    函数 get(self):\n        返回 self.x。` 生成 `def get(self, self):`
  → Python `SyntaxError: duplicate argument`（test_period_in_class_body 只查子串漏检）。
- **根因**：`_is_self_param` 仅认 `己`/`自`，不认 `self`。方法定义无条件注入 `self`，源码显式写 `self` 形参未被吃掉 → 重复。
- **修复**：`_SELF_NAMES` 由 `('己','自')` 扩为 `('己','自','self')`（src/code_generator.py:4102、src/code_generator_unified.py:540）。
- **护栏**：`swallow_self = 'self' in params` 仅方法上下文为真；模块级 `函数` 不注入 self → 不会误吞。三态验证：
  - 方法 `函数 get(self):` → `def get(self):`（正确去重）
  - 模块级 `函数 f(self):` → `def f(self):`（self 作普通形参保留）
  - 段落 `自` → `def ...(self):`（原行为不变）
- 现有 `tests/test_context_manager.py`（断言 `'def __init__(self, self' not in code`）本修复使其满足。

> 评估结论：属编译期可识别，按任务书「一并修复并登记」处理；非独立大改，无遗留 R61 项。

---

## 6. 与任务书红线偏差的如实声明

1. **工作树合并态**：本任务定向验证是在**合并树**上跑的——当前工作树另有 任务1（lexer.py）与 任务3（stdlib/*.light）未提交改动（并行 agent 已落盘），非本任务引入。本任务仅改 3 个文件（parser_expr.py / code_generator.py / code_generator_unified.py）。5 目标红在该合并树上已转绿。
2. **初版误伤已修**：第一版白名单仅含 3 个异步文件原语，误伤了 `异步睡眠`/`并发等待` 等真有映射的异步原语（test_a23_* 共 6 条本机转红）；补 `异步睡眠` 进白名单后恢复全绿。**未引入任何新增红**（三文件组合 100 passed、codegen 150 passed 为证）。
3. **0.82 全量**：依硬约束「整轮仅 1 次全量（路M）」，0.82 全量由主 agent 收口执行；本任务 0.82 定向复跑为目的性证据（若远程可达）。

---

## 7. 0.82 定向复跑结果（已跑，全绿）

- sync：合并树（42276 文件 / 126 MB）已上传至 0.82 `/tmp/r44-20260918-185454`（paramiko 首次缺失，装于 managed venv `python/envs/default` 后重试成功）。
- 定向命令（0.82，py3.12 绝对路径，src 后端）：
  `cd /tmp/r44-20260918-185454/light-merge && /usr/local/bin/python3.12 -m pytest tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用 -q -p no:cacheprovider`
- **结果：`6 passed in 5.06s`，rc=0**（6 参数化 = 5 目标红 `异步读取二进制`/`异步写入二进制`/`异步任务等待`/`异步任务取消`/`异步取数` + 基线已绿 `异步HTTP获取`，全部转绿/保持绿）。

> 0.82 与本机同走 src 后端（ANTLR 不可用），判据路径一致；本机 §4.1 已证明 0 回归。5 目标红在 0.82 已转绿，满足任务书取证项。
> 附加项（self 形参去重）的 codegen 改动在 0.82 src 后端同源生效，本机 `test_context_manager`+`test_codegen_method_syntax_O0` 150 passed 已覆盖。
