# -*- coding: utf-8 -*-
"""引 C 块的 ctypes 绑定回归用例（v7 单 25）

为什么不「跑产物」来验：`引 C` 只有在机器上真有 gcc/cc/clang 时才会编译、
dlopen 并真正绑定；开发机（Windows）三个编译器都没有，产物走占位 lambda 分支，
崩不崩根本测不出来——那把尺子在本机是瞎的，正是它让「无 argtypes」的缺陷一路漏到
FreeBSD runner 上才以 SIGSEGV 暴露。

所以本用例改为**平台无关**的判据：编译一段 引 C 源码，从产物里把生成的类型映射
（`_LIGHT_C_CTYPE` + `_light_c_type`）与签名正则单独取出来求值，直接断言
「C 声明 → ctypes 类型」的对应关系，以及绑定循环确实设了 restype/argtypes。
"""

import ast
import ctypes
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

_SOURCE = '''引 C:
    double 快速求和(double* arr, int n) {
        double s = 0.0;
        for (int i = 0; i < n; i++) s += arr[i];
        return s;
    }

    int 阶乘(int n) {
        if (n <= 1) return 1;
        return n * 阶乘(n - 1);
    }

    void 无返回(void) {
    }
结束引

打印("ok")
'''


def _compile(code):
    parser = LightParser()
    tree = parser.parse(code)
    if tree is None:
        raise RuntimeError('解析失败:\n' + '\n'.join(getattr(parser, 'errors', [])))
    return PythonCodeGenerator().generate(tree)


class TestCEmbedFFIBinding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.product = _compile(_SOURCE)
        module = ast.parse(cls.product)
        # 只挑出类型映射表与映射函数，单独求值（不执行整个产物，避免触发编译器探测）
        picked = []
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name == '_light_c_type':
                picked.append(node)
            elif isinstance(node, ast.Assign) and any(
                    getattr(t, 'id', '') == '_LIGHT_C_CTYPE' for t in node.targets):
                picked.append(node)
        if len(picked) < 2:
            raise AssertionError('产物里找不到 _LIGHT_C_CTYPE / _light_c_type')
        ns = {'_light_ctypes': ctypes}
        exec(compile(ast.Module(body=picked, type_ignores=[]), '<gen>', 'exec'), ns)
        cls.c_type = staticmethod(ns['_light_c_type'])

    def test_return_and_scalar_params_mapped(self):
        """标量类型按 C 语义映射，不再一律当 double"""
        self.assertIs(self.c_type('double'), ctypes.c_double)
        self.assertIs(self.c_type('int'), ctypes.c_int)
        self.assertIs(self.c_type('float'), ctypes.c_float)
        self.assertIs(self.c_type('int n'), ctypes.c_int)
        self.assertIsNone(self.c_type('void'))

    def test_pointer_params_mapped(self):
        """指针形参映射为 POINTER(...)/c_char_p，而不是被当成整数传值"""
        self.assertIs(self.c_type('double* arr'), ctypes.POINTER(ctypes.c_double))
        self.assertIs(self.c_type('double *arr'), ctypes.POINTER(ctypes.c_double))
        self.assertIs(self.c_type('int* p'), ctypes.POINTER(ctypes.c_int))
        self.assertIs(self.c_type('char* s'), ctypes.c_char_p)

    def test_signature_regex_extracts_full_signature(self):
        """签名正则要抓到 (返回类型, 函数名, 形参串) 三元组，含中文函数名"""
        import re
        m = re.search(r"_LIGHT_C_SIGS = _light_l4_re\.findall\(r'(.+?)', _LIGHT_C_CODE\)",
                      self.product)
        self.assertIsNotNone(m, '产物里找不到签名正则')
        sigs = re.findall(m.group(1), _SOURCE)
        self.assertIn(('double', '快速求和', 'double* arr, int n'), sigs)
        self.assertIn(('int', '阶乘', 'int n'), sigs)

    def test_binding_sets_restype_and_argtypes(self):
        """绑定循环必须按签名设 restype 与 argtypes（缺 argtypes 即是 SIGSEGV 的来源）"""
        self.assertIn('.restype = _light_c_type(_LIGHT_C_RET)', self.product)
        self.assertIn('.argtypes = _LIGHT_C_AT', self.product)
        # 旧实现把每个函数的返回类型硬编码成 c_double —— 不允许回退
        self.assertNotIn('.restype = _light_ctypes.c_double', self.product)

    def test_product_is_valid_python(self):
        """产物本身必须是合法 Python（防止上面的断言在语法坏掉的产物上仍然通过）"""
        ast.parse(self.product)


if __name__ == '__main__':
    unittest.main(verbosity=2)
