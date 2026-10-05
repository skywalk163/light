# -*- coding: utf-8 -*-
"""R116-A：原生（LLVM）后端 `使用 X 为 Y：`（WithStmt）与 `断言 …`（AssertStmt）收口。

背景（红线单 #LM-RED-WithStmt / #LM-RED-AssertStmt）：
  v3 的 `WithStatement` / `AssertStmt` 在适配层**没有转换器**，被降级成
  `<unknown:WithStatement>` / `<unknown:AssertStmt>` 伪装标识符，原生腿只能报
  「暂不支持语句类型」。R116-A 把它们转正：
    * WithStmt：进入调 `X.__进入__()` 并把返回值绑给 `Y`，执行体，离开调 `X.__退出__()`，
      且**体抛异常也走 `__退出__`** 再重抛（对齐 Python `with`）。`__进入__`/`__退出__`
      经既有通用方法调用 `dv_call_method` 发起。
    * AssertStmt：条件为真 → 运行期 no-op（生成的条件分支绕开失败块；失败块的
      异常创建代码是运行期不执行的死代码，模块里仍可见 `AssertionError` 常量，无害）；
      条件为假 → 抛 AssertionError（复用 `dv_create_exception_with_cause`）。

⚠️ 双下划线名约定：light 类用**中文** dunder（`__进入__`/`__退出__`）定义方法，对象方法表
也存中文名；转译后端在生成 Python 时才映射到 `__enter__`/`__exit__`。原生腿直接发中文名——
若发英文 `__enter__`，`dv_call_method` 查不到方法 → 返回 null，绑定变量变 `空`。

RunAsyncStmt 经核查：原生腿缺顶层异步运行所需 runtime 设施（事件循环 / 线程），属任务书
明确的「砍线」情形，不硬写，仅在 `docs/原生腿能力边界.md` §1.4 登记缺口与建议。
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
_CODEGEN_PY = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')


# ----------------------------------------------------------------------
# 一、IR 级：编得出来，且不残留 <unknown 伪装
# ----------------------------------------------------------------------

_编译用例 = [
    ('with-基本绑定',
     '设 f 为 1。\n'
     '使用 f 为 g：\n'
     '  打印 g。\n'
     '结束。\n'),
    ('with-体多语句',
     '设 计数 为 0。\n'
     '使用 计数 为 c：\n'
     '  设 c 为 c 加 1。\n'
     '  打印 c。\n'
     '结束。\n'),
    ('assert-真',
     '断言 1 等于 1。\n'
     '打印 "ok"。\n'),
    ('assert-假',
     '断言 1 等于 2。\n'
     '打印 "不应到达"。\n'),
    # 体抛异常也走 __退出__：__退出__ 里打印 "退出了" 来证明它被调用
    ('with-异常路径仍走退出',
     '类 管理器：\n'
     '  属性 资源。\n'
     '  构造()：\n'
     '    己资源 为 "资源"\n'
     '  段落 __进入__()：\n'
     '    返回 资源\n'
     '  段落 __退出__(错误)：\n'
     '    打印 "退出了"\n'
     '    返回 空\n'
     '段落 主()：\n'
     '  设 m 为 新建 管理器()\n'
     '  使用 m 为 r：\n'
     '    断言 1 等于 2。\n'
     '  打印 "不应到达"\n'
     '主()。\n'),
]


@pytest.mark.parametrize('名称, 源码', _编译用例, ids=[c[0] for c in _编译用例])
def test_编得出且不残留伪装(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'


def test_assert_假_必须生成_AssertionError_抛出():
    """断言失败不能静默吞掉——IR 里必须有 AssertionError 异常创建 + 抛出。"""
    ir = compile_source_typed('断言 1 等于 2。\n')
    assert 'AssertionError' in ir, '假断言没生成 AssertionError 类常量'
    assert 'dv_create_exception_with_cause' in ir, '假断言没走异常创建路径'


# ----------------------------------------------------------------------
# 二、静态护栏：白名单 + 分派不能悄悄丢
# ----------------------------------------------------------------------

def test_适配层白名单含_WithStatement_AssertStmt():
    """静态护栏：`_to_list_stmts` 的语句白名单必须含 WithStatement / AssertStmt。

    漏了它，`使用`/`断言` 会被包成 ExpressionStatement，原生腿的分派永远匹配不到——
    这是 R10-11b `生成`、R114 `全局` 踩过的同一个坑，同一个白名单第二次踩。
    """
    with open(_COMPILER_PY, encoding='utf-8') as f:
        src = f.read()
    i = src.find('def _to_list_stmts')
    assert i > 0, '找不到 _to_list_stmts'
    body = src[i:i + 2500]
    assert 'ast.WithStatement' in body, '_to_list_stmts 白名单里没有 WithStatement'
    assert 'ast.AssertStmt' in body, '_to_list_stmts 白名单里没有 AssertStmt'


def test_代码生成分派含_WithStatement_AssertStmt():
    """静态护栏：`_gen_statement` 的 isinstance 分派链必须含两条分支，且真有实现方法。

    防止日后重构把 WithStmt / AssertStmt 的分派静默删掉（那样又会退回 <unknown>）。
    """
    with open(_CODEGEN_PY, encoding='utf-8') as f:
        src = f.read()
    assert '_gen_typed_with' in src, '缺少 _gen_typed_with 实现'
    assert '_gen_typed_assert' in src, '缺少 _gen_typed_assert 实现'
    # 分派链里必须 isinstance 命中
    assert "isinstance(stmt, ast.WithStatement)" in src, '_gen_statement 没有 WithStatement 分支'
    assert "isinstance(stmt, ast.AssertStmt)" in src, '_gen_statement 没有 AssertStmt 分支'


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


def _运行(源码, 超时=300):
    from llvm.compiler import compile_light_typed
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r116wa_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env)
    return r


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_assert_真_真跑打印():
    r = _运行('断言 1 等于 1。\n打印 "ok"。\n')
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert r.stdout.decode('utf-8', 'replace').strip() == 'ok', \
        f'真断言不应影响后续执行：{r.stdout.decode("utf-8", "replace")!r}'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_assert_假_真跑抛AssertionError():
    r = _运行('断言 1 等于 2。\n打印 "不应到达"。\n')
    assert r.returncode != 0, '假断言必须抛异常（非零退出），不应静默通过'
    assert '不应到达' not in r.stdout.decode('utf-8', 'replace'), \
        '假断言抛错后，后续语句不应执行'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_with_真跑_进入绑定返回值且退出执行():
    """`使用 m 为 r：` 必须把 `__进入__()` 的返回值绑给 `r`，且 `__退出__` 正常路径执行。"""
    src = ('类 管理器：\n'
           '  属性 资源。\n'
           '  构造()：\n'
           '    己资源 为 "资源"\n'
           '  段落 __进入__()：\n'
           '    返回 资源\n'
           '  段落 __退出__(错误)：\n'
           '    返回 空\n'
           '段落 主()：\n'
           '  设 m 为 新建 管理器()\n'
           '  使用 m 为 r：\n'
           '    打印 r\n'
           '  打印 "结束"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    out = r.stdout.decode('utf-8', 'replace')
    # 绑定变量 r 必须是 __进入__ 的返回值 "资源"，而非变量名 "r" 或空
    assert '资源' in out, f'with 变量没绑到 __进入__ 返回值，实际：{out!r}'
    assert '结束' in out, f'with 块后代码没执行（__退出__ 没正常返回），实际：{out!r}'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_with_真跑_异常路径仍走退出():
    """体抛异常（断言失败）也必须走 `__退出__`，且不吞异常（非零退出）。"""
    src = ('类 管理器：\n'
           '  属性 资源。\n'
           '  构造()：\n'
           '    己资源 为 "资源"\n'
           '  段落 __进入__()：\n'
           '    返回 资源\n'
           '  段落 __退出__(错误)：\n'
           '    打印 "退出了"\n'
           '    返回 空\n'
           '段落 主()：\n'
           '  设 m 为 新建 管理器()\n'
           '  使用 m 为 r：\n'
           '    断言 1 等于 2。\n'
           '  打印 "不应到达"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode != 0, f'体抛异常必须向上传播（非零退出），实际 rc={r.returncode}'
    out = r.stdout.decode('utf-8', 'replace')
    assert '退出了' in out, f'异常路径 __退出__ 没被调用，实际：{out!r}'
    assert '不应到达' not in out, '异常被吞了，后续语句不应执行'
