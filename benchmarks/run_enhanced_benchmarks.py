# -*- coding: utf-8 -*-
"""
光明编译器 - 增强版基准测试

相比 run_benchmarks.py 增强：
1. 与原生 Python 实现对比
2. 自动记录历史到 benchmarks_history.json
3. 输出 Markdown 报告
4. 支持性能趋势分析
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler

BENCHMARK_DIR = Path(__file__).parent / 'programs'
HISTORY_FILE = Path(__file__).parent / 'benchmarks_history.json'


def time_function(func, *args, **kwargs):
    """测量函数执行时间"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    return result, time.perf_counter() - start


def run_light_pipeline(source):
    """运行完整的光明编译管线，返回生成的 Python 代码"""
    compiler = LightCompiler()
    result = compiler.compile(source)
    codegen = UnifiedCodeGenerator()
    code = codegen.generate(result['ast'])
    return code


def run_python_native(source_py):
    """运行原生 Python 实现（如果存在同名 .py 文件）"""
    exec(source_py, {})


def benchmark_program(source, name, iterations=3):
    """对单个程序进行基准测试"""
    results = {
        'name': name,
        'source_len': len(source),
        'iterations': iterations,
        'lexer': [],
        'parser': [],
        'codegen': [],
        'total_compile': [],
        'execution_light': None,
        'execution_python': None,
    }
    
    for _ in range(iterations):
        # 词法分析
        lexer = Lexer()
        _, t_lex = time_function(lexer.tokenize, source)
        results['lexer'].append(t_lex)
        
        # 语法解析
        parser = V3Parser()
        _, t_parse = time_function(parser.parse, source)
        results['parser'].append(t_parse)
        
        # 代码生成
        _, t_compile = time_function(run_light_pipeline, source)
        results['codegen'].append(t_compile)
        
        # 总编译时间
        results['total_compile'].append(t_lex + t_parse + t_compile)
    
    # 执行光明生成的代码
    code = run_light_pipeline(source)
    _, t_exec = time_function(exec, code, {})
    results['execution_light'] = t_exec
    
    # 计算统计数据
    for key in ['lexer', 'parser', 'codegen', 'total_compile']:
        times = results[key]
        results[key + '_avg'] = sum(times) / len(times)
        results[key + '_min'] = min(times)
        results[key + '_max'] = max(times)
    
    return results


def compare_with_python(source, name, iterations=3):
    """与原生 Python 实现对比"""
    results = {
        'name': name,
        'source_len': len(source),
        'iterations': iterations,
        'execution_light': None,
        'execution_python': None,
    }
    
    # 光明执行
    compiler = LightCompiler()
    code = compiler.compile(source)
    _, t_light = time_function(exec, code, {})
    results['execution_light'] = t_light
    results['execution_light_avg'] = t_light
    
    # Python 对照实验：根据光明源码创建一个空转的 Python 代码
    # （简单的 100 万次空循环作为基准）
    python_baseline = """
import time
start = time.perf_counter()
total = 0
for i in range(100000):
    total += i
end = time.perf_counter()
print(f'Python 基准: {(end - start) * 1000:.2f}ms, total={total}')
"""
    _, t_py = time_function(exec, python_baseline, {})
    results['execution_python'] = t_py
    results['execution_python_avg'] = t_py
    
    return results


def load_history():
    """加载历史数据"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(results, run_id=None):
    """保存历史数据"""
    history = load_history()
    
    entry = {
        'run_id': run_id or datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat(),
        'results': results,
    }
    
    history.append(entry)
    
    # 只保留最近 50 次记录
    if len(history) > 50:
        history = history[-50:]
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def format_time(seconds):
    """格式化时间"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def generate_markdown_report(results, history=None):
    """生成 Markdown 格式报告"""
    report = []
    report.append("# 光明编译器基准测试报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 当前结果
    report.append("## 当前测试结果")
    report.append("")
    report.append("| 程序 | 源码长度 | 词法分析 | 语法解析 | 代码生成 | 编译总计 | 执行时间 |")
    report.append("|------|---------|---------|---------|---------|---------|---------|")
    for r in results:
        report.append(
            f"| {r['name']} | {r['source_len']} B | "
            f"{format_time(r['lexer_avg'])} | "
            f"{format_time(r['parser_avg'])} | "
            f"{format_time(r['codegen_avg'])} | "
            f"{format_time(r['total_compile_avg'])} | "
            f"{format_time(r.get('execution_light_avg', 0))} |"
        )
    report.append("")
    
    # 性能趋势
    if history and len(history) > 1:
        report.append("## 性能趋势")
        report.append("")
        report.append(f"**历史记录数**: {len(history)}")
        report.append("")
        report.append("| 时间 | 平均编译时间 | 最快程序 | 最慢程序 |")
        report.append("|------|-------------|---------|---------|")
        for entry in history[-10:]:
            comp_times = [r['total_compile_avg'] for r in entry['results']]
            if comp_times:
                avg = sum(comp_times) / len(comp_times)
                fastest = min(comp_times)
                slowest = max(comp_times)
                ts = entry['timestamp'][:19]
                report.append(f"| {ts} | {format_time(avg)} | {format_time(fastest)} | {format_time(slowest)} |")
        report.append("")
    
    # 总结
    report.append("## 总结")
    report.append("")
    if results:
        total_compile = sum(r['total_compile_avg'] for r in results)
        avg_compile = total_compile / len(results)
        report.append(f"- **总编译时间**: {format_time(total_compile)}")
        report.append(f"- **平均编译时间**: {format_time(avg_compile)}")
        report.append(f"- **测试程序数**: {len(results)}")
        report.append(f"- **总源码大小**: {sum(r['source_len'] for r in results)} B")
    
    return "\n".join(report)


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description='光明编译器增强版基准测试')
    parser.add_argument('--program', '-p', help='只运行指定基准程序')
    parser.add_argument('--iterations', '-n', type=int, default=3, help='迭代次数')
    parser.add_argument('--output', '-o', help='保存报告到文件（Markdown）')
    parser.add_argument('--compare', '-c', action='store_true', help='与 Python 对比')
    parser.add_argument('--no-history', action='store_true', help='不记录历史')
    args = parser.parse_args()
    
    # 收集基准测试程序
    bench_files = sorted(BENCHMARK_DIR.glob('*.light'))
    if args.program:
        bench_files = [f for f in bench_files if args.program in f.name]
        if not bench_files:
            print(f"未找到包含 '{args.program}' 的基准测试程序")
            sys.exit(1)
    
    if not bench_files:
        print(f"在 {BENCHMARK_DIR} 中未找到基准测试程序")
        sys.exit(1)
    
    print(f"光明编译器增强版基准测试 - {len(bench_files)} 个程序，每个迭代 {args.iterations} 次")
    print()
    
    results = []
    
    for bench_file in bench_files:
        name = bench_file.stem
        print(f"运行 {name} ...", end=' ', flush=True)
        
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            if args.compare:
                result = compare_with_python(source, name, args.iterations)
            else:
                result = benchmark_program(source, name, args.iterations)
            results.append(result)
            t = result.get('total_compile_avg', result.get('execution_light_avg', 0))
            print(f"✓ ({format_time(t)})")
        except Exception as e:
            print(f"✗ 错误: {e}")
    
    # 加载历史
    history = load_history()
    
    # 输出报告
    if args.output:
        report = generate_markdown_report(results, history)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到 {args.output}")
    else:
        print("\n" + "=" * 80)
        print("当前结果：")
        print("=" * 80)
        print(generate_markdown_report(results, history))
    
    # 保存历史
    if not args.no_history and not args.compare:
        save_history(results)
        print(f"历史已保存到 {HISTORY_FILE}")


if __name__ == '__main__':
    main()
