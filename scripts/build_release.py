#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）一键构建发布包脚本

功能：
  1. 清理旧的构建产物
  2. 构建源码包（sdist）和 wheel 包
  3. 构建跨平台可执行文件（需在本机运行）
  4. 验证包元数据

用法：
  python scripts/build_release.py              # 构建源码包 + wheel
  python scripts/build_release.py --exe        # 构建源码包 + wheel + 可执行文件
  python scripts/build_release.py --exe-only   # 仅构建可执行文件
  python scripts/build_release.py --clean      # 仅清理构建产物
"""

import os
import sys
import shutil
import subprocess
import argparse

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def print_step(title):
    """打印带格式的步骤标题"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def clean():
    """清理旧的构建产物"""
    print_step("清理构建产物")

    dirs_to_clean = [
        os.path.join(PROJECT_DIR, 'dist'),
        os.path.join(PROJECT_DIR, 'build'),
        os.path.join(PROJECT_DIR, '*.spec'),
    ]

    for pattern in dirs_to_clean:
        # 处理 glob 模式
        if '*' in pattern:
            import glob
            for path in glob.glob(pattern):
                if os.path.isfile(path):
                    os.remove(path)
                    print(f"  删除文件: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"  删除目录: {path}")
        else:
            if os.path.exists(pattern):
                shutil.rmtree(pattern)
                print(f"  删除目录: {pattern}")

    # 清理 __pycache__ 目录
    pycache_dirs = []
    for root, dirs, _ in os.walk(PROJECT_DIR):
        for d in dirs:
            if d == '__pycache__':
                pycache_dirs.append(os.path.join(root, d))

    for d in pycache_dirs:
        shutil.rmtree(d, ignore_errors=True)

    print("  清理完成")


def build_package():
    """构建源码包和 wheel 包"""
    print_step("构建源码包 (sdist) 和 wheel 包")

    # 检查 build 模块
    try:
        import build
    except ImportError:
        print("正在安装 build 模块...")
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'build'],
            cwd=PROJECT_DIR, check=True
        )

    result = subprocess.run(
        [sys.executable, '-m', 'build'],
        cwd=PROJECT_DIR,
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print("❌ 构建失败!", file=sys.stderr)
        sys.exit(1)

    # 验证构建产物
    dist_dir = os.path.join(PROJECT_DIR, 'dist')
    if os.path.exists(dist_dir):
        artifacts = [f for f in os.listdir(dist_dir)
                     if f.endswith('.tar.gz') or f.endswith('.whl')]
        print(f"\n构建产物 ({len(artifacts)} 个):")
        for f in sorted(artifacts):
            filepath = os.path.join(dist_dir, f)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"  - {f} ({size_kb:.1f} KB)")

    print("✅ 源码包构建成功")


def verify_package():
    """验证包元数据（使用 twine）"""
    print_step("验证包元数据")

    dist_dir = os.path.join(PROJECT_DIR, 'dist')
    if not os.path.exists(dist_dir):
        print("  未找到 dist 目录，跳过验证", file=sys.stderr)
        return

    try:
        import twine
    except ImportError:
        print("正在安装 twine...")
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'twine'],
            cwd=PROJECT_DIR, check=True
        )

    result = subprocess.run(
        [sys.executable, '-m', 'twine', 'check', 'dist/*'],
        cwd=PROJECT_DIR,
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print("⚠️  包元数据验证有警告", file=sys.stderr)
    else:
        print("✅ 包元数据验证通过")


def build_executable():
    """构建可执行文件"""
    print_step("构建可执行文件")

    build_exe_path = os.path.join(PROJECT_DIR, 'build_exe.py')
    if not os.path.exists(build_exe_path):
        print("  ❌ build_exe.py 不存在，跳过可执行文件构建", file=sys.stderr)
        return

    result = subprocess.run(
        [sys.executable, build_exe_path, '--name', 'light6'],
        cwd=PROJECT_DIR,
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print("❌ 可执行文件构建失败!", file=sys.stderr)
        sys.exit(1)

    # 显示构建产物
    dist_dir = os.path.join(PROJECT_DIR, 'dist')
    if os.path.exists(dist_dir):
        exe_files = [f for f in os.listdir(dist_dir)
                     if os.path.isfile(os.path.join(dist_dir, f))]
        print(f"\n可执行文件:")
        for f in sorted(exe_files):
            filepath = os.path.join(dist_dir, f)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  - {f} ({size_mb:.2f} MB)")

    print("✅ 可执行文件构建成功")


def main():
    parser = argparse.ArgumentParser(
        description='光明（Light）一键构建发布包',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/build_release.py               # 构建源码包 + wheel
  python scripts/build_release.py --exe         # 构建源码包 + wheel + 可执行文件
  python scripts/build_release.py --exe-only    # 仅构建可执行文件
  python scripts/build_release.py --clean       # 仅清理构建产物
        """
    )
    parser.add_argument('--exe', action='store_true', help='同时构建可执行文件')
    parser.add_argument('--exe-only', action='store_true', help='仅构建可执行文件')
    parser.add_argument('--clean', action='store_true', help='仅清理构建产物')
    parser.add_argument('--no-verify', action='store_true', help='跳过包元数据验证')

    args = parser.parse_args()

    print("=" * 60)
    print("  光明（Light）发布包构建工具")
    print("=" * 60)
    print(f"  项目目录: {PROJECT_DIR}")
    print(f"  Python: {sys.version.split()[0]}")
    print("=" * 60)

    if args.clean:
        clean()
        return

    if args.exe_only:
        clean()
        build_executable()
        return

    # 默认：构建源码包
    clean()
    build_package()
    if not args.no_verify:
        verify_package()

    if args.exe:
        build_executable()

    print()
    print("=" * 60)
    print("  ✅ 发布包构建完成！")
    print("=" * 60)
    print()
    print("  下一步：")
    print("    python scripts/publish_pypi.py    # 发布到 PyPI")
    print()


if __name__ == '__main__':
    main()