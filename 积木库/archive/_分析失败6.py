# -*- coding: utf-8 -*-
"""分析cb_追加错误详情"""
import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blocks = data.get('逐块', {})

# 统计cb_追加错误
print('=== cb_追加 错误详情（前20个） ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if "cb_追加" in emsg:
            print(f'  {name}: {emsg.strip()[:150]}')
            count += 1
            if count >= 20:
                break

# 统计cb_追加错误的领域分布
print('\n=== cb_追加错误的领域分布 ===')
domain_counts = Counter()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if "cb_追加" in emsg:
            domain = name.split('\\')[0] if '\\' in name else name.split('/')[0]
            domain_counts[domain] += 1
for k, v in sorted(domain_counts.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')

# 统计所有错误（包括AttributeError前缀）
print('\n=== 完整错误统计 ===')
error_types = Counter()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if "ParseError" in emsg:
            error_types['ParseError'] += 1
        elif "TypeError" in emsg:
            error_types['TypeError'] += 1
        elif "NameError" in emsg:
            error_types['NameError'] += 1
        elif "AttributeError" in emsg:
            error_types['AttributeError'] += 1
        elif "RecursionError" in emsg:
            error_types['RecursionError'] += 1
        elif "UnboundLocalError" in emsg:
            error_types['UnboundLocalError'] += 1
        elif "SyntaxError" in emsg:
            error_types['SyntaxError'] += 1
        elif "IndexError" in emsg:
            error_types['IndexError'] += 1
        elif "ValueError" in emsg:
            error_types['ValueError'] += 1
        elif "KeyError" in emsg:
            error_types['KeyError'] += 1
        elif "ZeroDivisionError" in emsg:
            error_types['ZeroDivisionError'] += 1
        else:
            # 提取第一个错误类型
            first_line = emsg.strip().split('\n')[0]
            error_types[first_line[:80]] += 1
for k, v in sorted(error_types.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
print(f'总失败数: {sum(error_types.values())}')