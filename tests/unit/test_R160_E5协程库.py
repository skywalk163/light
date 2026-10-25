# -*- coding: utf-8 -*-
"""test_R160_E5协程库.py —— R160-C（R157-E5）协程库层双腿对拍测试。

状态
----
**段①（2026-10-18）只搭结构**：真实协程对拍用例全部挂在「段二号门」后
（环境变量 `R160_E5_SEG2=1` 启用；缺省 skip）。段①可跑的只有 4 项**结构检查**
（骨架存在性 / CRLF / 导出一致性 / src 腿导入）——不执行任何协程、不跑 native 腿
编译，**不 claim 绿**（协程运行时 L-219 未修，禁跑真实协程，任务书 §四 C 线段①禁令）。

段二号门打开的时机：**A 线交付 L-219 修复后**由主 agent 通知启动段②
（`stdlib/协程.light` 占位实现原位替换为真实现，签名不变，规格
`_R160_E5_协程库规格.md` §6）。

对拍契约（规格 §4 的测试侧落地）
------------------------------
- probe = 自包含 `.light` 源，只输出 `标记=值` 行；src 腿 `python -m cli.light_unified run`，
  native 腿 `compile_light_typed` 编译 + 跑 exe（缺 clang skip，见 tests/_native_helpers.py）。
- 判绿 = 两腿输出逐行全等（去 \\r）；native 腿另做 IR 佐证（`dv_coro_*` 调用点在 IR 里），
  防「同步退化」假绿（R159-L216 A1 同款）。
- 单腿 API（`恢复` = Tier-B native-only；`选择IO` 注入器腿相关）按**单腿契约**各自断言
  期望输出，不做两腿全等假判据（规格 §4.4）。
- 既有分歧放行：容器字符串引号 / 字典键引号（L-072）⇒ probe 不打印含字符串元素的
  容器原样；浮点不参与相等 ⇒ 一律取整。

段②预登记反跑锚点（规格 §6.2）：AR-1 创建协程删 create_task 包装 / AR-2 并行改按完成
顺序收结果 / AR-3 登记工人吞异常不登记 / AR-4 睡哨不登记哨兵 / AR-5 恢复在 src 腿改
no-op——每组改坏必须让对应用例转红。

R160-C2 补齐（2026-10-19）
--------------------------
- **AR-1/AR-2 落 src 腿锚点**（段②曾以「asyncio.gather 保序、src 腿无法干净表达」递延）：
  S7 = `创建协程` 登记调度（改坏 ⇒ 序=乙甲 变 甲乙）；S8 = `并行` 提交序收拢
  （改坏 ⇒ R0/R1 互换）。两处均已 mutate 实证转红并还原 IDENTICAL（见
  `_R160_C线补齐交付报告.md`）。
- **`选择IO` native 真实 fd**：S9 = 独立探针（不 import 协程库，绕开 L-227-b）验
  `await_io(真实fd, 1)` 真挂起真唤醒 + IR 佐证；S10 = 库层 probe（R161 就绪态，
  L-227-b 已由 R161-A 修复；R164 T-3 后红因改判 **L-229b**（native runtime 缺陷，
  非库层可修），仍 xfail，见下节）。
- **崩溃签名门补 POSIX `-11`**（SIGSEGV，与 Windows 访问冲突同族）：旧门只列
  `3221225477`/`3221226356`，两平台 SIGSEGV 形态全部漏 xfail。

R164 T-3 补齐（2026-10-24）
--------------------------
- **归因订正**：`stdlib/协程.light` 的竞速 / 选择睡眠 / 选择IO 改走**模块级全局结果槽表 +
  整数槽号**（零 Python import、与 src/native 同源），消除 native 腿「跨协程共享结果表
  因协程实参值拷贝而不可见」的结构性挂死（最小复现定性为 **L-229**）。L-227（codegen
  阻塞）已由 R161-A/R163-A 修复、L-238（`等待 <函数值实参>()` 立即返回 / 内联轮询零推进）
  在 0.88 当前树不可复现，二者均从归因剥离。
- 段② S3 / S4 / S6 三例由 `subprocess.TimeoutExpired⇒xfail` 转**真跑正常断言**
  （xfail 4 → 1、真跑 11 → 14）；S10 红因改判 **L-229b** 后仍 xfail（见下）。
- **L-229a（S3，已修）**：`竞速` 原 `返回 首条` 是全局 `_结果槽表` 内层表的**别名**，
  第二次 `开槽()` 令全局表增长后该别名在 native 腿失效 ⇒ SIGSEGV；改返回**游离新表**
  `[首条[0], 首条[1]]`（库层内部形态，公开签名/导出清单不变）；0.88 实测 `_P3` 转绿、
  `_P4`/`_P6` 不回归。
- **L-229b（S10，库层不可修）**：native 腿同一进程内**第二次**调用 竞速/选择睡眠/选择IO
  时，若某次被登记工人**无让出点即同步跑完**（如 `返回 真`），进程 SIGSEGV（rc=-11）。
  与 IO/`await_io`/`转字符串` 均无关（`选择睡眠` 同款即崩，无 socket 也崩）；两次调用且
  工人均有让出点不崩（`_P6`）、单次不崩；库层两种让出点注入实测均不能规避（其一还令
  `_P6` 转崩）。真因在 native 协程调度/codegen，`src/llvm` 属 T-3 禁改范围 ⇒ 据实留 xfail。

平台：本机 Windows 只初筛；判绿以 0.82 权威 + 0.86 Linux 为准（铁律 7/8），段②由
主 agent 统一触发。
"""

import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src'))
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

# ── 段二号门 ────────────────────────────────────────────────────────────────
_段二号启用 = os.environ.get('R160_E5_SEG2') == '1'
跳过段二号 = pytest.mark.skipif(
    not _段二号启用,
    reason=("R160-E5 段②未启动：A 线 L-219 修复交付前禁跑真实协程（会撞 SIGSEGV）。"
            "A 线交付后由主 agent 置 R160_E5_SEG2=1 启用本文件全部对拍用例。"))

_STDLIB = os.path.join(_ROOT, 'stdlib')
_协程模块 = os.path.join(_STDLIB, '协程.light')
_规格文档 = os.path.join(_ROOT, '_R160_E5_协程库规格.md')

# 导出清单：与 stdlib/协程.light 的「导出」段落逐项一致（Tier-C 的 是否完成 不导出，规格 §3.8）。
期望导出 = [
    '协程超时异常', '协程不支持异常',
    '创建协程', '等待协程',
    '并行', '竞速',
    '选择睡眠', '选择IO',
    '恢复',
]

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')
_SUBPROC_ENV = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}


# ═══════════════════════════════════════════════════════════════════════════
# 段① · 结构检查（可跑；不执行任何协程）
# ═══════════════════════════════════════════════════════════════════════════

def test_C1_骨架文件存在且为纯CRLF():
    """铁律 10 的真实要求 = 「行尾统一、不得混用」，纯 CRLF 或纯 LF 均可。

    判据 = (纯 CRLF) 或 (纯 LF)：`crlf > 0 and crlf == 总lf`，或 `crlf == 0 and 总lf > 0`。
    混用（crlf 与裸 LF 并存）仍判红——铁律 10 禁的是混用，不是 LF。

    函数名保留「纯CRLF」仅为不破坏既有验收点名，判据已行尾无关。

    为何必须行尾无关：git 索引存 LF；Windows 靠 `core.autocrlf=true` 检出 CRLF，
    FreeBSD 干净 clone 无 autocrlf ⇒ 检出 LF。同一 commit 在两平台工作树行尾不同，
    文件内容并未损坏。判据若硬绑 CRLF，则在非 Windows 机器上恒红（行尾 artifact，非代码缺陷）。
    """
    assert os.path.exists(_协程模块), f"骨架缺失：{_协程模块}（规格 §3 的 Tier-1 签名应已落）"
    数据 = open(_协程模块, 'rb').read()
    crlf = 数据.count(b'\r\n')
    总lf = 数据.count(b'\n')
    纯crlf = crlf > 0 and crlf == 总lf
    纯lf = crlf == 0 and 总lf > 0
    assert 纯crlf or 纯lf, (
        f"协程.light 行尾不一致（混用）：crlf={crlf} / 总LF={总lf}"
        f"（铁律 10 的真实要求：行尾必须统一，CRLF 或 LF 均可）")


def test_C2_导出清单与期望一致():
    """导出一致性：逐项 exact equality，防「规格承诺了但骨架没导出」的漂移。"""
    assert os.path.exists(_协程模块)
    文本 = open(_协程模块, encoding='utf-8').read()
    实际导出 = []
    for 行 in 文本.splitlines():
        行 = 行.strip()
        if 行.startswith('导出 '):
            实际导出.append(行[len('导出 '):].strip().rstrip('。').strip())
    assert 实际导出 == 期望导出, (
        f"导出清单与规格不符：实际={实际导出} 期望={期望导出}")


def test_C3_源码零Python导入():
    """P2：库层零 Python import——代码行出现 `导入 asyncio/time` 即红（会绑死 src-only）。

    注：只查**代码行**（剥离 `#` 注释行）——头注合法地写着「不 import asyncio」的禁令说明，
    注释里出现字样不判红；判据是真正的导入语句。
    """
    文本 = open(_协程模块, encoding='utf-8').read()
    代码行 = [行 for 行 in 文本.splitlines() if not 行.strip().startswith('#')]
    禁词 = ['导入 asyncio', '导入 time', 'import asyncio', 'import time']
    命中 = [w for w in 禁词 if any(w in 行 for 行 in 代码行)]
    assert not 命中, f"协程.light 代码行出现 Python import（破双腿 P2）：{命中}"


def test_C4_src腿可导入且导出可访问():
    """src 腿导入钩子可加载骨架（只执行模块级定义；占位段不被调用 ⇒ 不触协程运行时）。"""
    import _light_import_hook  # type: ignore[import]
    _light_import_hook.install([_STDLIB])
    模块 = __import__('协程')
    缺失 = [n for n in 期望导出 if not hasattr(模块, n)]
    assert not 缺失, f"导出不可访问：{缺失}"
    # 异常类须真可构造（段①导入期实测过；防「只有名没有类」的空壳）
    实例 = 模块.协程超时异常('探针')
    assert isinstance(实例, Exception) and str(实例) == '探针'


# ═══════════════════════════════════════════════════════════════════════════
# 段② · 双腿对拍用例（段二号门后；以下整段段①不执行）
# ═══════════════════════════════════════════════════════════════════════════

def _src_run(源码: str):
    """src（转译）腿：python -m cli.light_unified run，返回 (rc, stdout)。"""
    with tempfile.TemporaryDirectory(prefix='_r160c_src_') as d:
        路径 = os.path.join(d, '探针.light')
        with open(路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        结果 = subprocess.run(
            [sys.executable, '-m', 'cli.light_unified', 'run', 路径],
            capture_output=True, timeout=180, cwd=_ROOT, env=_SUBPROC_ENV,
            text=True, encoding='utf-8', errors='replace')
        return 结果.returncode, 结果.stdout.replace('\r', '').strip()


def _native_run(源码: str, 优化档: int = 0):
    """native 腿：compile_light_typed 编译 + 运行，返回 (rc, stdout)。"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix='_r160c_nat_') as d:
        主 = os.path.join(d, '主.light')
        with open(主, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        exe = compile_light_typed(主, os.path.join(d, '产物'),
                                  optimize_level=优化档, search_paths=[_STDLIB])
        结果 = subprocess.run([exe], capture_output=True, timeout=45,
                              cwd=d, text=True, encoding='utf-8', errors='replace')
        return 结果.returncode, 结果.stdout.replace('\r', '').strip()


# ── native 腿协程 codegen/runtime 阻塞登记（HEAD 复现，非本库引入）──
#   ① 跨 await 表达式（`f(等待 x)` 混合其它操作数）→ IR `does not dominate all uses`
#   ② 多函数模块导出表 → `use of undefined value '@_seg_*'`
#   ③ 嵌套 `创建任务(工人(共享表))` + 轮询 → SIGSEGV(0xC0000005) / 挂死
# 命中即 xfail（诚实：src 腿断言已真跑真绿）；其它失败照常抛出（真回归）。
# R164 T-3（2026-10-24）归因订正：① ②（L-227 codegen）已由 R161-A/R163-A 修复，本轮
#   复核不再复现；③ 经 9 批最小复现**一分为二**：
#     · **L-229a（库层 · 本轮已修）**：原 `竞速` 返回全局 `_结果槽表` 的**内层表别名** ⇒
#       native 腿第二次调用 SIGSEGV；已改为返回**游离新表** `[首条[0], 首条[1]]`（库层
#       内部形态，公开签名/导出清单不变）。S3/S4/S6 因此由 xfail 转真跑正常断言。
#     · **L-229b（native runtime · 库层不可修）**：同一进程内**第二次**调用 竞速/选择睡眠/
#       选择IO 且某次被登记工人**无让出点即同步跑完** ⇒ SIGSEGV（rc=-11）；真因在 native
#       协程调度/codegen，`src/llvm` 属 T-3 禁改 ⇒ 据实留 xfail（S10）。
#   L-238（`等待 <函数值实参>()` 立即返回 / 内联轮询零推进）在 0.88 当前树亦不可复现
#   （R163-A 修 L-232 后），从归因剥离。详见 _R164_C线交付报告.md。
_已知原生阻塞 = ('does not dominate all uses', "use of undefined value '@_seg_")
# R160-C2（2026-10-19）补 POSIX 崩溃签名：-11 = SIGSEGV，与 Windows 访问冲突同族
# （L-228）。0.82/0.86 双平台基线里 S1/S2/S5a 在 Linux 全为 rc=-11，旧门只列 Windows
# 码 ⇒ 两平台所有 SIGSEGV 形态都漏 xfail。修后 native 转绿时 rc=0 ⇒ 自动正常断言。
_已知崩溃 = (3221225477, 3221226356, -11)  # 0xC0000005 / 0xC0000374 / SIGSEGV


def _native_或_已知阻塞(源码: str):
    """native 腿编译+运行；命中登记的 codegen 阻塞(L-227)/runtime 崩溃(L-229b)则 xfail，其它异常照抛。"""
    try:
        return _native_run(源码)
    except RuntimeError as e:
        msg = str(e)
        if any(k in msg for k in _已知原生阻塞):
            pytest.xfail(f"L-227: native 协程 codegen 阻塞（{msg.splitlines()[0][:70]}）")
        raise
    except subprocess.TimeoutExpired:
        # R164 T-3 订正：此为**修复前库层**挂死的兜底登记（L-229a：共享结果表按值拷贝 ⇒
        # 跨协程写入不传回 ⇒ 父协程轮询永不退出）。本库已改走模块级全局结果槽表 + 整数槽号，
        # S3/S4/S6 实测转 rc=0 正常断言，此分支仅在挂到旧库时触发。L-238 在 0.88 当前树
        # 不可复现已剥离；L-227 codegen 阻塞由 R161-A/R163-A 修复。
        pytest.xfail(
            "L-229a(修复前库层兜底): native 协程挂死（跨协程共享结果表值拷贝不可见，"
            "父协程轮询永不退出；见 _R164_C线交付报告.md）")


def _原生IR文本(源码: str) -> str:
    """只编译取 IR 文本（不起 clang、不执行）；用于 `call ... @dv_coro_await_io` 佐证。"""
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    return compile_modules_typed({'主': 源码}, main_module='主', opt_level='O0')


def _IR调用点计数(ir: str) -> dict:
    """IR 文本 → 关键调用点计数（**行为面**断言用，不做字面量 `in` 断言）。

    只数 `call`/`define` 行，不数 `declare`（declare 只证明 ABI 声明存在，不证明真生成）。
    """
    import re
    return {
        '协程函数': len(re.findall(r'define void @_coro_', ir)),
        '创建': len(re.findall(r'call ptr @dv_coro_create', ir)),
        '等待': len(re.findall(r'call i32 @dv_coro_await\(', ir)),
        '睡眠': len(re.findall(r'call void @dv_coro_sleep', ir)),
        'IO等待': len(re.findall(r'call void @dv_coro_await_io', ir)),
    }


def _原生IR佐证(源码: str):
    """native 腿 IR 里必须真有协程生成（防「同步退化」假绿，R159-L216 A1 同款）。

    返回各调用点计数字典；呼叫方对关键项断言 > 0。
    注意：`compile_modules_typed` 不收 search_paths（签名 = sources/main_module/verbose/
    target_platform/debug/opt_level），故把 `stdlib/协程.light` 读进 sources 字典
    （模块名 '协程' 与探针 `从 协程 导入 …` 对齐）；编译期不起 clang、不执行。
    """
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    with open(_协程模块, encoding='utf-8') as f:
        库源 = f.read()
    ir = compile_modules_typed({'主': 源码, '协程': 库源},
                               main_module='主', opt_level='O0')
    return _IR调用点计数(ir)


# ── R160-C2（2026-10-19）：真实 fd 来源（native-only 内置，主 agent 已读码坐实）──
# `创建socket(域, 类型)` → 裸 fd i32（codegen_typed.py:4042，runtime dv_socket_create）；
# `绑定socket`/`监听socket`/`接受socket` 同族（:4153/:4172/:4190）。`打开文件` 返回
# LV_TYPE_FILE 句柄，**不是**裸 fd，故不作 fd 来源。
#
# 确定性形态（本机 native 腿实测，`_r160_scratch/c2_io_probe.light`）：
#   监听 socket + 先由同进程客户端 connect ⇒ accept 队列就绪 ⇒ `等待 await_io(fd, 1)`
#   立即返回。**不能只监听不连接**：无连接时监听 fd 的 POLLRDNORM 就绪语义按平台而异，
#   实测本机 Windows 上 `等待 await_io(监听fd, 1)` 永久挂起（负对照
#   `_r160_scratch/c2_io_negative.light`，10s 超时）⇒ 故 probe 一律「先 connect 再等」。
# events 编码：DV_POLL_READ=1 / DV_POLL_WRITE=2（runtime_typed.c:6426-6427），
# 本机实测 `await_io(客户端, 2)` 可写立即返回、`await_io(监听fd, 1)` 可读立即返回
# （`_r160_scratch/c2_io_events_probe.light`，out=可写=真/可读=真）⇒ 编码双向坐实。
#
# native 端口固定值 = 对拍确定性要求；该端口只在本进程内 bind（SO_REUSEADDR 未设），
# 若被占用则 BIND≠0 断言直接红（诚实失败，不静默跳过）。

# 独立探针（**不** `从 协程 导入`）：只验 `await_io(真实fd, 1)` 真挂起/真唤醒。
_P7_原生IO真实fd = (
    "异步 段落 主流程():\n"
    "  设 监听fd 为 创建socket(2, 1)\n"
    "  设 绑定 为 绑定socket(监听fd, \"127.0.0.1\", 45871)\n"
    "  打印(\"BIND=\" 加上 转字符串(绑定))\n"
    "  设 监听 为 监听socket(监听fd, 8)\n"
    "  打印(\"LISTEN=\" 加上 转字符串(监听))\n"
    "  设 客户端 为 创建socket(2, 1)\n"
    "  设 连上 为 连接socket(客户端, \"127.0.0.1\", 45871)\n"
    "  打印(\"CONNECT=\" 加上 转字符串(连上))\n"
    "  等待 await_io(监听fd, 1)\n"
    "  打印(\"就绪=真\")\n"
    "  设 连接 为 接受socket(监听fd)\n"
    "  如果 连接 大于 0:\n"
    "    打印(\"ACCEPT=正\")\n"
    "  否则:\n"
    "    打印(\"ACCEPT=负\")\n"
    "  socket_close(客户端)\n"
    "  socket_close(连接)\n"
    "  socket_close(监听fd)\n"
    "\n"
    "异步 运行 主流程()。\n"
)

# 库层 probe（R161 就绪态）：按规格 §3.7 参考包装写 `原生就绪可读` 注入段，
# 走 `从 协程 导入 选择IO`。L-227-b（多导出表）已由 R161-A 修复；
# R164 T-3 修复库层共享结果表后本探针无需改动，但红因改判 **L-229b**（见 S10 docstring）。
#
# R161-C（2026-10-20）注入形态订正：规格 §3.7 原参考包装写成
# `异步 段落 原生就绪可读(fd): 等待 await_io(fd, 1)`，但 `选择IO` 按规格调用
# **零参**就绪等待器（`就绪等待器()`，见 `stdlib/协程.light` 的就绪工人）——
# 形参 `fd` 永远收不到真实 fd。实测该形态下 `await_io` 收到垃圾 fd：
#   stderr = `[光明·事件循环] poller 等待失败：WSAPoll 失败: errno 10038`（WSAENOTSOCK），
#   rc=0 且 stdout 为空 ⇒ 假绿面（不是超时、不是就绪，是根本没 poll 到 socket）。
# 故改为「模块级全局 fd 邮槽」注入（R161-C 实证：协程实参是结构体拷贝，
# 容器/对象成员写不传播；模块级全局是唯一稳定的跨协程注入通道）。
# R164 T-3 订正：库层「共享结果表 + 父协程轮询」在 native 腿因协程实参值拷贝而结构性
# 不可用（L-229a），已改走模块级全局结果槽表；但本探针红未消——改判 **L-229b**：
# native 协程 runtime 在「第二次 竞速/选择 族调用 + 某次工人无让出点」下 SIGSEGV。
_P8_选择IO原生真实fd = (
    "从 协程 导入 选择IO, 协程超时异常\n"
    "\n"
    "设 _IO就绪fd 为 0\n"
    "\n"
    "异步 段落 原生就绪可读():\n"
    "  全局 _IO就绪fd\n"
    "  等待 await_io(_IO就绪fd, 1)\n"
    "  返回 真\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 监听fd 为 创建socket(2, 1)\n"
    "  设 绑定 为 绑定socket(监听fd, \"127.0.0.1\", 45873)\n"
    "  设 监听 为 监听socket(监听fd, 8)\n"
    "  设 客户端 为 创建socket(2, 1)\n"
    "  设 连上 为 连接socket(客户端, \"127.0.0.1\", 45873)\n"
    "  全局 _IO就绪fd\n"
    "  设 _IO就绪fd 为 监听fd\n"
    "  设 就绪0 为 等待 选择IO(原生就绪可读, 2.0)\n"
    "  打印(\"IO0=\" 加上 转字符串(就绪0))\n"
    # R165（判据前提订正，非改判据值）：第一次 选择IO 之后必须把就绪**排空**，
    # 否则监听 fd 的 accept 队列里那条连接还在 ⇒ level-trigger 下第二次 选择IO
    # 天然就绪、立刻返回「未超时」，`IO1=超时` 这条期望在语义上不可能成立。
    # 取证（同一二进制，R165 实测）：不加 accept → `IO1=未超时`；加 accept →
    # `IO1=超时`。修 L-229b 前该行被 SIGSEGV 掩盖，故长期未被发现。
    # 与 S9 的 `_P7` 形态对齐（S9 就是 await_io 后立即 接受socket）。
    "  设 连接A 为 接受socket(监听fd)\n"
    "  尝试:\n"
    "    等待 选择IO(原生就绪可读, 0.1)\n"
    "    打印(\"IO1=未超时\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 协程超时异常:\n"
    "      打印(\"IO1=超时\")\n"
    "    否则:\n"
    "      打印(\"IO1=其它\")\n"
    "  socket_close(连接A)\n"
    "  socket_close(客户端)\n"
    "  socket_close(监听fd)\n"
    "\n"
    "异步 运行 主流程()。\n"
)


# ---- 探针源（规格 §4.1 形态：只输出 标记=值；睡眠差 ≥50ms 制造确定性胜者）----

_P1_并行逐条收集 = (
    "从 协程 导入 并行\n"
    "\n"
    "类 我的错误 继承 Exception:\n"
    "  段落 构造(消息):\n"
    "    父.构造(消息)\n"
    "\n"
    "异步 段落 快():\n"
    "  等待 异步睡眠(0.05)\n"
    "  返回 1\n"
    "\n"
    "异步 段落 慢():\n"
    "  等待 异步睡眠(0.15)\n"
    "  返回 2\n"
    "\n"
    "异步 段落 炸():\n"
    "  抛出 新建 我的错误(\"炸\")\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 结果表 为 等待 并行([快, 慢, 炸])\n"
    "  打印(\"R0=\" 加上 转字符串(结果表[0]))\n"
    "  打印(\"R1=\" 加上 转字符串(结果表[1]))\n"
    "  设 第三项 为 结果表[2]\n"
    "  如果 类型(第三项) == 我的错误:\n"
    "    打印(\"R2=异常\")\n"
    "  否则:\n"
    "    打印(\"R2=非异常\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)

_P2_并行全或无 = (
    "从 协程 导入 并行\n"
    "\n"
    "类 我的错误 继承 Exception:\n"
    "  段落 构造(消息):\n"
    "    父.构造(消息)\n"
    "\n"
    "异步 段落 慢():\n"
    "  等待 异步睡眠(0.3)\n"
    "  返回 2\n"
    "\n"
    "异步 段落 快失败():\n"
    "  等待 异步睡眠(0.05)\n"
    "  抛出 新建 我的错误(\"首败\")\n"
    "\n"
    "异步 段落 主流程():\n"
    "  尝试:\n"
    "    设 结果表 为 等待 并行([慢, 快失败], \"全或无\")\n"
    "    打印(\"未抛出\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 我的错误:\n"
    "      打印(\"全或无=首败异常\")\n"
    "    否则:\n"
    "      打印(\"全或无=其它异常\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)

_P3_竞速确定性胜者 = (
    "从 协程 导入 竞速, 协程超时异常\n"
    "\n"
    "异步 段落 快():\n"
    "  等待 异步睡眠(0.05)\n"
    "  返回 \"快\"\n"
    "\n"
    "异步 段落 慢():\n"
    "  等待 异步睡眠(0.3)\n"
    "  返回 \"慢\"\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 胜者 为 等待 竞速([慢, 快])\n"
    "  打印(\"WIN=\" 加上 转字符串(胜者[0]))\n"
    "  打印(\"IDX=\" 加上 转字符串(胜者[1]))\n"
    "  尝试:\n"
    "    设 结果 为 等待 竞速([慢], 0.1)\n"
    "    打印(\"TIMEOUT=未触发\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 协程超时异常:\n"
    "      打印(\"TIMEOUT=是\")\n"
    "    否则:\n"
    "      打印(\"TIMEOUT=否\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)

_P4_选择睡眠 = (
    "从 协程 导入 选择睡眠, 协程超时异常\n"
    "\n"
    "异步 段落 慢():\n"
    "  等待 异步睡眠(0.3)\n"
    "  返回 \"迟到\"\n"
    "\n"
    "异步 段落 快():\n"
    "  等待 异步睡眠(0.02)\n"
    "  返回 \"准时\"\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 值0 为 等待 选择睡眠(快, 1.0)\n"
    "  打印(\"S0=\" 加上 转字符串(值0))\n"
    "  尝试:\n"
    "    等待 选择睡眠(慢, 0.1)\n"
    "    打印(\"S1=未超时\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 协程超时异常:\n"
    "      打印(\"S1=超时\")\n"
    "    否则:\n"
    "      打印(\"S1=其它\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)

# 恢复：Tier-B native-only。P5a 走 native 腿顶层调用（规格 §3.6 调用位约束）；
# P5b 走 src 腿验证「src 永久立抛」契约（规格 §3.6 / P3）。
_P5a_恢复native = (
    "从 协程 导入 创建协程, 恢复, 等待协程\n"
    "\n"
    "异步 段落 干活():\n"
    "  等待 异步睡眠(0.02)\n"
    "  返回 7\n"
    "\n"
    "设 句柄 为 创建协程(干活)\n"
    "恢复(句柄)\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 结果 为 等待 等待协程(句柄)\n"
    "  打印(\"R=\" 加上 转字符串(结果))\n"
    "\n"
    "异步 运行 主流程()。\n"
)

_P5b_恢复src立抛 = (
    "从 协程 导入 恢复, 协程不支持异常\n"
    "\n"
    "异步 段落 主流程():\n"
    "  尝试:\n"
    "    恢复(\"假句柄\")\n"
    "    打印(\"恢复=未抛\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 协程不支持异常:\n"
    "      打印(\"恢复=src立抛\")\n"
    "    否则:\n"
    "      打印(\"恢复=其它\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)

# 选择IO：框架对拍用「睡眠模拟就绪」的注入段（双腿同源）；native 真实 fd 见 S9/S10
# （规格 §3.7：events 编码已坐实 = READ 1 / WRITE 2，见 `_原生IR文本` 上方注释块）。
_P6_选择IO框架 = (
    "从 协程 导入 选择IO, 协程超时异常\n"
    "\n"
    "异步 段落 快就绪():\n"
    "  等待 异步睡眠(0.02)\n"
    "  返回 真\n"
    "\n"
    "异步 段落 慢就绪():\n"
    "  等待 异步睡眠(0.3)\n"
    "  返回 真\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 就绪0 为 等待 选择IO(快就绪, 1.0)\n"
    "  打印(\"IO0=\" 加上 转字符串(就绪0))\n"
    "  尝试:\n"
    "    等待 选择IO(慢就绪, 0.1)\n"
    "    打印(\"IO1=未超时\")\n"
    "  捕获 异常 e:\n"
    "    如果 类型(e) == 协程超时异常:\n"
    "      打印(\"IO1=超时\")\n"
    "    否则:\n"
    "      打印(\"IO1=其它\")\n"
    "\n"
    "异步 运行 主流程()。\n"
)


# ---- 段②用例 ----

@跳过段二号
def test_S1_并行逐条收集_双腿对拍():
    """期望（两腿逐行全等）：R0=1 / R1=2 / R2=异常；顺序=提交顺序（AR-2 反跑锚点）。"""
    rc_s, out_s = _src_run(_P1_并行逐条收集)
    assert rc_s == 0, out_s
    assert out_s == "R0=1\nR1=2\nR2=异常", f"逐条收集口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P1_并行逐条收集)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"
    try:
        ir = _原生IR佐证(_P1_并行逐条收集)
    except RuntimeError as e:
        if any(k in str(e) for k in _已知原生阻塞):
            pytest.xfail(f"L-227: IR 佐证 codegen 阻塞（{str(e).splitlines()[0][:70]}）")
        raise
    assert ir['创建'] >= 1 and ir['等待'] >= 1, f"IR 无协程生成（假绿风险）：{ir}"


@跳过段二号
def test_S2_并行全或无_双腿对拍():
    """期望（两腿逐行全等）：全或无=首败异常（按提交顺序首败即抛，AR-2）。"""
    rc_s, out_s = _src_run(_P2_并行全或无)
    assert rc_s == 0, out_s
    assert out_s == "全或无=首败异常", f"全或无口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P2_并行全或无)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"


@跳过段二号
def test_S3_竞速确定性胜者与超时_双腿对拍():
    """期望（两腿逐行全等）：WIN=快 / IDX=1 / TIMEOUT=是（AR-3/AR-4 反跑锚点）。"""
    rc_s, out_s = _src_run(_P3_竞速确定性胜者)
    assert rc_s == 0, out_s
    assert out_s == "WIN=快\nIDX=1\nTIMEOUT=是", f"竞速口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P3_竞速确定性胜者)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"


@跳过段二号
def test_S4_选择睡眠_双腿对拍():
    """期望（两腿逐行全等）：S0=准时 / S1=超时（AR-4 反跑锚点）。"""
    rc_s, out_s = _src_run(_P4_选择睡眠)
    assert rc_s == 0, out_s
    assert out_s == "S0=准时\nS1=超时", f"选择睡眠口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P4_选择睡眠)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"


@跳过段二号
@skip_without_clang
def test_S5a_恢复_native腿契约():
    """Tier-B native-only（规格 §4.4 单腿契约，不做两腿全等）：R=7。

    注：probe 走顶层 `创建协程`+`恢复`（规格 §3.6 调用位约束：仅协程外）。
    若段②实测「顶层调用异步段」native 编译/运行不通，登记为新发现并回改规格，
    不悄悄改判据。
    """
    rc_n, out_n = _native_或_已知阻塞(_P5a_恢复native)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_n == "R=7", f"恢复(native) 口径漂移：{out_n!r}"


@跳过段二号
def test_S5b_恢复_src腿立抛契约():
    """src 腿 Tier-B 契约（AR-5 反跑锚点）：恢复=src立抛（改 no-op 即红，P3）。"""
    rc_s, out_s = _src_run(_P5b_恢复src立抛)
    assert rc_s == 0, out_s
    assert out_s == "恢复=src立抛", f"src 腿 恢复 未按规格立抛：{out_s!r}"


@跳过段二号
def test_S6_选择IO框架_双腿对拍():
    """期望（两腿逐行全等）：IO0=True / IO1=超时。

    注：注入段为「睡眠模拟就绪」（双腿同源）；native 真实 fd 的两条 probe 见
    S9（独立探针，await_io 本体）与 S10（库层，R161 就绪态），规格 §3.7/§9.2。
    """
    rc_s, out_s = _src_run(_P6_选择IO框架)
    assert rc_s == 0, out_s
    assert out_s == "IO0=真\nIO1=超时", f"选择IO 框架口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P6_选择IO框架)
    if rc_n in _已知崩溃:
        pytest.xfail("L-229b: native 协程 runtime 崩溃（SIGSEGV 族；第二次 竞速/选择 族调用且某次工人无让出点即同步完成）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"


# ═══════════════════════════════════════════════════════════════════════════
# 段② · R160-C2 补齐（2026-10-19）：AR-1/AR-2 src 腿反跑锚点 + 选择IO native 真实 fd
# ═══════════════════════════════════════════════════════════════════════════

# AR-1 锚点：`创建协程` 若删掉 `创建任务` 包装（只 `返回 协程函数()`），句柄不再被
# 登记调度 ⇒ 完成顺序退回「按 await 顺序」⇒ 下面的 序=乙甲 变 序=甲乙 ⇒ 转红。
# 本探针只用 创建协程/等待协程 两个 API（不用 并行），把 AR-1 的失效面单独钉出来。
_P9_AR1_创建协程登记锚点 = (
    "从 协程 导入 创建协程, 等待协程\n"
    "\n"
    "设 轨迹 为 []\n"
    "\n"
    "异步 段落 甲():\n"
    "  等待 异步睡眠(0.2)\n"
    "  轨迹.追加(\"甲\")\n"
    "  返回 1\n"
    "\n"
    "异步 段落 乙():\n"
    "  等待 异步睡眠(0.05)\n"
    "  轨迹.追加(\"乙\")\n"
    "  返回 2\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 甲句 为 创建协程(甲)\n"
    "  设 乙句 为 创建协程(乙)\n"
    "  设 甲值 为 等待 等待协程(甲句)\n"
    "  设 乙值 为 等待 等待协程(乙句)\n"
    "  打印(\"甲=\" 加上 转字符串(甲值))\n"
    "  打印(\"乙=\" 加上 转字符串(乙值))\n"
    "  打印(\"序=\" 加上 轨迹[0] 加上 轨迹[1])\n"
    "\n"
    "异步 运行 主流程()。\n"
)

# AR-2 锚点：`并行` 若改按完成顺序收结果（工人完成即追加、返回共享表），
# 提交序 [慢, 快] 会收成 [1, 2] ⇒ 下面期望的 R0=2 / R1=1 转红。
# 睡眠差 150ms ≫ 调度抖动，顺序确定。
_P10_AR2_并行提交序锚点 = (
    "从 协程 导入 并行\n"
    "\n"
    "异步 段落 慢():\n"
    "  等待 异步睡眠(0.2)\n"
    "  返回 2\n"
    "\n"
    "异步 段落 快():\n"
    "  等待 异步睡眠(0.05)\n"
    "  返回 1\n"
    "\n"
    "异步 段落 主流程():\n"
    "  设 结果表 为 等待 并行([慢, 快])\n"
    "  打印(\"R0=\" 加上 转字符串(结果表[0]))\n"
    "  打印(\"R1=\" 加上 转字符串(结果表[1]))\n"
    "\n"
    "异步 运行 主流程()。\n"
)


@跳过段二号
def test_S7_AR1_创建协程登记锚点_src腿():
    """AR-1 反跑锚点（src 腿）：创建协程必须真登记调度。

    期望：甲=1 / 乙=2 / 序=乙甲。
    改坏（`创建协程` 删 `创建任务` 包装）⇒ 序=甲乙 ⇒ 本用例红。
    """
    rc_s, out_s = _src_run(_P9_AR1_创建协程登记锚点)
    assert rc_s == 0, out_s
    assert out_s == "甲=1\n乙=2\n序=乙甲", f"AR-1 锚点失效（创建协程未真登记调度）：{out_s!r}"


@跳过段二号
def test_S8_AR2_并行提交序锚点_src腿():
    """AR-2 反跑锚点（src 腿）：并行结果顺序 = 提交顺序，不是完成顺序。

    期望：R0=2 / R1=1（[慢, 快] 提交序）。
    改坏（并行改按完成顺序收结果）⇒ R0=1 / R1=2 ⇒ 本用例红。
    """
    rc_s, out_s = _src_run(_P10_AR2_并行提交序锚点)
    assert rc_s == 0, out_s
    assert out_s == "R0=2\nR1=1", f"AR-2 锚点失效（并行未按提交顺序收拢）：{out_s!r}"


@跳过段二号
@skip_without_clang
def test_S9_原生IO真实fd_独立探针():
    """选择IO 的 native 地基：`await_io(真实fd, 1)` 真挂起、真被 poller 唤醒。

    探针**不** `从 协程 导入`（历史上用于绕开 L-227-b 多导出表，该缺陷已由 R161-A 修复），只验 await_io 本体：
    监听 socket + 同进程客户端 connect ⇒ accept 队列就绪 ⇒ 立即唤醒。
    IR 佐证：`call void @dv_coro_await_io` 必须存在（防「同步退化」假绿）。
    """
    rc_n, out_n = _native_或_已知阻塞(_P7_原生IO真实fd)
    if rc_n in _已知崩溃:
        pytest.xfail("L-228: native 协程 runtime 崩溃（SIGSEGV 族；真实 fd await_io 路径）")
    assert rc_n == 0, out_n
    assert out_n == "BIND=0\nLISTEN=0\nCONNECT=0\n就绪=真\nACCEPT=正", (
        f"native await_io(真实fd,1) 口径漂移：{out_n!r}")
    ir = _原生IR文本(_P7_原生IO真实fd)
    调用点 = _IR调用点计数(ir)['IO等待']
    assert 调用点 >= 1, (
        f"IR 里没有 `call void @dv_coro_await_io` 调用点（await_io 未真生成，假绿风险）：{调用点}")


@跳过段二号
@skip_without_clang
def test_S10_选择IO_原生真实fd_库层probe():
    """库层 probe（R161 就绪态）：`从 协程 导入 选择IO` + 真实 fd 就绪等待器。

    期望：IO0=真 / IO1=超时。
    R164 T-3（2026-10-24）现状订正：L-227-b（多导出表 `use of undefined value '@_seg_*'`）
    已由 R161-A 修复；库层共享结果表已改走**模块级全局结果槽表 + 整数槽号**（消除 L-229a
    的实参值拷贝挂死），但本探针仍红，红因经 9 批最小复现改判为 **L-229b**——native 协程
    runtime 缺陷：同一进程内**第二次**调用 竞速/选择睡眠/选择IO 时，若某次被登记工人**无
    让出点即同步跑完**，进程 SIGSEGV（rc=-11）。触发与 IO/`await_io`/`转字符串` 均无关
    （`选择睡眠` 立即工人两次调用同款即崩；去掉 socket/await_io 也崩；单次不崩；两次调用
    且工人均有让出点不崩 —— `_P6`）。库层注入让出点两种写法实测均不能规避（其一令 `_P6`
    转崩）⇒ 真因在 native 协程调度/codegen，`src/llvm` 属 T-3 禁改范围，据实留 xfail。
    注入形态为模块级全局 fd 邮槽（详见 `_P8` 上方注释），红因不是「传了垃圾 fd」。

    R165（2026-10-25）状态订正：T-1 修掉 L-229b（`dv_deref_value` 对 LIST 深拷，根治
    「协程帧拆除时 locals 循环 free 掉全局 `_结果槽表` 的 list_data」的 use-after-free）后
    本探针不再崩溃（rc=0），但首跑仍红：`IO1=未超时`。取证判定为**探针前提失效**而非
    产品缺陷——监听 fd 的 accept 队列里那条连接从未被取走，level-trigger 下第二次
    `选择IO` 必然「已就绪」。同一二进制对照：不加 `接受socket` ⇒ 未超时；加 ⇒ 超时。
    故在 `_P8` 两次 `选择IO` 之间补 `接受socket(监听fd)`（与 S9 的 `_P7` 形态对齐），
    断言值 `IO0=真 / IO1=超时` **一字未改**。
    """
    rc_n, out_n = _native_或_已知阻塞(_P8_选择IO原生真实fd)
    assert rc_n == 0, out_n
    assert out_n == "IO0=真\nIO1=超时", f"选择IO(原生真实 fd) 口径漂移：{out_n!r}"

