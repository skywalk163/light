# -*- coding: utf-8 -*-
"""
光明（Light）代码格式化工具 —— 安全子集（R97 重写）

========================================================================
R97 重写说明（对应 R96-KI-01 语义破坏缺陷的根除）
------------------------------------------------------------------------
旧实现用「基于行首前缀猜测」的 regex 启发式重排缩进、给语句补冒号、加运算符
空格、排序导入。这在光明这种**缩进敏感**且关键字多为中文的语言上必然出错：
  1. `NEEDS_COLON` 含单字 `返/跳/过/抛/终`，`返回 x` 被前缀匹配到 `返` → 错补冒号；
  2. 整文件缩进重排为 4 空格，破坏嵌套块结构 → 产物不可解析。
R97 收敛为**只做"绝不改变语义"的空白安全变换**（见 `format_code`）。
本文件与 `src/formatter/light_formatter.py` 保持同一份安全逻辑，确保无论
`light fmt` 走哪条 CLI 路径，都不会破坏源文件。

安全子集内容：
  - 统一换行符为 \\n；
  - 去除每行行尾空白；
  - 折叠 3+ 连续空行为 2 个；
  - 去除文件首尾多余空行；
  - 确保文件以单个换行结尾。

安全性证明：光明块结构完全由「每行缩进 + 行内 token」决定；本工具对这两类
信息逐行精确保留（仅 rstrip 行尾空白，不碰行首缩进、不增删 token），
因此产物解析结果与输入**必然一致**。

注意：`src/formatter.py`（单文件）与 `src/formatter/`（包）并存是已知债务，
二者应择一保留；在合并前，两份实现必须保持一致（均为安全子集）。
========================================================================
"""

import os
import sys

from typing import List


def _safe_format(source: str) -> str:
    """空白安全格式化：仅去行尾空白 / 折叠空行 / 规范换行 / 末尾换行。

    不改变缩进与行内 token，故产物解析结果与输入一致。
    """
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    lines = source.split('\n')
    out: List[str] = []
    blank = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped == '':
            blank += 1
            if blank <= 2:
                out.append('')
        else:
            blank = 0
            out.append(stripped)
    while out and out[0] == '':
        out.pop(0)
    while out and out[-1] == '':
        out.pop()
    text = '\n'.join(out)
    if text and not text.endswith('\n'):
        text += '\n'
    return text


def format_code(source: str) -> str:
    """格式化光明代码（空白安全子集）。"""
    return _safe_format(source)


def check_format(source: str) -> list:
    """检查格式问题，返回差异列表（仅空白 / 空行层面）。"""
    formatted = _safe_format(source)
    if formatted == source:
        return []
    orig_lines = source.replace('\r\n', '\n').split('\n')
    fmt_lines = formatted.split('\n')
    issues = []
    for i in range(max(len(orig_lines), len(fmt_lines))):
        o = orig_lines[i] if i < len(orig_lines) else ''
        f = fmt_lines[i] if i < len(fmt_lines) else ''
        if o != f:
            issues.append({'line': i + 1, 'original': o, 'formatted': f})
    return issues


def format_file(filepath: str, check_only: bool = False) -> bool:
    """格式化单个文件。"""
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
            formatted = _safe_format(source)
            if formatted != source:
                # 还原 CRLF（若原文件使用）以免误伤整工作树换行风格
                crlf = '\r\n' in source
                payload = formatted.replace('\n', '\r\n') if crlf else formatted
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(payload)
                print(f"  OK {os.path.basename(filepath)} (formatted)")
            else:
                print(f"  OK {os.path.basename(filepath)} (unchanged)")
            return True
    except Exception as e:
        print(f"  ERR {os.path.basename(filepath)} - {e}")
        return False


def format_directory(directory: str, check_only: bool = False) -> int:
    """格式化目录下的 .light 文件。"""
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
    """CLI 入口（`light fmt`）：格式化文件或目录。"""
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
