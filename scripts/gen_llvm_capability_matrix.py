#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成原生（LLVM）后端**能力矩阵**：`docs/llvm_backend_capability_matrix.{md,json}`。

与既有的 `docs/原生腿能力清单.json` 分工不同：那份只登记「已支持」的东西（一条
单向清单），本矩阵要回答的是「**全部**语句类型里，哪些支持、哪些是缺口、缺口卡在
哪一层」——三层证据，逐条实测，缺口不许整片写成一句「覆盖有限」。

三层漏点（链条断在哪一层，就报哪一层，不许只报末端）：
  L1 适配层转换器   `compiler.AstAdapter._node_converters` 有没有这个 v3 节点的转换器
                    （没有 → 被包成 `<unknown:XXX>` 伪装标识符，后端永远认不出）
  L2 语句流白名单   `compiler.AstAdapter._to_list_stmts` 的白名单里有没有 legacy 落点
                    （没有 → 语句被包成 ExpressionStatement，分派链匹配不到。
                     R10-11b `生成`、R114-S1 `全局` 两次踩的都是这一层）
  L3 后端分派       `codegen_typed._gen_statement` 的 isinstance 链有没有分支

外加一列**实测**：拿一条最小源码真跑 `compile_source_typed`（能编 / 明确拒绝 /
编不过），防止「三层都有但产物是错的」这种最坏情况。

用法：
    python scripts/gen_llvm_capability_matrix.py            # 重生成 md + json
    python scripts/gen_llvm_capability_matrix.py --check     # 只比对，不写文件（门禁用）

门禁在 `tests/unit/test_llvm_capability_matrix.py`：矩阵与代码双向咬合——代码加了
支持而矩阵没更新会红，矩阵写了 supported 而代码其实不支持也会红。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'src')
V3 = os.path.join(SRC, 'ast_nodes_v3.py')
ADAPTER = os.path.join(SRC, 'compiler.py')
CODEGEN = os.path.join(SRC, 'llvm', 'codegen_typed.py')
OUT_MD = os.path.join(BASE, 'docs', 'llvm_backend_capability_matrix.md')
OUT_JSON = os.path.join(BASE, 'docs', 'llvm_backend_capability_matrix.json')

sys.path.insert(0, SRC)
sys.path.insert(0, BASE)


# ----------------------------------------------------------------------
# 语句类清单：v3 侧「作为语句出现」的节点
#   自动部分 = 类名以 Stmt / Statement / Decl 结尾
#   手工部分 = 命名不带后缀的语句类（漏了它们矩阵就不完整，脚本末尾会自检提醒）
# ----------------------------------------------------------------------

EXTRA_STMT_CLASSES = {
    'Assignment', 'CompoundAssignment', 'SelfAssignment',
    'IndexedAssignment', 'IndexedCompoundAssignment', 'DestructuringAssignment',
    'SegmentDefinition', 'ClassDefinition', 'InterfaceDefinition',
    'AsyncScope', 'DecoratorDefinition', 'TypeAlias',
}

# 不走 `_gen_statement` 分派、而由**上游路径**处理的 legacy 节点：
# 段落/类/接口/方法定义由 `_collect_*` + 各自的生成阶段处理，导出由
# `_gen_exported_aliases` 处理，导入由 `_process_imports` 处理。
# 把它们算成「gap:codegen」是冤枉——分派链没有分支不等于不支持。
UPSTREAM_PATH = {
    'SegmentDefinition', 'ClassDefinition', 'InterfaceDefinition',
    'MethodDefinition', 'ExportStatement', 'ImportStatement',
}

# 每条语句的最小实测源码；写不出来（语法/依赖不具备）的记 None，实测列标「—」。
# 这些用例是**能编过就行**的最小片段，不追求语义覆盖——语义由各模块的专项测试盯。
PROBE_CASES = {
    'VarDecl': '设 甲 为 1。\n打印 甲。\n',
    'Assignment': '设 甲 为 1。\n甲 为 2。\n打印 甲。\n',
    'CompoundAssignment': '设 甲 为 1。\n甲 加 2。\n打印 甲。\n',
    'IfStmt': '设 甲 为 1。\n如果 甲 等于 1：\n  打印 "对"。\n',
    'WhileStmt': '设 i 为 0。\n当 i < 3：\n  设 i 为 i 加 1。\n打印 i。\n',
    'ForeachStmt': '遍历 甲 于 列(1, 2)：\n  打印 甲。\n',
    'ReturnStmt': '段落 甲()：\n  返回 3。\n打印 甲()。\n',
    'BreakStmt': '设 i 为 0。\n当 i < 3：\n  跳出。\n',
    'ContinueStmt': '设 i 为 0。\n当 i < 3：\n  继续。\n',
    'TryStmt': '尝试：\n  设 甲 为 1。\n捕获 乙：\n  打印 乙。\n',
    'ThrowStmt': '抛出 "x"。\n',
    'AssertStmt': '断言 1 等于 1。\n',
    'ExportStmt': '设 甲 为 1。\n导出 甲。\n',
    'YieldStmt': ('段落 甲(n)：\n'
                  '  设 i 为 0\n'
                  '  当 i < n：\n'
                  '    生成 i\n'
                  '    设 i 为 i + 1\n'
                  '遍历 x 之 甲(3)：\n'
                  '  打印 x。\n'),
    'ScopeDeclStmt': ('段落 加一()：\n'
                      '  全局 计数。\n'
                      '  设 计数 为 计数 加 1。\n'
                      '加一()。\n'
                      '打印 计数。\n'),
    # 以下写不出可靠的单模块最小用例（语法未通 / 需外部依赖 / 异步），实测标「—」
    'ImportStmt': None,          # 模块级导入走 compile_light_project，单模块直编不具备
    'MatchStmt': None,           # v3 解析器层面就没通
    'WithStmt': None,
    'ParallelBlockStmt': None,
    'RunAsyncStmt': None,
    'TypeCheckToggleStmt': None,
    'PassStmt': None,
    'FFIFunctionDecl': None,
    'FFIVarArgsDecl': None,
    'SegmentDefinition': None,   # 段落定义本身由分派链上游处理，不作为体内语句实测
    # 类实例化要写 `新建 甲()`：只写 `甲()` 原生腿会当成未定义段落（实测过）
    'ClassDefinition': ('类 甲：\n'
                        '  属性 乙。\n'
                        '  构造：\n'
                        '    己乙 为 1。\n'
                        '设 己 为 新建 甲()。\n'
                        '打印 己.乙。\n'),
    'InterfaceDefinition': None,
    'MethodDefinition': None,
    'DecoratorDefinition': None,
    'TypeAlias': None,
    'AsyncScope': None,
    'SelfAssignment': None,
    'IndexedAssignment': None,
    'IndexedCompoundAssignment': None,
    'DestructuringAssignment': None,
}

# 光明源码里的写法（给人看的那一列）
SURFACE = {
    'VarDecl': '设 X 为 值。',
    'Assignment': 'X 为 值。',
    'CompoundAssignment': 'X 加 值。',
    'SelfAssignment': '己.X 为 值',
    'IndexedAssignment': 'X[0] 为 值',
    'IndexedCompoundAssignment': 'X[0] 加 值',
    'DestructuringAssignment': '设 [a, b] 为 X',
    'IfStmt': '如果 …：',
    'WhileStmt': '当 …：',
    'ForeachStmt': '遍历 X 于 …：',
    'ReturnStmt': '返回 …',
    'BreakStmt': '跳出',
    'ContinueStmt': '继续',
    'ImportStmt': '从 M 导入 …',
    'ExportStmt': '导出 …',
    'TryStmt': '尝试 / 捕获',
    'ThrowStmt': '抛出 …',
    'AssertStmt': '断言 …',
    'PassStmt': 'pass（空语句）',
    'YieldStmt': '生成 …',
    'ScopeDeclStmt': '全局 X。/ 外层 X。',
    'MatchStmt': '匹配 …',
    'WithStmt': '随 … 作为 X：',
    'ParallelBlockStmt': '并行 { … }',
    'RunAsyncStmt': '异步 运行 主()。',
    'TypeCheckToggleStmt': '类型检查开关',
    'FFIFunctionDecl': '外部函数声明',
    'FFIVarArgsDecl': '可变参数声明',
    'SegmentDefinition': '段落 名()：',
    'ClassDefinition': '类 名：',
    'InterfaceDefinition': '接口 名：',
    'MethodDefinition': '方法定义',
    'DecoratorDefinition': '@装饰器',
    'TypeAlias': '类型 甲 = 整数',
    'AsyncScope': '异步 作用域',
}


# ----------------------------------------------------------------------
# 代码扫描
# ----------------------------------------------------------------------

def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _method_src(src, name):
    """截取 `def name(` 起到下一个同级 `def` 为止的源码。"""
    lines = src.split('\n')
    start = None
    for i, line in enumerate(lines):
        if f'def {name}(' in line:
            start = i
            break
    if start is None:
        return ''
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('    def ') and not lines[i].startswith('        '):
            end = i
            break
    return '\n'.join(lines[start:end])


def scan_v3_stmt_classes():
    import inspect
    import ast_nodes_v3 as v3
    classes = []
    for name, cls in inspect.getmembers(v3, inspect.isclass):
        if not issubclass(cls, v3.ASTNode) or cls is v3.ASTNode:
            continue
        if name.endswith(('Stmt', 'Statement', 'Decl')) or name in EXTRA_STMT_CLASSES:
            classes.append(name)
    return sorted(set(classes))


def scan_adapter_map(adapter_src):
    """v3 节点名 -> 转换器方法名。

    直接全文扫注册字典：键（v3 节点名）全局唯一，而按 `def __init__` 截取会截错
    ——compiler.py 里不止一个类有 `__init__`，取到的可能是别人家的。
    """
    return dict(re.findall(r"'([A-Za-z_]\w*)':\s*self\.(_convert_\w+)", adapter_src))


def scan_converter_legacy_target(adapter_src, method_name):
    """转换器方法返回的 legacy 节点类型；返回 None 表示无落点（如 PassStmt 编成 no-op）。

    两种写法都得认：`return ast.XXX(...)` 和 `decl = ast.XXX(...)` + `return decl`
    （R114-S1 的 `_convert_scope_decl_stmt` 就是后者，只认前一种会把它当成 no-op）。
    """
    body = _method_src(adapter_src, method_name)
    if not body:
        return None
    m = re.search(r'return\s+ast\.(\w+)\(', body)
    if m:
        return m.group(1)
    m = re.search(r'return\s+(\w+)\s*$', body, re.M)
    if m:
        var = m.group(1)
        m2 = re.search(rf'\b{re.escape(var)}\s*=\s*ast\.(\w+)\(', body)
        if m2:
            return m2.group(1)
    return None


def scan_whitelist(adapter_src):
    body = _method_src(adapter_src, '_to_list_stmts')
    return set(re.findall(r'ast\.(\w+),', body)) | set(re.findall(r'ast\.(\w+),\s*\n', body))


def scan_dispatch(codegen_src):
    body = _method_src(codegen_src, '_gen_statement')
    return set(re.findall(r'isinstance\(stmt, ast\.(\w+)\)', body))


def probe(src_text):
    """真编一次，返回 (结果, 说明)。"""
    try:
        from llvm.compiler import compile_source_typed
    except Exception as e:  # pragma: no cover - 环境不具备时如实报
        return 'skip', f'无法导入原生腿编译器：{type(e).__name__}'
    try:
        ir = compile_source_typed(src_text)
    except NotImplementedError as e:
        return 'reject', str(e).split('（')[0]
    except Exception as e:
        return 'error', f'{type(e).__name__}: {str(e).splitlines()[0][:80]}'
    if '<unknown' in ir:
        return 'error', 'IR 里残留 <unknown 伪装'
    return 'ok', f'{len(ir)} 字符'


# ----------------------------------------------------------------------
# 矩阵组装
# ----------------------------------------------------------------------

def build(do_probe=True):
    v3_src = _read(V3)
    adapter_src = _read(ADAPTER)
    codegen_src = _read(CODEGEN)

    classes = scan_v3_stmt_classes()
    adapter_map = scan_adapter_map(adapter_src)
    whitelist = scan_whitelist(adapter_src)
    dispatch = scan_dispatch(codegen_src)

    rows = []
    for cls in classes:
        conv = adapter_map.get(cls)
        legacy = scan_converter_legacy_target(adapter_src, conv) if conv else None
        in_wl = (legacy in whitelist) if legacy else False
        in_dp = (legacy in dispatch) if legacy else False

        if conv is None:
            status = 'gap:adapter'
        elif legacy is None:
            # 转换器返回 None（如 PassStmt 编成 no-op）-> 语义上就是"不需要后端"
            status = 'n/a(no-op)'
        elif legacy in UPSTREAM_PATH:
            status = 'supported(upstream)'
        elif not in_wl:
            status = 'gap:whitelist'
        elif not in_dp:
            status = 'gap:codegen'
        else:
            status = 'supported'

        case = PROBE_CASES.get(cls)
        if case is None:
            probe_result, probe_note = ('—', '无自动用例')
        elif not do_probe:
            probe_result, probe_note = ('skip', '未实测（--no-probe）')
        else:
            probe_result, probe_note = probe(case)
            if status == 'supported' and probe_result != 'ok':
                status = 'broken'
            if status == 'supported(upstream)' and probe_result in ('reject', 'error'):
                status = 'broken(upstream)'
            if status.startswith('gap') and probe_result == 'ok':
                # 三层看着缺、实测却编过了 —— 说明扫描口径漏了，标出来而不是装作没事
                status = 'supported(?)'

        rows.append({
            'v3_class': cls,
            'surface': SURFACE.get(cls, ''),
            'adapter_converter': conv or '',
            'legacy_node': legacy or '',
            'in_stmt_whitelist': bool(in_wl),
            'in_dispatch': bool(in_dp),
            'probe_case': case,
            'probe_result': probe_result,
            'probe_note': probe_note,
            'status': status,
        })
    return rows, {'whitelist': sorted(whitelist), 'dispatch': sorted(dispatch)}


def render_md(rows, meta):
    total = len(rows)
    sup = sum(1 for r in rows if r['status'].startswith('supported'))
    gaps = [r for r in rows if r['status'].startswith('gap')]
    broken = [r for r in rows if r['status'] == 'broken']
    lines = [
        '# 原生（LLVM）后端能力矩阵',
        '',
        '> 由 `scripts/gen_llvm_capability_matrix.py` 自动生成，**不要手改**——',
        '> 改了 codegen / 适配层之后跑一次生成脚本，门禁 `tests/unit/test_llvm_capability_matrix.py`',
        '> 会拿本矩阵与代码双向对咬（代码支持了矩阵没更新会红，矩阵说支持代码其实不支也会红）。',
        '',
        '## 口径',
        '',
        '一条语句要真被原生腿支持，得过三层，断在哪层就报哪层：',
        '',
        '| 层 | 位置 | 断了会怎样 |',
        '|----|------|-----------|',
        '| L1 适配层转换器 | `compiler.AstAdapter._node_converters` | 被包成 `<unknown:XXX>` 伪装标识符，后端永远认不出 |',
        '| L2 语句流白名单 | `compiler.AstAdapter._to_list_stmts` | 语句被包成 ExpressionStatement，分派链匹配不到 |',
        '| L3 后端分派 | `codegen_typed._gen_statement` | 链尾兜底抛「暂不支持」 |',
        '',
        '外加一列**实测**：真跑 `compile_source_typed`。三层都过但实测编不过 → `broken`；',
        '三层看着缺却编过了 → `supported(?)`（说明扫描口径漏了，要人来看，不许装作没事）。',
        '',
        '## 汇总',
        '',
        f'- 语句类型总数：**{total}**',
        f'- 已支持：**{sup}**',
        f'- 缺口：**{len(gaps)}**',
        f'- 三层齐备但实测编不过：`{len(broken)}`',
        '',
        '## 矩阵',
        '',
        '| v3 语句类 | 写法 | L1 转换器 | legacy 落点 | L2 白名单 | L3 分派 | 实测 | 状态 |',
        '|---|---|---|---|---|---|---|---|',
    ]
    mark = {'ok': '✅', 'reject': '⛔', 'error': '❌', '—': '—', 'skip': '—'}
    for r in rows:
        lines.append(
            f"| `{r['v3_class']}` | {r['surface'] or '—'} | {'有' if r['adapter_converter'] else '**无**'} "
            f"| `{r['legacy_node'] or '—'}` | {'有' if r['in_stmt_whitelist'] else '**无**'} "
            f"| {'有' if r['in_dispatch'] else '**无**'} "
            f"| {mark.get(r['probe_result'], r['probe_result'])} {r['probe_note']} | `{r['status']}` |"
        )
    lines += [
        '',
        '## 缺口清单（按层归类）',
        '',
    ]
    by_layer = {}
    for r in gaps:
        by_layer.setdefault(r['status'], []).append(r['v3_class'])
    if not by_layer:
        lines.append('（当前没有缺口）')
    for layer in sorted(by_layer):
        lines.append(f'- **{layer}**（{len(by_layer[layer])}）：' +
                     '、'.join(f'`{c}`' for c in by_layer[layer]))
    lines += [
        '',
        '## 与既有清单的分工',
        '',
        '- `docs/原生腿能力清单.json`：只登记**已支持**的（内置函数 / 运行时符号 / 节点），单向清单。',
        '- 本矩阵：**全部**语句类型 × 三层证据 × 实测，缺口要可点名、可归层。',
    ]
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只比对，不写文件')
    ap.add_argument('--no-probe', action='store_true', help='跳过实测列（快，但矩阵不完整）')
    args = ap.parse_args()

    rows, meta = build(do_probe=not args.no_probe)
    md = render_md(rows, meta)
    payload = {
        'schema_version': '1.0',
        'description': '原生(LLVM)后端能力矩阵：v3 语句类 × 三层证据 × 实测',
        'generator': 'scripts/gen_llvm_capability_matrix.py',
        'counts': {
            'total': len(rows),
            'supported': sum(1 for r in rows if r['status'].startswith('supported')),
            'gap': sum(1 for r in rows if r['status'].startswith('gap')),
        },
        'rows': rows,
        'meta': meta,
    }

    if args.check:
        if not os.path.exists(OUT_JSON):
            print('矩阵 JSON 不存在，先跑一次生成脚本')
            return 2
        with open(OUT_JSON, encoding='utf-8') as f:
            old = json.load(f)
        diff = []
        old_map = {r['v3_class']: r for r in old['rows']}
        for r in rows:
            o = old_map.get(r['v3_class'])
            if o is None:
                diff.append(f"新增语句类 {r['v3_class']}（矩阵未登记）")
            elif o['status'] != r['status']:
                diff.append(f"{r['v3_class']}: 矩阵记 {o['status']}，实测 {r['status']}")
        if diff:
            print('矩阵与代码不一致：')
            for d in diff:
                print('  - ' + d)
            return 1
        print('矩阵与代码一致')
        return 0

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'已写出 {OUT_MD}')
    print(f'已写出 {OUT_JSON}')
    print(f"  语句类型 {payload['counts']['total']}｜已支持 {payload['counts']['supported']}"
          f"｜缺口 {payload['counts']['gap']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
