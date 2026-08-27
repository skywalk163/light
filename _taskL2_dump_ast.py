# -*- coding: utf-8 -*-
"""临时诊断：转储 .light 文件 AST（_taskL2_ 前缀，收尾清理）。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', os.getcwd())
sys.path.insert(0, os.path.join(LIGHT_MERGE, 'src'))
sys.path.insert(0, LIGHT_MERGE)
from light_parser_v3 import LightParser

path = sys.argv[1]
src = open(path, encoding='utf-8').read()
p = LightParser()
tree = p.parse(src)

def _fields(node):
    slots = getattr(type(node), '__slots__', None)
    if slots:
        for s in slots:
            if s.startswith('_'):
                continue
            yield s, getattr(node, s, None)

def _show(node, indent=0, seen=None):
    if seen is None:
        seen = set()
    if id(node) in seen:
        return
    seen.add(id(node))
    pref = '  ' * indent
    print(f"{pref}{type(node).__name__}")
    for k, v in _fields(node):
        if isinstance(v, list):
            print(f"{pref}  {k}: [")
            for item in v:
                if hasattr(type(item), '__slots__'):
                    _show(item, indent + 2, seen)
                else:
                    print(f"{'  ' * (indent + 2)}{item!r}")
            print(f"{pref}  ]")
        elif v is not None and hasattr(type(v), '__slots__'):
            print(f"{pref}  {k}:")
            _show(v, indent + 2, seen)
        elif v is not None:
            print(f"{pref}  {k}: {v!r}")

_show(tree)
