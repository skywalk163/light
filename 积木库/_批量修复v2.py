# -*- coding: utf-8 -*-
"""
光明积木库批量修复脚本 v2
=========================
修复 blocks_v5/ 目录中的积木文件：

Issue 1: 参数名含数字（如各乘0、减10、加50等）→ 替换为中文
Issue 2: lambda 参数名冲突 → 替换为希腊字母 λ
Issue 3: p_求和 后缀调用模式 → 已检查，KR20.light 已修复
Issue 4: 自动生成桩 → 添加 # 状态：签名占位，无实现

用法: python _批量修复v2.py
"""

import os
import re
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')

# ============================================================
# Issue 1: 参数名中的数字替换表
# 注意：替换顺序不重要了，因为我们会用正则做精确匹配
# 每个替换项 (old, new) 中的 old 是完整的参数名（不含空格）
# ============================================================
PARAM_DIGIT_FIXES = [
    # 带小数点的（参数名中不会出现小数点，但留作安全兜底）
    ('各乘0.5', '各乘零点五'),
    ('各减0.5', '各减零点五'),
    ('各加0.5', '各加零点五'),
    ('各除0.5', '各除零点五'),
    # 纯数字0
    ('各乘0', '各乘零'),
    ('各减0', '各减零'),
    ('各加0', '各加零'),
    ('各除0', '各除零'),
    # 两位数（注意：不匹配 加100 中的加10）
    ('减10', '减十'),
    ('加10', '加十'),
    ('减20', '减二十'),
    ('加20', '加二十'),
    ('减50', '减五十'),
    ('加50', '加五十'),
    # _2 → 甲
    ('_2', '甲'),
]


def fix_param_digits_in_paragraph(line):
    """
    修复 段落 行中的参数名数字。
    只在「接收」之后的参数列表中替换，不影响函数名。
    """
    stripped = line.lstrip()
    if not stripped.startswith('段落 '):
        return line, False

    if '接收' not in line:
        return line, False

    modified = False
    # 按「接收」分割，只替换后面的参数列表
    idx = line.index('接收')
    before = line[:idx + 2]  # 包含「接收」二字
    after = line[idx + 2:]   # 参数列表部分

    for old, new in PARAM_DIGIT_FIXES:
        if old in after:
            after = after.replace(old, new)
            modified = True

    result = before + after
    return result, modified


def fix_param_digits_in_return(line):
    """
    修复 返回 行中的参数名数字。
    只在 返回 行中替换，不影响函数名。
    """
    stripped = line.lstrip()
    if not stripped.startswith('返回 '):
        return line, False

    modified = False
    for old, new in PARAM_DIGIT_FIXES:
        if old in line:
            line = line.replace(old, new)
            modified = True

    return line, modified


def fix_lambda_in_paragraph(line):
    """在 段落 行中将 lambda 参数名替换为 λ"""
    stripped = line.lstrip()
    if not stripped.startswith('段落 '):
        return line, False
    if 'lambda' not in line:
        return line, False
    if '接收' not in line:
        return line, False

    # 只在「接收」之后替换 lambda（参数名）
    idx = line.index('接收')
    before = line[:idx + 2]
    after = line[idx + 2:]
    after = after.replace('lambda', 'λ')
    return before + after, True


def fix_lambda_in_return(line):
    """在 返回 行中将 lambda 变量名替换为 λ"""
    stripped = line.lstrip()
    if not stripped.startswith('返回 '):
        return line, False
    if 'lambda' not in line:
        return line, False
    line = line.replace('lambda', 'λ')
    return line, True


def is_stub(content):
    """判断是否为真正的桩（主体只有 返回 输入）"""
    lines = content.strip().split('\n')
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    if len(code_lines) < 3:
        return False
    last_line = code_lines[-1].strip()
    if last_line == '返回 输入':
        return True
    return False


def add_stub_status_line(content):
    """为自动生成桩添加 # 状态：签名占位，无实现 作为第二行"""
    lines = content.split('\n')
    if len(lines) < 1:
        return content, False
    # 检查是否已有状态行
    for line in lines[:5]:
        if '状态：签名占位，无实现' in line:
            return content, False
    lines.insert(1, '# 状态：签名占位，无实现')
    return '\n'.join(lines), True


def process_file(filepath):
    """处理单个 .light 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    content = original
    fixes_applied = []
    relpath = os.path.relpath(filepath, _HERE)

    # ---- Issue 1: 参数名中的数字修复 ----
    lines = content.split('\n')
    new_lines = list(lines)
    digit_fixed = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('段落 '):
            new_line, modified = fix_param_digits_in_paragraph(line)
            if modified:
                new_lines[i] = new_line
                digit_fixed = True
        elif stripped.startswith('返回 '):
            new_line, modified = fix_param_digits_in_return(line)
            if modified:
                new_lines[i] = new_line
                digit_fixed = True
    if digit_fixed:
        content = '\n'.join(new_lines)
        fixes_applied.append('Issue1:数字参数名')

    # ---- Issue 2: lambda 参数名修复 ----
    base = os.path.basename(filepath)
    if base in ('临界应力.light', '稳定系数.light'):
        lines = content.split('\n')
        new_lines = list(lines)
        lambda_fixed = False
        for i, line in enumerate(lines):
            modified = False
            stripped = line.lstrip()
            if stripped.startswith('段落 '):
                new_line, modified = fix_lambda_in_paragraph(line)
            elif stripped.startswith('返回 '):
                new_line, modified = fix_lambda_in_return(line)
            if modified:
                new_lines[i] = new_line
                lambda_fixed = True
        if lambda_fixed:
            content = '\n'.join(new_lines)
            fixes_applied.append('Issue2:lambda→λ')

    # ---- Issue 4: 自动生成桩标记 ----
    if '自动生成桩' in original:
        if is_stub(content):
            new_content, stub_fixed = add_stub_status_line(content)
            if stub_fixed:
                content = new_content
                fixes_applied.append('Issue4:添加桩状态')

    # 写回文件
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes_applied
    return False, fixes_applied


def main():
    stats = defaultdict(int)
    detail_log = []

    for root, dirs, files in os.walk(BLOCKS_DIR):
        for fname in files:
            if not fname.endswith('.light'):
                continue
            filepath = os.path.join(root, fname)
            modified, fixes = process_file(filepath)
            if modified:
                relpath = os.path.relpath(filepath, _HERE)
                detail_log.append(f'  ✓ {relpath}  [{", ".join(fixes)}]')
                for f in fixes:
                    stats[f] += 1
                stats['total'] += 1

    # 输出报告
    print('=' * 60)
    print('批量修复 v2 完成')
    print('=' * 60)
    print(f'\n共修复 {stats["total"]} 个文件：')
    for key, count in sorted(stats.items()):
        if key != 'total':
            print(f'  {key}: {count} 个文件')
    print()
    if detail_log:
        print('详细列表：')
        for line in detail_log:
            print(line)
    print()
    print('=' * 60)


if __name__ == '__main__':
    main()