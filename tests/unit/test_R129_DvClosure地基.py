# -*- coding: utf-8 -*-
"""R129-E：闭包地基 Step 1 — DvClosure 结构体 + dv_make_function_value 接收 env。

任务书 §6.4 验收判据：
  1. 现有所有函数值调用测试零回归（test_llvm_first_class_fn.py 等）。
  2. 新增本文件：验证函数值创建/调用/free/clone 在 env=NULL 时行为不变。

改动核心（runtime_typed.c）：
  - 新增 DvClosure {void* fn_ptr; LightValue* env;} 结构体。
  - LV_TYPE_FUNCTION 的 str 字段语义扩展为存 DvClosure*（不改 LightValue 布局）。
  - dv_make_function_value(result, fn_ptr, env)：env=NULL 表示普通段函数，向后兼容。
  - dv_call_value：从 DvClosure 解出 fn_ptr 跳入口（env 本轮暂不透传，R130 才用）。
  - dv_free / dv_clone：补 FUNCTION 类型处理（防泄漏 / 防双 free）。

真跑用例用子进程 + 临时目录（绝不往仓里写产物）；无 clang 时跳过（不阻塞交付）。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_light_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    with tempfile.TemporaryDirectory(prefix='_r129e_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    return r


def _输出(r):
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').strip()


_需真跑 = [
    pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑'),
    pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                       reason='未定位到 MSVC/Windows SDK 头，跳过'),
]


# ======================================================================
# 一、静态核对：DvClosure 结构体与签名已落地（不依赖 clang）
# ======================================================================

def test_源码含_DvClosure_结构体():
    """E 线核心：runtime_typed.c 必须有 DvClosure 结构体定义（此前虚记）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    assert 'typedef struct' in src and 'fn_ptr' in src and 'env' in src
    assert 'DvClosure' in src
    # 确认 DvClosure 携带 fn_ptr 和 env 两个字段
    import re
    m = re.search(r'typedef struct\s*\{[^}]*\} DvClosure;', src)
    assert m, '未找到 DvClosure 结构体定义'
    body = m.group(0)
    assert 'fn_ptr' in body, 'DvClosure 缺 fn_ptr 字段'
    assert 'env' in body, 'DvClosure 缺 env 字段'


def test_dv_make_function_value_签名含env():
    """dv_make_function_value 必须接收 3 参（result, fn_ptr, env）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    import re
    m = re.search(r'void dv_make_function_value\([^)]*\)', src)
    assert m, '未找到 dv_make_function_value 定义'
    sig = m.group(0)
    assert sig.count(',') >= 2, f'签名未含 env 参数：{sig}'
    assert 'LightValue* env' in sig, f'签名未含 env 形参：{sig}'


def test_dv_call_value_从DvClosure解包():
    """dv_call_value 必须从 DvClosure 解出 fn_ptr（而非直接 (DvSegFunc)fv->str）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    import re
    # 定位 dv_call_value 函数体
    m = re.search(r'void dv_call_value\(LightValue\* result[^)]*\)\s*\{', src)
    assert m, '未找到 dv_call_value 定义'
    start = m.end()
    # 找到函数体结束（下一个顶层函数 void）
    nxt = src.find('\nvoid ', start)
    body = src[start:nxt if nxt > 0 else start + 2000]
    assert 'DvClosure' in body, 'dv_call_value 未解包 DvClosure'
    assert 'clo->fn_ptr' in body, 'dv_call_value 未用 clo->fn_ptr'


def test_dv_free_补FUNCTION分支():
    """dv_free 必须补 FUNCTION 类型释放（防 DvClosure 泄漏）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    import re
    m = re.search(r'void dv_free\(LightValue\* v\)\s*\{', src)
    assert m, '未找到 dv_free 定义'
    body = src[m.end():m.end() + 3000]
    assert 'LV_TYPE_FUNCTION' in body, 'dv_free 未处理 FUNCTION 类型'
    assert 'DvClosure' in body, 'dv_free 未释放 DvClosure'


def test_dv_clone_补FUNCTION分支():
    """dv_clone 必须补 FUNCTION 深拷贝（防双 free）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    import re
    m = re.search(r'void dv_clone\(LightValue\* result, LightValue\* v\)\s*\{', src)
    assert m, '未找到 dv_clone 定义'
    body = src[m.end():m.end() + 3000]
    assert 'LV_TYPE_FUNCTION' in body, 'dv_clone 未处理 FUNCTION 类型'
    assert 'DvClosure' in body, 'dv_clone 未深拷贝 DvClosure'


def test_codegen_IR声明_3参():
    """codegen_typed.py 的 LLVM IR 声明必须同步为 3 参。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    assert 'declare void @dv_make_function_value(ptr, ptr, ptr)' in src, \
        'IR 声明未同步为 3 参'


def test_codegen_调用_传null_env():
    """codegen 调用 dv_make_function_value 必须传第 3 参（本轮暂传 null）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    assert 'dv_make_function_value(ptr {result_slot}, ptr {segptr}, ptr null)' in src, \
        'codegen 调用未传第 3 参 env'


# ======================================================================
# 二、向后兼容回归：env=NULL 的普通段函数行为不变
# ======================================================================

_普通段函数 = '''
段落 加倍(值):
  返回 值 乘以 2

段落 主():
  设 f 为 加倍
  打印(f(21))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_普通段函数_加倍():
    """真跑：普通段函数（env=NULL）封成函数值后调用，行为不变。"""
    r = _运行(_普通段函数)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '42', f'输出不符：{_输出(r)!r}'


_函数值传参 = '''
段落 加法(甲, 乙):
  返回 甲 加上 乙

段落 主():
  设 f 为 加法
  打印(f(3, 4))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_函数值多参调用():
    """真跑：函数值带多参调用，DvClosure 解包 fn_ptr 后正常分派。"""
    r = _运行(_函数值传参)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '7', f'输出不符：{_输出(r)!r}'


_非函数值 = '''
段落 主():
  设 x 为 42
  打印(x(1))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_非函数值当函数调用_报错():
    """反例：非函数值当函数调用必须响亮抛 NotImplementedError（不静默降级）。"""
    r = _运行(_非函数值)
    # 期望非零退出 + 报错文案含类型名
    assert r.returncode != 0, f'应报错但退出码为 0：{_输出(r)!r}'
    err = r.stderr.decode('utf-8', 'replace')
    assert '函数' in err or 'NotImplementedError' in err or '不能作为函数调用' in err, \
        f'报错文案不符：{err[-400:]}'


# ======================================================================
# 三、函数值生命周期：赋值/返回/传参（free/clone 路径）
# ======================================================================

_函数值返回 = '''
段落 加倍(值):
  返回 值 乘以 2

段落 返回函数():
  设 f 为 加倍
  返回 f

段落 主():
  设 g 为 返回函数()
  打印(g(5))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_函数值作为返回值():
    """函数值作为返回值（触发 dv_clone/free 路径），env=NULL 时行为不变。"""
    r = _运行(_函数值返回)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '10', f'输出不符：{_输出(r)!r}'


_函数值列表 = '''
段落 加倍(值):
  返回 值 乘以 2

段落 主():
  设 表 为 [加倍]
  设 f 为 表[0]
  打印(f(7))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_函数值存列表_索引调用():
    """函数值存列表后索引取出调用（dv_clone/dv_free 列表元素路径）。"""
    r = _运行(_函数值列表)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '14', f'输出不符：{_输出(r)!r}'


# ======================================================================
# 四、跨模块函数值（导入段名）
# ======================================================================

_跨模块 = '''
从 数学 导入 绝对值

段落 主():
  设 f 为 绝对值
  打印(f(-9))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_跨模块函数值():
    """跨模块导入段名封成函数值后调用（DvClosure 与既有 import 通路协同）。"""
    r = _运行(_跨模块)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '9', f'输出不符：{_输出(r)!r}'