# -*- coding: utf-8 -*-
"""T-0465 冷启动探针：真实模型 × light_agent 20 条任务，判定复用 benchmarks 判定器。

为什么单独写这个文件
--------------------
``benchmarks/light_agent/run_benchmarks_agent.py`` 只有 ``--model stub``（重放人写好的补丁，
必然 20/20），没有真实模型接线，也不接 ``light harness run`` 的评测集格式。
本卡要在「干净启动 + 最多 3 轮」口径下拿到真实数字，所以在这里做一个最小探针：

* **判定**：直接 ``import`` 判定器里的 ``prepare_workspace`` / ``run_command`` /
  ``judge_output`` / ``harvest_error_code``，**判据代码一行不改**（T-0462 独占，不碰）。
* **被测方**：OpenAI 兼容端点（默认读根 ``.env`` 的 OPENAI_BASE_URL / OPENAI_MODEL /
  OPENAI_API_KEY），单轮产出整份文件；失败则把**命令真实输出**（rc / stdout / stderr 摘录 +
  ``light ai check --json`` 诊断码）回喂，最多 3 轮。
* **两臂**：
  - ``with_entry``：system 里带 ``AGENTS.md`` + ``skills/light/SKILL.md``（T-0460 分支内容；
    基线 main 上这两个文件还没合入，所以从 git 对象读，不往工作区写文件）。
  - ``no_entry``：system 只有一句「这是光明语言工程」，模拟 R223 之前的冷启动。

口径边界（写进报告，不许含糊）
------------------------------
* 模型没有工具、不能自己读文件 —— 实验组把入口文档**注入** system，等价于「它已经读过」。
  这是「文档注入」，不是「模型自己发现文档」；发现率另行审计，不能拿这个数冒充。
* 判定只用 ``light run/compile/check`` 的返回码与文件断言，不用 LLM 打分。

用法::

    python docs/bench/coldstart_probe.py --arms with_entry,no_entry --rounds 3 \
        --out docs/bench/coldstart_20261125.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "benchmarks" / "light_agent"
JUDGE_PATH = BENCH_DIR / "run_benchmarks_agent.py"
ENV_PATH = Path(r"G:\dswork\duan-light-merge\.env")
ENTRY_COMMIT = "eef3fab30"          # T-0460：AGENTS.md / llms.txt / skills/light/SKILL.md

MAX_TOKENS = 4096                   # deepseek-flash 是推理模型：1200 会被思维链烧空
TEMPERATURE = 0.1
CALL_TIMEOUT = 120


def load_judge():
    spec = importlib.util.spec_from_file_location("la_judge", JUDGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_cfg() -> dict:
    cfg = {}
    for ln in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        cfg[k.strip()] = v.strip()
    for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
        if not cfg.get(k):
            raise SystemExit(f"根 .env 缺 {k}，无法跑真实模型；本卡应改走 --model stub 并标注")
    return cfg


def git_show(path: str) -> str:
    return subprocess.run(["git", "show", f"{ENTRY_COMMIT}:{path}"],
                          cwd=str(REPO_ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout


def call_model(cfg: dict, messages: list[dict]) -> dict:
    """一次调用；空回复但 finish_reason=length 时**加倍预算重试**。

    deepseek-flash 是推理模型：思维链会把 4096 token 烧光、正文还没开始写，
    返回空 content + finish_reason=length。这属于配置伪影，不是模型能力失败
    （docs/功能对标/L4_真实LLM复测报告.md §3 已记录同一现象）。所以这里把预算
    翻倍重试，最多 2 次（4096 → 8192 → 16384），每次重试都记在 ``budget_retries``。
    """
    url = cfg["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
    max_tokens = MAX_TOKENS
    attempts = 0
    started = time.monotonic()
    while True:
        body = json.dumps({
            "model": cfg["OPENAI_MODEL"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": TEMPERATURE,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": "Bearer " + cfg["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        choice = payload["choices"][0]
        out = choice["message"]["content"] or ""
        finish = choice.get("finish_reason")
        if out.strip() or finish != "length" or attempts >= 2:
            break
        attempts += 1
        max_tokens *= 2
    return {
        "content": out,
        "finish_reason": finish,
        "latency": round(time.monotonic() - started, 3),
        "usage": payload.get("usage", {}),
        "budget_retries": attempts,
        "max_tokens": max_tokens,
    }


FENCE_RE = re.compile(r"```(?:光明|light|Light)?\s*\n(.*?)```", re.S)


def extract_code(text: str) -> str:
    """从回复里抠出整份源码：优先最长的一段围栏代码，否则整段回复。"""
    blocks = [m.group(1) for m in FENCE_RE.finditer(text)]
    if blocks:
        return max(blocks, key=len)
    return text


def workspace_snapshot(workspace: Path) -> str:
    parts = []
    for p in sorted(workspace.rglob("*")):
        if p.is_file():
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            parts.append(f"### 文件 {p.relative_to(workspace)}\n{txt}")
    return "\n\n".join(parts)


SYSTEM_BASE = (
    "你是一个刚接手这个仓库的编程 Agent。仓库里是一门叫「光明（Light）」的中文关键字编程语言。\n"
    "规则：只输出目标文件的**完整内容**（整文件，不是 diff），放在一个 ```光明 围栏里；"
    "不要解释，不要输出其它文件，不要新增依赖。\n"
)

SYSTEM_ENTRY = SYSTEM_BASE + "\n以下是这个仓库给 Agent 的入口文档，按它说的写。\n\n<AGENTS.md>\n{agents}\n</AGENTS.md>\n\n" \
                             "<skills/light/SKILL.md>\n{skill}\n</skills/light/SKILL.md>\n"

USER_TEMPLATE = (
    "任务：{prompt}\n\n"
    "允许触碰的文件：{paths}\n"
    "要交付的文件：{entry}\n\n"
    "当前工作区内容：\n{snapshot}\n"
)

FEEDBACK_TEMPLATE = (
    "上一版产物跑判定命令 `{cmd}` 时失败。\n"
    "返回码：{rc}\n"
    "stdout（截断）：\n{stdout}\n"
    "stderr（截断）：\n{stderr}\n"
    "语言诊断码：{codes}\n\n"
    "请据此改对，仍然只输出「{entry}」的完整内容。"
)


def run_one(cfg: dict, judge, task: dict, arm: str, rounds: int, work_root: Path,
            timeout: float = 60.0) -> dict:
    record = {
        "id": task["id"], "category": task["category"], "difficulty": task["difficulty"],
        "arm": arm, "rounds": [], "pass@1": False, "passed": False, "rounds_used": 0,
    }
    workspace, _ = judge.prepare_workspace(task, BENCH_DIR, work_root)
    conversation = []
    sys_prompt = (SYSTEM_ENTRY.format(agents=git_show("AGENTS.md"), skill=git_show("skills/light/SKILL.md"))
                  if arm == "with_entry" else SYSTEM_BASE)
    conversation.append({"role": "system", "content": sys_prompt})

    last_failure = {}
    for n in range(1, rounds + 1):
        if n == 1:
            user = USER_TEMPLATE.format(
                prompt=task["prompt"], paths="、".join(task["paths"]),
                entry=task["entry"], snapshot=workspace_snapshot(workspace))
        else:
            user = FEEDBACK_TEMPLATE.format(
                cmd=task["expected"]["cmd"], rc=last_failure.get("rc", ""),
                stdout=(last_failure.get("stdout") or "")[:600],
                stderr=(last_failure.get("stderr") or "")[:600],
                codes=last_failure.get("codes") or "（无）",
                entry=task["entry"])
        conversation.append({"role": "user", "content": user})

        call = call_model(cfg, conversation)
        code = extract_code(call["content"])
        (workspace / task["entry"]).write_text(code, encoding="utf-8")
        conversation.append({"role": "assistant", "content": call["content"]})

        step = {"n": n, "latency": call["latency"], "finish_reason": call["finish_reason"],
                "chars": len(code), "budget_retries": call.get("budget_retries", 0),
                "max_tokens": call.get("max_tokens")}
        failure = {}
        proc = None
        try:
            proc = judge.run_command(task["expected"]["cmd"], task["entry"], workspace,
                                     REPO_ROOT, timeout)
            assert_stdout = None
            if "post_cmd" in task["expected"]:
                post_stdout = ""
                for post in task["expected"]["post_cmd"]:
                    post_proc = judge.run_command(post, task["entry"], workspace, REPO_ROOT, timeout)
                    if post_proc.returncode != 0:
                        failure = {"stage": "command", "detail": f"后置命令失败: {post}"}
                        break
                    post_stdout += post_proc.stdout or ""
                    proc.stderr = (proc.stderr or "") + (post_proc.stderr or "")
                assert_stdout = post_stdout
            if not failure:
                failure = judge.judge_output(task, proc, workspace, assert_stdout)
        except judge.TaskError as exc:
            failure = {"stage": exc.stage, "code": exc.code, "detail": exc.detail}

        if failure and proc is not None and workspace is not None:
            if not failure.get("code"):
                failure["code"] = judge.harvest_error_code(task, proc, workspace, REPO_ROOT, timeout)
            last_failure = {
                "rc": proc.returncode,
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "codes": failure.get("code") or "",
                "stage": failure.get("stage"),
                "detail": failure.get("detail", ""),
            }

        step.update(ok=not failure, stage="ok" if not failure else failure.get("stage"),
                    error_code="" if not failure else (failure.get("code") or ""))
        if failure:
            step["detail"] = (failure.get("detail") or "")[:240]
            step["rc"] = last_failure["rc"]
            step["stderr"] = (last_failure["stderr"] or "")[:240]
            step["code_head"] = code[:1500]
        record["rounds"].append(step)
        if not failure:
            record["passed"] = True
            record["rounds_used"] = n
            record["pass@1"] = (n == 1)
            break
    record["rounds_used"] = record["rounds_used"] or len(record["rounds"])
    if not record["passed"]:
        record["final_detail"] = (last_failure.get("detail") or "")[:240]
        record["final_stage"] = last_failure.get("stage")
        record["final_code"] = last_failure.get("codes")
    return record


def summarize(records: list[dict], rounds: int) -> dict:
    out = {}
    for arm in sorted({r["arm"] for r in records}):
        rows = [r for r in records if r["arm"] == arm]
        total = len(rows)
        pass1 = sum(1 for r in rows if r["pass@1"])
        passed = sum(1 for r in rows if r["passed"])
        fail1 = total - pass1
        healed = sum(1 for r in rows if (not r["pass@1"]) and r["passed"])
        codes = {}
        for r in rows:
            for s in r["rounds"]:
                if s.get("error_code"):
                    codes[s["error_code"]] = codes.get(s["error_code"], 0) + 1
        out[arm] = {
            "total": total,
            "pass_at_1": round(pass1 / total, 4) if total else None,
            f"pass_at_{rounds}": round(passed / total, 4) if total else None,
            "pass1_count": pass1, "passed_count": passed,
            "self_heal_rate": round(healed / fail1, 4) if fail1 else None,
            "self_heal_count": healed, "first_fail_count": fail1,
            "rounds_total": sum(len(r["rounds"]) for r in rows),
            "error_codes": dict(sorted(codes.items(), key=lambda kv: -kv[1])),
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="with_entry,no_entry")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--out", default="docs/bench/coldstart_20261125.json")
    ap.add_argument("--jobs", type=int, default=1, help="并发任务数（每任务独立工作区）")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="单条判定命令超时秒数（判定器默认 30；并发下 30 会假失败）")
    args = ap.parse_args(argv)

    judge = load_judge()
    cfg = load_cfg()
    tasks = [json.loads(ln) for ln in (BENCH_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.only:
        tasks = [t for t in tasks if t["id"] in args.only]

    work_root = Path(tempfile.mkdtemp(prefix="t0465-coldstart-"))
    records = []
    started = time.monotonic()
    jobs = max(1, args.jobs)

    def one(arm: str, task: dict) -> dict:
        t0 = time.monotonic()
        rec = run_one(cfg, judge, task, arm, args.rounds, work_root, args.timeout)
        rec["elapsed"] = round(time.monotonic() - t0, 2)
        print(f"{arm:10s} {rec['id']} pass@1={rec['pass@1']} passed={rec['passed']} "
              f"rounds={rec['rounds_used']} {rec['elapsed']}s", flush=True)
        return rec

    for arm in [a.strip() for a in args.arms.split(",") if a.strip()]:
        if jobs == 1:
            records.extend(one(arm, t) for t in tasks)
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                records.extend(pool.map(lambda t: one(arm, t), tasks))

    payload = {
        "bench": "light_agent",
        "probe": "T-0465 cold-start",
        "model": cfg["OPENAI_MODEL"],
        "endpoint": cfg["OPENAI_BASE_URL"],
        "arms": args.arms.split(","),
        "max_rounds": args.rounds,
        "timeout_s": args.timeout,
        "jobs": jobs,
        "entry_docs_from": ENTRY_COMMIT,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "wall_clock_s": round(time.monotonic() - started, 1),
        "tasks": records,
        "summary": summarize(records, args.rounds),
    }
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=1))
    print(f"写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
