# -*- coding: utf-8 -*-
"""
光明代码检查器 - 命令行工具

用法:
    python -m src.linter.cli file.light          # 检查单个文件
    python -m src.linter.cli .                   # 检查当前目录
    python -m src.linter.cli --rules E001,W001   # 仅启用指定规则
    python -m src.linter.cli --json file.light    # JSON 输出
"""

import os
import sys
import json
import argparse

from src.linter.light_linter import LightLinter, lint_file, lint_directory


def _load_light_toml() -> dict:
    """从当前工作目录读取 light.toml 配置（若存在）"""
    toml_path = os.path.join(os.getcwd(), 'light.toml')
    if not os.path.isfile(toml_path):
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import toml as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(toml_path, 'rb') as f:
            data = tomllib.load(f)
        return data.get('linter', data) if isinstance(data, dict) else {}
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(
        prog='light-lint',
        description='光明代码检查器'
    )
    parser.add_argument('target', help='文件或目录路径')
    parser.add_argument('--rules', help='仅启用指定规则，用逗号分隔（如 E001,W001）')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    parser.add_argument('--list-rules', action='store_true', help='列出所有可用规则')
    parser.add_argument('--style', choices=['工程体', '教学体'], default=None,
                        help='文体风格检查模式（工程体/教学体）')
    args = parser.parse_args()

    # 从 light.toml 读取默认 style（命令行参数优先）
    toml_cfg = _load_light_toml()
    if args.style is None and 'style' in toml_cfg:
        args.style = toml_cfg['style']

    if args.list_rules:
        from src.linter.light_linter import RULES
        print("可用规则:")
        for rule_id, rule_info in sorted(RULES.items()):
            print(f"  {rule_id} [{rule_info['severity']}] {rule_info['name']}: {rule_info['description']}")
        return 0

    enabled_rules = None
    if args.rules:
        enabled_rules = [r.strip() for r in args.rules.split(',') if r.strip()]

    linter = LightLinter(rules=enabled_rules, style=args.style)

    if args.json:
        # JSON 输出模式
        if os.path.isfile(args.target):
            results = linter.lint_file(args.target)
            print(linter.format_json(args.target))
        elif os.path.isdir(args.target):
            all_results = []
            for root, dirs, files in os.walk(args.target):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fp = os.path.join(root, f)
                        results = linter.lint_file(fp)
                        all_results.extend(linter.results)
            print(linter.format_json(args.target))
        else:
            print(f"错误: 路径不存在: {args.target}")
            return 1
    else:
        if os.path.isfile(args.target):
            return lint_file(args.target, linter)
        elif os.path.isdir(args.target):
            return lint_directory(args.target, linter)
        else:
            print(f"错误: 路径不存在: {args.target}")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())