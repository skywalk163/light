# -*- coding: utf-8 -*-
"""R122-A1：原生（LLVM）腿 `_light_bytes_split` 补齐的守单点。

背景（R122 §1 A1）：`_light_bytes_split(内容, 分隔)` 是**编译器内嵌 helper**，
不是 stdlib 导出函数——光明 parser 拒绝 `b'...'.split(...)` 这种「bytes 字面量后跟
`.方法`」的成员调用（句号被当语句结束符，R72-E · L-175），所以纯光明侧的字节分帧
只能走这个 helper。转译腿在 `src/code_generator.py:1483` 把它 emit 进产物，
**原生腿此前完全没有对应实现**，`stdlib/字节缓冲.light` 编译报
「未定义的段落：_light_bytes_split」。

本文件守两层：
  1. IR 级：`_light_bytes_split` 编得出来、不残留适配层 `<unknown` 伪装、
     且真的落到 `dv_bytes_split`（不是被别的分支悄悄吃掉）；
  2. 真跑级：与转译腿 Python `bytes.split` **逐例对拍**（多段 / 尾部空段 /
     空分隔 / 无分隔符），真跑缺 clang 或 MSVC 头时 skip（抄
     `test_llvm_builtin_gaps.py` 的 `_find_msvc_env`）。

⚠️ 已知边界（不许静默降级，登记在 `docs/原生腿能力边界.md` §12.2）：
  原生腿**无一等 bytes 类型**，`b"..."` 落成 STRING（type=3）、str 字段存原始
  UTF-8 字节；因此内嵌 NUL 会被 C 串尾截断，且无法区分 str 与 bytes。
  本文件的用例全部避开这两点（纯 ASCII、无 NUL），对拍才有意义。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直呼内嵌 helper 的最小源码（不依赖 stdlib/字节缓冲，避免跨模块解析牵连）
_源码_多段 = (
    '段落 主()：\n'
    '  设 帧表 为 _light_bytes_split(b"a\\nb\\nc\\n", b"\\n")\n'
    '  打印 长度(帧表)\n'
    '  打印 帧表[0]\n'
    '  打印 帧表[1]\n'
    '  打印 帧表[2]\n'
    '  打印 帧表[3]\n'
    # 末位是空串，打印出来是空行；末尾再打一个哨兵，免得空行被 .strip() 吃掉
    '  打印 "END"\n'
    '主()。\n'
)

_源码_空分隔 = (
    '段落 主()：\n'
    '  设 单 为 _light_bytes_split(b"x", b"")\n'
    '  打印 长度(单)\n'
    '  打印 单[0]\n'
    '主()。\n'
)

_源码_无分隔符 = (
    '段落 主()：\n'
    '  设 无 为 _light_bytes_split(b"abc", b"\\n")\n'
    '  打印 长度(无)\n'
    '  打印 无[0]\n'
    '主()。\n'
)


# ----------------------------------------------------------------------
# 一、IR 级：编得出 + 落到 dv_bytes_split + 不残留伪装
# ----------------------------------------------------------------------

@pytest.mark.parametrize('名称, 源码', [
    ('多段', _源码_多段),
    ('空分隔', _源码_空分隔),
    ('无分隔符', _源码_无分隔符),
], ids=['多段', '空分隔', '无分隔符'])
def test_light_bytes_split_编得出且落到dv_bytes_split(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'
    assert 'dv_bytes_split' in ir, \
        f'{名称}：没生成 dv_bytes_split 调用（该名字被别的分支吃掉了？）'


def test_字节缓冲模块可编():
    """`stdlib/字节缓冲.light` 是 A1 的解锁目标：本模块必须能被原生腿编过。

    走 `compile_source_typed`（单模块 IR）而不是多模块入口，测的是「本模块自身
    有没有原生腿不支持的构造」，不受其依赖（本模块零导入）影响。
    """
    path = os.path.join(_ROOT, 'stdlib', '字节缓冲.light')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    ir = compile_source_typed(src)
    assert 'dv_bytes_split' in ir, '字节缓冲.light 的 IR 里没看到 dv_bytes_split'
    assert '<unknown' not in ir, '字节缓冲.light 的 IR 里残留了 <unknown 伪装'


# ----------------------------------------------------------------------
# 二、真跑：与转译腿 Python bytes.split 逐例对拍
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
    """编译 + 真跑；子进程 cwd 设为临时目录，避免往仓里写测试产物。"""
    from llvm.compiler import compile_light_typed
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r122bs_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    return r


_需真跑 = [
    pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑'),
    pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                       reason='未定位到 MSVC/Windows SDK 头，跳过'),
]


def _输出(r):
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').strip()


@_需真跑[0]
@_需真跑[1]
def test_light_bytes_split_真跑_多段与尾部空段对齐Python():
    """b"a\\nb\\nc\\n".split(b"\\n") == [b'a', b'b', b'c', b'']（尾部空段保留）。"""
    r = _运行(_源码_多段)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['4', 'a', 'b', 'c', '', 'END'], f'多段对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_light_bytes_split_真跑_空分隔返回原内容单元素列表():
    """空分隔 → helper 返回 [_b]（不是空列表、不是抛 ValueError）。"""
    r = _运行(_源码_空分隔)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['1', 'x'], f'空分隔对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_light_bytes_split_真跑_无分隔符返回原内容单元素列表():
    """分隔符没出现 → [原内容]（CPython bytes.split 同口径）。"""
    r = _运行(_源码_无分隔符)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['1', 'abc'], f'无分隔符对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_字节缓冲_真跑_跨chunk切帧与残余保留():
    """端到端：推入两次 → 按 b"\\n" 切 → 完整帧 1 个，残余留在缓冲里。

    ⚠️ 这里**不用** `缓冲.清空()`：原生腿把 `清空` 归进 mutating 内置方法集合
    （`codegen_typed.py:4026/5253`），`obj.清空()` 会被截胡成 `dv_list_clear`
    而非类方法调用（既有行为差异，非 R122 引入，登记在能力边界 §12.3）。
    """
    src = (
        '导入 字节缓冲\n'
        '段落 主()：\n'
        '  设 缓冲 为 新建 字节缓冲()\n'
        '  缓冲.推入字节(b"hello ")\n'
        '  缓冲.推入字节(b"world\\nmore")\n'
        '  设 帧 为 缓冲.按字节切(b"\\n")\n'
        '  打印 长度(帧)\n'
        '  打印 帧[0]\n'
        '  打印 缓冲.取全部()\n'
        '主()。\n'
    )
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['1', 'hello world', 'more'], f'字节缓冲对拍失败，实际：{lines!r}'
