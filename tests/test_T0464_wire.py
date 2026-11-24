# -*- coding: utf-8 -*-
"""T-0464：把 ①–⑤ 的纯模块接进 CLI 的唯一热点 owner 验收。

覆盖任务卡的四条完成标准（全部用 subprocess 跑真 CLI，Agent 消费的是
stdout / stderr / 退出码三样东西）：

1. `ai check --json` 对 `def 问候():` → 诊断里**没有** `L0000`，有 `D1` 开头的码，
   且 `fix_edits` 是**可套用**结构（span + replacement，套用后整行变成
   `段落 问候：`）。
2. `light 运行 <文件>` 与 `light run <文件>` 的 stdout 与退出码逐字一致。
3. `ai card --level compact|standard|full` 三档都能出，长度符合 T-0459 上限
   （compact ≤300、standard ≤3000、full <600 且是索引页）。
4. `--fast` 与默认模式对同一坏文件的 error 数量一致（只是不做类型/运行检查）。

外加班：`--strict` 默认关、`light check --strict` 出 warning 而不改退出码、
中文别名写进 `--help`。

平台说明：全部用 Python 标准库，不依赖 head/grep/awk、`!`、`$()`；
Windows / FreeBSD 上都能跑。
"""

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 单行 `def`：行尾冒号会骗过报错文本归因（L0000），D1xx 必须接管这一行。
PYISM_SOURCE = 'def 问候():\n'
# 纯语法坏文件（不含 Python 惯性）：--fast 与默认模式的 error 数必须一致。
SYNTAX_ERROR_SOURCE = '设 甲 为 (\n打印(甲)\n'
# 可运行文件：别名与英文命令的 stdout / 退出码逐字一致。
RUN_SOURCE = '设 甲 为 1\n打印(甲)\n'
# 非规范写法：别名「打印」+ 缺少 L2 类型标注（--strict 的 D2xx 来源）。
STRICT_SOURCE = '设 甲 为 1\n打印(甲)\n'


def _run(*argv):
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'cli.light', *argv],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=REPO_ROOT, timeout=180,
    )


def _payload(proc):
    assert proc.stdout.strip(), f'stdout 为空，stderr={proc.stderr}'
    payload = json.loads(proc.stdout)
    assert isinstance(payload, dict), f'stdout 顶层应为对象，实际 {type(payload).__name__}'
    return payload


# `strict` 用例的简写入口（与 `_payload` 同源，只是命名更贴近语义）。
_json_of = _payload


def _write(directory, name, source):
    path = os.path.join(str(directory), name)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(source)
    return path


def _apply_edit(source, edit):
    """按 `fix_edits` 的 span 套用一次替换（列 1-based、end 开区间）。"""
    span = edit['span']
    lines = source.split('\n')
    index = span['start_line'] - 1
    line = lines[index]
    lines[index] = (line[:span['start_col'] - 1] + edit['replacement']
                    + line[span['end_col'] - 1:])
    return '\n'.join(lines)


# ── 模块级夹具：同一批真实进程只起一次 ──────────────────────────────
@pytest.fixture(scope='module')
def pyism_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('t0464'), 'pyism.light', PYISM_SOURCE)


@pytest.fixture(scope='module')
def pyism_json(pyism_file):
    return _run('ai', 'check', pyism_file, '--json')


@pytest.fixture(scope='module')
def syntax_error_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('t0464'), 'bad.light', SYNTAX_ERROR_SOURCE)


@pytest.fixture(scope='module')
def run_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('t0464'), 'run.light', RUN_SOURCE)


@pytest.fixture(scope='module')
def strict_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('t0464'), 'strict.light', STRICT_SOURCE)


class TestDiagnosticsWiring:
    """① D1xx 接管 L0000，并且给出可套用的 span + replacement。"""

    def test_d1_code_replaces_l0000(self, pyism_json):
        payload = _payload(pyism_json)
        codes = [d['code'] for d in payload['diagnostics']]
        assert payload['ok'] is False
        assert not any(code == 'L0000' for code in codes), \
            f'`def` 行不应再落 L0000 占位码，实际 {codes}'
        assert any(code.startswith('D1') for code in codes), \
            f'应出现 src/ai_pyisms 的 D1xx 码，实际 {codes}'

    def test_position_and_severity_follow_schema(self, pyism_json):
        payload = _payload(pyism_json)
        diag = next(d for d in payload['diagnostics'] if d['code'].startswith('D1'))
        assert diag['stage'] == '语法检查', diag
        assert diag['line'] == 1 and diag['column'] == 1, diag
        assert diag['severity'] in ('error', 'warning', 'info'), diag
        assert diag['provisional'] is False, diag

    def test_fix_edits_are_applicable(self, pyism_file, pyism_json):
        """`fix_edits` 不是 hint 的复制：span + replacement 套用后真的能改对。"""
        source = open(pyism_file, encoding='utf-8').read()
        payload = _payload(pyism_json)
        diag = next(d for d in payload['diagnostics'] if d['code'].startswith('D1'))
        assert diag['fix_edits'], f'{diag["code"]} 应带可套用修复：{diag}'
        edit = diag['fix_edits'][0]
        assert set(edit) == {'span', 'replacement'}, edit
        assert set(edit['span']) == {'start_line', 'start_col', 'end_line', 'end_col'}, edit
        patched = _apply_edit(source, edit)
        assert 'def' not in patched, f'套用后仍残留 Python 写法：{patched!r}'
        assert '段落' in patched, f'套用后应为光明写法：{patched!r}'

    def test_fix_suggestions_carry_the_same_edit(self, pyism_json):
        """顶层 fix_suggestions 与逐条诊断给出同一份可套用编辑，不各说各话。"""
        payload = _payload(pyism_json)
        entry = next(s for s in payload['fix_suggestions']
                     if str(s['code']).startswith('D1'))
        assert entry['fix_edits'], entry
        assert entry['fix_edits'][0]['replacement'], entry


class TestChineseAliases:
    """④ 中文子命令别名：与英文命令逐字一致（含退出码）。"""

    def test_run_alias_matches_english(self, run_file):
        chinese = _run('运行', run_file)
        english = _run('run', run_file)
        assert chinese.returncode == english.returncode, \
            f'退出码不一致：运行={chinese.returncode} run={english.returncode}'
        assert chinese.stdout == english.stdout, 'stdout 必须逐字一致'

    def test_alias_keeps_user_args_after_double_dash(self, run_file):
        """`--` 之后是脚本实参，别名翻译不得碰它。"""
        chinese = _run('运行', run_file, '--', '甲', '乙')
        english = _run('run', run_file, '--', '甲', '乙')
        assert chinese.returncode == english.returncode
        assert chinese.stdout == english.stdout

    def test_aliases_are_documented_in_help(self):
        proc = _run('--help')
        assert proc.returncode == 0, proc.stderr
        for alias in ('运行', '检查', '编译', '测试', '格式化'):
            assert alias in proc.stdout, f'--help 未说明中文别名「{alias}」'


class TestCardLevels:
    """③ 三层卡：长度硬指标来自 T-0459，CLI 不得破线。"""

    def test_compact_within_300(self):
        proc = _run('ai', 'card', '--level', 'compact')
        assert proc.returncode == 0, proc.stderr
        assert len(proc.stdout.strip()) <= 300, \
            f'compact 卡 {len(proc.stdout.strip())} 字符，超出 300 上限'

    def test_standard_within_3000(self):
        proc = _run('ai', 'card', '--level', 'standard')
        assert proc.returncode == 0, proc.stderr
        assert len(proc.stdout.strip()) <= 3000, \
            f'standard 卡 {len(proc.stdout.strip())} 字符，超出 3000 上限'

    def test_full_is_index_page(self):
        proc = _run('ai', 'card', '--level', 'full')
        assert proc.returncode == 0, proc.stderr
        card = proc.stdout.strip()
        assert len(card) < 600, f'full 是索引页，不该塞正文：{len(card)} 字符'
        assert 'docs/ai' in card, f'full 索引页应指向 docs/ai：{card!r}'

    def test_default_level_is_compact(self):
        default = _run('ai', 'card')
        compact = _run('ai', 'card', '--level', 'compact')
        assert default.stdout == compact.stdout, 'ai card 默认层应为 compact'

    def test_snippets_still_works(self):
        """③ 只加 --level，`ai snippets` 保留。"""
        proc = _run('ai', 'snippets')
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip(), 'snippets 仍应输出片段库'


class TestFastPath:
    """⑤ --fast：只是省时间，error 判据必须与默认路径一致。"""

    def test_error_count_matches_default(self, syntax_error_file):
        default = _payload(_run('ai', 'check', syntax_error_file, '--json'))
        fast = _payload(_run('ai', 'check', syntax_error_file, '--json', '--fast'))
        default_errors = [d for d in default['diagnostics'] if d['severity'] == 'error']
        fast_errors = [d for d in fast['diagnostics'] if d['severity'] == 'error']
        assert len(fast_errors) == len(default_errors), \
            f'--fast 改变了 error 数量：默认 {len(default_errors)} / fast {len(fast_errors)}'
        assert fast['ok'] == default['ok']

    def test_fast_skips_type_and_run_stage(self, strict_file):
        """--fast 不跑类型检查/运行检查：日志里不应出现 [2/2] 运行测试。"""
        proc = _run('ai', 'check', strict_file, '--json', '--fast')
        assert proc.returncode == 0, proc.stderr
        assert '[2/2] 运行测试' not in proc.stderr, proc.stderr


class TestStrictGate:
    """② --strict 默认关：关时零 D2xx，开时 warning 且不改退出码。"""

    def test_strict_off_by_default(self, strict_file):
        payload = _json_of(_run('ai', 'check', strict_file, '--json'))
        assert payload['ok'] is True, payload
        assert not any(str(d['code']).startswith('D2') for d in payload['diagnostics']), \
            f'默认不应输出 D2xx：{[d["code"] for d in payload["diagnostics"]]}'

    def test_strict_on_emits_warnings_without_failing(self, strict_file):
        proc = _run('ai', 'check', strict_file, '--json', '--strict')
        assert proc.returncode == 0, proc.stderr
        payload = _json_of(proc)
        strict = [d for d in payload['diagnostics'] if str(d['code']).startswith('D2')]
        assert strict, '--strict 应输出 D2xx'
        assert all(d['severity'] == 'warning' for d in strict), strict
        assert payload['ok'] is True, 'warning 不应把 ok 拖成 False'

    def test_light_check_strict_text_warning(self, strict_file):
        plain = _run('check', strict_file, '--no-type-check')
        strict = _run('check', strict_file, '--no-type-check', '--strict')
        assert '非规范写法' not in plain.stdout, f'--strict 关时不得多出 warning 段：{plain.stdout}'
        assert '非规范写法' in strict.stdout, f'--strict 开时应输出 warning 段：{strict.stdout}'
        assert strict.returncode == plain.returncode, '--strict 不得改变退出码'
