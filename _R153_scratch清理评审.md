# R153 · 历史 scratch / 临时物盘点（**本轮只盘点，不删、不动、不 git clean**）

> 业主裁定第三条：「确认下轮做清理评审，本轮不动 —— 不清理、不删除、不 git clean。」
> 本文件交付**盘点结果**，供下轮评审会直接据此分类与执行。
> 盘点时间：2026-10-16 ｜ 盘点脚本：`_r153_盘点scratch.py`（只读）
> **合计 45.0 MB / 31 个顶层条目，全部 UNTRACKED（tracked 数 = 0）。**

---

## 一、盘点表

| 名称 | 类型 | 文件数 | 大小 | 最后修改 | 来源（推断） | 可复现 |
|---|---|---|---|---|---|---|
| `_r151a_scratch/` | 目录 | 603 | **36.2 MB** | 2026-10-15 14:14 | R151-A 线（字符串工具/格式化/正则 三模块）探测产物；含 `src_head/` 与 `fix_probe/` **两份 src 源码整树副本** + 大量 suite*.log | 是（可从 git + 重跑重建） |
| `.scratch/` | 目录 | 171 | 6.6 MB | 2026-10-08 19:15 | E2 自举实验（`E2_A.py`/`E2_B.py` = bootstrap_v3 拷贝）、`_nn*` 探测 | 是 |
| `_recover/` | 目录 | 10 | 1.6 MB | 2026-10-15 12:57 | JSON 模块抢救脚本（`build_json`/`verify_json`/`diff_json` + `.ll` 中间产物 + `.bak`） | 是 |
| `_r148a_scratch/` | 目录 | 29 | 1.2 MB | 2026-10-14 20:51 | R148-A 线探测 | 是 |
| `_r148c_scratch/` | 目录 | 1 | 2.0 KB | 2026-10-14 22:38 | R148-C 线探测 | 是 |
| `_r152a_scratch/` | 目录 | 4 | 5.1 KB | 2026-10-15 22:42 | R152-A 线探测 | 是 |
| `_r152d_scratch/` | 目录 | 9 | 13.0 KB | 2026-10-16 06:33 | R152-D / **R153 是空 探针**（本轮在用） | 是 |
| `_r151_scratch/` | 目录 | 1 | 0.1 KB | 2026-10-15 11:14 | R151 探测残件 | 是 |
| `_r144c_apicmp.json` / `_refs.json` / `_shadows.json` | 文件 | 3 | 93.6 KB | 2026-10-12 | R144-C 对拍产物 | 是 |
| `_r152_test.log` / `_sync.log` / `_diff.log` / `_c2.log` | 文件 | 4 | 39.6 KB | 2026-10-16 | R152 门禁日志 | 是 |
| `_r140_diag.txt` / `_diag2.txt` / `_win_out.txt` | 文件 | 3 | 4.2 KB | 2026-10-12 | R140 诊断输出 | 是 |
| `_r140b_remote82.py` / `_r143_remote82.py` / `_r143_sync82.py` | 文件 | 3 | 11.3 KB | 2026-10-14 | 0.82 远控/同步一次性脚本 | 是 |
| `_r149d_fix_floor_gate_test.py` | 文件 | 1 | 5.7 KB | 2026-10-15 | R149-D 地板门修复脚本 | 是 |
| `_r150a_append_fs_light.py` / `_r150c_fix_*.py`（3 个） | 文件 | 4 | 12.2 KB | 2026-10-15 | R150 文件系统一次性修复脚本 | 是 |
| `_r152c_probe.py` | 文件 | 1 | 0.6 KB | 2026-10-15 22:32 | R152-C 探针 | 是 |
| `_r153_改判型.py` / `_改python侧.py` / `_补残留.py` / `_盘点scratch.py` | 文件 | 4 | 10.4 KB | 2026-10-16 | **R153 本轮改写脚本**（审计留痕用） | 是 |

**tracked 数全部为 0** ⇒ 以上任何一项都不会进 commit、也不会进 CI checkout。

---

## 二、与本机 `assert_quality.py` 3 条新增违规的对应关系

本机跑 `tools/ci/assert_quality.py` 报的 3 条「新增违规」，**全部来自 `_r151a_scratch/`**：

```
! _r151a_scratch/fix_probe/code_generator.py:1524        [非空断言式]
! _r151a_scratch/src_head/code_generator.py:1520         [非空断言式]
! _r151a_scratch/交接_D线/test_R151_形参遮蔽内置映射.py:110 [unittest字符串断言]
```

即：被判的是 **src 源码副本里的既有代码**（`src/code_generator.py` 本体那行是基线内的），
副本因为路径不同被视为「新条目」。

- 因 untracked，**CI 侧不受影响**（不 checkout）；pre-push 该门也是**非阻塞警告**。
- 业主裁定：暂记为**本地噪音，不阻塞 CI**；评审后再决定是否让质量脚本忽略 scratch 模式。

---

## 三、分类建议（供下轮评审会裁定，**本轮不执行**）

### A 类 · 可删（一次性产物 / 源码副本 / 日志，均可复现）

- 全部 7 个 `*_scratch/` 目录（`_r151a_scratch` 36 MB 是大头）
- `.scratch/`、`_recover/`
- 全部 `*.log` / `*diag*.txt`（`_r152_*.log`、`_r140_diag*`）
- 一次性脚本：`_r140b_remote82.py`、`_r143_remote82.py`、`_r143_sync82.py`、
  `_r149d_fix_floor_gate_test.py`、`_r150a_append_fs_light.py`、`_r150c_fix_*.py`、
  `_r152c_probe.py`
- `_r144c_*.json`（对拍产物，结论已入 R144 报告）

> ⚠️ **删除前二次确认**：尤其 `_r151a_scratch/src_head/`、`fix_probe/` 是**源码整树副本**，
> 删前须确认没有人在拿它们做 diff（当前无引用，但按业主要求须二次确认）。
> ⚠️ `_r152d_scratch/`、`_r153_改*.py` 是**本轮 R153 仍在用/刚用过的审计件**，
> 建议先归档再删（见 B 类）。

### B 类 · 需归档（有取证价值，建议移入 `docs/` 或 `reports/` 并 tracked）

- `_r153_改判型.py` / `_改python侧.py` / `_补残留.py` —— **R153 语义改写的审计脚本**，
  记录了「改了哪些文件、几处、CRLF 自检」，建议随 R153 交付归档。
- `_r152d_scratch/两腿是空探针.py` + `探针是空语义.light` —— 两腿语义实测证据，
  建议归档为「R153 语义实测探针」。
- `_r144c_*.json` 若下轮认为对拍证据有留存价值，可移入 `reports/`；否则按 A 类删。

### C 类 · 需保留并加入 `.gitignore` / 质量脚本忽略

- 目录名模式 `_r1*_scratch/`、`_r1*_scratch.py`、`.scratch/`、`_recover/`
  → 建议写入 `.gitignore`（防误 add）
- 同一批模式写入 `tools/ci/assert_quality.py` 的扫描排除表
  → 消除「源码副本被判新增违规」的本地噪音（业主裁定：评审后再决定）

---

## 四、执行前置条件（下轮评审会）

1. 逐条确认 A 类里没有仍被引用的件（建议 `grep -rn` 交叉验证）。
2. **删除前二次确认**（业主明示）。
3. 先做 B 类归档，再做 A 类删除，最后落 C 类忽略规则。
4. 本轮（R153）**不执行任何删除**。
