# 5 路并行任务 —— 查收与合入 main 报告

> 时间：2026-09-10 ｜ 基线 main = `5218f618` ｜ 合入后 main = `af10d26a`
> 合并策略：`git merge --no-ff`，全部 `ort` 策略，**零冲突**。

## 一、各路最终落点（合并前已厘清）

| 路 | 内容 | 实际位置 | 处理 |
|---|---|---|---|
| **road-1** 测试环境与健康 | native_leg 绝对路径治 cwd 污染 / import_hook FreeBSD `re` 路径 / R13B HTTPS 默认 skip / doc_block_scan `_SCAN_EXEMPT` / lightpub `ENV_DEPENDENCY` / HTTP客户端.md 围栏 / pack_verify_tar.py | `task-1-测试环境与健康` `4a59f2f0`（上一轮已从 task-3/task-4 摘出归位） | 直接合 |
| **road-2** stdlib 命名与特性 | 数学.light 补齐 排列/黄金比例/双曲/反三角/复数；code_generator 补 自然对数/常用对数/对数2 | `wt-task2` 工作树未提交 → 提交 `4265e81a` 到 `task-2` | 先提交再合 |
| **road-3** 测试方言与对象式 | 参数解析/数据验证/格式化/模板/缓存/进度条/高级文件 命名对齐；phase4/phase13/pure_light_hook 函数式；**混入 road-1 的 6 源码文件（重复）** | `task-3-测试方言修正` `208250b9` | 直接合（重复内容无冲突） |
| **road-4** 原生腿/运行时真 bug | 除法真除（取代 §15.1 裁决B，对齐 T7A）/ 统计 `排序` / llvm c3、optimizer | **真源码不在 task-4 分支**（task-4 只 pack 脚本+报告，与 road-1 重复），混在**主仓未提交改动**里 | 随主仓 road-4+5 提交 `56f19716` 到 `task-5` 一并合 |
| **road-5** 语言语法 L-075~L-078 | lexer 支持 hex(L-075) / 列表 `.移除()` `.弹栈()`(L-077) / codegen_typed+parser_stmt 后端 | 主仓未提交 → 提交 `56f19716` 到 `task-5`（含 road-4 真 bug） | 先提交再合 |

> **task-4 分支跳过**：其 3 个文件（pack_verify_tar.py / dataset_test_report.md / 交付报告）已被 task-1 完全包含，合并为冗余 no-op，故不并入。

## 二、合并提交历史

```
af10d26a merge(road-3): 测试方言与对象式API修正 (含 road-1 源码已先合)
b9633d73 merge(road-4+5): 原生腿真bug修复 + 光明语法缺陷补齐(L-075~L-078)
b8731da8 merge(road-2): stdlib 命名与特性对齐 —— 数学模块补齐
56be2c73 merge(road-1): 测试环境与健康 —— 源码归位
56f19716 feat(road-4+road-5): ...   ← task-5 提交
4265e81a feat(road-2): ...          ← task-2 提交
4a59f2f0 fix(路1): ...              ← task-1 提交
5218f618 chore(地板): ...           ← main 基线
```

## 三、查收验证

- ✅ 工作树无冲突残留、无暂存 tracked 改动（`git status` 干净，仅剩未跟踪的辅助脚本 `_ssh_*.py` 等，不纳入）
- ✅ 合并涉及的 10 个关键 `.py`（`code_generator`/`code_generator_unified`/`lexer`/`codegen_typed`/`parser_stmt` + `tools/lightpub_importability.py` + `stdlib/builtins.py`/`参数解析.py`/`数据验证.py`/`进度条.py`）`py_compile` 全过
- ✅ 唯一被两路改的 `code_generator.py`：road-2（@384 数学路由）与 road-4+5（@166 L-077 / @1024 除法 / @1144 lambda）**区域不重叠 → 干净合并**

## 四、残留缺口（road-5 未收尾，非合并破坏）

`docs/原生腿能力清单.json` 仍只有 `字典移除`/`列表弹出`，**没有 road-5 新增的 `弹栈`/`列表移除`(L-077)**：
- `tests/unit/test_native_leg_capability.py::test_内置函数清单与代码一致` 仍会失败（代码有、清单无）
- 同文件 `test_内置函数证据行号可定位` 是清单与 `codegen_typed.py` 证据行**长期漂移**（非本次引入，road-5 范围外）

> 未擅自改清单 JSON（1750+ 行大文件，需按 schema 精确补 `弹栈`/`列表移除` 并修证据行漂移）。**建议作为 road-5 收尾单独处理**，或确认这两测试是否进 `tests/ci_baseline_failures.txt` 基线。

## 五、后续建议

1. **road-5 收尾**：补 `弹栈`/`列表移除` 入 `原生腿能力清单.json` + `原生腿能力边界.md`（消 native_leg 1 个失败）；证据行漂移另议。
2. **未 push gitea**：本次仅本地合并。推前建议在 0.88 重传最新代码跑全量，CI 回归闸门 `check_regression.py` 只拦基线外新增失败——若 native_leg 两项已在基线则不挡。
3. **工作树清理**：`light-merge_t3`（task-3 工作树）、`wt-task2`（task-2）可保留或 `worktree remove`（勿用 `--force`，避免再次连坐孤儿化）。
