# -*- coding: utf-8 -*-
"""
光明编译器 - 编译器编译速度基准测试

测试内容：
1. 不同规模代码的编译时间（解析→AST→代码生成）
2. 增量编译 vs 全量编译速度对比
3. 不同优化级别（O0/O1/O2/O3）的编译时间
4. 输出结构化报告（JSON格式）
"""

import sys
import os
import time
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler, AstAdapter

# 导入优化器
from optimizer import (
    ConstantFoldingOptimizer,
    DeadCodeEliminationOptimizer,
    LoopInvariantOptimizer,
    PeepholeOptimizer,
    CommonSubexpressionEliminationOptimizer,
    InlineOptimizer,
)

BENCHMARK_DIR = Path(__file__).parent / 'programs'
REPORT_DIR = Path(__file__).parent / 'reports'


def time_it(func, *args, **kwargs):
    """测量函数执行时间，返回 (结果, 耗时秒)"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


# =============================================================================
# 优化级别定义
# =============================================================================

# 各优化级别对应的优化器列表
OPT_LEVELS = {
    'O0': [],  # 无优化
    'O1': [PeepholeOptimizer, ConstantFoldingOptimizer],  # 基本优化
    'O2': [PeepholeOptimizer, ConstantFoldingOptimizer, DeadCodeEliminationOptimizer,
           CommonSubexpressionEliminationOptimizer],  # 中等优化
    'O3': [PeepholeOptimizer, ConstantFoldingOptimizer, DeadCodeEliminationOptimizer,
           CommonSubexpressionEliminationOptimizer, LoopInvariantOptimizer,
           InlineOptimizer],  # 激进优化
}


def apply_optimizations(module, opt_level):
    """对模块应用指定级别的优化"""
    if opt_level not in OPT_LEVELS or opt_level == 'O0':
        return module, []

    optimizer_classes = OPT_LEVELS[opt_level]
    optimizer_stats = []
    module_copy = module

    for opt_cls in optimizer_classes:
        optimizer = opt_cls()
        module_copy = optimizer.optimize_with_stats(module_copy)
        if optimizer.stats:
            optimizer_stats.append(optimizer.stats.to_dict())

    return module_copy, optimizer_stats


def generate_source_variants():
    """生成不同规模的源代码用于编译速度测试

    基于现有的基准程序，生成更大规模的变体。
    """
    variants = {}

    # 1. 基于 many_functions.light 生成不同函数数量的版本
    for n in [10, 50, 100, 200]:
        lines = []
        for i in range(n):
            lines.append(f"段落 函数{i}：\n  返回 {i}")
        lines.append(f"\n设 结果 为 函数{n - 1}\n打印 结果")
        variants[f"函数_{n}个"] = "\n".join(lines)

    # 2. 基于 large_expressions.light 生成不同表达式长度的版本
    for n in [10, 50, 100]:
        parts = ["设 x 为 1"]
        for i in range(n):
            parts.append(f"设 y{i} 为 x 加 {i} 乘 2 减 1 加 x 乘 {i} 减 2")
        parts.append(f"打印 y{n - 1}")
        variants[f"表达式_{n}行"] = "\n".join(parts)

    # 3. 深度嵌套
    def gen_nested_if(depth):
        lines = ["段落 嵌套 接收 n："]

        def gen_ifs(current, max_depth):
            indent = "  " * (current + 1)
            if current >= max_depth:
                return [f"{indent}返回 n"]
            result = [f"{indent}如果 n 大于 {current} 那么："]
            result.extend(gen_ifs(current + 1, max_depth))
            return result

        lines.extend(gen_ifs(0, depth))
        lines.append(f"\n设 结果 为 嵌套(10)\n打印 结果")
        return "\n".join(lines)

    for n in [10, 20, 30]:
        variants[f"嵌套_{n}层"] = gen_nested_if(n)

    # 4. 大循环
    for n in [1000, 10000, 50000]:
        lines = [
            f"设 总和 为 0",
            f"设 i 为 0",
            f"当 i 小于 {n}：",
            f"  总和 为 总和 加 i",
            f"  i 为 i 加 1",
            f"打印 总和",
        ]
        variants[f"循环_{n}次"] = "\n".join(lines)

    return variants


def benchmark_compile_scale():
    """测试不同规模代码的编译时间"""
    print("=" * 80)
    print("1. 不同规模代码编译时间测试")
    print("=" * 80)

    variants = generate_source_variants()
    results = []

    for name, source in variants.items():
        print(f"  测试 {name} ... ", end='', flush=True)
        source_len = len(source)

        # 多次迭代取平均
        times = []
        for _ in range(3):
            # 词法分析
            lexer = Lexer()
            tokens, t_lex = time_it(lexer.tokenize, source)

            # 语法解析
            parser = V3Parser()
            ast_raw, t_parse = time_it(parser.parse, source)

            # AST 适配
            adapter = AstAdapter()
            ast, t_adapter = time_it(adapter.convert_module, ast_raw)

            # 代码生成
            codegen = UnifiedCodeGenerator()
            code, t_codegen = time_it(codegen.generate, ast)

            # 编译总时间
            t_total = t_lex + t_parse + t_adapter + t_codegen
            times.append({
                'lexer': t_lex,
                'parser': t_parse,
                'adapter': t_adapter,
                'codegen': t_codegen,
                'total': t_total,
                'token_count': len(tokens),
            })

        # 计算平均
        avg = {k: sum(t[k] for t in times) / len(times) for k in times[0]}
        result = {
            'name': name,
            'source_len': source_len,
            'iterations': 3,
            **avg,
        }
        results.append(result)
        print(f"✓ 编译总计 {format_time(avg['total'])} ({avg['token_count']} tokens)")

    return results


def benchmark_incremental_vs_full():
    """测试增量编译 vs 全量编译速度对比"""
    print("\n" + "=" * 80)
    print("2. 增量编译 vs 全量编译速度对比")
    print("=" * 80)

    # 构造测试场景：多段代码模拟多文件项目
    modules = {}
    for i in range(20):
        modules[f"模块{i}"] = f"""
段落 函数{i} 接收 x：
  返回 x 加 {i}

段落 入口{i}：
  设 结果 为 函数{i}(100)
  打印 结果
"""
    # 主模块依赖所有子模块
    main_module = "\n\n".join(modules.values())

    print(f"  测试项目：20个模块，总大小 {len(main_module)} 字符")

    # 全量编译
    print("  全量编译 ... ", end='', flush=True)
    full_times = []
    for _ in range(3):
        compiler = LightCompiler()
        _, t = time_it(compiler.compile, main_module)
        full_times.append(t)
    full_avg = sum(full_times) / len(full_times)
    print(f"✓ 平均 {format_time(full_avg)}")

    # 模拟增量编译（只编译新增/修改的模块）
    print("  增量编译（修改1个模块） ... ", end='', flush=True)
    inc_times = []
    for _ in range(3):
        # 模拟增量：只编译修改过的模块
        modified = modules["模块0"]
        modified = modified.replace("返回 x 加 0", "返回 x 加 100")

        compiler = LightCompiler()
        _, t = time_it(compiler.compile, modified)
        inc_times.append(t)
    inc_avg = sum(inc_times) / len(inc_times)
    print(f"✓ 平均 {format_time(inc_avg)}")

    # 模拟增量编译（修改一半模块）
    print("  增量编译（修改10个模块） ... ", end='', flush=True)
    inc_half_times = []
    for _ in range(3):
        half_modules = {}
        for i in range(20):
            if i < 10:
                half_modules[f"模块{i}"] = modules[f"模块{i}"].replace(
                    f"返回 x 加 {i}", f"返回 x 加 {i * 2}"
                )
            else:
                half_modules[f"模块{i}"] = modules[f"模块{i}"]

        half_source = "\n\n".join(half_modules.values())
        compiler = LightCompiler()
        _, t = time_it(compiler.compile, half_source)
        inc_half_times.append(t)
    inc_half_avg = sum(inc_half_times) / len(inc_half_times)
    print(f"✓ 平均 {format_time(inc_half_avg)}")

    results = {
        'project_size': len(main_module),
        'module_count': 20,
        'full_compile_avg': full_avg,
        'incremental_single_avg': inc_avg,
        'incremental_half_avg': inc_half_avg,
        'speedup_single': full_avg / inc_avg if inc_avg > 0 else 0,
        'speedup_half': full_avg / inc_half_avg if inc_half_avg > 0 else 0,
    }

    print(f"\n  速度提升（修改1个模块）: {results['speedup_single']:.1f}x")
    print(f"  速度提升（修改10个模块）: {results['speedup_half']:.1f}x")

    return results


def benchmark_optimization_levels():
    """测试不同优化级别的编译时间和代码质量"""
    print("\n" + "=" * 80)
    print("3. 不同优化级别（O0/O1/O2/O3）的编译时间")
    print("=" * 80)

    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))
    all_results = []

    for bench_file in bench_files:
        name = bench_file.stem
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"  测试 {name}:")
        level_results = {'name': name, 'source_len': len(source), 'levels': {}}

        for opt_level in ['O0', 'O1', 'O2', 'O3']:
            # 编译各阶段计时
            lexer = Lexer()
            tokens, t_lex = time_it(lexer.tokenize, source)

            parser = V3Parser()
            ast_raw, t_parse = time_it(parser.parse, source)

            adapter = AstAdapter()
            ast, t_adapter = time_it(adapter.convert_module, ast_raw)

            # 应用优化
            optimized_ast, opt_stats = apply_optimizations(ast, opt_level)
            t_opt = sum(s.get('elapsed', 0) for s in opt_stats)

            # 代码生成
            codegen = UnifiedCodeGenerator()
            code, t_codegen = time_it(codegen.generate, optimized_ast)

            t_total = t_lex + t_parse + t_adapter + t_opt + t_codegen
            generated_size = len(code)

            entry = {
                'lexer': t_lex,
                'parser': t_parse,
                'adapter': t_adapter,
                'optimization': t_opt,
                'codegen': t_codegen,
                'total': t_total,
                'generated_size': generated_size,
                'optimizer_stats': opt_stats,
            }
            level_results['levels'][opt_level] = entry
            print(f"    {opt_level}: {format_time(t_total)} (生成 {generated_size} 字符)")

        all_results.append(level_results)

    return all_results


def generate_report(scale_results, inc_results, opt_results, output_path):
    """生成结构化 JSON 报告"""
    report = {
        'report_type': 'compiler_benchmark',
        'timestamp': datetime.now().isoformat(),
        'summary': {},
        'scale_benchmark': scale_results,
        'incremental_benchmark': inc_results,
        'optimization_level_benchmark': opt_results,
    }

    # 计算汇总
    if scale_results:
        avg_compile = sum(r['total'] for r in scale_results) / len(scale_results)
        total_source = sum(r['source_len'] for r in scale_results)
        report['summary'] = {
            'total_programs': len(scale_results),
            'avg_compile_time': avg_compile,
            'total_source_size': total_source,
            'fastest_program': min(scale_results, key=lambda r: r['total'])['name'],
            'slowest_program': max(scale_results, key=lambda r: r['total'])['name'],
        }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到 {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description='光明编译器编译速度基准测试')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'compiler_benchmark.json'),
                        help='JSON 报告输出路径')
    parser.add_argument('--no-scale', action='store_true', help='跳过规模测试')
    parser.add_argument('--no-incremental', action='store_true', help='跳过增量编译测试')
    parser.add_argument('--no-opt-levels', action='store_true', help='跳过优化级别测试')
    args = parser.parse_args()

    print("光明编译器 - 编译速度基准测试")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    scale_results = None
    inc_results = None
    opt_results = None

    if not args.no_scale:
        scale_results = benchmark_compile_scale()

    if not args.no_incremental:
        inc_results = benchmark_incremental_vs_full()

    if not args.no_opt_levels:
        opt_results = benchmark_optimization_levels()

    # 生成报告
    report = generate_report(scale_results, inc_results, opt_results, args.output)

    print("\n" + "=" * 80)
    print("编译速度基准测试完成！")
    print("=" * 80)

    return report


if __name__ == '__main__':
    main()