"""临时诊断（不并入主线）：用用例自带的严格 master 复现 解析响应/中文字段 段错误。

用法：REPO=<仓库根> python tools/segv_218_probe.py [--asan] [--ir]
"""
import importlib.util
import os
import re
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
IR = '--ir' in sys.argv


def dump_ir():
    txt = open('客户.ll', encoding='utf-8', errors='replace').read()
    for fn in ('_method_f78_f81', '_method_f83_f77'):
        mth = re.search(r'^define [^\n]*@' + re.escape(fn) + r'\(', txt, re.M)
        if not mth:
            print(f'--- {fn}: 未找到 define')
            continue
        start = mth.start()
        nxt = txt.find('\ndefine', start + 1)
        body = txt[start: nxt if nxt > 0 else len(txt)]
        print(f'===== {fn} =====')
        for ln in body.splitlines():
            s = ln.strip()
            if any(k in s for k in ('dv_slot_release', 'dv_slot_set', 'dv_owned_dup',
                                    'dv_take', 'dv_move', 'dv_copy_own', 'dv_ret_finalize',
                                    'dv_temp_release', 'dv_class_set_member', 'dv_json',
                                    'dv_own', 'dv_len', 'dv_str')):
                print('   ', s[:200])
        print()


with m.严格主控({'结果': {'消息': '中文测试'}, '错误': None}) as 主控:
    with open('客户.light', 'w', encoding='utf-8', newline='\n') as f:
        f.write(m._客户端程序(主控.端口))
    exe = compile_light_typed('客户.light', '客户', optimize_level=0)
    if IR:
        dump_ir()
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
