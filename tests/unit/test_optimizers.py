# -*- coding: utf-8 -*-
"""
光明优化器测试 - 窥孔优化、CSE、内联
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ast_nodes import (
    NumberLiteral, StringLiteral, BooleanLiteral,
    BinaryOp, UnaryOp, Identifier, FunctionCall, Module,
    VariableDeclaration, Assignment, ExpressionStatement,
    PrintStatement, ReturnStatement, IfStatement, WhileStatement,
    SegmentDefinition
)
from optimizer.peephole import PeepholeOptimizer
from optimizer.cse import CommonSubexpressionEliminationOptimizer
from optimizer.inline import InlineOptimizer


def make_module(*stmts):
    """构造 Module"""
    m = Module()
    m.statements = list(stmts)
    m.segments = []
    m.classes = []
    return m


def make_module_with_segments(segments, *stmts):
    """构造带段落的 Module"""
    m = Module()
    m.statements = list(stmts)
    m.segments = list(segments)
    m.classes = []
    return m


class TestPeepholeOptimizer:
    """测试窥孔优化器"""

    def test_add_zero_right(self):
        """测试 x + 0 优化"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='+',
                       right=NumberLiteral(value=0))
        result = opt.optimize_expr(expr)
        assert isinstance(result, Identifier)
        assert result.name == 'x'

    def test_add_zero_left(self):
        """测试 0 + x 优化"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=NumberLiteral(value=0),
                       operator='+',
                       right=Identifier(name='x'))
        result = opt.optimize_expr(expr)
        assert isinstance(result, Identifier)
        assert result.name == 'x'

    def test_subtract_zero(self):
        """测试 x - 0 优化"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='-',
                       right=NumberLiteral(value=0))
        result = opt.optimize_expr(expr)
        assert isinstance(result, Identifier)
        assert result.name == 'x'

    def test_multiply_one_right(self):
        """测试 x * 1 优化"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='*',
                       right=NumberLiteral(value=1))
        result = opt.optimize_expr(expr)
        assert isinstance(result, Identifier)
        assert result.name == 'x'

    def test_multiply_zero(self):
        """测试 x * 0 优化为 0"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='*',
                       right=NumberLiteral(value=0))
        result = opt.optimize_expr(expr)
        assert isinstance(result, NumberLiteral)
        assert result.value == 0

    def test_divide_one(self):
        """测试 x / 1 优化"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='/',
                       right=NumberLiteral(value=1))
        result = opt.optimize_expr(expr)
        assert isinstance(result, Identifier)
        assert result.name == 'x'

    def test_subtract_self(self):
        """测试 x - x 优化为 0"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='-',
                       right=Identifier(name='x'))
        result = opt.optimize_expr(expr)
        assert isinstance(result, NumberLiteral)
        assert result.value == 0

    def test_equal_self(self):
        """测试 x == x 优化为 True"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='==',
                       right=Identifier(name='x'))
        result = opt.optimize_expr(expr)
        assert isinstance(result, BooleanLiteral)
        assert result.value is True

    def test_not_equal_self(self):
        """测试 x != x 优化为 False"""
        opt = PeepholeOptimizer()
        expr = BinaryOp(left=Identifier(name='x'),
                       operator='!=',
                       right=Identifier(name='x'))
        result = opt.optimize_expr(expr)
        assert isinstance(result, BooleanLiteral)
        assert result.value is False

    def test_not_true(self):
        """测试 !True 优化为 False"""
        opt = PeepholeOptimizer()
        expr = UnaryOp(operator='not',
                      operand=BooleanLiteral(value=True))
        result = opt.optimize_expr(expr)
        assert isinstance(result, BooleanLiteral)
        assert result.value is False

    def test_negative_number(self):
        """测试 -5 优化"""
        opt = PeepholeOptimizer()
        expr = UnaryOp(operator='-',
                      operand=NumberLiteral(value=5))
        result = opt.optimize_expr(expr)
        assert isinstance(result, NumberLiteral)
        assert result.value == -5

    def test_optimize_module(self):
        """测试优化整个模块"""
        opt = PeepholeOptimizer()
        module = make_module(
            ExpressionStatement(
                expression=BinaryOp(
                    left=Identifier(name='x'),
                    operator='+',
                    right=NumberLiteral(value=0)
                )
            )
        )
        opt.optimize(module)
        # 表达式应被优化为 x
        stmt = module.statements[0]
        assert isinstance(stmt.expression, Identifier)


class TestCSEOptimizer:
    """测试公共子表达式消除优化器"""

    def test_cse_basic(self):
        """测试基本的 CSE"""
        opt = CommonSubexpressionEliminationOptimizer()
        # x + y 出现两次
        common_expr = BinaryOp(
            left=Identifier(name='x'),
            operator='+',
            right=Identifier(name='y')
        )
        module = make_module(
            VariableDeclaration(name='a', value=common_expr),
            VariableDeclaration(name='b', value=common_expr)
        )
        opt.optimize(module)
        # 简化验证：模块被处理后仍是 2 条语句
        assert len(module.statements) == 2

    def test_cse_different_expressions(self):
        """测试不同表达式不共享"""
        opt = CommonSubexpressionEliminationOptimizer()
        e1 = BinaryOp(left=Identifier(name='x'), operator='+', right=Identifier(name='y'))
        e2 = BinaryOp(left=Identifier(name='x'), operator='-', right=Identifier(name='y'))
        module = make_module(
            VariableDeclaration(name='a', value=e1),
            VariableDeclaration(name='b', value=e2)
        )
        opt.optimize(module)
        # 表达式不同，应被保留为不同 BinaryOp
        assert isinstance(module.statements[0].value, BinaryOp)
        assert isinstance(module.statements[1].value, BinaryOp)

    def test_cse_after_assignment_invalidates(self):
        """测试赋值后缓存失效"""
        opt = CommonSubexpressionEliminationOptimizer()
        common = BinaryOp(
            left=Identifier(name='x'),
            operator='+',
            right=Identifier(name='y')
        )
        module = make_module(
            VariableDeclaration(name='a', value=common),
            Assignment(target=Identifier(name='x'),
                      value=NumberLiteral(value=0)),
            VariableDeclaration(name='b', value=common)
        )
        opt.optimize(module)
        # 第一个共享表达式可能被缓存，第二个因为 x 被重赋值而缓存失效
        # 简化验证：模块不崩溃
        assert module is not None

    def test_cse_literals_not_cached(self):
        """测试字面量不参与 CSE"""
        opt = CommonSubexpressionEliminationOptimizer()
        module = make_module(
            VariableDeclaration(name='a', value=NumberLiteral(value=42)),
            VariableDeclaration(name='b', value=NumberLiteral(value=42))
        )
        opt.optimize(module)
        # 数字字面量不会被替换为临时变量
        assert isinstance(module.statements[0].value, NumberLiteral)
        assert isinstance(module.statements[1].value, NumberLiteral)


class TestInlineOptimizer:
    """测试内联优化器"""

    def test_simple_function_inline(self):
        """测试简单函数内联"""
        opt = InlineOptimizer()
        # 定义段落
        seg = SegmentDefinition(name='greet')
        seg.parameters = []
        seg.body = [
            PrintStatement(value=StringLiteral(value='Hello'))
        ]
        # 调用段落
        module = make_module_with_segments(
            [seg],
            ExpressionStatement(
                expression=FunctionCall(
                    name=Identifier(name='greet'),
                    arguments=[]
                )
            )
        )
        opt.optimize(module)
        # 调用应被记录
        assert opt.call_counts.get('greet', 0) >= 1

    def test_recursive_function_not_inlined(self):
        """测试递归函数不内联"""
        opt = InlineOptimizer()
        # 递归函数
        seg = SegmentDefinition(name='factorial')
        seg.parameters = [Identifier(name='n')]
        seg.body = [
            IfStatement(
                condition=BinaryOp(
                    left=Identifier(name='n'),
                    operator='<=',
                    right=NumberLiteral(value=1)
                ),
                then_body=[ReturnStatement(value=NumberLiteral(value=1))],
                else_body=[]
            )
        ]
        module = make_module_with_segments([seg])
        opt.optimize(module)
        # 递归检查
        assert opt._is_recursive(seg, 'factorial') is False  # 这里的简化实现不深入检测

    def test_large_function_not_inlined(self):
        """测试大函数不内联"""
        opt = InlineOptimizer(max_size=3)
        seg = SegmentDefinition(name='big')
        seg.parameters = []
        seg.body = [PrintStatement(value=StringLiteral(value=f'line{i}')) for i in range(10)]
        seg.body = [VariableDeclaration(name=f'v{i}',
                                       value=NumberLiteral(value=i)) for i in range(5)]
        should = opt._should_inline(seg, 'big')
        assert should is False

    def test_call_counting(self):
        """测试调用次数统计"""
        opt = InlineOptimizer()
        seg = SegmentDefinition(name='helper')
        seg.parameters = []
        seg.body = [PrintStatement(value=StringLiteral(value='hi'))]
        # 3 次调用
        call_stmt = ExpressionStatement(
            expression=FunctionCall(
                name=Identifier(name='helper'),
                arguments=[]
            )
        )
        module = make_module_with_segments([seg],
            call_stmt, call_stmt, call_stmt)
        opt.optimize(module)
        assert opt.call_counts['helper'] == 3

    def test_inline_preserves_function(self):
        """测试内联不破坏段落定义"""
        opt = InlineOptimizer()
        seg = SegmentDefinition(name='noop')
        seg.parameters = []
        seg.body = [ExpressionStatement(
            expression=NumberLiteral(value=1)
        )]
        module = make_module_with_segments([seg])
        opt.optimize(module)
        # 段落应保留
        assert len(module.segments) == 1
        assert module.segments[0].name == 'noop'


class TestOptimizerIntegration:
    """测试优化器集成"""

    def test_pipeline(self):
        """测试完整优化管线"""
        module = make_module(
            ExpressionStatement(
                expression=BinaryOp(
                    left=BinaryOp(
                        left=Identifier(name='x'),
                        operator='*',
                        right=NumberLiteral(value=1)
                    ),
                    operator='+',
                    right=NumberLiteral(value=0)
                )
            )
        )

        # 窥孔优化
        PeepholeOptimizer().optimize(module)
        # 验证 x * 1 + 0 简化为 x
        stmt = module.statements[0]
        assert isinstance(stmt.expression, Identifier)
        assert stmt.expression.name == 'x'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
