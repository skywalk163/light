# -*- coding: utf-8 -*-
"""任务 A：前端阻断缺陷的**真跑**回归用例。

为什么不用字符串断言：现存 tests/test_async.py 全是 `assert 'async def' in py_code`
这类形状断言，于是「顶层 await 编出非法 Python」这种洞长期没人发现——产物根本没被
执行过。本文件每条用例都走两条腿：

  · run 腿    ：`python -m cli.light_unified run 源码.light`，比对 stdout
  · product 腿：`compile -o 产物.py` 再独立跑产物，比对同一份 stdout

两条腿的 sys.path 由不同的人铺（run 腿由 CLI 自己 insert src/，product 腿只有产物
引导段），历史上产物自洽问题就是这么暴露的，所以两条都要跑。

覆盖：A3（映射/筛选 参数序）。后续 A1/A2/A4~A7 在同一文件按段追加。
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# 子进程强制 UTF-8：Windows 控制台默认 cp936，中文/emoji 输出会抛
# UnicodeEncodeError，与被测语义无关。与 tests/e2e/test_e2e_chain.py 同一口径。
SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}


def _run_light(source: str):
    """`duan run 源码`：返回 (returncode, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / 'probe.light'
        src.write_text(source, encoding='utf-8')
        r = subprocess.run(
            [sys.executable, '-m', 'cli.light_unified', 'run', str(src)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
        return r.returncode, r.stdout, r.stderr


def _run_product(source: str):
    """`duan compile -o 产物.py` 后独立执行产物：返回 (returncode, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / 'probe.light'
        src.write_text(source, encoding='utf-8')
        out_py = Path(tmpdir) / 'product.py'
        c = subprocess.run(
            [sys.executable, '-m', 'cli.light_unified',
             'compile', str(src), '-o', str(out_py)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
        assert c.returncode == 0, f"编译失败:\n{c.stderr}\n{c.stdout}"
        assert out_py.exists(), f"产物未生成:\n{c.stdout}"
        r = subprocess.run(
            [sys.executable, str(out_py)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
        return r.returncode, r.stdout, r.stderr


def _assert_stdout(source: str, expected_lines):
    """两条腿都跑，且 stdout 逐行等于 expected_lines。"""
    expected = [s.strip() for s in expected_lines]
    for leg, runner in (('run', _run_light), ('product', _run_product)):
        rc, out, err = runner(source)
        assert rc == 0, f"[{leg}] 退出码 {rc}:\n{err}\n{out}"
        got = [ln.strip() for ln in out.strip().splitlines() if ln.strip()]
        assert got == expected, f"[{leg}] stdout 不符\n期望: {expected}\n实际: {got}"


# =============================================================================
# A3：映射 / 筛选 参数顺序
#
# 权威 docs/光明-完整规范文档.md:2553-2554：源码 `筛选列表条件` 等价
# `filter(条件, 列表)`、`映射列表函数` 等价 `map(函数, 列表)`——光明侧一律
# 「数据在前、函数在后」，codegen 负责换序。修复前 codegen 按源序直落，
# `映射([1,2], 接收 数：…)` → `map([1,2], lambda …)` → 运行期
# `TypeError: 'function' object is not iterable`。
# =============================================================================

def test_a3_映射_数据在前():
    _assert_stdout(
        '打印(列表(映射([1,2,3], 接收 数：返回 数 乘 2)))。\n',
        ['[2, 4, 6]'])


def test_a3_筛选_数据在前():
    _assert_stdout(
        '打印(列表(筛选([1,2,3,4], 接收 数：返回 数 模 2 等于 0)))。\n',
        ['[2, 4]'])


def test_a3_具名函数做实参():
    """函数不是 lambda 字面量时同样换序（这条走 Identifier 分支，不是 LambdaExpression）。"""
    source = (
        '段落 加倍 接收 数：\n'
        '    返回 数 乘 2。\n'
        '\n'
        '打印(列表(映射([1,2,3], 加倍)))。\n'
    )
    _assert_stdout(source, ['[2, 4, 6]'])


def test_a3_无括号并置式():
    """规范里的谓宾结构 `映射 列表 函数`（无括号）走同一个 ParagraphCall 分支。"""
    source = (
        '设 数据 为 [1,2,3]。\n'
        '设 结果 为 映射 数据 接收 数：返回 数 加上 10。\n'
        '打印(列表(结果))。\n'
    )
    _assert_stdout(source, ['[11, 12, 13]'])


def test_a3_旧语序_函数在前_编译期报错():
    """旧写法 `映射(接收 …, 数据)` 换序后会发射 map(lambda, 数据) —— 又一次静默错编。
    必须编译期拦住并给出修正提示，不许静默产出错代码。"""
    rc, out, err = _run_light(
        '打印(列表(映射(接收 数：返回 数 乘 2, [1,2,3])))。\n')
    assert rc != 0, f"旧语序应编译期报错，实际退出码 0:\n{out}"
    combined = out + err
    assert '数据在前' in combined, f"报错信息未给出语序提示:\n{combined}"


def test_a3_语序判不定时不换序():
    """两个实参都是裸名字（形参）时判不定语序：按源码语序原样发射，不猜。

    积木库 blocks_v4/blocks_v5 的 函数映射.light 正是 `返回 映射(甲, 输入)`
    这种写法（甲 是函数形参）。无条件换序会编成 `map(输入, 甲)`——参数颠倒，
    且 map 惰性求值不会立刻抛错，属于静默算错。这里真跑确认语义没被换坏。
    """
    source = (
        '段落 应用 接收 输入, 甲：\n'
        '    返回 映射(甲, 输入)。\n'
        '\n'
        '打印(列表(应用([1,2,3], 接收 数：返回 数 乘 2)))。\n'
    )
    _assert_stdout(source, ['[2, 4, 6]'])



# =============================================================================
# A2：生成器委托 `生成 全部 X。` → `yield from X`
#
# 修复前：`生成 从 乙()。` 编成 `yield 从` + `乙()` 两条语句（编译期零提示，
# 运行期才炸）；`生成 全部 乙()。` 编成 `yield all(乙)()`。两种写法都是静默错编。
# 现在 `全部` 落地委托，`从` 编译期报错。
# =============================================================================

def test_a2_生成器委托():
    source = (
        '段落 内层：\n'
        '    生成 1。\n'
        '    生成 2。\n'
        '\n'
        '段落 外层：\n'
        '    生成 全部 内层()。\n'
        '    生成 3。\n'
        '\n'
        '遍历 项 之 外层()：\n'
        '    打印(项)。\n'
    )
    _assert_stdout(source, ['1', '2', '3'])


def test_a2_全部带括号仍是内置all():
    """`生成 全部(列)。` 是把 all(列) 的布尔值 yield 出去，不能被委托语法抢走。"""
    source = (
        '段落 甲：\n'
        '    生成 全部([1, 0])。\n'
        '\n'
        '遍历 项 之 甲()：\n'
        '    打印(项)。\n'
    )
    _assert_stdout(source, ['False'])


def test_a2_生成_从_编译期报错():
    source = (
        '段落 内层：\n'
        '    生成 1。\n'
        '\n'
        '段落 外层：\n'
        '    生成 从 内层()。\n'
        '\n'
        '遍历 项 之 外层()：\n'
        '    打印(项)。\n'
    )
    rc, out, err = _run_light(source)
    assert rc != 0, f"`生成 从 …` 应编译期报错，实际退出码 0:\n{out}"
    combined = out + err
    assert '生成 全部' in combined, f"报错信息未指向 `生成 全部`:\n{combined}"


# =============================================================================
# A1：异步启动入口 `异步 运行 主()。` → `asyncio.run(主())`
#
# 修复前：光明写不出任何能跑的 async 程序——顶层 `等待 主()。` 生成模块级裸
# await → `SyntaxError: 'await' outside function`；没有 asyncio.run 等价物；
# 退路 `引 Python：asyncio.run(主())` 因 L4 块 exec 到独立 ModuleType 而看不见
# 光明侧的 `主` → NameError。
#
# 为什么是 `异步 运行` 而不是任务书建议的 `运行 异步`：见
# src/parser_stmt.py 的 _parse_run_async_stmt docstring——`运行` 已被现存
# .light 当作段落名/形参名使用，提成全局关键字会直接打红那些文件。
# =============================================================================

def test_a1_异步启动入口():
    """任务书 A1 验收断言原文。"""
    source = (
        '异步 段落 报数 接收 次数：\n'
        '    设 索引 为 0。\n'
        '    当 索引 小于 次数：\n'
        '        打印(索引)。\n'
        '        设 索引 为 索引 加上 1。\n'
        '\n'
        '异步 运行 报数(3)。\n'
    )
    _assert_stdout(source, ['0', '1', '2'])


def test_a1_await链路真跑():
    """启动器 + 异步段落里真 await 另一个异步段落，验证 await 结果拿得到。"""
    source = (
        '异步 段落 取数：\n'
        '    返回 7。\n'
        '\n'
        '异步 段落 主：\n'
        '    设 值 为 等待 取数()。\n'
        '    打印(值)。\n'
        '\n'
        '异步 运行 主()。\n'
    )
    _assert_stdout(source, ['7'])


def test_a1_顶层等待_编译期报错():
    rc, out, err = _run_light(
        '异步 段落 主：\n'
        '    打印(1)。\n'
        '\n'
        '等待 主()。\n'
    )
    assert rc != 0, f"顶层 等待 应编译期报错，实际退出码 0:\n{out}"
    combined = out + err
    assert '异步 运行' in combined, f"报错未指向启动语句:\n{combined}"


def test_a1_顶层异步作用域_编译期报错():
    rc, out, err = _run_light(
        '异步 段落 甲：\n'
        '    打印(1)。\n'
        '\n'
        '异步 作用域：\n'
        '    甲()。\n'
    )
    assert rc != 0, f"顶层 异步 作用域 应编译期报错，实际退出码 0:\n{out}"
    combined = out + err
    assert '异步 运行' in combined, f"报错未指向启动语句:\n{combined}"


# =============================================================================
# A4：调用侧关键字实参 `函数(位置实参, 名 = 值)` → Python kwargs
#
# 修复前有两个洞（探针 `连接("example.com", 超时 = 5)` 一次暴露两个）：
#   1) `接收 端口 等于 443` 的形参默认值被 parser 静默丢弃（原 default_val 是
#      死变量），产物只有 `def 连接(主机, 端口, 超时)` → 运行期
#      `missing 1 required positional argument: '端口'`。
#   2) 可变参数动词（ALL_VERB_ARITY 里 arity == -1，如 `打印`）的括号分支没有
#      kwarg 产生式，`打印("尾", end = "!")` 直接「意外的标记: 「=」」。
# 用户自定义段落的 kwarg 传递本来就通，所以这两条才是真正的缺口。
# =============================================================================

def test_a4_形参默认值与具名实参():
    """任务书 A4 验收断言原文：`连接("example.com", 超时 = 5)` → example.com:443/5。"""
    source = (
        '段落 连接 接收 主机, 端口 等于 443, 超时 等于 30：\n'
        '    打印(f"{主机}:{端口}/{超时}")。\n'
        '\n'
        '连接("example.com", 超时 = 5)。\n'
        '连接("a.com", 端口 = 80, 超时 = 1)。\n'
        '连接("b.com")。\n'
    )
    _assert_stdout(source, ['example.com:443/5', 'a.com:80/1', 'b.com:443/30'])


def test_a4_可变参数动词的具名实参():
    """`打印` 在 ALL_VERB_ARITY 里 arity == -1，走的是另一条括号分支。"""
    _assert_stdout('打印("尾", end = "!")。\n打印("")。\n', ['尾!'])


def test_a4_带类型注解的形参默认值():
    """`名: 类型 = 值` 与 `名=值` 是两种发射形状，都要真跑。"""
    source = (
        '段落 重试 接收 次数：整数 等于 3：\n'
        '    打印(次数)。\n'
        '\n'
        '重试()。\n'
        '重试(次数 = 9)。\n'
    )
    _assert_stdout(source, ['3', '9'])


# =============================================================================
# A5：作用域声明 `全局 名。` → global 名；`外层 名。` → nonlocal 名
#
# 修复前：段落体内无法写回外层变量——`设 计数 为 计数 加上 1` 一律是局部赋值，
# 而源码里的 `全局 计数。` 被当成并置式调用编成 `全局(计数)`，运行期
# `NameError: name '全局' is not defined`（静默错编，编译期零提示）。
#
# 实现走范式 A（词法零改动）：两词不进关键字表，由 parser 在语句开头对裸
# IDENTIFIER 前视接管，判据见 parser_stmt.py 的 _is_scope_decl_header。
# 之所以不进关键字表：实测加表会连带打红两处——`全局搜索搜索`（积木库）在无
# 声明的调用位置被切成 `全局`+`搜索搜索`；`外层 = 外层 + 1`
# （src/templates/data_analysis/分析.light:103）撞上 parser_stmt.py:578
# 赋值分支只认 IDENTIFIER，直接报「「外层」是保留关键字」。
# =============================================================================

def test_a5_全局写回模块变量():
    source = (
        '设 计数 为 0。\n'
        '\n'
        '段落 加一：\n'
        '    全局 计数。\n'
        '    设 计数 为 计数 加上 1。\n'
        '\n'
        '加一()。\n'
        '加一()。\n'
        '打印(计数)。\n'
    )
    _assert_stdout(source, ['2'])


def test_a5_外层写回外层变量():
    source = (
        '段落 甲：\n'
        '    设 值 为 1。\n'
        '    段落 乙：\n'
        '        外层 值。\n'
        '        设 值 为 值 加上 10。\n'
        '    乙()。\n'
        '    打印(值)。\n'
        '\n'
        '甲()。\n'
    )
    _assert_stdout(source, ['11'])


def test_a5_一句声明多个名字():
    source = (
        '设 甲 为 0。\n'
        '设 乙 为 0。\n'
        '\n'
        '段落 改：\n'
        '    全局 甲, 乙。\n'
        '    设 甲 为 7。\n'
        '    设 乙 为 8。\n'
        '\n'
        '改()。\n'
        '打印(甲)。\n'
        '打印(乙)。\n'
    )
    _assert_stdout(source, ['7', '8'])


def test_a5_把全局当变量名的旧写法不受影响():
    """范式 A 的守卫：`全局 等于 1。` 走的还是赋值分支，逐字不变。"""
    _assert_stdout('全局 等于 1。\n打印(全局)。\n', ['1'])


def test_a5_顶层作用域声明_编译期报错():
    rc, out, err = _run_light('全局 计数。\n打印(1)。\n')
    assert rc != 0, f"模块级 全局 应编译期报错，实际退出码 0:\n{out}"
    combined = out + err
    assert '段落' in combined, f"报错未说明只能写在段落体内:\n{combined}"


# =============================================================================
# A6：类体内 `属性 名 为 值。` / `属性 名：类型 为 值。`
#
# 修复前两种写法都是硬报错（不是静默错编）：属性名收集在 `为` 处停下，但默认值
# 分支只认 `等于`，剩下的 `为` 掉回类体循环 →「类体内不支持的成员声明：'为'」；
# `：类型` 同理无人接手。而 `为`/`等于` 在光明其余各处一律同义（设 甲 为 1 /
# 令 甲 = 1），AttributeDeclaration 也早就有 type_annotation 槽位（类级字段
# `设 名: 类型 为 值` 一直在用）。
# =============================================================================

def test_a6_属性_为_默认值():
    source = (
        '类 点：\n'
        '    属性 横 为 3。\n'
        '    属性 纵 为 4。\n'
        '\n'
        '    段落 显示 接收 己：\n'
        '        打印(f"{己.横},{己.纵}")。\n'
        '\n'
        '设 甲 为 点()。\n'
        '甲.显示()。\n'
    )
    _assert_stdout(source, ['3,4'])


def test_a6_属性带类型标注():
    source = (
        '类 计数器：\n'
        '    属性 次数：整数 为 0。\n'
        '\n'
        '    段落 加 接收 己：\n'
        '        己.次数 为 己.次数 加上 1。\n'
        '        打印(己.次数)。\n'
        '\n'
        '设 甲 为 计数器()。\n'
        '甲.加()。\n'
        '甲.加()。\n'
    )
    _assert_stdout(source, ['1', '2'])


def test_a6_旧写法_等于_不受影响():
    source = (
        '类 狗：\n'
        '    属性 品种 等于 "金毛"。\n'
        '\n'
        '    段落 叫 接收 己：\n'
        '        打印(己.品种)。\n'
        '\n'
        '设 甲 为 狗()。\n'
        '甲.叫()。\n'
    )
    _assert_stdout(source, ['金毛'])


# =============================================================================
# A7：推导式接受 `于`（以及 `中的`）
#
# 遍历 语句的连接词表 parser_stmt.py FOREACH_CONNECTORS_VAR_FIRST 是
# {之, 在, 于, 中的}，四处推导式却各自硬写 `之`/`在` 两支——而同一段代码里
# 的变量名停止词表写的又是四个词。于是 `[项 遍历 项 于 数据]` 的变量名在 `于`
# 处正确断开、紧接着连接词判断不认 `于`，硬报「列表推导期望'之'或'在'」。
# 修法是删掉第五份表：推导式改读 FOREACH_CONNECTORS_VAR_FIRST 这个单点
# （parser_expr.py _consume_comprehension_connector），而不是反向去掉 遍历 的 `于`。
# =============================================================================

def test_a7_列表推导_于():
    _assert_stdout(
        '设 数据 为 [1, 2, 3, 4]。\n'
        '打印([项 乘 2 遍历 项 于 数据])。\n',
        ['[2, 4, 6, 8]'])


def test_a7_集合推导_于_带条件():
    _assert_stdout(
        '设 数据 为 [1, 2, 3, 4]。\n'
        '打印({项 遍历 项 于 数据 若 项 模 2 等于 0})。\n',
        ['{2, 4}'])


def test_a7_字典推导_于():
    _assert_stdout(
        '打印({项: 项 乘 项 遍历 项 于 [1, 2]})。\n',
        ['{1: 1, 2: 4}'])


def test_a7_四个连接词等价():
    """之 / 在 / 于 / 中的 同表，四种写法结果一致。"""
    _assert_stdout(
        '设 数据 为 [1, 2]。\n'
        '打印([项 遍历 项 之 数据])。\n'
        '打印([项 遍历 项 在 数据])。\n'
        '打印([项 遍历 项 于 数据])。\n'
        '打印([项 遍历 项 中的 数据])。\n',
        ['[1, 2]'] * 4)


# ======================================================================
# 第二轮 A2
# ======================================================================

def test_a22_外层在段落名冲突时仍生效():
    """A2-2 反跑护栏：文件里有段落叫 `外` 时，`外层 计数。` 必须仍编成 nonlocal。

    旧判据只比单个 token 的 value，而分词是上下文相关的——`外` 被登记成定义名后
    `外层` 会切成 `外`+`层`，判据不命中，语句被当并置调用静默编成 `外层(计数)`，
    编译期零提示、运行期 NameError。孤立写法切得出单 token，所以常规用例照不出来，
    这条用例的价值全在「段落名叫 外」这个前提上，改动时不要把它简化掉。
    """
    _assert_stdout(
        '段落 外():\n'
        '    设 计数 为 0\n'
        '    段落 内():\n'
        '        外层 计数。\n'
        '        设 计数 为 计数 加 1。\n'
        '    内()。\n'
        '    打印 计数。\n'
        '\n'
        '外()。\n',
        ['1'])


def test_a22_全局在段落名冲突时仍生效():
    """A2-2 同一判据的 `全局` 侧：文件里有段落叫 `全` 时也要成立。"""
    _assert_stdout(
        '设 计数 为 0。\n'
        '段落 全():\n'
        '    返回 0。\n'
        '段落 加()：\n'
        '    全局 计数。\n'
        '    设 计数 为 计数 加 1。\n'
        '加()。\n'
        '打印 计数。\n',
        ['1'])


def test_a23_异步睡眠():
    """A2-3：`异步睡眠` 以前只在 src/lexer.py 的标识符白名单里，codegen 零映射，
    写了就是运行期 NameError。现在映射到 asyncio.sleep。"""
    _assert_stdout(
        '异步 段落 主()：\n'
        '    等待 异步睡眠(0.01)。\n'
        '    打印 "睡醒"。\n'
        '\n'
        '异步 运行 主()。\n',
        ['睡醒'])


def test_a23_限时():
    """A2-3：`限时(协程, 秒)` → asyncio.wait_for。agent 循环的单次请求超时靠它。"""
    _assert_stdout(
        '异步 段落 慢()：\n'
        '    等待 异步睡眠(0.01)。\n'
        '    返回 7。\n'
        '\n'
        '异步 段落 主()：\n'
        '    设 甲 为 等待 限时(慢(), 5)。\n'
        '    打印 甲。\n'
        '\n'
        '异步 运行 主()。\n',
        ['7'])


@pytest.mark.parametrize('间隔', ['等待 任务甲', '等待  任务甲'])
def test_a23_等待局部变量(间隔):
    """`等待 <局部变量>` 必须编成 `await 变量`，不许拼成一个名字。

    修复前：`src/parser_expr.py` 的 `等待` 分支只看下一个 token 的类型——
    `等待 任务甲。` 后面是 PERIOD 而不是 LPAREN/DOT，于是走进「复合标识符」分支，
    静默编成 `结果 = 等待任务甲`（不存在的名字）。`等待 报()`/`等待 限时(...)`
    看不出问题，纯粹因为它们后面跟着括号。
    判据改成**源码是否相邻**：`等待价值` 两 token 首尾相接才拼名字，中间有空白
    就是 await 一个值。参数化两种空白宽度，防止「只判一个空格」的假修。
    """
    _assert_stdout(
        '异步 段落 报(数)：\n'
        '    等待 异步睡眠(0.01)。\n'
        '    返回 数 乘 2。\n'
        '\n'
        '异步 段落 主()：\n'
        '    设 任务甲 为 创建任务(报(3))。\n'
        f'    设 结果 为 {间隔}。\n'
        '    打印 结果。\n'
        '\n'
        '异步 运行 主()。\n',
        ['6'])


def test_a23_等待价值复合词不受影响():
    """反跑护栏：词法层被切开的整词 `等待价值` 仍要当一个名字。

    这条和上面那条是一对——相邻判据两侧各钉一个，少任何一条都可能被
    「一律当 await」或「一律拼名字」的假修蒙过去。
    """
    _assert_stdout(
        '设 等待价值 为 3。\n'
        '打印 等待价值。\n',
        ['3'])



def test_a23_创建任务映射到create_task():
    """A2-3 的可验证部分：不经 `等待 变量`，直接确认 `创建任务` 真映射成
    asyncio.create_task 且产物带 import asyncio。

    与 `test_a23_等待局部变量` 分开写，是为了让「映射对了」和「`等待 变量` 不粘连」
    两件事各自有独立判据——合成一条的话，任一侧回归都分不清是哪一侧坏的。
    """

    source = (
        '异步 段落 报(数)：\n'
        '    返回 数 乘 2。\n'
        '\n'
        '异步 段落 主()：\n'
        '    设 任务甲 为 创建任务(报(3))。\n'
        '    设 果 为 等待 并发等待([任务甲])。\n'
        '    打印 果。\n'
        '\n'
        '异步 运行 主()。\n'
    )
    _assert_stdout(source, ['[6]'])



def test_a23_并发等待摊平列表():
    """A2-3：`并发等待(任务表)` → asyncio.gather(*任务表)。

    不摊平就是把 list 当单个 awaitable 传进 gather，运行期 TypeError——
    属静默错编的近亲，所以这条断言的是**结果值**而不是产物形状。
    """
    _assert_stdout(
        '异步 段落 报(数)：\n'
        '    等待 异步睡眠(0.01)。\n'
        '    返回 数 乘 10。\n'
        '\n'
        '异步 段落 主()：\n'
        '    设 表 为 [报(1), 报(2), 报(3)]。\n'
        '    设 果 为 等待 并发等待(表)。\n'
        '    打印 果。\n'
        '\n'
        '异步 运行 主()。\n',
        ['[10, 20, 30]'])


def test_a23_并发等待内联列表():
    """A2-3：实参写成内联列表字面量时同样要摊平。"""
    _assert_stdout(
        '异步 段落 报(数)：\n'
        '    返回 数 加 1。\n'
        '\n'
        '异步 段落 主()：\n'
        '    设 果 为 等待 并发等待([报(1), 报(2)])。\n'
        '    打印 果。\n'
        '\n'
        '异步 运行 主()。\n',
        ['[2, 3]'])


def test_a23_用户自定义段落压过异步原语名():
    """A2-3 反跑护栏：用户自己定义了 `限时` 段落时，必须走用户的实现，
    不许被 builtin_map 抢走编成 asyncio.wait_for。"""
    _assert_stdout(
        '段落 限时(甲, 乙)：\n'
        '    返回 甲 加 乙。\n'
        '\n'
        '打印 限时(1, 2)。\n',
        ['3'])


def test_a23_异步文件三名字仍是一个词且失败得响():
    """A2-3：`异步读取文件`/`异步写入文件`/`异步追加文件` 的**现状钉桩**。

    这三个名字在 `src/lexer.py` 的 COMMON_COMPOUND_WORDS 里（本轮保留原状），
    但**没有任何实现**——真实现只在 `stdlib/lightpub/异步运行时.py`，而那份代码
    第一行就是裸 `import aiofiles`（在 try 之前），`except ImportError` 是死代码。
    补零依赖实现要动 `stdlib/`，是任务 A2 明令不许碰的地盘，已进移交清单。

    那这条用例钉什么？钉「失败得响，不是静默错编」：
    - 若把名字从复合词表里删掉，`异步` 是关键字，会被切成 KEYWORD `异步` +
      IDENTIFIER `读取文件`，`设 内容 为 等待 异步读取文件("a")。` 静默编成
      `内容 = await 异步` 加一条结果被丢弃的 `读取文件('a')`——编译通过、语义全错。
    - 现在的行为是产物里出现完整的 `异步读取文件(...)` 调用，运行期报错，
      用户一眼看到缺的就是这个名字。

    判据：必须失败（rc != 0），且报错里出现**完整名字**。只提 `异步` 或
    只提 `读取文件` 即视为「又被切开」的回归。
    """
    source = (
        '异步 段落 主()：\n'
        '    设 内容 为 等待 异步读取文件("不存在.txt")。\n'
        '    打印 内容。\n'
        '\n'
        '异步 运行 主()。\n'
    )
    for leg, runner in (('run', _run_light), ('product', _run_product)):
        rc, out, err = runner(source)
        assert rc != 0, f"[{leg}] `异步读取文件` 没有实现，期望失败但退出码为 0:\n{out}"
        combined = err + out
        assert '异步读取文件' in combined, \
            f"[{leg}] 报错里没有完整名字，说明它又被切成了 `异步`+`读取文件`:\n{combined}"



def test_a23_异步睡眠真的睡了():
    """A2-3：`异步睡眠` → asyncio.sleep 的真跑。

    只断言「跑通且输出正确」，不断言墙钟时长——CI 机器上计时断言是
    典型的不稳定源。睡眠语义本身由 asyncio 保证，这里要保证的是
    「这个名字确实映射到了 asyncio.sleep 而不是一个裸标识符」。
    """
    _assert_stdout(
        '异步 段落 主()：\n'
        '    等待 异步睡眠(0.01)。\n'
        '    打印 "醒了"。\n'
        '\n'
        '异步 运行 主()。\n',
        ['醒了'])


def _compile_product_text(source: str) -> str:
    """编译并返回产物源码文本。

    **只用于「产物里必须出现某个构件」这类结构断言**（A2-4 的 `Generic[`/`TypeVar`），
    不许拿它替代真跑：本文件的口径是先真跑断言可观察行为，结构断言只做补充。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / 'probe.light'
        src.write_text(source, encoding='utf-8')
        out_py = Path(tmpdir) / 'product.py'
        c = subprocess.run(
            [sys.executable, '-m', 'cli.light_unified',
             'compile', str(src), '-o', str(out_py)],
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(REPO_ROOT), timeout=120, env=SUBPROC_ENV,
        )
        assert c.returncode == 0, f"编译失败:\n{c.stderr}\n{c.stdout}"
        return out_py.read_text(encoding='utf-8')


# ----------------------------------------------------------------------
# A2-4 泛型参数发射
#
# 修复前：parser 早就把 `[T]` 存进了 ClassDefinition.generic_params
# （parser_stmt.py:4393）、类型层也消费了（type_inferencer.py:329），但
# code_generator 全文 grep `generic_params|TypeVar|Generic` 零命中——
# `类 栈[T]：` 编成 `class 栈:`，泛型信息在产物里彻底消失（实测产物见
# 自测报告）。这是「解析得了、发射不出」的静默降级：不报错，只是丢东西。
# ----------------------------------------------------------------------

def test_a24_泛型类真跑():
    """泛型容器实例化 + 行为断言（不只看产物形状）。"""
    _assert_stdout(
        '类 栈[T]：\n'
        '  属性 项。\n'
        '  构造：\n'
        '    己项 为 列表创建()。\n'
        '  段落 压入 接收 值：\n'
        '    列表追加(己项, 值)。\n'
        '  段落 顶()：\n'
        '    返回 列表获取(己项, 0)。\n'
        '\n'
        '设 甲 为 栈()。\n'
        '甲.压入(7)。\n'
        '打印 甲.顶()。\n',
        ['7'])


def test_a24_泛型类产物带Generic与TypeVar():
    """结构断言：`Generic[T]` 与 `T = TypeVar('T')` 必须真出现在产物里。

    与上面那条分开：真跑能过不代表泛型没被丢——`class 栈:` 一样跑得出 7。
    这条就是专门钉「信息不许在发射时消失」的。
    """
    code = _compile_product_text(
        '类 栈[T]：\n'
        '  属性 项。\n'
        '  构造：\n'
        '    己项 为 列表创建()。\n'
        '\n'
        '设 甲 为 栈()。\n'
        '打印 "好"。\n')
    assert 'class 栈(Generic[T]):' in code, f"产物里没有 Generic[T]:\n{code[-800:]}"
    assert "T = TypeVar('T')" in code, f"产物里没有 TypeVar 定义:\n{code[:600]}"
    assert 'from typing import Generic, TypeVar' in code, \
        f"产物里没有按需 import:\n{code[:600]}"


def test_a24_多参数泛型类():
    """`[T, U]` 两个参数都要落到 Generic 里，且各出一条 TypeVar。"""
    source = (
        '类 对[T, U]：\n'
        '  属性 左。\n'
        '  属性 右。\n'
        '  构造 接收 左, 右：\n'
        '    己左 为 左。\n'
        '    己右 为 右。\n'
        '  段落 取左()：\n'
        '    返回 己左。\n'
        '\n'
        '设 甲 为 对(3, "四")。\n'
        '打印 甲.取左()。\n'
    )
    _assert_stdout(source, ['3'])
    code = _compile_product_text(source)
    assert 'class 对(Generic[T, U]):' in code, f"多参数泛型没落地:\n{code[-800:]}"
    assert "T = TypeVar('T')" in code and "U = TypeVar('U')" in code, \
        f"TypeVar 没有逐个发射:\n{code[:600]}"


def test_a24_段落级泛型():
    """段落级 `[T]`：Python 3.12 以前 def 头上没有泛型位，所以只登记 TypeVar。

    不登记的后果不是「少个语法糖」——形参注解里写 T 会发射出引用未定义名的注解，
    产物一导入就 NameError。这里断言 TypeVar 真的出现了，并且函数照常能跑。
    """
    source = (
        '段落 首个[T] 接收 表：\n'
        '  返回 列表获取(表, 0)。\n'
        '\n'
        '打印 首个(列(3, 4))。\n'
    )
    _assert_stdout(source, ['3'])
    code = _compile_product_text(source)
    assert "T = TypeVar('T')" in code, f"段落级泛型参数被丢了:\n{code[:600]}"


def test_a24_类型别名从编不出到能编():
    """A2-4 第三处：类型别名。

    改动前 `TypeAlias` 节点在 code_generator 里**没有分支**，直接落到链尾
    `raise CodeGenError("未知语句类型")`——`类型 数表 = 列表。` 一行就让整个文件
    编不出来（实测 run/compile 都是 rc=1）。
    """
    _assert_stdout(
        '类型 数表 = 列表。\n'
        '打印 "别名过了"。\n',
        ['别名过了'])


def test_a24_泛型类型别名带下标():
    """泛型别名的参数不许丢：`类型 表对[T] = 列表。` → `表对 = list[T]`。

    丢掉下标就是静默降级——`表对[整数]` 与 `表对` 会编成同一个东西。
    """
    source = (
        '类型 表对[T] = 列表。\n'
        '打印 "别名过了"。\n'
    )
    _assert_stdout(source, ['别名过了'])
    code = _compile_product_text(source)
    assert '表对 = list[T]' in code, f"泛型别名的参数被丢了:\n{code[-400:]}"


def test_a24_无泛型时不插typing():
    """反跑护栏：按需 import 必须真的「按需」。

    这条防的是「干脆无条件插一行 from typing import …」那种偷懒实现——
    那样做本条会红，而上面几条照样绿。
    """
    code = _compile_product_text('打印 1。\n')
    assert 'TypeVar' not in code, f"没有泛型却插了 TypeVar:\n{code[:600]}"
    assert 'Generic' not in code, f"没有泛型却插了 Generic:\n{code[:600]}"


# ----------------------------------------------------------------------
# A2-5 嵌套类
#
# 修复前：类体成员分派链没有 `类` 分支，落到链尾 self._error，报「类体内不支持
# 的成员声明：'类'」并级联出一串缩进错（实测 10 行源码报 10 个错）。
# ----------------------------------------------------------------------

def test_a25_嵌套类可实例化():
    """`会话.消息` 这种内嵌结构：外层类名点内层类名能构造。"""
    _assert_stdout(
        '类 会话：\n'
        '  类 消息：\n'
        '    属性 文。\n'
        '    构造 接收 文：\n'
        '      己文 为 文。\n'
        '  属性 条。\n'
        '  构造：\n'
        '    己条 为 列表创建()。\n'
        '\n'
        '设 甲 为 会话.消息("你好")。\n'
        '打印 甲.文。\n',
        ['你好'])


def test_a25_两个嵌套类且外层成员不被吞():
    """反跑护栏：嵌套类之后的外层成员必须还在。

    这是本项改动最容易错的地方——嵌套类体结束时吐的 DEDENT 属于外层，
    内层若把它吃掉，外层剩下的属性/段落会被当成内层的成员（静默错编）。
    所以这里同时断言两个内层类都能构造、外层自己的段落也还能调。
    """
    _assert_stdout(
        '类 工具：\n'
        '  类 参数：\n'
        '    属性 名。\n'
        '    构造 接收 名：\n'
        '      己名 为 名。\n'
        '  类 结果：\n'
        '    属性 值。\n'
        '    构造 接收 值：\n'
        '      己值 为 值。\n'
        '  属性 号。\n'
        '  构造：\n'
        '    己号 为 1。\n'
        '  段落 描述()：\n'
        '    返回 己号。\n'
        '\n'
        '设 甲 为 工具()。\n'
        '打印 甲.描述()。\n'
        '设 乙 为 工具.参数("阈值")。\n'
        '打印 乙.名。\n'
        '设 丙 为 工具.结果(9)。\n'
        '打印 丙.值。\n',
        ['1', '阈值', '9'])


def test_a25_三层嵌套():
    """递归发射必须真的递归：`甲.乙.丙` 三层都要能点到。

    只测两层的话，「递归产出」和「只多发射一层」这两种实现分不开。
    """
    _assert_stdout(
        '类 甲：\n'
        '  类 乙：\n'
        '    类 丙：\n'
        '      属性 值。\n'
        '      构造 接收 值：\n'
        '        己值 为 值。\n'
        '\n'
        '设 甲乙丙 为 甲.乙.丙(7)。\n'
        '打印 甲乙丙.值。\n',
        ['7'])


def test_a25_内层类继承顶层基类():
    """内层类的 `继承` 不能因为嵌套而丢：继承来的段落要还能调。

    内层类是在外层类体里发射的，基类名解析走的是模块作用域——这条用例
    钉的就是「嵌套没有改变基类名的解析位置」。
    """
    _assert_stdout(
        '类 基：\n'
        '  段落 说()：\n'
        '    返回 "基"。\n'
        '\n'
        '类 外：\n'
        '  类 内 继承 基：\n'
        '    属性 号。\n'
        '    构造 接收 号：\n'
        '      己号 为 号。\n'
        '\n'
        '设 甲 为 外.内(2)。\n'
        '打印 甲.说()。\n'
        '打印 甲.号。\n',
        ['基', '2'])


def test_a25_泛型外层含嵌套类():
    """A2-4 的 `Generic[T]` 与 A2-5 的嵌套类同篇：两个都要生效。

    发射顺序上嵌套类在静态字段之前、`Generic[T]` 在基类列表里，两处都动了
    类头/类体，所以必须有一条把它们放一起跑的用例。
    """
    _assert_stdout(
        '类 容器[T]：\n'
        '  类 项：\n'
        '    属性 值。\n'
        '    构造 接收 值：\n'
        '      己值 为 值。\n'
        '  属性 数。\n'
        '  构造：\n'
        '    己数 为 0。\n'
        '\n'
        '设 甲 为 容器.项(5)。\n'
        '打印 甲.值。\n'
        '设 乙 为 容器()。\n'
        '打印 乙.数。\n',
        ['5', '0'])



# ----------------------------------------------------------------------
# A2-7 可空 `?`：决策为**永不支持**，报错必须指向 `可空 整数`
# ----------------------------------------------------------------------

def test_a27_问号报错指向可空前缀():
    """`设 甲: 整数? 为 无。` 必须失败，且文案给出正确写法。

    改动前文案是 `未知字符: '?' (0x003F)`——技术上没错，但用户不知道该写什么。
    """
    rc, out, err = _run_light('设 甲: 整数? 为 无。\n打印 "可空"。\n')
    assert rc != 0, f"`?` 不该被接受:\n{out}"
    combined = err + out
    assert '可空 整数' in combined, f"报错没有指向 `可空 整数`:\n{combined}"


# ----------------------------------------------------------------------
# P0 通则：`异步` 是修饰符，出现在表达式位置一律拒绝
# ----------------------------------------------------------------------

@pytest.mark.parametrize('名字', [
    '异步读取二进制', '异步写入二进制', '异步HTTP获取',
    '异步任务等待', '异步任务取消', '异步取数',
])
def test_p0_异步修饰符不许当值用(名字):
    """凡是以 `异步` 开头又不在复合词表里的名字，必须**编译期失败**。

    改动前：`异步` 是关键字，这类名字被切成 KEYWORD `异步` + IDENTIFIER 余下部分，
    `设 果 为 等待 异步任务取消(x)。` 实测编成两条语句——`果 = await 异步` 加一条
    结果被丢弃的调用，一路 PARSE-OK。这是最高优先级的静默错编。

    为什么用通则拦而不是逐个往 `src/lexer.py` 复合词表里加名字：加名字只覆盖已知的
    几个，用户自写 `异步取数()` 照样中招（所以参数表里最后一个是自造名字）。
    护栏另一半是 `test_p0_异步在语句位置不受影响`——那三种合法写法都在语句层处理，
    不经过 `_parse_primary`，必须仍然能跑。
    """
    source = ('异步 段落 主()：\n'
              f'    设 果 为 等待 {名字}("x")。\n'
              '    打印 果。\n'
              '\n'
              '异步 运行 主()。\n')
    rc, out, err = _run_light(source)
    assert rc != 0, f"`{名字}` 被静默接受了，产物:\n{out}"
    assert '修饰符' in (err + out), f"报错没指出根因（`异步` 被当值用）:\n{err}\n{out}"


def test_p0_异步在语句位置不受影响():
    """`异步 段落` / `异步 遍历` / `异步 运行` 三种合法写法的反跑护栏。"""
    _assert_stdout(
        '异步 段落 生()：\n'
        '    生成 1。\n'
        '    生成 2。\n'
        '\n'
        '异步 段落 主()：\n'
        '    异步 遍历 值 于 生()：\n'
        '        打印 值。\n'
        '\n'
        '异步 运行 主()。\n',
        ['1', '2'])


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))



