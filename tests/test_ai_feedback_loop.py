# -*- coding: utf-8 -*-
"""T-0326：check → 归档 → 速查卡 的反馈闭环（端到端，subprocess 真跑 CLI）。

平台说明：全部用 Python 标准库，不用 head/grep/awk、`!`、`$()`；
「归档目录不可写」用「环境变量指向一个普通文件」模拟，Windows / FreeBSD 都成立。
"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOKEN = 'abcdef0123456789abcdef0123456789abcdef01'
PROBE_PATH = 'C:/Users/skywalk/secret/bad.light'
# 第 2 行尾随注释放绝对路径 + 长 token，验证归档脱敏；整份仍是 1 条语法错误。
BAD_SOURCE = (
    '设 甲 为 (\n'
    f'打印(甲)  # 探针 {TOKEN} {PROBE_PATH}\n'
)
REQUIRED_FIELDS = (
    'ts', 'last_seen', 'code', 'message', 'hint', 'fixes',
    'source_snippet', 'source_hash', 'lang_level', 'backend',
    'light_version', 'hits',
)


def _run(argv, env):
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'cli.light', *argv],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=REPO_ROOT, env=env, timeout=180,
    )


def _env(corpus_dir, **extra):
    env = dict(os.environ)
    env['LIGHT_ERROR_CORPUS_DIR'] = os.fspath(corpus_dir)
    env.pop('LIGHT_ERROR_CORPUS', None)  # 不受宿主环境残留影响
    env.update({key: str(value) for key, value in extra.items()})
    return env


def _bad_file(directory):
    path = os.path.join(str(directory), 'bad.light')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(BAD_SOURCE)
    return path


def _jsonl_rows(corpus_dir):
    if not os.path.isdir(str(corpus_dir)):
        return []
    rows = []
    for name in sorted(os.listdir(str(corpus_dir))):
        if not name.endswith('.jsonl'):
            continue
        with open(os.path.join(str(corpus_dir), name), encoding='utf-8') as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def _index_hits(corpus_dir):
    with open(os.path.join(str(corpus_dir), 'index.json'), encoding='utf-8') as handle:
        index = json.load(handle)
    return [entry['hits'] for entry in index['entries'].values()]


def _check(bad, corpus_dir, env=None, flags=()):
    return _run(['ai', 'check', bad, '--json', *flags],
                env or _env(corpus_dir))


def test_check_archives_one_sanitized_record(tmp_path):
    bad = _bad_file(tmp_path)
    corpus = tmp_path / 'corpus'
    proc = _check(bad, corpus)
    assert proc.returncode == 1, proc.stderr
    payload = json.loads(proc.stdout)
    assert any(d['severity'] == 'error' for d in payload['diagnostics'])

    rows = _jsonl_rows(corpus)
    assert len(rows) == 1, f'应落 1 条记录，实得 {len(rows)}'
    record = rows[0]
    for field in REQUIRED_FIELDS:
        assert field in record, f'缺字段 {field}'
    assert record['hits'] == 1
    assert record['source_hash']

    blob = json.dumps(record, ensure_ascii=False)
    assert TOKEN not in blob and '***' in blob            # 32 位以上疑似 token 打码
    assert 'C:/Users/skywalk/secret' not in blob           # 绝对路径只留 basename
    assert 'bad.light' in record['source_snippet']
    assert str(tmp_path) not in blob                       # 不含本机临时绝对路径


def test_identical_error_bumps_hits_without_new_row(tmp_path):
    bad = _bad_file(tmp_path)
    corpus = tmp_path / 'corpus'
    env = _env(corpus)
    first = _run(['ai', 'check', bad, '--json'], env)
    second = _run(['ai', 'check', bad, '--json'], env)
    assert first.returncode == second.returncode == 1
    assert len(_jsonl_rows(corpus)) == 1, '重复命中不应新增 JSONL 行'
    assert _index_hits(corpus) == [2]


def test_off_switch_and_no_corpus_flag_do_not_write(tmp_path):
    cases = (
        ('env_off', (), {'LIGHT_ERROR_CORPUS': 'off'}),
        ('flag_no_corpus', ('--no-corpus',), {}),
    )
    for name, flags, extra in cases:
        case = tmp_path / name
        case.mkdir()
        bad = _bad_file(case)
        corpus = case / 'corpus'
        proc = _check(bad, corpus, _env(corpus, **extra), flags)
        assert proc.returncode == 1, (name, proc.stderr)
        assert _jsonl_rows(corpus) == [], f'{name} 仍写了盘'
        assert not os.path.exists(os.path.join(str(corpus), 'index.json'))


def test_card_rank_pitfalls_shows_code_and_json_shape(tmp_path):
    bad = _bad_file(tmp_path)
    corpus = tmp_path / 'corpus'
    env = _env(corpus)
    assert _run(['ai', 'check', bad, '--json'], env).returncode == 1
    code = _jsonl_rows(corpus)[0]['code']

    card = _run(['ai', 'card', '--rank-pitfalls'], env)
    assert card.returncode == 0, card.stderr
    top = '\n'.join(card.stdout.splitlines()[:10])
    assert code in top, f'顶部 10 行未出现 {code}：\n{top}'
    assert 'STATUS.md' in top, '速查卡顶部未引用单一状态入口'

    structured = _run(['ai', 'card', '--rank-pitfalls', '--json'], env)
    assert structured.returncode == 0, structured.stderr
    data = json.loads(structured.stdout)
    assert set(data) == {'ranked', 'card'}
    assert any(item['code'] == code for item in data['ranked'])


def test_unwritable_corpus_does_not_change_exit_code(tmp_path):
    bad = _bad_file(tmp_path)
    blocker = tmp_path / 'not_a_dir'
    blocker.write_text('x', encoding='utf-8')  # 目录路径指向普通文件 → makedirs 必失败
    proc = _check(bad, blocker, _env(blocker))
    assert proc.returncode == 1, proc.stderr
    assert '[报错归档]' in proc.stderr and '失败' in proc.stderr
    assert json.loads(proc.stdout)['ok'] is False  # stdout 仍是可消费的 JSON
