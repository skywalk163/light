# -*- coding: utf-8 -*-
"""
光明（Light）可选类型系统 v4.2

提供编译时类型检查、类型推导和类型标注验证。
类型系统是可选（opt-in）的 —— 未标注类型的代码不会报错，标注了类型的代码会进行验证。

分级检查：
  - 签名级（SIGNATURE）：仅检查段落参数和返回值类型
  - 变量级（VARIABLE）：签名级 + 变量声明类型检查
  - 表达式级（EXPRESSION）：变量级 + 表达式运算类型检查

类型系统层次：
  - 基本类型：整数、浮点、字符串、布尔、空
  - 复合类型：列表、字典、元组
  - 联合类型：整数|浮点、字符串|空
  - 可选类型：可空整数、可空字符串
  - 函数类型：(参数类型) -> 返回类型
  - 泛型类型：列表<整数>、字典<字符串, 整数>

用法：
  from type_checker import TypeChecker, check_module

  checker = TypeChecker()
  issues = checker.check(module)

  for issue in issues:
      print(issue.level, issue.message, f"at line {issue.line}")
"""

import os
import sys
import re
from typing import List, Dict, Set, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum

# 确保能导入项目模块
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# 从 core.config 导入分级检查相关枚举
from core.config import TypeCheckLevel, SegmentTypeMode, LightConfig


# =============================================================================
# 类型检查严重程度
# =============================================================================

class TypeErrorSeverity(Enum):
    """类型错误严重程度"""
    ERROR = 'error'
    WARNING = 'warning'
    RUNTIME = 'runtime'


# =============================================================================
# 类型检查结果
# =============================================================================

@dataclass
class TypeCheckResult:
    """类型检查结果"""
    severity: TypeErrorSeverity
    message: str
    line: int = 0
    column: int = 0
    code: str = ''

    def is_error(self) -> bool:
        return self.severity == TypeErrorSeverity.ERROR

    def __repr__(self):
        loc = f"第{self.line}行" if self.line else ""
        return f"TypeCheckResult({self.severity.value}, {loc}: {self.message})"


# =============================================================================
# 类型检查器配置
# =============================================================================

@dataclass
class TypeCheckerConfig:
    """类型检查器配置：控制检查的粒度和严格程度"""
    check_level: TypeCheckLevel = TypeCheckLevel.NONE
    default_segment_mode: SegmentTypeMode = SegmentTypeMode.LOOSE

    @classmethod
    def from_light_config(cls, dc: LightConfig) -> 'TypeCheckerConfig':
        """从 LightConfig 创建配置"""
        return cls(
            check_level=dc.type_check_level,
            default_segment_mode=dc.default_segment_mode,
        )

    def apply_file_directives(self, source: str) -> 'TypeCheckerConfig':
        """从源文件注释中提取文件级类型检查指令并应用到配置"""
        directives = _extract_type_directives(source)
        config = TypeCheckerConfig(
            check_level=self.check_level,
            default_segment_mode=self.default_segment_mode,
        )

        # 类型检查级别
        level_str = directives.get('类型检查级别', '')
        if level_str:
            level_map = {
                'none': TypeCheckLevel.NONE, '无': TypeCheckLevel.NONE,
                'signature': TypeCheckLevel.SIGNATURE, '签名': TypeCheckLevel.SIGNATURE,
                'variable': TypeCheckLevel.VARIABLE, '变量': TypeCheckLevel.VARIABLE,
                'expression': TypeCheckLevel.EXPRESSION, '表达式': TypeCheckLevel.EXPRESSION,
            }
            key = level_str.strip().lower()
            if key in level_map:
                config.check_level = level_map[key]

        # 类型模式
        mode_str = directives.get('类型模式', '')
        if mode_str:
            mode_map = {
                'loose': SegmentTypeMode.LOOSE, '松散': SegmentTypeMode.LOOSE,
                'strict': SegmentTypeMode.STRICT, '严格': SegmentTypeMode.STRICT,
            }
            key = mode_str.strip().lower()
            if key in mode_map:
                config.default_segment_mode = mode_map[key]

        return config

    def get_segment_check_level(self, modifiers: List[str]) -> TypeCheckLevel:
        """根据段落修饰符确定检查级别"""
        if not modifiers:
            return self.check_level

        if '严格' in modifiers:
            return TypeCheckLevel.EXPRESSION
        if '松散' in modifiers:
            return TypeCheckLevel.NONE

        return self.check_level


def _extract_type_directives(source: str) -> Dict[str, str]:
    """从源文件中提取文件级类型检查指令（仅扫描文件开头的注释行）

    支持的指令格式：
      # 类型检查级别: 签名
      # 类型检查级别：签名
      # 类型模式: 严格
    """
    directives: Dict[str, str] = {}
    pattern = re.compile(r'#\s*(类型检查级别|类型模式)\s*[:：]\s*(.+)', re.IGNORECASE)

    for line in source.split('\n'):
        stripped = line.strip()
        # 空行跳过
        if not stripped:
            continue
        # 注释行：解析指令
        if stripped.startswith('#'):
            m = pattern.match(stripped)
            if m:
                directives[m.group(1)] = m.group(2).strip()
        else:
            # 非注释行：停止扫描
            break

    return directives


# =============================================================================
# 类型定义
# =============================================================================

class LightType:
    """光明类型基类"""

    def __str__(self):
        return self.to_light()

    def to_light(self) -> str:
        raise NotImplementedError

    def to_python(self) -> str:
        raise NotImplementedError

    def is_compatible(self, other: 'LightType') -> bool:
        """检查类型兼容性"""
        return isinstance(other, type(self))


@dataclass(frozen=True)
class PrimitiveType(LightType):
    """基本类型"""
    name: str  # 整数、浮点、字符串、布尔、空
    python_name: str

    def to_light(self) -> str:
        return self.name

    def to_python(self) -> str:
        return self.python_name

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, PrimitiveType):
            return self.name == other.name
        if isinstance(other, UnionType):
            return any(self.is_compatible(t) for t in other.types)
        if isinstance(other, OptionalType):
            return self.is_compatible(other.inner_type)
        return False


@dataclass(frozen=True)
class ListType(LightType):
    """列表类型：列表<元素类型>"""
    element_type: LightType

    def to_light(self) -> str:
        return f"列表<{self.element_type.to_light()}>"

    def to_python(self) -> str:
        return f"list[{self.element_type.to_python()}]"

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, ListType):
            return self.element_type.is_compatible(other.element_type)
        return False


@dataclass(frozen=True)
class DictType(LightType):
    """字典类型：字典<键类型, 值类型>"""
    key_type: LightType
    value_type: LightType

    def to_light(self) -> str:
        return f"字典<{self.key_type.to_light()}, {self.value_type.to_light()}>"

    def to_python(self) -> str:
        return f"dict[{self.key_type.to_python()}, {self.value_type.to_python()}]"

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, DictType):
            return self.key_type.is_compatible(other.key_type) and self.value_type.is_compatible(other.value_type)
        return False


@dataclass(frozen=True)
class UnionType(LightType):
    """联合类型：整数|浮点、字符串|空"""
    types: Tuple[LightType, ...]

    def to_light(self) -> str:
        return '|'.join(t.to_light() for t in self.types)

    def to_python(self) -> str:
        return ' | '.join(t.to_python() for t in self.types)

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, UnionType):
            return any(self.is_compatible(t) for t in other.types)
        return any(t.is_compatible(other) for t in self.types)


@dataclass(frozen=True)
class OptionalType(LightType):
    """可选类型：可空整数"""
    inner_type: LightType

    def to_light(self) -> str:
        return f"可空{self.inner_type.to_light()}"

    def to_python(self) -> str:
        return f"Optional[{self.inner_type.to_python()}]"

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, OptionalType):
            return self.inner_type.is_compatible(other.inner_type)
        if isinstance(other, PrimitiveType) and other.name == '空':
            return True
        return self.inner_type.is_compatible(other)


@dataclass(frozen=True)
class FunctionType(LightType):
    """函数类型：(参数类型) -> 返回类型"""
    param_types: Tuple[LightType, ...]
    return_type: LightType

    def to_light(self) -> str:
        params = ', '.join(t.to_light() for t in self.param_types)
        return f"({params}) -> {self.return_type.to_light()}"

    def to_python(self) -> str:
        params = ', '.join(t.to_python() for t in self.param_types)
        return f"Callable[[{params}], {self.return_type.to_python()}]"

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, FunctionType):
            if len(self.param_types) != len(other.param_types):
                return False
            for s, o in zip(self.param_types, other.param_types):
                if not s.is_compatible(o):
                    return False
            return self.return_type.is_compatible(other.return_type)
        return False


@dataclass(frozen=True)
class AnyType(LightType):
    """任意类型（未标注或无法推导）"""

    def to_light(self) -> str:
        return "任意"

    def to_python(self) -> str:
        return "Any"

    def is_compatible(self, other: 'LightType') -> bool:
        return True  # 任意类型与任何类型兼容


@dataclass(frozen=True)
class TypeVarType(LightType):
    """泛型类型变量（如 T、K、V）
    
    用于表示泛型类型参数，如列表[T] 中的 T。
    """
    name: str

    def to_light(self) -> str:
        return self.name

    def to_python(self) -> str:
        return self.name

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, TypeVarType):
            return self.name == other.name
        # 类型变量与任何类型兼容（由合一过程决定）
        return True


@dataclass(frozen=True)
class GenericTypeInstance(LightType):
    """泛型类型实例化（如 列表[T]、字典[K, V]）"""
    base_name: str
    type_args: Tuple[LightType, ...]

    def to_light(self) -> str:
        args = ', '.join(t.to_light() for t in self.type_args)
        return f"{self.base_name}<{args}>"

    def to_python(self) -> str:
        args = ', '.join(t.to_python() for t in self.type_args)
        return f"{self.base_name}[{args}]"

    def is_compatible(self, other: 'LightType') -> bool:
        if isinstance(other, GenericTypeInstance):
            if self.base_name != other.base_name:
                return False
            if len(self.type_args) != len(other.type_args):
                return False
            return all(s.is_compatible(o) for s, o in zip(self.type_args, other.type_args))
        # 兼容具体的 ListType/DictType
        if isinstance(other, ListType) and self.base_name in ('列表', 'List'):
            if len(self.type_args) == 1:
                return self.type_args[0].is_compatible(other.element_type)
            return True
        if isinstance(other, DictType) and self.base_name in ('字典', 'Map'):
            if len(self.type_args) == 2:
                return self.type_args[0].is_compatible(other.key_type) and \
                       self.type_args[1].is_compatible(other.value_type)
            return True
        return False


# =============================================================================
# 类型构建器
# =============================================================================

# 内置基本类型
TYPE_INT = PrimitiveType('整数', 'int')
TYPE_FLOAT = PrimitiveType('浮点', 'float')
TYPE_STRING = PrimitiveType('字符串', 'str')
TYPE_BOOL = PrimitiveType('布尔', 'bool')
TYPE_NONE = PrimitiveType('空', 'None')
TYPE_ANY = AnyType()

# 类型名称映射
BUILTIN_TYPE_MAP: Dict[str, LightType] = {
    '整数': TYPE_INT, '整': TYPE_INT, 'int': TYPE_INT,
    '浮点': TYPE_FLOAT, '浮': TYPE_FLOAT, 'float': TYPE_FLOAT,
    '字符串': TYPE_STRING, '串': TYPE_STRING, 'str': TYPE_STRING,
    '布尔': TYPE_BOOL, 'bool': TYPE_BOOL,
    '真': TYPE_BOOL, '假': TYPE_BOOL,
    '空': TYPE_NONE, 'None': TYPE_NONE, 'null': TYPE_NONE, 'nil': TYPE_NONE,
    '任意': TYPE_ANY, 'Any': TYPE_ANY,
}

# 复合类型前缀
COMPOUND_PREFIXES = {
    '列表': 'list', '列': 'list',
    '字典': 'dict', '典': 'dict',
    '可空': 'optional',
}


def parse_type_annotation(annotation: str) -> LightType:
    """解析类型标注字符串为类型对象"""
    if not annotation or not annotation.strip():
        return TYPE_ANY

    annotation = annotation.strip()

    # 基本类型
    if annotation in BUILTIN_TYPE_MAP:
        return BUILTIN_TYPE_MAP[annotation]

    # 泛型类型变量：T、K、V、Key、Val 等（单字母大写或全大写标识符）
    if _looks_like_type_var(annotation):
        return TypeVarType(annotation)

    # 列表类型：列表<整数>（必须在 | 之前检查，防止泛型内的 | 被拆分）
    if annotation.startswith('列表<') and annotation.endswith('>'):
        inner = parse_type_annotation(annotation[3:-1])
        return ListType(inner)

    # 字典类型：字典<字符串, 整数>（必须在 | 之前检查）
    if annotation.startswith('字典<') and annotation.endswith('>'):
        inner = annotation[3:-1]
        if ',' in inner:
            key_str, val_str = inner.split(',', 1)
            key_type = parse_type_annotation(key_str.strip())
            val_type = parse_type_annotation(val_str.strip())
            return DictType(key_type, val_type)
        return DictType(TYPE_ANY, TYPE_ANY)

    # 泛型类型实例：基名<类型参数, ...>（支持任意泛型基名）
    if '<' in annotation and annotation.endswith('>'):
        bracket = annotation.index('<')
        base_name = annotation[:bracket].strip()
        args_str = annotation[bracket + 1:-1].strip()
        if args_str and ',' in args_str:
            # 多个类型参数
            parts = [p.strip() for p in args_str.split(',')]
            type_args = tuple(parse_type_annotation(p) for p in parts)
        elif args_str:
            # 单个类型参数
            type_args = (parse_type_annotation(args_str),)
        else:
            type_args = ()
        return GenericTypeInstance(base_name, type_args)

    # 可选类型：可空整数（必须在 | 之前检查）
    if annotation.startswith('可空'):
        inner = parse_type_annotation(annotation[2:])
        return OptionalType(inner)

    # 联合类型：整数|浮点（最后检查，避免泛型内的 | 被拆分）
    if '|' in annotation:
        parts = [parse_type_annotation(p.strip()) for p in annotation.split('|')]
        return UnionType(tuple(parts))

    # 未知类型，返回任意
    return TYPE_ANY


def _looks_like_type_var(name: str) -> bool:
    """判断是否看起来像类型变量"""
    if not name:
        return False
    if len(name) == 1 and name.isascii() and name.isupper():
        return True
    # 首字母大写（ASCII），后续字符为字母或数字（大小写不限）
    if len(name) <= 10 and name[0].isascii() and name[0].isupper():
        return all(c.isascii() and c.isalnum() for c in name)
    return False


# =============================================================================
# 类型环境
# =============================================================================

class TypeEnv:
    """类型环境：跟踪当前作用域中变量的类型"""

    def __init__(self, parent: Optional['TypeEnv'] = None):
        self.parent = parent
        self.variables: Dict[str, LightType] = {}
        self.functions: Dict[str, FunctionType] = {}

    def define(self, name: str, t: LightType):
        self.variables[name] = t

    def lookup(self, name: str) -> LightType:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        return TYPE_ANY

    def define_function(self, name: str, t: FunctionType):
        self.functions[name] = t

    def lookup_function(self, name: str) -> Optional[FunctionType]:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_function(name)
        return None

    def push_scope(self) -> 'TypeEnv':
        return TypeEnv(parent=self)

    def pop_scope(self) -> 'TypeEnv':
        return self.parent if self.parent else self


# =============================================================================
# 类型推导
# =============================================================================

def infer_type_from_value(value_node) -> LightType:
    """从 AST 值节点推导类型"""
    if value_node is None:
        return TYPE_NONE

    node_type = type(value_node).__name__

    # 字面量
    if node_type == 'NumberLiteral':
        if isinstance(value_node.value, float):
            return TYPE_FLOAT
        return TYPE_INT

    if node_type == 'StringLiteral':
        return TYPE_STRING

    if node_type == 'BooleanLiteral':
        return TYPE_BOOL

    if node_type == 'NullLiteral':
        return TYPE_NONE

    # 列表字面量
    if node_type == 'ListLiteral':
        if hasattr(value_node, 'elements') and value_node.elements:
            elem_types = [infer_type_from_value(e) for e in value_node.elements]
            if all(t == elem_types[0] for t in elem_types):
                return ListType(elem_types[0])
            return ListType(TYPE_ANY)
        return ListType(TYPE_ANY)

    # 字典字面量
    if node_type == 'DictLiteral':
        if hasattr(value_node, 'pairs') and value_node.pairs:
            key_types = []
            val_types = []
            for k, v in value_node.pairs:
                key_types.append(infer_type_from_value(k))
                val_types.append(infer_type_from_value(v))
            kt = key_types[0] if all(t == key_types[0] for t in key_types) else TYPE_ANY
            vt = val_types[0] if all(t == val_types[0] for t in val_types) else TYPE_ANY
            return DictType(kt, vt)
        return DictType(TYPE_ANY, TYPE_ANY)

    # 二元运算
    if node_type == 'BinaryOp':
        left_t = infer_type_from_value(value_node.left)
        right_t = infer_type_from_value(value_node.right)
        op = value_node.operator

        # 算术运算返回整数或浮点
        if op in ('+', '-', '*', '/', '%', '**', '//'):
            if left_t == TYPE_FLOAT or right_t == TYPE_FLOAT:
                return TYPE_FLOAT
            return TYPE_INT

        # 比较运算返回布尔
        if op in ('>', '<', '>=', '<=', '==', '!=', '且', '或', 'and', 'or'):
            return TYPE_BOOL

        return TYPE_ANY

    # 一元运算
    if node_type == 'UnaryOp':
        if value_node.operator == '非' or value_node.operator == 'not':
            return TYPE_BOOL
        return TYPE_ANY

    # 变量引用
    if node_type == 'Identifier':
        return TYPE_ANY  # 需要从环境中查找

    return TYPE_ANY


# =============================================================================
# 独立类型检查器（CLI 用）
# =============================================================================

class IssueLevel(Enum):
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass
class TypeIssue:
    level: IssueLevel
    message: str
    line: int = 0
    column: int = 0
    code: str = ''


class TypeChecker:
    """光明独立类型检查器（CLI 使用）"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues: List[TypeIssue] = []
        self.env = TypeEnv()
        self.current_module = None

    def check(self, module) -> List[TypeIssue]:
        """检查整个模块的类型"""
        self.issues = []
        self.env = TypeEnv()
        self.current_module = module

        for stmt in getattr(module, 'statements', []):
            self._check_stmt(stmt, self.env)

        for seg in getattr(module, 'segments', []):
            self._check_segment(seg)

        for cls in getattr(module, 'classes', []):
            self._check_class(cls)

        return self.issues

    def _issue(self, level: IssueLevel, message: str, line: int = 0, column: int = 0, code: str = ''):
        self.issues.append(TypeIssue(level=level, message=message, line=line, column=column, code=code))

    def _check_stmt(self, stmt, env: TypeEnv):
        node_type = type(stmt).__name__

        if node_type == 'VarDecl':
            self._check_var_decl(stmt, env)
        elif node_type == 'Assignment':
            self._check_assignment(stmt, env)
        elif node_type == 'ExpressionStatement':
            if hasattr(stmt, 'expression'):
                self._check_expr(stmt.expression, env)
        elif node_type == 'PrintStatement':
            if hasattr(stmt, 'value') and stmt.value:
                self._check_expr(stmt.value, env)
        elif node_type == 'ReturnStatement':
            if hasattr(stmt, 'value') and stmt.value:
                inferred = self._check_expr(stmt.value, env)
                func_env = self._find_function_env(env)
                if func_env:
                    func_type = func_env.get('_return_type')
                    if func_type and func_type != TYPE_ANY:
                        if not inferred.is_compatible(func_type):
                            self._issue(
                                IssueLevel.WARNING,
                                f"返回类型不匹配: 期望 {func_type.to_light()}，实际 {inferred.to_light()}",
                                line=getattr(stmt, 'line', 0), code='T001'
                            )
        elif node_type == 'IfStatement':
            if hasattr(stmt, 'condition'):
                self._check_expr(stmt.condition, env)
            inner_env = env.push_scope()
            for s in getattr(stmt, 'then_body', []):
                self._check_stmt(s, inner_env)
            if hasattr(stmt, 'else_body') and stmt.else_body:
                else_env = env.push_scope()
                for s in stmt.else_body:
                    self._check_stmt(s, else_env)
        elif node_type == 'WhileStatement':
            if hasattr(stmt, 'condition'):
                self._check_expr(stmt.condition, env)
            inner_env = env.push_scope()
            for s in getattr(stmt, 'body', []):
                self._check_stmt(s, inner_env)
        elif node_type == 'ForeachStatement':
            if hasattr(stmt, 'iterable'):
                self._check_expr(stmt.iterable, env)
            inner_env = env.push_scope()
            iterable_type = self._check_expr(stmt.iterable, env) if hasattr(stmt, 'iterable') else TYPE_ANY
            if isinstance(iterable_type, ListType):
                inner_env.define(stmt.variable, iterable_type.element_type)
            for s in getattr(stmt, 'body', []):
                self._check_stmt(s, inner_env)
        elif node_type == 'TryStatement':
            try_env = env.push_scope()
            for s in getattr(stmt, 'try_body', []):
                self._check_stmt(s, try_env)
            if hasattr(stmt, 'catch_body') and stmt.catch_body:
                catch_env = env.push_scope()
                if hasattr(stmt, 'catch_var') and stmt.catch_var:
                    catch_env.define(stmt.catch_var, TYPE_ANY)
                for s in stmt.catch_body:
                    self._check_stmt(s, catch_env)

    def _check_var_decl(self, stmt, env: TypeEnv):
        inferred_type = infer_type_from_value(stmt.value) if hasattr(stmt, 'value') and stmt.value else TYPE_ANY
        annotated_type = TYPE_ANY
        if hasattr(stmt, 'type_annotation') and stmt.type_annotation:
            annotated_type = parse_type_annotation(stmt.type_annotation)

        final_type = annotated_type if annotated_type != TYPE_ANY else inferred_type

        if annotated_type != TYPE_ANY and inferred_type != TYPE_ANY and inferred_type != TYPE_NONE:
            if not inferred_type.is_compatible(annotated_type):
                self._issue(
                    IssueLevel.ERROR if self.strict else IssueLevel.WARNING,
                    f"类型不匹配: 变量 '{stmt.name}' 标注为 {annotated_type.to_light()}，"
                    f"但值为 {inferred_type.to_light()} 类型",
                    line=getattr(stmt, 'line', 0), code='T001'
                )

        env.define(stmt.name, final_type)

    def _check_assignment(self, stmt, env: TypeEnv):
        if hasattr(stmt, 'target') and hasattr(stmt.target, 'name'):
            target_name = stmt.target.name
            existing_type = env.lookup(target_name)
            inferred_type = infer_type_from_value(stmt.value) if hasattr(stmt, 'value') and stmt.value else TYPE_ANY

            if existing_type != TYPE_ANY and inferred_type != TYPE_ANY:
                if not inferred_type.is_compatible(existing_type):
                    self._issue(
                        IssueLevel.WARNING,
                        f"赋值类型不匹配: '{target_name}' 原类型 {existing_type.to_light()}，"
                        f"新值类型 {inferred_type.to_light()}",
                        line=getattr(stmt, 'line', 0), code='T002'
                    )

    def _check_expr(self, expr, env: TypeEnv) -> LightType:
        if expr is None:
            return TYPE_NONE
        inferred = infer_type_from_value(expr)
        if hasattr(expr, 'name') and type(expr).__name__ == 'Identifier':
            env_type = env.lookup(expr.name)
            if env_type != TYPE_ANY:
                return env_type
        return inferred

    def _check_segment(self, seg):
        func_env = self.env.push_scope()

        param_types = []
        for param in getattr(seg, 'parameters', []):
            if hasattr(param, 'type_annotation') and param.type_annotation:
                param_type = parse_type_annotation(param.type_annotation)
            else:
                param_type = TYPE_ANY
            param_types.append(param_type)
            func_env.define(param.name, param_type)

        return_type = TYPE_ANY
        if hasattr(seg, 'return_type') and seg.return_type:
            return_type = parse_type_annotation(seg.return_type)

        func_env.variables['_return_type'] = return_type
        func_type = FunctionType(tuple(param_types), return_type)
        self.env.define_function(seg.name, func_type)

        for stmt in getattr(seg, 'body', []):
            self._check_stmt(stmt, func_env)

        if return_type != TYPE_ANY and return_type != TYPE_NONE:
            if not self._has_return_in_block(getattr(seg, 'body', [])):
                self._issue(
                    IssueLevel.WARNING,
                    f"段落 '{seg.name}' 声明返回类型 {return_type.to_light()}，但可能没有返回值",
                    line=getattr(seg, 'line', 0), code='T003'
                )

    def _check_class(self, cls):
        for attr in getattr(cls, 'attributes', []):
            if hasattr(attr, 'type_annotation') and attr.type_annotation:
                parse_type_annotation(attr.type_annotation)

        for method in getattr(cls, 'methods', []):
            self._check_segment(method)

    def _find_function_env(self, env: TypeEnv) -> Optional[Dict]:
        current = env
        while current:
            if '_return_type' in current.variables:
                return current.variables
            current = current.parent
        return None

    def _has_return_in_block(self, body: List) -> bool:
        for stmt in body:
            if type(stmt).__name__ == 'ReturnStatement':
                return True
            if type(stmt).__name__ == 'IfStatement':
                if hasattr(stmt, 'else_body') and stmt.else_body:
                    if self._has_return_in_block(stmt.then_body) and self._has_return_in_block(stmt.else_body):
                        return True
                elif self._has_return_in_block(getattr(stmt, 'then_body', [])):
                    return True
        return False


# =============================================================================
# 分级类型检查器（编译器集成用）
# =============================================================================

class GradedTypeChecker:
    """分级类型检查器 —— 与编译器集成，支持三级检查

    根据 TypeCheckerConfig 的 check_level 执行不同粒度的检查：
      - SIGNATURE：仅检查段落参数和返回值类型标注
      - VARIABLE：签名级 + 变量声明类型检查
      - EXPRESSION：变量级 + 表达式运算类型检查
    """

    def __init__(self, config: TypeCheckerConfig):
        self.config = config
        self.results: List[TypeCheckResult] = []
        self._errors: List[TypeCheckResult] = []
        self._warnings: List[TypeCheckResult] = []
        # 函数签名注册表：段落名 -> (参数类型列表, 返回类型)
        self._func_registry: Dict[str, Tuple[List[LightType], LightType]] = {}

    def check(self, module, inferencer=None) -> List[TypeCheckResult]:
        """执行分级类型检查

        当提供 inferencer（TypeInferencer 实例）时，变量级和表达式级检查会
        利用 inferencer 的类型缓存获得更准确的类型信息。
        """
        self.results = []
        self._errors = []
        self._warnings = []
        self._inferencer = inferencer  # 保存引用供内部方法使用

        level = self.config.check_level

        if level.value >= TypeCheckLevel.SIGNATURE.value:
            self._check_signatures(module)

        if level.value >= TypeCheckLevel.VARIABLE.value:
            self._check_variables(module, inferencer)

        if level.value >= TypeCheckLevel.EXPRESSION.value:
            self._check_expressions(module, inferencer)

        return self.results

    def _add_result(self, severity: TypeErrorSeverity, message: str, line: int = 0, column: int = 0, code: str = ''):
        r = TypeCheckResult(severity=severity, message=message, line=line, column=column, code=code)
        self.results.append(r)
        if severity == TypeErrorSeverity.ERROR:
            self._errors.append(r)
        else:
            self._warnings.append(r)

    def _check_signatures(self, module):
        """签名级检查：检查段落参数和返回值是否有类型标注

        SIGNATURE 级别下，对缺少类型标注的段落参数和返回值产生警告。
        严格模式（'严格' 修饰符或 STRICT 段模式）下，警告升级为错误。
        同时注册函数签名，供后续调用检查使用。
        """
        for seg in getattr(module, 'segments', []):
            modifiers = getattr(seg, 'modifiers', []) or []
            is_strict = '严格' in modifiers
            is_strict_mode = self.config.default_segment_mode == SegmentTypeMode.STRICT

            param_types = []
            # 检查参数类型标注
            for param in getattr(seg, 'parameters', []):
                has_annotation = hasattr(param, 'type_annotation') and param.type_annotation
                if not has_annotation:
                    if is_strict:
                        self._add_result(
                            TypeErrorSeverity.ERROR,
                            f"严格段落 '{seg.name}' 的参数 '{param.name}' 缺少类型标注",
                            line=getattr(seg, 'line', 0), code='S001'
                        )
                    else:
                        # SIGNATURE 级别下总是产生警告
                        self._add_result(
                            TypeErrorSeverity.WARNING,
                            f"段落 '{seg.name}' 的参数 '{param.name}' 缺少类型标注",
                            line=getattr(seg, 'line', 0), code='S002'
                        )
                    param_types.append(TYPE_ANY)
                else:
                    param_types.append(parse_type_annotation(param.type_annotation))

            # 检查返回类型标注
            has_return = hasattr(seg, 'return_type') and seg.return_type
            return_type = TYPE_ANY
            if not has_return:
                if is_strict:
                    self._add_result(
                        TypeErrorSeverity.ERROR,
                        f"严格段落 '{seg.name}' 缺少返回类型标注",
                        line=getattr(seg, 'line', 0), code='S003'
                    )
                else:
                    # SIGNATURE 级别下总是产生警告
                    self._add_result(
                        TypeErrorSeverity.WARNING,
                        f"段落 '{seg.name}' 缺少返回类型标注",
                        line=getattr(seg, 'line', 0), code='S004'
                    )
            else:
                return_type = parse_type_annotation(seg.return_type)

            # 注册函数签名
            self._func_registry[seg.name] = (param_types, return_type)

            # 检查返回语句与声明类型是否匹配
            if has_return and return_type != TYPE_ANY and return_type != TYPE_NONE:
                self._check_return_types(seg, return_type)
                # CFG 分析：检查所有路径是否都有返回值
                cfg_issues = CFGAnalyzer.check_missing_return(seg, return_type)
                for issue in cfg_issues:
                    self._add_result(
                        TypeErrorSeverity.WARNING,
                        issue,
                        line=getattr(seg, 'line', 0), code='S006'
                    )
                # 检查不可达代码
                unreachable = CFGAnalyzer.find_unreachable_code(getattr(seg, 'body', []))
                for line in unreachable:
                    if line > 0:
                        self._add_result(
                            TypeErrorSeverity.WARNING,
                            f"段落 '{seg.name}' 第{line}行代码不可达",
                            line=line, code='S007'
                        )

    def _check_variables(self, module, inferencer=None):
        """变量级检查：检查变量声明类型是否匹配（利用 inferencer 获得更准确类型）"""
        for stmt in getattr(module, 'statements', []):
            self._check_stmt_variables(stmt, inferencer)

        for seg in getattr(module, 'segments', []):
            for stmt in getattr(seg, 'body', []):
                self._check_stmt_variables(stmt, inferencer)

    def _check_stmt_variables(self, stmt, inferencer=None):
        if stmt is None:
            return
        node_type = type(stmt).__name__

        if node_type == 'VarDecl':
            if hasattr(stmt, 'type_annotation') and stmt.type_annotation:
                annotated = parse_type_annotation(stmt.type_annotation)
                if hasattr(stmt, 'value') and stmt.value:
                    inferred = _get_best_type(stmt.value, inferencer)
                    if inferred != TYPE_ANY and inferred != TYPE_NONE and annotated != TYPE_ANY:
                        if not inferred.is_compatible(annotated):
                            self._add_result(
                                TypeErrorSeverity.WARNING,
                                f"变量 '{stmt.name}' 类型不匹配: 标注 {annotated.to_light()}，"
                                f"实际 {inferred.to_light()}",
                                line=getattr(stmt, 'line', 0), code='V001'
                            )
        elif node_type == 'IfStatement':
            for s in getattr(stmt, 'then_body', []):
                self._check_stmt_variables(s, inferencer)
            for s in getattr(stmt, 'else_body', []) or []:
                self._check_stmt_variables(s, inferencer)
        elif node_type in ('WhileStatement', 'ForeachStatement', 'TryStatement'):
            for s in getattr(stmt, 'body', []):
                self._check_stmt_variables(s, inferencer)

    def _check_expressions(self, module, inferencer=None):
        """表达式级检查：检查表达式运算类型是否正确（利用 inferencer 获得更准确类型）"""
        for stmt in getattr(module, 'statements', []):
            self._check_stmt_expressions(stmt, inferencer)

        for seg in getattr(module, 'segments', []):
            for stmt in getattr(seg, 'body', []):
                self._check_stmt_expressions(stmt, inferencer)

    def _check_stmt_expressions(self, stmt, inferencer=None):
        if stmt is None:
            return
        node_type = type(stmt).__name__

        if node_type == 'IfStatement':
            if hasattr(stmt, 'condition'):
                cond_type = _get_best_type(stmt.condition, inferencer)
                if cond_type != TYPE_ANY and cond_type != TYPE_BOOL:
                    self._add_result(
                        TypeErrorSeverity.WARNING,
                        f"条件表达式类型应为布尔，实际为 {cond_type.to_light()}",
                        line=getattr(stmt, 'line', 0), code='E001'
                    )
            for s in getattr(stmt, 'then_body', []):
                self._check_stmt_expressions(s, inferencer)
            for s in getattr(stmt, 'else_body', []) or []:
                self._check_stmt_expressions(s, inferencer)
        elif node_type in ('WhileStatement', 'ForeachStatement'):
            if hasattr(stmt, 'condition'):
                cond_type = _get_best_type(stmt.condition, inferencer)
                if cond_type != TYPE_ANY and cond_type != TYPE_BOOL:
                    self._add_result(
                        TypeErrorSeverity.WARNING,
                        f"循环条件类型应为布尔，实际为 {cond_type.to_light()}",
                        line=getattr(stmt, 'line', 0), code='E001'
                    )
            for s in getattr(stmt, 'body', []):
                self._check_stmt_expressions(s, inferencer)
        elif node_type == 'BinaryOp':
            op = getattr(stmt, 'operator', '')
            if op in ('+', '-', '*', '/', '%', '**', '//'):
                left_t = _get_best_type(getattr(stmt, 'left', None), inferencer)
                right_t = _get_best_type(getattr(stmt, 'right', None), inferencer)
                if left_t != TYPE_ANY and right_t != TYPE_ANY:
                    if left_t not in (TYPE_INT, TYPE_FLOAT) or right_t not in (TYPE_INT, TYPE_FLOAT):
                        if left_t == TYPE_STRING and right_t == TYPE_STRING and op == '+':
                            pass  # 字符串拼接是合法的
                        elif left_t != TYPE_STRING or right_t != TYPE_STRING:
                            self._add_result(
                                TypeErrorSeverity.WARNING,
                                f"算术运算 '{op}' 需要数字类型，但得到 {left_t.to_light()} 和 {right_t.to_light()}",
                                line=getattr(stmt, 'line', 0), code='E002'
                            )
        elif node_type == 'ParagraphCall':
            # 检查函数调用参数类型
            self._check_function_call(stmt, inferencer)
        elif node_type == 'ReturnStatement':
            # 这里不做详细检查，返回值检查在 _check_return_types 中完成
            pass

    def _check_function_call(self, stmt, inferencer=None):
        """检查函数调用：验证参数类型是否与函数签名匹配"""
        func_name = getattr(stmt, 'name', '')
        if not func_name or func_name not in self._func_registry:
            return  # 未知函数，跳过检查

        param_types, return_type = self._func_registry[func_name]
        args = getattr(stmt, 'args', [])

        # 检查参数数量
        if len(args) != len(param_types):
            self._add_result(
                TypeErrorSeverity.WARNING,
                f"函数 '{func_name}' 期望 {len(param_types)} 个参数，但传入了 {len(args)} 个",
                line=getattr(stmt, 'line', 0), code='E003'
            )
            return

        # 检查每个参数类型
        for i, (arg, expected_type) in enumerate(zip(args, param_types)):
            if expected_type == TYPE_ANY:
                continue
            arg_type = _get_best_type(arg, inferencer)
            if arg_type != TYPE_ANY and arg_type != TYPE_NONE:
                if not arg_type.is_compatible(expected_type):
                    self._add_result(
                        TypeErrorSeverity.WARNING,
                        f"函数 '{func_name}' 第 {i+1} 个参数类型不匹配: "
                        f"期望 {expected_type.to_light()}，实际 {arg_type.to_light()}",
                        line=getattr(stmt, 'line', 0), code='E004'
                    )

    def _check_return_types(self, seg, declared_return_type: LightType):
        """检查段落中的返回语句是否与声明的返回类型匹配"""
        seg_name = getattr(seg, 'name', '')
        for stmt in getattr(seg, 'body', []):
            self._check_return_stmt(stmt, declared_return_type, seg_name)

    def _check_return_stmt(self, stmt, declared_return_type: LightType, seg_name: str):
        """递归检查返回语句（使用 inferencer 获得更准确类型）"""
        if stmt is None:
            return
        node_type = type(stmt).__name__

        if node_type == 'ReturnStatement':
            if hasattr(stmt, 'value') and stmt.value:
                inferred = _get_best_type(stmt.value, self._inferencer)
                if inferred != TYPE_ANY and inferred != TYPE_NONE:
                    if not inferred.is_compatible(declared_return_type):
                        self._add_result(
                            TypeErrorSeverity.WARNING,
                            f"段落 '{seg_name}' 返回类型不匹配: "
                            f"声明 {declared_return_type.to_light()}，实际 {inferred.to_light()}",
                            line=getattr(stmt, 'line', 0), code='S005'
                        )
        elif node_type == 'IfStatement':
            for s in getattr(stmt, 'then_body', []):
                self._check_return_stmt(s, declared_return_type, seg_name)
            for s in getattr(stmt, 'else_body', []) or []:
                self._check_return_stmt(s, declared_return_type, seg_name)
        elif node_type in ('WhileStatement', 'ForeachStatement', 'TryStatement'):
            for s in getattr(stmt, 'body', []):
                self._check_return_stmt(s, declared_return_type, seg_name)

    def get_errors(self) -> List[TypeCheckResult]:
        return self._errors

    def get_warnings(self) -> List[TypeCheckResult]:
        return self._warnings

    def has_errors(self) -> bool:
        return len(self._errors) > 0


# =============================================================================
# 类型系统桥接：在简单 LightType 与高级 Type 之间转换
# =============================================================================

class LightTypeBridge:
    """类型系统桥接器：在 type_checker 的简单类型系统与 type_inferencer 的高级类型系统之间转换

    两个类型系统：
      - 简单系统（type_checker）：LightType 层次（PrimitiveType, ListType, DictType, ...）
      - 高级系统（type_system）：Type 层次（NumberType, StringType, BooleanType, ...）

    桥接器提供双向转换，使 GradedTypeChecker 能利用 TypeInferencer 的推断结果。
    """

    # 简单 → 高级映射
    _SIMPLE_TO_ADVANCED = {
        '整数': 'NumberType', '整': 'NumberType', 'int': 'NumberType',
        '浮点': 'NumberType', '浮': 'NumberType', 'float': 'NumberType',
        '字符串': 'StringType', '串': 'StringType', 'str': 'StringType',
        '布尔': 'BooleanType', 'bool': 'BooleanType',
        '空': 'NullType', 'None': 'NullType', 'null': 'NullType', 'nil': 'NullType',
        '任意': 'AnyType', 'Any': 'AnyType',
    }

    @staticmethod
    def simple_to_advanced(simple_type: LightType) -> 'Any':
        """将简单 LightType 转换为高级 Type 对象"""
        try:
            from type_system import (
                NumberType, StringType, BooleanType, NullType, AnyType as AdvAnyType,
                UnknownType, ListType as AdvListType, DictType as AdvDictType,
                OptionalTypeWrapper, FunctionType as AdvFunctionType, TypeVar,
            )
        except ImportError:
            return None

        if isinstance(simple_type, AnyType):
            return AdvAnyType()
        if isinstance(simple_type, PrimitiveType):
            name = simple_type.name
            if name in ('整数', '整', 'int', '浮点', '浮', 'float'):
                return NumberType()
            if name in ('字符串', '串', 'str'):
                return StringType()
            if name in ('布尔', 'bool', '真', '假'):
                return BooleanType()
            if name in ('空', 'None', 'null', 'nil'):
                return NullType()
            return AdvAnyType()
        if isinstance(simple_type, ListType):
            elem = LightTypeBridge.simple_to_advanced(simple_type.element_type)
            return AdvListType(elem) if elem else AdvListType()
        if isinstance(simple_type, DictType):
            kt = LightTypeBridge.simple_to_advanced(simple_type.key_type)
            vt = LightTypeBridge.simple_to_advanced(simple_type.value_type)
            return AdvDictType(kt, vt)
        if isinstance(simple_type, OptionalType):
            inner = LightTypeBridge.simple_to_advanced(simple_type.inner_type)
            return OptionalTypeWrapper(inner) if inner else OptionalTypeWrapper()
        if isinstance(simple_type, UnionType):
            # 联合类型：简化为第一个非空类型或 Any
            for t in simple_type.types:
                if not isinstance(t, PrimitiveType) or t.name != '空':
                    return LightTypeBridge.simple_to_advanced(t)
            return AdvAnyType()
        if isinstance(simple_type, TypeVarType):
            from type_system import TypeVar as AdvTypeVar
            return AdvTypeVar(simple_type.name)
        if isinstance(simple_type, GenericTypeInstance):
            from type_system import GenericTypeInstance as AdvGenericInstance
            args = [LightTypeBridge.simple_to_advanced(a) for a in simple_type.type_args]
            return AdvGenericInstance(simple_type.base_name, args)
        return None

    @staticmethod
    def advanced_to_simple(adv_type: 'Any') -> LightType:
        """将高级 Type 对象转换为简单 LightType"""
        if adv_type is None:
            return TYPE_ANY

        try:
            from type_system import (
                NumberType, StringType, BooleanType, NullType, AnyType as AdvAnyType,
                UnknownType, ListType as AdvListType, DictType as AdvDictType,
                OptionalTypeWrapper, FunctionType as AdvFunctionType, TypeVar,
            )
        except ImportError:
            return TYPE_ANY

        type_id = getattr(adv_type, '_type_id', 0)
        from type_system import (
            TYPE_ID_NUMBER, TYPE_ID_STRING, TYPE_ID_BOOLEAN, TYPE_ID_NULL,
            TYPE_ID_ANY, TYPE_ID_UNKNOWN, TYPE_ID_OPTIONAL, TYPE_ID_LIST,
            TYPE_ID_DICT, TYPE_ID_FUNCTION, TYPE_ID_TVAR,
        )

        if type_id == TYPE_ID_NUMBER:
            return TYPE_INT
        if type_id == TYPE_ID_STRING:
            return TYPE_STRING
        if type_id == TYPE_ID_BOOLEAN:
            return TYPE_BOOL
        if type_id == TYPE_ID_NULL:
            return TYPE_NONE
        if type_id == TYPE_ID_ANY:
            return TYPE_ANY
        if type_id == TYPE_ID_UNKNOWN:
            return TYPE_ANY
        if type_id == TYPE_ID_OPTIONAL:
            inner = LightTypeBridge.advanced_to_simple(adv_type.inner_type)
            return OptionalType(inner)
        if type_id == TYPE_ID_LIST:
            elem = LightTypeBridge.advanced_to_simple(getattr(adv_type, 'element_type', None))
            return ListType(elem)
        if type_id == TYPE_ID_DICT:
            kt = LightTypeBridge.advanced_to_simple(getattr(adv_type, 'key_type', None))
            vt = LightTypeBridge.advanced_to_simple(getattr(adv_type, 'value_type', None))
            return DictType(kt, vt)
        if type_id == TYPE_ID_FUNCTION:
            params = tuple(LightTypeBridge.advanced_to_simple(p) for p in getattr(adv_type, 'param_types', []))
            ret = LightTypeBridge.advanced_to_simple(getattr(adv_type, 'return_type', None))
            return FunctionType(params, ret)
        # TypeVar 或其他泛型类型，返回 Any
        if type_id == TYPE_ID_TVAR:
            return TypeVarType(getattr(adv_type, 'name', '?'))
        if type_id == TYPE_ID_GENERIC_INSTANCE:
            base_name = getattr(adv_type, 'base_name', '?')
            args = tuple(LightTypeBridge.advanced_to_simple(a) for a in getattr(adv_type, 'type_args', []))
            return GenericTypeInstance(base_name, args)
        return TYPE_ANY


# =============================================================================
# CFG 控制流分析：返回值路径检查
# =============================================================================

class CFGAnalyzer:
    """控制流分析器：用于分析段落的返回路径

    核心功能：
      - 检测所有路径是否都有返回值
      - 检测不可达代码
      - 检测遗漏的返回路径
    """

    @staticmethod
    def all_paths_return(body: List[Any]) -> bool:
        """检查代码块的所有执行路径是否都有 return 语句"""
        return CFGAnalyzer._check_paths(body, set())

    @staticmethod
    def _check_paths(stmts: List[Any], visited: Set[int]) -> bool:
        """递归检查语句列表是否所有路径都返回"""
        for stmt in stmts:
            if stmt is None:
                continue
            stmt_id = id(stmt)
            if stmt_id in visited:
                continue
            visited.add(stmt_id)

            node_type = type(stmt).__name__

            if node_type == 'ReturnStatement':
                return True

            if node_type == 'IfStatement':
                then_returns = CFGAnalyzer._check_paths(
                    getattr(stmt, 'then_body', []), visited.copy()
                )
                else_body = getattr(stmt, 'else_body', []) or []
                if else_body:
                    else_returns = CFGAnalyzer._check_paths(else_body, visited.copy())
                    if then_returns and else_returns:
                        return True  # 双分支都返回，if 语句整体返回
                    # 否则继续检查后续语句
                else:
                    # 无 else 分支：if 分支不保证所有路径都返回
                    if then_returns:
                        # 如果 if 分支返回了，但后续还有代码，则后续代码可能不可达
                        return False

            elif node_type == 'ThrowStatement':
                return True  # 抛出异常也算终止

            elif node_type == 'WhileStatement':
                # 循环可能不执行，不保证返回
                body_returns = CFGAnalyzer._check_paths(
                    getattr(stmt, 'body', []), visited.copy()
                )
                # 即使循环体返回，循环也可能不执行，所以不保证
                continue

            elif node_type == 'ForeachStatement':
                body_returns = CFGAnalyzer._check_paths(
                    getattr(stmt, 'body', []), visited.copy()
                )
                # 遍历可能为空，不保证返回
                continue

            elif node_type == 'TryStatement':
                try_returns = CFGAnalyzer._check_paths(
                    getattr(stmt, 'try_body', []), visited.copy()
                )
                catch_body = getattr(stmt, 'catch_body', []) or []
                catch_returns = CFGAnalyzer._check_paths(catch_body, visited.copy()) if catch_body else False
                if not (try_returns and catch_returns):
                    return False

        return False

    @staticmethod
    def check_missing_return(seg, declared_return_type: LightType) -> List[str]:
        """检查段落是否缺少返回语句，返回问题列表"""
        issues = []
        body = getattr(seg, 'body', [])
        seg_name = getattr(seg, 'name', '未知')

        if declared_return_type is None or declared_return_type == TYPE_ANY or declared_return_type == TYPE_NONE:
            return issues

        # 空 body 不算缺失返回（可能只是声明）
        if not body:
            return issues

        if not CFGAnalyzer.all_paths_return(body):
            issues.append(
                f"段落 '{seg_name}' 声明返回类型 {declared_return_type.to_light()}，"
                f"但并非所有路径都有返回值"
            )

        return issues

    @staticmethod
    def find_unreachable_code(body: List[Any]) -> List[int]:
        """查找不可达代码的行号列表"""
        unreachable = []
        for i, stmt in enumerate(body):
            if stmt is None:
                continue
            if i > 0:
                prev = body[i - 1]
                prev_type = type(prev).__name__ if prev else ''
                if prev_type in ('ReturnStatement', 'ThrowStatement'):
                    unreachable.append(getattr(stmt, 'line', 0))
        return unreachable


# =============================================================================
# 增强的类型推断辅助（使用 TypeInferencer）
# =============================================================================

def _get_inferencer_type(node, inferencer) -> LightType:
    """从 TypeInferencer 的 type_cache 中获取节点类型并转换为简单类型"""
    if inferencer is None:
        return TYPE_ANY
    try:
        type_cache = inferencer.get_type_cache()
        if id(node) in type_cache:
            adv_type = type_cache[id(node)]
            return LightTypeBridge.advanced_to_simple(adv_type)
    except Exception:
        pass
    return TYPE_ANY


def _get_best_type(node, inferencer=None) -> LightType:
    """获取节点的最佳类型：优先使用 inferencer，回退到简单推断"""
    if inferencer is not None:
        t = _get_inferencer_type(node, inferencer)
        if t != TYPE_ANY:
            return t
    return infer_type_from_value(node)


# =============================================================================
# 工厂函数（编译器集成入口）
# =============================================================================

def create_checker_from_source(source: str, dc: LightConfig) -> GradedTypeChecker:
    """从源代码和 LightConfig 创建分级类型检查器

    从源文件头部的注释中提取类型检查指令并应用到配置。
    """
    config = TypeCheckerConfig.from_light_config(dc)
    config = config.apply_file_directives(source)
    return GradedTypeChecker(config)


def create_checker_from_config(dc: LightConfig) -> GradedTypeChecker:
    """从 LightConfig 创建分级类型检查器（无源代码指令）"""
    config = TypeCheckerConfig.from_light_config(dc)
    return GradedTypeChecker(config)


# =============================================================================
# 便捷函数
# =============================================================================

def check_module(module, strict: bool = False) -> List[TypeIssue]:
    """检查模块的类型（独立检查器）"""
    checker = TypeChecker(strict=strict)
    return checker.check(module)


def check_source(source: str, strict: bool = False) -> Tuple[List[TypeIssue], Optional[Any]]:
    """检查源代码的类型（独立检查器）"""
    try:
        from light_parser_v3 import LightParser
        parser = LightParser()
        module = parser.parse(source)
        issues = check_module(module, strict=strict)
        return issues, module
    except Exception as e:
        return [TypeIssue(
            level=IssueLevel.ERROR,
            message=f"解析错误: {e}",
            code='PARSE_ERROR'
        )], None


def format_issues(issues: List[TypeIssue], source: str = '') -> str:
    """格式化类型检查问题为可读文本"""
    if not issues:
        return "未发现类型问题"

    lines = []
    for issue in issues:
        icon = {'error': 'E', 'warning': 'W', 'info': 'I'}
        loc = f"第{issue.line}行" if issue.line else ""
        code = f"[{issue.code}]" if issue.code else ""
        lines.append(f"{icon.get(issue.level.value, '?')} {code} {loc}: {issue.message}")

    return '\n'.join(lines)


# =============================================================================
# CLI 入口
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='光明类型检查器')
    parser.add_argument('source', nargs='?', help='源文件 (.light)')
    parser.add_argument('--strict', action='store_true', help='严格模式：类型不匹配报错')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')

    args = parser.parse_args()

    if args.source:
        with open(args.source, 'r', encoding='utf-8') as f:
            source = f.read()
    else:
        source = sys.stdin.read()

    issues, module = check_source(source, strict=args.strict)

    if args.json:
        import json
        result = [{
            'level': i.level.value,
            'message': i.message,
            'line': i.line,
            'column': i.column,
            'code': i.code,
        } for i in issues]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_issues(issues, source))

    if any(i.level == IssueLevel.ERROR for i in issues):
        sys.exit(1)