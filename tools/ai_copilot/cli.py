#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明 AI Copilot — 命令行入口

集成到 light CLI 的子命令，提供算力不足场景下的光明代码生成辅助。

用法：
    # 生成 prompt（粘贴给任意 AI 使用）
    light ai prompt "写一个二分查找函数"
    light ai prompt --mode translate "def add(a, b): return a + b"
    light ai prompt --mode paragraph "写一个阶乘段落"

    # 输出语法速查卡（精简版/完整版）
    light ai card
    light ai card --full

    # 列出代码片段库
    light ai snippets

    # Python→光明对照示例
    light ai examples

    # 校验光明代码（语法检查 + 运行）
    light ai check hello.light
"""

import argparse
import os
import sys
import subprocess

# 路径设置
_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_TOOL_DIR))
sys.path.insert(0, _TOOL_DIR)
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'src'))


def _ensure_utf8():
    """确保 stdout 使用 UTF-8 编码"""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


def cmd_prompt(args):
    """生成 prompt"""
    _ensure_utf8()
    from prompt_generator import generate_prompt

    mode = args.mode or "auto"
    compact = not args.full
    user_input = args.input

    # 如果输入是文件路径，读取文件内容
    if os.path.isfile(user_input):
        with open(user_input, encoding='utf-8') as f:
            user_input = f.read()

    prompt = generate_prompt(user_input, mode=mode, compact=compact)
    print(prompt)


def cmd_card(args):
    """输出语法速查卡"""
    _ensure_utf8()
    from syntax_card import generate_syntax_card

    compact = not args.full
    card = generate_syntax_card(compact=compact, include_verbs=args.verbs)
    print(card)


def cmd_snippets(args):
    """列出代码片段库"""
    _ensure_utf8()
    from snippets import list_snippets, get_snippet

    if args.name:
        snippet = get_snippet(args.name)
        if not snippet:
            print(f"片段不存在: {args.name}")
            sys.exit(1)
        print(f"名称：{args.name}")
        print(f"用途：{snippet['desc']}")
        print(f"模板：\n{snippet['code']}")
        if 'example' in snippet:
            print(f"示例：\n{snippet['example']}")
    else:
        print(list_snippets())


def cmd_examples(args):
    """输出 Python→光明对照示例"""
    _ensure_utf8()
    from syntax_card import generate_example_pairs
    print(generate_example_pairs())


def cmd_check(args):
    """校验光明代码文件"""
    _ensure_utf8()
    filepath = args.file

    if not os.path.isfile(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    # Step 1: 语法检查
    print(f"[1/2] 语法检查: {filepath}")
    result = subprocess.run(
        [sys.executable, '-m', 'cli.light', 'check', filepath],
        capture_output=True, text=True, encoding='utf-8',
        cwd=_PROJECT_DIR,
    )
    if result.returncode != 0:
        print(f"  ✗ 语法检查失败:")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return
    print(f"  ✓ 语法检查通过")

    # Step 2: 运行检查
    if args.run:
        print(f"[2/2] 运行测试: {filepath}")
        result = subprocess.run(
            [sys.executable, '-m', 'cli.light', 'run', filepath],
            capture_output=True, text=True, encoding='utf-8',
            cwd=_PROJECT_DIR,
            timeout=args.timeout,
        )
        if result.returncode != 0:
            print(f"  ✗ 运行失败:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        else:
            print(f"  ✓ 运行成功")
            if result.stdout.strip():
                print(f"  输出:")
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
    else:
        print("[2/2] 跳过运行检查（使用 --run 启用）")


def main():
    parser = argparse.ArgumentParser(
        prog='light ai',
        description='光明 AI Copilot — 算力不足场景下的光明代码生成辅助工具',
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # prompt 子命令
    p_prompt = subparsers.add_parser('prompt', help='生成让 AI 写光明代码的 prompt')
    p_prompt.add_argument('input', help='需求描述或 Python 代码（也支持文件路径）')
    p_prompt.add_argument('--mode', choices=['auto', 'translate', 'create', 'paragraph'],
                         default='auto', help='生成模式（默认 auto 自动检测）')
    p_prompt.add_argument('--full', action='store_true', help='使用完整语法卡（默认精简卡）')
    p_prompt.set_defaults(func=cmd_prompt)

    # card 子命令
    p_card = subparsers.add_parser('card', help='输出光明语法速查卡')
    p_card.add_argument('--full', action='store_true', help='完整版（默认精简版）')
    p_card.add_argument('--verbs', action='store_true', help='包含动词参数参照表')
    p_card.set_defaults(func=cmd_card)

    # snippets 子命令
    p_snippets = subparsers.add_parser('snippets', help='列出代码片段库')
    p_snippets.add_argument('name', nargs='?', help='查看指定片段详情')
    p_snippets.set_defaults(func=cmd_snippets)

    # examples 子命令
    p_examples = subparsers.add_parser('examples', help='Python→光明对照示例')
    p_examples.set_defaults(func=cmd_examples)

    # check 子命令
    p_check = subparsers.add_parser('check', help='校验光明代码（语法+运行）')
    p_check.add_argument('file', help='光明代码文件路径')
    p_check.add_argument('--run', action='store_true', help='同时运行测试')
    p_check.add_argument('--timeout', type=int, default=10, help='运行超时秒数（默认10）')
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == '__main__':
    main()
