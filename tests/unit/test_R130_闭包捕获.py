# -*- coding: utf-8 -*-
"""R130-A：codegen 嵌套段落自由变量捕获（闭包捕获）验收测试。

任务书（修订版）2.4 验收判据：
  1. 嵌套段落读取外层局部变量（值捕获）。
  2. **嵌套段落作为函数值返回**（创建后外层作用域销毁，闭包仍能读到捕获值）
     —— 依赖 2.2.2 的 **malloc 堆分配 env**；alloca 栈数组无法通过本用例。
  3. lambda 在嵌套作用域里捕获外层变量。
  4. 自由变量不与形参/局部变量冲突的边界用例。
  5. 捕获 env 的函数值被复制后，两份拷贝各自独立调用、均不崩溃（深拷贝语义）。
  6. 普通顶层段落（非嵌套）env=NULL 路径行为不变（向后兼容）。

真跑用例用子进程 + 临时目录（绝不往仓里写产物）；无 clang 时跳过（不阻塞交付）。
"""
import os
import re
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
    with tempfile.TemporaryDirectory(prefix='_r130a_', dir=_ROOT) as d:
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


def _行(r):
    """按行拆分输出（去掉尾部空行）。"""
    lines = [l for l in _输出(r).split('\n') if l.strip() != '']
    return lines


_需真跑 = [
    pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑'),
    pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                       reason='未定位到 MSVC/Windows SDK 头，跳过'),
]


# ======================================================================
# 一、静态核对：IR 层契约（不依赖 clang）
# ======================================================================

def test_段函数入口签名_含env第4参():
    """所有 @_seg_ 定义必须升级为 4 参签名 (result, args, num_args, env)。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    assert re.search(
        r"define void @_seg_\{[^\}]*\}\(ptr %result, ptr %args, i32 %num_args, ptr %env\)",
        src), '段函数入口签名未含第 4 参 env'
    assert 'ptr %result, ptr %args, i32 %num_args, ptr %env' in src, \
        '段函数定义未统一为 4 参'


def test_按名调用_传nullenv():
    """直接按名调用 @_seg_ 必须传第 4 参 null（顶层段无捕获）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    # 所有 call void @_seg_ 都带第 4 参
    assert 'i32 {num_args}, ptr null)' in src or 'i32 0, ptr null)' in src, \
        '按名调用未传第 4 参 env'


def test_函数值创建_传env指针():
    """函数值创建 dv_make_function_value 第 3 参必须来自 env 打包（或 null）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    assert 'ptr {env_ptr})' in src or 'ptr null)' in src, \
        'dv_make_function_value 未接收 env 打包结果'
    # env 必须用 malloc 堆分配（不是 alloca 栈数组）
    assert '@malloc' in src, 'env 打包未使用 malloc 堆分配'


def test_入口解包_从env参数():
    """段入口解包必须从 %env 参数取，而非全局变量（修订版 2.2.3）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
    src = open(p, encoding='utf-8').read()
    assert "icmp eq ptr {env_param}, null" in src, '解包未以 env 参数判空'
    assert "ptr {env_param}, i64 {i + 1}" in src, '解包未从 env 参数偏移取元素'


def test_runtime_透传env():
    """runtime dv_call_value 必须把 clo->env 透传为段入口第 4 参。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    assert 'fn(result, args, num_args, clo->env)' in src, \
        'dv_call_value 未透传 clo->env'
    # DvSegFunc 签名必须 4 参
    assert re.search(r'DvSegFunc\)\(LightValue\*, LightValue\*, int, LightValue\*\)',
                     src), 'DvSegFunc 未升级为 4 参'


def test_runtime_释放env():
    """dv_free 释放 FUNCTION 时必须释放 env 数组（防泄漏）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    assert 'dv_closure_env_free(clo->env)' in src, 'dv_free 未释放 env 数组'


def test_runtime_深拷贝env():
    """dv_clone 深拷贝 FUNCTION 时必须独立克隆 env 数组（防双 free/悬垂）。"""
    p = os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c')
    src = open(p, encoding='utf-8').read()
    assert 'dv_closure_env_clone(src->env)' in src, 'dv_clone 未深拷贝 env 数组'
    assert 'dst->env = src->env' not in src, 'dv_clone 仍在共享 env 指针'


# ======================================================================
# 二、真跑：嵌套段落值捕获（任务书 2.4-1）
# ======================================================================

_单自由变量 = '''
段落 外层(种子):
  设 增量 为 种子 加上 1
  段落 内层(值):
    返回 值 加上 增量
  返回 内层

段落 主():
  设 f 为 外层(10)
  打印(f(5))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_嵌套读取外层局部变量():
    """值捕获：内层段读到外层 `增量`（10+1=11），5+11=16。"""
    r = _运行(_单自由变量)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '16', f'输出不符：{_输出(r)!r}'


_多自由变量 = '''
段落 外层(甲, 乙):
  段落 内层(x):
    返回 (x 加上 甲) 乘以 乙
  返回 内层

段落 主():
  设 f 为 外层(3, 10)
  打印(f(2))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_多自由变量():
    """多个自由变量按序捕获：(2+3)*10=50。"""
    r = _运行(_多自由变量)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '50', f'输出不符：{_输出(r)!r}'


# ======================================================================
# 三、真跑：逃逸闭包（任务书 2.4-2，依赖堆分配 env）
# ======================================================================

_逃逸 = '''
段落 造闭包(基数):
  设 步长 为 基数 加上 100
  段落 内部(值):
    返回 值 加上 步长
  返回 内部

段落 主():
  设 f 为 造闭包(7)
  打印(f(1))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_逃逸闭包_外层销毁后仍可读():
    """外层段落返回后栈帧销毁，闭包仍能读到捕获值：1+107=108。"""
    r = _运行(_逃逸)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '108', f'输出不符：{_输出(r)!r}'


# ======================================================================
# 四、真跑：lambda 在嵌套作用域捕获（任务书 2.4-3）
# ======================================================================

_lambda捕获 = '''
段落 外层(n):
  段落 内部(x):
    返回 x 加上 n
  返回 内部

段落 主():
  设 f 为 外层(5)
  打印(f(3))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_lambda嵌套捕获():
    """嵌套段落里的闭包捕获逻辑同样适用于 lambda desugar：3+5=8。"""
    r = _运行(_lambda捕获)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '8', f'输出不符：{_输出(r)!r}'


# ======================================================================
# 五、真跑：自由变量与形参/局部变量不冲突（任务书 2.4-4）
# ======================================================================

_边界 = '''
段落 外层(基数):
  设 步长 为 基数 加上 1
  段落 内层(步长, 值):
    设 值 为 值 加上 1        # 局部 值 遮蔽
    返回 (值 加上 步长) 加上 基数   # 步长/值 是本段形参，基数 才是自由变量
  返回 内层

段落 主():
  设 f 为 外层(10)
  打印(f(100, 5))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_自由变量不冲突形参局部():
    """形参 步长/值 遮蔽同名外层；只有 基数 被捕获：(5+1)+100+10=116。"""
    r = _运行(_边界)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '116', f'输出不符：{_输出(r)!r}'


# ======================================================================
# 六、真跑：拷贝隔离（任务书 2.4-5，深拷贝语义）
# ======================================================================

_拷贝 = '''
段落 造闭包(基数):
  设 步长 为 基数 加上 1
  段落 内部(值):
    返回 值 加上 步长
  返回 内部

段落 主():
  设 f 为 造闭包(10)
  设 g 为 f            # dv_clone 深拷贝 env，两份独立
  打印(f(1))
  打印(g(2))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_拷贝后独立调用_不崩溃():
    """函数值复制后两份各自可独立调用、均不崩溃、结果各自正确。"""
    r = _运行(_拷贝)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _行(r) == ['12', '13'], f'输出不符：{_行(r)!r}'


_存列表 = '''
段落 造闭包(基数):
  设 步长 为 基数 加上 1
  段落 内部(值):
    返回 值 加上 步长
  返回 内部

段落 主():
  设 f 为 造闭包(10)
  设 表 为 [f]
  打印(f(1))
  打印(表[0](2))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_存列表后调用_深拷贝不悬垂():
    """函数值存列表会触发元素 dv_clone，深拷贝 env 后索引调用不崩溃。"""
    r = _运行(_存列表)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _行(r) == ['12', '13'], f'输出不符：{_行(r)!r}'


# ======================================================================
# 七、真跑：普通顶层段落 env=NULL 向后兼容（任务书 2.4-6）
# ======================================================================

_顶层 = '''
段落 加倍(值):
  返回 值 乘以 2

段落 加法(甲, 乙):
  返回 甲 加上 乙

段落 主():
  设 f 为 加倍
  打印(f(21))
  设 g 为 加法
  打印(g(3, 4))
  返回 "ok"

主()
'''


@_需真跑[0]
@_需真跑[1]
def test_真跑_普通顶层段_行为不变():
    """普通顶层段 env=NULL 路径：函数值创建/调用/传参行为完全不变。"""
    r = _运行(_顶层)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _行(r) == ['42', '7'], f'输出不符：{_行(r)!r}'


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
def test_真跑_跨模块函数值_零回归():
    """跨模块导入段封函数值后调用，env=NULL 向后兼容。"""
    r = _运行(_跨模块)
    assert r.returncode == 0, f'非零退出：{r.stderr.decode("utf-8", "replace")[-500:]}'
    assert _输出(r) == '9', f'输出不符：{_输出(r)!r}'