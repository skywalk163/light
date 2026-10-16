# -*- coding: utf-8 -*-
"""test_R119B_异步等待内存回收.py —— R119-B（原生腿异步 `等待` 协程回收修复）。

被测缺陷（R119-B，深水区）：
  原生腿（LLVM 后端）协程调度器在协程完成后**从不释放** LightCoroutine /
  LightFuture / args / locals，且 g_scheduler.num_coros 只增不减（上限
  DV_MAX_COROUTINES=4096）。长循环（如分布式 worker 的「逐任务执行」「心跳/
  注册」）每轮新建一个被 await 的子协程，累积泄漏（口语化记为「`节点 --sample`
  残余内存涨 ~29 MB/s」）。

修复位置：`src/llvm/runtime_typed.c`
  - LightFuture 加 `refcount` / `owner` 字段；新增 `dv_future_ref` /
    `dv_future_unref` / `dv_coro_free`。
  - `dv_coro_await` 两个分支（目标已就绪 / 挂起）各 +1；`dv_coro_get_await_result`
    读结果后 -1；归零即释放 future；当持有者协程已完成且为最后引用时，由
    `dv_future_unref` 连带 `dv_coro_free` 回收该协程（含 args/locals/result）。
  - 仅回收「被 await 的子协程 + 其 future」；顶层入口协程与 timer/io_wait 伪装
    future 不走 refcount（互不相干，详见 runtime_typed.c R119-B 注释块）。

验证结论（关键，避免误读）：
  本修复**确证**解决了「协程从不回收 / num_coros 只增不减」这一根因。但实测发现：
  受 DV_MAX_COROUTINES=4096 上限约束，原生腿存活协程数在任意情形都被封顶在 4096，
  因此协程泄漏本身在合成程序里是有界的（峰值 RSS 不会无限增长）。复现报告中的
  ~29 MB/s **无界**增长需要真实的分布式 worker 链路（socket 收发包体 / 请求对象等
  每轮分配），该链路原生腿无法在本环境真跑、也无法用合成程序等价替代。故：
  - 协程回收修复 = 必要且正确，消除 4096 封顶处的功能退化（撞顶后 `dv_coro_create`
    返回 NULL、`等待` 静默吞值）与协程内存积压；
  - 29 MB/s 无界增长的主导根因很可能在分布式模块的另一条每轮分配路径，需对真实
    `节点` worker 做内存画像（valgrind/heaptrack 或 RSS 采样）才能定位，属独立任务。

本测试的定位（务实）：
  B1 是**功能正确性回归护栏**——验证修复后的 await 长循环在两腿都产出 `总数=10000`，
  即修复没有破坏正常的「每轮 等待 子协程」语义（修复若引入 double-free / 计数错位，
  此处会 rc!=0 或总数错位）。它**不**作为「泄漏检测器」：合成程序的协程数受 4096
  封顶，关掉修复也只会封顶、不会无界增长（已在本地 150000 迭代 RSS 实测印证：
  修复开/关峰值 RSS 均为 ~8.9 MB）。泄漏的无界性验证留给真实 worker 画像任务。

判实方式（真编译 + 真运行 + 两腿对拍，仿 test_R145_R119B_嵌套对象字段写回.py）：
  原生腿输出 == Python 腿输出 == 显式期望值 `总数=10000`。

平台：clang 可用即真编译真运行（本机 Windows 有 clang 时同跑，与 test_R145_R119B
一致）；clang 缺失则 skip。
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

_SRC = os.path.join(仓库根, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


def 写文件(目录, 文件名, 内容):
    """无 BOM 写 .light（BOM 会被词法层当字符卡住）"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(内容)
    return 路径


def 原生腿跑(主文件, 目录):
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    exe = compile_light_typed(主文件, os.path.join(目录, '产物'), optimize_level=2)
    结果 = subprocess.run([exe], timeout=120, cwd=目录, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def python腿跑(主文件, 目录):
    结果 = subprocess.run(
        [sys.executable, os.path.join(仓库根, 'cli', 'light.py'), 'run', 主文件],
        cwd=目录, timeout=180, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def 双腿跑(tmp_path, 名, 源):
    """返回 (原生腿输出, Python腿输出)。两腿都真编译/真运行。"""
    目录 = str(tmp_path / 名)
    os.makedirs(目录, exist_ok=True)
    主文件 = 写文件(目录, 名 + '.light', 源)
    原_rc, 原_出 = 原生腿跑(主文件, 目录)
    py_rc, py_出 = python腿跑(主文件, 目录)
    assert 原_rc == 0, '原生腿 rc=%s stdout=%s' % (原_rc, 原_出)
    assert py_rc == 0, 'Python 腿 rc=%s stdout=%s' % (py_rc, py_出)
    return 原_出, py_出


# B1：长循环 await 功能正确性护栏 —— 修后每轮 await 子协程均能正确回收、总数=10000。
# 构造完全复用 test_R145_R119B 的 A4 句式（类内「异步 段落」被「等待」），仅把单次
# 调用放进 10000 次循环，确保每轮都新建并 await 一个子协程。
# 入口 `主` 保持同步（原生腿直接驱动同步入口；src 腿禁止在同步段落内写 `等待`），
# 循环体放进 `异步 段落 跑循环`，由 `异步 运行 工.跑循环()` 拉起（与 A4 的
# `异步 运行 对.注册()` 同构）。每轮 `等待 己.干活()` 新建+await 一个子协程。
# 注意（实测，非直觉）：子协程是 `返回 1` 的纯常量，受 DV_MAX_COROUTINES=4096 封顶 +
# `dv_coro_await` 对 NULL target 早返回 + stale `waiting_for` 返前次值 三重兜底，
# 即使关掉回收修复，合成程序也只会在 4096 处封顶、不崩、总数仍对。故本测试**不**作为
# 泄漏检测器（见模块头 docstring），只对拍「修复无引入 double-free / 计数错位」这一
# 功能正确性维度（修复若错，rc!=0 或总数错位会在此炸出）。
B1 = """类 工人:
  异步 段落 干活(自):
    返回 1
  异步 段落 跑循环(自):
    设 总数 为 0
    设 计数 为 0
    当 计数 < 10000:
      设 值 为 等待 己.干活()
      总数 为 总数 + 值
      计数 为 计数 + 1
    输出("总数=" 加上 转字符串(总数))

段落 主():
  设 工 为 新建 工人()
  异步 运行 工.跑循环()
"""


@skip_without_clang
def test_B1_长循环await功能正确_两腿对拍(tmp_path):
    """R119-B 修复后的 await 长循环功能正确性护栏（非泄漏检测器）。

    本测试验证修复**没有破坏**正常的「每轮 等待 子协程」语义：每轮
    `等待 己.干活()` 新建并 await 一个子协程，循环跑完应得 `总数=10000`。
    修复若引入引用计数错位 / double-free，此处会 rc!=0（崩溃）或总数错位而炸出，
    因此它是「修复不回归」的硬护栏。

    诚实边界（实测证伪旧表述）：合成程序中子协程是 `返回 1` 纯常量，受
    DV_MAX_COROUTINES=4096 封顶 + `dv_coro_await` 对 NULL target 早返回 +
    stale `waiting_for` 返前次值 三重兜底，关掉回收修复也只封顶、不崩、总数仍对
    （本地 150000 迭代 RSS 修复开/关均 ~8.9 MB）。故本测试**不**能检测协程泄漏
    的无界性——无界 ~29 MB/s 增长的主导根因在分布式模块另一条每轮分配路径
    （socket 收包/请求对象），需对真实 `节点` worker 做内存画像（valgrind/heaptrack/
    RSS 采样）定位，属独立任务。详见模块头 docstring。

    断言：原生腿、Python 腿均 `总数=10000`，且两条腿一致。
    """
    原, py = 双腿跑(tmp_path, 'B1', B1)
    assert 原 == ['总数=10000'], '原生腿=%s' % 原
    assert py == ['总数=10000'], 'Python 腿=%s' % py
    assert 原 == py
