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
from keywords import (
    VERB_ARITY, STDLIB_VERB_ARITY, ALL_VERB_ARITY,
    KEYWORDS_DOUBLE, KEYWORDS_SPECIAL, ALL_KEYWORDS,
)
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

# 具名实参（kwarg=value）参数名收集时的停用关键字集合（v7 新单 B）。
# 全仓唯一定义点：收名字时一旦碰到这些语句/表达式起始关键字即停，
# 防止把 `依据` 后面的 `段`… 误并进参数名。
#
# 引用点共 3 处（本文件内，按符号名定位，不写行号以免注释随编辑漂移；
# grep `_KWARG_NAME_STOP_KEYWORDS` 可一次列全）：
#   · _try_parse_keyword_arg() —— 被两条收参循环各调用一次。实测这条 helper
#     接走了绝大多数写法：`甲(a = 1)`、`排序(数组, 依据 = 键)`、`对象的方法(参数 = 1)`
#     全走 helper。
#   · 成员方法调用括号收参循环内联使用（_kwarg_stop_kws）。实测只有**英文点号**
#     写法 `对象.方法(参数 = 1)`（FFI/外部库调用）会进这里，「的」字写法不会。
#   · ParagraphCall 括号收参循环内联使用（_kwarg_stop_kws）。用 sys.settrace 试过
#     12 种候选写法都没命中它的 kwarg 段落——helper 先接走了，暂未找到可达输入。
#     保留不删是因为判据本身没错，删它属于无实证依据的清理；但别拿它当已验证路径。
# 两处内联不改调 helper，是因为取值粒度（_parse_comparison）与回退行为跟
# helper（_parse_logical_expr）不同，合并会改语义；此处只统一「判据集合」
# 这一份数据，杜绝集合本身漂移。守卫见
# tests/unit/test_prescan_embed_semicolon_kwarg.py 末两个测试类。
#
# 注意：_fn_stop / _fn_stop2 看着像同一份表，其实多了「在/于/中的/包含」四项，
# 服务的是**函数名动词合并**而不是 kwarg 收名，不可与本常量合并。
_KWARG_NAME_STOP_KEYWORDS = frozenset({
    '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
    '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
    '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
    '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
    '匹配', '情况', '的', '之', '对', '步', '至', '到',
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

    def _try_parse_keyword_arg(self) -> Optional[ASTNode]:
        """尝试把当前位置解析成具名实参 `名 = 值`；失败则原位回退并返回 None。

        —— v7 新单 B（具名实参 kwarg=value），上一轮修单 04 时备案的独立缺陷 ——
        括号式收参循环里原本没有「标识符 + `=` → 关键字实参」这条产生式，
        实测（改前）`甲(a = 1)` / `排序(xs, 依据 = f)` 一律抛
        「意外的标记: 「=」」。本方法补齐该产生式，产出 KeywordArg
        （ast_nodes_v3.py:1229），code_generator 的 ParagraphCall 分支
        （code_generator.py:2270-2274）已能把它发射成 Python `名=值`。

        判据（纯词法，不做语义猜测）：
          连续的 IDENTIFIER / 非停用 KEYWORD 若干个  +  紧跟一个 EQUALS。

        为什么这个判据不会把比较误判成赋值：
          · `=` 的 token 是 EQUALS（tokens.py:43），比较用的 `==` 是另一个
            token EQ_EQ（tokens.py:54，lexer.py:981-982 双字符优先匹配）。
            词法层面就已分开，收完名字看到 EQ_EQ 即回退成位置实参，
            故 `f(a == 1)`、`若 a == 1:` 不受影响（实测见报告反例）。
          · 赋值在光明里是**语句**不是表达式（海象运算符被 :52 显式拒绝），
            所以括号实参区里出现裸 `=` 只可能是具名实参。
          · 单向放宽：改前实参区一出现 EQUALS 就是 ParseError，即当前**能**
            解析成功的输入实参区里一定没有 EQUALS。因此本产生式只可能把
            「原本报错」变成「正确解析」，不可能改写任何既有产物。

        名字允许多 token 拼接：lexer 会把 `步长天` / `获取函数` 这类名字切成
        数段，只有确认后面紧跟 `=` 时才提交，否则 self.pos 原样还原。
        """
        cur = self._current()
        if not cur or cur.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            return None
        saved_pos = self.pos
        name_parts = []
        while self._current():
            t = self._current()
            if t.type == TokenType.IDENTIFIER:
                name_parts.append(self._consume().value)
            elif t.type == TokenType.KEYWORD and t.value not in _KWARG_NAME_STOP_KEYWORDS:
                name_parts.append(self._consume().value)
            else:
                break
        if not (name_parts and self._current() and self._current().type == TokenType.EQUALS):
            self.pos = saved_pos
            return None
        self._consume(TokenType.EQUALS)
        value = self._parse_logical_expr()
        if value is None:
            # 取不到值就整体回退：宁可维持原来的报错，也不要吞掉半个实参
            self.pos = saved_pos
            return None
        from ast_nodes_v3 import KeywordArg
        return KeywordArg(''.join(name_parts), value)

    
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
                # 处理"大于 等于"和"小于 等于"（空格分隔的两关键字，如"年龄 大于 等于 18"）
                if op in ('大于', '小于') and self._current() and \
                   self._current().type == TokenType.KEYWORD and self._current().value == '等于':
                    self._consume()  # 消耗"等于"
                    op = '大于等于' if op == '大于' else '小于等于'
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
        #
        # v7 单 07：原判据只认「等待 标识符(」一种「这是 await 而非复合词」的形状，
        # 漏了「等待 标识符.成员」。`等待 f.读取()` 的 token 流是
        #   KEYWORD(等待) IDENTIFIER(f) DOT(.) KEYWORD(读取) LPAREN RPAREN
        # peek2 是 DOT，于是走进下面的复合标识符分支，只吃掉 `等待`+`f` 返回
        # Identifier('等待f')，`.读取()` 整段被丢在流里没人消费，报
        # 「无法识别的语法元素：'.'」。`等待 对象.方法()` 是异步代码最常见的写法，
        # 判为编译器缺陷。DOT 归入「后续是 await 表达式」一侧即可，
        # RPAREN/NEWLINE 等仍留在复合标识符一侧，`等待价值` 零影响。
        # v7 单 31-C：`等` 是 L0 冻结表承诺的 await 单字别名，与 `等待` 同分支处理。
        if tok.type == TokenType.KEYWORD and tok.value in ('等待', '等'):
            kw = tok.value
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.IDENTIFIER:
                peek2 = self._peek(2)
                if peek2 and peek2.type not in (TokenType.LPAREN, TokenType.DOT):
                    # 复合标识符：等待 + 价值 = 等待价值（`等` 因 compound-safe 一般在
                    # 词法层就并成整词，极少走到这里；保留分支与 `等待` 语义对齐）
                    self._consume(TokenType.KEYWORD, kw)
                    ident = self._consume(TokenType.IDENTIFIER).value
                    return Identifier(kw + ident)
                # 等待 函数名() / 等待 对象.成员 → await 表达式
                self._consume(TokenType.KEYWORD, kw)
                expr = self._parse_expr()
                return AwaitExpr(expr)
            self._consume(TokenType.KEYWORD, kw)
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

        # 表达式位置的 `段(参数…) 返 <表达式>` = 匿名函数（v7 新单 B）
        # 真实用例 examples/L2_wenyan/主程序.light:58：
        #     设 排名 = 排序(学生列表, 依据 = 段(x) 返 -x之取平均分())
        # 改前实测：`段(x)` 被当成「调用名为 段 的函数」，后面的 `返 -x…` 又被当成
        # 同一个调用的第二个位置实参，产出
        #     sorted(学生列表, 依据=段(x), (返 - x.取平均分()))
        # ——python 直接 SyntaxError（positional argument follows keyword argument）。
        #
        # `段` 在**语句**位置是函数定义关键字，走的是 parser_stmt 那条路，不经过这里；
        # 本分支只在表达式位置生效，不影响 `段 名(…):` 的定义语法。
        #
        # 判据保守：必须凑齐 `段` `(` …参数… `)` `返` 才认。`返` 不出现就把 self.pos
        # 原样还原、退回原有的调用解析——回退后行为与改前逐字一致，既不会把已有
        # `段(x)` 形态改坏，也不会新造静默错译。
        if tok.type == TokenType.KEYWORD and tok.value == '段':
            _lam_saved_pos = self.pos
            lam = self._try_parse_duan_lambda()
            if lam is not None:
                return self._parse_postfix(lam)
            self.pos = _lam_saved_pos

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

        # 字节串 b"..."（v7 新单 H）
        # 不走插值检测：bytes 里没有中文插值语义，Python 也不支持 bf"" 组合。
        if tok.type == TokenType.BYTES:
            self._consume()
            return self._parse_postfix(StringLiteral(tok.value, is_bytes=True))


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
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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
                        # SEMICOLON 是同行多语句分隔符，必须终止实参收集 ——
                        # 否则 `打印 ""; 打印 "x"` 会把 `;` 送进 _parse_logical_expr
                        # 并在 _parse_primary 末尾抛「意外的标记: 「;」」
                        # （examples/L3_domain/all_in_one_L3_demo.light:41）。
                        # C 风格 `循环(init; cond; incr)` 的分号在括号内、由
                        # _parse_c_for_loop 自己消费，不经过这条无括号收参路径。
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.RPAREN, TokenType.RBRACKET,
                                             TokenType.NEWLINE, TokenType.DEDENT, TokenType.INDENT,
                                             TokenType.SEMICOLON):
                            break
                        # 三元条件表达式「如果 ... 那么 ... 否则 ...」等表达式起始关键字不能作为参数终止符，
                        # 否则「打印 如果 条件 那么 A 否则 B」会被截断为 打印 然后 如果 被当作语句
                        # （_EXPR_START_KEYWORDS 已覆盖「如果」及其他表达式起始关键字）
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
                    #
                    # v7 单 04：这里原来是 `while not RPAREN and collected < arity`，
                    # 拿动词的内置元数去截断**用户已用括号界定好**的参数列表。
                    # `求和` 在 keywords.py 的 VERB_ARITY 里 arity=1，于是
                    # `段 求和(a, b)` + `求和(10, 20)` 只收到 `10`，下面 :659 的
                    # 「跳过剩余 token 直到右括号」把 `, 20` 整段吞掉，产物变成
                    # `求和(10)`，运行期才炸 missing 1 required positional argument。
                    # 不是只丢最后一个：三参 `求和(1,2,3)` 会丢掉 arity 之后的全部。
                    # 编译期不报错、产物语义与源码不符，属静默错译。
                    #
                    # arity 上限的存在意义是给**无括号并置式**（`求和 10 20`）消歧——
                    # 那种写法没有分隔符，必须靠元数知道抓几个。而括号式的
                    # `(` … `)` 与 `,` 已经把边界写死了，再套 arity 纯属误用。
                    # 故去掉括号式这一侧的 arity 上限，:672 起的无括号分支不动。
                    #
                    # 单向放宽：对「实参数 ≤ arity」的一切旧输入，收满即遇 RPAREN 停，
                    # 产物逐字节不变；只有原本被吞参的输入改为忠实收全。不会凭空
                    # 产生原先没有的语义——要么正确执行，要么用户真传错参时得到
                    # 清晰的 Python TypeError。
                    self._consume(TokenType.LPAREN)
                    collected = 0
                    while not self._match(TokenType.RPAREN):
                        if self._current() and self._current().type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            continue
                        # v7 新单 B（第 3 票）：具名实参 `名 = 值`。
                        # `排序(学生列表, 依据 = f)` 里 `依据` 是参数名而非表达式；
                        # 改前实测 ParseError「意外的标记: 「=」」（不是静默错译）。
                        # 判据与回退理由见 _try_parse_keyword_arg 的 docstring：
                        # 取不到「名 + EQUALS」就原位回退，走下面原来的位置实参路径，
                        # 故对不含 `=` 的旧输入产物逐字节不变。
                        kwarg = self._try_parse_keyword_arg()
                        if kwarg is not None:
                            args.append(kwarg)
                            collected += 1
                            if self._match(TokenType.COMMA):
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

        # L0 v4.0 单字 `新`（≡ 新建）类实例化：新 类名(参数...)
        #
        # 与 `性`/`构` 同理，`新` 有意**不**升为保留字（新增、更新、最新、新建…
        # 都含此字，升为关键字会在词法层切碎大量标识符）。这里按三 token 形状
        # 识别：IDENTIFIER('新') + IDENTIFIER(类名) + LPAREN。
        # 只收带括号的形式——无括号的 `新 类名 参数...` 与「标识符并列」歧义，
        # 不值得为它扩大判据；需要时写 `新建` 双字形式。
        if (tok.type == TokenType.IDENTIFIER and tok.value == '新'
                and self._peek(1) and self._peek(1).type == TokenType.IDENTIFIER
                and self._peek(2) and self._peek(2).type == TokenType.LPAREN):
            self._consume()                      # 新
            class_name = self._consume().value   # 类名
            self._consume(TokenType.LPAREN)
            args = []
            while self._current() and self._current().type != TokenType.RPAREN:
                if self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                arg = self._parse_comparison()
                if arg is None:
                    break
                args.append(arg)
            self._consume(TokenType.RPAREN)
            return self._parse_postfix(ClassInstantiation(class_name, args))

        # 同上，但走 `超`（v7 新单 I）。
        # L2 v4.0 规范（docs/L2_文言体语法规范_v4.0.md:433/574/927）写的 super 形状是
        # `超.方法()`，而实现侧一直只认 `父`——规范承诺从未落地，写 `超.构(...)` 会被当成
        # 未定义标识符 `超`，编译过、运行期 NameError（静默错编）。
        # `超` 不升关键字：超时/超集/超参数/超几何/超导… 复合词会被 lexer 切碎
        # （同 `性`/`构`/`新` 的判断）。改按形状识别——IDENTIFIER('超') 后紧跟
        # 成员访问符（`.` / `的` / 已废弃的 `之`）才是 super，裸 `超` 仍是普通标识符。
        # 三种访问符都要认：`的` 是当前推荐写法，`.` 是 ASCII 形式，`之` 兼容旧文言体。
        #
        # 落点必须在下面那条「标识符」通吃分支之前：`超` 是 IDENTIFIER，一旦落进
        # _collect_single_arg 就再也回不来了（`父` 是 KEYWORD 所以能放在更后面）。
        _nxt = self._peek(1)
        if (tok.type == TokenType.IDENTIFIER and tok.value == '超'
                and _nxt is not None
                and (_nxt.type == TokenType.DOT
                     or (_nxt.type == TokenType.KEYWORD and _nxt.value in ('的', '之')))):
            self._consume()
            return self._parse_postfix(Identifier("super()"))

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
                arity = ALL_VERB_ARITY.get(name, 2)
                args = []
                if arity == -1:
                    # 可变参数
                    while self._current():
                        next_tok = self._current()
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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

        # 字节串 b"..."（v7 新单 H）
        if tok.type == TokenType.BYTES:
            self._consume()
            return StringLiteral(tok.value, is_bytes=True)

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
                    _fn_candidate = ''.join(_fn_parts2)
                    # 函数名含运算符动词的合并需以「用户已定义该名字」为前提。
                    #
                    # Bug 根因：词法器把 "n乘阶乘(" 拆成 标识符 n + 动词 乘 + 标识符 阶乘，
                    # 解析器原先无条件把这些相邻令牌合并成函数名 "n乘阶乘"，使本应是
                    # 乘法表达式 n * 阶乘(...) 的紧凑写法被误当成函数调用（NameError）。
                    #
                    # 修复方案：合并结果必须是 lexer 预扫描出的用户定义
                    # （lexer.user_definitions，来自段落/方法/变量声明）才生效，
                    # 否则回退令牌位置，交由二元运算符解析机制处理。
                    # 与 _parse_primary / _collect_single_arg 保持同一套规则（三处必须同步）。
                    _user_defs = getattr(self.lexer, 'user_definitions', None) or set()
                    if _fn_candidate in _user_defs:
                        name = _fn_candidate
                    else:
                        self.pos = _fn_saved_pos
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
                    if nt.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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
                    if nt.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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

        # 字节串 b"..."（v7 新单 H）
        if tok.type == TokenType.BYTES:
            self._consume()
            return StringLiteral(tok.value, is_bytes=True)

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
            
            # 合并连续的 IDENTIFIER 令牌（tokenizer 可能把 "字典创建" 拆成两个 IDENTIFIER）。
            # 不合并运算符动词（如"减去"、"取余"等）。
            #
            # Bug 根因：原实现合并时不检查令牌在源码中是否相邻（无空格），
            # 使 "转字符串 x"（转字符串 与 x 之间有空格）被错误合并成 "转字符串x"。
            #
            # 修复方案：用列号追踪相邻性 —— 仅当后一个 IDENTIFIER 的起始列恰好等于
            # 前一个令牌的结束列（col + len(value)）时才合并；带空格的 "转字符串 x"
            # 保持为两个独立标识符（转字符串 为函数调用，x 为参数）。
            _prev_col = tok.col + len(tok.value)
            while self._current() and self._current().type == TokenType.IDENTIFIER \
                    and self._current().value not in self.ADD_OP_MAP \
                    and self._current().value not in self.MUL_OP_MAP \
                    and self._current().value != '不':
                _cur = self._current()
                if _cur.col != _prev_col:
                    break
                name += self._consume().value
                _prev_col = _cur.col + len(_cur.value)
            
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
                    _fn_candidate = ''.join(_fn_parts)
                    # 函数名含运算符动词的合并需以「用户已定义该名字」为前提。
                    #
                    # Bug 根因：词法器把 "n乘阶乘(" 拆成 标识符 n + 动词 乘 + 标识符 阶乘，
                    # 解析器原先无条件合并成函数名 "n乘阶乘"，使紧凑乘法表达式
                    # n * 阶乘(n-1) 被误当成函数调用（NameError）。
                    #
                    # 修复方案：合并结果必须是 lexer 预扫描出的用户定义
                    # （lexer.user_definitions，来自段落/方法/变量声明）才生效，
                    # 否则回退令牌位置，交由二元运算符机制解析（n * 阶乘((n-1))）。
                    # 与 _collect_primary_arg / _collect_single_arg 保持同一套规则（三处必须同步）。
                    _user_defs = getattr(self.lexer, 'user_definitions', None) or set()
                    if _fn_candidate in _user_defs:
                        name = _fn_candidate
                    else:
                        self.pos = _fn_saved_pos
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
                # 如果是已知的 stdlib 动词，使用其 arity 限制参数收集
                stdlib_arity = STDLIB_VERB_ARITY.get(name)
                args = []

                # 括号语法：函数(参数1, 参数2)

                if self._current() and self._current().type == TokenType.LPAREN:
                    self._consume(TokenType.LPAREN)
                    while self._current() and self._current().type != TokenType.RPAREN:
                        if self._current().type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            continue
                        # 具名实参 `名 = 值`。_try_parse_keyword_arg 已接进另外两条
                        # 收参路径（:763 的 arity 路径、:2545 的后缀链式括号路径），
                        # 唯独这条「无 arity 记录的标识符括号调用」漏接，导致
                        # `日期范围(甲, 乙, 步长天=1)` 抛「意外的标记: 「=」」
                        # （examples/F阶段_标准库增强/F3_段言侧三个增强模块示例.light:21）。
                        # 该方法失败时 self.pos 原位回退，且 `==` 是 EQ_EQ 与 `=` 词法层
                        # 就分开，故 f(a == 1) 不受影响 —— 单向放宽。
                        kwarg = self._try_parse_keyword_arg()
                        if kwarg is not None:
                            args.append(kwarg)
                            continue
                        arg = self._parse_comparison()
                        if arg:
                            args.append(arg)
                        else:
                            break
                    if self._current() and self._current().type == TokenType.RPAREN:
                        self._consume(TokenType.RPAREN)
                    expr = ParagraphCall(name, args) if args else ParagraphCall(name, [])
                    return self._parse_postfix(expr)

                # 无括号语法：使用 arity 限制参数收集
                if stdlib_arity is not None:
                    if stdlib_arity == 0:
                        # 无参数函数
                        expr = ParagraphCall(name, [])
                    elif stdlib_arity == -1:
                        # 可变参数：收集到阻断符为止
                        while self._current():
                            next_tok = self._current()
                            if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
                                break
                            if next_tok.type == TokenType.KEYWORD and next_tok.value in KEYWORDS_DOUBLE:
                                break
                            if next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                                break
                            if next_tok.type == TokenType.IDENTIFIER and (next_tok.value in self.ADD_OP_MAP or next_tok.value in self.MUL_OP_MAP):
                                break
                            if next_tok.type == TokenType.IDENTIFIER and next_tok.value == '\u4e0d':
                                break
                            if next_tok.type == TokenType.NUMBER:
                                args.append(NumberLiteral(self._consume().value))
                            elif next_tok.type == TokenType.CHINESE_NUM:
                                args.append(NumberLiteral(self._consume().value))
                            elif next_tok.type == TokenType.STRING:
                                args.append(StringLiteral(self._consume().value))
                            elif next_tok.type == TokenType.IDENTIFIER:
                                args.append(Identifier(self._consume().value))
                            else:
                                break
                        expr = ParagraphCall(name, args)
                    else:

                        # 固定参数：收集指定数量
                        for _ in range(stdlib_arity):
                            if not self._current():
                                break
                            next_tok = self._current()
                            if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
                                break
                            if next_tok.type == TokenType.KEYWORD and next_tok.value in KEYWORDS_DOUBLE:
                                break
                            if next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                                break
                            if next_tok.type == TokenType.IDENTIFIER and (next_tok.value in self.ADD_OP_MAP or next_tok.value in self.MUL_OP_MAP):
                                break
                            if next_tok.type == TokenType.IDENTIFIER and next_tok.value == '\u4e0d':
                                break
                            if next_tok.type == TokenType.NUMBER:
                                args.append(NumberLiteral(self._consume().value))
                            elif next_tok.type == TokenType.CHINESE_NUM:
                                args.append(NumberLiteral(self._consume().value))
                            elif next_tok.type == TokenType.STRING:
                                args.append(StringLiteral(self._consume().value))
                            elif next_tok.type == TokenType.IDENTIFIER:
                                args.append(Identifier(self._consume().value))
                            else:
                                break
                        expr = ParagraphCall(name, args)
                else:
                    # 普通标识符：保持原有的贪婪收集行为
                    while self._current():
                        next_tok = self._current()
                        if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
                            break
                        if next_tok.type == TokenType.KEYWORD and next_tok.value in self.OPERATOR_VERBS:
                            break
                        if next_tok.type == TokenType.IDENTIFIER and                            (next_tok.value in self.ADD_OP_MAP or next_tok.value in self.MUL_OP_MAP):
                            break
                        if next_tok.type == TokenType.IDENTIFIER and next_tok.value == '不':
                            break
                        if next_tok.type == TokenType.KEYWORD and next_tok.value in KEYWORDS_DOUBLE:
                            break
                        if next_tok.type == TokenType.NUMBER:
                            args.append(NumberLiteral(self._consume().value))
                        elif next_tok.type == TokenType.CHINESE_NUM:
                            args.append(NumberLiteral(self._consume().value))
                        elif next_tok.type == TokenType.STRING:
                            args.append(StringLiteral(self._consume().value))
                        elif next_tok.type == TokenType.IDENTIFIER:
                            args.append(Identifier(self._consume().value))
                        else:
                            break
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
                if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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

        # 字节串 b"..."（v7 新单 H）
        if tok.type == TokenType.BYTES:
            self._consume()
            return StringLiteral(tok.value, is_bytes=True)

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
                    if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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
                if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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
            if re.match(r'^[\u4e00-\u9fa5a-zA-Z_][\u4e00-\u9fa5a-zA-Z0-9_.\[\]"\'\u3010\u3011]*$', expr_part):
                # 简单标识符：{甲}、{对象.属性}、{列表[0]}
                if m.start() > last_end:
                    parts.append(value[last_end:m.start()])
                if format_spec:
                    parts.append((Identifier(expr_part), format_spec))
                else:
                    parts.append(Identifier(expr_part))
                last_end = m.end()
                continue
            # 表达式插值：{甲 乘 甲}、{平方(甲)} — 子解析验证并生成表达式节点
            expr_node = self._try_parse_interp_expr(expr_part)
            if expr_node is None:
                has_invalid = True
                break
            if m.start() > last_end:
                parts.append(value[last_end:m.start()])
            if format_spec:
                parts.append((expr_node, format_spec))
            else:
                parts.append(expr_node)
            last_end = m.end()

        # 如果有无效的插值模式，整个字符串不作为插值处理
        if has_invalid:
            return None

        # 尾部普通文本
        if last_end < len(value):
            parts.append(value[last_end:])

        # 如果只有普通文本（没有真正的插值），返回 None
        has_expr = any(not isinstance(p, str) for p in parts)
        if not has_expr:
            return None

        return StringInterpolation(parts)

    def _try_parse_interp_expr(self, expr_text: str):
        """尝试将插值内容作为光明表达式解析；成功返回 ASTNode，失败返回 None"""
        import re
        # 快速拒绝模板字符/特殊符号（如 {%原始%}、反引号、反斜杠），不视为插值
        if re.search(r'[%\`\\]', expr_text):
            return None
        try:
            from lexer import Lexer
            from light_parser_v3 import LightParser
            sub_lexer = Lexer()
            sub_tokens = sub_lexer.tokenize(expr_text)
            sub_parser = LightParser()
            sub_parser.tokens = sub_tokens
            sub_parser.pos = 0
            node = sub_parser._parse_expr()
            # 必须消费完所有 token（容错末尾 EOF token），避免接受残句如 {甲 乘}
            if node is not None and sub_parser.pos >= len(sub_tokens) - 1:
                # Bug 根因（合并回归）：本方法（表达式插值兜底）来自段言侧，比
                # light 原先"仅允许简单标识符"的严格判定宽松得多。JSON 字面量
                # 形如 '{"name": "光明", "version": 4}' 会被 {…} 正则整体命中，
                # 再按第一个冒号切成 expr_part='"name"' + format_spec='"光明"…'，
                # 而 '"name"' 恰好能作为【纯字符串字面量】表达式解析成功，于是
                # 普通 JSON 串被误判为插值、生成出 f'{"name":…}' 直接炸掉。
                # 纯字面量（字符串/数字/布尔/空）插值本身没有任何意义（等价于
                # 直接写该字面量），light 原实现也不接受，故一律拒绝。
                if type(node).__name__ in (
                    'StringLiteral', 'NumberLiteral', 'BooleanLiteral', 'NullLiteral',
                ):
                    return None
                return node
        except Exception:
            pass
        return None


    def _try_parse_duan_lambda(self):
        """尝试解析表达式位置的 `段(参数…) 返 <表达式>` 匿名函数（v7 新单 B）。

        凑齐要素返回 LambdaExpression；缺 `(`、缺 `)`、缺 `返` 一律返回 None，
        由调用方还原 self.pos 退回普通调用解析。全程只前移 self.pos、不抛异常，
        保证「不认」时的行为与改动前逐字一致。
        """
        # 段
        if not (self._current() and self._current().type == TokenType.KEYWORD
                and self._current().value == '段'):
            return None
        self._consume(TokenType.KEYWORD, '段')

        # (
        if not (self._current() and self._current().type == TokenType.LPAREN):
            return None
        self._consume(TokenType.LPAREN)

        # 参数名列表，逗号分隔，允许空参
        params = []
        while self._current() and self._current().type != TokenType.RPAREN:
            tok = self._current()
            if tok.type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                params.append(self._consume().value)
            else:
                return None

        # )
        if not (self._current() and self._current().type == TokenType.RPAREN):
            return None
        self._consume(TokenType.RPAREN)

        # 返 / 返回：没有它就不是匿名函数，回退
        if not (self._current() and self._current().type == TokenType.KEYWORD
                and self._current().value in ('返', '返回')):
            return None
        self._consume(TokenType.KEYWORD, self._current().value)

        # 函数体：单个表达式
        body = self._parse_expr()
        if body is None:
            return None
        return LambdaExpression(params, body)

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
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
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

    def _列表字面量下标(self, node: ASTNode) -> ASTNode:
        """列表字面量紧跟后缀符时，把后缀接到字面量上。

        为什么必须做：字典/集合字面量都走 _parse_postfix，唯独列表字面量直接返回
        （见 _parse_primary 的 `return self._parse_list_literal()`），于是
        `[1,2,3][0]` 被解析成「两个相邻表达式」，静默算出 `([1,2,3], [0])`
        且 rc=0 —— 错误结果冒充成功，护栏（rc==0 且有输出）抓不到。
        同理，`[1,2,3].连接(",")` 也会因 `.` 未被接上而报「意外的标记 .」。

        这里在下一个 token 是「后缀触发符」时转交 _parse_postfix。_parse_postfix 自身
        只在遇到 BANG/LPAREN/DOT/「的」/「之」/LBRACKET 时才动作，其余（逗号、右括号、
        换行）一律原样返回，故影响面仅限真正的后缀写法，不改变 `设 表 为 [1,2,3]`、
        嵌套列表 `[[1],[2]]`、`打印([1,2,3])` 等行为。
        """
        tok = self._current()
        if tok is None:
            return node
        _后缀触发 = (
            tok.type == TokenType.LBRACKET
            or tok.type == TokenType.DOT
            or tok.type == TokenType.BANG
            or tok.type == TokenType.LPAREN
            or (tok.type == TokenType.KEYWORD and tok.value in ('的', '之'))
        )
        if _后缀触发:
            return self._parse_postfix(node)
        return node

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
                return self._列表字面量下标(ListComprehension(first_expr, var, it, cond))
            else:
                # 多重generator
                first_gen = generators[0]
                return self._列表字面量下标(ListComprehension(first_expr, first_gen[0], first_gen[1], first_gen[2], generators=generators))

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
        return self._列表字面量下标(ListLiteral(elements))
    
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
                    # 链式调用：expr()  → FunctionCallExpr(expr, args)
                    # 支持 func()()、obj.method()()、func()().method() 等
                    args = []
                    while not self._match(TokenType.RPAREN):
                        if self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._consume()
                            continue
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
                        arg = self._parse_comparison()
                        if arg is not None:
                            args.append(arg)
                        else:
                            break
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                        while self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                            self._consume()
                    if self._current() and self._current().type == TokenType.RPAREN:
                        self._consume(TokenType.RPAREN)
                    from ast_nodes_v3 import FunctionCallExpr
                    expr = FunctionCallExpr(expr, args)
                    continue

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
                    # 停用字判据统一走模块常量，与 _try_parse_keyword_arg 单点同源，避免分叉。
                    _kwarg_saved_pos = self.pos
                    _kwarg_name_parts = []
                    _kwarg_stop_kws = _KWARG_NAME_STOP_KEYWORDS
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
                # DOT 已在 lexer 层拆分：DOT 始终是英文点号（成员访问），PERIOD 是中文句号（语句结束）
                is_dot_access = True

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
                            # 停用字判据统一走模块常量，与 _try_parse_keyword_arg 单点同源，避免分叉。
                            _kwarg_saved_pos = self.pos
                            _kwarg_name_parts = []
                            _kwarg_stop_kws = _KWARG_NAME_STOP_KEYWORDS
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
                            if next_tok.type in (TokenType.DOT, TokenType.PERIOD, TokenType.COMMA, TokenType.RPAREN, TokenType.RBRACKET, TokenType.SEMICOLON):
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