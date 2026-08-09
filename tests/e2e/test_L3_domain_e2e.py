# -*- coding: utf-8 -*-
"""
L3 领域嵌入层 E2E 测试
覆盖：SQL（sqlite3 建表/插入/查询/聚合）、正则（验证/提取/命名捕获组/替换）、数学（解方程/求导/积分/矩阵/化简）
"""
import os
import sys
import io
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run_light(code: str) -> str:
    """编译并运行光明代码，返回标准输出"""
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        errors = '\n'.join(getattr(parser, 'errors', []))
        raise RuntimeError(f"解析失败:\n{errors}")

    gen = PythonCodeGenerator()
    py_code = gen.generate(ast)

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        namespace = {'__name__': '__main__'}
        exec(py_code, namespace)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


# ==========================================================
# 1. L3 SQL 嵌入测试
# ==========================================================
class TestL3_SQL_E2E(unittest.TestCase):
    """L3 SQL 领域嵌入：建表/插入/查询/聚合"""

    def test_create_table(self):
        """建表 + 插入 + 查询"""
        code = '''
引 Python:
    import sqlite3
    _L3_SQL_CONN = {}
    def _conn(db=":memory:"):
        if db not in _L3_SQL_CONN:
            _L3_SQL_CONN[db] = sqlite3.connect(db)
            _L3_SQL_CONN[db].row_factory = sqlite3.Row
        return _L3_SQL_CONN[db]
    def l3_sql_exec(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        _conn(db).commit()
        return c.rowcount
    def l3_sql_query(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        return [dict(r) for r in c.fetchall()]
结束引

设 DB = ":memory:"
l3_sql_exec(DB, "CREATE TABLE t (id INTEGER, name TEXT)")
l3_sql_exec(DB, "INSERT INTO t VALUES (?,?)", [1, "张三"])
l3_sql_exec(DB, "INSERT INTO t VALUES (?,?)", [2, "李四"])
设 结果 = l3_sql_query(DB, "SELECT * FROM t ORDER BY id")
打印("行数:", 长度(结果))
遍历 行 于 结果:
    打印(行["id"], 行["name"])
'''
        output = _run_light(code)
        self.assertIn("行数: 2", output)
        self.assertIn("1 张三", output)
        self.assertIn("2 李四", output)

    def test_aggregate_query(self):
        """聚合查询：AVG/MAX/MIN/COUNT"""
        code = '''
引 Python:
    import sqlite3
    _L3_SQL_CONN = {}
    def _conn(db=":memory:"):
        if db not in _L3_SQL_CONN:
            _L3_SQL_CONN[db] = sqlite3.connect(db)
            _L3_SQL_CONN[db].row_factory = sqlite3.Row
        return _L3_SQL_CONN[db]
    def l3_sql_exec(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        _conn(db).commit()
        return c.rowcount
    def l3_sql_query(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        return [dict(r) for r in c.fetchall()]
结束引

设 DB = ":memory:"
l3_sql_exec(DB, "CREATE TABLE scores (name TEXT, score REAL)")
l3_sql_exec(DB, "INSERT INTO scores VALUES (?,?)", ["张三", 88.5])
l3_sql_exec(DB, "INSERT INTO scores VALUES (?,?)", ["李四", 92.0])
l3_sql_exec(DB, "INSERT INTO scores VALUES (?,?)", ["王五", 76.3])
设 统计 = l3_sql_query(DB, "SELECT AVG(score) as avg, MAX(score) as mx, COUNT(*) as n FROM scores")
设 s = 统计[0]
打印(s["avg"])
打印(s["mx"])
打印(s["n"])
'''
        output = _run_light(code)
        self.assertIn("85.6", output)
        self.assertIn("92.0", output)
        self.assertIn("3", output)

    def test_parameterized_query(self):
        """参数化查询防注入"""
        code = '''
引 Python:
    import sqlite3
    _L3_SQL_CONN = {}
    def _conn(db=":memory:"):
        if db not in _L3_SQL_CONN:
            _L3_SQL_CONN[db] = sqlite3.connect(db)
            _L3_SQL_CONN[db].row_factory = sqlite3.Row
        return _L3_SQL_CONN[db]
    def l3_sql_exec(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        _conn(db).commit()
        return c.rowcount
    def l3_sql_query(db, sql, params=()):
        c = _conn(db).cursor()
        c.execute(sql, tuple(params))
        return [dict(r) for r in c.fetchall()]
结束引

设 DB = ":memory:"
l3_sql_exec(DB, "CREATE TABLE users (name TEXT)")
l3_sql_exec(DB, "INSERT INTO users VALUES (?)", ["admin"])
l3_sql_exec(DB, "INSERT INTO users VALUES (?)", ["guest"])
设 恶意输入 = "admin' OR '1'='1"
设 结果 = l3_sql_query(DB, "SELECT * FROM users WHERE name=?", [恶意输入])
打印("找到:", 长度(结果))
'''
        output = _run_light(code)
        self.assertIn("找到: 0", output)


# ==========================================================
# 2. L3 正则嵌入测试
# ==========================================================
class TestL3_Regex_E2E(unittest.TestCase):
    """L3 正则嵌入：验证/提取/命名捕获组/替换"""

    def test_email_validation(self):
        """邮箱验证"""
        code = '''
引 Python:
    import re
    def l3_re_match(pattern, text):
        return re.fullmatch(pattern, text) is not None
结束引

设 邮箱正则 = "[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+"
打印(l3_re_match(邮箱正则, "test@light-lang.org"))
打印(l3_re_match(邮箱正则, "bad-email@"))
打印(l3_re_match(邮箱正则, "user@example.com"))
'''
        output = _run_light(code)
        self.assertIn("True", output)
        self.assertIn("False", output)

    def test_extract_phone_numbers(self):
        """提取手机号"""
        code = '''
引 Python:
    import re
    def l3_re_findall(pattern, text):
        return re.findall(pattern, text)
结束引

设 文本 = "客服: 13812345678, 备用: 15987654321, 座机: 010-12345678"
设 手机正则 = "1[3-9]\\d{9}"
设 号码 = l3_re_findall(手机正则, 文本)
打印(长度(号码))
遍历 n 于 号码:
    打印(n)
'''
        output = _run_light(code)
        self.assertIn("2", output)
        self.assertIn("13812345678", output)
        self.assertIn("15987654321", output)

    def test_named_groups(self):
        """命名捕获组"""
        code = '''
引 Python:
    import re
    def l3_re_named_groups(pattern, text):
        m = re.match(pattern, text)
        return m.groupdict() if m else {}
结束引

设 日期正则 = "(?P<年>\\d{4})-(?P<月>\\d{2})-(?P<日>\\d{2})"
设 d = l3_re_named_groups(日期正则, "2026-08-04")
打印(d["年"])
打印(d["月"])
打印(d["日"])
'''
        output = _run_light(code)
        self.assertIn("2026", output)
        self.assertIn("08", output)
        self.assertIn("04", output)

    def test_regex_substitution(self):
        """正则替换"""
        code = '''
引 Python:
    import re
    def l3_re_sub(pattern, repl, text):
        return re.sub(pattern, repl, text)
结束引

设 文本 = "日期: 2026-08-04, 截止: 2026-12-31"
设 新文本 = l3_re_sub("(\\d{4})-(\\d{2})-(\\d{2})", "\\1/\\2/\\3", 文本)
打印(新文本)
'''
        output = _run_light(code)
        self.assertIn("2026/08/04", output)
        self.assertIn("2026/12/31", output)


# ==========================================================
# 3. L3 数学嵌入测试
# ==========================================================
class TestL3_Math_E2E(unittest.TestCase):
    """L3 数学嵌入：解方程/求导/积分/矩阵/化简"""

    def test_solve_quadratic(self):
        """解一元二次方程"""
        code = '''
引 Python:
    from sympy import symbols, Eq, solve
    def l3_math_solve_quadratic(a, b, c_val):
        x = symbols('x')
        sol = solve(Eq(a*x**2 + b*x + c_val, 0), x)
        return [float(s) if s.is_real else str(s) for s in sol]
结束引

设 解 = l3_math_solve_quadratic(2, 5, -3)
打印(解)
'''
        output = _run_light(code)
        self.assertIn("-3.0", output)
        self.assertIn("0.5", output)

    def test_derivative(self):
        """求导"""
        code = '''
引 Python:
    import sympy as sp
    def l3_math_derivative(expr_str):
        x = sp.symbols('x')
        expr = sp.sympify(expr_str)
        return str(sp.diff(expr, x))
结束引

打印(l3_math_derivative("x**3 + 2*x**2 - 5*x + 7"))
'''
        output = _run_light(code)
        self.assertIn("3*x**2 + 4*x - 5", output)

    def test_integrate(self):
        """定积分"""
        code = '''
引 Python:
    import sympy as sp
    def l3_math_integrate(expr, a, b):
        x = sp.symbols('x')
        res = sp.integrate(sp.sympify(expr), (x, a, b))
        return float(res.evalf())
结束引

打印(l3_math_integrate("sin(x)", 0, 3.141592653589793))
'''
        output = _run_light(code)
        self.assertIn("2.0", output)

    def test_matrix_multiply(self):
        """矩阵乘法"""
        code = '''
引 Python:
    from sympy import Matrix
    def l3_math_matrix_mult(A, B):
        MA = Matrix(A); MB = Matrix(B)
        R = MA * MB
        return [list(row) for row in R.tolist()]
结束引

设 A = [[1, 2, 3], [4, 5, 6]]
设 B = [[7, 8], [9, 10], [11, 12]]
设 C = l3_math_matrix_mult(A, B)
打印(长度(C))
遍历 c 于 C:
    打印(长度(c))
'''
        output = _run_light(code)
        self.assertIn("2", output)  # 2 行

    def test_simplify(self):
        """代数化简"""
        code = '''
引 Python:
    import sympy as sp
    def l3_math_simplify(expr_str):
        return str(sp.simplify(sp.sympify(expr_str)))
结束引

打印(l3_math_simplify("(x+1)*(x-1) + (x-2)**2"))
'''
        output = _run_light(code)
        self.assertIn("2*x**2 - 4*x + 3", output)


if __name__ == '__main__':
    unittest.main(verbosity=2)