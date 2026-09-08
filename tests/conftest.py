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

# ── 2026-09-08 CI 时间治理（task-CIperf）──────────────────────────────────────
# 预热最重的共享模块：全仓 7986 条用例的 test 文件几乎都 `from light_parser_v3
# import ...` / `from code_generator import ...`。这里在 conftest 加载期先把它们
# 构造一次，让后续测试文件的同名 import 直接命中 sys.modules 缓存。
# 注意：Python 的 import 本就按 sys.modules 去重，所以这一预热对「总 import 次数」
# 没有减少（首个测试文件触发后同样只构造一次）；实测对 collect 时间只有约 10% 的
# 边际收益（64s→57s），真正的 37min→15min 由 xdist 并行 + PR 跳过 slow 命中。
# 用 try/except 兜底：解析器若在某环境 import 失败，绝不能连累整轮收集（否则一个
# 解析器 bug 会把全仓测试全打成 collection error，掩盖真正的回归点）；失败时仅告警，
# 由真正依赖它的测试各自报错。
try:
    import light_parser_v3  # noqa: E402,F401
    import code_generator   # noqa: E402,F401
except Exception as _e:  # pylint: disable=broad-except
    import warnings
    warnings.warn("conftest 预热 light_parser_v3/code_generator 失败（%r），"
                  "回退为各测试文件自行 import。" % (_e,))



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
def analyzer(parser):
    """提供语义分析器实例。

    SemanticAnalyzer.__init__ 需要 module 参数（ast_unified.Module），
    但 light_parser_v3 产出 ast_nodes_v3.Module，两者不兼容
    （test_semantic.py 整体 skip）。这里返回 None 表示不可用，
    避免无参构造 TypeError；消费方应自行判断是否可用。
    """
    return None


@pytest.fixture
def generator():
    """提供代码生成器实例"""
    from code_generator import PythonCodeGenerator
    return PythonCodeGenerator()