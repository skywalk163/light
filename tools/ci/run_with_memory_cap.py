# -*- coding: utf-8 -*-
"""在内存上限下跑一个脚本，超限就掐掉。

    python tools/ci/run_with_memory_cap.py <脚本路径> [上限MB] [-- 脚本参数...]

## 为什么仓库里需要这个东西

2026-08-20 事故：`tools/ci/gen_doc_examples_baseline.py` 的前身裸跑在后台，
15 分钟吃到 **15.5GB 且仍在涨**（~2GB/分钟，只增不减），靠 `Stop-Process` 掐掉。
根因是光明 parser 对 `匹配` 列表 rest 模式（`情况 [头, 尾...]`）进入不终止的
分配循环——即**被扫描的输入本身能打爆扫描器**。

关键约束：**进程内自救不可行**。Windows 上 Python 没有 SIGALRM，纯 Python 的
疯狂分配循环无法被可靠打断；等 MemoryError 抛出时机器已经被拖垮。唯一可靠的
办法是外部看门狗——所以本工具用**父进程监控子进程**，而不是在目标脚本里加超时。

任何会把 docs / examples 大批量喂给编译器的脚本，都应该经此包装跑。

## 实现口径

- Windows：父进程轮询 `GetProcessMemoryInfo`（psapi），超限 `kill`。
  没有 job object，因为我们只需要观测 + 掐，不需要硬隔离。
- POSIX：交给内核，`setrlimit(RLIMIT_AS)`，子进程自己会拿到 MemoryError/OOM。
  比轮询精确，但拿不到峰值轨迹，所以只在 Windows 上报 peak。
"""

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IS_WIN = sys.platform == 'win32'

if _IS_WIN:
    import ctypes
    from ctypes import wintypes

    class _PMC(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t)]


def _run_windows(cmd, env, cap_mb):
    """轮询式看门狗。返回 (exit_code, peak_MB, killed)。"""
    p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding='utf-8', errors='replace')
    # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    h = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, p.pid)
    peak, killed = 0.0, False
    while p.poll() is None:
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            mb = pmc.WorkingSetSize / (1024 * 1024)
            peak = max(peak, mb)
            if mb > cap_mb:
                p.kill()
                killed = True
                break
        time.sleep(0.25)
    out = p.stdout.read() if p.stdout else ''
    return p.returncode, peak, killed, out


def _run_posix(cmd, env, cap_mb):
    """交给内核 RLIMIT_AS。拿不到峰值，peak 返回 None。"""
    import resource

    limit = int(cap_mb * 1024 * 1024)

    def _cap():
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    p = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True,
                       encoding='utf-8', errors='replace', preexec_fn=_cap)
    return p.returncode, None, False, p.stdout


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    script = argv[0]
    rest = argv[1:]
    cap_mb = 1500.0
    if rest and rest[0] != '--':
        cap_mb = float(rest[0])
        rest = rest[1:]
    if rest and rest[0] == '--':
        rest = rest[1:]

    env = dict(os.environ, PYTHONUTF8='1')
    cmd = [sys.executable, script] + rest
    t0 = time.time()
    runner = _run_windows if _IS_WIN else _run_posix
    code, peak, killed, out = runner(cmd, env, cap_mb)

    print('script: %s   cap_MB: %.0f' % (script, cap_mb))
    print('killed_by_cap: %s   exit: %s   elapsed: %.1fs'
          % (killed, code, time.time() - t0))
    if peak is not None:
        print('peak_MB: %.1f' % peak)
    print('--- output ---')
    print((out or '').strip())
    if killed:
        print('\n！超上限被掐。别调大上限就完事——先查是不是又踩到一个'
              '无限分配的输入块（见本文件文档串的事故记录）。')
        return 1
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
