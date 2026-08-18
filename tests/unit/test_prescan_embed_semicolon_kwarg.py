# -*- coding: utf-8 -*-
"""v7 单 28 回归用例（族 2）：五处独立缺陷的平台/版本无关守卫。

对应 examples/E阶段/E4_L4_沙箱隔离验证.light、examples/L3_domain/all_in_one_L3_demo.light、
examples/F阶段_标准库增强/F3_段言侧三个增强模块示例.light 的打红根因：

1. 词法预扫描（_scan_user_definitions）是**裸预扫描**，不跳过注释也不跳过字符串。
   `定义` 分支把其后标识符收进 user_definitions，若该集合里混入真关键字，
   后续该关键字会被降级为 IDENTIFIER。E4 里注释 `自定义段。` 命中 `定义`→收走 `段`，
   使 `段 主():` 的 `段` 被降级，整块编译失败。修复：`定义`/`设` 两个分支都必须
   加关键字闸门 `if name not in ALL_KEYWORDS`。

2. 嵌入块（引 Python: … 结束引）被整体吞掉时，词法器只前移 `i` 不前移 `line`，
   导致其后所有 token 的行号偏移（偏移量 = 嵌入块行数）。错误定位报在错误的行上。
   修复：吞掉嵌入块时按吞掉内容里的 `\\n` 数量同步前移 line/col。

3. `;`/`；` 作为语句分隔符（同一行写多条语句），文档承诺
   （docs/段言-完整规范文档.md 语句分隔一节）。此前只有 C 风格 `循环(init;cond;incr)`
   在 `_parse_c_for_loop` 里显式吃掉分号；顶层/段体/花括号体的语句序列循环、
   以及 `打印 a; 打印 b` 这类变参动词的无括号取参循环都不认分号。
   修复：在语句序列循环与取参循环里遇 SEMICOLON 跳过/断开；C 风格循环因先吃
   LPAREN 再显式 consume 分号，与之隔离，不受影响。

4. 括号调用里的命名实参 `f(x, 步长天=1)`：`_try_parse_keyword_arg` 已存在且接到
   arity 路径与后缀链，唯独 `_collect_single_arg` 的括号分支漏接，导致 `名=值`
   在括号里解析失败。修复：括号分支在 `_parse_comparison` 之前先试 keyword-arg。

5. INDENT/DEDENT 落到语句解析的错误分支时，旧实现把缩进宽度整数（如 '4'/'8'）
   当作「意外的标记」打印，语义无意义。修复：加 INDENT/DEDENT 分支给出
   「缩进不正确」这类可读信息。

判据全部走「词法器 token 类型/行号」或「解析 .light 看是否成树/报错文案」，
不依赖具体 Python 版本或平台，也不依赖任何第三方科学库。
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser                        # noqa: E402
from lexer import Lexer                                        # noqa: E402


def _parse(code):
    p = LightParser()
    tree = p.parse(code)
    return tree, list(getattr(p, 'errors', []))


class TestPrescanKeywordGate(unittest.TestCase):
    """缺陷1：预扫描不得因注释/字符串里的 `定义`/`设` 把真关键字降级。"""

    def test_comment_zidingyi_does_not_demote_duan(self):
        # 注释 `自定义段。` 含 `定义`，其后的 `段` 是真关键字，不得被收走降级
        toks = Lexer().tokenize('# 自定义段。\n段 主():\n    打印 1\n主()\n')
        seg = [t for t in toks if t.value == '段']
        self.assertTrue(seg, '未找到 段 token')
        for t in seg:
            self.assertEqual(t.type.name, 'KEYWORD',
                             '段 被预扫描降级成了 %s' % t.type.name)

    def test_duan_still_parses_as_function_def(self):
        tree, errs = _parse('# 自定义段。\n段 主():\n    打印 1\n主()\n')
        self.assertIsNotNone(tree, '含 段 注释的模块解析失败: %s' % errs)

    def test_string_literal_dingyi_does_not_demote_keyword(self):
        # 预扫描同样不跳字符串：字面量里的 `定义段` 也不得把 `段` 收走
        toks = Lexer().tokenize('设 说明 为 "自定义段落"\n段 主():\n    打印 1\n主()\n')
        seg = [t for t in toks if t.value == '段']
        self.assertTrue(seg, '未找到 段 token')
        for t in seg:
            self.assertEqual(t.type.name, 'KEYWORD',
                             '段 被字符串里的 定义 降级成了 %s' % t.type.name)

    def test_real_user_definition_still_collected(self):
        # 闸门只挡真关键字，不得连普通用户自定义名一起挡掉
        toks = Lexer().tokenize('定义 我的名字\n设 甲 为 1\n')
        self.assertTrue(any(t.value == '我的名字' for t in toks),
                        '普通用户自定义名被闸门误挡')


class TestEmbedBlockLineAdvance(unittest.TestCase):
    """缺陷2：吞掉嵌入块后，其后 token 行号不得偏移。"""

    def test_token_line_after_embed_block_is_correct(self):
        # 嵌入块占 1-4 行，第 5 行的 设 token 行号必须是 5
        src = '引 Python 工具:\n    x = 1\n    y = 2\n结束引\n设 甲 为 1\n'
        toks = Lexer().tokenize(src)
        sh = [t for t in toks if t.value == '设']
        self.assertTrue(sh, '未找到 设 token')
        self.assertEqual(sh[0].line, 5,
                         '嵌入块后 设 token 行号错位: %d（应为 5）' % sh[0].line)

    def test_error_line_after_embed_points_to_real_line(self):
        # 第 6 行有非法字符，报错行号必须落在 6，而非被嵌入块行数抵消
        src = ('引 Python 工具:\n    x = 1\n    y = 2\n结束引\n\n'
               '设 甲 为 @@@\n')
        p = LightParser()
        try:
            p.parse(src)
            msg = ' '.join(str(e) for e in getattr(p, 'errors', []))
        except Exception as e:
            msg = str(e)
        self.assertIn('6', msg, '嵌入块后错误行号未指向真实行 6: %s' % msg)


class TestSemicolonStatementSeparator(unittest.TestCase):
    """缺陷3：`;`/`；` 作为语句分隔符，且不破坏 C 风格循环。"""

    def test_toplevel_semicolon(self):
        tree, errs = _parse('设 甲 为 1; 设 乙 为 2\n')
        self.assertIsNotNone(tree, '顶层分号分隔失败: %s' % errs)

    def test_toplevel_fullwidth_semicolon(self):
        tree, errs = _parse('设 甲 为 1；设 乙 为 2\n')
        self.assertIsNotNone(tree, '顶层全角分号分隔失败: %s' % errs)

    def test_trailing_semicolon(self):
        tree, errs = _parse('设 甲 为 1;\n')
        self.assertIsNotNone(tree, '行尾分号失败: %s' % errs)

    def test_body_semicolon(self):
        tree, errs = _parse('段 主():\n    打印 1; 打印 2\n主()\n')
        self.assertIsNotNone(tree, '段体内分号分隔失败: %s' % errs)

    def test_print_string_args_with_semicolon(self):
        # 变参动词 打印 后跟字符串实参，分号必须断开而不并进实参
        tree, errs = _parse('段 主():\n    打印 ""; 打印 "x"\n主()\n')
        self.assertIsNotNone(tree, '打印 变参 + 分号 失败: %s' % errs)

    def test_c_style_for_loop_unaffected(self):
        # C 风格循环的分号在 _parse_c_for_loop 内消费，不得被语句分隔逻辑破坏
        tree, errs = _parse('循环(令 i = 0; i 小于 3; 令 i = i 加 1) {\n    打印 i\n}\n')
        self.assertIsNotNone(tree, 'C 风格循环回归: %s' % errs)

    def test_c_style_for_loop_empty_clauses(self):
        tree, errs = _parse('循环(;;) {\n    跳出\n}\n')
        self.assertIsNotNone(tree, 'C 风格空子句循环回归: %s' % errs)


class TestKeywordArgInBracketCall(unittest.TestCase):
    """缺陷4：括号调用里的命名实参 `f(x, 名=值)`。"""

    def test_named_arg_in_bracket_call(self):
        tree, errs = _parse('设 甲 为 某函数(1, 步长天=1)\n')
        self.assertIsNotNone(tree, '括号调用命名实参解析失败: %s' % errs)

    def test_multiple_named_args(self):
        tree, errs = _parse('设 甲 为 某函数(起=1, 止=10, 步长天=2)\n')
        self.assertIsNotNone(tree, '括号调用多命名实参解析失败: %s' % errs)


class TestIndentErrorMessage(unittest.TestCase):
    """缺陷5：缩进错误给出可读文案，而非打印宽度整数。"""

    def test_stray_indent_gives_readable_message(self):
        src = '设 甲 为 1\n    设 乙 为 2\n'
        p = LightParser()
        try:
            p.parse(src)
            msg = ' '.join(str(e) for e in getattr(p, 'errors', []))
        except Exception as e:
            msg = str(e)
        self.assertIn('缩进', msg, '缩进错误未给出「缩进」文案: %s' % msg)


if __name__ == '__main__':
    unittest.main()
