# -*- coding: utf-8 -*-
"""Light Agent Benchmark 的骨架自检（不跑任何模型、不联网）。

四条硬要求：
  1. ``tasks.jsonl`` 每行都能 ``json.loads``，字段齐全、枚举合法、配额对得上；
  2. 四类 ``error_class`` 都有足够的题量，且每类至少有一条「第一次错、第二次对」的重试卡；
  3. ``--model stub`` 跑全 120 条必须全绿（证明 harness 本身可离线判定）；
  4. 故意破坏一条 fixture，对应任务必须判失败（证明断言真的在起作用）。

外加一条入库自检：``setup.from`` 指向的起始件不仅要在磁盘上，还必须被 git 跟踪。
仓根 ``.gitignore`` 有全局 ``*.txt``／``*.json``，起始件被它吃掉时本地测试照样绿
（文件还在磁盘上），合入或换机才炸——T-0381 的 ``fixtures/数据.txt`` 就是这么漏的。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = REPO_ROOT / "benchmarks" / "light_agent"
RUNNER = BENCH_DIR / "run_benchmarks_agent.py"
TASKS_FILE = BENCH_DIR / "tasks.jsonl"

CATEGORIES = {"新建", "修改", "修复", "重构"}
ERROR_CLASS_MIN = {"新建": 40, "pyism": 30, "alias": 20, "stdlib": 30}
LEVEL_MIN = {"L1": 60, "L2": 40, "L3": 20}
KINDS = {"可运行", "可编译", "可检查"}
REQUIRED = ("id", "prompt", "entry", "paths", "expected", "difficulty",
            "category", "error_class")
REQUIRED_EXPECTED = ("kind", "cmd", "files")
MIN_TOTAL = 120
MIN_RETRY_CARDS = 30


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src")])
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run(*args: str, timeout: float = 600.0) -> subprocess.run:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=str(REPO_ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _load_tasks() -> list[dict]:
    tasks = []
    for lineno, line in enumerate(TASKS_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line:
            tasks.append((lineno, json.loads(line)))
    assert tasks, "tasks.jsonl 是空的"
    return tasks


def test_tasks_jsonl_is_parseable_and_complete():
    """每行合法 JSON、字段齐全、枚举合法、总量与难度配额对得上。"""
    rows = _load_tasks()
    seen_ids = set()
    for lineno, task in rows:
        for key in REQUIRED:
            assert key in task, f"第 {lineno} 行缺字段 {key}"
        expected = task["expected"]
        for key in REQUIRED_EXPECTED:
            assert key in expected, f"第 {lineno} 行 expected 缺字段 {key}"

        assert task["id"] not in seen_ids, f"任务 id 重复: {task['id']}"
        seen_ids.add(task["id"])

        assert task["category"] in CATEGORIES, f"{task['id']} category 非法"
        assert task["difficulty"] in ("L1", "L2", "L3"), f"{task['id']} difficulty 非法"
        assert expected["kind"] in KINDS, f"{task['id']} expected.kind 非法"
        assert isinstance(task["paths"], list) and task["paths"], f"{task['id']} paths 为空"
        assert task["entry"] in task["paths"], f"{task['id']} entry 不在 paths 里"
        assert isinstance(expected["files"], list) and expected["files"], \
            f"{task['id']} expected.files 为空"
        for spec in expected["files"]:
            assert "path" in spec, f"{task['id']} 的 files 断言缺 path"

    assert len(rows) >= MIN_TOTAL, f"任务数应 ≥{MIN_TOTAL}，实际 {len(rows)}"

    levels = {"L1": 0, "L2": 0, "L3": 0}
    for _, task in rows:
        levels[task["difficulty"]] += 1
    for level, minimum in LEVEL_MIN.items():
        assert levels[level] >= minimum, f"{level} 只有 {levels[level]} 条，要求 ≥{minimum}"


def test_error_class_quota_and_offline_shape():
    """四类 error_class 都够量；命令全以 light 开头、不联网；重试卡够数。"""
    rows = _load_tasks()
    classes = {key: 0 for key in ERROR_CLASS_MIN}
    retry_cards = 0
    for lineno, task in rows:
        assert task["error_class"] in ERROR_CLASS_MIN, \
            f"第 {lineno} 行 error_class 非法: {task['error_class']}"
        classes[task["error_class"]] += 1

        cmd = task["expected"]["cmd"]
        assert cmd.split()[0] == "light", \
            f"{task['id']} 的 expected.cmd 必须以 light 开头（离线判定）: {cmd}"
        for token in ("curl", "wget", "http://", "https://"):
            assert token not in cmd, f"{task['id']} 命令里出现联网字样: {cmd}"

        attempts = (task.get("stub") or {}).get("attempts") or []
        assert attempts, f"{task['id']} 没有任何 stub.attempts（--model stub 无从重放）"
        assert all(item.get("files") for item in attempts), \
            f"{task['id']} 有 attempt 没写 files"
        if len(attempts) >= 2:
            retry_cards += 1

    for cls, minimum in ERROR_CLASS_MIN.items():
        assert classes[cls] >= minimum, f"error_class={cls} 只有 {classes[cls]} 条，要求 ≥{minimum}"
    assert retry_cards >= MIN_RETRY_CARDS, \
        f"attempts≥2 的重试卡只有 {retry_cards} 条，要求 ≥{MIN_RETRY_CARDS}"


@pytest.mark.timeout(900)
def test_stub_runs_all_tasks_green():
    """--model stub 离线跑全量任务，必须全绿。"""
    proc = _run("--model", "stub", "--json", "--jobs", "6")
    assert proc.returncode == 0, f"stub 判定未全绿\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    payload = json.loads(proc.stdout)
    assert payload["model"] == "stub"
    summary = payload["summary"]
    rows = _load_tasks()
    assert summary["total"] == len(rows) >= MIN_TOTAL
    assert summary["passed"] == summary["total"]
    assert summary["failed"] == 0
    assert summary["pass_rate"] == 1.0
    # 重试是「第一次错、第二次对」真跑出来的，不是写死的常量。
    assert summary["retries_total"] >= MIN_RETRY_CARDS

    expected_ids = [task["id"] for _, task in rows]
    got_ids = [item["id"] for item in payload["tasks"]]
    assert got_ids == expected_ids, "结果顺序应与 tasks.jsonl 一致"

    for item in payload["tasks"]:
        for key in ("id", "ok", "stage", "error_code", "error_class",
                    "retries", "elapsed"):
            assert key in item, f"{item['id']} 的 --json 结果缺 {key}"
        assert item["ok"] is True
        assert item["stage"] == "ok"
        assert isinstance(item["retries"], int) and item["retries"] >= 0
        assert isinstance(item["elapsed"], (int, float)) and item["elapsed"] > 0


def test_summary_groups_pass_rate_by_error_class():
    """summary 必须按 error_class 分组给通过率，且四类都在。"""
    picks = ["LA-021", "LA-057", "LA-082", "LA-096"]
    proc = _run("--model", "stub", "--json", "--jobs", "2",
                "--task", picks[0], "--task", picks[1], "--task", picks[2],
                "--task", picks[3])
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)["summary"]

    by_class = summary["by_error_class"]
    assert set(by_class) == set(ERROR_CLASS_MIN), by_class
    for cls, item in by_class.items():
        assert item["total"] == 1, f"{cls} 分组条数不对: {item}"
        assert item["passed"] == 1 and item["failed"] == 0
        assert item["pass_rate"] == 1.0

    # 全量口径下每类的总量要和 tasks.jsonl 里的打标对得上（这里只验形状）。
    assert sum(item["total"] for item in by_class.values()) == summary["total"]


def test_stub_collects_retries_and_error_codes():
    """重试次数和错误码是真采集出来的，不是写死的常量。"""
    proc = _run("--model", "stub", "--json", "--jobs", "4",
                "--task", "LA-002", "--task", "LA-015")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    by_id = {item["id"]: item for item in payload["tasks"]}

    # LA-002：第一次写成开区间（45），第二次才改对 → 1 次重试，失败原因是输出不符。
    assert by_id["LA-002"]["retries"] == 1
    assert by_id["LA-002"]["error_code"] == "LA_E_STDOUT"
    assert [a["ok"] for a in by_id["LA-002"]["attempts"]] == [False, True]

    # LA-015：第一次改了名但没定义（运行期名称错误），第二次复用已有变量 → 错误码来自语言侧。
    assert by_id["LA-015"]["retries"] == 1
    assert by_id["LA-015"]["error_code"].startswith("L"), by_id["LA-015"]
    assert [a["ok"] for a in by_id["LA-015"]["attempts"]] == [False, True]

    assert payload["summary"]["retries_total"] == 2
    # 只挑了两条任务，平均 retry 按子集口径算：2/2 = 1.0。
    assert payload["summary"]["avg_retries"] == 1.0


@pytest.mark.timeout(300)
def test_broken_fixture_makes_task_fail():
    """把 LA-006 依赖的数据文件改坏，重放同一份补丁必须判失败。"""
    with tempfile.TemporaryDirectory(prefix="light-agent-bench-broken-") as tmp:
        copy = Path(tmp) / "bench"
        shutil.copytree(BENCH_DIR, copy)
        (copy / "fixtures" / "数据.txt").write_text("99\n", encoding="utf-8")

        broken = _run("--model", "stub", "--json", "--jobs", "1",
                      "--bench-dir", str(copy), "--task", "LA-006")
        assert broken.returncode == 1, (
            f"破坏 fixture 后仍判通过，断言没有生效\nstdout:\n{broken.stdout}")
        payload = json.loads(broken.stdout)
        item = payload["tasks"][0]
        assert item["id"] == "LA-006"
        assert item["ok"] is False
        assert item["error_code"] == "LA_E_STDOUT"
        assert item["attempts"][-1]["detail"]

        # 同一份补丁在未破坏的 benchmark 上必须仍然通过（对照组）。
        healthy = _run("--model", "stub", "--json", "--jobs", "1", "--task", "LA-006")
        assert healthy.returncode == 0, healthy.stdout
        assert json.loads(healthy.stdout)["tasks"][0]["ok"] is True


def test_unwired_model_is_reported_not_faked():
    """未接线的模型必须明确报错，不能假装跑出通过率。"""
    proc = _run("--model", "deepseek-chat")
    assert proc.returncode == 2
    assert "未接线" in proc.stderr
    assert "pass_rate" not in proc.stdout
    assert "deepseek-chat" in proc.stderr


def _git_tracked_bench_files() -> set[str] | None:
    """benchmark 目录下被 git 跟踪的文件（相对仓根、正斜杠）；没有 git 环境返回 None。"""
    git = shutil.which("git")
    if not git or not (REPO_ROOT / ".git").exists():
        return None
    proc = subprocess.run(
        [git, "-C", str(REPO_ROOT), "-c", "core.quotepath=false",
         "ls-files", "-z", "--", "benchmarks/light_agent"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60.0,
    )
    if proc.returncode != 0:
        return None
    return {item for item in proc.stdout.split("\0") if item}


def test_setup_fixtures_exist_and_are_tracked():
    """起始件必须在磁盘上，而且真的进了仓（防 *.txt 忽略规则静默吃掉）。"""
    refs = sorted({
        step["from"]
        for _, task in _load_tasks()
        for step in (task.get("setup") or [])
        if isinstance(step, dict) and step.get("from")
    })
    assert refs, "没有任何任务用到起始件，基准集已经不覆盖「改/修/重构」"

    missing = [ref for ref in refs if not (BENCH_DIR / ref).is_file()]
    assert not missing, f"起始件不存在: {missing}"

    tracked = _git_tracked_bench_files()
    if tracked is None:
        pytest.skip("没有可用的 git 工作树，跳过「起始件是否入库」检查")

    expected = {f"benchmarks/light_agent/{ref}" for ref in refs}
    untracked = sorted(expected - tracked)
    assert not untracked, (
        "起始件没进 git（多半被仓根忽略规则吃掉，本地却因为文件还在磁盘上而假绿）：\n  "
        + "\n  ".join(untracked)
    )
