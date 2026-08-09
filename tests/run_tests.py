# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 统一测试运行器

运行方式：
  python tests/run_tests.py              # 运行全部测试
  python tests/run_tests.py --quick      # 仅运行快速验证
  python tests/run_tests.py --unit      # 仅运行单元测试
  python tests/run_tests.py --integration # 仅运行集成测试
  python tests/run_tests.py --e2e       # 仅运行端到端测试
  python tests/run_tests.py --list      # 列出所有测试文件
  python tests/run_tests.py --all       # 运行所有测试（含 archive）
"""

import sys
import io
import os
import subprocess
import glob
import unittest

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def print_header(title):
    """打印带格式的标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def print_summary(results):
    """打印测试总结"""
    total = sum(r['total'] for r in results)
    passed = sum(r['passed'] for r in results)
    failed = sum(r['failed'] for r in results)
    errors = sum(r['errors'] for r in results)

    print()
    print("=" * 70)
    print("  测试总结")
    print("=" * 70)
    for r in results:
        status = "OK" if r['failed'] == 0 and r['errors'] == 0 else "FAIL"
        print(f"  [{status}] {r['name']}: {r['passed']}/{r['total']} 通过")

    total_failures = failed + errors
    print()
    if total_failures == 0:
        print(f"  [OK] 全部 {total} 个测试通过！")
    else:
        print(f"  [FAIL] {passed}/{total} 通过, {total_failures} 失败")
    print("=" * 70)
    print()

    return total_failures


def run_pytest(test_paths):
    """运行 pytest 测试

    Args:
        test_paths: 测试目录或文件列表
    """
    if not test_paths:
        return {'name': 'pytest', 'total': 0, 'passed': 0, 'failed': 0, 'errors': 0}

    cmd = [sys.executable, '-m', 'pytest'] + test_paths + ['-v', '--tb=short']

    result = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )

    # 解析输出获取统计
    lines = result.stdout.split('\n')
    total = passed = failed = errors = 0

    for line in lines:
        if 'PASSED' in line:
            passed += 1
            total += 1
        elif 'FAILED' in line:
            failed += 1
            total += 1
        elif 'ERROR' in line:
            errors += 1
            total += 1

    print(result.stdout)
    if result.stderr and 'PASSED' not in result.stdout:
        print(result.stderr[:500])

    return {'name': 'pytest', 'total': total, 'passed': passed, 'failed': failed, 'errors': errors}


def run_unit_tests():
    """运行单元测试"""
    print_header("单元测试 (tests/unit/)")
    test_dir = os.path.join(PROJECT_DIR, 'tests', 'unit')
    return run_pytest([test_dir])


def run_integration_tests():
    """运行集成测试"""
    print_header("集成测试 (tests/integration/)")
    test_dir = os.path.join(PROJECT_DIR, 'tests', 'integration')
    return run_pytest([test_dir])


def run_e2e_tests():
    """运行端到端测试"""
    print_header("端到端测试 (tests/e2e/)")
    test_dir = os.path.join(PROJECT_DIR, 'tests', 'e2e')
    return run_pytest([test_dir])


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("  光明（Light）编程语言 - 完整测试套件")
    print("=" * 70)
    print(f"  项目目录: {PROJECT_DIR}")
    print(f"  Python: {sys.version.split()[0]}")

    results = []

    # 1. 单元测试
    results.append(run_unit_tests())

    # 2. 集成测试
    results.append(run_integration_tests())

    # 3. 端到端测试
    results.append(run_e2e_tests())

    # 总结
    return print_summary(results)


def run_quick_tests():
    """运行快速测试（不依赖 pytest）"""
    print_header("快速验证测试")

    sys.path.insert(0, os.path.join(PROJECT_DIR, 'src'))

    tests_passed = 0
    tests_failed = 0

    test_cases = [
        ("ANTLR 后端存在", lambda: _check_antlr_exists()),
        ("SRC 后端存在", lambda: _check_src_exists()),
        ("Bootstrap 编译器存在", lambda: _check_bootstrap_exists()),
        ("CLI 工具存在", lambda: _check_cli_exists()),
    ]

    for name, test_fn in test_cases:
        print(f"  [{name}] ", end="")
        try:
            msg = test_fn()
            print(f"OK  {msg}")
            tests_passed += 1
        except AssertionError as e:
            print(f"FAIL  {e}")
            tests_failed += 1
        except Exception as e:
            print(f"ERROR  {e}")
            tests_failed += 1

    print(f"\n  快速验证: {tests_passed} 通过, {tests_failed} 失败")
    return {'name': '快速验证', 'total': len(test_cases), 'passed': tests_passed, 'failed': tests_failed, 'errors': 0}


def _check_antlr_exists():
    antlr_dir = os.path.join(PROJECT_DIR, 'antlrparser')
    assert os.path.exists(antlr_dir), "ANTLR 后端不存在"
    assert os.path.exists(os.path.join(antlr_dir, 'llvm_codegen.py')), "llvm_codegen.py 不存在"
    return "存在"


def _check_src_exists():
    src_dir = os.path.join(PROJECT_DIR, 'src')
    assert os.path.exists(src_dir), "SRC 后端不存在"
    assert os.path.exists(os.path.join(src_dir, 'compiler.py')), "compiler.py 不存在"
    return "存在"


def _check_bootstrap_exists():
    bootstrap_py = os.path.join(PROJECT_DIR, 'bootstrap', 'bootstrap_v3_compiled.py')
    assert os.path.exists(bootstrap_py), "Bootstrap 编译器不存在"
    return "存在"


def _check_cli_exists():
    cli_unified = os.path.join(PROJECT_DIR, 'cli', 'light_unified.py')
    assert os.path.exists(cli_unified), "CLI 统一工具不存在"
    return "存在"


def list_test_files():
    """列出所有测试文件"""
    print_header("测试文件列表")

    categories = {
        '单元测试': os.path.join(PROJECT_DIR, 'tests', 'unit'),
        '集成测试': os.path.join(PROJECT_DIR, 'tests', 'integration'),
        '端到端测试': os.path.join(PROJECT_DIR, 'tests', 'e2e'),
    }

    for category, test_dir in categories.items():
        print(f"\n  [{category}]")
        if os.path.exists(test_dir):
            for tf in glob.glob(os.path.join(test_dir, 'test_*.py')):
                name = os.path.basename(tf)
                print(f"    - {name}")

    print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='光明（Light）编程语言 - 统一测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tests/run_tests.py              # 运行全部测试
  python tests/run_tests.py --quick       # 仅快速验证
  python tests/run_tests.py --unit        # 仅单元测试
  python tests/run_tests.py --integration # 仅集成测试
  python tests/run_tests.py --e2e         # 仅端到端测试
  python tests/run_tests.py --list        # 列出测试文件
        """
    )
    parser.add_argument('--quick', action='store_true', help='仅运行快速验证测试')
    parser.add_argument('--unit', action='store_true', help='仅运行单元测试')
    parser.add_argument('--integration', action='store_true', help='仅运行集成测试')
    parser.add_argument('--e2e', action='store_true', help='仅运行端到端测试')
    parser.add_argument('--list', action='store_true', help='列出所有测试文件')

    args = parser.parse_args()

    if args.list:
        list_test_files()
        sys.exit(0)
    elif args.quick:
        result = run_quick_tests()
        sys.exit(0 if result['failed'] == 0 else 1)
    elif args.unit:
        result = run_unit_tests()
        sys.exit(0 if result['failed'] == 0 and result['errors'] == 0 else 1)
    elif args.integration:
        result = run_integration_tests()
        sys.exit(0 if result['failed'] == 0 and result['errors'] == 0 else 1)
    elif args.e2e:
        result = run_e2e_tests()
        sys.exit(0 if result['failed'] == 0 and result['errors'] == 0 else 1)
    else:
        exit_code = run_all_tests()
        sys.exit(exit_code)
