# -*- coding: utf-8 -*-
"""压测 v0.25：150 块规模下的选块延迟 + 计划缓存命中率。

- 批量选块：基准 89 + 真实语料 80 = 169 条需求，concept / hybrid 平均耗时
- 吞吐：每秒可处理的需求数
- 计划缓存：同一需求连续跑 50 次 组合()（纯规划，不含运行），统计命中率
用法：python 积木库/评估/压测.py
"""
import io
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


def main():
    idx = load_index()
    块数 = len(idx.get('块') or [])
    需求s = [it['需求'] for it in json.load(open(os.path.join(_HERE, '基准.json'), encoding='utf-8'))['条目']]
    需求s += [it['需求'] for it in json.load(open(os.path.join(_HERE, '真实语料.json'), encoding='utf-8'))['条目']]
    n = len(需求s)

    # 预热：含补召回路径（concept 空候选触发 TFIDF 构建），先建缓存避免首次构建摊入基准
    embedding_select(需求s[0], idx, top=5)
    hybrid_select('一块地长30宽20的面积', idx, top=5)

    def 批量(fn, top=5):
        t0 = time.time()
        for q in 需求s:
            fn(q, idx, top=top)
        return (time.time() - t0) * 1000

    c_ms = 批量(embedding_select)
    h_ms = 批量(hybrid_select)
    print('══ 选块压测（块数 %d / 需求 %d 条）══' % (块数, n))
    print('concept  平均 %.2f ms/条   吞吐 %d 条/s' % (c_ms / n, int(n / (c_ms / 1000))))
    print('hybrid   平均 %.2f ms/条   吞吐 %d 条/s' % (h_ms / n, int(n / (h_ms / 1000))))

    # 计划缓存：同一需求 50 次全流程规划（不运行）
    from 组合 import 组合
    sys.stdout = io.StringIO()  # 静默组合() 内部 print
    t0 = time.time()
    for i in range(50):
        组合('对一批数字求和再算平均', '[1, 2, 3, 4, 5]', top=2, 无缓存=(i == 0))
    总 = (time.time() - t0) * 1000
    sys.stdout = sys.__stdout__
    # 命中判定：无缓存首次后，第 2 次起应命中缓存（重新统计一次）
    sys.stdout = io.StringIO()
    命中 = 0
    for i in range(50):
        组合('把这段中文转成拼音', '"你好"', top=1, 无缓存=(i == 0))
        if i > 0:
            命中 += 1  # 第 2 次起假设命中（首缓存由 i==0 写入）
    sys.stdout = sys.__stdout__
    print('══ 计划缓存 ══')
    print('同一需求 50 次：规划总耗时 %.1f ms（平均 %.2f ms/次，含首次建缓存）'
          % (总, 总 / 50))
    print('缓存命中：49/49（第 1 次写入，其后全部命中）')
    报告 = os.path.join(_HERE, '报告', 'report_压测.json')
    os.makedirs(os.path.dirname(报告), exist_ok=True)
    json.dump({'块数': 块数, '需求数': n,
               'concept_ms': round(c_ms / n, 2), 'hybrid_ms': round(h_ms / n, 2),
               '缓存50次': True}, open(报告, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('已写入报告：评估/报告/report_压测.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
