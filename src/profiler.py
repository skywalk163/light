# -*- coding: utf-8 -*-
"""
光明（Light）性能分析器

功能：
  - 执行时间分析（分阶段细粒度计时）
  - 内存使用统计（含阶段峰值跟踪）
  - 编译时间按阶段分解（词法分析 → 语法解析 → AST适配 → 优化 → 代码生成）
  - 热点代码识别
  - 生成人类可读/机器可读的性能报告

用法：
  light profile file.light                     # 基础性能分析
  light profile file.light --memory            # 包含内存分析
  light profile file.light --report            # 生成性能报告
  light profile file.light --profile-report    # 生成详细编译器性能报告
  light --profile-report compile file.light    # 编译时附带性能分析
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
from typing import Optional, Dict, List, Any


class PhaseTimer:
    """分阶段计时器，用于编译器各阶段的耗时统计"""

    def __init__(self):
        self._phases: Dict[str, float] = {}
        self._current_phase: Optional[str] = None
        self._start_time: Optional[float] = None
        self._phase_order: List[str] = []

    def start_phase(self, name: str):
        """开始一个阶段计时（自动停止上一个阶段）"""
        if self._current_phase is not None:
            self.stop_phase()
        self._current_phase = name
        self._start_time = time.perf_counter()

    def stop_phase(self):
        """停止当前阶段计时"""
        if self._current_phase is not None and self._start_time is not None:
            elapsed = (time.perf_counter() - self._start_time) * 1000  # ms
            self._phases[self._current_phase] = round(elapsed, 3)
            if self._current_phase not in self._phase_order:
                self._phase_order.append(self._current_phase)
            self._current_phase = None
            self._start_time = None

    def get_phases(self) -> Dict[str, float]:
        """获取所有阶段耗时"""
        if self._current_phase is not None:
            self.stop_phase()
        return self._phases

    def get_phase_order(self) -> List[str]:
        """获取阶段执行顺序"""
        if self._current_phase is not None:
            self.stop_phase()
        return self._phase_order

    def get_total(self) -> float:
        """获取总耗时"""
        return sum(self.get_phases().values())

    def get_breakdown(self) -> Dict[str, Any]:
        """获取阶段分解详情"""
        phases = self.get_phases()
        total = sum(phases.values()) or 1
        return {
            'phases': phases,
            'phase_order': self.get_phase_order(),
            'total_ms': round(total, 2),
            'breakdown': {
                name: {
                    'time_ms': time_ms,
                    'percentage': round(time_ms / total * 100, 1)
                }
                for name, time_ms in phases.items()
            }
        }


class MemoryTracker:
    """内存使用追踪器，支持阶段级峰值记录"""

    def __init__(self):
        self._snapshots: Dict[str, Dict[str, float]] = {}
        self._current_phase: Optional[str] = None
        self._enabled = False

    def start(self):
        """启动内存追踪"""
        tracemalloc.start()
        self._enabled = True

    def stop(self) -> Dict[str, float]:
        """停止内存追踪，返回最终内存统计"""
        if not self._enabled:
            return {}
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self._enabled = False
        return {
            'current_kb': round(current / 1024, 2),
            'peak_kb': round(peak / 1024, 2),
        }

    def snapshot(self, phase_name: str):
        """记录当前阶段的内存快照"""
        if not self._enabled:
            return
        current, peak = tracemalloc.get_traced_memory()
        self._snapshots[phase_name] = {
            'current_kb': round(current / 1024, 2),
            'peak_kb': round(peak / 1024, 2),
        }

    def get_phase_memory(self) -> Dict[str, Dict[str, float]]:
        """获取各阶段内存使用"""
        return dict(self._snapshots)


class LightProfiler:
    """光明性能分析器"""

    def __init__(self):
        self.stats = {}
        self.traces = []
        self._phase_timer = PhaseTimer()
        self._memory_tracker = MemoryTracker()

    def profile(self, filepath: str, memory: bool = False, report: bool = False,
                profile_report: bool = False) -> dict:
        """分析光明程序的性能

        Args:
            filepath: 光明文件路径
            memory: 是否分析内存
            report: 是否生成详细报告
            profile_report: 是否生成编译器性能分析报告（含阶段分解）

        Returns:
            性能分析结果
        """
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        # 重置计时器
        self._phase_timer = PhaseTimer()
        self._memory_tracker = MemoryTracker()

        # 读取源代码
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        file_size = len(source)
        file_lines = source.count('\n') + 1

        # 启动内存追踪（如果启用）
        if memory:
            self._memory_tracker.start()

        # ====== 阶段1: 词法分析 ======
        if profile_report:
            self._phase_timer.start_phase('词法分析')
        lex_start = time.time()
        from lexer import Lexer
        lexer = Lexer()
        tokens = lexer.tokenize(source)
        lex_time = (time.time() - lex_start) * 1000
        if profile_report:
            self._phase_timer.stop_phase()
            self._memory_tracker.snapshot('词法分析')

        # ====== 阶段2: 语法解析 ======
        if profile_report:
            self._phase_timer.start_phase('语法解析')
        parse_start = time.time()
        parser = LightParser()
        module = parser.parse(source)
        parse_time = (time.time() - parse_start) * 1000
        if profile_report:
            self._phase_timer.stop_phase()
            self._memory_tracker.snapshot('语法解析')

        # ====== 阶段3: AST适配 ======
        if profile_report:
            self._phase_timer.start_phase('AST适配')
        adapt_start = time.time()
        from compiler import AstAdapter
        adapter = AstAdapter()
        our_ast = adapter.convert_module(module)
        adapt_time = (time.time() - adapt_start) * 1000
        if profile_report:
            self._phase_timer.stop_phase()
            self._memory_tracker.snapshot('AST适配')

        # ====== 阶段4: 优化 ======
        if profile_report:
            self._phase_timer.start_phase('优化')
        opt_start = time.time()
        from compiler import OPTIMIZERS
        for optimizer_cls in OPTIMIZERS:
            optimizer = optimizer_cls()
            our_ast = optimizer.optimize(our_ast)
        opt_time = (time.time() - opt_start) * 1000
        if profile_report:
            self._phase_timer.stop_phase()
            self._memory_tracker.snapshot('优化')

        # ====== 阶段5: 代码生成 ======
        if profile_report:
            self._phase_timer.start_phase('代码生成')
        codegen_start = time.time()
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)
        codegen_time = (time.time() - codegen_start) * 1000
        if profile_report:
            self._phase_timer.stop_phase()
            self._memory_tracker.snapshot('代码生成')

        compile_time = lex_time + parse_time + adapt_time + opt_time + codegen_time

        # 统计信息
        stats = {
            'file': os.path.basename(filepath),
            'source_size': file_size,
            'source_lines': file_lines,
            'compile_time_ms': round(compile_time, 2),
            'code_size': len(py_code),
            'code_lines': py_code.count('\n') + 1,
        }

        # 阶段分解（仅 profile_report 模式）
        if profile_report:
            phase_data = self._phase_timer.get_breakdown()
            stats['phase_breakdown'] = phase_data
            stats['phase_times_ms'] = {
                'lexer': round(lex_time, 3),
                'parser': round(parse_time, 3),
                'adapter': round(adapt_time, 3),
                'optimizer': round(opt_time, 3),
                'codegen': round(codegen_time, 3),
            }

        # 执行时间分析
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
            mem_stats = self._memory_tracker.stop()
            stats['memory_current_kb'] = mem_stats.get('current_kb', 0)
            stats['memory_peak_kb'] = mem_stats.get('peak_kb', 0)
            if profile_report:
                stats['memory_by_phase'] = self._memory_tracker.get_phase_memory()

        stats['total_time_ms'] = round(compile_time + exec_time, 2)

        # 生成报告
        if report or profile_report:
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
        pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(20)

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

        # 阶段分解
        if 'phase_breakdown' in stats:
            report['phase_breakdown'] = stats['phase_breakdown']

        # 内存信息
        if 'memory_current_kb' in stats:
            report['memory'] = {
                'current': f"{stats['memory_current_kb']} KB",
                'peak': f"{stats['memory_peak_kb']} KB"
            }

        if 'memory_by_phase' in stats:
            report['memory_by_phase'] = {
                phase: {
                    'current': f"{m['current_kb']} KB",
                    'peak': f"{m['peak_kb']} KB"
                }
                for phase, m in stats['memory_by_phase'].items()
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

            # 阶段分解建议
            phase_times = stats.get('phase_times_ms', {})
            if phase_times:
                total_compile = sum(phase_times.values()) or 1
                for phase_name, pt in sorted(phase_times.items(), key=lambda x: -x[1]):
                    pct = pt / total_compile * 100
                    if pct > 40:
                        suggestions.append(f'"{phase_name}" 阶段耗时占比 {pct:.1f}%，考虑优化此阶段')

            if suggestions:
                report['suggestions'] = suggestions

        return report


def format_profile_output(stats: dict, report: bool = False, cprofile: bool = False,
                          profile_report: bool = False):
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

    # 阶段分解（profile_report 模式）
    if profile_report and 'phase_breakdown' in stats:
        print("  [编译阶段分解]")
        breakdown = stats['phase_breakdown']['breakdown']
        for phase_name in stats['phase_breakdown']['phase_order']:
            if phase_name in breakdown:
                pd = breakdown[phase_name]
                bar = '█' * int(pd['percentage'] / 5) + '░' * (20 - int(pd['percentage'] / 5))
                print(f"    {phase_name:8s} {pd['time_ms']:8.2f} ms {bar} {pd['percentage']:.1f}%")
        print(f"    {'合计':8s} {stats['phase_breakdown']['total_ms']:8.2f} ms")
        print()

    # 执行信息
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

    # 阶段内存分解
    if 'memory_by_phase' in stats:
        print("  [阶段内存峰值]")
        for phase_name, mem in stats['memory_by_phase'].items():
            print(f"    {phase_name:8s} 当前: {mem['current_kb']:>8.2f} KB, 峰值: {mem['peak_kb']:>8.2f} KB")
        print()

    # 报告
    if (report or profile_report) and 'report' in stats:
        r = stats['report']
        print("  [性能报告]")
        print(f"    评级: {r.get('grade', 'N/A')}")
        if 'suggestions' in r:
            print(f"    建议:")
            for s in r['suggestions']:
                print(f"      - {s}")
        if 'memory' in r:
            print(f"    内存: 当前 {r['memory']['current']}, 峰值 {r['memory']['peak']}")
        if 'phase_breakdown' in r:
            print(f"    编译阶段分解:")
            for phase_name, pd in r['phase_breakdown']['breakdown'].items():
                print(f"      {phase_name}: {pd['time_ms']} ms ({pd['percentage']}%)")
        print()

    print("=" * 60)


def run_profile(target: str, memory: bool = False, report: bool = False,
                cprofile: bool = False, profile_report: bool = False):
    """运行性能分析"""
    profiler = LightProfiler()

    if cprofile:
        stats = profiler.profile_with_cprofile(target)
        format_profile_output(stats, cprofile=True)
    else:
        stats = profiler.profile(target, memory=memory, report=report,
                                 profile_report=profile_report)
        format_profile_output(stats, report=report, profile_report=profile_report)

    # 保存报告到文件
    if report or profile_report:
        report_path = os.path.splitext(target)[0] + '_profile.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"  详细报告已保存: {report_path}")