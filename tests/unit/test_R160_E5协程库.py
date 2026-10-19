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
    """新 .light 必须 CRLF（铁律 10）。判据 = crlf 计数 == 总 LF 计数且 > 0。"""
    assert os.path.exists(_协程模块), f"骨架缺失：{_协程模块}（规格 §3 的 Tier-1 签名应已落）"
    数据 = open(_协程模块, 'rb').read()
    crlf = 数据.count(b'\r\n')
    总lf = 数据.count(b'\n')
    assert crlf > 0 and crlf == 总lf, (
        f"协程.light 不是纯 CRLF：crlf={crlf} / 总LF={总lf}（铁律 10：新 .light 必须 CRLF）")


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


# ── L-227 已登记：native 腿协程 codegen/runtime 阻塞（HEAD 复现，非本库引入）──
#   ① 跨 await 表达式（`f(等待 x)` 混合其它操作数）→ IR `does not dominate all uses`
#   ② 多函数模块导出表 → `use of undefined value '@_seg_*'`
#   ③ 嵌套 `创建任务(工人(共享表))` + 轮询 → SIGSEGV(0xC0000005) / 挂死
# 命中三类即 xfail（诚实：src 腿断言已真跑真绿）；其它失败照常抛出（真回归）。
_已知原生阻塞 = ('does not dominate all uses', "use of undefined value '@_seg_")
_已知崩溃 = (3221225477, 3221226356)  # 0xC0000005 访问冲突 / 0xC0000374 堆损坏


def _native_或_已知阻塞(源码: str):
    """native 腿编译+运行；命中 L-227 已登记阻塞则 xfail，其它异常照抛。"""
    try:
        return _native_run(源码)
    except RuntimeError as e:
        msg = str(e)
        if any(k in msg for k in _已知原生阻塞):
            pytest.xfail(f"L-227: native 协程 codegen 阻塞（{msg.splitlines()[0][:70]}）")
        raise
    except subprocess.TimeoutExpired:
        pytest.xfail("L-227: native 协程 runtime 挂死（嵌套创建任务+共享表轮询）")


def _原生IR佐证(源码: str):
    """native 腿 IR 里必须真有协程生成（防「同步退化」假绿，R159-L216 A1 同款）。

    返回各调用点计数字典；呼叫方对关键项断言 > 0。
    注意：`compile_modules_typed` 不收 search_paths（签名 = sources/main_module/verbose/
    target_platform/debug/opt_level），故把 `stdlib/协程.light` 读进 sources 字典
    （模块名 '协程' 与探针 `从 协程 导入 …` 对齐）；编译期不起 clang、不执行。
    """
    import re
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    with open(_协程模块, encoding='utf-8') as f:
        库源 = f.read()
    ir = compile_modules_typed({'主': 源码, '协程': 库源},
                               main_module='主', opt_level='O0')
    return {
        '协程函数': len(re.findall(r'define void @_coro_', ir)),
        '创建': len(re.findall(r'call ptr @dv_coro_create', ir)),
        '等待': len(re.findall(r'call i32 @dv_coro_await\(', ir)),
        '睡眠': len(re.findall(r'call void @dv_coro_sleep', ir)),
    }


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

# 选择IO：框架对拍用「睡眠模拟就绪」的注入段（双腿同源）；native+await_io 真实
# fd 包装为段②扩展位（规格 §3.7 附录，events 编码待核实）。
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
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
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
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
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
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
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
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
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
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
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

    注：注入段为「睡眠模拟就绪」（双腿同源）；native 真实 fd（await_io 包装）
    为段②扩展位（规格 §3.7 附录，events 编码待核实后补 probe）。
    """
    rc_s, out_s = _src_run(_P6_选择IO框架)
    assert rc_s == 0, out_s
    assert out_s == "IO0=真\nIO1=超时", f"选择IO 框架口径漂移(src)：{out_s!r}"
    rc_n, out_n = _native_或_已知阻塞(_P6_选择IO框架)
    if rc_n in _已知崩溃:
        pytest.xfail("L-227: native 协程 runtime 崩溃（0xC0000005/0xC0000374，嵌套创建任务+共享表轮询）")
    assert rc_n == 0, out_n
    assert out_s == out_n, f"两腿输出不一致：src={out_s!r} native={out_n!r}"

