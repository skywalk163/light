"""修复已恢复的5个文件I/O条目的DU代码问题"""
import json, os

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl')
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset_backup_v44.jsonl')

with open(DATASET_PATH, 'r', encoding='utf-8') as f:
    data = [json.loads(l) for l in f if l.strip()]

# Backup
with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"Backup saved to {BACKUP_PATH}")

# Fix entry 1195 (v39[841]): multiple context managers -> nest them
# Problem: Light doesn't support comma-separated context managers
# Fix: nest the context managers, remove fake variable defs
item = data[1195]
du = item['output'].replace('\\n', '\n')
# Replace: 使用 读取文件("input.txt") 为 fin, 打开文件("output.txt", "w") 为 fout：
#     ...\n设 fin 为 空\n设 fout 为 空\n    ...
# With nested context managers
du = du.replace(
    '使用 读取文件("input.txt") 为 fin, 打开文件("output.txt", "w") 为 fout：\n设 fin 为 空\n设 fout 为 空',
    '使用 读取文件("input.txt") 为 fin：\n    使用 打开文件("output.txt", "w") 为 fout：'
)
# Fix indentation: the inner block needs extra indent
# The original had: \n    遍历 line 于 fin：\n        fout.write(line.upper())
# After nesting, the inner block should be indented one more level
du = du.replace(
    '\n    遍历 line 于 fin：\n        fout.write(line.upper())',
    '\n        遍历 line 于 fin：\n            fout.write(line.upper())'
)
item['output'] = du.replace('\n', '\\n')
print(f"Fixed [1195]: nested context managers")

# Fix entry 1197 (v39[854]): parts defined before line is available
item = data[1197]
du = item['output'].replace('\\n', '\n')
# Original: 设 parts 为 line.split(",") inside 使用 block, but before 遍历
# Fix: move parts definition inside the 遍历 loop
du = du.replace(
    '设 parts 为 line.split(",")\n    设 lines 为 [line.strip() 遍历 line 之 f 若 line.strip()]\n遍历 line 于 lines：\n    如果 len(parts) 大于等于 2：\n        打印(f"{parts[0]}: {parts[1]}")',
    '设 lines 为 [line.strip() 遍历 line 之 f 若 line.strip()]\n遍历 line 于 lines：\n    设 parts 为 line.split(",")\n    如果 len(parts) 大于等于 2：\n        打印(f"{parts[0]}: {parts[1]}")'
)
item['output'] = du.replace('\n', '\\n')
print(f"Fixed [1197]: moved parts definition inside loop")

# Fix entry 1198 (v39[855]): variables in wrong order
item = data[1198]
du = item['output'].replace('\\n', '\n')
# Original: row, values defined before loop, header inside loop body
# Fix: header before loop, values and row inside loop
du = du.replace(
    '设 row 为 dict(zip(header, values))\n        设 values 为 line.strip().split(",")\n    设 header 为 f.readline().strip().split(",")\n    遍历 line 于 f：\n        打印(row)',
    '设 header 为 f.readline().strip().split(",")\n    遍历 line 于 f：\n        设 values 为 line.strip().split(",")\n        设 row 为 dict(zip(header, values))\n        打印(row)'
)
item['output'] = du.replace('\n', '\\n')
print(f"Fixed [1198]: reordered variable definitions")

# Save
with open(DATASET_PATH, 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nSaved {len(data)} entries to {DATASET_PATH}")