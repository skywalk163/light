# -*- coding: utf-8 -*-
"""A2-1：原生（LLVM）后端语句分派的覆盖与兜底。

改动前 `TypedLLVMCodeGen._gen_statement` 的 isinstance 链**没有 else**：
不认识的语句被静默丢弃，编译照旧 PARSE-OK、IR 照旧生成，程序少干一件事却
一声不响——本仓库把这类缺陷叫「静默错编」，它比编不过糟得多。

上游还有第二层伪装：`compiler.AstAdapter` 对没有转换器的 v3 节点返回
`ExpressionStatement(Identifier("<unknown:XXX>"))`。这东西在原生后端看来是
一个合法的表达式语句，链尾兜底也抓不住它，所以 A2-1 在 `ExpressionStatement`
分支里先把这层伪装拆掉，报出它原本的 v3 类型名。

本文件两组断言：
  正跑：未支持语句必须抛 `NotImplementedError`，且**文案含语句类型名**——
        只说「不支持」不够，用户得知道是哪条语句。
  反跑：已支持语句（赋值 / `如果` / `遍历` / `返回`）必须仍然编得出 IR，
        且 IR 里不许残留 `<unknown`。少了这组，把兜底写成「一律抛」也能全绿。
另有一组静态断言钉住兜底本身还在（把 else 分支删掉、或把拆伪装那段注释掉，
仅靠正跑用例仍会红，但静态断言让「守卫是否在守」这件事本身可读）。

清单口径见 `docs/known_issues.md`「原生后端未支持语句类型清单」。
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_CODEGEN_TYPED = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'llvm', 'codegen_typed.py')


# ----------------------------------------------------------------------
# 正跑：未支持语句必须炸，且文案指名道姓
# ----------------------------------------------------------------------

# 每条：(用例名, 源码, 文案里必须出现的语句类型名)
# 「文案里的类型名」是**实测**取的，不是照 v3 节点名想当然：
#   `外层` 只能出现在嵌套段落里，而嵌套段落本身原生就不支持，所以先撞上
#   `SegmentDefinition`——报的是真正拦下它的那一层，不是 `ScopeDeclStmt`。
_拒绝用例 = [
    (
        '全局',
        '设 计数 为 0。\n'
        '段落 加一()：\n'
        '  全局 计数。\n'
        '  设 计数 为 计数 加 1。\n'
        '加一()。\n',
        'ScopeDeclStmt',
    ),
    (
        '外层',
        '段落 甲()：\n'
        '  设 计数 为 0\n'
        '  段落 乙()：\n'
        '    外层 计数。\n'
        '  乙()。\n'
        '甲()。\n',
        'SegmentDefinition',
    ),
    (
        '生成',
        '段落 甲()：\n'
        '  生成 1。\n'
        '甲()。\n',
        'YieldStmt',
    ),
    (
        '断言',
        '断言 1 等于 1。\n',
        'AssertStmt',
    ),
    (
        '类型别名',
        '类型 甲 = 整数。\n'
        '设 乙 为 1。\n',
        'TypeAlias',
    ),
    (
        '嵌套类',
        '类 甲：\n'
        '  类 丁：\n'
        '    属性 戊。\n'
        '    构造 接收 戊：\n'
        '      己戊 为 戊。\n'
        '  属性 乙。\n'
        '  构造：\n'
        '    己乙 为 1。\n'
        '\n'
        '设 己 为 甲.丁(2)。\n'
        '打印 己.戊。\n',
        'ClassDefinitionWithNested',
    ),
]


@pytest.mark.parametrize('名称, 源码, 类型名', _拒绝用例,
                         ids=[c[0] for c in _拒绝用例])
def test_未支持语句必须抛错且文案含语句名(名称, 源码, 类型名):
    with pytest.raises(NotImplementedError) as ei:
        compile_source_typed(源码)
    文案 = str(ei.value)
    assert 类型名 in 文案, f'{名称}：文案没点明语句类型（{类型名}），实际是：{文案}'
    # 光有类型名不够——用户还得知道往哪走。
    assert '转译后端' in 文案, f'{名称}：文案没给出可走的后端，实际是：{文案}'


# ----------------------------------------------------------------------
# 反跑护栏：已支持语句必须仍然编得出来
# ----------------------------------------------------------------------

_支持用例 = [
    ('赋值', '设 甲 为 1。\n打印 甲。\n'),
    ('如果', '设 甲 为 1。\n如果 甲 等于 1：\n  打印 "对"。\n'),
    ('遍历', '遍历 甲 于 列(1, 2)：\n  打印 甲。\n'),
    ('返回', '段落 甲()：\n  返回 3。\n打印 甲()。\n'),
    ('四者同篇',
     '设 甲 为 1。\n'
     '如果 甲 等于 1：\n'
     '  打印 "对"。\n'
     '遍历 乙 于 列(1, 2)：\n'
     '  打印 乙。\n'
     '段落 丙()：\n'
     '  返回 3。\n'
     '打印 丙()。\n'),
]


@pytest.mark.parametrize('名称, 源码', _支持用例, ids=[c[0] for c in _支持用例])
def test_已支持语句仍不抛(名称, 源码):
    ir = compile_source_typed(源码)
    assert len(ir) > 1000, f'{名称}：IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, f'{名称}：IR 里残留了适配层的 <unknown 伪装'


# ----------------------------------------------------------------------
# 静态断言：兜底与拆伪装两段代码本身还在
# ----------------------------------------------------------------------

def _codegen_源码():
    with open(_CODEGEN_TYPED, encoding='utf-8') as f:
        return f.read()


def test_分派链尾有兜底():
    """`_gen_statement` 的 isinstance 链必须以 else + 拒绝收尾。"""
    src = _codegen_源码()
    i = src.find('def _gen_statement(self, stmt):')
    assert i > 0, '找不到 _gen_statement'
    j = src.find('\n    def ', i + 10)
    body = src[i:j if j > 0 else len(src)]
    assert re.search(r'\n\s{8}else:\n(?:\s*#[^\n]*\n)*\s*self\._reject_unsupported_stmt\(',
                     body), '分派链尾的 else 兜底不见了'


def test_适配层伪装会被拆开():
    """`<unknown:XXX>` 必须在 ExpressionStatement 分支里被识破。"""
    src = _codegen_源码()
    assert '_ADAPTER_UNKNOWN_PREFIX' in src
    i = src.find('elif isinstance(stmt, ast.ExpressionStatement):')
    assert i > 0, '找不到 ExpressionStatement 分支'
    seg = src[i:i + 1200]
    assert '_ADAPTER_UNKNOWN_PREFIX' in seg and '_reject_unsupported_stmt' in seg, \
        'ExpressionStatement 分支里拆伪装那段不见了'
