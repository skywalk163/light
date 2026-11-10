# -*- coding: utf-8 -*-
"""tests/dogfood 公共逻辑：模块发现、CLI 探测、结果分片与报告。

本模块不依赖 pytest，供 conftest.py 与 test_lightharness_smoke.py 共用。
只读 lightharness，不修改其中任何文件；唯一写盘是 light 仓根 build/ 下的报告与分片。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- 路径与发现
REPO_ROOT = Path(__file__).resolve().parents[2]          # tests/dogfood/x.py -> light 仓根
BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"
BUILD_DIR = REPO_ROOT / "build"
REPORT_PATH = BUILD_DIR / "dogfood_report.json"
PART_DIR = BUILD_DIR / "dogfood_parts"

MODULE_SCOPE = ("src", "stdlib")   # 工程体模块；examples/ 是场景，docs/ 是历史负例，均不入 check 抽样
SKIP_TEXT = "未找到 lightharness，跳过（不是通过）"

# light 的 src/type_inferencer.py 类型推断结果会随 PYTHONHASHSEED 变化（实测
# src/mock大模型服务器.light：seed=1 稳定 rc=1，seed=0/2/42 稳定 rc=0，不固定则随机）。
# 判据必须可重复，因此固定子进程 hash seed；该非确定性本身作为 light 缺陷单独开卡，
# 不靠调基线掩盖。可用 LIGHT_DOGFOOD_HASH_SEED 覆盖以复现该缺陷。
HASH_SEED = os.environ.get("LIGHT_DOGFOOD_HASH_SEED", "0")


def find_lightharness() -> Path:
    """LIGHTHARNESS_DIR 优先；缺省 ../lightharness，并兼容 hive worktree 的深一层布局。"""
    explicit = os.environ.get("LIGHTHARNESS_DIR")
    if explicit:
        return Path(explicit).expanduser()
    candidates = (
        REPO_ROOT.parent / "lightharness",          # 任务卡字面缺省 ../lightharness
        REPO_ROOT.parent.parent / "lightharness",   # hive-wt/<task>/ -> dswork/lightharness
        REPO_ROOT / "lightharness",
    )
    for cand in candidates:
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if cand.is_dir() and ((cand / "运行.py").is_file() or (cand / "src").is_dir()):
            return cand
    return candidates[0]


LIGHTHARNESS_DIR = find_lightharness()


def sample_limit() -> int:
    raw = os.environ.get("LIGHT_DOGFOOD_LIMIT", "20")
    try:
        n = int(raw)
        return n if n > 0 else 20
    except (TypeError, ValueError):
        return 20


def discover_modules(root: Path) -> list[str]:
    """按 POSIX 风格相对路径的 Unicode 码点排序；无随机、与平台 locale 无关。"""
    found: set[str] = set()
    for sub in MODULE_SCOPE:
        base = root / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*.light"):
            if path.is_file():
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


ALL_MODULES = discover_modules(LIGHTHARNESS_DIR) if LIGHTHARNESS_DIR.is_dir() else []
SAMPLE = ALL_MODULES[: sample_limit()]


def load_baseline() -> set[str]:
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return set(data["failed_modules"])


# ---------------------------------------------------------------- 场景定义
# 场景 = 「一个用户目标被完整跑通」，不是「某模块存在」。
# expect 是 stdout 里的收尾标志：rc=0 之外还要真看到业务结果，避免空跑也算通过。
SCENES = [
    {
        "id": "JSON序列化与解析往返",
        "entry": "examples/冒烟.light",
        "expect": "自包含 stdlib 冒烟测试通过",
        "xfail": None,
        "desc": "字典 -> JSON 文本 -> 解析回字段 + 数学常量，自包含 stdlib 引导",
    },
    {
        "id": "字典存取与条件判定",
        "entry": "examples/test_字典.light",
        "expect": "--- 字典方法测试通过 ---",
        "xfail": None,
        "desc": "建表、包含/获取、键写入、条件倒置",
    },
    {
        "id": "类实例与列表增删",
        "entry": "examples/test_空表.light",
        "expect": "--- 测试结束 ---",
        "xfail": None,
        "desc": "类属性初始化、列表追加、长度回读",
    },
    {
        "id": "事件表构建与追加",
        "entry": "examples/test_事件表.light",
        "expect": "--- 测试2结束 ---",
        "xfail": None,
        "desc": "事件表容器创建、追加、长度回读",
    },
    {
        "id": "真实HTTP请求并解析响应",
        "entry": "examples/test_R41_真实网络IO.light",
        "expect": "",
        "xfail": (
            "需要真实网络 IO（本卡禁止联网，且该场景会本机起 HTTP 服务端/客户端）；"
            "此外 lightharness 的 src/*.light 模块引导依赖 运行.py 的进程内 sys.path 注入，"
            "独立 `python -m cli.light run` 子进程报 No module named 'web服务器'。"
        ),
        "desc": "本地起 web 服务 -> GET /health -> POST /v1/chat/completions -> 解析 200/401 响应",
    },
]
SCENE_BY_ID = {s["id"]: s for s in SCENES}


# ---------------------------------------------------------------- CLI 探测
_ERROR_PREFIXES = ("❌", "错误:", "解析失败", "[类型错误]", "[语法错误]")


def _first(lines: list[str]) -> str:
    return lines[0] if lines else ""


def run_cli(subcommand: str, rel: str, timeout: int = 90) -> dict:
    """跑 `python -m cli.light <check|run> <file>`，纯语法/类型检查或解释执行。

    子进程 cwd 固定为 light 仓根（cli 包所在），文件用绝对路径；不注入 PYTHONPATH，
    保持「独立 CLI 进程」的真实语义。错误首行同时看 stderr 与 stdout —— light CLI
    把类型错误打在 stdout，stderr 常常为空（见 docs/吃狗粮回归.md §缺陷清单）。
    """
    path = LIGHTHARNESS_DIR / rel
    cmd = [sys.executable, "-X", "utf8", "-m", "cli.light", subcommand, str(path)]
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = HASH_SEED
    t0 = time.perf_counter()
    out_lines: list[str] = []
    err_lines: list[str] = []
    rc = 124
    try:
        cp = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        rc = cp.returncode
        out_lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
        err_lines = [ln.strip() for ln in cp.stderr.splitlines() if ln.strip()]
    except subprocess.TimeoutExpired:
        err_lines = [f"TIMEOUT after {timeout}s"]
    except OSError as exc:
        err_lines = [f"SPAWN FAILED: {exc}"]

    error_first = _first([
        ln for ln in out_lines
        if ln.startswith(_ERROR_PREFIXES) or "类型错误:" in ln or "解析失败" in ln
    ])
    detail_first = _first([
        ln for ln in out_lines
        if ln.startswith(("[类型推断]", "[类型错误]", "[语法错误]", "错误:"))
        or "类型错误:" in ln or "解析失败" in ln
    ])
    return {
        "rc": rc,
        "elapsed_sec": round(time.perf_counter() - t0, 3),
        "stderr_first": _first(err_lines),
        "error_first": error_first[:240],
        "detail_first": detail_first[:300],
        "stdout_first": _first(out_lines)[:240],
        "stdout_last": out_lines[-1][:240] if out_lines else "",
        "stdout_excerpt": "\n".join(out_lines)[:4000],
        "command": " ".join(cmd[:5]) + " " + str(path),
    }


# ---------------------------------------------------------------- 结果收集
# 每个用例写独立分片文件：xdist 多 worker 并行时也不会互相覆盖。
_RESULTS: dict[str, dict] = {"check": {}, "scene": {}}


def record(kind: str, key: str, result: dict) -> None:
    _RESULTS.setdefault(kind, {})[key] = result
    try:
        PART_DIR.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(f"{kind}:{key}".encode("utf-8")).hexdigest()[:20]
        (PART_DIR / f"{kind}-{digest}.json").write_text(
            json.dumps({"kind": kind, "key": key, "result": result}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass  # 报告是观测产物，写不进去不能反过来让判据变红


def merged_results() -> dict[str, dict]:
    merged = {"check": dict(_RESULTS.get("check", {})), "scene": dict(_RESULTS.get("scene", {}))}
    if PART_DIR.is_dir():
        for part in PART_DIR.glob("*.json"):
            try:
                data = json.loads(part.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            merged.setdefault(data["kind"], {}).setdefault(data["key"], data["result"])
    return merged


def clear_parts() -> None:
    shutil.rmtree(PART_DIR, ignore_errors=True)


def write_report(results: dict[str, dict]) -> dict:
    checks = results["check"]
    scenes = results["scene"]
    baseline = load_baseline() if BASELINE_PATH.is_file() else set()
    failed = sorted(m for m, r in checks.items() if r["rc"] != 0)
    passed = sorted(m for m, r in checks.items() if r["rc"] == 0)
    new_failures = sorted(set(failed) - baseline)
    removable = sorted(m for m in baseline if m in checks and checks[m]["rc"] == 0)
    scene_passed = [s["id"] for s in SCENES if s["id"] in scenes and scenes[s["id"]]["rc"] == 0]
    scene_failed = [s["id"] for s in SCENES if s["id"] in scenes and scenes[s["id"]]["rc"] != 0]

    def slim(r: dict) -> dict:
        return {k: r[k] for k in (
            "rc", "elapsed_sec", "stderr_first", "error_first", "detail_first",
            "stdout_first", "stdout_last", "command",
        ) if k in r}

    report = {
        "schema": 1,
        "task": "T-0322",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "env": {
            "PYTHONHASHSEED": HASH_SEED,
            "note": "固定 hash seed 以消除 light 类型推断的非确定性（缺陷见 docs/吃狗粮回归.md）",
        },
        "lightharness_dir": str(LIGHTHARNESS_DIR),
        "lightharness_found": LIGHTHARNESS_DIR.is_dir(),
        "status": "ok" if LIGHTHARNESS_DIR.is_dir() else "skipped",
        "sample": {
            "limit": sample_limit(),
            "scope": list(MODULE_SCOPE),
            "total_modules": len(ALL_MODULES),
            "sampled": len(SAMPLE),
            "rule": "相对路径 Unicode 码点升序取前 N；禁止随机",
        },
        "modules": [{"module": m, **slim(checks[m])} for m in SAMPLE if m in checks],
        "scenes": [
            {
                "scene": s["id"], "entry": s["entry"], "desc": s["desc"],
                "xfail": bool(s["xfail"]), "reason": s["xfail"] or "",
                **slim(scenes[s["id"]]),
                "stdout_excerpt": scenes[s["id"]].get("stdout_excerpt", "")[:600],
            }
            for s in SCENES if s["id"] in scenes
        ],
        "baseline": {
            "file": "tests/dogfood/baseline.json",
            "debt": len(baseline),
            "failed_now": failed,
            "new_failures": new_failures,
            "removable": removable,
            "policy": "只允许缩小；上调需在 docs/吃狗粮回归.md 写明理由",
        },
        "summary": {
            "sampled": len(SAMPLE),
            "passed": len(passed),
            "failed": len(failed),
            "baseline_debt": len(baseline),
            "new_failures": len(new_failures),
            "baseline_removable": len(removable),
            "scenes_total": len(SCENES),
            "scenes_passed": len(scene_passed),
            "scenes_failed": len(scene_failed),
            "run_through_rate": round(len(passed) / len(checks), 4) if checks else None,
        },
    }
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
