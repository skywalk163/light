# -*- coding: utf-8 -*-
"""
L-051 / L-052 / L-057 / L-064 已修复缺陷回归测试

- L-051：多行字典/列表字面量不再破坏后续块缩进（lexer 括号类型判定）。
- L-052：字符串字面量 `${标识符}` 不再被当插值（$ 前缀保护）。
- L-057：类方法体内 `己.能力["X"](实参)`（成员访问+下标+调用）正确调用
         函数值，不再静默返回函数对象（返回值/语句级/赋值三形态）。
- L-064：超长段落（>100 条语句）不再被错误截断到模块顶层——_parse_body
         上限从 100 提升并加位置推进兜底。

运行方式：pytest tests/unit/test_L051_L052_L057_L064.py -v
"""

import io
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile(code: str) -> str:
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        raise RuntimeError('解析失败: %s' % '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(ast)


def _run(code: str) -> str:
    py_code = _compile(code)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(py_code, '<light>', 'exec'), {'__name__': '__main__'})
        return sys.stdout.getvalue().replace('\r\n', '\n')
    finally:
        sys.stdout = old_stdout


# ===========================================================================
# L-051：多行字典/列表字面量不破坏后续块缩进
# ===========================================================================
class TestL051MultilineLiteral:
    def test_multiline_dict(self):
        code = ('段落 主：\n'
                '  设 录 为 {\n'
                '    "a": 1,\n'
                '    "b": 2\n'
                '  }。\n'
                '  写 转字符串(录["a"] + 录["b"])。\n'
                '  打印 "后续语句"。\n'
                '主()。\n')
        out = _run(code)
        # `写` 不换行，`打印` 换行：3 + 后续语句
        assert out.replace('\r\n', '\n') == '3后续语句\n'

    def test_multiline_list_in_loop(self):
        code = ('段落 主：\n'
                '  设 表 为 [\n'
                '    1,\n'
                '    2\n'
                '  ]。\n'
                '  设 和 为 0。\n'
                '  遍历 项 之 表：\n'
                '    和 加上 项。\n'
                '  写 转字符串(和)。\n'
                '主()。\n')
        out = _run(code)
        assert out.strip() == '3'


# ===========================================================================
# L-052：字符串字面量 ${标识符} 不插值
# ===========================================================================
class TestL052DollarBraceLiteral:
    def test_dollar_brace_literal(self):
        code = ('段落 主：\n'
                '  设 路径 为 "${CLAUDE_PLUGIN_ROOT}/x"。\n'
                '  写 路径。\n'
                '主()。\n')
        out = _run(code)
        assert out.strip() == '${CLAUDE_PLUGIN_ROOT}/x'


# ===========================================================================
# L-057：类方法体内 己.能力["X"](实参) 函数值调用
# ===========================================================================
class TestL057MemberSubscriptCall:
    _CLS = ('段落 翻倍 接收 x：\n'
            '  返回 x * 2。\n'
            '类 引擎：\n'
            '  属性 能力。\n'
            '  构造 接收 能力：\n'
            '    己.能力 为 能力。\n')

    def test_return_form(self):
        """返回值形态：返回 己.能力["翻倍"](21)"""
        code = (self._CLS +
                '  段落 执行：\n'
                '    返回 己.能力["翻倍"](21)。\n'
                '引擎 等于 新建 引擎({"翻倍": 翻倍})。\n'
                '写 转字符串(引擎.执行())。\n')
        out = _run(code)
        assert out.strip() == '42'

    def test_stmt_form(self):
        """语句级形态：己.能力["标记"]("跑起来了") 丢弃返回值"""
        code = ('段落 标记 接收 x：\n'
                '  写 转字符串(x)。\n'
                '类 引擎：\n'
                '  属性 能力。\n'
                '  构造 接收 能力：\n'
                '    己.能力 为 能力。\n'
                '  段落 跑：\n'
                '    己.能力["标记"]("跑起来了")。\n'
                '引擎 等于 新建 引擎({"标记": 标记})。\n'
                '引擎.跑()。\n')
        out = _run(code)
        assert out.strip() == '跑起来了'

    def test_assign_form(self):
        """赋值形态：设 结果 为 己.能力[键](10)"""
        code = (self._CLS +
                '  段落 执行 接收 键：\n'
                '    设 结果 为 己.能力[键](10)。\n'
                '    返回 结果。\n'
                '引擎 等于 新建 引擎({"翻倍": 翻倍})。\n'
                '写 转字符串(引擎.执行("翻倍"))。\n')
        out = _run(code)
        assert out.strip() == '20'


# ===========================================================================
# L-064：超长段落（>100 条语句）不再截断到模块顶层
# ===========================================================================
class TestL064LongParagraph:
    def test_100plus_statements_kept_in_body(self):
        """主程 105 条累加语句（原 100 上限会截断）——全部保持段内并正确执行"""
        lines = ['段落 主程：']
        lines.append('  设 累计 为 0。')
        for i in range(105):
            lines.append(f'  设 累计 为 累计 + {i}。')
        lines.append('  写 转字符串(累计)。')
        lines.append('主程()。')
        code = '\n'.join(lines) + '\n'
        out = _run(code)
        assert out.strip() == str(sum(range(105)))

    def test_generated_body_no_zero_indent(self):
        """生成代码中主程体内不得出现 0 缩进语句（缩进归零回归）"""
        lines = ['段落 主程：']
        lines.append('  设 累计 为 0。')
        for i in range(130):
            lines.append(f'  设 累计 为 累计 + {i}。')
        lines.append('  写 转字符串(累计)。')
        code = '\n'.join(lines) + '\n'
        py_code = _compile(code)
        body = py_code.split('\n')
        # 找 def 主程 之后到模块级 主程() 调用之前的主程体
        idx = next(i for i, l in enumerate(body) if l.startswith('def 主程'))
        # 主程体应有缩进（4 空格），紧随 def 主程 的语句若有 0 缩进即失败
        next_line = body[idx + 1]
        assert next_line.startswith(' '), f'主程体首条语句缩进归零: {next_line!r}'
