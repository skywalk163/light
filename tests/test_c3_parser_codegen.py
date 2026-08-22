# -*- coding: utf-8 -*-
"""任务 C3-6 / C3-7：语法坑指路 + 异步文件原语编译期报错。

· C3-6：`对于 每个 X 在 [...]` 从未被文档承诺过（口径 9）——parser 必须给指路
  文案（「遍历 X 于 表：」），而不是把用户引到「无法识别的语法元素」。
· C3-7：`异步读取文件/异步写入文件/异步追加文件` 只有词法名没有实现（真实现只在
  stdlib/lightpub/异步运行时.py，stdlib/ 是别人的地盘）。选方案 B：编译期报错 +
  指路同步替代，不许静默编译成功 → 运行期 NameError。

两处都是 parser/codegen 级别，不需要 LLVM 运行时目标码，做成轻量用例。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator, CodeGenError  # noqa: E402

_指路片段 = '「遍历 X 于 表：」'
_介词说明 = '推导式（列表/字典）的介词是「之/在」，遍历语句的介词是「于」'


# =============================================================================
# C3-6：`对于 … 在 …` 语法坑
# =============================================================================

@pytest.mark.parametrize('源码', [
    '对于 每个 i 在 [1, 2, 3]：\n  打印 i。\n',
    '对于 i 在 [1, 2, 3]：\n  打印 i。\n',
], ids=['对于-每个', '对于-不带每个'])
def test_对于在不是遍历写法要指路(源码):
    with pytest.raises(Exception) as ei:
        LightParser().parse(源码)
    文案 = str(ei.value)
    assert _指路片段 in 文案, f'没指到「遍历 X 于 表」，实际是：{文案[:200]}'
    assert _介词说明 in 文案, f'没把两套介词并列写明白，实际是：{文案[:200]}'


def test_遍历写法仍然可用():
    """指路不破坏既有正确写法。"""
    src = '设 和 为 0。\n遍历 甲 于 [1, 2, 3]：\n  和 为 和 加 甲。\n打印 和。\n'
    module = LightParser().parse(src)
    py = PythonCodeGenerator().generate(module)
    ns = {}
    exec(compile(py, '<c3-foreach>', 'exec'), ns)
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(py, ns)
    assert buf.getvalue().strip() == '6'


# =============================================================================
# C3-7：异步文件原语编译期报错
# =============================================================================

@pytest.mark.parametrize('原语', ['异步读取文件', '异步写入文件', '异步追加文件'])
def test_异步文件原语编译期报错并指路(原语):
    src = f'设 内容 为 {原语}("a")。\n打印 内容。\n'
    module = LightParser().parse(src)
    with pytest.raises(CodeGenError) as ei:
        PythonCodeGenerator().generate(module)
    文案 = str(ei.value)
    assert 原语 in 文案, f'没点出原语名，实际是：{文案}'
    assert '读取文件 / 写入文件 / 追加文件' in 文案, f'没指到同步替代，实际是：{文案}'


def test_同步文件原语不受影响():
    """编译期报错不能误伤同步读取/写入。"""
    for 原语, 实参 in [('读取文件', '"a"'), ('写入文件', '"a", "hi"')]:
        src = f'设 内容 为 {原语}({实参})。\n打印 内容。\n'
        module = LightParser().parse(src)
        py = PythonCodeGenerator().generate(module)
        assert '异步' not in py, f'同步 {原语} 被误伤成了异步路径: {py}'
