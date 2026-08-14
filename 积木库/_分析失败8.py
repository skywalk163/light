# -*- coding: utf-8 -*-
"""分析剩余失败中的具体错误"""
import json
from collections import Counter

with open('_预跑结果.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blocks = data.get('逐块', {})

# 展示最常见的错误消息
error_msgs = Counter()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        # 截取前80字符作为key
        key = emsg.strip().split('\n')[0][:80]
        error_msgs[key] += 1

print('=== 最常见的错误消息（前20个） ===')
for k, v in sorted(error_msgs.items(), key=lambda x: -x[1])[:20]:
    print(f'  [{v}] {k}')

# 展示每个错误的第一个文件名
print('\n=== 每个错误类型的一个示例文件 ===')
seen = set()
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        key = emsg.strip().split('\n')[0][:80]
        if key not in seen:
            seen.add(key)
            print(f'  [{name}] {key}')

# 展示所有 NameError 的文件
print('\n=== NameError 文件清单 ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if 'not defined' in emsg:
            print(f'  {name}: {emsg.strip()[:100]}')
            count += 1
            if count >= 30:
                break

# 展示所有 'LightStr' object is not callable 的文件
print('\n=== LightStr is not callable 文件 ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if 'LightStr' in emsg and 'callable' in emsg:
            print(f'  {name}: {emsg.strip()[:100]}')
            count += 1
            if count >= 15:
                break

# 展示所有 'float' object is not callable 的文件
print('\n=== float is not callable 文件 ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if 'float' in emsg and 'callable' in emsg:
            print(f'  {name}: {emsg.strip()[:100]}')
            count += 1
            if count >= 15:
                break

# 展示所有 'int' object is not callable / subscriptable 的文件
print('\n=== int is not callable/subscriptable 文件 ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if "'int' object is not" in emsg:
            print(f'  {name}: {emsg.strip()[:100]}')
            count += 1
            if count >= 20:
                break

# 展示所有 int has no len 的文件
print('\n=== int has no len 文件 ===')
count = 0
for name, info in blocks.items():
    if info.get('status') == 'failed':
        emsg = info.get('error_msg', '')
        if "has no len()" in emsg:
            print(f'  {name}: {emsg.strip()[:100]}')
            count += 1
            if count >= 15:
                break