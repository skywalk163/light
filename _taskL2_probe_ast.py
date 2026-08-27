# -*- coding: utf-8 -*-
"""临时诊断：解析最小片段并打印全部 AST 节点类（适配 __slots__）。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', os.getcwd())
sys.path.insert(0, os.path.join(LIGHT_MERGE, 'src'))
sys.path.insert(0, LIGHT_MERGE)
from light_parser_v3 import LightParser

src = sys.argv[1]
p = LightParser()
tree = p.parse(src)
if hasattr(tree, 'statements'):
    tree = tree.statements

def _fields(node):
    slots = getattr(type(node), '__slots__', None)
    if slots:
        for s in slots:
            if s.startswith('_'):
                continue
            yield s, getattr(node, s, None)
    elif hasattr(node, '__dict__'):
        for k, v in vars(node).items():
            if k.startswith('_'):
                continue
            yield k, v

def walk(node, depth=0):
    if node is None:
        print('  ' * depth + 'None')
        return
    if isinstance(node, list):
        print('  ' * depth + '[list]')
        for x in node:
            walk(x, depth + 1)
        return
    if not hasattr(type(node), '__slots__') and not hasattr(node, '__dict__'):
        print('  ' * depth + repr(node))
        return
    name = type(node).__name__
    extra = ''
    for k in ('name', 'member', 'obj', 'callee', 'is_method_call', 'index'):
        try:
            v = getattr(node, k, None)
        except Exception:
            v = None
        if isinstance(v, (str, int, bool)):
            extra += f" {k}={v!r}"
    print('  ' * depth + name + extra)
    for k, v in _fields(node):
        walk(v, depth + 1)

walk(tree)
