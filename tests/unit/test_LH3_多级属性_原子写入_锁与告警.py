# -*- coding: utf-8 -*-
"""LH 第三轮（LH-23~LH-31）修复验收。

五组用例，各钉一条口径：

1. `设 A.B.C 为 值` 多级属性赋值（LH-26）—— 对象链、字典链都要成立，
   二级（`X.Y`）与「属性+索引」的老路径必须逐字节不变（回归项）。
2. 内置 `原子写入`（LH-28）—— 内容/权限正确、不留临时文件、失败不吞异常。
3. `可重入锁()` 与「不可重入锁重复加锁立即报错」（LH-24）—— 原本是静默卡死。
4. 类内「方法名 = 己.属性名」编译期告警（LH-30）—— 有冲突要报、无冲突要静默。
5. 编译缓存 key 含 stdlib 内容指纹（LH-13/L-246）—— 改 stdlib 必须让 key 变。

harness 与 tests/unit/test_LH08_内置名与语义.py 同（legacy 后端 LightParser +
PythonCodeGenerator），只断言本组口径。
"""
import contextlib
import importlib.util
import io
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _gen(src: str) -> str:
    module = LightParser().parse(src)
    return PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
        module, is_main=True)


def _run_capture(src: str):
    """跑一段光明源码，返回 (stdout, stderr)。编译期告警走 stderr。"""
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        py = _gen(src)
    out = io.StringIO()
    g = {'__name__': '__main__', '__file__': os.path.join(_ROOT, 'tests', 'lh3.light')}
    with contextlib.redirect_stdout(out):
        exec(compile(py, '<lh3>', 'exec'), g, g)
    return out.getvalue(), err.getvalue()


def _lines(src: str):
    out, _ = _run_capture(src)
    return [ln.strip() for ln in out.strip().splitlines()]


# ---------------------------------------------------------------- LH-26 多级属性 #

def test_多级属性赋值_对象链():
    out = _lines("""
类 内层:
  段落 初始化 接收:
    设 己.值 为 1

类 外层:
  段落 初始化 接收:
    设 己.内 为 内层()

设 对 为 外层()
设 对.内.值 为 42
打印 转字符串(对.内.值)
""")
    assert out == ['42'], f'对象链三级赋值失败：{out}'


def test_多级属性赋值_字典链():
    """dict 也要走 _light_attr_set(_light_attr_get(...))，不能裸发 a.b.c = v。"""
    out = _lines("""
设 表 为 {"内": {"k": 1}}
设 表.内.k 为 9
打印 转字符串(表["内"]["k"])
""")
    assert out == ['9'], f'字典链三级赋值失败：{out}'


def test_多级属性赋值_四级():
    out = _lines("""
设 表 为 {"a": {"b": {"c": 1}}}
设 表.a.b.c 为 7
打印 转字符串(表["a"]["b"]["c"])
""")
    assert out == ['7'], f'四级赋值失败：{out}'


def test_二级属性赋值_回归():
    """二级（X.Y）仍走原 VarDecl 路径，发射的是裸 `X.Y = v`，不能变成 setter 调用。"""
    code = _gen("""
类 盒:
  段落 初始化 接收:
    设 己.内 为 1
设 对 为 盒()
设 对.内 为 5
""")
    # 助手函数本体在引导段里必然存在，所以要断言的是**调用点**没有走 setter
    assert '_light_attr_set(对' not in code, (
        '二级赋值被改成 _light_attr_set 了 —— 老路径应当保持 VarDecl 发射')
    assert '对.内 = 5' in code, code[-500:]


def test_属性加索引赋值_回归():
    """对象.属性[索引] 的老路径不受多级支持影响。"""
    out = _lines("""
类 盒:
  段落 初始化 接收:
    设 己.列 为 [1, 2]
设 对 为 盒()
设 对.列[0] 为 5
打印 转字符串(对.列[0])
""")
    assert out == ['5'], f'属性+索引赋值回归：{out}'


# ---------------------------------------------------------------- LH-28 原子写入 #

def test_原子写入_内容与权限(tmp_path):
    target = tmp_path / 'cred.json'
    out = _lines(f"""
原子写入("{target}", "甲乙", "utf-8", 384)
打印 读取文件("{target}")
""")
    assert out == ['甲乙']
    assert oct(os.stat(target).st_mode & 0o777) == '0o600', '权限没传下去'
    # 临时文件必须清干净（同目录下的 .原子写入-*.tmp）
    leftovers = [p for p in os.listdir(tmp_path) if p.startswith('.原子写入-')]
    assert leftovers == [], f'临时文件残留：{leftovers}'


def test_原子写入_缺省两参(tmp_path):
    target = tmp_path / 'plain.txt'
    out = _lines(f"""
原子写入("{target}", "内容")
打印 转字符串(文件存在("{target}"))
""")
    assert out == ['真']


def test_原子写入_覆盖写不残留(tmp_path):
    """覆盖写两次，最终内容是新值，且不堆临时文件。"""
    target = tmp_path / 'x.txt'
    out = _lines(f"""
原子写入("{target}", "一")
原子写入("{target}", "二")
打印 读取文件("{target}")
""")
    assert out == ['二']
    assert [p for p in os.listdir(tmp_path) if p.startswith('.原子写入-')] == []


# ---------------------------------------------------------------- LH-24 锁 #

def test_可重入锁_同线程可重复加锁():
    out = _lines("""
从 线程 导入 可重入锁
设 锁 为 可重入锁()
锁.加锁()
锁.加锁()
锁.释放()
锁.释放()
打印 "ok"
""")
    assert out == ['ok']


def test_不可重入锁_重复加锁立即报错而不是卡死():
    """这是本轮的核心：原来会**永久阻塞且无提示**，现在必须抛可读异常。"""
    with pytest.raises(RuntimeError) as ei:
        _run_capture("""
从 线程 导入 互斥锁
设 锁 为 互斥锁()
锁.加锁()
锁.加锁()
""")
    assert '可重入锁' in str(ei.value), '报错没给出改法'


def test_互斥锁_可重入参数形式():
    out = _lines("""
从 线程 导入 互斥锁
设 锁 为 互斥锁(可重入 = 真)
锁.加锁()
锁.加锁()
锁.释放()
锁.释放()
打印 "ok"
""")
    assert out == ['ok']


# ---------------------------------------------------------------- LH-30 告警 #

def test_属性撞方法名_编译期告警():
    _, err = _run_capture("""
类 盒:
  段落 初始化 接收:
    设 己.状态 为 {"a": 1}
  段落 状态:
    返回 "我是方法"
""")
    assert '光明·告警' in err, f'没有告警：{err!r}'
    assert '状态' in err


def test_无冲突_不告警():
    """名字不撞车时一个字都不能多说，否则告警会被当噪音关掉。"""
    _, err = _run_capture("""
类 盒:
  段落 初始化 接收:
    设 己.状态值 为 {"a": 1}
  段落 状态:
    返回 "我是方法"
""")
    assert err.strip() == '', f'误报：{err!r}'


# ------------------------------------------------------- LH-13/L-246 缓存 key #

def _load_cli():
    spec = importlib.util.spec_from_file_location(
        '_lh3_cli', os.path.join(_ROOT, 'cli', 'light_unified.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_缓存key_随stdlib内容变化(tmp_path):
    """key 只含 stdlib **路径**时，改了 stdlib 会命中旧产物 —— 这是 L-246 的根因。"""
    stdlib = os.path.join(_ROOT, 'stdlib')
    cli = _load_cli()
    k1 = cli._compile_cache_key('设 x 为 1', 'antlr', stdlib)

    probe = os.path.join(stdlib, '线程.py')
    before = os.stat(probe).st_mtime_ns
    try:
        os.utime(probe, ns=(before, before + 1_000_000_000))
        cli._STDLIB_FP_CACHE.clear()
        k2 = cli._compile_cache_key('设 x 为 1', 'antlr', stdlib)
    finally:
        os.utime(probe, ns=(before, before))
        cli._STDLIB_FP_CACHE.clear()

    assert k1 != k2, 'stdlib 变了但缓存 key 没变 —— 会命中旧产物'


def test_缓存key_稳定_不因重复计算漂移():
    stdlib = os.path.join(_ROOT, 'stdlib')
    cli = _load_cli()
    cli._STDLIB_FP_CACHE.clear()
    a = cli._compile_cache_key('设 x 为 1', 'antlr', stdlib)
    cli._STDLIB_FP_CACHE.clear()
    b = cli._compile_cache_key('设 x 为 1', 'antlr', stdlib)
    assert a == b, '同一份源码/同一份 stdlib 的 key 必须稳定，否则缓存等于没有'
