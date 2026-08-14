#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（Duan）练习检查脚本

自动运行指定练习的 .duan 文件，将实际输出与预期输出比较，
并输出检查结果（通过/失败 + 差异）。

用法：
    python checker.py list                    # 列出所有练习
    python checker.py run <练习名>             # 运行单个练习
    python checker.py run all                 # 运行所有练习
    python checker.py run <练习名> --show      # 运行并显示详细差异
"""

import argparse
import os
import re
import subprocess
import sys

# ── 路径配置 ──────────────────────────────────────────────────────
# 支持从任何目录运行
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_EXERCISES_DIR = os.path.join(_SCRIPT_DIR, "exercises")
_PROJECT_DIR = os.path.dirname(os.path.dirname(_SCRIPT_DIR))  # 项目根目录

# 练习列表（按顺序）
EXERCISES = [
    "hello",
    "variables",
    "conditions",
    "loops",
    "functions",
    "lists",
    "strings",
    "dicts",
    "files",
    "comprehensive",
]

# 练习中文名
EXERCISE_NAMES = {
    "hello": "Hello World",
    "variables": "变量与运算",
    "conditions": "条件判断",
    "loops": "循环",
    "functions": "函数定义和调用",
    "lists": "列表操作",
    "strings": "字符串处理",
    "dicts": "字典操作",
    "files": "文件读写",
    "comprehensive": "综合练习",
}


# ── ANSI 颜色 ─────────────────────────────────────────────────────
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def color(text, *codes):
    """应用 ANSI 颜色代码"""
    return "".join(codes) + text + Colors.RESET


# ── 工具函数 ──────────────────────────────────────────────────────
def find_exercise_dir(name: str) -> str:
    """返回练习文件所在目录"""
    return _EXERCISES_DIR


def find_solution_file(name: str) -> str:
    """返回参考答案文件路径"""
    return os.path.join(_EXERCISES_DIR, f"{name}_solution.duan")


def find_skeleton_file(name: str) -> str:
    """返回骨架代码文件路径"""
    return os.path.join(_EXERCISES_DIR, f"{name}.duan")


def find_md_file(name: str) -> str:
    """返回练习说明文件路径"""
    return os.path.join(_EXERCISES_DIR, f"{name}.md")


def parse_expected_output(md_path: str) -> str:
    """
    从 .md 文件中解析预期输出。

    查找 `## 预期输出` 之后的代码块（```...```）内容。
    """
    if not os.path.exists(md_path):
        return ""

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找 ## 预期输出 之后的代码块
    pattern = r"## 预期输出\s*\n```\s*\n(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).rstrip("\n")
    return ""


def run_duan_file(filepath: str) -> tuple[int, str, str]:
    """
    运行 .duan 文件，返回 (返回码, stdout, stderr)。

    使用 subprocess 调用 duan_unified 解释器。
    """
    cmd = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "cli.duan_unified",
        "run",
        filepath,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=_PROJECT_DIR,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "执行超时（30秒）"
    except FileNotFoundError:
        return -1, "", f"找不到解释器: {sys.executable}"
    except Exception as e:
        return -1, "", str(e)


def normalize_output(text: str) -> str:
    """标准化输出，去除尾部空白和空行以便比较"""
    lines = text.rstrip("\n").split("\n")
    # 去除每行尾部空白
    lines = [line.rstrip() for line in lines]
    # 去除首尾空行，但保留中间空行
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(lines)


# ── 核心检查逻辑 ──────────────────────────────────────────────────
def check_exercise(name: str, show_diff: bool = False) -> dict:
    """
    检查单个练习。

    返回包含检查结果的字典：
    {
        "name": str,
        "passed": bool,
        "expected": str,
        "actual": str,
        "error": str,
        "diff_lines": list,
    }
    """
    solution_file = find_solution_file(name)
    md_file = find_md_file(name)

    result = {
        "name": name,
        "passed": False,
        "expected": "",
        "actual": "",
        "error": "",
        "diff_lines": [],
    }

    # 检查参考答案文件是否存在
    if not os.path.exists(solution_file):
        result["error"] = f"找不到参考答案文件: {solution_file}"
        return result

    # 解析预期输出
    expected = parse_expected_output(md_file)
    result["expected"] = expected

    # 运行参考答案文件
    returncode, stdout, stderr = run_duan_file(solution_file)

    if returncode != 0:
        result["error"] = f"运行失败（返回码 {returncode}）"
        if stderr:
            result["error"] += f"\n{stderr.strip()}"
        if stdout:
            result["actual"] = stdout.strip()
        return result

    # 捕获实际输出
    actual = stdout.strip()
    result["actual"] = actual

    # 比较输出
    norm_expected = normalize_output(expected)
    norm_actual = normalize_output(actual)

    if norm_expected == norm_actual:
        result["passed"] = True
    else:
        # 计算差异行
        exp_lines = norm_expected.split("\n") if norm_expected else []
        act_lines = norm_actual.split("\n") if norm_actual else []
        max_len = max(len(exp_lines), len(act_lines))

        for i in range(max_len):
            e = exp_lines[i] if i < len(exp_lines) else None
            a = act_lines[i] if i < len(act_lines) else None
            if e != a:
                result["diff_lines"].append((i + 1, e or "", a or ""))

    return result


def print_exercise_result(result: dict, show_diff: bool = False):
    """打印单个练习的检查结果"""
    name = result["name"]
    display_name = EXERCISE_NAMES.get(name, name)

    if result["error"]:
        print(f"  {color('✗', Colors.RED)} {display_name}")
        print(f"    {color('错误:', Colors.RED)} {result['error']}")
        return

    if result["passed"]:
        status = color("✓ 通过", Colors.GREEN, Colors.BOLD)
        print(f"  {color('✓', Colors.GREEN)} {display_name}  {status}")
    else:
        print(f"  {color('✗', Colors.RED)} {display_name}  {color('✗ 失败', Colors.RED, Colors.BOLD)}")

        if show_diff or True:
            if not result["expected"]:
                print(f"    {color('提示:', Colors.YELLOW)} 未找到预期输出（.md 文件中可能缺少 ## 预期输出 部分）")
            else:
                print(f"    {color('预期输出:', Colors.CYAN)}")
                for line in result["expected"].split("\n"):
                    print(f"      {line}")
                print(f"    {color('实际输出:', Colors.YELLOW)}")
                for line in result["actual"].split("\n"):
                    print(f"      {line}")

            if result["diff_lines"]:
                print(f"    {color('差异:', Colors.RED)}")
                for line_no, expected, actual in result["diff_lines"]:
                    print(f"      第 {line_no} 行:")
                    print(f"        {color(f'预期: {repr(expected)}', Colors.CYAN)}")
                    print(f"        {color(f'实际: {repr(actual)}', Colors.YELLOW)}")


# ── 命令实现 ──────────────────────────────────────────────────────
def cmd_list():
    """列出所有练习"""
    print(f"\n{color('段言练习列表', Colors.BOLD, Colors.CYAN)}")
    print(f"{'=' * 60}")
    print(f"  {'编号':<6} {'练习名':<20} {'说明文件':<20} {'骨架代码':<20} {'参考答案':<20}")
    print(f"{'-' * 60}")

    for i, name in enumerate(EXERCISES, 1):
        display_name = EXERCISE_NAMES.get(name, name)
        md_exists = os.path.exists(find_md_file(name))
        skel_exists = os.path.exists(find_skeleton_file(name))
        sol_exists = os.path.exists(find_solution_file(name))

        md_mark = color("✓", Colors.GREEN) if md_exists else color("✗", Colors.RED)
        skel_mark = color("✓", Colors.GREEN) if skel_exists else color("✗", Colors.RED)
        sol_mark = color("✓", Colors.GREEN) if sol_exists else color("✗", Colors.RED)

        print(f"  {i:<6} {display_name:<20} {md_mark:<20} {skel_mark:<20} {sol_mark:<20}")

    print(f"{'='  * 60}")
    print(f"  共 {len(EXERCISES)} 个练习\n")


def cmd_run(exercise_name: str, show_diff: bool = False):
    """运行指定练习或所有练习"""
    if exercise_name == "all":
        run_all(show_diff)
    elif exercise_name in EXERCISES:
        run_single(exercise_name, show_diff)
    else:
        print(f"{color('错误:', Colors.RED)} 未知练习名: {exercise_name}")
        print(f"可用练习: {', '.join(EXERCISES)}")
        sys.exit(1)


def run_single(name: str, show_diff: bool = False):
    """运行单个练习"""
    display_name = EXERCISE_NAMES.get(name, name)
    print(f"\n{color(f'▶ 检查练习: {display_name}', Colors.BOLD, Colors.CYAN)}")
    print(f"{'=' * 60}")

    result = check_exercise(name, show_diff)
    print_exercise_result(result, show_diff)

    print(f"{'=' * 60}")
    if result["passed"]:
        print(f"  {color('结果: 通过 ✓', Colors.GREEN, Colors.BOLD)}")
    else:
        print(f"  {color('结果: 失败 ✗', Colors.RED, Colors.BOLD)}")
    print()


def run_all(show_diff: bool = False):
    """运行所有练习"""
    total = len(EXERCISES)
    passed = 0
    failed = 0
    errors = 0

    print(f"\n{color('段言练习检查报告', Colors.BOLD, Colors.CYAN)}")
    print(f"{'=' * 60}")
    print(f"  开始检查 {total} 个练习...\n")

    results = []
    for name in EXERCISES:
        result = check_exercise(name, show_diff)
        results.append(result)
        print_exercise_result(result, show_diff)

        if result["error"]:
            errors += 1
        elif result["passed"]:
            passed += 1
        else:
            failed += 1

    # 汇总统计
    print(f"\n{color('=' * 60, Colors.BOLD)}")
    print(f"{color('汇总统计', Colors.BOLD, Colors.CYAN)}")
    print(f"  总练习: {total}")
    print(f"  {color(f'通过: {passed}', Colors.GREEN, Colors.BOLD)}")
    if failed > 0:
        print(f"  {color(f'失败: {failed}', Colors.RED, Colors.BOLD)}")
    if errors > 0:
        print(f"  {color(f'错误: {errors}', Colors.YELLOW, Colors.BOLD)}")

    if passed == total:
        print(f"\n  {color('恭喜！所有练习全部通过！ 🎉', Colors.GREEN, Colors.BOLD)}")
    else:
        print(f"\n  {color(f'通过率: {passed}/{total} ({passed * 100 // total}%)', Colors.YELLOW, Colors.BOLD)}")
    print()


# ── 主入口 ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="段言（Duan）练习检查脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python checker.py list              # 列出所有练习\n"
            "  python checker.py run all           # 检查所有练习\n"
            "  python checker.py run hello         # 检查单个练习\n"
            "  python checker.py run hello --show  # 显示详细差异\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list 子命令
    subparsers.add_parser("list", help="列出所有练习")

    # run 子命令
    p_run = subparsers.add_parser("run", help="运行练习检查")
    p_run.add_argument("exercise", help="练习名（如 hello）或 all（全部检查）")
    p_run.add_argument("--show", action="store_true", help="显示详细差异信息")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "run":
        cmd_run(args.exercise, show_diff=args.show)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()