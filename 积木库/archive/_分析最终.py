# -*- coding: utf-8 -*-
"""分析最新预跑结果"""
import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'总积木: {data.get("总积木")}')
print(f'通过: {data.get("通过")} ({data.get("通过率")})')
print(f'失败: {data.get("失败")}')
print(f'跳过: {data.get("跳过")}')

blocks = data.get('逐块', {})
error_types = Counter()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if 'ParseError' in emsg:
            error_types['ParseError'] += 1
        elif 'TypeError' in emsg:
            error_types['TypeError'] += 1
        elif 'NameError' in emsg:
            error_types['NameError'] += 1
        elif 'AttributeError' in emsg:
            error_types['AttributeError'] += 1
        else:
            first_line = emsg.strip().split('\n')[0][:60]
            error_types[first_line] += 1

print()
print('=== 错误类型统计 ===')
for k, v in sorted(error_types.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
print(f'总失败: {sum(error_types.values())}')

# 按领域
print('\n=== 按领域统计 ===')
domain_stats = Counter()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        domain = name.split('\\')[0] if '\\' in name else name.split('/')[0]
        domain_stats[domain] += 1
for k, v in sorted(domain_stats.items(), key=lambda x: -x[1])[:15]:
    print(f'  {k}: {v}')