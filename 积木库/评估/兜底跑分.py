# -*- coding: utf-8 -*-
"""兜底跑分（Q4 计划 2.4）—— 把真实 LLM 兜底闭环的「沉淀成功率」纳入 CI 门禁。

背景：兜底首跑 harness（`兜底首跑.py`）把每条库外意图的端到端结果写进 `运行日志.jsonl`
（需求/分类/是否兜底/成功/生成块名/体检/冒烟/语义正确/token）。但 `ci_eval.py` 的 22 项闸门
此前完全没覆盖「兜底闭环」本身 —— 一旦生成质量回退（prompt 被改坏、词法器升级引入新坑），
CI 不会红。本脚本把日志读成可量化指标，供 `ci_eval` 进程内调用。

设计约定（与 ci_eval 一致）：
  · 零依赖、可复现：只读数，不调 LLM、不改索引。
  · **有数据才评**：日志缺失或兜底行数 < `最小行数`（默认 10）时返回 None，
    ci_eval 据此跳过兜底闸门，绝不拿「没测过」当失败 —— 没有真跑过就不存在回归。
  · 阈值写在 `门槛.json` 的 `兜底` 段（沉淀成功率默认 ≥ 0.7，触发率默认 = 1.0）。

指标：
  · 触发率      = 触发兜底数 / 总行数（库外意图集应 100% 触发，漏触发=误判库内）
  · 沉淀成功率  = 成功沉淀数 / 触发兜底数（生成块过 体检+冒烟 且 组合成功）
  · 语义正确率  = 语义正确数 / 触发兜底数（仅对带 期望 的意图）
  · 分类拆解    = 各 分类 下的触发/沉淀明细（定位哪类意图最容易失败）

用法：
  python 积木库/评估/兜底跑分.py                 # 读默认 运行日志.jsonl
  python 积木库/评估/兜底跑分.py --日志 运行日志_v8_wnFyfF_15of20.jsonl
  python 积木库/评估/兜底跑分.py --最小行数 5 --阈值 0.6
"""

import argparse
import json
import os

_HERE = os.path.abspath(os.path.dirname(__file__))
_默认日志 = os.path.join(_HERE, '运行日志.jsonl')
_最小行数 = 10  # 不足这个数量的兜底记录视为「未真跑过」，闸门跳过


def 量(日志路径=_默认日志, 最小行数=_最小行数):
    """读取兜底运行日志，返回指标 dict；数据不足时返回 None（请跳过闸门）。"""
    if not os.path.isfile(日志路径):
        return None
    rows = []
    with open(日志路径, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    if not rows:
        return None
    触发 = [r for r in rows if r.get('是兜底')]
    if len(触发) < 最小行数:
        # 没真跑过足够样本 → 不评，避免拿 1 行局部失败当整体回归
        return None

    沉淀 = [r for r in 触发 if r.get('成功沉淀')]
    语义 = [r for r in 触发 if r.get('语义正确')]
    有期望 = [r for r in 触发 if r.get('期望')]
    分类 = {}
    for r in 触发:
        c = r.get('分类') or '未知'
        d = 分类.setdefault(c, {'触发': 0, '沉淀': 0})
        d['触发'] += 1
        if r.get('成功沉淀'):
            d['沉淀'] += 1
    return {
        '总条数': len(rows),
        '触发兜底数': len(触发),
        '触发率': round(len(触发) / len(rows), 4),
        '成功沉淀数': len(沉淀),
        '沉淀成功率': round(len(沉淀) / len(触发), 4),
        '语义正确数': len(语义),
        '语义正确率': (round(len(语义) / len(有期望), 4) if 有期望 else None),
        '有期望数': len(有期望),
        '平均token成本': _均token(触发),
        '分类拆解': 分类,
    }


def _均token(触发行):
    xs = []
    for r in 触发行:
        u = r.get('token成本')
        if isinstance(u, dict):
            n = u.get('total_tokens') or (u.get('prompt_tokens', 0) + u.get('completion_tokens', 0))
            if n:
                xs.append(n)
        elif isinstance(u, (int, float)):
            xs.append(u)
    return round(sum(xs) / len(xs), 1) if xs else None


def _打印(指标, 阈值=0.7):
    if 指标 is None:
        print('（兜底跑分跳过：日志缺失或兜底样本不足 %d 条，视为未真跑过）' % _最小行数)
        return
    print('\n══ 兜底闭环跑分 ══')
    print('  总条数 %d ｜ 触发兜底 %d ｜ 触发率 %.2f'
          % (指标['总条数'], 指标['触发兜底数'], 指标['触发率']))
    print('  成功沉淀 %d ｜ 沉淀成功率 %.2f（门槛 ≥ %.2f）%s'
          % (指标['成功沉淀数'], 指标['沉淀成功率'], 阈值,
             '✓' if 指标['沉淀成功率'] >= 阈值 - 1e-9 else '✗'))
    if 指标['语义正确率'] is not None:
        print('  语义正确率 %.2f（%d/%d 带期望）'
              % (指标['语义正确率'], 指标['语义正确数'], 指标['有期望数']))
    if 指标['平均token成本'] is not None:
        print('  平均 token 成本 %s/条' % 指标['平均token成本'])
    print('  分类拆解：')
    for c, d in 指标['分类拆解'].items():
        rate = (d['沉淀'] / d['触发']) if d['触发'] else 0
        print('    %-10s 触发 %d / 沉淀 %d（%.0f%%）' % (c, d['触发'], d['沉淀'], rate * 100))


def _cli():
    ap = argparse.ArgumentParser(description='兜底闭环跑分（读 运行日志.jsonl）')
    ap.add_argument('--日志', default=_默认日志, help='运行日志路径')
    ap.add_argument('--最小行数', type=int, default=_最小行数, help='触发兜底少于此数则跳过闸门')
    ap.add_argument('--阈值', type=float, default=0.7, help='沉淀成功率门槛')
    a = ap.parse_args()
    _打印(量(a.日志, a.最小行数), a.阈值)


if __name__ == '__main__':
    _cli()
