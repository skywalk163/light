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
import hashlib
import threading
import time

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
from errors import CompilerErrorCollector, ErrorEntry
from version import VERSION as _LANG_VERSION

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


# =============================================================================
# 编译器缓存系统（v5.2.0）
# 三级缓存：词法分析 → AST 解析 → 代码生成
# 使用内容哈希（SHA256）确保缓存一致性
# =============================================================================

class CompilerCache:
    """编译器缓存：三级缓存 + 自动失效

    缓存级别：
      1. 词法分析缓存 (_token_cache): source_hash → List[Token]
      2. AST 解析缓存 (_ast_cache): source_hash → v3_ast.Module
      3. 代码生成缓存 (_codegen_cache): source_hash → str

    所有缓存键使用源文件内容的 SHA256 哈希，确保内容变更时缓存自动失效。
    """

    def __init__(self, max_size: int = 100):
        self._token_cache: Dict[str, List[Token]] = {}
        self._ast_cache: Dict[str, Any] = {}
        self._codegen_cache: Dict[str, str] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    @staticmethod
    def content_hash(content: str) -> str:
        """计算源文件内容的 SHA256 哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def file_hash(file_path: str) -> str:
        """计算文件内容的 SHA256 哈希"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    # ---- 词法分析缓存 ----

    def get_token_cache(self, source_hash: str) -> Optional[List[Token]]:
        """获取缓存的词法分析结果"""
        with self._lock:
            result = self._token_cache.get(source_hash)
            if result is not None:
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
            return result

    def set_token_cache(self, source_hash: str, tokens: List[Token]) -> None:
        """设置词法分析缓存"""
        with self._lock:
            self._evict_if_needed(self._token_cache)
            self._token_cache[source_hash] = tokens

    # ---- AST 解析缓存 ----

    def get_ast_cache(self, source_hash: str) -> Optional[Any]:
        """获取缓存的 AST 解析结果"""
        with self._lock:
            result = self._ast_cache.get(source_hash)
            if result is not None:
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
            return result

    def set_ast_cache(self, source_hash: str, ast_module: Any) -> None:
        """设置 AST 解析缓存"""
        with self._lock:
            self._evict_if_needed(self._ast_cache)
            self._ast_cache[source_hash] = ast_module

    # ---- 代码生成缓存 ----

    def get_codegen_cache(self, source_hash: str) -> Optional[str]:
        """获取缓存的代码生成结果"""
        with self._lock:
            result = self._codegen_cache.get(source_hash)
            if result is not None:
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
            return result

    def set_codegen_cache(self, source_hash: str, code: str) -> None:
        """设置代码生成缓存"""
        with self._lock:
            self._evict_if_needed(self._codegen_cache)
            self._codegen_cache[source_hash] = code

    # ---- 缓存管理 ----

    def _evict_if_needed(self, cache: Dict) -> None:
        """如果缓存超过最大大小，执行 LRU 淘汰"""
        if len(cache) >= self._max_size:
            # 淘汰前 1/4 的条目（简单实现）
            keys = list(cache.keys())
            for k in keys[:len(keys) // 4]:
                del cache[k]
            self._stats['evictions'] += len(keys) // 4

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._token_cache.clear()
            self._ast_cache.clear()
            self._codegen_cache.clear()

    def clear_codegen(self) -> None:
        """仅清空代码生成缓存（源文件变更时最常用）"""
        with self._lock:
            self._codegen_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'token_cache_size': len(self._token_cache),
                'ast_cache_size': len(self._ast_cache),
                'codegen_cache_size': len(self._codegen_cache),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': self._stats['hits'] / max(self._stats['hits'] + self._stats['misses'], 1),
            }

    def invalidate_source(self, source_hash: str) -> None:
        """使指定源文件的所有缓存失效"""
        with self._lock:
            self._token_cache.pop(source_hash, None)
            self._ast_cache.pop(source_hash, None)
            self._codegen_cache.pop(source_hash, None)


# 全局缓存实例（单例）
_compiler_cache = CompilerCache()

# 向后兼容：旧的 _compile_cache 字典仍然保留
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
            'TupleLiteral': self._convert_tuple_literal,
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
            'UnaryOp': self._convert_unary_op,
            'SliceExpr': self._convert_slice_expr,
            'UnwrapExpression': self._convert_unwrap_expression,
            'RangeExpr': self._convert_range_expr,
            'AwaitExpr': self._convert_await_expr,
            'AsyncScope': self._convert_async_scope,
            'PassStmt': self._convert_pass_stmt,
            'KeywordArg': self._convert_keyword_arg,
            # R10-11b（第四批B）：`生成 表达式。` → 一等语句节点。
            # 此前 YieldStmt 无转换器 → 降级成 `<unknown:YieldStmt>` 标识符，
            # 原生腿只能报「暂不支持语句类型 YieldStmt」。
            'YieldStmt': self._convert_yield_stmt,
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
            # C3-4：转换器可能返回 None（如 PassStmt 空语句编成 no-op），直接跳过。
            if converted is None:
                continue
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
                # R10-11b：`生成` 是语句不是表达式，必须原样留在语句流里。
                # 漏了这条它会被包成 ExpressionStatement，原生腿的生成器
                # 分派就永远匹配不到。
                ast.YieldStatement,
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
                    default_value=self._convert_default_value(p.get('default')),
                ))
            elif isinstance(p, v3_ast.Parameter):
                params.append(ast.Parameter(
                    name=p.name,
                    type_annotation=getattr(p, 'type_annotation', None),
                    default_value=self._convert_default_value(getattr(p, 'default', None)),
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

    def _convert_keyword_arg(self, node) -> ast.KeywordArg:
        """关键字参数 f(名=值)：v3 KeywordArg -> ast.KeywordArg(name, value)。
        原生腿在函数调用参数展开时按目标函数参数名映射到位置。"""
        return ast.KeywordArg(name=str(node.name), value=self.convert(node.value))

    def _convert_paragraph_call(self, node) -> ast.FunctionCall:
        args = self._convert_list(node.args)
        return ast.FunctionCall(
            name=ast.SegmentName(name=node.name) if hasattr(ast, 'SegmentName')
                else ast.Identifier(name=node.name),
            arguments=args,
            type_args=[],
        )

    def _convert_number_literal(self, node) -> ast.NumberLiteral:
        s = str(node.value)
        return ast.NumberLiteral(value=float(node.value) if ('.' in s or 'e' in s.lower())
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

    def _convert_unary_op(self, node) -> ast.UnaryOp:
        return ast.UnaryOp(
            operator=node.operator,
            operand=self.convert(node.operand),
        )

    def _convert_slice_expr(self, node) -> ast.FunctionCall:
        """将 v3 SliceExpr 转换为 FunctionCall(slice, start, stop, step)"""
        args = []
        if node.start is not None:
            args.append(self.convert(node.start))
        if node.stop is not None:
            args.append(self.convert(node.stop))
        if node.step is not None:
            args.append(self.convert(node.step))
        return ast.FunctionCall(
            name=ast.Identifier(name='slice'),
            arguments=args,
            type_args=[],
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

    def _convert_yield_stmt(self, node) -> ast.YieldStatement:
        """R10-11b：`生成 表达式。` / `生成 全部 表达式。`

        只做节点转型，不做语义展开——生成器状态机在 codegen 侧（原生腿）
        与转译腿各自实现。`is_from` 原样透传，由后端决定是否支持。
        """
        return ast.YieldStatement(
            value=self.convert(getattr(node, 'value', None)),
            is_from=bool(getattr(node, 'is_from', False)),
        )

    def _convert_pass_stmt(self, node):
        """C3-4：`pass`（空语句）语义上就是 no-op，编成空操作而不是报错。

        返回 None：`_to_list_stmts` 会跳过 None，于是模块/段落体内不生成任何产物。
        之前 PassStmt 没有转换器，走 `<unknown:PassStmt>` 报「不支持 空语句」——
        对一条什么都没干的语句报不支持，很荒谬。
        """
        return None

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

    def _convert_tuple_literal(self, node) -> ast.TupleLiteral:
        return ast.TupleLiteral(elements=self._convert_list(node.elements))

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
        # v3 的 target 有两种形态：字符串文本（顶层 '映射[键]'，index 未拆分）
        # 或已解析的 IndexAccess 节点（段落内 映射[键]，obj/index 齐全）。
        # 后者绝不能包成 Identifier(name=IndexAccess)，否则 codegen 把 IndexAccess
        # 当字符串用崩溃（内置核心字典 字典设置 回归根因）。
        if isinstance(node.target, str):
            target = ast.IndexAccess(obj=ast.Identifier(name=node.target),
                                     index=self.convert(node.index))
        else:
            target = self.convert(node.target)
        return ast.Assignment(
            target=target,
            value=self.convert(node.value),
        )

    def _convert_default_value(self, raw):
        """把 v3 参数默认值（int/bool/str/None 或表达式节点）转成 AST 节点。"""
        if raw is None:
            return None
        if isinstance(raw, bool):
            return ast.BooleanLiteral(value=raw)
        if isinstance(raw, (int, float)):
            return ast.NumberLiteral(value=raw)
        if isinstance(raw, str):
            return ast.StringLiteral(value=raw)
        # 复杂默认表达式：v3 存表达式节点，递归转换
        return self.convert(raw)

    def _convert_parameter(self, node) -> ast.Parameter:
        default_raw = getattr(node, 'default', None)
        default_ast = None
        if default_raw is not None:
            if isinstance(default_raw, bool):
                default_ast = ast.BooleanLiteral(value=default_raw)
            elif isinstance(default_raw, (int, float)):
                default_ast = ast.NumberLiteral(value=default_raw)
            elif isinstance(default_raw, str):
                default_ast = ast.StringLiteral(value=default_raw)
            else:
                # 复杂默认表达式：v3 存表达式节点，递归转换
                default_ast = self.convert(default_raw)
        return ast.Parameter(
            name=node.name,
            type_annotation=getattr(node, 'type_annotation', None),
            default_value=default_ast,
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
        expr = getattr(node, 'expression', None) or getattr(node, 'element', None)
        return ast.ListComprehension(
            expression=self.convert(expr),

            variable=getattr(node, 'variable', 'x'),
            iterable=self.convert(getattr(node, 'iterable', None)),
            condition=self.convert(getattr(node, 'condition', None)),
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

    def _convert_string_interpolation(self, node) -> ast.StringInterpolation:
        """C3-2：把 v3 StringInterpolation 的 parts（交替 str 与 ASTNode）无损转成
        ast.StringInterpolation，供代码生成器做「分段 + 拼接」降级实现。
        改动前直接转成 StringLiteral 且值恒为空串——插值被静默吃掉。"""
        parts = []
        for part in getattr(node, 'parts', []):
            if isinstance(part, str):
                parts.append(part)
            else:
                parts.append(self.convert(part))
        return ast.StringInterpolation(parts=parts)

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
        variables = []
        if hasattr(node, 'variables'):
            variables = [str(v) for v in node.variables]
        elif hasattr(node, 'names'):
            variables = [str(n) for n in node.names]
        elif hasattr(node, 'targets'):
            variables = [str(t) for t in node.targets]
        return ast.DestructuringAssignment(
            variables=variables,
            value=self.convert(getattr(node, 'value', None)),
        )

    def _convert_with_stmt(self, node) -> ast.WithStatement:
        return ast.WithStatement(
            context_expr=self.convert(getattr(node, 'context_expr', None)),
            variable=getattr(node, 'variable', None),
            body=self._to_list_stmts(getattr(node, 'body', [])),
        )

    def _convert_dict_literal(self, node) -> ast.DictLiteral:
        # raw AST 的 DictLiteral.entries 为 (key, value) 元组列表；
        # **展开 用 (None, expr) 表示，需保留给代码生成器
        raw_entries = getattr(node, 'entries', None) or getattr(node, 'elements', [])
        entries = []
        for pair in raw_entries:
            if isinstance(pair, (tuple, list)) and len(pair) == 2:
                key, value = pair
                entries.append((self.convert(key) if key is not None else None,
                                self.convert(value)))
            else:
                entries.append((None, self.convert(pair)))
        return ast.DictLiteral(entries=entries)

    def _convert_dict_comprehension(self, node) -> ast.DictComprehension:
        return ast.DictComprehension(
            key_expr=self.convert(getattr(node, 'key_expr', None)),
            value_expr=self.convert(getattr(node, 'value_expr', None)),
            variable=getattr(node, 'variable', 'x'),
            iterable=self.convert(getattr(node, 'iterable', None)),
            condition=self.convert(getattr(node, 'condition', None)),
        )

    def _convert_match_stmt(self, node) -> ast.MatchStatement:
        cases = []
        for c in getattr(node, 'cases', []):
            cases.append(ast.MatchCase(
                pattern=self._convert_match_pattern(getattr(c, 'pattern', None)),
                guard=self.convert(getattr(c, 'guard', None)),
                body=self._to_list_stmts(getattr(c, 'body', [])),
            ))
        return ast.MatchStatement(
            subject=self.convert(getattr(node, 'subject', None)),
            cases=cases,
        )

    def _convert_match_pattern(self, pattern) -> ast.MatchPattern:
        """将 v3 MatchPattern / 字面量转换为 ast_nodes.MatchPattern"""
        if pattern is None:
            return None
        if isinstance(pattern, str):
            return ast.MatchPattern(kind='string', value=ast.StringLiteral(pattern))
        if not hasattr(pattern, 'kind'):
            # 字面量节点（NumberLiteral 等）兜底
            return ast.MatchPattern(kind='literal', value=pattern)
        value = getattr(pattern, 'value', None)
        if isinstance(value, str):
            value = ast.StringLiteral(value)
        else:
            value = self.convert(value)
        elements = [self._convert_match_pattern(e)
                    for e in getattr(pattern, 'elements', [])]
        return ast.MatchPattern(
            kind=getattr(pattern, 'kind', 'literal'),
            value=value,
            elements=elements,
            type_name=getattr(pattern, 'type_name', ''),
            binding=getattr(pattern, 'binding', ''),
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

    # 光明编译器版本号（唯一真源 src/version.py，禁止写死字面量）
    VERSION = _LANG_VERSION

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
        # 统一错误收集器（A3.1 新增）
        self._error_collector = CompilerErrorCollector()
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
    def compile(self, source: str, optimize: bool = True, use_cache: bool = True) -> Dict[str, Any]:
        """完整编译流程。返回字典：

        {
            'source': 源代码,
            'tokens': Token 列表,
            'ast_raw': ast_nodes_v3.Module,
            'ast': ast_nodes.Module,
            'inferencer': TypeInferencer（含类型标注信息）,
            'errors': 错误列表,
        }

        支持三级缓存优化（use_cache=True 时启用）：
        - 词法分析缓存：相同源内容跳过重复词法分析
        - AST 解析缓存：相同源内容跳过重复语法解析
        """
        # 重置错误状态（compile 可被重复调用，避免跨会话累积）
        self.errors = []
        self._typed_errors = []

        # 计算源内容哈希（用于缓存检索）
        source_hash = _compiler_cache.content_hash(source) if use_cache else None

        # 1) 词法分析（使用缓存）
        if use_cache and source_hash:
            tokens = _compiler_cache.get_token_cache(source_hash)
            if tokens is None:
                tokens = self.tokenize(source)
                _compiler_cache.set_token_cache(source_hash, tokens)
        else:
            tokens = self.tokenize(source)

        # 2) 语法解析（原始 v3 AST，使用缓存）
        if use_cache and source_hash:
            raw_ast = _compiler_cache.get_ast_cache(source_hash)
            if raw_ast is None:
                raw_ast = self.parse_raw(source)
                _compiler_cache.set_ast_cache(source_hash, raw_ast)
        else:
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
            modules = resolver.resolve_all(entry_name, source, str(entry_path.parent))
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
            # 将错误添加到统一收集器
            self._error_collector.add_lexer_error(
                message=str(e), line=line, column=col, exception=e,
            )
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
            # 将错误添加到统一收集器
            src_line = source.split('\n')[line - 1] if source and 0 < line <= len(source.split('\n')) else ''
            self._error_collector.add_parser_error(
                message=str(e), line=line, column=col,
                source_line=src_line, exception=e,
            )
            raise
        except Exception as e:
            self.errors.append(f"解析错误: {e}")
            self._error_collector.add_parser_error(
                message=str(e), exception=e,
            )
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
                # 添加到统一收集器
                self._error_collector.add_type_error(
                    message=err_str, line=err_line,
                )
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
                self._error_collector.add_type_error(
                    message=result.message, line=result.line, column=result.column,
                )
            elif result.severity.value == 'warning':
                if hasattr(self, 'warnings'):
                    self.warnings.append(f"[类型警告] {result.message}")
                self._error_collector.add_warning(ErrorEntry(
                    stage='类型检查', message=result.message,
                    line=result.line, column=result.column,
                ))

        if checker.has_errors():
            self.errors.append(f"类型检查发现 {len(checker.get_errors())} 个错误")

    # =================================================================
    # A3.1/A3.2: 统一错误格式化与查询接口
    # =================================================================

    def get_error_collector(self) -> CompilerErrorCollector:
        """获取统一错误收集器"""
        return self._error_collector

    def get_formatted_errors(self, source: str = '') -> str:
        """获取格式化的所有错误信息"""
        if source:
            self._error_collector.source = source
        return self._error_collector.format_all()

    def get_error_summary(self) -> str:
        """获取错误摘要"""
        return self._error_collector.format_summary()

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

def _normalize_cache_path(path: str) -> str:
    """规范化缓存路径（Windows 上统一小写，避免大小写不一致导致缓存未命中）"""
    abs_path = os.path.abspath(path)
    return os.path.normcase(abs_path)


def compile_file(file_path: str, use_cache: bool = True) -> Dict[str, Any]:
    """编译文件并返回编译结果

    Args:
        file_path: 源文件路径
        use_cache: 是否使用编译缓存，默认为 True

    Returns:
        编译结果字典，与 LightCompiler.compile() 返回格式相同
    """
    cache_key = _normalize_cache_path(file_path)
    abs_path = os.path.abspath(file_path)
    mtime = os.path.getmtime(abs_path)

    # 旧缓存系统（向后兼容，保持对象引用一致性）
    # 键使用规范化后的 cache_key（Windows 上大小写统一，避免缓存未命中）
    if use_cache and cache_key in _compile_cache:
        cached_mtime, cached_result = _compile_cache[cache_key]

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
    result = compiler.compile(source, use_cache=use_cache)

    if use_cache:
        _compile_cache[cache_key] = (mtime, result)
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


# =============================================================================
# 命令行入口：支持 --welcome 标志
# =============================================================================

def main():
    """编译器命令行入口

    支持 --welcome 标志触发首次运行引导体验。
    """
    import argparse
    parser = argparse.ArgumentParser(
        description='光明（Light）编程语言编译器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--welcome', action='store_true',
                        help='显示首次运行欢迎引导')
    parser.add_argument('--version', action='version',
                        version=f'光明编译器 v{LightCompiler.VERSION}')

    args = parser.parse_args()

    if args.welcome:
        try:
            from first_run import run_welcome
            result = run_welcome()
            if result == 'repl':
                from first_run import start_repl
                start_repl()
        except ImportError as e:
            print(f"[错误] 无法加载首次运行引导模块: {e}", file=sys.stderr)
            return 1
        return 0

    # 默认行为：输出帮助信息
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
