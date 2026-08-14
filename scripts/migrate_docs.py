#!/usr/bin/env python3
"""
段言文档迁移扫描脚本

扫描 .md 文档中的过时语法模式并生成报告（只读，不修改文件）。

检测的过时模式：
1. 令 X = Y          —— 旧赋值语法（推荐：设 X 为 Y）
2. 函数 名(...)       —— 旧函数定义（推荐：段落 名(...):）
3. 行尾分号 ;         —— 当前语法不使用分号
4. { ... } 花括号块   —— 应使用 ": ... 结束" 缩进块
5. version = "1.x"    —— 旧版本字符串（当前应为 4.x）

用法:
    python scripts/migrate_docs.py docs/
    python scripts/migrate_docs.py docs/syntax.md
    python scripts/migrate_docs.py docs/ --quiet   # 仅输出摘要
"""

import sys
import os
import re
from pathlib import Path


# =============================================================================
# 过时模式定义
# =============================================================================

# 仅在段言代码块内检测的语法模式
# 每项: (模式名, 编译后的正则, 简短说明)
SYNTAX_PATTERNS = [
    (
        '旧赋值 令 X = Y',
        re.compile(r'(?<!命)令\s+\S+\s*=\s*'),
        '建议改为「设 X 为 Y」',
    ),
    (
        '旧函数定义 函数 名(...)',
        re.compile(r'函数\s+\S+\s*\('),
        '建议改为「段落 名(...):」',
    ),
    (
        '行尾分号 ;',
        re.compile(r';\s*$'),
        '当前语法不使用分号，请移除',
    ),
    (
        '花括号块 { }',
        re.compile(r'\{\s*$|^\s*\}\s*$'),
        '建议使用「: ... 结束」缩进块',
    ),
]

# 全文件检测的模式（不限于代码块）
FILE_PATTERNS = [
    (
        '旧版本字符串 version = "1.x"',
        re.compile(r'version\s*=\s*"1\.'),
        '建议更新为 4.x 版本',
    ),
]


# =============================================================================
# Markdown 代码块跟踪
# =============================================================================

def iter_code_blocks(lines):
    """遍历行，标记每行是否处于段言代码块内。

    返回: 生成 (行号, 行内容, 是否在段言块内) 三元组
    """
    in_fence = False
    fence_lang = ''
    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        # 检测代码块开始/结束标记（``` 或 ~~~）
        if stripped.startswith('```') or stripped.startswith('~~~'):
            if not in_fence:
                in_fence = True
                # 提取语言标识
                fence_lang = stripped[3:].strip().lower()
            else:
                in_fence = False
                fence_lang = ''
            # 围栏行本身不算代码内容
            yield idx, line, False
            continue
        is_duan = in_fence and ('段言' in fence_lang or 'duan' in fence_lang)
        yield idx, line, is_duan


# =============================================================================
# 单文件扫描
# =============================================================================

def scan_file(filepath: str) -> list:
    """扫描单个 .md 文件，返回命中列表。

    每项: (行号, 模式名, 说明, 行内容)
    """
    hits = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception as e:
            print(f'  [错误] 无法读取 {filepath}: {e}', file=sys.stderr)
            return hits
    except Exception as e:
        print(f'  [错误] 无法读取 {filepath}: {e}', file=sys.stderr)
        return hits

    lines = content.splitlines()

    # 逐行扫描
    for lineno, line, in_duan_block in iter_code_blocks(lines):
        # 段言代码块内检测语法模式
        if in_duan_block:
            for name, pattern, hint in SYNTAX_PATTERNS:
                if pattern.search(line):
                    hits.append((lineno, name, hint, line.rstrip()))
        # 全文件检测版本字符串
        for name, pattern, hint in FILE_PATTERNS:
            if pattern.search(line):
                hits.append((lineno, name, hint, line.rstrip()))

    return hits


# =============================================================================
# 报告生成
# =============================================================================

def print_file_report(filepath: str, hits: list):
    """打印单个文件的命中报告"""
    if not hits:
        return
    print(f'\n📄 {filepath}  ({len(hits)} 处)')
    print('-' * 60)
    for lineno, name, hint, line in hits:
        # 截断过长的行
        display = line if len(line) <= 70 else line[:67] + '...'
        print(f'  行 {lineno:>4} │ {name}')
        print(f'         │   {hint}')
        print(f'         │   {display}')
        print()


def print_summary(all_results: dict):
    """打印汇总摘要"""
    print('\n' + '=' * 60)
    print('  段言文档过时语法扫描报告')
    print('=' * 60)

    total_files = 0
    files_with_hits = 0
    total_hits = 0
    category_stats = {}

    for filepath, hits in all_results.items():
        if hits == 'ERROR':
            continue
        total_files += 1
        if hits:
            files_with_hits += 1
            total_hits += len(hits)
        for _, name, _, _ in hits:
            category_stats[name] = category_stats.get(name, 0) + 1

    print(f'  扫描文件数: {total_files}')
    print(f'  命中文件数: {files_with_hits}')
    print(f'  命中总数:   {total_hits}')
    print()
    print('  按类别统计:')
    if category_stats:
        for name, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            print(f'    {name}: {count} 处')
    else:
        print('    (无过时语法)')
    print('=' * 60)


# =============================================================================
# 主函数
# =============================================================================

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quiet = '--quiet' in sys.argv

    if not args:
        print('用法: python scripts/migrate_docs.py <文件或目录>')
        print('     python scripts/migrate_docs.py docs/')
        print('选项: --quiet  仅输出摘要')
        sys.exit(1)

    all_results = {}

    for path_str in args:
        path = Path(path_str)

        if path.is_file() and path.suffix == '.md':
            hits = scan_file(str(path))
            all_results[str(path)] = hits
            if not quiet:
                print_file_report(str(path), hits)
        elif path.is_dir():
            md_files = sorted(path.rglob('*.md'))
            print(f'扫描目录: {path} ({len(md_files)} 个 .md 文件)')
            for f in md_files:
                hits = scan_file(str(f))
                all_results[str(f)] = hits
                if not quiet:
                    print_file_report(str(f), hits)
        else:
            print(f'跳过: {path} (不是 .md 文件或目录)')

    print_summary(all_results)

    # 有命中则返回退出码 1，便于 CI 集成
    has_hits = any(h for h in all_results.values() if h != 'ERROR')
    sys.exit(1 if has_hits else 0)


if __name__ == '__main__':
    main()
