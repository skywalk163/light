# -*- coding: utf-8 -*-
"""SFT 数据集质量校验：用真实编译器逐条解析样本 output，找出教坏模型的错误样本。

核心思想：训练数据里的段言代码必须能被段言编译器解析。任何解析不过的样本
都会直接教 AI 写出错误代码，属于必须清除的污染。

用法：
    .venv/Scripts/python.exe -X utf8 tools/dataset_audit.py [数据集路径]
    .venv/Scripts/python.exe -X utf8 tools/dataset_audit.py --fix   # 自动修正已知错误模式
"""
import io
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

DEFAULT_DATASET = os.path.join(ROOT, 'tools', 'ai_copilot', 'sft_dataset.jsonl')

# 「X 的 Y 次方」会被解析成属性访问 X.Y，运行期抛 AttributeError。
# 段言正确的幂运算是二元运算符「幂」：X 幂 Y。
# 底数可能是标识符、数字、带括号的表达式或下标访问，需要回扫提取，纯正则不够。
POWER_RX = re.compile(r'\s*的\s*([0-9]+(?:\.[0-9]+)?|[\w\u4e00-\u9fff.]+)\s*次(?:方|幂)')

_CLOSE_TO_OPEN = {')': '(', ']': '[', '}': '{'}


def _scan_base_start(text, end):
    """从 text[:end] 末尾回扫，找出幂运算底数表达式的起始下标。

    支持：标识符/数字（含中文）、括号或方括号结尾的表达式（含函数调用、下标访问）。
    """
    i = end
    while i > 0 and text[i - 1] in ' \t':
        i -= 1
    if i == 0:
        return None
    ch = text[i - 1]
    if ch in _CLOSE_TO_OPEN:
        # 平衡回扫到配对的开括号
        depth = 0
        j = i
        while j > 0:
            c = text[j - 1]
            if c in _CLOSE_TO_OPEN:
                depth += 1
            elif c in '([{':
                depth -= 1
                if depth == 0:
                    j -= 1
                    break
            j -= 1
        else:
            return None
        # 括号前如果紧跟标识符，说明是函数调用/下标，一并纳入
        k = j
        while k > 0 and (text[k - 1].isalnum() or text[k - 1] in '_.'
                         or '\u4e00' <= text[k - 1] <= '\u9fff'):
            k -= 1
        return k
    # 普通标识符或数字
    j = i
    while j > 0 and (text[j - 1].isalnum() or text[j - 1] in '_.'
                     or '\u4e00' <= text[j - 1] <= '\u9fff'):
        j -= 1
    return j if j < i else None


def fix_power_syntax(code):
    """把所有「底数 的 指数 次方/次幂」重写为「底数 幂 指数」。返回 (新代码, 修改次数)。"""
    n = 0
    while True:
        m = POWER_RX.search(code)
        if not m:
            break
        start = _scan_base_start(code, m.start())
        if start is None:
            # 找不到底数，避免死循环：跳过这一处
            break
        base = code[start:m.start()].strip()
        exponent = m.group(1)
        code = code[:start] + f"{base} 幂 {exponent}" + code[m.end():]
        n += 1
    return code, n


# 每条规则：(检测函数, 修复函数, 说明)
FIX_RULES = [
    (lambda c: bool(POWER_RX.search(c)),
     fix_power_syntax,
     '「X 的 Y 次方」→「X 幂 Y」（原写法被解析为属性访问 X.Y，运行期报错）'),
]


def parse_ok(code):
    """返回 (ok, err_first_line)。"""
    from duan_parser_v3 import DuanParser
    try:
        p = DuanParser()
        m = p.parse(code)
    except Exception as e:
        msg = str(e)
        for line in msg.split('\n'):
            line = line.strip().lstrip('│').strip()
            if line.startswith('原因:'):
                return False, line[3:].strip()[:90]
        return False, (msg.strip().split('\n')[0] or type(e).__name__)[:90]
    if m is None:
        return False, '解析返回空模块'
    for i in range(p.pos, len(p.tokens)):
        t = p.tokens[i]
        if t.type.name not in ('NEWLINE', 'DEDENT', 'INDENT', 'DOT', 'EOF'):
            return False, f"未消费 token '{t.value}' (行{t.line})"
    return True, None


def load(path):
    rows = []
    with io.open(path, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((ln, json.loads(line)))
            except Exception as e:
                print(f"  ! 第 {ln} 行 JSON 解析失败: {e}")
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_fix = '--fix' in sys.argv
    path = args[0] if args else DEFAULT_DATASET

    rows = load(path)
    print("=" * 68)
    print(f"数据集校验: {os.path.relpath(path, ROOT)}")
    print("=" * 68)
    print(f"样本总数: {len(rows)}")

    bad = []
    for ln, r in rows:
        code = r.get('output', '')
        if not code.strip():
            bad.append((ln, r, '空 output'))
            continue
        ok, err = parse_ok(code)
        if not ok:
            bad.append((ln, r, err))

    print(f"解析通过: {len(rows) - len(bad)}   失败: {len(bad)}   "
          f"合格率: {(len(rows) - len(bad)) / len(rows) * 100:.2f}%")

    if bad:
        print("\n--- 失败原因聚类 ---")
        for reason, cnt in Counter(b[2] for b in bad).most_common(15):
            print(f"  {cnt:>4}x  {reason}")

        print("\n--- 按 category 分布 ---")
        for cat, cnt in Counter(b[1].get('category', '?') for b in bad).most_common(10):
            print(f"  {cnt:>4}x  {cat}")

        print("\n--- 前 10 条失败样本 ---")
        for ln, r, err in bad[:10]:
            print(f"  行{ln} [{r.get('category', '?')}] {err}")
            print(f"      output: {r.get('output', '')[:80]!r}")

    # 已知错误模式统计（即使能解析，语义也是错的）
    print("\n--- 已知语义错误模式扫描 ---")
    pattern_hits = []
    for ln, r in rows:
        code = r.get('output', '')
        for detect, repair, desc in FIX_RULES:
            if detect(code):
                pattern_hits.append((ln, r, desc))
                break
    if pattern_hits:
        for desc, cnt in Counter(h[2] for h in pattern_hits).most_common():
            print(f"  {cnt:>4}x  {desc}")
        print("\n  示例:")
        for ln, r, desc in pattern_hits[:5]:
            bad = [l for l in r['output'].splitlines() if '次方' in l or '次幂' in l]
            print(f"    行{ln}: {(bad[0] if bad else r['output']).strip()[:66]}")
    else:
        print("  未发现已知错误模式。")

    if do_fix and pattern_hits:
        fixed_rows = []
        n_fixed = 0
        hit_lines = {h[0] for h in pattern_hits}
        for ln, r in rows:
            if ln in hit_lines:
                code = r['output']
                new = code
                for detect, repair, _ in FIX_RULES:
                    if detect(new):
                        new, _cnt = repair(new)
                if new != code:
                    ok, err = parse_ok(new)
                    if ok:
                        r['output'] = new
                        n_fixed += 1
                    else:
                        print(f"  ! 行{ln} 修正后仍无法解析，保持原样: {err}")
            fixed_rows.append(r)

        backup = path + '.bak_before_fix'
        if not os.path.exists(backup):
            with io.open(path, encoding='utf-8') as fsrc, \
                    io.open(backup, 'w', encoding='utf-8') as fdst:
                fdst.write(fsrc.read())
            print(f"\n已备份原文件 → {os.path.relpath(backup, ROOT)}")
        with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
            for r in fixed_rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f"已修正 {n_fixed} 条样本并写回 {os.path.relpath(path, ROOT)}")

    return 1 if (bad or pattern_hits) else 0


if __name__ == '__main__':
    sys.exit(main())
