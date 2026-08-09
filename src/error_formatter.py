# -*- coding: utf-8 -*-
"""
光明运行时错误信息友好化模块

将 Python 运行时的异常 traceback 转换为光明源码行号和友好的中文错误信息。
"""

import sys
import re
import traceback
from typing import List, Tuple, Optional


class LightErrorFormatter:
    """光明错误信息格式化器"""

    def __init__(self, source: str = '', source_name: str = '<光明代码>'):
        self.source = source
        self.source_name = source_name
        self.source_lines = source.split('\n') if source else []

    def parse_line_mapping(self, python_code: str) -> dict:
        """从生成的 Python 代码中解析 LIGHT_SRC 行号映射表

        Returns:
            dict: {python_line: (light_line, code_snippet)}
        """
        mapping = {}
        for line in python_code.split('\n'):
            m = re.match(r'#\s*LIGHT_SRC:(\d+):(.*)', line)
            if m:
                light_line = int(m.group(1))
                snippet = m.group(2)
                mapping[line] = (light_line, snippet)
        return mapping

    def build_full_mapping(self, python_code: str) -> dict:
        """构建完整的 Python 行号 -> 光明行号映射

        思路：
        1. 先找 LIGHT_SRC 注释对应的 Python 行号
        2. 假设两个相邻映射点之间是连续的（简单的近似）
        """
        lines = python_code.split('\n')
        anchors = []  # (py_line, light_line)

        for i, line in enumerate(lines):
            m = re.match(r'#\s*LIGHT_SRC:(\d+):', line)
            if m:
                anchors.append((i, int(m.group(1))))

        if not anchors:
            return {}

        mapping = {}
        for idx, (py_line, light_line) in enumerate(anchors):
            if idx + 1 < len(anchors):
                next_py, next_light = anchors[idx + 1]
                py_end = next_py
            else:
                py_end = len(lines)

            for p in range(py_line, py_end):
                if mapping.get(p) is None:
                    mapping[p] = light_line

        return mapping

    def format_exception(self, exc_type=None, exc_value=None, exc_tb=None) -> str:
        """格式化异常为光明友好的错误信息

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_tb: traceback 对象

        Returns:
            格式化后的错误信息字符串
        """
        if exc_type is None:
            exc_type, exc_value, exc_tb = sys.exc_info()

        if exc_type is None:
            return "未知错误"

        result = []
        result.append("=" * 60)
        result.append(f"❌ 光明运行时错误: {exc_type.__name__}")
        result.append("=" * 60)
        result.append("")

        result.append(f"📋 错误类型: {self._chinese_exc_name(exc_type.__name__)}")
        result.append(f"💬 错误信息: {exc_value}")
        result.append("")

        if exc_tb:
            result.append("📍 错误位置：")
            result.append("-" * 60)
            tb_lines = traceback.format_tb(exc_tb)
            for tb_line in tb_lines:
                result.append(tb_line.rstrip())

            result.append("")

        if self.source_lines:
            result.append(self._format_source_context(exc_tb))

        result.extend(self._suggest_fix(exc_type.__name__, str(exc_value)))

        return "\n".join(result)

    def format_traceback_string(self, tb_text: str) -> str:
        """格式化 traceback 字符串为光明友好版本"""
        result = []
        result.append("=" * 60)
        result.append("❌ 光明运行时错误")
        result.append("=" * 60)
        result.append("")
        result.append(tb_text)
        return "\n".join(result)

    def _chinese_exc_name(self, en_name: str) -> str:
        """将英文异常名转为中文"""
        mapping = {
            'NameError': '变量未定义',
            'TypeError': '类型错误',
            'ValueError': '值错误',
            'IndexError': '索引越界',
            'KeyError': '键不存在',
            'AttributeError': '属性不存在',
            'ZeroDivisionError': '除零错误',
            'IOError': '输入输出错误',
            'FileNotFoundError': '文件未找到',
            'ImportError': '导入错误',
            'ModuleNotFoundError': '模块未找到',
            'SyntaxError': '语法错误',
            'IndentationError': '缩进错误',
            'RuntimeError': '运行时错误',
            'StopIteration': '迭代结束',
            'RecursionError': '递归过深',
            'MemoryError': '内存不足',
            'OverflowError': '数值溢出',
            'ArithmeticError': '算术错误',
            'LookupError': '查找错误',
            'OSError': '系统错误',
            'PermissionError': '权限不足',
            'ConnectionError': '连接错误',
            'TimeoutError': '超时错误',
            'AssertionError': '断言失败',
            'UnicodeDecodeError': 'Unicode解码错误',
            'UnicodeEncodeError': 'Unicode编码错误',
            'EOFError': '文件提前结束',
            'FloatingPointError': '浮点运算错误',
            'ReferenceError': '引用错误',
            'TabError': 'Tab与空格混用',
            'SystemError': '系统内部错误',
            'SystemExit': '程序退出',
            'KeyboardInterrupt': '用户中断',
        }
        return mapping.get(en_name, en_name)

    def _format_source_context(self, exc_tb, context_lines: int = 2) -> str:
        """格式化错误位置的源码上下文"""
        result = []
        result.append("📄 源码上下文：")
        result.append("-" * 60)

        last_line = None
        for tb_frame, lineno in self._walk_tb(exc_tb):
            last_line = lineno
            break

        if last_line is None:
            result.append("（无法定位源码位置）")
            return "\n".join(result)

        start = max(0, last_line - context_lines - 1)
        end = min(len(self.source_lines), last_line + context_lines)

        for i in range(start, end):
            line_num = i + 1
            line_content = self.source_lines[i] if i < len(self.source_lines) else ''

            if line_num == last_line:
                result.append(f"  → {line_num:4d} | {line_content}  ◀━━ 错误位置")
            else:
                result.append(f"    {line_num:4d} | {line_content}")

        return "\n".join(result)

    def _walk_tb(self, exc_tb):
        """遍历 traceback"""
        while exc_tb:
            yield exc_tb.tb_frame, exc_tb.tb_lineno
            exc_tb = exc_tb.tb_next

    def _suggest_fix(self, exc_name: str, exc_msg: str) -> List[str]:
        """根据异常类型给出修复建议"""
        suggestions = []
        suggestions.append("")
        suggestions.append("💡 修复建议：")
        suggestions.append("-" * 60)

        if exc_name == 'NameError':
            suggestions.append("• 检查变量名是否拼写正确")
            suggestions.append("• 确认变量在使用前已经通过'设 ... 为'声明")
            suggestions.append("• 检查变量是否在正确的作用域内（如在段落内部定义的变量不能在外部使用）")
            suggestions.append(f"  错误信息提示: {exc_msg}")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 x 为 10")
            suggestions.append("          打印(x)")
            suggestions.append("")
            suggestions.append("    错误: 打印(x)")
            suggestions.append("          设 x 为 10")
        elif exc_name == 'TypeError':
            suggestions.append("• 检查操作数类型是否正确（如不能对文本进行乘法运算）")
            suggestions.append("• 确认函数调用时参数类型与声明一致")
            suggestions.append("• 如果使用了类型注解，请检查实际传值是否符合类型要求")
            suggestions.append(f"  错误信息提示: {exc_msg}")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 x 为 整数 = 10")
            suggestions.append("          设 y 为 整数 = 20")
            suggestions.append("          打印(x 加 y)")
            suggestions.append("")
            suggestions.append("    错误: 设 x 为 文本 = \"hello\"")
            suggestions.append("          打印(x 乘 2)")
        elif exc_name == 'IndexError':
            suggestions.append("• 检查列表索引是否在有效范围内（索引从0开始，长度为N的列表最大索引为N-1）")
            suggestions.append("• 可以先用 长度() 获取列表长度后再访问")
            suggestions.append("• 使用 有() 方法判断索引是否有效")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 lst 为 [1, 2, 3]")
            suggestions.append("          如 索引 < 长度(lst)：")
            suggestions.append("              打印(lst[索引])")
            suggestions.append("          否则：")
            suggestions.append("              打印(\"索引越界\")")
        elif exc_name == 'KeyError':
            suggestions.append("• 检查字典键是否存在")
            suggestions.append("• 可以用 有() 方法先判断键是否存在")
            suggestions.append("• 使用 获取() 方法提供默认值")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 d 为 {'名字': '张三'}")
            suggestions.append("          如 有(d, '年龄')：")
            suggestions.append("              打印(d['年龄'])")
            suggestions.append("          否则：")
            suggestions.append("              打印(获取(d, '年龄', 0))")
        elif exc_name == 'AttributeError':
            suggestions.append("• 检查对象是否拥有该属性或方法")
            suggestions.append("• 确认类名/对象名拼写正确")
            suggestions.append("• 检查是否混淆了属性和方法（方法需要加括号调用）")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 s 为 \"hello\"")
            suggestions.append("          打印(长度(s))")
            suggestions.append("")
            suggestions.append("    错误: 设 s 为 \"hello\"")
            suggestions.append("          打印(s.长度)")
        elif exc_name == 'ZeroDivisionError':
            suggestions.append("• 检查除数是否为零")
            suggestions.append("• 在除法前添加条件判断")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 除数 为 0")
            suggestions.append("          如 除数 != 0：")
            suggestions.append("              打印(10 / 除数)")
            suggestions.append("          否则：")
            suggestions.append("              打印(\"除数不能为零\")")
        elif exc_name == 'IndentationError':
            suggestions.append("• 检查缩进是否一致（光明使用 4 空格缩进）")
            suggestions.append("• 不要混用 Tab 和空格")
            suggestions.append("• 确保所有同级语句缩进级别相同")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 段落 测试：")
            suggestions.append("              打印(\"第一行\")")
            suggestions.append("              打印(\"第二行\")")
            suggestions.append("")
            suggestions.append("    错误: 段落 测试：")
            suggestions.append("              打印(\"第一行\")")
            suggestions.append("            打印(\"缩进不一致\")")
        elif exc_name == 'FileNotFoundError':
            suggestions.append("• 检查文件路径是否正确")
            suggestions.append("• 使用绝对路径或相对于当前目录的路径")
            suggestions.append("• 确认文件确实存在")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 内容 为 读取文件(\"data/文件.txt\")")
            suggestions.append("")
            suggestions.append("    错误: 设 内容 为 读取文件(\"不存在的文件.txt\")")
        elif exc_name == 'RecursionError':
            suggestions.append("• 检查函数是否存在无限递归")
            suggestions.append("• 增加递归终止条件")
            suggestions.append("• 考虑使用循环替代递归")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 段落 递归(n):")
            suggestions.append("              如 n <= 0:")
            suggestions.append("                  返回 0")
            suggestions.append("              返回 n 加 递归(n - 1)")
            suggestions.append("")
            suggestions.append("    错误: 段落 无限递归():")
            suggestions.append("              返回 无限递归()")
        elif exc_name == 'AssertionError':
            suggestions.append("• 检查断言条件是否正确")
            suggestions.append("• 确认前置条件满足")
            suggestions.append("• 如果断言总是失败，请修改条件或移除断言")
        elif exc_name == 'UnicodeDecodeError':
            suggestions.append("• 检查文件编码是否正确")
            suggestions.append("• 尝试指定编码格式（如 UTF-8）")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 设 内容 为 读取文件(\"文件.txt\", 编码=\"utf-8\")")
        elif exc_name == 'ImportError' or exc_name == 'ModuleNotFoundError':
            suggestions.append("• 检查模块名是否拼写正确")
            suggestions.append("• 确认模块已安装或在标准库路径中")
            suggestions.append("• 使用 导入 语句而不是直接使用模块名")
            suggestions.append("")
            suggestions.append("  示例：")
            suggestions.append("    正确: 导入 数学")
            suggestions.append("          打印(数学.π)")
        elif exc_name == 'PermissionError':
            suggestions.append("• 检查文件或目录的访问权限")
            suggestions.append("• 以管理员/超级用户身份运行程序")
            suggestions.append("• 确认目标路径有写入权限")
        elif exc_name == 'TimeoutError':
            suggestions.append("• 检查网络连接是否正常")
            suggestions.append("• 增加超时时间")
            suggestions.append("• 检查目标服务器是否可达")
        else:
            suggestions.append(f"• 详细错误信息: {exc_msg}")
            suggestions.append("• 可以查阅光明文档: docs/")
            suggestions.append("• 访问光明官网获取更多帮助")

        suggestions.append("")
        suggestions.append("📖 更多帮助：")
        suggestions.append("• 光明文档: https://docs.light-lang.org")
        suggestions.append("• 示例代码: examples/")
        suggestions.append("• 常见问题: docs/FAQ.md")

        suggestions.append("")
        return suggestions


def run_with_friendly_error(code: str, source: str = '', source_name: str = '<光明代码>') -> int:
    """执行代码并以友好的方式报告错误

    Args:
        code: 要执行的 Python 代码
        source: 光明源代码（用于上下文显示）
        source_name: 源代码名称

    Returns:
        退出码 (0=正常, 1=错误)
    """
    formatter = LightErrorFormatter(source, source_name)
    try:
        exec(code, {'__name__': '__main__', '__file__': source_name})
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        print(formatter.format_exception(exc_type, exc_value, exc_tb),
              file=sys.stderr, flush=True)
        return 1


def format_runtime_error(source: str, exc_type=None, exc_value=None, exc_tb=None) -> str:
    """便捷函数：格式化运行时错误

    Args:
        source: 光明源代码
        exc_type, exc_value, exc_tb: 异常信息，默认为 sys.exc_info()
    """
    formatter = LightErrorFormatter(source)
    return formatter.format_exception(exc_type, exc_value, exc_tb)


# 中文异常类型映射（供 raise 用）
LIGHT_EXCEPTION_MAP = {
    'NameError': '变量未定义错误',
    'TypeError': '类型错误',
    'ValueError': '值错误',
    'IndexError': '索引越界错误',
    'KeyError': '键不存在错误',
    'AttributeError': '属性不存在错误',
    'ZeroDivisionError': '除零错误',
    'IOError': '输入输出错误',
    'FileNotFoundError': '文件未找到错误',
    'RuntimeError': '运行时错误',
}


if __name__ == '__main__':
    # 测试
    source = '''设 x 为 10
设 y 为 0
设 z 为 x / y
打印 z
'''
    try:
        exec("x = 10\ny = 0\nz = x / y\nprint(z)")
    except Exception:
        print(format_runtime_error(source))
