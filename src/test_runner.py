# -*- coding: utf-8 -*-
"""
光明（Light）测试运行器

支持：
  - 自动发现 tests/ 目录下的 .light 测试文件
  - 运行单个或多个测试文件
  - 计时统计
  - 过滤测试
  - 详细输出
  - 彩色输出
  - 进度条

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
import re
import glob
import traceback

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ── ANSI 颜色 ──────────────────────────────────────────────────────
_USE_COLOR = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    """应用 ANSI 颜色（仅在终端中生效）"""
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def _green(text: str) -> str:
    return _c('32', text)

def _red(text: str) -> str:
    return _c('31', text)

def _yellow(text: str) -> str:
    return _c('33', text)

def _cyan(text: str) -> str:
    return _c('36', text)

def _bold(text: str) -> str:
    return _c('1', text)

def _dim(text: str) -> str:
    return _c('2', text)

# ── 进度条 ─────────────────────────────────────────────────────────

def _render_progress(current: int, total: int, bar_width: int = 30) -> str:
    """渲染进度条"""
    if total == 0:
        return ''
    fraction = current / total
    filled = int(bar_width * fraction)
    bar = '█' * filled + '░' * (bar_width - filled)
    pct = int(fraction * 100)
    return f"[{bar}] {pct}% ({current}/{total})"


# 已知的标准库模块名（不应被内联）
KNOWN_STDLIB_MODULES = {
    '文件系统', 'JSON', '字符串工具', '数学', '时间', '日期时间',
    '复制', 'os路径', 'csv', 'json', 'os', 're', 'random', 'math',
    'datetime', 'time', 'pathlib', 'typing', 'collections', 'itertools',
    'functools', 'subprocess', 'shutil', 'glob', 'tempfile', 'io', 'builtins',
}


def _register_test_modules(source: str, search_dirs: list, registered: set = None,
                           exported_names: set = None) -> None:
    """预编译用户模块并注册到 sys.modules，使测试文件中的导入语句能正常解析

    测试文件中的导入语句（如 导入《工具》为 工具）在生成 Python 代码时
    会变成 import 工具 as 工具，Python 无法解析中文模块名。
    此方法在运行前预编译用户模块的 .light 文件，创建 Python 模块对象
    并注册到 sys.modules 中，使 import 语句能正常解析。

    Args:
        source: 源代码
        search_dirs: 搜索模块文件的目录列表
        registered: 已注册的模块名集合
        exported_names: 收集到的所有模块导出函数名集合（用于跨模块标识符识别）
    """
    import types
    from light_parser_v3 import LightParser, ImportStmt
    from code_generator import PythonCodeGenerator

    if registered is None:
        registered = set()
    _already_collected = set()

    parser = LightParser()
    module = parser.parse(source)
    if not module:
        return

    for stmt in getattr(module, 'statements', []):
        if not isinstance(stmt, ImportStmt):
            continue
        mod_name = stmt.module_name
        if mod_name in registered or mod_name in KNOWN_STDLIB_MODULES:
            continue
        if getattr(stmt, 'language', None) in ('python', 'c'):
            continue

        # 在搜索目录中查找模块文件
        mod_path = None
        for d in search_dirs:
            candidate = os.path.join(d, f"{mod_name}.light")
            if os.path.exists(candidate):
                mod_path = candidate
                break

        if not mod_path:
            continue

        # 读取模块源码
        with open(mod_path, 'r', encoding='utf-8') as f:
            mod_source = f.read()

        # 标记为已注册
        registered.add(mod_name)

        # 递归注册模块自身的导入
        _register_test_modules(mod_source, search_dirs, registered, exported_names)

        # 编译模块并注册为 Python 模块
        try:
            mod_parser = LightParser()
            mod_module = mod_parser.parse(mod_source, filename=mod_path)
            if mod_module:
                mod_generator = PythonCodeGenerator()
                mod_py_code = mod_generator.generate(mod_module)
                mod_ns = {'__builtins__': __builtins__}
                exec(mod_py_code, mod_ns)
                mod_obj = types.ModuleType(mod_name)
                for k, v in mod_ns.items():
                    if not k.startswith('_'):
                        setattr(mod_obj, k, v)
                sys.modules[mod_name] = mod_obj
                # 收集模块的导出函数名（用于跨模块标识符识别）
                if exported_names is not None and mod_name not in _already_collected:
                    _already_collected.add(mod_name)
                    for name in dir(mod_obj):
                        if not name.startswith('_') and callable(getattr(mod_obj, name, None)):
                            exported_names.add(name)
        except Exception:
            pass


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

        # 解析用户模块导入（预编译并注册用户模块）
        test_dir = os.path.dirname(os.path.abspath(filepath))
        search_dirs = [test_dir]
        # 向上查找项目根目录（包含 tests/ 目录的父目录）
        parent = os.path.dirname(test_dir)
        if os.path.basename(test_dir) == 'tests' and os.path.isdir(parent):
            search_dirs.append(parent)
        exported_names = set()
        _register_test_modules(source, search_dirs, exported_names=exported_names)

        # 编译
        parser = LightParser()
        module = parser.parse(source, filename=filepath, extra_definitions=exported_names)
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
            pkg_name = None
            # 优先读取 light.json（光明包配置），回退到 package.toml
            json_file = os.path.join(test_dir, 'light.json')
            if os.path.exists(json_file):
                import json as _json
                try:
                    with open(json_file, 'r', encoding='utf-8') as jf:
                        pkg_cfg = _json.load(jf)
                    pkg_name = pkg_cfg.get('名称') or pkg_cfg.get('name')
                except Exception:
                    pkg_name = None
            if not pkg_name:
                toml_file = os.path.join(test_dir, 'package.toml')
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
        print(_yellow("⚠ 未找到测试文件。"))
        print("测试文件应放在 tests/ 目录下，或以 test_*.light / *_test.light 命名。")
        return 0

    print()
    print(_bold("=" * 56))
    print(_bold(f"  光明测试运行器"))
    print(f"  📁 项目目录: {directory}")
    print(f"  📄 找到 {_cyan(str(len(test_files)))} 个测试文件")
    print(_bold("=" * 56))
    print()

    results = []
    passed_count = 0
    failed_count = 0
    total_time = 0

    for i, filepath in enumerate(test_files):
        name = os.path.basename(filepath)
        bar = _render_progress(i, len(test_files))
        print(f"  {bar}  {name}  ", end='', flush=True)

        result = run_test_file(filepath, verbose)
        results.append(result)
        total_time += result['time']

        elapsed_ms = result['time']
        if result['passed']:
            # 清除进度条，显示 OK 状态
            print(f"\r  {_render_progress(i + 1, len(test_files))}  {_dim(name)}  {_green('✓')}  {_dim(f'({elapsed_ms:.1f}ms)')}    ")
            passed_count += 1
        else:
            print(f"\r  {_render_progress(i + 1, len(test_files))}  {_dim(name)}  {_red('✗')}  {_dim(f'({elapsed_ms:.1f}ms)')}    ")
            # 显示错误信息
            error_msg = result['error'].split('\n')[0] if result['error'] else '未知错误'
            print(f"      {_red('错误:')} {error_msg}")
            failed_count += 1

    # 打印汇总
    print()
    print(_bold("=" * 56))
    print(_bold("  测试汇总"))
    print(_bold("=" * 56))

    total = passed_count + failed_count
    for r in results:
        r_time = r['time']
        r_name = r['name']
        if r['passed']:
            print(f"  {_green('✓')} {_dim(r_name):40} {_dim(f'({r_time:.1f}ms)')}")
        else:
            print(f"  {_red('✗')} {_bold(r_name):40} {_dim(f'({r_time:.1f}ms)')}")

    print()
    if failed_count == 0:
        print(f"  {_green('✓')} {_bold(f'全部 {total} 个测试通过！')} 总耗时 {_dim(f'{total_time:.1f}ms')}")
    else:
        print(f"  {_red('✗')} {_bold(f'{passed_count}/{total} 通过, {failed_count} 失败')}")
        for r in results:
            if not r['passed']:
                print(f"    {_red('·')} {_bold(r['name'])}: {_red(r['error'])}")

    print(_bold("=" * 56))
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

    print()
    print(_bold("=" * 56))
    print(_bold(f"  光明测试 - {os.path.basename(filepath)}"))
    print(_bold("=" * 56))
    print()

    result = run_test_file(filepath, verbose)
    if result['passed']:
        print(f"  {_green('✓')} {_bold('测试通过')} ({_dim(str(result['time']) + 'ms')})")
        if result['output']:
            print(f"  {_cyan('输出:')}")
            for line in result['output'].split('\n'):
                print(f"    {line}")
    else:
        print(f"  {_red('✗')} {_bold('测试失败')} ({_dim(str(result['time']) + 'ms')})")
        print(f"  {_red('错误:')} {result['error']}")

    print()
    return 0 if result['passed'] else 1