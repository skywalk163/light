# -*- coding: utf-8 -*-
"""测试单个体育块"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 直接测试 _try_compile_block
from _预跑 import _parse_light_file, _try_compile_block, _create_light_namespace

fpath = r'D:\traework\light\积木库\blocks_v5\体育\三分命中率.light'
func_name, params, contract_input, contract_output, content, is_stub, callback_params, missing_vars = _parse_light_file(fpath)

print(f'func_name: {func_name}')
print(f'params: {params}')
print(f'contract_input: {contract_input}')
print(f'callback_params: {callback_params}')
print(f'missing_vars: {missing_vars}')

from _预跑 import _sample_args
args = _sample_args(func_name, params, contract_input, callback_params, content)
print(f'args: {args}')

try:
    result = _try_compile_block(content, func_name, params, contract_input, callback_params, missing_vars)
    print(f'result: {result}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()