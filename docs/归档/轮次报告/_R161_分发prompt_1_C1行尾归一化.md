# 【分发 Prompt 1/4】修复 C1 纯 CRLF 测试红（行尾 artifact，改测试判据）

## 任务

把 `tests/unit/test_R160_E5协程库.py::test_C1_骨架文件存在且为纯CRLF` 从「非 Windows 必红」
修为「行尾一致即过」。这是 R161 收口后剩余的 5 个红之一（#5），定性为**行尾 artifact，非代码缺陷**。

## 背景（上下文，勿重新探查）

- 仓库：`G:\dswork\duan-light-merge\light-merge`（Windows 本机开发树）。
- 当前 HEAD：`9f7f81c6e`（R161 收口修复，已推 gitea）。R161 本体 = `307af7932`。
- 权威测试机：**0.82**（192.168.0.82，FreeBSD 15.1，用户 `ai`）。干净树 `~/r161clean`
  已 fast-forward 到 `9f7f81c6e` 且 `git status` 干净。解释器 `/home/ai/lm082_venv/bin/python`。
- **0.86 已关机，不要尝试。**
- 本机 Windows **不跑 pytest**（PowerShell 会吞 python stdout）。一切测试在 0.82 跑。
- 本机 ssh 助手：`light-merge/_r161_scratch/d_remote.py`（paramiko，密码从项目根 `.env` 读），
  用法：`d_remote.run('82', cmd, timeout)` 返回 `(rc, out, err)`。也可用你自己惯常的方式。

## 问题定位

- 文件：`tests/unit/test_R160_E5协程库.py:88-96`

```python
def test_C1_骨架文件存在且为纯CRLF():
    """新 .light 必须 CRLF（铁律 10）。判据 = crlf 计数 == 总 LF 计数且 > 0。"""
    assert os.path.exists(_协程模块), ...
    数据 = open(_协程模块, 'rb').read()
    crlf = 数据.count(b'\r\n')
    总lf = 数据.count(b'\n')
    assert crlf > 0 and crlf == 总lf, (
        f"协程.light 不是纯 CRLF：crlf={crlf} / 总LF={总lf}（铁律 10：新 .light 必须 CRLF）")
```

- 症状（0.82 实测）：git 索引存的是 LF（`git ls-files --eol` → `i/lf`），Windows 靠
  `core.autocrlf=true` 在工作树转 CRLF，FreeBSD 干净 clone 无 autocrlf ⇒ 拿到 LF ⇒ `crlf=0` ⇒ 断言失败。
- 该红在**真 R160（`444d765a9`）树上同样失败**（已实测），非 R161 引入。
- 附带事实：`stdlib/协程.light` 内容本身没坏、没丢 CRLF——纯检出形态差异。

## 建议改法（唯一改动点 = 测试判据）

1. 判据从「纯 CRLF」放宽为「**行尾一致**」：纯 CRLF 或纯 LF 均放行，**混搭**（`0 < crlf < 总lf`）才红：

```python
    crlf = 数据.count(b'\r\n')
    总lf = 数据.count(b'\n')
    纯crlf = crlf > 0 and crlf == 总lf
    纯lf = crlf == 0 and 总lf > 0
    assert 纯crlf or 纯lf, (
        f"协程.light 行尾不一致：crlf={crlf} / 总LF={总lf}"
        f"（铁律 10：新 .light 行尾必须统一，CRLF 或 LF 均可）")
```

2. 同步更新 docstring 第一行（保留「铁律 10」引用，改述为「行尾统一」）。
3. **不要**改 `stdlib/协程.light` 本身；**不要**动 `.gitattributes`（全局 `*.light eol=crlf`
   会影响全部 2470 个文件的检出形态，牵动面远超两个测试——这是已评估否决的方案）。

## 验收（0.82 实测，据实报告）

```bash
# 1) 目标用例转绿
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python -m pytest \
    tests/unit/test_R160_E5协程库.py::test_C1_骨架文件存在且为纯CRLF -n 0 -p no:randomly -q
# 期望：1 passed

# 2) 整文件无连带（段二号门启用，全量 15 例）
cd /home/ai/r161clean && R160_E5_SEG2=1 /home/ai/lm082_venv/bin/python -m pytest \
    -n 0 -p no:randomly -q tests/unit/test_R160_E5协程库.py
# 修复前基线：1 failed, 10 passed, 4 xfailed；期望修复后：0 failed, 11 passed, 4 xfailed
```

## 纪律红线

- **不 commit、不 push**（任何仓）。改完把 diff 交回，由业主决定提交。
- `git add` 只用显式文件名，绝不 `git add .`。
- 凭证（`.env`）绝不进 commit、不进日志、不进报告。
- 只改上述一个测试函数；不顺手改其它用例。

## 交付物

1. `tests/unit/test_R160_E5协程库.py` 的修改（git diff）。
2. 简短报告：改法、两条验收命令的原始输出（rc + 汇总行）。
