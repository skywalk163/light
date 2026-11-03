# -*- coding: utf-8 -*-
"""sibling lightharness 可用性判定：缺失时**显式 skip**（不静默、不 collect error）。

## 为什么是 skip，而不是在 CI 里 checkout sibling（T-0241 裁决）

`tests/unit/test_builtins_drift.py` 与 `tests/unit/test_LH34_中文关键字参数.py` 里有
几条用例要读 `<本仓>/../lightharness/stdlib/builtins.py`（LH 运行时副本）。GitHub
run 41289797116 上这 9 条红（7 errors + 2 failed）签名全是
`FileNotFoundError: /home/runner/work/light/lightharness/stdlib/builtins.py`——
runner 只 checkout 本仓，sibling 天然不存在。

- **不 checkout sibling**：那等于把另一个仓的失败面接进本仓 CI，红了分不清是谁的账
  （跨仓同步该由 lightharness 仓自己的门禁负责）。
- **不静默跳过 / 不 collect error**：缺件是环境事实，不是本仓代码坏了；skip 的
  reason 会出现在 pytest 的 SKIPPED 汇总与 CI 日志里，看得见。
- **gitea 权威机有 sibling**：那几条在那边照常真跑，跨仓 drift 仍有真哨兵。

本地/权威机把 lightharness 放在 `light/../lightharness`（或做目录联接）即恢复真跑。
"""

import os

import pytest


def 缺失原因(lh_path):
    """sibling 副本缺失时返回可读原因，可用时返回 None。"""
    if os.path.isfile(lh_path):
        return None
    return (
        "需要 sibling lightharness（%s 不存在）：跨仓副本比对不在本仓 CI 的判绿范围，"
        "gitea 权威机有 sibling、那边照常真跑" % lh_path
    )


def 缺失则skip(lh_path):
    """用例体内调用：缺失即 pytest.skip，跳过汇总里可见。"""
    原因 = 缺失原因(lh_path)
    if 原因:
        pytest.skip(原因)
