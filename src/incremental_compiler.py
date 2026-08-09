"""光明增量编译器

只重新编译修改过的模块，加速大型项目编译。
支持文件监听模式，自动检测并重新编译变化文件。
"""

import os
import sys
import time
import hashlib
from typing import List, Dict, Optional, Any, Callable, Set
from pathlib import Path

try:
    from compiler_cache import CompilationCache
except ImportError:
    from src.compiler_cache import CompilationCache

# 导入 LLVM 编译相关函数
try:
    from llvm.compiler import (
        compile_source_typed,
        compile_modules_typed,
        compile_light_typed,
        find_clang,
    )
except ImportError:
    from src.llvm.compiler import (
        compile_source_typed,
        compile_modules_typed,
        compile_light_typed,
        find_clang,
    )


class DependencyGraph:
    """依赖图跟踪器

    跟踪文件之间的导入依赖关系，支持：
    - 模块导入关系记录
    - 依赖变更的级联失效
    - 依赖图拓扑排序
    - 循环依赖检测
    """

    def __init__(self):
        # 依赖图：模块名 -> 依赖的模块名列表
        self._graph: Dict[str, List[str]] = {}
        # 反向依赖图：模块名 -> 依赖它的模块名列表
        self._reverse_graph: Dict[str, List[str]] = {}
        # 模块名 -> 文件路径映射
        self._module_to_path: Dict[str, str] = {}
        # 文件路径 -> 模块名映射
        self._path_to_module: Dict[str, str] = {}

    def add_module(self, module_name: str, file_path: str, dependencies: List[str] = None):
        """添加模块及其依赖关系

        Args:
            module_name: 模块名
            file_path: 文件路径
            dependencies: 依赖的模块名列表
        """
        self._module_to_path[module_name] = file_path
        self._path_to_module[file_path] = module_name
        self._graph[module_name] = dependencies or []

        # 更新反向依赖
        for dep in (dependencies or []):
            if dep not in self._reverse_graph:
                self._reverse_graph[dep] = []
            if module_name not in self._reverse_graph[dep]:
                self._reverse_graph[dep].append(module_name)

    def get_dependencies(self, module_name: str) -> List[str]:
        """获取模块的直接依赖

        Args:
            module_name: 模块名

        Returns:
            依赖的模块名列表
        """
        return self._graph.get(module_name, [])

    def get_dependents(self, module_name: str) -> List[str]:
        """获取依赖该模块的所有模块（反向依赖）

        Args:
            module_name: 模块名

        Returns:
            依赖该模块的模块名列表
        """
        return self._reverse_graph.get(module_name, [])

    def get_cascade_affected(self, module_name: str) -> Set[str]:
        """获取模块变更时受影响的所有模块（级联影响）

        Args:
            module_name: 变更的模块名

        Returns:
            所有受影响的模块名集合
        """
        affected = set()
        to_visit = [module_name]
        visited = set()

        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            affected.add(current)
            # 所有依赖 current 的模块也受影响
            for dependent in self.get_dependents(current):
                if dependent not in visited:
                    to_visit.append(dependent)

        return affected

    def get_module_path(self, module_name: str) -> Optional[str]:
        """获取模块对应的文件路径

        Args:
            module_name: 模块名

        Returns:
            文件路径，未找到返回 None
        """
        return self._module_to_path.get(module_name)

    def get_module_name(self, file_path: str) -> Optional[str]:
        """获取文件路径对应的模块名

        Args:
            file_path: 文件路径

        Returns:
            模块名，未找到返回 None
        """
        return self._path_to_module.get(file_path)

    def has_cycle(self) -> bool:
        """检测依赖图中是否存在循环依赖

        Returns:
            True 表示存在循环依赖
        """
        # 使用 DFS 检测环
        visited = set()
        recursion_stack = set()

        def dfs(node):
            visited.add(node)
            recursion_stack.add(node)
            for dep in self._graph.get(node, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in recursion_stack:
                    return True
            recursion_stack.remove(node)
            return False

        for module in self._graph:
            if module not in visited:
                if dfs(module):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        """拓扑排序

        Returns:
            按依赖顺序排列的模块名列表（依赖者在前）
        """
        visited = set()
        result = []

        def dfs(node):
            visited.add(node)
            for dep in self._graph.get(node, []):
                if dep not in visited:
                    dfs(dep)
            result.append(node)

        for module in self._graph:
            if module not in visited:
                dfs(module)

        # 反转：被依赖者在前
        return list(reversed(result))

    def get_all_modules(self) -> List[str]:
        """获取所有模块名

        Returns:
            模块名列表
        """
        return list(self._graph.keys())

    def clear(self):
        """清空依赖图"""
        self._graph.clear()
        self._reverse_graph.clear()
        self._module_to_path.clear()
        self._path_to_module.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取依赖图统计信息

        Returns:
            统计信息字典
        """
        return {
            'total_modules': len(self._graph),
            'total_dependencies': sum(len(deps) for deps in self._graph.values()),
            'has_cycle': self.has_cycle(),
        }


class IncrementalCompiler:
    """增量编译器

    只重新编译修改过的模块，加速大型项目编译。
    跟踪文件依赖关系，支持增量编译和全量编译。

    Attributes:
        cache: 编译缓存实例
        dep_graph: 依赖图跟踪器
        _dirty_files: 脏文件集合
        _compiled_modules: 已编译的模块记录
        _file_dependencies: 文件依赖关系
    """

    def __init__(self, cache: CompilationCache = None):
        """初始化增量编译器

        Args:
            cache: 编译缓存实例，默认创建新的
        """
        self.cache = cache or CompilationCache()
        self.dep_graph = DependencyGraph()
        self._dirty_files: set = set()
        self._compiled_modules: Dict[str, Dict[str, Any]] = {}
        self._file_dependencies: Dict[str, List[str]] = {}
        self._module_resolver = None

    def _get_module_resolver(self, search_paths: List[str] = None):
        """获取模块解析器

        Args:
            search_paths: 搜索路径列表
        """
        if self._module_resolver is None:
            try:
                from module_resolver import ModuleResolver
            except ImportError:
                from src.module_resolver import ModuleResolver
            self._module_resolver = ModuleResolver(search_paths=search_paths or [os.getcwd()])
        return self._module_resolver

    def _parse_imports(self, source: str) -> List[str]:
        """解析源码中的导入语句

        Args:
            source: 源码字符串

        Returns:
            导入的模块名列表
        """
        imports = []
        for line in source.split('\n'):
            stripped = line.strip()
            # 支持 "导入" 和 "import" 两种语法
            if stripped.startswith('导入 ') or stripped.startswith('import '):
                parts = stripped.split()
                if len(parts) >= 2:
                    module_name = parts[1].strip('"\'')
                    imports.append(module_name)
            # 支持 "从 X 导入 Y" 语法
            elif stripped.startswith('从 ') or stripped.startswith('from '):
                parts = stripped.split()
                if len(parts) >= 2:
                    module_name = parts[1].strip('"\'')
                    imports.append(module_name)
        return imports

    def compile(self, file_path: str, force: bool = False, verbose: bool = False,
                target_platform: str = None, debug: bool = False,
                opt_level: str = 'O2') -> Dict[str, Any]:
        """增量编译单个文件（只编译修改过的文件）

        Args:
            file_path: 源文件路径
            force: 是否强制重新编译（忽略缓存）
            verbose: 是否输出详细信息
            target_platform: 目标平台
            debug: 是否生成调试信息
            opt_level: 优化级别

        Returns:
            编译结果字典
        """
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                'success': False,
                'error': f'文件不存在: {abs_path}',
                'file_path': abs_path,
                'cached': False,
            }

        # 检查缓存
        if not force and self.cache.is_fresh(abs_path):
            cached_result = self.cache.get_cached(abs_path)
            if cached_result is not None:
                if verbose:
                    print(f"[增量编译] 命中缓存: {abs_path}")
                return {
                    'success': True,
                    'ir': cached_result,
                    'file_path': abs_path,
                    'cached': True,
                    'force_compiled': False,
                }

        if verbose:
            print(f"[增量编译] 编译: {abs_path}")

        # 读取源文件
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except IOError as e:
            return {
                'success': False,
                'error': f'读取文件失败: {e}',
                'file_path': abs_path,
                'cached': False,
            }

        # 编译
        try:
            ir = compile_source_typed(
                source,
                verbose=verbose,
                target_platform=target_platform,
                debug=debug,
                opt_level=opt_level,
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'编译失败: {e}',
                'file_path': abs_path,
                'cached': False,
            }

        # 写入缓存
        self.cache.set_cached(abs_path, ir)

        # 记录编译信息
        self._compiled_modules[abs_path] = {
            'ir': ir,
            'compiled_at': time.time(),
            'opt_level': opt_level,
        }

        # 从脏文件集合中移除
        self._dirty_files.discard(abs_path)

        return {
            'success': True,
            'ir': ir,
            'file_path': abs_path,
            'cached': False,
            'force_compiled': force,
        }

    def compile_project(self, project_root: str, verbose: bool = False,
                        target_platform: str = None, debug: bool = False,
                        opt_level: str = 'O2') -> Dict[str, Any]:
        """增量编译整个项目

        支持依赖图跟踪，当模块 A 依赖模块 B 时，如果 B 发生变化，
        A 也会被自动重新编译。

        Args:
            project_root: 项目根目录路径
            verbose: 是否输出详细信息
            target_platform: 目标平台
            debug: 是否生成调试信息
            opt_level: 优化级别

        Returns:
            编译结果字典
        """
        project_root = os.path.abspath(project_root)

        if not os.path.isdir(project_root):
            return {
                'success': False,
                'error': f'项目目录不存在: {project_root}',
                'files_compiled': 0,
                'files_cached': 0,
                'files_failed': 0,
            }

        # 获取所有 .light 文件
        light_files = self._find_light_files(project_root)

        if verbose:
            print(f"[增量编译] 项目: {project_root}, 找到 {len(light_files)} 个 .light 文件")

        # 构建依赖图
        self._build_dependency_graph(light_files, verbose)

        # 获取脏模块列表（基于文件修改时间）
        dirty_modules = self.get_dirty_modules(project_root)

        # 如果存在依赖图，级联失效：依赖的模块变更时，依赖者也需要重新编译
        if self.dep_graph.get_all_modules():
            cascade_affected = set()
            for dirty_path in dirty_modules:
                mod_name = self.dep_graph.get_module_name(dirty_path)
                if mod_name:
                    affected = self.dep_graph.get_cascade_affected(mod_name)
                    cascade_affected.update(affected)
                    if verbose:
                        print(f"  [依赖图] {mod_name} 变更，影响 {len(affected)} 个模块")

            # 将级联受影响的模块也加入脏列表
            for mod_name in cascade_affected:
                mod_path = self.dep_graph.get_module_path(mod_name)
                if mod_path and mod_path not in dirty_modules:
                    dirty_modules.append(mod_path)

        if verbose:
            print(f"[增量编译] 脏模块: {len(dirty_modules)} 个")

        # 编译结果统计
        files_compiled = 0
        files_cached = 0
        files_failed = 0
        errors = []

        # 编译所有文件（脏文件重新编译，干净文件使用缓存）
        for file_path in light_files:
            force = file_path in dirty_modules
            result = self.compile(
                file_path,
                force=force,
                verbose=verbose,
                target_platform=target_platform,
                debug=debug,
                opt_level=opt_level,
            )

            if result.get('success'):
                if result.get('cached', False):
                    files_cached += 1
                else:
                    files_compiled += 1
            else:
                files_failed += 1
                errors.append(result.get('error', '未知错误'))

        return {
            'success': files_failed == 0,
            'project_root': project_root,
            'total_files': len(light_files),
            'files_compiled': files_compiled,
            'files_cached': files_cached,
            'files_failed': files_failed,
            'errors': errors,
            'dirty_modules': dirty_modules,
            'dep_graph_stats': self.dep_graph.get_stats() if self.dep_graph else {},
        }

    def _build_dependency_graph(self, light_files: List[str], verbose: bool = False):
        """构建项目依赖图

        解析每个文件的导入语句，建立模块间依赖关系。

        Args:
            light_files: .light 文件路径列表
            verbose: 是否输出详细信息
        """
        self.dep_graph.clear()

        # 第一遍：注册所有模块
        for file_path in light_files:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            self.dep_graph.add_module(module_name, file_path, [])

        # 第二遍：解析导入关系
        for file_path in light_files:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                imports = self._parse_imports(source)
                self.dep_graph.add_module(module_name, file_path, imports)
                if verbose and imports:
                    print(f"  [依赖图] {module_name} -> {', '.join(imports)}")
            except IOError:
                pass

        # 检测循环依赖
        if self.dep_graph.has_cycle():
            print("[警告] 检测到循环依赖！")

    def get_dirty_modules(self, project_root: str) -> List[str]:
        """获取需要重新编译的模块

        比较文件修改时间和缓存时间，找出已修改的文件。

        Args:
            project_root: 项目根目录路径

        Returns:
            需要重新编译的文件路径列表
        """
        project_root = os.path.abspath(project_root)
        light_files = self._find_light_files(project_root)
        dirty = []

        for file_path in light_files:
            if not self.cache.is_fresh(file_path):
                dirty.append(file_path)

        return dirty

    def mark_dirty(self, file_path: str):
        """标记文件为脏（需要重新编译）

        Args:
            file_path: 源文件路径
        """
        abs_path = os.path.abspath(file_path)
        self._dirty_files.add(abs_path)
        self.cache.invalidate(abs_path)

    def watch(self, project_root: str, callback: Callable = None,
              interval: float = 1.0, verbose: bool = False):
        """文件监听模式（自动重新编译变化文件）

        定期检查文件变化，自动重新编译修改过的文件。

        Args:
            project_root: 项目根目录路径
            callback: 编译完成后的回调函数（接收编译结果字典）
            interval: 检查间隔（秒），默认 1 秒
            verbose: 是否输出详细信息
        """
        project_root = os.path.abspath(project_root)
        if not os.path.isdir(project_root):
            print(f"[监听] 项目目录不存在: {project_root}")
            return

        print(f"[监听] 开始监控: {project_root} (间隔: {interval}s)")
        print("[监听] 按 Ctrl+C 停止")

        # 记录文件的当前状态
        file_states: Dict[str, float] = {}
        for file_path in self._find_light_files(project_root):
            try:
                file_states[file_path] = os.path.getmtime(file_path)
            except OSError:
                pass

        try:
            while True:
                time.sleep(interval)
                changed_files = []

                # 检查文件变化
                for file_path in list(file_states.keys()):
                    try:
                        current_mtime = os.path.getmtime(file_path)
                        if current_mtime != file_states[file_path]:
                            changed_files.append(file_path)
                            file_states[file_path] = current_mtime
                    except OSError:
                        # 文件被删除
                        changed_files.append(file_path)
                        del file_states[file_path]

                # 检查新文件
                for file_path in self._find_light_files(project_root):
                    if file_path not in file_states:
                        try:
                            file_states[file_path] = os.path.getmtime(file_path)
                            changed_files.append(file_path)
                        except OSError:
                            pass

                # 如果存在依赖图，级联影响
                if self.dep_graph.get_all_modules():
                    cascade_set = set(changed_files)
                    for changed_path in changed_files:
                        mod_name = self.dep_graph.get_module_name(changed_path)
                        if mod_name:
                            affected = self.dep_graph.get_cascade_affected(mod_name)
                            for aff_mod in affected:
                                aff_path = self.dep_graph.get_module_path(aff_mod)
                                if aff_path and aff_path not in cascade_set:
                                    cascade_set.add(aff_path)

                    changed_files = list(cascade_set)

                # 重新编译变化的文件
                for file_path in changed_files:
                    if verbose:
                        print(f"[监听] 检测到变化: {file_path}")

                    result = self.compile(
                        file_path,
                        force=True,
                        verbose=verbose,
                    )

                    if result.get('success'):
                        print(f"[监听] 重新编译成功: {file_path}")
                    else:
                        print(f"[监听] 编译失败: {file_path}: {result.get('error', '')}")

                    if callback:
                        callback(result)

        except KeyboardInterrupt:
            print("\n[监听] 已停止")

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _find_light_files(root_dir: str) -> List[str]:
        """递归查找所有 .light 文件

        Args:
            root_dir: 根目录路径

        Returns:
            .light 文件路径列表
        """
        light_files = []
        root = Path(root_dir)
        if not root.exists():
            return light_files

        for file_path in root.rglob('*.light'):
            if file_path.is_file():
                light_files.append(str(file_path))

        return sorted(light_files)

    def get_compile_stats(self) -> Dict[str, Any]:
        """获取编译统计信息

        Returns:
            编译统计信息字典
        """
        return {
            'compiled_modules': len(self._compiled_modules),
            'dirty_files': len(self._dirty_files),
            'file_dependencies': len(self._file_dependencies),
            'dep_graph_stats': self.dep_graph.get_stats(),
            'cache_stats': self.cache.stats() if self.cache else {},
        }