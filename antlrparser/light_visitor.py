"""
光明（Light）编程语言 ANTLR 访问器

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
    FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFIUnionDef,
    FFICallbackDef, FFIEnumDef, FFIVarArgsDecl,
)

# 导入自定义分词器
from light_tokenizer import create_antlr_token_stream

# 导入 mixin 模块
from visitor_expr import VisitorExprMixin


# =============================================================================
# 自定义错误监听器
# =============================================================================

class LightLangErrorListener(ErrorListener):
    """光明语法错误监听器 — 中文提示+修复建议"""

    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offending_symbol, line, column, msg, e):
        chinese_msg = self._translate_error(msg)
        suggestion = self._get_suggestion(msg)
        if suggestion:
            error_msg = f"第{line}行, 第{column}列: {chinese_msg}\n  建议: {suggestion}"
        else:
            error_msg = f"第{line}行, 第{column}列: {chinese_msg}"
        self.errors.append(error_msg)

    @staticmethod
    def _decode_unicode(msg: str) -> str:
        """解码消息中的 \\uXXXX 转义序列"""
        import re
        def replace_unicode(match):
            return chr(int(match.group(1), 16))
        return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, msg)

    @staticmethod
    def _translate_error(msg: str) -> str:
        """将 ANTLR 英文错误翻译为中文"""
        # 先解码 Unicode 转义
        msg = LightLangErrorListener._decode_unicode(msg)

        # mismatched input
        if msg.startswith("mismatched input"):
            # mismatched input 'X' expecting {'Y', 'Z'}
            parts = msg.split("expecting")
            if len(parts) == 2:
                found = parts[0].replace("mismatched input", "").strip().strip("'")
                expected = parts[1].strip()
                # 展开期望列表
                expected = expected.replace("{", "").replace("}", "")
                expected_list = [e.strip().strip("'") for e in expected.split(",")]
                if len(expected_list) == 1:
                    return f"期望 {expected_list[0]}，却遇到了 '{found}'"
                elif len(expected_list) <= 3:
                    expect_text = "、".join(expected_list)
                    return f"期望 {expect_text}，却遇到了 '{found}'"
                else:
                    expect_text = "、".join(expected_list[:3])
                    return f"语法不匹配: 遇到了 '{found}'，期望 {expect_text} 等"
            return f"语法不匹配: {msg}"

        # missing
        if msg.startswith("missing"):
            # missing 'X' at 'Y'
            parts = msg.split("at")
            if len(parts) == 2:
                missing = parts[0].replace("missing", "").strip().strip("'")
                location = parts[1].strip().strip("'")
                if location == '<EOF>':
                    return f"缺少 '{missing}'（文件末尾）"
                return f"在 '{location}' 处缺少 '{missing}'"
            return f"缺少语法元素: {msg}"

        # extraneous input
        if msg.startswith("extraneous input"):
            # extraneous input 'X' expecting {'Y', 'Z'}
            parts = msg.split("expecting")
            if len(parts) == 2:
                found = parts[0].replace("extraneous input", "").strip().strip("'")
                expected = parts[1].strip().replace("{", "").replace("}", "")
                expected_list = [e.strip().strip("'") for e in expected.split(",")]
                if len(expected_list) == 1:
                    return f"多余的 '{found}'，此处应为 {expected_list[0]}"
                expect_text = "、".join(expected_list[:3])
                return f"多余的 '{found}'，此处应为 {expect_text} 等"
            return f"多余输入: {msg}"

        # no viable alternative
        if msg.startswith("no viable alternative"):
            return "语法错误，无法解析此处的输入"

        # token recognition
        if msg.startswith("token recognition"):
            return f"无法识别的字符: {msg.split('at:')[1].strip() if 'at:' in msg else msg}"

        # 其他错误
        return msg

    @staticmethod
    def _get_suggestion(msg: str) -> str:
        """根据错误给出中文修复建议"""
        msg_lower = msg.lower()

        # 缺少句号
        if msg.startswith("missing") and ("PERIOD" in msg or "。'" in msg):
            return "每条语句末尾需要加中文句号「。」"

        # 缺少冒号
        if msg.startswith("missing") and "COLON" in msg:
            return "段定义或条件语句末尾需要加中文冒号「：」"

        # 多余结束
        if "K_END" in msg and ("extraneous" in msg_lower or "mismatched" in msg_lower):
            return "可能缺少「结束」标记，或层级缩进有误"

        # 括号不匹配
        if "mismatched" in msg_lower and ("LPAREN" in msg or "RPAREN" in msg):
            return "检查括号是否匹配，是否缺少左括号「（」或右括号「）」"

        # 中括号不匹配
        if "mismatched" in msg_lower and ("LBRACKET" in msg or "RBRACKET" in msg):
            return "检查中括号是否匹配，是否缺少「【」或「】」"

        # 语法结构错误
        if "no viable" in msg_lower:
            return "请检查此行的语法结构，是否有拼写错误或缺少关键字"

        # 结束标记错误
        if msg.startswith("missing") and "K_END" in msg:
            return "段落缺少结束标记「结束」，或层级缩进有误"

        return ""

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_errors(self) -> List[str]:
        return self.errors


# =============================================================================
# 访问器：ANTLR 解析树 → 光明 AST（组合模块）
# =============================================================================

class LightLangASTBuilder(VisitorExprMixin):
    """光明语言 AST 构建器"""
    pass


# =============================================================================
# 词法分析器包装
# =============================================================================

class LightLexer:
    """光明词法分析器包装"""

    def __init__(self):
        self.errors = []

    def tokenize(self, source: str) -> List:
        """将源代码分词为 Token 列表（使用自定义中文分词器）"""
        from light_tokenizer import LightLangTokenizer

        tokenizer = LightLangTokenizer()
        tokens = tokenizer.tokenize(source)

        if tokenizer.errors:
            self.errors = tokenizer.errors

        return tokens


# =============================================================================
# 语法解析器包装
# =============================================================================

class LightParser:
    """光明语法解析器包装"""

    def __init__(self):
        self.errors = []

    def parse(self, source: str) -> Optional[Module]:
        """解析源代码为 AST（使用自定义中文分词器 + ANTLR 解析器）"""
        # ANTLR Parser 已原生支持列表推导、匿名函数、模式匹配
        # 仅对异步/等待/推迟/并行 语法进行预处理转换
        source = self._preprocess_postfix_ternary(source)
        source = self._preprocess_async(source)
        # 自动关闭未闭合的块 — 启用以支持纯缩进语法（3.x 新语法）
        source = self._auto_close_blocks(source)

        # 使用自定义中文分词器
        token_stream = create_antlr_token_stream(source, LightLangLexer)
        parser = LightLangParser(token_stream)
        
        # 设置错误监听器
        error_listener = LightLangErrorListener()
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)

        # 解析
        tree = parser.program()

        if error_listener.has_errors():
            self.errors = error_listener.get_errors()
            return None

        # 构建 AST
        builder = LightLangASTBuilder()
        module = builder.visitProgram(tree)
        self.errors = builder.errors

        # 后处理：将预处理标记还原为真实AST节点
        if module is not None:
            module = self._postprocess_ast(module)

        return module

    def _preprocess_source(self, source: str) -> str:
        """预处理源代码：将新语法转换为ANTLR可解析的等效语法

        转换规则：
        1. 列表推导 [expr 遍历 var 之 list] → __列表推导__(expr, var, list)
        2. 匿名函数 接收 x：返回 expr。 → __匿名函数__(x, expr)
        3. 模式匹配 匹配 val：情况 ... 结束。 → __模式匹配__(val, ...)
        """
        import re

        # 1. 处理模式匹配
        source = self._preprocess_match(source)

        # 2. 处理列表推导
        source = self._preprocess_list_comprehension(source)

        # 3. 处理匿名函数
        source = self._preprocess_lambda(source)

        # 4. 处理异步/等待/推迟/并行
        source = self._preprocess_async(source)

        return source

    def _preprocess_postfix_ternary(self, source: str) -> str:
        """R76-A：后置三元 `设 X 为 值1 如果 条件 否则 值2`

        语法上等价改写为前缀三元（conditionalExpr）：
            设 X 为 如果 条件 那么 值1 否则 值2
        仅作用于 `设 … 为 …` 单行形态，避免误伤块级 否则。
        """
        import re
        pattern = re.compile(
            r'^(?P<pre>[ \t]*设[ \t]+\S+[ \t]+为[ \t]+)(?P<val>.+?)'
            r'[ \t]+如果[ \t]+(?P<cond>.+?)[ \t]+否则[ \t]+(?P<els>.+?)[ \t]*$',
            re.MULTILINE,
        )

        def rep(m):
            return (f"{m.group('pre')}如果 {m.group('cond')} "
                    f"那么 {m.group('val')} 否则 {m.group('els')}")

        return pattern.sub(rep, source)

    def _auto_close_blocks(self, source: str) -> str:
        """自动关闭未闭合的代码块（缩进驱动 + 显式「结束」感知）

        R76-A 根因②重写。旧实现用 `\\b`/`^(?:段|段落)\\b` 正则判定块开始，
        对 v3 无空格写法（如 `段落加法接收甲，乙：`、`如果甲大于乙：`）零匹配；
        且不感知源文件中已有的显式 `结束`，导致重复关闭（报「多余的 '结束'」）。

        新算法（逐行、缩进驱动）：
        1. 以冒号行尾判定块开始（不再依赖关键字正则，天然覆盖无空格写法）；
        2. 维护打开块栈 (indent, closable)；`closable=False` 表示语法上不带
           `结束` 的块（如 `匹配`：matchStmt 规则无 K_END）；
        3. 当出现缩进 <= 栈顶块缩进的行（含同级 `否则`/`情况`）时，先插入
           对应数量的 `结束` 行再放行当前行；
        4. 显式 `结束` 行关闭最近一个缩进 <= 其缩进的可关闭块，不重复插入；
        5. 文件末尾关闭所有残留可关闭块。
        """
        import re

        def strip_comment(stripped: str) -> str:
            for prefix in ('#', '//'):
                idx = stripped.find(prefix)
                if idx > 0:
                    return stripped[:idx].strip()
            return stripped

        # R76-A：块开始关键字（行中冒号 = 内联块体，如 `如果 x != y: 抛出 "..."`）
        _OPEN_KEYWORDS = ('如果', '若', '否则如果', '否则若', '否则', '当', '遍历', '对',
                          '尝试', '使用', '情况', '段落', '段', '类', '接口', '构造',
                          '方法', '数据类型')

        def is_block_opener(content: str) -> bool:
            if content.endswith('：') or content.endswith(':'):
                return True
            for kw in _OPEN_KEYWORDS:
                if content.startswith(kw):
                    c = max(content.rfind('：'), content.rfind(':'))
                    if c > 0 and c < len(content) - 1:
                        return True
            return False

        lines = source.split('\n')
        out = []
        # 栈元素: (块开始缩进, 是否需要合成 `结束`)
        stack = []

        def close_before(line_indent: int) -> None:
            """在当前行之前关闭所有缩进 >= line_indent 的可关闭块。"""
            while stack and stack[-1][1] and stack[-1][0] >= line_indent:
                b_indent, _ = stack.pop()
                out.append(' ' * b_indent + '结束')

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                out.append(line)
                continue
            indent = len(line) - len(line.lstrip())
            content = strip_comment(stripped)

            # ---- R76-A：类显式收尾标记（类结束/结束类）----
            # 语法上等价于该类的 `结束`：插入标准 结束 行后吞掉原行
            if re.match(r'^(?:类结束|结束类|段结束|结束段)[。.]?$', content):
                close_before(indent)
                continue

            # ---- 显式结束行：关闭最近一个缩进 <= 当前行缩进的可关闭块 ----
            if re.match(r'^结束[。.]?$', content):
                closed = False
                for k in range(len(stack) - 1, -1, -1):
                    b_indent, closable = stack[k]
                    if closable and b_indent <= indent:
                        del stack[k:]
                        closed = True
                        break
                out.append(line)
                # 未匹配到打开块时保持原样（如实交给解析器报错）
                continue

            # ---- 块开始行（冒号行尾，或行中冒号的内联块体）----
            if is_block_opener(content):
                close_before(indent)
                # `匹配` 块语法上不带 `结束`（matchStmt 无 K_END），只作容器
                is_match = bool(re.match(r'^(匹配|配)\b', content))
                stack.append((indent, not is_match))
                out.append(line)
                continue

            # ---- 普通语句行 ----
            close_before(indent)
            out.append(line)

        # 文件末尾关闭所有残留可关闭块
        while stack:
            b_indent, closable = stack.pop()
            if closable:
                out.append(' ' * b_indent + '结束')

        return '\n'.join(out)

    def _preprocess_async(self, source: str) -> str:
        """预处理异步/并发语法

        转换规则：
        1. 异步段 名称 → 段 __async_名称（前缀标记，由 visitor 检测并还原）
        2. 等待(表达式) → __await__(表达式)
        3. 等待 表达式 → __await__(表达式) （表达式为简单标识符时）
        4. 推迟：语句。 → __defer__ 语句。（推迟语句标记）
        5. 并行：...结束。 → __parallel__(...)（并行作用域标记）
        """
        import re

        # 1. "异步 段 名称" → "段 __async_名称"（也支持无空格的"异步段落"）
        source = re.sub(r'异步\s*(段(?:落)?)\s+', r'\1 __async_', source)

        # 2. "等待(" → "__await__("
        source = re.sub(r'等待\s*\(', '__await__(', source)

        # 3. 处理行尾的 "等待 表达式" → "__await__(表达式)"
        source = re.sub(
            r'等待\s+([a-zA-Z\u4e00-\u9fff_][a-zA-Z\u4e00-\u9fff_0-9]*)',
            r'__await__(\1)',
            source
        )

        # 4. 处理推迟语句：推迟：语句。 → __defer__(语句)。
        source = re.sub(
            r'推迟\s*[：:]\s*(.*?)[。.]',
            r'__defer__(\1)。',
            source
        )

        # 5. 处理并行作用域：并行：...结束。 → __parallel__(...)
        # 匹配"并行："到"结束。"的多行内容
        source = re.sub(
            r'并行\s*[：:]\s*\n(.*?)结束\s*[。.]',
            r'__parallel__(\1)',
            source,
            flags=re.DOTALL
        )

        return source

    def _preprocess_match(self, source: str) -> str:
        """预处理模式匹配语句

        匹配 值：
          情况 1：打印("一")。
          情况 2：打印("二")。
          情况 _：打印("其他")。
        结束。

        转换为：
        设 __匹配值__ 为 值。
        如果 __匹配值__ 等于 1：打印("一")。
        否则若 __匹配值__ 等于 2：打印("二")。
        否则：打印("其他")。
        结束。
        """
        import re
        # 匹配 "匹配" 开始，到 "结束。" 为止的块
        pattern = re.compile(
            r'匹配\s+(.+?)\s*[：:]\s*\n(.*?)\n\s*结束[。.]?',
            re.DOTALL
        )

        def replace_match(m):
            subject = m.group(1).strip()
            body = m.group(2).strip()
            var_name = '__匹配值__'

            # 解析情况分支
            case_pattern = re.compile(
                r'情况\s+(.+?)\s*[：:]\s*(.*?)(?=\n\s*情况|\s*$)',
                re.DOTALL
            )
            cases = case_pattern.findall(body)

            if not cases:
                return m.group(0)  # 无法解析，保持原样

            lines = [f'设 {var_name} 为 {subject}。']
            first = True
            for pattern_val, case_body in cases:
                pattern_val = pattern_val.strip()
                case_body = case_body.strip().rstrip('。').rstrip('.')
                if pattern_val == '_':
                    # 通配符 -> else
                    lines.append(f'否则：{case_body}。')
                elif first:
                    lines.append(f'如果 {var_name} 等于 {pattern_val}：{case_body}。')
                    first = False
                else:
                    lines.append(f'否则若 {var_name} 等于 {pattern_val}：{case_body}。')
            lines.append('结束。')
            return '\n'.join(lines)

        return pattern.sub(replace_match, source)

    def _preprocess_list_comprehension(self, source: str) -> str:
        """预处理列表推导

        [表达式 遍历 变量 之 列表]
        [表达式 遍历 变量 之 列表 如果 条件]

        转换为：
        __列表推导__(表达式, 变量, 列表)
        __列表推导筛选__(表达式, 变量, 列表, 条件)
        """
        import re
        # 匹配 [expr 遍历 var 之 iterable] 或 [... 遍历 var 之 iterable 如果 cond]
        pattern = re.compile(
            r'\[\s*(.+?)\s+遍历\s+(\S+)\s+之\s+(.+?)(?:\s+如果\s+(.+?))?\s*\]'
        )

        def replace_comp(m):
            expr = m.group(1).strip()
            var = m.group(2).strip()
            iterable = m.group(3).strip()
            condition = m.group(4)
            if condition:
                condition = condition.strip()
                return f'__列表推导筛选__({iterable}, 接收 {var}：返回 {expr}。, 接收 {var}：返回 {condition}。)'
            return f'__列表推导__({iterable}, 接收 {var}：返回 {expr}。)'

        return pattern.sub(replace_comp, source)

    def _preprocess_lambda(self, source: str) -> str:
        """预处理匿名函数

        接收 参数列表：返回 表达式。
        接收 x, y：返回 x 加 y。

        注意：只有当"接收"出现在表达式位置时才转换
        （段落定义中也有"接收"，但后面跟的是参数声明不是冒号）

        转换为：__匿名函数__(参数列表, 表达式)
        """
        import re
        # 匹配 接收 params：返回 expr。 或 接收 params：expr。
        # 注意：段落定义中 "段落 名称 接收 参数：" 后面是代码块不是单行表达式
        # 匿名函数的特点是 接收 后面直接跟参数名和冒号，且冒号后是单行表达式
        # 安全策略：只匹配括号内或赋值值中的匿名函数
        pattern = re.compile(
            r'接收\s+([^：:]+?)\s*[：:]\s*返回?\s*(.+?)[。.]'
        )

        def replace_lambda(m):
            params = m.group(1).strip()
            body = m.group(2).strip()
            return f'__匿名函数__({params}, {body})'

        return pattern.sub(replace_lambda, source)

    def _postprocess_ast(self, module: Module) -> Module:
        """后处理AST：将预处理标记还原为真实AST节点"""
        # 处理 __列表推导__、__列表推导筛选__、__匿名函数__ 函数调用
        # 转换为 ListComprehension / LambdaExpression AST 节点
        new_stmts = []
        for stmt in module.statements:
            result = self._transform_stmt(stmt)
            if result is not None:
                new_stmts.append(result)
            else:
                new_stmts.append(stmt)
        module.statements = new_stmts

        # 处理段落体中的语句
        for seg in module.segments:
            new_body = []
            for stmt in seg.body:
                result = self._transform_stmt(stmt)
                new_body.append(result if result else stmt)
            seg.body = new_body

        return module

    def _transform_stmt(self, stmt):
        """转换单个语句中的预处理标记"""
        # 处理表达式语句中的 __defer__ / __parallel__ 函数调用
        if isinstance(stmt, ExpressionStatement):
            expr = stmt.expression
            # 检测 __defer__(...) 函数调用 → DeferStatement
            if isinstance(expr, FunctionCall) and isinstance(expr.name, Identifier) and expr.name.name == '__defer__':
                body_stmts = []
                for arg in expr.arguments:
                    body_stmts.append(ExpressionStatement(expression=arg))
                return DeferStatement(
                    line=stmt.line, column=stmt.column,
                    body=body_stmts
                )
            # 检测 __parallel__(...) 函数调用 → AsyncScope
            if isinstance(expr, FunctionCall) and isinstance(expr.name, Identifier) and expr.name.name == '__parallel__':
                tasks = []
                for arg in expr.arguments:
                    tasks.append(ExpressionStatement(expression=arg))
                return AsyncScope(
                    line=stmt.line, column=stmt.column,
                    tasks=tasks
                )

            # 普通表达式处理
            result = self._transform_expr(stmt.expression)
            if result is not None:
                stmt.expression = result
                return stmt

        # 处理变量声明
        if isinstance(stmt, VariableDeclaration):
            expr = self._transform_expr(stmt.value)
            if expr is not None:
                stmt.value = expr
                return stmt

        # 处理赋值
        if isinstance(stmt, Assignment):
            expr = self._transform_expr(stmt.value)
            if expr is not None:
                stmt.value = expr
                return stmt

        # 处理打印
        if isinstance(stmt, PrintStatement):
            expr = self._transform_expr(stmt.value)
            if expr is not None:
                stmt.value = expr
                return stmt

        # 处理返回
        if isinstance(stmt, ReturnStatement) and stmt.value:
            expr = self._transform_expr(stmt.value)
            if expr is not None:
                stmt.value = expr
                return stmt

        return None

    def _transform_expr(self, expr):
        """转换表达式中的预处理标记"""
        if expr is None:
            return None

        # 检查是否是 __列表推导__ 或 __列表推导筛选__ 函数调用
        if isinstance(expr, FunctionCall):
            func_name = None
            if isinstance(expr.name, Identifier):
                func_name = expr.name.name

            if func_name == '__列表推导__':
                # __列表推导__(iterable, lambda)
                if len(expr.arguments) >= 2:
                    iterable = expr.arguments[0]
                    lambda_expr = expr.arguments[1]
                    if isinstance(lambda_expr, FunctionCall) and isinstance(lambda_expr.name, Identifier) and lambda_expr.name.name == '__匿名函数__':
                        return self._build_list_comprehension(lambda_expr, iterable, None)
                    # 如果lambda_expr本身已经是LambdaExpression
                    if isinstance(lambda_expr, LambdaExpression):
                        var = lambda_expr.parameters[0].name if lambda_expr.parameters else '当前项'
                        return ListComprehension(
                            line=expr.line, column=expr.column,
                            expression=lambda_expr.body, variable=var,
                            iterable=iterable, condition=None
                        )

            elif func_name == '__列表推导筛选__':
                # __列表推导筛选__(iterable, lambda, cond_lambda)
                if len(expr.arguments) >= 3:
                    iterable = expr.arguments[0]
                    lambda_expr = expr.arguments[1]
                    cond_lambda = expr.arguments[2]
                    var = '当前项'
                    body_expr = lambda_expr
                    cond_expr = cond_lambda
                    if isinstance(lambda_expr, FunctionCall) and isinstance(lambda_expr.name, Identifier) and lambda_expr.name.name == '__匿名函数__':
                        result = self._build_list_comprehension(lambda_expr, iterable, cond_lambda)
                        return result
                    if isinstance(lambda_expr, LambdaExpression):
                        var = lambda_expr.parameters[0].name if lambda_expr.parameters else '当前项'
                        body_expr = lambda_expr.body
                        cond_expr = cond_lambda.body if isinstance(cond_lambda, LambdaExpression) else cond_lambda
                        return ListComprehension(
                            line=expr.line, column=expr.column,
                            expression=body_expr, variable=var,
                            iterable=iterable, condition=cond_expr
                        )

            elif func_name == '__匿名函数__':
                return self._build_lambda(expr)

            elif func_name == '__await__':
                # 等待(表达式) → AwaitExpression(表达式)
                if len(expr.arguments) >= 1:
                    arg_expr = expr.arguments[0]
                    # 递归转换参数
                    transformed_arg = self._transform_expr(arg_expr) or arg_expr
                    return AwaitExpression(
                        line=expr.line, column=expr.column,
                        expression=transformed_arg
                    )

            # 递归处理函数参数
            new_args = []
            changed = False
            for arg in expr.arguments:
                transformed = self._transform_expr(arg)
                if transformed is not None:
                    new_args.append(transformed)
                    changed = True
                else:
                    new_args.append(arg)
            if changed:
                expr.arguments = new_args
                return expr

        # 递归处理二元运算
        if isinstance(expr, BinaryOp):
            left = self._transform_expr(expr.left)
            right = self._transform_expr(expr.right)
            if left is not None:
                expr.left = left
            if right is not None:
                expr.right = right
            if left is not None or right is not None:
                return expr

        # 递归处理列表字面量
        if isinstance(expr, ListLiteral):
            new_elements = []
            changed = False
            for e in expr.elements:
                transformed = self._transform_expr(e)
                if transformed is not None:
                    new_elements.append(transformed)
                    changed = True
                else:
                    new_elements.append(e)
            if changed:
                expr.elements = new_elements
                return expr

        return None

    def _build_list_comprehension(self, lambda_call: FunctionCall, iterable, cond_lambda=None):
        """从 __匿名函数__ 调用构建 ListComprehension"""
        if len(lambda_call.arguments) >= 2:
            # 参数1是参数名（ID），参数2是表达式
            params = []
            first_arg = lambda_call.arguments[0]
            if isinstance(first_arg, Identifier):
                var = first_arg.name
            else:
                var = str(first_arg)
            body_expr = lambda_call.arguments[1]
            condition = None
            if cond_lambda:
                if isinstance(cond_lambda, FunctionCall) and isinstance(cond_lambda.name, Identifier) and cond_lambda.name.name == '__匿名函数__':
                    condition = cond_lambda.arguments[1] if len(cond_lambda.arguments) >= 2 else None
                elif isinstance(cond_lambda, LambdaExpression):
                    condition = cond_lambda.body
                else:
                    condition = cond_lambda
            return ListComprehension(
                line=lambda_call.line, column=lambda_call.column,
                expression=body_expr, variable=var,
                iterable=iterable, condition=condition
            )
        return None

    def _build_lambda(self, func_call: FunctionCall):
        """从 __匿名函数__ 调用构建 LambdaExpression"""
        from light_ast import Parameter
        if len(func_call.arguments) >= 2:
            # 参数列表：可能是单个ID或逗号分隔的多个ID
            params = []
            first_arg = func_call.arguments[0]
            if isinstance(first_arg, Identifier):
                params.append(Parameter(line=first_arg.line, column=first_arg.column, name=first_arg.name))
            elif isinstance(first_arg, FunctionCall):
                # 多个参数被解析为函数调用
                for arg in first_arg.arguments:
                    if isinstance(arg, Identifier):
                        params.append(Parameter(line=arg.line, column=arg.column, name=arg.name))
            body = func_call.arguments[1]
            return LambdaExpression(
                line=func_call.line, column=func_call.column,
                parameters=params, body=body
            )
        return None


# =============================================================================
# 高层解析接口
# =============================================================================

def parse_source(source: str) -> Module:
    """解析光明源代码，返回 AST（错误信息已包含中文翻译）"""
    from light_error_handler import format_error_context

    parser = LightParser()
    module = parser.parse(source)
    if parser.errors:
        # 尝试显示行号和源码上下文
        import re
        for err in parser.errors:
            print(f"[语法错误] {err}", file=sys.stderr)
            # 尝试从错误消息中提取行号并显示上下文
            m = re.search(r'第(\d+)行', err)
            if m:
                line = int(m.group(1))
                col_m = re.search(r'第(\d+)列', err)
                column = int(col_m.group(1)) if col_m else 0
                context = format_error_context(source, line, column)
                if context:
                    print(f"{context}\n", file=sys.stderr)
    return module


def parse_file(filepath: str) -> Module:
    """从文件读取光明源代码并解析"""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    return parse_source(source)