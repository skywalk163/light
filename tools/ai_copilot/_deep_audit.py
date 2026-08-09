"""
深入调查重复条目、未翻译关键字、语法缺口
"""
import json, re, sys, os
from collections import Counter, defaultdict

data = [json.loads(l) for l in open('sft_dataset.jsonl', encoding='utf-8')]

print("=" * 70)
print("一、重复条目详细分析")
print("=" * 70)

# Find exact duplicates
py_map = defaultdict(list)
for i, item in enumerate(data):
    py = item['input']
    py_map[py].append(i)

duplicates = {k: v for k, v in py_map.items() if len(v) > 1}
print(f"完全重复的PY代码: {len(duplicates)} 组, 涉及 {sum(len(v) for v in duplicates.values())} 个条目")
print()

# Show duplicate groups
for py, indices in list(duplicates.items())[:10]:
    print(f"  重复 {len(indices)} 次: {py[:80]}...")
    print(f"    索引: {indices}")
    # Check if DU is also duplicate
    du_set = set()
    for idx in indices:
        du_set.add(data[idx]['output'])
    if len(du_set) > 1:
        print(f"    DU不同! 有 {len(du_set)} 个不同版本")
    print()

if len(duplicates) > 10:
    print(f"  ... 还有 {len(duplicates) - 10} 组")

# ============================================================
print("\n" + "=" * 70)
print("二、DU中未翻译的Python关键字")
print("=" * 70)

# Check for Python keywords in DU (excluding those in string literals)
keyword_checks = {
    'yield': r'\byield\b',
    'pass': r'\bpass\b',
    'continue': r'\bcontinue\b',
    'break': r'\bbreak\b',
    'True': r'\bTrue\b',
    'False': r'\bFalse\b',
    'None': r'\bNone\b',
    'def': r'\bdef\s',
    'class': r'\bclass\s',
    'import': r'\bimport\s',
    'elif': r'\belif\b',
    'lambda': r'\blambda\b',
}

for kw, pattern in keyword_checks.items():
    found = []
    for i, item in enumerate(data):
        du = item['output']
        # Exclude matches inside string literals
        # Simple check: if the match is between quotes, skip
        matches = list(re.finditer(pattern, du))
        for m in matches:
            # Check if inside quotes
            before = du[:m.start()]
            in_string = before.count("'") % 2 == 1 or before.count('"') % 2 == 1
            if not in_string:
                found.append((i, du[m.start():m.start()+30]))
                break
    
    if found:
        print(f"\n  {kw}: {len(found)} 条")
        for idx, snippet in found[:5]:
            print(f"    [{idx}] {snippet}...")
        if len(found) > 5:
            print(f"    ... 还有 {len(found)-5} 条")

# ============================================================
print("\n" + "=" * 70)
print("三、True/False/None 在DU中的使用分析")
print("=" * 70)

for kw in ['True', 'False', 'None']:
    found = []
    for i, item in enumerate(data):
        du = item['output']
        for m in re.finditer(r'\b' + kw + r'\b', du):
            before = du[:m.start()]
            in_string = before.count("'") % 2 == 1 or before.count('"') % 2 == 1
            if not in_string:
                found.append(i)
                break
    if found:
        print(f"  {kw}: {len(found)} 条")
        for idx in found[:3]:
            # Show context
            du = data[idx]['output']
            for m in re.finditer(r'\b' + kw + r'\b', du):
                before = du[:m.start()]
                in_string = before.count("'") % 2 == 1 or before.count('"') % 2 == 1
                if not in_string:
                    start = max(0, m.start()-20)
                    end = min(len(du), m.end()+20)
                    print(f"    [{idx}] ...{du[start:end]}...")
                    break

# ============================================================
print("\n" + "=" * 70)
print("四、语法缺口分析")
print("=" * 70)

gaps = {
    "多变量赋值 (a=b=c)": r'^\s*\w+\s*=\s*\w+\s*=\s*\w+',
    "生成器表达式": r'\(\s*\w+\s+for\s+\w+\s+in\s+',
    "try/except/finally": r'try.*except.*finally',
    "assert": r'\bassert\s+',
    "as别名 (import X as Y)": r'\bimport\s+\w+\s+as\b|\bfrom\s+\w+\s+import\s+\w+\s+as\b',
    "步长切片 [::step]": r'\[\s*\d*\s*:\s*\d*\s*:\s*\d+\s*\]',
    "装饰器 (@decorator)": r'^\s*@\w+',
    "yield生成器": r'\byield\b',
}

for name, pattern in gaps.items():
    count = 0
    for item in data:
        py = item['input']
        if re.search(pattern, py, re.MULTILINE):
            count += 1
    status = "✓ 已覆盖" if count > 0 else "✗ 缺失"
    if count > 0:
        print(f"  {status}: {name} ({count} 条)")
    else:
        print(f"  {status}: {name}")

# ============================================================
print("\n" + "=" * 70)
print("五、未使用的光明关键字（可能缺失的语法模式）")
print("=" * 70)

unused_api = [
    '写入文件', '删除文件', '文件存在', '中', '那么', '枚举', '排序', '压缩', '过滤',
    '匿名', '截取', '列表包含', '连接', '替换', '拆分', '去除', '转大写', '转小写',
    '开头', '结尾', '转整数', '转浮点', '转字符串', '字典获取', '字典设置',
    '字典键列表', '字典包含键', '解析JSON', '序列化JSON'
]

# Check if these are used in DU at all
for kw in unused_api:
    found = 0
    for item in data:
        if kw in item['output']:
            found += 1
    if found > 0:
        print(f"  {kw}: {found} 条 (实际有使用)")
    else:
        print(f"  {kw}: 0 条 (未使用)")

# ============================================================
print("\n" + "=" * 70)
print("六、DU中残留Python代码模式（深度检查）")
print("=" * 70)

# Check for patterns that suggest DU code is actually Python code
suspicious = []
for i, item in enumerate(data):
    du = item['output']
    py = item['input']
    
    # Check if DU starts with Python-style code
    python_lines = 0
    total_lines = 0
    for line in du.split('\n'):
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        # Check for Python-specific patterns
        if re.match(r'^\s*(def |class |import |from |elif |else:|except |finally:|try:|with |raise |return |break|continue|pass|yield |assert |global |nonlocal |del |lambda )', line):
            python_lines += 1
    
    if total_lines > 0 and python_lines / total_lines > 0.5:
        suspicious.append((i, python_lines, total_lines))

if suspicious:
    print(f"  疑似DU中有大量Python代码: {len(suspicious)} 条")
    for idx, pl, tl in suspicious[:5]:
        print(f"    [{idx}] {pl}/{tl} 行疑似Python")
        print(f"      DU: {data[idx]['output'][:100]}...")
else:
    print(f"  未发现疑似Python代码的DU条目")

print(f"\n检查完成。")