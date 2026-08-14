# -*- coding: utf-8 -*-
"""分析预跑失败详情"""
import json, re
from collections import Counter

data = json.load(open('_预跑结果.json', encoding='utf-8'))
block_results = data.get('逐块', {})

failures = [(k, v.get('error_msg', '')) for k, v in block_results.items() 
            if v.get('status') == 'failed']

# 1. missing_required_arg
missing_args = [(k, err) for k, err in failures 
                if 'missing' in err and 'required positional argument' in err]

missing_param_counter = Counter()
for fp, err in missing_args:
    m = re.search(r"missing (\d+) required positional argument: '([^']+)'", err)
    if m:
        params_str = m.group(2)
        for p in params_str.split("', '"):
            missing_param_counter[p] += 1
    else:
        missing_param_counter[f'UNPARSED: {err[:80]}'] += 1

print('=== missing_required_arg 缺失参数统计 ===')
for p, c in missing_param_counter.most_common(30):
    print(f'  "{p}": {c}')
print(f'  总计: {len(missing_args)}')

print()

# 2. lambda arg mismatch - show the files
lambda_mismatch = [(k, err) for k, err in failures if 'takes' in err and 'positional argument' in err]
print(f'=== lambda arg mismatch: {len(lambda_mismatch)} ===')
for fp, err in lambda_mismatch[:20]:
    print(f'  {fp}: {err}')
if len(lambda_mismatch) > 20:
    print(f'  ... and {len(lambda_mismatch) - 20} more')

print()

# 3. int not callable
int_not_callable = [(k, err) for k, err in failures if "int' object is not callable" in err]
print(f"=== 'int' object is not callable: {len(int_not_callable)} ===")
for fp, err in int_not_callable[:20]:
    print(f'  {fp}')
if len(int_not_callable) > 20:
    print(f'  ... and {len(int_not_callable) - 20} more')

print()

# 4. attribute_error
attr_err = [(k, err) for k, err in failures if err.startswith("'") and "has no attribute" in err]
print(f"=== AttributeError: {len(attr_err)} ===")
for fp, err in attr_err[:20]:
    print(f'  {fp}: {err}')
if len(attr_err) > 20:
    print(f'  ... and {len(attr_err) - 20} more')

print()

# 5. missing 'x' 的详细文件
missing_x = [(k, err) for k, err in missing_args if "'x'" in err]
print(f"=== missing 'x': {len(missing_x)} ===")
for fp, err in missing_x[:10]:
    print(f'  {fp}')

print()

# 6. missing '输入' 的详细文件
missing_input = [(k, err) for k, err in missing_args if "'输入'" in err]
print(f"=== missing '输入': {len(missing_input)} ===")
for fp, err in missing_input[:10]:
    print(f'  {fp}')

print()

# 7. missing '标准差' 的详细文件
missing_std = [(k, err) for k, err in missing_args if "'标准差'" in err]
print(f"=== missing '标准差': {len(missing_std)} ===")
for fp, err in missing_std[:10]:
    print(f'  {fp}')

print()

# 8. 所有 missing_required_arg 的详细文件
print('=== 所有 missing_required_arg 文件 ===')
for fp, err in sorted(missing_args):
    print(f'  {fp}: {err}')