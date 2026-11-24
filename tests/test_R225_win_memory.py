# -*- coding: utf-8 -*-
"""R225 / T-0445：Windows 上「内存错误 / 栈溢出」把下游判据打成假红的归因与修复。

## 现象（lightharness T-0442 验收期，2026-11-23，Windows 主机实测）

同一份代码、同一台 Windows、同一版光明：

- `tests/unit/test_工具执行.py` 里 2 条用例报「内存错误」（光明对 MemoryError 的中文名）；
- `examples/test_R42_真实工具链.light` 报栈溢出；
- 换 192.168.0.88（FreeBSD 15.1 / python3.12）同一份快照同文件全绿；
- 隔一天同机复跑，又全绿 —— 因此被当作「偶发 / 宿主资源」搁置。

## 归因（本轮钉死的部分：栈溢出是**光明侧确定性缺陷**，与宿主无关）

`PythonCodeGenerator._generate_expr` 对 BinaryOp 是**按 AST 形状逐层递归**的，
而 parser 把 `1 + 2 + 3` 解析成左结合链 `BinaryOp(BinaryOp(1, 2), 3)`：

1. 每层 1 个 `_generate_expr` 帧 → N 项链在 N≈1000 撞 `sys.getrecursionlimit()`
   （默认 1000）→ `RecursionError`；而在更小的 N 上，旧实现会先被「层层括号」放大：
   实测 n=200 通过、n=220 起产物已多到 CPython 解析器报
   `too many nested parentheses` → 变 SyntaxError（本文件「修复前实测」：
   `错误: 语法解析错误`）。**两头都红，且与操作系统无关**。
2. 于是「能解析、语义完全正确」的光明源码在编译期直接失败，下游判据拿到 rc≠0
   就打成红 —— 这就是假红的机制。同一段源码在 FreeBSD 上同样会红（Python 版本
   只有递归上限细节差异），所以「Linux/FreeBSD 全绿」并不能证明代码没问题，
   只说明那次没踩到阈值。

修复（`src/code_generator.py`，R225）：左撇运算链拆成
「首操作数 + [(运算符, 右子树)…]」后用循环 + 优先级折叠成一维文本，只对右子树
递归（右子树是叶子或小题，深度与链长无关）；`写 "a" + …` 的合并路径
（`_gen_write_merged`）同口径改造。语义与旧实现逐字对齐（右子树仍由同一个
`_generate_expr` 生成，只去掉同优先级左结合的多余括号），见 test_语义不变_*。

## 判据与反证

- 修复前：1200 项链在子进程里 `RecursionError`（本机 10 连跑 10/10 红；200 项链的
  `写` 变体则是 pycompile 阶段 `too many nested parentheses`）；
  修复后：10 连跑全绿，且峰值内存有记录（`test_长加法链_十次连跑`）。
- 反证：把 `PythonCodeGenerator._iterative_binary_chain` 置 False 退回旧实现，
  同一条链必须真红（`test_反证_旧递归实现必红`）——不是靠 skip/xfail 变绿的。

## 边界（不修的部分，如实登记）

- 深嵌套括号 / 深嵌套调用：parser 每个括号层约 12 帧（`parser_expr.py` 的 10 级
  优先级阶梯 + factor/primary），实测 60 层可编、80 层即 `RecursionError`。
  `parser_expr.py` 不在本卡允许路径内，本轮不动；不靠 `sys.setrecursionlimit`
  硬抬（Windows 线程栈更小，抬上限只会把「可捕获的 RecursionError」换成
  「打穿 C 栈的硬崩溃」）。`test_深嵌套边界_六十层仍可编` 只守住既有可用区间，
  不掩盖 80 层以上的缺口。
- 运算链超过 CPython 自身的编译上限（实测扁平 `a + b + …` 2500 项 OK、3000 项
  `RecursionError: maximum recursion depth exceeded during compilation`）属宿主
  Python 限制，与光明无关；本卡把光明的阈值从 ~220（SyntaxError）/~1000
  （RecursionError）抬到 CPython 的 ~2500。
- 「内存错误」（MemoryError）：本仓可及样本上**未能复现**。264 个 lightharness
  源模块单进程连跑编译，RSS 稳定在 ~27MB（不随文件数增长）；最大的 140KB 模块
  峰值 RSS ~63MB；5MB 单字符串字面量峰值 ~132MB。详见 .hive/summary.md 的内存曲线。
  在这一量级上「编译器分配失败」不成立，故 MemoryError 只可能是宿主瞬时压力
  （或原始失败快照里更重的模块，本仓未取到）。本文件只对可复现的栈溢出判绿，
  不对「内存错误」编造结论。

阈值全部为 Win10 与 FreeBSD 15.1 两平台实测后取约 2.3 倍余量（见文件内常量注释）。
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')

# ── 实测基线 ────────────────────────────────────────────────────────────
# 2026-11-24 Win10 / CPython 3.13.18：
#   1200 项链 parse 0.024s / gen 0.004s / pycompile 0.012s / 峰值 RSS 51.7MB
#   ≥200KB/≥4000 行大模块 parse 1.59s / gen 0.22s / pycompile 0.14s / 峰值 RSS 62.9MB
# 2026-11-24 192.168.0.88 FreeBSD 15.1 / CPython 3.12.13（同一份夹具）：
#   1200 项链 10 连跑峰值 RSS 106.9~109.4MB（解释器本身更重）
#   大模块 编译 1.77s / 峰值 RSS 132.4MB
# 阈值取两平台最大实测值的 ~2.3 倍，只拦「数量级爆炸」，不拦平台差异。
链条_峰值上限_MB = 250.0
链条_单次耗时上限_s = 5.0
大模块_峰值上限_MB = 300.0
大模块_编译耗时上限_s = 10.0

# 子进程探针：走 CLI 同款链路（LightParser → PythonCodeGenerator → compile → 可选 exec），
# 隔离模块缓存/全局状态，并回报真实的进程峰值内存。src 由 PYTHONPATH 提供，
# 因此 Windows 与 FreeBSD 用同一份脚本。
_子进程脚本 = r'''
# -*- coding: utf-8 -*-
import json, os, sys, time

def _peak_rss_mb():
    if os.name == 'nt':
        import ctypes, ctypes.wintypes as wt
        class _PMC(ctypes.Structure):
            _fields_ = [
                ('cb', wt.DWORD), ('PageFaultCount', wt.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
            ]
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()),
            ctypes.byref(pmc), pmc.cb)
        return pmc.PeakWorkingSetSize / 1048576.0 if ok else 0.0
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1048576.0 if sys.platform == 'darwin' else rss / 1024.0

src_path, mode, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src_path, 'r', encoding='utf-8') as f:
    source = f.read()

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

t0 = time.perf_counter()
module = LightParser().parse(source)
t1 = time.perf_counter()
code = PythonCodeGenerator().generate(module, is_main=True)
t2 = time.perf_counter()
compile(code, '<r225>', 'exec')
t3 = time.perf_counter()

rc = 0
if mode == 'run':
    ns = {'__name__': '__main__', '__file__': src_path}
    try:
        exec(compile(code, src_path, 'exec'), ns)
    except SystemExit as e:
        rc = int(e.code or 0)
    except BaseException as e:
        sys.stderr.write('%s: %s\n' % (type(e).__name__, e))
        rc = 1

stats = {
    'parse_s': round(t1 - t0, 3), 'gen_s': round(t2 - t1, 3), 'pycompile_s': round(t3 - t2, 3),
    'code_chars': len(code), 'code_lines': code.count('\n') + 1,
    'src_chars': len(source), 'src_lines': source.count('\n') + 1,
    'src_bytes': len(source.encode('utf-8')),
    'peak_mb': round(_peak_rss_mb(), 1), 'recursionlimit': sys.getrecursionlimit(),
}
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False)
sys.exit(rc)
'''

_探针缓存 = {}


def _探针路径(tmp_path):
    """把子进程脚本落到临时目录（每个 pytest 会话一份，避免依赖仓库残留）。"""
    p = _探针缓存.get('path')
    if p is None:
        p = str(tmp_path / '_r225_子进程.py')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(textwrap.dedent(_子进程脚本).lstrip('\n'))
        _探针缓存['path'] = p
    return p


def _跑(tmp_path, 源码, 模式='run', 超时=120):
    """子进程跑一段光明源码，返回 (rc, stdout, stderr, stats)。"""
    源文件 = tmp_path / '主.light'
    源文件.write_text(源码, encoding='utf-8', newline='\n')
    结果文件 = tmp_path / 'stats.json'
    if 结果文件.exists():
        结果文件.unlink()
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([SRC, ROOT] + (
        [env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    p = subprocess.run([sys.executable, _探针路径(tmp_path), str(源文件), 模式, str(结果文件)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=超时, cwd=str(tmp_path), env=env)
    stats = json.loads(结果文件.read_text(encoding='utf-8')) if 结果文件.exists() else {}
    return p.returncode, p.stdout or '', p.stderr or '', stats


def _包入口(正文):
    """把语句正文包进 `段落 主程序:`（光明主文件入口约定）。"""
    return '段落 主程序:\n' + ''.join(
        '  ' + 行 + '\n' for 行 in textwrap.dedent(正文).strip('\n').split('\n'))


def _加法链(n):
    return _包入口('设 甲 为 %s。\n写(转字符串(甲))。' % ' + '.join(['1'] * n))


def _进程内跑(源码):
    """进程内编译+运行，返回 stdout 的非空行（语义对拍用，不测内存）。"""
    import contextlib
    import io

    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    module = LightParser().parse(源码)
    code = PythonCodeGenerator().generate(module, is_main=True)
    缓冲 = io.StringIO()
    命名空间 = {'__name__': '__main__', '__file__': '<r225>'}
    with contextlib.redirect_stdout(缓冲):
        exec(compile(code, '<r225>', 'exec'), 命名空间)
    return [行 for 行 in 缓冲.getvalue().replace('\r', '').split('\n') if 行]



def _写拼接链(n):
    return _包入口('写 "a" + %s。' % ' + '.join(['"b"'] * n))


def _大模块(n=4300):
    """≥200KB / ≥4000 行的 .light：逐语句长拼接 + 大段变量，贴近 harness 模块形状。"""
    行 = ['段落 主程序:']
    for i in range(n):
        行.append('  设 变量%d 为 "标签%d" + 转字符串(%d + 1) + "。"。' % (i, i, i))
    for i in range(100):
        行.append('  设 文本%d 为 "标题%d" + 转字符串(变量%d)。' % (i, i, n - 1 - i))
    行.append('  写(变量%d)。' % (n - 1))
    行.append('  写("|")。')
    行.append('  写(变量0)。')
    return '\n'.join(行) + '\n'


# ══════════════════════════════════════════════════════════════════════
# 1. 判据①：长运算链 10 连跑（修复前必红，修复后全绿 + 峰值内存有记录）
# ══════════════════════════════════════════════════════════════════════

def test_长加法链_十次连跑(tmp_path):
    源 = _加法链(1200)
    峰值 = []
    for i in range(10):
        rc, out, err, stats = _跑(tmp_path, 源)
        assert rc == 0, '第 %d 次跑挂了：stderr 尾部=%r stats=%r' % (
            i + 1, err.strip().split('\n')[-3:], stats)
        assert out.strip() == '1200', '第 %d 次输出不对：%r' % (i + 1, out.strip()[:80])
        峰值.append(stats['peak_mb'])
        单次耗时 = stats['parse_s'] + stats['gen_s'] + stats['pycompile_s']
        assert 单次耗时 < 链条_单次耗时上限_s, '第 %d 次耗时 %.1fs 超上限' % (i + 1, 单次耗时)
    # 峰值内存必须真测到（0 表示探针没生效，不能算「有记录」）
    assert all(p > 0 for p in 峰值), 峰值
    assert max(峰值) <= 链条_峰值上限_MB, '峰值 %.1fMB 超上限 %.0fMB（曲线=%r）' % (
        max(峰值), 链条_峰值上限_MB, 峰值)
    print('[R225] 1200 项链 10 连跑峰值 RSS(MB)=%r' % (峰值,))


# ══════════════════════════════════════════════════════════════════════
# 2. 判据①（第二形态）：`写 "a" + …` 合并链，修复前同样栈溢出
# ══════════════════════════════════════════════════════════════════════

def test_写输出长拼接链(tmp_path):
    rc, out, err, stats = _跑(tmp_path, _写拼接链(1000))
    assert rc == 0, '写拼接链挂了：%r stats=%r' % (err.strip().split('\n')[-3:], stats)
    assert out.strip() == 'a' + 'b' * 1000, '输出被截断：长度=%d' % len(out.strip())
    assert stats['peak_mb'] <= 链条_峰值上限_MB, stats


# ══════════════════════════════════════════════════════════════════════
# 3. 判据②：≥200KB / ≥4000 行大模块的编译耗时与峰值内存基线
# ══════════════════════════════════════════════════════════════════════

def test_大模块基线_两百KB四千行(tmp_path):
    源 = _大模块()
    行数 = 源.count('\n')
    字节数 = len(源.encode('utf-8'))
    assert 行数 >= 4000, '夹具行数 %d < 4000' % 行数
    assert 字节数 >= 200 * 1024, '夹具字符数 %d < 200KB' % 字节数

    rc, out, err, stats = _跑(tmp_path, 源, 超时=180)
    assert rc == 0, '大模块编译/运行挂了：%r stats=%r' % (err.strip().split('\n')[-3:], stats)
    assert stats['src_lines'] >= 4000, stats
    assert stats['src_bytes'] >= 200 * 1024, stats
    # 产物规模与输出都核对，防止「编译通过但代码被截断」
    assert stats['code_lines'] > 8000, stats
    输出 = out.strip()
    assert '标签42994300。' in 输出 and 输出.endswith('标签01。'), 输出[-40:]

    编译耗时 = stats['parse_s'] + stats['gen_s'] + stats['pycompile_s']
    assert 编译耗时 < 大模块_编译耗时上限_s, '耗时 %.2fs 超上限 %.0fs' % (编译耗时, 大模块_编译耗时上限_s)
    assert stats['peak_mb'] <= 大模块_峰值上限_MB, '峰值 %.1fMB 超上限 %.0fMB' % (
        stats['peak_mb'], 大模块_峰值上限_MB)
    print('[R225] 大模块：%d 行 / %d 字节，编译 %.2fs，峰值 %.1fMB' % (
        stats['src_lines'], stats['src_chars'], 编译耗时, stats['peak_mb']))


# ══════════════════════════════════════════════════════════════════════
# 4. 反证：旧递归实现必须真红（不许靠 skip / xfail 变绿）
# ══════════════════════════════════════════════════════════════════════

def test_反证_旧递归实现必红():
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    module = LightParser().parse(_加法链(1200))

    gen = PythonCodeGenerator()
    gen._iterative_binary_chain = False
    with pytest.raises(RecursionError):
        gen.generate(module, is_main=True)

    # `写` 合并链的旧路径同样必须红
    gen2 = PythonCodeGenerator()
    gen2._iterative_binary_chain = False
    with pytest.raises(RecursionError):
        gen2.generate(LightParser().parse(_写拼接链(1000)), is_main=True)


# ══════════════════════════════════════════════════════════════════════
# 5. 修复口径：不是靠 sys.setrecursionlimit 硬抬；低上限下也必须能编
# ══════════════════════════════════════════════════════════════════════

def test_修复不靠抬高递归上限():
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    原上限 = sys.getrecursionlimit()
    module = LightParser().parse(_加法链(1200))
    code = PythonCodeGenerator().generate(module, is_main=True)
    assert sys.getrecursionlimit() == 原上限, '生成器改动了进程递归上限（那是硬抬，不是修复）'

    # 上限压到 700（低于旧实现所需）仍必须生成成功：栈深度与链长无关
    sys.setrecursionlimit(700)
    try:
        代码 = PythonCodeGenerator().generate(LightParser().parse(_加法链(1200)), is_main=True)
        compile(代码, '<r225>', 'exec')
    finally:
        sys.setrecursionlimit(原上限)


# ══════════════════════════════════════════════════════════════════════
# 6. 语义不变：扁平化只去括号，不改结合顺序/优先级/特殊算子口径
# ══════════════════════════════════════════════════════════════════════

_语义样例 = [
    ('混合优先级', '设 甲 为 1 + 2 * 3 - 4 整除 2。\n写(转字符串(甲))。', ['5']),
    ('减法左结合', '设 甲 为 10 - 3 - 2 - 1。\n写(转字符串(甲))。', ['4']),
    ('乘法链', '设 甲 为 2 * 3 * 4。\n写(转字符串(甲))。', ['24']),
    ('比较与逻辑', '设 甲 为 1。\n设 乙 为 2。\n设 丙 为 (甲 < 乙) 且 (乙 < 3)。\n写(转字符串(丙))。', ['真']),
    ('字符串包含', '设 丙 为 "abc" 包含 "b"。\n写(转字符串(丙))。', ['真']),
    ('写拼接合并', '设 甲 为 3。\n写 "值=" + 转字符串(甲) + "!"。', ['值=3!']),
    ('除以真除', '写(转字符串(7 除以 2))。\n写("|")。\n写(转字符串(-7 除以 2))。', ['3.5|-3.5']),
    ('整除截断', '写(转字符串(7 整除 2))。\n写("|")。\n写(转字符串(-7 整除 2))。', ['3|-4']),
    ('幂运算', '写(转字符串(2 幂 3))。\n写("|")。\n写(转字符串(2 幂 3 幂 1))。', ['8|8']),
    ('位异或', '写(转字符串(6 位异或 3))。', ['5']),
]


@pytest.mark.parametrize('名字,正文,期望', _语义样例, ids=[c[0] for c in _语义样例])
def test_语义不变_样例(名字, 正文, 期望):
    # 进程内编译+运行：语义对拍不需要子进程隔离，也不该为 3 行源码付一次解释器启动。
    输出 = _进程内跑(_包入口(正文))
    assert 输出 == 期望, '%s 输出漂移：%r' % (名字, 输出)


# ══════════════════════════════════════════════════════════════════════
# 7. 已知边界（不掩盖）：parser 深嵌套 60 层仍在可用区间
# ══════════════════════════════════════════════════════════════════════

def test_深嵌套边界_六十层仍可编():
    """R225 的修复不覆盖 parser 深嵌套（parser_expr.py 不在本卡路径内）。

    这里只守「既有可用区间不倒退」：60 层括号仍是绿的；80 层起会 RecursionError
    （见文件头「边界」段），不在此断言成绿，也不许用 skip 粉饰。
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    depth = 60
    源 = _包入口('设 甲 为 %s1%s。\n写(转字符串(甲))。' % ('(' * depth, ')' * depth))
    模块 = LightParser().parse(源)
    代码 = PythonCodeGenerator().generate(模块, is_main=True)
    compile(代码, '<r225-nest>', 'exec')
    assert _进程内跑(源) == ['1']


# ══════════════════════════════════════════════════════════════════════
# 8. 内存探针自证（两平台都要拿得到 >0 的峰值，否则上面的阈值形同虚设）
# ══════════════════════════════════════════════════════════════════════

def test_峰值内存探针可用(tmp_path):
    rc, out, err, stats = _跑(tmp_path, _加法链(50), 模式='compile')
    assert rc == 0, err[-200:]
    assert stats.get('peak_mb', 0) > 0, '峰值内存取不到（%r），阈值断言不可信' % stats
    assert stats.get('recursionlimit') == 1000, '子进程默认递归上限不是 1000：%r' % stats
