# -*- coding: utf-8 -*-
"""stdlib 原生腿就绪度指标（R115 首建，R117 改为多模块编译口径）。

自举率（tools/ci/bootstrap_rate.py）衡量「多少 stdlib 用光明写成」；本脚本盯的是
下一层：**这些带「纯光明实现」魔数的模块里，有多少能被原生腿（LLVM typed 后端）
按真实模块依赖直接编译通过**。编译走 `compile_light_typed` 多模块入口，产物只落临时目录，
模块依赖会递归解析并经 clang 验证、链接。

三桶口径（与 A 线能力矩阵同源）：
  可编      —— compile_light_typed 正常完成；
  明确拒绝  —— 抛 NotImplementedError（原生后端显式拒绝，含缺口类型名，如
               「原生后端暂不支持语句类型「MatchStatement」」）；
  其它错误  —— 其余一切：解析失败、导入失败、读不动、子进程超时/崩溃等。

魔数识别**复用 bootstrap_rate._是纯光明**（首两行含「纯光明实现」，与
stdlib/_light_import_hook.py::_is_pure_light 同口径），不自造。

为什么编译必须走子进程：多模块入口会递归编译依赖并运行 clang，耗时与内存占用
不确定。每模块一个子进程 + 默认 300s 超时，超时计「其它错误」桶，绝不拖死主进程。

用法（在本仓 venv python 下）：
  .venv/Scripts/python.exe tools/ci/llvm_stdlib_readiness.py
      扫全部魔数模块，打印就绪度 + 三桶完整名单，rc=0。
  ... llvm_stdlib_readiness.py --json <path>
      同上，并把机器可读结果写到 <path>（基线文件后缀须是 _baseline.json 才能进仓，
      .gitignore 已有 !tools/ci/*_baseline.json 豁免）。
  ... llvm_stdlib_readiness.py --base tools/ci/llvm_stdlib_readiness_baseline.json
      与基线对比，产出「新增不可编模块」清单；非空则 rc=1（闸门语义：就绪度只许升）。
  ... llvm_stdlib_readiness.py --sample 拼音转换 [--timeout 300]
      单模块调试，打印完整报错（不截断），不写文件。
  ... llvm_stdlib_readiness.py --root <仓库根>
      默认取本文件上两级目录，一般不用动。

退出码：0=正常（--base 时且无新增不可编）；1=有新增不可编或扫描失败；2=用法错误
（--sample 找不到模块 / 模块无魔数）。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import datetime

# 复用 bootstrap_rate 的魔数口径（同目录导入），不自造。
_CI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CI_DIR not in sys.path:
    sys.path.insert(0, _CI_DIR)
from bootstrap_rate import _是纯光明  # noqa: E402

_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_CI_DIR))
_结果前缀 = "RESULT:"
_编译入口 = "compile_light_typed(多模块)"

# 每模块一个子进程：全新解释器防内存累积，进程退出即释放；stdout 只认 RESULT: 行。
_CHILD = r'''
import json, os, re, sys, tempfile

def main():
    root, light_path = sys.argv[1], sys.argv[2]
    for p in (root, os.path.join(root, "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    def emit(payload):
        print("RESULT:" + json.dumps(payload, ensure_ascii=False))
    try:
        with open(light_path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError as e:
        emit({"bucket": "其它错误", "detail": "读不动 .light: %s" % e, "gap": "", "ir_len": 0})
        return 0
    try:
        from llvm.compiler import compile_light_typed
    except Exception as e:
        emit({"bucket": "其它错误", "detail": "导入编译器失败: %r" % (e,), "gap": "", "ir_len": 0})
        return 0
    try:
        with tempfile.TemporaryDirectory(prefix="llvm_readiness_") as tmpdir:
            output_base = os.path.join(tmpdir, os.path.splitext(os.path.basename(light_path))[0])
            compile_light_typed(light_path, output_path=output_base)
            ll_path = output_base + ".ll"
            with open(ll_path, encoding="utf-8", errors="replace") as fh:
                ir_len = len(fh.read())
        emit({"bucket": "可编", "detail": "", "gap": "", "ir_len": ir_len})
    except NotImplementedError as e:
        text = str(e)
        m = re.search(r"「(.+?)」", text)
        if not m:
            # `_reject_unknown_call` 口径：未定义的段落：名（源码行 …）
            m = re.search(r"未定义的段落：([^\s（。，]+)", text)
        emit({"bucket": "明确拒绝", "detail": text.splitlines()[0][:300],
              "gap": m.group(1) if m else "", "ir_len": 0})
    except Exception as e:
        emit({"bucket": "其它错误",
              "detail": ("%s: %s" % (type(e).__name__, str(e).splitlines()[0][:300])),
              "gap": "", "ir_len": 0})
    return 0

sys.exit(main())
'''


def 扫魔数模块(root):
    """扫 stdlib/（递归，与 bootstrap_rate 主扫同口径）下带魔数的 .light，返回 [(模块名, 绝对路径)]。"""
    stdlib_dir = os.path.join(root, "stdlib")
    found = []
    for dirpath, dirnames, filenames in os.walk(stdlib_dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in sorted(filenames):
            if not fn.endswith(".light"):
                continue
            full = os.path.join(dirpath, fn)
            if _是纯光明(full):
                found.append((fn[:-len(".light")], full))
    found.sort()
    return found


def _编一个(root, light_path, timeout):
    """子进程编译一个模块，返回 {bucket, detail, gap, ir_len}。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD, root, light_path],
            capture_output=True, timeout=timeout, env=env, cwd=root,
        )
    except subprocess.TimeoutExpired:
        return {"bucket": "其它错误", "detail": "编译超时(>%gs)，已按口径计入其它错误桶" % timeout,
                "gap": "", "ir_len": 0}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(_结果前缀):
            try:
                return json.loads(line[len(_结果前缀):])
            except ValueError:
                break
    head = (proc.stderr.decode("utf-8", "replace").strip().splitlines() or ["<无 stderr>"])[0]
    return {"bucket": "其它错误",
            "detail": "子进程异常退出 rc=%d: %s" % (proc.returncode, head[:300]),
            "gap": "", "ir_len": 0}


def _short(path, root):
    """绝对路径转仓库相对路径，报告里好读。"""
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path


def 扫全部(root, timeout, verbose=True):
    """扫全部魔数模块，最多 2 路并发编译，按模块名稳定汇总。"""
    modules = 扫魔数模块(root)
    if verbose:
        print("魔数模块总数：%d（口径：stdlib/ 下 .light 首两行含「纯光明实现」，"
              "复用 bootstrap_rate._是纯光明）" % len(modules))
        print("编译入口：%s；最多 2 路并发" % _编译入口)
    buckets = {"可编": [], "明确拒绝": [], "其它错误": []}
    details = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = pool.map(lambda item: _编一个(root, item[1], timeout), modules)
        for i, ((name, path), r) in enumerate(zip(modules, results), 1):
            buckets[r["bucket"]].append(name)
            details.append({"模块": name, "路径": _short(path, root), **r})
            if verbose:
                mark = {"可编": "OK ", "明确拒绝": "拒 ", "其它错误": "ERR"}[r["bucket"]]
                extra = (" 缺口=%s" % r["gap"]) if r.get("gap") else ""
                print("  [%2d/%d] %s %s%s" % (i, len(modules), mark, name, extra))
    total = len(modules)
    ready = len(buckets["可编"])
    return {
        "compile_entry": _编译入口,
        "total": total,
        "ready": ready,
        "rejected": len(buckets["明确拒绝"]),
        "other": len(buckets["其它错误"]),
        "rate": (ready / total) if total else 0.0,
        "buckets": buckets,
        "details": details,
    }


def _打印桶(result):
    b = result["buckets"]
    print("")
    print("就绪度 = 可编 / 总数 = %d / %d = %.2f%%" % (
        result["ready"], result["total"], result["rate"] * 100))
    print("")
    print("【可编】%d 个：" % len(b["可编"]))
    for n in b["可编"]:
        print("  - " + n)
    print("【明确拒绝（含缺口类型名）】%d 个：" % len(b["明确拒绝"]))
    for d in result["details"]:
        if d["bucket"] == "明确拒绝":
            print("  - %s（缺口=%s）" % (d["模块"], d.get("gap") or "未解析到类型名"))
    print("【其它错误】%d 个：" % len(b["其它错误"]))
    for d in result["details"]:
        if d["bucket"] == "其它错误":
            print("  - %s —— %s" % (d["模块"], d["detail"]))


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
    """基线/结果 JSON 落盘。本仓 core.autocrlf=true，文本文件统一 CRLF（bareLF 必须 0）。"""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text + "\r\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="stdlib 原生腿就绪度指标（多模块编译口径）")
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根（默认本脚本上两级）")
    ap.add_argument("--json", metavar="PATH", help="把机器可读结果写到 PATH")
    ap.add_argument("--base", metavar="PATH", help="与基线 JSON 对比，产出新增不可编清单")
    ap.add_argument("--sample", metavar="模块名", help="只编译指定模块（调试用，打印完整报错）")
    ap.add_argument("--timeout", type=float, default=300,
                    help="单模块编译超时秒数（默认 300；多模块路径含依赖递归与 clang，较慢）")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.sample:
        modules = dict(扫魔数模块(root))
        if args.sample not in modules:
            print("找不到魔数模块「%s」（注意：无魔数或不在 stdlib/ 下都算找不到）" % args.sample)
            return 2
        r = _编一个(root, modules[args.sample], args.timeout)
        print("模块：%s\n编译入口：%s\n桶：%s\nIR 长度：%s\n详情：%s" % (
            args.sample, _编译入口, r["bucket"], r.get("ir_len") or "-", r["detail"] or "（无）"))
        return 0

    result = 扫全部(root, args.timeout)
    _打印桶(result)

    if args.json:
        data = {
            "version": 2,
            "note": "stdlib 原生腿就绪度基线（R117 于 2026-10-06 改为多模块编译口径）。"
                    "就绪度 = 可编/魔数模块总数；可编名单只许增不许减——对 --base 跑出"
                    "「新增不可编」即 rc=1。compile_entry 记录测量入口；built_from_commit 是"
                    "生成基线时的 HEAD。",
            "compile_entry": result["compile_entry"],
            "built_from_commit": _built_from_commit(root),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "timeout_per_module_sec": args.timeout,
            "total": result["total"],
            "ready": result["ready"],
            "rejected": result["rejected"],
            "other": result["other"],
            "rate": result["rate"],
            "buckets": result["buckets"],
            "details": result["details"],
        }
        _写_json(args.json, data)
        print("")
        print("已写入：%s" % args.json)

    if args.base:
        with open(args.base, encoding="utf-8") as fh:
            base = json.load(fh)
        base_ready = set(base.get("buckets", {}).get("可编", []))
        now_ready = set(result["buckets"]["可编"])
        新增不可编 = sorted(base_ready - now_ready)
        新增可编 = sorted(now_ready - base_ready)
        print("")
        print("与基线 %s 对比：基线就绪度 %.2f%%（%d/%d）→ 当前 %.2f%%（%d/%d）" % (
            args.base,
            (base.get("rate") or 0) * 100, len(base_ready), base.get("total", len(base_ready)),
            result["rate"] * 100, len(now_ready), result["total"]))
        if 新增不可编:
            print("❌ 新增不可编模块（基线可编、现在不可编）——就绪度回退，闸门红：")
            for n in 新增不可编:
                d = next((x for x in result["details"] if x["模块"] == n), None)
                print("  - %s —— %s" % (n, d["detail"] if d else "（本次扫描未单独列出）"))
            return 1
        print("✅ 无新增不可编模块。" + ("本次新增可编 %d 个：%s" % (len(新增可编), "、".join(新增可编)) if 新增可编 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
