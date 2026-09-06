# -*- coding: utf-8 -*-
"""
T6B 原生编译运行 helper（被 test_T6B_时间系统内建_原生腿.py 以子进程方式调用）。

为什么需要它：
  原生腿测试会 spawn clang 把 .ll 降到目标对象，指令选择阶段在内存受限机上
  （如本机仅 ~696MB 空闲）可能 OOM。若 5 个原生测试在同一 pytest 进程里连续编译，
  Python RSS 累积会把空闲 RAM 压到阈值下，最后一个较重测试（时间管理）verify 阶段
  clang OOM。把「编译 + 运行」整体 fork 到独立子进程，每次都是全新 Python，clang
  拿到与单独运行相同的空闲 RAM（已验证稳定通过），且进程退出即释放，不污染其它测试。

用法：python _t6b_native_helper.py <src.light> <exe_path>
  - 环境变量 INCLUDE/LIB（MSVC/Windows SDK）由父进程透传。
  - 子进程把被测程序的 stdout 原样转发给父进程（key=value 行），便于测试解析。
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
        sys.stderr.write("usage: _t6b_native_helper.py <src> <exe>\n")
        return 2
    src = sys.argv[1]
    exe = sys.argv[2]
    try:
        from llvm.compiler import compile_light_typed
        out_exe = compile_light_typed(src, exe, optimize_level=0)
        if not out_exe or not os.path.exists(out_exe):
            sys.stderr.write("原生腿编译未产出可执行文件: %r\n" % (out_exe,))
            return 2
        r = subprocess.run([out_exe], capture_output=True, timeout=180)
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        sys.stderr.write(r.stderr.decode("utf-8", "replace"))
        return r.returncode
    except Exception:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
