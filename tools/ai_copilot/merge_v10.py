"""
段言 SFT 数据集合并脚本

将 v10 数据集 (sft_dataset_v10.jsonl) 合并到主数据集 (sft_dataset.jsonl) 中。
合并逻辑：
1. 备份主数据集
2. 读取两个数据集，按 (input, output) 对去重
3. 打乱顺序
4. 写入主数据集
5. 打印统计信息
"""

import json
import os
import shutil
import random
from collections import Counter, defaultdict

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_V9_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset.jsonl')
_V10_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset_v10.jsonl')
_BACKUP_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset.jsonl.bak')


def load_jsonl(path: str) -> list:
    """加载 JSONL 文件"""
    entries = []
    if not os.path.exists(path):
        print(f"  警告: 文件不存在 {path}")
        return entries
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  警告: 忽略无效 JSON 行: {e}")
    return entries


def save_jsonl(entries: list, path: str):
    """保存条目到 JSONL 文件"""
    with open(path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def compute_stats(entries: list) -> dict:
    """计算统计信息"""
    total = len(entries)
    category_counter = Counter()
    input_lengths = []
    output_lengths = []

    for entry in entries:
        cat = entry.get('category', '未分类')
        category_counter[cat] += 1
        inp = entry.get('input', '')
        out = entry.get('output', '')
        input_lengths.append(len(inp))
        output_lengths.append(len(out))

    return {
        'total': total,
        'categories': dict(category_counter.most_common()),
        'input_len': {
            'min': min(input_lengths) if input_lengths else 0,
            'max': max(input_lengths) if input_lengths else 0,
            'avg': round(sum(input_lengths) / len(input_lengths), 1) if input_lengths else 0,
        },
        'output_len': {
            'min': min(output_lengths) if output_lengths else 0,
            'max': max(output_lengths) if output_lengths else 0,
            'avg': round(sum(output_lengths) / len(output_lengths), 1) if output_lengths else 0,
        },
    }


def print_stats(stats: dict, label: str):
    """打印统计信息"""
    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print(f"{'=' * 50}")
    print(f"  总条目数: {stats['total']}")
    print(f"\n  按类别分布:")
    for cat, count in stats['categories'].items():
        print(f"    {cat:<12s}: {count:>5d} 条")
    print(f"\n  输入长度: 最短 {stats['input_len']['min']} / 最长 {stats['input_len']['max']} / 平均 {stats['input_len']['avg']}")
    print(f"  输出长度: 最短 {stats['output_len']['min']} / 最长 {stats['output_len']['max']} / 平均 {stats['output_len']['avg']}")


def main():
    print("=" * 50)
    print("  v10 数据集合并工具")
    print("=" * 50)

    # 1. 加载数据
    print("\n[1] 加载数据集...")
    v9_entries = load_jsonl(_V9_PATH)
    v10_entries = load_jsonl(_V10_PATH)
    print(f"  v9 数据集 (原): {len(v9_entries)} 条")
    print(f"  v10 数据集: {len(v10_entries)} 条")

    # 2. 备份原始 v9 数据集
    print("\n[2] 备份原始数据集...")
    if os.path.exists(_V9_PATH):
        shutil.copy2(_V9_PATH, _BACKUP_PATH)
        print(f"  已备份到: {_BACKUP_PATH}")

    # 3. 去重 (按 (input, output) 对)
    print("\n[3] 去重合并...")
    seen_pairs = set()
    merged = []
    duplicate_count = 0

    for entry in v9_entries:
        key = (entry.get('input', ''), entry.get('output', ''))
        if key not in seen_pairs:
            seen_pairs.add(key)
            merged.append(entry)
        else:
            duplicate_count += 1

    for entry in v10_entries:
        key = (entry.get('input', ''), entry.get('output', ''))
        if key not in seen_pairs:
            seen_pairs.add(key)
            merged.append(entry)
        else:
            duplicate_count += 1

    print(f"  v9 保留: {len(v9_entries)} 条")
    print(f"  v10 新增: {len(merged) - len(v9_entries)} 条")
    print(f"  去重移除: {duplicate_count} 条 (v10 内重复 + v9 已有)")
    print(f"  合并后总计: {len(merged)} 条")

    # 4. 打乱
    print("\n[4] 打乱数据集...")
    random.seed(42)
    random.shuffle(merged)
    print(f"  已完成")

    # 5. 写入主数据集
    print("\n[5] 写入主数据集...")
    save_jsonl(merged, _V9_PATH)
    print(f"  已写入: {_V9_PATH}")

    # 6. 输出统计
    stats = compute_stats(merged)
    print_stats(stats, "合并后数据集统计")

    print(f"\n{'=' * 50}")
    print("  合并完成!")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    main()