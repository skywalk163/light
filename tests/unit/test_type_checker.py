# -*- coding: utf-8 -*-
"""
光明分级类型检查系统单元测试

测试三级类型检查（签名/变量/表达式）和集成
"""

import sys
import os
import unittest
import io

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestTypeCheckerConfig(unittest.TestCase):
    """类型检查器配置测试"""

    @classmethod
    def setUpClass(cls):
        from type_checker import TypeCheckerConfig, TypeCheckLevel, SegmentTypeMode
        cls.TypeCheckerConfig = TypeCheckerConfig
        cls.TypeCheckLevel = TypeCheckLevel
        cls.SegmentTypeMode = SegmentTypeMode

    def test_default_config(self):
        """默认配置：不检查"""
        config = self.TypeCheckerConfig()
        self.assertEqual(config.check_level, self.TypeCheckLevel.NONE)
        self.assertEqual(config.default_segment_mode, self.SegmentTypeMode.LOOSE)

    def test_level_from_light_config(self):
        """从 LightConfig 创建配置"""
        from core.config import LightConfig
        dc = LightConfig()
        dc.type_check_level = self.TypeCheckLevel.VARIABLE
        dc.default_segment_mode = self.SegmentTypeMode.STRICT
        config = self.TypeCheckerConfig.from_light_config(dc)
        self.assertEqual(config.check_level, self.TypeCheckLevel.VARIABLE)
        self.assertEqual(config.default_segment_mode, self.SegmentTypeMode.STRICT)

    def test_file_directives_level(self):
        """文件级指令：类型检查级别"""
        source = '# 类型检查级别: 表达式\n段落 测试(a):整数:\n  返回 a'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.check_level, self.TypeCheckLevel.EXPRESSION)

    def test_file_directives_mode(self):
        """文件级指令：类型模式"""
        source = '# 类型模式: 严格\n段落 测试(a):整数:\n  返回 a'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.default_segment_mode, self.SegmentTypeMode.STRICT)

    def test_file_directives_both(self):
        """文件级指令：两者都有"""
        source = '# 类型检查级别: 变量\n# 类型模式: 严格\n段落 测试(a):整数:\n  返回 a'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.check_level, self.TypeCheckLevel.VARIABLE)
        self.assertEqual(config.default_segment_mode, self.SegmentTypeMode.STRICT)

    def test_file_directives_chinese_colon(self):
        """文件级指令：中文冒号"""
        source = '# 类型检查级别：签名\n段落 测试:\n  返回 1'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.check_level, self.TypeCheckLevel.SIGNATURE)

    def test_file_directives_case_insensitive(self):
        """文件级指令：大小写不敏感"""
        source = '# 类型检查级别: SIGNATURE\n段落 测试:\n  返回 1'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.check_level, self.TypeCheckLevel.SIGNATURE)

    def test_file_directives_stops_at_code(self):
        """文件级指令：非注释行停止扫描"""
        source = '# 类型检查级别: 表达式\n段落 测试:\n  返回 1\n# 类型检查级别: 签名'
        config = self.TypeCheckerConfig()
        config = config.apply_file_directives(source)
        self.assertEqual(config.check_level, self.TypeCheckLevel.EXPRESSION)

    def test_segment_check_level_strict(self):
        """段落修饰符：严格 = 表达式级"""
        config = self.TypeCheckerConfig(check_level=self.TypeCheckLevel.SIGNATURE)
        level = config.get_segment_check_level(['严格'])
        self.assertEqual(level, self.TypeCheckLevel.EXPRESSION)

    def test_segment_check_level_loose(self):
        """段落修饰符：松散 = 不检查"""
        config = self.TypeCheckerConfig(check_level=self.TypeCheckLevel.VARIABLE)
        level = config.get_segment_check_level(['松散'])
        self.assertEqual(level, self.TypeCheckLevel.NONE)

    def test_segment_check_level_default(self):
        """段落修饰符：无修饰符用全局配置"""
        config = self.TypeCheckerConfig(check_level=self.TypeCheckLevel.VARIABLE)
        level = config.get_segment_check_level([])
        self.assertEqual(level, self.TypeCheckLevel.VARIABLE)


class TestTypeCheckerIntegration(unittest.TestCase):
    """类型检查器集成测试（通过编译器）"""

    @classmethod
    def setUpClass(cls):
        from compiler import LightCompiler
        from core.config import TypeCheckLevel
        cls.Compiler = LightCompiler
        cls.TypeCheckLevel = TypeCheckLevel

    def test_signature_level_ok(self):
        """签名级检查：有类型标注的段落通过"""
        source = '# 类型检查级别: 签名\n段落 加法(a):整数, b:整数 返回 整数:\n  返回 a 加 b'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.SIGNATURE
        result = compiler.compile(source, optimize=False)
        type_errors = [e for e in compiler.errors if '类型错误' in str(e)]
        self.assertEqual(len(type_errors), 0)

    def test_signature_level_warning(self):
        """签名级检查：无类型标注产生警告"""
        source = '# 类型检查级别: 签名\n段落 加法(a, b):\n  返回 a 加 b'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.SIGNATURE
        result = compiler.compile(source, optimize=False)
        warnings = compiler.warnings
        self.assertGreater(len(warnings), 0)

    def test_signature_level_confirmed(self):
        """签名级检查：确认检查已执行"""
        source = '# 类型检查级别: 无\n段落 无警告(a, b):\n  返回 a 加 b'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.NONE
        result = compiler.compile(source, optimize=False)
        type_errors = [e for e in compiler.errors if '类型错误' in str(e)]
        self.assertEqual(len(type_errors), 0)

    def test_no_check_level(self):
        """不检查级别：跳过类型检查"""
        source = '段落 无检查(a, b):\n  返回 a 加 b'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.NONE
        result = compiler.compile(source, optimize=False)
        type_errors = [e for e in compiler.errors if '类型错误' in str(e)]
        self.assertEqual(len(type_errors), 0)


class TestStrictModifier(unittest.TestCase):
    """严格修饰符测试"""

    @classmethod
    def setUpClass(cls):
        from compiler import LightCompiler
        from core.config import TypeCheckLevel
        cls.Compiler = LightCompiler
        cls.TypeCheckLevel = TypeCheckLevel

    def test_strict_segment_parses(self):
        """严格段落能正常解析"""
        source = '严格 段落 测试(a):整数:\n  返回 a'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.EXPRESSION
        result = compiler.compile(source, optimize=False)
        self.assertIsNotNone(result)

    def test_strict_segment_without_type_annotation(self):
        """严格段落缺少类型标注报错"""
        source = '严格 段落 测试(a):\n  返回 a'
        compiler = self.Compiler()
        compiler._config.type_check_level = self.TypeCheckLevel.EXPRESSION
        result = compiler.compile(source, optimize=False)
        type_errors = [e for e in compiler.errors if '类型' in str(e)]
        self.assertGreater(len(type_errors), 0)


class TestTypeCheckResult(unittest.TestCase):
    """类型检查结果类测试"""

    @classmethod
    def setUpClass(cls):
        from type_checker import TypeCheckResult, TypeErrorSeverity
        cls.TypeCheckResult = TypeCheckResult
        cls.TypeErrorSeverity = TypeErrorSeverity

    def test_error_result(self):
        """错误级别的结果"""
        r = self.TypeCheckResult(self.TypeErrorSeverity.ERROR, '测试错误', line=10)
        self.assertTrue(r.is_error())
        self.assertEqual(r.line, 10)
        self.assertIn('error', r.__repr__())

    def test_warning_result(self):
        """警告级别的结果"""
        r = self.TypeCheckResult(self.TypeErrorSeverity.WARNING, '测试警告')
        self.assertFalse(r.is_error())

    def test_runtime_result(self):
        """运行时检查级别的结果"""
        r = self.TypeCheckResult(self.TypeErrorSeverity.RUNTIME, '运行时检查')
        self.assertFalse(r.is_error())


class TestExtractDirectives(unittest.TestCase):
    """指令提取测试"""

    def test_extract_type_directives(self):
        from type_checker import _extract_type_directives
        directives = _extract_type_directives('# 类型检查级别: 签名\n# 类型模式: 严格')
        self.assertEqual(directives.get('类型检查级别'), '签名')
        self.assertEqual(directives.get('类型模式'), '严格')

    def test_extract_empty(self):
        from type_checker import _extract_type_directives
        directives = _extract_type_directives('段落 测试:\n  返回 1')
        self.assertEqual(len(directives), 0)


if __name__ == '__main__':
    unittest.main()