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

@dataclass
class ASTNode:
    """AST 节点基类"""
    line: int = 0
    column: int = 0


# =============================================================================
# 字面量节点
# =============================================================================

@dataclass
class NumberLiteral(ASTNode):
    """数字字面量"""
    value: Union[int, float] = 0


@dataclass
class StringLiteral(ASTNode):
    """字符串字面量"""
    value: str = ""


@dataclass
class BooleanLiteral(ASTNode):
    """布尔字面量"""
    value: bool = False


@dataclass
class NullLiteral(ASTNode):
    """空值字面量"""
    pass


@dataclass
class SelfReference(ASTNode):
    """self引用（己）"""
    pass


# =============================================================================
# 标识符与名称节点
# =============================================================================

@dataclass
class Identifier(ASTNode):
    """标识符（变量名、段落名引用等）"""
    name: str = ""


@dataclass
class SegmentName(ASTNode):
    """段落名（《名称》）"""
    name: str = ""


@dataclass
class ModuleName(ASTNode):
    """模块/篇名（【名称】）"""
    name: str = ""


# =============================================================================
# 表达式节点
# =============================================================================

@dataclass
class BinaryOp(ASTNode):
    """二元运算"""
    left: ASTNode = None
    operator: str = ""
    right: ASTNode = None


@dataclass
class UnaryOp(ASTNode):
    """一元运算"""
    operator: str = ""
    operand: ASTNode = None


@dataclass
class FunctionCall(ASTNode):
    """函数/段落调用"""
    name: Union[SegmentName, Identifier] = None
    arguments: List[ASTNode] = field(default_factory=list)


@dataclass
class PipeExpression(ASTNode):
    """管道表达式（-> 或 并 连接）"""
    expressions: List[ASTNode] = field(default_factory=list)


@dataclass
class PropertyAccess(ASTNode):
    """属性访问（之字结构：对象之属性）"""
    obj: ASTNode = None
    property_name: str = ""


@dataclass
class IndexAccess(ASTNode):
    """索引访问（对象[索引]）"""
    obj: ASTNode = None
    index: ASTNode = None


@dataclass
class ListLiteral(ASTNode):
    """列表字面量"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class DictEntry(ASTNode):
    """典条目（键值对）"""
    key: ASTNode = None
    value: ASTNode = None


@dataclass
class DictLiteral(ASTNode):
    """典字面量（字典）"""
    entries: List[DictEntry] = field(default_factory=list)


@dataclass
class NewExpression(ASTNode):
    """类实例化表达式（新类名()）"""
    class_name: str = ""
    arguments: List[ASTNode] = field(default_factory=list)


@dataclass
class ConditionalExpression(ASTNode):
    """三元条件表达式：如果 条件 那么 值1 否则 值2"""
    condition: ASTNode = None
    then_expr: ASTNode = None
    else_expr: Optional[ASTNode] = None


@dataclass
class StringInterpolation(ASTNode):
    """字符串插值："你好，{名字}" -> f-string"""
    parts: List[Union[str, ASTNode]] = field(default_factory=list)  # 交替的字符串和表达式


@dataclass
class ListComprehension(ASTNode):
    """列表推导：[表达式 遍历 变量 之 列表]"""
    expression: ASTNode = None          # 输出表达式
    variable: str = ""                   # 遍历变量
    iterable: ASTNode = None            # 可迭代对象
    condition: Optional[ASTNode] = None # 可选过滤条件


@dataclass
class LambdaExpression(ASTNode):
    """匿名函数：接收 甲：返回 甲 乘 甲。"""
    parameters: List[Parameter] = field(default_factory=list)
    body: ASTNode = None                # 表达式体


@dataclass
class MatchStatement(ASTNode):
    """模式匹配：匹配 值：情况 ... 结束。"""
    subject: ASTNode = None             # 被匹配的值
    cases: List['MatchCase'] = field(default_factory=list)


@dataclass
class MatchCase(ASTNode):
    """匹配分支"""
    pattern: 'MatchPattern' = None      # 匹配模式
    guard: Optional[ASTNode] = None     # 守卫条件（情况 模式 如果 条件）
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class MatchPattern(ASTNode):
    """匹配模式"""
    kind: str = ""                      # 'number', 'string', 'bool', 'null', 'variable', 'wildcard', 'list', 'type_check'
    value: Optional[ASTNode] = None     # 字面量值或变量名
    elements: List['MatchPattern'] = field(default_factory=list)  # 列表模式元素
    type_name: str = ""                 # 类型检查模式中的类型名
    binding: str = ""                   # 变量绑定名


@dataclass
class DictComprehension(ASTNode):
    """字典推导：{键: 值 遍历 变量 之 列表}"""
    key_expr: ASTNode = None            # 键表达式
    value_expr: ASTNode = None          # 值表达式
    variable: str = ""                   # 遍历变量
    iterable: ASTNode = None            # 可迭代对象
    condition: Optional[ASTNode] = None # 可选过滤条件


@dataclass
class DecoratorDefinition(ASTNode):
    """装饰器定义：@段落名 标注 段落 ..."""
    decorator_name: str = ""            # 装饰器段落名
    paragraph: 'SegmentDefinition' = None  # 被装饰的段落


@dataclass
class DestructuringAssignment(ASTNode):
    """解构赋值：设 (甲, 乙) 为 元组"""
    variables: List[str] = field(default_factory=list)  # 解构变量列表
    value: ASTNode = None               # 被解构的值


@dataclass
class WithStatement(ASTNode):
    """上下文管理器：使用 表达式 作为 变量：...结束。"""
    context_expr: ASTNode = None        # 上下文表达式
    variable: Optional[str] = None      # 可选的 as 变量
    body: List[ASTNode] = field(default_factory=list)


# =============================================================================
# 语句节点
# =============================================================================

@dataclass
class VariableDeclaration(ASTNode):
    """变量声明"""
    name: str = ""
    value: ASTNode = None


@dataclass
class Assignment(ASTNode):
    """赋值语句"""
    target: ASTNode = None
    value: ASTNode = None


@dataclass
class CompoundAssignment(ASTNode):
    """复合赋值（甲 加上 1 → 甲 += 1）"""
    target: str = ""        # 变量名
    operator: str = ""      # '加', '减', '乘', '除', '模', '幂'
    value: ASTNode = None


@dataclass
class IfStatement(ASTNode):
    """条件语句"""
    condition: ASTNode = None
    then_body: List[ASTNode] = field(default_factory=list)
    else_body: Optional[List[ASTNode]] = None
    elseif_conditions: List[ASTNode] = field(default_factory=list)
    elseif_bodies: List[List[ASTNode]] = field(default_factory=list)


@dataclass
class ForeachStatement(ASTNode):
    """遍历循环"""
    variable: str = ""
    iterable: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class WhileStatement(ASTNode):
    """当循环"""
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class BreakStatement(ASTNode):
    """跳出语句"""
    pass


@dataclass
class ContinueStatement(ASTNode):
    """跳过语句"""
    pass


@dataclass
class ReturnStatement(ASTNode):
    """返回语句"""
    value: Optional[ASTNode] = None


@dataclass
class TryStatement(ASTNode):
    """异常捕获"""
    try_body: List[ASTNode] = field(default_factory=list)
    catch_var: str = ""
    catch_body: List[ASTNode] = field(default_factory=list)


@dataclass
class ThrowStatement(ASTNode):
    """抛出异常"""
    value: ASTNode = None


@dataclass
class PrintStatement(ASTNode):
    """打印/输出语句"""
    value: ASTNode = None


@dataclass
class ExpressionStatement(ASTNode):
    """表达式语句"""
    expression: ASTNode = None


# =============================================================================
# 段落定义节点
# =============================================================================

@dataclass
class Parameter(ASTNode):
    """参数定义"""
    name: str = ""
    type_annotation: Optional[str] = None
    default_value: Optional[ASTNode] = None


# =============================================================================
# 异步/并发节点
# =============================================================================

@dataclass
class AwaitExpression(ASTNode):
    """等待表达式（等待 异步操作）"""
    expression: ASTNode = None


@dataclass
class DeferStatement(ASTNode):
    """推迟语句（推迟 语句 — 在作用域退出时执行）"""
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class AsyncScope(ASTNode):
    """并行作用域（结构化并发）：并行 { 任务1 任务2 }"""
    tasks: List[ASTNode] = field(default_factory=list)
    result_vars: List[str] = field(default_factory=list)
    timeout: Optional[ASTNode] = None


@dataclass
class SegmentDefinition(ASTNode):
    """段落定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
    return_type: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)


# =============================================================================
# 数据/错误类型定义
# =============================================================================

@dataclass
class DataTypeField(ASTNode):
    """数据类型字段"""
    name: str = ""
    type_annotation: str = ""


@dataclass
class DataTypeDefinition(ASTNode):
    """数据类型定义"""
    name: str = ""
    fields: List[DataTypeField] = field(default_factory=list)


@dataclass
class ErrorTypeDefinition(ASTNode):
    """错误类型定义"""
    name: str = ""
    fields: List[DataTypeField] = field(default_factory=list)


# =============================================================================
# 类和接口定义
# =============================================================================

@dataclass
class MethodDefinition(ASTNode):
    """方法定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
    return_type: Optional[str] = None
    is_static: bool = False


@dataclass
class ConstructorDefinition(ASTNode):
    """构造函数定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class ClassDefinition(ASTNode):
    """类定义"""
    name: str = ""
    generic_params: List[str] = field(default_factory=list)  # 泛型参数列表
    superclasses: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    fields: List[ASTNode] = field(default_factory=list)  # 包含 varDecl
    methods: List[MethodDefinition] = field(default_factory=list)
    constructor: Optional[ConstructorDefinition] = None


@dataclass
class InterfaceMethod(ASTNode):
    """接口方法签名"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: str = ""


@dataclass
class InterfaceProperty(ASTNode):
    """接口属性签名"""
    name: str = ""
    type_annotation: str = ""


@dataclass
class InterfaceDefinition(ASTNode):
    """接口定义"""
    name: str = ""
    superinterfaces: List[str] = field(default_factory=list)
    methods: List[InterfaceMethod] = field(default_factory=list)
    properties: List[InterfaceProperty] = field(default_factory=list)


# =============================================================================
# 类型注解节点（泛型支持）
# =============================================================================

@dataclass
class GenericType(ASTNode):
    """泛型类型"""
    base_type: str = ""
    type_arguments: List[str] = field(default_factory=list)


# =============================================================================
# 模块节点
# =============================================================================

@dataclass
class ImportStatement(ASTNode):
    """导入语句"""
    module: str = ""
    names: List[str] = field(default_factory=list)


@dataclass
class ExportStatement(ASTNode):
    """导出语句"""
    name: str = ""


@dataclass
class Module(ASTNode):
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