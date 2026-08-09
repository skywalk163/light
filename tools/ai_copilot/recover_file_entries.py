#!/usr/bin/env python3
"""恢复文件 I/O 条目：添加文件预创建，使 PY 和 DU 都能正确执行"""
import json, os, re

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl')
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset_backup_v43.jsonl')

# Load current dataset
with open(DATASET_PATH, 'r', encoding='utf-8') as f:
    current = [json.loads(l) for l in f if l.strip()]

# Load v39 backup for original file entries
with open('sft_dataset_backup_v39.jsonl', 'r', encoding='utf-8') as f:
    v39 = [json.loads(l) for l in f if l.strip()]

# Backup current
with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
    for item in current:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
print(f"Backup saved to {BACKUP_PATH}")

# File entry definitions: (v39_index, input_filename, file_content)
# Each entry needs: input file to read, and optionally output file to write
file_entries = {
    # 840: read data.csv, print each line
    840: {
        'files': {'data.csv': 'hello\nworld\nfoo\nbar\n'},
        'cleanup': ['data.csv'],
    },
    # 841: read input.txt, write to output.txt (upper case)
    841: {
        'files': {'input.txt': 'hello\nworld\nFOO\n'},
        'cleanup': ['input.txt', 'output.txt'],
    },
    # 853: read numbers.txt, sum them
    853: {
        'files': {'numbers.txt': '10\n20\n30\n40\n50\n'},
        'cleanup': ['numbers.txt'],
    },
    # 854: read input.txt (CSV), print key:value pairs
    854: {
        'files': {'input.txt': 'name,Alice\nage,30\ncity,Beijing\n'},
        'cleanup': ['input.txt'],
    },
    # 855: read data.csv (CSV with header), print dict rows
    855: {
        'files': {'data.csv': 'name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n'},
        'cleanup': ['data.csv'],
    },
}

recovered = []
for v39_idx, config in file_entries.items():
    item = v39[v39_idx]
    py = item['input']
    du = item['output']
    cat = item.get('category', '')
    
    # Build file creation code for PY
    # Use os.linesep.join() to avoid \\n escaping issues with verify's replace('\\n', '\\n')
    py_setup = 'import os\n'
    du_setup = ''
    
    for fname, content in config['files'].items():
        lines = content.strip('\n').split('\n')
        lines_repr = '[' + ', '.join(repr(l) for l in lines) + ']'
        py_setup += f'with open({repr(fname)}, "w", encoding="utf-8") as _f:\n    _f.write(os.linesep.join({lines_repr} + [""]))\n'
        
        # Light setup
        du_setup += f'使用 打开文件("{fname}", "w") 为 _f：\\n    _f.write(os.linesep.join({lines_repr} + [""]))\\n'
    
    # Build cleanup code for PY
    py_cleanup = '\n'.join(f'os.remove({repr(fname)})' for fname in config['cleanup'])
    
    # Build cleanup for DU (using 删除文件)
    du_cleanup = '\\n'.join(f'删除文件("{fname}")' for fname in config['cleanup'])
    
    # New PY: setup + original + cleanup
    new_py = py_setup + '\n' + py + '\n' + py_cleanup
    
    # New DU: setup + original + cleanup
    # Original DU might have fake var defs that need cleanup
    new_du = du_setup + du + '\\n' + du_cleanup
    
    new_item = {
        'instruction': item.get('instruction', '用光明v3.2语法重写以下Python代码。'),
        'input': new_py,
        'output': new_du,
        'category': cat,
    }
    recovered.append(new_item)
    print(f"  Recovered v39[{v39_idx}] cat={cat}")

# Append recovered entries to current dataset
current.extend(recovered)

with open(DATASET_PATH, 'w', encoding='utf-8') as f:
    for item in current:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nRecovered {len(recovered)} file I/O entries")
print(f"Total entries: {len(current)}")
print(f"Saved to {DATASET_PATH}")