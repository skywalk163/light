# -*- coding: utf-8 -*-
"""R119-A：原生腿函数值补齐 —— `是函数` 判定 + `RunAsyncStmt` 异步启动。

背景（_R119_并行任务书.md §3）：
  * A1 `是函数`：R118 只落了英文 `callable`（dv_is_callable），中文「是函数」原生腿
    此前无分支（落到 `_reject_unknown_call` 报「未定义的段落/函数」）。本轮在
    `_gen_typed_builtin` 加 `是函数`/`is_function` 分支 → 新增 runtime `dv_is_function`
    （判 LightValue.type == LV_TYPE_FUNCTION）。
  * A2 `RunAsyncStmt`（`异步 运行 X()。`）：原生腿此前缺 L1 适配器转换器 + L2 语句白名单
    + L3 分派，整条链缺失，直接报「暂不支持语句类型 RunAsyncStmt」。runtime 协程调度器
    （dv_coro_run_to_completion 等）在 R10-11b 已就绪，故本轮 L1/L2/L3 三处补齐即转正，
    无需新建异步运行时——解锁 `节点.light`（原「明确拒绝」→ 可编）。

IR 级：编得过、无 `<unknown` 残留；真跑级：语义对齐转译腿（clang 编译 + 执行）。
"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed, compile_light_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CODEGEN_PY = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')


# ----------------------------------------------------------------------
# 一、IR 级：编得出来，且不残留 <unknown 伪装
# ----------------------------------------------------------------------

_是函数源码 = (
    '段落 回调()：\n'
    '  返回 1\n'
    '段落 主()：\n'
    '  设 a 为 是函数(回调)\n'
    '  设 b 为 是函数(42)\n'
    '  打印 a\n'
    '  打印 b\n'
    '主()。\n'
)

_异步运行源码 = (
    '异步 段落 子()：\n'
    '  打印 "跑了"\n'
    '异步 运行 子()。\n'
)


def test_是函数_编得出且不残留伪装():
    ir = compile_source_typed(_是函数源码)
    assert len(ir) > 1000, f'IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, 'IR 里残留了适配层的 <unknown 伪装'


def test_是函数_IR含dv_is_function():
    ir = compile_source_typed(_是函数源码)
    assert 'dv_is_function' in ir, '是函数 分支没生成 dv_is_function 调用'


def test_异步运行_编得出且不残留伪装():
    ir = compile_source_typed(_异步运行源码)
    assert len(ir) > 1000, f'IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, 'IR 里残留了适配层的 <unknown 伪装'


def test_异步运行_IR含dv_coro_run_to_completion():
    ir = compile_source_typed(_异步运行源码)
    assert 'dv_coro_run_to_completion' in ir, '异步运行 分支没生成 dv_coro_run_to_completion 调用'


def test_异步运行_分派链登记在代码():
    """反向验证：RunAsyncStmt 必须真的出现在 _gen_statement 的分派链上
    （不是靠别的通路蒙混过关）。"""
    with open(_CODEGEN_PY, encoding='utf-8') as f:
        src = f.read()
    assert "isinstance(stmt, ast.RunAsyncStmt)" in src, \
        '_gen_statement 没分派 RunAsyncStmt'


# ----------------------------------------------------------------------
# 二、真跑：语义必须跟转译腿一致（clang 编译 + 执行）
# ----------------------------------------------------------------------

def _find_msvc_env():
    if os.name != 'nt':
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"
    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(vs_base, year, edition, "VC", "Tools", "MSVC")
                if not os.path.isdir(inc_root):
                    continue
                for ver in sorted(os.listdir(inc_root), reverse=True):
                    cand_inc = os.path.join(inc_root, ver, "include")
                    cand_lib = os.path.join(inc_root, ver, "lib", "x64")
                    if os.path.isdir(cand_inc) and os.path.isdir(cand_lib):
                        msvc_inc, msvc_lib = cand_inc, cand_lib
                        break
                if msvc_inc:
                    break
            if msvc_inc:
                break
    sdk_inc = sdk_lib = None
    if os.path.isdir(kits_base):
        inc_root = os.path.join(kits_base, "Include")
        if os.path.isdir(inc_root):
            for ver in sorted(os.listdir(inc_root), reverse=True):
                parts = [os.path.join(inc_root, ver, x) for x in ("ucrt", "shared", "um")]
                if all(os.path.isdir(p) for p in parts):
                    sdk_inc = parts
                    sdk_lib = [os.path.join(kits_base, "Lib", ver, x, "x64")
                               for x in ("ucrt", "um")]
                    break
    include = ";".join([msvc_inc] + sdk_inc) if (msvc_inc and sdk_inc) else None
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_lib and sdk_lib) else None
    return include, lib


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


def _运行(源码, 超时=300):
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r119fp_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env)
    return r


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_是函数_真跑_函数值真_非函数值假():
    r = _运行(_是函数源码)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    out = r.stdout.decode('utf-8', 'replace')
    assert '真' in out, f'是函数(函数值) 应返回真，实际：{out!r}'
    assert '假' in out, f'是函数(非函数值) 应返回假，实际：{out!r}'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_异步运行_真跑_执行异步段():
    r = _运行(_异步运行源码)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    out = r.stdout.decode('utf-8', 'replace')
    assert '跑了' in out, f'异步运行 应驱动子段执行并打印，实际：{out!r}'
