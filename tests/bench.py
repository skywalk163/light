# -*- coding: utf-8 -*-
"""
光明 v4.0 性能基准测试
测量：编译速度、运行时性能、内存占用

用法:
  python bench.py              # 运行所有基准测试
  python bench.py --quick      # 快速模式（减少迭代）
  python bench.py --output report.json  # 输出 JSON 报告
"""
import os
import sys
import io
import time
import json
import tracemalloc
import argparse
from pathlib import Path

_project_root = Path(__file__).parent.parent
_src_dir = _project_root / 'src'
for p in [str(_src_dir), str(_project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


# ============================================================
# 测试用例
# ============================================================

def _light_hello():
    """最简单的程序"""
    return '印("你好，光明！")\n'

def _light_loop_n(n):
    """循环 N 次累加"""
    return f'''设 总和 为 0
设 甲 为 0
当 甲 < {n}：
  设 总和 为 总和 + 甲
  设 甲 为 甲 + 1
印(总和)
'''

def _light_fibonacci(n):
    """递归斐波那契"""
    return f'''段 fib(x)：
  若 x <= 1：
    返回 x
  返回 fib(x - 1) + fib(x - 2)
印(fib({n}))
'''

def _light_conditionals(n):
    """多层条件判断"""
    code = f'设 x 为 {n}\n'
    for i in range(10):
        code += f'若 x == {i}：\n  印({i})\n'
    code += '印("done")\n'
    return code

def _light_large_program(n):
    """生成大型程序"""
    code = f'设 总和 为 0\n'
    for i in range(n):
        code += f'设 甲{i} 为 {i}\n'
        code += f'设 总和 为 总和 + 甲{i}\n'
    code += '印(总和)\n'
    code += f'若 总和 > {n//2}：\n  印("大")\n否则：\n  印("小")\n'
    return code


# ============================================================
# 基准测试函数
# ============================================================

def bench_compile_speed(iterations=100):
    """测量编译速度（解析 + 代码生成）"""
    cases = {
        "hello": _light_hello(),
        "loop_1000": _light_loop_n(1000),
        "fib_15": _light_fibonacci(15),
        "conditionals": _light_conditionals(50),
        "large_100": _light_large_program(100),
    }

    results = {}
    for name, code in cases.items():
        times = []
        for _ in range(iterations):
            parser = LightParser()
            gen = PythonCodeGenerator()
            start = time.perf_counter()
            ast = parser.parse(code)
            if ast is not None:
                gen.generate(ast)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        avg = sum(times) / len(times) * 1000  # ms
        results[name] = {
            "avg_ms": round(avg, 4),
            "min_ms": round(min(times) * 1000, 4),
            "max_ms": round(max(times) * 1000, 4),
            "code_lines": code.count('\n'),
            "iterations": iterations
        }
    return results


def bench_runtime_vs_python(iterations=5):
    """对比光明运行时 vs 等效 Python 运行时"""
    cases = {
        "loop_sum": (
            _light_loop_n(100000),
            'sum(range(100000))'
        ),
        "fib_20": (
            _light_fibonacci(20),
            '''def fib(x):
    if x <= 1: return x
    return fib(x-1) + fib(x-2)
print(fib(20))'''
        ),
    }

    results = {}
    for name, (light_code, py_code) in cases.items():
        # 编译光明
        parser = LightParser()
        gen = PythonCodeGenerator()
        ast = parser.parse(light_code)
        compiled = gen.generate(ast)

        light_times = []
        py_times = []

        for _ in range(iterations):
            # 光明运行时
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            start = time.perf_counter()
            try:
                exec(compiled, {'__name__': '__main__'})
            except Exception:
                pass
            light_times.append(time.perf_counter() - start)
            sys.stdout = old_stdout

            # Python 运行时
            sys.stdout = io.StringIO()
            start = time.perf_counter()
            try:
                exec(py_code, {'__name__': '__main__'})
            except Exception:
                pass
            py_times.append(time.perf_counter() - start)
            sys.stdout = old_stdout

        light_avg = sum(light_times) / len(light_times) * 1000
        py_avg = sum(py_times) / len(py_times) * 1000
        ratio = light_avg / py_avg if py_avg > 0 else 0

        results[name] = {
            "light_avg_ms": round(light_avg, 2),
            "python_avg_ms": round(py_avg, 2),
            "ratio": round(ratio, 2),
            "iterations": iterations
        }
    return results


def bench_memory():
    """测量内存占用"""
    cases = {
        "small": _light_hello(),
        "medium": _light_loop_n(1000),
        "large": _light_large_program(200),
    }

    results = {}
    for name, code in cases.items():
        parser = LightParser()
        gen = PythonCodeGenerator()
        # 编译阶段内存
        tracemalloc.start()
        ast = parser.parse(code)
        compiled = gen.generate(ast)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results[name] = {
            "compile_current_kb": round(current / 1024, 2),
            "compile_peak_kb": round(peak / 1024, 2),
            "code_size_bytes": len(code.encode('utf-8')),
            "compiled_size_bytes": len(compiled.encode('utf-8')),
        }
    return results


def bench_parse_large(iterations=10):
    """测量解析大型程序"""
    parser = LightParser()

    sizes = [10, 50, 100, 200, 500]
    results = []

    for n in sizes:
        code = _light_large_program(n)
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            parser.parse(code)
            times.append(time.perf_counter() - start)
        avg = sum(times) / len(times) * 1000
        results.append({
            "statements": n,
            "code_lines": code.count('\n'),
            "avg_parse_ms": round(avg, 4),
            "iterations": iterations
        })
    return results


# ============================================================
# 主程序
# ============================================================

def print_table(headers, rows, aligns=None):
    """打印格式化表格"""
    if not aligns:
        aligns = ['<'] * len(headers)

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(vals):
        parts = []
        for i, v in enumerate(vals):
            w = col_widths[i]
            a = aligns[i] if i < len(aligns) else '<'
            parts.append(f"{str(v):{a}{w}}")
        return " | ".join(parts)

    sep = "-" * (sum(col_widths) + 3 * (len(headers) - 1))
    print(fmt_row(headers))
    print(sep)
    for row in rows:
        print(fmt_row(row))


def main():
    parser = argparse.ArgumentParser(description='光明 v4.0 性能基准测试')
    parser.add_argument('--quick', action='store_true', help='快速模式')
    parser.add_argument('--output', help='输出 JSON 报告路径')
    args = parser.parse_args()

    iters = 10 if args.quick else 100
    rt_iters = 3 if args.quick else 5

    print("=" * 70)
    print("  光明 v4.0 性能基准测试")
    print("=" * 70)

    # 1. 编译速度
    print("\n📊 1. 编译速度 (解析 + 代码生成)")
    print(f"   迭代次数: {iters}")
    compile_results = bench_compile_speed(iters)
    rows = []
    for name, r in compile_results.items():
        rows.append([name, f"{r['avg_ms']:.3f} ms", f"{r['min_ms']:.3f} ms",
                     f"{r['max_ms']:.3f} ms", f"{r['code_lines']} 行"])
    print_table(["测试用例", "平均耗时", "最小耗时", "最大耗时", "代码行数"], rows)
    print()

    # 2. 运行时对比
    print("📊 2. 运行时对比 (光明 vs Python)")
    print(f"   迭代次数: {rt_iters}")
    runtime_results = bench_runtime_vs_python(rt_iters)
    rows = []
    for name, r in runtime_results.items():
        rows.append([name, f"{r['light_avg_ms']:.2f} ms", f"{r['python_avg_ms']:.2f} ms",
                     f"{r['ratio']:.2f}x"])
    print_table(["测试用例", "光明耗时", "Python耗时", "比值"], rows)
    print()

    # 3. 内存
    print("📊 3. 内存占用")
    mem_results = bench_memory()
    rows = []
    for name, r in mem_results.items():
        rows.append([name, f"{r['compile_peak_kb']:.1f} KB", f"{r['code_size_bytes']} B",
                     f"{r['compiled_size_bytes']} B"])
    print_table(["测试用例", "编译峰值内存", "源码大小", "编译后大小"], rows)
    print()

    # 4. 解析缩放
    print("📊 4. 解析缩放性 (大规模程序)")
    print(f"   迭代次数: {iters // 10}")
    scale_results = bench_parse_large(iters // 10)
    rows = []
    for r in scale_results:
        rows.append([f"{r['statements']} 语句", f"{r['code_lines']} 行",
                     f"{r['avg_parse_ms']:.3f} ms"])
    print_table(["规模", "代码行数", "平均解析耗时"], rows)
    print()

    print("=" * 70)
    print("  基准测试完成")
    print("=" * 70)

    # 输出 JSON 报告
    if args.output:
        report = {
            "tool": "光明 v4.0 性能基准",
            "python_version": sys.version,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "compile_speed": compile_results,
            "runtime_comparison": runtime_results,
            "memory": mem_results,
            "parse_scalability": scale_results,
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到: {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())