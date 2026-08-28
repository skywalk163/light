# -*- coding: utf-8 -*-
"""调试cb_追加生成代码"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from code_generator import PythonCodeGenerator

content = open('blocks_v5/密码/Argon2.light', 'r', encoding='utf-8').read()
print('=== Source ===')
print(content)

parser = LightParser()
try:
    module = parser.parse(content)
    print('\n=== AST ===')
    for i, stmt in enumerate(module.statements):
        print(f'  [{i}] {type(stmt).__name__}: {stmt}')
        if hasattr(stmt, 'body'):
            print(f'  body: {stmt.body}')
        # 检查内部语句
        if hasattr(stmt, 'statements'):
            print(f'  statements: {stmt.statements}')
    
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    print('\n=== Generated Python Code ===')
    print(py_code)
except ParseError as e:
    print(f'\nParseError: {e}')
except Exception as e:
    print(f'\nError: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()