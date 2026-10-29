# -*- coding: utf-8 -*-
"""LH-22 / LH-18b / LH-12 定向用例（T-0198）。

三件事，各一组用例：

LH-22　括号**外**续行不成立，报错却指向「缩进不正确」（P1）
    缺陷：`打印 "a"` 换行后写 `    加上 "b"`，报的是「缩进不正确：这一行的缩进
    层级没有对应的语句块」——把人往缩进上引，对着改三遍缩进才会意识到是续行。
    本卡取任务卡期望方案 1：**上一行语法完整 + 本行以二元运算符开头 + 缩进更深**
    时自动续行（词法层不发射 NEWLINE，续行行前导缩进不进缩进栈）。
    方案 2（换一条「疑似续行」报错）作为续行前提不成立时的兜底：上一行没写完
    （`设 甲 为` + 缩进更深的 `加上 "b"`）时，报错文案必须点名「疑似续行」。

LH-18b　不支持反斜杠续行（P1）
    `设 乙 为 甲 加上 \\` + 换行 → 旧行为抛「意外的标记: 「\\」」+ 级联
    「缩进不正确」。现支持 `\\` + 行尾空白 + 换行的续行，`乙` 必须等于 "ab"。
    注意与字符串里的 `\\n` 转义是两件事：字符串转义一字未动（见
    test_字符串转义不受影响）。

LH-12　报错只给调用点，不给异常链（P2）
    跨模块异常时位置块高亮调用点、真因埋在消息体里。现在追加
    「异常链（抛出点 → 调用点）」，单帧报错不加任何输出。

反跑判据（改坏了会红）
· 删掉 lexer.tokenize 里的 `_line_ends_with_binary_op` 之外的**行首运算符续行**
  分支 → TestLH22括号外续行 全红；
· 删掉 `\\` 续行分支 → TestLH18b反斜杠续行 全红；
· 把 `_decascade_order` 退回 `errors[:MAX]` → TestLH22聚合报错 的乱序用例红；
· 删掉 format_error 里的 `_format_exception_chain` 调用 → TestLH12异常链 红。

运行方式：pytest tests/unit/test_LH22_续行.py -v
"""

import contextlib
import io
import os
import sys
import tempfile
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib"),
           os.path.join(_ROOT, "cli")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from parser_core import ParseError  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


# ── 运行辅助：编译 + exec，同时拿 stdout 和变量表 ────────────────────
def _compile(source: str) -> str:
    module = LightParser().parse(source)
    return PythonCodeGenerator().generate(module, is_main=False)


def _exec(source: str):
    """返回 (stdout, 命名空间)。命名空间用于直接断言变量值（如 `乙 == "ab"`）。"""
    py_code = _compile(source)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lh22_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lh22>', 'exec'), namespace)
    return buf.getvalue().replace('\r\n', '\n'), namespace


def _run(source: str) -> str:
    return _exec(source)[0]


class TestLH22括号外续行:
    """括号外的行首运算符续行：要么编译通过并拼对，要么报错点名「疑似续行」。"""

    def test_卡面原形_行首加上(self):
        src = '打印 "a"\n    加上 "b"\n'
        try:
            out = _run(src)
        except ParseError as exc:                      # 方案 2 兜底也必须成立
            assert '疑似续行' in str(exc), f'报错没指向续行：{exc}'
        else:
            assert out.strip() == 'ab'

    def test_段落体内行首运算符续行(self):
        src = ('段落 拼():\n'
               '  返回 "a"\n'
               '      加上 "b"\n'
               '\n'
               '打印 拼()\n')
        assert _run(src).strip() == 'ab'

    def test_连续三段续行(self):
        src = ('打印 "a"\n'
               '    加上 "b"\n'
               '    加上 "c"\n')
        assert _run(src).strip() == 'abc'

    def test_续行不打断块结构(self):
        """续行行的缩进不进缩进栈：后续语句必须仍留在函数体内。"""
        src = ('段落 主():\n'
               '  设 甲 为 "a"\n'
               '      加上 "b"\n'
               '  打印 甲\n'
               '  打印 "尾"\n'
               '\n'
               '主()\n')
        assert _run(src).splitlines() == ['ab', '尾']

    def test_续行行前注释与空行不中断(self):
        src = ('打印 "a"\n'
               '    # 注释行\n'
               '\n'
               '    加上 "b"\n')
        assert _run(src).strip() == 'ab'

    def test_上一行没写完时点名疑似续行(self):
        """续行前提不成立（上一行语法不完整）→ 必须说「疑似续行」而不是只说缩进。"""
        src = '设 甲 为\n    加上 "b"\n'
        with pytest.raises(ParseError) as ei:
            _compile(src)
        msg = str(ei.value)
        assert '疑似续行' in msg, msg
        assert '加上' in msg, msg

    def test_同级缩进不并入(self):
        """同级行是独立语句边界，不能被行首运算符续行吞掉。"""
        src = ('设 甲 为 1\n'
               '设 乙 为 2\n'
               '打印 甲\n'
               '打印 乙\n')
        assert _run(src).splitlines() == ['1', '2']


class TestLH22括号内回归:
    """括号内跨行本来就是合法语法，改动不得影响。"""

    def test_括号内多行表达式(self):
        src = '设 x 为 ("a" 加上\n   "b")\n打印 x\n'
        assert _run(src).strip() == 'ab'

    def test_括号内多行字典(self):
        src = ('设 表 为 ["甲": 1,\n'
               '        "乙": 2]\n'
               '打印 表["乙"]\n')
        assert _run(src).strip() == '2'

    def test_括号内行尾加号(self):
        src = '设 串 为 ("a" +\n        "b")\n打印 串\n'
        assert _run(src).strip() == 'ab'


class TestLH18b反斜杠续行:
    """`\\` + 行尾空白 + 换行 → 续行；`乙` 必须等于 "ab"。"""

    def test_反斜杠续行_变量值正确(self):
        src = ('设 甲 为 "a"\n'
               '设 乙 为 甲 加上 \\\n'
               '  "b"\n'
               '打印 乙\n')
        out, ns = _exec(src)
        assert ns.get('乙') == 'ab', f'乙={ns.get("乙")!r}'
        assert out.strip() == 'ab'

    def test_反斜杠续行_三段(self):
        src = ('设 甲 为 "a" 加上 \\\n'
               '  "b" 加上 \\\n'
               '  "c"\n'
               '打印 甲\n')
        out, ns = _exec(src)
        assert ns.get('甲') == 'abc'

    def test_反斜杠后续空行与注释行(self):
        src = ('设 甲 为 "a" 加上 \\\n'
               '\n'
               '  # 注释\n'
               '  "b"\n'
               '打印 甲\n')
        out, ns = _exec(src)
        assert ns.get('甲') == 'ab'

    def test_反斜杠续行不打断块结构(self):
        src = ('段落 f():\n'
               '  设 甲 为 "a" 加上 \\\n'
               '      "b"\n'
               '  返回 甲\n'
               '\n'
               '打印 f()\n'
               '打印 "尾"\n')
        assert _run(src).splitlines() == ['ab', '尾']

    def test_字符串转义不受影响(self):
        """`"a\\nb"` 里的 `\\n` 是字符串转义，绝不能被当成续行符。"""
        src = '设 甲 为 "a\\nb"\n打印 甲\n'
        assert _run(src) == 'a\nb\n'

    def test_注释里的反斜杠不当续行(self):
        src = ('设 甲 为 "a"\n'
               '# 注释 \\\n'
               '打印 甲\n')
        assert _run(src).strip() == 'a'

    def test_单行代码不受影响(self):
        src = '设 甲 为 "a" 加上 "b"\n打印 甲\n'
        assert _run(src).strip() == 'ab'


class TestLH22聚合报错:
    """聚合报错时第一条必须是真因，级联的「缩进不正确」不得排在前面。"""

    def test_级联回声位置无关地排到最后(self):
        """错误列表里回声在前、真因在后（恐慌模式恢复可能产生这种顺序），
        渲染时仍必须把真因放在「错误 1/2」。"""
        parser = LightParser()
        echo = ParseError('缩进不正确：这一行的缩进层级没有对应的语句块。', 3, 1)
        real = ParseError('意外的标记: 反斜杠续行', 2, 12)
        agg = parser._build_aggregate_error([echo, real])
        text = str(agg)
        first_block = text.split('错误 2/2')[0]
        assert '意外的标记' in first_block, text
        assert '缩进不正确' not in first_block, text
        # all_errors 保持原始顺序（工具链口径不变）
        assert agg.all_errors[0] is echo

    def test_上一行无错时缩进错误仍是第一条(self):
        """独立的缩进错误（上一行没有任何错误）不能被降级——它不是回声。"""
        parser = LightParser()
        indent_err = ParseError('缩进不正确：这一行的缩进层级没有对应的语句块。', 2, 1)
        later = ParseError('意外的标记: ）', 5, 9)
        text = str(parser._build_aggregate_error([indent_err, later]))
        assert '缩进不正确' in text.split('错误 2/2')[0], text

    def test_真实两错聚合第一条不是缩进回声(self):
        src = '设 甲 为\n    加上 "b"\n'
        with pytest.raises(ParseError) as ei:
            _compile(src)
        errs = getattr(ei.value, 'all_errors', None) or [ei.value]
        if len(errs) < 2:
            pytest.skip('本例只产生 1 条错误，聚合顺序无意义')
        assert '缩进不正确' not in str(errs[0])


class _RunCtx:
    """跑一个临时光明项目，抓运行期异常并格式化（沿用 L-093 的口径）。"""

    def __init__(self, files):
        self.tmp = tempfile.mkdtemp(prefix='lh12_')
        for rel, text in files.items():
            path = os.path.join(self.tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        self.entry = os.path.join(self.tmp, '主.light')

    def formatted_error(self):
        from cli.light import _run_src
        from enhanced_errors import ErrorFormatter
        src_main = open(self.entry, encoding='utf-8').read()
        try:
            _run_src(src_main, file_path=self.entry)
        except Exception as e:  # noqa: BLE001
            return ErrorFormatter().format_error(
                src_main, e,
                py_code=getattr(e, '_light_py_code', None),
                file_path=self.entry)
        raise AssertionError('预期运行期异常，但程序正常结束')

    def cleanup(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestLH12异常链:
    """报错必须带最短异常链（抛出点 → … → 调用点），而不是只有调用点。"""

    def test_跨模块异常带最短链(self):
        ctx = _RunCtx({
            '主.light': '从 依赖 导入 会炸。\n会炸()。\n',
            '依赖.light': '段落 会炸：\n  返回 1/0\n结束\n',
        })
        try:
            out = ctx.formatted_error()
            assert '异常链（抛出点 → 调用点）' in out, out
            chain_line = [ln for ln in out.splitlines() if '异常链（抛出点 → 调用点）' in ln][0]
            # 抛出点（依赖.light:2）与调用点（主.light:2）都必须在这条链上
            assert '依赖.light:2' in chain_line, chain_line
            assert '主.light:2' in chain_line, chain_line
            # 顺序必须是「抛出点 → 调用点」，不能反过来
            assert chain_line.index('依赖.light:2') < chain_line.index('主.light:2'), chain_line
        finally:
            ctx.cleanup()

    def test_单帧异常不额外输出链(self):
        ctx = _RunCtx({
            '主.light': '设 x 为 1/0。\n输出(x)。\n',
        })
        try:
            out = ctx.formatted_error()
            assert '异常链' not in out, out
        finally:
            ctx.cleanup()
