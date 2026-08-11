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
import sys


# =============================================================================
# 解析错误类
# =============================================================================

class ParseError(Exception):
    """语法解析错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, token_value: str = None, source_lines: list = None):
        self.message = message
        self.line = line
        self.col = col
        self.token_value = token_value
        self.source_lines = source_lines or []
        
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
        'DOT': '句号「。」或点号「.」',
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
            return '代码可能不完整，请检查是否缺少语句结尾的句号「。」或缺少右括号「)」。'
        if '期望句号或冒号' in message:
            return '函数/类定义后面需要冒号「:」，语句结尾需要句号「。」。'
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
        '返回': '「返回」用于函数返回值，后面需要跟返回表达式。如：返回 甲 + 乙。',
        '导入': '「导入」用于导入模块。如：导入 数学。 或 导入 Python: numpy。',
        '匹配': '「匹配」用于模式匹配。如：匹配 变量: 情况 值: ... 默认: ... 结束匹配。',
        '情况': '「情况」只能在「匹配」块内部使用。',
        '己': '「己」表示对象自身（相当于 Python 的 self），只能在类方法内部使用。',
        '父': '「父」表示父类（相当于 Python 的 super），用于调用父类方法。',
    }
    
    if tv in _reserved_hints:
        return _reserved_hints[tv]
    
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


# =============================================================================
# 递归下降解析器 - 核心基类
# =============================================================================

class LightParserCore:
    """光明完整语法解析器核心基类"""
    
    # 运算符动词集合（类常量，避免重复创建）
    OPERATOR_VERBS = frozenset({'加', '减', '乘', '除', '加上', '减去', '乘以', '除以', 
                                '大于', '小于', '等于', '不等于', '大于等于', '小于等于',
                                '不小于', '不大于',  # P2-3：比较运算符短形式
                                '模', '幂', '为'})
    
    # 操作符映射表（类常量）
    COMPARISON_OP_MAP = {
        '大于': '>', '小于': '<', '等于': '==',
        '不等于': '!=', '大于等于': '>=', '小于等于': '<=',
        '不小于': '>=', '不大于': '<=',  # P2-3：比较运算符短形式
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
        raise ParseError(message, line, col, token_value)
    
    def parse(self, source: str) -> Module:
        """解析光明代码"""
        # 词法分析
        tokens = self.lexer.tokenize(source)
        
        # 过滤掉 EOF，保留 NEWLINE、INDENT/DEDENT 用于块结构解析
        self.tokens = [t for t in tokens if t.type != TokenType.EOF]
        self.pos = 0
        
        # 解析模块
        return self._parse_module()
    
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
            raise ParseError(f"输入意外结束{hint}（建议检查是否缺少表达式或语句）", line, col)
        
        if expected_type and tok.type != expected_type:
            raise ParseError(f"期望 {expected_type}，但得到 {tok.type}（附近: '{tok.value}'）", tok.line, tok.col, tok.value)
        
        if expected_value and tok.value != expected_value:
            raise ParseError(f"期望'{expected_value}'，但得到'{tok.value}'（附近: '{tok.value}'）", tok.line, tok.col)
        
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
            tok.line if tok else 0, tok.col if tok else 0, tok.value if tok else None
        )