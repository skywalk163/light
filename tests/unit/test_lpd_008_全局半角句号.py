# -*- coding: utf-8 -*-
"""LP-D-008 回归：`全局` 声明用半角句号时给出全角句号提示（LP-D 批次 路2）。

缺陷回顾
--------
`全局 队列.`（半角句号）被解析器当成成员访问，报
「期望成员名，但得到 「\\n」」，建议完全不提"该用全角句号"。

修复口径（任务书 路2 验收 2）
--------------------------
`全局 名.`（半角 DOT 紧跟名单之后）→ 明确提示
「全局 声明要用全角句号「。」结束，不能用半角点号「.」」。
全角 `。` 行为不变；`全局 = 1。` / `全局(甲)` 等既有合法写法不受影响
（范式 A 口径：只拦「声明词 + 名单 + 半角点号」这一种误写形态）。

反跑判据
--------
· 撤掉 parser_stmt.py `_lpd008_diag_half_period` 及其调用点 → 用例 1 变红
  （回到「期望成员名」误导报错）。
"""
import io
import os
import sys
import types
import contextlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from parser_core import ParseError  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _run(source: str) -> str:
    module = LightParser().parse(source)
    py_code = PythonCodeGenerator().generate(module, is_main=False)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lpd_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lpd008>', 'exec'), namespace)
    return buf.getvalue()


class Test半角句号报错:
    def test_全局后半角句号_给全角提示(self):
        src = (
            "段落 主:\n"
            "  全局 队列.\n"
            "  队列 为 []\n"
            "  打印 \"ok\"\n"
            "\n"
            "主()\n"
        )
        with pytest.raises(ParseError) as ei:
            LightParser().parse(src)
        msg = str(ei.value)
        assert '全角句号' in msg
        assert '「。」' in msg
        assert '成员名' not in msg   # 不得再给误导性的成员访问报错

    def test_多名字半角句号_同样提示(self):
        src = "段落 主:\n  全局 队列, 缓存.\n  打印 \"ok\"\n\n主()\n"
        with pytest.raises(ParseError) as ei:
            LightParser().parse(src)
        assert '全角句号' in str(ei.value)


class Test对照_既有写法不受影响:
    def test_全角句号仍正常(self):
        src = (
            "段落 主:\n"
            "  全局 计数。\n"
            "  计数 为 0\n"
            "  打印 字符串(计数)\n"
            "\n"
            "主()\n"
        )
        assert _run(src).strip() == '0'

    def test_全角句号最简形态(self):
        src = "段落 主:\n  全局 队列。\n  队列 为 []\n  打印 \"ok\"\n\n主()\n"
        assert _run(src).strip() == 'ok'

    def test_全局作赋值目标_不被误拦(self):
        """范式 A 既有合法写法：`全局 = 1。` 走赋值分支，不得报全角句号错。"""
        src = "段落 主:\n  全局 = 1\n  打印 字符串(全局)\n\n主()\n"
        assert _run(src).strip() == '1'

    def test_全局作普通标识符_不被误拦(self):
        """`全局` 在表达式的其它位置（裸引用）按普通标识符处理，
        不得被本修的半角句号诊断拦下。"""
        src = "段落 主:\n  设 甲 为 1\n  设 结果 为 全局\n  打印 字符串(甲)\n\n主()\n"
        # 解析必须通过（运行期 NameError 与本修无关，此处只解析不执行）
        LightParser().parse(src)
