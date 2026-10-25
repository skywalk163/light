# -*- coding: utf-8 -*-
"""test_R165_L235_就地闭包env.py —— R165-A（L-235）嵌套段就地按名直调 env 打包验收门。

缺陷账 §二十二（L-235）：
  嵌套段被**就地按名调用**（未先封成函数值，即 `内层()` 直调而非 `设 f 为 内层; f()`）时，
  `_gen_typed_segment_call` 发射的直调点第 4 参 env 恒 `ptr null`（IR 铁证：
  `call void @_seg_f2(ptr %13, ptr null, i32 0, ptr null)`）。R130 的堆 env 只在
  `_gen_segment_function_value`（段名封函数值）路径构建；直调路径不构建 ⇒ 段入口
  `_emit_closure_env_unpack` 读到 NULL，原生腿把自由变量静默读成 0/空。
  与 L-232（协程闭包 env）同源不同投影：R163-A 修的是「封成函数值再 dv_call_value」
  路径，不覆盖就地直调。

本门三类断言：
  ① 行为三探针（stdout 行精确，clang 真跑）：
     - 同步就地：`同步就地=11`（修前自由变量读 0 ⇒ 0+1=1，输出 `同步就地=1`）
     - 异步就地：`异步就地合法=11`（异步嵌套段就地直调 + 等待）
     - 负对照：无自由变量的嵌套段 `负对照=11`（free_vars 为空必须仍传 null，不受影响）
  ② IR 佐证（计数/正则，禁止裸 `in` 字符串近似）：
     - 同步/异步探针的嵌套段直调点 `@_seg_*` 第 4 参是寄存器（env 包），不是 `ptr null`；
     - 负对照探针的嵌套段直调点第 4 参仍为 `ptr null`（勿误打包）。
  ③ clang 探测走 tests/_native_helpers.py 探测clang()：缺 clang = skip 不是 error。

反跑有牙（任务书硬要求，不写进本文件自动化，由 T-1 交付报告手证）：
  临时把 `_gen_typed_segment_call` 的 env 打包摘掉（env_arg 恒 'null'）⇒
  探针①同步就地必须转红（输出 `同步就地=1`）；还原后转绿。
"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, 'src'))
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from _native_helpers import 探测clang  # type: ignore[import]  # noqa: E402

_STDLIB = os.path.join(_ROOT, 'stdlib')


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
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_inc and sdk_inc) else None
    return include, lib


def _运行(源码, 超时=120):
    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix='_r165_l235_', dir=_ROOT) as d:
        src_path = os.path.join(d, '主.light')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, os.path.join(d, '产物'),
                                  optimize_level=0, search_paths=[_STDLIB])
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    return r


def _输出(r):
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').strip()


# ======================================================================
# 探针源码（行为与 IR 佐证共用）
# ======================================================================

# ① 同步就地：外层局部 `计=10`，嵌套段 `内层` 就地按名直调读它。
_同步就地源 = '''段落 主():
  设 计 为 10
  段落 内层():
    返回 计 加上 1
  设 r 为 内层()
  打印("同步就地=" 加上 r)
'''

# ② 异步就地：异步嵌套段就地直调 + 等待（env 经 wrapper 克隆进协程帧）。
_异步就地源 = '''异步 段落 主():
  设 计 为 10
  异步 段落 内层():
    返回 计 加上 1
  设 r 为 等待 内层()
  打印("异步就地合法=" 加上 r)

异步 运行 主()
'''

# ③ 负对照：嵌套段无自由变量，直调点 env 必须仍为 ptr null。
_负对照源 = '''段落 主():
  段落 无捕获():
    返回 5 加上 6
  设 r 为 无捕获()
  打印("负对照=" 加上 r)
'''

# 直调点形态：call void @_seg_<safe>(ptr %res, ptr <args>, i32 n, ptr <env>)
_SEG_CALL_RE = re.compile(
    r'call void @_seg_\S+\(ptr %\S+, ptr (null|%\S+), i32 \d+, ptr (null|%\S+)\)')


def _直调第4参列表(ir):
    """收集全部 @_seg_* 直调点的 (args 槽, env 槽)。"""
    return _SEG_CALL_RE.findall(ir)


# ======================================================================
# 一、IR 佐证（不依赖 clang，只取 codegen 文本）
# ======================================================================

def test_IR_同步就地直调点env非null():
    """嵌套段直调点第 4 参必须是寄存器（malloc 打包的 env），不是 ptr null。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_同步就地源)
    env_实参 = [env for (_args, env) in _直调第4参列表(ir)]
    assert any(env != 'null' for env in env_实参), \
        f'同步就地直调点未把 env 打包传入（第 4 参全为 null）：{ir[-800:]}'


def test_IR_异步就地直调点env非null():
    """异步嵌套段就地直调点同样必须传 env 包（wrapper 克隆进协程帧）。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_异步就地源)
    env_实参 = [env for (_args, env) in _直调第4参列表(ir)]
    assert any(env != 'null' for env in env_实参), \
        f'异步就地直调点未把 env 打包传入（第 4 参全为 null）：{ir[-800:]}'


def test_IR_负对照无捕获段仍传null():
    """free_vars 为空的嵌套段不得误打包：直调点第 4 参必须仍是 ptr null。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_负对照源)
    env_实参 = [env for (_args, env) in _直调第4参列表(ir)]
    assert env_实参, '未收集到任何 @_seg_ 直调点，IR 形态已变？'
    assert all(env == 'null' for env in env_实参), \
        f'无自由变量的段被误打包 env：{env_实参}；IR 尾部：{ir[-400:]}'


# ======================================================================
# 二、行为三探针（clang 真跑；缺 clang skip）
# ======================================================================

need_native = pytest.mark.skipif(探测clang() is None, reason='缺 clang：原生腿真跑跳过')


@need_native
def test_真跑_同步就地读捕获变量():
    """探针①：同步嵌套段就地直调，读外层 计=10 ⇒ 11。修前读 0 ⇒ 输出 =1。"""
    r = _运行(_同步就地源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '同步就地=11', f'输出不符：{_输出(r)!r}'


@need_native
def test_真跑_异步就地读捕获变量():
    """探针②：异步嵌套段就地直调 + 等待，env 克隆进协程帧后仍读到 10 ⇒ 11。"""
    r = _运行(_异步就地源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '异步就地合法=11', f'输出不符：{_输出(r)!r}'


@need_native
def test_真跑_负对照无捕获段不受影响():
    """探针③：无自由变量嵌套段路径（env=null）不得因本修法回归。"""
    r = _运行(_负对照源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '负对照=11', f'输出不符：{_输出(r)!r}'
