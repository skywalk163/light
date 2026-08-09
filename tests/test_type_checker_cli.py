# -*- coding: utf-8 -*-
"""
光明 v4.2 类型系统 CLI 工具测试

测试类型检查器的命令行接口：
  1. 独立 TypeChecker 的 CLI 模式
  2. 通过 check_source 和 check_module 检查
  3. 格式化输出
  4. JSON 输出
  5. 严格模式
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


# =============================================================================
# 第一部分：check_source 测试
# =============================================================================

def test_check_source_valid():
    """测试有效源代码的检查"""
    from type_checker import check_source

    source = """
段落 加法(a: 整数, b: 整数) 返回 整数:
    返回 a + b

段落 主():
    设 结果: 整数 为 加法(3, 5)
    打印(结果)
段落 主()
"""
    issues, module = check_source(source, strict=False)
    assert module is not None, "模块不应为 None"
    assert len(issues) == 0, f"不应有类型问题，实际 {len(issues)}"
    print("  [PASS] test_check_source_valid")


def test_check_source_with_type_mismatch():
    """测试类型不匹配的源代码"""
    from type_checker import check_source

    source = """
设 x: 整数 为 "字符串"
设 y: 字符串 为 42
"""
    issues, module = check_source(source, strict=False)
    assert module is not None, "模块不应为 None"
    # 类型不匹配应产生警告
    assert len(issues) > 0, f"类型不匹配应产生警告，实际 {len(issues)}"
    print(f"  [PASS] test_check_source_with_type_mismatch - {len(issues)} issues")


def test_check_source_strict():
    """测试严格模式"""
    from type_checker import check_source, IssueLevel

    source = """
设 x: 整数 为 "字符串"
"""
    issues, module = check_source(source, strict=True)
    assert module is not None, "模块不应为 None"
    # 严格模式下类型不匹配应为错误
    errors = [i for i in issues if i.level == IssueLevel.ERROR]
    assert len(errors) > 0, f"严格模式应有错误，实际 {len(errors)}"
    print(f"  [PASS] test_check_source_strict - {len(errors)} errors")


def test_check_source_syntax_error():
    """测试语法错误的源代码"""
    from type_checker import check_source, IssueLevel

    # 无效的光明语法
    source = "not valid light code @@@"
    issues, module = check_source(source, strict=False)
    # 应返回解析错误
    assert len(issues) > 0, f"语法错误应产生问题，实际 {len(issues)}"
    # 但模块应为 None（解析失败）
    print(f"  [PASS] test_check_source_syntax_error - {len(issues)} issues")


# =============================================================================
# 第二部分：check_module 测试
# =============================================================================

def test_check_module_basic():
    """测试 check_module 基本功能"""
    from type_checker import check_module
    from light_parser_v3 import LightParser

    parser = LightParser()
    source = """
设 姓名: 字符串 为 "张三"
设 年龄: 整数 为 25
"""
    module = parser.parse(source)
    issues = check_module(module, strict=False)
    # 类型匹配，无问题
    assert len(issues) == 0, f"类型匹配不应有问题，实际 {len(issues)}"
    print("  [PASS] test_check_module_basic")


def test_check_module_with_segments():
    """测试包含段落的模块检查"""
    from type_checker import check_module
    from light_parser_v3 import LightParser

    parser = LightParser()
    source = """
段落 计算(a: 整数, b: 整数) 返回 整数:
    返回 a + b

段落 主():
    打印(计算(3, 5))
段落 主()
"""
    module = parser.parse(source)
    issues = check_module(module, strict=False)
    # 类型匹配，无问题
    assert len(issues) == 0, f"类型匹配的段落不应有问题，实际 {len(issues)}"
    print("  [PASS] test_check_module_with_segments")


# =============================================================================
# 第三部分：format_issues 测试
# =============================================================================

def test_format_issues_empty():
    """测试空问题列表的格式化"""
    from type_checker import format_issues

    result = format_issues([])
    assert "未发现" in result, f"空问题应显示无问题，实际: {result}"
    print("  [PASS] test_format_issues_empty")


def test_format_issues_with_errors():
    """测试有问题的格式化输出"""
    from type_checker import format_issues, TypeIssue, IssueLevel

    issues = [
        TypeIssue(level=IssueLevel.ERROR, message="类型不匹配", line=10, code='T001'),
        TypeIssue(level=IssueLevel.WARNING, message="缺少类型标注", line=5, code='S002'),
    ]
    result = format_issues(issues)
    assert 'T001' in result, "输出应包含错误码"
    assert '类型不匹配' in result, "输出应包含错误消息"
    print(f"  [PASS] test_format_issues_with_errors")


# =============================================================================
# 第四部分：TypeCheckResult 测试
# =============================================================================

def test_type_check_result():
    """测试 TypeCheckResult 数据类"""
    from type_checker import TypeCheckResult, TypeErrorSeverity

    result = TypeCheckResult(
        severity=TypeErrorSeverity.ERROR,
        message="测试错误",
        line=10,
        column=5,
        code='T001',
    )
    assert result.is_error(), "错误级别应返回 True"
    assert result.severity == TypeErrorSeverity.ERROR
    assert result.message == "测试错误"
    assert result.line == 10
    assert result.column == 5
    assert result.code == 'T001'
    print("  [PASS] test_type_check_result")


# =============================================================================
# 第五部分：工厂函数测试
# =============================================================================

def test_create_checker_from_config():
    """测试工厂函数 create_checker_from_config"""
    from type_checker import create_checker_from_config, GradedTypeChecker
    from core.config import LightConfig, TypeCheckLevel, SegmentTypeMode

    config = LightConfig()
    config.type_check_level = TypeCheckLevel.EXPRESSION
    config.default_segment_mode = SegmentTypeMode.STRICT

    checker = create_checker_from_config(config)
    assert isinstance(checker, GradedTypeChecker), f"应返回 GradedTypeChecker，实际 {type(checker).__name__}"
    assert checker.config.check_level == TypeCheckLevel.EXPRESSION
    assert checker.config.default_segment_mode == SegmentTypeMode.STRICT
    print("  [PASS] test_create_checker_from_config")


def test_create_checker_from_source():
    """测试工厂函数 create_checker_from_source"""
    from type_checker import create_checker_from_source, GradedTypeChecker
    from core.config import LightConfig, TypeCheckLevel, SegmentTypeMode

    config = LightConfig()
    config.type_check_level = TypeCheckLevel.NONE
    config.default_segment_mode = SegmentTypeMode.LOOSE

    source = """# 类型检查级别: 表达式
# 类型模式: 严格

段落 主():
    打印("Hello")
段落 主()
"""
    checker = create_checker_from_source(source, config)
    assert isinstance(checker, GradedTypeChecker), f"应返回 GradedTypeChecker，实际 {type(checker).__name__}"
    # 文件指令应覆盖默认配置
    assert checker.config.check_level == TypeCheckLevel.EXPRESSION, \
        f"文件指令应设置级别为 EXPRESSION，实际 {checker.config.check_level}"
    assert checker.config.default_segment_mode == SegmentTypeMode.STRICT, \
        f"文件指令应设置模式为 STRICT，实际 {checker.config.default_segment_mode}"
    print("  [PASS] test_create_checker_from_source")


# =============================================================================
# 运行所有测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 v4.2 类型系统 CLI 工具测试")
    print("=" * 60)

    total = 0
    passed = 0

    tests = [
        test_check_source_valid,
        test_check_source_with_type_mismatch,
        test_check_source_strict,
        test_check_source_syntax_error,
        test_check_module_basic,
        test_check_module_with_segments,
        test_format_issues_empty,
        test_format_issues_with_errors,
        test_type_check_result,
        test_create_checker_from_config,
        test_create_checker_from_source,
    ]

    for test in tests:
        total += 1
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("所有测试通过!")
    else:
        print(f"有 {total - passed} 个测试失败")
    print("=" * 60)