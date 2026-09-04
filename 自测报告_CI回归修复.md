# 自测报告_CI回归修复（883e319c 回归闸门）

**日期**：2026-09-04
**分支 / worktree**：`fix/ci-division` / `G:\dswork\duan-light-merge\wt-CI`（独立 worktree，基线 883e319c）
**提交**：`ff5db4b7` fix(ci): 回归闸门 4 条新增打红——对齐裁决 B 除法语义
**根因提交**：`99580808`（T1，统一「除以」双后端向零截断）+ `883e319c`（裁决 B 后 `//` 独立 floor）

---

## 1. 现象与根因

CI 回归闸门（基线对比，基线 `tests/ci_baseline_failures.txt` 停更于 2026-08-27）在
883e319c 上新增 **4 条硬打红**（`tests.unit.*` 非 soft，闸门拦截）：

| 新增打红 | 根因 |
|---|---|
| `test_c_backend::test_operators_alias` | 光明 `/` 在 Python 腿经 `_light_trunc_div` 包裹，C 后端输出从 `(100 / 4)` 变为 `_light_trunc_div(100, 4)` |
| `test_examples_run::test_all_examples_output` | 3 个示例（student_management / module_demo / bootstrap_eval）用整型 `/` 算均值/计算器除法，被向零截断 |
| `test_light_examples_run::test_division` | `100 除 4` 期望 `25.0`（真除），现得 `25`（截断） |
| `test_地板搬迁_求和_S2::test_平均值仍是求和除长度` | stdlib `列表工具.light` 平均值 `总和 / 长度值` 整型截断，与 CPython `sum()/len()` 逐位不等 |

**共性**：裁决 B（§15.1）把 `/` 定义为「整数相除得整数（向零截断，对齐原生腿 i64
sdiv）」；T1/883e319c 落地后，仍按旧真除语义写死的测试与示例未同步更新，且基线
8 天未刷新，故判「新增」。这是**语义变更后的存量测试对齐欠账，不是新引入的实现回归**。

## 2. 修复（全部对齐裁决 B，未改任何除法语义本身）

1. **c_backend.py `_translate_call`**：`_light_trunc_div(a, b)` 调用映射回原生 C `(a / b)`。
   C 的 `/` 对整数天然向零截断、浮点真除——正是裁决 B 语义，直接发射原生 C 除法，
   避免把 Python 体的 trunc_div helper 原样打成坏 C。`test_operators_alias` 原断言
   `(100 / 4)` 原样通过（无需改测试）。
2. **examples/student_management.light** `平均成绩`：`总分 除 列表长度(...)` →
   `总分 除 转浮点(列表长度(...))`。均值语境需真除，改显式浮点操作数（§15.1 落法），
   输出保持 `84.33333333333333`。
3. **examples/module_demo.light** `平均值`：`求和(...) 除 转浮点(列表长度(...))`，
   输出保持 `3.0`。
4. **examples/bootstrap_eval.light** 求值器除法：`a 除 b` → `a 除 转浮点(b)`，
   输出保持 `8/2+3 = 7.0`、`100/25+7 = 11.0`。
5. **stdlib/列表工具.light** `平均值`：`总和 / 长度值` → `总和 / 转浮点(长度值)`，
   恢复与 CPython `sum()/len()` 逐位等价（int/int 也回 float，符合该函数定位）。
6. **tests/unit/test_light_examples_run.py::test_division**：期望 `25.0` → `25`
   （`100 除 4` 整数截断=25，与双后端一致，与同组 add/sub/mul 全 int 期望一致）。
7. **docs/known_issues.md §15.1**：补「裁决 B 落地后的 CI 对齐」说明。

## 3. 反跑判据验证

原 4 条新增打红逐一显式重跑（wt-CI）：

```
tests/unit/test_c_backend.py::TestCompileToC::test_operators_alias  PASSED
tests/unit/test_examples_run.py::TestExampleFilesRun::test_all_examples_output  PASSED
tests/unit/test_light_examples_run.py::TestVariableAndArithmetic::test_division  PASSED
tests/unit/test_地板搬迁_求和_S2.py::test_平均值仍是求和除长度  PASSED
4 passed, 22 subtests passed in 2.01s
```

## 4. 回归面核对（受影响文件整文件）

| 文件 | 结果 |
|---|---|
| tests/unit/test_c_backend.py（c_backend 改动） | PASS（整文件） |
| tests/unit/test_examples_run.py（3 示例改动） | PASS（整文件，22 示例全绿） |
| tests/unit/test_light_examples_run.py（test_division） | PASS（整文件） |
| tests/unit/test_地板搬迁_求和_S2.py（stdlib 平均值改动） | PASS（整文件，逐位等价全部保持） |
| tests/test_pure_light_hook.py（引用 列表工具） | 68 passed |
| tests/e2e/test_e2e_chain.py | 14 failed——**全部为基线欠账**：demo1_numpy_mean（本机无 numpy，CI 已证绿）+
  E4沙箱/demo3_math/demo2_pandas/demo3_matplotlib/demo5_sklearn/all_in_one（缺
  pandas/matplotlib/sklearn/sympy），与基线文件 12 条吻合；与本改动无关 |

## 5. 未动的部分（如实记录）

- **24 条非阻塞 soft 打红**（`--soft-classname 'tests.test_*'`，只报不拦）未动：多数是
  同源除法语义欠账（divide_assign / complex_arithmetic / binary_div / ternary 等），
  少数与除法无关（TLS 异步腿、harness 指标、metrics 分位等，可能 CI 环境相关）。
  它们不拦闸门；如需全清，应另起任务对齐或刷新基线。
- **`tests/ci_baseline_failures.txt` 未动**（仍 12 条 e2e 环境欠账）。
- **除法语义本身未改**：`/` 整数向零截断、`//` Python floor（裁决 B）保持不变。

## 6. 文件清单（7 个）

`c_backend.py`、`examples/student_management.light`、`examples/module_demo.light`、
`examples/bootstrap_eval.light`、`tests/unit/test_light_examples_run.py`、
`stdlib/列表工具.light`、`docs/known_issues.md`

## 7. 后续动作建议

- 将 `fix/ci-division` 合入 main 后，CI 回归闸门应转绿（4 条硬红已消）。
- 24 条 soft 打红 + e2e 基线欠账是否处理，另议。
