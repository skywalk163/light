# 第57轮 任务1 交付：解析链缺陷修复（lexer.py + code_generator.py）

> 日期：2026-09-18 ｜ 仓库：`light-merge`（HEAD 基线 `3e0de022`）
> 目标（任务书 §四）：4 例 example 红转绿（rc=0）、16 条 `错误` 红转绿，且不引入任何新红。
> 实测结论：**1a 已修（lexer.py 2 处最小改动，零新红、语料仅 4 个目标文件 token 变化）；1b 经路M 全量复核后已修（code_generator.py 类继承基类补异常名映射，16 条全量下转绿），详见文件末尾【第57轮更正】块。**

---

## 0. 一句话结论

| 子项 | 结论 |
|---|---|
| 1a 词法器缺陷（4 例 example 红） | ✅ **已修**：`src/lexer.py` 2 处最小改动；0.82（py3.12）4 例全部 rc=0；`test_回归 -k R22/R26/R27` 由 9 failed → **9 passed**；互举反跑 **0 新增解析失败**（并修复基线内 2 条）；全语料 38084 个 .light 的 token 流**只有 4 个目标文件变化** |
| 1b 16 条 `NameError: name '错误' is not defined` | ⛔ **不可复现，无需改 parser_stmt.py**：0.82 上 `tests/test_stdlib_phase9.py::测试断言工具` **16 passed × 3 轮**；参考基线 `082_lightmerge基线_2026-09-18-072454.json` 中该文件 **0 红**；且 `错误 ∉ VERB_ARITY / STDLIB_VERB_ARITY / ALL_VERB_ARITY`，R54 的两处改动**全部以 `VERB_ARITY` 为键**，结构上不可能影响到 `错误`（§5） |
| 未改动的文件 | `src/parser_stmt.py` **未改**（`git status` 只显示 `M src/lexer.py`）；保护表（CCW/CS/EMBED/OPERATOR_VERBS/_P0A_*）**未动** |

---

## 1. 缺陷确认（根因，实测定位而非推断）

用探针 `_r57_probe_tokens.py` 直接 `Lexer().tokenize(...)` 得到修复前切分：

| 输入 | 修复前 token | 期望 |
|---|---|---|
| `设 为了 为 "为了值"` | `设` + **`为`(KEYWORD) + `了`(IDENTIFIER)** + `为` + STRING | `设` + **`为了`(IDENTIFIER)** + `为` + STRING |
| `段落 测试返回语句:` | `段落` + **`测试` + `返回` + `语句`** + `:` | `段落` + **`测试返回语句`** + `:` |
| `段落 测试真的与返回:` | `段落` + **`测试真的与` + `返回`** + `:` | `段落` + **`测试真的与返回`** + `:` |
| `段落 测试_返回真:` | `段落` + **`测试_` + `返回` + `真`** + `:` | `段落` + **`测试_返回真`** + `:` |

**共同根因**：`src/lexer.py` 的**预扫描 `_scan_user_definitions`** 在登记「用户定义名」时，把名字里的**关键字当成了分隔符**，导致名字被**截断注册**。名字注册不全 → 预扫描白名单失效 → 该名字在正式分词时被关键字边界切开：

- **`段落` 分支**：无空格回退路径把 `接收`/`返回` 都当参数分隔符，于是段名被腰斩：
  `测试返回语句`→注册 `测试`、`测试真的与返回`→注册 `测试真的与`、`测试_返回真`→注册 `测试_`。
- **`设` 分支**：`为` 被视为赋值分隔符，**未加「已收集到名字字符」守卫**，遇到名字首字符就是 `为`（`为了`）时直接 `break`，名字收集为空 → 什么都没登记。

> 为什么 `作为`/`认为`/`成为`/`行为` 不红、只有 `为了` 红：那四个词的`为`不在词首，走**嵌入合并块**（head 非触发字）能整体成词；而 `为了` 的 `为` 在词首，命中 R36 新增的 `_emb_head_trigger` 闸门被挡在嵌入块之外，只能指望预扫描白名单 —— 而白名单恰好空。

**预扫描证据**（探针实测）：

```
'段落 测试返回语句:'      → user_defs = ['测试']          # 应 ['测试返回语句']
'段落 测试_返回真:'       → user_defs = ['测试_']         # 应 ['测试_返回真']
'设 为了 为 "为了值"'     → user_defs = []                 # 应 ['为了']
```

---

## 2. 修复（最小 diff，只动缺陷相关分支）

### 2.1 `_scan_user_definitions` 段落分支：无空格回退只认 `接收`

```diff
                 if _sep_pos == -1:
+                    # R57 任务1（1a）修复：无空格回退路径**只认 `接收`**，不再把 `返回`
+                    # 当作参数分隔符。…（略，见源码注释）
                     _s = j
                     while _s < _header_end:
                         _kw, _kl = self._match_keyword(source, _s)
-                        if _kw and _kl > 0 and _kw in ('接收', '返回'):
+                        if _kw and _kl > 0 and _kw == '接收':
                             _sep_pos = _s
```

理由：`段落 名 接收 参数:` 是唯一的分隔语法，`返回` 从来不是段落头分隔符（带空格的 `返回` 由**清晰分隔符循环**处理，且那一路 R21 已加 `_preceded_ok` 守卫）。
**影响面实测**：扫描全语料（38084 个 .light）中「段名内嵌 `返回`」的段落定义共 11 处，其中 7 处都带清晰分隔符 `接收`（不受本改动影响），**只有 4 处**（即本轮 4 个目标 test 文件）落在本回退路径上。

### 2.2 `_scan_user_definitions` 设分支：`为` 作分隔符须「名字已非空」

```diff
                     lookahead = k
                     while lookahead < n and _is_space_tab(source[lookahead]):
                         lookahead += 1
-                    if lookahead < n and source[lookahead] == '为':
+                    # R57 任务1（1a）修复：`为` 被视为赋值分隔符的前提是**名字已收集到字符**…
+                    if collected_something and lookahead < n and source[lookahead] == '为':
                         break
```

理由：名字首字符就是 `为`（`为了`）时它是名字成分而非分隔符；真正的赋值 `为` 出现在名字已非空之后才 break。

> **总 diff 规模**：`src/lexer.py` 2 hunk / 19 insertions / 2 deletions，全部为「目标词分支」改动，未触碰任何保护表、未重构。

---

## 3. token 流 diff（A/B 全语料对拍，最重要的兜底）

方法：`_r57_dump_tokens.py` 分别加载 **HEAD 版 lexer**（`git show HEAD:src/lexer.py`）与**修复版**，对 `light-merge/` + `lightharness/` 全树 **38084 个 .light** 逐个 tokenize，比对「token 数 + 完整 token 序列 sha1」。

**最终结果：20 行 diff → 仅 4 个文件变化，无任何意外波及。**

| 文件 | token 数（前→后） | 变化 |
|---|---|---|
| `lightharness/examples/test_R22_嵌入关键字冗余验证.light` | 83 → 81 | 2 处整词并入（`为了` ×2） |
| `lightharness/examples/test_R26_词首并入反向.light` | 668 → 664 | `测试返回语句`、`测试_返回语句` 等段名整词 |
| `lightharness/examples/test_R26_词首并入混合.light` | 563 → 561 | 段名整词 |
| `lightharness/examples/test_R27_词首并入反向.light` | 486 → 478 | 段名整词 |

> ⚠️ 过程记录：第一版方案曾尝试「把 `为` 从 `_emb_head_trigger` 剔除」，A/B 发现它会把 `def为真(`（`bootstrap/release/stdlib/断言工具.light`）里的 `为真` 在**函数调用语境**误并成 IDENTIFIER —— 属**意外波及**。据此**改回**，改用上面「预扫描」两处修复，重跑 A/B 后该文件零变化。这正是 A/B 对拍的价值。

---

## 4. 定向验证结果表（0.82 定向；命令取真 rc，不接 `| tail`）

环境：0.82 FreeBSD 15.1 + `/usr/local/bin/python3.12`（带 xdist/pytest-timeout），副本 `/tmp/r57-directed`（= R56 快照 + 本轮 3 个改动文件）。

| # | 验证项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 4 例 example 真 rc（0.82） | `运行.py examples/<名>.light`（`>log 2>&1; echo rc=$?`） | **4/4 `rc=0`** ✅ |
| 1' | 4 例 example 真 rc（本机 py3.13.14） | 同上（lightharness 运行器） | **4/4 `rc=0`** ✅ |
| 2 | token 流 diff | §3 全语料 A/B | 仅 4 个目标文件变化 ✅ |
| 3 | lightharness 词法 token 单测 | `pytest tests/test_R26_词首并入_token.py tests/test_R27_CS表16字词首并入_token.py` | **280 passed / 2 skipped** ✅ |
| 3' | light-merge 词法单测子集 | `pytest tests/unit/test_lexer*.py` | **8 failed / 49 passed** —— 8 条**全部在基线集合内**（见 §6），零新增；且 `test_lexer_performance_10000_lines` 由基线红**转绿** ✅ |
| 3'' | lightharness 例回归 | `pytest tests/test_回归.py -k "R22 or R26 or R27"` | **9 passed**（R56 同口径为 **9 failed**） ✅ |
| 4 | **互举反跑**（词法改动最重要兜底） | `python3.12 scripts/互举反跑.py` | 扫描 **677** 个 .light，可解析 675，失败 2；**新增失败 0**；基线内仍失败 2（`test_L101`/`test_L143`，与本轮无关的存量）；**已修复 2**（`test_R22_嵌入关键字冗余验证`、`test_R26_词首并入混合`）→ **✅ 绿** |

### 4.1 `互举反跑` 明细

```
待检：677 个 .light ｜ 可解析 675 ｜ 词法失败 0 ｜ 语法失败 2
基线：4 条（test_L101 / test_L143 / test_R22_嵌入关键字冗余验证 / test_R26_词首并入混合）
对比：新增失败 0 ｜ 基线内仍失败 2 ｜ 已修复 2
判据：✅ 0 新增解析失败 —— 绿
```

---

## 5. 1b：16 条 `错误` 红 —— 实测不可复现，判为不改 `parser_stmt.py`

任务书 1b 前提：「R54 放宽的『动词作变量名』守卫把关键字构造 `错误` 当普通标识符」。本轮**实测三路证据全部指向该前提不成立**：

1. **定向不可复现（0.82 py3.12）**：`pytest tests/test_stdlib_phase9.py::测试断言工具` → **16 passed，连续 3 轮全绿**（R56 记为 16 红）。
2. **参考基线本就 0 红**：本轮唯一权威基线 `082_lightmerge基线_2026-09-18-072454.json`（7806 用例 / 100 红）中，`test_stdlib_phase9` 出现次数 = **0**。（16 红只出现在更早的 `082_归因_R54_2026-09-18-065044.json` 里，且是「`test_stdlib_phase9/测试断言工具.py::test_*`」这种**并不存在的路径**，实为 `tests/test_stdlib_phase9.py` 中 `class 测试断言工具` 的 16 个方法。）
3. **根因链结构上不成立**：`错误` 的归属实测为 **`VERB_ARITY=False`、`STDLIB_VERB_ARITY=False`、`ALL_VERB_ARITY=False`、`ALL_KEYWORDS=False`**；而 `git show 3e0de022 -- src/parser_stmt.py` 显示 R54 的**两处**改动判定均为 `tok.value in VERB_ARITY` / `_tok0.value in VERB_ARITY`。**守卫以 `VERB_ARITY` 为键，`错误` 不在其中，R54 的改动在结构上触碰不到 `错误`。**

**处置**：不修改 `src/parser_stmt.py`（无失败用例支撑的改动 = 纯风险）。本轮「16 条红转绿」的验收事实成立（它们本就是绿的）；R56 的归因结论建议按其自身「不许臆断归因」铁律作废/降级为「当时该副本的局部状态」。

> 附加核对：`tests/test_stdlib_phase9.py` 的 `测试断言工具` 类 16 个方法导入的是 `from 断言工具 import ...`，模块源码 `stdlib/断言工具.light` 仅在 `类 断言失败异常 继承 错误:` 处用到 `错误`，该处 `错误` 是 IDENTIFIER 经 codegen 的 `exception_name_map` 映射为 `Exception`，与本轮 lexer 改动无交集（A/B 对拍该文件 token **零变化**）。

---

## 6. `tests/unit/test_lexer*.py` 8 条失败 —— 前后对照（零新增）

| 用例 | 基线（072454） | 本轮 | 说明 |
|---|---|---|---|
| `test_lexer_perf.py::test_lexer_performance_10000_lines` | 红（2.54s > 2.0s） | **转绿**（任务2 阈值处置） | 见任务2 交付 |
| `test_lexer_perf.py::test_lexer_correctness_smoke` | 红 | 仍红（基线内） | G5，见 §7 登记 L-174 |
| `test_lexer.py::test_chinese_number` | 红 | 仍红（基线内） | 存量词法债 |
| `test_lexer.py::test_number_prefix_still_split_when_rest_is_keyword` | 红 | 仍红（基线内） | 存量词法债 |
| `test_lexer.py::test_simple_tokenize` | 红 | 仍红（基线内） | 与 G5 同源（`设甲为三`） |
| `test_lexer_correctness_smoke`（并入上） | — | — | — |
| `test_lexer_p0a_deterministic.py`（3 条：六雷区/同构复合词/清空白名单后仍整体成词） | 红 | 仍红（基线内） | `导出事件表`/`外部命令` 应整体成词——**R32 `_P0A_MERGE_WHOLE` 精简后的存量债，与本轮修复面无关**（A/B token 对拍这些串零变化） |
| `test_lexer_compound_safe_alignment.py::test_除类型错误` | 红 | 仍红（基线内） | 存量债 |
| `tests/test_lexer.py::test_basic_keywords`（不在 `tests/unit/` 下） | 红 | 仍红（基线内） | R36「钉现状」与 G5 同源 |

**净效果：0 新增红 + 1 条转绿（性能断言）。**

---

## 7. 缺陷账登记

| 编号 | 缺陷 | 状态 |
|---|---|---|
| **L-173** | **预扫描 `_scan_user_definitions` 把名字内的关键字当分隔符 → 名字被截断注册**，进而分词时该名字被关键字切开。两处：① `段落` 分支无空格回退把 `返回` 当分隔符；② `设` 分支在名字首字符 `为` 处直接 `break`。表现：`设 为了 为 …` 报「期望'为'或'等于'，但得到「了」」；`段落 测试返回语句:` / `测试真的与返回:` / `测试_返回真:` 报 `name '语句'/'真' is not defined` / 「期望 冒号，但得到 返回」 | ✅ **已修（R57）**，复现/回归：`lightharness/examples/test_R22_嵌入关键字冗余验证.light`、`test_R26_词首并入{反向,混合}.light`、`test_R27_词首并入反向.light`（4 例 rc=0） |
| **L-174** | **无空格 `设 X为<中文数字>` 仍被嵌入块整体合并**（`设甲为三` → `设` + `甲为三`，`为` 丢失）→ 与「Level6 无空格分词」冲突。与 `test_lexer_correctness_smoke` / `test_basic_keywords` / `test_simple_tokenize` 同源 | ⛔ **登记未修（R57）**：属嵌入扫描分支，但修复需把中文数字加入 `_emb_value_heads`（`{空,真,假}`），会**扩大语义面**（任何 `X为<中文数字>` 形态的标识符都将被切开）。按任务书「不许为修它扩大改动面」，本轮**只登记不改**，留给专门轮次做全语料 A/B 后再定 |

---

## 8. 交付物

| 文件 | 内容 |
|---|---|
| `light-merge/src/lexer.py` | 2 处最小修复（§2） |
| `light-merge/_task1_R57_解析链修复.md` | 本文件 |
| 探针（待任务5 移档 → `lightharness/docs/历史存档/R57探针/`） | `_r57_probe_tokens.py`（切分探针）、`_r57_dump_tokens.py`（全语料 A/B token 转储）、`_r57_cmp_one.py`（单文件 token diff）、`_r57_082.py`（0.82 远端执行助手）、`_r57_lexer_base.py`（HEAD 版 lexer 快照） |
| 0.82 临时副本 | `/tmp/r57-directed`（与本轮改动文件一致；非交付物） |

## 9. 遗留 / 建议

1. **L-174** 待专门轮次处置（需全语料 A/B + 语义评审）。
2. `tests/unit/test_lexer_p0a_deterministic.py` 3 条（`导出事件表`/`外部命令` 应整体成词）为 R32 精简后的存量债，建议单独立项画像。
3. 复现用例目前只落在 `lightharness/examples/`（不进全量 `tests/` 收集）——按 R56 建议，应由**任务3** 把它们同步挂进 `tests/`。

---

## 10. 【第57轮更正】1b 结论翻转：16 条 `错误` 红为真，已由 code_generator.py 修复（路M 复核）

> §5 原判「16 条红不可复现、不改 parser_stmt.py」**基于定向跑**，被路M 首次全量证伪——**定向跑不触发生成路径，全量下 16 条真实存在**。本更正块记录翻转与修复；§5 原文保留不篡改。

### 10.1 翻转证据链（路M 首跑 092604）

1. **全量（0.82 py3.12 fast）16 条红复现**：`tests/test_stdlib_phase9.py::测试断言工具::test_*` 16 条 `NameError: name '错误' is not defined`（与 R56 归因一致）。
2. **本机 9 秒定向复现**：`pytest tests/test_bootstrap_light.py tests/test_stdlib_phase9.py` → 16 failed；单跑 phase9 → 全绿。**机制实锤**：
   - `test_bootstrap_light.py` 顶层 `_light_import_hook.install([_STDLIB])` 装钩子（全量/组合跑时先导入即生效；定向单跑 phase9 时钩子未装）；
   - `stdlib/断言工具.light` 首行含「纯光明实现」魔数 → 钩子**接管编译并忽略同名 .py**（`_light_import_hook.py:250-253`）；
   - 编译产物 `class 断言失败异常(错误):` ——**类继承基类名没走 `exception_name_map`**（`_resolve_exception_type` 只服务 try/except），`错误` 裸用 → 运行期 NameError。
   - 并行/串行差异：py3.12 xdist 下 phase9 所在 worker 是否导入过 bootstrap 是随机的 → R56 各轮红绿抖动（072454 恰好绿、其余 5 轮红）的根因即此。
3. **R56 归因维持**：R54 后的行为差异与 parser_stmt 无关（R54 diff 两处均以 VERB_ARITY 为键、`错误 ∉ VERB_ARITY`）；真实触发面是「钩子 + codegen 类基类不映射」这一组合，R53 回退轮（065044）恰好未触发（副本/顺序差异）。**归因标注**：#195 原文写「R54 引入 16 条新红」——本轮修正为「16 条红在 R54 后存在（触发条件=钩子装载 + 全量环境），修复落在 codegen 而非 parser_stmt」。

### 10.2 修复（`src/code_generator.py`，1 处逻辑 + 注释）

`_generate_class_definition` 的类基类拼接补异常名映射：

```diff
-            bases = ', '.join(b if b.startswith('Generic[') else self._sanitize_name(b)
-                              for b in all_bases)
+            bases = ', '.join(
+                b if b.startswith('Generic[')
+                else self._resolve_exception_type(self._sanitize_name(b))
+                for b in all_bases)
```

- `继承 错误` → `class X(Exception):`（exception_name_map 18 键全部生效；非异常名基类不在 map/builtins → 原样，行为不变；Generic[T] 完整表达式跳过）。
- 修复前「继承中文异常名」的类编译产物必 NameError（Python 无中文异常类），故修复是**纯改进**，无既有用例依赖旧行为。

### 10.3 验证

| 项 | 结果 |
|---|---|
| 本机复现脚本（install 钩子 → import 断言工具） | ✅ 成功，`断言失败异常 MRO = [断言失败异常, Exception, BaseException, object]` |
| 本机组合 pytest（bootstrap + phase9） | ✅ 16 条转绿（组合跑无 phase9 失败；剩余 16 failed 为基线存量：phase3 网络 4 + class_system 5 等） |
| `python -m py_compile code_generator.py` | ✅ 通过 |
| **0.82 全量终跑（100010）** | ✅ **99 红（无 phase9 16 条）；与真基线 072454 对拍：新增红 0、已修复 1（perf）、持平 99** |

### 10.4 缺陷账更新

- **L-175（新登记，R57 已修）**：codegen 类定义基类名未走 `exception_name_map` → `继承 错误` 编译成 `class X(错误):`，纯光明 stdlib 经 `_light_import_hook` 加载时运行期 NameError（phase9 16 条）。修复：类基类经 `_resolve_exception_type` 映射。
- **L-173**（lexer 预扫描）状态不变：已修。
- **L-174**（设甲为三）状态不变：登记未修。
