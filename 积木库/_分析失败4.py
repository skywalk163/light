# -*- coding: utf-8 -*-
"""分析失败模式 v4 - TypeError int is not callable 详细分析"""
import os, re, json
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
RESULTS_PATH = os.path.join(_HERE, '_预跑结果.json')
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')

with open(RESULTS_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)
results = data['逐块']

by_error = defaultdict(list)
for path, info in results.items():
    if info['status'] == 'failed':
        by_error[info['error']].append((path, info['error_msg']))

# TypeError: int is not callable 样本
print('=== TypeError: int is not callable 样本 ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "int object is not callable" in msg or "int' object is not callable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  错误: {msg[:200]}')
        print(f'  内容: {content.strip()[:300]}')
        print()
        count += 1
        if count >= 10: break

# 分析int is not callable中的函数名模式
print('=== int is not callable: 被调用函数名分析 ===')
func_calls = defaultdict(int)
for path, msg in by_error.get('TypeError', []):
    if "int object is not callable" in msg or "int' object is not callable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        # 找到函数定义行
        for line in content.split('\n'):
            if line.strip().startswith('段落 '):
                m = re.match(r'段落\s+(\S+)', line.strip())
                if m:
                    func_calls[m.group(1)] += 1
                break
for k, v in sorted(func_calls.items(), key=lambda x: -x[1])[:30]:
    print(f'  {k}: {v}')

# 查看"int is not callable"的错误消息中的函数名
print('\n=== int is not callable: 错误消息中的函数名 ===')
func_names = defaultdict(int)
for path, msg in by_error.get('TypeError', []):
    if "int object is not callable" in msg or "int' object is not callable" in msg:
        # 提取错误消息中的函数名
        m = re.search(r"'([^']+)' object is not callable", msg)
        if m:
            pass  # 已经知道是int
        # 从错误消息提取更多上下文
        # 通常错误消息类似于: 'int' object is not callable
        # 但实际上错误消息来自Python traceback，不会有函数名信息
        # 函数名信息在traceback中
        pass

# 统计"int has no len"的样本
print('\n=== int has no len() 样本 ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "has no len" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  错误: {msg[:200]}')
        print(f'  内容: {content.strip()[:300]}')
        print()
        count += 1
        if count >= 5: break

# 统计"int not subscriptable"的样本
print('\n=== int not subscriptable 样本 ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "not subscriptable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  错误: {msg[:200]}')
        print(f'  内容: {content.strip()[:300]}')
        print()
        count += 1
        if count >= 5: break

# 统计"str is not callable"的样本
print('\n=== str is not callable 样本 ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "str object is not callable" in msg or "str' object is not callable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  错误: {msg[:200]}')
        print(f'  内容: {content.strip()[:300]}')
        print()
        count += 1
        if count >= 5: break

# 统计AttributeError: str has no attribute '切分'的样本
print('\n=== AttributeError: 切分 样本 ===')
count = 0
for path, msg in by_error.get('AttributeError', []):
    if "切分" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  错误: {msg[:200]}')
        print(f'  内容: {content.strip()[:300]}')
        print()
        count += 1
        if count >= 5: break