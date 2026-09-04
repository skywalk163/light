# -*- coding: utf-8 -*-
"""
L-054：函数调用实参的嵌套字典/列表字面量内字符串含 \n 转义，
      不再把该语句之后的同级语句降级为模块级代码（def 主 提前结束）。

背景：单层字符串字面量的 \n（如 "a.ts:1:1\na.ts:5:3"）不受影响，
      仅嵌套字面量内的 \n 曾触发。lexer 的 _tokenize_string 把 \n 转义
      翻译成真实换行字符存入 STRING 值；若该换行参与缩进计算/块状态判定，
      该行之后的同级语句会被误判为模块级（函数内变量未定义 → 名称错误）。
      修复（L-051 同族机制）后：
        ① _tokenize_string 整体消费 \n 转义，不进入 lexer 换行/缩进逻辑；
        ② bracket_stack（L-051）抑制字面量括号内真实换行（多行字面量）。

回归锁定：
- 单行嵌套字典实参 + \n 转义：字符串值保留真实换行、后续同级语句保持段内；
- 多行嵌套字典实参 + \n 转义：缩进层级不破坏（L-051 同族）；
- 生成代码结构：嵌套字面量语句之后无模块级（0 缩进）的同级语句。

运行方式：pytest tests/unit/test_L054_nested_literal_newline.py -v
"""

import io
import os
import re
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


# 单行嵌套字典实参：格式化悬停({ "contents": "```ts\nx: number\n```" }, …)
_HOVER = ('段落 格式化悬停(内容, 上限):\n'
          '  返回 内容["contents"]\n')


class TestL054NestedLiteralNewline:
    def test_call_arg_nested_dict_newline_single_line(self):
        """单行嵌套字典实参 + \\n 转义：值保留真实换行、后续同级语句保持段内"""
        code = (_HOVER +
                '段落 主：\n'
                '  设 截4 为 格式化悬停({ "contents": "```ts\\nx: number\\n```" }, 16000)。\n'
                '  设 截5 为 截4。\n'
                '  写 转字符串(字符串长度(截5))。\n'
                '  打印 "后续语句"。\n'
                '主()。\n')
        out = _run(code)
        # 字符串长度("```ts\nx: number\n```") == 19；写(不换行)+打印(换行)
        assert out.strip() == '19后续语句'

    def test_call_arg_nested_dict_newline_value_preserved(self):
        """嵌套字面量内 \\n 转义被翻译成真实换行（非字面反斜杠 n）"""
        code = (_HOVER +
                '段落 主：\n'
                '  设 截4 为 格式化悬停({ "contents": "a\\nb" }, 16000)。\n'
                '  设 截5 为 截4。\n'
                '  写 截5。\n'
                '主()。\n')
        out = _run(code)
        # 值含真实换行 → "a\nb"（写 不追加换行）；若被当字面 "a\nb"(反斜杠) 则单行
        assert out == 'a\nb'

    def test_call_arg_nested_dict_newline_multi_line(self):
        """多行嵌套字典实参 + \\n 转义：bracket_stack 抑制字面量内换行，后续块不破坏"""
        code = (_HOVER +
                '段落 主：\n'
                '  设 截4 为 格式化悬停({\n'
                '    "contents": "```ts\\nx: number\\n```"\n'
                '  }, 16000)。\n'
                '  设 截5 为 截4。\n'
                '  写 转字符串(字符串长度(截5))。\n'
                '  打印 "后续语句"。\n'
                '主()。\n')
        out = _run(code)
        assert out.strip() == '19后续语句'

    def test_generated_body_keeps_siblings_in_def(self):
        """生成代码结构：嵌套字面量 \\n 语句之后的同级语句不得降级到模块级（0 缩进）"""
        code = ('段落 主：\n'
                '  设 截4 为 格式化悬停({ "contents": "a\\nb" }, 1)。\n'
                '  设 截5 为 截4。\n'
                '  写 转字符串(字符串长度(截5))。\n'
                '主()。\n')
        py_code = _compile(code)
        body = py_code.split('\n')
        idx = next(i for i, ln in enumerate(body) if re.match(r'^def 主\b', ln))
        degraded = []
        for i in range(idx + 1, len(body)):
            ln = body[i]
            if re.match(r'^def \S+', ln):
                break
            # 模块级「主()」是刻意调用，不算降级
            if re.match(r'^主\(\)', ln.strip()):
                continue
            if ln.strip() and not ln.startswith(' ') and not ln.startswith('#'):
                degraded.append((i + 1, ln.strip()))
        assert not degraded, f'同级语句被降级到模块级: {degraded}'
        # 段内变量赋值必须带 4 空格缩进
        assert any(ln.startswith('    截5 ') for ln in body[idx + 1:]), '截5 未保持在 def 主 体内'
