# Known Issues · CI / 门禁类（语言本体之外的工程侧遗留）

> 本目录只放**工程侧（CI / 门禁 / 测试稳定性）**的 known issue；
> **语言/编译器本体**的已知问题仍在 [`../known_issues.md`](../known_issues.md)。
> 建目录轮次：R94（2026-09-25 开发冻结轮）。

## 看板

| 编号 | 标题 | 状态 | 责任人 | 后续入口 | 阻塞发布 |
|---|---|---|---|---|---|
| KI-R94-01 | Windows 高负载下 xdist worker 被杀（node down → INTERNALERROR / 挂死） | `open / known-risk`（机理未定性，仅规避） | R95 轮负责人 | [R95-backlog-job-object.md](./R95-backlog-job-object.md) | 否 |
| KI-R94-02 | W-13 滑动窗口派发时序断言（阈值放宽换来的绿） | `accepted-risk`（**不销账**） | R95 轮负责人 | 去抖动化改造后重标阈值 | 否 |

## 约定：什么叫「有状态、有责任人、有后续入口」

1. **有状态**：只能是 `open` / `accepted-risk` / `closed(销账，须附证据)` 三态之一，
   禁止「观察中」这种无终态表述。
2. **有责任人**：写轮次负责人；未指定前由仓库 maintainer 兜底，不许留空。
3. **有后续入口**：必须给出下一个可执行动作（文档、backlog 编号、或明确的回滚条件）。

## 相关

- 运行手册（Windows 本机全量）：[`../运行手册_Windows本机全量.md`](../运行手册_Windows本机全量.md)
- 环境红台账：`tests/ci_environment_reds.txt`
- 判据脚本：`tests/ci_judge_env_reds.py`（`judge` / `self-check`）
