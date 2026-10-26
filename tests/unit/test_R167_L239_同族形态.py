# -*- coding: utf-8 -*-
"""R167-T4 回归门：L-239 同族三形态——双腿对拍 + 有牙反跑。

L-239 本尊（R166 修）：`异步 运行 X()` 中 X 是**同步段落**时 PY 腿不得崩。
本轮排查同族另外三种写法，每种一条「双腿一致」断言：

  ① `等待 X()` 而 X 是**同步段落**
       PY 腿原发 `await 同步干活()` ⇒ `await None` ⇒
       `TypeError: object NoneType can't be used in 'await' expression`；
       原生腿容忍非协程句柄、rc=0 正常跑完 ⇒ **腿不对称，本轮修复**。
       修法：`AwaitExpr`（语句与表达式两处）补判型——被等待者确证是**本模块
       同步段落**时去掉 `await`，其余（异步段落 / 函数值 / 表达式 / 导入名）
       维持原样。另把 `async_paragraphs` 的收集提前到发射前预扫描，使判型
       不依赖「被调段落写在调用点之前还是之后」。

  ② `异步 遍历 x 之 同步可迭代`
       任务书预判「B5 已用 `_light_async_iter` 运行时探测 `__aiter__`，普通
       list 不再抛」——**复核成立**，双腿已一致。本文件锁住该结论，防回退。

  ③ `异步 运行 f()` 而 f 是**函数值变量**
       任务书要求确认 R166 的「名字不可解析 ⇒ 维持 asyncio.run」这条路是
       「与原生腿一致」还是「新的不对称」。实测结论：
         · 原生腿**直接拒绝编译** `RunAsyncStmt(协程内)`（NotImplementedError，
           提示改用转译后端）⇒ 腿内调用 `异步 运行` 属于原生腿未实现的形态；
         · PY 腿自身也不一致：f 为异步段落值时 `asyncio.run(f())`
           （在协程里 ⇒ `asyncio.run() cannot be called from a running event
           loop`，rc=1），f 为同步段落值时 `asyncio.run(None)` 那条判型没命中，
           退化成 `f()` 后静默丢协程（Never awaited 警告，rc=0）。
       ⇒ 登记为语言级限制（原生腿未实现 + PY 腿语义待定），**本轮不修**，
       本文件只锁「PY 腿未回归到更坏形态」与「原生腿仍拒绝」这两条现状。

判据（0.88 权威机）
-------------------
    $ pytest tests/unit/test_R167_L239_同族形态.py -n 0 -p no:randomly -q
    期望：全绿。

反跑有牙（形态①）
-----------------
把 `_resolve_await_callable_kind` 的 `sync_paragraph` 分支改回 `'other'`
（等价于退回修前的无条件 `await`）⇒ `test_形态1_*` 三例立即转红；
本文件的 `test_形态1_反跑_去掉判型即转红` 用子进程注入该退化，自动验证有牙。
"""
import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'tests')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

_STDLIB = os.path.join(_ROOT, 'stdlib')

# ── 形态① ─ 等待 同步段落（被调段落写在调用点**之前**）
_形态1_同步在前 = (
    '段落 同步干活()：\n'
    '  输出("同步干活跑了")\n'
    '\n'
    '异步 段落 主()：\n'
    '  等待 同步干活()\n'
    '  输出("主结束")\n'
    '\n'
    '异步 运行 主()。\n'
)

# ── 形态① 反例 ─ 被调段落写在调用点**之后**（判型不得依赖声明顺序）
_形态1_同步在后 = (
    '异步 段落 主()：\n'
    '  等待 干活()\n'
    '  输出("主结束")\n'
    '\n'
    '段落 干活()：\n'
    '  输出("干活跑了")\n'
    '\n'
    '异步 运行 主()。\n'
)

# ── 形态① 负对照 ─ 等待异步段落必须继续发 await
_形态1_负对照 = (
    '异步 段落 异步干活()：\n'
    '  输出("异步干活跑了")\n'
    '\n'
    '异步 段落 主()：\n'
    '  等待 异步干活()\n'
    '  输出("主结束")\n'
    '\n'
    '异步 运行 主()。\n'
)

# ── 形态② ─ 异步 遍历 同步可迭代（列表 / 同步生成器）
_形态2_列表 = (
    '异步 段落 主()：\n'
    '  合计 为 0\n'
    '  异步 遍历 x 之 [1, 2, 3]:\n'
    '    合计 为 合计 + x\n'
    '  输出(合计)\n'
    '\n'
    '异步 运行 主()。\n'
)

# ── 形态③ ─ 异步 运行 函数值变量（异步段落值 / 同步段落值）
_形态3_异步值 = (
    '异步 段落 异步干活()：\n'
    '  输出("异步干活跑了")\n'
    '\n'
    '异步 段落 主()：\n'
    '  令 f 为 异步干活\n'
    '  异步 运行 f()\n'
    '  输出("主结束")\n'
    '\n'
    '异步 运行 主()。\n'
)

_形态3_同步值 = (
    '段落 同步干活()：\n'
    '  输出("同步干活跑了")\n'
    '\n'
    '异步 段落 主()：\n'
    '  令 f 为 同步干活\n'
    '  异步 运行 f()\n'
    '  输出("主结束")\n'
    '\n'
    '异步 运行 主()。\n'
)


def _py腿(源码: str):
    """PY 转译腿：`python -m cli.light_unified run <f>`，返回 (rc, stdout, stderr末行)。"""
    with tempfile.TemporaryDirectory(prefix='_r167_l239py_') as d:
        路径 = os.path.join(d, '探针.light')
        with open(路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        r = subprocess.run([sys.executable, '-m', 'cli.light_unified', 'run', 路径],
                           capture_output=True, timeout=180, cwd=_ROOT,
                           text=True, encoding='utf-8', errors='replace')
        out = (r.stdout or '').replace('\r', '').strip()
        err = (r.stderr or '').replace('\r', '').strip()
        return r.returncode, out, (err.splitlines()[-1] if err else '')


def _原生腿(源码: str):
    """原生腿：compile_light_typed 编译 + 运行，返回 (rc, stdout)。

    编译期 NotImplementedError（原生后端不支持的形态）以 rc='未实现' 返回，
    异常文本放在 stdout 里，供用例断言「原生腿确实拒绝了该形态」。
    """
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix='_r167_l239nat_') as d:
        主 = os.path.join(d, '主.light')
        with open(主, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        try:
            exe = compile_light_typed(主, os.path.join(d, '产物'), optimize_level=0,
                                      search_paths=[_STDLIB])
        except NotImplementedError as e:
            return '未实现', f'{type(e).__name__}: {e}'
        r = subprocess.run([exe], capture_output=True, timeout=60, cwd=d, text=True,
                           encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout or '').replace('\r', '').strip()


def _生成码(源码: str) -> str:
    """只走 codegen（不执行），用于结构性佐证。"""
    from light_parser_v3 import LightParser  # type: ignore[import]
    from code_generator import PythonCodeGenerator  # type: ignore[import]
    return PythonCodeGenerator().generate(LightParser().parse(源码), is_main=False)


# ══════════════════════════════════════════════════════════════════════
# 形态①：等待 同步段落
# ══════════════════════════════════════════════════════════════════════

def test_形态1_同步段落_PY腿不崩且输出正确():
    """修前 rc=1 + `object NoneType can't be used in 'await' expression`。"""
    rc, out, err = _py腿(_形态1_同步在前)
    assert rc == 0, f'PY 腿仍崩（rc={rc}）：{err}'
    assert out.splitlines() == ['同步干活跑了', '主结束'], f'PY 腿输出漂移：{out!r}'


def test_形态1_同步段落写在调用点之后_同样不崩():
    """判型不得依赖声明顺序：段落写在调用点之后，PY 腿同样 rc=0。

    这条钉的是 `_prescan_async_paragraphs`——若去掉预扫描、退回「发射到该段落
    才登记」，本用例立即转红（`await 干活()` ⇒ NoneType）。
    """
    rc, out, err = _py腿(_形态1_同步在后)
    assert rc == 0, f'声明顺序依赖回归（rc={rc}）：{err}'
    assert out.splitlines() == ['干活跑了', '主结束'], f'PY 腿输出漂移：{out!r}'


def test_形态1_生成码_同步段落不套await():
    """结构性佐证：同步段落恰好 0 处 `await`，异步段落恰好 1 处。"""
    同步码 = _生成码(_形态1_同步在前)
    异步码 = _生成码(_形态1_负对照)
    n_sync = 同步码.count('await 同步干活()')
    n_async = 异步码.count('await 异步干活()')
    assert n_sync == 0, f'同步段落仍被 await（{n_sync} 处）：\n{同步码}'
    assert n_async == 1, f'异步段落的 await 调用点应恰好 1 处，实际 {n_async} 处'


@skip_without_clang
def test_形态1_双腿对拍_同步段落输出一致():
    """双腿对拍：PY 腿与原生腿的 rc 与 stdout 必须完全一致。"""
    rc_n, out_n = _原生腿(_形态1_同步在前)
    rc_p, out_p, err_p = _py腿(_形态1_同步在前)
    assert rc_n == rc_p == 0, f'两腿 rc 不一致：native={rc_n} py={rc_p}（py stderr：{err_p}）'
    assert out_n == out_p == '同步干活跑了\n主结束', \
        f'两腿输出分歧：native={out_n!r} py={out_p!r}'


@skip_without_clang
def test_形态1_负对照_异步段落两腿仍一致():
    """负对照：等待异步段落走 await 的路径不得被本次改动影响。"""
    rc_n, out_n = _原生腿(_形态1_负对照)
    rc_p, out_p, err_p = _py腿(_形态1_负对照)
    assert rc_n == rc_p == 0, f'两腿 rc 不一致：native={rc_n} py={rc_p}（py stderr：{err_p}）'
    assert out_n == out_p == '异步干活跑了\n主结束', \
        f'两腿输出分歧：native={out_n!r} py={out_p!r}'


def test_形态1_反跑_去掉判型即转红(tmp_path):
    """有牙反跑：把 `sync_paragraph` 判型退化成 `other`（= 修前无条件 await），
    同一份探针必须转红。

    做法：把 `cli/` 与 `src/` 整份**复制**到 `tmp_path`（pytest 自带、由它清理），
    在**副本**里退化判型，再用副本的 `cli.light_unified` 跑探针——磁盘上的
    产品代码一个字节都不改。

    为什么不能进程内 monkeypatch：`-m cli.light_unified` 是全新进程，会重新
    import 生成器（第一版反跑因此**假绿**：RC=0 却判不出有牙，已改本方案）。
    为什么不走 `PYTHONPATH` 注入：子进程环境变量的改写在本机被沙箱拦下
    （`PermissionError: CHAT_REFERENCE_PROTECTED`），副本自带 CLI 则不依赖环境。
    为什么不用 `tempfile.TemporaryDirectory`：其退出清理会撞本机沙箱的删除审计
    而挂住（实测卡在 `os.unlink`），改用 pytest 托管目录。
    """
    import shutil

    d = str(tmp_path)
    for 子 in ('cli', 'src'):
        shutil.copytree(os.path.join(_ROOT, 子), os.path.join(d, 子),
                        ignore=shutil.ignore_patterns('__pycache__'))
    目标 = os.path.join(d, 'src', 'code_generator.py')
    with open(目标, encoding='utf-8') as f:
        原文 = f.read()
    # 只退化「确证是同步段落」这一步：把该分支的返回改成 'other'
    退化后 = 原文.replace(
        "        if 名 in self.sync_paragraphs:\n            return 'sync_paragraph'\n",
        "        if 名 in self.sync_paragraphs:\n            return 'other'\n", 1)
    assert 退化后 != 原文, '注入点没找到：`sync_paragraph` 判型分支已改形，反跑失效'
    with open(目标, 'w', encoding='utf-8', newline='\n') as f:
        f.write(退化后)

    探针 = os.path.join(d, '探针.light')
    with open(探针, 'w', encoding='utf-8', newline='\n') as f:
        f.write(_形态1_同步在前)

    # 先证明副本的生成码确实退化成 `await 同步干活()`
    r码 = subprocess.run(
        [sys.executable, '-c',
         'import sys; sys.path.insert(0, %r)\n'
         'from light_parser_v3 import LightParser\n'
         'from code_generator import PythonCodeGenerator\n'
         'src = open(%r, encoding="utf-8").read()\n'
         'print(PythonCodeGenerator().generate(LightParser().parse(src), is_main=False))'
         % (os.path.join(d, 'src'), 探针)],
        capture_output=True, timeout=120, text=True, encoding='utf-8',
        errors='replace', cwd=d)
    assert r码.returncode == 0, f'反跑副本生成码失败：{r码.stderr[-800:]}'
    assert 'await 同步干活()' in r码.stdout, \
        f'副本没退化成功（仍无 await）⇒ 反跑无意义：\n{r码.stdout[-800:]}'

    r = subprocess.run([sys.executable, '-m', 'cli.light_unified', 'run', 探针],
                       capture_output=True, timeout=180, cwd=d,
                       text=True, encoding='utf-8', errors='replace')
    err = (r.stderr or '').replace('\r', '').strip()
    assert r.returncode == 1, \
        f'去掉判型后探针仍绿（rc={r.returncode}）⇒ 断言无牙：stdout={r.stdout!r}'
    assert "can't be used in 'await' expression" in err, \
        f'转红原因不是预期的 await TypeError：{err[-800:]}'


# ══════════════════════════════════════════════════════════════════════
# 形态②：异步 遍历 同步可迭代（B5 已泛化，锁结论）
# ══════════════════════════════════════════════════════════════════════

def test_形态2_PY腿_普通列表可异步遍历():
    """B5 用 `_light_async_iter` 运行时探测 `__aiter__`，普通 list 回退为逐个 yield。"""
    rc, out, err = _py腿(_形态2_列表)
    assert rc == 0, f'PY 腿崩（rc={rc}）：{err}'
    assert out == '6', f'PY 腿输出漂移：{out!r}'


def test_形态2_生成码_用_light_async_iter包装():
    """结构性佐证：`异步 遍历` 必须经 `_light_async_iter(...)`，不得裸发 async for。"""
    码 = _生成码(_形态2_列表)
    assert 码.count('async for x in _light_async_iter(') == 1, \
        f'异步遍历未走 _light_async_iter：\n{码}'
    assert 码.count('async def _light_async_iter(') == 1, '缺少 _light_async_iter 辅助函数'


@skip_without_clang
def test_形态2_双腿对拍_列表异步遍历一致():
    rc_n, out_n = _原生腿(_形态2_列表)
    rc_p, out_p, err_p = _py腿(_形态2_列表)
    assert rc_n == rc_p == 0, f'两腿 rc 不一致：native={rc_n} py={rc_p}（py stderr：{err_p}）'
    assert out_n == out_p == '6', f'两腿输出分歧：native={out_n!r} py={out_p!r}'


# ══════════════════════════════════════════════════════════════════════
# 形态③：异步 运行 函数值变量（登记语言级限制，只锁现状）
# ══════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_形态3_原生腿_拒绝编译协程内异步运行():
    """原生腿对腿内 `异步 运行` 一律 NotImplementedError，提示改用转译后端。

    这条不是「腿一致」断言，而是把**原生腿未实现**的事实钉住：一旦哪天原生腿
    补上该形态，本用例会转红，提醒按双腿对拍口径重新登记。
    """
    rc_n, msg_n = _原生腿(_形态3_异步值)
    assert rc_n == '未实现', f'原生腿不再拒绝该形态（rc={rc_n}）：{msg_n!r}'
    assert 'RunAsyncStmt' in msg_n and '转译后端' in msg_n, \
        f'原生腿拒绝理由漂移：{msg_n!r}'
    rc_s, msg_s = _原生腿(_形态3_同步值)
    assert rc_s == '未实现', f'原生腿不再拒绝该形态（rc={rc_s}）：{msg_s!r}'


def test_形态3_PY腿_函数值不被误判为同步段落():
    """PY 腿侧的结构佐证：`异步 运行 f()`（f 为函数值变量）不得被本轮改动。

    本轮判型只落在「`等待 X()` 且 X 可解析为本模块同步段落」上；`异步 运行`
    分支保持 R166 原样。这里用「生成码里不出现 `await f(`」+「仍是 `f()` 调用」
    两条钉住现状：形态① 的判型没有外溢到函数值路径。
    """
    码 = _生成码(_形态3_同步值)
    assert 'await f(' not in 码, f'形态① 判型外溢到函数值路径（出现了 await f(））：\n{码}'
    assert '\n    f()' in 码, f'函数值调用形态被改动：\n{码}'
    assert 'async def 主' in 码, '主段落应仍为协程'


def test_形态3_PY腿_同步段落值不崩():
    """现状锁定：f 为同步段落值时 rc=0（R166 的「名字不可解析 ⇒ asyncio.run」
    判型把它按同步段落直调，协程被静默丢弃只剩 Never-awaited 警告）。

    这不是本轮修的形态（原生腿对腿内 `异步 运行` 整体未实现，无从对拍）；
    锁住是为了「不修也不许变得更坏」——真回潮成 rc=1 时本用例转红。
    """
    rc, out, err = _py腿(_形态3_同步值)
    assert rc == 0, f'PY 腿由「静默丢弃」恶化成崩溃（rc={rc}）：{err}'
    assert out.splitlines() == ['同步干活跑了', '主结束'], f'PY 腿输出漂移：{out!r}'
