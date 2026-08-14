"""
光明（Light）编程语言 - 完整语法解析器（v3.0）

组合模块：将核心基类、语句解析混入和表达式解析混入组合成完整解析器。

支持完整语法：
- 变量声明：定义甲等于三。
- 条件语句：如果...那么...否则...
- 循环语句：遍历...当...
- 段落定义：《段名》段(参数):
- 管道操作符：-> 和 ，
"""

from parser_core import LightParserCore, ParseError
from parser_stmt import ParserStmtMixin
from parser_expr import ParserExprMixin

# 重新导出 AST 节点类型（确保 from light_parser_v3 import * 正常工作）
from ast_nodes_v3 import (
    ASTNode, Module, VarDecl, IfStmt, ForeachStmt, WhileStmt, 
    ReturnStmt, BreakStmt, ContinueStmt, BinaryOp, UnaryOp, NumberLiteral,
    StringLiteral, Identifier, ParagraphCall, FunctionCallExpr, Paragraph, Pipeline,
    ImportStmt, ExportStmt, ClassInstantiation, SelfAssignment,
    CompoundAssignment, IndexedCompoundAssignment, MemberAccess, IndexAccess, ClassDefinition,
    AttributeDeclaration, MethodDefinition, Parameter, TryStmt,
    ThrowStmt, ParameterList, StringInterpolation, ListComprehension,
    LambdaExpression, ListLiteral, MatchStmt, MatchCase, MatchPattern,
    DictComprehension, DestructuringAssignment, ConditionalExpression,
    WithStmt, DecoratorDefinition, DecoratorInfo, DecoratedFunction, DictLiteral, InterfaceDefinition,
    MethodSignature, IndexedAssignment, RangeExpr, SliceExpr, SetComprehension, PassStmt, AssignmentExpression,
    TupleLiteral,
    FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef,
    FFIPointerType, FFIArrayType, FFIAddressOf, FFIDereference,
    FFIPointerOffset, FFISetPointerValue, FFIAllocMemory, FFIFreeMemory,
    FFICreateArray, FFISetArrayElement, FFIGetLastError, FFIGetErrno,
    FFISetErrno, FFITryCatch,
    FFIEnumDef, FFIUnionDef, FFICreateCallback, FFIVarArgsDecl,
    FFIStructByValue, FFILibraryPath,
    FFITypedefDef, FFIBitfieldDef, FFIFuncPtrDef, FFIDebugConfig, FFIPreprocessorDef,
)


class LightParser(LightParserCore, ParserStmtMixin, ParserExprMixin):
    """光明完整语法解析器"""
    pass


__all__ = [
    'LightParser', 'ParseError',
    # AST 节点类型
    'ASTNode', 'Module', 'VarDecl', 'IfStmt', 'ForeachStmt', 'WhileStmt',
    'ReturnStmt', 'BreakStmt', 'ContinueStmt', 'BinaryOp', 'UnaryOp', 'NumberLiteral',
    'StringLiteral', 'Identifier', 'ParagraphCall', 'FunctionCallExpr', 'Paragraph', 'Pipeline',
    'ImportStmt', 'ExportStmt', 'ClassInstantiation', 'SelfAssignment',
    'CompoundAssignment', 'MemberAccess', 'IndexAccess', 'ClassDefinition',
    'AttributeDeclaration', 'MethodDefinition', 'Parameter', 'TryStmt',
    'ThrowStmt', 'ParameterList', 'StringInterpolation', 'ListComprehension',
    'LambdaExpression', 'ListLiteral', 'MatchStmt', 'MatchCase', 'MatchPattern',
    'DictComprehension', 'DestructuringAssignment', 'ConditionalExpression',
    'WithStmt', 'DecoratorDefinition', 'DecoratorInfo', 'DecoratedFunction', 'DictLiteral', 'InterfaceDefinition',
    'MethodSignature', 'IndexedAssignment', 'RangeExpr', 'SliceExpr', 'SetComprehension', 'PassStmt', 'AssignmentExpression',
    'TupleLiteral',
    'FFILoadLibrary', 'FFIFunctionDecl', 'FFIStructDef', 'FFICallbackDef',
    'FFIPointerType', 'FFIArrayType', 'FFIAddressOf', 'FFIDereference',
    'FFIPointerOffset', 'FFISetPointerValue', 'FFIAllocMemory', 'FFIFreeMemory',
    'FFICreateArray', 'FFISetArrayElement', 'FFIGetLastError', 'FFIGetErrno',
    'FFISetErrno', 'FFITryCatch',
    'FFIEnumDef', 'FFIUnionDef', 'FFICreateCallback', 'FFIVarArgsDecl',
    'FFIStructByValue', 'FFILibraryPath',
    'FFITypedefDef', 'FFIBitfieldDef', 'FFIFuncPtrDef', 'FFIDebugConfig', 'FFIPreprocessorDef',
]


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("光明完整语法解析器测试（v3.0）")
    print("=" * 60)

    test_cases = [
        # 变量声明
        ('变量声明', '定义甲等于三。'),
        ('变量声明+运算', '定义丙等于三加五。'),

        # 条件语句
        ('条件语句', '''如果甲大于十那么：
  打印甲。
结束。'''),

        # 遍历循环
        ('遍历循环', '''遍历项在列表：
  打印项。
结束。'''),

        # 段落定义
        ('段落定义', '''《计算》段(甲: 数, 乙: 数) -> 数：
  返回甲加乙。
结束。'''),

        # 管道操作
        ('管道操作', '数据 -> 过滤 -> 排序。'),
    ]

    parser = LightParser()

    passed = 0
    failed = 0

    for name, test_code in test_cases:
        print(f"\n--- 测试: {name} ---")
        print(f"代码: {test_code[:50]}...")

        try:
            result = parser.parse(test_code)
            print(f"[OK] 解析成功")
            print(f"  类型: {type(result).__name__}")
            print(f"  语句数: {len(result.statements)}")
            for i, stmt in enumerate(result.statements):
                print(f"  语句{i+1}: {type(stmt).__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 解析失败")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)