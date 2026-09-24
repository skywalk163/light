# KI-R94-01 · Windows 高负载下 xdist worker 被杀（node down → INTERNALERROR / 挂死）

> **状态**：`open / known-risk`（**机理未定性**，R94 **不根治**）
> **登记轮次**：R94（2026-09-25，开发冻结轮）
> **责任人**：R95 轮次负责人（未指定前由仓库 maintainer 兜底）
> **后续入口**：[`R95-backlog-job-object.md`](./R95-backlog-job-object.md)
> **是否阻塞发布**：否（R94 裁定：未定性根因不阻塞冻结；只做规避 + 判绿口径收口）

---

## 1. 现象

Windows 本机跑 light-merge 全量（`pytest tests/`，xdist 并行）时，个别 worker 进程被杀，
日志出现：

```
[gwN] node down: Not properly terminated
```

后续走向二选一，都是**无效结果**：

| 走向 | 表现 | 观测实例 |
|---|---|---|
| A. 重启失败 | `INTERNALERROR ... execnet bootstrap io.read(1) got 0` | R93-M `mfinal`：4 次 node down，仅 3476 passed 即崩（正常 8000+） |
| B. 重启卡住 | 整轮挂死在 99%，无进展，被墙钟看门狗杀 | R93-M `mfinal2`：3 次 node down，卡死被 3000s 看门狗终止 |

两种走向都不产出可信 junit，**既不能判绿也不能判红**。

## 2. 触发条件

- 平台：**Windows 本机**（FreeBSD 0.82 与 Linux 0.86 未曾复现）。
- 负载：**整机 CPU 76%~99%**（桌面应用占满）。与**绝对负载强相关**。
- 与 worker 数**非单调**：`-n 8` 卡死过一次；`-n 4` 在**低负载**连续 3 轮干净，
  但在 **99% 负载**下同样崩（`mfinal` / `mfinal2` 均为 `-n 4`）。
  → **降 worker 是降低暴露面，不是修复**。
- 触发点集中在「自行拉起子进程 / 进程树」类用例附近，但**不是**这些用例的断言问题。

## 3. 已排除的假设（一手证据）

| 假设 | 验证方式 | 结论 |
|---|---|---|
| H1：PID 复用 + `stdlib/进程树.light` `[R92-A-LEAK]` PPID 链回溯补杀误伤兄弟 worker | 边界探针：并发 spawn **25,285** 个「两层短命进程树」制造极端 PID 复用压力，同时跑杀树用例（`-n 8`） | **未复现**：无关进程被杀 **0**，错误 **0**（`_r93/b_collateral_probe2.json`） |
| H2：杀树用例自身 flaky（树没建好） | R93-M 抓到残余红：99% 负载下双层 wrapper bootstrap >10s，等树窗口不够 → 孤立 5 轮全红 | **属实但已修且不属本议题**：`[R93-M-BOOTSTRAP-WINDOW]` 10s→30s（杀树断言一字未改），同负载下 3/3 绿 |
| H3：worker 数过多导致资源争抢 | `-n 8 / 6 / 4` 对照 | **部分成立**：`-n 4` 显著降低发生概率，但**高负载下仍崩**，故只是缓解 |

**剩余候选方向（均未验证）**：xdist/execnet 在 Windows 高负载下的自身脆弱性；
ctypes 调用 Job Object 时的崩溃；瞬时内存压力触发的系统级终止。

## 4. 结论

> **机理未定性。规避有效，但规避 ≠ 修复。**

R94 明确**不**做根因修复（Job Object 改造 / 创建时间闸门都会引入新逻辑、新测试、新风险，
与本轮「开发冻结」冲突）。只保留规避口径 + 判绿口径。

## 5. R94 现行规避口径（强制）

1. **默认 worker = `-n 4`**：已固化进 `pyproject.toml` 的 `addopts`
   （`[tool.pytest.ini_options]`）。命令行显式 `-n <N>` 可覆盖（后出现的生效），
   故 0.82 的 `scripts/082全量回归.py`（显式补 `-n auto`）**不受影响、保留吞吐**。
2. **跑前 CPU 门禁**：`python scripts/跑前CPU门禁.py --threshold 80 --sample 10`
   → 平均 CPU ≥80% 判定 `INVALID`，**不跑 / 不判红绿**（退出码 3）。
3. **判绿以 0.82 为准**：Windows 本机全量只作稳定性观察面；发布判绿取 FreeBSD 0.82
   的 `082全量回归.py test --py /usr/local/bin/python3.12 --base <时间戳基线>`。
4. **高负载 Windows 本机全量不在支持矩阵内**：该组合下的任何结果一律 `invalid`。
5. **`-n 8` 及以上禁用**：已观测到 node down + 挂死。

## 6. 回滚条件（何时重开本 issue）

出现任一情况即重开并升级为 P1：

- 低负载（<80%）下 `-n 4` 连续 2 轮出现 node down / INTERNALERROR / HANG；
- 0.82（FreeBSD）或 Linux 上首次复现同类 node down；
- 有新的可复现最小用例（不依赖整机 99% 负载）。

## 7. 移交 R95 的 backlog

见 [`R95-backlog-job-object.md`](./R95-backlog-job-object.md)：
① Job Object 成员查询（根治候选）；② 创建时间闸门（兜底候选，优先级低于 ①）。
