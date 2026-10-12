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

R141-B 升级（2026-10-12）：evidence 定位从「硬编码行号」改为**稳定锚点**。
旧判据按行号校验（行号落在方法区间内 + 该行文本含名字），codegen 每加一行、
462 条 evidence 行号全体漂移，忘记重生成就整片假红——实测头部插 50 行、
``test_内置函数证据行号可定位`` 462 条全红，而能力分文未变。现在 builtin 的
evidence 锚到 ``_gen_typed_builtin`` 方法名、runtime 的 evidence_define 锚到
``runtime_typed.c:<符号名>``，行号只存在于 ``*_line`` 附加信息字段、**不参与判据**
（对「真漂移」仍敏感：名字不存在/锚点方法不存在/定义签名不存在，照红）。

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

_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.abspath(os.path.join(
    _HERE, '..', '..', 'src', 'llvm', 'codegen_typed.py'))
_DOC = os.path.abspath(os.path.join(
    _HERE, '..', '..', 'docs', '原生腿能力边界.md'))
_JSON = os.path.abspath(os.path.join(
    _HERE, '..', '..', 'docs', '原生腿能力清单.json'))
_RT = os.path.abspath(os.path.join(
    _HERE, '..', '..', 'src', 'llvm', 'runtime_typed.c'))

# 文档承诺的已支持清单（与 docs/原生腿能力边界.md §1.1 / §2.1 一一对应）
_DOC_STMT_TYPES = frozenset({
    'VariableDeclaration', 'Assignment', 'SelfAssignment', 'CompoundAssignment',
    'IfStatement', 'ForeachStatement', 'WhileStatement', 'ReturnStatement',
    'BreakStatement', 'ContinueStatement', 'PrintStatement', 'TryStatement',
    'ThrowStatement',     'ExpressionStatement', 'ImportStatement', 'AsyncScope',
    'YieldStatement',  # R10-11b 第四批B 新增：生成器
    'ScopeDeclaration',  # R114-S1 新增：`全局 X。` 作用域声明
    'MatchStatement',          # R115-A 新增：`匹配 X：情况 …：`（字面量模式 + 通配）
    'DestructuringAssignment',  # R115-A 新增：`设 [甲, 乙] 为 …` 按位置解包
    'AssertStmt',               # R116-A 新增：`断言 <条件>。` / `断言 <条件>, <消息>。`
    'WithStatement',            # R116-A 新增：`使用 X 为 Y：` 上下文管理（__enter__/__exit__ + 异常安全退出）
    'RunAsyncStmt',             # R119-A 新增：`异步 运行 X()。` 顶层启动异步段（协程调度器驱动至完成）
    'SegmentDefinition',        # R130-A 新增：`段落` 嵌套定义（定义 no-op；段名在值位/调用位
                                # 经 _lookup_nested_seg 解析，闭包捕获外层自由变量）
})

_DOC_EXPR_TYPES = frozenset({
    'NumberLiteral', 'StringLiteral', 'BooleanLiteral', 'NullLiteral',
    'Identifier', 'BinaryOp', 'UnaryOp', 'FunctionCall', 'ParagraphCall',
    'IndexAccess', 'ListLiteral', 'DictLiteral', 'StringInterpolation',
    'ConditionalExpression', 'PropertyAccess', 'ClassInstantiation',
    'NewExpression', 'AwaitExpression', 'ExpressionStatement',
    'ListComprehension',  # A9-S2 新增
    'TupleLiteral',       # R10-11a 新增
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


def _方法体或空(src: str, name: str):
    """方法体源码；方法不存在返回 None（供锚点判据报「锚点方法不见了」）。"""
    i = src.find(f'def {name}(')
    if i <= 0:
        return None
    j = src.find('\n    def ', i + 10)
    return src[i:j if j > 0 else len(src)]


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


def test_内置函数证据锚点可定位():
    """JSON 清单里每条 builtin 的 evidence 必须锚到 _gen_typed_builtin 方法体内真注册的名字。

    R141-B：锚点判据（替代原行号判据，抗代码行漂移）：
    1. evidence 形如 ``src/llvm/codegen_typed.py:<方法名>``，且该方法在源码里存在
       —— 挡「锚点方法名随手填/方法被改名」；
    2. 该内置名以 ``'名字'`` 形式出现在该方法体内 —— 挡「JSON 登记了代码里
       没有的名字」（防吹牛）与「名字在该方法里根本找不到」。

    行号只作附加信息（``evidence_line`` 字段），**不参与判据**。旧判据按行号校验，
    codegen 头部插 50 行即 462 条全体假红（R141 实测），而那是行号噪声、能力分文未变。
    """
    data = _加载清单()
    src = _源码()
    方法体缓存 = {}
    errors = []
    for e in data['tables']['builtin_functions']['entries']:
        ev = e.get('evidence', '')
        m = re.fullmatch(r'src/llvm/codegen_typed\.py:(\w+)', ev)
        if not m:
            errors.append(f"{e['name']}: evidence 不是 `文件:方法` 锚点格式: {ev}")
            continue
        方法 = m.group(1)
        if 方法 not in 方法体缓存:
            方法体缓存[方法] = _方法体或空(src, 方法)
        body = 方法体缓存[方法]
        if body is None:
            errors.append(f"{e['name']}: 锚点方法 {方法} 在 codegen_typed.py 里不存在")
            continue
        if f"'{e['name']}'" not in body:
            errors.append(
                f"{e['name']}: 锚点方法 {方法} 的方法体里找不到该内置名的注册")
    assert not errors, '内置函数证据锚点问题:\n' + '\n'.join(errors)


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


def test_运行时符号证据锚点可定位():
    """runtime_symbols 的两条 evidence 必须锚到真实位置（R141-B：不再按行号判）。

    - ``evidence_declare``：文件锚点 ``src/llvm/codegen_typed.py``——该符号必须真以
      ``'declare ... @符号('`` 形式声明在 codegen_typed.py 里（declare 散落在
      _declare_typed_runtime 与少数 C 库声明处，精确指针是条目名本身）；
    - ``evidence_define``：定义锚点 ``src/llvm/runtime_typed.c:<符号>``——该符号必须
      真有函数定义（``<返回类型> <符号>(`` 签名行）；C 库函数豁免（标 C library）。

    行号（``evidence_declare_line`` / ``evidence_define_line``）只是附加信息，
    不参与判据：runtime_typed.c 每加一行、旧判据的 ±1 窗口就整体漂移假红。
    """
    data = _加载清单()
    cg_src = _源码()
    rt_src = _runtime源码()
    declared = _提取运行时符号(cg_src)
    rt_lines = rt_src.splitlines()
    errors = []
    for e in data['tables']['runtime_symbols']['entries']:
        name = e['name']
        ev_declare = e.get('evidence_declare', '')
        if ev_declare != 'src/llvm/codegen_typed.py':
            errors.append(f"{name}: evidence_declare 不是文件锚点: {ev_declare}")
        elif name not in declared:
            errors.append(f"{name}: codegen_typed.py 里没有它的 declare 声明")
        ev_define = e.get('evidence_define', '')
        if 'C library' in ev_define:
            continue
        m = re.fullmatch(r'src/llvm/runtime_typed\.c:(\w+)', ev_define)
        if not m or m.group(1) != name:
            errors.append(f"{name}: evidence_define 不是 `文件:符号名` 锚点: {ev_define}")
            continue
        pattern = re.compile(rf'^(?:[\w\s\*]+)\s+{re.escape(name)}\s*\(')
        if not any(pattern.match(l.rstrip()) for l in rt_lines):
            errors.append(f"{name}: runtime_typed.c 里找不到它的函数定义（签名行）")
    assert not errors, '运行时符号证据锚点问题:\n' + '\n'.join(errors)


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
    assert data['schema_version'] == '1.1', f'schema_version 不对: {data["schema_version"]}（R141-B 锚点化为 1.1）'
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
