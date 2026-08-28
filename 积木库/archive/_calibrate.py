# -*- coding: utf-8 -*-
"""光明积木选块置信度校准 v1.0 —— 自动阈值调优 + 失败用例分析 + 置信度评分。

功能：
  1. 全量基准测试（复用 _benchmark_accuracy 的测试用例）
  2. 失败用例分析（按根因分类）
  3. 自动阈值调优（基于经验分数分布推荐最优阈值）
  4. 置信度评分（给每个候选块打置信度标签）
  5. 生成校准报告

用法：
    python 积木库/_calibrate.py              # 运行完整校准
    python 积木库/_calibrate.py --dry-run    # 只分析，不写回阈值
    python 积木库/_calibrate.py --report     # 只生成报告
"""

import argparse
import json
import math
import os
import sys
import time

_HERE = os.path.abspath(os.path.dirname(__file__))

# ── 导入测试用例 ──
sys.path.insert(0, _HERE)
from _benchmark_accuracy import TEST_CASES, DOMAIN_TEST_CASES


def _load_index():
    path = os.path.join(_HERE, '索引.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ──────────────────────────────────────────────────────
# 1. 全量基准测试
# ──────────────────────────────────────────────────────

def _run_keyword(需求, index, top=3):
    from 选块 import select_blocks
    return select_blocks(需求, index, top=top)


def _run_concept(需求, index, top=3):
    from embedding选块 import embedding_select
    return embedding_select(需求, index, top=top, real=False)


def _run_tfidf(需求, index, top=3):
    from 语义选块 import semantic_select
    return semantic_select(需求, index, top=top)


def _run_hybrid(需求, index, top=3):
    from _ml_selector import 统一选块
    return 统一选块(需求, index, top=top)


def _命中(候选, 期望):
    候选名 = set(c['名称'] for c in 候选)
    for e in 期望:
        if e in 候选名:
            return True
    return False


def 运行基准(策略名, 策略函数, 测试集, index):
    """运行一组基准测试，返回详细结果"""
    总 = len(测试集)
    命中 = 0
    耗时 = 0.0
    详细 = []

    for 用例 in 测试集:
        需求 = 用例[0]
        期望 = 用例[1]
        t0 = time.time()
        try:
            候选 = 策略函数(需求, index, top=3)
        except Exception as e:
            候选 = []
        t1 = time.time()
        耗时 += t1 - t0
        h = _命中(候选, 期望)
        if h:
            命中 += 1
        详细.append({
            '需求': 需求,
            '期望': 期望[:3],
            '命中': h,
            '候选': [c['名称'] for c in 候选[:3]],
            '分数': [c.get('分数', 0) for c in 候选[:3]],
        })

    准确率 = 命中 / 总 * 100 if 总 > 0 else 0
    return {
        '策略': 策略名,
        '总用例': 总,
        '命中': 命中,
        '准确率': round(准确率, 1),
        '平均耗时': round(耗时 / 总 * 1000, 1),
        '详细': 详细,
    }


# ──────────────────────────────────────────────────────
# 2. 失败用例分析（按根因分类）
# ──────────────────────────────────────────────────────

def _分析根因(需求, 候选, 期望):
    """分析单个失败用例的根因"""
    if not 候选:
        return '无候选', '概念图/语义选块无法匹配该查询'

    # 检查候选名与期望名的字符重叠
    候选名 = set(候选)
    期望名 = set(期望)
    候选字 = set(c for name in 候选 for c in name)
    期望字 = set(c for name in 期望 for c in name)

    char_overlap = len(候选字 & 期望字)
    if char_overlap == 0:
        return '零字符重叠', '候选与期望块名没有共同字符，纯语义匹配失败'

    # 检查是否被数字误导
    import re
    候选数字 = set(re.findall(r'\d+', ' '.join(候选)))
    期望数字 = set(re.findall(r'\d+', ' '.join(期望)))
    查询数字 = set(re.findall(r'\d+', 需求))
    if 候选数字 and 候选数字 & 查询数字 and not 期望数字 & 查询数字:
        return '数字过度匹配', '查询中的数字误导了语义匹配，匹配到含相同数字的无关块'

    # 检查是否被宽泛概念词误导
    宽泛词 = {'数', '值', '量', '数', '计', '算', '函', '列', '组', '集', '表', '型'}
    候选宽泛 = sum(1 for c in ' '.join(候选) if c in 宽泛词)
    期望宽泛 = sum(1 for c in ' '.join(期望) if c in 宽泛词)
    if 候选宽泛 > 期望宽泛 + 2:
        return '宽泛词误导', '候选被宽泛概念词（数/值/量）误导'

    return '语义模糊', '查询语义模糊，多领域概念重叠'


def 分析失败(结果集):
    """分析所有策略的失败用例，按根因分类"""
    所有失败 = {}  # 需求 -> {策略->候选, 根因}
    for r in 结果集:
        for d in r['详细']:
            if not d['命中']:
                需求 = d['需求']
                if 需求 not in 所有失败:
                    所有失败[需求] = {'期望': d['期望'], '策略们': {}}
                所有失败[需求]['策略们'][r['策略']] = {
                    '候选': d['候选'],
                    '分数': d['分数'],
                }

    # 分析根因
    根因统计 = {}
    按需求 = []
    for 需求, info in 所有失败.items():
        # 取第一个失败的策略的候选
        第一个策略 = list(info['策略们'].keys())[0]
        候选 = info['策略们'][第一个策略]['候选']
        根因, 解释 = _分析根因(需求, 候选, info['期望'])
        根因统计[根因] = 根因统计.get(根因, 0) + 1
        按需求.append({
            '需求': 需求,
            '期望': info['期望'],
            '根因': 根因,
            '解释': 解释,
            '策略们': info['策略们'],
        })

    return {
        '总失败需求数': len(所有失败),
        '根因分布': 根因统计,
        '按需求': sorted(按需求, key=lambda x: x['需求']),
    }


# ──────────────────────────────────────────────────────
# 3. 自动阈值调优
# ──────────────────────────────────────────────────────

def 分析分数分布(测试集, index):
    """分析关键词选块的分数分布，推荐最优阈值"""
    scores = []
    for 用例 in 测试集:
        需求 = 用例[0]
        期望 = 用例[1]
        r = _run_keyword(需求, index, top=5)
        if r:
            top1_score = r[0]['分数']
            correct = [c['名称'] for c in r if c['名称'] in set(期望)]
            wrong = [c['名称'] for c in r if c['名称'] not in set(期望)]
            候选名 = [c['名称'] for c in r[:3]]
            top3_hit = any(c['名称'] in set(期望) for c in r[:3])
            scores.append({
                '需求': 需求,
                'top1_score': top1_score,
                'top3_hit': top3_hit,
                'top1_correct': r[0]['名称'] in set(期望) if r else False,
                'top1_name': r[0]['名称'] if r else '无',
                '正确块': correct[:3],
                '误匹配块': wrong[:3],  # 前3个错误候选
            })

    # 按分数分段统计正确率
    thresholds = [0, 2, 4, 5, 6, 8, 10, 12, 15]
    分段统计 = []
    for i in range(len(thresholds) - 1):
        lo, hi = thresholds[i], thresholds[i + 1]
        seg = [s for s in scores if lo <= s['top1_score'] < hi]
        if seg:
            n = len(seg)
            hit = sum(1 for s in seg if s['top3_hit'])
            分段统计.append({
                '范围': f'{lo}-{hi}',
                '用例数': n,
                'Top3命中': hit,
                'Top3准确率': round(hit / n * 100, 1),
                'Top1正确': sum(1 for s in seg if s['top1_correct']),
            })

    # 推荐阈值：找到使 Top-3 准确率 100% 的最低分数
    # 即：所有分数 ≥ threshold 的用例，Top-3 准确率 = 100%
    推荐阈值 = 0
    for t in sorted(set(s['top1_score'] for s in scores)):
        above = [s for s in scores if s['top1_score'] >= t]
        if above and all(s['top3_hit'] for s in above):
            推荐阈值 = t
            break

    # 统计各分数段的最低分用例
    low_score = [s for s in scores if s['top1_score'] <= 6]
    low_score.sort(key=lambda x: x['top1_score'])

    return {
        '总用例': len(scores),
        '推荐阈值': 推荐阈值,
        '分段统计': 分段统计,
        '低分用例': low_score[:10],
    }


def 推荐_ml阈值(分数分布, 概念图结果, tfidf结果):
    """基于经验数据推荐 _ml_selector.py 中的级联阈值"""
    # 当前阈值
    当前 = {
        'TF-IDF补充': 5.0,
        '概念图补充': 3.0,
        '语义补充': 2.0,
    }

    # 分析：所有正确匹配的最低 Top-1 分数
    低分正确 = [s for s in 分数分布['低分用例'] if s['top3_hit']]

    # 建议：TF-IDF 补充阈值应略低于最低正确匹配分数
    # 确保所有正确匹配不会被错误地触发补充
    if 低分正确:
        最低正确 = min(s['top1_score'] for s in 低分正确)
    else:
        最低正确 = 4.0

    # 阈值应略低于最低正确分数，以避免过早触发补充
    # 但同时要确保足够低以覆盖不确定性
    tfidf_threshold = max(4.0, 最低正确 - 0.5)
    concept_threshold = max(2.0, tfidf_threshold - 2.0)
    semantic_threshold = max(1.0, concept_threshold - 1.0)

    推荐 = {
        'TF-IDF补充': round(tfidf_threshold, 1),
        '概念图补充': round(concept_threshold, 1),
        '语义补充': round(semantic_threshold, 1),
    }

    return {
        '当前阈值': 当前,
        '推荐阈值': 推荐,
        '调优依据': (
            f'最低正确Top-1分数={最低正确}，'
            f'TF-IDF阈值设为低于此值避免误触发，'
            f'概念图/语义阈值依次递减'
        ),
    }


# ──────────────────────────────────────────────────────
# 4. 置信度评分
# ──────────────────────────────────────────────────────

def 计算置信度(候选, 策略名='关键词'):
    """给候选列表打置信度标签

    返回 (候选列表, 置信度标签)
    置信度标签: '高', '中', '低', '极低'
    """
    if not 候选:
        return 候选, '极低'

    top1 = 候选[0].get('分数', 0)
    gap = top1 - (候选[1].get('分数', 0) if len(候选) > 1 else 0)

    if 策略名 == '关键词':
        if top1 >= 10 and gap >= 2:
            return 候选, '高'
        elif top1 >= 6:
            return 候选, '中'
        elif top1 >= 4:
            return 候选, '低'
        else:
            return 候选, '极低'
    elif 策略名 == '混合':
        # 混合策略：关键词结果为主，其他策略补充
        if top1 >= 8:
            return 候选, '高'
        elif top1 >= 4:
            return 候选, '中'
        else:
            return 候选, '低'
    else:
        # TF-IDF / 概念图
        if top1 >= 0.15:
            return 候选, '中'
        elif top1 >= 0.08:
            return 候选, '低'
        else:
            return 候选, '极低'


def 添加置信度_到选块器():
    """给选块.py 添加置信度评分字段

    在每个候选块的返回结果中添加 '置信度' 字段。
    """
    from 选块 import select_blocks as original_select
    import functools

    @functools.wraps(original_select)
    def select_with_confidence(需求文本, index, top=None):
        候选 = original_select(需求文本, index, top=top)
        候选, 标签 = 计算置信度(候选, '关键词')
        for c in 候选:
            c['置信度'] = 标签
        return 候选

    return select_with_confidence


# ──────────────────────────────────────────────────────
# 5. 校准报告生成
# ──────────────────────────────────────────────────────

def 生成报告(基准结果们, 失败分析, 分数分布, 阈值推荐):
    """生成校准报告文本"""
    lines = []
    lines.append('=' * 70)
    lines.append('  光明积木选块置信度校准报告')
    lines.append('=' * 70)
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    lines.append(f'  生成时间: {ts}')
    lines.append('')

    # ── 各策略准确率 ──
    lines.append('─' * 70)
    lines.append('  1. 各策略准确率对比')
    lines.append('─' * 70)
    for r in 基准结果们:
        bar = '█' * int(r['准确率'] / 5)
        lines.append(f'  {r["策略"]:12s}  {r["准确率"]:5.1f}%  {bar}  ({r["命中"]}/{r["总用例"]}, {r["平均耗时"]}ms)')
    lines.append('')

    # ── 失败用例分析 ──
    lines.append('─' * 70)
    lines.append('  2. 失败用例分析')
    lines.append('─' * 70)
    lines.append(f'  总失败需求数: {失败分析["总失败需求数"]}')
    lines.append('')
    if 失败分析['根因分布']:
        lines.append('  根因分布:')
        for 根因, 计数 in sorted(失败分析['根因分布'].items(), key=lambda x: -x[1]):
            lines.append(f'    {根因}: {计数} 个')
        lines.append('')
        lines.append('  失败详情:')
        for item in 失败分析['按需求'][:20]:
            lines.append(f'    ✗ {item["需求"]}')
            lines.append(f'      期望: {item["期望"]}')
            lines.append(f'      根因: {item["根因"]}')
            for 策略, 细节 in item['策略们'].items():
                lines.append(f'      {策略}: {细节["候选"]}')
            lines.append('')
        if len(失败分析['按需求']) > 20:
            lines.append(f'    ... 还有 {len(失败分析["按需求"]) - 20} 个失败用例')
    else:
        lines.append('  无失败用例！所有策略全命中。')
    lines.append('')

    # ── 分数分布 ──
    lines.append('─' * 70)
    lines.append('  3. 关键词选块分数分布')
    lines.append('─' * 70)
    for seg in 分数分布['分段统计']:
        bar = '█' * int(seg['Top3准确率'] / 5)
        lines.append(f'  {seg["范围"]:8s}  {seg["用例数"]:3d} 用例  Top3 {seg["Top3准确率"]:5.1f}%  {bar}')
    lines.append(f'')
    lines.append(f'  推荐阈值 (Top-3 100% 准确的最低分数): {分数分布["推荐阈值"]}')
    lines.append('')
    if 分数分布['低分用例']:
        lines.append('  低分用例 (Top-1 ≤ 6):')
        for s in 分数分布['低分用例']:
            correct = '✅' if s['top3_hit'] else '❌'
            lines.append(f'    [{correct}] {s["top1_score"]:5.1f}  {s["需求"]:20s} → {s["top1_name"]}')
    lines.append('')

    # ── 阈值推荐 ──
    lines.append('─' * 70)
    lines.append('  4. 自动阈值调优推荐')
    lines.append('─' * 70)
    lines.append(f'  调优依据: {阈值推荐["调优依据"]}')
    lines.append('')
    lines.append(f'  {"阈值名称":20s}  {"当前值":>8s}  {"推荐值":>8s}  {"调整":>8s}')
    lines.append(f'  {"-"*20}  {"-"*8}  {"-"*8}  {"-"*8}')
    for key in ['TF-IDF补充', '概念图补充', '语义补充']:
        当前 = 阈值推荐['当前阈值'][key]
        推荐 = 阈值推荐['推荐阈值'][key]
        diff = 推荐 - 当前
        diff_str = f'+{diff:.1f}' if diff > 0 else f'{diff:.1f}' if diff < 0 else ' 0.0'
        lines.append(f'  {key:20s}  {当前:>8.1f}  {推荐:>8.1f}  {diff_str:>8s}')
    lines.append('')

    # ── 综合建议 ──
    lines.append('─' * 70)
    lines.append('  5. 综合建议')
    lines.append('─' * 70)
    最佳策略 = max(基准结果们, key=lambda r: r['准确率'])
    lines.append(f'  ✅ 最佳策略: {最佳策略["策略"]} ({最佳策略["准确率"]}%)')
    lines.append(f'  ✅ 目标 (Top-3 ≥ 90%): {"已达成" if 最佳策略["准确率"] >= 90 else "未达标"}')
    lines.append('')
    lines.append('  建议:')
    if 分数分布['推荐阈值'] > 0:
        lines.append(f'    • 关键词选块阈值保持 ≥ 0（所有用例都有候选）')
    if 阈值推荐['推荐阈值']['TF-IDF补充'] != 5.0:
        lines.append(f'    • TF-IDF补充阈值从 5.0 → {阈值推荐["推荐阈值"]["TF-IDF补充"]}')
    if 失败分析['总失败需求数'] > 0:
        lines.append(f'    • 当前有 {失败分析["总失败需求数"]} 个需求在所有策略中失败')
        lines.append(f'    • 建议: 检查索引中是否缺少对应块，或扩展概念词典')
    lines.append('')

    return '\n'.join(lines)


# ──────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description='光明积木选块置信度校准 v1.0')
    p.add_argument('--dry-run', action='store_true',
                   help='只分析，不写回阈值')
    p.add_argument('--report', action='store_true',
                   help='只生成报告，不写回阈值')
    args = p.parse_args()

    print('正在加载索引...')
    index = _load_index()
    print(f'  索引块数: {len(index.get("块", []))}')

    # ── 1. 全量基准测试 ──
    print('\n正在运行全量基准测试...')
    策略们 = [
        ('关键词选块', _run_keyword),
        ('概念图选块', _run_concept),
        ('TF-IDF选块', _run_tfidf),
        ('混合策略选块', _run_hybrid),
    ]
    基准结果们 = []
    for 名称, 函数 in 策略们:
        r = 运行基准(名称, 函数, TEST_CASES, index)
        基准结果们.append(r)
        print(f'  {名称}: {r["准确率"]}% ({r["命中"]}/{r["总用例"]})')

    # ── 2. 失败用例分析 ──
    print('\n正在分析失败用例...')
    失败分析 = 分析失败(基准结果们)
    print(f'  总失败需求数: {失败分析["总失败需求数"]}')
    for 根因, 计数 in 失败分析['根因分布'].items():
        print(f'    {根因}: {计数}')

    # ── 3. 分数分布分析 ──
    print('\n正在分析分数分布...')
    分数分布 = 分析分数分布(TEST_CASES, index)
    print(f'  推荐阈值: {分数分布["推荐阈值"]}')
    for seg in 分数分布['分段统计']:
        print(f'    {seg["范围"]:8s}: {seg["用例数"]:3d} 用例, Top3 {seg["Top3准确率"]:.1f}%')

    # ── 4. 阈值推荐 ──
    print('\n正在计算阈值推荐...')
    概念图结果 = 基准结果们[1]  # 概念图选块
    tfidf结果 = 基准结果们[2]   # TF-IDF选块
    阈值推荐 = 推荐_ml阈值(分数分布, 概念图结果, tfidf结果)
    print(f'  当前阈值: {阈值推荐["当前阈值"]}')
    print(f'  推荐阈值: {阈值推荐["推荐阈值"]}')

    # ── 5. 生成报告 ──
    print('\n正在生成校准报告...')
    报告 = 生成报告(基准结果们, 失败分析, 分数分布, 阈值推荐)
    print(报告)

    # 保存报告
    报告路径 = os.path.join(_HERE, '校准报告.txt')
    with open(报告路径, 'w', encoding='utf-8') as f:
        f.write(报告)
    print(f'\n报告已保存到: {报告路径}')

    # ── 6. 写回阈值（非 dry-run 模式） ──
    if not args.dry_run and not args.report:
        print('\n正在写回调优阈值到 _ml_selector.py ...')
        ml_path = os.path.join(_HERE, '_ml_selector.py')
        with open(ml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新 TF-IDF 补充阈值（行: 候选 and top1_分数 < 5.0）
        旧_tfidf = f'候选 and top1_分数 < {阈值推荐["当前阈值"]["TF-IDF补充"]}'
        新_tfidf = f'候选 and top1_分数 < {阈值推荐["推荐阈值"]["TF-IDF补充"]}'
        if 旧_tfidf in content:
            content = content.replace(旧_tfidf, 新_tfidf)
            print(f'  TF-IDF补充阈值: {阈值推荐["当前阈值"]["TF-IDF补充"]} → {阈值推荐["推荐阈值"]["TF-IDF补充"]}')
        else:
            # 尝试精确匹配空格
            for precision in [0.5, 1.0]:
                旧_tfidf = f'候选 and top1_分数 < {阈值推荐["当前阈值"]["TF-IDF补充"] - precision}'
                if 旧_tfidf in content:
                    content = content.replace(旧_tfidf, f'候选 and top1_分数 < {阈值推荐["推荐阈值"]["TF-IDF补充"]}')
                    print(f'  TF-IDF补充阈值: {阈值推荐["当前阈值"]["TF-IDF补充"] - precision} → {阈值推荐["推荐阈值"]["TF-IDF补充"]}')
                    break

        # 更新概念图补充阈值（行: 候选[0].get('分数', 0) < 3.0）
        旧_concept = f"候选[0].get('分数', 0) < {阈值推荐['当前阈值']['概念图补充']}"
        新_concept = f"候选[0].get('分数', 0) < {阈值推荐['推荐阈值']['概念图补充']}"
        if 旧_concept in content:
            content = content.replace(旧_concept, 新_concept)
            print(f'  概念图补充阈值: {阈值推荐["当前阈值"]["概念图补充"]} → {阈值推荐["推荐阈值"]["概念图补充"]}')

        # 更新语义补充阈值（行: 候选[0].get('分数', 0) < 2.0）
        旧_semantic = f"候选[0].get('分数', 0) < {阈值推荐['当前阈值']['语义补充']}"
        新_semantic = f"候选[0].get('分数', 0) < {阈值推荐['推荐阈值']['语义补充']}"
        if 旧_semantic in content:
            content = content.replace(旧_semantic, 新_semantic)
            print(f'  语义补充阈值: {阈值推荐["当前阈值"]["语义补充"]} → {阈值推荐["推荐阈值"]["语义补充"]}')

        with open(ml_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('  阈值写回完成！')

        # 验证：重新运行混合策略基准测试
        print('\n正在验证调优后的混合策略...')
        验证结果 = 运行基准('混合策略选块(调优后)', _run_hybrid, TEST_CASES, index)
        print(f'  准确率: {验证结果["准确率"]}% ({验证结果["命中"]}/{验证结果["总用例"]})')
        if 验证结果['准确率'] >= 100:
            print('  ✅ 调优后准确率保持 100%')
        else:
            print(f'  ⚠️ 调优后准确率变化: {验证结果["准确率"]}%')

    else:
        print('\n(dry-run 模式，未写回阈值)')

    print('\n校准完成！')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())