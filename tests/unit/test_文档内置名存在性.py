# -*- coding: utf-8 -*-
"""文档内置名存在性门禁（T-0203 · 防「文档教 AI 写不存在的名字」再犯）。

背景
----
`docs/AI编程指南.md` 是 AI 写光明代码的**唯一真源**：文档名错一个，所有照抄的代码全红。
历史事故（lighthive 侧 `LH-07` / `LH-11` / `LH-21`）都指向同一类问题——
「文档里写着的名字，源码里根本调不到」。本文件把这条约束变成**门禁**。

判据为什么是**双层**
------------------
只查登记表不行，只查运行时也不行，各有实证反例：

1. **只查运行时**会被 Python 内置名泄漏骗过——`设 x 为 len([1])` / `str(1)` /
   `sorted([2,1])` 在 src 腿**都能跑**（`repr` 同理），但它们不是光明内置名。
   ⇒ 必须再加「登记」闸。
2. **只查登记表**会被「登记表口径太宽」骗过——`builtin_names()` 约 2900 条，其中约 2591 条是
   **lightpub 模块函数**（`stdlib/lightpub/__index__.py:functions`），它们**不是地板内置名**，
   裸调用必然 `NameError`。实证两个：
   `临时目录`（真函数，须 `从 系统接口 导入`）、`转布尔`（真函数，须 `从 类型工具 导入`）——
   两者都在登记表里，但 `设 x 为 临时目录()` / `设 x 为 转布尔(空)` 直接 `NameError`。
   这是登记表为守「宁可漏报也不误报」红线而**有意放宽**的结果，不是 bug；
   但门禁若照抄这个口径，就会把「文档里写了个必须导入的名字却没说」放过去。
   ⇒ 必须再加「运行时可达」闸（并给这类名字显式声明导入方式）。

所以本门禁对文档里每个名字要求**同时**满足：
  (a) **登记**：出现在 `src/linter/light_linter.py::builtin_names()` 里，或在
      `DOC_IMPORT_NAMES` 里显式声明了「从哪个模块导入」（这类名字不是地板内置名）；
  (b) **可达**：真编译 + 真跑一段 `设 __probe 为 <名字>(空)`，**抛 NameError 即失败**
      （其它异常如 TypeError/AttributeError 都算可达——名字解析到了，只是参数不合适）。

豁免清单
--------
**当前为空**（`KNOWN_UNREACHABLE = frozenset()`）。
T-0203 已经把文档里两处伪名改掉了（`集合创建` → `集合([])`、`repr` → 换掉），
并把 `转布尔` 标成「需导入」。所以**不需要任何豁免**——
`test_known_unreachable_is_empty` 会盯着这一点，谁想偷偷加豁免先得改那条用例。

反跑（证明有牙）
---------------
`test_gate_has_teeth_*` 用**故意造假的名单**跑同一套判据，必须红。
只断「绿」不断「红会不会红」的门禁等于没装。
"""
import contextlib
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

DOC = os.path.join(_ROOT, 'docs', 'AI编程指南.md')
SECTION = '## 三、最常用内置函数'

# ── 非地板内置名：文档里注明了「要导入」的名字 → 导入语句 ─────────────────────
# 这些不是 `builtin_map` 里的地板内置名，裸调用必然 NameError，但文档已写明导入方式。
# 值 = 该名字的导入语句（本门禁会真跑它，所以「文档写的导入路径对不对」也一并钉住）。
DOC_IMPORT_NAMES = {
    '转布尔': '从 类型工具 导入 转布尔',
}

# ── 豁免清单（当前为空，见模块 docstring）────────────────────────────────────
KNOWN_UNREACHABLE = frozenset()


# =============================================================================
# 文档解析
# =============================================================================

def doc_builtin_names():
    """抽出「## 三、最常用内置函数」小节里所有表格第一列反引号内的名字（去重保序）。"""
    with open(DOC, encoding='utf-8') as f:
        lines = f.read().split('\n')
    start = next(i for i, l in enumerate(lines) if l.startswith(SECTION))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))

    names = []
    for line in lines[start:end]:
        s = line.strip()
        if not s.startswith('|') or s.startswith('|---'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if not cells:
            continue
        for cand in re.findall(r'`([^`]+)`', cells[0]):
            nm = re.sub(r'\(.*?\)$', '', cand).strip()
            if nm and nm not in names:
                names.append(nm)
    return names


# =============================================================================
# 判据实现
# =============================================================================

def _compile_and_exec(src, tag='<doc_builtin_probe>'):
    """走真实管线（LightParser → PythonCodeGenerator）编译并执行，返回 (ok, 错误描述)。

    NameError 是**唯一**的「不可达」信号；其它异常说明名字解析到了，算可达。
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    try:
        module = LightParser().parse(src)
        py = PythonCodeGenerator(stdlib_dir=os.path.join(_ROOT, 'stdlib')).generate(
            module, is_main=True)
    except Exception as e:  # noqa: BLE001 —— 编译期异常也要报出来，不能静默算通过
        return False, f'编译期异常 {type(e).__name__}: {e}'

    g = {'__name__': '__main__', '__file__': os.path.join(_ROOT, 'doc_probe.light')}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(py, tag, 'exec'), g, g)
    except NameError as e:
        return False, f'NameError: {e}'
    except Exception:  # noqa: BLE001 —— TypeError/AttributeError 等 = 名字可达
        return True, ''
    return True, ''


def reachability_failures(names):
    """对每个名字跑「登记 + 可达」双闸，返回 [(名字, 原因)]；全通过返回 []。"""
    from linter.light_linter import builtin_names

    registered = builtin_names()
    failures = []

    for name in names:
        if name in KNOWN_UNREACHABLE:
            continue
        if name in DOC_IMPORT_NAMES:
            # 文档已声明「这不是地板内置名，要导入」：只验「文档写的导入路径 + 调用」通不通，
            # 不再要求裸调用可达（那正是这类名字的定义）。
            ok, why = _compile_and_exec(DOC_IMPORT_NAMES[name] + f'\n设 __probe 为 {name}(空)\n')
            if not ok:
                failures.append((name, f'文档写的导入路径跑不通：{why}'))
            continue
        if name not in registered:
            failures.append(
                (name, '既不在 builtin_names() 登记表里，也没在 DOC_IMPORT_NAMES 声明导入方式'
                       '（Python 内置名泄漏不算数：len/str/sorted/repr 也能跑，但都不是光明内置名）'))
            continue

        # 注意：`registered` 里混着约 2591 条 lightpub 模块函数（登记表为守「宁可漏报」而放宽），
        # 所以「登记过」不等于「裸调用可达」——下面这一步才是真正的判据。
        ok, why = _compile_and_exec(f'设 __probe 为 {name}(空)\n')
        if not ok:
            failures.append((name, f'登记/文档里有，但源码里不可达：{why}'))

    return failures


# =============================================================================
# 1. 文档解析本身（解析失败会让后面所有用例变成空转假绿）
# =============================================================================

def test_doc_table_parsed():
    """必须能真从文档表里取到名字——否则整套门禁会「零名字全绿」。"""
    names = doc_builtin_names()
    assert len(names) >= 25, f'只解析到 {len(names)} 个名字，文档表结构可能变了：{names}'
    for must in ('打印', '是空', '皆空', '转字符串', '列表创建'):
        assert must in names, f'文档表里应含 `{must}`，实际没取到'


# =============================================================================
# 2. 主判据：文档里每个名字都必须「登记 + 可达」
# =============================================================================

def test_every_doc_name_registered_and_reachable():
    """**本门禁的主判据**：任何一个名字不可达 → 失败并逐个点名。"""
    names = doc_builtin_names()
    failures = reachability_failures(names)
    assert not failures, (
        '文档内置函数表里有不可达的名字（照抄这些名字的代码必红）：\n'
        + '\n'.join(f'  - {n}：{why}' for n, why in failures)
    )


def test_module_names_are_really_importable():
    """`DOC_IMPORT_NAMES` 里的名字，按文档写的导入语句必须能导入且能调用。"""
    for name, stmt in DOC_IMPORT_NAMES.items():
        ok, why = _compile_and_exec(stmt + f'\n设 __v 为 {name}(空)\n')
        assert ok, f'`{name}` 的文档导入路径 `{stmt}` 跑不通：{why}'


# =============================================================================
# 3. 防回退：本轮改掉的伪名不许再出现
# =============================================================================

@pytest.mark.parametrize('fake', ['集合创建', 'repr', '去除首尾空白'])
def test_known_fake_names_not_back_in_doc(fake):
    """`集合创建`/`repr`/`去除首尾空白` 都是**不存在**的名字，文档不许再写回去。"""
    names = doc_builtin_names()
    assert fake not in names, (
        f'`{fake}` 不是真实内置名，却被写回文档 §三 表——'
        f'`集合创建` 用 `集合([])` 代替；`repr` 用 `转字符串`；`去除首尾空白` 真名是 `去除空白`')


def test_empty_set_hint_is_actionable():
    """文档必须给出「怎么造空集合」的可执行答案（`集合创建` 删除后的替代说明）。"""
    with open(DOC, encoding='utf-8') as f:
        text = f.read()
    assert '集合([])' in text, '删掉 `集合创建` 后必须在文档里写清空集合的真实写法 `集合([])`'


# =============================================================================
# 4. 豁免清单必须为空（防「加豁免换绿」）
# =============================================================================

def test_known_unreachable_is_empty():
    """T-0203 已把文档侧的伪名清干净，**不应再需要任何豁免**。"""
    assert KNOWN_UNREACHABLE == frozenset(), (
        f'豁免清单不为空：{sorted(KNOWN_UNREACHABLE)}。'
        '要么改文档/补代码，要么在本用例里写明为什么必须豁免（并开卡跟踪）')


# =============================================================================
# 5. 反跑：门禁必须「红得起来」
# =============================================================================

def test_gate_has_teeth_unregistered_name():
    """造一个「运行时能跑但没登记」的名字（Python 内置 `len`）⇒ 必须被登记闸拦住。"""
    failures = reachability_failures(['len'])
    assert failures, '`len` 没在登记表里，登记闸却放过了它——门禁失效'
    assert failures[0][0] == 'len'
    assert '登记表' in failures[0][1]


def test_gate_has_teeth_module_function_name():
    """造一个「登记表里有、但裸调用不可达」的名字（lightpub 模块函数样本）⇒ 可达闸必须拦住。

    样本选 `临时目录`：它是**真实函数**（`stdlib/系统接口.py`，须 `从 系统接口 导入`），
    只因登记表把 lightpub 模块函数也收进来了，才会在「裸调用」这一层漏掉。
    这条用例钉的是「门禁不能照抄登记表口径」。
    """
    from linter.light_linter import builtin_names

    if '临时目录' not in builtin_names():
        pytest.skip('`临时目录` 已不在登记表里（口径变了），换样本再验反跑')
    failures = reachability_failures(['临时目录'])
    assert failures, '`临时目录` 登记了但裸调用不可达，可达闸却放过了它——门禁失效'
    assert '不可达' in failures[0][1]


def test_gate_has_teeth_nonexistent_name():
    """造一个根本不存在的名字 ⇒ 两个闸都该拦。"""
    failures = reachability_failures(['完全不存在的内置名xyz'])
    assert failures, '不存在的名字被放过了——门禁失效'


# =============================================================================
# 6. 顺带守住 T-0203 在 `src/compiler_cache.py` 落地的 NO_CACHE 逃生口
# =============================================================================

def test_no_cache_switch_reads_env(monkeypatch):
    """`NO_CACHE=1` / `LIGHT_NO_CACHE=1` 都要能让 `缓存已禁用()` 为真（LH-13 排查用）。"""
    from compiler_cache import 缓存已禁用

    monkeypatch.delenv('NO_CACHE', raising=False)
    monkeypatch.delenv('LIGHT_NO_CACHE', raising=False)
    assert 缓存已禁用() is False

    for name in ('NO_CACHE', 'LIGHT_NO_CACHE'):
        monkeypatch.delenv('NO_CACHE', raising=False)
        monkeypatch.delenv('LIGHT_NO_CACHE', raising=False)
        monkeypatch.setenv(name, '1')
        assert 缓存已禁用() is True, f'{name}=1 应停用缓存'

    monkeypatch.setenv('NO_CACHE', '0')
    monkeypatch.delenv('LIGHT_NO_CACHE', raising=False)
    assert 缓存已禁用() is False, '`NO_CACHE=0` 不应停用缓存'


def test_no_cache_switch_actually_bypasses_cache(tmp_path, monkeypatch):
    """开关要**真生效**：开了 NO_CACHE，`get_cached` 必须读不到刚写进去的缓存。"""
    from compiler_cache import CompilationCache

    src = tmp_path / 'a.light'
    src.write_text('打印(1)\n', encoding='utf-8')

    cache = CompilationCache(cache_dir=str(tmp_path / 'cache'))
    cache.set_cached(str(src), 'IR-结果')
    assert cache.get_cached(str(src)) == 'IR-结果', '基线：未开开关时应能命中缓存'

    monkeypatch.setenv('NO_CACHE', '1')
    cache2 = CompilationCache(cache_dir=str(tmp_path / 'cache'))
    cache2.set_cached(str(src), 'IR-结果2')
    assert cache2.get_cached(str(src)) is None, '开了 NO_CACHE 还能命中缓存 → 开关是假的'
