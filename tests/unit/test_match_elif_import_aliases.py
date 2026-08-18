# -*- coding: utf-8 -*-
"""v7 单 27 回归用例（族 1）：四处独立缺陷的平台/版本无关守卫。

对应 examples/L0_core/09、03、10 三个示例的打红根因：

1. `匹`/`例` 是 L0 冻结表承诺的 match/case 单字（docs/language/l0-core.md 模式匹配一节、
   docs/language/keywords.md:18），此前从未在 src/ 落地；且 `例 数：` 这种
   **裸内置类型名做类型模式**（无绑定名）是规范支持的写法
   （docs/完整语法参考.md:534-544），旧实现会把它当变量捕获，
   导致「name capture 使后续分支不可达」而整块编译失败。
   `匹` 还必须进 lexer 的 _COMPOUND_SAFE_SINGLE_KEYWORDS —— 词库里 89 个 `匹X`
   开头的标识符否则会被最长匹配切开。

2. `或若` 是 `否则若` 的 elif 同义别名（迁移工具 tools/v33_to_v40.py 已把
   `否则如果` 映射到 `或若`），此前 parser 不认，03 整块解析失败。

3. `导 X 自 Y` 模块绑定形式缺失：parser 只认 `导入 X 从 Y`，`自` 被自赋值分支抢走。
   口径见 docs/language/l0-core.md 模块一节 —— `自` 只作来源连接词（self 是 `己`）：
   `导 X 自 Y` ≡ `import Y as X`，与 `导入 X 从 Y` ≡ `from Y import X` 并列。

4. `obj.长度(实参)` 被无条件改写成 `len(obj)`：实参被整个丢掉、并对命名空间自身求 len。
   `字符串处理.长度(文本)` 因此译成 `len(字符串处理)`，编译期无声通过、
   运行期报 object of type 'module' has no len()。只有**无实参**的
   `列表.长度()` 才是「求这个对象的长度」。

判据全部走「编译 .light → 检查产物源码」或直接查关键字表/词法器，
不依赖具体 Python 版本或平台，也不依赖任何外部工具链。
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
from keywords import (                                       # noqa: E402
    ALL_KEYWORDS, KEYWORDS_MATCH, KEYWORDS_CONDITION, BUILTIN_TYPES,
)


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


def _body(py):
    """只取产物尾部的用户代码，避开体量巨大的运行时前导。"""
    marker = 'return _s.join('
    idx = py.rfind(marker)
    return py[py.index('\n', idx) + 1:] if idx != -1 else py


class TestMatchSingleCharAliases(unittest.TestCase):
    def test_aliases_registered(self):
        for ch in ('匹', '例'):
            self.assertIn(ch, KEYWORDS_MATCH, '%s 未进 KEYWORDS_MATCH' % ch)
            self.assertIn(ch, ALL_KEYWORDS, '%s 未进 ALL_KEYWORDS' % ch)

    def test_pi_is_compound_safe(self):
        # 缺陷守卫：`匹` 不设复合安全，词库里 匹配度/匹敌 之类标识符会被切开
        self.assertIn('匹', _COMPOUND_SAFE_SINGLE_KEYWORDS)
        toks = Lexer().tokenize('设 匹配度 为 1')
        names = [t.value for t in toks]
        self.assertIn('匹配度', names, '匹配度 被最长匹配切开了')

    def test_pi_lexes_as_keyword_when_standalone(self):
        toks = Lexer().tokenize('匹 值：\n  例：\n    印(1)\n')
        kw = [t for t in toks if t.value in ('匹', '例')]
        self.assertEqual(len(kw), 2)
        for t in kw:
            self.assertEqual(t.type.name, 'KEYWORD')

    def test_alias_generates_match_case(self):
        py = _body(_compile('匹 值：\n  例 数：\n    印("num")\n'
                            '  例 串：\n    印("str")\n'
                            '  例：\n    印("other")\n'))
        self.assertIn('match 值:', py)
        # `例 数：` 是**类型模式**而非变量捕获；数 覆盖 int/float 两种
        self.assertIn('case int() | float():', py)
        self.assertIn('case str():', py)
        self.assertIn('case _:', py)
        # 变量捕获会写成 `case 数:`（无括号），那样后续分支全部不可达
        self.assertNotIn('case 数:', py)
        ast.parse(py)

    def test_alias_equals_full_form(self):
        # 匹/例 与 匹配/情况 必须生成完全一致的 match 块 —— 同义别名
        short = _body(_compile('匹 值：\n  例 数：\n    印(1)\n  例：\n    印(2)\n'))
        full = _body(_compile('匹配 值：\n  情况 数：\n    印(1)\n  情况：\n    印(2)\n'))
        self.assertEqual(short, full)

    def test_bare_builtin_type_names_are_type_patterns(self):
        # 裸类型名走类型模式这条路，靠的是 BUILTIN_TYPES 这张表
        for name in ('数', '串', '列'):
            self.assertIn(name, BUILTIN_TYPES)


class TestElifAlias(unittest.TestCase):
    def test_huoruo_registered(self):
        self.assertIn('或若', KEYWORDS_CONDITION)
        self.assertIn('或若', ALL_KEYWORDS)

    def test_huoruo_generates_elif(self):
        py = _body(_compile('若 x > 10 则：\n  印("a")\n'
                            '或若 x > 5 则：\n  印("b")\n'
                            '否：\n  印("c")\n'))
        self.assertIn('elif', py)
        self.assertIn('else:', py)
        ast.parse(py)

    def test_huoruo_equals_fouzeruo(self):
        tpl = ('若 x > 10 则：\n  印("a")\n'
               '{kw} x > 5 则：\n  印("b")\n'
               '否：\n  印("c")\n')
        self.assertEqual(_body(_compile(tpl.format(kw='或若'))),
                         _body(_compile(tpl.format(kw='否则若'))))


class TestImportZiForm(unittest.TestCase):
    def test_same_name_needs_no_as(self):
        py = _body(_compile('导 数学 自 数学\n印("x")\n'))
        self.assertIn('import 数学', py)
        self.assertNotIn(' as ', py)
        # 不得退化成 from 数学 import 数学（那会 ImportError）
        self.assertNotIn('from 数学 import', py)
        ast.parse(py)

    def test_different_name_becomes_as(self):
        py = _body(_compile('导 m 自 数学\n印("x")\n'))
        self.assertIn('import 数学 as m', py)
        ast.parse(py)

    def test_cong_form_still_imports_symbol(self):
        # `从` 的符号导入语义不受影响
        py = _body(_compile('导入 平方根 从 数学\n印("x")\n'))
        self.assertIn('from 数学 import 平方根', py)
        ast.parse(py)


class TestLengthMemberCall(unittest.TestCase):
    def test_length_with_arg_stays_a_real_call(self):
        py = _body(_compile('设 文本 为 "abcd"\n印(字符串处理.长度(文本))\n'))
        self.assertIn('字符串处理.长度(文本)', py)
        # 缺陷守卫：实参被吞、对命名空间求 len 的旧错译
        self.assertNotIn('len(字符串处理)', py)
        ast.parse(py)

    def test_length_without_arg_still_becomes_len(self):
        py = _body(_compile('设 表 为 [1,2,3]\n印(表.长度())\n'))
        self.assertIn('len(表)', py)
        ast.parse(py)


class TestMathStdlibEnglishAliases(unittest.TestCase):
    """stdlib/数学.py 的模块文档字符串承诺了一批英文名，此前一个都没绑定。"""

    @classmethod
    def setUpClass(cls):
        stdlib_dir = os.path.join(_ROOT, 'stdlib')
        if stdlib_dir not in sys.path:
            sys.path.insert(0, stdlib_dir)
        import importlib
        cls.mod = importlib.import_module('数学')

    def test_documented_aliases_exist(self):
        for name in ('pi', 'pow', 'sqrt', 'sin', 'cos', 'tan',
                     'random', 'floor', 'ceil', 'round'):
            self.assertTrue(hasattr(self.mod, name), '数学.%s 缺失' % name)

    def test_pi_is_a_value_not_a_function(self):
        # 示例里写 数学.pi（属性），不是 数学.pi()
        self.assertAlmostEqual(self.mod.pi, 3.141592653589793, places=12)

    def test_chinese_names_unchanged(self):
        # 补别名不得改动既有中文接口的语义
        self.assertEqual(self.mod.幂(2, 10), 1024)
        self.assertEqual(self.mod.四舍五入(2.345, 2), 2.35)
        self.assertEqual(self.mod.向下取整(2.9), 2)


if __name__ == '__main__':
    unittest.main()
