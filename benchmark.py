#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（Duan）性能基准测试

测量关键操作的时间开销：
1. 词法分析（Lexer）
2. 语法解析（Parser）
3. 代码生成（Codegen）
4. 完整编译管线
5. 与 CPython 对比（等效 Python 代码）

用法：
  python benchmark.py                    # 运行全部基准
  python benchmark.py --quick            # 快速模式（少量迭代）
  python benchmark.py --compare-python   # 包含 CPython 对比
"""

import sys
import os
import time
import statistics
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# =============================================================================
# 测试样例
# =============================================================================

SAMPLE_CODE = '''
# 段言基准测试示例
段落 斐波那契 接收 n：
    如果 n 小于等于 1：
        返回 n
    返回 斐波那契(n 减 1) 加 斐波那契(n 减 2)

段落 快排 接收 列表：
    如果 len(列表) 小于等于 1：
        返回 列表
    设 基准 为 列表[0]
    设 左列 为 []
    设 右列 为 []
    设 i 为 1
    当 i 小于 len(列表)：
        如果 列表[i] 小于 基准：
            设 左列 为 左列 加 [列表[i]]
        否则：
            设 右列 为 右列 加 [列表[i]]
        设 i 为 i 加 1
    返回 快排(左列) 加 [基准] 加 快排(右列)

设 数据 为 [5, 3, 8, 1, 9, 2, 7, 4, 6]
打印("斐波那契(10) = ")打印(斐波那契(10))
打印("排序结果 = ")打印(快排(数据))
'''

LARGE_SAMPLE_CODE = '''
# 大文件基准测试
设 数据 为 []
设 i 为 0
当 i 小于 1000：
    设 数据 为 数据 加 [i]
    设 i 为 i 加 1
'''

# 等效 Python 代码（用于对比）
PYTHON_EQUIVALENT = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    left = [x for x in arr[1:] if x < pivot]
    right = [x for x in arr[1:] if x >= pivot]
    return quicksort(left) + [pivot] + quicksort(right)

data = [5, 3, 8, 1, 9, 2, 7, 4, 6]
print("fibonacci(10) =", fibonacci(10))
print("sorted =", quicksort(data))
'''


# =============================================================================
# 基准测试工具
# =============================================================================

class Benchmark:
    def __init__(self, quick=False):
        self.quick = quick
        self.results = []

    def measure(self, name, fn, iterations=100):
        """测量函数执行时间"""
        if self.quick:
            iterations = max(iterations // 10, 3)

        # 预热
        for _ in range(3):
            fn()

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # ms

        avg = statistics.mean(times)
        med = statistics.median(times)
        mn = min(times)
        mx = max(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0

        self.results.append({
            'name': name,
            'avg_ms': avg,
            'med_ms': med,
            'min_ms': mn,
            'max_ms': mx,
            'stdev': stdev,
            'iterations': iterations,
        })

        print(f"  {name:<30}  avg={avg:8.3f}ms  med={med:8.3f}ms  "
              f"min={mn:8.3f}ms  max={mx:8.3f}ms  (n={iterations})")

    def print_summary(self):
        """打印汇总"""
        print("\n" + "=" * 70)
        print("基准测试汇总")
        print("=" * 70)
        print(f"{'测试项':<30} {'平均(ms)':<10} {'中位数(ms)':<12} {'吞吐(万 token/s)':<16} {'标准差':<10}")
        print("-" * 70)
        for r in sorted(self.results, key=lambda x: x['avg_ms']):
            tp = f"{r['throughput'] / 10000:8.2f}" if r.get('throughput') else "-"
            print(f"{r['name']:<30} {r['avg_ms']:<10.3f} {r['med_ms']:<12.3f} {tp:<16} {r['stdev']:<10.3f}")


# =============================================================================
# 具体测试
# =============================================================================

def bench_lexer(bm: Benchmark):
    """词法分析基准"""
    from lexer import Lexer
    lexer = Lexer()
    bm.measure("Lexer 词法分析（小文件）", lambda: lexer.tokenize(SAMPLE_CODE), 500)
    bm.measure("Lexer 词法分析（大文件）", lambda: lexer.tokenize(LARGE_SAMPLE_CODE), 200)


def bench_lexer_throughput(bm: Benchmark):
    """词法分析 Token/s 吞吐量基准

    测量单位时间内可处理的 token 数量，验证 Lexer 健壮化后
    吞吐量不低于修改前水平。输出格式：X.XX 万 token/s。
    """
    from lexer import Lexer

    def measure_throughput(name, source, iterations=200):
        lexer = Lexer()
        # 预热并统计 token 数
        tokens = lexer.tokenize(source)
        token_count = len(tokens)

        for _ in range(3):
            lexer.tokenize(source)

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            lexer.tokenize(source)
            end = time.perf_counter()
            times.append(end - start)

        avg_sec = statistics.mean(times)
        throughput = token_count / avg_sec  # token/s

        self = bm
        self.results.append({
            'name': name,
            'avg_ms': avg_sec * 1000,
            'med_ms': statistics.median(times) * 1000,
            'min_ms': min(times) * 1000,
            'max_ms': max(times) * 1000,
            'stdev': statistics.stdev(times) * 1000 if len(times) > 1 else 0,
            'iterations': iterations,
            'token_count': token_count,
            'throughput': throughput,
        })
        print(f"  {name:<30}  avg={avg_sec * 1000:8.3f}ms  吞吐={throughput / 10000:8.2f} 万 token/s  (n={iterations}, tokens={token_count})")

    measure_throughput("Lexer 吞吐（小文件）", SAMPLE_CODE, 500)
    measure_throughput("Lexer 吞吐（大文件 10x）", LARGE_SAMPLE_CODE * 10, 200)


def bench_parser(bm: Benchmark):
    """语法解析基准"""
    from lexer import Lexer
    from duan_parser_v3 import DuanParser
    lexer = Lexer()
    parser = DuanParser()

    # 预先 tokenize 以单独测量 parser
    tokens = lexer.tokenize(SAMPLE_CODE)
    large_tokens = lexer.tokenize(LARGE_SAMPLE_CODE * 10)

    bm.measure("Parser 解析（小文件）", lambda: parser.parse(SAMPLE_CODE), 500)
    bm.measure("Parser 解析（大文件）", lambda: parser.parse(LARGE_SAMPLE_CODE * 10), 200)


def bench_codegen(bm: Benchmark):
    """代码生成基准"""
    from duan_parser_v3 import DuanParser
    from code_generator import PythonCodeGenerator
    parser = DuanParser()
    generator = PythonCodeGenerator()

    module = parser.parse(SAMPLE_CODE)
    large_module = parser.parse(LARGE_SAMPLE_CODE * 10)

    bm.measure("Codegen 代码生成（小文件）", lambda: generator.generate(module), 500)
    bm.measure("Codegen 代码生成（大文件）", lambda: generator.generate(large_module), 200)


def bench_full_pipeline(bm: Benchmark):
    """完整编译管线基准"""
    bm.measure("完整管线（词法+解析+生成）", lambda: _run_pipeline(SAMPLE_CODE), 200)
    bm.measure("完整管线（大文件 10x）", lambda: _run_pipeline(LARGE_SAMPLE_CODE * 10), 100)


def _run_pipeline(source):
    """运行完整编译管线"""
    from lexer import Lexer
    from duan_parser_v3 import DuanParser
    from code_generator import PythonCodeGenerator
    lexer = Lexer()
    parser = DuanParser()
    generator = PythonCodeGenerator()
    tokens = lexer.tokenize(source)
    module = parser.parse(source)
    py_code = generator.generate(module)
    return py_code


def bench_compare_python(bm: Benchmark):
    """与 CPython 对比"""
    # 编译并执行段言代码
    from duan_parser_v3 import DuanParser
    from code_generator import PythonCodeGenerator

    def run_duan():
        parser = DuanParser()
        module = parser.parse(SAMPLE_CODE)
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)
        ns = {'print': lambda *a: None}
        exec(py_code, ns)

    # 直接执行等效 Python 代码
    def run_python():
        ns = {'print': lambda *a: None}
        exec(PYTHON_EQUIVALENT, ns)

    bm.measure("段言 编译+执行", run_duan, 50)
    bm.measure("CPython 直接执行", run_python, 50)


# =============================================================================
# 主入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='段言性能基准测试')
    parser.add_argument('--quick', action='store_true', help='快速模式（少量迭代）')
    parser.add_argument('--compare-python', action='store_true', help='包含 CPython 对比')
    args = parser.parse_args()

    print("=" * 70)
    print("段言（Duan）性能基准测试")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"平台: {sys.platform}")
    if args.quick:
        print("模式: 快速（少量迭代）")
    print()

    bm = Benchmark(quick=args.quick)

    print("\n[1/4] 词法分析基准")
    print("-" * 50)
    bench_lexer(bm)

    print("\n[1b/4] 词法分析 Token/s 吞吐量基准")
    print("-" * 50)
    bench_lexer_throughput(bm)

    print("\n[2/4] 语法解析基准")
    print("-" * 50)
    bench_parser(bm)

    print("\n[3/4] 代码生成基准")
    print("-" * 50)
    bench_codegen(bm)

    print("\n[4/4] 完整管线基准")
    print("-" * 50)
    bench_full_pipeline(bm)

    if args.compare_python:
        print("\n[5/4] CPython 对比")
        print("-" * 50)
        bench_compare_python(bm)

    bm.print_summary()

    print("\n完成。")


if __name__ == '__main__':
    main()