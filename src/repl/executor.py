#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光明 REPL 混合执行引擎

支持：
1. 简单表达式解释执行（AST遍历）
2. 复杂代码块编译执行（生成Python代码）
"""

import sys
import os
import re
from typing import Dict, Any, Optional, List

# 添加路径
_current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _current_dir)
sys.path.insert(0, os.path.join(_current_dir, 'src'))
sys.path.insert(0, os.path.join(_current_dir, 'antlrparser'))


# =============================================================================
# 环境类
# =============================================================================

class Environment:
    """存储变量和函数的环境"""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Any] = {}

    def get(self, name: str) -> Any:
        """获取变量"""
        return self.variables.get(name)

    def set(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value

    def has(self, name: str) -> bool:
        """检查变量是否存在"""
        return name in self.variables

    def has_function(self, name: str) -> bool:
        """检查函数是否存在"""
        return name in self.functions

    def set_function(self, name: str, func: Any) -> None:
        """设置函数"""
        self.functions[name] = func

    def get_function(self, name: str) -> Optional[Any]:
        """获取函数"""
        return self.functions.get(name)


# =============================================================================
# 混合执行引擎
# =============================================================================

class Executor:
    """光明混合执行引擎

    执行流程：
    1. 解析代码 → AST
    2. 判断复杂度
    3. 简单表达式 → 解释执行（遍历AST）
    4. 复杂代码 → 编译执行（生成Python + exec）
    """

    # 运算符映射
    OP_MAP = {
        '加': '+', '减': '-', '乘': '*', '除': '/',
        '大于': '>', '小于': '<', '等于': '==',
        '不等于': '!=', '大于等于': '>=', '小于等于': '<=',
        '且': 'and', '或': 'or', '非': 'not',
    }

    # 内置函数
    BUILTINS = {
        '打印': 'print',
        '长': 'len',
        '首': lambda lst: lst[0] if lst else None,
        '末': lambda lst: lst[-1] if lst else None,
        '排序': 'sorted',
        '求和': 'sum',
        '反转': 'reversed',
        '转字符串': 'str',
        '转整数': 'int',
        '转浮点': 'float',
    }

    def __init__(self, env: Environment = None):
        """初始化执行引擎"""
        self.env = env if env is not None else Environment()
        self._debug_engine = None
        self._debug_enabled = False
        self._setup_builtins()

    def set_debug_engine(self, engine) -> None:
        """设置调试引擎

        Args:
            engine: DebugEngine 实例
        """
        self._debug_engine = engine
        self._debug_enabled = engine is not None

    def get_debug_engine(self):
        """获取调试引擎"""
        return self._debug_engine

    def _should_break(self, line_info: dict) -> bool:
        """检查调试引擎是否应该暂停

        Args:
            line_info: 行信息字典，包含 file_path, line 等

        Returns:
            是否应该暂停
        """
        if not self._debug_enabled or self._debug_engine is None:
            return False
        return self._debug_engine.should_break(
            line_info.get('file_path', '<repl>'),
            line_info.get('line', 0)
        )

    def _setup_builtins(self) -> None:
        """设置内置函数"""
        for name, func in self.BUILTINS.items():
            if callable(func) and not isinstance(func, str):
                self.env.set_function(name, func)

    def execute(self, code: str, env: Dict = None) -> Any:
        """主执行方法

        Args:
            code: 光明代码
            env: 可选的环境字典

        Returns:
            执行结果
        """
        # 合并环境
        if env:
            for k, v in env.items():
                self.env.set(k, v)

        # 判断复杂度
        if self._is_simple(code):
            # 简单表达式 → 解释执行
            return self._interpret_simple(code)
        else:
            # 复杂代码 → 编译执行
            return self._compile_and_run(code)

    def _is_simple(self, code: str) -> bool:
        """判断是否是简单表达式

        简单表达式（解释执行）：
        - 标识符、数字、字符串、布尔、列表
        - 二元运算、一元运算
        - 函数调用、属性访问、索引访问
        - 变量声明（设 ... 为 ...）
        - 打印语句

        复杂代码块（编译执行）：
        - 段落定义、类定义、接口定义
        - 条件语句（如果）
        - 循环语句（当、遍历）
        - 返回语句、导入/导出语句（多行）
        """
        line = code.strip()
        # 单行变量声明 `设 甲 为 10` 是简单的
        if line.startswith('设') and '为' in line and line.count('\n') == 0:
            return True
        # 单行打印是简单的
        if line.startswith('打印') and line.count('\n') == 0:
            return True
        # 复杂代码关键词（多行/块结构）
        complex_keywords = ['函数', '段落', '类', '接口', '如果', '当', '遍历',
                          '返回', '导入', '导出']
        # 只有多行或块结构才视为复杂
        if '\n' in code:
            return False
        for kw in complex_keywords:
            if kw in code:
                return False
        return True

    def _interpret_simple(self, code: str) -> Any:
        """解释执行简单表达式"""
        # 移除空白和句号
        code = code.strip().strip('。').strip()

        # 处理变量声明: 设 甲 为 3 -> 甲 = 3
        var_match = re.match(r'设\s+(\S+)\s+为\s+(.+)', code)
        if var_match:
            name = var_match.group(1)
            value_expr = var_match.group(2).strip()
            value = self._eval_expr(value_expr)
            self.env.set(name, value)
            # 调试：更新调试引擎的变量
            if self._debug_enabled and self._debug_engine:
                self._debug_engine.update_local_vars({name: value})
            return value

        # 处理打印语句: 打印(甲)。 -> print(甲)
        print_match = re.match(r'打印\((.+)\)', code)
        if print_match:
            expr = print_match.group(1).strip()
            value = self._eval_expr(expr)
            print(value)
            return value

        # 处理段落定义: 函数/段落 平方(数值): 返回 数值 * 数值。结束。
        # 简化处理：只支持单行定义
        # 新语法：函数/段落 名(参数): 返回 表达式。
        seg_match = re.match(r'(?:函数|段落)\s+(\S+)\s*\(([^)]*)\)\s*:\s*返回\s+(.+)', code)
        if seg_match:
            name = seg_match.group(1)
            params = [p.strip() for p in seg_match.group(2).split(',') if p.strip()]
            body = seg_match.group(3)
            # 创建函数
            def segment_func(*args):
                local_env = {}
                for i, p in enumerate(params):
                    local_env[p] = args[i] if i < len(args) else None
                return self._eval_expr(body, local_env)
            self.env.set_function(name, segment_func)
            return name
        # 旧语法兼容：函数/段落 平方 接收 数值: 返回 数值 * 数值。
        seg_match_old = re.match(r'(?:函数|段落)\s+(\S+)\s+接收\s+(\S+)\s*:\s*返回\s+(.+)', code)
        if seg_match_old:
            name = seg_match_old.group(1)
            param = seg_match_old.group(2)
            body = seg_match_old.group(3)
            def segment_func_old(*args):
                local_env = {param: args[0] if args else None}
                return self._eval_expr(body, local_env)
            self.env.set_function(name, segment_func_old)
            return name

        # 其他表达式：直接求值
        return self._eval_expr(code)

    def _eval_expr(self, expr: str, local_vars: Dict = None) -> Any:
        """对表达式求值"""
        if local_vars is None:
            local_vars = {}

        expr = expr.strip()

        # 数字
        if re.match(r'^-?\d+\.?\d*$', expr):
            num = float(expr) if '.' in expr else int(expr)
            return num

        # 字符串
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # 列表字面量
        if expr.startswith('[') and expr.endswith(']'):
            items = expr[1:-1].split(',')
            return [self._eval_expr(item.strip()) for item in items if item.strip()]

        # 二元运算
        for op, py_op in self.OP_MAP.items():
            if op in expr:
                parts = expr.split(op)
                if len(parts) == 2:
                    left = self._eval_expr(parts[0].strip(), local_vars)
                    right = self._eval_expr(parts[1].strip(), local_vars)
                    if op == '加' and (isinstance(left, str) or isinstance(right, str)):
                        return str(left) + str(right)
                    return eval(f"{left} {py_op} {right}")
                elif len(parts) > 2 and op in ['且', '或']:
                    result = self._eval_expr(parts[0].strip(), local_vars)
                    for i in range(1, len(parts)):
                        right = self._eval_expr(parts[i].strip(), local_vars)
                        if op == '且':
                            result = result and right
                        else:
                            result = result or right
                    return result

        # 函数调用
        func_match = re.match(r'(\S+)\((.*)\)$', expr)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2).strip()

            # 解析参数（需要考虑嵌套括号和列表）
            if args_str:
                args = self._parse_args(args_str, local_vars)
            else:
                args = []

            # 调用函数
            return self._call_function(func_name, args)

        # 标识符/变量
        if expr in local_vars:
            return local_vars[expr]
        value = self.env.get(expr)
        if value is not None:
            return value

        # 尝试作为 Python 表达式求值
        try:
            # 替换变量名
            py_expr = expr
            for name, value in local_vars.items():
                py_expr = re.sub(r'\b' + name + r'\b', repr(value), py_expr)
            for name, value in self.env.variables.items():
                py_expr = re.sub(r'\b' + name + r'\b', repr(value), py_expr)
            return eval(py_expr)
        except Exception:
            return None

    def _call_function(self, name: str, args: List) -> Any:
        """调用函数"""
        # 检查内置函数
        if name in self.BUILTINS:
            builtin = self.BUILTINS[name]
            if callable(builtin) and not isinstance(builtin, str):
                return builtin(*args)
            elif isinstance(builtin, str):
                # Python 内置函数
                return eval(f"{builtin}({', '.join(repr(a) for a in args)})")

        # 检查环境中的函数
        if self.env.has_function(name):
            func = self.env.get_function(name)
            return func(*args)

        # 未知函数
        return None

    def _parse_args(self, args_str: str, local_vars: Dict) -> List:
        """解析函数参数（考虑嵌套括号和列表）"""
        args = []
        current = []
        depth = 0
        in_list = False

        for ch in args_str:
            if ch == '[':
                in_list = True
                current.append(ch)
            elif ch == ']':
                in_list = False
                current.append(ch)
            elif ch == ',' and depth == 0 and not in_list:
                args.append(''.join(current).strip())
                current = []
            else:
                if ch == '(' or ch == ')':
                    depth += 1 if ch == '(' else -1
                current.append(ch)

        if current:
            args.append(''.join(current).strip())

        return [self._eval_expr(arg, local_vars) for arg in args if arg]

    def _compile_and_run(self, code: str) -> Any:
        """编译并执行复杂代码

        优先使用 ANTLR 解析器后端（parse_source + UnifiedCodeGenerator），
        不可用时回退到 src 手写解析器后端（LightParser + PythonCodeGenerator）。
        如果编译执行失败，会回退到解释执行。
        """
        try:
            module = None
            python_code = None

            # 优先尝试 ANTLR 解析器后端
            try:
                from antlrparser.light_visitor import parse_source
                from code_generator_unified import UnifiedCodeGenerator

                module = parse_source(code)
                if module:
                    python_code = UnifiedCodeGenerator().generate(module)
            except Exception:
                module = None
                python_code = None

            # 回退到 src 手写解析器后端
            if python_code is None:
                from light_parser_v3 import LightParser
                from code_generator import PythonCodeGenerator

                parser = LightParser()
                module = parser.parse(code)
                if module:
                    generator = PythonCodeGenerator()
                    python_code = generator.generate(module)

            if python_code is not None:

                # 使用持久化执行环境，维持 REPL 会话状态
                if not hasattr(self, '_exec_globals'):
                    self._exec_globals = {
                        '__builtins__': __builtins__,
                    }
                exec_globals = self._exec_globals
                # 暴露解释执行环境，供生成代码访问
                exec_globals['_light_env'] = self.env

                exec(python_code, exec_globals)

                # 更新 Environment 中的变量和函数（供后续解释执行使用）
                for name, value in exec_globals.items():
                    if not name.startswith('_'):
                        if callable(value):
                            self.env.set_function(name, value)
                        else:
                            self.env.set(name, value)

                return None
        except Exception as e:
            # 编译执行失败，回退到解释执行
            pass

        # 回退到解释执行
        return self._interpret_simple(code)

    def has_function(self, name: str) -> bool:
        """检查函数是否存在"""
        return self.env.has_function(name)

    def reset(self) -> None:
        """重置环境"""
        self.env = Environment()
        self._setup_builtins()
        if hasattr(self, '_exec_globals'):
            del self._exec_globals


# =============================================================================
# 快捷函数
# =============================================================================

def execute_code(code: str, env: Dict = None) -> Any:
    """执行光明代码的快捷函数"""
    executor = Executor()
    if env:
        for k, v in env.items():
            executor.env.set(k, v)
    return executor.execute(code)