# -*- coding: utf-8 -*-
"""v7 单 26 回归用例（族 5）：三处独立缺陷的平台/版本无关守卫。

1. `掷` 是文档承诺的 throw 同义别名（l0-core.md:97 等），此前从未在 src/ 落地，
   导致 examples/L0_core/07_试_异常处理.light 里的 掷(...) 被当未定义标识符。
2. 带名捕获 `捕 错误信息：` 必须绑定异常变量（生成 except ... as 错误信息）。
   07 原来写裸 `捕：`，靠一个语言里根本不存在的隐式 错误信息 —— 属示例错误，已破例改。
3. 引 SQL（带标签）块：连接过去用 connect('{标签}.db')，在 CWD 落持久磁盘文件、跨运行
   存活，令非幂等 CREATE TABLE 第二次运行报错；且动词判定没剥掉 -- 注释行，SELECT 前有
   注释时被误判成 DDL（生成 _e{n} 而非 _q{n}）。

判据全部走「编译 .light → 检查产物源码 / eval 产物」，不依赖具体 Python 版本或平台，
也不依赖任何外部工具链。
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

from light_parser_v3 import LightParser          # noqa: E402
from code_generator import PythonCodeGenerator   # noqa: E402
from lexer import Lexer                           # noqa: E402
from keywords import KEYWORDS_EXCEPTION, ALL_KEYWORDS  # noqa: E402


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


class TestThrowAlias(unittest.TestCase):
    def test_zhi_is_registered_keyword(self):
        # 缺陷守卫：'掷' 必须在异常关键字集合、进而在 ALL_KEYWORDS 里
        self.assertIn('掷', KEYWORDS_EXCEPTION)
        self.assertIn('掷', ALL_KEYWORDS)

    def test_zhi_lexes_as_keyword(self):
        # lexer 必须把独立的 掷 识别成 KEYWORD，而非 IDENTIFIER
        toks = Lexer().tokenize('掷("boom")')
        kw = [t for t in toks if t.value == '掷']
        self.assertTrue(kw, '掷 未被词法器产出')
        self.assertEqual(kw[0].type.name, 'KEYWORD')

    def test_zhi_compiles_to_raise(self):
        code = '段 检查(n)：\n  若 n <= 0 则：\n    掷("必须为正")\n  返回 n\n'
        py = _compile(code)
        # 注意：不能只断言 py 里有 'raise' —— 产物前导本来就有 raise RuntimeError('FFI 不可用…')，
        # 那种判据在缺陷未修时也会绿（本用例最初就踩了这个坑）。判据必须锚到本条语句：
        # _generate_throw_stmt 对非异常名的值发一对 `_light_exc = <值>` + `raise _light_exc ...`。
        lines = [l.strip() for l in py.splitlines()]
        self.assertIn('_light_exc = "必须为正"', lines)
        self.assertTrue(any(l.startswith('raise _light_exc') for l in lines),
                        '掷 未生成 raise _light_exc 语句')
        # 且不得把 掷 当普通函数调用漏出去
        self.assertNotIn('掷(', py)
        ast.parse(py)

    def test_zhi_matches_pao(self):
        # 掷 与 抛 应生成等价的 raise —— 同义别名
        base = '段 f(n)：\n  {kw}("x")\n  返回 n\n'
        py_zhi = _compile(base.format(kw='掷'))
        py_pao = _compile(base.format(kw='抛'))
        norm = lambda s: '\n'.join(l for l in s.splitlines() if 'raise' in l)
        self.assertEqual(norm(py_zhi), norm(py_pao))


def _exec(py):
    """exec 产物并返回命名空间（判据要落到运行期，不能只看源码）。"""
    ns = {'__name__': '_light_test_mod'}
    exec(compile(py, '<light-product>', 'exec'), ns)
    return ns


class TestThrowNewException(unittest.TestCase):
    """`抛出 新建 异常("消息")` 的运行期 NameError 缺陷守卫。

    `新建 X(...)` 解析成 ClassInstantiation，而 _generate_throw_stmt 原先只认
    Identifier / ParagraphCall 两种形态，中文异常名走到通用尾巴就被原样发成
    `_light_exc = 异常("消息")` —— 产物里 异常 这个名字从未绑定，编译期全绿、
    运行到该行才 NameError。判据必须运行产物，只看源码里有没有 raise 不够。
    """

    def test_new_exception_raises_at_runtime(self):
        ns = _exec(_compile('段 f()：\n  抛出 新建 异常("boom")\n'))
        with self.assertRaises(Exception) as cm:
            ns['f']()
        # 缺陷未修时这里是 NameError（NameError 也是 Exception 的子类，
        # 所以必须把类型钉死成 Exception 本身，且校验消息真的带上了）
        self.assertIs(type(cm.exception), Exception)
        self.assertEqual(cm.exception.args, ('boom',))

    def test_new_exception_maps_to_python_type(self):
        py = _compile('段 f()：\n  抛出 新建 运行时错误("x")\n')
        lines = [l.strip() for l in py.splitlines()]
        self.assertIn('raise RuntimeError("x")', lines)
        # 不得再退化成未绑定名的 _light_exc 赋值
        self.assertNotIn('_light_exc = 运行时错误("x")', lines)
        ns = _exec(py)
        with self.assertRaises(RuntimeError) as cm:
            ns['f']()
        self.assertEqual(cm.exception.args, ('x',))

    def test_new_exception_without_args(self):
        py = _compile('段 f()：\n  抛出 新建 值错误()\n')
        self.assertIn('raise ValueError()', [l.strip() for l in py.splitlines()])
        ns = _exec(py)
        with self.assertRaises(ValueError):
            ns['f']()

    def test_new_form_matches_direct_form(self):
        # 新建 形态与直呼形态必须发出同一条 raise
        # 产物前导本来就有若干 raise（FFI 不可用、断言失败等），必须先剔掉
        _前导 = ('FFI 不可用', 'raise ImportError()', 'raise AssertionError(_msg)')
        norm = lambda s: [l.strip() for l in s.splitlines()
                          if l.strip().startswith('raise ')
                          and not any(p in l for p in _前导)]
        py_new = _compile('段 f()：\n  抛出 新建 键错误("k")\n')
        py_direct = _compile('段 f()：\n  抛出 键错误("k")\n')
        self.assertEqual(norm(py_new), norm(py_direct))
        self.assertEqual(norm(py_new), ['raise KeyError("k")'])

    def test_unknown_class_still_uses_generic_tail(self):
        # 修复只针对 exception_name_map 里的中文异常名；自定义类必须仍走通用尾巴，
        # 否则会把用户自己的异常类静默换成内置类型。
        py = _compile('类 我的错误：\n  段 初始化(己)：\n    过\n\n段 f()：\n  抛出 新建 我的错误()\n')
        lines = [l.strip() for l in py.splitlines()]
        self.assertTrue(any(l.startswith('_light_exc = ') for l in lines),
                        '自定义异常类被错误地并进了内置异常映射分支')
        ast.parse(py)


class TestCatchVarBinding(unittest.TestCase):
    def test_named_catch_binds_variable(self):
        code = '试：\n  掷("坏了")\n捕 错误信息：\n  打印(错误信息)\n'
        py = _compile(code)
        self.assertIn('except Exception as 错误信息:', py)
        ast.parse(py)

    def test_bare_catch_has_no_binding(self):
        # 裸捕不应凭空绑定任何名字（这正是 07 老写法的坑）
        code = '试：\n  掷("坏了")\n捕：\n  打印("捕获")\n'
        py = _compile(code)
        self.assertIn('except Exception:', py)
        self.assertNotIn('as 错误信息', py)


class TestSqlEmbed(unittest.TestCase):
    _SQL = (
        '引 SQL 成绩:\n'
        '    CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT);\n'
        '    INSERT INTO students(name) VALUES (?);\n'
        '    -- 这条查询前面有注释，动词必须能穿过注释识别成 SELECT\n'
        '    SELECT name FROM students WHERE name > ?;\n'
        '结束引\n'
        '\n'
        '段 主()：\n'
        '    设 r = l3_sql_成绩_e0()\n'
        '    返回 r\n'
    )

    def test_connection_is_in_memory_not_disk(self):
        py = _compile(self._SQL)
        self.assertIn("connect(':memory:')", py)
        # 不得再落任何 {标签}.db 磁盘文件
        self.assertNotIn("'成绩.db'", py)
        self.assertNotIn('成绩.db', py)

    def test_select_after_comment_becomes_query_fn(self):
        py = _compile(self._SQL)
        # 语句下标：0=CREATE、1=INSERT、2=（注释行 + ）SELECT
        # SELECT 应生成查询函数 _q{n}（返回 list[dict]），不能被误判成 DDL 的 _e{n}
        self.assertIn('def l3_sql_成绩_q2(', py)
        self.assertNotIn('def l3_sql_成绩_e2(', py)
        self.assertIn('fetchall()', py)
        ast.parse(py)

    def test_ddl_still_execs(self):
        py = _compile(self._SQL)
        self.assertIn('def l3_sql_成绩_e0(', py)  # CREATE TABLE
        self.assertIn('def l3_sql_成绩_e1(', py)  # INSERT


if __name__ == '__main__':
    unittest.main()
