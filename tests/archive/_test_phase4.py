"""
Phase 4 测试 - 「结束」在简单块中可选

测试内容：
1. Python后端：结束在简单块中可选
2. ANTLR后端：通过预处理自动插入结束
"""

import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('.', 'src'))

all_ok = True

# 1. Python 后端测试
print("=" * 50)
print("1. Python 后端")
print("=" * 50)
from light_parser_v3 import LightParser as PyParser
from code_generator import PythonCodeGenerator

def test_py(name, source, expected_in_output=None):
    global all_ok
    try:
        parser = PyParser()
        module = parser.parse(source)
        gen = PythonCodeGenerator()
        code = gen.generate(module)
        local_vars = {}
        exec(code, {}, local_vars)
        if expected_in_output is not None:
            local_vals = {k: v for k, v in local_vars.items() if not k.startswith('_')}
            if expected_in_output not in str(local_vals):
                print(f'  FAIL({name}): unexpected result')
                all_ok = False
                return
        print(f'  OK: {name}')
    except Exception as e:
        print(f'  FAIL({name}): {e}')
        all_ok = False

# Python后端已支持结束可选
test_py('如果-无结束',
    '设 甲 为 5。如果 甲 大于 3：打印 "ok"。',
    None)

test_py('如果-有结束',
    '设 甲 为 5。如果 甲 大于 3：打印 "ok"。结束。',
    None)

test_py('遍历-无结束',
    '设 列表 为 [1, 2]。遍历 元素 在 列表：打印 元素。',
    None)

test_py('遍历-有结束',
    '设 列表 为 [1, 2]。遍历 元素 在 列表：打印 元素。结束。',
    None)


# 2. ANTLR 后端测试
print()
print("=" * 50)
print("2. ANTLR 后端")
print("=" * 50)
from antlrparser.light_visitor import parse_source
from antlrparser.light_interpreter import Interpreter

def test_antlr(name, source, expected_in_output):
    global all_ok
    module = parse_source(source)
    if not module:
        # 如果解析失败，显示更详细的信息
        from antlrparser.light_visitor import LightParser
        p = LightParser()
        p.parse(source)
        if p.errors:
            print(f'  FAIL({name}): 解析错误 - {p.errors[0]}')
        else:
            print(f'  FAIL({name}): 解析错误（未知）')
        all_ok = False
        return
    interp = Interpreter()
    try:
        interp.interpret(module)
        output = ''.join(interp.output_lines)
        if expected_in_output in output:
            print(f'  OK: {name} -> {output.strip()}')
        else:
            print(f'  FAIL({name}): expected "{expected_in_output}" in "{output}"')
            all_ok = False
    except Exception as e:
        print(f'  FAIL({name}): {e}')
        all_ok = False

# 测试有结束（原始语法）
test_antlr('遍历-有结束',
    '设 列表 为 [1, 2]。遍历 元素 于 列表：打印 元素。结束。',
    '1')

# 测试无结束（新语法-预处理自动补全）
test_antlr('遍历-无结束',
    '设 列表 为 [1, 2]。遍历 元素 于 列表：打印 元素。设 甲 为 3。打印 甲。',
    '3')

# 测试函数定义后直接跟语句（无结束）
test_antlr('函数-无结束+后续语句',
    '函数 双倍 接收 数：返回 数 乘 2。设 结果 为 双倍(5)。打印 结果。',
    '10')

# 测试if语句无结束
test_antlr('如果-无结束',
    '设 甲 为 10。如果 甲 大于 5：打印 "大"。设 乙 为 20。打印 乙。',
    '20')

# 测试多个语句连续（无结束）
test_antlr('多语句-无结束',
    '设 列表 为 [1, 2]。对 元素 中的 列表：打印 元素。设 和 为 0。遍历 项 中的 列表：设 和 为 和 加 项。打印 和。',
    '3')


# ============================================================
print()
if all_ok:
    print("🎉 Phase 4 全部通过！")
else:
    print("❌ Phase 4 有测试失败")