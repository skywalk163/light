#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）发布到 PyPI 辅助脚本

功能：
  1. 检查构建产物是否存在
  2. 验证包元数据
  3. 发布到 PyPI（正式仓库或测试仓库）
  4. 支持从环境变量读取 API token

用法：
  python scripts/publish_pypi.py                    # 发布到正式 PyPI
  python scripts/publish_pypi.py --test             # 发布到 TestPyPI
  python scripts/publish_pypi.py --repository mypypi  # 发布到自定义仓库
  python scripts/publish_pypi.py --check-only       # 仅检查，不发布

环境变量：
  PYPI_API_TOKEN         PyPI API token（推荐使用）
  TEST_PYPI_API_TOKEN    TestPyPI API token
  TWINE_USERNAME         PyPI 用户名（如无 token 时使用）
  TWINE_PASSWORD         PyPI 密码（如无 token 时使用）
"""

import os
import sys
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


def check_dist():
    """检查构建产物是否存在"""
    dist_dir = os.path.join(PROJECT_DIR, 'dist')
    if not os.path.exists(dist_dir):
        print("  ❌ dist 目录不存在！请先运行 build_release.py 构建发布包。", file=sys.stderr)
        print("     python scripts/build_release.py")
        sys.exit(1)

    artifacts = [f for f in os.listdir(dist_dir)
                 if f.endswith('.tar.gz') or f.endswith('.whl')]
    if not artifacts:
        print("  ❌ dist 目录中没有构建产物！请先运行 build_release.py。", file=sys.stderr)
        sys.exit(1)

    print(f"  找到 {len(artifacts)} 个构建产物:")
    for f in sorted(artifacts):
        size = os.path.getsize(os.path.join(dist_dir, f))
        print(f"    - {f} ({size / 1024:.1f} KB)")

    return dist_dir


def verify_package(dist_dir):
    """使用 twine 验证包"""
    print_step("验证包元数据")

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'twine', 'check', '--strict']
            + [os.path.join(dist_dir, f) for f in os.listdir(dist_dir)
               if f.endswith('.tar.gz') or f.endswith('.whl')],
            cwd=PROJECT_DIR,
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            print("  ❌ 包元数据验证失败！", file=sys.stderr)
            sys.exit(1)
        print("  ✅ 包元数据验证通过")
    except FileNotFoundError:
        print("  ⚠️  twine 未安装，跳过验证")
        print("  安装: pip install twine")


def publish(dist_dir, repository, check_only):
    """发布到 PyPI"""
    if check_only:
        print_step("检查模式 — 未发布")
        print("  ✅ 所有检查通过，可以发布。")
        return

    print_step(f"发布到 {repository}")

    # 构建 twine 命令
    cmd = [sys.executable, '-m', 'twine', 'upload']

    # 根据仓库设置参数
    if repository == 'testpypi':
        cmd.extend(['--repository-url', 'https://test.pypi.org/legacy/'])
        token = os.environ.get('TEST_PYPI_API_TOKEN')
        if token:
            cmd.extend(['--password', token])
            cmd.extend(['--username', '__token__'])
    elif repository == 'pypi':
        token = os.environ.get('PYPI_API_TOKEN')
        if token:
            cmd.extend(['--password', token])
            cmd.extend(['--username', '__token__'])

    # 添加包文件
    for f in os.listdir(dist_dir):
        if f.endswith('.tar.gz') or f.endswith('.whl'):
            cmd.append(os.path.join(dist_dir, f))

    # 打印发布信息（不暴露 token）
    print(f"  仓库: {repository}")
    print(f"  文件: {len(cmd) - 5} 个")
    auth_method = "API token" if any('token' in part for part in cmd) else "用户名/密码"
    print(f"  认证方式: {auth_method}")
    print()

    # 确认发布
    if not check_only:
        print("  即将发布到 PyPI...")
        try:
            # 不显示实际命令（避免 token 泄露）
            result = subprocess.run(
                cmd, cwd=PROJECT_DIR,
                capture_output=True, text=True
            )
            print(result.stdout)
            if result.returncode != 0:
                print(result.stderr)
                print("  ❌ 发布失败！", file=sys.stderr)
                sys.exit(1)
            print("  ✅ 发布成功！")
            print(f"  查看: https://pypi.org/project/light/")
        except FileNotFoundError:
            print("  ❌ twine 未安装，请先安装: pip install twine", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='光明（Light）发布到 PyPI 辅助脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
环境变量:
  PYPI_API_TOKEN          PyPI API token（推荐）
  TEST_PYPI_API_TOKEN     TestPyPI API token

示例:
  python scripts/publish_pypi.py                    # 发布到正式 PyPI
  python scripts/publish_pypi.py --test             # 发布到 TestPyPI
  python scripts/publish_pypi.py --check-only       # 仅检查不发布
        """
    )
    parser.add_argument('--test', action='store_true', help='发布到 TestPyPI')
    parser.add_argument('--repository', type=str, default=None,
                        help='自定义仓库 URL')
    parser.add_argument('--check-only', action='store_true',
                        help='仅检查包，不发布')

    args = parser.parse_args()

    print("=" * 60)
    print("  光明（Light）PyPI 发布工具")
    print("=" * 60)
    print(f"  项目目录: {PROJECT_DIR}")
    print(f"  Python: {sys.version.split()[0]}")
    print("=" * 60)

    # 确定目标仓库
    if args.repository:
        repository = args.repository
    elif args.test:
        repository = 'testpypi'
    else:
        repository = 'pypi'

    # 检查构建产物
    dist_dir = check_dist()

    # 验证包
    verify_package(dist_dir)

    # 发布
    publish(dist_dir, repository, args.check_only)

    print()
    print("=" * 60)
    if args.check_only:
        print("  ✅ 检查完成，准备就绪。")
    else:
        print("  ✅ 发布流程完成！")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()