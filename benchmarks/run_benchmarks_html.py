# -*- coding: utf-8 -*-
"""
光明编译器 - 增强版基准测试（带 HTML 报告生成）

功能：
1. 编译时间详细测量（词法分析、语法解析、代码生成、执行）
2. 内存使用测量（可选）
3. 与原生 Python 对比
4. 生成 HTML 格式报告
5. 历史趋势记录
"""

import sys
import os
import time
import json
import io
import tracemalloc
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import LightCompiler

BENCHMARK_DIR = Path(__file__).parent / 'programs'
HISTORY_FILE = Path(__file__).parent / 'benchmarks_history.json'
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


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def format_memory(bytes_size: int) -> str:
    """格式化内存大小显示"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.1f} MB"


def format_memory_short(bytes_size: int) -> str:
    """格式化内存大小显示（短格式）"""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f}KB"
    else:
        return f"{bytes_size / (1024 * 1024):.1f}MB"


def benchmark_program_detailed(source: str, name: str, iterations: int = 3,
                                measure_memory: bool = False) -> Dict:
    """对单个程序进行详细基准测试"""
    results = {
        'name': name,
        'source_len': len(source),
        'iterations': iterations,
        'lexer_times': [],
        'parser_times': [],
        'codegen_times': [],
        'execution_times': [],
        'total_compile_times': [],
        'token_count': 0,
        'memory_lexer': 0,
        'memory_parser': 0,
        'memory_codegen': 0,
        'memory_execution': 0,
        'memory_total': 0,
    }

    for i in range(iterations):
        # 词法分析
        tokens, t_lex = time_it(Lexer().tokenize, source)
        results['lexer_times'].append(t_lex)
        if i == 0:
            results['token_count'] = len(tokens)
            if measure_memory:
                _, mem_lex = mem_it(Lexer().tokenize, source)
                results['memory_lexer'] = mem_lex

        # 语法解析
        ast_raw, t_parse = time_it(V3Parser().parse, source)
        results['parser_times'].append(t_parse)
        if i == 0 and measure_memory:
            _, mem_parse = mem_it(V3Parser().parse, source)
            results['memory_parser'] = mem_parse

        # 代码生成
        from compiler import AstAdapter
        adapter = AstAdapter()
        ast = adapter.convert_module(ast_raw)
        codegen = UnifiedCodeGenerator()
        code, t_codegen = time_it(codegen.generate, ast)
        results['codegen_times'].append(t_codegen)
        if i == 0 and measure_memory:
            _, mem_codegen = mem_it(codegen.generate, ast)
            results['memory_codegen'] = mem_codegen

        # 编译总时间
        t_total = t_lex + t_parse + t_codegen
        results['total_compile_times'].append(t_total)

        # 执行时间（仅运行一次）
        if i == 0:
            if measure_memory:
                tracemalloc.start()
            _, t_exec = time_it(exec, code, {})
            results['execution_times'].append(t_exec)
            if measure_memory:
                _, mem_exec = tracemalloc.get_traced_memory()
                results['memory_execution'] = mem_exec
                tracemalloc.stop()

    # 计算统计
    for key in ['lexer', 'parser', 'codegen', 'total_compile']:
        times = results[f'{key}_times']
        if times:
            results[f'{key}_avg'] = sum(times) / len(times)
            results[f'{key}_min'] = min(times)
            results[f'{key}_max'] = max(times)
        else:
            results[f'{key}_avg'] = 0
            results[f'{key}_min'] = 0
            results[f'{key}_max'] = 0

    if results['execution_times']:
        results['execution_avg'] = results['execution_times'][0]

    if measure_memory:
        results['memory_total'] = (results['memory_lexer'] + results['memory_parser'] +
                                    results['memory_codegen'] + results['memory_execution'])

    return results


def load_history() -> List[Dict]:
    """加载历史数据"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(results: List[Dict], run_id: Optional[str] = None):
    """保存历史数据"""
    history = load_history()
    entry = {
        'run_id': run_id or datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat(),
        'results': results,
    }
    history.append(entry)
    if len(history) > 50:
        history = history[-50:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def generate_html_report(results: List[Dict], history: Optional[List[Dict]] = None,
                          output_path: Optional[Path] = None) -> str:
    """生成 HTML 格式基准测试报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 计算汇总
    total_compile = sum(r.get('total_compile_avg', 0) for r in results)
    avg_compile = total_compile / len(results) if results else 0
    total_source = sum(r.get('source_len', 0) for r in results)

    # 生成表格行
    table_rows = []
    for r in results:
        name = r['name']
        src_len = r.get('source_len', 0)
        t_lex = format_time(r.get('lexer_avg', 0))
        t_parse = format_time(r.get('parser_avg', 0))
        t_codegen = format_time(r.get('codegen_avg', 0))
        t_total = format_time(r.get('total_compile_avg', 0))
        t_exec = format_time(r.get('execution_avg', 0))

        # 内存
        mem_lex = format_memory_short(r.get('memory_lexer', 0))
        mem_total = format_memory_short(r.get('memory_total', 0))

        # 计算百分比
        tc = r.get('total_compile_avg', 0)
        if tc > 0:
            lex_pct = r.get('lexer_avg', 0) / tc * 100
            parse_pct = r.get('parser_avg', 0) / tc * 100
            codegen_pct = r.get('codegen_avg', 0) / tc * 100
        else:
            lex_pct = parse_pct = codegen_pct = 0

        table_rows.append(f"""
        <tr>
            <td>{name}</td>
            <td>{src_len} B</td>
            <td>{t_lex}<br><small>{lex_pct:.1f}%</small></td>
            <td>{t_parse}<br><small>{parse_pct:.1f}%</small></td>
            <td>{t_codegen}<br><small>{codegen_pct:.1f}%</small></td>
            <td><strong>{t_total}</strong></td>
            <td>{t_exec}</td>
            <td>{mem_lex}</td>
            <td>{mem_total}</td>
        </tr>""")

    # 生成历史趋势行
    history_rows = ''
    if history and len(history) > 1:
        for entry in history[-10:]:
            comp_times = [r.get('total_compile_avg', 0) for r in entry.get('results', [])]
            if comp_times:
                avg = sum(comp_times) / len(comp_times)
                fastest = min(comp_times)
                slowest = max(comp_times)
                ts = entry.get('timestamp', '')[:19]
                history_rows += f"""
        <tr>
            <td>{ts}</td>
            <td>{format_time(avg)}</td>
            <td>{format_time(fastest)}</td>
            <td>{format_time(slowest)}</td>
            <td>{len(comp_times)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>光明编译器基准测试报告</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
    h2 {{ color: #333; margin-top: 30px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
    .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
    .summary-card .value {{ font-size: 24px; font-weight: bold; color: #1a73e8; }}
    .summary-card .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    th, td {{ padding: 10px 12px; text-align: center; border: 1px solid #e0e0e0; }}
    th {{ background: #1a73e8; color: #fff; font-weight: 500; }}
    tr:nth-child(even) {{ background: #f8f9fa; }}
    tr:hover {{ background: #e8f0fe; }}
    small {{ color: #888; font-size: 10px; }}
    .timestamp {{ color: #888; font-size: 14px; margin: 10px 0; }}
    .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #888; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
    .badge-ok {{ background: #e6f4ea; color: #1e7e34; }}
    @media (max-width: 768px) {{ .container {{ padding: 15px; }} table {{ font-size: 12px; }} th, td {{ padding: 6px 8px; }} }}
</style>
</head>
<body>
<div class="container">
    <h1>📊 光明编译器基准测试报告</h1>
    <p class="timestamp">生成时间: {now} | Python {sys.version.split()[0]}</p>

    <div class="summary">
        <div class="summary-card">
            <div class="value">{len(results)}</div>
            <div class="label">测试程序数</div>
        </div>
        <div class="summary-card">
            <div class="value">{format_time(total_compile)}</div>
            <div class="label">总编译时间</div>
        </div>
        <div class="summary-card">
            <div class="value">{format_time(avg_compile)}</div>
            <div class="label">平均编译时间</div>
        </div>
        <div class="summary-card">
            <div class="value">{total_source} B</div>
            <div class="label">总源码大小</div>
        </div>
    </div>

    <h2>测试结果</h2>
    <table>
        <thead>
            <tr>
                <th>程序</th>
                <th>源码长度</th>
                <th>词法分析</th>
                <th>语法解析</th>
                <th>代码生成</th>
                <th>编译总计</th>
                <th>执行时间</th>
                <th>内存(词法)</th>
                <th>内存(总计)</th>
            </tr>
        </thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>

    <h2>性能趋势</h2>
    <table>
        <thead>
            <tr>
                <th>时间</th>
                <th>平均编译时间</th>
                <th>最快程序</th>
                <th>最慢程序</th>
                <th>程序数</th>
            </tr>
        </thead>
        <tbody>
            {history_rows if history_rows else '<tr><td colspan="5">暂无历史数据</td></tr>'}
        </tbody>
    </table>

    <div class="footer">
        <p>光明 (Light) 编译器 - 基准测试工具 | <span class="badge badge-ok">v1.0</span></p>
    </div>
</div>
</body>
</html>"""

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML 报告已保存到 {output_path}")

    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description='光明编译器增强版基准测试（HTML报告）')
    parser.add_argument('--program', '-p', help='只运行指定基准程序')
    parser.add_argument('--iterations', '-n', type=int, default=3, help='迭代次数（默认3）')
    parser.add_argument('--mem', '-m', action='store_true', help='测量内存占用')
    parser.add_argument('--no-history', action='store_true', help='不记录历史')
    parser.add_argument('--output', '-o', help='HTML 报告输出路径')
    parser.add_argument('--json', '-j', help='同时输出 JSON 结果到文件')
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
    if args.mem:
        print("（已启用内存测量）")
    print()

    results = []
    for bench_file in bench_files:
        name = bench_file.stem
        print(f"运行 {name} ...", end=' ', flush=True)
        with open(bench_file, 'r', encoding='utf-8') as f:
            source = f.read()
        try:
            result = benchmark_program_detailed(source, name, args.iterations, measure_memory=args.mem)
            results.append(result)
            t = format_time(result.get('total_compile_avg', 0))
            print(f"✓ ({t})")
        except Exception as e:
            print(f"✗ 错误: {e}")

    # 生成 HTML 报告
    history = load_history() if not args.no_history else []
    report_path = args.output or (REPORT_DIR / f'benchmark_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html')
    generate_html_report(results, history, Path(report_path))

    # 保存 JSON
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"JSON 结果已保存到 {args.json}")

    # 保存历史
    if not args.no_history:
        save_history(results)
        print(f"历史已保存到 {HISTORY_FILE}")

    # 打印摘要
    print()
    print("=" * 60)
    print("基准测试摘要")
    print("=" * 60)
    for r in results:
        name = r['name'][:20]
        t_total = format_time(r.get('total_compile_avg', 0))
        t_exec = format_time(r.get('execution_avg', 0))
        tokens = r.get('token_count', 0)
        print(f"  {name:<20} 编译: {t_total:<10} 执行: {t_exec:<10} Token: {tokens}")
    print("=" * 60)


if __name__ == '__main__':
    main()