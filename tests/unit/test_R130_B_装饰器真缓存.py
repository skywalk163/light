# -*- coding: utf-8 -*-
"""R130-B：对象池缓存装饰器真缓存实现（原生腿 O0 真跑）。

任务书 §3.4 验收判据：
  1. @缓存装饰器 装饰的函数，同参数第二次调用走缓存（不执行原函数）。
  2. 记忆化 装饰的函数，行为同上。
  3. LRU缓存装饰器 保持直通退化（红线 5，本轮不翻面）。

实现要点（B 线）：
  - 嵌套段落捕获外层缓存表 + 函数值形参 原函数（R130-A 能力）。
  - 调用位用**固定参数**（§3.3-1 降级：函数值调用位暂不支持 *参数 展开）。
  - 键 = 转字符串(参数)；本轮不做容量淘汰（§3.3-3）。

无 clang 时跳过（不阻塞交付）。
"""
import os
import subprocess
import sys
import tempfile

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))


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


_需要 = (
    pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑'),
    pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                       reason='未定位到 MSVC/Windows SDK 头，跳过'),
)


def _运行(源码, 超时=300):
    from llvm.compiler import compile_light_typed
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r130b_', dir=_REPO) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    return r


def _行(r):
    text = r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').replace('\r', '\n')
    lines = [l for l in text.split('\n') if l.strip() != '']
    return lines


_BASE = '''
从 对象池缓存 导入 缓存装饰器 记忆化 LRU缓存装饰器

段落 计算(值):
  返回 值 乘以 值
'''


_需要[0]
_需要[1]
def test_真跑_缓存装饰器_同参命中异参独立():
    """@缓存装饰器：同参第二次命中缓存不执行原函数；异参独立缓存。"""
    src = _BASE + '''
段落 主:
  设 装饰器 为 缓存装饰器(10)
  设 装饰 为 装饰器(计算)
  输出(转文本(装饰(5)))
  输出(转文本(装饰(5)))
  输出(转文本(装饰(6)))
  输出(转文本(装饰(5)))
'''
    r = _运行(src)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[-400:]
    assert _行(r) == ['25', '25', '36', '25'], _行(r)


_需要[0]
_需要[1]
def test_真跑_记忆化_同参命中异参独立():
    """记忆化：同上行为。"""
    src = _BASE + '''
段落 主:
  设 记忆 为 记忆化(计算)
  输出(转文本(记忆(3)))
  输出(转文本(记忆(3)))
  输出(转文本(记忆(4)))
'''
    r = _运行(src)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[-400:]
    assert _行(r) == ['9', '9', '16'], _行(r)


_需要[0]
_需要[1]
def test_真跑_LRU缓存装饰器_保持直通():
    """红线 5：LRU缓存装饰器 保持直通退化，行为等价原函数。"""
    src = _BASE + '''
段落 主:
  设 装饰器 为 LRU缓存装饰器(16)
  设 装饰 为 装饰器(计算)
  输出(转文本(装饰(2)))
  输出(转文本(装饰(3)))
'''
    r = _运行(src)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[-400:]
    # 直通：不缓存，仍执行原函数
    assert _行(r) == ['4', '9'], _行(r)


_需要[0]
_需要[1]
def test_真跑_多装饰器实例_缓存表独立():
    """两个 缓存装饰器 实例各自独立缓存表（捕获外层缓存表不共享）。"""
    src = _BASE + '''
段落 主:
  设 装饰器1 为 缓存装饰器(10)
  设 装饰器2 为 缓存装饰器(10)
  设 装1 为 装饰器1(计算)
  设 装2 为 装饰器2(计算)
  输出(转文本(装1(5)))
  输出(转文本(装2(5)))
  输出(转文本(装1(5)))
'''
    r = _运行(src)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[-400:]
    assert _行(r) == ['25', '25', '25'], _行(r)