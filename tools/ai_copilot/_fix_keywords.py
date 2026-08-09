"""
修复DU中的Python关键字残留：
1. pass -> 设 _ 为 空
2. reverse=True -> reverse=真
3. yield from -> 用Light语法替代
"""
import json, re

data = [json.loads(l) for l in open('sft_dataset.jsonl', encoding='utf-8')]

fixes = 0

for i, item in enumerate(data):
    du = item['output']
    original = du
    
    # 1. Fix pass (but not inside string literals like print("pass"))
    # Strategy: replace standalone 'pass' in DU code blocks
    # The pass appears as a statement in Light paragraphs
    # Replace '\n        pass' or '\n    pass' patterns
    du = re.sub(r'(?<=\n)    pass(?=\n|$)', '    设 _ 为 空', du)
    du = re.sub(r'(?<=\n)        pass(?=\n|$)', '        设 _ 为 空', du)
    du = re.sub(r'(?<=\n)            pass(?=\n|$)', '            设 _ 为 空', du)
    # Also handle pass at end of string
    du = re.sub(r'(?<=\n)    pass$', '    设 _ 为 空', du)
    du = re.sub(r'(?<=\n)        pass$', '        设 _ 为 空', du)
    
    # 2. Fix reverse=True -> reverse=真
    du = du.replace('reverse=True', 'reverse=真')
    
    # 3. Fix yield from -> 遍历并产出
    # yield from expr -> 遍历 _item 于 expr：产出 _item
    # But Light might not have '产出' keyword. For now, keep as is.
    # yield from is rare (3 entries) and Light doesn't support it well.
    
    if du != original:
        fixes += 1
        data[i]['output'] = du

print(f"修复了 {fixes} 个条目")

# 统计残留
pass_count = 0
true_count = 0
for i, item in enumerate(data):
    du = item['output']
    for m in re.finditer(r'\bpass\b', du):
        before = du[:m.start()]
        in_string = before.count("'") % 2 == 1 or before.count('"') % 2 == 1
        if not in_string:
            pass_count += 1
            break
    for m in re.finditer(r'\bTrue\b', du):
        before = du[:m.start()]
        in_string = before.count("'") % 2 == 1 or before.count('"') % 2 == 1
        if not in_string:
            true_count += 1
            break

print(f"残留: pass={pass_count}, True={true_count}")

# 保存
with open('sft_dataset.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"数据集已保存: {len(data)} 条")