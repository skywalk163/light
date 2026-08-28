import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

block_results = data['逐块']

# 统计失败类型
error_types = Counter()
missing_cb = []
parse_errs = []

for path, result in block_results.items():
    if result.get('status') == 'failed':
        err = result.get('error_msg', '')
        if 'missing' in err and 'cb_' in err:
            missing_cb.append(path)
            error_types['missing_cb_追加'] += 1
        elif 'ParseError' in err:
            parse_errs.append(path)
            error_types['ParseError'] += 1
        elif 'TypeError' in err:
            error_types['TypeError'] += 1
        elif 'NameError' in err:
            error_types['NameError'] += 1
        elif 'ValueError' in err:
            error_types['ValueError'] += 1
        elif 'AttributeError' in err:
            error_types['AttributeError'] += 1
        elif 'SyntaxError' in err:
            error_types['SyntaxError'] += 1
        elif 'LexerError' in err:
            error_types['LexerError'] += 1
        else:
            error_types[err[:50]] += 1

print('=== 错误类型统计 ===')
for err_type, count in error_types.most_common(20):
    print(f'  {err_type}: {count}')

print(f'\n=== missing cb_追加 示例 (前5个) ===')
for p in missing_cb[:5]:
    print(f'  {p}')
    
print(f'\n=== ParseError 示例 (前5个) ===')
for p in parse_errs[:5]:
    r = block_results[p]
    print(f'  {p}')
    err_msg = str(r.get('error_msg', ''))
    print(f'    error: {err_msg[:80]}')

print(f'\n=== 总计 ===')
print(f'  失败总数: {sum(error_types.values())}')
print(f'  missing cb_追加: {len(missing_cb)}')
print(f'  ParseError: {len(parse_errs)}')