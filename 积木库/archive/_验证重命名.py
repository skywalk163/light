# -*- coding: utf-8 -*-
"""验证所有重命名的块并更新索引."""
import json
import os
import subprocess
import sys

_REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
V5 = os.path.join(_REPO, '积木库', 'blocks_v5', '统计')
IDX = os.path.join(_REPO, '积木库', '索引.json')

names = ['零一间数', '区间计数', '十倍数数', '二倍数数', '三倍数数', '五倍数数',
         '超过十数', '超过百数', '小于零点一数']

all_pass = True
for name in names:
    path = os.path.join(V5, '%s.light' % name)
    r = subprocess.run(
        [sys.executable, os.path.join(_REPO, 'cli', 'light.py'), 'check', path],
        capture_output=True, text=True, timeout=10, cwd=_REPO
    )
    ok = r.returncode == 0
    if not ok:
        all_pass = False
    status = 'PASS' if ok else 'FAIL'
    print('%s: %s' % (status, name))

# Update index.json
rename_map = {
    '统计/10100间数': '统计/区间计数',
    '统计/01间数': '统计/零一间数',
    '统计/10倍数数': '统计/十倍数数',
    '统计/2倍数数': '统计/二倍数数',
    '统计/3倍数数': '统计/三倍数数',
    '统计/5倍数数': '统计/五倍数数',
    '统计/大于10数': '统计/超过十数',
    '统计/大于100数': '统计/超过百数',
    '统计/小于01数': '统计/小于零点一数',
}

with open(IDX, 'r', encoding='utf-8') as f:
    idx = json.load(f)

changes = 0
if isinstance(idx, dict):
    for key in list(idx.keys()):
        val = idx[key]
        if isinstance(val, str):
            for old_ref, new_ref in rename_map.items():
                if old_ref in val:
                    idx[key] = val.replace(old_ref, new_ref)
                    changes += 1
        elif isinstance(val, dict):
            for sub_key in val:
                sub_val = val[sub_key]
                if isinstance(sub_val, str):
                    for old_ref, new_ref in rename_map.items():
                        if old_ref in sub_val:
                            val[sub_key] = sub_val.replace(old_ref, new_ref)
                            changes += 1

if changes > 0:
    with open(IDX, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print('Index updated: %d references changed' % changes)
else:
    print('Index: no changes needed')

print('All pass: %s' % all_pass)