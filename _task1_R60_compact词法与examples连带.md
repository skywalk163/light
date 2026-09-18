# 第60轮 任务1 · compact 无空格二元运算符（词法层）+ examples 连带清障 交付报告

> 范围：`复刻_第60轮_任务prompt分发_compact词法与异步报错与截取族轮.md` **任务1**（light-merge 仓）
> 改动仓：`light-merge/`（已改 `src/lexer.py` + `src/code_generator.py`，未提交）
> 基线：`lightharness/reports/082_lightmerge基线_2026-09-18-172617.json`（13 红）
> 分工声明：**仅任务1**。任务2（`src/parser_expr.py`）与任务3（stdlib 截取族）的未提交改动系其它 agent 已在工作区落盘，本任务未触碰、未回退（隔离验证时临时还原过 `parser_expr.py`，验证后原样恢复）。

---

## 一、结论

| 判据 | 结果 |
|---|---|
| 目标红 1 `tests/unit/test_parser.py::TestParser::test_compact_binary_expr_with_call` | **转绿** |
| 目标红 2 `tests/unit/test_examples_run.py::TestExampleFilesRun::test_all_examples_output` | **转绿**（22 subtests 全过；该测试含 5 个子失败，全部清障，见第三节） |
| 本机定向（parser/examples/类系统 4 文件 + 钉桩 R19 + T6C×2） | **408 passed / 0 failed** |
| 0.82 定向（副本 /tmp/r44-20260918-190439，py3.12） | **405 passed / 0 failed**（同 6 文件） |
| 全语料 token A/B（38091 文件，HEAD 词法器 vs 当前词法器） | **6 个文件变化，逐条取证为同族改善**（第五节） |
| 互举反跑（677 .light，隔离口径） | **0 新增解析失败；已修复 2**（第四节） |
| 行尾 / 魔数 | 2 文件全 CRLF、0 bare LF；未改任何 `.light`，护栏不适用 |

**⚠️ 必须向主 agent 声明的跨任务问题（非任务1 造成，但影响 R60 门）**：工作区已有**任务2 的 parser_expr.py A2-3 拦截**（IDENTIFIER 形态「异步*」当值一律报错）。互举反跑在**含该改动的口径下新增 3 条解析失败**（`stdlib/并发.light` 81、`stdlib/HTTP服务端.light` 451、`examples/test_R21_L152家族嵌套形参.light` 66——`异步作用域`/`异步接受`/`异步信号量` 等合法已定义名被拦截）。隔离口径（parser_expr.py 还原为 HEAD）为 0 新增。**该拦截判据需任务2 agent 收窄（放行已定义名/调用语境），否则路M 全量会撞 3 条新增红。** 详见第四节。

---

## 二、修复内容（行号级）

### 2.1 修复A：运算符 + 已知名 + `(` 的并入例外（核心，`src/lexer.py` 探测循环 :2945 附近，+18）

**根因（实测取证）**：`n乘阶乘(n减1)` 中 ASCII 分支已切出 `IDENTIFIER 'n'`，随后的汉字段 `乘阶乘` 命中探测循环 R20 规则「纯 CJK 串含运算符 + 整串后紧跟 `(` → 整串按函数名并入」（:2945-2950）。该规则**没有**输出循环 :3097-3102 早就有的 v7-单02 例外（运算符余部恰为已知名时不并入）→ `乘阶乘` 整串成 IDENTIFIER，再被 parser_expr 的相邻标识符合并粘成 `n乘阶乘` 调用名 → NameError。同族：`返回斐波那契(数减一)加斐波那契(数减二)` 的汉字段 `加斐波那契`（advanced.light 行11，症状：斐波那契全打 1）。

**修复**：在该规则上加同款例外——运算符余部 ∈ `STDLIB_VERB_ARITY / ALL_VERB_ARITY / user_definitions`（即 `(` 属于余部名字的调用）时**不得**并入；并加**左操作数收窄**防误伤：
- 运算符在段首且段前紧邻非汉字字符（`n乘阶乘` 的 `n` / `)加斐波那契` 的 `)`）⇒ 左操作数在段外，放行；
- 运算符在段中且左部 ∈ user_definitions（`数乘阶乘` 的 `数` 是已声明形参）⇒ 放行；
- 其余（`删除环境变量(` 的 `除`，左部 `删` 未声明）⇒ 维持并入，复合函数名零波及。

**效果**：`n乘阶乘(n减1)` → `n` `乘` `阶乘(n减1)`；`…加斐波那契(…)` → `加` + `斐波那契(…)`。

### 2.2 修复B：R21 上下文合并的 `接收`/`己`/`自` 定向豁免（`src/lexer.py` :2567 附近，+6 -1）

**根因（实测取证）**：basic.light 行20 `段落加法接收甲，乙：`，汉字段 `接收甲` 被 R21「非语句起始的关键字前缀标识符整体成词」并入（lead `接收`），`接收` 关键字丢失 → 解析期「期望冒号得到逗号」（basic.light 全文件 ParseError）。student_management.light 的 `己平均成绩` 同被 R21 并入单标识符，读取位无 self 语义 → NameError。

**修复**：R21 判据新增定向豁免（其余复合名一律维持既有并入，**严禁一般化放开**——首轮实现用「余部 ∈ user_definitions 即拆」的一般化闸门，实测误伤 40+ 文件——`设备名`→`设`+`备名`、`设置`→`设`+`置`、`函数甲`→`函数`+`甲`、`定义X`/`导入X`/`从X`/`假注册表` 等（`备`/`置` 等单字会被 _scan_user_definitions 荒谬登记，如 磁盘IO.light 的 ud 含 `'备'`），与 R59「31 文件误伤后回退」同款教训，已全部回退收窄为两条）：
1. `接收` + 余部已声明（形参必被 `_scan_user_definitions` 登记）**且** 整串后紧随 `，/：`（真形参表位置）——`网络流量控制.light` 的自由名 `接收缓存`（非形参表位置）不受影响；
2. `己/自` + 余部已声明（self 前缀读位，与 R59 任务1 1B 的 codegen 粘连展开同族）——`己平均成绩` → `己` + `平均成绩`。

### 2.3 修复C：src 后端 `_class_attr_names` 沿继承链收集（`src/code_generator.py`，+27 -2）

**根因（实测取证）**：class_complete.light 中 `狗`/`猫`（继承 `动物`）方法内读取 `己名称`，R59 任务1 1B 的读取位展开判据是「剩余部分 ∈ _class_attr_names」，而 src 后端 `_generate_class_definition`（:2708）只收**本类** `stmt.attributes`——基类声明的属性不在集合内 → 不展开 → 运行期 NameError（unified 后端同位置 R59 已有 `_collect_class_attr_names`，本修复把同口径补齐到 src 后端）。

**修复**：`__init__` 新增 `self._class_attr_registry: dict`（类名→属性名集合，按生成顺序登记）；`_generate_class_definition` 收集本类属性后，沿 `stmt.base_classes / stmt.superclasses` 并入基类属性全集再登记。前向引用基类（尚未生成）查不到，与修复前行为一致（不更差）。

---

## 三、目标红 2 的 5 个子失败清障明细

`test_all_examples_output` 实测含 5 个子失败（基线内全部存在，非本轮新增）：

| 子失败 | 症状 | 归属修复 |
|---|---|---|
| hello.light | `name 'n乘阶乘' is not defined` | 2.1（乘阶乘 切分） |
| advanced.light | 斐波那契全打 `1`（`加斐波那契` 并入，加法右操作数丢失） | 2.1（加斐波那契 切分） |
| basic.light | 行20 `段落加法接收甲，乙：` ParseError | 2.2（接收甲 切分） |
| student_management.light | `name '己平均成绩' is not defined` | 2.2（己平均成绩 切分） |
| class_complete.light | `name '己名称' is not defined`（狗/猫读基类属性） | 2.3（继承链属性收集） |

---

## 四、护栏证据

### 4.1 全语料 token A/B（38091 文件，`_r59_dump_tokens.py`，HEAD 词法器 vs 当前词法器，同一文件内容）

**6 个文件变化，逐条取证**（与「预期：examples/basic.light、hello.light 及所修用例文件」对齐，另 2 个 `己X` 同族文件如实列出）：

| 文件 | before → after | 判定 |
|---|---|---|
| examples/hello.light | `IDENTIFIER(乘阶乘)` → `KEYWORD(乘)+IDENTIFIER(阶乘)` | 修复A 同族改善 |
| examples/basic.light | `IDENTIFIER(接收甲/接收数)` → `KEYWORD(接收)+IDENTIFIER(甲/数)`；`IDENTIFIER(数乘阶乘)` → `数+乘+阶乘` | 修复B/修复A 同族改善 |
| examples/advanced.light | `IDENTIFIER(加斐波那契)` → `KEYWORD(加)+IDENTIFIER(斐波那契)` | 修复A 同族改善 |
| examples/student_management.light | `IDENTIFIER(己平均成绩)` → `KEYWORD(己)+IDENTIFIER(平均成绩)` | 修复B 己X 同族（读取位 self 语义恢复） |
| demo/reasonix_single.light | `IDENTIFIER(己环节列表×3 / 己历史记录×2)` → `KEYWORD(己)+IDENTIFIER(…)` | 同上（parse+codegen 复验 OK，635 行） |
| examples/Z阶段_可选类型系统/Z7_类与接口类型标注.light | `IDENTIFIER(己平均分)` → `KEYWORD(己)+IDENTIFIER(平均分)` | 同上（复验 OK，352 行） |

其余 43 个曾出现的 token 变化（设备名/设置/设施/函数甲/定义X/导入X/从X/假注册表/删除环境变量/网络流量控制接收缓存等）**经逐条取证为误伤，已通过收窄判据全部回退**（相关文件 token 与 HEAD 逐字节一致）。

### 4.2 互举反跑（677 .light）

- **隔离口径**（parser_expr.py=HEAD，仅本任务改动）：**新增失败 0**；已修复 2（test_R22_嵌入关键字冗余验证 / test_R26_词首并入混合）；基线内仍失败 2 → ✅ 绿
- **工作区口径**（含任务2 A2-3 拦截）：新增失败 3（并发.light/HTTP服务端.light/test_R21——`异步作用域`/`异步接受`/`异步信号量`），**全部由任务2 拦截过宽导致，非任务1 词法改动**。已临时还原复验后原样恢复任务2 文件。

### 4.3 本机 + 0.82 定向

- 本机（light-merge venv py3.13）：6 文件定向 405 passed + 钉桩/T6C 3 passed = 408 passed / 0 failed
- 0.82（/tmp/r44-20260918-190439，`/usr/local/bin/python3.12`）：6 文件定向 **405 passed / 0 failed**
- `tests/test_R40_语言支撑配套.py::test_现状钉桩_R19_为字整串合并`、T6C 参数解析/URL 对拍：**全绿**（R59 修复未被破坏）

---

## 五、改动文件清单（2 文件，未 commit）

```
light-merge/src/lexer.py           (+33 -3)  修复A（探测循环运算符例外+左操作数收窄）+ 修复B（R21 接收/己/自 定向豁免）
light-merge/src/code_generator.py  (+27 -2)  修复C（src 后端 _class_attr_registry 继承链属性收集）
```

---

## 六、风险与红线偏差声明

1. **改动面超出「词法层」**：修复C 落在 `src/code_generator.py`（非 lexer）。这是目标红 2 的 5 个子失败中 class_complete.light 的必要修复（R59 1B unified 侧已同款、src 侧缺口），且 392 条类系统相关测试全绿背书。若主 agent 认为越界，可单独回退该文件，代价是 test_all_examples_output 退回红（其余 4 子失败不受影响）。
2. **token A/B 红线偏差**：任务书预期变化集「examples/basic、hello 及所修用例文件」，实测 6 文件——超出部分为 reasonix_single.light、Z7_类与接口类型标注.light（`己X` 读取位展开同族，2.2 修复B 的连带改善，已逐条取证+复验）。
3. **`接收`/`己`/`自` 豁免均为定向判据**（余部已声明 + 形参表位置/自前缀），一般化闸门实测误伤 40+ 文件已全部回退，防误伤证据见 4.1。
4. **跨任务风险（需主 agent 收口前裁决）**：任务2 的 `异步*` IDENTIFIER 一律拦截会新增 3 条解析失败（详见第一节 ⚠️）；按分工未越权代修。
5. 未跑全量（任务书硬约束：整轮仅路M 1 次）；0.82 副本含任务2/3 未提交改动（工作区现状），但目标 6 文件的 405 passed 不受其影响。
