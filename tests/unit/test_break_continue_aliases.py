# -*- coding: utf-8 -*-
"""v7 单 31-A 回归用例：`断`/`跃` 是 L0 冻结表承诺的 break/continue 单字别名。

`docs/language/l0-core.md:26-27` 把 `断`=break、`跃`=continue 列进「30 字冻结表」，
另有 `docs/language/keywords.md:9,36`、`docs/language/完整语法参考.md:56-57,251-252`、
`docs/guide/迁移指南.md:29`、`docs/guide/分层语法入门.md:23` 共 6 份文档承诺，
但 `src/` 从未落地。旧行为是**静默错编**（比硬报错更坏）：

    当 真：        →  while True:
      断                 断()        # 编成对未定义函数的调用，编译期零提示

按已定口径（文档承诺过的别名从缺 → 判编译器缺陷，先例见单 26 的 `掷`）补齐。

判据设计的两点讲究：
1. **不能用 `'break' in code` 这种子串判据** —— 产物引导段自带 `for/break`，
   任何输入都会让子串命中，断言退化成永真式。这里改为把产物喂给 `ast.parse`，
   在对应的 While/For 节点体内找 `ast.Break`/`ast.Continue`。
2. 除「新别名可用」外，另加一条**与既有别名产物等价**的断言：`断` 与 `跳出`
   编出的 AST dump 必须逐字相同。这样即便将来 break 的生成方式改了，
   也不会出现「别名走了另一条退化路径」而测试仍绿的情况。

复合词保护同样必测：`断` 全仓 174 处词首（`stdlib/断言工具.light` 的 `断言*` 族
最密集），不进 lexer 的 `_COMPOUND_SAFE_SINGLE_KEYWORDS` 会被最长匹配切成 `断`+`言*`。

全部判据不依赖 Python 版本、平台或任何外部工具链。
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
from keywords import ALL_KEYWORDS, KEYWORDS_LOOP             # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _find_loop(code, loop_cls):
    """在产物里找出**用户写的**那个循环节点。

    引导段自带若干 for，所以按源码行号取最靠后的一个（用户代码在产物末尾）。
    不能用 `ast.walk` 的迭代顺序挑「最后一个」—— walk 是广度优先，
    顺序按深度而非位置，会挑中引导段里嵌得更深的那个循环。
    """
    tree = ast.parse(code)
    found = [n for n in ast.walk(tree) if isinstance(n, loop_cls)]
    assert found, '产物里没有 %s 节点' % loop_cls.__name__
    return max(found, key=lambda n: n.lineno)


def _loop_body_types(loop_node):
    return [type(stmt) for stmt in loop_node.body]


class TestBreakContinueAliasTables(unittest.TestCase):
    """关键字表与词法器表的成员判定。"""

    def test_断_跃_已进循环关键字表(self):
        self.assertIn('断', KEYWORDS_LOOP)
        self.assertIn('跃', KEYWORDS_LOOP)
        # KEYWORDS_LOOP 并入 KEYWORDS_DOUBLE 再并入 ALL_KEYWORDS，lexer 只查后者
        self.assertIn('断', ALL_KEYWORDS)
        self.assertIn('跃', ALL_KEYWORDS)

    def test_断_跃_已进复合词安全表(self):
        # 不在此表则 断言失败/跃迁能量 等标识符会被最长匹配切碎
        self.assertIn('断', _COMPOUND_SAFE_SINGLE_KEYWORDS)
        self.assertIn('跃', _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestBreakAlias(unittest.TestCase):
    """`断` → break。"""

    def test_断_编成_break(self):
        code = _compile('当 真：\n    断\n')
        loop = _find_loop(code, ast.While)
        self.assertIn(ast.Break, _loop_body_types(loop),
                      'while 体内没有 break，实际为 %s' % _loop_body_types(loop))

    def test_断_与_跳出_产物等价(self):
        a = _find_loop(_compile('当 真：\n    断\n'), ast.While)
        b = _find_loop(_compile('当 真：\n    跳出\n'), ast.While)
        self.assertEqual(ast.dump(a), ast.dump(b))

    def test_断_不再编成函数调用(self):
        """旧缺陷的反向守卫：`断` 曾被编成 `断()`。"""
        loop = _find_loop(_compile('当 真：\n    断\n'), ast.While)
        self.assertNotIn(ast.Expr, _loop_body_types(loop))


class TestContinueAlias(unittest.TestCase):
    """`跃` → continue。"""

    def test_跃_编成_continue(self):
        code = _compile('遍 i 于 范围(3)：\n    跃\n')
        loop = _find_loop(code, ast.For)
        self.assertIn(ast.Continue, _loop_body_types(loop),
                      'for 体内没有 continue，实际为 %s' % _loop_body_types(loop))

    def test_跃_与_跳过_产物等价(self):
        a = _find_loop(_compile('遍 i 于 范围(3)：\n    跃\n'), ast.For)
        b = _find_loop(_compile('遍 i 于 范围(3)：\n    跳过\n'), ast.For)
        self.assertEqual(ast.dump(a), ast.dump(b))

    def test_跃_不再编成函数调用(self):
        loop = _find_loop(_compile('遍 i 于 范围(3)：\n    跃\n'), ast.For)
        self.assertNotIn(ast.Expr, _loop_body_types(loop))


class TestCompoundIdentifiersSurvive(unittest.TestCase):
    """含 `断`/`跃` 的标识符不得被切碎（v7 单 27-E 同型回归的守卫）。"""

    # 取自 stdlib/断言工具.light、积木库索引块名、工程域块与 stdlib 导出名
    #
    # 注意 `断言为真` 有意**不在**这张表里：它在表达式语境（`打印 断言为真。`）
    # 会被切成 `断言` + `为` + `真`，但断点在 `为`/`真` 这两个长期存在的关键字上，
    # `断言` 本身是完整的 —— 与本单的 `断` 无关，是另一支既有缺陷（表达式语境下
    # 含 `为`/`真` 的标识符被撕开）。声明语境（`导出 断言为真。`、`段 断言为真(值)：`）
    # 靠预扫描白名单是完整的。此处不把它当本单的判据，免得测试变成在测别人的债。
    NAMES = (
        '断言失败', '判断回文', '中断标志', '断裂韧性',
        '跃迁能量', '活跃线程数', '阶跃函数',
    )

    def test_标识符保持单个_token(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values,
                              '%s 被切碎了：%s' % (name, [(t.type.name, t.value) for t in tokens]))

    def test_复合词标识符可端到端使用(self):
        code = _compile('设 断言失败 为 1。\n打印 断言失败。\n')
        self.assertIn('断言失败 = 1', code)
        self.assertIn('print(断言失败)', code)

    def test_孤立单字仍是关键字(self):
        """反向确认：保护复合词没有把孤立的 断/跃 也一起降级成标识符。"""
        for ch in ('断', '跃'):
            with self.subTest(ch=ch):
                tokens = [t for t in Lexer('%s\n' % ch).tokenize()
                          if t.type.name not in ('NEWLINE', 'EOF', 'INDENT', 'DEDENT')]
                self.assertEqual([(t.type.name, t.value) for t in tokens],
                                 [('KEYWORD', ch)])


if __name__ == '__main__':
    unittest.main()
