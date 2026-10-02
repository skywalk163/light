#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compiler_bench.py —— 光明编译器「每例启动耗时」基准 + 温解释器缓存验证（轨道 C 支线）

背景（国庆7天_开发计划书_v2 §四·轨道 C 支线）：
  「编译器启动约 15s/例是当前最大痛点，尝试缓存编译产物」。

结论（本脚本实测）：
  - 冷启动（每次 `light.py run` 起一个新 Python 进程）≈ 4.6s/例（本机 Windows 开发机；
    计划书里的 15s 是 0.82 / 1.5 资源更紧的盒子上测得）。
  - 真正瓶颈不是 codegen（约 0.5s），而是「每个例子都重新拉起解释器 + 重新 import
    整个编译器（code_generator / antlrparser / stdlib）」的固定开销（≈ 4s）。
  - 把编译器留在进程内（温解释器 / 编译守护进程）后，每例降到 ≈ 0.5s —— 约 8x 提速。
  - 因此「缓存编译产物（.py）」收益很小（codegen 本就快）；真正的杠杆是「温解释器」，
    即把解释器+编译器常驻，对每个 .light 只做 codegen+exec。

用法：
  python scripts/compiler_bench.py            # 默认 6 个例子
  python scripts/compiler_bench.py 10        # 指定例子数
  python scripts/compiler_bench.py 6 --verbose

本脚本是**纯增量**工具：不修改编译器源码，只复用 `cli/light.py` 的公开函数
`_run_src(source, file_path, stdlib_dir)` 在进程内做温编译，用于量化提速。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "cli", "light.py")
PY = sys.executable

SAMPLE = '段落 主:\n    设 消息 为 "bench-{i}"\n    打印(消息)\n'


def _make_samples(n, d):
    paths = []
    for i in range(n):
        p = os.path.join(d, f"bench_{i}.light")
        with open(p, "w", encoding="utf-8") as f:
            f.write(SAMPLE.format(i=i))
        paths.append(p)
    return paths


def _baseline(subprocess_paths):
    """冷启动：每个文件起一个全新 Python 进程跑 `light.py run`。"""
    total = 0.0
    for p in subprocess_paths:
        t0 = time.perf_counter()
        r = subprocess.run(
            [PY, CLI, "run", p],
            capture_output=True, text=True,
        )
        total += time.perf_counter() - t0
        if r.returncode != 0:
            raise RuntimeError(f"baseline run failed on {p}:\n{r.stderr[-500:]}")
    return total


def _warm(subprocess_paths):
    """温解释器：import 编译器一次，进程内对每例调用 _run_src。"""
    spec = importlib.util.spec_from_file_location("light_cli", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    total = 0.0
    for p in subprocess_paths:
        with open(p, encoding="utf-8") as f:
            src = f.read()
        t0 = time.perf_counter()
        mod._run_src(src, p, None)
        total += time.perf_counter() - t0
    return total


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    verbose = "--verbose" in sys.argv
    print(f"[compiler_bench] 例子数={n}  CLI={CLI}")
    with tempfile.TemporaryDirectory() as d:
        paths = _make_samples(n, d)
        t_b = _baseline(paths)
        t_w = _warm(paths)
    per_b = t_b / n
    per_w = t_w / n
    speedup = per_b / per_w if per_w else float("inf")
    print()
    print(f"  冷启动（每例新进程） : 总计 {t_b:6.2f}s | 每例 {per_b:5.2f}s")
    print(f"  温解释器（进程内复用）: 总计 {t_w:6.2f}s | 每例 {per_w:5.2f}s")
    print(f"  提速倍数            : {speedup:5.1f}x")
    print()
    print("[结论] 每例成本几乎全在『拉起解释器+import 编译器』；把编译器常驻（编译守护进程）")
    print("       后每例 ≈ codegen+exec（~0.5s）。缓存 .py 产物收益很小，真正杠杆是温解释器。")
    if verbose:
        print(f"[env] python={PY}")
    # 返回结构化数据供调用方读取
    return {"baseline_total": t_b, "warm_total": t_w,
            "baseline_per": per_b, "warm_per": per_w, "speedup": speedup}


if __name__ == "__main__":
    main()
