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


def _is_pure_light(light_file: str) -> bool:
    """判断一个 .light 文件是否显式声明为「纯光明实现」。

    约定：文件首行（注释行）包含魔数「纯光明实现」即视为纯光明模块，
    钩子将优先加载它并无视同名 .py 的存在。该机制用于「自举率」：
    让真正由光明写成的实现不再被同名 .py 兜底遮蔽。
    """
    try:
        with open(light_file, 'r', encoding='utf-8') as fh:
            head = fh.readline() + fh.readline()
            return '纯光明实现' in head
    except Exception:
        return False


def _exists_exact(base: str, name: str) -> bool:
    """判断 base 目录下是否存在**名字大小写完全相同**的文件。

    不能只用 `os.path.isfile`：Windows / macOS 的文件系统大小写不敏感，
    `stdlib/json.light` 会命中 `stdlib/JSON.light`。一旦 JSON.light 声明了
    「纯光明实现」，钩子就会把 Python 标准库的 `import json` 也劫持成光明门面，
    于是任何第三方库里的 `from json import loads`（pandas 就有）当场 ImportError。
    模块名必须逐字符相等，钩子才许应答。
    """
    if not os.path.isfile(os.path.join(base, name)):
        return False
    try:
        return name in os.listdir(base)
    except OSError:
        return False


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
                if not _exists_exact(base, fullname + '.light'):
                    continue
                # 同名 .py 存在 => 除非 .light 显式声明「纯光明实现」，否则源文件只是
                # 清单，让标准机制加载 .py（优先原则保持不变，只是开了纯光明出口）。
                if _exists_exact(base, fullname + '.py'):
                    if not _is_pure_light(light_file):
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
    # 必须插到标准 PathFinder 之前，才能在存在同名 .py 时也接管纯光明模块：
    # 标准机制看到 .py 就直接加载，挂在队尾的查找器根本不会被轮到。
    # 我们的 find_spec 对「无 .light 文件」或「非纯光明且同名 .py 存在」返回 None，
    # 因此会安全地让位给标准机制，不影响普通模块。
    sys.meta_path.insert(1, finder)
    return finder


def uninstall() -> None:
    """卸载钩子（主要给测试用）。"""
    finder = _current_finder()
    if finder is not None:
        sys.meta_path.remove(finder)
