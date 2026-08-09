# -*- coding: utf-8 -*-
"""
光明代码格式化器 - 命令行工具

用法:
    python -m src.formatter.cli file.light          # 格式化单个文件
    python -m src.formatter.cli .                   # 格式化当前目录
    python -m src.formatter.cli --check file.light   # 仅检查格式
    python -m src.formatter.cli --indent 2 file     # 指定缩进大小
"""

import os
import sys
import argparse
from pathlib import Path

from src.formatter.light_formatter import LightFormatter


def format_file(filepath: str, check_only: bool = False,
                indent_size: int = 4, max_line_length: int = 80) -> bool:
    """格式化单个文件"""
    formatter = LightFormatter(indent_size=indent_size, max_line_length=max_line_length)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"  ERR {os.path.basename(filepath)} - 读取失败: {e}")
        return False

    if check_only:
        issues = formatter.check(source)
        if issues:
            print(f"  x {os.path.basename(filepath)} - {len(issues)} 个格式问题")
            for issue in issues[:5]:
                print(f"    L{issue['line']}: {issue['original'][:60]}")
                print(f"         -> {issue['formatted'][:60]}")
            if len(issues) > 5:
                print(f"    ... 还有 {len(issues) - 5} 个问题")
            return False
        print(f"  OK {os.path.basename(filepath)}")
        return True
    else:
        formatted = formatter.format(source)
        if formatted != source:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted)
            print(f"  OK {os.path.basename(filepath)} (已格式化)")
        else:
            print(f"  OK {os.path.basename(filepath)} (无需更改)")
        return True


def format_directory(directory: str, check_only: bool = False,
                     indent_size: int = 4, max_line_length: int = 80) -> int:
    """格式化目录中的 .light 文件"""
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        return 1

    light_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.endswith('.light'):
                light_files.append(os.path.join(root, f))

    if not light_files:
        print("未找到 .light 文件")
        return 0

    print(f"找到 {len(light_files)} 个 .light 文件\n")
    all_ok = True
    for fp in sorted(light_files):
        if not format_file(fp, check_only, indent_size, max_line_length):
            all_ok = False

    print()
    if check_only:
        print("所有文件格式正确" if all_ok else "存在格式问题，请运行格式化修复")
    else:
        print("格式化完成")
    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(
        prog='light-fmt',
        description='光明代码格式化器'
    )
    parser.add_argument('target', help='文件或目录路径')
    parser.add_argument('--check', action='store_true', help='仅检查格式，不修改文件')
    parser.add_argument('--indent', type=int, default=4, help='缩进空格数（默认 4）')
    parser.add_argument('--max-line-length', type=int, default=80, help='最大行长度（默认 80）')
    args = parser.parse_args()

    target = args.target
    if os.path.isdir(target):
        return format_directory(target, args.check, args.indent, args.max_line_length)
    elif os.path.isfile(target):
        ok = format_file(target, args.check, args.indent, args.max_line_length)
        return 0 if ok else 1
    else:
        print(f"错误: 路径不存在: {target}")
        return 1


if __name__ == '__main__':
    sys.exit(main())