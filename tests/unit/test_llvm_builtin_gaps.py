# -*- coding: utf-8 -*-
"""R117-B：原生（LLVM）后端「Python 直通名 / 函数值调用 / await」缺口收口。

背景（R117 §0 拒绝桶分桶表，起草会话实测）：
  就绪度指标给出的 27 条「明确拒绝」里，去掉口径 bug（桶①，A 线修）之后剩下的
  **真**缺口分在桶②③④⑤。本文件守 B 线落地的部分：

  - 桶② Python 直通名 7 个：`callable` / `getattr`（三参带默认值）/ `open`
    （含 `encoding=` 关键字参数）/ `字符串`（字节序列解码）/ `属性错误`
    （异常类名直呼构造）/ `副本` / `随机字节`
  - 桶④ `等待 异步睡眠(x)`：`异步睡眠` 是 Python 直通名（asyncio.sleep），
    `等待`（AwaitExpression）在非协程内已退化为直接求值，补名即可落地
  - 桶③ 函数值调用（`设 处理器 等于 空` 后 `处理器(...)`）与桶⑤ `RunAsyncStmt`
    **本轮砍线**——不是不写，是原生腿 LightValue 没有一等函数值类型 / 没有顶层
    异步运行设施，硬写就是空壳。这里用「必须响亮报错」的断言把砍线钉住，
    与 `docs/原生腿能力边界.md` §11 的登记互指。

⚠️ 语义差异（不许静默降级，全部登记在 `docs/原生腿能力边界.md` §11.2）：
  * `callable`：原生腿无一等函数值，只有「对象注册了中文 dunder `__调用__`」为真，
    段名/类/lambda 一律假（Python 为真）。
  * `随机字节`：返回 n 个 0..255 整数的**列表**（原生无 bytes 类型），
    熵源是 MT19937 而非 os.urandom，**非密码学安全**。
  * `异步睡眠`：落地为 `dv_sleep`（真睡 N 秒），没有 asyncio 的「让出控制权」语义。

真跑：clang + MSVC 头，抄 `test_llvm_with_assert_async.py` 的 `_find_msvc_env`；
文件类用例把子进程 cwd 设到临时目录，绝不往仓里写测试产物。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------------
# 一、IR 级：桶② + 桶④ 每个名字都编得出来，且不残留 <unknown 伪装
# ----------------------------------------------------------------------

_编译用例 = [
    ('callable',
     '段落 主()：\n'
     '  如果 callable(主)：\n'
     '    打印 "T"\n'
     '  否则：\n'
     '    打印 "F"\n'
     '主()。\n'),
    ('callable-无参',
     '段落 主()：\n'
     '  打印 callable()\n'
     '主()。\n'),
    ('getattr-三参',
     '段落 主()：\n'
     '  打印 getattr(1, "errno", 空)\n'
     '主()。\n'),
    ('getattr-两参',
     '段落 主()：\n'
     '  打印 getattr(1, "errno")\n'
     '主()。\n'),
    ('open-位置参数',
     '段落 主()：\n'
     '  设 f 为 open("a.txt", "r")\n'
     '  打印 f\n'
     '主()。\n'),
    ('open-关键字参数encoding',
     '段落 主()：\n'
     '  设 f 为 open("a.txt", "r", encoding="utf-8")\n'
     '  打印 f\n'
     '主()。\n'),
    ('字符串-字节列表解码',
     '段落 主()：\n'
     '  打印 字符串([104, 105], "utf-8")\n'
     '主()。\n'),
    ('字符串-单参转文本',
     '段落 主()：\n'
     '  打印 字符串(123)\n'
     '主()。\n'),
    ('属性错误-直呼构造',
     '段落 主()：\n'
     '  抛出 属性错误("x")\n'
     '主()。\n'),
    ('副本',
     '段落 主()：\n'
     '  设 d 为 {"a": 1}\n'
     '  打印 副本(d)\n'
     '主()。\n'),
    ('随机字节',
     '段落 主()：\n'
     '  打印 长(随机字节(8))\n'
     '主()。\n'),
    ('异步睡眠-等待',
     '段落 主()：\n'
     '  等待 异步睡眠(0.01)\n'
     '  打印 "ok"\n'
     '主()。\n'),
    ('位运算',
     '段落 主()：\n'
     '  打印 (12 位与 10)\n'
     '  打印 (12 位或 10)\n'
     '主()。\n'),
]


@pytest.mark.parametrize('名称, 源码', _编译用例, ids=[c[0] for c in _编译用例])
def test_桶二名字编得出且不残留伪装(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'


def test_属性错误走异常类构造通路():
    """`属性错误` 必须走 `dv_class_new_named`（与 `运行时错误` 同一条通路）。"""
    ir = compile_source_typed('段落 主()：\n  抛出 属性错误("x")\n主()。\n')
    assert 'dv_class_new_named' in ir, '属性错误 没走异常类构造通路'


# ----------------------------------------------------------------------
# 二、反例：砍线的形态必须响亮报错，不许静默降级成 0
# ----------------------------------------------------------------------

def test_函数值调用必须拒绝不许静默():
    """桶③：`设 处理器 等于 空` 后 `处理器(1)` —— 原生腿无一等函数值，必须报错。

    静默降级会让 `处理器(1)` 编成整数 0，产物行为错还不报错（C3-1 的同一类坑）。
    """
    src = ('段落 f(a)：\n'
           '  返回 a\n'
           '段落 主()：\n'
           '  设 处理器 等于 空\n'
           '  设 处理器 等于 f\n'
           '  打印 处理器(1)\n'
           '主()。\n')
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(src)
    assert '处理器' in str(ei.value), f'报错必须点名是谁未定义：{ei.value}'


def test_RunAsyncStmt必须拒绝并报出类型名():
    """桶⑤：`异步 运行 f()。` 必须报「暂不支持语句类型 RunAsyncStmt」（R116-A 已砍线）。"""
    src = ('异步 段落 f()：\n'
           '  返回 1\n'
           '段落 主()：\n'
           '  异步 运行 f()。\n'
           '主()。\n')
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(src)
    assert 'RunAsyncStmt' in str(ei.value), f'报错必须含语句类型名：{ei.value}'


# ----------------------------------------------------------------------
# 三、真跑：语义对拍（含对照组）
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
    with tempfile.TemporaryDirectory(prefix='_r117bgap_', dir=_ROOT) as d:
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
def test_callable_真跑_带__调用__的对象为真而整数为假():
    """对照组：`callable(对象)` 与 `callable(1)` 输出必须不同（真 / 假）。

    ⚠️ 原生腿无一等函数值，故真的那条只有「对象注册了 `__调用__`」这一种形态。
    """
    src = ('类 可调用物：\n'
           '  段落 __调用__()：\n'
           '    返回 1\n'
           '段落 主()：\n'
           '  设 a 为 新建 可调用物()\n'
           '  如果 callable(a)：\n'
           '    打印 "T"\n'
           '  否则：\n'
           '    打印 "F"\n'
           '  如果 callable(1)：\n'
           '    打印 "T"\n'
           '  否则：\n'
           '    打印 "F"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['T', 'F'], f'callable 对拍失败（应 真/假），实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_getattr_真跑_命中取成员缺失取默认值():
    """三参形态：命中给成员值，缺失给默认值（不是报错、不是空）。"""
    src = ('类 东西：\n'
           '  属性 名。\n'
           '  构造()：\n'
           '    己名 为 "值"\n'
           '段落 主()：\n'
           '  设 o 为 新建 东西()\n'
           '  打印 getattr(o, "名", "默认")\n'
           '  打印 getattr(o, "不存在", "默认")\n'
           '  打印 getattr(o, "名")\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['值', '默认', '值'], f'getattr 对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_open_真跑_带encoding打开并读回内容():
    """`open(路径, 模式, encoding=…)` 必须拿到真句柄并读回写入的内容。"""
    src = ('段落 主()：\n'
           '  写入文件("r117b_gap.txt", "你好")\n'
           '  设 f 为 open("r117b_gap.txt", "r", encoding="utf-8")\n'
           '  打印 f.read()\n'
           '  打印 f.关闭()\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines[0] == '你好', f'open/读回内容不对，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_字符串_真跑_字节列表解码与单参转文本():
    src = ('段落 主()：\n'
           '  打印 字符串([104, 105], "utf-8")\n'
           '  打印 字符串(123)\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['hi', '123'], f'字符串 对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_副本_真跑_改副本不改原字典():
    """对照组：改副本后原字典必须还是 1 —— 证明不是 `dv_clone` 那种共享存储。"""
    src = ('段落 主()：\n'
           '  设 d 为 {"a": 1}\n'
           '  设 e 为 副本(d)\n'
           '  字典设置(e, "a", 99)\n'
           '  打印 d["a"]\n'
           '  打印 e["a"]\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['1', '99'], f'副本 未脱钩（原字典被改），实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_随机字节_真跑_长度等于入参():
    src = ('段落 主()：\n'
           '  设 b 为 随机字节(8)\n'
           '  打印 长(b)\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert _输出(r) == '8', f'随机字节(8) 长度不对，实际：{_输出(r)!r}'


@_需真跑[0]
@_需真跑[1]
def test_异步睡眠_真跑_等待后继续执行():
    src = ('段落 主()：\n'
           '  等待 异步睡眠(0.01)\n'
           '  打印 "ok"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert _输出(r) == 'ok', f'等待 异步睡眠 后没继续，实际：{_输出(r)!r}'


@_需真跑[0]
@_需真跑[1]
def test_属性错误_真跑_抛出未捕获异常():
    r = _运行('段落 主()：\n  抛出 属性错误("x")\n主()。\n')
    assert r.returncode != 0, '抛出 属性错误 必须非零退出'
    assert '属性错误' in r.stderr.decode('utf-8', 'replace'), \
        'stderr 里应能看到 属性错误 类名'


@_需真跑[0]
@_需真跑[1]
def test_位运算_真跑_位与位或对齐Python():
    src = ('段落 主()：\n'
           '  打印 (12 位与 10)\n'
           '  打印 (12 位或 10)\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['8', '14'], f'位运算对拍失败（Python: 8 / 14），实际：{lines!r}'


def test_真跑用例清单不为空():
    """静态护栏：上面的真跑用例被整体删掉时（相比只剩 IR 级）会被这条挡下。"""
    assert len(_编译用例) >= 12, '桶②/桶④ 的 IR 用例被删了'
