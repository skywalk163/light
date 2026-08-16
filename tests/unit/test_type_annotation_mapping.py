# -*- coding: utf-8 -*-
"""类型注解映射回归测试（单 24）

背景：`设 姓名: 字符串 为 "张三"` 曾生成 `姓名: 字符串 = "张三"` —— 中文类型名
没被映射成 `str`，原样泄漏进 Python 注解。

**为什么这份测试不去「跑产物」**：Python 3.14 起 PEP 649/749 让变量注解延迟求值，
泄漏的名字在 3.14 上根本不会被求值，跑产物一路绿；而 3.14 之前注解立即求值，
同一份产物直接 `NameError`。也就是说「跑产物」这把尺子在 3.14 开发机上是瞎的
（单 24 的红就是只在 FreeBSD CI 上暴露、本机复现不出来）。

所以这里改成**显式 eval 每一条注解表达式**：无论哪个 Python 版本，泄漏的中文
类型名都会稳定地抛 NameError。
"""

import ast
import io
import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in (_src_dir, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _compile_light(code: str) -> str:
    """把光明源码编译成 Python 产物文本"""
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        errors = '\n'.join(getattr(parser, 'errors', []))
        raise RuntimeError(f"解析失败:\n{errors}")
    return PythonCodeGenerator().generate(tree)


def _annotation_sources(py_code: str):
    """取出产物里所有注解表达式的源码文本（变量注解 + 形参 + 返回值）"""
    out = []
    for node in ast.walk(ast.parse(py_code)):
        if isinstance(node, ast.AnnAssign) and node.annotation is not None:
            out.append(ast.unparse(node.annotation))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                out.append(ast.unparse(node.returns))
            args = node.args
            for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                if arg.annotation is not None:
                    out.append(ast.unparse(arg.annotation))
    return out


def _exec_product(py_code: str) -> dict:
    """执行产物，返回其命名空间（吞掉产物的标准输出）"""
    namespace = {'__name__': '__main__'}
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(py_code, namespace)
    finally:
        sys.stdout = old_stdout
    return namespace


# 覆盖单 24 里实测泄漏过的全部形态：裸别名、联合类型、裸可空前缀、
# 泛型内层、以及「泛型套泛型且内层带逗号」（曾被 split(',') 劈成 `字典<字符串`）
_SOURCE = '''
设 姓名: 字符串 为 "张三"
设 身高: 浮点 为 1.75
设 编号: 整数|字符串 为 7
设 别名: 可空字符串 为 空
设 分数表: 列表<浮点> 为 【1.5, 2.5】
设 档案: 列表<字典<字符串, 整数|字符串>> 为 【】

段落 拼接(前缀: 字符串, 后缀: 字符串) 返回 字符串:
    返回 前缀 + 后缀

段落 安全除法(甲: 浮点, 乙: 浮点) 返回 浮点|字符串:
    返回 甲

打印(姓名)
'''


class TestAnnotationTypeMapping(unittest.TestCase):
    """产物注解里不得残留未映射的中文类型名"""

    @classmethod
    def setUpClass(cls):
        cls.py_code = _compile_light(_SOURCE)
        cls.annotations = _annotation_sources(cls.py_code)

    def test_annotations_are_emitted(self):
        """先确认这份源码真的产出了注解，否则下面的断言会退化成永真式"""
        self.assertGreaterEqual(
            len(self.annotations), 8,
            f"注解数量异常偏少，测试可能没测到东西: {self.annotations}")

    def test_every_annotation_is_evaluable(self):
        """逐条 eval 注解表达式——泄漏的中文类型名在任何 Python 版本上都会 NameError

        这是本测试的核心断言：不依赖 PEP 649 的求值时机。
        """
        namespace = _exec_product(self.py_code)
        for expr in self.annotations:
            with self.subTest(注解=expr):
                try:
                    eval(expr, namespace)
                except NameError as exc:
                    self.fail(f"注解 {expr!r} 求值失败（中文类型名泄漏进产物）: {exc}")

    def test_no_builtin_chinese_type_name_leaks(self):
        """产物注解里不得出现内置中文类型名

        与上一条互补：上一条抓「求值炸」，这一条抓「求值不炸但语义已错」
        （比如中文类型名恰好和用户定义的类同名时）。
        用户自定义类名不在此列——它们本就该原样透传。
        """
        builtin_cn = set(PythonCodeGenerator._LIGHT_TYPE_MAP)
        for expr in self.annotations:
            names = {n.id for n in ast.walk(ast.parse(expr, mode='eval'))
                     if isinstance(n, ast.Name)}
            leaked = names & builtin_cn
            self.assertFalse(
                leaked, f"注解 {expr!r} 残留未映射的内置中文类型名: {sorted(leaked)}")


class TestMapTypeTable(unittest.TestCase):
    """_map_type 各形态的直接断言（定位用：上面的产物级测试红了看这里）"""

    @classmethod
    def setUpClass(cls):
        cls.gen = PythonCodeGenerator()

    def test_bare_aliases(self):
        """曾缺失的别名：字符串/浮点 —— 单 24 的直接根因"""
        self.assertEqual(self.gen._map_type('字符串'), 'str')
        self.assertEqual(self.gen._map_type('浮点'), 'float')
        self.assertEqual(self.gen._map_type('浮点数'), 'float')
        self.assertEqual(self.gen._map_type('整数'), 'int')

    def test_union(self):
        self.assertEqual(self.gen._map_type('整数|字符串'), 'int | str')
        self.assertEqual(self.gen._map_type('整数|浮点|字符串'), 'int | float | str')

    def test_nullable_prefix(self):
        self.assertEqual(self.gen._map_type('可空字符串'), 'Optional[str]')
        self.assertEqual(self.gen._map_type('可空整数'), 'Optional[int]')

    def test_generic_inner_mapped(self):
        self.assertEqual(self.gen._map_type('列表<浮点>'), 'list[float]')
        self.assertEqual(self.gen._map_type('列表<整数|浮点>'), 'list[int | float]')

    def test_nested_generic_not_split_by_comma(self):
        """内层逗号不得把嵌套泛型劈坏（曾产出 `list[字典<字符串]`）"""
        self.assertEqual(
            self.gen._map_type('列表<字典<字符串, 整数|字符串>>'), 'list[dict]')

    def test_user_type_passes_through(self):
        """用户自定义类名原样透传，不要误伤"""
        self.assertEqual(self.gen._map_type('学生'), '学生')


if __name__ == '__main__':
    unittest.main()
