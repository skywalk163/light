# -*- coding: utf-8 -*-
"""
光明编译器 - 性能基准测试

测试编译器各模块的性能表现
"""

import sys
import os
import io
import time
import statistics
from typing import List, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'antlrparser'))

from light_tokenizer import LightLangTokenizer as Lexer
from light_visitor import LightParser


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.lexer = Lexer()
        self.parser = LightParser()
    
    def measure_time(self, func, *args, iterations: int = 100) -> Tuple[float, float, float]:
        """
        测量函数执行时间
        
        Returns:
            (平均时间, 最小时间, 最大时间) 单位：毫秒
        """
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # 转换为毫秒
        
        return statistics.mean(times), min(times), max(times)
    
    def benchmark_lexer(self, code: str, name: str, iterations: int = 100):
        """词法分析器基准测试"""
        avg_time, min_time, max_time = self.measure_time(
            self.lexer.tokenize, code, iterations=iterations
        )
        
        tokens = self.lexer.tokenize(code)
        token_count = len(tokens)
        
        print(f"\n{name}:")
        print(f"  代码长度: {len(code)} 字符")
        print(f"  Token数量: {token_count}")
        print(f"  平均时间: {avg_time:.3f} ms")
        print(f"  最小时间: {min_time:.3f} ms")
        print(f"  最大时间: {max_time:.3f} ms")
        print(f"  吞吐量: {len(code) / avg_time:.1f} chars/ms")
        
        return {
            'name': name,
            'code_length': len(code),
            'token_count': token_count,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'throughput': len(code) / avg_time
        }
    
    def benchmark_parser(self, code: str, name: str, iterations: int = 50):
        """语法解析器基准测试"""
        avg_time, min_time, max_time = self.measure_time(
            self.parser.parse, code, iterations=iterations
        )

        module = self.parser.parse(code)
        # 统计段落、类和语句数量
        stmt_count = len(module.segments) if module else 0

        print(f"\n{name}:")
        print(f"  代码长度: {len(code)} 字符")
        print(f"  段落数量: {stmt_count}")
        print(f"  平均时间: {avg_time:.3f} ms")
        print(f"  最小时间: {min_time:.3f} ms")
        print(f"  最大时间: {max_time:.3f} ms")
        print(f"  吞吐量: {len(code) / avg_time:.1f} chars/ms")

        return {
            'name': name,
            'code_length': len(code),
            'stmt_count': stmt_count,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'throughput': len(code) / avg_time
        }

    def benchmark_full_compile(self, code: str, name: str, iterations: int = 20):
        """完整编译流程基准测试（解析+解释执行）"""
        def compile_pipeline():
            tokens = self.lexer.tokenize(code)
            module = self.parser.parse(code)
            return module

        avg_time, min_time, max_time = self.measure_time(
            compile_pipeline, iterations=iterations
        )

        module = compile_pipeline()

        print(f"\n{name}:")
        print(f"  代码长度: {len(code)} 字符")
        print(f"  平均时间: {avg_time:.3f} ms")
        print(f"  最小时间: {min_time:.3f} ms")
        print(f"  最大时间: {max_time:.3f} ms")
        print(f"  吞吐量: {len(code) / avg_time:.1f} chars/ms")

        return {
            'name': name,
            'code_length': len(code),
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'throughput': len(code) / avg_time
        }


def run_benchmarks():
    """运行所有基准测试"""
    print("=" * 70)
    print("光明编译器性能基准测试")
    print("=" * 70)
    
    benchmark = PerformanceBenchmark()
    
    # 测试用例
    test_cases = [
        # 简单变量声明
        ("简单变量", '设甲为123。'),
        
        # 算术表达式
        ("算术表达式", '设结果为三加五乘二。'),
        
        # 条件语句
        ("条件语句", '如果甲大于乙那么打印甲。否则打印乙。'),
        
        # 函数定义
        ("函数定义", '《加法》段(甲, 乙)：返回甲加乙。'),
        
        # 复杂函数
        ("递归函数", '''《阶乘》段(数)：
  如果数小于等于一那么返回一。
  返回数乘《阶乘》参数数减一。'''),
        
        # 多语句
        ("多语句", '设甲为1。设乙为2。设丙为3。设丁为4。设戊为5。'),
        
        # 大量变量声明
        ("大量变量", '\n'.join([f'定义变量{i}等于{i}。' for i in range(50)])),
    ]
    
    # 词法分析器测试
    print("\n" + "=" * 70)
    print("词法分析器性能测试")
    print("=" * 70)
    
    lexer_results = []
    for name, code in test_cases:
        result = benchmark.benchmark_lexer(code, name, iterations=100)
        lexer_results.append(result)
    
    # 语法解析器测试
    print("\n" + "=" * 70)
    print("语法解析器性能测试")
    print("=" * 70)
    
    parser_results = []
    for name, code in test_cases:
        result = benchmark.benchmark_parser(code, name, iterations=50)
        parser_results.append(result)
    
    # 完整编译流程测试
    print("\n" + "=" * 70)
    print("完整编译流程性能测试")
    print("=" * 70)
    
    compile_results = []
    for name, code in test_cases[:5]:  # 只测试前5个
        result = benchmark.benchmark_full_compile(code, name, iterations=20)
        compile_results.append(result)
    
    # 性能总结
    print("\n" + "=" * 70)
    print("性能总结")
    print("=" * 70)
    
    # 词法分析器平均性能
    lexer_avg_time = statistics.mean([r['avg_time'] for r in lexer_results])
    lexer_avg_throughput = statistics.mean([r['throughput'] for r in lexer_results])
    
    print(f"\n词法分析器:")
    print(f"  平均编译时间: {lexer_avg_time:.3f} ms")
    print(f"  平均吞吐量: {lexer_avg_throughput:.1f} chars/ms")
    
    # 语法解析器平均性能
    parser_avg_time = statistics.mean([r['avg_time'] for r in parser_results])
    parser_avg_throughput = statistics.mean([r['throughput'] for r in parser_results])
    
    print(f"\n语法解析器:")
    print(f"  平均编译时间: {parser_avg_time:.3f} ms")
    print(f"  平均吞吐量: {parser_avg_throughput:.1f} chars/ms")
    
    # 完整编译平均性能
    compile_avg_time = statistics.mean([r['avg_time'] for r in compile_results])
    compile_avg_throughput = statistics.mean([r['throughput'] for r in compile_results])
    
    print(f"\n完整编译流程:")
    print(f"  平均编译时间: {compile_avg_time:.3f} ms")
    print(f"  平均吞吐量: {compile_avg_throughput:.1f} chars/ms")
    
    # 性能等级评估
    print("\n" + "=" * 70)
    print("性能等级评估")
    print("=" * 70)
    
    # 简单代码编译时间
    simple_compile_time = compile_results[0]['avg_time']
    
    if simple_compile_time < 5:
        performance_grade = "优秀"
        emoji = "🌟🌟🌟"
    elif simple_compile_time < 10:
        performance_grade = "良好"
        emoji = "🌟🌟"
    elif simple_compile_time < 20:
        performance_grade = "一般"
        emoji = "🌟"
    else:
        performance_grade = "需优化"
        emoji = "⚠️"
    
    print(f"\n简单代码编译时间: {simple_compile_time:.3f} ms")
    print(f"性能等级: {performance_grade} {emoji}")
    
    print("\n" + "=" * 70)
    print("基准测试完成")
    print("=" * 70)
    
    return {
        'lexer': lexer_results,
        'parser': parser_results,
        'compile': compile_results,
        'summary': {
            'lexer_avg_time': lexer_avg_time,
            'parser_avg_time': parser_avg_time,
            'compile_avg_time': compile_avg_time,
            'performance_grade': performance_grade
        }
    }


class StdlibBenchmark:
    """标准库性能基准测试"""

    def __init__(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))

    def measure_time(self, func, iterations: int = 1000) -> Tuple[float, float, float]:
        """测量函数执行时间"""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        return statistics.mean(times), min(times), max(times)

    def benchmark_哈希(self):
        """测试哈希模块性能"""
        from 加密 import MD5, SHA256, SHA512

        data = 'hello world' * 100

        def test_md5():
            return MD5(data)

        def test_sha256():
            return SHA256(data)

        def test_sha512():
            return SHA512(data)

        print(f"\n  哈希模块 (数据长度: {len(data)}):")
        for name, func in [('MD5', test_md5), ('SHA256', test_sha256), ('SHA512', test_sha512)]:
            avg, mn, mx = self.measure_time(func, iterations=500)
            print(f"    {name}: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")

    def benchmark_JSON(self):
        """测试 JSON 模块性能"""
        import json

        data = {'key' + str(i): 'value' + str(i) for i in range(100)}
        json_str = json.dumps(data)

        from JSON import 解析JSON, 生成JSON

        def test_parse():
            return 解析JSON(json_str)

        def test_generate():
            return 生成JSON(data)

        print(f"\n  JSON模块 (100个字段):")
        avg, mn, mx = self.measure_time(test_parse, iterations=500)
        print(f"    解析JSON: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")
        avg, mn, mx = self.measure_time(test_generate, iterations=500)
        print(f"    生成JSON: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")

    def benchmark_缓存(self):
        """测试缓存模块性能"""
        from 缓存 import 缓存管理器

        cache = 缓存管理器(类型='lru', 最大容量=1000)

        def test_cache_ops():
            for i in range(100):
                cache.设置(f'key{i}', i)
            for i in range(100):
                _ = cache.获取(f'key{i}')

        print(f"\n  缓存模块 (LRU, 100次读写):")
        avg, mn, mx = self.measure_time(test_cache_ops, iterations=200)
        print(f"    平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")

    def benchmark_数据验证(self):
        """测试数据验证模块性能"""
        from 数据验证 import 验证邮箱, 验证手机号, 验证必填, 验证集合

        emails = ['test@example.com', 'user.name+tag@domain.co.uk', 'a@b.c']
        phones = ['13812345678', '15912345678', '18812345678']

        def test_email():
            for e in emails:
                验证邮箱(e)

        def test_phone():
            for p in phones:
                验证手机号(p)

        def test_validation_set():
            规则 = {
                'name': [('必填',), ('长度', 1, 50)],
                'age': [('类型', int), ('范围', 0, 150)],
                'email': [('邮箱',)],
            }
            数据 = {'name': '张三', 'age': 25, 'email': 'test@example.com'}
            验证集合(规则, 数据)

        print(f"\n  数据验证模块:")
        avg, mn, mx = self.measure_time(test_email, iterations=500)
        print(f"    邮箱验证(3个): 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")
        avg, mn, mx = self.measure_time(test_phone, iterations=500)
        print(f"    手机号验证(3个): 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")
        avg, mn, mx = self.measure_time(test_validation_set, iterations=500)
        print(f"    批量验证: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")

    def benchmark_正则表达式(self):
        """测试正则表达式模块性能"""
        from 正则表达式 import 匹配, 查找全部, 替换

        text = 'hello123world456python789' * 100

        def test_match():
            return 匹配(r'\d+', text)

        def test_findall():
            return 查找全部(r'\d+', text)

        def test_replace():
            return 替换(r'\d+', 'X', text)

        print(f"\n  正则表达式模块 (文本长度: {len(text)}):")
        avg, mn, mx = self.measure_time(test_match, iterations=200)
        print(f"    匹配: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")
        avg, mn, mx = self.measure_time(test_findall, iterations=200)
        print(f"    查找全部: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")
        avg, mn, mx = self.measure_time(test_replace, iterations=200)
        print(f"    替换: 平均={avg:.3f}ms, 最小={mn:.3f}ms, 最大={mx:.3f}ms")

    def run_all(self):
        """运行所有标准库性能基准测试"""
        print("\n" + "=" * 70)
        print("标准库性能基准测试")
        print("=" * 70)

        self.benchmark_哈希()
        self.benchmark_JSON()
        self.benchmark_缓存()
        self.benchmark_数据验证()
        self.benchmark_正则表达式()

        print("\n" + "=" * 70)
        print("标准库基准测试完成")
        print("=" * 70)


def run_stdlib_benchmarks():
    """运行标准库性能基准测试"""
    benchmark = StdlibBenchmark()
    benchmark.run_all()


if __name__ == '__main__':
    run_benchmarks()
    run_stdlib_benchmarks()
