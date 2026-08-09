# -*- coding: utf-8 -*-
"""
光明编译器 - 运行时性能基准测试

测试内容：
1. 光明代码执行时间与等效 Python 代码对比
2. 标准库关键模块（数学、字符串、JSON、排序）性能
3. 输出对比报告（JSON格式）
"""

import sys
import os
import time
import json
import argparse
import math
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compiler import LightCompiler
from lexer import Lexer
from light_parser_v3 import LightParser as V3Parser
from code_generator_unified import UnifiedCodeGenerator
from compiler import AstAdapter

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


def compile_light(source):
    """编译光明源代码，返回生成的 Python 代码"""
    compiler = LightCompiler()
    result = compiler.compile(source)
    return result


def run_light(source):
    """编译并执行光明代码"""
    code = compile_light(source)
    exec(code, {})
    return code


# =============================================================================
# 光明 vs Python 性能对比
# =============================================================================

# 基准测试用例：光明代码 vs 等效 Python 代码
BENCHMARK_CASES = [
    {
        'name': '斐波那契(30)',
        'light': '''
段落 斐波那契 接收 n：
  如果 n 小于 2 那么：
    返回 n
  否则：
    返回 斐波那契(n 减 1) 加 斐波那契(n 减 2)

设 结果 为 斐波那契(30)
打印 结果
''',
        'python': '''
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

result = fibonacci(30)
print(result)
''',
    },
    {
        'name': '冒泡排序(100元素)',
        'light': '''
段落 冒泡排序 接收 列表, 长度：
  设 i 为 0
  当 i 小于 长度 减 1：
    设 j 为 0
    当 j 小于 长度 减 i 减 1：
      如果 列表[j] 大于 列表[j 加 1] 那么：
        设 临时 为 列表[j]
        列表[j] 为 列表[j 加 1]
        列表[j 加 1] 为 临时
      j 为 j 加 1
    i 为 i 加 1
  返回 列表

设 数据 为 [64, 34, 25, 12, 22, 11, 90, 45, 33, 77, 56, 8, 100, 29, 60, 95, 43, 78, 3, 19, 88, 51, 37, 72, 15, 82, 49, 61, 28, 55, 99, 18, 7, 44, 66, 92, 38, 23, 75, 84, 5, 53, 97, 14, 31, 69, 41, 86, 58, 2, 47, 71, 35, 80, 26, 93, 10, 54, 39, 76, 20, 67, 48, 83, 16, 59, 42, 91, 30, 73, 6, 50, 36, 85, 21, 62, 45, 96, 12, 70, 52, 89, 27, 74, 40, 81, 17, 63, 46, 94, 32, 65, 24, 79, 9, 57, 68, 13, 87, 98]
设 长度 为 100
设 结果 为 冒泡排序(数据, 长度)
打印 "排序完成"
''',
        'python': '''
def bubble_sort(arr, n):
    i = 0
    while i < n - 1:
        j = 0
        while j < n - i - 1:
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
            j += 1
        i += 1
    return arr

data = [64, 34, 25, 12, 22, 11, 90, 45, 33, 77, 56, 8, 100, 29, 60, 95, 43, 78, 3, 19, 88, 51, 37, 72, 15, 82, 49, 61, 28, 55, 99, 18, 7, 44, 66, 92, 38, 23, 75, 84, 5, 53, 97, 14, 31, 69, 41, 86, 58, 2, 47, 71, 35, 80, 26, 93, 10, 54, 39, 76, 20, 67, 48, 83, 16, 59, 42, 91, 30, 73, 6, 50, 36, 85, 21, 62, 45, 96, 12, 70, 52, 89, 27, 74, 40, 81, 17, 63, 46, 94, 32, 65, 24, 79, 9, 57, 68, 13, 87, 98]
n = 100
result = bubble_sort(data, n)
print("排序完成")
''',
    },
    {
        'name': '汉诺塔(20层)',
        'light': '''
段落 汉诺塔 接收 n, 源, 目标, 辅助：
  如果 n 等于 1 那么：
    返回
  否则：
    汉诺塔(n 减 1, 源, 辅助, 目标)
    汉诺塔(n 减 1, 辅助, 目标, 源)

汉诺塔(20, "A", "C", "B")
打印 "汉诺塔完成"
''',
        'python': '''
def hanoi(n, source, target, auxiliary):
    if n == 1:
        return
    else:
        hanoi(n - 1, source, auxiliary, target)
        hanoi(n - 1, auxiliary, target, source)

hanoi(20, "A", "C", "B")
print("汉诺塔完成")
''',
    },
    {
        'name': '累加求和(100万次)',
        'light': '''
设 总和 为 0
设 i 为 0
当 i 小于 100000：
  总和 为 总和 加 i
  i 为 i 加 1
打印 总和
''',
        'python': '''
total = 0
i = 0
while i < 100000:
    total += i
    i += 1
print(total)
''',
    },
    {
        'name': '矩阵乘法(50x50)',
        'light': '''
设 大小 为 50
设 矩阵A 为 []
设 矩阵B 为 []
设 结果 为 []

设 i 为 0
当 i 小于 大小：
  设 行A 为 []
  设 行B 为 []
  设 j 为 0
  当 j 小于 大小：
    行A 追加 (i 乘 大小 加 j)
    行B 追加 (j 乘 大小 加 i)
    j 为 j 加 1
  矩阵A 追加 行A
  矩阵B 追加 行B
  结果 追加 行A
  i 为 i 加 1

设 i 为 0
当 i 小于 大小：
  设 j 为 0
  当 j 小于 大小：
    设 和 为 0
    设 k 为 0
    当 k 小于 大小：
      和 为 和 加 矩阵A[i][k] 乘 矩阵B[k][j]
      k 为 k 加 1
    结果[i][j] 为 和
    j 为 j 加 1
  i 为 i 加 1

打印 "矩阵乘法完成"
''',
        'python': '''
size = 50
matrix_a = []
matrix_b = []
result = []

for i in range(size):
    row_a = []
    row_b = []
    for j in range(size):
        row_a.append(i * size + j)
        row_b.append(j * size + i)
    matrix_a.append(row_a)
    matrix_b.append(row_b)
    result.append(row_a)

for i in range(size):
    for j in range(size):
        s = 0
        for k in range(size):
            s += matrix_a[i][k] * matrix_b[k][j]
        result[i][j] = s

print("矩阵乘法完成")
''',
    },
]


def benchmark_light_vs_python():
    """光明代码执行时间与等效 Python 代码对比"""
    print("=" * 80)
    print("1. 光明 vs Python 运行时性能对比")
    print("=" * 80)

    results = []

    for case in BENCHMARK_CASES:
        name = case['name']
        print(f"\n  测试: {name}")

        # 光明编译 + 执行
        light_compile_time = 0
        light_exec_times = []
        for _ in range(3):
            compiler = LightCompiler()
            _, t_compile = time_it(compiler.compile, case['light'])
            code = compiler.compile(case['light'])
            light_compile_time += t_compile

            _, t_exec = time_it(exec, code, {})
            light_exec_times.append(t_exec)
        light_compile_avg = light_compile_time / 3
        light_exec_avg = sum(light_exec_times) / len(light_exec_times)

        print(f"    光明: 编译={format_time(light_compile_avg)}, 执行={format_time(light_exec_avg)}")

        # Python 执行
        py_times = []
        for _ in range(3):
            _, t_exec = time_it(exec, case['python'], {})
            py_times.append(t_exec)
        py_exec_avg = sum(py_times) / len(py_times)
        print(f"    Python: 执行={format_time(py_exec_avg)}")

        # 对比
        ratio = light_exec_avg / py_exec_avg if py_exec_avg > 0 else float('inf')
        print(f"    对比: 光明/Python = {ratio:.2f}x")

        result = {
            'name': name,
            'light_compile_avg': light_compile_avg,
            'light_exec_avg': light_exec_avg,
            'python_exec_avg': py_exec_avg,
            'ratio_light_to_python': ratio,
        }
        results.append(result)

    return results


# =============================================================================
# 标准库模块性能测试
# =============================================================================

def benchmark_stdlib_math():
    """测试数学运算性能"""
    print("\n" + "=" * 80)
    print("2. 标准库关键模块性能测试")
    print("=" * 80)

    results = []

    # 2.1 数学运算
    print("\n  2.1 数学运算:")
    math_results = {'category': 'math', 'tests': []}

    # 大量浮点运算
    n = 100000
    data = [random.random() * 100 for _ in range(1000)]

    # 光明数学运算
    light_math_code = f'''
段落 数学运算 接收 数据：
  设 总和 为 0
  设 乘积 为 1
  设 最大值 为 数据[0]
  设 最小值 为 数据[0]
  设 i 为 0
  当 i 小于 {len(data)}：
    总和 为 总和 加 数据[i]
    乘积 为 乘积 乘 (数据[i] 加 1)
    如果 数据[i] 大于 最大值 那么 最大值 为 数据[i]
    如果 数据[i] 小于 最小值 那么 最小值 为 数据[i]
    i 为 i 加 1
  返回 总和

设 数据 为 {data}
设 结果 为 数学运算(数据)
打印 结果
'''
    try:
        compiler = LightCompiler()
        code = compiler.compile(light_math_code)
        _, t_light_math = time_it(exec, code, {})
        print(f"    光明数学运算: {format_time(t_light_math)}")
        math_results['tests'].append({'name': '数学运算', 'light_time': t_light_math})
    except Exception as e:
        print(f"    光明数学运算: ✗ 错误: {e}")
        math_results['tests'].append({'name': '数学运算', 'error': str(e)})

    # Python 数学运算
    def py_math_ops(data):
        total = 0
        product = 1
        max_val = data[0]
        min_val = data[0]
        for i in range(len(data)):
            total += data[i]
            product *= (data[i] + 1)
            if data[i] > max_val:
                max_val = data[i]
            if data[i] < min_val:
                min_val = data[i]
        return total

    _, t_py_math = time_it(py_math_ops, data)
    print(f"    Python数学运算: {format_time(t_py_math)}")
    math_results['tests'][-1]['python_time'] = t_py_math
    math_results['tests'][-1]['ratio'] = t_light_math / t_py_math if t_py_math > 0 else float('inf')

    results.append(math_results)

    # 2.2 字符串操作
    print("\n  2.2 字符串操作:")
    string_results = {'category': 'string', 'tests': []}

    # 字符串拼接与处理
    light_str_code = '''
设 文本 为 "光明编程语言性能测试"
设 结果 为 ""
设 i 为 0
当 i 小于 1000：
  结果 为 结果 加 文本 加 字符串(i)
  i 为 i 加 1
打印 "字符串操作完成"
'''
    try:
        compiler = LightCompiler()
        code = compiler.compile(light_str_code)
        _, t_light_str = time_it(exec, code, {})
        print(f"    光明字符串操作: {format_time(t_light_str)}")
        string_results['tests'].append({'name': '字符串拼接', 'light_time': t_light_str})
    except Exception as e:
        print(f"    光明字符串操作: ✗ 错误: {e}")
        string_results['tests'].append({'name': '字符串拼接', 'error': str(e)})

    # Python 字符串操作
    def py_str_ops():
        text = "光明编程语言性能测试"
        result = ""
        for i in range(1000):
            result += text + str(i)
        return result

    _, t_py_str = time_it(py_str_ops)
    print(f"    Python字符串操作: {format_time(t_py_str)}")
    if 'light_time' in string_results['tests'][-1]:
        string_results['tests'][-1]['python_time'] = t_py_str
        string_results['tests'][-1]['ratio'] = string_results['tests'][-1]['light_time'] / t_py_str if t_py_str > 0 else float('inf')

    results.append(string_results)

    # 2.3 排序性能
    print("\n  2.3 排序性能:")
    sort_results = {'category': 'sorting', 'tests': []}

    sort_data = [random.randint(0, 10000) for _ in range(200)]

    light_sort_code = f'''
段落 冒泡排序 接收 列表, 长度：
  设 i 为 0
  当 i 小于 长度 减 1：
    设 j 为 0
    当 j 小于 长度 减 i 减 1：
      如果 列表[j] 大于 列表[j 加 1] 那么：
        设 临时 为 列表[j]
        列表[j] 为 列表[j 加 1]
        列表[j 加 1] 为 临时
      j 为 j 加 1
    i 为 i 加 1
  返回 列表

设 数据 为 {sort_data}
设 长度 为 {len(sort_data)}
设 结果 为 冒泡排序(数据, 长度)
打印 "排序完成"
'''
    try:
        compiler = LightCompiler()
        code = compiler.compile(light_sort_code)
        _, t_light_sort = time_it(exec, code, {})
        print(f"    光明冒泡排序(200元素): {format_time(t_light_sort)}")
        sort_results['tests'].append({'name': '冒泡排序(200)', 'light_time': t_light_sort})
    except Exception as e:
        print(f"    光明冒泡排序: ✗ 错误: {e}")
        sort_results['tests'].append({'name': '冒泡排序(200)', 'error': str(e)})

    # Python 排序
    def py_bubble_sort(arr):
        n = len(arr)
        for i in range(n - 1):
            for j in range(n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr

    _, t_py_sort = time_it(py_bubble_sort, sort_data.copy())
    print(f"    Python冒泡排序(200元素): {format_time(t_py_sort)}")
    if 'light_time' in sort_results['tests'][-1]:
        sort_results['tests'][-1]['python_time'] = t_py_sort
        sort_results['tests'][-1]['ratio'] = sort_results['tests'][-1]['light_time'] / t_py_sort if t_py_sort > 0 else float('inf')

    results.append(sort_results)

    # 2.4 JSON 处理
    print("\n  2.4 JSON 数据处理:")
    json_results = {'category': 'json', 'tests': []}

    # 列表操作模拟 JSON 数据处理
    light_list_code = '''
设 数据 为 []
设 i 为 0
当 i 小于 500：
  设 记录 为 [i, i 乘 2, 字符串(i) 加 "_value"]
  数据 追加 记录
  i 为 i 加 1

设 总和 为 0
设 i 为 0
当 i 小于 500：
  总和 为 总和 加 数据[i][1]
  i 为 i 加 1
打印 总和
'''
    try:
        compiler = LightCompiler()
        code = compiler.compile(light_list_code)
        _, t_light_json = time_it(exec, code, {})
        print(f"    光明列表数据处理(500条): {format_time(t_light_json)}")
        json_results['tests'].append({'name': '列表数据处理(500)', 'light_time': t_light_json})
    except Exception as e:
        print(f"    光明列表数据处理: ✗ 错误: {e}")
        json_results['tests'].append({'name': '列表数据处理(500)', 'error': str(e)})

    # Python 等效操作
    def py_list_ops():
        data = []
        for i in range(500):
            record = [i, i * 2, str(i) + "_value"]
            data.append(record)
        total = 0
        for i in range(500):
            total += data[i][1]
        return total

    _, t_py_json = time_it(py_list_ops)
    print(f"    Python列表数据处理(500条): {format_time(t_py_json)}")
    if 'light_time' in json_results['tests'][-1]:
        json_results['tests'][-1]['python_time'] = t_py_json
        json_results['tests'][-1]['ratio'] = json_results['tests'][-1]['light_time'] / t_py_json if t_py_json > 0 else float('inf')

    results.append(json_results)

    return results


def generate_report(light_vs_py_results, stdlib_results, output_path):
    """生成结构化 JSON 报告"""
    report = {
        'report_type': 'runtime_benchmark',
        'timestamp': datetime.now().isoformat(),
        'light_vs_python': light_vs_py_results,
        'stdlib_benchmark': stdlib_results,
        'summary': {},
    }

    # 计算汇总
    if light_vs_py_results:
        avg_ratio = sum(r.get('ratio_light_to_python', 0) for r in light_vs_py_results) / len(light_vs_py_results)
        report['summary'] = {
            'test_count': len(light_vs_py_results),
            'avg_light_to_python_ratio': avg_ratio,
            'fastest_relative': min(light_vs_py_results, key=lambda r: r.get('ratio_light_to_python', float('inf')))['name'],
            'slowest_relative': max(light_vs_py_results, key=lambda r: r.get('ratio_light_to_python', 0))['name'],
        }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到 {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description='光明编译器运行时性能基准测试')
    parser.add_argument('--output', '-o', default=str(REPORT_DIR / 'runtime_benchmark.json'),
                        help='JSON 报告输出路径')
    parser.add_argument('--no-compare', action='store_true', help='跳过光明 vs Python 对比')
    parser.add_argument('--no-stdlib', action='store_true', help='跳过标准库测试')
    args = parser.parse_args()

    print("光明编译器 - 运行时性能基准测试")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    light_vs_py_results = None
    stdlib_results = None

    if not args.no_compare:
        light_vs_py_results = benchmark_light_vs_python()

    if not args.no_stdlib:
        stdlib_results = benchmark_stdlib_math()

    # 生成报告
    report = generate_report(light_vs_py_results, stdlib_results, args.output)

    print("\n" + "=" * 80)
    print("运行时性能基准测试完成！")
    print("=" * 80)

    return report


if __name__ == '__main__':
    main()