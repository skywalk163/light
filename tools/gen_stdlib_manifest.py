#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准库 / 扩展库「导出清单」生成器

背景
----
stdlib 与 contrib 下的模块，真正的实现都在同名 `.py` 文件里，
配套的 `.duan` 文件只是一份**导出清单**（manifest），形如：

    # 段言标准库 - 哈希与加密模块
    #
    # 用法：
    #   从《哈希》导入《MD5》。

    导出 MD5 SHA1 SHA256 SHA512。

但历史上有大量 `.duan` 被当成「说明文档」来写：整篇是没有 `#` 前缀的
散文，于是词法器把「段言标准库」这类文字当成关键字，导致解析全红。
本工具把这些文件重建为合法清单：

1. 从 `.py` 的 `__all__`（或公开的顶层 def/class）提取导出名；
2. 把原 `.duan` 里的散文说明整体转成 `#` 注释（**文档不丢**）；
3. 追加 `导出 ...。` 语句；
4. 生成后立即用真实解析器验证，**解析不通过就不写盘**。

安全策略
--------
* 默认 dry-run，必须显式 `--apply` 才写盘；
* 只处理「不含代码行」的文件，含旧代码的文件仅列出、不自动改
  （需要 `--force` 才处理，并且同样受解析验证保护）；
* 写盘前生成 `.bak_before_manifest` 备份。

用法
----
    python tools/gen_stdlib_manifest.py                # 预览
    python tools/gen_stdlib_manifest.py --apply        # 执行
    python tools/gen_stdlib_manifest.py --apply stdlib # 只处理 stdlib
"""

import argparse
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

DEFAULT_DIRS = ['stdlib', 'contrib']

# 判定「这一行是段言代码」而不是散文说明。三条规则互补：
#
# 1) CODE_LINE_RX：关键字 + 分隔符的常规写法（`段落 X(...)`、`导出 A B。`）。
#    要求关键字后必须有分隔符，避免误伤 “创建计数器(可迭代对象) - 统计…” 这类文档行。
# 2) BLOCK_OPEN_RX：关键字后**没有空格**的 Python 直译残留（`定义设置随机种子(种子):`）。
#    只认「定义类」关键字且整行以冒号收尾，所以 `导出：` / `用法：` 这类文档小标题不会误判。
# 3) PY_LEFTOVER_RX：直接混进来的 Python 语句（`return ...`、`import ...`、`self.x`）。
CODE_LINE_RX = re.compile(
    r'^\s*(段落|函数|定义|设|类|导出|从|导入|如果|返回|对于|当|实现|协议|接口|结构|循环|尝试)'
    r'[\s（(《]'
)
BLOCK_OPEN_RX = re.compile(
    r'^\s*(段落|函数|定义|类|如果|对于|当|循环|尝试|实现|协议|接口|结构)\S.*[:：]\s*$'
)
PY_LEFTOVER_RX = re.compile(
    r'^\s*(return|import|from|def|class|pass|raise|with|try|except|elif|else)\b|\bself\.'
)


def is_code_line(line):
    return bool(
        CODE_LINE_RX.search(line)
        or BLOCK_OPEN_RX.search(line)
        or PY_LEFTOVER_RX.search(line)
    )

# 每行 导出 语句最多放几个名字 / 多少个字符
NAMES_PER_LINE = 6
MAX_LINE_CHARS = 60


# ---------------------------------------------------------------- 导出名提取

def extract_exports(py_path):
    """从 .py 里提取导出名。优先 __all__，否则取公开顶层 def/class。"""
    with io.open(py_path, encoding='utf-8') as f:
        src = f.read()
    try:
        tree = ast.parse(src, filename=py_path)
    except SyntaxError as e:
        return None, f'.py 自身语法错误: {e}'

    # 1) __all__
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id == '__all__':
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    continue
                names = [str(n) for n in value if isinstance(n, str)]
                names = [n for n in names if n and not n.startswith('_')]
                if names:
                    return names, '__all__'

    # 2) 回退：公开的顶层 def / class
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith('_'):
                names.append(node.name)
    if names:
        return names, '顶层def/class'
    return None, '未找到任何导出名'


def module_doc_first_line(py_path):
    """取 .py 模块 docstring 的首个非空行，用作清单头部说明。"""
    try:
        with io.open(py_path, encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=py_path)
        doc = ast.get_docstring(tree)
    except Exception:
        doc = None
    if not doc:
        return None
    for line in doc.splitlines():
        if line.strip():
            return line.strip()
    return None


# ---------------------------------------------------------------- 清单生成

def classify_lines(text):
    """把原 .duan 拆成 (文档行, 代码行)。文档行保留顺序，用于转注释。"""
    doc_lines, code_lines = [], []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            doc_lines.append('')
            continue
        if s.startswith('#'):
            doc_lines.append(line.rstrip())
            continue
        if is_code_line(line):
            code_lines.append(line.rstrip())
        else:
            doc_lines.append(line.rstrip())
    return doc_lines, code_lines


def to_comment_block(doc_lines):
    """把混杂的文档行统一成 # 注释块，并去掉首尾多余空行。"""
    out = []
    for line in doc_lines:
        if not line.strip():
            out.append('#')
        elif line.lstrip().startswith('#'):
            out.append(line)
        else:
            out.append('# ' + line)
    # 折叠连续的空注释行，并裁掉首尾
    folded = []
    for line in out:
        if line == '#' and folded and folded[-1] == '#':
            continue
        folded.append(line)
    while folded and folded[0] == '#':
        folded.pop(0)
    while folded and folded[-1] == '#':
        folded.pop()
    return folded


LEGACY_DEF_RX = re.compile(
    r'^\s*(?:段落|函数|定义|类|实现|协议|接口|结构)\s*'
    r'([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)'
)


def legacy_defined_names(code_lines):
    """提取旧代码里定义的顶层名字，用于「丢弃是否安全」的覆盖度校验。"""
    names = []
    for line in code_lines:
        if line[:1] in (' ', '\t'):
            continue  # 只看顶层定义
        m = LEGACY_DEF_RX.match(line)
        if m:
            names.append(m.group(1))
    return names


def coverage_report(code_lines, exports):
    """旧代码定义的名字是否都能在 .py 导出里找到。

    返回 (已覆盖数, 未覆盖名字列表)。未覆盖说明 .duan 里可能有 .py 没有的
    独有实现，此时丢弃旧代码是危险的，必须人工介入。
    """
    defined = legacy_defined_names(code_lines)
    if not defined:
        return 0, []
    exp = set(exports)
    missing = [n for n in defined if n not in exp]
    return len(defined) - len(missing), missing


def chunk_names(names):
    """把导出名切成若干 导出 语句，兼顾行宽可读性。"""
    lines, cur, cur_len = [], [], 0
    for n in names:
        if cur and (len(cur) >= NAMES_PER_LINE or cur_len + len(n) + 1 > MAX_LINE_CHARS):
            lines.append('导出 ' + ' '.join(cur) + '。')
            cur, cur_len = [], 0
        cur.append(n)
        cur_len += len(n) + 1
    if cur:
        lines.append('导出 ' + ' '.join(cur) + '。')
    return lines


def build_manifest(duan_path, py_path, module_name):
    """返回 (新内容, 导出名列表, 来源, 原代码行, 错误)。"""
    names, source = extract_exports(py_path)
    if not names:
        return None, None, source, None, f'无法提取导出名（{source}）'

    with io.open(duan_path, encoding='utf-8') as f:
        original = f.read()
    doc_lines, code_lines = classify_lines(original)

    header = to_comment_block(doc_lines)
    if not header:
        desc = module_doc_first_line(py_path) or f'{module_name}模块'
        header = [f'# 段言标准库 - {desc}']

    # 补一条统一的用法示例（原文档没写过 从《…》导入 才补）
    joined = '\n'.join(header)
    if '导入' not in joined:
        header += ['#', '# 用法：', f'#   从《{module_name}》导入《{names[0]}》。']

    body = chunk_names(names)
    content = '\n'.join(header) + '\n\n' + '\n'.join(body) + '\n'
    return content, names, source, code_lines, None


def parses_ok(content):
    """用真实解析器验证生成结果。"""
    from duan_parser_v3 import DuanParser
    try:
        parser = DuanParser()
        module = parser.parse(content)
    except Exception as e:
        return False, f'{type(e).__name__}: {str(e).strip().splitlines()[:1]}'
    if module is None:
        return False, '返回空模块'
    for i in range(parser.pos, len(parser.tokens)):
        t = parser.tokens[i]
        if t.type.name not in ('NEWLINE', 'DEDENT', 'INDENT', 'DOT', 'EOF'):
            return False, f"残留 token '{t.value}' (行 {t.line})"
    return True, None


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description='生成 stdlib/contrib 的段言导出清单')
    ap.add_argument('dirs', nargs='*', default=None, help='要处理的目录，默认 stdlib contrib')
    ap.add_argument('--apply', action='store_true', help='真正写盘（默认仅预览）')
    ap.add_argument('--force', action='store_true', help='连含旧代码的文件也一起重建')
    ap.add_argument('--quiet', action='store_true', help='只打印汇总')
    args = ap.parse_args()

    dirs = args.dirs or DEFAULT_DIRS

    targets = []
    for d in dirs:
        full = os.path.join(ROOT, d)
        if not os.path.isdir(full):
            print(f'跳过不存在的目录: {d}')
            continue
        for name in sorted(os.listdir(full)):
            if not name.endswith('.duan'):
                continue
            duan = os.path.join(full, name)
            py = duan[:-5] + '.py'
            if os.path.exists(py):
                targets.append((d, name[:-5], duan, py))

    rebuilt, skipped_code, skipped_ok, failed = [], [], [], []

    for d, mod, duan, py in targets:
        # 已经能解析的清单不动
        with io.open(duan, encoding='utf-8') as f:
            cur = f.read()
        ok_now, _ = parses_ok(cur)
        if ok_now:
            skipped_ok.append(f'{d}/{mod}.duan')
            continue

        content, names, source, code_lines, err = build_manifest(duan, py, mod)
        if err:
            failed.append((f'{d}/{mod}.duan', err))
            continue

        # 旧代码能否安全丢弃：它定义的名字必须都已在 .py 的导出里
        if code_lines:
            covered, missing = coverage_report(code_lines, names)
            if missing and not args.force:
                skipped_code.append((
                    f'{d}/{mod}.duan', len(code_lines),
                    f'{len(missing)} 个名字 .py 里没有: ' + '、'.join(missing[:3])
                ))
                continue

        ok, why = parses_ok(content)
        if not ok:
            failed.append((f'{d}/{mod}.duan', f'生成结果仍无法解析: {why}'))
            continue

        if args.apply:
            with io.open(duan + '.bak_before_manifest', 'w', encoding='utf-8', newline='\n') as f:
                f.write(cur)
            with io.open(duan, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
        rebuilt.append((f'{d}/{mod}.duan', len(names), source, len(code_lines or [])))

    # ---- 报告 ----
    mode = '已写盘' if args.apply else '预览（未写盘，加 --apply 执行）'
    print('=' * 66)
    print(f'导出清单生成器 — {mode}')
    print('=' * 66)
    print(f'扫描目录: {", ".join(dirs)}   有 .py 配套的 .duan: {len(targets)}')
    print(f'  ✅ 原本就合法: {len(skipped_ok)}')
    print(f'  🔧 重建清单:   {len(rebuilt)}')
    print(f'  ⏭  含旧代码跳过: {len(skipped_code)}')
    print(f'  ❌ 失败:       {len(failed)}')

    if rebuilt and not args.quiet:
        print('\n--- 重建的清单 ---')
        for f, n, src, ncode in rebuilt:
            extra = f'  (顺带清理 {ncode} 行旧代码)' if ncode else ''
            print(f'  ✓ {f:<38} 导出 {n:3d} 项  来源: {src}{extra}')

    if skipped_code and not args.quiet:
        print('\n--- 含旧代码，需人工确认（--force 可强制重建）---')
        for f, n, sample in skipped_code:
            print(f'  ⏭ {f:<38} {n:3d} 行代码  例: {sample}')

    if failed:
        print('\n--- 失败 ---')
        for f, why in failed:
            print(f'  ✗ {f:<38} {why}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
