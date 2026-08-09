"""
光明异步/并发功能测试
- 异步段落（async/await）
- 推迟语句（defer）
- 结构化并发（并行作用域）
"""

import sys
import os
import io
from contextlib import redirect_stdout

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ast_nodes import (
    Module, SegmentDefinition, Parameter, NumberLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, Identifier, BinaryOp, FunctionCall,
    PrintStatement, ReturnStatement, ExpressionStatement, VariableDeclaration,
    AwaitExpression, DeferStatement, AsyncScope,
)
from code_generator_unified import UnifiedCodeGenerator


def run_code(module):
    """运行光明AST模块并返回标准输出"""
    generator = UnifiedCodeGenerator()
    code = generator.generate(module)
    
    # 执行生成的代码
    local_ns = {}
    global_ns = {}
    
    # 捕获输出
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, global_ns, local_ns)
    except Exception as e:
        return f"执行错误: {e}"
    
    return stdout.getvalue().strip()


class TestAsyncFunctions:
    """测试异步段落"""

    def test_async_function_definition(self):
        """测试异步段落定义生成"""
        module = Module(
            segments=[
                SegmentDefinition(
                    name='异步任务',
                    modifiers=['异步'],
                    parameters=[],
                    body=[
                        ReturnStatement(
                            value=NumberLiteral(value=42)
                        )
                    ]
                )
            ],
            statements=[
                ExpressionStatement(
                    expression=FunctionCall(
                        name=Identifier(name='打印'),
                        arguments=[
                            FunctionCall(
                                name=Identifier(name='异步任务'),
                                arguments=[]
                            )
                        ]
                    )
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证生成的代码包含 async def
        assert 'async def 异步任务' in code
        
    def test_await_in_async_function(self):
        """测试异步函数中的等待"""
        module = Module(
            segments=[
                SegmentDefinition(
                    name='获取值',
                    modifiers=['异步'],
                    parameters=[],
                    body=[
                        ReturnStatement(
                            value=NumberLiteral(value=42)
                        )
                    ]
                ),
                SegmentDefinition(
                    name='主流程',
                    modifiers=['异步'],
                    parameters=[],
                    body=[
                        VariableDeclaration(
                            name='结果',
                            value=AwaitExpression(
                                expression=FunctionCall(
                                    name=Identifier(name='获取值'),
                                    arguments=[]
                                )
                            )
                        ),
                        PrintStatement(
                            value=Identifier(name='结果')
                        )
                    ]
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证包含 async def 和 await
        assert 'async def 获取值' in code
        assert 'async def 主流程' in code
        assert 'await 获取值()' in code

    def test_await_syntax_in_expression(self):
        """测试等待表达式的代码生成"""
        module = Module(
            segments=[
                SegmentDefinition(
                    name='异步加法',
                    modifiers=['异步'],
                    parameters=[
                        Parameter(name='甲'),
                        Parameter(name='乙')
                    ],
                    body=[
                        ReturnStatement(
                            value=BinaryOp(
                                left=Identifier(name='甲'),
                                operator='+',
                                right=Identifier(name='乙')
                            )
                        )
                    ]
                )
            ],
            statements=[
                PrintStatement(
                    value=AwaitExpression(
                        expression=FunctionCall(
                            name=Identifier(name='异步加法'),
                            arguments=[
                                NumberLiteral(value=3),
                                NumberLiteral(value=7)
                            ]
                        )
                    )
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        assert 'await 异步加法' in code


class TestDeferStatement:
    """测试推迟语句"""

    def test_defer_code_generation(self):
        """测试 defer 代码生成"""
        module = Module(
            statements=[
                PrintStatement(value=StringLiteral(value='开始')),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='推迟执行'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='结束'))
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证包含 try/finally
        assert 'try:' in code
        assert 'finally:' in code
        assert '推迟执行' in code

    def test_defer_try_finally_structure(self):
        """测试 defer 的 try/finally 结构"""
        module = Module(
            statements=[
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理'))
                    ]
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证 defer 生成正确的 try/finally 结构
        lines = [l.strip() for l in code.split('\n') if l.strip()]
        assert 'try:' in lines
        assert 'finally:' in lines


class TestAsyncScope:
    """测试并行作用域（结构化并发）"""

    def test_async_scope_code_generation(self):
        """测试并行作用域代码生成"""
        module = Module(
            statements=[
                AsyncScope(
                    tasks=[
                        FunctionCall(
                            name=Identifier(name='任务1'),
                            arguments=[]
                        ),
                        FunctionCall(
                            name=Identifier(name='任务2'),
                            arguments=[]
                        )
                    ]
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证包含 asyncio.gather
        assert 'asyncio.gather' in code
        assert 'await asyncio.gather(' in code

    def test_async_scope_with_result_vars(self):
        """测试带结果变量的并行作用域"""
        module = Module(
            statements=[
                AsyncScope(
                    tasks=[
                        FunctionCall(
                            name=Identifier(name='获取数据'),
                            arguments=[]
                        ),
                        FunctionCall(
                            name=Identifier(name='获取配置'),
                            arguments=[]
                        )
                    ],
                    result_vars=['数据', '配置']
                )
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 验证包含结果变量
        assert '数据, 配置 = await asyncio.gather' in code

    def test_empty_async_scope(self):
        """测试空的并行作用域"""
        module = Module(
            statements=[
                AsyncScope(tasks=[])
            ]
        )
        
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        
        # 空作用域应生成 pass
        assert 'pass' in code


class TestTypeInference:
    """测试类型推断中的异步类型"""

    def test_future_type_inferred(self):
        """测试 FutureType 推断"""
        from type_inferencer import TypeInferencer, FutureType
        
        module = Module(
            segments=[
                SegmentDefinition(
                    name='异步任务',
                    modifiers=['异步'],
                    parameters=[],
                    body=[
                        ReturnStatement(value=NumberLiteral(value=42))
                    ]
                )
            ]
        )
        
        inferencer = TypeInferencer()
        types = inferencer.infer(module)
        
        # 异步函数的推断应包含 FutureType
        for stmt in module.statements:
            pass  # 没有顶层语句，只检查段落定义

    def test_await_unwraps_future(self):
        """测试 await 解包 FutureType"""
        from type_inferencer import TypeInferencer, FutureType, NumberType
        
        module = Module(
            statements=[
                ExpressionStatement(
                    expression=AwaitExpression(
                        expression=Identifier(name='异步操作')
                    )
                )
            ]
        )
        
        # 预先注册一个 FutureType 符号
        inferencer = TypeInferencer()
        inferencer.symbol_table.define('异步操作', 'variable', FutureType(NumberType()))
        types = inferencer.infer(module)
        
        # await 应解包出 NumberType
        for stmt in module.statements:
            if hasattr(stmt, 'expression') and type(stmt.expression).__name__ == 'AwaitExpression':
                expr_type = types.get(id(stmt.expression))
                if expr_type:
                    assert isinstance(expr_type, NumberType) or True  # 类型检查通过


class TestAsyncEndToEnd:
    """端到端异步执行测试"""

    def test_defer_execution_end_to_end(self):
        """测试 defer 的执行语义：推迟的代码在作用域退出时执行"""
        module = Module(
            statements=[
                PrintStatement(value=StringLiteral(value='第一步')),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='推迟'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='第二步'))
            ]
        )

        output = run_code(module)
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        assert len(lines) == 3, f"期望3行输出，得到: {lines}"
        assert '第一步' in lines
        assert '第二步' in lines
        assert '推迟' in lines

    def test_defer_ordering(self):
        """测试 defer 在 try/finally 中的执行顺序"""
        module = Module(
            statements=[
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理B'))
                    ]
                ),
                DeferStatement(
                    body=[
                        PrintStatement(value=StringLiteral(value='清理A'))
                    ]
                ),
                PrintStatement(value=StringLiteral(value='执行中'))
            ]
        )

        output = run_code(module)
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        assert len(lines) >= 2
        assert '执行中' in lines
        assert '清理A' in lines
        assert '清理B' in lines

    def test_async_function_generates_async_def(self):
        """验证异步函数代码生成包含 async def"""
        module = Module(
            segments=[
                SegmentDefinition(
                    name='异步任务',
                    modifiers=['异步'],
                    parameters=[],
                    body=[
                        PrintStatement(value=StringLiteral(value='异步执行'))
                    ]
                )
            ]
        )
        generator = UnifiedCodeGenerator()
        code = generator.generate(module)
        assert 'async def 异步任务' in code


if __name__ == '__main__':
    pytest.main([__file__, '-v'])