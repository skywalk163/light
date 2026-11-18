# -*- coding: utf-8 -*-
"""tests/dogfood 的 pytest 接线：环境适配 + 报告汇总。

关于仓库级 addopts
------------------
仓库根 pyproject.toml 的 addopts 是
`--tb=short --durations=15 --ignore=tests/archive --timeout=60 -n 4 --dist=loadscope`，
其中 --timeout / -n / --dist 分别需要 pytest-timeout / pytest-xdist 插件。
本机（Windows）没装这两个插件，`python -m pytest -q tests/dogfood/` 会在解析命令行
阶段就直接报 `unrecognized arguments: --timeout=60 -n --dist=loadscope` —— 与产物无关。
pytest 9 又禁止普通 addoption 注册小写短选项（`-n` 报 lowercase short options are
reserved），所以不能靠「占位注册」兜住 -n。

本卡不允许改 pyproject.toml，于是两层处理：
  1) tests/dogfood/pytest.ini —— 让这个目录自带判据配置，rootdir 局部化，不继承
     仓库级的插件依赖（26 条用例串行跑，每条 subprocess 自带超时）；
  2) pytest_load_initial_conftests —— 兜底：万一 inifile 仍指向 pyproject.toml，
     把本机没装插件的那几个参数从 argv 里摘掉，其余 addopts 原样保留。
插件已安装的机器上两层都是 no-op，xdist/timeout 照常接管。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dogfood import (  # noqa: E402
    ALL_MODULES, LIGHTHARNESS_DIR, SAMPLE, SKIP_TEXT,
    clear_parts, merged_results, write_report,
)


def pytest_load_initial_conftests(early_config, parser, args):
    """兜底：剥掉本机没有插件支撑的 addopts 参数（含 `-n 4` 的取值）。"""
    drop = set()
    if importlib.util.find_spec("pytest_timeout") is None:
        drop.add("--timeout")
    if importlib.util.find_spec("xdist") is None:
        drop.update({"-n", "--numprocesses", "--dist"})
    if not drop:
        return

    cleaned = []
    i = 0
    while i < len(args):
        arg = args[i]
        name = arg.split("=", 1)[0]
        if name in drop:
            if "=" not in arg and i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 1  # 吃掉 `-n 4` / `--timeout 60` 的取值
            i += 1
            continue
        cleaned.append(arg)
        i += 1
    args[:] = cleaned


def pytest_report_header(config):
    if not LIGHTHARNESS_DIR.is_dir():
        return f"dogfood: {SKIP_TEXT}（LIGHTHARNESS_DIR={LIGHTHARNESS_DIR}）"
    return (f"dogfood: lightharness={LIGHTHARNESS_DIR} | "
            f"工程体模块 {len(ALL_MODULES)} 个 | 确定化抽样 {len(SAMPLE)} 个")


HERE = Path(__file__).resolve().parent

# 缺 lightharness 时也必须跑的文件：它验证的正是「缺 lightharness 时 skip 不许越界」，
# 自己再被 skip 就等于没有守卫（T-0387）。它不依赖本机 lightharness。
ALWAYS_RUN = frozenset({"test_dogfood_scope.py"})


def _in_dogfood(item) -> bool:
    """这条用例是否收集自 tests/dogfood/ 本身。

    `pytest_collection_modifyitems` 拿到的是**整个 session** 的 items，不是本目录的；
    T-0322 当初直接全量 add_marker，导致 0.88 在没有 lightharness 的验收现场把
    全仓 10531 条用例一起 skip，rc=0 假绿（T-0387）。这里按路径收口。
    """
    fspath = getattr(item, "path", None) or getattr(item, "fspath", None)
    if fspath is None:
        return False
    try:
        p = Path(str(fspath)).resolve()
    except OSError:
        return False
    return p == HERE or HERE in p.parents


def pytest_collection_modifyitems(config, items):
    if LIGHTHARNESS_DIR.is_dir():
        return
    scoped = [
        item for item in items
        if _in_dogfood(item)
        and Path(str(getattr(item, "fspath", "") or "")).name not in ALWAYS_RUN
    ]
    if not scoped:
        return
    print(f"\n{SKIP_TEXT}")
    marker = pytest.mark.skip(reason=SKIP_TEXT)
    for item in scoped:
        item.add_marker(marker)
    if len(scoped) != len(items):
        print(f"[dogfood] 只跳过本目录 {len(scoped)} 条；同 session 另外 "
              f"{len(items) - len(scoped)} 条不受影响")


def pytest_sessionstart(session):
    # 只在 master 清一次分片；xdist worker 有 workerinput，跳过以免并发删文件
    if not hasattr(session.config, "workerinput"):
        clear_parts()


def pytest_sessionfinish(session, exitstatus):
    if hasattr(session.config, "workerinput"):
        return  # 报告由 master 统一落盘
    write_report(merged_results())
