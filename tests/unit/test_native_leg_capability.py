# -*- coding: utf-8 -*-
"""C3-3 + B7：原生腿能力边界表 <-> 实现 的源码级守单点。

背景：第二轮的能力边界靠读源码猜；本轮把它变成可执行断言。``docs/原生腿能力边界.md``
是给 A3/B3 与后来者看的地图，本文件是它的哨兵——**读 ``codegen_typed.py`` 的
``_gen_statement`` / ``_gen_expression`` 两条 isinstance 分派链，把实际分派的节点类型
与文档（本文件内嵌副本）比对**：

- 代码侧**加了**新节点、文档没更 -> ``实际 ⊄ 文档`` 红（防腐烂）
- 代码侧**删了**旧节点、文档还吹 -> ``文档 ⊄ 实际`` 红（防吹牛）

两句各一半，合成「实际 == 文档」的强咬合。改文档必须同改本文件内嵌清单，
否则必有一边红——这正是「判据表靠源码级断言守单点」的既定口径。

B7 升级（2026-08-24）：增加内置函数与运行时导出符号的双向反跑——
读取 ``docs/原生腿能力清单.json`` 机读数据，与 ``codegen_typed.py`` 实际分派链比对：

- 代码里**加了**新内置名、JSON 没登记 -> 红（防腐烂）
- JSON 里**写了**代码里没有的内置名 -> 红（防吹牛）
- 运行时符号同理双向咬合

注意：
- ``hasattr(ast, 'SelfAssignment') and isinstance(stmt, ast.SelfAssignment)`` 这类
  写法里 ``ast.SelfAssignment`` 也会被正则抓到，属正常。
- ``_gen_expression`` 开头有剥 ``ExpressionStatement`` 外壳的分支，也算在表达式位
  支持的名单里（它把适配层伪装拆开转交）。
"""

import json
import os
import re

import pytest

_CODE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'llvm', 'codegen_typed.py')
_DOC = os.path.join(
    os.path.dirname(__file__), '..', '..', 'docs', '原生腿能力边界.md')
_JSON = os.path.join(
    os.path.dirname(__file__), '..', '..', 'docs', '原生腿能力清单.json')
_RT = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'llvm', 'runtime_typed.c')

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
    'ListComprehension',  # A9-S2 新增
})


def _源码() -> str:
    with open(_CODE, encoding='utf-8') as f:
        return f.read()


def _runtime源码() -> str:
    with open(_RT, encoding='utf-8') as f:
        return f.read()


def _提取分派类型(method_src: str, obj_var: str) -> set:
    """从一段方法源码里抓 ``isinstance(<obj_var>, ast.XXX)`` 的类型名（去重）。

    只认链上自己的变量（语句链是 ``stmt``，表达式链是 ``expr``）——``_gen_statement``
    的 ``ExpressionStatement`` 分支里还有对 ``expr`` 的表达式级检查（拆伪装/变更方法），
    那属于表达式位，不能算进语句清单。
    """
    return set(re.findall(
        rf'isinstance\({obj_var}, ast\.([A-Za-z_]\w*)', method_src))


def _取方法体(src: str, name: str) -> str:
    i = src.find(f'def {name}(')
    assert i > 0, f'找不到 {name}'
    j = src.find('\n    def ', i + 10)
    return src[i:j if j > 0 else len(src)]


def _方法行区间(src: str, name: str):
    """返回方法体的 (首行号, 末行号)，1-based 闭区间。"""
    i = src.find(f'def {name}(')
    assert i > 0, f'找不到 {name}'
    j = src.find('\n    def ', i + 10)
    起 = src[:i].count('\n') + 1
    止 = (src[:j].count('\n') + 1) if j > 0 else src.count('\n') + 1
    return 起, 止


def _提取内置名(method_src: str) -> set:
    """从 _gen_typed_builtin 方法体里提取所有注册的内置函数名（含中英文别名）。"""
    names = set()
    for m in re.finditer(r"if name in \(([^)]+)\)", method_src):
        names.update(re.findall(r"'([^']+)'", m.group(1)))
    # TLS dict entries: ('中文名', '英文名'): 'c_func'
    for m in re.finditer(r"\('([^']+)',\s*'([^']+)'\):\s*'([^']+)'", method_src):
        names.add(m.group(1))
        names.add(m.group(2))
    return names


def _提取运行时符号(src: str) -> set:
    """从 codegen_typed.py 提取 'declare ... @symbol(' 声明的运行时符号名。"""
    return set(re.findall(r"'declare\s+\S+\s+@(\w+)\s*\(", src))


def _加载清单() -> dict:
    """加载 docs/原生腿能力清单.json 机读数据。"""
    assert os.path.exists(_JSON), f'能力清单 JSON 不见了: {_JSON}'
    with open(_JSON, encoding='utf-8') as f:
        return json.load(f)


# ── 语句层 ──────────────────────────────────────────────

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


def test_语句节点清单与JSON一致():
    """JSON 能力清单的 statement_nodes 必须与代码实际分派链一致。"""
    data = _加载清单()
    json_names = frozenset(
        e['name'] for e in data['tables']['statement_nodes']['entries']
        if e.get('supported', True))
    实际 = _提取分派类型(_取方法体(_源码(), '_gen_statement'), 'stmt')
    assert 实际 == json_names, \
        f'JSON 清单与代码实际不一致:\n  代码有但 JSON 没有: {sorted(实际 - json_names)}\n' \
        f'  JSON 有但代码没有: {sorted(json_names - 实际)}'


def test_表达式节点清单与JSON一致():
    """JSON 能力清单的 expression_nodes 必须与代码实际分派链一致。"""
    data = _加载清单()
    json_names = frozenset(
        e['name'] for e in data['tables']['expression_nodes']['entries']
        if e.get('supported', True))
    实际 = _提取分派类型(_取方法体(_源码(), '_gen_expression'), 'expr')
    assert 实际 == json_names, \
        f'JSON 清单与代码实际不一致:\n  代码有但 JSON 没有: {sorted(实际 - json_names)}\n' \
        f'  JSON 有但代码没有: {sorted(json_names - 实际)}'


# ── 内置函数层（B7 新增） ──────────────────────────────────

def test_内置函数清单与代码一致():
    """JSON 能力清单的 builtin_functions 必须与 _gen_typed_builtin 实际注册名一致。

    双向反跑：
    - 代码里加了新内置名、JSON 没登记 -> 红（防腐烂）
    - JSON 里写了代码里没有的内置名 -> 红（防吹牛）
    """
    data = _加载清单()
    json_names = frozenset(
        e['name'] for e in data['tables']['builtin_functions']['entries'])
    实际 = _提取内置名(_取方法体(_源码(), '_gen_typed_builtin'))
    assert 实际 == json_names, \
        f'内置函数清单与代码不一致:\n' \
        f'  代码有但 JSON 没有: {sorted(实际 - json_names)}\n' \
        f'  JSON 有但代码没有: {sorted(json_names - 实际)}'


def test_内置函数证据行号可定位():
    """JSON 清单里每条 builtin 的 evidence 行号必须**真指到注册它的那一行**。

    两条判据（都可反跑）：
    1. 行号落在 `_gen_typed_builtin` 方法体的行区间内 —— 挡「行号随手填个数」；
    2. 那一行的文本里出现该内置名 —— 挡「行号在区间内但指错行」。

    合并期收紧：B7 原稿只断「1 <= 行号 <= 文件总行数」并把真判据注释掉
    （「放宽：只要行号在合理范围内即可」）。codegen_typed.py 四千行，任何
    数字都过，那条判据等于不存在——正是「上界断言」这一假绿形态。
    """
    data = _加载清单()
    src = _源码()
    src_lines = src.splitlines()
    起, 止 = _方法行区间(src, '_gen_typed_builtin')
    errors = []
    for e in data['tables']['builtin_functions']['entries']:
        ev = e.get('evidence', '')
        m = re.search(r'codegen_typed\.py:(\d+)', ev)
        if not m:
            errors.append(f"{e['name']}: evidence 格式不对: {ev}")
            continue
        lineno = int(m.group(1))
        if not (起 <= lineno <= 止):
            errors.append(
                f"{e['name']}: 行号 {lineno} 在 _gen_typed_builtin "
                f"区间 [{起}, {止}] 之外")
            continue
        if e['name'] not in src_lines[lineno - 1]:
            errors.append(
                f"{e['name']}: codegen_typed.py:{lineno} 那一行没有这个名字："
                f"{src_lines[lineno - 1].strip()[:60]}")
    assert not errors, '内置函数证据行号问题:\n' + '\n'.join(errors)


# ── 运行时导出符号层（B7 新增） ────────────────────────────

def test_运行时符号清单与代码一致():
    """JSON 能力清单的 runtime_symbols 必须与 codegen_typed.py 声明的符号一致。

    双向反跑：
    - 代码里加了新符号、JSON 没登记 -> 红
    - JSON 里写了代码里没有的符号 -> 红
    """
    data = _加载清单()
    json_names = frozenset(
        e['name'] for e in data['tables']['runtime_symbols']['entries'])
    实际 = _提取运行时符号(_源码())
    assert 实际 == json_names, \
        f'运行时符号清单与代码不一致:\n' \
        f'  代码有但 JSON 没有: {sorted(实际 - json_names)}\n' \
        f'  JSON 有但代码没有: {sorted(json_names - 实际)}'


def test_运行时符号在runtime有定义():
    """JSON 清单里每条 runtime_symbol 的 runtime_typed.c 定义行号必须可定位。

    C 库函数（setjmp/_setjmp）不在此列——它们不是 runtime_typed.c 定义的。
    """
    data = _加载清单()
    rt_src = _runtime源码()
    errors = []
    for e in data['tables']['runtime_symbols']['entries']:
        ev = e.get('evidence_define', '')
        # C library symbols are exempt
        if 'C library' in ev:
            continue
        m = re.search(r'runtime_typed\.c:(\d+)', ev)
        if not m:
            errors.append(f"{e['name']}: evidence_define 格式不对: {ev}")
            continue
        lineno = int(m.group(1))
        if lineno < 1:
            errors.append(f"{e['name']}: 行号越界 {lineno}")
            continue
        # 粗检：该行附近能找到符号名
        rt_lines = rt_src.splitlines()
        window = '\n'.join(rt_lines[max(0, lineno-2):lineno+2])
        if e['name'] not in window:
            errors.append(f"{e['name']}: 在 runtime_typed.c:{lineno} 附近找不到符号名")
    assert not errors, '运行时符号定义定位问题:\n' + '\n'.join(errors)


# ── 文档与兜底 ──────────────────────────────────────────

def test_文档存在且登记了清单():
    """文档不能被人删空或改成空壳。"""
    assert os.path.exists(_DOC), f'能力边界表文档不见了: {_DOC}'
    with open(_DOC, encoding='utf-8') as f:
        text = f.read()
    assert '原生腿能力边界表' in text, '文档标题丢了'
    for t in _DOC_STMT_TYPES | _DOC_EXPR_TYPES:
        assert t in text, f'文档里找不到节点 {t}（文档与内嵌清单漂移了）'
    # B7: 文档必须登记了网络层
    for kw in ('socket', 'poller', '事件循环', 'TLS'):
        assert kw in text, f'文档里找不到网络层关键词 {kw}（B7 补登缺失）'


def test_JSON清单存在且结构完整():
    """JSON 能力清单必须存在且包含四张表。"""
    data = _加载清单()
    assert data['schema_version'] == '1.0', f'schema_version 不对: {data["schema_version"]}'
    # baseline_commit 只断「在册且是个短 SHA」，不写死具体值：写死 HEAD 的 SHA
    # 是第五轮已裁决过的坑（commit 1ff86237「总纲不再写死 HEAD 的 SHA」），
    # 一旦合并/改基线就得改测试，改测试的人只会把断言删掉。
    assert re.fullmatch(r'[0-9a-f]{7,40}', data.get('baseline_commit', '')), \
        f'baseline_commit 不是短 SHA: {data.get("baseline_commit")!r}'
    for table_name in ('statement_nodes', 'expression_nodes',
                       'builtin_functions', 'runtime_symbols'):
        assert table_name in data['tables'], f'JSON 缺少表: {table_name}'
        assert 'entries' in data['tables'][table_name], f'{table_name} 缺 entries'
        assert 'count' in data['tables'][table_name], f'{table_name} 缺 count'
        actual_count = len(data['tables'][table_name]['entries'])
        declared_count = data['tables'][table_name]['count']
        assert actual_count == declared_count, \
            f'{table_name}: count={declared_count} 但实际 entries={actual_count}'
    # B7: 必须有平台裁决记录
    assert 'platform_notes' in data, 'JSON 缺 platform_notes'
    assert 'TLS' in data['platform_notes'], 'JSON 缺 TLS 平台裁决'
    assert 'posix_ruling' in data['platform_notes']['TLS'], 'JSON 缺 POSIX TLS 裁决'


def test_兜底拒绝函数还在():
    """表达式层/语句层的两条链尾兜底函数不能被删——删了静默降级就复活。"""
    src = _源码()
    for fn in ('_reject_unsupported_expr', '_reject_unsupported_stmt',
               '_reject_unknown_call'):
        assert f'def {fn}(' in src, f'兜底函数 {fn} 不见了'
