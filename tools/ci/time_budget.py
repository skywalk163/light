# -*- coding: utf-8 -*-
"""CI 时间预算闸门：超预算按红处理。

口径（2026-08-22 用户裁决）：
  - pull_request 一轮 ≤ 600s（10 分钟）
  - push main 一轮   ≤ 1200s（20 分钟）
超了就退出码 1。理由：CI 慢到没人愿意等，等价于没有 CI——所以时间和正确性一样
是硬指标，不是文档里的一句愿望。

用法（打点 + 收尾判定）：
    python3 tools/ci/time_budget.py --mark 开始
    ...              # 若干 CI 步骤
    python3 tools/ci/time_budget.py --mark 单元集成
    ...
    python3 tools/ci/time_budget.py --check --budget 600

打点文件默认 .ci/timings.tsv，每行 `epoch<TAB>名称`。`--check` 用
「最后一个打点 − 第一个打点」当本轮耗时，并把相邻打点的差值当各段耗时列出来
（谁超时一眼可见，不用翻 raw log）。

只用标准库、不用 shell `date`：Windows runner 上没有 `date +%s`。
"""

from __future__ import annotations

import argparse
import os
import sys
import time

DEFAULT_FILE = os.path.join('.ci', 'timings.tsv')


def 打点(path, name, fresh=False):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    # host 模式 runner 复用 workspace 时可能留着上一轮的打点文件，
    # 那会让「最后一个减第一个」跨到上一轮去、算出一个假的超时。起点打点一律清空。
    with open(path, 'w' if fresh else 'a', encoding='utf-8', newline='\n') as fh:
        fh.write('%.3f\t%s\n' % (time.time(), name))
    print('[CI 计时] 打点 %s' % name)
    return 0


def 读打点(path):
    marks = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if not line.strip():
                continue
            epoch, _, name = line.partition('\t')
            marks.append((float(epoch), name))
    return marks


def 判定(path, budget):
    try:
        marks = 读打点(path)
    except FileNotFoundError:
        print('[CI 计时] 找不到打点文件 %s —— 前面的步骤没打点，无法判定预算' % path)
        return 2
    if len(marks) < 2:
        print('[CI 计时] 打点不足 2 个（%d），无法算耗时' % len(marks))
        return 2

    total = marks[-1][0] - marks[0][0]
    print('[CI 计时] 各段耗时：')
    for (t0, _), (t1, name) in zip(marks, marks[1:]):
        print('       %7.1fs  %s' % (t1 - t0, name))
    print('[CI 计时] 本轮合计 %.1fs / 预算 %ds' % (total, budget))

    if total > budget:
        print('[CI 计时] 超预算 %.1fs，按红处理。' % (total - budget))
        print('[CI 计时] 先看上面最大的那一段；跑得最慢的用例用 pytest --durations 定位。')
        return 1
    print('[CI 计时] 通过：在预算内，余量 %.1fs。' % (budget - total))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default=DEFAULT_FILE, help='打点文件，默认 .ci/timings.tsv')
    ap.add_argument('--mark', help='记一个打点，值是段名（写在这个打点之前那段的名字）')
    ap.add_argument('--fresh', action='store_true', help='配合 --mark：清空打点文件重新开始（起点用）')
    ap.add_argument('--check', action='store_true', help='收尾判定：合计耗时是否在预算内')
    ap.add_argument('--budget', type=int, help='预算秒数（--check 必填）')
    args = ap.parse_args()

    if args.mark:
        return 打点(args.file, args.mark, fresh=args.fresh)
    if args.check:
        if args.budget is None:
            ap.error('--check 需要 --budget')
        return 判定(args.file, args.budget)
    ap.error('要么 --mark，要么 --check')


if __name__ == '__main__':
    sys.exit(main())
