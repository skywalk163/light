"""回归测试：_light_import_hook 不得拦截 Python 标准库同名 .light 影子。

背景（gitea run 161 e2e 的 my_first.light 循环导入）：
钩子曾对任何 <名>.light 存在即接管 import，导致编译 .light 时
`light_parser_v3 → ... → inspect` 被拦截去编译 inspect.light，而 inspect.light
又 import 编译器 → 循环导入。修复后，非别名的 Python 标准库名 import 必须放行
给真 CPython，只有 `_light_<名>` 别名（re）仍加载纯光明实现。

本测试不依赖 meta_path 排序（本地 venv 的 DistutilsMetaFinder 可能让钩子排不到
标准库前），因此直接断言 find_spec 行为，并额外做一次「钩子置顶 + 驱逐 sys.modules」
的 CI 条件模拟，确认 import inspect 不再循环。
"""
import importlib
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STDLIB_DIR = os.path.join(REPO_ROOT, 'stdlib')


@pytest.fixture
def hook():
    sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))
    sys.path.insert(0, STDLIB_DIR)
    from _light_import_hook import install, uninstall
    finder = install([STDLIB_DIR])
    yield finder
    uninstall()


def test_find_spec_does_not_intercept_stdlib_pure_shadow(hook):
    """inspect/sys 这类无 .py 兄弟的纯影子，find_spec 必须返回 None（放行 CPython）。"""
    assert hook.find_spec('inspect') is None
    assert hook.find_spec('sys') is None
    assert hook.find_spec('time') is None


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
        assert 'Lib' in re.__file__ and 're' in re.__file__, \
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
