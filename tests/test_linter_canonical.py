# -*- coding: utf-8 -*-
"""R222-D / T-0380：归一通道（--canonical）测试。

覆盖：
- 逐类归一结果与 `code`（L5001–L5004）；
- 幂等：canonicalize 两次结果相同；
- 有歧义的 `等于` 只进 skipped，不硬猜；
- 字符串/注释、`函数1`/`相加` 这类词内别名不被误改；
- benchmarks/programs/ 真实文件 `--apply` 后 AST 指纹不变；
- `--canonical` 不写回时文件内容与 mtime 不变；
- `--help` 能看到 `--canonical`，light.toml 的 canonical 配置生效。
"""

import dataclasses
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from linter.canonical import canonicalize  # noqa: E402


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _dump(node):
    """把 AST 递归转成可比较的普通结构，忽略位置字段。"""
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return {
            '__type__': type(node).__name__,
            **{
                f.name: _dump(getattr(node, f.name))
                for f in dataclasses.fields(node)
                if f.name not in ('line', 'column')
            },
        }
    if isinstance(node, (list, tuple)):
        return [_dump(x) for x in node]
    if isinstance(node, dict):
        return {str(k): _dump(v) for k, v in node.items()}
    if isinstance(node, (str, int, float, bool)) or node is None:
        return node
    return repr(node)


def _ast_fingerprint(source: str):
    """AST 指纹：同一语义的不同写法必须得到同一结果。"""
    from light_parser_v3 import LightParser
    return _dump(LightParser().parse(source))


def _run_cli(args, cwd=ROOT):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(SRC_DIR)
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'src.linter.cli', *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        # 子进程被 `-X utf8` 强制用 UTF-8 输出，父进程也必须按 UTF-8 解码：
        # 不显式给 encoding 时 subprocess 用 locale 默认（Windows = GBK），
        # 中文输出会在读线程里抛 UnicodeDecodeError，proc.stdout 变成 None，
        # 断言报成 TypeError —— 真实差异被掩盖（T-0391 的假红）。
        encoding='utf-8',
        errors='replace',
    )


BENCHMARKS = sorted((ROOT / 'benchmarks' / 'programs').glob('*.light'))


# ---------------------------------------------------------------------------
# 逐类归一
# ---------------------------------------------------------------------------

SAMPLE = (
    "// 注释里的（全角）：不动\n"
    "函数 演示（甲，乙）：\n"
    "    返回 甲 加上 乙 。   \n"
)


def test_canonical_forms_and_codes():
    new, edits, skipped = canonicalize(SAMPLE, style='工程体')

    # 标点（L5001）
    assert '段落 演示(甲,乙):' in new
    assert '返回 甲 + 乙 ;' in new  # 运算符（L5002）+ 行尾空白（L5004）
    # 注释内部原样保留
    assert '// 注释里的（全角）：不动' in new
    # 尾随空白已清掉
    assert '返回 甲 + 乙 ;\n' in new

    codes = {e.code for e in edits}
    assert codes == {'L5001', 'L5002', 'L5003', 'L5004'}
    assert skipped == []


def test_canonical_is_idempotent():
    once, _, _ = canonicalize(SAMPLE, style='工程体')
    twice, edits2, skipped2 = canonicalize(once, style='工程体')
    assert twice == once
    assert edits2 == []


def test_text_inside_strings_is_untouched():
    src = '打印 "全角：标点（不动）。"\n'
    new, edits, skipped = canonicalize(src)
    assert new == src
    assert edits == []


def test_identifier_prefix_is_not_rewritten():
    # `函数1` 是标识符，不是关键字 函数 + 1；`相加` 也不是运算符 加。
    src = "段落 函数1：\n    返回 1\n\n段落 相加(甲, 乙)：\n    返回 甲 加 乙\n"
    new, _, _ = canonicalize(src)
    assert '函数1' in new
    assert '段落 相加(甲, 乙)' in new
    # 只有独立成词的 `加` 会被归一
    assert '返回 甲 + 乙' in new


def test_operator_like_function_name_is_not_rewritten():
    src = "段落 加(甲, 乙)：\n    返回 甲\n"
    new, edits, _ = canonicalize(src)
    assert '段落 加(甲, 乙)' in new
    assert not [e for e in edits if e.code == 'L5002']


def test_ambiguous_equal_is_skipped_not_rewritten():
    src = "如果 甲 等于 乙 那么：\n    返回 真\n"
    new, edits, skipped = canonicalize(src)
    assert '等于' in new  # 没有硬猜成 ==
    assert any(s.text == '等于' and s.code == 'L5002' for s in skipped)


def test_assignment_equal_is_not_reported_as_ambiguous():
    src = "设 甲 等于 1\n"
    new, edits, skipped = canonicalize(src)
    assert new == src
    assert skipped == []


def test_learning_style_uses_single_char_function_keyword():
    src = "段落 演示(甲)：\n    返回 甲\n"
    new, edits, _ = canonicalize(src, style='教学体')
    assert '段 演示(甲):' in new
    assert any(e.code == 'L5003' and e.after == '段' for e in edits)


# ---------------------------------------------------------------------------
# benchmarks 真实文件：--apply 后语义不变
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('src_path', BENCHMARKS, ids=lambda p: p.name)
def test_apply_keeps_ast_fingerprint(src_path, tmp_path):
    dst = tmp_path / src_path.name
    shutil.copyfile(src_path, dst)

    before = _ast_fingerprint(dst.read_text(encoding='utf-8'))
    proc = _run_cli(['--canonical', '--apply', str(dst)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = _ast_fingerprint(dst.read_text(encoding='utf-8'))

    assert before == after


def test_report_only_keeps_file_and_mtime(tmp_path):
    dst = tmp_path / 'sample.light'
    text = '设 甲 为 1。   \n'
    dst.write_text(text, encoding='utf-8')
    mtime_before = dst.stat().st_mtime_ns

    proc = _run_cli(['--canonical', '--dry-run', str(dst)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'L5001' in proc.stdout

    assert dst.read_text(encoding='utf-8') == text
    assert dst.stat().st_mtime_ns == mtime_before


def test_cli_help_lists_canonical():
    proc = _run_cli(['--help'])
    assert proc.returncode == 0
    assert '--canonical' in proc.stdout
    assert '--apply' in proc.stdout


def test_light_toml_locks_style_and_canonical_mode():
    text = (ROOT / 'light.toml').read_text(encoding='utf-8')
    assert 'style = "工程体"' in text

    tomllib = pytest.importorskip('tomllib')
    cfg = tomllib.loads(text)['linter']
    assert cfg['style'] == '工程体'
    assert cfg['canonical'] == '报告'
