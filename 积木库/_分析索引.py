# -*- coding: utf-8 -*-
"""分析索引文件，了解块名模式"""
import json

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, '索引.json'), encoding='utf-8') as f:
    idx = json.load(f)

blocks = idx.get('块', [])
print(f'总块数: {len(blocks)}')
print(f'\n前20个块名:')
for b in blocks[:20]:
    print(f'  {b["名称"]:20s} 领域: {b.get("领域", "?")}')

# 统计含关键字的块名
keywords = ['求和', '排序', '反转', '替换', '拼接', '切分', '大写', '小写',
            '去重', '过滤', '取整', '四舍五入', '转整数', '转文本',
            '最大值', '最小值', '绝对值', '标准差', '方差', '中位数',
            '众数', '分位数', '平均数', '均值', '个税', '人民币',
            '素数', '阶乘', '斐波那契', '取余', '求幂', '百分比',
            '包含', '长度', '截取', '速度', '压强', '电阻', '密度',
            '人口', '覆盖率', '编码', '密码', '存储', '网络',
            '复利', '增长率', 'GDP', 'pH', '功率', '周期', '频率',
            '热量', '容量', '效率', '日志', '时间', '日期',
            '映射', '迭代', '枚举', '累积', '归约', '计数',
            '类型', '集合', '交集', '并集', '差集', '子集',
            '物理', '化学', '生物', '天文', '地理', '颜色',
            '音乐', '工具', '经济', '财务', '法律', '教育',
            '体育', '农业', '医学', '工程', '计算机', '网络',
            '编码', '密码', '电子', '颜色', '音乐', '工具',
            '财务', '经济', '法律', '教育', '心理', '体育', '农业',
            '医学', '工程', '计算机', '网络', '编码', '密码',
            '电子', '颜色', '音乐', '工具', '中文']
for kw in keywords:
    matches = [b['名称'] for b in blocks if kw in b['名称']]
    if matches:
        print(f'\n含「{kw}」的块 ({len(matches)}):')
        for m in matches[:5]:
            print(f'  - {m}')
        if len(matches) > 5:
            print(f'  ... 还有 {len(matches)-5} 个')

# 所有领域
domains = set()
for b in blocks:
    d = b.get('领域', [])
    if isinstance(d, list):
        for dd in d:
            domains.add(dd)
    else:
        domains.add(d)
print(f'\n所有领域 ({len(domains)}):')
for d in sorted(domains):
    print(f'  - {d}')