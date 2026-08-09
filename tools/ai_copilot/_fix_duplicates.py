"""
修复关键问题：
1. 去重重复条目
2. 修复DU中未翻译的pass/yield
3. 修复True/False/None在DU中的残留
"""
import json, re

data = [json.loads(l) for l in open('sft_dataset.jsonl', encoding='utf-8')]

print(f"原始条目数: {len(data)}")

# ============================================================
# 1. 去重：保留第一个出现的条目
# ============================================================
seen = set()
unique_data = []
dup_count = 0
for item in data:
    py = item['input']
    if py in seen:
        dup_count += 1
    else:
        seen.add(py)
        unique_data.append(item)

print(f"去重后: {len(unique_data)} 条 (移除 {dup_count} 条重复)")

# ============================================================
# 2. 修复DU中未翻译的Python关键字
# ============================================================
fix_count = 0

for i, item in enumerate(unique_data):
    du = item['output']
    original_du = du
    
    # 修复 pass -> 跳过 (但要注意，光明中"跳过"是continue的意思)
    # pass 在光明中应该用空语句，或者直接省略
    # 检查pass是否在独立行
    lines = du.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^pass\s*$', stripped):
            # 如果pass是缩进块中的唯一语句，替换为空操作
            indent = len(line) - len(line.lstrip())
            new_lines.append(' ' * indent + '设 _ 为 空')
            fix_count += 1
        else:
            new_lines.append(line)
    du = '\n'.join(new_lines)
    
    # 修复 yield from -> 需要生成器委托，光明暂时用简单的yield替代
    # yield from expr -> 遍历 item 于 expr：yield item
    # 但光明可能不支持yield... 先保留
    
    # 修复 True/False/None (在关键字参数中)
    # 修复 False/None (作为变量值)
    du = re.sub(r'\bFalse\b', '假', du)
    du = re.sub(r'\bNone\b', '空', du)
    # True 比较复杂，在关键字参数中保留，在变量值中替换
    # 只在赋值上下文中替换 True
    du = re.sub(r'为 True\b', '为 真', du)
    du = re.sub(r'为 True\n', '为 真\n', du)
    
    if du != original_du:
        unique_data[i]['output'] = du

print(f"修复DU关键字: {fix_count} 处 pass")

# 统计修复后的True/False/None残留
true_count = sum(1 for item in unique_data if re.search(r'\bTrue\b', item['output']))
false_count = sum(1 for item in unique_data if re.search(r'\bFalse\b', item['output']))
none_count = sum(1 for item in unique_data if re.search(r'\bNone\b', item['output']))
print(f"修复后残留: True={true_count}, False={false_count}, None={none_count}")

# ============================================================
# 保存
# ============================================================
# 备份
with open('sft_dataset_backup_v43.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print("备份保存到 sft_dataset_backup_v43.jsonl")

# 保存去重修复后的数据集
with open('sft_dataset.jsonl', 'w', encoding='utf-8') as f:
    for item in unique_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"数据集保存: {len(unique_data)} 条")

# 验证
verify_data = [json.loads(l) for l in open('sft_dataset.jsonl', encoding='utf-8')]
py_set = set(item['input'] for item in verify_data)
print(f"验证: {len(verify_data)} 条, 去重后 {len(py_set)} 唯一")