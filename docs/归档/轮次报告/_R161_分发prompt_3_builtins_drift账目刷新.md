# 【分发 Prompt 3/4】刷新 builtins_drift 账目（跑 sync 脚本，一条红变两组用例绿）

## 任务

刷新 `stdlib/builtins.py` 三副本账目，使 R161 收口后剩余的 2 个红转绿：

- `tests/unit/test_builtins_drift.py::test_lh_name_diff_only_lh_only`（#6）
- `tests/unit/test_builtins_drift.py::test_lh_public_body_hash_equals_main`（#7，`KeyError: '是否可执行'` 是同一根因的连带）

定性：**账目刷新，非代码 bug**。26 项缺口在 R160 与 R161 完全一致，与 R161 四线改动无关。

## 背景（上下文，勿重新探查）

- 仓库：`G:\dswork\duan-light-merge\light-merge`（Windows 本机开发树）。
- 当前 HEAD：`9f7f81c6e`（R161 收口修复，已推 gitea）。R161 本体 = `307af7932`。
- 权威测试机：**0.82**（192.168.0.82，FreeBSD 15.1，用户 `ai`）。干净树 `~/r161clean`
  已 ff 到 `9f7f81c6e`。解释器 `/home/ai/lm082_venv/bin/python`。
- **0.86 已关机，不要尝试。** 本机 Windows **不跑 pytest**，一切测试在 0.82 跑。
- 本机 ssh 助手：`light-merge/_r161_scratch/d_remote.py`，用法 `d_remote.run('82', cmd, timeout)`。

## 问题定位（0.82 已实测）

| 树 | main 函数数 | LH 副本函数数 | `set(lh)-set(main)` | `set(main)-set(lh)` | 缺口签名 |
|---|---|---|---|---|---|
| 真 R160（444d765a9） | 184 | 159 | `{'整数'}` == LH_ONLY ✓ | **26** | `a038f936a4b303bb` |
| R161（307af7932） | 184 | 159 | `{'整数'}` == LH_ONLY ✓ | **26** | `a038f936a4b303bb` |

26 项缺口（两树逐项相同，main 有而 LH 副本无）：

```
XML生成 XML解析 停止所有监控 停止目录监控 停止线程 创建符号链接
十进制乘 十进制减 十进制加 十进制比较 十进制除
均值 归档 文件监控线程 文件解锁 文件锁定 是否可执行
最大值 最小值 目录监控 磁盘用量 等待线程 解压
设置文件所有者 设置权限 读取符号链接
```

## 修法（一个幂等脚本）

```bash
# 0.82 上（LH_PATH 实测解析为 /home/ai/lightharness/stdlib/builtins.py，存在）
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python scripts/sync_builtins.py
# 期望：exit 0，输出含自检通过；第二次重跑应无 diff（幂等）
```

⚠️ **该脚本跨两个仓、改三个位置**（动手前先确认，动手后逐处报告 diff）：

1. `light-merge/bootstrap/release/stdlib/builtins.py`（**本仓**内，自举打包副本）
2. `lightharness/stdlib/builtins.py`（**LH 仓**，0.82 上在 `/home/ai/lightharness`；
   本机对应 `G:\dswork\duan-light-merge\lightharness`）
3. `lightharness/stdlib/内置核心判型.light`（**LH 仓**，LH_LIGHT_SYNC 定向同步）

脚本设计上幂等（真源 = `light-merge/stdlib/builtins.py`，158 函数），自带反例自检，
任一不成立 exit 非 0。LH_ONLY={'整数'}、BOOT_JSON_EXEMPT/B OOT_PORTED 等豁免以脚本常量为唯一权威，
**不要**手改任何副本内容来"凑绿"。

顺序建议：先 0.82 跑 + 复跑验收 → 再在本机 Windows 树同样跑一遍（两机一致）→
报告两个仓各自的 `git diff --stat` 与关键 diff。

## 验收（0.82 实测，据实报告）

```bash
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python -m pytest \
    tests/unit/test_builtins_drift.py -n 0 -p no:randomly -q
# 期望：2 passed（修复前 2 failed）
```

同时确认没跑坏别的（脚本动了 boot 副本）：

```bash
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python -m pytest \
    tests/unit/test_builtins_drift.py tests/unit/test_R114*.py -n 0 -p no:randomly -q 2>&1 | tail -3
# 期望：全绿（若 test_R114* 有既有失败，区分是否为本次引入）
```

## 纪律红线

- **两个仓都不 commit、不 push。** lightharness 是否提交由业主单独决定。
- `git add` 只用显式文件名。
- 凭证（`.env`）绝不进 commit、日志、报告。
- 跑完必须报告：三个改动位置的 diff 统计、验收命令原始输出、本机 Windows 树是否同步跑过。

## 交付物

1. 两个仓的 `git status` / `git diff --stat`。
2. 简短报告：脚本输出、验收命令原始输出、幂等复跑结果。
