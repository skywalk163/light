#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 核心类

提供交互式开发环境的核心功能。
"""

import sys
import os
from typing import List, Optional, Dict, Any

# 添加路径
_current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _current_dir)
sys.path.insert(0, os.path.join(_current_dir, 'src'))
sys.path.insert(0, os.path.join(_current_dir, 'antlrparser'))

from .executor import Executor, Environment
from .commands import CommandHandler
from .highlighter import LightHighlighter
from .completer import LightCompleter
from .enhanced import EnhancedREPL, HAS_PROMPT_TOOLKIT
from errors import LightError, LightErrorFormatter, format_source_context, format_error_with_context
from debug_engine import DebugEngine


# =============================================================================
# LightREPL 核心类
# =============================================================================

class LightREPL:
    """光明交互式开发环境核心类

    提供：
    - 代码执行
    - 环境管理
    - 历史记录
    - 多行支持
    - 命令处理
    - 语法高亮
    - 代码补全
    """

    def __init__(self, enhanced: bool = False):
        """初始化REPL

        Args:
            enhanced: 是否使用增强模式（prompt_toolkit）
        """
        self.executor = Executor()
        self.highlighter = LightHighlighter(use_color=True)
        self.completer = LightCompleter(
            env=self.executor.env.variables if self.executor.env else {}
        )
        self.command_handler = CommandHandler(
            env=self.executor.env.variables if self.executor.env else {},
            executor=self.executor,
            debug_engine=self._debug_engine,
        )
        self.buffer: List[str] = []
        self.history: List[str] = []
        self._history_index = -1  # 历史导航索引
        self.debug_mode = False
        self._debug_engine = DebugEngine()
        self.enhanced = enhanced

        # 尝试加载增强模式
        if enhanced:
            if HAS_PROMPT_TOOLKIT:
                self._enhanced_impl = EnhancedREPL(self)
                self._use_enhanced = True
            else:
                self._use_enhanced = False
        else:
            self._use_enhanced = False

    # ------------------------------------------------------------------
    # 多行检测
    # ------------------------------------------------------------------

    def _is_multiline_start(self, line: str) -> bool:
        """判断是否是多行开始"""
        line = line.strip()
        starters = ['函数', '段落', '类', '接口', '如果', '当', '遍历', '尝试']
        for s in starters:
            if line.startswith(s) and (line.endswith(':') or line.endswith('：')):
                return True
        return False

    def _is_multiline_end(self, line: str) -> bool:
        """判断是否是多行结束"""
        return line.strip() in ['结束。', '结束', '结束。', '否则', '否则：', '否则:']

    def _is_indented_block(self, line: str) -> bool:
        """判断是否是缩进块中的行"""
        stripped = line.strip()
        if not stripped:
            return False
        # 缩进块中的行以缩进开头
        return line.startswith(' ') or line.startswith('\t')

    def _is_continuation(self, line: str) -> bool:
        """判断当前行是否需要继续输入"""
        stripped = line.strip()
        if not stripped:
            return False
        # 以运算符结尾的行需要继续
        operators = ['+', '-', '*', '/', '加', '减', '乘', '除', '且', '或', '，', ',']
        for op in operators:
            if stripped.endswith(op):
                return True
        # 未闭合的括号
        if stripped.count('(') > stripped.count(')'):
            return True
        if stripped.count('[') > stripped.count(']'):
            return True
        return False

    # ------------------------------------------------------------------
    # 缓冲区管理
    # ------------------------------------------------------------------

    def execute_buffer(self) -> Optional[str]:
        """执行缓冲区代码"""
        if not self.buffer:
            return None

        code = '\n'.join(self.buffer)
        self.buffer = []
        self.history.append(code)

        return self._execute_code(code)

    def _execute_code(self, code: str) -> Optional[str]:
        """执行代码并格式化错误

        Args:
            code: 要执行的光明代码

        Returns:
            执行结果或错误信息
        """
        try:
            # 调试模式：在代码执行前检查断点
            if self.debug_mode and self._debug_engine:
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    if self._debug_engine.should_break('<repl>', i):
                        stack_info = self._format_debug_state()
                        return f"⏸ 暂停于行 {i}\n{stack_info}"

            result = self.executor.execute(code)

            # 高亮显示结果
            if result is not None:
                output = str(result)
                # 尝试高亮输出
                try:
                    highlighted = self.highlighter.highlight(output)
                    return highlighted
                except Exception:
                    return output

            return None
        except LightError as e:
            # 使用 LightErrorFormatter 格式化光明错误
            return LightErrorFormatter.format(e, code)
        except SyntaxError as e:
            # 语法错误
            line = e.lineno or 0
            col = e.offset or 0
            context = format_source_context(code, line, col)
            msg = f"语法错误: {e.msg}"
            if context:
                msg += f"\n{context}"
            return msg
        except Exception as e:
            # 其他错误
            import traceback
            tb = traceback.format_exc()
            # 尝试提取行号
            line = 0
            if hasattr(e, 'lineno'):
                line = e.lineno
            elif hasattr(e, 'line'):
                line = e.line
            context = format_source_context(code, line) if line else ""
            msg = f"错误: {type(e).__name__}: {e}"
            if context:
                msg += f"\n{context}"
            return msg

    def _format_debug_state(self) -> str:
        """格式化调试状态信息"""
        if not self._debug_engine:
            return ""
        status = self._debug_engine.get_status()
        parts = []
        parts.append(f"  当前位置: {status['current_file']}:{status['current_line']}")
        vars = self._debug_engine.get_variables()
        if vars:
            parts.append("  变量:")
            for name, value in vars.items():
                parts.append(f"    {name} = {repr(value)}")
        watch = self._debug_engine.get_watch_values()
        if watch:
            parts.append("  监视:")
            for name, value in watch.items():
                parts.append(f"    {name} = {repr(value)}")
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # 输入处理
    # ------------------------------------------------------------------

    def process_input(self, line: str) -> Optional[str]:
        """处理输入"""
        line = line.strip()

        # 空行
        if not line:
            if self.buffer:
                return self.execute_buffer()
            return None

        # 注释
        if line.startswith('#'):
            return None

        # 命令（以 : 开头）
        if line.startswith(':'):
            result = self.command_handler.handle(line)
            self.history.append(line)

            if result == 'CLEAR':
                os.system('cls' if os.name == 'nt' else 'clear')
                self.print_banner()
                return None
            elif result == 'RESET':
                self.executor.reset()
                self.completer.update_env(
                    self.executor.env.variables if self.executor.env else {}
                )
                return "环境已重置"

            return result

        # 多行检测：缩进块
        if self.buffer:
            # 已经在缓冲区中
            if self._is_multiline_end(line):
                self.buffer.append(line)
                return self.execute_buffer()
            self.buffer.append(line)
            return None

        # 多行开始
        if self._is_multiline_start(line) or self._is_continuation(line):
            self.buffer.append(line)
            return None

        # 单行执行
        return self.execute_line(line)

    # ------------------------------------------------------------------
    # 输入输出
    # ------------------------------------------------------------------

    def print_banner(self):
        """打印欢迎信息"""
        print("""
╔══════════════════════════════════════════════╗
║           光明 (LightLang) REPL              ║
║           版本: 1.0.0                        ║
║                                              ║
║  输入光明代码，按 Enter 执行                  ║
║  输入 :help 获取帮助                         ║
║  输入 :exit 或按 Ctrl+D 退出                 ║
║                                              ║
║  支持: 多行输入 / 代码补全 / 语法高亮         ║
║        调试模式 / 断点 / 变量监视             ║
╚══════════════════════════════════════════════╝
""")

    def read_input(self, prompt: str) -> Optional[str]:
        """读取用户输入（支持历史导航）"""
        # 在增强模式下使用 prompt_toolkit
        if self._use_enhanced:
            return self._enhanced_impl.read_input(prompt)

        try:
            line = input(prompt)
            return line
        except EOFError:
            return None

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    def execute_line(self, line: str) -> Optional[str]:
        """执行单行代码"""
        self.history.append(line)
        return self._execute_code(line)

    def execute(self, code: str):
        """执行代码并返回结果

        Args:
            code: 光明代码

        Returns:
            执行结果
        """
        return self.executor.execute(code)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def run(self):
        """启动REPL主循环"""
        self.print_banner()

        while True:
            try:
                # 读取输入
                if self.buffer:
                    prompt = "...   "
                else:
                    prompt = "光明> "

                line = self.read_input(prompt)

                if line is None:
                    break

                # 处理输入
                result = self.process_input(line)

                # 显示结果（对结果进行语法高亮）
                if result and result != 'EXIT':
                    # 如果是错误信息，直接显示（已包含格式化）
                    if result.startswith(('错误:', '语法错误:', '┌─', '┌─')):
                        print(result, file=sys.stderr)
                    else:
                        print(result)

                if result == 'EXIT':
                    print("再见！")
                    break

            except KeyboardInterrupt:
                print("\n^C")
                self.buffer = []
            except EOFError:
                print("\n再见！")
                break


# =============================================================================
# 入口点
# =============================================================================

def main():
    """REPL入口点"""
    repl = LightREPL()
    repl.run()


if __name__ == '__main__':
    main()