# -*- coding: utf-8 -*-
r"""动态 CI 徽章生成器（R137 D 线建）。

## 为什么要写它

README 顶部的「CI 门禁」徽章此前是**手工写死**的静态快照
（`7912 passed/0 failed`，指向外部 shields.io 与 `docs/known-issues/`）。
静态徽章有两个硬伤：

1. **会撒谎且没人知道它什么时候开始撒的**——数字一旦写进 README，
   与仓库真实状态之间就没有任何自动校验，红了几百条也照样绿着。
2. **依赖外部服务**——shields.io 在本机/自托管 Gitea 环境可能不可达，
   徽章直接裂图，而裂图同样看不出 CI 到底是红是绿。

本脚本把徽章改成**本地生成**：真跑一次 pytest（或读一份既有结果文件），
把 passed / failed / coverage 落成 `docs/ci_badge.json` + `docs/ci_badge.svg`，
README 直接引用本地 SVG。**不联网**，SVG 用纯字符串模板拼，无第三方依赖。

## 与 tools/ci/spec_coverage.py 的关系

先读了它（R137 D 线第 1 步）。结论：**口径不同，无法复用**。
`spec_coverage.py` 量的是「功能对标清单的 done 条数棘轮」
（数据来自 `任务书/功能对标清单_harness.json`，判据是完成度只升不降）；
本脚本量的是「测试通过数 / 覆盖率」——两者没有公共的度量逻辑可抽。
沿用它的只是**工程约定**：`--root` 参数、中文 docstring 讲清口径与判据、
输出 JSON 带 `version` + `note` 说明、RC 语义（0 通过 / 1 红 / 2 用法错）。

## 数据来源（诚实性红线：绝不硬编码数字冒充跑出来的结果）

1. **实跑**（默认）：调 `python -m pytest <scope> -q --tb=no`，
   同时产出 junit xml 做权威计数，末尾汇总行做交叉校验。
2. **读既有结果**：`--junit-xml` / `--summary-json` 直接解析。
3. **`--skip-tests`**：只读上一次产物（默认 `--out-json`）便于快速迭代；
   若产物不存在，则 passed/failed/coverage 一律写 `null`、
   `coverage_available` 写 `false`、徽章转灰——**不伪造、不填 0 充数**。

无论哪种来源，`source` 字段都会写明数据究竟从哪来。

## 幂等

- JSON 只有 `generated_at`（系统时间）与 `duration_seconds` 两次跑会不同，
  其余字段结构完全一致。
- **SVG 里不写时间戳**，因此同数据连跑两次产出字节完全一致。

## 用法

```bash
python tools/ci/gen_badge.py --help
python tools/ci/gen_badge.py --skip-tests          # 快速模式，只读已有产物
python tools/ci/gen_badge.py --scope tests/unit/   # 默认即此，真跑
python tools/ci/gen_badge.py --strict              # 有失败则 RC=1（CI 门禁用）
```

## RC 语义

- `0`：徽章已生成（无论测试红绿——徽章本身就是红绿的呈现载体）。
- `1`：`--strict` 下存在 failed/error；或实跑时 pytest 进程级崩溃。
- `2`：用法错误（仓库根不存在 / 结果文件读不动 / 解析不出计数）。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

_HERE = os.path.dirname(os.path.abspath(__file__))
# tools/ci/ 的上两级即仓库根
_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_HERE))

# ── shields 常规配色（徽章不是股票，红=失败、绿=通过、灰=未知）──────────────
_COLOR = {
    "brightgreen": "#4c1",
    "green": "#97ca00",
    "yellow": "#dfb317",
    "orange": "#fe7d37",
    "red": "#e05d44",
    "lightgrey": "#9f9f9f",
}

_FONT = "Verdana,DejaVu Sans,Geneva,sans-serif"


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------
def _posix(path):
    """键一律走 POSIX `/`：跨平台可比，不许带 os.sep（gitea run 71 教训）。"""
    return path.replace("\\", "/")


def _模块可用(name):
    """不 import 就能判断插件在不在，避免 import 副作用。"""
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _当前提交(root):
    """产物是基于哪个提交生成的。与 tools/ci 其它脚本同口径。"""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


# ---------------------------------------------------------------------------
# 数据来源 1：解析 junit xml
# ---------------------------------------------------------------------------
def 读_junit(path):
    """从 junit xml 读 (passed, failed, error, skipped)。

    pytest 的 junit 根节点可能是 `<testsuites>`（多个 suite）或单个 `<testsuite>`。
    passed 不直接给出，按 `tests - failures - errors - skipped` 推。
    """
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise ValueError("junit xml 解析失败：%s" % e)

    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall("testsuite")
    if not suites:
        raise ValueError("junit xml 里找不到任何 <testsuite> 节点")

    def _int(el, key):
        try:
            return int(float(el.get(key, 0) or 0))
        except (TypeError, ValueError):
            return 0

    tests = fail = err = skip = 0
    for s in suites:
        tests += _int(s, "tests")
        fail += _int(s, "failures")
        err += _int(s, "errors")
        skip += _int(s, "skipped")
    passed = tests - fail - err - skip
    if passed < 0:
        raise ValueError("junit xml 计数自相矛盾：tests=%d 小于 failures+errors+skipped=%d"
                         % (tests, fail + err + skip))
    return passed, fail, err, skip


# ---------------------------------------------------------------------------
# 数据来源 2：解析 pytest 末尾汇总行（交叉校验用）
# ---------------------------------------------------------------------------
_汇总 = re.compile(
    r"(?P<n>\d+)\s+(?P<kind>passed|failed|error|errors|skipped|xfailed|xpassed)")


def 解析末行(text):
    """从 pytest `-q --tb=no` 输出末尾解析计数。

    认多种形态：
      `1234 passed, 5 failed in 12.34s`
      `1 passed, 2 skipped in 0.05s`
      `no tests ran in 0.01s`
    """
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    tail = [ln for ln in text.strip().splitlines() if ln.strip()][-8:]
    for line in reversed(tail):
        if not re.search(r"\b(passed|failed|error|errors|no tests ran)\b", line):
            continue
        hit = False
        for m in _汇总.finditer(line):
            hit = True
            kind = m.group("kind")
            if kind == "errors":
                kind = "error"
            if kind in counts:
                counts[kind] += int(m.group("n"))
        if hit:
            return counts, line.strip()
        # `no tests ran` 这一行，计为全 0 但视为有效结果
        if "no tests ran" in line:
            return counts, line.strip()
    return None, None


# ---------------------------------------------------------------------------
# 数据来源 3：跑 pytest
# ---------------------------------------------------------------------------
def 跑测试(root, scope, timeout, cov_source):
    """真跑一次 pytest，返回 (结果dict, 诊断dict)。

    结果 dict 里 passed/failed/error/skipped 为 int 或 None（跑不出来时）。
    """
    import time

    t0 = time.time()
    workdir = tempfile.mkdtemp(prefix="gen_badge_")
    junit = os.path.join(workdir, "junit.xml")
    cov_json = os.path.join(workdir, "coverage.json")

    try:
        cmd = [sys.executable, "-m", "pytest", *scope,
               "-q", "--tb=no", "--junitxml=%s" % junit,
               "-p", "no:cacheprovider",
               # addopts 里写死了 `-n 4 --dist=loadscope --timeout=60`，
               # 本脚本只想要单进程稳定结果，直接清空再自己给超时。
               "-o", "addopts="]
        if timeout > 0 and _模块可用("pytest_timeout"):
            cmd.append("--timeout=%d" % timeout)

        used_cov = False
        if cov_source and _模块可用("pytest_cov"):
            cmd += ["--cov=%s" % cov_source, "--cov-report=json:%s" % cov_json]
            used_cov = "pytest-cov"
        elif cov_source and _模块可用("coverage"):
            # 退回 coverage 命令行亲自跑一遍（慢，但仍是真实测量）
            cmd = [sys.executable, "-m", "coverage", "run",
                   "--source=%s" % cov_source, "-m", "pytest",
                   *scope, "-q", "--tb=no", "--junitxml=%s" % junit,
                   "-p", "no:cacheprovider", "-o", "addopts="]
            if timeout > 0 and _模块可用("pytest_timeout"):
                cmd.append("--timeout=%d" % timeout)
            used_cov = "coverage-cli"

        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True,
                                  text=True, errors="replace",
                                  timeout=timeout if timeout > 0 else None)
            rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            return {"passed": None, "failed": None, "error": None,
                    "skipped": None}, {"崩溃": "pytest 超时（>%ds）" % timeout}

        # ── 覆盖率 ──
        coverage = None
        coverage_available = False
        if used_cov == "coverage-cli":
            subprocess.run([sys.executable, "-m", "coverage", "json",
                            "-o", cov_json], cwd=root, capture_output=True,
                           text=True, timeout=timeout if timeout > 0 else 300)
        if used_cov and os.path.isfile(cov_json):
            try:
                with open(cov_json, encoding="utf-8") as fh:
                    cov = json.load(fh)
                pct = cov.get("totals", {}).get("percent_covered")
                if pct is not None:
                    coverage = round(float(pct), 1)
                    coverage_available = True
            except (ValueError, OSError, TypeError):
                pass

        # ── 计数：junit 权威，末行汇总交叉校验 ──
        counts = None
        source_note = ""
        if os.path.isfile(junit):
            try:
                p, f, e, s = 读_junit(junit)
                counts = {"passed": p, "failed": f, "error": e, "skipped": s}
                source_note = "junit-xml"
            except ValueError as e:
                counts = None
                source_note = "junit-xml 解析失败：%s" % e
        if counts is None:
            c, line = 解析末行(out)
            if c is None:
                return ({"passed": None, "failed": None, "error": None,
                         "skipped": None},
                        {"崩溃": "两种口径都解析不出计数；pytest rc=%d" % rc,
                         "pytest_rc": rc, "输出尾部": out[-800:]})
            counts = c
            source_note = "末行汇总（%s）" % (line[:60] if line else "?")

        counts["coverage"] = coverage
        counts["coverage_available"] = coverage_available
        诊断 = {
            "pytest_rc": rc,
            "计数口径": source_note,
            "覆盖率口径": used_cov or "不可用（降级 n/a）",
            "duration_seconds": round(time.time() - t0, 2),
            "超时上限": timeout,
        }
        return counts, 诊断
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 数据来源 4：读既有汇总 JSON（--skip-tests / --summary-json）
# ---------------------------------------------------------------------------
def 读汇总(path):
    """从既有汇总 json 读 passed/failed/coverage。

    只认本脚本自己写出的 schema（见 `产出_JSON`），不猜别人的格式——
    猜错就是把别处的数字当成测试结果，同样属于假绿。
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise ValueError("汇总 json 读不动：%s" % e)
    if not isinstance(data, dict) or "passed" not in data:
        raise ValueError("%s 不是本脚本产出的汇总（缺 `passed` 字段）" % path)
    return {
        "passed": data.get("passed"),
        "failed": data.get("failed"),
        "error": data.get("error"),
        "skipped": data.get("skipped"),
        "coverage": data.get("coverage"),
        "coverage_available": bool(data.get("coverage_available")),
    }


# ---------------------------------------------------------------------------
# SVG：纯字符串模板拼接（无网络、无第三方库）
# ---------------------------------------------------------------------------
def _文本宽(s, size=11):
    """按 11px Verdana 估宽：ASCII ≈ 6.6px，CJK/全角 ≈ 11px。

    用 `textLength` 兜底，估宽只影响色块比例，不会让文字溢出。
    """
    w = 0.0
    for ch in s:
        w += 6.6 if ord(ch) < 128 else 11.0
    return w * (size / 11.0)


_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="{aria}">
  <title>{aria}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-color="#000" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
{rects}    <rect width="{w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="{font}" font-size="11">
{texts}  </g>
</svg>
"""


def 渲染_SVG(段):
    """段：[(label, value, color_name)]，拼成一行多段 shields 风格 SVG。"""
    parts_r = []
    parts_t = []
    x = 0.0
    for label, value, color in 段:
        lw = _文本宽(label) + 12
        vw = _文本宽(value) + 12
        parts_r.append('    <rect x="%s" width="%s" height="20" fill="#555"/>'
                       '<rect x="%s" width="%s" height="20" fill="%s"/>'
                       % (_f(x), _f(lw), _f(x + lw), _f(vw), _COLOR[color]))
        parts_t.append(
            '    <text x="%s" y="14" textLength="%s" lengthAdjust="spacingAndGlyphs">%s</text>'
            '<text x="%s" y="14" textLength="%s" lengthAdjust="spacingAndGlyphs">%s</text>'
            % (_f(x + lw / 2), _f(_文本宽(label)), escape(label),
               _f(x + lw + vw / 2), _f(_文本宽(value)), escape(value)))
        x += lw + vw
    aria = " / ".join("%s %s" % (lb, vl) for lb, vl, _ in 段)
    return _SVG.format(w=_f(x), aria=escape(aria), font=_FONT,
                       rects="\n".join(parts_r) + "\n",
                       texts="\n".join(parts_t) + "\n")


def _f(v):
    """浮点数转紧凑字符串，避免 `20.000000000000004` 污染模板。"""
    return ("%.2f" % v).rstrip("0").rstrip(".") or "0"


# ---------------------------------------------------------------------------
# 配色判据
# ---------------------------------------------------------------------------
def 测试色(passed, failed, error):
    """未知=灰；有 failed/error=红；有通过且零失败=亮绿。"""
    if passed is None:
        return "lightgrey"
    if (failed or 0) > 0 or (error or 0) > 0:
        return "red"
    if passed > 0:
        return "brightgreen"
    return "lightgrey"


def 覆盖率色(coverage, available):
    """未知=灰；>=80 亮绿；>=60 黄；<60 橙。

    刻意不用红——覆盖率低是「测得不够」，不是「测挂了」，
    红色留给真正的失败（口径：颜色只表达这一项本身的状态）。
    """
    if not available or coverage is None:
        return "lightgrey"
    if coverage >= 80:
        return "brightgreen"
    if coverage >= 60:
        return "yellow"
    return "orange"


# ---------------------------------------------------------------------------
# 产出
# ---------------------------------------------------------------------------
def 产出_JSON(数据, root, source, scope, 诊断=None):
    return {
        "version": 1,
        "note": ("CI 徽章数据快照，由 tools/ci/gen_badge.py 生成；"
                 "README 顶部徽章引用同目录下的 ci_badge.svg。"
                 "`source` 标明本次数据是真跑还是读已有结果，"
                 "计数为 null 表示本次没拿到数据——宁可转灰也不填假数。"
                 "`scope` 是本次真正跑过的 pytest 目标：读数只对它成立，"
                 "**不是**全仓全量的口径，别拿它冒充全量结果。"),
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "built_from_commit": _当前提交(root),
        "source": source,
        # 实跑时为真实跑过的 pytest 目标；读既有结果时为 []——那两种路径下
        # 「跑到哪」不由本脚本决定，写上去等于暗示自己跑过。
        "scope": scope,
        "passed": 数据.get("passed"),
        "failed": 数据.get("failed"),
        "error": 数据.get("error"),
        "skipped": 数据.get("skipped"),
        "coverage": 数据.get("coverage"),
        "coverage_available": bool(数据.get("coverage_available")),
        "diagnostics": 诊断 or {},
    }


def 写文件(path, text):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gen_badge.py",
        description="生成本地 CI 徽章（docs/ci_badge.json + docs/ci_badge.svg），不联网。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("示例：\n"
                "  python tools/ci/gen_badge.py --skip-tests\n"
                "  python tools/ci/gen_badge.py --scope tests/unit/\n"
                "  python tools/ci/gen_badge.py --strict\n"),
    )
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根目录，默认脚本所在仓库根")
    ap.add_argument("--out-json", default=None, help="JSON 输出路径，默认 <root>/docs/ci_badge.json")
    ap.add_argument("--out-svg", default=None, help="SVG 输出路径，默认 <root>/docs/ci_badge.svg")
    ap.add_argument("--scope", nargs="*", default=None,
                    help="pytest 目标路径，默认 tests/unit/；传多个用空格分隔")
    ap.add_argument("--skip-tests", action="store_true",
                    help="不跑测试，只读既有产物（默认读 --out-json）")
    ap.add_argument("--summary-json", default=None,
                    help="读既有汇总 json（须为本脚本产出）代替实跑")
    ap.add_argument("--junit-xml", default=None, help="读既有 junit xml 代替实跑")
    ap.add_argument("--no-cov", action="store_true", help="不测覆盖率（等价于 coverage_available=false）")
    ap.add_argument("--cov-source", default="src", help="覆盖率统计源，默认 src；空串关闭")
    ap.add_argument("--timeout", type=int, default=900, help="pytest 子进程超时秒数，默认 900；0 表示不限")
    ap.add_argument("--strict", action="store_true", help="存在 failed/error 时返回 1（CI 门禁用）")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("[CI徽章] 红：仓库根不存在：%s" % root)
        return 2

    out_json = args.out_json or os.path.join(root, "docs", "ci_badge.json")
    out_svg = args.out_svg or os.path.join(root, "docs", "ci_badge.svg")
    scope = args.scope if args.scope else ["tests/unit/"]
    # 允许 `--scope tests\unit\` 这类反斜杠写法
    scope = [s.replace("\\", "/") for s in scope]
    cov_source = "" if args.no_cov else args.cov_source

    诊断 = {"scope": scope, "root": root}
    数据 = None

    # ── 读既有结果 ──
    if args.junit_xml:
        try:
            p, f, e, s = 读_junit(args.junit_xml)
        except ValueError as err:
            print("[CI徽章] 红：%s" % err)
            return 2
        数据 = {"passed": p, "failed": f, "error": e, "skipped": s,
                "coverage": None, "coverage_available": False}
        source = "junit-xml:%s" % _posix(args.junit_xml)
    elif args.summary_json:
        try:
            数据 = 读汇总(args.summary_json)
        except ValueError as err:
            print("[CI徽章] 红：%s" % err)
            return 2
        source = "summary-json:%s" % _posix(args.summary_json)
    elif args.skip_tests:
        if os.path.isfile(out_json):
            try:
                数据 = 读汇总(out_json)
                source = "cached:%s" % _posix(os.path.relpath(out_json, root))
                诊断["说明"] = "未跑测试，沿用上一次产物"
            except ValueError as err:
                print("[CI徽章] 红：%s" % err)
                return 2
        else:
            数据 = {"passed": None, "failed": None, "error": None,
                    "skipped": None, "coverage": None, "coverage_available": False}
            source = "skipped"
            诊断["说明"] = "未跑测试且无既有产物，全部读数转灰（不填 0 充数）"
    else:
        # ── 实跑 ──
        数据, 跑诊断 = 跑测试(root, scope, args.timeout, cov_source)
        诊断.update(跑诊断)
        source = "pytest-run"
        if 数据.get("passed") is None:
            print("[CI徽章] 红：实跑没拿到计数：%s" % 跑诊断.get("崩溃", "?"))
            return 1

    # ── 渲染徽章段 ──
    passed = 数据.get("passed")
    failed = 数据.get("failed")
    error = 数据.get("error")
    coverage = 数据.get("coverage")
    cov_ok = bool(数据.get("coverage_available"))

    段 = [
        ("tests", "%s passed" % passed if passed is not None else "n/a",
         测试色(passed, failed, error)),
        ("failed", str(failed) if failed is not None else "n/a",
         "red" if (failed or 0) > 0 or (error or 0) > 0
         else ("brightgreen" if failed is not None else "lightgrey")),
        ("coverage", ("%.1f%%" % coverage) if cov_ok and coverage is not None else "n/a",
         覆盖率色(coverage, cov_ok)),
    ]

    payload = 产出_JSON(数据, root, source,
                        scope if source == "pytest-run" else [], 诊断)
    写文件(out_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    写文件(out_svg, 渲染_SVG(段))

    print("[CI徽章] 来源：%s" % source)
    print("[CI徽章] passed=%s failed=%s error=%s skipped=%s coverage=%s%s"
          % (passed, failed, error, 数据.get("skipped"),
             coverage if cov_ok else "n/a",
             "" if cov_ok else "（coverage_available=false，已优雅降级）"))
    print("[CI徽章] 已写出 %s" % _posix(os.path.relpath(out_json, root)))
    print("[CI徽章] 已写出 %s" % _posix(os.path.relpath(out_svg, root)))

    if args.strict and ((failed or 0) > 0 or (error or 0) > 0):
        print("[CI徽章] 红（--strict）：存在 failed/error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
