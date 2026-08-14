# -*- coding: utf-8 -*-
"""
合并预跑结果到索引.json + 生成发版元数据
==========================================
读取 _预跑结果.json，将逐块通过/失败状态写入索引.json 的每个块，
并生成 _发版元数据.json 用于版本发布。

用法: python _合并预跑索引.py [--dry-run]
  --dry-run: 仅预览变更，不写文件
"""

import os, sys, json, time
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
INDEX_PATH = os.path.join(_HERE, '索引.json')
RESULTS_PATH = os.path.join(_HERE, '_预跑结果.json')
META_PATH = os.path.join(_HERE, '_发版元数据.json')


def _normalize_path(p):
    """统一路径分隔符为 /"""
    return p.replace('\\', '/')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='合并预跑结果到索引')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不写文件')
    args = parser.parse_args()

    # 读取预跑结果
    if not os.path.exists(RESULTS_PATH):
        print(f"[错误] 未找到预跑结果文件: {RESULTS_PATH}")
        print("请先运行 python _预跑.py")
        sys.exit(1)

    with open(RESULTS_PATH, 'r', encoding='utf-8') as f:
        results = json.load(f)

    # 读取索引
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = json.load(f)

    blocks = index.get('块', [])
    print(f"[合并] 索引: {len(blocks)} 块, 预跑结果: {len(results.get('逐块', {}))} 条")

    # 构建预跑结果查找表（路径 → 状态）
    block_results = results.get('逐块', {})
    normalized_results = {}
    for path, status in block_results.items():
        normalized_results[_normalize_path(path)] = status

    # 统计
    update_count = 0
    missing_count = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    by_domain = defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0})

    for block in blocks:
        path = _normalize_path(block.get('路径', ''))
        domain = block.get('领域', '未知')

        if path in normalized_results:
            result = normalized_results[path]
            status = result.get('status', 'skipped')
            error = result.get('error')
            error_msg = result.get('error_msg')

            # 添加预跑字段
            block['预跑通过'] = (status == 'passed')
            block['预跑状态'] = status
            if error and status != 'passed':
                block['预跑错误'] = error
            elif '预跑错误' in block:
                del block['预跑错误']

            update_count += 1
            by_domain[domain]['total'] += 1
            if status == 'passed':
                passed_count += 1
                by_domain[domain]['passed'] += 1
            elif status == 'failed':
                failed_count += 1
                by_domain[domain]['failed'] += 1
            else:
                skipped_count += 1
                by_domain[domain]['skipped'] += 1
        else:
            # 未测试的块，标记为未测试
            block['预跑通过'] = False
            block['预跑状态'] = '未测试'
            if '预跑错误' in block:
                del block['预跑错误']
            missing_count += 1
            by_domain[domain]['total'] += 1
            by_domain[domain]['skipped'] += 1

    # 计算通过率
    total_tested = passed_count + failed_count
    pass_rate = passed_count / max(total_tested, 1) * 100
    total_blocks = len(blocks)

    # 更新索引顶层说明
    index['说明'] = (
        f"光明积木库索引，共 {total_blocks} 块，{len(by_domain)} 个领域。"
        f"预跑通过率: {passed_count}/{total_tested} ({pass_rate:.1f}%)"
    )

    # 输出预览
    print(f"[合并] 已更新: {update_count} 块")
    print(f"[合并] 未测试: {missing_count} 块")
    print(f"[合并] 预跑通过率: {passed_count}/{total_tested} ({pass_rate:.1f}%)")
    print(f"\n按领域统计:")
    print(f"{'领域':12s} {'总数':>6s} {'通过':>6s} {'失败':>6s} {'跳过':>6s} {'通过率':>8s}")
    print('-' * 44)
    for domain in sorted(by_domain.keys()):
        d = by_domain[domain]
        dr = d['passed'] / max(d['total'], 1) * 100
        print(f"{domain:12s} {d['total']:>6d} {d['passed']:>6d} {d['failed']:>6d} {d['skipped']:>6d} {dr:>7.1f}%")

    if args.dry_run:
        print(f"\n[干跑模式] 未写入文件")
        return

    # 写入更新后的索引
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n[合并] 索引已更新: {INDEX_PATH}")

    # ================================================================
    # 生成发版元数据
    # ================================================================
    meta = {
        '版本': index.get('版本', '未知'),
        '生成时间': index.get('生成时间', ''),
        '合并时间': time.strftime('%Y-%m-%d %H:%M:%S'),
        '预跑测试时间': results.get('测试时间', ''),
        '总积木': total_blocks,
        '预跑结果': {
            '通过': passed_count,
            '失败': failed_count,
            '跳过': skipped_count,
            '未测试': missing_count,
            '通过率': f'{pass_rate:.1f}%',
        },
        '按领域': {},
        '失败分类': {},
    }

    for domain in sorted(by_domain.keys()):
        d = by_domain[domain]
        dr = d['passed'] / max(d['total'], 1) * 100
        meta['按领域'][domain] = {
            '总数': d['total'], '通过': d['passed'], '失败': d['failed'],
            '跳过': d['skipped'], '通过率': f'{dr:.1f}%',
        }

    # 统计失败类型
    for path, result in normalized_results.items():
        if result.get('status') == 'failed':
            err = result.get('error', '未知')
            meta['失败分类'][err] = meta['失败分类'].get(err, 0) + 1

    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[合并] 发版元数据已生成: {META_PATH}")


if __name__ == '__main__':
    main()