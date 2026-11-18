"""临时诊断（不并入主线）：用用例自带的严格 master 复现 解析响应/中文字段 段错误。

用法：REPO=<仓库根> python tools/_debug_218.py [--asan]
"""
import importlib.util
import os
import subprocess
import sys

ROOT = os.environ.get('REPO', os.getcwd())
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'unit'))

spec = importlib.util.spec_from_file_location(
    't218', os.path.join(ROOT, 'tests', 'unit', 'test_R159_L218_ContentLength口径.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from llvm.compiler import compile_light_typed  # noqa: E402

ASAN = '--asan' in sys.argv

with m.严格主控({'结果': {'消息': '中文测试'}, '错误': None}) as 主控:
    with open('客户.light', 'w', encoding='utf-8', newline='\n') as f:
        f.write(m._客户端程序(主控.端口))
    exe = compile_light_typed('客户.light', '客户', optimize_level=0)
    if ASAN:
        subprocess.run(['clang', '-c', '-O1', '-g', '-fsanitize=address,undefined',
                        '客户.ll', '-o', 'a.o'], check=False)
        subprocess.run(['clang', '-c', '-O1', '-g', '-fsanitize=address,undefined',
                        os.path.join(ROOT, 'src/llvm/runtime_typed.c'), '-o', 'rt.o'],
                       check=False)
        subprocess.run(['clang', '-fsanitize=address,undefined', '-g', 'a.o', 'rt.o',
                        '-o', '客户_asan', '-lm', '-pthread'], check=False)
        exe = '客户_asan'
        os.environ['ASAN_OPTIONS'] = 'detect_leaks=0'
    r = subprocess.run([os.path.abspath(exe)], capture_output=True, text=True, timeout=180)
    print('--- rc=', r.returncode)
    print('OUT=', repr(r.stdout[-2000:]))
    print('ERR=', r.stderr[-6000:])
    print('master 记录 =', 主控.记录, '解析失败 =', 主控.解析失败)
