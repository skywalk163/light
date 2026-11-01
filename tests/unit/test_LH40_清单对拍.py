# -*- coding: utf-8 -*-
"""linter 内置名清单 ↔ 运行期真身对拍门禁（T-0213 · L-261）。

背景
----
`src/linter/builtins.py` 是「什么是光明内置名」的共享数据源，但它和
`stdlib/builtins.py` 的真身**从来没有对拍过**。于是 `集合创建`、`计数`、`连接`
这类「登记了、运行期却是 NameError」的名字在清单里长期存活：

    设 s 为 集合创建([1,2,2,3])     ⇒ name '集合创建' is not defined
    设 x 为 集()                    ⇒ name '集' is not defined
    设 y 为 真值                    ⇒ name '真值' is not defined

`tests/unit/test_文档内置名存在性.py` 只查**文档里出现的名字**，清单这一侧是裸奔的；
本文件补的就是这一侧。与 LH-21（= L-251）同源的假绿：linter 因为「它是内置」而放行，
错误一路留到运行期深处才炸，而且炸在离书写点很远的地方。

判据为什么是**双闸**
------------------
与文档门禁同款，且两侧各有一个实证漏网口：

1. **只查可达**会被 Python 内置名泄漏骗过——`repr` 在生成模块的命名空间里**真能解析到**
   （它只是 Python 内置名，不是光明内置名），只查可达它一路绿。T-0203 已裁定
   `repr` 是伪名（真名 `转字符串`），所以必须再加「登记」闸。
2. **只查登记**会被「登记表本身骗人」骗过——`builtin_map` 里确实有
   `FFI调试` / `XML生成`，但词法先把名字尾部的保留关键字切开，用户写出来的
   根本不是这个名字（`打印(FFI调试(1))` → `NameError: name 'FFI' is not defined`）。
   所以必须再加「可达」闸。

⇒ 清单里每个名字都要**同时**满足：
  (a) **登记**：来自权威注册表——`code_generator.builtin_map` /
      `keywords.BUILTIN_TYPES` / `stdlib/builtins.py::__all__` / 值字面量；
  (b) **可达**：走真实管线（`LightParser` → `PythonCodeGenerator`）生成 Python，
      在**真命名空间**里解析该名字，NameError / AttributeError 即失败。

判据怎么做到「真跑」又不炸
--------------------------
不能像文档门禁那样 `exec` 整段探针程序：`设 __probe 为 退出程序(空)` 会真的
`sys.exit`，`输入(空)` 会阻塞 stdin。所以本门禁分两步：

  1. **一次编译**：把全部名字写成一个程序的 331 条 `设 __probe_<i> 为 <名字>(空)`，
     走真实管线编译（preamble 因此带上 stdlib / asyncio / FFI 的真实导入）；
  2. **只 exec preamble**，然后逐条把探针赋值语句右侧的 Python 表达式取出来，
     **剥掉调用**（`ast` 里把 `Call` 换成它的 `func`）后 `eval`——
     名字/属性解析照跑，副作用一点不触发。

`设 __probe 为 <名字>(空)` 这个探针形式不是随便挑的：裸引用（`设 x 为 名字`）对
类型名与动词式调用是**假阴性**（`集合` 裸引用报 NameError，`集合(空)` 才映射到 `set`），
而文档门禁用的正是调用形式。

反跑（证明有牙）
---------------
`test_闸*_反跑_*` 用**故意造假的名单**跑同一套判据，必须红；另有
`test_闸B_对Python内置名泄漏无牙_故必须有闸A` 专门钉住闸 B 的已知盲区，
防止后人「觉得闸 A 多余」把它删掉。
"""
import ast
import contextlib
import functools
import importlib.util
import io
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'stdlib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 关键字式内置：只能写成 `新建 类名()`，写成 `新建(空)` 解析器会判「期望类名」──
# 它们的可达性改用「调用点重定向表里的 Python 表达式」判定（见对应用例）。
# 集合必须**精确**等于实测不可写的名字，多一个少一个都要红——防止后人拿它当豁免抽屉。
_KEYWORD_FORM_NAMES = frozenset({'新建'})

# ── 值字面量（不走 builtin_map，由 codegen 直接落成 True/False/None）──────────
_LITERAL_NAMES = frozenset({'真', '假', '空', 'True', 'False', 'None'})

_PROBE_LINE = re.compile(r'^__probe_(\d+) = (.+)$')


# =============================================================================
# 清单侧
# =============================================================================

def list_names():
    """`src/linter/builtins.py` 给出的内置名全集（被门禁的对象）。"""
    from linter.builtins import get_builtin_names

    return get_builtin_names()


def excluded_names():
    """`src/linter/builtins.py` 显式剔除的名字 → 理由（T-0213 的清理账目）。"""
    from linter.builtins import _EXCLUDED_NAMES

    return dict(_EXCLUDED_NAMES)


# =============================================================================
# 闸 A · 登记：权威注册表
# =============================================================================

@functools.lru_cache(maxsize=1)
def _load_stdlib_builtins_module():
    """按路径加载 `stdlib/builtins.py`（不走 `import builtins`，避免撞 Python 内置模块）。"""
    path = os.path.join(_ROOT, 'stdlib', 'builtins.py')
    spec = importlib.util.spec_from_file_location('_lh40_stdlib_builtins', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def authoritative_names():
    """权威注册表：调用点重定向表 ∪ 内置类型 ∪ 运行时导出 ∪ 值字面量。"""
    from code_generator import PythonCodeGenerator
    from keywords import BUILTIN_TYPES

    names = set(PythonCodeGenerator().builtin_map)
    names |= set(BUILTIN_TYPES)
    names |= set(getattr(_load_stdlib_builtins_module(), '__all__', ()))
    names |= set(_LITERAL_NAMES)
    return names


def registry_failures(names):
    """闸 A：返回 [(名字, 原因)]；全通过返回 []。"""
    auth = authoritative_names()
    return [
        (n, '不在权威注册表里（builtin_map / BUILTIN_TYPES / stdlib/builtins.py::__all__ / 字面量）')
        for n in names
        if n not in auth
    ]


# =============================================================================
# 闸 B · 可达：真实管线 + 真命名空间
# =============================================================================

class _StripCall(ast.NodeTransformer):
    """把 `Call` 换成它的 `func`：保留名字/属性解析，绝不真的调用。"""

    def visit_Call(self, node):
        self.generic_visit(node)
        return node.func


def _resolves(expr, namespace):
    """在真命名空间里解析一个 Python 表达式（不求值副作用）。"""
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:  # 生成器表达式以外的语法问题，直接算失败
        return False, f'生成的 Python 表达式无法解析（{expr!r}）：SyntaxError: {e}'
    tree = ast.fix_missing_locations(_StripCall().visit(tree))
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            eval(compile(tree, '<lh40_probe>', 'eval'), namespace)
    except NameError as e:
        return False, f'NameError: {e}'
    except AttributeError as e:
        return False, f'AttributeError: {e}'
    except Exception as e:  # noqa: BLE001 —— 解析期任何异常都说明这个名字不可用
        return False, f'{type(e).__name__}: {e}'
    return True, ''


@functools.lru_cache(maxsize=8)
def _probe(names_key):
    """编译一次探针程序并 exec 它的 preamble，返回 (命名空间, {名字: 生成表达式})。

    `names_key` 是排好序的元组（lru_cache 要可哈希）。**一次编译**是刻意的：
    逐名编译 331 次要 ~26s，批量一次 ~0.5s。
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    names = list(names_key)
    src = '\n'.join(f'设 __probe_{i} 为 {n}(空)' for i, n in enumerate(names)) + '\n'
    py = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
        LightParser().parse(src), is_main=True)

    lines = py.split('\n')
    first = next((i for i, l in enumerate(lines) if _PROBE_LINE.match(l)), None)
    assert first is not None, '生成的 Python 里找不到任何 __probe_<i> 赋值行，探针形式变了'

    namespace = {'__name__': '__main__', '__file__': os.path.join(_ROOT, 'lh40_probe.light')}
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        exec(compile('\n'.join(lines[:first]), '<lh40_preamble>', 'exec'), namespace, namespace)

    exprs = {}
    for line in lines[first:]:
        m = _PROBE_LINE.match(line)
        if m:
            exprs[names[int(m.group(1))]] = m.group(2).strip()
    return namespace, exprs


def reachability_report(names):
    """闸 B：返回 (失败列表, 写不出调用形式的名字, 真正探测到的名字集合)。"""
    names = sorted(set(names))

    writable, unparseable = [], []
    from light_parser_v3 import LightParser

    for n in names:
        try:
            LightParser().parse(f'设 __probe 为 {n}(空)\n')
            writable.append(n)
        except Exception:  # noqa: BLE001 —— 解析失败 = 这个名字写不成调用形式
            unparseable.append(n)

    if not writable:
        return [], unparseable, set()

    namespace, exprs = _probe(tuple(writable))
    failures, covered = [], set()
    for n in writable:
        expr = exprs.get(n)
        if expr is None:
            # 生成了探针语句但取不到右侧表达式：说明生成结果不是单行赋值（形态变了）。
            failures.append((n, '探针语句没有生成成单行赋值，无法判定（生成形态可能变了）'))
            continue
        covered.add(n)
        ok, why = _resolves(expr, namespace)
        if not ok:
            failures.append((n, f'清单里有，但运行期解析不到（生成 {expr!r}）：{why}'))
    return failures, unparseable, covered


def reachability_failures(names):
    """闸 B 的简版：只关心失败项（写不出调用形式的名字也计为失败）。"""
    failures, unparseable, _ = reachability_report(names)
    for n in unparseable:
        failures.append((n, '源码里写不成 `<名字>(...)` 形式（解析器直接报错）'))
    return failures


# =============================================================================
# 1. 清单结构（解析失败会让后面所有用例变成空转假绿）
# =============================================================================

def test_清单非空且含关键名字():
    """清单必须真取到名字——否则整套门禁会「零名字全绿」。

    判据不写下界（`len(x) >= N` 是弱断言）：改为**结构信号**——关键名字必须在，
    且不带空白/括号残留。
    """
    names = list_names()
    assert names, 'linter 内置名清单一个名字都没取到'
    for must in ('打印', '是空', '列表创建', '集合', '整数'):
        assert must in names, f'清单里应含 `{must}`，实际没有（数据源可能变了）'
    for nm in names:
        assert nm.strip() == nm and '(' not in nm, f'名字不干净：{nm!r}'


def test_来源映射与名字集合一一对应():
    """`get_builtin_sources()` 必须覆盖每一个名字（否则 summary / tools 会漏来源）。"""
    from linter.builtins import get_builtin_sources

    names = list_names()
    sources = get_builtin_sources()
    assert set(sources) == set(names), (
        f'来源映射与名字集合不一致：只在名字里 {sorted(set(names) - set(sources))}，'
        f'只在来源里 {sorted(set(sources) - set(names))}')


# =============================================================================
# 2. 闸 A · 登记
# =============================================================================

def test_闸A_权威注册表本身有货():
    """防「注册表加载失败 → 空集合 → 闸 A 全绿」的空转假绿。"""
    auth = authoritative_names()
    from code_generator import PythonCodeGenerator

    assert len(PythonCodeGenerator().builtin_map) > 200, 'builtin_map 规模异常（加载可能失败）'
    assert len(getattr(_load_stdlib_builtins_module(), '__all__', ())) > 80, \
        'stdlib/builtins.py::__all__ 规模异常'
    assert {'打印', '是空', '集合'} <= auth, f'权威注册表缺关键名字：{auth & {"打印", "是空", "集合"}}'


def test_闸A_清单是权威注册表的子集():
    """**闸 A 主判据**：清单里每个名字都得在权威注册表里登记过。"""
    failures = registry_failures(sorted(list_names()))
    assert not failures, (
        '清单里有名字不在权威注册表里（`repr` 这类「能跑但只是 Python 内置名泄漏」的伪名就这样混进来）：\n'
        + '\n'.join(f'  - {n}：{why}' for n, why in failures))


def test_闸A_反跑_repr必须被拦住():
    """反跑：`repr` 能跑（Python 内置名泄漏），但**不是**光明内置名 ⇒ 闸 A 必须红。"""
    failures = registry_failures(['repr'])
    assert failures, '`repr` 不在权威注册表里，闸 A 却放过了它——闸 A 失效'


# live 表的口径更宽（约 2900 条，把 lightpub 模块函数也收了进来，见
# test_文档内置名存在性.py 的说明），所以这里只能单向包含。
_PY_LITERAL_SPELLINGS = frozenset({'True', 'False', 'None'})


def test_清单是live判定表的子集():
    """清单里的名字，`light_linter` 的判定表必须也认——否则本文件在替 linter 说谎。

    这条是「对拍」的另一半：闸 A/B 比的是**真身**，这里比的是**linter 自己的口径**。
    两者都过，清单才既「跑得起来」又「和 linter 不打架」。
    """
    from linter.light_linter import builtin_names

    live = builtin_names()
    extra = sorted(set(list_names()) - set(live) - _PY_LITERAL_SPELLINGS)
    assert not extra, (
        f'这些名字在 linter 清单里、却不在 light_linter 的判定表里（口径脱节）：{extra}\n'
        f'（`True`/`False`/`None` 是豁免项：它们只是字面量在生成 Python 里的拼法）')


# =============================================================================
# 3. 闸 B · 可达
# =============================================================================

def test_闸B_每个名字运行期都解析得到():
    """**闸 B 主判据**：清单里每个名字，在真命名空间里都必须解析得到。"""
    names = sorted(list_names())
    failures, unparseable, covered = reachability_report(names)

    assert not failures, (
        '清单里有运行期解析不到的名字（照抄这些名字的代码必红）：\n'
        + '\n'.join(f'  - {n}：{why}' for n, why in failures))
    assert set(unparseable) == _KEYWORD_FORM_NAMES, (
        f'写不成调用形式的名字变了：{sorted(unparseable)}。'
        f'若确属关键字式内置（如 `新建 类名()`），显式登记进 _KEYWORD_FORM_NAMES 并说明；'
        f'若是伪名，从清单里摘掉')
    assert covered == set(names) - _KEYWORD_FORM_NAMES, (
        f'有名字没被探针覆盖：{sorted(set(names) - _KEYWORD_FORM_NAMES - covered)}'
        '（覆盖不全 = 门禁在漏检）')


def test_闸B_关键字式内置按映射表达式判可达():
    """`新建` 只能写成 `新建 类名()`，可达性改判它的调用点映射表达式。"""
    from code_generator import PythonCodeGenerator

    bm = PythonCodeGenerator().builtin_map
    namespace, _ = _probe(('打印',))
    for name in sorted(_KEYWORD_FORM_NAMES):
        expr = bm.get(name, name)
        ok, why = _resolves(expr, namespace)
        assert ok, f'关键字式内置 `{name}` 的映射表达式 {expr!r} 在运行期解析不到：{why}'


def test_闸B_反跑_伪名必须红():
    """反跑：T-0213 清掉的伪名，用同一套判据必须红得起来。"""
    fakes = ['集合创建', '计数', '连接', '集', '真值']
    failures = reachability_failures(fakes)
    assert {n for n, _ in failures} == set(fakes), (
        f'这些伪名应当全部被拦住，实际只拦住 {sorted(n for n, _ in failures)}')


def test_闸B_反跑_根本不存在的名字必须红():
    """反跑：造一个瞎编的名字，必须红。"""
    failures = reachability_failures(['完全不存在的内置名xyz'])
    assert failures, '不存在的名字被放过了——闸 B 失效'


def test_闸B_对Python内置名泄漏无牙_故必须有闸A():
    """钉住闸 B 的**已知盲区**：`repr` / `len` 在真命名空间里解析得到（Python 内置名）。

    这不是闸 B 的 bug，是「运行时可达」这个判据的边界。所以闸 A（登记）不可删——
    谁要删闸 A，先看这条用例为什么红。
    """
    assert reachability_failures(['repr', 'len']) == [], (
        '闸 B 开始能拦住 Python 内置名泄漏了？若确实如此，本用例与闸 A 可以一起简化，'
        '但必须先改这条用例写明新证据')


# =============================================================================
# 4. 剔除账目（T-0213）：不许静默删名
# =============================================================================

def test_剔除名单里的名字真的都不在清单里():
    """`_EXCLUDED_NAMES` 的每个名字都必须真的从清单里消失（防「声明剔除、实际没剔」）。"""
    names = list_names()
    still = sorted(n for n in excluded_names() if n in names)
    assert not still, f'这些名字声明剔除却仍在清单里：{still}'


def test_剔除名单覆盖T0213清掉的全部伪名():
    """卡面要求：清理掉的名字必须逐条记账，不许静默删名。"""
    expected = {
        # 手工兜底清单里的伪名
        '集合创建', '计数', '连接', '转布尔', 'repr',
        # 字面量位登记的伪名
        '真值', '假值',
        # BUILTIN_TYPES 里没有运行期映射的缩写别名
        '集', '典', '数', '浮数', '小数',
        # 词法把名字尾部的保留关键字切开，用户写不出来
        'FFI调试', 'XML生成',
    }
    assert set(excluded_names()) == expected, (
        f'剔除账目变了。多出：{sorted(set(excluded_names()) - expected)}；'
        f'缺失：{sorted(expected - set(excluded_names()))}')


def test_剔除名单每条都有非空理由():
    """每个剔除项都要写明理由（summary / 复查都要能引用）。"""
    for name, why in excluded_names().items():
        assert isinstance(why, str) and why.strip(), f'`{name}` 的剔除理由为空'


def test_词法切关键字的名字确实写不出来():
    """`_UNSPELLABLE_NAMES` 必须**实测**写不出来，不能凭印象塞进去。

    判据：写成 `<名字>(空)` 要么解析失败，要么生成出来的表达式**已经不是这个名字**
    （`XML生成` 就属于后者：生成 `XML(None)`）。
    """
    from linter.builtins import _UNSPELLABLE_NAMES
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    gen = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib'))
    for name in sorted(_UNSPELLABLE_NAMES):
        try:
            py = gen.generate(LightParser().parse(f'设 __probe_0 为 {name}(空)\n'), is_main=True)
        except Exception:  # noqa: BLE001 —— 解析就失败，属于「写不出来」
            continue
        rhs = [m.group(1).strip() for m in
               (_PROBE_LINE.match(l) for l in py.split('\n')) if m]
        assert rhs, f'`{name}` 的探针没生成赋值语句，无法判定'
        head = rhs[0].split('(')[0].strip()
        assert head != name, (
            f'`{name}` 实测**能**正常写出（生成 {rhs[0]!r}），不该在 _UNSPELLABLE_NAMES 里')


def test_清单里没有不可写名字():
    """清单与「写不出来」集合必须互斥。"""
    from linter.builtins import _UNSPELLABLE_NAMES

    assert not (set(list_names()) & set(_UNSPELLABLE_NAMES)), (
        f'清单里混进了写不出来的名字：{sorted(set(list_names()) & set(_UNSPELLABLE_NAMES))}')


def test_类型别名剔除只删没有映射的那几个():
    """防「顺手把有映射的类型名一起删了」：有真映射的别名必须留着。"""
    from linter.builtins import _UNRESOLVABLE_ALIASES
    from code_generator import PythonCodeGenerator

    bm = PythonCodeGenerator().builtin_map
    for keep in ('集合', '字典', '整数', '列表', '文本', '布尔', '任意', '串', '列'):
        assert keep in list_names(), f'`{keep}` 有运行期映射，不该从清单里消失'
    for gone in _UNRESOLVABLE_ALIASES:
        assert gone not in bm, f'`{gone}` 现在有映射了？那就不该再剔除'


# =============================================================================
# 5. 防回退：文档门禁已裁定的伪名不许回流到清单
# =============================================================================

@pytest.mark.parametrize('fake', ['集合创建', 'repr', '真值', '假值'])
def test_文档侧已裁定的伪名不在清单里(fake):
    """T-0203（文档门禁）裁定过的伪名，不许在本清单里复活。"""
    assert fake not in list_names(), f'`{fake}` 是伪名，不许回到 linter 清单里'
