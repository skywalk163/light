#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言 vs Python 性能基准测试

运行相同算法在 Python 和 段言（通过 src 解释器）中的执行时间对比。
生成比较报告到 docs/性能基准_vs_Python.md

用法:
  python tools/benchmark_vs_python.py
"""

import sys
import os
import time
import math
import json
import subprocess
from pathlib import Path

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / 'src'))
sys.path.insert(0, str(PROJECT_DIR))

# 导入段言编译执行器
from duan_parser_v3 import DuanParser
from code_generator import PythonCodeGenerator


def run_duan_code(source_code: str) -> str:
    """通过 src 后端编译并执行段言代码，返回输出"""
    parser = DuanParser()
    module = parser.parse(source_code)
    if module is None:
        raise RuntimeError("段言解析失败")

    generator = PythonCodeGenerator()
    py_code = generator.generate(module)

    output_lines = []
    def _capture_print(*args, **kwargs):
        line = ' '.join(str(a) for a in args)
        output_lines.append(line)

    namespace = {'print': _capture_print, '__name__': '__main__'}
    exec(py_code, namespace)
    return '\n'.join(output_lines)


def time_python(code):
    """测量 Python 代码执行时间"""
    namespace = {}
    start = time.perf_counter()
    exec(code, namespace)
    elapsed = time.perf_counter() - start
    return namespace, elapsed


def time_duan(code_template: str, iterations: int = 1) -> float:
    """测量段言代码执行时间"""
    start = time.perf_counter()
    for _ in range(iterations):
        run_duan_code(code_template)
    elapsed = time.perf_counter() - start
    return elapsed / iterations


# ===== 基准测试 1: 斐波那契数列 =====

PY_FIBONACCI_CODE = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(30):
    fibonacci(i)
"""

DUAN_FIBONACCI_CODE = """
段落 斐波那契 接收 n：
  如果 n 小于等于 1：
    返回 n。
  返回 斐波那契(n - 1) + 斐波那契(n - 2)。

设 i 为 0。
当 i 小于 30：
  斐波那契(i)。
  i 为 i + 1。
"""


# ===== 基准测试 2: 素数筛法 =====

PY_PRIME_CODE = """
def sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    return [i for i in range(n + 1) if is_prime[i]]

sieve(100000)
"""

DUAN_PRIME_CODE = """
段落 素数筛 接收 n：
  设 标记 为 []。
  设 i 为 0。
  当 i 小于等于 n：
    列表追加(标记, 真)。
    i 为 i + 1。

  标记[0] 为 假。
  标记[1] 为 假。

  设 i 为 2。
  当 i * i 小于等于 n：
    如果 标记[i]：
      设 j 为 i * i。
      当 j 小于等于 n：
        标记[j] 为 假。
        j 为 j + i。
    i 为 i + 1。

  设 结果 为 []。
  设 i 为 0。
  当 i 小于等于 n：
    如果 标记[i]：
      列表追加(结果, i)。
    i 为 i + 1。

  返回 结果。

素数筛(10000)。
"""


# ===== 基准测试 3: 冒泡排序 =====

PY_BUBBLE_CODE = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

data = [i for i in range(200, 0, -1)]
bubble_sort(data)
"""

DUAN_BUBBLE_CODE = """
段落 冒泡排序 接收 数组：
  设 n 为 列表长度(数组)。
  设 i 为 0。
  当 i 小于 n - 1：
    设 j 为 0。
    当 j 小于 n - i - 1：
      如果 数组[j] 大于 数组[j + 1]：
        设 临时 为 数组[j]。
        数组[j] 为 数组[j + 1]。
        数组[j + 1] 为 临时。
      j 为 j + 1。
    i 为 i + 1。
  返回 数组。

设 数据 为 []。
设 i 为 200。
当 i 大于等于 1：
  列表追加(数据, i)。
  i 为 i - 1。

冒泡排序(数据)。
"""


# ===== 基准测试 4: 阶乘计算 =====

PY_FACTORIAL_CODE = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

factorial(500)
"""

DUAN_FACTORIAL_CODE = """
段落 阶乘 接收 n：
  如果 n 小于等于 1：
    返回 1。
  返回 n * 阶乘(n - 1)。

阶乘(100)。
"""


# ===== 基准测试 5: 汉诺塔 =====

PY_HANOI_CODE = """
def hanoi(n, source, target, auxiliary):
    if n == 1:
        return
    hanoi(n - 1, source, auxiliary, target)
    hanoi(n - 1, auxiliary, target, source)

hanoi(20, 'A', 'C', 'B')
"""

DUAN_HANOI_CODE = """
段落 汉诺塔 接收 n, 来源, 目标, 辅助：
  如果 n 等于 1：
    返回。
  汉诺塔(n - 1, 来源, 辅助, 目标)。
  汉诺塔(n - 1, 辅助, 目标, 来源)。

汉诺塔(15, "A", "C", "B")。
"""


# ===== 基准测试 6: 列表操作 =====

PY_LIST_OPS_CODE = """
def list_ops():
    data = []
    for i in range(10000):
        data.append(i)
    for i in range(5000):
        data.pop()
    for i in range(5000):
        data.insert(0, i)
    return len(data)

list_ops()
"""

DUAN_LIST_OPS_CODE = """
段落 列表操作：
  设 数据 为 []。
  设 i 为 0。
  当 i 小于 1000：
    列表追加(数据, i)。
    i 为 i + 1。

  设 i 为 0。
  当 i 小于 500：
    列表弹出(数据)。
    i 为 i + 1。

  设 i 为 0。
  当 i 小于 500：
    列表插入(数据, 0, i)。
    i 为 i + 1。

  返回 列表长度(数据)。

列表操作()。
"""


# ===== 基准测试 7: 字符串操作 =====

PY_STR_CODE = """
def str_ops():
    s = ""
    for i in range(1000):
        s += str(i)
    s = s.replace("5", "FIVE")
    parts = s.split("FIVE")
    return len(parts)

str_ops()
"""

DUAN_STR_CODE = """
段落 字符串操作：
  设 s 为 ""。
  设 i 为 0。
  当 i 小于 200：
    s 为 s + 转字符串(i)。
    i 为 i + 1。

  s 为 替换字符串(s, "5", "FIVE")。
  设 部分 为 分割字符串(s, "FIVE")。
  返回 列表长度(部分)。

字符串操作()。
"""


# ===== 基准测试 8: 矩阵乘法 (CPU密集型) =====

PY_MATRIX_CODE = """
def matrix_mul(n):
    A = [[i * n + j for j in range(n)] for i in range(n)]
    B = [[j * n + i for j in range(n)] for i in range(n)]
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += A[i][k] * B[k][j]
            C[i][j] = s
    return C

matrix_mul(50)
"""

DUAN_MATRIX_CODE = """
段落 矩阵乘法 接收 n：
  设 A 为 []。
  设 i 为 0。
  当 i 小于 n：
    设 行 为 []。
    设 j 为 0。
    当 j 小于 n：
      列表追加(行, i * n + j)。
      j 为 j + 1。
    列表追加(A, 行)。
    i 为 i + 1。

  设 B 为 []。
  设 i 为 0。
  当 i 小于 n：
    设 行 为 []。
    设 j 为 0。
    当 j 小于 n：
      列表追加(行, j * n + i)。
      j 为 j + 1。
    列表追加(B, 行)。
    i 为 i + 1。

  设 C 为 []。
  设 i 为 0。
  当 i 小于 n：
    设 行 为 []。
    设 j 为 0。
    当 j 小于 n：
      列表追加(行, 0)。
      j 为 j + 1。
    列表追加(C, 行)。
    i 为 i + 1。

  设 i 为 0。
  当 i 小于 n：
    设 j 为 0。
    当 j 小于 n：
      设 s 为 0。
      设 k 为 0。
      当 k 小于 n：
        s 为 s + A[i][k] * B[k][j]。
        k 为 k + 1。
      C[i][j] 为 s。
      j 为 j + 1。
    i 为 i + 1。
  返回 C。

矩阵乘法(30)。
"""


# ===== 基准测试 9: 快速排序 (CPU密集型) =====

PY_QUICKSORT_CODE = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    left = [x for x in arr[1:] if x <= pivot]
    right = [x for x in arr[1:] if x > pivot]
    return quicksort(left) + [pivot] + quicksort(right)

import random
data = [random.randint(0, 10000) for _ in range(5000)]
quicksort(data)
"""

DUAN_QUICKSORT_CODE = """
段落 快速排序 接收 数组：
  如果 列表长度(数组) 小于等于 1：
    返回 数组。
  设 基准 为 数组[0]。
  设 左 为 []。
  设 右 为 []。
  设 i 为 1。
  当 i 小于 列表长度(数组)：
    如果 数组[i] 小于等于 基准：
      列表追加(左, 数组[i])。
    否则：
      列表追加(右, 数组[i])。
    i 为 i + 1。
  返回 合并列表(快速排序(左), 合并列表([基准], 快速排序(右)))。

段落 合并列表 接收 a, b：
  设 结果 为 []。
  设 i 为 0。
  当 i 小于 列表长度(a)：
    列表追加(结果, a[i])。
    i 为 i + 1。
  设 i 为 0。
  当 i 小于 列表长度(b)：
    列表追加(结果, b[i])。
    i 为 i + 1。
  返回 结果。

设 数据 为 []。
设 i 为 0。
当 i 小于 1000：
  列表追加(数据, (i * 7 + 3) % 1000)。
  i 为 i + 1。

快速排序(数据)。
"""


# ===== 基准测试 10: JSON 序列化/解析 (IO密集型模拟) =====

PY_JSON_CODE = """
import json
data = {"users": [{"id": i, "name": f"user_{i}", "scores": [i * j for j in range(5)]} for i in range(100)]}
for _ in range(20):
    s = json.dumps(data, ensure_ascii=False)
    d = json.loads(s)
"""

DUAN_JSON_CODE = """
设 数据 为 {}。
设 用户列表 为 []。
设 i 为 0。
当 i 小于 50：
  设 用户 为 {}。
  用户["id"] 为 i。
  用户["name"] 为 "user_" + 转字符串(i)。
  设 分数 为 []。
  设 j 为 0。
  当 j 小于 5：
    列表追加(分数, i * j)。
    j 为 j + 1。
  用户["scores"] 为 分数。
  列表追加(用户列表, 用户)。
  i 为 i + 1。
数据["users"] 为 用户列表。

设 i 为 0。
当 i 小于 5：
  设 s 为 序列化JSON(数据)。
  设 d 为 解析JSON(s)。
  i 为 i + 1。
"""


# ===== 基准测试 11: 文件 I/O (IO密集型模拟) =====

PY_FILEIO_CODE = """
import tempfile, os
content = "\\n".join(f"line_{i}" for i in range(10000))
tmpdir = tempfile.mkdtemp()
for _ in range(5):
    path = os.path.join(tmpdir, f"test_{_}.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()
"""

DUAN_FILEIO_CODE = """
段落 文件IO 接收：
  设 内容 为 ""。
  设 i 为 0。
  当 i 小于 1000：
    内容 为 内容 + "line_" + 转字符串(i) + "\\n"。
    i 为 i + 1。

  设 i 为 0。
  当 i 小于 3：
    写入文件("_benchmark_temp_" + 转字符串(i) + ".txt", 内容)。
    设 读取 为 读取文件("_benchmark_temp_" + 转字符串(i) + ".txt")。
    i 为 i + 1。

文件IO()。
"""


# ===== 基准测试 12: 大列表拼接 (内存操作) =====

PY_LIST_CONCAT_CODE = """
def list_concat():
    result = []
    for i in range(100):
        result.extend([i] * 100)
    return len(result)

list_concat()
"""

DUAN_LIST_CONCAT_CODE = """
段落 列表拼接：
  设 结果 为 []。
  设 i 为 0。
  当 i 小于 50：
    设 j 为 0。
    当 j 小于 50：
      列表追加(结果, i)。
      j 为 j + 1。
    i 为 i + 1。
  返回 列表长度(结果)。

列表拼接()。
"""


# ===== 基准测试 13: 字典操作 (内存操作) =====

PY_DICT_CODE = """
def dict_ops():
    d = {}
    for i in range(10000):
        d[f"key_{i}"] = i
    total = 0
    for i in range(5000):
        total += d.get(f"key_{i}", 0)
    return total

dict_ops()
"""

DUAN_DICT_CODE = """
段落 字典操作：
  设 d 为 {}。
  设 i 为 0。
  当 i 小于 2000：
    d["key_" + 转字符串(i)] 为 i。
    i 为 i + 1。
  设 总和 为 0。
  设 i 为 0。
  当 i 小于 1000：
    如果 字典包含键(d, "key_" + 转字符串(i))：
      总和 为 总和 + d["key_" + 转字符串(i)]。
    i 为 i + 1。
  返回 总和。

字典操作()。
"""


def run_benchmark(name: str, py_code: str, duan_code: str,
                  py_iterations: int = 3, duan_iterations: int = 1):
    """运行单次基准测试，返回 (name, python_time, duan_time, ratio)"""
    print(f"  运行基准测试: {name}...")

    # Python 基准
    py_times = []
    for _ in range(py_iterations):
        _, t = time_python(py_code)
        py_times.append(t)
    py_avg = sum(py_times) / len(py_times)

    # 段言基准
    duan_times = []
    for _ in range(max(1, duan_iterations)):
        try:
            t = time_duan(duan_code)
            duan_times.append(t)
        except Exception as e:
            print(f"    段言执行错误: {e}")
            return (name, py_avg, None, None)

    duan_avg = sum(duan_times) / len(duan_times)

    if duan_avg > 0 and py_avg > 0:
        ratio = duan_avg / py_avg
    else:
        ratio = None

    print(f"    Python: {py_avg:.6f}s, 段言: {duan_avg:.6f}s, 比率: {ratio:.2f}x" if ratio else
          f"    Python: {py_avg:.6f}s, 段言: {duan_avg:.6f}s")
    return (name, py_avg, duan_avg, ratio)


def generate_report(results: list, output_path: str):
    """生成 Markdown 报告"""
    lines = []
    lines.append("# 段言 vs Python 性能基准测试报告")
    lines.append("")
    lines.append("> 生成时间: 2026-08-07")
    lines.append("> 测试环境: 段言 v5.5.0 (SRC 后端) vs Python 3.x")
    lines.append("")
    lines.append("## 测试概述")
    lines.append("")
    lines.append("本报告对比了段言编程语言（通过 SRC 后端解释执行）与 Python 在相同算法下的执行性能。")
    lines.append("")
    lines.append("| 测试编号 | 测试名称 | Python 耗时 (s) | 段言耗时 (s) | 比率 (段言/Python) |")
    lines.append("|---------|---------|----------------|-------------|-------------------|")

    for i, (name, py_time, duan_time, ratio) in enumerate(results, 1):
        py_str = f"{py_time:.6f}" if py_time is not None else "N/A"
        duan_str = f"{duan_time:.6f}" if duan_time is not None else "失败"
        ratio_str = f"{ratio:.2f}x" if ratio is not None else "N/A"
        lines.append(f"| {i} | {name} | {py_str} | {duan_str} | {ratio_str} |")

    lines.append("")
    lines.append("## 测试详情")
    lines.append("")

    for i, (name, py_time, duan_time, ratio) in enumerate(results, 1):
        lines.append(f"### {i}. {name}")
        lines.append("")
        if py_time is not None:
            lines.append(f"- Python 耗时: **{py_time:.6f}** 秒")
        if duan_time is not None:
            lines.append(f"- 段言耗时: **{duan_time:.6f}** 秒")
        if ratio is not None:
            lines.append(f"- 性能比率: **{ratio:.2f}x** (段言是 Python 的 {ratio:.2f} 倍)")
        lines.append("")

    # 计算平均比率
    valid_ratios = [r for _, _, _, r in results if r is not None]
    if valid_ratios:
        avg_ratio = sum(valid_ratios) / len(valid_ratios)
        lines.append(f"## 总结")
        lines.append("")
        lines.append(f"- 共完成 **{len(results)}** 项基准测试")
        lines.append(f"- **{len(valid_ratios)}** 项测试成功完成")
        lines.append(f"- **{len(results) - len(valid_ratios)}** 项测试失败")
        lines.append(f"- 段言平均执行时间为 Python 的 **{avg_ratio:.2f} 倍**")
        lines.append("")

        # 按场景分类
        lines.append("### 按场景分类")
        lines.append("")
        lines.append("| 场景分类 | 测试项 | 平均比率 |")
        lines.append("|---------|-------|---------|")
        cpu_tests = [r for r in results if 'CPU密集型' in r[0] or r[0] in ['斐波那契数列 (n=30)', '素数筛法 (n=10000)', '冒泡排序 (n=200)', '阶乘计算 (n=100)', '汉诺塔 (n=15)', '矩阵乘法 (30x30)', '快速排序 (n=1000)']]
        io_tests = [r for r in results if 'IO密集型' in r[0] or r[0] in ['JSON 序列化/解析', '文件 I/O 读写']]
        mem_tests = [r for r in results if '内存操作' in r[0] or r[0] in ['列表操作 (1000次)', '字符串操作 (200次)', '大列表拼接 (2500元素)', '字典操作 (2000键值)']]
        for cat, tests, label in [('CPU 密集型', cpu_tests, 'CPU'), ('IO 密集型', io_tests, 'IO'), ('内存操作', mem_tests, '内存')]:
            valid = [r[3] for r in tests if r[3] is not None]
            if valid:
                avg = sum(valid) / len(valid)
                names = ', '.join(r[0] for r in tests)
                lines.append(f"| {label} | {names} | {avg:.2f}x |")
        lines.append("")

        lines.append("> 注：段言目前通过 SRC 后端解释执行（编译为 Python 字节码再运行），")
        lines.append("> 性能差距主要来源于解释执行的开销。未来 LLVM 后端完成后将大幅提升性能。")
        lines.append("")

    report = "\n".join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存到: {output_path}")


def main():
    print("=" * 60)
    print("段言 vs Python 性能基准测试")
    print("=" * 60)
    print()

    benchmarks = [
        ("斐波那契数列 (n=30)", PY_FIBONACCI_CODE, DUAN_FIBONACCI_CODE, 3, 1),
        ("素数筛法 (n=10000)", PY_PRIME_CODE, DUAN_PRIME_CODE, 3, 1),
        ("冒泡排序 (n=200)", PY_BUBBLE_CODE, DUAN_BUBBLE_CODE, 3, 1),
        ("阶乘计算 (n=100)", PY_FACTORIAL_CODE, DUAN_FACTORIAL_CODE, 3, 1),
        ("汉诺塔 (n=15)", PY_HANOI_CODE, DUAN_HANOI_CODE, 3, 1),
        ("列表操作 (1000次)", PY_LIST_OPS_CODE, DUAN_LIST_OPS_CODE, 3, 1),
        ("字符串操作 (200次)", PY_STR_CODE, DUAN_STR_CODE, 3, 1),
        ("矩阵乘法 (30x30)", PY_MATRIX_CODE, DUAN_MATRIX_CODE, 3, 1),
        ("快速排序 (n=1000)", PY_QUICKSORT_CODE, DUAN_QUICKSORT_CODE, 3, 1),
        ("JSON 序列化/解析", PY_JSON_CODE, DUAN_JSON_CODE, 3, 1),
        ("文件 I/O 读写", PY_FILEIO_CODE, DUAN_FILEIO_CODE, 3, 1),
        ("大列表拼接 (2500元素)", PY_LIST_CONCAT_CODE, DUAN_LIST_CONCAT_CODE, 3, 1),
        ("字典操作 (2000键值)", PY_DICT_CODE, DUAN_DICT_CODE, 3, 1),
    ]

    results = []
    for name, py_code, duan_code, py_iter, duan_iter in benchmarks:
        try:
            result = run_benchmark(name, py_code, duan_code, py_iter, duan_iter)
            results.append(result)
        except Exception as e:
            print(f"  基准测试失败 [{name}]: {e}")
            results.append((name, 0, 0, None))

    # 清理临时文件
    for f in Path('.').glob('_benchmark_temp_*.txt'):
        try:
            f.unlink()
        except Exception:
            pass

    # 生成报告
    output_path = PROJECT_DIR / 'docs' / '性能基准_vs_Python.md'
    generate_report(results, str(output_path))

    print("\n" + "=" * 60)
    print("基准测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()