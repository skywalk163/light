# -*- coding: utf-8 -*-
"""R166-T3 回归门：L-239 —— `异步 运行 X()` 中 X 是**同步段落**时 PY 腿不得崩。

缺陷回顾（缺陷账 §二十四，R165-T3 五段式登记）
------------------------------------------------
`异步 运行 同步主()。` 这种写法，原生腿（`dv_coro_run_to_completion` 收到非协程
句柄）会把段落直接跑完、rc=0；PY 转译腿却无条件生成 `asyncio.run(同步主())`，
`同步主()` 求值为 `None` ⇒ `ValueError: a coroutine was expected, got None`。
0.88 实测（修前）：

    场景 A（X 同步段落）  native (0, '同步跑')   py (1, '同步跑', 'a coroutine was expected, got None')
    场景 B（X 异步段落）  native (0, '异步跑')   py (0, '异步跑', '')

根因：`src/code_generator.py` 的 `RunAsyncStmt` 分支无条件 `asyncio.run(...)`，
缺同文件模块级 `ParagraphCall` 分支那句 `name in self.async_paragraphs` 判型。

修法：判型后同步段落直接同步调用（与原生腿对齐）；名字不可解析（函数值/动态调用）
维持 `asyncio.run` 不变。

反跑判据
--------
把 `RunAsyncStmt` 分支改回无条件 `asyncio.run(...)` ⇒ `test_PY腿_同步段落不崩`
立即转红（`a coroutine was expected, got None`）。
"""
import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'tests')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

_STDLIB = os.path.join(_ROOT, 'stdlib')

# 场景 A：被启动的是**同步**段落（L-239 本尊）
_同步源 = '段落 同步主():\n  输出("同步跑")\n异步 运行 同步主()。\n'

# 场景 B（负对照）：被启动的是异步段落，必须继续走 asyncio.run
_异步源 = '异步 段落 异步主():\n  输出("异步跑")\n异步 运行 异步主()。\n'


def _py腿(源码: str):
    """PY 转译腿：`python -m cli.light_unified run <f>`，返回 (rc, stdout, stderr末行)。"""
    with tempfile.TemporaryDirectory(prefix='_r166_l239py_') as d:
        路径 = os.path.join(d, '探针.light')
        with open(路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        r = subprocess.run([sys.executable, '-m', 'cli.light_unified', 'run', 路径],
                           capture_output=True, timeout=180, cwd=_ROOT,
                           text=True, encoding='utf-8', errors='replace')
        out = (r.stdout or '').replace('\r', '').strip()
        err = (r.stderr or '').replace('\r', '').strip()
        return r.returncode, out, (err.splitlines()[-1] if err else '')


def _原生腿(源码: str):
    """原生腿：compile_light_typed 编译 + 运行，返回 (rc, stdout)。"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix='_r166_l239nat_') as d:
        主 = os.path.join(d, '主.light')
        with open(主, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        exe = compile_light_typed(主, os.path.join(d, '产物'), optimize_level=0,
                                  search_paths=[_STDLIB])
        r = subprocess.run([exe], capture_output=True, timeout=60, cwd=d, text=True,
                           encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout or '').replace('\r', '').strip()


def _生成码(源码: str) -> str:
    """只走 codegen（不执行），用于结构性佐证。"""
    from light_parser_v3 import LightParser  # type: ignore[import]
    from code_generator import PythonCodeGenerator  # type: ignore[import]
    return PythonCodeGenerator().generate(LightParser().parse(源码), is_main=False)


def test_PY腿_同步段落不崩且输出正确():
    """L-239 本尊：`异步 运行 同步主()` 的 PY 腿必须 rc=0（修前 rc=1 + ValueError）。"""
    rc, out, err = _py腿(_同步源)
    assert rc == 0, f'PY 腿仍崩（rc={rc}）：{err}'
    assert out == '同步跑', f'PY 腿输出漂移：{out!r}'


def test_生成码_同步段落不套asyncio_run():
    """结构性佐证：同步段落不得被包 `asyncio.run(...)`；异步段落必须包。

    用 `count` 精确计数（不用 `in`）：同步源恰好 0 处、异步源恰好 1 处。
    """
    同步码 = _生成码(_同步源)
    异步码 = _生成码(_异步源)
    n_sync = 同步码.count('asyncio.run(')
    n_async = 异步码.count('asyncio.run(')
    assert n_sync == 0, f'同步段落仍被包 asyncio.run（{n_sync} 处）：\n{同步码}'
    assert n_async == 1, f'异步段落的 asyncio.run 调用点应恰好 1 处，实际 {n_async} 处'


@skip_without_clang
def test_双腿对拍_同步段落输出一致():
    """双腿对拍：修后 PY 腿与原生腿的 rc 与 stdout 必须完全一致。"""
    rc_n, out_n = _原生腿(_同步源)
    rc_p, out_p, err_p = _py腿(_同步源)
    assert rc_n == rc_p == 0, f'两腿 rc 不一致：native={rc_n} py={rc_p}（py stderr：{err_p}）'
    assert out_n == out_p == '同步跑', f'两腿输出分歧：native={out_n!r} py={out_p!r}'


@skip_without_clang
def test_负对照_异步段落两腿仍一致():
    """负对照：异步段落走 asyncio.run 的路径不得被本次改动影响。"""
    rc_n, out_n = _原生腿(_异步源)
    rc_p, out_p, err_p = _py腿(_异步源)
    assert rc_n == rc_p == 0, f'两腿 rc 不一致：native={rc_n} py={rc_p}（py stderr：{err_p}）'
    assert out_n == out_p == '异步跑', f'两腿输出分歧：native={out_n!r} py={out_p!r}'
