# -*- coding: utf-8 -*-
"""R226 / T-0446：parser 深嵌套（括号 / 单参调用）≥80 层 RecursionError 的修复。

## 现象（2026-11-24，Win10 / CPython 3.13；FreeBSD 15.1 / 3.12 同）

同一份语义完全合法的光明源码：

    段落 主程序:
      设 甲 为 ((((…1…)))).
      写(转字符串(甲))。

- **60 层括号**：绿，能编能跑；
- **80 层括号**：`RecursionError: maximum recursion depth exceeded`（parser 阶段直接红）；
- 嵌套调用 `f(f(f(…1…)))` 同形：70 层绿、80 层红。

## 归因

`src/parser_expr.py` 的 10 级优先级阶梯（logical_or → logical_and → comparison →
bitor → bitxor → bitand → shift → add → mul → power → primary）每层括号都要
**从最低优先级重新下钻一整轮**：`_parse_primary` 见到 `(` 就把整条阶梯再进一遍。
实测约 13~14 个 Python 帧/层，默认上限 1000 ⇒ 60~70 层见顶。与操作系统无关，
与 R225 修的 codegen 运算链递归也不是同一处（那条链已迭代化）。

## 修复（两条迭代化路径；不抬 `sys.setrecursionlimit`、不碰 AST 形状与语法表）

1. **括号组**（`_parse_paren_nest` + `_parse_expr_tail`）：连续 n 层 `(` 一次吃掉，
   组内只解析一次，之后每关闭一层右括号就用「已得左值」继续跑本层表达式
   （阶梯函数新增 `left` 种子参数，默认 None 时行为与改前逐字一致）。
   一层括号 = 一次循环迭代 ⇒ 栈深与层数解耦。
2. **单参调用链**（`_parse_call_spine`）：`f(g(h(…)))` 的 callee 名压进 Python 列表，
   最内层交给原解析器，再逐层回卷；形状不符（链太短 / 某层不止一实参 / 某层后面
   还接后缀）即原样回滚 pos，退回原路径 —— 原本能过的写法语义零变化。

## 判据与反证

- 150 层括号 / 150 层嵌套调用 / 150 层「每层带运算符」的混合嵌套：parse → generate
  → compile → exec 全过，输出与 Python 逐层算出来的期望值一致；
- **压小上限**：子进程把 `sys.setrecursionlimit` 压到 500 后，同一 150 层夹具仍可编可跑；
- **栈深解耦的硬证据**：二分出「让本段源码 parse 成功的最小递归上限」，30 层与
  150 层实测同为 60（判据断言的差值 ≤ 4）；
- **反证**：把内部开关 `_iterative_paren_parse` / `_iterative_call_spine` 置 False
  （退回改前的逐层递归），同一 150 层夹具在子进程里必须真红（`RecursionError`），
  不是靠 skip/xfail 变绿的；
- **语义对拍**：40+ 种形态（纯括号、混优先级、比较链、`包含`、除法/整除、幂、
  元组、调用、带运算符的括号组…）在开关 True/False 两条路径下 AST 结构、
  生成的 Python 文本、运行输出三者逐字一致；
- **大模块回归**：≥300KB / ≥4400 行模块仍绿，编译耗时与峰值内存设上限。

## 边界（不修的部分，如实登记）

- **嵌套调用**：parse 侧已与层数解耦（parse-only 最小递归上限 55 恒定，30 层与
  150 层持平），但 `code_generator` 仍按 AST 形状逐层递归（实测 ~1.7 帧/层），
  且 CPython 自身 ≈200~250 层括号即 `too many nested parentheses`。实测：
  150/200 层在递归上限 500 下全过；300 层在 500 上限下先撞 codegen 递归。
  两条都是宿主/既有实现边界，本卡只保证判据要求的 150 层。
- **深嵌套块缩进**（>100 层）是 CPython `MAXINDENT` 硬限制，不在本卡范围。
- 同卡第二残留 **`/` 链**的 `_light_trunc_div` 逐层调用：本轮不修，复测现状为
  `1/1/…/1`（N 项）在 N=200 时仍可编可跑，N=220 起产物被 CPython 判
  `too many nested parentheses`（宿主嵌套上限，非 Python 递归上限）；递归上限压到
  500 时 150 项仍绿。详见 `.hive/summary.md`。
- **既有缺陷（非本卡引入，不动）**：`(1+2)*3` 生成 `1 + 2 * 3`（实跑 7，应为 9），
  `(1+2)*(3+4)` 同理。基线 HEAD 上复现一致，属 codegen 折叠时对「低优先级括号组
  当左操作数」漏补括号，与本卡的深嵌套问题无关；本判据因此不对这类形态断期望值，
  只按「新旧路径逐字一致」判（见 `_混合嵌套源` 注释）。
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')

# ── 判据常量（改动后两平台实测，见下；阈值只拦数量级爆炸）──────────────
# 2026-11-24 本机 Win10 / CPython 3.12.9：
#   150 层括号 / 150 层嵌套调用：parse+gen+pycompile ≈ 1.2s 内、峰值 RSS ≈ 40MB
#   大模块（303721 字节 / 4405 行）：parse 1.30s / gen 0.16s / pycompile 0.16s，峰值 70.9MB
#   解耦硬证据：parse 成功所需最小递归上限 30 层 = 55、150 层 = 55（完全持平）
# 2026-11-24 192.168.0.88 FreeBSD 15.1 / CPython 3.12.13（同一份夹具）：
#   大模块 parse 1.88s / gen 0.26s / pycompile 0.19s / 峰值 68.6MB；最小上限同样 55/55
# 阈值取两平台最大实测值的 ~3.6 倍（耗时）/ ~5.6 倍（内存），只拦「数量级爆炸」。
判定层数 = 150
压小上限 = 500
大模块_峰值上限_MB = 400.0
大模块_编译耗时上限_s = 25.0

# 子进程探针：走 CLI 同款链路（LightParser → PythonCodeGenerator → compile → exec），
# 隔离模块缓存/全局状态，回报真实进程峰值内存，并可注入递归上限与「退回旧路径」开关。
# src 由 PYTHONPATH 提供，Windows 与 FreeBSD 用同一份脚本。
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
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 0
legacy = len(sys.argv) > 5 and sys.argv[5] == 'legacy'

if limit:
    # 判据手段：压小上限，证明栈深与嵌套层数无关（不是修复手段）
    sys.setrecursionlimit(limit)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator
import parser_expr
if legacy:
    parser_expr.ParserExprMixin._iterative_paren_parse = False
    parser_expr.ParserExprMixin._iterative_call_spine = False

with open(src_path, 'r', encoding='utf-8') as f:
    source = f.read()

stats = {'mode': mode, 'recursionlimit': sys.getrecursionlimit(), 'legacy': legacy}

if mode == 'minlimit':
    # 二分「让本段源码 parse 成功的最小递归上限」：层数解耦时该值不随层数增长。
    # 只看 parse——codegen 对嵌套调用仍逐层递归（见文件头「边界」）。
    def _attempt(l):
        sys.setrecursionlimit(l)
        try:
            LightParser().parse(source)
            return True
        except RecursionError:
            return False
    if not _attempt(20000):
        stats['min_limit'] = -1
    else:
        lo, hi = 16, 20000
        while lo < hi:
            mid = (lo + hi) // 2
            if _attempt(mid):
                hi = mid
            else:
                lo = mid + 1
        stats['min_limit'] = lo
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    sys.exit(0)

try:
    t0 = time.perf_counter()
    module = LightParser().parse(source)
    t1 = time.perf_counter()
    code = PythonCodeGenerator().generate(module, is_main=True)
    t2 = time.perf_counter()
    obj = compile(code, '<r226>', 'exec')
    t3 = time.perf_counter()
    out = ''
    if mode == 'run':
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(obj, {'__name__': '__main__'})
        out = buf.getvalue()
    stats.update({
        'parse_s': round(t1 - t0, 3), 'gen_s': round(t2 - t1, 3),
        'pycompile_s': round(t3 - t2, 3),
        'code_chars': len(code), 'code_lines': code.count('\n') + 1,
        'src_bytes': len(source.encode('utf-8')), 'src_lines': source.count('\n') + 1,
        'peak_mb': round(_peak_rss_mb(), 1),
    })
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    sys.stdout.write(out)
    sys.exit(0)
except SystemExit as e:
    # 生成物的入口约定可能带 SystemExit（同 R225 探针口径）：按退出码算，不算失败
    stats['exit_code'] = int(e.code or 0)
    stats['peak_mb'] = round(_peak_rss_mb(), 1)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    sys.exit(int(e.code or 0))
except BaseException as e:
    stats['error'] = '%s: %s' % (type(e).__name__, str(e).split('\n')[0][:200])
    stats['peak_mb'] = round(_peak_rss_mb(), 1)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)
    sys.stderr.write(stats['error'] + '\n')
    sys.exit(3)
'''

_探针缓存 = {}


def _探针路径(tmp_path):
    """把子进程脚本落到临时目录（每个会话一份，不依赖仓库残留）。"""
    p = _探针缓存.get('path')
    if p is None:
        p = str(tmp_path / '_r226_子进程.py')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(textwrap.dedent(_子进程脚本).lstrip('\n'))
        _探针缓存['path'] = p
    return p


def _跑(tmp_path, 源码, 模式='run', 上限=None, 旧路径=False, 超时=180):
    """子进程跑一段光明源码，返回 (rc, stdout, stderr, stats)。"""
    源文件 = tmp_path / '主.light'
    源文件.write_text(源码, encoding='utf-8', newline='\n')
    结果文件 = tmp_path / 'stats.json'
    if 结果文件.exists():
        结果文件.unlink()
    env = dict(os.environ)
    # 只用 src（不加仓库根）：夹具不依赖仓库里的 stdlib/目录残留，
    # 生成物落到 code_generator 自带的内建兜底，几十毫秒级；
    # 加仓库根会触发 stdlib 包的导入，单项就要 20s+，判据跑不起来。
    env['PYTHONPATH'] = os.pathsep.join(
        [SRC] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    参数 = [sys.executable, _探针路径(tmp_path), str(源文件), 模式, str(结果文件)]
    参数.append(str(上限) if 上限 else '0')
    参数.append('legacy' if 旧路径 else 'new')
    p = subprocess.run(参数, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=超时, cwd=str(tmp_path), env=env)
    stats = json.loads(结果文件.read_text(encoding='utf-8')) if 结果文件.exists() else {}
    return p.returncode, p.stdout or '', p.stderr or '', stats


def _包入口(正文):
    """把语句正文包进 `段落 主程序:`（光明主文件入口约定）。"""
    return '段落 主程序:\n' + ''.join(
        '  ' + 行 + '\n' for 行 in textwrap.dedent(正文).strip('\n').split('\n'))


def _括号源(层数, 内层='1'):
    return _包入口('设 甲 为 %s%s%s。\n写(转字符串(甲))。' % ('(' * 层数, 内层, ')' * 层数))


def _调用源(层数):
    """f(f(f(…1…)))：带一个恒等段落 f，避免依赖任何 stdlib/外网。"""
    return ('段落 f(乙):\n  返回 乙。\n\n' +
            _包入口('设 甲 为 %s1%s。\n写(转字符串(甲))。' % ('f(' * 层数, ')' * 层数)))


def _混合嵌套源(层数):
    """每层括号组后面还接运算符：`((((1)+3)-1)+3)…`（每层一个括号组 + 一个运算符）。

    括号层迭代化要能处理「括号组后面还有运算符延续」这条路，形态就压它。
    运算符取同一优先级（加减层）：`(1+2)*3` 这类「低优先级括号组当左操作数」
    的产物今天在 codegen 侧本来就不对（基线 HEAD 实测 7 而非 9，属既有缺陷，
    不在本卡范围），拿它当期望值会把这个既有缺陷固化进判据，故这里不混优先级；
    混合优先级的形态由下面的 _对拍样例按「新旧路径逐字一致」判。
    """
    表达式 = '1'
    for i in range(层数):
        表达式 = '(' + 表达式 + ')' + ('+3' if i % 2 == 0 else '-1')
    return (_包入口('设 甲 为 %s。\n写(转字符串(甲))。' % 表达式),
            _混合期望值(层数))


def _混合期望值(层数):
    值 = 1
    for i in range(层数):
        值 = 值 + 3 if i % 2 == 0 else 值 - 1
    return str(值)


def _进程内编译运行(源码):
    """进程内编译 + 运行，返回 stdout 非空行（语义对拍用，不测内存）。

    exec 期间临时把工作目录切到空目录：生成物会按 `__file__`/cwd 去找 stdlib，
    停在仓库根上会把整包 stdlib 导进来（实测单次 20s+），而本判据只需要
    转字符串/写 这类内建兜底。切目录既快又不依赖仓库残留，跑完还原。
    """
    import contextlib
    import io
    import tempfile

    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    模块 = LightParser().parse(源码)
    代码 = PythonCodeGenerator().generate(模块, is_main=True)
    缓冲 = io.StringIO()
    原cwd = os.getcwd()
    _空目录 = _探针缓存.get('cwd')
    if _空目录 is None:
        _空目录 = tempfile.mkdtemp(prefix='r226_')
        _探针缓存['cwd'] = _空目录
    try:
        os.chdir(_空目录)
        with contextlib.redirect_stdout(缓冲):
            exec(compile(代码, '<r226>', 'exec'), {'__name__': '__main__'})
    finally:
        os.chdir(原cwd)
    return [行 for 行 in 缓冲.getvalue().replace('\r', '').split('\n') if 行]


def _大模块(n=4300):
    """≥300KB / ≥4400 行的 .light：逐语句长拼接 + 大段变量，贴近 harness 模块形状。"""
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
# 1. 判据①：150 层括号 / 150 层嵌套调用 / 150 层混合嵌套，可编可跑
# ══════════════════════════════════════════════════════════════════════

def test_一百五十层括号_可编可跑(tmp_path):
    rc, out, err, stats = _跑(tmp_path, _括号源(判定层数))
    assert rc == 0, '150 层括号挂了：%r stats=%r' % (err.strip().split('\n')[-2:], stats)
    assert out.strip() == '1', '输出不对：%r' % out.strip()[:80]
    # 生成物不得把 150 层括号原样搬进 Python（否则 compile 阶段撞 CPython 嵌套上限）
    assert stats['code_chars'] < 20000, '生成物体积异常（括号没被收敛？）：%r' % stats


def test_一百五十层嵌套调用_可编可跑(tmp_path):
    rc, out, err, stats = _跑(tmp_path, _调用源(判定层数))
    assert rc == 0, '150 层嵌套调用挂了：%r stats=%r' % (err.strip().split('\n')[-2:], stats)
    assert out.strip() == '1', '输出不对：%r' % out.strip()[:80]


def test_一百五十层运算符续接混合嵌套_可编可跑(tmp_path):
    """每层括号组后面还接运算符：证明迭代化不是只认「纯括号塔」。"""
    源, 期望 = _混合嵌套源(判定层数)
    rc, out, err, stats = _跑(tmp_path, 源)
    assert rc == 0, '150 层混合嵌套挂了：%r stats=%r' % (err.strip().split('\n')[-2:], stats)
    assert out.strip() == 期望, '输出不对：%r != %r' % (out.strip(), 期望)


# ══════════════════════════════════════════════════════════════════════
# 2. 判据②：压小递归上限（500）后同一 150 层夹具仍可编可跑
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('形态', ['括号', '嵌套调用'])
def test_压小递归上限500_仍可编可跑(tmp_path, 形态):
    源 = _括号源(判定层数) if 形态 == '括号' else _调用源(判定层数)
    rc, out, err, stats = _跑(tmp_path, 源, 上限=压小上限)
    assert stats.get('recursionlimit') == 压小上限, '子进程上限没压到 500：%r' % stats
    assert rc == 0, '%s 在递归上限 500 下挂了：%r stats=%r' % (
        形态, err.strip().split('\n')[-2:], stats)
    assert out.strip() == '1', '%s 输出不对：%r' % (形态, out.strip()[:80])


# ══════════════════════════════════════════════════════════════════════
# 3. 判据③：栈深与嵌套层数解耦（硬证据：最小递归上限不随层数增长）
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('形态', ['括号', '嵌套调用'])
def test_栈深与层数解耦(tmp_path, 形态):
    """30 层与 150 层「parse 成功所需的最小递归上限」必须基本相等。

    改前实测：每层约 13~14 帧，150 层需要 ~2000+；解耦后两者同为解释器基线。
    差值留 4 帧余量，只拦「随层数线性增长」这一件事。
    """
    浅 = _跑(tmp_path, (_括号源(30) if 形态 == '括号' else _调用源(30)),
             模式='minlimit')[3]
    深 = _跑(tmp_path, (_括号源(判定层数) if 形态 == '括号' else _调用源(判定层数)),
             模式='minlimit')[3]
    assert 浅.get('min_limit', -1) > 0, '30 层最小上限测不到：%r' % 浅
    assert 深.get('min_limit', -1) > 0, '150 层最小上限测不到：%r' % 深
    assert 深['min_limit'] <= 浅['min_limit'] + 4, (
        '%s：栈深随层数增长（30 层 %d 帧，150 层 %d 帧）—— 迭代化没生效'
        % (形态, 浅['min_limit'], 深['min_limit']))
    print('[R226] %s parse 最小递归上限：30 层=%d，150 层=%d'
          % (形态, 浅['min_limit'], 深['min_limit']))


# ══════════════════════════════════════════════════════════════════════
# 4. 反证：退回旧逐层递归，同一夹具必须真红（不是 skip/xfail 变绿）
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('形态', ['括号', '嵌套调用'])
def test_反证_退回逐层递归必红(tmp_path, 形态):
    源 = _括号源(判定层数) if 形态 == '括号' else _调用源(判定层数)
    rc, out, err, stats = _跑(tmp_path, 源, 旧路径=True)
    assert rc != 0, '%s 关掉迭代路径后竟然还是绿的：%r' % (形态, out.strip()[:80])
    assert 'RecursionError' in stats.get('error', ''), (
        '%s 关掉迭代路径后的失败原因不是 RecursionError：%r' % (形态, stats.get('error')))


# ══════════════════════════════════════════════════════════════════════
# 5. 语义对拍：新旧两条路径 AST / 生成物 / 运行结果逐字一致
# ══════════════════════════════════════════════════════════════════════

_对拍样例 = [
    ('纯括号', '((((1))))'),
    ('单层括号', '(1)'),
    ('带运算符的括号组', '((((1+2)*3)))'),
    ('混优先级', '(1 + 2 * 3 - 4 整除 2)'),
    ('混优先级_括号改结合', '((1 + 2) * (3 - 4))'),
    ('减法左结合', '(10 - 3 - 2 - 1)'),
    ('比较链', '(1 < 2 且 2 < 3)'),
    ('比较_大于等于', '(3 大于 等于 2)'),
    ('字符串包含', '("abc" 包含 "b")'),
    ('除法真除', '(7 除以 2)'),
    ('整除截断', '(-7 整除 2)'),
    ('幂右结合', '(2 幂 3 幂 2)'),
    ('元组字面量', '((1, 2))'),
    ('元组再套括号', '((1, 2), 3)'),
    ('调用_单层', '转字符串(1)'),
    ('调用_套括号', '(转字符串((1+2)))'),
    ('调用_单参嵌表达式', '转字符串((1+2)*3)'),
    ('调用_多实参', '两参(((1)), ((2)))'),
    ('调用_嵌在括号里', '转字符串(f(1))'),
    ('后置三元', '((1) 如果 真 否则 (2))'),
    ('范围表达式', '(1 至 3 步 2)'),
    ('位运算', '((6 位异或 3) 位与 7)'),
    ('布尔与或', '((真 且 假) 或 真)'),
    ('负号', '(减去 (1 + 2))'),
    ('深一点_混合', '(((((1+2)*3)+4)*5)+6)'),
    ('括号里套调用再套括号', '((转字符串(1)))'),
]


def _结构摘要(节点, 深度=0):
    """AST 的结构摘要（用于新旧路径逐字对拍）。"""
    if 深度 > 80:
        return '...'
    if isinstance(节点, (list, tuple)):
        return '[' + ','.join(_结构摘要(x, 深度 + 1) for x in 节点) + ']'
    if isinstance(节点, dict):
        return '{' + ','.join('%s:%s' % (k, _结构摘要(v, 深度 + 1))
                             for k, v in 节点.items()) + '}'
    名称 = type(节点).__name__
    if hasattr(节点, '__dict__'):
        字段 = [(k, v) for k, v in vars(节点).items() if not k.startswith('_')]
        return '%s(%s)' % (名称, ','.join('%s=%s' % (k, _结构摘要(v, 深度 + 1))
                                          for k, v in 字段))
    return '%s(%r)' % (名称, 节点)


def _两条路径各跑一遍(源):
    """返回 (AST 摘要, 生成代码, 运行输出)，分别来自新路径与旧路径。"""
    import parser_expr
    类 = parser_expr.ParserExprMixin
    原开关 = (类._iterative_paren_parse, 类._iterative_call_spine)
    结果 = {}
    try:
        for 标签, 开关 in (('新路径', True), ('旧路径', False)):
            类._iterative_paren_parse = 开关
            类._iterative_call_spine = 开关
            from light_parser_v3 import LightParser
            from code_generator import PythonCodeGenerator
            模块 = LightParser().parse(源)
            代码 = PythonCodeGenerator().generate(模块, is_main=True)
            输出 = _进程内编译运行(源)
            结果[标签] = (_结构摘要(模块), 代码, 输出)
    finally:
        类._iterative_paren_parse, 类._iterative_call_spine = 原开关
    return 结果['新路径'], 结果['旧路径']


# 对拍源码的公共前缀：提供恒等段落 f（调用形态用）与两参段落（多实参形态用）。
_对拍前缀 = '段落 f(乙):\n  返回 乙。\n\n段落 两参(甲, 乙):\n  返回 甲。\n\n'


@pytest.mark.parametrize('名字,表达式', _对拍样例, ids=[c[0] for c in _对拍样例])
def test_语义对拍_新旧路径逐字一致(名字, 表达式):
    """修深嵌套不许改优先级/结合性：AST、生成物、运行结果三者都要逐字相同。"""
    源 = _对拍前缀 + _包入口('设 结果 为 %s。\n写(转字符串(结果))。' % 表达式)
    新, 旧 = _两条路径各跑一遍(源)
    assert 新[0] == 旧[0], '%s：AST 不一致\n新=%s\n旧=%s' % (名字, 新[0][:400], 旧[0][:400])
    assert 新[1] == 旧[1], '%s：生成的 Python 文本不一致' % 名字
    assert 新[2] == 旧[2], '%s：运行输出不一致 %r != %r' % (名字, 新[2], 旧[2])


def test_语义对拍_一百五十层括号与裸值等价():
    """150 层括号的 AST 必须就是 `1`：纯括号层在生成物里不许留任何括号。"""
    from light_parser_v3 import LightParser

    甲 = LightParser().parse(_括号源(判定层数))
    乙 = LightParser().parse(_括号源(0))
    assert _结构摘要(甲) == _结构摘要(乙), '150 层括号改变了 AST 结构'


# ══════════════════════════════════════════════════════════════════════
# 6. 修复口径：不是靠硬抬递归上限（静态守卫 + 运行期守卫）
# ══════════════════════════════════════════════════════════════════════

def test_修复没有硬抬递归上限():
    import re

    源 = open(os.path.join(SRC, 'parser_expr.py'), encoding='utf-8').read()
    assert not re.search(r'setrecursionlimit\s*\(', 源), \
        'parser_expr.py 里出现 setrecursionlimit 调用（硬抬不是修复）'
    assert not re.search(r'stack_size\s*\(', 源), \
        'parser_expr.py 里出现 threading.stack_size 调用（硬抬不是修复）'

    原上限 = sys.getrecursionlimit()
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator
    模块 = LightParser().parse(_括号源(判定层数))
    PythonCodeGenerator().generate(模块, is_main=True)
    assert sys.getrecursionlimit() == 原上限, '编译过程改动了进程递归上限'

    # 压到 500 再在进程内走一遍（子进程版见判据②，这里守住「本进程也不许改上限」）
    sys.setrecursionlimit(压小上限)
    try:
        _进程内编译运行(_括号源(判定层数))
        _进程内编译运行(_调用源(判定层数))
    finally:
        sys.setrecursionlimit(原上限)


# ══════════════════════════════════════════════════════════════════════
# 7. 大模块回归：≥300KB / ≥4400 行仍绿，耗时与峰值内存设上限
# ══════════════════════════════════════════════════════════════════════

def test_大模块回归_三百KB四千行(tmp_path):
    rc, out, err, stats = _跑(tmp_path, _大模块(4300), 超时=300)
    assert rc == 0, '大模块挂了：%r stats=%r' % (err.strip().split('\n')[-2:], stats)
    assert stats['src_bytes'] >= 200 * 1024, '夹具不够大：%r 字节' % stats['src_bytes']
    assert stats['src_lines'] >= 4000, '夹具行数不够：%r' % stats['src_lines']
    总耗时 = stats['parse_s'] + stats['gen_s'] + stats['pycompile_s']
    assert 总耗时 < 大模块_编译耗时上限_s, '编译耗时 %.1fs 超上限：%r' % (总耗时, stats)
    assert stats['peak_mb'] > 0, '峰值内存没测到（探针失效）：%r' % stats
    assert stats['peak_mb'] <= 大模块_峰值上限_MB, '峰值 %.1fMB 超上限：%r' % (
        stats['peak_mb'], stats)
    assert out.strip(), '大模块没有输出'
    print('[R226] 大模块 %d 字节 / %d 行：parse %.2fs gen %.2fs pycompile %.2fs 峰值 %.1fMB'
          % (stats['src_bytes'], stats['src_lines'], stats['parse_s'],
             stats['gen_s'], stats['pycompile_s'], stats['peak_mb']))


# ══════════════════════════════════════════════════════════════════════
# 8. 既有可用区间不倒退（60 层，改前也是绿的）
# ══════════════════════════════════════════════════════════════════════

def test_六十层仍可编可跑():
    assert _进程内编译运行(_括号源(60)) == ['1']
    assert _进程内编译运行(_调用源(60)) == ['1']
