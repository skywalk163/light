# -*- coding: utf-8 -*-
"""
光明（Light）测试运行器

支持：
  - 自动发现 tests/ 目录下的 .light 测试文件
  - 运行单个或多个测试文件
  - 计时统计
  - 过滤测试
  - 详细输出

用法：
  light test                        # 运行当前项目的所有测试
  light test -v                     # 详细输出
  light test --filter <名称>        # 按名称过滤
  light test tests/test_math.light   # 运行指定文件
"""

import os
import sys
import time
import io
import glob
import traceback

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def discover_test_files(directory: str, pattern: str = None) -> list:
    """发现测试文件

    按以下规则查找：
    1. tests/ 目录下的所有 .light 文件（递归）
    2. 当前目录下匹配 *_test.light 或 test_*.light 的文件

    Args:
        directory: 项目根目录
        pattern: 过滤模式（可选）

    Returns:
        测试文件路径列表
    """
    test_files = []

    # 规则1: tests/ 目录
    tests_dir = os.path.join(directory, 'tests')
    if os.path.isdir(tests_dir):
        for root, dirs, files in os.walk(tests_dir):
            for f in files:
                if f.endswith('.light'):
                    test_files.append(os.path.join(root, f))

    # 规则2: 根目录下的 *_test.light 和 test_*.light
    for fname in os.listdir(directory):
        if fname.endswith('.light'):
            if fname.endswith('_test.light') or fname.startswith('test_'):
                fpath = os.path.join(directory, fname)
                if os.path.isfile(fpath) and fpath not in test_files:
                    test_files.append(fpath)

    # 应用过滤
    if pattern:
        test_files = [f for f in test_files if pattern.lower() in os.path.basename(f).lower()]

    return sorted(test_files)


def run_test_file(filepath: str, verbose: bool = False) -> dict:
    """运行单个测试文件

    Args:
        filepath: .light 文件路径
        verbose: 是否详细输出

    Returns:
        {'name': str, 'passed': bool, 'time': float, 'output': str, 'error': str}
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    name = os.path.basename(filepath)
    start_time = time.time()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        # 编译
        parser = LightParser()
        module = parser.parse(source)
        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 执行
        output_lines = []
        def capture_print(*args, **kwargs):
            line = ' '.join(str(a) for a in args)
            output_lines.append(line)

        namespace = {
            'print': capture_print,
            '__name__': '__main__',
            '__file__': filepath
        }

        # 预加载同目录下的 源.light 作为模块，供测试文件导入
        test_dir = os.path.dirname(os.path.abspath(filepath))
        src_file = os.path.join(test_dir, '源.light')
        if os.path.exists(src_file):
            import re as _re
            toml_file = os.path.join(test_dir, '段件.toml')
            pkg_name = None
            if os.path.exists(toml_file):
                with open(toml_file, 'r', encoding='utf-8') as tf:
                    toml_text = tf.read()
                m = _re.search(r'名称\s*=\s*"([^"]+)"', toml_text)
                if m:
                    pkg_name = m.group(1)
            if pkg_name:
                with open(src_file, 'r', encoding='utf-8') as sf:
                    src_source = sf.read()
                src_parser = LightParser()
                src_module = src_parser.parse(src_source)
                src_generator = PythonCodeGenerator()
                src_py_code = src_generator.generate(src_module)
                src_namespace = dict(namespace)
                exec(src_py_code, src_namespace)
                # 注册为 Python 模块，使 from pkg_name import * 可用
                import types
                mod = types.ModuleType(pkg_name)
                for k, v in src_namespace.items():
                    if not k.startswith('__'):
                        setattr(mod, k, v)
                sys.modules[pkg_name] = mod

        exec(py_code, namespace)

        elapsed = (time.time() - start_time) * 1000
        output = '\n'.join(output_lines)

        if verbose and output:
            print(f"    输出: {output.replace(chr(10), chr(10) + '          ')}")

        return {
            'name': name,
            'passed': True,
            'time': elapsed,
            'output': output,
            'error': ''
        }

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        tb = traceback.format_exc()

        if verbose:
            print(f"    错误: {e}")
            for line in tb.split('\n')[-6:]:
                if line.strip():
                    print(f"          {line}")

        return {
            'name': name,
            'passed': False,
            'time': elapsed,
            'output': '',
            'error': str(e)
        }


def run_tests(directory: str, filter_pattern: str = None, verbose: bool = False) -> int:
    """运行所有测试

    Args:
        directory: 项目根目录
        filter_pattern: 过滤模式
        verbose: 详细输出

    Returns:
        退出码（0=全部通过, 1=有失败）
    """
    # 添加 src 到路径
    project_dir = directory
    while project_dir and not os.path.exists(os.path.join(project_dir, 'src')):
        parent = os.path.dirname(project_dir)
        if parent == project_dir:
            break
        project_dir = parent

    src_dir = os.path.join(project_dir, 'src')
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # 发现测试文件
    test_files = discover_test_files(directory, filter_pattern)
    if not test_files:
        print("未找到测试文件。")
        print("测试文件应放在 tests/ 目录下，或以 test_*.light / *_test.light 命名。")
        return 0

    print("=" * 60)
    print(f"  光明测试运行器")
    print(f"  项目目录: {directory}")
    print(f"  找到 {len(test_files)} 个测试文件")
    print("=" * 60)
    print()

    results = []
    passed_count = 0
    failed_count = 0
    total_time = 0

    for i, filepath in enumerate(test_files):
        name = os.path.basename(filepath)
        print(f"  [{i+1}/{len(test_files)}] {name} ... ", end='', flush=True)

        result = run_test_file(filepath, verbose)
        results.append(result)
        total_time += result['time']

        if result['passed']:
            print(f"OK ({result['time']:.1f}ms)")
            passed_count += 1
        else:
            print(f"FAIL ({result['time']:.1f}ms) - {result['error']}")
            failed_count += 1

    # 打印汇总
    print()
    print("=" * 60)
    print("  测试汇总")
    print("=" * 60)

    total = passed_count + failed_count
    for r in results:
        status = "OK" if r['passed'] else "FAIL"
        print(f"  [{status}] {r['name']} ({r['time']:.1f}ms)")

    print()
    if failed_count == 0:
        print(f"  [OK] 全部 {total} 个测试通过！总耗时 {total_time:.1f}ms")
    else:
        print(f"  [FAIL] {passed_count}/{total} 通过, {failed_count} 失败")
        for r in results:
            if not r['passed']:
                print(f"    ✗ {r['name']}: {r['error']}")

    print("=" * 60)
    print()

    return 0 if failed_count == 0 else 1


def run_single_file(filepath: str, verbose: bool = False) -> int:
    """运行单个测试文件

    Args:
        filepath: .light 文件路径
        verbose: 详细输出

    Returns:
        退出码
    """
    if not os.path.exists(filepath):
        print(f"文件未找到: {filepath}")
        return 1

    if not filepath.endswith('.light'):
        print(f"不是 .light 文件: {filepath}")
        return 1

    # 添加 src 到路径
    project_dir = os.path.dirname(os.path.abspath(filepath))
    while project_dir and not os.path.exists(os.path.join(project_dir, 'src')):
        parent = os.path.dirname(project_dir)
        if parent == project_dir:
            break
        project_dir = parent

    src_dir = os.path.join(project_dir, 'src')
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    print("=" * 60)
    print(f"  光明测试 - {os.path.basename(filepath)}")
    print("=" * 60)
    print()

    result = run_test_file(filepath, verbose)
    if result['passed']:
        print(f"  [OK] 测试通过 ({result['time']:.1f}ms)")
        if result['output']:
            print(f"  输出: {result['output']}")
    else:
        print(f"  [FAIL] 测试失败 ({result['time']:.1f}ms)")
        print(f"  错误: {result['error']}")

    print()
    return 0 if result['passed'] else 1