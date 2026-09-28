# -*- coding: utf-8 -*-
"""LP-D-003 回归：中文数字作标识符（词法/标识符诊断，LP-D 批次 路1）。

缺陷回顾
--------
中文数字（如 `六`）被词法当成整数字面量 6：
  · 未声明就当下标名用（`六["级别"]`）→ 静默编成 `6["级别"]`，编译期零提示，
    运行期才报英文 'int' object is not subscriptable 且行号对不上源码；
  · 已声明的 `六` 在 legacy src 后端（light run 生产路径）读取位仍被
    code_generator 的中文数字映射打回 `6`（unified 后端无此映射，双后端分叉）。

修复口径（任务书 路1 验收 1）
--------------------------
1. 声明过的中文数字变量名可正常下标访问（双腿：legacy PythonCodeGenerator +
   UnifiedCodeGenerator 产物都要对）；
2. 未声明而直接当下标名用时，编译期给明确中文报错（不再放行到运行期）。

反跑判据
--------
· 撤掉 lexer.py `_lpd003_check_cn_num_subscript` → 用例 2 变红（静默通过）；
· 撤掉 code_generator.py Identifier 分支的声明名豁免（改回无条件映射）→
  用例 1 / 3 变红（`六` 读取位又变 `6`）。
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
from keywords import reserved_word_identifier_error  # noqa: E402


# ── 运行辅助：legacy src 后端（light run 生产路径）────────────────────

def _legacy_compile_and_run(source: str):
    """LightParser + PythonCodeGenerator（legacy src 后端）编译并执行。"""
    import contextlib
    module = LightParser().parse(source)
    py_code = PythonCodeGenerator().generate(module, is_main=False)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd003>', 'exec'), namespace)
    return buf.getvalue(), py_code


def _unified_compile_and_run(source: str):
    """LightCompiler + UnifiedCodeGenerator（unified 后端）编译并执行。"""
    import contextlib
    result = LightCompiler().compile(source)
    py_code = UnifiedCodeGenerator().generate(result['ast'])
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd003>', 'exec'), namespace)
    return buf.getvalue(), py_code


_声明后下标 = (
    "段落 主:\n"
    "  设 六 为 [\"级别\": 6]\n"
    "  打印 字符串(六[\"级别\"])\n"
    "\n"
    "主()\n"
)


class Test声明过的中文数字:
    """验收 1 前半：声明过的中文数字变量名可正常下标访问。"""

    def test_legacy后端_声明过可下标读(self):
        out, py = _legacy_compile_and_run(_声明后下标)
        assert out.strip() == '6'
        # 产物里不得再把声明过的 六 打回数字
        assert '6["级别"]' not in py
        assert '六["级别"]' in py

    def test_unified后端_声明过可下标读(self):
        out, _py = _unified_compile_and_run(_声明后下标)
        assert out.strip() == '6'

    def test_legacy后端_下标写与算术更新(self):
        src = (
            "段落 主:\n"
            "  设 六 为 5\n"
            "  设 六 为 六 + 1\n"
            "  打印 字符串(六)\n"
            "\n"
            "主()\n"
        )
        out, _py = _legacy_compile_and_run(src)
        assert out.strip() == '6'

    def test_codegen_声明名豁免_反跑哨兵(self):
        """反跑判据：撤掉 code_generator.py Identifier 分支的声明名豁免 → 红。

        直接驱动 _generate_expr(Identifier('六'))：六 在局部变量集里时
        必须按名字发射（返回 '六'），不得返回 '6'。
        """
        from ast_nodes_v3 import Identifier
        gen = PythonCodeGenerator()
        gen._local_variables.add('六')
        assert gen._generate_expr(Identifier('六')) == '六'
        # 未声明的中文数字 Identifier（防御兜底路径）仍映射为数字
        gen2 = PythonCodeGenerator()
        assert gen2._generate_expr(Identifier('六')) == '6'


class Test未声明中文数字下标:
    """验收 1 后半：未声明就当下标名用 → 编译期明确中文报错。"""

    def test_未声明下标名_编译期中文报错(self):
        src = "段落 主:\n  打印 字符串(六[\"级别\"])\n\n主()\n"
        with pytest.raises(LexerError) as ei:
            Lexer().tokenize(src)
        msg = str(ei.value)
        assert '中文数字' in msg
        assert '六' in msg
        assert '设 六' in msg  # 给出声明指引

    def test_未声明下标名_不再漏到运行期(self):
        """老缺陷形态：编译只给 SyntaxWarning、运行期 int subscriptable。
        修复后词法阶段必须直接拦截。"""
        src = "设 d 为 [\"级别\": 6]\n打印 字符串(七[\"级别\"])\n"
        with pytest.raises(LexerError):
            Lexer().tokenize(src)

    def test_声明过的中文数字不触发守卫(self):
        """声明（设/参数）过的中文数字走 IDENTIFIER 重分类，不得误报。"""
        src_ok1 = "设 六 为 [\"级别\": 6]\n打印 字符串(六[\"级别\"])\n"
        toks = Lexer().tokenize(src_ok1)  # 不应抛
        assert any(t.type.name == 'IDENTIFIER' and t.value == '六' for t in toks)
        src_ok2 = "段落 取级别(六):\n  返回 六[\"级别\"]\n"
        Lexer().tokenize(src_ok2)  # 不应抛

    def test_保留字诊断表齐全(self):
        # 路1 附带：诊断取 keywords 表而非硬编码
        for w in ('尝试', '捕获', '如果', '段落', '返回', '设', '导入',
                  '导出', '类', '属性', '抛出', '跳出', '遍历', '当'):
            assert w in reserved_word_identifier_error(w)
