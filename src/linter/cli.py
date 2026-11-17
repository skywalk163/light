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


def _iter_light_files(root: str):
    """遍历目录下所有 .light 文件（跳过隐藏目录与 __pycache__）。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        for name in filenames:
            if name.endswith('.light'):
                yield os.path.join(dirpath, name)


def _run_canonical(target: str, style: str, write: bool, json_out: bool) -> int:
    """归一通道：默认只报告差异，write=True 时写回。"""
    from src.linter.canonical import canonicalize, edits_as_dicts

    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = sorted(_iter_light_files(target))
    else:
        print(f"错误: 路径不存在: {target}")
        return 1

    report = []
    total_edits = total_skipped = 0

    for path in files:
        with open(path, 'r', encoding='utf-8', newline='') as f:
            source = f.read()
        new_source, edits, skipped = canonicalize(source, style=style)
        total_edits += len(edits)
        total_skipped += len(skipped)

        if not edits and not skipped:
            continue

        report.append({
            'file': path,
            'edits': edits_as_dicts(edits),
            'skipped': edits_as_dicts(skipped),
        })

        if json_out:
            continue

        print(f"归一 {path}：{len(edits)} 处可自动改，{len(skipped)} 处需人工判断")
        for e in edits:
            print(f"  {e.code} 第{e.line}行:{e.col} 「{e.before}」→「{e.after}」  {e.reason}")
        for s in skipped:
            print(f"  {s.code} 第{s.line}行:{s.col} 「{s.text}」跳过：{s.reason}")

        changed_lines = sorted({e.line for e in edits})
        if changed_lines:
            old_lines = source.split('\n')
            new_lines = new_source.split('\n')
            print(f"  将改 {len(changed_lines)} 行：{changed_lines}")
            for ln in changed_lines[:20]:
                before = old_lines[ln - 1] if ln <= len(old_lines) else ''
                after = new_lines[ln - 1] if ln <= len(new_lines) else ''
                print(f"    第{ln}行 - {before}")
                print(f"    第{ln}行 + {after}")
            if len(changed_lines) > 20:
                print(f"    …… 其余 {len(changed_lines) - 20} 行省略")

        if write and new_source != source:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new_source)
            print(f"  已写回：{path}")

    if json_out:
        import json as _json
        print(_json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"归一汇总：{len(files)} 个文件，{total_edits} 处可自动改，"
              f"{total_skipped} 处需人工判断")

    return 0


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
    parser.add_argument('--check-names', action='store_true',
                        help='执行 AST 级静态名检查（LH-21 E016 未定义的名字 / LH-09 W016 导入名被局部遮蔽）')
    parser.add_argument('--canonical', action='store_true',
                        help='归一检查：同类等价写法收敛到单一权威形态（默认只报告差异）')
    parser.add_argument('--apply', action='store_true',
                        help='把归一结果写回文件（需配合 --canonical；默认 --dry-run）')
    parser.add_argument('--dry-run', action='store_true',
                        help='归一模式只报告差异、不写回（默认行为）')
    args = parser.parse_args()

    # 从 light.toml 读取默认 style / canonical 模式（命令行参数优先）
    toml_cfg = _load_light_toml()
    if args.style is None and 'style' in toml_cfg:
        args.style = toml_cfg['style']
    canonical_cfg = toml_cfg.get('canonical', '关')

    if args.list_rules:
        from src.linter.light_linter import RULES
        print("可用规则:")
        for rule_id, rule_info in sorted(RULES.items()):
            print(f"  {rule_id} [{rule_info['severity']}] {rule_info['name']}: {rule_info['description']}")
        return 0

    # 归一通道：`--canonical` 显式开启；light.toml 的 canonical = 关/报告/写回
    # 决定「未显式给 --apply/--dry-run 时是否写回」，CLI 参数优先。
    if args.canonical and not args.check_names:
        if args.apply:
            write = True
        elif args.dry_run:
            write = False
        else:
            write = canonical_cfg == '写回'
        return _run_canonical(args.target, args.style or '工程体', write, args.json)

    enabled_rules = None
    if args.rules:
        enabled_rules = [r.strip() for r in args.rules.split(',') if r.strip()]

    linter = LightLinter(rules=enabled_rules, style=args.style)

    if args.check_names:
        # LH-21 / LH-09：AST 级静态名检查（`cli/light.py check` 由另一张卡在改，
        # 本卡先在这条 CLI 上开放，规则默认不并入 lint()，避免误报污染全仓 check）
        if os.path.isfile(args.target):
            files = [args.target]
        elif os.path.isdir(args.target):
            files = _iter_light_files(args.target)
        else:
            print(f"错误: 路径不存在: {args.target}")
            return 1
        for fp in files:
            linter.lint_names_file(fp)
        if args.json:
            print(linter.format_json(args.target))
        else:
            out = linter.format_results(args.target)
            if out:
                print(out)
        return 1 if any(r.severity == 'error' for r in linter.results) else 0

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