# -*- coding: utf-8 -*-
"""R130-C：对象池缓存装饰器 双腿对拍（原生腿 .light vs Python 腿 .py）。

任务书 §4.1-2 验收判据（口径 §3.3-5：phase10 .py 真装饰器为规范源）：
  1. 缓存装饰器：同参数第二次调用不执行原函数（命中缓存）。
  2. 记忆化：同上。
  3. 不同参数：各自独立缓存（不串键）。
  红线 5 复核：LRU缓存装饰器 保持直通退化（每次调用都执行原函数）。

双腿对拍方式：
  - **原生腿**：`.light` 源码内 `从 对象池缓存 导入 …`，codegen 编译到 exe，
    副作用用「打印 SIDE」行计数判定缓存是否命中（同参第二次不得再打印 SIDE）。
  - **Python 腿**：直接 `from stdlib.对象池缓存 import …`（不装 hook 即走 .py），
    同样的副作用探针（`print("SIDE")`），输出格式与原生腿逐条对齐。
  - 双腿各产出同一行序列，逐值 `assert`，即 §4.2「新增对拍测试双腿一致」。

无 clang 时跳过（不阻塞交付）。
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.join(_REPO, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "src"))
if os.path.join(_REPO, "stdlib") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "stdlib"))

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402

# R13C 同款 flaky 加固：全量 xdist 时 clang/LLVM 编译竞争易超全局 --timeout=60。
# 每用例独立编译运行（3 秒级墙钟），并发下最坏实测可破 60s，故本文件整体上调超时。
pytestmark = pytest.mark.timeout(240)
sys.dont_write_bytecode = True


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


def _行(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return [l for l in text.split('\n') if l.strip() != '']


def _运行_原生腿(源码, 超时=300):
    """原生腿：compile_light_typed → exe → 运行，返回 stdout 行列表。"""
    from llvm.compiler import compile_light_typed
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r130c_native_', dir=_REPO) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[-600:]
    return _行(r.stdout.decode('utf-8', 'replace'))


def _跑_python_腿(计算体, 装饰器名, 参数):
    """Python 腿：**显式加载 `stdlib/对象池缓存` 的规范源**，口径不靠碰运气。

    全量 xdist 时某 worker 可能已装 hook；若直接 `from 对象池缓存 import ...`，
    拿到的是哪个源取决于谁先装钩子（`.py` 还是 `.light`），Python 腿对拍口径
    会被污染成不可控的混合态。所以规范源必须**显式指定**（§3.3-5）。

    R144-C：`stdlib/对象池缓存.py` 影子已清，规范源随之迁到 `.light`：
    显式经 `_light_import_hook` 加载，拿 src 腿（Python codegen）。
    对拍的另一头是原生腿（LLVM O0 子进程真跑）——两条独立后端，
    因此判据强度不下降，只是规范源从「历史 .py」换成「现役 .light」。

    以 计算 为被装饰函数（含 print("SIDE") 副作用探针），执行与原生腿相同的
    调用序列（装饰器名决定用哪个装饰器），捕获 stdout 行序列返回。
    """
    import importlib.util
    py_path = os.path.join(_REPO, 'stdlib', '对象池缓存.py')
    if os.path.isfile(py_path):
        # xdist 多 worker 并发 importlib 加载同模块名会冲突（收集不一致），用唯一名
        mod_name = '_R130_对象池缓存_py规范源_%d' % id(object())
        spec = importlib.util.spec_from_file_location(mod_name, py_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    else:
        # R144-C：`stdlib/对象池缓存.py` 影子已清（.light 首两行带「纯光明实现」
        # 魔数，运行期本就取代 .py）。规范源随之迁到 .light：**显式**经
        # `_light_import_hook` 加载，拿 src 腿（Python codegen）——与上面
        # 「显式按绝对路径加载」同一条纪律：口径必须**显式指定**，不能碰运气
        # 看哪个 worker 先装过钩子。对拍的另一头仍是原生腿（LLVM O0 子进程真跑），
        # 两条独立后端，不是同一份代码比两次。
        import _light_import_hook
        _light_import_hook.install([os.path.join(_REPO, 'stdlib')])
        sys.modules.pop('对象池缓存', None)
        try:
            mod = importlib.import_module('对象池缓存')
        finally:
            sys.modules.pop('对象池缓存', None)
    decorator = {'缓存装饰器': lambda f: mod.缓存装饰器(10)(f),
                 '记忆化': lambda f: mod.记忆化(f),
                 'LRU缓存装饰器': lambda f: mod.LRU缓存装饰器(16)(f)}[装饰器名]
    ns = {}
    exec(计算体, ns)
    计算 = ns['计算']
    装饰 = decorator(计算)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if 装饰器名 == '缓存装饰器':
            print(装饰(5))
            print(装饰(5))
            print(装饰(6))
            print(装饰(5))
        elif 装饰器名 == '记忆化':
            print(装饰(3))
            print(装饰(3))
            print(装饰(4))
        else:  # LRU缓存装饰器：.light 直通 / .py 缓存别名，同参二调用
            print(装饰(2))
            print(装饰(2))
    return _行(buf.getvalue())


_NATIVE_计算 = '''
段落 计算(值):
  打印("SIDE")
  返回 值 乘以 值
'''

_PY_计算 = '''
def 计算(值):
    print("SIDE")
    return 值 * 值
'''


@_需要[0]
@_需要[1]
def test_对拍_缓存装饰器_同参命中():
    """缓存装饰器：同参第二次不执行原函数；异参各自独立缓存。"""
    src = ('从 对象池缓存 导入 缓存装饰器\n'
           + _NATIVE_计算 +
           '''
段落 主:
  设 装饰器 为 缓存装饰器(10)
  设 装饰 为 装饰器(计算)
  输出(转文本(装饰(5)))
  输出(转文本(装饰(5)))
  输出(转文本(装饰(6)))
  输出(转文本(装饰(5)))
''')
    native = _运行_原生腿(src)
    assert native.count('SIDE') == 2, f"同参未命中缓存，SIDE 出现 {native.count('SIDE')} 次，输出={native}"
    # 双腿输出均含 SIDE 探针行 + 返回值行，逐条对齐
    assert native == ['SIDE', '25', '25', 'SIDE', '36', '25'], native
    py = _跑_python_腿(_PY_计算, '缓存装饰器', 10)
    assert py == native, f"双腿不一致：native={native} py={py}"


@_需要[0]
@_需要[1]
def test_对拍_记忆化_同参命中():
    """记忆化：同上行为。"""
    src = ('从 对象池缓存 导入 记忆化\n'
           + _NATIVE_计算 +
           '''
段落 主:
  设 记忆 为 记忆化(计算)
  输出(转文本(记忆(3)))
  输出(转文本(记忆(3)))
  输出(转文本(记忆(4)))
''')
    native = _运行_原生腿(src)
    assert native.count('SIDE') == 2, f"记忆化未命中缓存，输出={native}"
    assert native == ['SIDE', '9', '9', 'SIDE', '16'], native
    py = _跑_python_腿(_PY_计算, '记忆化', None)
    assert py == native, f"双腿不一致：native={native} py={py}"


@_需要[0]
@_需要[1]
def test_对拍_LRU缓存装饰器_保持直通():
    """R145-A 翻面：LRU缓存装饰器 已对齐 .py（真缓存），同参二调用命中缓存。

    R130 红线 5 曾裁定「LRU缓存装饰器 保持直通退化」——名带 LRU 却做不了淘汰。
    R145-A 任务书要求「以工作区 stdlib/对象池缓存.py 为参考实现修 .light，修到
    导出 API 面与语义一致」；`.py` 侧 LRU缓存装饰器 = 缓存装饰器 别名（真缓存），
    直通是分歧。本轮翻面：`.light` 的 LRU缓存装饰器 现转发 缓存装饰器（真缓存）。
    判据同步改为断言真缓存：同参二调用第二次命中，SIDE 只出现 1 次。
    """
    src = ('从 对象池缓存 导入 LRU缓存装饰器\n'
           + _NATIVE_计算 +
           '''
段落 主:
  设 装饰器 为 LRU缓存装饰器(16)
  设 装饰 为 装饰器(计算)
  输出(转文本(装饰(2)))
  输出(转文本(装饰(2)))
''')
    native = _运行_原生腿(src)
    assert native.count('SIDE') == 1, f"LRU缓存装饰器 应为真缓存（同参二调用命中 1 次 SIDE），输出={native}"
    assert native == ['SIDE', '4', '4'], native
    # 双腿一致：.light 翻面后与 .py 语义对齐（都是真缓存，SIDE=1）
    py = _跑_python_腿(_PY_计算, 'LRU缓存装饰器', 16)
    assert py == native, f"双腿不一致：native={native} py={py}"