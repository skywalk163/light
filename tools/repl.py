# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - REPL 交互式解释器

提供交互式的光明编程环境，支持逐行执行、变量查看、命令历史、基础调试等功能。
"""

import sys
import os
import io
import traceback
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator
from tokens import TokenType
from errors import format_exception


BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║           光明（LightLang）交互式解释器 v1.6.0                     ║
╠══════════════════════════════════════════════════════════════════╣
║  输入表达式或语句，按回车执行。                                   ║
║  命令: 帮助(help) | 退出(quit) | 变量(vars) | 历史(history)      ║
║  调试: 跟踪(trace) | 跳过(step) | 断点(bp) | 运行(run)           ║
╚══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║                        光明 REPL 帮助                            ║
╠══════════════════════════════════════════════════════════════════╣
║  一般命令:                                                        ║
║    帮助 / help     - 显示此帮助信息                               ║
║    退出 / quit     - 退出 REPL                                   ║
║    变量 / vars     - 显示当前所有变量                             ║
║    清除 / clear    - 清除所有变量                                 ║
║    历史 / history  - 显示命令历史                                 ║
║    代码 / code     - 显示累积的 Python 代码                       ║
║    加载 / load     - 加载并执行 .light 文件                        ║
║                                                                    ║
║  调试命令:                                                        ║
║    跟踪 / trace    - 启用/禁用语句跟踪                            ║
║    跳过 / step     - 单步执行（调试模式）                         ║
║    断点 / bp       - 设置/显示断点                                ║
║    运行 / run      - 从断点继续运行                                ║
║                                                                    ║
║  快捷键:                                                          ║
║    Ctrl+C          - 取消当前输入                                 ║
║    Ctrl+D          - 退出 REPL                                   ║
║    ↑/↓             - 浏览命令历史（如果支持）                      ║
╚══════════════════════════════════════════════════════════════════╝
"""


class LightREPL:
    """光明交互式解释器"""

    def __init__(self):
        self.compiler = LightCompiler()
        self.codegen = UnifiedCodeGenerator()
        self.globals: Dict[str, Any] = {}
        self.accumulated_code: List[str] = []
        self.statement_buffer: List[str] = []
        self.in_block = False
        self.block_indent = 0
        
        # 命令历史
        self.history: List[str] = []
        self.history_index = -1
        
        # 调试模式
        self.trace_enabled = False
        self.debug_mode = False
        self.breakpoints: set = set()
        self.current_line = 0

    def reset(self):
        """重置 REPL 状态"""
        self.globals = {}
        self.accumulated_code = []
        self.statement_buffer = []
        self.in_block = False
        self.block_indent = 0
        self.current_line = 0

    def _exec_code(self, python_code: str) -> str:
        """执行 Python 代码，返回输出"""
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exec(python_code, self.globals)
            output = sys.stdout.getvalue()
        except Exception as e:
            # 使用美化的错误格式
            output = format_exception(type(e), e, e.__traceback__)
        finally:
            sys.stdout = old_stdout
        return output

    def _compile_and_run(self, source: str) -> str:
        """编译并运行光明代码"""
        self.current_line += 1
        
        # 如果启用了跟踪，打印即将执行的代码
        if self.trace_enabled:
            print(f"▶ 第 {self.current_line} 行: {source.strip()[:60]}...")
        
        try:
            result = self.compiler.compile(source)
            if result['errors']:
                return "\n".join(f"✗ {e}" for e in result['errors'])

            ast = result['ast']
            python_code = self.codegen.generate(ast)
            self.accumulated_code.append(python_code)
            return self._exec_code(python_code)
        except Exception as e:
            return format_exception(type(e), e, e.__traceback__)

    def _is_expression(self, source: str) -> bool:
        """简单判断是否是表达式"""
        source = source.strip()
        if not source:
            return False
        statement_keywords = [
            '设', '定义', '如果', '遍历', '当', '段落', '类', '返回',
            '打印', '导入', '从', '导出', '属性', '构造', '尝试',
            '捕获', '最终', '抛出', '继续', '跳出', '对于',
        ]
        for kw in statement_keywords:
            if source.startswith(kw):
                return False
        return True

    def show_variables(self):
        """显示当前变量"""
        vars_list = []
        exclude_names = {
            '__builtins__', '__name__', '__doc__', '__package__',
            '__loader__', '__spec__', '__file__', '__cached__',
            'sys', 'os', 'io', 'asyncio', 'importlib', 'spec',
            'Path', 'List', 'Dict', 'Any', 'Optional',
        }
        for k, v in self.globals.items():
            if k not in exclude_names and not k.startswith('_light_'):
                if hasattr(v, '__module__') and v.__module__ in ('builtins', 'os', 'sys', 'io'):
                    continue
                vars_list.append((k, v))

        if not vars_list:
            print("（无变量）")
            return

        print("╔══════════════════════════════════════════════════════════╗")
        print("║                        当前变量                           ║")
        print("╠══════════════════════════════════════════════════════════╣")
        for name, value in vars_list:
            if callable(value):
                type_hint = "<函数>"
            elif isinstance(value, type):
                type_hint = "<类>"
            elif isinstance(value, (list, tuple)):
                type_hint = f"<{type(value).__name__} len={len(value)}>"
            elif isinstance(value, dict):
                type_hint = f"<dict len={len(value)}>"
            else:
                type_hint = f"<{type(value).__name__}>"
            
            value_str = repr(value)
            if len(value_str) > 40:
                value_str = value_str[:37] + "..."
            print(f"║  {name:<20} {type_hint:<20} = {value_str:<20}║")
        print("╚══════════════════════════════════════════════════════════╝")

    def show_history(self):
        """显示命令历史"""
        if not self.history:
            print("（无历史记录）")
            return
        
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                        命令历史                           ║")
        print("╠══════════════════════════════════════════════════════════╣")
        for i, cmd in enumerate(self.history[-50:], 1):  # 只显示最近50条
            if len(cmd) > 50:
                cmd = cmd[:47] + "..."
            print(f"║  {i:3d}: {cmd:<50}║")
        print("╚══════════════════════════════════════════════════════════╝")

    def show_code(self):
        """显示累积的 Python 代码"""
        if not self.accumulated_code:
            print("（无代码）")
            return
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                    累积的 Python 代码                     ║")
        print("╠══════════════════════════════════════════════════════════╣")
        for i, code in enumerate(self.accumulated_code):
            lines = code.strip().split('\n')
            print(f"║  --- 第 {i+1} 段 ({len(lines)} 行) ---")
            for line in lines[:10]:  # 每段最多显示10行
                if len(line) > 50:
                    line = line[:47] + "..."
                print(f"║    {line}")
            if len(lines) > 10:
                print(f"║    ... ({len(lines) - 10} 行省略)")
        print("╚══════════════════════════════════════════════════════════╝")

    def show_breakpoints(self):
        """显示断点"""
        if not self.breakpoints:
            print("（无断点）")
            return
        print(f"断点: {', '.join(str(bp) for bp in sorted(self.breakpoints))}")

    def toggle_trace(self):
        """切换跟踪模式"""
        self.trace_enabled = not self.trace_enabled
        status = "启用" if self.trace_enabled else "禁用"
        print(f"✓ 语句跟踪已{status}")

    def load_file(self, filepath: str):
        """加载并执行 .light 文件"""
        if not os.path.exists(filepath):
            print(f"✗ 文件不存在: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"📂 加载文件: {filepath}")
        output = self._compile_and_run(source)
        if output:
            print(output.rstrip())

    def _detect_block_start(self, line: str) -> bool:
        """检测是否是块开始"""
        return line.rstrip().endswith('：') or line.rstrip().endswith(':')

    def _get_indent(self, line: str) -> int:
        """获取行的缩进级别"""
        count = 0
        for ch in line:
            if ch == ' ':
                count += 1
            elif ch == '\t':
                count += 4
            else:
                break
        return count

    def _add_to_history(self, line: str):
        """添加命令到历史"""
        if line.strip() and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.history_index = len(self.history)

    def process_line(self, line: str) -> Optional[str]:
        """处理一行输入"""
        # 添加到历史
        self._add_to_history(line)
        
        stripped = line.strip()

        # 空行处理
        if not stripped:
            if self.in_block:
                return self._execute_buffer()
            return ""

        # 特殊命令
        if stripped in ('帮助', 'help', '?'):
            return HELP_TEXT

        if stripped in ('退出', 'quit', 'exit', 'q'):
            return 'QUIT'

        if stripped in ('变量', 'vars', '变量()', 'v'):
            self.show_variables()
            return ""

        if stripped in ('清除', 'clear', 'reset', 'c'):
            self.reset()
            return "✓ 已清除所有变量和代码"

        if stripped in ('历史', 'history', 'hist', 'h'):
            self.show_history()
            return ""

        if stripped in ('代码', 'code', 'src'):
            self.show_code()
            return ""

        if stripped in ('跟踪', 'trace', 't'):
            self.toggle_trace()
            return ""

        if stripped in ('断点', 'bp', 'break'):
            self.show_breakpoints()
            return ""

        if stripped.startswith('加载 ') or stripped.startswith('load '):
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                filepath = parts[1].strip().strip('"').strip("'")
                self.load_file(filepath)
            else:
                return "用法: 加载 <文件名>"
            return ""

        # 处理块结构
        if self.in_block:
            current_indent = self._get_indent(line)
            if current_indent < self.block_indent:
                return self._execute_buffer()
            self.statement_buffer.append(line)
            return None

        # 检查是否开始新块
        if self._detect_block_start(stripped):
            self.in_block = True
            self.block_indent = 2
            self.statement_buffer = [line]
            return None

        # 普通语句
        return self._run_single_statement(line)

    def _execute_buffer(self) -> str:
        """执行缓冲的代码块"""
        source = '\n'.join(self.statement_buffer) + '\n'
        self.statement_buffer = []
        self.in_block = False
        self.block_indent = 0
        return self._compile_and_run(source)

    def _run_single_statement(self, line: str) -> str:
        """运行单条语句"""
        source = line + '\n'
        if self._is_expression(line):
            try:
                result = self.compiler.compile(source)
                if not result['errors']:
                    ast = result['ast']
                    python_code = self.codegen.generate(ast)
                    output = self._exec_code(python_code)
                    if not output.strip():
                        print_source = f"打印 {line}\n"
                        result2 = self.compiler.compile(print_source)
                        if not result2['errors']:
                            ast2 = result2['ast']
                            python_code2 = self.codegen.generate(ast2)
                            output2 = self._exec_code(python_code2)
                            if output2.strip():
                                self.accumulated_code.append(python_code2)
                                return output2.rstrip()
                    self.accumulated_code.append(python_code)
                    return output.rstrip() if output else ""
            except:
                pass
        return self._compile_and_run(source)

    def run(self):
        """运行 REPL 主循环"""
        print(BANNER)

        while True:
            try:
                if self.in_block:
                    prompt = "... "
                else:
                    prompt = ">>> "

                line = input(prompt)
                result = self.process_line(line)

                if result == 'QUIT':
                    print("再见！")
                    break

                if result is not None:
                    if result:
                        print(result)

            except KeyboardInterrupt:
                print()
                print("（按 Ctrl+D 或输入 '退出' 退出）")
                self.statement_buffer = []
                self.in_block = False
                continue

            except EOFError:
                print()
                print("再见！")
                break


def main():
    """REPL 入口函数"""
    repl = LightREPL()
    repl.run()


if __name__ == '__main__':
    main()

