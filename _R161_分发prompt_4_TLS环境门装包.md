# 【分发 Prompt 4/4】消除 TLS/依赖环境门（0.82 venv 装 cryptography + requests）

## 任务

消除 R161 收口后剩余的 1 个 failed + 9 个 error——全部是**环境依赖缺失**，不是代码问题：

- `tests/test_tls_light.py::test_缺cryptography必须响亮降级`（#9，缺 `cryptography`）
- 9 errors = `tests/lightpub/test_lightpub_bridge.py` ×6（`ModuleNotFoundError: requests`）
  + `tests/test_async_io_light.py::TestTLS异步读腿` ×3（`ModuleNotFoundError: cryptography`）

## 背景（上下文，勿重新探查）

- 仓库：`G:\dswork\duan-light-merge\light-merge`（Windows 本机开发树）。
- 当前 HEAD：`9f7f81c6e`（R161 收口修复，已推 gitea）。R161 本体 = `307af7932`。
- 权威测试机：**0.82**（192.168.0.82，FreeBSD 15.1，用户 `ai`）。干净树 `~/r161clean`
  已 ff 到 `9f7f81c6e`。解释器 `/home/ai/lm082_venv/bin/python`（所有测试用这个 venv）。
- **0.86 已关机，不要尝试。** 本机 Windows **不跑 pytest**。
- 本机 ssh 助手：`light-merge/_r161_scratch/d_remote.py`，用法 `d_remote.run('82', cmd, timeout)`。
- 设计背景：`tests/test_tls_light.py` 头注写明——缺 cryptography 时**不许静默转绿**，
  只留一条响亮降级的红；只有显式 `LIGHT_ALLOW_SKIP_TLS_TEST=1` 才整文件 skip（人为放行）。
  **本次要的是真修复（装包），不是放行。**

## 修法（只动 0.82 的 venv，不动代码）

```bash
# 0.82 上，装进 lm082_venv（先用 --dry-run 或直接装，据实报告输出）
/home/ai/lm082_venv/bin/pip install cryptography requests
```

- **不要**设 `LIGHT_ALLOW_SKIP_TLS_TEST=1`（那是人为跳过，会把红藏起来）。
- **不要**改任何测试或源码。
- 装完报告两包版本：`/home/ai/lm082_venv/bin/pip show cryptography requests | head -20`。

## ⚠️ 装包后的风险必须验证（重点）

`cryptography` 装上后 TLS 测试会**真跑**（自签证书、真握手），可能暴露此前被环境门掩盖的真实问题。
必须整文件跑并如实报告：

```bash
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python -m pytest \
    tests/test_tls_light.py tests/lightpub/test_lightpub_bridge.py \
    tests/test_async_io_light.py -n 0 -p no:randomly -q 2>&1 | tail -6
```

- 期望基线（修复后）：9 个 error 全清、`test_缺cryptography必须响亮降级` 转绿或按设计消失
  （装包后它可能因依赖已满足而 skip/pass，以实测为准，据实报告）。
- 若出现**新的 failed**（依赖装上前被掩盖的真问题）：**不要自行修饰**，原样报告，
  连同失败断言与 stderr 关键行交回业主定位。
- 若 lightpub bridge 需要网络/端口：据实报告跳过或失败原因，不要伪造绿色。

## 纪律红线

- **不 commit、不 push**；本任务只动 0.82 venv。
- 装包范围仅限 `cryptography` / `requests` 两个，不顺手升其它包（避免引入无关漂移）。
- 凭证（`.env`）绝不进日志/报告。
- 远端 `pip` 如遇超时，重试一次后据实报告，不要换源强行安装。

## 交付物

1. pip install 原始输出 + 两包版本号。
2. 三个测试文件的验收原始输出（rc + 汇总行 + 任何新 failed 的断言原文）。
