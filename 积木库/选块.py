# -*- coding: utf-8 -*-
"""光明积木选块器 v0 —— 本地关键词匹配（**零 token，不外接任何大模型**）。

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

# v1 升级版打分策略：
#   1) 块名是查询的子串 → 最强信号 +10 + 长度奖励
#   2) 查询是块名的子串 → 次强信号 +8 + 短名奖励
#   3) 块名中每个字命中查询 → +2（含数字字母，用于精确匹配）
#   4) 领域命中 → +3
#   5) 描述字符重叠 → 极弱信号 +0.05（仅同分排序）
#   6) 查询尾字奖励 → 短名（≤3字）含尾字 +4，排除常见后缀

#: 块名在查询中完整出现的加分。最强信号。
_权重_块名_完整 = 10.0
#: 块名在查询中出现时，每字长度奖励（越长越精确）
_权重_块名_长度 = 0.5
#: 查询是块名子串时的加分（次强信号，如查询"求和"匹配"中文数求和"）
_权重_查询_子串 = 8.0
#: 查询是块名子串时，短名奖励
_权重_查询_子串_短名 = 0.3
#: 块名中每个字命中查询的加分（含数字字母）
_权重_块名字 = 2.0
#: 领域词出现在需求里的加分。中等信号。
_权重_领域 = 3.0
#: 查询末尾汉字出现在短名块名中的加分。受控信号。
_权重_查询_尾字 = 5.0
#: 描述里每个命中字符的加分。极弱信号，仅用于同分排序。
_权重_描述字 = 0.05
#: 尾字停用字集（常见后缀，不具语义区分度，不给尾字奖励）
_尾字_停用 = frozenset({'算', '法', '化', '性', '度', '率', '型', '式',
                     '器', '机', '体', '值', '数', '量', '表', '图', '本',
                     '符', '写', '换', '并'})


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
    """给一个块打分。分数无绝对含义，只用于同一次查询内部排序。

    v1 升级版：
    - 优先块名子串匹配，大幅降低字符重叠噪声
    - 领域匹配作为辅助信号
    """
    name = block.get('名称', '')
    desc = block.get('描述', '')
    domains = _领域列表(block)

    score = 0.0

    # 1) 块名是查询的子串（最强信号）
    #    例：查询"反转文本" → 块名"反转"是子串 → +10 + 2*0.5 = 11
    #    例：查询"计算标准差" → 块名"标准差"是子串 → +10 + 3*0.5 = 11.5
    if name and name in query:
        score += _权重_块名_完整 + len(name) * _权重_块名_长度

    # 2) 查询是块名的子串（次强信号）
    #    例：查询"求和" → 块名"中文数求和"包含"求和" → +8 + 短名奖励
    elif query in name:
        # 块名越短，匹配越精确（短名比长名更精确）
        score += _权重_查询_子串 + max(0, 10 - len(name)) * _权重_查询_子串_短名

    # 3) 块名中每个字命中查询 → 加分（含数字字母，用于精确匹配）
    if name:
        name_chars = set(_切字(name))
        match_count = sum(1 for c in name_chars if c in query_chars)
        score += match_count * _权重_块名字

    # 4) 领域匹配
    for d in domains:
        if d and d in query:
            score += _权重_领域

    # 5) 描述字符重叠（极弱信号，仅用于同分排序）
    描述字 = set(_切字(desc))
    score += sum(1 for c in query_chars if c in 描述字) * _权重_描述字

    # 6) 查询末尾汉字出现在短名块名中 → 受控加分
    #    中文语义中，关键信息常在末尾（如"计算1到100的和"的"和"）
    #    仅限短名（≤3汉字），排除常见后缀，且块名半数以上汉字匹配查询
    if name:
        query_cjk = [c for c in query_chars if '\u4e00' <= c <= '\u9fff']
        if query_cjk:
            tail_char = query_cjk[-1]
            if tail_char not in _尾字_停用:
                # 用 set 去重后计算汉字数（防"集合并集"等含重复字的块名长度误判）
                name_cjk = list({c for c in _切字(name) if '\u4e00' <= c <= '\u9fff'})
                if len(name_cjk) <= 3 and tail_char in name_cjk:
                    # 块名汉字匹配率 ≥ 50% 才给奖励（防"饱和度""中和热"误匹配）
                    cjk_match = sum(1 for c in name_cjk if c in query_cjk)
                    if cjk_match / max(1, len(name_cjk)) >= 0.5:
                        score += _权重_查询_尾字

    return score


def select_blocks(需求文本, index, top=None):
    """按关键词重叠给索引里的块打分，返回候选列表。

    返回项形如::
        {'名称': '求和', '领域': '数据', '导出名': '汇总',
         '路径': '数据/求和.light', '描述': '...', '分数': 11.9}

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
        description='光明积木选块器 v0（本地关键词匹配，零 token）')
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