# 光明（Light）公开路线图

> 最后更新：2026-10-26（R167 门禁假绿清零轮）。
> 各轮详细收口见 [`docs/归档/轮次报告/`](docs/归档/轮次报告/)，本文件只保留对外可承诺的部分。
> 详细技术路线见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。

## 当前版本

- 语言本体：**v0.4.0**（稳定，2026-10-03 版本号统一发布）。
  - ⚠️ 版本号口径铁规：仓库内 `v5.x / v6.x / v7.x` 字样均为历史阶段代号，
    写于 2026-10-03 版本号体系统一之前，不是当前真实版本号。对外一律用「光明 / light · v0.4.0」。
- 复刻 harness：r95-dev（2026-09-25，R95 根因战场闭环）。
- 积木库：独立仓 `lighting`（14222 积木 / 45 领域）。

## 北极星（3 个月，到 R98）

> 一个新人在**零作者介入**下，能跑通：发现 → 安装 → Hello World → 复用一个第三方包 → 提交第一个 PR。

## 阶段

### ✅ R96（诚信与地基）

- CLI 命令可用性校正：`light fmt` 因语义破坏缺陷默认关闭并标注（R96-KI-01）。
- 三仓治理文件补齐（LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / SUPPORT / CHANGELOG / ROADMAP / CONTRIBUTORS）。
- 生态地图 + `AWESOME-光明.md` + RFC 提案流程。
- 版本一致性校验脚本（`scripts/check_version_consistency.py`）。

### ✅ R97（工具兑现 · 已闭环）

- ✅ T9–T19 全部完成（R137–R140 各线交付）：
  - T9 `light fmt` 收敛为空白安全子集；
  - T10/T11 `light doc` / `light profile` 对真实工程可用；
  - T12 `light install/publish` + 共享 registry（默认区域选择，国内 gitcode / 国外 github）；
  - T13 积木库 ↔ `light pkg` 打通；
  - T14 LSP 诊断服务 + T16 LSP 编辑体验补全；
  - T15 CI badge 动态生成（本地 SVG，不联网）；
  - T17 原生腿语义正确性深挖（L-182/L-191/L-194 已修，native 可跑率 79.17%）；
  - T18 `--target wasm` CLI 接通（Pyodide 后端）；
  - T19 文档债务清理（docs/blog 11 篇版本号口径统一）。
- 详见各轮收口报告归档。

### 🚀 R98（发行与增长）

- 官网门户（对标 go.dev 三栏）；
- 在线 Playground（WASM 后端）；
- 一键安装脚本；
- 3 个样板第三方包 + 发布教程；
- 展示墙 + 月度 Newsletter + 生态热度榜。

## 本批已落地（AI 友好反馈回路，T-0316 ~ T-0326）

以下能力各自在对应任务分支验收，T-0326 把它们接进主流程并记录归集；本段只登记已落地事实。

- 结构化错误码体系（`src/diagnostics/`，T-0316）· 报错行号锚定与 stdlib 导入提示（`src/enhanced_errors.py`，T-0317）；
- `light ai check --json` 机器可读诊断（T-0318）· 本地报错数据集与脱敏（`tools/ai_copilot/error_corpus.py`，T-0319）；
- 按近 30 天错误频次动态置顶的语法速查卡（`error_stats.py` / `syntax_card.py`，T-0320）；
- MVP Surface 与五方向真跑场景（`docs/MVP_SURFACE.md`、`examples/mvp/`，T-0321）；
- 吃狗粮场景回归与基线欠账表（`tests/dogfood/`，T-0322）· 覆盖率门（`tests/test_coverage_gate.py`，T-0323）；
- `STATUS.md` 单一状态入口（T-0324）· LSP 标识符语言一致性检查（T-0325）；
- 收尾接线：check 失败自动归档（可关闭、失败不阻断）、card 频次置顶、速查卡引用 STATUS.md（T-0326）。

## 不在计划内（明确划界）

- 不改变核心编译器后端架构（LLVM/C/WASM 探索单列于 `docs/ROADMAP.md`）；
- 不做商业托管 / 云 IDE（社区开源优先）。

## 如何参与路线讨论

- 提案：见 [`docs/community/rfc流程.md`](docs/community/rfc流程.md)；
- 想法：GitHub Discussions → ideas 模板；
- 进度：各轮收口报告见 [`docs/归档/轮次报告/`](docs/归档/轮次报告/) 与 `docs/known-issues/`。
