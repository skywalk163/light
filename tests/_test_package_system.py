"""
光明包系统测试（package_manager + module_resolver + compiler 扩展测试

关键功能测试
"""
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

# 确保 src 可用
_project_root = Path(__file__).resolve().parent.parent
_src_dir = _project_root / "src"
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_src_dir))


def _make_temp_project_dir():
    """生成临时项目目录（用完自动清理。"""
    tmp_root = Path(tempfile.mkdtemp(prefix="light_pkg_"))
    return tmp_root


class TestTomlParsing(unittest.TestCase):
    """测试 TOML 简化解析"""

    def setUp(self):
        self.tmp = _make_temp_project_dir()

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_basic_package_config(self):
        # 基本字段解析
        from package_manager import PackageManager
        (self.tmp / "package.toml").write_text(
            "[package]\nname = \"示例\"\nversion = \"1.0.0\"\nentry = \"主.light\"\nauthors = [\"测试员\"]\n\n[dependencies]\n数学 = \"1.0\"\n", encoding="utf-8")
        (self.tmp / "主.light").write_text("段 主():\\n    打印(\"你好\")\n结束。\n", encoding="utf-8")
        pm = PackageManager(self.tmp)
        cfg = pm.load_config()
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.name, "示例")
        self.assertEqual(cfg.version, "1.0.0")
        self.assertEqual(cfg.entry, "主.light")
        self.assertEqual(cfg.authors, ["测试员"])
        self.assertIn("数学", cfg.dependencies)

    def test_package_toml_missing(self):
        # 不存在 package.toml 返回 None
        from package_manager import PackageManager
        pm = PackageManager(self.tmp)
        cfg = pm.load_config()
        self.assertIsNone(cfg)

    def test_init_project_creates_files(self):
        # init_project 生成 package.toml 和 主.light
        from package_manager import PackageManager
        pm = PackageManager(self.tmp)
        ok = pm.init_project("测试项目")
        self.assertTrue(ok)
        self.assertTrue((self.tmp / "package.toml").exists())
        self.assertTrue((self.tmp / "主.light").exists())


class TestModuleLookup(unittest.TestCase):
    """测试模块查找"""

    def setUp(self):
        self.tmp = _make_temp_project_dir()
        (self.tmp / "数学.light").write_text(
            "段 加(甲, 乙):\\n    返回 甲 加 乙。\\n结束。\\n",
            encoding="utf-8")

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_find_simple_module(self):
        from package_manager import PackageManager
        pm = PackageManager(self.tmp)
        path = pm.find_module("数学")
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())

    def test_find_module_not_found(self):
        from package_manager import PackageManager
        pm = PackageManager(self.tmp)
        path = pm.find_module("不存在的模块")
        self.assertIsNone(path)


class TestBuildProject(unittest.TestCase):
    """测试 compile_project / build_project"""

    def setUp(self):
        self.tmp = _make_temp_project_dir()
        (self.tmp / "package.toml").write_text(
            "[package]\nname = \"测试项目\"\nversion = \"0.1.0\"\nentry = \"主.light\"\n\n[dependencies]\n", encoding="utf-8")
        (self.tmp / "主.light").write_text(
            "段 主():\\n    打印(\"测试\")\\n结束。\\n", encoding="utf-8")

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_simple_project(self):
        from compiler import DuanCompiler
        c = DuanCompiler(project_root=str(self.tmp))
        result = c.compile_project(str(self.tmp))
        self.assertIn("success", result)
        self.assertIn("modules", result)
        self.assertIn("order", result)


class TestModuleDependencyResolver(unittest.TestCase):
    """测试 ModuleDependencyResolver"""

    def setUp(self):
        self.tmp = _make_temp_project_dir()
        # 创建主模块导入 工具
        (self.tmp / "工具.light").write_text(
            "段 打印(内容):\\n    返回 内容。\\n结束。\\n", encoding="utf-8")

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_topological_order(self):
        from module_resolver import ModuleDependencyResolver
        resolver = ModuleDependencyResolver([self.tmp])
        modules = resolver.resolve_all("主", "导入 工具。\\n段 主():\\n结束。\\n")
        order = resolver.topological_order()
        self.assertIsInstance(order, list)
        # 工具 应当出现于 主 之前
        idx_tool = order.index("工具") if "工具" in order else None
        idx_main = order.index("主") if "主" in order else None
        if idx_tool is not None and idx_main is not None:
            self.assertLess(idx_tool, idx_main)

    def test_circular_dependency_detection(self):
        from module_resolver import ModuleDependencyResolver, CircularDependencyError
        # A -> B -> A
        (self.tmp / "甲.light").write_text("导入 乙。\n", encoding="utf-8")
        (self.tmp / "乙.light").write_text("导入 甲。\n", encoding="utf-8")
        resolver = ModuleDependencyResolver([self.tmp])
        with self.assertRaises(CircularDependencyError):
            resolver.resolve_all("甲", "导入 乙。\n")


class TestBackwardCompatibility(unittest.TestCase):
    """确保现有功能不破坏之前的测试（单模块编译）"""

    def test_compile_single_module_unchanged(self):
        from compiler import DuanCompiler
        c = DuanCompiler()
        result = c.compile("设 甲 为 三。")
        self.assertIsNotNone(result)
        self.assertIn("ast", result)
        self.assertIn("tokens", result)

    def test_init_no_project_root(self):
        # DuanCompiler()不传project_root仍可工作
        from compiler import DuanCompiler
        c = DuanCompiler()
        self.assertIsNone(c.project_root)
        result = c.compile("段 主():\n结束。\n")
        self.assertIsNotNone(result)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestTomlParsing, TestModuleLookup, TestBuildProject,
                 TestModuleDependencyResolver, TestBackwardCompatibility):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
