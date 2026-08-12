# -*- coding: utf-8 -*-
"""
光明积木库导出工具
==================
将积木库导出为干净的 JSON 文件，包含：
  1. 积木完整列表（含所有字段）
  2. 领域统计
  3. 名称索引（方便快速查找）

用法:
  python export_blocks.py                          # 导出到积木库目录
  python export_blocks.py --output 路径/积木库.json  # 指定输出路径
"""

import json, os, sys, argparse
from collections import Counter

_HERE = os.path.abspath(os.path.dirname(__file__))


def 加载索引():
    路径 = os.path.join(_HERE, '索引.json')
    with open(路径, 'r', encoding='utf-8') as f:
        return json.load(f)


def 导出_积木库(输出路径=None):
    索引 = 加载索引()
    块列表 = 索引['块']

    # 领域统计
    领域计数 = Counter(b['领域'] for b in 块列表)
    层级计数 = Counter(b.get('层级', 0) for b in 块列表)
    稳定性计数 = Counter(b.get('稳定性', 'unknown') for b in 块列表)

    # 构建名称 → 块 的快速索引
    名称索引 = {}
    for b in 块列表:
        名称索引[b['名称']] = {
            '领域': b['领域'],
            '层级': b.get('层级', 0),
            '描述': b['描述'],
            '路径': b.get('路径', ''),
            '导出名': b.get('导出名', b['名称']),
            '输入类型': [i['类型'] for i in b.get('输入', [])],
            '输出类型': b.get('输出', {}).get('类型', '?'),
        }

    # 导出的完整结构
    导出 = {
        '版本': 索引.get('版本', '0.2.0'),
        '导出时间': '2026-08-10',
        '统计': {
            '总块数': len(块列表),
            '领域数': len(领域计数),
            '领域分布': dict(领域计数.most_common()),
            '层级分布': dict(层级计数.most_common()),
            '稳定性分布': dict(稳定性计数.most_common()),
            '领域列表': sorted(领域计数.keys()),
        },
        '块': 块列表,
        '名称索引': 名称索引,
    }

    if 输出路径 is None:
        输出路径 = os.path.join(_HERE, '积木库_导出.json')

    with open(输出路径, 'w', encoding='utf-8') as f:
        json.dump(导出, f, ensure_ascii=False, indent=2)

    print(f"积木库已导出到: {输出路径}")
    print(f"总块数: {导出['统计']['总块数']}")
    print(f"领域数: {导出['统计']['领域数']}")
    print(f"领域分布:")
    for 领域, 计数 in 领域计数.most_common():
        print(f"  {领域}: {计数}")
    print(f"层级分布: {dict(层级计数.most_common())}")

    return 导出


def 查找_积木(名称, 输出路径=None):
    """快速查找指定名称的积木"""
    导出 = 导出_积木库(输出路径)
    名称索引 = 导出['名称索引']
    if 名称 in 名称索引:
        print(f"积木: {名称}")
        for k, v in 名称索引[名称].items():
            print(f"  {k}: {v}")
    else:
        # 模糊查找
        print(f"未找到精确匹配「{名称}」，模糊匹配:")
        for n in 名称索引:
            if 名称 in n:
                print(f"  {n}: {名称索引[n]['描述']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='光明积木库导出工具')
    parser.add_argument('--output', '-o', default=None, help='输出路径')
    parser.add_argument('--查找', '-q', default=None, help='查找积木名称')
    args = parser.parse_args()

    if args.查找:
        查找_积木(args.查找, args.output)
    else:
        导出_积木库(args.output)