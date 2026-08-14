# -*- coding: utf-8 -*-
"""段言积木选块器 v0 —— 本地关键词匹配（**零 token，不外接任何大模型**）。

移植自 jikuai tools/ai-bridge/select.py。把 AI 的职责从「生成几百行代码」
降级为「从索引里选块」。本文件实现「选块」这一步的本地下位替代：用字符
重叠打分代替语义理解。够用来把整条组合链路跑通；同义改写留待 v0.13。

用法::
    python 积木库/选块.py "对一批数字求和"
    python 积木库/选块.py "农历" --top 3
"""

import argparse
import json
import os

_HERE = os.path.abspath(os.path.dirname(__file__))

#: 块名完整出现在需求文本里的加分。最强信号。
_权重_块名 = 8.0
#: 领域词出现在需求里的加分。中等信号。
_权重_领域 = 3.0
#: 描述里每个命中字符的加分。弱信号，仅用于同分排序。
_权重_描述字 = 0.3


def index_path():
    """`积木库/索引.json` 的绝对路径。"""
    return os.path.join(_HERE, '索引.json')


def load_index(path=None):
    """读块索引，返回解析后的字典。"""
    target = path or index_path()
    with open(target, 'r', encoding='utf-8') as f:
        return json.load(f)


def _切字(text):
    """切出有意义的字符：保留中日韩汉字与字母数字，丢标点空白。"""
    return [c for c in text
            if ('\u4e00' <= c <= '\u9fff') or c.isalnum()]


def _领域列表(block):
    d = block.get('领域') or []
    return [d] if isinstance(d, str) else list(d)


def _打分(query, query_chars, block):
    """给一个块打分。分数无绝对含义，只用于同一次查询内部排序。"""
    name = block.get('名称', '')
    desc = block.get('描述', '')
    domains = _领域列表(block)

    干草堆 = set(_切字(name + desc + ''.join(domains)))
    score = float(len(set(query_chars) & 干草堆))

    if name and name in query:
        score += _权重_块名
    for d in domains:
        if d and d in query:
            score += _权重_领域

    描述字 = set(_切字(desc))
    score += sum(1 for c in query_chars if c in 描述字) * _权重_描述字
    return score


def select_blocks(需求文本, index, top=None):
    """按关键词重叠给索引里的块打分，返回候选列表。

    返回项形如::
        {'名称': '求和', '领域': '数据', '导出名': '汇总',
         '路径': '数据/求和.duan', '描述': '...', '分数': 11.9}

    排序：分数降序；同分按名称升序（输出确定，便于测试）。
    分数 ≤ 0 的块直接丢弃。
    """
    query_chars = _切字(需求文本)
    候选 = []
    for block in index.get('块') or []:
        score = _打分(需求文本, query_chars, block)
        if score <= 0:
            continue
        候选.append({
            '名称': block['名称'],
            '领域': _领域列表(block)[0] if _领域列表(block) else '?',
            '导出名': block.get('导出名', '?'),
            '路径': block.get('路径', ''),
            '描述': block.get('描述', ''),
            '分数': round(score, 2),
        })
    候选.sort(key=lambda c: (-c['分数'], c['名称']))
    return 候选[:top] if top is not None else 候选


def _cli(argv=None):
    p = argparse.ArgumentParser(
        description='段言积木选块器 v0（本地关键词匹配，零 token）')
    p.add_argument('需求', help='自然语言需求文本')
    p.add_argument('--top', type=int, default=5, help='候选数上限（默认 5）')
    args = p.parse_args(argv)

    index = load_index()
    print(json.dumps({
        '需求': args.需求,
        '块总数': len(index.get('块') or []),
        '候选': select_blocks(args.需求, index, top=args.top),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
