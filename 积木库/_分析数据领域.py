# -*- coding: utf-8 -*-
"""分析失败详情"""
import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blocks = data['逐块']

# 查找失败条目
fails = [(p, i) for p, i in blocks.items() if isinstance(i, dict) and i.get('status') == 'failed']
print('失败总数:', len(fails))

# 按领域分组
domain_fails = Counter()
for p, i in fails:
    parts = p.replace('\\', '/').split('/')
    domain = parts[0] if len(parts) > 1 else 'unknown'
    domain_fails[domain] += 1

print('\n各领域失败数:')
for d, c in domain_fails.most_common():
    print('  %s: %d' % (d, c))

# 错误类型分布 - 使用error_msg字段
error_types = Counter()
for p, i in fails:
    err = i.get('error_msg', i.get('error', '未知'))
    # 对于TypeError等，取前100字符
    short_err = str(err)[:100]
    error_types[short_err] += 1

print('\n详细错误类型分布(前20):')
for err, cnt in error_types.most_common(20):
    print('  [%d] %s' % (cnt, err))

# 数据领域前20个失败详情
print('\n数据领域失败详情(前20):')
data_fails = [(p, i) for p, i in fails if p.replace('\\', '/').split('/')[0] == '数据']
for p, i in data_fails[:20]:
    err = i.get('error_msg', i.get('error', ''))
    print('  %s: %s' % (p, str(err)[:120]))

# 格式领域前20个失败详情
print('\n格式领域失败详情(前20):')
fmt_fails = [(p, i) for p, i in fails if p.replace('\\', '/').split('/')[0] == '格式']
for p, i in fmt_fails[:20]:
    err = i.get('error_msg', i.get('error', ''))
    print('  %s: %s' % (p, str(err)[:120]))

# 类型领域前20个失败详情
print('\n类型领域失败详情(前20):')
type_fails = [(p, i) for p, i in fails if p.replace('\\', '/').split('/')[0] == '类型']
for p, i in type_fails[:20]:
    err = i.get('error_msg', i.get('error', ''))
    print('  %s: %s' % (p, str(err)[:120]))