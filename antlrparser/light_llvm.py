"""
光明 LLVM 编译器 - v2
直接编译 .light 源码为原生可执行文件
"""

import sys
import os
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from light_visitor import LightParser
from llvm_codegen import LLVMCodeGen


def compile_light(source_path: str, output_path: str = None, verbose: bool = False):
    """
    编译 .light 文件为原生可执行文件
    
    Args:
        source_path: .light 源文件路径
        output_path: 输出 .exe 路径（默认与源文件同名）
        verbose: 是否输出详细信息
    """
    # 读取源码
    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    if verbose:
        print(f"[1/5] 解析源码: {len(source)} 字符")

    # 解析
    parser = LightParser()
    module = parser.parse(source)
    if module is None:
        errors = '\n'.join(parser.errors) if parser.errors else "未知错误"
        raise RuntimeError(f"解析失败:\n{errors}")

    if verbose:
        print(f"  解析成功: {len(module.segments)} 段, {len(module.statements)} 语句")

    # 生成 LLVM IR
    if verbose:
        print("[2/5] 生成 LLVM IR...")
    codegen = LLVMCodeGen()
    ir = codegen.generate(module)

    # 写入 .ll 文件
    base_path = output_path or source_path.replace('.light', '')
    if base_path.endswith('.exe'):
        base_path = base_path[:-4]
    ll_path = base_path + '.ll'
    with open(ll_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

    # 编译运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runtime')
    runtime_c = os.path.join(runtime_dir, 'light_runtime.c')
    runtime_o = os.path.join(runtime_dir, 'light_runtime.o')

    # 查找 clang
    clang = find_clang()
    if verbose:
        print(f"  使用编译器: {clang}")

    if verbose:
        print("[3/5] 编译运行时库...")
    result = subprocess.run(
        [clang, '-c', '-O2', runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[4/5] 编译 LLVM IR...")
    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', '-O2', ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为 .exe
    exe_path = base_path + '.exe'
    if verbose:
        print(f"[5/5] 链接为 .exe...")
    result = subprocess.run(
        [clang, ir_o, runtime_o, '-o', exe_path],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    # 清理临时文件
    for f in [ir_o]:
        try:
            os.remove(f)
        except:
            pass

    if verbose:
        size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({size} 字节)")

    return exe_path


def find_clang():
    """查找 clang 编译器"""
    # 常见路径
    candidates = [
        r'E:\Program Files\LLVM\bin\clang.exe',
        r'C:\Program Files\LLVM\bin\clang.exe',
        r'D:\Program Files\LLVM\bin\clang.exe',
        '/usr/bin/clang',
        '/usr/local/bin/clang',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # 从 PATH 查找
    for path in os.environ.get('PATH', '').split(os.pathsep):
        clang_path = os.path.join(path, 'clang.exe' if sys.platform == 'win32' else 'clang')
        if os.path.exists(clang_path):
            return clang_path
    raise RuntimeError("未找到 clang 编译器。请安装 LLVM: https://github.com/llvm/llvm-project/releases")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='光明 LLVM 编译器')
    ap.add_argument('source', help='.light 源文件')
    ap.add_argument('output', nargs='?', help='输出 .exe 路径')
    ap.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    args = ap.parse_args()

    try:
        compile_light(args.source, args.output, verbose=args.verbose or True)
    except Exception as e:
        print(f"编译错误: {e}", file=sys.stderr)
        sys.exit(1)