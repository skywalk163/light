# -*- coding: utf-8 -*-
"""任务 C3-5：泛型形参/返回类型注解真发射 + 产物真跑。

改动前（实测）：`段落 压入 接收 值: T：` 产出 `def 压入(self, 值):`——注解被
静默丢掉，类头 `T = TypeVar('T')` 与 `class 栈(Generic[T])` 成了孤立声明，
`get_type_hints` 解析不出任何形参类型。

本文件是「判据表靠源码级断言守单点」口径之外的**真跑**用例：既断言产物形态
（注解语法在位），又 `exec` 产物证明能跑、`get_type_hints` 真能解析出 TypeVar。
不做 `assert 'T' in py_code` 那种字符串断言式假测试（第二轮明令禁止）。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def _transpile(source: str) -> str:
    """用产品实际生成器编译光明源码 → Python 产物。"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    module = LightParser().parse(source)
    return PythonCodeGenerator().generate(module)


def _exec_product(py_code: str) -> dict:
    ns = {}
    exec(compile(py_code, '<c3-generics>', 'exec'), ns)
    return ns


# =============================================================================
# 1. 泛型类：构造/方法形参注解发射 + exec 真跑
# =============================================================================

def test_generic_class_method_param_annotation_emitted():
    src = '''\
类 栈[T]：
  属性 项。
  构造 接收 项: T：
    己项 为 项。
  段落 压入 接收 值: T：
    返回 值。
'''
    py = _transpile(src)
    # 形态断言：注解语法在位（不是裸 'T' in py_code，而是整行签名）
    assert 'class 栈(Generic[T]):' in py
    assert 'def __init__(self, 项: T):' in py
    assert 'def 压入(self, 值: T):' in py


def test_generic_class_exec_runs_and_get_type_hints_resolves_T():
    src = '''\
类 栈[T]：
  属性 项。
  构造 接收 项: T：
    己项 为 项。
  段落 压入 接收 值: T：
    返回 值。
'''
    py = _transpile(src)
    ns = _exec_product(py)
    from typing import get_type_hints

    栈 = ns['栈']
    s = 栈(5)
    assert s.压入(9) == 9

    hints = get_type_hints(栈.压入)
    assert '值' in hints, f"形参注解没被 get_type_hints 解析出来: {hints}"
    # ~T 就是模块命名空间里那个 TypeVar
    assert hints['值'].__name__ == 'T'


# =============================================================================
# 2. 段落级泛型：返回类型注解发射（def 头上不发 [T]，这是保留决策）
# =============================================================================

def test_generic_paragraph_return_annotation_emitted():
    src = '''\
段落 首个[T] 接收 表 返回 T：
  返回 表[0]。
'''
    py = _transpile(src)
    assert 'def 首个(表) -> T:' in py


def test_generic_paragraph_exec_runs_and_get_type_hints_resolves_T():
    src = '''\
段落 首个[T] 接收 表 返回 T：
  返回 表[0]。
'''
    py = _transpile(src)
    ns = _exec_product(py)
    from typing import get_type_hints

    首个 = ns['首个']
    assert 首个([1, 2, 3]) == 1

    hints = get_type_hints(首个)
    assert 'return' in hints, f"返回注解没被 get_type_hints 解析出来: {hints}"
    assert hints['return'].__name__ == 'T'


# =============================================================================
# 3. 普通（非泛型）类型注解也要真发射——改了方法发射路径，不能只盯泛型
# =============================================================================

def test_plain_method_param_annotation_still_emitted():
    src = '''\
类 计算器：
  段落 双倍 接收 数: 整数：
    返回 数 乘 2。
'''
    py = _transpile(src)
    assert 'def 双倍(self, 数: int):' in py
    ns = _exec_product(py)
    assert ns['计算器']().双倍(21) == 42
