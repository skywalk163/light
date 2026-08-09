"""
光明（Light）编程语言 - 统一AST系统（用于机器码生成）

这是为原生编译器设计的统一AST，包含：
1. 完整的类型系统支持
2. 符号表和作用域信息
3. 代码生成所需的额外元数据
4. 跨平台代码生成支持
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Dict, Set

# =============================================================================
# 类型系统定义
# =============================================================================

class Type:
    """类型基类"""
    pass

@dataclass
class PrimitiveType(Type):
    """基本类型"""
    kind: str  # 'int', 'float', 'bool', 'char', 'void', 'string'
    
    def __eq__(self, other):
        if isinstance(other, PrimitiveType):
            return self.kind == other.kind
        return False
    
    def __repr__(self):
        return self.kind

@dataclass
class PointerType(Type):
    """指针类型"""
    pointee: Type
    
    def __repr__(self):
        return f"*{repr(self.pointee)}"

@dataclass
class ArrayType(Type):
    """数组类型"""
    element_type: Type
    size: Optional[int] = None  # None表示动态数组
    
    def __repr__(self):
        if self.size is not None:
            return f"[{self.size}] {repr(self.element_type)}"
        return f"[] {repr(self.element_type)}"

@dataclass
class StructType(Type):
    """结构体类型"""
    name: str
    fields: List[Tuple[str, Type]]
    
    def __repr__(self):
        return f"struct {self.name}"

@dataclass
class FunctionType(Type):
    """函数类型"""
    return_type: Type
    param_types: List[Type]
    
    def __repr__(self):
        params = ", ".join(repr(p) for p in self.param_types)
        return f"({params}) -> {repr(self.return_type)}"

# 预定义类型
TYPE_INT = PrimitiveType('int')
TYPE_FLOAT = PrimitiveType('float')
TYPE_BOOL = PrimitiveType('bool')
TYPE_CHAR = PrimitiveType('char')
TYPE_VOID = PrimitiveType('void')
TYPE_STRING = PrimitiveType('string')

# =============================================================================
# AST节点基类
# =============================================================================

@dataclass
class ASTNode:
    """AST节点基类"""
    line: int = 0
    column: int = 0
    
    # 类型信息（用于代码生成）
    inferred_type: Optional[Type] = None
    
    # 符号表信息
    scope_id: Optional[int] = None

# =============================================================================
# 字面量节点
# =============================================================================

@dataclass
class NumberLiteral(ASTNode):
    """数字字面量"""
    value: Union[int, float] = 0
    
    def __post_init__(self):
        if isinstance(self.value, int):
            self.inferred_type = TYPE_INT
        else:
            self.inferred_type = TYPE_FLOAT

@dataclass
class StringLiteral(ASTNode):
    """字符串字面量"""
    value: str = ""
    
    def __post_init__(self):
        self.inferred_type = TYPE_STRING

@dataclass
class BooleanLiteral(ASTNode):
    """布尔字面量"""
    value: bool = False
    
    def __post_init__(self):
        self.inferred_type = TYPE_BOOL

@dataclass
class CharLiteral(ASTNode):
    """字符字面量"""
    value: str = ""
    
    def __post_init__(self):
        self.inferred_type = TYPE_CHAR

# =============================================================================
# 标识符节点
# =============================================================================

@dataclass
class Identifier(ASTNode):
    """标识符"""
    name: str = ""
    symbol_ref: Optional[Symbol] = None  # 符号引用

@dataclass
class Symbol:
    """符号表条目"""
    name: str
    type: Type
    scope_id: int
    is_mutable: bool = False
    is_global: bool = False
    offset: Optional[int] = None  # 栈偏移（用于代码生成）
    address: Optional[int] = None  # 全局地址（用于代码生成）

# =============================================================================
# 表达式节点
# =============================================================================

@dataclass
class BinaryOp(ASTNode):
    """二元运算"""
    left: ASTNode = None
    operator: str = ""  # '+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>='
    right: ASTNode = None

@dataclass
class UnaryOp(ASTNode):
    """一元运算"""
    operator: str = ""  # '+', '-', '!', '*' (解引用), '&' (取地址)
    operand: ASTNode = None

@dataclass
class FunctionCall(ASTNode):
    """函数调用"""
    callee: ASTNode = None  # 可以是Identifier或其他表达式
    arguments: List[ASTNode] = field(default_factory=list)
    function_type: Optional[FunctionType] = None  # 函数类型信息

@dataclass
class ArrayAccess(ASTNode):
    """数组访问"""
    array: ASTNode = None
    index: ASTNode = None

@dataclass
class StructAccess(ASTNode):
    """结构体成员访问"""
    struct: ASTNode = None
    field_name: str = ""
    field_offset: int = 0  # 字段偏移（用于代码生成）

@dataclass
class CastExpression(ASTNode):
    """类型转换"""
    value: ASTNode = None
    target_type: Type = None

# =============================================================================
# 语句节点
# =============================================================================

@dataclass
class Block(ASTNode):
    """代码块"""
    statements: List[ASTNode] = field(default_factory=list)
    scope_id: int = 0

@dataclass
class VariableDeclaration(ASTNode):
    """变量声明"""
    name: str = ""
    type: Optional[Type] = None
    initializer: Optional[ASTNode] = None
    is_mutable: bool = False
    symbol: Optional[Symbol] = None  # 关联的符号

@dataclass
class Assignment(ASTNode):
    """赋值语句"""
    target: ASTNode = None  # Identifier, ArrayAccess, or StructAccess
    value: ASTNode = None

@dataclass
class IfStatement(ASTNode):
    """条件语句"""
    condition: ASTNode = None
    then_block: Block = None
    else_block: Optional[Block] = None
    
    # 代码生成标签
    then_label: Optional[str] = None
    else_label: Optional[str] = None
    end_label: Optional[str] = None

@dataclass
class WhileStatement(ASTNode):
    """while循环"""
    condition: ASTNode = None
    body: Block = None
    
    # 代码生成标签
    loop_label: Optional[str] = None
    end_label: Optional[str] = None

@dataclass
class ForStatement(ASTNode):
    """for循环"""
    init: Optional[ASTNode] = None
    condition: Optional[ASTNode] = None
    update: Optional[ASTNode] = None
    body: Block = None
    
    # 代码生成标签
    loop_label: Optional[str] = None
    end_label: Optional[str] = None

@dataclass
class BreakStatement(ASTNode):
    """break语句"""
    target_loop: Optional[ASTNode] = None  # 指向循环节点

@dataclass
class ContinueStatement(ASTNode):
    """continue语句"""
    target_loop: Optional[ASTNode] = None  # 指向循环节点

@dataclass
class ReturnStatement(ASTNode):
    """return语句"""
    value: Optional[ASTNode] = None

@dataclass
class ExpressionStatement(ASTNode):
    """表达式语句"""
    expression: ASTNode = None

@dataclass
class PrintStatement(ASTNode):
    """打印语句"""
    value: ASTNode = None

# =============================================================================
# 函数和全局定义节点
# =============================================================================

@dataclass
class Parameter(ASTNode):
    """函数参数"""
    name: str = ""
    type: Type = None
    symbol: Optional[Symbol] = None  # 关联的符号
    
    def __post_init__(self):
        if self.type is None:
            self.type = TYPE_VOID

@dataclass
class FunctionDefinition(ASTNode):
    """函数定义"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Type = None
    body: Block = None
    symbol: Optional[Symbol] = None  # 关联的符号
    
    # 代码生成信息
    stack_size: int = 0
    local_count: int = 0
    
    def __post_init__(self):
        if self.return_type is None:
            self.return_type = TYPE_VOID

@dataclass
class StructDefinition(ASTNode):
    """结构体定义"""
    name: str = ""
    fields: List[Tuple[str, Type]] = field(default_factory=list)
    size: int = 0  # 结构体大小（字节）
    field_offsets: Dict[str, int] = field(default_factory=dict)  # 字段偏移

@dataclass
class GlobalVariable(ASTNode):
    """全局变量"""
    name: str = ""
    type: Type = None
    initializer: Optional[ASTNode] = None
    symbol: Optional[Symbol] = None  # 关联的符号
    
    def __post_init__(self):
        if self.type is None:
            self.type = TYPE_VOID

# =============================================================================
# 模块节点
# =============================================================================

@dataclass
class Module(ASTNode):
    """模块（顶层节点）"""
    name: Optional[str] = None
    functions: List[FunctionDefinition] = field(default_factory=list)
    structs: List[StructDefinition] = field(default_factory=list)
    globals: List[GlobalVariable] = field(default_factory=list)
    
    # 符号表
    scopes: Dict[int, Dict[str, Symbol]] = field(default_factory=dict)
    next_scope_id: int = 1
    
    # 字符串常量池（用于代码生成）
    string_constants: Dict[str, int] = field(default_factory=dict)
    next_string_offset: int = 0

    def add_scope(self) -> int:
        """创建新作用域并返回ID"""
        scope_id = self.next_scope_id
        self.scopes[scope_id] = {}
        self.next_scope_id += 1
        return scope_id
    
    def add_symbol(self, scope_id: int, name: str, symbol: Symbol):
        """在指定作用域添加符号"""
        if scope_id not in self.scopes:
            self.scopes[scope_id] = {}
        self.scopes[scope_id][name] = symbol
    
    def lookup_symbol(self, scope_id: int, name: str) -> Optional[Symbol]:
        """在作用域链中查找符号"""
        current_id = scope_id
        while current_id is not None:
            if current_id in self.scopes and name in self.scopes[current_id]:
                return self.scopes[current_id][name]
            # 简单实现：假设父作用域是当前ID减1
            # 实际实现需要维护作用域层次结构
            if current_id == 0:
                break
            current_id -= 1
        return None

# =============================================================================
# AST访问者模式（用于代码生成）
# =============================================================================

class ASTVisitor:
    """AST访问者基类"""
    
    def visit(self, node: ASTNode):
        """调度访问方法"""
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.visit_default)
        return method(node)
    
    def visit_default(self, node: ASTNode):
        """默认访问方法"""
        pass
    
    def visit_NumberLiteral(self, node: NumberLiteral):
        pass
    
    def visit_StringLiteral(self, node: StringLiteral):
        pass
    
    def visit_BooleanLiteral(self, node: BooleanLiteral):
        pass
    
    def visit_CharLiteral(self, node: CharLiteral):
        pass
    
    def visit_Identifier(self, node: Identifier):
        pass
    
    def visit_BinaryOp(self, node: BinaryOp):
        self.visit(node.left)
        self.visit(node.right)
    
    def visit_UnaryOp(self, node: UnaryOp):
        self.visit(node.operand)
    
    def visit_FunctionCall(self, node: FunctionCall):
        self.visit(node.callee)
        for arg in node.arguments:
            self.visit(arg)
    
    def visit_ArrayAccess(self, node: ArrayAccess):
        self.visit(node.array)
        self.visit(node.index)
    
    def visit_StructAccess(self, node: StructAccess):
        self.visit(node.struct)
    
    def visit_CastExpression(self, node: CastExpression):
        self.visit(node.value)
    
    def visit_Block(self, node: Block):
        for stmt in node.statements:
            self.visit(stmt)
    
    def visit_VariableDeclaration(self, node: VariableDeclaration):
        if node.initializer:
            self.visit(node.initializer)
    
    def visit_Assignment(self, node: Assignment):
        self.visit(node.target)
        self.visit(node.value)
    
    def visit_IfStatement(self, node: IfStatement):
        self.visit(node.condition)
        self.visit(node.then_block)
        if node.else_block:
            self.visit(node.else_block)
    
    def visit_WhileStatement(self, node: WhileStatement):
        self.visit(node.condition)
        self.visit(node.body)
    
    def visit_ForStatement(self, node: ForStatement):
        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
        if node.update:
            self.visit(node.update)
        self.visit(node.body)
    
    def visit_BreakStatement(self, node: BreakStatement):
        pass
    
    def visit_ContinueStatement(self, node: ContinueStatement):
        pass
    
    def visit_ReturnStatement(self, node: ReturnStatement):
        if node.value:
            self.visit(node.value)
    
    def visit_ExpressionStatement(self, node: ExpressionStatement):
        self.visit(node.expression)
    
    def visit_PrintStatement(self, node: PrintStatement):
        self.visit(node.value)
    
    def visit_FunctionDefinition(self, node: FunctionDefinition):
        self.visit(node.body)
    
    def visit_StructDefinition(self, node: StructDefinition):
        pass
    
    def visit_GlobalVariable(self, node: GlobalVariable):
        if node.initializer:
            self.visit(node.initializer)
    
    def visit_Module(self, node: Module):
        for struct in node.structs:
            self.visit(struct)
        for global_var in node.globals:
            self.visit(global_var)
        for func in node.functions:
            self.visit(func)
