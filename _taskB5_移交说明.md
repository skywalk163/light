# B5 路移交说明 — 语言核心四补

分支：task-B5 | 基线：1ff86237 | 工作目录：wt-B5

## 四补完成状态

### B5-1 一等函数值 + 多语句 lambda ✅
- 函数可当值传递（赋给变量、做实参、做返回值）
- lambda 支持多语句体（生成命名函数 `_light_lambda_N`），不再限单表达式
- 改动文件：parser_expr.py, ast_nodes.py, ast_nodes_v3.py, code_generator.py
- 测试：test_frontend_blockers_run.py（61 passed）、test_modern_features.py

### B5-2 推迟（defer）FILO 延迟栈语义 ✅
- `推迟` 关键字从 0 命中落地到主链路 code_generator.py
- 语义：推迟体在作用域退出时执行（FILO 栈序），包括提前 return 和异常路径
- 旧 unified 链路的内联语义（try-body-pass / finally-就地执行）已废弃，改为与主链路一致
- 旧 test_async.py:133-155 断言已改（`['开始','推迟执行','结束']` → `['开始','结束','推迟执行']`）
- 改动文件：keywords.py, lexer.py, parser_stmt.py, code_generator.py, code_generator_unified.py, tests/test_async.py
- 行为测试 7 项：基本顺序 / FILO 多 defer / early return / 异常路径 / 块形式（主链路+unified 各覆盖）
- 反跑证明：`reversed(_light_defers)` → `_light_defers`（FIFO 损坏），FILO 测试红
- `推迟` 关键字全仓 A/B 扫描通过（0 切词误伤）

### B5-3 异步遍历泛化 ✅
- `异步 遍历` 现在支持普通 list / range / 任何同步可迭代对象
- 实现方式：编译器自动插入 `_light_async_iter` 辅助函数，运行时探测 `__aiter__`
  - 异步生成器走原路 `async for`
  - 普通 list/range 等回退为逐个 yield
- 修复 code_generator_unified.py 完全忽略 `is_async` 的问题
- 改动文件：code_generator.py, code_generator_unified.py
- 行为测试 4 项：普通 list / 异步生成器 / range / 同步遍历不受影响
- 反跑证明：去掉 `_light_async_iter` 包装直接发 `async for`，普通 list 抛 TypeError
- 文档更新：统一语法规范_v3.2.md §8 异步遍历说明

### B5-4 位运算 ✅
- 六个中文中缀位运算符 + 一个一元前缀：
  - `位与`(&) `位或`(|) `位异或`(^) `左移`(<<) `右移`(>>) `位非`(~)
- 优先级链遵循 Python 口径：算术 > 位移 > 位与 > 位异或 > 位或 > 比较
- 改动文件：parser_core.py（BITWISE_*_MAP 映射表 + BITWISE_OP_WORDS）
  - parser_expr.py（四层解析链路 + _parse_primary 中位非识别）
  - code_generator.py（operator_map 中文→Python 符号映射）
  - lexer.py（COMMON_COMPOUND_WORDS 复合词保护）
- 18 个积木库存量文件（blocks/blocks_v4/blocks_v5 各 6 个）全部可编译
  - 实际扫描到 30 个文件（含按位与/按位或/按位异或/按位取反/左移位/右移位变体），全部 OK
- 行为测试 14 项：六种运算各 1-2 个 + 优先级 3 项 + 积木库存量编译验证 2 项
- 反跑证明：去掉 code_generator operator_map 中位运算映射，测试红（SyntaxError）
- 位运算关键字全仓 A/B 扫描通过

## 开工首日两裁决

### 裁决 1：`推迟` 落哪条生成器链路
**裁决**：落主链路 code_generator.py。
原因：主链路 4489 行是实际编译入口，unified 是旧链路。`推迟` 从 keywords→lexer→parser→codegen 全链路新建，
unified 链路同步改造保持一致。旧 test_async.py:133-155 的内联语义断言已改。

### 裁决 2：位或的符号形式
**裁决**：只保留中文词 `位或`，不给符号形式。
原因：
1. `|` 已是管道操作符（tokens.py PIPE），上下文歧义消解代价高
2. 全仓 18+ 个积木文件全部使用中文词形式，无一使用符号
3. 语言一贯用中文词做运算符（加/减/乘/除/大于/小于/等于），`位或` 一致

## 已知遗留（需 A5 订正）

- **stdlib/选择器.light:21-22**：注释写着「不用 位与/位或（该方言里不被当作二元运算符）」，
  现在位运算已落地，该注释变假。该文件归 A5 独占，B5 不碰。请 A5 在合入后订正。

## 例外授权使用

- **stdlib/代理循环.light:411**：过时注释「光明无闭包」已改为「轮次状态以 己.当前轮 属性传递，
  供事件载荷使用。」（删掉「光明无闭包，」前缀）

## 测试统计

| 测试文件 | 通过数 |
|---------|--------|
| tests/test_async.py | 35 passed（含 B5-2 defer 7项 + B5-3 异步遍历 4项） |
| tests/test_frontend_blockers_run.py | 61 passed |
| tests/test_codegen.py | 18 passed |
| tests/test_modern_features.py | 13 passed |
| tests/test_feature_core_light.py | 14 passed（B5-4 位运算） |
| tests/test_core_coverage.py | - |
| tests/test_comprehensive.py | - |
| **合计（核心回归）** | **205 passed, 1 skipped, 0 failed** |

## 假测试门禁扫描

B5 新增测试文件扫描结果：
- tests/test_async.py: 0 违规（唯一 `is not None` 是 pre-existing baseline 行 656/846）
- tests/test_feature_core_light.py: 0 违规

## 交付文件清单

src/: keywords.py, lexer.py, parser_core.py, parser_expr.py, parser_stmt.py,
  ast_nodes.py, ast_nodes_v3.py, code_generator.py, code_generator_unified.py
tests/: test_async.py, test_feature_core_light.py (new)
docs/: 统一语法规范_v3.2.md
stdlib/: 代理循环.light (仅 line 411 注释订正)
