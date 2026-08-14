# -*- coding: utf-8 -*-
"""分析成对乘的AST结构"""
import sys, os
sys.path.insert(0, os.path.join('..', 'src'))
sys.path.insert(0, '..')

with open('blocks_v5/数据/成对乘.light', 'r', encoding='utf-8') as f:
    content = f.read()

from light_parser_v3 import LightParser
parser = LightParser()
module = parser.parse(content)

for stmt in module.statements:
    if type(stmt).__name__ == 'Paragraph':
        for b in stmt.body:
            bt = type(b).__name__
            if bt == 'WhileStmt':
                for tb in b.body:
                    tbt = type(tb).__name__
                    if tbt == 'MemberAccess':
                        ma = tb  # tb itself is the MemberAccess
                        print('MemberAccess obj:', type(ma.obj).__name__)
                        if hasattr(ma.obj, 'name'):
                            print('  obj name:', ma.obj.name)
                        print('MemberAccess member:', ma.member)
                        print('MemberAccess args:', [type(a).__name__ for a in ma.args])
                        for i, a in enumerate(ma.args):
                            print('  Arg %d:' % i, type(a).__name__)
                            if hasattr(a, 'name'):
                                print('    name:', a.name)
                            if hasattr(a, 'left'):
                                print('    left:', type(a.left).__name__)
                                if hasattr(a.left, 'name'):
                                    print('      left name:', a.left.name)
                                if hasattr(a.left, 'obj'):
                                    print('      left obj:', type(a.left.obj).__name__)
                                    if hasattr(a.left.obj, 'name'):
                                        print('        left obj name:', a.left.obj.name)
                                if hasattr(a.left, 'index'):
                                    print('      left index:', type(a.left.index).__name__)
                                    if hasattr(a.left.index, 'name'):
                                        print('        left index name:', a.left.index.name)
                            if hasattr(a, 'right'):
                                print('    right:', type(a.right).__name__)
                                if hasattr(a.right, 'name'):
                                    print('      right name:', a.right.name)
                                if hasattr(a.right, 'left'):
                                    print('      right left:', type(a.right.left).__name__)
                                    if hasattr(a.right.left, 'name'):
                                        print('        right left name:', a.right.left.name)
                                if hasattr(a.right, 'right'):
                                    print('      right right:', type(a.right.right).__name__)
                                    if hasattr(a.right.right, 'name'):
                                        print('        right right name:', a.right.right.name)
                                if hasattr(a.right, 'obj'):
                                    print('      right obj:', type(a.right.obj).__name__)
                                    if hasattr(a.right.obj, 'name'):
                                        print('        right obj name:', a.right.obj.name)
                                if hasattr(a.right, 'index'):
                                    print('      right index:', type(a.right.index).__name__)
                                    if hasattr(a.right.index, 'name'):
                                        print('        right index name:', a.right.index.name)