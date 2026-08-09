"""
Light 模块预处理器
在编译前处理导入语句，将多个模块内联为单个文件
"""

import os
from pathlib import Path
from typing import List, Dict, Set, Tuple


class ModulePreprocessor:
    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or []
        self.module_cache: Dict[str, str] = {}
        self.exported_symbols: Dict[str, Set[str]] = {}

    def find_module(self, module_name: str, current_dir: str) -> str:
        """查找模块文件路径"""
        file_name = module_name + ".light"
        paths_to_try = []
        paths_to_try.append(os.path.join(current_dir, file_name))
        paths_to_try.append(os.path.join(current_dir, "模块", file_name))
        paths_to_try.append(os.path.join(current_dir, "modules", file_name))
        paths_to_try.append(os.path.join(current_dir, "test_modules", file_name))
        for sp in self.search_paths:
            paths_to_try.append(os.path.join(sp, file_name))
        for path in paths_to_try:
            if os.path.exists(path):
                return os.path.normpath(path)
        raise FileNotFoundError(f"模块未找到: {module_name}\n搜索路径:\n" + 
                                "\n".join(f"  - {p}" for p in paths_to_try))

    def extract_imports(self, source: str) -> List[str]:
        """从源码中提取导入的模块名"""
        imports = []
        for line in source.split('\n'):
            stripped = line.strip()
            if stripped.startswith('导入 '):
                parts = stripped.split()
                if len(parts) >= 2:
                    module_name = parts[1]
                    if module_name not in imports:
                        imports.append(module_name)
        return imports

    def extract_exports(self, source: str) -> Set[str]:
        """从源码中提取导出的符号名"""
        exports = set()
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            # 独立导出语句：导出 符号名
            if stripped.startswith('导出 '):
                parts = stripped.split()
                if len(parts) >= 2:
                    exports.add(parts[1])
            # 内联导出：段 函数名 导出 接收 或 段落 函数名 导出 接收
            if ' 导出 ' in stripped and ('段 ' in stripped or '段落 ' in stripped):
                parts = stripped.split()
                for j, p in enumerate(parts):
                    if p == '导出' and j > 0:
                        if parts[0] == '段' or parts[0] == '段落':
                            if j >= 2:
                                exports.add(parts[j - 1])
        return exports

    def build_dependency_graph(self, main_file: str) -> Tuple[Dict[str, str], List[str]]:
        """构建依赖图并拓扑排序"""
        modules = {}
        main_dir = os.path.dirname(os.path.abspath(main_file))
        to_visit = [(main_file, main_dir)]
        visited = set()
        order = []

        while to_visit:
            module_path, current_dir = to_visit.pop()
            abs_path = os.path.normpath(os.path.abspath(module_path))
            if abs_path in visited:
                continue
            visited.add(abs_path)
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
            modules[abs_path] = source
            module_name = os.path.splitext(os.path.basename(module_path))[0]
            order.append((abs_path, module_name))
            imports = self.extract_imports(source)
            for imp in reversed(imports):
                try:
                    found_path = self.find_module(imp, current_dir)
                    found_dir = os.path.dirname(found_path)
                    to_visit.append((found_path, found_dir))
                except FileNotFoundError:
                    pass

        return modules, [p for p, _ in order]

    def detect_circular_deps(self, modules: Dict[str, str], order: List[str]) -> List[str]:
        """检测循环依赖"""
        graph = {}
        name_to_path = {}
        for path in order:
            name = os.path.splitext(os.path.basename(path))[0]
            name_to_path[name] = path
            imports = self.extract_imports(modules[path])
            graph[path] = set()
            for imp in imports:
                if imp in name_to_path:
                    graph[path].add(name_to_path[imp])

        visited = set()
        rec_stack = set()
        cycle = []

        def dfs(node, path):
            if node in rec_stack:
                idx = path.index(node)
                cycle.extend(path[idx:] + [node])
                return True
            if node in visited:
                return False
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, set()):
                if dfs(neighbor, path + [neighbor]):
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if dfs(node, [node]):
                return cycle
        return []

    def inline_modules(self, main_file: str) -> str:
        """将主文件及其所有依赖内联为单个源码"""
        modules, order = self.build_dependency_graph(main_file)
        cycle = self.detect_circular_deps(modules, order)
        if cycle:
            names = [os.path.basename(p) for p in cycle]
            raise ValueError(f"检测到循环依赖: {' → '.join(names)}")

        combined = []
        processed = set()
        for path in reversed(order):
            if path in processed:
                continue
            processed.add(path)
            source = modules[path]
            filtered_lines = []
            for line in source.split('\n'):
                stripped = line.strip()
                if stripped.startswith('导入 '):
                    continue
                filtered_lines.append(line)
            combined.extend(filtered_lines)
            combined.append('')

        return '\n'.join(combined)


def preprocess_compile(main_file: str, compile_func) -> str:
    """预处理并编译主文件"""
    preprocessor = ModulePreprocessor()
    combined_source = preprocessor.inline_modules(main_file)
    return compile_func(combined_source)
