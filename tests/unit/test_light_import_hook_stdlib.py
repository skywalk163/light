"""回归测试：_light_import_hook 不得拦截 Python 标准库同名 .light 影子。

背景（gitea run 161 e2e 的 my_first.light 循环导入）：
钩子曾对任何 <名>.light 存在即接管 import，导致编译 .light 时
`light_parser_v3 → ... → inspect` 被拦截去编译 inspect.light，而 inspect.light
又 import 编译器 → 循环导入。修复后，非别名的 Python 标准库名 import 必须放行
给真 CPython，只有 `_light_<名>` 别名（re）仍加载纯光明实现。

本测试不依赖 meta_path 排序（本地 venv 的 DistutilsMetaFinder 可能让钩子排不到
标准库前），因此直接断言 find_spec 行为，并额外做一次「钩子置顶 + 驱逐 sys.modules」
的 CI 条件模拟，确认 import inspect 不再循环。

R165-T2 两层加固（治 R164 全量门唯一 new_red「全量门内红、单文件隔离绿」）：
1. 用例侧：`hook` fixture 不再复用 conftest 的全局 finder，先 `uninstall()` 再装
   只含 stdlib 的全新 finder，判据与会话历史解耦；
2. 产品侧：`find_spec` 的「标准库保护」从全局 `any(search_dirs)` 下沉为**逐 base**
   判定，另有 `test_find_spec_stdlib_shadow_immune_to_polluted_search_paths` 直接
   把「含 inspect.py 的目录」塞进 search_paths 复现污染场景（回退产品修复即转红）。
"""
import importlib
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STDLIB_DIR = os.path.join(REPO_ROOT, 'stdlib')


@pytest.fixture
def hook():
    """给本文件一个**干净**的 finder（search_paths 只有 stdlib），跑完还原全局 finder。

    R165-T2 治 R164 全量门唯一 new_red：旧 fixture 直接复用 conftest 的全局 finder
    （`install()` 命中 `_current_finder()` 就只 extend、不清理），于是本文件的判据
    随会话历史漂移——全量门里前序用例把「含 inspect.py 的目录」extend 进来之后，
    `find_spec('inspect')` 就从 None 变成一个 LightLoader spec，单文件隔离跑却全绿。
    现在先 `uninstall()` 再装全新 finder，判据只取决于 stdlib 目录本身，与全局
    finder 的会话历史无关（同 test_lpd_009 的做法）。
    """
    sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))
    sys.path.insert(0, STDLIB_DIR)
    import _light_import_hook as _hook

    prev = None
    prev_index = None
    for _i, _f in enumerate(sys.meta_path):
        if isinstance(_f, _hook.LightFinder):
            prev, prev_index = _f, _i
            break
    _hook.uninstall()
    finder = _hook.install([STDLIB_DIR])
    try:
        yield finder
    finally:
        _hook.uninstall()
        if prev is not None:
            # 还原**同一个实例**（连同它原有的 search_paths），不新建 finder：
            # 别的用例/全局 conftest 可能持有该实例的引用。
            sys.meta_path.insert(prev_index, prev)


def test_find_spec_does_not_intercept_stdlib_pure_shadow(hook):
    """inspect/sys 这类无 .py 兄弟的纯影子，find_spec 必须返回 None（放行 CPython）。"""
    assert hook.find_spec('inspect') is None
    assert hook.find_spec('sys') is None
    assert hook.find_spec('time') is None


def test_find_spec_stdlib_shadow_immune_to_polluted_search_paths(hook):
    """守卫口径必须**逐 base**：别的目录有 inspect.py 不许给 stdlib/inspect.light 放行。

    R164 全量门唯一 new_red 的最小复现：把「含 inspect.py 的目录」（这里取真 CPython
    的 stdlib 目录）extend 进同一个 finder，再问 `find_spec('inspect')`。
    旧守卫是 `any(search_dirs 里有 inspect.py)` —— 全局判真 ⇒ 放行 ⇒ 加载循环走到
    stdlib 那个 base（它有 inspect.light、没有 inspect.py）就返回 LightLoader spec，
    于是 inspect.light 被编译（正是守卫要防的循环导入）。
    逐 base 判定后：承载 inspect.light 的目录没有 .py 兄弟 ⇒ 跳过，整体返回 None。
    """
    import inspect as _cpython_inspect

    cpython_stdlib = os.path.dirname(os.path.abspath(_cpython_inspect.__file__))
    assert os.path.isfile(os.path.join(cpython_stdlib, 'inspect.py')), (
        f'前置失败：{cpython_stdlib} 下没有 inspect.py，本用例失去污染源')
    # 前置：stdlib 目录里 inspect.light 必须存在且是纯影子（无同名 .py），
    # 否则本用例断言的不是「影子被误加载」这件事。
    assert os.path.isfile(os.path.join(STDLIB_DIR, 'inspect.light'))
    assert not os.path.isfile(os.path.join(STDLIB_DIR, 'inspect.py')), (
        'stdlib/ 下出现了 inspect.py，本用例的污染形态已变，需重新设计')

    hook.extend([cpython_stdlib])          # 模拟前序用例污染 search_paths
    assert cpython_stdlib in hook.search_paths, '前置失败：污染目录未进入 search_paths'

    spec = hook.find_spec('inspect')
    assert spec is None, (
        f'污染 search_paths 后 inspect 仍被钩子接管：loader={getattr(spec, "loader", None)!r}'
        '（守卫退回全局 any() 判定即复现 R164 new_red）')


def test_find_spec_preserves_re_alias(hook):
    """_light_re 别名仍返回 spec，继续加载 re.light。"""
    spec = hook.find_spec('_light_re')
    if spec is None:
        raise AssertionError("_light_re 未被钩子接管（find_spec 返回 None）")
    # 不断 `is not None`：要断「确实回落到 re.light 且 loader 是光明加载器」，
    # 否则钩子只回一个空壳 spec 也会绿。
    # 注：spec_from_loader 不会填 origin（实测为 None），有信号的是 loader 本身。
    assert type(spec.loader).__name__ == 'LightLoader', (
        f"loader 应为 LightLoader，实际={type(spec.loader).__name__}")
    assert spec.loader.light_path.endswith('re.light'), (
        f"_light_re 的 loader 应指向 re.light，实际={spec.loader.light_path}")


def test_find_spec_preserves_chinese_modules(hook):
    """中文模块（数学/列表工具）非标准库名，仍由钩子加载。"""
    assert hook.find_spec('数学') is not None
    assert hook.find_spec('列表工具') is not None


def test_import_inspect_resolves_to_cpython_under_hook(hook):
    """CI 条件模拟：钩子置顶 + 从 sys.modules 驱逐 inspect，import inspect 必须命中真 CPython。"""
    sys.meta_path.remove(hook)
    sys.meta_path.insert(0, hook)  # 模拟 CI：钩子比标准 PathFinder 更靠前
    saved = sys.modules.pop('inspect', None)
    try:
        import inspect  # noqa: F401
        assert inspect.__file__.endswith(os.path.join('Lib', 'inspect.py')) or \
            'python' in inspect.__file__.lower() and 'inspect.py' in inspect.__file__, \
            f'inspect 应解析到真 CPython 模块，实际: {inspect.__file__}'
    finally:
        sys.meta_path.remove(hook)
        sys.meta_path.insert(1, hook)
        if saved is not None:
            sys.modules['inspect'] = saved
        else:
            sys.modules.pop('inspect', None)


def test_import_re_resolves_to_cpython_but_alias_loads_light(hook):
    """import re → CPython re；import_module('_light_re') → stdlib/re.light。"""
    saved_re = sys.modules.pop('re', None)
    saved_alias = sys.modules.pop('_light_re', None)
    try:
        import re  # noqa: F401
        re_file = (re.__file__ or '').replace('\\', '/')
        # FreeBSD/Linux 上标准库路径形如 /usr/local/lib/python3.12/re/__init__.py，
        # 不含 'Lib'——只断「命中 CPython 的 re，而非光明 stdlib 的影子」。
        assert 'stdlib' not in re_file and not re_file.endswith('re.light'), \
            f'import re 应命中 CPython re，实际: {re.__file__}'
        mod = importlib.import_module('_light_re')
        assert mod.__file__.replace('\\', '/').endswith('stdlib/re.light'), \
            f'_light_re 应加载 re.light，实际: {mod.__file__}'
    finally:
        if saved_re is not None:
            sys.modules['re'] = saved_re
        else:
            sys.modules.pop('re', None)
        if saved_alias is not None:
            sys.modules['_light_re'] = saved_alias
        else:
            sys.modules.pop('_light_re', None)
