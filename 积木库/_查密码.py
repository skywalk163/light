# -*- coding: utf-8 -*-
"""查询密码领域预跑失败详情"""
import json

data = json.load(open('_预跑结果.json', encoding='utf-8'))
blocks = data.get('逐块', {})

count = 0
for name, info in sorted(blocks.items()):
    if name.startswith('密码\\') and info.get('status') == 'failed':
        print(f'[{info.get("error_type","?")}] {name}')
        emsg = info.get('error_msg', '')
        print(f'  {emsg[:120]}')
        print()
        count += 1
        if count >= 30:
            break
print(f'共显示 {count} 个密码领域失败')