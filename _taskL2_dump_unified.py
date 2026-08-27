# -*- coding: utf-8 -*-
"""临时诊断：用统一后端生成 try/catch 代码（_taskL2_ 前缀，收尾清理）。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', os.getcwd())
for p in [os.path.join(LIGHT_MERGE, 'src'), LIGHT_MERGE]:
    if p not in sys.path:
        sys.path.insert(0, p)
from light_parser_v3 import LightParser
from code_generator_unified import UnifiedCodeGenerator

src = open(sys.argv[1], encoding='utf-8').read()
p = LightParser()
module = p.parse(src)
g = UnifiedCodeGenerator()
print(g.generate(module))
