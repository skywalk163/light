# -*- coding: utf-8 -*-
"""测试密码领域积木，显示具体错误信息"""
import os, sys, traceback, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser, ParseError
from code_generator import PythonCodeGenerator

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCKS_DIR = os.path.join(HERE, 'blocks_v5', '密码')

# 读取所有非自递归桩的密码积木
files = sorted(os.listdir(BLOCKS_DIR))
for f in files:
    if not f.endswith('.light'):
        continue
    fpath = os.path.join(BLOCKS_DIR, f)
    with open(fpath, 'r', encoding='utf-8') as fh:
        source = fh.read()
    
    # 跳过自递归桩
    lines = source.strip().split('\n')
    last_line = lines[-1].strip() if lines else ''
    func_name = f.replace('.light', '')
    if last_line == f'返回 {func_name}(输入)' or last_line == f'返回 {func_name}(输入)':
        continue
    
    print(f'\n{"="*60}')
    print(f'文件: {f}')
    print(f'源码: {source.strip()}')
    
    # 解析
    try:
        parser = LightParser()
        ast = parser.parse(source)
        print(f'解析: OK')
        
        # 生成代码
        try:
            gen = PythonCodeGenerator()
            py_code = gen.generate(ast)
            print(f'生成: OK')
            print(f'代码: {py_code.strip()[:200]}')
        except Exception as e:
            print(f'生成错误: {e}')
            traceback.print_exc(limit=3)
            
    except ParseError as e:
        print(f'解析错误: {e}')
    except Exception as e:
        print(f'其他错误: {e}')
        traceback.print_exc(limit=3)