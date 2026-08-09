"""
光明（Light）编程语言 ANTLR 访问器 - 表达式类 visit 方法混入
"""

from typing import List, Optional, Union

from antlr4 import *
from LightLangParser import LightLangParser

from light_ast import (
    NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
    Identifier, SegmentName, BinaryOp, UnaryOp, FunctionCall,
    PipeExpression, PropertyAccess, IndexAccess, ListLiteral, DictLiteral, NewExpression,
    ConditionalExpression,
    StringInterpolation, ListComprehension, LambdaExpression,
    Parameter, SelfReference,
    AwaitExpression,
)

from visitor_stmt import VisitorStmtMixin


class VisitorExprMixin(VisitorStmtMixin):
    """表达式 visit 方法混入类"""

    # ----- 表达式 -----

    def visitExpr(self, ctx: LightLangParser.ExprContext):
        """表达式入口"""
        child = ctx.getChild(0)
        if isinstance(child, LightLangParser.PipelineExprContext):
            return self.visitPipelineExpr(child)
        elif isinstance(child, LightLangParser.AndExprContext):
            return self.visitAndExpr(child)
        elif isinstance(child, LightLangParser.OrExprContext):
            return self.visitOrExpr(child)
        elif isinstance(child, LightLangParser.ComparisonExprContext):
            return self.visitComparisonExpr(child)
        elif isinstance(child, LightLangParser.AdditiveExprContext):
            return self.visitAdditiveExpr(child)
        elif isinstance(child, LightLangParser.MultiplicativeExprContext):
            return self.visitMultiplicativeExpr(child)
        elif isinstance(child, LightLangParser.UnaryExprContext):
            return self.visitUnaryExpr(child)
        elif isinstance(child, LightLangParser.PostfixExprContext):
            return self.visitPostfixExpr(child)
        elif isinstance(child, LightLangParser.PrimaryContext):
            return self.visitPrimary(child)
        return self.visit(child)

    def visitPipelineExpr(self, ctx: LightLangParser.PipelineExprContext):
        """管道表达式"""
        # 使用 getTypedRuleContexts 获取 AndExpr 子节点
        exprs = [self.visitAndExpr(c)
                 for c in ctx.getTypedRuleContexts(LightLangParser.AndExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        line = ctx.start.line
        col = ctx.start.column
        return PipeExpression(line=line, column=col, expressions=exprs)

    def visitAndExpr(self, ctx: LightLangParser.AndExprContext):
        """逻辑与表达式"""
        exprs = [self.visitOrExpr(c)
                 for c in ctx.getTypedRuleContexts(LightLangParser.OrExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        # 从左到右构建 BinaryOp
        result = exprs[0]
        for i in range(1, len(exprs)):
            result = BinaryOp(line=result.line, column=result.column,
                              left=result, operator='且', right=exprs[i])
        return result

    def visitOrExpr(self, ctx: LightLangParser.OrExprContext):
        """逻辑或表达式"""
        exprs = [self.visitComparisonExpr(c)
                 for c in ctx.getTypedRuleContexts(LightLangParser.ComparisonExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        result = exprs[0]
        for i in range(1, len(exprs)):
            result = BinaryOp(line=result.line, column=result.column,
                              left=result, operator='or', right=exprs[i])
        return result

    def visitComparisonExpr(self, ctx: LightLangParser.ComparisonExprContext):
        """比较表达式"""
        exprs = [self.visitAdditiveExpr(a)
                 for a in ctx.getTypedRuleContexts(LightLangParser.AdditiveExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        ops = [c.getText() for c in ctx.compOp()]
        result = exprs[0]
        for i, op in enumerate(ops):
            result = BinaryOp(line=result.line, column=result.column,
                              left=result, operator=op, right=exprs[i+1])
        return result

    def visitAdditiveExpr(self, ctx: LightLangParser.AdditiveExprContext):
        """加减表达式"""
        exprs = [self.visitMultiplicativeExpr(m)
                 for m in ctx.getTypedRuleContexts(LightLangParser.MultiplicativeExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        ops = [c.getText() for c in ctx.addOp()]
        result = exprs[0]
        for i, op in enumerate(ops):
            result = BinaryOp(line=result.line, column=result.column,
                              left=result, operator=op, right=exprs[i+1])
        return result

    def visitMultiplicativeExpr(self, ctx: LightLangParser.MultiplicativeExprContext):
        """乘除表达式（将 ×/÷ 符号归一化为 乘/除 中文关键字）"""
        exprs = [self.visitUnaryExpr(u)
                 for u in ctx.getTypedRuleContexts(LightLangParser.UnaryExprContext)]
        if len(exprs) == 1:
            return exprs[0]
        ops = [c.getText() for c in ctx.multOp()]
        result = exprs[0]
        for i, op in enumerate(ops):
            # 归一化符号运算符
            normalized_op = op
            if op == '×':
                normalized_op = '乘'
            elif op == '÷':
                normalized_op = '除'
            result = BinaryOp(line=result.line, column=result.column,
                              left=result, operator=normalized_op, right=exprs[i+1])
        return result

    def visitUnaryExpr(self, ctx: LightLangParser.UnaryExprContext):
        """一元表达式"""
        if ctx.K_NOT() or ctx.NOT():
            op = ctx.K_NOT().getText() if ctx.K_NOT() else ctx.NOT().getText()
            operand = self.visitUnaryExpr(ctx.unaryExpr())
            return UnaryOp(line=ctx.start.line, column=ctx.start.column,
                           operator=op, operand=operand)
        if ctx.MINUS() or ctx.K_MINUS():
            operand = self.visitUnaryExpr(ctx.unaryExpr())
            return UnaryOp(line=ctx.start.line, column=ctx.start.column,
                           operator='-', operand=operand)
        return self.visitPostfixExpr(ctx.postfixExpr())

    def visitPostfixExpr(self, ctx: LightLangParser.PostfixExprContext):
        """后缀表达式：处理索引访问、属性访问、函数调用"""
        base = self.visitPrimary(ctx.primary())

        # 如果已经是 NewExpression，直接返回（避免被包装成 FunctionCall）
        if isinstance(base, NewExpression):
            return base

        # 顺序处理后缀操作（按子节点位置）
        child_idx = 1  # 0 是 primary
        while child_idx < ctx.getChildCount():
            child = ctx.getChild(child_idx)

            if isinstance(child, TerminalNode):
                ttype = child.symbol.type

                # 属性访问：对象之属性
                if ttype == LightLangParser.K_OF:
                    child_idx += 1
                    prop_name = ctx.getChild(child_idx).getText()
                    child_idx += 1
                    base = PropertyAccess(line=base.line, column=base.column,
                                          obj=base, property_name=prop_name)

                # 属性访问：对象.属性
                elif ttype == LightLangParser.DOT:
                    child_idx += 1
                    prop_name = ctx.getChild(child_idx).getText()
                    child_idx += 1
                    base = PropertyAccess(line=base.line, column=base.column,
                                          obj=base, property_name=prop_name)

                # 属性访问：对象的属性（新增，「的」作为属性访问运算符）
                elif ttype == LightLangParser.K_DE:
                    child_idx += 1
                    prop_name = ctx.getChild(child_idx).getText()
                    child_idx += 1
                    base = PropertyAccess(line=base.line, column=base.column,
                                          obj=base, property_name=prop_name)

                # 索引访问：对象[索引]
                elif ttype == LightLangParser.LBRACKET:
                    child_idx += 1
                    idx_expr = self.visit(ctx.getChild(child_idx))
                    child_idx += 1  # 跳过 expr
                    child_idx += 1  # 跳过 RBRACKET
                    base = IndexAccess(line=base.line, column=base.column,
                                       obj=base, index=idx_expr)

                # 函数调用：(参数)
                elif ttype == LightLangParser.LPAREN:
                    child_idx += 1  # 跳过 LPAREN
                    args = []
                    if (child_idx < ctx.getChildCount() and
                            isinstance(ctx.getChild(child_idx),
                                       LightLangParser.ExprListContext)):
                        args = self.visitExprList(ctx.getChild(child_idx))
                        child_idx += 1
                    child_idx += 1  # 跳过 RPAREN
                    base = FunctionCall(line=base.line, column=base.column,
                                        name=base, arguments=args)

                # 《段名》(参数) 调用
                elif ttype == LightLangParser.BOOK_L:
                    child_idx += 1
                    seg_name = ctx.getChild(child_idx).getText()  # ID
                    child_idx += 1  # 跳过 ID
                    child_idx += 1  # 跳过 BOOK_R
                    child_idx += 1  # 跳过 LPAREN
                    args = []
                    if (child_idx < ctx.getChildCount() and
                            isinstance(ctx.getChild(child_idx),
                                       LightLangParser.ExprListContext)):
                        args = self.visitExprList(ctx.getChild(child_idx))
                        child_idx += 1
                    child_idx += 1  # 跳过 RPAREN
                    seg = SegmentName(line=base.line, column=base.column, name=seg_name)
                    base = FunctionCall(line=base.line, column=base.column,
                                        name=seg, arguments=args)
                # ID(参数) - 直接调用（无书名号）
                elif ttype == LightLangParser.ID and child_idx + 1 < ctx.getChildCount():
                    next_child = ctx.getChild(child_idx + 1)
                    if isinstance(next_child, TerminalNode) and next_child.symbol.type == LightLangParser.LPAREN:
                        seg_name = child.getText()
                        child_idx += 1  # 跳过 ID
                        child_idx += 1  # 跳过 LPAREN
                        args = []
                        if (child_idx < ctx.getChildCount() and
                                isinstance(ctx.getChild(child_idx),
                                           LightLangParser.ExprListContext)):
                            args = self.visitExprList(ctx.getChild(child_idx))
                            child_idx += 1
                        child_idx += 1  # 跳过 RPAREN
                        seg = SegmentName(line=base.line, column=base.column, name=seg_name)
                        base = FunctionCall(line=base.line, column=base.column,
                                            name=seg, arguments=args)
                    else:
                        child_idx += 1
                else:
                    child_idx += 1
            else:
                child_idx += 1

        return base

    def _get_type_as_identifier_name(self, ctx):
        """从 typeAsIdentifier 规则中提取名称文本"""
        if ctx is None:
            return ''
        if ctx.T_NUMBER():
            return ctx.T_NUMBER().getText()
        if ctx.T_INT():
            return ctx.T_INT().getText()
        if ctx.T_FLOAT():
            return ctx.T_FLOAT().getText()
        if ctx.T_STRING():
            return ctx.T_STRING().getText()
        if ctx.T_LIST():
            return ctx.T_LIST().getText()
        if ctx.T_DICT():
            return ctx.T_DICT().getText()
        if ctx.T_SET():
            return ctx.T_SET().getText()
        if ctx.T_BOOL():
            return ctx.T_BOOL().getText()
        if ctx.T_ANY():
            return ctx.T_ANY().getText()
        return ctx.getText()

    def visitPrimary(self, ctx: LightLangParser.PrimaryContext):
        """基本表达式"""
        line = ctx.start.line
        col = ctx.start.column

        if ctx.NUMBER():
            text = ctx.NUMBER().getText()
            if '.' in text:
                return NumberLiteral(line=line, column=col, value=float(text))
            return NumberLiteral(line=line, column=col, value=int(text))

        if ctx.STRING():
            text = ctx.STRING().getText()
            # 去掉引号并解析转义序列
            raw = text[1:-1]
            # 检测是否包含插值表达式 {xxx}
            interpolated = self._parse_string_interpolation(raw, line, col)
            if interpolated is not None:
                return interpolated
            # 普通字符串
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
            return StringLiteral(line=line, column=col, value=''.join(escaped))

        if ctx.K_TRUE():
            return BooleanLiteral(line=line, column=col, value=True)
        if ctx.K_FALSE():
            return BooleanLiteral(line=line, column=col, value=False)
        if ctx.K_NULL():
            return NullLiteral(line=line, column=col)

        # self引用：己（通过检查子节点）
        for child in ctx.getChildren():
            if hasattr(child, 'symbol') and hasattr(child.symbol, 'type'):
                if child.symbol.type == LightLangParser.K_SELF:
                    return SelfReference(line=line, column=col)

        # 三元条件表达式：如果 条件 那么 值1 否则 值2
        if ctx.conditionalExpr():
            return self.visitConditionalExpr(ctx.conditionalExpr())

        # 实例化表达式：新 类名() - 必须在 ID 检查之前
        if ctx.K_NEW():
            class_name = ctx.ID().getText()
            arguments = []
            if ctx.exprList():
                arguments = self.visitExprList(ctx.exprList())
            return NewExpression(line=line, column=col, class_name=class_name, arguments=arguments)

        # 列表推导：[表达式 遍历 变量 之 列表]
        if ctx.listComprehension():
            return self.visitListComprehension(ctx.listComprehension())

        # 匿名函数：接收 甲：返回 甲 乘 甲。
        if ctx.lambdaExpr():
            return self.visitLambdaExpr(ctx.lambdaExpr())

        # 动词调用处理（基于Parser语法规则）
        # 列表操作动词
        if ctx.K_FIRST():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='首'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_LAST():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='末'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_REST():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='余'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_LENGTH():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='长'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_SORT():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='排序'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_REVERSE():
            return FunctionCall(line=line, column=col,
                                name=Identifier(line=line, column=col, name='反转'),
                                arguments=[self.visitExpr(ctx.expr(0))])
        # K_SUM, K_MAX, K_MIN 已移除
        if ctx.K_UNIQUE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='去重'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_FILTER():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='筛选'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_MAP():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='映射'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])

        # 字符串操作动词
        if ctx.K_TO_INT():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='转整数'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_TO_FLOAT():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='转浮点'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_TO_STR():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='转字符串'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_STR_LEN():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='字符串长度'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_STR_SPLIT():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='分割字符串'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_STR_JOIN():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='连接字符串'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_STR_REPLACE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='替换字符串'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1)), self.visitExpr(ctx.expr(2))])
        if ctx.K_STR_TRIM():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='去除空白'),
                               arguments=[self.visitExpr(ctx.expr(0))])

        # 文件操作动词
        if ctx.K_READ_FILE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='读取文件'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_WRITE_FILE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='写入文件'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_APPEND_FILE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='追加文件'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_FILE_EXISTS():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='文件存在'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_DIR_EXISTS():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='目录存在'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_MAKE_DIR():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='创建目录'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_REMOVE_FILE():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='删除文件'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_REMOVE_DIR():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='删除目录'),
                               arguments=[self.visitExpr(ctx.expr(0))])

        # 系统操作动词
        if ctx.K_ENV():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='环境变量'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_SET_ENV():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='设置环境变量'),
                               arguments=[self.visitExpr(ctx.expr(0)), self.visitExpr(ctx.expr(1))])
        if ctx.K_ARGS():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='参数列表'),
                               arguments=[])
        if ctx.K_EXIT():
            args = []
            if ctx.expr():
                args = [self.visitExpr(ctx.expr(0))]
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='退出程序'),
                               arguments=args)
        if ctx.K_CWD():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='当前目录'),
                               arguments=[])
        if ctx.K_CD():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='切换目录'),
                               arguments=[self.visitExpr(ctx.expr(0))])
        if ctx.K_EXEC():
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='执行命令'),
                               arguments=[self.visitExpr(ctx.expr(0))])

        # I/O操作动词 (K_PRINT和K_OUTPUT已移至printStmt规则)
        if ctx.K_INPUT():
            args = []
            if ctx.expr():
                args = [self.visitExpr(ctx.expr(0))]
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='输入'),
                               arguments=args)
        if ctx.K_READ():
            args = []
            if ctx.expr():
                args = [self.visitExpr(ctx.expr(0))]
            return FunctionCall(line=line, column=col,
                               name=Identifier(line=line, column=col, name='读取'),
                               arguments=args)

        if ctx.ID():
            name = ctx.ID().getText()
            # 检查是否为中文数字（如 四十二、三点一四）
            cn_value = self._is_chinese_number(name)
            if cn_value is not None:
                if isinstance(cn_value, float):
                    return NumberLiteral(line=line, column=col, value=cn_value)
                return NumberLiteral(line=line, column=col, value=cn_value)
            # 特殊处理：以"己"开头的标识符 -> 己.属性
            if name.startswith('己'):
                # 拆分为 self.属性
                prop_name = name[1:]  # 去掉"己"前缀
                if prop_name:  # 确保有属性名
                    return PropertyAccess(line=line, column=col,
                                          obj=SelfReference(line=line, column=col),
                                          property_name=prop_name)
            return Identifier(line=line, column=col, name=name)

        # 类型关键字用作标识符（如变量名"数"）
        if ctx.typeAsIdentifier():
            type_id = ctx.typeAsIdentifier()
            name = self._get_type_as_identifier_name(type_id)
            return Identifier(line=line, column=col, name=name)

        if ctx.LPAREN():
            exprs = ctx.expr()
            if exprs:
                return self.visitExpr(exprs[0])
            return None

        if ctx.LBRACKET():
            # 统一通过 bracketContent 处理
            if ctx.bracketContent():
                return self.visitBracketContent(ctx.bracketContent())
            # 空列表
            return ListLiteral(line=line, column=col, elements=[])

        if ctx.BOOK_L() and ctx.BOOK_R():
            return SegmentName(line=line, column=col, name=ctx.ID().getText())

        # Fallback
        return None

    def visitConditionalExpr(self, ctx: LightLangParser.ConditionalExprContext):
        """三元条件表达式：如果 条件 那么 值1 否则 值2"""
        line = ctx.start.line
        col = ctx.start.column
        # conditionalExpr 规则：K_IF expr K_THEN expr ( K_ELSE expr )?
        # 子规则索引：K_IF(0), expr(0), K_THEN(1), expr(1), K_ELSE(2)?, expr(2)?
        condition = self.visitExpr(ctx.expr(0))
        then_expr = self.visitExpr(ctx.expr(1))
        else_expr = None
        if ctx.K_ELSE():
            else_expr = self.visitExpr(ctx.expr(2))
        return ConditionalExpression(
            line=line, column=col,
            condition=condition,
            then_expr=then_expr,
            else_expr=else_expr,
        )

    def visitImplicitCall(self, ctx: LightLangParser.ImplicitCallContext):
        """隐式函数调用参数列表"""
        args = []
        for i in range(len(ctx.implicitArg())):
            arg_ctx = ctx.implicitArg(i)
            arg = self.visitImplicitArg(arg_ctx)
            if arg is not None:
                args.append(arg)
        return args

    def visitImplicitArg(self, ctx: LightLangParser.ImplicitArgContext):
        """隐式函数调用的单个参数"""
        line = ctx.start.line
        col = ctx.start.column

        if ctx.NUMBER():
            text = ctx.NUMBER().getText()
            if '.' in text:
                return NumberLiteral(line=line, column=col, value=float(text))
            return NumberLiteral(line=line, column=col, value=int(text))

        if ctx.STRING():
            text = ctx.STRING().getText()
            raw = text[1:-1]
            # 解析转义序列
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
            return StringLiteral(line=line, column=col, value=''.join(escaped))

        if ctx.K_TRUE():
            return BooleanLiteral(line=line, column=col, value=True)
        if ctx.K_FALSE():
            return BooleanLiteral(line=line, column=col, value=False)
        if ctx.K_NULL():
            return NullLiteral(line=line, column=col)
        if ctx.K_SELF():
            return SelfReference(line=line, column=col)

        if ctx.ID():
            name = ctx.ID().getText()
            # 检查是否为中文数字
            cn_value = self._is_chinese_number(name)
            if cn_value is not None:
                if isinstance(cn_value, float):
                    return NumberLiteral(line=line, column=col, value=cn_value)
                return NumberLiteral(line=line, column=col, value=cn_value)
            return Identifier(line=line, column=col, name=name)

        return None

    def visitExprList(self, ctx: LightLangParser.ExprListContext):
        """表达式列表"""
        return [self.visitExpr(e) for e in ctx.expr()]

    def _parse_string_interpolation(self, raw: str, line: int, col: int):
        """检测字符串中是否包含 {表达式} 插值，若有则返回StringInterpolation节点"""
        import re

        # 快速检测：如果字符串以 { 或 [ 开头，很可能是 JSON，跳过插值检测
        if raw and raw[0] in ('{', '['):
            return None

        # 匹配 {expr} 模式（非转义的 { }）
        # 先检查是否有未转义的 {
        has_interpolation = False
        i = 0
        while i < len(raw):
            if raw[i] == '\\' and i + 1 < len(raw):
                i += 2  # 跳过转义字符
                continue
            if raw[i] == '{':
                has_interpolation = True
                break
            i += 1

        if not has_interpolation:
            return None

        # 拆分为交替的字符串片段和表达式
        parts = []
        current_str = []
        i = 0
        while i < len(raw):
            if raw[i] == '\\' and i + 1 < len(raw):
                nxt = raw[i + 1]
                if nxt == 'n':
                    current_str.append('\n')
                elif nxt == 't':
                    current_str.append('\t')
                elif nxt == 'r':
                    current_str.append('\r')
                elif nxt == '\\':
                    current_str.append('\\')
                elif nxt == '{':
                    current_str.append('{')
                elif nxt == '}':
                    current_str.append('}')
                else:
                    current_str.append(raw[i])
                    current_str.append(nxt)
                i += 2
                continue
            if raw[i] == '{':
                # 保存前面的字符串部分
                if current_str:
                    parts.append(''.join(current_str))
                    current_str = []
                # 找到匹配的 }
                j = i + 1
                depth = 1
                while j < len(raw) and depth > 0:
                    if raw[j] == '{':
                        depth += 1
                    elif raw[j] == '}':
                        depth -= 1
                    j += 1
                if depth == 0:
                    expr_text = raw[i+1:j-1].strip()
                    # 解析插值表达式
                    try:
                        expr_ast = self._parse_interpolation_expr(expr_text, line, col)
                        parts.append(expr_ast)
                    except Exception:
                        # 如果解析失败，当作普通文本
                        parts.append('{' + expr_text + '}')
                    i = j
                else:
                    current_str.append(raw[i])
                    i += 1
            else:
                current_str.append(raw[i])
                i += 1

        # 保存最后的字符串部分
        if current_str:
            parts.append(''.join(current_str))

        return StringInterpolation(line=line, column=col, parts=parts)

    def _parse_interpolation_expr(self, expr_text: str, line: int, col: int):
        """解析字符串插值中的表达式文本为AST节点"""
        # 使用ANTLR解析器解析表达式
        from light_tokenizer import create_antlr_token_stream
        from LightLangLexer import LightLangLexer
        from LightLangParser import LightLangParser

        token_stream = create_antlr_token_stream(expr_text, LightLangLexer)
        parser = LightLangParser(token_stream)
        parser.removeErrorListeners()
        tree = parser.expr()
        return self.visitExpr(tree)

    def visitListComprehension(self, ctx: LightLangParser.ListComprehensionContext):
        """列表推导：[表达式 遍历 变量 之 列表]"""
        line = ctx.start.line
        col = ctx.start.column
        expression = self.visitExpr(ctx.expr(0))  # 第一个expr是输出表达式
        variable = self._get_identifier_like_name(ctx.identifier_like())
        iterable = self.visitExpr(ctx.expr(1))  # 第二个expr是可迭代对象
        condition = None
        if ctx.K_IF():
            condition = self.visitExpr(ctx.expr(2))  # 第三个expr是条件（如果有）
        return ListComprehension(line=line, column=col,
                                 expression=expression, variable=variable,
                                 iterable=iterable, condition=condition)

    def visitLambdaExpr(self, ctx: LightLangParser.LambdaExprContext):
        """匿名函数：接收 甲：返回 甲 乘 甲。"""
        line = ctx.start.line
        col = ctx.start.column
        params = []
        if ctx.paramList():
            params = self.visitParamList(ctx.paramList())
        # 函数体：如果有 返回 关键字则取expr，否则取expr
        body_expr = self.visitExpr(ctx.expr()) if ctx.expr() else None
        return LambdaExpression(line=line, column=col, parameters=params, body=body_expr)

    def visitTypeAnnotation(self, ctx: LightLangParser.TypeAnnotationContext):
        """类型注解"""
        if ctx.ID():
            return ctx.ID().getText()
        if ctx.builtinType():
            return ctx.builtinType().getText()
        return "任意"