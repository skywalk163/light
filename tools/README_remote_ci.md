# remote_ci.py —— 0.88（FreeBSD 15.1）统一排队跑测

多个 agent 的机器各不相同（Windows 老机 / 云沙箱 / FreeBSD），同一份改动在不同机器上
「红绿」不可比、耗时也没法归因。所以测试统一到 `192.168.0.88` 上跑，这里负责排队与隔离。
本工具在本仓的位置是 `tools/remote_ci.py`（源码同源副本见 `duan-light-merge/_tools/remote_ci.py`）；
0.88 全量基线见 `tools/baseline_0_88_light_merge.md`，测试分级闸门见 `docs/测试分级与远程跑测.md`。

## 一、命令

```bash
python tools/remote_ci.py --list                       # 谁在跑、还有没有空位
python tools/remote_ci.py --repo .                     # 排队跑本仓全量（2 槽 × -n 6）
python tools/remote_ci.py --repo . --tag 某线路 -- -k linter    # `--` 之后透传 pytest
python tools/remote_ci.py --repo . --slots 1 --jobs 12   # 重活独占
```

`--repo` 也可以指向其它本地仓目录（如 `lightprism`）。
**注意**：`--repo` 的默认值是按 `duan-light-merge` 目录布局写的（指向 `仓根/light-merge`），
在本仓里跑请**显式带 `--repo .`**（R222 各卡的示例口径），不要依赖默认值。
**注意**：`--repo` / `--tag` / `--slots` / `--jobs` / `--timeout` 这些是本工具自己的参数，
必须写在 `--` **之前**；`--` 之后才是 pytest 的。

## 二、它做了什么

1. 打包本地工作树（不含 `.git` / `.venv` / `__pycache__` / `outputs` 等；`*.sh` 在**包内**转 LF，
   tar 条目用 POSIX 分隔符），上传到 `/tmp/lp-ci/run-<时间戳>-<tag>.tgz`；
2. 远端用 `mkdir` 的原子性抢槽：`/tmp/lp-ci/slots/slot-1..N`，抢不到就排队等，
   锁超过 4 小时无更新会被自动回收（防死锁）；
3. 解包到 `/tmp/lp-ci/run-<时间戳>-<tag>/`，在里面跑 `PYTHONPATH=src python3 -m pytest`；
4. 退出时释放槽位，并在 `/tmp/lp-ci/queue.log` 记三行 START / END（rc 与耗时）。

## 三、纪律

- 不直连 ssh 跑 pytest；不删别人的 `run-*` 目录；不手工删 `slots/slot-*`（那是抢别人的锁）。
- 排队输出 `[queue] 槽位全满，排队等待` 不是失败，不要 Ctrl-C 改本地跑。
- `--queue-timeout` 到点退出码 75，表示**没上跑**，如实汇报。
- 口令来自 `.env` 的 `SSH_USER_WORKBUDDY` / `SSH_PASS_WORKBUDDY`，**不许写进任何交付物、日志、汇报**。
  工具不写死凭据路径，按候选顺序找第一个存在的：`LP_ENV_FILE` / `--env-file`（最优先）→
  仓根 `.env` → 上一级 `.env` → 上一级 `duan-light-merge/.env` → `~/.lp_ci_env`。
  在 `G:/dswork/duan-light-merge/light-merge` 主 checkout 里跑会自动命中上一级的 `.env`；
  在 hive worktree 等隔离目录里跑时候选都不会命中，需显式指定，例如：
  `python tools/remote_ci.py --env-file G:/dswork/duan-light-merge/.env --list`。

## 四、前置条件（0.88 上已具备，2026-11-17 核实）

| 项 | 值 |
|---|---|
| 系统 | FreeBSD 15.1-RELEASE-p1 amd64，12 vCPU |
| Python | 3.12.13 |
| pytest / xdist | 8.4.2 / 3.8.0 |
| pytest-timeout | 2.4.0（`light-merge` 的 `pyproject.toml` 里 `addopts` 硬依赖它，缺了直接 `unrecognized arguments` 起不来） |
| torch | 2.12.1a0 |

## 五、遇到这两类报错先看这里

- **`no tests ran` 且瞬间退出**：多半是 pytest 收到了一个多余的 `--`（`pytest -- -k xxx`）。
  本工具已剥掉分隔符；自己手敲命令时不要让 `--` 落到 pytest 手里。
- **`unrecognized arguments: --timeout=60`**：远端缺 `pytest-timeout`。
  要么 `python3 -m pip install --user pytest-timeout`，要么加 `--no-addopts` 清空仓库 addopts。

## 六、实测耗时（12 vCPU）

| 场景 | 耗时 |
|---|---|
| lightprism 全量，单槽 `-n 6` | 49 s |
| lightprism 全量，双槽并行 | 65 s / 65 s |
| light-merge `-k linter`（40 项） | 172 s（其中收集约 72–89 s，全仓 10,155 项） |

**并行收益全在 xdist**：串行在 12 核上并不快（测试是延迟受限：大量 `subprocess.run` 起
python/bash），所以永远带 `-n`，不要串行跑全量。

> AI生成
