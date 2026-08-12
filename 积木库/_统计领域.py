import json

with open(r'd:\traework\light\积木库\积木库_导出_v4.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('版本:', d['版本'])
print('总块数:', d['总块数'])
print('领域数:', d['领域数'])
print()

块 = d['块']
统计 = {}
for b in 块:
    领域 = b['领域']
    统计[领域] = 统计.get(领域, 0) + 1

for 领域, 数量 in sorted(统计.items(), key=lambda x: -x[1]):
    bar = '#' * min(数量 // 5, 40)
    print(f'{领域:>8}: {数量:>4} {bar}')

print(f'\n总计: {sum(统计.values())} 块, {len(统计)} 个领域')
print(f'平均: {sum(统计.values()) / len(统计):.0f} 块/领域')
print(f'最少: {min(统计.values())} 块 ({min(统计, key=统计.get)})')
print(f'还需: {10000 - sum(统计.values())} 块到10000')