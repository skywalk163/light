# -*- coding: utf-8 -*-
"""标准库速查表与 `stdlib/` 目录对拍门禁。

## 立项由来

`docs/stdlib.md` 长期写「109 个 .light 模块」，而 `ls stdlib/*.light` 实测 **119**；
速查表只有 101 行，还多出一个**根本不存在**的 `DNS` 行（全仓零引用）。
后果与 `test_文档内置名存在性.py` 是同一类：**文档教 AI 用一个不存在的东西**。

数字错会被 `tests/test_docs_status.py::test_module_count_matches_declared` 抓
（它读 STATUS.md 的 `顶层模块 N 个`），但**表格覆盖不全**没人管——
因为没有任何断言把「表格行」和「目录文件」联系起来。

## 本文件钉什么

1. 速查表里的模块名集合 **等于** `stdlib/*.light` 的 basename 集合（双向，既不许缺也不许多）。
2. 表头声明的数字与实算一致（防「表格补了但抬头没改」）。
3. 无重复行（重复会被集合比较掩盖）。

只解析 `docs/stdlib.md` 第一张速查表区（`## 模块速查表` 到下一个 `## `），
不碰后面「阶段1-13」的详细说明段。
"""
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
DOC = os.path.join(_ROOT, 'docs', 'stdlib.md')
STDLIB = os.path.join(_ROOT, 'stdlib')


def _doc_rows():
    """返回 (速查表模块名列表[保序], 表头声明数 or None)。"""
    with open(DOC, encoding='utf-8') as f:
        lines = f.read().splitlines()

    start = next((i for i, l in enumerate(lines) if l.startswith('## 模块速查表')), None)
    assert start is not None, '没找到 `## 模块速查表` 标题——表结构变了，本门禁已失效'
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))

    names = []
    for line in lines[start:end]:
        m = re.match(r'\|\s*`([^`]+)`\s*\|', line)
        if m:
            names.append(m.group(1).strip())

    head = lines[start]
    num = re.search(r'(\d+)\s*个', head)
    return names, (int(num.group(1)) if num else None)


def _stdlib_modules():
    return sorted(f[:-6] for f in os.listdir(STDLIB)
                  if f.endswith('.light') and os.path.isfile(os.path.join(STDLIB, f)))


def test_table_rows_are_unique():
    names, _ = _doc_rows()
    dup = sorted({n for n in names if names.count(n) > 1})
    assert not dup, f'速查表有重复模块行：{dup}'


def test_table_covers_every_module():
    """主判据：目录里每个模块都必须有一行，且每行都必须对应真实文件。"""
    names, _ = _doc_rows()
    table = set(names)
    disk = set(_stdlib_modules())

    missing = sorted(disk - table)
    phantom = sorted(table - disk)

    assert not missing, (
        f'`stdlib/` 里有 {len(missing)} 个模块没进速查表：{missing}\n'
        '（新增模块请同步 `docs/stdlib.md` 的模块表）')
    assert not phantom, (
        f'速查表里有 {len(phantom)} 行在 `stdlib/` 下没有对应 `.light` 文件：{phantom}\n'
        '（文档不许教不存在的东西——若是纯 .py 腿模块，请显式注明腿归属）')


def test_declared_count_matches_rows_and_disk():
    """表头数字 == 表格行数 == 目录模块数（三者必须一致）。"""
    names, declared = _doc_rows()
    disk = _stdlib_modules()
    assert declared is not None, '`## 模块速查表` 标题里没写「N 个」——声明数字缺失'
    assert declared == len(names), f'表头声明 {declared} 个，表格实际 {len(names)} 行'
    assert declared == len(disk), f'表头声明 {declared} 个，`stdlib/*.light` 实算 {len(disk)} 个'


def test_no_phantom_dns_row():
    """`DNS` 从来不是本仓的 stdlib 模块（历史误记）；防止再被"补"回去。"""
    names, _ = _doc_rows()
    assert 'DNS' not in names, (
        '`DNS` 不是 stdlib 模块（`ls stdlib/*.light | grep -i dns` 为空），'
        '不要写回速查表；需要 DNS 解析请用 `网络请求` 或 L4 引 Python 的 socket')
