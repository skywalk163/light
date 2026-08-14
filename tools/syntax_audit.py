# -*- coding: utf-8 -*-
"""段言语法体检：批量解析全仓 .duan 文件，统计真实可解析率并归类失败原因。

用法：
    .venv/Scripts/python.exe -X utf8 tools/syntax_audit.py [目录...]
不带参数时默认体检 examples/ stdlib/ contrib/ demo/ benchmarks/ project/ duantests/ demos/
"""
import io
import json
import os
import re
import sys
import time
import traceback
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'stdlib'))

DEFAULT_DIRS = ['examples', 'stdlib', 'contrib', 'demo',
                'benchmarks', 'project', 'duantests', 'demos']

# 旧语法特征（用于把失败归因到"新旧语法不兼容"）
LEGACY_PATTERNS = [
    (r'^\s*函数\s+\S+\s*\(', '旧式 函数 名(参数)'),
    (r'^\s*定义\s+\S+\s*\(', '旧式 定义 名(参数)'),
    (r'\{\s*$', '花括号块 {'),
    (r'^\s*\}', '花括号块 }'),
    (r'^\s*结束\s*$', '独立 结束 行'),
]


def detect_legacy(source):
    hits = []
    for line in source.split('\n'):
        for pat, name in LEGACY_PATTERNS:
            if re.search(pat, line):
                hits.append(name)
                break
    return sorted(set(hits))


def classify(err_msg):
    """把错误信息归类，便于聚合统计。"""
    m = err_msg
    if '无法识别语法' in m:
        tok = re.search(r"无法识别语法\s*'([^']*)'", m)
        return f"未消费token:{tok.group(1) if tok else '?'}"
    if 'IndentationError' in m or '缩进' in m:
        return '缩进错误'
    if 'is not defined' in m:
        return '名字未定义'
    if 'Unexpected' in m or '意外' in m:
        return '意外token'
    first = m.strip().split('\n')[0]
    return first[:60]


def summarize_error(text):
    """从「框线式」聚合错误里提取可读摘要。

    解析器抛出的 ParseError 首行是空行 + '┌─ 语法错误'，直接取 splitlines()[0]
    会得到空串。这里优先抓第一条「原因:」，并带上错误总数。
    """
    if not text:
        return text
    total = None
    m = re.search(r'发现 (\d+) 个语法错误', text)
    if m:
        total = int(m.group(1))
    reason = None
    for line in text.splitlines():
        s = line.strip().lstrip('│').strip()
        if s.startswith('原因:'):
            s = s[3:].strip()
            if s.startswith('发现') and '个语法错误' in s:
                continue  # 跳过聚合头，继续找第一条真实原因
            reason = s
            break
    if reason is None:
        for line in text.splitlines():
            s = line.strip()
            if s and not s.startswith(('┌', '│', '└', '-', '错误')):
                reason = s
                break
    reason = reason or text.strip()[:80]
    if total and total > 1:
        return f"[共{total}处] {reason}"
    return reason


def parse_one(path):
    """返回 (ok, err_msg)。ok=True 表示完整解析且无残留 token。"""
    from duan_parser_v3 import DuanParser
    with io.open(path, encoding='utf-8') as f:
        source = f.read()
    try:
        parser = DuanParser()
        module = parser.parse(source)
    except Exception as e:
        return False, source, f"{type(e).__name__}: {summarize_error(str(e))}"
    if module is None:
        return False, source, "解析失败：返回空模块"
    # 与 duan check 一致：检测未消费的实质性 token
    for i in range(parser.pos, len(parser.tokens)):
        t = parser.tokens[i]
        if t.type.name not in ('NEWLINE', 'DEDENT', 'INDENT', 'DOT', 'EOF'):
            return False, source, (f"解析未完成：无法识别语法 '{t.value}' "
                                   f"(行 {t.line}, 列 {t.col})")
    return True, source, None


def main():
    dirs = sys.argv[1:] or DEFAULT_DIRS
    files = []
    for d in dirs:
        full = os.path.join(ROOT, d)
        if not os.path.isdir(full):
            continue
        for dirpath, _, names in os.walk(full):
            if '__pycache__' in dirpath or '.bak' in dirpath:
                continue
            for n in sorted(names):
                if n.endswith('.duan'):
                    files.append(os.path.join(dirpath, n))

    results = []
    t0 = time.time()
    for p in files:
        try:
            ok, source, err = parse_one(p)
        except Exception:
            ok, source, err = False, '', 'AUDIT_CRASH: ' + traceback.format_exc(limit=1)
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        results.append({
            'file': rel,
            'ok': ok,
            'error': err,
            'category': classify(err) if err else None,
            'legacy': detect_legacy(source) if (source and not ok) else [],
        })
    elapsed = time.time() - t0

    total = len(results)
    passed = sum(1 for r in results if r['ok'])
    failed = total - passed

    print("=" * 68)
    print("段言语法体检报告")
    print("=" * 68)
    print(f"扫描目录: {', '.join(dirs)}")
    print(f"文件总数: {total}   通过: {passed}   失败: {failed}   "
          f"通过率: {passed / total * 100:.1f}%" if total else "无文件")
    print(f"耗时: {elapsed:.2f}s")

    # 按目录汇总
    per_dir = {}
    for r in results:
        top = r['file'].split('/')[0]
        d = per_dir.setdefault(top, [0, 0])
        d[0] += 1
        if r['ok']:
            d[1] += 1
    print("\n--- 按目录 ---")
    for d in sorted(per_dir):
        tot, ok = per_dir[d]
        print(f"  {d:<14} {ok:>3}/{tot:<3}  {ok / tot * 100:5.1f}%")

    if failed:
        print("\n--- 失败原因聚类 ---")
        for cat, cnt in Counter(r['category'] for r in results if not r['ok']).most_common():
            print(f"  {cnt:>3}x  {cat}")

        legacy_files = [r for r in results if not r['ok'] and r['legacy']]
        print(f"\n--- 其中含旧语法特征的文件: {len(legacy_files)} ---")
        for cat, cnt in Counter(
                x for r in legacy_files for x in r['legacy']).most_common():
            print(f"  {cnt:>3}x  {cat}")

        print("\n--- 失败明细 ---")
        for r in results:
            if not r['ok']:
                tag = ('[旧语法:' + ','.join(r['legacy']) + ']') if r['legacy'] else ''
                print(f"  ✗ {r['file']} {tag}")
                print(f"      {r['error'].splitlines()[0][:110]}")

    out = os.path.join(ROOT, 'tools', 'syntax_audit_report.json')
    with io.open(out, 'w', encoding='utf-8') as f:
        json.dump({'total': total, 'passed': passed, 'failed': failed,
                   'results': results}, f, ensure_ascii=False, indent=2)
    print(f"\n明细已写入: {os.path.relpath(out, ROOT)}")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
