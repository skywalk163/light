# -*- coding: utf-8 -*-
"""R153 补漏：第一轮清单没盘到的 5 处（正是「只修一处还会再爆第三处」的实证）。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

新 = 'lambda x: x is None or (isinstance(x, str) and len(x) == 0)'
模式 = re.compile(r'(_(?:light|duan)_builtin\.是空\s*=\s*lambda x: x is None)')

目标 = [
    'bootstrap/release/bootstrap_compiler.py',
    'bootstrap/run_compiler.py',
    'bootstrap/test_parser_debug.py',
    'tests/test_self_host.py',
    'tools/archive/verify_bootstrap.py',
]

总数 = 0
坏 = False
for f in 目标:
    if not os.path.isfile(f):
        print('!! 缺失 %s' % f)
        坏 = True
        continue
    t = open(f, 'r', encoding='utf-8').read()
    n = len(模式.findall(t))
    if n == 0:
        print('!! %s 无匹配' % f)
        坏 = True
        continue
    t2 = 模式.sub(lambda m: m.group(1).replace('lambda x: x is None', 新), t)
    open(f, 'w', encoding='utf-8', newline='').write(t2)
    print('OK %s 替换 %d 处' % (f, n))
    总数 += n

print('补漏共 %d 处' % 总数)
sys.exit(0 if not 坏 else 1)
