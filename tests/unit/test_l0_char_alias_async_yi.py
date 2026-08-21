# -*- coding: utf-8 -*-
"""v7 单 31-G 回归用例：`异` —— L0 冻结表承诺的 async 单字别名。

`docs/language/l0-core.md:113-118`「## 异步（2字）」同时承诺 `异`(async) 与
`等`(await)。31-C 只落了 `等`，`异` 留到本单。旧行为与 `等` 同类，是**静默错编**
而非硬报错：`异 段 甲()：` 里的 `异` 落成 IDENTIFIER，编出来的是同步 `def`，
async 语义整条丢掉，编译期零提示——按口径 15（静默错编 > 硬报错）优先级最高。

## 范式 B（真关键字），与 31-F 四个字都不同

`异` 进 `keywords.KEYWORDS_ASYNC` + `lexer._COMPOUND_SAFE_SINGLE_KEYWORDS`，
parser 侧只把四处 `== '异步'` 放宽成 `in ('异步', '异')`。
走范式 B 而不是 31-F 的范式 A，理由是位置语义不成立：`异` 出现在语句开头时
今天**不报错**（它落成 IDENTIFIER 被当普通调用），没有「原本必然出错」的位置
可以安全接管，只能从词法层改。

## 只加 `异`，**不加 `异常`** —— 31-E 推演被 31-G 实测证伪

31-E 曾按「`等于`/`等待` 用 len-2 最长匹配护住 `等`」的机理类比，推演出
「落 `异` 之前必须先把 `异常` 也进关键字表做保护」。全仓 token A/B（37255 个
`.light` 文件）证伪了这个推演：

- `异` 单加：REGRESS=0、SPLIT=2
- `异` + `异常`：REGRESS=0、SPLIT=7

`异常` 进表护不住 `异常`，它自己变成新切割点，把 `异常信息`/`断言失败异常`/
`异常列表`/`异常值检测` 统统撕开。**教训：漂移方向必须实跑 A/B，不能凭最长匹配
的机理类比推。** 本文件为此留了一条硬断言（`test_异常_不得进关键字表`），
谁再想「顺手补保护」会先撞上它。

`异` 单加的那 2 例 SPLIT 都是 bootstrap/release/stdlib 里 `def异常`/`def异常处理`
这种「def 粘着中文名」的已损坏生成产物，改后读法（`def` + `异常`）比改前更贴
字面，且都不在任何测试断言路径上（口径 17 的 SPLIT 判据）。

## 判据设计

1. **与 `异步` 产物逐字节等价**，四种形态各一条：段落 / 遍历 / 作用域 /
   上下文管理器。等价判据同时钉住「别名生效」与「没走另一条退化路径」。
2. **每形态一个语义锚**，防等价断言退化成「两边都没生效所以相等」：
   `ast.AsyncFunctionDef` / `ast.AsyncFor` / `ast.AsyncWith` / `asyncio.gather`。
   段落那条尤其要紧——旧行为编出的是**同步 `def`**，只比等价判据多这一个锚才能
   区分「async 落地了」和「两边都退化成 def」。
3. **modifier 归一**：`异` 解析后存进 `Paragraph.modifiers` 的必须是 `'异步'`，
   这样 `code_generator.py:1408` 的 `'异步' in modifiers` 一行都不用改。
4. **负面守卫**：含 `异` 的复合词不得被切碎；`异常` 不在关键字表；
   `异步`/`等待`/`等` 的既有写法不回归；`尝试/捕获 异常` 仍能编。

## 反跑（防永真式）

落地前把改动整体拉掉
（`git stash push -- src/keywords.py src/lexer.py src/parser_stmt.py`）重跑本
文件：**12 failed / 8 passed**。红的是全部等价 + 语义锚 + 表成员断言（`异` 尚未
落地时它们都必然红），绿的 8 条是负面守卫（复合词不切碎、`异常` 不在表、
`异步`/`等` 原样可用、异常捕获仍能编）——它们在改前也必须绿，那正是「负面守卫
不该反跑变红」的含义。
注意：本单 commit 之后反跑基准要换成 `HEAD~1`（31-D 踩过的坑）。

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
from keywords import ALL_KEYWORDS, KEYWORDS_ASYNC            # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _has_node(code, node_type):
    return any(isinstance(n, node_type) for n in ast.walk(ast.parse(code)))


def _identifiers(src):
    return [t.value for t in Lexer(src).tokenize() if t.type.name == 'IDENTIFIER']


# 四种形态：(名字, `异` 写法, `异步` 写法, 语义锚)
_FORMS = [
    ('段落', '异 段 甲()：\n    返回 1。\n结束\n',
             '异步 段 甲()：\n    返回 1。\n结束\n', ast.AsyncFunctionDef),
    ('遍历', '异 遍 甲 于 乙：\n    打印 甲。\n结束\n',
             '异步 遍历 甲 于 乙：\n    打印 甲。\n结束\n', ast.AsyncFor),
    ('上下文', '使用 异 甲 为 乙：\n    打印 乙。\n结束\n',
               '使用 异步 甲 为 乙：\n    打印 乙。\n结束\n', ast.AsyncWith),
]


class TestAsyncCharAliasEquivalence(unittest.TestCase):
    """`异` → async（等价于 `异步`），四种形态逐字节对齐 + 各带语义锚。"""

    def test_四形态与异步产物等价(self):
        for name, src_yi, src_full, _anchor in _FORMS:
            with self.subTest(形态=name):
                self.assertEqual(_compile(src_yi), _compile(src_full))

    def test_四形态语义锚(self):
        for name, src_yi, _src_full, anchor in _FORMS:
            with self.subTest(形态=name):
                self.assertTrue(
                    _has_node(_compile(src_yi), anchor),
                    '%s：产物里没有 %s 节点，async 语义没落地' % (name, anchor.__name__))

    def test_异段落编成async_def而非同步def(self):
        """最要紧的一条：旧行为**不报错**，只是把 `异` 当标识符、编出同步 `def`。

        单看「能编过」或「产物含 甲」都会假绿，必须钉住 AsyncFunctionDef 且
        排除同名的同步 FunctionDef。
        """
        tree = ast.parse(_compile('异 段 甲()：\n    返回 1。\n结束\n'))
        名为甲 = [n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and n.name == '甲']
        self.assertEqual(len(名为甲), 1, '产物里名为 甲 的定义不止一个：%s' % 名为甲)
        self.assertIsInstance(名为甲[0], ast.AsyncFunctionDef)

    def test_异作用域与异步作用域等价(self):
        """作用域形态单列：产物不是 Async* 节点，而是 `await asyncio.gather(...)`。

        必须包在异步段落里：`异步 作用域` 编出的是 `await asyncio.gather(...)`，
        写在模块顶层就是模块级裸 await（Python `SyntaxError`），因此 codegen
        现在在顶层直接报错（单 A1）。本用例原先正是断言那种顶层写法能编过。
        """
        a = _compile('异 段 主()：\n    异 作用域：\n        打印 1。\n    结束\n结束\n')
        b = _compile('异步 段 主()：\n    异步 作用域：\n        打印 1。\n    结束\n结束\n')
        self.assertEqual(a, b)
        self.assertIn('asyncio.gather', a)

    def test_异与等可同时用(self):
        """`异`(31-G) + `等`(31-C) 两个单字别名同句，与全字写法等价。"""
        a = _compile('异 段 甲()：\n    设 乙 为 等 丙()。\n    返回 乙。\n结束\n')
        b = _compile('异步 段 甲()：\n    设 乙 为 等待 丙()。\n    返回 乙。\n结束\n')
        self.assertEqual(a, b)
        self.assertTrue(_has_node(a, ast.Await))


class TestAsyncCharAliasModifierNormalized(unittest.TestCase):
    """`异` 解析后必须把 modifier 归一成 `'异步'`。

    codegen 判 async 的那一行是 `'异步' in (stmt.modifiers or [])`
    （`src/code_generator.py`）。若 parser 存了裸 `'异'`，等价断言会红，但
    红在「产物差一个 async」这种难读的地方；这条把失配钉在 AST 层，直接指出原因。
    """

    def _modifiers(self, src):
        tree = LightParser().parse(src)
        self.assertIsNotNone(tree, '解析失败：%r' % src)
        for stmt in tree.statements:
            if hasattr(stmt, 'modifiers') and getattr(stmt, 'name', None) == '甲':
                return list(stmt.modifiers or [])
        raise AssertionError('AST 里找不到名为 甲 的段落：%s'
                             % [type(s).__name__ for s in tree.statements])

    def test_异_存成异步(self):
        self.assertIn('异步', self._modifiers('异 段 甲()：\n    返回 1。\n结束\n'))

    def test_异_不残留裸单字(self):
        self.assertNotIn('异', self._modifiers('异 段 甲()：\n    返回 1。\n结束\n'))


class TestAsyncCharAliasTables(unittest.TestCase):
    """表成员：`异` 必须同时进两张表；`异常` 一张都不许进。"""

    def test_异_进关键字表(self):
        self.assertIn('异', KEYWORDS_ASYNC)
        self.assertIn('异', ALL_KEYWORDS)

    def test_异_进复合词保护表(self):
        """范式 B 的硬要求：单字进关键字表就必须同时进 compound-safe，
        否则全仓 595 处词内 `异` 会被从中间切开（先例：31-B `现`、31-C `等`）。"""
        self.assertIn('异', _COMPOUND_SAFE_SINGLE_KEYWORDS)

    def test_异常_不得进关键字表(self):
        """31-E 推演 → 31-G 实测证伪的那一条，钉成断言。

        `异常` 进表不是给 `异` 加 len-2 保护，而是自己变成新切割点：
        全仓 A/B 的 SPLIT 从 2 涨到 7。谁想「顺手补保护」先看工单 31-G。
        """
        self.assertNotIn('异常', ALL_KEYWORDS)
        self.assertNotIn('异常', _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestAsyncCharAliasNoRegression(unittest.TestCase):
    """负面守卫：这些在改前改后都必须绿（反跑时不该变红）。"""

    def test_含异复合词不被切碎(self):
        for name in ('异常信息', '异或', '位异或', '变异系数', '异常值检测',
                     '断言失败异常', '异常列表', '差异对比'):
            with self.subTest(name=name):
                src = '设 %s 为 1。\n' % name
                self.assertIn(name, _identifiers(src),
                              '%s 被切碎了：%s' % (name, [(t.type.name, t.value)
                                                        for t in Lexer(src).tokenize()]))

    def test_异步原样可用(self):
        code = _compile('异步 段 甲()：\n    返回 1。\n结束\n')
        self.assertTrue(_has_node(code, ast.AsyncFunctionDef))

    def test_等待与等原样可用(self):
        a = _compile('异步 段 甲()：\n    设 乙 为 等待 丙()。\n    返回 乙。\n结束\n')
        b = _compile('异步 段 甲()：\n    设 乙 为 等 丙()。\n    返回 乙。\n结束\n')
        self.assertEqual(a, b)
        self.assertTrue(_has_node(a, ast.Await))

    def test_异常捕获语法仍能编(self):
        """`异常` 没进关键字表的直接好处：`捕获 X 异常` 这类写法不受影响。"""
        code = _compile('尝试：\n    打印 1。\n捕获 异常 为 错：\n    打印 错。\n结束\n')
        self.assertTrue(_has_node(code, ast.Try))


if __name__ == '__main__':
    unittest.main()
