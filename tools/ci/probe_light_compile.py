# -*- coding: utf-8 -*-
"""任意 .light 原生腿编译探针（R122 C1 首建）。

与 `llvm_stdlib_readiness.py` 同一编译入口、同一子进程口径，但**不限定魔数模块**：
它能探测**任意** `.light`——不论首两行有没有「纯光明实现」魔数。这正是 R121
「零风险分母扩军」当时缺的工具：当时要逐个手写临时脚本去试那 7 个无魔数候选
（中止/插件/SSE/伪终端/路径护栏/进程树/字节缓冲），现在固化成一条命令。

三桶口径与就绪度脚本完全一致（不自造）：
  可编      —— compile_light_typed 正常完成；
  明确拒绝  —— 抛 NotImplementedError（原生后端显式拒绝，含缺口类型名/段落名）；
  其它错误  —— 其余一切：解析失败、导入失败(NativeImportError)、读不动、超时/崩溃。

为什么仍走子进程：多模块入口会递归编译依赖并跑 clang，耗时与内存不确定。
每模块一个子进程 + 默认 300s 超时，超时计「其它错误」，绝不拖死主进程。
（子进程 worker 与 llvm_stdlib_readiness._CHILD 逐字一致，保证同入口同口径。）

用法（在本仓 venv python 下）：
  .venv/Scripts/python.exe tools/ci/probe_light_compile.py 字节缓冲
      按模块名探测（任意有无魔数），打印桶 + 缺口 + 首个错误。
  .venv/Scripts/python.exe tools/ci/probe_light_compile.py stdlib/字节缓冲.light
      直接给 .light 路径也行。
  .venv/Scripts/python.exe tools/ci/probe_light_compile.py --nonmagic
      批量探测 stdlib/ 下**所有无魔数** .light（候选池，就绪度分母扩军清单）。
  .venv/Scripts/python.exe tools/ci/probe_light_compile.py --all [--timeout 300]
      批量探测 stdlib/ 下**所有** .light（含已有魔数的，全量体检）。
  ... probe_light_compile.py 模块A 模块B ...
      一次探测多个模块名/路径。

退出码：0=正常跑完探测；2=用法错误（目标找不到 / 模块名命中多个文件）。
本工具是**诊断探针**，不做门禁判定——翻魔数的可编前置校验由 `flip_magic.py`
直接 import 这里的 `probe_one()` 复用，保证两边口径永不分叉。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys

# 复用 bootstrap_rate 的魔数口径（同目录导入），不自造。
_CI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CI_DIR not in sys.path:
    sys.path.insert(0, _CI_DIR)
from bootstrap_rate import _是纯光明  # noqa: E402

_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_CI_DIR))
_结果前缀 = "RESULT:"
_编译入口 = "compile_light_typed(多模块)"

# 每模块一个子进程：全新解释器防内存累积，进程退出即释放；stdout 只认 RESULT: 行。
# 与 llvm_stdlib_readiness._CHILD 逐字一致（同入口同口径）。
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
        with tempfile.TemporaryDirectory(prefix="probe_compile_") as tmpdir:
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


def 遍历_light(root):
    """扫 stdlib/（递归）下全部 .light，返回 [(模块名, 绝对路径)]。与魔数无关。"""
    stdlib_dir = os.path.join(root, "stdlib")
    found = []
    for dirpath, dirnames, filenames in os.walk(stdlib_dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in sorted(filenames):
            if fn.endswith(".light"):
                found.append((fn[:-len(".light")], os.path.join(dirpath, fn)))
    found.sort()
    return found


def probe_one(root, light_path, timeout):
    """【供 flip_magic 复用】子进程编译一个 .light，返回 {bucket, detail, gap, ir_len}。

    这是翻魔数的「前置可编校验」权威来源：翻不可编的模块会分母涨分子不涨、
    反而拉低就绪度（单调性约束），所以 flip_magic 在动字节前必须先过这一关。
    """
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
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path


def _resolve_targets(root, names, scan_all, scan_nonmagic):
    """把命令行目标解析成 [(模块名, 绝对路径)]。

    - names 里既可是模块名（按 basename 在 stdlib/ 下找），也可是直接 .light 路径；
    - scan_nonmagic=True：批量取 stdlib/ 下所有**无魔数** .light；
    - scan_all=True：批量取 stdlib/ 下所有 .light。
    """
    all_lights = 遍历_light(root)
    by_basename = {}
    for 名, 路径 in all_lights:
        by_basename.setdefault(名, []).append(路径)

    if scan_all:
        return list(all_lights)
    if scan_nonmagic:
        return [(名, 路径) for 名, 路径 in all_lights if not _是纯光明(路径)]

    out = []
    for t in names:
        cand = None
        if t.endswith(".light") and os.path.isfile(t):
            cand = [os.path.abspath(t)]
        else:
            base = os.path.basename(t)[:-len(".light")] if t.endswith(".light") else t
            if base in by_basename:
                cand = by_basename[base]
        if not cand:
            print("找不到 .light 目标：%s" % t)
            return None
        if len(cand) > 1:
            print("模块名「%s」命中多个 .light，请改用具体路径：" % t)
            for p in cand:
                print("  - %s" % _short(p, root))
            return None
        路径 = cand[0]
        out.append((os.path.basename(路径)[:-len(".light")], 路径))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="任意 .light 原生腿编译探针（不限魔数）")
    ap.add_argument("targets", nargs="*", metavar="模块名|.light路径",
                    help="要探测的模块名或 .light 路径（可多个）")
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根（默认本脚本上两级）")
    ap.add_argument("--all", action="store_true", help="探测 stdlib/ 下所有 .light")
    ap.add_argument("--nonmagic", action="store_true",
                    help="探测 stdlib/ 下所有无魔数 .light（分母扩军候选池）")
    ap.add_argument("--timeout", type=float, default=300,
                    help="单模块编译超时秒数（默认 300）")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    if not args.targets and not args.all and not args.nonmagic:
        ap.error("必须给出至少一个目标（模块名/.light路径），或 --all / --nonmagic")

    modules = _resolve_targets(root, args.targets, args.all, args.nonmagic)
    if modules is None:
        return 2

    print("探测模块数：%d（编译入口：%s；最多 2 路并发）" % (len(modules), _编译入口))
    buckets = {"可编": [], "明确拒绝": [], "其它错误": []}
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for (名, 路径), r in zip(modules, pool.map(lambda it: probe_one(root, it[1], args.timeout), modules)):
            buckets[r["bucket"]].append(名)
            results.append({"模块": 名, "路径": _short(路径, root), **r})
            mark = {"可编": "OK ", "明确拒绝": "拒 ", "其它错误": "ERR"}[r["bucket"]]
            extra = (" 缺口=%s" % r["gap"]) if r.get("gap") else ""
            detail = ("  -- %s" % r["detail"]) if r.get("detail") else ""
            print("  %s %s%s%s" % (mark, 名, extra, detail))

    print("")
    print("汇总：可编 %d / 明确拒绝 %d / 其它错误 %d" % (
        len(buckets["可编"]), len(buckets["明确拒绝"]), len(buckets["其它错误"])))
    if buckets["可编"]:
        print("【可编】%s" % "、".join(buckets["可编"]))
    if buckets["明确拒绝"]:
        print("【明确拒绝】")
        for d in results:
            if d["bucket"] == "明确拒绝":
                print("  - %s（缺口=%s）" % (d["模块"], d.get("gap") or "未解析到类型名"))
    if buckets["其它错误"]:
        print("【其它错误】")
        for d in results:
            if d["bucket"] == "其它错误":
                print("  - %s —— %s" % (d["模块"], d["detail"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
