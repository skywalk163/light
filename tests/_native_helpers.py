# -*- coding: utf-8 -*-
"""原生腿测试公共辅助。

TODO(移交:A7): 本文件是 B7 创建的占位桩。A7 合入后会用正式版替换。
正式版应提供 require_clang() / require_native_backend() 等辅助函数，
统一处理 clang 缺失时的 skip 逻辑。

B7 临时实现：包装 find_clang()，缺 clang 时 pytest.skip 而非 RuntimeError。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llvm.compiler import find_clang  # noqa: E402


def require_clang():
    """返回 clang 路径；缺 clang 时调 pytest.skip 而非 raise RuntimeError。

    TODO(移交:A7): A7 正式版可能增加更多检测（版本号、目标三元组等）。
    """
    try:
        return find_clang()
    except RuntimeError as exc:
        pytest.skip(f'clang 不可用: {exc}')


def have_clang() -> bool:
    """返回 clang 是否可用（不 skip）。"""
    try:
        find_clang()
        return True
    except RuntimeError:
        return False
