# -*- coding: utf-8 -*-
"""任务 C3-2：原生腿补的几个表达式——真跑，不许只断言 IR 文本。

按「判据表靠源码级断言守单点 / 新能力必须真跑并断言 stdout」的既定口径：
`.light → IR → clang → exe` 全链路跑起来，断言 stdout（或断言炸得响亮）。
运行时目标码整场只编一次（tests/llvm运行时.py）。

覆盖：
· DictLiteral 真跑（harness 消息/载荷全是字典，原生腿承载 harness 的硬前提）
· StringInterpolation 真跑（降级实现：拆段 + 字符串拼接）
· RangeExpr（经 `范围()` 内置）真跑
· 未支持表达式的报错路径（C3-1）与 SliceExpr 的指路文案（C3-2 决策：不做切片）
· PassStmt 编成空操作（C3-4）
"""

import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llvm.compiler import compile_source_typed, find_clang  # noqa: E402
from llvm运行时 import 取运行时对象, 取链接库参数  # noqa: E402

_CODEGEN_TYPED = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'llvm', 'codegen_typed.py')


def _run_native(source: str, timeout: int = 20):
    """`.light → IR → clang → exe` 全链路，返回 (returncode, stdout)。"""
    ir = compile_source_typed(source)
    clang = find_clang()
    runtime_o = 取运行时对象(clang)
    with tempfile.TemporaryDirectory(prefix='_taskC3_') as tmp:
        ir_path = os.path.join(tmp, 'probe.ll')
        exe_path = os.path.join(tmp, 'probe.exe')
        with open(ir_path, 'w', encoding='utf-8') as f:
            f.write(ir)
        link = subprocess.run(
            [clang, '-O2', '-o', exe_path, ir_path, runtime_o, *取链接库参数()],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        if link.returncode != 0:
            raise AssertionError(f'clang 链接失败:\n{link.stderr[:2000]}')
        run = subprocess.run(
            [exe_path], capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=timeout)
        return run.returncode, run.stdout.strip()


def _assert_stdout(source: str, expected_lines):
    rc, out = _run_native(source)
    assert rc == 0, f'退出码 {rc}，stdout: {out!r}'
    got = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert got == [s.strip() for s in expected_lines], f'stdout 不符\n期望: {expected_lines}\n实际: {got}'


# =============================================================================
# DictLiteral：字典字面量真跑
# =============================================================================

def test_dict_literal_构建与索引真跑():
    _assert_stdout(
        '设 字典 为 {"甲": 1, "乙": 2}。\n'
        '打印 字典["乙"]。\n'
        '打印 字典["甲"]。\n',
        ['2', '1'])


def test_dict_literal_空字典():
    # 运行时 dv_to_string 对字典只给简化表示「dict」，所以断言它确实是字典
    # （类型 7 DICT），而不是空串/0——空字典字面量编得出、跑得动。
    _assert_stdout(
        '设 字典 为 {}。\n'
        '打印 字典。\n',
        ['dict'])


def test_dict_literal_混合键值类型():
    _assert_stdout(
        '设 字典 为 {"名": "小明", 年龄: 18}。\n'
        '打印 字典["名"]。\n'
        '打印 字典[年龄]。\n',
        ['小明', '18'])


# =============================================================================
# StringInterpolation：字符串插值真跑（降级实现：拆段 + 拼接）
# =============================================================================

def test_string_interpolation_字面段与表达式段():
    _assert_stdout(
        '设 名字 为 "小明"。\n'
        '设 年龄 为 18。\n'
        '打印 f"你好，{名字}，{年龄} 岁"。\n',
        ['你好，小明，18 岁'])


def test_string_interpolation_纯字面段():
    """没有插值段时不能编坏（退化成纯字符串）。"""
    _assert_stdout(
        '打印 f"没有插值段"。\n',
        ['没有插值段'])


# =============================================================================
# RangeExpr：经 `范围()` 内置真跑（不需要切片）
# =============================================================================

def test_range_expr_真跑():
    # 原生腿 `范围(起, 止)` 是闭区间（runtime `sle` 判定，改动前既有语义）：
    # 1..4 包含两端 → 1,2,3,4。测的是「能真跑」，不是修正语义。
    _assert_stdout(
        '遍历 甲 于 范围(1, 4)：\n'
        '  打印 甲。\n',
        ['1', '2', '3', '4'])


# =============================================================================
# C3-1 报错路径：未支持表达式必须炸得响亮，不许静默编成 0
# =============================================================================

_拒绝用例 = [
    ('字典推导', '打印([数 乘 2 遍历 数 于 [1, 2]])。\n', 'ListComprehension'),
    ('集合字面量表达式位', '设 甲 为 {1, 2}。\n', 'SetLiteral'),
    ('元组字面量', '设 甲 为 (1, 2)。\n', 'TupleLiteral'),
    ('Lambda', '设 平方 为 接收 甲：返回 甲 乘 甲。\n', 'LambdaExpression'),
    # C3-4：以下四条是适配层缺转换器的**语句**位节点，同样要能报出原 v3 真名。
    # （一个未支持类型一条，C3-4 口径：每个走 <unknown:XXX> 的节点都能自报家门）
    ('装饰器段落', '@性能 段落 甲()：\n  返回 1。\n打印 甲()。\n', 'DecoratedFunction'),
    ('异步运行', '异步 运行 主()。\n', 'RunAsyncStmt'),
    ('断言语句', '设 甲 为 1。\n断言 甲 == 1。\n', 'AssertStmt'),
    ('全局声明', '全局 甲。\n', 'ScopeDeclStmt'),
    ('生成语句', '段落 甲()：\n  生成 1。\n', 'YieldStmt'),
    ('类型别名', '类型 甲 为 整数。\n', 'TypeAlias'),
]


@pytest.mark.parametrize('名称, 源码, 类型名', _拒绝用例, ids=[c[0] for c in _拒绝用例])
def test_未支持表达式必须抛错且文案含类型名(名称, 源码, 类型名):
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(源码)
    文案 = str(ei.value)
    assert 类型名 in 文案, f'{名称}：文案没点明表达式类型（{类型名}），实际是：{文案}'
    assert '转译后端' in 文案, f'{名称}：文案没给出可走的后端，实际是：{文案}'


def test_切片表达式报错指路():
    """SliceExpr 本轮不做切片：报错要指到可用的替代，不许藏成「未定义段落」。"""
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed('设 甲 为 [1, 2, 3]。\n设 乙 为 甲[1:2]。\n')
    文案 = str(ei.value)
    assert 'SliceExpr' in 文案 and '截取' in 文案, f'切片文案没指路，实际是：{文案}'


def test_未知段落调用报错列出候选():
    """拼错名字的段落调用：报错并列出本模块已定义候选（不再静默编成 0）。"""
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(
            '段落 计算总和(表)：\n'
            '  返回 3。\n'
            '设 结果 为 计算总合(表)。\n')
    文案 = str(ei.value)
    assert '计算总合' in 文案, f'没报出拼错的段落名，实际是：{文案}'
    assert '计算总和' in 文案, f'没列出已定义候选，实际是：{文案}'


def test_整除运算符真跑():
    """`整除`（parser 归一成 '//'）改动前在原生腿静默编成 dv_add——`7 整除 2`
    算出 9。现在双整数走 sdiv 整除，真跑断言 3。"""
    _assert_stdout(
        '设 甲 为 7 整除 2。\n'
        '打印 甲。\n',
        ['3'])


def test_二元运算符链尾不是静默加法():
    """防守位静态断言：`_gen_typed_binary_op` 链尾必须抛 NotImplementedError，
    不许改回 `dv_add`。parser 正常情况下产不出未知运算符 BinaryOp（`管道` 会被
    切词成标识符），所以这里守住的是「兜底还在守」本身，不做假真跑。"""
    import re as _re
    src = open(_CODEGEN_TYPED, encoding='utf-8').read()
    i = src.find('def _gen_typed_binary_op')
    assert i > 0, '找不到 _gen_typed_binary_op'
    j = src.find('\n    def ', i + 10)
    body = src[i:j if j > 0 else len(src)]
    assert _re.search(r'\n\s{8}raise NotImplementedError\(', body), \
        '二元运算符链尾兜底不见了'
    assert 'dv_add' in src, 'dv_add 还在映射表里（整除需要它走 dv_div）'


# =============================================================================
# C3-4：PassStmt 编成空操作而不是报错
# =============================================================================

def test_pass_stmt_编成空操作():
    _assert_stdout(
        '设 甲 为 1。\n'
        'pass。\n'
        '打印 甲。\n',
        ['1'])


def test_pass_stmt_在段落体内():
    _assert_stdout(
        '段落 甲()：\n'
        '  pass。\n'
        '  返回 7。\n'
        '打印 甲()。\n',
        ['7'])
