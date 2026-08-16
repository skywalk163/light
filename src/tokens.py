"""
光明（Light）编程语言 - Token 定义

基于设计规范：
- 决策27：双字关键字
- 决策28：元数驱动解析
- 决策29：三层分词机制
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    """Token 类型"""
    
    # 字面量
    NUMBER = auto()      # 数字（整数或浮点数）
    STRING = auto()      # 字符串
    FSTRING = auto()     # f-string（格式化字符串）
    BYTES = auto()       # 字节串 b"..." / B"..."（v7 新单 H）
    CHINESE_NUM = auto() # 中文数字（三、五、十等）
    
    # 标识符和关键字
    IDENTIFIER = auto()  # 标识符（变量名、函数名）
    KEYWORD = auto()     # 关键字
    
    # 运算符
    OPERATOR = auto()    # 运算符（加、减、乘、除等）
    
    # 符号
    DOT = auto()         # 英文点号 .（成员访问符）
    PERIOD = auto()      # 中文句号 。（语句结束符）
    COMMA = auto()       # 逗号 ，（管道操作符）
    SEMICOLON = auto()   # 分号 ；
    COLON = auto()       # 冒号 ：
    LPAREN = auto()      # 左括号 （
    RPAREN = auto()      # 右括号 ）
    LBRACKET = auto()    # 左方括号 【
    RBRACKET = auto()    # 右方括号 】
    LBRACE = auto()      # 左花括号 {
    RBRACE = auto()      # 右花括号 }
    EQUALS = auto()      # 等于 =
    AT = auto()          # @ 装饰器符号
    PLUS = auto()        # + 加号（字符串连接等）
    MINUS = auto()       # - 减号
    STAR = auto()        # * 乘号
    SLASH = auto()       # / 除号
    PERCENT = auto()     # % 模运算
    LESS = auto()        # < 小于
    GREATER = auto()     # > 大于
    LESS_EQUAL = auto()  # <= 小于等于
    GREATER_EQUAL = auto()  # >= 大于等于
    EQ_EQ = auto()       # == 等于比较
    NOT_EQ = auto()      # != 不等于
    BANG = auto()        # 感叹号 ! 或 ！（可空解包）
    
    # 段落标记
    LBOOK = auto()       # 左书名号 《
    RBOOK = auto()       # 右书名号 》
    
    # 管道操作符
    ARROW = auto()       # 箭头 ->
    PIPE = auto()        # 管道操作符（，或 ->）
    WALRUS = auto()      # 海象运算符 := （不支持）
    
    # 结构
    INDENT = auto()      # 缩进增加
    DEDENT = auto()      # 缩进减少
    NEWLINE = auto()     # 换行
    
    # 嵌入块
    EMBED_BLOCK = auto()  # 嵌入的外语代码块（Python/C等）

    # 特殊
    EOF = auto()         # 文件结束


@dataclass(slots=True)
class Token:
    """Token 数据结构"""
    type: TokenType
    value: Any
    line: int
    col: int
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return False
        return (self.type == other.type and 
                self.value == other.value and
                self.line == other.line and
                self.col == other.col)
