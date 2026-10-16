# -*- coding: utf-8 -*-
"""R153 · `tests/` 顶层最小门禁：任何 collection-time ImportError 必须阻断合并。

为什么要有这道门
----------------
`tests/` 顶层（155 个 `test_*.py`）**长期不在任何门禁里** —— 常规回归只跑 `tests/unit/`。
后果是这类缺陷能静默存活很久：

    tests/test_stdlib_phase4.py:307   from 编码解码 import ... 字符集转换为字符串 ...
    
该名字根本不存在（`ImportError`），但没人知道 —— 顶层从不被执行，它就从不红。
R152-E1 是靠**偶然**写静态扫描才挖出来的。业主裁定：「这种静默 ImportError 不应再靠偶然挖出」。

本门做什么 / 不做什么
----------------------
* **做**：`pytest --collect-only` 全量收集 `tests/` 顶层所有 `test_*.py`，rc != 0 即红。
  挡住的是**模块级** ImportError / 语法错 / 收集期异常 —— 这是「新增导入错误阻断合并」的第一道。
* **不做（明确边界）**：collect-only **不执行用例**，因此挡不住**函数内** import
  （上面那条 `字符集转换为字符串` 就写在 `def test_...` 里）。那一档由 R152-E1 的
  `tests/unit/test_R152_魔数only出口对等.py` 静态层覆盖 —— 两道门分工，不要互相替代。

  ⚠️ 还有一个更深的洞，本门**也挡不住**，登记在此备查：
  函数内 ImportError 若发生在 `pytest.mark.xfail(strict=False)` 用例里，会被**吞成 xfail**
  （`test_stdlib_phase4.py:303` 正是如此），即使顶层真跑起来也不红。
  要堵这一档需要「xfail 用例不得因 ImportError 而 xfail」的专项，属下一档门禁，本轮不做。

欠账清单契约（业主裁定）
------------------------
现有欠账允许短期显式 skip，但**必须带 issue 和到期，不能静默**：
`_已知欠账[文件名] = (理由, issue, 到期日)`；到期日一过，skip 自动变红，逼人销账。
当前**零欠账**（155/155 全可 collect）。清单留空但机制保留 —— 见 `test_欠账机制有牙`。

耗时
----
一次批量 collect 155 个文件本机实测 ~159s，远超 pyproject 全局 `--timeout=60`。
按 R152-C2 同一纪律：**逐例提限，不动全局**（动全局会掩盖真挂死）。
"""
import datetime
import glob
import os
import re
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _顶层测试文件():
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(_REPO, 'tests', 'test_*.py')))


# ── 已知欠账清单（当前为空：155/155 全可 collect）────────────────────────────
# 新增欠账时按此格式登记，缺任一字段或过期都会红（见 test_欠账机制有牙）：
#   'tests/test_xxx.py': ('一句话说明为什么现在 collect 不过',
#                         'ISSUE 编号或任务书条目（如 _R153_是空语义对齐清单.md §x）',
#                         '2026-12-31'),
_已知欠账 = {}


def _检查欠账条目(条目):
    """返回 None 表示条目合规；否则返回不合规原因（用于断言 + 反跑）。"""
    理由, issue, 到期 = 条目
    if not (理由 or '').strip():
        return '欠账缺「理由」——不许静默 skip'
    if not (issue or '').strip():
        return '欠账缺「issue/来源」——不许无出处 skip'
    try:
        到期日 = datetime.date.fromisoformat(到期)
    except (TypeError, ValueError):
        return '欠账到期日不是 ISO 日期（YYYY-MM-DD）：%r' % (到期,)
    if 到期日 < datetime.date.today():
        return '欠账已于 %s 到期，必须销账或重订期（理由：%s）' % (到期, 理由)
    return None


@pytest.mark.timeout(600)
def test_顶层测试文件全部可collect():
    """155 个顶层 test_*.py 必须全部可收集；rc != 0 即红，并定位到具体文件。"""
    文件们 = _顶层测试文件()
    assert 文件们, 'tests/ 顶层没扫到任何 test_*.py —— 扫描逻辑坏了'

    # 先跳过登记在册的欠账（带理由/issue/到期，到期自动转红）
    待查 = []
    for f in 文件们:
        条目 = _已知欠账.get('tests/' + f)
        if 条目 is None:
            待查.append('tests/' + f)
            continue
        因 = _检查欠账条目(条目)
        assert 因 is None, 'tests/%s 的欠账登记不合规：%s' % (f, 因)

    cmd = [sys.executable, '-m', 'pytest', '--collect-only', '-q',
           '-p', 'no:cacheprovider'] + 待查
    r = subprocess.run(cmd, cwd=_REPO, capture_output=True, timeout=900)
    if r.returncode == 0:
        return

    out = (r.stdout.decode('utf-8', 'replace') + '\n' + r.stderr.decode('utf-8', 'replace'))
    # 定位：pytest 收集失败会打 `ERROR tests/x.py` 或 `ERROR collecting tests/x.py`
    坏 = sorted(set(re.findall(r'ERROR (?:collecting )?(tests[/\\][^\s:]+\.py)', out)))
    未登记 = [b for b in 坏 if b.replace('\\', '/') not in _已知欠账]
    raise AssertionError(
        'tests/ 顶层有 %d 个文件 collect 失败（rc=%d）：\n  %s\n'
        '未登记欠账的文件：%s\n'
        '—— 要么修好，要么按 _已知欠账 格式登记（理由 + issue + 到期），不许放着不管。\n'
        '%s' % (len(坏), r.returncode, '\n  '.join(坏) or '(未能从输出定位文件)',
                未登记 or '(无)', out[-1500:]))


def test_欠账清单条目字段完整():
    for 路径, 条目 in _已知欠账.items():
        assert len(条目) == 3, '%s 欠账条目必须是 (理由, issue, 到期) 三元组' % 路径
        assert _检查欠账条目(条目) is None, '%s 欠账登记不合规：%s' % (路径, _检查欠账条目(条目))


def test_欠账清单不过期():
    过期 = {p: _检查欠账条目(e) for p, e in _已知欠账.items() if _检查欠账条目(e)}
    assert not 过期, '以下欠账已过期，必须销账或重订期：%s' % 过期


def test_欠账机制有牙():
    """反跑：清单为空时门也不能是摆设 —— 四种坏登记都必须被判不合规。"""
    # 过期 → 必须红
    assert _检查欠账条目(('理由', 'ISSUE-1', '2020-01-01')) is not None
    # 缺理由 / 缺 issue → 必须红（不许静默 skip）
    assert _检查欠账条目(('', 'ISSUE-1', '2999-01-01')) is not None
    assert _检查欠账条目(('理由', '', '2999-01-01')) is not None
    # 合规 → 放行
    assert _检查欠账条目(('理由', 'ISSUE-1', '2999-01-01')) is None


def test_门禁自身在扫描面内():
    """本文件自己也是顶层 test_*.py，必须在扫描面里（否则门会漏掉自己）。"""
    assert os.path.basename(__file__) in _顶层测试文件()


def test_扫描面覆盖顶层全部():
    """顶层 test_*.py 全在扫描面；不递归子目录（tests/unit 等另有门禁）。"""
    面 = set(_顶层测试文件())
    assert 'test_R153_顶层collect门禁.py' in 面
    # 顶层文件里不应混入子目录路径
    assert all('/' not in f and '\\' not in f for f in 面)
