"""
光明（Light）编程语言 ANTLR 访问器 - 语句类 visit 方法混入
"""

from typing import List, Optional, Union

from antlr4 import *
from LightLangParser import LightLangParser

from light_ast import (
    NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
    Identifier, FunctionCall, PropertyAccess, SelfReference,
    ListComprehension, DictLiteral, ListLiteral,
    ExpressionStatement,
    IfStatement, ForeachStatement, WhileStatement,
    BreakStatement, ContinueStatement, ReturnStatement,
    TryStatement, ThrowStatement, MatchStatement, MatchCase, MatchPattern,
    WithStatement, DecoratorDefinition, DictComprehension,
    PrintStatement, DictEntry,
)

from visitor_decl import VisitorDeclMixin


class VisitorStmtMixin(VisitorDeclMixin):
    """语句 visit 方法混入类"""

    # ----- 语句 -----

    def visitStmt(self, ctx: LightLangParser.StmtContext):
        """语句分发"""
        if ctx.varDecl():
            return self.visitVarDecl(ctx.varDecl())
        elif ctx.assignStmt():
            return self.visitAssignStmt(ctx.assignStmt())
        elif ctx.compoundAssignStmt():
            return self.visitCompoundAssignStmt(ctx.compoundAssignStmt())
        elif ctx.ifStmt():
            return self.visitIfStmt(ctx.ifStmt())
        elif ctx.foreachStmt():
            return self.visitForeachStmt(ctx.foreachStmt())
        elif ctx.whileStmt():
            return self.visitWhileStmt(ctx.whileStmt())
        elif ctx.returnStmt():
            return self.visitReturnStmt(ctx.returnStmt())
        elif ctx.breakStmt():
            return self.visitBreakStmt(ctx.breakStmt())
        elif ctx.continueStmt():
            return self.visitContinueStmt(ctx.continueStmt())
        elif ctx.tryStmt():
            return self.visitTryStmt(ctx.tryStmt())
        elif ctx.throwStmt():
            return self.visitThrowStmt(ctx.throwStmt())
        elif ctx.matchStmt():
            return self.visitMatchStmt(ctx.matchStmt())
        elif ctx.withStmt():
            return self.visitWithStmt(ctx.withStmt())
        elif ctx.printStmt():
            return self.visitPrintStmt(ctx.printStmt())
        elif ctx.exprStmt():
            return self.visitExprStmt(ctx.exprStmt())
        return None

    def visitIfStmt(self, ctx: LightLangParser.IfStmtContext):
        """条件语句"""
        line = ctx.start.line
        col = ctx.start.column

        condition = self.visitExpr(ctx.expr(0))

        then_body = []
        if ctx.block(0):
            then_body = self.visitBlock(ctx.block(0))

        else_body = None
        num_elseif = len(ctx.K_ELSE_IF())
        if ctx.K_ELSE():
            # else 体在最后一个 block（索引 = elseif 数量 + 1）
            else_body = self.visitBlock(ctx.block(num_elseif + 1))

        # elseif 子句
        elseif_conditions = []
        elseif_bodies = []
        if num_elseif > 0:
            for i in range(num_elseif):
                # elseif 条件
                cond_idx = i + 1
                elseif_conditions.append(self.visitExpr(ctx.expr(cond_idx)))
                # elseif 体
                elseif_bodies.append(self.visitBlock(ctx.block(i + 1)))

        return IfStatement(
            line=line, column=col,
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            elseif_conditions=elseif_conditions,
            elseif_bodies=elseif_bodies,
        )

    def visitForeachStmt(self, ctx: LightLangParser.ForeachStmtContext):
        """遍历循环"""
        line = ctx.start.line
        col = ctx.start.column

        # 遍历变量（直接从foreachStmt获取）
        variable = ctx.ID().getText() if ctx.ID() else "当前项"

        iterable = self.visitExpr(ctx.expr())

        body = []
        if ctx.block():
            body = self.visitBlock(ctx.block())

        return ForeachStatement(line=line, column=col, variable=variable,
                                iterable=iterable, body=body)

    def visitWhileStmt(self, ctx: LightLangParser.WhileStmtContext):
        """当循环"""
        line = ctx.start.line
        col = ctx.start.column
        condition = self.visitExpr(ctx.expr())
        body = []
        if ctx.block():
            body = self.visitBlock(ctx.block())
        return WhileStatement(line=line, column=col, condition=condition, body=body)

    def visitReturnStmt(self, ctx: LightLangParser.ReturnStmtContext):
        """返回语句"""
        line = ctx.start.line
        col = ctx.start.column
        value = None
        if ctx.expr():
            value = self.visitExpr(ctx.expr())
        return ReturnStatement(line=line, column=col, value=value)

    def visitBreakStmt(self, ctx: LightLangParser.BreakStmtContext):
        """跳出语句"""
        return BreakStatement(line=ctx.start.line, column=ctx.start.column)

    def visitContinueStmt(self, ctx: LightLangParser.ContinueStmtContext):
        """跳过语句"""
        return ContinueStatement(line=ctx.start.line, column=ctx.start.column)

    def visitTryStmt(self, ctx: LightLangParser.TryStmtContext):
        """异常捕获"""
        line = ctx.start.line
        col = ctx.start.column
        try_body = self.visitBlock(ctx.block(0))
        catch_var = ctx.ID().getText()
        catch_body = self.visitBlock(ctx.block(1))
        return TryStatement(line=line, column=col, try_body=try_body,
                            catch_var=catch_var, catch_body=catch_body)

    def visitThrowStmt(self, ctx: LightLangParser.ThrowStmtContext):
        """抛出异常"""
        line = ctx.start.line
        col = ctx.start.column
        value = self.visitExpr(ctx.expr())
        return ThrowStatement(line=line, column=col, value=value)

    def visitMatchStmt(self, ctx: LightLangParser.MatchStmtContext):
        """模式匹配语句"""
        line = ctx.start.line
        col = ctx.start.column
        subject = self.visitExpr(ctx.expr())
        cases = []
        for case_ctx in ctx.matchCase():
            cases.append(self.visitMatchCase(case_ctx))
        return MatchStatement(line=line, column=col, subject=subject, cases=cases)

    def visitMatchCase(self, ctx: LightLangParser.MatchCaseContext):
        """匹配分支"""
        line = ctx.start.line
        col = ctx.start.column
        pattern = self.visitMatchPattern(ctx.matchPattern())
        guard = None
        if ctx.K_IF():
            # 从expr中找守卫条件
            exprs = ctx.expr()
            if exprs:
                guard = self.visitExpr(exprs[0])
        body = self.visitBlock(ctx.block()) if ctx.block() else []
        return MatchCase(line=line, column=col, pattern=pattern, guard=guard, body=body)

    def visitMatchPattern(self, ctx: LightLangParser.MatchPatternContext):
        """匹配模式"""
        line = ctx.start.line
        col = ctx.start.column

        if ctx.NUMBER():
            text = ctx.NUMBER().getText()
            value = float(text) if '.' in text else int(text)
            return MatchPattern(line=line, column=col, kind='number',
                                value=NumberLiteral(line=line, column=col, value=value))
        if ctx.STRING():
            text = ctx.STRING().getText()
            raw = text[1:-1]
            value = self._unescape_string(raw)
            return MatchPattern(line=line, column=col, kind='string',
                                value=StringLiteral(line=line, column=col, value=value))
        if ctx.K_TRUE():
            return MatchPattern(line=line, column=col, kind='bool',
                                value=BooleanLiteral(line=line, column=col, value=True))
        if ctx.K_FALSE():
            return MatchPattern(line=line, column=col, kind='bool',
                                value=BooleanLiteral(line=line, column=col, value=False))
        if ctx.K_NULL():
            return MatchPattern(line=line, column=col, kind='null')
        if ctx.UNDERSCORE():
            return MatchPattern(line=line, column=col, kind='wildcard')

        # 列表模式
        if ctx.LBRACKET():
            elements = []
            if ctx.matchPatternList():
                elements = [self.visitMatchPattern(p) for p in ctx.matchPatternList().matchPattern()]
            return MatchPattern(line=line, column=col, kind='list', elements=elements)

        # 类型检查模式：类名 之 变量
        if ctx.K_OF():
            type_name = ctx.ID(0).getText() if ctx.ID(0) else ""
            binding = ctx.ID(1).getText() if len(ctx.ID()) > 1 else ""
            return MatchPattern(line=line, column=col, kind='type_check',
                                type_name=type_name, binding=binding)

        # 变量绑定或标识符
        if ctx.ID():
            name = ctx.ID().getText()
            # 小写/中文标识符视为变量绑定，大写标识符视为枚举匹配
            return MatchPattern(line=line, column=col, kind='variable', binding=name)

        return MatchPattern(line=line, column=col, kind='wildcard')

    def visitWithStmt(self, ctx: LightLangParser.WithStmtContext):
        """上下文管理器语句：使用 表达式 作为 变量：...结束。"""
        line = ctx.start.line
        col = ctx.start.column
        context_expr = self.visitExpr(ctx.expr())
        variable = ctx.ID().getText() if ctx.ID() else None
        body = self.visitBlock(ctx.block()) if ctx.block() else []
        return WithStatement(line=line, column=col,
                             context_expr=context_expr, variable=variable, body=body)

    def visitDecoratorDef(self, ctx: LightLangParser.DecoratorDefContext):
        """装饰器定义：@段落名 标注 段落 ..."""
        line = ctx.start.line
        col = ctx.start.column
        decorator_name = ctx.ID().getText()
        paragraph = self.visitParagraphDef(ctx.paragraphDef())
        return DecoratorDefinition(line=line, column=col,
                                   decorator_name=decorator_name, paragraph=paragraph)

    def visitDictComprehension(self, ctx: LightLangParser.DictComprehensionContext):
        """字典推导：{键: 值 遍历 变量 之 列表}"""
        line = ctx.start.line
        col = ctx.start.column
        key_expr = self.visitExpr(ctx.expr(0))
        value_expr = self.visitExpr(ctx.expr(1))
        variable = self._get_identifier_like_name(ctx.identifier_like())
        iterable = self.visitExpr(ctx.expr(2))
        condition = None
        if ctx.K_IF():
            condition = self.visitExpr(ctx.expr(3))
        return DictComprehension(line=line, column=col,
                                 key_expr=key_expr, value_expr=value_expr,
                                 variable=variable, iterable=iterable,
                                 condition=condition)

    def visitBracketContent(self, ctx: LightLangParser.BracketContentContext):
        """方括号内容：消除列表/字典/推导歧义"""
        line = ctx.start.line
        col = ctx.start.column

        # 1. 字典推导：键: 值 遍历 ...
        if ctx.dictComprehension():
            return self.visitDictComprehension(ctx.dictComprehension())

        # 2. 字典字面量：键: 值, ...
        if ctx.dictLiteral():
            from light_ast import DictEntry
            entries = []
            for entry_ctx in ctx.dictLiteral().dictEntry():
                key = self.visitExpr(entry_ctx.expr(0))
                value = self.visitExpr(entry_ctx.expr(1))
                entries.append(DictEntry(line=key.line, column=key.column, key=key, value=value))
            return DictLiteral(line=line, column=col, entries=entries)

        # 3. 列表推导：表达式 遍历 变量 之 ...
        if ctx.K_FOREACH():
            expression = self.visitExpr(ctx.expr(0))
            variable = self._get_identifier_like_name(ctx.identifier_like())
            iterable = self.visitExpr(ctx.expr(1))
            condition = None
            if ctx.K_IF():
                condition = self.visitExpr(ctx.expr(2))
            return ListComprehension(line=line, column=col,
                                     expression=expression, variable=variable,
                                     iterable=iterable, condition=condition)

        # 4. 列表字面量
        if ctx.exprList():
            elements = self.visitExprList(ctx.exprList())
            return ListLiteral(line=line, column=col, elements=elements)

        # 空列表
        return ListLiteral(line=line, column=col, elements=[])

    @staticmethod
    def _unescape_string(raw: str) -> str:
        """解析字符串转义序列"""
        escaped = []
        i = 0
        while i < len(raw):
            if raw[i] == '\\' and i + 1 < len(raw):
                nxt = raw[i + 1]
                if nxt == 'n':
                    escaped.append('\n')
                elif nxt == 't':
                    escaped.append('\t')
                elif nxt == 'r':
                    escaped.append('\r')
                elif nxt == '\\':
                    escaped.append('\\')
                elif nxt == '"':
                    escaped.append('"')
                elif nxt == "'":
                    escaped.append("'")
                else:
                    escaped.append(raw[i])
                    escaped.append(nxt)
                i += 2
            else:
                escaped.append(raw[i])
                i += 1
        return ''.join(escaped)

    def visitPrintStmt(self, ctx: LightLangParser.PrintStmtContext):
        """打印语句"""
        line = ctx.start.line
        col = ctx.start.column
        # 新语法: 打印(exprList) 或 输出(exprList)
        expr_list = ctx.exprList()
        if expr_list:
            # 多个参数用逗号连接
            values = [self.visitExpr(e) for e in expr_list.expr()]
            if len(values) == 1:
                value = values[0]
            else:
                # 多个参数拼接成一个表达式
                value = values[0]
        else:
            value = None
        return PrintStatement(line=line, column=col, value=value)

    def visitExprStmt(self, ctx: LightLangParser.ExprStmtContext):
        """表达式语句"""
        line = ctx.start.line
        col = ctx.start.column
        expr = self.visitExpr(ctx.expr())
        # 独立的标识符作为表达式语句时，视为无参数函数调用
        # 例如：问候。 → FunctionCall(问候, [])
        if isinstance(expr, Identifier):
            expr = FunctionCall(line=expr.line, column=expr.column,
                                name=expr, arguments=[])
        return ExpressionStatement(line=line, column=col, expression=expr)