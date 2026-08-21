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


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))


