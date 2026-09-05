"""
光明（Light）编程语言 AST 节点定义

与 src/ast_nodes.py 保持兼容的 AST 节点结构
供 ANTLR 解析器生成 AST 使用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union, Any


# =============================================================================
# 基础节点
# =============================================================================

# =============================================================================
# AST 类型 ID 常量（整数分派用，替代 isinstance 字符串比较）
# =============================================================================

AST_TYPE_ID_NUMBER_LITERAL = 1
AST_TYPE_ID_STRING_LITERAL = 2
AST_TYPE_ID_BOOLEAN_LITERAL = 3
AST_TYPE_ID_NULL_LITERAL = 4
AST_TYPE_ID_SELF_REFERENCE = 5
AST_TYPE_ID_IDENTIFIER = 6
AST_TYPE_ID_SEGMENT_NAME = 7
AST_TYPE_ID_MODULE_NAME = 8
AST_TYPE_ID_BINARY_OP = 9
AST_TYPE_ID_UNARY_OP = 10
AST_TYPE_ID_FUNCTION_CALL = 11
AST_TYPE_ID_PIPE_EXPRESSION = 12
AST_TYPE_ID_PROPERTY_ACCESS = 13
AST_TYPE_ID_INDEX_ACCESS = 14
AST_TYPE_ID_LIST_LITERAL = 15
AST_TYPE_ID_DICT_ENTRY = 16
AST_TYPE_ID_DICT_LITERAL = 17
AST_TYPE_ID_NEW_EXPRESSION = 18
AST_TYPE_ID_CONDITIONAL_EXPRESSION = 19
AST_TYPE_ID_STRING_INTERPOLATION = 20
AST_TYPE_ID_LIST_COMPREHENSION = 21
AST_TYPE_ID_LAMBDA_EXPRESSION = 22
AST_TYPE_ID_MATCH_STATEMENT = 23
AST_TYPE_ID_MATCH_CASE = 24
AST_TYPE_ID_MATCH_PATTERN = 25
AST_TYPE_ID_DICT_COMPREHENSION = 26
AST_TYPE_ID_DECORATOR_DEFINITION = 27
AST_TYPE_ID_DESTRUCTURING_ASSIGNMENT = 28
AST_TYPE_ID_WITH_STATEMENT = 29
AST_TYPE_ID_VARIABLE_DECLARATION = 30
AST_TYPE_ID_ASSIGNMENT = 31
AST_TYPE_ID_COMPOUND_ASSIGNMENT = 32
AST_TYPE_ID_IF_STATEMENT = 33
AST_TYPE_ID_FOREACH_STATEMENT = 34
AST_TYPE_ID_WHILE_STATEMENT = 35
AST_TYPE_ID_BREAK_STATEMENT = 36
AST_TYPE_ID_CONTINUE_STATEMENT = 37
AST_TYPE_ID_RETURN_STATEMENT = 38
AST_TYPE_ID_CATCH_CLAUSE = 39
AST_TYPE_ID_TRY_STATEMENT = 40
AST_TYPE_ID_THROW_STATEMENT = 41
AST_TYPE_ID_PRINT_STATEMENT = 42
AST_TYPE_ID_EXPRESSION_STATEMENT = 43
AST_TYPE_ID_EMBED_BLOCK = 44
AST_TYPE_ID_PARAMETER = 45
AST_TYPE_ID_AWAIT_EXPRESSION = 46
AST_TYPE_ID_DEFER_STATEMENT = 47
AST_TYPE_ID_ASYNC_SCOPE = 48
AST_TYPE_ID_SEGMENT_DEFINITION = 49
AST_TYPE_ID_DATA_TYPE_FIELD = 50
AST_TYPE_ID_ATTRIBUTE_DECLARATION = 51
AST_TYPE_ID_DATA_TYPE_DEFINITION = 52
AST_TYPE_ID_ERROR_TYPE_DEFINITION = 53
AST_TYPE_ID_METHOD_DEFINITION = 54
AST_TYPE_ID_CONSTRUCTOR_DEFINITION = 55
AST_TYPE_ID_CLASS_DEFINITION = 56
AST_TYPE_ID_INTERFACE_METHOD = 57
AST_TYPE_ID_INTERFACE_PROPERTY = 58
AST_TYPE_ID_INTERFACE_DEFINITION = 59
AST_TYPE_ID_GENERIC_TYPE = 60
AST_TYPE_ID_GENERIC_PARAMETER_DECL = 61
AST_TYPE_ID_ENUM_VARIANT = 62
AST_TYPE_ID_ENUM_DEFINITION = 63
AST_TYPE_ID_TRAIT_METHOD_SIGNATURE = 64
AST_TYPE_ID_TRAIT_DEFINITION = 65
AST_TYPE_ID_TRAIT_IMPLEMENTATION = 66
AST_TYPE_ID_UNWRAP_EXPRESSION = 67
AST_TYPE_ID_OPTIONAL_TYPE = 68
AST_TYPE_ID_TYPE_ALIAS = 69
AST_TYPE_ID_IMPORT_STATEMENT = 70
AST_TYPE_ID_EXPORT_STATEMENT = 71
AST_TYPE_ID_FFI_LOAD_LIBRARY = 72
AST_TYPE_ID_FFI_FUNCTION_DECL = 73
AST_TYPE_ID_FFI_STRUCT_DEF = 74
AST_TYPE_ID_FFI_CALLBACK_DEF = 75
AST_TYPE_ID_FFI_POINTER_TYPE = 76
AST_TYPE_ID_FFI_ARRAY_TYPE = 77
AST_TYPE_ID_FFI_ADDRESS_OF = 78
AST_TYPE_ID_FFI_DEREFERENCE = 79
AST_TYPE_ID_FFI_POINTER_OFFSET = 80
AST_TYPE_ID_FFI_SET_POINTER_VALUE = 81
AST_TYPE_ID_FFI_ALLOC_MEMORY = 82
AST_TYPE_ID_FFI_FREE_MEMORY = 83
AST_TYPE_ID_FFI_CREATE_ARRAY = 84
AST_TYPE_ID_FFI_SET_ARRAY_ELEMENT = 85
AST_TYPE_ID_FFI_GET_LAST_ERROR = 86
AST_TYPE_ID_FFI_GET_ERRNO = 87
AST_TYPE_ID_FFI_SET_ERRNO = 88
AST_TYPE_ID_FFI_TRY_CATCH = 89
AST_TYPE_ID_FFI_ENUM_DEF = 90
AST_TYPE_ID_FFI_UNION_DEF = 91
AST_TYPE_ID_FFI_CREATE_CALLBACK = 92
AST_TYPE_ID_FFI_VAR_ARGS_DECL = 93
AST_TYPE_ID_FFI_STRUCT_BY_VALUE = 94
AST_TYPE_ID_FFI_LIBRARY_PATH = 95
AST_TYPE_ID_FFI_TYPEDEF_DEF = 96
AST_TYPE_ID_FFI_BITFIELD_DEF = 97
AST_TYPE_ID_FFI_FUNC_PTR_DEF = 98
AST_TYPE_ID_FFI_DEBUG_CONFIG = 99
AST_TYPE_ID_FFI_PREPROCESSOR_DEF = 100
AST_TYPE_ID_MODULE = 101
AST_TYPE_ID_KEYWORD_ARG = 102
AST_TYPE_ID_TUPLE_LITERAL = 103
# R10-11b（第四批B）：生成器。v3 的 `生成 表达式。` / `生成 全部 表达式。`
# 此前在 AstAdapter 里没有转换器，被降级成 `<unknown:YieldStmt>` 标识符，
# 原生腿只能拒绝。此处补一等节点，供适配层转型 + codegen 分派。
# 节点 ID 用 104（103 已分配给 R10-11a 的 TupleLiteral）。
AST_TYPE_ID_YIELD_STATEMENT = 104


@dataclass(slots=True)
class ASTNode:
    """AST 节点基类"""
    line: int = 0
    column: int = 0
    _ast_type_id: int = 0  # 子类覆盖


# =============================================================================
# 字面量节点
# =============================================================================

@dataclass(slots=True)
class NumberLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_NUMBER_LITERAL, init=False, repr=False)
    """数字字面量"""
    value: Union[int, float] = 0


@dataclass(slots=True)
class StringLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_STRING_LITERAL, init=False, repr=False)
    """字符串字面量"""
    value: str = ""


@dataclass(slots=True)
class BooleanLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_BOOLEAN_LITERAL, init=False, repr=False)
    """布尔字面量"""
    value: bool = False


@dataclass(slots=True)
class NullLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_NULL_LITERAL, init=False, repr=False)
    """空值字面量"""
    pass


@dataclass(slots=True)
class SelfReference(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_SELF_REFERENCE, init=False, repr=False)
    """self引用（己）"""
    pass


# =============================================================================
# 标识符与名称节点
# =============================================================================

@dataclass(slots=True)
class Identifier(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_IDENTIFIER, init=False, repr=False)
    """标识符（变量名、段落名引用等）"""
    name: str = ""


@dataclass(slots=True)
class SegmentName(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_SEGMENT_NAME, init=False, repr=False)
    """段落名（《名称》）"""
    name: str = ""


@dataclass(slots=True)
class ModuleName(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_MODULE_NAME, init=False, repr=False)
    """模块/篇名（【名称】）"""
    name: str = ""


# =============================================================================
# 表达式节点
# =============================================================================

@dataclass(slots=True)
class BinaryOp(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_BINARY_OP, init=False, repr=False)
    """二元运算"""
    left: ASTNode = None
    operator: str = ""
    right: ASTNode = None


@dataclass(slots=True)
class UnaryOp(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_UNARY_OP, init=False, repr=False)
    """一元运算"""
    operator: str = ""
    operand: ASTNode = None


@dataclass(slots=True)
class FunctionCall(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FUNCTION_CALL, init=False, repr=False)
    """函数/段落调用"""
    name: Union[SegmentName, Identifier] = None
    arguments: List[ASTNode] = field(default_factory=list)
    type_args: List[str] = field(default_factory=list)  # 显式类型参数（如 映射[数](...)）


@dataclass(slots=True)
class PipeExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_PIPE_EXPRESSION, init=False, repr=False)
    """管道表达式（-> 或 并 连接）"""
    expressions: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class PropertyAccess(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_PROPERTY_ACCESS, init=False, repr=False)
    """属性访问（之字结构：对象之属性）"""
    obj: ASTNode = None
    property_name: str = ""


@dataclass(slots=True)
class IndexAccess(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_INDEX_ACCESS, init=False, repr=False)
    """索引访问（对象[索引]）"""
    obj: ASTNode = None
    index: ASTNode = None


@dataclass(slots=True)
class ListLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_LIST_LITERAL, init=False, repr=False)
    """列表字面量"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class TupleLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TUPLE_LITERAL, init=False, repr=False)
    """元组字面量"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class DictEntry(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DICT_ENTRY, init=False, repr=False)
    """典条目（键值对）"""
    key: ASTNode = None
    value: ASTNode = None


@dataclass(slots=True)
class DictLiteral(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DICT_LITERAL, init=False, repr=False)
    """典字面量（字典）"""
    entries: List[DictEntry] = field(default_factory=list)


@dataclass(slots=True)
class NewExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_NEW_EXPRESSION, init=False, repr=False)
    """类实例化表达式（新类名()）"""
    class_name: str = ""
    arguments: List[ASTNode] = field(default_factory=list)
    type_args: List[str] = field(default_factory=list)  # 显式类型参数（如 数组[数](3)）


@dataclass(slots=True)
class ConditionalExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_CONDITIONAL_EXPRESSION, init=False, repr=False)
    """三元条件表达式：如果 条件 那么 值1 否则 值2"""
    condition: ASTNode = None
    then_expr: ASTNode = None
    else_expr: Optional[ASTNode] = None


@dataclass(slots=True)
class StringInterpolation(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_STRING_INTERPOLATION, init=False, repr=False)
    """字符串插值："你好，{名字}" -> f-string"""
    parts: List[Union[str, ASTNode]] = field(default_factory=list)  # 交替的字符串和表达式


@dataclass(slots=True)
class ListComprehension(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_LIST_COMPREHENSION, init=False, repr=False)
    """列表推导：[表达式 遍历 变量 之 列表]"""
    expression: ASTNode = None          # 输出表达式
    variable: str = ""                   # 遍历变量
    iterable: ASTNode = None            # 可迭代对象
    condition: Optional[ASTNode] = None # 可选过滤条件


@dataclass(slots=True)
class LambdaExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_LAMBDA_EXPRESSION, init=False, repr=False)
    """匿名函数：接收 甲：返回 甲 乘 甲。"""
    parameters: List[Parameter] = field(default_factory=list)
    body: ASTNode = None                # 表达式体
    body_statements: List[ASTNode] = field(default_factory=list)  # 多语句体（C风格匿名函数）


@dataclass(slots=True)
class MatchStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_MATCH_STATEMENT, init=False, repr=False)
    """模式匹配：匹配 值：情况 ... 结束。"""
    subject: ASTNode = None             # 被匹配的值
    cases: List['MatchCase'] = field(default_factory=list)


@dataclass(slots=True)
class MatchCase(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_MATCH_CASE, init=False, repr=False)
    """匹配分支"""
    pattern: 'MatchPattern' = None      # 匹配模式
    guard: Optional[ASTNode] = None     # 守卫条件（情况 模式 如果 条件）
    body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class MatchPattern(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_MATCH_PATTERN, init=False, repr=False)
    """匹配模式"""
    kind: str = ""                      # 'number', 'string', 'bool', 'null', 'variable', 'wildcard', 'list', 'type_check'
    value: Optional[ASTNode] = None     # 字面量值或变量名
    elements: List['MatchPattern'] = field(default_factory=list)  # 列表模式元素
    type_name: str = ""                 # 类型检查模式中的类型名
    binding: str = ""                   # 变量绑定名


@dataclass(slots=True)
class DictComprehension(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DICT_COMPREHENSION, init=False, repr=False)
    """字典推导：{键: 值 遍历 变量 之 列表}"""
    key_expr: ASTNode = None            # 键表达式
    value_expr: ASTNode = None          # 值表达式
    variable: str = ""                   # 遍历变量
    iterable: ASTNode = None            # 可迭代对象
    condition: Optional[ASTNode] = None # 可选过滤条件


@dataclass(slots=True)
class DecoratorDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DECORATOR_DEFINITION, init=False, repr=False)
    """装饰器定义：@段落名 标注 段落 ..."""
    decorator_name: str = ""            # 装饰器段落名
    paragraph: 'SegmentDefinition' = None  # 被装饰的段落


@dataclass(slots=True)
class DestructuringAssignment(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DESTRUCTURING_ASSIGNMENT, init=False, repr=False)
    """解构赋值：设 (甲, 乙) 为 元组"""
    variables: List[str] = field(default_factory=list)  # 解构变量列表
    value: ASTNode = None               # 被解构的值


@dataclass(slots=True)
class WithStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_WITH_STATEMENT, init=False, repr=False)
    """上下文管理器：使用 表达式 作为 变量：...结束。"""
    context_expr: ASTNode = None        # 上下文表达式
    variable: Optional[str] = None      # 可选的 as 变量
    body: List[ASTNode] = field(default_factory=list)


# =============================================================================
# 语句节点
# =============================================================================

@dataclass(slots=True)
class VariableDeclaration(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_VARIABLE_DECLARATION, init=False, repr=False)
    """变量声明"""
    name: str = ""
    value: ASTNode = None
    type_annotation: Optional[str] = None
    is_mutable: bool = False
    destructure_names: List[str] = field(default_factory=list)  # 解构赋值变量名列表


@dataclass(slots=True)
class Assignment(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ASSIGNMENT, init=False, repr=False)
    """赋值语句"""
    target: ASTNode = None
    value: ASTNode = None


@dataclass(slots=True)
class CompoundAssignment(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_COMPOUND_ASSIGNMENT, init=False, repr=False)
    """复合赋值（甲 加上 1 → 甲 += 1）"""
    target: str = ""        # 变量名
    operator: str = ""      # '加', '减', '乘', '除', '模', '幂'
    value: ASTNode = None


@dataclass(slots=True)
class IfStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_IF_STATEMENT, init=False, repr=False)
    """条件语句"""
    condition: ASTNode = None
    then_body: List[ASTNode] = field(default_factory=list)
    else_body: Optional[List[ASTNode]] = None
    elseif_conditions: List[ASTNode] = field(default_factory=list)
    elseif_bodies: List[List[ASTNode]] = field(default_factory=list)


@dataclass(slots=True)
class ForeachStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FOREACH_STATEMENT, init=False, repr=False)
    """遍历循环"""
    variable: str = ""
    iterable: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class WhileStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_WHILE_STATEMENT, init=False, repr=False)
    """当循环"""
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class BreakStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_BREAK_STATEMENT, init=False, repr=False)
    """跳出语句"""
    pass


@dataclass(slots=True)
class ContinueStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_CONTINUE_STATEMENT, init=False, repr=False)
    """跳过语句"""
    pass


@dataclass(slots=True)
class ReturnStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_RETURN_STATEMENT, init=False, repr=False)
    """返回语句"""
    value: Optional[ASTNode] = None


@dataclass(slots=True)
class CatchClause(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_CATCH_CLAUSE, init=False, repr=False)
    """捕获子句"""
    catch_type: str = ""
    catch_var: str = ""
    catch_body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class TryStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TRY_STATEMENT, init=False, repr=False)
    """异常捕获"""
    try_body: List[ASTNode] = field(default_factory=list)
    catch_clauses: List[CatchClause] = field(default_factory=list)
    catch_type: str = ""       # 异常类型（如 "ValueError"）- 向后兼容
    catch_var: str = ""         # 异常变量名 - 向后兼容
    catch_body: List[ASTNode] = field(default_factory=list)  # 向后兼容
    finally_body: List[ASTNode] = field(default_factory=list)  # finally 块


@dataclass(slots=True)
class ThrowStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_THROW_STATEMENT, init=False, repr=False)
    """抛出异常"""
    value: ASTNode = None


@dataclass(slots=True)
class PrintStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_PRINT_STATEMENT, init=False, repr=False)
    """打印/输出语句"""
    value: ASTNode = None


@dataclass(slots=True)
class KeywordArg(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_KEYWORD_ARG, init=False, repr=False)
    """关键字参数：f(名=值)。原生腿按目标函数参数名映射到位置。"""
    name: str = ""
    value: ASTNode = None


@dataclass(slots=True)
class YieldStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_YIELD_STATEMENT, init=False, repr=False)
    """生成语句（生成器产出）。

    `生成 表达式。` → value=表达式, is_from=False
    `生成 全部 表达式。` → yield from（生成器委托），原生腿暂不支持，
    由 codegen 显式拒绝（不许静默降级成 `生成 表达式`）。
    """
    value: Optional[ASTNode] = None
    is_from: bool = False


@dataclass(slots=True)
class ExpressionStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_EXPRESSION_STATEMENT, init=False, repr=False)
    """表达式语句"""
    expression: ASTNode = None


@dataclass(slots=True)
class EmbedBlock(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_EMBED_BLOCK, init=False, repr=False)
    """嵌入块语句：嵌入 Python/C: ... 结束嵌入"""
    language: str = ""       # "Python", "C" 等
    code: str = ""           # 原始嵌入代码
    imports: list = None     # 嵌入块中需要传入的光明变量名列表
    exports: list = None     # 嵌入块中需要传出的变量名列表


# =============================================================================
# 段落定义节点
# =============================================================================

@dataclass(slots=True)
class Parameter(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_PARAMETER, init=False, repr=False)
    """参数定义"""
    name: str = ""
    type_annotation: Optional[str] = None
    default_value: Optional[ASTNode] = None


# =============================================================================
# 异步/并发节点
# =============================================================================

@dataclass(slots=True)
class AwaitExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_AWAIT_EXPRESSION, init=False, repr=False)
    """等待表达式（等待 异步操作）"""
    expression: ASTNode = None


@dataclass(slots=True)
class DeferStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DEFER_STATEMENT, init=False, repr=False)
    """推迟语句（推迟 语句 — 在作用域退出时执行）"""
    body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class AsyncScope(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ASYNC_SCOPE, init=False, repr=False)
    """并行作用域（结构化并发）：并行 { 任务1 任务2 }"""
    tasks: List[ASTNode] = field(default_factory=list)
    result_vars: List[str] = field(default_factory=list)  # 可选的返回结果变量
    timeout: Optional[ASTNode] = None  # 可选超时


@dataclass(slots=True)
class SegmentDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_SEGMENT_DEFINITION, init=False, repr=False)
    """段落定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
    return_type: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    generic_params: List[str] = field(default_factory=list)  # 泛型参数列表（如 ["T", "U"]）


# =============================================================================
# 数据/错误类型定义
# =============================================================================

@dataclass(slots=True)
class DataTypeField(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DATA_TYPE_FIELD, init=False, repr=False)
    """数据类型字段"""
    name: str = ""
    type_annotation: str = ""


@dataclass(slots=True)
class AttributeDeclaration(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ATTRIBUTE_DECLARATION, init=False, repr=False)
    """属性声明（类定义中使用）"""
    name: str = ""
    type_annotation: Optional[str] = None
    default_value: Optional[ASTNode] = None


@dataclass(slots=True)
class DataTypeDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_DATA_TYPE_DEFINITION, init=False, repr=False)
    """数据类型定义"""
    name: str = ""
    fields: List[DataTypeField] = field(default_factory=list)


@dataclass(slots=True)
class ErrorTypeDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ERROR_TYPE_DEFINITION, init=False, repr=False)
    """错误类型定义"""
    name: str = ""
    fields: List[DataTypeField] = field(default_factory=list)


# =============================================================================
# 类和接口定义
# =============================================================================

@dataclass(slots=True)
class MethodDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_METHOD_DEFINITION, init=False, repr=False)
    """方法定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
    return_type: Optional[str] = None
    is_static: bool = False
    generic_params: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ConstructorDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_CONSTRUCTOR_DEFINITION, init=False, repr=False)
    """构造函数定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)


@dataclass(slots=True)
class ClassDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_CLASS_DEFINITION, init=False, repr=False)
    """类定义"""
    name: str = ""
    generic_params: List[str] = field(default_factory=list)  # 泛型参数列表
    superclasses: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    fields: List[ASTNode] = field(default_factory=list)  # 包含 varDecl
    methods: List[MethodDefinition] = field(default_factory=list)
    constructor: Optional[ConstructorDefinition] = None


@dataclass(slots=True)
class InterfaceMethod(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_INTERFACE_METHOD, init=False, repr=False)
    """接口方法签名"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: str = ""


@dataclass(slots=True)
class InterfaceProperty(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_INTERFACE_PROPERTY, init=False, repr=False)
    """接口属性签名"""
    name: str = ""
    type_annotation: str = ""


@dataclass(slots=True)
class InterfaceDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_INTERFACE_DEFINITION, init=False, repr=False)
    """接口定义"""
    name: str = ""
    superinterfaces: List[str] = field(default_factory=list)
    methods: List[InterfaceMethod] = field(default_factory=list)
    properties: List[InterfaceProperty] = field(default_factory=list)


# =============================================================================
# 类型注解节点（泛型支持）
# =============================================================================

@dataclass(slots=True)
class GenericType(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_GENERIC_TYPE, init=False, repr=False)
    """泛型类型（如 列表[数]、字典[串, 数]）"""
    base_type: str = ""
    type_arguments: List[str] = field(default_factory=list)


@dataclass(slots=True)
class GenericParameterDecl(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_GENERIC_PARAMETER_DECL, init=False, repr=False)
    """泛型参数声明"""
    name: str = ""
    constraint: Optional[str] = None  # 可选的上界约束


# =============================================================================
# 枚举/代数数据类型（ADT）
# =============================================================================

@dataclass(slots=True)
class EnumVariant(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ENUM_VARIANT, init=False, repr=False)
    """枚举变体"""
    name: str = ""
    fields: List[DataTypeField] = field(default_factory=list)  # 携带的数据字段


@dataclass(slots=True)
class EnumDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_ENUM_DEFINITION, init=False, repr=False)
    """枚举/代数数据类型定义"""
    name: str = ""
    generic_params: List[str] = field(default_factory=list)
    variants: List[EnumVariant] = field(default_factory=list)
    derives: List[str] = field(default_factory=list)  # 派生 trait（如 相等, 比较）


# =============================================================================
# Trait/接口系统增强
# =============================================================================

@dataclass(slots=True)
class TraitMethodSignature(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TRAIT_METHOD_SIGNATURE, init=False, repr=False)
    """Trait 方法签名"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: str = ""
    has_default: bool = False  # 是否有默认实现


@dataclass(slots=True)
class TraitDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TRAIT_DEFINITION, init=False, repr=False)
    """Trait 定义"""
    name: str = ""
    generic_params: List[str] = field(default_factory=list)
    methods: List[TraitMethodSignature] = field(default_factory=list)
    super_traits: List[str] = field(default_factory=list)


@dataclass(slots=True)
class TraitImplementation(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TRAIT_IMPLEMENTATION, init=False, repr=False)
    """Trait 实现"""
    trait_name: str = ""
    type_name: str = ""
    methods: List[MethodDefinition] = field(default_factory=list)
    generic_args: List[str] = field(default_factory=list)  # 泛型实参


# =============================================================================
# 空安全类型
# =============================================================================

@dataclass(slots=True)
class UnwrapExpression(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_UNWRAP_EXPRESSION, init=False, repr=False)
    """解包表达式（值! 或 unwrap(值)）"""
    value: Any = None


@dataclass(slots=True)
class OptionalType(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_OPTIONAL_TYPE, init=False, repr=False)
    """可空类型（如 数|空）"""
    inner_type: str = ""


# =============================================================================
# 类型别名
# =============================================================================

@dataclass(slots=True)
class TypeAlias(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_TYPE_ALIAS, init=False, repr=False)
    """类型别名定义"""
    name: str = ""
    target_type: str = ""
    generic_params: List[str] = field(default_factory=list)


# =============================================================================
# 模块节点
# =============================================================================

@dataclass(slots=True)
class ImportStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_IMPORT_STATEMENT, init=False, repr=False)
    """导入语句"""
    module: str = ""
    names: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ExportStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_EXPORT_STATEMENT, init=False, repr=False)
    """导出语句"""
    name: str = ""
    names: List[str] = field(default_factory=list)


# =============================================================================
# C FFI 节点（外部函数接口）
# =============================================================================

@dataclass(slots=True)
class FFILoadLibraryStatement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_LOAD_LIBRARY, init=False, repr=False)
    """加载动态库：加载库 "libxxx.so" 为 别名"""
    library_path: str = ""
    alias: str = ""


@dataclass(slots=True)
class FFIFunctionDeclaration(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_FUNCTION_DECL, init=False, repr=False)
    """外部函数声明：外部 段落 函数名 接收 参数... 返回 类型 在 库别名"""
    name: str = ""
    params: List[dict] = field(default_factory=list)
    return_type: Optional[str] = None
    library_alias: str = ""
    c_name: Optional[str] = None


@dataclass(slots=True)
class FFIStructDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_STRUCT_DEF, init=False, repr=False)
    """外部结构体定义"""
    name: str = ""
    fields: List[dict] = field(default_factory=list)


@dataclass(slots=True)
class FFICallbackDefinition(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_CALLBACK_DEF, init=False, repr=False)
    """外部回调类型定义"""
    name: str = ""
    params: List[dict] = field(default_factory=list)
    return_type: Optional[str] = None


# =============================================================================
# C FFI 指针/数组/错误处理节点（第二阶段，旧 AST 兼容）
# =============================================================================

@dataclass(slots=True)
class FFIPointerType(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_POINTER_TYPE, init=False, repr=False)
    """指针类型"""
    base_type: str = ""


@dataclass(slots=True)
class FFIArrayType(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_ARRAY_TYPE, init=False, repr=False)
    """数组类型"""
    base_type: str = ""
    size: Optional[int] = None


@dataclass(slots=True)
class FFIAddressOf(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_ADDRESS_OF, init=False, repr=False)
    """取地址"""
    target: Optional[ASTNode] = None


@dataclass(slots=True)
class FFIDereference(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_DEREFERENCE, init=False, repr=False)
    """解引用"""
    pointer: Optional[ASTNode] = None


@dataclass(slots=True)
class FFIPointerOffset(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_POINTER_OFFSET, init=False, repr=False)
    """指针偏移"""
    pointer: Optional[ASTNode] = None
    offset: Optional[ASTNode] = None


@dataclass(slots=True)
class FFISetPointerValue(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_SET_POINTER_VALUE, init=False, repr=False)
    """设指针值"""
    pointer: Optional[ASTNode] = None
    value: Optional[ASTNode] = None


@dataclass(slots=True)
class FFIAllocMemory(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_ALLOC_MEMORY, init=False, repr=False)
    """分配内存"""
    size: Optional[ASTNode] = None


@dataclass(slots=True)
class FFIFreeMemory(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_FREE_MEMORY, init=False, repr=False)
    """释放内存"""
    pointer: Optional[ASTNode] = None


@dataclass(slots=True)
class FFICreateArray(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_CREATE_ARRAY, init=False, repr=False)
    """创建数组"""
    base_type: str = ""
    size: Optional[ASTNode] = None


@dataclass(slots=True)
class FFISetArrayElement(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_SET_ARRAY_ELEMENT, init=False, repr=False)
    """设置数组元素"""
    array: Optional[ASTNode] = None
    index: Optional[ASTNode] = None
    value: Optional[ASTNode] = None


@dataclass(slots=True)
class FFIGetLastError(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_GET_LAST_ERROR, init=False, repr=False)
    """获取最后FFI错误"""
    pass


@dataclass(slots=True)
class FFIGetErrno(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_GET_ERRNO, init=False, repr=False)
    """获取系统错误码"""
    pass


@dataclass(slots=True)
class FFISetErrno(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_SET_ERRNO, init=False, repr=False)
    """设置系统错误码"""
    value: Optional[ASTNode] = None


@dataclass(slots=True)
class FFITryCatch(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_TRY_CATCH, init=False, repr=False)
    """FFI 错误捕获"""
    try_body: List[ASTNode] = field(default_factory=list)
    error_var: str = "错误"
    catch_body: List[ASTNode] = field(default_factory=list)


# =============================================================================
# C FFI 第三阶段节点（旧 AST 兼容）
# =============================================================================

@dataclass(slots=True)
class FFIEnumDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_ENUM_DEF, init=False, repr=False)
    """C枚举定义"""
    name: str = ""
    values: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class FFIUnionDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_UNION_DEF, init=False, repr=False)
    """C联合体定义"""
    name: str = ""
    fields: List[dict] = field(default_factory=list)


@dataclass(slots=True)
class FFICreateCallback(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_CREATE_CALLBACK, init=False, repr=False)
    """创建回调函数"""
    callback_type: str = ""
    light_function: str = ""


@dataclass(slots=True)
class FFIVarArgsDecl(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_VAR_ARGS_DECL, init=False, repr=False)
    """变长参数声明"""
    name: str = ""
    params: List[dict] = field(default_factory=list)
    return_type: Optional[str] = None
    library_alias: str = ""
    c_name: Optional[str] = None


@dataclass(slots=True)
class FFIStructByValue(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_STRUCT_BY_VALUE, init=False, repr=False)
    """结构体按值传递"""
    struct_type: str = ""
    fields: Dict[str, ASTNode] = field(default_factory=dict)


@dataclass(slots=True)
class FFILibraryPath(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_LIBRARY_PATH, init=False, repr=False)
    """跨平台库路径"""
    name: str = ""
    platform_map: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# C FFI 第四阶段节点（旧 AST 兼容）
# =============================================================================

@dataclass(slots=True)
class FFITypedefDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_TYPEDEF_DEF, init=False, repr=False)
    """C类型别名"""
    name: str = ""
    base_type: str = ""


@dataclass(slots=True)
class FFIBitfieldDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_BITFIELD_DEF, init=False, repr=False)
    """C位域定义"""
    name: str = ""
    base_type: str = ""
    fields: List[dict] = field(default_factory=list)


@dataclass(slots=True)
class FFIFuncPtrDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_FUNC_PTR_DEF, init=False, repr=False)
    """C函数指针类型"""
    name: str = ""
    params: List[dict] = field(default_factory=list)
    return_type: Optional[str] = None


@dataclass(slots=True)
class FFIDebugConfig(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_DEBUG_CONFIG, init=False, repr=False)
    """FFI调试配置"""
    enabled: bool = True
    log_calls: bool = False
    log_types: bool = False
    trace_memory: bool = False


@dataclass(slots=True)
class FFIPreprocessorDef(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_FFI_PREPROCESSOR_DEF, init=False, repr=False)
    """C预处理器宏"""
    name: str = ""
    value: str = ""


@dataclass(slots=True)
class Module(ASTNode):
    _ast_type_id: int = field(default=AST_TYPE_ID_MODULE, init=False, repr=False)
    """模块（篇）- 顶层节点"""
    name: Optional[str] = None
    imports: List[ImportStatement] = field(default_factory=list)
    exports: List[ExportStatement] = field(default_factory=list)
    segments: List[SegmentDefinition] = field(default_factory=list)
    classes: List[ClassDefinition] = field(default_factory=list)
    interfaces: List[InterfaceDefinition] = field(default_factory=list)
    data_types: List[DataTypeDefinition] = field(default_factory=list)
    error_types: List[ErrorTypeDefinition] = field(default_factory=list)
    statements: List[ASTNode] = field(default_factory=list)
    # 新类型定义
    enums: List[EnumDefinition] = field(default_factory=list)
    trait_defs: List[TraitDefinition] = field(default_factory=list)
    trait_impls: List[TraitImplementation] = field(default_factory=list)
    type_aliases: List[TypeAlias] = field(default_factory=list)


# =============================================================================
# 辅助函数
# =============================================================================

def ast_to_dict(node: ASTNode) -> dict:
    """将 AST 节点转换为字典（用于序列化）"""
    if isinstance(node, ASTNode):
        result = {'type': node.__class__.__name__}
        for field_name in node.__dataclass_fields__:
            value = getattr(node, field_name)
            if isinstance(value, list):
                result[field_name] = [ast_to_dict(item) for item in value]
            elif isinstance(value, ASTNode):
                result[field_name] = ast_to_dict(value)
            else:
                result[field_name] = value
        return result
    return node


# =============================================================================
# 兼容别名（统一双轨制：ast_nodes_v3.py 的命名 → ast_nodes.py 的命名）
# 使旧代码可以用 ImportStmt 引用 ImportStatement 等
# =============================================================================

ImportStmt = ImportStatement
ExportStmt = ExportStatement