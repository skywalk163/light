# -*- coding: utf-8 -*-
"""R115-A：原生（LLVM）后端 `匹配 …` / `设 [甲, 乙] 为 …` 两条语句。

背景：R114 建的能力矩阵（`docs/llvm_backend_capability_matrix.md`）把缺口分了层，
其中 `MatchStmt` / `WithStmt` / `DestructuringAssignment` 三条都是 **L1 适配层
转换器有、L2 语句流白名单有、只差 L3 codegen 分派**。本轮按性价比排序补，
本文件是它们的判据。

三条的处置并不一样，别混为一谈：
  * `MatchStatement` —— **已支持**，但只到「字面量模式 + `情况 _：` 通配」。
    变量绑定 / 守卫 / 序列 / 结构 / 类型模式**明确拒绝**（`_reject_unsupported_stmt`），
    绝不静默降级成「不比较直接命中」——那是最坏的假绿。
  * `DestructuringAssignment` —— **已支持**，按位置解包；元素个数不匹配**抛运行时
    异常**，绝不静默少赋几个变量（Python 解包会抛 ValueError，同口径）。
  * `WithStatement` —— **R116-A 已转正**（见本文件 `test_能力矩阵把两条语句记成已支持`
    与 `test_能力边界文档登记了两条语句`）。此前（R115-A 阶段）因 runtime 缺上下文
    管理协议而暂缓；R116-A 改走既有 `dv_call_method` 发中文 dunder `__进入__`/`__退出__`，
    无需新增 runtime 符号即落地。`_拒绝用例` 里的 `使用_上下文管理` 一项已随晋级移除。

关于默认分支的一个实测事实（写在这里防后人踩）：
  光明的默认分支写法是 **`情况 _：`**，**不是 `其它：`**——`其它：` 在解析器层
  就报「无法识别的语法元素：'：'」。任务书里写的「`其它` 默认分支」与实现不符，
  以实测为准。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CODEGEN_TYPED = os.path.join(_ROOT, 'src', 'llvm', 'codegen_typed.py')
_COMPILER_PY = os.path.join(_ROOT, 'src', 'compiler.py')


# ----------------------------------------------------------------------
# 一、IR 级：编得出、不残留伪装
# ----------------------------------------------------------------------

_编译用例 = [
    ('匹配_命中第二支',
     '设 等级 为 2。\n'
     '匹配 等级：\n'
     '  情况 1：\n'
     '    打印 "低"。\n'
     '  情况 2：\n'
     '    打印 "中"。\n'
     '  情况 _：\n'
     '    打印 "其它"。\n'
     '结束。\n'),
    ('匹配_字符串模式',
     '设 颜色 为 "红"。\n'
     '匹配 颜色：\n'
     '  情况 "红"：\n'
     '    打印 "停止"。\n'
     '  情况 "绿"：\n'
     '    打印 "通行"。\n'
     '  情况 _：\n'
     '    打印 "注意"。\n'
     '结束。\n'),
    ('匹配_布尔模式',
     '设 甲 为 真。\n'
     '匹配 甲：\n'
     '  情况 真：\n'
     '    打印 "T"。\n'
     '  情况 假：\n'
     '    打印 "F"。\n'
     '结束。\n'),
    ('匹配_段落内返回',
     '段落 分(n)：\n'
     '  匹配 n：\n'
     '    情况 1：\n'
     '      返回 "一"。\n'
     '    情况 _：\n'
     '      返回 "多"。\n'
     '  结束。\n'
     '打印 分(1)。\n'),
    ('匹配_分支体内声明变量',
     '设 等级 为 2。\n'
     '匹配 等级：\n'
     '  情况 2：\n'
     '    设 结果 为 "中"。\n'
     '    打印 结果。\n'
     '  情况 _：\n'
     '    打印 "其它"。\n'
     '结束。\n'),
    ('解构_列表括号式',
     '设 [甲, 乙] 为 [1, 2]。\n打印 甲。\n打印 乙。\n'),
    ('解构_裸多目标',
     '设 甲, 乙 为 [3, 4]。\n打印 甲。\n打印 乙。\n'),
    ('解构_段落内',
     '段落 主()：\n'
     '  设 [甲, 乙] 为 [7, 8]。\n'
     '  打印 甲。\n'
     '  打印 乙。\n'
     '主()。\n'),
    ('解构_三目标',
     '设 [甲, 乙, 丙] 为 [1, 2, 3]。\n打印 丙。\n'),
]


@pytest.mark.parametrize('名称, 源码', _编译用例, ids=[c[0] for c in _编译用例])
def test_两条语句编得出且不残留伪装(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'


def test_匹配_字面量模式的值没在适配层丢():
    """R115-A 根因护栏：v3 的字面量模式把值存在 `value` 字段的**原生标量**上。

    适配层原实现只把 str 包成 StringLiteral，int/float/bool 一律走 `self.convert`
    ——原生标量不是 AST 节点，convert 只能产出 `<unknown:int>`，**模式的字面值
    在适配层就被丢掉了**，`情况 1：` 与 `情况 2：` 变得无法区分。这里钉住
    「每个字面量模式都必须带着自己的真值」。
    """
    sys.path.insert(0, os.path.join(_ROOT, 'src'))
    from light_parser_v3 import LightParser
    from compiler import AstAdapter
    源码 = ('设 等级 为 2。\n'
            '匹配 等级：\n'
            '  情况 1：\n'
            '    打印 "a"。\n'
            '  情况 2：\n'
            '    打印 "b"。\n'
            '  情况 "红"：\n'
            '    打印 "c"。\n'
            '结束。\n')
    mod = AstAdapter().convert_module(LightParser().parse(源码))
    stmt = mod.statements[1]
    值表 = [(c.pattern.kind, getattr(c.pattern.value, 'value', None))
            for c in stmt.cases]
    assert 值表[0] == ('number', 1), f'第一个模式的真值丢了：{值表[0]}'
    assert 值表[1] == ('number', 2), f'第二个模式的真值丢了：{值表[1]}'
    assert 值表[2] == ('string', '红'), f'字符串模式的真值丢了：{值表[2]}'


# ----------------------------------------------------------------------
# 二、拒绝用例：不许静默降级
# ----------------------------------------------------------------------

_拒绝用例 = [
    ('匹配_变量绑定模式',
     '设 甲 为 2。\n'
     '匹配 甲：\n'
     '  情况 乙：\n'
     '    打印 乙。\n'
     '结束。\n',
     'pattern=variable'),
    ('匹配_守卫条件',
     '设 甲 为 2。\n'
     '匹配 甲：\n'
     '  情况 _ 如果 甲 大于 1：\n'
     '    打印 "x"。\n'
     '结束。\n',
     'guard'),
    ('匹配_列表模式',
     '设 甲 为 [1, 2]。\n'
     '匹配 甲：\n'
     '  情况 [乙, 丙]：\n'
     '    打印 乙。\n'
     '结束。\n',
     'pattern=list'),
    ('匹配_类型检查模式',
     '设 甲 为 2。\n'
     '匹配 甲：\n'
     '  情况 整数：\n'
     '    打印 "int"。\n'
     '结束。\n',
     'MatchStmt'),
]


@pytest.mark.parametrize('名称, 源码, 类型名', _拒绝用例,
                         ids=[c[0] for c in _拒绝用例])
def test_不支持的形态必须抛错且文案指名(名称, 源码, 类型名):
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(源码)
    文案 = str(ei.value)
    assert 类型名 in 文案, f'{名称}：文案没点明不支持的形态（{类型名}），实际是：{文案}'
    assert '转译后端' in 文案, f'{名称}：文案没给出可走的后端，实际是：{文案}'


def test_使用_缺口定性_运行时没有上下文管理协议():
    """把「`使用` 为什么不做」钉成可执行事实，而不是一句口头结论。

    `src/llvm/runtime_typed.c` 里没有 `__进入__`/`__退出__`（或 dv_enter/dv_exit）
    任何对应物——runtime 里唯一叫 `dv_exit` 的是**进程退出**（`dv_exit(int code)`），
    跟上下文管理毫无关系。这个断言在 runtime 补齐协议后会自然变红，
    提醒持锁人：那时本条可以转正。
    """
    with open(os.path.join(_ROOT, 'src', 'llvm', 'runtime_typed.c'),
              encoding='utf-8') as f:
        rt = f.read()
    for 符号 in ('__enter__', '__exit__', 'dv_enter', 'dv_context_enter'):
        assert 符号 not in rt, (
            f'runtime_typed.c 里出现了 {符号}：上下文管理协议疑似已具备，'
            f'请重估 WithStatement 缺口并转正本用例')
    assert 'dv_exit' in rt, 'dv_exit 不见了（它是进程退出，不是上下文退出）'


def _源码片段(path, name, 长度=4000):
    with open(path, encoding='utf-8') as f:
        src = f.read()
    i = src.find(f'def {name}(')
    assert i > 0, f'找不到 {name}'
    return src[i:i + 长度]


def test_分派链登记了两条新语句():
    """静态护栏：L3 分派链必须有这两个 legacy 节点的分支。"""
    body = _源码片段(_CODEGEN_TYPED, '_gen_statement')
    for 节点 in ('MatchStatement', 'DestructuringAssignment'):
        assert f'isinstance(stmt, ast.{节点})' in body, \
            f'_gen_statement 里没有 ast.{节点} 的分支'


def test_变量预收集覆盖了两条新语句():
    """R10-11b / R114 踩过两次的同一个坑：局部变量只在 entry 块按
    `_collect_vars_from_stmts` 的结果批量 alloca。解构目标与 `匹配` 分支体里的
    变量若不被收集，只能落到 `alloca_local` 那永不 flush 的 `_pending_allocas`，
    产生未定义值 `%N`。
    """
    body = _源码片段(_CODEGEN_TYPED, '_collect_vars_from_stmts', 3500)
    assert 'ast.DestructuringAssignment' in body, \
        '_collect_vars_from_stmts 没收集解构目标'
    assert 'ast.MatchStatement' in body, \
        '_collect_vars_from_stmts 没递归匹配分支体'


# ----------------------------------------------------------------------
# 三、真跑：语义必须跟转译腿一致（clang 编译 + 执行）
# ----------------------------------------------------------------------

def _find_msvc_env():
    if os.name != 'nt':
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"
    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(vs_base, year, edition, "VC", "Tools", "MSVC")
                if not os.path.isdir(inc_root):
                    continue
                for ver in sorted(os.listdir(inc_root), reverse=True):
                    cand_inc = os.path.join(inc_root, ver, "include")
                    cand_lib = os.path.join(inc_root, ver, "lib", "x64")
                    if os.path.isdir(cand_inc) and os.path.isdir(cand_lib):
                        msvc_inc, msvc_lib = cand_inc, cand_lib
                        break
                if msvc_inc:
                    break
            if msvc_inc:
                break
    sdk_inc = sdk_lib = None
    if os.path.isdir(kits_base):
        inc_root = os.path.join(kits_base, "Include")
        if os.path.isdir(inc_root):
            for ver in sorted(os.listdir(inc_root), reverse=True):
                parts = [os.path.join(inc_root, ver, x) for x in ("ucrt", "shared", "um")]
                if all(os.path.isdir(p) for p in parts):
                    sdk_inc = parts
                    sdk_lib = [os.path.join(kits_base, "Lib", ver, x, "x64")
                               for x in ("ucrt", "um")]
                    break
    include = ";".join([msvc_inc] + sdk_inc) if (msvc_inc and sdk_inc) else None
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_lib and sdk_lib) else None
    return include, lib


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


def _真跑(源码):
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r115a_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        from llvm.compiler import compile_light_typed
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=300, env=env)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    # Windows 控制台会把 \n 变成 \r\n，统一掉再比
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').strip()


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_匹配_真跑_命中分支与默认分支必须不同():
    """对照组：同一段源码只改 subject，命中分支 vs 走 `情况 _：` 输出必须不同。

    只测「命中某支输出正确」是假绿——把比较全部短路成「总是走第一支」也能过。
    """
    模板 = ('设 等级 为 {}。\n'
            '匹配 等级：\n'
            '  情况 1：\n'
            '    打印 "低"。\n'
            '  情况 2：\n'
            '    打印 "中"。\n'
            '  情况 _：\n'
            '    打印 "其它"。\n'
            '结束。\n')
    assert _真跑(模板.format(1)) == '低', '没命中第 1 支'
    assert _真跑(模板.format(2)) == '中', '没命中第 2 支'
    assert _真跑(模板.format(9)) == '其它', '没走默认分支'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_匹配_真跑_字符串模式与段落内返回():
    assert _真跑('设 颜色 为 "绿"。\n'
                 '匹配 颜色：\n'
                 '  情况 "红"：\n'
                 '    打印 "停止"。\n'
                 '  情况 "绿"：\n'
                 '    打印 "通行"。\n'
                 '  情况 _：\n'
                 '    打印 "注意"。\n'
                 '结束。\n') == '通行'
    assert _真跑('段落 分(n)：\n'
                 '  匹配 n：\n'
                 '    情况 1：\n'
                 '      返回 "一"。\n'
                 '    情况 _：\n'
                 '      返回 "多"。\n'
                 '  结束。\n'
                 '打印 分(1)。\n打印 分(9)。\n') == '一\n多'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_解构_真跑_按位置赋值():
    """对照组：交换列表元素顺序，两个目标的值必须跟着换——盯「按位置」不是「按值」。"""
    assert _真跑('设 [甲, 乙] 为 [11, 22]。\n打印 甲。\n打印 乙。\n') == '11\n22'
    assert _真跑('设 [甲, 乙] 为 [22, 11]。\n打印 甲。\n打印 乙。\n') == '22\n11'
    assert _真跑('设 甲, 乙 为 [33, 44]。\n打印 甲。\n打印 乙。\n') == '33\n44'


@pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑')
@pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                    reason='未定位到 MSVC/Windows SDK 头，跳过')
def test_解构_真跑_个数不匹配必须报错不许静默少赋():
    """转译腿发的是 Python 解包，个数不符抛 ValueError；原生腿同口径抛异常。

    反例护栏：若实现悄悄跳过少赋的变量，`甲` 会读到 null 而程序照旧 rc=0，
    这就是「静默错编」。故这里断言**非 0 退出或输出里带失败信息**。
    """
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    src = '设 [甲, 乙, 丙] 为 [1, 2]。\n打印 "不该到这"。\n'
    with tempfile.TemporaryDirectory(prefix='_r115a_bad_', dir=_ROOT) as d:
        sp = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(sp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        from llvm.compiler import compile_light_typed
        out = compile_light_typed(sp, exe, optimize_level=0)
        r = subprocess.run([out], capture_output=True, timeout=300, env=env)
    out_txt = (r.stdout.decode('utf-8', 'replace') +
               r.stderr.decode('utf-8', 'replace'))
    assert '不该到这' not in out_txt or r.returncode != 0, (
        f'个数不匹配被静默吞掉了：rc={r.returncode} 输出={out_txt[:400]!r}')


# ----------------------------------------------------------------------
# 四、能力矩阵必须跟着更新
# ----------------------------------------------------------------------

def test_能力矩阵把两条语句记成已支持():
    """矩阵 JSON 与代码双向咬合：代码支持了而矩阵还记成缺口 → 红。"""
    path = os.path.join(_ROOT, 'docs', 'llvm_backend_capability_matrix.json')
    import json
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    状态 = {r['v3_class']: r['status'] for r in data['rows']}
    assert 状态['MatchStmt'].startswith('supported'), \
        f'MatchStmt 在矩阵里还是 {状态["MatchStmt"]}'
    assert 状态['DestructuringAssignment'].startswith('supported'), \
        f'DestructuringAssignment 在矩阵里还是 {状态["DestructuringAssignment"]}'
    # `使用 X 为 Y：` 本轮（R116-A）已转正：进入调 `__进入__` 绑定返回值、
    # 体、离开调 `__退出__`，异常亦走 `__退出__` 后重抛。矩阵必须如实记成 supported。
    assert 状态['WithStmt'].startswith('supported'), \
        f'WithStmt 在矩阵里还是 {状态["WithStmt"]}（R116-A 已实现，应记成 supported）'


def test_能力边界文档登记了两条语句():
    path = os.path.join(_ROOT, 'docs', '原生腿能力边界.md')
    with open(path, encoding='utf-8') as f:
        text = f.read()
    for 词 in ('MatchStatement', 'DestructuringAssignment', '使用 X 为 Y'):
        assert 词 in text, f'能力边界文档里找不到 {词}'
