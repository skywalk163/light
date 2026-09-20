# 第59轮 任务1 · 词法 L-174 变体 + codegen 粘连修复 交付报告

> 范围：`复刻_第59轮_任务prompt分发_codegen粘连与L174变体轮.md` **任务1**（light-merge 仓，20 条）
> 改动仓：`light-merge/`（已改 `src/lexer.py` + `src/code_generator.py` + `src/code_generator_unified.py`，未提交）
> 基线：`lightharness/reports/082_lightmerge基线_2026-09-18-133701.json`（64 红）

---

## 一、结论

| 判据 | 结果 |
|---|---|
| 任务1 目标 20 条（本机） | **20/20 全绿**（24 passed / 0 failed，rc=0） |
| 任务1 目标 20 条（0.82 py3.12） | **全绿**（随 7 文件定向一并验证） |
| 7 个相关文件全量（本机 & 0.82） | **两侧均 14 failed / 478 passed**，14 条**全部为基线内红**（task2/task4 范畴）→ **0 新增红** |
| 全语料 token A/B（38091 文件） | **3 个文件变化，全部为同族改善**（`X为<表达式>` 连写赋值尾被正确切分，见第五节） |
| 互举反跑（677 .light） | **0 新增解析失败**（词法失败 0；语法失败 2 为基线内） |
| 行尾 | 3 文件全 CRLF、0 bare LF |

**任务1 完成**：20 条红全部转绿，文件级零新增红，token A/B 差异经逐条取证全部为同族改善。

---

## 二、1A · L-174 变体（6 条：`为`+表达式 无空格被嵌入块吞并）

### 2.1 修复前后对照

| 红 | 源码 | 修复前 tokens | 修复后 tokens |
|---|---|---|---|
| `test_parser.py::test_arithmetic_expression` | `设结果为甲加乙。` | `设` + `结果为甲加乙` + `。` | `设` `结` `果`→`结果` `为` `甲` `加` `乙` `。` |
| `test_parser.py::test_nested_expression` | `设结果为甲加乙乘丙。` | `设` + `结果为甲加乙乘丙` | `设` `结果` `为` `甲` `加` `乙` `乘` `丙` `。` |
| `test_parser.py::test_function_with_body` | 块内 `设结果为甲加乙。` | 同上 | 同上 |
| `test_parser.py::test_call_in_expression` | `设结果为段落计算(甲，乙)。` | **`设结果为段落计算`** + `(` … | `设` `结果` `为` `段落计算` `(` `甲` `，` `乙` `)` `。` |
| `_test_null_safety.py::test_unwrap_on_nullable_variable` | `设值为空。设值2为值!。` | `设`+**`设值2`**+`为`+`值`+`!` | `设` `值` `为` `空` `。` `设` `值2` `为` `值` `!` `。` |
| `_test_null_safety.py::test_operation_without_unwrap` | `设值为空。设结果为值加1。` | `设` + `结果为值加1` | `设` `结果` `为` `值` `加` `1` `。` |

### 2.2 机制（实测取证）

R58 的 L-174 修复只覆盖 `为` 后跟**值字面量/中文数字**（`设甲为三`）。变体是 `为` 后跟**表达式**（`为甲加乙` / `为值` / `为段落计算(...)`），三类子机制：

1. **`为` 后跟汉字标识符 → 嵌入块整串合并**（`设结果为甲加乙` → `设` + `结果为甲加乙`）。
   `为` ∈ `_EMBED_MAX_MATCH_KEYWORDS`，R58 的切分条件只认 `_after ∈ {空,真,假}` 或中文数字，
   `_after = 甲` 时落入 `_emb_hit = True` 整串合并。
2. **函数调用语境 `_emb_iscall` 无条件合并**（`设结果为段落计算(甲，乙)`：整串后紧随 `(`，
   连 `设` 一起并成 IDENTIFIER(设结果为段落计算)）。
3. **同行 `。` 之后第二条语句不在「语句起始」**（`_at_statement_start` 只认 `\n\r:：`，不认 `。`）
   → `设值2…` 被 R21「关键字前缀标识符整体成词」并成 IDENTIFIER(设值2)，变量名凭空多一个 `设`。

### 2.3 改动点（`src/lexer.py`，+47/-4）

| # | 位置 | 改动 |
|---|---|---|
| 1 | `_at_statement_start`（:1788） | 语句起始判据**新增 `。`**（`'\n\r:：'` → `'\n\r:：。'`）。`。` 是光明语句终止符，同行多语句的第二条本就该按语句起始切分。**不影响**带空格的 `设 设备名 为 1`（其名字前的非空白是 `设`） |
| 2 | 嵌入块头触发（:2363） | `_emb_head_trigger` 增加 `or _emb_head_kw == '设'`：`设` 是声明语句关键字，词首命中即不被嵌入块整串合并。与既有 `设备`→`设`+`备` 切法口径一致 |
| 3 | 嵌入块 `_ek=='为'` 分支（:2394-2439） | 新增 `_assign_tail` 判据，并把 `_emb_iscall` 合并改为「`_assign_tail` 时不合并」：`为` 后随**汉字**（非值字面量）+ 与前一字**粘连** + 未被更长关键字跨越 ⇒ 把 `为` 交还关键字、前缀独立成词 |

`_assign_tail` 判据（四者同时成立，防误伤）：
```python
_assign_tail = (_ek == '为' and _glued_to_prev                       # ② 连写（设X为…）
                and bool(_after) and _is_han(_after)                 # ① 为后随汉字
                and _after not in _emb_value_heads                   # ④ 非值字面量（断言为真(…) 不变）
                and not self._emb_keyword_spanning(source, pos, _ep)) # ③ 未被更长关键字跨越（因为… 不变）
```

---

## 三、1B · codegen 粘连 `己X`/`自X` 读取位不展开（14 条）

### 3.1 机制（实测取证）

词法层把 `己姓名` 整词成单个 IDENTIFIER（`己`/`自` 是高频构词字，**不升保留字**）。写入位
`己姓名 为 姓名` 由编译器/SelfAssignment 通路正确落成 `self.姓名 = 姓名`；**读取位**（实参/
返回/表达式）此前**无任何一层展开** → 运行期 `name '己姓名' is not defined`。

实证（`LightCompiler().compile` + 对应后端产物）：
```
# 修复前（unified，tests/integration/test_class_system.py 口径）
class 人:
    def __init__(self, 姓名, 年龄):
        self.姓名 = 姓名        # 写入位正确
    def 介绍(self):
        print(己姓名)           # ← 读取位泄漏 → NameError
# 修复后
    def 介绍(self):
        print(self.姓名)        # ✓
```

### 3.2 后端归属（14 条）

| 后端 | 条数 | 测试 |
|---|---|---|
| **src**（`PythonCodeGenerator`） | 9 | `test_context_manager.py` 4（继承链可用 / chao×3）、`test_level6_types.py` 1、`test_edge_cases.py` 1、`test_frontend_blockers_run.py` 3（a24×2 / a25，经 `cli.light_unified` src 腿） |
| **unified**（`UnifiedCodeGenerator`） | 5 | `tests/integration/test_class_system.py` 5 |

### 3.3 改动点（+102/-6）

**`src/code_generator.py::_resolve_identifier_name`（:4342）**：在既有 `己/自 → self`、`己.attr → self.attr`
分支后，新增**粘连前缀读取位展开**：`_in_class_method` 且 `name.startswith('己'|'自')` 且
`剩余部分 ∈ _class_attr_names` ⇒ 发射 `self.<剩余>`。`_class_attr_names` 既有（由 `_generate_class_definition`
从 `stmt.attributes` 收集），无需新增。

**`src/code_generator_unified.py`**（unified 后端**原本没有** `_class_attr_names`）：
- `__init__`（:58）：新增 `self._class_attr_names: set = set()`。
- `_resolve_name`（:615）：新增同款粘连前缀展开分支。
- `_generate_class`（:1536）：开头**存档 + 按类作用域收集**本类属性名，末尾还原
  （保证嵌套类互不污染）。
- 新增 `_collect_class_attr_names(cls)`（:628）：来源 ① 声明式属性 `属性 X`（v2 `fields` / v3
  `attributes`）；② 构造/方法体内 `己X 为 …`（编译器可能已落成 `Assignment(Identifier('self.X'))`
  或未展开的 `SelfAssignment(attr_name=X)`）；沿 MRO 收集 `__slots__` 递归遍历方法体。

---

## 四、验证证据

### 4.1 本机（light-merge venv，py3.13）
```
20 条目标 + 关联：24 passed, 468 deselected  (rc=0)
7 文件全量：14 failed, 478 passed in 349s
  → 14 条 = 基线内红（task2 6 条 + task4 8 条），逐条比对 133701 基线，0 新增
```

### 4.2 0.82 定向（远端 /tmp/r44-20260918-145026，py3.12）
```
cd <远端>/light-merge && /usr/local/bin/python3.12 -m pytest <7 文件> -q --tb=line -rfE -o addopts= -p no:cacheprovider
→ 14 failed, 478 passed in 56.45s（与本机逐条一致）
```
14 条失败清单（**全部在基线 64 红内**）：
`_test_null_safety.py` 2（test_paragraph_call / test_func_non_nullable_param_with_nullable_arg，task4）
＋ `test_frontend_blockers_run.py` 5（异步修饰符当值用，task4）
＋ `test_context_manager.py` 7（await_chained_member / 自_param_and_body_both_self / 为搭配函数调用 / 自之属性赋值 / 自之属性带索引赋值 / 普通标识符之成员赋值 / 点号成员赋值未被破坏，task2）

### 4.3 互举反跑（677 .light）
```
可解析 675 ｜ 词法失败 0 ｜ 语法失败 2（基线内）｜ 读取失败 0
对比：新增失败 0 ｜ 基线内仍失败 2 ｜ 已修复 2   →  ✅ 绿
```

### 4.4 全语料 token A/B（38091 文件）
判据「除 main.light 外逐字节一致」的**实测偏差**（见第五节）：3 个文件变化，全部为同族改善。
> 注：R58 基线已含 L-174 基础型修复，故 `examples/modules/main.light` **本轮不再差异**（其改善已在 R58 落地）。

---

## 五、token A/B 偏差说明（3 文件，逐条取证为同族改善）

| 文件 | 修复前 | 修复后 | 判定 |
|---|---|---|---|
| `bootstrap/release/stdlib/字符串处理.light` | `IDENTIFIER(设格式化为百分比)` | `设` `格式化` `为` `百分比` | 同族（`设X为<表达式>` 连写赋值尾）；修复前 `设`+`为` 全丢失 |
| `examples/basic.light` | `结果为甲加乙乘2` / `设和为加法` / `设阶乘结果为阶乘` / `计数为计数加1` | 各自切分为 `X` `为` `表达式` | 同族；均为 1A 目标缺陷的语料实例 |
| `examples/hello.light` | `和为和加i` | `和` `为` `和` `加` `i` | 同族；**正是 lexer.py:2877 注释里登记的已知缺陷**（产物 `和 = 和加i` → NameError） |

**证据链**：`tests/unit/test_examples_run.py::test_all_examples_output` 的失败内容已由
「hello.light 行18 **期望'为'或'等于'**」（L-174 症状）变为「hello.light **name 'n乘阶乘' is not defined**」
（紧凑运算符 `n乘阶乘` 并入，属任务4 归因的 R60 范畴）——即 **L-174 症状确已消除**，
与任务书第七节 task4 预测「预计任务1 修 L-174 变体后 hello.light 部分转绿」一致。

> ⚠️ **纪律偏差声明**（据此报告请主 agent 裁定）：任务书 1A 红线写「仅 main.light 允许差异」，
> 因 R58 基线已修 main.light，本轮实测差异转移到 3 个**同族语料文件**。经逐条 token 取证，
> 3 处均是把「无空格 `X为<表达式>`」从错误的整串/丢字切分纠正为正确切分，**无任何反向或无关变化**。

---

## 六、改动文件清单（3 文件，显式列出）

```
light-merge/src/lexer.py                   (+47 -4)   R59 任务1 1A：L-174 变体（含 `。` 语句起始、`设` 头触发、_assign_tail）
light-merge/src/code_generator.py          (+12)      R59 任务1 1B：src 后端 `己X`/`自X` 读取位展开
light-merge/src/code_generator_unified.py  (+90 -2)   R59 任务1 1B：unified 后端 `_class_attr_names` 收集 + 读取位展开
```
行尾：3 文件全 CRLF、0 bare LF。**未 commit**（外发 agent 只改文件 + 验证，合流归主 agent/路M）。

探针/中间产物（待任务5 移档 → `lightharness/docs/历史存档/R59探针/`）：
`lightharness/_r59_probe1.py` / `_r59_probe2.py` / `_r59_probe3.py` / `_r59_scan_weimid.py` /
`_r59_dump_tokens.py` / `_r59_lexer_base.py`（= git HEAD R58 版）/ `_r59_tok_base.tsv` / `_r59_tok_new2.tsv` /
`_r59_反跑.json` / `_r59_反跑.txt`。

---

## 七、风险与说明

1. **token A/B 3 文件偏差**：见第五节，全部同族改善，已给逐条 before/after 与 examples 测试证据；
   是否接受由主 agent 依门判据裁定。
2. **`。` 纳入语句起始**：语义正确且与 `\n`/`:` 同口径；已 A/B 证明除 3 个目标文件外零波及。
3. **`_assign_tail` 防误伤**：靠 `_glued_to_prev` + `_after ∈ 汉字` + `not _after ∈ {空,真,假}` +
   `_emb_keyword_spanning` 四重收窄；已实测 `设 是否为零 为 假` / `断言为真(甲)` / `因为百分数` /
   `设 匹配度 为 1` / `设备` / `设计模式` 全部维持原行为。
4. **unified `_class_attr_names` 为新增状态**：只在 `_generate_class` 内存档/还原，
   嵌套类不互相污染；`_collect_class_attr_names` 遍历沿 MRO 取 slots，深度上限 40 + visited 集防环。
5. **未动项**：`tests/` 未改（本轮无需改测试）；`examples/harness/评测报告.md` 未动。
6. **file 级零新增红**已在本机 + 0.82 双侧核对；**整轮唯一全量**（路M）由主 agent 跑。
