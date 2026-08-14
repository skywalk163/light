# -*- coding: utf-8 -*-
"""扰动跑分 v0.21：基准外泛化评测。

基准.json 的措辞和概念词典同源，跑到 1.0 只能证明「没退化」，证明不了泛化。
扰动集.json 用迂回、口语、场景化说法描述同一能力，刻意避开块名用字——
这里掉下来的分才是选块器真实的能力边界。

同时对比三种选块器，看混合重排到底救回了什么：
  concept  概念图（现役默认）
  hybrid   概念图召回 + 并列群内语义重排
  tfidf    纯 TF-IDF 语义
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
from 语义选块 import semantic_select  # noqa: E402
from 混合选块 import hybrid_select  # noqa: E402


def 载入(path=None):
    p = path or os.path.join(_HERE, '扰动集.json')
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    return d['条目'], d.get('版本', '?')


选块器 = {
    'concept': lambda q, idx: embedding_select(q, idx, top=5),
    'hybrid': lambda q, idx: hybrid_select(q, idx, top=5),
    'tfidf': lambda q, idx: semantic_select(q, idx, top=5),
}

# 真·句向量（需 sentence_transformers + 已缓存模型）：DUAN_EVAL_REAL=1 时加测
if os.environ.get('DUAN_EVAL_REAL') == '1':
    选块器['real'] = lambda q, idx: embedding_select(q, idx, top=5, real=True)


def 评一个(名, fn, 条目, idx):
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
    n = len(条目)
    return {
        '选块器': 名, 'Hit@1': round(命中1 / n, 4), 'Hit@3': round(命中3 / n, 4),
        'MRR': round(mrr / n, 4), '空候选': len(空), '空编号': 空,
        '耗时ms': round((time.time() - t0) * 1000 / n, 2), '错例': 错,
    }


def main(argv=None):
    条目, 版本 = 载入()
    idx = load_index()
    print('══ 扰动集泛化评测 %s ══' % 版本)
    print('条目 %d 条 / 库内可见块 %d 个\n'
          % (len(条目), len([b for b in idx['块'] if b.get('选块可见', True)])))

    结果 = [评一个(k, v, 条目, idx) for k, v in 选块器.items()]
    print('%-9s %-8s %-8s %-8s %-8s %s' % ('选块器', 'Hit@1', 'Hit@3', 'MRR', '空候选', '平均耗时'))
    for r in 结果:
        print('%-9s %-8s %-8s %-8s %-8s %sms'
              % (r['选块器'], r['Hit@1'], r['Hit@3'], r['MRR'], r['空候选'], r['耗时ms']))

    主 = [r for r in 结果 if r['选块器'] == 'concept'][0]
    混 = [r for r in 结果 if r['选块器'] == 'hybrid'][0]
    print('\n── 概念图空候选（%d 条：措辞未命中任何库内概念 → 会走兜底）──' % 主['空候选'])
    编号表 = {it['编号']: it for it in 条目}
    for e in 主['空编号']:
        print('  %s %s  期望=%s' % (e, 编号表[e]['需求'], 编号表[e]['期望块']))
    print('\n── 概念图错例（%d 条）──' % len(主['错例']))
    for e, q, got, exp in 主['错例']:
        print('  %s %-24s 期望=%-8s 实得=%s' % (e, q, exp, got))

    差 = set(x[0] for x in 主['错例']) - set(x[0] for x in 混['错例'])
    退 = set(x[0] for x in 混['错例']) - set(x[0] for x in 主['错例'])
    print('\n── 混合重排相对概念图 ──')
    print('  救回：%s' % (sorted(差) or '无'))
    print('  拖坏：%s' % (sorted(退) or '无'))

    报告 = os.path.join(_HERE, '报告')
    os.makedirs(报告, exist_ok=True)
    with open(os.path.join(报告, 'report_扰动.json'), 'w', encoding='utf-8') as f:
        json.dump({'版本': 版本, '结果': 结果}, f, ensure_ascii=False, indent=2)
    print('\n已写入报告：评估/报告/report_扰动.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
