"""
光明（Light）编程语言 - 增强类型推断器（Phase 1 版本）

特点：
- 完整的类型系统：基本类型、复合类型、泛型类型、类类型、接口类型
- 基于合一（unification）的类型变量解析
- 泛型段落（函数）的类型参数推断
- 泛型类实例化
- 局部变量类型推断
- 函数返回类型推断
"""

import sys
import os
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# 统一类型系统（Phase 1 增强版）
from type_system import (
    Type, NumberType, StringType, BooleanType, NullType,
    AnyType, UnknownType, OptionalTypeWrapper, UnionType,
    ListType, DictType, TupleType, SetType,
    FunctionType, TypeVar, GenericTypeInstance, GenericTypeDef,
    ClassType, InterfaceType, EnumType, FutureType,
    TypeSubstitution, UnificationError, unify, TypeParser,
    TypedSymbol, TypeSymbolTable, TypeErrorInference,
    TYPE_NUMBER, TYPE_STRING, TYPE_BOOLEAN, TYPE_NULL, TYPE_UNKNOWN, TYPE_ANY,
    TYPE_ID_NUMBER, TYPE_ID_STRING, TYPE_ID_BOOLEAN, TYPE_ID_NULL,
    TYPE_ID_LIST, TYPE_ID_DICT,
)

# 导入统一 AST 节点定义
from ast_nodes import (
    VariableDeclaration, Assignment, IfStatement, ForeachStatement,
    WhileStatement, BreakStatement, ContinueStatement, ReturnStatement,
    TryStatement, ThrowStatement, PrintStatement, ExpressionStatement,
    NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
    Identifier, SegmentName, BinaryOp, UnaryOp, FunctionCall,
    PropertyAccess, IndexAccess, ListLiteral, DictLiteral, DictEntry,
    NewExpression, SelfReference, SegmentDefinition, ClassDefinition,
    MethodDefinition, ConstructorDefinition, Parameter,
    Module, ListComprehension, LambdaExpression, StringInterpolation,
    ConditionalExpression, PipeExpression, MatchStatement, MatchCase, MatchPattern,
    AwaitExpression, DeferStatement, AsyncScope,
    EnumDefinition, EnumVariant, DataTypeField,
    TraitDefinition, TraitMethodSignature, TraitImplementation,
    TypeAlias, OptionalType as ASTOptionalType, UnwrapExpression,
    AST_TYPE_ID_NUMBER_LITERAL, AST_TYPE_ID_STRING_LITERAL,
    AST_TYPE_ID_BOOLEAN_LITERAL, AST_TYPE_ID_NULL_LITERAL,
    AST_TYPE_ID_SELF_REFERENCE, AST_TYPE_ID_IDENTIFIER,
    AST_TYPE_ID_BINARY_OP, AST_TYPE_ID_UNARY_OP, AST_TYPE_ID_FUNCTION_CALL,
    AST_TYPE_ID_PIPE_EXPRESSION, AST_TYPE_ID_PROPERTY_ACCESS,
    AST_TYPE_ID_INDEX_ACCESS, AST_TYPE_ID_LIST_LITERAL,
    AST_TYPE_ID_DICT_LITERAL, AST_TYPE_ID_NEW_EXPRESSION,
    AST_TYPE_ID_CONDITIONAL_EXPRESSION, AST_TYPE_ID_STRING_INTERPOLATION,
    AST_TYPE_ID_LIST_COMPREHENSION, AST_TYPE_ID_LAMBDA_EXPRESSION,
    AST_TYPE_ID_MATCH_STATEMENT, AST_TYPE_ID_DICT_COMPREHENSION,
    AST_TYPE_ID_VARIABLE_DECLARATION, AST_TYPE_ID_ASSIGNMENT,
    AST_TYPE_ID_IF_STATEMENT, AST_TYPE_ID_FOREACH_STATEMENT,
    AST_TYPE_ID_WHILE_STATEMENT, AST_TYPE_ID_RETURN_STATEMENT,
    AST_TYPE_ID_PRINT_STATEMENT, AST_TYPE_ID_EXPRESSION_STATEMENT,
    AST_TYPE_ID_THROW_STATEMENT, AST_TYPE_ID_DEFER_STATEMENT,
    AST_TYPE_ID_ASYNC_SCOPE, AST_TYPE_ID_SEGMENT_DEFINITION,
    AST_TYPE_ID_AWAIT_EXPRESSION, AST_TYPE_ID_UNWRAP_EXPRESSION,
)


# =============================================================================
# 辅助：检查节点实例
# =============================================================================

# =============================================================================
# 类型推断器
# =============================================================================

@dataclass
class InferenceResult:
    """单个表达式的推断结果（类型 + 相关的替换）"""
    inferred_type: Type
    substitution: TypeSubstitution = field(default_factory=TypeSubstitution)


@dataclass
class SegmentCacheEntry:
    """段推断缓存条目（增量推断用）"""
    source_hash: str        # 段体源码哈希
    dep_type_hashes: Dict[str, str] = field(default_factory=dict)  # 依赖段名 → 依赖段类型哈希
    result_type: Optional[FunctionType] = None  # 缓存推断结果
    # 依赖此段的段名集合（用于级联失效）
    reverse_deps: Set[str] = field(default_factory=set)


class TypeInferencer:
    """光明增强类型推断器（Phase 1 版本）"""

    def __init__(self):
        self.symbol_table = TypeSymbolTable()
        self.type_cache: Dict[int, Type] = {}
        self.errors: List[str] = []
        # 结构化错误列表（携带位置信息）
        self._typed_errors: List[TypeErrorInference] = []

        # 注册内置类型
        self._init_builtin_types()

        # 当前正在推断的函数返回类型
        self._current_return_type: Optional[Type] = None

        # 是否在异步函数中
        self._in_async_function: bool = False

        # 已知的枚举定义（名称 → EnumType）
        self.enum_defs: Dict[str, EnumType] = {}

        # 已知的 trait/接口定义（名称 → InterfaceType/TraitType）
        self.trait_defs: Dict[str, InterfaceType] = {}

        # 泛型类定义：名称 → 泛型参数名列表
        self.generic_class_defs: Dict[str, List[str]] = {}

        # 泛型段落定义：名称 → 泛型参数名列表
        self.generic_segment_defs: Dict[str, List[str]] = {}

        # 泛型类实例化记录（名称 → 类型参数列表）—— 用于辅助测试
        self.generic_class_instances: Dict[str, List[Type]] = {}

        # 方法预扫描缓存：(类名, 方法名) → FunctionType
        self._method_pre_scan_cache: Dict[Tuple[str, str], FunctionType] = {}

        # HM 推断阶段：在段体推断期间累积的替换（用于反馈到段签名）
        self._hm_subs: Optional[TypeSubstitution] = None

        # 调用图：段名 → 被调用段名集合（用于拓扑排序优化）
        self._call_graph: Dict[str, Set[str]] = {}

        # 增量推断缓存：段名 → 缓存条目
        self._segment_cache: Dict[str, SegmentCacheEntry] = {}
        self._incremental: bool = False

        # ⭐ 并行推断配置
        self._parallel: bool = False
        self._max_workers: int = 4

        # trait 实现（(trait名, 类型名) → 方法名 → FunctionType）
        self.trait_impls: Dict[Tuple[str, str], Dict[str, FunctionType]] = {}

        # 类型字符串解析器
        self.type_parser = TypeParser(self.symbol_table)

        # 当前正在处理的 module（用于类定义查找）
        self.module = None

        # 收集函数体中的返回语句类型（用于推断未声明的返回类型）
        self._collected_return_types: List[Type] = []

        # 解构赋值跟踪（解构 (x, y) = expr）
        self._destructure_target: Optional[Tuple[str, ...]] = None

        # 类型别名注册表：名称 → 目标类型字符串
        self.type_aliases: Dict[str, str] = {}

    # ---- 内置类型初始化 ----
    def _init_builtin_types(self):
        """初始化内置类型"""
        self._builtin_type_names = {'数', '串', '布尔', '空', '列表', '字典', '任意', '元组', '集合'}

    def _add_error(self, message: str, node=None, line: int = 0, col: int = 0):
        """添加类型错误（同时更新结构化错误列表和字符串列表）"""
        err = TypeErrorInference(message, node, line, col)
        self._typed_errors.append(err)
        self.errors.append(str(err))

    # ---- 类型字符串解析 ----
    def _parse_type_string(self, type_str) -> Type:
        """将类型字符串解析为 Type 对象"""
        if type_str is None:
            return TYPE_ANY
        # 解析类型别名引用
        resolved = self._resolve_type_alias(type_str)
        return self.type_parser.parse(resolved)

    # ---- 注册枚举 ----
    def register_enum(self, enum_def: EnumDefinition):
        """注册枚举类型"""
        variants = {}
        for variant in enum_def.variants:
            field_types = [self._parse_type_string(f.type_annotation) for f in variant.fields]
            variants[variant.name] = field_types

        enum_type = EnumType(
            enum_name=enum_def.name,
            variants=variants,
            generic_params=list(getattr(enum_def, 'generic_params', []) or []),
        )
        self.enum_defs[enum_def.name] = enum_type
        self.symbol_table.define(enum_def.name, 'enum', enum_type)

    # ---- 注册 Trait/接口 ----
    def register_trait(self, trait_def: TraitDefinition):
        """注册 trait 定义"""
        methods = {}
        for method in trait_def.methods:
            param_types = [self._parse_type_string(p.type_annotation) for p in method.parameters]
            return_type = self._parse_type_string(method.return_type)
            methods[method.name] = FunctionType(param_types, return_type)

        iface = InterfaceType(interface_name=trait_def.name, methods=methods)
        self.trait_defs[trait_def.name] = iface

    # ---- 注册 InterfaceDefinition（中文命名） ----
    def register_interface(self, iface_def):
        """注册接口定义（InterfaceDefinition 节点）"""
        methods = {}
        for method in iface_def.methods:
            param_types = [self._parse_type_string(p.type_annotation) for p in method.parameters]
            return_type = self._parse_type_string(method.return_type)
            methods[method.name] = FunctionType(param_types, return_type)

        iface = InterfaceType(interface_name=iface_def.name, methods=methods)
        self.trait_defs[iface_def.name] = iface

    # ---- 注册 Trait/接口 实现 ----
    def register_trait_impl(self, impl: TraitImplementation):
        """注册 trait 实现并检查方法是否完整且签名匹配"""
        key = (impl.trait_name, impl.type_name)
        methods = {}
        for method in impl.methods:
            param_types = [self._parse_type_string(p.type_annotation) for p in method.parameters]
            return_type = self._parse_type_string(method.return_type)
            methods[method.name] = FunctionType(param_types, return_type)
        self.trait_impls[key] = methods

        # 类型实现 trait 检查（方法存在性 + 签名匹配）
        if impl.trait_name in self.trait_defs:
            required = self.trait_defs[impl.trait_name]
            for method_name, func_type in required.methods.items():
                if method_name not in methods:
                    self._add_error(
                        f"类型 '{impl.type_name}' 未实现接口 '{impl.trait_name}' "
                        f"的必需方法 '{method_name}'",
                        node=impl
                    )
                else:
                    # 签名匹配检查
                    actual_ft = methods[method_name]
                    err = required.method_signature_matches(method_name, actual_ft)
                    if err:
                        self._add_error(f"类型 '{impl.type_name}' 实现接口 '{impl.trait_name}': {err}", node=impl)

    # ---- 主推断入口（HM 两阶段） ----
    def infer(self, module: Module, incremental: bool = False) -> Dict[int, Type]:
        """对整个模块进行类型推断（HM 风格两阶段：预扫描 + 推断 + 泛化）

        Args:
            module: 要推断的模块
            incremental: 是否启用增量推断缓存（IDE 场景下可大幅提速）
        """
        self.type_cache = {}
        self.symbol_table = TypeSymbolTable()
        self.type_parser = TypeParser(self.symbol_table)
        self.errors = []
        self._typed_errors = []
        self.enum_defs = {}
        self.trait_defs = {}
        self.trait_impls = {}
        self.generic_class_defs = {}
        self.generic_segment_defs = {}
        self.generic_class_instances = {}
        self._method_pre_scan_cache = {}
        self._hm_subs = None
        self._incremental = incremental
        self.module = module

        # 阶段 0：注册所有类型定义（枚举、trait、类）
        self._scan_type_definitions(module)

        # 注册类型别名
        self._register_type_aliases(module)

        # 阶段 1：注册 trait 实现
        for impl in getattr(module, 'trait_impls', []):
            self.register_trait_impl(impl)

        # 阶段 2：预扫描所有段/方法定义（用 TypeVar 填充未知类型）
        self._pre_scan_definitions(module)

        # 阶段 3：HM 风格推断所有函数体（合一 + 泛化）
        self._hm_infer_module(module)

        # 阶段 4：推断顶层语句（独立的 HM 上下文，不污染段签名）
        self._hm_subs = None
        if hasattr(module, 'statements'):
            for stmt in module.statements:
                self._infer_statement(stmt)

        return self.type_cache

    # ---- 工具：根据类名查找类定义 ----
    def _lookup_class_def(self, name: str) -> Optional['ClassDefinition']:
        """在当前 module 中查找指定名称的类定义"""
        if self.module is None:
            return None
        for cls in getattr(self.module, 'classes', []) or []:
            if getattr(cls, 'name', None) == name:
                return cls
        return None

    # ---- 扫描阶段 ----
    def _scan_type_definitions(self, module: Module):
        """扫描所有类型定义（建立符号表）"""
        # 注册枚举
        for enum_def in getattr(module, 'enums', []):
            self.register_enum(enum_def)

        # 注册 trait/接口（包括 InterfaceDefinition 中文命名）
        for trait_def in getattr(module, 'trait_defs', []):
            self.register_trait(trait_def)
        for iface_def in getattr(module, 'interfaces', []):
            self.register_interface(iface_def)

        # 注册类（包括泛型类）
        if hasattr(module, 'classes'):
            for cls in module.classes:
                class_type = ClassType(cls.name)
                self.symbol_table.define(cls.name, 'class', class_type)
                # 记录泛型参数
                generic_params = getattr(cls, 'generic_params', None) or []
                if generic_params:
                    self.generic_class_defs[cls.name] = list(generic_params)

        # 注册段落/函数（包括泛型段落）
        if hasattr(module, 'segments'):
            for segment in module.segments:
                generic_params = getattr(segment, 'generic_params', None) or []
                if generic_params:
                    self.generic_segment_defs[segment.name] = list(generic_params)

    # ---- 类型别名注册与解析 ----
    def _register_type_aliases(self, module: Module):
        """注册模块中的类型别名"""
        self.type_aliases.clear()
        # 从 module.type_aliases 注册
        for alias in getattr(module, 'type_aliases', []) or []:
            name = getattr(alias, 'name', '')
            target = getattr(alias, 'target_type', '')
            if name and target:
                self.type_aliases[name] = target
        # 从 module.statements 中扫描 TypeAlias 节点
        from ast_nodes import TypeAlias as TypeAliasNode
        for stmt in getattr(module, 'statements', []) or []:
            if isinstance(stmt, TypeAliasNode):
                name = getattr(stmt, 'name', '')
                target = getattr(stmt, 'target_type', '')
                if name and target:
                    self.type_aliases[name] = target

    def _resolve_type_alias(self, type_str: str) -> str:
        """递归解析类型别名引用"""
        if not type_str:
            return type_str
        # 精确匹配别名
        if type_str in self.type_aliases:
            resolved = self.type_aliases[type_str]
            return self._resolve_type_alias(resolved)
        # 别名可能出现在泛型参数中，如 列表<数字列表>
        # 通过替换别名引用来实现
        resolved = type_str
        for alias_name, alias_target in sorted(self.type_aliases.items(), key=lambda x: -len(x[0])):
            if alias_name in resolved:
                resolved = resolved.replace(alias_name, alias_target)
        return resolved

    # ---- HM 阶段 1：预扫描所有定义，注册类型签名 ----
    def _pre_scan_definitions(self, module: Module):
        """第一阶段：扫描所有顶层段/类/方法定义，为每个注册初始类型签名。

        未标注的参数/返回类型使用 TypeVar 填充，便于后续通过合一推断。
        顶层语句中的段定义也一并扫描，确保相互调用能找到签名。
        """
        # 统一收集所有需要预扫描的段：module.segments + statements 中的段
        def _iter_segments():
            for seg in getattr(module, 'segments', []) or []:
                yield seg
            for stmt in getattr(module, 'statements', []) or []:
                if isinstance(stmt, SegmentDefinition):
                    yield stmt

        for segment in _iter_segments():
            # 显式的泛型参数名
            explicit_generics = list(getattr(segment, 'generic_params', None) or [])

            param_types: List[Type] = []
            tv_counter = [0]

            def _new_tvar(suggest: Optional[str] = None) -> TypeVar:
                if suggest and suggest not in [t.name for t in param_types if isinstance(t, TypeVar)]:
                    return TypeVar(suggest)
                name = f"T{tv_counter[0]}"
                tv_counter[0] += 1
                return TypeVar(name)

            for i, param in enumerate(segment.parameters):
                if param.type_annotation:
                    try:
                        param_types.append(self._parse_type_string(param.type_annotation))
                    except Exception:
                        param_types.append(_new_tvar())
                else:
                    # 尝试使用显式泛型参数名（按顺序）
                    if i < len(explicit_generics):
                        param_types.append(TypeVar(explicit_generics[i]))
                    else:
                        param_types.append(_new_tvar())

            # 返回类型：有标注用标注，否则用 TypeVar('R')
            if segment.return_type:
                try:
                    ret_type = self._parse_type_string(segment.return_type)
                except Exception:
                    ret_type = TypeVar('R')
            else:
                ret_type = TypeVar('R')

            func_type = FunctionType(param_types, ret_type)
            # 注册或覆盖符号
            existing = self.symbol_table.lookup(segment.name)
            if existing and existing.data_type is TYPE_UNKNOWN:
                existing.data_type = func_type
            else:
                self.symbol_table.define(segment.name, 'function', func_type)

        # 扫描类中的方法（用于类内部的方法调用推断）
        for cls in getattr(module, 'classes', []) or []:
            for method in getattr(cls, 'methods', []) or []:
                m_param_types: List[Type] = []
                for i, mp in enumerate(method.parameters):
                    if mp.type_annotation:
                        try:
                            m_param_types.append(self._parse_type_string(mp.type_annotation))
                            continue
                        except Exception:
                            pass
                    m_param_types.append(TypeVar(f"a{i}"))
                if method.return_type:
                    try:
                        m_ret = self._parse_type_string(method.return_type)
                    except Exception:
                        m_ret = TypeVar('R')
                else:
                    m_ret = TypeVar('R')
                # 记录在一个简单字典中，供 PropertyAccess 查找（可选）
                self._method_pre_scan_cache[(cls.name, method.name)] = FunctionType(m_param_types, m_ret)

    # ---- 调用图构建与拓扑排序 ----
    def _build_call_graph(self, module: Module):
        """构建调用图：段名 → 被调用段名集合。
        对每个段体做轻量 AST 遍历，收集 FunctionCall 调用的目标段名。
        """
        self._call_graph = {}

        def _iter_segments():
            for seg in getattr(module, 'segments', []) or []:
                yield seg
            for stmt in getattr(module, 'statements', []) or []:
                if isinstance(stmt, SegmentDefinition):
                    yield stmt

        # 先收集所有已知段名
        known_segments = set()
        for seg in _iter_segments():
            known_segments.add(seg.name)

        # 对每个段收集其调用的段
        for seg in _iter_segments():
            callees = self._collect_callees(seg)
            # 只保留已知段名（排除内置函数、方法调用等）
            self._call_graph[seg.name] = callees & known_segments

    def _collect_callees(self, segment) -> Set[str]:
        """轻量 AST 遍历：收集段体中 FunctionCall 调用的目标段名。
        不做完整类型推断，只做 AST 节点扫描。
        """
        callees: Set[str] = set()

        def _walk(node):
            if node is None:
                return
            if hasattr(node, '_ast_type_id') and node._ast_type_id == AST_TYPE_ID_FUNCTION_CALL:
                func_name = None
                if hasattr(node.name, 'name'):
                    func_name = node.name.name
                elif hasattr(node.name, '_ast_type_id') and node.name._ast_type_id == AST_TYPE_ID_IDENTIFIER:
                    func_name = node.name.name
                if func_name:
                    callees.add(func_name)
            # 递归遍历子节点
            for attr in ('body', 'statements', 'arguments', 'expression', 'value',
                         'condition', 'true_branch', 'false_branch', 'else_branch',
                         'then_branch', 'cases', 'tasks', 'left', 'right', 'operand',
                         'elements', 'key', 'target', 'iterable', 'handler'):
                child = getattr(node, attr, None)
                if child is not None:
                    if isinstance(child, list):
                        for item in child:
                            _walk(item)
                    else:
                        _walk(child)

        for stmt in getattr(segment, 'body', []) or []:
            _walk(stmt)
        return callees

    # ---- 增量推断缓存 ----
    def _compute_segment_hash(self, segment) -> str:
        """计算段体源码哈希（用于增量推断缓存键）。"""
        body_repr = repr([str(type(s).__name__) for s in (getattr(segment, 'body', []) or [])])
        return hashlib.md5(body_repr.encode('utf-8')).hexdigest()

    def _compute_type_hash(self, ft: FunctionType) -> str:
        """计算函数类型的哈希（用于检测依赖段类型是否变化）。"""
        return hashlib.md5(str(ft).encode('utf-8')).hexdigest()

    def _invalidate_dependents(self, seg_name: str):
        """递归失效所有依赖此段的缓存条目（级联失效）。"""
        to_process = [seg_name]
        processed: Set[str] = set()
        while to_process:
            current = to_process.pop()
            if current in processed:
                continue
            processed.add(current)
            if current in self._segment_cache:
                entry = self._segment_cache[current]
                for rd in entry.reverse_deps:
                    if rd not in processed:
                        to_process.append(rd)
                # 删除此缓存条目（将被重新推断）
                del self._segment_cache[current]

    def _check_cache(self, segment, dep_type_hashes: Dict[str, str]) -> Optional[FunctionType]:
        """检查段推断缓存是否有效。

        Returns:
            若缓存命中，返回缓存的 FunctionType；否则返回 None（需要重新推断）。
        """
        if not self._incremental:
            return None

        seg_name = segment.name
        if seg_name not in self._segment_cache:
            return None

        entry = self._segment_cache[seg_name]
        source_hash = self._compute_segment_hash(segment)

        # 检查源码是否变化
        if source_hash != entry.source_hash:
            # 源码变化，失效此段及其所有依赖者
            self._invalidate_dependents(seg_name)
            return None

        # 检查依赖段类型是否变化
        for dep_name, expected_hash in entry.dep_type_hashes.items():
            if dep_name not in dep_type_hashes:
                # 依赖段不再存在
                self._invalidate_dependents(seg_name)
                return None
            if dep_type_hashes[dep_name] != expected_hash:
                # 依赖段类型变化，失效此段及级联依赖
                self._invalidate_dependents(seg_name)
                return None

        return entry.result_type

    def _update_cache(self, seg_name: str, source_hash: str,
                       dep_type_hashes: Dict[str, str], result_type: FunctionType):
        """更新段推断缓存（同时更新反向依赖关系）。"""
        # 计算旧的反向依赖集合（用于清理）
        old_reverse_deps: Set[str] = set()
        if seg_name in self._segment_cache:
            old_reverse_deps = self._segment_cache[seg_name].reverse_deps

        # 创建新缓存条目
        entry = SegmentCacheEntry(
            source_hash=source_hash,
            dep_type_hashes=dep_type_hashes,
            result_type=result_type,
        )
        self._segment_cache[seg_name] = entry

        # 更新新依赖的反向引用
        for dep_name in dep_type_hashes:
            if dep_name not in self._segment_cache:
                self._segment_cache[dep_name] = SegmentCacheEntry(
                    source_hash="", dep_type_hashes={}, result_type=None
                )
            self._segment_cache[dep_name].reverse_deps.add(seg_name)

        # 清理旧依赖的反向引用（不再依赖的段）
        removed_deps = old_reverse_deps - set(dep_type_hashes.keys())
        for old_dep in removed_deps:
            if old_dep in self._segment_cache:
                self._segment_cache[old_dep].reverse_deps.discard(seg_name)

    def _topo_sort_segments(self, segments: List) -> List[List]:
        """拓扑排序：将段按调用依赖分层。
        
        调用图 _call_graph 是 caller -> {callees}，即 A 调用 B 意味着 A 依赖 B。
        因此 B 必须先于 A 推断。构建反向图（被调用者 → 调用者集合）用于更新入度。
        
        返回：[[段1, 段2], [段3], ...]，每层内的段无相互依赖，可并行推断。
        有环的段（相互递归）放在同一层，标记为需要额外迭代。
        """
        if not self._call_graph:
            return [segments]

        # 构建名称 → 段映射
        name_to_seg = {seg.name: seg for seg in segments}
        seg_names = set(name_to_seg.keys())

        # 入度 = 此段依赖的段数（即它调用的段数）
        in_degree: Dict[str, int] = {}
        for seg in segments:
            callees = self._call_graph.get(seg.name, set()) & seg_names
            in_degree[seg.name] = len(callees)

        # 构建反向图：被调用者 → 调用者集合（用于更新入度）
        reverse_graph: Dict[str, Set[str]] = {}
        for caller, callees in self._call_graph.items():
            if caller not in seg_names:
                continue
            for callee in callees:
                if callee in seg_names:
                    if callee not in reverse_graph:
                        reverse_graph[callee] = set()
                    reverse_graph[callee].add(caller)

        # BFS 拓扑分层
        layers: List[List] = []
        remaining = set(seg.name for seg in segments)
        in_scc: Set[str] = set()  # 相互递归的段

        while remaining:
            # 找出当前入度为 0 的段（无依赖，可立即推断）
            current_layer = []
            for name in list(remaining):
                if in_degree.get(name, 0) == 0:
                    current_layer.append(name_to_seg[name])
                    remaining.discard(name)

            if current_layer:
                layers.append(current_layer)
                # 移除当前层段对依赖它的段（调用者）的入度影响
                for seg in current_layer:
                    for caller in reverse_graph.get(seg.name, set()):
                        if caller in in_degree:
                            in_degree[caller] = max(0, in_degree[caller] - 1)
            else:
                # 剩余段形成环（SCC），全部放入同一层
                scc_layer = [name_to_seg[name] for name in remaining]
                layers.append(scc_layer)
                in_scc.update(remaining)
                remaining.clear()

        return layers

    # ---- HM 阶段 2：推断函数体并泛化 ----

    # ⭐ 并行推断：在隔离环境中推断单个段
    def _infer_segment_isolated(self, segment, pre_func_type: FunctionType,
                                  sym_table_snapshot, call_graph: Dict[str, Set[str]],
                                  incremental: bool) -> Tuple[str, Optional[FunctionType], List[str]]:
        """在隔离的符号表副本中推断单个段，返回 (段名, 推断结果, 错误列表)。

        用于并行推断：每个 worker 线程拥有独立的符号表和类型缓存，
        避免线程间竞争。
        """
        errors: List[str] = []
        # 使用符号表快照创建隔离环境
        saved_symbol_table = self.symbol_table
        saved_errors = self.errors
        saved_typed_errors = self._typed_errors
        saved_type_cache = self.type_cache
        saved_hm_subs = self._hm_subs
        saved_return_type = self._current_return_type
        saved_collected = self._collected_return_types
        saved_incremental = self._incremental

        try:
            # 设置隔离环境
            self.symbol_table = sym_table_snapshot
            self.errors = []
            self._typed_errors = []
            self.type_cache = {}
            self._hm_subs = TypeSubstitution()
            self._incremental = incremental

            # 进入段作用域
            self.symbol_table.enter_scope()
            self._hm_subs = TypeSubstitution()

            for param, ptype in zip(segment.parameters, pre_func_type.param_types):
                self.symbol_table.define(param.name, 'parameter', ptype)

            self._current_return_type = pre_func_type.return_type
            self._collected_return_types = []

            try:
                for body_stmt in segment.body:
                    self._infer_statement(body_stmt)
            except Exception as e:
                errors.append(f"段 '{segment.name}' 推断异常: {e}")

            # 应用累积的替换
            local_subs = self._hm_subs.clone()
            if self._collected_return_types:
                try:
                    for rt in self._collected_return_types:
                        new_subs = unify(
                            pre_func_type.return_type.apply_substitution(local_subs),
                            rt.apply_substitution(local_subs),
                            local_subs,
                        )
                        local_subs = new_subs
                except UnificationError:
                    pass

            resolved_params = [pt.apply_substitution(local_subs)
                               for pt in pre_func_type.param_types]
            resolved_return = pre_func_type.return_type.apply_substitution(local_subs)

            # 无 return 且未显式声明返回 → 视为空
            if not self._collected_return_types and not segment.return_type \
                    and isinstance(resolved_return, TypeVar) \
                    and resolved_return.name not in local_subs:
                resolved_return = TYPE_NULL

            final_func_type = FunctionType(resolved_params, resolved_return)
            generalized = self._generalize(segment.name, final_func_type)

            self.symbol_table.exit_scope()

            return (segment.name, generalized, errors)

        finally:
            # 恢复原始状态
            self.symbol_table = saved_symbol_table
            self.errors = saved_errors
            self._typed_errors = saved_typed_errors
            self.type_cache = saved_type_cache
            self._hm_subs = saved_hm_subs
            self._current_return_type = saved_return_type
            self._collected_return_types = saved_collected
            self._incremental = saved_incremental

    def _hm_infer_module(self, module: Module):
        """第二阶段：HM 风格推断所有段体并进行 let-polymorphism 泛化。

        关键设计：
          * 预扫描阶段给每个段注册了「泛型占位」签名。
          * 段之间可能存在相互调用，因此需要多次迭代：
              迭代 1：先推断所有段体（此时调用者可能看到的是被调用者的 pre 类型）
              迭代 2：重新推断调用者的段体（此时调用者能看到被调用者已推断的具体类型）
          * 在写入符号表时，保留最泛化的版本，以便后续 FunctionCall 实例化。
          * ⭐ type_cache 在段体推断期间必须独立管理，避免旧结果污染。
          * 同时处理所有类定义（包括接口实现验证）。
        """
        def _iter_segments():
            for seg in getattr(module, 'segments', []):
                yield seg
            for stmt in getattr(module, 'statements', []):
                if isinstance(stmt, SegmentDefinition):
                    yield stmt

        # ---- 先推断枚举、trait 定义（内部一致性检查）----
        for enum_def in getattr(module, 'enums', []) or []:
            self._infer_enum_def(enum_def)

        for trait_def in getattr(module, 'trait_defs', []) or []:
            self._infer_trait_def(trait_def)

        # ---- 处理类定义（包括接口实现验证）----
        for cls in getattr(module, 'classes', []) or []:
            self._infer_class(cls)

        # ---- 处理段定义 ----
        all_segs = list(_iter_segments())

        # ⭐ 构建调用图并拓扑排序
        self._build_call_graph(module)
        layers = self._topo_sort_segments(all_segs)

        # 推断每个段体（支持拓扑分层 + 并行推断 + SCC 多轮迭代）
        for layer_idx, layer_segs in enumerate(layers):
            # 判断当前层是否包含 SCC（相互递归），需要 2 轮迭代
            layer_names = {seg.name for seg in layer_segs}
            has_scc = any(
                self._call_graph.get(seg.name, set()) & layer_names
                for seg in layer_segs
            )
            max_iters = 2 if has_scc else 1

            # ⭐ 并行推断：同层无 SCC 且段数 > 1 时，并行推断
            use_parallel = (
                self._parallel
                and not has_scc
                and len(layer_segs) > 1
                and max_iters == 1
            )

            for _ in range(max_iters):
                if use_parallel:
                    # ---- 并行推断 ----
                    sym_table_snap = self.symbol_table.snapshot()
                    futures = {}
                    with ThreadPoolExecutor(max_workers=min(self._max_workers, len(layer_segs))) as executor:
                        for segment in layer_segs:
                            sym = self.symbol_table.lookup(segment.name)
                            if sym is None or not isinstance(sym.data_type, FunctionType):
                                continue
                            pre_func_type = sym.data_type
                            # 每个 worker 使用独立的符号表副本
                            worker_snap = sym_table_snap.snapshot() if sym_table_snap else TypeSymbolTable()
                            future = executor.submit(
                                self._infer_segment_isolated,
                                segment, pre_func_type, worker_snap,
                                self._call_graph, self._incremental
                            )
                            futures[future] = (segment, pre_func_type)

                        for future in as_completed(futures):
                            segment, pre_func_type = futures[future]
                            try:
                                seg_name, generalized, worker_errors = future.result()
                                if generalized is not None:
                                    sym = self.symbol_table.lookup(seg_name)
                                    if sym and isinstance(sym.data_type, FunctionType):
                                        sym.data_type = generalized
                                if worker_errors:
                                    for err in worker_errors:
                                        self._add_error(err, node=segment)
                            except Exception as e:
                                self._add_error(f"段 '{segment.name}' 并行推断异常: {e}", node=segment)
                else:
                    # ---- 串行推断（含 SCC 多轮迭代） ----
                    for segment in layer_segs:
                        sym = self.symbol_table.lookup(segment.name)
                        if sym is None or not isinstance(sym.data_type, FunctionType):
                            continue

                        pre_func_type = sym.data_type

                        # ⭐ 增量推断：构建依赖段类型哈希并检查缓存
                        source_hash = self._compute_segment_hash(segment)
                        dep_type_hashes: Dict[str, str] = {}
                        for dep_name in self._call_graph.get(segment.name, set()):
                            dep_sym = self.symbol_table.lookup(dep_name)
                            if dep_sym and isinstance(dep_sym.data_type, FunctionType):
                                dep_type_hashes[dep_name] = self._compute_type_hash(dep_sym.data_type)

                        cached = self._check_cache(segment, dep_type_hashes)
                        if cached is not None:
                            sym.data_type = cached
                            continue

                        # ⭐ 保存并重置 type_cache
                        saved_cache = self.type_cache
                        self.type_cache = {}

                        self.symbol_table.enter_scope()
                        self._hm_subs = TypeSubstitution()

                        for param, ptype in zip(segment.parameters, pre_func_type.param_types):
                            self.symbol_table.define(param.name, 'parameter', ptype)

                        self._current_return_type = pre_func_type.return_type
                        self._collected_return_types = []
                        try:
                            for body_stmt in segment.body:
                                self._infer_statement(body_stmt)
                        except Exception as e:
                            self._add_error(f"段 '{segment.name}' 推断异常: {e}", node=segment)

                        # 应用累积的替换
                        local_subs = self._hm_subs.clone()
                        if self._collected_return_types:
                            try:
                                for rt in self._collected_return_types:
                                    new_subs = unify(
                                        pre_func_type.return_type.apply_substitution(local_subs),
                                        rt.apply_substitution(local_subs),
                                        local_subs,
                                    )
                                    local_subs = new_subs
                            except UnificationError:
                                pass

                        resolved_params = [pt.apply_substitution(local_subs)
                                           for pt in pre_func_type.param_types]
                        resolved_return = pre_func_type.return_type.apply_substitution(local_subs)

                        if not self._collected_return_types and not segment.return_type \
                                and isinstance(resolved_return, TypeVar) \
                                and resolved_return.name not in local_subs:
                            resolved_return = TYPE_NULL

                        final_func_type = FunctionType(resolved_params, resolved_return)
                        generalized = self._generalize(segment.name, final_func_type)
                        sym.data_type = generalized

                        if self._incremental:
                            self._update_cache(segment.name, source_hash, dep_type_hashes, generalized)

                        self._current_return_type = None
                        self._hm_subs = TypeSubstitution()
                        self.type_cache = saved_cache
                        self.symbol_table.exit_scope()

    # ---- Let-polymorphism：泛化与实例化 ----
    def _generalize(self, name: str, t: Type) -> Type:
        """将具体类型中的自由类型变量提升为泛型参数（let-generalization）。

        返回的类型仍保留 TypeVar 形式，但会被记录为泛型段，供调用处实例化。
        这里实现为：将 t 中的自由 TypeVar 名称收集并登记到 generic_segment_defs。
        """
        fvs = list(t.collect_type_vars())
        if fvs:
            # 按名称排序获得确定性结果
            fv_names = sorted({tv.name for tv in fvs})
            # 记录为泛型段（用于调试/测试）
            self.generic_segment_defs[name] = fv_names
        return t

    def _instantiate(self, func_type: FunctionType) -> FunctionType:
        """将泛型类型实例化为调用点的具体类型（生成新鲜的 TypeVar）。

        对 func_type 中的所有 TypeVar（即自由类型变量）替换为全新的 TypeVar，
        避免不同调用点之间污染。这是 HM 的核心机制之一。
        """
        if not isinstance(func_type, FunctionType):
            return func_type

        fvs = list(func_type.collect_type_vars())
        if not fvs:
            return func_type

        # 建立 旧名称 → 新鲜 TypeVar 的替换
        subs = TypeSubstitution()
        seen = set()
        counter = [0]
        for tv in fvs:
            if tv.name in seen:
                continue
            seen.add(tv.name)
            # 生成一个全新的、唯一的 TypeVar 名称
            fresh_name = f"{tv.name}'{counter[0]}"
            counter[0] += 1
            subs.bind(tv.name, TypeVar(fresh_name))

        new_params = [p.apply_substitution(subs) for p in func_type.param_types]
        new_return = func_type.return_type.apply_substitution(subs)
        return FunctionType(new_params, new_return)

    # ---- 主推断阶段 ----
    def _infer_module(self, module: Module):
        """推断模块内容"""
        for enum_def in getattr(module, 'enums', []):
            self._infer_enum_def(enum_def)

        for trait_def in getattr(module, 'trait_defs', []):
            self._infer_trait_def(trait_def)

        if hasattr(module, 'classes'):
            for cls in module.classes:
                self._infer_class(cls)

        if hasattr(module, 'segments'):
            for segment in module.segments:
                self._infer_segment(segment)

        if hasattr(module, 'statements'):
            for stmt in module.statements:
                self._infer_statement(stmt)

    def _infer_enum_def(self, enum_def: EnumDefinition):
        """推断枚举定义"""
        self.symbol_table.enter_scope()

        generic_params = getattr(enum_def, 'generic_params', None) or []
        for gp in generic_params:
            self.symbol_table.define_generic_param(gp)

        for variant in enum_def.variants:
            field_types = [self._parse_type_string(f.type_annotation) for f in variant.fields]
            if field_types:
                func_type = FunctionType(field_types, self.enum_defs.get(enum_def.name, EnumType(enum_name=enum_def.name)))
            else:
                func_type = FunctionType([], self.enum_defs.get(enum_def.name, EnumType(enum_name=enum_def.name)))
            self.symbol_table.define(variant.name, 'function', func_type)

        self.symbol_table.exit_scope()

    def _infer_trait_def(self, trait_def: TraitDefinition):
        """推断 trait 定义 —— 验证方法签名内部一致性"""
        seen_methods = set()
        for method in trait_def.methods:
            if method.name in seen_methods:
                self._add_error(
                    f"接口 '{trait_def.name}' 中存在重复方法 '{method.name}'",
                    node=trait_def
                )
            seen_methods.add(method.name)

    # ---- 类推断（包括泛型类 + 接口实现验证） ----
    def _infer_class(self, cls: ClassDefinition):
        """推断类（支持泛型类 + 接口实现验证）"""
        self.symbol_table.enter_scope()

        # 注册泛型参数
        generic_params = getattr(cls, 'generic_params', None) or []
        for gp in generic_params:
            self.symbol_table.define_generic_param(gp)

        # 处理构造函数
        if cls.constructor:
            self._infer_constructor(cls.constructor)

        # 处理方法并构建方法签名索引
        class_method_sigs: Dict[str, FunctionType] = {}
        for method in cls.methods:
            self._infer_method(method)
            param_types = [self._parse_type_string(p.type_annotation) for p in method.parameters]
            return_type = self._parse_type_string(method.return_type) if method.return_type else TYPE_UNKNOWN
            class_method_sigs[method.name] = FunctionType(param_types, return_type)

        # 验证类实现的接口
        declared_interfaces = getattr(cls, 'interfaces', None) or []
        resolved_interfaces: List[InterfaceType] = []
        for iface_name in declared_interfaces:
            if iface_name in self.trait_defs:
                iface = self.trait_defs[iface_name]
                resolved_interfaces.append(iface)
                # 逐个检查接口方法是否被实现
                self._check_class_implements_interface(cls.name, iface, class_method_sigs)
            else:
                self._add_error(f"类 '{cls.name}' 声明的接口 '{iface_name}' 未定义", node=cls)

        # 更新符号表中该类的 ClassType，记录实现的接口
        sym = self.symbol_table.lookup(cls.name)
        if sym and isinstance(sym.data_type, ClassType):
            sym.data_type.implements_interfaces = resolved_interfaces

        self.symbol_table.exit_scope()

    def _check_class_implements_interface(self, class_name: str, iface: InterfaceType,
                                           class_methods: Dict[str, FunctionType]):
        """检查类是否完整实现了接口的所有方法（存在性 + 签名匹配）"""
        for method_name, required_ft in iface.methods.items():
            if method_name not in class_methods:
                self._add_error(
                    f"类 '{class_name}' 未实现接口 '{iface.interface_name}' "
                    f"的必需方法 '{method_name}'"
                )
                continue
            actual_ft = class_methods[method_name]
            err = iface.method_signature_matches(method_name, actual_ft)
            if err:
                self._add_error(
                    f"类 '{class_name}' 实现接口 '{iface.interface_name}': {err}"
                )

    def _infer_constructor(self, constructor: ConstructorDefinition):
        """推断构造函数"""
        self.symbol_table.enter_scope()

        for param in constructor.parameters:
            param_type = self._parse_type_string(param.type_annotation)
            self.symbol_table.define(param.name, 'parameter', param_type)

        for stmt in constructor.body:
            self._infer_statement(stmt)

        self.symbol_table.exit_scope()

    def _infer_method(self, method: MethodDefinition):
        """推断方法"""
        self.symbol_table.enter_scope()

        self.symbol_table.define('己', 'parameter', TYPE_ANY)

        for param in method.parameters:
            param_type = self._parse_type_string(param.type_annotation)
            self.symbol_table.define(param.name, 'parameter', param_type)

        if method.return_type:
            self._current_return_type = self._parse_type_string(method.return_type)
        else:
            self._current_return_type = None

        for stmt in method.body:
            self._infer_statement(stmt)

        self._current_return_type = None
        self.symbol_table.exit_scope()

    # ---- 段落/函数（含泛型）推断 ----
    def _infer_segment(self, segment: SegmentDefinition):
        """推断段落（函数）—— 支持泛型参数"""
        self.symbol_table.enter_scope()

        # 检查是否为异步函数
        is_async = '异步' in (getattr(segment, 'modifiers', []) or [])
        if is_async:
            self._in_async_function = True

        # 注册泛型参数到当前作用域
        generic_params = getattr(segment, 'generic_params', None) or []
        for gp in generic_params:
            self.symbol_table.define_generic_param(gp)

        # 注册参数类型（含 TypeVar）
        param_types: List[Type] = []
        for param in segment.parameters:
            if param.type_annotation:
                ptype = self._parse_type_string(param.type_annotation)
            else:
                ptype = TYPE_UNKNOWN
            param_types.append(ptype)
            self.symbol_table.define(param.name, 'parameter', ptype)

        # 设置返回类型（含 TypeVar）
        declared_return: Optional[Type] = None
        if segment.return_type:
            declared_return = self._parse_type_string(segment.return_type)
            self._current_return_type = declared_return
            if is_async:
                self._current_return_type = FutureType(declared_return)
        else:
            self._current_return_type = None

        # 推断函数体
        self._collected_return_types = []
        for stmt in segment.body:
            self._infer_statement(stmt)

        # 构建函数类型签名
        return_type_for_sig: Type
        if declared_return is not None:
            return_type_for_sig = declared_return
        elif self._collected_return_types:
            # 从返回语句推断返回类型
            inferred = self._collected_return_types[0]
            for t in self._collected_return_types[1:]:
                try:
                    subs = unify(inferred, t)
                    inferred = inferred.apply_substitution(subs)
                except UnificationError:
                    # 返回类型不一致，使用 Unknown
                    inferred = TYPE_UNKNOWN
                    break
            return_type_for_sig = inferred
        elif generic_params:
            return_type_for_sig = TYPE_UNKNOWN
        else:
            # 无返回语句 → 返回空
            return_type_for_sig = TYPE_NULL

        if is_async and not isinstance(return_type_for_sig, FutureType):
            return_type_for_sig = FutureType(return_type_for_sig)

        function_type = FunctionType(param_types, return_type_for_sig)

        # 更新符号表中该函数的类型
        sym = self.symbol_table.lookup(segment.name)
        if sym:
            sym.data_type = function_type

        self._current_return_type = None
        if is_async:
            self._in_async_function = False
        self.symbol_table.exit_scope()

    # ---- 语句推断 ----
    def _infer_defer_stmt(self, stmt: DeferStatement):
        self.symbol_table.enter_scope()
        for s in stmt.body:
            self._infer_statement(s)
        self.symbol_table.exit_scope()
        self.type_cache[id(stmt)] = TYPE_NULL
        return TYPE_NULL

    def _infer_async_scope(self, stmt: AsyncScope):
        elem_types = []
        for task in stmt.tasks:
            t = self._infer_expr(task)
            elem_types.append(t)
        result = ListType()
        self.type_cache[id(stmt)] = result
        return result

    def _infer_statement(self, stmt) -> Type:
        """推断语句类型，返回语句的整体类型（通常是返回语句的返回类型）"""
        if stmt is None:
            return TYPE_NULL

        ast_type_id = getattr(stmt, '_ast_type_id', 0)
        if ast_type_id == AST_TYPE_ID_VARIABLE_DECLARATION:
            return self._infer_var_decl(stmt)

        elif ast_type_id == AST_TYPE_ID_ASSIGNMENT:
            return self._infer_assignment(stmt)

        elif ast_type_id == AST_TYPE_ID_IF_STATEMENT:
            return self._infer_if_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_FOREACH_STATEMENT:
            return self._infer_foreach_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_WHILE_STATEMENT:
            return self._infer_while_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_RETURN_STATEMENT:
            return self._infer_return_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_MATCH_STATEMENT:
            return self._infer_match_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_EXPRESSION_STATEMENT:
            return self._infer_expr(stmt.expression)

        elif ast_type_id == AST_TYPE_ID_PRINT_STATEMENT:
            if hasattr(stmt, 'value') and stmt.value is not None:
                self._infer_expr(stmt.value)
            return TYPE_NULL

        elif ast_type_id == AST_TYPE_ID_THROW_STATEMENT:
            if hasattr(stmt, 'value') and stmt.value is not None:
                self._infer_expr(stmt.value)
            return TYPE_NULL

        elif ast_type_id == AST_TYPE_ID_FUNCTION_CALL:
            return self._infer_expr(stmt)

        elif ast_type_id == AST_TYPE_ID_SEGMENT_DEFINITION:
            self._infer_segment(stmt)
            return TYPE_NULL

        elif ast_type_id == AST_TYPE_ID_DEFER_STATEMENT:
            return self._infer_defer_stmt(stmt)

        elif ast_type_id == AST_TYPE_ID_ASYNC_SCOPE:
            return self._infer_async_scope(stmt)

        return TYPE_NULL

    # ---- 变量声明推断 ----
    def _infer_var_decl(self, stmt) -> Type:
        """推断变量声明（支持解构赋值）"""

        # 检查是否解构赋值：解构 (x, y) = 表达式
        destructure_names = getattr(stmt, 'destructure_names', None)
        if destructure_names:
            return self._infer_destructure_decl(stmt, destructure_names)

        expr_type = self._infer_expr(stmt.value)

        # 检查类型注解
        type_annotation = getattr(stmt, 'type_annotation', None)
        final_type = expr_type

        if type_annotation:
            anno_type = self._parse_type_string(type_annotation)
            # 尝试合一（允许类型变量绑定）
            try:
                subs = unify(anno_type, expr_type)
                final_type = anno_type.apply_substitution(subs)
            except UnificationError:
                # 合一失败：类型不匹配
                if not expr_type.is_subtype_of(anno_type):
                    self._add_error(
                        f"类型不匹配: 变量 '{stmt.name}' 声明为 {anno_type}，"
                        f"但初始值类型为 {expr_type}",
                        node=stmt
                    )
                final_type = anno_type

        # 可空性检查
        if isinstance(expr_type, NullType) and type_annotation and '|空' not in type_annotation:
            self._add_error(
                f"空安全错误: 变量 '{stmt.name}' 声明为不可空类型 {type_annotation}，"
                f"但不能赋值为空",
                node=stmt
            )

        is_mutable = getattr(stmt, 'is_mutable', False)
        self.symbol_table.define(stmt.name, 'variable', final_type, is_mutable)
        self.type_cache[id(stmt)] = final_type
        return final_type

    def _infer_destructure_decl(self, stmt, destructure_names: List[str]) -> Type:
        """推断解构变量声明：解构 (x, y) = 表达式"""
        expr_type = self._infer_expr(stmt.value)

        # 期望表达式返回 TupleType
        if isinstance(expr_type, TupleType):
            element_types = expr_type.element_types
            for i, name in enumerate(destructure_names):
                if i < len(element_types):
                    var_type = element_types[i]
                else:
                    var_type = TYPE_UNKNOWN
                is_mutable = getattr(stmt, 'is_mutable', False)
                self.symbol_table.define(name, 'variable', var_type, is_mutable)
        elif isinstance(expr_type, ListType):
            # 列表解构：所有变量获取元素类型
            elem_type = expr_type.element_type or TYPE_UNKNOWN
            for name in destructure_names:
                is_mutable = getattr(stmt, 'is_mutable', False)
                self.symbol_table.define(name, 'variable', elem_type, is_mutable)
        else:
            # 未知类型，全部标记为 Unknown
            for name in destructure_names:
                is_mutable = getattr(stmt, 'is_mutable', False)
                self.symbol_table.define(name, 'variable', TYPE_UNKNOWN, is_mutable)
            self._add_error(
                f"解构赋值期望元组或列表类型，实际为 {expr_type}",
                node=stmt
            )

        result_type = expr_type  # 整个解构表达式的类型
        self.type_cache[id(stmt)] = result_type
        return result_type

    def _infer_assignment(self, stmt) -> Type:
        """推断赋值语句"""
        value_type = self._infer_expr(stmt.value)

        target_type_id = getattr(stmt.target, '_ast_type_id', 0)
        if target_type_id == AST_TYPE_ID_IDENTIFIER:
            target_name = stmt.target.name
            symbol = self.symbol_table.lookup(target_name)
            if symbol:
                if not symbol.is_mutable:
                    self._add_error(
                        f"不可变变量 '{target_name}' 不能重新赋值",
                        node=stmt
                    )
                # 类型兼容检查（使用合一）
                try:
                    subs = unify(symbol.data_type, value_type)
                    updated = symbol.data_type.apply_substitution(subs)
                    self.symbol_table.update_type(target_name, updated)
                except UnificationError as e:
                    if not value_type.is_subtype_of(symbol.data_type):
                        self._add_error(
                            f"类型不匹配: 变量 '{target_name}' 类型为 {symbol.data_type}，"
                            f"不能赋值为 {value_type} ({e.message})",
                            node=stmt
                        )
            self.type_cache[id(stmt)] = value_type
            return value_type

        elif target_type_id == AST_TYPE_ID_PROPERTY_ACCESS:
            self._infer_expr(stmt.target)
            self.type_cache[id(stmt)] = value_type
            return value_type

        self.type_cache[id(stmt)] = value_type
        return value_type

    def _infer_if_stmt(self, stmt) -> Type:
        cond_type = self._infer_expr(stmt.condition)
        if not isinstance(cond_type, (BooleanType, AnyType, UnknownType)):
            self._add_error(
                f"条件表达式类型应为布尔，实际为 {cond_type}",
                node=stmt
            )

        # 类型守卫检测：若 是整数(值) / 是字符串(值) 等 => 在 then 分支中缩小类型
        narrowed_var = None
        narrowed_type = None
        else_narrowed_type = None
        type_guard_info = self._detect_type_guard(stmt.condition)
        if type_guard_info:
            var_name, narrowed, else_narrowed = type_guard_info
            narrowed_var = var_name
            narrowed_type = narrowed
            else_narrowed_type = else_narrowed

        self.symbol_table.enter_scope()
        if narrowed_var and narrowed_type:
            # 在 then 分支中，变量类型缩小为检查类型
            self.symbol_table.define(narrowed_var, 'variable', narrowed_type)
        for s in stmt.then_body:
            self._infer_statement(s)
        self.symbol_table.exit_scope()

        if stmt.else_body:
            self.symbol_table.enter_scope()
            if narrowed_var and else_narrowed_type:
                # 在 else 分支中，变量类型缩小为排除类型（联合类型）
                self.symbol_table.define(narrowed_var, 'variable', else_narrowed_type)
            for s in stmt.else_body:
                self._infer_statement(s)
            self.symbol_table.exit_scope()

        for elseif_body in getattr(stmt, 'elseif_bodies', []) or []:
            self.symbol_table.enter_scope()
            if narrowed_var and else_narrowed_type:
                self.symbol_table.define(narrowed_var, 'variable', else_narrowed_type)
            for s in elseif_body:
                self._infer_statement(s)
            self.symbol_table.exit_scope()
        return TYPE_NULL

    # ---- 类型守卫与类型缩小辅助 ----
    _TYPE_GUARD_FUNCTIONS = {
        '是整数': (TYPE_NUMBER, '数'),
        '是字符串': (TYPE_STRING, '串'),
        '是浮点': (TYPE_NUMBER, '数'),
        '是布尔': (TYPE_BOOLEAN, '布尔'),
        '是列表': (ListType(), '列表'),
        '是字典': (DictType(), '字典'),
        '是空': (TYPE_NULL, '空'),
    }

    def _detect_type_guard(self, condition) -> Optional[Tuple[str, Type, Type]]:
        """检测条件表达式是否为类型守卫（如 是整数(值)）
        
        返回 (变量名, then分支缩小类型, else分支排除类型) 或 None
        """
        ast_type_id = getattr(condition, '_ast_type_id', 0)
        if ast_type_id != AST_TYPE_ID_FUNCTION_CALL:
            return None

        # 获取函数名
        func_name = ''
        if hasattr(condition, 'name'):
            name = condition.name
            func_name = getattr(name, 'name', '') or getattr(name, 'value', '') or ''

        if func_name not in self._TYPE_GUARD_FUNCTIONS:
            return None

        narrowed_type, _ = self._TYPE_GUARD_FUNCTIONS[func_name]

        # 检查第一个参数是否为标识符
        args = getattr(condition, 'arguments', []) or []
        if not args:
            return None

        arg = args[0]
        arg_ast_type = getattr(arg, '_ast_type_id', 0)
        if arg_ast_type != AST_TYPE_ID_IDENTIFIER:
            return None

        var_name = getattr(arg, 'name', '') or getattr(arg, 'value', '')
        if not var_name:
            return None

        # 查找当前变量类型（用于 else 分支的类型缩小）
        symbol = self.symbol_table.lookup(var_name)
        original_type = symbol.data_type if symbol else TYPE_UNKNOWN

        # then 分支：缩小为检查类型
        then_type = narrowed_type

        # else 分支：如果是联合类型，排除检查类型
        else_type = original_type
        if isinstance(original_type, UnionType):
            remaining = [t for t in original_type.types if not self._types_are_equal(t, narrowed_type)]
            if remaining:
                else_type = UnionType(remaining) if len(remaining) > 1 else remaining[0]
            else:
                else_type = TYPE_NULL
        elif isinstance(original_type, OptionalTypeWrapper):
            if narrowed_type == original_type.inner_type:
                else_type = TYPE_NULL
            else:
                else_type = original_type

        return (var_name, then_type, else_type)

    def _types_are_equal(self, a: Type, b: Type) -> bool:
        """比较两个类型是否相等（基于 _type_id 和基本属性）"""
        if a._type_id != b._type_id:
            return False
        if a._type_id == TYPE_ID_NUMBER or a._type_id == TYPE_ID_STRING or \
           a._type_id == TYPE_ID_BOOLEAN or a._type_id == TYPE_ID_NULL:
            return True
        if a._type_id == TYPE_ID_LIST:
            if hasattr(b, 'element_type') and hasattr(a, 'element_type'):
                return self._types_are_equal(a.element_type or TYPE_ANY, b.element_type or TYPE_ANY)
            return True
        if a._type_id == TYPE_ID_DICT:
            return True
        return str(a) == str(b)

    def _infer_foreach_stmt(self, stmt) -> Type:
        iter_type = self._infer_expr(stmt.iterable)

        self.symbol_table.enter_scope()

        # 推断循环变量类型
        if isinstance(iter_type, ListType):
            var_type = iter_type.element_type or TYPE_UNKNOWN
        elif isinstance(iter_type, GenericTypeInstance) and iter_type.base_name in ('列表', 'List'):
            var_type = iter_type.type_args[0] if iter_type.type_args else TYPE_UNKNOWN
        elif isinstance(iter_type, StringType):
            var_type = TYPE_STRING
        else:
            var_type = TYPE_UNKNOWN
        self.symbol_table.define(stmt.variable, 'variable', var_type)

        for s in stmt.body:
            self._infer_statement(s)
        self.symbol_table.exit_scope()
        return TYPE_NULL

    def _infer_while_stmt(self, stmt) -> Type:
        cond_type = self._infer_expr(stmt.condition)
        if not isinstance(cond_type, (BooleanType, AnyType, UnknownType)):
            self._add_error(
                f"循环条件类型应为布尔，实际为 {cond_type}",
                node=stmt
            )

        self.symbol_table.enter_scope()
        for s in stmt.body:
            self._infer_statement(s)
        self.symbol_table.exit_scope()
        return TYPE_NULL

    def _infer_return_stmt(self, stmt) -> Type:
        if stmt.value:
            return_type = self._infer_expr(stmt.value)
            # 收集返回类型以便在无显式声明时推断
            if return_type is not None:
                self._collected_return_types.append(return_type)
            if self._current_return_type:
                try:
                    subs = unify(self._current_return_type, return_type)
                    # ⭐ 累积到当前段的 HM 上下文中
                    hm_subs = getattr(self, '_hm_subs', None)
                    if hm_subs is not None:
                        for k, v in subs.items():
                            if k not in hm_subs:
                                hm_subs[k] = v
                            else:
                                hm_subs[k] = hm_subs[k].apply_substitution(subs)
                    resolved = self._current_return_type.apply_substitution(subs)
                    self._current_return_type = resolved
                except UnificationError:
                    if not return_type.is_subtype_of(self._current_return_type):
                        self._add_error(
                            f"返回类型不匹配: 期望 {self._current_return_type}，实际为 {return_type}",
                            node=stmt
                        )
            self.type_cache[id(stmt)] = return_type
            return return_type
        else:
            if self._current_return_type and not isinstance(self._current_return_type, (NullType, UnknownType, AnyType)):
                self._add_error(
                    f"返回类型不匹配: 期望 {self._current_return_type}，但无返回值",
                    node=stmt
                )
            return TYPE_NULL

    def _infer_match_stmt(self, stmt) -> Type:
        subject_type = self._infer_expr(stmt.subject)
        self.type_cache[id(stmt)] = TYPE_UNKNOWN

        if isinstance(subject_type, EnumType):
            matched_variants = set()
            for case in stmt.cases:
                pattern = case.pattern
                variant_name = self._get_pattern_variant_name(pattern)
                if variant_name:
                    matched_variants.add(variant_name)

                self.symbol_table.enter_scope()
                if pattern and getattr(pattern, 'binding', None):
                    binding_type = self._get_binding_type(subject_type, pattern)
                    self.symbol_table.define(pattern.binding, 'variable', binding_type)

                # 枚举变体字段绑定：若 变体(字段名)
                if pattern and getattr(pattern, 'kind', '') == 'variable':
                    binding = getattr(pattern, 'binding', None)
                    if binding and variant_name:
                        variant_fields = subject_type.get_variant_types(variant_name)
                        if variant_fields:
                            # 绑定整个变体值
                            self.symbol_table.define(binding, 'variable', subject_type)
                            # 如果有字段绑定，逐个绑定
                            field_bindings = getattr(pattern, 'field_bindings', None) or []
                            for i, fb in enumerate(field_bindings):
                                if i < len(variant_fields):
                                    self.symbol_table.define(fb, 'variable', variant_fields[i])

                if case.guard:
                    guard_type = self._infer_expr(case.guard)
                    if not isinstance(guard_type, (BooleanType, AnyType, UnknownType)):
                        self._add_error(
                            f"匹配守卫条件类型应为布尔，实际为 {guard_type}",
                            node=stmt
                        )

                for s in case.body:
                    self._infer_statement(s)
                self.symbol_table.exit_scope()

            has_wildcard = any(
                getattr(c.pattern, 'kind', '') == 'wildcard' for c in stmt.cases
            )

            if not has_wildcard and subject_type.enum_name in self.enum_defs:
                enum_def = self.enum_defs[subject_type.enum_name]
                unmatched = []
                for v in enum_def.variants:
                    if v not in matched_variants:
                        unmatched.append(v)
                if unmatched:
                    self._add_error(
                        f"非穷尽匹配: 枚举 '{subject_type.enum_name}' 的以下变体未处理: "
                        + ", ".join(unmatched),
                        node=stmt
                    )

        elif isinstance(subject_type, UnionType):
            # 联合类型模式匹配：类型缩小
            matched_types = set()
            for case in stmt.cases:
                pattern = case.pattern
                pattern_kind = getattr(pattern, 'kind', '')
                self.symbol_table.enter_scope()

                if pattern_kind == 'type_check':
                    # 类型检查模式：若 整数(值)
                    type_name = getattr(pattern, 'type_name', '')
                    binding = getattr(pattern, 'binding', None)
                    if type_name:
                        narrowed_type = self._parse_type_string(type_name)
                        matched_types.add(type_name)
                        if binding:
                            self.symbol_table.define(binding, 'variable', narrowed_type)
                    elif binding:
                        self.symbol_table.define(binding, 'variable', subject_type)
                else:
                    # 通配符或变量绑定
                    binding = getattr(pattern, 'binding', None)
                    if binding:
                        self.symbol_table.define(binding, 'variable', subject_type)

                if case.guard:
                    guard_type = self._infer_expr(case.guard)
                    if not isinstance(guard_type, (BooleanType, AnyType, UnknownType)):
                        self._add_error(
                            f"匹配守卫条件类型应为布尔，实际为 {guard_type}",
                            node=stmt
                        )

                for s in case.body:
                    self._infer_statement(s)
                self.symbol_table.exit_scope()

            # 检查联合类型穷尽性
            has_wildcard = any(
                getattr(c.pattern, 'kind', '') in ('wildcard', 'variable') and
                not getattr(c.pattern, 'type_name', None)
                for c in stmt.cases
            )
            if not has_wildcard:
                # 警告未匹配的联合成员
                unmatched = [str(t) for t in subject_type.types
                            if str(t) not in matched_types]
                if unmatched:
                    self._add_error(
                        f"非穷尽匹配: 联合类型未处理的成员: {', '.join(unmatched)}",
                        node=stmt
                    )

        else:
            # 普通类型匹配
            for case in stmt.cases:
                self.symbol_table.enter_scope()
                pattern = case.pattern
                if pattern and getattr(pattern, 'binding', None):
                    # 类型缩小：为匹配变量绑定更具体的类型
                    type_name = getattr(pattern, 'type_name', None)
                    if type_name:
                        narrowed = self._parse_type_string(type_name)
                        self.symbol_table.define(pattern.binding, 'variable', narrowed)
                    else:
                        self.symbol_table.define(pattern.binding, 'variable', subject_type)
                for s in case.body:
                    self._infer_statement(s)
                self.symbol_table.exit_scope()
        return TYPE_NULL

    def _get_pattern_variant_name(self, pattern) -> Optional[str]:
        if pattern is None:
            return None
        if hasattr(pattern, 'kind') and pattern.kind == 'variable':
            if hasattr(pattern, 'value') and isinstance(pattern.value, str) and pattern.value and pattern.value[0].isascii() and pattern.value[0].isupper():
                return pattern.value
        if hasattr(pattern, 'kind') and pattern.kind == 'type_check':
            return pattern.type_name
        return None

    def _get_binding_type(self, enum_type: EnumType, pattern) -> Type:
        """获取模式匹配中绑定的变量类型
        
        根据枚举变体的字段类型返回合适的绑定类型：
        - 如果变体有多个字段，返回 TupleType
        - 如果变体只有一个字段，返回该字段的类型
        - 如果变体没有字段，返回枚举类型本身
        """
        variant_name = self._get_pattern_variant_name(pattern)
        if variant_name and enum_type.enum_name in self.enum_defs:
            def_enum = self.enum_defs[enum_type.enum_name]
            field_types = def_enum.get_variant_types(variant_name)
            if field_types:
                if len(field_types) == 1:
                    return field_types[0]
                elif len(field_types) > 1:
                    return TupleType(field_types)
        return TYPE_UNKNOWN

    # ---- 表达式推断 ----
    def _infer_expr(self, expr) -> Type:
        """推断表达式类型"""
        if expr is None:
            return TYPE_NULL

        if id(expr) in self.type_cache:
            return self.type_cache[id(expr)]

        result_type: Type = TYPE_UNKNOWN
        ast_type_id = getattr(expr, '_ast_type_id', 0)

        # 字面量
        if ast_type_id == AST_TYPE_ID_NUMBER_LITERAL:
            result_type = TYPE_NUMBER
        elif ast_type_id == AST_TYPE_ID_STRING_LITERAL:
            result_type = TYPE_STRING
        elif ast_type_id == AST_TYPE_ID_BOOLEAN_LITERAL:
            result_type = TYPE_BOOLEAN
        elif ast_type_id == AST_TYPE_ID_NULL_LITERAL:
            result_type = TYPE_NULL

        # 解包表达式：值! 或 unwrap(值)
        elif ast_type_id == AST_TYPE_ID_UNWRAP_EXPRESSION:
            inner_type = self._infer_expr(expr.value)
            if isinstance(inner_type, OptionalTypeWrapper):
                result_type = inner_type.inner_type
            elif isinstance(inner_type, NullType):
                result_type = TYPE_UNKNOWN  # 空值! → 运行时失败
            else:
                # 非可空类型但 unwrap 了：警告但允许
                result_type = inner_type
            return result_type

        # 标识符
        elif ast_type_id == AST_TYPE_ID_IDENTIFIER:
            # 特殊处理：'空'、'None' 等是「可空的底类型」，被推断为 NullType
            if expr.name in ('None', '空', 'null', 'NULL'):
                result_type = TYPE_NULL
            else:
                symbol = self.symbol_table.lookup(expr.name)
                if symbol:
                    result_type = symbol.data_type
                elif expr.name in self.enum_defs:
                    result_type = EnumType(enum_name=expr.name)
                elif expr.name in self.trait_defs:
                    result_type = self.trait_defs[expr.name]
                elif expr.name in self.generic_class_defs:
                    result_type = ClassType(expr.name)
                else:
                    result_type = TYPE_UNKNOWN

        # 二元运算
        elif ast_type_id == AST_TYPE_ID_BINARY_OP:
            left_type = self._infer_expr(expr.left)
            right_type = self._infer_expr(expr.right)
            op = expr.operator

            # ⭐ 可空类型强制检查：可空类型不能直接参与运算，必须先 unwrap
            def _is_nullable(t):
                return isinstance(t, (OptionalTypeWrapper, NullType))

            if _is_nullable(left_type) and not isinstance(right_type, (AnyType, UnknownType, TypeVar)):
                self._add_error(
                    f"可空类型不能直接参与运算 '{op}': 左侧类型为 {left_type}，"
                    f"需要先使用 '!' 或 'unwrap()' 解包",
                    node=expr
                )
            if _is_nullable(right_type) and not isinstance(left_type, (AnyType, UnknownType, TypeVar)):
                self._add_error(
                    f"可空类型不能直接参与运算 '{op}': 右侧类型为 {right_type}，"
                    f"需要先使用 '!' 或 'unwrap()' 解包",
                    node=expr
                )

            # 小工具：HM 风格双向合一，把 TypeVar 约束为具体类型
            # 同时把产生的替换累积到 self._hm_subs（若在段体推断上下文）
            def _try_unify_both_as(target: Type) -> bool:
                try:
                    subs1 = unify(left_type, target)
                    subs2 = unify(right_type, target)
                    # 累积到当前段的 HM 上下文中
                    hm_subs = getattr(self, '_hm_subs', None)
                    if hm_subs is not None:
                        for k, v in subs1.items():
                            if k not in hm_subs:
                                hm_subs[k] = v
                        for k, v in subs2.items():
                            if k not in hm_subs:
                                hm_subs[k] = v
                    return True
                except UnificationError:
                    return False

            if op in ('+', '加'):
                if isinstance(left_type, StringType) and isinstance(right_type, StringType):
                    result_type = TYPE_STRING
                elif isinstance(left_type, NumberType) and isinstance(right_type, NumberType):
                    result_type = TYPE_NUMBER
                elif isinstance(left_type, StringType) or isinstance(right_type, StringType):
                    # 其中一边是字符串，尝试把另一边合一为字符串（宽松）
                    _try_unify_both_as(TYPE_STRING)
                    result_type = TYPE_STRING
                elif isinstance(left_type, TypeVar) and isinstance(right_type, TypeVar) and left_type.name == right_type.name:
                    # 同名 TypeVar：T + T → T（保持多态）
                    result_type = left_type
                elif isinstance(left_type, NumberType) or isinstance(right_type, NumberType):
                    # 一边是 数，另一边可能是 TypeVar/UNKNOWN，HM 合一
                    _try_unify_both_as(TYPE_NUMBER)
                    result_type = TYPE_NUMBER
                elif isinstance(left_type, (TypeVar, UnknownType)) or isinstance(right_type, (TypeVar, UnknownType)):
                    # 至少一边是 TypeVar/UNKNOWN —— 按 HM 规则推断为 数
                    # 但如果失败则回退为 UNKNOWN
                    if _try_unify_both_as(TYPE_NUMBER):
                        result_type = TYPE_NUMBER
                    else:
                        result_type = TYPE_UNKNOWN
                else:
                    # 完全具体但不一致
                    try:
                        unify(left_type, TYPE_NUMBER)
                        unify(right_type, TYPE_NUMBER)
                        result_type = TYPE_NUMBER
                    except UnificationError:
                        result_type = TYPE_UNKNOWN
            elif op in ('-', '减', '*', '乘', '/', '除', '%', '模', '^', '幂'):
                # 算术：HM 风格 —— 若是 TypeVar 则合一为 数
                try:
                    unify(left_type, TYPE_NUMBER)
                    unify(right_type, TYPE_NUMBER)
                except UnificationError:
                    self._add_error(f"算术运算 '{op}' 需要数字类型，但得到 {left_type} 和 {right_type}", node=expr)
                result_type = TYPE_NUMBER
            elif op in ('>', '<', '>=', '<=', '==', '!=', '等于', '不等于', '大于', '小于', '大于等于', '小于等于'):
                result_type = TYPE_BOOLEAN
            elif op in ('且', '与', '或', 'and', 'or'):
                result_type = TYPE_BOOLEAN
            else:
                result_type = TYPE_UNKNOWN

        # 一元运算
        elif ast_type_id == AST_TYPE_ID_UNARY_OP:
            operand_type = self._infer_expr(expr.operand)
            if expr.operator in ('非', 'not', '!'):
                result_type = TYPE_BOOLEAN if isinstance(operand_type, BooleanType) else TYPE_UNKNOWN
            elif expr.operator in ('-',):
                result_type = TYPE_NUMBER if isinstance(operand_type, NumberType) else TYPE_UNKNOWN
            else:
                result_type = operand_type

        # 函数调用 / 段落调用
        elif ast_type_id == AST_TYPE_ID_FUNCTION_CALL:
            result_type = self._infer_function_call(expr)

        # 属性访问（支持泛型类实例方法查找）
        elif ast_type_id == AST_TYPE_ID_PROPERTY_ACCESS:
            obj_type = self._infer_expr(expr.obj)
            property_name = expr.property_name

            # 通用：先按 obj_type 的类定义查找方法
            if isinstance(obj_type, ClassType):
                cls_def = self._lookup_class_def(obj_type.class_name)
                if cls_def is not None:
                    # 构建从泛型参数名 → 实际类型的替换
                    param_names = list(self.generic_class_defs.get(obj_type.class_name, []))
                    subs = TypeSubstitution()
                    if param_names and obj_type.type_args:
                        for i, pn in enumerate(param_names):
                            if i < len(obj_type.type_args):
                                subs.bind(pn, obj_type.type_args[i])

                    # 在方法列表中查找
                    for method in getattr(cls_def, 'methods', []) or []:
                        if method.name == property_name:
                            # 构建 FunctionType 并应用替换
                            m_params = []
                            for mp in method.parameters:
                                if mp.type_annotation:
                                    m_params.append(self._parse_type_string(mp.type_annotation))
                                else:
                                    m_params.append(TYPE_UNKNOWN)
                            m_return = self._parse_type_string(method.return_type) if method.return_type else TYPE_UNKNOWN
                            ft = FunctionType(m_params, m_return)
                            if param_names:
                                ft = ft.apply_substitution(subs)
                            result_type = ft
                            self.type_cache[id(expr)] = result_type
                            return result_type

            # 在对象类型中按属性名查找（简单的 Any）
            result_type = TYPE_UNKNOWN

        # 索引访问
        elif ast_type_id == AST_TYPE_ID_INDEX_ACCESS:
            obj_type = self._infer_expr(expr.obj)
            index_type = self._infer_expr(expr.index)

            if isinstance(obj_type, ListType):
                result_type = obj_type.element_type or TYPE_UNKNOWN
            elif isinstance(obj_type, GenericTypeInstance) and obj_type.base_name in ('列表', 'List'):
                result_type = obj_type.type_args[0] if obj_type.type_args else TYPE_UNKNOWN
            elif isinstance(obj_type, StringType):
                result_type = TYPE_STRING
            elif isinstance(obj_type, DictType):
                result_type = obj_type.value_type or TYPE_UNKNOWN
            elif isinstance(obj_type, GenericTypeInstance) and obj_type.base_name in ('字典', 'Map'):
                result_type = obj_type.type_args[1] if len(obj_type.type_args) > 1 else TYPE_UNKNOWN
            else:
                result_type = TYPE_UNKNOWN

        # 列表字面量（支持泛型元素类型推断）
        elif ast_type_id == AST_TYPE_ID_LIST_LITERAL:
            element_types = [self._infer_expr(e) for e in expr.elements]
            if element_types:
                # 尝试合一所有元素类型
                common_type: Type = element_types[0]
                all_matched = True
                for t in element_types[1:]:
                    try:
                        subs = unify(common_type, t)
                        common_type = common_type.apply_substitution(subs)
                    except UnificationError:
                        all_matched = False
                        break
                if all_matched:
                    result_type = ListType(common_type)
                else:
                    result_type = ListType(TYPE_ANY)
            else:
                result_type = ListType(TYPE_UNKNOWN)

        # 字典字面量
        elif ast_type_id == AST_TYPE_ID_DICT_LITERAL:
            key_types = []
            val_types = []
            for entry in expr.entries:
                if hasattr(entry, 'key'):
                    kt = self._infer_expr(entry.key)
                    key_types.append(kt)
                if hasattr(entry, 'value'):
                    vt = self._infer_expr(entry.value)
                    val_types.append(vt)
            # 统一键类型
            key_type: Type
            if key_types:
                key_type = key_types[0]
                for t in key_types[1:]:
                    try:
                        subs = unify(key_type, t)
                        key_type = key_type.apply_substitution(subs)
                    except UnificationError:
                        key_type = TYPE_ANY
                        break
            else:
                key_type = TYPE_UNKNOWN
            # 统一值类型
            val_type: Type
            if val_types:
                val_type = val_types[0]
                for t in val_types[1:]:
                    try:
                        subs = unify(val_type, t)
                        val_type = val_type.apply_substitution(subs)
                    except UnificationError:
                        val_type = TYPE_ANY
                        break
            else:
                val_type = TYPE_UNKNOWN
            result_type = DictType(key_type, val_type)

        # 类实例化（支持泛型类 + 类型参数推断）
        elif ast_type_id == AST_TYPE_ID_NEW_EXPRESSION:
            arg_types = [self._infer_expr(a) for a in expr.arguments]
            class_name = expr.class_name

            if class_name in self.generic_class_defs:
                # 泛型类：根据显式类型参数 + 构造函数参数推断类型参数
                param_names = self.generic_class_defs[class_name]
                type_args: List[Type] = [TYPE_UNKNOWN for _ in param_names]

                # 1) 处理显式类型参数（如 数组[数](3)）
                explicit_args = getattr(expr, 'type_args', None) or []
                subs = TypeSubstitution()
                for i, ta_str in enumerate(explicit_args):
                    if i < len(param_names):
                        parsed = self._parse_type_string(ta_str) if isinstance(ta_str, str) else TYPE_UNKNOWN
                        subs.bind(param_names[i], parsed)
                        type_args[i] = parsed

                # 2) 若有构造函数参数，尝试从参数类型进行合一推断剩余类型参数
                cls_def = self._lookup_class_def(class_name)
                if cls_def is not None and cls_def.constructor:
                    ctor = cls_def.constructor
                    ctor_param_types: List[Type] = []
                    # 临时作用域：注册泛型参数以允许解析类型变量
                    self.symbol_table.enter_scope()
                    for gp in param_names:
                        self.symbol_table.define_generic_param(gp)
                    try:
                        for param in ctor.parameters:
                            if param.type_annotation:
                                ctor_param_types.append(self._parse_type_string(param.type_annotation))
                            else:
                                ctor_param_types.append(TYPE_UNKNOWN)
                    finally:
                        self.symbol_table.exit_scope()

                    # 合一推断：对每个形参和实参进行合一
                    for formal, actual in zip(ctor_param_types, arg_types):
                        try:
                            new_subs = unify(formal, actual, subs)
                            subs = new_subs
                        except UnificationError:
                            # 若合一失败，跳过该参数（保持 UNKNOWN）
                            pass

                    # 应用替换到所有类型参数位置
                    for i, name in enumerate(param_names):
                        if i < len(type_args) and isinstance(type_args[i], UnknownType):
                            tv = TypeVar(name)
                            resolved = tv.apply_substitution(subs)
                            if not isinstance(resolved, TypeVar) or resolved.name != name:
                                type_args[i] = resolved

                result_type = ClassType(class_name, type_args)
                # 记录实例化（便于测试/调试）
                self.generic_class_instances[class_name] = type_args
            else:
                # 内置泛型名称检查（如 "列表"）
                if class_name in ('列表', 'List'):
                    elem = arg_types[0] if arg_types else TYPE_UNKNOWN
                    result_type = ListType(elem)
                elif class_name in ('字典', 'Map'):
                    k = arg_types[0] if len(arg_types) > 0 else TYPE_UNKNOWN
                    v = arg_types[1] if len(arg_types) > 1 else TYPE_UNKNOWN
                    result_type = DictType(k, v)
                else:
                    result_type = ClassType(class_name)

        elif ast_type_id == AST_TYPE_ID_SELF_REFERENCE:
            result_type = TYPE_ANY

        elif ast_type_id == AST_TYPE_ID_LIST_COMPREHENSION:
            iter_type = self._infer_expr(expr.iterable)
            self.symbol_table.enter_scope()
            if isinstance(iter_type, ListType):
                self.symbol_table.define(expr.variable, 'variable', iter_type.element_type or TYPE_UNKNOWN)
            elif isinstance(iter_type, GenericTypeInstance) and iter_type.base_name in ('列表', 'List'):
                self.symbol_table.define(expr.variable, 'variable',
                                         iter_type.type_args[0] if iter_type.type_args else TYPE_UNKNOWN)
            else:
                self.symbol_table.define(expr.variable, 'variable', TYPE_UNKNOWN)
            if expr.condition:
                cond_type = self._infer_expr(expr.condition)
                if not isinstance(cond_type, (BooleanType, AnyType, UnknownType)):
                    self._add_error(f"列表推导过滤条件类型应为布尔，实际为 {cond_type}", node=expr)
            elem_type = self._infer_expr(expr.expression)
            self.symbol_table.exit_scope()
            result_type = ListType(elem_type)

        elif ast_type_id == AST_TYPE_ID_LAMBDA_EXPRESSION:
            result_type = self._infer_lambda(expr)

        elif ast_type_id == AST_TYPE_ID_STRING_INTERPOLATION:
            for part in expr.parts:
                if not isinstance(part, str):
                    self._infer_expr(part)
            result_type = TYPE_STRING

        elif ast_type_id == AST_TYPE_ID_CONDITIONAL_EXPRESSION:
            cond_type = self._infer_expr(expr.condition)
            if not isinstance(cond_type, (BooleanType, AnyType, UnknownType)):
                self._add_error(f"条件表达式类型应为布尔，实际为 {cond_type}", node=expr)
            then_type = self._infer_expr(expr.then_expr)
            if expr.else_expr:
                else_type = self._infer_expr(expr.else_expr)
                try:
                    subs = unify(then_type, else_type)
                    result_type = then_type.apply_substitution(subs)
                except UnificationError:
                    result_type = then_type
            else:
                result_type = then_type

        elif ast_type_id == AST_TYPE_ID_PIPE_EXPRESSION:
            cur_type = TYPE_UNKNOWN
            for sub_expr in expr.expressions:
                cur_type = self._infer_expr(sub_expr)
            result_type = cur_type

        elif ast_type_id == AST_TYPE_ID_AWAIT_EXPRESSION:
            inner_type = self._infer_expr(expr.expression)
            if isinstance(inner_type, FutureType):
                result_type = inner_type.inner_type
            else:
                result_type = inner_type

        else:
            result_type = TYPE_UNKNOWN

        self.type_cache[id(expr)] = result_type
        return result_type

    # ---- Lambda 表达式推断（HM 风格，含 TypeVar 参数） ----
    def _infer_lambda(self, expr) -> FunctionType:
        """推断 lambda 表达式：
        - 未标注的参数用 TypeVar 填充（支持合一推断）
        - 推断 body 类型作为返回类型
        """
        self.symbol_table.enter_scope()
        param_types: List[Type] = []
        for i, param in enumerate(expr.parameters):
            if getattr(param, 'type_annotation', None):
                try:
                    ptype = self._parse_type_string(param.type_annotation)
                except Exception:
                    ptype = TypeVar(f"lam{i}")
            else:
                ptype = TypeVar(f"lam{i}")
            param_types.append(ptype)
            self.symbol_table.define(param.name, 'parameter', ptype)

        # 推断 body
        body_type = self._infer_expr(expr.body)

        # 应用可能从外部合一所产生的替换（当前作用域内的参数 TypeVar 被合一后的值替换）
        # 这里简单处理：对 param_types 和 body_type 应用全局 TypeSubstitution 是不实际的，
        # 因为我们在 unify 时产生的替换仅用于推断，不持久化到一个全局环境。
        # 但在 _infer_function_call 中对每个调用会重新实例化，因此是安全的。

        self.symbol_table.exit_scope()
        return FunctionType(param_types, body_type)

    # ---- 函数/段落调用推断（核心：泛型参数推断） ----
    def _infer_function_call(self, expr) -> Type:
        """推断函数调用类型，支持 HM 风格泛型实例化。

        步骤：
        1. 推断实参类型
        2. 查找函数符号
        3. 实例化（将泛型类型变量替换为新鲜 TypeVar）
        4. 用实参与形参合一，得到替换
        5. 将替换应用到返回类型，得到具体返回类型
        6. 若在段体推断上下文中（self._hm_subs 存在），累积替换以便
           将参数 TypeVar 的约束反馈回段签名
        """
        # 分析参数
        arg_types = [self._infer_expr(a) for a in expr.arguments]

        # 获取函数名
        func_name = None
        name_type_id = getattr(expr.name, '_ast_type_id', 0)
        if name_type_id == AST_TYPE_ID_IDENTIFIER:
            func_name = expr.name.name
        elif hasattr(expr.name, 'name'):
            func_name = expr.name.name

        if not func_name:
            return TYPE_UNKNOWN

        # 检查是否枚举变体构造函数
        if func_name in self.enum_defs:
            return self.enum_defs[func_name]
        for enum_name, enum_type in self.enum_defs.items():
            if func_name in getattr(enum_type, 'variants', {}):
                return enum_type

        # 查找符号（可能是泛型段/函数）
        symbol = self.symbol_table.lookup(func_name)

        # 显式类型参数（如 映射[T=数](...) 或 映射[数](...)）
        explicit_type_args = getattr(expr, 'type_args', None) or []

        if symbol and isinstance(symbol.data_type, FunctionType):
            func_type = symbol.data_type

            # --- HM 关键步骤：实例化泛型类型 ---
            instantiated = self._instantiate(func_type)

            # 检查参数数量
            if len(arg_types) != len(instantiated.param_types):
                self._add_error(
                    f"函数 '{func_name}' 需要 {len(instantiated.param_types)} 个参数，"
                    f"但提供了 {len(arg_types)} 个",
                    node=expr
                )
                return instantiated.return_type

            # ⭐ 可空类型强制检查：形参非可空时，实参不可为可空类型
            for i, (formal, actual) in enumerate(zip(instantiated.param_types, arg_types)):
                # 显式声明为可空的形参允许传入可空
                if isinstance(formal, OptionalTypeWrapper):
                    continue
                # 其他任意情况下，只要实参是可空的，就报告解包问题
                if isinstance(actual, (OptionalTypeWrapper, NullType)):
                    self._add_error(
                        f"函数 '{func_name}' 第 {i + 1} 个参数类型不可空，"
                        f"但传入可空类型 {actual}，需要先使用 '!' 或 'unwrap()' 解包",
                        node=expr
                    )

            # 若在段体推断上下文中，从 self._hm_subs 继承当前已知约束
            subs = getattr(self, '_hm_subs', None)
            if subs is not None:
                subs = subs.clone()
            else:
                subs = TypeSubstitution()

            # 处理显式类型参数
            if explicit_type_args:
                tvars_ordered = _collect_type_vars_ordered(instantiated)
                for i, expr_arg in enumerate(explicit_type_args):
                    if i < len(tvars_ordered):
                        tv_name = tvars_ordered[i]
                        concrete = self._parse_type_string(expr_arg) if isinstance(expr_arg, str) else TYPE_UNKNOWN
                        subs.bind(tv_name, concrete)

            # 通过参数与形参合一推断剩余类型变量
            for formal, actual in zip(instantiated.param_types, arg_types):
                try:
                    formal_applied = formal.apply_substitution(subs)
                    new_subs = unify(formal_applied, actual, subs)
                    subs = new_subs
                except UnificationError:
                    if not actual.is_subtype_of(formal):
                        self._add_error(
                            f"函数 '{func_name}' 参数类型不匹配: "
                            f"期望 {formal}，实际 {actual}",
                            node=expr
                        )

            # 将替换应用到返回类型得到具体返回类型
            resolved_return = instantiated.return_type.apply_substitution(subs)

            # ⭐ 累积约束到当前段的 HM 上下文（若存在）
            hm_subs = getattr(self, '_hm_subs', None)
            if hm_subs is not None:
                for k, v in subs.items():
                    if k not in hm_subs:
                        hm_subs[k] = v
                    else:
                        hm_subs[k] = hm_subs[k].apply_substitution(subs)

            return resolved_return

        # 符号存在但类型未知（如仅声明的段落）
        if symbol:
            return symbol.data_type or TYPE_UNKNOWN

        # 内置函数类型推断
        return self._infer_builtin_return(func_name, arg_types)

    def _infer_builtin_return(self, func_name: str, arg_types: List[Type]) -> Type:
        """推断内置函数返回类型"""
        # 普通内置函数
        builtin_returns = {
            '打印': TYPE_NULL,
            '显示': TYPE_NULL,
            '读取': TYPE_STRING,
            '长': TYPE_NUMBER,
            '长度': TYPE_NUMBER,
            '字符串长度': TYPE_NUMBER,
            '列表长度': TYPE_NUMBER,
            '转整数': TYPE_NUMBER,
            '转为整数': TYPE_NUMBER,
            '转浮点': TYPE_NUMBER,
            '转为浮点': TYPE_NUMBER,
            '转字符串': TYPE_STRING,
            '转为字符串': TYPE_STRING,
            '是整数': TYPE_BOOLEAN,
            '是浮点': TYPE_BOOLEAN,
            '是字符串': TYPE_BOOLEAN,
            '是列表': TYPE_BOOLEAN,
            '是字典': TYPE_BOOLEAN,
            '是空': TYPE_BOOLEAN,
            '文件存在': TYPE_BOOLEAN,
            '目录存在': TYPE_BOOLEAN,
            '排序': ListType(),
            '反转': ListType(),
            '求和': TYPE_NUMBER,
            '求最大': TYPE_NUMBER,
            '求最小': TYPE_NUMBER,
        }

        if func_name in builtin_returns:
            return builtin_returns[func_name]

        # 泛化处理：支持泛型的内置操作
        if arg_types:
            if func_name in ('列表追加', '列表添加'):
                if isinstance(arg_types[0], ListType):
                    return arg_types[0]
                if isinstance(arg_types[0], GenericTypeInstance) and arg_types[0].base_name in ('列表', 'List'):
                    return arg_types[0]
                return ListType()
            if func_name in ('映射',):
                # 映射[T](列表[T], T->T) -> 列表[T]（泛型）
                if len(arg_types) >= 1:
                    if isinstance(arg_types[0], ListType) and arg_types[0].element_type:
                        return ListType(arg_types[0].element_type)
                    if isinstance(arg_types[0], GenericTypeInstance) and arg_types[0].base_name in ('列表', 'List'):
                        if arg_types[0].type_args:
                            return ListType(arg_types[0].type_args[0])
                return ListType()
            if func_name.startswith('列表'):
                if isinstance(arg_types[0], ListType):
                    return arg_types[0]
                return ListType()
            if func_name.startswith('字典'):
                return DictType()

        return TYPE_UNKNOWN

    # ---- 公共辅助 ----
    def get_errors(self) -> List[str]:
        return self.errors

    def get_typed_errors(self) -> List[TypeErrorInference]:
        """获取结构化类型错误列表（携带位置信息）"""
        return self._typed_errors

    def get_type_cache(self) -> Dict[int, Type]:
        return self.type_cache


# =============================================================================
# 辅助：按顺序收集函数签名中的类型变量
# =============================================================================

def _collect_type_vars_ordered(t: Type) -> List[str]:
    """按首次出现顺序收集类型变量名"""
    result: List[str] = []
    seen: Set[str] = set()

    def walk(node: Type):
        if isinstance(node, TypeVar):
            if node.name not in seen:
                seen.add(node.name)
                result.append(node.name)
        elif isinstance(node, FunctionType):
            for p in node.param_types:
                walk(p)
            walk(node.return_type)
        elif isinstance(node, ListType) and node.element_type:
            walk(node.element_type)
        elif isinstance(node, DictType):
            if node.key_type:
                walk(node.key_type)
            if node.value_type:
                walk(node.value_type)
        elif isinstance(node, GenericTypeInstance):
            for a in node.type_args:
                walk(a)
        elif isinstance(node, ClassType) and node.type_args:
            for a in node.type_args:
                walk(a)
        elif isinstance(node, FutureType):
            walk(node.inner_type)
        elif isinstance(node, OptionalTypeWrapper):
            walk(node.inner_type)
        elif isinstance(node, TupleType):
            for a in node.element_types:
                walk(a)
        elif isinstance(node, SetType) and node.element_type:
            walk(node.element_type)

    walk(t)
    return result


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明增强类型推断器测试 (Phase 1)")
    print("=" * 60)

    # 测试基本类型
    test_module = Module(
        statements=[
            VariableDeclaration(
                name='结果',
                value=BinaryOp(
                    left=NumberLiteral(value=3),
                    operator='+',
                    right=NumberLiteral(value=5)
                )
            ),
            ExpressionStatement(
                expression=BinaryOp(
                    left=StringLiteral(value='3 + 5 = '),
                    operator='+',
                    right=Identifier(name='结果')
                )
            )
        ]
    )

    inferencer = TypeInferencer()
    types = inferencer.infer(test_module)

    print("推断结果:")
    for stmt in test_module.statements:
        stmt_type = types.get(id(stmt), "?")
        print(f"  {type(stmt).__name__}: {stmt_type}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
