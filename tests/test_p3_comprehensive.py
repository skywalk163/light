#!/usr/bin/env python3
"""
P3 终极验证：编译更复杂的 v3.2 程序
测试 LLVM 后端对多种语言特性的综合支持
"""
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, 'src')
from llvm.compiler import compile_source_typed, find_clang


def run_test(name, code, expected_output=None):
    """编译并运行一个光明程序，返回是否成功"""
    print(f"\n{'='*60}")
    print(f"  测试: {name}")
    print(f"{'='*60}")

    # 1. 生成 IR
    try:
        ir = compile_source_typed(code, verbose=False)
        print(f"  [✓] IR 生成成功: {len(ir)} 字符")
    except Exception as e:
        print(f"  [✗] IR 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. 保存 IR 并编译
    ir_path = f'tests/_p3_{name}.ll'
    exe_path = f'tests/_p3_{name}.exe'
    with open(ir_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    try:
        clang = find_clang()
        runtime_c = 'src/llvm/runtime_typed.c'
        result = subprocess.run(
            [clang, '-O2', '-o', exe_path, ir_path, runtime_c],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=30
        )

        if result.returncode != 0:
            print(f"  [✗] 编译失败!")
            print(f"  stderr: {result.stderr[:2000]}")
            return False
        print(f"  [✓] 编译成功")

        # 3. 运行
        run_result = subprocess.run(
            [exe_path],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=10
        )

        output = run_result.stdout.strip()
        print(f"  输出:\n    {output.replace(chr(10), chr(10) + '    ')}")

        if run_result.stderr:
            print(f"  stderr: {run_result.stderr[:500]}")
        print(f"  返回码: {run_result.returncode}")

        if expected_output is not None:
            if expected_output in output:
                print(f"  [✓] 输出验证通过")
            else:
                print(f"  [✗] 输出不匹配，期望包含: {expected_output}")
                return False

        return True

    except subprocess.TimeoutExpired:
        print(f"  [✗] 运行超时")
        return False
    except Exception as e:
        print(f"  [✗] 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        for p in [ir_path, exe_path]:
            if os.path.exists(p):
                os.unlink(p)


# ============================================================
# 测试用例
# ============================================================

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


def main():
    print("=" * 60)
    print("  P3 终极验证：复杂 v3.2 程序编译测试")
    print("=" * 60)

    passed = 0
    failed = 0
    failed_tests = []

    for name, code, expected in TESTS:
        if run_test(name, code, expected):
            passed += 1
        else:
            failed += 1
            failed_tests.append(name)

    print(f"\n{'='*60}")
    print(f"  测试结果: {passed} 通过, {failed} 失败, 共 {len(TESTS)} 个")
    print(f"{'='*60}")

    if failed_tests:
        print(f"  失败的测试: {', '.join(failed_tests)}")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
