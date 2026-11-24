# -*- coding: utf-8 -*-
"""T-0465：`light ai check` 冷启动延迟实测（P50/P90）。

口径：用户在真实仓库里的一条命令 = 起一个 Python 子进程跑 ``python -m cli.light``。
所以计时包含解释器启动；用 ``judge.build_argv`` / ``judge.build_env`` 保证与判定器
调用 CLI 的方式完全一致（不额外加 PYTHONPATH 之类的偏差）。

输入文件取 ``benchmarks/light_agent/stub_answers`` 里每条任务最后一次成功补丁
（等价于一份「正常的光明源码」），既不是空文件也不是必然报错的坏文件。

用法::

    python docs/bench/ai_check_latency.py --reps 3 --out docs/bench/ai_check_latency_20261125.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "benchmarks" / "light_agent"


def load_judge():
    spec = importlib.util.spec_from_file_location(
        "la_judge", BENCH_DIR / "run_benchmarks_agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pick_source(task: dict) -> Path | None:
    attempts = task.get("stub", {}).get("attempts") or []
    if not attempts:
        return None
    files = attempts[-1].get("files") or {}
    rel = files.get(task["entry"]) or next(iter(files.values()), None)
    return BENCH_DIR / rel if rel else None


def time_once(judge, template: str, entry: str, workspace: Path) -> dict:
    argv = judge.build_argv(template, entry, workspace, REPO_ROOT)
    started = time.monotonic()
    proc = subprocess.run(argv, cwd=str(workspace), env=judge.build_env(REPO_ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)
    elapsed = round(time.monotonic() - started, 4)
    diags = 0
    codes: list[str] = []
    ok = None
    try:
        payload = json.loads(proc.stdout)
        items = payload.get("diagnostics", [])
        diags = len(items)
        codes = [d.get("code") for d in items if d.get("code")]
        ok = payload.get("ok")
    except Exception:
        pass
    return {"elapsed": elapsed, "rc": proc.returncode, "diagnostics": diags, "codes": codes,
            "ok": ok}


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    idx = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[idx]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="docs/bench/ai_check_latency_20261125.json")
    args = ap.parse_args(argv)

    judge = load_judge()
    tasks = [json.loads(ln) for ln in
             (BENCH_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    variants = ("relpath", "abspath", "abspath_run")
    work_root = Path(tempfile.mkdtemp(prefix="t0465-latency-"))
    rows = []
    for task in tasks:
        src = pick_source(task)
        if src is None or not src.is_file():
            rows.append({"id": task["id"], "skipped": f"没有可用的输入文件: {src}"})
            continue
        workspace = work_root / task["id"]
        workspace.mkdir(parents=True, exist_ok=True)
        target = workspace / task["entry"]
        target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        row = {"id": task["id"], "samples": {}}
        for name in variants:
            # 相对路径是冷启动 agent 最自然的写法；绝对路径是「文件在 worktree 里」时唯一能跑通的写法。
            template = {
                "relpath": "light ai check {entry} --json",
                "abspath": f"light ai check {target.as_posix()} --json",
                "abspath_run": f"light ai check {target.as_posix()} --json --run",
            }[name]
            samples = [time_once(judge, template, task["entry"], workspace)
                       for _ in range(args.reps)]
            row["samples"][name] = samples
        rows.append(row)

    summary = {}
    for name in variants:
        vals = [s["elapsed"] for r in rows if "samples" in r for s in r["samples"][name]]
        rcs = [s["rc"] for r in rows if "samples" in r for s in r["samples"][name]]
        diag_counts = [s["diagnostics"] for r in rows if "samples" in r for s in r["samples"][name]]
        oks = [s.get("ok") for r in rows if "samples" in r for s in r["samples"][name]]
        summary[name] = {
            "n": len(vals),
            "p50": round(pct(vals, 0.5), 3),
            "p90": round(pct(vals, 0.9), 3),
            "mean": round(statistics.mean(vals), 3) if vals else None,
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "rc_histogram": {str(rc): rcs.count(rc) for rc in sorted(set(rcs))},
            "ok_true": sum(1 for o in oks if o is True),
            "diagnostics_sum": sum(diag_counts),
            "diagnostics_nonzero_samples": sum(1 for d in diag_counts if d),
        }

    payload = {
        "probe": "T-0465 ai check latency",
        "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "reps_per_task": args.reps,
        "tasks": len(tasks),
        "summary": summary,
        "rows": rows,
    }
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
