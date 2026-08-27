# -*- coding: utf-8 -*-
"""临时诊断：编译 .light → 生成代码 → exec 运行（_taskL2_ 前缀，收尾清理）。"""
import sys, io, os, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', os.getcwd())
sys.path.insert(0, os.path.join(LIGHT_MERGE, 'src'))
sys.path.insert(0, LIGHT_MERGE)
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

path = sys.argv[1]
src = open(path, encoding='utf-8').read()
p = LightParser(); g = PythonCodeGenerator()
tree = p.parse(src)
code = g.generate(tree)
ns = {'__name__': '__main__'}
try:
    exec(compile(code, '<gen>', 'exec'), ns)
    print('=== EXEC OK ===')
except Exception:
    traceback.print_exc()
    print('=== EXEC FAILED ===')
