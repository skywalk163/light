# 任务2 R59 —— L-096 helper 测试期望更新（21 条）

> 日期：2026-09-18 ｜ 轮次：R59 ｜ 性质：**只改测试断言，不改 codegen**
> 前置：任务1（词法 L-174 变体 + codegen 粘连修复）已落地（工作树 `src/` 三文件未提交改动 + `_task1_R59_词法与codegen修复.md` 在位）
> 背景：L-096（E批次）有意把纯属性访问/成员赋值统一发射为 `_light_attr_get/_light_attr_set`（code_generator.py:1329-1344 定义、1687-1693 赋值分支、3819-3822 访问分支），类实例走 getattr/setattr，与旧直发点号**运行期语义等价**，仅产物文本形态变化 → 21 条断言过时，改断言即可。

---

## 一、结果总账

| 验证 | 结果 |
|---|---|
| 本机定向（4 文件，`-o addopts=`，Windows py host） | 改前 **21 failed / 194 passed** → 改后 **215 passed, 0 failed** |
| 0.82 定向（副本 `/tmp/r44-20260918-145026`，py3.12，同模板 `-o addopts=`） | **215 passed, 0 failed**，`__RC__=0`（退出码自证，未接 tail） |
| 文件内零新增红 | ✅（两侧一致；改前 194 条绿的用例改后仍全绿） |
| codegen 源码 | **0 diff**（本任务只动 tests/） |

留痕（已移档 `lightharness/docs/历史存档/R59探针/`）：`_r59_task2_本机改前.log` / `_r59_task2_本机改后.log` / `_r59_task2_082定向.log` / `_r59_t2_probe*.py`（产物形态取证脚本，已自 light-merge 根移出）。

## 二、改动文件清单（4 文件，显式列出）

```
light-merge/tests/unit/test_v35_chained_call.py   （9 条断言更新）
light-merge/tests/unit/test_v34_syntax_sugar.py   （4 条断言更新）
light-merge/tests/test_context_manager.py         （7 条断言更新）
light-merge/tests/test_async_class_method.py      （1 条断言更新）
```

每处断言更新均在测试 docstring 或行内注明「L-096 helper 形态（R59 更新）」；所有断言文本先经只读编译冒烟取证（任务1 落地后的当前产物），非照抄 R58 归因。**未 commit**（合流归主 agent/路M）。

## 三、逐条断言变更前后对比（21 条）

### 3.1 tests/unit/test_v35_chained_call.py（9 条，产物文本均冒烟实证）

| # | 用例 | 改前断言 | 改后断言 |
|---|---|---|---|
| 1 | test_dot_member_access | `'p.x' in py` | `"_light_attr_get(p, 'x')" in py` |
| 2 | test_mixed_period_and_dot | `'p.x' in py` | `"_light_attr_get(p, 'x')" in py` |
| 3 | test_no_period_no_dot_ambiguity | `'p.x = 3' in py` + `'p.y' in py` | `"_light_attr_set(p, 'x', 3)" in py` + `"_light_attr_set(p, 'y', (_light_attr_get(p, 'x') + 1))" in py` |
| 4 | test_period_in_class_body | `'self.x' in py` | `"_light_attr_get(self, 'x')" in py` |
| 5 | test_dot_access_after_new_keyword | `'a.x' in py` | `"_light_attr_get(a, 'x')" in py` |
| 6 | test_two_level_attr_assign | `'b.a.x = 42' in py or '.x = 42' in py` | `"_light_attr_set(_light_attr_get(b, 'a'), 'x', 42)" in py` |
| 7 | test_self_chain_assign | `'self.inner.val' in py or '.inner.val' in py` | `"_light_attr_set(_light_attr_get(self, 'inner'), 'val', v)" in py` |
| 8 | test_three_level_attr_assign | `'a.b.c.val = 99' in py or '.val = 99' in py` | `"_light_attr_set(_light_attr_get(_light_attr_get(a, 'b'), 'c'), 'val', 99)" in py` |
| 9 | test_attr_assign_with_expr | `'a.x = ' in py` + `'10 + 20' in py or '30' in py` | `"_light_attr_set(a, 'x', (10 + 20))" in py` + `'10 + 20' in py`（去掉 `or '30'` 宽松分支，表达式原样发射） |

### 3.2 tests/unit/test_v34_syntax_sugar.py（4 条）

| # | 用例 | 改前 | 改后 |
|---|---|---|---|
| 10 | test_self_attr_eq | `'self.x = 1' in py` | `"_light_attr_set(self, 'x', 1)" in py` |
| 11 | test_self_attr_等于 | `'self.x == 1' in py or 'self.x = 1' in py` | 仅保留 `"_light_attr_set(self, 'x', 1)" in py`（**删除 `==` 备选**：「等于」在语句位是赋值非比较，实测两形态产物同为 helper 赋值） |
| 12 | test_obj_attr_eq | `'p.x = 10' in py` | `"_light_attr_set(p, 'x', 10)" in py` |
| 13 | test_dot_access_still_works | `'p.x' in py` | `"_light_attr_get(p, 'x')" in py` |

### 3.3 tests/test_context_manager.py（7 条）

| # | 用例 | 改前 | 改后 |
|---|---|---|---|
| 14 | TestL2OOPCodegen::test_自_param_and_body_both_self | `'self.姓名 = 姓名' in code` | `"_light_attr_set(self, '姓名', 姓名)" in code`（`def __init__(self, self` 不出现的护栏与 exec 行为断言原样保留） |
| 15 | TestAwaitMemberAccess::test_await_chained_member | `'await 甲.乙.丙()' in result` | `"await _light_attr_get(甲, '乙').丙()" in result`（方法调用 `.丙()` 仍直发） |
| 16 | TestJueyiE遍历为连接词::test_为搭配函数调用 | `'==' not in result` | **断言收窄**：`'in range(1, 10) ==' not in result`——原断言被产物头部运行时预置（内置 lambda 表，如『是负零』的 `v == 0.0`）合法 `==` 误伤；「为 不被吞成 ==」的语义防线收窄到循环行，codegen 未动 |
| 17 | TestJueyiOOP成员赋值目标::test_自之属性赋值 | `'self.姓名 = 姓名' in result` | `"_light_attr_set(self, '姓名', 姓名)" in result`（`self.之姓名` 不出现的反断言保留） |
| 18 | 同::test_自之属性带索引赋值 | `'self.成绩[科目] = 分数' in result` | `"_light_attr_get(self, '成绩')[科目] = 分数" in result` |
| 19 | 同::test_普通标识符之成员赋值 | `'obj.字段 = 1' in result` | `"_light_attr_set(obj, '字段', 1)" in result` |
| 20 | 同::test_点号成员赋值未被破坏 | `'obj.字段 = 1' in result` | `"_light_attr_set(obj, '字段', 1)" in result` |

### 3.4 tests/test_async_class_method.py（1 条）

| # | 用例 | 改前 | 改后 |
|---|---|---|---|
| 21 | TestAsyncClassMethod::test_03_async_method读写己属性 | `"self.值 = (self.值 + 1)" in code or "self.值 = self.值 + 1" in code` | `"_light_attr_set(self, '值', (self.值 + 1))" in code`（`return self.值` 与 exec+asyncio 行为断言原样保留） |

## 四、另立工作项（不修，仅登记）

- `def get(self, self)` 静默错编形状：test_period_in_class_body 等产物中，显式写出的 `self` 形参被收集为普通形参导致重复（`_is_self_param` 判据与部分解析路径形参表对不上时发生）。当前未造成运行期错误（Python 允许同名参数遮蔽?否——此处为 SyntaxError 风险面），按任务书指示**不在本任务修复**，建议 R60 立项核查 `_generate_method` 形参去重链路。

## 五、风险与说明

1. **只动断言不动行为**：21 条中的 exec/运行期行为断言（如 test_03 的 asyncio 执行、test_自_param_and_body_both_self 的实例行为）全部原样保留，本任务零语义弱化；唯二收紧点：#9 删掉 `or '30'`、#11 删掉 `==` 备选，均是向「语义正确」方向收紧，实测仍绿。
2. **断言文本取证**：全部以任务1 落地后的当前产物为准（冒烟脚本 `_r59_t2_probe*.py`，已随探针存档），非沿用 R58 归因文本；两侧（本机/0.82）产物一致。
3. **互涉确认**：任务1 的粘连 `己X` 读取位展开不影响本批 21 条（均为带点/普通对象形态），实测 215 条全绿即证。
4. **未动项**：`src/` 零改动；`tests/_temp_cbackend/`（任务书「不要动」清单）未触碰；`test_pure_light_hook` 相关未路过。
5. 探针/中间产物已自 light-merge 根移至 `lightharness/docs/历史存档/R59探针/`，light-merge 工作树只余本任务 4 个 tests 文件 + 任务1 的 3 个 src 文件改动。
