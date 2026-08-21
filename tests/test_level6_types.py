# -*- coding: utf-8 -*-
"""
段言（Duan）Level 6 类型注解系统测试

覆盖：
  1. TypeAnnotation AST 节点（创建、to_dict、_fields、__repr__、__slots__）
  2. 基本类型名映射（整数→int, 文本→str, 布尔→bool, 小数→float, 空→None）
  3. 可选类型包装（整数? → Optional[int]）
  4. 列表类型记法（[整数] → List[int]）
  5. 字典类型记法（{文本: 整数} → Dict[str, int]）
  6. 函数类型记法（接收 整数, 文本 返回 布尔 → Callable[[int, str], bool]）
  7. 类型注解零成本（不影响代码生成的运行时语义）
  8. type_checker 与带注解变量协同工作
  9. type_system.py 既有类型类（is_subtype_of / unify / TypeParser 等）
"""

import sys
import os
import types

# conftest.py 已将 src 与项目根加入 sys.path，这里保持与同级测试一致的显式保险
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from ast_nodes_v3 import (
    TypeAnnotation, VarDecl, NumberLiteral, StringLiteral, ASTNode,
)
from type_system import (
    Type, NumberType, StringType, BooleanType, NullType, AnyType, UnknownType,
    OptionalTypeWrapper, ListType, DictType, TupleType, SetType, FunctionType,
    TypeVar, GenericTypeInstance, ClassType, InterfaceType,
    TypeSubstitution, UnificationError, unify, TypeParser,
    TypeSymbolTable, TypeErrorInference,
    TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL, TYPE_ANY, TYPE_UNKNOWN,
)
from type_checker import (
    GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity,
)
from core.config import TypeCheckLevel, SegmentTypeMode


# =============================================================================
# 1. TypeAnnotation 节点创建与序列化
# =============================================================================

class TestTypeAnnotationNode:
    """TypeAnnotation AST 节点基础行为"""

    def test_inherits_from_astnode(self):
        node = TypeAnnotation(base_type='整数')
        assert isinstance(node, ASTNode)

    def test_basic_creation_defaults(self):
        node = TypeAnnotation(base_type='整数')
        assert node.base_type == '整数'
        assert node.is_optional is False
        assert node.is_list is False
        assert node.is_dict is False
        assert node.key_type is None
        assert node.value_type is None
        assert node.params == []
        assert node.return_type is None

    def test_slots_does_not_allow_arbitrary_attrs(self):
        """__slots__ 限制：不能添加额外属性"""
        node = TypeAnnotation(base_type='整数')
        assert not hasattr(node, '__dict__')
        with pytest.raises(AttributeError):
            node.some_random_field = 1

    def test_slots_contains_all_declared_fields(self):
        expected = {
            'base_type', 'is_optional', 'is_list', 'is_dict',
            'key_type', 'value_type', 'params', 'return_type',
            # ASTNode 基类的 slots
            'line', 'col',
        }
        declared = set(TypeAnnotation.__slots__) | set(ASTNode.__slots__)
        assert expected.issubset(declared)

    def test_line_col_propagated_from_base(self):
        node = TypeAnnotation(base_type='整数', line=12, col=5)
        assert node.line == 12
        assert node.col == 5

    def test_to_dict_basic(self):
        node = TypeAnnotation(base_type='文本')
        d = node.to_dict()
        assert d['node'] == 'TypeAnnotation'
        assert d['base_type'] == '文本'
        assert d['is_optional'] is False
        assert d['is_list'] is False
        assert d['is_dict'] is False
        assert d['key_type'] is None
        assert d['value_type'] is None
        assert d['params'] == []
        assert d['return_type'] is None

    def test_to_dict_list(self):
        node = TypeAnnotation(base_type='整数', is_list=True)
        d = node.to_dict()
        assert d['is_list'] is True
        assert d['base_type'] == '整数'

    def test_to_dict_dict(self):
        node = TypeAnnotation(is_dict=True, key_type='文本', value_type='整数')
        d = node.to_dict()
        assert d['is_dict'] is True
        assert d['key_type'] == '文本'
        assert d['value_type'] == '整数'

    def test_to_dict_optional(self):
        node = TypeAnnotation(base_type='整数', is_optional=True)
        d = node.to_dict()
        assert d['is_optional'] is True

    def test_to_dict_function(self):
        node = TypeAnnotation(params=['整数', '文本'], return_type='布尔')
        d = node.to_dict()
        assert d['params'] == ['整数', '文本']
        assert d['return_type'] == '布尔'

    def test_to_dict_returns_independent_copy_of_params(self):
        """to_dict 返回的 params 列表应独立于内部状态"""
        src_params = ['整数', '文本']
        node = TypeAnnotation(params=src_params, return_type='布尔')
        d = node.to_dict()
        d['params'].append('被篡改')
        assert node.params == ['整数', '文本']  # 内部未受影响

    def test_fields_returns_tuple(self):
        node = TypeAnnotation(base_type='整数', is_optional=True)
        f = node._fields()
        assert isinstance(f, tuple)
        # 顺序：base_type, is_optional, is_list, is_dict, key_type, value_type, params, return_type
        assert f[0] == '整数'
        assert f[1] is True
        assert f[6] == ()  # 空 params 转为元组

    def test_fields_distinguishes_equal_nodes(self):
        a = TypeAnnotation(base_type='整数')
        b = TypeAnnotation(base_type='整数')
        c = TypeAnnotation(base_type='文本')
        assert a._fields() == b._fields()
        assert a._fields() != c._fields()

    def test_repr_basic(self):
        assert repr(TypeAnnotation(base_type='整数')) == 'TypeAnnotation(整数)'

    def test_repr_list(self):
        assert repr(TypeAnnotation(base_type='整数', is_list=True)) == 'TypeAnnotation([整数])'

    def test_repr_dict(self):
        node = TypeAnnotation(is_dict=True, key_type='文本', value_type='整数')
        assert repr(node) == 'TypeAnnotation({文本: 整数})'

    def test_repr_optional(self):
        assert repr(TypeAnnotation(base_type='整数', is_optional=True)) == 'TypeAnnotation(整数?)'

    def test_repr_function(self):
        node = TypeAnnotation(params=['整数', '文本'], return_type='布尔')
        assert repr(node) == 'TypeAnnotation(接收 整数, 文本 返回 布尔)'


# =============================================================================
# 2. 基本类型名映射
# =============================================================================

class TestBasicTypeMapping:
    """段言基本类型名 → Python 类型名"""

    @pytest.mark.parametrize('duan,py', [
        ('整数', 'int'),
        ('文本', 'str'),
        ('布尔', 'bool'),
        ('小数', 'float'),
        ('空', 'None'),
    ])
    def test_required_mapping(self, duan, py):
        """任务指定五组映射必须成立"""
        assert TypeAnnotation._map_basic(duan) == py

    @pytest.mark.parametrize('duan,py', [
        ('整数', 'int'),
        ('小数', 'float'),
        ('浮数', 'float'),
        ('数', 'float'),
        ('文本', 'str'),
        ('串', 'str'),
        ('布尔', 'bool'),
        ('空', 'None'),
        ('任意', 'Any'),
        ('列表', 'list'),
        ('列', 'list'),
        ('字典', 'dict'),
        ('典', 'dict'),
        ('集合', 'set'),
        ('集', 'set'),
    ])
    def test_full_mapping_table(self, duan, py):
        assert TypeAnnotation._DUAN_TO_PYTHON[duan] == py

    def test_unknown_type_passthrough(self):
        """未在映射表中的类型名原样返回（自定义类型）"""
        assert TypeAnnotation._map_basic('自定义类型') == '自定义类型'

    def test_to_python_type_basic(self):
        assert TypeAnnotation(base_type='整数').to_python_type() == 'int'
        assert TypeAnnotation(base_type='文本').to_python_type() == 'str'
        assert TypeAnnotation(base_type='布尔').to_python_type() == 'bool'
        assert TypeAnnotation(base_type='小数').to_python_type() == 'float'
        assert TypeAnnotation(base_type='空').to_python_type() == 'None'

    def test_mapping_consistent_with_code_generator(self):
        """TypeAnnotation 的类型映射应与 code_generator._map_type 一致"""
        from code_generator import PythonCodeGenerator
        gen = PythonCodeGenerator()
        for duan, py in TypeAnnotation._DUAN_TO_PYTHON.items():
            assert gen._map_type(duan) == py, f"映射不一致: {duan}"


# =============================================================================
# 3. 可选类型包装
# =============================================================================

class TestOptionalType:
    """整数? 形式的可选类型"""

    def test_optional_flag(self):
        node = TypeAnnotation(base_type='整数', is_optional=True)
        assert node.is_optional is True

    def test_to_python_type_optional(self):
        node = TypeAnnotation(base_type='整数', is_optional=True)
        assert node.to_python_type() == 'Optional[int]'

    def test_to_python_type_optional_text(self):
        node = TypeAnnotation(base_type='文本', is_optional=True)
        assert node.to_python_type() == 'Optional[str]'

    def test_optional_does_not_imply_list_or_dict(self):
        node = TypeAnnotation(base_type='整数', is_optional=True)
        assert node.is_list is False
        assert node.is_dict is False


# =============================================================================
# 4. 列表类型记法
# =============================================================================

class TestListType:
    """[整数] 形式的列表类型"""

    def test_list_flag_and_base_type(self):
        node = TypeAnnotation(base_type='整数', is_list=True)
        assert node.is_list is True
        assert node.base_type == '整数'

    def test_to_python_type_list(self):
        node = TypeAnnotation(base_type='整数', is_list=True)
        assert node.to_python_type() == 'List[int]'

    def test_to_python_type_list_text(self):
        node = TypeAnnotation(base_type='文本', is_list=True)
        assert node.to_python_type() == 'List[str]'

    def test_to_python_type_list_empty_base(self):
        """无元素类型的列表 → List[Any]"""
        node = TypeAnnotation(is_list=True)
        assert node.to_python_type() == 'List[Any]'

    def test_list_with_optional(self):
        """[整数]? → Optional[List[int]]"""
        node = TypeAnnotation(base_type='整数', is_list=True, is_optional=True)
        assert node.to_python_type() == 'Optional[List[int]]'


# =============================================================================
# 5. 字典类型记法
# =============================================================================

class TestDictType:
    """{文本: 整数} 形式的字典类型"""

    def test_dict_flags_and_kv(self):
        node = TypeAnnotation(is_dict=True, key_type='文本', value_type='整数')
        assert node.is_dict is True
        assert node.key_type == '文本'
        assert node.value_type == '整数'

    def test_to_python_type_dict(self):
        node = TypeAnnotation(is_dict=True, key_type='文本', value_type='整数')
        assert node.to_python_type() == 'Dict[str, int]'

    def test_to_python_type_dict_optional_value(self):
        node = TypeAnnotation(is_dict=True, key_type='文本', value_type='整数')
        # 字典本身可选
        node.is_optional = True
        assert node.to_python_type() == 'Optional[Dict[str, int]]'

    def test_to_python_type_dict_missing_kv(self):
        """缺少键/值类型 → Any 兜底"""
        node = TypeAnnotation(is_dict=True)
        assert node.to_python_type() == 'Dict[Any, Any]'

    def test_dict_takes_precedence_over_base_type(self):
        """is_dict=True 时优先按字典渲染，忽略 base_type"""
        node = TypeAnnotation(base_type='整数', is_dict=True, key_type='文本', value_type='小数')
        assert node.to_python_type() == 'Dict[str, float]'


# =============================================================================
# 6. 函数类型记法
# =============================================================================

class TestFunctionType:
    """接收 整数, 文本 返回 布尔 形式的函数类型"""

    def test_function_fields(self):
        node = TypeAnnotation(params=['整数', '文本'], return_type='布尔')
        assert node.params == ['整数', '文本']
        assert node.return_type == '布尔'

    def test_to_python_type_function(self):
        node = TypeAnnotation(params=['整数', '文本'], return_type='布尔')
        assert node.to_python_type() == 'Callable[[int, str], bool]'

    def test_to_python_type_function_single_param(self):
        node = TypeAnnotation(params=['小数'], return_type='小数')
        assert node.to_python_type() == 'Callable[[float], float]'

    def test_function_with_optional(self):
        node = TypeAnnotation(params=['整数'], return_type='布尔', is_optional=True)
        assert node.to_python_type() == 'Optional[Callable[[int], bool]]'

    def test_function_without_params_falls_back_to_basic(self):
        """仅有 return_type 而无 params 时，不视作函数类型"""
        node = TypeAnnotation(base_type='整数', return_type='布尔')
        assert node.to_python_type() == 'int'


# =============================================================================
# 7. 类型注解零成本（不影响代码生成的运行时语义）
# =============================================================================

class TestZeroCost:
    """类型注解为零成本：生成的代码运行时语义不变"""

    def _gen_var_decl(self, type_annotation):
        from code_generator import PythonCodeGenerator
        gen = PythonCodeGenerator()
        gen._generate_var_decl(
            VarDecl('x', NumberLiteral(10), type_annotation=type_annotation)
        )
        return gen.output_lines

    def test_annotated_and_unannotated_produce_same_runtime_value(self):
        lines_with = self._gen_var_decl('整数')
        lines_without = self._gen_var_decl(None)

        ns_with = {}
        ns_without = {}
        exec('\n'.join(lines_with), ns_with)
        exec('\n'.join(lines_without), ns_without)

        # 运行时值完全一致 —— 注解不改变语义
        assert ns_with['x'] == ns_without['x'] == 10

    def test_annotation_appears_in_generated_code(self):
        """类型注解确实被渲染为 Python 注解（: int）"""
        lines_with = self._gen_var_decl('整数')
        assert any(': int' in line for line in lines_with)

    def test_no_annotation_when_absent(self):
        lines_without = self._gen_var_decl(None)
        assert not any(': int' in line for line in lines_without)

    def test_runtime_type_check_off_by_default(self):
        """代码生成器默认关闭运行时类型检查（零开销）"""
        from code_generator import PythonCodeGenerator
        gen = PythonCodeGenerator()
        assert gen._runtime_type_check is False

    def test_no_runtime_check_inserted_when_disabled(self):
        """默认配置下不应注入 _light_check_type 调用"""
        lines = self._gen_var_decl('整数')
        assert not any('_light_check_type' in line for line in lines)

    def test_typeannotation_node_does_not_break_code_generator(self):
        """TypeAnnotation 节点对象本身不参与 code_generator 流程
        （code_generator 仅识别字符串形式 type_annotation）。
        将 TypeAnnotation 节点作为结构化表示独立于 codegen，互不干扰。
        """
        # TypeAnnotation 是结构化节点，与 codegen 用的字符串注解解耦
        node = TypeAnnotation(base_type='整数', is_list=True)
        # 它能独立产出 Python 类型表达式
        assert node.to_python_type() == 'List[int]'
        # 而 code_generator 仍使用字符串注解路径正常工作
        lines = self._gen_var_decl('整数')
        assert any('x' in line for line in lines)


# =============================================================================
# 8. type_checker 与带注解变量协同工作
# =============================================================================

def _make_module(segment):
    """构造一个最小模块对象，包含 segments 列表"""
    return types.SimpleNamespace(statements=[], segments=[segment])


def _make_segment(name, body, parameters=None, return_type='空', modifiers=None):
    """构造一个最小段落对象

    return_type 默认给 '空'（而不是 None）：SIGNATURE 档对缺少返回类型标注的段落
    无条件发 S004 警告（src/type_checker.py:912-918），会污染那些只想观察变量级
    告警的结果集。'空' 解析为 TYPE_NONE，既跳过 S004，也跳过
    src/type_checker.py:926 之后的 CFG 返回值分析（S006/S007）。
    """
    return types.SimpleNamespace(
        name=name,
        body=body,
        parameters=parameters or [],
        return_type=return_type,
        modifiers=modifiers or [],
    )


class TestTypeCheckerWithAnnotations:
    """分级类型检查器与变量类型注解"""

    # 口径变更(v7 合并)：VARIABLE 档以 light 现行实现为准——只对「注解与推断类型冲突」告警，不对缺注解告警。原 duan 期望「缺注解→告警」已废止。
    def test_variable_level_warns_on_annotation_conflict(self):
        """VARIABLE 级别下，注解与推断类型冲突的变量应产生 WARNING（V001）"""
        body = [VarDecl('数量', StringLiteral('十'), type_annotation='整数')]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(
            check_level=TypeCheckLevel.VARIABLE,
            default_segment_mode=SegmentTypeMode.LOOSE,
        )
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)

        warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
        assert len(warnings) == 1
        assert warnings[0].code == 'V001'
        assert '数量' in warnings[0].message

    # 口径变更(v7 合并)：VARIABLE 档以 light 现行实现为准——只对「注解与推断类型冲突」告警，不对缺注解告警。原 duan 期望「缺注解→告警」已废止。
    def test_variable_level_silent_on_missing_annotation(self):
        """VARIABLE 级别下，未注解变量不产生 V001（light 语义：缺注解不发声）"""
        body = [VarDecl('未注解变量', NumberLiteral(1), type_annotation=None)]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(
            check_level=TypeCheckLevel.VARIABLE,
            default_segment_mode=SegmentTypeMode.LOOSE,
        )
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)

        assert [r for r in results if r.code == 'V001'] == []
        assert [r for r in results if '未注解变量' in r.message] == []

    def test_variable_level_no_warning_with_annotation(self):
        """VARIABLE 级别下，带类型注解且类型相符的变量不应产生 WARNING"""
        body = [VarDecl('已注解变量', NumberLiteral(1), type_annotation='整数')]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(
            check_level=TypeCheckLevel.VARIABLE,
            default_segment_mode=SegmentTypeMode.LOOSE,
        )
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)

        warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
        assert warnings == []

    def test_none_level_skips_checking(self):
        """NONE 级别下不产生任何结果"""
        body = [VarDecl('未注解变量', NumberLiteral(1), type_annotation=None)]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(check_level=TypeCheckLevel.NONE)
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)
        assert results == []

    def test_signature_level_does_not_check_variables(self):
        """SIGNATURE 级别（低于 VARIABLE）不检查变量类型"""
        body = [VarDecl('数量', StringLiteral('十'), type_annotation='整数')]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(
            check_level=TypeCheckLevel.SIGNATURE,
            default_segment_mode=SegmentTypeMode.LOOSE,
        )
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)

        # SIGNATURE 级别不会触发变量级检查：同样的冲突在 VARIABLE 档会产出 V001
        assert [r for r in results if r.code == 'V001'] == []

    # 口径变更(v7 合并)：VARIABLE 档以 light 现行实现为准——只对「注解与推断类型冲突」告警，不对缺注解告警。原 duan 期望「缺注解→告警」已废止。
    def test_mixed_annotated_and_unannotated(self):
        """混合场景：只对「注解与推断类型冲突」的变量产生警告"""
        body = [
            VarDecl('注解相符', NumberLiteral(1), type_annotation='整数'),
            VarDecl('注解冲突', StringLiteral('十'), type_annotation='整数'),
            VarDecl('无注解', NumberLiteral(2), type_annotation=None),
        ]
        seg = _make_segment('段落一', body)
        module = _make_module(seg)

        config = TypeCheckerConfig(
            check_level=TypeCheckLevel.VARIABLE,
            default_segment_mode=SegmentTypeMode.LOOSE,
        )
        checker = GradedTypeChecker(config)
        results = checker.check(module, inferencer=None)

        warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
        # 仅"注解冲突"产生警告："注解相符"类型一致，"无注解"按 light 语义不发声
        assert len(warnings) == 1
        assert warnings[0].code == 'V001'
        assert '注解冲突' in warnings[0].message


# =============================================================================
# 9. type_system.py 既有类型类
# =============================================================================

class TestBasicTypes:
    """基本类型行为"""

    def test_singletons(self):
        """基本类型为单例"""
        assert NumberType() is NumberType()
        assert StringType() is StringType()
        assert BooleanType() is BooleanType()
        assert NullType() is NullType()
        assert AnyType() is AnyType()

    def test_type_id_constants(self):
        assert NumberType()._type_id == 1
        assert StringType()._type_id == 2
        assert BooleanType()._type_id == 3
        assert NullType()._type_id == 4
        assert AnyType()._type_id == 5

    def test_repr_uses_chinese_display_name(self):
        assert repr(NumberType()) == '数'
        assert repr(StringType()) == '串'
        assert repr(BooleanType()) == '布尔'
        assert repr(NullType()) == '空'
        assert repr(AnyType()) == '任意'


class TestIsSubtypeOf:
    """is_subtype_of 关系"""

    def test_same_type_is_subtype(self):
        assert NumberType().is_subtype_of(NumberType())
        assert StringType().is_subtype_of(StringType())

    def test_different_basic_not_subtype(self):
        assert not NumberType().is_subtype_of(StringType())
        assert not StringType().is_subtype_of(BooleanType())

    def test_any_is_supertype_of_all(self):
        """任意类型是所有类型的超类型"""
        assert NumberType().is_subtype_of(AnyType())
        assert StringType().is_subtype_of(AnyType())
        assert BooleanType().is_subtype_of(AnyType())
        assert NullType().is_subtype_of(AnyType())

    def test_any_is_subtype_of_any(self):
        assert AnyType().is_subtype_of(AnyType())

    def test_null_assignable_to_optional_and_any(self):
        """空值可赋给可空类型或任意类型"""
        assert NullType().is_subtype_of(AnyType())
        assert NullType().is_subtype_of(OptionalTypeWrapper(NumberType()))
        assert NullType().is_subtype_of(NullType())
        # 空值不能赋给非空的具体类型
        assert not NullType().is_subtype_of(NumberType())

    def test_unknown_compatible_with_all(self):
        """未知类型与所有类型兼容（渐进式推断）"""
        assert UnknownType().is_subtype_of(NumberType())
        assert UnknownType().is_subtype_of(AnyType())


class TestOptionalTypeWrapper:
    """OptionalTypeWrapper 行为"""

    def test_repr(self):
        opt = OptionalTypeWrapper(NumberType())
        assert repr(opt) == '数|空'

    def test_unwrap(self):
        inner = NumberType()
        opt = OptionalTypeWrapper(inner)
        assert opt.unwrap() is inner

    def test_optional_subtype_of_optional(self):
        assert OptionalTypeWrapper(NumberType()).is_subtype_of(
            OptionalTypeWrapper(NumberType())
        )

    def test_optional_not_subtype_of_concrete(self):
        """可空类型不是具体类型的子类型"""
        assert not OptionalTypeWrapper(NumberType()).is_subtype_of(NumberType())

    def test_optional_subtype_of_any(self):
        assert OptionalTypeWrapper(NumberType()).is_subtype_of(AnyType())


class TestListType:
    """ListType 行为"""

    def test_repr_with_element(self):
        assert repr(ListType(NumberType())) == '列表[数]'

    def test_repr_without_element(self):
        assert repr(ListType()) == '列表'

    def test_list_subtype_covariant(self):
        """列表元素协变：List[数] <: List[数]"""
        assert ListType(NumberType()).is_subtype_of(ListType(NumberType()))

    def test_list_with_unknown_element_compatible(self):
        assert ListType(NumberType()).is_subtype_of(ListType(None))

    def test_list_not_subtype_of_dict(self):
        assert not ListType(NumberType()).is_subtype_of(DictType())


class TestDictType:
    """DictType 行为"""

    def test_repr_with_kv(self):
        d = DictType(StringType(), NumberType())
        assert repr(d) == '字典[串: 数]'

    def test_repr_without_kv(self):
        assert repr(DictType()) == '字典'

    def test_dict_subtype_same_kv(self):
        d1 = DictType(StringType(), NumberType())
        d2 = DictType(StringType(), NumberType())
        assert d1.is_subtype_of(d2)

    def test_dict_not_subtype_of_list(self):
        assert not DictType(StringType(), NumberType()).is_subtype_of(ListType())


class TestFunctionType:
    """FunctionType 行为"""

    def test_repr(self):
        ft = FunctionType([NumberType(), StringType()], BooleanType())
        assert repr(ft) == '(数, 串) -> 布尔'

    def test_function_subtype_same_signature(self):
        f1 = FunctionType([NumberType()], BooleanType())
        f2 = FunctionType([NumberType()], BooleanType())
        assert f1.is_subtype_of(f2)

    def test_function_arity_mismatch_not_subtype(self):
        f1 = FunctionType([NumberType()], BooleanType())
        f2 = FunctionType([NumberType(), StringType()], BooleanType())
        assert not f1.is_subtype_of(f2)


class TestUnification:
    """类型合一（unify）"""

    def test_unify_same_basic(self):
        subs = unify(NumberType(), NumberType())
        assert isinstance(subs, TypeSubstitution)

    def test_unify_with_any_succeeds(self):
        subs = unify(NumberType(), AnyType())
        assert isinstance(subs, TypeSubstitution)

    def test_unify_type_var_binds(self):
        tv = TypeVar('T')
        subs = unify(tv, NumberType())
        assert subs['T'] == NumberType() or subs['T'] is NumberType()

    def test_unify_incompatible_raises(self):
        with pytest.raises(UnificationError):
            unify(NumberType(), StringType())

    def test_unify_lists(self):
        subs = unify(ListType(NumberType()), ListType(NumberType()))
        assert isinstance(subs, TypeSubstitution)

    def test_unify_functions(self):
        f1 = FunctionType([NumberType()], BooleanType())
        f2 = FunctionType([NumberType()], BooleanType())
        subs = unify(f1, f2)
        assert isinstance(subs, TypeSubstitution)

    def test_unification_error_message(self):
        try:
            unify(NumberType(), StringType())
        except UnificationError as e:
            assert '类型合一失败' in str(e)


class TestTypeParser:
    """TypeParser 字符串 → Type 解析"""

    def setup_method(self):
        self.parser = TypeParser()

    def test_parse_basic_number(self):
        t = self.parser.parse('数')
        assert t._type_id == TYPE_NUMBER._type_id

    def test_parse_alias_integers(self):
        """整数是 数 的别名"""
        t = self.parser.parse('整数')
        assert t._type_id == TYPE_NUMBER._type_id

    def test_parse_alias_text(self):
        """文本是 串 的别名"""
        t = self.parser.parse('文本')
        assert t._type_id == TYPE_STRING._type_id

    def test_parse_boolean(self):
        t = self.parser.parse('布尔')
        assert t._type_id == TYPE_BOOLEAN._type_id

    def test_parse_null(self):
        t = self.parser.parse('空')
        assert t._type_id == TYPE_NULL._type_id

    def test_parse_any(self):
        t = self.parser.parse('任意')
        assert t._type_id == TYPE_ANY._type_id

    def test_parse_list(self):
        t = self.parser.parse('列表[数]')
        assert t._type_id == 8  # TYPE_ID_LIST
        assert t.element_type._type_id == TYPE_NUMBER._type_id

    def test_parse_dict(self):
        t = self.parser.parse('字典[串: 数]')
        assert t._type_id == 9  # TYPE_ID_DICT
        assert t.key_type._type_id == TYPE_STRING._type_id
        assert t.value_type._type_id == TYPE_NUMBER._type_id

    def test_parse_optional(self):
        t = self.parser.parse('数|空')
        assert t._type_id == 7  # TYPE_ID_OPTIONAL

    def test_parse_function_with_parens_is_multi_param(self):
        """带括号的 (数, 串) -> 布尔：括号只是分组，等价于两参数函数

        口径以设计文档为准（docs/superpowers/specs/
        2026-07-01-level6-type-annotation-design.md：
        `(整数, 小数) -> 布尔  // 等价于 接收整数,小数返回布尔`）。
        TypeParser 的函数类型分支先剥外层括号，再按顶层逗号切分。
        单参元组要写 `元组[数, 串] -> 布尔`（见下一条）。
        """
        t = self.parser.parse('(数, 串) -> 布尔')
        assert t._type_id == 12  # TYPE_ID_FUNCTION
        assert len(t.param_types) == 2
        assert t.param_types[0]._type_id == TYPE_NUMBER._type_id
        assert t.param_types[1]._type_id == TYPE_STRING._type_id
        assert t.return_type._type_id == TYPE_BOOLEAN._type_id

    def test_parse_function_tuple_param_needs_tuple_syntax(self):
        """单参元组只能显式写 元组[...]：剥外层括号不该让元组参数无法表达"""
        t = self.parser.parse('元组[数, 串] -> 布尔')
        assert t._type_id == 12  # TYPE_ID_FUNCTION
        assert len(t.param_types) == 1
        assert t.param_types[0]._type_id == 10  # TYPE_ID_TUPLE
        assert t.return_type._type_id == TYPE_BOOLEAN._type_id

    def test_parse_function_multiple_params(self):
        """数, 串 -> 布尔：无括号时按逗号切分得到多参数函数"""
        t = self.parser.parse('数, 串 -> 布尔')
        assert t._type_id == 12  # TYPE_ID_FUNCTION
        assert len(t.param_types) == 2
        assert t.param_types[0]._type_id == TYPE_NUMBER._type_id
        assert t.param_types[1]._type_id == TYPE_STRING._type_id
        assert t.return_type._type_id == TYPE_BOOLEAN._type_id

    def test_parse_type_sugar_list(self):
        """中文语法糖：整数列表 → ListType(数)"""
        t = self.parser.parse('整数列表')
        assert t._type_id == 8
        assert t.element_type._type_id == TYPE_NUMBER._type_id

    def test_parse_type_sugar_dict(self):
        """中文语法糖：文本到整数字典 → DictType(串, 数)"""
        t = self.parser.parse('文本到整数字典')
        assert t._type_id == 9
        assert t.key_type._type_id == TYPE_STRING._type_id
        assert t.value_type._type_id == TYPE_NUMBER._type_id

    def test_parse_unknown_class_fallback(self):
        """未识别名称回退为 ClassType"""
        t = self.parser.parse('某自定义类')
        assert t._type_id == 16  # TYPE_ID_CLASS


class TestTypeSymbolTable:
    """类型符号表作用域与泛型参数"""

    def test_define_and_lookup(self):
        st = TypeSymbolTable()
        assert st.define('x', 'variable', NumberType()) is True
        sym = st.lookup('x')
        assert sym is not None
        assert sym.name == 'x'

    def test_define_duplicate_in_same_scope_fails(self):
        st = TypeSymbolTable()
        assert st.define('x', 'variable', NumberType()) is True
        assert st.define('x', 'variable', StringType()) is False

    def test_scope_nesting(self):
        st = TypeSymbolTable()
        st.define('外层', 'variable', NumberType())
        st.enter_scope()
        st.define('内层', 'variable', StringType())
        # 内层可看到外层
        assert st.lookup('外层') is not None
        assert st.lookup('内层') is not None
        st.exit_scope()
        # 退出后看不到内层
        assert st.lookup('内层') is None
        assert st.lookup('外层') is not None

    def test_generic_param(self):
        st = TypeSymbolTable()
        st.define_generic_param('T')
        resolved = st.resolve_type_param('T')
        assert resolved is not None
        assert resolved._type_id == 13  # TYPE_ID_TVAR


class TestTypeErrorInference:
    """类型推断异常"""

    def test_error_carries_message(self):
        err = TypeErrorInference('类型不匹配')
        assert '类型不匹配' in str(err)

    def test_error_with_line(self):
        err = TypeErrorInference('错误', line=42)
        assert '42' in str(err)


# =============================================================================
# 10. 泛型尖括号语法（D08 后续 3.2.2 类型系统增强）
# =============================================================================

class TestGenericAngleBracketParsing:
    """TypeParser 泛型尖括号语法：列表<整数> / 字典<字符串, 小数> / 可选<整数>"""

    def setup_method(self):
        self.parser = TypeParser()

    def test_list_angle(self):
        """列表<整数> → ListType(数)"""
        t = self.parser.parse('列表<整数>')
        assert t._type_id == 8  # TYPE_ID_LIST
        assert t.element_type._type_id == TYPE_NUMBER._type_id

    def test_dict_angle_comma(self):
        """字典<字符串, 小数> → DictType(串, 数)"""
        t = self.parser.parse('字典<字符串, 小数>')
        assert t._type_id == 9  # TYPE_ID_DICT
        assert t.key_type._type_id == TYPE_STRING._type_id
        assert t.value_type._type_id == TYPE_NUMBER._type_id

    def test_dict_angle_no_space(self):
        """字典<字符串,小数> 无空格逗号"""
        t = self.parser.parse('字典<字符串,小数>')
        assert t._type_id == 9
        assert t.key_type._type_id == TYPE_STRING._type_id
        assert t.value_type._type_id == TYPE_NUMBER._type_id

    def test_optional_angle(self):
        """可选<整数> → OptionalTypeWrapper(数)"""
        t = self.parser.parse('可选<整数>')
        assert isinstance(t, OptionalTypeWrapper)
        assert t.inner_type._type_id == TYPE_NUMBER._type_id

    def test_optional_angle_可空(self):
        """可空<串> → OptionalTypeWrapper(串)"""
        t = self.parser.parse('可空<串>')
        assert isinstance(t, OptionalTypeWrapper)
        assert t.inner_type._type_id == TYPE_STRING._type_id

    def test_nested_generic(self):
        """嵌套泛型：列表<列表<整数>>"""
        t = self.parser.parse('列表<列表<整数>>')
        assert t._type_id == 8
        assert t.element_type._type_id == 8  # 内层仍是列表
        assert t.element_type.element_type._type_id == TYPE_NUMBER._type_id

    def test_nested_dict_value(self):
        """字典<字符串, 列表<整数>>"""
        t = self.parser.parse('字典<字符串, 列表<整数>>')
        assert t._type_id == 9
        assert t.value_type._type_id == 8  # 值是列表
        assert t.value_type.element_type._type_id == TYPE_NUMBER._type_id

    def test_square_bracket_still_works(self):
        """方括号形式不回归：列表[整数]"""
        t = self.parser.parse('列表[整数]')
        assert t._type_id == 8
        assert t.element_type._type_id == TYPE_NUMBER._type_id


class TestGenericTypeCodegen:
    """泛型注解的完整管线：解析 → 类型推断 → 代码生成 → 执行"""

    SRC = '''
段落 处理列表 接收 数据: 列表<整数>:
    返回 列表长度(数据)

段落 主 接收:
    设 数据: 列表<整数> 为 [1, 2, 3]
    设 映射 为 字典<字符串, 小数> = {}
    设 可选值 为 可选<整数> = 空
    打印('泛型OK', 处理列表(数据), 可选值)
    返回 0
主()
'''

    @staticmethod
    def _compile(src):
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        parser = LightParser()
        module = parser.parse(src)
        assert getattr(parser, 'errors', []) == [], getattr(parser, 'errors', [])
        return PythonCodeGenerator().generate(module)

    def test_parse_no_errors(self):
        from light_parser_v3 import LightParser
        parser = LightParser()
        parser.parse(self.SRC)
        assert getattr(parser, 'errors', []) == []

    def test_codegen_valid_python(self):
        py = self._compile(self.SRC)
        # 泛型注解必须映射为 Python 合法类型，而非原样输出 < >
        assert '列表<' not in py
        assert 'list[int]' in py or 'list[float]' in py
        compile(py, '<duan-generics>', 'exec')

    def test_execute_success(self):
        py = self._compile(self.SRC)
        ns = {}
        exec(py, ns)

    def test_optional_null_assignment_no_error(self):
        """可选<整数> 赋值为空：空安全检查不报错"""
        src = '''
段落 主 接收:
    设 可选值 为 可选<整数> = 空
    打印(可选值)
主()
'''
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        parser = LightParser()
        module = parser.parse(src)
        assert getattr(parser, 'errors', []) == []
        py = PythonCodeGenerator().generate(module)
        ns = {}
        exec(py, ns)


class TestGenericTypeInference:
    """泛型注解的类型推断：可声明、可推断、可传递"""

    @staticmethod
    def _infer_src(src):
        from compiler import LightCompiler
        c = LightCompiler()
        result = c.compile(src)
        return result

    def test_paragraph_signature(self):
        """段落参数 列表<整数> → 函数类型 (列表[数]) -> 数"""
        src = '''
段落 处理列表 接收 数据: 列表<整数>:
    返回 列表长度(数据)

段落 主 接收:
    设 数据: 列表<整数> 为 [1, 2, 3]
    处理列表(数据)
主()
'''
        result = self._infer_src(src)
        assert result['errors'] == [], result['errors']
        inf = result['inferencer']
        sym = inf.symbol_table.lookup('处理列表')
        assert sym is not None
        ft = sym.data_type
        assert ft._type_id == 12  # TYPE_ID_FUNCTION
        assert len(ft.param_types) == 1
        assert ft.param_types[0]._type_id == 8  # 列表
        assert ft.param_types[0].element_type._type_id == TYPE_NUMBER._type_id
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_optional_type_inferred(self):
        """可选<整数> 推断为 OptionalTypeWrapper（经段落返回类型传播）"""
        src = '''
段落 主 接收:
    设 可选值 为 可选<整数> = 空
    返回 可选值
主()
'''
        result = self._infer_src(src)
        assert result['errors'] == [], result['errors']
        inf = result['inferencer']
        sym = inf.symbol_table.lookup('主')
        assert sym is not None
        ft = sym.data_type
        assert ft._type_id == 12  # TYPE_ID_FUNCTION
        assert isinstance(ft.return_type, OptionalTypeWrapper)
        assert ft.return_type.inner_type._type_id == TYPE_NUMBER._type_id

    def test_non_nullable_null_rejected(self):
        """整数 赋值为空 → 空安全错误"""
        src = '''
段落 主 接收:
    设 值 为 整数 = 空
    打印(值)
主()
'''
        result = self._infer_src(src)
        assert any('空安全' in e for e in result['errors']), result['errors']

    def test_generic_flow_through_call(self):
        """泛型注解在调用链中传递：列表<整数> 传入后返回长度"""
        src = '''
段落 处理列表 接收 数据: 列表<整数>:
    返回 列表长度(数据)

段落 包装 接收 数据: 列表<整数>:
    返回 处理列表(数据)

段落 主 接收:
    设 数据: 列表<整数> 为 [1, 2, 3]
    打印(包装(数据))
主()
'''
        result = self._infer_src(src)
        assert result['errors'] == [], result['errors']


# =============================================================================
# 11. 可空类型 unwrap 系统（3.2.2：安全解包、空值传播）
# =============================================================================

class TestNullableUnwrap:
    """可选<整数> 安全解包：值! / unwrap() / 判空比较 / 空值传播"""

    @staticmethod
    def _run(src, expect_errors=0):
        from compiler import LightCompiler
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        c = LightCompiler()
        result = c.compile(src)
        errors = result['errors']
        if expect_errors:
            assert len(errors) >= expect_errors, errors
            return None
        assert errors == [], errors
        m = LightParser().parse(src)
        py = PythonCodeGenerator().generate(m)
        ns = {}
        exec(py, ns)

    def test_unwrap_bang(self):
        """值! 解包后参与运算"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 5
    设 y 为 x! 加 1
    打印(y)
主()
''')

    def test_unwrap_function_form(self):
        """unwrap(值) 函数形式解包"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 7
    设 y 为 unwrap(x) 加 1
    打印(y)
主()
''')

    def test_unwrap_null_raises_assert(self):
        """空值! 解包 → 运行时断言失败"""
        src = '''
段落 主 接收:
    设 x 为 可选<整数> = 空
    设 y 为 x! 加 1
    打印(y)
主()
'''
        # 编译应无类型错误；运行时尝试解包空值应失败
        from compiler import LightCompiler
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        c = LightCompiler()
        assert c.compile(src)['errors'] == []
        py = PythonCodeGenerator().generate(LightParser().parse(src))
        try:
            exec(py, {})
        except AssertionError:
            return
        raise AssertionError("空值解包应触发断言失败")

    def test_null_compare_等于(self):
        """可选值 == 空 判空合法"""
        self._run('''
段落 取非空 接收 v: 可选<整数>:
    如果 v 等于 空：
        返回 0
    返回 v!
段落 主 接收:
    打印(取非空(空))
    打印(取非空(9))
主()
''')

    def test_null_compare_不等于(self):
        """可选值 != 空 判空合法"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 3
    如果 x 不等于 空：
        打印(x!)
    否则：
        打印('空')
主()
''')

    def test_null_compare_value(self):
        """判空+解包模式：空→0，非空→原值"""
        self._run('''
段落 取非空 接收 v: 可选<整数>:
    设 结果 为 0
    如果 v 不等于 空：
        设 结果 为 v!
    返回 结果
段落 主 接收:
    打印(取非空(空))
    打印(取非空(9))
主()
''')

    def test_optional_param_accepts_null(self):
        """可空形参可接收 空 与普通值"""
        self._run('''
段落 打印可选 接收 v: 可选<整数>:
    打印(v)
段落 主 接收:
    打印可选(空)
    打印可选(3)
主()
''')

    def test_optional_flows_between_vars(self):
        """空值传播：可选值赋给另一可选变量"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 空
    设 y 为 可选<整数> = x
    打印(y)
主()
''')

    def test_unwrapped_operation_rejected(self):
        """未解包参与运算 → 类型错误"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 5
    设 y 为 x 加 1
    打印(y)
主()
''', expect_errors=1)

    def test_unwrapped_argument_rejected(self):
        """未解包传给非可空参数 → 类型错误"""
        self._run('''
段落 双倍 接收 n: 整数:
    返回 n 乘 2
段落 主 接收:
    设 x 为 可选<整数> = 4
    打印(双倍(x))
主()
''', expect_errors=1)

    def test_optional_in_condition_rejected(self):
        """可选值直接作条件 → 类型错误（须显式判空）"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 空
    如果 x：
        打印('真')
    否则：
        打印('假')
主()
''', expect_errors=1)

    def test_optional_assign_non_null(self):
        """可选<整数> = 5 合法（unify 可选与内部类型兼容）"""
        self._run('''
段落 主 接收:
    设 x 为 可选<整数> = 5
    打印(x!)
主()
''')

    def test_nested_optional_list(self):
        """列表<可选<整数>> 嵌套泛型"""
        self._run('''
段落 主 接收:
    设 数据 为 列表<可选<整数>> = [1, 空, 3]
    打印(列表长度(数据))
    设 首值 为 数据[0]!
    打印(首值)
主()
''')

    def test_unify_optional_with_inner(self):
        """unify(可选<数>, 数) 成功（可空兼容合一）"""
        from type_system import unify, OptionalTypeWrapper, NumberType, TypeSubstitution
        opt = OptionalTypeWrapper(NumberType())
        subs = unify(opt, NumberType())
        assert isinstance(subs, TypeSubstitution)

    def test_compiler_errors_reset_across_compile(self):
        """LightCompiler 重复 compile 不累积上次错误"""
        from compiler import LightCompiler
        c = LightCompiler()
        bad = '''
段落 主 接收:
    设 x 为 可选<整数> = 5
    设 y 为 x 加 1
    打印(y)
主()
'''
        good = '''
段落 主 接收:
    打印('OK')
主()
'''
        c.compile(bad)
        good_result = c.compile(good)
        assert good_result['errors'] == [], good_result['errors']


# =============================================================================
# 12. 类型场景集成测试（3.2.2：类型检查器 + 推断引擎，覆盖 50+ 类型场景）
# =============================================================================

class _TypeScenarioBase:
    """类型场景集成测试基类：真实段言源码 → LightCompiler 编译 → 推断/执行断言"""

    @staticmethod
    def _compile(src):
        from compiler import LightCompiler
        c = LightCompiler()
        return c.compile(src)

    @staticmethod
    def _exec(src):
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator
        py = PythonCodeGenerator().generate(LightParser().parse(src))
        ns = {}
        exec(py, ns)

    def _ok(self, src):
        """编译无错误且可执行"""
        r = self._compile(src)
        assert r['errors'] == [], r['errors']
        self._exec(src)

    def _err(self, src, keyword):
        """编译应报含 keyword 的类型错误"""
        r = self._compile(src)
        assert any(keyword in str(e) for e in r['errors']), r['errors']

    def _sig(self, src, seg_name):
        """返回段落推断的函数类型（模块级符号）"""
        r = self._compile(src)
        assert r['errors'] == [], r['errors']
        sym = r['inferencer'].symbol_table.lookup(seg_name)
        assert sym is not None, f"未找到段落 {seg_name}"
        return sym.data_type


class TestTypeScenarioBasic(_TypeScenarioBase):
    """基本类型推断场景"""

    def test_integer_literal_type(self):
        ft = self._sig('''
段落 取数 接收:
    返回 42
段落 主 接收:
    打印(取数())
主()
''', '取数')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_float_literal_type(self):
        ft = self._sig('''
段落 取数 接收:
    返回 3.14
段落 主 接收:
    打印(取数())
主()
''', '取数')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_string_literal_type(self):
        ft = self._sig('''
段落 取串 接收:
    返回 '你好'
段落 主 接收:
    打印(取串())
主()
''', '取串')
        assert ft.return_type._type_id == TYPE_STRING._type_id

    def test_boolean_literal_type(self):
        ft = self._sig('''
段落 取布尔 接收:
    返回 真
段落 主 接收:
    打印(取布尔())
主()
''', '取布尔')
        assert ft.return_type._type_id == TYPE_BOOLEAN._type_id

    def test_null_literal_type(self):
        ft = self._sig('''
段落 取空 接收:
    返回 空
段落 主 接收:
    打印(取空())
主()
''', '取空')
        assert ft.return_type._type_id == TYPE_NULL._type_id

    def test_arithmetic_result_type(self):
        ft = self._sig('''
段落 计算 接收:
    返回 1 加 2 乘 3
段落 主 接收:
    打印(计算())
主()
''', '计算')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_string_concat_type(self):
        ft = self._sig('''
段落 拼接 接收:
    返回 'a' 加 'b'
段落 主 接收:
    打印(拼接())
主()
''', '拼接')
        assert ft.return_type._type_id == TYPE_STRING._type_id

    def test_compare_result_boolean(self):
        ft = self._sig('''
段落 比较 接收:
    返回 5 大于 3
段落 主 接收:
    打印(比较())
主()
''', '比较')
        assert ft.return_type._type_id == TYPE_BOOLEAN._type_id

    def test_annotation_mismatch_rejected(self):
        self._err('''
段落 主 接收:
    设 x 为 整数 = '字符串'
    打印(x)
主()
''', '类型不匹配')

    def test_variable_annotation_ok(self):
        self._ok('''
段落 主 接收:
    设 x 为 整数 = 10
    打印(x)
主()
''')


class TestTypeScenarioComposite(_TypeScenarioBase):
    """复合类型推断场景"""

    def test_list_literal_type(self):
        ft = self._sig('''
段落 构建 接收:
    设 数据 为 [1, 2, 3]
    返回 数据
段落 主 接收:
    打印(构建())
主()
''', '构建')
        assert ft.return_type._type_id == 8  # 列表
        assert ft.return_type.element_type._type_id == TYPE_NUMBER._type_id

    def test_list_string_type(self):
        ft = self._sig('''
段落 构建 接收:
    设 数据 为 ['a', 'b']
    返回 数据
段落 主 接收:
    打印(构建())
主()
''', '构建')
        assert ft.return_type._type_id == 8
        assert ft.return_type.element_type._type_id == TYPE_STRING._type_id

    def test_empty_list_type(self):
        ft = self._sig('''
段落 构建 接收:
    设 数据 为 []
    返回 数据
段落 主 接收:
    打印(构建())
主()
''', '构建')
        assert ft.return_type._type_id == 8

    def test_list_index_type(self):
        ft = self._sig('''
段落 取元素 接收:
    设 数据 为 [10, 20, 30]
    返回 数据[1]
段落 主 接收:
    打印(取元素())
主()
''', '取元素')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_list_append_ok(self):
        self._ok('''
段落 主 接收:
    设 数据 为 [1, 2]
    设 数据 为 数据 加 [3]
    打印(列表长度(数据))
主()
''')

    def test_list_length_number(self):
        ft = self._sig('''
段落 取长 接收:
    设 数据 为 [1, 2, 3]
    返回 列表长度(数据)
段落 主 接收:
    打印(取长())
主()
''', '取长')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_dict_literal_ok(self):
        self._ok('''
段落 主 接收:
    设 映射 为 {'a': 1, 'b': 2}
    打印(映射['a'])
主()
''')

    def test_dict_generic_annotation(self):
        ft = self._sig('''
段落 建映射 接收:
    设 映射: 字典<字符串, 整数> 为 {}
    返回 映射
段落 主 接收:
    打印(建映射())
主()
''', '建映射')
        assert ft.return_type._type_id == 9  # 字典

    def test_list_generic_annotation(self):
        ft = self._sig('''
段落 建列表 接收:
    设 数据: 列表<串> 为 ['x']
    返回 数据
段落 主 接收:
    打印(建列表())
主()
''', '建列表')
        assert ft.return_type._type_id == 8
        assert ft.return_type.element_type._type_id == TYPE_STRING._type_id

    def test_list_mismatch_rejected(self):
        self._err('''
段落 主 接收:
    设 x: 列表<整数> 为 ['str']
    打印(x)
主()
''', '类型不匹配')


class TestTypeScenarioSegment(_TypeScenarioBase):
    """段落/函数类型推断场景"""

    def test_param_annotation_signature(self):
        ft = self._sig('''
段落 双倍 接收 n: 整数:
    返回 n 乘 2
段落 主 接收:
    打印(双倍(4))
主()
''', '双倍')
        assert ft._type_id == 12  # 函数类型
        assert len(ft.param_types) == 1
        assert ft.param_types[0]._type_id == TYPE_NUMBER._type_id
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_return_annotation(self):
        ft = self._sig('''
段落 取串 接收 -> 串:
    返回 'abc'
段落 主 接收:
    打印(取串())
主()
''', '取串')
        assert ft.return_type._type_id == TYPE_STRING._type_id

    def test_inferred_return_no_annotation(self):
        ft = self._sig('''
段落 取数 接收:
    返回 7
段落 主 接收:
    打印(取数())
主()
''', '取数')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_multi_return_unified(self):
        ft = self._sig('''
段落 选择 接收 标记: 布尔:
    如果 标记：
        返回 1
    返回 2
段落 主 接收:
    打印(选择(真))
主()
''', '选择')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_recursion(self):
        ft = self._sig('''
段落 阶乘 接收 n: 整数:
    如果 n 小于等于 1：
        返回 1
    返回 n 乘 阶乘(n 减 1)
段落 主 接收:
    打印(阶乘(5))
主()
''', '阶乘')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id

    def test_wrong_arity_rejected(self):
        self._err('''
段落 双参 接收 a, b:
    返回 a 加 b
段落 主 接收:
    打印(双参(1))
主()
''', '参数')

    def test_wrong_param_type_rejected(self):
        self._err('''
段落 双倍 接收 n: 整数:
    返回 n 乘 2
段落 主 接收:
    打印(双倍('abc'))
主()
''', '类型不匹配')

    def test_wrong_return_type_rejected(self):
        self._err('''
段落 坏 接收 -> 整数:
    返回 'str'
段落 主 接收:
    打印(坏())
主()
''', '返回类型不匹配')

    def test_no_return_is_null(self):
        ft = self._sig('''
段落 执行任务 接收:
    打印('hi')
段落 主 接收:
    执行任务()
主()
''', '执行任务')
        assert ft.return_type._type_id == TYPE_NULL._type_id

    def test_nested_call_flow(self):
        self._ok('''
段落 内层 接收 n: 整数:
    返回 n 加 1
段落 外层 接收 n: 整数:
    返回 内层(n) 乘 2
段落 主 接收:
    打印(外层(3))
主()
''')

    def test_void_segment_callable(self):
        self._ok('''
段落 问候 接收:
    打印('你好')
段落 主 接收:
    问候()
    问候()
主()
''')


class TestTypeScenarioControlFlow(_TypeScenarioBase):
    """控制流类型推断场景"""

    def test_if_compare_condition(self):
        self._ok('''
段落 主 接收:
    如果 5 大于 3：
        打印('大')
    否则：
        打印('小')
主()
''')

    def test_if_boolean_var_condition(self):
        self._ok('''
段落 主 接收:
    设 标记 为 真
    如果 标记：
        打印('真')
主()
''')

    def test_elseif_chain(self):
        ft = self._sig('''
段落 分级 接收 n: 整数:
    如果 n 大于 90：
        返回 'A'
    否则若 n 大于 80：
        返回 'B'
    否则：
        返回 'C'
段落 主 接收:
    打印(分级(85))
主()
''', '分级')
        assert ft.return_type._type_id == TYPE_STRING._type_id

    def test_while_loop(self):
        self._ok('''
段落 求和 接收 n: 整数:
    设 结果 为 0
    设 i 为 1
    当 i 小于等于 n：
        设 结果 为 结果 加 i
        设 i 为 i 加 1
    返回 结果
段落 主 接收:
    打印(求和(10))
主()
''')

    def test_foreach_loop(self):
        self._ok('''
段落 求和 接收 数据: 列表<整数>:
    设 结果 为 0
    遍历 元素 于 数据：
        设 结果 为 结果 加 元素
    返回 结果
段落 主 接收:
    打印(求和([1, 2, 3]))
主()
''')

    def test_loop_return_type(self):
        ft = self._sig('''
段落 求和 接收 n: 整数:
    设 结果 为 0
    设 i 为 1
    当 i 小于等于 n：
        设 结果 为 结果 加 i
        设 i 为 i 加 1
    返回 结果
段落 主 接收:
    打印(求和(10))
主()
''', '求和')
        assert ft.return_type._type_id == TYPE_NUMBER._type_id


class TestTypeScenarioClass(_TypeScenarioBase):
    """类类型推断场景"""

    SRC_COUNTER = '''
类 计数器：
    属性 当前。
    构造 接收 初值：
        己当前 为 初值
    段落 增加：
        己当前 为 己当前 加 1
    段落 读取：
        返回 己当前
段落 主 接收:
    设 计数 为 新建 计数器(5)
    计数.增加()
    计数.增加()
    打印(计数.读取())
主()
'''

    def test_class_instantiation(self):
        self._ok(self.SRC_COUNTER)

    def test_class_type_symbol(self):
        r = self._compile(self.SRC_COUNTER)
        sym = r['inferencer'].symbol_table.lookup('计数器')
        assert sym is not None
        assert sym.data_type.class_name == '计数器'

    def test_method_call_result(self):
        self._ok('''
类 计算器：
    段落 双倍 接收 n: 整数：
        返回 n 乘 2
段落 主 接收:
    设 工具 为 新建 计算器()
    打印(工具.双倍(21))
主()
''')

    def test_inheritance(self):
        self._ok('''
类 动物：
    属性 名称。
    构造 接收 名字：
        己名称 为 名字
    段落 叫声：
        返回 '...'
类 狗 继承 动物：
    段落 叫声：
        返回 '汪汪'
段落 主 接收:
    设 狗子 为 新建 狗('旺财')
    打印(狗子.叫声())
主()
''')

    def test_static_attribute(self):
        self._ok('''
类 工具：
    静态 属性 版本 等于 '1.0'
段落 主 接收:
    打印(工具.版本)
主()
''')

    def test_class_field_annotation(self):
        self._ok('''
类 人：
    属性 姓名。
    构造 接收 名字: 串：
        己姓名 为 名字
段落 主 接收:
    设 某人 为 新建 人('张三')
    打印(某人.姓名)
主()
''')


class TestTypeScenarioChecker(_TypeScenarioBase):
    """类型检查器配置分级场景（GradedTypeChecker 独立路径）"""

    @staticmethod
    def _make_var_body(annotated=False):
        from ast_nodes_v3 import VarDecl, NumberLiteral
        return [VarDecl('未注解变量', NumberLiteral(1), type_annotation='整数' if annotated else None)]

    @staticmethod
    def _make_conflict_body():
        """注解为整数、实际赋字符串——light 语义下唯一会触发 V001 的形态"""
        from ast_nodes_v3 import VarDecl, StringLiteral
        return [VarDecl('冲突变量', StringLiteral('十'), type_annotation='整数')]

    def test_none_level_skips(self):
        from type_checker import GradedTypeChecker, TypeCheckerConfig
        from core.config import TypeCheckLevel
        seg = _make_segment('段落一', self._make_var_body())
        checker = GradedTypeChecker(TypeCheckerConfig(check_level=TypeCheckLevel.NONE))
        assert checker.check(_make_module(seg), inferencer=None) == []

    # 口径变更(v7 合并)：VARIABLE 档以 light 现行实现为准——只对「注解与推断类型冲突」告警，不对缺注解告警。原 duan 期望「缺注解→告警」已废止。
    def test_variable_level_warns_on_conflict(self):
        from type_checker import GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity
        from core.config import TypeCheckLevel, SegmentTypeMode
        config = TypeCheckerConfig(check_level=TypeCheckLevel.VARIABLE,
                                   default_segment_mode=SegmentTypeMode.LOOSE)
        seg = _make_segment('段落一', self._make_conflict_body())
        results = GradedTypeChecker(config).check(_make_module(seg), inferencer=None)
        warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
        assert len(warnings) == 1
        assert warnings[0].code == 'V001'
        assert '冲突变量' in warnings[0].message

    # 口径变更(v7 合并)：VARIABLE 档以 light 现行实现为准——只对「注解与推断类型冲突」告警，不对缺注解告警。原 duan 期望「缺注解→告警」已废止。
    def test_variable_level_silent_on_missing_annotation(self):
        from type_checker import GradedTypeChecker, TypeCheckerConfig
        from core.config import TypeCheckLevel, SegmentTypeMode
        config = TypeCheckerConfig(check_level=TypeCheckLevel.VARIABLE,
                                   default_segment_mode=SegmentTypeMode.LOOSE)
        seg = _make_segment('段落一', self._make_var_body())
        results = GradedTypeChecker(config).check(_make_module(seg), inferencer=None)
        assert [r for r in results if r.code == 'V001'] == []
        assert [r for r in results if '未注解变量' in r.message] == []

    def test_variable_level_annotated_no_warn(self):
        from type_checker import GradedTypeChecker, TypeCheckerConfig, TypeErrorSeverity
        from core.config import TypeCheckLevel, SegmentTypeMode
        seg = _make_segment('段落一', self._make_var_body(annotated=True))
        config = TypeCheckerConfig(check_level=TypeCheckLevel.VARIABLE,
                                   default_segment_mode=SegmentTypeMode.LOOSE)
        results = GradedTypeChecker(config).check(_make_module(seg), inferencer=None)
        warnings = [r for r in results if r.severity == TypeErrorSeverity.WARNING]
        assert warnings == []

    def test_signature_level_no_variable_check(self):
        from type_checker import GradedTypeChecker, TypeCheckerConfig
        from core.config import TypeCheckLevel, SegmentTypeMode
        seg = _make_segment('段落一', self._make_conflict_body())
        config = TypeCheckerConfig(check_level=TypeCheckLevel.SIGNATURE,
                                   default_segment_mode=SegmentTypeMode.LOOSE)
        results = GradedTypeChecker(config).check(_make_module(seg), inferencer=None)
        # 同样的注解冲突在 VARIABLE 档会产出 V001，SIGNATURE 档不应触发变量级检查
        assert [r for r in results if r.code == 'V001'] == []

    def test_file_directive_parse(self):
        from type_checker import _extract_type_directives
        source = '# 类型检查级别: 签名\n段落 主 接收:\n    打印(1)\n'
        directives = _extract_type_directives(source)
        assert '类型检查级别' in directives  # 能提取到类型指令
        assert directives['类型检查级别'] == '签名'

    def test_check_level_ordering(self):
        from core.config import TypeCheckLevel
        assert TypeCheckLevel.NONE.value < TypeCheckLevel.SIGNATURE.value
        assert TypeCheckLevel.SIGNATURE.value < TypeCheckLevel.VARIABLE.value
        assert TypeCheckLevel.VARIABLE.value < TypeCheckLevel.EXPRESSION.value
