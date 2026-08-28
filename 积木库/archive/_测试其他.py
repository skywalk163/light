# -*- coding: utf-8 -*-
"""测试多个块"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from _预跑 import _parse_light_file, _try_compile_block, _sample_args, _is_subscript_usage

blocks = [
    r'D:\traework\light\积木库\blocks_v5\函数\函数互相关.light',
    r'D:\traework\light\积木库\blocks_v5\函数\函数卷积.light',
    r'D:\traework\light\积木库\blocks_v5\函数\函数过滤.light',
    r'D:\traework\light\积木库\blocks_v5\函数\柯里化.light',
    r'D:\traework\light\积木库\blocks_v5\密码\密钥强度.light',
    r'D:\traework\light\积木库\blocks_v5\密码\Argon2.light',
    r'D:\traework\light\积木库\blocks_v5\数据\对乘.light',
    r'D:\traework\light\积木库\blocks_v5\数据\数据归一化.light',
    r'D:\traework\light\积木库\blocks_v5\类型\文本转公约.light',
]

for fpath in blocks:
    name = os.path.basename(fpath)
    func_name, params, contract_input, contract_output, content, is_stub, callback_params, missing_vars = _parse_light_file(fpath)
    
    print(f'=== {name} ===')
    print(f'  params: {params}')
    print(f'  contract_input: {contract_input}')
    print(f'  callback_params: {callback_params}')
    print(f'  missing_vars: {missing_vars}')
    
    args = _sample_args(func_name, params, contract_input, callback_params, content)
    print(f'  args: {args}')
    
    # 检查下标检测
    for p in params:
        sub = _is_subscript_usage(content, p)
        if sub:
            print(f'  subscript: {p}')
    
    if is_stub:
        print(f'  SKIP (stub)')
        print()
        continue
    
    try:
        result = _try_compile_block(content, func_name, params, contract_input, callback_params, missing_vars)
        print(f'  OK: {result}')
    except Exception as e:
        print(f'  FAIL: {type(e).__name__}: {e}')
    print()