# -*- coding: utf-8 -*-
"""
光明（Light）增强错误提示模块

功能：
  - 类似 Rust 编译器的错误渲染
  - 箭头指向错误位置
  - 代码片段高亮
  - 修复建议
  - 示例代码
"""

import os
import sys


# =============================================================================
# 模块级错误名称映射表
# =============================================================================

_CHINESE_NAMES = {
    # Python 标准异常
    'SyntaxError': '语法解析错误',
    'TypeError': '类型错误',
    'ValueError': '值错误',
    'NameError': '名称错误',
    'IndexError': '索引错误',
    'KeyError': '键错误',
    'AttributeError': '属性错误',
    'ImportError': '导入错误',
    'RuntimeError': '运行时错误',
    'ZeroDivisionError': '除零错误',
    'FileNotFoundError': '文件未找到',
    'IOError': '输入输出错误',
    'MemoryError': '内存错误',
    'RecursionError': '递归错误',
    'StopIteration': '迭代停止',
    'AssertionError': '断言错误',
    'NotImplementedError': '未实现错误',
    'OverflowError': '溢出错误',
    'ArithmeticError': '算术错误',
    'LookupError': '查找错误',
    'IndentationError': '缩进错误',
    'TabError': '制表符错误',
    'UnicodeError': 'Unicode 错误',
    'UnicodeDecodeError': 'Unicode 解码错误',
    'UnicodeEncodeError': 'Unicode 编码错误',
    'EOFError': '输入结束错误',
    'KeyboardInterrupt': '用户中断',
    'SystemExit': '系统退出',
    'OSError': '系统错误',
    'ModuleNotFoundError': '模块未找到',
    'PermissionError': '权限不足',
    'ConnectionError': '连接错误',
    'TimeoutError': '超时错误',
    'FloatingPointError': '浮点运算错误',
    'ReferenceError': '引用错误',
    'SystemError': '系统内部错误',
    'GeneratorExit': '生成器退出',
    'IsADirectoryError': '是目录错误',
    'NotADirectoryError': '不是目录错误',
    'InterruptedError': '中断错误',
    'BrokenPipeError': '管道破裂错误',
    'BlockingIOError': '阻塞 IO 错误',
    'ChildProcessError': '子进程错误',
    'ProcessLookupError': '进程查找错误',
    # 段言自定义错误
    'LexerError': '词法分析错误',
    'ParserError': '语法解析错误',
    'SemanticError': '语义分析错误',
    'CodeGenError': '代码生成错误',
    'CompileError': '编译错误',
    'DuanError': '段言错误',
    'ModuleError': '模块错误',
    'CircularDependencyError': '循环依赖错误',
    'ParseError': '解析错误',
    'UnificationError': '类型统一错误',
    'TypeErrorInference': '类型推断错误',
}

_CHINESE_HINTS = {
    'SyntaxError': '请检查代码语法是否正确，确保所有括号、引号、冒号、句号等符号已正确配对。段言语句需要以句号「。」结尾，代码块以冒号「：」开始。',
    'TypeError': '请检查操作数类型是否匹配，段言中文本和数字不能直接进行运算。可使用「整数()」「文本()」等函数进行类型转换。',
    'ValueError': '请检查传入的值是否在有效范围内，可能需要先进行类型转换或做边界检查。',
    'NameError': '请检查变量名是否拼写正确，使用前需先通过「设」关键字定义变量。段言中变量必须先定义后使用。',
    'IndexError': '请检查索引是否在有效范围内，段言列表索引从 0 开始，长度为 N 的列表最大索引为 N-1。可使用「长度()」获取列表长度。',
    'KeyError': '请检查字典键是否存在，可以使用「字典包含键()」方法先判断键是否存在，或用「字典获取()」提供默认值。',
    'AttributeError': '请检查对象是否拥有该属性或方法，需确认类定义中已声明。注意区分属性和方法——方法需要加括号调用。',
    'ImportError': '请检查模块名是否拼写正确，确认模块已安装或在标准库路径中。段言中模块名使用中文，如「导入 数学」。',
    'RuntimeError': '程序运行时出现异常，请根据具体错误信息排查。建议检查代码逻辑和数据处理流程。',
    'ZeroDivisionError': '除数不能为零，请在除法前添加条件判断，如「如果 除数 != 0：」。',
    'FileNotFoundError': '请检查文件路径是否正确，确认文件是否存在。建议使用绝对路径或相对于当前目录的正确路径。',
    'IOError': '输入输出操作失败，请检查文件状态和权限。确认文件未被其他程序占用，且当前用户有读写权限。',
    'MemoryError': '内存不足，请尝试优化代码或增加系统内存。建议分批处理大数据量，避免一次性加载过多数据。',
    'RecursionError': '递归过深，请检查函数是否存在无限递归，增加递归终止条件。考虑用循环替代递归。',
    'StopIteration': '迭代器已无更多元素，请检查循环逻辑或使用默认值。可在遍历时使用「尝试」结构捕获停止信号。',
    'AssertionError': '断言条件不满足，请检查断言表达式是否正确。确认前置条件、中间结果和后置条件是否符合预期。',
    'NotImplementedError': '该方法尚未实现，请补充实现代码。如果是抽象方法，请确保子类已正确覆写。',
    'OverflowError': '数值运算结果超出范围，请使用更大的数据类型或调整运算逻辑。',
    'ArithmeticError': '算术运算出错，请检查操作数和运算符是否正确。注意运算优先级，必要时使用括号显式分组。',
    'LookupError': '查找操作失败，请检查索引或键是否存在。建议先使用「包含」方法验证后再访问。',
    'IndentationError': '缩进不正确，请检查代码缩进是否一致。段言使用 4 个空格作为标准缩进，不要混用 Tab 和空格。',
    'TabError': '制表符使用不一致，请统一使用空格进行缩进。建议在编辑器中设置将 Tab 自动转换为空格。',
    'UnicodeDecodeError': '文件编码与解码方式不匹配，请指定正确的编码格式，如「读取文件(路径, 编码="utf-8")」。',
    'UnicodeEncodeError': '编码失败，请检查文本中是否包含无法编码的字符，指定合适的编码格式。',
    'EOFError': '输入意外结束，请检查输入是否完整。确认文件没有损坏，或输入流未提前关闭。',
    'KeyboardInterrupt': '用户按下了 Ctrl+C 中断了程序执行。',
    'OSError': '系统调用失败，请检查文件路径、网络连接和系统资源状态。确认操作权限是否足够。',
    'ModuleNotFoundError': '模块未找到，请检查模块名是否拼写正确，确认模块已安装。段言中可使用「导入 模块名」导入模块。',
    'PermissionError': '权限不足，请检查文件或目录的访问权限。尝试以管理员身份运行或修改文件权限。',
    'ConnectionError': '网络连接失败，请检查网络连接是否正常，确认目标服务器地址和端口是否正确。',
    'TimeoutError': '操作超时，请检查网络状态或增加超时时间。确认目标服务是否正常运行。',
    'FloatingPointError': '浮点运算出错，请检查是否存在除以零、精度溢出等浮点异常情况。',
    'ReferenceError': '引用错误，尝试访问已被垃圾回收的弱引用对象。',
    'SystemError': '解释器内部错误，请记录错误信息并报告给段言开发团队。',
    # 段言自定义错误提示
    'LexerError': '词法分析时发现非法字符或无法识别的符号。请检查代码中是否包含段言不支持的字符，确保使用正确的中文关键字。',
    'ParserError': '语法解析失败，请检查代码结构是否正确。段言中语句通常以句号「。」结尾，段落定义以冒号「：」结尾。',
    'SemanticError': '语义分析错误，请检查变量是否已定义、类型是否匹配、函数调用参数是否正确。段言要求先定义后使用。',
    'CodeGenError': '代码生成失败，请检查代码中是否存在段言不支持的语法结构或特殊用法。',
    'CompileError': '编译过程中出现错误，请根据具体错误信息调整代码。可尝试使用「--backend」切换编译后端。',
    'DuanError': '段言运行时错误，请根据具体错误信息进行排查和修复。',
    'ModuleError': '模块加载错误，请检查模块名是否正确，确认模块文件存在且没有语法错误。',
    'CircularDependencyError': '模块间存在循环依赖，请重构代码消除循环导入。可以将共用部分提取到独立模块中。',
    'ParseError': '解析错误，请检查代码语法是否正确，确认语句格式符合段言语法的要求。',
    'UnificationError': '类型统一失败，请检查两个类型是否兼容。段言不支持隐式类型转换，需要显式转换。',
    'TypeErrorInference': '类型推断失败，请为变量添加显式类型注解或确保赋值表达式类型明确。',
}

_EXAMPLE_SNIPPETS = {
    'SyntaxError': '  打印("你好，世界！")\n  如果 甲 > 10：\n      打印("甲大于10")',
    'TypeError': '  设 数字 为 整数("123")  # 将文本转换为整数\n  设 文本 为 文本(123)     # 将整数转换为文本',
    'ValueError': '  设 数字 为 整数(输入())  # 确保输入可转换为整数\n  如 数字 在 1 到 100 之间：\n      打印(数字)',
    'NameError': '  设 变量名 为 值\n  打印(变量名)  # 先定义后使用',
    'IndexError': '  设 列表 为 [1, 2, 3]\n  如 索引 < 长度(列表)：\n      打印(列表[索引])',
    'KeyError': '  设 字典 为 {"名字": "张三"}\n  如 字典包含键(字典, "名字")：\n      打印(字典["名字"])',
    'AttributeError': '  设 文本 为 "hello"\n  打印(字符串长度(文本))  # 使用函数而非属性',
    'ImportError': '  导入 数学\n  打印(数学.平方根(16))',
    'ZeroDivisionError': '  如 除数 != 0：\n      打印(10 除以 除数)\n  否则：\n      打印("除数不能为零")',
    'FileNotFoundError': '  设 内容 为 读取文件("data/文件.txt")',
    'RecursionError': '  段落 阶乘(n)：\n      如 n <= 1：\n          返回 1\n      返回 n 乘 阶乘(n - 1)',
    'AssertionError': '  断言 甲 > 0， "甲必须大于0"',
    'NotImplementedError': '  段落 待实现()：\n      引发 未实现错误("此功能待实现")',
    'OverflowError': '  设 大数 为 10 的 100 次方  # 使用大整数类型',
    'ArithmeticError': '  设 结果 为 (10 加 5) 乘 2  # 使用括号明确优先级',
    'LookupError': '  设 列表 为 [1, 2, 3]\n  设 元素 为 列表获取(列表, 索引, 默认值)',
    'IndentationError': '  段落 测试：\n      打印("正确缩进")\n      打印("保持缩进一致")',
    'TabError': '  请统一使用空格进行缩进，不要混用 Tab 和空格',
    'ModuleNotFoundError': '  导入 数学\n  打印(数学.平方根(16))',
    'PermissionError': '  请检查文件权限或以管理员身份运行',
    'UnicodeDecodeError': '  设 内容 为 读取文件("文件.txt", 编码="utf-8")',
    'UnicodeEncodeError': '  设 文本 为 文本编码(内容, 编码="utf-8")',
    'EOFError': '  请检查输入是否完整，确认文件没有损坏',
    'OSError': '  请检查文件路径、网络连接和系统资源状态',
    'ConnectionError': '  请检查网络连接是否正常，确认目标服务器地址是否正确',
    'TimeoutError': '  请检查网络状态或增加超时时间',
    # 段言自定义错误示例
    'LexerError': '  设 甲 为 10  # 使用正确的中文关键字\n  打印(甲)',
    'ParserError': '  设 甲 为 10。\n  打印(甲)  # 确保语句以句号「。」结尾',
    'SemanticError': '  设 甲 为 10\n  打印(甲)  # 先定义后使用',
    'CodeGenError': '  请检查代码中是否存在段言不支持的语法结构',
    'CompileError': '  请根据具体错误信息调整代码，可尝试切换编译后端',
    'DuanError': '  请根据具体的错误信息进行修复',
    'ModuleError': '  导入 数学\n  打印(数学.平方根(16))  # 确保模块名正确',
    'CircularDependencyError': '  请将共用部分提取到独立模块中，消除循环依赖',
    'ParseError': '  设 甲 为 10。\n  打印(甲)  # 确保语法正确',
    'UnificationError': '  设 甲 为 整数 = 10\n  设 乙 为 文本 = 文本(甲)  # 显式转换',
    'TypeErrorInference': '  设 甲 为 整数  # 添加类型注解可帮助类型推断',
}


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
        chinese_name = _CHINESE_NAMES.get(err_type, err_type)
        parts.append(self._color('error', '错误'))
        parts.append(f': {chinese_name}')
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

        # 追加示例代码片段
        example = self.get_example_snippet(err_type)
        if example:
            parts.append(f'\n  参考示例：\n{example}')

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

    def get_example_snippet(self, err_type: str) -> str:
        """根据错误类型返回对应的段言代码示例

        Args:
            err_type: 错误类型名称

        Returns:
            格式化的代码示例字符串，如果无对应示例则返回空字符串
        """
        snippet = _EXAMPLE_SNIPPETS.get(err_type)
        if snippet:
            return snippet
        # 尝试匹配基类错误类型
        for base_type in ['DuanError', 'RuntimeError', 'LookupError', 'ArithmeticError']:
            if base_type in _EXAMPLE_SNIPPETS:
                return _EXAMPLE_SNIPPETS[base_type]
        return ''

    def _get_suggestion(self, err_type: str, err_msg: str) -> str:
        """获取修复建议"""
        # 先尝试返回通用的中文修改指引
        hint = _CHINESE_HINTS.get(err_type)
        if hint:
            return hint

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