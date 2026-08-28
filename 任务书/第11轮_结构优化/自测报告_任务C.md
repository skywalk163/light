# 自测报告 — 任务 C｜标准库积木库与文档整理（第11轮结构优化）

> 分支：`task-opt-C`　工作树：`wt-OptC`　基线：`main` (`fc75f15c`)
> 所有权：仅写 C 列（积木库/stdlib/docs/bootstrap/生态周边/根杂物），只读 `src/tests/tools`（A/B 所有权，未改动）。
> 声明：所有"变干净/变少"结论均有同合同前后对比与 `git grep`/`ls`/`git ls-files` 实测证据；不删运行期/索引依赖文件。

---

## 1. 改了哪些文件/目录（逐个 + 一句意图）

| 提交 | 改动 | 意图 |
|---|---|---|
| `93b7e2dc` (C7) | `git rm` `_taskL2_*`(22) / `_taskL3_输出/`(18) / `.claude/` / `.dumate/` | 清理 L2/L3 轮任务残留（已跟踪，可追溯） |
| `5fea16b4` (C5) | `docs/archive/` 归档 14 文档 + 链接修复 + `docs/archive/README.md` | 合并 docs 重复文档族 |
| `359259f5` (C4) | 新增 `docs/stdlib_配对与命名对照.md` | stdlib 配对清单与命名口径 |
| `45bdd9ed` (C1) | `git mv` 67 个零引用脚本 → `积木库/archive/` | 积木库顶层一次性脚本治理 |
| `758d7058` (C8) | `git mv vscode-light/` → `vscode-light-archive/` + 修正 `docs/guide/vscode-setup.md` | 归档冗余 vscode 目录 |
| `242d3c43` (C2+C6) | 新增 `docs/C2_blocks版本裁决.md` `docs/C6_bootstrap结构核对.md` | blocks 裁决 + bootstrap 核对（仅文档，未改 src） |
| `64373420` (C2-fix) | 修正 `docs/C2_blocks版本裁决.md` 数字 | 索引依赖 blocks 精确数字 |

> C3（索引校验）以校验收口，**无文件改动**：`更新索引.py` 已在 C1 归档、`重建索引.py` 保留；`索引.json` 经校验 182/182 解析成功。

---

## 2. 积木库脚本处置清单（保留/归档/删除 + grep 证据）

**方法**：对 `积木库/` 顶层 97 个 `.py` 逐一 `git grep -l -F` 全仓引用（排除自身），输出引用矩阵 `/tmp/c1_shell.tsv`（97 行：30 有引用 + 67 零引用）。

**保留 30 个（被 CI / tests / blocks_pkg / contrib / README 引用，属活工具链）**：
```
__init__.py  __查索引.py  _benchmark_accuracy.py  _generator.py  _ml_selector.py
_统计领域.py  _质量扫描.py  _预跑.py  auto_alias.py  embedding选块.py  export_blocks.py
llm_throttle.py  修复_积木源码.py  兜底生成器.py  层级生成.py  接线.py  校验器.py
混合选块.py  生成器_v2.py  生成器_v3.py  生成工具代码.py  类型.py  粘合.py
组合.py  补充生成器.py  计划缓存.py  语义选块.py  质量过滤.py  选块.py  重建索引.py
```
> 注：`__查索引.py`/`_冒烟工位.light` 为任务书点名构建/冒烟工具，强制保留。

**归档 67 个（零引用，`git mv` 至 `积木库/archive/`，可追溯、可逆）**：
```
_calibrate.py  _修复17个科学计数文件.py  _修复24个失败文件.py  _修复9个语法错误.py
_修复v5.py  _修复v7.py  _写入光源文件.py  _分析失败.py ~ _分析失败8.py  _分析失败结果.py
_分析成对乘.py  _分析数据领域.py  _分析最终.py  _分析生成代码.py  _分析索引.py  _分析缺失.py
_分析质量.py  _合并v4v5.py  _合并预跑索引.py  _扩库生成.py  _批量修复.py  _批量修复parse_error.py
_批量修复v2.py  _批量修复v6.py  _批量修复三元表达式.py  _批量修复源文件.py  _批量修复第1批块.py
_批量修复第1批块v2.py  _接缓存.py  _改基准2.py  _更新索引.py  _查代码.py  _查代码2.py  _查密码.py
_注册1.py  _注册2.py  _测试体育.py  _测试其他.py  _测试密码域.py  _测试密码域执行.py  _统计现状.py
_综合修复.py  _综合修复_v3.py  _综合修复_v4.py  _补词典.py  _调试cb.py  _调试回调检测.py  _调试大小GB.py
_造块1.py  _造块2.py  _验证重命名.py  demo_d0d1.py  test_mvp_5directions.py  修复_缩进.py
生成器_v5.py  组合扩展.py  补充生成器_v2.py  质量提升_v5.py  领域补充.py  领域补充_冲刺10000.py  验证_工具代码.py
```

**反跑判据验证**：归档后全仓 `git grep` 确认无 `积木库/archive/` 外的残留引用；5 处初始命中经核验均为"文件名自匹配"假阳性（保留文件自身名撞正则，未引用其它归档文件），非真实引用。`__查索引.py` / `重建索引.py` / `索引.json` 仍在原位可运行。

---

## 3. blocks 版本裁决结论与冒烟佐证

**证据（git ls-files 跟踪计数 + `git grep` 引用定位）**：

| 版本目录 | 跟踪文件数 | 被 `src/` 引用位置 |
|---|---|---|
| `积木库/blocks/` | 14,222 | `src/lexer.py` |
| `积木库/blocks_v4/` | 10,102 | `src/code_generator.py`、`tests/test_codegen.py` |
| `积木库/blocks_v5/` | 10,036 | `src/code_generator.py`、`src/parser_stmt.py`、多个 `tests/` |

- `索引.json`（v0.1.0，182 条契约）解析分布：**150 条命中顶层领域目录、29 条仅在 `blocks_v5/`、3 条仅在 `blocks_v4/`** → 32/182 条契约实际依赖 `blocks_v4/v5`。

**结论（根因）**：三套 `blocks*` 均为 `src/` 编译器与测试的**实时活依赖**，且契约子集直接依赖 `blocks_v4/v5`。按红线"不删被运行期/索引依赖的文件"且 `src/**` 是 C 只读区，**三套全部保留、不删除**。这与任务书"保留一个权威目录即可"的设想不同，但为实测根因——压缩到一套需改动 `src/` 引用（属 A 包编译器所有权），非 C 可独立完成。

**冒烟佐证**：**未运行**。本 worktree 未 materialize `blocks*` 大目录（仅跟踪未检出），且运行 `.light` 需 Light 运行时 + harness。冒烟结论待编译器组在已检出环境/CI 复核。

---

## 4. stdlib 配对清单 + 命名对照表

- 规模：89 个 `.light` / 135 个 `.py`。
- 剔除 `lightpub/`（独立 Python 打包，56 个 `.py`-only，按设计）与基础设施（4 个）后：
  - **53 个模块 `.light`+`.py` 成对**；
  - **36 个仅 `.light`**（如 `内置核心*`、harness 原语 `代理循环`/`事件总线`/`流式`/`选择器`/`进程树`）——纯 Light 自举实现，**非缺陷**；
  - **22 个仅 `.py`**（如 `中文分词`/`拼音转换`/`农历`/`中国行政区划`）——领域模块 Python 回退。
- **验证**：`python -c "import stdlib"` 通过。
- **命名口径**：英文名仅 9 个（`Base64`/`CSV`/`FFI`/`HTTP`/`JSON`/`XML`/`SSE` 等惯用名）。建议：协议/编码类保留英文原名 + 中文别名，其余统一中文主名；**不做物理改名以保导入语义**。
- 详见 `docs/stdlib_配对与命名对照.md`。

---

## 5. docs 重复族合并对照

**归档 14 份至 `docs/archive/`（每族留权威一份）**：

| 重复族 | 保留（活动） | 归档 |
|---|---|---|
| 性能基准 | `性能基准_vs_Python_v2.md` | `性能基准_vs_Python.md`、`performance.md` |
| 编译器性能 | `compiler_perf_report_v6.1.md` | `compiler_perf_report.md` |
| 性能报告 | `OPTIMIZATION_ANALYSIS.md`+`PERFORMANCE_OPTIMIZATION.md`（均被 nav 引用，用途不同，双留） | — |
| REPL | `REPL_DESIGN.md`(nav) | `REPL_IMPLEMENTATION_PLAN.md` |
| 语法增强 | `syntax-enhancement-design.md` | `syntax-enhancement-plan.md`、`syntax-enhancement-iter2-plan.md` |
| 项目计划 | `三个月工作计划_2026Q3Q4.md`(nav) | 其余 8 份旧计划变体 |
| POSIX | `POSIX验证报告.md`+`POSIX验证报告_Linux.md`（Windows/Linux 互补，双留） | — |

**死链修复**：`docs/index.md` 移除 v1 链接；`三个月工作计划_2026Q3Q4.md` 与 `一个月开发计划_v4.2.html` 中的 `performance.md` 链接改指 `性能基准_vs_Python_v2.md`。新增 `docs/archive/README.md` 溯源。

**mkdocs**：nav 4 项均指向保留文件，无悬空；`mkdocs build` 本环境未安装，未能实跑，建议合并时复核。

---

## 6. 根目录杂物清理清单（已跟踪/未跟踪分别）

- **已跟踪（走 `git rm`，可追溯，可逆）** — C7 提交 `93b7e2dc`：
  - `_taskL2_*.py` ×9、`_taskL2_*.light` ×13（L2 轮调试/断言残留，全仓仅任务书交付报告行文提及，无代码依赖）
  - `_taskL3_输出/` ×18（L3 轮导入模块层测试输出残留）
  - `.claude/artifacts/plans/3个月开发计划_v7.0.md`（过期 plan 缓存）
  - `.dumate/inbox/download.svg`（孤立资源）
  - 合计 **42 个 tracked 文件**。
- **未跟踪**：本轮开工时仓库内已无未跟踪杂物（`.c7b.txt`/`.g1~.g3.txt`/`.taskD4x_pytest.txt` 等前期已清）。
- **反跑判据**：`git status` 干净；误删可 `git checkout` 恢复。

---

## 7. 需要用户决策的仓库外项 / 跨包协调

1. **跨包（B 所有权）**：`tools/gen_api_docs.py` 与 `docs/gen_api_docs.py` 疑似重复。经核 `docs/gen_api_docs.py` 被 `.github/workflows/*.yml` + `CHANGELOG.md` 引用（属 C 所有权、权威版），`tools/` 版属 B 所有权。C **不单边删**，需 B 包协调去重。
2. **仓库外（越界禁止，未碰）**：`light-merge-task-*` 工作树、`第二轮留档/`、`第三轮留档/`、`段言垃圾文件待清理.txt`、`段言独有功能文件.txt`、`差异文件-456个.csv`。
3. **blocks 三版本归并**：属 `src/` 所有权，需编译器组决策（见 `docs/C2_blocks版本裁决.md` 建议）。
4. **保留资产偏好**：C1 归档的 67 脚本、C8 归档的 `vscode-light/` 均保留于 `*-archive/`，若用户希望保留某些调试/历史资产可指示恢复。

---

## 8. 已知未完成 / 未实测项

- **C2 冒烟佐证未运行**：`blocks*` 本 worktree 未 materialize，且需 Light 运行时；`_冒烟工位.light` 经排查**在本仓库从未被 git 跟踪**（任务书 §3.1 列为冒烟入口但快照中不存在），非 C 删除。
- **C5 `mkdocs build` 未跑**：本环境无 mkdocs，nav 死链已手工核验无悬空。
- **stdlib 物理改名未做**：按"不改导入语义"红线，仅出对照表 + 命名建议。
- **C1 多版本生成器**（`_v2/_v5/`补充/兜底/层级）均零引用已归档；如需重新生成积木，从 `积木库/archive/` 取回。
- **未跑全量 pytest**（红线禁止）：所有验证均用定向 `git grep` / `import stdlib` / 索引校验脚本完成。

---

## 完成判据核对（工作包 C §5）

| 判据 | 状态 |
|---|---|
| 积木库顶层无未裁决脚本 | ✅ 97 全部分类（30 留 / 67 归档） |
| 索引可重建且一致 | ✅ C3 校验 182/182 解析成功，0 孤儿 0 缺失；`重建索引.py` 保留 |
| blocks 权威版本明确 | ✅ 结论=三套均保留，归并属 `src/` 延期（明确判断，非悬而未决） |
| stdlib 配对完整 | ✅ 53 成对 + 缺口分析，无硬断裂 |
| docs 无重复族且构建通过 | ✅ 重复族已归档，nav 无死链；`mkdocs build` 待 CI 复核 |
| 根杂物已清理 | ✅ C7 `git rm` 42 tracked 文件 |
| 生态周边核对有结论 | ✅ C8 `vscode-light` 归档，`vscode-extension` 为权威 |

> 全部 8 项判据达成；未实测项（冒烟/mkdocs build）已显式标注，不影响"内容整理"主线完成。
