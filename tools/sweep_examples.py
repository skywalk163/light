# -*- coding: utf-8 -*-
"""
遍历 examples/ 下所有 .duan 示例，逐阶段（解析/生成/运行）报告状态。

用途：快速发现未被单元测试覆盖的示例是否存在语法/编译/运行问题。
用法：python tools/sweep_examples.py [--verbose]
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from duan_parser_v3 import DuanParser
from code_generator import PythonCodeGenerator


def sweep(path: str, verbose: bool = False) -> dict:
    results = {}
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            if not fn.endswith('.duan'):
                continue
            rel = os.path.relpath(os.path.join(root, fn), path)
            fp = os.path.join(root, fn)
            with open(fp, 'r', encoding='utf-8') as f:
                code = f.read()
            # 阶段1：解析（解析失败时 DuanParser 可能返回 None，也可能抛 ParseError）
            parser = DuanParser()
            try:
                ast = parser.parse(code)
            except Exception as e:  # noqa: BLE001
                msg = str(e).strip().splitlines()
                results[rel] = ('解析失败', msg[-1] if msg else type(e).__name__)
                continue
            if ast is None:
                errs = '\n'.join(getattr(parser, 'errors', []))
                results[rel] = ('解析失败', errs.splitlines()[0] if errs else '无错误信息')
                continue
            # 阶段2：生成 Python 代码
            try:
                py_code = PythonCodeGenerator().generate(ast)
            except Exception as e:  # noqa: BLE001
                results[rel] = ('生成失败', f'{type(e).__name__}: {e}')
                continue
            # 阶段3：运行（捕获 stdout）
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                exec(py_code, {'__name__': '__main__'})
                out = sys.stdout.getvalue().strip()
                results[rel] = ('运行OK', out[:80].replace('\n', '\\n') if out else '(无输出)')
            except Exception as e:  # noqa: BLE001
                tb = traceback.format_exc().strip().splitlines()
                msg = tb[-1] if tb else str(e)
                results[rel] = ('运行异常', msg)
            finally:
                sys.stdout = old_stdout
    return results


if __name__ == '__main__':
    verbose = '--verbose' in sys.argv
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples')
    results = sweep(base, verbose)
    ok = [k for k, v in results.items() if v[0] == '运行OK']
    bad = [k for k, v in results.items() if v[0] != '运行OK']
    print(f'共 {len(results)} 个示例：运行OK {len(ok)}，异常/失败 {len(bad)}')
    print('\n--- 运行OK ---')
    for k in ok:
        print(f'  OK    {k}')
    print('\n--- 异常/失败 ---')
    for k in bad:
        status, msg = results[k]
        print(f'  {status:<4} {k}')
        print(f'        原因: {msg}')
