# -*- coding: utf-8 -*-
"""T-0318：`light ai check --json` 的机器可读诊断契约。

全部用例都用 subprocess 跑**真实 CLI**，而不是直接调内部函数：外部 Agent
消费的是 stdout / stderr / 退出码这三样东西，只有走真进程才算数。

契约（与 `light ai check --help`、docs/AI编程指南.md 同一口径）：
  * `--json` 时 stdout 只有一个 JSON 对象（schema_version=1），前后无杂字；
  * 进度/日志走 stderr，绝不混进 stdout；
  * 退出码 0=无 error 级诊断，1=有 error 级诊断，2=用法/文件错误。

无 `--json` 时的文本输出是既有行为，本卡不改它；这里比对的是关键行基线
（见 ``TEXT_BASELINE_OK`` / ``TEXT_BASELINE_ERROR``）。基线内联在本文件里，
不额外新增 tests/fixtures 文件——本卡只允许改三个路径。
"""

import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_DIAGNOSTIC = 1
EXIT_USAGE = 2

# ── 样本源码 ──
# 干净文件：语法、类型都过
CLEAN_SOURCE = "设 甲 为 1\n打印(甲)\n"
# 语法错误：第 2 行第 5 列缺右括号（位置必须被如实报出来）
SYNTAX_ERROR_SOURCE = "设 甲 为 (\n打印(甲)\n"
# 运行期错误：第 2 行列表越界（--run 时才暴露）
RUNTIME_ERROR_SOURCE = "设 甲 为 [1, 2]\n打印(甲[9])\n"
# 触发后端感知的类定义
CLASS_SOURCE = '类 动物：\n    设 名字 为 ""\n'

# 词法错误：`&&` 触发 check 的纯文本路径（没有 ┌─ 边框块），位置在 2 行 10 列
LEXICAL_ERROR_SOURCE = "设 数 为 1\n如果 数 > 0 && 数 < 2：\n    打印(数)\n"

# ── 无 --json 时的关键行基线（只比关键行，避免环境差异）──
TEXT_BASELINE_OK = (
    '[1/2] 语法检查',
    '✓ 语法检查通过',
    '[2/2] 跳过运行检查（使用 --run 启用）',
)
TEXT_BASELINE_ERROR = (
    '[1/2] 语法检查',
    '✗ 语法检查失败',
)

REQUIRED_DIAGNOSTIC_FIELDS = (
    'code', 'severity', 'stage', 'line', 'column',
    'message', 'hint', 'fixes', 'candidates', 'provisional',
)

# stdout 上不许出现的文本进度/emoji（JSON 里的中文不算）
STDOUT_FORBIDDEN = ('[0/2]', '[1/2]', '[2/2]', '✓', '✗', '→', '📄', '✅', '❌', '⚠')


def _write(directory, name, source):
    path = os.path.join(str(directory), name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(source)
    return path


def _run_ai_check(*argv):
    """跑真实 CLI，返回 CompletedProcess（stdout/stderr 都是 utf-8 解码后的文本）。"""
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'cli.light', 'ai', 'check', *argv],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=REPO_ROOT, timeout=180,
    )


def _json_of(proc):
    """stdout 必须能直接 json.loads —— 不剥前缀、不找子串。"""
    payload = json.loads(proc.stdout)
    assert isinstance(payload, dict), f'stdout 顶层应为对象，实际 {type(payload).__name__}'
    return payload


# ── 样本文件（module 级，避免每个用例重复落盘）──
@pytest.fixture(scope='module')
def clean_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('ai_check'), 'clean.light', CLEAN_SOURCE)


@pytest.fixture(scope='module')
def syntax_error_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('ai_check'), 'bad.light', SYNTAX_ERROR_SOURCE)


@pytest.fixture(scope='module')
def runtime_error_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('ai_check'), 'rt.light', RUNTIME_ERROR_SOURCE)


@pytest.fixture(scope='module')
def class_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('ai_check'), 'cls.light', CLASS_SOURCE)


@pytest.fixture(scope='module')
def missing_path(tmp_path_factory):
    return os.path.join(str(tmp_path_factory.mktemp('ai_check')), 'nope.light')


# ── 复用同一批真实进程结果 ──
@pytest.fixture(scope='module')
def clean_json(clean_file):
    return _run_ai_check(clean_file, '--json')


@pytest.fixture(scope='module')
def syntax_error_json(syntax_error_file):
    return _run_ai_check(syntax_error_file, '--json')


@pytest.fixture(scope='module')
def missing_json(missing_path):
    return _run_ai_check(missing_path, '--json')


@pytest.fixture(scope='module')
def runtime_error_json(runtime_error_file):
    return _run_ai_check(runtime_error_file, '--json', '--run')


@pytest.fixture(scope='module')
def class_json(class_file):
    return _run_ai_check(class_file, '--json')


@pytest.fixture(scope='module')
def lexical_error_file(tmp_path_factory):
    return _write(tmp_path_factory.mktemp('ai_check'), 'lex.light', LEXICAL_ERROR_SOURCE)


@pytest.fixture(scope='module')
def lexical_json(lexical_error_file):
    return _run_ai_check(lexical_error_file, '--json')


class TestExitCodeContract:
    """三种退出码各一例（0 / 1 / 2），外加 --run 失败也归 1。"""

    def test_clean_file_exits_0(self, clean_json):
        assert clean_json.returncode == EXIT_OK, clean_json.stderr

    def test_error_file_exits_1(self, syntax_error_json):
        assert syntax_error_json.returncode == EXIT_DIAGNOSTIC, syntax_error_json.stderr

    def test_missing_file_exits_2(self, missing_json):
        assert missing_json.returncode == EXIT_USAGE, missing_json.stderr

    def test_run_failure_exits_1(self, runtime_error_json):
        assert runtime_error_json.returncode == EXIT_DIAGNOSTIC, runtime_error_json.stderr


class TestStdoutIsSingleJsonObject:
    """stdout 只有 JSON 本体，没有进度、没有 emoji、没有第二行。"""

    def test_stdout_parses_directly(self, syntax_error_json):
        payload = _json_of(syntax_error_json)
        assert payload['schema_version'] == SCHEMA_VERSION

    def test_stdout_has_no_extra_text(self, syntax_error_json):
        stdout = syntax_error_json.stdout
        assert stdout.strip().startswith('{') and stdout.strip().endswith('}')
        assert len([line for line in stdout.splitlines() if line.strip()]) == 1, \
            f'stdout 应为单行 JSON，实际:\n{stdout}'

    def test_stdout_has_no_progress_or_emoji(self, syntax_error_json):
        stdout = syntax_error_json.stdout
        for token in STDOUT_FORBIDDEN:
            assert token not in stdout, f'stdout 不应出现进度/emoji「{token}」:\n{stdout}'

    def test_clean_payload_shape(self, clean_json):
        payload = _json_of(clean_json)
        assert payload['ok'] is True
        assert payload['file'].endswith('clean.light')
        assert payload['backend_hints'] == []
        assert payload['diagnostics'] == []
        assert isinstance(payload['duration_ms'], int) and payload['duration_ms'] >= 0


class TestDiagnosticFields:
    """每条诊断的必备字段与类型；位置是真实行列，未知才为 0。"""

    def test_required_fields_and_types(self, syntax_error_json):
        payload = _json_of(syntax_error_json)
        assert payload['ok'] is False
        assert payload['diagnostics'], '语法错误文件不应得到空诊断'
        for diag in payload['diagnostics']:
            for field in REQUIRED_DIAGNOSTIC_FIELDS:
                assert field in diag, f'诊断缺少字段 {field}: {diag}'
            assert isinstance(diag['code'], str) and re.match(r'^L\d{4}$', diag['code']), diag
            assert diag['severity'] in ('error', 'warning', 'info'), diag
            assert isinstance(diag['stage'], str) and diag['stage'], diag
            assert isinstance(diag['line'], int) and diag['line'] >= 0, diag
            assert isinstance(diag['column'], int) and diag['column'] >= 0, diag
            assert isinstance(diag['message'], str) and diag['message'], diag
            assert isinstance(diag['hint'], str), diag
            assert isinstance(diag['fixes'], list) and all(isinstance(x, str) for x in diag['fixes']), diag
            assert len(diag['fixes']) <= 3, diag
            assert isinstance(diag['candidates'], list), diag
            assert isinstance(diag['provisional'], bool), diag

    def test_error_position_is_real(self, syntax_error_json):
        payload = _json_of(syntax_error_json)
        diag = payload['diagnostics'][0]
        assert diag['stage'] == '语法检查', diag
        assert diag['line'] == 2, f'错误在第 2 行，实际 {diag["line"]}'
        assert diag['column'] == 5, f'错误在第 5 列，实际 {diag["column"]}'

    def test_unknown_position_stays_zero(self, missing_json):
        """位置未知就写 0，不许编造行号。"""
        payload = _json_of(missing_json)
        for diag in payload['diagnostics']:
            assert diag['line'] == 0 and diag['column'] == 0, diag


class TestBackendHints:
    def test_class_keyword_produces_hint(self, class_json):
        payload = _json_of(class_json)
        assert payload['backend_hints'], '类定义应触发后端提示'
        hint = payload['backend_hints'][0]
        assert set(hint) == {'keyword', 'desc', 'suggestion'}
        assert hint['keyword'] == '类'
        assert 'llvm-typed' in hint['suggestion']

    def test_clean_file_has_no_hint(self, clean_json):
        assert _json_of(clean_json)['backend_hints'] == []


class TestRunStage:
    """`--json --run`：运行失败必须变成 stage="运行" 的诊断，而不是 traceback。"""

    def test_run_failure_becomes_diagnostic(self, runtime_error_json):
        payload = _json_of(runtime_error_json)
        assert payload['ok'] is False
        stages = [diag['stage'] for diag in payload['diagnostics']]
        assert '运行' in stages, f'运行失败应落在 stage="运行"，实际 {stages}'
        runtime_diag = next(d for d in payload['diagnostics'] if d['stage'] == '运行')
        assert runtime_diag['line'] == 2, runtime_diag
        assert 'Traceback' not in runtime_error_json.stdout

    def test_progress_goes_to_stderr(self, runtime_error_json):
        stderr = runtime_error_json.stderr
        stdout = runtime_error_json.stdout
        assert '[1/2] 语法检查' in stderr, stderr
        assert '[2/2] 运行测试' in stderr, stderr
        assert '[1/2]' not in stdout and '[2/2]' not in stdout, stdout


class TestPlainTextFallback:
    """`&&` 这类词法错误走纯文本路径（check 不打 ┌─ 块），位置与归因不能丢。"""

    def test_lexical_error_has_real_position(self, lexical_json):
        assert lexical_json.returncode == EXIT_DIAGNOSTIC, lexical_json.stderr
        payload = _json_of(lexical_json)
        diag = payload['diagnostics'][0]
        assert diag['stage'] == '语法检查', diag
        assert diag['line'] == 2, f'词法错误在第 2 行，实际 {diag["line"]}'
        assert diag['column'] == 10, f'词法错误在第 10 列，实际 {diag["column"]}'
        assert '词法' in diag['message'], diag['message']

    def test_noise_lines_are_not_used_as_message(self, lexical_json):
        """兜底不得把 `📄 检查文件 / 总行数` 这种检查头当成诊断正文。"""
        diag = _json_of(lexical_json)['diagnostics'][0]
        for noise in ('📄', '检查文件', '总行数', '代码行', '注释行'):
            assert noise not in diag['message'], f'诊断正文混入检查头「{noise}」: {diag["message"]}'


class TestTextPathUnchanged:
    """无 `--json` 时的文本输出与退出码维持既有行为。"""

    def test_clean_text_output(self, clean_file):
        proc = _run_ai_check(clean_file)
        assert proc.returncode == EXIT_OK, proc.stderr
        for line in TEXT_BASELINE_OK:
            assert line in proc.stdout, f'缺少基线行「{line}」:\n{proc.stdout}'
        assert not proc.stdout.strip().startswith('{'), '无 --json 时不应输出 JSON'

    def test_error_text_output(self, syntax_error_file):
        proc = _run_ai_check(syntax_error_file)
        for line in TEXT_BASELINE_ERROR:
            assert line in proc.stdout, f'缺少基线行「{line}」:\n{proc.stdout}'

    def test_missing_file_text_output(self, missing_path):
        """老行为：打印「文件不存在」并以 0 退出（本卡不改它）。"""
        proc = _run_ai_check(missing_path)
        assert proc.returncode == EXIT_OK, proc.stderr
        assert '文件不存在' in proc.stdout