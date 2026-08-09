# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - pytest 配置
"""

import sys
import io
import os
import pytest

# 添加项目根目录和 src 目录到路径
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
_tools_dir = os.path.join(_project_root, 'tools')
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _tools_dir)


@pytest.fixture(autouse=True)
def _preserve_stdout():
    """在所有测试前后保存/恢复 sys.stdout/sys.stderr
    防止 exec() 执行测试代码时关闭 stdout 导致 pytest crash
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    yield
    # 如果 stdout/stderr 被关闭，恢复
    if sys.stdout is None or (hasattr(sys.stdout, 'closed') and sys.stdout.closed):
        sys.stdout = old_stdout
    if sys.stderr is None or (hasattr(sys.stderr, 'closed') and sys.stderr.closed):
        sys.stderr = old_stderr


@pytest.fixture
def parser():
    """提供解析器实例"""
    from light_parser_v3 import LightParser
    return LightParser()


@pytest.fixture
def analyzer():
    """提供语义分析器实例"""
    from semantic_analyzer import SemanticAnalyzer
    return SemanticAnalyzer()


@pytest.fixture
def generator():
    """提供代码生成器实例"""
    from code_generator import PythonCodeGenerator
    return PythonCodeGenerator()