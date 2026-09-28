# -*- coding: utf-8 -*-
"""LP-D-010 回归：遍历循环变量名在循环体内可作函数调用。

缺陷回顾
--------
`遍历 回调 之 表:` 循环体内 `回调("a")` 报「『回调』是保留关键字，不能直接作为
语句开头」+「缩进不正确」。
根因：循环变量名（回调 是 FFI 关键字）在循环体内仍发 KEYWORD，
没有被像「声明过的动词名」那样重分类为可调用标识符。

修复口径（任务书 验收 2b）
-------------------------
遍历/遍 头部的循环变量名（含 回调 等关键字名）在 token 流层面重分类为
IDENTIFIER（tokenize 出口后置重分类），循环体内 `回调("a")` 正常解析执行。

反跑判据（先红后绿）
--------------------
· 撤掉 lexer.py 出口 `_lpd013_010_reclassify_declared_keywords` 中的遍历变量
  收集 → 本文件在修复前必然失败（循环体内 KEYWORD(回调) 报语句开头错误）。
"""
import io
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from lexer import Lexer  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
from compiler import LightCompiler  # noqa: E402
from code_generator_unified import UnifiedCodeGenerator  # noqa: E402


# ── 运行辅助：双腿（legacy src 后端 / unified 后端）───────────────────

def _legacy_compile_and_run(source: str):
    import contextlib
    module = LightParser().parse(source)
    py_code = PythonCodeGenerator().generate(module, is_main=False)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd010_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd010>', 'exec'), namespace)
    return buf.getvalue(), py_code


def _unified_compile_and_run(source: str):
    import contextlib
    result = LightCompiler().compile(source)
    py_code = UnifiedCodeGenerator().generate(result['ast'])
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd010_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd010>', 'exec'), namespace)
    return buf.getvalue(), py_code


# ── 用例源：遍历 回调 之 表 + 循环体内 回调("a") 调用 ──────────────────

_遍历回调作循环变量 = (
    "段落 回应(值):\n"
    "  返回 值\n"
    "\n"
    "段落 主:\n"
    "  设 表 为 [回应]\n"
    "  遍历 回调 之 表:\n"
    "    打印 字符串(回调(\"a\"))\n"
    "\n"
    "主()\n"
)


class Test遍历循环变量可调用:
    """验收 2b：遍历循环变量名（FFI 关键字 回调）在循环体内可作函数调用（双腿）。"""

    def test_legacy后端_循环体内回调可调用(self):
        out, py = _legacy_compile_and_run(_遍历回调作循环变量)
        assert out.strip() == 'a'
        assert '回调("a")' in py  # 回调 保持标识符原样，不被改写

    def test_unified后端_循环体内回调可调用(self):
        out, _py = _unified_compile_and_run(_遍历回调作循环变量)
        assert out.strip() == 'a'

    def test_token流_循环体内回调为IDENTIFIER(self):
        """词法层断言：循环体内调用位 回调 已重分类为 IDENTIFIER；
        头部声明位保持 KEYWORD（parser 的 _scan_foreach_names 接受 KEYWORD 名）。"""
        toks = Lexer().tokenize(_遍历回调作循环变量)
        for i, t in enumerate(toks):
            if t.type.name == 'KEYWORD' and t.value == '回调':
                # 头部声明位：其后应为连接词（之）；
                # 循环体内调用位（LPAREN 前）不得再是 KEYWORD
                nxt = toks[i + 1] if i + 1 < len(toks) else None
                assert not (nxt and nxt.type.name == 'LPAREN')
        vals = [t.value for t in toks if t.type.name == 'IDENTIFIER']
        assert vals.count('回调') >= 1  # 循环体内调用位已重分类