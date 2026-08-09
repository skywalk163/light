"""
光明（Light）编程语言 - 语义分析器

负责：
1. 符号表构建和管理
2. 类型检查和推断
3. 作用域分析
4. 错误检测
"""

from typing import Dict, List, Optional, Any, Set
from ast_unified import *

class SemanticError(Exception):
    """语义错误异常"""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column

class SemanticAnalyzer(ASTVisitor):
    """语义分析器"""
    
    def __init__(self, module: Module):
        self.module = module
        self.current_scope_id = 0
        self.errors: List[SemanticError] = []
        
        # 创建全局作用域
        self.module.add_scope()
        
    def add_error(self, message: str, node: ASTNode):
        """添加错误"""
        self.errors.append(SemanticError(message, node.line, node.column))
    
    def enter_scope(self) -> int:
        """进入新作用域"""
        self.current_scope_id = self.module.add_scope()
        return self.current_scope_id
    
    def exit_scope(self):
        """退出当前作用域（简单实现）"""
        if self.current_scope_id > 0:
            self.current_scope_id -= 1
    
    def declare_symbol(self, name: str, type: Type, node: ASTNode, is_mutable: bool = False, is_global: bool = False):
        """声明符号"""
        symbol = Symbol(
            name=name,
            type=type,
            scope_id=self.current_scope_id,
            is_mutable=is_mutable,
            is_global=is_global
        )
        
        # 检查符号是否已存在于当前作用域
        existing = self.module.lookup_symbol(self.current_scope_id, name)
        if existing:
            if existing.scope_id == self.current_scope_id:
                self.add_error(f"符号 '{name}' 已在当前作用域定义", node)
                return None
        
        self.module.add_symbol(self.current_scope_id, name, symbol)
        return symbol
    
    def resolve_symbol(self, name: str, node: ASTNode) -> Optional[Symbol]:
        """解析符号引用"""
        symbol = self.module.lookup_symbol(self.current_scope_id, name)
        if not symbol:
            self.add_error(f"未定义的符号 '{name}'", node)
        return symbol
    
    def check_types(self, expected: Type, actual: Type, node: ASTNode, context: str = ""):
        """检查类型兼容性（使用子类型关系，支持多态）"""
        if expected is None or actual is None:
            return
        
        # 相同类型直接通过
        if expected == actual:
            return
        
        # 尝试子类型检查（支持多态、可空类型等）
        # 如果 Type 对象有 is_subtype_of 方法，使用它
        if hasattr(expected, 'is_subtype_of'):
            if expected.is_subtype_of(actual) or actual.is_subtype_of(expected):
                return
        
        # 兼容性检查失败，报告错误
        self.add_error(f"类型不匹配{context}：期望 {expected}，得到 {actual}", node)
    
    def visit_Module(self, node: Module):
        """访问模块"""
        # 首先处理结构体定义
        for struct in node.structs:
            self.visit(struct)
        
        # 然后处理全局变量
        for global_var in node.globals:
            self.visit(global_var)
        
        # 最后处理函数
        for func in node.functions:
            self.visit(func)
    
    def visit_StructDefinition(self, node: StructDefinition):
        """访问结构体定义"""
        # 计算结构体大小和字段偏移
        offset = 0
        field_offsets = {}
        
        for field_name, field_type in node.fields:
            # 简单对齐：按8字节对齐
            if offset % 8 != 0:
                offset = ((offset // 8) + 1) * 8
            field_offsets[field_name] = offset
            
            # 计算字段大小
            field_size = self.get_type_size(field_type)
            offset += field_size
        
        node.size = offset
        node.field_offsets = field_offsets
    
    def get_type_size(self, type: Type) -> int:
        """获取类型大小（字节）"""
        if isinstance(type, PrimitiveType):
            sizes = {
                'void': 0,
                'bool': 1,
                'char': 1,
                'int': 8,
                'float': 8,
                'string': 8  # 字符串是指针
            }
            return sizes.get(type.kind, 8)
        elif isinstance(type, PointerType):
            return 8
        elif isinstance(type, ArrayType):
            elem_size = self.get_type_size(type.element_type)
            if type.size is not None:
                return elem_size * type.size
            return 8  # 动态数组是指针
        elif isinstance(type, StructType):
            # 查找结构体定义
            for struct in self.module.structs:
                if struct.name == type.name:
                    return struct.size
            return 0
        elif isinstance(type, FunctionType):
            return 8  # 函数指针
        return 8
    
    def visit_GlobalVariable(self, node: GlobalVariable):
        """访问全局变量"""
        # 声明全局符号
        symbol = self.declare_symbol(node.name, node.type, node, is_global=True)
        node.symbol = symbol
        
        # 检查初始化器类型
        if node.initializer:
            self.visit(node.initializer)
            if node.initializer.inferred_type:
                self.check_types(node.type, node.initializer.inferred_type, node, "（全局变量初始化）")
    
    def visit_FunctionDefinition(self, node: FunctionDefinition):
        """访问函数定义"""
        # 声明函数符号
        func_type = FunctionType(return_type=node.return_type, param_types=[p.type for p in node.parameters])
        symbol = self.declare_symbol(node.name, func_type, node, is_global=True)
        node.symbol = symbol
        
        # 进入函数作用域
        self.enter_scope()
        
        # 声明参数
        param_offset = 16  # RBP + 16 开始（跳过返回地址和RBP）
        for param in node.parameters:
            param_symbol = self.declare_symbol(param.name, param.type, param)
            param.symbol = param_symbol
            param_symbol.offset = param_offset
            param_offset += self.get_type_size(param.type)
        
        # 访问函数体
        if node.body:
            self.visit(node.body)
        
        # 退出函数作用域
        self.exit_scope()
    
    def visit_Block(self, node: Block):
        """访问代码块"""
        # 进入块作用域
        self.enter_scope()
        node.scope_id = self.current_scope_id
        
        # 访问所有语句
        for stmt in node.statements:
            self.visit(stmt)
        
        # 退出块作用域
        self.exit_scope()
    
    def visit_VariableDeclaration(self, node: VariableDeclaration):
        """访问变量声明"""
        # 如果没有显式类型，从初始化器推断
        if node.type is None and node.initializer:
            self.visit(node.initializer)
            node.type = node.initializer.inferred_type
        elif node.type is None:
            self.add_error("变量声明需要类型注解或初始化器", node)
            node.type = TYPE_INT  # 默认类型
        
        # 声明符号
        symbol = self.declare_symbol(node.name, node.type, node, is_mutable=node.is_mutable)
        node.symbol = symbol
        
        # 检查初始化器类型
        if node.initializer:
            if node.initializer.inferred_type:
                self.check_types(node.type, node.initializer.inferred_type, node, "（变量初始化）")
    
    def visit_Identifier(self, node: Identifier):
        """访问标识符"""
        # 解析符号
        symbol = self.resolve_symbol(node.name, node)
        node.symbol_ref = symbol
        
        # 设置推断类型
        if symbol:
            node.inferred_type = symbol.type
    
    def visit_NumberLiteral(self, node: NumberLiteral):
        """访问数字字面量"""
        # 类型已经在__post_init__中设置
        pass
    
    def visit_StringLiteral(self, node: StringLiteral):
        """访问字符串字面量"""
        # 类型已经在__post_init__中设置
        pass
    
    def visit_BooleanLiteral(self, node: BooleanLiteral):
        """访问布尔字面量"""
        # 类型已经在__post_init__中设置
        pass
    
    def visit_BinaryOp(self, node: BinaryOp):
        """访问二元运算"""
        self.visit(node.left)
        self.visit(node.right)
        
        left_type = node.left.inferred_type
        right_type = node.right.inferred_type
        
        if not left_type or not right_type:
            return
        
        # 检查操作数类型兼容性（使用子类型关系）
        self.check_types(left_type, right_type, node, "（二元运算）")
        
        # 设置结果类型
        node.inferred_type = left_type
    
    def visit_UnaryOp(self, node: UnaryOp):
        """访问一元运算"""
        self.visit(node.operand)
        
        operand_type = node.operand.inferred_type
        if not operand_type:
            return
        
        # 设置结果类型
        if node.operator == '!' and operand_type == TYPE_BOOL:
            node.inferred_type = TYPE_BOOL
        elif node.operator in ('+', '-'):
            node.inferred_type = operand_type
        elif node.operator == '&':
            node.inferred_type = PointerType(operand_type)
        elif node.operator == '*':
            if isinstance(operand_type, PointerType):
                node.inferred_type = operand_type.pointee
            else:
                self.add_error("解引用操作需要指针类型", node)
    
    def visit_FunctionCall(self, node: FunctionCall):
        """访问函数调用"""
        self.visit(node.callee)
        
        # 检查参数类型
        for i, arg in enumerate(node.arguments):
            self.visit(arg)
        
        # 如果是标识符调用，检查函数签名
        if isinstance(node.callee, Identifier) and node.callee.symbol_ref:
            func_symbol = node.callee.symbol_ref
            if isinstance(func_symbol.type, FunctionType):
                func_type = func_symbol.type
                
                # 检查参数数量
                if len(node.arguments) != len(func_type.param_types):
                    self.add_error(
                        f"参数数量不匹配：期望 {len(func_type.param_types)} 个参数，得到 {len(node.arguments)} 个",
                        node
                    )
                    return
                
                # 检查参数类型
                for i, (arg, expected_type) in enumerate(zip(node.arguments, func_type.param_types)):
                    if arg.inferred_type:
                        self.check_types(expected_type, arg.inferred_type, arg, f"（参数 {i+1}）")
                
                # 设置返回类型
                node.inferred_type = func_type.return_type
                node.function_type = func_type
    
    def visit_Assignment(self, node: Assignment):
        """访问赋值语句"""
        self.visit(node.target)
        self.visit(node.value)
        
        target_type = node.target.inferred_type
        value_type = node.value.inferred_type
        
        if target_type and value_type:
            self.check_types(target_type, value_type, node, "（赋值）")
        
        # 检查赋值目标是否可写
        if isinstance(node.target, Identifier) and node.target.symbol_ref:
            if not node.target.symbol_ref.is_mutable:
                self.add_error(f"无法赋值给不可变变量 '{node.target.name}'", node)
    
    def visit_IfStatement(self, node: IfStatement):
        """访问条件语句"""
        self.visit(node.condition)
        
        # 检查条件类型
        if node.condition.inferred_type and node.condition.inferred_type != TYPE_BOOL:
            self.add_error("if条件必须是布尔类型", node)
        
        self.visit(node.then_block)
        if node.else_block:
            self.visit(node.else_block)
    
    def visit_WhileStatement(self, node: WhileStatement):
        """访问while循环"""
        self.visit(node.condition)
        
        # 检查条件类型
        if node.condition.inferred_type and node.condition.inferred_type != TYPE_BOOL:
            self.add_error("while条件必须是布尔类型", node)
        
        self.visit(node.body)
    
    def visit_ForStatement(self, node: ForStatement):
        """访问for循环"""
        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
            if node.condition.inferred_type and node.condition.inferred_type != TYPE_BOOL:
                self.add_error("for条件必须是布尔类型", node)
        if node.update:
            self.visit(node.update)
        self.visit(node.body)
    
    def visit_ReturnStatement(self, node: ReturnStatement):
        """访问return语句"""
        if node.value:
            self.visit(node.value)
    
    def analyze(self) -> List[SemanticError]:
        """执行语义分析"""
        self.visit(self.module)
        return self.errors
