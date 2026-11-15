#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniLog 黑盒测试 runner —— 语言无关，唯一依赖是工作目录下的 ./minilog。

用法：
  python3 run_suite.py --target ./minilog --stage v1
  python3 run_suite.py --target ./minilog --stage v2          # 含 v1 回归
  python3 run_suite.py --target ./minilog --suite hidden --stage v2
  python3 run_suite.py --target ./minilog --suite all --stage v2 --json report.json

约定：
- 每个用例在独立的临时目录中运行，避免上一用例残留文件影响结果。
- 用例的 files 字段把 fixture 复制到临时目录的指定文件名。
- output_file=True 时自动追加 --output=_out.txt 到参数末尾，并校验该文件内容。
- 超时默认 30s（用例体量最大 5000 行，正常实现远低于此）。
- 比对 stdout/stderr/输出文件为**逐字节**比对（bytes），不做 strip/normalize。
- 每个用例附加采集 wall-clock 耗时，供成本分析使用。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
CASES_DIR = os.path.join(HERE, "cases")


def as_bytes(v):
    return v.encode("utf-8") if isinstance(v, str) else (v or b"")


def fixture_bytes(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def load_cases(suite):
    out = []
    for s in (["visible", "hidden"] if suite == "all" else [suite]):
        with open(os.path.join(CASES_DIR, s + ".json"), "r", encoding="utf-8") as f:
            out.extend(json.load(f)["cases"])
    return out


def expected_bytes(c, key, file_key):
    if file_key in c:
        return fixture_bytes(c[file_key])
    return as_bytes(c.get(key, ""))


def run_one(target, c, timeout):
    """返回 (passed, detail_dict)。"""
    tmp = tempfile.mkdtemp(prefix="minilog-")
    detail = {"id": c["id"], "stage": c["stage"], "args": c["args"],
              "note": c.get("note", ""), "failures": []}
    try:
        # 1) 铺 files
        for dest, src in c.get("files", {}).items():
            with open(os.path.join(tmp, dest), "wb") as f:
                f.write(fixture_bytes(src))

        # 2) stdin
        if "stdin_file" in c:
            stdin_data = fixture_bytes(c["stdin_file"])
        else:
            stdin_data = as_bytes(c.get("stdin", ""))

        # 3) args（output_file 模式追加 --output）
        args = list(c["args"])
        out_path = None
        if c.get("output_file"):
            out_path = os.path.join(tmp, "_out.txt")
            if c.get("preexisting_output") is not None:
                with open(out_path, "wb") as f:
                    f.write(as_bytes(c["preexisting_output"]))
            args.append("--output=_out.txt")
        elif c.get("preexisting_output") is not None:
            pass

        # H-19 需要父目录不存在
        if "sub/no.txt" in " ".join(args):
            # 保持 sub 目录不创建
            pass

        # 4) 执行
        t0 = time.perf_counter()
        try:
            p = subprocess.run([target] + args, input=stdin_data,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=tmp, timeout=timeout)
        except subprocess.TimeoutExpired:
            detail["failures"].append("TIMEOUT after %.1fs" % timeout)
            detail["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return False, detail
        except OSError as e:
            detail["failures"].append("EXEC ERROR: %s" % e)
            detail["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return False, detail
        detail["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        detail["actual_exit"] = p.returncode

        # 5) 比对
        def check(label, got, want):
            if got != want:
                detail["failures"].append(
                    "%s mismatch: got %d bytes, want %d bytes" %
                    (label, len(got), len(want)))
                detail.setdefault("diff", {})[label] = {
                    "got_head": got[:300].decode("utf-8", "replace"),
                    "want_head": want[:300].decode("utf-8", "replace"),
                }

        if p.returncode != c["expected_exit"]:
            detail["failures"].append(
                "exit: got %d, want %d" % (p.returncode, c["expected_exit"]))

        check("stdout", p.stdout, expected_bytes(c, "expected_stdout",
                                                 "expected_stdout_file"))
        if c.get("expected_stderr_nonempty"):
            if len(p.stderr) == 0:
                detail["failures"].append("stderr: expected non-empty, got 0 bytes")
        else:
            check("stderr", p.stderr, as_bytes(c.get("expected_stderr", "")))

        if out_path is not None:
            if os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    check("output_file", f.read(),
                          as_bytes(c.get("expected_output_file", "")))
            else:
                detail["failures"].append("output_file: not created")

        detail["passed"] = len(detail["failures"]) == 0
        return detail["passed"], detail
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="./minilog", help="minilog 可执行文件路径")
    ap.add_argument("--suite", choices=["visible", "hidden", "all"],
                    default="visible")
    ap.add_argument("--stage", choices=["v1", "v2"], default="v1",
                    help="v2 会包含全部 v1 用例作为回归")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--json", dest="json_out", default=None,
                    help="把逐用例明细写成 JSON（供 05-analysis 使用）")
    a = ap.parse_args()

    target = os.path.abspath(a.target)
    if not os.path.exists(target):
        print("FATAL: target not found: %s" % target, file=sys.stderr)
        return 2
    if not os.access(target, os.X_OK):
        print("FATAL: target not executable: %s" % target, file=sys.stderr)
        return 2

    cases = [c for c in load_cases(a.suite)
             if a.stage == "v2" or c["stage"] == "v1"]
    results = []
    for c in cases:
        ok, d = run_one(target, c, a.timeout)
        results.append(d)
        flag = "PASS" if ok else "FAIL"
        print("[%s] %-7s %-4s %6.1fms  %s" %
              (flag, d["id"], d["stage"], d["elapsed_ms"], d["note"]))
        for f in d["failures"]:
            print("         └─ %s" % f)

    passed = sum(1 for d in results if d["passed"])
    total = len(results)
    print("\n== %s / stage=%s : %d/%d passed (%.1f%%) ==" %
          (a.suite, a.stage, passed, total, 100.0 * passed / max(total, 1)))

    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"target": target, "suite": a.suite, "stage": a.stage,
                       "passed": passed, "total": total,
                       "results": results}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("report -> %s" % a.json_out)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
