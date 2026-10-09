# -*- coding: utf-8 -*-
"""R114-S1：原生（LLVM）后端 `全局` / `外层` 作用域声明（v3 ScopeDeclStmt）。

背景：红线单 #LM-RED-ScopeDeclStmt —— v3 的 `ScopeDeclStmt` 在适配层**没有转换器**，
被降级成 `<unknown:ScopeDeclStmt>` 伪装标识符，原生腿只能报「暂不支持语句类型
ScopeDeclStmt」。标准库 `.light` 一旦翻「纯光明实现」魔数就会撞上它。

语义对齐（实现前先定死，免得两个后端各说各话）：
  * 转译腿把 `全局 X` 编成 Python 的 `global X`：段落内读写的是**模块级**变量。
  * 原生腿没有 Python 的作用域栈，但有等价物：模块级变量本来就是 LLVM 全局
    `@__var_X`，且 `get_var` / `set_var` 已经是「`_globals` 优先于 `_local_vars`」。
    所以 `全局 X` 的落地 = **把 X 挂进 `_globals`**。

一个必须知道的差异（实测，写在这里防后人误判）：
  模块级**已经**声明过的变量，原生腿即使不写 `全局` 也照样写回全局槽（LLVM 语义：
  模块级变量是编译期分配的内存，函数内直接读写），而 Python 会当成局部。
  `全局` 真正不可替代的场景是**模块级没有同名声明**时——它把名字抬成模块级槽，
  使跨段落可见（对应 Python 里 `global X` + `X = 1` 在模块级创建 X）。
  本文件的真跑用例专门盯这一条，不盯「写了跟没写一样」的那条。

另：`外层`（nonlocal）只在嵌套段落里有意义，而嵌套段落原生腿本就不支持（先撞
SegmentDefinition），如实拒绝；模块级写 `全局` 与转译腿同口径拒绝。
"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_COMPILER_PY = os.path.join(_ROOT, 'src', 'compiler.py')


# ----------------------------------------------------------------------
# 一、IR 级：编得出来，且真的落到全局槽
# ----------------------------------------------------------------------

_编译用例 = [
    ('基本写回',
     '设 计数 为 0。\n'
     '段落 加一()：\n'
     '  全局 计数。\n'
     '  设 计数 为 计数 加 1。\n'
     '加一()。\n'
     '打印 计数。\n'),
    ('模块级无同名声明',
     '段落 加一()：\n'
     '  全局 计数。\n'
     '  设 计数 为 计数 加 1。\n'
     '加一()。\n'
     '打印 计数。\n'),
    ('多名字',
     '设 甲 为 1。\n'
     '设 乙 为 10。\n'
     '段落 改()：\n'
     '  全局 甲, 乙。\n'
     '  设 甲 为 甲 加 乙。\n'
     '改()。\n'
     '打印 甲。\n'),
    ('跨段落读写',
     '段落 加一()：\n'
     '  全局 计数。\n'
     '  设 计数 为 计数 加 1。\n'
     '段落 主()：\n'
     '  加一()。\n'
     '  加一()。\n'
     '  打印 计数。\n'
     '主()。\n'),
    # R114-S2：全局**容器**的原地修改。少了这条，`全局` 对字典/列表只能读不能改，
    # 表面「编译通过」实际表一直是空的（stdlib 拼音表就是这样全空的）。
    ('全局容器原地改',
     '设 表 为 新建字典()\n'
     '段落 填()：\n'
     '  全局 表。\n'
     '  字典设置(表, "你", "ni")\n'
     '段落 主()：\n'
     '  填()。\n'
     '  打印 字典获取(表, "你", "MISS")。\n'
     '主()。\n'),
]


@pytest.mark.parametrize('名称, 源码', _编译用例, ids=[c[0] for c in _编译用例])
def test_全局_编得出且不残留伪装(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'
    # 真正的证据：`全局` 必须真的产生一个模块级 LightValue 槽，而不是悄悄编没了
    assert re.search(r'@__var_\w+ = global', ir), f'{名称}：IR 里没有模块级全局槽声明'


# ----------------------------------------------------------------------
# 二、拒绝用例：不许静默降级
# ----------------------------------------------------------------------

def test_模块级写全局必须拒绝():
    """与转译后端同口径：`全局` 只许写在段落体内。"""
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed('全局 甲。\n设 甲 为 1。\n')
    assert '只能写在段落' in str(ei.value), f'文案没说清原因：{ei.value}'


def test_外层仍被嵌套段落拦下():
    """`外层` 只在嵌套段落里有意义。R130-A 前嵌套段落原生腿不支持，
    先撞 SegmentDefinition；R130-A 起嵌套段落（值捕获）已支持，
    `外层`（nonlocal 引用捕获）按红线 4 仍拒——报真正拦下它的 ScopeDeclStmt。"""
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(
            '段落 甲()：\n'
            '  设 计数 为 0\n'
            '  段落 乙()：\n'
            '    外层 计数。\n'
            '  乙()。\n'
            '甲()。\n')
    assert 'ScopeDeclStmt' in str(ei.value), f'报错了层：{ei.value}'


def test_适配层白名单含作用域声明():
    """静态护栏：`_to_list_stmts` 的语句白名单必须含 ScopeDeclaration。

    漏了它，`全局` 会被包成 ExpressionStatement，原生腿的分派永远匹配不到——
    这是 R10-11b `生成` 踩过的同一个坑，同一个白名单第二次踩。
    """
    with open(_COMPILER_PY, encoding='utf-8') as f:
        src = f.read()
    i = src.find('def _to_list_stmts')
    assert i > 0, '找不到 _to_list_stmts'
    body = src[i:i + 2500]
    assert 'ast.ScopeDeclaration' in body, '_to_list_stmts 白名单里没有 ScopeDeclaration'


# ----------------------------------------------------------------------
# 三、真跑：语义必须跟转译腿一致（clang 编译 + 执行）
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


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_全局_真跑_跨段落可见():
    """模块级无同名声明时，`全局` 抬出的槽必须跨段落可见（Python `global` 同语义）。"""
    src = ('段落 加一()：\n'
           '  全局 计数。\n'
           '  设 计数 为 计数 加 1。\n'
           '段落 主()：\n'
           '  加一()。\n'
           '  加一()。\n'
           '  打印 计数。\n'
           '主()。\n')
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r114_scope_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        from llvm.compiler import compile_light_typed
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=300)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert r.stdout.decode('utf-8', 'replace').strip() == '2', \
        f'跨段落写回没生效：{r.stdout.decode("utf-8", "replace")!r}'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_全局容器_原地修改必须写回全局():
    """R114-S2 回归护栏：全局字典的 `字典设置` 必须写回全局槽，不能改副本。

    根因是 `get_var` 的 globals 分支 `load` 出 SSA 后没登记槽位，`_store_dv` 于是
    另开临时槽——局部表因此生效、全局表因此丢失。表现是「编译过了但表是空的」。
    """
    src = ('设 表 为 新建字典()\n'
           '段落 填()：\n'
           '  全局 表。\n'
           '  字典设置(表, "你", "ni")\n'
           '段落 主()：\n'
           '  填()。\n'
           '  打印 字典获取(表, "你", "MISS")。\n'
           '主()。\n')
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r114_s2_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        from llvm.compiler import compile_light_typed
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=300)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert r.stdout.decode('utf-8', 'replace').strip() == 'ni', \
        f'全局容器原地修改没写回（改的是副本？）：{r.stdout.decode("utf-8", "replace")!r}'
