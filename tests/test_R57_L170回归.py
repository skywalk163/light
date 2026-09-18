# -*- coding: utf-8 -*-
"""R57 任务3：L-170 复现用例挂 tests/（G7 覆盖缺口收口）。

背景：
  R54 修复 L-170（核心 arity-2 动词作变量名用于「下标/成员赋值目标」时被
  静默编译成比较表达式），复现用例 `examples/test_L170.light` 只放在
  examples/ —— light-merge 的全量 pytest 只收集 `tests/`，examples/*.light
  不进全量门。一旦该修复将来被回退/破坏，全量门**不会红**（G7 缺口）。

本文件把 examples/test_L170.light 的断言逻辑同步进 tests/：
  · 源码内嵌（不依赖被 .gitignore 忽略的 examples/test_*.light，克隆即用）；
  · 两条腿（run + product），沿用 tests/test_frontend_blockers_run.py 的机制——
    两条腿 sys.path 铺法不同，产物自洽问题只有 product 腿能暴露；
  · 断言运行时输出 `L170-OK`（examples 内已有 如果/抛出 显式断言，
    静默变比较会以抛错形式暴露，而非仅看编译产物）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}

# 与 examples/test_L170.light 逐字一致（R54 交付的复现用例源码）
L170_SOURCE = '''\
段落 主:
  设 映射 为 {}
  设 k 为 "a"
  映射[k] 为 99
  如果 映射[k] != 99: 抛出 "L170_下标赋值_未生效"

  映射之x 为 7
  如果 映射["x"] != 7: 抛出 "L170_之成员赋值_未生效"

  映射.项 为 8
  如果 映射["项"] != 8: 抛出 "L170_dot成员赋值_未生效"

  设 筛选 为 {}
  设 k2 为 "b"
  筛选[k2] 为 2
  如果 筛选[k2] != 2: 抛出 "L170_筛选下标赋值_未生效"

  打印("L170-OK")
'''


def _write_src(tmpdir: Path) -> Path:
    src = tmpdir / 'test_L170_regression.light'
    src.write_text(L170_SOURCE, encoding='utf-8')
    return src


def _run_light(source_path: Path):
    """run 腿：python -m cli.light run 源码.light（与 lightharness 运行.py 同一入口）。"""
    r = subprocess.run(
        [sys.executable, '-m', 'cli.light', 'run', str(source_path)],
        capture_output=True, text=True, encoding='utf-8',
        cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
    )
    return r.returncode, r.stdout, r.stderr


def _run_product(source_path: Path, tmpdir: Path):
    """product 腿：compile -o 产物.py 后独立执行。"""
    out_py = tmpdir / 'product.py'
    c = subprocess.run(
        [sys.executable, '-m', 'cli.light',
         'compile', str(source_path), '-o', str(out_py)],
        capture_output=True, text=True, encoding='utf-8',
        cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
    )
    assert c.returncode == 0, f"[compile] 退出码 {c.returncode}:\n{c.stderr}\n{c.stdout}"
    assert out_py.exists(), f"产物未生成:\n{c.stdout}"
    r = subprocess.run(
        [sys.executable, str(out_py)],
        capture_output=True, text=True, encoding='utf-8',
        cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
    )
    return r.returncode, r.stdout, r.stderr


def test_L170_赋值真生效_运行时输出L170_OK():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = _write_src(Path(tmpdir))
        for leg, runner in (('run', _run_light),
                            ('product', lambda p: _run_product(p, Path(tmpdir)))):
            rc, out, err = runner(src)
            assert rc == 0, f'[{leg}] 退出码 {rc}:\n{err}\n{out}'
            assert 'L170-OK' in out, (
                f'[{leg}] 未输出 L170-OK（赋值可能被静默编译成比较）:\n{out[-500:]}'
            )
            for marker in ('L170_下标赋值_未生效', 'L170_之成员赋值_未生效',
                           'L170_dot成员赋值_未生效', 'L170_筛选下标赋值_未生效'):
                assert marker not in (out + err), f'[{leg}] 出现失败标记 {marker}'
