"""
光明（Light）编程语言 - 表达式解析混入类

提供所有表达式级别解析方法，包括：
- 算术表达式（加、减、乘、除）
- 比较表达式
- 逻辑表达式
- 基本表达式（数字、字符串、标识符、括号等）
- 后缀表达式（函数调用、成员访问、索引访问）
- 列表/字典字面量
- Lambda 表达式
- 字符串插值
"""

from typing import List, Any, Optional, Union
from tokens import Token, TokenType
from keywords import VERB_ARITY, ALL_KEYWORDS, KEYWORDS_SPECIAL, ALL_KEYWORDS
from ast_nodes_v3 import *
from ast_nodes import UnwrapExpression
from parser_core import ParseError

# 作为表达式开头的关键字（不应在参数解析中中断）
_EXPR_START_KEYWORDS = frozenset({
    '己', '自',     # self引用
    '非',           # 一元取反
    '等待',         # await表达式
    '如果',         # 三元条件表达式
    '函数',         # 匿名函数
    '接收',         # lambda
    '真', '假', '空',  # 特殊值
})


class ParserExprMixin:
    """表达式解析混入类"""
    
    def _is_expr_terminator(self) -> bool:
        """检查当前 token 是否是表达式终止符"""
        tok = self._current()
        if tok is None:
            return True
        if tok.type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.DOT, TokenType.PERIOD):
            return True
        return False
    
    def _parse_expr(self) -> ASTNode:
        """解析表达式（支持管道操作符、逻辑运算符和后置三元）"""
        # 明确标注不支持的特性（P1-3）：海象运算符 :=
        if self._match(TokenType.WALRUS):
            tok = self._current()
            self._error(
                "光明不支持海象运算符 ':='。请使用「设」语句声明变量后再使用。",
                tok.line, tok.col
            )
        
        left = self._parse_logical_expr()
        
        # 后置三元表达式：值 如果 条件 否则 值
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '如果':
            self._consume(TokenType.KEYWORD, '如果')
            condition = self._parse_logical_expr()
            else_expr = None
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '否则':
                self._consume(TokenType.KEYWORD, '否则')
                else_expr = self._parse_expr()
            return ConditionalExpression(condition, left, else_expr)
        
        # 管道操作符 / 因果链
        stages = [left]
        connector = None
        
        while self._match(TokenType.ARROW) or self._match(TokenType.COMMA):
            if self._match(TokenType.ARROW):
                self._consume(TokenType.ARROW)
                connector = 'arrow'  # 管道：函数组合
            else:
                self._consume(TokenType.COMMA)
                connector = 'comma'  # 因果链：条件,动作
            
            right = self._parse_logical_expr()
            stages.append(right)
        
        if len(stages) > 1:
            return Pipeline(stages, connector=connector or 'comma')
        
        return left
    
    def _parse_logical_expr(self) -> ASTNode:
        """解析逻辑表达式（且/与, 或）"""
        # 明确标注不支持的特性（P1-3）：海象运算符 :=
        if self._match(TokenType.WALRUS):
            tok = self._current()
            self._error(
                "光明不支持海象运算符 ':='。请使用「设」语句声明变量后再使用。",
                tok.line, tok.col
            )
        
        left = self._parse_comparison()
        
        while self._current() and not self._is_expr_terminator():
            tok = self._current()
            if tok.type == TokenType.KEYWORD and tok.value in self.LOGICAL_OP_MAP:
                op = self._consume().value
                # 跳过 NEWLINE/INDENT/DEDENT（支持多行表达式）
                while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._consume()
                right = self._parse_comparison()
                left = BinaryOp(self.LOGICAL_OP_MAP[op], left, right)
            else:
                break
        
        return left
    
    def _parse_comparison(self) -> ASTNode:
        """解析比较表达式"""
        left = self._parse_add_expr()
        
        while self._current() and not self._is_expr_terminator():
            tok = self._current()
            # 明确标注不支持的特性（P1-3）：海象运算符 :=
            if tok.type == TokenType.WALRUS:
                self._error(
                    "光明不支持海象运算符 ':='。请使用「设」语句声明变量后再使用。",
                    tok.line, tok.col
                )
            # 遇到"那么"关键字，停止解析
            if tok.type == TokenType.KEYWORD and tok.value == '那么':
                break
            if tok.type == TokenType.KEYWORD and tok.value in self.OPERATOR_VERBS:
                op = self._consume().value
                right = self._parse_add_expr()
                left = BinaryOp(self.COMPARISON_OP_MAP.get(op, op), left, right)
            elif tok.type == TokenType.LESS:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('<', left, right)
            elif tok.type == TokenType.GREATER:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('>', left, right)
            elif tok.type == TokenType.LESS_EQUAL:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('<=', left, right)
            elif tok.type == TokenType.GREATER_EQUAL:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('>=', left, right)
            elif tok.type == TokenType.EQ_EQ:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('==', left, right)
            elif tok.type == TokenType.NOT_EQ:
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('!=', left, right)
            # in / not in 运算符：在 / 于 / 不在 / 不于
            elif tok.type == TokenType.KEYWORD and tok.value in ('在', '于'):
                self._consume()
                right = self._parse_add_expr()
                left = BinaryOp('in', left, right)
            elif tok.type == TokenType.IDENTIFIER and tok.value == '不' and \
                 self._peek(1) and self._peek(1).type == TokenType.KEYWORD and \
                 self._peek(1).value in ('在', '于'):
                self._consume()  # 不
                self._consume()  # 在/于
                right = self._parse_add_expr()
                left = BinaryOp('not in', left, right)
            else:
                break
        
        return left
    
    def _parse_add_expr(self) -> ASTNode:
        """解析加减表达式"""
        left = self._parse_mul_expr()
        
        while self._current() and not self._is_expr_terminator():
            tok = self._current()
            # 支持：加、减、加上、减去
            if tok.type == TokenType.KEYWORD and tok.value in self.ADD_OP_MAP:
                op = self._consume().value
                right = self._parse_mul_expr()
                left = BinaryOp(self.ADD_OP_MAP[op], left, right)
            # "减去"被lexer保护为IDENTIFIER，也需识别
            elif tok.type == TokenType.IDENTIFIER and tok.value in self.ADD_OP_MAP:
                op = self._consume().value
                right = self._parse_mul_expr()
                left = BinaryOp(self.ADD_OP_MAP[op], left, right)
            elif tok.type == TokenType.PLUS:
                # 处理 + 符号（字符串连接等）
                self._consume()
                right = self._parse_mul_expr()
                left = BinaryOp('+', left, right)
            elif tok.type == TokenType.MINUS:
                # 处理 - 符号（减法）
                self._consume()
                right = self._parse_mul_expr()
                left = BinaryOp('-', left, right)
            else:
                break
        
        # 检查是否为范围表达式：表达式 至 表达式 或 表达式 到 表达式
        # 例如：i加上1至n、0至n减去1
        _range_tok = self._current()
        if _range_tok and _range_tok.type == TokenType.KEYWORD and _range_tok.value in ('至', '到'):
            self._consume(TokenType.KEYWORD)
            end_expr = self._parse_add_expr()
            
            # 检查是否有步长：步 数字
            step_expr = None
            step_tok = self._current()
            if step_tok and step_tok.type == TokenType.KEYWORD and step_tok.value == '步':
                self._consume(TokenType.KEYWORD, '步')
                step_expr = self._parse_add_expr()
            
            return RangeExpr(left, end_expr, step_expr)
        
        return left
    
    def _parse_mul_expr(self) -> ASTNode:
        """解析乘除表达式"""
        left = self._parse_power_expr()
        
        while self._current() and not self._is_expr_terminator():
            tok = self._current()
            # 支持：乘、除、乘以、除以
            if tok.type == TokenType.KEYWORD and tok.value in self.MUL_OP_MAP:
                op = self._consume().value
                # 检查右操作数是否有效
                next_tok = self._current()
                if next_tok and next_tok.type not in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE, TokenType.NEWLINE, TokenType.EOF, TokenType.COMMA, TokenType.COLON):
                    # 右侧解析power_expr，保证乘除优先于加减，但幂运算优先级更高
                    right = self._parse_power_expr()
                    left = BinaryOp(self.MUL_OP_MAP[op], left, right)
                else:
                    # 右操作数无效，跳过这个运算符
                    pass
            # "取余"等被lexer保护为IDENTIFIER，也需识别
            elif tok.type == TokenType.IDENTIFIER and tok.value in self.MUL_OP_MAP:
                op = self._consume().value
                right = self._parse_power_expr()
                left = BinaryOp(self.MUL_OP_MAP[op], left, right)
            elif tok.type == TokenType.STAR:
                self._consume()
                # 检查是否是 ** （幂运算）
                if self._current() and self._current().type == TokenType.STAR:
                    self._consume()
                    right = self._parse_power_expr()
                    left = BinaryOp('**', left, right)
                else:
                    right = self._parse_power_expr()
                    left = BinaryOp('*', left, right)
            elif tok.type == TokenType.SLASH:
                self._consume()
                # 检查是否是 // （整除）
                if self._current() and self._current().type == TokenType.SLASH:
                    self._consume()
                    right = self._parse_power_expr()
                    left = BinaryOp('//', left, right)
                else:
                    right = self._parse_power_expr()
                    left = BinaryOp('/', left, right)
            elif tok.type == TokenType.PERCENT:
                self._consume()
                right = self._parse_power_expr()
                left = BinaryOp('%', left, right)
            else:
                # 遇到加减运算符或其他，返回让上层处理
                break
        
        return left
    
    def _parse_power_expr(self) -> ASTNode:
        """解析幂表达式（优先级高于乘除，右结合）"""
        left = self._parse_primary()
        
        while self._current() and not self._is_expr_terminator():
            tok = self._current()
            if tok.type == TokenType.KEYWORD and tok.value in self.POWER_OP_MAP:
                op = self._consume().value
                # 幂运算是右结合的，右侧递归调用自身
                right = self._parse_power_expr()
                left = BinaryOp(self.POWER_OP_MAP[op], left, right)
            elif tok.type == TokenType.IDENTIFIER and tok.value in self.POWER_OP_MAP:
                op = self._consume().value
                right = self._parse_power_expr()
                left = BinaryOp(self.POWER_OP_MAP[op], left, right)
            elif tok.type == TokenType.STAR:
                # 检查 ** 幂运算符号
                self._consume()
                if self._current() and self._current().type == TokenType.STAR:
                    self._consume()
                    right = self._parse_power_expr()
                    left = BinaryOp('**', left, right)
                else:
                    # 单个 * 不是幂运算，回退
                    self.pos -= 1
                    break
            else:
                break
        
        return left
    
    def _parse_primary(self) -> ASTNode:
        """解析基本表达式"""
        tok = self._current()
        
        if tok is None:
            return self._error(f"意外的输入结束")
        
        # 一元运算符：非（逻辑非）
        if tok.type == TokenType.KEYWORD and tok.value == '非':
            self._consume(TokenType.KEYWORD, '非')
            operand = self._parse_primary()
            return UnaryOp('非', operand)
        
        # 一元负号
        if tok.type == TokenType.MINUS:
            self._consume()
            operand = self._parse_primary()
            return UnaryOp('-', operand)
        
        # 一元负号（中文）：减去 / 负 作为一元运算符
        if tok.type == TokenType.KEYWORD and tok.value in ('减去', '负'):
            self._consume()
            operand = self._parse_primary()
            return UnaryOp('-', operand)
        
        # 等待表达式：等待 异步操作
        # 注意：如果等待后跟的是标识符且不是函数调用，则视为复合标识符（如「等待价值」）
        if tok.type == TokenType.KEYWORD and tok.value == '等待':
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.IDENTIFIER:
                peek2 = self._peek(2)
                if peek2 and peek2.type != TokenType.LPAREN:
                    # 复合标识符：等待 + 价值 = 等待价值
                    self._consume(TokenType.KEYWORD, '等待')
                    ident = self._consume(TokenType.IDENTIFIER).value
                    return Identifier('等待' + ident)
                # 等待 函数名() → await 表达式
                self._consume(TokenType.KEYWORD, '等待')
                expr = self._parse_expr()
                return AwaitExpr(expr)
            self._consume(TokenType.KEYWORD, '等待')
            expr = self._parse_expr()
            return AwaitExpr(expr)
        
        # 三元条件表达式：如果 条件 那么 值1 否则 值2
        # 也支持：如果 条件 则 值1 否则 值2
        if tok.type == TokenType.KEYWORD and tok.value == '如果':
            self._consume(TokenType.KEYWORD, '如果')
            condition = self._parse_expr()
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('那么', '则'):
                self._consume(TokenType.KEYWORD, self._current().value)
            then_expr = self._parse_expr()
            else_expr = None
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '否则':
                self._consume(TokenType.KEYWORD, '否则')
                else_expr = self._parse_expr()
            return ConditionalExpression(condition, then_expr, else_expr)
        
        # 括号表达式
        if tok.type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            
            # 跳过 NEWLINE/INDENT/DEDENT（支持多行括号表达式）
            while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._consume()
            
            # 支持海象运算符等价物：设 变量 为 表达式
            # 例如：(设 n 为 len(data)) → Python 的 (n := len(data))
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '设':
                self._consume(TokenType.KEYWORD, '设')
                # 变量名
                _walrus_saved = self.pos
                _walrus_name = self._parse_primary()
                if not isinstance(_walrus_name, Identifier):
                    self.pos = _walrus_saved
                    # 不是海象运算符，回退并重新解析
                    self._consume(TokenType.LPAREN)  # 重新开始
                    expr = self._parse_expr()
                    self._consume(TokenType.RPAREN)
                    if isinstance(expr, Pipeline):
                        return TupleLiteral(expr.stages)
                    return self._parse_postfix(expr)
                # 为 或 等于
                if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('为', '等于'):
                    self._consume()
                else:
                    self.pos = _walrus_saved
                    self._consume(TokenType.LPAREN)
                    expr = self._parse_expr()
                    self._consume(TokenType.RPAREN)
                    if isinstance(expr, Pipeline):
                        return TupleLiteral(expr.stages)
                    return self._parse_postfix(expr)
                # 值表达式
                _walrus_value = self._parse_expr()
                self._consume(TokenType.RPAREN)
                from ast_nodes_v3 import AssignmentExpression
                return AssignmentExpression(_walrus_name.name, _walrus_value)
            
            expr = self._parse_expr()
            # 跳过 NEWLINE/INDENT/DEDENT（支持多行括号表达式）
            while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._consume()
            self._consume(TokenType.RPAREN)
            # 如果括号内是逗号分隔的表达式（Pipeline），视为元组字面量
            # 例如：(x, y) → TupleLiteral，而非 Pipeline(x → y)
            if isinstance(expr, Pipeline):
                return TupleLiteral(expr.stages)
            return self._parse_postfix(expr)
        
        # 数字
        if tok.type == TokenType.NUMBER:
            self._consume()
            expr = NumberLiteral(tok.value)
            
            # 检查是否为范围表达式：1至10 或 1到10 或 0至len(lst)减去1
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('至', '到'):
                self._consume(TokenType.KEYWORD)  # 消耗「至」或「到」
                # end表达式可以是数字或任意表达式
                end_expr = self._parse_add_expr()
                
                # 检查是否有步长：步 数字
                step_expr = None
                step_tok = self._current()
                if step_tok and step_tok.type == TokenType.KEYWORD and step_tok.value == '步':
                    self._consume(TokenType.KEYWORD, '步')
                    step_expr = self._parse_add_expr()
                
                expr = RangeExpr(expr, end_expr, step_expr)
            
            return self._parse_postfix(expr)

        # 中文数字
        if tok.type == TokenType.CHINESE_NUM:
            self._consume()
            
            # 检查中文数字后是否紧接标识符（如"三倍"作为函数名）
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.IDENTIFIER:
                id_name = self._consume(TokenType.IDENTIFIER).value
                expr = Identifier(f"{tok.value}{id_name}")
                return self._parse_postfix(expr)
            
            expr = NumberLiteral(tok.value)
            return self._parse_postfix(expr)

        # C风格匿名函数：函数(params){body}
        if tok.type == TokenType.KEYWORD and tok.value == '函数':
            return self._parse_c_anonymous_function()

        # 匿名函数：接收 参数：返回 表达式。
        if tok.type == TokenType.KEYWORD and tok.value == '接收':
            return self._parse_lambda()

        # 字符串（支持插值检测）
        if tok.type == TokenType.STRING:
            self._consume()
            # 检测插值表达式 {xxx}
            interpolated = self._parse_string_interpolation(tok.value, tok.line, tok.col)
            if interpolated is not None:
                return self._parse_postfix(interpolated)
            expr = StringLiteral(tok.value)
            return self._parse_postfix(expr)

        # 特殊值（真、假、空）
        if tok.type == TokenType.KEYWORD and tok.value in KEYWORDS_SPECIAL:
            self._consume()
            # 转换为对应的Python值
            if tok.value == '真':
                expr = Identifier('True')
            elif tok.value == '假':
                expr = Identifier('False')
            else:  # '空'
                expr = Identifier('None')
            return self._parse_postfix(expr)

        # 段落调用：《段名》(参数)
        if tok.type == TokenType.LBOOK:
            expr = self._parse_paragraph_call()
            return self._parse_postfix(expr)

        # 动词调用（KEYWORD token 且值为动词，但排除运算符动词）
        # 运算符动词由 _parse_add_expr 等方法处理
        if tok.type == TokenType.KEYWORD and tok.value in VERB_ARITY and tok.value not in self.OPERATOR_VERBS:
            verb_name = tok.value
            # 检查下一个token是否是有效的表达式起始符
            # 如果不是（如NEWLINE、EOF、RPAREN等），则当作变量名处理
            # 修复：标准差等统计函数名被用作变量名时导致的ParseError
            _next = self._peek(1)
            if _next and _next.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.RPAREN,
                                         TokenType.RBRACKET, TokenType.RBRACE, TokenType.COMMA,
                                         TokenType.COLON, TokenType.DOT, TokenType.PERIOD):
                self._consume()
                return self._parse_postfix(Identifier(verb_name))
            self._consume()
            
            # 特殊处理：新建（类实例化）
            if verb_name == '新建':
                # 新建 类名 参数...
                # 类名可能由多个token组成（如"空类"中"空"是KEYWORD，"类"是KEYWORD）
                class_name_parts = []
                while self._current():
                    ct = self._current()
                    if ct.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        class_name_parts.append(ct.value)
                        self._consume()
                    else:
                        break
                class_name = ''.join(class_name_parts)
                
                if not class_name:
                    return self._error("期望类名")
                
                # 收集参数（支持括号式和无括号式）
                args = []
                if self._current() and self._current().type == TokenType.LPAREN:
                    # 括号式参数：新建 类名(参数1, 参数2)
                    self._consume(TokenType.LPAREN)
                    while not self._match(TokenType.RPAREN):
                        arg = self._parse_comparison()
                        if arg is not None:
                            args.append(arg)
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                    self._consume(TokenType.RPAREN)
                else:
                    # 无括号参数
                    while self._current():
                        next_tok = self._current()
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                            break
                        if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS and next_tok.value not in _EXPR_START_KEYWORDS:
                            break
                        arg = self._collect_primary_arg()
                        if arg:
                            args.append(arg)
                        else:
                            break
                
                expr = ClassInstantiation(class_name, args)
                return self._parse_postfix(expr)
            
            # 收集参数（元数驱动）
            arity = VERB_ARITY[verb_name]
            args = []

            if arity == 0:
                # 无参数函数：支持 "刷新输出" 或 "刷新输出()"
                if self._current() and self._current().type == TokenType.LPAREN:
                    self._consume(TokenType.LPAREN)
                    # 跳过可选的空格/内容直到右括号
                    while self._current() and self._current().type != TokenType.RPAREN:
                        self._consume()
                    if self._current() and self._current().type == TokenType.RPAREN:
                        self._consume(TokenType.RPAREN)
            elif arity == -1:
                # 可变参数：收集到阻断符为止
                # 检查是否使用了括号语法
                if self._current() and self._current().type == TokenType.LPAREN:
                    # 括号式参数：列(参数1, 参数2, 参数3)
                    self._consume(TokenType.LPAREN)
                    while not self._match(TokenType.RPAREN):
                        if self._current() and self._current().type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            continue
                        # 支持 *args / **kwargs 展开
                        if self._current() and self._current().type == TokenType.STAR:
                            self._consume(TokenType.STAR)
                            if self._current() and self._current().type == TokenType.STAR:
                                self._consume(TokenType.STAR)
                                arg = self._parse_logical_expr()
                                if arg and isinstance(arg, Identifier):
                                    args.append(Identifier(f'**{arg.name}'))
                            else:
                                arg = self._parse_logical_expr()
                                if arg and isinstance(arg, Identifier):
                                    args.append(Identifier(f'*{arg.name}'))
                            if self._match(TokenType.COMMA):
                                self._consume(TokenType.COMMA)
                            continue
                        arg = self._parse_logical_expr()
                        if arg:
                            args.append(arg)
                        else:
                            break
                    if self._current() and self._current().type == TokenType.RPAREN:
                        self._consume(TokenType.RPAREN)
                else:
                    # 无括号式：列 参数1 参数2 参数3
                    # 支持逗号分隔参数，如：输出 "答案:", 42。
                    while self._current():
                        next_tok = self._current()
                        # 逗号是参数分隔符，不是管道运算符
                        if next_tok.type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            continue
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.RPAREN, TokenType.RBRACKET,
                                             TokenType.NEWLINE, TokenType.DEDENT, TokenType.INDENT):
                            break
                        if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS and next_tok.value not in _EXPR_START_KEYWORDS:
                            break
                        # 收集完整表达式（支持嵌套函数调用、比较和逻辑运算符）
                        arg = self._parse_logical_expr()
                        if arg:
                            args.append(arg)
                        else:
                            break
            else:
                # 固定参数数量（使用完整表达式解析，支持嵌套函数调用和比较运算符）
                # 检查是否使用了括号语法：动词(参数1, 参数2)
                if self._current() and self._current().type == TokenType.LPAREN:
                    # 括号式参数：列表追加(成绩, 分数)
                    self._consume(TokenType.LPAREN)
                    collected = 0
                    while not self._match(TokenType.RPAREN) and collected < arity:
                        if self._current() and self._current().type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            continue
                        arg = self._parse_logical_expr()
                        if arg:
                            args.append(arg)
                            collected += 1
                        else:
                            break
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                    # 跳过剩余的 token 直到右括号
                    while self._current() and self._current().type != TokenType.RPAREN:
                        self._consume()
                    if self._current() and self._current().type == TokenType.RPAREN:
                        self._consume(TokenType.RPAREN)
                else:
                    # 无括号式：列表追加 成绩 分数
                    for _ in range(arity):
                        if self._current() and self._current().type not in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN):
                            arg = self._parse_comparison()
                            if arg:
                                args.append(arg)

            expr = ParagraphCall(verb_name, args)
            return self._parse_postfix(expr)

        # 标识符：可能带参数（段落调用）
        if tok.type == TokenType.IDENTIFIER:
            return self._collect_single_arg()

        # 运算符动词作为函数调用（如"除(10, 0)"或"幂 二 十"）
        if tok.type == TokenType.KEYWORD and tok.value in self.OPERATOR_VERBS:
            name = tok.value
            next_tok = self._peek(1)
            # 检测：如果后面是块关键字（那么、否则、结束、当）或标点（。，）
            # 且没有括号，则将此运算符关键字作为标识符（变量名）处理
            if not next_tok or next_tok.type == TokenType.LPAREN:
                pass  # 下面的正常分支处理括号
            elif (next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS) or \
                 next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN,
                                    TokenType.RBRACKET, TokenType.COLON, TokenType.EOF):
                if next_tok.type != TokenType.LPAREN:
                    # 当作变量名处理，如 "如果操作等于加那么..." 中的 "加"
                    self._consume()
                    return self._parse_postfix(Identifier(name))
            if next_tok and next_tok.type == TokenType.LPAREN:
                # 函数调用 with parentheses
                self._consume()
                self._consume(TokenType.LPAREN)
                args = []
                while self._current() and self._current().type != TokenType.RPAREN:
                    if self._current().type == TokenType.COMMA:
                        self._consume(TokenType.COMMA)
                        continue
                    arg = self._parse_comparison()
                    if arg:
                        args.append(arg)
                    else:
                        break
                self._consume(TokenType.RPAREN)
                expr = ParagraphCall(name, args)
                return self._parse_postfix(expr)
            else:
                # 无括号：动词 参数1 参数2（如"幂 二 十"）
                # 使用元数驱动参数收集
                self._consume()
                arity = VERB_ARITY.get(name, 2)
                args = []
                if arity == -1:
                    # 可变参数
                    while self._current():
                        next_tok = self._current()
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                            break
                        if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS and next_tok.value not in _EXPR_START_KEYWORDS:
                            break
                        arg = self._parse_comparison()
                        if arg:
                            args.append(arg)
                        else:
                            break
                else:
                    # 固定参数
                    for _ in range(arity):
                        if self._current() and self._current().type not in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN):
                            arg = self._parse_comparison()
                            if arg:
                                args.append(arg)
                expr = ParagraphCall(name, args)
                return self._parse_postfix(expr)

        # 字典字面量 {key: value, ...}
        if tok.type == TokenType.LBRACE:
            return self._parse_dict_literal()

        # 列表字面量 [元素1, 元素2, ...]
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_literal()

        # Self引用：己.属性名 或 己属性名（类方法中表示self）
        # 注意：己单独使用时，由代码生成器根据 _in_class_method 决定是否映射为 self
        # 这样可以避免将参数名 己（天干地支）错误映射为 self
        if tok.type == TokenType.KEYWORD and tok.value == '己':
            self._consume()
            # 支持 己.属性名 语法（带点号）
            if self._current() and self._current().type == TokenType.DOT:
                self._consume(TokenType.DOT)
                # 收集属性名
                name_parts = []
                while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 遇到赋值运算符或常见分隔符时停止
                    if self._current().value in ('等于', '为', '加', '减', '乘', '除', '模',
                                                  '大于', '小于', '大于等于', '小于等于', '不等于',
                                                  '与', '或', '非', '在', '到', '从',
                                                  '加上', '减去', '乘以', '除以', '模以', '幂', '幂以', '取余',
                                                  '且', '或', '不在', '于'):
                        break
                    name_parts.append(self._consume().value)
                if name_parts:
                    attr_name = ''.join(name_parts)
                    expr = Identifier(f"self.{attr_name}")
                    return self._parse_postfix(expr)
                else:
                    return self._error("己.后应跟属性名", tok.line, tok.col)
            # 无点号：己属性名 或 己（单独使用）
            name_parts = []
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 遇到赋值运算符或常见分隔符时停止
                if self._current().value in ('等于', '为', '加', '减', '乘', '除', '模',
                                              '大于', '小于', '大于等于', '小于等于', '不等于',
                                              '与', '或', '非', '在', '到', '从',
                                              '加上', '减去', '乘以', '除以', '模以', '幂', '幂以', '取余',
                                              '且', '或', '不在', '于'):
                    break
                name_parts.append(self._consume().value)
            if name_parts:
                attr_name = ''.join(name_parts)
                # 代码生成器根据 _in_class_method 决定是否加 self. 前缀
                expr = Identifier(f"己.{attr_name}")
                return self._parse_postfix(expr)
            else:
                # 己单独使用，由代码生成器根据 _in_class_method 决定是否映射为 self
                expr = Identifier("己")
                return self._parse_postfix(expr)

        # Super引用：父.方法名() → super().方法名()
        if tok.type == TokenType.KEYWORD and tok.value == '父':
            self._consume()
            expr = Identifier("super()")
            return self._parse_postfix(expr)

        # 段落调用：函数/段落 段名(参数)
        if tok.type == TokenType.KEYWORD and tok.value in ('函数', '段落'):
            self._consume()
            name_parts = []
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                name_parts.append(self._consume().value)
            if not name_parts:
                return self._error("函数/段落调用后应跟段名", tok.line, tok.col)
            name = ''.join(name_parts)
            if self._current() and self._current().type == TokenType.LPAREN:
                self._consume(TokenType.LPAREN)
                args = []
                while self._current() and self._current().type != TokenType.RPAREN:
                    if self._current().type == TokenType.COMMA:
                        self._consume(TokenType.COMMA)
                        continue
                    args.append(self._parse_expr())
                self._consume(TokenType.RPAREN)
                expr = ParagraphCall(name, args)
            else:
                expr = Identifier(name)
            return self._parse_postfix(expr)
        
        # 其他关键字作为标识符处理（如参数名中的关键字部分）
        if tok.type == TokenType.KEYWORD:
            name = tok.value
            self._consume()
            return self._parse_postfix(Identifier(name))
        
        # f-string
        if tok.type == TokenType.FSTRING:
            str_val = self._consume().value
            from ast_nodes_v3 import StringInterpolation
            parts = self._parse_fstring_parts(str_val)
            return self._parse_postfix(StringInterpolation(parts))

        raise ParseError(f"意外的标记: {tok.type} = '{tok.value}'（附近: '{tok.value}'）", tok.line, tok.col)

    def _collect_primary_arg(self) -> Optional[ASTNode]:
        """收集单个primary参数（不进行段落调用检测）"""
        tok = self._current()
        if tok is None:
            return None

        # 数字
        if tok.type == TokenType.NUMBER:
            self._consume()
            return NumberLiteral(tok.value)

        # 中文数字
        if tok.type == TokenType.CHINESE_NUM:
            self._consume()
            return NumberLiteral(tok.value)

        # 字符串
        if tok.type == TokenType.STRING:
            self._consume()
            return StringLiteral(tok.value)

        # 标识符（检查是否为函数调用，如"字符串长度 日期"）
        if tok.type == TokenType.IDENTIFIER:
            name = tok.value
            self._consume()
            
            # 函数名含动词关键字合并（同 _collect_single_arg 逻辑）
            if self._current() and self._current().type == TokenType.KEYWORD:
                _fn_saved_pos = self.pos
                _fn_prev = tok
                _fn_parts2 = [name]
                _fn_stop2 = frozenset({
                    '为','等于','接收','返回','令','循环','断言','输出',
                    '如果','否则','那么','若','则','当','遍历','设','定义',
                    '类','构造','函数','段落','尝试','捕获','抛出','最终','导入',
                    '导出','从','真','假','空','且','或','非','与','等待',
                    '匹配','情况','的','之','对','步','至','到','在','于','中的',
                    '包含',  # 动词停止符
                })
                while self._current():
                    _ct = self._current()
                    if _ct.type == TokenType.KEYWORD and _ct.value not in _fn_stop2:
                        if _fn_prev.col + len(_fn_prev.value) != _ct.col:
                            break
                        _fn_parts2.append(_ct.value)
                        _fn_prev = _ct
                        self._consume()
                    elif _ct.type == TokenType.IDENTIFIER:
                        if _fn_prev.col + len(_fn_prev.value) != _ct.col:
                            break
                        _fn_parts2.append(_ct.value)
                        _fn_prev = _ct
                        self._consume()
                    else:
                        break
                if self._current() and self._current().type == TokenType.LPAREN:
                    name = ''.join(_fn_parts2)
                else:
                    self.pos = _fn_saved_pos
            
            # 检查下一个token是否是参数（嵌套函数调用模式）
            next_tok = self._current()
            if next_tok and next_tok.type in (TokenType.NUMBER, TokenType.CHINESE_NUM, TokenType.STRING,
                                               TokenType.IDENTIFIER, TokenType.LBOOK):
                # 可能是函数调用，尝试收集后续参数
                args = []
                while self._current():
                    nt = self._current()
                    # 停止条件
                    if nt.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                        break
                    # 遇到动词运算符停止（如加、减、大于等）
                    if nt.type == TokenType.KEYWORD and nt.value in self.OPERATOR_VERBS:
                        break
                    # 遇到其他关键字停止
                    if nt.type == TokenType.KEYWORD and nt.value in ALL_KEYWORDS:
                        break
                    
                    # 收集参数
                    if nt.type == TokenType.NUMBER:
                        args.append(NumberLiteral(self._consume().value))
                    elif nt.type == TokenType.CHINESE_NUM:
                        args.append(NumberLiteral(self._consume().value))
                    elif nt.type == TokenType.STRING:
                        args.append(StringLiteral(self._consume().value))
                    elif nt.type == TokenType.IDENTIFIER:
                        args.append(Identifier(self._consume().value))
                    elif nt.type == TokenType.LBOOK:
                        args.append(self._parse_paragraph_call())
                    else:
                        break
                
                if args:
                    expr = ParagraphCall(name, args)
                    return self._parse_postfix(expr)
            
            # 简单标识符
            expr = Identifier(name)
            return self._parse_postfix(expr)

        # 关键字作为标识符（检查是否为函数调用）
        if tok.type == TokenType.KEYWORD:
            name = tok.value
            self._consume()
            
            # 检查下一个token是否构成函数调用
            next_tok = self._current()
            if next_tok and next_tok.type in (TokenType.NUMBER, TokenType.CHINESE_NUM, TokenType.STRING,
                                               TokenType.IDENTIFIER):
                # 可能是函数调用，尝试收集后续参数
                args = []
                while self._current():
                    nt = self._current()
                    # 停止条件
                    if nt.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                        break
                    # 遇到动词运算符停止
                    if nt.type == TokenType.KEYWORD and nt.value in self.OPERATOR_VERBS:
                        break
                    # 遇到其他关键字停止（双字关键字通常是语句结构）
                    if nt.type == TokenType.KEYWORD and nt.value in ALL_KEYWORDS:
                        break
                    
                    if nt.type == TokenType.NUMBER:
                        args.append(NumberLiteral(self._consume().value))
                    elif nt.type == TokenType.CHINESE_NUM:
                        args.append(NumberLiteral(self._consume().value))
                    elif nt.type == TokenType.STRING:
                        args.append(StringLiteral(self._consume().value))
                    elif nt.type == TokenType.IDENTIFIER:
                        args.append(Identifier(self._consume().value))
                    else:
                        break
                
                if args:
                    expr = ParagraphCall(name, args)
                    return self._parse_postfix(expr)
            
            # 简单标识符
            expr = Identifier(name)
            return self._parse_postfix(expr)

        # 特殊值
        if tok.type == TokenType.KEYWORD and tok.value in KEYWORDS_SPECIAL:
            self._consume()
            if tok.value == '真':
                return Identifier('True')
            elif tok.value == '假':
                return Identifier('False')
            else:  # '空'
                return Identifier('None')

        # 书名号段落调用
        if tok.type == TokenType.LBOOK:
            return self._parse_paragraph_call()

        # 括号表达式
        if tok.type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            expr = self._parse_expr()
            self._consume(TokenType.RPAREN)
            return expr

        # 列表字面量
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_literal()

        return None

    def _collect_single_arg(self) -> Optional[ASTNode]:
        """收集单个参数（可能包含段落调用）"""
        tok = self._current()
        if tok is None:
            return None

        # 数字
        if tok.type == TokenType.NUMBER:
            self._consume()
            return NumberLiteral(tok.value)

        # 中文数字
        if tok.type == TokenType.CHINESE_NUM:
            self._consume()
            return NumberLiteral(tok.value)

        # 字符串
        if tok.type == TokenType.STRING:
            self._consume()
            return StringLiteral(tok.value)

        # 标识符
        if tok.type == TokenType.IDENTIFIER:
            name = tok.value
            self._consume()
            
            # f-string 检测：f 后跟 STRING => f"..."
            if name == 'f' and self._current() and self._current().type == TokenType.STRING:
                str_val = self._consume().value
                parts = self._parse_fstring_parts(str_val)
                from ast_nodes_v3 import StringInterpolation
                expr = StringInterpolation(parts)
                return self._parse_postfix(expr)
            
            # 合并连续的 IDENTIFIER 令牌（用于处理 tokenizer 将 "字典创建" 拆分为两个 IDENTIFIER 的情况）
            # 但不合并运算符动词（如"减去"、"取余"等）
            while self._current() and self._current().type == TokenType.IDENTIFIER \
                    and self._current().value not in self.ADD_OP_MAP \
                    and self._current().value not in self.MUL_OP_MAP \
                    and self._current().value != '不':
                name += self._consume().value
            
            # 函数名含动词关键字合并（如"添加模板"被拆分为 添+加+模+板，其中加/模是 OPERATOR_VERBS）
            # 仅当 token 在源码中相邻（无空格）且合并后紧跟 ( 时才合并
            # 通过相邻性检查区分 "添加模板" 和 "甲 加 乙"
            if self._current() and self._current().type == TokenType.KEYWORD:
                _fn_saved_pos = self.pos
                _fn_prev = tok
                _fn_parts = [name]
                _fn_stop = frozenset({
                    '为','等于','接收','返回','令','循环','断言','输出',
                    '如果','否则','那么','若','则','当','遍历','设','定义',
                    '类','构造','函数','段落','尝试','捕获','抛出','最终','导入',
                    '导出','从','真','假','空','且','或','非','与','等待',
                    '匹配','情况','的','之','对','步','至','到','在','于','中的',
                    '包含',  # 动词停止符
                })
                while self._current():
                    _ct = self._current()
                    if _ct.type == TokenType.KEYWORD and _ct.value not in _fn_stop:
                        if _fn_prev.col + len(_fn_prev.value) != _ct.col:
                            break
                        _fn_parts.append(_ct.value)
                        _fn_prev = _ct
                        self._consume()
                    elif _ct.type == TokenType.IDENTIFIER:
                        if _fn_prev.col + len(_fn_prev.value) != _ct.col:
                            break
                        _fn_parts.append(_ct.value)
                        _fn_prev = _ct
                        self._consume()
                    else:
                        break
                if self._current() and self._current().type == TokenType.LPAREN:
                    name = ''.join(_fn_parts)
                else:
                    self.pos = _fn_saved_pos
            
            # 检查是否为范围表达式：标识符至标识符 或 标识符到标识符
            # 例如：left至right、start到end
            _range_tok = self._current()
            if _range_tok and _range_tok.type == TokenType.KEYWORD and _range_tok.value in ('至', '到'):
                self._consume(TokenType.KEYWORD)  # 消耗「至」或「到」
                # end表达式可以是数字或任意表达式
                end_expr = self._parse_add_expr()
                
                # 检查是否有步长：步 数字
                step_expr = None
                step_tok = self._current()
                if step_tok and step_tok.type == TokenType.KEYWORD and step_tok.value == '步':
                    self._consume(TokenType.KEYWORD, '步')
                    step_expr = self._parse_add_expr()
                
                range_expr = RangeExpr(Identifier(name), end_expr, step_expr)
                return self._parse_postfix(range_expr)
            
            # 运算符动词（不应收集为参数）
            
            # 检查下一个token是否是运算符动词（包括KEYWORD和IDENTIFIER类型）
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                # 下一个是运算符，不收集参数，直接返回标识符
                expr = Identifier(name)
            elif next_tok and next_tok.type == TokenType.IDENTIFIER and                  (next_tok.value in self.ADD_OP_MAP or next_tok.value in self.MUL_OP_MAP):
                # 下一个是IDENTIFIER类型的运算符（如"减去"），不收集参数
                expr = Identifier(name)
            else:
                # 检查是否是段落调用（标识符后跟参数）
                args = []
                while self._current():
                    next_tok = self._current()
                    # 停止条件：句号、逗号、右括号
                    if next_tok.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                        break
                    # 遇到运算符动词停止
                    if next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                        break
                    # 遇到IDENTIFIER类型的运算符（如"减去"）停止
                    if next_tok.type == TokenType.IDENTIFIER and                        (next_tok.value in self.ADD_OP_MAP or next_tok.value in self.MUL_OP_MAP):
                        break
                    # 遇到"不"（not in的前缀）停止
                    if next_tok.type == TokenType.IDENTIFIER and next_tok.value == '不':
                        break
                    # 遇到其他关键字（除运算符动词外）停止
                    if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS:
                        break
                    
                    # 收集单个参数（只收集primary，不包含运算）
                    if next_tok.type == TokenType.NUMBER:
                        args.append(NumberLiteral(self._consume().value))
                    elif next_tok.type == TokenType.CHINESE_NUM:
                        args.append(NumberLiteral(self._consume().value))
                    elif next_tok.type == TokenType.STRING:
                        args.append(StringLiteral(self._consume().value))
                    elif next_tok.type == TokenType.IDENTIFIER:
                        # 收集标识符作为独立参数（不嵌套）
                        args.append(Identifier(self._consume().value))
                    else:
                        break
                
                # 如果有参数，作为段落调用
                if args:
                    expr = ParagraphCall(name, args)
                else:
                    expr = Identifier(name)
            
            return self._parse_postfix(expr)
        
        # 关键字作为标识符（如参数名）
        if tok.type == TokenType.KEYWORD:
            name = tok.value
            self._consume()
            
            # 同样检查是否是段落调用
            args = []
            while self._current():
                next_tok = self._current()
                if next_tok.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                    break
                if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS:
                    break
                
                arg = self._collect_primary_arg()
                if arg:
                    args.append(arg)
                else:
                    break
            
            if args:
                expr = ParagraphCall(name, args)
            else:
                expr = Identifier(name)
            
            return self._parse_postfix(expr)
        
        # 特殊值
        if tok.type == TokenType.KEYWORD and tok.value in KEYWORDS_SPECIAL:
            self._consume()
            if tok.value == '真':
                return Identifier('True')
            elif tok.value == '假':
                return Identifier('False')
            else:  # '空'
                return Identifier('None')

        # 段落调用
        if tok.type == TokenType.LBOOK:
            return self._parse_paragraph_call()

        # 括号表达式
        if tok.type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            expr = self._parse_expr()
            self._consume(TokenType.RPAREN)
            return expr

        # 列表字面量
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_literal()

        # 注意：不再递归处理动词，避免无限循环
        # 动词作为独立语句处理，不作为参数
        return None

        # 数字
        if tok.type == TokenType.NUMBER:
            self._consume()
            return NumberLiteral(tok.value)

        # 中文数字
        if tok.type == TokenType.CHINESE_NUM:
            self._consume()
            return NumberLiteral(tok.value)

        # 字符串
        if tok.type == TokenType.STRING:
            self._consume()
            return StringLiteral(tok.value)

        # 标识符
        if tok.type == TokenType.IDENTIFIER:
            name = tok.value
            self._consume()
            
            # 运算符动词（不应收集为参数）
            
            # 检查下一个token是否是运算符动词
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                # 下一个是运算符，不收集参数，直接返回标识符
                expr = Identifier(name)
            else:
                # 检查是否是段落调用（标识符后跟参数）
                args = []
                while self._current():
                    next_tok = self._current()
                    # 停止条件：句号、逗号、右括号
                    if next_tok.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                        break
                    # 遇到运算符动词停止
                    if next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                        break
                    # 遇到其他关键字（除运算符动词外）停止
                    if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS and next_tok.value not in _EXPR_START_KEYWORDS:
                        break
                    
                    # 收集单个参数（只收集primary，不包含运算）
                    if next_tok.type == TokenType.NUMBER:
                        args.append(NumberLiteral(self._consume().value))
                    elif next_tok.type == TokenType.CHINESE_NUM:
                        args.append(NumberLiteral(self._consume().value))
                    elif next_tok.type == TokenType.STRING:
                        args.append(StringLiteral(self._consume().value))
                    elif next_tok.type == TokenType.IDENTIFIER:
                        # 收集标识符作为独立参数（不嵌套）
                        args.append(Identifier(self._consume().value))
                    else:
                        break
                
                # 如果有参数，作为段落调用
                if args:
                    expr = ParagraphCall(name, args)
                else:
                    expr = Identifier(name)
            
            return self._parse_postfix(expr)
        
        # 关键字作为标识符（如参数名）
        if tok.type == TokenType.KEYWORD:
            name = tok.value
            self._consume()
            
            # 同样检查是否是段落调用
            args = []
            while self._current():
                next_tok = self._current()
                if next_tok.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                    break
                if next_tok.type == TokenType.KEYWORD and next_tok.value in ALL_KEYWORDS and next_tok.value not in _EXPR_START_KEYWORDS:
                    break
                
                arg = self._collect_single_arg()
                if arg:
                    args.append(arg)
                else:
                    break
            
            if args:
                expr = ParagraphCall(name, args)
            else:
                expr = Identifier(name)
            
            return self._parse_postfix(expr)
        
        # 特殊值
        if tok.type == TokenType.KEYWORD and tok.value in KEYWORDS_SPECIAL:
            self._consume()
            if tok.value == '真':
                return Identifier('True')
            elif tok.value == '假':
                return Identifier('False')
            else:  # '空'
                return Identifier('None')

        # 段落调用
        if tok.type == TokenType.LBOOK:
            return self._parse_paragraph_call()

        # 括号表达式
        if tok.type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            expr = self._parse_expr()
            self._consume(TokenType.RPAREN)
            return expr

        # 注意：不再递归处理动词，避免无限循环
        # 动词作为独立语句处理，不作为参数

        return None
    
    def _parse_string_interpolation(self, value: str, line: int = 0, col: int = 0):
        """检测字符串插值：如果字符串包含 {xxx}，返回 StringInterpolation 节点，否则返回 None"""
        if '{' not in value:
            return None

        import re
        parts = []
        last_end = 0
        has_invalid = False
        for m in re.finditer(r'\{([^}]+)\}', value):
            expr_text = m.group(1).strip()
            # 检查是否是有效的插值表达式
            # 有效标识符：中文、字母、数字、下划线、点号(属性)、方括号(索引)
            # 支持格式说明符：{expr:format_spec}
            # 无效模式如 {%原始%} 不应作为插值
            format_spec = ''
            if ':' in expr_text:
                # 分离表达式和格式说明符（如 {3.14159:.4f}、{value:,}）
                colon_idx = expr_text.index(':')
                expr_part = expr_text[:colon_idx].strip()
                format_spec = expr_text[colon_idx+1:].strip()
            else:
                expr_part = expr_text
            if not re.match(r'^[\u4e00-\u9fa5a-zA-Z_][\u4e00-\u9fa5a-zA-Z0-9_.\[\]"\'\u3010\u3011]*$', expr_part):
                has_invalid = True
                break
            # 插值前的普通文本
            if m.start() > last_end:
                parts.append(value[last_end:m.start()])
            # 插值表达式（作为标识符），如果有格式说明符则存储为元组
            if format_spec:
                parts.append((Identifier(expr_part), format_spec))
            else:
                parts.append(Identifier(expr_part))
            last_end = m.end()

        # 如果有无效的插值模式，整个字符串不作为插值处理
        if has_invalid:
            return None

        # 尾部普通文本
        if last_end < len(value):
            parts.append(value[last_end:])

        # 如果只有普通文本（没有真正的插值），返回 None
        has_expr = any(isinstance(p, (Identifier, tuple)) for p in parts)
        if not has_expr:
            return None

        return StringInterpolation(parts)


    def _parse_c_anonymous_function(self) -> ASTNode:
        """解析C风格匿名函数：函数(params){body}

        转换为 LambdaExpression 或带语句体的匿名函数。
        """
        # 函数
        self._consume(TokenType.KEYWORD, '函数')

        # 参数列表
        params = []
        if self._current() and self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            while self._current() and self._current().type != TokenType.RPAREN:
                tok = self._current()
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    params.append(self._consume().value)
                else:
                    break
            if self._current() and self._current().type == TokenType.RPAREN:
                self._consume(TokenType.RPAREN)

        # 函数体 {body}
        body_expr = self._parse_c_anon_body()

        if body_expr is not None:
            return LambdaExpression(params, body_expr)
        return LambdaExpression(params, Identifier('None'))

    def _parse_c_anon_body(self):
        """解析匿名函数体，返回单个表达式或None"""
        from tokens import TokenType as TT
        if not self._current() or self._current().type != TT.LBRACE:
            return None

        self._consume(TT.LBRACE)

        # 跳过 NEWLINE / INDENT
        while self._current() and self._current().type in (TT.NEWLINE, TT.INDENT):
            self._consume()

        # 收集体内语句，寻找 return 表达式
        result_expr = None
        depth = 0

        while self._current() and self._current().type != TT.RBRACE:
            tok = self._current()

            if tok.type == TT.NEWLINE:
                self._consume(TT.NEWLINE)
                continue
            if tok.type == TT.INDENT:
                self._consume(TT.INDENT)
                depth += 1
                continue
            if tok.type == TT.DEDENT:
                if depth > 0:
                    self._consume(TT.DEDENT)
                    depth -= 1
                    continue
                else:
                    break

            # 检查是否是 返回 expr
            if tok.type == TT.KEYWORD and tok.value == '返回':
                self._consume(TT.KEYWORD, '返回')
                if self._current() and self._current().type != TT.RBRACE and                    self._current().type != TT.NEWLINE and self._current().type != TT.DEDENT:
                    result_expr = self._parse_expr()
                else:
                    result_expr = Identifier('None')
                # 跳过到 RBRACE
                while self._current() and self._current().type != TT.RBRACE:
                    if self._current().type == TT.DEDENT and depth > 0:
                        self._consume(TT.DEDENT)
                        depth -= 1
                        continue
                    if self._current().type == TT.NEWLINE:
                        self._consume(TT.NEWLINE)
                        continue
                    self._consume()
                break
            else:
                # 跳过非return语句（简化处理）
                # 尝试解析为表达式语句
                try:
                    expr = self._parse_expr()
                    if result_expr is None:
                        result_expr = expr
                except Exception:
                    self._consume()

        # 消耗 DEDENT
        while self._current() and self._current().type == TT.DEDENT and depth > 0:
            self._consume(TT.DEDENT)
            depth -= 1

        # 消耗 RBRACE
        if self._current() and self._current().type == TT.RBRACE:
            self._consume(TT.RBRACE)

        if result_expr is None:
            result_expr = Identifier('None')
        return result_expr

    def _parse_lambda(self) -> LambdaExpression:
        """解析匿名函数：接收 参数1 参数2：返回 表达式。 或 接收 参数1 参数2：表达式。"""
        # 接收
        self._consume(TokenType.KEYWORD, '接收')
        
        # 收集参数名（支持逗号分隔：接收 x, y：返回 ...）
        # 也支持 *args, **kwargs
        params = []
        while self._current():
            tok = self._current()
            if tok.type == TokenType.STAR:
                self._consume(TokenType.STAR)
                if self._current() and self._current().type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    if self._current() and self._current().type == TokenType.IDENTIFIER:
                        params.append('**' + self._consume(TokenType.IDENTIFIER).value)
                    elif self._current() and self._current().type == TokenType.KEYWORD:
                        params.append('**' + self._consume(TokenType.KEYWORD).value)
                else:
                    if self._current() and self._current().type == TokenType.IDENTIFIER:
                        params.append('*' + self._consume(TokenType.IDENTIFIER).value)
                    elif self._current() and self._current().type == TokenType.KEYWORD:
                        params.append('*' + self._consume(TokenType.KEYWORD).value)
            elif tok.type == TokenType.IDENTIFIER:
                params.append(self._consume(TokenType.IDENTIFIER).value)
            elif tok.type == TokenType.KEYWORD and tok.value not in ('返回', '匹配', '情况', '如果', '若', '否则', '遍历', '当', '设', '定义', '类', '构造', '段落', '函数', '尝试', '捕获', '抛出', '最终', '导入', '导出', '从'):
                # 允许非语句关键字作为参数名
                params.append(self._consume(TokenType.KEYWORD).value)
            else:
                break
            # 检查逗号（多参数分隔）
            if self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                continue
            else:
                break
        
        # 冒号
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
        
        # 可选的"返回"关键字
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, '返回')
        
        # 表达式（函数体）
        body = self._parse_comparison()
        
        # 可选的句号
        if self._current() and self._current().type == TokenType.DOT:
            self._consume(TokenType.DOT)
        
        return LambdaExpression(params, body)

    def _parse_dict_literal(self) -> ASTNode:
        """解析字典字面量或字典推导

        普通字典：{key: value, key2: value2, ...}
        字典推导：{key: value 遍历 变量 之 可迭代对象} 或 {key: value 遍历 变量 之 可迭代对象 若 条件}
        """
        self._consume(TokenType.LBRACE)
        entries = []
        # 空字典 {}
        if self._match(TokenType.RBRACE):
            self._consume(TokenType.RBRACE)
            return self._parse_postfix(DictLiteral(entries))
        
        # 跳过 NEWLINE/INDENT/DEDENT（支持多行字典）
        while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self._consume()
        
        # 支持 **dict 展开（如 {**d1, **d2}）
        if self._current() and self._current().type == TokenType.STAR:
            self._consume(TokenType.STAR)
            if self._current() and self._current().type == TokenType.STAR:
                self._consume(TokenType.STAR)
                # 解析后面的表达式
                spread_expr = self._parse_comparison()
                # 收集所有条目（包括 ** 展开和普通 key: value）
                entries = []
                # 用特殊的 key=None, value=Identifier("**expr") 表示展开
                entries.append((None, spread_expr))
                # 继续收集后续条目
                while self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                    while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._consume()
                    if self._match(TokenType.RBRACE):
                        break
                    # 检查是否又是 ** 展开
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        if self._current() and self._current().type == TokenType.STAR:
                            self._consume(TokenType.STAR)
                            spread = self._parse_comparison()
                            entries.append((None, spread))
                            continue
                    key = self._parse_comparison()
                    self._consume(TokenType.COLON)
                    val = self._parse_comparison()
                    # 检查三元表达式：值 如果 条件 否则 值
                    if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '如果':
                        self._consume(TokenType.KEYWORD, '如果')
                        cond = self._parse_logical_expr()
                        else_val = None
                        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '否则':
                            self._consume(TokenType.KEYWORD, '否则')
                            else_val = self._parse_logical_expr()
                        from ast_nodes_v3 import ConditionalExpression
                        val = ConditionalExpression(cond, val, else_val)
                    entries.append((key, val))
                self._consume(TokenType.RBRACE)
                return self._parse_postfix(DictLiteral(entries))
        
        # 键
        key = self._parse_comparison()
        
        # 检查是否是集合推导：{expr 遍历 变量 之 可迭代对象 遍历 变量 之 ...}
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
            # 集合推导模式 - 支持多重遍历
            generators = []  # List of (variable_str, iterable_ast, condition_ast_or_None)
            
            _sc_stop_keywords = frozenset({'之', '在', '于', '中的'})
            
            while self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                self._consume(TokenType.KEYWORD, '遍历')
                
                # 变量名（支持多变量：k, v）
                variables = []
                if self._current() and not (self._current().type == TokenType.KEYWORD and self._current().value in _sc_stop_keywords):
                    while True:
                        var_tok = self._current()
                        if var_tok and var_tok.type == TokenType.IDENTIFIER:
                            variables.append(self._consume(TokenType.IDENTIFIER).value)
                        elif var_tok and var_tok.type == TokenType.KEYWORD and var_tok.value not in _sc_stop_keywords:
                            variables.append(self._consume(TokenType.KEYWORD).value)
                        else:
                            break
                        # 检查逗号（多变量）
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                            continue
                        break
                if not variables:
                    variables = ['_']
                variable = ', '.join(variables)

                # 之 / 在
                if self._match(TokenType.KEYWORD, '之'):
                    self._consume(TokenType.KEYWORD, '之')
                elif self._match(TokenType.KEYWORD, '在'):
                    self._consume(TokenType.KEYWORD, '在')
                else:
                    tok = self._current()
                    return self._error(f"集合推导期望'之'或'在'",
                                     tok.line if tok else 0, tok.col if tok else 0)
                
                # 可迭代对象
                iterable = self._parse_comparison()
                
                # 可选条件：若 条件 或 如果 条件
                condition = None
                tok = self._current()
                if tok and tok.type == TokenType.KEYWORD and tok.value in ('若', '如果'):
                    self._consume()
                    condition = self._parse_expr()
                
                generators.append((variable, iterable, condition))
            
            self._consume(TokenType.RBRACE)
            
            # 单个generator时保持向后兼容
            if len(generators) == 1:
                var, it, cond = generators[0]
                return self._parse_postfix(SetComprehension(key, var, it, cond))
            else:
                # 多重generator
                first_gen = generators[0]
                return self._parse_postfix(SetComprehension(key, first_gen[0], first_gen[1], first_gen[2], generators=generators))
        
        # 检查是否是集合字面量：{val1, val2, ...}（第一个元素后跟逗号或右花括号，而非冒号）
        if self._current() and self._current().type in (TokenType.COMMA, TokenType.RBRACE):
            elements = [key]
            while self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                # 跳过 NEWLINE/INDENT/DEDENT（支持多行集合）
                while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._consume()
                if self._match(TokenType.RBRACE):
                    break
                elem = self._parse_comparison()
                elements.append(elem)
            self._consume(TokenType.RBRACE)
            return self._parse_postfix(SetLiteral(elements))
        
        # 冒号
        self._consume(TokenType.COLON)
        # 值
        value = self._parse_comparison()
        # 检查三元表达式：值 如果 条件 否则 值
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '如果':
            self._consume(TokenType.KEYWORD, '如果')
            cond = self._parse_logical_expr()
            else_val = None
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '否则':
                self._consume(TokenType.KEYWORD, '否则')
                else_val = self._parse_logical_expr()
            from ast_nodes_v3 import ConditionalExpression
            value = ConditionalExpression(cond, value, else_val)
        
        # 检查是否是字典推导：后面是否有"遍历"（支持多重遍历）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
            # 字典推导模式 - 支持多重遍历
            generators = []  # List of (variable_str, iterable_ast, condition_ast_or_None)
            
            _dc_stop_keywords = frozenset({'之', '在', '于', '中的'})
            
            while self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                self._consume(TokenType.KEYWORD, '遍历')
                
                # 变量名（支持多变量：k, v）
                variables = []
                if self._current() and not (self._current().type == TokenType.KEYWORD and self._current().value in _dc_stop_keywords):
                    while True:
                        var_tok = self._current()
                        if var_tok and var_tok.type == TokenType.IDENTIFIER:
                            variables.append(self._consume(TokenType.IDENTIFIER).value)
                        elif var_tok and var_tok.type == TokenType.KEYWORD and var_tok.value not in _dc_stop_keywords:
                            variables.append(self._consume(TokenType.KEYWORD).value)
                        else:
                            break
                        # 检查逗号（多变量）
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                            continue
                        break
                if not variables:
                    variables = ['_']
                variable = ', '.join(variables)
                
                # 之 / 在
                if self._match(TokenType.KEYWORD, '之'):
                    self._consume(TokenType.KEYWORD, '之')
                elif self._match(TokenType.KEYWORD, '在'):
                    self._consume(TokenType.KEYWORD, '在')
                else:
                    tok = self._current()
                    return self._error(f"字典推导期望'之'或'在'",
                                     tok.line if tok else 0, tok.col if tok else 0)
                
                # 可迭代对象
                iterable = self._parse_comparison()
                
                # 可选条件：若 条件 或 如果 条件
                condition = None
                tok = self._current()
                if tok and tok.type == TokenType.KEYWORD and tok.value in ('若', '如果'):
                    self._consume()
                    condition = self._parse_expr()
                
                generators.append((variable, iterable, condition))
            
            self._consume(TokenType.RBRACE)
            
            # 单个generator时保持向后兼容
            if len(generators) == 1:
                var, it, cond = generators[0]
                return self._parse_postfix(DictComprehension(key, value, var, it, cond))
            else:
                # 多重generator
                first_gen = generators[0]
                return self._parse_postfix(DictComprehension(key, value, first_gen[0], first_gen[1], first_gen[2], generators=generators))
        
        # 普通字典字面量
        entries = [(key, value)]
        while True:
            # 跳过 NEWLINE/INDENT/DEDENT
            while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._consume()
            # 逗号分隔
            if self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                # 跳过 NEWLINE/INDENT/DEDENT
                while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._consume()
                if self._match(TokenType.RBRACE):
                    break
                # 支持 **dict 展开（如 {"k": 1, **other}）
                if self._current() and self._current().type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        spread = self._parse_comparison()
                        entries.append((None, spread))
                        continue
                key = self._parse_comparison()
                self._consume(TokenType.COLON)
                val = self._parse_comparison()
                # 检查三元表达式：值 如果 条件 否则 值
                if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '如果':
                    self._consume(TokenType.KEYWORD, '如果')
                    cond = self._parse_logical_expr()
                    else_val = None
                    if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '否则':
                        self._consume(TokenType.KEYWORD, '否则')
                        else_val = self._parse_logical_expr()
                    from ast_nodes_v3 import ConditionalExpression
                    val = ConditionalExpression(cond, val, else_val)
                entries.append((key, val))
                continue
            break
        self._consume(TokenType.RBRACE)
        return self._parse_postfix(DictLiteral(entries))

    def _parse_list_literal(self) -> ASTNode:
        """解析列表字面量或列表推导
        
        普通列表：[元素1, 元素2, ...]
        列表推导：[表达式 遍历 变量 之 可迭代对象] 或 [表达式 遍历 变量 之 可迭代对象 若 条件]
        """
        self._consume(TokenType.LBRACKET)
        
        # 空列表
        if self._match(TokenType.RBRACKET):
            self._consume(TokenType.RBRACKET)
            return ListLiteral([])

        # 跳过 NEWLINE/INDENT/DEDENT（支持多行列表）
        while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self._consume()

        # 解析第一个元素/表达式
        first_expr = self._parse_comparison()

        # 检查是否是字典推导：键: 值 遍历 变量 之 ...
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            value_expr = self._parse_comparison()

            # 检查后面是否有"遍历"（支持多重遍历）
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                # 字典推导模式 - 支持多重遍历
                generators = []  # List of (variable_str, iterable_ast, condition_ast_or_None)
                
                _ldc_stop_keywords = frozenset({'之', '在', '于', '中的'})
                
                while self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                    self._consume(TokenType.KEYWORD, '遍历')

                    # 变量名（支持多变量）
                    variables = []
                    if self._current() and not (self._current().type == TokenType.KEYWORD and self._current().value in _ldc_stop_keywords):
                        while True:
                            var_tok = self._current()
                            if var_tok and var_tok.type == TokenType.IDENTIFIER:
                                variables.append(self._consume(TokenType.IDENTIFIER).value)
                            elif var_tok and var_tok.type == TokenType.KEYWORD and var_tok.value not in _ldc_stop_keywords:
                                variables.append(self._consume(TokenType.KEYWORD).value)
                            else:
                                break
                            if self._match(TokenType.COMMA):
                                self._consume(TokenType.COMMA)
                                continue
                            break
                    if not variables:
                        variables = ['_']
                    variable = ', '.join(variables)

                    # 之
                    if self._match(TokenType.KEYWORD, '之'):
                        self._consume(TokenType.KEYWORD, '之')
                    elif self._match(TokenType.KEYWORD, '在'):
                        self._consume(TokenType.KEYWORD, '在')
                    else:
                        tok = self._current()
                        return self._error(f"字典推导期望'之'或'在'",
                                         tok.line if tok else 0, tok.col if tok else 0)

                    # 可迭代对象
                    iterable = self._parse_comparison()

                    # 可选条件
                    condition = None
                    tok = self._current()
                    if tok and tok.type == TokenType.KEYWORD and tok.value in ('若', '如果'):
                        self._consume()
                        condition = self._parse_expr()

                    generators.append((variable, iterable, condition))

                self._consume(TokenType.RBRACKET)
                
                if len(generators) == 1:
                    var, it, cond = generators[0]
                    return DictComprehension(first_expr, value_expr, var, it, cond)
                else:
                    first_gen = generators[0]
                    return DictComprehension(first_expr, value_expr, first_gen[0], first_gen[1], first_gen[2], generators=generators)

            # 普通字典字面量：键: 值, 键: 值, ...
            entries = [(first_expr, value_expr)]
            while self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                key = self._parse_comparison()
                self._consume(TokenType.COLON)
                val = self._parse_comparison()
                entries.append((key, val))
            self._consume(TokenType.RBRACKET)
            return DictLiteral(entries)

        # 检查是否是列表推导（后面跟着"遍历"关键字）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
            # 列表推导模式 - 支持多重遍历
            generators = []  # List of (variable_str, iterable_ast, condition_ast_or_None)

            while self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                self._consume(TokenType.KEYWORD, '遍历')

                # 变量名（支持多变量：k, v）
                # 如果遍历后直接跟 之/在，说明变量名为空，默认用 _
                _lc_stop_keywords = frozenset({'之', '在', '于', '中的'})
                variables = []
                if self._current() and not (self._current().type == TokenType.KEYWORD and self._current().value in _lc_stop_keywords):
                    while True:
                        var_tok = self._current()
                        if var_tok and var_tok.type == TokenType.IDENTIFIER:
                            variables.append(self._consume(TokenType.IDENTIFIER).value)
                        elif var_tok and var_tok.type == TokenType.KEYWORD and var_tok.value not in _lc_stop_keywords:
                            variables.append(self._consume(TokenType.KEYWORD).value)
                        else:
                            break
                        # 检查逗号（多变量）
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                            continue
                        break
                if not variables:
                    variables = ['_']
                variable = ', '.join(variables)

                # 之 / 在
                if self._match(TokenType.KEYWORD, '之'):
                    self._consume(TokenType.KEYWORD, '之')
                elif self._match(TokenType.KEYWORD, '在'):
                    self._consume(TokenType.KEYWORD, '在')
                else:
                    tok = self._current()
                    return self._error(f"列表推导期望'之'或'在'，但得到 {tok.type if tok else '输入结束'}",
                                     tok.line if tok else 0, tok.col if tok else 0)

                # 可迭代对象
                iterable = self._parse_comparison()

                # 可选条件：若 条件 或 如果 条件
                condition = None
                if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('若', '如果'):
                    self._consume()
                    condition = self._parse_expr()

                generators.append((variable, iterable, condition))

            self._consume(TokenType.RBRACKET)

            # 单个generator时保持向后兼容
            if len(generators) == 1:
                var, it, cond = generators[0]
                return ListComprehension(first_expr, var, it, cond)
            else:
                # 多重generator
                first_gen = generators[0]
                return ListComprehension(first_expr, first_gen[0], first_gen[1], first_gen[2], generators=generators)

        # 普通列表字面量：元素, 元素, ...
        elements = [first_expr]
        while self._match(TokenType.COMMA):
            self._consume(TokenType.COMMA)
            # 跳过 NEWLINE/INDENT/DEDENT（支持多行列表）
            while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._consume()
            if self._match(TokenType.RBRACKET):
                break
            elem = self._parse_comparison()
            elements.append(elem)
        self._consume(TokenType.RBRACKET)
        return ListLiteral(elements)
    
    def _parse_fstring_parts(self, str_val: str) -> list:
        """解析 f-string 内容，返回交替的 str 和 ASTNode 列表"""
        parts = []
        current_text = ''
        i = 0
        while i < len(str_val):
            if str_val[i] == '{' and i + 1 < len(str_val) and str_val[i+1] != '{':
                # 保存之前的文本
                if current_text:
                    parts.append(current_text)
                    current_text = ''
                # 找到匹配的 }，同时检测格式说明符中的 ':'
                j = i + 1
                depth = 1
                while j < len(str_val) and depth > 0:
                    if str_val[j] == '{':
                        depth += 1
                    elif str_val[j] == '}':
                        depth -= 1
                    if depth > 0:
                        j += 1
                expr_str = str_val[i+1:j]
                # 分离格式说明符：{expr:format_spec} 中第一个不在嵌套括号内的 ':'
                format_spec = ''
                expr_part = expr_str
                colon_idx = -1
                brace_depth = 0
                for k, ch in enumerate(expr_str):
                    if ch == '{':
                        brace_depth += 1
                    elif ch == '}':
                        brace_depth -= 1
                    elif ch == ':' and brace_depth == 0:
                        colon_idx = k
                        break
                if colon_idx >= 0:
                    expr_part = expr_str[:colon_idx].strip()
                    format_spec = expr_str[colon_idx+1:].strip()
                # 将表达式字符串作为光明表达式解析
                try:
                    from lexer import Lexer
                    from light_parser_v3 import LightParser
                    sub_lexer = Lexer()
                    sub_tokens = sub_lexer.tokenize(expr_part)
                    sub_parser = LightParser()
                    sub_parser.tokens = sub_tokens
                    sub_parser.pos = 0
                    expr_node = sub_parser._parse_expr()
                    if expr_node:
                        if format_spec:
                            parts.append((expr_node, format_spec))
                        else:
                            parts.append(expr_node)
                    else:
                        if format_spec:
                            parts.append((Identifier(expr_part), format_spec))
                        else:
                            parts.append(Identifier(expr_part))
                except Exception:
                    if format_spec:
                        parts.append((Identifier(expr_part), format_spec))
                    else:
                        parts.append(Identifier(expr_part))
                i = j + 1
            elif str_val[i] == '}' and i + 1 < len(str_val) and str_val[i+1] == '}':
                current_text += '}'
                i += 2
            else:
                current_text += str_val[i]
                i += 1
        if current_text:
            parts.append(current_text)
        return parts

    def _parse_postfix(self, expr: ASTNode) -> ASTNode:
        """解析后缀表达式（索引访问、成员访问、函数调用、解包）"""
        while self._current():
            tok = self._current()

            # 解包操作：值! 或 值！
            if tok.type == TokenType.BANG:
                self._consume(TokenType.BANG)
                expr = UnwrapExpression(value=expr)
                continue

            # 函数调用：(参数1, 参数2, ...)
            # 例如：累计(数值 减 1)  或  三倍(甲)
            if tok.type == TokenType.LPAREN:
                self._consume(TokenType.LPAREN)

                # 获取函数名
                if isinstance(expr, Identifier):
                    func_name = expr.name
                elif isinstance(expr, str):
                    func_name = expr
                else:
                    return self._error(f"不支持在复杂表达式后进行括号调用: {type(expr).__name__}（可将'()'改为'。'或去掉括号）")

                # 收集参数（直到右括号）- 使用比较表达式而非完整表达式
                # 以避免逗号被当作管道操作符处理
                args = []
                while not self._match(TokenType.RPAREN):
                    # 跳过 NEWLINE/INDENT/DEDENT（支持多行函数调用）
                    if self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._consume()
                        continue
                    # 支持 C 风格关键字参数：name = value
                    # name 可能由多个 token 组成（如 "获取函数" 被拆分为 "获取"+函数"）
                    _kwarg_saved_pos = self.pos
                    _kwarg_name_parts = []
                    _kwarg_stop_kws = frozenset({
                        '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
                        '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
                        '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
                        '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
                        '匹配', '情况', '的', '之', '对', '步', '至', '到',
                    })
                    while self._current():
                        _t = self._current()
                        if _t.type == TokenType.IDENTIFIER:
                            _kwarg_name_parts.append(self._consume().value)
                        elif _t.type == TokenType.KEYWORD and _t.value not in _kwarg_stop_kws:
                            _kwarg_name_parts.append(self._consume().value)
                        else:
                            break
                    if _kwarg_name_parts and self._current() and self._current().type == TokenType.EQUALS:
                        # 确认是关键字参数，消耗 = 并解析值
                        self._consume(TokenType.EQUALS)
                        kwarg_val = self._parse_comparison()
                        if kwarg_val is not None:
                            kwarg_name = ''.join(_kwarg_name_parts)
                            from ast_nodes_v3 import KeywordArg
                            args.append(KeywordArg(kwarg_name, kwarg_val))
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                        while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._consume()
                        continue
                    else:
                        # 不是关键字参数，回退
                        self.pos = _kwarg_saved_pos
                    # 支持 *args 和 **kwargs 展开
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        # 检查是否是 **kwargs（双星号）
                        if self._current() and self._current().type == TokenType.STAR:
                            self._consume(TokenType.STAR)
                            arg = self._parse_comparison()
                            if arg is not None and isinstance(arg, Identifier):
                                args.append(Identifier(f'**{arg.name}'))
                        else:
                            arg = self._parse_comparison()
                            if arg is not None and isinstance(arg, Identifier):
                                args.append(Identifier(f'*{arg.name}'))
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                        while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._consume()
                        continue
                    arg = self._parse_comparison()
                    if arg is not None:
                        # 检查是否是生成器表达式：表达式 遍历 变量 之 可迭代对象
                        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                            generators = []
                            _ge_stop = frozenset({'之', '在', '于', '中的'})
                            while self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '遍历':
                                self._consume(TokenType.KEYWORD, '遍历')
                                variables = []
                                if self._current() and not (self._current().type == TokenType.KEYWORD and self._current().value in _ge_stop):
                                    while True:
                                        vt = self._current()
                                        if vt and vt.type == TokenType.IDENTIFIER:
                                            variables.append(self._consume(TokenType.IDENTIFIER).value)
                                        elif vt and vt.type == TokenType.KEYWORD and vt.value not in _ge_stop:
                                            variables.append(self._consume(TokenType.KEYWORD).value)
                                        else:
                                            break
                                        if self._match(TokenType.COMMA):
                                            self._consume(TokenType.COMMA)
                                            continue
                                        break
                                if not variables:
                                    variables = ['_']
                                variable = ', '.join(variables)
                                if self._match(TokenType.KEYWORD, '之'):
                                    self._consume(TokenType.KEYWORD, '之')
                                elif self._match(TokenType.KEYWORD, '在'):
                                    self._consume(TokenType.KEYWORD, '在')
                                else:
                                    break
                                iterable = self._parse_comparison()
                                condition = None
                                if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('若', '如果'):
                                    self._consume()
                                    condition = self._parse_expr()
                                generators.append((variable, iterable, condition))
                            if generators:
                                if len(generators) == 1:
                                    var, it, cond = generators[0]
                                    arg = ListComprehension(arg, var, it, cond)
                                else:
                                    first_gen = generators[0]
                                    arg = ListComprehension(arg, first_gen[0], first_gen[1], first_gen[2], generators=generators)
                        args.append(arg)
                    else:
                        break
                    # 逗号分隔
                    if self._match(TokenType.COMMA):
                        self._consume(TokenType.COMMA)
                    # 跳过逗号后的 NEWLINE/INDENT/DEDENT
                    while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                        self._consume()

                self._consume(TokenType.RPAREN)
                expr = ParagraphCall(func_name, args)
                continue

            # 成员访问：obj.member 或 obj.method()
            # 支持英文点号(.) 和 中文"的"两种属性访问语法
            # "obj.属性" / "obj.方法()" 或 "obj的属性" / "obj的方法()"
            is_dot_access = False
            if tok.type == TokenType.DOT:
                # 检查是否是英文点号（成员访问）还是中文句号（语句结束）        
                if tok.value == '.':
                    is_dot_access = True
                # 中文句号(。)是语句结束符，不进行成员访问

            # 「的」作为光明原生属性访问运算符
            # 「.」用于 FFI/外部库调用（如 requests.get）
            # 「之」已从成员访问中废弃，仅保留在推导式中作为循环引导符
            if not is_dot_access and tok.type == TokenType.KEYWORD and tok.value == '的':
                is_dot_access = True
            elif not is_dot_access and tok.type == TokenType.KEYWORD and tok.value == '之':
                # 在遍历循环上下文中（遍 X 之 Y），"之"是连接词，不是成员访问符
                if self._in_foreach_context:
                    pass  # 留给 foreach 语句解析连接词
                else:
                    # 检查是否在推导式上下文中（之 列表/之 集合 等）
                    # 如果不在推导式上下文，发出废弃警告
                    import warnings
                    warnings.warn(
                        f"「之」作为成员访问符已废弃，请改用「的」。如：对象.属性 → 对象的属性",
                        DeprecationWarning, stacklevel=2
                    )
                    is_dot_access = True

            if is_dot_access:
                self._consume()  # 消耗点号

                # 获取成员名
                member_tok = self._current()
                if member_tok and member_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    member_name = member_tok.value
                    self._consume()

                    # 检查是否是方法调用（后面跟着参数）
                    args = []
                    has_parens = False

                    # 检查是否是括号括起来的参数列表
                    if self._current() and self._current().type == TokenType.LPAREN:
                        has_parens = True
                        self._consume(TokenType.LPAREN)
                        # 收集参数直到右括号
                        while not self._match(TokenType.RPAREN):
                            # 跳过 NEWLINE/INDENT/DEDENT（支持多行方法调用）
                            if self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                                self._consume()
                                continue
                            # 支持 *args 和 **kwargs 展开
                            if self._current() and self._current().type == TokenType.STAR:
                                self._consume(TokenType.STAR)
                                if self._current() and self._current().type == TokenType.STAR:
                                    self._consume(TokenType.STAR)
                                    arg = self._parse_comparison()
                                    if arg is not None and isinstance(arg, Identifier):
                                        args.append(Identifier(f'**{arg.name}'))
                                else:
                                    arg = self._parse_comparison()
                                    if arg is not None and isinstance(arg, Identifier):
                                        args.append(Identifier(f'*{arg.name}'))
                                if self._match(TokenType.COMMA):
                                    self._consume(TokenType.COMMA)
                                continue
                            # 支持关键字参数：name = value
                            _kwarg_saved_pos = self.pos
                            _kwarg_name_parts = []
                            _kwarg_stop_kws = frozenset({
                                '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
                                '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
                                '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
                                '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
                                '匹配', '情况', '的', '之', '对', '步', '至', '到',
                            })
                            while self._current():
                                _t = self._current()
                                if _t.type == TokenType.IDENTIFIER:
                                    _kwarg_name_parts.append(self._consume().value)
                                elif _t.type == TokenType.KEYWORD and _t.value not in _kwarg_stop_kws:
                                    _kwarg_name_parts.append(self._consume().value)
                                else:
                                    break
                            if _kwarg_name_parts and self._current() and self._current().type == TokenType.EQUALS:
                                # 确认是关键字参数，消耗 =
                                self._consume(TokenType.EQUALS)
                                kwarg_val = self._parse_comparison()
                                if kwarg_val is not None:
                                    kwarg_name = ''.join(_kwarg_name_parts)
                                    # 用 KeywordArg 节点包装，code_generator 中生成 name=value
                                    from ast_nodes_v3 import KeywordArg
                                    args.append(KeywordArg(kwarg_name, kwarg_val))
                            else:
                                # 不是关键字参数，回退
                                self.pos = _kwarg_saved_pos
                                arg = self._parse_comparison()
                                if arg is not None:
                                    args.append(arg)
                                else:
                                    break
                            if self._match(TokenType.COMMA):
                                self._consume(TokenType.COMMA)
                            # 跳过逗号后的 NEWLINE/INDENT/DEDENT
                            while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                                self._consume()
                        self._consume(TokenType.RPAREN)
                    else:
                        # 无括号模式：收集参数直到阻断符
                        while self._current():
                            next_tok = self._current()
                            # 阻断符：句号、逗号、右括号、右中括号、关键字      
                            if next_tok.type in (TokenType.DOT, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET):
                                break
                            if next_tok.type == TokenType.KEYWORD and (next_tok.value in ALL_KEYWORDS or next_tok.value in VERB_ARITY) and next_tok.value not in _EXPR_START_KEYWORDS:
                                break

                            # 收集参数
                            arg = self._collect_primary_arg()
                            if arg:
                                args.append(arg)
                            else:
                                break

                    # 有括号一定是方法调用，无括号根据参数数量判断
                    is_method_call = has_parens or len(args) > 0
                    expr = MemberAccess(expr, member_name, is_method_call, args)
                    continue
                else:
                    if member_tok is None:
                        return self._error("期望成员名，但到达了文件末尾", 0, 0)
                    return self._error(f"期望成员名，但得到 {member_tok.type} = '{member_tok.value}'", member_tok.line, member_tok.col)

            # 索引访问：[index] 或 [start:stop:step]（切片）或 【index】
            if tok.type == TokenType.LBRACKET:
                self._consume(TokenType.LBRACKET)
                # 检查是否是切片 [:...] 或 [start:stop...]
                if self._match(TokenType.COLON):
                    # 切片 [:stop:step] 或 [:stop] 或 [::step]
                    self._consume(TokenType.COLON)
                    stop = None
                    if not self._match(TokenType.RBRACKET) and not self._match(TokenType.COLON):
                        stop = self._parse_expr()
                    step = None
                    if self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        if not self._match(TokenType.RBRACKET):
                            step = self._parse_expr()
                    self._consume(TokenType.RBRACKET)
                    expr = IndexAccess(expr, SliceExpr(None, stop, step))
                else:
                    start = self._parse_expr()
                    if self._match(TokenType.COLON):
                        # 切片 [start:stop:step] 或 [start:stop] 或 [start:]
                        self._consume(TokenType.COLON)
                        stop = None
                        if not self._match(TokenType.RBRACKET) and not self._match(TokenType.COLON):
                            stop = self._parse_expr()
                        step = None
                        if self._match(TokenType.COLON):
                            self._consume(TokenType.COLON)
                            if not self._match(TokenType.RBRACKET):
                                step = self._parse_expr()
                        self._consume(TokenType.RBRACKET)
                        expr = IndexAccess(expr, SliceExpr(start, stop, step))
                    else:
                        self._consume(TokenType.RBRACKET)
                        expr = IndexAccess(expr, start)
            else:
                break

        return expr

    def _parse_paragraph_call(self) -> ASTNode:
        """解析书名号内容：可能是字符串字面量或段落调用"""
        # 《
        self._consume(TokenType.LBOOK)

        # 段名或字符串内容
        name_tok = self._consume(TokenType.IDENTIFIER)
        name = name_tok.value

        # 》
        self._consume(TokenType.RBOOK)

        # 如果后面跟着 LPAREN，则是段落调用
        if self._match(TokenType.LPAREN):
            self._consume(TokenType.LPAREN)

            args = []
            while not self._match(TokenType.RPAREN):
                # 使用 _parse_comparison 而非 _parse_expr，
                # 避免逗号被误识别为管道操作符
                arg = self._parse_comparison()
                args.append(arg)

                # 逗号分隔
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)

            self._consume(TokenType.RPAREN)

            return ParagraphCall(name, args)

        # 否则是字符串字面量
        return StringLiteral(name)