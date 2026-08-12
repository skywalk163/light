# -*- coding: utf-8 -*-
"""
合并 v4 和 v5 积木库，取最优结果：
- v4 有更多真实公式（物理、化学、生物等）
- v5 有更全面的领域覆盖
- 合并时优先保留有真实公式的块
"""

import os, json, re

_HERE = os.path.dirname(os.path.abspath(__file__))

def 加载v4():
    with open(os.path.join(_HERE, '积木库_导出_v4.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

def 加载v5():
    with open(os.path.join(_HERE, '积木库_导出_v5.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

def 是存根(源码):
    """判断是否是简单的存根块（函数名(输入)模式）"""
    返回行 = [l.strip() for l in 源码.split('\n') if '返回' in l]
    if not 返回行:
        return True
    返回表达式 = 返回行[0]
    return bool(re.match(r'返回\s+\w+\(输入\)$', 返回表达式))

def 是通用块(名称, 领域):
    """判断是否是v3风格的通用块"""
    通用模式 = ['各元素', '乘积', '成对', '滚动', '过滤']
    if any(名称.startswith(p) for p in 通用模式):
        return True
    return False

def 主流程():
    print('合并 v4 + v5 -> v5_final')
    print('=' * 40)

    v4 = 加载v4()
    v5 = 加载v5()

    v4块 = {b['导出名']: b for b in v4['块']}
    v5块 = {b['导出名']: b for b in v5['块']}

    # 合并策略：
    # 1. 如果v4有该块且不是存根，用v4的
    # 2. 如果v5有该块且不是存根，用v5的
    # 3. 如果两个都有且都是存根，用v5的（领域更准确）
    # 4. 如果只有一个有，用那个
    # 5. 去除通用块（各元素、乘积等）

    合并后 = {}
    来源统计 = {'v4_公式': 0, 'v5_公式': 0, 'v4_存根': 0, 'v5_存根': 0, '通用_丢弃': 0}

    for 导出名 in set(list(v4块.keys()) + list(v5块.keys())):
        b4 = v4块.get(导出名)
        b5 = v5块.get(导出名)

        # 检查是否是通用块
        if b4 and 是通用块(b4['名称'], b4['领域']):
            来源统计['通用_丢弃'] += 1
            continue
        if b5 and 是通用块(b5['名称'], b5['领域']):
            来源统计['通用_丢弃'] += 1
            continue

        if b4 and b5:
            # 两者都有，优先用有公式的
            b4存根 = 是存根(b4['源码'])
            b5存根 = 是存根(b5['源码'])
            if not b4存根:
                合并后[导出名] = b4
                来源统计['v4_公式'] += 1
            elif not b5存根:
                合并后[导出名] = b5
                来源统计['v5_公式'] += 1
            else:
                # 都是存根，用v5的
                合并后[导出名] = b5
                来源统计['v5_存根'] += 1
        elif b4:
            if not 是存根(b4['源码']):
                合并后[导出名] = b4
                来源统计['v4_公式'] += 1
            else:
                合并后[导出名] = b4
                来源统计['v4_存根'] += 1
        else:  # b5 only
            if not 是存根(b5['源码']):
                合并后[导出名] = b5
                来源统计['v5_公式'] += 1
            else:
                合并后[导出名] = b5
                来源统计['v5_存根'] += 1

    # 统计
    total = sum(来源统计.values())
    print(f'\n合并结果:')
    print(f'  总块数: {len(合并后)}')
    print(f'  v4公式块: {来源统计["v4_公式"]} ({来源统计["v4_公式"]/len(合并后)*100:.1f}%)')
    print(f'  v5公式块: {来源统计["v5_公式"]} ({来源统计["v5_公式"]/len(合并后)*100:.1f}%)')
    print(f'  v4存根块: {来源统计["v4_存根"]} ({来源统计["v4_存根"]/len(合并后)*100:.1f}%)')
    print(f'  v5存根块: {来源统计["v5_存根"]} ({来源统计["v5_存根"]/len(合并后)*100:.1f}%)')
    print(f'  丢弃通用块: {来源统计["通用_丢弃"]}')
    print(f'  公式块合计: {来源统计["v4_公式"] + 来源统计["v5_公式"]} ({(来源统计["v4_公式"] + 来源统计["v5_公式"])/len(合并后)*100:.1f}%)')
    print(f'  存根块合计: {来源统计["v4_存根"] + 来源统计["v5_存根"]} ({(来源统计["v4_存根"] + 来源统计["v5_存根"])/len(合并后)*100:.1f}%)')

    # 按领域统计
    领域统计 = {}
    for b in 合并后.values():
        领域 = b['领域']
        领域统计[领域] = 领域统计.get(领域, 0) + 1

    print(f'\n领域分布:')
    for 领域, 数量 in sorted(领域统计.items(), key=lambda x: -x[1]):
        print(f'  {领域:>8}: {数量}')

    print(f'\n领域数: {len(领域统计)}')
    print(f'平均: {len(合并后)/len(领域统计):.0f} 块/领域')

    # 写入JSON
    输出 = {
        '版本': '5.0',
        '领域数': len(领域统计),
        '总块数': len(合并后),
        '块': list(合并后.values()),
    }
    输出路径 = os.path.join(_HERE, '积木库_导出_v5.json')
    with open(输出路径, 'w', encoding='utf-8') as f:
        json.dump(输出, f, ensure_ascii=False, indent=2)
    print(f'\n写入 {输出路径}: {len(合并后)} 块')

    return 合并后, 来源统计


if __name__ == '__main__':
    主流程()