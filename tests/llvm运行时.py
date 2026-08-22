# -*- coding: utf-8 -*-
"""LLVM 运行时目标码（runtime_typed.o）的进程级缓存。

【为什么要有这个文件】
tests 里所有走 clang 的端到端用例，原来都是这么编的：

    clang -O2 -o x.exe prog.ll src/llvm/runtime_typed.c

也就是每一条用例都把整个 runtime_typed.c 从头编译一遍。实测（Windows /
clang = C:\\Program Files\\LLVM\\bin\\clang.exe）：

    clang -O2 -c src/llvm/runtime_typed.c -o rt.o        → 1.82s   （单编运行时）
    clang -O2 -o x.exe tiny.ll rt.o                      → 0.26s   （用预编好的 .o 链接）
    clang -O2 -o x.exe tiny.ll src/llvm/runtime_typed.c   → 1.92s   （每次重编运行时）

结论：1.92 - 0.26 ≈ 1.7s 是纯粹白烧的，而且每条用例烧一次。

所以：运行时只在**整个 pytest 进程里编一次**，缓存成 .o，后面所有用例只做链接。
请不要"顺手"改回直接把 .c 塞进 clang 命令行——那等于把上面这笔账重新交一遍。

【正确性约束】
1. 缓存按 (clang 绝对路径, 额外编译参数, runtime_typed.c 的 mtime_ns + size) 分桶。
   宏/参数不同 → 键不同 → 一定重新编译，绝不复用别人的目标码。
   有用例是靠"换编译宏"来验证编译期开关的，混用目标码会让那种断言变成永真。
2. .o 只写进 tempfile.mkdtemp() 建的临时目录，atexit 时删除；绝不写进仓库目录
   （仓库根目录那个野生的 runtime_typed.obj 就是反面教材）。
3. 编译失败直接抛 RuntimeError（带 clang stderr），不静默回退成"继续用 .c"。
   静默回退会让这次性能优化变成一个看不见的假绿。
"""

import atexit
import hashlib
import os
import shutil
import subprocess
import tempfile

# 仓库根目录（本文件位于 <root>/tests/）
仓库根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 运行时 C 源码的绝对路径
运行时源码路径 = os.path.join(仓库根目录, 'src', 'llvm', 'runtime_typed.c')

# 缓存键 -> .o 绝对路径
_目标码缓存 = {}

# 存放 .o 的临时目录（懒创建，atexit 清理）
_临时目录 = None


def _取临时目录():
    """懒创建临时目录并注册 atexit 清理。"""
    global _临时目录
    if _临时目录 is None:
        _临时目录 = tempfile.mkdtemp(prefix='light_runtime_o_')
        atexit.register(shutil.rmtree, _临时目录, True)
    return _临时目录


def 取运行时对象(clang, 额外参数=()):
    """把 src/llvm/runtime_typed.c 编成 .o 并缓存，返回 .o 路径。

    Args:
        clang: clang 可执行文件路径。
        额外参数: 追加到 `-O2` 之后的编译参数元组，例如 ('-DLIGHT_FORCE_SELECT',)
                  或 ('-O0', '-g')。参数不同会被视为不同的缓存桶，必定重新编译。
                  clang 里后出现的 -O 覆盖先出现的，所以传 ('-O0',) 即为 -O0。

    Returns:
        已编译好的 .o 文件绝对路径（位于进程私有临时目录内）。

    Raises:
        RuntimeError: clang 编译失败（消息中带 clang 的 stderr），
                      或 runtime_typed.c 不存在。
    """
    if not os.path.exists(运行时源码路径):
        raise RuntimeError(f"运行时源码不存在: {运行时源码路径}")

    额外 = tuple(额外参数)
    源码状态 = os.stat(运行时源码路径)
    缓存键 = (
        os.path.abspath(clang),
        额外,
        源码状态.st_mtime_ns,
        源码状态.st_size,
    )

    已有 = _目标码缓存.get(缓存键)
    if 已有 is not None and os.path.exists(已有):
        return 已有

    指纹 = hashlib.sha1(repr(缓存键).encode('utf-8')).hexdigest()[:12]
    目标路径 = os.path.join(_取临时目录(), f'runtime_typed_{指纹}.o')

    编译命令 = [clang, '-O2', *额外, '-c', 运行时源码路径, '-o', 目标路径]
    结果 = subprocess.run(
        编译命令,
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=仓库根目录,
    )
    if 结果.returncode != 0 or not os.path.exists(目标路径):
        raise RuntimeError(
            "运行时目标码编译失败（不做静默回退，避免掩盖真实问题）\n"
            f"命令: {' '.join(编译命令)}\n"
            f"返回码: {结果.returncode}\n"
            f"stderr:\n{结果.stderr}\n"
            f"stdout:\n{结果.stdout}"
        )

    _目标码缓存[缓存键] = 目标路径
    return 目标路径
