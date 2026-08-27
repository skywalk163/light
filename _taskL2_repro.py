# -*- coding: utf-8 -*-
"""临时诊断：完全复刻 lightharness 运行.py 的路径与调用，打印 traceback（_taskL2_ 前缀）。"""
import sys, io, os, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = r'G:\dswork\duan-light-merge\lightharness'
STDLIB = os.path.join(ROOT, 'stdlib')
SRC = os.path.join(ROOT, 'src')
LIGHT_MERGE = r'G:\dswork\duan-light-merge\light-merge-task-L2'
for p in [STDLIB, ROOT, SRC,
          os.path.join(LIGHT_MERGE, 'src'),
          os.path.join(LIGHT_MERGE, 'antlrparser'),
          LIGHT_MERGE]:
    if p not in sys.path:
        sys.path.insert(0, p)
try:
    import _light_import_hook
    _light_import_hook.install([STDLIB, ROOT, SRC])
except Exception as exc:
    print(f'警告: 钩子安装失败: {exc}')

import cli.light as cl
print('cli.light from:', cl.__file__)
print('code_generator from:', __import__('code_generator').__file__)

entry = os.path.join(ROOT, 'examples', 'test_L006.light')
src = open(entry, encoding='utf-8').read()
try:
    out = cl._run_src(src, file_path=entry)
    print('=== RUN OK ===')
    print(out)
except SystemExit as e:
    print('SystemExit rc =', e.code)
except Exception:
    traceback.print_exc()
