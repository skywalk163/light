# -*- coding: utf-8 -*-
"""test_R163_L232_协程闭包env.py —— R163-A（L-232）协程闭包捕获外层变量验收门。

缺陷账 §二十一（L-232）：
  异步嵌套段 `异步 段落 内层()` 捕获外层局部变量 `计` 时，协程状态机既不收 %env
  形参、dv_coro_create 也不传 env、帧里不给自由变量槽 ⇒ codegen 兜底把 `计` 降级成
  标识符字符串常量，`计 加上 1` 退化为字符串拼接 `计1`。

本门三类断言（R163 任务书 A 线 §2.3）：
  ① 行为三探针（stdout 行精确）：
     - 异步闭包捕获：`异步闭包=11`（修前 = `异步闭包=计1`）
     - 同步闭包对照：`同步闭包=11`（同步腿本就正确，防两腿分歧）
     - 异步无捕获阴性对照：`异步无捕获=11`（无捕获路径不得回归）
  ② IR 佐证（计数/集合，禁止裸 `in` 字符串近似）：
     - 状态机 define 行带 `ptr %env` 第 5 参；
     - dv_coro_create 调用点带 env 实参；
     - 协程体里不出现「被捕获变量名的字符串常量」（对照修前的 .str.30 = "计"）。
  ③ clang 探测走 tests/_native_helpers.py 探测clang()：缺 clang = skip 不是 error。

反跑有牙（任务书硬要求，不写进本文件自动化，由 A 线交付报告手证）：
  摘掉状态机 %env 形参（或 dv_coro_create 不传 env）⇒ 探针①必须转红（不是 skip、
  不是静默绿）；还原后转绿。
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
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_inc and sdk_lib) else None
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
    with tempfile.TemporaryDirectory(prefix='_r163_l232_', dir=_ROOT) as d:
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
# 一、IR 佐证（不依赖 clang，只取 codegen 文本）
# ======================================================================

# 探针①源码（与真跑共用）：异步闭包捕获外层局部 `计`。
_异步闭包源 = '''段落 造(计):
  异步 段落 内层():
    返回 计 加上 1
  返回 内层

异步 段落 主():
  设 f 为 造(10)
  设 v 为 等待 f()
  打印("异步闭包=" 加上 v)

异步 运行 主()
'''


def test_IR_状态机签名带env第五参():
    """_coro_* 定义行必须是 5 参（含 ptr %env）。计数匹配，非裸 in。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_异步闭包源)
    匹配 = re.findall(
        r'define void @_coro_\S+\(ptr %result, ptr %coro, ptr %args, i32 %num_args, ptr %env\)',
        ir)
    assert len(匹配) >= 1, f'协程状态机 define 行未含第 5 参 ptr %env：{ir[-800:]}'


def test_IR_dv_coro_create调用点传env():
    """dv_coro_create 调用必须带 env 实参（末参 ptr %env）。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_异步闭包源)
    调用 = re.findall(r'call ptr @dv_coro_create\([^)]*ptr %env\)', ir)
    assert len(调用) >= 1, f'dv_coro_create 调用点未传 env 实参：{ir[-800:]}'


def test_IR_捕获变量不再降级为字符串常量():
    """修前 `计` 被降级成字符串常量（.str = "计"，UTF-8 E8 AE A1）。
    修后自由变量从 env 解包，IR 里不应再出现该标识符的字符串常量。"""
    from llvm.compiler import compile_source_typed  # type: ignore[import]
    ir = compile_source_typed(_异步闭包源)
    # 计 = U+8BA1 = UTF-8 字节 E8 AE A1；IR 里字符串常量转义为 \E8\AE\A1
    assert r'\E8\AE\A1' not in ir, \
        'IR 仍含「计」字符串常量 ⇒ 自由变量仍在降级为标识符字符串'


# ======================================================================
# 二、行为三探针（clang 真跑；缺 clang skip）
# ======================================================================

need_native = pytest.mark.skipif(探测clang() is None, reason='缺 clang：原生腿真跑跳过')


@need_native
def test_真跑_异步闭包捕获外层变量():
    """探针①：异步闭包读捕获的 `计`(=10)，10+1=11。修前输出 `异步闭包=计1`。"""
    r = _运行(_异步闭包源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '异步闭包=11', f'输出不符：{_输出(r)!r}'


_同步闭包源 = '''段落 造(计):
  段落 内层():
    返回 计 加上 1
  返回 内层

段落 主():
  设 f 为 造(10)
  设 v 为 f()
  打印("同步闭包=" 加上 v)
'''


@need_native
def test_真跑_同步闭包对照():
    """探针②：同步闭包本就正确（11），防协程修法引入两腿分歧。"""
    r = _运行(_同步闭包源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '同步闭包=11', f'输出不符：{_输出(r)!r}'


_异步无捕获源 = '''段落 造():
  异步 段落 内层():
    返回 5 加上 6
  返回 内层

异步 段落 主():
  设 f 为 造()
  设 v 为 等待 f()
  打印("异步无捕获=" 加上 v)

异步 运行 主()
'''


@need_native
def test_真跑_异步无捕获阴性对照():
    """探针③：无捕获异步段路径（env=null）不得因本修法回归。"""
    r = _运行(_异步无捕获源)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8","replace")[-500:]}'
    assert _输出(r) == '异步无捕获=11', f'输出不符：{_输出(r)!r}'
