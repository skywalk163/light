#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析生成的Python代码"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lexer import Lexer
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

filepath = sys.argv[1]
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

print(f'=== 源文件: {filepath} ===')
print(content)
print()

# 使用LightParser直接解析源代码
parser = LightParser()
module = parser.parse(content)
print('=== AST ===')
print(module)
print()

gen = PythonCodeGenerator()
code = gen.generate(module)
print('=== Generated Python ===')
print(code)