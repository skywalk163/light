"""
光明 - 第4周模块系统与包管理器完善测试

测试以下功能：
1. 循环依赖检测增强
2. SemVer 语义化版本解析与比较
3. 包发布流程
4. 依赖解析器
5. 标准库自动加载
6. 缓存管理
"""
import sys
import os
import unittest

# 添加 src 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# =============================================================================
# 循环依赖检测测试
# =============================================================================

class TestCircularDependency(unittest.TestCase):
    """循环依赖检测测试"""

    def setUp(self):
        from module_resolver import ModuleResolver, DependencyGraph, ModuleInfo
        self.resolver = ModuleResolver(auto_load_stdlib=False)
        self.ModuleInfo = ModuleInfo
        self.DependencyGraph = DependencyGraph

    def _make_graph_with_cycle(self):
        """构建一个包含循环依赖的图: A -> B -> C -> A"""
        graph = self.DependencyGraph()
        a = self.ModuleInfo(name='A', path='', imports=[], dependencies={'B'})
        b = self.ModuleInfo(name='B', path='', imports=[], dependencies={'C'})
        c = self.ModuleInfo(name='C', path='', imports=[], dependencies={'A'})
        graph.add_module(a)
        graph.add_module(b)
        graph.add_module(c)
        graph.add_dependency('A', 'B')
        graph.add_dependency('B', 'C')
        graph.add_dependency('C', 'A')
        return graph

    def _make_graph_without_cycle(self):
        """构建无循环依赖的图: A -> B -> C"""
        graph = self.DependencyGraph()
        a = self.ModuleInfo(name='A', path='', imports=[], dependencies={'B'})
        b = self.ModuleInfo(name='B', path='', imports=[], dependencies={'C'})
        c = self.ModuleInfo(name='C', path='', imports=[], dependencies=set())
        graph.add_module(a)
        graph.add_module(b)
        graph.add_module(c)
        graph.add_dependency('A', 'B')
        graph.add_dependency('B', 'C')
        return graph

    def test_detect_single_cycle(self):
        """检测单个循环依赖"""
        graph = self._make_graph_with_cycle()
        cycle = self.resolver.detect_circular_dependency(graph)
        self.assertIsNotNone(cycle)
        self.assertIn('A', cycle)
        self.assertIn('B', cycle)
        self.assertIn('C', cycle)

    def test_detect_no_cycle(self):
        """无循环依赖时返回 None"""
        graph = self._make_graph_without_cycle()
        cycle = self.resolver.detect_circular_dependency(graph)
        self.assertIsNone(cycle)

    def test_detect_all_cycles(self):
        """检测所有循环依赖"""
        # 构建两个环: A->B->A 和 C->D->E->C
        graph = self.DependencyGraph()
        modules_data = [
            ('A', {'B'}), ('B', {'A'}),
            ('C', {'D'}), ('D', {'E'}), ('E', {'C'}),
            ('F', set()),
        ]
        for name, deps in modules_data:
            info = self.ModuleInfo(name=name, path='', imports=[], dependencies=deps)
            graph.add_module(info)
            for dep in deps:
                graph.add_dependency(name, dep)

        cycles = self.resolver.detect_all_cycles(graph)
        self.assertEqual(len(cycles), 2)

    def test_circular_dependency_error_message(self):
        """循环依赖错误信息包含修复建议"""
        from module_resolver import CircularDependencyError
        err = CircularDependencyError(['A', 'B', 'C', 'A'])
        msg = str(err)
        self.assertIn('修复建议', msg)
        self.assertIn('检查模块间的导入关系', msg)
        self.assertIn('A', msg)
        self.assertIn('B', msg)

    def test_topological_sort_valid(self):
        """拓扑排序正确处理无环图"""
        graph = self._make_graph_without_cycle()
        order = self.resolver.topological_sort(graph)
        # C 应该在 B 之前，B 应该在 A 之前
        self.assertGreater(order.index('B'), order.index('C'))
        self.assertGreater(order.index('A'), order.index('B'))

    def test_topological_sort_with_cycle(self):
        """拓扑排序在有环图时抛出异常"""
        from module_resolver import CircularDependencyError
        graph = self._make_graph_with_cycle()
        with self.assertRaises(CircularDependencyError):
            self.resolver.topological_sort(graph)


# =============================================================================
# 语义化版本测试
# =============================================================================

class TestSemVer(unittest.TestCase):
    """语义化版本测试"""

    def test_parse_valid(self):
        """解析有效的版本号"""
        from lightpkg import SemVer
        v = SemVer.parse('1.2.3')
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 3)

    def test_parse_with_pre_release(self):
        """解析带预发布标签的版本号"""
        from lightpkg import SemVer
        v = SemVer.parse('2.0.0-alpha')
        self.assertEqual(v.major, 2)
        self.assertEqual(v.pre_release, 'alpha')

    def test_parse_with_build(self):
        """解析带构建元数据的版本号"""
        from lightpkg import SemVer
        v = SemVer.parse('1.0.0+build.123')
        self.assertEqual(v.build, 'build.123')

    def test_parse_invalid(self):
        """解析无效的版本号应抛出异常"""
        from lightpkg import SemVer
        with self.assertRaises(ValueError):
            SemVer.parse('not-a-version')
        with self.assertRaises(ValueError):
            SemVer.parse('1.2')
        with self.assertRaises(ValueError):
            SemVer.parse('1.2.3.4')

    def test_compare_less(self):
        """版本比较（小于）"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.parse('1.0.0') < SemVer.parse('2.0.0'))
        self.assertTrue(SemVer.parse('1.0.0') < SemVer.parse('1.1.0'))
        self.assertTrue(SemVer.parse('1.0.0') < SemVer.parse('1.0.1'))
        self.assertTrue(SemVer.parse('1.0.0-alpha') < SemVer.parse('1.0.0'))

    def test_compare_equal(self):
        """版本比较（等于）"""
        from lightpkg import SemVer
        self.assertEqual(SemVer.parse('1.0.0'), SemVer.parse('1.0.0'))
        self.assertEqual(SemVer.parse('2.0.0-alpha'), SemVer.parse('2.0.0-alpha'))

    def test_compare_greater(self):
        """版本比较（大于）"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.parse('2.0.0') > SemVer.parse('1.0.0'))
        self.assertTrue(SemVer.parse('1.0.0') > SemVer.parse('1.0.0-alpha'))

    def test_satisfied_by_exact(self):
        """精确版本约束"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.satisfied_by('1.0.0', '1.0.0'))
        self.assertFalse(SemVer.satisfied_by('1.0.0', '1.0.1'))

    def test_satisfied_by_range(self):
        """范围版本约束"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.satisfied_by('>=1.0.0,<2.0.0', '1.5.0'))
        self.assertFalse(SemVer.satisfied_by('>=1.0.0,<2.0.0', '2.0.0'))
        self.assertTrue(SemVer.satisfied_by('>=1.0.0,<2.0.0', '1.0.0'))

    def test_satisfied_by_caret(self):
        """^ 约束"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.satisfied_by('^1.2.3', '1.5.0'))
        self.assertFalse(SemVer.satisfied_by('^1.2.3', '2.0.0'))

    def test_satisfied_by_tilde(self):
        """~ 约束"""
        from lightpkg import SemVer
        self.assertTrue(SemVer.satisfied_by('~1.2.3', '1.2.5'))
        self.assertFalse(SemVer.satisfied_by('~1.2.3', '1.3.0'))

    def test_str(self):
        """版本号转字符串"""
        from lightpkg import SemVer
        self.assertEqual(str(SemVer.parse('1.2.3')), '1.2.3')
        self.assertEqual(str(SemVer.parse('2.0.0-alpha')), '2.0.0-alpha')
        self.assertEqual(str(SemVer.parse('1.0.0+build.1')), '1.0.0+build.1')


# =============================================================================
# 依赖解析器测试
# =============================================================================

class TestDependencyResolver(unittest.TestCase):
    """依赖解析器测试"""

    def setUp(self):
        from lightpkg import DependencyResolver
        self.resolver = DependencyResolver()

    def test_resolve_simple(self):
        """解析简单依赖"""
        result = self.resolver.resolve('non_existent_pkg')
        self.assertIn('non_existent_pkg', result)

    def test_check_conflict_empty(self):
        """空依赖无冲突"""
        conflicts = self.resolver.check_conflict({})
        self.assertEqual(len(conflicts), 0)


# =============================================================================
# 标准库自动加载测试
# =============================================================================

class TestStdlibAutoLoad(unittest.TestCase):
    """标准库自动加载测试"""

    def test_stdlib_discovery(self):
        """标准库模块自动发现"""
        from module_resolver import ModuleResolver
        resolver = ModuleResolver(auto_load_stdlib=True)
        names = resolver.get_stdlib_module_names()
        # 至少应该有一些标准库模块
        self.assertGreater(len(names), 0)
        # 数学模块应该存在
        self.assertIn('数学', names)

    def test_stdlib_module_load(self):
        """加载标准库模块"""
        from module_resolver import ModuleResolver
        resolver = ModuleResolver(auto_load_stdlib=True)
        module = resolver.load_stdlib_module('数学')
        self.assertIsNotNone(module)
        self.assertEqual(module.name, '数学')

    def test_preload_builtins(self):
        """预加载内置模块"""
        from module_resolver import ModuleResolver
        resolver = ModuleResolver(auto_load_stdlib=True)
        resolver.preload_builtins()
        self.assertIn('builtins', resolver.module_cache)

    def test_find_stdlib_module(self):
        """查找标准库模块文件"""
        from module_resolver import ModuleResolver
        resolver = ModuleResolver(auto_load_stdlib=True)
        path = resolver.find_module('数学')
        self.assertTrue(path.exists())
        self.assertIn('数学', str(path))


# =============================================================================
# 包发布流程测试
# =============================================================================

class TestPackagePublishFlow(unittest.TestCase):
    """包发布流程测试"""

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_package(self):
        """测试包初始化"""
        from lightpkg import cmd_init

        class Args:
            name = 'test-pkg'
            dir = self.temp_dir

        result = cmd_init(Args())
        self.assertEqual(result, 0)

        # 验证 light.json 存在
        pkg_json = os.path.join(self.temp_dir, 'light.json')
        self.assertTrue(os.path.exists(pkg_json))

        # 验证 main.light 存在
        main_light = os.path.join(self.temp_dir, 'main.light')
        self.assertTrue(os.path.exists(main_light))

    def test_publish_validation(self):
        """发布前版本验证"""
        from lightpkg import SemVer
        # 有效版本
        SemVer.parse('1.0.0')
        SemVer.parse('2.3.4-beta')
        # 无效版本
        with self.assertRaises(ValueError):
            SemVer.parse('invalid')


# =============================================================================
# 缓存管理测试
# =============================================================================

class TestCacheManagement(unittest.TestCase):
    """缓存管理测试"""

    def test_cache_clean(self):
        """清理缓存（空缓存）"""
        from lightpkg import _cache_clean, _cache_clear, _cache_status
        # 先清空
        _cache_clear()
        # 清理过期的（空缓存）
        count = _cache_clean()
        self.assertEqual(count, 0)

    def test_cache_status(self):
        """缓存状态查询"""
        from lightpkg import _cache_status
        status = _cache_status()
        self.assertIn('total_entries', status)
        self.assertIn('cache_dir', status)
        self.assertIn('ttl_seconds', status)


if __name__ == '__main__':
    unittest.main(verbosity=2)