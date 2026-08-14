"""
光明（Light）编程语言 - 语法解析器核心框架

提供基础解析框架：
- 词法分析集成
- Token 流管理
- 辅助方法（_current, _consume, _match, _peek）
- 操作符映射表
"""

from typing import List, Any, Optional, Dict, Union
from lexer import Lexer, LexerError
from tokens import Token, TokenType
from keywords import VERB_ARITY, KEYWORDS_DOUBLE, KEYWORDS_SPECIAL
from ast_nodes_v3 import *
import os
import sys


# =============================================================================
# 解析错误类
# =============================================================================

class ParseError(Exception):
    """语法解析错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, token_value: str = None, source_lines: list = None, filename: str = None):
        self.message = message
        self.line = line
        self.col = col
        self.token_value = token_value
        self.source_lines = source_lines or []
        self.filename = filename
        
        # 根据错误内容生成修复建议
        hint = _generate_hint(message, token_value)
        
        parts = []
        
        # 错误类型（带颜色标记）
        parts.append("\n┌─ 语法错误")
        
        # 位置信息
        if line:
            pos_info = f"行 {line}"
            if col:
                pos_info += f", 列 {col}"
            if filename:
                pos_info += f" ({os.path.basename(filename)})"
            parts.append(f"│ 位置: {pos_info}")
        
        # 源代码上下文
        if line and self.source_lines:
            parts.append("│")
            for i in range(max(0, line - 2), min(len(self.source_lines), line + 1)):
                line_num = i + 1
                line_content = self.source_lines[i].rstrip()
                prefix = "│ " if line_num != line else "│→"
                parts.append(f"{prefix} {line_num:4d} │ {line_content}")
                # 在错误列位置添加指示符
                if line_num == line and col:
                    parts.append(f"│       │ {' ' * (min(col, 60) - 1)}^ 错误在这里")
        
        # 错误信息（清理 TokenType 前缀，使消息更友好）
        friendly_msg = _make_friendly(message)
        parts.append(f"│ 原因: {friendly_msg}")
        if token_value:
            parts.append(f"│ 附近: '{token_value}'")
        
        # 修复建议
        if hint:
            parts.append(f"│ 建议: {hint}")
        
        # T1.3 教程链接
        tutorial_link = _get_tutorial_link(message)
        if tutorial_link:
            parts.append(f"│ 教程: {tutorial_link}")
        
        parts.append("└─")
        
        super().__init__('\n'.join(parts))


def _make_friendly(message: str) -> str:
    """将内部错误消息转换为用户友好的表述"""
    import re
    # TokenType.NAME = 'value' -> value
    message = re.sub(r"TokenType\.(\w+)\s*=\s*'([^']*)'", r"「\2」", message)
    # TokenType.NAME (no value) -> 友好名称
    _token_friendly = {
        'COLON': '冒号「:」',
        'LPAREN': '左括号「(」',
        'RPAREN': '右括号「)」',
        'LBRACKET': '左方括号「[」',
        'RBRACKET': '右方括号「]」',
        'LBRACE': '左花括号「{」',
        'RBRACE': '右花括号「}」',
        'DOT': '点号「.」',
        'PERIOD': '句号「。」',
        'COMMA': '逗号「,」',
        'EQUALS': '等号「=」',
        'STAR': '星号「*」',
        'SLASH': '斜杠「/」',
        'PLUS': '加号「+」',
        'MINUS': '减号「-」',
        'KEYWORD': '关键字',
        'IDENTIFIER': '标识符（名称）',
        'NUMBER': '数字',
        'STRING': '字符串',
        'NEWLINE': '换行',
        'INDENT': '缩进',
        'DEDENT': '取消缩进',
        'AT': '装饰符「@」',
        'BANG': '感叹号「!」',
        'PERCENT': '百分号「%」',
        'LESS': '小于号「<」',
        'GREATER': '大于号「>」',
    }
    def _replace_token(m):
        name = m.group(1)
        return _token_friendly.get(name, name)
    message = re.sub(r'TokenType\.(\w+)', _replace_token, message)
    # Token(xxx, 'value', ...) -> 'value'
    message = re.sub(r"Token\((\w+),\s*'([^']*)',?\s*[^)]*\)", r"「\2」", message)
    return message


def _generate_hint(message: str, token_value: str = None) -> str:
    """根据错误模式生成修复建议"""
    if not token_value:
        # 无 token_value 的通用建议
        if '输入意外结束' in message or '意外的输入结束' in message:
            return '代码可能不完整，请检查是否缺少右括号「)」或冒号「:」。句号「。」是可选的，不需要每句末尾都加。'
        if '期望句号或冒号' in message:
            return '函数/类定义后面需要冒号「:」。句号「。」是可选的。'
        return ''
    
    tv = token_value
    
    # 保留关键字用作变量名
    _reserved_hints = {
        '属性': '「属性」是保留关键字，不能用作变量名。请改用其他名称，如「特性」或「字段」。',
        '构造': '「构造」是保留关键字，用于定义构造函数。请改用其他变量名。',
        '函数': '「函数」是保留关键字，用于定义函数。请改用其他变量名，如「方法」或「过程」。',
        '类': '「类」是保留关键字，用于定义类。请改用其他变量名。',
        '如果': '「如果」是保留关键字。如需条件判断，请使用「如果 条件: ... 否则 ...」语法。',
        '否则': '「否则」需要跟在「如果」块后面，且后面需要冒号「:」。',
        '循环': '「循环」是保留关键字。如需循环，请使用「循环 ... 直到 ...」或「遍历 变量 于 ...」语法。',
        '返回': '「返回」用于函数返回值，后面需要跟返回表达式。如：返回 甲 加 乙。',
        '导入': '「导入」用于导入模块。如：导入 数学。 或 从 数学 导入 圆周率。',
        '匹配': '「匹配」用于模式匹配。如：匹配 变量: 情况 值: ... 默认: ... 结束匹配。',
        '情况': '「情况」只能在「匹配」块内部使用。',
        '己': '「己」表示对象自身（相当于 Python 的 self），只能在类方法内部使用。',
        '父': '「父」表示父类（相当于 Python 的 super），用于调用父类方法。',
        # T1.1 新增关键字提示
        '遍历': '「遍历」用于循环遍历列表或范围。如：遍历 项 于 列表: ... 或 遍历 数 于 1至10: ...',
        '当': '「当」用于条件循环（相当于 while）。如：当 条件: ...',
        '尝试': '「尝试」用于异常处理。如：尝试: ... 捕获 错误类型 为 变量: ...',
        '捕获': '「捕获」在「尝试」块中用于捕获异常。如：捕获 ValueError 为 e: ...',
        '抛出': '「抛出」用于主动抛出异常。如：抛出 ValueError("消息")。',
        '最终': '「最终」在「尝试」块中用于无论是否异常都执行的代码。',
        '静态': '「静态」修饰函数使其成为静态方法。如：静态 函数 方法名(): ...',
        '异步': '「异步」修饰函数使其成为异步函数。如：异步 函数 名字(): ...',
        '等待': '「等待」用于等待异步操作完成（相当于 await）。如：设 结果 为 等待 异步函数()。',
        '使用': '「使用」用于上下文管理器（相当于 with）。如：使用 文件 为 变量: ...',
        '嵌入': '「嵌入」用于在段言中嵌入 Python/C 代码块。如：嵌入 Python: ... 结束嵌入',
        '标注': '「标注」用于自定义装饰器。如：标注 装饰器名\n函数 名字(): ...',
        '定义': '「定义」用于声明常量。如：定义 圆周率 为 3.14159。',
        '继承': '「继承」用于类继承。如：类 子类 继承 父类: ...',
        '段落': '「段落」是「函数」的兼容写法，用于定义函数。如：段落 名字(参数): ...',
        '接口': '「接口」用于定义接口。如：接口 名字: ...',
        '实现': '「实现」用于类实现接口。如：类 子类 实现 接口名: ...',
        '枚举': '「枚举」用于定义枚举类型（FFI）。如：枚举 名字: ...',
        '结构体': '「结构体」用于定义C结构体（FFI）。如：结构体 名字: ...',
        '异常': '「异常」不是段言关键字。如需异常处理，请使用「尝试/捕获/抛出」语法。',
    }
    
    if tv in _reserved_hints:
        return _reserved_hints[tv]
    
    # T1.2 分词冲突检测
    _split_conflict_hints = {
        '函': '词法分析可能将包含「函数」的标识符错误拆分。请尝试在关键字和标识符之间加空格，或更换变量名。',
        '数': '词法分析可能将包含「数据」「数字」等的标识符错误拆分。请尝试加空格分隔。',
        '输': '词法分析可能将包含「输出」的标识符错误拆分。请尝试加空格分隔。',
        '返': '词法分析可能将包含「返回」的标识符错误拆分。请尝试加空格分隔。',
    }
    if tv in _split_conflict_hints:
        return _split_conflict_hints[tv]
    
    # T1.3 教程链接提示
    _tutorial_links = {
        'COLON': '参考教程：30分钟入门段言.md 第3章「条件判断」',
        'KEYWORD': '参考教程：30分钟入门段言.md 第2章「变量与赋值」',
        'FUNCTION': '参考教程：30分钟入门段言.md 第6章「函数/段落」',
        'CLASS': '参考教程：30分钟入门段言.md 第8章「类与对象」',
        'LPAREN': '参考教程：30分钟入门段言.md 第6章「函数/段落」',
        'RPAREN': '参考教程：30分钟入门段言.md 第6章「函数/段落」',
        'INDENT': '参考教程：30分钟入门段言.md 第3章「条件判断」',
        'DEDENT': '参考教程：30分钟入门段言.md 第3章「条件判断」',
    }
    # 如果消息中包含 TokenType 相关信息，追加教程链接
    for tok_type, link in _tutorial_links.items():
        if f'TokenType.{tok_type}' in message:
            # 先返回标点错误提示，教程链接在后面追加
            break
    
    # 常见标点错误
    if tv == '=':
        return '光明使用「为」进行赋值。如：设 甲 为 10。而不是 甲 = 10。'
    if tv == ':':
        if '期望标识符' in message:
            return '函数/类定义需要名称。如：函数 名字(参数): 或 类 名字:'
        return '检查冒号「:」位置是否正确。函数定义、条件、循环后面都需要冒号。'
    if tv == ')':
        return '可能缺少左括号「(」或参数不完整。'
    if tv == '(':
        return '可能缺少右括号「)」。'
    if tv == '.':
        return '成员访问使用「.」或「的」。如：对象的属性 或 对象.属性。句号使用「。」。'
    if tv == '。':
        return '句号「。」用于结束语句。如果这不是语句结尾，请检查表达式是否完整。'
    
    # TokenType 相关
    if 'TokenType.COLON' in message or '期望 TokenType.COLON' in message:
        return '可能缺少冒号「:」。函数定义、条件、循环后面都需要冒号。'
    if 'TokenType.RPAREN' in message:
        return '可能缺少右括号「)」。'
    if 'TokenType.RBRACKET' in message:
        return '可能缺少右方括号「】」或「]」。'
    
    return ''


def _get_tutorial_link(message: str) -> str:
    """T1.3: 根据错误消息中的 TokenType 返回教程链接"""
    _tutorial_links = {
        'COLON': '30分钟入门段言.md 第3章「条件判断」',
        'LPAREN': '30分钟入门段言.md 第6章「函数/段落」',
        'RPAREN': '30分钟入门段言.md 第6章「函数/段落」',
        'INDENT': '30分钟入门段言.md 第3章「条件判断」',
        'DEDENT': '30分钟入门段言.md 第3章「条件判断」',
        'LBRACKET': '30分钟入门段言.md 第7章「列表与字典」',
        'RBRACKET': '30分钟入门段言.md 第7章「列表与字典」',
    }
    for tok_type, link in _tutorial_links.items():
        if f'TokenType.{tok_type}' in message:
            return link
    return ''


# =============================================================================
# 递归下降解析器 - 核心基类
# =============================================================================

class LightParserCore:
    """光明完整语法解析器核心基类"""
    
    # 运算符动词集合（类常量，避免重复创建）
    OPERATOR_VERBS = frozenset({'加', '减', '乘', '除', '加上', '减去', '乘以', '除以', 
                                '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
                                '不小于', '不大于',  # P2-3：比较运算符短形式
                                '包含',  # 包含关系运算符
                                '模', '幂', '为'})
    
    # 操作符映射表（类常量）
    COMPARISON_OP_MAP = {
        '大于': '>', '小于': '<', '等于': '==',
        '不等于': '!=', '大于等于': '>=', '小于等于': '<=',
        '不小于': '>=', '不大于': '<=',  # P2-3：比较运算符短形式
        '包含': '@@contains@@',  # 特殊处理：左操作数包含右操作数 → right in left
        '为': '==',
    }
    ADD_OP_MAP = {'加': '+', '减': '-', '加上': '+', '减去': '-'}
    MUL_OP_MAP = {'乘': '*', '除': '/', '模': '%', '乘以': '*', '除以': '/', '模以': '%', '取余': '%', '整除': '//'}
    POWER_OP_MAP = {'幂': '**', '幂以': '**'}
    LOGICAL_OP_MAP = {'且': 'and', '与': 'and', '或': 'or'}
    
    def __init__(self):
        self.lexer = Lexer()
        self.tokens: List[Token] = []
        self.pos = 0
        self._in_foreach_context = False  # 在遍历循环中禁用"之"的成员访问解析

    def _error(self, message: str, line: int = 0, col: int = 0, token_value: str = None):
        """报告解析错误（抛出 ParseError）"""
        raise ParseError(message, line, col, token_value, filename=getattr(self, '_filename', None))
    
    def parse(self, source: str, filename: str = None, extra_definitions: set = None) -> Module:
        """解析光明代码，支持多错误收集（T1.4 恐慌模式 Error Recovery）
        
        Args:
            source: 光明源代码
            filename: 源文件路径（用于错误信息显示）
            extra_definitions: 跨模块的用户定义标识符集合（如已注册模块的导出函数名）
        """
        self._filename = filename
        
        # 词法分析（传入跨模块定义，使 lexer 能识别其他模块的函数名）
        tokens = self.lexer.tokenize(source, extra_definitions=extra_definitions)
        
        # 过滤掉 EOF，保留 NEWLINE、INDENT/DEDENT 用于块结构解析
        self.tokens = [t for t in tokens if t.type != TokenType.EOF]
        self.pos = 0
        
        # 保存源代码行用于错误上下文显示
        self._source_lines = source.splitlines()
        
        # 解析模块
        return self._parse_module_with_recovery()
    
    def _parse_module_with_recovery(self) -> Module:
        """T1.4: 带错误恢复的模块解析
        
        遇到语法错误时，跳到下一个语句边界继续解析，
        最后一次性报告所有收集到的错误。
        """
        errors = []
        statements = []
        
        while self._current():
            tok = self._current()
            
            # 跳过外层 DEDENT
            if tok.type == TokenType.DEDENT:
                dedent_level = getattr(tok, 'value', None)
                if dedent_level is None or dedent_level == 0:
                    self._consume(TokenType.DEDENT)
                    continue
            
            # 跳过空行
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                continue
            
            # 跳过孤立句号
            if tok.type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
                continue
            
            # 跳过"结束"关键字
            if tok.type == TokenType.KEYWORD and tok.value == '结束':
                self._consume(TokenType.KEYWORD, '结束')
                continue
            if tok.type == TokenType.IDENTIFIER and tok.value == '结束':
                self._consume(TokenType.IDENTIFIER, '结束')
                continue
            
            # 尝试解析一个语句
            try:
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)
                else:
                    # 无法解析，前进一个 token 避免死循环
                    self.pos += 1
            except ParseError as e:
                # 补充源代码上下文
                if not e.source_lines and hasattr(self, '_source_lines'):
                    e.source_lines = self._source_lines
                errors.append(e)
                # 同步到下一个语句边界
                self._synchronize_to_statement_boundary()
            except (IndexError, KeyError) as e:
                # 内部异常，包装为 ParseError
                tok = self._current()
                pe = ParseError(
                    f"内部解析异常: {type(e).__name__}: {e}",
                    tok.line if tok else 0,
                    tok.col if tok else 0,
                    tok.value if tok else None,
                    filename=getattr(self, '_filename', None)
                )
                if hasattr(self, '_source_lines'):
                    pe.source_lines = self._source_lines
                errors.append(pe)
                self._synchronize_to_statement_boundary()
        
        # 如果有错误，报告错误
        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise self._build_aggregate_error(errors)

        return Module(statements)

    # 一次最多详细展示多少个错误。超出部分只做归类统计——
    # 语法错误绝大多数是级联的，第一个错之后的几十上百条都是它的回声，
    # 全量打印会把真正有用的第一条淹没掉。
    MAX_REPORTED_ERRORS = 8

    def _build_aggregate_error(self, errors):
        """把多个语法错误聚合成一份可读的报告。

        策略：按出现顺序展示前 MAX_REPORTED_ERRORS 条完整信息，
        其余按「原因」归类只给计数，并提示如何查看全部。
        完整错误列表挂在异常的 all_errors 属性上，供工具链程序化读取。
        """
        total = len(errors)
        shown = errors[:self.MAX_REPORTED_ERRORS]
        rest = errors[self.MAX_REPORTED_ERRORS:]

        head = (f"发现 {total} 个语法错误"
                f"（下面详列前 {len(shown)} 个，建议从第 1 个开始修）:\n\n")
        body = "\n\n---\n\n".join(
            f"错误 {i + 1}/{total}:\n{str(e)}" for i, e in enumerate(shown)
        )

        tail = ""
        if rest:
            buckets = {}
            for e in rest:
                key = (getattr(e, 'message', None) or str(e).strip().splitlines()[0])[:70]
                buckets[key] = buckets.get(key, 0) + 1
            tail = f"\n\n---\n\n另有 {len(rest)} 个错误（按原因归类）:\n"
            for reason, cnt in sorted(buckets.items(), key=lambda kv: -kv[1])[:8]:
                tail += f"  × {cnt:<4} {reason}\n"
            if len(buckets) > 8:
                tail += f"  ...（还有 {len(buckets) - 8} 类）\n"
            tail += ("\n提示：这些多半是第 1 个错误引发的级联错误，"
                     "修好前面的通常会一起消失。")

        agg = ParseError(head + body + tail)
        agg.all_errors = errors
        agg.error_count = total
        return agg
    
    def _synchronize_to_statement_boundary(self):
        """T1.4: 恐慌模式同步 — 跳过 token 直到下一个语句边界
        
        语句边界：句号「。」后、换行后、DEDENT 后、文件结束。
        策略：先尝试找到句号，如果找不到就跳到下一个 NEWLINE。
        """
        # 最多跳过 200 个 token 避免无限循环
        max_skip = 200
        skipped = 0
        
        while self._current() and skipped < max_skip:
            tok = self._current()
            
            # 句号：消耗后结束同步
            if tok.type == TokenType.PERIOD:
                self._consume(TokenType.PERIOD)
                return
            
            # 换行：消耗后结束同步（下一行是新语句）
            if tok.type == TokenType.NEWLINE:
                self._consume(TokenType.NEWLINE)
                return
            
            # DEDENT：消耗后结束同步
            if tok.type == TokenType.DEDENT:
                self._consume(TokenType.DEDENT)
                return
            
            # 跳过当前 token
            self.pos += 1
            skipped += 1
    
    def _current(self) -> Optional[Token]:
        """获取当前 Token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _peek(self, offset: int = 0) -> Optional[Token]:
        """查看指定位置的 Token"""
        idx = self.pos + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return None
    
    def _consume(self, expected_type=None, expected_value=None) -> Token:
        """消耗并返回当前 Token"""
        tok = self._current()
        if tok is None:
            last_tok = self.tokens[-1] if self.tokens else None
            line = last_tok.line if last_tok else 0
            col = last_tok.col if last_tok else 0
            hint = ""
            if expected_type:
                hint = f" (期望 {expected_type}"
                if expected_value:
                    hint += f" = '{expected_value}'"
                hint += ")"
            raise ParseError(f"输入意外结束{hint}（建议检查是否缺少表达式或语句）", line, col, filename=getattr(self, '_filename', None))
        
        if expected_type and tok.type != expected_type:
            raise ParseError(f"期望 {expected_type}，但得到 {tok.type}（附近: '{tok.value}'）", tok.line, tok.col, tok.value, filename=getattr(self, '_filename', None))
        
        if expected_value and tok.value != expected_value:
            raise ParseError(f"期望'{expected_value}'，但得到'{tok.value}'（附近: '{tok.value}'）", tok.line, tok.col, filename=getattr(self, '_filename', None))
        
        self.pos += 1
        return tok
    
    def _match(self, token_type, value=None) -> bool:
        """检查当前 Token 是否匹配"""
        tok = self._current()
        if tok is None:
            return False
        if tok.type != token_type:
            return False
        if value is not None and tok.value != value:
            return False
        return True
    
    # =========================================================================
    # 段落/函数 关键字兼容辅助方法
    # '函数' 是首选关键字，'段落' 和 '段' 是向后兼容别名
    # =========================================================================
    
    PARAGRAPH_KEYWORDS = frozenset({'函数', '段落', '段'})
    
    def _is_paragraph_kw(self, tok: Optional[Token]) -> bool:
        """检查 token 是否是段落/函数定义关键字（函数/段落/段）"""
        return tok is not None and tok.type == TokenType.KEYWORD and tok.value in self.PARAGRAPH_KEYWORDS
    
    def _match_paragraph_kw(self) -> bool:
        """检查当前 token 是否是段落/函数定义关键字（函数/段落/段）"""
        return self._is_paragraph_kw(self._current())
    
    def _consume_paragraph_kw(self) -> Token:
        """消耗段落/函数定义关键字（函数/段落/段），返回该 token"""
        tok = self._current()
        if tok is not None and tok.type == TokenType.KEYWORD and tok.value in self.PARAGRAPH_KEYWORDS:
            self.pos += 1
            return tok
        raise ParseError(
            f"期望'函数'（或兼容写法'段落'/'段'），但得到 {tok.type if tok else '输入结束'}"
            f"（附近: '{tok.value if tok else ''}'）",
            tok.line if tok else 0, tok.col if tok else 0, tok.value if tok else None,
            filename=getattr(self, '_filename', None)
        )