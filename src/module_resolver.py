"""
光明（Light）编程语言 - 模块解析器

实现功能：
1. 模块查找（搜索.light文件）
2. 依赖图构建
3. 循环依赖检测
4. 拓扑排序（确定编译顺序）
"""

import os
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field

# 添加 src 目录到路径
import sys
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from light_parser_v3 import LightParser, ImportStmt


# =============================================================================
# 错误类型
# =============================================================================

class ModuleError(Exception):
    """模块相关错误基类"""
    pass


class ModuleNotFoundError(ModuleError):
    """模块未找到"""
    def __init__(self, module_name: str, search_paths: List[str]):
        self.module_name = module_name
        self.search_paths = search_paths
        message = f"模块未找到: '{module_name}'\n搜索路径:\n"
        for path in search_paths:
            message += f"  - {path}\n"
        super().__init__(message)


class CircularDependencyError(ModuleError):
    """循环依赖错误"""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        # 增强格式：显示环路径 + 修复建议
        message = "检测到循环依赖:\n  " + " → ".join(cycle)
        message += "\n\n修复建议:"
        message += "\n  1. 检查模块间的导入关系，避免相互引用"
        message += "\n  2. 将公共功能提取到独立模块，由相互依赖的双方共同引用"
        message += "\n  3. 使用接口抽象解耦模块依赖"
        # A2-6：这一条以前只写「在段落内部延迟导入」五个字，而实测那条绕法**当时并不
        # 工作**（依赖抽取的文本兜底把缩进的导入也算成模块级依赖，环照报）。已在
        # `_extract_imports_from_text` 修好，同时把建议写成可照抄的形状——文档腐烂的
        # 修法是让建议真能用，不是把建议删掉。
        message += "\n  4. 把回边改成**段落体内的延迟导入**（缩进写在段落里，"
        message += "调用时才执行，不计入模块级依赖）："
        message += "\n       《乙活》段()："
        message += "\n         从《甲》导入《甲活》。      ← 缩进，不是顶格"
        message += "\n         返回 甲活()。"
        message += "\n       结束。"
        message += "\n     注意：顶格写的导入一律算模块级依赖，照旧拒绝成环。"
        message += "\n  5. 检查模块名是否写错，导致误导入"
        if len(cycle) >= 2:
            message += f"\n  6. 请检查模块「{cycle[0]}」和「{cycle[1]}」之间的相互导入"
        super().__init__(message)


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str                    # 模块名
    path: Path                   # 文件路径
    imports: List[ImportStmt]    # 导入的模块
    dependencies: Set[str] = field(default_factory=set)  # 依赖的模块名
    exports: List[str] = field(default_factory=list)     # 导出的符号
    
    def __repr__(self):
        return f"ModuleInfo({self.name}, deps={self.dependencies})"


@dataclass
class DependencyGraph:
    """依赖图"""
    nodes: Dict[str, ModuleInfo] = field(default_factory=dict)
    edges: Dict[str, Set[str]] = field(default_factory=dict)
    
    def add_module(self, module: ModuleInfo):
        """添加模块节点"""
        self.nodes[module.name] = module
        if module.name not in self.edges:
            self.edges[module.name] = set()
    
    def add_dependency(self, from_module: str, to_module: str):
        """添加依赖关系"""
        if from_module not in self.edges:
            self.edges[from_module] = set()
        self.edges[from_module].add(to_module)
    
    def get_dependencies(self, module_name: str) -> Set[str]:
        """获取模块的直接依赖"""
        return self.edges.get(module_name, set())
    
    def get_all_dependencies(self, module_name: str) -> Set[str]:
        """获取模块的所有依赖（递归）"""
        all_deps = set()
        to_visit = list(self.get_dependencies(module_name))
        
        while to_visit:
            dep = to_visit.pop()
            if dep not in all_deps:
                all_deps.add(dep)
                to_visit.extend(self.get_dependencies(dep))
        
        return all_deps


# =============================================================================
# 模块解析器
# =============================================================================

class ModuleResolver:
    """模块解析器"""
    
    def __init__(self, search_paths: List[str] = None, auto_load_stdlib: bool = True):
        """
        初始化模块解析器
        
        Args:
            search_paths: 模块搜索路径列表，None表示使用默认路径
            auto_load_stdlib: 是否自动加载标准库模块
        """
        # 默认搜索路径：当前目录 + stdlib 目录 + contrib 目录
        base_dir = os.path.dirname(__file__)
        stdlib_path = os.path.join(base_dir, '..', 'stdlib')
        contrib_path = os.path.join(base_dir, '..', 'contrib')
        if search_paths is None:
            search_paths = ['.', stdlib_path, contrib_path]
        self.search_paths = search_paths
        self.stdlib_path = stdlib_path
        self.lexer = Lexer()
        self.parser = LightParser()
        self.module_cache: Dict[str, ModuleInfo] = {}
        self._stdlib_modules: Dict[str, ModuleInfo] = {}
        self._builtins_loaded = False
        self.auto_load_stdlib = auto_load_stdlib
        if auto_load_stdlib:
            self._discover_stdlib_modules()
    
    def _discover_stdlib_modules(self):
        """发现并缓存标准库中的所有模块"""
        stdlib_dir = Path(self.stdlib_path)
        if not stdlib_dir.exists():
            return
        
        # 扫描 .light 和 .py 文件
        for ext in ['*.light', '*.py']:
            for module_path in stdlib_dir.glob(ext):
                module_name = module_path.stem
                if module_name.startswith('__'):
                    continue
                try:
                    module_info = self.parse_module(module_path)
                    self._stdlib_modules[module_name] = module_info
                except Exception:
                    pass  # 跳过无法解析的标准库模块
    
    def get_stdlib_module(self, module_name: str) -> Optional[ModuleInfo]:
        """获取标准库模块信息"""
        return self._stdlib_modules.get(module_name)
    
    def get_stdlib_module_names(self) -> List[str]:
        """获取所有可用的标准库模块名"""
        return sorted(self._stdlib_modules.keys())
    
    def load_stdlib_module(self, module_name: str) -> Optional[ModuleInfo]:
        """
        加载标准库模块
        
        Args:
            module_name: 模块名
        
        Returns:
            模块信息，如果未找到则返回 None
        """
        if module_name in self.module_cache:
            return self.module_cache[module_name]
        
        module_info = self._stdlib_modules.get(module_name)
        if module_info:
            self.module_cache[module_name] = module_info
            return module_info
        
        return None
    
    def preload_builtins(self):
        """
        预加载内置模块（builtins）
        确保内置函数在编译时可用
        """
        if self._builtins_loaded:
            return
        
        builtins_path = Path(self.stdlib_path) / 'builtins.py'
        if builtins_path.exists():
            try:
                module_info = self.parse_module(builtins_path)
                self.module_cache['builtins'] = module_info
                self._builtins_loaded = True
            except Exception:
                pass
        
        # 也尝试加载 builtins.light
        builtins_light = Path(self.stdlib_path) / 'builtins.light'
        if builtins_light.exists():
            try:
                module_info = self.parse_module(builtins_light)
                self.module_cache['builtins'] = module_info
                self._builtins_loaded = True
            except Exception:
                pass
    
    def find_module(self, module_name: str, from_dir: str = None) -> Path:
        """
        查找模块文件
        
        Args:
            module_name: 模块名
            from_dir: 从哪个目录开始查找（用于相对导入）
        
        Returns:
            模块文件路径
        
        Raises:
            ModuleNotFoundError: 模块未找到
        """
        # 模块文件名（优先 .light，其次 .py）
        module_files = [f"{module_name}.light", f"{module_name}.py"]
        
        # 构建搜索路径
        search_dirs = []
        
        # 1. 从当前目录查找（如果有）
        if from_dir:
            search_dirs.append(from_dir)
        
        # 2. 从搜索路径查找
        search_dirs.extend(self.search_paths)
        
        # 3. 从环境变量 LIGHT_PATH 查找
        light_path = os.environ.get('LIGHT_PATH', '')
        if light_path:
            search_dirs.extend(light_path.split(os.pathsep))
        
        # 搜索
        searched = []
        for search_dir in search_dirs:
            search_path = Path(search_dir)
            if not search_path.is_absolute():
                search_path = Path.cwd() / search_path
            
            for module_file in module_files:
                module_path = search_path / module_file
                searched.append(str(module_path))
                
                if module_path.exists():
                    return module_path.resolve()
        
        # 未找到
        raise ModuleNotFoundError(module_name, searched)
    
    def parse_module(self, module_path: Path) -> ModuleInfo:
        """
        解析模块文件
        
        Args:
            module_path: 模块文件路径
        
        Returns:
            模块信息
        """
        # 检查缓存
        module_name = module_path.stem
        if module_name in self.module_cache:
            return self.module_cache[module_name]
        
        # 读取文件
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # 根据文件扩展名选择解析方式
        suffix = module_path.suffix
        if suffix == '.py':
            return self._parse_python_module(module_path, source)
        
        # 光明文件：使用光明解析器
        # 词法分析和语法解析
        try:
            tokens = self.lexer.tokenize(source)
            module_ast = self.parser.parse(source)
        except Exception:
            # 光明解析器失败（如 src 后端 lexer bug），
            # 尝试用同名 .py 文件解析
            py_path = module_path.with_suffix('.py')
            if py_path.exists():
                with open(py_path, 'r', encoding='utf-8') as f:
                    py_source = f.read()
                return self._parse_python_module(py_path, py_source)
            # 没有 .py fallback，尝试从文本提取导出符号和导入依赖
            text_exports = self._extract_exports_from_text(source)
            text_deps = self._extract_imports_from_text(source)
            module_info = ModuleInfo(
                name=module_name,
                path=module_path,
                imports=[],
                dependencies=text_deps,
                exports=text_exports
            )
            self.module_cache[module_name] = module_info
            return module_info
        
        # 提取导入语句
        imports = []
        dependencies = set()
        
        for stmt in module_ast.statements:
            if isinstance(stmt, ImportStmt):
                imports.append(stmt)
                dependencies.add(stmt.module_name)
        
        # 提取导出符号
        exports = []
        for stmt in module_ast.statements:
            if hasattr(stmt, 'symbols') and stmt.symbols:
                if stmt.symbols == ['*']:
                    # 导出全部，需要收集所有函数名
                    for s in module_ast.statements:
                        if hasattr(s, 'name') and hasattr(s, 'params'):
                            # 这是段落定义
                            exports.append(s.name)
                else:
                    exports.extend(stmt.symbols)
        
        # 如果光明解析未能提取到 exports，尝试同名 .py 文件
        if not exports:
            py_path = module_path.with_suffix('.py')
            if py_path.exists():
                with open(py_path, 'r', encoding='utf-8') as f:
                    py_source = f.read()
                return self._parse_python_module(py_path, py_source)
        
        # 如果仍然没有 exports，尝试从源码文本中提取"导出"语句
        if not exports:
            exports = self._extract_exports_from_text(source)
        
        # 如果光明解析未能提取到 dependencies，也尝试从文本提取
        if not dependencies:
            dependencies = self._extract_imports_from_text(source)
        
        # 创建模块信息
        module_info = ModuleInfo(
            name=module_name,
            path=module_path,
            imports=imports,
            dependencies=dependencies,
            exports=exports
        )
        
        # 缓存
        self.module_cache[module_name] = module_info
        
        return module_info
    
    def _parse_python_module(self, module_path: Path, source: str) -> ModuleInfo:
        """
        解析 Python 格式的模块文件（如 stdlib 中的 .py 文件）
        
        使用 Python AST 解析器提取导出符号和导入依赖。
        
        Args:
            module_path: 模块文件路径
            source: 文件源代码
        
        Returns:
            模块信息
        """
        module_name = module_path.stem
        
        # 检查缓存
        if module_name in self.module_cache:
            return self.module_cache[module_name]
        
        import ast as python_ast
        
        try:
            tree = python_ast.parse(source)
        except SyntaxError:
            # 解析失败，返回空信息
            module_info = ModuleInfo(
                name=module_name,
                path=module_path,
                imports=[],
                dependencies=set(),
                exports=[]
            )
            self.module_cache[module_name] = module_info
            return module_info
        
        # 提取导入依赖
        dependencies = set()
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.Import):
                for alias in node.names:
                    dependencies.add(alias.name)
            elif isinstance(node, python_ast.ImportFrom):
                if node.module:
                    dependencies.add(node.module)
        
        # 提取导出符号
        exports = []
        # 先检查 __all__
        all_names = None
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.Assign):
                for target in node.targets:
                    if isinstance(target, python_ast.Name) and target.id == '__all__':
                        if isinstance(node.value, python_ast.List):
                            all_names = [
                                elt.value for elt in node.value.elts
                                if isinstance(elt, python_ast.Constant)
                            ]
        
        if all_names is not None:
            exports = all_names
        else:
            # 没有 __all__，收集所有顶级定义
            for node in tree.body:
                if isinstance(node, python_ast.FunctionDef):
                    exports.append(node.name)
                elif isinstance(node, python_ast.ClassDef):
                    exports.append(node.name)
                elif isinstance(node, python_ast.Assign):
                    for target in node.targets:
                        if isinstance(target, python_ast.Name):
                            exports.append(target.id)
        
        module_info = ModuleInfo(
            name=module_name,
            path=module_path,
            imports=[],
            dependencies=dependencies,
            exports=exports
        )
        
        self.module_cache[module_name] = module_info
        return module_info
    
    def _extract_exports_from_text(self, source: str) -> List[str]:
        """
        从源码文本中提取"导出"语句声明的符号名。
        
        支持两种格式：
        - 导出 符号一 符号二。
        - 导出《符号一》，《符号二》。
        
        Args:
            source: 源码文本
        
        Returns:
            导出符号名列表
        """
        import re
        exports = []
        for line in source.split('\n'):
            line = line.strip()
            if not line.startswith('导出'):
                continue
            
            # 格式1: 导出《符号一》，《符号二》。
            # 格式2: 导出 符号一 符号二。
            # 提取《》内的名称
            book_names = re.findall(r'《([^》]+)》', line)
            if book_names:
                exports.extend(book_names)
                continue
            
            # 提取空格/逗号分隔的名称（去掉句号）
            # 格式: 导出 符号一 符号二。 或 导出 符号一，符号二。
            rest = line[2:].strip()  # 去掉"导出"
            rest = rest.rstrip('。')  # 去掉句号
            if rest:
                # 按逗号或空格分割
                names = re.split(r'[，,\s]+', rest)
                exports.extend(n for n in names if n)
        
        return exports
    
    def _extract_imports_from_text(self, source: str) -> Set[str]:
        """
        从源码文本中提取"从...导入..."语句声明的**模块级**依赖。

        支持格式：
        - 从《模块名》导入《符号》。
        - 从《模块名》导入《符号一》，《符号二》。
        - 导入《模块名》。

        A2-6：**只认顶格（无缩进）的导入行**。

        为什么：本方法是 `parse_module` 的兜底（AST 里没抽到 ImportStmt 时才调，
        见 :352-354），而 AST 那条路只扫 `module_ast.statements`（顶层）。两条路
        口径原本不一致——一个模块如果**只在段落体内**写导入，AST 抽到 0 条、于是
        落到本方法，本方法 `line.strip()` 之后把缩进信息扔掉，把段落体内的延迟导入
        也算成模块级依赖。实测（`_taskA2_probe9.py`，两模块对照）：回边写在段落体内
        的那组，`延迟乙` 的 `imports=0` 却 `dependencies=['延迟甲']`，
        `detect_circular_dependency` 照样报环 `['延迟甲','延迟乙','延迟甲']`——
        也就是说 CircularDependencyError 文案 :54 里官方建议的那条绕法
        「在段落内部延迟导入」**自己不工作**。

        判据取「行首有无空白」而不是解析：本方法存在的前提就是解析已经失败或没抽到，
        不能反过来依赖解析。缩进的导入是函数体内的局部导入，按 Python 语义它在
        **调用时**才执行，模块级依赖图里本来就不该有这条边。

        顶层循环依赖照旧拒绝（`detect_circular_dependency` / `topological_sort`
        一行未动，没有任何放行开关）。

        Args:
            source: 源码文本

        Returns:
            模块级依赖模块名集合
        """
        import re
        dependencies = set()
        for raw_line in source.split('\n'):
            # 顶格判据：有前导空白 → 段落/类体内的延迟导入，不计入模块级依赖
            if raw_line[:1] in (' ', '\t'):
                continue
            line = raw_line.strip()

            # 格式: 从《模块名》导入...
            if line.startswith('从'):
                match = re.match(r'从《([^》]+)》', line)
                if match:
                    dependencies.add(match.group(1))
                continue

            # 格式: 导入《模块名》。
            if line.startswith('导入'):
                match = re.match(r'导入《([^》]+)》', line)
                if match:
                    dependencies.add(match.group(1))

        return dependencies
    
    def build_dependency_graph(self, main_module: str, from_dir: str = None) -> DependencyGraph:
        """
        构建依赖图
        
        Args:
            main_module: 主模块名
            from_dir: 主模块所在目录
        
        Returns:
            依赖图
        """
        graph = DependencyGraph()
        visited = set()
        
        def visit(module_name: str, module_dir: str = None):
            """访问模块并构建依赖图"""
            if module_name in visited:
                return
            
            visited.add(module_name)
            
            # 查找模块
            module_path = self.find_module(module_name, module_dir)
            
            # 解析模块
            module_info = self.parse_module(module_path)
            
            # 添加到图
            graph.add_module(module_info)
            
            # 处理依赖
            module_dir = str(module_path.parent)
            for dep_name in module_info.dependencies:
                try:
                    visit(dep_name, module_dir)
                    graph.add_dependency(module_name, dep_name)
                except ModuleNotFoundError as e:
                    print(f"警告: {e}")
        
        # 从主模块开始构建
        visit(main_module, from_dir)
        
        return graph
    
    def detect_circular_dependency(self, graph: DependencyGraph) -> Optional[List[str]]:
        """
        检测循环依赖
        
        Args:
            graph: 依赖图
        
        Returns:
            循环依赖路径，如果没有则返回 None
        """
        # 使用 DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph.nodes}
        parent = {}
        
        def dfs(node: str) -> Optional[List[str]]:
            """深度优先搜索检测环"""
            color[node] = GRAY
            
            for neighbor in graph.get_dependencies(node):
                if color.get(neighbor, WHITE) == GRAY:
                    # 找到环，构建环路径
                    cycle = [neighbor]
                    current = node
                    while current != neighbor:
                        cycle.append(current)
                        current = parent.get(current)
                        if current is None:
                            break
                    cycle.append(neighbor)
                    return list(reversed(cycle))
                
                if color.get(neighbor, WHITE) == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        # 从每个未访问的节点开始
        for node in graph.nodes:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result
        
        return None
    
    def detect_all_cycles(self, graph: DependencyGraph) -> List[List[str]]:
        """
        检测所有循环依赖，返回所有环的列表
        
        Args:
            graph: 依赖图
        
        Returns:
            所有循环依赖路径的列表，每个元素是一个环路径
        """
        # 使用 DFS 检测所有环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph.nodes}
        parent = {}
        all_cycles = []
        visited_edges = set()  # 用于去重，避免报告重复的环
        
        def dfs(node: str, path_stack: List[str]):
            """深度优先搜索检测所有环"""
            color[node] = GRAY
            path_stack.append(node)
            
            for neighbor in graph.get_dependencies(node):
                if color.get(neighbor, WHITE) == GRAY:
                    # 找到环，构建环路径
                    cycle = []
                    # 从 path_stack 中提取环
                    idx = path_stack.index(neighbor)
                    cycle = path_stack[idx:] + [neighbor]
                    
                    # 规范化环表示：以最小节点开头、按最小旋转
                    if cycle:
                        min_idx = cycle.index(min(cycle))
                        cycle = cycle[min_idx:] + cycle[1:min_idx + 1]
                    
                    cycle_key = tuple(cycle)
                    if cycle_key not in visited_edges:
                        visited_edges.add(cycle_key)
                        all_cycles.append(cycle)
                
                elif color.get(neighbor, WHITE) == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor, path_stack)
            
            path_stack.pop()
            color[node] = BLACK
        
        # 从每个未访问的节点开始
        for node in graph.nodes:
            if color[node] == WHITE:
                dfs(node, [])
        
        return all_cycles
    
    def topological_sort(self, graph: DependencyGraph) -> List[str]:
        """
        拓扑排序（确定编译顺序）
        
        Args:
            graph: 依赖图
        
        Returns:
            模块名列表（按编译顺序）
        """
        # 使用 Kahn 算法
        in_degree = {node: 0 for node in graph.nodes}
        
        # 计算入度
        for node in graph.nodes:
            for dep in graph.get_dependencies(node):
                if dep in in_degree:
                    in_degree[node] += 1
        
        # 找到所有入度为0的节点
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按字典序排序，保证确定性
            queue.sort()
            node = queue.pop(0)
            result.append(node)
            
            # 更新依赖此节点的模块的入度
            for other in graph.nodes:
                if node in graph.get_dependencies(other):
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
        
        # 检查是否所有节点都已处理
        if len(result) != len(graph.nodes):
            # 有环，不应该发生（应该先检测环）
            remaining = [node for node in graph.nodes if node not in result]
            raise CircularDependencyError(remaining)
        
        return result
    
    def resolve(self, main_file: str) -> Tuple[List[ModuleInfo], DependencyGraph]:
        """
        解析主文件及其所有依赖
        
        Args:
            main_file: 主文件路径
        
        Returns:
            (模块列表（按编译顺序），依赖图)
        
        Raises:
            ModuleNotFoundError: 模块未找到
            CircularDependencyError: 循环依赖
        """
        # 获取主模块信息
        main_path = Path(main_file).resolve()
        main_dir = str(main_path.parent)
        main_name = main_path.stem
        
        # 构建依赖图
        graph = self.build_dependency_graph(main_name, main_dir)
        
        # 检测循环依赖
        cycle = self.detect_circular_dependency(graph)
        if cycle:
            raise CircularDependencyError(cycle)
        
        # 拓扑排序
        order = self.topological_sort(graph)
        
        # 按顺序获取模块信息
        modules = [graph.nodes[name] for name in order]
        
        return modules, graph


# =============================================================================
# ModuleDependencyResolver —— 从入口模块递归解析依赖 + 拓扑排序
# =============================================================================

@dataclass
class ResolvedModule:
    """已解析模块（用于 compile_project 跨模块链接）"""
    name: str
    path: Path
    imports: List[str] = field(default_factory=list)
    source: str = ""
    ast: Any = None  # light_parser_v3.Module
    exports: List[str] = field(default_factory=list)  # 可外部可见的符号名


class CircularDependencyError(Exception):
    """循环依赖错误（与上方重名但可共存，此处保持清晰）"""

    def __init__(self, cycle: List[str]):
        self.cycle = list(cycle)
        message = "检测到循环依赖:\n  " + " → ".join(self.cycle)
        message += "\n\n修复建议:"
        message += "\n  1. 检查模块间的导入关系，避免相互引用"
        message += "\n  2. 将公共功能提取到独立模块，由相互依赖的双方共同引用"
        message += "\n  3. 使用接口抽象解耦模块依赖"
        message += "\n  4. 在段落内部延迟导入（局部导入），避免模块级循环"
        message += "\n  5. 检查模块名是否写错，导致误导入"
        if len(self.cycle) >= 2:
            message += f"\n  6. 请检查模块「{self.cycle[0]}」和「{self.cycle[1]}」之间的相互导入"
        super().__init__(message)


class ModuleDependencyResolver:
    """递归解析入口模块及所有 import 依赖，进行循环检测与拓扑排序。

    与模块中的 ImportStmt（`导入 模块`、`从 模块 导入 符号`）协同工作。
    支持相对导入（`从 .模块 导入 符号` / `从 ..模块 导入 符号`），
    并对已解析的文件提供缓存（按修改时间自动失效）。
    """

    def __init__(self, search_paths: List[Path]):
        # 规范化搜索路径
        self.search_paths: List[Path] = [Path(p) for p in search_paths]
        self.modules: Dict[str, ResolvedModule] = {}
        # 文件级缓存：key=绝对路径字符串
        # value = {'mtime': int, 'size': int, 'source': str, 'ast': Any,
        #          'imports': List[str], 'exports': List[str]}
        self._cache: Dict[str, Dict[str, Any]] = {}
        # 统计：parsed=实际解析次数，cache_hits=缓存命中次数
        self.stats: Dict[str, int] = {'parsed': 0, 'cache_hits': 0}

    def clear_cache(self) -> None:
        """清空模块缓存与统计信息。"""
        self._cache.clear()
        self.stats = {'parsed': 0, 'cache_hits': 0}

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def resolve_all(self, entry_module_name: str, source: str,
                    entry_dir: Optional[str] = None
                    ) -> Dict[str, ResolvedModule]:
        """从入口模块出发，递归解析所有导入的模块。

        缓存统计（stats.parsed / stats.cache_hits）跨调用累计，
        仅在构造或 clear_cache() 时清零。
        """
        visited: Set[str] = set()
        stack: List[str] = []
        self.modules.clear()
        try:
            self._resolve_recursive(entry_module_name, source, visited, stack, entry_dir)
        except CircularDependencyError:
            raise
        return self.modules

    def topological_order(self) -> List[str]:
        """返回模块拓扑排序结果（被依赖的在前）。"""
        order: List[str] = []
        visited: Set[str] = set()
        temp: List[str] = []  # 有序递归栈（用于保序检测循环）

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in temp:
                idx = temp.index(name)
                cycle = temp[idx:] + [name]
                raise CircularDependencyError(cycle)
            temp.append(name)
            if name in self.modules:
                for imp in self.modules[name].imports:
                    visit(imp)
            temp.pop()
            visited.add(name)
            order.append(name)

        # 先处理入口，再处理其余
        entry_candidates = list(self.modules.keys())
        for name in entry_candidates:
            visit(name)
        return order

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _resolve_recursive(self, module_name: str, source: Optional[str],
                           visited: Set[str], stack: List[str],
                           module_dir: Optional[str] = None,
                           module_path: Optional[Path] = None) -> None:
        if module_name in visited:
            return
        if module_name in stack:
            idx = stack.index(module_name)
            cycle = stack[idx:] + [module_name]
            raise CircularDependencyError(cycle)

        if source is None:
            # 子模块：优先使用文件级缓存（按 mtime/size 自动失效）
            loaded = self._load_resolved(module_path) if module_path else None
            if loaded is None:
                return
            source, ast_node, imports, exports = loaded
            default_path = module_path
        else:
            # 入口模块：source 由调用方提供，直接解析
            ast_node = self._parse_ast(source)
            imports = self._extract_imports(ast_node)
            exports = self._extract_exports(ast_node)
            default_path = self._find_module_path(module_name, module_dir)
            if default_path is None:
                # 入口可能只是内存中的源码（无对应文件），
                # 用入口目录作为逻辑路径，保证相对导入基准正确
                default_path = (Path(module_dir) / f"{module_name}.light") \
                    if module_dir else Path(f"{module_name}.light")

        # 记录已解析模块
        self.modules[module_name] = ResolvedModule(
            name=module_name,
            path=default_path,
            imports=list(imports),
            source=source,
            ast=ast_node,
            exports=exports,
        )
        # 注意：此时 *不* 将 module_name 加入 visited，
        # 否则循环依赖检测失效。依赖处理结束后再标记 visited。

        # 递归解析导入
        new_stack = stack + [module_name]
        current_dir = str(default_path.parent)
        for imp in imports:
            if imp in visited:
                continue
            if imp in new_stack:
                raise CircularDependencyError(new_stack + [imp])
            imp_path = self._find_module_path(imp, current_dir)
            if imp_path is None:
                # 找不到文件的模块，使用占位空模块（由 compiler 做警告）
                self.modules[imp] = ResolvedModule(
                    name=imp,
                    path=Path(f"{imp}.light"),
                    imports=[],
                    source="",
                    ast=None,
                    exports=[],
                )
                visited.add(imp)
                continue
            self._resolve_recursive(imp, None, visited, new_stack,
                                    str(imp_path.parent), imp_path)

        # 所有依赖处理完毕，再标记 visited
        visited.add(module_name)

    def _parse_ast(self, source: str) -> Any:
        """解析光明源码为 AST（解析失败时返回 None，由 compiler 报告错误）。"""
        try:
            from light_parser_v3 import LightParser  # type: ignore
            parser = LightParser()
            return parser.parse(source)
        except Exception:
            return None

    def _load_resolved(self, module_path: Path) -> Optional[Tuple[str, Any, List[str], List[str]]]:
        """带文件级缓存的模块加载。

        返回 (source, ast, imports, exports)；文件不存在或读取失败时返回 None。
        同一路径的模块在文件未变更时只解析一次，之后命中缓存。
        """
        if module_path is None:
            return None
        key = str(module_path.resolve())
        try:
            st = module_path.stat()
            mtime, size = st.st_mtime_ns, st.st_size
        except OSError:
            return None
        cached = self._cache.get(key)
        if cached is not None and cached['mtime'] == mtime and cached['size'] == size:
            self.stats['cache_hits'] += 1
            return (cached['source'], cached['ast'],
                    cached['imports'], cached['exports'])
        try:
            source = module_path.read_text(encoding="utf-8")
        except OSError:
            return None
        ast_node = self._parse_ast(source)
        imports = self._extract_imports(ast_node)
        exports = self._extract_exports(ast_node)
        self.stats['parsed'] += 1
        self._cache[key] = {
            'mtime': mtime,
            'size': size,
            'source': source,
            'ast': ast_node,
            'imports': imports,
            'exports': exports,
        }
        return (source, ast_node, imports, exports)

    def _extract_imports(self, ast_node: Any) -> List[str]:
        """从 AST 中提取所有导入的模块名（支持 导入 / 使用 两种语法）。"""
        imports: List[str] = []
        if ast_node is None:
            return imports
        statements = getattr(ast_node, "statements", None) or []
        for stmt in statements:
            type_name = type(stmt).__name__
            if type_name == "ImportStmt":
                # `导入 模块` 或 `从 模块 导入 符号`（含相对导入 .模块）
                mod_name = getattr(stmt, "module_name", None)
                if mod_name:
                    imports.append(mod_name)
            elif type_name == "UseStmt" or (hasattr(stmt, "module_name") and
                                              hasattr(stmt, "is_use")):
                # `使用 模块`（扩展形式）
                imports.append(stmt.module_name)
        return imports

    def _extract_exports(self, ast_node: Any) -> List[str]:
        """提取模块中可对外暴露的符号（段落/类 名）。

        - 若模块含显式 `导出 符号...` 语句，则只导出这些符号
        - 否则导出所有 `段 名(...)` 与 `类 名(...)`
        - 可选地支持公开的 / pub 标注前缀
        """
        names: List[str] = []
        if ast_node is None:
            return names
        statements = getattr(ast_node, "statements", None) or []

        explicit_exports: List[str] = []
        for stmt in statements:
            type_name = type(stmt).__name__
            if type_name == "ExportStmt":
                syms = getattr(stmt, "symbols", None) or []
                explicit_exports.extend(str(s) for s in syms)

        if explicit_exports:
            return list(dict.fromkeys(explicit_exports))

        # 隐式导出：收集所有段落与类定义
        for stmt in statements:
            type_name = type(stmt).__name__
            if type_name in ("Paragraph", "ParagraphDef", "FunctionDef",
                             "段定义"):
                name = getattr(stmt, "name", None)
                if name:
                    names.append(str(name))
            elif type_name in ("ClassDefinition", "ClassDef", "类定义"):
                name = getattr(stmt, "name", None)
                if name:
                    names.append(str(name))
        return list(dict.fromkeys(names))

    def _find_module_path(self, module_name: str,
                          base_dir: Optional[str] = None) -> Optional[Path]:
        """根据模块名在搜索路径中寻找 .light 文件。

        支持相对导入（`.模块` / `..模块`，基于 base_dir 解析）：
        - `.工具`  → base_dir/工具.light
        - `..工具` → base_dir 的上级目录/工具.light
        """
        if not module_name:
            return None
        # 相对导入：.模块 / ..模块（. 表示当前目录，.. 表示上级目录）
        if module_name.startswith('.'):
            if not base_dir:
                return None
            dots = len(module_name) - len(module_name.lstrip('.'))
            rel = module_name[dots:]
            base = Path(base_dir)
            for _ in range(dots - 1):
                base = base.parent
            if rel:
                for suffix in ('.light', '.py'):
                    cand = base / (rel + suffix)
                    if cand.is_file():
                        return cand
            else:
                # 纯点前缀（如 从 . 导入）：以 base_dir 自身为包目录，
                # 在其中查找与 base_dir 同名的模块文件
                for suffix in ('.light', '.py'):
                    cand = base / (base.name + suffix)
                    if cand.is_file():
                        return cand
            return None
        candidates = [
            f"{module_name}.light",
            module_name.replace(".", os.sep) + ".light",
            module_name.replace("/", os.sep) + ".light",
        ]
        dirs: List[Path] = []
        if base_dir:
            dirs.append(Path(base_dir))
        dirs.extend(self.search_paths)
        for base in dirs:
            if not base.exists():
                continue
            # seen 仅在当前目录内去重（module_name 无分隔符时三个候选相同）；
            # 若跨目录共用会导致第一个目录之后的搜索路径全部被跳过
            seen: Set[str] = set()
            for cand in candidates:
                if cand in seen:
                    continue
                seen.add(cand)
                path = base / cand
                if path.is_file():
                    return path
        return None


# =============================================================================
# 模块加载器
# =============================================================================

class ModuleLoader:
    """模块加载器"""
    
    def __init__(self, resolver: ModuleResolver = None):
        """
        初始化模块加载器
        
        Args:
            resolver: 模块解析器
        """
        self.resolver = resolver or ModuleResolver()
        self.loaded_modules: Dict[str, ModuleInfo] = {}
    
    def load(self, module_name: str, from_dir: str = None) -> ModuleInfo:
        """
        加载模块
        
        Args:
            module_name: 模块名
            from_dir: 从哪个目录查找
        
        Returns:
            模块信息
        """
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        # 查找模块
        module_path = self.resolver.find_module(module_name, from_dir)
        
        # 解析模块
        module_info = self.resolver.parse_module(module_path)
        
        # 加载依赖
        module_dir = str(module_path.parent)
        for dep_name in module_info.dependencies:
            if dep_name not in self.loaded_modules:
                self.load(dep_name, module_dir)
        
        # 标记为已加载
        self.loaded_modules[module_name] = module_info
        
        return module_info
    
    def load_project(self, main_file: str) -> List[ModuleInfo]:
        """
        加载整个项目
        
        Args:
            main_file: 主文件路径
        
        Returns:
            模块列表（按依赖顺序）
        """
        modules, graph = self.resolver.resolve(main_file)
        return modules


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    print("="*60)
    print("光明模块解析器测试")
    print("="*60)
    
    # 创建测试环境
    test_dir = Path("examples/modules")
    
    # 测试1: 查找模块
    print("\n测试1: 查找模块")
    print("-"*60)
    
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    try:
        module_path = resolver.find_module("math_utils")
        print(f"✓ 找到模块: {module_path}")
    except ModuleNotFoundError as e:
        print(f"✗ {e}")
    
    # 测试2: 解析模块
    print("\n测试2: 解析模块")
    print("-"*60)
    
    try:
        module_info = resolver.parse_module(module_path)
        print(f"✓ 模块名: {module_info.name}")
        print(f"  依赖: {module_info.dependencies}")
        print(f"  导出: {module_info.exports}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: 构建依赖图
    print("\n测试3: 构建依赖图")
    print("-"*60)
    
    main_file = test_dir / "main.light"
    
    if main_file.exists():
        try:
            graph = resolver.build_dependency_graph("main", str(test_dir))
            print(f"✓ 依赖图节点数: {len(graph.nodes)}")
            print("  模块列表:")
            for name, info in graph.nodes.items():
                print(f"    - {name} (依赖: {info.dependencies})")
        except Exception as e:
            print(f"✗ 构建失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 测试4: 检测循环依赖
    print("\n测试4: 检测循环依赖")
    print("-"*60)
    
    cycle = resolver.detect_circular_dependency(graph)
    if cycle:
        print(f"✗ 检测到循环依赖: {' → '.join(cycle)}")
    else:
        print("✓ 无循环依赖")
    
    # 测试5: 拓扑排序
    print("\n测试5: 拓扑排序")
    print("-"*60)
    
    try:
        order = resolver.topological_sort(graph)
        print(f"✓ 编译顺序: {' → '.join(order)}")
    except Exception as e:
        print(f"✗ 排序失败: {e}")
    
    # 测试6: 完整解析
    print("\n测试6: 完整解析")
    print("-"*60)
    
    if main_file.exists():
        try:
            modules, graph = resolver.resolve(str(main_file))
            print(f"✓ 解析成功，共 {len(modules)} 个模块")
            print("  编译顺序:")
            for i, module in enumerate(modules, 1):
                print(f"    {i}. {module.name} ({module.path.name})")
        except Exception as e:
            print(f"✗ 解析失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
