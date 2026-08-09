# -*- coding: utf-8 -*-
"""
光明 v4.2 可选类型系统综合测试

测试覆盖：
  1. 类型系统桥接（LightTypeBridge）
  2. CFG 控制流分析（CFGAnalyzer）
  3. GradedTypeChecker 分级检查（SIGNATURE/VARIABLE/EXPRESSION）
  4. 类型推断器集成
  5. 类型兼容性检查
  6. 边界情况
"""
import sys
import os

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# =============================================================================
# 第一部分：类型系统桥接测试
# =============================================================================

def test_type_bridge_simple_types():
    """测试简单类型双向转换"""
    from type_checker import LightTypeBridge, TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_BOOL, TYPE_NONE, TYPE_ANY

    # 简单 → 高级
    from type_system import NumberType, StringType, BooleanType, NullType, AnyType as AdvAnyType

    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_INT), NumberType), "整数 → NumberType 失败"
    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_FLOAT), NumberType), "浮点 → NumberType 失败"
    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_STRING), StringType), "字符串 → StringType 失败"
    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_BOOL), BooleanType), "布尔 → BooleanType 失败"
    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_NONE), NullType), "空 → NullType 失败"
    assert isinstance(LightTypeBridge.simple_to_advanced(TYPE_ANY), AdvAnyType), "任意 → AnyType 失败"

    # 高级 → 简单
    assert LightTypeBridge.advanced_to_simple(NumberType()) == TYPE_INT, "NumberType → 整数 失败"
    assert LightTypeBridge.advanced_to_simple(StringType()) == TYPE_STRING, "StringType → 字符串 失败"
    assert LightTypeBridge.advanced_to_simple(BooleanType()) == TYPE_BOOL, "BooleanType → 布尔 失败"
    assert LightTypeBridge.advanced_to_simple(NullType()) == TYPE_NONE, "NullType → 空 失败"
    print("  [PASS] test_type_bridge_simple_types")


def test_type_bridge_compound_types():
    """测试复合类型双向转换"""
    from type_checker import LightTypeBridge, TYPE_INT, TYPE_STRING, ListType, DictType, OptionalType

    # 列表类型
    simple_list = ListType(TYPE_INT)
    adv_list = LightTypeBridge.simple_to_advanced(simple_list)
    from type_system import ListType as AdvListType
    assert isinstance(adv_list, AdvListType), "列表 → AdvListType 失败"

    back = LightTypeBridge.advanced_to_simple(adv_list)
    assert isinstance(back, ListType), "AdvListType → 列表 失败"
    assert back.element_type == TYPE_INT, f"元素类型不匹配: {back.element_type}"

    # 字典类型
    simple_dict = DictType(TYPE_STRING, TYPE_INT)
    adv_dict = LightTypeBridge.simple_to_advanced(simple_dict)
    from type_system import DictType as AdvDictType
    assert isinstance(adv_dict, AdvDictType), "字典 → AdvDictType 失败"

    back = LightTypeBridge.advanced_to_simple(adv_dict)
    assert isinstance(back, DictType), "AdvDictType → 字典 失败"

    # 可选类型
    simple_opt = OptionalType(TYPE_INT)
    adv_opt = LightTypeBridge.simple_to_advanced(simple_opt)
    from type_system import OptionalTypeWrapper
    assert isinstance(adv_opt, OptionalTypeWrapper), "可空 → OptionalTypeWrapper 失败"

    back = LightTypeBridge.advanced_to_simple(adv_opt)
    assert isinstance(back, OptionalType), "OptionalTypeWrapper → 可空 失败"
    print("  [PASS] test_type_bridge_compound_types")


def test_type_bridge_union_types():
    """测试联合类型转换"""
    from type_checker import LightTypeBridge, TYPE_INT, TYPE_FLOAT, TYPE_STRING, UnionType

    simple_union = UnionType((TYPE_INT, TYPE_FLOAT))
    adv = LightTypeBridge.simple_to_advanced(simple_union)
    from type_system import NumberType
    # 联合类型简化为第一个非空类型
    assert isinstance(adv, NumberType), f"联合类型应转换为 NumberType，实际 {type(adv).__name__}"
    print("  [PASS] test_type_bridge_union_types")


def test_type_bridge_none_input():
    """测试空输入"""
    from type_checker import LightTypeBridge, TYPE_ANY

    assert LightTypeBridge.simple_to_advanced(None) is None, "None 输入应返回 None"
    assert LightTypeBridge.advanced_to_simple(None) == TYPE_ANY, "None 高级类型应返回 TYPE_ANY"
    print("  [PASS] test_type_bridge_none_input")


# =============================================================================
# 第二部分：CFG 控制流分析测试
# =============================================================================

def test_cfg_all_paths_return_simple():
    """测试简单返回路径检测"""
    from type_checker import CFGAnalyzer

    # 模拟 ReturnStatement
    class MockReturn:
        def __init__(self): pass
    MockReturn.__name__ = 'ReturnStatement'

    # 单个返回语句
    assert CFGAnalyzer.all_paths_return([MockReturn()]), "单个返回语句应该检测到"
    print("  [PASS] test_cfg_all_paths_return_simple")


def test_cfg_all_paths_return_if_else():
    """测试 if-else 双分支返回路径检测"""
    from type_checker import CFGAnalyzer

    class MockReturn:
        pass
    MockReturn.__name__ = 'ReturnStatement'

    class MockIf:
        def __init__(self):
            self.then_body = []
            self.else_body = []
    MockIf.__name__ = 'IfStatement'

    # if-else 都有返回
    if_stmt = MockIf()
    if_stmt.then_body = [MockReturn()]
    if_stmt.else_body = [MockReturn()]
    assert CFGAnalyzer.all_paths_return([if_stmt]), "if-else 双分支都返回应该检测到"
    print("  [PASS] test_cfg_all_paths_return_if_else")


def test_cfg_all_paths_return_if_only():
    """测试仅 if 分支返回（无 else）"""
    from type_checker import CFGAnalyzer

    class MockReturn:
        pass
    MockReturn.__name__ = 'ReturnStatement'

    class MockIf:
        then_body = []
        else_body = []
    MockIf.__name__ = 'IfStatement'

    # 仅 if 返回，无 else
    if_stmt = MockIf()
    if_stmt.then_body = [MockReturn()]
    if_stmt.else_body = []
    assert not CFGAnalyzer.all_paths_return([if_stmt]), "仅 if 返回不应判定为全部返回"
    print("  [PASS] test_cfg_all_paths_return_if_only")


def test_cfg_all_paths_return_no_return():
    """测试无返回语句"""
    from type_checker import CFGAnalyzer

    class MockPrint:
        pass
    MockPrint.__name__ = 'PrintStatement'

    assert not CFGAnalyzer.all_paths_return([MockPrint()]), "无返回语句不应判定为返回"
    print("  [PASS] test_cfg_all_paths_return_no_return")


def test_cfg_all_paths_return_empty():
    """测试空代码块"""
    from type_checker import CFGAnalyzer
    assert not CFGAnalyzer.all_paths_return([]), "空代码块不应判定为返回"
    print("  [PASS] test_cfg_all_paths_return_empty")


def test_cfg_find_unreachable():
    """测试不可达代码检测"""
    from type_checker import CFGAnalyzer

    class MockReturn:
        line = 10
    MockReturn.__name__ = 'ReturnStatement'

    class MockPrint:
        line = 11
    MockPrint.__name__ = 'PrintStatement'

    # return 后面的代码不可达
    unreachable = CFGAnalyzer.find_unreachable_code([MockReturn(), MockPrint()])
    assert 11 in unreachable, f"return 后面的代码应该标记为不可达，实际 {unreachable}"
    print("  [PASS] test_cfg_find_unreachable")


def test_cfg_throw_unreachable():
    """测试 throw 后的不可达代码"""
    from type_checker import CFGAnalyzer

    class MockThrow:
        line = 5
    MockThrow.__name__ = 'ThrowStatement'

    class MockPrint:
        line = 6
    MockPrint.__name__ = 'PrintStatement'

    unreachable = CFGAnalyzer.find_unreachable_code([MockThrow(), MockPrint()])
    assert 6 in unreachable, f"throw 后面的代码应该标记为不可达，实际 {unreachable}"
    print("  [PASS] test_cfg_throw_unreachable")


# =============================================================================
# 第三部分：GradedTypeChecker 分级检查测试
# =============================================================================

def test_graded_checker_signature_level():
    """测试签名级检查"""
    from type_checker import (
        GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity, TYPE_INT, TYPE_STRING
    )
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.SIGNATURE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )
    checker = GradedTypeChecker(config)

    # 模拟一个有类型标注的段落
    class MockParam:
        def __init__(self, name, type_annotation):
            self.name = name
            self.type_annotation = type_annotation

    class MockSeg:
        def __init__(self, name, params, return_type, body, modifiers=None):
            self.name = name
            self.parameters = params
            self.return_type = return_type
            self.body = body
            self.modifiers = modifiers or []
            self.line = 1

    class MockModule:
        def __init__(self):
            self.segments = []
            self.statements = []
            self.classes = []

    module = MockModule()
    seg = MockSeg(
        name='测试段',
        params=[MockParam('a', '整数'), MockParam('b', '整数')],
        return_type='整数',
        body=[],
    )
    module.segments.append(seg)

    results = checker.check(module)
    # 有类型标注的段落不应产生警告
    assert len(results) == 0, f"完全标注的段落不应产生警告，实际 {len(results)} 个: {results}"
    print("  [PASS] test_graded_checker_signature_level - fully annotated")


def test_graded_checker_signature_missing():
    """测试签名级检查 - 缺少标注"""
    from type_checker import (
        GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity
    )
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.SIGNATURE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )
    checker = GradedTypeChecker(config)

    class MockParam:
        def __init__(self, name, type_annotation=None):
            self.name = name
            self.type_annotation = type_annotation

    class MockSeg:
        def __init__(self, name, params, return_type, body, modifiers=None):
            self.name = name
            self.parameters = params
            self.return_type = return_type
            self.body = body
            self.modifiers = modifiers or []
            self.line = 1

    class MockModule:
        def __init__(self):
            self.segments = []
            self.statements = []
            self.classes = []

    module = MockModule()
    seg = MockSeg(
        name='无标注段',
        params=[MockParam('a'), MockParam('b')],  # 无类型标注
        return_type=None,  # 无返回类型标注
        body=[],
    )
    module.segments.append(seg)

    results = checker.check(module)
    # 应该产生缺少类型标注的警告
    assert len(results) > 0, f"缺少标注的段落应产生警告，实际 {len(results)} 个"
    warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
    assert len(warnings) >= 2, f"至少应有2个警告（参数+返回），实际 {len(warnings)}"
    print(f"  [PASS] test_graded_checker_signature_missing - {len(results)} warnings")


def test_graded_checker_strict_mode():
    """测试严格模式"""
    from type_checker import (
        GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity
    )
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.SIGNATURE,
        default_segment_mode=SegmentTypeMode.STRICT,
    )
    checker = GradedTypeChecker(config)

    class MockParam:
        def __init__(self, name, type_annotation=None):
            self.name = name
            self.type_annotation = type_annotation

    class MockSeg:
        def __init__(self, name, params, return_type, body, modifiers=None):
            self.name = name
            self.parameters = params
            self.return_type = return_type
            self.body = body
            self.modifiers = modifiers or []
            self.line = 1

    class MockModule:
        def __init__(self):
            self.segments = []
            self.statements = []
            self.classes = []

    module = MockModule()
    seg = MockSeg(
        name='严格段',
        params=[MockParam('a')],  # 无类型标注
        return_type=None,
        body=[],
        modifiers=['严格'],  # 严格修饰符
    )
    module.segments.append(seg)

    results = checker.check(module)
    errors = [r for r in results if r.severity == TypeErrorSeverity.ERROR]
    assert len(errors) > 0, f"严格模式缺少标注应产生错误，实际 {len(errors)} 个错误"
    print(f"  [PASS] test_graded_checker_strict_mode - {len(errors)} errors")


def test_graded_checker_none_level():
    """测试 NONE 级别（不检查）"""
    from type_checker import (
        GradedTypeChecker, TypeCheckerConfig
    )
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.NONE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )
    checker = GradedTypeChecker(config)

    class MockParam:
        def __init__(self, name, type_annotation=None):
            self.name = name
            self.type_annotation = type_annotation

    class MockSeg:
        def __init__(self, name, params, return_type, body, modifiers=None):
            self.name = name
            self.parameters = params
            self.return_type = return_type
            self.body = body
            self.modifiers = modifiers or []
            self.line = 1

    class MockModule:
        def __init__(self):
            self.segments = []
            self.statements = []
            self.classes = []

    module = MockModule()
    seg = MockSeg(
        name='无检查段',
        params=[MockParam('a')],
        return_type=None,
        body=[],
    )
    module.segments.append(seg)

    results = checker.check(module)
    assert len(results) == 0, f"NONE 级别不应产生结果，实际 {len(results)} 个"
    print("  [PASS] test_graded_checker_none_level")


# =============================================================================
# 第四部分：类型兼容性测试
# =============================================================================

def test_type_compatibility_primitives():
    """测试基本类型兼容性"""
    from type_checker import TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_BOOL, TYPE_NONE, TYPE_ANY

    # 同一类型兼容
    assert TYPE_INT.is_compatible(TYPE_INT), "整数应与整数兼容"
    assert TYPE_STRING.is_compatible(TYPE_STRING), "字符串应与字符串兼容"

    # 不同类型不兼容
    assert not TYPE_INT.is_compatible(TYPE_STRING), "整数不应与字符串兼容"
    assert not TYPE_BOOL.is_compatible(TYPE_INT), "布尔不应与整数兼容"

    # Any 与一切兼容
    assert TYPE_ANY.is_compatible(TYPE_INT), "任意应与整数兼容"
    assert TYPE_ANY.is_compatible(TYPE_STRING), "任意应与字符串兼容"
    print("  [PASS] test_type_compatibility_primitives")


def test_type_compatibility_union():
    """测试联合类型兼容性"""
    from type_checker import TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_NONE, UnionType, OptionalType

    union = UnionType((TYPE_INT, TYPE_FLOAT))
    assert union.is_compatible(TYPE_INT), "整数|浮点应与整数兼容"
    assert union.is_compatible(TYPE_FLOAT), "整数|浮点应与浮点兼容"
    assert not union.is_compatible(TYPE_STRING), "整数|浮点不应与字符串兼容"

    # 联合类型之间的兼容性
    union2 = UnionType((TYPE_INT, TYPE_FLOAT, TYPE_STRING))
    assert union2.is_compatible(TYPE_INT), "三联合应与整数兼容"
    print("  [PASS] test_type_compatibility_union")


def test_type_compatibility_optional():
    """测试可选类型兼容性"""
    from type_checker import TYPE_INT, TYPE_STRING, TYPE_NONE, OptionalType

    opt_int = OptionalType(TYPE_INT)
    assert opt_int.is_compatible(TYPE_INT), "可空整数应与整数兼容"
    assert opt_int.is_compatible(TYPE_NONE), "可空整数应与空兼容"
    assert not opt_int.is_compatible(TYPE_STRING), "可空整数不应与字符串兼容"
    print("  [PASS] test_type_compatibility_optional")


def test_type_compatibility_list():
    """测试列表类型兼容性"""
    from type_checker import TYPE_INT, TYPE_STRING, TYPE_ANY, ListType

    list_int = ListType(TYPE_INT)
    list_str = ListType(TYPE_STRING)
    list_any = ListType(TYPE_ANY)

    assert list_int.is_compatible(list_int), "列表<整数>应与列表<整数>兼容"
    assert list_any.is_compatible(list_int), "列表<任意>应与列表<整数>兼容（任意接受一切）"
    assert not list_int.is_compatible(list_str), "列表<整数>不应与列表<字符串>兼容"
    print("  [PASS] test_type_compatibility_list")


def test_type_compatibility_dict():
    """测试字典类型兼容性"""
    from type_checker import TYPE_INT, TYPE_STRING, DictType

    dict1 = DictType(TYPE_STRING, TYPE_INT)
    dict2 = DictType(TYPE_STRING, TYPE_INT)
    dict3 = DictType(TYPE_INT, TYPE_STRING)

    assert dict1.is_compatible(dict2), "相同字典类型应兼容"
    assert not dict1.is_compatible(dict3), "不同值类型字典不应兼容"
    print("  [PASS] test_type_compatibility_dict")


def test_type_compatibility_function():
    """测试函数类型兼容性"""
    from type_checker import TYPE_INT, TYPE_FLOAT, TYPE_STRING, FunctionType, UnionType

    f1 = FunctionType((TYPE_INT, TYPE_INT), TYPE_INT)
    f2 = FunctionType((TYPE_INT, TYPE_INT), TYPE_INT)
    f3 = FunctionType((TYPE_INT,), TYPE_INT)
    f4 = FunctionType((TYPE_INT, TYPE_INT), TYPE_STRING)

    assert f1.is_compatible(f2), "相同函数类型应兼容"
    assert not f1.is_compatible(f3), "不同参数数量不应兼容"
    assert not f1.is_compatible(f4), "不同返回类型不应兼容"
    print("  [PASS] test_type_compatibility_function")


# =============================================================================
# 第五部分：类型推断器集成测试
# =============================================================================

def test_get_best_type_without_inferencer():
    """测试无 inferencer 时的 _get_best_type"""
    from type_checker import _get_best_type, TYPE_INT

    class MockNumber:
        value = 42
    MockNumber.__name__ = 'NumberLiteral'

    t = _get_best_type(MockNumber(), None)
    assert t == TYPE_INT, f"数字字面量应推断为整数，实际 {t}"
    print("  [PASS] test_get_best_type_without_inferencer")


def test_get_best_type_with_inferencer():
    """测试有 inferencer 时的 _get_best_type"""
    from type_checker import _get_best_type, _get_inferencer_type, TYPE_STRING
    from type_system import StringType

    # 模拟 inferencer
    class MockInferencer:
        def get_type_cache(self):
            return {}

    inferencer = MockInferencer()

    class MockString:
        value = "hello"
    MockString.__name__ = 'StringLiteral'

    t = _get_best_type(MockString(), inferencer)
    assert t == TYPE_STRING, f"字符串字面量应推断为字符串，实际 {t}"
    print("  [PASS] test_get_best_type_with_inferencer")


def test_get_inferencer_type_with_cache():
    """测试从 inferencer 缓存获取类型"""
    from type_checker import _get_inferencer_type, TYPE_INT
    from type_system import NumberType

    class MockNode:
        pass

    node = MockNode()
    cache = {id(node): NumberType()}

    class MockInferencer:
        def get_type_cache(self):
            return cache

    t = _get_inferencer_type(node, MockInferencer())
    assert t == TYPE_INT, f"从缓存获取的 NumberType 应转换为整数，实际 {t}"
    print("  [PASS] test_get_inferencer_type_with_cache")


# =============================================================================
# 第六部分：边界情况测试
# =============================================================================

def test_parse_type_annotation_invalid():
    """测试无效类型标注解析"""
    from type_checker import parse_type_annotation, TYPE_ANY

    assert parse_type_annotation('') == TYPE_ANY, "空字符串应返回 Any"
    assert parse_type_annotation('   ') == TYPE_ANY, "空白字符串应返回 Any"
    print("  [PASS] test_parse_type_annotation_invalid")


def test_parse_type_annotation_nested_generic():
    """测试嵌套泛型解析"""
    from type_checker import parse_type_annotation, ListType, DictType

    # 列表<字典<字符串, 整数>>
    t = parse_type_annotation('列表<字典<字符串, 整数>>')
    # 注意：解析器可能无法完美处理嵌套泛型，但至少不应崩溃
    assert t is not None, "嵌套泛型不应返回 None"
    print(f"  [PASS] test_parse_type_annotation_nested_generic - {t.to_light() if hasattr(t, 'to_light') else t}")


def test_type_directives_extraction():
    """测试文件指令提取"""
    from type_checker import _extract_type_directives

    source = "# 类型检查级别: 签名\n# 类型模式: 严格\n设 x 为 42"
    directives = _extract_type_directives(source)
    assert directives.get('类型检查级别') == '签名', f"类型检查级别应为'签名'，实际 {directives}"
    assert directives.get('类型模式') == '严格', f"类型模式应为'严格'，实际 {directives}"
    print("  [PASS] test_type_directives_extraction")


def test_type_directives_stop_at_code():
    """测试指令在遇到代码后停止"""
    from type_checker import _extract_type_directives

    source = "设 x 为 42\n# 类型检查级别: 签名"
    directives = _extract_type_directives(source)
    assert '类型检查级别' not in directives, "代码行后的指令不应被提取"
    print("  [PASS] test_type_directives_stop_at_code")


def test_type_checker_config_apply_directives():
    """测试配置应用文件指令"""
    from type_checker import TypeCheckerConfig
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.NONE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )
    source = "# 类型检查级别: 表达式\n# 类型模式: 严格"
    new_config = config.apply_file_directives(source)
    assert new_config.check_level == TypeCheckLevel.EXPRESSION, f"指令应设置级别为表达式，实际 {new_config.check_level}"
    assert new_config.default_segment_mode == SegmentTypeMode.STRICT, f"指令应设置模式为严格，实际 {new_config.default_segment_mode}"
    print("  [PASS] test_type_checker_config_apply_directives")


def test_type_checker_config_segment_check_level():
    """测试段落级检查级别"""
    from type_checker import TypeCheckerConfig
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.SIGNATURE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )

    assert config.get_segment_check_level([]) == TypeCheckLevel.SIGNATURE, "无修饰符应使用默认级别"
    assert config.get_segment_check_level(['严格']) == TypeCheckLevel.EXPRESSION, "严格修饰符应升级为表达式级"
    assert config.get_segment_check_level(['松散']) == TypeCheckLevel.NONE, "松散修饰符应降级为不检查"
    print("  [PASS] test_type_checker_config_segment_check_level")


def test_type_env_scope():
    """测试类型环境作用域"""
    from type_checker import TypeEnv, TYPE_INT, TYPE_STRING, TYPE_ANY

    env = TypeEnv()
    env.define('x', TYPE_INT)

    inner = env.push_scope()
    inner.define('y', TYPE_STRING)

    assert env.lookup('x') == TYPE_INT, "外层应能查找到 x"
    assert inner.lookup('x') == TYPE_INT, "内层应继承外层的 x"
    assert inner.lookup('y') == TYPE_STRING, "内层应能查找到 y"
    assert env.lookup('y') == TYPE_ANY, "外层不应能看到内层的 y"

    popped = inner.pop_scope()
    assert popped == env, "pop_scope 应返回父作用域"
    print("  [PASS] test_type_env_scope")


def test_type_checker_has_errors():
    """测试错误检测"""
    from type_checker import GradedTypeChecker, TypeCheckerConfig
    from core.config import TypeCheckLevel, SegmentTypeMode

    config = TypeCheckerConfig(
        check_level=TypeCheckLevel.NONE,
        default_segment_mode=SegmentTypeMode.LOOSE,
    )
    checker = GradedTypeChecker(config)

    class MockModule:
        segments = []
        statements = []
        classes = []

    checker.check(MockModule())
    assert not checker.has_errors(), "无错误时 has_errors 应返回 False"
    assert len(checker.get_errors()) == 0, "无错误时 get_errors 应返回空列表"
    assert len(checker.get_warnings()) == 0, "无警告时 get_warnings 应返回空列表"
    print("  [PASS] test_type_checker_has_errors")


# =============================================================================
# 运行所有测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明 v4.2 可选类型系统综合测试")
    print("=" * 60)

    total = 0
    passed = 0

    tests = [
        # 第一部分：类型系统桥接
        test_type_bridge_simple_types,
        test_type_bridge_compound_types,
        test_type_bridge_union_types,
        test_type_bridge_none_input,
        # 第二部分：CFG 控制流分析
        test_cfg_all_paths_return_simple,
        test_cfg_all_paths_return_if_else,
        test_cfg_all_paths_return_if_only,
        test_cfg_all_paths_return_no_return,
        test_cfg_all_paths_return_empty,
        test_cfg_find_unreachable,
        test_cfg_throw_unreachable,
        # 第三部分：GradedTypeChecker 分级检查
        test_graded_checker_signature_level,
        test_graded_checker_signature_missing,
        test_graded_checker_strict_mode,
        test_graded_checker_none_level,
        # 第四部分：类型兼容性
        test_type_compatibility_primitives,
        test_type_compatibility_union,
        test_type_compatibility_optional,
        test_type_compatibility_list,
        test_type_compatibility_dict,
        test_type_compatibility_function,
        # 第五部分：类型推断器集成
        test_get_best_type_without_inferencer,
        test_get_best_type_with_inferencer,
        test_get_inferencer_type_with_cache,
        # 第六部分：边界情况
        test_parse_type_annotation_invalid,
        test_parse_type_annotation_nested_generic,
        test_type_directives_extraction,
        test_type_directives_stop_at_code,
        test_type_checker_config_apply_directives,
        test_type_checker_config_segment_check_level,
        test_type_env_scope,
        test_type_checker_has_errors,
    ]

    for test in tests:
        total += 1
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("所有测试通过!")
    else:
        print(f"有 {total - passed} 个测试失败")
    print("=" * 60)