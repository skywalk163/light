# -*- coding: utf-8 -*-
"""
光明编译器核心模块
"""

from .interfaces import (
    ILexer, IParser, ISemanticAnalyzer, ICodeGenerator, ICompiler,
    Position, SourceLocation
)
from .errors import (
    LightError, LexerError, ParserError, SemanticError, CodeGenError,
    TypeError, NameError, CompileError, error_context
)
from .config import LightConfig, OutputFormat, OptimizationLevel, get_default_config

__all__ = [
    # 接口
    'ILexer', 'IParser', 'ISemanticAnalyzer', 'ICodeGenerator', 'ICompiler',
    'Position', 'SourceLocation',
    
    # 错误
    'LightError', 'LexerError', 'ParserError', 'SemanticError', 'CodeGenError',
    'TypeError', 'NameError', 'CompileError', 'error_context',
    
    # 配置
    'LightConfig', 'OutputFormat', 'OptimizationLevel', 'get_default_config',
]
