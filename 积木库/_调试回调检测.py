# -*- coding: utf-8 -*-
"""调试回调参数检测逻辑"""
import re

content = open('blocks_v5/文件/大小GB.light', 'r', encoding='utf-8').read()
print('=== Content ===')
print(content)

# 测试 _is_callback_param
param = 'cb_文本'
pattern = re.compile(r'(?<![a-zA-Z_\u4e00-\u9fff])' + re.escape(param) + r'\s*\(')
match = pattern.search(content)
print(f'\n=== Regex match for {param} ===')
print(f'Match: {match}')
if match:
    print(f'Matched text: {match.group()}')

# 测试所有参数
from _预跑 import _is_callback_param, _parse_light_file, _sample_args, COMMON_MISSING_VARS

func_name, params, contract_input, contract_output, content, is_stub, callback_params, missing_vars = _parse_light_file('blocks_v5/文件/大小GB.light')
print(f'\n=== Parse result ===')
print(f'func_name: {func_name}')
print(f'params: {params}')
print(f'contract_input: {contract_input}')
print(f'callback_params: {callback_params}')
print(f'missing_vars: {missing_vars}')

# 测试 _sample_args
args = _sample_args(func_name, params, contract_input, callback_params, content)
print(f'\n=== Sample args ===')
for i, p in enumerate(params):
    print(f'  {p}: {args[i]}')