from .base import Optimizer
from ast_nodes import (
    ASTNode, Module, BinaryOp, UnaryOp,
    NumberLiteral, StringLiteral, BooleanLiteral,
    VariableDeclaration, Assignment, IfStatement,
    ExpressionStatement, PrintStatement, ReturnStatement,
    WhileStatement, ForeachStatement,
    FunctionCall, SegmentDefinition, ClassDefinition,
)


class ConstantFoldingOptimizer(Optimizer):
    """常量折叠优化器
    
    后序遍历 AST，对纯字面量的二元运算进行常量折叠。
    支持的运算：
    - 算术：加(+)、减(-)、乘(*)、除(/)、模(%)、幂(**)
    - 字符串：加(+)拼接
    - 比较：大于(>)、小于(<)、等于(==)、不等于(!=)、大于等于(>=)、小于等于(<=)
    - 布尔：且(and)、或(or)
    """

    def optimize(self, module: Module) -> Module:
        """优化整个模块"""
        module.statements = [self._optimize_stmt(stmt) for stmt in module.statements]
        module.segments = [self._optimize_segment(seg) for seg in module.segments]
        module.classes = [self._optimize_class(cls) for cls in module.classes]
        return module

    def optimize_expr(self, expr: ASTNode) -> ASTNode:
        """优化单个表达式"""
        return self._optimize_expr(expr)

    def _optimize_expr(self, expr: ASTNode) -> ASTNode:
        """后序遍历优化表达式"""
        if isinstance(expr, BinaryOp):
            return self._fold_binary_op(expr)
        if isinstance(expr, UnaryOp):
            return self._optimize_unary_op(expr)
        if isinstance(expr, FunctionCall):
            return self._optimize_function_call(expr)
        return expr

    def _fold_binary_op(self, node: BinaryOp) -> ASTNode:
        """折叠二元运算（后序遍历）"""
        node.left = self._optimize_expr(node.left)
        node.right = self._optimize_expr(node.right)

        left = node.left
        right = node.right
        op = node.operator

        if not self._is_literal(left) or not self._is_literal(right):
            return node

        left_val = self._literal_value(left)
        right_val = self._literal_value(right)

        try:
            result = self._apply_op(op, left_val, right_val)
        except ZeroDivisionError:
            return node
        except Exception:
            return node

        return self._make_literal(result, node.line, node.column)

    def _is_literal(self, node: ASTNode) -> bool:
        """判断节点是否为纯字面量"""
        return isinstance(node, (NumberLiteral, StringLiteral, BooleanLiteral))

    def _literal_value(self, node: ASTNode):
        """获取字面量的值"""
        return node.value

    def _make_literal(self, value, line: int = 0, column: int = 0) -> ASTNode:
        """根据值创建字面量节点"""
        if isinstance(value, bool):
            return BooleanLiteral(value=value, line=line, column=column)
        if isinstance(value, (int, float)):
            return NumberLiteral(value=value, line=line, column=column)
        if isinstance(value, str):
            return StringLiteral(value=value, line=line, column=column)
        return None

    def _apply_op(self, op: str, left, right):
        """应用二元运算"""
        if op == '+':
            return left + right
        if op == '-':
            return left - right
        if op == '*':
            return left * right
        if op == '/':
            # 「除以」/「除」整数相除向零截断（与原生腿 i64 sdiv 一致，见 known_issues §15.1 选 B）；
            # 浮点操作数退化为真除法（与原生腿 fdiv 一致）。不可用 Python //（floor），
            # 否则负数语义与原生腿分叉（-7//2=-4 vs sdiv -3）。
            if type(left) is int and type(right) is int:
                return left // right if left * right >= 0 else -((-left) // right)
            return left / right
        if op == '//':
            # 「整除」保留 Python floor 语义，负数为向下取整。
            return left // right
        if op == '%':
            return left % right
        if op == '**':
            return left ** right
        if op == '>':
            return left > right
        if op == '<':
            return left < right
        if op == '==':
            return left == right
        if op == '!=':
            return left != right
        if op == '>=':
            return left >= right
        if op == '<=':
            return left <= right
        if op == 'and':
            return left and right
        if op == 'or':
            return left or right
        raise ValueError(f"不支持的运算符: {op}")

    def _optimize_unary_op(self, node) -> ASTNode:
        """优化一元运算"""
        if hasattr(node, 'operand'):
            node.operand = self._optimize_expr(node.operand)
        return node

    def _optimize_function_call(self, node: FunctionCall) -> FunctionCall:
        """优化函数调用参数"""
        node.arguments = [self._optimize_expr(arg) for arg in node.arguments]
        return node

    def _optimize_stmt(self, stmt: ASTNode) -> ASTNode:
        """优化语句"""
        if isinstance(stmt, VariableDeclaration):
            if stmt.value:
                stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, Assignment):
            stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, ExpressionStatement):
            stmt.expression = self._optimize_expr(stmt.expression)
        elif isinstance(stmt, PrintStatement):
            stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, ReturnStatement):
            if stmt.value:
                stmt.value = self._optimize_expr(stmt.value)
        elif isinstance(stmt, IfStatement):
            stmt.condition = self._optimize_expr(stmt.condition)
            stmt.then_body = [self._optimize_stmt(s) for s in stmt.then_body]
            if stmt.else_body:
                stmt.else_body = [self._optimize_stmt(s) for s in stmt.else_body]
        elif isinstance(stmt, WhileStatement):
            stmt.condition = self._optimize_expr(stmt.condition)
            stmt.body = [self._optimize_stmt(s) for s in stmt.body]
        elif isinstance(stmt, ForeachStatement):
            stmt.iterable = self._optimize_expr(stmt.iterable)
            stmt.body = [self._optimize_stmt(s) for s in stmt.body]
        return stmt

    def _optimize_segment(self, seg: SegmentDefinition) -> SegmentDefinition:
        """优化段落定义"""
        seg.body = [self._optimize_stmt(stmt) for stmt in seg.body]
        return seg

    def _optimize_class(self, cls: ClassDefinition) -> ClassDefinition:
        """优化类定义"""
        return cls
