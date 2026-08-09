"""
光明（Light）编程语言 - 统一错误处理器

提供：
1. 语法错误监听器（ANTLR 到中文翻译）
2. 运行时错误类（带行号、列号）
3. 错误上下文显示（源码片段 + 指示箭头）
4. 修复建议生成

与 light_visitor.py 中的 LightLangErrorListener 共享同一基础逻辑。
"""

import sys
import os
from typing import List, Optional, Tuple


# =============================================================================
# 运行时错误类型
# =============================================================================

class LightError(Exception):
    """光明错误基类"""

    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None,
                 source: Optional[str] = None):
        self.message = message
        self.line = line
        self.column = column
        self.source = source
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """格式化错误消息"""
        if self.line is not None and self.column is not None:
            return f"{self.message}（第{self.line}行，第{self.column}列）"
        return self.message


class LexerError(LightError):
    """词法错误"""
    pass


class ParserError(LightError):
    """语法错误"""
    pass


class SemanticError(LightError):
    """语义错误"""
    pass


class CodeGenError(LightError):
    """代码生成错误"""
    pass


class RuntimeError(LightError):
    """运行时错误"""
    pass


# =============================================================================
# 错误上下文显示
# =============================================================================

def format_error_context(source: str, line: int, column: int, context_lines: int = 2) -> str:
    """
    格式化错误上下文（源码片段 + 指示箭头）

    Args:
        source: 源代码
        line: 错误行号（从1开始）
        column: 错误列号（从0开始）
        context_lines: 显示的上下文行数

    Returns:
        格式化的错误上下文字符串
    """
    if not source:
        return ""

    lines = source.split('\n')
    start = max(0, line - context_lines - 1)
    end = min(len(lines), line + context_lines)

    result = []
    for i in range(start, end):
        line_num = i + 1
        prefix = "→ " if line_num == line else "  "
        result.append(f"{prefix}{line_num:4d} | {lines[i]}")

        if line_num == line:
            # 添加错误指示箭头
            pointer = " " * (len(prefix) + 7 + column) + "^——" + "此处出错"
            result.append(pointer)

    return '\n'.join(result)


# =============================================================================
# 错误格式化与修复建议
# =============================================================================

def suggest_fix(error_type: str, symbol: str, context: str = "") -> Optional[str]:
    """
    根据错误类型提供修复建议

    Args:
        error_type: 错误类型
        symbol: 错误符号
        context: 上下文

    Returns:
        修复建议字符串
    """
    suggestions = {
        'missing_LPAREN': f"函数调用需要括号，尝试改为 {symbol}()",
        'missing_RPAREN': f"缺少右括号，检查括号是否配对",
        'missing_COLON': f"代码块开始需要冒号「：」",
        'missing_PERIOD': f"语句结束需要句号「。」",
        'missing_K_END': f"代码块缺少「结束」标记",
        'mismatched_ID': f"期望标识符，'{symbol}' 可能是关键字",
        'unexpected_symbol': f"符号 '{symbol}' 在此处不合法",
        'no_viable': f"请检查此行的语法结构",
        'extra_END': f"「结束」标记过多，或层级缩进有误",
    }

    key = f"{error_type}_{symbol}" if symbol else error_type
    return suggestions.get(key) or suggestions.get(error_type)


def show_error(title: str, message: str, source: Optional[str] = None,
               line: Optional[int] = None, column: Optional[int] = None,
               suggestion: Optional[str] = None) -> str:
    """
    生成格式化的错误显示字符串

    Args:
        title: 错误类型标题（如"语法错误"、"运行时错误"）
        message: 错误描述
        source: 源代码（用于显示上下文）
        line: 错误行号
        column: 错误列号
        suggestion: 修复建议

    Returns:
        格式化的错误字符串
    """
    parts = []
    parts.append(f"⚠ {title}")

    if line is not None and column is not None:
        parts.append(f"  位置: 第{line}行，第{column}列")

    parts.append(f"  信息: {message}")

    if source and line is not None:
        context = format_error_context(source, line, column or 0)
        if context:
            parts.append(f"\n{context}")

    if suggestion:
        parts.append(f"  建议: {suggestion}")

    return '\n'.join(parts)


# =============================================================================
# CLI 错误显示
# =============================================================================

def print_error(title: str, message: str, source: Optional[str] = None,
                line: Optional[int] = None, column: Optional[int] = None,
                suggestion: Optional[str] = None):
    """在终端输出格式化的错误信息（带颜色）"""
    try:
        from cli import red, yellow, dim
    except ImportError:
        # 备用：无颜色输出
        def red(t): return t
        def yellow(t): return t
        def dim(t): return t

    print(red(f"⚠ {title}"), file=sys.stderr)
    if line is not None:
        loc = f"  位置: 第{line}行"
        loc += f"，第{column}列" if column is not None else ""
        print(dim(loc), file=sys.stderr)
    print(f"  信息: {yellow(message)}", file=sys.stderr)

    if source and line is not None:
        context = format_error_context(source, line, column or 0)
        if context:
            print(f"\n{dim(context)}", file=sys.stderr)

    if suggestion:
        print(f"  建议: {suggestion}", file=sys.stderr)


# =============================================================================
# 便捷包装：解析错误显示
# =============================================================================

def display_parse_errors(errors: List[str], source: str, filepath: str = ""):
    """格式化显示解析错误列表"""
    header = f" 文件: {filepath}" if filepath else ""
    print(f"\n{header}", file=sys.stderr) if header else None
    for err in errors:
        print(f"  · {err}", file=sys.stderr)