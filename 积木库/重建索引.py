# -*- coding: utf-8 -*-
"""重建索引.json：从 积木库_导出_v4.json 生成标准的索引.json

索引.json 字段:
  名称, 领域, 层级, 描述, 输入, 输出, 稳定性, 路径, 导出名

积木库_导出_v4.json 中有:
  名称, 领域, 导出名, 描述, 输入, 输出, 稳定性, 源码
"""

import json
import os

_HERE = os.path.abspath(os.path.dirname(__file__))

def _find_file_in_blocks(name, blocks_v5):
    """在 blocks_v5 所有子目录中搜索 name.light，返回 (领域, 相对路径) 或 None"""
    for area in os.listdir(blocks_v5):
        ap = os.path.join(blocks_v5, area, name + '.light')
        if os.path.exists(ap):
            return area, f'{area}/{name}.light'
    return None

def _generate_stub(name, domain, desc, v5_dir):
    """为缺失的块生成桩 .light 文件"""
    area_dir = os.path.join(v5_dir, domain)
    os.makedirs(area_dir, exist_ok=True)
    path = os.path.join(area_dir, name + '.light')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'# 积木：{name}（{domain}领域，自动生成桩）\n')
        f.write(f'# 契约：{desc}\n')
        f.write(f'导出 {name}\n')
        f.write(f'段落 {name} 接收 输入：\n')
        f.write(f'    # TODO: 实现 {name}\n')
        f.write(f'    返回 输入\n')
    return f'{domain}/{name}.light'

def main():
    v4_path = os.path.join(_HERE, '积木库_导出_v4.json')
    idx_path = os.path.join(_HERE, '索引.json')
    blocks_v5 = os.path.join(_HERE, 'blocks_v5')

    with open(v4_path, 'r', encoding='utf-8') as f:
        v4 = json.load(f)

    # 加载旧索引以保留层级信息
    old_idx = {}
    old_path = os.path.join(_HERE, '索引.json')
    if os.path.exists(old_path):
        with open(old_path, 'r', encoding='utf-8') as f:
            old = json.load(f)
        for b in old.get('块', []):
            old_idx[b['名称']] = b

    blocks = v4.get('块', [])
    print(f'[加载] 积木库_导出_v4.json: {len(blocks)} 个块')

    new_blocks = []
    fixed_domain = []
    generated_stubs = []

    for b in blocks:
        name = b['名称']
        domain = v4_domain = b['领域']
        rel_path = f'{domain}/{name}.light'
        full_path = os.path.join(blocks_v5, rel_path)

        # 保留旧索引中的层级
        old_entry = old_idx.get(name)
        level = 0
        if old_entry:
            level = old_entry.get('层级', 0)

        # 查找文件
        if os.path.exists(full_path):
            final_path = rel_path
        else:
            result = _find_file_in_blocks(name, blocks_v5)
            if result:
                actual_domain, final_path = result
                if actual_domain != v4_domain:
                    fixed_domain.append((name, v4_domain, actual_domain))
                    domain = actual_domain
            else:
                # 生成桩文件
                desc = b.get('描述', f'计算{name}')
                final_path = _generate_stub(name, v4_domain, desc, blocks_v5)
                generated_stubs.append((name, v4_domain))

        new_block = {
            '名称': name,
            '领域': domain,
            '层级': level,
            '描述': b.get('描述', ''),
            '输入': b.get('输入', []),
            '输出': b.get('输出', {'类型': '空'}),
            '稳定性': b.get('稳定性', 'generated'),
            '路径': final_path,
            '导出名': b.get('导出名', name),
        }
        new_blocks.append(new_block)

    # 统计
    areas = {}
    for b in new_blocks:
        a = b['领域']
        areas[a] = areas.get(a, 0) + 1

    new_index = {
        '版本': 'v5.1',
        '生成时间': '2026-08-11',
        '说明': f'光明积木库索引，共 {len(new_blocks)} 块，{len(areas)} 个领域。从积木库_导出_v4.json 重建。',
        '块': new_blocks,
    }

    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(new_index, f, ensure_ascii=False, indent=2)

    print(f'\n[写入] 索引.json: {len(new_blocks)} 块，{len(areas)} 个领域')
    print(f'\n领域分布:')
    for a, n in sorted(areas.items(), key=lambda x: -x[1]):
        print(f'  {a}: {n}')

    if fixed_domain:
        print(f'\n⚠ 修正领域不一致的块 ({len(fixed_domain)} 个):')
        for name, old_d, new_d in fixed_domain:
            print(f'  {name}: {old_d} → {new_d}')

    if generated_stubs:
        print(f'\n🆕 生成桩文件的块 ({len(generated_stubs)} 个):')
        for name, d in generated_stubs:
            print(f'  {d}/{name}.light')

    print('\n✅ 重建完成')


if __name__ == '__main__':
    main()