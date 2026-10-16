# -*- coding: utf-8 -*-
"""R153：批量同步 `是空` 的 Python 侧 / 自举侧定义到新语义（null 或 空串）。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

新 = 'lambda x: x is None or (isinstance(x, str) and len(x) == 0)'

# 1) 自举链 / 生成器的 `_xxx_builtin.是空 = lambda x: x is None`
目标 = [
    'bootstrap/bootstrap_v3.light',
    'bootstrap/codegen.light',
    'bootstrap/release/bootstrap_v3.light',
    'bootstrap/bootstrap_v3_gen.py',
    'bootstrap/bootstrap_v3_gen2.py',
    'bootstrap/bootstrap_v3_gen3.py',
]
_自举模式 = re.compile(r'(_(?:light|duan)_builtin\.是空\s*=\s*lambda x: x is None)')
总数 = 0
for f in 目标:
    if not os.path.isfile(f):
        print('!! 缺失 %s' % f)
        continue
    t = open(f, 'r', encoding='utf-8').read()
    n = len(_自举模式.findall(t))
    if n == 0:
        print('   %s 无匹配（跳过）' % f)
        continue
    t2 = _自举模式.sub(lambda m: m.group(1).replace(
        'lambda x: x is None', 新), t)
    open(f, 'w', encoding='utf-8', newline='').write(t2)
    print('OK %s 替换 %d 处' % (f, n))
    总数 += n

# 2) src 腿两个 codegen 的 fallback 表
for f, old, new in [
    ('src/code_generator.py',
     'self._add_line("    (\'是空\', lambda v: v is None),")',
     'self._add_line("    (\'是空\', lambda v: v is None or (isinstance(v, str) and len(v) == 0)),"),  # R153：null 或 空串'),
    ('src/code_generator_unified.py',
     'self._add_line("    (\'是空\', lambda v: v is None),")',
     'self._add_line("    (\'是空\', lambda v: v is None or (isinstance(v, str) and len(v) == 0)),"),  # R153：null 或 空串'),
]:
    t = open(f, 'r', encoding='utf-8').read()
    if t.count(old) != 1:
        print('!! %s fallback 行数异常：%d' % (f, t.count(old)))
        sys.exit(1)
    open(f, 'w', encoding='utf-8', newline='').write(t.replace(old, new))
    print('OK %s fallback 已改' % f)

print('自举/生成器共替换 %d 处' % 总数)
