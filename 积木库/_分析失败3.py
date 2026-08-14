# -*- coding: utf-8 -*-
"""分析失败模式 v3 - 详细ParseError和TypeError样本"""
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

# 1. 无法识别的语法元素 - 样本
print('=== ParseError: 无法识别的语法元素 ===')
count = 0
for path, msg in by_error.get('ParseError', []):
    if '无法识别的语法元素' in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:150]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 8:
            break

# 2. ParseError: 期望冒号 with 关键字 - 更多样本
print('=== ParseError: 期望冒号 with 关键字 ===')
count = 0
for path, msg in by_error.get('ParseError', []):
    if '期望 冒号' in msg and '关键字' in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:150]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 8:
            break

# 3. 期望冒号 with 数字
print('=== ParseError: 期望冒号 with 数字 ===')
count = 0
for path, msg in by_error.get('ParseError', []):
    if '期望 冒号' in msg and '数字' in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:150]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 5:
            break

# 4. 期望冒号 with CHINESE_NUM
print('=== ParseError: 期望冒号 with CHINESE_NUM ===')
count = 0
for path, msg in by_error.get('ParseError', []):
    if '期望 冒号' in msg and 'CHINESE_NUM' in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:150]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 5:
            break

# 5. TypeError: int is not callable - 更多样本
print('=== TypeError: int object is not callable ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "int object is not callable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:120]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 8:
            break

# 6. TypeError: 'str' object is not callable
print('=== TypeError: str object is not callable ===')
count = 0
for path, msg in by_error.get('TypeError', []):
    if "str object is not callable" in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:120]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 5:
            break

# 7. 统计期望冒号中的关键字
print('=== 期望冒号: 关键字词频统计 ===')
keywords_used = defaultdict(int)
for path, msg in by_error.get('ParseError', []):
    if '期望 冒号' in msg and '关键字' in msg:
        m = re.search(r'附近: \'([^\']+)\'', msg)
        if m:
            keywords_used[m.group(1)] += 1
for k, v in sorted(keywords_used.items(), key=lambda x: -x[1])[:20]:
    print(f'  {k}: {v}')

# 8. 统计"int is not callable"中的函数名
print('=== TypeError int is not callable: 函数名统计 ===')
func_called = defaultdict(int)
for path, msg in by_error.get('TypeError', []):
    if "int object is not callable" in msg:
        m = re.search(r'(\w[\w\u4e00-\u9fff]*)\(', msg)
        # 从文件名推断
        func_name = os.path.splitext(os.path.basename(path))[0]
        func_called[func_name] += 1
for k, v in sorted(func_called.items(), key=lambda x: -x[1])[:20]:
    print(f'  {k}: {v}')

# 9. 统计TypeError: unsupported operand 中的类型
print('=== TypeError: unsupported operand 统计 ===')
te_operand = defaultdict(int)
for path, msg in by_error.get('TypeError', []):
    if "unsupported operand" in msg:
        te_operand[msg[:80]] += 1
for k, v in sorted(te_operand.items(), key=lambda x: -x[1])[:10]:
    print(f'  [{v}] {k}')

# 10. 统计SyntaxError
print('=== SyntaxError 样本 ===')
for path, msg in by_error.get('SyntaxError', [])[:5]:
    full = os.path.join(BLOCKS_DIR, path)
    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f'[{path}]')
    print(f'  错误: {msg[:150]}')
    print(f'  内容: {content.strip()[:200]}')
    print()

# 11. 统计ValueError
print('=== ValueError 样本 ===')
for path, msg in by_error.get('ValueError', [])[:5]:
    full = os.path.join(BLOCKS_DIR, path)
    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f'[{path}]')
    print(f'  错误: {msg[:150]}')
    print(f'  内容: {content.strip()[:200]}')
    print()

# 12. 统计"真"是保留关键字
print('=== ParseError: "真"是保留关键字 ===')
count = 0
for path, msg in by_error.get('ParseError', []):
    if '真' in msg and '保留关键字' in msg:
        full = os.path.join(BLOCKS_DIR, path)
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f'[{path}]')
        print(f'  {msg[:150]}')
        print(f'  内容: {content.strip()[:200]}')
        print()
        count += 1
        if count >= 5:
            break