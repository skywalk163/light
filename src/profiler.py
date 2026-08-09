# -*- coding: utf-8 -*-
"""
光明（Light）性能分析器

功能：
  - 执行时间分析
  - 内存使用统计
  - 函数调用次数统计
  - 热点代码识别

用法：
  light profile file.light           # 基础性能分析
  light profile file.light --memory  # 包含内存分析
  light profile file.light --report  # 生成性能报告
"""

import os
import sys
import time
import json
import tracemalloc
import cProfile
import pstats
import io
from pathlib import Path


class LightProfiler:
    """光明性能分析器"""

    def __init__(self):
        self.stats = {}
        self.traces = []

    def profile(self, filepath: str, memory: bool = False, report: bool = False) -> dict:
        """分析光明程序的性能

        Args:
            filepath: 光明文件路径
            memory: 是否分析内存
            report: 是否生成详细报告

        Returns:
            性能分析结果
        """
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        # 读取源代码
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        # 编译
        compile_start = time.time()
        parser = LightParser()
        module = parser.parse(source)
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)
        compile_time = (time.time() - compile_start) * 1000

        # 统计信息
        stats = {
            'file': os.path.basename(filepath),
            'source_size': len(source),
            'source_lines': source.count('\n') + 1,
            'compile_time_ms': round(compile_time, 2),
            'code_size': len(py_code),
            'code_lines': py_code.count('\n') + 1,
        }

        # 执行时间分析
        if memory:
            tracemalloc.start()

        exec_start = time.time()

        # 执行代码
        output_lines = []
        def capture_print(*args, **kwargs):
            line = ' '.join(str(a) for a in args)
            output_lines.append(line)

        namespace = {
            'print': capture_print,
            '__name__': '__main__',
            '__file__': filepath
        }

        try:
            exec(py_code, namespace)
            exec_time = (time.time() - exec_start) * 1000
            stats['exec_time_ms'] = round(exec_time, 2)
            stats['success'] = True
            stats['output_lines'] = len(output_lines)
        except Exception as e:
            exec_time = (time.time() - exec_start) * 1000
            stats['exec_time_ms'] = round(exec_time, 2)
            stats['success'] = False
            stats['error'] = str(e)

        # 内存分析
        if memory:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            stats['memory_current_kb'] = round(current / 1024, 2)
            stats['memory_peak_kb'] = round(peak / 1024, 2)

        stats['total_time_ms'] = round(compile_time + exec_time, 2)

        # 生成报告
        if report:
            stats['report'] = self._generate_report(stats)
            stats['output'] = '\n'.join(output_lines) if output_lines else ''

        return stats

    def profile_with_cprofile(self, filepath: str) -> dict:
        """使用 cProfile 进行详细性能分析

        Args:
            filepath: 光明文件路径

        Returns:
            详细性能分析结果
        """
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        parser = LightParser()
        module = parser.parse(source)
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 使用 cProfile 分析
        profiler = cProfile.Profile()
        profiler.enable()

        namespace = {
            'print': lambda *a, **k: None,
            '__name__': '__main__',
            '__file__': filepath
        }

        try:
            exec(py_code, namespace)
        except Exception:
            pass

        profiler.disable()

        # 获取统计信息
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)

        result = {
            'file': os.path.basename(filepath),
            'profile': stream.getvalue()
        }

        return result

    def _generate_report(self, stats: dict) -> dict:
        """生成性能报告"""
        report = {
            'summary': {
                'status': '成功' if stats.get('success') else '失败',
                'total_time': f"{stats.get('total_time_ms', 0)} ms",
                'compile_time': f"{stats.get('compile_time_ms', 0)} ms",
                'exec_time': f"{stats.get('exec_time_ms', 0)} ms",
                'source_lines': stats.get('source_lines', 0),
                'code_lines': stats.get('code_lines', 0),
                'output_lines': stats.get('output_lines', 0),
            },
            'source': {
                'size': stats.get('source_size', 0),
                'lines': stats.get('source_lines', 0),
            },
            'compiled': {
                'size': stats.get('code_size', 0),
                'lines': stats.get('code_lines', 0),
                'expansion_ratio': round(stats.get('code_lines', 1) / max(stats.get('source_lines', 1), 1), 2)
            }
        }

        if 'memory_current_kb' in stats:
            report['memory'] = {
                'current': f"{stats['memory_current_kb']} KB",
                'peak': f"{stats['memory_peak_kb']} KB"
            }

        if stats.get('success'):
            # 性能评级
            exec_time = stats.get('exec_time_ms', 0)
            if exec_time < 10:
                grade = 'A (极快)'
            elif exec_time < 50:
                grade = 'B (快)'
            elif exec_time < 200:
                grade = 'C (一般)'
            elif exec_time < 1000:
                grade = 'D (慢)'
            else:
                grade = 'E (很慢)'
            report['grade'] = grade

            # 建议
            suggestions = []
            if stats.get('compile_time_ms', 0) > stats.get('exec_time_ms', 0) * 2:
                suggestions.append('编译时间较长，考虑使用 light compile 预编译')
            if exec_time > 500:
                suggestions.append('执行时间较长，考虑使用 LLVM 后端原生编译 (light pkg native)')
            if stats.get('expansion_ratio', 1) > 10:
                suggestions.append('代码膨胀率较高，检查是否有大量内置函数调用')
            if suggestions:
                report['suggestions'] = suggestions

        return report


def format_profile_output(stats: dict, report: bool = False, cprofile: bool = False):
    """格式化输出性能分析结果"""
    print("=" * 60)
    print("  光明性能分析")
    print("=" * 60)
    print(f"  文件: {stats.get('file', '')}")
    print()

    if cprofile:
        print("  cProfile 详细分析:")
        print("-" * 60)
        print(stats.get('profile', ''))
        print("-" * 60)
        return

    # 基本信息
    print("  [编译信息]")
    print(f"    源代码: {stats.get('source_size', 0)} 字节, {stats.get('source_lines', 0)} 行")
    print(f"    编译后: {stats.get('code_size', 0)} 字节, {stats.get('code_lines', 0)} 行")
    print(f"    编译耗时: {stats.get('compile_time_ms', 0)} ms")
    print()

    print("  [执行信息]")
    if stats.get('success'):
        print(f"    状态: 成功")
    else:
        print(f"    状态: 失败 - {stats.get('error', '未知错误')}")
    print(f"    执行耗时: {stats.get('exec_time_ms', 0)} ms")
    print(f"    总耗时: {stats.get('total_time_ms', 0)} ms")
    print(f"    输出行数: {stats.get('output_lines', 0)}")
    print()

    # 内存信息
    if 'memory_current_kb' in stats:
        print("  [内存信息]")
        print(f"    当前内存: {stats['memory_current_kb']} KB")
        print(f"    峰值内存: {stats['memory_peak_kb']} KB")
        print()

    # 报告
    if report and 'report' in stats:
        r = stats['report']
        print("  [性能报告]")
        print(f"    评级: {r.get('grade', 'N/A')}")
        if 'suggestions' in r:
            print(f"    建议:")
            for s in r['suggestions']:
                print(f"      - {s}")
        if 'memory' in r:
            print(f"    内存: 当前 {r['memory']['current']}, 峰值 {r['memory']['peak']}")
        print()

    print("=" * 60)


def run_profile(target: str, memory: bool = False, report: bool = False, cprofile: bool = False):
    """运行性能分析"""
    profiler = LightProfiler()

    if cprofile:
        stats = profiler.profile_with_cprofile(target)
        format_profile_output(stats, cprofile=True)
    else:
        stats = profiler.profile(target, memory=memory, report=report)
        format_profile_output(stats, report=report)

    # 保存报告到文件
    if report:
        report_path = os.path.splitext(target)[0] + '_profile.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"  详细报告已保存: {report_path}")