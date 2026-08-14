# -*- coding: utf-8 -*-
"""真实跑分 v0.25：真实语料泛化评测（按调参段 / 留出段分段统计）。

真实语料.json 的措辞刻意口语化、场景化、避开块名用字。与扰动集不同：
  - 覆盖扩库后的 8 个新领域（集合/几何/统计/金融/Web/加解密/文件/日期）；
  - 显式标 段：调参（允许照此补概念词典别名）/ 留出（只测不调，对外数字）。

用法：python 积木库/评估/真实跑分.py
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.dirname(_HERE)
for p in (_LIB, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from embedding选块 import load_index, embedding_select  # noqa: E402
from 混合选块 import hybrid_select  # noqa: E402


def 载入():
    with open(os.path.join(_HERE, '真实语料.json'), encoding='utf-8') as f:
        return json.load(f)


选块器 = {
    'concept': lambda q, idx: embedding_select(q, idx, top=5),
    'hybrid': lambda q, idx: hybrid_select(q, idx, top=5),
}


def 评一段(名, fn, 条目, idx):
    命中1 = 命中3 = 0
    mrr = 0.0
    空 = []
    错 = []
    t0 = time.time()
    for it in 条目:
        c = fn(it['需求'], idx)
        名单 = [x['名称'] for x in c]
        期 = it['期望块']
        if not 名单:
            空.append(it['编号'])
            continue
        if 名单[0] == 期:
            命中1 += 1
        else:
            错.append((it['编号'], it['需求'], 名单[:3], 期))
        if 期 in 名单[:3]:
            命中3 += 1
        if 期 in 名单:
            mrr += 1.0 / (名单.index(期) + 1)
    n = len(条目) or 1
    return {'Hit@1': round(命中1 / n, 4), 'Hit@3': round(命中3 / n, 4),
            'MRR': round(mrr / n, 4), '空候选': len(空), '错例': 错}


def main():
    d = 载入()
    全部 = d['条目']
    调参 = [it for it in 全部 if it.get('段') == '调参']
    留出 = [it for it in 全部 if it.get('段') == '留出']
    idx = load_index()
    print('══ 真实语料泛化评测 %s ══' % d.get('版本'))
    print('共 %d 条（调参 %d / 留出 %d）  库内可见块 %d\n'
          % (len(全部), len(调参), len(留出),
             len([b for b in idx['块'] if b.get('选块可见', True)])))

    for 段名, 条目 in (('调参段', 调参), ('留出段', 留出), ('全部', 全部)):
        print('── %s（%d 条）──' % (段名, len(条目)))
        for 名, fn in 选块器.items():
            r = 评一段(名, fn, 条目, idx)
            print('  %-8s Hit@1=%-7s Hit@3=%-7s MRR=%-7s 空=%d 错=%d'
                  % (名, r['Hit@1'], r['Hit@3'], r['MRR'], r['空候选'], len(r['错例'])))
        print()

    # 留出段错例详情（对外泛化能力只看这里）
    留错 = 评一段('concept', 选块器['concept'], 留出, idx)['错例']
    print('── 留出段概念图错例（%d）──' % len(留错))
    编号表 = {it['编号']: it for it in 全部}
    for e, q, got, exp in 留错:
        print('  %s %-22s 期望=%-8s 实得=%s' % (e, q, exp, got))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
