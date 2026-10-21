# -*- coding: utf-8 -*-
"""R161 A 线回归门：L-227/L-228/L-221 协程 native 修复（R162-A 真门改造）

覆盖
----
- L-227-a：跨 await SSA dominance（跨挂起点的值物化进协程帧 locals）
- L-227-b：多导出表编号（`_seg_f*` 不重复、不越界）
- L-228：协程帧 locals 持久化（栈 alloca → 持久帧槽 `dv_coro_get_local`）
- L-221：await-join（等待已完成协程要能恢复等待方）

R162-A 改造前这道门是**假绿**：`WORK_DIR/PYTHON_EXE/COMPILER_EXE` 硬编码
`G:\\dswork\\...\\src\\lightc.exe`，0.82/0.86 上没有该 exe ⇒ 6 条用例
`NATIVE_ONLY` 全 skip、2 条 `pytest.xfail()` 无条件下 ⇒ 实跑数 0。本轮改动：

1. 仓库根从 `__file__` 推导（对齐 `tests/unit/test_R160_E5协程库.py`），删掉全部
   Windows 硬编码路径与 `lightc.exe` 依赖。
2. native 腿改走**产品路径** `llvm.compiler.compile_light_typed` 编译 + 真跑产物；
   clang 探测复用 `tests/_native_helpers.py` 的 `探测clang()`（缺 clang **skip 不许 error**）。
3. 断言升级为**行为断言**：跑出来的退出码 + stdout 必须逐行等于期望值
   （`x=42` / `V=5` / 三任务结果序 / `结果=5` / `结果=3` / `结果=42`），
   IR 只当**佐证**（`dv_coro_get_local` 调用点计数、`_seg_f*` define 无重复），
   不再用「IR 里出现某字符串」当主判据。
4. 修两条测试源码 bug（语言里根本不存在，真跑必挂）：
   `.添加` → `.追加`（列表追加方法）；`循环 3 次:` → `当 ... :`（本语言没有
   `循环 N 次` 语法，全仓仅此一处，属写测试时臆造）。
5. 删 `check_dominance_in_ir()`（恒返回 `True` 的假绿本体）与两条无条件
   `pytest.xfail()` 的假反跑用例。

反跑锚点（**手工**执行，不在本文件里写成没跑过的断言）
---------------------------------------------
- 回退 L-227-a 修复 → 双层协程用例复现 `does not dominate all uses`
- 回退 L-227-b 修复 → 多导出模块编译报 `use of undefined value '@_seg_f*'`
- 回退 L-228 修复 → 嵌套协程用例复现 0xC0000374 堆损坏
- 回退 L-221 修复 → 等待已完成协程拿不到返回值
"""

import os
import re
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src'))
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

_STDLIB = os.path.join(_ROOT, 'stdlib')

# ── 探针源码（每条只输出 `标记=值` 行，便于逐行全等断言）─────────────────────

L227A_跨await源 = """
异步 段落 测试():
  设 x 为 42
  等待 异步睡眠(0.01)
  打印("x=" 加上 转字符串(x))
  返回 x

异步 运行 测试()。
"""

L227A_双层源 = """
异步 段落 内层():
  异步睡眠(0.02)
  返回 5

异步 段落 外层():
  设 v 为 等待 内层()
  打印("V=" 加上 转字符串(v))
  返回 v

异步 运行 外层()。
"""

L227B_多导出源 = """
异步 段落 任务1():
  异步睡眠(0.01)
  返回 1

异步 段落 任务2():
  异步睡眠(0.01)
  返回 2

异步 段落 任务3():
  异步睡眠(0.01)
  返回 3

异步 段落 主流程():
  设 t1 为 创建任务(任务1())
  设 t2 为 创建任务(任务2())
  设 t3 为 创建任务(任务3())
  打印("结果1=" 加上 转字符串(等待 t1))
  打印("结果2=" 加上 转字符串(等待 t2))
  打印("结果3=" 加上 转字符串(等待 t3))

异步 运行 主流程()。
"""

L228_嵌套源 = """
异步 段落 内层():
  异步睡眠(0.02)
  返回 5

异步 段落 工人(协程函数):
  设 值 为 等待 协程函数()
  返回 值

异步 段落 主流程():
  设 结果 为 等待 工人(内层)
  打印("结果=" 加上 转字符串(结果))
  打印("完成")

异步 运行 主流程()。
"""

L228_共享表源 = """
异步 段落 工人(共享表):
  设 i 为 0
  当 i 小于 3:
    等待 异步睡眠(0.01)
    共享表.追加(1)
    设 i 为 i 加上 1
  返回 共享表.长度()

异步 段落 主流程():
  设 表 为 []
  设 任务 为 创建任务(工人(表))
  等待 异步睡眠(0.05)
  设 结果 为 等待 任务
  打印("结果=" 加上 转字符串(结果))

异步 运行 主流程()。
"""

L221_await_join源 = """
异步 段落 已完成任务():
  返回 42

异步 段落 主流程():
  设 任 为 创建任务(已完成任务())
  等待 异步睡眠(0.01)
  设 结果 为 等待 任
  打印("结果=" 加上 转字符串(结果))

异步 运行 主流程()。
"""


# ── 产品路径：编译 + 真跑 ────────────────────────────────────────────────────

def _native_run(源码: str, 超时: int = 45):
    """native 腿：`compile_light_typed` 编译 + 跑 exe，返回 (rc, stdout)。

    走**产品路径**（用户敲 `light run --backend llvm-typed` 时走的就是这条），
    不再调用仓库里并不存在的 `src/lightc.exe`。
    """
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix='_r162_nat_') as d:
        主 = os.path.join(d, '主.light')
        with open(主, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        exe = compile_light_typed(主, os.path.join(d, '产物'),
                                  optimize_level=0, search_paths=[_STDLIB])
        结果 = subprocess.run([exe], capture_output=True, timeout=超时, cwd=d,
                              text=True, encoding='utf-8', errors='replace')
        return 结果.returncode, 结果.stdout.replace('\r', '').strip()


def _ir口径(源码: str) -> dict:
    """只编译取 IR（不起 clang、不执行），返回有信号的计数/集合。

    有信号 = 「数量/集合关系」，不是「字符串 in IR」：
      * `帧槽读取`：`call ... @dv_coro_get_local` 行数（栈 alloca 退化则归零）
      * `导出定义`：`define ... @_seg_f*` 的名字列表（重名 = L-227-b 编号碰撞）
      * `协程函数`：`define void @_coro_*` 的名字列表
    """
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    ir = compile_modules_typed({'主': 源码}, main_module='主', opt_level='O0')
    return {
        '帧槽读取': len(re.findall(r'call [^@]*@dv_coro_get_local', ir)),
        '导出定义': re.findall(r'^define [^@]*@(_seg_f\w+)', ir, re.M),
        '协程函数': re.findall(r'define void @(_coro_\w+)', ir),
    }


def _断言输出(源码: str, 期望行: list):
    """行为断言：退出码 0 且 stdout 逐行等于期望（去 \\r、去首尾空白）。"""
    rc, out = _native_run(源码)
    assert rc == 0, f"退出码应 0，实得 {rc}（stdout={out!r}）"
    实际行 = [l for l in out.split('\n') if l.strip()]
    assert 实际行 == 期望行, f"输出不符：期望 {期望行}，实得 {实际行}"
    return out


# ═══════════════════════════════════════════════════════════════════════════
# L-227-a：跨 await SSA dominance
# ═══════════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_l227a_跨await值持久化():
    """跨挂起点的局部变量必须活到 resume 之后：`x=42`（不是 0／不是垃圾值）。

    IR 佐证：协程 locals 走持久帧槽 `dv_coro_get_local`，不是栈 alloca。
    """
    _断言输出(L227A_跨await源, ['x=42'])
    口径 = _ir口径(L227A_跨await源)
    assert 口径['帧槽读取'] > 0, "IR 里没有 dv_coro_get_local 调用 ⇒ locals 退回栈 alloca（L-228 形态）"
    assert 口径['协程函数'] == ['_coro_f1'], f"协程状态机函数异常：{口径['协程函数']}"


@skip_without_clang
def test_l227a_双层协程返回值():
    """两层协程 + `等待 内层()`：内层返回值要真的传回外层（`V=5`）。

    这是 L-227-a 的原始复现形态（`%5 = load %gs3` 定义在 resume_0、resume_1
    路径不经过定义块 ⇒ dominance 违反）。
    """
    _断言输出(L227A_双层源, ['V=5'])
    口径 = _ir口径(L227A_双层源)
    assert 口径['帧槽读取'] > 0, "IR 里没有 dv_coro_get_local 调用"
    assert len(口径['协程函数']) == 2, f"应生成 2 个协程状态机，实得 {口径['协程函数']}"


# ═══════════════════════════════════════════════════════════════════════════
# L-227-b：多导出表编号
# ═══════════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_l227b_多导出表三任务():
    """多段落模块（4 个异步段落）导出表编号不得碰撞/越界。

    行为断言：三个任务按创建序返回 1/2/3（乱序或缺失 = 编号复用）。
    IR 佐证：`_seg_f*` 的 define 名**无重复**（L-227-b 根因就是编号分配撞车，
    表现为 `use of undefined value '@_seg_f*'`）。
    """
    _断言输出(L227B_多导出源, ['结果1=1', '结果2=2', '结果3=3'])
    口径 = _ir口径(L227B_多导出源)
    定义 = 口径['导出定义']
    assert len(定义) == 4, f"4 个顶层段落应各有一条 _seg_f* 定义，实得 {len(定义)}：{定义}"
    assert len(set(定义)) == len(定义), f"_seg_f* 编号重复（L-227-b 回归）：{定义}"
    assert len(口径['协程函数']) == 4, f"应生成 4 个协程状态机，实得 {口径['协程函数']}"


# ═══════════════════════════════════════════════════════════════════════════
# L-228：协程帧 locals 持久化
# ═══════════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_l228_嵌套协程帧持久化():
    """嵌套协程（`工人` 里 `等待 协程函数()`）不得堆损坏：结果=5 + 完成。

    L-228 未修时这里复现 0xC0000374（Windows）/ SIGSEGV（POSIX）。
    """
    _断言输出(L228_嵌套源, ['结果=5', '完成'])
    口径 = _ir口径(L228_嵌套源)
    assert 口径['帧槽读取'] > 0, "IR 里没有 dv_coro_get_local 调用 ⇒ 帧未持久化（L-228 回归）"


@skip_without_clang
def test_l228_共享表入参():
    """共享列表作协程入参：子协程的 `追加` 必须写回调用方的同一个表（结果=3）。

    注：原用例写 `共享表.添加(1)`——语言里没有 `.添加`，列表追加是 `.追加`；
    循环也误写成 `循环 3 次:`（本语言无此语法）。两者都是测试源码 bug，已修。
    """
    _断言输出(L228_共享表源, ['结果=3'])


# ═══════════════════════════════════════════════════════════════════════════
# L-221：await-join
# ═══════════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_l221_等待已完成任务():
    """等待一个**已经跑完**的任务：等待方必须被恢复并拿到返回值（结果=42）。

    L-221 未修时等待方永远不被唤醒（用例挂死到超时）。
    """
    _断言输出(L221_await_join源, ['结果=42'])
    口径 = _ir口径(L221_await_join源)
    assert 口径['帧槽读取'] > 0, "IR 里没有 dv_coro_get_local 调用"
