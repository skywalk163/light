"""让 Python 的 import 机制能直接加载纯光明（.light）模块。

背景
----
光明标准库的绝大多数模块是「.light 清单 + 同名 .py 实现」的组合：
`.light` 只声明导出名，真正的实现在 `.py` 里。这类模块靠 CPython
自带的导入机制就能工作。

但光明也允许**纯光明模块**——只有 `.light`、没有 `.py`（例如
`stdlib/列表工具.light`）。代码生成器为 `从《列表工具》导入《求和》`
生成的是普通的 `from 列表工具 import 求和`，而 CPython 只认
`.py/.pyc`，于是运行期直接报 `ModuleNotFoundError`——模块等于不存在。

这个钩子补上这一环：在 `sys.meta_path` 上挂一个查找器，遇到找不到的
模块名时去搜索路径里找 `<名字>.light`，就地编译成 Python 再执行。

设计要点
--------
1. **`.py` 优先**：若同名 `.py` 存在，直接放行给标准机制。
   `.light` 在那种情况下只是清单，不是实现。
2. **只处理顶层模块名**：带点的子模块交给标准机制。
3. **失败即让路**：任何异常都返回 None，绝不让钩子本身拖垮 import。
4. **幂等**：重复 install 不会叠加多个查找器。

用法
----
    import _light_import_hook
    _light_import_hook.install([stdlib_dir, script_dir])
"""
from __future__ import annotations

import importlib.abc
import importlib.util
import os
import sys

__all__ = ['install', 'uninstall', 'LightFinder', 'LightLoader']

# 编译结果缓存：绝对路径 -> 生成的 Python 源码
_CODE_CACHE: dict[str, str] = {}

# 正在编译中的路径，防止循环导入导致无限递归
_COMPILING: set[str] = set()


def _ensure_compiler_importable(stdlib_dir: str) -> None:
    """确保光明编译器（src/）在 sys.path 上。

    在 `light run` 场景下 cli 已经加过了；独立运行生成的 .py 时没有，
    这里按 stdlib 的同级目录去找。
    """
    try:
        from light_parser_v3 import LightParser  # noqa: F401
        return
    except ImportError:
        pass

    project_dir = os.path.dirname(os.path.abspath(stdlib_dir))
    for sub in ('src', 'antlrparser'):
        cand = os.path.join(project_dir, sub)
        if os.path.isdir(cand) and cand not in sys.path:
            sys.path.insert(0, cand)


def _compile_light(light_path: str, stdlib_dir: str) -> str:
    """把 .light 文件编译成 Python 源码（带缓存）。"""
    key = os.path.abspath(light_path)
    cached = _CODE_CACHE.get(key)
    if cached is not None:
        return cached

    _ensure_compiler_importable(stdlib_dir)
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    with open(light_path, 'r', encoding='utf-8') as fh:
        source = fh.read()

    module_ast = LightParser().parse(source)
    generated = PythonCodeGenerator().generate(module_ast)
    _CODE_CACHE[key] = generated
    return generated


class LightLoader(importlib.abc.Loader):
    """把 .light 编译后执行到模块命名空间里。"""

    def __init__(self, fullname: str, light_path: str, stdlib_dir: str):
        self.fullname = fullname
        self.light_path = light_path
        self.stdlib_dir = stdlib_dir

    def create_module(self, spec):  # noqa: D102 - 用默认模块对象
        return None

    def exec_module(self, module) -> None:  # noqa: D102
        key = os.path.abspath(self.light_path)
        if key in _COMPILING:
            raise ImportError(
                f'光明模块循环导入: {self.fullname} ({self.light_path})'
            )
        _COMPILING.add(key)
        try:
            code = _compile_light(self.light_path, self.stdlib_dir)
            module.__file__ = self.light_path
            module.__light_source__ = self.light_path
            exec(compile(code, self.light_path, 'exec'), module.__dict__)
        finally:
            _COMPILING.discard(key)


class LightFinder(importlib.abc.MetaPathFinder):
    """在给定目录里查找 <模块名>.light。"""

    def __init__(self, search_paths):
        self.search_paths: list[str] = []
        self.extend(search_paths)

    def extend(self, search_paths) -> None:
        for p in search_paths or ():
            if not p:
                continue
            ap = os.path.abspath(p)
            if os.path.isdir(ap) and ap not in self.search_paths:
                self.search_paths.append(ap)

    @property
    def _stdlib_dir(self) -> str:
        return self.search_paths[0] if self.search_paths else os.getcwd()

    def find_spec(self, fullname, path=None, target=None):  # noqa: D102
        # 子模块（带点）交给标准机制
        if '.' in fullname:
            return None
        try:
            for base in self.search_paths:
                light_file = os.path.join(base, fullname + '.light')
                if not os.path.isfile(light_file):
                    continue
                # 同名 .py 存在 => 源文件只是清单，让标准机制加载 .py
                if os.path.isfile(os.path.join(base, fullname + '.py')):
                    return None
                loader = LightLoader(fullname, light_file, self._stdlib_dir)
                return importlib.util.spec_from_loader(fullname, loader)
        except Exception:
            # 钩子出问题绝不能影响正常 import
            return None
        return None


def _current_finder():
    for f in sys.meta_path:
        if isinstance(f, LightFinder):
            return f
    return None


def install(search_paths) -> LightFinder:
    """安装（或扩充）光明导入钩子。重复调用是安全的。"""
    finder = _current_finder()
    if finder is not None:
        finder.extend(search_paths)
        return finder
    finder = LightFinder(search_paths)
    # 放在末尾：优先让标准机制处理 .py，找不到时才轮到我们
    sys.meta_path.append(finder)
    return finder


def uninstall() -> None:
    """卸载钩子（主要给测试用）。"""
    finder = _current_finder()
    if finder is not None:
        sys.meta_path.remove(finder)
