# -*- coding: utf-8 -*-
"""stdlib 原生腿「可跑」就绪度指标（R131-A 首建）。

`tools/ci/llvm_stdlib_readiness.py` 只回答「能不能编出 IR」——但 **可编 ≠ 可跑 ≠
跑得对**。本脚本补第二把尺子：**对每个「可编」模块，生成一个最小导入驱动，真编
成 exe 并真执行**，判据是「进程 rc==0 且 stdout 含 SMOKE_OK」。

为什么需要它（R131 实测动机）：
  `light run --backend native` 跑一个中等复杂度样例（`_r131_scratch/probe_real.light`）
  能通（JSON round-trip / 文件系统写读删 / 类 / 异常 / 遍历全过），但**跑通的同时
  抓到两个真缺陷**（L-186 `列表排序` 不写回、L-187 异常栈追踪串台）。只盯「可编率」
  永远发现不了这类问题。

驱动形态（每个模块自动生成，落 `_r131_scratch/smoke/`，不写源码树其他位置）：

    从 <模块> 导入 <导出名1>, <导出名2>, ...。
    段落 主():
      输出("SMOKE_OK")
      返回 0

  导出名从 `stdlib/<模块>.light` 的 `^导出` 行解析（按空白切分、去结尾「。」，
  最多取前 `_MAX_IMPORT_NAMES` 个，避免驱动编译爆炸）。**只导入不调用**：本轮验的
  是「模块能被原生腿加载 + 顶层初始化 + 链接成 exe 后跑完不崩」，不是语义正确性
  （语义正确性靠双腿对拍测试，见「对拍覆盖率」）。

四桶口径：
  可跑   —— 编译 + 执行成功，rc==0 且 stdout 含 SMOKE_OK；
  跑崩   —— 编译成功但执行失败（rc≠0 / 崩溃 / 超时 / 无 SMOKE_OK）；
  编不过 —— compile_light_typed 失败（含明确拒绝 NotImplementedError）；
  无导出 —— 解析不到 `^导出` 名（本轮不判成败，单独列，避免把「解析不到导出」
            误记成模块缺陷）。

第二个数字「对拍覆盖率」：
  扫 `tests/` 下已有的原生腿对拍测试，统计「可编模块中有多少个被至少一条双腿对拍
  用例覆盖」。这是**只读普查**（用文件名 + 文件内容的启发式匹配），不新增测试、
  不判用例质量。目的是回答「71 个可编模块里，有多少个的语义真被双腿校验过」。

为什么编译必须走子进程（与 llvm_stdlib_readiness.py 同款理由）：
  多模块入口会递归编译依赖并运行 clang + 链接，耗时与内存占用不确定。每模块一个
  子进程 + 默认 300s 超时，超时计「跑崩」桶，绝不拖死主进程。

用法（在本仓 venv python 下）：
  .venv/Scripts/python.exe tools/ci/native_run_readiness.py
      扫全部「可编」模块，打印可跑/跑崩/编不过/无导出 四桶完整名单 + 对拍覆盖率，rc=0。
  ... native_run_readiness.py --json <path>
      同上，并把机器可读结果写到 <path>（基线文件后缀须是 `_baseline.json` 才能进仓，
      .gitignore 已有 `!tools/ci/*_baseline.json` 豁免）。
  ... native_run_readiness.py --base tools/ci/native_run_readiness_baseline.json
      与基线对比，产出「由跑转崩」清单；非空则 rc=1（闸门语义：可跑名单只许增不许减）。
  ... native_run_readiness.py --sample <模块名> [--timeout 300]
      单模块调试，打印完整报错（不截断），不写文件。
  ... native_run_readiness.py --root <仓库根>
      默认取本文件上两级目录，一般不用动。

⚠️ 跑批耗时：每个模块（编译 + clang 链接 + 执行）约 40–90s，71 个模块 2 路并发
约 25–50 分钟。**本脚本不进 PR 级 CI**（太慢），定位为轮次门禁 / nightly。

退出码：0=正常（--base 时且无「由跑转崩」）；1=有「由跑转崩」；2=用法错误
（--sample 找不到模块 / 该模块不在可编桶）。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

# 复用 bootstrap_rate / llvm_stdlib_readiness 的既有口径，不自造。
_CI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CI_DIR not in sys.path:
    sys.path.insert(0, _CI_DIR)
from bootstrap_rate import _是纯光明  # noqa: E402

_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_CI_DIR))
_结果前缀 = "RESULT:"
_编译入口 = "compile_light_typed(驱动模块)"
_哨兵 = "SMOKE_OK"

# 单模块最多导入多少个导出名：够触发模块加载即可，多了会让驱动编译时间失控。
_MAX_IMPORT_NAMES = 8

_准备就绪基线 = os.path.join(_CI_DIR, "llvm_stdlib_readiness_baseline.json")

# 驱动落点：仓库内的 scratch 目录（不是 tempfile）——原生腿的模块解析以源文件位置
# 为锚之一，放系统 Temp 有可能解析不到 stdlib，故固定在仓库内，跑完由调用方清理。
_SMOKE_DIRNAME = "_r131_scratch/smoke"

_导出行 = re.compile(r"^导出\s+(.+?)[\s。]*$")


# ---------------------------------------------------------------- 子进程编译+执行

_CHILD = r'''
import json, os, re, sys, subprocess, tempfile

def main():
    root, driver_path, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
    for p in (root, os.path.join(root, "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    def emit(payload):
        print("RESULT:" + json.dumps(payload, ensure_ascii=False))

    try:
        from llvm.compiler import compile_light_typed
    except Exception as e:
        emit({"bucket": "编不过", "detail": "导入编译器失败: %r" % (e,), "gap": "", "stdout": ""})
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="native_run_") as tmpdir:
            out_base = os.path.join(tmpdir, "driver")
            exe = compile_light_typed(driver_path, out_base)
            if not exe or not os.path.exists(exe):
                emit({"bucket": "编不过", "detail": "编译未产出可执行文件: %s" % (exe,),
                      "gap": "", "stdout": ""})
                return 0
            try:
                proc = subprocess.run([exe], capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                emit({"bucket": "跑崩", "detail": "执行超时(>%gs)" % timeout, "gap": "", "stdout": ""})
                return 0
            out = proc.stdout.decode("utf-8", "replace")
            err = proc.stderr.decode("utf-8", "replace")
            if proc.returncode != 0:
                emit({"bucket": "跑崩",
                      "detail": "rc=%d | stderr: %s" % (proc.returncode, err.strip()[:300]),
                      "gap": "", "stdout": out[:500]})
                return 0
            if "SMOKE_OK" not in out:
                emit({"bucket": "跑崩",
                      "detail": "rc=0 但 stdout 无 SMOKE_OK 哨兵（可能主段未被调用）",
                      "gap": "", "stdout": out[:500]})
                return 0
            emit({"bucket": "可跑", "detail": "", "gap": "", "stdout": out[:500]})
    except NotImplementedError as e:
        text = str(e)
        m = re.search(r"「(.+?)」", text)
        if not m:
            m = re.search(r"未定义的段落：([^\s（。，]+)", text)
        emit({"bucket": "编不过", "detail": text.splitlines()[0][:300],
              "gap": m.group(1) if m else "", "stdout": ""})
    except Exception as e:
        emit({"bucket": "编不过",
              "detail": ("%s: %s" % (type(e).__name__, str(e).splitlines()[0][:300])),
              "gap": "", "stdout": ""})
    return 0

sys.exit(main())
'''


# ---------------------------------------------------------------- 模块与导出名

def 取可编模块(root, 基线路径=_准备就绪基线):
    """返回 llvm_stdlib_readiness 基线「可编」桶里的模块名（排序后）。

    基线缺失时退化为「扫全部魔数模块」（与 llvm_stdlib_readiness 主扫同口径），
    并在 stderr 提示——此时「编不过」桶会包含那些本来就不可编的模块，属预期。
    """
    if os.path.exists(基线路径):
        with open(基线路径, encoding="utf-8") as fh:
            base = json.load(fh)
        names = list(base.get("buckets", {}).get("可编", []))
        if names:
            return sorted(names)
        print("警告：基线的「可编」桶为空，退化为扫全部魔数模块", file=sys.stderr)
    mods = 扫魔数模块(root)
    return [n for n, _ in mods]


def 扫魔数模块(root):
    """扫 stdlib/（递归）下带魔数的 .light，返回 [(模块名, 绝对路径)]。"""
    stdlib_dir = os.path.join(root, "stdlib")
    found = []
    for dirpath, dirnames, filenames in os.walk(stdlib_dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in sorted(filenames):
            if not fn.endswith(".light"):
                continue
            full = os.path.join(dirpath, fn)
            if _是纯光明(full):
                found.append((fn[: -len(".light")], full))
    found.sort()
    return found


def 解析导出名(light_path, limit=_MAX_IMPORT_NAMES):
    """从 `^导出` 行解析导出名（可跨多行累加），最多 limit 个。"""
    names = []
    try:
        with open(light_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = _导出行.match(line.strip())
                if not m:
                    continue
                for tok in m.group(1).split():
                    tok = tok.strip("。，、;；")
                    if tok and tok not in names:
                        names.append(tok)
                if len(names) >= limit:
                    break
    except OSError:
        return []
    return names[:limit]


def _模块路径表(root):
    return {n: p for n, p in 扫魔数模块(root)}


# ---------------------------------------------------------------- 驱动生成

def 生成驱动(root, 模块, 导出名, 目录):
    """写一个最小导入驱动 .light，返回路径。"""
    os.makedirs(目录, exist_ok=True)
    # 模块名可能含中文/特殊字符，驱动文件名用索引安全化由调用方保证；这里直接用模块名。
    path = os.path.join(目录, "驱动_%s.light" % 模块)
    body = "从 %s 导入 %s。\n段落 主():\n  输出(\"%s\")\n  返回 0\n" % (
        模块, " ".join(导出名), _哨兵)
    # core.autocrlf=true：文本文件统一 CRLF（bareLF 必须 0）。
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(body)
    return path


# ---------------------------------------------------------------- 对拍覆盖率普查

_对拍文件特征 = ("原生腿", "对拍", "native", "llvm")


def 普查对拍覆盖(root, 模块们):
    """统计可编模块中有多少被 tests/ 下的原生腿对拍测试提及。

    启发式（诚实声明）：先看测试文件名是否含 原生腿/对拍/native/llvm 特征，再看
    该文件内容是否出现模块名。**只证明「被提及」，不证明用例质量或断言强度**——
    真判据是人工审用例，本脚本只给普查数字。
    返回 (已覆盖模块集合, 命中文件数, 扫描文件数)。
    """
    tests_dir = os.path.join(root, "tests")
    命中文件 = []
    扫过 = 0
    if not os.path.isdir(tests_dir):
        return set(), 0, 0
    for dirpath, dirnames, filenames in os.walk(tests_dir):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            扫过 += 1
            low = fn.lower()
            if not any(k in low for k in _对拍文件特征):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            命中文件.append((os.path.relpath(full, root).replace("\\", "/"), text))
    已覆盖 = set()
    for 模块 in 模块们:
        for _path, text in 命中文件:
            if 模块 in text:
                已覆盖.add(模块)
                break
    return 已覆盖, len(命中文件), 扫过


# ---------------------------------------------------------------- 主扫

def _跑一个(root, 驱动路径, timeout):
    """子进程编译+执行一个驱动，返回 {bucket, detail, gap, stdout}。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD, root, 驱动路径, str(timeout)],
            capture_output=True, timeout=timeout + 120, env=env, cwd=root,
        )
    except subprocess.TimeoutExpired:
        return {"bucket": "跑崩", "detail": "子进程超时(>%gs)" % (timeout + 120),
                "gap": "", "stdout": ""}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(_结果前缀):
            try:
                return json.loads(line[len(_结果前缀):])
            except ValueError:
                break
    head = (proc.stderr.decode("utf-8", "replace").strip().splitlines() or ["<无 stderr>"])[0]
    return {"bucket": "编不过",
            "detail": "子进程异常退出 rc=%d: %s" % (proc.returncode, head[:300]),
            "gap": "", "stdout": ""}


def 扫全部(root, timeout, workers=2, verbose=True):
    modules = 取可编模块(root)
    路径表 = _模块路径表(root)
    smoke_dir = os.path.join(root, _SMOKE_DIRNAME)
    if verbose:
        print("可编模块总数：%d（来源：llvm_stdlib_readiness 基线「可编」桶）" % len(modules))
        print("编译入口：%s；并发 %d；单模块超时 %gs" % (_编译入口, workers, timeout))
        print("判据：rc==0 且 stdout 含哨兵「%s」" % _哨兵)
    buckets = {"可跑": [], "跑崩": [], "编不过": [], "无导出": []}
    details = []
    待跑 = []
    for name in modules:
        path = 路径表.get(name)
        names = 解析导出名(path) if path else []
        if not names:
            buckets["无导出"].append(name)
            details.append({"模块": name, "路径": (os.path.relpath(path, root).replace("\\", "/") if path else ""),
                            "bucket": "无导出", "detail": "解析不到导出名", "gap": "", "stdout": ""})
            if verbose:
                print("  [跳过] %s —— 解析不到导出名" % name)
            continue
        drv = 生成驱动(root, name, names, smoke_dir)
        待跑.append((name, path, drv, names))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(lambda item: _跑一个(root, item[2], timeout), 待跑)
        for i, ((name, path, drv, names), r) in enumerate(zip(待跑, results), 1):
            buckets[r["bucket"]].append(name)
            details.append({"模块": name,
                            "路径": os.path.relpath(path, root).replace("\\", "/"),
                            "导入名": names, **r})
            if verbose:
                mark = {"可跑": "RUN", "跑崩": "CRASH", "编不过": "NOCMP", "无导出": "NOEXP"}[r["bucket"]]
                extra = ("  —— %s" % r["detail"][:160]) if r.get("detail") else ""
                print("  [%2d/%d] %s %s%s" % (i, len(待跑), mark, name, extra))

    已覆盖, 命中文件数, 扫过文件数 = 普查对拍覆盖(root, modules)
    total = len(modules)
    return {
        "compile_entry": _编译入口,
        "sentinel": _哨兵,
        "total": total,
        "runnable": len(buckets["可跑"]),
        "crashed": len(buckets["跑崩"]),
        "uncompilable": len(buckets["编不过"]),
        "no_export": len(buckets["无导出"]),
        # 可跑率分母 = 有导出名的模块（无导出不参与成败判定）
        "judged": len(待跑),
        "run_rate": (len(buckets["可跑"]) / len(待跑)) if 待跑 else 0.0,
        "pair_covered": len(已覆盖),
        "pair_rate": (len(已覆盖) / total) if total else 0.0,
        "pair_files_hit": 命中文件数,
        "pair_files_scanned": 扫过文件数,
        "pair_covered_modules": sorted(已覆盖),
        "buckets": buckets,
        "details": details,
        "smoke_dir": os.path.relpath(smoke_dir, root).replace("\\", "/"),
    }


def _打印桶(result):
    b = result["buckets"]
    print("")
    print("可跑率 = 可跑 / 参判 = %d / %d = %.2f%%" % (
        result["runnable"], result["judged"], result["run_rate"] * 100))
    print("对拍覆盖率 = 被对拍用例提及的模块 / 可编总数 = %d / %d = %.2f%%"
          "（普查口径：扫 tests/ 下 %d 个文件，命中 %d 个含原生腿/对拍特征）" % (
              result["pair_covered"], result["total"], result["pair_rate"] * 100,
              result["pair_files_scanned"], result["pair_files_hit"]))
    print("")
    print("【可跑】%d 个：" % len(b["可跑"]))
    for n in b["可跑"]:
        print("  - " + n)
    print("【跑崩】%d 个（★ 这些是真信号：能编但跑不起来）：" % len(b["跑崩"]))
    for d in result["details"]:
        if d["bucket"] == "跑崩":
            print("  - %s —— %s" % (d["模块"], d["detail"]))
    print("【编不过】%d 个：" % len(b["编不过"]))
    for d in result["details"]:
        if d["bucket"] == "编不过":
            print("  - %s —— %s" % (d["模块"], d["detail"]))
    print("【无导出】%d 个（不参判）：" % len(b["无导出"]))
    for n in b["无导出"]:
        print("  - " + n)


def _built_from_commit(root):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, timeout=30, cwd=root)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _写_json(path, data):
    """基线 JSON 落盘。本仓 core.autocrlf=true，文本文件统一 CRLF（bareLF 必须 0）。"""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text + "\r\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="stdlib 原生腿「可跑」就绪度指标（驱动执行口径）")
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根（默认本脚本上两级）")
    ap.add_argument("--json", metavar="PATH", help="把机器可读结果写到 PATH")
    ap.add_argument("--base", metavar="PATH", help="与基线对比，产出「由跑转崩」清单")
    ap.add_argument("--sample", metavar="模块名", help="只跑指定模块（调试用，打印完整报错）")
    ap.add_argument("--timeout", type=float, default=300,
                    help="单模块执行超时秒数（默认 300；编译另含 clang 链，子进程墙钟再 +120）")
    ap.add_argument("--workers", type=int, default=2, help="并发数（默认 2；跑批重，勿调高）")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.sample:
        路径表 = _模块路径表(root)
        if args.sample not in 路径表:
            print("找不到魔数模块「%s」（无魔数或不在 stdlib/ 下都算找不到）" % args.sample)
            return 2
        names = 解析导出名(路径表[args.sample])
        if not names:
            print("模块「%s」解析不到导出名，无法生成驱动" % args.sample)
            return 2
        smoke_dir = os.path.join(root, _SMOKE_DIRNAME)
        drv = 生成驱动(root, args.sample, names, smoke_dir)
        r = _跑一个(root, drv, args.timeout)
        print("模块：%s\n驱动：%s\n导入名：%s\n编译入口：%s\n桶：%s\n详情：%s" % (
            args.sample, os.path.relpath(drv, root).replace("\\", "/"), " ".join(names),
            _编译入口, r["bucket"], r["detail"] or "（无）"))
        if r.get("stdout"):
            print("stdout：%r" % r["stdout"])
        return 0

    result = 扫全部(root, args.timeout, args.workers)
    _打印桶(result)

    if args.json:
        data = {
            "version": 1,
            "note": "stdlib 原生腿「可跑」就绪度基线（R131-A 首建）。可编≠可跑：本脚本对"
                    "llvm_stdlib_readiness 基线的每个「可编」模块生成最小导入驱动 → 真编译"
                    "成 exe → 真执行，判据 rc==0 且 stdout 含哨兵 SMOKE_OK。可跑名单只许增"
                    "不许减——对 --base 跑出「由跑转崩」即 rc=1。pair_rate 是对拍覆盖率普查"
                    "（启发式：只证明被 tests/ 下原生腿对拍用例提及，不证明用例质量）。"
                    "跑批约 25-50 分钟，**不进 PR 级 CI**，定位轮次门禁/nightly。",
            "compile_entry": result["compile_entry"],
            "sentinel": result["sentinel"],
            "built_from_commit": _built_from_commit(root),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "timeout_per_module_sec": args.timeout,
            "total": result["total"],
            "judged": result["judged"],
            "runnable": result["runnable"],
            "crashed": result["crashed"],
            "uncompilable": result["uncompilable"],
            "no_export": result["no_export"],
            "run_rate": result["run_rate"],
            "pair_covered": result["pair_covered"],
            "pair_rate": result["pair_rate"],
            "pair_files_hit": result["pair_files_hit"],
            "pair_files_scanned": result["pair_files_scanned"],
            "pair_covered_modules": result["pair_covered_modules"],
            "buckets": result["buckets"],
            "details": result["details"],
            "smoke_dir": result["smoke_dir"],
        }
        _写_json(args.json, data)
        print("")
        print("已写入：%s" % args.json)

    if args.base:
        with open(args.base, encoding="utf-8") as fh:
            base = json.load(fh)
        base_runnable = set(base.get("buckets", {}).get("可跑", []))
        now_runnable = set(result["buckets"]["可跑"])
        由跑转崩 = sorted(base_runnable - now_runnable)
        新增可跑 = sorted(now_runnable - base_runnable)
        print("")
        print("与基线 %s 对比：基线可跑率 %.2f%%（%d/%d）→ 当前 %.2f%%（%d/%d）" % (
            args.base,
            (base.get("run_rate") or 0) * 100, len(base_runnable), base.get("judged", len(base_runnable)),
            result["run_rate"] * 100, len(now_runnable), result["judged"]))
        if 由跑转崩:
            print("❌ 由跑转崩的模块（基线可跑、现在跑不起来）——闸门红：")
            for n in 由跑转崩:
                d = next((x for x in result["details"] if x["模块"] == n), None)
                print("  - %s —— %s" % (n, d["detail"] if d else "（本次扫描未单独列出）"))
            return 1
        print("✅ 无「由跑转崩」模块。" + ("本次新增可跑 %d 个：%s" % (len(新增可跑), "、".join(新增可跑)) if 新增可跑 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
