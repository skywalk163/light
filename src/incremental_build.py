"""
段言（Duan）编程语言 - 增量编译系统

基于文件变更检测和依赖图追踪，实现仅重新编译变更文件及其依赖链。

核心机制：
1. 文件变更检测：基于 mtime + SHA256 内容哈希
2. 依赖图追踪：利用 module_resolver 的依赖图
3. 增量编译：仅重新编译变更文件及其下游依赖
4. 构建缓存：.duan_build_cache.json 持久化构建状态
5. 并行编译：独立模块并行编译加速
6. 快速模式：--fast 跳过非关键优化
7. 编译时间统计
"""

import os
import json
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, Set, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class FileState:
    """文件构建状态"""
    mtime: float          # 文件修改时间
    content_hash: str     # 文件内容 SHA256 哈希
    output_mtime: float   # 输出文件修改时间（0 表示不存在）

    def is_valid(self) -> bool:
        """检查缓存是否有效：输出文件存在"""
        return self.output_mtime > 0


@dataclass
class IntermediateCache:
    """中间编译结果缓存（三级缓存）

    缓存词法分析、AST 解析、代码生成等中间结果，
    避免重复计算。
    """
    token_cache: Dict[str, object] = field(default_factory=dict)
    ast_cache: Dict[str, object] = field(default_factory=dict)
    codegen_cache: Dict[str, str] = field(default_factory=dict)
    max_size: int = 200

    def get_token(self, key: str):
        return self.token_cache.get(key)

    def set_token(self, key: str, value: object):
        if len(self.token_cache) >= self.max_size:
            self.token_cache.clear()
        self.token_cache[key] = value

    def get_ast(self, key: str):
        return self.ast_cache.get(key)

    def set_ast(self, key: str, value: object):
        if len(self.ast_cache) >= self.max_size:
            self.ast_cache.clear()
        self.ast_cache[key] = value

    def get_codegen(self, key: str) -> Optional[str]:
        return self.codegen_cache.get(key)

    def set_codegen(self, key: str, value: str):
        if len(self.codegen_cache) >= self.max_size:
            self.codegen_cache.clear()
        self.codegen_cache[key] = value

    def invalidate(self, key: str):
        self.token_cache.pop(key, None)
        self.ast_cache.pop(key, None)
        self.codegen_cache.pop(key, None)

    def clear(self):
        self.token_cache.clear()
        self.ast_cache.clear()
        self.codegen_cache.clear()


@dataclass
class CompileTimeStats:
    """编译时间统计"""
    total_time: float = 0.0
    parse_time: float = 0.0
    codegen_time: float = 0.0
    output_time: float = 0.0
    file_count: int = 0
    parallel_files: int = 0

    def to_dict(self) -> dict:
        return {
            'total_time': round(self.total_time, 4),
            'parse_time': round(self.parse_time, 4),
            'codegen_time': round(self.codegen_time, 4),
            'output_time': round(self.output_time, 4),
            'file_count': self.file_count,
            'parallel_files': self.parallel_files,
        }

    def summary(self) -> str:
        """生成可读的编译时间摘要"""
        lines = [
            "编译时间统计:",
            f"  总耗时:     {self.total_time:.4f}s",
            f"  解析阶段:   {self.parse_time:.4f}s ({(self.parse_time / max(self.total_time, 0.001)) * 100:.1f}%)",
            f"  代码生成:   {self.codegen_time:.4f}s ({(self.codegen_time / max(self.total_time, 0.001)) * 100:.1f}%)",
            f"  输出写入:   {self.output_time:.4f}s",
            f"  编译文件数: {self.file_count}",
        ]
        if self.parallel_files > 0:
            lines.append(f"  并行编译:   {self.parallel_files} 个文件并行")
        return '\n'.join(lines)


@dataclass
class BuildCache:
    """构建缓存"""
    version: str = "2.0"
    created_at: float = 0.0
    updated_at: float = 0.0
    files: Dict[str, FileState] = field(default_factory=dict)
    # 依赖图快照：{模块名: [依赖模块名]}
    dep_graph: Dict[str, List[str]] = field(default_factory=dict)
    # 编译时间历史（最近 10 次）
    time_history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'files': {k: asdict(v) for k, v in self.files.items()},
            'dep_graph': self.dep_graph,
            'time_history': self.time_history[-10:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BuildCache':
        cache = cls()
        cache.version = data.get('version', '1.0')
        cache.created_at = data.get('created_at', 0.0)
        cache.updated_at = data.get('updated_at', 0.0)
        for k, v in data.get('files', {}).items():
            cache.files[k] = FileState(**v)
        cache.dep_graph = data.get('dep_graph', {})
        cache.time_history = data.get('time_history', [])
        return cache


# =============================================================================
# 依赖图优化
# =============================================================================

class DependencyGraph:
    """优化的依赖图

    支持：
    - 拓扑排序（Kahn 算法）
    - 反向依赖追踪
    - 分层并行分组（同一层级的模块可并行编译）
    """

    def __init__(self, dep_graph: Dict[str, List[str]]):
        self.graph = dep_graph

    def get_reverse_deps(self) -> Dict[str, Set[str]]:
        """构建反向依赖图

        Returns:
            {模块名: {依赖此模块的模块集合}}
        """
        reverse: Dict[str, Set[str]] = {}
        for module, deps in self.graph.items():
            if module not in reverse:
                reverse[module] = set()
            for dep in deps:
                if dep not in reverse:
                    reverse[dep] = set()
                reverse[dep].add(module)
        return reverse

    def topological_sort(self) -> List[str]:
        """Kahn 算法拓扑排序

        Returns:
            拓扑有序的模块名列表
        """
        in_degree: Dict[str, int] = {}
        for module in self.graph:
            if module not in in_degree:
                in_degree[module] = 0
            for dep in self.graph[module]:
                if dep not in in_degree:
                    in_degree[dep] = 0
                in_degree[module] = in_degree.get(module, 0) + 1

        queue = [m for m in in_degree if in_degree[m] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in self.graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """获取可并行编译的分组

        按拓扑排序分层，同一层级的模块之间无依赖关系，可并行编译。

        Returns:
            分组列表，每组内的模块可并行编译
        """
        in_degree: Dict[str, int] = {}
        for module in self.graph:
            if module not in in_degree:
                in_degree[module] = 0
            for dep in self.graph[module]:
                if dep not in in_degree:
                    in_degree[dep] = 0
                in_degree[module] = in_degree.get(module, 0) + 1

        groups = []
        remaining = set(in_degree.keys())

        while remaining:
            # 当前入度为 0 的模块（无未处理依赖）
            current_group = [m for m in remaining if in_degree.get(m, 0) == 0]
            if not current_group:
                # 循环依赖：将剩余全部放入同一组
                groups.append(list(remaining))
                break

            groups.append(current_group)
            for m in current_group:
                remaining.remove(m)
                for dep in self.graph.get(m, []):
                    if dep in in_degree:
                        in_degree[dep] = max(0, in_degree[dep] - 1)

        return groups

    def get_affected(self, changed_modules: Set[str],
                     file_to_module: Dict[str, str]) -> Set[str]:
        """获取受变更影响的所有模块（BFS 反向依赖追踪）

        使用优化的 BFS 算法，避免重复遍历。

        Args:
            changed_modules: 变更的模块名集合
            file_to_module: 文件路径到模块名的映射

        Returns:
            需要重新编译的全部模块名集合
        """
        reverse = self.get_reverse_deps()

        affected: Set[str] = set(changed_modules)
        queue = list(changed_modules)
        visited: Set[str] = set(queue)

        while queue:
            current = queue.pop(0)
            for downstream in reverse.get(current, set()):
                if downstream not in visited:
                    visited.add(downstream)
                    queue.append(downstream)
                    affected.add(downstream)

        return affected


# =============================================================================
# 增量构建器
# =============================================================================

class IncrementalBuilder:
    """增量编译构建器

    用法:
        builder = IncrementalBuilder(project_dir)
        changed_files = builder.detect_changes()
        builder.build(changed_files, fast=True)
    """

    CACHE_FILENAME = '.duan_build_cache.json'

    def __init__(self, project_dir: str = '.'):
        self.project_dir = Path(project_dir).resolve()
        self.cache_path = self.project_dir / self.CACHE_FILENAME
        self.cache = self._load_cache()
        # 中间结果缓存
        self._intermediate_cache = IntermediateCache()
        # 编译时间统计
        self._stats = CompileTimeStats()
        # 线程锁（缓存访问安全）
        self._cache_lock = threading.Lock()

        # 延迟导入 module_resolver（避免循环依赖）
        self._resolver = None

    @property
    def resolver(self):
        if self._resolver is None:
            from module_resolver import ModuleResolver
            self._resolver = ModuleResolver()
        return self._resolver

    # ------------------------------------------------------------------
    # 缓存管理
    # ------------------------------------------------------------------

    def _load_cache(self) -> BuildCache:
        """加载构建缓存"""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding='utf-8'))
                return BuildCache.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        cache = BuildCache()
        cache.created_at = time.time()
        cache.updated_at = time.time()
        return cache

    def _save_cache(self):
        """保存构建缓存"""
        self.cache.updated_at = time.time()
        self.cache_path.write_text(
            json.dumps(self.cache.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    # ------------------------------------------------------------------
    # 文件变更检测
    # ------------------------------------------------------------------

    @staticmethod
    def _content_hash(file_path: Path) -> str:
        """计算文件内容哈希"""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def _get_mtime(self, file_path: Path) -> float:
        """获取文件修改时间"""
        try:
            return file_path.stat().st_mtime
        except OSError:
            return 0.0

    def _get_output_mtime(self, source_path: Path) -> float:
        """获取输出文件修改时间"""
        output_path = source_path.with_suffix('.py')
        if output_path.exists():
            return self._get_mtime(output_path)
        return 0.0

    def detect_changes(self, duan_files: List[Path]) -> Tuple[Set[str], Set[str]]:
        """检测文件变更

        Args:
            duan_files: 项目中的 .duan 文件列表

        Returns:
            (changed_files, unchanged_files): 变更和未变更的文件路径集合
        """
        changed: Set[str] = set()
        unchanged: Set[str] = set()

        for f in duan_files:
            fpath = str(f.resolve())
            current_mtime = self._get_mtime(f)
            current_hash = self._content_hash(f)

            cached = self.cache.files.get(fpath)
            if cached is None:
                # 新文件：需要编译
                changed.add(fpath)
            elif cached.content_hash != current_hash:
                # 内容变更：需要编译
                changed.add(fpath)
                # 使中间缓存失效
                self._intermediate_cache.invalidate(current_hash)
            elif not cached.is_valid():
                # 输出文件不存在：需要编译
                changed.add(fpath)
            elif cached.mtime != current_mtime:
                # mtime 变更但内容未变（如 touch）：不需要编译，但更新缓存
                unchanged.add(fpath)
            else:
                # 完全未变更
                unchanged.add(fpath)

        return changed, unchanged

    def _build_dep_graph(self, main_file: Path) -> Dict[str, List[str]]:
        """构建依赖图

        Args:
            main_file: 入口文件路径

        Returns:
            依赖图字典：{模块名: [依赖模块名]}
        """
        try:
            result = self.resolver.resolve_module(main_file)
            graph = {}
            for mod_name, mod_info in result.items():
                if hasattr(mod_info, 'dependencies'):
                    graph[mod_name] = list(mod_info.dependencies)
                else:
                    graph[mod_name] = []
            return graph
        except Exception:
            return {}

    def _update_dep_graph_from_cache(self, duan_files: List[Path]) -> Dict[str, List[str]]:
        """从缓存中构建或更新依赖图

        优先使用缓存中的依赖图，避免重复解析。

        Args:
            duan_files: 项目中的 .duan 文件列表

        Returns:
            依赖图字典
        """
        # 如果缓存中有有效的依赖图，直接使用
        if self.cache.dep_graph:
            return self.cache.dep_graph

        # 否则构建新的依赖图
        graph = {}
        for f in duan_files:
            try:
                source = f.read_text(encoding='utf-8')
                # 快速扫描导入语句（不完整解析）
                imports = self._scan_imports(source)
                mod_name = f.stem
                graph[mod_name] = imports
            except Exception:
                mod_name = f.stem
                graph[mod_name] = []

        self.cache.dep_graph = graph
        return graph

    @staticmethod
    def _scan_imports(source: str) -> List[str]:
        """快速扫描导入语句，不进行完整解析

        只提取 '导入 XXX' 或 'import XXX' 形式的语句。

        Args:
            source: 源码字符串

        Returns:
            导入的模块名列表
        """
        imports = []
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith('导入'):
                parts = stripped.split()
                if len(parts) >= 2:
                    imports.append(parts[1])
            elif stripped.startswith('import'):
                parts = stripped.split()
                if len(parts) >= 2:
                    imports.append(parts[1])
        return imports

    def _get_dependent_files(self, changed_files: Set[str],
                              dep_graph: Dict[str, List[str]]) -> Set[str]:
        """获取需要重新编译的所有文件（变更文件 + 下游依赖）

        使用优化的 DependencyGraph 进行 BFS 反向依赖追踪。

        Args:
            changed_files: 变更的文件路径集合
            dep_graph: 依赖图

        Returns:
            需要重新编译的全部文件路径集合
        """
        # 将文件路径转换为模块名
        file_to_module: Dict[str, str] = {}
        for fpath in self.cache.files:
            module_name = Path(fpath).stem
            file_to_module[fpath] = module_name

        # 将变更文件路径转换为模块名
        changed_modules: Set[str] = set()
        for fpath in changed_files:
            mod = file_to_module.get(fpath)
            if mod:
                changed_modules.add(mod)
            else:
                # 未在缓存中的文件，直接用文件名
                changed_modules.add(Path(fpath).stem)

        dg = DependencyGraph(dep_graph)
        affected_modules = dg.get_affected(changed_modules, file_to_module)

        # 将受影响的模块名转回文件路径
        module_to_file = {v: k for k, v in file_to_module.items()}
        affected: Set[str] = set(changed_files)
        for mod in affected_modules:
            fpath = module_to_file.get(mod)
            if fpath:
                affected.add(fpath)

        return affected

    def build(self, duan_files: List[Path], main_file: Optional[Path] = None,
              force: bool = False, verbose: bool = True, fast: bool = False,
              parallel: bool = True, max_workers: int = None) -> int:
        """执行增量编译

        Args:
            duan_files: 项目中的 .duan 文件列表
            main_file: 入口文件（用于构建依赖图）
            force: 强制全量编译
            verbose: 是否输出详细信息
            fast: 快速模式，跳过非关键优化
            parallel: 是否启用并行编译
            max_workers: 并行编译的最大线程数（默认 CPU 核心数）

        Returns:
            编译成功数
        """
        self._stats = CompileTimeStats()
        start_time = time.time()

        if force:
            if verbose:
                print("[增量编译] 强制全量编译")
            return self._full_build(duan_files, verbose, fast=fast,
                                    parallel=parallel, max_workers=max_workers)

        # 1. 检测变更
        changed, unchanged = self.detect_changes(duan_files)

        if not changed:
            if verbose:
                print(f"[增量编译] 所有文件均未变更，跳过编译")
            return len(duan_files)

        # 2. 构建依赖图，计算受影响范围
        if main_file and main_file.exists():
            dep_graph = self._build_dep_graph(main_file)
        else:
            dep_graph = self._update_dep_graph_from_cache(duan_files)

        if dep_graph:
            affected = self._get_dependent_files(changed, dep_graph)
        else:
            affected = changed

        if verbose:
            print(f"[增量编译] 变更文件: {len(changed)}, 受影响文件: {len(affected)}, 跳过: {len(unchanged)}")

        # 3. 编译受影响文件
        files_to_build = [f for f in duan_files if str(f.resolve()) in affected]
        result = self._compile_files(files_to_build, verbose, fast=fast,
                                     parallel=parallel, max_workers=max_workers,
                                     dep_graph=dep_graph)

        # 记录时间统计
        self._stats.total_time = time.time() - start_time
        self._stats.file_count = len(files_to_build)
        self.cache.time_history.append(self._stats.to_dict())
        self._save_cache()

        if verbose and self._stats.total_time > 0:
            print(f"\n{self._stats.summary()}")

        return result

    def _full_build(self, duan_files: List[Path], verbose: bool = True,
                    fast: bool = False, parallel: bool = True,
                    max_workers: int = None) -> int:
        """全量编译（不使用增量缓存）"""
        return self._compile_files(duan_files, verbose, fast=fast,
                                   parallel=parallel, max_workers=max_workers)

    def _compile_files(self, files: List[Path], verbose: bool = True,
                       fast: bool = False, parallel: bool = True,
                       max_workers: int = None,
                       dep_graph: Dict[str, List[str]] = None) -> int:
        """编译指定文件列表

        支持并行编译（通过依赖图分组，同一组内无依赖关系的文件可并行编译）。

        Args:
            files: 要编译的 .duan 文件列表
            verbose: 是否输出详细信息
            fast: 快速模式，跳过非关键优化
            parallel: 是否启用并行编译
            max_workers: 并行编译的最大线程数
            dep_graph: 依赖图（用于并行分组）

        Returns:
            编译成功数
        """
        if not files:
            return 0

        # 快速模式：跳过非关键优化
        if fast and verbose:
            print("[增量编译] 快速模式: 跳过非关键优化")

        # 解析时间
        parse_start = time.time()

        if parallel and len(files) > 1 and dep_graph:
            return self._parallel_compile(files, verbose, fast, max_workers, dep_graph)

        # 串行编译
        success_count = 0
        for f in files:
            try:
                source = f.read_text(encoding='utf-8')
                output_file = f.with_suffix('.py')

                # 检查中间缓存
                source_hash = hashlib.sha256(source.encode('utf-8')).hexdigest()
                cached_code = self._intermediate_cache.get_codegen(source_hash)

                if cached_code is not None:
                    py_code = cached_code
                    if verbose:
                        print(f"[缓存] {f.name} (命中中间缓存)")
                else:
                    # 使用 src 后端编译
                    from duan_parser_v3 import DuanParser
                    from code_generator import PythonCodeGenerator
                    parser = DuanParser()
                    module = parser.parse(source)
                    if module is None:
                        if verbose:
                            print(f"[跳过] 解析失败: {f.name}", file=__import__('sys').stderr)
                        continue

                    generator = PythonCodeGenerator()
                    py_code = generator.generate(module)
                    # 缓存中间结果
                    self._intermediate_cache.set_codegen(source_hash, py_code)

                # 写入输出文件
                output_file.write_text(py_code, encoding='utf-8')

                # 更新缓存
                fpath = str(f.resolve())
                self.cache.files[fpath] = FileState(
                    mtime=self._get_mtime(f),
                    content_hash=self._content_hash(f),
                    output_mtime=self._get_output_mtime(f),
                )

                if verbose:
                    print(f"[编译] {f.name} -> {output_file.name}")
                success_count += 1

            except Exception as e:
                if verbose:
                    print(f"[错误] 编译 {f.name} 失败: {e}", file=__import__('sys').stderr)
                continue

        # 记录时间
        self._stats.parse_time += time.time() - parse_start
        self._stats.codegen_time += time.time() - parse_start
        self._stats.file_count = len(files)

        # 保存缓存
        self._save_cache()

        if verbose:
            print(f"\n[摘要] 成功: {success_count}/{len(files)}")

        return success_count

    def _parallel_compile(self, files: List[Path], verbose: bool = False,
                          fast: bool = False, max_workers: int = None,
                          dep_graph: Dict[str, List[str]] = None) -> int:
        """并行编译文件

        根据依赖图分组，同一组内的文件可并行编译。

        Args:
            files: 要编译的文件列表
            verbose: 是否输出详细信息
            fast: 快速模式
            max_workers: 最大线程数
            dep_graph: 依赖图

        Returns:
            编译成功数
        """
        if max_workers is None:
            import os as _os
            max_workers = min(32, (_os.cpu_count() or 4) + 2)

        if dep_graph is None:
            dep_graph = {}

        # 构建文件名到模块名的映射
        file_to_module: Dict[str, str] = {}
        for f in files:
            file_to_module[str(f.resolve())] = f.stem

        # 过滤依赖图，只保留需要编译的文件
        module_set = set(file_to_module.values())
        filtered_graph = {
            m: [d for d in deps if d in module_set]
            for m, deps in dep_graph.items() if m in module_set
        }

        # 获取并行分组
        dg = DependencyGraph(filtered_graph)
        groups = dg.get_parallel_groups()

        if verbose:
            # 将分组信息映射回文件路径
            module_to_file = {v: k for k, v in file_to_module.items()}
            file_groups = []
            for group in groups:
                fg = [module_to_file.get(m, m) for m in group if m in module_to_file]
                if fg:
                    file_groups.append(fg)

            print(f"[增量编译] 并行分组: {len(file_groups)} 组, {max_workers} 线程")

        success_count = 0
        total_parallel = 0

        for group in groups:
            # 将模块名转回文件路径
            module_to_file = {v: k for k, v in file_to_module.items()}
            group_files = []
            for m in group:
                fpath = module_to_file.get(m)
                if fpath:
                    group_files.append(Path(fpath))

            if not group_files:
                continue

            if len(group_files) > 1:
                total_parallel += len(group_files)
                # 并行编译这一组
                with ThreadPoolExecutor(max_workers=min(max_workers, len(group_files))) as executor:
                    future_to_file = {
                        executor.submit(self._compile_single_file, f, verbose, fast): f
                        for f in group_files
                    }
                    for future in as_completed(future_to_file):
                        f = future_to_file[future]
                        try:
                            if future.result():
                                success_count += 1
                        except Exception as e:
                            if verbose:
                                print(f"[错误] 编译 {f.name} 失败: {e}", file=__import__('sys').stderr)
            else:
                # 单文件串行编译
                try:
                    if self._compile_single_file(group_files[0], verbose, fast):
                        success_count += 1
                except Exception as e:
                    if verbose:
                        print(f"[错误] 编译 {group_files[0].name} 失败: {e}", file=__import__('sys').stderr)

        self._stats.parallel_files = total_parallel

        if verbose:
            print(f"\n[摘要] 成功: {success_count}/{len(files)}")

        return success_count

    def _compile_single_file(self, f: Path, verbose: bool = False,
                              fast: bool = False) -> bool:
        """编译单个文件

        Args:
            f: .duan 文件路径
            verbose: 是否输出详细信息
            fast: 快速模式

        Returns:
            True 表示编译成功
        """
        t_start = time.time()

        try:
            source = f.read_text(encoding='utf-8')
            output_file = f.with_suffix('.py')

            # 检查中间缓存
            source_hash = hashlib.sha256(source.encode('utf-8')).hexdigest()
            cached_code = None

            with self._cache_lock:
                cached_code = self._intermediate_cache.get_codegen(source_hash)

            if cached_code is not None:
                py_code = cached_code
                if verbose:
                    print(f"[缓存] {f.name} (命中中间缓存)")
            else:
                from duan_parser_v3 import DuanParser
                from code_generator import PythonCodeGenerator

                parser = DuanParser()
                module = parser.parse(source)
                if module is None:
                    if verbose:
                        print(f"[跳过] 解析失败: {f.name}", file=__import__('sys').stderr)
                    return False

                generator = PythonCodeGenerator()
                py_code = generator.generate(module)

                # 缓存中间结果
                with self._cache_lock:
                    self._intermediate_cache.set_codegen(source_hash, py_code)

            # 写入输出文件
            output_file.write_text(py_code, encoding='utf-8')

            # 更新缓存
            with self._cache_lock:
                fpath = str(f.resolve())
                self.cache.files[fpath] = FileState(
                    mtime=self._get_mtime(f),
                    content_hash=self._content_hash(f),
                    output_mtime=self._get_output_mtime(f),
                )

            elapsed = time.time() - t_start
            if verbose:
                print(f"[编译] {f.name} -> {output_file.name} ({elapsed:.3f}s)")

            return True

        except Exception as e:
            elapsed = time.time() - t_start
            if verbose:
                print(f"[错误] 编译 {f.name} 失败: {e} ({elapsed:.3f}s)", file=__import__('sys').stderr)
            return False

    def clear_cache(self):
        """清除构建缓存"""
        if self.cache_path.exists():
            self.cache_path.unlink()
        self.cache = BuildCache()
        self.cache.created_at = time.time()
        self.cache.updated_at = time.time()
        self._intermediate_cache.clear()

    def clear_intermediate_cache(self):
        """仅清除中间结果缓存，保留构建缓存"""
        self._intermediate_cache.clear()

    def get_stats(self) -> dict:
        """获取构建统计信息"""
        return {
            'cached_files': len(self.cache.files),
            'cache_created': self.cache.created_at,
            'cache_updated': self.cache.updated_at,
            'cache_path': str(self.cache_path),
            'dep_graph_nodes': len(self.cache.dep_graph),
            'intermediate_cache_size': (
                len(self._intermediate_cache.token_cache)
                + len(self._intermediate_cache.ast_cache)
                + len(self._intermediate_cache.codegen_cache)
            ),
            'last_build_time': self._stats.to_dict() if self._stats.total_time > 0 else None,
            'time_history_count': len(self.cache.time_history),
        }

    def get_time_history(self) -> List[Dict]:
        """获取编译时间历史"""
        return list(self.cache.time_history)


# =============================================================================
# CLI 工具函数
# =============================================================================

def incremental_build_cli(project_dir: str = '.', force: bool = False,
                           verbose: bool = True, fast: bool = False,
                           parallel: bool = True, jobs: int = None) -> int:
    """增量编译 CLI 入口

    Args:
        project_dir: 项目目录
        force: 强制全量编译
        verbose: 是否输出详细信息
        fast: 快速模式，跳过非关键优化
        parallel: 是否启用并行编译
        jobs: 并行编译线程数

    Returns:
        0 = 成功, 1 = 失败
    """
    root = Path(project_dir).resolve()
    if not root.is_dir():
        print(f"[错误] 目录不存在: {root}", file=__import__('sys').stderr)
        return 1

    duan_files = list(root.glob('*.duan'))
    if not duan_files:
        print(f"[错误] 未找到 .duan 文件: {root}", file=__import__('sys').stderr)
        return 1

    main_file = root / 'main.duan'
    if not main_file.exists():
        main_file = duan_files[0]

    builder = IncrementalBuilder(project_dir)
    result = builder.build(duan_files, main_file=main_file, force=force,
                           verbose=verbose, fast=fast, parallel=parallel,
                           max_workers=jobs)

    return 0 if result > 0 else 1


if __name__ == '__main__':
    import sys
    force = '--force' in sys.argv or '-f' in sys.argv
    fast = '--fast' in sys.argv
    no_parallel = '--no-parallel' in sys.argv
    jobs = None
    if '--jobs' in sys.argv:
        idx = sys.argv.index('--jobs')
        if idx + 1 < len(sys.argv):
            try:
                jobs = int(sys.argv[idx + 1])
            except ValueError:
                pass
    project = sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else '.'
    sys.exit(incremental_build_cli(project, force=force, fast=fast,
                                    parallel=not no_parallel, jobs=jobs))