# -*- coding: utf-8 -*-
"""
光明交互式调试器

提供带调试功能的 REPL，支持断点、单步执行、变量监视等。
"""

import sys
import os
import io
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from compiler import LightCompiler
from code_generator_unified import UnifiedCodeGenerator
from errors import format_exception
from light_debug import LightDebugger, DebuggerContext, create_debugger


BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║         光明（LightLang）交互式调试器 v1.6.0                   ║
╠══════════════════════════════════════════════════════════════════╣
║  输入表达式或语句，按回车执行。                               ║
║  命令: 帮助(help) | 退出(quit) | 变量(vars)                 ║
║  断点: b 行号 | c | n | s | p 变量名                        ║
╚══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║                     光明调试器帮助                            ║
╠══════════════════════════════════════════════════════════════════╣
║  一般命令:                                                    ║
║    帮助 / help     - 显示此帮助信息                           ║
║    退出 / quit     - 退出调试器                               ║
║    运行 / run      - 运行程序                                 ║
║    加载 / load     - 加载并执行文件                           ║
║                                                                    ║
║  断点命令:                                                    ║
║    b <行号>        - 在指定行设置断点                          ║
║    b                - 列出所有断点                             ║
║    d <行号>        - 删除断点                                 ║
║    c                - 继续运行到下一个断点                      ║
║    n                - 单步执行（跳过函数）                     ║
║    s                - 单步执行（进入函数）                     ║
║    r                - 运行到函数返回                           ║
║                                                                    ║
║  调试命令:                                                    ║
║    p <变量>        - 打印变量值                               ║
║    w                - 显示调用栈                               ║
║    l                - 显示当前行附近的代码                      ║
║    vars             - 显示所有局部变量                         ║
║    globals          - 显示所有全局变量                         ║
║                                                                    ║
║  快捷键:                                                      ║
║    Ctrl+C          - 中断执行                                 ║
║    Ctrl+D          - 退出调试器                               ║
╚══════════════════════════════════════════════════════════════════╝
"""


class LightDebugREPL:
    """光明交互式调试器"""
    
    def __init__(self):
        self.compiler = LightCompiler()
        self.codegen = UnifiedCodeGenerator()
        self.globals: Dict[str, Any] = {}
        self.source_lines: List[str] = []
        self.current_line = 0
        self.current_file = '<debug>'
        
        # 调试器
        self.debugger = create_debugger()
        self.debugger.globals = self.globals
        
        # 断点映射（行号 -> 源文本索引）
        self.breakpoint_lines: set = set()
        
        # 运行状态
        self.running = False
        self.paused = False
        
    def set_breakpoint(self, line: int):
        """设置断点"""
        if line < 1 or line > len(self.source_lines):
            print(f"错误: 行号 {line} 超出范围 (1-{len(self.source_lines)})")
            return False
        
        self.breakpoint_lines.add(line)
        self.debugger.set_breakpoint(self.current_file, line)
        print(f"✓ 断点已设置: 第 {line} 行")
        return True
    
    def delete_breakpoint(self, line: int):
        """删除断点"""
        if line in self.breakpoint_lines:
            self.breakpoint_lines.remove(line)
            self.debugger.clear_breakpoint(self.current_file, line)
            print(f"✓ 断点已删除: 第 {line} 行")
        else:
            print(f"错误: 第 {line} 行没有断点")
    
    def list_breakpoints(self):
        """列出所有断点"""
        if not self.breakpoint_lines:
            print("（无断点）")
            return
        
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                        断点列表                           ║")
        print("╠══════════════════════════════════════════════════════════╣")
        for line in sorted(self.breakpoint_lines):
            bp = self.debugger.get_breakpoint(self.current_file, line)
            status = "启用" if bp and bp.enabled else "禁用"
            print(f"║  {line:4d} 行  [{status}]", end="")
            if line <= len(self.source_lines):
                code = self.source_lines[line - 1].strip()
                if len(code) > 30:
                    code = code[:27] + "..."
                print(f"  {code}")
            else:
                print()
        print("╚══════════════════════════════════════════════════════════╝")
    
    def show_source(self, center_line: int = None, context: int = 3):
        """显示源代码"""
        if not self.source_lines:
            print("（无源代码）")
            return
        
        if center_line is None:
            center_line = self.current_line
        
        start = max(1, center_line - context)
        end = min(len(self.source_lines), center_line + context)
        
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                        源代码                            ║")
        print("╠══════════════════════════════════════════════════════════╣")
        
        for i in range(start, end + 1):
            line_content = self.source_lines[i - 1].rstrip()
            prefix = "→" if i == center_line else " "
            bp_marker = "●" if i in self.breakpoint_lines else " "
            print(f"║ {prefix}{bp_marker} {i:4d} │ {line_content}")
        
        print("╚══════════════════════════════════════════════════════════╝")
    
    def show_stack(self):
        """显示调用栈"""
        print(self.debugger.format_stack_trace())
    
    def show_variables(self, frame=None):
        """显示变量"""
        print(self.debugger.format_variables(frame))
    
    def print_variable(self, name: str):
        """打印变量值"""
        # 先查找局部变量
        value = None
        
        # 从调用栈中查找
        for frame in self.debugger.call_stack:
            if name in frame.locals:
                value = frame.locals[name]
                break
        
        # 再查找全局变量
        if value is None and name in self.globals:
            value = self.globals[name]
        
        if value is not None:
            print(f"{name} = {self.debugger._format_value(value)}")
        else:
            print(f"错误: 变量 '{name}' 未定义")
    
    def compile_source(self, source: str) -> Optional[str]:
        """编译源代码"""
        self.source_lines = source.split('\n')
        
        try:
            result = self.compiler.compile(source)
            if result['errors']:
                for error in result['errors']:
                    print(f"编译错误: {error}")
                return None
            
            ast = result['ast']
            return self.codegen.generate(ast)
        except Exception as e:
            print(format_exception(type(e), e, e.__traceback__))
            return None
    
    def run_with_debug(self, python_code: str):
        """在调试模式下运行代码"""
        self.running = True
        self.debugger.start()
        
        # 设置源代码用于显示
        if self.source_lines:
            self.show_source(self.current_line)
        
        try:
            with DebuggerContext(self.debugger) as ctx:
                ctx.globals = self.globals
                
                # 创建局部命名空间
                namespace = {'__builtins__': __builtins__}
                namespace.update(self.globals)
                
                # 执行代码
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    exec(compile(python_code, self.current_file, 'exec'), namespace)
                    output = sys.stdout.getvalue()
                    if output:
                        print(output.rstrip())
                except KeyboardInterrupt:
                    print("\n（用户中断）")
                except Exception as e:
                    print(format_exception(type(e), e, e.__traceback__))
                finally:
                    sys.stdout = old_stdout
                    # 更新全局变量
                    for k, v in namespace.items():
                        if not k.startswith('__'):
                            self.globals[k] = v
        finally:
            self.running = False
    
    def step_over(self):
        """单步跳过"""
        self.debugger.set_step(LightDebugger.STEP_OVER)
        self.debugger.start()
    
    def step_into(self):
        """单步进入"""
        self.debugger.set_step(LightDebugger.STEP_INTO)
        self.debugger.start()
    
    def step_out(self):
        """单步跳出"""
        self.debugger.set_step(LightDebugger.STEP_OUT)
        self.debugger.start()
    
    def continue_run(self):
        """继续运行"""
        self.debugger.step_mode = LightDebugger.STEP_NONE
        self.debugger.start()
    
    def load_file(self, filepath: str):
        """加载文件"""
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在: {filepath}")
            return False
        
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        self.current_file = filepath
        self.source_lines = source.split('\n')
        
        # 编译
        python_code = self.compile_source(source)
        if python_code:
            print(f"✓ 已加载: {filepath}")
            self.run_with_debug(python_code)
            return True
        
        return False
    
    def run(self):
        """运行 REPL 主循环"""
        print(BANNER)
        
        buffer = []
        in_multiline = False
        
        while True:
            try:
                prompt = "... " if in_multiline else "(调试)>>> "
                line = input(prompt)
                
                stripped = line.strip()
                
                # 空行处理
                if not stripped:
                    if in_multiline and buffer:
                        # 执行累积的代码
                        source = '\n'.join(buffer)
                        python_code = self.compile_source(source)
                        if python_code:
                            self.run_with_debug(python_code)
                        buffer = []
                        in_multiline = False
                    continue
                
                # 调试命令
                if stripped.startswith('b '):
                    # 设置断点
                    try:
                        line_num = int(stripped[2:])
                        self.set_breakpoint(line_num)
                    except ValueError:
                        print("用法: b <行号>")
                    continue
                
                if stripped == 'b':
                    # 列出断点
                    self.list_breakpoints()
                    continue
                
                if stripped.startswith('d '):
                    # 删除断点
                    try:
                        line_num = int(stripped[2:])
                        self.delete_breakpoint(line_num)
                    except ValueError:
                        print("用法: d <行号>")
                    continue
                
                if stripped in ('c', 'cont', 'continue'):
                    # 继续运行
                    self.continue_run()
                    print("（继续执行）")
                    continue
                
                if stripped in ('n', 'next'):
                    # 单步跳过
                    self.step_over()
                    print("（单步跳过）")
                    continue
                
                if stripped in ('s', 'step'):
                    # 单步进入
                    self.step_into()
                    print("（单步进入）")
                    continue
                
                if stripped in ('r', 'return'):
                    # 单步返回
                    self.step_out()
                    print("（单步返回）")
                    continue
                
                if stripped.startswith('p '):
                    # 打印变量
                    var_name = stripped[2:].strip()
                    self.print_variable(var_name)
                    continue
                
                if stripped == 'w':
                    # 显示调用栈
                    self.show_stack()
                    continue
                
                if stripped == 'l':
                    # 显示当前行附近的代码
                    self.show_source()
                    continue
                
                if stripped in ('vars', 'variables'):
                    # 显示变量
                    self.show_variables()
                    continue
                
                if stripped in ('globals', 'g'):
                    # 显示全局变量
                    print("全局变量:")
                    for name, value in sorted(self.globals.items()):
                        if not name.startswith('_'):
                            print(f"  {name} = {self.debugger._format_value(value)}")
                    continue
                
                # 一般命令
                if stripped in ('帮助', 'help', '?'):
                    print(HELP_TEXT)
                    continue
                
                if stripped in ('退出', 'quit', 'exit', 'q'):
                    print("再见！")
                    break
                
                if stripped.startswith('加载 ') or stripped.startswith('load '):
                    parts = stripped.split(None, 1)
                    if len(parts) == 2:
                        filepath = parts[1].strip().strip('"').strip("'")
                        self.load_file(filepath)
                    else:
                        print("用法: 加载 <文件名>")
                    continue
                
                if stripped == '清除':
                    self.globals = {}
                    print("✓ 已清除所有变量")
                    continue
                
                # 作为代码执行
                buffer.append(line)
                
                # 检查是否需要更多输入
                source_so_far = '\n'.join(buffer)
                if source_so_far.count(':') > source_so_far.count('结束') or \
                   source_so_far.endswith('：') or \
                   source_so_far.endswith('('):
                    in_multiline = True
                    continue
                
                # 执行代码
                python_code = self.compile_source(source_so_far)
                if python_code:
                    self.run_with_debug(python_code)
                buffer = []
                in_multiline = False
                
            except KeyboardInterrupt:
                print()
                print("（按 Ctrl+D 或输入 '退出' 退出）")
                buffer = []
                in_multiline = False
                continue
                
            except EOFError:
                print()
                print("再见！")
                break


def main():
    """入口函数"""
    repl = LightDebugREPL()
    repl.run()


if __name__ == '__main__':
    main()
