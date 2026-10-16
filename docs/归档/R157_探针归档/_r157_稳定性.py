# -*- coding: utf-8 -*-
"""R157 A 线 · _module_has_imports 稳定性探针 v2（轻量，单进程连跑）。"""
import os
import sys
import time

REPO = os.path.dirname(os.path.abspath(__file__))
for p in ('src', 'stdlib', 'contrib'):
    sys.path.insert(0, os.path.join(REPO, p))

import _light_import_hook  # noqa: E402
_light_import_hook.install([os.path.join(REPO, 'stdlib'),
                            os.path.join(REPO, 'contrib'), REPO])

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200

from 中国行政区划 import ChinaRegion  # noqa: E402
from llvm.compiler import _module_has_imports  # noqa: E402

r = ChinaRegion()
code = ['从 中国行政区划 导入 获取行政区划代码', '段落 主:']
for n, c in r._region_code_map.items():
    code.append('  输出(获取行政区划代码("%s"))' % n)
for n, c in [("湛江市", "440800"), ("中山市", "442000"),
             ("东莞市", "441900"), ("金华市", "330700")]:
    code.append('  输出(获取行政区划代码("%s"))' % n)
src = '\n'.join(code)

false_cnt = 0
err_cnt = 0
timings = []
for i in range(N):
    t0 = time.time()
    try:
        v = _module_has_imports(src)
        if v is not True:
            false_cnt += 1
    except Exception as e:
        err_cnt += 1
        if err_cnt <= 3:
            print(f"  异常#{err_cnt} @{i}: {type(e).__name__}: {str(e)[:80]}")
    timings.append(time.time() - t0)

print(f"[稳定性] {N} 次 _module_has_imports 调用")
print(f"  False: {false_cnt}  异常: {err_cnt}  True: {N - false_cnt - err_cnt}")
print(f"  avg={sum(timings)/len(timings)*1000:.1f}ms  "
      f"max={max(timings)*1000:.1f}ms  min={min(timings)*1000:.1f}ms")