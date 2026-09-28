# -*- coding: utf-8 -*-
"""LP-D-013 回归：单字关键字被「设」声明后可作标识符（成员访问基名等）。

缺陷回顾
--------
`设 出 为 []` 本身正常，但随后 `出.追加(1)` 报「无法识别的语法元素：'.'」；
`设 跳过 为 []` 后 `跳过.追加(1)` 同例。
根因：单字关键字（出/跳过/...）在语句起始位发 KEYWORD，
没有像「声明过的动词名」那样被重分类为 IDENTIFIER，
于是导出语句 / continue 语句解析器接管并撞上 '.'。

修复口径（任务书 验收 2a / 3）
-----------------------------
1. 被 `设 X 为 ...` 声明过的单字关键字（出/跳过）在标识符位置重分类为
   IDENTIFIER（tokenize 出口后置重分类），可作成员访问基名：`出.追加(1)` 正常解析；
2. 未声明而误用（`出.追加(1)` 但无 `设 出`）时，编译期给明确中文报错，
   不再报英文「无法识别的语法元素：'.'」。

反跑判据（先红后绿）
--------------------
· 撤掉 lexer.py 出口的 `_lpd013_010_reclassify_declared_keywords` → 用例 1/2 变红
  （出/跳过 仍是 KEYWORD，'.' 报错）；
· 撤掉未声明诊断分支 → 用例 3/4 变红（又回英文 '.' 报错）。
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

from lexer import Lexer, LexerError  # noqa: E402
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
    namespace = {'_light_builtin': builtin, '__name__': '_lpd013_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd013>', 'exec'), namespace)
    return buf.getvalue(), py_code


def _unified_compile_and_run(source: str):
    import contextlib
    result = LightCompiler().compile(source)
    py_code = UnifiedCodeGenerator().generate(result['ast'])
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd013_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd013>', 'exec'), namespace)
    return buf.getvalue(), py_code


# ── 用例源：声明过的单字关键字作成员访问基名 ──────────────────────────

_声明的出_成员访问 = (
    "段落 主:\n"
    "  设 出 为 []\n"
    "  出.追加(1)\n"
    "  打印 字符串(出[0])\n"
    "\n"
    "主()\n"
)

_声明的跳过_成员访问 = (
    "段落 主:\n"
    "  设 跳过 为 []\n"
    "  跳过.追加(1)\n"
    "  打印 字符串(跳过[0])\n"
    "\n"
    "主()\n"
)

# ── 用例源：未声明即误用的诊断（期望编译期中文报错） ──────────────────

_未声明的出 = "段落 主:\n  出.追加(1)\n\n主()\n"
_未声明的跳过 = "段落 主:\n  跳过.追加(1)\n\n主()\n"


class Test设声明单字关键字后作标识符:
    """验收 1 前半：声明过的 出/跳过 可作成员访问基名（双腿）。"""

    def test_legacy后端_出声明的可成员访问(self):
        out, py = _legacy_compile_and_run(_声明的出_成员访问)
        assert out.strip() == '1'
        assert '出.append(1)' in py  # 出 保持标识符原样，仅 追加→append 映射

    def test_unified后端_出声明的可成员访问(self):
        out, _py = _unified_compile_and_run(_声明的出_成员访问)
        assert out.strip() == '1'

    def test_legacy后端_跳过的可成员访问(self):
        out, py = _legacy_compile_and_run(_声明的跳过_成员访问)
        assert out.strip() == '1'
        assert '跳过.append(1)' in py

    def test_token流_声明过的单字关键字为IDENTIFIER(self):
        """词法层断言：声明的 出/跳过 在成员访问位重分类为 IDENTIFIER；
        声明位（设 X 为）保持原类型——出 本就发 IDENTIFIER（L-046），
        跳过 声明位是 KEYWORD（parser 的设 目标位接受 KEYWORD）。"""
        for src in (_声明的出_成员访问, _声明的跳过_成员访问):
            toks = Lexer().tokenize(src)
            vals = [t.value for t in toks if t.type.name == 'IDENTIFIER']
            assert ('出' in vals) or ('跳过' in vals)
            # 成员访问位（DOT 前）不得再有 KEYWORD 出/跳过
            for i, t in enumerate(toks):
                if t.type.name == 'KEYWORD' and t.value in ('出', '跳过'):
                    nxt = toks[i + 1] if i + 1 < len(toks) else None
                    assert not (nxt and nxt.type.name == 'DOT')


class Test未声明误用单字关键字:
    """验收 3：未声明而误用给明确中文报错，不再报英文 '.'。"""

    def test_未声明的出_中文诊断(self):
        with pytest.raises(LexerError) as ei:
            Lexer().tokenize(_未声明的出)
        msg = str(ei.value)
        assert '出' in msg
        assert '设 出' in msg  # 给出声明指引
        assert "'.'" not in msg  # 不再报英文点号

    def test_未声明的跳过_中文诊断(self):
        with pytest.raises(LexerError) as ei:
            Lexer().tokenize(_未声明的跳过)
        msg = str(ei.value)
        assert '跳过' in msg
        assert '设 跳过' in msg
        assert "'.'" not in msg

    def test_token流_未声明不重分类(self):
        """未声明的 出/跳过 保持 KEYWORD（诊断由本轮 lexer 出口守卫抛出）。"""
        with pytest.raises(LexerError):
            Lexer().tokenize(_未声明的出)