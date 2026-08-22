# -*- coding: utf-8 -*-
"""C3-3：原生腿能力边界表 ↔ 实现 的源码级守单点。

背景：第二轮的能力边界靠读源码猜；本轮把它变成可执行断言。`docs/原生腿能力边界.md`
是给 A3/B3 与后来者看的地图，本文件是它的哨兵——**读 `codegen_typed.py` 的
`_gen_statement` / `_gen_expression` 两条 isinstance 分派链，把实际分派的节点类型
与文档（本文件内嵌副本）比对**：

- 代码侧**加了**新节点、文档没更 → `实际 ⊄ 文档` 红（防腐烂）
- 代码侧**删了**旧节点、文档还吹 → `文档 ⊄ 实际` 红（防吹牛）

两句各一半，合成「实际 == 文档」的强咬合。改文档必须同改本文件内嵌清单，
否则必有一边红——这正是「判据表靠源码级断言守单点」的既定口径。

注意：
- `hasattr(ast, 'SelfAssignment') and isinstance(stmt, ast.SelfAssignment)` 这类
  写法里 `ast.SelfAssignment` 也会被正则抓到，属正常。
- `_gen_expression` 开头有剥 `ExpressionStatement` 外壳的分支，也算在表达式位
  支持的名单里（它把适配层伪装拆开转交）。
"""

import os
import re

import pytest

_CODE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'llvm', 'codegen_typed.py')
_DOC = os.path.join(
    os.path.dirname(__file__), '..', '..', 'docs', '原生腿能力边界.md')

# 文档承诺的已支持清单（与 docs/原生腿能力边界.md §1.1 / §2.1 一一对应）
_DOC_STMT_TYPES = frozenset({
    'VariableDeclaration', 'Assignment', 'SelfAssignment', 'CompoundAssignment',
    'IfStatement', 'ForeachStatement', 'WhileStatement', 'ReturnStatement',
    'BreakStatement', 'ContinueStatement', 'PrintStatement', 'TryStatement',
    'ThrowStatement', 'ExpressionStatement', 'ImportStatement', 'AsyncScope',
})

_DOC_EXPR_TYPES = frozenset({
    'NumberLiteral', 'StringLiteral', 'BooleanLiteral', 'NullLiteral',
    'Identifier', 'BinaryOp', 'UnaryOp', 'FunctionCall', 'ParagraphCall',
    'IndexAccess', 'ListLiteral', 'DictLiteral', 'StringInterpolation',
    'ConditionalExpression', 'PropertyAccess', 'ClassInstantiation',
    'NewExpression', 'AwaitExpression', 'ExpressionStatement',
})


def _源码() -> str:
    with open(_CODE, encoding='utf-8') as f:
        return f.read()


def _提取分派类型(method_src: str, obj_var: str) -> set:
    """从一段方法源码里抓 `isinstance(<obj_var>, ast.XXX)` 的类型名（去重）。

    只认链上自己的变量（语句链是 `stmt`，表达式链是 `expr`）——`_gen_statement`
    的 `ExpressionStatement` 分支里还有对 `expr` 的表达式级检查（拆伪装/变更方法），
    那属于表达式位，不能算进语句清单。
    """
    return set(re.findall(
        rf'isinstance\({obj_var}, ast\.([A-Za-z_]\w*)', method_src))


def _取方法体(src: str, name: str) -> str:
    i = src.find(f'def {name}(')
    assert i > 0, f'找不到 {name}'
    j = src.find('\n    def ', i + 10)
    return src[i:j if j > 0 else len(src)]


def test_语句分派链与文档清单一致():
    body = _取方法体(_源码(), '_gen_statement')
    实际 = _提取分派类型(body, 'stmt')
    assert 实际 <= _DOC_STMT_TYPES, \
        f'代码侧出现了文档没登记的语句节点: {sorted(实际 - _DOC_STMT_TYPES)}'
    assert _DOC_STMT_TYPES <= 实际, \
        f'文档承诺的语句节点在代码侧找不到: {sorted(_DOC_STMT_TYPES - 实际)}'


def test_表达式分派链与文档清单一致():
    body = _取方法体(_源码(), '_gen_expression')
    实际 = _提取分派类型(body, 'expr')
    assert 实际 <= _DOC_EXPR_TYPES, \
        f'代码侧出现了文档没登记的表达式节点: {sorted(实际 - _DOC_EXPR_TYPES)}'
    assert _DOC_EXPR_TYPES <= 实际, \
        f'文档承诺的表达式节点在代码侧找不到: {sorted(_DOC_EXPR_TYPES - 实际)}'


def test_文档存在且登记了清单():
    """文档不能被人删空或改成空壳。"""
    assert os.path.exists(_DOC), f'能力边界表文档不见了: {_DOC}'
    with open(_DOC, encoding='utf-8') as f:
        text = f.read()
    assert '原生腿能力边界表' in text, '文档标题丢了'
    for t in _DOC_STMT_TYPES | _DOC_EXPR_TYPES:
        assert t in text, f'文档里找不到节点 {t}（文档与内嵌清单漂移了）'


def test_兜底拒绝函数还在():
    """表达式层/语句层的两条链尾兜底函数不能被删——删了静默降级就复活。"""
    src = _源码()
    for fn in ('_reject_unsupported_expr', '_reject_unsupported_stmt',
               '_reject_unknown_call'):
        assert f'def {fn}(' in src, f'兜底函数 {fn} 不见了'
