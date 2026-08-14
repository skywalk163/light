#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（Duan）编译器性能分析工具

分析编译各阶段耗时：
  - 词法分析 (Lexer.tokenize)
  - 语法解析 (DuanParser.parse)
  - 代码生成 (PythonCodeGenerator.generate)
  - 总编译流水线

支持大文件（100KB+）性能测试、内存使用分析。

用法:
  python tools/compiler_profiler.py [file.duan]
  python tools/compiler_profiler.py --generate-large  # 生成大文件并测试
  python tools/compiler_profiler.py --report          # 生成性能分析报告
"""

import sys
import os
import time
import tracemalloc
import gc
from pathlib import Path
from typing import List, Dict, Tuple

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / 'src'))
sys.path.insert(0, str(PROJECT_DIR))

from lexer import Lexer, LexerError
from duan_parser_v3 import DuanParser, ParseError
from code_generator import PythonCodeGenerator
from ast_nodes_v3 import Module


def generate_large_test_file(size_kb: int = 100) -> str:
    """生成大段言测试文件，用于性能测试"""
    lines = []
    lines.append("# 大型段言性能测试文件\n")
    lines.append("导入 数学\n")
    lines.append("")

    # 生成大量函数定义
    for i in range(100):
        lines.append(f"段落 func_{i} 接收 x, y：")
        lines.append(f"    设 r 为 x * y + {i}")
        lines.append(f"    如果 r 大于 100：")
        lines.append(f"        返回 r / 2")
        lines.append(f"    否则：")
        lines.append(f"        返回 r * 2")
        lines.append("")

    # 生成列表操作
    for i in range(20):
        lines.append(f"设 lst_{i} 为 [{i}, {i+1}, {i+2}, {i+3}, {i+4}]")
        lines.append(f"设 lst_{i}_s 为 lst_{i}[0] + lst_{i}[1] + lst_{i}[2]")
        lines.append("")

    # 生成条件嵌套
    lines.append("段落 deep_nest 接收 n：")
    for i in range(10):
        indent = "    " * (i + 1)
        lines.append(f"{indent}如果 n 等于 {i}：")
        indent2 = "    " * (i + 2)
        lines.append(f"{indent2}设 r 为 n * {i}")
    indent_final = "    " * 12
    lines.append(f"{indent_final}返回 r")
    lines.append("")

    # 生成类定义
    for i in range(5):
        lines.append(f"类 MyClass_{i}：")
        lines.append(f"    属性 a")
        lines.append(f"    段落 init 接收 x：")
        lines.append(f"        己.a 为 x")
        lines.append(f"    段落 calc 接收：")
        lines.append(f"        返回 己.a + {i}")
        lines.append("")

    # 生成主函数调用
    lines.append("段落 main 接收：")
    lines.append("    设 total 为 0")
    for i in range(50):
        lines.append(f"    设 res_{i} 为 func_{i % 100}({i}, {i + 1})")
        lines.append(f"    设 total 为 total + res_{i}")
    lines.append("    返回 total")
    lines.append("")

    lines.append("main()")
    lines.append("")

    content = "\n".join(lines)

    # 确保达到目标大小
    while len(content.encode('utf-8')) < size_kb * 1024:
        # 添加更多重复内容
        for i in range(100, 200):
            lines.append(f"段落 额外函数_{i} 接收 x：")
            lines.append(f"    返回 x * {i}")
            lines.append("")
        content = "\n".join(lines)

    actual_size = len(content.encode('utf-8'))
    return content, actual_size


class CompilerProfiler:
    """编译器性能分析器"""

    def __init__(self):
        self.results = {}

    def profile_stage(self, name: str, fn, *args, **kwargs) -> Tuple[any, float, float]:
        """分析单个阶段，返回 (结果, 耗时_ms, 内存峰值_kb)"""
        gc.collect()
        tracemalloc.start()

        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_kb = peak / 1024
        return result, elapsed, memory_kb

    def profile_compilation(self, source: str, name: str = "测试文件") -> Dict:
        """分析完整编译流水线"""
        print(f"\n{'=' * 60}")
        print(f"  编译器性能分析: {name}")
        print(f"{'=' * 60}")
        print(f"  源码大小: {len(source)} 字节 ({len(source.encode('utf-8')) / 1024:.1f} KB)")
        print(f"  源码行数: {source.count(chr(10)) + 1}")
        print()

        stages = {}

        # Stage 1: 词法分析
        lexer = Lexer()
        tokens, lex_time, lex_mem = self.profile_stage("词法分析", lexer.tokenize, source)
        stages['词法分析'] = {'time_ms': round(lex_time, 2), 'memory_kb': round(lex_mem, 2), 'tokens': len(tokens)}
        print(f"  [词法分析] {lex_time:.2f}ms | {lex_mem:.2f}KB | {len(tokens)} tokens")

        # Stage 2: 语法解析（含词法分析）
        parser = DuanParser()
        module, parse_time, parse_mem = self.profile_stage("语法解析", parser.parse, source)
        parse_time_excluding_lex = max(parse_time - lex_time, 0)  # 减去词法分析时间
        stages['语法解析（含词法）'] = {'time_ms': round(parse_time, 2), 'memory_kb': round(parse_mem, 2), 'nodes': self._count_ast_nodes(module)}
        stages['语法解析（纯解析）'] = {'time_ms': round(parse_time_excluding_lex, 2)}
        print(f"  [语法解析] {parse_time:.2f}ms (纯解析: {parse_time_excluding_lex:.2f}ms) | {parse_mem:.2f}KB | AST节点: {stages['语法解析（含词法）']['nodes']}")

        # Stage 3: 代码生成
        generator = PythonCodeGenerator()
        py_code, gen_time, gen_mem = self.profile_stage("代码生成", generator.generate, module)
        stages['代码生成'] = {'time_ms': round(gen_time, 2), 'memory_kb': round(gen_mem, 2), 'code_lines': py_code.count(chr(10)) + 1}
        print(f"  [代码生成] {gen_time:.2f}ms | {gen_mem:.2f}KB | {py_code.count(chr(10)) + 1} 行代码")

        # 总流水线
        total_time = parse_time + gen_time
        stages['总流水线'] = {'time_ms': round(total_time, 2)}
        print(f"  [总流水线] {total_time:.2f}ms")

        # 各阶段占比
        print()
        print(f"  --- 各阶段耗时占比 ---")
        for stage_name, data in stages.items():
            if 'time_ms' in data and total_time > 0:
                pct = data['time_ms'] / total_time * 100
                bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                print(f"  {stage_name:12s}: {data['time_ms']:8.2f}ms ({pct:5.1f}%) {bar}")

        # 阶段间数据
        pipeline = {
            'name': name,
            'source_size': len(source),
            'source_size_kb': round(len(source.encode('utf-8')) / 1024, 1),
            'source_lines': source.count(chr(10)) + 1,
            'stages': stages,
            'total_time_ms': round(total_time, 2),
        }
        self.results[name] = pipeline
        return pipeline

    def _count_ast_nodes(self, module) -> int:
        """递归统计 AST 节点数"""
        count = 1  # 当前节点
        for attr_name in dir(module):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(module, attr_name)
                if isinstance(attr, list):
                    for item in attr:
                        if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool)):
                            count += self._count_ast_nodes(item)
                elif hasattr(attr, '__dict__') and not isinstance(attr, (str, int, float, bool, type(None))):
                    count += self._count_ast_nodes(attr)
            except Exception:
                pass
        return count

    def profile_file(self, filepath: str) -> Dict:
        """分析单个段言文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        return self.profile_compilation(source, Path(filepath).name)

    def generate_report(self, output_path: str):
        """生成 Markdown 性能分析报告"""
        lines = []
        lines.append("# 段言编译器性能分析报告")
        lines.append("")
        lines.append("> 生成时间: 2026-08-07")
        lines.append("> 测试环境: 段言 v5.5.0 (SRC 后端)")
        lines.append("")
        lines.append("## 测试概述")
        lines.append("")
        lines.append("本报告对段言编译器的各阶段进行性能分析，包括：")
        lines.append("")
        lines.append("- **词法分析** (Lexer.tokenize)：将源码拆分为 Token 流")
        lines.append("- **语法解析** (DuanParser.parse)：将 Token 流构建为 AST")
        lines.append("- **代码生成** (PythonCodeGenerator.generate)：将 AST 转换为 Python 代码")
        lines.append("")
        lines.append("## 测试结果")
        lines.append("")

        for name, pipeline in self.results.items():
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"- 源码大小: {pipeline['source_size_kb']} KB ({pipeline['source_lines']} 行)")
            lines.append(f"- 总编译耗时: {pipeline['total_time_ms']:.2f} ms")
            lines.append("")

            stages = pipeline.get('stages', {})
            if stages:
                lines.append("| 阶段 | 耗时 (ms) | 占比 | 内存 (KB) | 产出 |")
                lines.append("|------|----------|------|-----------|------|")
                total = stages.get('总流水线', {}).get('time_ms', 0)
                stage_order = ['词法分析', '语法解析（含词法）', '语法解析（纯解析）', '代码生成', '总流水线']
                for stage_name in stage_order:
                    if stage_name in stages:
                        data = stages[stage_name]
                        time_str = f"{data['time_ms']:.2f}"
                        pct = f"{data['time_ms'] / total * 100:.1f}%" if total > 0 else "N/A"
                        mem_str = f"{data.get('memory_kb', 'N/A')}"
                        if stage_name == '词法分析':
                            output = f"{data.get('tokens', 'N/A')} tokens"
                        elif stage_name == '语法解析（含词法）':
                            output = f"{data.get('nodes', 'N/A')} AST节点"
                        elif stage_name == '语法解析（纯解析）':
                            output = "（词法分析已分离）"
                        elif stage_name == '代码生成':
                            output = f"{data.get('code_lines', 'N/A')} 行Python"
                        else:
                            output = "-"
                        lines.append(f"| {stage_name} | {time_str} | {pct} | {mem_str} | {output} |")
                lines.append("")

        lines.append("## 性能分析")
        lines.append("")

        # 计算平均数据
        all_total_times = [p['total_time_ms'] for p in self.results.values()]
        if all_total_times:
            avg_total = sum(all_total_times) / len(all_total_times)
            lines.append(f"- 平均总编译耗时: {avg_total:.2f} ms")
            lines.append(f"- 测试文件数: {len(self.results)}")
            lines.append("")

        lines.append("### 瓶颈分析")
        lines.append("")
        lines.append("1. **语法解析** 通常是编译管道的瓶颈，尤其在处理大量嵌套结构时")
        lines.append("2. **代码生成** 的耗时与 AST 节点数成正比，大型 AST 可导致显著延迟")
        lines.append("3. **词法分析** 相对轻量，但随着源码增大仍可能成为瓶颈")
        lines.append("")
        lines.append("### 优化建议")
        lines.append("")
        lines.append("1. **三态缓存**：编译器缓存系统（CompilerCache）可缓存各阶段结果，避免重复编译")
        lines.append("2. **增量编译**：增量构建系统（IncrementalBuilder）只编译变更部分")
        lines.append("3. **并行编译**：多文件项目可并行执行词法分析阶段")
        lines.append("4. **AST 优化**：减少 AST 节点数量可降低代码生成耗时")
        lines.append("")
        lines.append("> 注：以上数据基于 SRC 后端的 Python 解释执行环境。")
        lines.append("> LLVM 后端将使用不同的编译管道，性能特征可能有所不同。")
        lines.append("")

        report = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到: {output_path}")

    def profile_examples(self, example_dir: str = None):
        """分析示例目录中的文件"""
        if example_dir is None:
            example_dir = str(PROJECT_DIR / 'examples')

        files = []
        for root, _dirs, filenames in os.walk(example_dir):
            for f in filenames:
                if f.endswith('.duan'):
                    files.append(os.path.join(root, f))

        print(f"\n找到 {len(files)} 个段言文件")
        for filepath in sorted(files):
            try:
                self.profile_file(filepath)
            except Exception as e:
                print(f"  [错误] {filepath}: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='段言编译器性能分析工具')
    parser.add_argument('file', nargs='?', help='要分析的段言文件')
    parser.add_argument('--generate-large', action='store_true', help='生成大文件并测试')
    parser.add_argument('--report', action='store_true', help='生成性能分析报告')
    parser.add_argument('--examples', action='store_true', help='分析所有示例文件')
    args = parser.parse_args()

    profiler = CompilerProfiler()

    if args.file:
        profiler.profile_file(args.file)

    if args.examples:
        profiler.profile_examples()

    if args.generate_large:
        # 生成大文件并测试
        for size_kb in [10, 50, 100, 200]:
            print(f"\n生成 {size_kb}KB 测试文件...")
            source, actual_size = generate_large_test_file(size_kb)
            profiler.profile_compilation(source, f"大文件 ({size_kb}KB)")

    if not args.file and not args.examples and not args.generate_large:
        # 默认：分析标准示例文件 + 大文件
        examples = [
            str(PROJECT_DIR / 'examples' / 'hello.duan'),
            str(PROJECT_DIR / 'examples' / 'basic.duan'),
            str(PROJECT_DIR / 'examples' / 'hanoi.duan'),
            str(PROJECT_DIR / 'examples' / 'calculator.duan'),
            str(PROJECT_DIR / 'examples' / 'class_example.duan'),
            str(PROJECT_DIR / 'examples' / 'student_management.duan'),
        ]
        for filepath in examples:
            if os.path.isfile(filepath):
                profiler.profile_file(filepath)

        # 大文件测试
        for size_kb in [10, 50, 100, 200]:
            print(f"\n生成 {size_kb}KB 测试文件...")
            source, actual_size = generate_large_test_file(size_kb)
            profiler.profile_compilation(source, f"大文件 ({size_kb}KB)")

    # 生成报告
    if args.report or not args.file:
        output_path = str(PROJECT_DIR / 'docs' / 'compiler_perf_report.md')
        profiler.generate_report(output_path)

    print("\n" + "=" * 60)
    print("性能分析完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()