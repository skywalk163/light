# -*- coding: utf-8 -*-
"""R227 / T-0447：内存取证采集器的判据——快照字段齐全、统计可手算对拍、三态可构造。

本文件是 T-0447 的验收判据，配套工具是 `tools/r225_mem_capture.py`（取证采集器，
只采数不改编译器行为）。任务卡要求全文件 < 60s，夹具全部 tmp_path 现生成
（不依赖 lightharness、外网、目录残留），不许用 skip/xfail 粉饰断言。

覆盖面与 T-0447 交付项的对应：

1. 采集器产物形态：runs.csv 行数 = 模块数 × 轮数、字段齐全，summary.json 关键节齐全；
2. 统计正确性：growth_pct / linear_slope / 单调性 / 三态判定全部**手算对拍**
   （纯函数直接喂构造数据），再用真实采集的 rounds 数据复核 summary 与手算一致；
3. 三态判定：leak / stable / flaky 三组构造数据各给一个（另附 failing 防三态混淆）；
4. 失败快照真实触发：注入一个必抛 RecursionError 的模块（300 层深嵌套括号，
   T-0445 实测 80 层即红，300 层是确定性红），断言快照字段齐全——traceback 全文、
   当时 RSS、系统可用物理内存、句柄数、tracemalloc top10（按行号聚合）、Python 版本、
   主机名、开始/结束时间、并发数、模块路径、rc；
5. 双平台内存分支：Windows 分支（ctypes+psapi）在本机实跑断言有效值；POSIX 分支
   （resource.getrusage + sysctl）在 Windows 上只验证「按平台分支导入、降级不崩」
   （这是 Windows 上唯一可测的部分），真分支在 FreeBSD 15.1 实机验证——
   skip 只用于「当前平台没有该分支」，且已在 .hive/summary.md 双平台对照节说明；
6. 退出码语义：全绿 → 0；有失败 → 非 0（由用例 4 的必炸采集承担非 0 断言）。

阈值口径沿用 T-0445 实测（链条峰值 250MB / 大模块 300MB / 单次 5s / 10s），
本卡只采数，不新增阈值，也不对采集样本做阈值红绿判断。
"""

import csv
import json
import os
import subprocess
import sys

import pytest

from tools.r225_mem_capture import (
    classify_rounds,
    growth_pct,
    is_monotonic_nondecreasing,
    linear_slope,
    memory_info,
    posix_memory_info,
    windows_memory_info,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
CAPTURE = os.path.join(ROOT, 'tools', 'r225_mem_capture.py')


# ── 夹具：tmp_path 现生成小 .light（无 BOM，避免词法器不认 0xFEFF）──────────

def _写模块(path, 正文):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(正文)
    return str(path)


def _小模块集(tmp_path):
    """3 个语义正确的小 .light（判据主夹具）。"""
    d = tmp_path / 'mods'
    d.mkdir()
    return [
        _写模块(d / '甲.light', '段落 主程序:\n  设 甲 为 1 + 2。\n  写(转字符串(甲))。\n'),
        _写模块(d / '乙.light', '段落 主程序:\n  设 乙 为 "你好" + "光明"。\n  写(乙)。\n'),
        _写模块(d / '丙.light', '段落 主程序:\n  写(转字符串(3 * 4))。\n'),
    ]


def _必炸模块(tmp_path):
    """必抛 RecursionError：300 层括号 × ~12 帧/层 ≈ 3600 帧 > 递归上限 1000。"""
    d = tmp_path / 'mods_fail'
    d.mkdir(exist_ok=True)
    depth = 300
    _写模块(d / '好.light', '段落 主程序:\n  写(转字符串(1 + 2))。\n')
    return str(_写模块(d / '必炸模块.light',
                       '段落 主程序:\n  设 甲 为 %s1%s。\n  写(转字符串(甲))。\n'
                       % ('(' * depth, ')' * depth)))


def _跑采集(out_dir, modules_dir, rounds, workers, extra=()):
    """跑采集器子进程，返回 (returncode, stdout, stderr)。PYTHONPATH 自带 SRC+ROOT。"""
    out_dir.mkdir(exist_ok=True)
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(
        [SRC, ROOT] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    cmd = [sys.executable, CAPTURE,
           '--modules', str(modules_dir), '--rounds', str(rounds),
           '--workers', str(workers), '--out', str(out_dir),
           '--timeout-s', '300', '--label', 'test_R227'] + list(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=280, cwd=ROOT, env=env)
    return p.returncode, p.stdout or '', p.stderr or ''


def _读summary(out_dir):
    with open(os.path.join(str(out_dir), 'summary.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def _读csv(out_dir):
    with open(os.path.join(str(out_dir), 'runs.csv'), 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════════════
# 1. 产物形态：行数 = 模块数 × 轮数，CSV/summary 字段齐全
# ══════════════════════════════════════════════════════════════════════

def test_采集器_行数与字段齐全(tmp_path):
    mods = _小模块集(tmp_path)
    out = tmp_path / 'out_main'
    rc, stdout, stderr = _跑采集(out, os.path.dirname(mods[0]), rounds=2, workers=1)
    assert rc == 0, '全绿采集退出码应为 0：stdout=%r stderr=%r' % (stdout[-300:], stderr[-300:])

    rows = _读csv(out)
    assert len(rows) == len(mods) * 2, 'CSV 行数 %d ≠ 模块数 %d × 轮数 2' % (len(rows), len(mods))
    表头 = set(rows[0].keys())
    必需字段 = {'round', 'module', 'src_bytes', 'src_lines', 'compile_ms',
               'rss_before_kb', 'rss_after_kb', 'peak_ws_kb', 'private_kb',
               'rc', 'exception_type', 'exception_tail', 'snapshot_file'}
    assert 必需字段 <= 表头, 'CSV 缺字段：%r' % (必需字段 - 表头,)
    # 每行数据要有真值：字节数 > 0、编译耗时为数字、rc == 0
    for row in rows:
        assert int(row['src_bytes']) > 0, row
        assert float(row['compile_ms']) >= 0.0, row
        assert int(row['rc']) == 0, row

    summary = _读summary(out)
    for key in ('tool', 'machine', 'python', 'params', 'rounds', 'slopes',
                'classification', 'memory_unit_note'):
        assert key in summary, 'summary 缺 %s 节' % key
    assert len(summary['rounds']) == 2, summary['rounds']
    for r in summary['rounds']:
        for k in ('first_rss_kb', 'last_rss_kb', 'peak_rss_kb', 'growth_pct', 'failures'):
            assert k in r, (key, k)
    # 机器信息要能定位宿主：主机名/平台/CPU/物理内存
    m = summary['machine']
    for k in ('hostname', 'platform', 'cpu_count'):
        assert m.get(k), (k, m)
    assert summary['python']['version'], summary['python']


# ══════════════════════════════════════════════════════════════════════
# 2. 统计正确性：纯函数手算对拍 + 真实 summary 数据复核
# ══════════════════════════════════════════════════════════════════════

def test_斜率与增长百分比_手算对拍(tmp_path):
    # 纯函数：构造序列直接对拍
    assert growth_pct([100, 105, 110]) == pytest.approx(10.0)
    assert growth_pct([100000, 105000, 110000]) == pytest.approx(10.0)
    assert growth_pct([100]) == 0.0
    assert growth_pct([]) == 0.0
    assert growth_pct([0, 5]) == 0.0, '首值非正要降级 0，不许除零崩'
    assert linear_slope([100, 105, 110]) == pytest.approx(5.0)
    assert linear_slope([100, 130]) == pytest.approx(30.0)
    assert linear_slope([100]) == 0.0
    assert is_monotonic_nondecreasing([1, 1, 2, 3]) is True
    assert is_monotonic_nondecreasing([1, 2, 1]) is False

    # 集成复核：主采集的 summary 里每轮 growth_pct 必须等于
    # 手算 (last_rss_kb - first_rss_kb) / first_rss_kb * 100
    mods = _小模块集(tmp_path)
    out = tmp_path / 'out_stats'
    rc, stdout, stderr = _跑采集(out, os.path.dirname(mods[0]), rounds=2, workers=1)
    assert rc == 0, stderr[-300:]
    summary = _读summary(out)
    for r in summary['rounds']:
        first, last = r['first_rss_kb'], r['last_rss_kb']
        if first > 0:
            expect = (last - first) / first * 100.0
            assert r['growth_pct'] == pytest.approx(expect, abs=0.01), r
    # 轮间斜率 = (末轮 last - 首轮 last) / (轮数-1)
    lasts = [r['last_rss_kb'] for r in summary['rounds']]
    assert summary['slopes']['round_to_round_kb_per_round'] == pytest.approx(
        linear_slope(lasts), abs=0.01), summary['slopes']


# ══════════════════════════════════════════════════════════════════════
# 3. 三态判定：3 组构造数据分别给出 leak / stable / flaky（另附 failing）
# ══════════════════════════════════════════════════════════════════════

def test_三态判定_三组构造数据():
    # leak：轮间峰值 RSS 单调上升且总增长 30% > 5%
    leak_rounds = [{'round': i + 1, 'peak_rss_kb': p, 'failures': 0, 'growth_pct': 0.0}
                   for i, p in enumerate([100000, 110000, 120000, 130000])]
    assert classify_rounds(leak_rounds) == 'leak'

    # leak（第二形态）：非首轮连编的轮内单向爬升（单调非降 + 增长 > 5%）
    leak_in_round = [
        {'round': 1, 'peak_rss_kb': 24000, 'failures': 0, 'growth_pct': 8.0,
         'in_round_monotonic': True, 'in_round_growth_pct': 8.0},
        {'round': 2, 'peak_rss_kb': 27000, 'failures': 0, 'growth_pct': 9.0,
         'in_round_monotonic': True, 'in_round_growth_pct': 9.0},
    ]
    assert classify_rounds(leak_in_round) == 'leak'
    # 反例：首轮的轮内爬升是 Python 预热驻留（T-0445 口径 22→27MB），不算 leak
    warmup_only = [dict(leak_in_round[0])]
    assert classify_rounds(warmup_only) == 'stable'

    # stable：小幅波动、无失败（增长 0.5% ≤ 5%，且非单调——波动不是泄漏）
    stable_rounds = [{'round': i + 1, 'peak_rss_kb': p, 'failures': 0, 'growth_pct': 0.5}
                     for i, p in enumerate([100000, 101000, 99000, 100500])]
    assert classify_rounds(stable_rounds) == 'stable'

    # flaky：同输入不同轮结果不一致（第 1 轮失败、第 2 轮通过）
    flaky_rounds = [
        {'round': 1, 'peak_rss_kb': 100000, 'failures': 1, 'growth_pct': 0.0},
        {'round': 2, 'peak_rss_kb': 100500, 'failures': 0, 'growth_pct': 0.0},
    ]
    assert classify_rounds(flaky_rounds) == 'flaky'

    # failing：每轮一致失败且无内存爬升（三态之外的如实标注，不许混淆成 stable/flaky）
    failing_rounds = [{'round': i + 1, 'peak_rss_kb': p, 'failures': 2, 'growth_pct': 0.0}
                      for i, p in enumerate([100000, 100200])]
    assert classify_rounds(failing_rounds) == 'failing'


# ══════════════════════════════════════════════════════════════════════
# 4. 失败快照真实触发：必炸模块注入，断言快照字段齐全 + 退出码非 0
# ══════════════════════════════════════════════════════════════════════

def test_失败快照_真实触发且字段齐全(tmp_path):
    必炸 = _必炸模块(tmp_path)
    out = tmp_path / 'out_fail'
    rc, stdout, stderr = _跑采集(out, os.path.dirname(必炸), rounds=1, workers=2,
                                 extra=('--tracemalloc',))
    # 退出码语义：有失败 → 非 0（本用例同时承担非 0 断言；全绿 → 0 由用例 1/5 承担）
    assert rc != 0, '注入必炸模块后采集器必须非 0 退出，stdout=%r' % stdout[-300:]

    rows = _读csv(out)
    炸行 = [r for r in rows if r['exception_type'] == 'RecursionError']
    assert len(炸行) == 1, '必炸模块应有且仅有一行 RecursionError：%r' % (
        [r['module_name'] for r in rows],)
    row = 炸行[0]
    assert row['exception_tail'].strip(), '异常尾部 200 字符必须记录'
    assert int(row['rc']) != 0

    summary = _读summary(out)
    assert summary['classification'] == 'failing', summary['classification']
    assert summary['failure_count'] >= 1
    assert len(summary['snapshots']) == 1, summary['snapshots']

    snap_path = os.path.join(str(out), 'snapshots', summary['snapshots'][0])
    assert os.path.exists(snap_path), snap_path
    with open(snap_path, 'r', encoding='utf-8') as f:
        snap = json.load(f)
    # 快照字段齐全（T-0447 交付第 1 条的硬性清单）
    assert snap['exception_type'] == 'RecursionError'
    assert snap['traceback'].strip(), 'traceback 全文必须落盘'
    assert not snap['traceback_missing'], 'RecursionError 一定带 traceback，缺失即采集器 bug'
    assert snap['rss_kb'] and snap['rss_kb'] > 0
    assert snap['avail_phys_kb'] and snap['avail_phys_kb'] > 0
    assert snap['total_phys_kb'] and snap['total_phys_kb'] > 0
    # 句柄数按平台断言：Windows 必须取到（GetProcessHandleCount）；
    # POSIX 无该口径，采集器应如实降级为 None（红线：拿不到降级、不许崩）
    if os.name == 'nt':
        assert isinstance(snap['handles'], int) and snap['handles'] > 0, snap['handles']
    else:
        assert snap['handles'] is None, 'POSIX 无句柄数口径，应降级 None：%r' % snap['handles']
    assert snap['tracemalloc_enabled'] is True, 'tracemalloc 开启时快照必须含 top10'
    assert len(snap['tracemalloc_top10_by_lineno']) > 0
    for item in snap['tracemalloc_top10_by_lineno']:
        assert item['file_line'].count(':') >= 1 and item['bytes'] > 0, item
    assert snap['python_version']
    assert snap['hostname']
    assert snap['started_at'] and snap['finished_at']
    assert snap['concurrency'] == 2
    assert snap['module'].endswith('必炸模块.light')
    assert snap['rc'] == 1


# ══════════════════════════════════════════════════════════════════════
# 5. 退出码语义（全绿 → 0；subprocess 模式的行数契约顺带覆盖）
# ══════════════════════════════════════════════════════════════════════

def test_退出码_全绿为0且subprocess模式行数契约(tmp_path):
    mods = _小模块集(tmp_path)
    out = tmp_path / 'out_green_sub'
    rc, stdout, stderr = _跑采集(out, os.path.dirname(mods[0]), rounds=1, workers=2)
    assert rc == 0, stderr[-300:]
    rows = _读csv(out)
    assert len(rows) == len(mods) * 1, 'subprocess 模式 CSV 行数 %d ≠ 模块数 %d × 轮数 1' % (
        len(rows), len(mods))


# ══════════════════════════════════════════════════════════════════════
# 6. 双平台内存分支：Windows 实跑断言；POSIX 真分支 FreeBSD 验证（skip 仅限平台缺席）
# ══════════════════════════════════════════════════════════════════════

def test_内存分支_windows_psapi():
    if os.name != 'nt':
        pytest.skip('当前平台非 Windows，psapi 分支不存在（POSIX 上由 resource 分支承担）')
    w = windows_memory_info()
    assert w['peak_working_set_kb'] > 0, '峰值工作集取不到（psapi 未生效）：%r' % w
    assert w['working_set_kb'] > 0, w
    assert w['private_kb'] > 0, '私有字节（PrivateUsage）取不到：%r' % w
    assert w['total_phys_kb'] > 0, 'GlobalMemoryStatusEx 总物理内存取不到：%r' % w
    assert w['avail_phys_kb'] > 0, w
    assert w['handles'] > 0, '句柄数取不到：%r' % w
    # 统一入口按平台分发后字段等价
    m = memory_info()
    assert m['peak_ws_kb'] == w['peak_working_set_kb']
    assert m['handles'] == w['handles']


def test_内存分支_posix_getrusage():
    if os.name == 'nt':
        # Windows 上唯一可测的部分：resource 模块不存在，按平台分支导入必须
        # 降级返回（degraded=True）且**不崩**——这是红线「别顶格 import resource」的
        # 直接验证。POSIX 真分支（ru_maxrss > 0 + sysctl 可用内存）在 FreeBSD 15.1
        # 实机跑同一判据验证，见 .hive/summary.md「双平台对照」节。
        p = posix_memory_info()
        assert p.get('degraded') is True, 'Windows 上 POSIX 分支应降级而非抛错：%r' % p
        assert p.get('peak_rss_kb') is None, p
        pytest.skip('POSIX 真分支需 FreeBSD/Linux（当前平台无 resource 模块）；'
                    'Windows 已实测降级不崩，真分支见双平台对照')
    p = posix_memory_info()
    assert p['peak_rss_kb'] and p['peak_rss_kb'] > 0, 'ru_maxrss 取不到：%r' % p
    assert not p.get('degraded'), p
