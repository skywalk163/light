#!/usr/bin/env python3
"""
P3 终极验证：编译更复杂的 v3.2 程序
测试 LLVM 后端对多种语言特性的综合支持

说明：原文件为模块级脚本（无 pytest 测试函数），pytest 收集 0 个测试，
属「虚假通过」（D04 测试可信度债务）。已迁移为真正的 pytest 参数化测试。
LLVM 编译需依赖 clang，本机未安装时明确跳过（环境缺失，非测试失败）。
"""

import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from llvm.compiler import compile_source_typed, find_clang

# clang 不可用时跳过（环境缺失，非测试失败）
try:
    _CLANG = find_clang()
    CLANG_AVAILABLE = bool(_CLANG)
except Exception:
    _CLANG = None
    CLANG_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CLANG_AVAILABLE,
    reason="clang 编译器不可用（未安装 LLVM），跳过 LLVM 编译测试"
)


def _run_llvm_test(code, expected_output):
    """编译并运行一个光明程序，返回 (成功, 信息)"""
    # 1. 生成 IR
    try:
        ir = compile_source_typed(code, verbose=False)
    except Exception as e:
        return False, f"IR 生成失败: {e}"

    if not ir:
        return False, "IR 生成失败: 空输出"

    # 2. 保存 IR 并编译
    with tempfile.TemporaryDirectory() as tmpdir:
        ir_path = os.path.join(tmpdir, 'prog.ll')
        exe_path = os.path.join(tmpdir, 'prog.exe')
        with open(ir_path, 'w', encoding='utf-8') as f:
            f.write(ir)
        try:
            clang = find_clang()
            runtime_c = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'src', 'llvm', 'runtime_typed.c')
            result = subprocess.run(
                [clang, '-O2', '-o', exe_path, ir_path, runtime_c],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=30
            )
            if result.returncode != 0:
                return False, f"编译失败: {result.stderr[:1000]}"

            # 3. 运行
            run_result = subprocess.run(
                [exe_path],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=10
            )
            output = run_result.stdout.strip()
            if expected_output is not None and expected_output not in output:
                return False, f"输出不匹配，期望包含 '{expected_output}'，实际: '{output}'"
            return True, output
        except subprocess.TimeoutExpired:
            return False, "运行超时"
        except Exception as e:
            return False, f"错误: {e}"


TESTS = []

# 测试1: 变量、算术、打印
TESTS.append((
    "01_基本算术",
    '''
设 甲 为 10
设 乙 为 20
设 丙 为 甲 加 乙
打印 丙
''',
    "30"
))

# 测试2: 条件语句
TESTS.append((
    "02_条件分支",
    '''
设 分数 为 85
如果 分数 大于 60：
  打印 "及格"
否则：
  打印 "不及格"
''',
    "及格"
))

# 测试3: while 循环
TESTS.append((
    "03_循环累加",
    '''
设 总和 为 0
设 计数 为 1
当 计数 小于等于 5：
  总和 = 总和 加 计数
  计数 = 计数 加 1
打印 总和
''',
    "15"
))

# 测试4: 段落定义与调用
TESTS.append((
    "04_段落调用",
    '''
段落 加法 接收 甲, 乙：
  返回 甲 加 乙

设 结果 为 加法(3, 5)
打印 结果
''',
    "8"
))

# 测试5: 嵌套段落调用
TESTS.append((
    "05_嵌套调用",
    '''
段落 平方 接收 数：
  返回 数 乘 数

段落 立方 接收 数：
  返回 数 乘 数 乘 数

打印 平方(4)
打印 立方(3)
''',
    "16"
))

# 测试6: 多条件分支
TESTS.append((
    "06_多条件",
    '''
设 等级 为 85
如果 等级 大于 90：
  打印 "优秀"
否则 如果 等级 大于 80：
  打印 "良好"
否则 如果 等级 大于 60：
  打印 "及格"
否则：
  打印 "不及格"
''',
    "良好"
))

# 测试7: 段落内条件逻辑
TESTS.append((
    "07_段落条件",
    '''
段落 判断 接收 数：
  如果 数 大于 0：
    返回 1
  否则：
    返回 0

打印 判断(5)
打印 判断(-3)
''',
    "1"
))

# 测试8: 循环中的条件
TESTS.append((
    "08_循环条件",
    '''
设 计数 为 0
设 偶数和 为 0
当 计数 小于 10：
  计数 = 计数 加 1
  如果 计数 模 2 等于 0：
    偶数和 = 偶数和 加 计数
打印 偶数和
''',
    "30"
))

# 测试9: 递归段落（阶乘）
TESTS.append((
    "09_递归阶乘",
    '''
段落 阶乘 接收 数：
  如果 数 小于等于 1：
    返回 1
  否则：
    返回 数 乘 阶乘(数 减 1)

打印 阶乘(5)
''',
    "120"
))

# 测试10: 字符串处理
TESTS.append((
    "10_字符串",
    '''
设 名字 为 "光明"
打印 名字
打印 "你好"
''',
    "光明"
))

# 测试11: 减法与负数
TESTS.append((
    "11_减法运算",
    '''
设 甲 为 100
设 乙 为 45
打印 甲 减 乙
打印 乙 减 甲
''',
    "55"
))

# 测试12: 乘除模运算
TESTS.append((
    "12_乘除模",
    '''
设 甲 为 7
设 乙 为 3
打印 甲 乘 乙
打印 甲 除 乙
打印 甲 模 乙
''',
    "21"
))

# 测试13: 复杂表达式
TESTS.append((
    "13_复杂表达式",
    '''
设 甲 为 3
设 乙 为 4
设 丙 为 (甲 加 乙) 乘 2
打印 丙
''',
    "14"
))

# 测试14: 段落多参数与返回值
TESTS.append((
    "14_多参数段落",
    '''
段落 计算 接收 甲, 乙, 丙：
  返回 甲 加 乙 加 丙

打印 计算(10, 20, 30)
''',
    "60"
))

# 测试15: 斐波那契递归
TESTS.append((
    "15_斐波那契",
    '''
段落 斐波那契 接收 数：
  如果 数 小于 2：
    返回 数
  否则：
    返回 斐波那契(数 减 1) 加 斐波那契(数 减 2)

打印 斐波那契(10)
''',
    "55"
))

# 测试16: 嵌套循环
TESTS.append((
    "16_嵌套循环",
    '''
设 结果 为 0
设 外层 为 0
当 外层 小于 3：
  设 内层 为 0
  当 内层 小于 3：
    结果 = 结果 加 1
    内层 = 内层 加 1
  外层 = 外层 加 1
打印 结果
''',
    "9"
))

# 测试17: 段落调用链
TESTS.append((
    "17_调用链",
    '''
段落 双倍 接收 数：
  返回 数 乘 2

段落 加一 接收 数：
  返回 数 加 1

设 结果 为 双倍(加一(5))
打印 结果
''',
    "12"
))

# 测试18: 比较运算
TESTS.append((
    "18_比较运算",
    '''
设 甲 为 5
设 乙 为 10
如果 甲 小于 乙：
  打印 "甲小于乙"
否则：
  打印 "甲大于等于乙"
''',
    "甲小于乙"
))

# 测试19: 最大值段落
TESTS.append((
    "19_最大值",
    '''
段落 最大值 接收 甲, 乙：
  如果 甲 大于 乙：
    返回 甲
  否则：
    返回 乙

打印 最大值(15, 8)
''',
    "15"
))

# 测试20: 累乘
TESTS.append((
    "20_累乘",
    '''
段落 累乘 接收 数：
  设 结果 为 1
  设 计数 为 1
  当 计数 小于等于 数：
    结果 = 结果 乘 计数
    计数 = 计数 加 1
  返回 结果

打印 累乘(6)
''',
    "720"
))


@pytest.mark.parametrize("name,code,expected", TESTS, ids=[t[0] for t in TESTS])
def test_llvm_program(name, code, expected):
    """LLVM 后端编译并运行光明程序，验证输出"""
    ok, info = _run_llvm_test(code, expected)
    assert ok, info
