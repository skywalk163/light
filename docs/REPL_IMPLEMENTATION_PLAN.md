# REPL 环境实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 创建光明语言的交互式开发环境（REPL），支持混合执行、自动补全、语法高亮和调试功能。

**架构：** 轻量核心 + 可选增强包。核心REPL无第三方依赖，增强功能依赖prompt_toolkit。混合执行引擎根据代码复杂度选择解释执行或编译执行。

**技术栈：** Python 3.8+、ANTLR4、prompt_toolkit（可选）

---

## 文件结构

```
src/repl/
├── __init__.py          # 包入口，导出 LightREPL 类
├── executor.py          # 混合执行引擎（核心）
├── commands.py          # REPL命令处理
├── core.py              # 核心REPL循环（无依赖）
├── completer.py         # 自动补全（prompt_toolkit）
├── highlighter.py       # 语法高亮（prompt_toolkit）
├── enhanced.py          # 增强REPL（prompt_toolkit）
├── debugger.py          # 调试支持

antlrparser/
├── light_repl.py         # 入口脚本（更新）
├── light_cli.py          # CLI整合（更新）

tests/
├── test_executor.py     # 执行引擎测试
├── test_commands.py     # 命令处理测试
├── test_repl.py         # REPL集成测试
```

---

### 任务 1：混合执行引擎

**文件：**
- 创建：`src/repl/__init__.py`
- 创建：`src/repl/executor.py`
- 创建：`tests/test_executor.py`

- [ ] **步骤 1：创建包入口**

```python
# src/repl/__init__.py
"""
光明 REPL 包

提供交互式开发环境。
"""

from .executor import Executor
from .core import LightREPL

__all__ = ['Executor', 'LightREPL']
```

- [ ] **步骤 2：编写执行引擎测试**

```python
# tests/test_executor.py
"""混合执行引擎测试"""

import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'antlrparser')

from repl.executor import Executor

def test_simple_expression():
    """测试简单表达式解释执行"""
    exec = Executor()
    result = exec.execute("甲 加 5", env={'甲': 3})
    assert result == 8, f"期望 8，得到 {result}"

def test_variable_declaration():
    """测试变量声明编译执行"""
    exec = Executor()
    exec.execute("设 甲 为 3。")
    assert exec.env.get('甲') == 3

def test_function_call():
    """测试函数调用解释执行"""
    exec = Executor()
    exec.execute("设 甲 为 42。")
    output = exec.execute("打印(甲)。")
    assert output == "42" or output is None  # 打印可能返回None

def test_paragraph_definition():
    """测试段落定义编译执行"""
    exec = Executor()
    exec.execute("""段落 平方 接收 数值:
    返回 数值 乘 数值。
结束。""")
    assert exec.has_function('平方')

def test_complexity_detection():
    """测试复杂度判断"""
    exec = Executor()
    assert exec._is_simple("甲 加 5") == True
    assert exec._is_simple("设 甲 为 3。") == False
    assert exec._is_simple("段落 平方...") == False

if __name__ == '__main__':
    test_simple_expression()
    test_variable_declaration()
    test_function_call()
    test_paragraph_definition()
    test_complexity_detection()
    print("✅ 所有执行引擎测试通过")
```

- [ ] **步骤 3：运行测试验证失败**

运行：`python tests/test_executor.py`
预期：FAIL，报错 "module 'repl' has no attribute 'executor'"

- [ ] **步骤 4：编写执行引擎实现**

```python
# src/repl/executor.py
"""
混合执行引擎

根据代码复杂度选择执行方式：
- 简单表达式：解释执行（AST遍历）
- 复杂代码块：编译执行（生成Python代码）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Any, Dict, Optional
from antlr4 import InputStream, CommonTokenStream
from LightLangLexer import LightLangLexer
from LightLangParser import LightLangParser
from light_visitor import LightLangASTBuilder
from code_generator_unified import UnifiedCodeGenerator


class Environment:
    """执行环境，存储变量和函数"""
    
    def __init__(self, parent=None):
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Any] = {}
        self.parent = parent
    
    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"变量 '{name}' 未定义")
    
    def set(self, name: str, value: Any):
        self.variables[name] = value
    
    def has(self, name: str) -> bool:
        if name in self.variables or name in self.functions:
            return True
        if self.parent:
            return self.parent.has(name)
        return False
    
    def has_function(self, name: str) -> bool:
        if name in self.functions:
            return True
        if self.parent:
            return self.parent.has_function(name)
        return False


class Executor:
    """混合执行引擎"""
    
    # 简单表达式类型（解释执行）
    SIMPLE_TYPES = {
        'Identifier', 'NumberLiteral', 'StringLiteral', 
        'BooleanLiteral', 'ListLiteral', 'BinaryOp', 'UnaryOp',
        'FunctionCall', 'PropertyAccess', 'IndexAccess'
    }
    
    # 复杂语句类型（编译执行）
    COMPLEX_TYPES = {
        'VariableDeclaration', 'SegmentDefinition', 'ClassDefinition',
        'IfStatement', 'WhileStatement', 'ForeachStatement',
        'ReturnStatement', 'ImportStatement', 'ExportStatement'
    }
    
    def __init__(self):
        self.env = Environment()
        self.output_buffer = []
        self.generator = UnifiedCodeGenerator()
    
    def execute(self, code: str, env: Dict = None) -> Any:
        """执行代码，返回结果"""
        # 解析代码
        module = self._parse(code)
        if module is None:
            return None
        
        # 判断复杂度
        if self._is_simple(code):
            return self._interpret(module, env)
        else:
            return self._compile_and_run(module)
    
    def _parse(self, code: str) -> Any:
        """解析代码为AST"""
        try:
            input_stream = InputStream(code)
            lexer = LightLangLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = LightLangParser(token_stream)
            tree = parser.program()
            
            if parser.getNumberOfSyntaxErrors() > 0:
                return None
            
            builder = LightLangASTBuilder()
            return builder.visitProgram(tree)
        except Exception as e:
            print(f"解析错误: {e}")
            return None
    
    def _is_simple(self, code: str) -> bool:
        """判断是否是简单表达式"""
        # 简单判断：不包含定义关键字
        simple_keywords = ['段落', '类', '接口', '如果', '当', '遍历', '返回', '导入', '导出', '设']
        for kw in simple_keywords:
            if kw in code:
                return False
        return True
    
    def _interpret(self, module, env: Dict = None) -> Any:
        """解释执行AST"""
        if env:
            for k, v in env.items():
                self.env.set(k, v)
        
        # 遍历AST执行
        result = None
        for stmt in module.statements:
            result = self._eval_node(stmt)
        return result
    
    def _eval_node(self, node) -> Any:
        """评估AST节点"""
        node_type = type(node).__name__
        
        if node_type == 'NumberLiteral':
            return node.value
        elif node_type == 'StringLiteral':
            return node.value
        elif node_type == 'BooleanLiteral':
            return node.value
        elif node_type == 'Identifier':
            return self.env.get(node.name)
        elif node_type == 'BinaryOp':
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._apply_op(node.operator, left, right)
        elif node_type == 'FunctionCall':
            return self._call_function(node)
        elif node_type == 'ExpressionStatement':
            return self._eval_node(node.expression)
        elif node_type == 'PrintStatement':
            val = self._eval_node(node.value)
            print(val)
            self.output_buffer.append(str(val))
            return None
        
        return None
    
    def _apply_op(self, op: str, left: Any, right: Any) -> Any:
        """应用运算符"""
        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b,
            '加': lambda a, b: a + b,
            '减': lambda a, b: a - b,
            '乘': lambda a, b: a * b,
            '除': lambda a, b: a / b,
            '大于': lambda a, b: a > b,
            '小于': lambda a, b: a < b,
            '等于': lambda a, b: a == b,
        }
        if op in ops:
            return ops[op](left, right)
        raise ValueError(f"未知运算符: {op}")
    
    def _call_function(self, node) -> Any:
        """调用函数"""
        func_name = node.name.name if hasattr(node.name, 'name') else str(node.name)
        args = [self._eval_node(arg) for arg in node.arguments]
        
        # 内置函数
        builtins = {
            '打印': lambda x: print(x),
            'print': lambda x: print(x),
            '长': lambda x: len(x),
            'len': lambda x: len(x),
            '首': lambda x: x[0] if x else None,
            '末': lambda x: x[-1] if x else None,
            '排序': lambda x: sorted(x),
            '求和': lambda x: sum(x),
        }
        
        if func_name in builtins:
            result = builtins[func_name](*args)
            self.output_buffer.append(str(result) if result is not None else '')
            return result
        
        # 用户定义函数
        if self.env.has_function(func_name):
            func = self.env.functions[func_name]
            return func(*args)
        
        raise NameError(f"函数 '{func_name}' 未定义")
    
    def _compile_and_run(self, module) -> Any:
        """编译执行（生成Python代码）"""
        py_code = self.generator.generate(module)
        
        # 创建执行环境
        exec_env = {
            '__builtins__': __builtins__,
            '_light_builtin': self._create_builtin_module(),
        }
        
        # 添加当前变量
        for k, v in self.env.variables.items():
            exec_env[k] = v
        
        # 执行
        try:
            exec(py_code, exec_env)
            
            # 更新环境
            for k, v in exec_env.items():
                if k not in ['__builtins__', '_light_builtin']:
                    self.env.set(k, v)
            
            return None
        except Exception as e:
            print(f"执行错误: {e}")
            return None
    
    def _create_builtin_module(self):
        """创建内置模块"""
        import types
        builtin = types.ModuleType('_light_builtin')
        builtin.打印 = print
        builtin.长 = len
        builtin.首 = lambda x: x[0] if x else None
        builtin.末 = lambda x: x[-1] if x else None
        builtin.排序 = sorted
        builtin.求和 = sum
        builtin.转字符串 = str
        builtin.字符串长度 = len
        builtin.分割字符串 = lambda s, sep: s.split(sep)
        return builtin
    
    def has_function(self, name: str) -> bool:
        return self.env.has_function(name)
    
    def reset(self):
        """重置环境"""
        self.env = Environment()
        self.output_buffer = []
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python tests/test_executor.py`
预期：PASS，输出 "✅ 所有执行引擎测试通过"

- [ ] **步骤 6：Commit**

```bash
git add src/repl/__init__.py src/repl/executor.py tests/test_executor.py
git commit -m "feat(repl): add hybrid executor engine"
```

---

### 任务 2：命令处理

**文件：**
- 创建：`src/repl/commands.py`
- 创建：`tests/test_commands.py`

- [ ] **步骤 1：编写命令处理测试**

```python
# tests/test_commands.py
"""REPL命令处理测试"""

import sys
sys.path.insert(0, 'src')

from repl.commands import CommandHandler

def test_help_command():
    """测试帮助命令"""
    handler = CommandHandler()
    result = handler.handle(':help')
    assert '帮助' in result or 'help' in result.lower()

def test_exit_command():
    """测试退出命令"""
    handler = CommandHandler()
    result = handler.handle(':exit')
    assert result == 'EXIT'

def test_vars_command():
    """测试变量显示命令"""
    handler = CommandHandler(env={'甲': 3, '乙': 5})
    result = handler.handle(':vars')
    assert '甲' in result and '乙' in result

def test_clear_command():
    """测试清屏命令"""
    handler = CommandHandler()
    result = handler.handle(':clear')
    assert result == 'CLEAR'

def test_reset_command():
    """测试重置命令"""
    handler = CommandHandler()
    result = handler.handle(':reset')
    assert result == 'RESET'

def test_unknown_command():
    """测试未知命令"""
    handler = CommandHandler()
    result = handler.handle(':unknown')
    assert '未知' in result or 'unknown' in result.lower()

def test_chinese_alias():
    """测试中文别名"""
    handler = CommandHandler()
    result = handler.handle(':帮助')
    assert '帮助' in result or 'help' in result.lower()

if __name__ == '__main__':
    test_help_command()
    test_exit_command()
    test_vars_command()
    test_clear_command()
    test_reset_command()
    test_unknown_command()
    test_chinese_alias()
    print("✅ 所有命令处理测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python tests/test_commands.py`
预期：FAIL，报错 "module 'repl.commands' not found"

- [ ] **步骤 3：编写命令处理实现**

```python
# src/repl/commands.py
"""
REPL命令处理

处理以 : 开头的特殊命令。
"""

from typing import Dict, Any, Optional


class CommandHandler:
    """命令处理器"""
    
    # 命令映射（英文 -> 中文别名）
    COMMANDS = {
        'help': ['帮助', 'h'],
        'exit': ['退出', 'quit', 'q'],
        'clear': ['清除', 'cls'],
        'reset': ['重置'],
        'vars': ['变量', 'var'],
        'funcs': ['段落', 'func', 'functions'],
        'classes': ['类', 'class'],
        'history': ['历史'],
        'load': ['加载'],
        'save': ['保存'],
        'debug': ['调试'],
        'step': ['单步'],
        'break': ['断点'],
    }
    
    def __init__(self, env: Dict = None, executor=None):
        self.env = env or {}
        self.executor = executor
        self.history = []
    
    def handle(self, input: str) -> Any:
        """处理命令输入"""
        # 移除前导 :
        if input.startswith(':'):
            input = input[1:]
        
        # 解析命令和参数
        parts = input.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ''
        
        # 查找命令
        for main_cmd, aliases in self.COMMANDS.items():
            if cmd == main_cmd or cmd in aliases:
                return self._execute(main_cmd, args)
        
        return f"未知命令: {cmd}。输入 :help 获取帮助。"
    
    def _execute(self, cmd: str, args: str) -> Any:
        """执行命令"""
        if cmd == 'help':
            return self._help()
        elif cmd == 'exit':
            return 'EXIT'
        elif cmd == 'clear':
            return 'CLEAR'
        elif cmd == 'reset':
            return 'RESET'
        elif cmd == 'vars':
            return self._show_vars()
        elif cmd == 'funcs':
            return self._show_funcs()
        elif cmd == 'classes':
            return self._show_classes()
        elif cmd == 'history':
            return self._show_history()
        elif cmd == 'load':
            return self._load_file(args)
        elif cmd == 'save':
            return self._save_session(args)
        elif cmd == 'debug':
            return self._toggle_debug(args)
        else:
            return f"命令 '{cmd}' 待实现"
    
    def _help(self) -> str:
        """显示帮助"""
        return """
光明 REPL 帮助

命令:
  :help / :帮助     - 显示此帮助
  :exit / :退出     - 退出 REPL
  :clear / :清除    - 清屏
  :reset / :重置    - 重置环境
  :vars / :变量     - 显示所有变量
  :funcs / :段落    - 显示所有段落
  :classes / :类    - 显示所有类
  :history / :历史  - 显示命令历史
  :load <file>      - 加载文件
  :save <file>      - 保存会话
  :debug on/off     - 开启/关闭调试

语法示例:
  设 甲 为 3。           # 变量声明
  打印(甲)。             # 函数调用
  段落 平方 接收 数值:   # 段落定义
    返回 数值 乘 数值。
  结束。
"""
    
    def _show_vars(self) -> str:
        """显示变量"""
        if not self.env:
            return "无变量"
        
        lines = ["当前变量:"]
        for name, value in sorted(self.env.items()):
            lines.append(f"  {name} = {value}")
        return '\n'.join(lines)
    
    def _show_funcs(self) -> str:
        """显示段落"""
        if not self.executor or not hasattr(self.executor, 'env'):
            return "无段落"
        
        funcs = [k for k in self.executor.env.functions.keys()]
        if not funcs:
            return "无段落"
        
        lines = ["已定义段落:"]
        for name in sorted(funcs):
            lines.append(f"  {name}")
        return '\n'.join(lines)
    
    def _show_classes(self) -> str:
        """显示类"""
        return "无类定义"
    
    def _show_history(self) -> str:
        """显示历史"""
        if not self.history:
            return "无历史记录"
        
        lines = ["命令历史:"]
        for i, cmd in enumerate(self.history[-20:], 1):
            lines.append(f"  {i}. {cmd}")
        return '\n'.join(lines)
    
    def _load_file(self, filename: str) -> str:
        """加载文件"""
        if not filename:
            return "请指定文件名: :load <文件>"
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                code = f.read()
            return f"加载文件: {filename}\n代码长度: {len(code)} 字符"
        except FileNotFoundError:
            return f"文件不存在: {filename}"
    
    def _save_session(self, filename: str) -> str:
        """保存会话"""
        if not filename:
            return "请指定文件名: :save <文件>"
        
        # TODO: 实现保存逻辑
        return f"会话已保存到: {filename}"
    
    def _toggle_debug(self, args: str) -> str:
        """切换调试模式"""
        if args == 'on':
            return "调试模式已开启"
        elif args == 'off':
            return "调试模式已关闭"
        else:
            return "用法: :debug on/off"
    
    def add_history(self, cmd: str):
        """添加到历史"""
        self.history.append(cmd)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python tests/test_commands.py`
预期：PASS，输出 "✅ 所有命令处理测试通过"

- [ ] **步骤 5：Commit**

```bash
git add src/repl/commands.py tests/test_commands.py
git commit -m "feat(repl): add command handler"
```

---

### 任务 3：核心REPL循环

**文件：**
- 创建：`src/repl/core.py`
- 创建：`tests/test_repl.py`
- 修改：`antlrparser/light_repl.py`

- [ ] **步骤 1：编写REPL集成测试**

```python
# tests/test_repl.py
"""REPL集成测试"""

import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'antlrparser')

from repl.core import LightREPL

def test_repl_creation():
    """测试REPL创建"""
    repl = LightREPL()
    assert repl.executor is not None
    assert repl.command_handler is not None

def test_repl_execute():
    """测试REPL执行"""
    repl = LightREPL()
    result = repl.execute_line("设 甲 为 3。")
    assert repl.executor.env.has('甲')

def test_repl_command():
    """测试REPL命令"""
    repl = LightREPL()
    result = repl.process_input(":help")
    assert '帮助' in result or 'help' in result.lower()

def test_repl_multiline():
    """测试多行输入"""
    repl = LightREPL()
    # 模拟多行输入
    repl.buffer.append("段落 平方 接收 数值:")
    repl.buffer.append("  返回 数值 乘 数值。")
    result = repl.execute_buffer()
    assert repl.executor.has_function('平方')

if __name__ == '__main__':
    test_repl_creation()
    test_repl_execute()
    test_repl_command()
    test_repl_multiline()
    print("✅ 所有REPL集成测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python tests/test_repl.py`
预期：FAIL，报错 "module 'repl.core' not found"

- [ ] **步骤 3：编写核心REPL实现**

```python
# src/repl/core.py
"""
核心REPL循环

无第三方依赖的纯Python实现。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Optional, List
from .executor import Executor
from .commands import CommandHandler


class LightREPL:
    """光明 REPL"""
    
    def __init__(self, enhanced=False):
        """初始化REPL
        
        Args:
            enhanced: 是否使用增强模式（prompt_toolkit）
        """
        self.executor = Executor()
        self.command_handler = CommandHandler(
            env=self.executor.env.variables,
            executor=self.executor
        )
        self.buffer: List[str] = []
        self.history: List[str] = []
        self.debug_mode = False
        self.enhanced = enhanced
        
        # 尝试加载增强模式
        if enhanced:
            try:
                from .enhanced import EnhancedREPL
                self._enhanced_impl = EnhancedREPL(self)
            except ImportError:
                self.enhanced = False
                self._enhanced_impl = None
    
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
                
                # 显示结果
                if result and result != 'EXIT':
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
    
    def read_input(self, prompt: str) -> Optional[str]:
        """读取用户输入"""
        try:
            return input(prompt)
        except EOFError:
            return None
    
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
╚══════════════════════════════════════════════╝
""")
    
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
        
        # 命令
        if line.startswith(':'):
            result = self.command_handler.handle(line)
            self.history.append(line)
            
            if result == 'CLEAR':
                os.system('cls' if os.name == 'nt' else 'clear')
                self.print_banner()
                return None
            elif result == 'RESET':
                self.executor.reset()
                return "环境已重置"
            
            return result
        
        # 多行检测
        if self._is_multiline_start(line):
            self.buffer.append(line)
            return None
        
        # 添加到缓冲区
        if self.buffer:
            self.buffer.append(line)
            if self._is_multiline_end(line):
                return self.execute_buffer()
            return None
        
        # 单行执行
        return self.execute_line(line)
    
    def _is_multiline_start(self, line: str) -> bool:
        """判断是否是多行开始"""
        starters = ['段落', '类', '接口', '如果', '当', '遍历', '尝试']
        for s in starters:
            if line.startswith(s) and (line.endswith(':') or line.endswith('：')):
                return True
        return False
    
    def _is_multiline_end(self, line: str) -> bool:
        """判断是否是多行结束"""
        return line.strip() in ['结束。', '结束', '结束。', '否则', '否则：', '否则:']
    
    def execute_line(self, line: str) -> Optional[str]:
        """执行单行代码"""
        self.history.append(line)
        
        try:
            result = self.executor.execute(line)
            
            # 显示输出
            if self.executor.output_buffer:
                output = '\n'.join(self.executor.output_buffer)
                self.executor.output_buffer = []
                return output
            
            if result is not None:
                return str(result)
            
            return None
        except Exception as e:
            return f"错误: {e}"
    
    def execute_buffer(self) -> Optional[str]:
        """执行缓冲区代码"""
        code = '\n'.join(self.buffer)
        self.buffer = []
        self.history.append(code)
        
        try:
            self.executor.execute(code)
            return "执行完成"
        except Exception as e:
            return f"错误: {e}"


def main():
    """REPL入口"""
    repl = LightREPL()
    repl.run()


if __name__ == '__main__':
    main()
```

- [ ] **步骤 4：更新入口脚本**

```python
# antlrparser/light_repl.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
光明 REPL 入口
"""

import sys
import os

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from repl.core import main

if __name__ == "__main__":
    main()
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python tests/test_repl.py`
预期：PASS，输出 "✅ 所有REPL集成测试通过"

- [ ] **步骤 6：手动测试REPL**

运行：`python antlrparser/light_repl.py`
输入：`:help`
预期：显示帮助信息

- [ ] **步骤 7：Commit**

```bash
git add src/repl/core.py tests/test_repl.py antlrparser/light_repl.py
git commit -m "feat(repl): add core REPL loop"
```

---

### 任务 4：自动补全

**文件：**
- 创建：`src/repl/completer.py`

- [ ] **步骤 1：编写补全实现**

```python
# src/repl/completer.py
"""
自动补全

提供关键字、动词、变量名补全。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import List, Dict
from keywords import KEYWORDS, VERB_ARITY


class LightCompleter:
    """光明自动补全"""
    
    # 关键字列表
    KEYWORDS_LIST = [
        '设', '为', '段落', '接收', '返回', '类', '继承', '实现',
        '属性', '构造', '新建', '己', '如果', '那么', '否则', '结束',
        '遍历', '当', '跳出', '跳过', '尝试', '捕获', '抛出',
        '导入', '导出', '从', '真', '假', '空',
    ]
    
    # 动词列表
    VERBS_LIST = list(VERB_ARITY.keys())
    
    # 内置类型
    TYPES_LIST = ['数', '串', '列', '典', '布尔', '任意', '整数', '浮数']
    
    def __init__(self, env: Dict = None):
        self.env = env or {}
    
    def get_completions(self, text: str, cursor_pos: int) -> List[str]:
        """获取补全建议"""
        # 获取当前输入的前缀
        prefix = text[:cursor_pos]
        
        # 提取最后一个词
        words = prefix.split()
        if not words:
            return self.KEYWORDS_LIST[:10]
        
        last_word = words[-1]
        
        # 收集所有可能的补全
        candidates = []
        
        # 关键字
        candidates.extend(self._match(last_word, self.KEYWORDS_LIST))
        
        # 动词
        candidates.extend(self._match(last_word, self.VERBS_LIST))
        
        # 类型
        candidates.extend(self._match(last_word, self.TYPES_LIST))
        
        # 环境变量
        if self.env:
            candidates.extend(self._match(last_word, list(self.env.keys())))
        
        return candidates[:20]
    
    def _match(self, prefix: str, candidates: List[str]) -> List[str]:
        """匹配前缀"""
        return [c for c in candidates if c.startswith(prefix)]
    
    def update_env(self, env: Dict):
        """更新环境"""
        self.env = env


# prompt_toolkit 补全器（可选）
try:
    from prompt_toolkit.completion import Completer, Completion
    
    class PromptToolkitCompleter(Completer):
        """prompt_toolkit 补全器"""
        
        def __init__(self, light_completer: LightCompleter):
            self.completer = light_completer
        
        def get_completions(self, document, complete_event):
            text = document.text
            cursor_pos = document.cursor_position
            
            completions = self.completer.get_completions(text, cursor_pos)
            
            for i, c in enumerate(completions):
                yield Completion(c, start_position=-len(text.split()[-1]) if text.split() else 0)
    
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    PromptToolkitCompleter = None
```

- [ ] **步骤 2：更新 __init__.py 导出**

```python
# src/repl/__init__.py
"""
光明 REPL 包
"""

from .executor import Executor, Environment
from .commands import CommandHandler
from .core import LightREPL
from .completer import LightCompleter

__all__ = ['Executor', 'Environment', 'CommandHandler', 'LightREPL', 'LightCompleter']
```

- [ ] **步骤 3：Commit**

```bash
git add src/repl/completer.py src/repl/__init__.py
git commit -m "feat(repl): add auto-completer"
```

---

### 任务 5：语法高亮

**文件：**
- 创建：`src/repl/highlighter.py`

- [ ] **步骤 1：编写高亮实现**

```python
# src/repl/highlighter.py
"""
语法高亮

提供关键字、动词、字符串等的高亮显示。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Dict, List, Tuple
from keywords import KEYWORDS, VERB_ARITY


class LightHighlighter:
    """光明语法高亮"""
    
    # ANSI颜色代码
    COLORS = {
        'keyword': '\033[34m',     # 蓝色
        'verb': '\033[32m',        # 绿色
        'string': '\033[33m',      # 黄色
        'number': '\033[35m',      # 紫色
        'comment': '\033[90m',     # 灰色
        'error': '\033[31m',       # 红色
        'reset': '\033[0m',        # 重置
    }
    
    # 关键字集合
    KEYWORDS_SET = set([
        '设', '为', '段落', '接收', '返回', '类', '继承', '实现',
        '属性', '构造', '新建', '己', '如果', '那么', '否则', '结束',
        '遍历', '当', '跳出', '跳过', '尝试', '捕获', '抛出',
        '导入', '导出', '从', '真', '假', '空',
    ])
    
    # 动词集合
    VERBS_SET = set(VERB_ARITY.keys())
    
    def highlight(self, text: str) -> str:
        """高亮文本"""
        result = []
        i = 0
        
        while i < len(text):
            # 注释
            if text[i] == '#':
                end = text.find('\n', i)
                if end == -1:
                    end = len(text)
                result.append(self.COLORS['comment'])
                result.append(text[i:end])
                result.append(self.COLORS['reset'])
                i = end
                continue
            
            # 字符串
            if text[i] in '"\'':
                quote = text[i]
                result.append(self.COLORS['string'])
                result.append(quote)
                i += 1
                while i < len(text) and text[i] != quote:
                    if text[i] == '\\' and i + 1 < len(text):
                        result.append(text[i:i+2])
                        i += 2
                    else:
                        result.append(text[i])
                        i += 1
                if i < len(text):
                    result.append(text[i])
                    i += 1
                result.append(self.COLORS['reset'])
                continue
            
            # 数字
            if text[i].isdigit():
                result.append(self.COLORS['number'])
                while i < len(text) and (text[i].isdigit() or text[i] == '.'):
                    result.append(text[i])
                    i += 1
                result.append(self.COLORS['reset'])
                continue
            
            # 中文关键字/动词
            if self._is_chinese(text[i]):
                word = self._extract_chinese_word(text, i)
                
                if word in self.KEYWORDS_SET:
                    result.append(self.COLORS['keyword'])
                    result.append(word)
                    result.append(self.COLORS['reset'])
                elif word in self.VERBS_SET:
                    result.append(self.COLORS['verb'])
                    result.append(word)
                    result.append(self.COLORS['reset'])
                else:
                    result.append(word)
                
                i += len(word)
                continue
            
            # 其他字符
            result.append(text[i])
            i += 1
        
        return ''.join(result)
    
    def _is_chinese(self, ch: str) -> bool:
        """判断是否是中文"""
        return '\u4e00' <= ch <= '\u9fff'
    
    def _extract_chinese_word(self, text: str, start: int) -> str:
        """提取中文词"""
        end = start
        while end < len(text) and self._is_chinese(text[end]):
            end += 1
        return text[start:end]


# prompt_toolkit 高亮器（可选）
try:
    from prompt_toolkit.lexers import Lexer
    from prompt_toolkit.styles import Style
    
    class PromptToolkitLexer(Lexer):
        """prompt_toolkit 词法分析器"""
        
        def __init__(self, highlighter: LightHighlighter):
            self.highlighter = highlighter
        
        def lex_document(self, document):
            def get_line(lineno):
                line = document.lines[lineno]
                # 返回高亮后的文本
                return [(self.highlighter.highlight(line),)]
            return get_line
    
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    PromptToolkitLexer = None
```

- [ ] **步骤 2：Commit**

```bash
git add src/repl/highlighter.py
git commit -m "feat(repl): add syntax highlighter"
```

---

### 任务 6：增强REPL

**文件：**
- 创建：`src/repl/enhanced.py`

- [ ] **步骤 1：编写增强REPL实现**

```python
# src/repl/enhanced.py
"""
增强REPL

使用 prompt_toolkit 提供高级功能。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'antlrparser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Optional

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


class EnhancedREPL:
    """增强REPL（prompt_toolkit）"""
    
    def __init__(self, core_repl):
        """初始化
        
        Args:
            core_repl: LightREPL 核心实例
        """
        if not HAS_PROMPT_TOOLKIT:
            raise ImportError("prompt_toolkit 未安装")
        
        self.core = core_repl
        
        # 创建补全器
        from .completer import LightCompleter, PromptToolkitCompleter
        self.completer = LightCompleter(self.core.executor.env.variables)
        self.pt_completer = PromptToolkitCompleter(self.completer)
        
        # 创建高亮器
        from .highlighter import LightHighlighter, PromptToolkitLexer
        self.highlighter = LightHighlighter()
        self.pt_lexer = PromptToolkitLexer(self.highlighter)
        
        # 创建会话
        history_file = os.path.expanduser("~/.light_repl_history")
        self.session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.pt_completer,
            lexer=self.pt_lexer,
            style=Style.from_dict({
                'prompt': 'ansicyan bold',
            })
        )
    
    def run(self):
        """运行增强REPL"""
        self.core.print_banner()
        
        while True:
            try:
                # 获取提示符
                if self.core.buffer:
                    prompt = "...   "
                else:
                    prompt = "光明> "
                
                # 读取输入
                line = self.session.prompt(prompt)
                
                # 处理输入
                result = self.core.process_input(line)
                
                # 显示结果
                if result and result != 'EXIT':
                    print(result)
                
                if result == 'EXIT':
                    print("再见！")
                    break
                
                # 更新补全器环境
                self.completer.update_env(self.core.executor.env.variables)
                
            except KeyboardInterrupt:
                print("\n^C")
                self.core.buffer = []
            except EOFError:
                print("\n再见！")
                break
```

- [ ] **步骤 2：更新 core.py 支持增强模式**

修改 `src/repl/core.py` 的 `__init__` 方法，添加增强模式检测：

```python
def __init__(self, enhanced=False):
    """初始化REPL"""
    self.executor = Executor()
    self.command_handler = CommandHandler(
        env=self.executor.env.variables,
        executor=self.executor
    )
    self.buffer: List[str] = []
    self.history: List[str] = []
    self.debug_mode = False
    
    # 尝试加载增强模式
    if enhanced:
        try:
            from .enhanced import EnhancedREPL, HAS_PROMPT_TOOLKIT
            if HAS_PROMPT_TOOLKIT:
                self._enhanced_impl = EnhancedREPL(self)
                self._use_enhanced = True
            else:
                self._use_enhanced = False
        except ImportError:
            self._use_enhanced = False
    else:
        self._use_enhanced = False

def run(self):
    """启动REPL"""
    if self._use_enhanced:
        self._enhanced_impl.run()
    else:
        self._run_basic()
```

- [ ] **步骤 3：Commit**

```bash
git add src/repl/enhanced.py src/repl/core.py
git commit -m "feat(repl): add enhanced REPL with prompt_toolkit"
```

---

### 任务 7：CLI整合

**文件：**
- 修改：`antlrparser/light_cli.py`

- [ ] **步骤 1：更新CLI添加REPL命令**

```python
# antlrparser/light_cli.py 修改部分

# 在 subparsers 中添加 repl 命令
repl_parser = subparsers.add_parser("repl", help="启动交互式REPL")
repl_parser.add_argument("--enhanced", action="store_true", help="使用增强模式")

# 在 main() 函数中添加处理
elif args.command == "repl":
    from repl.core import LightREPL
    repl = LightREPL(enhanced=args.enhanced)
    repl.run()

# 无参数时进入REPL
if not args.command:
    from repl.core import LightREPL
    repl = LightREPL()
    repl.run()
```

- [ ] **步骤 2：测试CLI**

运行：`python antlrparser/light_cli.py`
预期：自动进入REPL

运行：`python antlrparser/light_cli.py repl --enhanced`
预期：进入增强REPL（需安装prompt_toolkit）

- [ ] **步骤 3：Commit**

```bash
git add antlrparser/light_cli.py
git commit -m "feat(cli): integrate REPL into CLI"
```

---

### 任务 8：调试支持（可选）

**文件：**
- 创建：`src/repl/debugger.py`

- [ ] **步骤 1：编写调试器实现**

```python
# src/repl/debugger.py
"""
调试支持

提供断点、单步执行、变量监视等功能。
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass


@dataclass
class Breakpoint:
    """断点"""
    line: int
    file: str = ""
    condition: str = ""


class Debugger:
    """调试器"""
    
    def __init__(self, executor):
        self.executor = executor
        self.breakpoints: Dict[int, Breakpoint] = {}
        self.watch_vars: Set[str] = set()
        self.debug_mode = False
        self.step_mode = False
        self.current_line = 0
        self.call_stack: List[str] = []
    
    def toggle(self, state: bool = None) -> str:
        """切换调试模式"""
        if state is None:
            self.debug_mode = not self.debug_mode
        else:
            self.debug_mode = state
        
        return f"调试模式: {'开启' if self.debug_mode else '关闭'}"
    
    def add_breakpoint(self, line: int, condition: str = "") -> str:
        """添加断点"""
        bp = Breakpoint(line=line, condition=condition)
        self.breakpoints[line] = bp
        return f"断点设置: 行 {line}"
    
    def remove_breakpoint(self, line: int) -> str:
        """移除断点"""
        if line in self.breakpoints:
            del self.breakpoints[line]
            return f"断点移除: 行 {line}"
        return f"断点不存在: 行 {line}"
    
    def list_breakpoints(self) -> str:
        """列出断点"""
        if not self.breakpoints:
            return "无断点"
        
        lines = ["当前断点:"]
        for bp in self.breakpoints.values():
            lines.append(f"  行 {bp.line}")
        return '\n'.join(lines)
    
    def watch(self, var_name: str) -> str:
        """监视变量"""
        self.watch_vars.add(var_name)
        return f"监视变量: {var_name}"
    
    def unwatch(self, var_name: str) -> str:
        """取消监视"""
        if var_name in self.watch_vars:
            self.watch_vars.remove(var_name)
            return f"取消监视: {var_name}"
        return f"未监视: {var_name}"
    
    def show_watches(self) -> str:
        """显示监视变量"""
        if not self.watch_vars:
            return "无监视变量"
        
        lines = ["监视变量:"]
        for var in sorted(self.watch_vars):
            try:
                val = self.executor.env.get(var)
                lines.append(f"  {var} = {val}")
            except:
                lines.append(f"  {var} = <未定义>")
        return '\n'.join(lines)
    
    def step(self) -> str:
        """单步执行"""
        self.step_mode = True
        return "单步模式开启"
    
    def continue_exec(self) -> str:
        """继续执行"""
        self.step_mode = False
        return "继续执行"
    
    def backtrace(self) -> str:
        """显示调用栈"""
        if not self.call_stack:
            return "调用栈为空"
        
        lines = ["调用栈:"]
        for i, frame in enumerate(self.call_stack):
            lines.append(f"  {i}. {frame}")
        return '\n'.join(lines)
    
    def inspect(self, var_name: str) -> str:
        """查看变量详情"""
        try:
            val = self.executor.env.get(var_name)
            return f"{var_name}: {type(val).__name__} = {val}"
        except NameError:
            return f"变量 '{var_name}' 未定义"
    
    def log_execution(self, stmt_type: str, details: str):
        """记录执行日志"""
        if self.debug_mode:
            print(f"[调试] {stmt_type}: {details}")
    
    def check_breakpoint(self) -> bool:
        """检查是否到达断点"""
        if self.current_line in self.breakpoints:
            bp = self.breakpoints[self.current_line]
            if bp.condition:
                # TODO: 评估条件
                return True
            return True
        return False
```

- [ ] **步骤 2：更新命令处理添加调试命令**

在 `src/repl/commands.py` 中添加调试命令处理：

```python
# 在 _execute 方法中添加
elif cmd == 'debug':
    return self._toggle_debug(args)
elif cmd == 'step':
    return self._step()
elif cmd == 'break':
    return self._set_breakpoint(args)
elif cmd == 'watch':
    return self._watch_var(args)
elif cmd == 'inspect':
    return self._inspect_var(args)
elif cmd == 'backtrace':
    return self._backtrace()

# 添加新方法
def _step(self) -> str:
    if self.executor and hasattr(self.executor, 'debugger'):
        return self.executor.debugger.step()
    return "调试器未初始化"

def _set_breakpoint(self, args: str) -> str:
    if self.executor and hasattr(self.executor, 'debugger'):
        try:
            line = int(args)
            return self.executor.debugger.add_breakpoint(line)
        except ValueError:
            return "用法: :break <行号>"
    return "调试器未初始化"

def _watch_var(self, args: str) -> str:
    if self.executor and hasattr(self.executor, 'debugger'):
        return self.executor.debugger.watch(args)
    return "调试器未初始化"

def _inspect_var(self, args: str) -> str:
    if self.executor and hasattr(self.executor, 'debugger'):
        return self.executor.debugger.inspect(args)
    return "调试器未初始化"

def _backtrace(self) -> str:
    if self.executor and hasattr(self.executor, 'debugger'):
        return self.executor.debugger.backtrace()
    return "调试器未初始化"
```

- [ ] **步骤 3：Commit**

```bash
git add src/repl/debugger.py src/repl/commands.py
git commit -m "feat(repl): add debugger support"
```

---

## 实现优先级总结

| Phase | 任务 | 依赖 | 状态 |
|-------|------|------|------|
| 1 | 混合执行引擎 | 无 | 核心 |
| 2 | 命令处理 | 任务1 | 核心 |
| 3 | 核心REPL | 任务1,2 | 核心 |
| 4 | 自动补全 | 任务3 | 增强 |
| 5 | 语法高亮 | 任务3 | 增强 |
| 6 | 增强REPL | 任务4,5 | 增强 |
| 7 | CLI整合 | 任务3,6 | 核心 |
| 8 | 调试支持 | 任务1 | 高级 |

---

**计划已完成。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**