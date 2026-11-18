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
# [R93-C-PATH-ORDER] 顺序调整：stdlib 必须先于 contrib 入 sys.path。
# 原写法把 contrib 插在最前（_contrib_dir 最后 insert → 成为 sys.path[0]），于是裸
# `import 进程`（以及 线程/网络请求/配置/随机/数据验证/HTTP服务端 等 stdlib 与 contrib
# 同名模块）一律命中 contrib 实现，而非 stdlib 实现。两套同名模块是**两套不同的真
# 实现**（contrib/进程.py 有 进程队列/进程锁 但**没有** 当前进程PID/进程启动），
# 于是 test_stdlib_comprehensive.py::TestStdlib进程::test_import / test_process_pid
# 在「人为切子集、无其他文件先预热 stdlib 进程模块进 sys.modules」时必红（R91-C 挂的
# 那个尾巴的真根因）。本调整让裸 import 落回 stdlib；`from contrib.X import ...` 走
# 显式包路径，不受影响。标记：R93-C-PATH-ORDER
sys.path.insert(0, _contrib_dir)
sys.path.insert(0, _stdlib_dir)
#
# ── R152-C1：会话级安装纯光明导入钩子（基础设施先行项）──────────────────
# 背景：phase13 的 `测试集合工具模块`（以及字符串常量/参数解析/高级文件等一批）
# 直跑全报 ModuleNotFoundError —— 那批模块只有 `.light`（无同名 `.py`），只能由
# `stdlib/_light_import_hook.py` 编译加载。钩子原先只由「跑过光明产物」的测试
# 顺带 install()，且 `stdlib/__init__.py` 的 install 只在 `import stdlib` 时才触发；
# 顶层测试直跑时没有任何一方装钩子 ⇒ 纯光明模块等于不存在（R152 §2.1 实踩 8/8 红）。
# 这里在 conftest 加载期统一装一次，命中 pytest 缓存后本进程内后续测试直接可用。
#
# 安全边界（_light_import_hook 设计要点 1/3，实测复核）：
#   · `.py` 优先：同名 `.py` 存在且 `.light` 无「纯光明实现」魔数 ⇒ 让路标准机制；
#   · 标准库保护：os/sys/time/re/inspect 等 Python 标准库名即使有 `.light` 影子也
#     不接管（这些名字在 stdlib 下没有同名 `.py`，且 `_STDLIB_MODULES` 保护）；
#   · 失败即让路：钩子编译异常一律返回 None，不会拖垮正常 import。
# 实际会切换行为的只有 3 个模块（.light 带魔数 + 同名 .py）：JSON / 数学 / 文件系统，
# 它们按设计应由纯光明腿遮蔽 `.py`；本文件不改变该约定。
# 幂等：钩子 install() 自带去重，与各测试文件自装的重复调用安全。
try:
    import _light_import_hook
    _light_import_hook.install([_stdlib_dir, _contrib_dir, _project_root])
except Exception as _e:
    import warnings
    warnings.warn('R152-C1 conftest 安装光明导入钩子失败（%r），'
                  '纯光明模块相关测试可能 ModuleNotFoundError。' % (_e,))

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



# ── T-0390：slow 用例的超时提限接线 ──────────────────────────────────────────
# 背景：pyproject 的 addopts 写死 `--timeout=60`（每用例上限）。一批用例在 0.88
# 全量 `-n 6` 下实测 52–61s，60s 正好压在它们头上；机器被别的 agent 挤到 load≈15
# 时就在 59–61s 之间随机翻红，同一份提交三轮全量的失败集合互不相同。
#
# 这里给**标记了 slow 的用例**补一条 `timeout` marker。pytest-timeout 的取值顺序是
# 「item 上的 timeout marker > 命令行 --timeout」（见 pytest_timeout.py
# `_get_item_settings`：marker 先赋值，`if timeout is None` 才回落到 ini 值），
# 所以只有 slow 用例被提限，**全局 --timeout=60 原样保留**——真卡死的快用例
# 仍旧 60s 被掐，不会把整轮拖到 remote_ci 的 --timeout=5400s。
#
# 秒数用环境变量 `LIGHT_SLOW_TIMEOUT` 覆盖，默认 600：踩线耗时随机器/负载变，
# 机器更慢时在命令行前加 `LIGHT_SLOW_TIMEOUT=1200` 即可，不动代码。
# 为什么不用 ini（`slow_timeout = …`）：仓库根的 conftest.py 不在本卡可改路径里，
# 自定义 ini 选项只能在 rootdir 的 conftest 用 `pytest_addoption` 注册；放
# tests/conftest.py 里注册已经晚了，pytest 会先报 "Unknown config option"。
#
# 不指定 timeout 方法：让它沿用 pytest-timeout 的默认（POSIX 走 signal、Windows
# 走 thread）。显式写 `method="signal"` 在 Windows 上直接不可用。
_SLOW_TIMEOUT = float(os.environ.get("LIGHT_SLOW_TIMEOUT", "600"))


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("slow") is None:
            continue
        if item.get_closest_marker("timeout") is not None:
            continue  # 用例自己指定了更精确的提限，让路
        item.add_marker(pytest.mark.timeout(_SLOW_TIMEOUT))


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
    """提供语义分析器工厂。

    R135-A 前：`SemanticAnalyzer.__init__` 需要 `ast_unified.Module`，而
    `light_parser_v3` 产出 `ast_nodes_v3.Module`，两者不兼容（`test_semantic.py`
    整体 skip），因此本 fixture 只能返回 None。

    R135-A 后：`src/semantic_analyzer.py` 已内置 v3 适配层（自带符号表 +
    `_v3_visit_*` 分派），任何 v3 Module 都能直接分析。这里返回一个
    `analyze(源码) -> (module, analyzer)` 工厂，方便用例断言错误列表。
    """
    from semantic_analyzer import SemanticAnalyzer

    def _analyze(source: str):
        module = parser.parse(source)
        analyzer = SemanticAnalyzer(module)
        if getattr(analyzer, 'v3_mode', False):
            analyzer.analyze_v3(module)
        else:
            analyzer.visit_Module(module)
        return module, analyzer

    return _analyze


@pytest.fixture
def generator():
    """提供代码生成器实例"""
    from code_generator import PythonCodeGenerator
    return PythonCodeGenerator()