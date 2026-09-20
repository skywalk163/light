#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANTLR 腿冒烟矩阵工具（R75-C）

用途
------------------------------------------------------------
`cli/light_unified.py --backend antlr` 是 unified 代码生成腿（code_generator_unified.py）
唯一的端到端入口。它此前因缺 ANTLR 生成产物而完全不可用（见
scripts/generate_antlr_parser.py 的说明）。本工具把「ANTLR 腿对任意 .light 集合的
解析通过率」变成一条命令 + 一份落盘矩阵，供回归与路线图排期用。

它只做**解析**（LightParser.parse），不执行、不编译产物 —— 因此很快，也不会因为
示例本身需要输入/网络/工具链而产生噪声红。

用法
------------------------------------------------------------
    <venv>/python.exe scripts/antlr_leg_smoke.py                     # 默认 examples/*.light
    <venv>/python.exe scripts/antlr_leg_smoke.py --glob "stdlib/*.light"
    <venv>/python.exe scripts/antlr_leg_smoke.py --out reports/antlr腿_冒烟.md
    <venv>/python.exe scripts/antlr_leg_smoke.py --strict            # 有失败即 rc=1

输出
------------------------------------------------------------
- stdout：通过率 + 逐文件 ok/fail + 失败首错
- 文件：Markdown 矩阵（默认 reports/antlr腿_冒烟_<时间戳>.md），含错误归类统计

注意：`antlrparser/light_visitor.py` 的 `_auto_close_blocks`（缩进→`结束`）与
`light_tokenizer.py` 的语句终止符合成尚未适配 v3 缩进语法，因此当前 v3 示例的
通过率极低 —— 这是本工具的**测量结果**，不是它的缺陷。留待 R76 处理。
"""

from __future__ import annotations

import argparse
import glob
import io
import os
import sys
import time
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ('src', 'antlrparser', os.path.join('antlrparser', 'light_parser')):
    p = os.path.join(REPO_ROOT, _sub)
    if os.path.isdir(p):
        sys.path.insert(0, p)


# 失败归类：按首错里的特征串归因，供路线图量化
BUCKETS = [
    ("缺语句终止符(PERIOD)", "缺少 'PERIOD'"),
    ("块未闭合(缺 `结束`)", "缁撴潫"),
    ("块未闭合(缺 `结束`)", "期望 PERIOD，却遇到了 ''"),
    ("语法不匹配", "语法不匹配"),
    ("多余 token", "多余的"),
    ("缺括号", "缺少 'LPAREN'"),
    ("缺括号", "缺少 'RPAREN'"),
]


def bucket_of(err: str) -> str:
    for name, needle in BUCKETS:
        if needle in err:
            return name
    return "其它"


def main() -> int:
    ap = argparse.ArgumentParser(description="ANTLR 腿解析冒烟矩阵")
    ap.add_argument('--glob', dest='pattern', default='examples/*.light',
                    help='相对仓库根的 glob（默认 examples/*.light）')
    ap.add_argument('--out', default=None, help='矩阵落盘路径（默认 reports/antlr腿_冒烟_<ts>.md）')
    ap.add_argument('--strict', action='store_true', help='有失败则 rc=1')
    ap.add_argument('--show-errors', type=int, default=0, help='每个失败文件打印前 N 条错误（默认 0）')
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(REPO_ROOT, args.pattern)))
    if not files:
        print(f"[错误] glob 未匹配到文件: {args.pattern}")
        return 2

    from light_visitor import LightParser  # 延迟导入：让 --help 不依赖 antlr 运行时

    rows, buckets = [], Counter()
    ok = 0
    t0 = time.time()
    for f in files:
        rel = os.path.relpath(f, REPO_ROOT).replace('\\', '/')
        try:
            src = io.open(f, encoding='utf-8').read()
        except Exception as exc:                                # noqa: BLE001
            rows.append((rel, 'READ_ERR', f'{type(exc).__name__}: {exc}'))
            buckets['读文件失败'] += 1
            continue
        p = LightParser()
        try:
            mod = p.parse(src)
            errs = list(p.errors)
        except Exception as exc:                                # noqa: BLE001
            mod, errs = None, [f'[异常] {type(exc).__name__}: {exc}']
        if mod is not None and not errs:
            ok += 1
            rows.append((rel, 'OK', ''))
        else:
            first = (errs[0] if errs else '解析返回 None')
            first = str(first).replace('\n', ' ')
            rows.append((rel, 'FAIL', first))
            buckets[bucket_of(first)] += 1

    elapsed = time.time() - t0
    total = len(files)
    lines = [
        '# ANTLR 腿解析冒烟矩阵（cli/light_unified.py --backend antlr 的前置能力）',
        '',
        f'- 生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}',
        f'- 集合：`{args.pattern}`（{total} 个文件）',
        f'- 结果：**{ok} / {total} 解析通过**（耗时 {elapsed:.1f}s，仅解析不执行）',
        f'- 工具：`scripts/antlr_leg_smoke.py`',
        '',
        '## 失败归类',
        '',
        '| 归类 | 数量 |',
        '|---|---|',
    ]
    for name, cnt in buckets.most_common():
        lines.append(f'| {name} | {cnt} |')
    lines += ['', '## 逐文件', '', '| 文件 | 结果 | 首错 |', '|---|---|---|']
    for rel, st, err in rows:
        lines.append(f'| `{rel}` | {st} | {err[:110]} |')
    report = '\n'.join(lines) + '\n'

    out = args.out or os.path.join(REPO_ROOT, 'reports',
                                   f'antlr腿_冒烟_{time.strftime("%Y-%m-%d-%H%M%S")}.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(report)

    print(f'ANTLR 腿解析冒烟：{ok}/{total} 通过（{elapsed:.1f}s）')
    print(f'矩阵已落盘：{os.path.relpath(out, REPO_ROOT)}')
    for name, cnt in buckets.most_common():
        print(f'  失败归类 {name}: {cnt}')
    if args.show_errors:
        shown = 0
        for rel, st, err in rows:
            if st != 'OK' and shown < args.show_errors:
                print(f'  [FAIL] {rel}\n         {err[:160]}')
                shown += 1
    return 1 if (args.strict and ok != total) else 0


if __name__ == '__main__':
    sys.exit(main())
