"""
build_bootstrap_release.py - 自举编译器发布构建

构建自举编译器二进制发布包：
  1. 合并所有 bootstrap 模块 -> bootstrap_v3.duan
  2. 用 SRC 后端编译为 Python 代码
  3. 尝试用 PyInstaller 打包为独立可执行文件
  4. 验证构建产物

Usage:
    python build_bootstrap_release.py              # 完整构建
    python build_bootstrap_release.py --skip-pyinstaller  # 跳过 EXE 打包
    python build_bootstrap_release.py --clean      # 清理构建产物
"""

import sys
import os
import shutil
import subprocess
import argparse

# =============================================================================
# 路径配置
# =============================================================================

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.normpath(os.path.join(_script_dir, '..'))
_src_dir = os.path.join(_project_dir, 'src')

sys.path.insert(0, _src_dir)
sys.path.insert(0, _project_dir)

# 构建输出目录
BUILD_DIR = os.path.join(_script_dir, 'build')
DIST_DIR = os.path.join(_script_dir, 'dist')
RELEASE_DIR = os.path.join(_script_dir, 'release')


# =============================================================================
# 构建步骤
# =============================================================================

def step_clean():
    """清理之前的构建产物"""
    print("=" * 60)
    print("Step 0: 清理构建产物")
    print("=" * 60)
    for d in [BUILD_DIR, DIST_DIR, RELEASE_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  删除: {d}")
    print()


def step_merge_modules():
    """合并所有 bootstrap 模块为 bootstrap_v3.duan"""
    print("=" * 60)
    print("Step 1: 合并 bootstrap 模块 -> bootstrap_v3.duan")
    print("=" * 60)

    from merge_bootstrap import modules, bootstrap_dir

    output_path = os.path.join(bootstrap_dir, 'bootstrap_v3.duan')
    if os.path.exists(output_path):
        os.remove(output_path)

    # 重新运行 merge_bootstrap 的主逻辑
    output_lines = [
        "# bootstrap_v3.duan - v3.2 自举编译器（合并版）",
        "# 由 merge_bootstrap.py / build_bootstrap_release.py 自动生成",
        "",
    ]

    for module in modules:
        path = os.path.join(bootstrap_dir, module)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        filtered = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('导入 ') or stripped.startswith('从 '):
                continue
            if stripped.startswith('导出 '):
                continue
            filtered.append(line)
        output_lines.append(f"\n# ===== {module} =====\n")
        output_lines.append('\n'.join(filtered))

    output = '\n'.join(output_lines)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"  已生成: {output_path} ({len(output)} 字符)")
    print()
    return output_path


def step_compile_bootstrap(bootstrap_path):
    """用 SRC 后端编译 bootstrap_v3.duan 为 Python 代码"""
    print("=" * 60)
    print("Step 2: 编译自举编译器 (Duan -> Python)")
    print("=" * 60)

    from run_compiler import compile_bootstrap_dir

    # 编译到 Python
    os.makedirs(BUILD_DIR, exist_ok=True)
    output_py = os.path.join(BUILD_DIR, 'bootstrap_compiler.py')

    py_code = compile_bootstrap_dir(bootstrap_path, output_py)
    if py_code is None or len(py_code) == 0:
        print("  ERROR: 编译失败")
        sys.exit(1)

    # 验证 Python 语法
    try:
        compile(py_code, output_py, 'exec')
        print(f"  Python 语法验证: 通过")
    except SyntaxError as e:
        print(f"  Python 语法验证: 失败 - {e}")
        sys.exit(1)

    print(f"  生成 {len(py_code)} 字符的 Python 代码")
    print()
    return py_code, output_py


def step_verify_bootstrap(py_code):
    """验证自举编译器能正确编译测试程序"""
    print("=" * 60)
    print("Step 3: 验证自举编译器")
    print("=" * 60)

    from run_compiler import execute_generated_code

    # 执行生成的代码
    print("  执行自举编译器...")
    namespace = execute_generated_code(py_code)

    # 检查关键导出
    required = ['词法分析', 'parse', 'generate', 'compile_source', 'compile_file']
    for name in required:
        assert name in namespace, f"缺少导出函数: {name}"
    print("  关键导出函数: 全部存在")

    # 编译并执行一个简单测试
    test_code = """
段落 测试 接收 x：
  返回 x 乘 2 加 1

设 结果 为 测试(5)
打印(结果)
"""
    print("  编译测试程序...")
    result_py = namespace['compile_source'](test_code)

    # 验证语法
    compile(result_py, '<test>', 'exec')
    print("  测试程序语法: 通过")

    # 执行
    test_ns = {'_duan_builtin': type(sys)('_duan_builtin')}
    test_ns['_duan_builtin'].打印 = print
    test_ns['_duan_builtin'].转字符串 = str
    test_ns['_duan_builtin'].转整数 = int
    exec(result_py, test_ns)
    print("  测试程序执行: 成功")

    print("  验证: 通过")
    print()


def step_create_wrapper(py_code, output_py):
    """创建命令行包装脚本"""
    print("=" * 60)
    print("Step 4: 创建命令行包装脚本")
    print("=" * 60)

    os.makedirs(DIST_DIR, exist_ok=True)

    # 创建 duan-compiler.py 包装脚本
    wrapper_path = os.path.join(DIST_DIR, 'duan-compiler.py')
    # 将编译器代码编码为 base64 以避免 repr 转义问题
    import base64
    py_code_bytes = py_code.encode('utf-8')
    encoded = base64.b64encode(py_code_bytes).decode('ascii')
    with open(wrapper_path, 'w', encoding='utf-8') as f:
        f.write(f'''#!/usr/bin/env python3
"""
Duan Bootstrap Compiler - 段言自举编译器
版本: 3.2.0

用法:
    python duan-compiler.py <source.duan> [output.py]

编译 .duan 文件为 Python 代码。
"""

import sys
import os
import base64
import types

# 内嵌的自举编译器代码（base64 编码）
# 由 build_bootstrap_release.py 自动生成

COMPILER_B64 = {repr(encoded)}

# 模块级执行编译器代码
_compiler_ns = {{}}
_compiler_code = base64.b64decode(COMPILER_B64).decode('utf-8')
exec(_compiler_code, _compiler_ns)

def compile_source(source):
    return _compiler_ns['compile_source'](source)

def compile_file(filepath):
    return _compiler_ns['compile_file'](filepath)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    source_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(source_path):
        print(f"Error: file not found: {{source_path}}")
        sys.exit(1)

    py_code = compile_file(source_path)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(py_code)
        print(f"Written to: {{output_path}}")
    else:
        print(py_code)

if __name__ == '__main__':
    main()
''')
    print(f"  已生成: {wrapper_path}")

    # 验证包装脚本语法
    try:
        compile(open(wrapper_path, encoding='utf-8').read(), wrapper_path, 'exec')
        print(f"  包装脚本语法: 通过")
    except SyntaxError as e:
        print(f"  包装脚本语法: 失败 - {e}")

    print()


def step_try_pyinstaller(wrapper_path):
    """尝试用 PyInstaller 打包为独立 EXE"""
    print("=" * 60)
    print("Step 5: 尝试 PyInstaller 打包")
    print("=" * 60)

    try:
        import PyInstaller
        print("  PyInstaller 已安装，开始打包...")
    except ImportError:
        print("  PyInstaller 未安装，跳过 EXE 打包")
        print("  提示: pip install pyinstaller 后可重新运行")
        print()
        return None

    exe_dir = os.path.join(DIST_DIR, 'duan-compiler')
    os.makedirs(exe_dir, exist_ok=True)

    try:
        subprocess.run(
            [sys.executable, '-m', 'PyInstaller',
             '--onefile',
             '--name', 'duan-compiler',
             '--distpath', exe_dir,
             '--specpath', BUILD_DIR,
             '--workpath', os.path.join(BUILD_DIR, 'pyinstaller'),
             wrapper_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        exe_path = os.path.join(exe_dir, 'duan-compiler.exe')
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path)
            print(f"  EXE 已生成: {exe_path} ({file_size / 1024:.1f} KB)")
            print()
            return exe_path
        else:
            print("  EXE 生成失败（未找到输出文件）")
            print()
            return None

    except subprocess.TimeoutExpired:
        print("  PyInstaller 超时，跳过")
        print()
        return None
    except subprocess.CalledProcessError as e:
        print(f"  PyInstaller 打包失败: {e}")
        print(f"  stderr: {e.stderr[:500]}")
        print()
        return None


def step_package_release(exe_path, output_py):
    """打包发布文件"""
    print("=" * 60)
    print("Step 6: 打包发布文件")
    print("=" * 60)

    os.makedirs(RELEASE_DIR, exist_ok=True)

    # 复制核心文件
    shutil.copy2(output_py, os.path.join(RELEASE_DIR, 'bootstrap_compiler.py'))
    print(f"  复制: bootstrap_compiler.py -> {RELEASE_DIR}")

    # 复制包装脚本
    wrapper_src = os.path.join(DIST_DIR, 'duan-compiler.py')
    if os.path.exists(wrapper_src):
        shutil.copy2(wrapper_src, os.path.join(RELEASE_DIR, 'duan-compiler.py'))
        print(f"  复制: duan-compiler.py -> {RELEASE_DIR}")

    # 复制 EXE（如果存在）
    if exe_path and os.path.exists(exe_path):
        shutil.copy2(exe_path, os.path.join(RELEASE_DIR, 'duan-compiler.exe'))
        print(f"  复制: duan-compiler.exe -> {RELEASE_DIR}")

    # 复制 bootstrap_v3.duan
    bootstrap_src = os.path.join(_script_dir, 'bootstrap_v3.duan')
    if os.path.exists(bootstrap_src):
        shutil.copy2(bootstrap_src, os.path.join(RELEASE_DIR, 'bootstrap_v3.duan'))
        print(f"  复制: bootstrap_v3.duan -> {RELEASE_DIR}")

    # 复制 stdlib 目录
    stdlib_src = os.path.join(_project_dir, 'stdlib')
    stdlib_dst = os.path.join(RELEASE_DIR, 'stdlib')
    if os.path.isdir(stdlib_src):
        if os.path.exists(stdlib_dst):
            shutil.rmtree(stdlib_dst)
        shutil.copytree(stdlib_src, stdlib_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print(f"  复制: stdlib/ -> {stdlib_dst}")

    # 创建 README.txt
    readme_path = os.path.join(RELEASE_DIR, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("""Duan Bootstrap Compiler v3.2.0 - 段言自举编译器
=============================================

文件说明:
  bootstrap_compiler.py  - 自举编译器 Python 源码
  duan-compiler.py       - 命令行包装脚本
  duan-compiler.exe      - 独立可执行文件（如有）
  bootstrap_v3.duan      - 自举编译器段言源码
  stdlib/                - 段言标准库（运行时必需）

依赖:
  - Python 3.8+
  - stdlib/ 目录必须与脚本在同一目录

用法:
  python duan-compiler.py <source.duan> [output.py]
  或
  duan-compiler.exe <source.duan> [output.py]

示例:
  python duan-compiler.py hello.duan hello.py

构建日期: %s
""" % __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    print(f"  README: {readme_path}")
    print()


def step_verify_release():
    """验证发布包"""
    print("=" * 60)
    print("Step 7: 验证发布包")
    print("=" * 60)

    # 检查关键文件
    required_files = [
        'bootstrap_compiler.py',
        'duan-compiler.py',
        'bootstrap_v3.duan',
        'README.txt',
    ]

    all_ok = True
    for filename in required_files:
        path = os.path.join(RELEASE_DIR, filename)
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        status = "OK" if exists else "MISSING"
        print(f"  {status}: {filename} ({size} bytes)")
        if not exists:
            all_ok = False

    # 验证 duan-compiler.py 能正常工作
    wrapper_path = os.path.join(RELEASE_DIR, 'duan-compiler.py')
    if os.path.exists(wrapper_path):
        try:
            # 创建一个临时测试文件
            test_file = os.path.join(RELEASE_DIR, '_test_temp.duan')
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('段落 测试 接收 x：\n  返回 x 乘 2\n\n打印(测试(21))\n')

            result = subprocess.run(
                [sys.executable, wrapper_path, test_file],
                capture_output=True, text=True, timeout=30
            )
            os.remove(test_file)

            if result.returncode == 0:
                # 验证输出能正确执行
                try:
                    exec(result.stdout, {'_duan_builtin': type(sys)('_duan_builtin')})
                    print(f"  发布包验证: 通过")
                except Exception as e:
                    print(f"  发布包验证: 输出执行失败 - {e}")
                    all_ok = False
            else:
                print(f"  发布包验证: 执行失败 - {result.stderr[:200]}")
                all_ok = False
        except Exception as e:
            print(f"  发布包验证: 异常 - {e}")
            all_ok = False

    print()
    return all_ok


# =============================================================================
# 主流程
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='构建自举编译器发布包')
    parser.add_argument('--skip-pyinstaller', action='store_true',
                        help='跳过 PyInstaller EXE 打包')
    parser.add_argument('--clean', action='store_true',
                        help='清理构建产物')
    parser.add_argument('--skip-verify', action='store_true',
                        help='跳过验证步骤')
    args = parser.parse_args()

    if args.clean:
        step_clean()
        print("清理完成。")
        return

    print("=" * 60)
    print("  段言自举编译器发布构建")
    print(f"  项目目录: {_project_dir}")
    print("=" * 60)
    print()

    # Step 1: 合并模块
    bootstrap_path = step_merge_modules()

    # Step 2: 编译为 Python
    py_code, output_py = step_compile_bootstrap(bootstrap_path)

    # Step 3: 验证
    if not args.skip_verify:
        step_verify_bootstrap(py_code)

    # Step 4: 创建包装脚本
    wrapper_path = step_create_wrapper(py_code, output_py)

    # Step 5: 尝试 PyInstaller
    exe_path = None
    if not args.skip_pyinstaller:
        exe_path = step_try_pyinstaller(wrapper_path)

    # Step 6: 打包发布
    step_package_release(exe_path, output_py)

    # Step 7: 验证发布包
    if not args.skip_verify:
        all_ok = step_verify_release()
    else:
        all_ok = True

    # 总结
    print("=" * 60)
    print("构建总结")
    print("=" * 60)
    print(f"  发布目录: {RELEASE_DIR}")
    if os.path.exists(RELEASE_DIR):
        for f in sorted(os.listdir(RELEASE_DIR)):
            fpath = os.path.join(RELEASE_DIR, f)
            size = os.path.getsize(fpath)
            print(f"    {f:30s} {size:>8d} bytes")
    print()
    if all_ok:
        print("自举编译器发布构建成功！")
    else:
        print("自举编译器发布构建完成（部分步骤失败）")
        sys.exit(1)


if __name__ == '__main__':
    main()