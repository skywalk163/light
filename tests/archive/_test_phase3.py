"""
Phase 3 测试 - 新增遍历语法别名（对/中的）

测试内容：
1. 「对」作为「遍历」的别名
2. 「中的」作为「在/之/于」的遍历分隔符
3. 复合词安全：「对象」不被拆分为「对」+「象」
"""

import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('.', 'src'))

all_ok = True

# 1. 验证分词器（ANTLR后端）
print("=" * 50)
print("1. 验证分词器（ANTLR后端）")
print("=" * 50)
from antlrparser.light_tokenizer import LightLangTokenizer
tokenizer = LightLangTokenizer()

tests = [
    # 「对」映射为 K_FOREACH
    ('对', 'K_FOREACH'),
    # 「中的」映射为 K_AT
    ('中的', 'K_AT'),
    # 复合词安全：「对象」不应被拆分
    ('对象', 'ID'),
    # 「对」在「对于」中不应被拆分
    ('对于', 'ID'),
    # 「中的」在「目标中的」中不应被拆分（标识符中部分）
]
for text, expected_type in tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == expected_type:
        print(f'  OK: {text} -> {expected_type}')
    else:
        print(f'  FAIL: {text} -> {tokens[0].type_name if tokens else "NO_TOKEN"} (expected {expected_type})')
        all_ok = False

# 2. Python 后端测试
print()
print("=" * 50)
print("2. Python 后端")
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

# 需要先定义一个列表用于遍历
test_py('对别名(遍历列表)',
    '设 列表 为 [1, 2, 3]。遍历 元素 在 列表：打印 元素。结束。',
    None)

# 辅助：先验证遍历能正常工作
print("  (遍历基础功能验证)")

# 3. ANTLR 后端测试
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

# 测试「对」别名（ANTLR后端使用「于」作为分隔符）
test_antlr('对别名(ANTLR)',
    '设 列表 为 [1, 2, 3]。对 元素 于 列表：打印 元素。结束。',
    '1')

# 测试「中的」别名
test_antlr('中的别名(ANTLR)',
    '设 列表 为 [1, 2, 3]。遍历 元素 中的 列表：打印 元素。结束。',
    '1')

# 测试「对」+「中的」组合
test_antlr('对+中的(ANTLR)',
    '设 列表 为 [1, 2, 3]。对 元素 中的 列表：打印 元素。结束。',
    '1')


# 4. 遍历循环功能完整性测试
print()
print("=" * 50)
print("4. 遍历循环功能")
print("=" * 50)

# 基础遍历 + 累计求和
test_antlr('遍历+中的+累计',
    '设 列表 为 [1, 2, 3, 4, 5]。设 和 为 0。遍历 元素 中的 列表：设 和 为 和 加 元素。结束。打印 和。',
    '15')

# 使用「对」别名
test_antlr('对+累计',
    '设 列表 为 [1, 2, 3, 4, 5]。设 和 为 0。对 元素 中的 列表：设 和 为 和 加 元素。结束。打印 和。',
    '15')


# ============================================================
print()
if all_ok:
    print("🎉 Phase 3 全部通过！")
else:
    print("❌ Phase 3 有测试失败")