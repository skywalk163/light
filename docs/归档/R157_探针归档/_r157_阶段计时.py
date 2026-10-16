# -*- coding: utf-8 -*-
"""R157 A 线 · 阶段计时探针 v2：走完整 compile_light_typed 产品路径。"""
import os
import sys
import time
import subprocess
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(REPO, 'src'), os.path.join(REPO, 'stdlib'),
          os.path.join(REPO, 'contrib')):
    if p not in sys.path:
        sys.path.insert(0, p)

import _light_import_hook  # noqa: E402
_light_import_hook.install([os.path.join(REPO, 'stdlib'),
                            os.path.join(REPO, 'contrib'), REPO])

t0 = time.time()
from 中国行政区划 import ChinaRegion  # noqa: E402
t1 = time.time()
print(f"[A] import + ChinaRegion(): {t1 - t0:.3f}s")

r = ChinaRegion()
code = ['从 中国行政区划 导入 获取行政区划代码', '段落 主:']
exp = []
for n, c in r._region_code_map.items():
    code.append('  输出(获取行政区划代码("%s"))' % n)
    exp.append(c)
for n, c in [("湛江市", "440800"), ("中山市", "442000"),
             ("东莞市", "441900"), ("金华市", "330700")]:
    code.append('  输出(获取行政区划代码("%s"))' % n)
    exp.append(c)
src = '\n'.join(code)
t2 = time.time()
print(f"[B] 生成源码 {len(code)} 行: {t2 - t1:.3f}s")

# 关键：_module_has_imports 是否判为 True（决定走多模块还是快速路径）
from llvm.compiler import _module_has_imports  # noqa: E402
t3 = time.time()
has_imp = _module_has_imports(src)
t4 = time.time()
print(f"[C] _module_has_imports = {has_imp}  耗时 {t4 - t3:.3f}s")

# 完整 compile_light_typed（产品路径）
from llvm.compiler import compile_light_typed  # noqa: E402
t5 = time.time()
with tempfile.TemporaryDirectory(prefix='_r157_t_') as d:
    sp = os.path.join(d, '主.light')
    with open(sp, 'w', encoding='utf-8') as f:
        f.write(src)
    t6 = time.time()
    exe = compile_light_typed(sp, os.path.join(d, '产物'),
                              optimize_level=0)
    t7 = time.time()
    print(f"[D] 写文件 {t6 - t5:.3f}s   compile_light_typed O0 {t7 - t6:.3f}s")
    rr = subprocess.run([exe], capture_output=True, timeout=300, cwd=d)
    t8 = time.time()
    print(f"[E] run {t8 - t7:.3f}s  rc={rr.returncode}  "
          f"out_lines={len(rr.stdout.decode('utf-8','replace').strip().splitlines())}")
    print(f"[总] {t8 - t0:.3f}s")