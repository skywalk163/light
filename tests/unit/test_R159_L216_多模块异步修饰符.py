# -*- coding: utf-8 -*-
"""test_R159_L216_多模块异步修饰符.py —— R159-A（L-216）多模块编译路径丢弃 `异步`。

被测缺陷（R158-C 坐实，R159-A 修复）：
  `src/llvm/compiler.py::compile_modules_typed` 的段落生成循环**不传 modifiers**，
  于是任何带 import 的（多模块）原生腿程序，其全部 `异步 段` 都按普通函数生成：
  无协程状态机、`创建任务` 实参立即求值、模块级 `异步 运行` 直接跑完。
  后果：原生分布式 worker 的**领任务循环永不可达**（实测领任务=0/12874）。
  对照：单模块路径（`codegen_typed.generate()`）一直是传的，所以单文件程序正常
  —— 这正是本缺陷长期没被发现的原因（探针都在单模块里写）。

**判据核心是 IR 实证，不是行为绿**：本缺陷的假绿形态正是「看起来能跑，但协程根本
没生成」（同步执行 + `等待` 退化成透传，结果值照样正确）。所以 A1 直接数 IR 里的
协程函数 / switch case-range / `dv_coro_create` 调用点。

覆盖：
  A1 IR 实证：多模块探针的 IR 必须有 `_coro_*` 函数 + switch 状态机 + 创建点；
     修复前这三项全为 0（只余 declare，故计数只统计**调用点**，不统计 declare）。
  A2 行为实证：多模块程序里「心跳协程」与「主循环」必须**真交织**
     （同步语义下心跳会先跑完，主循环根本轮不到）。
  A3 `等待` 对非协程值必须透传（L-216 修复前靠「同步退化」隐式成立的语义，
     修好后必须显式成立，否则 stdlib 里 `等待 同步段落()` 会拿到 空）。
  A4 嵌套段定义不得被算进外层协程的挂起点（多算 → switch 引用从未 emit 的
     resume 标签 → clang: use of undefined value）。

反跑（证明断言有牙，已在 R159-A 现场做过）：
  把 `compiler.py` 里新加的 `modifiers = codegen._segment_modifiers.get(reg_key, [])`
  删掉（恢复不传）→ A1 三项计数立刻归零、A2 变成「心跳先跑完」→ 转红。
  恢复后全绿。反跑不写进自动化用例（它需要改 src/，属 CI 不该做的事）。

平台：本机 Windows 只做初筛（L0）；权威证据在 0.82，Linux 平台证据在 0.86。
"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

_测试目录 = os.path.dirname(os.path.abspath(__file__))
_仓库根 = os.path.dirname(os.path.dirname(_测试目录))
if os.path.join(_仓库根, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(_仓库根, 'src'))
if os.path.join(_仓库根, 'tests') not in sys.path:
    sys.path.insert(0, os.path.join(_仓库根, 'tests'))

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')

辅助源 = (
    "异步 段落 干活(值):\n"
    "  睡眠(10)\n"
    "  返回 值 加 1\n"
    "\n"
    "导出 干活\n"
)

主源 = (
    "从 辅助 导入 干活\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 任务 为 创建任务(干活(41))\n"
    "  设 结果 为 等待 任务\n"
    "  打印(结果)\n"
    "\n"
    "异步 运行 主流程()。\n"
)


def _写文件(目录, 名, 内容):
    路径 = os.path.join(目录, 名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as f:
        f.write(内容)
    return 路径


def _多模块IR():
    """直接用 compile_modules_typed 拿合并 IR（不起 clang，快）。"""
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    return compile_modules_typed({'主': 主源, '辅助': 辅助源},
                                 main_module='主', opt_level='O0')


def _多模块编译并跑(tmp_path, 名, 主文件源, 辅助文件源):
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    目录 = os.path.join(str(tmp_path), 名)
    os.makedirs(目录, exist_ok=True)
    _写文件(目录, '辅助.light', 辅助文件源)
    主 = _写文件(目录, '主.light', 主文件源)
    exe = compile_light_typed(主, os.path.join(目录, '产物'), optimize_level=0,
                              search_paths=[目录])
    结果 = subprocess.run([exe], cwd=目录, timeout=120, **子进程口径)
    return 结果.returncode, 结果.stdout.replace('\r', '').strip()


# ═══════════════════════════════════════════════════════════════════════════
# A1 · IR 实证（本线的硬判据）
# ═══════════════════════════════════════════════════════════════════════════
def test_A1_多模块异步段必须生成协程状态机():
    ir = _多模块IR()
    # 只统计**调用点/定义**：运行时 declare 恒定存在（declare ptr @dv_coro_create
    # 之类），拿它们计数会把「0 个协程」掩盖成 1~2，是本缺陷最典型的假绿陷阱。
    协程函数 = len(re.findall(r'define void @_coro_', ir))
    创建调用 = len(re.findall(r'call ptr @dv_coro_create', ir))
    等待调用 = len(re.findall(r'call i32 @dv_coro_await\(', ir))
    switch = len(re.findall(r'^\s*switch i32', ir, re.M))
    睡眠调用 = len(re.findall(r'call void @dv_coro_sleep', ir))

    assert 协程函数 >= 2, (
        "多模块程序的异步段没有生成协程函数（define @_coro_* = %d）—— "
        "compile_modules_typed 又漏传 modifiers 了" % 协程函数)
    assert switch >= 2, "协程状态机 switch 缺失（=%d）" % switch
    assert 创建调用 >= 2, "dv_coro_create 调用点 = %d（每个异步段包装函数一处）" % 创建调用
    assert 等待调用 >= 1, "`等待 任务` 没有生成 dv_coro_await 调用点（=%d）" % 等待调用
    assert 睡眠调用 >= 1, "`睡眠` 没有走协程挂起（dv_coro_sleep 调用点 = %d）" % 睡眠调用


@skip_without_clang
def test_A1b_多模块异步程序跑出正确结果(tmp_path):
    """IR 对 + 行为对：跨模块协程句柄能被 `等待` 取到结果。"""
    rc, 输出 = _多模块编译并跑(tmp_path, 'a1b', 主源, 辅助源)
    assert rc == 0, 输出
    assert 输出 == "42", "跨模块协程结果丢失/错位，实际输出=%r" % 输出


# ═══════════════════════════════════════════════════════════════════════════
# A2 · 行为实证：真并发（不是「先跑完一个再跑下一个」）
# ═══════════════════════════════════════════════════════════════════════════
_心跳辅助 = (
    "异步 段落 心跳循环():\n"
    "  设 j 为 0\n"
    "  当 j 小于 2:\n"
    '    打印("心跳")\n'
    "    设 j 为 j 加 1\n"
    "    睡眠(30)\n"
    "\n"
    "异步 段落 领任务循环():\n"
    "  设 i 为 0\n"
    "  当 i 小于 3:\n"
    '    打印("领任务")\n'
    "    设 i 为 i 加 1\n"
    "    睡眠(5)\n"
)

_心跳主 = (
    "从 辅助 导入 心跳循环, 领任务循环\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 心跳 为 创建任务(心跳循环())\n"
    "  等待 领任务循环()\n"
    '  打印("完成")\n'
    "\n"
    "异步 运行 主流程()。\n"
)


@skip_without_clang
def test_A2_心跳协程与主循环真交织(tmp_path):
    """同步语义下心跳会先整段跑完（领任务一条都不出）；协程语义下必须交织。"""
    rc, 输出 = _多模块编译并跑(tmp_path, 'a2', _心跳主, _心跳辅助)
    assert rc == 0, 输出
    行 = 输出.split("\n")
    assert 行.count("领任务") == 3, "领任务循环没有跑满 3 轮，实际输出=%r" % 输出
    assert 行.count("心跳") == 2, "心跳协程没有跑满 2 轮，实际输出=%r" % 输出
    # 交织判据：第一轮心跳必须在「第一轮领任务」之前出现，且第二轮心跳在
    # 「最后一轮领任务」之后出现 —— 说明两个协程真的在时间上重叠。
    assert 行.index("心跳") < 行.index("领任务"), "心跳没有先启动：%r" % 输出
    最后心跳 = len(行) - 1 - 行[::-1].index("心跳")
    assert 最后心跳 > 行.index("领任务"), "两轮心跳都在领任务之前跑完 = 同步语义：%r" % 输出


# ═══════════════════════════════════════════════════════════════════════════
# A3 · `等待` 对非协程值必须透传
# ═══════════════════════════════════════════════════════════════════════════
@skip_without_clang
def test_A3_等待同步段落返回值必须透传(tmp_path):
    """`等待 同步段落()` 必须拿到返回值（不许是 空）。

    L-216 修复前，多模块程序整体按同步编译，`等待` 走「退化情况」直接透传，
    所以 stdlib 里 `等待 己.客户端.请求(...)`（原生腿 请求 是同步段落）才跑得通。
    修好 L-216 后段成了真协程，若 `等待` 仍按协程语义处理普通值，调用方会拿到 空
    —— 实测直接导致原生 worker 对 空 取下标而段错误。
    """
    源 = (
        "段落 取值():\n"
        "  返回 7\n"
        "\n"
        "异步 段落 主流程():\n"
        "  设 v 为 等待 取值()\n"
        "  打印(v)\n"
        "\n"
        "异步 运行 主流程()。\n"
    )
    目录 = os.path.join(str(tmp_path), 'a3')
    os.makedirs(目录, exist_ok=True)
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    主 = _写文件(目录, '主.light', 源)
    exe = compile_light_typed(主, os.path.join(目录, '产物'), optimize_level=0)
    结果 = subprocess.run([exe], cwd=目录, timeout=120, **子进程口径)
    assert 结果.returncode == 0, 结果.stdout + 结果.stderr
    assert 结果.stdout.replace('\r', '').strip() == "7", (
        "`等待 同步段落()` 没透传返回值，实际=%r" % 结果.stdout)


# ═══════════════════════════════════════════════════════════════════════════
# A4 · 嵌套段定义不得被算进外层协程的挂起点
# ═══════════════════════════════════════════════════════════════════════════
@skip_without_clang
def test_A4_嵌套段定义的挂起点不计入外层协程(tmp_path):
    """外层异步段里定义一个含 `睡眠` 的嵌套段 → 旧实现多算 1 个挂起点 → IR 非法。"""
    源 = (
        "异步 段落 外():\n"
        "  段落 内():\n"
        "    睡眠(5)\n"
        "  等待 内()\n"
        '  打印("外完成")\n'
        "\n"
        "异步 运行 外()。\n"
    )
    目录 = os.path.join(str(tmp_path), 'a4')
    os.makedirs(目录, exist_ok=True)
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    主 = _写文件(目录, '主.light', 源)
    # 旧实现这里会抛 RuntimeError（clang: use of undefined value '%resume_...'）
    exe = compile_light_typed(主, os.path.join(目录, '产物'), optimize_level=0)
    结果 = subprocess.run([exe], cwd=目录, timeout=120, **子进程口径)
    assert 结果.returncode == 0, 结果.stdout + 结果.stderr
    assert 结果.stdout.replace('\r', '').strip() == "外完成", 结果.stdout
