#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（DuanLang）示例项目打包脚本

将 examples/ 目录下的 .duan 示例项目编译为可独立分发的工具包。
支持两种后端：
  - src（Python 解释执行）：编译为 .py 并生成包装脚本
  - llvm（LLVM 原生编译）：生成 LLVM IR，再尝试编译为原生二进制

用法：
  python tools/packager/build_example.py                    # 打包所有示例
  python tools/packager/build_example.py data_cleaner        # 打包指定示例
  python tools/packager/build_example.py --backend llvm      # 使用 LLVM 后端
  python tools/packager/build_example.py --output dist       # 指定输出目录
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# 项目根目录（tools/packager/../../）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保可以导入段言编译器模块
_src_path = os.path.join(PROJECT_ROOT, 'src')
_antlr_path = os.path.join(PROJECT_ROOT, 'antlrparser')
if os.path.isdir(_src_path):
    sys.path.insert(0, _src_path)
if os.path.isdir(_antlr_path):
    sys.path.insert(0, _antlr_path)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ============================================================
# 示例项目打包配置
# ============================================================
# 每项配置：
#   entry:    .duan 入口文件（相对项目根目录）
#   files:    需要打包到输出目录的附加文件
#   description: 工具描述
EXAMPLES = {
    "data_cleaner": {
        "entry": "examples/data_cleaner/主程序.duan",
        "files": [
            "examples/data_cleaner/README.md",
            "examples/data_cleaner/sample_data.csv",
        ],
        "description": "数据清洗工具 - CSV/JSON 数据处理",
    },
    "data_pipeline": {
        "entry": "examples/data_pipeline/pipeline.duan",
        "files": [
            "examples/data_pipeline/README.md",
            "examples/data_pipeline/sample_data.csv",
        ],
        "description": "数据处理管道 - CSV 读取/清洗/聚合/存储/导出 ETL 工具",
    },
    "web_crawler": {
        "entry": "examples/web_crawler/crawler.duan",
        "files": [
            "examples/web_crawler/README.md",
        ],
        "description": "Web 爬虫 - 递归抓取网页链接，生成站点地图",
    },
    "cli_tool": {
        "entry": "examples/cli_tool/file_organizer.duan",
        "files": [
            "examples/cli_tool/README.md",
        ],
        "description": "文件整理器 - 按文件类型自动分类整理",
    },
    # 可以在此处添加更多示例项目
}


def _ensure_project_root():
    """确保当前工作目录是项目根目录"""
    os.chdir(PROJECT_ROOT)


def _make_executable_script(target_dir, entry_name, py_file_rel, backend):
    """创建可执行包装脚本（.bat / .sh）

    Args:
        target_dir: 输出目录
        entry_name: 示例名称（用作脚本名）
        py_file_rel: 生成的 .py 文件相对于 target_dir 的路径
        backend: 后端类型

    Returns:
        生成的脚本文件名
    """
    if sys.platform == "win32":
        # Windows .bat 包装脚本
        bat_path = os.path.join(target_dir, f"{entry_name}.bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write('@echo off\r\n')
            f.write('chcp 65001 > nul\r\n')
            f.write('set PYTHONIOENCODING=utf-8\r\n')
            f.write(f'"{sys.executable}" "%~dp0{py_file_rel}" %*\r\n')
            f.write('if errorlevel 1 pause\r\n')
        return f"{entry_name}.bat"
    else:
        # Unix shell 脚本
        sh_path = os.path.join(target_dir, entry_name)
        with open(sh_path, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\n')
            f.write('DIR="$(cd "$(dirname "$0")" && pwd)"\n')
            f.write(f'export PYTHONIOENCODING=utf-8\n')
            f.write(f'exec "{sys.executable}" "$DIR/{py_file_rel}" "$@"\n')
        os.chmod(sh_path, 0o755)
        return entry_name


def _compile_src(source, entry_name, target_dir):
    """使用 SRC 后端编译 .duan 为 .py

    Args:
        source: .duan 源码
        entry_name: 示例名称
        target_dir: 目标输出目录

    Returns:
        (py_file_rel, success) 生成的 .py 文件相对路径和是否成功
    """
    try:
        from duan_parser_v3 import DuanParser
        from code_generator import PythonCodeGenerator
    except ImportError as e:
        print(f"  [错误] 无法导入 SRC 编译模块: {e}", file=sys.stderr)
        return None, False

    try:
        parser = DuanParser()
        module = parser.parse(source)
        if module is None:
            print("  [错误] 语法解析失败", file=sys.stderr)
            return None, False

        generator = PythonCodeGenerator()
        python_code = generator.generate(module)

        py_file = os.path.join(target_dir, f"{entry_name}.py")
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write("# 由段言编译器自动生成\n")
            f.write("# 源文件: 请勿直接编辑此文件\n")
            f.write("# 用法: python 此文件 [参数...]\n")
            f.write("# -*- coding: utf-8 -*-\n")
            f.write("\n")
            # 注入项目路径，确保运行时能找到标准库模块
            f.write("import sys, os\n")
            f.write(f"_root = os.path.dirname(os.path.abspath(__file__))\n")
            f.write(f"_project = os.path.join(_root, '..', '..', '..')\n")
            f.write(f"_project = os.path.normpath(_project)\n")
            f.write(f"for _p in [os.path.join(_project, 'src'), os.path.join(_project, 'antlrparser')]:\n")
            f.write(f"    if os.path.isdir(_p) and _p not in sys.path:\n")
            f.write(f"        sys.path.insert(0, _p)\n")
            f.write(f"del _root, _project, _p\n")
            f.write("\n")
            f.write(python_code)

        return f"{entry_name}.py", True
    except Exception as e:
        print(f"  [错误] SRC 编译异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None, False


def _compile_llvm(source, entry_name, target_dir):
    """使用 LLVM 后端编译 .duan 为 LLVM IR 并尝试生成原生二进制

    Args:
        source: .duan 源码
        entry_name: 示例名称
        target_dir: 目标输出目录

    Returns:
        (binary_rel, success) 生成的可执行文件相对路径和是否成功
    """
    try:
        from compiler import DuanCompiler
    except ImportError as e:
        print(f"  [错误] 无法导入 LLVM 编译模块: {e}", file=sys.stderr)
        return None, False

    try:
        compiler = DuanCompiler()
        tokens = compiler.tokenize(source)
        raw_ast = compiler.parse_raw(source)
        module = compiler.adapt(raw_ast)

        if not module:
            print("  [错误] LLVM 解析失败", file=sys.stderr)
            return None, False

        # 生成 LLVM IR
        llvm_ir = compiler.generate_llvm_ir(module)

        ll_file = os.path.join(target_dir, f"{entry_name}.ll")
        with open(ll_file, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        print(f"  [LLVM IR] 已生成: {ll_file}")

        # 尝试编译为原生二进制
        exe_name = f"{entry_name}.exe" if sys.platform == "win32" else entry_name
        exe_path = os.path.join(target_dir, exe_name)

        try:
            # 使用 llc 将 LLVM IR 编译为目标文件
            obj_file = os.path.join(target_dir, f"{entry_name}.o")
            subprocess.run(
                ["llc", "-filetype=obj", ll_file, "-o", obj_file],
                check=True, capture_output=True, text=True
            )

            # 使用 clang 链接为目标文件
            subprocess.run(
                ["clang", obj_file, "-o", exe_path],
                check=True, capture_output=True, text=True
            )

            # 清理中间文件
            if os.path.exists(obj_file):
                os.remove(obj_file)

            if sys.platform != "win32":
                os.chmod(exe_path, 0o755)

            print(f"  [原生二进制] 已生成: {exe_path}")
            return exe_name, True

        except FileNotFoundError:
            print("  [警告] 未找到 llc/clang，仅生成 LLVM IR（需手动编译）")
            print("         编译命令: llc -filetype=obj 文件.ll && clang 文件.o -o 程序")
            return f"{entry_name}.ll", True
        except subprocess.CalledProcessError as e:
            print(f"  [警告] 原生编译失败: {e.stderr or e.stdout}")
            print("  [提示] 已保留 LLVM IR 文件，可手动编译")
            return f"{entry_name}.ll", True

    except Exception as e:
        print(f"  [错误] LLVM 编译异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None, False


def build_example(example_name, backend="src", output_dir="output"):
    """构建单个示例项目

    Args:
        example_name: 示例名称（EXAMPLES 字典中的键）
        backend: 编译后端，"src" 或 "llvm"
        output_dir: 输出根目录

    Returns:
        是否成功
    """
    _ensure_project_root()

    if example_name not in EXAMPLES:
        print(f"[错误] 未知示例: {example_name}")
        print(f"  可用示例: {', '.join(EXAMPLES.keys())}")
        return False

    config = EXAMPLES[example_name]
    entry_path = os.path.join(PROJECT_ROOT, config["entry"])
    target_dir = os.path.join(output_dir, example_name)

    print(f"\n{'='*60}")
    print(f"  打包: {example_name}")
    print(f"  描述: {config['description']}")
    print(f"  入口: {config['entry']}")
    print(f"  后端: {backend}")
    print(f"{'='*60}")

    # 检查入口文件是否存在
    if not os.path.exists(entry_path):
        print(f"  [错误] 入口文件不存在: {entry_path}", file=sys.stderr)
        print(f"  [提示] 请先在 EXAMPLES 配置中添加正确的路径")
        return False

    # 创建输出目录
    os.makedirs(target_dir, exist_ok=True)

    # 读取源文件
    with open(entry_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 编译
    if backend == "src":
        py_file_rel, success = _compile_src(source, example_name, target_dir)
        if not success:
            return False

        # 创建可执行包装脚本
        exe_name = _make_executable_script(target_dir, example_name, py_file_rel, backend)
        print(f"  [可执行文件] 已生成: {os.path.join(target_dir, exe_name)}")

    elif backend == "llvm":
        binary_rel, success = _compile_llvm(source, example_name, target_dir)
        if not success:
            return False
        exe_name = binary_rel
    else:
        print(f"  [错误] 不支持的后端: {backend}", file=sys.stderr)
        return False

    # 复制附加文件
    copied_files = []
    for file_rel in config["files"]:
        src = os.path.join(PROJECT_ROOT, file_rel)
        if os.path.exists(src):
            dst = os.path.join(target_dir, os.path.basename(file_rel))
            shutil.copy2(src, dst)
            copied_files.append(os.path.basename(file_rel))
        else:
            print(f"  [警告] 附加文件不存在: {src}")

    # 打印输出结构
    print(f"\n  [输出目录] {os.path.abspath(target_dir)}")
    print(f"  {os.path.join(target_dir, exe_name)}")
    for fname in copied_files:
        print(f"  {os.path.join(target_dir, fname)}")

    print(f"  [成功] 打包完成: {example_name}")
    return True


def build_all(backend="src", output_dir="output"):
    """构建所有示例项目"""
    success_count = 0
    fail_count = 0

    for name in EXAMPLES:
        if build_example(name, backend, output_dir):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"  打包汇总: 成功 {success_count} / 总计 {len(EXAMPLES)}")
    if fail_count > 0:
        print(f"  失败: {fail_count}")
    print(f"{'='*60}")

    return fail_count == 0


def list_examples():
    """列出所有可打包的示例"""
    print("\n可用示例:")
    print(f"{'='*60}")
    for name, config in EXAMPLES.items():
        entry_exists = "✓" if os.path.exists(os.path.join(PROJECT_ROOT, config["entry"])) else "✗"
        print(f"  {name}")
        print(f"    描述: {config['description']}")
        print(f"    入口: {config['entry']} [{entry_exists}]")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="段言（DuanLang）示例项目打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/packager/build_example.py                      # 打包全部
  python tools/packager/build_example.py data_pipeline        # 打包指定示例
  python tools/packager/build_example.py --backend llvm       # 使用 LLVM 后端
  python tools/packager/build_example.py --output dist        # 指定输出目录
  python tools/packager/build_example.py --list               # 列出可用示例
        """
    )
    parser.add_argument("example", nargs="?", help="示例名称（不指定则打包全部）")
    parser.add_argument("--backend", choices=["src", "llvm"], default="src",
                        help="编译后端：src（Python 解释执行，默认）或 llvm（LLVM 原生编译）")
    parser.add_argument("--output", default="output", help="输出目录（默认: output）")
    parser.add_argument("--list", action="store_true", help="列出所有可打包的示例")

    args = parser.parse_args()

    if args.list:
        list_examples()
        return 0

    if args.example:
        success = build_example(args.example, args.backend, args.output)
        return 0 if success else 1
    else:
        success = build_all(args.backend, args.output)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())