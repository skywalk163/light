# 工作包 B：测试 / CI / 工具链质量 —— 去重、提速、门禁治理

> 分发给 **Agent B** 的独立任务书。本文件自包含，不依赖总纲以外的其他文件；与总纲冲突处以此文件为准。
> **声明**：使用性能优化流程——**无测量，不结论；无同合同证据，不授权。**
> 本包是质量工程 + 可测量性能优化：所有「更快 / 更少 / 更干净」的结论必须有同机同输入的基线对比，禁止凭印象。

---

## 1. 目标

把测试体系与工程基建从「逐轮累积态」整理成「按层组织、无重复、门禁可信、全量回归可控」的状态：
- 测试文件去重重构（不改变被测代码 `src/**` 的行为，也不改变断言意图）。
- 测试目录结构规范化，与 `pyproject.toml` 的 testpaths 对齐。
- 全量回归时间可测量、可治理（建立基线 → 找出最慢 → 单变量优化 → 回归守卫）。
- CI 存量红基线治理（不靠本机装库转绿）。
- `tools/` 一次性脚本归档，保留权威工具链。

---

## 2. 文件所有权

- **写（唯一所有权）**：
  - `tests/**`（含 unit / integration / e2e / archive / level9_project / 根级 200+ 测试文件）
  - `tools/**`（含 `tools/ci/*`、`tools/ai_copilot/*`、`tools/repl*.py` 等）
  - `benchmarks/**`
  - `.github/workflows/**`、`.gitea/workflows/**`
  - `pyproject.toml`（pytest / coverage / flake8 / 打包配置）、`.flake8`
- **只读（验证用，禁止改动）**：`src/**`、`cli/**`、`stdlib/**`、`积木库/**`、`docs/**`
- **协调约束**：`pyproject.toml` 的 `setuptools.packages.find.exclude` 若需按 Agent A 的交付建议调整，
  由主线合并时统一写入，B 不在本包内自行增删 A 相关排除项。

---

## 3. 现状证据（2026-08-28 已核实）

### 3.1 规模与结构
- `tests/` 280 个文件，约 72,306 行；子目录 `unit` / `integration` / `e2e` / `archive` / `level9_project`，
  另有 200+ 个测试文件直接堆在 `tests/` 根级。
- `pyproject.toml` 已配置 `testpaths=["tests"]`、`addopts="--tb=short --durations=15 --ignore=tests/archive"`、
  `norecursedirs=["archive","__pycache__"]`；注释声明全量约 3800 条用例。
- CI 快照（`tests/ci_baseline_failures.txt`）：`collected=1203 failures=12 errors=0 skipped=55`；
  12 条红中含 6 条依赖三方库（numpy/pandas/matplotlib/sklearn/sympy）的存量欠账，判据为「只有 CI run 实证转绿才允许下线」。

### 3.2 重复/重叠测试族（去重候选，先做断言与引用分析再合并）
- `test_stdlib_phase2.py` … `test_stdlib_phase13.py`（12 个逐轮累积文件）+ `test_stdlib_complete.py`、`test_stdlib_comprehensive.py`
- `test_comprehensive.py` / `test_comprehensive_v2.py` / `test_core_coverage.py` / `test_e2e_full_coverage.py`
- LLVM 族：`test_llvm_*.py`（13+ 个，如 test_llvm_async/optimization/optimizer/net/tls/exception…）
- FFI 族：`test_ffi*.py`（7+ 个：test_ffi/at_c/phase2/phase3/phase4/stdlib_mock）
- 自举族：`test_self_host.py` / `test_self_host_bootstrap.py` / `test_bootstrap_light.py`
- 其它：`test_light_stdlib.py` / `test_light_stdlib2.py`、`test_stdlib_third_party.py` 等

### 3.3 已知质量/性能问题
- **timing 敏感用例**（协作规程 §0 已记载）：`L1_baihua/10_引Python画笑脸.light` 靠 120s 子进程超时判死；
  socket 用例、进程超时用例同样对机器负载敏感 → 多路并行必造假红，也是全量回归不稳定的主因之一。
- 全量 3800 条用例在 `--durations=15` 下每轮自报最慢 15 条，但尚无跨轮存档基线（本轮应建立）。

### 3.4 工具链（tools/ 138 文件 45,506 行）
- **权威质量脚本**（保留并文档化）：`tools/ci/check_regression.py`、`assert_quality.py`、`bootstrap_rate.py`、
  `dist_criteria.py`、`floor_bootstrap.py`、`gen_doc_examples_baseline.py`、`native_product.py`、
  `python_direct_calls.py`、`run_with_memory_cap.py`、`spec_coverage.py`、`time_budget.py`
- **一次性/实验脚本**（归档候选，先确认无 CI/文档引用）：
  - `tools/ai_copilot/`：`_fix_duplicates.py`、`_fix_keywords.py`、`_fix_last1/4.py`、`_fix_new_entries(_v2).py`、
    `_fix_pass3.py`、`_fix_recovered(_v2,_v3).py`、`_audit_dataset.py`、`_deep_audit.py`、`_quick_verify.py`、
    `diagnose_gguf(2,3).py`、`build_sft_dataset(_v10,_v12).py`、`merge_and_convert.py`、`merge_v10.py`、
    `train_cpu_lora.py`、`train_gpu_lora.py`、`train_lora_7b.py`、`train_sft.py`、`recover_6_file_entries.py`、`recover_file_entries.py`
  - `tools/repl.py` 与 `tools/repl_v3.py` 重复（`src/repl/` 才是权威 REPL，tools 两份需裁决归档）
- **CI 工作流**：`.github/workflows/{ci,quality-gate,eval,docs,deploy-docs,docs-deploy,release,vsce-publish}.yml`、`.gitea/workflows/ci.yml`

---

## 4. 任务清单（每项必须带反跑判据）

| # | 任务 | 反跑判据（改哪一行立红 → 复位绿） | 边界 |
|---|---|---|---|
| B1 | **建立测试基线**（无测量不结论）：独占环境跑一次全量 pytest，记录总耗时、`--durations=15` 最慢 15 条、按目录/文件统计耗时、timing 敏感用例清单，存档为 `_taskOptB_baseline.md` | 基线报告与本机复跑数值一致（±10%）；记录不准不算基线 | 只测量不改码 |
| B2 | **测试文件去重**：对 §3.2 各重复族先做「断言/覆盖/引用」分析，合并到按模块组织的单一文件（如 `test_stdlib.py` 覆盖 phase2~13），删除冗余副本；不改变断言意图 | 合并后全量 `collected` 数下降（重复断言减少）且 `passed` 不减；revert 合并后测试仍全绿 | 不改 `src/**` |
| B3 | **目录结构规范化**：把 `tests/` 根级 200+ 文件按 unit / integration / e2e 归位（conftest 与 import 路径兼容处理），与 `pyproject.toml` testpaths 对齐；`tests/archive/` 收编过期用例 | 归位后 `pytest tests/unit` 等各子集可独立运行；revert 后照旧 | 不重写用例逻辑 |
| B4 | **全量回归提速**：基于 B1 基线做单变量优化——慢用例标 `timeout`/降级、`pytest-xdist` 可行性评估（注意 timing 敏感用例的并行隔离）、CI 分段（unit 快段 / e2e 慢段）、缓存与过滤；**每项优化独立 commit + 同合同 A/B 测量** | 优化后同机同输入全量耗时较基线下降（量化 X%）；回滚优化项耗时回到基线 | 不删用例、不改语义 |
| B5 | **CI 存量红治理**：核对 12 条基线红的性质，6 条三方库欠账维持「CI 实证才下线」判据并补文档；其余红逐个根因分类（编译缺陷/环境/断言），可修则修（可修的定义：不用装库、不改语言语义） | 每条处置按 `tools/ci/check_regression.py --write-baseline` 重新生成基线，CI 只拦新增打红 | 禁止靠本机装库转绿 |
| B6 | **工具链清理**：把 §3.4 一次性脚本归档到 `tools/ai_copilot/archive/`（或删除），先全仓 grep 确认无 CI/文档/代码引用；`tools/repl.py`/`repl_v3.py` 裁决后归档；保留 `tools/ci/*` 权威脚本并补充顶部一行注释说明用途 | 归档后全仓 grep 无引用；`tools/ci/check_regression.py` 等仍可运行 | 不删有引用的 |

---

## 5. 验证与交付

- **定向测试范围**：与本次改动相关的子集（你合并/移动过的测试文件对应目录 + 你新增的真跑用例）；禁止跑全量（除非独占机器且经主线允许）。
- **交付格式**：
  1. 改了哪些文件（逐个 + 一句意图）
  2. B1 基线报告（总耗时 / 最慢 15 条 / 分目录耗时）与 B4 每次优化的 A/B 原始数据
  3. 重复族合并前后 `collected / passed / failed / skipped / errors` 对照表
  4. 每个删除/合并/归档的反跑判据实测
  5. 工具链归档清单与引用核查结果
  6. 已知未完成 / 未实测项
- **完成判据**：测试基线已存档、重复族已合并（collected 下降且 passed 不减）、目录结构规范化、
  全量回归有量化提速结论（或明确「不建议本轮动，理由 X」）、CI 存量红有逐条结论、工具链已清理。
