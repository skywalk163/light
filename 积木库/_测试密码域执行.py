# -*- coding: utf-8 -*-
"""测试密码领域积木的执行，显示具体错误信息"""
import os, sys, traceback, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCKS_DIR = os.path.join(HERE, 'blocks_v5', '密码')

# 复用 _预跑.py 中的函数
sys.path.insert(0, HERE)
from _预跑 import _try_compile_block, _is_callback_param, _sample_args, _find_missing_vars, _create_light_namespace, COMMON_MISSING_VARS

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
    if last_line == f'返回 {func_name}(输入)':
        continue
    
    print(f'\n{"="*60}')
    print(f'文件: {f}')
    
    # 解析契约
    import re
    contract_match = re.search(r'# 契约：输入 \[([^\]]*)\] → 输出 (\S+)', source)
    contract_input = contract_match.group(1).split(', ') if contract_match else []
    contract_output = contract_match.group(2) if contract_match else ''
    
    # 获取参数名
    params = []
    for line in lines:
        if line.startswith('段落 ') and '接收' in line:
            parts = line.split('接收')
            if len(parts) > 1:
                param_str = parts[1].strip().rstrip(':')
                params = [p.strip() for p in param_str.split(',')]
            break
    
    # 检测回调参数
    callback_params = [p for p in params if _is_callback_param(source, p)]
    
    # 检测缺失变量
    missing_vars = _find_missing_vars(source, params)
    
    print(f'  参数: {params}')
    print(f'  回调: {callback_params}')
    print(f'  缺失变量: {missing_vars[:10]}{"..." if len(missing_vars) > 10 else ""}')
    
    try:
        result = _try_compile_block(source, func_name, params, contract_input, callback_params, missing_vars)
        print(f'  结果: ✅ {result}')
    except Exception as e:
        print(f'  错误: ❌ {type(e).__name__}: {e}')
        traceback.print_exc(limit=3)