# -*- coding: utf-8 -*-
"""临时诊断：转储 .light 源码的 token 流（_taskL2_ 前缀）。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', os.getcwd())
sys.path.insert(0, os.path.join(LIGHT_MERGE, 'src'))
sys.path.insert(0, LIGHT_MERGE)
import lexer as lexer_mod

src = sys.argv[1]
from lexer import Lexer
toks = Lexer().tokenize(src)
for t in toks:
    print(type(t).__name__, repr(getattr(t, 'value', None)), getattr(t, 'type', None))
