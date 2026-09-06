# -*- coding: utf-8 -*-
"""
T6A 原生编译运行 helper（子进程隔离，避免 compile_light_typed 模块缓存污染）。

用法：
  python _t6a_native_helper.py <src.light> <exe_path> [optimize_level] [--compile-only]

  - 正常模式：编译 + 运行，返回被测程序 returncode，stdout/stderr 原样转发。
  - --compile-only：仅编译不运行，编译成功返回 0，失败返回非 0 并把异常写到 stderr。
"""
import os
import sys
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: _t6a_native_helper.py <src> <exe> [opt] [--compile-only]\n")
        return 2
    src = sys.argv[1]
    exe = sys.argv[2]
    compile_only = "--compile-only" in sys.argv
    opt = 0
    for a in sys.argv[3:]:
        if a != "--compile-only":
            try:
                opt = int(a)
            except ValueError:
                pass
    try:
        from llvm.compiler import compile_light_typed
        out_exe = compile_light_typed(src, exe, optimize_level=opt)
        if compile_only:
            return 0
        if not out_exe or not os.path.exists(out_exe):
            sys.stderr.write("编译未产出可执行文件\n")
            return 2
        r = subprocess.run([out_exe], capture_output=True, timeout=180)
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        sys.stderr.write(r.stderr.decode("utf-8", "replace"))
        return r.returncode
    except Exception as e:
        sys.stderr.write(f"{type(e).__name__}: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
