# -*- coding: utf-8 -*-
"""R220 · linter 内置名清单 ↔ 运行期真身，**真起 CLI** 的逐名对拍门禁（T-0278）。

为什么还要一份（LH40 已经有了）
------------------------------
`tests/unit/test_LH40_清单对拍.py` 的双闸走的是「进程内生成 Python → 只 exec
preamble → ast 把 Call 换成 func 后 eval」。它快、无副作用，但**没有真的启动
解释器入口**：`cli.light run` 的参数解析、stdlib 物理路径挂载、preamble 的
`_light_builtin` 兜底分支、错误包装层，全都没被走到。本文件补的就是这一整段
真实链路——每个登记名都用 `subprocess` 真起 `python -m cli.light run` 探测。
两个门禁是互补的两层，不是重复。

探针为什么长这样
----------------
   试:
       设 __p 为 <名字>(__哨兵__)
   捕 错误 为 e:
       打印 "R220|<i>|", 转字符串(e)

* `__哨兵__` 是**故意不定义**的实参。Python 求值 `f(x)` 时先解析 `f` 再求值 `x`：
  - 名字有真身 → 解析成功 → 实参炸 `name '__哨兵__' is not defined`；
  - 名字没真身 → 直接炸 `name '<名字>' is not defined`。
  于是**函数体永远不会被执行**（`退出程序` 不会 sys.exit，`输入` 不会等 stdin），
  却仍然真真切切地走完了「解析名字」这一步。
* 调用必须放在 `设 __p 为 ...` 右侧：把 `假(...)` / `枚举(...)` / `新建(...)`
  之类放到语句开头会被词法判「保留关键字不能直接作为语句开头」，整批探针
  直接解析失败。这个形态是实测撞过 15 个语法错误后定下来的。
* 每个名字一条独立的 `试/捕`，stdout 打一行带索引的标记 ⇒ 一次 CLI 就能拿到
  **逐名**结果；同时用「标记集合 == 探测名单」钉死覆盖完整性，杜绝「零标记全绿」。
* 刻意**顺序**起 CLI、不并发，并在 Windows 上带 `CREATE_NO_WINDOW`：
  无控制台父进程下高频 spawn console 子进程会撞 conhost 分配竞争
  （T-0206 的死锁形态）。全量 CI 走 `-n 4`，各 worker 的 CLI 子进程仍可能并发，
  所以这个标志不能省；`HIVE_NO_WINDOW=0` 是逃生阀。

判别力边界（重要，别当双向判据用）
----------------------------------
本门禁只钉「**清单里的名字 → 运行期可达**」这一个方向。反方向有已知盲区：
`repr` / `len` 真 CLI 下也能解析到（Python 内置名泄漏），但它们不是光明内置名。
`test_R220_可达闸对Python内置名泄漏无牙` 会实证这个盲区，提醒后人别删 LH40 闸 A。
清单 ⊆ 权威注册表那一半仍由 LH40 闸 A 负责；本文件不重复实现。

T-0278 现场定性（卡面 §一 的证据已过期，此处留痕，不改 docs/）
--------------------------------------------------------------
  集合创建        rc=1 / name '集合创建' is not defined，但它**已不在**清单里
                  （T-0213 剔除），现状不是「清单假绿」；真写法 `集合([...])`。
  字典设置默认值  rc=1 / name '字典设置默认值' is not defined，清单 0 处、
                  stdlib 0 处 —— 从未登记也从未实现，是清单外的未落地提案，
                  不属于「清单 → 运行期」对拍范围。补实现要给
                  `src/code_generator.py::builtin_map` 接线（T-0277 独占），本卡做不到。
  对拍结论        清单 333 名，332 个可写探针全部可达，`新建` 关键字式单列 ⇒
                  三态处置里「假绿差异」0 项，本卡不增删任何登记名。

另有一类**反向脱节**：`stdlib/builtins.py::__all__` 里 11 个名字只在 `__all__`、
不在 `builtin_map`（`众数` / `圆周率` / `平均数` / …），真 CLI 裸调用全部
NameError。它们也不在清单里——清单没盖章是对的，**不要**因为「`__all__` 说有」
就补登，那会凭空造出新假绿。对应用例是 `test_R220_地板导出但未接线的名字不许进清单`。
"""
import functools
import importlib.util
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SENTINEL = '__哨兵__'
# 名字解析成功才会走到实参求值，于是哨兵报未定义 = 该名字可达。
_REACHABLE = "name '__哨兵__' is not defined"
_MARK = re.compile(r'^R220\|(\d+)\|\s*(.*)$')

# 关键字式内置：只能写 `新建 类名()`，写成 `<名字>(...)` 解析器报「期望类名」。
# 集合必须**精确**等于实测写不出的名字，多一个少一个都要红——防止变成豁免抽屉。
_KEYWORD_FORM_NAMES = frozenset({'新建'})

_NEW_KEYWORD_PROBE = '''类 哨兵盒：
    段落 初始化(自己, 甲):
        设 自己.值 为 甲
试:
    设 __p 为 新建 哨兵盒(__哨兵__)
捕 错误 为 e:
    打印 "R220|0|", 转字符串(e)
'''

_CARD_PROBE_A = '设 s 为 集合创建([1,2,2,3])\n打印 转字符串(s)\n'
_CARD_PROBE_B = '设 d 为 {"a":1}\n字典设置默认值(d, "b", 5)\n打印 转字符串(d)\n'


# =============================================================================
# 数据侧
# =============================================================================

def linter_names():
    """被门禁的对象：`src/linter/builtins.py` 给出的内置名全集。"""
    from linter.builtins import get_builtin_names

    return sorted(get_builtin_names())


@functools.lru_cache(maxsize=1)
def stdlib_only_all_names():
    """`stdlib/builtins.py::__all__` 里**没有** `builtin_map` 调用点接线的名字。

    这类名字「地板宣称导出、源码却裸调用不到」，是另一类容易误判的脱节。
    """
    path = os.path.join(_ROOT, 'stdlib', 'builtins.py')
    spec = importlib.util.spec_from_file_location('_r220_stdlib_builtins', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from code_generator import PythonCodeGenerator

    exported = set(getattr(mod, '__all__', ()) or ())
    mapped = set(PythonCodeGenerator().builtin_map)
    return tuple(sorted(exported - mapped))


# =============================================================================
# 真 CLI 探测
# =============================================================================

def _probe_source(names):
    """把每个名字写成一条独立的 `试/捕` 探针（调用放 `设 ... 为` 右侧）。"""
    lines = []
    for i, name in enumerate(names):
        lines.append('试:')
        lines.append(f'    设 __p 为 {name}({_SENTINEL})')
        lines.append('捕 错误 为 e:')
        lines.append(f'    打印 "R220|{i}|", 转字符串(e)')
    return '\n'.join(lines) + '\n'


def _no_window_kwargs():
    """Windows 上不给 console 子进程分配新控制台（T-0206 死锁修法）。

    `HIVE_NO_WINDOW=0` 保留逃生阀；非 Windows 平台返回空字典。
    """
    if os.name != 'nt' or os.environ.get('HIVE_NO_WINDOW') == '0':
        return {}
    flag = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return {'creationflags': flag} if flag else {}


def _run_cli(src, tmp_path, tag):
    """**真起** `python -m cli.light run`。临时源码写在 tmp_path，cwd 必须是仓根。"""
    path = os.path.join(str(tmp_path), tag + '.light')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(src)
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'cli.light', 'run', path],
        cwd=_ROOT, env=env, capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=240,
        **_no_window_kwargs())


def probe(names, tmp_path, tag):
    """逐名探测，返回 (CompletedProcess, {名字: 捕获到的错误文本})。"""
    names = list(names)
    cp = _run_cli(_probe_source(names), tmp_path, tag)
    got = {}
    for line in cp.stdout.splitlines():
        m = _MARK.match(line.strip())
        if m:
            i = int(m.group(1))
            if 0 <= i < len(names):
                got[names[i]] = m.group(2).strip()
    return cp, got


def _assert_fully_covered(cp, got, names):
    """覆盖完整性：CLI 真跑完 + 每个名字都有一条标记，杜绝空转假绿。"""
    assert cp.returncode == 0, (
        f'真 CLI 探针程序没跑完（rc={cp.returncode}），可能是某个名字写不成调用形式：\n'
        + cp.stderr[:2000])
    assert set(got) == set(names), (
        f'逐名标记覆盖不全，门禁在漏检：缺 {sorted(set(names) - set(got))}，'
        f'多 {sorted(set(got) - set(names))}')


# =============================================================================
# 1. 清单结构（解析失败会让后面所有用例变成空转假绿）
# =============================================================================

def test_R220_清单结构信号():
    """不写 `len(x) >= N` 弱断言：用关键名字 + 名字干净度做结构信号。"""
    names = linter_names()
    assert names, 'linter 内置名清单一个名字都没取到'
    for must in ('打印', '是空', '列表创建', '集合', '整数', '转字符串'):
        assert must in names, f'清单里应含 `{must}`（数据源可能变了）'
    for name in names:
        assert name.strip() == name and '(' not in name and '|' not in name, \
            f'名字不干净（会破坏探针/标记解析）：{name!r}'
    assert _KEYWORD_FORM_NAMES <= set(names), \
        '关键字式内置已从清单里消失？豁免集合必须跟着改，不能留空转'


# =============================================================================
# 2. 主判据：清单里每个名字，真 CLI 运行期都解析得到
# =============================================================================

def test_R220_清单每个名字真CLI运行期可达(tmp_path):
    """**主判据**：332 条探针一次真跑，逐名核对；任何不可达都点名。"""
    names = linter_names()
    writable = [n for n in names if n not in _KEYWORD_FORM_NAMES]
    cp, got = probe(writable, tmp_path, 'r220_all_names')
    _assert_fully_covered(cp, got, writable)

    bad = [(n, got[n]) for n in writable if _REACHABLE not in got[n]]
    assert not bad, (
        '清单里有名字真 CLI 运行期解析不到（linter 放行 → 用户代码运行期才炸）：\n'
        + '\n'.join(f'  - {n}：{why}' for n, why in bad))


# =============================================================================
# 3. 反跑：门禁必须「红得起来」
# =============================================================================

def test_R220_三态处置_臆造名已清且反跑必红(tmp_path):
    """态③ 复核 + 反跑：T-0213 清掉的伪名必须仍不在清单，且判据能拦住它们。"""
    from linter.builtins import _EXCLUDED_NAMES

    names = set(linter_names())
    still = sorted(n for n in _EXCLUDED_NAMES if n in names)
    assert not still, f'声明剔除却仍在清单里的名字：{still}'

    fakes = ['集合创建', '字典设置默认值', '计数', '集', '真值', '转布尔',
             '完全不存在的内置名xyz']
    cp, got = probe(fakes, tmp_path, 'r220_fakes')
    _assert_fully_covered(cp, got, fakes)
    passed = [n for n in fakes if _REACHABLE in got[n]]
    assert not passed, (
        f'这些伪名被判成「可达」了，可达闸失效：{passed}\n'
        '（`完全不存在的内置名xyz` 词法会切成 `完全不存`，错误消息不含哨兵，正合预期）')


def test_R220_探针本身有牙_阳性对照(tmp_path):
    """反跑的另一半：已知真名字必须被判可达，否则「全不可达」也会假绿。"""
    good = ['打印', '集合', '转字符串', '列表创建']
    cp, got = probe(good, tmp_path, 'r220_positive')
    _assert_fully_covered(cp, got, good)
    missed = [n for n in good if _REACHABLE not in got[n]]
    assert not missed, f'这些真名字被判成不可达，探针形态坏了：{missed}'


def test_R220_可达闸对Python内置名泄漏无牙_故必须保留LH40闸A(tmp_path):
    """钉住本门禁的**已知盲区**：`repr` / `len` 真 CLI 可达，但不是光明内置名。

    这不是 bug，是「运行时可达」这个单侧判据的边界。谁要把 LH40 闸 A 删掉，
    先看这条用例为什么红。
    """
    leaks = ['repr', 'len']
    cp, got = probe(leaks, tmp_path, 'r220_py_leaks')
    _assert_fully_covered(cp, got, leaks)
    assert all(_REACHABLE in got[n] for n in leaks), (
        '真 CLI 开始能拦住 Python 内置名泄漏了？若确实如此，本用例与 LH40 闸 A '
        '可以一起简化，但必须先改这条用例写明新证据')
    assert not (set(leaks) & set(linter_names())), \
        '泄漏名混进清单了（这正是 LH40 闸 A 该拦的）'


# =============================================================================
# 4. 关键字式内置：单列，不许变成豁免抽屉
# =============================================================================

def test_R220_关键字式名字确实写不出调用形式(tmp_path):
    """`新建` 写成 `<名字>(...)` 必须真的解析失败，不能凭印象塞进豁免集合。"""
    for name in sorted(_KEYWORD_FORM_NAMES):
        cp = _run_cli(_probe_source([name]), tmp_path, 'r220_kw_unwritable')
        assert cp.returncode != 0, (
            f'`{name}` 实测能写成 `<名字>(...)`，那就不该在 _KEYWORD_FORM_NAMES 里')


def test_R220_关键字式内置真CLI可达(tmp_path):
    """换成合法写法 `新建 类名(__哨兵__)` 后，名字必须真解析得到。"""
    cp = _run_cli(_NEW_KEYWORD_PROBE, tmp_path, 'r220_kw_reachable')
    assert cp.returncode == 0, (
        f'关键字式内置探针没跑通（rc={cp.returncode}）：\n' + cp.stderr[:2000])
    assert _REACHABLE in cp.stdout, (
        '`新建` 的关键字式探针没有报「哨兵未定义」，说明名字没解析到：\n'
        + cp.stdout[:1000])


# =============================================================================
# 5. 反向脱节：`__all__` 有、`builtin_map` 没有的名字
# =============================================================================

def test_R220_地板导出但未接线的名字不许进清单(tmp_path):
    """态① 的反向哨兵：`__all__` 独家名字真 CLI 裸调用不可达，清单不许给它们盖章。

    这些名字有真身（stdlib 顶层函数），但调用点没接线；若照着 `__all__` 把它们
    补登进清单，就会凭空造出新的「linter 放行 / 运行期 NameError」假绿。
    """
    only = list(stdlib_only_all_names())
    assert '圆周率' in only, (
        '`圆周率` 已不在「__all__ 独家」名单里：若已接线进 builtin_map，'
        '请同步更新本用例的样本与说明，别直接删掉这条结构信号')
    assert not (set(only) & set(linter_names())), (
        '这些「地板导出但未接线」的名字混进 linter 清单了：'
        f'{sorted(set(only) & set(linter_names()))}')

    cp, got = probe(only, tmp_path, 'r220_only_all')
    _assert_fully_covered(cp, got, only)
    reachable = [n for n in only if _REACHABLE in got[n]]
    assert not reachable, (
        f'这些 `__all__` 独家名字真 CLI 变得可达了：{reachable}。'
        '那说明 builtin_map 已接线，可以按正常流程补登清单，但要先改本用例')


# =============================================================================
# 6. 卡面两张探针：把「清单没撒谎」钉住，而不是把臆造名修成能跑
# =============================================================================

def test_R220_卡面两张探针的一致性定性(tmp_path):
    """`集合创建` / `字典设置默认值` 的 rc 可以变，但「清单与实现」必须一致。

    * `集合创建` 是裁定过的臆造名 ⇒ 永远不许进清单、也不该补实现；
    * `字典设置默认值` 若将来补了实现（rc=0），就**必须**同步登记进清单；
      没实现（rc=1）就**不许**登记。这样门禁不会挡住合法改进，只挡脱节。
    """
    names = set(linter_names())

    cp_a = _run_cli(_CARD_PROBE_A, tmp_path, 'r220_card_a')
    assert cp_a.returncode != 0, '`集合创建` 竟然能跑了？须复核 T-0203 的裁定'
    assert "name '集合创建' is not defined" in cp_a.stderr, \
        '探针 A 的失败原因变了：' + cp_a.stderr[:1500]
    assert '集合创建' not in names, '清单不许为裁定过的臆造名盖章'

    cp_b = _run_cli(_CARD_PROBE_B, tmp_path, 'r220_card_b')
    if cp_b.returncode == 0:
        assert '字典设置默认值' in names, (
            '`字典设置默认值` 已补实现（rc=0），却没同步登记进 linter 清单——'
            '这又变成「跑得起来但 linter 不认」的脱节')
    else:
        assert "name '字典设置默认值' is not defined" in cp_b.stderr, \
            '探针 B 的失败原因变了：' + cp_b.stderr[:1500]
        assert '字典设置默认值' not in names, (
            '`字典设置默认值` 还没实现，却在 linter 清单里——这正是卡面说的假绿')
