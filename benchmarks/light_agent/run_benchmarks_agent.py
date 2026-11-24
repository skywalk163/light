# -*- coding: utf-8 -*-
"""
Light Agent Benchmark —— 面向 AI 编程能力的可离线判定集。

一张卡回答一个问题：给同一个 Agent 同一句 prompt，它一次能不能写对？
本脚本只提供**判定骨架**，不接任何真实模型：

  * ``--model stub``（默认）用 ``stub_answers/`` 里记录好的补丁文件重放，
    在临时工作区跑 ``light check`` / ``light run`` / ``light compile``，
    只用「进程返回码 + 文件内容断言」判对错，不调模型、不联网、不用 LLM 打分。
  * ``--model <其它名字>`` 是给后续「模型接入」卡留的接口；现在未接线，
    直接报错退出（rc=2），不会假装跑出结果。

用法::

    python benchmarks/light_agent/run_benchmarks_agent.py --model stub
    python benchmarks/light_agent/run_benchmarks_agent.py --model stub --json
    python benchmarks/light_agent/run_benchmarks_agent.py --model stub --task LA-006

判据口径见 ``docs/LightAgentBench说明.md``。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BENCH_DIR = HERE
DEFAULT_REPO_ROOT = HERE.parents[1]
DEFAULT_TIMEOUT = 30.0

CATEGORIES = ("新建", "修改", "修复", "重构")
DIFFICULTIES = ("L1", "L2", "L3")
KINDS = ("可运行", "可编译", "可检查")
# error_class 回答的是「Agent 到底为什么会错」，与 category（题目形态）正交：
#   新建   —— 从零写一个能跑的程序，题面不给骨架
#   pyism  —— 题面用 Python 词汇诱导（函数/for/range/len/sum/str/%//…），落到光明要换写法
#   alias  —— 同一语义的别名/双字体诱惑（遍历 … 从 … 到、输出、若…则、重复 N 次、全角符号）
#   stdlib —— 必须用对 stdlib 函数名（读取文件/写入文件/转整数/解析JSON/排序列表…）
ERROR_CLASSES = ("新建", "pyism", "alias", "stdlib")
REQUIRED_TASK_KEYS = ("id", "prompt", "entry", "paths", "expected", "difficulty",
                      "category", "error_class")
REQUIRED_EXPECTED_KEYS = ("kind", "cmd", "files")

# 语言侧诊断码（T-0318 起的 `light ai check --json` 契约）：L0000 为占位码，
# L1xxx–L5xxx 由诊断码注册表（B 线）后续补齐。这里只认形状，不认具体值。
DIAG_CODE_RE = re.compile(r"\bL\d{4}\b")

# 判定失败时给「骨架自己」的错误码，便于把 benchmark 故障和语言报错分开看。
E_FIXTURE = "LA_E_FIXTURE"
E_MISSING_FILE = "LA_E_MISSING_FILE"
E_RC = "LA_E_RC"                 # 命令返回码不符合预期
E_STDOUT = "LA_E_STDOUT"         # 标准输出断言不成立
E_FILE_CONTAINS = "LA_E_FILE_CONTAINS"
E_FILE_NOT_CONTAINS = "LA_E_FILE_NOT_CONTAINS"
E_FILE_EQUALS = "LA_E_FILE_EQUALS"
E_TIMEOUT = "LA_E_TIMEOUT"
E_CMD = "LA_E_CMD"               # 命令起不来（解释器/路径问题）


class TaskError(Exception):
    """判定过程中可以确定归因的失败（不吞 traceback）。"""

    def __init__(self, stage: str, code: str, detail: str):
        super().__init__(detail)
        self.stage = stage
        self.code = code
        self.detail = detail


# ── 读任务 ────────────────────────────────────────────────────────────────


def load_tasks(bench_dir: Path) -> list[dict]:
    """读 tasks.jsonl：逐行 json.loads，坏行直接报行号，不跳过。"""
    path = bench_dir / "tasks.jsonl"
    tasks: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"tasks.jsonl 第 {lineno} 行不是合法 JSON: {exc}") from exc
            tasks.append(task)
    return tasks


def validate_task(task: dict, index: int) -> None:
    """字段齐全性自检：缺字段就直接失败，不让骨架带着半张卡跑。"""
    where = f"第 {index + 1} 条任务（{task.get('id') or '无 id'}）"
    for key in REQUIRED_TASK_KEYS:
        if key not in task:
            raise ValueError(f"{where} 缺字段 {key}")
    expected = task["expected"]
    for key in REQUIRED_EXPECTED_KEYS:
        if key not in expected:
            raise ValueError(f"{where} 的 expected 缺字段 {key}")
    if task["category"] not in CATEGORIES:
        raise ValueError(f"{where} category 非法: {task['category']}")
    if task["error_class"] not in ERROR_CLASSES:
        raise ValueError(f"{where} error_class 非法: {task['error_class']}")
    if task["difficulty"] not in DIFFICULTIES:
        raise ValueError(f"{where} difficulty 非法: {task['difficulty']}")
    if expected["kind"] not in KINDS:
        raise ValueError(f"{where} expected.kind 非法: {expected['kind']}")
    if task["entry"] not in task["paths"]:
        raise ValueError(f"{where} 的 entry 不在 paths 里")


# ── 工作区 ────────────────────────────────────────────────────────────────


def prepare_workspace(task: dict, bench_dir: Path, root: Path) -> tuple[Path, Path]:
    """按任务建一个干净工作区：铺 setup 里声明的 fixture。"""
    root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f"{task['id']}-", dir=str(root)))
    for item in task.get("setup", []):
        src = bench_dir / item["from"]
        dst = workspace / item["to"]
        if not src.is_file():
            raise TaskError("setup", E_FIXTURE, f"fixture 不存在: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return workspace, workspace


def apply_attempt(task: dict, attempt: dict, bench_dir: Path, workspace: Path) -> None:
    """把记录好的补丁文件铺进工作区（整文件快照，等价于 Agent 的产物）。"""
    files = attempt.get("files") or {}
    if not files:
        raise TaskError("setup", E_FIXTURE, "attempt 里没有任何 files")
    for rel_target, rel_source in files.items():
        src = bench_dir / rel_source
        if not src.is_file():
            raise TaskError("setup", E_FIXTURE, f"记录的补丁文件不存在: {src}")
        dst = workspace / rel_target
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


# ── 跑命令 ────────────────────────────────────────────────────────────────


def build_env(repo_root: Path) -> dict:
    env = os.environ.copy()
    pythonpath = [str(repo_root), str(repo_root / "src")]
    existing = env.get("PYTHONPATH")
    if existing:
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def build_argv(template: str, entry: str, workspace: Path, repo_root: Path) -> list[str]:
    """把任务卡里的可读命令翻成 argv。

    ``light``  → ``python -m cli.light``；``python`` → 当前解释器。
    ``{entry}`` / ``{stdlib}`` / ``{out}`` / ``{workspace}`` 都按**整 token**替换，
    所以路径里有空格也不会被拆开。
    """
    out_path = workspace / (Path(entry).stem + ".py")
    ctx = {
        "entry": entry,
        "stdlib": str(repo_root / "stdlib"),
        "out": str(out_path),
        "workspace": str(workspace),
    }
    argv = [token.format(**ctx) for token in template.split()]
    if not argv:
        raise TaskError("setup", E_CMD, "expected.cmd 为空")
    if argv[0] == "light":
        argv = [sys.executable, "-m", "cli.light"] + argv[1:]
    elif argv[0] == "python":
        argv[0] = sys.executable
    return argv


def run_command(
    template: str,
    entry: str,
    workspace: Path,
    repo_root: Path,
    timeout: float,
) -> subprocess.CompletedProcess:
    argv = build_argv(template, entry, workspace, repo_root)
    try:
        return subprocess.run(
            argv,
            cwd=str(workspace),
            env=build_env(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TaskError("command", E_TIMEOUT, f"命令超时（{timeout:g}s）: {template}") from exc
    except OSError as exc:
        raise TaskError("command", E_CMD, f"命令起不来: {exc}") from exc


# ── 断言 ──────────────────────────────────────────────────────────────────


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def count_occurrences(haystack: str, needle: str) -> int:
    return haystack.count(needle)


def judge_output(task: dict, proc: subprocess.CompletedProcess, workspace: Path,
                 assert_stdout: str | None = None) -> dict:
    """返回 {stage, code, detail}：空字典表示通过。

    ``assert_stdout`` 用于「先 check/compile 再 run」的任务：check 自己会往 stdout
    打统计和类型检查噪音，行为断言只认后置命令的输出。
    """
    expected = task["expected"]
    want_rc = int(expected.get("rc", 0))

    stdout = (proc.stdout or "").replace("\r\n", "\n") if assert_stdout is None \
        else assert_stdout.replace("\r\n", "\n")
    stderr = (proc.stderr or "").replace("\r\n", "\n")

    if proc.returncode != want_rc:
        detail = (stderr or stdout).strip()
        return {
            "stage": "command",
            "code": "",  # 由 harvest_error_code 用语言自己的码补上
            "detail": f"返回码 {proc.returncode}，期望 {want_rc}: {detail[:400]}",
        }

    for spec in expected.get("files", []):
        path = workspace / spec["path"]
        if not path.is_file():
            return {
                "stage": "assert",
                "code": E_MISSING_FILE,
                "detail": f"期望产出的文件不存在: {spec['path']}",
            }
        text = read_text(path)
        if "equals" in spec:
            if text.strip() != spec["equals"].strip():
                return {
                    "stage": "assert",
                    "code": E_FILE_EQUALS,
                    "detail": f"{spec['path']} 内容与期望快照不一致",
                }
        for needle in spec.get("contains", []):
            if needle not in text:
                return {
                    "stage": "assert",
                    "code": E_FILE_CONTAINS,
                    "detail": f"{spec['path']} 缺少片段: {needle}",
                }
        for needle in spec.get("not_contains", []):
            if needle in text:
                return {
                    "stage": "assert",
                    "code": E_FILE_NOT_CONTAINS,
                    "detail": f"{spec['path']} 不应出现片段: {needle}",
                }

    for needle in expected.get("stdout_contains", []):
        if needle not in stdout:
            return {
                "stage": "assert",
                "code": E_STDOUT,
                "detail": f"标准输出缺少: {needle}",
            }
    for needle in expected.get("stdout_not_contains", []):
        if needle in stdout:
            return {
                "stage": "assert",
                "code": E_STDOUT,
                "detail": f"标准输出不应出现: {needle}",
            }
    for needle, wanted in (expected.get("stdout_count") or {}).items():
        actual = count_occurrences(stdout, needle)
        if actual != wanted:
            return {
                "stage": "assert",
                "code": E_STDOUT,
                "detail": f"标准输出「{needle}」出现 {actual} 次，期望 {wanted} 次",
            }
    if "stdout_equals" in expected:
        if stdout.strip() != expected["stdout_equals"].strip():
            return {
                "stage": "assert",
                "code": E_STDOUT,
                "detail": f"标准输出与期望不一致: {stdout.strip()[:200]!r}",
            }
    return {}


# ── 错误码 ────────────────────────────────────────────────────────────────


def harvest_error_code(task: dict, proc: subprocess.CompletedProcess, workspace: Path,
                       repo_root: Path, timeout: float) -> str:
    """失败时补一个**确定性**错误码：优先语言自己的诊断码，其次骨架码。

    走 ``light ai check --json`` 拿结构化诊断（rc=0/1/2，单条 JSON）；
    拿不到就退化成 ``LA_E_RC_<rc>``。不猜、不用 LLM、不做模糊匹配。
    """
    detail_codes = DIAG_CODE_RE.findall(f"{proc.stdout or ''}\n{proc.stderr or ''}")
    if detail_codes:
        return detail_codes[0]

    if Path(task["entry"]).suffix == ".light":
        try:
            ai = run_command(
                "light ai check {entry} --run --json",
                task["entry"], workspace, repo_root, timeout,
            )
            payload = json.loads(ai.stdout) if ai.stdout.strip().startswith("{") else {}
            codes = [d.get("code") for d in payload.get("diagnostics", []) if d.get("code")]
            if codes:
                return codes[0]
        except Exception:
            pass  # 诊断路径拿不到就落骨架码，不影响主判定结论

    return f"{E_RC}_{proc.returncode}"


# ── 单卡判定 ──────────────────────────────────────────────────────────────


def run_task(task: dict, bench_dir: Path, repo_root: Path, work_root: Path,
             timeout: float, keep: bool) -> dict:
    started = time.monotonic()
    attempts = task.get("stub", {}).get("attempts") or []
    record: dict = {
        "id": task["id"],
        "ok": False,
        "stage": "setup",
        "error_code": "",
        "error_class": task.get("error_class", ""),
        "retries": 0,
        "elapsed": 0.0,
        "attempts": [],
    }

    if not attempts:
        record.update(stage="setup", error_code=E_FIXTURE,
                      elapsed=round(time.monotonic() - started, 3))
        record["detail"] = "任务没有记录 stub 补丁（--model stub 无从重放）"
        return record

    last_failure: dict = {}
    workspace: Path | None = None
    for index, attempt in enumerate(attempts):
        if workspace is not None and not keep:
            shutil.rmtree(workspace, ignore_errors=True)
        failure: dict = {}
        proc = None
        try:
            workspace, _ = prepare_workspace(task, bench_dir, work_root)
            apply_attempt(task, attempt, bench_dir, workspace)
            proc = run_command(task["expected"]["cmd"], task["entry"], workspace,
                               repo_root, timeout)
            assert_stdout = None
            if "post_cmd" in task["expected"]:
                post_stdout = ""
                for post in task["expected"]["post_cmd"]:
                    post_proc = run_command(post, task["entry"], workspace, repo_root, timeout)
                    if post_proc.returncode != 0:
                        failure = {
                            "stage": "command",
                            "code": f"{E_RC}_{post_proc.returncode}",
                            "detail": f"后置命令失败: {post}",
                        }
                        break
                    post_stdout += post_proc.stdout or ""
                    proc.stderr = (proc.stderr or "") + (post_proc.stderr or "")
                assert_stdout = post_stdout
            if not failure:
                failure = judge_output(task, proc, workspace, assert_stdout)
        except TaskError as exc:
            failure = {"stage": exc.stage, "code": exc.code, "detail": exc.detail}
        last_failure = failure

        attempt_record = {"n": index + 1, "ok": not failure,
                          "stage": "ok" if not failure else failure["stage"],
                          "error_code": failure.get("code", "")}
        if failure and proc is not None and not failure.get("code") and workspace is not None:
            code = harvest_error_code(task, proc, workspace, repo_root, timeout)
            failure["code"] = code
            attempt_record["error_code"] = code
        if failure:
            attempt_record["detail"] = failure.get("detail", "")
        record["attempts"].append(attempt_record)

        if not failure:
            record.update(ok=True, stage="ok", error_code="", retries=index)
            break
        record.update(stage=failure["stage"], error_code=failure["code"], retries=index + 1)

    if record["ok"]:
        # 一次通过时 error_code 留空；有重试时保留「最后一次失败」的码，
        # 它才是这次 retry 的成因，汇总里的错误码分布就靠它。
        if record["retries"]:
            record["error_code"] = record["attempts"][-2]["error_code"]

    if workspace is not None and not keep:
        shutil.rmtree(workspace, ignore_errors=True)
    record["elapsed"] = round(time.monotonic() - started, 3)
    return record


# ── 汇总 ──────────────────────────────────────────────────────────────────


def summarize(records: list[dict]) -> dict:
    total = len(records)
    passed = sum(1 for item in records if item["ok"])
    codes: dict[str, int] = {}
    # 分布按「尝试」统计：重试前的失败也算一次真实报错。
    for item in records:
        for attempt in item["attempts"]:
            if attempt["error_code"]:
                codes[attempt["error_code"]] = codes.get(attempt["error_code"], 0) + 1
    retries = sum(item["retries"] for item in records)

    # 按 error_class 分组的通过率：修「读取」到底有没有用，看这一组自己的数字。
    groups: dict[str, dict] = {}
    for item in records:
        cls = item.get("error_class") or "未分类"
        bucket = groups.setdefault(cls, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if item["ok"]:
            bucket["passed"] += 1
    order = list(ERROR_CLASSES) + sorted(k for k in groups if k not in ERROR_CLASSES)
    by_class = {
        cls: {
            "total": groups[cls]["total"],
            "passed": groups[cls]["passed"],
            "failed": groups[cls]["total"] - groups[cls]["passed"],
            "pass_rate": round(groups[cls]["passed"] / groups[cls]["total"], 4),
        }
        for cls in order if cls in groups
    }

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "retries_total": retries,
        "avg_retries": round(retries / total, 4) if total else 0.0,
        "error_codes": dict(sorted(codes.items())),
        "by_error_class": by_class,
    }


def format_human(records: list[dict], summary: dict, model: str) -> str:
    lines = [f"Light Agent Benchmark（model={model}，{summary['total']} 条）"]
    for item in records:
        mark = "✓" if item["ok"] else "✗"
        code = f"  [{item['error_code']}]" if item["error_code"] else ""
        lines.append(
            f"  {item['id']}  {mark}  stage={item['stage']:<8} "
            f"retries={item['retries']}  {item['elapsed']:>6.2f}s{code}"
        )
        if not item["ok"]:
            last = (item.get("attempts") or [{}])[-1]
            if last.get("detail"):
                lines.append(f"      └ {last['detail'][:160]}")
    lines.append(
        f"通过 {summary['passed']}/{summary['total']} = {summary['pass_rate'] * 100:.1f}%"
        f"｜平均 retry {summary['avg_retries']:.2f}"
        f"｜错误码 {summary['error_codes'] or '无'}"
    )
    by_class = summary.get("by_error_class") or {}
    if by_class:
        parts = [
            f"{cls} {item['passed']}/{item['total']}={item['pass_rate'] * 100:.1f}%"
            for cls, item in by_class.items()
        ]
        lines.append("按 error_class：" + "｜".join(parts))
    return "\n".join(lines)


# ── 入口 ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Light Agent Benchmark：可离线判定的 AI 编程能力任务集")
    parser.add_argument("--model", default="stub",
                        help="stub=用记录好的补丁离线判定（默认）；其它值当前未接线")
    parser.add_argument("--task", action="append", default=[],
                        help="只跑指定任务 id（可重复）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    parser.add_argument("--list", action="store_true", help="列出任务，不跑")
    parser.add_argument("--bench-dir", default=str(DEFAULT_BENCH_DIR),
                        help="benchmark 目录（默认本文件所在目录）")
    parser.add_argument("--repo", default=str(DEFAULT_REPO_ROOT),
                        help="light 仓根目录（默认按本文件位置推断）")
    parser.add_argument("--workspace", default=None,
                        help="临时工作区根目录（默认系统临时目录）")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"单条命令超时秒数（默认 {DEFAULT_TIMEOUT:g}）")
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1),
                        help="并行判定条数（默认 min(4, CPU 数)；任务之间无共享状态）")
    parser.add_argument("--keep", action="store_true", help="保留临时工作区便于排查")
    args = parser.parse_args(argv)

    bench_dir = Path(args.bench_dir).resolve()
    repo_root = Path(args.repo).resolve()

    if args.model != "stub":
        print(
            f"未接线：--model {args.model} 还没有实现。\n"
            "本卡只交付可离线判定的骨架（--model stub）；模型接入是后续任务，"
            "这里不会假装跑出通过率。",
            file=sys.stderr,
        )
        return 2

    if not (bench_dir / "tasks.jsonl").is_file():
        print(f"找不到任务集: {bench_dir / 'tasks.jsonl'}", file=sys.stderr)
        return 2
    if not (repo_root / "cli" / "light.py").is_file():
        print(f"--repo 不像 light 仓根目录（缺 cli/light.py）: {repo_root}", file=sys.stderr)
        return 2

    tasks = load_tasks(bench_dir)
    for index, task in enumerate(tasks):
        validate_task(task, index)
    if args.task:
        wanted = set(args.task)
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            print(f"任务集里没有: {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    if args.list:
        for task in tasks:
            print(f"{task['id']}  {task['difficulty']}  {task['category']}  "
                  f"{task['expected']['kind']}  {task['entry']}  {task['prompt']}")
        return 0

    work_root = Path(args.workspace) if args.workspace else \
        Path(tempfile.mkdtemp(prefix="light-agent-bench-"))
    jobs = max(1, args.jobs)
    if not args.json:
        print(f"跑 {len(tasks)} 条任务（jobs={jobs}）…", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        # map 保序：records 与 tasks 一一对应，结果可复现。
        records = list(pool.map(
            lambda task: run_task(task, bench_dir, repo_root, work_root,
                                  args.timeout, args.keep),
            tasks,
        ))

    summary = summarize(records)
    payload = {
        "bench": "light_agent",
        "model": args.model,
        "repo": str(repo_root),
        "tasks": records,
        "summary": summary,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_human(records, summary, args.model))

    if not args.keep and args.workspace is None:
        shutil.rmtree(work_root, ignore_errors=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
