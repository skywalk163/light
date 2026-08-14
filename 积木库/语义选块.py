# -*- coding: utf-8 -*-
"""段言积木『语义选块』v0.13 —— 本地 TF-IDF + 同义词 + 领域先验（零 token）。

移植并升级 jikuai 的 v0.13 检索思路（bench_retrieval.py 里的 Retriever 在
vector_index=None 时退化为 TF-IDF + 同义词 + 领域先验）。不依赖任何大模型，
也不依赖 numpy——纯 Python 实现，随时可跑。

若运行环境装了 sentence-transformers 与 text2vec-base-chinese，会自动升级为
真·向量检索（仍零 token，仅本地推理）；否则走 TF-IDF 启发式。两种路径都
**不产生任何 AI token**。

用法：
    python 积木库/语义选块.py "计算平均工资" --top 3
    python 积木库/语义选块.py "把金额写成大写" --top 3
"""

import argparse
import json
import math
import os

_HERE = os.path.abspath(os.path.dirname(__file__))


def index_path():
    """`积木库/索引.json` 的绝对路径。"""
    return os.path.join(_HERE, '索引.json')


def load_index(path=None):
    """读块索引，返回解析后的字典。"""
    target = path or index_path()
    with open(target, 'r', encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 中文分词：字符 unigram + bigram + 英文/数字整词
# ---------------------------------------------------------------------------
def _切词(text):
    text = ''.join(c for c in text
                   if ('\u4e00' <= c <= '\u9fff') or c.isalnum() or c == ' ')
    toks = []
    prev = ''
    for c in text:
        if c == ' ':
            prev = ''
            continue
        toks.append(c)                 # unigram
        if prev:
            toks.append(prev + c)      # bigram
        prev = c
    for w in text.split():
        if len(w) > 1 and not any('\u4e00' <= ch <= '\u9fff' for ch in w):
            toks.append(w.lower())
    return toks


# ---------------------------------------------------------------------------
# 同义词扩展表（v0.13 的核心增量，弥补纯字符重叠的同义改写盲区）
# 键=规范块名；值=用户可能说的同义/口语表达
# ---------------------------------------------------------------------------
_同义词 = {
    '求和': ['加总', '累加', '合计', '总和', '加和', '求和'],
    '均值': ['平均', '平均值', '平均数', '算平均', '求平均'],
    '最大': ['极大', '最大值', '最高', '最大'],
    '最小': ['极小', '最小值', '最低', '最小'],
    '计数': ['个数', '数量', '多少条', '长度', '计数'],
    '个税': ['所得税', '缴纳税', '速算', '个税', '税'],
    '保留分': ['四舍五入到分', '保留两位小数', '保留两位', '四舍五入', '取整到分'],
    '分页参数': ['分页', '翻页', 'offset', '每页', '页码'],
    '去空格': ['去空白', 'trim', '去掉空格', '清理首尾空格'],
    '转小写': ['小写', '转小写', '小写化', 'tolower'],
    '转大写': ['大写', '转大写', '大写化', 'toupper'],
    '反转文本': ['反转', '倒序', '逆序', '翻转字符串', '反转字符串'],
    '替换文本': ['替换', '取代', '字符串替换', '把换成'],
    '文本长度': ['长度', '字符数', '字数', '字符串长度'],
    '拼接文本': ['拼接', '连接', 'join', '合并文本', '串接'],
    '提取数字': ['抽数字', '取数字', '数字提取', '抽取数值', '识别数字'],
    '包含': ['包含', '含有', '是否包含', '有吗'],
    '切分文本': ['切分', '分割', 'split', '按分开', '拆分'],
    '数字转中文': ['数字转中文', '阿拉伯数字转中文', '念出来', '读成中文'],
    '中文转数字': ['中文转数字', '中文转阿拉伯', '解析中文数'],
    '人民币大写': ['人民币大写', '金额大写', '大写金额', '写成大写', '中文大写'],
    '生成范围': ['范围', 'range', '从到步', '生成数列', '区间'],
    '排序列表': ['排序', '排列', 'sort', '有序', '从小到大'],
    '取唯一': ['去重', '唯一', 'unique', '不重复', '去重复'],
    '取偶数': ['偶数', '双数', '筛选偶数'],
    '取奇数': ['奇数', '单数', '筛选奇数'],
    '取余数': ['取余', '求余', '余数', 'mod', '取模'],
    '求幂': ['幂', '次方', 'pow', '指数', '乘方'],
    '拼接列表': ['合并列表', '连接列表', '列表拼接', 'concat'],
    '取子列表': ['切片', '子列表', '截取', '取一段', 'slice'],
}


def _扩展同义词(tokens):
    """把命中同义别名的查询，反向扩展出规范词，提升召回。"""
    out = list(tokens)
    text = ''.join(tokens)
    for 规范, 别名 in _同义词.items():
        for a in 别名:
            if a in text:
                out.append(规范)
                break
    return out


# ---------------------------------------------------------------------------
# TF-IDF（纯 Python，无 numpy）
# ---------------------------------------------------------------------------
class _TFIDF:
    def __init__(self, docs):
        self.df = {}
        for toks in docs:
            for t in set(toks):
                self.df[t] = self.df.get(t, 0) + 1
        self.N = len(docs) or 1

    def 向量(self, toks):
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        vec = {}
        for t, c in tf.items():
            idf = math.log((self.N + 1) / (self.df.get(t, 0) + 1)) + 1
            vec[t] = c * idf
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1
        return {t: v / norm for t, v in vec.items()}


def _余弦(a, b):
    return sum(a[t] * b[t] for t in (set(a) & set(b)))


# ---------------------------------------------------------------------------
# 可选升级：真·向量检索（环境装了 sentence-transformers 才启用）
# ---------------------------------------------------------------------------
def _真向量检索可用():
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:
        return False


class _向量检索:
    def __init__(self, blocks):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('shibing624/text2vec-base-chinese')
        self.blocks = blocks
        self.embs = self.model.encode(
            [self._文本(b) for b in blocks], normalize_embeddings=True)

    @staticmethod
    def _文本(b):
        d = b.get('领域') or []
        if isinstance(d, str):
            d = [d]
        return (b.get('名称', '') + ' ' + ' '.join(d) + ' ' + b.get('描述', ''))

    def 检索(self, 需求, top):
        import numpy as np
        q = self.model.encode([需求], normalize_embeddings=True)[0]
        sims = self.embs @ q
        order = sorted(range(len(self.blocks)), key=lambda i: -sims[i])[:top]
        return [(float(sims[i]), self.blocks[i]) for i in order]


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
# v0.25：TF-IDF 模型按库对象缓存（见 semantic_select），避免补召回场景每次全量重建。
_tfidf缓存 = {}
_TFIDF缓存上限 = 4


def _to_candidate(b, score):
    d = b.get('领域') or []
    if isinstance(d, list):
        d0 = d[0] if d else '?'
    else:
        d0 = d or '?'
    return {
        '名称': b.get('名称'),
        '领域': d0,
        '导出名': b.get('导出名', '?'),
        '路径': b.get('路径', ''),
        '描述': b.get('描述', ''),
        '分数': round(score, 4),
    }


def semantic_select(需求, index, top=None):
    """语义选块：返回候选字典列表（与 选块.select_blocks 同构，含 分数）。"""
    blocks = index.get('块') or []
    if not blocks:
        return []

    # 真·向量路径（零 token，仅本地推理）
    # v0.24：默认不自动启用真向量——Windows 批量调用 sentence_transformers 会硬崩，
    # 且基准显示真向量（0.823）反不如概念图（0.984）。与 embedding选块.py 约定对齐：
    # 仅 DUAN_EMBED_REAL=1 显式启用，默认走 TF-IDF（混合选块二级补召回依赖此默认）。
    if _真向量检索可用() and os.environ.get('DUAN_EMBED_REAL') == '1':
        try:
            retr = _向量检索(blocks)
            picked = retr.检索(需求, top or 5)
            return [_to_candidate(b, s) for s, b in picked]
        except Exception:
            pass  # 任何异常都降级到 TF-IDF

    # TF-IDF + 同义词 + 领域先验 启发式
    # v0.25：TF-IDF 模型按库对象缓存。此前每次调用都对全库重建（150 块切词+同义词
    # 扩展），补召回场景（concept 空候选）下动辄数秒——压测暴露：真实语料里 concept
    # 空候选触发补召回，单条 13s。库不变则模型不变，复用即可。
    def _领域(b):
        d = b.get('领域') or []
        return ' '.join(d) if isinstance(d, list) else str(d)

    key = id(blocks)
    if key not in _tfidf缓存:
        if len(_tfidf缓存) >= _TFIDF缓存上限:
            _tfidf缓存.clear()
        docs = []
        for b in blocks:
            text = b.get('名称', '') + ' ' + _领域(b) + ' ' + b.get('描述', '')
            toks = _切词(text)
            # 把同义词别名也加进文档，提升召回（文档侧扩展）
            blob = b.get('描述', '') + b.get('名称', '')
            for 规范, 别名 in _同义词.items():
                if any(a in blob for a in 别名):
                    toks.append(规范)
            docs.append(toks)
        _tfidf缓存[key] = (_TFIDF(docs), docs)
    tfidf, docs = _tfidf缓存[key]
    q_vec = tfidf.向量(_扩展同义词(_切词(需求)))

    候选 = []
    for b, vec in zip(blocks, (tfidf.向量(d) for d in docs)):
        score = _余弦(q_vec, vec)
        if score <= 0:
            continue
        候选.append(_to_candidate(b, score))
    候选.sort(key=lambda c: -c['分数'])
    return 候选[:top] if top else 候选


def _cli(argv=None):
    p = argparse.ArgumentParser(
        description='段言积木语义选块 v0.13（本地 TF-IDF+同义词，零 token）')
    p.add_argument('需求', help='自然语言需求文本')
    p.add_argument('--top', type=int, default=5, help='候选数上限')
    args = p.parse_args(argv)

    index = load_index()
    mode = '向量检索' if _真向量检索可用() else 'TF-IDF+同义词'
    候选 = semantic_select(args.需求, index, top=args.top)
    print(json.dumps({'需求': args.需求, '模式': mode,
                      '块总数': len(index.get('块') or []),
                      '候选': 候选}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
