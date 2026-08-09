# -*- coding: utf-8 -*-
"""
光明编译器 - 内存使用分析基准测试

测试内容：
1. 使用 tracemalloc 追踪解析/编译/执行各阶段内存使用
2. 分析大文件编译的内存峰值
3. 输出内存分析报告（JSON格式）
"""

import sys
import os
import time
import json
import argparse
import tracemalloc
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler, AstAdapter

BENCHMARK_DIR = Path(__file__).parent / 'programs'
REPORT_DIR = Path(__file__).parent / 'reports'


def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def format_memory(bytes_size):
    """格式化内存大小显示"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def mem_it(func, *args, **kwargs):
    """测量函数执行的内存峰值，返回 (结果, 峰值字节, 当前使用字节)"""
    tracemalloc.start()
    try:
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        return result, peak, current
    finally:
        tracemalloc.stop()


def time_and_mem(func, *args, **kwargs):
    """同时测量时间和内存，返回 (结果, 耗时秒, 峰值字节)"""
    tracemalloc.start()
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        return result, elapsed, peak
    finally:
        tracemalloc.stop()


# =============================================================================
# 各阶段内存分析
# =============================================================================

def analyze_phase_memory(source, name):
    """分析编译各阶段的内存使用"""
    result = {
        'name': name,
        'source_len': len(source),
        'phases': {},
    }

    # 词法分析阶段
    lexer = Lexer()
    tokens, t_lex, m_lex = time_and_mem(lexer.tokenize, source)
    result['phases']['lexer'] = {
        'time': t_lex,
        'peak_memory': m_lex,
        'token_count': len(tokens),
    }

    # 语法解析阶段
    parser = V3Parser()
    ast_raw, t_parse, m_parse = time_and_mem(parser.parse, source)
    result['phases']['parser'] = {
        'time': t_parse,
        'peak_memory': m_parse,
    }

    # AST 适配阶段
    adapter = AstAdapter()
    ast, t_adapter, m_adapter = time_and_mem(adapter.convert_module, ast_raw)
    result['phases']['adapter'] = {
        'time': t_adapter,
        'peak_memory': m_adapter,
    }

    # 代码生成阶段
    codegen = UnifiedCodeGenerator()
    code, t_codegen, m_codegen = time_and_mem(codegen.generate, ast)
    result['phases']['codegen'] = {
        'time': t_codegen,
        'peak_memory': m_codegen,
        'generated_size': len(code),
    }

    # 总计
    result['total_time'] = t_lex + t_parse + t_adapter + t_codegen
    result['peak_memory'] = max(m_lex, m_parse, m_adapter, m_codegen)
    result['generated_code_size'] = len(code)

    return result


def benchmark_phase_memory():
    """分析现有基准程序各阶段内存使用"""
    print("=" * 80)
    print("1. 编译各阶段内存使用分析")
    print("=" * 80)

    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))
    results = []

    for bench_file in bench_files:
        name = bench_file.stem
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"  分析 {name} ... ", end='', flush=True)
        try:
            phase_result = analyze_phase_memory(source, name)
            results.append(phase_result)
            print(f"✓ 峰值内存: {format_memory(phase_result['peak_memory'])}")
        except Exception as e:
            print(f"✗ 错误: {e}")

    return results


# =============================================================================
# 大文件内存压力测试
# =============================================================================

def generate_large_source(size_kb):
    """生成指定大小的光明源代码用于内存压力测试"""
    lines = []
    # 填充大量变量声明和表达式
    for i in range(size_kb * 10):  # 大约每10行产生1KB
        lines.append(f"设 变量{i} 为 {i} 加 {i * 2} 减 {i // 2} 乘 3")
    lines.append(f"打印 变量{size_kb * 10 - 1}")
    return "\n".join(lines)


def benchmark_large_file_memory():
    """分析大文件编译的内存峰值"""
    print("\n" + "=" * 80)
    print("2. 大文件编译内存压力测试")
    print("=" * 80)

    sizes = [10, 50, 100, 200]  # KB
    results = []

    for size_kb in sizes:
        print(f"  生成 {size_kb}KB 源代码 ... ", end='', flush=True)
        source = generate_large_source(size_kb)
        actual_size_kb = len(source) / 1024
        print(f"实际 {actual_size_kb:.1f}KB")

        print(f"  编译大文件 ({size_kb}KB) ... ", end='', flush=True)
        try:
            phase_result = analyze_phase_memory(source, f"大文件_{size_kb}KB")
            results.append(phase_result)

            peak = phase_result['peak_memory']
            ratio = peak / len(source)  # 内存/源码比例
            print(f"✓ 峰值内存: {format_memory(peak)} (比率: {ratio:.2f}x)")
        except Exception as e:
            print(f"✗ 错误: {e}")
            results.append({
                'name': f"大文件_{size_kb}KB",
                'source_len': len(source),
                'error': str(e),
            })

    return results


# =============================================================================
# 内存泄漏检测
# =============================================================================

def benchmark_memory_leak():
    """检测重复编译是否有内存泄漏趋势"""
    print("\n" + "=" * 80)
    print("3. 重复编译内存泄漏检测")
    print("=" * 80)

    # 使用一个中等大小的源代码
    source = generate_large_source(50)  # 50KB

    iterations = 10
    peak_memories = []

    print(f"  重复编译 {iterations} 次（50KB 源码）...")

    for i in range(iterations):
        # 清除 tracemalloc 的累积数据
        tracemalloc.start()

        try:
            start = time.perf_counter()
            compiler = LightCompiler()
            result = compiler.compile(source)
            elapsed = time.perf_counter() - start

            _, peak = tracemalloc.get_traced_memory()
            peak_memories.append(peak)
            print(f"    第 {i + 1:2d} 次: 编译={format_time(elapsed)}, 峰值内存={format_memory(peak)}")
        except Exception as e:
            print(f"    第 {i + 1:2d} 次: ✗ 错误: {e}")
        finally:
            tracemalloc.stop()

    # 分析趋势
    if len(peak_memories) >= 3:
        first_half = peak_memories[:len(peak_memories) // 2]
        second_half = peak_memories[len(peak_memories) // 2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        trend = avg_second - avg_first
        has_leak = trend > avg_first * 0.2  # 后半段比前半段高20%以上视为泄漏

        result = {
            'iterations': iterations,
            'source_size': len(source),
            'peak_memories': peak_memories,
            'avg_first_half': avg_first,
            'avg_second_half': avg_second,
            'memory_trend_bytes': trend,
            'has_memory_leak': has_leak,
        }

        print(f"\n  内存泄漏检测: {'⚠️ 发现泄漏趋势' if has_leak else '✓ 无泄漏迹象'}")
        print(f"    前半段平均: {format_memory(avg_first)}")
        print(f"    后半段平均: {format_memory(avg_second)}")
        print(f"    差异: {format_memory(trend)}")

        return result

    return None


def generate_report(phase_results, large_file_results, leak_result, output_path):
    """生成结构化 JSON 报告"""
    report = {
        'report_type': 'memory_benchmark',
        'timestamp': datetime.now().isoformat(),
        'phase_analysis': phase_results,
        'large_file_analysis': large_file_results,
        'memory_leak_analysis': leak_result,
        'summary': {},
    }

    # 计算汇总
    summary = {}

    if phase_results:
        avg_peak = sum(r['peak_memory'] for r in phase_results) / len(phase_results)
        max_peak = max(r['peak_memory'] for r in phase_results)
        max_peak_program = max(phase_results, key=lambda r: r['peak_memory'])['name']
        summary['phase_analysis'] = {
            'program_count': len(phase_results),
            'avg_peak_memory': avg_peak,
            'max_peak_memory': max_peak,
            'max_peak_program': max_peak_program,
        }

        # 各阶段平均内存
        avg_lexer_mem = sum(r['phases']['lexer']['peak_memory'] for r in phase_results) / len(phase_results)
        avg_parser_mem = sum(r['phases']['parser']['peak_memory'] for r in phase_results) / len(phase_results)
        avg_codegen_mem = sum(r['phases']['codegen']['peak_memory'] for r in phase_results) / len(phase_results)
        summary['avg_phase_memory'] = {
            'lexer': avg_lexer_mem,
            'parser': avg_parser_mem,
            'codegen': avg_codegen_mem,
        }

    if large_file_results:
        valid_results = [r for r in large_file_results if 'error' not in r]
        if valid_results:
            avg_large_peak = sum(r['peak_memory'] for r in valid_results) / len(valid_results)
            avg_large_ratio = sum(r['peak_memory'] / r['source_len'] for r in valid_results) / len(valid_results)
            summary['large_file'] = {
                'test_count': len(valid_results),
                'avg_peak_memory': avg_large_peak,
                'avg_memory_to_source_ratio': avg_large_ratio,
            }

    report['summary'] = summary

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到 {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description='光明编译器内存使用分析基准测试')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'memory_benchmark.json'),
                        help='JSON 报告输出路径')
    parser.add_argument('--no-phase', action='store_true', help='跳过各阶段内存分析')
    parser.add_argument('--no-large', action='store_true', help='跳过大型文件测试')
    parser.add_argument('--no-leak', action='store_true', help='跳过内存泄漏检测')
    args = parser.parse_args()

    print("光明编译器 - 内存使用分析基准测试")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    phase_results = None
    large_file_results = None
    leak_result = None

    if not args.no_phase:
        phase_results = benchmark_phase_memory()

    if not args.no_large:
        large_file_results = benchmark_large_file_memory()

    if not args.no_leak:
        leak_result = benchmark_memory_leak()

    # 生成报告
    report = generate_report(phase_results, large_file_results, leak_result, args.output)

    print("\n" + "=" * 80)
    print("内存使用分析基准测试完成！")
    print("=" * 80)

    return report


if __name__ == '__main__':
    main()