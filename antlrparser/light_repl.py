#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - REPL 交互式开发环境

提供交互式的光明代码执行环境，支持：
- 逐行输入代码并立即执行
- 命令历史记录
- 多行代码输入
- 自动补全（可选）
- 退出命令
"""

import sys
import os
import io
import readline

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source
from light_interpreter import Interpreter, LightValue

class LightREPL:
    """光明 REPL 类"""
    
    def __init__(self):
        self.interpreter = None
        self.history = []
        self.multiline_buffer = []
        self.prompt = "光明> "
        self.multiline_prompt = "...   "
        self.init_interpreter()
        
        # 设置命令历史
        self.setup_readline()
    
    def init_interpreter(self):
        """初始化解释器"""
        self.interpreter = Interpreter()
    
    def setup_readline(self):
        """设置命令行历史和自动补全"""
        # 历史文件
        history_file = os.path.expanduser("~/.light_repl_history")
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        # 设置历史长度
        readline.set_history_length(1000)
        
        # 保存历史的钩子
        import atexit
        atexit.register(lambda: readline.write_history_file(history_file))
        
        # 自动补全
        readline.parse_and_bind('tab: complete')
    
    def run(self):
        """启动REPL主循环"""
        self.print_banner()
        
        while True:
            try:
                # 读取用户输入
                if self.multiline_buffer:
                    line = self.read_input(self.multiline_prompt)
                else:
                    line = self.read_input(self.prompt)
                
                if line is None:
                    break
                
                # 处理命令
                if self.handle_command(line):
                    continue
                
                # 处理多行输入
                if self.handle_multiline(line):
                    continue
                
                # 执行单行代码
                self.execute_line(line)
                
            except EOFError:
                print("\n再见！")
                break
            except KeyboardInterrupt:
                print("\n^C")
                self.multiline_buffer = []
            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()
    
    def read_input(self, prompt):
        """读取用户输入"""
        try:
            return input(prompt)
        except EOFError:
            return None
    
    def print_banner(self):
        """打印欢迎信息"""
        banner = """
╔══════════════════════════════════════════════╗
║           光明 (LightLang) REPL              ║
║           版本: 1.0.0                        ║
║                                              ║
║  输入光明代码，按 Enter 执行                  ║
║  输入 '退出' 或按 Ctrl+D 退出                ║
║  输入 '帮助' 获取帮助信息                    ║
║  多行代码以 '结束。' 结尾                     ║
╚══════════════════════════════════════════════╝
"""
        print(banner)
    
    def handle_command(self, line):
        """处理特殊命令"""
        line = line.strip()
        
        if line == '退出' or line == 'quit' or line == 'exit':
            print("再见！")
            sys.exit(0)
        
        if line == '帮助' or line == 'help':
            self.print_help()
            return True
        
        if line == '清除' or line == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_banner()
            return True
        
        if line == '重置' or line == 'reset':
            self.init_interpreter()
            print("解释器已重置")
            return True
        
        if line == '变量' or line == 'vars':
            self.print_variables()
            return True
        
        return False
    
    def print_help(self):
        """打印帮助信息"""
        help_text = """
光明 REPL 命令:

  退出 / quit / exit   - 退出 REPL
  帮助 / help          - 显示此帮助信息
  清除 / clear         - 清屏
  重置 / reset         - 重置解释器状态
  变量 / vars          - 显示当前变量列表

语法示例:

  变量定义:
    定义 x 等于 42。
    定义 问候语 等于 "你好"。

  算术运算:
    定义 y 等于 10 加 5。
    定义 z 等于 2 幂 10。

  条件语句:
    如果 x 大于 10 那么: 打印("大")。结束。

  段落定义:
    《加》段(a, b): 返回 a 加 b。结束。

  类定义:
    《人》类: 定义 姓名 等于 ""。结束。

  实例化:
    定义 p 等于 新 人()。

  方法调用:
    p之说话()。
"""
        print(help_text)
    
    def print_variables(self):
        """打印当前变量列表"""
        if not hasattr(self.interpreter, 'env'):
            print("无变量")
            return
        
        env = self.interpreter.env
        variables = []
        
        while env:
            variables.extend(env.variables.keys())
            env = env.parent
        
        if not variables:
            print("无变量")
            return
        
        print("当前变量:")
        for var in sorted(variables):
            try:
                val = self.interpreter.env.get(var)
                print(f"  {var} = {self.format_value(val)}")
            except Exception:
                print(f"  {var} = <无法获取>")
    
    def format_value(self, val):
        """格式化值用于显示"""
        if val is None:
            return "空"
        if isinstance(val, LightValue):
            if val.type_name == '串':
                return f'"{val.value}"'
            elif val.type_name == '布尔':
                return '真' if val.value else '假'
            elif val.type_name == '实例':
                return f"<实例: {val.value.__class__.__name__}>"
            else:
                return str(val.value)
        return str(val)
    
    def handle_multiline(self, line):
        """处理多行输入"""
        line_stripped = line.strip()
        
        # 如果是空行且没有缓冲区，跳过
        if not line_stripped and not self.multiline_buffer:
            return True
        
        # 添加到缓冲区
        self.multiline_buffer.append(line)
        
        # 检查是否结束
        if line_stripped.endswith('。') or line_stripped.endswith('结束'):
            # 执行多行代码
            code = '\n'.join(self.multiline_buffer)
            self.execute_multiline(code)
            self.multiline_buffer = []
            return True
        
        return True  # 继续收集
    
    def execute_line(self, line):
        """执行单行代码"""
        line = line.strip()
        if not line:
            return
        
        # 添加到历史
        self.history.append(line)
        
        try:
            # 解析并执行
            module = parse_source(line)
            if module is None:
                print("[语法错误] 解析失败")
                return
            
            # 执行
            self.interpreter.interpret_module(module)
            
            # 检查是否有返回值（对于表达式）
            # REPL通常会打印最后一个表达式的值
            
        except Exception as e:
            print(f"执行错误: {e}")
    
    def execute_multiline(self, code):
        """执行多行代码"""
        print(f"\n执行代码:\n{code}\n")
        
        try:
            module = parse_source(code)
            if module is None:
                print("[语法错误] 解析失败")
                return
            
            self.interpreter.interpret_module(module)
            print("执行完成")
            
        except Exception as e:
            print(f"执行错误: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主入口"""
    repl = LightREPL()
    repl.run()

if __name__ == "__main__":
    main()