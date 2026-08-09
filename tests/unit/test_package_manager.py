# -*- coding: utf-8 -*-
"""
光明包管理器单元测试

测试 PackageManager 核心功能：项目初始化、配置加载、模块查找、TomlParser 解析。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from package_manager import (
    PackageManager, PackageConfig, Package,
    TomlParser,
)


class TestTomlParser(unittest.TestCase):
    """TOML 解析器测试"""

    def setUp(self):
        self.parser = TomlParser()

    def test_parse_empty(self):
        result = self.parser.parse("")
        self.assertEqual(result, {})

    def test_parse_comments(self):
        content = "# 这是注释\n; 分号注释\nkey = \"值\""
        result = self.parser.parse(content)
        self.assertEqual(result.get('key'), '值')

    def test_parse_section(self):
        content = "[package]\nname = \"测试\""
        result = self.parser.parse(content)
        self.assertIn('package', result)
        self.assertEqual(result['package']['name'], '测试')

    def test_parse_string(self):
        result = self.parser.parse('key = "你好"')
        self.assertEqual(result['key'], '你好')

    def test_parse_integer(self):
        result = self.parser.parse('key = 42')
        self.assertEqual(result['key'], 42)

    def test_parse_float(self):
        result = self.parser.parse('key = 3.14')
        self.assertEqual(result['key'], 3.14)

    def test_parse_boolean_true(self):
        for val in ['true', 'True', 'TRUE', 'yes', '是', '真']:
            result = self.parser.parse(f'key = {val}')
            self.assertTrue(result['key'], f"失败于: {val}")

    def test_parse_boolean_false(self):
        for val in ['false', 'False', 'FALSE', 'no', '否', '假']:
            result = self.parser.parse(f'key = {val}')
            self.assertFalse(result['key'], f"失败于: {val}")

    def test_parse_array(self):
        result = self.parser.parse('key = ["甲", "乙", "丙"]')
        self.assertEqual(result['key'], ['甲', '乙', '丙'])

    def test_parse_inline_table(self):
        result = self.parser.parse('key = { version = "1.0", path = "../lib" }')
        self.assertIsInstance(result['key'], dict)
        self.assertEqual(result['key']['version'], '1.0')
        self.assertEqual(result['key']['path'], '../lib')

    def test_parse_full_config(self):
        content = '''# 光明项目配置
[package]
name = "测试项目"
version = "1.2.3"
entry = "主.light"
authors = ["张三", "李四"]
description = "测试用"

[dependencies]
utils = "0.1.0"
mylib = { version = "0.2.0", path = "../mylib" }
'''
        result = self.parser.parse(content)
        self.assertEqual(result['package']['name'], '测试项目')
        self.assertEqual(result['package']['version'], '1.2.3')
        self.assertEqual(result['package']['authors'], ['张三', '李四'])
        self.assertEqual(result['dependencies']['utils'], '0.1.0')
        self.assertIsInstance(result['dependencies']['mylib'], dict)
        self.assertEqual(result['dependencies']['mylib']['path'], '../mylib')


class TestPackageConfig(unittest.TestCase):
    """包配置数据模型测试"""

    def test_default_config(self):
        cfg = PackageConfig()
        self.assertEqual(cfg.name, '未命名')
        self.assertEqual(cfg.version, '0.1.0')
        self.assertEqual(cfg.entry, '主.light')
        self.assertEqual(cfg.dependencies, {})
        self.assertEqual(cfg.authors, [])

    def test_to_dict(self):
        cfg = PackageConfig(
            name='测试',
            version='2.0.0',
            entry='main.light',
            dependencies={'utils': '1.0'},
            authors=['作者'],
            description='描述'
        )
        d = cfg.to_dict()
        self.assertEqual(d['name'], '测试')
        self.assertEqual(d['version'], '2.0.0')
        self.assertEqual(d['entry'], 'main.light')
        self.assertEqual(d['dependencies'], {'utils': '1.0'})
        self.assertEqual(d['authors'], ['作者'])
        self.assertEqual(d['description'], '描述')


class TestPackageManagerInit(unittest.TestCase):
    """PackageManager 初始化测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_pkg_test_')
        self.pm = PackageManager(project_root=Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_project_creates_files(self):
        self.assertTrue(self.pm.init_project(name='测试包'))
        toml_path = Path(self.tmpdir) / 'package.toml'
        main_path = Path(self.tmpdir) / '主.light'
        self.assertTrue(toml_path.exists(), 'package.toml 应被创建')
        self.assertTrue(main_path.exists(), '主.light 应被创建')

    def test_init_project_idempotent(self):
        self.assertTrue(self.pm.init_project(name='包甲'))
        # 再次初始化应视为幂等成功
        self.assertTrue(self.pm.init_project(name='包甲'))

    def test_init_project_config_loaded(self):
        self.pm.init_project(name='我的包')
        self.assertIsNotNone(self.pm.config)
        self.assertEqual(self.pm.config.name, '我的包')
        self.assertEqual(self.pm.config.entry, '主.light')

    def test_init_project_default_name(self):
        # 不传 name，使用目录名
        self.pm.init_project()
        self.assertIsNotNone(self.pm.config)
        # 目录名是 tempfile 给的，非空即可
        self.assertTrue(self.pm.config.name)

    def test_init_project_main_source_v3_syntax(self):
        self.pm.init_project(name='测试')
        main_path = Path(self.tmpdir) / '主.light'
        content = main_path.read_text(encoding='utf-8')
        # v3.2 语法：段落 名称 接收：
        self.assertIn('段落', content)
        self.assertIn('接收', content)


class TestPackageManagerLoadConfig(unittest.TestCase):
    """PackageManager 配置加载测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_pkg_load_')
        self.pm = PackageManager(project_root=Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_config_no_file(self):
        result = self.pm.load_config()
        self.assertIsNone(result)
        self.assertIsNone(self.pm.config)

    def test_load_config_valid(self):
        toml_content = '''[package]
name = "加载测试"
version = "0.5.0"
entry = "main.light"
authors = ["作者甲"]

[dependencies]
lib1 = "1.0.0"
lib2 = { version = "2.0", path = "../lib2" }
'''
        (Path(self.tmpdir) / 'package.toml').write_text(toml_content, encoding='utf-8')
        cfg = self.pm.load_config()
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.name, '加载测试')
        self.assertEqual(cfg.version, '0.5.0')
        self.assertEqual(cfg.entry, 'main.light')
        self.assertEqual(cfg.authors, ['作者甲'])
        self.assertEqual(cfg.dependencies['lib1'], '1.0.0')
        self.assertEqual(cfg.dependencies['lib2'], '2.0')

    def test_load_config_authors_as_string(self):
        # authors 为单字符串时应转为单元素列表
        toml_content = '''[package]
name = "测试"
authors = "单一作者"
'''
        (Path(self.tmpdir) / 'package.toml').write_text(toml_content, encoding='utf-8')
        cfg = self.pm.load_config()
        self.assertEqual(cfg.authors, ['单一作者'])

    def test_load_config_defaults(self):
        # 仅 name，其余使用默认值
        toml_content = '[package]\nname = "最小配置"\n'
        (Path(self.tmpdir) / 'package.toml').write_text(toml_content, encoding='utf-8')
        cfg = self.pm.load_config()
        self.assertEqual(cfg.name, '最小配置')
        self.assertEqual(cfg.version, '0.1.0')
        self.assertEqual(cfg.entry, '主.light')
        self.assertEqual(cfg.dependencies, {})

    def test_load_config_search_paths_updated(self):
        self.pm.init_project(name='测试')
        self.pm.load_config()
        self.assertEqual(self.pm.search_paths[0], Path(self.tmpdir))


class TestPackageManagerFindModule(unittest.TestCase):
    """PackageManager 模块查找测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_pkg_find_')
        self.pm = PackageManager(project_root=Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_find_module_empty_name(self):
        self.assertIsNone(self.pm.find_module(''))

    def test_find_module_simple(self):
        # 创建 数学.light
        (Path(self.tmpdir) / '数学.light').write_text('# 数学模块', encoding='utf-8')
        result = self.pm.find_module('数学')
        self.assertIsNotNone(result)
        self.assertEqual(result.name, '数学.light')

    def test_find_module_dotted(self):
        # 创建 数学/工具.light
        sub = Path(self.tmpdir) / '数学'
        sub.mkdir()
        (sub / '工具.light').write_text('# 工具', encoding='utf-8')
        result = self.pm.find_module('数学.工具')
        self.assertIsNotNone(result)
        self.assertTrue(result.name.endswith('工具.light'))

    def test_find_module_slash(self):
        sub = Path(self.tmpdir) / '工具集'
        sub.mkdir()
        (sub / '辅助.light').write_text('# 辅助', encoding='utf-8')
        result = self.pm.find_module('工具集/辅助')
        self.assertIsNotNone(result)

    def test_find_module_not_found(self):
        result = self.pm.find_module('不存在的模块')
        self.assertIsNone(result)


class TestPackageManagerPathDeps(unittest.TestCase):
    """PackageManager path 依赖解析测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_pkg_deps_')
        self.pm = PackageManager(project_root=Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_resolve_path_dependencies_no_config(self):
        # 没有 package.toml 时返回空字典
        result = self.pm.resolve_path_dependencies()
        self.assertEqual(result, {})

    def test_resolve_path_dependencies_valid(self):
        # 创建依赖目录
        dep_dir = Path(self.tmpdir).parent / 'dep_lib'
        dep_dir.mkdir(exist_ok=True)
        try:
            toml_content = f'''[package]
name = "依赖测试"

[dependencies]
mylib = {{ version = "1.0", path = "{dep_dir}" }}
'''
            (Path(self.tmpdir) / 'package.toml').write_text(toml_content, encoding='utf-8')
            self.pm.load_config()
            result = self.pm.resolve_path_dependencies()
            self.assertIn('mylib', result)
            self.assertTrue(result['mylib'].exists())
            # 应被添加到搜索路径
            self.assertIn(result['mylib'], self.pm.search_paths)
        finally:
            import shutil
            shutil.rmtree(dep_dir, ignore_errors=True)

    def test_resolve_path_dependencies_relative(self):
        # 相对路径依赖
        rel_dep = Path(self.tmpdir) / 'lib' / 'relmod'
        rel_dep.mkdir(parents=True, exist_ok=True)
        toml_content = '''[dependencies]
relmod = { path = "./lib/relmod" }
'''
        (Path(self.tmpdir) / 'package.toml').write_text(toml_content, encoding='utf-8')
        self.pm.load_config()
        result = self.pm.resolve_path_dependencies()
        self.assertIn('relmod', result)


class TestPackageManagerBuildRun(unittest.TestCase):
    """PackageManager 构建与运行测试（端到端）"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='light_pkg_build_')
        self.pm = PackageManager(project_root=Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_project_no_config(self):
        result = self.pm.build_project()
        self.assertFalse(result['success'])
        self.assertIn('package.toml', ''.join(result.get('errors', [])))

    def test_build_project_success(self):
        self.pm.init_project(name='构建测试')
        result = self.pm.build_project()
        self.assertTrue(result['success'], f"构建失败: {result.get('errors')}")
        self.assertEqual(result['entry'], '主.light')
        self.assertIn('主', result.get('order', []))

    def test_build_project_missing_entry(self):
        # 创建 package.toml 但删除入口文件
        self.pm.init_project(name='测试')
        (Path(self.tmpdir) / '主.light').unlink()
        result = self.pm.build_project()
        self.assertFalse(result['success'])
        self.assertTrue(any('入口文件不存在' in e for e in result.get('errors', [])))

    def test_run_project_success(self):
        self.pm.init_project(name='运行测试')
        ret = self.pm.run_project()
        self.assertEqual(ret, 0, "运行应成功返回 0")


class TestPackageDataModel(unittest.TestCase):
    """Package 数据模型测试"""

    def test_package_creation(self):
        cfg = PackageConfig(name='测试')
        pkg = Package(config=cfg, root_path=Path('/tmp/test'))
        self.assertEqual(pkg.config.name, '测试')
        self.assertEqual(pkg.modules, {})

    def test_package_with_modules(self):
        cfg = PackageConfig(name='带模块')
        pkg = Package(config=cfg, root_path=Path('.'), modules={'甲': object(), '乙': object()})
        self.assertEqual(len(pkg.modules), 2)
        self.assertIn('甲', pkg.modules)
        self.assertIn('乙', pkg.modules)


if __name__ == '__main__':
    unittest.main()
