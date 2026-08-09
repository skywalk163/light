# -*- coding: utf-8 -*-
"""
光明编译器 - 基准测试运行器

测量编译各阶段（词法、解析、代码生成、执行）的性能和内存占用。
支持通过 --run-new 运行新增的专项基准测试。
"""

import sys
import os
import time
import json
import argparse
import subprocess
import tracemalloc
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler


BENCHMARK_DIR = Path(__file__).parent / 'programs'
REPORT_DIR = Path(__file__).parent / 'reports'


def time_it(func, *args, **kwargs):
    """测量函数执行时间，返回 (结果, 耗时秒)"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def mem_it(func, *args, **kwargs):
    """测量函数执行的内存峰值，返回 (结果, 峰值字节)"""
    tracemalloc.start()
    try:
        result = func(*args, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
        return result, peak
    finally:
        tracemalloc.stop()


def run_lexer(source):
    """运行词法分析器"""
    lexer = Lexer()
    tokens = lexer.tokenize(source)
    return tokens


def run_parser(source):
    """运行语法解析器（v3）"""
    parser = V3Parser()
    ast = parser.parse(source)
    return ast


def run_codegen(ast):
    """运行代码生成器"""
    codegen = UnifiedCodeGenerator()
    code = codegen.generate(ast)
    return code


def run_execution(code):
    """运行生成的 Python 代码"""
    exec(code, {})


def benchmark_program(source, name, iterations=3, measure_memory=False):
    """对单个程序进行基准测试"""
    results = {
        'name': name,
        'source_len': len(source),
        'iterations': iterations,
        'lexer': [],
        'parser': [],
        'codegen': [],
        'execution': [],
        'total_compile': [],
        'token_count': 0,
        'memory_lexer': 0,
        'memory_parser': 0,
        'memory_codegen': 0,
        'memory_total': 0,
    }

    for i in range(iterations):
        # 词法分析
        tokens, t_lex = time_it(run_lexer, source)
        results['lexer'].append(t_lex)
        if i == 0:
            results['token_count'] = len(tokens)
            if measure_memory:
                _, mem_lex = mem_it(run_lexer, source)
                results['memory_lexer'] = mem_lex

        # 语法解析（直接传 source，解析器内部会做词法分析）
        ast_raw, t_parse = time_it(run_parser, source)
        results['parser'].append(t_parse)
        if i == 0 and measure_memory:
            _, mem_parse = mem_it(run_parser, source)
            results['memory_parser'] = mem_parse

        # 转换 AST 并生成代码
        from compiler import AstAdapter
        adapter = AstAdapter()
        ast = adapter.convert_module(ast_raw)
        code, t_codegen = time_it(run_codegen, ast)
        results['codegen'].append(t_codegen)
        if i == 0 and measure_memory:
            _, mem_codegen = mem_it(run_codegen, ast)
            results['memory_codegen'] = mem_codegen

        # 编译总时间
        t_total_compile = t_lex + t_parse + t_codegen
        results['total_compile'].append(t_total_compile)
        if i == 0 and measure_memory:
            results['memory_total'] = mem_lex + mem_parse + mem_codegen

        # 执行时间（仅运行一次，避免重复执行副作用）
        if i == 0:
            _, t_exec = time_it(run_execution, code)
            results['execution'].append(t_exec)

    # 计算统计数据
    for key in ['lexer', 'parser', 'codegen', 'total_compile']:
        times = results[key]
        results[key + '_avg'] = sum(times) / len(times)
        results[key + '_min'] = min(times)
        results[key + '_max'] = max(times)

    if results['execution']:
        results['execution_avg'] = results['execution'][0]

    return results


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


def print_results(results_list, show_memory=False):
    """打印基准测试结果表格"""
    print()
    if show_memory:
        print("=" * 130)
        print(f"{'基准测试':<25} {'源码长度':<10} {'词法分析':<12} {'语法解析':<12} {'代码生成':<12} {'编译总计':<12} {'内存(词法)':<12} {'内存(总计)':<12}")
        print("-" * 130)
    else:
        print("=" * 90)
        print(f"{'基准测试':<25} {'源码长度':<10} {'词法分析':<12} {'语法解析':<12} {'代码生成':<12} {'编译总计':<12}")
        print("-" * 90)

    for r in results_list:
        name = r['name'][:24]
        src_len = f"{r['source_len']} B"
        t_lex = format_time(r['lexer_avg'])
        t_parse = format_time(r['parser_avg'])
        t_codegen = format_time(r['codegen_avg'])
        t_total = format_time(r['total_compile_avg'])
        
        if show_memory:
            m_lex = format_memory(r.get('memory_lexer', 0))
            m_total = format_memory(r.get('memory_total', 0))
            print(f"{name:<25} {src_len:<10} {t_lex:<12} {t_parse:<12} {t_codegen:<12} {t_total:<12} {m_lex:<12} {m_total:<12}")
        else:
            print(f"{name:<25} {src_len:<10} {t_lex:<12} {t_parse:<12} {t_codegen:<12} {t_total:<12}")

    if show_memory:
        print("=" * 130)
    else:
        print("=" * 90)

    # 执行时间
    print()
    print("执行时间（仅运行一次）：")
    print("-" * 40)
    for r in results_list:
        if r.get('execution'):
            print(f"  {r['name']:<25} {format_time(r['execution_avg'])}")
    print()

    # Token 统计
    print("Token 统计：")
    print("-" * 40)
    for r in results_list:
        if r.get('token_count'):
            print(f"  {r['name']:<25} {r['token_count']} 个")
    print()


NEW_BENCHMARKS = [
    ('benchmark_compiler', '编译器编译速度基准测试'),
    ('benchmark_runtime', '运行时性能基准测试'),
    ('benchmark_memory', '内存使用分析'),
    ('benchmark_hotspot', '热点代码优化分析'),
    ('benchmark_large_project', '大项目编译测试'),
]


def run_new_benchmark(script_name, label):
    """运行新增的专项基准测试"""
    script_path = Path(__file__).parent / f"{script_name}.py"
    if not script_path.exists():
        print(f"  — 跳过 {label}，脚本不存在: {script_path}")
        return

    output_path = REPORT_DIR / f"{script_name.replace('benchmark_', '')}.json"
    cmd = [sys.executable, str(script_path), '--output', str(output_path)]

    print(f"\n▶ 运行: {label}")
    print(f"  命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.stdout:
            # 只打印最后几行
            lines = result.stdout.strip().split('\n')
            for line in lines[-5:]:
                print(f"  {line}")
        if result.returncode == 0:
            print(f"  ✓ {label} 完成，报告: {output_path}")
        else:
            print(f"  ✗ {label} 失败 (返回码 {result.returncode})")
            if result.stderr:
                print(f"  错误: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print(f"  ⏱ {label} 超时")
    except Exception as e:
        print(f"  ✗ {label} 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='光明编译器基准测试')
    parser.add_argument('--program', '-p', help='只运行指定基准程序')
    parser.add_argument('--iterations', '-n', type=int, default=3, help='迭代次数（默认3）')
    parser.add_argument('--json', '-j', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--output', '-o', help='将结果保存到文件')
    parser.add_argument('--mem', '-m', action='store_true', help='测量内存占用（会降低性能）')
    # 新增参数：运行专项基准测试
    parser.add_argument('--run-new', '-r', nargs='*', choices=['all'] + [n for n, _ in NEW_BENCHMARKS],
                        help='运行新增的专项基准测试（指定名称，或 all 运行全部）')
    parser.add_argument('--list-new', action='store_true', help='列出所有可用的专项基准测试')
    args = parser.parse_args()

    # 如果只是列出专项基准测试
    if args.list_new:
        print("可用的专项基准测试：")
        for name, label in NEW_BENCHMARKS:
            print(f"  {name}: {label}")
        return

    # 运行专项基准测试（如果指定了 --run-new）
    if args.run_new is not None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        if 'all' in args.run_new:
            targets = NEW_BENCHMARKS
        else:
            targets = [(n, l) for n, l in NEW_BENCHMARKS if n in args.run_new]

        print(f"光明编译器专项基准测试 - {len(targets)} 个测试")
        print("=" * 60)
        for name, label in targets:
            run_new_benchmark(name, label)
        return

    # 原有逻辑：运行 benchmarks/programs/ 中的基准测试
    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))

    if args.program:
        bench_files = [f for f in bench_files if args.program in f.name]
        if not bench_files:
            print(f"未找到包含 '{args.program}' 的基准测试程序")
            sys.exit(1)

    if not bench_files:
        print(f"在 {BENCHMARK_DIR} 中未找到基准测试程序")
        sys.exit(1)

    print(f"光明编译器基准测试 - {len(bench_files)} 个程序，每个迭代 {args.iterations} 次")
    if args.mem:
        print("（已启用内存测量）")
    print()

    results_list = []

    for bench_file in bench_files:
        name = bench_file.stem
        print(f"运行 {name} ...", end=' ', flush=True)

        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            results = benchmark_program(source, name, args.iterations, measure_memory=args.mem)
            results_list.append(results)
            print(f"✓ ({format_time(results['total_compile_avg'])})")
        except Exception as e:
            print(f"✗ 错误: {e}")

    # 输出结果
    if args.json:
        output = json.dumps(results_list, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"结果已保存到 {args.output}")
        else:
            print()
            print(output)
    else:
        print_results(results_list, show_memory=args.mem)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results_list, f, indent=2, ensure_ascii=False)
            print(f"结果已保存到 {args.output}")

    # 提示可以运行专项基准测试
    if not args.run_new:
        print()
        print("提示：使用 --run-new all 可运行新增加的专项基准测试")
        print("      使用 --list-new 可查看所有可用的专项基准测试")


if __name__ == '__main__':
    main()
