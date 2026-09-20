# Generated from LightLangParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .LightLangParser import LightLangParser
else:
    from LightLangParser import LightLangParser

from typing import List, Optional, Tuple, Any, Union


# This class defines a complete generic visitor for a parse tree produced by LightLangParser.

class LightLangParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by LightLangParser#program.
    def visitProgram(self, ctx:LightLangParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#moduleDecl.
    def visitModuleDecl(self, ctx:LightLangParser.ModuleDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#definition.
    def visitDefinition(self, ctx:LightLangParser.DefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#paragraphDef.
    def visitParagraphDef(self, ctx:LightLangParser.ParagraphDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#block.
    def visitBlock(self, ctx:LightLangParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#blockContent.
    def visitBlockContent(self, ctx:LightLangParser.BlockContentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#classDef.
    def visitClassDef(self, ctx:LightLangParser.ClassDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#genericParams.
    def visitGenericParams(self, ctx:LightLangParser.GenericParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#classMember.
    def visitClassMember(self, ctx:LightLangParser.ClassMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#methodDef.
    def visitMethodDef(self, ctx:LightLangParser.MethodDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#constructorDef.
    def visitConstructorDef(self, ctx:LightLangParser.ConstructorDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#attributeDecl.
    def visitAttributeDecl(self, ctx:LightLangParser.AttributeDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#interfaceDef.
    def visitInterfaceDef(self, ctx:LightLangParser.InterfaceDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#interfaceMember.
    def visitInterfaceMember(self, ctx:LightLangParser.InterfaceMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#paramList.
    def visitParamList(self, ctx:LightLangParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#param.
    def visitParam(self, ctx:LightLangParser.ParamContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#typeMark.
    def visitTypeMark(self, ctx:LightLangParser.TypeMarkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dataTypeDef.
    def visitDataTypeDef(self, ctx:LightLangParser.DataTypeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dataTypeField.
    def visitDataTypeField(self, ctx:LightLangParser.DataTypeFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#errorTypeDef.
    def visitErrorTypeDef(self, ctx:LightLangParser.ErrorTypeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#importStmt.
    def visitImportStmt(self, ctx:LightLangParser.ImportStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#exportStmt.
    def visitExportStmt(self, ctx:LightLangParser.ExportStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#path.
    def visitPath(self, ctx:LightLangParser.PathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#importList.
    def visitImportList(self, ctx:LightLangParser.ImportListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#importItem.
    def visitImportItem(self, ctx:LightLangParser.ImportItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#stmt.
    def visitStmt(self, ctx:LightLangParser.StmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#varDecl.
    def visitVarDecl(self, ctx:LightLangParser.VarDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#assignStmt.
    def visitAssignStmt(self, ctx:LightLangParser.AssignStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#compoundAssignStmt.
    def visitCompoundAssignStmt(self, ctx:LightLangParser.CompoundAssignStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#compoundAssignOp.
    def visitCompoundAssignOp(self, ctx:LightLangParser.CompoundAssignOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#ifStmt.
    def visitIfStmt(self, ctx:LightLangParser.IfStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#foreachStmt.
    def visitForeachStmt(self, ctx:LightLangParser.ForeachStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#foreachVar.
    def visitForeachVar(self, ctx:LightLangParser.ForeachVarContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#whileStmt.
    def visitWhileStmt(self, ctx:LightLangParser.WhileStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#returnStmt.
    def visitReturnStmt(self, ctx:LightLangParser.ReturnStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#breakStmt.
    def visitBreakStmt(self, ctx:LightLangParser.BreakStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#continueStmt.
    def visitContinueStmt(self, ctx:LightLangParser.ContinueStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#tryStmt.
    def visitTryStmt(self, ctx:LightLangParser.TryStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#throwStmt.
    def visitThrowStmt(self, ctx:LightLangParser.ThrowStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#matchStmt.
    def visitMatchStmt(self, ctx:LightLangParser.MatchStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#matchCase.
    def visitMatchCase(self, ctx:LightLangParser.MatchCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#matchPattern.
    def visitMatchPattern(self, ctx:LightLangParser.MatchPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#matchPatternList.
    def visitMatchPatternList(self, ctx:LightLangParser.MatchPatternListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#printStmt.
    def visitPrintStmt(self, ctx:LightLangParser.PrintStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#withStmt.
    def visitWithStmt(self, ctx:LightLangParser.WithStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#decoratorDef.
    def visitDecoratorDef(self, ctx:LightLangParser.DecoratorDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#exprStmt.
    def visitExprStmt(self, ctx:LightLangParser.ExprStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#expr.
    def visitExpr(self, ctx:LightLangParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#pipelineExpr.
    def visitPipelineExpr(self, ctx:LightLangParser.PipelineExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#andExpr.
    def visitAndExpr(self, ctx:LightLangParser.AndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#orExpr.
    def visitOrExpr(self, ctx:LightLangParser.OrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#comparisonExpr.
    def visitComparisonExpr(self, ctx:LightLangParser.ComparisonExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#compOp.
    def visitCompOp(self, ctx:LightLangParser.CompOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#comparisonKTo.
    def visitComparisonKTo(self, ctx:LightLangParser.ComparisonKToContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#additiveExpr.
    def visitAdditiveExpr(self, ctx:LightLangParser.AdditiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#addOp.
    def visitAddOp(self, ctx:LightLangParser.AddOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx:LightLangParser.MultiplicativeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#multOp.
    def visitMultOp(self, ctx:LightLangParser.MultOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#unaryExpr.
    def visitUnaryExpr(self, ctx:LightLangParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#postfixExpr.
    def visitPostfixExpr(self, ctx:LightLangParser.PostfixExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#memberName.
    def visitMemberName(self, ctx:LightLangParser.MemberNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#primary.
    def visitPrimary(self, ctx:LightLangParser.PrimaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#implicitCall.
    def visitImplicitCall(self, ctx:LightLangParser.ImplicitCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#implicitArg.
    def visitImplicitArg(self, ctx:LightLangParser.ImplicitArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dictLiteral.
    def visitDictLiteral(self, ctx:LightLangParser.DictLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dictEntry.
    def visitDictEntry(self, ctx:LightLangParser.DictEntryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#listComprehension.
    def visitListComprehension(self, ctx:LightLangParser.ListComprehensionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#identifier_like.
    def visitIdentifier_like(self, ctx:LightLangParser.Identifier_likeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#typeAsIdentifier.
    def visitTypeAsIdentifier(self, ctx:LightLangParser.TypeAsIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#lambdaExpr.
    def visitLambdaExpr(self, ctx:LightLangParser.LambdaExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dictComprehension.
    def visitDictComprehension(self, ctx:LightLangParser.DictComprehensionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#bracketContent.
    def visitBracketContent(self, ctx:LightLangParser.BracketContentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#dictContent.
    def visitDictContent(self, ctx:LightLangParser.DictContentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#typeAnnotation.
    def visitTypeAnnotation(self, ctx:LightLangParser.TypeAnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#builtinType.
    def visitBuiltinType(self, ctx:LightLangParser.BuiltinTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#exprList.
    def visitExprList(self, ctx:LightLangParser.ExprListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LightLangParser#conditionalExpr.
    def visitConditionalExpr(self, ctx:LightLangParser.ConditionalExprContext):
        return self.visitChildren(ctx)



del LightLangParser