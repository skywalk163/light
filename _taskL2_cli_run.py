# -*- coding: utf-8 -*-
"""临时诊断：按 运行.py 链路调用 cli.light 的 cmd_run（_taskL2_ 前缀，收尾清理）。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = r'G:\dswork\duan-light-merge\light-merge-task-L2'
for p in [LIGHT_MERGE, os.path.join(LIGHT_MERGE, 'src')]:
    if p not in sys.path:
        sys.path.insert(0, p)
entry = r'G:\dswork\duan-light-merge\lightharness\examples\test_L006.light'
from cli.light import main as light_main
sys.argv = ['light', 'run', entry]
try:
    rc = light_main()
    print('rc =', rc)
except SystemExit as e:
    print('SystemExit rc =', e.code)
