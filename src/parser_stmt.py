"""
光明（Light）编程语言 - 语句解析混入类

提供所有语句级别解析方法，包括：
- 模块解析
- 变量声明、赋值、条件、循环
- 导入/导出
- 段落定义
- 类/接口定义
- 模式匹配
- 异常处理
"""

from typing import List, Any, Optional
from tokens import Token, TokenType
from keywords import VERB_ARITY, STDLIB_VERB_ARITY, ALL_VERB_ARITY, KEYWORDS_DOUBLE, KEYWORDS_SPECIAL, BUILTIN_TYPES
from ast_nodes_v3 import *
from parser_core import ParseError



# C风格语法 AST 节点
class CForStmt(ASTNode):
    """C风格for循环：循环(init;cond;incr){body}"""
    def __init__(self, init, condition, increment, body):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body

    def __repr__(self):
        return f"CForStmt(init={self.init}, cond={self.condition}, incr={self.increment})"


class Block(ASTNode):
    """花括号代码块"""
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({len(self.statements)} stmts)"


class ClassDefinitionWithNested(ClassDefinition):
    """A2-5：带嵌套类的类定义。

    为什么是子类而不是给 `ClassDefinition` 加字段：宿主节点在
    `ast_nodes_v3.py:504-505`，`__slots__` 固定为六项且基类 `ASTNode` 也有
    `__slots__`（实例没有 `__dict__`，动态挂属性直接 AttributeError）；而
    `ast_nodes_v3.py` **不在任务 A2 的可改文件清单里**（任务书「交付要求」①）。
    子类加一个 slot 同时满足两个约束：`isinstance(x, ClassDefinition)` 仍为真，
    既有消费方（`type_inferencer` / `compiler.AstAdapter` / `llvm` 侧）零改动；
    而且**没有嵌套类时根本不构造这个子类**，对既有产物零影响。
    """
    __slots__ = ('nested_classes',)

    def __init__(self, *args, nested_classes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.nested_classes = nested_classes or []

    def __repr__(self):
        return f"ClassDefinitionWithNested({self.name}, 嵌套 {len(self.nested_classes)})"


class ParserStmtMixin:
    """语句解析混入类"""
    
    # =========================================================================
    # 类型标注解析
    # =========================================================================
    
    def _parse_type_annotation(self) -> Optional[str]:
        """解析复杂类型标注，如 列表<整数>、整数|浮点、可空整数、字典<字符串, 整数>
        
        返回完整的类型标注字符串，不包含后续的运算符/分隔符。
        返回 None 表示没有类型标注。
        """
        parts = []
        self._parse_type_union(parts)
        if not parts:
            return None
        return ''.join(parts)
    
    def _parse_type_union(self, parts: list):
        """解析联合类型：type(|type)*"""
        self._parse_type_atom(parts)
        while self._current() and self._current().type == TokenType.PIPE:
            parts.append(self._consume(TokenType.PIPE).value)
            self._parse_type_atom(parts)
    
    def _parse_type_atom(self, parts: list):
        """解析类型原子：基本类型 | 泛型类型 | 可选类型
        
        支持：
        - 基本类型：整数、浮点、字符串、布尔、空、任意、int、float、str、bool
        - 泛型类型：列表<元素类型>、字典<键类型, 值类型>
        - 可选类型：可空 类型
        """
        if not self._current():
            return
        
        tok = self._current()
        
        # 可选类型：可空 整数
        if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) and tok.value == '可空':
            parts.append(self._consume().value)
            self._parse_type_atom(parts)
            return
        
        # 基本类型名
        if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            type_name = self._consume().value
            parts.append(type_name)
            
            # 泛型类型：列表<...> 或 字典<...>
            if self._current() and self._current().type == TokenType.LESS:
                parts.append(self._consume(TokenType.LESS).value)
                # 泛型参数
                self._parse_type_union(parts)  # 第一个泛型参数
                # 字典<键, 值> 需要逗号分隔
                while self._current() and self._current().type == TokenType.COMMA:
                    parts.append(self._consume(TokenType.COMMA).value)
                    self._parse_type_union(parts)
                if self._current() and self._current().type == TokenType.GREATER:
                    parts.append(self._consume(TokenType.GREATER).value)
                # 支持嵌套泛型：列表<字典<字符串, 整数>> 的连续 >>
                while self._current() and self._current().type == TokenType.GREATER:
                    # 但不要把单个 > 当作闭括号重复消费
                    # 检查是否后面还有 >（嵌套泛型结束）
                    next_tok = self._peek(1)
                    if next_tok and next_tok.type == TokenType.GREATER:
                        # 这是嵌套泛型的闭合，需要把 > 留到外层处理
                        # 但当前 token 是 GREATER，且之前已经消费了对应的 LESS
                        # 这种情况下，外层 LESS 已经消费了一个 GREATER
                        # 内层嵌套的 LESS 也需要对应的 GREATER
                        # 实际上，外层 LESS 消费后会递归调用 _parse_type_atom
                        # 递归调用会自己消费 GREATER
                        # 所以这里不需要再消费
                        break
                    break
        else:
            # 可能是括号包裹的类型：(整数|浮点) -> 字符串
            if self._current().type == TokenType.LPAREN:
                parts.append(self._consume(TokenType.LPAREN).value)
                self._parse_type_union(parts)
                if self._current() and self._current().type == TokenType.RPAREN:
                    parts.append(self._consume(TokenType.RPAREN).value)
    
    # =========================================================================
    # 语法规则
    # =========================================================================
    
    def _parse_module(self) -> Module:
        """解析模块"""
        statements = []

        while self._current():
            tok = self._current()

            # 跳过外层的DEDENT（level=0）
            if tok.type == TokenType.DEDENT:
                dedent_level = getattr(tok, 'value', None)
                # 如果level是None或level == 0，表示这是外层结构的结束
                # 消耗这个DEDENT并继续
                if dedent_level is None or dedent_level == 0:
                    self._consume(TokenType.DEDENT)
                    continue

            # 跳过空行（NEWLINE）
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue

            # 分号：同行多语句分隔符。与 parser_core._parse_module_with_recovery
            # 的容错版同口径（见那里的注释）。
            if tok.type == TokenType.SEMICOLON:
                self._consume(TokenType.SEMICOLON)
                continue


            # 跳过孤立的句号（结构定义结束后的可选终止符）
            if tok.type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
                continue

            # 跳过模块顶层的"结束"关键字（可选的块终止符）
            if tok.type == TokenType.KEYWORD and tok.value == '结束':
                self._consume(TokenType.KEYWORD, '结束')
                continue
            if tok.type == TokenType.IDENTIFIER and tok.value == '结束':
                self._consume(TokenType.IDENTIFIER, '结束')
                continue

            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
            else:
                # 无法解析，跳出循环避免无限循环
                break

        return Module(statements)

    def _parse_statement(self) -> Optional[ASTNode]:
        """解析语句"""
        tok = self._current()
        
        if tok is None:
            return None
        
        # 嵌入块：嵌入 Python/C: ... 结束嵌入
        if tok.type == TokenType.EMBED_BLOCK:
            return self._parse_embed_block()

        # 导入语句：导入 / 导
        if tok.type == TokenType.KEYWORD and tok.value in ('导入', '导'):
            return self._parse_import_stmt()

        # 导入语句单字别名 `引`（v7 单 31-F，L0 冻结表 docs/language/l0-core.md:64
        # 「模块（3字）」把 `引` 定为「导入/引用」）。
        #
        # 与本单另两个字不同：`引` **本来就是关键字**（KEYWORDS_EMBED，且已在
        # `_COMPOUND_SAFE_SINGLE_KEYWORDS` 里），缺的只是这条 parser 分支——
        # 所以词法层与关键字表零改动，A/B 风险为 0。
        #
        # 与 L4 嵌入块（`引 Python:` … `结束引`）的消歧**已经在词法层完成**，这里
        # 不需要再判冒号：`lexer._tokenize_embed_block` 要求语言名后面必须紧跟冒号，
        # 否则回报 `(None, 0)`、不吞任何字符，控制流落到普通标识符/关键字分词，
        # 于是 `引 数学。` 到达 parser 的形态是 KEYWORD('引') + IDENTIFIER('数学') +
        # PERIOD；而写成 `引 Python:` 的合法嵌入块会被词法器整块吃掉成一个
        # EMBED_BLOCK token（上面 :190 那条分支处理），根本不会走到这里。
        if tok.type == TokenType.KEYWORD and tok.value == '引':
            return self._parse_import_stmt()

        # 从...导入语句：从
        if tok.type == TokenType.KEYWORD and tok.value == '从':
            return self._parse_from_import_stmt()
        
        # 导出语句：导出 / 出
        if tok.type == TokenType.KEYWORD and tok.value in ('导出', '出'):
            return self._parse_export_stmt()
        
        # 变量声明：定义
        if tok.type == TokenType.KEYWORD and tok.value == '定义':
            return self._parse_var_decl()
        
        # 常量修饰符前缀：常 设 名 为 值。（v7 单 33）
        # `常量` 是等义双字写法。必须排在 '设' 分支之前。
        if tok.type == TokenType.KEYWORD and tok.value in ('常', '常量'):
            return self._parse_const_modifier()

        # 变量声明：设...为...
        if tok.type == TokenType.KEYWORD and tok.value == '设':
            return self._parse_set_stmt()
        
        # C风格变量声明：令 name = expr
        if tok.type == TokenType.IDENTIFIER and tok.value == '令':
            return self._parse_c_var_decl()
        
        # C风格函数定义：函数 name(params){body}
        # 仅当函数后跟标识符时才作为函数定义
        if tok.type == TokenType.IDENTIFIER and tok.value == '函数' and self._peek(1) and self._peek(1).type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            return self._parse_c_function()
        
        # C风格for循环：循环(init;cond;incr){body}
        # 仅当循环后跟(时才作为C风格for循环，否则可能是不含(的标识符部分（如"继续循环"）
        if tok.type == TokenType.IDENTIFIER and tok.value == '循环' and self._peek(1) and self._peek(1).type == TokenType.LPAREN:
            return self._parse_c_for_loop()
        
        # 裸花括号代码块：{ stmts }
        if tok.type == TokenType.LBRACE:
            body = self._parse_brace_body()
            return Block(body)
        
        # 条件语句：如果 / 若
        if tok.type == TokenType.KEYWORD and tok.value in ('如果', '若'):
            return self._parse_if_stmt()
        
        # 遍历循环：遍历 / 遍
        if tok.type == TokenType.KEYWORD and tok.value in ('遍历', '遍'):
            return self._parse_foreach_stmt()

        # C3-6：`对于 … 在 …` 遍历写法（含 `对于 每个 X 在 [...]`）。
        # 判定：文档从未承诺过这种写法（口径 9）。`对于` 在词法上不是关键字，
        # 被切成 `对`(IDENTIFIER) + `于`(KEYWORD)，于是旧行为一路掉进表达式解析、
        # 在冒号处报「无法识别的语法元素：'：'」，把用户往错误方向引。
        # 这里识别出「对 + 于」这个 `对于` 的忠实切法，直接给指路文案。
        # 只看这两个 token，绝不碰词法层（`对`/`于` 仍是单字，见
        # tests/unit/test_lexer_compound_safe_alignment.py::TestDropSignaturesFixed::test_对于）。
        if tok.type == TokenType.IDENTIFIER and tok.value == '对':
            nxt = self._peek(1)
            if nxt is not None and nxt.type == TokenType.KEYWORD and nxt.value == '于':
                self._error(
                    "「对于 … 在 …」不是光明支持的遍历写法。"
                    "光明遍历循环的写法是「遍历 X 于 表：」，例如：遍历 项 于 列表：。"
                    "另注意：推导式（列表/字典）的介词是「之/在」，"
                    "遍历语句的介词是「于」，两者不要混用。",
                    tok.line, tok.col, tok.value
                )
        
        # 当循环：当
        if tok.type == TokenType.KEYWORD and tok.value == '当':
            return self._parse_while_stmt()
        
        # 返回语句：返回 / 返
        if tok.type == TokenType.KEYWORD and tok.value in ('返回', '返'):
            return self._parse_return_stmt()
        
        # 跳出语句：跳出 / 跳 / 断（v7 单 31-A：'断' 是 L0 冻结表承诺的 break 别名）
        if tok.type == TokenType.KEYWORD and tok.value in ('跳出', '跳', '断'):
            self._consume(TokenType.KEYWORD, tok.value)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return BreakStmt()

        # 跳过语句：跳过 / 过 / 继续 / 跃（v7 单 31-A：'跃' 是 L0 承诺的 continue 别名）
        if tok.type == TokenType.KEYWORD and tok.value in ('跳过', '过', '继续', '跃'):
            self._consume(TokenType.KEYWORD, tok.value)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return ContinueStmt()
        
        # 空语句：pass（Python兼容）
        if tok.type == TokenType.IDENTIFIER and tok.value == 'pass':
            self._consume(TokenType.IDENTIFIER)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return PassStmt()
        
        # 类型检查开关：开启类型检查 / 关闭类型检查
        if tok.type == TokenType.KEYWORD and tok.value in ('开启', '关闭'):
            next_tok = self._peek(1)
            if next_tok and (next_tok.value == '类型' or next_tok.value == '类型检查'):
                # 支持 "开启 类型检查" 和 "开启类型检查" 两种写法
                if next_tok.value == '类型检查':
                    # "类型检查" 作为一个整体标识符
                    enable = tok.value == '开启'
                    line, col = tok.line, tok.col
                    self._consume(TokenType.KEYWORD)  # 开启/关闭
                    self._consume()  # 类型检查（IDENTIFIER）
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    return TypeCheckToggleStmt(enable, line, col)
                else:
                    next_next = self._peek(2)
                    if next_next and next_next.value == '检查':
                        enable = tok.value == '开启'
                        line, col = tok.line, tok.col
                        self._consume(TokenType.KEYWORD)  # 开启/关闭
                        self._consume(TokenType.KEYWORD)  # 类型
                        self._consume()  # 检查（可能是 IDENTIFIER）
                        if self._current() and self._current().type == TokenType.PERIOD:
                            self._consume(TokenType.PERIOD)
                        return TypeCheckToggleStmt(enable, line, col)
        
        # 异常捕获：尝试 / 试
        if tok.type == TokenType.KEYWORD and tok.value in ('尝试', '试'):
            return self._parse_try_stmt()
        
        # 抛出异常：抛出 / 抛 / 掷（v7 单 26：'掷' 是文档承诺的别名，见 keywords.py）
        if tok.type == TokenType.KEYWORD and tok.value in ('抛出', '抛', '掷'):
            return self._parse_throw_stmt()
        
        # B5：推迟语句（defer）—— 推迟 体在作用域退出时执行（FILO 栈序）
        if tok.type == TokenType.KEYWORD and tok.value == '推迟':
            return self._parse_defer_stmt()

        
        # 生成器/生成语句：生成 表达式
        if tok.type == TokenType.KEYWORD and tok.value == '生成':
            return self._parse_yield_stmt()
        
        # 异步相关：异步 段落 / 异步作用域 / 异步 遍历 / 等待
        # （`异` 是 v7 单 31-G 补的 L0 单字别名，与 `异步` 等价；`等` 见单 31-C）
        if tok.type == TokenType.KEYWORD and tok.value in ('异步', '异'):
            # 查看下一个 token 判断是异步段落还是异步作用域还是异步遍历
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('函数', '段落', '段'):
                # 异步段落：异步 函数/段落/段 段名 ...
                return self._parse_async_paragraph()
            elif next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value == '作用域':
                # 异步作用域：异步作用域 ...
                return self._parse_async_scope()
            elif next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('遍历', '遍'):
                # 异步遍历：异步 遍历 变量 于 可迭代对象
                self._consume(TokenType.KEYWORD)  # 异步 / 异
                return self._parse_foreach_stmt(is_async=True)
            elif next_tok and next_tok.value == '运行':
                # A1 异步启动入口：异步 运行 主()。 → asyncio.run(主())
                return self._parse_run_async_stmt()

            else:

                # 默认为异步段落（向前兼容）
                return self._parse_async_paragraph()
        
        # 严格段落：严格 段落 段名 ...
        if tok.type == TokenType.KEYWORD and tok.value == '严格':
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('函数', '段落', '段'):
                return self._parse_strict_paragraph()
            # 否则作为普通标识符处理（严格可能作为变量名）
        
        # 松散段落：松散 段落 段名 ...（显式声明为松散模式）
        if tok.type == TokenType.KEYWORD and tok.value == '松散':
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('函数', '段落', '段'):
                self._consume(TokenType.KEYWORD, '松散')
                para = self._parse_paragraph_v2()
                if '松散' not in para.modifiers:
                    para.modifiers = list(para.modifiers) + ['松散']
                return para
            # 否则作为普通标识符处理
        
        # 等待表达式作为语句：等待 异步调用。（`等` 是 v7 单 31-C 补的 L0 单字别名）
        if tok.type == TokenType.KEYWORD and tok.value in ('等待', '等'):
            return self._parse_expr_stmt()

        
        # 段落定义：函数/段落/段 段名 接收 参数
        # 注意：段落调用（段落段名(参数)）由表达式解析器处理
        if tok.type == TokenType.KEYWORD and tok.value in ('函数', '段落', '段'):
            # 检查后面是否是段名后跟括号
            next_tok = self._peek(1)
            second_tok = self._peek(2)
            if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) \
                    and second_tok and second_tok.type == TokenType.LPAREN:
                # 向前扫描：找到匹配的 ) 后，如果紧跟 : 则是段落定义，否则是段落调用
                if self._is_paragraph_definition():
                    return self._parse_paragraph_v2()
                # 这是段落调用，作为表达式语句处理
                return self._parse_expr_stmt()
            # 否则作为段落定义处理
            return self._parse_paragraph_v2()
        
        # 类定义：类 类名
        if tok.type == TokenType.KEYWORD and tok.value == '类':
            return self._parse_class_definition()

        # 接口定义：接口 / 接 / 协议 接口名
        if tok.type == TokenType.KEYWORD and tok.value in ('接口', '接', '协议'):
            return self._parse_interface_definition()

        # 接口定义单字别名 `约`（v7 单 31-F，L0 冻结表 docs/language/l0-core.md:57）。
        #
        # 走「范式 A」：判 **IDENTIFIER 而非 KEYWORD**，词法层与关键字表零改动。
        # 先例是单 31-C 的 `私`/`护`/`静`（见 :3917 起那段注释）。之所以不进
        # `ALL_KEYWORDS`：`约` 是高频构词字（全仓代码侧词内 198 处，最大公约数/归约/
        # 违约金/约束…），进表就得在词法层动最长匹配，风险远大于收益。
        #
        # **必须带前视守卫**，不能只判「裸 IDENTIFIER 是 `约`」：`约 等于 1。` 这种
        # 以 `约` 为变量名的赋值语句今天是合法的（落到 :535 的赋值分支），无条件抢过来
        # 会把能跑的代码改坏。守卫取「本行内出现冒号」——即文档承诺的 `约 名：` 形态；
        # 该形态今天**一律硬报错**（实测与从不进任何关键字表的对照字 `鱼` 报错逐字相同，
        # 见工单 31-E），所以新增分支只可能把「原本报错」变成「能解析」。
        if (tok.type == TokenType.IDENTIFIER and tok.value == '约'
                and self._is_interface_char_header()):
            return self._parse_interface_definition()

        # 模式匹配：匹配 / 配 / 匹（v7 单 27：'匹' 是 L0 冻结表承诺的别名）
        if tok.type == TokenType.KEYWORD and tok.value in ('匹配', '配', '匹'):
            return self._parse_match_stmt()

        # 上下文管理器：使用
        if tok.type == TokenType.KEYWORD and tok.value == '使用':
            return self._parse_with_stmt()

        # C FFI：外部 段落 ...
        if tok.type == TokenType.KEYWORD and tok.value == '外部':
            return self._parse_ffi_decl()

        # C FFI：加载库 ...
        if tok.type == TokenType.KEYWORD and tok.value == '加载库':
            return self._parse_ffi_load_library()

        # @C FFI标记（独立语法标记，非装饰器）
        if tok.type == TokenType.AT and self._peek(1) and \
           self._peek(1).type == TokenType.IDENTIFIER and self._peek(1).value == 'C':
            self._consume(TokenType.AT)  # 消耗 @
            self._consume()  # 消耗 C
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value == '加载库':
                return self._parse_ffi_load_library()
            return self._parse_ffi_decl(from_at_c=True)

        # 类型别名定义：类型 别名 = 类型定义
        if tok.type == TokenType.KEYWORD and tok.value == '类型':
            return self._parse_type_alias()

        # 动词调用作为独立语句
        if tok.type == TokenType.KEYWORD and tok.value in VERB_ARITY:
            return self._parse_expr_stmt()
        
        # stdlib 函数调用作为独立语句（不再是 KEYWORD，走 IDENTIFIER 路径）
        if tok.type == TokenType.IDENTIFIER and tok.value in STDLIB_VERB_ARITY:
            return self._parse_expr_stmt()
        
        # self赋值语句：己/自 属性名 为 值
        if tok.type == TokenType.KEYWORD and tok.value in ('己', '自'):
            return self._parse_self_assignment()

        # super调用：父.方法名(参数)
        if tok.type == TokenType.KEYWORD and tok.value == '父':
            return self._parse_expr_stmt()

        # 裸字符串语句（docstring）："""...""" 或 "..." 单独成行。
        #
        # Bug 根因：_parse_statement 原先没有任何 STRING 分支，裸字符串作为独立
        # 语句时直接落入末尾的"无法识别的语法元素"报错分支；而词法器此前还会把
        # """...""" 拆成三个 STRING token（见 lexer.py _tokenize_string 的修复），
        # 首 token 为空字符串，报错信息形如「无法识别的语法元素：''」。
        # 这导致 bootstrap_eval.light / bootstrap_lexer.light 中函数体首行的
        # """文档字符串""" 无法解析。
        #
        # 修复方案（配合词法器三引号修复）：此处将 STRING 作为表达式语句解析，
        # codegen 输出 Python 字符串语句——Python 会把函数/类/模块体首行的字符串
        # 视为 docstring，其余位置的裸字符串为无操作表达式，与 Python 语义一致。
        # 对应 codegen 分支见 code_generator.py _generate_statement 的 StringLiteral 分支。
        if tok.type == TokenType.STRING:
            return self._parse_expr_stmt()

        # 装饰器：@段落名 标注 段落 ...（支持装饰器链）
        if tok.type == TokenType.AT:
            saved_pos = self.pos
            # 收集所有 @decorator 行
            decorators = []
            custom_decorator_seen = False
            while self._current() and self._current().type == TokenType.AT:
                # 检测是否是 @C（FFI标记，非装饰器）
                peek = self._peek(1)
                if peek and peek.type == TokenType.IDENTIFIER and peek.value == 'C':
                    # 这是 @C FFI，不是装饰器
                    # 如果已经收集了装饰器，回退并报错
                    if decorators:
                        self._error("装饰器不能与 @C FFI 标记混用")
                    break
                decorator_info = self._parse_decorator_info()
                if decorator_info:
                    # 检查是否是内置装饰器
                    if decorator_info.name in ('静态方法', '类方法', '特性', '抽象'):
                        # 内置装饰器后必须紧跟函数定义，不能有多个装饰器
                        if decorators:
                            self._error(f"内置装饰器 @{decorator_info.name} 不能与其他装饰器链式使用")
                        # 回退，使用原有的 _parse_decorator 处理
                        self.pos = saved_pos
                        return self._parse_decorator()
                    decorators.append(decorator_info)
                    custom_decorator_seen = True
                # 跳过装饰器后的 NEWLINE
                while self._match(TokenType.NEWLINE):
                    self._consume(TokenType.NEWLINE)
                # 跳过 INDENT（如果装饰器后有缩进）
                while self._match(TokenType.INDENT):
                    self._consume(TokenType.INDENT)
            
            if not decorators:
                self._error("期望装饰器名")
            
            # 跳过 NEWLINE
            while self._match(TokenType.NEWLINE):
                self._consume(TokenType.NEWLINE)
            # 跳过 INDENT
            while self._match(TokenType.INDENT):
                self._consume(TokenType.INDENT)
            
            # 标注（可选关键字）
            if self._match(TokenType.KEYWORD, '标注'):
                self._consume(TokenType.KEYWORD, '标注')
                while self._match(TokenType.NEWLINE):
                    self._consume(TokenType.NEWLINE)
                while self._match(TokenType.INDENT):
                    self._consume(TokenType.INDENT)
            
            # 解析被装饰的函数定义
            paragraph = None
            if self._match(TokenType.LBOOK):
                # 《段名》段 语法
                self._consume(TokenType.LBOOK)
                name_tok = self._current()
                if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    name = self._consume().value
                    if self._match(TokenType.RBOOK):
                        self._consume(TokenType.RBOOK)
                        if self._match(TokenType.KEYWORD, '段') or self._match(TokenType.KEYWORD, '函数') or self._match(TokenType.KEYWORD, '段落'):
                            self._consume()
                            paragraph = self._parse_paragraph_v2(name=name)
                        else:
                            tok = self._current()
                            self._error(f"期望 '段' 关键字，但得到 {tok.value if tok else '输入结束'}")
                    else:
                        tok = self._current()
                        self._error(f"期望 '》'，但得到 {tok.value if tok else '输入结束'}")
                else:
                    tok = self._current()
                    self._error(f"期望段名，但得到 {tok.type if tok else '输入结束'}")
            elif self._match(TokenType.KEYWORD, '函数') or self._match(TokenType.KEYWORD, '段落'):
                paragraph = self._parse_paragraph_v2()
            elif self._match(TokenType.KEYWORD, '构造'):
                paragraph = self._parse_method_definition(is_constructor=True)
            else:
                tok = self._current()
                self._error(f"装饰器后必须跟函数定义（'函数 段名' 或 '《段名》段'），但得到 {tok.value if tok else '输入结束'}")
            
            return DecoratedFunction(decorators, paragraph)
        
        # 明确标注不支持的特性（P1-3）：async / await 关键字
        if tok.type == TokenType.IDENTIFIER and tok.value == 'async':
            self._error(
                "光明不支持 'async' 关键字。请使用「异步」替代，例如：异步 段落 段名()。",
                tok.line, tok.col
            )
        if tok.type == TokenType.IDENTIFIER and tok.value == 'await':
            self._error(
                "光明不支持 'await' 关键字。请使用「等待」替代，例如：等待 异步调用()。",
                tok.line, tok.col
            )
        
        # 断言语句：断言 <条件>，<可选消息>。
        if tok.type == TokenType.IDENTIFIER and tok.value == '断言':
            return self._parse_assert_stmt()

        # A5 作用域声明：全局 名。/ 外层 名。（范式 A：词法零改动，见
        # _is_scope_decl_header 的判据说明）
        # A2-2：判据不能只看单 token——`外` 一旦成为本文件的段落名，`外层` 会被
        # 切成 `外` + `层` 两个 IDENTIFIER，旧判据直接漏掉、静默编成 `外层(计数)`。
        scope_span = self._scope_decl_word_span()
        if scope_span is not None:
            scope_word, scope_tokens = scope_span
            if self._is_scope_decl_header(scope_tokens):
                return self._parse_scope_decl_stmt(scope_word, scope_tokens)



        # 赋值语句：标识符 等于 值。
        if tok.type == TokenType.IDENTIFIER:
            return self._parse_assignment_stmt()

        # 书名号（《）作为段落定义或表达式语句
        if tok.type == TokenType.LBOOK:
            saved_pos = self.pos
            self._consume(TokenType.LBOOK)
            name_tok = self._current()
            if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                name = self._consume().value
                if self._match(TokenType.RBOOK):
                    self._consume(TokenType.RBOOK)
                    # 检查后面是否是 段、函数 或 段落（段落定义关键字）
                    if self._match(TokenType.KEYWORD, '段') or self._match(TokenType.KEYWORD, '函数') or self._match(TokenType.KEYWORD, '段落'):
                        self._consume()  # 消耗 段/函数/段落
                        return self._parse_paragraph_v2(name=name)
            # 回退并作为表达式语句处理
            self.pos = saved_pos
            return self._parse_expr_stmt()

        # 未知语法：报错而非静默失败
        # 根据当前 token 类型给出更有针对性的提示
        if tok.type == TokenType.KEYWORD:
            self._error(
                f"「{tok.value}」是保留关键字，不能直接作为语句开头。"
                f"请检查语法是否正确，或参考光明语法文档。",
                tok.line, tok.col, tok.value
            )
        elif tok.type == TokenType.EQUALS:
            self._error(
                f"赋值需要使用「设」或「令」关键字。如：设 甲 为 10。或：令 甲 = 10。",
                tok.line, tok.col, tok.value
            )
        elif tok.type in (TokenType.INDENT, TokenType.DEDENT):
            # INDENT/DEDENT 的 value 是缩进宽度整数，直接塞进 '{tok.value}' 会打出
            # 「无法识别的语法元素：'4'」这种误导信息（把内部计数当成源码片段）。
            # 走到这里说明缩进没对齐到任何语句块，改报缩进问题本身。
            self._error(
                "缩进不正确：这一行的缩进层级没有对应的语句块。"
                "请检查上一条语句是否以「：」结尾、或本行缩进是否多/少了一级。",
                tok.line, tok.col, tok.value
            )
        else:
            self._error(
                f"无法识别的语法元素：'{tok.value}'。"
                f"请检查语句是否正确，或参考光明语法文档。",
                tok.line, tok.col, tok.value
            )

    def _parse_assert_stmt(self) -> ASTNode:
        """解析断言语句：断言 <条件>，<可选消息>。
        
        语法：
            断言 <条件表达式>。
            断言 <条件表达式>，<消息表达式>。
        
        示例：
            断言 结果 等于 42。
            断言 字符串包含(结果, "测试")，"问候语应包含名称"。
        
        注意：使用 _parse_logical_expr 而非 _parse_expr 解析条件，
        因为 _parse_expr 会把逗号（，）当作管道操作符，导致消息
        被错误地解析为管道链的一部分。
        """
        from ast_nodes_v3 import AssertStmt
        
        # 消耗 断言
        self._consume(TokenType.IDENTIFIER, '断言')
        
        # 解析条件表达式（使用 _parse_logical_expr 避免逗号被当作管道）
        condition = self._parse_logical_expr()
        
        # 检查是否有逗号（，或,）分隔的消息
        message = None
        if self._current() and self._current().type == TokenType.COMMA:
            self._consume(TokenType.COMMA)
            message = self._parse_expr()
        
        # 消耗句号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return AssertStmt(condition, message)

    # A5：`全局` / `外层` 对应的 Python 作用域声明关键字
    _SCOPE_DECL_WORDS = {'全局': 'global', '外层': 'nonlocal'}

    # A2-2：这两个词都是双字，被切开最多两个 token；留 1 个余量防单字再拆
    _SCOPE_DECL_MAX_TOKENS = 3

    def _scope_decl_word_span(self):
        """当前位置是否拼出一个作用域声明词；返回 (词, 占用 token 数) 或 None。

        为什么不能只比单个 token 的 value（A2-2 的根因）：光明的分词是上下文相关的。
        文件里只要出现过 `段落 外(...)`，`外` 就被登记成定义名，于是同一文件里的
        `外层 计数。` 会被切成 `IDENTIFIER '外'` + `IDENTIFIER '层'`——旧判据不命中，
        语句被当成并置调用静默编成 `外层(计数)`，编译期零提示、运行期 NameError，
        跟修单前一模一样。孤立写法能切成单 token，所以常规用例照不出来。

        为什么这条路不会反过来打破「`外` 作段落名」的现有用例：拼接只在**源码里
        字面相邻**时才做（同一行、后一个 token 的列号正好等于前一个的列号 + 字符数），
        并且拼出来的整体必须**逐字等于** `全局`/`外层`。因此
          · `外()。`     → 下一个 token 是 LPAREN，不是 IDENTIFIER，不拼；
          · `外 为 1。`  → 下一个是 KEYWORD `为`，不拼；
          · `外 层()`    → 拼成 `外层`，但 _is_scope_decl_header 见到 LPAREN 返回 False；
          · `全局搜索搜索(甲)` → 首 token 已等于 `全局`，走单 token 分支，同样被
            header 判据挡在 LPAREN 上。
        三处现有用例（templates/data_analysis/分析.light 的 `外层 = 外层 + 1`、
        段落名 `外`、函数名 `全局搜索搜索`）都落在返回 None / header 判 False 一侧。
        """
        tok = self._current()
        if tok is None or tok.type != TokenType.IDENTIFIER or not isinstance(tok.value, str):
            return None
        if tok.value in self._SCOPE_DECL_WORDS:
            return tok.value, 1
        text = tok.value
        if not any(w.startswith(text) for w in self._SCOPE_DECL_WORDS):
            return None
        prev = tok
        idx = self.pos + 1
        used = 1
        while idx < len(self.tokens) and used < self._SCOPE_DECL_MAX_TOKENS:
            t = self.tokens[idx]
            if t.type != TokenType.IDENTIFIER or not isinstance(t.value, str):
                return None
            if t.line != prev.line or t.col != prev.col + len(str(prev.value)):
                return None  # 中间有空白或别的字符：这是两个词，不是一个词被切开
            text += t.value
            used += 1
            if text in self._SCOPE_DECL_WORDS:
                return text, used
            if not any(w.startswith(text) for w in self._SCOPE_DECL_WORDS):
                return None
            prev = t
            idx += 1
        return None

    def _is_scope_decl_header(self, word_tokens: int = 1) -> bool:
        """前视：当前的裸 `全局` / `外层` 是否是作用域声明头。

        `word_tokens` 是声明词自身占用的 token 数（分词可能把双字词切成两个）。

        判据是严格形态 `全局 名[，名]*。`——`全局` 之后只能是标识符与逗号，
        直到句号/换行/EOF 为止。为什么要卡这么死（范式 A 的成立前提）：

        · 今天 `全局 计数。` 被当成并置式调用编成 `全局(计数)`，运行期 NameError，
          即这个形态的输入集合与「原本能跑的程序」不相交（实测产物见工单 A5）。
        · 反过来 `全局 = 1。`（EQUALS）、`全局(甲)`（LPAREN）、`全局 等于 1。`
          （KEYWORD）这些今天合法的写法一律返回 False，原样走赋值/表达式分支。
          src/templates/data_analysis/分析.light:103 的 `外层 = 外层 + 1` 就落在
          这一侧，所以那个文件逐字不变。

        选范式 A（词法零改动）而不是把两词加进关键字表，是因为实测加表会连带
        两处回归：`全局搜索搜索` 在没有声明的调用位置被切成 `全局`+`搜索搜索`；
        `外层 = 外层 + 1` 因 parser_stmt.py:578 的赋值分支只认 IDENTIFIER 而
        直接报「「外层」是保留关键字」。
        """
        idx = self.pos + word_tokens  # 跳过 `全局` / `外层` 自身（可能占多个 token）

        expect_name = True
        seen_name = False
        while idx < len(self.tokens):
            t = self.tokens[idx]
            if expect_name:
                if t.type != TokenType.IDENTIFIER:
                    return False
                seen_name = True
                expect_name = False
            else:
                if t.type == TokenType.COMMA:
                    expect_name = True
                elif t.type in (TokenType.PERIOD, TokenType.NEWLINE, TokenType.EOF):
                    return seen_name
                else:
                    return False
            idx += 1
        return False

    def _parse_scope_decl_stmt(self, word: str = None, word_tokens: int = 1) -> ASTNode:
        """解析作用域声明：全局 计数。/ 外层 值, 次数。

        `word` / `word_tokens` 由 _scope_decl_word_span 给出：分词可能把 `外层`
        切成两个 token，这里要把它们全部吃掉再读名字列表。
        """
        from ast_nodes_v3 import ScopeDeclStmt

        first_tok = self._consume(TokenType.IDENTIFIER)
        for _ in range(word_tokens - 1):
            self._consume(TokenType.IDENTIFIER)
        if word is None:
            word = first_tok.value
        kind = self._SCOPE_DECL_WORDS[word]


        names = [self._consume(TokenType.IDENTIFIER).value]
        while self._current() and self._current().type == TokenType.COMMA:
            self._consume(TokenType.COMMA)
            names.append(self._consume(TokenType.IDENTIFIER).value)

        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        return ScopeDeclStmt(names, kind)

    def _parse_expr_stmt(self) -> ASTNode:
        """解析表达式语句（动词调用等）"""
        expr = self._parse_expr()
        # 消耗句号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        return expr
    
    def _parse_embed_block(self) -> ASTNode:
        """解析嵌入块语句
        
        语法：嵌入 Python: ... 结束嵌入
             嵌入 C: ... 结束嵌入
        
        lexer 已将整个嵌入块识别为单个 EMBED_BLOCK token，
        token.value 为 (language, code) 元组。
        """
        tok = self._consume(TokenType.EMBED_BLOCK)
        language, code = tok.value
        # 消耗可能的句号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        return EmbedBlock(
            language=language,
            code=code,
            line=tok.line,
            col=tok.col
        )

    
    def _parse_self_assignment(self) -> ASTNode:
        """解析self赋值语句或属性赋值语句
        
        语法1（方法内部）：己属性名 为 值。
        生成：SelfAssignment(attr_name, value)
        
        语法2（设置对象属性）：己 obj.attr 为 值。
        生成：Assignment(target=MemberAccess(obj, attr), value)
        
        语法3（self属性赋值）：己.属性名 为 值。
        生成：Assignment(target=Identifier("self.属性名"), value)
        """
        # 保存当前位置（在消耗己之前），用于回溯
        saved_pos_before_ji = self.pos
        
        # 己 / 自
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 保存当前位置（在消耗己之后），用于回退到无点号情况
        saved_pos = self.pos
        
        # 先检查：己.属性名 = value 语法（己后直接跟成员访问符 . / 之 / 的）
        #
        # Bug 根因：原先只认 DOT。`自之成绩[科目] = 分数`
        # （examples/L2_wenyan/学生模块.light:35）在 `自` 之后是 KEYWORD `之`，
        # 于是掉到下面「原来的 SelfAssignment 处理逻辑」，那段把 `之` 当成属性名的
        # 第一个字拼进去（得到 self.之成绩，实测 `自之成绩 = {}` → `self.之成绩 = {}`
        # 是静默错译），而且它不认索引后缀，`[` 直接报「期望'为'或'等于'」。
        # 这里把 `之`/`的` 与 DOT 等同看待，交给下面这条早已支持链式访问 + 索引后缀
        # 的成熟路径。对照：`己.成绩[科目] = 分数` 一直是对的。
        if self._current() and (
                self._current().type == TokenType.DOT
                or (self._current().type == TokenType.KEYWORD
                    and self._current().value in ('之', '的'))):
            # 这是 己.属性名 = value 语法 或 己.方法名() 方法调用
            # 手动解析 己.属性名，避免 _parse_expr 把后续运算符也消耗掉
            self._consume()  # 消耗成员访问符 . / 之 / 的

            
            # 获取属性名
            attr_tok = self._current()
            if attr_tok and attr_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                attr_name = attr_tok.value
                self._consume()
            else:
                return self._error(f"己引用后应跟属性名",
                                 attr_tok.line if attr_tok else 0, attr_tok.col if attr_tok else 0)
            
            # 构建 target_expr = MemberAccess(Identifier("self"), attr_name)
            from ast_nodes_v3 import MemberAccess
            target_expr = MemberAccess(Identifier("self"), attr_name, False, [])
            
            # 深层链式访问：己.data.value 或 己.cache["key"] 或 自之成绩[科目]
            # 继续解析后续的 .属性 / 之属性 / 的属性 和 [索引] 链
            while self._current():
                if (self._current().type == TokenType.DOT
                        or (self._current().type == TokenType.KEYWORD
                            and self._current().value in ('之', '的'))):
                    self._consume()  # 消耗成员访问符 . / 之 / 的
                    member_tok = self._current()

                    if member_tok and member_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        member_name = member_tok.value
                        self._consume()
                        target_expr = MemberAccess(target_expr, member_name, False, [])
                        continue
                    else:
                        break
                elif self._current().type == TokenType.LBRACKET:
                    self._consume(TokenType.LBRACKET)
                    # 同上：不要在函数内 import IndexAccess，第 17 行已 import *。
                    index = self._parse_expr()
                    self._consume(TokenType.RBRACKET)
                    target_expr = IndexAccess(target_expr, index)
                    continue
                else:
                    break
            
            # 检查是否是赋值
            assign_op = None
            compound_ops = {
                '加上': '+=', '减去': '-=', '乘以': '*=', '除以': '/=',
                '整除': '//=', '模以': '%=', '幂以': '**=',
            }
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
                assign_op = '为'
            elif self._match(TokenType.KEYWORD, '等于'):
                self._consume(TokenType.KEYWORD, '等于')
                assign_op = '等于'
            elif self._match(TokenType.EQUALS):
                self._consume(TokenType.EQUALS)
                assign_op = '='
            elif self._current() and self._current().type == TokenType.KEYWORD and self._current().value in compound_ops:
                op_text = self._consume().value
                assign_op = compound_ops[op_text]
            
            if assign_op:
                # 赋值语句
                value = self._parse_expr()
                
                # 句号（可选）
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                
                if assign_op in ('+=', '-=', '*=', '/=', '%=', '**='):
                    # 复合赋值：target op= value → target = target op value
                    from ast_nodes_v3 import BinaryOp
                    bin_op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/', '%=': '%', '**=': '**'}
                    bin_expr = BinaryOp(bin_op_map[assign_op], target_expr, value)
                    return Assignment(target_expr, bin_expr)
                
                # 返回赋值节点（target 是属性访问表达式）
                return Assignment(target_expr, value)
            else:
                # 不是赋值——回退到己之前，用完整表达式解析器处理整个链式调用
                # （如 己.history.append(内容) 需要被完整解析为 MemberAccess 链）
                self.pos = saved_pos_before_ji
                return self._parse_expr_stmt()
        
        # 先尝试解析一个表达式，看看是不是属性访问
        # 我们先尝试解析标识符，然后看看后面有没有点号
        if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            first_ident = self._consume()
            # 看看后面是不是点号
            if self._current() and self._current().type == TokenType.DOT:
                # 这是属性访问：己.属性名 = value 或 己 obj.attr = value
                # 回退到己之前，用表达式解析器来解析
                self.pos = saved_pos_before_ji
                target_expr = self._parse_expr()
                
                # 为
                if self._match(TokenType.KEYWORD, '为'):
                    self._consume(TokenType.KEYWORD, '为')
                elif self._match(TokenType.KEYWORD, '等于'):
                    self._consume(TokenType.KEYWORD, '等于')
                elif self._match(TokenType.EQUALS):
                    self._consume(TokenType.EQUALS)
                else:
                    tok = self._current()
                    self._error(f"期望'为'或'等于'，但得到 {tok.type} = '{tok.value}'", tok.line, tok.col)
                
                # 值
                value = self._parse_expr()
                
                # 句号（可选）
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                
                # 返回赋值节点（target 是属性访问表达式）
                return Assignment(target_expr, value)
            else:
                # 不是属性访问，回退，按原来的 SelfAssignment 处理
                self.pos = saved_pos
        
        # 原来的 SelfAssignment 处理逻辑
        # 属性名（可能以"己"开头，但已经被消费了）
        # 这里属性名可能是单个标识符，也可能带类型等
        attr_name_tokens = []
        
        # 收集属性名，直到遇到"为"或"等于"关键字
        while self._current():
            tok = self._current()

            if tok.type == TokenType.KEYWORD and tok.value in ('为', '等于'):
                break

            if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                attr_name_tokens.append(tok.value)
                self._consume()
            else:
                break
        
        # 拼接属性名（处理"己名称"这种"己"+"名称"的情况）
        attr_name = ''.join(attr_name_tokens)
        
        # 为
        tok = self._current()
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
        elif self._match(TokenType.KEYWORD, '等于'):
            self._consume(TokenType.KEYWORD, '等于')
        elif self._match(TokenType.EQUALS):
            self._consume(TokenType.EQUALS)
        else:
            # 兼容其他赋值操作符
            self._error(f"期望'为'或'等于'，但得到 {tok.type} = '{tok.value}'", tok.line, tok.col)
        
        # 值
        value = self._parse_expr()
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 创建赋值节点（self.attr_name = value）
        return SelfAssignment(attr_name, value)
    
    def _parse_assignment_stmt(self) -> ASTNode:
        """解析赋值语句：标识符 等于 值。或 标识符 加上/减去/乘以/除以 值。
        
        支持以下形式：
        - 标识符 等于/为/= 值
        - 标识符 加上/减去/乘以/除以 值（复合赋值）
        - 标识符[索引] 等于/为/= 值（索引赋值）
        - obj.attr 等于/为/= 值（属性赋值，v3.4 新增）
        """
        # 复合赋值运算符映射
        compound_ops = {
            '加上': '加',
            '减去': '减',
            '乘以': '乘',
            '除以': '除',
            '模以': '模',
            '幂以': '幂',
        }
        
        # 保存初始位置用于完整回退
        saved_pos = self.pos
        
        # 标识符
        name_tok = self._consume(TokenType.IDENTIFIER)
        name = name_tok.value
        
        # 检查属性赋值：obj.attr / obj之attr / obj的attr 等于/为/= 值（v3.4 新增）
        # 支持链式：obj.a.b.c = value
        #
        # 中文成员访问符也要认：parser_expr.py:2428-2431 已明确「的」是光明原生
        # 属性访问符、「.」留给 FFI/外部库，「之」是历史写法。原先这里只认 DOT，
        # 于是 `自之姓名 = 姓名`（examples/L2_wenyan/学生模块.light:15）在 `自`
        # 之后遇到 KEYWORD `之` 就掉出赋值分支、回退成表达式语句，把 `自之姓名`
        # 读完后 `=` 落到语句层，报「赋值需要使用「设」或「令」关键字」。
        # 对照：`己.姓名 = 姓名`（DOT）与 `设 自之姓名 为 姓名`（走 设 语句）都通。
        #
        # 判据仍是纯语法且完全可回退：收完目标链之后必须紧跟 等于/为/=，
        # 否则整段回退到标识符之前交给 _parse_expr_stmt()——所以
        # `s1之录入成绩("语文", 88)` 这类方法调用语句逐字不变。
        if self._current() and (
                self._current().type == TokenType.DOT
                or (self._current().type == TokenType.KEYWORD
                    and self._current().value in ('之', '的'))):
            # 构建链式成员访问目标
            target = Identifier(name)
            while self._current() and (
                    self._current().type == TokenType.DOT
                    or (self._current().type == TokenType.KEYWORD
                        and self._current().value in ('之', '的'))):
                self._consume()  # 成员访问符：. / 之 / 的
                attr_tok = self._current()
                if attr_tok and attr_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    attr_name = self._consume().value
                    target = MemberAccess(target, attr_name)
                else:
                    # 属性名不是有效的标识符/关键字，回退
                    self.pos = saved_pos
                    return self._parse_expr_stmt()

            # 成员链之后的索引后缀：`自之成绩[科目] = 分数`（学生模块.light:35）
            while self._current() and self._current().type == TokenType.LBRACKET:
                self._consume(TokenType.LBRACKET)
                idx_expr = self._parse_expr()
                self._consume(TokenType.RBRACKET)
                target = IndexAccess(target, idx_expr)

            # 检查等于/为/=
            if self._match(TokenType.KEYWORD, '等于') or self._match(TokenType.KEYWORD, '为') or self._match(TokenType.EQUALS):
                self._consume()
                value = self._parse_expr()
                # 句号（可选）
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                return Assignment(target, value)
            
            # 不是赋值，可能是表达式语句（如 obj.a.b()）
            self.pos = saved_pos
            return self._parse_expr_stmt()

        
        # 检查索引赋值：甲[丁] 为/等于 值。 或 甲[丁][戊] 为/等于 值。
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            index = self._parse_expr()
            self._consume(TokenType.RBRACKET)
            
            # 构建索引访问链：甲[丁][戊] → IndexAccess(IndexAccess(Identifier("甲"), 丁), 戊)
            # IndexAccess 走本文件第 17 行的 `from ast_nodes_v3 import *`。
            # 这里原先有一句函数内 `from ast_nodes_v3 import IndexAccess`，
            # 那会把 IndexAccess 变成整个 _parse_assignment_stmt 的局部名，于是
            # 上面第 894 行（成员链索引后缀，本轮新增）先执行时抛
            # UnboundLocalError，把本该是 ParseError 的诊断变成解析器内部崩溃
            # （实测样本 bootstrap/release/stdlib/对象池缓存.light）。已删除。
            target = IndexAccess(Identifier(name), index)
            while self._current() and self._current().type == TokenType.LBRACKET:
                self._consume(TokenType.LBRACKET)
                next_index = self._parse_expr()
                self._consume(TokenType.RBRACKET)
                target = IndexAccess(target, next_index)
            
            # 检查索引复合赋值：甲[丁] 加上 值。
            if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in compound_ops:
                op_text = self._current().value
                operator = compound_ops[op_text]
                self._consume(TokenType.KEYWORD, op_text)
                value = self._parse_expr()
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                return Assignment(target, BinaryOp(operator, target, value))
            
            # 检查等于/为/=
            if not self._match(TokenType.KEYWORD, '等于') and not self._match(TokenType.KEYWORD, '为') and not self._match(TokenType.EQUALS):
                # 不是赋值语句（如 graph[u].append(v)），完整回退到标识符之前
                self.pos = saved_pos
                return self._parse_expr_stmt()
            
            # 消耗等于/为/=
            self._consume()
            
            value = self._parse_expr()
            
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            
            return Assignment(target, value)
        
        # 检查复合赋值：甲 加上 1。
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in compound_ops:
            op_text = self._current().value
            operator = compound_ops[op_text]
            self._consume(TokenType.KEYWORD, op_text)
            
            # 值
            value = self._parse_expr()
            
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            
            return CompoundAssignment(name, operator, value)
        
        # 等于或为或=
        if not self._match(TokenType.KEYWORD, '等于') and not self._match(TokenType.KEYWORD, '为') and not self._match(TokenType.EQUALS):
            # 不是赋值语句，可能是表达式
            self.pos = saved_pos  # 完整回退到标识符之前
            return self._parse_expr_stmt()
        
        # 消耗等于/为/=
        self._consume()
        
        # 值
        value = self._parse_expr()
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return VarDecl(name, value)
    

    # =========================================================================
    # C风格语法解析
    # =========================================================================

    def _parse_c_function(self) -> ASTNode:
        """解析C风格函数定义：函数 name(params){body}

        生成与 段落 相同的 Paragraph AST 节点。
        """
        # 函数
        self._consume(TokenType.IDENTIFIER, '函数')

        # 函数名（合并连续 IDENTIFIER 和 KEYWORD，如 "测试_作用域守卫" 可能被拆分）
        name_tok = self._current()
        if not name_tok or name_tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            self._error(f"期望函数名标识符，但得到 {name_tok.type if name_tok else '输入结束'}",
                        name_tok.line if name_tok else 0, name_tok.col if name_tok else 0)
        name_parts = []
        # 收集连续的 IDENTIFIER 和 KEYWORD token 作为函数名
        # 停止关键字：语句级关键字不应出现在函数名中
        _func_stop_keywords = frozenset({
            '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
            '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
            '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
            '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
            '匹配', '的', '之', '对', '步', '至', '到', '推迟',
            '导', '出', '遍', '返', '跳', '过', '试', '捕', '抛', '掷', '终', '配', '否', '接', '承', '自',
        })
        while self._current():
            tok = self._current()
            if tok.value in _func_stop_keywords:
                break
            if tok.type == TokenType.IDENTIFIER:
                name_parts.append(self._consume(TokenType.IDENTIFIER).value)
            elif tok.type == TokenType.KEYWORD:
                name_parts.append(self._consume(TokenType.KEYWORD).value)
            else:
                break
        name = ''.join(name_parts)
        if not name:
            self._error(f"期望函数名标识符，但得到 {name_tok.type if name_tok else '输入结束'}",
                        name_tok.line if name_tok else 0, name_tok.col if name_tok else 0)

        # 参数列表 (params)
        params = []
        if self._current() and self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            while self._current() and self._current().type != TokenType.RPAREN:
                tok = self._current()
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                # 支持 *args / **kwargs
                if tok.type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '**' + ''.join(param_parts), 'type': None})
                    else:
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '*' + ''.join(param_parts), 'type': None})
                    continue
                if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_name = self._consume().value
                    param_type = None
                    # 支持参数类型注解：param: type
                    if self._current() and self._current().type == TokenType.COLON:
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    # 支持默认值：= 值
                    if self._current() and self._current().type == TokenType.EQUALS:
                        self._consume(TokenType.EQUALS)
                        if self._current() and self._current().type in (TokenType.NUMBER, TokenType.CHINESE_NUM, TokenType.STRING, TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume()
                    params.append({'name': param_name, 'type': param_type})
                else:
                    break
            if self._current() and self._current().type == TokenType.RPAREN:
                self._consume(TokenType.RPAREN)

        # 函数体 {body}
        body = self._parse_brace_body()

        return Paragraph(name, params, None, body)

    def _parse_c_var_decl(self) -> ASTNode:
        """解析C风格变量声明：令 name = expr

        生成与 设 name 为 expr 相同的 VarDecl AST 节点。
        """
        # 令
        self._consume(TokenType.IDENTIFIER, '令')

        # 变量名（合并连续 IDENTIFIER 和 KEYWORD，如 "已关闭" 中的 "关闭" 是关键字）
        name_tok = self._current()
        if not name_tok or name_tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            self._error(f"期望标识符，但得到 {name_tok.type if name_tok else '输入结束'}",
                        name_tok.line if name_tok else 0, name_tok.col if name_tok else 0)
        name_parts = []
        # 收集连续的 IDENTIFIER 和 KEYWORD token 作为变量名
        # 停止条件：=、等于、:、;、)、,、NEWLINE 等
        # # 停止关键字：与 _parse_c_function 保持一致，确保变量名/函数名合并行为统一
        _stop_keywords = frozenset({
            '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
            '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
            '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
            '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
            '匹配', '情况', '的', '之', '对', '步', '至', '到', '在', '于', '中的',
            '导', '出', '遍', '返', '跳', '过', '试', '捕', '抛', '掷', '终', '配', '否', '接', '承', '自',
        })
        while self._current():
            tok = self._current()
            if tok.type == TokenType.IDENTIFIER:
                name_parts.append(self._consume(TokenType.IDENTIFIER).value)
            elif tok.type == TokenType.KEYWORD and tok.value not in _stop_keywords:
                # 关键字可能是变量名的一部分（如 "已关闭" 中的 "关闭"、"使用率" 中的 "使用"）
                # 但要排除语句级关键字，避免吞掉后续语句
                name_parts.append(self._consume(TokenType.KEYWORD).value)
            else:
                break
        name = ''.join(name_parts)
        if not name:
            self._error(f"期望标识符，但得到 {name_tok.type if name_tok else '输入结束'}",
                        name_tok.line if name_tok else 0, name_tok.col if name_tok else 0)

        # 可选类型注解：令 name: type = expr
        type_annotation = None
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            type_annotation = self._parse_type_annotation()

        # = 或 等于
        if self._match(TokenType.EQUALS):
            self._consume(TokenType.EQUALS)
        elif self._match(TokenType.KEYWORD, '等于'):
            self._consume(TokenType.KEYWORD, '等于')
        else:
            tok = self._current()
            self._error(f"期望'='，但得到 {tok.type if tok else '输入结束'} = '{tok.value if tok else ''}'",
                        tok.line if tok else 0, tok.col if tok else 0)

        # 值
        value = self._parse_expr()

        # 句号（可选，用于独立语句）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        return VarDecl(name, value, type_annotation=type_annotation)

    def _parse_c_for_loop(self) -> ASTNode:
        """解析C风格for循环：循环(init;cond;incr){body}

        生成 CForStmt AST 节点。
        """
        # 循环
        self._consume(TokenType.IDENTIFIER, '循环')

        # (
        self._consume(TokenType.LPAREN)

        # init 子句：令 name = expr 或 name = expr 或空
        init = None
        if not self._match(TokenType.SEMICOLON):
            init = self._parse_for_clause()
        if self._current() and self._current().type == TokenType.SEMICOLON:
            self._consume(TokenType.SEMICOLON)

        # condition 子句
        condition = None
        if not self._match(TokenType.SEMICOLON):
            condition = self._parse_expr()
        if self._current() and self._current().type == TokenType.SEMICOLON:
            self._consume(TokenType.SEMICOLON)

        # increment 子句
        increment = None
        if not self._match(TokenType.RPAREN):
            increment = self._parse_for_clause()
        if self._current() and self._current().type == TokenType.RPAREN:
            self._consume(TokenType.RPAREN)

        # 循环体 {body}
        body = self._parse_brace_body()

        return CForStmt(init, condition, increment, body)

    def _parse_for_clause(self) -> ASTNode:
        """解析for循环的子句（init或incr）"""
        # 令 name = expr
        if self._match(TokenType.IDENTIFIER, '令'):
            return self._parse_c_var_decl()
        # name = expr（赋值）
        saved_pos = self.pos
        if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 合并连续 IDENTIFIER 和 KEYWORD
            name_parts = []
            _stop_kw = {'为', '等于', '接收', '返回'}
            while self._current():
                tok = self._current()
                if tok.type == TokenType.IDENTIFIER:
                    name_parts.append(self._consume(TokenType.IDENTIFIER).value)
                elif tok.type == TokenType.KEYWORD and tok.value not in _stop_kw:
                    name_parts.append(self._consume(TokenType.KEYWORD).value)
                else:
                    break
            name = ''.join(name_parts)
            if name and self._match(TokenType.EQUALS):
                self._consume(TokenType.EQUALS)
                value = self._parse_expr()
                return VarDecl(name, value)
            else:
                # 不是赋值，回退
                self.pos = saved_pos
        # 普通表达式
        return self._parse_expr()

    def _parse_brace_body(self) -> list:
        """解析花括号包围的代码块 { stmts }

        支持多行（带缩进）和单行两种形式。
        """
        self._consume(TokenType.LBRACE)

        # 跳过 NEWLINE
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)

        statements = []

        # 多行模式：有 INDENT
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
            statements = self._parse_body()
            # _parse_body 在 depth==0 遇到 DEDENT 时停止，不消耗 DEDENT
            if self._current() and self._current().type == TokenType.DEDENT:
                self._consume(TokenType.DEDENT)
        else:
            # 单行模式：解析语句直到 RBRACE
            while self._current() and self._current().type != TokenType.RBRACE:
                tok = self._current()
                if tok.type == TokenType.NEWLINE:
                    self._consume(TokenType.NEWLINE)
                    continue
                if tok.type == TokenType.DEDENT:
                    self._consume(TokenType.DEDENT)
                    continue
                if tok.type == TokenType.INDENT:
                    self._consume(TokenType.INDENT)
                    continue
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)
                else:
                    break

        # 跳过 NEWLINE
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)

        # 消耗 RBRACE
        if self._current() and self._current().type == TokenType.RBRACE:
            self._consume(TokenType.RBRACE)

        return statements

    def _parse_import_stmt(self) -> ImportStmt:
        """解析导入语句
        
        语法：
        1. 导入 模块名。
        2. 导入 模块名 为 别名。
        3. 导入 模块名一，模块名二。
        4. 导入 模块名一 为 别名一，模块名二 为 别名二。
        5. 导入《模块名》。
        6. 导入《模块名》为 别名。
        7. 导入 子模块名.符号 从 模块名（倒装形式）。
        8. 导入 Python: 模块名。（导入Python第三方库）
        9. 导入 C: 模块名。（导入C语言库）
        10. 导入 标准模块名。（导入光明标准库，"标准"前缀可选）
        """
        # 导入 / 导
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 检查语言前缀：Python: / C:
        language = None
        if self._current() and self._current().type == TokenType.IDENTIFIER:
            lang_tok = self._current()
            if lang_tok.value == 'Python':
                # 检查后面是否是冒号
                saved = self.pos
                self._consume()
                if self._current() and self._current().type == TokenType.COLON:
                    self._consume(TokenType.COLON)
                    language = 'python'
                else:
                    # 不是冒号，回退
                    self.pos = saved
            elif lang_tok.value == 'C':
                saved = self.pos
                self._consume()
                if self._current() and self._current().type == TokenType.COLON:
                    self._consume(TokenType.COLON)
                    language = 'c'
                else:
                    self.pos = saved
        
        # 收集所有导入的模块（支持多模块）
        module_entries = []  # [(module_name, alias), ...]
        
        while True:
            # 模块名（可以是标识符、关键字或书名号包裹）
            module_name = None
            if self._match(TokenType.LBOOK):
                # 书名号语法：《模块名》
                self._consume(TokenType.LBOOK)
                name_tok = self._consume(TokenType.IDENTIFIER)
                module_name = name_tok.value
                self._consume(TokenType.RBOOK)
            else:
                # 简单语法：模块名（支持点号分隔的路径，如 系统.路径）
                tok = self._current()
                if tok.type == TokenType.IDENTIFIER:
                    module_name = self._consume(TokenType.IDENTIFIER).value
                elif tok.type == TokenType.KEYWORD:
                    module_name = self._consume(TokenType.KEYWORD).value
                else:
                    self._error(f"期望模块名，但得到 {tok.type} = '{tok.value}'（建议：使用「从 模块名 导入 名称。」语法）", tok.line, tok.col)
                
                # 支持点号分隔的模块路径：os.path → os.path
                while self._current() and self._current().type == TokenType.DOT:
                    dot = self._consume(TokenType.DOT)
                    next_tok = self._current()
                    if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        part = self._consume().value
                        module_name += '.' + part
                    else:
                        # 遇到句号但后面不是标识符，回退
                        self.pos -= 1
                        break
            
            # 检查是否有别名：为
            alias = None
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
                alias_tok = self._consume(TokenType.IDENTIFIER)
                alias = alias_tok.value
            
            module_entries.append((module_name, alias))
            
            # 检查是否还有逗号分隔的更多模块
            if self._current() and self._current().type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            else:
                break
        
        # 检查是否是 "导 模块 出 符号一, 符号二" 语法（from-import 的正装形式）
        #
        # 「出」在两种上下文里语义完全不同，必须按位置区分：
        #   1. 语句开头的「出 A, B」 → 导出声明，声明本模块对外暴露什么
        #      → __all__ = ['A', 'B']（由 _parse_export_stmt 处理，不在这里）
        #   2. 「导 X 出 A, B」里的「出」 → from-import 的 import-list 引导词
        #      → from X import A, B（本分支）
        #
        # 缺这一支时，`导 X 出 A, B` 只会被消费成「导 X」，剩下的「出 A, B」
        # 落回 _parse_statement 被当成**独立的导出声明**，产出
        #     import X
        #     __all__ = ['A', 'B']
        # 两处都错：A/B 在导入方一个名字都没绑定（用到就 NameError），而
        # __all__ 写在导入方也毫无意义（它是导出方的声明）。解析、代码生成、
        # python compile 全过，只有运行期才炸——典型的静默错译。
        if len(module_entries) == 1 and (self._match(TokenType.KEYWORD, '出')
                                         or self._match(TokenType.KEYWORD, '导出')):
            self._consume(TokenType.KEYWORD, self._current().value)
            symbols = []
            while True:
                if self._match(TokenType.LBOOK):
                    # 书名号语法：《符号》
                    self._consume(TokenType.LBOOK)
                    symbols.append(self._consume(TokenType.IDENTIFIER).value)
                    self._consume(TokenType.RBOOK)
                elif self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 「为」是别名引导词，不是符号名，必须在这里截断，
                    # 否则 `导 X 出 A 为 P` 会把「为」「P」也当成导入符号。
                    if self._current().value == '为':
                        break
                    symbols.append(self._consume().value)
                else:
                    break

                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                    continue
                # 空格分隔的更多符号 / 紧邻的书名号
                if self._current() and self._current().type in (
                        TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.LBOOK):
                    if self._current().value == '为':
                        break
                    continue
                break

            if not symbols:
                tok = self._current()
                self._error(
                    "「导 %s 出 ...」后面缺少要导入的名称" % module_entries[0][0],
                    tok.line if tok else 0, tok.col if tok else 0)

            # 别名（可选）：导 X 出 A 为 P → from X import A as P
            fi_alias = module_entries[0][1]
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
                if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    fi_alias = self._consume().value

            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)

            return ImportStmt(module_entries[0][0], symbols=symbols,
                              alias=fi_alias, language=language)

        # v7 单 27：「导 <名> 自 <模块>」—— 模块绑定形（import <模块> as <名>）
        #
        # 「自」也要按位置区分两种语义（同上面「出」的处置）：
        #   1. 语句开头的「自」→ self/this（_parse_statement:403 → _parse_self_assignment），
        #      如 `自.姓名 = 姓名`。本分支只在「导 <名>」已消费之后才可能命中，够不到那里。
        #   2. 「导 <名> 自 <模块>」里的「自」→ 模块来源引导词
        #      （docs/language/l0-core.md:66、docs/language/keywords.md:13 列 `自` = 从）
        #
        # 与「从」分支（下面）的语义差别：
        #   `导入 X 从 Y` = from Y import X   —— 取符号
        #   `导 X 自 Y`   = import Y as X     —— 绑模块
        # 故 `导 数学 自 数学` → `import 数学`（名与源同名时不发多余的 as），
        # 之后 `数学.圆周率` 才有模块对象可取属性。若照「从」分支译成
        # `from 数学 import 数学` 会 ImportError——数学 模块里没有叫 数学 的名字。
        #
        # 缺这一支时，「自 数学」落回 _parse_statement 被当成 self 赋值，
        # 报「期望'为'或'等于'」——与本例真实意图毫无关系的误导性错误。
        if len(module_entries) == 1 and self._match(TokenType.KEYWORD, '自'):
            self._consume(TokenType.KEYWORD, '自')
            src_tok = self._current()
            if not (src_tok and src_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD)):
                self._error("「导 %s 自 ...」后面缺少模块名" % module_entries[0][0],
                            src_tok.line if src_tok else 0, src_tok.col if src_tok else 0)
            real_module = self._consume().value
            while self._current() and self._current().type == TokenType.DOT:
                self._consume(TokenType.DOT)
                next_tok = self._current()
                if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    real_module += '.' + self._consume().value
                else:
                    self.pos -= 1
                    break
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            local_name = module_entries[0][1] or module_entries[0][0]
            alias = None if local_name == real_module else local_name
            return ImportStmt(real_module, symbols=None, alias=alias, language=language)

        # 检查是否是 "导入 符号 从 模块" 语法（from import 的倒装形式）
        if self._match(TokenType.KEYWORD, '从'):
            self._consume(TokenType.KEYWORD, '从')
            # 相对导入前缀：导入 符号 从 .模块 / 从 ..模块
            rel_prefix = ''
            while self._current() and self._current().type == TokenType.DOT:
                self._consume(TokenType.DOT)
                rel_prefix += '.'
            # 读取真正的模块名（支持点号分隔路径）
            real_module = ''
            real_module_tok = self._current()
            if real_module_tok and real_module_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) \
                    and real_module_tok.value != '导入':
                real_module = self._consume().value
                # 支持点号分隔的模块路径
                while self._current() and self._current().type == TokenType.DOT:
                    self._consume(TokenType.DOT)
                    next_tok = self._current()
                    if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        real_module += '.' + self._consume().value
                    else:
                        self.pos -= 1
                        break
            else:
                real_module = module_entries[0][0] if module_entries else ''
            # 合成相对导入前缀
            if rel_prefix:
                real_module = rel_prefix + real_module
            # module_name 实际上是导入的符号
            symbols = [m[0] for m in module_entries]
            return ImportStmt(real_module, symbols=symbols, alias=module_entries[0][1] if module_entries else None, language=language)
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 多模块导入：返回第一个模块的导入语句
        if len(module_entries) == 1:
            return ImportStmt(module_entries[0][0], symbols=None, alias=module_entries[0][1], language=language)
        else:
            # 多模块导入：返回第一个模块，标记额外模块
            extra_modules = [(m, a) for m, a in module_entries[1:]]
            return ImportStmt(module_entries[0][0], symbols=None, alias=module_entries[0][1],
                            extra_modules=extra_modules, language=language)
    
    def _parse_from_import_stmt(self) -> ImportStmt:
        """解析从...导入语句
        
        语法：
        1. 从 模块名 导入 符号一 符号二。
        2. 从《模块名》导入《符号一》，《符号二》。
        3. 从 模块名 导入《符号一》《符号二》。
        """
        # 从
        self._consume(TokenType.KEYWORD, '从')
        
        # 相对导入前缀：从 .模块 导入 / 从 ..模块 导入
        # （. 表示当前目录，.. 表示上级目录，支持多级）
        relative_prefix = ''
        while self._current() and self._current().type == TokenType.DOT:
            self._consume(TokenType.DOT)
            relative_prefix += '.'
        
        # 模块名（支持点号分隔的路径，如 系统.路径）
        module_name = None
        if self._match(TokenType.LBOOK):
            # 书名号语法：《模块名》
            self._consume(TokenType.LBOOK)
            name_tok = self._consume(TokenType.IDENTIFIER)
            module_name = name_tok.value
            self._consume(TokenType.RBOOK)
        else:
            # 简单语法：模块名（可以是标识符或关键字）
            tok = self._current()
            if tok.type == TokenType.IDENTIFIER:
                module_name = self._consume(TokenType.IDENTIFIER).value
            elif tok.type == TokenType.KEYWORD and not (relative_prefix and tok.value == '导入'):
                # 相对导入时「导入」关键字不可作为模块名（如 从 . 导入 函数）
                module_name = self._consume(TokenType.KEYWORD).value
            elif relative_prefix:
                # 相对导入但模块名省略（如 从 . 导入 函数），留给合成逻辑处理
                pass
            else:
                self._error(f"期望模块名，但得到 {tok.type} = '{tok.value}'（建议：使用「从 模块名 导入 名称。」语法）", tok.line, tok.col)
            
            # 支持点号分隔的模块路径：os.path → os.path
            while self._current() and self._current().type == TokenType.DOT:
                self._consume(TokenType.DOT)
                next_tok = self._current()
                if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    part = self._consume().value
                    module_name += '.' + part
                else:
                    # 遇到句号但后面不是标识符，回退
                    self.pos -= 1
                    break
        
        # 合成相对导入的完整模块名（如 .模块 / ..模块）
        if relative_prefix:
            module_name = relative_prefix + (module_name or '')
        
        # 导入 / 导
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 符号列表（可以是书名号包裹、标识符或关键字）
        symbols = []
        while True:
            # 读取符号
            if self._match(TokenType.LBOOK):
                # 书名号语法：《符号》
                self._consume(TokenType.LBOOK)
                symbol_tok = self._consume(TokenType.IDENTIFIER)
                symbols.append(symbol_tok.value)
                self._consume(TokenType.RBOOK)
            elif self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 简单语法：符号名（可以是标识符或关键字）
                tok = self._consume()
                symbols.append(tok.value)
            else:
                break
            
            # 检查是否有逗号（继续导入）
            if self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                continue
            
            # 检查是否还有更多符号（空格分隔）
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                continue
            
            # 紧邻的书名号：导入《符号一》《符号二》《符号三》。
            # 缺这一支会在读完第一个《符号》后直接 break，后面的符号被
            # 静默丢弃——解析、代码生成全部通过，直到运行期才报 NameError。
            if self._current() and self._current().type == TokenType.LBOOK:
                continue
            
            # 检查是否结束（句号）
            if self._current() and self._current().type == TokenType.PERIOD:
                break
            
            # 如果不是标识符/关键字或句号，结束
            break
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 别名（可选）：从 模块 导入 符号 为 别名
        alias = None
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '为':
            self._consume(TokenType.KEYWORD, '为')
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                alias = self._consume().value
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return ImportStmt(module_name, symbols=symbols, alias=alias)

    def _parse_const_modifier(self) -> ASTNode:
        """解析常量修饰符前缀：`常 设 名 为 值。`（v7 单 33）。

        `常` 是 `docs/language/l0-core.md`「修饰（5字）」承诺的最后一个缺口；
        `常量`（双字）在 `KEYWORDS_DEFINE` 里挂了很久但同样没有解析路径，
        写 `常量 甲 为 1。` 一直报「「常量」是保留关键字，不能直接作为语句开头」。
        本单把整族一次收掉：两种写法都作为 `设` 语句的**前缀修饰符**。

        产物语义（必须说清，别当成实现了 const）：Python 没有常量，本修饰符
        **不改变产物**——`常 设 甲 为 1。` 与 `设 甲 为 1。` 编出同一行赋值。
        它的价值在于消灭旧的**静默错编**：落地前 `常 设 甲 为 1。` 会先编出一行
        多余的 `常()` 函数调用再接赋值，编译期零提示、运行期 NameError。
        真正的不可重赋值检查若要做，是另一支单（需要作用域跟踪），不在本单。
        """
        修饰符 = self._current().value
        self._consume(TokenType.KEYWORD)          # 吃掉 常 / 常量
        nxt = self._current()
        if not (nxt and nxt.type == TokenType.KEYWORD and nxt.value == '设'):
            self._error(
                f"「{修饰符}」是常量修饰符，后面必须跟「设」。"
                f"如：{修饰符} 设 圆周率 为 3.14159。",
                getattr(nxt, 'line', 0), getattr(nxt, 'col', 0),
                getattr(nxt, 'value', None))
        return self._parse_set_stmt()

    def _parse_set_stmt(self) -> ASTNode:
        """解析变量声明：设 变量名 为 值。或 设 变量 为 类型 = 值。或 解构赋值：设（甲，乙）为 元组。"""
        # 设
        self._consume(TokenType.KEYWORD, '设')
        
        # 检查是否为解构赋值：设 (甲, 乙) 为 元组 或 设 [首, 余] 为 列表
        if self._current() and self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            variables = []
            # 收集变量名
            while self._current():
                tok = self._current()
                if tok.type == TokenType.IDENTIFIER:
                    variables.append(self._consume(TokenType.IDENTIFIER).value)
                elif tok.type == TokenType.KEYWORD:
                    variables.append(self._consume(TokenType.KEYWORD).value)
                else:
                    break
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
            self._consume(TokenType.RPAREN)
            # 为
            self._consume(TokenType.KEYWORD, '为')
            # 值
            value = self._parse_expr()
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return DestructuringAssignment(variables, value, style='tuple')
        
        # 检查是否为列表解构赋值：设 [首, 余] 为 列表
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            variables = []
            # 收集变量名
            while self._current():
                tok = self._current()
                if tok.type == TokenType.IDENTIFIER:
                    variables.append(self._consume(TokenType.IDENTIFIER).value)
                elif tok.type == TokenType.KEYWORD:
                    variables.append(self._consume(TokenType.KEYWORD).value)
                else:
                    break
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
            self._consume(TokenType.RBRACKET)
            # 为
            self._consume(TokenType.KEYWORD, '为')
            # 值
            value = self._parse_expr()
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return DestructuringAssignment(variables, value, style='list')
        
        # 普通变量声明：变量名（支持标识符和关键字）
        name_tok = self._current()
        if name_tok and name_tok.type == TokenType.IDENTIFIER:
            name = self._consume(TokenType.IDENTIFIER).value
        elif name_tok and name_tok.type == TokenType.KEYWORD:
            name = self._consume(TokenType.KEYWORD).value
        else:
            self._error(f"期望标识符，但得到 {name_tok.type if name_tok else '输入结束'}",
                             name_tok.line if name_tok else 0, name_tok.col if name_tok else 0)
        
        # 检查多变量声明：设 x, y, z 为 0, 0, 0
        if self._match(TokenType.COMMA):
            variables = [name]
            while self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                tok = self._current()
                if tok and tok.type == TokenType.IDENTIFIER:
                    variables.append(self._consume(TokenType.IDENTIFIER).value)
                elif tok and tok.type == TokenType.KEYWORD:
                    variables.append(self._consume(TokenType.KEYWORD).value)
                else:
                    break
            # 多目标共享的类型注解：设 甲, 乙: 数 为 造()
            #
            # 单目标路径（本文件 :1778）早就支持 `: 类型`，多目标路径原先直接
            # 要求 为/等于/=，撞到冒号只会报「期望'为'或'等于'，但得到 冒号」——
            # 错误指向的位置对，说的话却把人往「你漏写了为」上引。
            # 口径（新单 G 裁定）：注解**广播**到每个目标，codegen 先发每个目标
            # 一条纯注解行再发解包语句。Python 不允许 `甲, 乙: float = f()`
            # （SyntaxError），所以只能这么落地。
            multi_type_annotation = None
            if self._current() and self._current().type == TokenType.COLON:
                self._consume(TokenType.COLON)
                multi_type_annotation = self._parse_type_annotation()
            # 为
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
            elif self._match(TokenType.KEYWORD, '等于'):
                self._consume(TokenType.KEYWORD, '等于')
            elif self._match(TokenType.EQUALS):
                self._consume(TokenType.EQUALS)
            else:
                tok = self._current()
                self._error(f"期望'为'或'等于'，但得到 {tok.type if tok else '输入结束'}",
                           tok.line if tok else 0, tok.col if tok else 0)
            value = self._parse_comparison()
            # 检查是否有逗号分隔的多值（如 设 x, y, z 为 0, 0, 0）
            if self._match(TokenType.COMMA):
                values = [value]
                while self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                    values.append(self._parse_comparison())
                # 构建元组字面量作为值
                from ast_nodes_v3 import TupleLiteral
                value = TupleLiteral(values)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return DestructuringAssignment(variables, value, style='tuple',
                                           type_annotation=multi_type_annotation)

        
        # 支持属性赋值：设 obj.attr 为 value 或 设 己.attr 为 value
        if self._current() and self._current().type == TokenType.DOT:
            self._consume(TokenType.DOT)
            # 收集属性名
            attr_parts = []
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 遇到赋值运算符或常见分隔符时停止
                if self._current().value in ('为', '等于', '加上', '减去', '乘以', '除以', '幂', '取余',
                                              '大于', '小于', '大于等于', '小于等于', '不等于',
                                              '与', '或', '非', '在', '到', '从', '且'):
                    break
                attr_parts.append(self._consume().value)
            if attr_parts:
                attr_name = '.'.join(attr_parts)
                full_name = f"{name}.{attr_name}"
            else:
                full_name = name
            
            # 检查是否是属性+索引赋值：设 obj.attr[index] 为 value 或 设 obj.attr[i][j] 为 value
            if self._current() and self._current().type == TokenType.LBRACKET:
                self._consume(TokenType.LBRACKET)
                index_expr = self._parse_expr()
                self._consume(TokenType.RBRACKET)
                # 支持多重索引：obj.attr[i][j]...
                target_expr = IndexAccess(Identifier(full_name), index_expr)
                while self._current() and self._current().type == TokenType.LBRACKET:
                    self._consume(TokenType.LBRACKET)
                    next_index = self._parse_expr()
                    self._consume(TokenType.RBRACKET)
                    target_expr = IndexAccess(target_expr, next_index)
                # 期望"为"或"等于"
                if self._match(TokenType.KEYWORD, '为'):
                    self._consume(TokenType.KEYWORD, '为')
                elif self._match(TokenType.KEYWORD, '等于'):
                    self._consume(TokenType.KEYWORD, '等于')
                elif self._match(TokenType.EQUALS):
                    self._consume(TokenType.EQUALS)
                else:
                    tok = self._current()
                    self._error(f"期望'为'或'等于'，但得到 {tok.type if tok else '输入结束'}",
                               tok.line if tok else 0, tok.col if tok else 0)
                value = self._parse_expr()
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                return IndexedAssignment(target=target_expr, index=None, value=value)
            
            # 期望"为"或"等于"
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
            elif self._match(TokenType.KEYWORD, '等于'):
                self._consume(TokenType.KEYWORD, '等于')
            elif self._match(TokenType.EQUALS):
                self._consume(TokenType.EQUALS)
            else:
                tok = self._current()
                self._error(f"期望'为'或'等于'，但得到 {tok.type if tok else '输入结束'} = '{tok.value if tok else ''}'",
                           tok.line if tok else 0, tok.col if tok else 0)
            value = self._parse_expr()
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            # 生成属性赋值：name.attr = value
            return VarDecl(full_name, value, type_annotation=None)

        # 支持索引赋值：设 obj[index] 为 value 或 设 obj[i][j] 为 value
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            index_expr = self._parse_expr()
            self._consume(TokenType.RBRACKET)
            # 支持多重索引：obj[i][j]...
            target_expr = IndexAccess(Identifier(name), index_expr)
            while self._current() and self._current().type == TokenType.LBRACKET:
                self._consume(TokenType.LBRACKET)
                next_index = self._parse_expr()
                self._consume(TokenType.RBRACKET)
                target_expr = IndexAccess(target_expr, next_index)
            # 期望"为"或"等于"
            if self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
            elif self._match(TokenType.KEYWORD, '等于'):
                self._consume(TokenType.KEYWORD, '等于')
            elif self._match(TokenType.EQUALS):
                self._consume(TokenType.EQUALS)
            else:
                tok = self._current()
                self._error(f"期望'为'或'等于'，但得到 {tok.type if tok else '输入结束'} = '{tok.value if tok else ''}'",
                           tok.line if tok else 0, tok.col if tok else 0)
            value = self._parse_expr()
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return IndexedAssignment(target=target_expr, index=None, value=value)
        
        # 类型注解（可选）：设 变量: 类型 为 值
        type_annotation = None
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            type_annotation = self._parse_type_annotation()
        
        # 为（支持设 变量 为 值 和 设 变量 为 类型 = 值 两种语法）
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
            
            # 检查是否是 设 变量 为 类型 = 值 语法
            # 如果"为"后面是类型名（内置类型或标识符），后面跟着 = 或 等于，则是类型注解
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                next_tok = self._peek(1)
                is_type_annotation = False
                
                # 判断下一个token是否是等号或"等于"关键字
                if next_tok and (next_tok.type == TokenType.EQUALS or 
                               (next_tok.type == TokenType.KEYWORD and next_tok.value == '等于')):
                    is_type_annotation = True
                elif next_tok and next_tok.type == TokenType.COLON:
                    is_type_annotation = True
                elif next_tok and next_tok.type == TokenType.LESS:
                    # 泛型类型注解：设 x 为 列表<整数> = []
                    is_type_annotation = True
                
                if is_type_annotation:
                    # 这是类型注解：设 x 为 整数 = 10 / 设 x 为 列表<整数> = []
                    type_annotation = self._parse_type_annotation()
                
                # 处理 = 或 等于
                if self._match(TokenType.EQUALS):
                    self._consume(TokenType.EQUALS)
                elif self._match(TokenType.KEYWORD, '等于'):
                    self._consume(TokenType.KEYWORD, '等于')
                
                # 值
                value = self._parse_expr()
            else:
                # 传统语法：设 x 为 值（没有类型注解）
                value = self._parse_expr()
        elif self._match(TokenType.KEYWORD, '等于'):
            self._consume(TokenType.KEYWORD, '等于')
            value = self._parse_expr()
        elif self._match(TokenType.EQUALS):
            self._consume(TokenType.EQUALS)
            value = self._parse_expr()
        elif type_annotation is not None:
            # 注解-无初值声明：设 姓名: 串（没有 为/等于/=）
            #
            # 规范要求这个形式：docs/L2_文言体语法规范_v4.0.md:599-600、:622-623。
            # 原先无条件要求 为/等于/=，模块级和类体内都报
            # ParseError「期望'为'或'等于'，但得到 换行」。
            # 只在已经吃到 `: 类型` 时才允许省略初值：裸 `设 x` 仍然报错。
            value = None
        else:
            tok = self._current()
            raise ParseError(
                f"期望'为'或'等于'，但得到 {tok.type if tok else '输入结束'} = '{tok.value if tok else ''}'",
                tok.line if tok else 0, tok.col if tok else 0, tok.value if tok else None)
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return VarDecl(name, value, type_annotation=type_annotation)
    
    def _parse_export_stmt(self) -> ExportStmt:
        """解析导出语句
        
        语法：
        1. 导出 符号一 符号二。
        2. 导出《符号一》，《符号二》。
        3. 导出 全部。
        """
        # 导出 / 出
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 检查是否是"全部"
        if self._match(TokenType.IDENTIFIER, '全部'):
            self._consume(TokenType.IDENTIFIER, '全部')
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return ExportStmt(['*'])  # 特殊标记：导出全部
        
        # 符号列表（可以是书名号包裹或简单标识符/关键字）
        symbols = []
        while True:
            # 读取符号
            if self._match(TokenType.LBOOK):
                # 书名号语法：《符号》
                self._consume(TokenType.LBOOK)
                symbol_tok = self._consume(TokenType.IDENTIFIER)
                symbols.append(symbol_tok.value)
                self._consume(TokenType.RBOOK)
            else:
                # 简单语法：符号名（支持IDENTIFIER和KEYWORD）
                tok = self._current()
                if tok and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    self._consume()
                    symbols.append(tok.value)
                else:
                    break
            
            # 检查是否有逗号（继续导出）
            if self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                continue
            
            # 检查是否还有更多符号（空格分隔）
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                continue
            
            # 检查是否结束（句号）
            if self._current() and self._current().type == TokenType.PERIOD:
                break
            
            # 如果不是标识符/关键字或句号，结束
            tok = self._current()
            if not tok or tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                break
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return ExportStmt(symbols)
    
    def _parse_var_decl(self) -> VarDecl:
        """解析变量声明（已移除的语法：定义 x 等于 y）

        此语法已从光明语法中移除。请使用「设 x 为 y」替代。
        """
        tok = self._current()
        self._error(
            f"语法「定义 x 等于 y」已移除，请改用「设 x 为 y」。如需定义类属性，请使用类定义语法。",
            tok.line if tok else 0, tok.col if tok else 0, tok.value if tok else None
        )
    
    def _parse_if_stmt(self) -> IfStmt:
        """解析条件语句（循环实现，支持任意深度嵌套）"""
        
        # 解析第一个条件
        if self._match(TokenType.KEYWORD, '若'):
            self._consume(TokenType.KEYWORD, '若')
        elif self._match(TokenType.KEYWORD, '如果'):
            self._consume(TokenType.KEYWORD, '如果')
        else:
            tok = self._current()
            self._error(f"期望'如果'或'若'，但得到'{tok.value if tok else '输入结束'}'",
                             tok.line if tok else 0, tok.col if tok else 0)
        
        condition = self._parse_expr()
        
        if self._match(TokenType.KEYWORD, '则'):
            self._consume(TokenType.KEYWORD, '则')
        elif self._match(TokenType.KEYWORD, '那么'):
            self._consume(TokenType.KEYWORD, '那么')
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 单行体：如果 条件 那么 语句。  （无冒号，无换行）
        if self._current() and self._current().type not in (TokenType.COLON, TokenType.LBRACE, TokenType.NEWLINE):
            then_body = [self._parse_statement()]
            # 处理 否则 / 否则如果 链
            result = IfStmt(condition, then_body, None)
            current = result
            while self._current() and (self._match(TokenType.KEYWORD, '否则') or self._match(TokenType.KEYWORD, '否')):
                self._consume(TokenType.KEYWORD, self._current().value)
                if self._match(TokenType.KEYWORD, '如果') or self._match(TokenType.KEYWORD, '若'):
                    self._consume(TokenType.KEYWORD, self._current().value)
                    elif_condition = self._parse_expr()
                    if self._match(TokenType.KEYWORD, '那么'):
                        self._consume(TokenType.KEYWORD, '那么')
                    elif_body = [self._parse_statement()]
                    current.else_body = IfStmt(elif_condition, elif_body, None)
                    current = current.else_body
                else:
                    else_body = [self._parse_statement()]
                    current.else_body = else_body
                    break
            return result
        
        # C风格花括号体：如果(cond){body} 否则{body} 否则如果(cond){body}
        if self._current() and self._current().type == TokenType.LBRACE:
            then_body = self._parse_brace_body()
            result = IfStmt(condition, then_body, None)
            current = result
            # 处理 C 风格的 否则 / 否则如果 链
            while self._current() and (self._match(TokenType.KEYWORD, '否则') or self._match(TokenType.KEYWORD, '否')):
                self._consume(TokenType.KEYWORD, self._current().value)
                if self._match(TokenType.KEYWORD, '如果'):
                    # 否则如果(cond){body}
                    self._consume(TokenType.KEYWORD, '如果')
                    elif_condition = self._parse_expr()
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    if self._current() and self._current().type == TokenType.LBRACE:
                        elif_body = self._parse_brace_body()
                    else:
                        # 回退到冒号+缩进体（混合写法兼容）
                        self._consume(TokenType.COLON)
                        _hn = False
                        while self._current() and self._current().type == TokenType.NEWLINE:
                            _hn = True
                            self._consume(TokenType.NEWLINE)
                        if self._current() and self._current().type == TokenType.INDENT:
                            self._consume(TokenType.INDENT)
                        elif_body = self._parse_body(allow_single_line=not _hn, stop_on_else=True)
                        if self._current() and self._current().type == TokenType.DEDENT:
                            self._consume(TokenType.DEDENT)
                    current.else_body = IfStmt(elif_condition, elif_body, None)
                    current = current.else_body
                else:
                    # 否则{body}
                    if self._current() and self._current().type == TokenType.LBRACE:
                        else_body = self._parse_brace_body()
                    else:
                        # 回退到冒号+缩进体（混合写法兼容）
                        self._consume(TokenType.COLON)
                        _hn = False
                        while self._current() and self._current().type == TokenType.NEWLINE:
                            _hn = True
                            self._consume(TokenType.NEWLINE)
                        if self._current() and self._current().type == TokenType.INDENT:
                            self._consume(TokenType.INDENT)
                        else_body = self._parse_body(allow_single_line=not _hn, stop_on_else=True)
                        if self._current() and self._current().type == TokenType.DEDENT:
                            self._consume(TokenType.DEDENT)
                    current.else_body = else_body
                    break
            return result
        
        self._consume(TokenType.COLON)
        
        has_newline = False
        while self._current() and self._current().type == TokenType.NEWLINE:
            has_newline = True
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        # 如果有 NEWLINE（即多行体），不需要 allow_single_line 模式
        then_body = self._parse_body(allow_single_line=not has_newline, stop_on_else=True)
        
        # 消耗 DEDENT（if体结束）
        # _parse_body 遇到 DEDENT 时会 break，不消耗 DEDENT，留给调用者处理
        # 这里只消耗一个 DEDENT（当前 if 层对应的）
        if self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        
        # 跳过 DEDENT 后面的 NEWLINE
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('否则', '否'):
                pass
            else:
                self._consume(TokenType.KEYWORD, '结束')
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            next_tok = self._peek(1)
            if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('否则', '否'):
                pass
            else:
                self._consume(TokenType.IDENTIFIER)
                if self._current() and self._current().type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
        
        # 创建根节点
        result = IfStmt(condition, then_body, None)
        current = result
        
        # 循环处理否则如果/否则分支（'或若' 是 v7 单 27 补齐的 '否则若' 同义别名）
        while self._current() and (self._match(TokenType.KEYWORD, '否则') or self._match(TokenType.KEYWORD, '否') or self._match(TokenType.KEYWORD, '否则若') or self._match(TokenType.KEYWORD, '或若')):
            if self._match(TokenType.KEYWORD, '否则若') or self._match(TokenType.KEYWORD, '或若'):
                # 否则若 / 或若：作为单个token的elif
                self._consume(TokenType.KEYWORD, self._current().value)
                elif_condition = self._parse_expr()
                
                if self._match(TokenType.KEYWORD, '则'):
                    self._consume(TokenType.KEYWORD, '则')
                elif self._match(TokenType.KEYWORD, '那么'):
                    self._consume(TokenType.KEYWORD, '那么')
                
                self._consume(TokenType.COLON)
                
                has_newline = False
                while self._current() and self._current().type == TokenType.NEWLINE:
                    has_newline = True
                    self._consume(TokenType.NEWLINE)
                if self._current() and self._current().type == TokenType.INDENT:
                    self._consume(TokenType.INDENT)
                
                elif_body = self._parse_body(allow_single_line=not has_newline, stop_on_else=True)
                
                # 消耗 DEDENT（否则如果体结束）
                if self._current() and self._current().type == TokenType.DEDENT:
                    self._consume(TokenType.DEDENT)
                
                # 创建新节点并链接
                current.else_body = IfStmt(elif_condition, elif_body, None)
                current = current.else_body
            elif self._match(TokenType.KEYWORD, '否则') or self._match(TokenType.KEYWORD, '否'):
                self._consume(TokenType.KEYWORD, self._current().value)
                
                if self._match(TokenType.KEYWORD, '如果') or self._match(TokenType.KEYWORD, '若'):
                    # 否则如果/否若：创建新的 IfStmt 作为 else_body
                    self._consume(TokenType.KEYWORD, self._current().value)
                    elif_condition = self._parse_expr()
                    
                    if self._match(TokenType.KEYWORD, '则'):
                        self._consume(TokenType.KEYWORD, '则')
                    elif self._match(TokenType.KEYWORD, '那么'):
                        self._consume(TokenType.KEYWORD, '那么')
                    
                    self._consume(TokenType.COLON)
                    
                    has_newline = False
                    while self._current() and self._current().type == TokenType.NEWLINE:
                        has_newline = True
                        self._consume(TokenType.NEWLINE)
                    if self._current() and self._current().type == TokenType.INDENT:
                        self._consume(TokenType.INDENT)
                    
                    elif_body = self._parse_body(allow_single_line=not has_newline, stop_on_else=True)
                    
                    # 消耗 DEDENT（否则如果体结束）
                    if self._current() and self._current().type == TokenType.DEDENT:
                        self._consume(TokenType.DEDENT)
                    
                    # 创建新节点并链接
                    current.else_body = IfStmt(elif_condition, elif_body, None)
                    current = current.else_body
                else:
                    # 否则：直接解析 else_body
                    self._consume(TokenType.COLON)
                    
                    has_newline = False
                    while self._current() and self._current().type == TokenType.NEWLINE:
                        has_newline = True
                        self._consume(TokenType.NEWLINE)
                    if self._current() and self._current().type == TokenType.INDENT:
                        self._consume(TokenType.INDENT)
                    
                    else_body = self._parse_body(allow_single_line=not has_newline, stop_on_else=True)
                    
                    # 消耗 DEDENT（否则体结束）
                    if self._current() and self._current().type == TokenType.DEDENT:
                        self._consume(TokenType.DEDENT)
                    
                    current.else_body = else_body
                    break
        
        # 消耗结束（如果存在）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return result
    
    # ------------------------------------------------------------------
    # 遍历循环：连接词 → 语序 映射表（单 01 已定口径，按连接词纯语法消歧）
    #
    # 变量在前： 遍 变量[, 变量...] <连接词> 可迭代对象
    #   于     examples/L0_core/04_遍_循环.light:7 `遍 果 于 水果：`
    #   在     tests/test_core_coverage.py:161     `遍历 i 在 1 到 10：`
    #   中的   docs/统一语法规范_v3.2.md:164        `遍历 项 中的 列表：`
    #   之     tests/test_edge_cases.py:338        `遍历 项 之 列表：`
    #          （历史上两种语序混用，无法纯语法消歧：`遍 甲 之 乙` 的 token 序列
    #          完全一致。v7 合并裁定裸 `之` 一律为「变量在前」；需要「可迭代对象
    #          在前」必须写 `之为` 或 `为`。口径已同步至
    #          docs/L1_白话体语法规范_v4.0.md 9.1 与 docs/guide/常见问题.md）

    #
    # 可迭代对象在前： 遍 可迭代对象 <连接词> 变量[, 变量...]
    #   为     docs/L1_白话体语法规范_v4.0.md:601、docs/guide/常见问题.md:244
    #          examples/E阶段_L3L4原生语法/E1_L3_SQL原生.light:41 `遍 好成绩 为 行:`
    #   之为   docs/L1_白话体语法规范_v4.0.md:318 `遍[1,2,3]之为i:`
    #          docs/L2_文言体语法规范_v4.0.md:367 `遍 列表 之为 元素:`
    #          （词法上是 `之` + `为` 两个 token，故可与裸 `之` 纯语法区分）
    # ------------------------------------------------------------------
    FOREACH_CONNECTORS_VAR_FIRST = frozenset({'之', '在', '于', '中的'})
    FOREACH_CONNECTORS_ITER_FIRST = frozenset({'为'})
    FOREACH_CONNECTORS = FOREACH_CONNECTORS_VAR_FIRST | FOREACH_CONNECTORS_ITER_FIRST

    def _scan_foreach_names(self):
        """前瞻：把当前位置尝试识别为「名字列表」（`名 (, 名)*` 紧跟连接词）。

        纯语法判定，不看标识符含义、不查符号表。命中则把 self.pos 推进到
        连接词之前并返回名字列表；不命中则完全回滚并返回 None。
        """
        saved = self.pos
        names = []
        while True:
            tok = self._current()
            if tok is None or tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                break
            if tok.type == TokenType.KEYWORD and tok.value in self.FOREACH_CONNECTORS:
                break
            names.append(tok.value)
            self.pos += 1
            nxt = self._current()
            if nxt is not None and nxt.type == TokenType.COMMA:
                self.pos += 1
                continue
            break
        tok = self._current()
        if names and tok is not None and tok.type == TokenType.KEYWORD \
                and tok.value in self.FOREACH_CONNECTORS:
            return names
        self.pos = saved
        return None

    # ------------------------------------------------------------------
    # 裁决 E：`遍 <任意表达式> 为 <变量>:`
    #
    # 根因（实测取证）：`为` 在 parser_core.py:263 属于 OPERATOR_VERBS，
    # 且 parser_core.py:271 把它映射成 `==`。所以当第一操作数不是「裸名字列表」
    # （`_scan_foreach_names` 前瞻失败，如 `d的项`、`范围(1,10)`）而走
    # `_parse_expr()` 时，parser_expr.py:132-140 的比较循环会把连接词 `为`
    # 当成 `==` 吞掉，整行被读成 `<可迭代对象> == <变量>`；随后连接词检查
    # 看到的是 `:`，报「遍历循环期望'在'、'之'、'于'、'中的'、'为'或'之为'，
    # 但得到 「:」」。裸标识符形（`遍 xs 为 项`）之所以一直是绿的，是因为
    # `_scan_foreach_names` 抢先命中了名字列表路径，压根没走表达式解析。
    #
    # 消歧判据（纯语法，不做语义推断，与既定「遍历语序按连接词区分」口径一致）：
    # 先在 foreach 头部做一次括号深度感知的只读前瞻，找第一个 **深度 0** 的 `为`：
    #   * 若它前一个（深度 0 的）token 是 `之`，那是 `之为`，交回原有路径
    #     ——原有路径本来就对，`_in_foreach_context` 会让 `之` 及时停下；
    #   * 否则判定为「可迭代对象在前 + 单字 `为`」形态，于是
    #       1) 把 `为` 临时从 self.OPERATOR_VERBS 摘掉，比较循环就会在 `为`
    #          处 break，表达式恰好停在连接词之前（不需要回溯）；
    #       2) 把 `_in_foreach_context` 置 False——既然已经出现 `为`，语序
    #          已定为「可迭代对象在前」，头部里的 `之` 就不可能是连接词，
    #          必须恢复它的成员访问语义，否则 `遍 自之成绩的项 为 项` 会被
    #          切成「变量 自 + 连接词 之」。
    # 头部边界：深度 0 的 COLON，或 NEWLINE / 输入结束。
    # ------------------------------------------------------------------
    _FOREACH_HEADER_OPEN = (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE)
    _FOREACH_HEADER_CLOSE = (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE)

    def _scan_foreach_lone_wei(self) -> bool:
        """前瞻：foreach 头部是否存在「单字 `为`」连接词（`之为` 不算）。

        纯只读，不移动 self.pos。
        """
        depth = 0
        i = self.pos
        prev = None  # 上一个深度 0 的实义 token
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.type in self._FOREACH_HEADER_OPEN:
                depth += 1
            elif tok.type in self._FOREACH_HEADER_CLOSE:
                depth -= 1
            elif depth == 0:
                # 头部结束：没找到 `为`
                if tok.type in (TokenType.COLON, TokenType.NEWLINE):
                    return False
                if tok.type == TokenType.KEYWORD and tok.value == '为':
                    # `之为` 走原有路径
                    return not (prev is not None
                                and prev.type == TokenType.KEYWORD
                                and prev.value == '之')
            if depth == 0 and tok.type not in (
                    TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                prev = tok
            i += 1
        return False

    def _parse_foreach_targets(self):
        """解析循环目标名列表 `名 (, 名)*`，返回 Python for 目标文本。"""
        names = []
        while True:
            tok = self._current()
            if tok is None or tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                break
            names.append(self._consume().value)
            nxt = self._current()
            if nxt is not None and nxt.type == TokenType.COMMA:
                self._consume()
                continue
            break
        return ', '.join(names) if names else '_'

    def _parse_foreach_stmt(self, is_async: bool = False) -> ForeachStmt:
        """解析遍历循环

        语法（语序由连接词决定，见 FOREACH_CONNECTORS_* 映射表）：
              遍 变量 之/于/在/中的 可迭代对象:
              遍 变量, 变量 之/于/在/中的 可迭代对象:
              遍 可迭代对象 为/之为 变量[, 变量]:
              遍 变量 之/于/在/中的 起始 至 结束:
              上述各式亦支持 C 风格 `{ body }`
        """
        # 跳过 NEWLINE
        if self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        
        # 遍历 / 对 / 遍
        if self._match(TokenType.KEYWORD, '对'):
            self._consume(TokenType.KEYWORD, '对')
        elif self._match(TokenType.KEYWORD, '遍'):
            self._consume(TokenType.KEYWORD, '遍')
        else:
            self._consume(TokenType.KEYWORD, '遍历')
        
        # ---- 第一操作数：可能是「变量名列表」，也可能是「可迭代对象表达式」 ----
        # 先做纯语法前瞻：`名 (, 名)*` 且紧跟连接词 → 认定为名字列表。
        # 前瞻失败（如 `范围(1,10)`、`[1,2,3]`、`配置.项()`）才按表达式解析，
        # 这条回退路径在改动前一律是解析错误，属纯新增能力。
        # ---- 第一操作数：可能是「变量名列表」，也可能是「可迭代对象表达式」 ----
        # 裁决 E 优先级：先看头部有没有深度 0 的单字 `为`。有 → 语序已定为
        # 「可迭代对象在前」，绝不能再走名字列表路径。
        #
        # 必须放在 `_scan_foreach_names` **之前**：`遍 自之成绩的项 为 项:` 里
        # `自` 是裸名字、紧跟的 `之` 又恰好在连接词表里，名字列表前瞻会误命中
        # ['自'] 并把 `之` 当连接词，于是产出 `for 自 in (自之成绩的项 == 项)`
        # ——这正是 examples/L2_wenyan/学生模块.light:39 改前的静默错编。
        iter_first_wei = self._scan_foreach_lone_wei()

        # 名字列表前瞻（纯语法）：`名 (, 名)*` 且紧跟连接词 → 认定为名字列表。
        # 前瞻失败（如 `范围(1,10)`、`[1,2,3]`、`配置.项()`）才按表达式解析。
        lhs_names = None if iter_first_wei else self._scan_foreach_names()
        lhs_expr = None
        if lhs_names is None:
            old_foreach_context = self._in_foreach_context
            saved_operator_verbs = self.OPERATOR_VERBS
            if iter_first_wei:
                # 摘掉 `为`：parser_expr 的比较循环会在连接词处 break，
                # 表达式恰好停在 `为` 之前，不再吞成 `==`。
                self.OPERATOR_VERBS = saved_operator_verbs - {'为'}
                # 语序已定，头部里的 `之` 只能是成员访问，恢复其正常语义。
                self._in_foreach_context = False
            else:
                self._in_foreach_context = True
            try:
                lhs_expr = self._parse_expr()
            finally:
                self.OPERATOR_VERBS = saved_operator_verbs
                self._in_foreach_context = old_foreach_context



        # ---- 连接词：决定语序。`之为` 是 `之`+`为` 两个 token，优先整体匹配 ----
        tok = self._current()
        if tok is not None and tok.type == TokenType.KEYWORD and tok.value in self.FOREACH_CONNECTORS:
            nxt = self._peek(1)
            if (tok.value == '之' and nxt is not None
                    and nxt.type == TokenType.KEYWORD and nxt.value == '为'):
                self._consume()
                self._consume()
                connector = '之为'
            else:
                connector = self._consume().value
        else:
            self._error(
                f"遍历循环期望'在'、'之'、'于'、'中的'、'为'或'之为'，但得到 {tok.type} = '{tok.value}'",
                tok.line, tok.col)

        if connector in self.FOREACH_CONNECTORS_ITER_FIRST or connector == '之为':
            # 可迭代对象在前：遍 可迭代对象 为/之为 变量[, 变量]
            if lhs_expr is not None:
                iterable = lhs_expr
            elif len(lhs_names) == 1:
                iterable = Identifier(lhs_names[0])
            else:
                # 多个名字不可能是可迭代对象，判为语法错误而非猜测
                self._error(
                    f"遍历循环连接词 '{connector}' 要求「可迭代对象在前」，"
                    f"但前面出现了多个名字：{', '.join(lhs_names)}",
                    tok.line, tok.col)
            variable = self._parse_foreach_targets()
        else:
            # 变量在前：遍 变量[, 变量] 之/于/在/中的 可迭代对象
            if lhs_names is not None:
                variable = ', '.join(lhs_names)
            elif isinstance(lhs_expr, Identifier):
                variable = lhs_expr.name
            else:
                # 连接词判定为「变量在前」，但变量位置不是名字（如 `遍[1,2,3]之为i`
                # 在紧凑分词下被切成 `之` + `为i`）。此处报错，避免退化成
                # `for _ in ...` 这种静默错编。
                self._error(
                    f"遍历循环连接词 '{connector}' 要求「变量在前」，"
                    f"但连接词左侧不是循环变量名",
                    tok.line, tok.col)


            # 设置上下文标志，防止"之"在可迭代对象表达式中被当作成员访问符消耗
            old_foreach_context = self._in_foreach_context
            self._in_foreach_context = True

            # 解析可迭代对象表达式（完整表达式）
            iterable = self._parse_expr()

            # 恢复上下文标志
            self._in_foreach_context = old_foreach_context

            # 处理隐式范围表达式：遍 i 于 1 至 N
            # 当可迭代对象表达式之后还有非终止符 token 时，尝试解析为范围结束表达式
            if self._current() and self._current().type not in (TokenType.COLON, TokenType.LBRACE, TokenType.NEWLINE, TokenType.PERIOD):
                range_saved_pos = self.pos
                try:
                    end_expr = self._parse_add_expr()
                    if self.pos > range_saved_pos:
                        iterable = RangeExpr(iterable, end_expr, None)
                except Exception:
                    self.pos = range_saved_pos

        
        # C风格花括号体：遍历 x 于 列表{ body }
        if self._current() and self._current().type == TokenType.LBRACE:
            body = self._parse_brace_body()
            return ForeachStmt(variable, iterable, body, is_async=is_async)
        
        # 冒号
        self._consume(TokenType.COLON)
        
        # 消耗所有连续的 NEWLINE 和 INDENT（处理空行和注释行）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        # 循环体
        body = self._parse_body()
        
        # 消耗 DEDENT（循环体结束）
        if self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        
        # 消耗"结束"关键字（可选）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return ForeachStmt(variable, iterable, body, is_async=is_async)
    
    def _parse_while_stmt(self) -> WhileStmt:
        """解析当循环"""
        # 当
        self._consume(TokenType.KEYWORD, '当')
        
        # 条件
        condition = self._parse_expr()
        
        # 那么（可选）
        if self._match(TokenType.KEYWORD, '那么'):
            self._consume(TokenType.KEYWORD, '那么')
        
        # 冒号
        self._consume(TokenType.COLON)
        
        # 消耗所有连续的 NEWLINE、DEDENT 和 INDENT（处理多行条件中的缩进变化）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        # 多行条件可能导致额外的 DEDENT/INDENT，需要先消耗 DEDENT
        while self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        # 循环体 - 使用_parse_body
        body = self._parse_body()
        
        # 消耗 DEDENT（循环体结束）
        # _parse_body 遇到 DEDENT 时会 break，不消耗 DEDENT，留给调用者处理
        # 这里只消耗一个 DEDENT（当前 while 层对应的）
        if self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        
        # 消耗"结束"关键字（可选）
        # "结束"可能被词法分析器识别为 IDENTIFIER（非关键字），两种情况都要处理
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return WhileStmt(condition, body)
    
    def _parse_return_stmt(self) -> ReturnStmt:
        """解析返回语句"""
        # 返回
        self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
        
        # 表达式（可选）
        value = None
        # 检查是否有表达式：如果下一个token不是句号、不是DEDENT、不是NEWLINE、不是语句关键字，则解析表达式
        if self._current():
            tok = self._current()
            if tok.type != TokenType.PERIOD and tok.type != TokenType.DEDENT and tok.type != TokenType.NEWLINE:
                # 检查是否是语句关键字
                is_stmt_keyword = False
                if tok.type == TokenType.KEYWORD:
                    if tok.value in ('函数', '段落'):
                        # 段落调用（段落段名(参数)）应该作为表达式处理
                        next_tok = self._peek(1)
                        if next_tok and next_tok.type == TokenType.LPAREN:
                            # 段落段名(参数)形式，作为表达式处理
                            is_stmt_keyword = False
                        else:
                            # 段落定义，作为语句关键字
                            is_stmt_keyword = True
                    else:
                        is_stmt_keyword = (tok.value in ('设', '定义', '当', '如果', '若', '遍历', '遍',
                                                          '打印', '导入', '导', '导出', '出', '跳出', '跳', '跳过', '过', '继续',
                                                          '断', '跃',
                                                          '尝试', '试', '抛出', '抛', '掷', '匹配', '配', '返回', '返',
                                                          '构造', '类', '接口', '接', '推迟'))
                if not is_stmt_keyword:
                    # 先解析第一个表达式（不含逗号/管道）
                    first = self._parse_logical_expr()
                    
                    # 后置三元表达式：值 如果 条件 否则 值
                    if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '如果':
                        self._consume(TokenType.KEYWORD, '如果')
                        condition = self._parse_logical_expr()
                        else_expr = None
                        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('否则', '否'):
                            self._consume(TokenType.KEYWORD, self._current().value)
                            else_expr = self._parse_expr()
                        value = ConditionalExpression(condition, first, else_expr)
                    # 检查是否是多值返回（逗号分隔）
                    elif self._current() and self._current().type == TokenType.COMMA:
                        values = [first]
                        while self._current() and self._current().type == TokenType.COMMA:
                            self._consume(TokenType.COMMA)
                            # 跳过 NEWLINE
                            while self._current() and self._current().type in (TokenType.NEWLINE,):
                                self._consume()
                            values.append(self._parse_logical_expr())
                        value = TupleLiteral(values)
                    else:
                        # 单值返回
                        value = first
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return ReturnStmt(value)
    
    def _parse_clause_body(self) -> List[ASTNode]:
        """解析「引导词 + 冒号 + 换行 + INDENT ... DEDENT」形式的子句块体，
        并**正确收束本块自己的 DEDENT**。

        与直接 `self._parse_body()` 的差别（这正是缺陷根因）：
        _parse_body 的契约是「调用者已消耗当前块的 INDENT」（见其 docstring），
        它内部的 depth 只用来跟踪**嵌套**结构。直接调用而不先消耗 INDENT 时，
        本块自己的 INDENT 会被当成嵌套记进 depth（0→1），于是块结束的那个
        DEDENT 只把 depth 减回 0 而**不会停止循环**，块后面的**兄弟**语句
        就被继续吞进本块。

        试/捕/终 三个块过去都是直接调用 _parse_body()，只是「碰巧」能停住：
        try 块后面紧跟 `捕`、catch 块后面紧跟 `终`，而 _parse_body 对
        捕/终/否则/结束 这几个关键字有 break。一旦块后面是**普通语句**
        （最终块是最后一个子句，天然如此），就没有任何 break 条件，后续
        兄弟语句被静默并入块内——解析、代码生成、python compile 全过，
        只有运行期语义是错的（典型静默错译）。

        本方法按 _parse_body 的契约来：先消耗本块的 INDENT，让 depth 从 0
        起算，块结束的 DEDENT 便会在 depth==0 时被看到 → _parse_body 停止并
        把 DEDENT 留给本方法消耗。这与「否则」子句（_parse_try_stmt 里原本
        就写对了的那一支）用的是同一套写法。
        """
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)

        indented = False
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
            indented = True

        body = self._parse_body()

        if indented and self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)

        return body

    def _parse_catch_clause(self):
        """解析单个捕获子句
        
        返回: (catch_type, catch_var, catch_body)
        
        支持语法：
          捕获 异常类型：
          捕获 异常变量：
          捕获 异常类型 异常变量：
          捕获 (异常类型1, 异常类型2)：
          捕获 (异常类型1, 异常类型2) 异常变量：
          捕获 异常类型1, 异常类型2：         （无括号多类型）
          捕获 异常类型1, 异常类型2 异常变量：（无括号多类型 + 变量）
        """
        catch_type = None
        catch_var = None
        
        # 读取类型/变量名
        tok = self._current()
        if tok and tok.type == TokenType.LPAREN:
            # 捕获 (Type1, Type2)：语法
            self._consume(TokenType.LPAREN)
            types = []
            while True:
                type_tok = self._current()
                if type_tok and type_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    types.append(self._consume().value)
                else:
                    break
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break
            self._consume(TokenType.RPAREN)
            catch_type = ', '.join(types)
            
            # 检查是否有变量名
            var_tok = self._current()
            if var_tok and var_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) and var_tok.value != '：':
                catch_var = self._consume().value
        elif tok and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 先读取第一个标识符/关键字
            first = self._consume().value
            
            # 检查是否有逗号分隔的多类型（无括号）
            if self._match(TokenType.COMMA):
                types = [first]
                while self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                    type_tok = self._current()
                    if type_tok and type_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        types.append(self._consume().value)
                    else:
                        break
                catch_type = ', '.join(types)
                
                # 检查是否有变量名
                var_tok = self._current()
                if var_tok and var_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) and var_tok.value != '：':
                    catch_var = self._consume().value
            else:
                # 单类型或变量
                next_tok = self._current()
                if next_tok and next_tok.type == TokenType.COLON:
                    # 只有一个标识符/关键字，后面是冒号
                    # 启发式判断：以大写字母开头视为类型名，否则视为变量名
                    if first and first[0].isupper():
                        catch_type = first
                    else:
                        catch_var = first
                elif next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 跳过 '为' 关键字
                    if next_tok.value == '为':
                        self._consume()  # 消费 '为'
                        catch_type = first
                        var_tok = self._current()
                        if var_tok and var_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            catch_var = self._consume().value
                        else:
                            catch_var = first
                    else:
                        # 有类型和变量名
                        catch_type = first
                        catch_var = self._consume().value
                else:
                    # 只有一个标识符，视为变量名
                    catch_var = first
        
        # 冒号（可能是中文冒号或英文冒号）
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
        
        # catch块。
        # 必须用 _parse_clause_body（消耗本块 INDENT/DEDENT）而不是裸
        # _parse_body()：catch 块后面可能紧跟**兄弟**语句（当 catch 是最后一个
        # 子句时），这些普通语句不触发 _parse_body 的关键字 break，会被静默吞入
        # except 块——典型折叠 bug（见 _parse_clause_body docstring）。
        catch_body = self._parse_clause_body()
        
        return catch_type, catch_var, catch_body
    
    def _parse_try_stmt(self) -> TryStmt:
        """解析异常捕获语句
        
        语法：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        
        或带类型过滤：
        尝试：
          语句...
        捕获 值异常：
          语句...
        
        或带类型和变量：
        尝试：
          语句...
        捕获 值异常 异常变量：
          语句...
        
        或多个捕获块：
        尝试：
          语句...
        捕获 我的异常 e：
          语句...
        捕获 异常 e：
          语句...
        
        或带最终块：
        尝试：
          语句...
        捕获 异常变量：
          语句...
        最终：
          语句...
        结束。
        """
        # 尝试 / 试
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 冒号
        self._consume(TokenType.COLON)
        
        # try块。
        # 与 catch/finally 块统一使用 _parse_clause_body：先消耗本块 INDENT，
        # 再调 _parse_body（depth 从 0 起算），最后消耗 DEDENT。
        # 此前用裸 _parse_body()「碰巧」能停住（try 后面紧跟 捕/终/结束 等
        # 关键字，_parse_body 有 break），但 DEDENT 的消耗路径不规范，且
        # 与 catch 块的修固保持一致。
        try_body = self._parse_clause_body()
        
        # 捕获（可选，支持多个）
        catch_clauses = []
        catch_type = None
        catch_var = None
        catch_body = []
        
        first_catch = True
        while self._match(TokenType.KEYWORD, '捕获') or self._match(TokenType.KEYWORD, '捕'):
            self._consume(TokenType.KEYWORD, self._current().value)
            
            ct, cv, cb = self._parse_catch_clause()
            catch_clauses.append((ct, cv, cb))
            
            if first_catch:
                catch_type = ct
                catch_var = cv
                catch_body = cb
                first_catch = False
        
        # 最终（可选）
        finally_body = []
        if self._match(TokenType.KEYWORD, '最终') or self._match(TokenType.KEYWORD, '终'):
            self._consume(TokenType.KEYWORD, self._current().value)
            
            # 冒号
            self._consume(TokenType.COLON)
            
            # finally块。
            # 必须用 _parse_clause_body（消耗本块 INDENT/DEDENT）而不是裸
            # _parse_body()：最终块是 try 语句的最后一个子句，其后紧跟的
            # 是**兄弟**语句而非 捕/终/否则/结束 等能触发 _parse_body 停止的
            # 关键字。裸 _parse_body 会把本块 INDENT 记成嵌套 depth，块结束的
            # DEDENT 只把 depth 减回 0 而不停止，导致后续兄弟语句被静默吞进
            # finally 块（见 _parse_clause_body 的 docstring）。
            finally_body = self._parse_clause_body()
        
        # 否则（可选）- try 块的 else 子句，没有异常时执行
        else_body = []
        if self._match(TokenType.KEYWORD, '否则'):
            self._consume(TokenType.KEYWORD, '否则')
            self._consume(TokenType.COLON)
            has_newline = False
            while self._current() and self._current().type == TokenType.NEWLINE:
                has_newline = True
                self._consume(TokenType.NEWLINE)
            if self._current() and self._current().type == TokenType.INDENT:
                self._consume(TokenType.INDENT)
            else_body = self._parse_body(allow_single_line=not has_newline, stop_on_else=True)
            if self._current() and self._current().type == TokenType.DEDENT:
                self._consume(TokenType.DEDENT)
        
        # 消耗"结束"关键字（可选）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER)
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return TryStmt(try_body, catch_clauses=catch_clauses, 
                       catch_type=catch_type, catch_var=catch_var, 
                       catch_body=catch_body, finally_body=finally_body,
                       else_body=else_body)
    
    def _parse_throw_stmt(self) -> ThrowStmt:
        """解析抛出异常语句
        
        语法：抛出 表达式。 或 抛出（重新抛出当前异常）
        """
        # 抛出 / 抛
        self._consume(TokenType.KEYWORD, self._current().value)
        
        # 检查是否是裸抛出（重新抛出当前异常）
        tok = self._current()
        if tok and tok.type in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.PERIOD, TokenType.EOF):
            # 裸抛出：抛出（重新抛出当前异常）
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return ThrowStmt(None)
        
        # 异常值
        value = self._parse_expr()
        
        # from 子句（可选）：抛出 ValueError(...) from 空 或 抛出 值错误 从 原异常
        from_expr = None
        if self._current() and self._current().value in ('from', '从'):
            self._consume()  # consume 'from' or '从' (IDENTIFIER or KEYWORD)
            from_expr = self._parse_expr()
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return ThrowStmt(value, from_expr)

    def _parse_defer_stmt(self):
        """解析推迟语句（B5：defer）

        语法：推迟 语句。 或 推迟：\n  语句1\n  语句2\n
        语义：推迟体在作用域退出时执行（FILO 栈序），包括提前 return 和异常路径。
        """
        from ast_nodes import DeferStatement
        # 推迟
        self._consume(TokenType.KEYWORD, '推迟')

        # 两种形式：
        # 1. 单语句：推迟 打印("清理")。
        # 2. 块语句：推迟：
        #        语句1
        #        语句2
        tok = self._current()
        if tok and tok.type == TokenType.COLON:
            # 块形式：推迟：\n  body
            self._consume(TokenType.COLON)
            # 跳过 NEWLINE，消费 INDENT（_parse_body 要求调用者已消耗 INDENT）
            while self._current() and self._current().type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
            indented = False
            if self._current() and self._current().type == TokenType.INDENT:
                self._consume(TokenType.INDENT)
                indented = True
            body = self._parse_body()
            if indented and self._current() and self._current().type == TokenType.DEDENT:
                self._consume(TokenType.DEDENT)
        else:
            # 单语句形式：推迟 <语句>
            stmt = self._parse_statement()
            body = [stmt] if stmt else []

        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        return DeferStatement(body=body)


    def _parse_yield_stmt(self):
        """解析生成语句
        
        语法：生成 表达式。 / 生成。 / 生成 全部 表达式。（生成器委托 yield from）
        """
        from ast_nodes_v3 import YieldStmt
        # 生成
        self._consume(TokenType.KEYWORD, '生成')
        
        # 检查是否是裸生成（生成 None）
        tok = self._current()
        if tok and tok.type in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.PERIOD, TokenType.EOF):
            # 句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return YieldStmt(None)
        
        # A2 生成器委托：`生成 全部 乙()。` → `yield from 乙()`
        # `全部` 已是既有词（builtin_map 里 全部→all、`导出 全部` 也用它），语义贴合。
        # 判据是「全部 后面不是左括号」：`生成 全部(列)。` 仍是把 all(列) 的布尔结果
        # yield 出去，那是普通表达式，不能被抢走。
        nxt = self._peek(1)
        if (tok.value == '全部'
                and not (nxt and nxt.type == TokenType.LPAREN)):
            self._consume()  # 全部
            value = self._parse_expr()
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
            return YieldStmt(value, is_from=True)
        
        # `生成 从 乙()。` 曾静默编成 `yield 从` + `乙()` 两条语句（编译期零提示，
        # 运行期才炸 NameError）。委托只认 `生成 全部`，这条写法必须报错。
        if tok.value in ('从', 'from'):
            self._error(
                "生成器委托请写 `生成 全部 表达式。`（等价 yield from），"
                "不支持 `生成 从 …`",
                getattr(tok, 'line', 0), getattr(tok, 'column', 0), tok.value)
        
        # 生成值
        value = self._parse_expr()
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return YieldStmt(value)


    def _attach_param_default(self, params) -> None:
        """把 `等于`/`=` 之后的默认值挂到最近一个形参上（A4）。调用前 `等于` 已被消耗。

        `接收` 形参表原先只是把默认值 token 消耗进一个**从不写回**的局部变量
        （旧 default_val），于是 `段落 连接 接收 主机, 端口 等于 443` 编成
        `def 连接(主机, 端口)`，调用 `连接("h", 超时 = 5)` 运行期才炸 missing
        positional argument。括号式方法形参那条通路（本文件 :4397 起）早就落地了
        默认值，只有 `接收` 这条漏了——语法过得去、跑起来才炸，属静默错编。

        只收单 token 字面量/标识符，与 :4402 同一判据：`接收` 形参表没有括号
        界定边界，放宽成完整表达式会把后面的 `返回 类型` 或体冒号一起吃掉。
        """
        tok = self._current()
        if not tok or tok.type not in (TokenType.NUMBER, TokenType.CHINESE_NUM,
                                       TokenType.STRING, TokenType.IDENTIFIER,
                                       TokenType.KEYWORD):
            return
        val = self._consume().value
        if tok.type == TokenType.NUMBER:
            val_str = str(val)
            default_value = NumberLiteral(float(val_str) if '.' in val_str else int(val_str))
        elif tok.type == TokenType.CHINESE_NUM:
            # 词法层已把中文数字转成 int（lexer.py:1584/1947）
            default_value = NumberLiteral(val)
        elif tok.type == TokenType.STRING:
            default_value = StringLiteral(val)
        elif val == '真':
            default_value = Identifier('True')
        elif val == '假':
            default_value = Identifier('False')
        elif val == '空':
            default_value = Identifier('None')
        else:
            default_value = Identifier(val)
        if params:
            params[-1]['default'] = default_value

    def _parse_run_async_stmt(self):
        """解析异步启动语句：`异步 运行 主()。` → `asyncio.run(主())`

        为什么落在 `异步 运行` 而不是任务书建议的 `运行 异步`：后者要求把
        `运行` 提成全局关键字，而全仓 .light 里 `运行` 已被当作段落名与形参名
        使用（examples/J阶段_L4_C_Go_MoonBit/J1_C_快速求和.light:16 `段 运行():`、
        积木库/blocks_v5/网络/网络可用性.light:4 形参 `运行`），提关键字会直接
        打红这些文件。`异步 运行` 把 `运行` 限制在 `异步` 之后的上下文里识别，
        既零新增关键字（无需全仓 token A/B 扫描），又与既有
        `异步 段落 / 异步 遍历 / 异步 作用域` 同族同头，风格一致。
        """
        from ast_nodes_v3 import RunAsyncStmt
        self._consume(TokenType.KEYWORD)   # 异步 / 异
        self._consume()                    # 运行
        call = self._parse_expr()
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        return RunAsyncStmt(call)

    def _is_paragraph_definition(self) -> bool:

        """向前扫描，判断 段落 主(...) 是段落定义还是段落调用。
        
        段落定义：段落 主()： 或 段落 主(参数1, 参数2)： 或 段落 主(参数) 返回 类型：
        段落调用：段落 主()  （无冒号）
        
        从当前token（段落/段关键字）开始，扫描到匹配的 ) 后检查是否有 : 或 返回/-> 类型 :。
        """
        # 当前位置是 段落/段 关键字，后面是 段名(参数...)
        # 从段名后的 ( 开始扫描，找到匹配的 )
        pos = self.pos
        # 跳过 段落/段 关键字
        idx = pos
        # 跳过段名
        idx += 1
        # 现在 idx 应该指向 (
        if idx >= len(self.tokens):
            return False
        # 向前扫描，找匹配的 )
        paren_depth = 0
        while idx < len(self.tokens):
            t = self.tokens[idx]
            if t.type == TokenType.LPAREN:
                paren_depth += 1
            elif t.type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth == 0:
                    # 找到匹配的 )，检查下一个token是否是 : 或 返回/-> 类型 :
                    next_idx = idx + 1
                    if next_idx < len(self.tokens):
                        next_t = self.tokens[next_idx]
                        if next_t.type == TokenType.COLON:
                            return True
                        # 支持 返回 类型: 或 -> 类型: 语法
                        if (next_t.type == TokenType.KEYWORD and next_t.value == '返回') or \
                           next_t.type == TokenType.ARROW:
                            # 扫描到下一个 : 确认是段落定义
                            scan_idx = next_idx + 1
                            paren_depth2 = 0
                            while scan_idx < len(self.tokens):
                                st = self.tokens[scan_idx]
                                if st.type == TokenType.LESS:
                                    paren_depth2 += 1
                                elif st.type == TokenType.GREATER:
                                    paren_depth2 -= 1
                                elif st.type == TokenType.COLON and paren_depth2 == 0:
                                    return True
                                elif st.type == TokenType.LPAREN:
                                    paren_depth2 += 1
                                elif st.type == TokenType.RPAREN:
                                    paren_depth2 -= 1
                                scan_idx += 1
                        return False
                    return False
            idx += 1
        return False
    
    def _parse_paragraph_v2(self, name: str = None) -> Paragraph:
        """解析段落定义：函数/段落/段 段名 接收 参数1, 参数2："""
        if name is None:
            # 消耗 函数、段落 或 段 关键字
            if self._match(TokenType.KEYWORD, '函数'):
                self._consume(TokenType.KEYWORD, '函数')
            elif self._match(TokenType.KEYWORD, '段落'):
                self._consume(TokenType.KEYWORD, '段落')
            elif self._match(TokenType.KEYWORD, '段'):
                self._consume(TokenType.KEYWORD, '段')
            else:
                tok = self._current()
                self._error(f"期望'函数'（或兼容写法'段落'/'段'），但得到 {tok.type if tok else '输入结束'}",
                                 tok.line if tok else 0, tok.col if tok else 0)
        
            name_tok = self._current()
            name_parts = []
            if name_tok and name_tok.type == TokenType.IDENTIFIER:
                name_parts.append(self._consume(TokenType.IDENTIFIER).value)
            elif name_tok and name_tok.type == TokenType.CHINESE_NUM:
                name_parts.append(str(self._consume(TokenType.CHINESE_NUM).value))
            elif name_tok and name_tok.type == TokenType.KEYWORD:
                name_parts.append(self._consume(TokenType.KEYWORD).value)
            else:
                self._error(f"期望标识符作为段名，但得到 {name_tok.type if name_tok else '输入结束'}", name_tok.line if name_tok else 0, name_tok.col if name_tok else 0, name_tok.value if name_tok else None)
            
            while self._current():
                next_tok = self._current()
                if next_tok.type == TokenType.IDENTIFIER:
                    name_parts.append(self._consume(TokenType.IDENTIFIER).value)
                elif next_tok.type == TokenType.CHINESE_NUM:
                    name_parts.append(str(self._consume(TokenType.CHINESE_NUM).value))
                elif next_tok.type == TokenType.KEYWORD and next_tok.value not in ('接收', '返回'):
                    name_parts.append(self._consume(TokenType.KEYWORD).value)
                else:
                    break
            
            name = ''.join(name_parts)
        
        generic_params = []
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                param_name = self._consume().value
                generic_params.append(param_name)
                if self._current() and self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                else:
                    break
            if self._current() and self._current().type == TokenType.RBRACKET:
                self._consume(TokenType.RBRACKET)
        
        params = []
        # 支持括号式参数：段名(参数1, 参数2)： 或 《段名》段(参数1, 参数2)：
        if self._match(TokenType.LPAREN):
            self._consume(TokenType.LPAREN)
            _stmt_keywords_paren = {'设', '定义', '当', '如果', '若', '遍历', '返回', '打印', '导入', '导出', '跳出', '跳过', '尝试', '抛出', '匹配', '推迟'}
            while self._current() and self._current().type != TokenType.RPAREN:
                tok = self._current()
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                if tok.type == TokenType.IDENTIFIER:
                    param_name = self._consume(TokenType.IDENTIFIER).value
                    param_type = None
                    # 检查类型注解：参数名: 类型
                    if self._current() and self._current().type == TokenType.COLON:
                        next_tok = self._peek(1)
                        if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume(TokenType.COLON)
                            param_type = self._parse_type_annotation()
                    params.append({'name': param_name, 'type': param_type})
                elif tok.type == TokenType.KEYWORD and tok.value not in _stmt_keywords_paren:
                    param_name = self._consume(TokenType.KEYWORD).value
                    param_type = None
                    if self._current() and self._current().type == TokenType.COLON:
                        next_tok = self._peek(1)
                        if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume(TokenType.COLON)
                            param_type = self._parse_type_annotation()
                    params.append({'name': param_name, 'type': param_type})
                else:
                    break
            self._consume(TokenType.RPAREN)
            # 支持括号外的参数类型标注：(a):整数, b:整数
            param_idx = 0
            _type_annotation_keywords = {'返回', '设', '定义', '当', '如果', '若', '遍历', '打印', '导入', '导出', '跳出', '跳过', '尝试', '抛出', '匹配', '异步', '等待', '推迟'}
            while (self._current() and self._current().type == TokenType.COLON
                   and param_idx < len(params)):
                next_tok = self._peek(1)
                if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.CHINESE_NUM) \
                        and not (next_tok.type == TokenType.KEYWORD and next_tok.value in _type_annotation_keywords):
                    next_next = self._peek(2)
                    if next_next and next_next.type == TokenType.NEWLINE:
                        break  # 段落体冒号
                    self._consume(TokenType.COLON)
                    type_tok = self._current()
                    if type_tok and type_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.CHINESE_NUM):
                        params[param_idx]['type'] = self._consume().value
                    param_idx += 1
                    if self._current() and self._current().type == TokenType.COMMA:
                        self._consume(TokenType.COMMA)
                        if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            if param_idx < len(params):
                                param_idx += 1
                            else:
                                extra_name = self._consume().value
                                params.append({'name': extra_name, 'type': None})
                else:
                    break
        elif self._match(TokenType.KEYWORD, '接收'):
            # 旧式参数语法：接收 参数1, 参数2
            # 已废弃，推荐使用括号式：段落 名(参数1, 参数2)：
            import warnings
            warnings.warn(
                f"语法「段落 名 接收 参数」已废弃，请改用「函数 名(参数)」或「段落 名(参数)」。在未来的版本中将移除「接收」关键字。",
                DeprecationWarning, stacklevel=2
            )
            self._consume(TokenType.KEYWORD, '接收')
            
            _stmt_keywords = {'设', '定义', '当', '如果', '若', '遍历', '遍', '返回', '返', '打印', '导入', '导', '导出', '出', '跳出', '跳', '跳过', '过', '断', '跃', '尝试', '试', '抛出', '抛', '掷', '匹配', '配', '类', '接口', '接', '推迟'}
            while self._current() and self._current().type != TokenType.COLON:
                tok = self._current()
                if tok.type == TokenType.KEYWORD and (tok.value == '返回' or tok.value == '返' or tok.value in _stmt_keywords):
                    break
                # 支持 -> 返回类型语法
                if tok.type == TokenType.ARROW:
                    break
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                # 支持 *args / **kwargs
                if tok.type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '**' + ''.join(param_parts), 'type': None})
                    else:
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '*' + ''.join(param_parts), 'type': None})
                    continue
                if tok.type == TokenType.IDENTIFIER:
                    param_name = self._consume(TokenType.IDENTIFIER).value
                    param_type = None
                    
                    # 检查是否是 参数名: 类型 语法
                    if self._current() and self._current().type == TokenType.COLON:
                        next_tok = self._peek(1)
                        if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.CHINESE_NUM) \
                                and (next_tok.type != TokenType.KEYWORD or next_tok.value not in ('返回', '设', '定义', '当', '如果', '若', '遍历', '打印', '导入', '导出', '跳出', '跳过', '尝试', '抛出', '匹配')):
                            self._consume(TokenType.COLON)
                            type_tok = self._current()
                            if type_tok and type_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.CHINESE_NUM):
                                param_type = self._parse_type_annotation()
                        else:
                            params.append({'name': param_name, 'type': param_type})
                            break
                    # 检查是否是 参数名 类型名 语法（空格分隔，类型名是内置类型或普通标识符）
                    elif self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        next_tok = self._current()
                        next_next = self._peek(1)
                        
                        # 判断是否是类型名：
                        # 1. 是内置类型
                        # 2. 是标识符且下一个token是逗号或关键字（返回、设等），但不包括冒号（冒号可能是块开始）
                        is_type = False
                        if next_tok.value in BUILTIN_TYPES:
                            is_type = True
                        elif next_tok.type == TokenType.IDENTIFIER:
                            if next_next and (next_next.type == TokenType.COMMA or 
                                             (next_next.type == TokenType.KEYWORD and 
                                              (next_next.value == '返回' or next_next.value in _stmt_keywords))):
                                is_type = True
                        
                        if is_type:
                            param_type = self._parse_type_annotation()
                    
                    params.append({'name': param_name, 'type': param_type})
                    # 支持默认值：参数名 等于 默认值 或 参数名 = 默认值
                    if self._current() and ((self._current().type == TokenType.KEYWORD and self._current().value == '等于') or self._current().type == TokenType.EQUALS):
                        self._consume()
                        self._attach_param_default(params)
                elif tok.type == TokenType.KEYWORD:
                    if tok.value == '接收':
                        self._consume(TokenType.KEYWORD, tok.value)
                        continue
                    if tok.value == '返回' or tok.value == '返' or tok.value in _stmt_keywords:
                        break
                    if tok.value == '等于':
                        # 这是前一个参数的默认值，消耗它和值
                        self._consume(TokenType.KEYWORD, '等于')
                        self._attach_param_default(params)
                        continue

                    param_name = self._consume(TokenType.KEYWORD).value
                    param_type = None
                    
                    # 检查是否是 参数名: 类型 语法
                    if self._current() and self._current().type == TokenType.COLON:
                        next_tok = self._peek(1)
                        if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.CHINESE_NUM):
                            self._consume(TokenType.COLON)
                            type_tok = self._current()
                            if type_tok and type_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD, TokenType.CHINESE_NUM):
                                param_type = self._parse_type_annotation()
                        else:
                            params.append({'name': param_name, 'type': param_type})
                            break
                    # 检查是否是 参数名 类型名 语法（仅当参数名不是关键字时）
                    # 关键字参数名（如「等待」）后的标识符是参数名的一部分，不是类型注解
                    elif self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        next_tok = self._current()
                        next_next = self._peek(1)
                        if next_tok.value in BUILTIN_TYPES:
                            param_type = self._parse_type_annotation()
                        elif next_tok.type == TokenType.IDENTIFIER and next_next and \
                             (next_next.type == TokenType.COMMA or next_next.type == TokenType.COLON):
                            if param_name in ('等待', '异步', '同步'):
                                # 关键字参数名后紧跟标识符时，合并为复合参数名
                                # 例如「等待价值」应作为一个参数名，而不是「等待: 价值」
                                param_name += self._consume(TokenType.IDENTIFIER).value
                            else:
                                param_type = self._parse_type_annotation()
                    
                    params.append({'name': param_name, 'type': param_type})
                    # 支持默认值：参数名 等于 默认值 或 参数名 = 默认值
                    if self._current() and ((self._current().type == TokenType.KEYWORD and self._current().value == '等于') or self._current().type == TokenType.EQUALS):
                        self._consume()
                        self._attach_param_default(params)
                else:
                    break

        
        return_type = None
        if (self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '返回'):
            next_tok = self._peek(1)
            if next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
                return_type = self._parse_type_annotation()
        elif (self._current() and self._current().type == TokenType.ARROW):
            self._consume(TokenType.ARROW)
            return_type = self._parse_type_annotation()
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        self._consume(TokenType.COLON)

        # 跳过所有连续的 NEWLINE（处理空行和注释行）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)

        body = self._parse_body(stop_on_paragraph=False)

        # 消耗 DEDENT（段落体结束）
        # _parse_body 遇到 DEDENT 时会 break，不消耗 DEDENT，留给调用者处理
        # 这里只消耗一个 DEDENT（当前段层对应的）
        if self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER)
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return Paragraph(name, params, return_type, body, generic_params=generic_params)
    
    def _parse_async_paragraph(self) -> Paragraph:
        """解析异步段落定义：异步 段落/函数/段 段名 ...

        v7 单 31-G：`异` 是 `异步` 的 L0 单字别名，此处一并接受；
        存入 modifiers 的一律归一为 `'异步'`，下游（code_generator 判 async def）不用改。
        """
        # 异步 / 异
        tok = self._current()
        if tok and tok.type == TokenType.KEYWORD and tok.value == '异':
            self._consume(TokenType.KEYWORD, '异')
        else:
            self._consume(TokenType.KEYWORD, '异步')

        # 调用普通段落解析
        para = self._parse_paragraph_v2()
        
        # 添加异步修饰符
        if '异步' not in para.modifiers:
            para.modifiers = list(para.modifiers) + ['异步']
        
        return para
    
    def _parse_strict_paragraph(self) -> Paragraph:
        """解析严格段落定义：严格 段落 段名 ..."""
        self._consume(TokenType.KEYWORD, '严格')
        
        para = self._parse_paragraph_v2()
        
        if '严格' not in para.modifiers:
            para.modifiers = list(para.modifiers) + ['严格']
        
        return para
    
    def _parse_async_scope(self) -> AsyncScope:
        """解析异步作用域：异步作用域：
            任务1
            任务2
        结束
        """
        # 异步 / 异（v7 单 31-G 单字别名）
        self._consume(TokenType.KEYWORD)
        self._consume(TokenType.KEYWORD, '作用域')
        
        # 可选的结果变量名列表
        result_vars = []
        tok = self._current()
        if tok and tok.type == TokenType.IDENTIFIER:
            # 收集变量名，直到遇到冒号
            while self._current() and self._current().type == TokenType.IDENTIFIER:
                result_vars.append(self._current().value)
                self._consume(TokenType.IDENTIFIER)
        
        self._consume(TokenType.COLON)
        
        # 消耗所有连续的 NEWLINE 和 INDENT（处理空行和注释行）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        # 解析任务列表（每个语句是一个任务）
        tasks = []
        
        body = self._parse_body()
        
        # 消耗 DEDENT
        if self._current() and self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        
        # 消耗"结束"关键字
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '结束':
            self._consume(TokenType.KEYWORD, '结束')
            # 消耗句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.IDENTIFIER and self._current().value == '结束':
            self._consume(TokenType.IDENTIFIER, '结束')
            # 消耗句号（可选）
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
        
        return AsyncScope(tasks=body, result_vars=result_vars)
    
    def _parse_body(self, allow_single_line=False, stop_on_else=False, stop_on_paragraph=True) -> List[ASTNode]:
        """解析代码块
        
        正确处理嵌套的 INDENT/DEDENT：
        - 调用者已消耗当前块的 INDENT
        - 内部嵌套结构（if/while/for 等）会产生额外的 INDENT/DEDENT
        - 用 depth 计数器跟踪嵌套深度
        - 当 depth 回到 -1 时，表示遇到了调用者那个 INDENT 对应的 DEDENT，停止解析
        
        参数:
            allow_single_line: 是否允许单行语句模式。在单行模式下，当 depth == 0 且
                             下一行是语句关键字时，会停止解析。这用于处理单行 if/while/for
                             语句的 then_body。默认 False，用于段落体等多行块。
            stop_on_else: 是否在 depth==0 时遇到'否则'就停止解析。默认 False，
                         在 if 语句的 then_body 中设为 True，让 if 语句处理 else 分支。
            stop_on_paragraph: 是否在 depth==0 时遇到段落定义就停止解析。默认 True，
                              在段落体内部设为 False，允许继续解析后续的模块级段落。
        """
        statements = []
        depth = 0

        max_statements = 100
        count = 0

        while self._current() and count < max_statements:
            tok = self._current()
            
            # 分号：同行多语句分隔符（`打印 ""; 打印 "x"`）。
            # 文档明文承诺 `;` 与全角 `；` 等价、可在一行里分隔多个独立语句
            # （docs/光明-完整规范文档.md:345-346,356-357,660-664、
            #  docs/统一语法规范_v3.1.md:171），此前从未实现。
            # 与 NEWLINE 的区别：单行模式（allow_single_line）下 NEWLINE 要 break，
            # 而 `;` 恰恰是「本行还有下一句」，必须继续收。
            # C 风格 `循环(init; cond; incr)` 头部的分号在 _parse_c_for_loop 内部
            # 就被 _consume 掉了（:1169-1179，先吃 LPAREN 再逐段解析），流不到这里。
            if tok.type == TokenType.SEMICOLON:
                self._consume(TokenType.SEMICOLON)
                continue

            # 跳过 NEWLINE token
            if tok.type == TokenType.NEWLINE:
                if allow_single_line:
                    break
                self._consume(TokenType.NEWLINE)
                continue

            # INDENT：嵌套深度增加
            if tok.type == TokenType.INDENT:
                self._consume(TokenType.INDENT)
                depth += 1
                continue

            # DEDENT：嵌套深度减少
            if tok.type == TokenType.DEDENT:
                if depth == 0:
                    # 检查是否是空行导致的假 DEDENT（后面跟着 INDENT）
                    next_tok = self._peek(1)
                    if next_tok and next_tok.type == TokenType.INDENT:
                        # 跳过这对 DEDENT+INDENT，继续解析
                        self._consume(TokenType.DEDENT)
                        self._consume(TokenType.INDENT)
                        continue
                    # 深度为 0 时遇到 DEDENT，说明当前块结束
                    # 不消耗这个 DEDENT，留给调用者处理
                    break
                else:
                    # 嵌套结构结束，消耗 DEDENT 并减少深度
                    self._consume(TokenType.DEDENT)
                    depth -= 1
                    continue

            # 否则标记（if语句的else分支）- 在 depth==0 时遇到否则总是停止
            # 让调用者（如_parse_if_stmt）来处理
            if stop_on_else and depth == 0 and tok.type == TokenType.KEYWORD and tok.value in ('否则', '否'):
                # 检查后面是否是冒号或如果
                next_tok = self._peek(1)
                if next_tok and next_tok.type == TokenType.COLON:
                    # 否则: - 这是 if 语句的 else 分支，停止解析让调用者处理
                    break
                if next_tok and next_tok.type == TokenType.KEYWORD and next_tok.value in ('如果', '若'):
                    # 否则如果 - 这是 if 语句的 elif 分支，停止解析让调用者处理
                    break
            if stop_on_else and depth == 0 and tok.type == TokenType.KEYWORD and tok.value in ('否则若', '否若', '或若'):
                # 否则若 - 作为单个token的elif，停止解析让调用者处理
                break

            # 异常处理的特殊标记（捕获、最终、否则、结束）- 仅在 depth==0 时停止
            if depth == 0 and tok.type == TokenType.KEYWORD and tok.value in ('捕获', '捕', '最终', '终', '否则', '否', '结束'):
                break
            if depth == 0 and tok.type == TokenType.IDENTIFIER and tok.value == '结束':
                break

            # 类/接口/协议定义（在body中遇到的，作为嵌套处理）- 仅在 depth==0 时停止
            if depth == 0 and tok.type == TokenType.KEYWORD and tok.value in ('类', '接口', '接', '协议'):
                break

            # 跳过孤立的句号（块结束后的可选终止符）
            if tok.type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
                continue

            if stop_on_paragraph and depth == 0 and tok.type == TokenType.KEYWORD and tok.value in ('函数', '段落', '段'):
                # 检查后面是否是段名后跟括号（段落调用）
                next_tok = self._peek(1)
                second_tok = self._peek(2)
                if not (next_tok and next_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) 
                        and second_tok and second_tok.type == TokenType.LPAREN):
                    # 这是段落定义，不是段落调用，停止解析
                    break

            # 解析语句
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
                count += 1
                
                # 在 allow_single_line 模式下，解析完一个语句后，如果下一个 token 是语句关键字，
                # 且不是 NEWLINE，则停止解析（表示这个语句是单行语句）
                if allow_single_line:
                    next_tok = self._current()
                    if next_tok and next_tok.type == TokenType.KEYWORD:
                        if next_tok.value in ('返回', '设', '定义', '打印', '导入', '导出', '跳出', '跳过', '抛出', '如果', '若', '当', '遍历', '推迟'):
                            break
            else:
                break

        return statements
    
    # =============================================================================
    # 段落定义解析（《段名》段 语法）
    # =============================================================================
    
    def _parse_paragraph(self) -> Paragraph:
        """解析《段名》段 语法
        
        示例：
        《加法》段 接收 甲, 乙：
            返回 甲 加 乙。
        """
        # 《
        self._consume(TokenType.LBOOK)
        # 段名
        name = self._consume(TokenType.IDENTIFIER).value
        # 》
        self._consume(TokenType.RBOOK)
        # 段（可选关键字）
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '段':
            self._consume(TokenType.KEYWORD, '段')
        
        params = []
        generic_params = []
        
        # 接收 参数列表
        if self._match(TokenType.KEYWORD, '接收'):
            self._consume(TokenType.KEYWORD, '接收')
            
            _stmt_keywords = {'设', '定义', '当', '如果', '若', '遍历', '遍', '返回', '返', '打印', '导入', '导', '导出', '出', '跳出', '跳', '跳过', '过', '断', '跃', '尝试', '试', '抛出', '抛', '掷', '匹配', '配', '类', '接口', '接', '推迟'}
            while self._current() and self._current().type != TokenType.COLON:
                tok = self._current()
                if tok.type == TokenType.KEYWORD and (tok.value == '返回' or tok.value == '返' or tok.value in _stmt_keywords):
                    break
                if tok.type == TokenType.ARROW:
                    break
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                # 支持 *args / **kwargs
                if tok.type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    if self._current() and self._current().type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '**' + ''.join(param_parts), 'type': None})
                    else:
                        param_parts = []
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            param_parts.append(self._consume().value)
                        if param_parts:
                            params.append({'name': '*' + ''.join(param_parts), 'type': None})
                    continue
                if tok.type == TokenType.IDENTIFIER:
                    param_name = self._consume(TokenType.IDENTIFIER).value
                    param_type = None
                    # 支持默认值：等于 值 或 = 值
                    if self._current() and ((self._current().type == TokenType.KEYWORD and self._current().value == '等于') or self._current().type == TokenType.EQUALS):
                        self._consume()
                        if self._current() and self._current().type in (TokenType.NUMBER, TokenType.CHINESE_NUM, TokenType.STRING, TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume()
                    params.append({'name': param_name, 'type': param_type})
                elif tok.type == TokenType.KEYWORD:
                    if tok.value == '接收':
                        self._consume(TokenType.KEYWORD, tok.value)
                        continue
                    if tok.value == '返回' or tok.value == '返' or tok.value in _stmt_keywords:
                        break
                    if tok.value == '等于':
                        self._consume(TokenType.KEYWORD, '等于')
                        if self._current() and self._current().type in (TokenType.NUMBER, TokenType.CHINESE_NUM, TokenType.STRING, TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume()
                        continue
                    param_name = self._consume(TokenType.KEYWORD).value
                    params.append({'name': param_name, 'type': None})
                else:
                    break
        
        # 冒号
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
        elif self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 方法体
        body = []
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        while self._current():
            tok = self._current()
            if tok.type == TokenType.DEDENT:
                break
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            else:
                break
        
        return Paragraph(name, params, None, body)
    
    # =============================================================================
    # 类定义解析
    # =============================================================================

    def _peek_bracket_class(self) -> bool:
        """检查是否是《类名》类: 语法"""
        # 当前应该是 LBOOK，检查后跟 IDENTIFIER RBOOK KEYWORD('类')
        if self._peek(1) and self._peek(1).type == TokenType.IDENTIFIER:
            if self._peek(2) and self._peek(2).type == TokenType.RBOOK:
                if self._peek(3) and self._peek(3).type == TokenType.KEYWORD and self._peek(3).value == '类':
                    return True
        return False

    def _parse_bracket_class(self) -> ClassDefinition:
        """解析《类名》类: 语法
        
        示例：
        《计算器》类:
            定义 结果 等于 0。
            《加》方法(x):
                结果 等于 结果 加 x。
        """
        # 《
        self._consume(TokenType.LBOOK)
        # 类名
        name = self._consume(TokenType.IDENTIFIER).value
        # 》
        self._consume(TokenType.RBOOK)
        # 类
        self._consume(TokenType.KEYWORD, '类')
        # 冒号
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
        elif self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 类体
        attributes = []
        methods = []
        
        while self._current():
            tok = self._current()
            
            # DEDENT 结束类体
            if tok.type == TokenType.DEDENT:
                break
            
            # 属性定义：定义 属性名 等于 值。
            if tok.type == TokenType.KEYWORD and tok.value == '定义':
                attr = self._parse_bracket_class_attribute()
                if attr:
                    attributes.append(attr)
                continue
            
            # 方法定义：《方法名》方法(参数)
            if tok.type == TokenType.LBOOK:
                method = self._parse_bracket_class_method()
                if method:
                    methods.append(method)
                continue
            
            # 跳过空行等
            self._consume()
        
        return ClassDefinition(
            name=name,
            attributes=attributes,
            methods=methods,
            base_classes=[]
        )

    def _parse_bracket_class_attribute(self) -> Optional[AttributeDeclaration]:
        """解析《类名》类中的属性定义：定义 属性名 等于 值。"""
        # 定义
        self._consume(TokenType.KEYWORD, '定义')
        
        # 属性名
        name_tok = self._consume(TokenType.IDENTIFIER)
        attr_name = name_tok.value
        
        # 初始值（可选）
        default_value = None
        # 等于
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '等于':
            self._consume(TokenType.KEYWORD, '等于')
            # 初始值
            default_value = self._parse_expr()
        
        # 句号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return AttributeDeclaration(name=attr_name, default_value=default_value)

    def _parse_bracket_class_method(self) -> Optional[MethodDefinition]:
        """解析《类名》类中的方法定义：《方法名》方法(参数)"""
        # 《
        self._consume(TokenType.LBOOK)
        
        # 方法名
        name_tok = self._consume(TokenType.IDENTIFIER)
        method_name = name_tok.value
        
        # 》
        self._consume(TokenType.RBOOK)
        
        # 方法
        kw_tok = self._current()
        if kw_tok and kw_tok.type in (TokenType.KEYWORD, TokenType.IDENTIFIER) and kw_tok.value == '方法':
            self._consume()
        else:
            self._error(f"期望'方法'，但得到 {kw_tok.type if kw_tok else '输入结束'}（附近: '{kw_tok.value if kw_tok else ''}'）", kw_tok.line if kw_tok else 0, kw_tok.col if kw_tok else 0)
        
        # 参数列表 (params)
        params = []
        if self._match(TokenType.LPAREN):
            self._consume(TokenType.LPAREN)
            while not self._match(TokenType.RPAREN):
                tok = self._current()
                if tok and tok.type == TokenType.IDENTIFIER:
                    param_name = self._consume(TokenType.IDENTIFIER).value
                    params.append(Parameter(name=param_name))
                elif tok and tok.type == TokenType.KEYWORD:
                    param_name = self._consume(TokenType.KEYWORD).value
                    params.append(Parameter(name=param_name))
                # 逗号
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                elif self._match(TokenType.RPAREN):
                    break
                else:
                    break
            self._consume(TokenType.RPAREN)
        
        # 冒号
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
        elif self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        # 方法体
        body = []
        while self._current():
            tok = self._current()
            
            # DEDENT 结束方法体
            if tok.type == TokenType.DEDENT:
                break
            
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            else:
                break
        
        return MethodDefinition(
            name=method_name,
            parameters=params,
            body=body,
            is_constructor=(method_name == '初始化' or method_name == '构造')
        )

    def _parse_class_field_declaration(self, access_modifier: str = 'public',
                                       is_static: bool = False) -> AttributeDeclaration:
        """解析类体内的字段声明，转成 AttributeDeclaration。

        支持两种等价写法：
        - `设 名[: 类型] [为/= 值]`（文言体）
        - `令 名 = 值`（C 风格，`_parse_c_var_decl` 产出同样的 VarDecl）

        规范依据：docs/L2_文言体语法规范_v4.0.md:543（设 总数: 数 = 0）、
        :599-600 与 :622-623（设 姓名: 串，无初值）。

        `设`/`令` 写在类体内表达的是类级字段（类字段/类属性），因此统一
        is_static=True，由 code_generator 落在 class 体内，
        而不是塞进自动生成的 __init__。
        """
        tok = self._current()
        if tok is not None and tok.type == TokenType.IDENTIFIER and tok.value == '令':
            node = self._parse_c_var_decl()
        else:
            node = self._parse_set_stmt()
        if not isinstance(node, VarDecl):
            self._error(
                "类体内的'设'/'令'只支持「名[: 类型] [为 值]」形式的字段声明"
                f"（当前写法解析为 {type(node).__name__}）",
                tok.line if tok else 0, tok.col if tok else 0,
                tok.value if tok else None)
        return AttributeDeclaration(
            name=node.name,
            type_annotation=node.type_annotation,
            default_value=node.value,
            access_modifier=access_modifier,
            is_static=True,
        )

    # 类头部引导词：类名 / 基类名 / 接口名的收集循环遇到它们必须停止，
    # 否则 `类 学生 接 可打印:` 会被吞成类名 "学生接可打印"。
    # `接` 是 `实现` 的单字同义词（规范 L2 v4.0 §一 定义与类型四字：类 承 接 配）。
    # v7 单 31-B 追加 `现`：L0 冻结表 docs/language/l0-core.md:58 把 `现` 定为「实现接口」。
    # 不进这张停止词表的后果是**静默错编**：`类 学生 现 可打印:` 被类名收集循环整段吞掉，
    # 编成 `class 学生现可打印:`（类名粘连、接口丢失、编译期零提示），形同当年缺 `接` 的 bug。
    _CLASS_HEADER_STOP_KEYWORDS = ('继承', '承', '实现', '接', '现')

    def _parse_class_ref_list(self) -> List[str]:
        """收集逗号分隔的类型引用名列表（用于 `承`/`继承` 与 `实现`/`接` 之后）。

        - 单个名字可由多个 token 组成（如"可打印"被词法切成"可"+"打印"）；
        - 遇到逗号开始下一个名字；
        - 遇到冒号/句号/换行，或另一个类头部引导词（承/继承/实现/接）时整体结束，
          因此 `类 学生 承 人 接 可打印, 可序列化:` 能被正确切分。
        """
        names: List[str] = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            if (self._current().type == TokenType.KEYWORD
                    and self._current().value in self._CLASS_HEADER_STOP_KEYWORDS):
                break
            parts = []
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                if (self._current().type == TokenType.KEYWORD
                        and self._current().value in self._CLASS_HEADER_STOP_KEYWORDS):
                    break
                parts.append(self._consume().value)
            if parts:
                names.append(''.join(parts))
            else:
                break
            if self._match(TokenType.COMMA):
                self._consume(TokenType.COMMA)
                continue
            break
        return names

    def _parse_class_definition(self) -> ClassDefinition:
        """解析类定义

        语法：
        类 类名。
          属性 属性名。
          属性 属性名。

          构造 参数 参数名 参数名。
            己属性名 为 参数名。

          段落 方法名 参数 参数名。
            方法体。

        或带继承：
        类 类名 继承 父类名。
          ...
        """
        # 类
        self._consume(TokenType.KEYWORD, '类')

        # 类名（支持IDENTIFIER和KEYWORD，可能由多个token组成如"空类"）
        name_parts = []
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 检查是否遇到类头部引导词（继承/承/实现/接/接口）。
                #
                # Bug 根因：原先停止词表缺少单字 `接`，于是 `类 学生 接 可打印:`
                # 的 `接` 与 `可打印` 被类名收集循环吞掉，静默错译成
                # `class 学生接可打印:`（既没有基类也没有接口）。
                #
                # name_parts 非空才停止：类名本身可以以这些字开头（如 `类 接口测试:`），
                # 空名字停止会把类名整段丢掉。
                if (name_parts
                        and self._current().type == TokenType.KEYWORD
                        and self._current().value in self._CLASS_HEADER_STOP_KEYWORDS):
                    break
                # 检查是否遇到句号或冒号
                if self._current().type in (TokenType.PERIOD, TokenType.COLON):    
                    break
                name_parts.append(self._consume().value)
        else:
            self._error(f"期望类名，但得到 {name_tok.type if name_tok else '输入结束'}")
        class_name = ''.join(name_parts)

        # 泛型参数？（可选）如：类 栈[T]:
        generic_params = []
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                param_name = self._consume().value
                generic_params.append(param_name)
                if self._current() and self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                else:
                    break
            if self._current() and self._current().type == TokenType.RBRACKET:
                self._consume(TokenType.RBRACKET)
            else:
                self._error(f"期望右方括号 ']'，但得到 {self._current()}")

        # 继承？（可选）支持逗号分隔多个基类：类 学生 承 人, 甲:
        base_classes = []
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('继承', '承'):
            self._consume(TokenType.KEYWORD, self._current().value)
            base_classes = self._parse_class_ref_list()
            if not base_classes:
                tok = self._current()
                self._error(f"期望父类名，但得到 {tok.type if tok else '输入结束'}",
                            tok.line if tok else 0, tok.col if tok else 0)

        # 实现接口（可选）。`接` 是 `实现` 的同义词（规范 L2 v4.0 §一、把
        # `类 承 接 配` 列为四字定义词）；`现` 是 L0 冻结表 :58 承诺的同义词
        # （v7 单 31-B）。支持逗号分隔多接口，也支持与 `承` 同行组合：
        # 类 X 承 Y 接 A, B: / 类 X 承 Y 现 A, B:
        interfaces = []
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('实现', '接', '现'):
            self._consume(TokenType.KEYWORD, self._current().value)
            interfaces = self._parse_class_ref_list()
            if not interfaces:
                tok = self._current()
                self._error(f"期望接口名，但得到 {tok.type if tok else '输入结束'}",
                            tok.line if tok else 0, tok.col if tok else 0)

        # 句号或冒号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        elif self._current() and self._current().type == TokenType.COLON:       
            self._consume(TokenType.COLON)
        else:
            self._error(f"期望句号或冒号，但得到 {self._current()}")       

        # 类体
        attributes = []
        methods = []
        nested_classes = []

        # 解析类体（依赖 INDENT/DEDENT 结构）
        # 首先跳过 NEWLINE，然后检查是否有 INDENT（表示有类体）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            # A2-5：记下本类体的缩进宽度。INDENT/DEDENT 的 value 都是缩进层级
            # （lexer.py:690 / :695，DEDENT 带的是**退回到的**层级），嵌套类要靠它
            # 才能分清「方法体结束」和「本类结束」。
            body_indent = self._current().value
            self._consume(TokenType.INDENT)  # 消耗 INDENT
            
            while self._current():
                tok = self._current()

                # DEDENT 处理
                if tok.type == TokenType.DEDENT:
                    if tok.value == 0:
                        # 完全结束类体
                        self._consume(TokenType.DEDENT)
                        break
                    elif isinstance(body_indent, int) and tok.value < body_indent:
                        # A2-5：退到比本类体更浅的层级 → 本类（嵌套类）结束。
                        # **不消耗**：这个 DEDENT 属于外层类体，留给外层的循环处理，
                        # 否则外层会少收一个 DEDENT 而把后续成员当成本类的成员吞掉。
                        # 顶层类走不到这里（它只可能 DEDENT 到 0，已被上面接住）。
                        break
                    else:
                        # 中间级别的 DEDENT（方法体结束等），消耗后继续
                        self._consume(TokenType.DEDENT)
                        continue

                # 跳过 NEWLINE（类体内语句之间的换行）
                if tok.type == TokenType.NEWLINE:
                    self._consume(TokenType.NEWLINE)
                    continue

                # 访问修饰符检测
                #
                # v7 单 31-C：`私`/`护` 是 L0 冻结表（docs/language/l0-core.md:120-128
                # 「## 修饰（4字）」）承诺的 私有 / 受保护，`src/` 从未落地——旧行为是
                # 类体兜底分支硬报「类体内不支持的成员声明：'私'」。
                # 判据用 **IDENTIFIER 而非 KEYWORD**，与下方 `性`/`构` 同一范式（理由见
                # :3963 起那段注释）：这三个字都是高频构词字（全仓词首 护 23 / 私 80 /
                # 静 121 处），进 `ALL_KEYWORDS` 就得在词法层动最长匹配，风险远高于收益；
                # 而「类体成员位置的裸 IDENTIFIER」此前**一律落到 else 报错**，所以在这里
                # 加分支只可能把「原本报错」变成「能解析」，不可能改动任何既有能过的语义。
                access_modifier = 'public'
                is_static = False
                if tok.type == TokenType.KEYWORD and tok.value == '私有':
                    access_modifier = 'private'
                    self._consume(TokenType.KEYWORD, '私有')
                    tok = self._current()
                elif tok.type == TokenType.KEYWORD and tok.value == '公有':
                    access_modifier = 'public'
                    self._consume(TokenType.KEYWORD, '公有')
                    tok = self._current()
                elif tok.type == TokenType.KEYWORD and tok.value == '保护':
                    access_modifier = 'protected'
                    self._consume(TokenType.KEYWORD, '保护')
                    tok = self._current()
                elif tok.type == TokenType.IDENTIFIER and tok.value == '私':
                    access_modifier = 'private'
                    self._consume(TokenType.IDENTIFIER, '私')
                    tok = self._current()
                elif tok.type == TokenType.IDENTIFIER and tok.value == '护':
                    access_modifier = 'protected'
                    self._consume(TokenType.IDENTIFIER, '护')
                    tok = self._current()
                elif tok.type == TokenType.IDENTIFIER and tok.value == '公':
                    # v7 单 31-F 补上同族第四个字（l0-core.md:127 `公`=公共）。
                    # 与上面 `私`/`护` 同一范式、同一理由：31-C 落地时 `公` 因「全仓
                    # A/B 有 5 文件切法漂移」被留下，但那 5 例是**范式 B（进关键字表）**
                    # 的代价（`CNF公式` 会切成 `CNF`+`公式`）；走这里的范式 A 后代价归零。
                    access_modifier = 'public'
                    self._consume(TokenType.IDENTIFIER, '公')
                    tok = self._current()


                # 静态修饰符检测（`静` 同上，L0 冻结表 :128 承诺的 静态）
                if tok.type == TokenType.KEYWORD and tok.value == '静态':
                    is_static = True
                    self._consume(TokenType.KEYWORD, '静态')
                    tok = self._current()
                elif tok.type == TokenType.IDENTIFIER and tok.value == '静':
                    is_static = True
                    self._consume(TokenType.IDENTIFIER, '静')
                    tok = self._current()


                # 类方法修饰符检测
                is_classmethod = False
                if tok.type == TokenType.KEYWORD and tok.value == '类方法':
                    is_classmethod = True
                    self._consume(TokenType.KEYWORD, '类方法')
                    tok = self._current()

                # 特性（property）修饰符检测
                is_property = False
                if tok.type == TokenType.KEYWORD and tok.value == '特性':
                    is_property = True
                    self._consume(TokenType.KEYWORD, '特性')
                    tok = self._current()

                # 属性声明（支持公有、私有、保护和静态）
                # L-021 修复（范式 A）：`属性` 从 KEYWORDS_CLASS 移除后词法层
                # 不再切 KEYWORD，这里同时接受 IDENTIFIER。仿 `性` 分支（4398 行）。
                if ((tok.type == TokenType.KEYWORD and tok.value == '属性') or
                    (tok.type == TokenType.IDENTIFIER and tok.value == '属性')):
                    attr = self._parse_attribute_declaration()
                    attr.access_modifier = access_modifier
                    attr.is_static = is_static
                    attributes.append(attr)
                elif tok.type == TokenType.KEYWORD and tok.value == '私属性':
                    attr = self._parse_attribute_declaration()
                    attr.access_modifier = 'private'
                    attributes.append(attr)

                # L0 v4.0 单字成员声明：`性` ≡ 属性，`构` ≡ 构造
                # （examples/L0_core/06_类_面向对象.light 用的就是这一套写法）
                #
                # 判据用 IDENTIFIER 而不是 KEYWORD，是**有意为之**：`性`/`构` 是
                # 高频构词字（性能、性别、结构、构建、构造…），一旦加进
                # keywords.ALL_KEYWORDS 就会在词法层把大量标识符切碎，血溅半径
                # 远大于本单收益。实测（.scratch token 探针）这两个字在类体成员
                # 位置本来就是独立 IDENTIFIER token，按位置识别即可，词法零改动。
                #
                # 安全性：类体成员位置上的 IDENTIFIER 此前一律落到本 elif 链末尾
                # 的 self._error（"类体内不支持的成员声明"），所以这两个分支只能
                # 把「原本报错」变成「能解析」，不可能改变任何既有能过的语义。
                elif tok.type == TokenType.IDENTIFIER and tok.value == '性':
                    attr = self._parse_attribute_declaration()
                    attr.access_modifier = access_modifier
                    attr.is_static = is_static
                    attributes.append(attr)
                elif tok.type == TokenType.IDENTIFIER and tok.value == '构':
                    method = self._parse_method_definition(is_constructor=True)
                    methods.append(method)


                # 构造函数
                elif tok.type == TokenType.KEYWORD and tok.value == '构造':
                    method = self._parse_method_definition(is_constructor=True)
                    methods.append(method)

                # A2-5：嵌套类。类体内 `类 消息：` 递归走同一个类定义解析器。
                # 改动前这里没有分支，`类` 落到链尾 self._error（「类体内不支持的
                # 成员声明：'类'」）并级联出一串缩进错（实测一段 10 行的
                # `类 会话/类 消息` 报 10 个错）。递归安全性：本方法只用局部状态
                # （attributes/methods/nested_classes/body_indent 都是局部变量），
                # 嵌套层数由缩进天然限制。
                elif tok.type == TokenType.KEYWORD and tok.value == '类':
                    nested_classes.append(self._parse_class_definition())


                # 异步方法：异步 段落/函数/段 方法名 ...
                #
                # 类体内 `异步 段落 名字():` 以前落到链尾 self._error（「类体内不支持
                # 的成员声明：'异步'」），导致 stdlib/流式.light 的四个异步读腿只能甩到
                # 模块级。这里复用 _parse_async_paragraph（返回 Paragraph + modifiers
                # 含 '异步'），code_generator 的 _generate_method 通过 getattr(method,
                # 'modifiers', []) 检测 '异步' 来发射 async def。
                #
                # 安全性：此前 `异步` 在类体内一律落到 else 报错，加分支只可能把
                # 「原本报错」变成「能解析」。名字限制裁决（不许以「异步」开头）
                # 在 _parse_paragraph_v2 里已有，这里不放开。
                elif tok.type == TokenType.KEYWORD and tok.value in ('异步', '异'):
                    method = self._parse_async_paragraph()
                    method.access_modifier = access_modifier
                    method.is_static = is_static
                    method.is_classmethod = is_classmethod
                    methods.append(method)

                # 方法定义（支持公有、私有、保护和静态）
                # 单字 `段` 与 `段落`/`函数` 同义（parser_core.PARAGRAPH_KEYWORDS）。
                # Bug 根因：这里原先只认 ('函数','段落')，L0 单字 `段` 落到末尾的
                # `else: break`，类体提前结束，剩余成员被丢回模块级当独立语句解析，
                # 于是 `类 人:\n 段 介绍():` 静默错译成模块级 `def 介绍():`。
                elif self._is_paragraph_kw(tok):
                    method = self._parse_method_definition(is_constructor=False)
                    method.access_modifier = access_modifier
                    method.is_static = is_static
                    method.is_classmethod = is_classmethod
                    methods.append(method)
                elif tok.type == TokenType.KEYWORD and tok.value == '私段落':
                    method = self._parse_method_definition(is_constructor=False)
                    method.access_modifier = 'private'
                    methods.append(method)

                # 类字段声明：设 名[: 类型] [为/= 值] / 令 名 = 值（C 风格同义写法）
                # 规范 docs/L2_文言体语法规范_v4.0.md:543、:599-600、:622-623
                elif ((tok.type == TokenType.KEYWORD and tok.value == '设')
                        or (tok.type == TokenType.IDENTIFIER and tok.value == '令')):
                    attr = self._parse_class_field_declaration(
                        access_modifier=access_modifier, is_static=is_static)
                    attributes.append(attr)

                # 空体占位：过 / 跳过 / 继续 / pass（类体内不产生成员）
                elif ((tok.type == TokenType.KEYWORD and tok.value in ('过', '跳过', '继续'))
                        or (tok.type == TokenType.IDENTIFIER and tok.value == 'pass')):
                    self._consume()
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    continue

                # 结束标记（方法定义结束后的"结束。"）
                elif tok.value == '结束' and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    self._consume()
                    # 可选句号
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    continue

                # 孤立句号：跳过
                elif tok.type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                    continue

                # 装饰器：@静态方法、@类方法、@特性、@抽象 等
                elif tok.type == TokenType.AT:
                    decorator = self._parse_decorator()
                    if decorator is not None:
                        # 内置装饰器返回 DecoratorDefinition（含被装饰的段落）
                        from ast_nodes_v3 import DecoratorDefinition
                        if isinstance(decorator, DecoratorDefinition):
                            method = decorator.paragraph
                            if method is not None:
                                method.access_modifier = access_modifier
                                if decorator.decorator_name == '静态方法':
                                    method.is_static = True
                                elif decorator.decorator_name == '类方法':
                                    method.is_classmethod = True
                                elif decorator.decorator_name == '特性':
                                    method.is_property = True
                                elif decorator.decorator_name == '抽象':
                                    method.is_abstract = True
                                methods.append(method)

                # 其他情况：类体内不支持的成员声明。
                #
                # 这里原先是 `break`，会静默结束类体并把剩余成员泄漏到模块级
                # （方法变模块函数、字段变模块变量），且全程 PARSE-OK 无任何提示。
                # 静默错译远比报错危险，故改为明确报错。
                # 注意：类体的正常收尾走上面的 DEDENT 分支，不经过此处。
                else:
                    self._error(
                        f"类体内不支持的成员声明：'{tok.value}'"
                        f"（类体内可用：属性/私属性/性/设/构造/构/函数/段落/段/私段落/类/@装饰器/过/结束；"
                        f"修饰符前缀：私有/公有/保护/静态/类方法/特性，或单字 私/公/护/静）",


                        tok.line, tok.col, tok.value)

        # A2-5：只有真有嵌套类时才换成子类节点。`ast_nodes_v3.ClassDefinition`
        # 不在 A2 可改文件之列，所以嵌套字段挂在本文件的子类上（见文件头部
        # `ClassDefinitionWithNested`）——**无嵌套时必须还回原类**，否则给基类
        # 传 `nested_classes=` 会 TypeError。
        node_cls = ClassDefinitionWithNested if nested_classes else ClassDefinition
        kwargs = {}
        if nested_classes:
            kwargs['nested_classes'] = nested_classes
        return node_cls(
            name=class_name,
            attributes=attributes,
            methods=methods,
            base_classes=base_classes,
            generic_params=generic_params,
            interfaces=interfaces,
            **kwargs,
        )

    def _parse_attribute_declaration(self) -> AttributeDeclaration:
        """解析属性声明

        语法：属性 属性名 [：类型] [等于/为 默认值] [。]
             性  属性名 [：类型] [等于/为 默认值] [。]   ← L0 v4.0 单字写法，同义

        A6 补齐两处（补齐前都是硬报错，见工单 A6）：
        · `为` 与 `等于` 同义。光明其余各处赋值一律两词通用（`设 甲 为 1`／
          `令 甲 = 1`），只有属性默认值单认 `等于`：`属性 横 为 0。` 在属性名
          收集处于 `为` 停下、默认值分支又不认 `为`，`为` 掉回类体循环，报
          「类体内不支持的成员声明：'为'」。
        · `：类型` 之前被属性名收集循环的 COLON 分支跳出后无人接手，同样掉回
          类体循环报错；而 AttributeDeclaration 早就有 type_annotation 槽位，
          类级字段（`设 名: 类型 为 值`）也一直在用它。
        """
        # 属性关键字消费
        # `性`/`属性` 在词法层都是 IDENTIFIER（有意不升为保留字，
        # 见类体分发处 4386-4397 行注释）。L-021 后 `属性` 从 KEYWORDS_CLASS
        # 移除，也走 IDENTIFIER 路径。保留 KEYWORD fallback 以防旧缓存。
        cur = self._current()
        if cur and cur.type == TokenType.IDENTIFIER and cur.value in ('性', '属性'):
            self._consume()
        else:
            self._consume(TokenType.KEYWORD, '属性')


        # 属性名（支持多字标识符，如"余额"被拆分为"余"+"额"）
        attr_name_parts = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 遇到分隔符时停止
            if self._current().type == TokenType.PERIOD:
                break
            if self._current().type == TokenType.NEWLINE:
                break
            if self._current().type == TokenType.COLON:
                break
            # 赋值关键字（等于/为）不是属性名的一部分，停止收集以便解析默认值。
            #
            # Bug 根因：属性名收集循环原先只处理 PERIOD/NEWLINE/COLON 三种分隔符，
            # 会把「等于/为」当作属性名的一部分吞掉，导致 docstring 声明支持的
            # "属性 名称 等于 默认值"（如 class_complete.light 的 属性 品种 等于 "金毛"）
            # 解析失败，级联产生大量"无法识别的语法元素"错误。
            #
            # 修复方案：遇到 等于/为 立即停止收集属性名，交由下方"默认值（可选）"
            # 逻辑继续解析 等于 默认值 部分。
            if self._current().value in ('等于', '为'):
                break
            attr_name_parts.append(self._current().value)
            self._consume()
        if not attr_name_parts:
            name_tok = self._consume(TokenType.IDENTIFIER)
            attr_name = name_tok.value
        else:
            attr_name = ''.join(attr_name_parts)

        # 类型标注（可选）：属性 次数：整数
        type_annotation = None
        if self._current() and self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            type_annotation = self._parse_type_annotation()

        # 默认值（可选）：等于 与 为 同义
        default_value = None
        if (self._current() and self._current().type == TokenType.KEYWORD
                and self._current().value in ('等于', '为')):
            self._consume()
            default_value = self._parse_expr()

        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        return AttributeDeclaration(name=attr_name,
                                    type_annotation=type_annotation,
                                    default_value=default_value)

    def _parse_method_definition(self, is_constructor=False) -> MethodDefinition:
        """解析方法定义

        语法：
        构造 接收 参数名 参数名：
          方法体

        或：
        段落 方法名 接收 参数名 参数名：
          方法体

        或：
        段落 方法名 接收 参数名 参数名：
          方法体
        """
        method_name = None

        if is_constructor:
            # 构造 / 构（L0 v4.0 单字写法，同义）
            # `构` 在词法层是 IDENTIFIER，理由同 `性`（见类体成员分发处注释）。
            if (self._current() and self._current().type == TokenType.IDENTIFIER
                    and self._current().value == '构'):
                self._consume()
            else:
                self._consume(TokenType.KEYWORD, '构造')
            method_name = '__init__'

        else:
            # 段落 / 函数 / 单字 段（三者同义，见 parser_core.PARAGRAPH_KEYWORDS）
            if self._match_paragraph_kw():
                self._consume_paragraph_kw()
            else:
                tok = self._current()
                self._error(f"期望'函数'（或兼容写法'段落'/'段'），但得到'{tok.value if tok else '输入结束'}'",
                                tok.line if tok else 0, tok.col if tok else 0, tok.value if tok else None)
            
            # 方法名可能是IDENTIFIER或KEYWORD（如"加""减""乘"）
            name_tok = self._current()
            if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                method_name = name_tok.value
                self._consume()
            else:
                self._error(f"期望方法名，但得到 {name_tok.type if name_tok else '输入结束'}", name_tok.line if name_tok else 0, name_tok.col if name_tok else 0, name_tok.value if name_tok else None)

        # 泛型参数？（可选）如：段落 映射[T, U] 接收 列表：
        generic_params = []
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                param_name = self._consume().value
                generic_params.append(param_name)
                if self._current() and self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                else:
                    break
            if self._current() and self._current().type == TokenType.RBRACKET:
                self._consume(TokenType.RBRACKET)

        # 参数列表（支持"参数"/"接收"关键字或括号形式）
        parameters = []
        if self._current() and self._current().type == TokenType.KEYWORD:
            kw = self._current().value
            if kw == '接收':
                self._consume(TokenType.KEYWORD)

                # 收集参数（支持多字参数名和逗号分隔，支持*args/**kwargs）
                while self._current():
                    ptok = self._current()
                    # 支持 *args / **kwargs
                    if ptok.type == TokenType.STAR:
                        self._consume(TokenType.STAR)
                        # 检查是否 ** (双星号)
                        if self._current() and self._current().type == TokenType.STAR:
                            self._consume(TokenType.STAR)
                            # 收集参数名
                            param_parts = []
                            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                                param_parts.append(self._current().value)
                                self._consume()
                            if param_parts:
                                param_name = '**' + ''.join(param_parts)
                                parameters.append(Parameter(name=param_name))
                        else:
                            param_parts = []
                            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                                param_parts.append(self._current().value)
                                self._consume()
                            if param_parts:
                                param_name = '*' + ''.join(param_parts)
                                parameters.append(Parameter(name=param_name))
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                        continue
                    if ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        param_parts = []
                        # 收集参数名，但遇到"等于"时停止
                        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD) \
                                and self._current().value != '等于':
                            param_parts.append(self._current().value)
                            self._consume()
                        param_name = ''.join(param_parts)
                        param = Parameter(name=param_name)
                        parameters.append(param)
                        # 支持类型注解：参数名: 类型（含泛型 列表<整数>）
                        # 仅当冒号后紧跟类型名（且非换行）时才视为类型注解；
                        # 否则（如「构造 接收 初值：」）该冒号是方法体的体冒号
                        if self._current() and self._current().type == TokenType.COLON \
                                and self._peek(1) and self._peek(1).type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                            self._consume(TokenType.COLON)
                            param.type_annotation = self._parse_type_annotation()
                        # 支持默认值：等于 值 或 = 值
                        default_value = None
                        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '等于':
                            self._consume(TokenType.KEYWORD, '等于')
                            default_tok = self._current()
                            if default_tok and default_tok.type in (TokenType.NUMBER, TokenType.STRING, TokenType.IDENTIFIER, TokenType.KEYWORD):
                                val = self._consume().value
                                if default_tok.type == TokenType.NUMBER:
                                    val_str = str(val)
                                    default_value = NumberLiteral(float(val_str) if '.' in val_str else int(val_str))
                                elif default_tok.type == TokenType.STRING:
                                    default_value = StringLiteral(val)
                                else:
                                    # 翻译真/假/空为 Python True/False/None
                                    if val == '真':
                                        default_value = Identifier('True')
                                    elif val == '假':
                                        default_value = Identifier('False')
                                    elif val == '空':
                                        default_value = Identifier('None')
                                    else:
                                        default_value = Identifier(val)
                        elif self._current() and self._current().type == TokenType.EQUALS:
                            self._consume(TokenType.EQUALS)
                            default_tok = self._current()
                            if default_tok and default_tok.type in (TokenType.NUMBER, TokenType.STRING, TokenType.IDENTIFIER, TokenType.KEYWORD):
                                val = self._consume().value
                                if default_tok.type == TokenType.NUMBER:
                                    val_str = str(val)
                                    default_value = NumberLiteral(float(val_str) if '.' in val_str else int(val_str))
                                elif default_tok.type == TokenType.STRING:
                                    default_value = StringLiteral(val)
                                else:
                                    # 翻译真/假/空为 Python True/False/None
                                    if val == '真':
                                        default_value = Identifier('True')
                                    elif val == '假':
                                        default_value = Identifier('False')
                                    elif val == '空':
                                        default_value = Identifier('None')
                                    else:
                                        default_value = Identifier(val)
                        if default_value is not None:
                            param.default_value = default_value
                        # 跳过逗号
                        if self._match(TokenType.COMMA):
                            self._consume(TokenType.COMMA)
                    else:
                        break
        elif self._current() and self._current().type == TokenType.LPAREN:
            # 括号参数形式：(参数1, 参数2, ...)
            self._consume(TokenType.LPAREN)
            while self._current() and self._current().type != TokenType.RPAREN:
                if self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                # 收集多 token 参数名
                param_parts = []
                while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_parts.append(self._current().value)
                    self._consume()
                if param_parts:
                    param = Parameter(name=''.join(param_parts))
                    # 支持类型注解：参数名: 类型（含泛型 列表<整数>）
                    if self._current() and self._current().type == TokenType.COLON \
                            and self._peek(1) and self._peek(1).type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        self._consume(TokenType.COLON)
                        param.type_annotation = self._parse_type_annotation()
                    parameters.append(param)
                else:
                    break
            if self._current() and self._current().type == TokenType.RPAREN:
                self._consume(TokenType.RPAREN)

        # 返回类型（可选）：返回 类型 或 -> 类型
        return_type = None
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '返回':
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        elif self._current() and self._current().type == TokenType.ARROW:
            self._consume(TokenType.ARROW)
            return_type = self._parse_type_annotation()

        # 句号或冒号
        tok_colon = self._current()
        if tok_colon and tok_colon.type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        elif tok_colon and tok_colon.type == TokenType.COLON:
            self._consume(TokenType.COLON)
        else:
            self._error(f"期望句号或冒号，但得到 {tok_colon.type if tok_colon else '输入结束'}", tok_colon.line if tok_colon else 0, tok_colon.col if tok_colon else 0, tok_colon.value if tok_colon else None)

        # 方法体
        body = []
        
        # 消耗方法体的 INDENT（如果有）
        # 先跳过 NEWLINE，再找 INDENT
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)
        
        while self._current():
            tok = self._current()

            # DEDENT 结束方法体
            if tok.type == TokenType.DEDENT:
                break

            # 跳过 NEWLINE（方法体内语句之间的换行）
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue

            # 解析语句
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            else:
                break

        return MethodDefinition(
            name=method_name,
            parameters=parameters,
            body=body,
            return_type=return_type,
            is_constructor=is_constructor,
            generic_params=generic_params,
        )

    def _is_interface_char_header(self) -> bool:
        """前视：当前的裸 `约` 是否是「接口声明头」而不是普通标识符。

        判据是「本行（到 NEWLINE 为止）里出现冒号」，即 L0 冻结表承诺的
        `约 接口名：` / `约 接口名 继承 父：` 形态。为什么必须带这条守卫：
        `约 等于 1。` 这类以 `约` 为变量名的语句今天是合法的（走赋值分支），
        无条件把裸 `约` 当接口关键字会把能跑的代码改坏。

        反过来，带冒号的那个形态今天**一律硬报错**（实测与从不进任何关键字表的
        对照字 `鱼` 报错逐字相同，见工单 31-E），所以此处返回 True 的输入集合
        与「原本能编过的输入集合」不相交——这正是范式 A 成立的前提。
        """
        idx = self.pos + 1  # 跳过 `约` 自身
        # 名字至少要有一个 token，且不能立刻就是冒号（`约：` 不是接口声明）
        if idx >= len(self.tokens):
            return False
        if self.tokens[idx].type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            return False
        while idx < len(self.tokens):
            t = self.tokens[idx]
            if t.type == TokenType.COLON:
                return True
            if t.type in (TokenType.NEWLINE, TokenType.PERIOD, TokenType.EOF):
                return False
            idx += 1
        return False

    def _parse_interface_definition(self) -> InterfaceDefinition:
        """解析接口定义

        语法：
        接口/协议 名称：
          段落 方法名 参数 参数名 返回 类型。
          段落 方法名(参数) 返回 类型。

        或带继承：
        接口/协议 名称 继承 父接口1, 父接口2：
          ...
        """
        # 接口 / 接 / 协议（支持 '接口'、'接' 和 '协议' 关键字）
        # v7 单 31-F：另接受裸 IDENTIFIER `约`（范式 A，词法层零改动）。
        # 调用方 `_parse_statement` 已用 `_is_interface_char_header()` 前视过，
        # 这里只负责把那个 token 吃掉。
        trait_kw = self._current()
        if trait_kw and trait_kw.type == TokenType.KEYWORD and trait_kw.value in ('接口', '接', '协议'):
            self._consume(TokenType.KEYWORD, trait_kw.value)
        elif trait_kw and trait_kw.type == TokenType.IDENTIFIER and trait_kw.value == '约':
            self._consume(TokenType.IDENTIFIER, '约')
        else:
            self._error(f"期望'接口'或'协议'，但得到 {trait_kw.type if trait_kw else '输入结束'}")

        # 接口名（可能由多个token组成，与类名类似）
        name_parts = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 检查是否遇到"继承"关键字或冒号/句号
            if self._current().type == TokenType.KEYWORD and self._current().value in ('继承', '承'):
                break
            if self._current().type in (TokenType.COLON, TokenType.PERIOD):        
                break
            name_parts.append(self._consume().value)
        name = ''.join(name_parts)
        if not name:
            self._error(f"期望接口名，但得到 {self._current().type if self._current() else '输入结束'}")

        # 继承（可选）
        super_interfaces = []
        if self._match(TokenType.KEYWORD, '继承') or self._match(TokenType.KEYWORD, '承'):
            self._consume(TokenType.KEYWORD, self._current().value)
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 收集多 token 名称（如"可打印"被拆为"可"+"打印"）
                parts = []
                while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 遇到逗号、冒号、句号时停止
                    if self._current().type in (TokenType.COLON, TokenType.PERIOD):
                        break
                    parts.append(self._consume().value)
                if parts:
                    super_interfaces.append(''.join(parts))
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                else:
                    break

        # 冒号或句号
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
        elif self._match(TokenType.PERIOD):
            self._consume(TokenType.PERIOD)

        # 接口体
        methods = []
        properties = []
        
        # 跳过 NEWLINE（冒号后可能有换行）
        while self._current() and self._current().type == TokenType.NEWLINE:
            self._consume(TokenType.NEWLINE)
        
        # 解析接口体（依赖 INDENT/DEDENT 结构）
        # 首先检查是否有 INDENT（表示有接口体）
        if self._current() and self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)  # 消耗 INDENT
            
            while self._current():
                tok = self._current()

                # DEDENT 结束接口体
                if tok.type == TokenType.DEDENT:
                    self._consume(TokenType.DEDENT)  # 消耗这个 DEDENT
                    break

                # 跳过空行
                if tok.type == TokenType.NEWLINE:
                    self._consume(TokenType.NEWLINE)
                    continue

                # 方法签名：函数/段落/段 方法名 接收 参数名 返回 类型
                # 单字 `段` 与 `段落`/`函数` 同义。原先只认 ('函数','段落')，
                # `接 可打印:\n 段 字符串化() -> 串` 会落进末尾的 `else: break`，
                # 接口体提前结束，成员被丢回模块级静默错译成 `段()` + `字符串化()(串)`。
                if self._is_paragraph_kw(tok):
                    sig = self._parse_method_signature()
                    methods.append(sig)

                # 属性声明：属性 名称（可选类型）
                # L-021 修复：`属性` 从 KEYWORDS_CLASS 移除后走 IDENTIFIER 路径
                elif ((tok.type == TokenType.KEYWORD and tok.value == '属性') or
                      (tok.type == TokenType.IDENTIFIER and tok.value == '属性')):
                    attr = self._parse_attribute_declaration()
                    properties.append(attr)

                # 空体占位：过 / 跳过 / 继续 / pass
                elif ((tok.type == TokenType.KEYWORD and tok.value in ('过', '跳过', '继续'))
                        or (tok.type == TokenType.IDENTIFIER and tok.value == 'pass')):
                    self._consume()
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    continue

                # 结束标记
                elif tok.value == '结束' and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    self._consume()
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    continue

                # 孤立句号：跳过
                elif tok.type == TokenType.PERIOD:
                    self._consume(TokenType.PERIOD)
                    continue

                # 其他情况：接口体内不支持的成员声明。
                # 原先是 `break`（静默结束接口体，成员泄漏到模块级），改为明确报错。
                # 注意：接口体的正常收尾走上面的 DEDENT 分支，不经过此处。
                else:
                    self._error(
                        f"接口体内不支持的成员声明：'{tok.value}'"
                        f"（接口体内可用：函数/段落/段/属性/过/结束）",
                        tok.line, tok.col, tok.value)

        return InterfaceDefinition(name, methods, properties, super_interfaces) 

    # 方法名收集时遇到这些关键字必须停止：它们是参数/返回值的引导词，
    # 不能被吞进方法名。否则「段落 解码 接收 raw」会得到方法名"解码接收raw"。
    _METHOD_NAME_STOP_KEYWORDS = ('返回', '接收', '参数', '需要')

    def _parse_method_signature(self) -> MethodSignature:
        """解析接口/协议中的方法。

        既支持抽象声明，也支持带默认实现的方法体：

        抽象声明（实现类必须覆写）：
            段落 方法名 接收 参数名 返回 类型。
            段落 方法名(参数) 返回 类型。
            段落 方法名。

        默认实现（实现类可直接继承）：
            段落 方法名 接收 参数名：
                语句。
        """
        # 消耗 函数 / 段落 / 单字 段（三者同义）
        if self._match_paragraph_kw():
            self._consume_paragraph_kw()
        else:
            tok = self._current()
            self._error(f"期望'函数'（或兼容写法'段落'/'段'），但得到'{tok.value if tok else '输入结束'}'",
                        tok.line if tok else 0, tok.col if tok else 0)

        # 方法名（可能由多个token组成，如"从JSON"被拆为从+JSON）
        name_parts = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 遇到LPAREN、参数/返回引导词、句号、冒号等停止
            if self._current().type == TokenType.LPAREN:
                break
            if (self._current().type == TokenType.KEYWORD
                    and self._current().value in self._METHOD_NAME_STOP_KEYWORDS):
                break
            if self._current().type in (TokenType.PERIOD, TokenType.COLON):
                break
            name_parts.append(self._consume().value)
        name = ''.join(name_parts)
        if not name:
            self._error(f"期望方法名")

        # 参数
        params = []

        # 括号参数：(参数1, 参数2, ...)
        if self._match(TokenType.LPAREN):
            self._consume(TokenType.LPAREN)
            while self._current() and self._current().type != TokenType.RPAREN: 
                if self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                param_tok = self._current()
                if param_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD): 
                    param_name = self._consume().value
                    # 可选类型注解
                    param_type = None
                    if self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    params.append(Parameter(param_name, param_type))
                else:
                    break
            self._consume(TokenType.RPAREN)
        # 无括号参数：接收 参数1, 参数2 / 参数 参数1, 参数2
        elif (self._current() and self._current().type == TokenType.KEYWORD
                and self._current().value in ('接收', '参数', '需要')):
            self._consume(TokenType.KEYWORD, self._current().value)
            while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                # 「返回」引导返回类型，不是参数名
                if (self._current().type == TokenType.KEYWORD
                        and self._current().value == '返回'):
                    break
                param_name = self._consume().value
                param_type = None
                # 类型注解：参数名: 类型（注意与块起始冒号区分——
                # 块冒号后面跟的是换行，类型注解后面跟的是类型名）
                if self._match(TokenType.COLON):
                    nxt = self._peek(1)
                    if nxt and nxt.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                params.append(Parameter(param_name, param_type))
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
                    continue
                break

        # 返回类型（可选）：返回 类型 / -> 类型
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        elif self._current() and self._current().type == TokenType.ARROW:
            # `段 字符串化() -> 串`（规范写法）。原先只认关键字 `返回`，
            # ARROW 落到接口体循环的兜底分支被当成"不支持的成员声明"。
            # 类方法路径早已支持 ARROW（本文件 :3957-3958），此处对齐。
            self._consume(TokenType.ARROW)
            return_type = self._parse_type_annotation()

        # 默认实现方法体（可选）：冒号 + 缩进块
        body = None
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
            body = self._parse_body()
            return MethodSignature(name, params, return_type, body)

        # 句号（可选）—— 纯抽象声明
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        return MethodSignature(name, params, return_type, None)

    def _parse_match_stmt(self) -> MatchStmt:
        """解析模式匹配语句

        语法：
        匹配 值：
          情况 模式1：
            语句。
          情况 模式2：
            语句。
          情况 _：
            语句。
        """
        # 匹配 / 配
        self._consume(TokenType.KEYWORD, self._current().value)

        # 匹配的值（表达式）
        subject = self._parse_expr()

        # 冒号
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)

        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        # 解析各个情况
        cases = []
        while self._current():
            tok = self._current()

            # 跳过 NEWLINE
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue

            # 跳过 INDENT（匹配块开始时的缩进标记）
            if tok.type == TokenType.INDENT:
                self._consume(TokenType.INDENT)
                continue

            # DEDENT：可能是 case body 结束后的缩进回退，检查后面是否还有"情况"
            if tok.type == TokenType.DEDENT:
                # 先消费当前 DEDENT
                self._consume(TokenType.DEDENT)
                # 检查后面是否还有 NEWLINE 或另一个 DEDENT
                while self._current() and self._current().type == TokenType.NEWLINE:
                    self._consume(TokenType.NEWLINE)
                # 如果下一个 token 是"情况"/"例"，说明还有更多 case，继续循环
                if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('情况', '例'):
                    continue
                # 默认分支（其他/否）也要继续，否则 `其他:` 会落回顶层语句解析
                if self._is_match_default_lead(self._current()):
                    continue
                # 否则匹配块结束
                break

            # 情况分支（'例' 是 v7 单 27 补齐的 case 别名）
            if tok.type == TokenType.KEYWORD and tok.value in ('情况', '例'):
                case = self._parse_match_case()
                cases.append(case)
            # 默认分支：其他 / 否
            elif self._is_match_default_lead(tok):
                case = self._parse_match_case(default_branch=True)
                cases.append(case)
            else:
                # 跳过无法识别的token
                break

        return MatchStmt(subject, cases)

    def _parse_with_stmt(self) -> WithStmt:
        """解析上下文管理器：使用 表达式 为 变量：...（依赖缩进）

        支持：
        - 使用 表达式 为 变量：...（同步上下文管理器）
        - 使用 异步 表达式 为 变量：...（异步上下文管理器）
        - 使用 表达式1 为 变量1, 表达式2 为 变量2：...（多个上下文管理器）
        """
        # 使用
        self._consume(TokenType.KEYWORD, '使用')

        # 检测通配符导入：使用 模块名.*
        if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            saved_pos = self.pos
            mod_tok = self._consume()
            mod_name = mod_tok.value
            if self._current() and self._current().type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
                if self._current() and self._current().type == TokenType.STAR:
                    self._consume(TokenType.STAR)
                    # 消耗句号（可选）
                    if self._current() and self._current().type == TokenType.PERIOD:
                        self._consume(TokenType.PERIOD)
                    return ImportStmt(mod_name, symbols=['*'], alias=None)

            # 不是通配符导入，回退
            self.pos = saved_pos

        # 检测异步上下文管理器：使用 异步 ...（`异` 是 v7 单 31-G 的单字别名）
        is_async = False
        if self._current() and self._current().type == TokenType.KEYWORD and self._current().value in ('异步', '异'):
            self._consume(TokenType.KEYWORD)
            is_async = True

        # 解析上下文管理器列表（支持多个：使用 expr1 为 v1, expr2 为 v2）
        # 注意：由于 _parse_expr() 会将逗号作为管道操作符消费，
        # 多个上下文管理器会先被解析为 Pipeline 节点，需要在此拆分
        items = []

        # 解析上下文表达式（可能包含多个逗号分隔的表达式，被解析为 Pipeline）
        context_expr = self._parse_expr()

        # 检查是否为 Pipeline（多个上下文管理器通过逗号分隔）
        if isinstance(context_expr, Pipeline):
            # 每个 stage 是一个上下文管理器表达式
            for stage in context_expr.stages:
                variable = None
                if isinstance(stage, BinaryOp) and stage.operator == '==':
                    # '为' 被解析为 '==' 运算符，提取左右两边
                    if isinstance(stage.right, Identifier):
                        variable = stage.right.name
                        stage = stage.left
                items.append((stage, variable))
        else:
            # 单个上下文管理器
            variable = None
            if isinstance(context_expr, BinaryOp) and context_expr.operator == '==':
                # '为' 被解析为 '==' 运算符，提取左右两边
                if isinstance(context_expr.right, Identifier):
                    variable = context_expr.right.name
                    context_expr = context_expr.left
            elif self._match(TokenType.KEYWORD, '为'):
                self._consume(TokenType.KEYWORD, '为')
                var_tok = self._current()
                if var_tok and var_tok.type == TokenType.IDENTIFIER:
                    variable = self._consume(TokenType.IDENTIFIER).value
                elif var_tok and var_tok.type == TokenType.KEYWORD:
                    variable = self._consume(TokenType.KEYWORD).value
                else:
                    self._error(f"期望变量名，但得到 {var_tok.type if var_tok else '输入结束'}")
            items.append((context_expr, variable))

        # 保存第一个上下文管理器到 context_expr / variable（兼容旧代码）
        first_expr, first_var = items[0] if items else (None, None)

        # 冒号（可选）
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)

        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        # 体
        body = self._parse_body()

        return WithStmt(first_expr, first_var, body, is_async=is_async, items=items)

    def _parse_decorator_info(self) -> DecoratorInfo:
        """解析单个装饰器信息（@名字 或 @名字(参数)）

        返回装饰器信息（DecoratorInfo），不含被装饰函数。
        用于装饰器链场景：多个 @decorator 行后跟一个函数定义。
        """
        # @
        self._consume(TokenType.AT)

        # 装饰器名（支持多token名称）
        name_parts = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 遇到"标注"、"函数"、"段落"、"构造"、"《"或"("时停止收集名称
            if self._current().type == TokenType.KEYWORD and self._current().value in ('标注', '函数', '段落', '构造'):
                break
            if self._current().type == TokenType.LBOOK:
                break
            if self._current().type == TokenType.LPAREN:
                break
            name_parts.append(self._consume().value)
        if not name_parts:
            tok = self._current()
            self._error(f"期望装饰器名，但得到 {tok.type if tok else '输入结束'}")
        decorator_name = ''.join(name_parts)

        # 可选的装饰器参数：@decorator(args)
        decorator_args = None
        if self._current() and self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            decorator_args = []
            while not self._match(TokenType.RPAREN):
                if self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._consume()
                    continue
                # 支持关键字参数：name = value
                _kwarg_saved_pos = self.pos
                _kwarg_name_parts = []
                _kwarg_stop_kws = frozenset({
                    '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
                    '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
                    '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
                    '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
                    '匹配', '情况', '的', '之', '对', '步', '至', '到', '推迟',
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
                        from ast_nodes_v3 import KeywordArg
                        decorator_args.append(KeywordArg(kwarg_name, kwarg_val))
                else:
                    # 不是关键字参数，回退
                    self.pos = _kwarg_saved_pos
                    arg = self._parse_comparison()
                    if arg is not None:
                        decorator_args.append(arg)
                    else:
                        break
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
            self._consume(TokenType.RPAREN)

        return DecoratorInfo(decorator_name, decorator_args)

    def _parse_decorator(self) -> DecoratorDefinition:
        """解析装饰器定义

        语法：
        @自定义装饰器 标注 段落 ...
        @静态方法 / @类方法 / @特性（后跟段落或构造定义）
        """
        # @
        self._consume(TokenType.AT)

        # 装饰器名（支持多token名称，如"自定义装饰器"被拆为"自"+"定义"+"装饰器"）
        decorator_name = None
        name_parts = []
        while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            # 遇到"标注"、"段落"、"构造"、"《"或"("时停止收集名称
            if self._current().type == TokenType.KEYWORD and self._current().value in ('标注', '函数', '段落', '构造'):
                break
            if self._current().type == TokenType.LBOOK:
                break
            if self._current().type == TokenType.LPAREN:
                break
            name_parts.append(self._consume().value)
        if name_parts:
            decorator_name = ''.join(name_parts)
        else:
            tok = self._current()
            self._error(f"期望装饰器名，但得到 {tok.type if tok else '输入结束'}")

        # 可选的装饰器参数：@decorator(args)
        decorator_args = None
        if self._current() and self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            decorator_args = []
            while not self._match(TokenType.RPAREN):
                if self._current() and self._current().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                    self._consume()
                    continue
                # 支持关键字参数：name = value
                _kwarg_saved_pos = self.pos
                _kwarg_name_parts = []
                _kwarg_stop_kws = frozenset({
                    '为', '等于', '接收', '返回', '令', '循环', '断言', '输出',
                    '如果', '否则', '那么', '若', '则', '当', '遍历', '设', '定义',
                    '类', '构造', '函数', '段落', '尝试', '捕获', '抛出', '最终', '导入',
                    '导出', '从', '真', '假', '空', '且', '或', '非', '与', '等待',
                    '匹配', '情况', '的', '之', '对', '步', '至', '到', '推迟',
                    '导', '出', '遍', '返', '跳', '过', '试', '捕', '抛', '掷', '终', '配', '否', '接', '承', '自',
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
                        from ast_nodes_v3 import KeywordArg
                        decorator_args.append(KeywordArg(kwarg_name, kwarg_val))
                else:
                    # 不是关键字参数，回退
                    self.pos = _kwarg_saved_pos
                    arg = self._parse_comparison()
                    if arg is not None:
                        decorator_args.append(arg)
                    else:
                        break
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
            self._consume(TokenType.RPAREN)

        # 内置装饰器处理（@静态方法、@类方法、@特性、@抽象）
        if decorator_name in ('静态方法', '类方法', '特性', '抽象'):
            # 跳过装饰器名与被装饰定义之间的 NEWLINE
            while self._match(TokenType.NEWLINE):
                self._consume(TokenType.NEWLINE)
            # 跳过可选的"标注"关键字（@抽象 标注 段落 ...）
            if self._match(TokenType.KEYWORD, '标注'):
                self._consume(TokenType.KEYWORD, '标注')
                while self._match(TokenType.NEWLINE):
                    self._consume(TokenType.NEWLINE)
            paragraph = None
            if self._match(TokenType.LBOOK):
                paragraph = self._parse_paragraph()
            elif self._match(TokenType.KEYWORD, '函数') or self._match(TokenType.KEYWORD, '段落'):
                paragraph = self._parse_paragraph_v2()
            elif self._match(TokenType.KEYWORD, '构造'):
                paragraph = self._parse_method_definition(is_constructor=True)
            else:
                self._error("装饰器后必须跟函数定义或构造定义")
            return DecoratorDefinition(decorator_name, paragraph)

        # 标注（可选关键字）— 仅自定义装饰器
        if self._match(TokenType.KEYWORD, '标注'):
            self._consume(TokenType.KEYWORD, '标注')
            # 跳过标注后的 NEWLINE（@decorator 标注\n段落 ...）
            while self._match(TokenType.NEWLINE):
                self._consume(TokenType.NEWLINE)

        # 解析被装饰的段落
        paragraph = None
        if self._match(TokenType.LBOOK):
            # 《段名》段形式
            paragraph = self._parse_paragraph()
        elif self._match(TokenType.KEYWORD, '函数') or self._match(TokenType.KEYWORD, '段落'):
            # 函数/段落 段名 参数形式
            paragraph = self._parse_paragraph_v2()
        elif self._match(TokenType.KEYWORD, '构造'):
            # 构造定义
            paragraph = self._parse_method_definition(is_constructor=True)
        else:
            self._error("装饰器后必须跟函数定义（'《段名》段' 或 '函数 段名'）")

        return DecoratorDefinition(decorator_name, paragraph, decorator_args)

    # 默认分支引导词。`其他` 全仓未注册为关键字（词法上是 IDENTIFIER），
    # 按裁定不提升为关键字，只在 match 块里额外接受值为 `其他` 的 IDENTIFIER；
    # `否` 是关键字（src/keywords.py:51，否则的 L0 单字），规范
    # docs/L2_文言体语法规范_v4.0.md:384-407 用 `否:` 作默认分支，一并接受。
    _MATCH_DEFAULT_WORDS = ('其他', '否', '否则')

    # 布尔守卫式判据（纯语法）：模式解析完成后若当前 token 属于以下比较/逻辑运算符，
    # 说明 `情况 <...>` 后面其实是一个布尔表达式，而不是模式。
    _MATCH_GUARD_OP_TYPES = frozenset({
        TokenType.LESS, TokenType.GREATER,
        TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
        TokenType.EQ_EQ, TokenType.NOT_EQ,
    })
    # 中文运算符（parser_core.COMPARISON_OP_MAP / LOGICAL_OP_MAP，
    # 故意不含 '为'：`为` 在语句层另有含义）
    _MATCH_GUARD_OP_KEYWORDS = frozenset({
        '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
        '不小于', '不大于', '包含', '且', '与', '或',
    })

    def _is_match_default_lead(self, tok: Optional[Token]) -> bool:
        """当前 token 是否是 match 默认分支引导词（其他 / 否 / 否则）"""
        return (tok is not None
                and tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD)
                and tok.value in self._MATCH_DEFAULT_WORDS)

    def _is_match_guard_operator(self, tok: Optional[Token]) -> bool:
        """当前 token 是否是比较/逻辑运算符（用于布尔守卫式的纯语法判据）"""
        if tok is None:
            return False
        if tok.type in self._MATCH_GUARD_OP_TYPES:
            return True
        return tok.type == TokenType.KEYWORD and tok.value in self._MATCH_GUARD_OP_KEYWORDS

    def _parse_match_case(self, default_branch: bool = False) -> MatchCase:
        """解析匹配分支：情况 模式[ 若 条件]：语句...  /  其他：语句...

        default_branch=True 时当前 token 是 `其他`/`否`，等价于 `情况 _`。
        """
        guard = None
        if default_branch:
            # 其他 / 否 → 通配模式（codegen 发射 case _:）
            self._consume()
            pattern = MatchPattern('wildcard')
        else:
            # 情况 / 例（v7 单 27：'例' 是 case 别名）
            self._consume(TokenType.KEYWORD, self._current().value)

            # `情况：` / `例：`（引导词后直接冒号）→ 通配默认分支（等价 case _:）
            if self._current() and self._current().type == TokenType.COLON:
                pattern = MatchPattern('wildcard')
            else:
                # 解析模式
                pattern_start = self.pos
                pattern = self._parse_match_pattern()

                # 布尔守卫式：情况 a >= 90: → case _ if (a >= 90):
                #
                # 纯语法判据：模式解析完后若紧跟比较/逻辑运算符，说明这一段本来是
                # 布尔表达式（模式解析已经把 `a` 误当捕获模式吃掉），回退到模式起点
                # 整体按表达式重解析。不做语义推断：`情况 <裸标识符>:`（后面直接跟冒号）
                # 仍按捕获模式处理，不因为主语是 `真` 就改读法。
                if self._is_match_guard_operator(self._current()):
                    self.pos = pattern_start
                    guard = self._parse_expr()
                    pattern = MatchPattern('wildcard')

        # 可选的守卫条件：若 条件
        if guard is None and self._current() and self._current().type == TokenType.KEYWORD \
                and self._current().value in ('若', '如果'):
            self._consume(TokenType.KEYWORD)
            guard = self._parse_expr()

        # 冒号
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)

        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)

        # 分支体
        body = []
        while self._current():
            tok = self._current()

            # 跳过 NEWLINE
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue

            # 跳过 INDENT
            if tok.type == TokenType.INDENT:
                self._consume(TokenType.INDENT)
                continue

            # 遇到下一个"情况"、默认分支引导词或 DEDENT，停止
            if tok.type == TokenType.KEYWORD and tok.value == '情况':
                break
            if self._is_match_default_lead(tok):
                break
            if tok.type == TokenType.DEDENT:
                break

            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            else:
                break

        return MatchCase(pattern, guard, body)

    def _parse_match_pattern(self) -> MatchPattern:
        """解析匹配模式"""
        tok = self._current()

        if tok is None:
            return MatchPattern('wildcard')

        # 通配符：_（下划线）
        if tok.type == TokenType.IDENTIFIER and tok.value == '_':
            self._consume()
            return MatchPattern('wildcard')

        # 数字模式
        if tok.type == TokenType.NUMBER:
            self._consume()
            return MatchPattern('number', value=tok.value)

        if tok.type == TokenType.CHINESE_NUM:
            self._consume()
            return MatchPattern('number', value=tok.value)

        # 字符串模式
        if tok.type == TokenType.STRING:
            self._consume()
            return MatchPattern('string', value=tok.value)

        # 布尔模式
        if tok.type == TokenType.KEYWORD and tok.value == '真':
            self._consume()
            return MatchPattern('bool', value=True)
        if tok.type == TokenType.KEYWORD and tok.value == '假':
            self._consume()
            return MatchPattern('bool', value=False)

        # 空模式
        if tok.type == TokenType.KEYWORD and tok.value == '空':
            self._consume()
            return MatchPattern('null')

        # 列表模式：[模式1, 模式2, ...]
        if tok.type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)
            elements = []
            while not self._match(TokenType.RBRACKET):
                elem_pattern = self._parse_match_pattern()
                elements.append(elem_pattern)
                if self._match(TokenType.COMMA):
                    self._consume(TokenType.COMMA)
            self._consume(TokenType.RBRACKET)
            return MatchPattern('list', elements=elements)

        # 类型检查或变量绑定：标识符
        if tok.type == TokenType.IDENTIFIER:
            name = tok.value
            self._consume()
            # 检查是否是类型检查模式（标识符后跟另一个标识符，如"整数 甲"表示甲是整数类型）
            next_tok = self._current()
            if next_tok and next_tok.type == TokenType.IDENTIFIER and next_tok.value != '_':
                binding = self._consume(TokenType.IDENTIFIER).value
                return MatchPattern('type_check', type_name=name, binding=binding)
            # v7 单 27：无绑定的裸类型名也是类型检查模式（`例 整数：` → `case int():`）。
            # 规范 docs/language/完整语法参考.md:534-544 的示例正是这个形态。
            # 旧实现一律判成变量捕获，生成 `case 整数:` —— 捕获模式不可反驳，
            # 会让后续分支全部 unreachable，Python 直接编译报错。
            if name in BUILTIN_TYPES:
                return MatchPattern('type_check', type_name=name, binding='')
            return MatchPattern('variable', binding=name)

        # 关键字作为模式
        if tok.type == TokenType.KEYWORD:
            name = tok.value
            self._consume()
            # v7 单 27：部分类型名词法上是 KEYWORD（如 `列` 在 VERB_ARITY 里），
            # 同样要走类型检查，且同样支持带绑定形式 `例 列 值：`。
            if name in BUILTIN_TYPES:
                next_tok = self._current()
                if next_tok and next_tok.type == TokenType.IDENTIFIER and next_tok.value != '_':
                    binding = self._consume(TokenType.IDENTIFIER).value
                    return MatchPattern('type_check', type_name=name, binding=binding)
                return MatchPattern('type_check', type_name=name, binding='')
            return MatchPattern('variable', binding=name)

        return MatchPattern('wildcard')

    # =========================================================================
    # C FFI 解析方法
    # =========================================================================

    def _parse_ffi_decl(self, from_at_c: bool = False) -> ASTNode:
        """解析外部声明：外部 函数/段落/结构体/回调/枚举/联合体/变长参数 ...
        也支持 @C 语法标记。
        
        语法：
        外部 函数 函数名 接收 参数... 返回 类型 在 库别名
        外部 段落 函数名 接收 参数... 返回 类型 在 库别名（兼容写法）
        外部 结构体 名称 { 字段: 类型, ... }
        外部 回调 名称 接收 参数... 返回 类型
        外部 枚举 名称 { 成员 = 值, ... }
        外部 联合体 名称 { 字段: 类型, ... }
        外部 变长参数 函数/段落 函数名 接收 参数... 返回 类型 在 库别名
        """
        # 外部（仅非@C模式需要）
        if not from_at_c:
            self._consume(TokenType.KEYWORD, '外部')
        
        tok = self._current()
        if tok is None:
            self._error("期望'函数'（或兼容写法'段落'）、'结构体'、'回调'、'枚举'、'联合体'或'变长参数'")
        
        if tok.type == TokenType.KEYWORD and tok.value == '变长参数':
            return self._parse_ffi_varargs_decl()
        elif tok.type == TokenType.KEYWORD and tok.value == '枚举':
            return self._parse_ffi_enum_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '联合体':
            return self._parse_ffi_union_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '类型别名':
            return self._parse_ffi_typedef_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '位域':
            return self._parse_ffi_bitfield_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '函数指针':
            return self._parse_ffi_funcptr_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '调试':
            return self._parse_ffi_debug_config()
        elif tok.type == TokenType.KEYWORD and tok.value == '宏':
            return self._parse_ffi_preprocessor_def()
        elif tok.type == TokenType.KEYWORD and tok.value in ('函数', '段落'):
            return self._parse_ffi_function_decl()
        elif tok.type == TokenType.KEYWORD and tok.value == '结构体':
            return self._parse_ffi_struct_def()
        elif tok.type == TokenType.KEYWORD and tok.value == '回调':
            return self._parse_ffi_callback_def()
        else:
            self._error(f"期望'函数'（或兼容写法'段落'）、'结构体'、'回调'、'枚举'、'联合体'或'变长参数'，但得到'{tok.value}'")

    def _parse_ffi_load_library(self) -> FFILoadLibrary:
        """解析加载库语句：加载库 "libxxx.so" 为 别名"""
        # 加载库
        self._consume(TokenType.KEYWORD, '加载库')
        
        # 库路径（字符串）
        path_tok = self._current()
        if path_tok and path_tok.type == TokenType.STRING:
            library_path = self._consume(TokenType.STRING).value
        else:
            self._error(f"期望库路径（字符串），但得到 {path_tok.type if path_tok else '输入结束'}")
        
        # 为
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
        else:
            self._error("期望'为'关键字")
        
        # 别名
        alias_tok = self._current()
        if alias_tok and alias_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            alias = self._consume().value
        else:
            self._error(f"期望库别名，但得到 {alias_tok.type if alias_tok else '输入结束'}")
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFILoadLibrary(library_path, alias)

    def _parse_ffi_function_decl(self) -> FFIFunctionDecl:
        """解析外部函数声明：外部 函数/段落 函数名 接收 参数... 返回 类型 在 库别名"""
        # 函数 或 段落
        if self._match(TokenType.KEYWORD, '函数'):
            self._consume(TokenType.KEYWORD, '函数')
        else:
            self._consume(TokenType.KEYWORD, '段落')
        
        # 函数名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望函数名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 可选C函数名：为 "c_func_name"
        c_name = None
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
            c_name_tok = self._current()
            if c_name_tok and c_name_tok.type == TokenType.STRING:
                c_name = self._consume(TokenType.STRING).value
            else:
                self._error(f"期望C函数名（字符串），但得到 {c_name_tok.type if c_name_tok else '输入结束'}")
        
        # 参数：接收 参数1: 类型, 参数2: 类型
        # 或 v2 语法：参数名直接跟在函数名后（无"接收"关键字）
        params = []
        has_jieshou = False
        if self._match(TokenType.KEYWORD, '接收'):
            has_jieshou = True
            self._consume(TokenType.KEYWORD, '接收')
        
        # 如果有"接收"关键字，或当前token是标识符（v2语法），则解析参数
        if has_jieshou or (self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD) and self._current().value not in ('返回', '在')):
            while self._current():
                ptok = self._current()
                if ptok.type == TokenType.KEYWORD and ptok.value in ('返回', '在'):
                    break
                if ptok.type == TokenType.PERIOD:
                    break
                
                if ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    # 收集参数名，直到遇到 '为' 或 ',' 或 '返回' 或 '在' 或 '。'
                    param_parts = []
                    while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        if self._current().value in ('返回', '在', '为'):
                            break
                        if self._match(TokenType.COMMA) or self._current().type == TokenType.PERIOD:
                            break
                        param_parts.append(self._current().value)
                        self._consume()
                    param_name = ''.join(param_parts)
                    if not param_name:
                        break
                    
                    # 类型注解：为 类型 或 : 类型
                    param_type = None
                    if self._match(TokenType.KEYWORD, '为'):
                        self._consume(TokenType.KEYWORD, '为')
                        param_type = self._parse_type_annotation()
                    elif self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    
                    params.append({'name': param_name, 'type': param_type})
                    
                    # 跳过逗号
                    if self._match(TokenType.COMMA):
                        self._consume(TokenType.COMMA)
                else:
                    break
        
        # 返回类型：返回 类型
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        
        # 库别名：在 库别名
        library_alias = ''
        if self._match(TokenType.KEYWORD, '在'):
            self._consume(TokenType.KEYWORD, '在')
            alias_tok = self._current()
            if alias_tok and alias_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                library_alias = self._consume().value
            else:
                self._error(f"期望库别名，但得到 {alias_tok.type if alias_tok else '输入结束'}")
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIFunctionDecl(name, params, return_type, library_alias, c_name)

    def _parse_ffi_struct_def(self) -> FFIStructDef:
        """解析外部结构体定义：外部 结构体 名称 { 字段: 类型, ... }"""
        # 结构体
        self._consume(TokenType.KEYWORD, '结构体')
        
        # 结构体名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望结构体名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 花括号
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.LBRACE)
        else:
            self._error("期望 '{'")
        
        # 字段列表
        fields = []
        while self._current() and self._current().type != TokenType.RBRACE:
            ftok = self._current()
            if ftok.type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            
            if ftok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                field_name = self._consume().value
                
                # 冒号
                if self._match(TokenType.COLON):
                    self._consume(TokenType.COLON)
                
                # 字段类型
                if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    field_type = self._consume().value
                    fields.append({'name': field_name, 'type': field_type})
                else:
                    break
            else:
                break
        
        if self._match(TokenType.RBRACE):
            self._consume(TokenType.RBRACE)
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIStructDef(name, fields)

    def _parse_ffi_callback_def(self) -> FFICallbackDef:
        """解析外部回调定义：外部 回调 名称 接收 参数... 返回 类型"""
        # 回调
        self._consume(TokenType.KEYWORD, '回调')
        
        # 回调名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望回调名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 参数：接收 参数1: 类型, 参数2: 类型
        params = []
        if self._match(TokenType.KEYWORD, '接收'):
            self._consume(TokenType.KEYWORD, '接收')
            
            while self._current():
                ptok = self._current()
                if ptok.type == TokenType.KEYWORD and (ptok.value == '返回' or ptok.value == '返'):
                    break
                if ptok.type == TokenType.PERIOD:
                    break
                
                if ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_parts = []
                    while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        if self._current().value in ('返回', '为'):
                            break
                        if self._match(TokenType.COMMA):
                            break
                        param_parts.append(self._current().value)
                        self._consume()
                    param_name = ''.join(param_parts)
                    if not param_name:
                        break
                    
                    param_type = None
                    if self._match(TokenType.KEYWORD, '为'):
                        self._consume(TokenType.KEYWORD, '为')
                        param_type = self._parse_type_annotation()
                    elif self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    
                    params.append({'name': param_name, 'type': param_type})
                    
                    if self._match(TokenType.COMMA):
                        self._consume(TokenType.COMMA)
                else:
                    break
        
        # 返回类型：返回 类型
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFICallbackDef(name, params, return_type)

    def _parse_ffi_enum_def(self) -> FFIEnumDef:
        """解析C枚举定义：外部 枚举 名称 { 成员 = 值, ... }"""
        # 枚举
        self._consume(TokenType.KEYWORD, '枚举')
        
        # 枚举名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望枚举名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 花括号
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.LBRACE)
        else:
            self._error("期望 '{'")
        
        # 枚举值列表
        values = {}
        auto_val = 0
        while self._current() and self._current().type != TokenType.RBRACE:
            ftok = self._current()
            if ftok.type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            
            if ftok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                member_name = self._consume().value
                
                # 可选的值赋值：= 值
                if self._match(TokenType.EQUALS):
                    self._consume(TokenType.EQUALS)
                    val_tok = self._current()
                    if val_tok and val_tok.type == TokenType.NUMBER:
                        values[member_name] = self._consume(TokenType.NUMBER).value
                    elif val_tok and val_tok.type == TokenType.CHINESE_NUM:
                        values[member_name] = self._consume(TokenType.CHINESE_NUM).value
                    else:
                        self._error(f"期望数值，但得到 {val_tok.type if val_tok else '输入结束'}")
                else:
                    values[member_name] = auto_val
                    auto_val += 1
            else:
                break
        
        if self._match(TokenType.RBRACE):
            self._consume(TokenType.RBRACE)
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIEnumDef(name, values)

    def _parse_ffi_union_def(self) -> FFIUnionDef:
        """解析C联合体定义：外部 联合体 名称 { 字段: 类型, ... }"""
        # 联合体
        self._consume(TokenType.KEYWORD, '联合体')
        
        # 联合体名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望联合体名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 花括号
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.LBRACE)
        else:
            self._error("期望 '{'")
        
        # 字段列表
        fields = []
        while self._current() and self._current().type != TokenType.RBRACE:
            ftok = self._current()
            if ftok.type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            
            if ftok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                field_name = self._consume().value
                
                if self._match(TokenType.COLON):
                    self._consume(TokenType.COLON)
                
                if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    field_type = self._consume().value
                    fields.append({'name': field_name, 'type': field_type})
                else:
                    break
            else:
                break
        
        if self._match(TokenType.RBRACE):
            self._consume(TokenType.RBRACE)
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIUnionDef(name, fields)

    def _parse_ffi_varargs_decl(self) -> FFIVarArgsDecl:
        """解析变长参数声明：外部 变长参数 函数/段落 函数名 接收 参数... 返回 类型 在 库别名"""
        # 变长参数
        self._consume(TokenType.KEYWORD, '变长参数')
        
        # 函数 或 段落
        if self._match(TokenType.KEYWORD, '函数'):
            self._consume(TokenType.KEYWORD, '函数')
        elif self._match(TokenType.KEYWORD, '段落'):
            self._consume(TokenType.KEYWORD, '段落')
        else:
            self._error("期望'函数'（或兼容写法'段落'）关键字")
        
        # 函数名
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望函数名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        # 可选C函数名：为 "c_func_name"
        c_name = None
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
            c_name_tok = self._current()
            if c_name_tok and c_name_tok.type == TokenType.STRING:
                c_name = self._consume(TokenType.STRING).value
            else:
                self._error(f"期望C函数名（字符串），但得到 {c_name_tok.type if c_name_tok else '输入结束'}")
        
        # 固定参数：接收 参数1: 类型, 参数2: 类型
        params = []
        if self._match(TokenType.KEYWORD, '接收'):
            self._consume(TokenType.KEYWORD, '接收')
            
            while self._current():
                ptok = self._current()
                if ptok.type == TokenType.KEYWORD and ptok.value in ('返回', '在'):
                    break
                if ptok.type == TokenType.PERIOD:
                    break
                
                if ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_parts = []
                    while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        if self._current().value in ('返回', '在', '为'):
                            break
                        if self._match(TokenType.COMMA):
                            break
                        param_parts.append(self._current().value)
                        self._consume()
                    param_name = ''.join(param_parts)
                    if not param_name:
                        break
                    
                    param_type = None
                    if self._match(TokenType.KEYWORD, '为'):
                        self._consume(TokenType.KEYWORD, '为')
                        param_type = self._parse_type_annotation()
                    elif self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    
                    params.append({'name': param_name, 'type': param_type})
                    
                    if self._match(TokenType.COMMA):
                        self._consume(TokenType.COMMA)
                else:
                    break
        
        # 返回类型：返回 类型
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        
        # 库别名：在 库别名
        library_alias = ''
        if self._match(TokenType.KEYWORD, '在'):
            self._consume(TokenType.KEYWORD, '在')
            alias_tok = self._current()
            if alias_tok and alias_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                library_alias = self._consume().value
            else:
                self._error(f"期望库别名，但得到 {alias_tok.type if alias_tok else '输入结束'}")
        
        # 句号（可选）
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIVarArgsDecl(name, params, return_type, library_alias, c_name)

    # ---- 类型别名解析 ----
    def _parse_type_alias(self):
        """解析类型别名定义：类型 别名 = 类型定义（返回 TypeAlias 节点）
        
        语法：
            类型 名字 = 类型定义
            类型 名字[泛型参数] = 类型定义
        """
        from ast_nodes import TypeAlias
        
        line, col = self._current().line, self._current().col
        self._consume(TokenType.KEYWORD, '类型')  # 消耗 类型
        
        # 别名名称
        name_tok = self._current()
        if not name_tok or name_tok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            self._error(f"期望类型别名名称，但得到 {name_tok.type if name_tok else '输入结束'}", line, col)
            return TypeAlias(name='', target_type='')
        name = self._consume().value
        
        # 可选的泛型参数：[T, K, V]
        generic_params = []
        if self._current() and self._current().type == TokenType.LBRACKET:
            self._consume(TokenType.LBRACKET)  # 消耗 [
            while self._current() and self._current().type != TokenType.RBRACKET:
                param_tok = self._current()
                if param_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    generic_params.append(self._consume().value)
                if self._current() and self._current().type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                elif self._current() and self._current().type != TokenType.RBRACKET:
                    self._error(f"类型别名泛型参数解析错误，期望 ']' 或 ','，但得到 {self._current().value}")
                    break
            if self._current() and self._current().type == TokenType.RBRACKET:
                self._consume(TokenType.RBRACKET)
            else:
                self._error("期望 ']' 结束类型别名泛型参数")
        
        # 等号
        if self._current() and self._current().type == TokenType.EQUALS:
            self._consume(TokenType.EQUALS)  # 消耗 =
        else:
            # 也支持中文冒号 ： 或 为 关键字
            if self._current() and self._current().type == TokenType.COLON:
                self._consume(TokenType.COLON)
            elif self._current() and self._current().type == TokenType.KEYWORD and self._current().value == '为':
                self._consume(TokenType.KEYWORD, '为')
            else:
                self._error("期望 '='、':' 或 '为' 在类型别名定义中")
        
        # 目标类型定义（读取直到行尾或句号）
        target_type_parts = []
        while self._current() and self._current().type != TokenType.PERIOD and \
              self._current().type != TokenType.NEWLINE and \
              self._current().type != TokenType.EOF:
            target_type_parts.append(self._consume().value)
        
        # 消耗句号
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        target_type = ' '.join(target_type_parts).strip()
        
        result = TypeAlias(
            name=name,
            target_type=target_type,
            generic_params=generic_params,
        )
        result.line, result.column = line, col
        return result

    def _parse_ffi_typedef_def(self) -> FFITypedefDef:
        """解析C类型别名：外部 类型别名 名称 为 基础类型"""
        self._consume(TokenType.KEYWORD, '类型别名')
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望类型别名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        base_type = name
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                base_type = self._consume().value
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFITypedefDef(name, base_type)

    def _parse_ffi_bitfield_def(self) -> FFIBitfieldDef:
        """解析C位域定义：外部 位域 名称 : 基础类型 { 字段: 位数, ... }"""
        self._consume(TokenType.KEYWORD, '位域')
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望位域名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        base_type = '整数'
        if self._match(TokenType.COLON):
            self._consume(TokenType.COLON)
            if self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                base_type = self._consume().value
        
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.LBRACE)
        else:
            self._error("期望 '{'")
        
        fields = []
        while self._current() and self._current().type != TokenType.RBRACE:
            ftok = self._current()
            if ftok.type == TokenType.COMMA:
                self._consume(TokenType.COMMA)
                continue
            if ftok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                field_name = self._consume().value
                bit_width = 1
                if self._match(TokenType.COLON):
                    self._consume(TokenType.COLON)
                    if self._current() and self._current().type == TokenType.NUMBER:
                        bit_width = self._consume(TokenType.NUMBER).value
                fields.append({'name': field_name, 'bits': bit_width})
            else:
                break
        
        if self._match(TokenType.RBRACE):
            self._consume(TokenType.RBRACE)
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIBitfieldDef(name, base_type, fields)

    def _parse_ffi_funcptr_def(self) -> FFIFuncPtrDef:
        """解析C函数指针类型：外部 函数指针 名称 接收 参数... 返回 类型"""
        self._consume(TokenType.KEYWORD, '函数指针')
        name_tok = self._current()
        if name_tok and name_tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            name = self._consume().value
        else:
            self._error(f"期望函数指针名，但得到 {name_tok.type if name_tok else '输入结束'}")
        
        params = []
        if self._match(TokenType.KEYWORD, '接收'):
            self._consume(TokenType.KEYWORD, '接收')
            while self._current():
                ptok = self._current()
                if ptok.type == TokenType.KEYWORD and (ptok.value == '返回' or ptok.value == '返'):
                    break
                if ptok.type == TokenType.PERIOD:
                    break
                if ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    param_parts = []
                    while self._current() and self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        if self._current().value in ('返回', '为'):
                            break
                        if self._match(TokenType.COMMA):
                            break
                        param_parts.append(self._current().value)
                        self._consume()
                    param_name = ''.join(param_parts)
                    if not param_name:
                        break
                    param_type = None
                    if self._match(TokenType.KEYWORD, '为'):
                        self._consume(TokenType.KEYWORD, '为')
                        param_type = self._parse_type_annotation()
                    elif self._match(TokenType.COLON):
                        self._consume(TokenType.COLON)
                        param_type = self._parse_type_annotation()
                    params.append({'name': param_name, 'type': param_type})
                    if self._match(TokenType.COMMA):
                        self._consume(TokenType.COMMA)
                else:
                    break
        
        return_type = None
        if self._match(TokenType.KEYWORD, '返回'):
            self._consume(TokenType.KEYWORD, self._current().value)  # 返回 / 返
            return_type = self._parse_type_annotation()
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIFuncPtrDef(name, params, return_type)

    def _parse_ffi_debug_config(self) -> FFIDebugConfig:
        """解析FFI调试配置：外部 调试 { 开启, 记录调用, 记录类型, 追踪内存 }"""
        self._consume(TokenType.KEYWORD, '调试')
        
        enabled = True
        log_calls = False
        log_types = False
        trace_memory = False
        
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.LBRACE)
            while self._current() and self._current().type != TokenType.RBRACE:
                tok = self._current()
                if tok.type == TokenType.COMMA:
                    self._consume(TokenType.COMMA)
                    continue
                if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    val = self._consume().value
                    if val == '关闭':
                        enabled = False
                    elif val == '开启':
                        enabled = True
                    elif val == '记录调用':
                        log_calls = True
                    elif val == '记录类型':
                        log_types = True
                    elif val == '追踪内存':
                        trace_memory = True
                else:
                    break
            if self._match(TokenType.RBRACE):
                self._consume(TokenType.RBRACE)
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIDebugConfig(enabled, log_calls, log_types, trace_memory)

    def _parse_ffi_preprocessor_def(self) -> FFIPreprocessorDef:
        """解析C预处理器宏：外部 宏 名称 为 值"""
        self._consume(TokenType.KEYWORD, '宏')
        
        # 宏名可能由多个 token 组成（如"最大连接"被拆分为"最大连"+关键字"接"）
        name_parts = []
        while self._current():
            tok = self._current()
            if tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                if tok.value == '为':
                    break
                name_parts.append(self._consume().value)
            else:
                break
        if not name_parts:
            self._error(f"期望宏名，但得到 {self._current().type if self._current() else '输入结束'}")
        name = ''.join(name_parts)
        
        value = ""
        if self._match(TokenType.KEYWORD, '为'):
            self._consume(TokenType.KEYWORD, '为')
            if self._current():
                if self._current().type == TokenType.NUMBER:
                    value = str(self._consume(TokenType.NUMBER).value)
                elif self._current().type == TokenType.STRING:
                    value = self._consume(TokenType.STRING).value
                elif self._current().type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    value = self._consume().value
        
        if self._current() and self._current().type == TokenType.PERIOD:
            self._consume(TokenType.PERIOD)
        
        return FFIPreprocessorDef(name, value)