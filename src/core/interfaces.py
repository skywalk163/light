# -*- coding: utf-8 -*-
"""
光明（Light）编译器核心接口定义
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from dataclasses import dataclass


@dataclass
class Position:
    """源码位置"""
    line: int
    column: int
    filename: Optional[str] = None
    
    def __str__(self):
        if self.filename:
            return f"{self.filename}:{self.line}:{self.column}"
        return f"行{self.line}:列{self.column}"


class SourceLocation:
    """源码位置信息"""
    
    def __init__(self, start: Position, end: Optional[Position] = None):
        self.start = start
        self.end = end or start


class ILexer(ABC):
    """词法分析器接口"""
    
    @abstractmethod
    def tokenize(self, source: str, filename: Optional[str] = None) -> List[Any]:
        """
        将源码转换为 Token 流
        
        Args:
            source: 源代码字符串
            filename: 文件名（用于错误报告）
        
        Returns:
            Token 列表
        """
        pass


class IParser(ABC):
    """语法解析器接口"""
    
    @abstractmethod
    def parse(self, source: str, filename: Optional[str] = None) -> Any:
        """
        将源码解析为 AST
        
        Args:
            source: 源代码字符串
            filename: 文件名（用于错误报告）
        
        Returns:
            AST 根节点
        """
        pass
    
    @abstractmethod
    def parse_tokens(self, tokens: List[Any]) -> Any:
        """
        将 Token 流解析为 AST
        
        Args:
            tokens: Token 列表
        
        Returns:
            AST 根节点
        """
        pass


class ISemanticAnalyzer(ABC):
    """语义分析器接口"""
    
    @abstractmethod
    def analyze(self, ast: Any) -> bool:
        """
        分析 AST 的语义
        
        Args:
            ast: AST 根节点
        
        Returns:
            分析是否成功
        """
        pass
    
    @abstractmethod
    def get_symbol_table(self) -> Any:
        """获取符号表"""
        pass


class ICodeGenerator(ABC):
    """代码生成器接口"""
    
    @abstractmethod
    def generate(self, ast: Any) -> str:
        """
        将 AST 转换为目标代码
        
        Args:
            ast: AST 根节点
        
        Returns:
            生成的代码字符串
        """
        pass


class ICompiler(ABC):
    """编译器接口"""
    
    @abstractmethod
    def compile(self, source: str, filename: Optional[str] = None) -> str:
        """
        完整编译流程
        
        Args:
            source: 源代码字符串
            filename: 文件名（用于错误报告）
        
        Returns:
            生成的目标代码
        """
        pass
    
    @abstractmethod
    def compile_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        编译文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（可选）
        
        Returns:
            生成的目标代码
        """
        pass
