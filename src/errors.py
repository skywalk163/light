# -*- coding: utf-8 -*-
"""
光明编译器 - 美化的错误和 traceback 处理

提供中文错误信息、源代码上下文显示、栈追踪美化等功能。
"""

import sys
import traceback
import os
from typing import List, Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass, field


def format_exception(exc_type, exc_value, exc_tb, source_lines=None):
    """格式化异常为美化的中文输出"""
    if source_lines is None:
        source_lines = []
    
    # 词法/语法错误
    if hasattr(exc_value, 'source_lines'):
        return str(exc_value)
    
    # 普通异常
    lines = []
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║                      光明运行错误                         ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")
    
    # 异常类型
    exc_name = exc_type.__name__
    chinese_names = {
        'SyntaxError': '语法错误',
        'NameError': '名称错误',
        'TypeError': '类型错误',
        'ValueError': '值错误',
        'IndexError': '索引错误',
        'KeyError': '键错误',
        'AttributeError': '属性错误',
        'ZeroDivisionError': '除零错误',
        'OverflowError': '溢出错误',
        'RecursionError': '递归错误',
        'ImportError': '导入错误',
        'ModuleNotFoundError': '模块未找到',
        'FileNotFoundError': '文件未找到',
        'PermissionError': '权限错误',
        'RuntimeError': '运行时错误',
        'StopIteration': '迭代停止',
        'AssertionError': '断言错误',
        'IndentationError': '缩进错误',
        'TabError': '制表符错误',
        'UnicodeError': 'Unicode 错误',
        'EOFError': '输入结束错误',
        'KeyboardInterrupt': '用户中断',
        'SystemExit': '系统退出',
    }
    chinese_name = chinese_names.get(exc_name, exc_name)
    lines.append(f"║  错误类型: {chinese_name:<45}║")
    
    # 错误信息
    error_msg = str(exc_value)
    if len(error_msg) > 45:
        error_msg = error_msg[:42] + "..."
    lines.append(f"║  错误信息: {error_msg:<45}║")
    
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")
    
    # 栈追踪
    tb_list = traceback.format_tb(exc_tb)
    if len(tb_list) > 1:
        lines.append("调用栈:")
        lines.append("─" * 60)
        
        for i, tb_entry in enumerate(tb_list):
            # 解析栈追踪条目
            for line in tb_entry.strip().split('\n'):
                if 'File' in line:
                    # 解析文件路径
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        file_part = parts[0].replace('File ', '').strip('"')
                        location_part = parts[1].strip() if len(parts) > 1 else ''
                        # 只显示项目内的文件
                        if 'light' in file_part.lower() or 'src' in file_part.lower():
                            lines.append(f"  → {file_part} {location_part}")
            if i > 0:  # 跳过第一个（用户代码）
                break
    
    lines.append("")
    return '\n'.join(lines)


def install_excepthook():
    """安装自定义的异常处理器"""
    old_excepthook = sys.excepthook
    
    def custom_excepthook(exc_type, exc_value, exc_tb):
        # 如果是光明相关的错误，使用美化格式
        if 'light' in str(exc_type).lower() or hasattr(exc_value, 'source_lines'):
            print(format_exception(exc_type, exc_value, exc_tb), file=sys.stderr)
        else:
            # 其他错误使用原始格式
            old_excepthook(exc_type, exc_value, exc_tb)
    
    sys.excepthook = custom_excepthook


def format_source_context(source, line, col=None, context_lines=3):
    """格式化源代码上下文（增强版：显示行号、列号箭头、上下文行）"""
    if not source:
        return ""
    
    lines = source.split('\n')
    if line < 1 or line > len(lines):
        return ""
    
    result = []
    result.append("📄 源代码上下文:")
    result.append("─" * 60)
    
    start = max(0, line - context_lines - 1)
    end = min(len(lines), line + context_lines)
    
    # 计算行号宽度
    line_width = len(str(len(lines)))
    
    for i in range(start, end):
        line_num = i + 1
        line_content = lines[i].rstrip()
        
        if line_num == line:
            # 错误行：使用箭头标记
            result.append(f"  → {line_num:>{line_width}} │ {line_content}")
            if col is not None and col > 0:
                # 计算箭头位置（考虑行号宽度和前缀）
                arrow_indent = 6 + line_width + min(col, len(line_content))
                if col <= len(line_content):
                    result.append(f"    {' ' * (line_width)} │ {' ' * (min(col, len(line_content)) - 1)}^── 此处")
                else:
                    result.append(f"    {' ' * (line_width)} │ {' ' * (len(line_content))}  ^── 此处")
            else:
                result.append(f"    {' ' * (line_width)} │{' ' * len(line_content)}  ◀━━ 错误位置")
        else:
            result.append(f"    {line_num:>{line_width}} │ {line_content}")
    
    result.append("─" * 60)
    return '\n'.join(result)


def format_error_with_context(error: Exception, source: str = None, 
                               line: int = 0, col: int = 0) -> str:
    """整合错误信息、源代码位置、修复建议的完整格式
    
    Args:
        error: 异常对象
        source: 源代码文本
        line: 错误行号
        col: 错误列号
        
    Returns:
        格式化的完整错误信息
    """
    parts = []
    parts.append("")
    parts.append("┌─────────────────────────────────────────────────────────┐")
    
    # 错误类型和消息
    if isinstance(error, LightError):
        parts.append(f"│  {error.__class__.__name__}")
        parts.append(f"│  {error.message}")
        if error.hint:
            parts.append(f"│  提示: {error.hint}")
        # 修复建议
        if error.fix_suggestions:
            parts.append("│")
            parts.append("│  💡 修复建议:")
            for i, suggestion in enumerate(error.fix_suggestions, 1):
                parts.append(f"│    {i}. {suggestion}")
    else:
        parts.append(f"│  {type(error).__name__}: {error}")
    
    parts.append("└─────────────────────────────────────────────────────────┘")
    
    # 源代码上下文
    if source and line > 0:
        context = format_source_context(source, line, col)
        if context:
            parts.append("")
            parts.append(context)
    
    # 格式化后的完整字符串
    return '\n'.join(parts)


class LightError(Exception):
    """光明基础错误类"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None, source_lines: List[str] = None):
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.fix_suggestions = fix_suggestions or []
        self.source_lines = source_lines or []
        
        parts = []
        parts.append("\n┌─ 光明错误")
        
        if line:
            pos_info = f"行 {line}"
            if col:
                pos_info += f", 列 {col}"
            parts.append(f"│ 位置: {pos_info}")
        
        parts.append(f"│ 原因: {message}")
        
        if hint:
            parts.append(f"│ 提示: {hint}")
        
        if self.fix_suggestions:
            parts.append("│")
            parts.append("│ 💡 修复建议:")
            for i, s in enumerate(self.fix_suggestions, 1):
                parts.append(f"│   {i}. {s}")
        
        parts.append("└─")
        super().__init__('\n'.join(parts))


class LexerError(LightError):
    """词法分析错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None):
        # 自动匹配常见词法错误的修复建议
        if fix_suggestions is None:
            fix_suggestions = LightErrorFormatter.get_fix_suggestions('LexerError', message)
        message = f"词法分析错误: {message}"
        super().__init__(message, line, col, hint, fix_suggestions)


class SemanticError(LightError):
    """语义分析错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None):
        # 自动匹配常见语义错误的修复建议
        if fix_suggestions is None:
            fix_suggestions = LightErrorFormatter.get_fix_suggestions('SemanticError', message)
        message = f"语义错误: {message}"
        super().__init__(message, line, col, hint, fix_suggestions)


class ParseError(LightError):
    """语法解析错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None):
        if fix_suggestions is None:
            fix_suggestions = LightErrorFormatter.get_fix_suggestions('ParseError', message)
        message = f"语法错误: {message}"
        super().__init__(message, line, col, hint, fix_suggestions)


class LightErrorFormatter:
    """统一错误格式化器"""
    
    # 常见错误的自动修复建议字典
    FIX_SUGGESTIONS = {
        'LexerError': {
            '未闭合的字符串': [
                '在字符串末尾添加闭合引号: "..."',
                '检查字符串内是否有转义字符',
                '确保字符串使用相同的引号开头和结尾',
            ],
            '字符串未闭合': [
                '在字符串末尾添加闭合引号: "..."',
                '检查字符串内是否有转义字符',
                '确保字符串使用相同的引号开头和结尾',
            ],
            '未知字符': [
                '检查输入中是否有非法字符',
                '使用允许的字符集重新输入',
                '光明支持中文字符、英文字母、数字和基本标点符号',
            ],
            '书名号': [
                '确保书名号《》成对出现',
                '检查段落名是否以《》包裹',
                '示例: 段落《我的段落》',
            ],
            'f-string': [
                '检查f-string的引号是否闭合',
                '确保f-string中的表达式语法正确',
                'f-string示例: f"值为{变量}"',
            ],
            '中文数字': [
                '检查中文数字格式是否正确',
                '支持的中文数字: 零一二三四五六七八九十百千万亿',
            ],
        },
        'SemanticError': {
            '未定义的变量': [
                '检查变量名拼写是否正确',
                '在使用变量前先声明: 设 变量名 为 值',
                '检查变量是否在正确的作用域内',
            ],
            '未定义的名称': [
                '检查名称拼写是否正确',
                '确认该名称已被定义或导入',
                '检查是否遗漏了"导入"语句',
            ],
            '类型不匹配': [
                '检查操作数的类型是否正确',
                '确保函数参数类型与声明一致',
                '使用类型转换函数（如 转整数、转字符串）',
            ],
            '重复定义': [
                '移除重复的变量或函数定义',
                '使用不同的名称避免冲突',
                '检查是否意外导入了同名的模块',
            ],
            '参数数量': [
                '检查函数调用时参数数量是否匹配',
                '查看函数定义需要的参数个数',
                '确保参数之间用逗号分隔',
            ],
            '作用域': [
                '检查变量是否在正确的作用域内',
                '在函数内部定义的变量不能在外部访问',
                '如需访问外部变量，请使用参数传递',
            ],
        },
        'ParseError': {
            '语法': [
                '检查代码语法是否正确',
                '确保所有括号、引号都已闭合',
                '检查中英文标点符号是否混用',
            ],
            '冒号': [
                '确保块语句后有冒号（如：如果...：）',
                '中英文冒号均可使用',
                '示例: 如果 条件:',
            ],
            '缩进': [
                '检查缩进是否正确（建议使用4个空格）',
                '不要混用Tab和空格',
                '同一代码块内的语句缩进必须一致',
            ],
            '括号': [
                '检查括号是否匹配',
                '确保左括号(和右括号)数量一致',
                '使用嵌套括号时注意层级关系',
            ],
            '引号': [
                '检查引号是否闭合',
                '字符串必须使用引号包裹',
                '示例: "这是一个字符串"',
            ],
        },
    }
    
    @staticmethod
    def get_fix_suggestions(error_type: str, message: str) -> List[str]:
        """根据错误类型和消息自动匹配修复建议
        
        Args:
            error_type: 错误类型名称（如 'LexerError', 'SemanticError'）
            message: 错误消息文本
            
        Returns:
            匹配的修复建议列表，未匹配时返回空列表
        """
        suggestions_map = LightErrorFormatter.FIX_SUGGESTIONS.get(error_type, {})
        matched = []
        for keyword, suggestions in suggestions_map.items():
            if keyword in message:
                matched.extend(suggestions)
        return matched
    
    @staticmethod
    def format(error: Exception, source: str = None) -> str:
        """统一格式化错误
        
        Args:
            error: 异常对象
            source: 可选的源代码
            
        Returns:
            格式化的错误信息
        """
        if isinstance(error, LightError):
            return format_error_with_context(error, source, error.line, error.col)
        else:
            # 普通异常
            parts = []
            parts.append(f"\n┌─ 错误: {type(error).__name__}")
            parts.append(f"│ {error}")
            
            # 尝试获取修复建议
            suggestions = LightErrorFormatter.get_fix_suggestions(
                type(error).__name__, str(error))
            if suggestions:
                parts.append("│")
                parts.append("│ 💡 修复建议:")
                for i, s in enumerate(suggestions, 1):
                    parts.append(f"│   {i}. {s}")
            
            parts.append("└─")
            return '\n'.join(parts)
    
    @staticmethod
    def format_with_source(error: Exception, source: str, line: int, col: int) -> str:
        """带源代码标注的格式化
        
        Args:
            error: 异常对象
            source: 源代码文本
            line: 错误行号
            col: 错误列号
            
        Returns:
            带源代码标注的完整错误信息
        """
        return format_error_with_context(error, source, line, col)


class CodeGenError(LightError):
    """代码生成错误"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None):
        if fix_suggestions is None:
            fix_suggestions = LightErrorFormatter.get_fix_suggestions('CodeGenError', message)
        message = f"代码生成错误: {message}"
        super().__init__(message, line, col, hint, fix_suggestions)


class TypeError_ (LightError):
    """类型错误（避开内置 TypeError 名称）"""
    def __init__(self, message: str, line: int = 0, col: int = 0, hint: str = None,
                 fix_suggestions: List[str] = None, expected_type: str = None,
                 actual_type: str = None):
        if fix_suggestions is None:
            fix_suggestions = LightErrorFormatter.get_fix_suggestions('TypeError', message)
        self.expected_type = expected_type
        self.actual_type = actual_type
        msg = f"类型错误: {message}"
        if expected_type and actual_type:
            msg += f" (期望 {expected_type}, 实际 {actual_type})"
        super().__init__(msg, line, col, hint, fix_suggestions)


class NameError_(LightError):
    """名称错误（避开内置 NameError 名称）"""
    def __init__(self, name: str, line: int = 0, col: int = 0, filename: str = None):
        super().__init__(f"未定义的名称: {name}", line, col)


# 扩展修复建议字典
LightErrorFormatter.FIX_SUGGESTIONS['CodeGenError'] = {
    '未知语句': [
        '检查代码中是否有不受支持的语法结构',
        '确保所有语句类型已被编译器支持',
    ],
    '不支持的表达式': [
        '检查表达式中使用了哪些操作符',
        '某些高级表达式可能需要更新编译器版本',
    ],
}
LightErrorFormatter.FIX_SUGGESTIONS['TypeError'] = {
    '类型不匹配': [
        '检查操作数的类型是否正确',
        '确保函数参数类型与声明一致',
        '使用类型转换函数（如 转整数、转字符串）',
    ],
    '无法将': [
        '检查赋值或传参的类型是否兼容',
        '使用类型转换函数进行显式转换',
        '检查变量声明时的类型注解',
    ],
    '期望': [
        '检查函数调用时参数类型是否正确',
        '查看函数定义需要的参数类型',
        '确保传参顺序与定义一致',
    ],
}


# =============================================================================
# 统一错误收集器
# =============================================================================

@dataclass
class ErrorEntry:
    """单个错误条目（携带位置信息和源代码上下文）"""
    stage: str                      # 错误阶段: 词法/语法/类型/代码生成
    message: str                    # 错误消息
    line: int = 0                   # 错误行号
    column: int = 0                 # 错误列号
    source_line: str = ''           # 错误行的源代码
    fix_suggestions: List[str] = field(default_factory=list)  # 修复建议
    exception: Optional[Exception] = None  # 原始异常（可选）
    
    def format(self, source: str = '') -> str:
        """格式化单个错误条目为统一格式"""
        parts = []
        parts.append("")
        parts.append("┌─ 错误")
        if self.stage:
            parts.append(f"│ 阶段: {self.stage}")
        if self.line:
            pos = f"行 {self.line}"
            if self.column:
                pos += f", 列 {self.column}"
            parts.append(f"│ 位置: {pos}")
        parts.append(f"│ 原因: {self.message}")
        if self.fix_suggestions:
            parts.append("│")
            parts.append("│ 💡 修复建议:")
            for i, s in enumerate(self.fix_suggestions, 1):
                parts.append(f"│   {i}. {s}")
        if self.source_line:
            parts.append("│")
            parts.append(f"│ 代码: {self.source_line.strip()}")
        parts.append("└─")
        
        # 源代码上下文（如果提供了源代码）
        if source and self.line > 0:
            ctx = format_source_context(source, self.line, self.column)
            if ctx:
                return '\n'.join(parts) + '\n' + ctx
        return '\n'.join(parts)


class CompilerErrorCollector:
    """统一错误收集器：收集并格式化编译各阶段的错误
    
    使用示例：
        collector = CompilerErrorCollector(source)
        collector.add_lexer_error("未闭合的字符串", 3, 10)
        collector.add_parser_error("期望 '为'", 5, 1, "设 甲 10")
        collector.add_type_error("类型不匹配: 期望整数, 实际字符串", 8, 15)
        collector.add_codegen_error("不支持的表达式", 12, 5)
        collector.add_error(ErrorEntry(stage="语法", message="...", line=3))
        print(collector.format_all())  # 显示所有错误
        print(collector.format_summary())  # 显示错误摘要
    """
    
    def __init__(self, source: str = ''):
        self.source = source
        self.errors: List[ErrorEntry] = []
        self.warnings: List[ErrorEntry] = []
    
    def add_error(self, entry: ErrorEntry):
        """添加一个错误条目"""
        self.errors.append(entry)
    
    def add_warning(self, entry: ErrorEntry):
        """添加一个警告条目"""
        self.warnings.append(entry)
    
    def add_lexer_error(self, message: str, line: int = 0, column: int = 0,
                        source_line: str = '', exception: Exception = None):
        """添加词法分析错误"""
        suggestions = LightErrorFormatter.get_fix_suggestions('LexerError', message)
        self.errors.append(ErrorEntry(
            stage='词法分析', message=message, line=line, column=column,
            source_line=source_line, fix_suggestions=suggestions, exception=exception,
        ))
    
    def add_parser_error(self, message: str, line: int = 0, column: int = 0,
                         source_line: str = '', exception: Exception = None):
        """添加语法解析错误"""
        suggestions = LightErrorFormatter.get_fix_suggestions('ParseError', message)
        self.errors.append(ErrorEntry(
            stage='语法解析', message=message, line=line, column=column,
            source_line=source_line, fix_suggestions=suggestions, exception=exception,
        ))
    
    def add_type_error(self, message: str, line: int = 0, column: int = 0,
                       source_line: str = '', exception: Exception = None):
        """添加类型检查错误"""
        suggestions = LightErrorFormatter.get_fix_suggestions('TypeError', message)
        self.errors.append(ErrorEntry(
            stage='类型检查', message=message, line=line, column=column,
            source_line=source_line, fix_suggestions=suggestions, exception=exception,
        ))
    
    def add_codegen_error(self, message: str, line: int = 0, column: int = 0,
                          source_line: str = '', exception: Exception = None):
        """添加代码生成错误"""
        suggestions = LightErrorFormatter.get_fix_suggestions('CodeGenError', message)
        self.errors.append(ErrorEntry(
            stage='代码生成', message=message, line=line, column=column,
            source_line=source_line, fix_suggestions=suggestions, exception=exception,
        ))
    
    def add_semantic_error(self, message: str, line: int = 0, column: int = 0,
                           source_line: str = '', exception: Exception = None):
        """添加语义分析错误"""
        suggestions = LightErrorFormatter.get_fix_suggestions('SemanticError', message)
        self.errors.append(ErrorEntry(
            stage='语义分析', message=message, line=line, column=column,
            source_line=source_line, fix_suggestions=suggestions, exception=exception,
        ))
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def error_count(self) -> int:
        return len(self.errors)
    
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def format_all(self, separate: bool = True) -> str:
        """格式化所有错误和警告
        
        Args:
            separate: 是否用分隔线分隔每个错误
        
        Returns:
            格式化的错误信息字符串
        """
        parts = []
        
        if not self.errors and not self.warnings:
            return ""
        
        # 错误
        if self.errors:
            parts.append(f"\n{'='*60}")
            parts.append(f"❌ 发现 {len(self.errors)} 个错误:")
            parts.append(f"{'='*60}")
            for i, err in enumerate(self.errors):
                formatted = err.format(self.source)
                parts.append(formatted)
                if separate and i < len(self.errors) - 1:
                    parts.append("─" * 40)
        
        # 警告
        if self.warnings:
            parts.append(f"\n{'='*60}")
            parts.append(f"⚠️  发现 {len(self.warnings)} 个警告:")
            parts.append(f"{'='*60}")
            for i, warn in enumerate(self.warnings):
                formatted = warn.format(self.source)
                parts.append(formatted)
                if separate and i < len(self.warnings) - 1:
                    parts.append("─" * 40)
        
        return '\n'.join(parts)
    
    def format_summary(self) -> str:
        """格式化错误摘要（仅统计信息，不含详细内容）"""
        if not self.has_errors() and not self.warnings:
            return "✅ 编译通过，无错误"
        
        parts = []
        parts.append("📊 编译结果摘要:")
        parts.append(f"  错误: {self.error_count()} 个")
        parts.append(f"  警告: {self.warning_count()} 个")
        
        if self.errors:
            # 按阶段统计
            from collections import Counter
            stages = Counter(e.stage for e in self.errors)
            for stage, count in stages.most_common():
                parts.append(f"    {stage}: {count} 个错误")
        
        return '\n'.join(parts)
    
    def get_errors_by_stage(self, stage: str) -> List[ErrorEntry]:
        """按阶段获取错误"""
        return [e for e in self.errors if e.stage == stage]
    
    def clear(self):
        """清空所有错误和警告"""
        self.errors.clear()
        self.warnings.clear()


# 增强 format_source_context：支持更丰富的视觉标记
def format_source_context_rich(source: str, line: int, col: int = None,
                                context_lines: int = 3, show_line_numbers: bool = True) -> str:
    """增强版源代码上下文格式化（更丰富的视觉标记）
    
    Args:
        source: 源代码文本
        line: 错误行号（1-based）
        col: 错误列号（1-based，可选）
        context_lines: 上下文行数
        show_line_numbers: 是否显示行号
    
    Returns:
        格式化的源代码上下文
    """
    if not source:
        return ""
    
    lines = source.split('\n')
    if line < 1 or line > len(lines):
        return ""
    
    result = []
    result.append("📄 源代码上下文:")
    result.append("─" * 60)
    
    start = max(0, line - context_lines - 1)
    end = min(len(lines), line + context_lines)
    
    # 计算行号宽度
    line_width = len(str(len(lines))) if show_line_numbers else 0
    
    for i in range(start, end):
        line_num = i + 1
        line_content = lines[i].rstrip()
        
        if line_num == line:
            # 错误行：使用醒目的箭头标记
            prefix = "  → " if show_line_numbers else "→ "
            line_str = f"{prefix}{line_num:>{line_width}} │ {line_content}" if show_line_numbers else f"{prefix}{line_content}"
            result.append(line_str)
            if col is not None and col > 0 and col <= len(line_content) + 1:
                # 显示精确的列号指示（^ 符号）
                arrow_indent = len(prefix) + (line_width + 3 if show_line_numbers else 0) + min(col - 1, len(line_content))
                result.append(f"{' ' * arrow_indent}▲ 此处")
            else:
                arrow_indent = len(prefix) + (line_width + 3 if show_line_numbers else 0) + len(line_content)
                result.append(f"{' ' * arrow_indent}◀ 此附近")
        else:
            prefix = "    " if show_line_numbers else "  "
            line_str = f"{prefix}{line_num:>{line_width}} │ {line_content}" if show_line_numbers else f"{prefix}{line_content}"
            result.append(line_str)
    
    result.append("─" * 60)
    return '\n'.join(result)


# 安装默认的异常处理器
install_excepthook()