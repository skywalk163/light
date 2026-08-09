# -*- coding: utf-8 -*-
"""
光明编译器 - 一键运行所有基准测试并生成汇总报告

运行所有基准测试并生成汇总报告（JSON + 控制台输出）。
"""

import sys
import os
import time
import json
import argparse
import subprocess
import importlib
from pathlib import Path
from datetime import datetime

BENCHMARK_DIR = Path(__file__).parent
REPORT_DIR = BENCHMARK_DIR / 'reports'


def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def run_benchmark_script(script_name: str, label: str, extra_args: list = None) -> dict:
    """运行单个基准测试脚本

    Args:
        script_name: 脚本文件名（不含 .py）
        label: 显示名称
        extra_args: 额外命令行参数

    Returns:
        {
            'name': str,
            'status': 'success' | 'skipped' | 'error',
            'elapsed': float,
            'error': str | None,
            'output_path': str | None,
        }
    """
    script_path = BENCHMARK_DIR / f"{script_name}.py"
    if not script_path.exists():
        return {
            'name': label,
            'status': 'skipped',
            'elapsed': 0,
            'error': f"脚本不存在: {script_path}",
            'output_path': None,
        }

    output_path = REPORT_DIR / f"{script_name.replace('benchmark_', '')}.json"
    cmd = [sys.executable, str(script_path), '--output', str(output_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'=' * 80}")
    print(f"▶ 运行: {label}")
    print(f"  命令: {' '.join(cmd)}")
    print(f"{'=' * 80}")

    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = time.perf_counter() - start

        # 打印输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"  STDERR: {result.stderr[:500]}")

        if result.returncode == 0:
            print(f"  ✓ {label} 完成 ({format_time(elapsed)})")
            status = 'success'
            error = None
        else:
            print(f"  ✗ {label} 失败 (返回码 {result.returncode})")
            status = 'error'
            error = result.stderr[:500] if result.stderr else f"返回码: {result.returncode}"

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        print(f"  ⏱ {label} 超时")
        status = 'error'
        error = '执行超时（600秒）'
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  ✗ {label} 错误: {e}")
        status = 'error'
        error = str(e)

    return {
        'name': label,
        'script': script_name,
        'status': status,
        'elapsed': elapsed,
        'error': error,
        'output_path': str(output_path) if status == 'success' else None,
    }


def load_json_report(path: str) -> dict:
    """加载 JSON 报告文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def generate_summary_report(results: list) -> dict:
    """从所有单项报告生成汇总报告"""
    summary = {
        'report_type': 'summary_benchmark',
        'timestamp': datetime.now().isoformat(),
        'benchmarks': results,
        'overall': {},
    }

    # 加载各报告并提取关键指标
    all_summaries = {}
    for r in results:
        if r['status'] == 'success' and r['output_path']:
            report = load_json_report(r['output_path'])
            all_summaries[r['script']] = report.get('summary', {})

    # 计算整体统计
    total_elapsed = sum(r['elapsed'] for r in results)
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')

    summary['overall'] = {
        'total_benchmarks': len(results),
        'success_count': success_count,
        'error_count': error_count,
        'skipped_count': skipped_count,
        'total_elapsed': total_elapsed,
        'all_summaries': all_summaries,
    }

    return summary


def print_summary(results: list, summary: dict):
    """打印汇总报告"""
    print(f"\n{'=' * 80}")
    print(f"📊 光明编译器基准测试汇总报告")
    print(f"{'=' * 80}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # 各测试结果
    print(f"{'基准测试':<30} {'状态':<10} {'耗时':<15}")
    print(f"{'-' * 55}")
    for r in results:
        status_icon = {'success': '✓', 'error': '✗', 'skipped': '—'}.get(r['status'], '?')
        elapsed_str = format_time(r['elapsed']) if r['status'] != 'skipped' else '-'
        print(f"  {r['name']:<28} {status_icon:<10} {elapsed_str:<15}")
        if r['error']:
            print(f"  {'':>30} 错误: {r['error'][:100]}")

    # 整体统计
    print(f"\n{'=' * 80}")
    print("整体统计")
    print(f"{'=' * 80}")
    o = summary['overall']
    print(f"  总基准测试: {o['total_benchmarks']}")
    print(f"  成功: {o['success_count']}")
    print(f"  失败: {o['error_count']}")
    print(f"  跳过: {o['skipped_count']}")
    print(f"  总耗时: {format_time(o['total_elapsed'])}")

    # 报告文件
    print(f"\n报告文件:")
    print(f"  {REPORT_DIR / 'summary_benchmark.json'}")

    # 各单项报告
    print(f"\n单项报告:")
    for r in results:
        if r['output_path']:
            print(f"  {r['name']:<28} → {r['output_path']}")


def main():
    parser = argparse.ArgumentParser(description='光明编译器 - 一键运行所有基准测试')
    parser.add_argument('--skip-compiler', action='store_true', help='跳过编译器速度测试')
    parser.add_argument('--skip-runtime', action='store_true', help='跳过运行时测试')
    parser.add_argument('--skip-memory', action='store_true', help='跳过内存分析')
    parser.add_argument('--skip-hotspot', action='store_true', help='跳过热点分析')
    parser.add_argument('--skip-large', action='store_true', help='跳过大型项目测试')
    parser.add_argument('--skip-legacy', action='store_true', help='跳过原有基准测试')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'summary_benchmark.json'),
                        help='汇总报告输出路径')
    parser.add_argument('--quick', '-q', action='store_true',
                        help='快速模式（跳过大型项目测试和内存泄漏检测）')
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("光明编译器 - 一键运行所有基准测试")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    if args.quick:
        print("快速模式：跳过大型项目测试")
    print()

    # 定义要运行的基准测试
    benchmark_tasks = [
        {
            'script': 'benchmark_compiler',
            'label': '编译器编译速度基准测试',
            'skip': args.skip_compiler,
            'extra_args': ['--no-scale'] if args.quick else None,
        },
        {
            'script': 'benchmark_runtime',
            'label': '运行时性能基准测试',
            'skip': args.skip_runtime,
            'extra_args': None,
        },
        {
            'script': 'benchmark_memory',
            'label': '内存使用分析',
            'skip': args.skip_memory,
            'extra_args': ['--no-leak'] if args.quick else None,
        },
        {
            'script': 'benchmark_hotspot',
            'label': '热点代码优化分析',
            'skip': args.skip_hotspot,
            'extra_args': None,
        },
        {
            'script': 'benchmark_large_project',
            'label': '大项目编译测试',
            'skip': args.skip_large or args.quick,
            'extra_args': None,
        },
    ]

    # 执行所有基准测试
    results = []
    for task in benchmark_tasks:
        if task['skip']:
            results.append({
                'name': task['label'],
                'script': task['script'],
                'status': 'skipped',
                'elapsed': 0,
                'error': '用户跳过',
                'output_path': None,
            })
            print(f"  — 跳过: {task['label']}")
        else:
            result = run_benchmark_script(task['script'], task['label'], task['extra_args'])
            results.append(result)

    # 生成汇总报告
    summary = generate_summary_report(results)

    # 保存汇总报告
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n汇总报告已保存到 {output_path}")

    # 打印汇总
    print_summary(results, summary)

    # 返回退出码
    if any(r['status'] == 'error' for r in results):
        print("\n⚠️ 部分基准测试失败，请查看上述错误信息。")
        sys.exit(1)
    else:
        print("\n✓ 所有基准测试完成！")
        sys.exit(0)


if __name__ == '__main__':
    main()