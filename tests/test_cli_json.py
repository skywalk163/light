# -*- coding: utf-8 -*-
"""T-0382：R222 接线卡的机器可读契约（spec / ast / check / symbols / patch / ai check）。

所有用例都用 subprocess 起**真实的** ``cli/light.py``，而不是直接调内部函数：
外部 Agent 消费的只有 stdout / stderr / 退出码三样东西，只有走真进程才算数。

契约（本文件是唯一来源）：
  * 每个 ``--json`` 子命令 stdout 只有一个 JSON 对象（单行、前无杂字、后无杂字），
    能直接 ``json.loads`` 回环；
  * 诊断字段齐全且类型稳定；位置未知就写 0，绝不编造行号；
  * 退出码：0 = 无 error 级诊断（warning 不失败）；1 = 有 error 级诊断
    （或被补丁引擎拒绝）；2 = 用法 / 文件错误；
  * ``--partial`` 遇未闭合输入必须不 fail、不抛栈，返回 ``partial: true``。

无 ``--json`` 时的文本路径是既有行为，本卡不改它；这里只钉住几条关键行基线。
"""

import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO_ROOT, 'cli', 'light.py')

EXIT_OK = 0
EXIT_DIAGNOSTIC = 1
EXIT_USAGE = 2

SCHEMA_VERSION = 1

# ── 样本源码 ──
CLEAN_SOURCE = "设 甲 为 1\n打印(甲)\n"
# 第 2 行第 5 列缺右括号：位置必须被如实报出来
SYNTAX_ERROR_SOURCE = "设 甲 为 (\n打印(甲)\n"
# 第 2 行未闭合：--partial 必须只检查第 1 行，且不失败
UNCLOSED_SOURCE = "设 甲 为 1\n设 乙 为 (\n"

# 诊断的必备字段（与 `light ai check --json` 同一口径 + anchor/file）
REQUIRED_DIAG_FIELDS = (
    'code', 'severity', 'stage', 'line', 'column',
    'message', 'hint', 'fixes', 'candidates', 'provisional',
    'anchor', 'file',
)
SEVERITIES = ('error', 'warning', 'info')
# ai check 顶层 stage 允许的四个阶段（任务卡口径）
AI_STAGES = ('词法', '语法', '类型', '运行')

# stdout 上不许出现的进度 / emoji（JSON 里的中文不算）
STDOUT_FORBIDDEN = ('📄', '✅', '❌', '⚠', '🔎', '✓', '✗', '[1/2]', '[2/2]')


def _write(directory, name, source):
    path = os.path.join(str(directory), name)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(source)
    return path


def _run(*argv, stdin=None):
    """跑真实 CLI；stdout/stderr 一律 UTF-8 解码，避免平台默认编码干扰。"""
    return subprocess.run(
        [sys.executable, '-X', 'utf8', CLI, *argv],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=REPO_ROOT, timeout=180,
        input=stdin,
    )


def _json_of(proc):
    """stdout 必须能直接 json.loads —— 不剥前缀、不找子串。"""
    payload = json.loads(proc.stdout)
    assert isinstance(payload, dict), f'stdout 顶层应为对象，实际 {type(payload).__name__}'
    return payload


def _assert_single_line_json(proc):
    """stdout 恰好一个 JSON 对象，且只占一行。"""
    stdout = proc.stdout
    assert stdout.strip().startswith('{') and stdout.strip().endswith('}'), \
        f'stdout 不是单个 JSON 对象:\n{stdout}'
    assert len([line for line in stdout.splitlines() if line.strip()]) == 1, \
        f'stdout 应为单行 JSON，实际:\n{stdout}'
    for token in STDOUT_FORBIDDEN:
        assert token not in stdout, f'stdout 不应出现进度/emoji「{token}」:\n{stdout}'


def _assert_diagnostics(diagnostics):
    """每条诊断字段齐全、类型稳定。"""
    assert isinstance(diagnostics, list), diagnostics
    for diag in diagnostics:
        for field in REQUIRED_DIAG_FIELDS:
            assert field in diag, f'诊断缺少字段 {field}: {diag}'
        assert isinstance(diag['code'], str) and re.match(r'^L\d{4}$', diag['code']), diag
        assert diag['severity'] in SEVERITIES, diag
        assert isinstance(diag['stage'], str) and diag['stage'], diag
        assert isinstance(diag['line'], int) and diag['line'] >= 0, diag
        assert isinstance(diag['column'], int) and diag['column'] >= 0, diag
        assert isinstance(diag['message'], str) and diag['message'], diag
        assert isinstance(diag['hint'], str), diag
        assert isinstance(diag['fixes'], list) and all(isinstance(x, str) for x in diag['fixes']), diag
        assert len(diag['fixes']) <= 3, diag
        assert isinstance(diag['candidates'], list), diag
        assert isinstance(diag['provisional'], bool), diag
        assert diag['anchor'] in ('parser', 'linter', 'cli'), diag
        assert isinstance(diag['file'], str) or diag['file'] is None, diag


# ── 样本文件（module 级，避免每个用例重复落盘）──
@pytest.fixture(scope='module')
def clean_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('cli_json'), 'clean.light', CLEAN_SOURCE)


@pytest.fixture(scope='module')
def syntax_error_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('cli_json'), 'bad.light', SYNTAX_ERROR_SOURCE)


@pytest.fixture(scope='module')
def unclosed_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('cli_json'), 'open.light', UNCLOSED_SOURCE)


@pytest.fixture(scope='module')
def missing_path(tmp_path_factory):
    return os.path.join(str(tmp_path_factory.mktemp('cli_json')), 'nope.light')


class TestSpecSubcommand:
    """`light spec [--json] [--check]`：权威表只读输出 / 陈旧校验。"""

    def test_spec_json_is_authoritative_table(self):
        proc = _run('spec', '--json')
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        # 就是 spec/light.spec.json 原文：不加 ok 壳字段
        assert payload['schema_version'] == SCHEMA_VERSION
        assert payload['spec'] == 'light.spec.json'
        for key in ('keywords', 'operators', 'stdlib', 'syntax_forms', 'diagnostics'):
            assert isinstance(payload[key], (list, dict)), key

    def test_spec_check_json_forwards_exit_code(self):
        proc = _run('spec', '--check', '--json')
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert payload['check'] is True
        assert payload['exit_code'] == proc.returncode
        assert proc.returncode in (EXIT_OK, EXIT_DIAGNOSTIC), proc.stdout
        assert payload['ok'] is (proc.returncode == EXIT_OK)

    def test_spec_check_text_mode_no_json(self):
        proc = _run('spec', '--check')
        assert proc.returncode in (EXIT_OK, EXIT_DIAGNOSTIC), proc.stdout
        assert not proc.stdout.strip().startswith('{'), '不带 --json 不应吐 JSON'


class TestAstJson:
    """`light ast --json`：薄转发 src/patch_engine.ast_to_json。"""

    def test_ast_json_shape(self, clean_file):
        proc = _run('ast', '--json', clean_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert payload['ok'] is True
        ast = payload['ast']
        assert ast['language'] == 'light'
        assert ast['schema_version'] == SCHEMA_VERSION
        assert ast['file'] == clean_file
        root = ast['root']
        assert root['kind'] == 'Module'
        span = root['span']
        for key in ('start_line', 'start_col', 'end_line', 'end_col'):
            assert isinstance(span[key], int), span
        assert ast['source']['line_count'] >= 1
        assert ast['source']['node_count'] >= 1

    def test_ast_json_roundtrip(self, clean_file):
        payload = _json_of(_run('ast', '--json', clean_file))
        # 回环：dump 后再 parse 必须完全一致（说明没有不可序列化对象混进来）
        assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload

    def test_ast_json_missing_file_exits_2(self, missing_path):
        proc = _run('ast', '--json', missing_path)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_USAGE, proc.stdout
        assert payload['ok'] is False and payload['ast'] is None
        assert '文件不存在' in payload['error']


class TestCheckJson:
    """`light check --json [--partial]`：结构化诊断 + 明确 rc。"""

    def test_clean_file_exits_0(self, clean_file):
        proc = _run('check', '--json', clean_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert payload['ok'] is True
        assert payload['diagnostics'] == []
        assert payload['partial'] is False
        assert payload['partial_from_line'] == 0
        assert payload['backend'] == 'src'
        assert isinstance(payload['summary']['total_lines'], int)

    def test_syntax_error_exits_1(self, syntax_error_file):
        proc = _run('check', '--json', syntax_error_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_DIAGNOSTIC, proc.stderr
        assert payload['ok'] is False
        assert payload['diagnostics'], '语法错误不应得到空诊断'
        _assert_diagnostics(payload['diagnostics'])
        assert any(d['severity'] == 'error' for d in payload['diagnostics'])
        first = payload['diagnostics'][0]
        # 位置是真实行列：右括号缺失在第 2 行第 5 列，不许写成 0
        assert first['line'] == 2, first
        assert first['column'] == 5, first

    def test_missing_file_exits_2(self, missing_path):
        proc = _run('check', '--json', missing_path)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_USAGE, proc.stdout
        assert payload['ok'] is False
        _assert_diagnostics(payload['diagnostics'])
        assert payload['diagnostics'][0]['stage'] == '用法'

    def test_partial_unclosed_does_not_fail(self, unclosed_file):
        proc = _run('check', '--json', '--partial', unclosed_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        # --partial：未闭合尾巴只记 warning，不 fail
        assert proc.returncode == EXIT_OK, proc.stdout
        assert payload['partial'] is True
        assert payload['partial_from_line'] == 2
        assert not any(d['severity'] == 'error' for d in payload['diagnostics'])
        _assert_diagnostics(payload['diagnostics'])
        assert 'Traceback' not in proc.stderr, proc.stderr

    def test_partial_closed_file_is_not_partial(self, clean_file):
        payload = _json_of(_run('check', '--json', '--partial', clean_file))
        assert payload['partial'] is False
        assert payload['ok'] is True

    def test_warning_only_keeps_rc_0(self, unclosed_file):
        """warning 级诊断不得把 rc 抬到 1（本卡 rc 语义：error 才失败）。"""
        payload = _json_of(_run('check', '--json', '--partial', unclosed_file))
        assert payload['diagnostics']
        assert all(d['severity'] == 'warning' for d in payload['diagnostics'])


class TestCheckTextModeUnchanged:
    """不带新开关时，`light check` 的输出与退出码必须与今天一致。"""

    def test_default_clean_still_passes(self, clean_file):
        proc = _run('check', clean_file)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert '✅ 语法检查通过' in proc.stdout, proc.stdout
        assert not proc.stdout.strip().startswith('{'), '默认路径不应吐 JSON'

    def test_default_broken_still_exits_1(self, syntax_error_file):
        proc = _run('check', syntax_error_file)
        assert proc.returncode == EXIT_DIAGNOSTIC, proc.stdout
        assert '❌ 发现' in proc.stdout, proc.stdout

    def test_partial_text_mode_does_not_fail(self, unclosed_file):
        proc = _run('check', '--partial', unclosed_file)
        assert proc.returncode == EXIT_OK, proc.stdout
        assert '部分检查（--partial）' in proc.stderr, proc.stderr
        assert 'Traceback' not in proc.stderr, proc.stderr


class TestSymbolsJson:
    """`light symbols --json`：薄转发 src/patch_engine.symbols_json。"""

    def test_symbols_json_shape(self, clean_file):
        proc = _run('symbols', '--json', clean_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert payload['ok'] is True
        symbols = payload['symbols']
        for key in ('definitions', 'imports', 'exports', 'scopes', 'references'):
            assert key in symbols, f'symbols 缺少 {key}: {list(symbols)}'
        assert isinstance(symbols['definitions'], list) and symbols['definitions'], symbols
        definition = symbols['definitions'][0]
        assert definition['name'] == '甲'
        assert definition['canonical'] == '甲'
        assert isinstance(definition['span']['start_line'], int)
        assert definition['references'] >= 1

    def test_symbols_json_missing_file_exits_2(self, missing_path):
        proc = _run('symbols', '--json', missing_path)
        _assert_single_line_json(proc)
        assert proc.returncode == EXIT_USAGE, proc.stdout
        assert _json_of(proc)['ok'] is False


class TestPatchJson:
    """`light patch [--json] <file> --edits <json>`：只输出结果，不写文件。"""

    def test_patch_replaces_span(self, clean_file):
        edits = json.dumps([{
            'span': {'start_line': 1, 'start_col': 7, 'end_line': 1, 'end_col': 8},
            'text': '42',
        }], ensure_ascii=False)
        proc = _run('patch', '--json', clean_file, '--edits', edits)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert payload['ok'] is True
        assert payload['changed'] is True
        assert payload['patched_source'].startswith('设 甲 为 42')
        assert payload['diff_summary']['changed_lines'] == {'old': [1], 'new': [1]}
        # 不许落盘：原文件必须逐字不变
        with open(clean_file, encoding='utf-8') as handle:
            assert handle.read() == CLEAN_SOURCE

    def test_patch_accepts_edits_from_stdin(self, clean_file):
        edits = json.dumps([{
            'span': {'start_line': 1, 'start_col': 7, 'end_line': 1, 'end_col': 8},
            'text': '42',
        }], ensure_ascii=False)
        proc = _run('patch', '--json', clean_file, '--edits', '-', stdin=edits)
        _assert_single_line_json(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert _json_of(proc)['changed'] is True

    def test_patch_rejects_overlap(self, clean_file):
        # 起点在终点之后 = 不闭合，必须被拒（rc=1，不是 traceback）
        edits = json.dumps([{
            'span': {'start_line': 1, 'start_col': 9, 'end_line': 1, 'end_col': 2},
            'text': '9',
        }], ensure_ascii=False)
        proc = _run('patch', '--json', clean_file, '--edits', edits)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_DIAGNOSTIC, proc.stdout
        assert payload['ok'] is False and payload['patched_source'] is None
        assert '补丁被拒' in payload['error'], payload['error']
        assert 'Traceback' not in proc.stderr, proc.stderr

    def test_patch_bad_json_exits_2(self, clean_file):
        proc = _run('patch', '--json', clean_file, '--edits', 'not-json')
        _assert_single_line_json(proc)
        assert proc.returncode == EXIT_USAGE, proc.stdout
        assert 'JSON' in _json_of(proc)['error']


class TestAiCheckJsonStage:
    """`light ai check --json`：R222 补齐 ok / stage / diagnostics / fix_suggestions。"""

    def test_stage_and_fix_suggestions_on_clean(self, clean_file):
        proc = _run('ai', 'check', '--json', clean_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert payload['ok'] is True
        assert payload['stage'] in AI_STAGES, payload['stage']
        assert payload['diagnostics'] == []
        assert payload['fix_suggestions'] == []

    def test_stage_on_syntax_error(self, syntax_error_file):
        proc = _run('ai', 'check', '--json', syntax_error_file)
        _assert_single_line_json(proc)
        payload = _json_of(proc)
        assert proc.returncode == EXIT_DIAGNOSTIC, proc.stderr
        assert payload['ok'] is False
        assert payload['stage'] in AI_STAGES, payload['stage']
        assert payload['diagnostics'], '语法错误不应得到空诊断'
        for key in ('code', 'severity', 'stage', 'line', 'column',
                    'message', 'hint', 'fixes', 'candidates', 'provisional'):
            assert key in payload['diagnostics'][0], payload['diagnostics'][0]
        assert isinstance(payload['fix_suggestions'], list)
        for suggestion in payload['fix_suggestions']:
            for key in ('code', 'stage', 'line', 'column', 'hint', 'fixes'):
                assert key in suggestion, suggestion


class TestNoSideEffects:
    """接线不许带来「自动写文件」这类副作用，也不许改既有子命令的默认行为。"""

    def test_spec_json_does_not_write_spec_file(self):
        path = os.path.join(REPO_ROOT, 'spec', 'light.spec.json')
        before = os.stat(path).st_mtime_ns
        _run('spec', '--json')
        assert os.stat(path).st_mtime_ns == before, 'spec --json 不应改写权威表'

    def test_ast_text_mode_still_human(self, clean_file):
        proc = _run('ast', clean_file)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert 'Module' in proc.stdout, proc.stdout
        assert not proc.stdout.strip().startswith('{'), '不带 --json 不应吐 JSON'
