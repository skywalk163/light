#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSH（DeepSeek Harness, Minimal 模式）append-only 会话日志分析器。

设计前提（重要）：
  本机未发现可直接对接的 DSH 会话日志 schema 样本（lightharness 的 append-only
  `编辑日志格式.md` 是「编辑+check」格式，不是 Agent 会话轨迹）。因此本脚本
  **不假设任何私有格式**，而是：
    1. 定义一份显式、公开的规范化中间格式（NormalizedEvent，见 §文档）；
    2. 提供 3 个 adapter（规范化 JSONL / OpenAI 风格 messages / 编辑日志格式）；
    3. 对未知格式给出明确的 `unparsed` 报告，绝不猜测、绝不静默丢行。

规范化事件（每行一个 JSON 对象，字段均可缺省，缺省时按下方默认值）：
  {
    "seq": 0,                      # 轮次序号，从 0 递增
    "role": "assistant",           # user | assistant | tool | system
    "kind": "tool_call",           # message | tool_call | tool_result | error | edit | check
    "tool": "Bash",                # Bash | Edit | Write | ... (仅 tool_call/tool_result)
    "content": "...",              # 文本/命令/输出/报错内容
    "tokens_in": 0, "tokens_out": 0,
    "ts": "2026-11-15T10:00:00+08:00",   # 可选，ISO8601
    "ok": true                     # 可选，check/运行结果是否成功
  }

输出指标（对应原方案「度量」表）：
  完成度   —— 由 run_suite.py 的 report 提供，本脚本只合并
  可靠性   —— first_run_failed, edit_run_cycles, error_recovery_count
  成本     —— total_tokens_in/out, total_tokens, wall_clock_sec
  光明专项 —— semantic_acquisition_cost（前 N 轮的关键字猜测轮数）、
              l4_first_try_success（Track B）、boundary_error_rate（Track B）

用法：
  python3 dsh_analyze.py --log trial.jsonl --suite-report report.json --out metrics.json
  python3 dsh_analyze.py --log trial.jsonl --adapter openai --track B --out metrics.json
  python3 dsh_analyze.py --selftest
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

# ---------------------------------------------------------------- 关键字猜测信号
# 原方案「前 N 轮有多少轮在搜索/猜测关键字含义」——这里给出**可操作化定义**：
# 命中任一模式即计 1 轮（同一轮多次命中只计 1）。这些模式是可审计的正则，不是 LLM 判断。
GUESS_PATTERNS = [
    # 1) 在文档/示例里检索 L0 关键字
    r"(grep|rg|find|cat|sed|search).{0,80}(L0|核心字|关键字|keywords?|语法|syntax)",
    r"(grep|rg).{0,60}(若|遍|当|设|段|导|引|结束引|印|返)",
    # 2) 光明编译器的「未定义关键字/标识符/语法」报错
    r"(未定义|未识别|unknown|undefined|unexpected|NameError|SyntaxError).{0,60}"
    r"(若|遍|当|设|段|导|引|字|keyword|identifier|token)",
    r"L\d{4}.{0,40}(关键|语法|词法|关键字)",
    # 3) Agent 文本里显式表达「猜/试关键字」
    r"(试(一)?试|猜测|不确定|可能是|查(一)?下|文档里|应该是).{0,40}"
    r"(若|遍|当|设|段|导|引|关键字|L0|写法)",
    r"(which|what|guess|try).{0,40}(keyword|L0|若|遍|设|段)\??",
]
GUESS_RE = [re.compile(p, re.I) for p in GUESS_PATTERNS]

# 跨语言边界错误（Track B）
BOUNDARY_PATTERNS = [
    r"(编码|encoding|utf-?8|UnicodeDecodeError|UnicodeEncodeError|gbk)",
    r"(ctypes|ArgumentError|TypeError).{0,80}(str|bytes|c_char_p|int|void\s*\*)",
    r"(段错误|Segmentation|SIGSEGV|生命周期|lifetime|悬垂|dangling|use.after.free)",
    r"(FFI|dlopen|undefined symbol|so\b|动态库).{0,60}(fail|error|找不到|失败)",
]
BOUNDARY_RE = [re.compile(p, re.I) for p in BOUNDARY_PATTERNS]

L4_OK_PATTERNS = [r"(L4|引\s*(Python|C|Go|MoonBit)|FFI|外部函数).{0,60}(成功|通过|pass|ok|编译成功)"]
L4_FAIL_PATTERNS = [r"(L4|引\s*(Python|C|Go|MoonBit)|FFI|外部函数).{0,60}(失败|报错|fail|error)"]
L4_OK_RE = [re.compile(p, re.I) for p in L4_OK_PATTERNS]
L4_FAIL_RE = [re.compile(p, re.I) for p in L4_FAIL_PATTERNS]

EDIT_TOOLS = {"edit", "write", "replace", "patch", "安全替换", "编辑", "写文件"}
RUN_TOOLS = {"bash", "shell", "exec", "run", "terminal", "命令"}
# 「探查/检索」类命令不算运行被测程序（grep/cat/ls/find/which/pip/...）
PROBE_RE = re.compile(
    r"^\s*(grep|rg|cat|head|tail|sed|awk|ls|find|which|whereis|pip|uv|"
    r"cd|pwd|echo|man|help|git\s+(status|log|show)|python\s+-c)", re.I)
# 「运行被测程序」的判定：命令里出现编译/运行入口
EXEC_RE = re.compile(
    r"(minilog|minibridge|light\s+(run|compile)|lightc|python3?\s+\S+\.py|"
    r"go\s+(build|run)|cargo\s+(build|run)|g\+\+|gcc|moon\s+build|"
    r"run_suite|pytest|make\b)", re.I)


# ---------------------------------------------------------------- adapters
def _norm(seq, role="assistant", kind="message", tool="", content="",
          tokens_in=0, tokens_out=0, ts=None, ok=None):
    d = {"seq": seq, "role": role, "kind": kind, "tool": tool,
         "content": content or "", "tokens_in": tokens_in,
         "tokens_out": tokens_out}
    if ts:
        d["ts"] = ts
    if ok is not None:
        d["ok"] = ok
    return d


def adapter_normalized(lines):
    """已规范化 JSONL：逐行取字段，缺字段补默认。"""
    out, unparsed = [], []
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            unparsed.append(i + 1)
            continue
        if not isinstance(d, dict):
            unparsed.append(i + 1)
            continue
        out.append(_norm(
            seq=d.get("seq", len(out)), role=d.get("role", "assistant"),
            kind=d.get("kind", "message"), tool=d.get("tool", ""),
            content=str(d.get("content", "")),
            tokens_in=int(d.get("tokens_in", 0) or 0),
            tokens_out=int(d.get("tokens_out", 0) or 0),
            ts=d.get("ts"), ok=d.get("ok")))
    return out, unparsed


def adapter_openai(lines):
    """OpenAI 风格：每行是 {messages:[...], usage:{...}} 或单条 message。"""
    out, unparsed = [], []
    seq = 0
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            unparsed.append(i + 1)
            continue
        if not isinstance(d, dict):
            unparsed.append(i + 1)
            continue
        usage = d.get("usage", {}) or {}
        ti, to = int(usage.get("prompt_tokens", 0) or 0), \
                 int(usage.get("completion_tokens", 0) or 0)
        msgs = d.get("messages") if isinstance(d.get("messages"), list) else [d]
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role", "assistant")
            content = m.get("content", "") or ""
            tool = m.get("name", "") or ""
            if isinstance(content, list):  # 多模态 content
                content = " ".join(str(x.get("text", "")) for x in content
                                   if isinstance(x, dict))
            kind = "tool_result" if role == "tool" else (
                "tool_call" if m.get("tool_calls") else "message")
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function", {}) or {}
                    out.append(_norm(seq, "assistant", "tool_call",
                                     fn.get("name", ""),
                                     str(fn.get("arguments", "")), ts=d.get("ts")))
                    seq += 1
            out.append(_norm(seq, role, kind, tool, str(content),
                             ti if seq == 0 else 0, to if seq == 0 else 0,
                             ts=d.get("ts")))
            seq += 1
    return out, unparsed


def adapter_editlog(lines):
    """lightharness 编辑日志格式（docs/编辑日志格式.md schema v1）。

    一条记录 = 一次编辑 + 前后各一次 check。展开为 3 个规范化事件：
    check_before → edit → check_after。token 字段在该格式中不存在，**不臆造**，记 0
    并在输出里置 token_coverage=none。
    """
    out, unparsed = [], []
    seq = 0
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            unparsed.append(i + 1)
            continue
        if "schema_version" not in d or "diff" not in d:
            unparsed.append(i + 1)
            continue
        ts = d.get("ts")
        # 顺序必须是 check_before → edit → check_after（该格式一条记录即一次编辑循环）
        cb = d.get("check_before")
        if isinstance(cb, dict):
            out.append(_norm(seq, "tool", "check", "check",
                             str(cb.get("message", "") or ""),
                             ts=ts, ok=bool(cb.get("ok"))))
            seq += 1
        diff = d.get("diff") or {}
        body = diff.get("unified") or diff.get("after") or ""
        out.append(_norm(seq, "assistant", "edit", "Edit", str(body), ts=ts))
        seq += 1
        ca = d.get("check_after")
        if isinstance(ca, dict):
            out.append(_norm(seq, "tool", "check", "check",
                             str(ca.get("message", "") or ""),
                             ts=ts, ok=bool(ca.get("ok"))))
            seq += 1
    return out, unparsed


ADAPTERS = {"normalized": adapter_normalized, "openai": adapter_openai,
            "editlog": adapter_editlog}


# ---------------------------------------------------------------- 指标
def _text(ev):
    return str(ev.get("content", ""))


def _is_guess(ev):
    t = _text(ev)
    # 只在 Agent 侧动作（工具调用 / 文本 / 工具返回的报错）里找信号
    return any(r.search(t) for r in GUESS_RE)


def analyze(events, track="A", n_window=8, suite_report=None):
    n = len(events)
    ti = sum(int(e.get("tokens_in", 0) or 0) for e in events)
    to = sum(int(e.get("tokens_out", 0) or 0) for e in events)

    # wall clock：有 ts 就算首尾差；无 ts 记 None，不外推
    tss = [e["ts"] for e in events if e.get("ts")]
    wall = None
    if len(tss) >= 2:
        def parse(s):
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None
        ps = [parse(s) for s in tss]
        ps = [p for p in ps if p is not None]
        if len(ps) >= 2:
            # 统一到 naive UTC 以便相减（带/不带时区混用时按各自原值比较）
            try:
                wall = round((max(ps) - min(ps)).total_seconds(), 2)
            except TypeError:
                wall = None

    # 编辑-运行循环：一次 edit 后紧跟一次 run 工具调用算一个循环
    cycles, pending_edit = 0, False
    first_run_failed = None
    run_seen = 0
    FAIL_RE = re.compile(r"(error|failed|traceback|编译失败|报错|exit code [1-9]|non-zero)", re.I)
    OK_RE = re.compile(r"(pass|ok|成功|exit code 0)", re.I)
    for e in events:
        tool = str(e.get("tool", "")).lower()
        kind = e.get("kind")
        if kind == "edit" or tool in EDIT_TOOLS:
            pending_edit = True
            continue
        # 只把「执行命令」类事件当作一次运行；tool_result / message 里的报错文本
        # 属于上一轮运行的回显，不计入「首次运行」，否则会把中间轮误判为首次。
        is_check = kind == "check" and e.get("ok") is not None
        cmd = _text(e)
        is_exec_call = (tool in RUN_TOOLS
                        and kind in ("tool_call", "check", "")
                        and not PROBE_RE.match(cmd)
                        and (EXEC_RE.search(cmd) or is_check))
        if not is_exec_call:
            continue
        run_seen += 1
        if pending_edit:
            cycles += 1
            pending_edit = False
        if first_run_failed is None:
            ok = e.get("ok")
            txt = _text(e)
            # 关键：tool_call 的 content 是**命令文本**，可能自带 "error" 等字样
            # （如 `--level=error`），绝不能拿命令文本判失败。
            # 只有 tool_result / check 的**输出文本**才用于失败匹配。
            is_output = (kind in ("tool_result", "check") or
                         e.get("role") == "tool" or ok is not None)
            if ok is False:
                first_run_failed = True
            elif ok is True:
                first_run_failed = False
            elif is_output and FAIL_RE.search(txt) and not OK_RE.search(txt):
                first_run_failed = True
            elif is_output and OK_RE.search(txt):
                first_run_failed = False
            # 其余（纯命令文本且无 ok）不下结论，等后续输出/check 事件
    if first_run_failed is None:
        first_run_failed = False  # 无运行事件时不猜

    # 错误恢复：一次报错之后的下一轮 edit 计 1 次恢复
    recovery, in_error = 0, False
    for e in events:
        txt = _text(e).lower()
        if e.get("ok") is False or re.search(r"(error|failed|traceback|失败|报错)", txt):
            in_error = True
        elif in_error and (e.get("kind") == "edit" or
                           str(e.get("tool", "")).lower() in EDIT_TOOLS):
            recovery += 1
            in_error = False

    # 语义习得成本：前 N 轮里命中关键字猜测模式的**轮数**（按 seq 去重）
    guess_rounds = set()
    for e in events[:n_window]:
        if _is_guess(e):
            guess_rounds.add(e.get("seq", 0))
    # 首次出现 L0 正确用法之前的猜测轮数，作为第二观测量
    first_l0_seq = None
    L0_USE = re.compile(r"(^|\s)(若|遍|当|设|段|导|返|印)\s", re.M)
    for e in events:
        if e.get("kind") == "edit" and L0_USE.search(_text(e)):
            first_l0_seq = e.get("seq")
            break

    # Track B 专项
    l4_first, boundary_errors, l4_attempts = None, 0, 0
    if track == "B":
        for e in events:
            t = _text(e)
            if any(r.search(t) for r in L4_OK_RE + L4_FAIL_RE):
                l4_attempts += 1
                if l4_first is None:
                    l4_first = not any(r.search(t) for r in L4_FAIL_RE)
            if any(r.search(t) for r in BOUNDARY_RE):
                boundary_errors += 1
    boundary_rate = (boundary_errors / l4_attempts) if l4_attempts else None

    result = {
        "track": track,
        "event_count": n,
        # 成本
        "total_tokens_in": ti,
        "total_tokens_out": to,
        "total_tokens": ti + to,
        "token_coverage": "full" if (ti + to) > 0 else "none",
        "wall_clock_sec": wall,
        # 可靠性
        "first_run_failed": first_run_failed,
        "edit_run_cycles": cycles,
        "run_event_count": run_seen,
        "error_recovery_count": recovery,
        # 光明专项
        "semantic_acquisition": {
            "window_n": n_window,
            "guess_rounds": len(guess_rounds),
            "guess_seq": sorted(guess_rounds),
            "first_l0_usage_seq": first_l0_seq,
            "patterns": GUESS_PATTERNS,
        },
        # Track B
        "track_b": {
            "l4_attempts": l4_attempts,
            "l4_first_try_success": l4_first,
            "boundary_error_count": boundary_errors,
            "boundary_error_rate": boundary_rate,
        } if track == "B" else None,
        "suite": None,
    }
    if suite_report:
        result["suite"] = {
            "passed": suite_report.get("passed"),
            "total": suite_report.get("total"),
            "pass_rate": (suite_report.get("passed", 0) /
                          max(suite_report.get("total", 1), 1)),
        }
    return result


def selftest():
    """合成 3 段轨迹，验证各 adapter 与指标计算。"""
    print("== selftest ==")
    # 1) normalized：前 3 轮在猜关键字，之后编辑+运行成功
    evs = [
        _norm(0, "assistant", "tool_call", "Bash",
              "grep -rn 'L0 核心字' docs/  # 查关键字", tokens_in=100, tokens_out=30,
              ts="2026-11-15T10:00:00"),
        _norm(1, "assistant", "tool_result", "Bash",
              "SyntaxError: 未定义关键字 若", tokens_in=50, tokens_out=10,
              ts="2026-11-15T10:00:30"),
        _norm(2, "assistant", "message", "",
              "试一下 遍 的写法，可能是 遍 x 于 y", tokens_in=80, tokens_out=40,
              ts="2026-11-15T10:01:00"),
        _norm(3, "assistant", "edit", "Edit", "段 主():\n  遍 行 于 行表: 印(行)",
              tokens_in=90, tokens_out=60, ts="2026-11-15T10:02:00"),
        _norm(4, "assistant", "tool_call", "Bash", "./minilog filter --level=error",
              tokens_in=60, tokens_out=20, ts="2026-11-15T10:03:00"),
        _norm(5, "assistant", "tool_result", "Bash", "exit code 0, all pass",
              ok=True, tokens_in=30, tokens_out=5, ts="2026-11-15T10:03:30"),
    ]
    m = analyze(evs, track="A", n_window=8)
    assert m["total_tokens"] == 100 + 30 + 50 + 10 + 80 + 40 + 90 + 60 + 60 + 20 + 30 + 5
    assert m["semantic_acquisition"]["guess_rounds"] == 3, m["semantic_acquisition"]
    assert m["edit_run_cycles"] == 1, m["edit_run_cycles"]
    assert m["wall_clock_sec"] == 210.0, m["wall_clock_sec"]
    assert m["first_run_failed"] is False, m["first_run_failed"]
    assert m["semantic_acquisition"]["first_l0_usage_seq"] == 3
    print("  normalized OK: tokens=%d cycles=%d guess=%d wall=%s" %
          (m["total_tokens"], m["edit_run_cycles"],
           m["semantic_acquisition"]["guess_rounds"], m["wall_clock_sec"]))

    # 2) Track B 边界错误
    evs_b = [
        _norm(0, "assistant", "tool_call", "Bash", "light run minibridge.light",
              tokens_in=100, tokens_out=40),
        _norm(1, "assistant", "tool_result", "Bash",
              "L4 引 C 编译失败: undefined symbol", ok=False,
              tokens_in=40, tokens_out=10),
        _norm(2, "assistant", "edit", "Edit", "加载库 ...",
              tokens_in=60, tokens_out=30),
        _norm(3, "assistant", "tool_result", "Bash",
              "ctypes.ArgumentError: expected bytes, got str (编码 utf-8)",
              ok=False, tokens_in=40, tokens_out=10),
        _norm(4, "assistant", "tool_result", "Bash",
              "L4 FFI 调用成功, pass", ok=True, tokens_in=30, tokens_out=5),
    ]
    mb = analyze(evs_b, track="B")
    assert mb["track_b"]["l4_first_try_success"] is False, mb["track_b"]
    assert mb["track_b"]["boundary_error_count"] >= 1, mb["track_b"]
    assert mb["track_b"]["l4_attempts"] == 2, mb["track_b"]
    print("  track B OK: l4_first=%s attempts=%d boundary=%d" %
          (mb["track_b"]["l4_first_try_success"], mb["track_b"]["l4_attempts"],
           mb["track_b"]["boundary_error_count"]))

    # 3) editlog adapter
    lines = [
        json.dumps({"schema_version": 1, "event_id": "h-1", "ts": "2026-11-15T10:00:00+08:00",
                    "session_id": "s1", "task_id": None, "agent": None, "repo": "x",
                    "file": "a.light", "file_hash_before": "a" * 16,
                    "file_hash_after": "b" * 16, "edit_kind": "PATCH",
                    "diff": {"after": "设 甲 为 1"},
                    "check_before": {"ok": False, "code": "L4001", "severity": "error",
                                     "stage": "parse", "message": "语法错误"},
                    "check_after": {"ok": True, "code": None, "severity": None,
                                    "stage": None, "message": None},
                    "outcome": "fixed", "light_version": "0.4.2", "backend": "python"}),
    ]
    e3, un = adapter_editlog(lines)
    assert not un and len(e3) == 3, (e3, un)
    assert (e3[0]["ok"] is False and e3[1]["kind"] == "edit"
            and e3[2]["ok"] is True), e3
    m3 = analyze(e3)
    assert m3["token_coverage"] == "none" and m3["total_tokens"] == 0
    print("  editlog OK: %d events, token_coverage=%s" % (len(e3), m3["token_coverage"]))

    # 4) 未知格式不得静默吞掉
    e4, un4 = adapter_normalized(["THIS IS NOT JSON", "{}"])
    assert un4 == [1], un4
    print("  unparsed OK: %s" % un4)
    print("== selftest passed ==")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", help="append-only 会话日志（JSONL）")
    ap.add_argument("--adapter", choices=list(ADAPTERS) + ["auto"], default="auto")
    ap.add_argument("--track", choices=["A", "B"], default="A")
    ap.add_argument("--window", type=int, default=8, help="语义习得观察窗口 N 轮")
    ap.add_argument("--suite-report", default=None, help="run_suite.py --json 的输出")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return 0
    if not a.log:
        print("ERROR: --log required (or use --selftest)", file=sys.stderr)
        return 2
    with open(a.log, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    chosen = a.adapter
    events, unparsed = [], []
    if chosen == "auto":
        # 按「能解析且字段命中率最高」选 adapter，结果写进报告供人工复核
        cands = []
        for name, fn in ADAPTERS.items():
            ev, un = fn(lines)
            hit = sum(1 for e in ev if e.get("tool") or e.get("tokens_in")
                      or e.get("tokens_out"))
            cands.append((hit - len(un) * 2, -len(un), name, ev, un))
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
        _, _, chosen, events, unparsed = cands[0]
        print("auto adapter -> %s (candidates: %s)" %
              (chosen, ", ".join("%s=%d" % (c[2], c[0]) for c in cands)))
    else:
        events, unparsed = ADAPTERS[chosen](lines)

    suite = None
    if a.suite_report:
        with open(a.suite_report, "r", encoding="utf-8") as f:
            suite = json.load(f)
    m = analyze(events, track=a.track, n_window=a.window, suite_report=suite)
    m["adapter"] = chosen
    m["unparsed_lines"] = unparsed
    if unparsed:
        m["warning"] = "%d line(s) could not be parsed; NOT counted in metrics" % len(unparsed)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("metrics -> %s" % a.out)
    print(json.dumps({k: v for k, v in m.items()
                      if k not in ("semantic_acquisition", "track_b")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
