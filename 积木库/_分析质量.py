# -*- coding: utf-8 -*-
"""分析当前积木库质量"""
import json

d = json.load(open('积木库_导出_v4.json', 'r', encoding='utf-8'))
blocks = d['块']

# 按领域查看前20个块的源码
for domain in ['心理', '体育', '音乐', '天文', '环境', '编码', '电子', '颜色', '工具', '数组', '概率', '教育']:
    domain_blocks = [b for b in blocks if b['领域'] == domain]
    print('=== %s (%d 块) ===' % (domain, len(domain_blocks)))
    cnt = 0
    for b in domain_blocks:
        if cnt >= 20:
            break
        src = b['源码'][:120].replace('\n', ' | ')
        print('  %-12s: %s' % (b['名称'], src))
        cnt += 1
    if len(domain_blocks) > 20:
        print('  ... 还有 %d 个块' % (len(domain_blocks)-20))