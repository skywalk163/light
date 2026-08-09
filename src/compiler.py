"""
光明（Light）编程语言 - 统一编译器管道

完整链路：  源码 → 词法分析 → 语法解析 → AST 适配 → 类型检查
          (source)  (Lexer)   (LightParser)  (Adapter)  (TypeInferencer)

这是连接前端解析器与后端类型系统的桥梁。
"""

from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import os
import traceback

from lexer import Lexer, LexerError
from tokens import Token, TokenType
from keywords import VERB_ARITY
from light_parser_v3 import LightParser, ParseError
import ast_nodes as ast
import ast_nodes_v3 as v3_ast
from optimizer import (
    DeadCodeEliminationOptimizer,
    ConstantFoldingOptimizer,
    LoopInvariantOptimizer,
)
from errors import LightError, LightErrorFormatter, format_source_context, format_error_with_context

# 导入编译缓存系统
try:
    from compiler_cache import CompilationCache
    _HAS_CACHE = True
except ImportError:
    _HAS_CACHE = False
    CompilationCache = None

OPTIMIZERS = [
    DeadCodeEliminationOptimizer,
    ConstantFoldingOptimizer,
    LoopInvariantOptimizer,
]

# L3 领域嵌入模块注册表
# 每个模块通过 `引 Python:` 语法在 .light 文件中导入使用
L3_MODULES = {
    'l3_echarts': {
        'module': 'l3_echarts',
        'class': 'L3ECharts',
        'description': 'ECharts 可视化 DSL（柱状图/折线图/饼图/散点图）',
    },
    'l3_markdown': {
        'module': 'l3_markdown',
        'class': 'L3Markdown',
        'description': 'Markdown 文档生成 DSL（标题/段落/列表/表格/代码块）',
    },
}

# FFI 模块注册表
# 通过 `引 Python:` 语法在 .light 文件中导入使用
FFI_MODULES = {
    'ffi_go': {
        'module': 'ffi_go',
        'class': 'GoFFI',
        'description': 'Go FFI 绑定（引用Go库/绑定函数/类型转换）',
    },
    'ffi_rust': {
        'module': 'ffi_rust',
        'class': 'RustFFI',
        'description': 'Rust FFI 绑定（引用Rust库/绑定函数/字符串处理）',
    },
}


_compile_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_compilation_cache_instance = None


def _get_cache() -> Optional[Any]:
    """获取或创建全局编译缓存实例"""
    global _compilation_cache_instance
    if _compilation_cache_instance is None and _HAS_CACHE:
        _compilation_cache_instance = CompilationCache()
    return _compilation_cache_instance


# =============================================================================
# AST 适配器：v3 AST → 我们的 ast_nodes 格式
# =============================================================================

class AstAdapter:
    """将 `ast_nodes_v3` 节点转换为 `ast_nodes.py` 节点

    现有 LightParser v3 输出 ast_nodes_v3 的节点，这些节点使用 __slots__
    的普通类设计。而我们的类型系统基于 ast_nodes.py（dataclass 设计）。
    本适配器在两者之间提供无损转换。
    """

    def __init__(self):
        self._node_converters = {
            'Module': self._convert_module,
            'VarDecl': self._convert_var_decl,
            'Paragraph': self._convert_paragraph,
            'ParagraphCall': self._convert_paragraph_call,
            'NumberLiteral': self._convert_number_literal,
            'StringLiteral': self._convert_string_literal,
            'BooleanLiteral': self._convert_boolean_literal,
            'Identifier': self._convert_identifier,
            'BinaryOp': self._convert_binary_op,
            'IfStmt': self._convert_if_stmt,
            'ForeachStmt': self._convert_foreach_stmt,
            'WhileStmt': self._convert_while_stmt,
            'ReturnStmt': self._convert_return_stmt,
            'BreakStmt': self._convert_break_stmt,
            'ContinueStmt': self._convert_continue_stmt,
            'ClassDefinition': self._convert_class_definition,
            'ClassInstantiation': self._convert_class_instantiation,
            'MethodDefinition': self._convert_method_definition,
            'AttributeDeclaration': self._convert_attribute_declaration,
            'ListLiteral': self._convert_list_literal,
            'MemberAccess': self._convert_member_access,
            'IndexAccess': self._convert_index_access,
            'CompoundAssignment': self._convert_compound_assignment,
            'SelfAssignment': self._convert_self_assignment,
            'Assignment': self._convert_assignment,
            'IndexedAssignment': self._convert_indexed_assignment,
            'Parameter': self._convert_parameter,
            'ImportStmt': self._convert_import_stmt,
            'ExportStmt': self._convert_export_stmt,
            'ConditionalExpression': self._convert_conditional_expression,
            'ListComprehension': self._convert_list_comprehension,
            'Pipeline': self._convert_pipeline,
            'TryStmt': self._convert_try_stmt,
            'ThrowStmt': self._convert_throw_stmt,
            'StringInterpolation': self._convert_string_interpolation,
            'InterfaceDefinition': self._convert_interface_definition,
            'MethodSignature': self._convert_method_signature,
            'DestructuringAssignment': self._convert_destructure_assignment,
            'WithStmt': self._convert_with_stmt,
            'DictLiteral': self._convert_dict_literal,
            'DictComprehension': self._convert_dict_comprehension,
            'MatchStmt': self._convert_match_stmt,
            'MatchCase': self._convert_match_case,
            'LambdaExpression': self._convert_lambda_expression,
            'UnwrapExpression': self._convert_unwrap_expression,
            'RangeExpr': self._convert_range_expr,
            'AwaitExpr': self._convert_await_expr,
            'AsyncScope': self._convert_async_scope,
        }

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def convert(self, node) -> ast.ASTNode:
        """将 v3 AST 节点转换为 ast_nodes 格式"""
        if node is None:
            return None

        type_name = type(node).__name__
        converter = self._node_converters.get(type_name)

        if converter is None:
            # 未知节点类型：包装为通用表达式语句
            return ast.ExpressionStatement(expression=ast.Identifier(name=f"<unknown:{type_name}>"))

        return converter(node)

    def convert_module(self, node) -> ast.Module:
        """将 v3 Module 转换为我们的 Module 格式"""
        return self._convert_module(node)

    # ------------------------------------------------------------------
    # 辅助函数
    # ------------------------------------------------------------------
    def _convert_list(self, items) -> List[ast.ASTNode]:
        """递归转换节点列表"""
        if items is None:
            return []
        return [self.convert(item) for item in items]

    def _to_list_stmts(self, items) -> List[ast.ASTNode]:
        """v3 语句转换（确保每个项目都是独立语句）"""
        if not items:
            return []
        result = []
        for item in items:
            if item is None:
                continue
            converted = self.convert(item)
            # 表达式需要包装为 ExpressionStatement
            if not isinstance(converted, (
                ast.VariableDeclaration, ast.Assignment, ast.IfStatement,
                ast.WhileStatement, ast.ForeachStatement,
                ast.ReturnStatement, ast.BreakStatement, ast.ContinueStatement,
                ast.ExpressionStatement, ast.SegmentDefinition, ast.ClassDefinition,
                ast.InterfaceDefinition, ast.TryStatement, ast.ThrowStatement,
                ast.WithStatement, ast.MatchStatement, ast.DestructuringAssignment,
                ast.ImportStatement, ast.ExportStatement, ast.CompoundAssignment,
                ast.AsyncScope,
            )):
                converted = ast.ExpressionStatement(expression=converted)
            result.append(converted)
        return result

    # ------------------------------------------------------------------
    # 节点转换器
    # ------------------------------------------------------------------
    def _convert_module(self, node) -> ast.Module:
        segments = []
        classes = []
        interfaces = []
        statements = []
        imports = []
        exports = []

        other_stmts = []
        for stmt in node.statements or []:
            converted = self.convert(stmt)
            if isinstance(converted, ast.SegmentDefinition):
                segments.append(converted)
            elif isinstance(converted, ast.ClassDefinition):
                classes.append(converted)
            elif isinstance(converted, ast.InterfaceDefinition):
                interfaces.append(converted)
            elif isinstance(converted, ast.ImportStatement):
                imports.append(converted)
            elif isinstance(converted, ast.ExportStatement):
                exports.append(converted)
            else:
                other_stmts.append(stmt)

        statements = self._to_list_stmts(other_stmts)

        return ast.Module(
            name=None,
            imports=imports,
            exports=exports,
            segments=segments,
            classes=classes,
            interfaces=interfaces,
            data_types=[],
            error_types=[],
            statements=statements,
            enums=[],
            trait_defs=[],
            trait_impls=[],
            type_aliases=[],
        )

    def _convert_var_decl(self, node) -> ast.VariableDeclaration:
        val = self.convert(node.value) if node.value else None
        return ast.VariableDeclaration(
            name=node.name,
            value=val,
            type_annotation=getattr(node, 'type_annotation', None),
            is_mutable=True,
            destructure_names=[],
        )

    def _convert_paragraph(self, node) -> ast.SegmentDefinition:
        params = []
        for p in node.params:
            if isinstance(p, dict):
                params.append(ast.Parameter(
                    name=p.get('name', 'x'),
                    type_annotation=p.get('type'),
                ))
            elif isinstance(p, v3_ast.Parameter):
                params.append(ast.Parameter(
                    name=p.name,
                    type_annotation=getattr(p, 'type_annotation', None),
                ))
            else:
                params.append(ast.Parameter(name=str(p)))

        return ast.SegmentDefinition(
            name=node.name,
            parameters=params,
            body=self._to_list_stmts(node.body),
            return_type=getattr(node, 'return_type', None),
            modifiers=list(getattr(node, 'modifiers', []) or []),
            generic_params=list(getattr(node, 'generic_params', []) or []),
        )

    def _convert_paragraph_call(self, node) -> ast.FunctionCall:
        args = self._convert_list(node.args)
        return ast.FunctionCall(
            name=ast.SegmentName(name=node.name) if hasattr(ast, 'SegmentName')
                else ast.Identifier(name=node.name),
            arguments=args,
            type_args=[],
        )

    def _convert_number_literal(self, node) -> ast.NumberLiteral:
        return ast.NumberLiteral(value=float(node.value) if '.' in str(node.value)
                                 else int(node.value))

    def _convert_string_literal(self, node) -> ast.StringLiteral:
        return ast.StringLiteral(value=str(node.value))

    def _convert_boolean_literal(self, node) -> ast.BooleanLiteral:
        if isinstance(node.value, bool):
            val = node.value
        else:
            val = str(node.value).lower() in ('true', '是', '真', '对')
        return ast.BooleanLiteral(value=val)

    def _convert_identifier(self, node) -> ast.Identifier:
        return ast.Identifier(name=node.name)

    def _convert_binary_op(self, node) -> ast.BinaryOp:
        return ast.BinaryOp(
            operator=str(node.operator),
            left=self.convert(node.left),
            right=self.convert(node.right),
        )

    def _convert_if_stmt(self, node) -> ast.IfStatement:
        # 处理 elif 链：else_body 可能是一个 IfStmt 对象
        elseif_conditions = []
        elseif_bodies = []
        else_body = None
        
        current_else = node.else_body
        while current_else is not None:
            # 检查是不是 IfStmt（elif 链）
            if type(current_else).__name__ == 'IfStmt':
                # 这是一个 elif 分支
                elseif_conditions.append(self.convert(current_else.condition))
                elseif_bodies.append(self._to_list_stmts(current_else.then_body))
                current_else = current_else.else_body
            else:
                # 这是最终的 else 体（语句列表）
                else_body = self._to_list_stmts(current_else)
                break
        
        return ast.IfStatement(
            condition=self.convert(node.condition),
            then_body=self._to_list_stmts(node.then_body),
            else_body=else_body,
            elseif_conditions=elseif_conditions,
            elseif_bodies=elseif_bodies,
        )

    def _convert_foreach_stmt(self, node) -> ast.ForeachStatement:
        return ast.ForeachStatement(
            variable=node.variable,
            iterable=self.convert(node.iterable),
            body=self._to_list_stmts(node.body),
        )

    def _convert_range_expr(self, node) -> ast.ASTNode:
        """将 v3 RangeExpr 转换为 FunctionCall(范围, start, end)"""
        start = self.convert(node.start)
        end = self.convert(node.end)
        args = [start]
        if end is not None:
            args.append(end)
        if node.step is not None and node.step != 1:
            args.append(self.convert(node.step))
        return ast.FunctionCall(
            name=ast.Identifier(name='范围'),
            arguments=args,
            column=0,
            line=0,
        )
    
    def _convert_await_expr(self, node) -> ast.AwaitExpression:
        """将 v3 AwaitExpr 转换为 AwaitExpression"""
        return ast.AwaitExpression(
            expression=self.convert(node.expression),
        )
    
    def _convert_async_scope(self, node) -> ast.AsyncScope:
        """将 v3 AsyncScope 转换为 AsyncScope"""
        return ast.AsyncScope(
            tasks=self._convert_list(node.tasks),
            result_vars=list(node.result_vars or []),
        )

    def _convert_while_stmt(self, node) -> ast.WhileStatement:
        return ast.WhileStatement(
            condition=self.convert(node.condition),
            body=self._to_list_stmts(node.body),
        )

    def _convert_return_stmt(self, node) -> ast.ReturnStatement:
        return ast.ReturnStatement(value=self.convert(node.value) if node.value else None)

    def _convert_break_stmt(self, node) -> ast.BreakStatement:
        return ast.BreakStatement()

    def _convert_continue_stmt(self, node) -> ast.ContinueStatement:
        return ast.ContinueStatement()

    def _convert_class_definition(self, node) -> ast.ClassDefinition:
        # 分离构造函数和方法
        constructor = None
        methods = []
        for m in node.methods:
            m_converted = self._convert_method_definition(m)
            if m_converted is None:
                continue
            if getattr(m, 'is_constructor', False) or m.name == node.name:
                # 构造函数
                constructor = ast.ConstructorDefinition(
                    name=m.name,
                    parameters=[ast.Parameter(name=p.name if hasattr(p, 'name') else str(p),
                                                type_annotation=getattr(p, 'type_annotation', None))
                                 for p in getattr(m, 'parameters', [])],
                    body=self._to_list_stmts(getattr(m, 'body', [])),
                )
            else:
                methods.append(m_converted)

        return ast.ClassDefinition(
            name=node.name,
            generic_params=list(getattr(node, 'generic_params', []) or []),
            superclasses=list(getattr(node, 'base_classes', []) or []),
            interfaces=list(getattr(node, 'interfaces', []) or []),
            fields=[
                ast.AttributeDeclaration(name=a.name,
                                         type_annotation=getattr(a, 'type_annotation', None),
                                         default_value=self.convert(getattr(a, 'default_value', None))
                                         if hasattr(a, 'default_value') and a.default_value else None)
                for a in (node.attributes or [])
            ],
            methods=methods,
            constructor=constructor,
        )

    def _convert_class_instantiation(self, node) -> ast.NewExpression:
        return ast.NewExpression(
            class_name=node.class_name,
            arguments=self._convert_list(node.args),
            type_args=[],
        )

    def _convert_method_definition(self, node) -> Optional[ast.MethodDefinition]:
        params = []
        for p in getattr(node, 'parameters', []):
            if hasattr(p, 'name'):
                params.append(ast.Parameter(
                    name=p.name,
                    type_annotation=getattr(p, 'type_annotation', None),
                ))
            elif isinstance(p, dict):
                params.append(ast.Parameter(
                    name=p.get('name', 'x'),
                    type_annotation=p.get('type'),
                ))
        return ast.MethodDefinition(
            name=node.name,
            parameters=params,
            body=self._to_list_stmts(getattr(node, 'body', [])),
            return_type=getattr(node, 'return_type', None),
            is_static=False,
            generic_params=list(getattr(node, 'generic_params', []) or []),
        )

    def _convert_attribute_declaration(self, node) -> ast.AttributeDeclaration:
        return ast.AttributeDeclaration(
            name=node.name,
            type_annotation=getattr(node, 'type_annotation', None),
            default_value=self.convert(getattr(node, 'default_value', None)) if hasattr(node, 'default_value') and node.default_value else None,
        )

    def _convert_list_literal(self, node) -> ast.ListLiteral:
        return ast.ListLiteral(elements=self._convert_list(node.elements))

    def _convert_member_access(self, node):
        if getattr(node, 'is_method_call', False) and getattr(node, 'args', None) is not None:
            return ast.FunctionCall(
                name=ast.PropertyAccess(
                    obj=self.convert(node.obj),
                    property_name=node.member,
                ),
                arguments=self._convert_list(node.args),
                type_args=[],
            )
        return ast.PropertyAccess(
            obj=self.convert(node.obj),
            property_name=node.member,
        )

    def _convert_index_access(self, node) -> ast.IndexAccess:
        return ast.IndexAccess(
            obj=self.convert(node.obj),
            index=self.convert(node.index),
        )

    def _convert_compound_assignment(self, node) -> ast.CompoundAssignment:
        return ast.CompoundAssignment(
            target=node.target,
            operator=node.operator,
            value=self.convert(node.value),
        )

    def _convert_assignment(self, node) -> ast.Assignment:
        return ast.Assignment(
            target=self.convert(node.target),
            value=self.convert(node.value),
        )

    def _convert_self_assignment(self, node) -> ast.Assignment:
        return ast.Assignment(
            target=ast.Identifier(name=f"self.{node.attr_name}"),
            value=self.convert(node.value),
        )

    def _convert_indexed_assignment(self, node) -> ast.Assignment:
        # 没有专用 IndexedAssignment → 使用 Assignment(IndexAccess 目标, 值)
        return ast.Assignment(
            target=ast.IndexAccess(obj=ast.Identifier(name=node.target),
                                    index=self.convert(node.index)),
            value=self.convert(node.value),
        )

    def _convert_parameter(self, node) -> ast.Parameter:
        return ast.Parameter(
            name=node.name,
            type_annotation=getattr(node, 'type_annotation', None),
        )

    def _convert_import_stmt(self, node) -> ast.ImportStatement:
        return ast.ImportStatement(
            module=node.module_name,
            names=getattr(node, 'symbols', []) or [],
        )

    def _convert_export_stmt(self, node) -> ast.ExportStatement:
        symbols = getattr(node, 'symbols', []) or []
        names = []
        for s in symbols:
            if isinstance(s, str):
                names.append(s)
            elif hasattr(s, 'name'):
                names.append(s.name)
            else:
                names.append(str(s) if s else '')
        names = [n for n in names if n]
        first_name = names[0] if names else ''
        return ast.ExportStatement(name=first_name, names=names)

    def _convert_conditional_expression(self, node) -> ast.ConditionalExpression:
        return ast.ConditionalExpression(
            condition=self.convert(node.condition),
            then_expr=self.convert(node.then_expr),
            else_expr=self.convert(node.else_expr) if node.else_expr else None,
        )

    def _convert_list_comprehension(self, node) -> ast.ListComprehension:
        return ast.ListComprehension(
            element=self.convert(getattr(node, 'element', node.expression)) if hasattr(node, 'element') or hasattr(node, 'expression') else ast.Identifier(name='x'),
            variable=getattr(node, 'variable', 'x'),
            iterable=self.convert(getattr(node, 'iterable', ast.Identifier(name='列表'))),
            condition=None,
        )

    def _convert_pipeline(self, node) -> ast.FunctionCall:
        """将管道操作简化为第一段的函数调用（作为语句级表达式）"""
        stages = getattr(node, 'stages', [])
        if stages:
            return ast.FunctionCall(
                name=ast.Identifier(name=f"<pipeline>"),
                arguments=[self.convert(s) for s in stages],
                type_args=[],
            )
        return ast.FunctionCall(name=ast.Identifier(name='<pipeline>'), arguments=[], type_args=[])

    def _convert_try_stmt(self, node) -> ast.TryStatement:
        catch_clauses = []
        v3_clauses = getattr(node, 'catch_clauses', [])
        if v3_clauses:
            for ct, cv, cb in v3_clauses:
                catch_clauses.append(ast.CatchClause(
                    catch_type=ct or "",
                    catch_var=cv or "",
                    catch_body=self._to_list_stmts(cb),
                ))
        
        return ast.TryStatement(
            try_body=self._to_list_stmts(getattr(node, 'try_body', [])),
            catch_clauses=catch_clauses,
            catch_var=getattr(node, 'catch_var', None) or "",
            catch_type=getattr(node, 'catch_type', None) or "",
            catch_body=self._to_list_stmts(getattr(node, 'catch_body', [])),
            finally_body=self._to_list_stmts(getattr(node, 'finally_body', [])),
        )

    def _convert_throw_stmt(self, node) -> ast.ThrowStatement:
        return ast.ThrowStatement(value=self.convert(node.value) if node.value else None)

    def _convert_string_interpolation(self, node) -> ast.StringLiteral:
        # 简化处理：直接转换为字符串字面量
        return ast.StringLiteral(value=str(getattr(node, 'value', '')))

    def _convert_interface_definition(self, node) -> ast.InterfaceDefinition:
        methods = []
        for m in getattr(node, 'methods', []):
            if hasattr(m, 'name'):
                methods.append(ast.MethodDefinition(
                    name=m.name,
                    parameters=[],
                    body=[],
                    return_type=getattr(m, 'return_type', None),
                ))
        return ast.InterfaceDefinition(
            name=node.name,
            methods=methods,
            superinterfaces=getattr(node, 'superinterfaces', []) or [],
        )

    def _convert_method_signature(self, node) -> ast.MethodDefinition:
        return ast.MethodDefinition(
            name=node.name,
            parameters=[],
            body=[],
            return_type=getattr(node, 'return_type', None),
        )

    def _convert_destructure_assignment(self, node) -> ast.DestructuringAssignment:
        names = []
        if hasattr(node, 'names'):
            names = list(node.names)
        elif hasattr(node, 'targets'):
            names = [str(t) for t in node.targets]
        return ast.DestructuringAssignment(
            names=names,
            value=self.convert(getattr(node, 'value', None)),
        )

    def _convert_with_stmt(self, node) -> ast.WithStatement:
        return ast.WithStatement(
            resource=self.convert(getattr(node, 'resource', None)),
            alias=getattr(node, 'alias', None),
            body=self._to_list_stmts(getattr(node, 'body', [])),
        )

    def _convert_dict_literal(self, node) -> ast.DictLiteral:
        return ast.DictLiteral(entries=self._convert_list(getattr(node, 'elements', [])))

    def _convert_dict_comprehension(self, node) -> ast.ListComprehension:
        # 简化：映射为列表推导式占位
        return ast.ListComprehension(
            element=self.convert(getattr(node, 'element', ast.Identifier(name='x'))),
            variable=getattr(node, 'variable', 'x'),
            iterable=self.convert(getattr(node, 'iterable', ast.Identifier(name='列表'))),
            condition=None,
        )

    def _convert_match_stmt(self, node) -> ast.MatchStatement:
        cases = []
        for c in getattr(node, 'cases', []):
            if hasattr(c, 'pattern'):
                cases.append(ast.MatchCase(
                    pattern=str(getattr(c.pattern, 'value', c.pattern)) if c.pattern else '未命名',
                    body=self._to_list_stmts(getattr(c, 'body', [])),
                ))
        return ast.MatchStatement(
            target=self.convert(getattr(node, 'target', None)),
            cases=cases,
        )

    def _convert_match_case(self, node) -> ast.MatchCase:
        return ast.MatchCase(
            pattern=str(getattr(node, 'pattern', '默认')),
            body=self._to_list_stmts(getattr(node, 'body', [])),
        )

    def _convert_lambda_expression(self, node) -> ast.LambdaExpression:
        params = []
        for p in getattr(node, 'parameters', []) or []:
            if hasattr(p, 'name'):
                params.append(ast.Parameter(name=p.name))
            else:
                params.append(ast.Parameter(name=str(p)))
        return ast.LambdaExpression(
            parameters=params,
            body=self.convert(getattr(node, 'body', None)),
        )

    def _convert_unwrap_expression(self, node) -> ast.UnwrapExpression:
        return ast.UnwrapExpression(value=self.convert(getattr(node, 'value', None)))


# =============================================================================
# LightCompiler —— 统一编译器入口
# =============================================================================

class LightCompiler:
    """光明统一编译器

    使用示例：
        compiler = LightCompiler()
        # 完整流程
        result = compiler.compile('定义甲等于三。')
        # 分步：解析 → 检查
        module = compiler.parse('定义甲等于三。')
        typed = compiler.type_check(module)
        # 查看错误
        if compiler.errors:
            print(compiler.errors)

    跨模块项目级使用：
        compiler = LightCompiler(project_root='/path/to/project')
        result = compiler.compile_project('/path/to/project')
    """

    # 光明编译器版本号
    VERSION = "1.0.0"

    def __init__(self, project_root: Optional[str] = None):
        from core.config import LightConfig
        self._lexer = Lexer()
        self._parser = LightParser()
        self._adapter = AstAdapter()
        self._inferencer = None  # 延迟初始化（会创建 TypeInferencer）
        self._config = LightConfig()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._typed_errors = []  # 结构化类型错误（携带位置信息）
        # 项目级扩展
        self.project_root: Optional[Path] = Path(project_root) if project_root else None
        # 跨模块符号缓存：module_name -> { symbol_name: symbol_info }
        self.global_module_symbols: Dict[str, Dict[str, Any]] = {}
        # 标准库模块解析器（延迟初始化）
        self._stdlib_resolver = None

    # ------------------------------------------------------------------
    # 版本信息
    # ------------------------------------------------------------------
    def version(self) -> str:
        """返回光明编译器版本号"""
        return self.VERSION

    # ------------------------------------------------------------------
    # 标准库预加载
    # ------------------------------------------------------------------
    def preload_stdlib(self):
        """预加载标准库模块，确保内置函数在编译时可用"""
        try:
            from module_resolver import ModuleResolver
            resolver = ModuleResolver(auto_load_stdlib=True)
            resolver.preload_builtins()
            self._stdlib_resolver = resolver
            # 记录标准库模块名
            stdlib_names = resolver.get_stdlib_module_names()
            if stdlib_names:
                self.warnings.append(f"已加载 {len(stdlib_names)} 个标准库模块")
        except Exception as e:
            self.warnings.append(f"标准库预加载失败: {e}")

    def _inject_stdlib_symbols(self, inferencer: Any) -> None:
        """将标准库符号注入到类型推断器的符号表中"""
        if self._stdlib_resolver is None:
            return
        if not hasattr(inferencer, "symbol_table"):
            return
        sym_table = inferencer.symbol_table
        if sym_table is None or not hasattr(sym_table, "define"):
            return
        
        # 注入内置函数符号
        stdlib_names = self._stdlib_resolver.get_stdlib_module_names()
        for name in stdlib_names:
            if name == 'builtins':
                continue
            try:
                type_val = getattr(inferencer, "type_unknown", None)
                sym_table.define(str(name), "module", type_val)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 核心入口
    # ------------------------------------------------------------------
    def compile(self, source: str, optimize: bool = True) -> Dict[str, Any]:
        """完整编译流程。返回字典：

        {
            'source': 源代码,
            'tokens': Token 列表,
            'ast_raw': ast_nodes_v3.Module,
            'ast': ast_nodes.Module,
            'inferencer': TypeInferencer（含类型标注信息）,
            'errors': 错误列表,
        }
        """
        # 1) 词法分析
        tokens = self.tokenize(source)

        # 2) 语法解析（原始 v3 AST）
        raw_ast = self.parse_raw(source)

        # 3) AST 适配
        our_ast = self.adapt(raw_ast)

        # 4) 优化（默认开启）
        if optimize:
            our_ast = self.optimize_ast(our_ast)

        # 5) 类型检查
        self.type_check(our_ast, source)

        return {
            'source': source,
            'tokens': tokens,
            'ast_raw': raw_ast,
            'ast': our_ast,
            'inferencer': self._inferencer,
            'errors': list(self.errors),
        }

    # ------------------------------------------------------------------
    # 项目级入口（多模块编译）
    # ------------------------------------------------------------------
    def compile_project(self, project_root: Optional[str] = None, optimize: bool = True) -> Dict[str, Any]:
        """编译整个光明项目（支持多模块。

        流程：
          1. 解析 package.toml，寻找入口模块
          2. 从入口模块出发递归解析所有依赖（ModuleDependencyResolver）
          3. 按拓扑顺序编译每个模块，合并导出符号到全局符号表
          4. 在类型检查阶段将导入模块的符号合并到当前作用域
        """
        pr_path = Path(project_root) if project_root else self.project_root
        if pr_path is not None:
            self.project_root = pr_path
        root = self.project_root
        if root is None:
            root = Path(os.getcwd())

        # 预加载标准库
        self.preload_stdlib()

        # 1) 加载配置
        try:
            from package_manager import PackageManager  # type: ignore
        except Exception as e:
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": None,
                "entry": "",
                "project_root": str(root),
                "errors": [f"无法导入 PackageManager: {e}"],
            }

        pm = PackageManager(root)
        config = pm.load_config()
        if config is None:
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": None,
                "entry": "",
                "project_root": str(root),
                "errors": ["未找到 package.toml 或解析失败"],
            }

        entry_path = root / config.entry
        if not entry_path.exists():
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": config,
                "entry": config.entry,
                "project_root": str(root),
                "errors": [f"入口文件不存在: {config.entry}"],
            }

        try:
            source = entry_path.read_text(encoding="utf-8")
        except OSError as e:
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": config,
                "entry": config.entry,
                "project_root": str(root),
                "errors": [f"读取入口文件失败: {e}"],
            }

        # 2) 解析所有模块依赖
        try:
            from module_resolver import ModuleDependencyResolver  # type: ignore
        except Exception as e:
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": config,
                "entry": config.entry,
                "project_root": str(root),
                "errors": [f"无法导入 ModuleDependencyResolver: {e}"],
            }

        resolver = ModuleDependencyResolver([root])
        entry_name = entry_path.stem
        try:
            modules = resolver.resolve_all(entry_name, source)
        except Exception as e:
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": config,
                "entry": config.entry,
                "project_root": str(root),
                "errors": [f"解析依赖失败: {e}"],
            }

        # 3) 拓扑排序
        try:
            order = resolver.topological_order()
        except Exception as e:
            # 循环依赖或其他排序错误
            return {
                "success": False,
                "modules": {},
                "order": [],
                "config": config,
                "entry": config.entry,
                "project_root": str(root),
                "errors": [f"拓扑排序失败: {e}"],
            }

        # 4) 按顺序编译每个模块
        module_results: Dict[str, Dict[str, Any]] = {}
        self.global_module_symbols = {}
        # 清空错误（保留已有错误以兼容）
        original_errors = list(self.errors)
        self.errors = []

        for mod_name in order:
            if mod_name not in modules:
                continue
            mod_info = modules[mod_name]
            mod_source = mod_info.source if mod_info.source else ""
            if not mod_source:
                continue
            try:
                tokens_mod = self.tokenize(mod_source)
                raw_ast_mod = self.parse_raw(mod_source)
                our_ast_mod = self.adapt(raw_ast_mod)
                # 优化（默认开启）
                if optimize:
                    our_ast_mod = self.optimize_ast(our_ast_mod)
                # 类型推断：让 inferencer 拥有当前模块及其导入模块符号
                from type_inferencer import TypeInferencer  # type: ignore
                mod_inferencer = TypeInferencer()
                # 注入标准库符号
                self._inject_stdlib_symbols(mod_inferencer)
                # 合并已编译模块的符号到当前类型推断器
                self._merge_module_symbols(mod_inferencer, modules, mod_name)
                mod_inferencer.infer(our_ast_mod)
                # 记录导出符号
                module_results[mod_name] = {
                    "tokens": tokens_mod,
                    "ast_raw": raw_ast_mod,
                    "ast": our_ast_mod,
                    "inferencer": mod_inferencer,
                    "exports": list(mod_info.exports),
                    "errors": list(getattr(mod_inferencer, "errors", [])),
                    "source": mod_source,
                }
                # 记录符号（跨模块）
                self._record_module_symbols(mod_name, our_ast_mod, mod_info.exports)
                if hasattr(mod_inferencer, "errors"):
                    self.errors.extend(mod_inferencer.errors)
            except Exception as e:
                module_results[mod_name] = {
                    "tokens": [],
                    "ast_raw": None,
                    "ast": None,
                    "inferencer": None,
                    "exports": list(mod_info.exports),
                    "errors": [f"模块 {mod_name} 编译失败: {e}"],
                    "source": mod_source,
                }
                self.errors.append(f"模块 {mod_name} 编译失败: {e}")

        success = len(self.errors) == 0
        # 恢复原始错误（如在初始化阶段出现）
        self.errors.extend(original_errors)
        return {
            "success": success,
            "entry": config.entry,
            "config": config,
            "modules": module_results,
            "order": order,
            "project_root": str(root),
            "errors": list(self.errors),
        }

    # ------------------------------------------------------------------
    # 分步方法
    # ------------------------------------------------------------------
    def tokenize(self, source: str) -> List[Token]:
        """词法分析"""
        try:
            return self._lexer.tokenize(source)
        except LexerError as e:
            # 提取行号/列号信息并添加上下文
            line = getattr(e, 'line', 0)
            col = getattr(e, 'col', 0)
            context = format_source_context(source, line, col) if source else ""
            self.errors.append(f"词法错误: {e}")
            if context:
                self.errors.append(context)
            raise

    def parse_raw(self, source: str):
        """语法解析（返回 v3 AST）"""
        try:
            return self._parser.parse(source)
        except ParseError as e:
            # 提取行号/列号信息
            line = getattr(e, 'line', 0)
            col = getattr(e, 'column', 0) or getattr(e, 'col', 0)
            context = format_source_context(source, line, col) if source else ""
            self.errors.append(f"语法错误: {e}")
            if context:
                self.errors.append(context)
            raise
        except Exception as e:
            self.errors.append(f"解析错误: {e}")
            raise

    def adapt(self, raw_ast) -> ast.Module:
        """将 v3 AST 适配为我们的 ast_nodes.Module"""
        return self._adapter.convert_module(raw_ast)

    def optimize_ast(self, module: ast.Module) -> ast.Module:
        """依次运行所有优化器，返回优化后的模块"""
        for optimizer_cls in OPTIMIZERS:
            optimizer = optimizer_cls()
            module = optimizer.optimize(module)
        return module

    def type_check(self, module: ast.Module, source: str = '') -> Any:
        """对适配后的 AST 进行类型推断与检查。返回 inferencer 实例。"""
        from type_inferencer import TypeInferencer
        from type_checker import create_checker_from_source, create_checker_from_config

        self._inferencer = TypeInferencer()
        self._inferencer.infer(module)

        # 聚合类型推断错误（字符串列表，保持向后兼容）
        if hasattr(self._inferencer, 'errors'):
            for err in self._inferencer.errors:
                # 尝试提取行号信息
                err_str = str(err)
                err_line = self._extract_line_from_error(err)
                if source and err_line:
                    context = format_source_context(source, err_line)
                    self.errors.append(f"[类型推断] {err_str}")
                    if context:
                        self.errors.append(context)
                else:
                    self.errors.append(f"[类型推断] {err_str}")
        # 也保存结构化错误（携带位置信息）
        if hasattr(self._inferencer, 'get_typed_errors'):
            self._typed_errors = self._inferencer.get_typed_errors()

        # 分级类型检查
        if source:
            checker = create_checker_from_source(source, self._config)
        else:
            checker = create_checker_from_config(self._config)

        if checker.config.check_level.value > 0:
            check_results = checker.check(module, self._inferencer)
            self._collect_type_check_results(checker)

        return self._inferencer

    def _collect_type_check_results(self, checker) -> None:
        """收集类型检查结果并格式化输出"""
        for result in checker.results:
            if result.severity.value == 'error':
                self.errors.append(f"[类型错误] {result.message}")
            elif result.severity.value == 'warning':
                if hasattr(self, 'warnings'):
                    self.warnings.append(f"[类型警告] {result.message}")

        if checker.has_errors():
            self.errors.append(f"类型检查发现 {len(checker.get_errors())} 个错误")

        if checker.get_warnings():
            self.errors.append(f"类型检查发现 {len(checker.get_warnings())} 个警告")

    # ------------------------------------------------------------------
    # 跨模块符号链接
    # ------------------------------------------------------------------
    def _record_module_symbols(self, module_name: str,
                                module_ast: Any,
                                exports: List[str]) -> None:
        """记录模块导出的符号（用于跨模块可见性控制）。"""
        sym_table: Dict[str, Any] = {}
        # 显式导出优先
        if exports:
            # 遍历 statements 找匹配的段落/类
            statements = getattr(module_ast, "statements", None) or []
            for stmt in statements:
                stmt_name = getattr(stmt, "name", None)
                if stmt_name and str(stmt_name) in [str(e) for e in exports]:
                    sym_table[str(stmt_name)] = {
                        "kind": type(stmt).__name__,
                        "node": stmt,
                        "public": True,
                    }
        # 隐式导出
        else:
            segments = getattr(module_ast, "segments", None) or []
            classes = getattr(module_ast, "classes", None) or []
            statements = getattr(module_ast, "statements", None) or []
            for seg in list(segments) + list(classes):
                name = getattr(seg, "name", None)
                if name:
                    sym_table[str(name)] = {
                        "kind": type(seg).__name__,
                        "node": seg,
                        "public": True,
                    }
            for stmt in statements:
                name = getattr(stmt, "name", None)
                if name:
                    key = str(name)
                    if key not in sym_table:
                        sym_table[key] = {
                            "kind": type(stmt).__name__,
                            "node": stmt,
                            "public": True,
                        }
        self.global_module_symbols[module_name] = sym_table

    def _merge_module_symbols(self, inferencer: Any,
                              modules: Dict[str, Any],
                              current_module_name: str) -> None:
        """将已编译模块的符号合并到当前模块的 inferencer 符号表。"""
        if not hasattr(inferencer, "symbol_table"):
            return
        sym_table = inferencer.symbol_table
        if sym_table is None or not hasattr(sym_table, "define"):
            return
        current = modules.get(current_module_name)
        if current is None:
            return
        imports = getattr(current, "imports", []) or []
        for imported_name in imports:
            mod_symbols = self.global_module_symbols.get(str(imported_name), {})
            if not mod_symbols:
                continue
            for sym_name, info in mod_symbols.items():
                try:
                    # 使用 TypeInferencer.type_unknown 作为占位类型
                    type_val = getattr(inferencer, "type_unknown", None)
                    sym_table.define(str(sym_name),
                                     str(info.get("kind", "function")),
                                     type_val)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # 错误定位辅助
    # ------------------------------------------------------------------
    def _extract_line_from_error(self, error: Any) -> int:
        """从错误对象中提取行号
        
        Args:
            error: 错误对象（可以是异常或字符串）
            
        Returns:
            行号，如果无法提取则返回 0
        """
        # 检查对象属性
        if hasattr(error, 'line'):
            line = getattr(error, 'line', 0)
            if line:
                return line
        if hasattr(error, 'lineno'):
            line = getattr(error, 'lineno', 0)
            if line:
                return line
        
        # 从字符串中匹配
        import re
        err_str = str(error)
        match = re.search(r'[行\s](\d+)', err_str)
        if match:
            return int(match.group(1))
        match = re.search(r'line\s*(\d+)', err_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return 0

    def _format_error_with_context(self, error: Exception, source: str,
                                    line: int = 0, col: int = 0) -> str:
        """格式化错误并附带源代码上下文
        
        Args:
            error: 异常对象
            source: 源代码
            line: 行号
            col: 列号
            
        Returns:
            格式化的错误信息
        """
        if isinstance(error, LightError):
            return format_error_with_context(error, source, line or error.line, col or error.col)
        return format_error_with_context(error, source, line, col)

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def describe(self, module: ast.Module, indent: int = 0) -> str:
        """简单的 AST 描述（调试用）"""
        out = []
        prefix = '  ' * indent
        for seg in module.segments:
            out.append(f"{prefix}段『{seg.name}』: {len(seg.parameters)} 参数")
        for cls in module.classes:
            out.append(f"{prefix}类『{cls.name}』")
        for stmt in module.statements:
            out.append(f"{prefix}语句: {type(stmt).__name__}")
        return '\n'.join(out)

    def generate_llvm_ir(self, module: ast.Module) -> str:
        """生成 LLVM IR 代码
        
        使用 antlrparser/llvm_codegen.py 中的 LLVMCodeGen 生成 LLVM IR。
        需要确保 antlrparser 目录在 sys.path 中。
        """
        import sys
        import os
        antlrparser_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'antlrparser')
        if antlrparser_path not in sys.path:
            sys.path.insert(0, antlrparser_path)
        
        try:
            from llvm_codegen import LLVMCodeGen
            codegen = LLVMCodeGen()
            return codegen.generate(module)
        except ImportError as e:
            self.errors.append(f"无法导入 LLVM 代码生成器: {e}")
            raise


# =============================================================================
# 顶层便捷函数
# =============================================================================

def compile_file(file_path: str, use_cache: bool = True) -> Dict[str, Any]:
    """编译文件并返回编译结果

    Args:
        file_path: 源文件路径
        use_cache: 是否使用编译缓存，默认为 True

    Returns:
        编译结果字典，与 LightCompiler.compile() 返回格式相同
    """
    abs_path = os.path.abspath(file_path)
    mtime = os.path.getmtime(abs_path)

    # 旧缓存系统（向后兼容，保持对象引用一致性）
    if use_cache and abs_path in _compile_cache:
        cached_mtime, cached_result = _compile_cache[abs_path]
        if cached_mtime == mtime:
            return cached_result

    # 新缓存系统（CompilationCache）
    if use_cache and _HAS_CACHE:
        cache = _get_cache()
        if cache and cache.is_fresh(abs_path):
            cached_result = cache.get_cached(abs_path)
            if cached_result is not None:
                import json
                return json.loads(cached_result) if isinstance(cached_result, str) else {}

    with open(abs_path, 'r', encoding='utf-8') as f:
        source = f.read()

    compiler = LightCompiler()
    result = compiler.compile(source)

    if use_cache:
        _compile_cache[abs_path] = (mtime, result)
        # 也写入新缓存系统
        if _HAS_CACHE:
            cache = _get_cache()
            if cache:
                import json
                cache.set_cached(abs_path, json.dumps(result, ensure_ascii=False, default=str))

    return result


def compile_source(source: str) -> LightCompiler:
    """编译源码并返回已完成类型检查的编译器实例"""
    c = LightCompiler()
    c.compile(source)
    return c


def parse_source(source: str) -> ast.Module:
    """仅解析源码，返回适配后的 AST"""
    c = LightCompiler()
    tokens = c.tokenize(source)
    raw = c.parse_raw(source)
    return c.adapt(raw)


def tokenize_source(source: str) -> List[Token]:
    """仅进行词法分析"""
    return LightCompiler().tokenize(source)


# =============================================================================
# 便捷的类型查询 API（在编译器完成后使用）
# =============================================================================

class CompilerQuery:
    """便捷查询编译器结果的辅助类"""

    def __init__(self, compiler: LightCompiler):
        self.compiler = compiler

    def infer_variable_type(self, var_name: str) -> Optional[str]:
        """查询变量类型"""
        if not self.compiler._inferencer:
            return None
        sym = self.compiler._inferencer.symbol_table.lookup(var_name)
        if sym is None or not hasattr(sym, 'data_type') or sym.data_type is None:
            return None
        return str(sym.data_type)

    def has_type_errors(self) -> bool:
        return self.compiler.has_errors
