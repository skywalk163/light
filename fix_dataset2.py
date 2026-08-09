"""Fix the 如果 prefix issue in converted list comprehensions"""
import json

with open(r'c:\dumatework\light\tools\ai_copilot\sft_dataset_v3.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_items = []
for line in lines:
    data = json.loads(line.strip())
    output = data['output']
    
    # Fix: 若 如果 → 若
    # The pattern 若 如果 cond should be 若 cond
    import re
    output = re.sub(r'若 如果 ', '若 ', output)
    
    data['output'] = output
    fixed_items.append(data)

with open(r'c:\dumatework\light\tools\ai_copilot\sft_dataset_v3.jsonl', 'w', encoding='utf-8') as f:
    for item in fixed_items:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print('Fixed 若 如果 → 若')
print('Done!')