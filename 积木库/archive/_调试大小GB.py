# -*- coding: utf-8 -*-
"""调试大小GB.light 生成代码"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from code_generator import PythonCodeGenerator

content = open('blocks_v5/文件/大小GB.light', 'r', encoding='utf-8').read()
print('=== Source ===')
print(content)

parser = LightParser()
try:
    module = parser.parse(content)
    gen = PythonCodeGenerator()
    py_code = gen.generate(module)
    print('\n=== Generated Python Code ===')
    # 只打印函数体部分
    for line in py_code.split('\n'):
        if 'def ' in line or 'return ' in line or 'cb_' in line or '文本' in line:
            print(line)
except Exception as e:
    print(f'Error: {e}')