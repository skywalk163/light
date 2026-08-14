"""
Phase 5 验证脚本 - 复合赋值语法（加上、减去等）

测试内容：
  甲 加上 1。  → 甲 += 1
  甲 减去 2。  → 甲 -= 2
  甲 乘以 3。  → 甲 *= 3
  甲 除以 4。  → 甲 /= 4
  甲 模以 5。  → 甲 %= 5
  甲 幂以 2。  → 甲 **= 2
"""
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('.', 'src'))

all_ok = True

# 1. 验证分词器
print("=" * 50)
print("1. 验证分词器（ANTLR后端）")
print("=" * 50)
from antlrparser.light_tokenizer import LightLangTokenizer
tokenizer = LightLangTokenizer()

token_tests = [
    ('加上', 'K_PLUS_ASSIGN'),
    ('减去', 'K_MINUS_ASSIGN'),
    ('乘以', 'K_MULTIPLY_ASSIGN'),
    ('除以', 'K_DIVIDE_ASSIGN'),
    ('模以', 'K_MOD_ASSIGN'),
    ('幂以', 'K_POW_ASSIGN'),
]
for text, expected_type in token_tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == expected_type:
        print(f'  OK: {text} -> {expected_type}')
    else:
        print(f'  FAIL: {text} -> {tokens[0].type_name if tokens else "NO_TOKEN"} (expected {expected_type})')
        all_ok = False

# 验证原有关键字仍正常工作
old_tests = [
    ('加', 'K_PLUS'),
    ('减', 'K_MINUS'),
    ('乘', 'K_MULTIPLY'),
    ('设', 'K_SET'),
    ('为', 'K_AS'),
]
for text, expected_type in old_tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == expected_type:
        print(f'  OK: {text} -> {expected_type}')
    else:
        print(f'  FAIL: {text} -> {tokens[0].type_name if tokens else "NO_TOKEN"} (expected {expected_type})')
        all_ok = False

# 复合词安全：「加上」不应被错误拆分
compound_tests = ['加工', '加减', '加法']
for text in compound_tests:
    tokens = tokenizer.tokenize(text)
    if tokens and tokens[0].type_name == 'ID':
        print(f'  OK: {text} -> ID({tokens[0].text})')
    else:
        print(f'  FAIL: {text} -> {tokens[0].type_name if tokens else "NO_TOKEN"} (expected ID)')
        all_ok = False

# 2. Python 后端测试
print()
print("=" * 50)
print("2. Python 后端（解析+代码生成）")
print("=" * 50)
from light_parser_v3 import LightParser as PyParser, CompoundAssignment
from code_generator import PythonCodeGenerator

def test_py(name, source, expected_py=None):
    global all_ok
    parser = PyParser()
    try:
        module = parser.parse(source)
        if not module.statements:
            print(f'  FAIL: {name}: 无语句')
            all_ok = False
            return
        stmt = module.statements[0]
        if not isinstance(stmt, CompoundAssignment):
            print(f'  FAIL: {name}: 期望 CompoundAssignment，得到 {type(stmt).__name__}')
            all_ok = False
            return
        gen = PythonCodeGenerator()
        py_code = gen.generate(module)
        if expected_py:
            # 验证生成的Python代码包含预期内容
            lines = [l for l in py_code.split('\n') if l.strip() and not l.strip().startswith('#')]
            stmt_line = next((l for l in lines if l.strip().startswith(('甲 ', '乙 ', '丙 '))), None)
            if stmt_line and expected_py in stmt_line:
                print(f'  OK: {name} -> {stmt_line.strip()}')
            else:
                print(f'  FAIL: {name}: 未找到 "{expected_py}"')
                print(f'        python code: {py_code}')
                all_ok = False
        else:
            print(f'  OK: {name}')
    except Exception as e:
        print(f'  FAIL: {name}: {e}')
        all_ok = False

# 验证解析器正确识别复合赋值
test_py('加上', '甲 加上 1。', '甲 += 1')
test_py('减去', '甲 减去 2。', '甲 -= 2')
test_py('乘以', '甲 乘以 3。', '甲 *= 3')
test_py('除以', '甲 除以 4。', '甲 /= 4')
test_py('模以', '甲 模以 5。', '甲 %= 5')
test_py('幂以', '甲 幂以 2。', '甲 **= 2')

# 验证与普通赋值不冲突
print()
print("  验证与普通赋值不冲突:")
from light_parser_v3 import VarDecl
parser = PyParser()
module = parser.parse('甲 等于 10。')
stmt = module.statements[0]
if isinstance(stmt, VarDecl):
    print(f'  OK: 普通赋值 -> VarDecl({stmt.name}, {stmt.value})')
else:
    print(f'  FAIL: 普通赋值 -> {type(stmt).__name__} (期望 VarDecl)')
    all_ok = False

# 3. ANTLR 后端测试
print()
print("=" * 50)
print("3. ANTLR 后端（解析+访问器）")
print("=" * 50)
sys.path.insert(0, os.path.join('.', 'antlrparser'))
from antlrparser.light_visitor import LightParser as LightLangVisitor

def test_antlr(name, source, expected_target=None, expected_op=None, expected_val=None):
    global all_ok
    try:
        visitor = LightLangVisitor()
        module = visitor.parse(source)
        if not module or not module.statements:
            print(f'  FAIL: {name}: 无语句')
            all_ok = False
            return
        stmt = module.statements[0]
        # 检查是否为 CompoundAssignment（通过属性判断，避免模块路径导致的 isinstance 问题）
        if not hasattr(stmt, 'target') or not hasattr(stmt, 'operator'):
            print(f'  FAIL: {name}: 期望 CompoundAssignment，得到 {type(stmt).__name__}')
            all_ok = False
            return
        if expected_target and stmt.target != expected_target:
            print(f'  FAIL: {name}: target="{stmt.target}" (expected "{expected_target}")')
            all_ok = False
            return
        if expected_op and stmt.operator != expected_op:
            print(f'  FAIL: {name}: operator="{stmt.operator}" (expected "{expected_op}")')
            all_ok = False
            return
        print(f'  OK: {name} -> {stmt.target} {stmt.operator}= ...')
    except Exception as e:
        print(f'  FAIL: {name}: {e}')
        all_ok = False

test_antlr('加上-ANTLR', '甲 加上 1。', '甲', '加')
test_antlr('减去-ANTLR', '甲 减去 2。', '甲', '减')
test_antlr('乘以-ANTLR', '甲 乘以 3。', '甲', '乘')
test_antlr('除以-ANTLR', '甲 除以 4。', '甲', '除')
test_antlr('模以-ANTLR', '甲 模以 5。', '甲', '模')
test_antlr('幂以-ANTLR', '甲 幂以 2。', '甲', '幂')

# 4. ANTLR 解释器执行测试
print()
print("=" * 50)
print("4. ANTLR 解释器执行测试")
print("=" * 50)
from antlrparser.light_interpreter import run_source

def test_run(name, source, expected_output=None):
    global all_ok
    try:
        interpreter = run_source(source)
        output = interpreter.get_output().strip()
        # 取最后一行输出（可能有 打印 和 输出 两行）
        last_line = output.split('\n')[-1] if '\n' in output else output
        if expected_output is not None:
            if last_line == expected_output:
                print(f'  OK: {name} -> "{output}"')
            else:
                print(f'  FAIL: {name}: 输出="{output}" (expected "{expected_output}")')
                all_ok = False
        else:
            print(f'  OK: {name}')
    except Exception as e:
        print(f'  FAIL: {name}: {e}')
        import traceback
        traceback.print_exc()
        all_ok = False

# 注意：解释器测试需要语句返回可打印的值
# 我们使用打印语句来检查结果
test_run('加上-执行', '设 甲 为 10。甲 加上 5。打印 甲。输出 甲。', '15')
test_run('减去-执行', '设 甲 为 10。甲 减去 3。打印 甲。输出 甲。', '7')
test_run('乘以-执行', '设 甲 为 5。甲 乘以 4。打印 甲。输出 甲。', '20')
test_run('除以-执行', '设 甲 为 20。甲 除以 4。打印 甲。输出 甲。', '5.0')
test_run('模以-执行', '设 甲 为 17。甲 模以 5。打印 甲。输出 甲。', '2')
test_run('幂以-执行', '设 甲 为 2。甲 幂以 3。打印 甲。输出 甲。', '8')

# 5. 多步连续复合赋值
print()
print("=" * 50)
print("5. 连续复合赋值")
print("=" * 50)
test_run('连续运算', '设 甲 为 2。甲 加上 3。甲 乘以 4。打印 甲。输出 甲。', '20')
test_run('混合运算', '设 甲 为 100。甲 减去 20。甲 除以 4。打印 甲。输出 甲。', '20.0')

# 输出汇总
print()
print("=" * 50)
if all_ok:
    print("Phase 5 全部测试通过！")
else:
    print(f"Phase 5 存在失败测试！")
print("=" * 50)

sys.exit(0 if all_ok else 1)