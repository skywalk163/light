# -*- coding: utf-8 -*-
"""v7 单 31-C 回归用例：`私`/`护`/`静`/`等` 四个 L0 冻结表承诺的单字别名。

`docs/language/l0-core.md` 两节：
- `:113-118`「## 异步（2字）」—— `异`=async、`等`=await
- `:120-128`「## 修饰（4字）」—— `常`=常量、`护`=受保护、`私`=私有、`公`=公共、`静`=静态

本单只落 **`私`/`护`/`静`/`等`** 这四个字。选这四个不是拍脑袋，是先用全仓
token A/B 逐字预筛（37255 个 `.light` 文件，改前=HEAD、改后=逐字进表）筛出来的
**零漂移**集合；同批筛掉的：`公`（5 文件切法漂移）、`异`（2 文件）、`常`/`写`/`约`
（**吞字**，阻塞于 lexer 返回值失配）。详见工单 31-C。

旧行为分两类，四个字都属「文档承诺过但 src/ 从缺」：

    类 甲：              →  硬报「类体内不支持的成员声明：'私'」
        私 段 乙()：…

    异步 段 甲()：        →  **静默错编** `乙 = 等(丙)()`
        设 乙 为 等 丙()。    （`等` 落成 IDENTIFIER，按缺省 arity=1 当一元函数调用，
                             编译期零提示，运行期才 NameError）

两条落地路线是**有意分开**的：

- `私`/`护`/`静` 走「范式 A」——判 **IDENTIFIER 而非 KEYWORD**，词法层零改动，
  与 `性`/`构` 同一先例（理由见 `src/parser_stmt.py` 那段注释）。这三个字是高频构词字
  （全仓词首 护 23 / 私 80 / 静 121 处），进 `ALL_KEYWORDS` 就得动最长匹配，风险远大于
  收益；而「类体成员位置的裸 IDENTIFIER」此前一律落到 else 报错，所以新增分支只可能
  把「原本报错」变成「能解析」。本文件因此有一条**反向守卫**：断言这三个字**仍不是**
  关键字，防止后人「顺手」把它们塞进 keywords.py 而不自觉扩大了词法面。
- `等` 只能走「范式 B」——await 在表达式位，没有「类体成员位」这种可锚的上下文，
  必须成为真关键字，并同步进 `_COMPOUND_SAFE_SINGLE_KEYWORDS`。

判据设计：每个别名都断言**与既有多字同义词的产物逐字节相同**（`私` vs `私有`、
`护` vs `保护`、`静` vs `静态`、`等` vs `等待`）。这比「产物里有没有某个子串」强：
子串判据会被大段引导代码假绿（见单 26 `掷` 的教训），而等价判据同时钉住「别名生效」
与「没走另一条退化路径」。特别是 `护`：codegen 目前**丢弃** protected（既不改名也不加
标记，见 `src/code_generator.py:2106-2109` 只判 `== 'private'`），所以这里绝不能断言
产物里有 `_` 前缀——那会把「`护` 别名生效」和「protected 语义未实现」两件事混在一起测。
protected 的语义落地是独立的一笔债，不在本单范围。

**已知边界（不在本单修）**：`等` 紧跟另一个 compound-safe 单字时（如 `等为真`）会踩
`lexer._skip_compound_safe_and_match` 的历史「回报内层结果」失配，`等` 整字消失——
与 `约` 被撤单的机制完全相同。差别在于**全仓 37255 文件里不存在这种串**（A/B 实测
0 漂移 0 吞字），所以按「A/B 零漂移即可落地」的口径放行；根治要等那处失配被正面修掉
（工单 31-D）。本文件的复合词守卫只覆盖语料里真实存在的形态。

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


def _user_tail(code):
    """取产物里用户代码那一段（引导段在前，用户代码在末尾）。

    只用于失败信息展示，判据本身走全文等价，不依赖这个切法。
    """
    lines = [l for l in code.splitlines() if l.strip()]
    return lines[-8:]


class TestAliasTableMembership(unittest.TestCase):
    """表成员判定——正向（`等`）与反向（`私`/`护`/`静`）。"""

    def test_等_已进异步关键字表(self):
        self.assertIn('等', KEYWORDS_ASYNC)
        # KEYWORDS_ASYNC 并入 KEYWORDS_DOUBLE 再并入 ALL_KEYWORDS，lexer 只查后者
        self.assertIn('等', ALL_KEYWORDS)

    def test_等_已进复合词安全表(self):
        self.assertIn('等', _COMPOUND_SAFE_SINGLE_KEYWORDS)

    def test_私护静_仍不是关键字(self):
        """范式 A 的反向守卫：这三个字靠 parser 的 IDENTIFIER 分支识别，
        **不得**进关键字表——进了就把词法面扩大到 224 处词首占用上去了。"""
        for ch in ('私', '护', '静'):
            with self.subTest(ch=ch):
                self.assertNotIn(ch, ALL_KEYWORDS)
                self.assertNotIn(ch, _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestMemberModifierAliases(unittest.TestCase):
    """`私`→private、`护`→protected、`静`→static，产物须与多字写法逐字节一致。"""

    CASES = (
        ('私', '私有'),
        ('护', '保护'),
        ('静', '静态'),
    )

    def test_修饰方法_与多字写法等价(self):
        for short, long in self.CASES:
            with self.subTest(修饰符=short):
                a = _compile('类 甲：\n    %s 段 乙()：\n        返 1。\n' % short)
                b = _compile('类 甲：\n    %s 段 乙()：\n        返 1。\n' % long)
                self.assertEqual(a, b, '「%s」与「%s」产物不一致；新写法尾部：%s'
                                 % (short, long, _user_tail(a)))

    def test_修饰属性_与多字写法等价(self):
        for short, long in self.CASES:
            with self.subTest(修饰符=short):
                a = _compile('类 甲：\n    %s 属性 名。\n' % short)
                b = _compile('类 甲：\n    %s 属性 名。\n' % long)
                self.assertEqual(a, b)

    def test_私_确实落成私有改名(self):
        """至少有一个修饰符要验到「语义真的生效」，否则三条等价断言可能一起
        退化成「两边都没生效所以相等」。private 是三者里 codegen 唯一落地的
        （单下划线改名，src/code_generator.py:2106-2109），拿它当锚。"""
        tree = ast.parse(_compile('类 甲：\n    私 段 乙()：\n        返 1。\n'))
        cls = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and n.name == '甲')
        names = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
        self.assertIn('_乙', names, '私有改名没生效，类成员：%s' % names)

    def test_静_确实落成staticmethod(self):
        """同上，`静` 的语义锚：@staticmethod + 无 self 形参。"""
        tree = ast.parse(_compile('类 甲：\n    静 段 乙()：\n        返 1。\n'))
        cls = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and n.name == '甲')
        fn = next(m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == '乙')
        decorators = [d.id for d in fn.decorator_list if isinstance(d, ast.Name)]
        self.assertIn('staticmethod', decorators)
        self.assertEqual([a.arg for a in fn.args.args], [])

    def test_旧硬报错已消失(self):
        """三个字此前都落到类体兜底分支硬报错，现在必须能解析。"""
        for short, _ in self.CASES:
            with self.subTest(修饰符=short):
                self.assertIsNotNone(
                    LightParser().parse('类 甲：\n    %s 属性 名。\n' % short))


class TestAwaitAlias(unittest.TestCase):
    """`等`→await，产物须与 `等待` 逐字节一致。"""

    def test_等_函数调用_与等待等价(self):
        a = _compile('异步 段 甲()：\n    设 乙 为 等 丙()。\n')
        b = _compile('异步 段 甲()：\n    设 乙 为 等待 丙()。\n')
        self.assertEqual(a, b, '新写法尾部：%s' % _user_tail(a))

    def test_等_成员调用_与等待等价(self):
        """`等 对象.方法()` 这一支单独钉：`等待` 侧的 DOT 归属是单独修过的
        （见 src/parser_expr.py 该分支上方注释），别名必须跟着走同一条路。"""
        a = _compile('异步 段 甲()：\n    设 乙 为 等 丙.丁()。\n')
        b = _compile('异步 段 甲()：\n    设 乙 为 等待 丙.丁()。\n')
        self.assertEqual(a, b, '新写法尾部：%s' % _user_tail(a))

    def test_等_确实编成await而非函数调用(self):
        """旧缺陷是静默编成 `等(丙)()`。判据取 AST 节点，不查子串——
        引导段里本来就有 await，子串判据会假绿。"""
        tree = ast.parse(_compile('异步 段 甲()：\n    设 乙 为 等 丙()。\n'))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.AsyncFunctionDef) and n.name == '甲')
        awaits = [n for n in ast.walk(fn) if isinstance(n, ast.Await)]
        self.assertTrue(awaits, '函数体里没有 Await 节点，产物：%s'
                        % ast.dump(fn))
        # 反向：不得出现「把 等 当函数名调用」的形态
        called = [n.func.id for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn('等', called)

    def test_孤立等仍是关键字(self):
        tokens = [t for t in Lexer('等\n').tokenize()
                  if t.type.name not in ('NEWLINE', 'EOF', 'INDENT', 'DEDENT')]
        self.assertEqual([(t.type.name, t.value) for t in tokens], [('KEYWORD', '等')])


class TestCompoundIdentifiersSurvive(unittest.TestCase):
    """含 `等`/`私`/`护`/`静` 的标识符不得被切碎（单 27-E 同型回归守卫）。

    只覆盖语料里真实存在的形态。`等于X` 不在此列——`等于` 是既有 len-2 关键字，
    `等于阈值` 切成 `等于`+`阈值` 是本单之前就有的行为，不是本单引入的。
    """

    NAMES = (
        '等级判断', '等价关系', '等额本息', '等压过程', '等容过程', '等待时间',
        '私钥数据', '护理费用', '护照号码',
        '静脉氧含量', '静态方法名', '静默异常', '静息膜电位',
    )

    def test_标识符保持单个_token(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values, '%s 被切碎了：%s'
                              % (name, [(t.type.name, t.value) for t in tokens]))

    def test_复合词可端到端使用(self):
        code = _compile('设 等级判断 为 1。\n打印 等级判断。\n')
        self.assertIn('等级判断 = 1', code)
        self.assertIn('print(等级判断)', code)

    def test_既有等于用法不受影响(self):
        """`等于` 是 len-2 关键字，结构性最长匹配优先命中，新增单字 `等` 不得改变它。"""
        tokens = [t for t in Lexer('如果 甲 等于 乙 那么\n').tokenize()
                  if t.type.name == 'KEYWORD']
        self.assertIn('等于', [t.value for t in tokens])
        self.assertNotIn('等', [t.value for t in tokens])


if __name__ == '__main__':
    unittest.main()
