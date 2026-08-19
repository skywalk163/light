# -*- coding: utf-8 -*-
"""v7 单 31-F 回归用例：`约`/`公`/`引 X`/`写` 四个 L0 冻结表承诺的单字别名。

`docs/language/l0-core.md` 四处承诺，`src/` 均从未落地：

- `:57`  「## 接口（2字）」 `约` = 接口定义
- `:64`  「## 模块（3字）」 `引` = 导入/引用
- `:96`  「## 输出（2字）」 `写` = write
- `:127` 「## 修饰（4字）」 `公` = 公共

按已定口径（多份文档承诺过的别名从缺 → 判编译器缺陷）处理。先例：单 26 `掷`、
单 31-A `断`/`跃`、单 31-B `现`、单 31-C `私`/`护`/`静`/`等`。

## 三种落地范式，本单一次用了两种（外加一条零成本的纯 parser 新增）

本单**没有任何一个字进关键字表**——这是与 31-A/31-B/31-C 最大的区别，也是
31-E 全仓预筛（37255 个 `.light` 文件 token A/B）得出的结论：

- `约`（范式 A）：parser 判 **IDENTIFIER 而非 KEYWORD**，词法层零改动。
  依据是 31-E 的位置语义实测——`约 名：` 这个形态今天**一律硬报错**，且报错与
  「从不进任何关键字表的对照字 `鱼`」逐字相同，说明该位置的裸标识符本来就必然
  出错，新增分支只可能把「原本报错」变成「能解析」。
  **但必须带前视守卫**：`约 等于 1。` / `设 约 为 1。` 这类以 `约` 为变量名的写法
  今天是合法的，守卫取「本行内有冒号」（见 `src/parser_stmt.py`
  `_is_interface_char_header`）。本文件为此专门留了两条负面用例。
- `公`（范式 A）：与 31-C 的 `私`/`护`/`静` 同一个 elif 链、同一条理由。
  31-C 当年把 `公` 留下，理由是「全仓 A/B 有 5 文件切法漂移」——那 5 例
  （`CNF公式` → `CNF`+`公式`）是**范式 B 的代价**，走范式 A 后代价归零。
- `引 X`（纯 parser 新增）：`引` **本来就是关键字**（`KEYWORDS_EMBED`，且早已在
  `_COMPOUND_SAFE_SINGLE_KEYWORDS` 里），缺的只是 import 语句分支，所以词法层
  零改动、A/B 风险为 0。与 L4 嵌入块（`引 Python:` … `结束引`）的消歧**在词法层
  就已完成**：`lexer._tokenize_embed_block` 要求语言名后面必须紧跟冒号，否则回报
  `(None, 0)` 且不吞字符，于是 `引 数学。` 落回普通分词。
- `写`（范式 C = `code_generator.builtin_map`）：**用户裁决的路线**，先例是同表里的
  `印`→print。不走范式 B 有两条硬理由：(1) `写` 全仓代码侧词内 797 处
  （`大写` 99 / `小写` 80 / `转小写` 27 …），进表就会把这些词从中间切开；
  (2) `积木库/blocks_v5/网络/HTTP方法判断.light` 把 `写` 当**数据值**用
  （`POST, 写, 其他` 的分支枚举），进关键字表会把那种写法改坏，而 `builtin_map`
  只在**调用点**生效，天然兼容。本文件为 (2) 专门留了一条负面用例。

## 判据设计

1. **与既有多字同义词产物逐字节等价**（`约` vs `接口`、`公` vs `公有`、
   `引` vs `导入`）。这比「产物里有没有某个子串」强：子串判据会被大段引导代码
   假绿（单 26 `掷` 的教训），而等价判据同时钉住「别名生效」与「没走另一条退化路径」。
2. **每个字至少一条语义锚**，防止等价断言退化成「两边都没生效所以相等」：
   `约` 取 `ast.ClassDef` 的 `bases` 含 `ABC`；`引` 取 `ast.Import`；
   `写` 取产物里出现 `_light_builtin.写入输出(...)` 调用。
3. **负面守卫**（本单特有，因为范式 A/C 都是「不进表」）：
   - 三个字仍**不在** `ALL_KEYWORDS` / `_COMPOUND_SAFE_SINGLE_KEYWORDS`；
   - `约` 作变量名的既有写法仍能编（前视守卫没有抢过头）；
   - `写` 作数据值时**不得**被 `builtin_map` 改写；
   - 含这些字的复合词标识符不得被切碎。

## 反跑（防永真式）

落地前把改动整体拉掉（`git stash push -- src/parser_stmt.py src/code_generator.py`）
重跑本文件：**14 failed / 11 passed**，红的正是四个字的正面用例与语义锚
（`约`/`公`/`引` 的等价、语义锚、旧硬报错已消失，`写` 的两条），绿的 11 条是负面守卫与
表成员断言（它们在改前也应该绿——那正是「负面守卫不该反跑变红」的含义）。
注意：本单 commit 之后，反跑基准要换成 `HEAD~1`，`HEAD` 已经是修好的版本
（这是 31-D 踩过的坑）。

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
from keywords import ALL_KEYWORDS                            # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _classdef(code, name):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(
        '产物里没有名为 %r 的类，现有类名：%s'
        % (name, sorted(n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef))))


def _base_names(classdef):
    return [b.id for b in classdef.bases if isinstance(b, ast.Name)]


class TestParadigmACTablesUntouched(unittest.TestCase):
    """反向守卫：本单四个字**没有一个**该进关键字表。

    `约`/`公` 走范式 A（parser 判 IDENTIFIER），`写` 走范式 C（builtin_map），
    三者进表都会把词法面扩大到上千处词内占用上去（`最大公约数`/`CNF公式`/
    `大写`/`小写`…）。谁要「顺手」把它们塞进 keywords.py，先看工单 31-E/31-F。
    """

    def test_约公写_仍不是关键字(self):
        for ch in ('约', '公', '写'):
            with self.subTest(ch=ch):
                self.assertNotIn(ch, ALL_KEYWORDS)
                self.assertNotIn(ch, _COMPOUND_SAFE_SINGLE_KEYWORDS)

    def test_引_本来就是关键字(self):
        """`引` 是唯一例外——它在本单之前就是 KEYWORDS_EMBED 成员，
        本单只加 parser 分支，所以这里是**正向**断言。"""
        self.assertIn('引', ALL_KEYWORDS)
        self.assertIn('引', _COMPOUND_SAFE_SINGLE_KEYWORDS)


class TestInterfaceCharAlias(unittest.TestCase):
    """`约` → 接口定义（等价于 `接口`/`接`/`协议`）。"""

    SRC_约 = '约 可打印：\n    段 显示()。\n'
    SRC_接口 = '接口 可打印：\n    段 显示()。\n'

    def test_约_与接口产物等价(self):
        self.assertEqual(_compile(self.SRC_约), _compile(self.SRC_接口))

    def test_约_确实编成抽象基类(self):
        """语义锚：接口落成 `class X(ABC)`。旧行为是硬报语法错误，编不出任何类。"""
        node = _classdef(_compile(self.SRC_约), '可打印')
        self.assertIn('ABC', _base_names(node))

    def test_约_支持继承子句(self):
        code = _compile('接口 甲：\n    段 x()。\n\n约 乙 继承 甲：\n    段 y()。\n')
        self.assertEqual(_base_names(_classdef(code, '乙')), ['ABC', '甲'])

    def test_旧硬报错已消失(self):
        self.assertIsNotNone(LightParser().parse(self.SRC_约))


class TestInterfaceCharLookaheadGuard(unittest.TestCase):
    """前视守卫的负面用例：`约` 作普通变量名的既有写法**不得**被抢走。

    这是范式 A 的真风险点——`_parse_statement` 里那条 IDENTIFIER 分支若不带
    「本行有冒号」的守卫，`约 等于 1。` 就会被当成接口声明，把能跑的代码改坏。
    """

    def test_约_可作赋值目标(self):
        code = _compile('约 等于 1。\n打印 约。\n')
        self.assertIn('约 = 1', code)
        self.assertIn('print(约)', code)

    def test_约_可作设语句目标(self):
        code = _compile('设 约 为 1。\n打印 约。\n')
        self.assertIn('约 = 1', code)

    def test_含约复合词不被切碎(self):
        for name in ('合约乘数', '最大公约数值', '违约金额', '约束条件'):
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values, '%s 被切碎了：%s'
                              % (name, [(t.type.name, t.value) for t in tokens]))


class TestPublicModifierAlias(unittest.TestCase):
    """`公` → public 成员修饰符（等价于 `公有`）。"""

    def test_公_修饰方法_与公有等价(self):
        a = _compile('类 甲：\n    公 段 乙()：\n        返 1。\n')
        b = _compile('类 甲：\n    公有 段 乙()：\n        返 1。\n')
        self.assertEqual(a, b)

    def test_公_修饰属性_与公有等价(self):
        a = _compile('类 甲：\n    公 属性 名。\n')
        b = _compile('类 甲：\n    公有 属性 名。\n')
        self.assertEqual(a, b)

    def test_公_不加私有改名(self):
        """语义锚（反向）：public 的可观测语义就是「不改名」。
        与 `私` 的 `_乙` 改名对照，确保 `公` 没有误落到 private 分支。"""
        tree = ast.parse(_compile('类 甲：\n    公 段 乙()：\n        返 1。\n'))
        cls = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and n.name == '甲')
        names = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
        self.assertIn('乙', names)
        self.assertNotIn('_乙', names)

    def test_旧硬报错已消失(self):
        self.assertIsNotNone(LightParser().parse('类 甲：\n    公 属性 名。\n'))

    def test_含公复合词不被切碎(self):
        for name in ('CNF公式', '最小公倍数', '公里每小时'):
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values, '%s 被切碎了：%s'
                              % (name, [(t.type.name, t.value) for t in tokens]))


class TestImportCharAlias(unittest.TestCase):
    """`引 X` → import（等价于 `导入 X`）。"""

    def test_引_与导入产物等价(self):
        self.assertEqual(_compile('引 数学。\n'), _compile('导入 数学。\n'))

    def test_引_确实编成import(self):
        """语义锚取 ast.Import 节点：产物引导段本来就有一堆 import，
        子串判据会假绿，所以按 `names` 精确匹配模块名。"""
        tree = ast.parse(_compile('引 数学。\n'))
        mods = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                for a in n.names]
        self.assertIn('数学', mods)

    def test_引_支持为别名(self):
        tree = ast.parse(_compile('引 数学 为 数。\n'))
        pairs = [(a.name, a.asname) for n in ast.walk(tree)
                 if isinstance(n, ast.Import) for a in n.names]
        self.assertIn(('数学', '数'), pairs)

    def test_旧硬报错已消失(self):
        self.assertIsNotNone(LightParser().parse('引 数学。\n'))

    def test_嵌入块仍走词法层不受影响(self):
        """消歧守卫：带冒号的 `引 Python:` 必须仍被词法器整块吃成 EMBED_BLOCK，
        绝不能因为新增了 import 分支而漏到 parser 去。"""
        tokens = Lexer('引 Python:\n    x = 1\n结束引\n').tokenize()
        kinds = [t.type.name for t in tokens]
        self.assertIn('EMBED_BLOCK', kinds)
        self.assertNotIn('引', [str(t.value) for t in tokens if t.type.name == 'KEYWORD'])
        self.assertIn('x = 1', _compile('引 Python:\n    x = 1\n结束引\n'))

    def test_含引复合词不被切碎(self):
        for name in ('索引位置', '推理引擎', '引号处理'):
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values, '%s 被切碎了：%s'
                              % (name, [(t.type.name, t.value) for t in tokens]))


class TestWriteBuiltinAlias(unittest.TestCase):
    """`写` → write（范式 C：`builtin_map`，先例 `印`→print）。"""

    def test_写_调用编成写入输出(self):
        """语义锚：旧行为原样发射 `写("hi")` → 运行期 NameError。
        现在必须落成 `_light_builtin.写入输出("hi")`（sys.stdout.write + flush）。"""
        tree = ast.parse(_compile('写("hi")。\n'))
        targets = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if isinstance(n.func.value, ast.Name):
                    targets.append('%s.%s' % (n.func.value.id, n.func.attr))
        self.assertIn('_light_builtin.写入输出', targets)

    def test_写_不再是裸名调用(self):
        """反向：不得留下把 `写` 当自由函数名调用的形态（那就是旧的 NameError 缺陷）。"""
        tree = ast.parse(_compile('写("hi")。\n'))
        called = [n.func.id for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn('写', called)

    def test_写_作数据值时不得被改写(self):
        """范式 C 相对范式 B 的关键优势，也是选它的理由之一：
        `积木库/blocks_v5/网络/HTTP方法判断.light` 把 `写` 当分支枚举的数据值用
        （`POST, 写, 其他`）。builtin_map 只在调用点生效，此处必须原样保留。"""
        code = _compile('设 方法 为 写。\n打印 方法。\n')
        self.assertIn('方法 = 写', code)

    def test_含写复合词不被切碎(self):
        """范式 C 的又一条优势：`大写`/`小写` 都不在关键字表里，
        走范式 B 会被新增的单字 `写` 从中间切开，走范式 C 完全不碰词法。"""
        for name in ('大写', '小写', '转小写', '写入文件路径', '首字母大写'):
            with self.subTest(name=name):
                tokens = Lexer('设 %s 为 1。\n' % name).tokenize()
                values = [t.value for t in tokens if t.type.name == 'IDENTIFIER']
                self.assertIn(name, values, '%s 被切碎了：%s'
                              % (name, [(t.type.name, t.value) for t in tokens]))

    def test_用户自定义同名段落压过内置映射(self):
        """既有机制的回归确认：用户显式定义了 `写` 就不该再被顶成内置
        （`_user_defined_functions` 那条判据，见 src/code_generator.py 的
        `expr.name not in self._user_defined_functions`）。"""
        code = _compile('段 写(甲)：\n    返 甲。\n\n写(1)。\n')
        self.assertNotIn('_light_builtin.写入输出(1)', code)


if __name__ == '__main__':
    unittest.main()
