# -*- coding: utf-8 -*-
"""
光明编译器 - 大项目编译测试

测试内容：
1. 生成包含 50/100/200 个模块的大项目
2. 测试编译时间、内存占用、依赖解析时间
3. 输出可扩展性报告（JSON格式）
"""

import sys
import os
import time
import json
import argparse
import tracemalloc
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compiler import LightCompiler
from incremental_compiler import IncrementalCompiler, DependencyGraph

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


# =============================================================================
# 大项目生成
# =============================================================================

def generate_large_project(num_modules: int, output_dir: Path, with_deps: bool = True):
    """生成包含多个模块的大项目

    Args:
        num_modules: 模块数量
        output_dir: 输出目录
        with_deps: 是否生成模块间依赖关系
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成主模块
    main_lines = ['// 主模块\n']

    # 生成各个模块
    for i in range(num_modules):
        module_name = f"模块{i}"
        module_file = output_dir / f"{module_name}.light"

        lines = [f"// {module_name}\n"]

        # 添加导入依赖（如果启用依赖）
        if with_deps and i > 0:
            # 每个模块依赖前一个模块
            lines.append(f"导入 \"模块{i - 1}.light\"\n")

        # 添加一些函数定义
        for j in range(5):
            lines.append(f"""
段落 函数_{i}_{j} 接收 x：
  设 结果 为 x 加 {i} 乘 {j} 减 {i + j}
  返回 结果
""")

        # 添加一些类定义
        if i % 2 == 0:
            lines.append(f"""
类 类_{i}：
  属性 值
  构造 接收 值：
    己值 为 值
  段落 获取：
    返回 己值 加 {i}
""")

        # 添加一些循环和条件
        lines.append(f"""
段落 处理_{i}：
  设 总和 为 0
  设 i 为 0
  当 i 小于 10：
    总和 为 总和 加 i 乘 {i}
    i 为 i 加 1
  返回 总和
""")

        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(''.join(lines))

        # 主模块引用
        if i % 10 == 0:
            main_lines.append(f"导入 \"{module_name}.light\"\n")

    # 生成主模块
    main_lines.append("\n\n段落 主函数：")
    main_lines.append("  打印 \"大项目编译测试完成\"")
    main_lines.append(f"  打印 \"模块数: {num_modules}\"\n")
    main_lines.append("主函数()\n")

    main_file = output_dir / "main.light"
    with open(main_file, 'w', encoding='utf-8') as f:
        f.write(''.join(main_lines))

    # 计算总大小
    total_size = 0
    for fpath in output_dir.glob('*.light'):
        total_size += fpath.stat().st_size

    return output_dir, total_size


# =============================================================================
# 编译时间测试
# =============================================================================

def benchmark_compile_time(project_dir: Path, num_modules: int):
    """测试大项目编译时间"""
    print(f"\n  编译 {num_modules} 个模块 ... ", end='', flush=True)

    main_file = project_dir / 'main.light'
    with open(main_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # 编译
    times = []
    for _ in range(3):
        compiler = LightCompiler()
        result, t = time_it(compiler.compile, source)
        times.append(t)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"平均 {format_time(avg_time)} (最小 {format_time(min_time)} / 最大 {format_time(max_time)})")

    return {
        'num_modules': num_modules,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'iterations': 3,
    }


# =============================================================================
# 内存占用测试
# =============================================================================

def benchmark_memory(project_dir: Path, num_modules: int):
    """测试大项目编译内存占用"""
    print(f"  内存占用 ({num_modules} 模块) ... ", end='', flush=True)

    main_file = project_dir / 'main.light'
    with open(main_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # 编译并测量内存
    compiler = LightCompiler()
    _, peak = mem_it(compiler.compile, source)

    print(f"峰值: {format_memory(peak)}")

    return {
        'num_modules': num_modules,
        'peak_memory': peak,
    }


# =============================================================================
# 依赖解析时间测试
# =============================================================================

def benchmark_dependency_resolution(project_dir: Path, num_modules: int):
    """测试依赖解析时间"""
    print(f"  依赖解析 ({num_modules} 模块) ... ", end='', flush=True)

    # 构建依赖图
    dep_graph = DependencyGraph()

    start = time.perf_counter()

    # 模拟依赖解析
    for i in range(num_modules):
        deps = [f"模块{i - 1}"] if i > 0 else []
        dep_graph.add_module(f"模块{i}", str(project_dir / f"模块{i}.light"), deps)

    # 拓扑排序
    for i in range(num_modules):
        deps = dep_graph.get_dependencies(f"模块{i}")
        _ = deps

    elapsed = time.perf_counter() - start

    print(format_time(elapsed))

    return {
        'num_modules': num_modules,
        'resolution_time': elapsed,
    }


# =============================================================================
# 可扩展性分析
# =============================================================================

def benchmark_scalability(module_counts=None):
    """测试不同规模项目的可扩展性"""
    if module_counts is None:
        module_counts = [50, 100, 200]

    print("=" * 80)
    print("大项目编译可扩展性测试")
    print("=" * 80)

    results = []

    # 创建临时目录
    temp_base = Path(tempfile.mkdtemp(prefix='light_bench_large_'))

    try:
        for num_modules in module_counts:
            print(f"\n--- 测试 {num_modules} 个模块 ---")

            # 生成项目
            print(f"  生成项目...", end=' ', flush=True)
            project_dir, total_size = generate_large_project(num_modules, temp_base / f"proj_{num_modules}")
            print(f"总大小 {total_size / 1024:.1f} KB")

            # 编译时间
            time_result = benchmark_compile_time(project_dir, num_modules)

            # 内存占用
            mem_result = benchmark_memory(project_dir, num_modules)

            # 依赖解析
            dep_result = benchmark_dependency_resolution(project_dir, num_modules)

            result = {
                'num_modules': num_modules,
                'total_size': total_size,
                'compile_time': time_result,
                'memory': mem_result,
                'dependency': dep_result,
            }
            results.append(result)

    finally:
        # 清理临时目录
        shutil.rmtree(temp_base, ignore_errors=True)

    return results


def generate_report(results, output_path):
    """生成结构化 JSON 报告"""
    report = {
        'report_type': 'large_project_benchmark',
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'summary': {},
        'scalability_analysis': {},
    }

    # 计算汇总
    if results:
        valid_results = [r for r in results if 'error' not in r]
        if valid_results:
            # 编译时间汇总
            for r in valid_results:
                ct = r['compile_time']
                r['compile_time']['size_per_second'] = r['total_size'] / ct['avg_time'] if ct['avg_time'] > 0 else 0

            # 可扩展性分析
            if len(valid_results) >= 2:
                scalability = {}
                for i in range(1, len(valid_results)):
                    prev = valid_results[i - 1]
                    curr = valid_results[i]
                    module_ratio = curr['num_modules'] / prev['num_modules']
                    time_ratio = curr['compile_time']['avg_time'] / prev['compile_time']['avg_time']
                    mem_ratio = curr['memory']['peak_memory'] / prev['memory']['peak_memory']

                    scalability[f"{prev['num_modules']}_to_{curr['num_modules']}"] = {
                        'module_ratio': module_ratio,
                        'time_ratio': time_ratio,
                        'mem_ratio': mem_ratio,
                        'time_scalability': 'linear' if abs(time_ratio - module_ratio) / module_ratio < 0.3 else 'superlinear' if time_ratio > module_ratio else 'sublinear',
                        'mem_scalability': 'linear' if abs(mem_ratio - module_ratio) / module_ratio < 0.3 else 'superlinear' if mem_ratio > module_ratio else 'sublinear',
                    }
                report['scalability_analysis'] = scalability

            report['summary'] = {
                'test_count': len(valid_results),
                'module_counts': [r['num_modules'] for r in valid_results],
                'avg_compile_times': [r['compile_time']['avg_time'] for r in valid_results],
                'peak_memories': [r['memory']['peak_memory'] for r in valid_results],
            }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到 {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description='光明编译器大项目编译测试')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'large_project_benchmark.json'),
                        help='JSON 报告输出路径')
    parser.add_argument('--modules', '-m', type=int, nargs='+', default=[50, 100, 200],
                        help='要测试的模块数量（默认: 50 100 200）')
    args = parser.parse_args()

    print("光明编译器 - 大项目编译测试")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"模块数: {args.modules}")
    print()

    results = benchmark_scalability(args.modules)

    # 生成报告
    report = generate_report(results, args.output)

    print("\n" + "=" * 80)
    print("大项目编译测试完成！")
    print("=" * 80)

    return report


if __name__ == '__main__':
    main()