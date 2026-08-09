"""
光明（Light）编程语言 - Python 后端 AST 节点定义

从 light_parser_v3.py 提取，作为独立模块供代码生成器/语义分析器使用。
"""

from typing import List, Any, Optional, Dict


# =============================================================================
# AST 节点定义
# =============================================================================

class ASTNode:
    """AST 节点基类"""
    __slots__ = ('line', 'col', '_ast_type_id')
    
    def __init__(self, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        self._ast_type_id = 0  # v3 节点统一使用 0，不参与 v4 的 _ast_type_id 分派


class Module(ASTNode):
    __slots__ = ('statements',)
    """模块"""
    def __init__(self, statements: List[ASTNode], line: int = 0, col: int = 0):
        super().__init__(line, col)
        self.statements = statements
    
    def __repr__(self):
        return f"Module({len(self.statements)} statements)"


class ParameterList(ASTNode):
    __slots__ = ('params',)
    """参数列表（用于参数声明语句）"""
    def __init__(self, params: List[str]):
        self.params = params
    
    def __repr__(self):
        return f"ParameterList({self.params})"


class VarDecl(ASTNode):
    __slots__ = ('name', 'value', 'type_annotation')
    """变量声明"""
    def __init__(self, name: str, value: ASTNode, type_annotation: Optional[str] = None, line: int = 0, col: int = 0):
        super().__init__(line, col)
        self.name = name
        self.value = value
        self.type_annotation = type_annotation
    
    def __repr__(self):
        if self.type_annotation:
            return f"VarDecl({self.name}: {self.type_annotation} = {self.value})"
        return f"VarDecl({self.name} = {self.value})"


class IfStmt(ASTNode):
    __slots__ = ('condition', 'then_body', 'else_body')
    """条件语句"""
    def __init__(self, condition: ASTNode, then_body: List[ASTNode], else_body: Optional[List[ASTNode]] = None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body
    
    def __repr__(self):
        return f"IfStmt({self.condition})"


class ForeachStmt(ASTNode):
    __slots__ = ('variable', 'iterable', 'body', 'is_async')
    """遍历循环"""
    def __init__(self, variable: str, iterable: ASTNode, body: List[ASTNode], is_async: bool = False):
        self.variable = variable
        self.iterable = iterable
        self.body = body
        self.is_async = is_async
    
    def __repr__(self):
        prefix = "AsyncForeachStmt" if self.is_async else "ForeachStmt"
        return f"{prefix}({self.variable} in {self.iterable})"


class WhileStmt(ASTNode):
    __slots__ = ('condition', 'body')
    """当循环"""
    def __init__(self, condition: ASTNode, body: List[ASTNode]):
        self.condition = condition
        self.body = body
    
    def __repr__(self):
        return f"WhileStmt({self.condition})"


class Paragraph(ASTNode):
    __slots__ = ('name', 'params', 'return_type', 'body', 'generic_params', 'modifiers',
                 'access_modifier', 'is_static', 'is_classmethod', 'is_property', 'is_abstract')
    """段落定义"""
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: Optional[str], body: List[ASTNode],
                 generic_params: List[str] = None, modifiers: List[str] = None):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
        self.generic_params = generic_params or []
        self.modifiers = modifiers or []
        self.access_modifier = 'public'
        self.is_static = False
        self.is_classmethod = False
        self.is_property = False
        self.is_abstract = False
    
    def __repr__(self):
        return f"Paragraph({self.name})"


class ReturnStmt(ASTNode):
    __slots__ = ('value',)
    """返回语句"""
    def __init__(self, value: Optional[ASTNode]):
        self.value = value
    
    def __repr__(self):
        return f"ReturnStmt({self.value})"


class BinaryOp(ASTNode):
    __slots__ = ('operator', 'left', 'right')
    """二元运算"""
    def __init__(self, operator: str, left: ASTNode, right: ASTNode):
        self.operator = operator
        self.left = left
        self.right = right
    
    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"


class UnaryOp(ASTNode):
    __slots__ = ('operator', 'operand')
    """一元运算
    
    支持的运算符：
    - '非'：逻辑非
    - '-'：负号
    """
    def __init__(self, operator: str, operand: ASTNode):
        self.operator = operator
        self.operand = operand
    
    def __repr__(self):
        return f"({self.operator} {self.operand})"


class NumberLiteral(ASTNode):
    __slots__ = ('value',)
    """数字字面量"""
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return f"{self.value}"


class StringLiteral(ASTNode):
    __slots__ = ('value',)
    """字符串字面量"""
    def __init__(self, value: str):
        self.value = value
    
    def __repr__(self):
        return f'"{self.value}"'


class Identifier(ASTNode):
    __slots__ = ('name',)
    """标识符"""
    def __init__(self, name: str):
        self.name = name
    
    def __repr__(self):
        return self.name


class ParagraphCall(ASTNode):
    __slots__ = ('name', 'args')
    """段落调用"""
    def __init__(self, name: str, args: List[ASTNode]):
        self.name = name
        self.args = args
    
    def __repr__(self):
        return f"《{self.name}》({', '.join(map(str, self.args))})"


class SliceExpr(ASTNode):
    __slots__ = ('start', 'stop', 'step')
    """切片表达式: start:stop:step"""
    def __init__(self, start: ASTNode = None, stop: ASTNode = None, step: ASTNode = None):
        self.start = start
        self.stop = stop
        self.step = step
    
    def __repr__(self):
        return f"{self.start or ''}:{self.stop or ''}:{self.step or ''}"


class IndexAccess(ASTNode):
    __slots__ = ('obj', 'index')
    """索引访问（字符串/列表索引）"""
    def __init__(self, obj: ASTNode, index: ASTNode):
        self.obj = obj
        self.index = index
    
    def __repr__(self):
        return f"{self.obj}[{self.index}]"


class AssignmentExpression(ASTNode):
    __slots__ = ('name', 'value')
    """赋值表达式（海象运算符等价物）：设 n 为 len(data) → n := len(data)"""
    def __init__(self, name: str, value: ASTNode):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f"设 {self.name} 为 {self.value}"


class BreakStmt(ASTNode):
    __slots__ = ()
    """跳出语句"""
    def __repr__(self):
        return "跳出"


class ContinueStmt(ASTNode):
    __slots__ = ()
    """跳过语句"""
    def __repr__(self):
        return "跳过"


class PassStmt(ASTNode):
    __slots__ = ()
    """空语句（pass）"""
    def __repr__(self):
        return "pass"


class TypeCheckToggleStmt(ASTNode):
    __slots__ = ('enable',)
    """类型检查开关语句：开启类型检查 / 关闭类型检查"""
    def __init__(self, enable: bool, line: int = 0, col: int = 0):
        super().__init__(line, col)
        self.enable = enable
    
    def __repr__(self):
        return f"TypeCheckToggle({'开启' if self.enable else '关闭'})"


class TryStmt(ASTNode):
    __slots__ = ('try_body', 'catch_clauses', 'catch_type', 'catch_var', 'catch_body', 'finally_body')
    """异常捕获语句"""
    def __init__(self, try_body: List[ASTNode], catch_clauses: List = None, 
                 catch_type: str = None, catch_var: str = None,
                 catch_body: List[ASTNode] = None, finally_body: List[ASTNode] = None):
        self.try_body = try_body
        self.catch_clauses = catch_clauses or []
        self.catch_type = catch_type
        self.catch_var = catch_var
        self.catch_body = catch_body or []
        self.finally_body = finally_body or []
    
    def __repr__(self):
        if self.catch_clauses:
            return f"TryStmt(catch_clauses: {len(self.catch_clauses)})"
        return f"TryStmt(catch: {self.catch_var})"


class CatchClause(ASTNode):
    __slots__ = ('catch_type', 'catch_var', 'catch_body')
    """捕获子句"""
    def __init__(self, catch_type: str = None, catch_var: str = None, catch_body: List[ASTNode] = None):
        self.catch_type = catch_type
        self.catch_var = catch_var
        self.catch_body = catch_body or []
    
    def __repr__(self):
        return f"CatchClause(type={self.catch_type}, var={self.catch_var})"


class ThrowStmt(ASTNode):
    __slots__ = ('value', 'from_expr')
    """抛出异常语句"""
    def __init__(self, value: ASTNode, from_expr: ASTNode = None):
        self.value = value
        self.from_expr = from_expr
    
    def __repr__(self):
        if self.from_expr:
            return f"ThrowStmt({self.value} from {self.from_expr})"
        return f"ThrowStmt({self.value})"


class Pipeline(ASTNode):
    __slots__ = ('stages',)
    """管道操作"""
    def __init__(self, stages: List[ASTNode]):
        self.stages = stages
    
    def __repr__(self):
        return ' -> '.join(map(str, self.stages))


class ImportStmt(ASTNode):
    __slots__ = ('module_name', 'symbols', 'alias', 'extra_modules', 'language')
    """导入语句
    
    language: None=光明标准库, 'python'=Python第三方库, 'c'=C语言库
    """
    def __init__(self, module_name: str, symbols: List[str] = None, alias: str = None, extra_modules: list = None, language: str = None):
        self.module_name = module_name
        self.symbols = symbols
        self.alias = alias
        self.extra_modules = extra_modules or []  # 多模块导入时的额外模块 [(module_name, alias), ...]
        self.language = language  # None=光明, 'python'=Python, 'c'=C
    
    def __repr__(self):
        lang_prefix = f"[{self.language}] " if self.language else ""
        if self.symbols:
            symbols_str = ', '.join(self.symbols)
            if self.alias:
                return f"ImportStmt({lang_prefix}from {self.module_name} import {symbols_str} as {self.alias})"
            return f"ImportStmt({lang_prefix}from {self.module_name} import {symbols_str})"
        else:
            if self.alias:
                return f"ImportStmt({lang_prefix}import {self.module_name} as {self.alias})"
            return f"ImportStmt({lang_prefix}import {self.module_name})"


class ExportStmt(ASTNode):
    __slots__ = ('symbols',)
    """导出语句"""
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
    
    def __repr__(self):
        return f"ExportStmt({', '.join(self.symbols)})"


class Parameter(ASTNode):
    __slots__ = ('name', 'type_annotation', 'default_value')
    """参数定义"""
    def __init__(self, name: str, type_annotation: str = None, default_value: ASTNode = None):
        self.name = name
        self.type_annotation = type_annotation
        self.default_value = default_value
    
    def __repr__(self):
        return f"Parameter({self.name})"


class AttributeDeclaration(ASTNode):
    __slots__ = ('name', 'type_annotation', 'default_value', 'access_modifier', 'is_static')
    """属性声明"""
    def __init__(self, name: str, type_annotation: str = None, default_value: ASTNode = None,
                 access_modifier: str = 'public', is_static: bool = False):
        self.name = name
        self.type_annotation = type_annotation
        self.default_value = default_value
        self.access_modifier = access_modifier
        self.is_static = is_static
    
    def __repr__(self):
        return f"AttributeDeclaration({self.name})"


class MethodDefinition(ASTNode):
    __slots__ = ('name', 'parameters', 'body', 'return_type', 'is_constructor', 'generic_params', 'access_modifier', 'is_static', 'is_classmethod', 'is_property', 'is_abstract')
    """方法定义"""
    def __init__(self, name: str, parameters: List[Parameter], body: List[ASTNode],
                 return_type: str = None, is_constructor: bool = False,
                 generic_params: List[str] = None,
                 access_modifier: str = 'public', is_static: bool = False,
                 is_classmethod: bool = False, is_property: bool = False,
                 is_abstract: bool = False):
        self.name = name
        self.parameters = parameters
        self.body = body
        self.return_type = return_type
        self.is_constructor = is_constructor
        self.generic_params = generic_params or []
        self.access_modifier = access_modifier
        self.is_static = is_static
        self.is_classmethod = is_classmethod
        self.is_property = is_property
        self.is_abstract = is_abstract
    
    def __repr__(self):
        return f"MethodDefinition({self.name})"


class CompoundAssignment(ASTNode):
    __slots__ = ('target', 'operator', 'value')
    """复合赋值（甲 加上 1 → 甲 += 1）"""
    def __init__(self, target: str, operator: str, value: ASTNode):
        self.target = target
        self.operator = operator  # '加', '减', '乘', '除', '模', '幂'
        self.value = value
    
    def __repr__(self):
        return f"CompoundAssignment({self.target} {self.operator}= {self.value})"


class IndexedAssignment(ASTNode):
    __slots__ = ('target', 'index', 'value')
    """索引赋值（甲[丁] 为 值 → 甲[丁] = 值）"""
    def __init__(self, target: str, index: ASTNode, value: ASTNode):
        self.target = target
        self.index = index
        self.value = value
    
    def __repr__(self):
        return f"IndexedAssignment({self.target}[{self.index}] = {self.value})"


class IndexedCompoundAssignment(ASTNode):
    __slots__ = ('target', 'index', 'operator', 'value')
    """索引复合赋值（甲[丁] 加上 值 → 甲[丁] += 值）"""
    def __init__(self, target: str, index: ASTNode, operator: str, value: ASTNode):
        self.target = target
        self.index = index
        self.operator = operator  # '加', '减', '乘', '除', '模', '幂'
        self.value = value
    
    def __repr__(self):
        return f"IndexedCompoundAssignment({self.target}[{self.index}] {self.operator}= {self.value})"


class Assignment(ASTNode):
    __slots__ = ('target', 'value')
    """赋值语句（target 可以是 Identifier、PropertyAccess、IndexAccess 等）"""
    def __init__(self, target: ASTNode, value: ASTNode):
        self.target = target
        self.value = value
    
    def __repr__(self):
        return f"Assignment({self.target} = {self.value})"


class SelfAssignment(ASTNode):
    __slots__ = ('attr_name', 'value')
    """self赋值语句"""
    def __init__(self, attr_name: str, value: ASTNode):
        self.attr_name = attr_name
        self.value = value
    
    def __repr__(self):
        return f"SelfAssignment(self.{self.attr_name})"


class ClassDefinition(ASTNode):
    __slots__ = ('name', 'attributes', 'methods', 'base_classes', 'generic_params', 'interfaces')
    """类定义"""
    def __init__(self, name: str, attributes: List[AttributeDeclaration], 
                 methods: List[MethodDefinition], base_classes: List[str] = None,
                 generic_params: List[str] = None, interfaces: List[str] = None):
        self.name = name
        self.attributes = attributes
        self.methods = methods
        self.base_classes = base_classes or []
        self.generic_params = generic_params or []
        self.interfaces = interfaces or []
    
    def __repr__(self):
        return f"ClassDefinition({self.name})"


class ClassInstantiation(ASTNode):
    __slots__ = ('class_name', 'args')
    """类实例化"""
    def __init__(self, class_name: str, args: List[ASTNode]):
        self.class_name = class_name
        self.args = args
    
    def __repr__(self):
        return f"ClassInstantiation({self.class_name})"


class ConditionalExpression(ASTNode):
    __slots__ = ('condition', 'then_expr', 'else_expr')
    """三元条件表达式"""
    def __init__(self, condition: ASTNode, then_expr: ASTNode, else_expr: Optional[ASTNode] = None):
        self.condition = condition
        self.then_expr = then_expr
        self.else_expr = else_expr
    
    def __repr__(self):
        return f"ConditionalExpression({self.condition}, {self.then_expr}, {self.else_expr})"


class MemberAccess(ASTNode):
    __slots__ = ('obj', 'member', 'is_method_call', 'args')
    """成员访问"""
    def __init__(self, obj: ASTNode, member: str, is_method_call: bool = False, args: List[ASTNode] = None):
        self.obj = obj
        self.member = member
        self.is_method_call = is_method_call
        self.args = args or []
    
    def __repr__(self):
        return f"MemberAccess({self.obj}.{self.member})"


class ListLiteral(ASTNode):
    __slots__ = ('elements',)
    """列表字面量"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements
    
    def __repr__(self):
        return f"[{', '.join(map(str, self.elements))}]"


class TupleLiteral(ASTNode):
    __slots__ = ('elements',)
    """元组字面量"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements
    
    def __repr__(self):
        return f"({', '.join(map(str, self.elements))})"


class SetLiteral(ASTNode):
    __slots__ = ('elements',)
    """集合字面量"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements
    
    def __repr__(self):
        return f"{{{', '.join(map(str, self.elements))}}}"


class StringInterpolation(ASTNode):
    __slots__ = ('parts',)
    """字符串插值"""
    def __init__(self, parts: List):
        self.parts = parts  # 交替的 str 和 ASTNode
    
    def __repr__(self):
        return f"StringInterpolation({len(self.parts)} parts)"


class ListComprehension(ASTNode):
    __slots__ = ('expression', 'variable', 'iterable', 'condition', 'generators')
    """列表推导"""
    def __init__(self, expression: ASTNode, variable: str, iterable: ASTNode, condition: ASTNode = None, generators=None):
        self.expression = expression
        self.variable = variable
        self.iterable = iterable
        self.condition = condition
        # generators: List of (variable_str, iterable_ast, condition_ast_or_None)
        # None means single generator (backward compat)
        self.generators = generators
    
    def __repr__(self):
        return f"ListComprehension([{self.expression} for {self.variable} in {self.iterable}])"


class SetComprehension(ASTNode):
    __slots__ = ('expression', 'variable', 'iterable', 'condition', 'generators')
    """集合推导: {expr for var in iterable if condition}"""
    def __init__(self, expression: ASTNode, variable: str, iterable: ASTNode, condition: ASTNode = None, generators=None):
        self.expression = expression
        self.variable = variable
        self.iterable = iterable
        self.condition = condition
        # generators: List of (variable_str, iterable_ast, condition_ast_or_None)
        # None means single generator (backward compat)
        self.generators = generators
    
    def __repr__(self):
        return f"SetComprehension({{{self.expression} for {self.variable} in {self.iterable}}})"


class LambdaExpression(ASTNode):
    __slots__ = ('params', 'body')
    """匿名函数"""
    def __init__(self, params: List[str], body: ASTNode):
        self.params = params
        self.body = body
    
    def __repr__(self):
        return f"Lambda({', '.join(self.params)}: {self.body})"


class MatchStmt(ASTNode):
    __slots__ = ('subject', 'cases')
    """模式匹配"""
    def __init__(self, subject: ASTNode, cases: List):
        self.subject = subject
        self.cases = cases
    
    def __repr__(self):
        return f"MatchStmt({len(self.cases)} cases)"


class MatchCase(ASTNode):
    __slots__ = ('pattern', 'guard', 'body')
    """匹配分支"""
    def __init__(self, pattern, guard: ASTNode = None, body: List[ASTNode] = None):
        self.pattern = pattern
        self.guard = guard
        self.body = body or []
    
    def __repr__(self):
        return f"MatchCase({self.pattern})"


class MatchPattern(ASTNode):
    __slots__ = ('kind', 'value', 'elements', 'type_name', 'binding')
    """匹配模式"""
    def __init__(self, kind: str, value=None, elements: List = None, type_name: str = '', binding: str = ''):
        self.kind = kind
        self.value = value
        self.elements = elements or []
        self.type_name = type_name
        self.binding = binding
    
    def __repr__(self):
        if self.kind == 'wildcard':
            return '_'
        if self.kind == 'variable':
            return self.binding
        if self.kind == 'number':
            return str(self.value)
        if self.kind == 'string':
            return f'"{self.value}"'
        return f"MatchPattern({self.kind})"


class DictComprehension(ASTNode):
    __slots__ = ('key_expr', 'value_expr', 'variable', 'iterable', 'condition', 'generators')
    """字典推导"""
    def __init__(self, key_expr: ASTNode, value_expr: ASTNode, variable: str,
                 iterable: ASTNode, condition: ASTNode = None, generators=None):
        self.key_expr = key_expr
        self.value_expr = value_expr
        self.variable = variable
        self.iterable = iterable
        self.condition = condition
        # generators: List of (variable_str, iterable_ast, condition_ast_or_None)
        # None means single generator (backward compat)
        self.generators = generators
    
    def __repr__(self):
        return f"DictComprehension({{{self.key_expr}: {self.value_expr} for {self.variable} in {self.iterable}}})"


class DecoratorDefinition(ASTNode):
    __slots__ = ('decorator_name', 'paragraph', 'args')
    """装饰器定义"""
    def __init__(self, decorator_name: str, paragraph, args=None):
        self.decorator_name = decorator_name
        self.paragraph = paragraph
        self.args = args  # 可选的装饰器参数列表（如 @repeat(3) 中的 [3]）
    
    def __repr__(self):
        return f"DecoratorDefinition(@{self.decorator_name})"


class MethodSignature(ASTNode):
    __slots__ = ('name', 'parameters', 'return_type')
    """接口方法签名"""
    def __init__(self, name: str, parameters: List[Parameter] = None, return_type: str = None):
        self.name = name
        self.parameters = parameters or []
        self.return_type = return_type
    
    def __repr__(self):
        return f"MethodSignature({self.name})"


class InterfaceDefinition(ASTNode):
    __slots__ = ('name', 'methods', 'properties', 'super_interfaces')
    """接口定义"""
    def __init__(self, name: str, methods: List[MethodSignature], 
                 properties: List[AttributeDeclaration] = None,
                 super_interfaces: List[str] = None):
        self.name = name
        self.methods = methods
        self.properties = properties or []
        self.super_interfaces = super_interfaces or []
    
    def __repr__(self):
        return f"InterfaceDefinition({self.name})"


class DestructuringAssignment(ASTNode):
    __slots__ = ('variables', 'value', 'style')
    """解构赋值
    
    style: 'tuple' 或 'list'，区分元组解构和列表解构
    """
    def __init__(self, variables: List[str], value: ASTNode, style: str = 'tuple'):
        self.variables = variables
        self.value = value
        self.style = style  # 'tuple' 或 'list'
    
    def __repr__(self):
        bracket = '(' if self.style == 'tuple' else '['
        end_bracket = ')' if self.style == 'tuple' else ']'
        return f"DestructuringAssignment({bracket}{', '.join(self.variables)}{end_bracket} = {self.value})"


class WithStmt(ASTNode):
    __slots__ = ('context_expr', 'variable', 'body')
    """上下文管理器"""
    def __init__(self, context_expr: ASTNode, variable: str = None, body: List[ASTNode] = None):
        self.context_expr = context_expr
        self.variable = variable
        self.body = body or []
    
    def __repr__(self):
        var = f" as {self.variable}" if self.variable else ""
        return f"WithStmt({self.context_expr}{var})"


class DictLiteral(ASTNode):
    __slots__ = ('entries',)
    """字典字面量"""
    def __init__(self, entries: List):
        self.entries = entries
    
    def __repr__(self):
        items = [f"{k}: {v}" for k, v in self.entries]
        return f"DictLiteral({{{', '.join(items)}}})"


class RangeExpr(ASTNode):
    __slots__ = ('start', 'end', 'step')
    """范围表达式
    
    语法：
    - 1至10       # 从1到10（包含10）
    - 1到10       # 从1到10（包含10）
    - 1到10步2    # 从1到10，步长为2
    
    生成 Python: range(start, end+1) 或 range(start, end+1, step)
    """
    def __init__(self, start: ASTNode, end: ASTNode, step: ASTNode = None):
        self.start = start
        self.end = end
        self.step = step
    
    def __repr__(self):
        step_str = f"步{self.step}" if self.step else ""
        return f"RangeExpr({self.start}至{self.end}{step_str})"


# =============================================================================
# 异步/并发节点
# =============================================================================

class AwaitExpr(ASTNode):
    __slots__ = ('expression',)
    """等待表达式（等待 异步操作）"""
    def __init__(self, expression: ASTNode):
        self.expression = expression
    
    def __repr__(self):
        return f"等待({self.expression})"


class AsyncScope(ASTNode):
    __slots__ = ('tasks', 'result_vars')
    """并行作用域（结构化并发）"""
    def __init__(self, tasks: List[ASTNode], result_vars: List[str] = None):
        self.tasks = tasks
        self.result_vars = result_vars or []
    
    def __repr__(self):
        return f"异步作用域({len(self.tasks)}个任务)"


# =============================================================================
# C FFI 节点（外部函数接口）
# =============================================================================

class FFILoadLibrary(ASTNode):
    __slots__ = ('library_path', 'alias')
    """加载动态库：加载库 "libxxx.so" 为 别名"""
    def __init__(self, library_path: str, alias: str):
        self.library_path = library_path
        self.alias = alias
    
    def __repr__(self):
        return f"FFILoadLibrary({self.library_path} -> {self.alias})"


class FFIFunctionDecl(ASTNode):
    __slots__ = ('name', 'params', 'return_type', 'library_alias', 'c_name')
    """
    外部函数声明：外部 段落 函数名 接收 参数... 返回 类型 在 库别名
    c_name: 可选，实际的C函数名（如果与光明函数名不同）
    """
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: Optional[str],
                 library_alias: str, c_name: str = None):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.library_alias = library_alias
        self.c_name = c_name or name
    
    def __repr__(self):
        return f"FFIFunctionDecl({self.name} in {self.library_alias})"


class FFIStructDef(ASTNode):
    __slots__ = ('name', 'fields')
    """
    C结构体定义：外部 结构体 名称 { 字段1: 类型, 字段2: 类型 }
    用于定义与C对应的结构体类型
    """
    def __init__(self, name: str, fields: List[Dict[str, str]]):
        self.name = name
        self.fields = fields
    
    def __repr__(self):
        return f"FFIStructDef({self.name}, {len(self.fields)} fields)"


class FFICallbackDef(ASTNode):
    __slots__ = ('name', 'params', 'return_type')
    """
    C回调函数类型定义：外部 回调 名称 接收 参数... 返回 类型
    用于定义C回调函数签名
    """
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: Optional[str]):
        self.name = name
        self.params = params
        self.return_type = return_type
    
    def __repr__(self):
        return f"FFICallbackDef({self.name})"


# =============================================================================
# C FFI 指针/数组/错误处理节点（第二阶段）
# =============================================================================

class FFIPointerType(ASTNode):
    __slots__ = ('base_type',)
    """指针类型：指针[整数]"""
    def __init__(self, base_type: str):
        self.base_type = base_type
    
    def __repr__(self):
        return f"指针[{self.base_type}]"


class FFIArrayType(ASTNode):
    __slots__ = ('base_type', 'size')
    """数组类型：数组[整数] 或 数组[整数, 5]"""
    def __init__(self, base_type: str, size: Optional[int] = None):
        self.base_type = base_type
        self.size = size
    
    def __repr__(self):
        if self.size:
            return f"数组[{self.base_type}, {self.size}]"
        return f"数组[{self.base_type}]"


class FFIAddressOf(ASTNode):
    __slots__ = ('target',)
    """取地址：取地址(变量)"""
    def __init__(self, target: ASTNode):
        self.target = target
    
    def __repr__(self):
        return f"取地址({self.target})"


class FFIDereference(ASTNode):
    __slots__ = ('pointer',)
    """解引用：解引用(指针)"""
    def __init__(self, pointer: ASTNode):
        self.pointer = pointer
    
    def __repr__(self):
        return f"解引用({self.pointer})"


class FFIPointerOffset(ASTNode):
    __slots__ = ('pointer', 'offset')
    """指针偏移：指针偏移(指针, 偏移量)"""
    def __init__(self, pointer: ASTNode, offset: ASTNode):
        self.pointer = pointer
        self.offset = offset
    
    def __repr__(self):
        return f"指针偏移({self.pointer}, {self.offset})"


class FFISetPointerValue(ASTNode):
    __slots__ = ('pointer', 'value')
    """通过指针写入值：设指针值(指针, 值)"""
    def __init__(self, pointer: ASTNode, value: ASTNode):
        self.pointer = pointer
        self.value = value
    
    def __repr__(self):
        return f"设指针值({self.pointer}, {self.value})"


class FFIAllocMemory(ASTNode):
    __slots__ = ('size',)
    """分配内存：分配内存(大小)"""
    def __init__(self, size: ASTNode):
        self.size = size
    
    def __repr__(self):
        return f"分配内存({self.size})"


class FFIFreeMemory(ASTNode):
    __slots__ = ('pointer',)
    """释放内存：释放内存(指针)"""
    def __init__(self, pointer: ASTNode):
        self.pointer = pointer
    
    def __repr__(self):
        return f"释放内存({self.pointer})"


class FFICreateArray(ASTNode):
    __slots__ = ('base_type', 'size')
    """创建数组：创建数组 整数 [5]"""
    def __init__(self, base_type: str, size: ASTNode):
        self.base_type = base_type
        self.size = size
    
    def __repr__(self):
        return f"创建数组 {self.base_type}[{self.size}]"


class FFISetArrayElement(ASTNode):
    __slots__ = ('array', 'index', 'value')
    """设置数组元素：设置数组(数组, 索引, 值)"""
    def __init__(self, array: ASTNode, index: ASTNode, value: ASTNode):
        self.array = array
        self.index = index
        self.value = value
    
    def __repr__(self):
        return f"设置数组({self.array}, {self.index}, {self.value})"


class FFIGetLastError(ASTNode):
    __slots__ = ()
    """获取最后的FFI错误：获取FFI错误()"""
    def __repr__(self):
        return "获取FFI错误()"


class FFIGetErrno(ASTNode):
    __slots__ = ()
    """获取系统错误码：获取系统错误码()"""
    def __repr__(self):
        return "获取系统错误码()"


class FFISetErrno(ASTNode):
    __slots__ = ('value',)
    """设置系统错误码：设系统错误码(值)"""
    def __init__(self, value: ASTNode):
        self.value = value
    
    def __repr__(self):
        return f"设系统错误码({self.value})"


class FFITryCatch(ASTNode):
    __slots__ = ('try_body', 'error_var', 'catch_body')
    """FFI 错误捕获：尝试 捕获 外部错误 为 甲："""
    def __init__(self, try_body: List[ASTNode], error_var: str = None,
                 catch_body: List[ASTNode] = None):
        self.try_body = try_body or []
        self.error_var = error_var or '错误'
        self.catch_body = catch_body or []
    
    def __repr__(self):
        return f"FFITryCatch({len(self.try_body)} try, {len(self.catch_body)} catch)"


# =============================================================================
# C FFI 第三阶段：回调/结构体传值/枚举/联合体/变长参数
# =============================================================================

class FFIEnumDef(ASTNode):
    __slots__ = ('name', 'values')
    """
    C枚举定义：外部 枚举 名称 { 成员 = 值, ... }
    """
    def __init__(self, name: str, values: Dict[str, int]):
        self.name = name
        self.values = values
    
    def __repr__(self):
        return f"FFIEnumDef({self.name}, {len(self.values)} values)"


class FFIUnionDef(ASTNode):
    __slots__ = ('name', 'fields')
    """
    C联合体定义：外部 联合体 名称 { 字段: 类型, ... }
    """
    def __init__(self, name: str, fields: List[Dict[str, str]]):
        self.name = name
        self.fields = fields
    
    def __repr__(self):
        return f"FFIUnionDef({self.name}, {len(self.fields)} fields)"


class FFICreateCallback(ASTNode):
    __slots__ = ('callback_type', 'light_function')
    """
    创建回调：创建回调(回调类型, 光明函数)
    """
    def __init__(self, callback_type: str, light_function: str):
        self.callback_type = callback_type
        self.light_function = light_function
    
    def __repr__(self):
        return f"创建回调({self.callback_type}, {self.light_function})"


class FFIVarArgsDecl(ASTNode):
    __slots__ = ('name', 'params', 'return_type', 'library_alias', 'c_name')
    """
    变长参数外部函数声明：外部 段落 名称 接收 参数... 在 库别名
    """
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: Optional[str],
                 library_alias: str, c_name: str = None):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.library_alias = library_alias
        self.c_name = c_name or name
    
    def __repr__(self):
        return f"FFIVarArgsDecl({self.name} in {self.library_alias})"


class FFIStructByValue(ASTNode):
    __slots__ = ('struct_type', 'fields')
    """
    结构体按值传递：用于创建结构体实例并传递给C函数
    """
    def __init__(self, struct_type: str, fields: Dict[str, ASTNode]):
        self.struct_type = struct_type
        self.fields = fields
    
    def __repr__(self):
        return f"FFIStructByValue({self.struct_type}, {len(self.fields)} fields)"


class FFILibraryPath(ASTNode):
    __slots__ = ('name', 'platform_map')
    """
    跨平台库路径：根据当前平台自动选择库文件
    """
    def __init__(self, name: str, platform_map: Dict[str, str] = None):
        self.name = name
        self.platform_map = platform_map or {}
    
    def __repr__(self):
        return f"FFILibraryPath({self.name})"


# =============================================================================
# C FFI 第四阶段：typedef/位域/函数指针/回调生命周期/调试
# =============================================================================

class FFITypedefDef(ASTNode):
    __slots__ = ('name', 'base_type')
    """C类型别名：外部 类型别名 名称 为 基础类型"""
    def __init__(self, name: str, base_type: str):
        self.name = name
        self.base_type = base_type
    
    def __repr__(self):
        return f"FFITypedefDef({self.name} -> {self.base_type})"


class FFIBitfieldDef(ASTNode):
    __slots__ = ('name', 'base_type', 'fields')
    """C位域定义：外部 位域 名称 : 基础类型 { 字段: 位数, ... }"""
    def __init__(self, name: str, base_type: str, fields: List[Dict[str, int]]):
        self.name = name
        self.base_type = base_type
        self.fields = fields
    
    def __repr__(self):
        return f"FFIBitfieldDef({self.name}, {len(self.fields)} fields)"


class FFIFuncPtrDef(ASTNode):
    __slots__ = ('name', 'params', 'return_type')
    """C函数指针类型：外部 函数指针 名称 接收 参数... 返回 类型"""
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: Optional[str]):
        self.name = name
        self.params = params
        self.return_type = return_type
    
    def __repr__(self):
        return f"FFIFuncPtrDef({self.name})"


class FFIDebugConfig(ASTNode):
    __slots__ = ('enabled', 'log_calls', 'log_types', 'trace_memory')
    """FFI调试配置：外部 调试 { 开启, 记录调用, 记录类型, 追踪内存 }"""
    def __init__(self, enabled: bool = True, log_calls: bool = False,
                 log_types: bool = False, trace_memory: bool = False):
        self.enabled = enabled
        self.log_calls = log_calls
        self.log_types = log_types
        self.trace_memory = trace_memory
    
    def __repr__(self):
        return f"FFIDebugConfig(enabled={self.enabled})"


class FFIPreprocessorDef(ASTNode):
    __slots__ = ('name', 'value')
    """C预处理器宏：外部 宏 名称 为 值"""
    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f"FFIPreprocessorDef({self.name}={self.value})"


class KeywordArg(ASTNode):
    """关键字参数：name=value（用于函数/方法调用中的关键字参数）"""
    __slots__ = ('name', 'value')
    def __init__(self, name: str, value):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f"KeywordArg({self.name}={self.value})"


class EmbedBlock(ASTNode):
    """嵌入块语句：嵌入 Python/C: ... 结束嵌入
    
    将外部语言代码作为"外语引用"嵌入光明代码中，
    类似中文文本中嵌入数学公式或英文片段。
    """
    __slots__ = ('language', 'code', 'imports', 'exports')
    def __init__(self, language: str = '', code: str = '',
                 imports: list = None, exports: list = None,
                 line: int = 0, col: int = 0):
        super().__init__(line, col)
        self.language = language       # "Python", "C" 等
        self.code = code               # 原始嵌入代码
        self.imports = imports or []   # 需要传入的光明变量名列表
        self.exports = exports or []   # 需要传出的变量名列表
    
    def __repr__(self):
        return f"EmbedBlock({self.language}, {len(self.code)} chars)"