# -*- coding: utf-8 -*-
"""
段言全量回归测试运行器

功能：
  - 运行 tests/ 目录下的所有测试
  - 收集结果（通过、失败、跳过、错误）
  - 生成详细报告
  - 识别新出现的失败项
  - 导出结果到 JSON 报告文件
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path


def run_tests(test_dir: str = None) -> dict:
    """运行所有测试并收集结果"""
    if test_dir is None:
        test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests')

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("  段言（Duan）全量回归测试")
    print("=" * 70)
    print(f"  测试目录: {test_dir}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start_time = time.time()

    # 运行 pytest
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', test_dir, '-v', '--tb=short'],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    elapsed = time.time() - start_time

    # 解析输出
    stdout = result.stdout
    stderr = result.stderr

    # 提取总结行
    summary_line = ''
    for line in stdout.split('\n'):
        if 'passed' in line and 'failed' in line:
            summary_line = line.strip()
            break
        if '==' in line and ('passed' in line or 'failed' in line):
            summary_line = line.strip()

    # 提取失败列表
    failed_tests = []
    for line in stdout.split('\n'):
        if line.startswith('FAILED '):
            # Parse: FAILED path::test_name - error_message
            parts = line.replace('FAILED ', '', 1).split(' - ', 1)
            if len(parts) >= 1:
                test_info = {'test': parts[0]}
                if len(parts) > 1:
                    test_info['error'] = parts[1]
                failed_tests.append(test_info)

    # 提取通过的测试
    passed_tests = []
    for line in stdout.split('\n'):
        if ' PASSED' in line or 'PASSED' in line:
            # Extract test name
            parts = line.split()
            for p in parts:
                if '::' in p or p.endswith('.py'):
                    passed_tests.append(p)
                    break

    # 统计
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    errors = 0

    # 从 pytest 输出中解析
    for line in stdout.split('\n'):
        line = line.strip()
        if 'passed' in line and 'failed' in line:
            # e.g. "= 2482 passed, 11 failed, 48 skipped, 1350 warnings in 97.49s ="
            import re
            m = re.search(r'(\d+)\s+passed', line)
            if m:
                passed = int(m.group(1))
            m = re.search(r'(\d+)\s+failed', line)
            if m:
                failed = int(m.group(1))
            m = re.search(r'(\d+)\s+skipped', line)
            if m:
                skipped = int(m.group(1))
            m = re.search(r'(\d+)\s+errors', line)
            if m:
                errors = int(m.group(1))
            total = passed + failed + skipped + errors

    report = {
        'timestamp': datetime.now().isoformat(),
        'duration_seconds': round(elapsed, 2),
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'errors': errors,
            'pass_rate': round(passed / max(total, 1) * 100, 1),
        },
        'failed_tests': failed_tests,
        'exit_code': result.returncode,
    }

    # 打印摘要
    print()
    print("-" * 70)
    print("  测试结果摘要")
    print("-" * 70)
    print(f"  总计: {total}")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    print(f"  错误: {errors}")
    print(f"  通过率: {report['summary']['pass_rate']}%")
    print(f"  耗时: {elapsed:.2f} 秒")
    print()

    if failed_tests:
        print("  ❌ 失败测试:")
        for t in failed_tests:
            print(f"     - {t['test']}")
            if 'error' in t:
                print(f"       原因: {t['error'][:120]}")
        print()

    # 保存 JSON 报告
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'test_report_v6.1.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  📄 JSON 报告已保存: {report_path}")

    return report


def main():
    report = run_tests()
    if report['exit_code'] != 0:
        print(f"\n  ⚠️  测试套件返回非零退出码: {report['exit_code']}")
        sys.exit(report['exit_code'])
    return 0


if __name__ == '__main__':
    sys.exit(main())