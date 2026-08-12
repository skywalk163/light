# -*- coding: utf-8 -*-
"""将 v5 JSON 导出为 .light 文件"""
import os, json, shutil

_HERE = os.path.dirname(os.path.abspath(__file__))

def 安全文件名(名称):
    安全 = ''
    for c in 名称:
        if c in r'<>:"/\|?*':
            安全 += '_'
        else:
            安全 += c
    return 安全

def 主流程():
    with open(os.path.join(_HERE, '积木库_导出_v5.json'), 'r', encoding='utf-8') as f:
        数据 = json.load(f)

    输出目录 = os.path.join(_HERE, 'blocks_v5')
    if os.path.exists(输出目录):
        shutil.rmtree(输出目录)
    os.makedirs(输出目录)

    写入计数 = 0
    领域目录 = {}
    for 块 in 数据['块']:
        领域 = 块['领域']
        领域路径 = os.path.join(输出目录, 领域)
        if 领域 not in 领域目录:
            os.makedirs(领域路径, exist_ok=True)
            领域目录[领域] = True
        导出名 = 安全文件名(块['导出名'])
        源码 = 块.get('源码', '')
        if 源码:
            文件路径 = os.path.join(领域路径, f'{导出名}.light')
            with open(文件路径, 'w', encoding='utf-8') as f:
                f.write(源码)
            写入计数 += 1

    print(f'写入 {写入计数} 个 .light 文件到 {输出目录}')
    print(f'共 {数据["总块数"]} 块, {数据["领域数"]} 个领域')

if __name__ == '__main__':
    主流程()