# -*- coding: utf-8 -*-
"""T-0390 · slow 用例的超时提限接线（tests/conftest.py）必须是活的。

## 这条护栏钉的是什么

pyproject 的 addopts 写死 `--timeout=60`（每用例上限）。一批用例在 0.88 全量
`-n 6` 下实测 52–61s，60s 正好压在它们头上；机器被别的 agent 挤到 load≈15 时
就在 59–61s 之间随机翻红 —— 同一份提交三轮全量的失败集合互不相同
（T-0383 实测 21/19/14，来回翻 11 条）。

修法：`tests/conftest.py::pytest_collection_modifyitems` 给标了 `slow` 的 item
合成一条 `timeout` marker（默认 600s，`LIGHT_SLOW_TIMEOUT` 可覆盖），
**全局 `--timeout=60` 原样保留**。pytest-timeout 的取值顺序是
「item 上的 timeout marker > 命令行 --timeout」，所以效果是「只有慢用例被提限，
快用例卡死仍旧 60s 就掐」——这正是不许「直接删掉 --timeout=60」的那条红线。

## 为什么真跑子进程、而且分两次跑

要钉的是 pytest-timeout 的取值契约，不是本仓某行代码，所以得真跑到「超时真的发生
或真的没发生」。但不能把「该绿」和「该红」两条探针塞进**同一个** pytest 会话：
pytest-timeout 的 thread 方法（Windows 默认）一旦触发就 dump 栈并 `os._exit`，
整个会话直接结束，第二条探针根本轮不到 —— 第一版就是这么假的（诊断记录见
本文件末尾注释）。拆成两次独立会话，每次只有一条探针，判据才干净。

探针用 `time.sleep` 而不是真起编译子进程：超时只跟墙钟有关，与用例内容无关，
两条 sleep 合计 5s，比拉一份真产物（4–8s/条 + 编译抖动）可靠得多。
"""

import os
import subprocess
import sys
from pathlib import Path

_仓根 = Path(__file__).resolve().parents[2]

_慢探针 = '''\
import time
import pytest


@pytest.mark.slow
def test_标了slow的慢用例():
    time.sleep(2.5)
'''

_快探针 = '''\
import time


def test_没标slow的慢用例():
    time.sleep(2.5)
'''


def _跑一条探针(tmp_path, 文件名, 内容):
    """在临时目录真跑一次 pytest：全局超时压到 1s，返回 (rc, 输出文本)。

    conftest 用**本仓 tests/conftest.py 的副本**，这样测的就是真实接线，
    而不是在这里重抄一遍逻辑。临时目录自成 rootdir，不继承仓库级 addopts。
    """
    沙盒 = tmp_path / 文件名.replace(".py", "")
    测试目录 = 沙盒 / "tests"
    测试目录.mkdir(parents=True)
    (测试目录 / "conftest.py").write_text(
        (_仓根 / "tests" / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
    目标 = 测试目录 / 文件名
    目标.write_text(内容, encoding="utf-8")

    p = subprocess.run(
        [sys.executable, "-m", "pytest", str(目标), "-q", "-p", "no:cacheprovider",
         "-o", "addopts=", "-o", "timeout=1", "-o", "markers=slow: 慢测试"],
        cwd=str(沙盒), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
        env={**os.environ, "LIGHT_SLOW_TIMEOUT": "600"},
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def test_标slow的用例能活过全局1秒超时(tmp_path):
    """正向：slow 用例拿到 600s（marker 压过命令行的 --timeout=1），必须全绿。"""
    rc, 文本 = _跑一条探针(tmp_path, "test_慢.py", _慢探针)
    assert rc == 0, f"slow 用例应被提限到 600s、跑满 2.5s 后绿，实际 rc={rc}：\n{文本[-3000:]}"
    assert "1 passed" in 文本, f"期望 1 passed：\n{文本[-3000:]}"


def test_没标slow的用例仍被全局1秒掐红(tmp_path):
    """反向：没标 slow 的用例不受提限影响，1s 就该红。

    这条是「提限没被写成全局放宽」的反证 —— 若有人图省事把 `--timeout=60` 删了或
    改成 `--timeout=600`，这条探针会变绿，护栏当场立红。

    ⚠️ 判据只断「rc≠0 + 出现 Timeout 横幅」，**不断言 pytest 的汇总行**：thread 方法
    超时后是 `os._exit`，整轮直接被带走，连 "1 failed" 都不会打印（这正是下面留档
    的那条踩坑记录）。
    """
    rc, 文本 = _跑一条探针(tmp_path, "test_快.py", _快探针)
    assert rc != 0, f"未标 slow 的用例应被 1s 掐红，实际 rc={rc}：\n{文本[-3000:]}"
    assert "Timeout" in 文本, f"红的原因应是超时：\n{文本[-3000:]}"


# ── 第一版为什么假绿（留档，避免下次再踩）──────────────────────────────────
# 第一版把「标 slow 的 2.5s 探针」和「没标 slow 的 2.5s 探针」放在**同一个**会话里，
# 期望「1 passed + 1 failed」。实测是「2 个 Timeout 横幅、0 passed」：pytest-timeout
# 的 thread 方法（Windows 默认，也是本仓 CI 在 Windows 上的默认）触发后会 dump
# 全部线程栈并 `os._exit`，整轮直接死掉，先红的把还没跑的也一起带走 ——
# 于是「一绿一红」永远凑不出来。这不是接线坏了，是探针设计错了。
# 拆成两次单测例会话后，正向（slow 活下来）与反向（非 slow 被掐）各自可判。
