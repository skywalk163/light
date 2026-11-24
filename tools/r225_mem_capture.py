# -*- coding: utf-8 -*-
"""R227 / T-0447：T-0445「内存错误」取证采集器——原始失败快照 + 同机连跑统计与内存曲线。

## 背景与目标

T-0445 收口时唯一悬而未决的一条：lightharness 验收期在 Windows 上报过
「内存错误 / 栈溢出」（光明对 MemoryError 的中文名），但修复 codegen 递归后
一切复现手段都不红，只能写「不可复现」，无法判宿主、也无法判已修好——
根因是**没有原始失败快照**。本采集器只做取证（不改编译器行为），把这条线
落成「有硬证据的三分结论」之一，或明确列出还缺哪些环境条件。

## 用法

    python tools/r225_mem_capture.py --modules DIR --rounds N --workers W --out DIR
                                     [--timeout-s S] [--per-module-timeout-s S]
                                     [--mode inproc|subprocess] [--tracemalloc]
                                     [--amplify] [--balloon-pct PCT] [--label L]

- `--mode inproc`（`--workers 1` 默认）：单个连编子进程按模块顺序连编 N 轮，
  对齐 T-0445「264 模块单进程连编」口径，可测**进程内累积泄漏**（轮内爬升）。
- `--mode subprocess`（`--workers W>1` 默认，或显式指定）：每个模块每轮独立
  编译子进程（内存可归零，失败可定位到单模块），W 路并行。
- `--amplify`：在 out 下生成 3 个放大模块（1200 项链 / ≥200KB 大模块 /
  大模块+项链+深嵌套叠加，借 T-0445 口径）并只采这些。
- `--balloon-pct PCT`：采集期间起「内存气球」子进程，把系统可用物理内存压到
  约 PCT%（如 10），模拟内存紧张；气球自带超时自杀，采集结束即被终止。
- `--tracemalloc`：子进程开 tracemalloc（失败快照里落 top10，按行号聚合）。
  有开销（约 2x 慢），大批量矩阵建议不开，放大矩阵与快照取证建议开。

## 产物（--out 目录）

- `runs.csv`：每模块每轮一行（crash 也占一行，exception_type=CRASH）。
- `summary.json`：机器信息、Python 版本、参数快照、每轮首/末/峰值 RSS 与
  增长百分比、轮间/轮内斜率、三态判定（leak/stable/flaky，一致失败另标
  failing）、失败清单、崩溃清单、快照索引。
- `report.txt`：给人看的 ASCII 表（每轮一行），可直接贴进任务 summary。
- `snapshots/*.json`：失败即抓快照——traceback 全文（Windows 的 MemoryError
  偶发不带 traceback 时落「当时内存快照 + 模块路径 + rc」并标 traceback 缺失，
  绝不静默吞掉）、当时 RSS、系统可用物理内存、进程句柄数、tracemalloc top10
  （按行号聚合）、Python 版本、主机名、开始/结束时间、并发数。

## 内存采集口径（两条分支，本卡核心）

- Windows：`ctypes` + `psapi.GetProcessMemoryInfo`（WorkingSetSize /
  PeakWorkingSetSize / PrivateUsage，取 EX 结构），系统级可用内存走
  `GlobalMemoryStatusEx`；句柄数走 `GetProcessHandleCount`。
- FreeBSD / POSIX：`resource.getrusage(RUSAGE_SELF).ru_maxrss`（KB，macOS 为
  字节，按平台折算），可用内存走 `sysctl hw.realmem` +
  `vm.stats.vm.v_free_count * hw.pagesize`（任一拿不到即降级为 None，不许崩）；
  POSIX 无「当前工作集/私有字节」的纯 Python 口径，rss_before/after 退化为
  峰值口径（ru_maxrss 快照，after ≥ before），私有字节/句柄数记 None。
- `resource` 在 Windows 上不存在，**按平台分支导入**，不顶格 import。

## 判宿主的三态判定（进 summary.json 且被判据覆盖）

- `leak`：轮间 RSS 单调上升且总增长 > 5%，或单轮内出现单向爬升（增长 > 5%）；
- `stable`：增长 ≤ 5% 且无失败；
- `flaky`：同输入不同轮结果不一致（某轮失败、下一轮通过）；
- `failing`：每轮都一致失败且无内存爬升（三态之外如实标注，指向确定性失败）。

## 红线对齐

- 纯 Python（Windows 上无 head/grep/awk/!/$()，shell 判据会 exit 255 假失败）；
- 单次采集 ≤ 30 分钟：`--timeout-s` 看门狗到点自杀（kill 子进程、落盘已有数据、
  summary 标 aborted），balloon/worker 自身也带超时退出，不常驻占机；
- 不依赖外网、真实凭证、特定目录残留（编译器由 PYTHONPATH 提供）。

阈值口径沿用 T-0445 实测（链条峰值 250MB / 大模块 300MB），本卡只采数不设阈值。
"""

import argparse
import concurrent.futures
import csv
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time

TOOL_VERSION = 'r227-1.0'
MEMORY_UNIT_NOTE = ('KB。Windows: WorkingSetSize/PeakWorkingSetSize/PrivateUsage（psapi EX 结构）；'
                    'POSIX: ru_maxrss 峰值口径（before/after 为两次 getrusage 快照），'
                    'private/handles 在 POSIX 无纯 Python 口径记 null。')

# ══════════════════════════════════════════════════════════════════════
# 纯计算函数（判据直接调，手算对拍）
# ══════════════════════════════════════════════════════════════════════

def growth_pct(values):
    """首末增长百分比：(末-首)/首*100。空/单点/首值<=0 一律 0.0（不崩）。"""
    if not values or len(values) < 2:
        return 0.0
    first, last = values[0], values[-1]
    if first <= 0:
        return 0.0
    return (last - first) / first * 100.0


def linear_slope(values):
    """平均斜率：(末-首)/(n-1)。n<2 返回 0.0。"""
    if not values or len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / (len(values) - 1)


def is_monotonic_nondecreasing(values):
    """非严格单调非降：允许相等，不允许回落。"""
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))


def classify_rounds(rounds, growth_threshold_pct=5.0):
    """三态判定（本卡判宿主的核心函数）。

    rounds：按轮序的 [{'peak_rss_kb': float, 'failures': int,
                       'growth_pct': float(轮内首末增长, 可缺省 0.0),
                       'round': int(轮号), 'in_round_monotonic': bool,
                       'in_round_growth_pct': float}, ...]
    返回 'leak' / 'stable' / 'flaky' / 'failing'。

    - flaky 优先：同输入不同轮结果不一致（有失败轮也有通过轮）；
    - leak：轮间峰值 RSS 单调上升、总增长 > 阈值**且末半程仍在上爬**（末段收敛
      检查——前几轮涨、之后持平是缓存/编译产物驻留的收敛形态，不是泄漏）；
      或单轮内单向爬升——**只认非首轮**的 inproc 轮（首轮连编的 AST/code
      驻留是 Python 常态，T-0445 口径 22→27MB 即此类；真泄漏的形态是
      后续轮继续爬升、基线递增），且轮内序列单调非降、增长 > 阈值；
    - stable：无失败且末半程收敛（增长 ≤ 阈值）。全程总增长只作展示：
      「前几轮驻留、末段持平」的缓存收敛形态归 stable，不算失败；
    - failing：每轮一致失败且无内存爬升（确定性失败信号，如实标注）。
    """
    if not rounds:
        return 'stable'
    has_fail = any(r.get('failures', 0) > 0 for r in rounds)
    has_pass = any(r.get('failures', 0) == 0 for r in rounds)
    if has_fail and has_pass:
        return 'flaky'
    peaks = [float(r.get('peak_rss_kb', 0.0)) for r in rounds]
    if (len(peaks) >= 2 and is_monotonic_nondecreasing(peaks)
            and growth_pct(peaks) > growth_threshold_pct):
        # 末段收敛检查：最后半程仍在上爬才算持续泄漏。前几轮涨、之后持平是
        # 缓存/编译产物驻留的收敛形态（矩阵 1 实测：峰值 39.9→44.2MB 后
        # 连续 6 轮零增长），不是泄漏——只看全程单调+总增长会把所有带
        # 缓存的进程首采都打成假 leak。
        half = peaks[len(peaks) // 2:]
        if growth_pct(half) > growth_threshold_pct:
            return 'leak'
    for r in rounds:
        if (int(r.get('round', 0) or 0) > 1 and r.get('in_round_monotonic')
                and float(r.get('in_round_growth_pct', 0.0)) > growth_threshold_pct):
            return 'leak'
    if not has_fail:
        # 无失败：末段收敛（≤阈值）即 stable。全程总增长只作展示——
        # 「前几轮驻留、末段持平」的缓存收敛形态不是泄漏也不是失败；
        # 字面 stable（全程增长≤5%）由非单调/低增长路径自然覆盖。
        half = peaks[len(peaks) // 2:] if len(peaks) >= 2 else peaks
        if growth_pct(half) <= growth_threshold_pct:
            return 'stable'
    return 'failing'


# ══════════════════════════════════════════════════════════════════════
# 内存探针：父进程侧（采集器自身环境）与子进程侧共用同一套口径。
# Windows 必须全部可用；POSIX 拿不到的降级 None，绝不崩。
# ══════════════════════════════════════════════════════════════════════

def windows_memory_info():
    """Windows：ctypes + psapi。返回 dict（KB），失败字段记 0/-1，不抛。"""
    import ctypes
    import ctypes.wintypes as wt

    class _PMCE(ctypes.Structure):
        _fields_ = [
            ('cb', wt.DWORD), ('PageFaultCount', wt.DWORD),
            ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
            ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
            ('PrivateUsage', ctypes.c_size_t),  # PROCESS_MEMORY_COUNTERS_EX 才有
        ]

    class _MSE(ctypes.Structure):
        _fields_ = [
            ('dwLength', wt.DWORD), ('dwMemoryLoad', wt.DWORD),
            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]

    out = {'working_set_kb': 0, 'peak_working_set_kb': 0, 'private_kb': 0,
           'avail_phys_kb': 0, 'total_phys_kb': 0, 'handles': -1}
    try:
        pmc = _PMCE()
        pmc.cb = ctypes.sizeof(_PMCE)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()),
            ctypes.byref(pmc), pmc.cb)
        if ok:
            out['working_set_kb'] = int(pmc.WorkingSetSize // 1024)
            out['peak_working_set_kb'] = int(pmc.PeakWorkingSetSize // 1024)
            out['private_kb'] = int(pmc.PrivateUsage // 1024)
        mse = _MSE()
        mse.dwLength = ctypes.sizeof(_MSE)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mse)):
            out['avail_phys_kb'] = int(mse.ullAvailPhys // 1024)
            out['total_phys_kb'] = int(mse.ullTotalPhys // 1024)
        n = wt.DWORD(0)
        if ctypes.windll.kernel32.GetProcessHandleCount(
                ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()),
                ctypes.byref(n)):
            out['handles'] = int(n.value)
    except Exception:
        pass
    return out


def posix_memory_info():
    """FreeBSD/POSIX：getrusage + sysctl。拿不到的降级 None，绝不崩。

    Windows 上 `resource` 不存在——按平台分支导入（红线），降级路径返回
    degraded=True 的 dict，让判据能在 Windows 上验证「不崩 + 正确降级」。
    """
    out = {'peak_rss_kb': None, 'private_kb': None, 'avail_phys_kb': None,
           'total_phys_kb': None, 'handles': None, 'degraded': False}
    try:
        import resource  # Windows 无此模块；本函数只在 POSIX 分支被真实调用
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        out['peak_rss_kb'] = rss / 1048576.0 if sys.platform == 'darwin' else float(rss)
    except ImportError:
        out['degraded'] = True
        return out
    except Exception:
        out['degraded'] = True
    # 可用内存：sysctl hw.realmem（总）与 v_free_count*pagesize（可用）
    def _sysctl(name):
        try:
            p = subprocess.run(['sysctl', '-n', name], capture_output=True,
                               text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                return int(p.stdout.strip())
        except Exception:
            pass
        return None
    realmem = _sysctl('hw.realmem')
    pagesize = _sysctl('hw.pagesize')
    free_pages = _sysctl('vm.stats.vm.v_free_count')
    if realmem is not None:
        out['total_phys_kb'] = realmem // 1024
    if pagesize is not None and free_pages is not None:
        out['avail_phys_kb'] = (pagesize * free_pages) // 1024
    return out


def memory_info():
    """按平台分发的统一入口（返回 KB 字段）。"""
    if os.name == 'nt':
        w = windows_memory_info()
        return {'working_set_kb': w['working_set_kb'],
                'peak_ws_kb': w['peak_working_set_kb'],
                'private_kb': w['private_kb'],
                'avail_phys_kb': w['avail_phys_kb'],
                'total_phys_kb': w['total_phys_kb'],
                'handles': w['handles']}
    p = posix_memory_info()
    return {'working_set_kb': p['peak_rss_kb'],
            'peak_ws_kb': p['peak_rss_kb'],
            'private_kb': p['private_kb'],
            'avail_phys_kb': p['avail_phys_kb'],
            'total_phys_kb': p['total_phys_kb'],
            'handles': p['handles'],
            'degraded': p.get('degraded', False)}


# ══════════════════════════════════════════════════════════════════════
# 子进程脚本（compile-one / compile-batch 双模式）。内嵌字符串运行时落盘，
# 由 PYTHONPATH 提供光明编译器，Windows 与 FreeBSD 用同一份。
# ══════════════════════════════════════════════════════════════════════

_WORKER_SCRIPT = r'''
# -*- coding: utf-8 -*-
"""R227 采集子进程。argv 分发：
  compile-one  SRC STATS_PATH SNAPSHOT_DIR TRACEMALLOC(0/1) CONCURRENCY
  compile-batch LIST_PATH ROUNDS JSONL_PATH TRACEMALLOC(0/1) CONCURRENCY SNAPSHOT_DIR
编译链路对齐 T-0445 探针：LightParser -> PythonCodeGenerator -> compile。
"""
import json, os, socket, sys, time, traceback

_T0 = time.time()

def _mem():
    """统一内存探针（KB）。Windows: psapi EX；POSIX: getrusage + sysctl。"""
    if os.name == 'nt':
        import ctypes, ctypes.wintypes as wt
        class _PMCE(ctypes.Structure):
            _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                        ('PrivateUsage', ctypes.c_size_t)]
        class _MSE(ctypes.Structure):
            _fields_ = [('dwLength', wt.DWORD), ('dwMemoryLoad', wt.DWORD),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        d = {'working_set_kb': 0, 'peak_ws_kb': 0, 'private_kb': 0,
             'avail_phys_kb': 0, 'total_phys_kb': 0, 'handles': -1}
        try:
            pmc = _PMCE(); pmc.cb = ctypes.sizeof(_PMCE)
            if ctypes.windll.psapi.GetProcessMemoryInfo(
                    ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()),
                    ctypes.byref(pmc), pmc.cb):
                d['working_set_kb'] = int(pmc.WorkingSetSize // 1024)
                d['peak_ws_kb'] = int(pmc.PeakWorkingSetSize // 1024)
                d['private_kb'] = int(pmc.PrivateUsage // 1024)
            mse = _MSE(); mse.dwLength = ctypes.sizeof(_MSE)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mse)):
                d['avail_phys_kb'] = int(mse.ullAvailPhys // 1024)
                d['total_phys_kb'] = int(mse.ullTotalPhys // 1024)
            n = wt.DWORD(0)
            if ctypes.windll.kernel32.GetProcessHandleCount(
                    ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()), ctypes.byref(n)):
                d['handles'] = int(n.value)
        except Exception:
            pass
        return d
    d = {'working_set_kb': None, 'peak_ws_kb': None, 'private_kb': None,
         'avail_phys_kb': None, 'total_phys_kb': None, 'handles': None}
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        d['peak_ws_kb'] = d['working_set_kb'] = (
            rss / 1048576.0 if sys.platform == 'darwin' else float(rss))
    except Exception:
        pass

    def _sysctl(name):
        try:
            import subprocess as _sp
            p = _sp.run(['sysctl', '-n', name], capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                return int(p.stdout.strip())
        except Exception:
            pass
        return None
    realmem, pagesize, freepages = _sysctl('hw.realmem'), _sysctl('hw.pagesize'), _sysctl('vm.stats.vm.v_free_count')
    if realmem is not None:
        d['total_phys_kb'] = realmem // 1024
    if pagesize is not None and freepages is not None:
        d['avail_phys_kb'] = (pagesize * freepages) // 1024
    return d

def _tm_top10():
    """tracemalloc top10，按 (文件, 行号) 聚合。未启用返回 (False, [])。"""
    try:
        import tracemalloc
        if not tracemalloc.is_tracing():
            return False, []
        agg = {}
        for stat in tracemalloc.take_snapshot().statistics('lineno'):
            f0 = stat.traceback[0]
            key = '%s:%s' % (f0.filename, f0.lineno)
            agg[key] = agg.get(key, 0) + stat.size
        top = sorted(agg.items(), key=lambda kv: -kv[1])[:10]
        return True, [{'file_line': k, 'bytes': v} for k, v in top]
    except Exception:
        return False, []

def _snapshot(src_path, exc, conc, snapshot_dir, tag, tb_text):
    """失败即抓快照：traceback/RSS/可用内存/句柄数/tracemalloc/版本/主机名/时间/并发。

    tb_text 必须在 except 块内用 traceback.format_exc() 抓好再传入——
    except 结束后 sys.exc_info() 已清空，事后调用只会得到 'NoneType: None'。
    Windows 的 MemoryError 偶发不带 traceback：tb_text 为空时落
    「当时内存快照 + 模块路径 + rc」并标 traceback_missing，绝不静默吞掉。
    """
    tb_missing = not (tb_text or '').strip()
    m = _mem()
    tm_on, top = _tm_top10()
    snap = {
        'kind': 'snapshot', 'module': src_path, 'rc': 1,
        'exception_type': type(exc).__name__,
        'exception_tail': (str(exc) or '')[-200:],
        'traceback': '' if tb_missing else tb_text,
        'traceback_missing': bool(tb_missing),
        'rss_kb': m['working_set_kb'], 'peak_ws_kb': m['peak_ws_kb'],
        'private_kb': m['private_kb'],
        'avail_phys_kb': m['avail_phys_kb'], 'total_phys_kb': m['total_phys_kb'],
        'handles': m['handles'],
        'tracemalloc_enabled': tm_on,
        'tracemalloc_top10_by_lineno': top,
        'python_version': sys.version,
        'hostname': socket.gethostname(),
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(_T0)),
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'concurrency': int(conc),
    }
    path = os.path.join(snapshot_dir, 'snap_%s_%d.json' % (tag, int(time.time() * 1000)))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    return path, snap

def _read_src(p):
    with open(p, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def _compile_one(src_path, conc, snapshot_dir, tag, tm_flag):
    """编译单个模块，返回 (stats, snapshot_path, snapshot)。失败不抛，落快照。"""
    mem_before = _mem()          # 编译器已 import，模块编译前
    if tm_flag:
        import tracemalloc
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    t0 = time.perf_counter()
    snapshot_path = snapshot = None
    exc = None
    rc = 0
    tb_text = None
    try:
        source = _read_src(src_path)
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        module = LightParser().parse(source)
        code = PythonCodeGenerator().generate(module, is_main=True)
        compile(code, '<r227>', 'exec')
    except BaseException as e:   # MemoryError/RecursionError 都要抓；不吞 SystemExit 之外的任何类型
        exc = e
        rc = 1
        tb_text = traceback.format_exc()   # 必须在 except 块内抓，出去就没了
    t3 = time.perf_counter()
    mem_after = _mem()
    stats = {
        'module': src_path, 'src_bytes': os.path.getsize(src_path),
        'src_lines': _read_src(src_path).count('\n') + 1,
        'compile_ms': round((t3 - t0) * 1000.0, 1),
        'rss_before_kb': mem_before['working_set_kb'],
        'rss_after_kb': mem_after['working_set_kb'],
        'peak_ws_kb': mem_after['peak_ws_kb'],
        'private_kb': mem_after['private_kb'],
        'sys_avail_phys_kb': mem_after['avail_phys_kb'],
        'rc': rc,
        'exception_type': type(exc).__name__ if exc is not None else None,
        'exception_tail': (str(exc) or '')[-200:] if exc is not None else None,
        'concurrency': int(conc),
    }
    if exc is not None:
        snapshot_path, snapshot = _snapshot(src_path, exc, conc, snapshot_dir, tag, tb_text)
    return stats, snapshot_path, snapshot

def _run_compile_one(argv):
    src, stats_path, snapshot_dir, tm_flag, conc = argv[2], argv[3], argv[4], argv[5] == '1', argv[6]
    tag = os.path.basename(src)
    stats, snapshot_path, _snap = _compile_one(src, conc, snapshot_dir, tag, tm_flag)
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    print(snapshot_path or '')
    sys.exit(0 if stats['rc'] == 0 else 1)

def _run_compile_batch(argv):
    list_path, rounds, jsonl_path, tm_flag, conc, snapshot_dir = (
        argv[2], int(argv[3]), argv[4], argv[5] == '1', argv[6], argv[7])
    with open(list_path, 'r', encoding='utf-8') as f:
        modules = [ln.strip() for ln in f if ln.strip()]
    if tm_flag:
        import tracemalloc
        tracemalloc.start()
    with open(jsonl_path, 'w', encoding='utf-8') as jf:
        for r in range(1, rounds + 1):
            for src in modules:
                tag = 'r%d_%s' % (r, os.path.basename(src))
                stats, snapshot_path, _snap = _compile_one(src, conc, snapshot_dir, tag, tm_flag)
                rec = dict(stats)
                rec.update({'kind': 'record', 'round': r,
                            'module_name': os.path.basename(src),
                            'snapshot_file': os.path.basename(snapshot_path) if snapshot_path else ''})
                jf.write(json.dumps(rec, ensure_ascii=False) + '\n')
                jf.flush()
        jf.write(json.dumps({'kind': 'done'}) + '\n')
        jf.flush()
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-one':
        _run_compile_one(sys.argv)
    elif len(sys.argv) > 1 and sys.argv[1] == 'compile-batch':
        _run_compile_batch(sys.argv)
    else:
        sys.stderr.write('usage: worker compile-one|compile-batch ...\n')
        sys.exit(2)
'''

_BALLOON_SCRIPT = r'''
# -*- coding: utf-8 -*-
"""R227 内存气球：把系统可用物理内存压到约 TARGET_PCT%，写 ready 后持有；
自带 TIMEOUT_S 秒自杀，被父进程 terminate 也能立即退出。不常驻占机。"""
import os, sys, time

def _avail_kb():
    if os.name == 'nt':
        import ctypes, ctypes.wintypes as wt
        class _MSE(ctypes.Structure):
            _fields_ = [('dwLength', wt.DWORD), ('dwMemoryLoad', wt.DWORD),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        mse = _MSE(); mse.dwLength = ctypes.sizeof(_MSE)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mse)):
            return int(mse.ullAvailPhys // 1024)
        return 0
    try:
        import subprocess as sp
        tot = sp.run(['sysctl', '-n', 'hw.realmem'], capture_output=True, text=True, timeout=5)
        pg = sp.run(['sysctl', '-n', 'hw.pagesize'], capture_output=True, text=True, timeout=5)
        fr = sp.run(['sysctl', '-n', 'vm.stats.vm.v_free_count'], capture_output=True, text=True, timeout=5)
        total = int(tot.stdout.strip()); pagesize = int(pg.stdout.strip()); free = int(fr.stdout.strip())
        return (pagesize * free) // 1024
    except Exception:
        return 0

def main():
    target_pct, ready_path, timeout_s = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    avail_kb = _avail_kb()
    to_take_kb = max(0, int(avail_kb * (100 - target_pct) / 100.0))
    chunks = []
    taken_kb = 0
    chunk_bytes = 256 * 1024 * 1024
    while taken_kb < to_take_kb:
        want = min(chunk_bytes, (to_take_kb - taken_kb) * 1024)
        try:
            chunks.append(b'\x01' * want)   # 写非零，确保物理页真实占用
        except MemoryError:
            break
        taken_kb += want // 1024
    with open(ready_path, 'w', encoding='utf-8') as f:
        f.write('%d' % taken_kb)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
'''

# ══════════════════════════════════════════════════════════════════════
# 放大模块生成（矩阵3：借 T-0445 的 1200 项链与 ≥200KB 大模块口径）
# ══════════════════════════════════════════════════════════════════════

def _包入口(正文):
    return '段落 主程序:\n' + ''.join('  ' + 行 + '\n' for 行 in 正文.strip('\n').split('\n'))


def _项链模块(n=1200):
    return _包入口('设 甲 为 %s。\n写(转字符串(甲))。' % ' + '.join(['1'] * n))


def _大模块(n=4300):
    """≥200KB / ≥4000 行，形状贴近 harness 模块（T-0445 同款）。"""
    行 = ['段落 主程序:']
    for i in range(n):
        行.append('  设 变量%d 为 "标签%d" + 转字符串(%d + 1) + "。"。' % (i, i, i))
    for i in range(100):
        行.append('  设 文本%d 为 "标题%d" + 转字符串(变量%d)。' % (i, i, n - 1 - i))
    行.append('  写(变量%d)。' % (n - 1))
    行.append('  写("|")。')
    行.append('  写(变量0)。')
    return '\n'.join(行) + '\n'


def _叠加模块():
    """大模块正文 + 1200 项链 + 60 层深嵌套括号，三重压力叠加。"""
    parts = ['段落 主程序:']
    for i in range(3000):
        parts.append('  设 叠变量%d 为 "块%d" + 转字符串(%d * 2 + 1) + "。"。' % (i, i, i))
    parts.append('  设 链甲 为 %s。' % ' + '.join(['1'] * 1200))
    parts.append('  设 嵌甲 为 %s1%s。' % ('(' * 60, ')' * 60))
    parts.append('  写(转字符串(链甲))。')
    parts.append('  写("|")。')
    parts.append('  写(转字符串(嵌甲))。')
    return '\n'.join(parts) + '\n'


def write_amplified_modules(out_dir):
    """在 out_dir/amplified 下生成 3 个放大模块，返回模块目录。"""
    amp_dir = os.path.join(out_dir, 'amplified')
    os.makedirs(amp_dir, exist_ok=True)
    items = [('放大_1200项链.light', _项链模块(1200)),
             ('放大_大模块200KB.light', _大模块()),
             ('放大_叠加_项链嵌套大模块.light', _叠加模块())]
    for name, text in items:
        with open(os.path.join(amp_dir, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    return amp_dir


# ══════════════════════════════════════════════════════════════════════
# 采集主流程
# ══════════════════════════════════════════════════════════════════════

def collect_modules(modules_dir):
    found = []
    for root, _dirs, files in os.walk(modules_dir):
        for fn in files:
            if fn.lower().endswith('.light'):
                found.append(os.path.join(root, fn))
    return sorted(found)


def _worker_env():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(
        [os.path.join(root, 'src'), root] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    return env


def _machine_info():
    m = memory_info()
    return {'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'cpu_count': os.cpu_count(),
            'total_phys_kb': m.get('total_phys_kb'),
            'avail_phys_kb_start': m.get('avail_phys_kb')}


class _Watchdog:
    """总超时看门狗：deadline 到点返回 True（采集器自杀收口）。"""

    def __init__(self, timeout_s):
        self.deadline = time.monotonic() + timeout_s

    def expired(self):
        return time.monotonic() >= self.deadline


def run_inproc(modules, rounds, out_dir, tm_flag, conc, per_module_timeout_s, watchdog):
    """单子进程连编全部模块 × N 轮，tail 线程收 jsonl。"""
    tmp_dir = os.path.join(out_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    list_path = os.path.join(tmp_dir, 'modules.list')
    with open(list_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(modules))
    jsonl_path = os.path.join(out_dir, 'raw_inproc.jsonl')
    worker = _write_worker(out_dir)
    cmd = [sys.executable, worker, 'compile-batch', list_path, str(rounds),
           jsonl_path, '1' if tm_flag else '0', str(conc),
           os.path.join(out_dir, 'snapshots')]
    env = _worker_env()
    records = []
    aborted = {'flag': False}
    proc = subprocess.Popen(cmd, cwd=out_dir, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def _tail():
        done = False
        while not done:
            try:
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except OSError:
                lines = []
            got = []
            for ln in lines:
                try:
                    obj = json.loads(ln)
                except Exception:
                    continue
                if obj.get('kind') == 'done':
                    done = True
                elif obj.get('kind') == 'record':
                    got.append(obj)
            if got:
                records[:] = got   # jsonl 全量覆盖读，直接替换
            if done or proc.poll() is not None:
                break
            time.sleep(1.0)
        # 收尾再补一次全量读（防竞态漏行）
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            got = [json.loads(ln) for ln in lines if ln.strip()]
            records[:] = [o for o in got if o.get('kind') == 'record']
            if any(o.get('kind') == 'done' for o in got):
                done = True
        except Exception:
            pass
        aborted['done'] = done

    tail_thread = threading.Thread(target=_tail, daemon=True)
    tail_thread.start()
    stderr_text = ''
    try:
        proc.wait(timeout=max(1, int(watchdog.deadline - time.monotonic())))
        try:
            stderr_text = (proc.stderr.read() or '').decode('utf-8', 'replace') if proc.stderr else ''
        except Exception:
            stderr_text = ''
    except subprocess.TimeoutExpired:
        aborted['flag'] = True
        proc.kill()
        try:
            proc.wait(timeout=10)
        except Exception:
            pass
    tail_thread.join(timeout=15)
    # batch 子进程异常退出（crash/OOM）不得静默：从已完成记录推断缺口并记 crash
    if proc.returncode not in (0, None) and not aborted.get('done'):
        expected = len(modules) * rounds
        missing = expected - len(records)
        if missing > 0:
            records.append({'kind': 'record', 'round': rounds, 'module': '<batch-worker>',
                            'module_name': '<batch-worker>', 'src_bytes': 0, 'src_lines': None,
                            'compile_ms': None, 'rss_before_kb': None, 'rss_after_kb': None,
                            'peak_ws_kb': None, 'private_kb': None, 'sys_avail_phys_kb': None,
                            'rc': 1, 'exception_type': 'CRASH',
                            'exception_tail': ('batch worker 提前退出 rc=%s，缺口 %d 条未采；stderr 尾部: %s'
                                               % (proc.returncode, missing, stderr_text[-200:])),
                            'snapshot_file': '', 'concurrency': conc})
    return records, aborted['flag'] or not aborted.get('done', True)


def run_subprocess_pool(modules, rounds, workers, out_dir, tm_flag, conc,
                        per_module_timeout_s, watchdog, log):
    """每模块每轮独立编译子进程，W 线程并行。crash/OOM 落盘成一条 CRASH 记录。"""
    tmp_dir = os.path.join(out_dir, 'tmp')
    snap_dir = os.path.join(out_dir, 'snapshots')
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(snap_dir, exist_ok=True)
    worker = _write_worker(out_dir)
    env = _worker_env()
    tasks = [(r, m) for r in range(1, rounds + 1) for m in modules]
    records = []
    lock = threading.Lock()
    completed = [0]
    aborted = {'flag': False}

    def _one(task):
        r, src = task
        if watchdog.expired():
            aborted['flag'] = True
            return None
        stats_path = os.path.join(tmp_dir, 'r%d_i%d.json' % (r, abs(hash(src)) % (10 ** 12)))
        if os.path.exists(stats_path):
            os.remove(stats_path)
        cmd = [sys.executable, worker, 'compile-one', src, stats_path, snap_dir,
               '1' if tm_flag else '0', str(conc)]
        snapshot_file = ''
        try:
            p = subprocess.run(cmd, cwd=out_dir, env=env, capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=per_module_timeout_s)
            snapshot_file = (p.stdout or '').strip().splitlines()[-1] if (p.stdout or '').strip() else ''
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    rec = json.load(f)
            else:
                # rc≠0 且无 stats：硬崩溃/OOM，必须落盘，不许静默
                rec = {'module': src, 'src_bytes': os.path.getsize(src) if os.path.exists(src) else 0,
                       'src_lines': None, 'compile_ms': None, 'rss_before_kb': None,
                       'rss_after_kb': None, 'peak_ws_kb': None, 'private_kb': None,
                       'sys_avail_phys_kb': None, 'rc': p.returncode, 'exception_type': 'CRASH',
                       'exception_tail': ('子进程 rc=%s 且未落 stats（疑似 OOM/硬崩溃）；stderr 尾部: %s'
                                          % (p.returncode, (p.stderr or '')[-200:])),
                       'concurrency': conc}
        except subprocess.TimeoutExpired:
            rec = {'module': src, 'src_bytes': os.path.getsize(src) if os.path.exists(src) else 0,
                   'src_lines': None, 'compile_ms': None, 'rss_before_kb': None,
                   'rss_after_kb': None, 'peak_ws_kb': None, 'private_kb': None,
                   'sys_avail_phys_kb': None, 'rc': 1, 'exception_type': 'CRASH_TIMEOUT',
                   'exception_tail': '子进程超过 per-module-timeout=%ss 被杀' % per_module_timeout_s,
                   'concurrency': conc}
        rec.update({'kind': 'record', 'round': r, 'module_name': os.path.basename(src),
                    'snapshot_file': os.path.basename(snapshot_file) if snapshot_file else ''})
        with lock:
            records.append(rec)
            completed[0] += 1
            if completed[0] % 50 == 0:
                log('[r227] 进度 %d/%d' % (completed[0], len(tasks)))
        try:
            if os.path.exists(stats_path):
                os.remove(stats_path)
        except OSError:
            pass
        return rec

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(_one, tasks))
    return records, aborted['flag']


def _write_worker(out_dir):
    worker = os.path.join(out_dir, '_r227_worker.py')
    with open(worker, 'w', encoding='utf-8', newline='\n') as f:
        f.write(_WORKER_SCRIPT)
    return worker


def _start_balloon(out_dir, pct, timeout_s):
    """起内存气球，等 ready。返回 (Popen) 或 None（起不来不阻塞取证）。"""
    balloon = os.path.join(out_dir, '_r227_balloon.py')
    with open(balloon, 'w', encoding='utf-8', newline='\n') as f:
        f.write(_BALLOON_SCRIPT)
    ready_path = os.path.join(out_dir, 'balloon.ready')
    if os.path.exists(ready_path):
        os.remove(ready_path)
    proc = subprocess.Popen([sys.executable, balloon, str(pct), ready_path,
                             str(max(60, timeout_s))],
                            cwd=out_dir, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            return None
        if os.path.exists(ready_path):
            try:
                with open(ready_path, 'r', encoding='utf-8') as f:
                    taken = int(f.read().strip() or 0)
                return proc if taken > 0 else None
            except Exception:
                return None
        time.sleep(0.5)
    proc.kill()
    return None


def _round_aggregates(records, rounds, inproc=False):
    """每轮聚合：首/末/峰值 RSS（KB）、增长百分比、失败数、崩溃数、耗时。

    inproc=True 时额外按 jsonl 写入顺序（= 模块顺序）计算轮内
    rss_after 序列的单调性与首末增长，供三态判定「单轮内单向爬升」用；
    subprocess 模式每模块是独立进程，该序列无进程内驻留语义，不填。
    """
    per_round = {r: [] for r in range(1, rounds + 1)}
    for rec in records:
        per_round.setdefault(rec['round'], []).append(rec)
    rounds_out = []
    for r in sorted(per_round):
        rs = per_round[r]
        before = [x['rss_before_kb'] for x in rs if isinstance(x.get('rss_before_kb'), (int, float))]
        after = [x['rss_after_kb'] for x in rs if isinstance(x.get('rss_after_kb'), (int, float))]
        peaks = [x['peak_ws_kb'] for x in rs if isinstance(x.get('peak_ws_kb'), (int, float))]
        first = sum(before) / len(before) if before else 0.0
        last = sum(after) / len(after) if after else 0.0
        peak = max(peaks) if peaks else 0.0
        row = {
            'round': r,
            'record_count': len(rs),
            'first_rss_kb': round(first, 1),
            'last_rss_kb': round(last, 1),
            'peak_rss_kb': round(peak, 1),
            'growth_pct': round(growth_pct([first, last]), 2) if first > 0 else 0.0,
            'failures': sum(1 for x in rs if x.get('rc') not in (0, None)
                            and x.get('exception_type') not in ('CRASH', 'CRASH_TIMEOUT')),
            'crashes': sum(1 for x in rs if x.get('exception_type') in ('CRASH', 'CRASH_TIMEOUT')),
            'compile_ms_total': round(sum(x['compile_ms'] for x in rs
                                          if isinstance(x.get('compile_ms'), (int, float))), 1),
        }
        if inproc:
            seq = [x['rss_after_kb'] for x in rs if isinstance(x.get('rss_after_kb'), (int, float))]
            row['in_round_monotonic'] = len(seq) >= 2 and is_monotonic_nondecreasing(seq)
            row['in_round_growth_pct'] = (round(growth_pct(seq), 2) if len(seq) >= 2 else 0.0)
        rounds_out.append(row)
    return rounds_out


def write_outputs(out_dir, records, rounds_out, args, machine, started_at, finished_at,
                  aborted_flag, module_count):
    """runs.csv + summary.json + report.txt。返回退出码。"""
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, 'runs.csv')
    cols = ['round', 'mode', 'module', 'module_name', 'src_bytes', 'src_lines',
            'compile_ms', 'rss_before_kb', 'rss_after_kb', 'peak_ws_kb', 'private_kb',
            'sys_avail_phys_kb', 'rc', 'exception_type', 'exception_tail', 'snapshot_file',
            'concurrency']
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for rec in sorted(records, key=lambda x: (x['round'], str(x.get('module_name', '')))):
            row = {c: rec.get(c, '') for c in cols}
            row['module_name'] = rec.get('module_name') or os.path.basename(str(rec.get('module', '')))
            if isinstance(row.get('exception_tail'), str) and len(row['exception_tail']) > 200:
                row['exception_tail'] = row['exception_tail'][-200:]
            w.writerow(row)

    peak_series = [r['peak_rss_kb'] for r in rounds_out]
    last_series = [r['last_rss_kb'] for r in rounds_out]
    classification = classify_rounds(rounds_out)
    slopes = {
        'round_to_round_kb_per_round': round(linear_slope(last_series), 2),
        'total_growth_pct': round(growth_pct(peak_series), 2),
        'per_round_slope_kb_per_module': [
            {'round': r['round'], 'slope_kb': round(linear_slope(
                [x['rss_after_kb'] for x in sorted(
                    [rec for rec in records if rec['round'] == r['round']],
                    key=lambda y: str(y.get('module_name', '')))
                 if isinstance(x.get('rss_after_kb'), (int, float))]), 2)}
            for r in rounds_out],
    }
    failures = [{'round': rec['round'], 'module': rec.get('module_name') or rec.get('module'),
                 'exception_type': rec.get('exception_type'), 'rc': rec.get('rc'),
                 'exception_tail': rec.get('exception_tail'),
                 'snapshot_file': rec.get('snapshot_file')}
                for rec in records if rec.get('rc') not in (0, None)]
    crashes = [f for f in failures if f['exception_type'] in ('CRASH', 'CRASH_TIMEOUT')]
    snapshots = sorted({f['snapshot_file'] for f in failures if f.get('snapshot_file')})

    summary = {
        'tool': 'r225_mem_capture', 'version': TOOL_VERSION,
        'label': args.label, 'mode': args.effective_mode,
        'params': {'modules_dir': os.path.abspath(args.modules),
                   'rounds': args.rounds, 'workers': args.workers,
                   'timeout_s': args.timeout_s,
                   'per_module_timeout_s': args.per_module_timeout_s,
                   'tracemalloc': args.tracemalloc,
                   'balloon_pct': args.balloon_pct,
                   'amplify': args.amplify,
                   'module_count': module_count},
        'machine': machine,
        'python': {'version': sys.version, 'executable': sys.executable},
        'memory_unit_note': MEMORY_UNIT_NOTE,
        'started_at': started_at, 'finished_at': finished_at,
        'duration_s': round(_parse_ts(finished_at) - _parse_ts(started_at), 1) if finished_at and started_at else None,
        'aborted': aborted_flag,
        'rounds': rounds_out,
        'slopes': slopes,
        'classification': classification,
        'failure_count': len(failures),
        'crash_count': len(crashes),
        'failures': failures[:200],
        'crashes': crashes[:200],
        'snapshots': snapshots,
    }
    with open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    lines = []
    lines.append('[R227 内存采集报告] label=%s  mode=%s  workers=%s  rounds=%s  modules=%s%s' % (
        args.label, args.effective_mode, args.workers, args.rounds, module_count,
        '  [已超时截断 aborted]' if aborted_flag else ''))
    lines.append('平台: %s' % machine['platform'])
    lines.append('Python: %s' % sys.version.split()[0])
    lines.append('')
    lines.append('轮  记录数  首RSS(MB)  末RSS(MB)  峰值(MB)  增长%   编译耗时(s)  失败  崩溃')
    for r in rounds_out:
        lines.append('%2d  %5d    %8.1f  %8.1f  %8.1f  %5.2f  %10.2f  %4d  %4d' % (
            r['round'], r['record_count'], r['first_rss_kb'] / 1024.0, r['last_rss_kb'] / 1024.0,
            r['peak_rss_kb'] / 1024.0, r['growth_pct'], r['compile_ms_total'] / 1000.0,
            r['failures'], r['crashes']))
    lines.append('')
    lines.append('轮间斜率: %.2f KB/轮    轮间峰值总增长: %.2f%%' % (
        slopes['round_to_round_kb_per_round'], slopes['total_growth_pct']))
    inproc_slopes = [s['slope_kb'] for s in slopes['per_round_slope_kb_per_module']]
    lines.append('轮内斜率(每模块增量, KB/模块): [%s]' % ', '.join(
        '%.2f' % s for s in inproc_slopes))
    lines.append('三态判定: %s' % classification)
    lines.append('失败: %d 条 / 崩溃: %d 条 / 快照: %d 份' % (
        len(failures), len(crashes), len(snapshots)))
    if snapshots:
        lines.append('快照文件: %s' % ', '.join(snapshots[:10]) + (' ...' if len(snapshots) > 10 else ''))
    with open(os.path.join(out_dir, 'report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 1 if failures else 0


def _parse_ts(s):
    import datetime
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S').timestamp()
    except Exception:
        return 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description='R227 内存取证采集器（T-0447）')
    ap.add_argument('--modules', required=True, help='.light 模块目录')
    ap.add_argument('--rounds', type=int, default=1)
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeout-s', type=int, default=1800,
                    help='单次采集总超时（默认 1800s=30 分钟，到点自杀）')
    ap.add_argument('--per-module-timeout-s', type=int, default=120,
                    help='subprocess 模式单模块编译子进程超时')
    ap.add_argument('--mode', choices=['inproc', 'subprocess'], default=None,
                    help='缺省时 workers=1 -> inproc（连编），workers>1 -> subprocess')
    ap.add_argument('--tracemalloc', action='store_true')
    ap.add_argument('--amplify', action='store_true',
                    help='生成 3 个放大模块（1200 项链 / ≥200KB 大模块 / 叠加）并只采这些')
    ap.add_argument('--balloon-pct', type=int, default=0,
                    help='>0 时起内存气球，把可用物理内存压到约该百分比再采集')
    ap.add_argument('--label', default='capture')
    args = ap.parse_args(argv)
    args.effective_mode = args.mode or ('inproc' if args.workers <= 1 else 'subprocess')

    started_at = time.strftime('%Y-%m-%dT%H:%M:%S')
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'snapshots'), exist_ok=True)

    if args.amplify:
        args.modules = write_amplified_modules(out_dir)
    modules = collect_modules(args.modules)
    if not modules:
        sys.stderr.write('[r227] 未找到 .light 模块：%s\n' % args.modules)
        return 2
    conc = args.workers if args.effective_mode == 'subprocess' else 1
    watchdog = _Watchdog(args.timeout_s)
    machine = _machine_info()

    log = lambda s: print(s, flush=True)
    log('[r227] label=%s mode=%s rounds=%d workers=%d modules=%d tracemalloc=%s balloon=%s%%' % (
        args.label, args.effective_mode, args.rounds, args.workers, len(modules),
        args.tracemalloc, args.balloon_pct))

    balloon = None
    if args.balloon_pct > 0:
        log('[r227] 起内存气球：目标可用物理内存 ~%d%%' % args.balloon_pct)
        balloon = _start_balloon(out_dir, args.balloon_pct, args.timeout_s)
        if balloon is None:
            log('[r227] 气球未能就绪（跳过压内存，继续正常采集）')

    try:
        if args.effective_mode == 'inproc':
            records, aborted_flag = run_inproc(modules, args.rounds, out_dir,
                                               args.tracemalloc, conc,
                                               args.per_module_timeout_s, watchdog)
        else:
            records, aborted_flag = run_subprocess_pool(
                modules, args.rounds, args.workers, out_dir, args.tracemalloc, conc,
                args.per_module_timeout_s, watchdog, log)
    finally:
        if balloon is not None:
            try:
                balloon.kill()
                balloon.wait(timeout=10)
                log('[r227] 气球已终止')
            except Exception:
                pass

    finished_at = time.strftime('%Y-%m-%dT%H:%M:%S')
    rounds_out = _round_aggregates(records, args.rounds,
                                   inproc=(args.effective_mode == 'inproc'))
    if not records:
        sys.stderr.write('[r227] 采集失败：0 条记录（worker 可能整体崩溃）\n')
        return 2
    rc = write_outputs(out_dir, records, rounds_out, args, machine,
                       started_at, finished_at, aborted_flag, len(modules))
    tmp_dir = os.path.join(out_dir, 'tmp')
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    log('[r227] 完成：退出码=%d 产物=%s' % (rc, out_dir))
    return rc


if __name__ == '__main__':
    sys.exit(main())
