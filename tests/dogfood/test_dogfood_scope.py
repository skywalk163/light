# -*- coding: utf-8 -*-
"""T-0387 回归：dogfood 的 skip 只能作用于 tests/dogfood/ 自己。

T-0322 的 conftest 在 `pytest_collection_modifyitems` 里对传入的 `items` 全量
`add_marker(skip)`，而 `items` 是整个 session 的收集结果。0.88 验收现场没有同级
`lightharness`，于是全仓 10531 条用例被打上 skip，rc=0 —— 全量假绿。

本用例把真实 conftest/_dogfood/用例拷进一个临时仓，放一条同 session 的兄弟用例，
在没有 lightharness 的条件下跑混跑，验证：
  1) 兄弟用例照常真跑（passed），不被 dogfood 的 skip 连坐；
  2) dogfood 目录自己仍然是 skip（不是报错、也不是消失）。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_COPY = ("conftest.py", "_dogfood.py", "baseline.json", "test_lightharness_smoke.py")

SIBLING = '''\
def test_sibling_runs():
    assert True
'''


def _build_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    dogfood = repo / "tests" / "dogfood"
    dogfood.mkdir(parents=True)
    for name in _COPY:
        shutil.copy2(HERE / name, dogfood / name)
    (repo / "tests" / "test_sibling.py").write_text(SIBLING, encoding="utf-8")
    return repo


def test_混跑不连坐(tmp_path):
    repo = _build_fixture_repo(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # 显式指到不存在的路径：无论本机有没有 lightharness，都稳定走 skip 分支
    env["LIGHTHARNESS_DIR"] = str(tmp_path / "no-such-lightharness")

    cp = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
         "-rs", "tests/test_sibling.py", "tests/dogfood"],
        cwd=str(repo), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, f"混跑应 rc=0（dogfood 只是 skip，不是失败）：\n{out}"

    passed = re.search(r"(\d+) passed", out)
    assert passed and int(passed.group(1)) >= 1, (
        f"兄弟用例没跑起来（被 dogfood 的 skip 连坐）：\n{out}"
    )
    skips = [ln for ln in out.splitlines() if ln.startswith("SKIPPED")]
    assert skips, f"dogfood 目录在没有 lightharness 时应 skip 而不是报错：\n{out}"
    assert all("dogfood" in ln for ln in skips), (
        f"有 dogfood 之外的用例被跳过（skip 漏出本目录）：\n" + "\n".join(skips)
    )
