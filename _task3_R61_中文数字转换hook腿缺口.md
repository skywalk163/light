# R61 任务3 交付报告 · `中文数字转换.light` 裸名 `去除空格` hook 腿缺口处置

> 任务书：`复刻_第61轮_任务prompt分发_拆分后首轮全量与存量红清零轮.md` §3
> 轮次定位：0 条红（预防/顺带）｜未 commit、未 push（合流归主 agent 路M）

---

## 1. 结论

**取「补映射」方案，缺口已收口**：在 hook 腿的 `builtin_map` 补上 `去除空格` →
`_light_builtin.去除空白`，与原生腿 `codegen_typed` 早已存在的同族判定对齐。
**未改任何 `stdlib/*.light`**（保留「零导入」纯光明写法），零新机制、零新语义。

- 本机定向：**25 passed / rc=0**（新增 8 + R60 原 17，`-k "not 三后端"`）
- 0.82 定向：**26 passed / `__RC__=0`**（+ R11B 中文数字 O0 对拍 1 条）
- 顺带收口：同款缺口在 `颜色.light` / `格式化.light` / `参数解析.light` 共 3 个
  纯光明模块一并转绿（见 §2.3）

---

## 2. 缺口定位（行号级）

### 2.1 失效链路

| 腿 | 入口 | `去除空格` 的处理 | 结果 |
|---|---|---|---|
| 原生腿（LLVM O0） | `src/llvm/codegen_typed.py:2655` | `if name in ('去除空格','trim','strip','去除空白','str_strip'): → dv_trim` | ✅ 正常 |
| **hook 腿（Python import hook）** | `stdlib/_light_import_hook.py:126` → `from code_generator import PythonCodeGenerator` | `builtin_map` 只登记 `去除空白`（`src/code_generator.py:617`） | ❌ 裸名落进产物 → `NameError` |

`stdlib/中文数字转换.light:1` 首行是「纯光明实现」→ 钩子优先加载 `.light` 而非同名
`.py`（`_light_import_hook.py:250-252`），因此走 hook 腿时**必然**命中该缺口。

复现（改动前，本机）：

```
>>> import 中文数字转换
>>> 中文数字转换.中文转阿拉伯数字("一百二十三")
NameError: name '去除空格' is not defined
```

产物取证（`PythonCodeGenerator().generate(...)`，改动前）：

```
342:    文本 = 去除空格(中文串)      ← 裸名，未走 _light_builtin
544:    文本 = 去除空格(中文串)
```

### 2.2 与 `去除空白` 的语义等价性

`stdlib/字符串处理.py:51-53`

```python
def 去除空格(s: str) -> str:
    """去除两端空格"""
    return s.strip()
```

与产物前缀里既有的 `_light_builtin.去除空白 = lambda s: s.strip()`
（`src/code_generator.py:1188` / `:1241`，try/except 两分支都绑）**逐字等价**，
故映射是纯别名补齐，不改任何语义。

### 2.3 同款缺口影响面（全仓 `*.light` 扫描）

| 文件 | 行 | 说明 |
|---|---|---|
| `stdlib/中文数字转换.light` | 54、167 | 本任务目标（R60 已登记） |
| `stdlib/颜色.light` | 198、225、228 | 同款，本轮一并转绿 |
| `stdlib/格式化.light` | 207 | 同款，本轮一并转绿 |
| `stdlib/参数解析.light` | 35、37 | 同款，本轮一并转绿 |
| `examples/data_pipeline/pipeline.light` | 30/37/48/96/105/110 | 例子侧同款（未在本轮定向范围内） |

---

## 3. 处置取舍（任务书 §3 三选一）

| 方案 | 评估 | 取舍 |
|---|---|---|
| **① 补映射** | 原生腿本就把它当同族内置；补一行即两腿对齐，一次修好 4 个模块，且不破坏「零导入」写法 | ✅ **采用** |
| ② 改 `.light` 为显式全名（`去除空格`→`去除空白`） | 只治 `中文数字转换` 一处；`颜色/格式化/参数解析` 仍带缺口，且与原生腿既有的宽松收词设计相悖 | ❌ 不采用 |
| ③ 维持登记 | 缺口真实存在且可复现（非设计取舍），留红无收益 | ❌ 不采用 |

判据依据：原生腿 `codegen_typed.py:2655` 把 `去除空格` 与 `去除空白` 并列在同一族，
说明**语言层设计上 `去除空格` 就是合法的全局名**；hook 腿漏登记属实现缺口，不是刻意区分。

---

## 4. 改动文件清单（行号级）

1. **`src/code_generator.py`**（+8 行，`builtin_map`）
   - L618-624：新增注释块（R61 任务3 归因说明）
   - L625：`'去除空格': '_light_builtin.去除空白',`
2. **`tests/unit/test_R61_中文数字转换_hook腿.py`**（新增，8 用例）
   - hook 腿：`中文转阿拉伯数字` 4 例（含首尾空格/零十二）、`中文转浮点数` 3 例（含首尾空格）
   - 原生腿：`test_原生腿_中文数字转换_含首尾空格_对拍` 1 例（runner 复用
     `tests/unit/test_原生腿_R11B_中文工具.py`，不另造一份）
   - 先断言 `__file__` 以 `.light` 结尾，确保跑的是纯光明实现而非被 `.py` 顶替
3. **`tests/unit/test_R60_截取语义误用族.py`**（-1 行 + 注释更新）
   - L62-66：删除已失效的 `中文数字.去除空格 = str.strip` 桥接（保留即会掩盖本缺口的回归），
     注释同步说明收口理由
   - ⚠️ 该文件另有 **任务4 并行改动**（L153-332 三后端用例），非本任务产物，未触碰
4. **未改** `stdlib/中文数字转换.light` → 魔数护栏（L-176）天然不涉（首两行未动）

---

## 5. 本机定向结果

```
$ python -m pytest tests/unit/test_R61_中文数字转换_hook腿.py \
                 tests/unit/test_R60_截取语义误用族.py \
                 -k "not 三后端" -o addopts=
25 passed, 5 deselected        （rc=0；5 deselected = 任务4 的三后端用例，不属本任务范围）

$ python -m pytest tests/test_pure_light_hook.py tests/unit/test_L055_L061_L062.py \
                 tests/unit/test_examples_run.py -o addopts=
85 passed, 1 skipped, 1 xfailed, 22 subtests passed   （魔数护栏未红）
```

hook 腿逐值取证（改动后）：

```
中文数字转换.中文转阿拉伯数字("  一百二十三  ") -> 123      （与 .py 参考一致）
中文数字转换.中文转浮点数(" 三点一四 ")        -> 3.14     （与 .py 参考一致）
颜色.RGB解析("  #ff8800  ")                   -> [255, 136, 0]
```

---

## 6. 0.82 定向结果

- 远程副本：`/tmp/r44-20260918-202728`（R60 路M 同步副本，本例为**增量推送** 3 个文件：
  `src/code_generator.py`、`tests/unit/test_R61_中文数字转换_hook腿.py`、`tests/unit/test_R60_截取语义误用族.py`）
- 解释器：`/usr/local/bin/python3.12`（绝对路径）；推送前后 `grep` 自证映射行数 0 → 1；
  跑前 `rm -rf src/__pycache__ stdlib/__pycache__`；退出码不接管道（`echo __RC__=$?`）

```
__RC__=0
26 passed, 5 deselected   in 6.48s
```

（26 = 新增 8 + R60 原 17 + `test_原生腿_R11B_中文工具.py::test_中文数字转换_O0对拍` 1）

---

## 7. 如实声明（与任务书红线的偏差 / 范围外发现）

1. **实修范围大于任务书目标 1 处**：任务书只点 `中文数字转换.light`；同类裸名在
   `颜色.light`/`格式化.light`/`参数解析.light` 另有 5 处，属**同一根因**，随补映射一并转绿。
   未越界改语义（映射目标即 `str.strip`）。
2. **`code_generator_unified.py`（ANTLR/unified 后端）仍带同款缺口**（本任务**未修**，登记）：
   实测 `UnifiedCodeGenerator().generate(中文数字转换.light 的 AST)` 产物中裸名
   `去除空格(中文串)` 仍出现 **2 行**。它与 `src/code_generator.py` 是两套独立表
   （`code_generator_unified.py:167` 同样只登记 `去除空白`）。
   任务书 §3 的「hook 腿」= `_light_import_hook` → `code_generator.py`，unified 后端不在其内；
   一行等价映射（`'去除空格': '_light_builtin.去除空白'`）即可收口，**建议**由任务4
   「三后端覆盖」一并决定是否纳入。
3. **范围外观测（影响 R61 门，请路M/任务4 关注）**：推送 `test_R60_截取语义误用族.py` 时该文件
   已含**任务4 并行新增的三后端用例**。其中 **2 条在原生腿 O0 上红**，且**本机与 0.82 双侧一致复现**：
   - `test_三后端_颜色_RGB解析去井号`：原生腿 `rc=1`，`运行时错误 at RGB解析`
   - `test_三后端_参数解析_等号切分与去横线`：原生腿输出 2 行、期望 3 行（缺 `test`）
   两条的 **src 后端断言均通过**（正是本任务补映射后才可能通过：改动前 `颜色.RGB解析`
   /`参数解析.参数转类型` 在 src 腿会直接 `NameError`）。失败点全在原生腿，与本任务改动
   无关（本任务只动 Python 侧 `builtin_map`，LLVM 路径 `src/llvm/` 无任何 `code_generator`
   引用；已实测取证）。若这两条计入全量，将形成 **2 条新增红**，与「预期 0 红」冲突，
   **建议任务4 收口前处置**（或按任务书 §4「明确记录不可跑腿原因」降级为登记）。
4. **本机另有一条与本次改动无关的存量红**（已用 `git stash` 单文件回退取证：基线同样红）：
   `tests/unit/test_原生腿_R11B_中文工具.py::test_中文分词_O0对拍`
   （`分词len[今天天气真不错] assert 3 == 4`）。本机 Windows 红、R60 门 0.82 基线内绿，
   属本机环境差异，非本轮引入。
5. **未跑全量**（本机零全量；0.82 全量仅路M 1 次），**未 commit / 未 push**。
6. 未改 `stdlib/*.light`，L-176 魔数护栏无从触发；`test_pure_light_hook.py` 本机复跑未见红。
7. 临时探针/0.82 驱动脚本已全部删除，工作区无本任务遗留临时文件。

---

## 8. 遗留 / 建议

- unified（ANTLR）后端同款映射缺失：已登记，一行可修，交由任务4/路M 决策。
- 任务4 三后端用例的原生腿 2 红：**会影响 R61 门**，见 §7.3，非本任务范围。
- `examples/data_pipeline/pipeline.light` 的 6 处裸名 `去除空格` 现已随本映射在 hook 腿可用；
  该例子未纳入本轮定向。