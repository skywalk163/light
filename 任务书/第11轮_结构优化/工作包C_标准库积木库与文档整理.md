# 工作包 C：内容与生态整理 —— 积木库 / stdlib / docs / 自举 / 示例 / 杂物清理

> 分发给 **Agent C** 的独立任务书。本文件自包含，不依赖总纲以外的其他文件；与总纲冲突处以此文件为准。
> **声明**：使用性能优化流程——**无测量，不结论；无同合同证据，不授权。**
> 本包以「内容盘点 → 清理 / 归并 / 索引重建 → 可消费验证」为主线；不改变任何语言行为，不删被运行期/文档引用的文件。

---

## 1. 目标

把内容与生态层从「生成 / 修复脚本与多版本堆叠态」整理成「单一权威内容 + 可索引 + 无杂物」的状态：
- `积木库/`：治理顶层一次性脚本、裁决多套 blocks 版本、重建并核验索引。
- `stdlib/`：核对 `.light`/`.py` 配对完整性、统一命名口径。
- `docs/`：合并重复文档族、建立索引、归档过期计划。
- 根目录与生态周边：清理任务残留与垃圾文件、核对周边组件（lsp / vscode-extension 等）。

---

## 2. 文件所有权

- **写（唯一所有权）**：
  - `积木库/**`、`stdlib/**`、`docs/**`、`bootstrap/**`、`examples/**`、`contrib/**`
  - 生态周边：`lsp/**`、`debug-adapter/**`、`vscode-extension/**`、`vscode-light/**`、`blocks_pkg/**`、
    `playground/**`、`edu/**`、`demo*/**`、`example1/**`、`testproj2/**`、`test_project*/**`、
    `opensource_projects/**`、`ollama_model/**`、`lighttests/**`
  - 根文档与根杂物（仓库内）：`README.md`、`CHANGELOG.md`、`CONTRIBUTING.md`、`LICENSE`、`mkdocs.yml`、
    `.g1.txt`、`.g2.txt`、`.g3.txt`、`.c7b.txt`、`.taskD4x_pytest.txt`、`_taskL2_*.py`、`_taskL2_*.light`、
    `.scratch/`、`_taskL3_输出/`、`__pycache__/`、`.light_cache/`、`.claude/`、`.dumate/`
- **只读（验证用，禁止改动）**：`src/**`、`cli/**`、`tests/**`、`pyproject.toml`、`.github/**`、`.gitea/**`
- **越界禁止**：`g:\dswork\duan-light-merge\` 根下（仓库外）的 `light-merge-task-*` 工作树、`第二轮留档/`、
  `第三轮留档/`、`段言垃圾文件待清理.txt`、`段言独有功能文件.txt`、`差异文件-456个.csv` 等一律不碰；
  如需用户决策，在交付说明中列出，不自行删除。

---

## 3. 现状证据（2026-08-28 已核实）

### 3.1 积木库（37,022 文件，504,607 行 —— 全项目最大）
- **顶层一次性脚本堆叠（40+ 个，清理候选，先 grep 引用再归档）**：
  - `_分析*`：`_分析失败(1~8).py`、`_分析失败结果.py`、`_分析数据领域.py`、`_分析生成代码.py`、`_分析索引.py`、
    `_分析缺失.py`、`_分析质量.py`、`_分析最终.py`、`_分析成对乘.py`
  - `_修复*`：`_修复17个科学计数文件.py`、`_修复24个失败文件.py`、`_修复9个语法错误.py`、`_修复v5.py`、`_修复v7.py`、
    `_批量修复(.py/_v2/_v6/三元表达式/parse_error/第1批块/v2/源文件).py`、`_综合修复(_v3,_v4).py`、`修复_积木源码.py`、`修复_缩进.py`
  - `_生成*`：`_生成器_v2.py`、`_生成器_v3.py`、`_生成器_v5.py`、`兜底生成器.py`、`补充生成器(_v2).py`、`层级生成.py`、`生成工具代码.py`
  - `_选块*`：`混合选块.py`、`语义选块.py`、`embedding选块.py`、`组合.py`、`组合扩展.py`、`统计双指标配方.json`、`范围跨度配方.json`
  - `_索引*`：`重建索引.py`、`更新索引.py`、`_查索引.py`、`_注册1.py`、`_接缓存.py`、`索引.json`、`积木库_导出_v4.json`
  - `_测试/调试/其他`：`_测试密码域(.py/执行.py)`、`_测试体育.py`、`_测试其他.py`、`_调试cb.py`、`_调试回调检测.py`、
    `_调试大小GB.py`、`校验器.py`、`类型.py`、`接线.py`、`粘合.py`、`auto_alias.py`、`export_blocks.py`、`llm_throttle.py`、`计划缓存.py`
- **多套 blocks 版本目录并存**：`blocks/` + `blocks_v4/` + `blocks_v5/`（需裁决权威版本，结合 `索引.json` 与冒烟测试）
- **领域目录**：`中文/几何/函数/化学/单位/地理/密码/工具/工具代码/排序/搜索/数学/数据/数组/文件/文本/日期/时间/校验/格式/物理/生成/生物/类型/系统/统计/编码/网络/计算机/评估/财务/迭代/逻辑/随机/集合/音乐/颜色/验证`
- **冒烟/验证入口**：`_冒烟工位.light`、`__组合测试.light`、`test_mvp_5directions.py`、`_质量扫描.py`、`_质量报告.md`、`_预跑报告.md`

### 3.2 stdlib（224 文件，55,442 行）
- `.light`（自举实现）与 `.py`（Python 回退）成对：`Base64/CSV/JSON/XML/FFI/HTTP/SSE/中文NLP/列表工具/加密…` 均成对存在。
- 命名口径不统一：英文名（`Base64.light`、`CSV.light`、`JSON.light`…）与中文名（`中文NLP.light`、`列表工具.light`、`临时文件.light`…）并存；
  部分仅中文名（`事件总线.light`、`代理循环.light`、`伪终端.light`…）。
- 子目录：`分布式/`、`lightpub/`；根级另有 `_light_import_hook.py`、`builtins.py`、`uuid工具.py` 等。

### 3.3 docs（373 文件，94,845 行）
- **重复文档族（合并候选）**：
  - 性能类：`性能基准_vs_Python.md` + `性能基准_vs_Python_v2.md`；`PERFORMANCE_OPTIMIZATION.md` + `OPTIMIZATION_ANALYSIS.md` + `performance.md`；`compiler_perf_report.md` + `compiler_perf_report_v6.1.md`
  - 计划类：`三个月工作计划_*` ×6（2026Q3Q4 / 6.2_6.3 / v5.2~v6.0 / v5.5~v6.0 / v6.0~v6.1 / v6.1~v6.2）
  - 验证类：`POSIX验证报告.md` + `POSIX验证报告_Linux.md`（仓库根级另有同名副本）
  - 设计类：`REPL_DESIGN.md` + `REPL_IMPLEMENTATION_PLAN.md`；`syntax-enhancement-design.md` + `syntax-enhancement-iter2-plan.md` + `syntax-enhancement-plan.md`
- 根级已有一个英文 `index.md`；`docs/gen_api_docs.py`、`tools/gen_api_docs.py` 疑似重复。
- `known_issues.md` 是核心缺陷账（配合第 10 轮回写）。

### 3.4 bootstrap（184 文件，72,194 行）
- 自举编译器（Light 源码，README 称 95 段落），第 10 轮 R10-6 要求盘点「哪些语法仍是手动编译器独占」。
- 本轮 C 只做**结构核对**：目录/文件命名是否与 `src/` 手写编译器对应、是否有重复文件；功能差距盘点留给语言泳道，C 只出清单不实现。

### 3.5 根目录杂物（仓库内）
- 任务残留：`.c7b.txt`、`.g1.txt`、`.g2.txt`、`.g3.txt`、`.taskD4x_pytest.txt`、`_taskL2_*.py`（7 个）、`_taskL2_*.light`（10+）、`.scratch/`、`_taskL3_输出/`
- 缓存/生成物：`__pycache__/`、`.light_cache/`
- 先 `git ls-files` 确认跟踪状态：已跟踪的走 `git rm`（可追溯），未跟踪的直接删；删除前逐文件确认不是他人未提交工作。

---

## 4. 任务清单（每项必须带反跑判据）

| # | 任务 | 反跑判据（改哪一行立红 → 复位绿） | 边界 |
|---|---|---|---|
| C1 | **积木库顶层脚本治理**：对 §3.1 全部 40+ 个 `_*.py`/生成器/选块脚本逐一 grep 引用（含 `__查索引.py`/`_冒烟工位.light`/CI 引用），无引用的归档到 `积木库/archive/`（或删除），有引用的保留并补一行用途注释；多版本生成器（_v2/_v3/_v5、补充/兜底/层级）裁决保留一个权威 + 归档其余 | 归档后全仓 grep 无残留引用；`__查索引.py` / `_冒烟工位.light` 仍可运行 | 不删运行期/索引依赖 |
| C2 | **积木库版本目录裁决**：比对 `blocks/` vs `blocks_v4/` vs `blocks_v5/`（文件数、索引覆盖、冒烟通过率），裁决权威版本并文档化；跑 `_冒烟工位.light` / `__组合测试.light` 佐证 | 裁决后权威版本索引可重建、冒烟全绿；revert 归并立红可定位 | 保留一个权威目录即可 |
| C3 | **积木库索引一致性**：重建/校验 `索引.json`，确认与 blocks 实际文件一一对应（无孤儿索引、无缺失索引）；`重建索引.py`/`更新索引.py` 二选一保留 | 重建后索引与文件数一致；删掉索引中一条对应块立红可检出 | 不批量改块内容 |
| C4 | **stdlib 配对与命名**：输出 `.light`/`.py` 配对完整性清单（缺 `.light` 或缺 `.py` 的条目）；产出中英文名对照表并统一到文档口径（建议以中文名为主、英文名文档化别名） | 对照表逐条可 grep 到实际文件；命名调整后 `python -c "import stdlib"` 及 `从 X 导入` 定向用例绿 | 不改导入语义 |
| C5 | **docs 去重与索引**：合并 §3.3 重复文档族（保留最新/最权威一份，其余标「已并入 XX」或归档），更新 `index.md` 建立分类索引；删除 `docs/gen_api_docs.py` 与 `tools/gen_api_docs.py` 二选一的重复 | 合并后 `mkdocs` 构建通过、无死链；revert 合并不影响构建 | 不改技术结论 |
| C6 | **bootstrap 结构核对**：输出 bootstrap 目录文件清单与 `src/` 手写编译器对应关系，标出重复/冗余文件；功能差距（R10-6）只出盘点清单 | 核对清单逐条可落文件路径 | 不实现语言功能 |
| C7 | **根目录杂物清理**：按 §3.5 清理仓库内任务残留/缓存/垃圾文件（已跟踪走 `git rm`，未跟踪直接删），先确认无他人未提交工作 | 清理后 `git status` 干净；误删可 `git checkout` 恢复 | 不碰仓库外目录 |
| C8 | **生态周边核对**：`lsp/`、`debug-adapter/`、`vscode-extension/` 与 `vscode-light/` 是否存在重复/冗余（如两个 vscode 目录），输出核对结论并做最小清理 | 清理后对应组件构建/语法可用 | 不动 `.github` CI 依赖的构建产物 |

---

## 5. 验证与交付

- **验证方式**：积木库 `__查索引.py` / `_冒烟工位.light` / `__组合测试.light`；stdlib 的「从 X 导入」定向用例；
  `mkdocs build`（docs 改动）；`git status`（杂物清理后干净）。禁止跑全量 pytest。
- **交付格式**：
  1. 改了哪些文件/目录（逐个 + 一句意图）
  2. 积木库脚本处置清单（保留/归档/删除 + grep 证据）
  3. blocks 版本裁决结论与冒烟佐证
  4. stdlib 配对清单 + 命名对照表
  5. docs 重复族合并对照（并入哪份、哪份归档）
  6. 根目录杂物清理清单（已跟踪/未跟踪分别处理）
  7. 需要用户决策的仓库外项（列出即可）
  8. 已知未完成 / 未实测项
- **完成判据**：积木库顶层无未裁决脚本、索引可重建且一致、blocks 权威版本明确、stdlib 配对完整、
  docs 无重复族且构建通过、根杂物已清理、生态周边核对有结论。
