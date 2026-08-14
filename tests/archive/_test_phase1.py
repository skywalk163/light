"""Phase 1 验证脚本 - 修正版"""
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('.', 'src'))

all_ok = True

# 1. 验证分词器
print("=" * 50)
print("1. 验证分词器")
print("=" * 50)
from antlrparser.light_tokenizer import LightLangTokenizer
tokenizer = LightLangTokenizer()

tests = [
    ('函数', 'K_SEGMENT'),
    ('若', 'K_IF'),
    ('则', 'K_THEN'),
    ('段落', 'K_SEGMENT'),
    ('如果', 'K_IF'),
    ('接收', 'K_RECEIVE'),
]
for text, expected_type in tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == expected_type:
        print(f'  OK: {text} -> {expected_type}')
    else:
        print(f'  FAIL: {text} -> {tokens[0].type_name if tokens else "NO_TOKEN"} (expected {expected_type})')
        all_ok = False

# 复合词安全
compound_tests = ['若干', '规则']
for text in compound_tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == 'ID':
        print(f'  OK: {text} -> ID({tokens[0].text})')
    else:
        all_ok = False

# 2. Python 后端测试（无需句号/结束）
print()
print("=" * 50)
print("2. Python 后端")
print("=" * 50)
from light_parser_v3 import LightParser as PyParser
from code_generator import PythonCodeGenerator

def test_py(name, source, expected_output=None):
    global all_ok
    try:
        parser = PyParser()
        module = parser.parse(source)
        gen = PythonCodeGenerator()
        code = gen.generate(module)
        local_vars = {}
        exec(code, {}, local_vars)
        if expected_output is not None:
            local_vals = {k: v for k, v in local_vars.items() if not k.startswith('_')}
            if expected_output not in str(local_vals):
                print(f'  FAIL({name}): unexpected result')
                all_ok = False
                return
        print(f'  OK: {name}')
    except Exception as e:
        print(f'  FAIL({name}): {e}')
        all_ok = False

# 测试函数别名
test_py('函数别名',
    '函数 平方 输入 数值：返回 数值 乘 数值。',
    None)

# 测试若别名
test_py('若条件',
    '若 真：打印 "ok"。')
print("   (若别名通过)")

# 3. ANTLR 后端（严格语法，需要句号和结束）
print()
print("=" * 50)
print("3. ANTLR 后端")
print("=" * 50)
from antlrparser.light_visitor import parse_source
from antlrparser.light_interpreter import Interpreter

def test_antlr(name, source, expected_in_output):
    global all_ok
    module = parse_source(source)
    if not module:
        print(f'  FAIL({name}): parse error')
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

# 函数别名（严格语法）
test_antlr('函数+接收',
    '函数 平方 接收 数值：返回 数值 乘 数值。结束。设 结果 为 平方(5)。打印 结果。',
    '25')

# 若条件别名
test_antlr('若条件',
    '设 甲 为 10。若 甲 大于 5：打印 "甲大于5"。否则：打印 "甲不大于5"。结束。',
    '甲大于5')

# 向后兼容（原有关键字仍然有效）
test_antlr('向后兼容',
    '段落 平方 接收 数值：返回 数值 乘 数值。结束。设 结果 为 平方(5)。打印 结果。',
    '25')

print()
if all_ok:
    print("所有测试通过!")
else:
    print("有测试失败!")
    sys.exit(1)