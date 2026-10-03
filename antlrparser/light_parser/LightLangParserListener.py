# Generated from LightLangParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .LightLangParser import LightLangParser
else:
    from LightLangParser import LightLangParser

from typing import List, Optional, Tuple, Any, Union


# This class defines a complete listener for a parse tree produced by LightLangParser.
class LightLangParserListener(ParseTreeListener):

    # Enter a parse tree produced by LightLangParser#program.
    def enterProgram(self, ctx:LightLangParser.ProgramContext):
        pass

    # Exit a parse tree produced by LightLangParser#program.
    def exitProgram(self, ctx:LightLangParser.ProgramContext):
        pass


    # Enter a parse tree produced by LightLangParser#moduleDecl.
    def enterModuleDecl(self, ctx:LightLangParser.ModuleDeclContext):
        pass

    # Exit a parse tree produced by LightLangParser#moduleDecl.
    def exitModuleDecl(self, ctx:LightLangParser.ModuleDeclContext):
        pass


    # Enter a parse tree produced by LightLangParser#definition.
    def enterDefinition(self, ctx:LightLangParser.DefinitionContext):
        pass

    # Exit a parse tree produced by LightLangParser#definition.
    def exitDefinition(self, ctx:LightLangParser.DefinitionContext):
        pass


    # Enter a parse tree produced by LightLangParser#paragraphDef.
    def enterParagraphDef(self, ctx:LightLangParser.ParagraphDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#paragraphDef.
    def exitParagraphDef(self, ctx:LightLangParser.ParagraphDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#block.
    def enterBlock(self, ctx:LightLangParser.BlockContext):
        pass

    # Exit a parse tree produced by LightLangParser#block.
    def exitBlock(self, ctx:LightLangParser.BlockContext):
        pass


    # Enter a parse tree produced by LightLangParser#blockContent.
    def enterBlockContent(self, ctx:LightLangParser.BlockContentContext):
        pass

    # Exit a parse tree produced by LightLangParser#blockContent.
    def exitBlockContent(self, ctx:LightLangParser.BlockContentContext):
        pass


    # Enter a parse tree produced by LightLangParser#classDef.
    def enterClassDef(self, ctx:LightLangParser.ClassDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#classDef.
    def exitClassDef(self, ctx:LightLangParser.ClassDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#genericParams.
    def enterGenericParams(self, ctx:LightLangParser.GenericParamsContext):
        pass

    # Exit a parse tree produced by LightLangParser#genericParams.
    def exitGenericParams(self, ctx:LightLangParser.GenericParamsContext):
        pass


    # Enter a parse tree produced by LightLangParser#classMember.
    def enterClassMember(self, ctx:LightLangParser.ClassMemberContext):
        pass

    # Exit a parse tree produced by LightLangParser#classMember.
    def exitClassMember(self, ctx:LightLangParser.ClassMemberContext):
        pass


    # Enter a parse tree produced by LightLangParser#methodDef.
    def enterMethodDef(self, ctx:LightLangParser.MethodDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#methodDef.
    def exitMethodDef(self, ctx:LightLangParser.MethodDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#constructorDef.
    def enterConstructorDef(self, ctx:LightLangParser.ConstructorDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#constructorDef.
    def exitConstructorDef(self, ctx:LightLangParser.ConstructorDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#attributeDecl.
    def enterAttributeDecl(self, ctx:LightLangParser.AttributeDeclContext):
        pass

    # Exit a parse tree produced by LightLangParser#attributeDecl.
    def exitAttributeDecl(self, ctx:LightLangParser.AttributeDeclContext):
        pass


    # Enter a parse tree produced by LightLangParser#interfaceDef.
    def enterInterfaceDef(self, ctx:LightLangParser.InterfaceDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#interfaceDef.
    def exitInterfaceDef(self, ctx:LightLangParser.InterfaceDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#interfaceMember.
    def enterInterfaceMember(self, ctx:LightLangParser.InterfaceMemberContext):
        pass

    # Exit a parse tree produced by LightLangParser#interfaceMember.
    def exitInterfaceMember(self, ctx:LightLangParser.InterfaceMemberContext):
        pass


    # Enter a parse tree produced by LightLangParser#paramList.
    def enterParamList(self, ctx:LightLangParser.ParamListContext):
        pass

    # Exit a parse tree produced by LightLangParser#paramList.
    def exitParamList(self, ctx:LightLangParser.ParamListContext):
        pass


    # Enter a parse tree produced by LightLangParser#param.
    def enterParam(self, ctx:LightLangParser.ParamContext):
        pass

    # Exit a parse tree produced by LightLangParser#param.
    def exitParam(self, ctx:LightLangParser.ParamContext):
        pass


    # Enter a parse tree produced by LightLangParser#typeMark.
    def enterTypeMark(self, ctx:LightLangParser.TypeMarkContext):
        pass

    # Exit a parse tree produced by LightLangParser#typeMark.
    def exitTypeMark(self, ctx:LightLangParser.TypeMarkContext):
        pass


    # Enter a parse tree produced by LightLangParser#dataTypeDef.
    def enterDataTypeDef(self, ctx:LightLangParser.DataTypeDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#dataTypeDef.
    def exitDataTypeDef(self, ctx:LightLangParser.DataTypeDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#dataTypeField.
    def enterDataTypeField(self, ctx:LightLangParser.DataTypeFieldContext):
        pass

    # Exit a parse tree produced by LightLangParser#dataTypeField.
    def exitDataTypeField(self, ctx:LightLangParser.DataTypeFieldContext):
        pass


    # Enter a parse tree produced by LightLangParser#errorTypeDef.
    def enterErrorTypeDef(self, ctx:LightLangParser.ErrorTypeDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#errorTypeDef.
    def exitErrorTypeDef(self, ctx:LightLangParser.ErrorTypeDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#importStmt.
    def enterImportStmt(self, ctx:LightLangParser.ImportStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#importStmt.
    def exitImportStmt(self, ctx:LightLangParser.ImportStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#exportStmt.
    def enterExportStmt(self, ctx:LightLangParser.ExportStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#exportStmt.
    def exitExportStmt(self, ctx:LightLangParser.ExportStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#path.
    def enterPath(self, ctx:LightLangParser.PathContext):
        pass

    # Exit a parse tree produced by LightLangParser#path.
    def exitPath(self, ctx:LightLangParser.PathContext):
        pass


    # Enter a parse tree produced by LightLangParser#importList.
    def enterImportList(self, ctx:LightLangParser.ImportListContext):
        pass

    # Exit a parse tree produced by LightLangParser#importList.
    def exitImportList(self, ctx:LightLangParser.ImportListContext):
        pass


    # Enter a parse tree produced by LightLangParser#importItem.
    def enterImportItem(self, ctx:LightLangParser.ImportItemContext):
        pass

    # Exit a parse tree produced by LightLangParser#importItem.
    def exitImportItem(self, ctx:LightLangParser.ImportItemContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiLoadLibrary.
    def enterFfiLoadLibrary(self, ctx:LightLangParser.FfiLoadLibraryContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiLoadLibrary.
    def exitFfiLoadLibrary(self, ctx:LightLangParser.FfiLoadLibraryContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiFunctionDecl.
    def enterFfiFunctionDecl(self, ctx:LightLangParser.FfiFunctionDeclContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiFunctionDecl.
    def exitFfiFunctionDecl(self, ctx:LightLangParser.FfiFunctionDeclContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiParamList.
    def enterFfiParamList(self, ctx:LightLangParser.FfiParamListContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiParamList.
    def exitFfiParamList(self, ctx:LightLangParser.FfiParamListContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiParam.
    def enterFfiParam(self, ctx:LightLangParser.FfiParamContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiParam.
    def exitFfiParam(self, ctx:LightLangParser.FfiParamContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiLibraryAlias.
    def enterFfiLibraryAlias(self, ctx:LightLangParser.FfiLibraryAliasContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiLibraryAlias.
    def exitFfiLibraryAlias(self, ctx:LightLangParser.FfiLibraryAliasContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiStructDef.
    def enterFfiStructDef(self, ctx:LightLangParser.FfiStructDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiStructDef.
    def exitFfiStructDef(self, ctx:LightLangParser.FfiStructDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiFieldList.
    def enterFfiFieldList(self, ctx:LightLangParser.FfiFieldListContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiFieldList.
    def exitFfiFieldList(self, ctx:LightLangParser.FfiFieldListContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiField.
    def enterFfiField(self, ctx:LightLangParser.FfiFieldContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiField.
    def exitFfiField(self, ctx:LightLangParser.FfiFieldContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiCallbackDef.
    def enterFfiCallbackDef(self, ctx:LightLangParser.FfiCallbackDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiCallbackDef.
    def exitFfiCallbackDef(self, ctx:LightLangParser.FfiCallbackDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiEnumDef.
    def enterFfiEnumDef(self, ctx:LightLangParser.FfiEnumDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiEnumDef.
    def exitFfiEnumDef(self, ctx:LightLangParser.FfiEnumDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiEnumMemberList.
    def enterFfiEnumMemberList(self, ctx:LightLangParser.FfiEnumMemberListContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiEnumMemberList.
    def exitFfiEnumMemberList(self, ctx:LightLangParser.FfiEnumMemberListContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiEnumMember.
    def enterFfiEnumMember(self, ctx:LightLangParser.FfiEnumMemberContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiEnumMember.
    def exitFfiEnumMember(self, ctx:LightLangParser.FfiEnumMemberContext):
        pass


    # Enter a parse tree produced by LightLangParser#ffiVarArgsDecl.
    def enterFfiVarArgsDecl(self, ctx:LightLangParser.FfiVarArgsDeclContext):
        pass

    # Exit a parse tree produced by LightLangParser#ffiVarArgsDecl.
    def exitFfiVarArgsDecl(self, ctx:LightLangParser.FfiVarArgsDeclContext):
        pass


    # Enter a parse tree produced by LightLangParser#stmt.
    def enterStmt(self, ctx:LightLangParser.StmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#stmt.
    def exitStmt(self, ctx:LightLangParser.StmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#varDecl.
    def enterVarDecl(self, ctx:LightLangParser.VarDeclContext):
        pass

    # Exit a parse tree produced by LightLangParser#varDecl.
    def exitVarDecl(self, ctx:LightLangParser.VarDeclContext):
        pass


    # Enter a parse tree produced by LightLangParser#assignStmt.
    def enterAssignStmt(self, ctx:LightLangParser.AssignStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#assignStmt.
    def exitAssignStmt(self, ctx:LightLangParser.AssignStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#compoundAssignStmt.
    def enterCompoundAssignStmt(self, ctx:LightLangParser.CompoundAssignStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#compoundAssignStmt.
    def exitCompoundAssignStmt(self, ctx:LightLangParser.CompoundAssignStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#compoundAssignOp.
    def enterCompoundAssignOp(self, ctx:LightLangParser.CompoundAssignOpContext):
        pass

    # Exit a parse tree produced by LightLangParser#compoundAssignOp.
    def exitCompoundAssignOp(self, ctx:LightLangParser.CompoundAssignOpContext):
        pass


    # Enter a parse tree produced by LightLangParser#ifStmt.
    def enterIfStmt(self, ctx:LightLangParser.IfStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#ifStmt.
    def exitIfStmt(self, ctx:LightLangParser.IfStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#foreachStmt.
    def enterForeachStmt(self, ctx:LightLangParser.ForeachStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#foreachStmt.
    def exitForeachStmt(self, ctx:LightLangParser.ForeachStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#foreachVar.
    def enterForeachVar(self, ctx:LightLangParser.ForeachVarContext):
        pass

    # Exit a parse tree produced by LightLangParser#foreachVar.
    def exitForeachVar(self, ctx:LightLangParser.ForeachVarContext):
        pass


    # Enter a parse tree produced by LightLangParser#whileStmt.
    def enterWhileStmt(self, ctx:LightLangParser.WhileStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#whileStmt.
    def exitWhileStmt(self, ctx:LightLangParser.WhileStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#returnStmt.
    def enterReturnStmt(self, ctx:LightLangParser.ReturnStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#returnStmt.
    def exitReturnStmt(self, ctx:LightLangParser.ReturnStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#breakStmt.
    def enterBreakStmt(self, ctx:LightLangParser.BreakStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#breakStmt.
    def exitBreakStmt(self, ctx:LightLangParser.BreakStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#continueStmt.
    def enterContinueStmt(self, ctx:LightLangParser.ContinueStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#continueStmt.
    def exitContinueStmt(self, ctx:LightLangParser.ContinueStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#tryStmt.
    def enterTryStmt(self, ctx:LightLangParser.TryStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#tryStmt.
    def exitTryStmt(self, ctx:LightLangParser.TryStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#catchSpec.
    def enterCatchSpec(self, ctx:LightLangParser.CatchSpecContext):
        pass

    # Exit a parse tree produced by LightLangParser#catchSpec.
    def exitCatchSpec(self, ctx:LightLangParser.CatchSpecContext):
        pass


    # Enter a parse tree produced by LightLangParser#identifier_or_type.
    def enterIdentifier_or_type(self, ctx:LightLangParser.Identifier_or_typeContext):
        pass

    # Exit a parse tree produced by LightLangParser#identifier_or_type.
    def exitIdentifier_or_type(self, ctx:LightLangParser.Identifier_or_typeContext):
        pass


    # Enter a parse tree produced by LightLangParser#throwStmt.
    def enterThrowStmt(self, ctx:LightLangParser.ThrowStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#throwStmt.
    def exitThrowStmt(self, ctx:LightLangParser.ThrowStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#matchStmt.
    def enterMatchStmt(self, ctx:LightLangParser.MatchStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#matchStmt.
    def exitMatchStmt(self, ctx:LightLangParser.MatchStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#matchCase.
    def enterMatchCase(self, ctx:LightLangParser.MatchCaseContext):
        pass

    # Exit a parse tree produced by LightLangParser#matchCase.
    def exitMatchCase(self, ctx:LightLangParser.MatchCaseContext):
        pass


    # Enter a parse tree produced by LightLangParser#matchPattern.
    def enterMatchPattern(self, ctx:LightLangParser.MatchPatternContext):
        pass

    # Exit a parse tree produced by LightLangParser#matchPattern.
    def exitMatchPattern(self, ctx:LightLangParser.MatchPatternContext):
        pass


    # Enter a parse tree produced by LightLangParser#matchPatternList.
    def enterMatchPatternList(self, ctx:LightLangParser.MatchPatternListContext):
        pass

    # Exit a parse tree produced by LightLangParser#matchPatternList.
    def exitMatchPatternList(self, ctx:LightLangParser.MatchPatternListContext):
        pass


    # Enter a parse tree produced by LightLangParser#printStmt.
    def enterPrintStmt(self, ctx:LightLangParser.PrintStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#printStmt.
    def exitPrintStmt(self, ctx:LightLangParser.PrintStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#withStmt.
    def enterWithStmt(self, ctx:LightLangParser.WithStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#withStmt.
    def exitWithStmt(self, ctx:LightLangParser.WithStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#decoratorDef.
    def enterDecoratorDef(self, ctx:LightLangParser.DecoratorDefContext):
        pass

    # Exit a parse tree produced by LightLangParser#decoratorDef.
    def exitDecoratorDef(self, ctx:LightLangParser.DecoratorDefContext):
        pass


    # Enter a parse tree produced by LightLangParser#exprStmt.
    def enterExprStmt(self, ctx:LightLangParser.ExprStmtContext):
        pass

    # Exit a parse tree produced by LightLangParser#exprStmt.
    def exitExprStmt(self, ctx:LightLangParser.ExprStmtContext):
        pass


    # Enter a parse tree produced by LightLangParser#expr.
    def enterExpr(self, ctx:LightLangParser.ExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#expr.
    def exitExpr(self, ctx:LightLangParser.ExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#pipelineExpr.
    def enterPipelineExpr(self, ctx:LightLangParser.PipelineExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#pipelineExpr.
    def exitPipelineExpr(self, ctx:LightLangParser.PipelineExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#andExpr.
    def enterAndExpr(self, ctx:LightLangParser.AndExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#andExpr.
    def exitAndExpr(self, ctx:LightLangParser.AndExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#orExpr.
    def enterOrExpr(self, ctx:LightLangParser.OrExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#orExpr.
    def exitOrExpr(self, ctx:LightLangParser.OrExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#comparisonExpr.
    def enterComparisonExpr(self, ctx:LightLangParser.ComparisonExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#comparisonExpr.
    def exitComparisonExpr(self, ctx:LightLangParser.ComparisonExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#compOp.
    def enterCompOp(self, ctx:LightLangParser.CompOpContext):
        pass

    # Exit a parse tree produced by LightLangParser#compOp.
    def exitCompOp(self, ctx:LightLangParser.CompOpContext):
        pass


    # Enter a parse tree produced by LightLangParser#comparisonKTo.
    def enterComparisonKTo(self, ctx:LightLangParser.ComparisonKToContext):
        pass

    # Exit a parse tree produced by LightLangParser#comparisonKTo.
    def exitComparisonKTo(self, ctx:LightLangParser.ComparisonKToContext):
        pass


    # Enter a parse tree produced by LightLangParser#additiveExpr.
    def enterAdditiveExpr(self, ctx:LightLangParser.AdditiveExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#additiveExpr.
    def exitAdditiveExpr(self, ctx:LightLangParser.AdditiveExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#addOp.
    def enterAddOp(self, ctx:LightLangParser.AddOpContext):
        pass

    # Exit a parse tree produced by LightLangParser#addOp.
    def exitAddOp(self, ctx:LightLangParser.AddOpContext):
        pass


    # Enter a parse tree produced by LightLangParser#multiplicativeExpr.
    def enterMultiplicativeExpr(self, ctx:LightLangParser.MultiplicativeExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#multiplicativeExpr.
    def exitMultiplicativeExpr(self, ctx:LightLangParser.MultiplicativeExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#multOp.
    def enterMultOp(self, ctx:LightLangParser.MultOpContext):
        pass

    # Exit a parse tree produced by LightLangParser#multOp.
    def exitMultOp(self, ctx:LightLangParser.MultOpContext):
        pass


    # Enter a parse tree produced by LightLangParser#unaryExpr.
    def enterUnaryExpr(self, ctx:LightLangParser.UnaryExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#unaryExpr.
    def exitUnaryExpr(self, ctx:LightLangParser.UnaryExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#postfixExpr.
    def enterPostfixExpr(self, ctx:LightLangParser.PostfixExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#postfixExpr.
    def exitPostfixExpr(self, ctx:LightLangParser.PostfixExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#memberName.
    def enterMemberName(self, ctx:LightLangParser.MemberNameContext):
        pass

    # Exit a parse tree produced by LightLangParser#memberName.
    def exitMemberName(self, ctx:LightLangParser.MemberNameContext):
        pass


    # Enter a parse tree produced by LightLangParser#primary.
    def enterPrimary(self, ctx:LightLangParser.PrimaryContext):
        pass

    # Exit a parse tree produced by LightLangParser#primary.
    def exitPrimary(self, ctx:LightLangParser.PrimaryContext):
        pass


    # Enter a parse tree produced by LightLangParser#implicitCall.
    def enterImplicitCall(self, ctx:LightLangParser.ImplicitCallContext):
        pass

    # Exit a parse tree produced by LightLangParser#implicitCall.
    def exitImplicitCall(self, ctx:LightLangParser.ImplicitCallContext):
        pass


    # Enter a parse tree produced by LightLangParser#implicitArg.
    def enterImplicitArg(self, ctx:LightLangParser.ImplicitArgContext):
        pass

    # Exit a parse tree produced by LightLangParser#implicitArg.
    def exitImplicitArg(self, ctx:LightLangParser.ImplicitArgContext):
        pass


    # Enter a parse tree produced by LightLangParser#dictLiteral.
    def enterDictLiteral(self, ctx:LightLangParser.DictLiteralContext):
        pass

    # Exit a parse tree produced by LightLangParser#dictLiteral.
    def exitDictLiteral(self, ctx:LightLangParser.DictLiteralContext):
        pass


    # Enter a parse tree produced by LightLangParser#dictEntry.
    def enterDictEntry(self, ctx:LightLangParser.DictEntryContext):
        pass

    # Exit a parse tree produced by LightLangParser#dictEntry.
    def exitDictEntry(self, ctx:LightLangParser.DictEntryContext):
        pass


    # Enter a parse tree produced by LightLangParser#listComprehension.
    def enterListComprehension(self, ctx:LightLangParser.ListComprehensionContext):
        pass

    # Exit a parse tree produced by LightLangParser#listComprehension.
    def exitListComprehension(self, ctx:LightLangParser.ListComprehensionContext):
        pass


    # Enter a parse tree produced by LightLangParser#identifier_like.
    def enterIdentifier_like(self, ctx:LightLangParser.Identifier_likeContext):
        pass

    # Exit a parse tree produced by LightLangParser#identifier_like.
    def exitIdentifier_like(self, ctx:LightLangParser.Identifier_likeContext):
        pass


    # Enter a parse tree produced by LightLangParser#typeAsIdentifier.
    def enterTypeAsIdentifier(self, ctx:LightLangParser.TypeAsIdentifierContext):
        pass

    # Exit a parse tree produced by LightLangParser#typeAsIdentifier.
    def exitTypeAsIdentifier(self, ctx:LightLangParser.TypeAsIdentifierContext):
        pass


    # Enter a parse tree produced by LightLangParser#lambdaExpr.
    def enterLambdaExpr(self, ctx:LightLangParser.LambdaExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#lambdaExpr.
    def exitLambdaExpr(self, ctx:LightLangParser.LambdaExprContext):
        pass


    # Enter a parse tree produced by LightLangParser#dictComprehension.
    def enterDictComprehension(self, ctx:LightLangParser.DictComprehensionContext):
        pass

    # Exit a parse tree produced by LightLangParser#dictComprehension.
    def exitDictComprehension(self, ctx:LightLangParser.DictComprehensionContext):
        pass


    # Enter a parse tree produced by LightLangParser#bracketContent.
    def enterBracketContent(self, ctx:LightLangParser.BracketContentContext):
        pass

    # Exit a parse tree produced by LightLangParser#bracketContent.
    def exitBracketContent(self, ctx:LightLangParser.BracketContentContext):
        pass


    # Enter a parse tree produced by LightLangParser#dictContent.
    def enterDictContent(self, ctx:LightLangParser.DictContentContext):
        pass

    # Exit a parse tree produced by LightLangParser#dictContent.
    def exitDictContent(self, ctx:LightLangParser.DictContentContext):
        pass


    # Enter a parse tree produced by LightLangParser#typeAnnotation.
    def enterTypeAnnotation(self, ctx:LightLangParser.TypeAnnotationContext):
        pass

    # Exit a parse tree produced by LightLangParser#typeAnnotation.
    def exitTypeAnnotation(self, ctx:LightLangParser.TypeAnnotationContext):
        pass


    # Enter a parse tree produced by LightLangParser#builtinType.
    def enterBuiltinType(self, ctx:LightLangParser.BuiltinTypeContext):
        pass

    # Exit a parse tree produced by LightLangParser#builtinType.
    def exitBuiltinType(self, ctx:LightLangParser.BuiltinTypeContext):
        pass


    # Enter a parse tree produced by LightLangParser#exprList.
    def enterExprList(self, ctx:LightLangParser.ExprListContext):
        pass

    # Exit a parse tree produced by LightLangParser#exprList.
    def exitExprList(self, ctx:LightLangParser.ExprListContext):
        pass


    # Enter a parse tree produced by LightLangParser#conditionalExpr.
    def enterConditionalExpr(self, ctx:LightLangParser.ConditionalExprContext):
        pass

    # Exit a parse tree produced by LightLangParser#conditionalExpr.
    def exitConditionalExpr(self, ctx:LightLangParser.ConditionalExprContext):
        pass



del LightLangParser