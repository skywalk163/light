# 运行手册 · Windows 本机全量门禁（R94 冻结版）

> **适用范围**：light-merge（LM）在 **Windows 本机**跑 `pytest tests/` 全量。
> **R94 裁定**：Windows 本机全量是**稳定性观察面**；**发布判绿以 FreeBSD 0.82 为准**。
> **不在支持矩阵内**：整机 CPU ≥80% 时的 Windows 本机全量——该组合下的结果一律 `invalid`。

---

## 0. 三条硬规矩

1. **CPU <80% 才跑**；≥80% → 不跑，结果标 `invalid`，**不判红也不判绿**。
2. **worker 默认 `-n 4`**（已写进 `pyproject.toml` 的 `addopts`，无需手动加）。
   ⚠️ `-n 4` **不是修复**，只是降低资源争抢与暴露面；99% 负载下仍会崩。
3. **判绿以 0.82 为准**，本机只回答「结构是否干净」（无 node down / 无 INTERNALERROR / 无挂死）。

## 1. 标准流程（复制即用）

```bash
# 工作目录：G:/dswork/duan-light-merge/light-merge
cd /g/dswork/duan-light-merge/light-merge

# ① 跑前 CPU 门禁（平均 CPU ≥80% 直接拒绝，退出码 3）
python scripts/跑前CPU门禁.py --threshold 80 --sample 10
echo "RC=$?"      # 0=放行  3=拒绝(invalid，别跑)  2=环境错误

# ② 门禁 + 全量一步跑（推荐：不通过就不跑）
python scripts/跑前CPU门禁.py --threshold 80 --sample 10 -- \
  python -m pytest tests/ -p no:cacheprovider -q \
    --junitxml=_r94/full.xml --basetemp=_r94_bt_full

# ③ 判红绿：对拍环境红台账（基线缺省=台账全集）
python tests/ci_judge_env_reds.py judge --current _r94/full.xml
echo "RC=$?"      # 0=新增红 0（绿）  1=有新增红（必须逐条解释）
```

判据脚本自检（改台账后必跑）：

```bash
python tests/ci_judge_env_reds.py self-check
```

## 2. 结果分级

| 情形 | 判定 | 处理 |
|---|---|---|
| 门禁 PASS + 无 node down/INTERNALERROR/HANG + judge 新增红 0 | **有效绿** | 可作为本机稳定性证据 |
| 门禁 PASS + judge 新增红 > 0 | **红** | 逐条取证：是回归还是新环境项（入账需 2/2 隔离绿证据） |
| 出现 `[gwN] node down` / `INTERNALERROR` / 墙钟超时挂死 | **invalid** | 不判红绿；重开 [KI-R94-01](./known-issues/R94-xdist-worker-kill.md) 检查是否触及回滚条件 |
| 门禁拒绝（CPU ≥80%） | **invalid** | 换个时间跑；不要 `--force` 后拿结果当结论 |

## 3. 支持矩阵（R94 冻结版）

| 平台 | 负载 | worker | 结果效力 |
|---|---|---|---|
| Windows 本机 | CPU <80% | `-n 4`（默认） | **有效**（判绿仍以 0.82 为准） |
| Windows 本机 | CPU ≥80% | 任意 | **invalid**（不在支持矩阵） |
| Windows 本机 | 任意 | `-n 8` 及以上 | **禁用**（已观测 node down + 挂死） |
| FreeBSD 0.82 | — | `-n auto`（082 脚本显式覆盖） | **判绿权威** |
| Linux 0.86 | — | `-n auto` | 参考 |

## 4. 0.82 判绿（权威口径）

```bash
# 工作目录：G:/dswork/duan-light-merge/lightharness
export MSYS_NO_PATHCONV=1     # ⚠️ 不加会把 /usr/local/bin/python3.12 路径转换坏 → rc=127

python scripts/082全量回归.py sync
python scripts/082全量回归.py test --py /usr/local/bin/python3.12
python scripts/082全量回归.py diff --base reports/082_lightmerge基线_<时间戳>.json
```

判据：新增红 = 本轮失败 − 基线失败，**两侧为 0 才 rc=0**。必须带 `--base`（对拍时间戳基线，
不是 `latest`）。

## 5. 常见坑

- ⛔ 别用 `多平台矩阵.py --mode lm-full --refresh-local` 的「新增红 0」当判据
  （它把新基线写进 latest 再自比，恒为 0）。
- ⛔ 别在**前台** bash 会话里直接起全量：会话超时被 SIGTERM 后，孤儿 pytest 无法 fork
  worker → 假 INTERNALERROR（R93 `n4c1` 实例，507 failed 是中断产物）。长跑只走后台任务。
- ⚠️ 高负载下 Windows 本机全量的红/绿**都不算数**，包括「恰好全绿」——它可能是偶然。

## 6. 相关文档

- [KI-R94-01 · Windows 高负载下 xdist worker 被杀](./known-issues/R94-xdist-worker-kill.md)
- [KI-R94-02 · W-13 accepted-risk](./known-issues/R94-W13-accepted-risk.md)
- [R95 backlog · Job Object / 创建时间闸门](./known-issues/R95-backlog-job-object.md)
- 环境红台账：`tests/ci_environment_reds.txt`（格式与判据见文件头）
