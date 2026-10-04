# -*- coding: utf-8 -*-
"""R114-S1（L3 门禁）：原生（LLVM）后端能力矩阵不许烂、不许退、不许吹牛。

矩阵本身由 `scripts/gen_llvm_capability_matrix.py` 生成（人读 md + 机读 json）。
本文件是它的**门禁**：拿矩阵与代码双向对咬，三条断言各盯一类腐烂：

  1. 不许退（回退保护，deepseek 建议的硬卡点）
     矩阵里记成 `supported*` 的语句类型，重新扫代码必须仍是 supported。
     谁把 `_gen_statement` 的某个分支删了、或把 `_to_list_stmts` 白名单里的
     某项去掉了，这里立刻红——「今天支持、明天又坏」不再有可能悄悄发生。

  2. 不许吹牛（实测护栏）
     矩阵里 supported 且带最小用例、且当时实测 `ok` 的项，现在真编一次必须还 ok。
     少了这条，把矩阵手动改成 supported（或生成器扫描口径写错）也能全绿。

  3. 不许漏登记（防腐烂）
     代码里新出现的 v3 语句类，矩阵里必须有条目——提示去跑生成脚本。
"""
import importlib.util
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, 'src'))
sys.path.insert(0, _ROOT)

_MATRIX_JSON = os.path.join(_ROOT, 'docs', 'llvm_backend_capability_matrix.json')
_GEN = os.path.join(_ROOT, 'scripts', 'gen_llvm_capability_matrix.py')


def _load_gen():
    spec = importlib.util.spec_from_file_location('_gen_llvm_capability_matrix', _GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def matrix():
    if not os.path.exists(_MATRIX_JSON):
        pytest.fail(f'能力矩阵不存在：{_MATRIX_JSON}（跑 scripts/gen_llvm_capability_matrix.py 生成）')
    with open(_MATRIX_JSON, encoding='utf-8') as f:
        return json.load(f)


def test_矩阵格式完整(matrix):
    assert matrix.get('schema_version') == '1.0'
    assert matrix['rows'], '矩阵一行都没有'
    for r in matrix['rows']:
        for k in ('v3_class', 'legacy_node', 'status'):
            assert k in r, f'条目缺字段 {k}：{r}'


def test_已支持项不许回退(matrix):
    """回退保护：矩阵记 supported 的，重新扫代码必须还是 supported。"""
    gen = _load_gen()
    rows, _ = gen.build(do_probe=False)
    now = {r['v3_class']: r for r in rows}
    regressed = []
    for r in matrix['rows']:
        if not r['status'].startswith('supported'):
            continue
        cur = now.get(r['v3_class'])
        if cur is None:
            regressed.append(f"{r['v3_class']}：矩阵有、代码里扫不到（语句类被改名/删了？）")
        elif not cur['status'].startswith('supported'):
            regressed.append(
                f"{r['v3_class']}：矩阵记 {r['status']}，现在扫出来是 {cur['status']} "
                f"（L1转换器={'有' if cur['adapter_converter'] else '无'} "
                f"L2白名单={'有' if cur['in_stmt_whitelist'] else '无'} "
                f"L3分派={'有' if cur['in_dispatch'] else '无'}）")
    assert not regressed, '能力矩阵回退：\n  - ' + '\n  - '.join(regressed)


def test_新语句类必须登记进矩阵(matrix):
    """防腐烂：代码里新出现的 v3 语句类，矩阵里得有条目。"""
    gen = _load_gen()
    rows, _ = gen.build(do_probe=False)
    known = {r['v3_class'] for r in matrix['rows']}
    missing = [r['v3_class'] for r in rows if r['v3_class'] not in known]
    assert not missing, (
        '这些语句类代码里有、矩阵没登记，跑一次 '
        'scripts/gen_llvm_capability_matrix.py：' + '、'.join(missing))


@pytest.mark.parametrize('row', [
    pytest.param(r, id=r['v3_class'])
    for r in json.load(open(_MATRIX_JSON, encoding='utf-8'))['rows']
    if r['status'].startswith('supported') and r['probe_case'] and r['probe_result'] == 'ok'
])
def test_已支持项真编得过(row):
    """实测护栏：矩阵说支持、当时也实测过，现在必须还编得过。"""
    gen = _load_gen()
    result, note = gen.probe(row['probe_case'])
    assert result == 'ok', f"{row['v3_class']} 编不过了：{result} / {note}"


def test_缺口项必须是明确拒绝而不是静默编过():
    """反跑：矩阵里记成 gap 的项，若它有最小用例，实测不该是「编过还带 <unknown>」。

    允许 reject（明确拒绝，正是缺口该有的样子）；出现 `ok` 说明扫描口径漏了，
    生成器会把它标成 `supported(?)`——那条由 `test_已支持项真编得过` 之外的
    人工确认处理，这里只负责拦「静默编过还自以为支持」。
    """
    gen = _load_gen()
    rows, _ = gen.build(do_probe=False)
    suspicious = []
    for r in rows:
        if not r['status'].startswith('gap'):
            continue
        if not r['probe_case']:
            continue
        result, note = gen.probe(r['probe_case'])
        if result == 'ok':
            suspicious.append(f"{r['v3_class']}：矩阵记 {r['status']}，实测却编过了（{note}）")
    assert not suspicious, '缺口项与实测矛盾（跑生成脚本重新定级）：\n  - ' + '\n  - '.join(suspicious)
