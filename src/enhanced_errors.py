# -*- coding: utf-8 -*-
"""
光明（Light）增强错误提示模块

功能：
  - 类似 Rust 编译器的错误渲染
  - 箭头指向错误位置
  - 代码片段高亮
  - 修复建议

用法：
  from error_formatter import format_error
  print(format_error(error_info))
"""

import os
import sys


class ErrorFormatter:
    """错误格式化器"""

    def __init__(self):
        self.use_colors = sys.stdout.isatty()

    def format_error(self, source: str, error: Exception, line_num: int = None, col: int = None) -> str:
        """格式化错误信息

        Args:
            source: 源代码
            error: 异常对象
            line_num: 错误行号（可选）
            col: 错误列号（可选）

        Returns:
            格式化后的错误信息
        """
        import traceback

        lines = source.split('\n')
        err_type = type(error).__name__
        err_msg = str(error)

        # 尝试从异常中提取行号
        if line_num is None:
            line_num = self._extract_line_num(error)

        # 从 traceback 中提取行号
        if line_num is None:
            for frame in traceback.extract_tb(error.__traceback__):
                line_num = frame.lineno
                break

        # 构建错误信息
        parts = []

        # 错误标题
        parts.append(self._color('error', '错误'))
        parts.append(f': {err_type}')
        parts.append(self._color('reset', ''))
        parts.append(f'\n  {err_msg}')

        # 如果有源代码，显示代码片段
        if source and lines:
            if line_num is not None and line_num > 0 and line_num <= len(lines):
                parts.append('\n')
                parts.append(self._show_code_snippet(lines, line_num, col))
            else:
                # 显示前几行作为上下文
                parts.append('\n')
                parts.append(self._color('code', '源代码:'))
                parts.append('\n')
                for i, line in enumerate(lines[:5]):
                    parts.append(f' {i+1} {line}\n')

        # 修复建议
        suggestion = self._get_suggestion(err_type, err_msg)
        if suggestion:
            parts.append(f'\n  {self._color("suggestion", "建议:")} {suggestion}')

        parts.append('\n')
        return ''.join(parts)

    def _color(self, color: str, text: str) -> str:
        """添加颜色"""
        if not self.use_colors:
            return text

        colors = {
            'error': '\033[91m',
            'warning': '\033[93m',
            'info': '\033[94m',
            'suggestion': '\033[92m',
            'code': '\033[96m',
            'reset': '\033[0m',
        }
        if color in colors:
            return colors[color] + text + colors['reset']
        return text

    def _extract_line_num(self, error: Exception) -> int:
        """从异常中提取行号"""
        msg = str(error)
        # 尝试匹配常见的行号格式
        import re
        match = re.search(r'行\s*(\d+)', msg)
        if match:
            return int(match.group(1))
        match = re.search(r'line\s*(\d+)', msg, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _show_code_snippet(self, lines: list, line_num: int, col: int = None) -> str:
        """显示代码片段"""
        snippet = []
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 2)

        # 计算行号宽度
        line_width = len(str(len(lines)))

        for i in range(start, end):
            line_idx = i + 1
            line = lines[i]
            padding = ' ' * (line_width - len(str(line_idx)))

            if line_idx == line_num:
                # 当前错误行
                snippet.append(f' {padding}{line_idx} {self._color("code", line)}')

                # 箭头指向错误位置
                if col is not None and col > 0 and col <= len(line):
                    arrow_padding = ' ' * (line_width + 1 + col - 1)
                    snippet.append(f' {padding}│')
                    snippet.append(f' {padding}│{arrow_padding}^')
                    snippet.append(f' {padding}│')
                else:
                    # 如果没有列号，在行尾显示箭头
                    arrow_padding = ' ' * (line_width + 1 + len(line))
                    snippet.append(f' {padding}│')
                    snippet.append(f' {padding}│{" " * len(line)}^')
                    snippet.append(f' {padding}│')
            else:
                # 上下文行
                snippet.append(f' {padding}{line_idx} {line}')

        return '\n'.join(snippet)

    def _get_suggestion(self, err_type: str, err_msg: str) -> str:
        """获取修复建议"""
        suggestions = {
            # 语法错误
            'SyntaxError': {
                '冒号': '确保块语句后有冒号（如：如果...：）',
                '缩进': '检查缩进是否正确',
                '括号': '检查括号是否匹配',
                '引号': '检查引号是否闭合',
            },
            # 名称错误
            'NameError': {
                '未定义': '确保变量已声明',
                '未找到': '检查拼写是否正确',
            },
            # 类型错误
            'TypeError': {
                '参数': '检查函数参数类型是否正确',
                '操作数': '检查操作数类型是否匹配',
            },
            # 索引错误
            'IndexError': {
                '越界': '确保索引在有效范围内',
            },
            # 属性错误
            'AttributeError': {
                '属性': '检查对象是否有该属性',
            },
        }

        # 按错误类型查找
        if err_type in suggestions:
            for keyword, suggestion in suggestions[err_type].items():
                if keyword in err_msg:
                    return suggestion

        # 通用建议
        if '光明' in err_msg or 'light' in err_msg.lower():
            return '检查光明语法是否正确，参考语法文档'

        return None


def format_error(source: str, error: Exception, line_num: int = None, col: int = None) -> str:
    """格式化错误信息（便捷函数）"""
    formatter = ErrorFormatter()
    return formatter.format_error(source, error, line_num, col)


def install_error_handler():
    """安装全局错误处理器"""
    def _error_handler(exc_type, exc_value, exc_tb):
        import traceback
        formatter = ErrorFormatter()

        # 获取源代码信息
        source = ''
        line_num = None

        # 尝试从 traceback 获取文件和行号
        for frame in traceback.extract_tb(exc_tb):
            if frame.filename.endswith('.light'):
                try:
                    with open(frame.filename, 'r', encoding='utf-8') as f:
                        source = f.read()
                    line_num = frame.lineno
                except Exception:
                    pass
                break

        # 打印格式化的错误
        print(formatter.format_error(source, exc_value, line_num), file=sys.stderr)

    sys.excepthook = _error_handler