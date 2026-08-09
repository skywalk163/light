# -*- coding: utf-8 -*-
"""
第9周 增量编译器测试

测试增量编译器的依赖图跟踪、缓存机制、增量编译大型项目等功能。
"""

import sys
import os
import tempfile
import time
import pytest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


# ============================================================================
# 依赖图测试
# ============================================================================

class TestDependencyGraph:
    """测试依赖图跟踪器"""

    def test_import(self):
        """测试导入"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph
        assert DependencyGraph is not None

    def test_add_module(self):
        """测试添加模块"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('main', '/path/main.light', ['utils', 'io'])
        graph.add_module('utils', '/path/utils.light', [])
        graph.add_module('io', '/path/io.light', [])

        assert graph.get_dependencies('main') == ['utils', 'io']
        assert graph.get_dependencies('utils') == []

    def test_get_dependents(self):
        """测试获取反向依赖"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('main', '/path/main.light', ['utils', 'io'])
        graph.add_module('app', '/path/app.light', ['utils'])
        graph.add_module('utils', '/path/utils.light', [])

        dependents = graph.get_dependents('utils')
        assert 'main' in dependents
        assert 'app' in dependents
        assert len(dependents) == 2

    def test_cascade_affected(self):
        """测试级联影响"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        # A -> B -> C
        graph.add_module('A', '/path/a.light', ['B'])
        graph.add_module('B', '/path/b.light', ['C'])
        graph.add_module('C', '/path/c.light', [])

        # C 变更，A 和 B 都应该受影响
        affected = graph.get_cascade_affected('C')
        assert 'C' in affected
        assert 'B' in affected
        assert 'A' in affected
        assert len(affected) == 3

        # A 变更，只有 A 受影响
        affected = graph.get_cascade_affected('A')
        assert 'A' in affected
        assert len(affected) == 1

    def test_cycle_detection(self):
        """测试循环依赖检测"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('A', '/path/a.light', ['B'])
        graph.add_module('B', '/path/b.light', ['C'])
        graph.add_module('C', '/path/c.light', ['A'])  # 循环

        assert graph.has_cycle() is True

        # 无循环
        graph2 = DependencyGraph()
        graph2.add_module('A', '/path/a.light', ['B'])
        graph2.add_module('B', '/path/b.light', [])
        assert graph2.has_cycle() is False

    def test_topological_sort(self):
        """测试拓扑排序"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('A', '/path/a.light', ['B', 'C'])
        graph.add_module('B', '/path/b.light', ['C'])
        graph.add_module('C', '/path/c.light', [])

        # 拓扑排序：依赖者在前（A 依赖 B 和 C，B 依赖 C）
        sorted_mods = graph.topological_sort()
        # A 依赖 B 和 C，所以 A 在 B 和 C 之前
        assert sorted_mods.index('A') < sorted_mods.index('C')
        assert sorted_mods.index('A') < sorted_mods.index('B')

    def test_module_path_mapping(self):
        """测试模块路径映射"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('main', '/path/main.light', [])

        assert graph.get_module_path('main') == '/path/main.light'
        assert graph.get_module_name('/path/main.light') == 'main'
        assert graph.get_module_path('nonexistent') is None

    def test_get_stats(self):
        """测试获取统计信息"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('A', '/path/a.light', ['B'])
        graph.add_module('B', '/path/b.light', [])

        stats = graph.get_stats()
        assert stats['total_modules'] == 2
        assert stats['total_dependencies'] == 1
        assert stats['has_cycle'] is False

    def test_clear(self):
        """测试清空依赖图"""
        try:
            from incremental_compiler import DependencyGraph
        except ImportError:
            from src.incremental_compiler import DependencyGraph

        graph = DependencyGraph()
        graph.add_module('A', '/path/a.light', [])
        assert graph.get_all_modules() == ['A']
        graph.clear()
        assert graph.get_all_modules() == []


# ============================================================================
# 增量编译器测试
# ============================================================================

class TestIncrementalCompiler:
    """测试增量编译器"""

    @pytest.fixture
    def compiler(self):
        """创建增量编译器实例"""
        try:
            from incremental_compiler import IncrementalCompiler
        except ImportError:
            from src.incremental_compiler import IncrementalCompiler
        return IncrementalCompiler()

    def test_import(self):
        """测试导入"""
        try:
            from incremental_compiler import IncrementalCompiler
        except ImportError:
            from src.incremental_compiler import IncrementalCompiler
        assert IncrementalCompiler is not None

    def test_compiler_creation(self, compiler):
        """测试编译器创建"""
        assert compiler is not None
        assert compiler.cache is not None
        assert compiler.dep_graph is not None

    def test_compile_nonexistent_file(self, compiler):
        """测试编译不存在的文件"""
        result = compiler.compile('/nonexistent/file.light')
        assert result['success'] is False
        assert 'error' in result
        assert '不存在' in result['error']

    @pytest.fixture
    def temp_light_file(self, tmp_path):
        """创建临时 .light 文件"""
        source_file = tmp_path / "test.light"
        source_file.write_text('打印 "hello"。', encoding='utf-8')
        return str(source_file)

    def test_compile_file(self, compiler, temp_light_file):
        """测试编译文件"""
        result = compiler.compile(temp_light_file, force=True)
        # 可能编译失败（因为缺少 clang 等），但接口应该返回正确结构
        assert 'success' in result
        assert 'file_path' in result
        assert 'cached' in result
        assert result['file_path'] == os.path.abspath(temp_light_file)

    def test_mark_dirty(self, compiler, temp_light_file):
        """测试标记脏文件"""
        compiler.mark_dirty(temp_light_file)
        assert os.path.abspath(temp_light_file) in compiler._dirty_files

    def test_parse_imports(self, compiler):
        """测试解析导入语句"""
        source = '''
导入 "utils"
import "io"
从 "math" 导入 sin
from "os" import path
设 x 为 1。
'''
        imports = compiler._parse_imports(source)
        assert 'utils' in imports
        assert 'io' in imports
        assert 'math' in imports
        assert 'os' in imports
        assert len(imports) == 4

    def test_find_light_files(self, compiler, tmp_path):
        """测试查找 .light 文件"""
        # 创建一些 .light 文件
        (tmp_path / "a.light").write_text("test", encoding='utf-8')
        (tmp_path / "b.light").write_text("test", encoding='utf-8')
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.light").write_text("test", encoding='utf-8')

        files = compiler._find_light_files(str(tmp_path))
        assert len(files) == 3
        assert all(f.endswith('.light') for f in files)

    def test_get_compile_stats(self, compiler):
        """测试获取编译统计信息"""
        stats = compiler.get_compile_stats()
        assert 'compiled_modules' in stats
        assert 'dirty_files' in stats
        assert 'file_dependencies' in stats
        assert 'dep_graph_stats' in stats
        assert 'cache_stats' in stats

    def test_compile_project_nonexistent(self, compiler):
        """测试编译不存在的项目"""
        result = compiler.compile_project('/nonexistent/path')
        assert result['success'] is False
        assert 'error' in result

    def test_dep_graph_builder(self, compiler, tmp_path):
        """测试依赖图构建"""
        # 创建模块文件
        utils = tmp_path / "utils.light"
        utils.write_text('''光明工具模块
设 版本 为 1。
''', encoding='utf-8')

        main = tmp_path / "main.light"
        main.write_text('''导入 "utils"
设 x 为 1。
''', encoding='utf-8')

        # 构建依赖图
        light_files = [str(main), str(utils)]
        compiler._build_dependency_graph(light_files)

        # 验证依赖关系
        assert compiler.dep_graph.get_module_name(str(main)) == 'main'
        assert compiler.dep_graph.get_module_name(str(utils)) == 'utils'
        deps = compiler.dep_graph.get_dependencies('main')
        assert 'utils' in deps


if __name__ == '__main__':
    pytest.main([__file__, '-v'])