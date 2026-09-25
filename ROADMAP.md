# 光明（Light）公开路线图

> 最后更新：2026-09-25（R96）　来源：社区生态建设总纲 R96
> 详细技术路线见仓库内 [`docs/ROADMAP.md`](docs/ROADMAP.md)；本文件只保留**对外可承诺**的部分。

## 当前版本

- 语言本体：**v7.0.0**（稳定，2026-08-14 双线合并与品牌统一版）
- 复刻 harness：r95-dev（2026-09-25，R95 根因战场闭环）
- 积木库：独立仓 `lighting`（14222 积木 / 45 领域）

## 北极星（3 个月，到 R98）

> 一个新人在**零作者介入**下，能跑通：发现 → 安装 → Hello World → 复用一个第三方包 → 提交第一个 PR。

## 阶段

### ✅ R96（本轮 · 诚信与地基）
- CLI 命令可用性校正：`light fmt` 因语义破坏缺陷默认关闭并标注（R96-KI-01），其余命令实测可用；
- 三仓治理文件补齐（LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / SUPPORT / CHANGELOG / ROADMAP / CONTRIBUTORS）；
- 生态地图 + `AWESOME-光明.md` + RFC 提案流程；
- 版本一致性校验脚本（`scripts/check_version_consistency.py`）。

### 🔜 R97（工具兑现）
- **T9 修复 R96-KI-01**：重写 / 收敛 `src/formatter`，消除"补冒号＋重排缩进"破坏；
- T10/T11 验收 `light doc` / `light profile` 对真实工程可用；
- T12 `light install/publish` + 共享 registry（Go-Modules 式 "git 即 registry"）；
- T13 积木库 ↔ `light pkg` 打通；
- T14 LSP / 诊断服务（编辑器从"高亮"升级到"报错+跳转"）；
- T15 CI badge + 覆盖率对外可见。

### 🚀 R98（发行与增长）
- 官网门户（对标 go.dev 三栏）；
- 在线 Playground（WASM 后端）；
- 一键安装脚本；
- 3 个样板第三方包 + 发布教程；
- 展示墙 + 月度 Newsletter + 生态热度榜。

## 不在计划内（明确划界）

- 不改变核心编译器后端架构（LLVM/C/WASM 探索单列于 `docs/ROADMAP.md`）；
- 不做商业托管 / 云 IDE（社区开源优先）。

## 如何参与路线讨论

- 提案：见 [`docs/community/rfc流程.md`](docs/community/rfc流程.md)；
- 想法：GitHub Discussions → ideas 模板；
- 进度：各轮收口报告（如 `R95_收口报告.md`）与 `docs/known-issues/`。
