# -*- coding: utf-8 -*-
"""
R96-KI-01 回归测试：格式化器不得破坏合法代码（R97 修复验收）

验收标准（见 docs/known-issues/R96-formatter-semantic-break.md）：
  对任意 examples/ 与 stdlib/ 下的 .light 执行 `light fmt` 后，
  `light check` 的通过率与格式化前完全一致（允许空行/缩进规范化，禁止语义改变）。

本测试不依赖真实编译器，而是通过**结构不变量**直接证明"无语义改变"，
这在 光明 这种缩进敏感语言上比抽样跑编译器更强：

  光明 的块结构完全由「每行缩进 + 行内 token」决定。安全子集格式化器
  对二者逐行精确保留（仅 rstrip 行尾空白），因此格式化前后任意文件的
  「非空行的(缩进宽度, 去尾空白内容)序列」必然逐条相等 ⇒ 解析结果必然一致。

覆盖：
  1. R96-KI-01 复现用例 examples/_test_nested_closure.light（含 CLI 写回路径，
     验证 CRLF 还原不破坏）；
  2. examples/ 全量 + stdlib/ 抽样：解析保留不变量；
  3. 幂等性；
  4. 绝不给 `返回/抛/跳/过/终` 等语句错误补冒号。
"""

import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formatter.light_formatter import LightFormatter, format_code
from formatter import run_formatter  # CLI 入口（含 CRLF 还原）

EXAMPLES_DIR = os.path.join(ROOT, 'examples')
STDLIB_DIR = os.path.join(ROOT, 'stdlib')

REPRO_EXAMPLE = os.path.join(EXAMPLES_DIR, '_test_nested_closure.light')

# 单字关键字曾被错误当作"需要冒号"的前缀（R96-KI-01 根因）
BAD_COLON_PREFIXES = ('返', '跳', '过', '抛', '终')


def _content_lines(text):
    """返回 [(缩进宽度, 去尾空白内容), ...]，仅非空行。"""
    out = []
    for line in text.split('\n'):
        s = line.rstrip()
        if s == '':
            continue
        indent = len(line) - len(line.lstrip())
        out.append((indent, s))
    return out


def _find_light_files(directory, cap=None):
    result = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for name in files:
            if name.endswith('.light'):
                result.append(os.path.join(root, name))
    result.sort()
    if cap is not None and len(result) > cap:
        result = result[:cap]
    return result


@pytest.fixture(scope='module')
def fmt():
    return LightFormatter(indent_size=4, max_line_length=80)


# ======================================================================
# 1. R96-KI-01 复现用例
# ======================================================================
def test_repro_example_preserves_parse(fmt):
    assert os.path.isfile(REPRO_EXAMPLE), "复现用例缺失: %s" % REPRO_EXAMPLE
    with open(REPRO_EXAMPLE, 'r', encoding='utf-8') as f:
        source = f.read()

    formatted = format_code(source)

    # 不变量：非空行(缩进, 内容)序列逐条相等 ⇒ 解析一致
    assert _content_lines(source) == _content_lines(formatted), \
        "复现用例格式化后解析结构改变（R96-KI-01 复发！）"

    # 绝不补冒号：'返回 x + y' 不能被改成 '返回 x + y：'
    assert '返回 x + y：' not in formatted
    assert '返回 x + y:' not in formatted
    # 原有合法冒号（段落定义）必须保留
    assert '段落 外层(x):' in formatted
    assert '段落 内层(y):' in formatted


def test_repro_example_via_cli_run_formatter(fmt):
    """走 CLI 写回路径（含 CRLF 还原），确认不会产生破坏性改写。"""
    assert os.path.isfile(REPRO_EXAMPLE)
    with open(REPRO_EXAMPLE, 'rb') as f:
        raw = f.read()
    crlf = b'\r\n' in raw
    source = raw.decode('utf-8')

    tmp = tempfile.NamedTemporaryFile(suffix='.light', delete=False, mode='wb')
    try:
        tmp.write(raw)
        tmp.close()
        rc = run_formatter(tmp.name, check_only=False)
        assert rc == 0, "run_formatter 返回非 0: %r" % rc
        with open(tmp.name, 'rb') as f:
            out_raw = f.read()
        out = out_raw.decode('utf-8')
        # CRLF 风格应被还原（不误伤整工作树）
        if crlf:
            assert b'\r\n' in out_raw, "run_formatter 未还原原始 CRLF 风格"
        # 解析保留不变量
        assert _content_lines(source) == _content_lines(out), \
            "CLI 写回后解析结构改变（R96-KI-01 复发！）"
        assert '返回 x + y：' not in out
        assert '返回 x + y:' not in out
    finally:
        os.unlink(tmp.name)


# ======================================================================
# 2. examples/ 全量 + stdlib/ 抽样：解析保留不变量
# ======================================================================
def test_examples_corpus_preserves_parse(fmt):
    files = _find_light_files(EXAMPLES_DIR)
    assert files, "examples/ 下未找到 .light 文件"
    failed = []
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                src = f.read()
        except Exception as exc:  # 个别文件编码异常不应拖累整体
            failed.append((fp, 'read: %s' % exc))
            continue
        out = format_code(src)
        if _content_lines(src) != _content_lines(out):
            failed.append((fp, 'parse-structure changed'))
        # 冒号防护
        for ln in out.split('\n'):
            s = ln.rstrip()
            for p in BAD_COLON_PREFIXES:
                if s.startswith(p) and (s.endswith('：') or s.endswith(':')):
                    # 允许形如 '返回:' 只在确实是块首的情形；光明 中 返/跳/过/抛/终
                    # 作为语句关键字不应带冒号。这里仅记录可疑项。
                    failed.append((fp, 'suspicious colon: %s' % s))
                    break
    assert not failed, "以下文件格式化后解析/冒号异常:\n" + "\n".join(
        "  %s -> %s" % (f, m) for f, m in failed)


def test_stdlib_corpus_preserves_parse(fmt):
    files = _find_light_files(STDLIB_DIR, cap=600)
    assert files, "stdlib/ 下未找到 .light 文件"
    failed = []
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                src = f.read()
        except Exception as exc:
            failed.append((fp, 'read: %s' % exc))
            continue
        out = format_code(src)
        if _content_lines(src) != _content_lines(out):
            failed.append((fp, 'parse-structure changed'))
    assert not failed, "stdlib 以下文件格式化后解析结构改变:\n" + "\n".join(
        "  %s -> %s" % (f, m) for f, m in failed)


# ======================================================================
# 3. 幂等性
# ======================================================================
def test_idempotent_on_examples(fmt):
    files = _find_light_files(EXAMPLES_DIR)
    for fp in files:
        with open(fp, 'r', encoding='utf-8') as f:
            src = f.read()
        once = format_code(src)
        twice = format_code(once)
        assert once == twice, "格式化非幂等: %s" % fp


# ======================================================================
# 4. 冒号防护（单元级）
# ======================================================================
def test_no_spurious_colon_on_statement_keywords(fmt):
    snippets = [
        "返回 x + y\n",
        "抛 异常(\"err\")\n",
        "跳\n",
        "过\n",
        "终\n",
    ]
    for snip in snippets:
        out = format_code(snip)
        s = out.rstrip()
        for p in BAD_COLON_PREFIXES:
            if s.startswith(p):
                assert not (s.endswith('：') or s.endswith(':')), \
                    "语句关键字被错误补冒号: %r" % s
