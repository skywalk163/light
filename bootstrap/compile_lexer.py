import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'cli')
from lexer import Lexer
from light_parser_v3 import LightParser
from semantic_analyzer import SemanticAnalyzer
from code_generator import PythonCodeGenerator
with open('bootstrap/lexer.light', 'r', encoding='utf-8') as f:
    source = f.read()
lexer = Lexer()
tokens = lexer.tokenize(source)
print(f'Tokens: {len(tokens)}')
parser = LightParser()
module = parser.parse(source)
print(f'Statements: {len(module.statements)}')
analyzer = SemanticAnalyzer()
stdfuncs = ['字典创建','字典设置','字典获取','字典包含键','列表创建','列表追加','列表长度','列表获取','列表包含','列表弹出','字符串长度','字符串获取','截取']
for fn in stdfuncs:
    analyzer.symbol_table.define(fn, 'paragraph', '未知')
success = analyzer.analyze(module)
if analyzer.errors:
    for e in analyzer.errors:
        print(f'  Error: {e.message}')
if success:
    gen = PythonCodeGenerator()
    code = gen.generate(module)
    with open('bootstrap/lexer_compiled.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'Generated: {len(code)} chars')
else:
    print('FAILED')

# Add token.light functions
analyzer.symbol_table.define('创建令牌','paragraph','未知')
analyzer.symbol_table.define('令牌种别集','paragraph','未知')
analyzer.symbol_table.define('是关键字','paragraph','未知')
analyzer.symbol_table.define('符号种别','paragraph','未知')
