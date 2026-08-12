import json

d = json.load(open(r'd:\traework\light\积木库\积木库_导出_v4.json', 'r', encoding='utf-8'))
print('版本:', d['版本'])
print('领域数:', d['领域数'])
print('总块数:', d['总块数'])

块 = d['块']
if isinstance(块, dict):
    print(f'领域数: {len(块)}')
    统计 = sorted([(k, len(v)) for k, v in 块.items()], key=lambda x: -x[1])
    for k, v in 统计:
        print(f'  {k}: {v}')