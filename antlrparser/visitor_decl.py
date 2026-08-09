"""
光明（Light）编程语言 ANTLR 访问器 - 声明类 visit 方法混入

将 ANTLR 解析树转换为光明 AST 节点
"""

import sys
import os
from typing import List, Optional, Union

# 添加当前目录到路径，以便导入生成的解析器
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parser_dir = os.path.join(_current_dir, 'light_parser')
sys.path.insert(0, _parser_dir)

# ANTLR imports
from antlr4 import *
from antlr4.tree.Trees import Trees
from antlr4.error.ErrorListener import ErrorListener

# 导入 ANTLR 生成的解析器（从 light_parser 目录）
from LightLangLexer import LightLangLexer
from LightLangParser import LightLangParser
from LightLangParserVisitor import LightLangParserVisitor

# 导入 AST 节点
from light_ast import (
    ASTNode, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
    Identifier, SegmentName, ModuleName, BinaryOp, UnaryOp, FunctionCall,
    PipeExpression, PropertyAccess, IndexAccess, ListLiteral, DictLiteral, NewExpression,
    ConditionalExpression,
    StringInterpolation, ListComprehension, LambdaExpression,
    MatchStatement, MatchCase, MatchPattern,
    DictComprehension, DecoratorDefinition, DestructuringAssignment, WithStatement,
    VariableDeclaration, Assignment, CompoundAssignment, IfStatement, ForeachStatement,
    WhileStatement, BreakStatement, ContinueStatement, ReturnStatement,
    TryStatement, ThrowStatement, PrintStatement, ExpressionStatement,
    Parameter, SegmentDefinition, DataTypeField, DataTypeDefinition,
    ErrorTypeDefinition, ImportStatement, ExportStatement, Module,
    ClassDefinition, InterfaceDefinition, MethodDefinition, ConstructorDefinition,
    InterfaceMethod, InterfaceProperty, SelfReference,
    AwaitExpression, DeferStatement, AsyncScope,
)


class VisitorDeclMixin(LightLangParserVisitor):
    """声明 visit 方法混入类"""

    def __init__(self):
        super().__init__()
        self.errors = []
        self.warnings = []

    def _add_warning(self, message: str, line: int, column: int):
        """添加警告信息"""
        self.warnings.append(f"警告 [行{line}:{column}]: {message}")

    # ----- 中文数字转换 -----

    _CN_DIGITS = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000,
    }

    def _is_chinese_number(self, text: str):
        """检查文本是否为中文数字，若是则返回数值，否则返回 None"""
        if not text:
            return None

        # 检查所有字符是否都是中文数字相关
        for ch in text:
            if ch not in self._CN_DIGITS and ch != '点':
                return None

        # 处理小数
        if '点' in text:
            parts = text.split('点', 1)
            if len(parts) != 2:
                return None
            int_part = self._convert_chinese_integer(parts[0])
            if int_part is None:
                return None
            frac = 0.0
            frac_len = 0
            for ch in parts[1]:
                if ch in self._CN_DIGITS and self._CN_DIGITS[ch] < 10:
                    frac = frac * 10 + self._CN_DIGITS[ch]
                    frac_len += 1
                else:
                    return None
            if frac_len == 0:
                return float(int_part)
            return float(int_part) + frac / (10 ** frac_len)

        # 处理整数
        return self._convert_chinese_integer(text)

    def _convert_chinese_integer(self, text: str):
        """将中文整数转换为数值"""
        if not text:
            return None

        digits = self._CN_DIGITS

        # 简单数字
        if text in digits:
            return digits[text]

        # 处理复合数字（如十六、一百零一、三百二十一）
        result = 0
        temp = 0
        for ch in text:
            if ch in digits:
                d = digits[ch]
                if d >= 10:  # 十、百、千、万是进位单位
                    if temp == 0:
                        temp = 1  # "十"在开头表示1*10
                    temp *= d
                    result += temp
                    temp = 0
                elif d == 0:  # 零表示空位
                    temp = 0
                else:  # 0-9的数字
                    temp = d
            else:
                return None

        result += temp
        return result

    # ----- 程序 -----

    def visitProgram(self, ctx: LightLangParser.ProgramContext):
        """程序入口"""
        module = Module(line=1, column=1)

        for child in ctx.getChildren():
            if isinstance(child, LightLangParser.ModuleDeclContext):
                module.name = self.visitModuleDecl(child)
            elif isinstance(child, LightLangParser.ImportStmtContext):
                module.imports.append(self.visitImportStmt(child))
            elif isinstance(child, LightLangParser.ExportStmtContext):
                module.exports.append(self.visitExportStmt(child))
            elif isinstance(child, LightLangParser.DefinitionContext):
                defn = self.visitDefinition(child)
                if isinstance(defn, SegmentDefinition):
                    module.segments.append(defn)
                elif isinstance(defn, ClassDefinition):
                    module.classes.append(defn)
                elif isinstance(defn, InterfaceDefinition):
                    module.interfaces.append(defn)
                elif isinstance(defn, DataTypeDefinition):
                    module.data_types.append(defn)
                elif isinstance(defn, ErrorTypeDefinition):
                    module.error_types.append(defn)
            elif isinstance(child, LightLangParser.StmtContext):
                stmt = self.visitStmt(child)
                if stmt:
                    module.statements.append(stmt)

        return module

    def visitModuleDecl(self, ctx: LightLangParser.ModuleDeclContext):
        """模块声明 【名称】"""
        return ctx.ID().getText()

    # ----- 段落定义 -----

    def visitParagraphDef(self, ctx: LightLangParser.ParagraphDefContext):
        """段落定义"""
        # 新语法：段落 名称 接收 参数列表:
        raw_name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column

        # 检测是否为异步段落（名称以 __async_ 为前缀）
        modifiers = []
        if raw_name.startswith('__async_'):
            name = raw_name[len('__async_'):]
            modifiers.append('异步')
        else:
            name = raw_name

        # 参数列表
        params = []
        if ctx.paramList():
            params = self.visitParamList(ctx.paramList())

        # 返回类型
        return_type = None
        if ctx.typeAnnotation():
            return_type = self.visitTypeAnnotation(ctx.typeAnnotation())

        # 段落体
        body = []
        if ctx.block():
            body = self.visitBlock(ctx.block())

        return SegmentDefinition(
            line=line, column=col,
            name=name,
            parameters=params,
            body=body,
            return_type=return_type,
            modifiers=modifiers,
        )

    def visitParagraphBody(self, ctx):
        """段落体：用于兼容旧的语法名称"""
        return self.visitBlock(ctx)

    def visitBlock(self, ctx: LightLangParser.BlockContext):
        """代码块（语句列表）"""
        stmts = []
        for child in ctx.getChildren():
            # 只处理StmtContext，忽略K_END标记
            if isinstance(child, LightLangParser.StmtContext):
                stmt = self.visitStmt(child)
                if stmt:
                    stmts.append(stmt)
            elif isinstance(child, LightLangParser.DefinitionContext):
                # 块内嵌套定义
                defn = self.visitDefinition(child)
                if defn:
                    stmts.append(defn)
        return stmts

    def visitClassDef(self, ctx: LightLangParser.ClassDefContext):
        """类定义"""
        name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column

        # 提取泛型参数
        generic_params = []
        if ctx.genericParams():
            for id_ctx in ctx.genericParams().ID():
                generic_params.append(id_ctx.getText())

        superclasses = []
        interfaces = []

        # 处理继承和实现
        child_list = list(ctx.getChildren())
        inherit_found = False
        use_found = False

        for child in child_list:
            if hasattr(child, 'getText'):
                txt = child.getText()
                if txt == '继承':
                    inherit_found = True
                    use_found = False
                elif txt == '使用':
                    use_found = True
                    inherit_found = False
                elif inherit_found and isinstance(child, LightLangParser.TypeAnnotationContext):
                    superclasses.append(self.visitTypeAnnotation(child))
                elif use_found and isinstance(child, LightLangParser.TypeAnnotationContext):
                    interfaces.append(self.visitTypeAnnotation(child))

        fields = []
        methods = []
        constructor = None

        for member in ctx.classMember():
            if member.attributeDecl():
                # 属性声明：属性 名字。
                attr_ctx = member.attributeDecl()
                field_name = attr_ctx.ID().getText()
                field = DataTypeField(
                    name=field_name,
                    type_annotation=""
                )
                fields.append(field)
            elif member.methodDef():
                method = self.visitMethodDef(member.methodDef())
                # 如果方法名为"初始化"，则作为构造函数
                if method.name == '初始化':
                    constructor = ConstructorDefinition(
                        line=method.line,
                        column=method.column,
                        parameters=method.parameters,
                        body=method.body
                    )
                else:
                    methods.append(method)
            elif member.constructorDef():
                constructor = self.visitConstructorDef(member.constructorDef())

        return ClassDefinition(
            line=line, column=col,
            name=name,
            generic_params=generic_params,
            superclasses=superclasses,
            interfaces=interfaces,
            fields=fields,
            methods=methods,
            constructor=constructor,
        )

    def visitMethodDef(self, ctx: LightLangParser.MethodDefContext):
        """方法定义"""
        name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column

        params = []
        if ctx.paramList():
            params = self.visitParamList(ctx.paramList())

        return_type = None
        if ctx.typeAnnotation():
            return_type = self.visitTypeAnnotation(ctx.typeAnnotation())

        body = []
        if ctx.block():
            body = self.visitBlock(ctx.block())

        return MethodDefinition(
            line=line, column=col,
            name=name,
            parameters=params,
            body=body,
            return_type=return_type,
            is_static=False,
        )

    def visitConstructorDef(self, ctx: LightLangParser.ConstructorDefContext):
        """构造函数定义"""
        name = "构造"  # 构造函数名固定为"构造"
        line = ctx.start.line
        col = ctx.start.column

        params = []
        if ctx.paramList():
            params = self.visitParamList(ctx.paramList())

        body = []
        if ctx.block():
            body = self.visitBlock(ctx.block())

        return ConstructorDefinition(
            line=line, column=col,
            name=name,
            parameters=params,
            body=body,
        )

    def visitInterfaceDef(self, ctx: LightLangParser.InterfaceDefContext):
        """接口定义"""
        name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column

        superinterfaces = []
        inherit_found = False

        for child in ctx.getChildren():
            if hasattr(child, 'getText') and child.getText() == '继承':
                inherit_found = True
            elif inherit_found and isinstance(child, LightLangParser.TypeAnnotationContext):
                superinterfaces.append(self.visitTypeAnnotation(child))

        methods = []
        properties = []

        for member in ctx.interfaceMember():
            # interfaceMember: K_METHOD ID LPAREN paramList? RPAREN (K_RETURN typeAnnotation)? PERIOD?
            method_name = member.ID().getText()
            params = []
            if member.paramList():
                params = self.visitParamList(member.paramList())
            return_type = None
            if member.typeAnnotation():
                return_type = self.visitTypeAnnotation(member.typeAnnotation())
            methods.append(InterfaceMethod(
                line=member.start.line, column=member.start.column,
                name=method_name,
                parameters=params,
                return_type=return_type,
            ))

        return InterfaceDefinition(
            line=line, column=col,
            name=name,
            superinterfaces=superinterfaces,
            methods=methods,
            properties=properties,
        )

    def visitParamList(self, ctx: LightLangParser.ParamListContext):
        """参数列表"""
        return [self.visitParam(p) for p in ctx.param()]

    def visitParam(self, ctx: LightLangParser.ParamContext):
        """单个参数"""
        name = self._get_identifier_like_name(ctx.identifier_like())
        line = ctx.start.line
        col = ctx.start.column

        typ = None
        if ctx.typeAnnotation():
            typ = self.visitTypeAnnotation(ctx.typeAnnotation())

        default = None
        if ctx.expr():
            default = self.visitExpr(ctx.expr())

        return Parameter(line=line, column=col, name=name,
                         type_annotation=typ, default_value=default)

    def _get_identifier_like_name(self, ctx):
        """从 identifier_like 规则中提取名称文本"""
        if ctx is None:
            return ''
        if ctx.ID():
            return ctx.ID().getText()
        # 内置类型token也可以作为标识符名
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
        if ctx.K_TRUE():
            return ctx.K_TRUE().getText()
        if ctx.K_FALSE():
            return ctx.K_FALSE().getText()
        if ctx.K_NULL():
            return ctx.K_NULL().getText()
        # fallback
        return ctx.getText()

    def visitBlock(self, ctx: LightLangParser.BlockContext):
        """代码块（语句列表）"""
        stmts = []
        for child in ctx.getChildren():
            # 处理BlockContentContext
            if isinstance(child, LightLangParser.BlockContentContext):
                # 检查是否有K_END标记
                if child.K_END():
                    # 遇到"结束"标记，终止块
                    break
                inner = child.stmt()
                if inner:
                    stmt = self.visitStmt(inner)
                    if stmt:
                        stmts.append(stmt)
            elif isinstance(child, LightLangParser.StmtContext):
                stmt = self.visitStmt(child)
                if stmt:
                    stmts.append(stmt)
            elif isinstance(child, LightLangParser.DefinitionContext):
                # 块内嵌套定义
                defn = self.visitDefinition(child)
                if defn:
                    stmts.append(defn)
        return stmts

    def visitDefinition(self, ctx: LightLangParser.DefinitionContext):
        """定义分发"""
        if ctx.paragraphDef():
            return self.visitParagraphDef(ctx.paragraphDef())
        elif ctx.classDef():
            return self.visitClassDef(ctx.classDef())
        elif ctx.interfaceDef():
            return self.visitInterfaceDef(ctx.interfaceDef())
        elif ctx.dataTypeDef():
            return self.visitDataTypeDef(ctx.dataTypeDef())
        elif ctx.errorTypeDef():
            return self.visitErrorTypeDef(ctx.errorTypeDef())
        elif ctx.decoratorDef():
            return self.visitDecoratorDef(ctx.decoratorDef())
        return None

    # ----- 类型定义 -----

    def visitDataTypeDef(self, ctx: LightLangParser.DataTypeDefContext):
        """数据类型定义"""
        name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column
        fields = [self.visitDataTypeField(f) for f in ctx.dataTypeField()]
        return DataTypeDefinition(line=line, column=col, name=name, fields=fields)

    def visitErrorTypeDef(self, ctx: LightLangParser.ErrorTypeDefContext):
        """错误类型定义"""
        name = ctx.ID().getText()
        line = ctx.start.line
        col = ctx.start.column
        fields = [self.visitDataTypeField(f) for f in ctx.dataTypeField()]
        return ErrorTypeDefinition(line=line, column=col, name=name, fields=fields)

    def visitDataTypeField(self, ctx: LightLangParser.DataTypeFieldContext):
        """类型字段"""
        name = ctx.ID().getText()
        typ = self.visitTypeAnnotation(ctx.typeAnnotation())
        line = ctx.start.line
        col = ctx.start.column
        return DataTypeField(line=line, column=col, name=name, type_annotation=typ)

    # ----- 导入/导出 -----

    def visitImportStmt(self, ctx: LightLangParser.ImportStmtContext):
        """导入语句"""
        line = ctx.start.line
        col = ctx.start.column

        # 从...导入 格式
        if ctx.K_FROM():
            path_ctx = ctx.path()
            module = "".join(t.getText() for t in path_ctx.getChildren())
            names = [self.visitImportItem(item) for item in ctx.importList().importItem()]
            return ImportStatement(line=line, column=col, module=module, names=names)

        # 直接导入
        names = [self.visitImportItem(item) for item in ctx.importList().importItem()]
        return ImportStatement(line=line, column=col, module="", names=names)

    def visitImportItem(self, ctx: LightLangParser.ImportItemContext):
        """导入项"""
        return ctx.ID().getText()

    def visitExportStmt(self, ctx: LightLangParser.ExportStmtContext):
        """导出语句"""
        line = ctx.start.line
        col = ctx.start.column
        name = ctx.ID().getText()
        return ExportStatement(line=line, column=col, name=name)

    # ----- 变量声明和赋值 -----

    def visitVarDecl(self, ctx: LightLangParser.VarDeclContext):
        """变量声明"""
        line = ctx.start.line
        col = ctx.start.column

        # 解构赋值：设 (甲, 乙) 为 元组 — 有 LPAREN
        if ctx.LPAREN():
            variables = [self._get_identifier_like_name(il) for il in ctx.identifier_like()]
            value = self.visitExpr(ctx.expr())
            return DestructuringAssignment(line=line, column=col,
                                           variables=variables, value=value)

        # 己属性赋值：设 己属性名 为 值 — 有 K_SELF
        if ctx.K_SELF():
            prop = ctx.ID(0).getText() if ctx.ID() else ''
            if prop:
                target = PropertyAccess(line=line, column=col,
                                        obj=SelfReference(line=line, column=col),
                                        property_name=prop)
                value = self.visitExpr(ctx.expr()) if ctx.expr() else None
                return Assignment(line=line, column=col, target=target, value=value)

        # 普通变量声明：设 甲 为 值 — 用 identifier_like 获取变量名
        ils = ctx.identifier_like()
        if ils and len(ils) > 0:
            name = self._get_identifier_like_name(ils[0] if isinstance(ils, list) else ils)
            value = self.visitExpr(ctx.expr()) if ctx.expr() else None

            # 特殊处理：以"己"开头的变量名 -> 转换为属性赋值
            if name.startswith('己'):
                prop_name = name[1:]  # 去掉"己"前缀
                if prop_name:  # 确保有属性名
                    target = PropertyAccess(line=line, column=col,
                                            obj=SelfReference(line=line, column=col),
                                            property_name=prop_name)
                    return Assignment(line=line, column=col, target=target, value=value)

            return VariableDeclaration(line=line, column=col, name=name, value=value)

        # 兼容旧语法：定义 变量名 等于 值。 (K_DEFINE ID)
        if ctx.ID():
            ids = ctx.ID()
            name = ids[0].getText() if isinstance(ids, list) else ids.getText()
            value = self.visitExpr(ctx.expr()) if ctx.expr() else None
            return VariableDeclaration(line=line, column=col, name=name, value=value)

        return None

    def visitAssignStmt(self, ctx: LightLangParser.AssignStmtContext):
        """赋值语句"""
        line = ctx.start.line
        col = ctx.start.column

        # 己属性赋值：己属性名 = 值
        if ctx.K_SELF():
            prop = ctx.ID().getText() if ctx.ID() else ''
            value = self.visitExpr(ctx.expr(0))
            target = PropertyAccess(line=line, column=col,
                                    obj=SelfReference(line=line, column=col),
                                    property_name=prop)
            return Assignment(line=line, column=col, target=target, value=value)

        # 属性赋值：primary . ID = 值
        if ctx.primary() and ctx.DOT():
            expr = self.visitPrimary(ctx.primary())
            prop = ctx.ID().getText()
            value = self.visitExpr(ctx.expr(0))
            target = PropertyAccess(line=line, column=col,
                                    obj=expr, property_name=prop)
            return Assignment(line=line, column=col, target=target, value=value)

        # 属性赋值：primary 的 ID = 值（「的」作为属性访问运算符）
        if ctx.primary() and ctx.K_DE():
            expr = self.visitPrimary(ctx.primary())
            prop = ctx.ID().getText()
            value = self.visitExpr(ctx.expr(0))
            target = PropertyAccess(line=line, column=col,
                                    obj=expr, property_name=prop)
            return Assignment(line=line, column=col, target=target, value=value)

        # 索引赋值：primary [ expr ] = 值（甲[丁] = 值）
        if ctx.primary() and ctx.LBRACKET():
            obj = self.visitPrimary(ctx.primary())
            index = self.visitExpr(ctx.expr(0))
            value = self.visitExpr(ctx.expr(1))
            target = IndexAccess(line=line, column=col, obj=obj, index=index)
            return Assignment(line=line, column=col, target=target, value=value)

        # 简单变量赋值：甲 = 值（使用 identifier_like）
        value = self.visitExpr(ctx.expr(0))
        if ctx.identifier_like():
            name = self._get_identifier_like_name(ctx.identifier_like())
        elif ctx.ID():
            name = ctx.ID().getText()
        else:
            name = ''
        # 特殊处理：以"己"开头的变量名
        if name.startswith('己'):
            prop_name = name[1:]
            if prop_name:
                target = PropertyAccess(line=line, column=col,
                                        obj=SelfReference(line=line, column=col),
                                        property_name=prop_name)
                return Assignment(line=line, column=col, target=target, value=value)

        target = Identifier(line=line, column=col, name=name)
        return Assignment(line=line, column=col, target=target, value=value)

    def visitCompoundAssignStmt(self, ctx: LightLangParser.CompoundAssignStmtContext):
        """复合赋值语句：甲 加上 1 → 甲 += 1"""
        line = ctx.start.line
        col = ctx.start.column

        # 变量名
        name = self._get_identifier_like_name(ctx.identifier_like())

        # 复合赋值运算符映射
        op_map = {
            'K_PLUS_ASSIGN': '加',
            'K_MINUS_ASSIGN': '减',
            'K_MULTIPLY_ASSIGN': '乘',
            'K_DIVIDE_ASSIGN': '除',
            'K_MOD_ASSIGN': '模',
            'K_POW_ASSIGN': '幂',
        }

        # 获取运算符（从 compoundAssignOp 规则的 token 中获取）
        op_ctx = ctx.compoundAssignOp()
        if op_ctx.K_PLUS_ASSIGN():
            operator = '加'
        elif op_ctx.K_MINUS_ASSIGN():
            operator = '减'
        elif op_ctx.K_MULTIPLY_ASSIGN():
            operator = '乘'
        elif op_ctx.K_DIVIDE_ASSIGN():
            operator = '除'
        elif op_ctx.K_MOD_ASSIGN():
            operator = '模'
        elif op_ctx.K_POW_ASSIGN():
            operator = '幂'
        else:
            operator = '加'  # fallback

        # 值
        value = self.visitExpr(ctx.expr())

        return CompoundAssignment(line=line, column=col, target=name, operator=operator, value=value)