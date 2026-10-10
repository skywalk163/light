"""
光明（Light）编程语言 - 语义分析器

负责：
1. 符号表构建和管理
2. 类型检查和推断
3. 作用域分析
4. 错误检测
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from ast_unified import *

# =============================================================================
# R135-A · L5 G1：ast_nodes_v3 适配层
# =============================================================================
# 背景（docs/known_issues.md G1）：
#   `SemanticAnalyzer` 期望 `ast_unified.Module`（有 `add_scope` 等符号表接口），
#   而 `light_parser_v3` 产出 `ast_nodes_v3.Module`（`__slots__` 类，只有
#   `statements`）。两套 AST 的节点命名体系也不同（`VarDecl` vs
#   `VariableDeclaration`），直接派发会整片落进 `visit_default`，等于空跑。
#
# 适配策略（任务书 §3.2 路线 2a + 独立符号表）：
#   1) 符号表不挂在 module 上，改由分析器自带（`self.scopes`）——
#      v3 Module 无需补任何接口。
#   2) v3 节点走独立分派（`_v3_visit_<节点名>`），与既有 unified `visit_*`
#      彻底隔离，既有 unified 语义逻辑与行为零改动。
#   3) 不向 v3 节点写回任何属性（ast_nodes_v3 全族 `__slots__`，写回即
#      AttributeError）。
#   4) v3 的 `数`/`串`/`布尔` 等类型只映射到统一类型的“标签”，
#      用于建立符号条目；类型兼容性检查在 v3 模式下关闭，避免大面积误报
#      （见 `docs/known_issues.md` G1 条目）。
# =============================================================================

try:  # v3 AST 可选依赖：缺失时 unified 路径仍可独立工作
    import ast_nodes_v3 as _v3

    _V3_AVAILABLE = True
except Exception:  # pragma: no cover - 仅防御性兜底
    _v3 = None
    _V3_AVAILABLE = False


# v3 节点名 → ast_unified 节点名（供文档/诊断与未来统一使用）
V3_TO_UNIFIED = {
    'VarDecl': 'VariableDeclaration',
    'Paragraph': 'FunctionDefinition',
    'ParagraphCall': 'FunctionCall',
    'FunctionCallExpr': 'FunctionCall',
    'IfStmt': 'IfStatement',
    'WhileStmt': 'WhileStatement',
    'ForeachStmt': 'ForStatement',
    'ReturnStmt': 'ReturnStatement',
    'BreakStmt': 'BreakStatement',
    'ContinueStmt': 'ContinueStatement',
    'IndexAccess': 'ArrayAccess',
    'MemberAccess': 'StructAccess',
    'ClassDefinition': 'StructDefinition',
    'RecordDefinition': 'StructDefinition',
}


def _is_v3_node(node: Any) -> bool:
    """判断是否 ast_nodes_v3 节点。"""
    return _V3_AVAILABLE and isinstance(node, _v3.ASTNode)


def _is_v3_module(module: Any) -> bool:
    """判断入参是 v3 Module 还是 unified Module。

    v3 Module 只有 `statements`；unified Module 有 `add_scope`/`scopes`。
    """
    if module is None:
        return False
    if _V3_AVAILABLE and isinstance(module, _v3.Module):
        return True
    return hasattr(module, 'statements') and not hasattr(module, 'add_scope')


# ---- 已知可调用名（避免把内置调用误报成“未定义符号”） --------------------
try:
    from keywords import (
        ALL_VERB_ARITY as _ALL_VERB_ARITY,
        ALL_KEYWORDS as _ALL_KEYWORDS,
        BUILTIN_TYPES as _BUILTIN_TYPES,
    )
except Exception:  # pragma: no cover - 仅防御性兜底
    _ALL_VERB_ARITY, _ALL_KEYWORDS, _BUILTIN_TYPES = {}, frozenset(), frozenset()

# 字面量/常量关键字：解析器把 `真`/`假` 折成 Identifier('True'/'False')
_V3_LITERAL_NAMES = frozenset({'True', 'False', 'None', '真', '假', '空', '真值', '假值'})

# v3 模式用的两个“宽类型”标签：`数` 与“未知/任意”。
# 复用统一类型体系里的既有单例，避免新增类型种类污染 unified 路径。
# v3 模式关闭类型兼容性检查（否则 `数` 与 `串` 会在字面量比较处大面积误报），
# 因此这两个标签只承担“符号存在性”的登记职责。
TYPE_NUMBER = PrimitiveType('number')
TYPE_ANY = PrimitiveType('any')

_STATIC_CALLABLE = (
    frozenset(_ALL_VERB_ARITY) | frozenset(_ALL_KEYWORDS) | frozenset(_BUILTIN_TYPES)
)
_KNOWN_CALLABLE_CACHE: Optional[frozenset] = None


def _is_known_callable(name: Optional[str]) -> bool:
    """名字是否为已登记的可调用/内置名（动词表 + 关键字 + 代码生成器内建表）。

    代码生成器内建表惰性加载且整体 try/except：该表缺失绝不能把语义分析
    拖成异常源。
    """
    if not name:
        return False
    if name in _V3_LITERAL_NAMES:
        return True
    global _KNOWN_CALLABLE_CACHE
    if _KNOWN_CALLABLE_CACHE is None:
        names = set(_STATIC_CALLABLE)
        try:
            from code_generator import PythonCodeGenerator

            names |= set(PythonCodeGenerator().builtin_map.keys())
        except Exception:  # pragma: no cover - 兜底
            pass
        _KNOWN_CALLABLE_CACHE = frozenset(names)
    return name in _KNOWN_CALLABLE_CACHE

class SemanticError(Exception):
    """语义错误异常"""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column

class SemanticAnalyzer(ASTVisitor):
    """语义分析器

    R135-A：同时支持两套 AST
      * `ast_unified.Module` → 走既有 `visit_*`，符号表挂在 module 上（行为不变）
      * `ast_nodes_v3.Module` → 走内部 `_v3_visit_<节点名>`，自带独立符号表
    """

    def __init__(self, module: Module):
        self.module = module
        self.errors: List[SemanticError] = []

        # R135-A：v3 模式开关。两种模式彻底隔离，互不污染。
        self.v3_mode = _is_v3_module(module)

        if self.v3_mode:
            # 独立符号表：不挂在 module 上（v3 Module 无 add_scope）
            self.scopes: Dict[int, Dict[str, Symbol]] = {}
            self._scope_stack: List[int] = []
            # 类作用域栈：`己属性 为 值` 声明的属性要落在最近的类作用域上
            self._v3_class_scopes: List[int] = []
            # 文件里是否存在「来源不可知」的导入（`导入 X`，无符号表）
            self._v3_has_opaque_import = False
            self._v3_new_scope()
        else:
            self.current_scope_id = 0
            # 创建全局作用域（unified 路径原行为）
            self.module.add_scope()

    # ------------------------------------------------------------------
    # 符号表：v3 模式实现（统一模式仍走 module.add_scope/lookup_symbol）
    # ------------------------------------------------------------------
    def _v3_new_scope(self) -> int:
        """v3 模式：新建作用域并压栈。"""
        scope_id = len(self.scopes) + 1
        self.scopes[scope_id] = {}
        self._scope_stack.append(scope_id)
        self.current_scope_id = scope_id
        return scope_id

    def _v3_pop_scope(self) -> None:
        """v3 模式：退出当前作用域。"""
        if self._scope_stack:
            self._scope_stack.pop()
        self.current_scope_id = self._scope_stack[-1] if self._scope_stack else 1

    def _v3_lookup(self, name: str) -> Optional[Symbol]:
        """v3 模式：沿作用域栈自内向外查找。"""
        for scope_id in reversed(self._scope_stack):
            found = self.scopes.get(scope_id, {}).get(name)
            if found is not None:
                return found
        return None

    def _v3_declare(self, name: str, type: Optional[Type], node: Any,
                    is_mutable: bool = False) -> Optional[Symbol]:
        """v3 模式：在当前作用域声明符号。

        v3 语义口径：重复声明 = 重绑定，**不**报「已在当前作用域定义」。
        """
        symbol = Symbol(
            name=name,
            type=type,
            scope_id=self.current_scope_id,
            is_mutable=is_mutable,
        )
        self.scopes.setdefault(self.current_scope_id, {})[name] = symbol
        return symbol

    def add_error(self, message: str, node: ASTNode):
        """添加错误"""
        self.errors.append(SemanticError(
            message,
            getattr(node, 'line', 0) or 0,
            getattr(node, 'col', getattr(node, 'column', 0)) or 0,
        ))
    
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
        existing = self._lookup_current_scope(name)
        if existing:
            if existing.scope_id == self.current_scope_id:
                self.add_error(f"符号 '{name}' 已在当前作用域定义", node)
                return None

        self._store_symbol(symbol)
        return symbol

    def _lookup_current_scope(self, name: str) -> Optional[Symbol]:
        """当前作用域查找（兼容两套模式）。"""
        if self.v3_mode:
            return self.scopes.get(self.current_scope_id, {}).get(name)
        return self.module.lookup_symbol(self.current_scope_id, name)

    def _store_symbol(self, symbol: Symbol) -> None:
        """写入符号表（兼容两套模式）。"""
        if self.v3_mode:
            self.scopes.setdefault(self.current_scope_id, {})[symbol.name] = symbol
        else:
            self.module.add_symbol(self.current_scope_id, symbol.name, symbol)
    
    def resolve_symbol(self, name: str, node: ASTNode) -> Optional[Symbol]:
        """解析符号引用"""
        symbol = self._lookup_current_scope(name)
        if not symbol:
            self.add_error(f"未定义的符号 '{name}'", node)
        return symbol
    
    def check_types(self, expected: Type, actual: Type, node: ASTNode, context: str = ""):
        """检查类型兼容性（使用子类型关系，支持多态）"""
        if expected is None or actual is None:
            return
        if self.v3_mode:
            # v3 类型标签过粗（`数`/`任意`），类型兼容性检查会大面积误报，
            # 故 v3 模式只做符号存在性检查。详见 docs/known_issues.md G1。
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
        """访问模块（R135-A：v3 Module 自动路由到适配层）"""
        if self.v3_mode:
            return self._v3_visit_module(node)

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
    
    # ==================================================================
    # R135-A · v3 适配层
    # ==================================================================
    # 设计要点：
    #   * v3 节点**不写回任何属性**（ast_nodes_v3 全族用 __slots__，写回即崩）；
    #     所有分析结果只落在分析器自带的符号表里。
    #   * 未知 v3 节点一律走 `_v3_visit_unknown` 保守递归，不报错、不中断。
    #   * 只有「用了查不到的普通标识符」才记一条语义错误。
    # ==================================================================
    def analyze_v3(self, module: Any) -> List[SemanticError]:
        """对 `ast_nodes_v3.Module` 执行语义分析。"""
        self._v3_visit_module(module)
        return self.errors

    def _v3_dispatch(self, node: Any):
        """v3 节点分派：查 `_v3_visit_<节点名>`，未覆盖走 `_v3_visit_unknown`。"""
        if node is None or not _is_v3_node(node):
            # 兜底：非 v3 节点绝不喂给 unified 的 visit_*（两套 visit 方法空间不同）
            return None
        method = getattr(self, '_v3_visit_' + type(node).__name__, None)
        if method is None:
            method = self._v3_visit_unknown
        return method(node)

    def _v3_visit_seq(self, nodes: Any) -> None:
        """按序分析语句序列。

        注意：v3 的 `then_body` / `else_body` / `body` 有时是**单个节点**而非
        列表（嵌套 `如果` 等场景），故这里对非序列入参按单节点处理——
        早期版本直接 `for` 会抛 `TypeError: 'IfStmt' object is not iterable`。
        """
        if nodes is None:
            return
        if isinstance(nodes, (list, tuple)):
            for item in nodes:
                self._v3_dispatch(item)
            return
        self._v3_dispatch(nodes)

    def _v3_dispatch_child(self, value: Any) -> None:
        """递归遍历子节点（列表/字典/单节点），只处理 v3 节点。"""
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                self._v3_dispatch_child(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                self._v3_dispatch_child(item)
            return
        if _is_v3_node(value):
            self._v3_dispatch(value)

    def _v3_visit_unknown(self, node: Any):
        """未覆盖的 v3 节点：不报错，仅保守递归子节点。

        覆盖度统计见 `_r135_scratch/v3_coverage.txt`；本方法存在保证
        「新增 v3 节点不会让语义分析抛异常」。
        """
        for slot in getattr(type(node), '__slots__', ()):
            self._v3_dispatch_child(getattr(node, slot, None))
        return None

    # ---- 语句 --------------------------------------------------------
    def _v3_visit_module(self, node: Any):
        """v3 Module：`statements` 即全局作用域的语句序列。

        先做一次**声明提升**：光明允许在定义之前调用段落/类/导入名
        （bootstrap/ 与 stdlib/ 大量依赖），若不提升会整片误报未定义。
        """
        statements = getattr(node, 'statements', None)
        self._v3_hoist(statements)
        self._v3_visit_seq(statements)

    # 可在使用前被引用的顶层声明
    _V3_HOIST_KINDS = frozenset({
        'Paragraph', 'ClassDefinition', 'RecordDefinition', 'InterfaceDefinition',
        'FFIFunctionDecl', 'FFIVarArgsDecl', 'EnumDefinition',
    })

    def _v3_hoist(self, statements: Any) -> None:
        """声明提升：把段落/类/导入名先登记进当前作用域。"""
        if statements is None:
            return
        if not isinstance(statements, (list, tuple)):
            statements = [statements]
        for stmt in statements:
            if not _is_v3_node(stmt):
                continue
            kind = type(stmt).__name__
            if kind == 'ImportStmt':
                self._v3_visit_ImportStmt(stmt)
            elif kind == 'DecoratedFunction':
                inner = getattr(stmt, 'function', None)
                if _is_v3_node(inner) and getattr(inner, 'name', None):
                    self._v3_declare(inner.name, TYPE_ANY, inner, is_mutable=False)
            elif kind in self._V3_HOIST_KINDS:
                nm = getattr(stmt, 'name', None)
                if nm:
                    self._v3_declare(nm, TYPE_ANY, stmt, is_mutable=False)

    def _v3_visit_VarDecl(self, node: Any):
        """v3 变量声明。`设`/`令`/重绑定都产出 VarDecl。

        v3 口径：重复声明 = 重绑定，不报重复定义。
        """
        if getattr(node, 'value', None) is not None:
            self._v3_use(node.value)
        annotation = getattr(node, 'type_annotation', None)
        name = getattr(node, 'name', None)
        if name:
            self._v3_declare(name, self._type_from_annotation(annotation) or TYPE_ANY,
                             node, is_mutable=not getattr(node, 'block_scoped', False))
        return None

    def _v3_visit_Paragraph(self, node: Any):
        """v3 段落定义 = 函数定义：登记函数名，参数进新作用域。"""
        name = getattr(node, 'name', None)
        if name:
            self._v3_declare(name, TYPE_ANY, node, is_mutable=False)
        self._v3_new_scope()
        for param in getattr(node, 'params', None) or []:
            p_name, p_type = self._v3_param_of(param)
            if p_name:
                self._v3_declare(p_name, self._type_from_annotation(p_type) or TYPE_ANY, node)
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_ParagraphCall(self, node: Any):
        """v3 段落/内置调用：实参照常分析；被调名走统一判定入口。"""
        name = getattr(node, 'name', None)
        for arg in getattr(node, 'args', None) or []:
            self._v3_dispatch(arg)
        if not self._v3_is_resolvable(name):
            self.add_error(f"未定义的符号 '{name}'", node)
        return None

    def _v3_visit_FunctionCallExpr(self, node: Any):
        """v3 计算型调用 `x[i]()` / `a.b()`（callee 是表达式而非名字）。"""
        self._v3_dispatch_child(getattr(node, 'callee', None))
        for arg in getattr(node, 'args', None) or []:
            self._v3_dispatch(arg)
        return None

    def _v3_visit_IfStmt(self, node: Any):
        self._v3_use(getattr(node, 'condition', None))
        self._v3_new_scope()
        self._v3_visit_seq(getattr(node, 'then_body', None))
        self._v3_pop_scope()
        else_body = getattr(node, 'else_body', None)
        if else_body:
            self._v3_new_scope()
            self._v3_visit_seq(else_body)
            self._v3_pop_scope()
        return None

    def _v3_visit_WhileStmt(self, node: Any):
        self._v3_use(getattr(node, 'condition', None))
        self._v3_new_scope()
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_ForeachStmt(self, node: Any):
        self._v3_use(getattr(node, 'iterable', None))
        self._v3_new_scope()
        variable = getattr(node, 'variable', None)
        if variable:
            self._v3_declare(variable, TYPE_ANY, node, is_mutable=True)
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_ReturnStmt(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_ThrowStmt(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        self._v3_use(getattr(node, 'from_expr', None))
        return None

    def _v3_visit_AssertStmt(self, node: Any):
        self._v3_use(getattr(node, 'condition', None))
        self._v3_use(getattr(node, 'message', None))
        return None

    def _v3_visit_Assignment(self, node: Any):
        self._v3_use(getattr(node, 'target', None))
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_IndexedAssignment(self, node: Any):
        self._v3_use(getattr(node, 'target', None))
        self._v3_use(getattr(node, 'index', None))
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_IndexedCompoundAssignment(self, node: Any):
        self._v3_use(getattr(node, 'target', None))
        self._v3_use(getattr(node, 'index', None))
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_CompoundAssignment(self, node: Any):
        self._v3_use(getattr(node, 'target', None))
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_SelfAssignment(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_TryStmt(self, node: Any):
        self._v3_visit_seq(getattr(node, 'try_body', None))
        clauses = getattr(node, 'catch_clauses', None) or []
        for clause in clauses:
            self._v3_new_scope()
            var = getattr(clause, 'catch_var', None)
            if var:
                self._v3_declare(var, TYPE_ANY, clause, is_mutable=True)
            self._v3_visit_seq(getattr(clause, 'catch_body', None))
            self._v3_pop_scope()
        if not clauses:
            # 兼容 catch_var / catch_body 直挂形态
            var = getattr(node, 'catch_var', None)
            if var:
                self._v3_new_scope()
                self._v3_declare(var, TYPE_ANY, node, is_mutable=True)
            self._v3_visit_seq(getattr(node, 'catch_body', None))
            if var:
                self._v3_pop_scope()
        self._v3_visit_seq(getattr(node, 'finally_body', None))
        self._v3_visit_seq(getattr(node, 'else_body', None))
        return None

    def _v3_visit_MatchStmt(self, node: Any):
        self._v3_use(getattr(node, 'subject', None))
        for case in getattr(node, 'cases', None) or []:
            self._v3_new_scope()
            self._v3_bind_pattern(getattr(case, 'pattern', None), case)
            self._v3_use(getattr(case, 'guard', None))
            self._v3_visit_seq(getattr(case, 'body', None))
            self._v3_pop_scope()
        return None

    def _v3_visit_DecoratedFunction(self, node: Any):
        self._v3_dispatch_child(getattr(node, 'function', None))
        return None

    def _v3_visit_LambdaExpression(self, node: Any):
        self._v3_new_scope()
        for param in getattr(node, 'params', None) or []:
            p_name, _p_type = self._v3_param_of(param)
            if p_name:
                self._v3_declare(p_name, TYPE_ANY, node)
        self._v3_use(getattr(node, 'body', None))
        self._v3_visit_seq(getattr(node, 'body_statements', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_WithStmt(self, node: Any):
        self._v3_use(getattr(node, 'context_expr', None))
        for item in getattr(node, 'items', None) or []:
            self._v3_dispatch_child(item)
        self._v3_new_scope()
        var = getattr(node, 'variable', None)
        if var:
            self._v3_declare(var, TYPE_ANY, node, is_mutable=True)
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_WithCloseStmt(self, node: Any):
        self._v3_dispatch_child(getattr(node, 'items', None))
        self._v3_new_scope()
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_DestructuringAssignment(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        self._v3_new_scope()
        for name in getattr(node, 'variables', None) or []:
            if isinstance(name, str) and name:
                self._v3_declare(name, TYPE_ANY, node, is_mutable=True)
        self._v3_pop_scope()
        return None

    def _v3_visit_ImportStmt(self, node: Any):
        """导入进来的名字视为已绑定（不细究来源）。

        只登记**显式符号表**（`从 数学 导入 求和`）。像 `导入 token` 这种不带
        符号表的写法，被导入的名字来源不可知（模块可能在别的文件里定义），
        此时置 `_v3_has_opaque_import`，让后续未定义判定整体放宽——否则
        `bootstrap/parser.light`（依赖 `token` / `light_ast`）会误报几十条。
        """
        symbols = getattr(node, 'symbols', None)
        if symbols:
            for name in symbols:
                if isinstance(name, str) and name and name.isidentifier():
                    self._v3_declare(name, TYPE_ANY, node)
        else:
            self._v3_has_opaque_import = True
        for slot in ('alias',):
            alias = getattr(node, slot, None)
            if isinstance(alias, str) and alias.isidentifier():
                self._v3_declare(alias, TYPE_ANY, node)
        return None

    # ---- 表达式 ------------------------------------------------------
    def _v3_visit_BinaryOp(self, node: Any):
        self._v3_use(getattr(node, 'left', None))
        self._v3_use(getattr(node, 'right', None))
        return None

    def _v3_visit_UnaryOp(self, node: Any):
        self._v3_use(getattr(node, 'operand', None))
        return None

    def _v3_visit_Identifier(self, node: Any):
        self._v3_check_identifier(node)
        return None

    def _v3_visit_MemberAccess(self, node: Any):
        """成员访问：obj 是符号引用，member 是属性名（不查符号）。"""
        self._v3_use(getattr(node, 'obj', None))
        for arg in getattr(node, 'args', None) or []:
            self._v3_dispatch(arg)
        return None

    def _v3_visit_IndexAccess(self, node: Any):
        self._v3_use(getattr(node, 'obj', None))
        self._v3_use(getattr(node, 'index', None))
        return None

    def _v3_visit_SliceExpr(self, node: Any):
        self._v3_use(getattr(node, 'start', None))
        self._v3_use(getattr(node, 'stop', None))
        self._v3_use(getattr(node, 'step', None))
        return None

    def _v3_visit_Pipeline(self, node: Any):
        self._v3_visit_seq(getattr(node, 'stages', None))
        return None

    def _v3_visit_ListLiteral(self, node: Any):
        self._v3_visit_seq(getattr(node, 'elements', None))
        return None

    # 元组/集合字面量的字段名同为 `elements`
    _v3_visit_TupleLiteral = _v3_visit_ListLiteral
    _v3_visit_SetLiteral = _v3_visit_ListLiteral

    def _v3_visit_DictLiteral(self, node: Any):
        self._v3_dispatch_child(getattr(node, 'entries', None))
        return None

    def _v3_visit_ClassInstantiation(self, node: Any):
        for arg in getattr(node, 'args', None) or []:
            self._v3_dispatch(arg)
        return None

    # ---- 类 / 方法 / `己` -------------------------------------------
    def _v3_visit_ClassDefinition(self, node: Any):
        """v3 类定义。

        v3 的类体是**另一套作用域模型**：属性（`性 X`）与 `己X` / `己.X`
        声明出来的实例属性，在本类的方法里可直接裸名引用。适配层用一个
        「类作用域」承载这些名字，避免类内合法引用被误报成未定义。
        """
        name = getattr(node, 'name', None)
        if name:
            self._v3_declare(name, TYPE_ANY, node, is_mutable=False)

        self._v3_new_scope()
        self._v3_class_scopes.append(self.current_scope_id)

        # 属性声明与父类名先入类作用域
        for attr in getattr(node, 'attributes', None) or []:
            a_name = getattr(attr, 'name', None)
            if a_name:
                self._v3_declare(a_name, TYPE_ANY, attr, is_mutable=True)
        for base in getattr(node, 'base_classes', None) or []:
            self._v3_use(base)

        # 方法体内的 `己X` 会登记到「最近的类作用域」
        self._v3_method_scope_depth = getattr(self, '_v3_method_scope_depth', 0)
        for method in getattr(node, 'methods', None) or []:
            self._v3_dispatch(method)

        self._v3_class_scopes.pop()
        self._v3_pop_scope()
        return None

    def _v3_visit_MethodDefinition(self, node: Any):
        """v3 类方法：参数 + `己` + 方法体内的 `己X` 一起登记。"""
        self._v3_new_scope()
        self._v3_declare('己', TYPE_ANY, node, is_mutable=False)
        self._v3_declare('self', TYPE_ANY, node, is_mutable=False)
        for param in getattr(node, 'parameters', None) or []:
            p_name, p_type = self._v3_param_of(param)
            if p_name:
                self._v3_declare(p_name, self._type_from_annotation(p_type) or TYPE_ANY, node)
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_MethodSignature(self, node: Any):
        self._v3_new_scope()
        self._v3_declare('己', TYPE_ANY, node, is_mutable=False)
        self._v3_declare('self', TYPE_ANY, node, is_mutable=False)
        for param in getattr(node, 'parameters', None) or []:
            p_name, p_type = self._v3_param_of(param)
            if p_name:
                self._v3_declare(p_name, self._type_from_annotation(p_type) or TYPE_ANY, node)
        self._v3_visit_seq(getattr(node, 'body', None))
        self._v3_pop_scope()
        return None

    def _v3_visit_AttributeDeclaration(self, node: Any):
        """类属性声明：落类作用域（供方法内裸名引用）。"""
        name = getattr(node, 'name', None)
        target = self._v3_class_scopes[-1] if self._v3_class_scopes else self.current_scope_id
        if name:
            self.scopes.setdefault(target, {})[name] = Symbol(
                name=name, type=TYPE_ANY, scope_id=target, is_mutable=True)
        self._v3_use(getattr(node, 'default_value', None))
        return None

    def _v3_visit_SelfAssignment(self, node: Any):
        """`己X 为 V` / `己.X 为 V`：把属性名登记进类作用域。"""
        attr = getattr(node, 'attr_name', None)
        if attr:
            target = self._v3_class_scopes[-1] if self._v3_class_scopes else self.current_scope_id
            self.scopes.setdefault(target, {})[attr] = Symbol(
                name=attr, type=TYPE_ANY, scope_id=target, is_mutable=True)
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_InterfaceDefinition(self, node: Any):
        self._v3_dispatch_child(getattr(node, 'methods', None))
        self._v3_dispatch_child(getattr(node, 'properties', None))
        return None

    # ---- 杂项：与 unified 路径无对应概念，显式登记为「已覆盖、不约束」 -----
    def _v3_visit_ExportStmt(self, node: Any):
        """`导出 名字`：不引入新符号，不约束。"""
        return None

    def _v3_visit_PassStmt(self, node: Any):
        return None

    def _v3_visit_BreakStmt(self, node: Any):
        return None

    def _v3_visit_ContinueStmt(self, node: Any):
        return None

    def _v3_visit_NumberLiteral(self, node: Any):
        return None

    def _v3_visit_StringLiteral(self, node: Any):
        return None

    def _v3_visit_BooleanLiteral(self, node: Any):
        return None

    def _v3_visit_CharLiteral(self, node: Any):
        return None

    def _v3_visit_TypeAnnotation(self, node: Any):
        return None

    def _v3_visit_Parameter(self, node: Any):
        return None

    def _v3_visit_ParameterList(self, node: Any):
        return None

    def _v3_visit_KeywordArg(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_ConditionalExpression(self, node: Any):
        self._v3_use(getattr(node, 'condition', None))
        self._v3_use(getattr(node, 'then_expr', None))
        self._v3_use(getattr(node, 'else_expr', None))
        return None

    def _v3_visit_StringInterpolation(self, node: Any):
        for part in getattr(node, 'parts', None) or []:
            self._v3_use(part)
        return None

    def _v3_visit_YieldStmt(self, node: Any):
        self._v3_use(getattr(node, 'value', None))
        return None

    def _v3_visit_AwaitExpr(self, node: Any):
        self._v3_use(getattr(node, 'expression', None))
        return None

    def _v3_visit_RunAsyncStmt(self, node: Any):
        self._v3_use(getattr(node, 'call', None))
        return None

    def _v3_visit_RangeExpr(self, node: Any):
        self._v3_use(getattr(node, 'start', None))
        self._v3_use(getattr(node, 'end', None))
        self._v3_use(getattr(node, 'step', None))
        return None

    def _v3_visit_ScopeDeclStmt(self, node: Any):
        """`全局 计数。` / `外层 值。`：把已有符号按声明向上提。

        实现：`全局` 把名字复制到全局作用域；`外层` 把名字登记到**上一级**
        作用域。只对已在符号表中的名字生效，避免凭空造符号。
        """
        kind = getattr(node, 'kind', None)
        names = getattr(node, 'names', None) or []
        if isinstance(names, str):
            names = [names]
        for name in names:
            if not (isinstance(name, str) and name):
                continue
            if kind == 'global':
                found = self._v3_lookup(name)
                self.scopes.setdefault(1, {})[name] = found or Symbol(
                    name=name, type=TYPE_ANY, scope_id=1, is_mutable=True)
            elif kind in ('outer', 'nonlocal') and len(self._scope_stack) >= 2:
                outer = self._scope_stack[-2]
                found = self._v3_lookup(name)
                self.scopes.setdefault(outer, {})[name] = found or Symbol(
                    name=name, type=TYPE_ANY, scope_id=outer, is_mutable=True)
        return None

    def _v3_visit_FFILoadLibrary(self, node: Any):
        return None

    def _v3_visit_FFIFunctionDecl(self, node: Any):
        name = getattr(node, 'name', None)
        if name:
            self._v3_declare(name, TYPE_ANY, node, is_mutable=False)
        return None

    def _v3_visit_FFIVarArgsDecl(self, node: Any):
        return self._v3_visit_FFIFunctionDecl(node)

    def _v3_visit_FFIStructDef(self, node: Any):
        name = getattr(node, 'name', None)
        if name:
            self._v3_declare(name, TYPE_ANY, node, is_mutable=False)
        return None

    def _v3_visit_FFIEnumDef(self, node: Any):
        return self._v3_visit_FFIStructDef(node)

    def _v3_visit_FFIUnionDef(self, node: Any):
        return self._v3_visit_FFIStructDef(node)

    def _v3_visit_FFITypedefDef(self, node: Any):
        return self._v3_visit_FFIStructDef(node)

    def _v3_visit_FFICallbackDef(self, node: Any):
        return self._v3_visit_FFIStructDef(node)

    def _v3_visit_EmbedBlock(self, node: Any):
        """`引 Python:` / `引 模式 日期:` 嵌入块。

        v3 把这些块编译成 Python 源码，其中定义的/导出的名字对**后续光明代码
        可见**（`引 Python: ... result = math.sqrt(16)` 之后 `出 result`）。
        注意 `language` 里可能带修饰词（`模式 日期`），末段才是引入的名字。
        """
        language = (getattr(node, 'language', None) or '').strip()
        parts = language.split()
        if parts and parts[-1] not in ('Python', 'C', 'Go', 'MoonBit', 'Rust',
                                       'JavaScript', 'JS', 'Shell'):
            alias = parts[-1]
            if alias.isidentifier():
                self._v3_declare(alias, TYPE_ANY, node, is_mutable=False)

        for bucket in ('exports', 'imports'):
            value = getattr(node, bucket, None)
            for name in (value or []):
                if isinstance(name, str) and name and name.isidentifier():
                    self._v3_declare(name, TYPE_ANY, node, is_mutable=False)

        # 嵌入代码里 `名 = 值` / `def 名` 定义的名字
        code = getattr(node, 'code', None)
        if isinstance(code, str):
            for raw in code.splitlines():
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('def ') and '(' in line:
                    name = line[4:line.index('(')].strip()
                elif '=' in line and '==' not in line:
                    name = line.split('=', 1)[0].strip()
                else:
                    continue
                if name.isidentifier():
                    self._v3_declare(name, TYPE_ANY, node, is_mutable=True)
        return None

    def _v3_visit_RecordDefinition(self, node: Any):
        self._v3_visit_ClassDefinition(node)
        self._v3_dispatch_child(getattr(node, 'fields', None))
        return None

    # ---- v3 小工具 ---------------------------------------------------
    def _v3_param_of(self, param: Any) -> Tuple[Optional[str], Optional[str]]:
        """段落/匿名函数的参数既可能是 dict，也可能是 v3 Parameter 节点。"""
        if isinstance(param, dict):
            return param.get('name'), param.get('type')
        if isinstance(param, str):
            return param, None
        return getattr(param, 'name', None), getattr(param, 'type_annotation', None)

    def _v3_bind_pattern(self, pattern: Any, node: Any) -> None:
        """匹配模式里的绑定名（`情况 名字：`）登记进当前作用域。"""
        binding = getattr(pattern, 'binding', None)
        if binding:
            self._v3_declare(binding, TYPE_ANY, node, is_mutable=True)

    def _v3_use(self, expr: Any) -> None:
        """把表达式当作“被使用”处理：标识符查符号，其余按需递归。"""
        if expr is None:
            return
        if _is_v3_node(expr):
            if type(expr).__name__ == 'Identifier':
                self._v3_check_identifier(expr)
            else:
                self._v3_dispatch(expr)
            return
        self._v3_dispatch_child(expr)

    def _v3_check_identifier(self, node: Any) -> None:
        """标识符：已知可调用名/字面量跳过，其余必须已在符号表中。

        `X的Y` 链（`宠物的长度`）在 v3 里是**一个整体 Identifier**：`的` 作为
        后缀成员访问符时只在 `_is_paren_dict_key` 上留痕，没有结构化节点。
        这类名字按「成员链」处理——对象侧可见即放行，否则 examples/L1_baihua
        这类合法代码会被大面积误报（实测）。
        """
        name = getattr(node, 'name', None)
        if not self._v3_is_resolvable(name):
            self.add_error(f"未定义的符号 '{name}'", node)

    def _v3_is_resolvable(self, name: Optional[str]) -> bool:
        """名字是否可解析。

        **唯一**的「未定义」判定入口——`_v3_check_identifier`（标识符引用）与
        `_v3_visit_ParagraphCall`（被调名）都必须走这里，否则两条路径的口径会
        漂移（早期版本正是如此：调用路径漏判「来源不可知导入」，导致
        `bootstrap/parser.light` 误报 55 条 `make_binary_op`）。
        """
        if not name:
            return True
        if name in _V3_LITERAL_NAMES:
            return True
        if name.endswith('()'):
            # v3 把 `super()` 这类形态当成**一个标识符**（字面带括号），
            # 不是调用节点 —— 按内建调用处理，不报未定义。
            return True
        if _is_known_callable(name):
            return True
        if self._v3_lookup(name) is not None:
            return True
        if self._v3_is_instance_attr(name):
            return True
        if self._v3_is_member_chain(name):
            return True
        # 文件里有「来源不可知」的导入（`导入 X` 不带符号表）时，
        # 无法判定该名字是否来自被导入模块 → 一律放行，避免大面积误报。
        return bool(self._v3_has_opaque_import)

    def _v3_is_instance_attr(self, name: str) -> bool:
        """`己X` / `己.X` 实例属性引用。

        v3 把 `己名称` 解析成**单个 Identifier**（`己` 只是前缀），没有结构化
        成员节点，方法体内的实例属性因此无法用符号表核验 → 按属性引用放行。
        """
        if name.startswith('己'):
            return True
        return name == 'self' or name.startswith('self.')

    def _v3_is_member_chain(self, name: str) -> bool:
        """`A的B` / `A.B` 成员访问链：对象侧可见即放行。"""
        for sep in ('的', '.'):
            if sep in name:
                head = name.split(sep, 1)[0]
                if not head:
                    return True
                if head in _V3_LITERAL_NAMES or _is_known_callable(head):
                    return True
                return self._v3_lookup(head) is not None
        return False

    def _type_from_annotation(self, annotation: Optional[str]) -> Optional[Type]:
        """v3 中文类型注解 → 统一类型标签。未知注解归入 `任意`。"""
        if not annotation:
            return None
        key = str(annotation).strip()
        if key in ('数', '整数', '浮数', '浮点', '小数'):
            return TYPE_NUMBER
        if key in ('串', '文本', '字符串'):
            return TYPE_STRING
        if key in ('布尔', '真值'):
            return TYPE_BOOL
        return TYPE_ANY

    def analyze(self) -> List[SemanticError]:
        """执行语义分析"""
        self.visit(self.module)
        return self.errors
