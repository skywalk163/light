# -*- coding: utf-8 -*-
"""查看完整生成的Python代码"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

files = [
    r'D:\traework\light\积木库\blocks_v5\体育\PER.light',
    r'D:\traework\light\积木库\blocks_v5\体育\三分命中率.light',
    r'D:\traework\light\积木库\blocks_v5\密码\密钥强度.light',
]

for fpath in files:
    name = os.path.basename(fpath)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    try:
        parser = LightParser()
        module = parser.parse(content)
        gen = PythonCodeGenerator()
        py_code = gen.generate(module)
        print(f'=== {name} ===')
        print(py_code)
        print()
    except Exception as e:
        print(f'{name}: ERROR: {e}')
        print()