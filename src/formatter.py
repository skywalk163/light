# -*- coding: utf-8 -*-
"""
光明（Light）代码格式化工具

功能：
  - 统一缩进（4 空格）
  - 确保块关键字后有冒号
  - 去除行尾空白
  - 规范化空行
  - 支持 --check 模式

用法：
  light fmt file.light           # 格式化单个文件
  light fmt .                   # 格式化当前目录
  light fmt --check file.light   # 仅检查格式
"""

import os
import sys
import io
import re

# 增加缩进的关键字
BLOCK_START = {
    '如果', '否则如果', '否则若',
    '遍历', '当',
    '尝试', '捕获',
    '匹配', '情况',
    '函数', '段落', '段',
    '类', '接口',
    '构造',
    '异步',
    '使用',
    '嵌入',
    '标注',
    '枚举', '结构体',
    '最终',
    '继承', '实现',
    '静态',
    # L0 单字关键字（v4.1）
    '若', '遍', '试', '捕', '配', '否',
}

# 需要冒号的关键字
NEEDS_COLON = BLOCK_START | {'否则', '接收', '否', '返', '跳', '过', '抛', '终'}

# 输出关键字（不增加缩进，但需要特殊处理）
OUTPUT_KW = {'打印', '返回', '抛出', '继续', '跳出', '导出'}

# 缩进不变量（它们本身不增加缩进，但后续嵌套块需要）
# 这些关键字在下一行保持缩进
INDENT_UNCHANGED = {'否则', '否则如果', '否则若', '捕获', '情况', '默认'}


def _get_keyword(content: str, keywords: set) -> str:
    """获取内容开头的关键字（按长度降序匹配，优先匹配长关键字）"""
    content = content.strip()
    if not content or content.startswith('#'):
        return ''
    
    # 按长度降序排序，确保长关键字优先匹配（如"否则如果"在"否则"之前）
    for kw in sorted(keywords, key=len, reverse=True):
        if content == kw:
            return kw
        # 检查是否以关键字开头，后面跟空格、中文冒号、英文冒号、左括号等
        if content.startswith(kw):
            rest = content[len(kw):]
            if not rest or rest[0] in ' ：:（(（' or '\u4e00' <= rest[0] <= '\u9fff' or rest[0].isalpha() or rest[0] == '《':
                return kw
    # 特殊处理"从"（导入语句）
    if content.startswith('从') and '导入' in content:
        return '从'
    return ''


def _is_comment_or_empty(content: str) -> bool:
    """检查是否是注释或空行"""
    return content.startswith('#') or not content.strip()


def _needs_indent(content: str) -> bool:
    """检查该行是否需要减少缩进"""
    kw = _get_keyword(content, INDENT_UNCHANGED)
    return kw in INDENT_UNCHANGED


def _needs_dedent(content: str) -> bool:
    """检查该行是否在缩进减少后还需要额外处理"""
    return False


def format_code(source: str) -> str:
    """格式化光明代码"""
    lines = source.split('\n')
    result = []
    indent = 0
    # 用于跟踪已处理的行是否在块内
    in_block_stack = []

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped:
            # 保留空行
            result.append('')
            continue

        content = stripped.strip()

        # 注释行保持原样不修改
        if content.startswith('#'):
            result.append('    ' * indent + content)
            continue

        # 获取关键字
        keyword = _get_keyword(content, NEEDS_COLON)

        # 处理"否则"、"否则如果"、"否则若"、"捕获"、"情况"、"默认"以及
        # L0 单字关键字"否"、"捕"：
        # 它们应该与对应的上一级（如"如果"、"尝试"、"匹配"）同级
        if keyword in ('否则', '否则如果', '否则若', '捕获', '情况', '默认', '否', '捕'):
            actual_indent = max(0, indent - 1)
        elif keyword == '从':
            # "从"导入语句不增加缩进
            actual_indent = indent
        else:
            actual_indent = indent

        # 格式化行内容：确保块关键字后有冒号
        if not content.startswith('#'):
            if keyword in NEEDS_COLON:
                # 检查是否已经有冒号（中文或英文）
                if not content.rstrip().endswith('：') and not content.rstrip().endswith(':'):
                    # 如果行以"："结尾（中文冒号），则不添加
                    if not content.rstrip().endswith(':'):
                        content = content + '：'

        # 构建格式化后的行
        formatted_line = '    ' * actual_indent + content
        result.append(formatted_line)

        # 更新下一行的缩进
        if keyword in BLOCK_START:
            indent = actual_indent + 1
        elif keyword in INDENT_UNCHANGED or keyword in ('否', '捕'):
            indent = actual_indent + 1
        else:
            indent = actual_indent

    # 移除末尾空行（保留文件末尾的换行）
    while result and result[-1] == '':
        result.pop()

    return '\n'.join(result) + '\n'


def check_format(source: str) -> list:
    """检查格式问题"""
    formatted = format_code(source)
    if formatted != source:
        orig_lines = source.split('\n')
        fmt_lines = formatted.split('\n')
        issues = []
        max_len = max(len(orig_lines), len(fmt_lines))
        for i in range(max_len):
            o = orig_lines[i].rstrip() if i < len(orig_lines) else ''
            f = fmt_lines[i].rstrip() if i < len(fmt_lines) else ''
            if o != f:
                issues.append({'line': i + 1, 'original': o, 'formatted': f})
        return issues
    return []


def format_file(filepath: str, check_only: bool = False) -> bool:
    """格式化单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        if check_only:
            issues = check_format(source)
            if issues:
                print(f"  x {os.path.basename(filepath)} - {len(issues)} issues")
                for issue in issues[:5]:
                    print(f"    L{issue['line']}: {issue['original'][:60]}")
                    print(f"         -> {issue['formatted'][:60]}")
                if len(issues) > 5:
                    print(f"    ... and {len(issues) - 5} more")
                return False
            print(f"  OK {os.path.basename(filepath)}")
            return True
        else:
            formatted = format_code(source)
            if formatted != source:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                print(f"  OK {os.path.basename(filepath)} (formatted)")
            else:
                print(f"  OK {os.path.basename(filepath)} (unchanged)")
            return True
    except Exception as e:
        print(f"  ERR {os.path.basename(filepath)} - {e}")
        return False


def format_directory(directory: str, check_only: bool = False) -> int:
    """格式化目录"""
    if not os.path.isdir(directory):
        print(f"Error: directory not found: {directory}")
        return 1

    light_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.endswith('.light'):
                light_files.append(os.path.join(root, f))

    if not light_files:
        print("No .light files found")
        return 0

    print(f"Found {len(light_files)} .light file(s)\n")
    all_ok = True
    for fp in sorted(light_files):
        if not format_file(fp, check_only):
            all_ok = False

    print()
    if check_only:
        print("All files OK" if all_ok else "Format issues found - run light fmt to fix")
    else:
        print("Formatting complete")
    return 0 if all_ok else 1


def run_formatter(target: str, check_only: bool = False):
    if os.path.isdir(target):
        return format_directory(target, check_only)
    elif os.path.isfile(target):
        ok = format_file(target, check_only)
        sys.stdout.flush()
        return 0 if ok else 1
    else:
        print(f"Error: path not found: {target}")
        sys.stdout.flush()
        return 1