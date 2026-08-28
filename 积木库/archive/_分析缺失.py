#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析COMMON_MISSING_VARS中缺少的NameError变量"""
import json
import re

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
results = d.get('逐块', {})

name_errs = {}
for p, info in results.items():
    if isinstance(info, dict) and info.get('error') == 'NameError':
        msg = info.get('error_msg', '')
        m = re.search(r"name '([^']+)' is not defined", msg)
        if m:
            name_errs[p] = m.group(1)

with open('_预跑.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有COMMON_MISSING_VARS中的变量名
pattern = re.compile(r"'([^']+)':\s+")
lines = content.split('\n')
in_dict = False
dict_vars = set()
for line in lines:
    if 'COMMON_MISSING_VARS' in line and '{' in line:
        in_dict = True
        continue
    if in_dict:
        if '}' in line and not line.strip().startswith('#'):
            break
        m = pattern.search(line)
        if m:
            dict_vars.add(m.group(1))

# 找出未定义的变量
missing_vars = {}
for path, var in name_errs.items():
    if var not in dict_vars:
        if var not in missing_vars:
            missing_vars[var] = []
        missing_vars[var].append(path)

print(f'NameError总数: {len(name_errs)}')
print(f'COMMON_MISSING_VARS中定义的变量数: {len(dict_vars)}')
print(f'未定义的变量数: {len(missing_vars)}')
print()
print('=== 未定义的缺失变量 ===')
# 按出现次数排序
for var, files in sorted(missing_vars.items(), key=lambda x: -len(x[1])):
    print(f"  '{var}': 出现在 {len(files)} 个文件")
    for f in files[:5]:
        print(f"    - {f}")
    if len(files) > 5:
        print(f"    ... 还有 {len(files)-5} 个")