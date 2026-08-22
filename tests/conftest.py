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
# stdlib/ 与 contrib/ 也要在路径上：tests/test_stdlib_phase9~13.py 直接
# `import 测试框架` 这类裸模块名，那批模块实际住在 stdlib/ 和 contrib/ 下。
# 它们原先各自 sys.path.insert 了 'c:/traework/light/stdlib' /
# 'c:/dumatework/light/stdlib' 这类别的机器上的绝对路径，换机器就整文件 ImportError；
# 路径统一收到这里按 __file__ 推导，测试文件里不再出现绝对路径。
_stdlib_dir = os.path.join(_project_root, 'stdlib')
_contrib_dir = os.path.join(_project_root, 'contrib')
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _tools_dir)
sys.path.insert(0, _stdlib_dir)
sys.path.insert(0, _contrib_dir)



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