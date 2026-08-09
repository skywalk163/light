# -*- coding: utf-8 -*-
"""
光明（Light）编译器错误处理
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class SourceLocation:
    """源码位置"""
    line: int
    column: int
    filename: Optional[str] = None
    
    def __str__(self):
        if self.filename:
            return f"{self.filename}:{self.line}:{self.column}"
        return f"行{self.line}:列{self.column}"


class LightError(Exception):
    """光明编译器基础错误"""
    
    def __init__(self, message: str, location: Optional[SourceLocation] = None):
        self.message = message
        self.location = location
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.location:
            return f"[{self.location}] {self.message}"
        return self.message


class LexerError(LightError):
    """词法错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0, 
                 filename: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        super().__init__(f"词法错误: {message}", location)


class ParserError(LightError):
    """语法错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0,
                 filename: Optional[str] = None, token: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        self.token = token
        
        msg = f"语法错误: {message}"
        if token:
            msg += f" (在 '{token}' 附近)"
        
        super().__init__(msg, location)


class SemanticError(LightError):
    """语义错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0,
                 filename: Optional[str] = None, symbol: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        self.symbol = symbol
        
        msg = f"语义错误: {message}"
        if symbol:
            msg += f" (符号: {symbol})"
        
        super().__init__(msg, location)


class CodeGenError(LightError):
    """代码生成错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0,
                 filename: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        super().__init__(f"代码生成错误: {message}", location)


class TypeError(LightError):
    """类型错误"""
    
    def __init__(self, message: str, expected_type: Optional[str] = None,
                 actual_type: Optional[str] = None, line: int = 0, column: int = 0,
                 filename: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        self.expected_type = expected_type
        self.actual_type = actual_type
        
        msg = f"类型错误: {message}"
        if expected_type and actual_type:
            msg += f" (期望 {expected_type}, 实际 {actual_type})"
        
        super().__init__(msg, location)


class NameError(LightError):
    """名称错误"""
    
    def __init__(self, name: str, line: int = 0, column: int = 0,
                 filename: Optional[str] = None):
        location = SourceLocation(line, column, filename) if line > 0 else None
        super().__init__(f"未定义的名称: {name}", location)


class CompileError(LightError):
    """编译错误（综合错误）"""
    
    def __init__(self, message: str, errors: Optional[List[LightError]] = None):
        self.errors = errors or []
        super().__init__(message)
    
    def add_error(self, error: LightError):
        """添加错误"""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def __str__(self):
        if not self.errors:
            return self.message
        
        lines = [self.message]
        for error in self.errors:
            lines.append(f"  - {error}")
        return '\n'.join(lines)


# 错误处理辅助函数

def error_context(line: int, column: int, source: str, context_lines: int = 2) -> str:
    """
    生成错误上下文信息
    
    Args:
        line: 行号
        column: 列号
        source: 源代码
        context_lines: 上下文行数
    
    Returns:
        格式化的错误上下文
    """
    lines = source.split('\n')
    
    start_line = max(0, line - context_lines - 1)
    end_line = min(len(lines), line + context_lines)
    
    context = []
    for i in range(start_line, end_line):
        line_num = i + 1
        prefix = '>>>' if line_num == line else '   '
        context.append(f"{prefix} {line_num:4d} | {lines[i]}")
        
        if line_num == line:
            # 添加错误位置指示
            pointer = ' ' * (len(prefix) + len(str(line_num)) + 8 + column - 1) + '^'
            context.append(pointer)
    
    return '\n'.join(context)
