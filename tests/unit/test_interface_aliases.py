# -*- coding: utf-8 -*-
"""v7 单 31-B 回归用例：`现` 是 L0 冻结表承诺的「实现接口」单字别名。

`docs/language/l0-core.md:53-58`「## 接口（2字）」把 `约`=接口定义、`现`=实现接口
列进 30 字冻结表，但 `src/` 从未落地。**本单只落 `现`**，`约` 有意留后（原因见文末）。

`现` 的旧行为是**静默错编**——比硬报错更坏：

    类 学生 现 可打印：     →  class 学生现可打印:
                              （类名粘连 + 基类整段丢失 + 编译期零提示）

`现` 被类名收集循环整段吞掉，与当年 `_CLASS_HEADER_STOP_KEYWORDS` 漏掉单字 `接`
的 bug 完全同型（见 `src/parser_stmt.py` 该表上方注释），修法也一致：补进停止词表。

按已定口径（文档承诺过的别名从缺 → 判编译器缺陷）处理。先例：单 26 的 `掷`、
单 31-A 的 `断`/`跃`。

判据设计：
1. 不用子串判据（`'class 学生(可打印)' in code` 之类）—— 产物含大段引导代码，
   格式随生成器实现漂移。改为 `ast.parse` 后取 `ClassDef`，直接看 `name` 与
   `bases`，正好卡住旧缺陷的两个症状（名字粘连、基类丢失）。
2. 另有一条**与既有同义词产物等价**的断言（`现` vs `实现`），防止别名走另一条
   退化路径而测试仍绿。

**`约` 为何不在本单落地**：`约` 一旦进 `ALL_KEYWORDS` + `_COMPOUND_SAFE_SINGLE_KEYWORDS`，
`合约乘数` 这种「`约` 紧跟另一个 compound-safe 单字」的串会踩到
`lexer._skip_compound_safe_and_match` 的历史「回报内层结果」语义失配，实测编成
`合 * 乘数`——**源文本里的 `约` 整字消失**。那正是单 B 要消除的返回值失配缺陷类，
不能为补别名再引入一处。而 `约` 当前的失败形态是**硬报语法错误**（可见的），
不是静默错编，所以可以等到该失配被正面修掉之后再补。详见工单 31-B。
本文件末尾有一条守卫用例，确保 `约` 仍**不是**关键字——将来谁要加它，必须先看工单。

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
from keywords import ALL_KEYWORDS, KEYWORDS_CLASS            # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _classdef(code, name):
    """在产物里按名字取 ClassDef 节点。

    按名字而不是按位置取：这顺带把「类名是否被粘连」变成了硬判据——旧缺陷下
    `学生` 这个名字根本不存在（产物里叫 `学生现可打印`），查找失败即测试失败。
    """
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(
        '产物里没有名为 %r 的类，现有类名：%s'
        % (name, sorted(n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)))
    )


def _base_names(classdef):
    return [b.id for b in classdef.bases if isinstance(b, ast.Name)]


class TestImplementsAliasTables(unittest.TestCase):
    """关键字表与词法器表的成员判定。"""

    def test_现_已进类关键字表(self):
        self.assertIn('现', KEYWORDS_CLASS)
        # KEYWORDS_CLASS 并入 KEYWORDS_DOUBLE 再并入 ALL_KEYWORDS，lexer 只查后者
        self.assertIn('现', ALL_KEYWORDS)

    def test_现_已进复合词安全表(self):
        # 不在此表则 现在时间/现象记录 等标识符会被最长匹配切碎
        self.assertIn('现', _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestImplementsAlias(unittest.TestCase):
    """`现` → 实现接口（等价于 `实现`/`接`）。"""

    SRC_现 = '接口 可打印：\n    段 打印(己)。\n\n类 学生 现 可打印：\n    性 名。\n'
    SRC_实现 = '接口 可打印：\n    段 打印(己)。\n\n类 学生 实现 可打印：\n    性 名。\n'

    def test_现_落成基类而非粘进类名(self):
        node = _classdef(_compile(self.SRC_现), '学生')
        self.assertEqual(_base_names(node), ['可打印'])

    def test_现_与_实现_产物等价(self):
        a = _classdef(_compile(self.SRC_现), '学生')
        b = _classdef(_compile(self.SRC_实现), '学生')
        self.assertEqual(ast.dump(a), ast.dump(b))

    def test_旧缺陷类名不再出现(self):
        """旧行为把类名编成 `学生现可打印`（静默错编）。它必须彻底消失。"""
        tree = ast.parse(_compile(self.SRC_现))
        names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertNotIn('学生现可打印', names)

    def test_承_与_现_可同行组合(self):
        code = _compile(
            '接口 可打印：\n    段 打印(己)。\n\n'
            '类 人：\n    性 名。\n\n'
            '类 学生 承 人 现 可打印：\n    性 学号。\n'
        )
        node = _classdef(code, '学生')
        self.assertEqual(_base_names(node), ['人', '可打印'])


class TestCompoundIdentifiersSurvive(unittest.TestCase):
    """含 `现` 的标识符不得被切碎（v7 单 27-E 同型回归的守卫）。

    `实现方法` 这类以 `实` 起头的名字额外验证一件事：长度 2 的关键字 `实现`
    由结构性最长匹配优先命中，不会因为新增单字 `现` 而改变既有切法。
    """

    NAMES = (
        '现在时间', '现象记录', '现场数据',
        '出现次数', '表现良好', '实现方法', '发现结果', '体现方式',
    )

    def test_标识符保持单个_token(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values,
                              '%s 被切碎了：%s' % (name, [(t.type.name, t.value) for t in tokens]))

    def test_复合词标识符可端到端使用(self):
        code = _compile('设 现在时间 为 1。\n打印 现在时间。\n')
        self.assertIn('现在时间 = 1', code)
        self.assertIn('print(现在时间)', code)

    def test_孤立单字仍是关键字(self):
        """反向确认：保护复合词没有把孤立的 现 也一起降级成标识符。"""
        tokens = [t for t in Lexer('现\n').tokenize()
                  if t.type.name not in ('NEWLINE', 'EOF', 'INDENT', 'DEDENT')]
        self.assertEqual([(t.type.name, t.value) for t in tokens], [('KEYWORD', '现')])


class TestInterfaceCharDeferred(unittest.TestCase):
    """`约` 本单有意未落地的守卫。

    见模块 docstring 与工单 31-B：`约` 进关键字表会让 `合约乘数` 丢掉 `约` 整字
    （lexer 历史返回值失配）。谁要解掉这条守卫，先把那处失配正面修掉并做全仓 A/B。
    """

    def test_约_仍不是关键字(self):
        self.assertNotIn('约', ALL_KEYWORDS)
        self.assertNotIn('约', _COMPOUND_SAFE_SINGLE_KEYWORDS)

    def test_含约标识符不丢字(self):
        for name in ('合约乘数', '约定俗成', '契约检查', '节约能源'):
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                # 判据是「源文本的每个字都还在 token 流里」，而不是「切成一个 token」：
                # `合约乘数` 里的 `乘` 本来就是既有关键字，会切开——那是另一支旧债。
                joined = ''.join(str(t.value) for t in tokens
                                 if t.type.name in ('IDENTIFIER', 'KEYWORD'))
                for ch in name:
                    self.assertIn(ch, joined, '%s 里的 %r 在 token 流里消失了' % (name, ch))


if __name__ == '__main__':
    unittest.main()
