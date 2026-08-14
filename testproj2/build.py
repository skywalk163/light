#!/usr/bin/env python3
"""段言项目构建脚本 - 编译 .duan 文件为 .py"""

import os
import sys
import subprocess
from pathlib import Path


def build():
    """编译项目中所有 .duan 文件"""
    project_dir = Path(__file__).parent
    entry = project_dir / "main.duan"

    if not entry.exists():
        print(f"[错误] 入口文件不存在: {entry}")
        return False

    # 编译入口文件
    result = subprocess.run(
        [sys.executable, "-m", "cli.duan_unified", "compile", str(entry)],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
        return False

    # 编译测试文件
    test_entry = project_dir / "tests" / "test_工具.duan"
    if test_entry.exists():
        result = subprocess.run(
            [sys.executable, "-m", "cli.duan_unified", "compile", str(test_entry)],
            capture_output=True, text=True, cwd=str(project_dir)
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout)
            return False

    print(f"[成功] 项目构建完成: {project_dir}")
    return True


def run_tests():
    """运行测试"""
    project_dir = Path(__file__).parent
    test_file = project_dir / "tests" / "test_工具.duan"
    
    if not test_file.exists():
        print("[错误] 测试文件不存在")
        return False
    
    result = subprocess.run(
        [sys.executable, "-m", "cli.duan_unified", "run", str(test_file)],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


if __name__ == "__main__":
    # 默认构建，如果参数是 "test" 则运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = run_tests()
    else:
        success = build()
    sys.exit(0 if success else 1)
