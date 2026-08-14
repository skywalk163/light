# -*- coding: utf-8 -*-
"""
段言（Duan）编程语言 - REPL v3（基于 v3 解析器）

使用 DuanParser + PythonCodeGenerator 的交互式编程环境，
支持逐行执行、多行块结构、变量查看、命令历史等功能。

用法：
  duan repl              # 启动 REPL（使用旧版，自动回退到 v3）
  duan repl --v3         # 启动基于 v3 解析器的 REPL
"""

import sys
import os
import io
import traceback
from typing import Dict, Any, Optional, List

# 确保 src 在路径中
_src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║           段言（DuanLang）交互式解析器 v3.0                       ║
╠══════════════════════════════════════════════════════════════════╣
║  输入段言代码，按回车执行。                                       ║
║                                                                  ║
║  命令:                                                           ║
║    帮助 / help    - 显示此帮助信息                                ║
║    退出 / quit    - 退出 REPL                                    ║
║    变量 / vars    - 显示当前所有变量                              ║
║    清除 / clear   - 清除所有变量                                  ║
║    历史 / history - 显示命令历史                                  ║
║    加载 / load    - 加载并执行 .duan 文件                         ║
║                                                                  ║
║  快捷键:                                                         ║
║    Ctrl+C  - 取消当前输入                                        ║
║    Ctrl+D  - 退出 REPL                                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║                        段言 REPL 帮助                            ║
╠══════════════════════════════════════════════════════════════════╣
║  一般命令:                                                        ║
║    帮助 / help      - 显示此帮助信息                              ║
║    退出 / quit      - 退出 REPL                                  ║
║    变量 / vars      - 显示当前所有变量                            ║
║    清除 / clear     - 清除所有变量                                ║
║    历史 / history   - 显示命令历史                                ║
║    加载 / load      - 加载并执行 .duan 文件                       ║
║                                                                  ║
║  REPL 支持多行块结构：                                            ║
║    输入以「:」结尾的语句会进入多行模式，                               ║
║    连续输入缩进代码块，空行后执行。                                  ║
║                                                                  ║
║  用法示例:                                                        ║
║    >>> 设 甲 为 10。                                              ║
║    >>> 打印(甲)                                                    ║
║    >>> 如果 甲 大于 5:                                            ║
║    ...     打印("甲大于5")                                         ║
║    >>>                                                        ║
╚══════════════════════════════════════════════════════════════════╝
"""


class DuanREPLV3:
    """基于 v3 解析器的段言交互式解释器"""

    def __init__(self):
        self.globals: Dict[str, Any] = {
            '__builtins__': __builtins__,
        }
        self.accumulated_code: List[str] = []
        self.statement_buffer: List[str] = []
        self.in_block = False
        self.block_indent = 0

        # 命令历史
        self.history: List[str] = []
        self.history_index = -1

    def reset(self):
        """重置 REPL 状态"""
        self.globals = {'__builtins__': __builtins__}
        self.accumulated_code = []
        self.statement_buffer = []
        self.in_block = False
        self.block_indent = 0

    def _compile_and_run(self, source: str) -> str:
        """使用 v3 解析器编译并运行段言代码"""
        from duan_parser_v3 import DuanParser, ParseError
        from code_generator import PythonCodeGenerator, CodeGenError

        output_buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        try:
            parser = DuanParser()
            module = parser.parse(source)
            if module is None:
                return "[语法错误] 解析失败"

            generator = PythonCodeGenerator()
            python_code = generator.generate(module)

            self.accumulated_code.append(python_code)

            try:
                exec(python_code, self.globals)
            except Exception as e:
                tb = traceback.format_exc()
                # 只显示最后几行
                tb_lines = tb.strip().split('\n')
                short_tb = '\n'.join(tb_lines[-4:])
                return f"[运行错误] {type(e).__name__}: {e}\n  {short_tb}"

            output = output_buffer.getvalue()
            return output if output else ""

        except ParseError as e:
            return str(e)
        except CodeGenError as e:
            return f"[代码生成错误] {e}"
        except Exception as e:
            return f"[错误] {type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout

    def _is_expression(self, source: str) -> bool:
        """判断是否是一个表达式（而非语句）"""
        source = source.strip()
        if not source:
            return False
        statement_keywords = [
            '设', '定义', '如果', '否则', '否则若', '否则如果',
            '遍历', '当', '段落', '函数', '类', '返回',
            '打印', '导入', '从', '导出', '属性', '构造', '尝试',
            '捕获', '最终', '抛出', '继续', '跳出', '对于',
            '匹配', '情况', '默认', '使用', '静态', '异步', '等待',
            '嵌入', '标注', '继承', '实现', '枚举', '结构体',
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
        }
        for k, v in self.globals.items():
            if k not in exclude_names and not k.startswith('_'):
                if callable(v) and not isinstance(v, type):
                    continue  # 跳过函数，只显示数据变量
                vars_list.append((k, v))

        if not vars_list:
            print("（无变量）")
            return

        print("╔══════════════════════════════════════════════════════════╗")
        print("║                        当前变量                           ║")
        print("╠══════════════════════════════════════════════════════════╣")
        for name, value in vars_list:
            if isinstance(value, type):
                type_hint = "<类>"
            elif isinstance(value, (list, tuple)):
                type_hint = f"<{type(value).__name__} len={len(value)}>"
            elif isinstance(value, dict):
                type_hint = f"<dict len={len(value)}>"
            elif isinstance(value, str):
                if len(value) > 30:
                    type_hint = "<str>"
                else:
                    type_hint = ""
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
        for i, cmd in enumerate(self.history[-50:], 1):
            if len(cmd) > 50:
                cmd = cmd[:47] + "..."
            print(f"║  {i:3d}: {cmd:<50}║")
        print("╚══════════════════════════════════════════════════════════╝")

    def load_file(self, filepath: str):
        """加载并执行 .duan 文件"""
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
        stripped = line.strip()
        return stripped.endswith('：') or stripped.endswith(':')

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
        output = self._compile_and_run(source)
        return output.rstrip() if output else ""

    def run(self):
        """运行 REPL 主循环"""
        # 尝试使用 prompt_toolkit 以获得更好的交互体验
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.key_binding import KeyBindings

            history_file = os.path.join(os.path.expanduser('~'), '.duan_history')
            kb = KeyBindings()

            session = PromptSession(
                history=FileHistory(history_file),
                auto_suggest=AutoSuggestFromHistory(),
                key_bindings=kb,
                enable_history_search=True,
            )

            print(BANNER)
            while True:
                try:
                    if self.in_block:
                        prompt = "... "
                    else:
                        prompt = ">>> "

                    line = session.prompt(prompt)
                    result = self.process_line(line)

                    if result == 'QUIT':
                        print("再见！")
                        break

                    if result is not None:
                        if result:
                            print(result)

                except KeyboardInterrupt:
                    print()
                    self.statement_buffer = []
                    self.in_block = False
                    continue

                except EOFError:
                    print()
                    print("再见！")
                    break

        except ImportError:
            # 回退到基本 input()
            self._run_basic()

    def _run_basic(self):
        """使用基本 input() 运行 REPL"""
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
                self.statement_buffer = []
                self.in_block = False
                continue

            except EOFError:
                print()
                print("再见！")
                break


def main():
    """REPL v3 入口函数"""
    repl = DuanREPLV3()
    repl.run()


if __name__ == '__main__':
    main()