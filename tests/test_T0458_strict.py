# -*- coding: utf-8 -*-
"""T-0458：strict 检测器（别名 / 中文标点 / 省略类型）的验收测试。

覆盖任务卡的完成标准：
* L2 规范样本（单字 + 英文标点 + 显式类型）→ 0 条；
* L1 样本（双字 + 中文标点 + 省略类型）→ 三类都命中，`replacement` 非空（TYPE 除外）；
* 位置断言精确到列，并用 ``python -m cli.light tokens`` 的输出交叉验证一次；
* spec 读不到时抛明确异常，不静默返回空列表。

另外几条是「检测器不该做的事」的护栏：不给非法替换（句号）、不给会改变字符串内容的
替换、不猜 spec 没登记的别名关系。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import ai_strict
from ai_strict import StrictError, StrictFinding, StrictSpecError

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "spec" / "light.spec.json"


# --------------------------------------------------------------------------- #
# 夹具：规范样本 / 非规范样本
# --------------------------------------------------------------------------- #

#: L2 规范写法：单字关键字 + 英文标点 + 显式类型标注。
L2_SAMPLES = [
    "设 甲: 数 = 10。\n",
    "设 甲: 数 = 10。\n若 甲 大于 1 则 返 甲。\n否 返 0。\n",
    "段 加(甲: 数, 乙: 数):\n  返 甲 加 乙。\n",
    "遍 乙 之 [1, 2, 3]:\n  印(乙)。\n",
    "设 名: 串 = \"光明\"。\n印(名)。\n",
    "设 表: 列 = [1, 2]。\n设 典: 典 = {\"端口\": 8080}。\n",
    "常 设 上限: 数 = 3。\n",
]

#: L1 写法：双字关键字 + 中文标点 + 省略类型。
L1_SAMPLE = (
    "设 甲 为 3。\n"
    "如果 甲 大于 1 则：\n"
    "  返回 甲。\n"
    "否则：\n"
    "  返回 0。\n"
    "遍历 乙 之 [1，2]：\n"
    "  打印（乙）。\n"
)


@pytest.fixture(scope="module")
def spec_tables():
    return ai_strict._build_tables(ai_strict.load_spec(SPEC_PATH), str(SPEC_PATH))


def _line_of(source: str, line: int) -> str:
    return source.splitlines()[line - 1]


def _slice(source: str, finding: StrictFinding) -> str:
    """按「行内 [column-1, end_column-1)」切原文——位置口径的自证方式。"""
    return _line_of(source, finding.line)[finding.column - 1:finding.end_column - 1]


def _kinds(findings):
    return {f.kind for f in findings}


# --------------------------------------------------------------------------- #
# 1. 幂等：L2 规范样本 → 0 条
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("source", L2_SAMPLES, ids=lambda s: s.splitlines()[0][:16])
def test_L2规范样本零命中(source):
    """已经是 L2 的代码不该被报——否则归一器会自己制造 churn。"""
    assert ai_strict.check(source) == []


def test_空源码零命中():
    assert ai_strict.check("") == []


def test_只有注释零命中():
    source = "# 全角，标点：在注释里不算代码\n// 打印 也不算\n"
    assert ai_strict.check(source) == []


# --------------------------------------------------------------------------- #
# 2. L1 样本 → 三类都命中，replacement 非空（TYPE 除外）
# --------------------------------------------------------------------------- #


def test_L1样本三类都命中():
    findings = ai_strict.check(L1_SAMPLE)
    assert _kinds(findings) == {"ALIAS", "PUNCT", "TYPE"}


def test_L1样本每条replacement非空且TYPE除外():
    for finding in ai_strict.check(L1_SAMPLE):
        if finding.kind == "TYPE":
            # 类型靠人/agent 判断，检测器不编——留空是契约，不是遗漏。
            assert finding.replacement == ""
            assert "<类型>" in finding.expected
        else:
            assert finding.replacement
            assert finding.replacement != finding.actual


def test_L1样本按行列升序返回():
    findings = ai_strict.check(L1_SAMPLE)
    keys = [(f.line, f.column) for f in findings]
    assert keys == sorted(keys)


def test_同一位置同类规则只报一次():
    findings = ai_strict.check(L1_SAMPLE)
    keys = [(f.line, f.column, f.kind) for f in findings]
    assert len(keys) == len(set(keys))


# --------------------------------------------------------------------------- #
# 3. 位置精确到列（原文切片自证）
# --------------------------------------------------------------------------- #


def test_每条finding的列区间切出的就是actual():
    for finding in ai_strict.check(L1_SAMPLE):
        assert _slice(L1_SAMPLE, finding) == finding.actual, finding


def test_位置从1起且end_column大于column():
    for finding in ai_strict.check(L1_SAMPLE):
        assert finding.line >= 1
        assert finding.column >= 1
        assert finding.end_column > finding.column


def test_汉字按一列计():
    """`打印` 在 `  打印（乙）。` 里是第 3 列，不是第 5 列。"""
    findings = [f for f in ai_strict.check(L1_SAMPLE) if f.kind == "ALIAS"]
    by_actual = {f.actual: f for f in findings}
    assert by_actual["打印"].line == 7
    assert by_actual["打印"].column == 3
    assert by_actual["打印"].end_column == 5


# --------------------------------------------------------------------------- #
# 4. 用 `python -m cli.light tokens` 交叉验证列位置（任务卡点名要做一次）
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"Token\((\w+),\s*(?:'([^']*)'|(\S+?)),\s*L(\d+):C(\d+)\)")


def _cli_tokens(tmp_path: Path, source: str):
    """跑 CLI 的 tokens 子命令，返回 [(类型, 文本, 行, 列)]。"""
    path = tmp_path / "sample.light"
    path.write_text(source, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "cli.light", "tokens", str(path)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    out = proc.stdout.decode("utf-8", "replace")
    tokens = []
    for match in _TOKEN_RE.finditer(out):
        kind = match.group(1)
        text = match.group(2) if match.group(2) is not None else match.group(3)
        tokens.append((kind, text, int(match.group(4)), int(match.group(5))))
    assert tokens, f"CLI 没吐出任何 token：\n{out[:500]}"
    return tokens


def test_列位置与CLI的tokens输出一致(tmp_path):
    """逐条把 finding 的位置对到 CLI 打印的 L行:C列 上。"""
    source = "设 甲 为 3。\n如果 甲 大于 1 则 返回 甲。\n"
    findings = ai_strict.check(source)
    assert findings, "样本本身应当命中，否则这条交叉验证是空转"

    tokens = _cli_tokens(tmp_path, source)
    at_position = {(line, col): (kind, text) for kind, text, line, col in tokens}

    checked = 0
    for finding in findings:
        key = (finding.line, finding.column)
        assert key in at_position, (
            f"{finding.kind} {finding.actual!r} 报在 {finding.line}:{finding.column}，"
            f"但 CLI 在那个位置没有 token；CLI 有 {sorted(at_position)}"
        )
        kind, text = at_position[key]
        if finding.kind == "PUNCT" and len(finding.actual) > 1:
            # 中文引号是整条字符串：CLI 的 token 值是字符串体，不是引号本身。
            assert kind == "STRING"
            assert finding.actual[1:-1] == text
        elif finding.kind == "TYPE":
            # TYPE 锚在 `设` 这个声明关键字上，区间覆盖到变量名。
            assert kind == "KEYWORD"
            assert text == "设"
        else:
            assert text == finding.actual, f"{kind} token 文本 {text!r} != {finding.actual!r}"
        checked += 1
    assert checked == len(findings)


# --------------------------------------------------------------------------- #
# 5. ALIAS：规则全部来自 spec
# --------------------------------------------------------------------------- #


def test_spec登记的别名逐条可检出(spec_tables):
    """spec 里每个别名都要么被检出、要么给出「为什么不报」的结构化理由。"""
    missing = []
    for alias, main in sorted(spec_tables.alias_to_main.items()):
        report = ai_strict.check_report(f"{alias}。")
        findings = [f for f in report.findings if f.kind == "ALIAS"]
        if findings:
            if len(findings) != 1 or findings[0].replacement != main:
                missing.append((alias, main, [f.replacement for f in findings]))
            continue
        reasons = [s.reason for s in report.skipped_source if s.word == alias]
        if not reasons:
            missing.append((alias, main, "既没检出也没写理由"))
    assert missing == [], f"这些 spec 别名没被检出：{missing}"


def test_词法层是标识符的上下文别名不报但记理由():
    """`属性` 在 spec 里登记为「性」的别名，但词法层发 IDENTIFIER（上下文关键字）。

    检测器不做语法分析，无法把上下文关键字和同名标识符分开，因此不报——但必须
    在 skipped_source 里说清楚，不能悄悄吞掉。
    """
    report = ai_strict.check_report("属性 甲 为 1。\n")
    assert [f for f in report.findings if f.kind == "ALIAS"] == []
    hits = [s for s in report.skipped_source if s.word == "属性"]
    assert hits and "IDENTIFIER" in hits[0].reason


def test_别名替换值等于spec主形式():
    findings = ai_strict.check("如果 甲 则 否 乙。\n")
    pairs = {f.actual: f.replacement for f in findings if f.kind == "ALIAS"}
    assert pairs["如果"] == "若"
    spec = ai_strict.load_spec(SPEC_PATH)
    tables = ai_strict._build_tables(spec, str(SPEC_PATH))
    for actual, replacement in pairs.items():
        assert replacement == tables.alias_to_main[actual]


def test_跳出跳过取spec主形式而非卡面举例():
    """卡面正文写「跳出→跳、跳过→过」，但 spec 登记的「主形式」是 断 / 跃。

    规则表的唯一真相是 spec（任务卡第 3 条），这里按 spec 走；`跳` / `过` 因为
    没登记主形式，会出现在 skipped_spec 里等人补 spec，而不是被悄悄当成规范形。
    """
    findings = [f for f in ai_strict.check("跳出。\n跳过。\n") if f.kind == "ALIAS"]
    assert [(f.actual, f.replacement) for f in findings] == [("跳出", "断"), ("跳过", "跃")]


def test_spec没登记的别名一律跳过不猜():
    """`返回→返`、`定义→设` 在 spec 里没有别名关系登记，检测器不许自己补。"""
    report = ai_strict.check_report("返回 甲。\n定义 乙 为 1。\n")
    assert [f for f in report.findings if f.kind == "ALIAS"] == []
    skipped = {s.word for s in report.skipped_spec if s.rule == "ALIAS"}
    assert {"返回", "定义"} <= skipped


def test_卡面举例但spec完全没条目的词不报():
    """`并且` / `或者` 在 spec.keywords 里根本没有条目——没有关系可依，只能不报。"""
    for source in ("甲 并且 乙。\n", "甲 或者 乙。\n"):
        assert [f for f in ai_strict.check(source) if f.kind == "ALIAS"] == []


def test_标识符里含别名不误报():
    """`打印格式` 是一个标识符，不该被拆成 `打印` + `格式` 再报 ALIAS。"""
    findings = ai_strict.check("设 打印格式 为 \"x\"。\n")
    assert [f for f in findings if f.kind == "ALIAS"] == []


def test_字符里的别名不误报():
    findings = ai_strict.check("设 名: 串 = \"如果 否则 打印\"。\n")
    assert findings == []


# --------------------------------------------------------------------------- #
# 6. PUNCT：中文标点 → 英文，但绝不产出非法代码
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("source,actual,replacement", [
    ("设 甲: 数 = 1；印(甲)。\n", "；", ";"),
    ("设 甲: 数 = 1，2。\n", "，", ","),
    ("若 甲 大于 1：\n  印(1)。\n", "：", ":"),
    ("设 甲: 列 = 【1】。\n", "【", "["),
    ("设 甲: 列 = 【1】。\n", "】", "]"),
    ("设 甲: 典 = ｛1: 2｝。\n", "｛", "{"),
    ("设 甲: 典 = ｛1: 2｝。\n", "｝", "}"),
    ("印（1）。\n", "（", "("),
    ("印（1）。\n", "）", ")"),
])
def test_单字符中文标点映射(source, actual, replacement):
    findings = [f for f in ai_strict.check(source) if f.actual == actual]
    assert len(findings) == 1, f"{actual!r} 应命中一次，实际 {findings}"
    assert findings[0].kind == "PUNCT"
    assert findings[0].replacement == replacement


def test_句号不替换成半角点():
    """spec 明确句号是唯一语句结束符、半角 `.` 会变成小数点——替换即产出非法代码。"""
    findings = ai_strict.check("设 甲: 数 = 1。\n")
    assert findings == []
    assert "。" not in ai_strict._build_tables(
        ai_strict.load_spec(SPEC_PATH), str(SPEC_PATH)).punct_to_ascii


def test_中文双引号按整条字符串替换():
    findings = ai_strict.check("印「光明」。\n")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind == "PUNCT"
    assert finding.actual == "「光明」"
    assert finding.expected == '"光明"'
    assert finding.replacement == '"光明"'
    assert _slice("印「光明」。\n", finding) == "「光明」"


def test_中文单引号按整条字符串替换():
    findings = ai_strict.check("印『光明』。\n")
    assert [(f.actual, f.replacement) for f in findings] == [("『光明』", "'光明'")]


def test_字符串体含目标引号时跳过并记录():
    """`「他说"好"」` 直接换成 `"他说"好""` 会截断字符串——只报告跳过，不硬给替换。"""
    report = ai_strict.check_report('印「他说"好"」。\n')
    assert [f for f in report.findings if f.actual.startswith("「")] == []
    assert any(s.rule == "PUNCT" and "ASCII" in s.reason for s in report.skipped_source)


def test_跨行字符串跳过并记录():
    report = ai_strict.check_report("印「第一行\n第二行」。\n")
    assert [f for f in report.findings if f.actual.startswith("「")] == []
    assert any("跨行" in s.reason for s in report.skipped_source)


def test_字符串体里的全角逗号不算标点():
    """`「，」` 里的 `，` 是字符串内容，不该被单独报成 COMMA 替换。"""
    findings = ai_strict.check("印「，」。\n")
    assert [f for f in findings if f.actual == "，"] == []
    # 整条字符串仍按引号规则给替换（字符串体原样保留，全角逗号不单独动）。
    assert [(f.actual, f.replacement) for f in findings] == [("「，」", '"，"')]


# --------------------------------------------------------------------------- #
# 7. TYPE：只报不给替换
# --------------------------------------------------------------------------- #


def test_省略类型报TYPE且不给替换():
    findings = [f for f in ai_strict.check("设 甲 为 10。\n") if f.kind == "TYPE"]
    assert len(findings) == 1
    assert findings[0].actual == "设 甲"
    assert findings[0].replacement == ""
    assert findings[0].column == 1
    assert findings[0].end_column == 4


def test_已有类型标注不报TYPE():
    assert [f for f in ai_strict.check("设 甲: 数 = 10。\n") if f.kind == "TYPE"] == []


def test_常量修饰符后的声明仍算语句起始():
    findings = [f for f in ai_strict.check("常 设 上限 为 3。\n") if f.kind == "TYPE"]
    assert len(findings) == 1
    assert findings[0].column == 3  # 锚在 `设` 上，不是行首的 `常`（列 1）


def test_分号后的声明也算语句起始():
    findings = [f for f in ai_strict.check("设 甲: 数 = 1；设 乙 为 2。\n") if f.kind == "TYPE"]
    assert [f.actual for f in findings] == ["设 乙"]


def test_多目标声明跳过并记录():
    report = ai_strict.check_report("设 甲, 乙 为 1。\n")
    assert [f for f in report.findings if f.kind == "TYPE"] == []
    assert any(s.rule == "TYPE" for s in report.skipped_source)


# --------------------------------------------------------------------------- #
# 8. spec 读不到 → 明确异常，不静默返回空列表
# --------------------------------------------------------------------------- #


def test_不存在的spec路径抛异常而不是返回空列表(tmp_path):
    missing = tmp_path / "nope" / "light.spec.json"
    with pytest.raises(StrictSpecError) as excinfo:
        ai_strict.check("设 甲: 数 = 1。\n", spec_path=missing)
    assert "spec 不存在" in str(excinfo.value)


def test_spec不是JSON抛异常(tmp_path):
    bad = tmp_path / "light.spec.json"
    bad.write_text("{ 这不是 json", encoding="utf-8")
    with pytest.raises(StrictSpecError) as excinfo:
        ai_strict.check("设 甲: 数 = 1。\n", spec_path=bad)
    assert "不是合法 JSON" in str(excinfo.value)


def test_spec缺keywords段抛异常(tmp_path):
    bad = tmp_path / "light.spec.json"
    bad.write_text(json.dumps({"operators": []}), encoding="utf-8")
    with pytest.raises(StrictSpecError) as excinfo:
        ai_strict.check("设 甲: 数 = 1。\n", spec_path=bad)
    assert "keywords" in str(excinfo.value)


def test_spec顶层不是对象抛异常(tmp_path):
    bad = tmp_path / "light.spec.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(StrictSpecError) as excinfo:
        ai_strict.check("设 甲: 数 = 1。\n", spec_path=bad)
    assert "顶层" in str(excinfo.value)


def test_异常是StrictError的子类():
    assert issubclass(StrictSpecError, StrictError)


# --------------------------------------------------------------------------- #
# 9. 分词失败 / 参数校验
# --------------------------------------------------------------------------- #


def test_源码无法分词抛StrictError():
    with pytest.raises(StrictError) as excinfo:
        ai_strict.check("设 甲: 数 = “中文弯引号”。\n")
    assert "无法分词" in str(excinfo.value)


def test_不支持的canonical抛ValueError():
    with pytest.raises(ValueError):
        ai_strict.check("设 甲: 数 = 1。\n", canonical="L1")


def test_source必须是字符串():
    with pytest.raises(TypeError):
        ai_strict.check(None)


# --------------------------------------------------------------------------- #
# 10. 幂等与结构化输出
# --------------------------------------------------------------------------- #


def _apply(source: str, findings) -> str:
    """把带 replacement 的 finding 一次性套回源码（同位置多个时按 kind 顺序）。"""
    lines = source.splitlines(keepends=True)
    per_line = {}
    for finding in findings:
        if finding.replacement:
            per_line.setdefault(finding.line, []).append(finding)
    for line_no, items in per_line.items():
        text = lines[line_no - 1]
        for finding in sorted(items, key=lambda f: f.column, reverse=True):
            start = finding.column - 1
            end = finding.end_column - 1
            assert text[start:end] == finding.actual, (text, finding)
            text = text[:start] + finding.replacement + text[end:]
        lines[line_no - 1] = text
    return "".join(lines)


def test_套用替换后只剩TYPE未解():
    """归一器是收敛的：ALIAS/PUNCT 全部消掉，只剩需要人判断的 TYPE。"""
    source = L1_SAMPLE
    rewritten = _apply(source, ai_strict.check(source))
    remaining = _kinds(ai_strict.check(rewritten))
    assert remaining == {"TYPE"}, ai_strict.check(rewritten)


def test_套用替换两轮后稳定():
    """再套一轮不该再变（幂等），否则归一器会自己振荡。"""
    first = _apply(L1_SAMPLE, ai_strict.check(L1_SAMPLE))
    second = _apply(first, ai_strict.check(first))
    assert first == second


def test_report可序列化为JSON():
    report = ai_strict.check_report(L1_SAMPLE)
    payload = report.to_dict()
    text = json.dumps(payload, ensure_ascii=False)
    back = json.loads(text)
    assert back["spec_path"].endswith("light.spec.json")
    assert len(back["findings"]) == len(report.findings)
    for item in back["findings"]:
        assert set(item) == {"line", "column", "end_column", "kind", "actual",
                             "expected", "replacement", "message"}
        assert item["kind"] in ai_strict.KINDS


def test_skipped_spec列出spec缺信息的别名():
    report = ai_strict.check_report("设 甲: 数 = 1。\n")
    words = {s.word for s in report.skipped_spec if s.rule == "ALIAS"}
    assert words, "spec 里确实有一批多字词没登记主形式，清单不该是空的"
    assert all(s.reason for s in report.skipped_spec)


# --------------------------------------------------------------------------- #
# 11. 纯模块护栏：不写盘、不碰禁止路径
# --------------------------------------------------------------------------- #


def test_模块不写盘(tmp_path, monkeypatch):
    """检测器只返回结构化结果，绝不自己改源码。"""
    target = tmp_path / "keep.light"
    original = "设 甲 为 1。\n"
    target.write_text(original, encoding="utf-8")

    before = target.read_text(encoding="utf-8")
    ai_strict.check(before)
    assert target.read_text(encoding="utf-8") == before == original


def test_模块源码不引用禁止修改的模块():
    """任务卡禁止改 diagnostics / cli / spec / lexer —— 本模块也不许 import 它们。"""
    source = (REPO_ROOT / "src" / "ai_strict.py").read_text(encoding="utf-8")
    for forbidden in ("diagnostics", "cli.light", "spec.build_spec"):
        assert forbidden not in source.replace("src/diagnostics", ""), forbidden


def test_finding位置校验拒绝非法值():
    with pytest.raises(ValueError):
        StrictFinding(line=0, column=1, end_column=1, kind="ALIAS",
                      actual="如果", expected="若", replacement="若", message="")
    with pytest.raises(ValueError):
        StrictFinding(line=1, column=2, end_column=1, kind="ALIAS",
                      actual="如果", expected="若", replacement="若", message="")
    with pytest.raises(ValueError):
        StrictFinding(line=1, column=1, end_column=2, kind="ALIAS",
                      actual="如果", expected="若", replacement="", message="")
    with pytest.raises(ValueError):
        StrictFinding(line=1, column=1, end_column=2, kind="NOPE",
                      actual="如果", expected="若", replacement="若", message="")