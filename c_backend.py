#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C 代码生成器 - 将光明生成的 Python 代码翻译为 C 代码

生成的 C 代码可通过 Clang/LLVM 或 GCC 编译为原生可执行文件。
"""

import ast
import os
import sys
import re


# ── 类型映射表 ──
PY_TYPE_TO_C = {
    'int': 'int',
    'float': 'double',
    'str': 'const char*',
    'bool': 'int',
    'None': 'void',
    'list': 'PyObject*',  # 复杂类型暂用 void*
    'dict': 'PyObject*',
}

# 光明函数名到 C 函数名的映射
FN_MAP = {
    '输出': 'light_print',
    '打印': 'light_print',
    '转字符串': 'light_str',
}

# 需要生成的运行时函数
RUNTIME_HEADER = '''#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>

/* ── 光明运行时库 ── */

void light_print(const char* s) {
    printf("%s", s);
}

void light_print_int(int n) {
    printf("%d", n);
}

void light_print_double(double d) {
    printf("%g", d);
}

void light_print_bool(int b) {
    printf("%s", b ? "真" : "假");
}

void light_println(void) {
    printf("\\n");
}

/* 多参数输出：最多支持 10 个参数 */
void light_print_1(const char* a0) { light_print(a0); }
void light_print_1i(const char* a0, int a1) { light_print(a0); light_print_int(a1); }
void light_print_1d(const char* a0, double a1) { light_print(a0); light_print_double(a1); }
void light_print_1s(const char* a0, const char* a1) { light_print(a0); light_print(a1); }

'''

# 缩进
INDENT = "    "


class PythonToC:
    """将 Python AST 转换为 C 代码"""
    
    # 内部变量名列表——这些变量由编译器生成，不应出现在 C 输出中
    _INTERNAL_VARS = frozenset({'类型检查开启', '调试模式'})
    
    def __init__(self):
        self.c_code = ""
        self.indent_level = 0
        self.func_decls = []  # 函数声明列表
        self.var_types = {}   # 变量类型跟踪
        self.current_func = None
        self.temp_var_counter = 0
        self.has_runtime = False
    
    def indent(self):
        return INDENT * self.indent_level
    
    def new_temp_var(self, c_type):
        """生成临时变量名"""
        self.temp_var_counter += 1
        name = f"_tmp_{self.temp_var_counter}"
        return name
    
    def translate_python_to_c(self, python_code):
        """将 Python 代码翻译为 C 代码"""
        # 解析 Python AST
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return f"/* 语法错误: {e} */\n"
        
        # 生成 C 代码
        self.c_code = RUNTIME_HEADER
        self.has_runtime = True
        
        # 遍历 AST 节点
        for node in tree.body:
            self._translate_node(node)
        
        return self.c_code
    
    def _translate_node(self, node):
        """翻译单个 AST 节点"""
        if isinstance(node, ast.FunctionDef):
            self._translate_function_def(node)
        elif isinstance(node, ast.Assign):
            self._translate_assign(node)
        elif isinstance(node, ast.Expr):
            self._translate_expr(node.value)
        elif isinstance(node, ast.If):
            self._translate_if(node)
        elif isinstance(node, ast.While):
            self._translate_while(node)
        elif isinstance(node, ast.For):
            self._translate_for(node)
        elif isinstance(node, ast.Return):
            self._translate_return(node)
        elif isinstance(node, ast.Pass):
            self.c_code += self.indent() + "/* pass */\n"
        elif isinstance(node, ast.Import):
            pass  # 忽略 import
        elif isinstance(node, ast.ImportFrom):
            pass  # 忽略 import from
        elif isinstance(node, ast.AnnAssign):
            self._translate_ann_assign(node)
        else:
            self.c_code += f"{self.indent()}/* 未支持的节点: {type(node).__name__} */\n"
    
    def _get_type_annotation(self, node):
        """获取类型注解"""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Subscript):
            # 复合类型如 list[int]
            return f"{self._get_type_annotation(node.value)}[{self._get_type_annotation(node.slice)}]"
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None
    
    def _type_to_c(self, py_type):
        """Python 类型名到 C 类型"""
        if py_type is None:
            return 'int'  # 默认类型
        # 处理复合类型
        if '[' in py_type:
            base = py_type.split('[')[0]
            if base == '列表':
                return 'void**'  # 简化处理
            if base == '字典':
                return 'void**'
            return 'void*'
        # 基础类型映射
        mapping = {
            '整数': 'int',
            '小数': 'double',
            '文本': 'const char*',
            '布尔': 'int',
            '空': 'void',
            'int': 'int',
            'float': 'double',
            'str': 'const char*',
            'bool': 'int',
            'None': 'void',
        }
        return mapping.get(py_type, 'int')
    
    def _translate_expr_to_c(self, node):
        """将 Python 表达式翻译为 C 表达式字符串"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                # 转义字符串
                escaped = node.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                return f'"{escaped}"'
            elif isinstance(node.value, bool):
                return '1' if node.value else '0'
            elif isinstance(node.value, int):
                return str(node.value)
            elif isinstance(node.value, float):
                return str(node.value)
            elif node.value is None:
                return '0'
            else:
                return str(node.value)
        
        elif isinstance(node, ast.Name):
            name = node.id
            # 映射中文布尔值
            if name == '真':
                return '1'
            if name == '假':
                return '0'
            if name == '无':
                return '0'
            return name
        
        elif isinstance(node, ast.BinOp):
            left = self._translate_expr_to_c(node.left)
            right = self._translate_expr_to_c(node.right)
            op = self._get_op(node.op)
            return f'({left} {op} {right})'
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._translate_expr_to_c(node.operand)
            if isinstance(node.op, ast.Not):
                return f'(!{operand})'
            elif isinstance(node.op, ast.USub):
                return f'(-{operand})'
            elif isinstance(node.op, ast.UAdd):
                return f'(+{operand})'
            return f'({operand})'
        
        elif isinstance(node, ast.Compare):
            left = self._translate_expr_to_c(node.left)
            ops = [self._get_cmp_op(op) for op in node.ops]
            comparators = [self._translate_expr_to_c(c) for c in node.comparators]
            
            if len(ops) == 1:
                return f'({left} {ops[0]} {comparators[0]})'
            else:
                # 链式比较: a < b < c → (a < b && b < c)
                result = f'({left} {ops[0]} {comparators[0]}'
                for i in range(1, len(ops)):
                    result += f' && {comparators[i-1]} {ops[i]} {comparators[i]}'
                result += ')'
                return result
        
        elif isinstance(node, ast.BoolOp):
            values = [self._translate_expr_to_c(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return '(' + ' && '.join(values) + ')'
            elif isinstance(node.op, ast.Or):
                return '(' + ' || '.join(values) + ')'
        
        elif isinstance(node, ast.Call):
            return self._translate_call(node)
        
        elif isinstance(node, ast.IfExp):
            test = self._translate_expr_to_c(node.test)
            body = self._translate_expr_to_c(node.body)
            orelse = self._translate_expr_to_c(node.orelse)
            return f'({test} ? {body} : {orelse})'
        
        elif isinstance(node, ast.Subscript):
            value = self._translate_expr_to_c(node.value)
            slice_val = self._translate_expr_to_c(node.slice)
            return f'({value}[{slice_val}])'
        
        elif isinstance(node, ast.List):
            elts = [self._translate_expr_to_c(e) for e in node.elts]
            return '{' + ', '.join(elts) + '}'
        
        elif isinstance(node, ast.Dict):
            return '{0}'  # 简化处理
        
        elif isinstance(node, ast.Attribute):
            value = self._translate_expr_to_c(node.value)
            return f'({value}.{node.attr})'
        
        else:
            return f'/* 未支持的表达式: {type(node).__name__} */ 0'
    
    def _get_op(self, op):
        """获取运算符"""
        op_map = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '/',
            ast.Mod: '%',
            ast.Pow: 'pow',
            ast.LShift: '<<',
            ast.RShift: '>>',
            ast.BitOr: '|',
            ast.BitXor: '^',
            ast.BitAnd: '&',
        }
        for cls, c_op in op_map.items():
            if isinstance(op, cls):
                return c_op
        return '/* ? */'
    
    def _get_cmp_op(self, op):
        """获取比较运算符"""
        op_map = {
            ast.Eq: '==',
            ast.NotEq: '!=',
            ast.Lt: '<',
            ast.LtE: '<=',
            ast.Gt: '>',
            ast.GtE: '>=',
            ast.Is: '==',
            ast.IsNot: '!=',
            ast.In: '/* in */',
            ast.NotIn: '/* not in */',
        }
        for cls, c_op in op_map.items():
            if isinstance(op, cls):
                return c_op
        return '/* ? */'
    
    def _translate_call(self, node):
        """翻译函数调用"""
        func_name = self._get_func_name(node.func)
        args = [self._translate_expr_to_c(a) for a in node.args]
        
        # 检查是否是输出函数
        if func_name == '输出' or func_name == '打印':
            return self._translate_print(node.args)
        
        # 检查是否是光明运行时函数
        if func_name in FN_MAP:
            c_func = FN_MAP[func_name]
            return f'{c_func}({", ".join(args)})'

        # 光明「除以/除」在 Python 腿经 _light_trunc_div 包裹（整数向零截断、浮点真除）；
        # C 的 `/` 对整数天然向零截断、浮点真除，正是裁决 B 语义，直接映射回原生 C `/`，
        # 避免把 Python 体的 trunc_div helper 原样发射成坏 C。
        if func_name == '_light_trunc_div' and len(args) == 2:
            return f'({args[0]} / {args[1]})'

        return f'{func_name}({", ".join(args)})'
    
    def _get_func_name(self, node):
        """获取函数名"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f'{self._translate_expr_to_c(node.value)}.{node.attr}'
        return 'unknown_func'
    
    def _translate_print(self, arg_nodes):
        """翻译输出函数调用
        
        参数:
            arg_nodes: 原始 AST 表达式节点列表
        """
        if not arg_nodes:
            return 'printf("\\n")'
        
        # 构建格式字符串和参数列表
        fmt_parts = []
        c_args = []
        for node in arg_nodes:
            c_expr = self._translate_expr_to_c(node)
            arg_type = self._infer_type(node)
            
            if arg_type == 'const char*' or arg_type == 'str':
                fmt_parts.append('%s')
                c_args.append(c_expr)
            elif arg_type == 'double':
                fmt_parts.append('%g')
                c_args.append(c_expr)
            else:
                # int, bool 等
                fmt_parts.append('%d')
                c_args.append(c_expr)
        
        fmt = '"' + ''.join(fmt_parts) + '"'
        return f'printf({fmt}, {", ".join(c_args)})'
    
    def _translate_function_def(self, node):
        """翻译函数定义"""
        func_name = node.name
        # 跳过主函数特殊处理（在 C 中主函数是 main）
        is_main = (func_name == '主函数')
        
        # 收集参数
        args = []
        arg_types = []
        arg_names = []
        
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = 'int'
            if arg.annotation:
                py_type = self._get_type_annotation(arg.annotation)
                arg_type = self._type_to_c(py_type)
            args.append(f'{arg_type} {arg_name}')
            arg_types.append(arg_type)
            arg_names.append(arg_name)
            self.var_types[arg_name] = arg_type
        
        # 获取返回类型
        return_type = 'int'
        if node.returns:
            py_return = self._get_type_annotation(node.returns)
            return_type = self._type_to_c(py_return)
        
        if is_main:
            return_type = 'int'
            c_func_name = 'main'
            args = []  # main 函数无参数
        else:
            c_func_name = func_name
        
        # 生成函数声明
        decl = f'{return_type} {c_func_name}({", ".join(args)})'
        self.func_decls.append(decl + ';')
        
        # 生成函数定义
        self.c_code += f'\n{decl} {{\n'
        self.indent_level = 1
        
        # 翻译函数体
        for stmt in node.body:
            self._translate_node(stmt)
        
        # 默认返回值
        if return_type != 'void' and not self._has_return(node):
            if return_type == 'int':
                self.c_code += f'{self.indent()}return 0;\n'
        
        self.indent_level = 0
        self.c_code += '}\n\n'
    
    def _has_return(self, node):
        """检查函数是否有 return 语句"""
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                return True
        return False
    
    def _translate_assign(self, node):
        """翻译赋值语句"""
        if len(node.targets) == 1:
            target = node.targets[0]
            value = self._translate_expr_to_c(node.value)
            
            if isinstance(target, ast.Name):
                var_name = target.id
                # 跳过编译器内部变量（如 类型检查开启）
                if var_name in self._INTERNAL_VARS:
                    return
                # 推断类型
                var_type = self._infer_type(node.value)
                if var_name not in self.var_types:
                    self.var_types[var_name] = var_type
                    self.c_code += f'{self.indent()}{var_type} {var_name} = {value};\n'
                else:
                    self.c_code += f'{self.indent()}{var_name} = {value};\n'
            elif isinstance(target, ast.Subscript):
                var_name = self._translate_expr_to_c(target.value)
                index = self._translate_expr_to_c(target.slice)
                self.c_code += f'{self.indent()}{var_name}[{index}] = {value};\n'
            else:
                self.c_code += f'{self.indent()}/* 赋值: {ast.dump(target)} = {value} */\n'
    
    def _translate_ann_assign(self, node):
        """翻译带类型注解的赋值"""
        target = node.target
        value = self._translate_expr_to_c(node.value) if node.value else '0'
        
        if isinstance(target, ast.Name):
            var_name = target.id
            # 跳过编译器内部变量
            if var_name in self._INTERNAL_VARS:
                return
            if node.annotation:
                py_type = self._get_type_annotation(node.annotation)
                var_type = self._type_to_c(py_type)
            else:
                var_type = self._infer_type(node.value) if node.value else 'int'
            
            self.var_types[var_name] = var_type
            self.c_code += f'{self.indent()}{var_type} {var_name} = {value};\n'
    
    def _infer_type(self, node):
        """推断表达式类型"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int):
                return 'int'
            elif isinstance(node.value, float):
                return 'double'
            elif isinstance(node.value, str):
                return 'const char*'
            elif isinstance(node.value, bool):
                return 'int'
            else:
                return 'int'
        elif isinstance(node, ast.Name):
            return self.var_types.get(node.id, 'int')
        elif isinstance(node, ast.BinOp):
            # 根据运算符推断
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)):
                left_type = self._infer_type(node.left)
                right_type = self._infer_type(node.right)
                if 'double' in (left_type, right_type):
                    return 'double'
                return 'int'
            return 'int'
        elif isinstance(node, ast.Compare):
            return 'int'  # 比较结果总是 int (bool)
        elif isinstance(node, ast.Call):
            return 'int'  # 默认
        elif isinstance(node, ast.List):
            return 'void**'
        elif isinstance(node, ast.Dict):
            return 'void**'
        elif isinstance(node, ast.UnaryOp):
            return self._infer_type(node.operand)
        return 'int'
    
    def _translate_expr(self, node):
        """翻译表达式语句"""
        if isinstance(node, ast.Call):
            expr = self._translate_call(node)
            if not expr.endswith(';'):
                expr += ';'
            self.c_code += f'{self.indent()}{expr}\n'
        else:
            expr = self._translate_expr_to_c(node)
            self.c_code += f'{self.indent()}{expr};\n'
    
    def _translate_if(self, node):
        """翻译 if 语句"""
        test = self._translate_expr_to_c(node.test)
        self.c_code += f'{self.indent()}if ({test}) {{\n'
        self.indent_level += 1
        for stmt in node.body:
            self._translate_node(stmt)
        self.indent_level -= 1
        
        # 处理 elif 和 else
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif
                self.c_code += self.indent() + '} else '
                self._translate_if_head(node.orelse[0])
            else:
                # else
                self.c_code += self.indent() + '} else {\n'
                self.indent_level += 1
                for stmt in node.orelse:
                    self._translate_node(stmt)
                self.indent_level -= 1
                self.c_code += self.indent() + '}\n'
        else:
            self.c_code += self.indent() + '}\n'
    
    def _translate_if_head(self, node):
        """翻译 if/elif 头部"""
        test = self._translate_expr_to_c(node.test)
        self.c_code += f'if ({test}) {{\n'
        self.indent_level += 1
        for stmt in node.body:
            self._translate_node(stmt)
        self.indent_level -= 1
        
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self.c_code += self.indent() + '} else '
                self._translate_if_head(node.orelse[0])
            else:
                self.c_code += self.indent() + '} else {\n'
                self.indent_level += 1
                for stmt in node.orelse:
                    self._translate_node(stmt)
                self.indent_level -= 1
                self.c_code += self.indent() + '}\n'
        else:
            self.c_code += self.indent() + '}\n'
    
    def _translate_while(self, node):
        """翻译 while 语句"""
        test = self._translate_expr_to_c(node.test)
        self.c_code += f'{self.indent()}while ({test}) {{\n'
        self.indent_level += 1
        for stmt in node.body:
            self._translate_node(stmt)
        self.indent_level -= 1
        self.c_code += f'{self.indent()}}}\n'
    
    def _translate_for(self, node):
        """翻译 for 语句（简化：只处理 range）"""
        # 简化：将 for x in range(n) 翻译为 for (int x = 0; x < n; x++)
        target = node.target.id if isinstance(node.target, ast.Name) else 'i'
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
            args = node.iter.args
            if len(args) == 1:
                end = self._translate_expr_to_c(args[0])
                self.c_code += f'{self.indent()}for (int {target} = 0; {target} < {end}; {target}++) {{\n'
            elif len(args) == 2:
                start = self._translate_expr_to_c(args[0])
                end = self._translate_expr_to_c(args[1])
                self.c_code += f'{self.indent()}for (int {target} = {start}; {target} < {end}; {target}++) {{\n'
            else:
                self.c_code += f'{self.indent()}/* for 循环: range({", ".join(self._translate_expr_to_c(a) for a in args)}) */\n'
                self.c_code += f'{self.indent()}{{\n'
        else:
            self.c_code += f'{self.indent()}/* for 循环 */\n'
            self.c_code += f'{self.indent()}{{\n'
        
        self.indent_level += 1
        for stmt in node.body:
            self._translate_node(stmt)
        self.indent_level -= 1
        self.c_code += f'{self.indent()}}}\n'
    
    def _translate_return(self, node):
        """翻译 return 语句"""
        if node.value:
            value = self._translate_expr_to_c(node.value)
            self.c_code += f'{self.indent()}return {value};\n'
        else:
            self.c_code += f'{self.indent()}return;\n'


def 编译到C(源代码):
    """将光明源文件编译为 C 代码
    
    参数:
        源代码: 光明源文件内容（字符串）
    
    返回:
        C 代码字符串，失败时返回 None
    """
    try:
        import ast
        import os
        import sys
        # 尝试从 light6 模块加载编译器
        try:
            from light6 import 编译代码
        except ImportError:
            # 直接加载编译器
            _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            # 支持 PyInstaller 打包后的路径查找
            if getattr(sys, 'frozen', False):
                _MEIPASS = getattr(sys, '_MEIPASS', None)
                if _MEIPASS and os.path.isdir(os.path.join(_MEIPASS, 'bootstrap')):
                    _BOOTSTRAP_DIR = os.path.join(_MEIPASS, 'bootstrap')
                else:
                    _BOOTSTRAP_DIR = os.path.join(_BASE_DIR, 'bootstrap')
            else:
                _BOOTSTRAP_DIR = os.path.join(_BASE_DIR, 'bootstrap')
            if os.path.isdir(_BOOTSTRAP_DIR):
                sys.path.insert(0, _BOOTSTRAP_DIR)
            # 创建运行时命名空间
            ns = {}
            ns['列表创建'] = lambda *args: list(args)
            ns['列表追加'] = lambda lst, item: lst.append(item)
            ns['列表获取'] = lambda lst, i: lst[i]
            ns['列表长度'] = len
            ns['列表弹栈'] = lambda lst: lst.pop() if lst else None
            ns['字符串长度'] = len
            ns['字符串获取'] = lambda s, i: s[i]
            ns['截取'] = lambda s, a, b: s[a:b]
            ns['打印'] = print
            ns['输出'] = print
            ns['转字符串'] = str
            ns['建'] = lambda t, v: [t, v]
            ns['真'] = True
            ns['假'] = False
            ns['类型检查开启'] = False
            compiler_path = os.path.join(_BOOTSTRAP_DIR, 'level7_generated.py')
            with open(compiler_path, 'r', encoding='utf-8-sig') as f:
                code = f.read()
            exec(code, ns)
            编译代码 = ns['编译']
        
        py_code = 编译代码(源代码)
        if py_code is None:
            return None
        
        # 将 Python 代码翻译为 C
        translator = PythonToC()
        c_code = translator.translate_python_to_c(py_code)
        
        # 确保 main 函数调用主函数
        if '主函数' in py_code:
            c_code = c_code.replace(
                'int main() {',
                'int main(int argc, char** argv) {'
            )
        
        return c_code
    
    except Exception as e:
        import traceback
        print(f"[C 后端错误] {e}", file=sys.stderr)
        traceback.print_exc()
        return None


def 编译光明到C文件(光明文件路径, c文件路径=None):
    """将光明文件编译为 C 源文件
    
    参数:
        光明文件路径: .light 文件路径
        c文件路径: 输出的 .c 文件路径（可选）
    
    返回:
        成功时返回 C 文件路径，失败时返回 None
    """
    if not os.path.exists(光明文件路径):
        print(f"[错误] 文件不存在: {光明文件路径}", file=sys.stderr)
        return None
    
    with open(光明文件路径, 'r', encoding='utf-8') as f:
        源代码 = f.read()
    
    c_code = 编译到C(源代码)
    if c_code is None:
        return None
    
    if c文件路径 is None:
        基础名 = os.path.splitext(os.path.basename(光明文件路径))[0]
        c文件路径 = os.path.join(os.path.dirname(光明文件路径), 基础名 + '.c')
    
    with open(c文件路径, 'w', encoding='utf-8') as f:
        f.write(c_code)
    
    print(f"[C 后端] 已生成: {c文件路径}")
    return c文件路径


def 编译C到原生(c文件路径, exe_path=None):
    """使用系统上可用的 C 编译器将 C 文件编译为原生可执行文件
    
    按顺序尝试: clang, gcc, cl (MSVC)
    
    参数:
        c文件路径: .c 文件路径
        exe_path: 输出的 .exe 文件路径（可选）
    
    返回:
        成功时返回 exe 路径，失败时返回 None
    """
    import subprocess
    
    if not os.path.exists(c文件路径):
        print(f"[错误] C 文件不存在: {c文件路径}", file=sys.stderr)
        return None
    
    if exe_path is None:
        基础名 = os.path.splitext(os.path.basename(c文件路径))[0]
        exe_path = os.path.join(os.path.dirname(c文件路径), 基础名 + '.exe')
    
    # 查找可用的 C 编译器
    compilers = [
        ('clang', ['clang', '-o', exe_path, c文件路径, '-O2', '-Wall']),
        ('gcc', ['gcc', '-o', exe_path, c文件路径, '-O2', '-Wall']),
        ('cl', ['cl', '/Fe' + exe_path, c文件路径, '/O2', '/W3']),
    ]
    
    for name, cmd in compilers:
        try:
            result = subprocess.run([name, '--version'], capture_output=True, text=True, timeout=5)
            print(f"[C 编译器] 找到: {name}")
            print(f"[C 编译器] 正在编译: {c文件路径}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(exe_path):
                size = os.path.getsize(exe_path)
                print(f"[C 编译器] 编译成功!")
                print(f"[C 编译器] 输出: {exe_path}")
                print(f"[C 编译器] 大小: {size / 1024:.1f} KB")
                return exe_path
            else:
                print(f"[C 编译器] 编译失败 (返回码: {result.returncode})")
                if result.stderr:
                    for line in result.stderr.split('\n')[-5:]:
                        if line.strip():
                            print(f"  {line}", file=sys.stderr)
                        
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    print(f"[C 编译器] 未找到可用的 C 编译器")
    print(f"[C 编译器] 请安装 Clang/LLVM 或 GCC 后重试")
    print(f"[C 编译器] 或手动编译: clang -o {exe_path} {c文件路径}")
    return None


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python c_backend.py <源文件.light> [输出.c]")
        print("       python c_backend.py --compile <源文件.c> [输出.exe]")
        sys.exit(1)
    
    if sys.argv[1] == '--compile':
        c_file = sys.argv[2]
        exe = sys.argv[3] if len(sys.argv) > 3 else None
        result = 编译C到原生(c_file, exe)
        if result:
            print(f"[成功] 原生可执行文件: {result}")
        else:
            sys.exit(1)
    else:
        light_file = sys.argv[1]
        c_file = sys.argv[2] if len(sys.argv) > 2 else None
        result = 编译光明到C文件(light_file, c_file)
        if result:
            print(f"[成功] 生成的 C 文件: {result}")
            # 尝试编译
            exe = 编译C到原生(result)
            if exe:
                print(f"[成功] 原生可执行文件: {exe}")
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()