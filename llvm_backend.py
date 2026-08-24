#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C 编译器包装脚本（**不是 LLVM 后端**，名字是历史遗留）

⚠️ 第七轮 A7 的表态（任务书 §2.6-2）：

**这个文件不生成 LLVM IR。** 它做的事是「找一个能用的 C 编译器
（clang / gcc / cl），把 `.c` 编成 exe」，即 `查找C编译器()`（:47）与
`编译C到原生()`（:73）。与 `c_backend.编译C到原生` 功能重复。

**谁在用**：全仓无任何模块 import 它（本轮 grep `llvm_backend` 的命中只有
自己的 `__main__` 用法串、任务书、以及 `docs/llvm_backend_design.md`
—— 后者是同名文档，不是本文件）。它只能被当独立脚本手动跑。
本轮**没有删**它：`docs/known_issues.md` 13.1 节还在描述它，而那份文档
不在 A7 的授权文件里，删了会留一条改不了的文档腐烂。第八轮若要删，
连同那一节一起处理。

**原生编译推荐走哪条**：

    light compile 源文件.light --backend llvm-typed [-o 输出] [--optimize O0..O3]
    light run     源文件.light --backend llvm-typed        # 编译到临时目录再执行

实现在 `src/llvm/compiler.py`（`compile_light_typed`）：
`.light → LLVM IR → clang → exe`，IR 由 `src/llvm/codegen_typed.py` 生成，
运行时是 `src/llvm/runtime_typed.c`（含 socket / poller / 事件循环 / TLS）。
另有一条更老的 `antlrparser/llvm_codegen.py`（由 `antlrparser/light_llvm.py`
驱动，依赖 antlr4 运行时），只在旧路径冒烟里出现，新代码别再往上加东西。

编译流程（本文件自己那条）：
  光明 (.light) → C 代码 (.c) → Clang/LLVM → 原生可执行文件 (.exe)

支持的编译器 (按顺序尝试)：
  1. clang (LLVM 原生前端)
  2. gcc (GNU Compiler Collection)
  3. cl (MSVC)

依赖：
  - 需要安装 Clang 或 GCC 编译器
  - 推荐: https://github.com/llvm/llvm-project/releases (LLVM/Clang)
  - 推荐: https://www.mingw-w64.org/ (MinGW-w64 GCC)
"""


import os
import sys
import subprocess


def 查找C编译器():
    """查找系统上可用的 C 编译器
    
    返回:
        (编译器名称, 编译器路径) 或 (None, None)
    """
    candidates = [
        ('clang', 'clang'),
        ('gcc', 'gcc'),
        ('msvc', 'cl'),
    ]
    
    for name, cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return (name, cmd)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    return (None, None)


def 编译C到原生(c文件路径, exe路径=None):
    """使用系统上可用的 C 编译器编译为原生可执行文件
    
    参数:
        c文件路径: .c 文件路径
        exe路径: 输出的 .exe 文件路径（可选）
    
    返回:
        成功时返回 exe 路径，失败时返回 None
    """
    if not os.path.exists(c文件路径):
        print(f"[错误] C 文件不存在: {c文件路径}", file=sys.stderr)
        return None
    
    if exe路径 is None:
        基础名 = os.path.splitext(os.path.basename(c文件路径))[0]
        exe路径 = os.path.join(os.path.dirname(os.path.abspath(c文件路径)), 基础名 + '.exe')
    
    # 查找可用的编译器
    compiler_name, compiler_cmd = 查找C编译器()
    
    if compiler_name is None:
        print(f"[LLVM 后端] 未找到可用的 C 编译器", file=sys.stderr)
        print(f"[LLVM 后端] 请安装 LLVM/Clang: https://github.com/llvm/llvm-project/releases", file=sys.stderr)
        print(f"[LLVM 后端] 或安装 MinGW-w64: https://www.mingw-w64.org/", file=sys.stderr)
        print(f"[LLVM 后端] 或手动编译: clang -o {exe路径} {c文件路径}", file=sys.stderr)
        return None
    
    # 构建编译命令
    if compiler_name == 'msvc':
        cmd = [compiler_cmd, f'/Fe{exe路径}', c文件路径, '/O2', '/W3']
    else:
        cmd = [compiler_cmd, '-o', exe路径, c文件路径, '-O2', '-Wall']
    
    print(f"[LLVM 后端] 编译器: {compiler_name} ({compiler_cmd})")
    print(f"[LLVM 后端] 正在编译: {c文件路径}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(exe路径):
            文件大小 = os.path.getsize(exe路径)
            print(f"[LLVM 后端] 编译成功!")
            print(f"[LLVM 后端] 输出: {exe路径}")
            print(f"[LLVM 后端] 大小: {文件大小 / 1024:.1f} KB")
            return exe路径
        else:
            print(f"[LLVM 后端] 编译失败 (返回码: {result.returncode})", file=sys.stderr)
            if result.stderr:
                for line in result.stderr.split('\n')[-10:]:
                    if line.strip():
                        print(f"  {line}", file=sys.stderr)
            return None
    
    except subprocess.TimeoutExpired:
        print(f"[错误] 编译超时（超过 2 分钟）", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[错误] 编译过程异常: {e}", file=sys.stderr)
        return None


def 编译光明为原生(光明文件路径, 输出路径=None):
    """将光明源文件直接编译为原生可执行文件
    
    先使用 C 后端生成 C 代码，再通过 LLVM 工具链编译为原生代码。
    
    参数:
        光明文件路径: .light 文件路径
        输出路径: 输出的 .exe 文件路径（可选）
    
    返回:
        成功时返回 exe 路径，失败时返回 None
    """
    # 1. 生成 C 代码
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from c_backend import 编译光明到C文件
    
    c文件 = 编译光明到C文件(光明文件路径)
    if c文件 is None:
        return None
    
    # 2. 编译为原生可执行文件
    exe = 编译C到原生(c文件, 输出路径)
    return exe


if __name__ == '__main__':
    # 命令行入口
    if len(sys.argv) < 2:
        print("用法:")
        print("  python llvm_backend.py <源文件.light> [输出.exe]")
        print("  python llvm_backend.py --compile <源文件.c> [输出.exe]")
        print("  python llvm_backend.py --check        检查 C 编译器")
        sys.exit(1)
    
    if sys.argv[1] == '--check':
        name, cmd = 查找C编译器()
        if name:
            result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
            print(f"[LLVM 后端] 找到编译器: {name} ({cmd})")
            print(result.stdout.split('\n')[0])
        else:
            print(f"[LLVM 后端] 未找到 C 编译器")
            print(f"[LLVM 后端] 请安装 LLVM/Clang 或 MinGW-w64 后重试")
        sys.exit(0)
    
    elif sys.argv[1] == '--compile':
        if len(sys.argv) < 3:
            print("用法: python llvm_backend.py --compile <源文件.c> [输出.exe]")
            sys.exit(1)
        c_file = sys.argv[2]
        exe = sys.argv[3] if len(sys.argv) > 3 else None
        result = 编译C到原生(c_file, exe)
    else:
        光明文件 = sys.argv[1]
        输出 = sys.argv[2] if len(sys.argv) > 2 else None
        result = 编译光明为原生(光明文件, 输出)
    
    if result:
        print(f"\n[成功] 原生可执行文件: {result}")
    else:
        print(f"\n[失败] 编译失败", file=sys.stderr)
        sys.exit(1)