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

—— 追加：v7 kwarg 判据收敛单（本文件末两个类）——
上面第 4 条只保证「括号里能写 `名=值`」，没管这条判据的**数据源有几份**。
处置遗留 stash 时发现 parser_expr.py 里同一份 44 字停用集合存了 3 份
（模块常量 + 两条内联收参分支各一份副本），加字时会静默漂移。
收敛后内联分支改引模块常量，并补 TestKwargStopKeywordsSinglePoint（源码级，
钉住「只有一个定义点」）与 TestKwargAtEveryBracketSite（行为级，钉住 4 条
收参循环都还能出 `名=值`，且 `==` 不被误读成具名实参）。
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


class TestKwargStopKeywordsSinglePoint(unittest.TestCase):
    """v7 收敛单：kwarg 停用字判据在 parser_expr.py 里只能有**一个定义点**。

    背景（本轮 stash 处置时发现的遗留分叉隐患）：
    「具名实参 `名 = 值`」这条产生式落在 4 条括号式收参循环上，其中
      · 2 条走 helper `_try_parse_keyword_arg()`；
      · 2 条（ParagraphCall 括号收参、`obj的方法(...)` 括号收参）保留内联实现，
        因为取值粒度是 `_parse_comparison` 而 helper 用 `_parse_logical_expr`，
        回退行为也不同，合并会改语义。
    收敛前这 2 条内联分支各自复制了一份 44 字停用集合（与模块常量逐字相同），
    共 3 份同款数据。任何人往 `_KWARG_NAME_STOP_KEYWORDS` 加一个字，两份内联
    副本会静默漂移——判据分叉的典型形状，且不会被任何行为测试打红。
    收敛做法：只统一「判据集合」这一份数据（内联分支改引模块常量），不动取值粒度。

    本类是**源码级**守卫，配 TestKwargAtEveryBracketSite 的行为级守卫一起用：
    行为测试只能证明「现在对」，证不了「没有第二份表」。
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_ROOT, 'src', 'parser_expr.py')
        with open(path, 'r', encoding='utf-8') as f:
            cls.源码 = f.read()
        cls.源码路径 = path

    def test_停用集合只有一个定义点(self):
        次数 = self.源码.count('_KWARG_NAME_STOP_KEYWORDS = frozenset({')
        self.assertEqual(1, 次数,
                         '_KWARG_NAME_STOP_KEYWORDS 的 frozenset 定义点应恰好 1 处，实得 %d 处' % 次数)

    def test_内联分支不得自建停用集合(self):
        # 收敛后内联分支只允许 `_kwarg_stop_kws = _KWARG_NAME_STOP_KEYWORDS`，
        # 一旦有人重新写回 `_kwarg_stop_kws = frozenset({...})`，此断言打红。
        self.assertNotIn('_kwarg_stop_kws = frozenset(', self.源码,
                         '内联收参分支又自建了一份 kwarg 停用集合，判据已分叉')

    def test_每处内联赋值都指向模块常量(self):
        赋值 = [行.strip() for 行 in self.源码.splitlines()
                if 行.strip().startswith('_kwarg_stop_kws =')]
        self.assertTrue(赋值, '未找到 _kwarg_stop_kws 赋值，内联收参分支可能被改名')
        for 行 in 赋值:
            self.assertEqual('_kwarg_stop_kws = _KWARG_NAME_STOP_KEYWORDS', 行,
                             '内联赋值未指向模块常量: %s' % 行)

    def test_不得与函数名动词合并表混淆(self):
        """`_fn_stop` / `_fn_stop2` 看着像同一份表，实际多 4 项，不可合并。

        它们服务的是**函数名动词合并**（`获取函数` 拼名），比 kwarg 停用集合多
        「在/于/中的/包含」。若哪天有人图省事把两者合并，kwarg 参数名里就再也
        写不出含「在/于/包含」的名字了。这里从反面钉住：模块常量**不含**这 4 项。
        """
        from parser_expr import _KWARG_NAME_STOP_KEYWORDS
        for 字 in ('在', '于', '中的', '包含'):
            self.assertNotIn(字, _KWARG_NAME_STOP_KEYWORDS,
                             'kwarg 停用集合混进了函数名动词合并表专有的「%s」' % 字)


class TestKwargAtEveryBracketSite(unittest.TestCase):
    """行为级守卫：括号式收参的各条 kwarg 路径都要真能出 `名=值`。

    判据取「生成的 Python 末行」，因为 code_generator 会在前面吐一大段
    stdlib 前导，只有末行是本次语句的产物。

    路由实测（sys.settrace 记录 parser_expr.py 行命中，逐条核过）：
      · `甲(a = 1)`、`排序(数组, 依据 = 键)`、`对象的方法(参数 = 1)`
        —— 都走 helper `_try_parse_keyword_arg`，**不进**两处内联分支；
      · `对象.方法(参数 = 1)`（英文点号 = FFI/外部库调用写法）
        —— 唯一进「成员方法调用」内联分支的写法；
      · ParagraphCall 内联分支的 kwarg 段落，12 种候选写法全都没命中，
        实测未找到可达输入（helper 先接走了），故本类不为它编造覆盖。
        这一条只由 TestKwargStopKeywordsSinglePoint 的源码级断言守着。
    """

    @classmethod
    def setUpClass(cls):
        try:
            from code_generator import PythonCodeGenerator
        except ImportError as e:                          # pragma: no cover
            raise unittest.SkipTest('code_generator 不可用: %s' % e)
        cls.Gen = PythonCodeGenerator

    def _末行(self, 源码):
        tree, errs = _parse(源码)
        self.assertIsNotNone(tree, '%r 解析失败: %s' % (源码, errs))
        out = self.Gen().generate(tree)
        行 = [l for l in out.strip().split('\n') if l.strip()]
        return 行[-1]

    def test_英文点号成员调用走内联分支(self):
        """`对象.方法(参数 = 1)`——实测唯一进「成员方法调用」内联收参分支的写法。

        反跑证过：把该分支的 EQUALS 判据改成别的 token，只有本用例打红。
        """
        self.assertIn('参数=1', self._末行('设 甲 为 对象.方法(参数 = 1)。'))

    def test_的字成员调用(self):
        # 走 helper，不进内联分支；与上一条一起把两条路由都钉住
        self.assertIn('参数=1', self._末行('设 乙 为 对象的方法(参数 = 1)。'))

    def test_段落调用具名实参(self):
        # 走 helper。排序→sorted、依据→key 由 builtin_map 落地
        self.assertIn('key=', self._末行('设 丙 为 排序(数组, 依据 = 键)。'))

    def test_helper分支多个具名实参(self):
        末行 = self._末行('设 丁 为 甲(a = 1, b = 2)。')
        self.assertIn('a=1', 末行)
        self.assertIn('b=2', 末行)

    def test_比较运算不得被误读成具名实参(self):
        """`==` 是独立的 EQ_EQ token，收名字后看到它必须回退成位置实参。

        这是整条产生式「单向放宽」的关键反例：若判据写成看见 `=` 就当 kwarg，
        `甲(乙 == 丙)` 会被改写成 `甲(乙=丙)`——静默错译，比报错危险得多。
        """
        末行 = self._末行('设 戊 为 甲(乙 == 丙)。')
        self.assertIn('==', 末行, '比较运算被吞成了具名实参: %s' % 末行)




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
