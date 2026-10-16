# -*- coding: utf-8 -*-
"""R153：两腿 `是空` 语义探针——同一份 .light 分别走 src 腿（生成 Python 后 exec）
与 原生腿（LLVM 编译后跑），逐输入打印判定，用于定 broaden 前后的行为差异。"""
import os
import subprocess
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, 'src'))

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
from llvm.compiler import compile_light_typed  # noqa: E402


def run_src(path):
    src = open(path, 'r', encoding='utf-8').read()
    ast = LightParser().parse(src)
    code = PythonCodeGenerator().generate(ast)
    g = {'__name__': '__main__'}
    try:
        exec(compile(code, path, 'exec'), g)
    except Exception as e:
        return 'SRC 失败: %s: %s' % (type(e).__name__, str(e)[:200])
    if '主' in g and callable(g['主']):
        g['主']()
    return ''


def run_native(path):
    with tempfile.TemporaryDirectory(prefix='_nat3_') as d:
        exe = compile_light_typed(path, os.path.join(d, 'p'), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=120)
        return (r.stdout.decode('utf-8', errors='replace').replace('\r', '')
                + ('ERR:' + r.stderr.decode('utf-8', errors='replace')[:200] if r.returncode else ''))


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '探针是空语义.light')
    print('===== SRC 腿 =====')
    print(run_src(p))
    print('===== 原生腿 =====')
    print(run_native(p))
