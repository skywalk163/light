# -*- coding: utf-8 -*-
"""v7 单 33 回归用例：`常` —— L0 冻结表最后一个缺口的落地。

`docs/language/l0-core.md`「## 修饰（5字）」承诺 `常 护 私 公 静` 五个字。
31-C/31-F 收了 `护/私/公/静`（范式 A），`常` 一直挂着「保留字，暂未实现」，
是 `tests/unit/test_spec_docs_sync.py` 缺口基线里**唯一**的成员。本单收掉它。

## 旧行为是静默错编，不是硬报错

落地前 `常 设 甲 为 1。` **不报错**：`常` 落成 IDENTIFIER，被当成一条函数调用
语句，于是产物里多出一行 `常()` 再接 `甲 = 1`。编译期零提示、运行期才 NameError。
按口径 15（静默错编 > 硬报错）这是最高优先级档。

同族的双字写法**也不可用**：`常量 甲 为 1。` 报「「常量」是保留关键字，不能直接
作为语句开头」——`常量` 早就在 `KEYWORDS_DEFINE` 里，但从来没有解析路径。
即 `常` 家族整族当前无可用写法。本单一并收掉两种写法。

## 范式 B，且位置语义已排除范式 A

`常` 出现在语句开头时今天**不报错**（落成 IDENTIFIER 被当普通调用），没有
「原本必然出错」的位置可以安全接管，所以范式 A 不成立，只能从词法层改：
进 `keywords.KEYWORDS_DEFINE` + `lexer._COMPOUND_SAFE_SINGLE_KEYWORDS`。

## 全仓 token A/B（口径：新增单字关键字必须过全仓 A/B，且不得沿用旧推演）

31-E 当年对 `常` 的推演结论**不能直接用**（31-G 已证明这类最长匹配类比会
出错），本单自己重跑了一遍：37255 个 `.light`，改前=工作树 `src/`、
改后=注入 `常` 的临时副本，逐文件比 token 流。

    语料文件数 37255   哈希不同 4   分档 {'SPLIT': 4}

**REGRESS=0、SPLIT=4**，4 例全是 `异常` 被切开，且全在
`bootstrap/release/stdlib` 的已损坏生成产物里（`除异常`、`def异常`、
`def异常处理`），不在任何测试断言路径上：

    CSV读写器.light     ['除异常', ':'] → ['除异', '常', ':']
    断言工具.light      ['异常', '('] → ['异', '常', '(']
    日志系统增强.light   ['def', '异常'] → ['def异常', '(']
    装饰器.light        ['def', '异常处理'] → ['def异常处理', '(']

与 31-G 的 `异`（SPLIT=2，同样全是 `异常`）同型。**不要顺手把 `异常` 加进
关键字表来「保护」它** —— 31-G 实测证伪：`异常` 进表不是保护，而是自己变成
新切割点，SPLIT 反而从 2 涨到 7。本文件为此留了硬断言
`test_异常_仍不得进关键字表`。

## 产物语义：不改产物，别当成实现了 const

Python 没有常量。`常 设 甲 为 1。` 与 `设 甲 为 1。` 编出**完全相同**的产物。
`常` 的价值是（a）声明意图可写、（b）消灭上面那行多余的 `常()`。真正的
不可重赋值检查需要作用域跟踪，是另一支单，本单明确不做——所以本文件也**没有**
「重赋值会报错」这类断言，免得给出假承诺。

## 判据设计

1. **与不带修饰符的 `设` 产物逐字节等价**（`常` / `常量` 各一条）。这条同时钉住
   「修饰符被识别」与「没走另一条退化路径」。
2. **语义锚：产物里不得出现 `常()` 调用**。这是旧行为的指纹；只有等价断言的话，
   「两边都退化」也能相等，必须单独钉这一条。
3. **修饰符后面不是 `设` 时要给出可操作的报错**，而不是继续静默错编。
4. **负面守卫**（改前改后都必须绿）：含 `常` 的复合词不得被切碎；`异常` 不在
   关键字表；`常量` 原有的其它用法不回归。

## 反跑（防永真式，口径 17）

把 `常` 从 `keywords.KEYWORDS_DEFINE` 里删掉重跑本文件：等价断言、`常()` 语义
锚、报错断言、两张表成员断言全红；负面守卫仍绿（它们在改前也必须绿，那正是
「负面守卫不该反跑变红」的含义）。实测于 2026-08-20。
"""

import ast
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser                      # noqa: E402
from code_generator import PythonCodeGenerator               # noqa: E402
from lexer import Lexer, _COMPOUND_SAFE_SINGLE_KEYWORDS      # noqa: E402
from keywords import ALL_KEYWORDS, KEYWORDS_DEFINE           # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _identifiers(src):
    return [t.value for t in Lexer(src).tokenize() if t.type.name == 'IDENTIFIER']


_裸设 = '设 圆周率 为 3.14159。\n'
_单字 = '常 设 圆周率 为 3.14159。\n'
_双字 = '常量 设 圆周率 为 3.14159。\n'


class TestConstModifierEquivalence(unittest.TestCase):
    """`常` / `常量` 前缀与不带修饰符的 `设` 产物等价。"""

    def test_单字修饰符与裸设等价(self):
        self.assertEqual(_compile(_裸设), _compile(_单字))

    def test_双字修饰符与裸设等价(self):
        self.assertEqual(_compile(_裸设), _compile(_双字))

    def test_产物里不得出现常调用(self):
        """旧行为的指纹：`常` 落成 IDENTIFIER 时会多编出一行 `常()`。

        等价断言单独用不够——两边都退化也能相等。这条直接在 AST 上排除
        「有一个名为 `常` 或 `常量` 的调用」。
        """
        for 名, src in (('常', _单字), ('常量', _双字)):
            with self.subTest(修饰符=名):
                tree = ast.parse(_compile(src))
                裸调用 = [n for n in ast.walk(tree)
                          if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Name)
                          and n.func.id in ('常', '常量')]
                self.assertEqual([], 裸调用,
                                 '产物里还有 %s() 调用，修饰符没被识别' % 名)

    def test_赋值确实落地(self):
        """防「等价 + 无常调用」退化成「两边都编不出赋值」。"""
        tree = ast.parse(_compile(_单字))
        目标 = [t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)]
        self.assertIn('圆周率', 目标)


class TestConstModifierError(unittest.TestCase):
    """修饰符后面不跟 `设` 时必须报错，而不是继续静默错编。"""

    def test_常后面缺设时报错并给出写法(self):
        """注意：`LightParser.parse` 是 **raise** ParseError，不是返回 None 收错
        （parser_core.py::_parse_module_with_recovery 末尾 `raise errors[0]`）。
        初版按「返回 None + parser.errors」写，实测直接被异常打穿——记在此免得重踩。
        """
        from parser_core import ParseError
        for 名 in ('常', '常量'):
            with self.subTest(修饰符=名):
                with self.assertRaises(ParseError) as cm:
                    LightParser().parse('%s 圆周率 为 3.14159。\n' % 名)
                msg = str(cm.exception)
                self.assertIn('设', msg,
                              '报错里没告诉用户要写「设」：%s' % msg[:200])
                self.assertIn(名, msg)


class TestConstModifierTables(unittest.TestCase):
    """表成员：`常` 必须同时进两张表；`异常` 一张都不许进。"""

    def test_常_进关键字表(self):
        self.assertIn('常', KEYWORDS_DEFINE)
        self.assertIn('常', ALL_KEYWORDS)

    def test_常_进复合词保护表(self):
        """范式 B 的硬要求：单字进关键字表就必须同时进 compound-safe，
        否则全仓 444 处词内 `常` 会被从中间切开（先例：31-B `现`、31-G `异`）。"""
        self.assertIn('常', _COMPOUND_SAFE_SINGLE_KEYWORDS)

    def test_异常_仍不得进关键字表(self):
        """31-G 实测证伪的那条推演，在本单继续钉住。

        `常` 与 `异` 都会切 `异常`，但把 `异常` 加进表**不是**保护——它自己会
        变成新切割点（31-G：SPLIT 从 2 涨到 7）。谁想「顺手补保护」先看工单 31-G/33。
        """
        self.assertNotIn('异常', ALL_KEYWORDS)
        self.assertNotIn('异常', _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestConstModifierNoRegression(unittest.TestCase):
    """负面守卫：这些在改前改后都必须绿（反跑时不该变红）。"""

    def test_含常复合词不被切碎(self):
        for name in ('异常', '常数', '常量表', '自然常数', '正常值',
                     '常见问题', '日常任务', '异常信息'):
            with self.subTest(name=name):
                src = '设 %s 为 1。\n' % name
                self.assertIn(name, _identifiers(src),
                              '%s 被切碎了：%s' % (name, [(t.type.name, t.value)
                                                        for t in Lexer(src).tokenize()]))

    def test_裸设原样可用(self):
        self.assertIn('圆周率', _compile(_裸设))

    def test_异常捕获语法仍能编(self):
        """`异常` 没进关键字表的直接好处：`捕获 X 异常` 这类写法不受影响。"""
        code = _compile('尝试：\n    打印 1。\n捕获 异常 为 错：\n    打印 错。\n结束\n')
        self.assertTrue(any(isinstance(n, ast.Try) for n in ast.walk(ast.parse(code))))


if __name__ == '__main__':
    unittest.main()
