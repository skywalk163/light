# -*- coding: utf-8 -*-
"""混合选块 v0.21：概念图召回 + 语义重排。

为什么不是「两个分数直接加权求和」
--------------------------------
概念图选块在 89 条基准上已经 Hit@1=1.0。任何全局融合都会把它已经答对的题
重新洗一遍牌——收益为零，风险为全部。跑分 v0.16 的教训已经写在
embedding选块.py 里：真·句向量做主检索时链路正确率从 0.984 掉到 0.823。

所以混合重排只做一件事：**在概念图自己分不清的地方，引入第二意见。**

  召回：概念图（保留「非通用领域概念交集」硬约束）
        → 库外需求依旧得到空候选，兜底通路完全不变
  判胶着：top1 与后续候选的概念分差 < δ（默认 0.03）才算「并列群」
        → 并列群 ≤ 1 个元素时直接原样返回，零额外开销
  重排：只对并列群内部按 融合分 = α×概念分 + (1-α)×语义分 重新排序
        → 群外候选保持概念图原序，绝不越过群边界

这样设计的结果是：概念图有把握时它说了算；没把握时（同类块概念集重合导致
余弦全 1.0，这是受控概念空间的固有特性）才让 TF-IDF 字面证据来打破平局。

重排分源
--------
默认 TF-IDF 字符 n-gram（复用 语义选块.py，零依赖、亚毫秒）。
装了 sentence_transformers 且 DUAN_EMBED_REAL=1 时改用真·句向量——
真向量在「宽召回后精排」这个位置才发挥得出来，做主检索反而有害。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from embedding选块 import (load_index, index_path, embedding_select,  # noqa: E402
                          可选块, 概念向量, _块概念向量, _余弦 as _概念余弦,
                          _通用领域)
from 语义选块 import (_TFIDF, _切词, _扩展同义词, _余弦 as _tfidf余弦,  # noqa: E402
                    semantic_select)

# 并列判定阈值：概念分与 top1 差距在此以内视为「分不清」
DELTA = float(os.environ.get('DUAN_HYBRID_DELTA', '0.03'))
# 融合权重：概念图占多少（其余给语义分）
ALPHA = float(os.environ.get('DUAN_HYBRID_ALPHA', '0.7'))
# 补召回候选的「待裁决分」：高于所有兜底阈值，好让流程走到校验器那一步
补召回分 = float(os.environ.get('DUAN_HYBRID_BACKFILL', '0.5'))


# ---------------------------------------------------------------------------
# 重排打分器
# ---------------------------------------------------------------------------
class _TFIDF重排:
    """字符 n-gram TF-IDF。IDF 在全库上拟合，罕见字更有区分力。"""

    名 = 'tfidf'

    def __init__(self, blocks):
        self.blocks = blocks
        docs = [_扩展同义词(_切词(self._文本(b))) for b in blocks]
        self.model = _TFIDF(docs)
        self.vecs = {b['名称']: self.model.向量(d) for b, d in zip(blocks, docs)}

    @staticmethod
    def _文本(b):
        d = b.get('领域') or []
        if isinstance(d, str):
            d = [d]
        return b.get('名称', '') + ' ' + ' '.join(d) + ' ' + b.get('描述', '')

    def 打分(self, 需求, 名称列表):
        q = self.model.向量(_扩展同义词(_切词(需求)))
        return {n: _tfidf余弦(q, self.vecs.get(n, {})) for n in 名称列表}


class _真向量重排:
    """句向量精排。只在小候选集上跑，避开「长描述 vs 短查询」的各向异性放大。"""

    名 = 'real'

    def __init__(self, blocks):
        from embedding选块 import _取模型, _块文本, _模型名
        self.model = _取模型(_模型名())
        self.blocks = {b['名称']: b for b in blocks}
        self._文本 = _块文本

    def 打分(self, 需求, 名称列表):
        import numpy as np
        块 = [self.blocks[n] for n in 名称列表 if n in self.blocks]
        if not 块:
            return {}
        embs = self.model.encode([self._文本(b) for b in 块],
                                 normalize_embeddings=True)
        q = self.model.encode([需求], normalize_embeddings=True)[0]
        sims = np.asarray(embs) @ q
        return {b['名称']: float(s) for b, s in zip(块, sims)}


_重排缓存 = {}


def _取重排器(index, real):
    key = (id(index), 'real' if real else 'tfidf')
    if key not in _重排缓存:
        blocks = 可选块(index.get('块') or [])
        if real:
            _重排缓存[key] = _真向量重排(blocks)
        else:
            _重排缓存[key] = _TFIDF重排(blocks)
    return _重排缓存[key]


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def 并列群(候选, delta=None):
    """返回与 top1 概念分差距在 delta 以内的候选下标（含 top1）。"""
    if not 候选:
        return []
    d = DELTA if delta is None else delta
    顶 = 候选[0]['分数']
    群 = [i for i, c in enumerate(候选) if 顶 - c['分数'] <= d]
    # 并列群必须是前缀（候选已按分降序），否则说明分数非单调，直接放弃重排
    return 群 if 群 == list(range(len(群))) else [0]


def hybrid_select(需求, index, top=None, alpha=None, delta=None, real=None,
                  补召回=True, 诊断=None):
    """混合选块：概念图召回（空则 TF-IDF 补召回）+ 并列群内语义重排。

    返回与 embedding_select 同构的候选列表。
    诊断 传入 dict 时会回填 {'并列数','重排','换序','补召回'} 便于评估。
    """
    # 1) 召回：完全沿用概念图（含库外硬约束），召回宽度放大以便重排有料可挑
    宽度 = max(top or 3, 8)
    候选 = embedding_select(需求, index, top=宽度, real=False)
    if 诊断 is not None:
        诊断.update({'并列数': 0, '重排': False, '换序': False, '补召回': False})

    # 1.5) 二级补召回：概念图给不出候选时，用字面证据兜一层
    #
    # 扰动集（评估/扰动跑分.py）揭穿了概念词典的真实边界：基准 89 条 Hit@1=1.0，
    # 换成迂回说法后只剩 0.375，其中 18/40 是「一个概念都没命中」的空候选——
    # 这些需求的能力明明在库里，却会被判成库外去走兜底，白白生成重复积木。
    # 空候选时放 TF-IDF 进来做宽召回，把「该不该用」的判断权交给校验器：
    # 校验器本来就是第二道闸，让它裁决比让概念词典沉默地判死刑更合理。
    if not 候选 and 补召回:
        备 = semantic_select(需求, index, top=max(top or 3, 3))
        备 = [c for c in 备 if c['名称'] in {b['名称'] for b in 可选块(index.get('块') or [])}]
        if not 备:
            return []
        for c in 备:
            # TF-IDF 分与概念余弦量纲不可比，硬塞进分数阈值只会误判。
            # 统一改写成「待裁决分」（高于所有兜底阈值），把关口让给校验器。
            c['语义分'] = c['分数']
            c['分数'] = 补召回分
            c['来源'] = '补召回'
        if 诊断 is not None:
            诊断.update({'补召回': True, '补召回数': len(备)})
        return 备[:top] if top else 备

    if len(候选) < 2:
        return 候选[:top] if top else 候选

    # 2) 判胶着
    群 = 并列群(候选, delta)
    if len(群) < 2:
        # 概念图有把握，不动它
        return 候选[:top] if top else 候选

    if real is None:
        real = os.environ.get('DUAN_EMBED_REAL') == '1'
    a = ALPHA if alpha is None else alpha

    # 3) 群内重排
    群候选 = [候选[i] for i in 群]
    名单 = [c['名称'] for c in 群候选]
    原序 = list(名单)
    try:
        重排器 = _取重排器(index, real)
        语义分 = 重排器.打分(需求, 名单)
    except Exception as e:
        print('[混合] 重排器不可用，保持概念图原序：%s' % e)
        return 候选[:top] if top else 候选

    # 语义分做群内 min-max 归一，避免不同打分器量纲差异污染融合
    vals = [语义分.get(n, 0.0) for n in 名单]
    lo, hi = min(vals), max(vals)
    跨度 = (hi - lo) or 1.0
    for c in 群候选:
        s = (语义分.get(c['名称'], 0.0) - lo) / 跨度
        c['概念分'] = c['分数']
        c['语义分'] = round(语义分.get(c['名称'], 0.0), 4)
        c['分数'] = round(a * c['概念分'] + (1 - a) * s, 4)
    群候选.sort(key=lambda c: -c['分数'])

    结果 = 群候选 + 候选[len(群):]
    if 诊断 is not None:
        诊断.update({'并列数': len(群), '重排': True,
                     '换序': [c['名称'] for c in 群候选] != 原序,
                     '打分器': 重排器.名})
    return 结果[:top] if top else 结果


def _cli(argv=None):
    p = argparse.ArgumentParser(description='段言积木混合选块 v0.21（概念图召回 + 语义重排）')
    p.add_argument('需求', help='自然语言需求文本')
    p.add_argument('--top', type=int, default=5)
    p.add_argument('--alpha', type=float, default=None, help='概念分权重（默认 0.7）')
    p.add_argument('--delta', type=float, default=None, help='并列判定阈值（默认 0.03）')
    p.add_argument('--real', action='store_true', help='用真·句向量做重排')
    args = p.parse_args(argv)

    index = load_index()
    诊 = {}
    候选 = hybrid_select(args.需求, index, top=args.top, alpha=args.alpha,
                       delta=args.delta, real=(True if args.real else None),
                       诊断=诊)
    print(json.dumps({'需求': args.需求, '诊断': 诊,
                      '候选': 候选 or '（空：需求未命中任何库内概念）'},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
