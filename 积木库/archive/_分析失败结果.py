import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blocks = data['逐块']
fails = [(path, info) for path, info in blocks.items() if info['status'] == 'failed']
print(f'总失败数: {len(fails)}')
print()

# 按错误类型分组
err_types = Counter()
for path, info in fails:
    err_type = info.get('error_type', '未知')
    err_types[err_type] += 1
print('错误类型分布:')
for et, cnt in err_types.most_common():
    print(f'  {et}: {cnt}')
print()

# 按领域分组
domain_fails = Counter()
for path, info in fails:
    domain = path.replace('\\', '/').split('/')[0]
    domain_fails[domain] += 1
print('按领域失败数:')
for d, cnt in domain_fails.most_common():
    print(f'  {d}: {cnt}')
print()

# 显示所有失败详情
print(f'=== 所有失败详情 ===')
for i, (path, info) in enumerate(fails, start=1):
    msg = info.get('error_msg', '?')
    err_type = info.get('error_type', '?')
    short_msg = str(msg)[:120]
    print(f'{i}. [{err_type}] {path}')
    if short_msg:
        print(f'   {short_msg}')