# -*- coding: utf-8 -*-
"""T-0465 验收：AI 友好度公开报告的「有据可查」约束。

这张卡最容易出的错不是写得不好，而是**编数字**。所以测试不检查文采，
只检查四件事：

1. 报告在、四段齐（北极星四项 / 与 R222 对比 / 错误码 Top10 / 结论）；
2. 没有 ``TODO`` / ``TBD`` / ``待填`` 这类未完成占位；
3. 每个百分比 / ``pass@`` / ``P50`` / ``ms`` 数字都带来源标记（``实测`` / ``bench`` / ``stub``），
   出现 ``未跑`` 必须紧跟「（原因）」；
4. **报告里的关键数字能从数据文件复算出来**（冷启动 JSON、延迟 JSON、stub JSON），
   报告提到的数据文件必须真实存在且能解析。

第 4 条是关键：只写「有来源」而来源文件不存在，等于给假数字盖了个章。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_DOCS = REPO_ROOT / "docs" / "bench"
REPORT = BENCH_DOCS / "AI友好度_20261126.md"
COLDSTART = BENCH_DOCS / "coldstart_20261125.json"
LATENCY = BENCH_DOCS / "ai_check_latency_20261125.json"
STUB = BENCH_DOCS / "stub_run_20261125.json"

REQUIRED_SECTIONS = ("北极星四项", "与 R222", "错误码 Top10", "结论")
PROVENANCE = ("实测", "bench", "stub")
PLACEHOLDERS = ("TODO", "TBD", "待填")
METRIC_RE = re.compile(r"pass@|\d%|P50|P90|\bms\b|毫秒")


def read_report() -> str:
    assert REPORT.is_file(), f"报告不存在: {REPORT}"
    return REPORT.read_text(encoding="utf-8")


def test_report_exists_and_has_four_sections():
    text = read_report()
    assert len(text) > 2000, "报告太短，四个指标段写不下"
    for section in REQUIRED_SECTIONS:
        assert section in text, f"报告缺段落：{section}"


def test_no_placeholder_left():
    text = read_report()
    for marker in PLACEHOLDERS:
        assert marker not in text, f"报告里还有未完成占位：{marker}"


def test_every_metric_line_has_provenance():
    """每个带指标数字的行都必须带来源标记，防止「看起来专业的裸数字」。"""
    offenders = []
    for lineno, line in enumerate(read_report().splitlines(), 1):
        if not METRIC_RE.search(line):
            continue
        if "未跑（" in line:
            continue                      # 未跑行由下一条用例单独管原因
        if not any(tag in line for tag in PROVENANCE):
            offenders.append((lineno, line.strip()[:80]))
    assert not offenders, f"这些行有数字但没写来源：{offenders}"


def test_unrun_always_has_reason_in_parentheses():
    """`未跑` 必须紧跟「（原因）」，原因不能空。"""
    text = read_report()
    bare = re.findall(r"未跑(?![（(])", text)
    assert not bare, "`未跑` 后面必须跟（原因）"
    reasons = re.findall(r"未跑[（(]([^）)]*)[）)]", text)
    assert reasons, "报告应当至少有一处「未跑（原因）」——发现率那段"
    for reason in reasons:
        assert len(reason.strip()) >= 2, f"未跑的原因太短或是空的：{reason!r}"


def test_report_numbers_match_data_files():
    """报告里的关键数字必须能从数据文件复算，且数据文件本身真实存在。"""
    for path in (COLDSTART, LATENCY, STUB):
        assert path.is_file(), f"报告引用的数据文件不存在: {path.name}"
        json.loads(path.read_text(encoding="utf-8"))    # 必须能解析

    coldstart = json.loads(COLDSTART.read_text(encoding="utf-8"))
    summary = coldstart["summary"]
    tasks = coldstart["tasks"]
    assert len(tasks) == 40, "冷启动实验应是 2 臂 × 20 条"
    assert {t["arm"] for t in tasks} == {"with_entry", "no_entry"}

    text = read_report()
    for arm in ("with_entry", "no_entry"):
        s = summary[arm]
        total = s["total"]
        pass1 = s["pass1_count"]
        passed = s["passed_count"]
        # 百分比按一位小数核对；计数按「x/20」核对 —— 两种写法都在报告里出现
        assert f"{pass1 / total * 100:.1f}%" in text, f"{arm} 的 pass@1 百分比与数据不符"
        assert f"{pass1}/{total}" in text, f"{arm} 的 pass@1 计数与数据不符"
        assert f"{passed / total * 100:.1f}%" in text, f"{arm} 的 pass@3 百分比与数据不符"
        assert f"{passed}/{total}" in text, f"{arm} 的 pass@3 计数与数据不符"
        heal = s["self_heal_rate"]
        assert f"{heal * 100:.1f}%" in text, f"{arm} 的自愈率与数据不符"

    latency = json.loads(LATENCY.read_text(encoding="utf-8"))
    abspath_p50_ms = round(latency["summary"]["abspath"]["p50"] * 1000)
    assert f"{abspath_p50_ms} ms" in text, "ai check 的 P50（绝对路径）与延迟数据不符"
    assert latency["summary"]["abspath"]["rc_histogram"].get("0") == 60, \
        "绝对路径口径应当 60/60 rc=0 —— 否则延迟数字没有意义"
    assert latency["summary"]["relpath"]["rc_histogram"].get("1") == 60, \
        "相对路径口径应当 60/60 rc=1（当前的路径解析缺陷）"

    stub = json.loads(STUB.read_text(encoding="utf-8"))["summary"]
    assert stub["pass_rate"] == 1.0 and stub["passed"] == 20
    assert "20/20" in text and "stub" in text, "stub 基线（20/20）必须在报告里标明"


def test_report_cites_its_evidence_files():
    """报告必须点名它引用的三份原始数据，读者才能自己复算。"""
    text = read_report()
    for path in (COLDSTART, LATENCY, STUB):
        assert path.name in text, f"报告没引用数据文件：{path.name}"


def test_data_files_are_tracked_by_git():
    """数据文件必须**真的进了 git**，否则换台机器复算不出来。

    仓根 `.gitignore` 有一条 `*.json`，会把这里的原始数据一起吃掉；
    docs/bench/.gitignore 用 `!*.json` 把它们捞回来。这条用例就是防止有人
    本地看着绿、一合入/换机就红（docs/LightAgentBench说明.md §2 记过同一个坑）。
    """
    targets = ["docs/bench/" + p.name for p in (COLDSTART, LATENCY, STUB)]
    proc = subprocess.run(["git", "ls-files", "--"] + targets, cwd=str(REPO_ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    assert proc.returncode == 0, f"git ls-files 跑不起来: {proc.stderr}"
    listed = proc.stdout.split()
    missing = [t for t in targets if t not in listed]
    assert not missing, f"这些数据文件还没被 git 跟踪（会被仓根 *.json 忽略）：{missing}"
