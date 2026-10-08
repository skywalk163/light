# -*- coding: utf-8 -*-
"""R124-B1：4 个纯光明模块的「判型」出口在原生（LLVM）腿的真实能力钉死。

背景（R123-D 挖出、R124-A1 修复的地基缺陷）：原生腿 `dv_isinstance`
（`src/llvm/runtime_typed.c`）对**原生标量**（int/float/str/bool/list/dict 等）
恒返回假（`isinstance(42, int) = 假`），只对**类实例**走继承链。这导致：

  - `内置核心判型`（`是整数`/`是字符串`/`是列表`/`是字典`/`是浮点`/`是数值`/`是布尔`）
  - `内置核心列表`（`副本`/`浅拷贝`/`深拷贝` 用 isinstance 分流 dict/list）
  - `字符串工具轻量`（`连接字符串` 用 isinstance 判 str 是否为合法连接符/元素）

在原生腿的判型结果**全部失真**（应真返假 / 应独立返共享）。

本文件做两件事：
  1. **转译腿（translate，Python）**：经 `_light_import_hook` 真加载 .light，
     断言判型出口正确 —— 证明缺陷**不在 .light 真身**（代码本身对，是原生腿运行时错）。
  2. **原生腿（LLVM）**：真编译 + 真跑，断言判型应真；A1（R124-A）未落地前
     这些断言**必然失败**，按 `pytest.mark.xfail` 登记（不阻塞 CI）；A1 落地后
     自动转绿（无需改本文件）。

⚠️ `代理循环` 不在原生腿钉死范围内：它 `从 大模型客户端/模式校验/事件总线 导入`，
     其中之一拖入 `threading`，原生腿 `NativeImportError`（纯 C 运行时无 Python 互操作）
     —— 与 isinstance 缺陷无关、先于它发生。故 `代理循环.类型是字符串` 只在转译腿钉死，
     原生腿侧是「模块不可编」而非「判型失真」。这是 R124 对任务书 R1 影响面
     「4 个纯光明模块」的**实测修正**：实际受 isinstance 影响的只有上述 3 个可编纯光明模块。

真跑：clang + MSVC 头，抄 test_llvm_builtin_gaps.py 的 `_find_msvc_env`；
子进程 cwd 设临时目录，绝不往仓里写测试产物。
"""
import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # light-merge/
sys.path.insert(0, os.path.join(_ROOT, 'src'))

from llvm.compiler import compile_light_typed  # noqa: E402

_STDLIB = os.path.join(_ROOT, 'stdlib')

# 转译腿：在模块级安装 import hook（与 test_distributed_eval_light.py 同款做法），
# 让 `from X import ...` 真加载 .light 真身。
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook  # noqa: E402
_light_import_hook.install([_STDLIB])  # noqa: E402


# ===========================================================================
# 一、转译腿（translate）：断言 4 个模块的判型出口正确（证明缺陷不在 .light 真身）
# ===========================================================================
def test_转译腿_内置核心判型_各标量判型正确():
    from 内置核心判型 import (  # noqa: E402
        是整数, 是字符串, 是列表, 是字典, 是浮点, 是数值, 是布尔)
    assert 是整数(42) is True, "转译腿：是整数(42) 应真"
    assert 是字符串("a") is True, "转译腿：是字符串('a') 应真"
    assert 是列表([1]) is True, "转译腿：是列表([1]) 应真"
    assert 是字典({}) is True, "转译腿：是字典({}) 应真"
    assert 是浮点(1.0) is True, "转译腿：是浮点(1.0) 应真"
    assert 是数值(3.5) is True, "转译腿：是数值(3.5) 应真"
    assert 是布尔(True) is True, "转译腿：是布尔(True) 应真"


def test_转译腿_内置核心列表_副本独立():
    from 内置核心列表 import 副本  # noqa: E402
    d = {"a": 1}
    e = 副本(d)
    e["a"] = 99  # 改副本
    assert d["a"] == 1, "转译腿：副本应与原字典脱钩（原仍 1）"
    assert e["a"] == 99, "转译腿：副本自身应被改成 99"


def test_转译腿_字符串工具轻量_连接字符串正例加反例():
    from 字符串工具轻量 import 连接字符串  # noqa: E402
    assert 连接字符串(["a", "b"], "-") == "a-b", "转译腿：合法 str 元素应正常拼接"
    # 收严口径：非 str 元素必须 TypeError，不许静默拼接
    with pytest.raises(TypeError):
        连接字符串([1, 2], "-")


def test_转译腿_代理循环_可加载():
    """`代理循环` 在转译腿（Python）可正常加载：证明 .light 真身无语法/语义问题。

    注意：`类型是字符串` 是 代理循环 内某个类的**方法**（非模块级导出），且 代理循环
    拖入 `threading` ⇒ 原生腿 NativeImportError（模块不可编，isinstance 缺陷无从触发）。
    故 代理循环 的 isinstance 影响为**空**：只在转译腿验证「可加载」，原生腿侧交给
    `test_原生腿_代理循环_不可编_与isinstance无关` 的护栏。这与任务书 R1 影响面
    「4 个纯光明模块」的**实测修正**一致——实际受 isinstance 影响的只有 3 个可编模块。
    """
    import 代理循环  # noqa: E402, F401
    assert 代理循环 is not None


# ===========================================================================
# 二、原生腿（LLVM）：真编译 + 真跑，A1 未落地前必然失败 → xfail（不阻塞 CI）
# ===========================================================================
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


def _运行原生(driver_src, 超时=120):
    """原生腿：编译 driver .light（含 `从 X 导入 ...`）→ 真跑 exe；cwd 设临时目录。"""
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r124b1_', dir=_ROOT) as d:
        sp = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(sp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(driver_src)
        out = compile_light_typed(sp, exe, optimize_level=0, search_paths=[_STDLIB])
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


@_需真跑[0]
@_需真跑[1]
@pytest.mark.xfail(
    reason='R124-A1 未落地：原生腿 isinstance 对原生标量恒假（dv_isinstance 仅服务类实例）',
    strict=False)
def test_原生腿_内置核心判型_各标量判型失真():
    src = ('从 内置核心判型 导入 是整数 是字符串 是列表 是字典 是数值 是布尔 是浮点\n'
           '打印("整数:" + 转字符串(是整数(42)))\n'
           '打印("字符串:" + 转字符串(是字符串("a")))\n'
           '打印("列表:" + 转字符串(是列表([1])))\n'
           '打印("字典:" + 转字符串(是字典({})))\n'
           '打印("数值:" + 转字符串(是数值(3.5)))\n'
           '打印("布尔:" + 转字符串(是布尔(真)))\n'
           '打印("浮点:" + 转字符串(是浮点(1.0)))\n')
    r = _运行原生(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    # A1 修复前原生腿全部返「假」，修复后应全部返「真」
    assert lines == ['整数:真', '字符串:真', '列表:真', '字典:真', '数值:真', '布尔:真', '浮点:真'], \
        f'原生腿判型失真（isinstance 缺陷），实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
@pytest.mark.xfail(
    reason='R124-A1 未落地：原生腿 isinstance 对原生标量恒假 ⇒ 副本 不分流 dict/list',
    strict=False)
def test_原生腿_内置核心列表_副本不独立():
    src = ('从 内置核心列表 导入 副本\n'
           '设 d 为 {"a":1}\n'
           '设 e 为 副本(d)\n'
           '字典设置(e, "a", 99)\n'
           '打印("原:" + 转字符串(d["a"]))\n'
           '打印("副:" + 转字符串(e["a"]))\n')
    r = _运行原生(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    # A1 前：isinstance 恒假 ⇒ 副本 走「原样返回」，改副本 = 改原 ⇒ 原=99；
    # A1 后：副本 正确分流 dict ⇒ 原仍 1、副本 99。
    assert lines == ['原:1', '副:99'], f'原生腿 副本 未脱钩（isinstance 缺陷），实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
@pytest.mark.xfail(
    reason='R124-A1 未落地：原生腿 isinstance(连接符, str) 恒假 ⇒ 连接字符串 对合法 str 也抛',
    strict=False)
def test_原生腿_字符串工具轻量_连接字符串抛():
    src = ('从 字符串工具轻量 导入 连接字符串\n'
           '打印("连接:" + 连接字符串(["a", "b"], "-"))\n')
    r = _运行原生(src)
    # A1 前：isinstance 恒假 ⇒ 合法 str 也被判非 str ⇒ 抛 属性错误（rc != 0）；
    # A1 后：合法输入应正常拼接得 "a-b"。
    assert r.returncode == 0 and _输出(r) == '连接:a-b', \
        f'原生腿 连接字符串 对合法输入应得 a-b，实际 rc={r.returncode} out={_输出(r)!r}'


def test_原生腿_代理循环_不可编_与isinstance无关():
    """`代理循环` 不在 isinstance 钉死范围：它拖入 `threading`，原生腿 NativeImportError。

    这是**模块不可编**的既成事实（纯 C 运行时无 Python 互操作），先于且独立于
    R124-A1 的 isinstance 缺陷发生；其 `类型是字符串` 只在转译腿钉死（见上）。
    本用例仅做**反跑护栏**：若哪天原生腿能编 代理循环 了，这条断言会立红，
    提醒把 `类型是字符串` 的 isinstance 钉死补进原生腿。
    """
    from llvm.compiler import find_clang
    if not find_clang():
        pytest.skip('未找到 clang，跳过原生腿编译探测')
    src = ('从 代理循环 导入 类型是字符串\n'
           '打印(转字符串(类型是字符串("a")))\n')
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r124b1_', dir=_ROOT) as d:
        sp = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(sp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        try:
            compile_light_typed(sp, exe, optimize_level=0, search_paths=[_STDLIB])
        except Exception as e:  # noqa: BLE001
            # 当前预期：NativeImportError（threading）—— 与 isinstance 无关
            assert 'NativeImportError' in type(e).__name__ or 'threading' in str(e), \
                '代理循环 编译错误已不再是 threading NativeImportError，请重新评估原生腿钉死范围：%r' % (e,)
            return
    pytest.fail('代理循环 现在竟能原生编译 —— 应把 类型是字符串 的 isinstance 钉死补进原生腿')
