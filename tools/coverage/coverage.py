#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 (LightLang) 代码覆盖率工具 — 基础原型（单文件行覆盖率）

设计要点
--------
光明源码经编译器翻译为 Python 时，会在每条语句前插入 `# LIGHT_SRC:<n>`
标记，其中 <n> 是原始 .light 源文件的行号。本工具利用该标记作为
「源→目标」映射，做到对光明源码行级的覆盖率统计（而非仅 Python 层）。

工作流程
--------
1. `light compile <file>.light -o <tmp>.py` 生成带标记的 Python。
2. 扫描生成文件，建立  Python行号 → 光明行号  的映射表。
3. 在 tracer 下执行生成的 Python，记录被执行到的光明行号。
4. 解析光明源中的 `段落`(函数) 边界，按函数分组输出覆盖率。

命令
----
    python coverage.py run   <file>.light [--out <cov.json>]
    python coverage.py report [<cov.json>] [--show-missing]

注意（原型限制）
----------------
- 仅统计「行覆盖率」，不含分支覆盖率。
- 被测程序若含交互输入(输入(...))会阻塞；请传入非交互输入或改造后测试。
- 依赖现有 `cli/light.py compile` 与编译器，未改动核心编译器/stdlib。
- 接入 `light coverage` 子命令只需在 `cli/light.py` 增加少量子parser（见 README.md）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent.parent  # light-merge 仓库根（tools/coverage -> tools -> root）
CLI = PROJECT_DIR / "cli" / "light.py"

LIGHT_SRC_RE = re.compile(r"#\s*LIGHT_SRC:(\d+)")
FUNC_DEF_RE = re.compile(r"^\s*段落\s*([A-Za-z0-9_\u4e00-\u9fff]+)\s*接收")


def compile_to_py(light_file: Path, py_out: Path) -> None:
    """调用现有编译器把 .light 翻译为带 LIGHT_SRC 标记的 Python。"""
    if not CLI.exists():
        raise RuntimeError(f"未找到编译器入口: {CLI}")
    cmd = [sys.executable, str(CLI), "compile", str(light_file), "-o", str(py_out)]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    if res.returncode != 0:
        raise RuntimeError("编译失败:\n" + (res.stderr or res.stdout))


def build_src_map(py_path: Path):
    """建立 Python 行号 -> 光明行号 映射。

    注意：`# LIGHT_SRC:<n>` 标记写在语句**前一行**（注释行），而 tracer 在
    实际代码行触发，因此需要把「每个代码行」映射到「其之前最近一个标记」的光明行号。
    """
    light_of_line = {}
    cur = None
    with open(py_path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            m = LIGHT_SRC_RE.search(line)
            if m:
                cur = int(m.group(1))
            light_of_line[i] = cur
    return light_of_line


def run_with_trace(py_path: Path, light_of_line: dict):
    """在 tracer 下执行生成的 Python，返回被覆盖到的光明行号集合。"""
    covered_light = set()

    def tracer(frame, event, arg):
        if event == "line" and frame.f_code.co_filename == str(py_path):
            ln = frame.f_lineno
            lit = light_of_line.get(ln)
            if lit is not None:
                covered_light.add(lit)
        return tracer

    src = open(py_path, encoding="utf-8").read()
    cwd = os.getcwd()
    try:
        os.chdir(str(PROJECT_DIR))  # 保证 stdlib 相对路径可被解析
        sys.settrace(tracer)
        exec(compile(src, str(py_path), "exec"), {})
    finally:
        sys.settrace(None)
        os.chdir(cwd)
    return covered_light


def parse_functions(light_path: Path):
    """解析光明源中的 段落(函数) 边界（按缩进判定函数体结束）。

    光明使用类 Python 的缩进语法：函数体 = 定义行之后、缩进深于定义行的
    连续语句；遇到缩进不大于定义行的语句即视为函数结束（或到下一函数定义）。
    """
    lines = light_path.read_text(encoding="utf-8").splitlines()
    indent_of = lambda s: len(s) - len(s.lstrip(" \t"))
    starts = []
    for i, ln in enumerate(lines, 1):
        m = FUNC_DEF_RE.match(ln)
        if m:
            starts.append((i, m.group(1), indent_of(ln)))
    funcs = []
    total = len(lines)
    for idx, (s, name, ind) in enumerate(starts):
        next_start = starts[idx + 1][0] if idx + 1 < len(starts) else total + 1
        e = s
        for j in range(s + 1, next_start):
            cur = lines[j - 1]
            if cur.strip() == "":
                e = j
                continue
            if indent_of(cur) <= ind:
                break
            e = j
        funcs.append({"name": name, "start": s, "end": e})
    return funcs, total


def collect(light_file: Path):
    """编译、执行、统计，返回覆盖率数据结构。"""
    with tempfile.TemporaryDirectory() as td:
        py_out = Path(td) / "_cov_gen.py"
        compile_to_py(light_file, py_out)
        light_of_line = build_src_map(py_out)
        executable_light = {v for v in light_of_line.values() if v is not None}
        covered_light = run_with_trace(py_out, light_of_line)

    funcs, total_lines = parse_functions(light_file)
    func_ranges = [(f["start"], f["end"]) for f in funcs]

    def in_any_func(ln):
        for (s, e) in func_ranges:
            if s <= ln <= e:
                return True
        return False

    # 顶层可执行行（不属于任何函数）
    top_exec = sorted(l for l in executable_light if not in_any_func(l))
    top_cov = sorted(l for l in covered_light if not in_any_func(l))

    func_stats = []
    for f in funcs:
        rng = range(f["start"], f["end"] + 1)
        ex = [l for l in executable_light if l in rng]
        cv = [l for l in covered_light if l in rng]
        func_stats.append(
            {
                "name": f["name"],
                "start": f["start"],
                "end": f["end"],
                "executable": len(ex),
                "covered": len(cv),
                "missing": sorted(set(ex) - set(cv)),
            }
        )

    total_exec = len(executable_light)
    total_cov = len(covered_light & executable_light)
    return {
        "file": str(light_file),
        "total_lines": total_lines,
        "executable_lines": total_exec,
        "covered_lines": total_cov,
        "coverage_percent": round(100.0 * total_cov / total_exec, 1) if total_exec else 0.0,
        "top_level": {
            "executable": len(top_exec),
            "covered": len(top_cov),
            "missing": sorted(set(top_exec) - set(top_cov)),
        },
        "functions": func_stats,
        "missing_lines": sorted(set(executable_light) - covered_light),
    }


def cmd_run(args):
    light_file = Path(args.file)
    if not light_file.exists():
        print(f"错误：文件不存在 {light_file}", file=sys.stderr)
        return 2
    data = collect(light_file)
    out = Path(args.out)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成覆盖率数据：{out}")
    print(
        f"  可执行行 {data['executable_lines']} · 已覆盖 {data['covered_lines']} · "
        f"覆盖率 {data['coverage_percent']}%"
    )
    return 0


def cmd_report(args):
    cov = Path(args.cov)
    if not cov.exists():
        print(f"错误：未找到覆盖率数据 {cov}（先运行 coverage run）", file=sys.stderr)
        return 2
    data = json.loads(cov.read_text(encoding="utf-8"))

    print(f"覆盖率报告：{data['file']}")
    print(f"总览：可执行行 {data['executable_lines']} / 已覆盖 {data['covered_lines']} "
          f"= {data['coverage_percent']}%")
    print()
    print(f"{'函数':<16}{'可执行':>8}{'已覆盖':>8}{'覆盖率':>10}")
    print("-" * 44)
    for f in data["functions"]:
        pct = (100.0 * f["covered"] / f["executable"]) if f["executable"] else 0.0
        print(f"{f['name']:<16}{f['executable']:>8}{f['covered']:>8}{pct:>9.1f}%")
    top = data["top_level"]
    tp = (100.0 * top["covered"] / top["executable"]) if top["executable"] else 0.0
    print(f"{'(顶层)':<16}{top['executable']:>8}{top['covered']:>8}{tp:>9.1f}%")
    print("-" * 44)

    if args.show_missing and data["missing_lines"]:
        print("\n未覆盖行（光明源码行号）:")
        print("  " + ", ".join(str(x) for x in data["missing_lines"]))
    return 0


def main():
    ap = argparse.ArgumentParser(description="光明代码覆盖率工具（基础原型）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="编译并执行，生成覆盖率数据")
    p_run.add_argument("file", help=".light 源文件")
    p_run.add_argument("--out", default="coverage.lightcov", help="输出 JSON 路径")
    p_run.set_defaults(func=cmd_run)

    p_rep = sub.add_parser("report", help="展示覆盖率报告")
    p_rep.add_argument("cov", nargs="?", default="coverage.lightcov", help="覆盖率 JSON")
    p_rep.add_argument("--show-missing", action="store_true", help="列出未覆盖行")
    p_rep.set_defaults(func=cmd_report)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
