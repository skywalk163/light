#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言多语言代码转换器

将 Java/C 代码转换为段言（DuanLang）代码。

支持特性：
  - Java：类、方法、循环、条件、变量、数组、异常处理
  - C：函数、结构体、循环、条件、指针、数组、宏

用法：
    python code_converter.py --from-java Hello.java
    python code_converter.py --from-c main.c
    duan ai convert --from-java Hello.java
    duan ai convert --from-c main.c
"""

import argparse
import os
import re
import sys
from typing import Optional, List, Dict, Tuple


# ═══════════════════════════════════════════════════════════════════
# Java 转换器
# ═══════════════════════════════════════════════════════════════════

class Java2DuanConverter:
    """Java 代码 → 段言 转换器"""

    # Java 基本类型 → 段言类型映射
    TYPE_MAP = {
        'int': '整数',
        'long': '整数',
        'float': '浮数',
        'double': '浮数',
        'boolean': '布尔',
        'char': '字符',
        'byte': '整数',
        'short': '整数',
        'String': '字符串',
        'void': '空',
        'int[]': '整数列表',
        'String[]': '字符串列表',
        'char[]': '字符列表',
        'byte[]': '字节列表',
    }

    # 操作符映射
    OP_MAP = {
        '+': '加',
        '-': '减',
        '*': '乘',
        '/': '除以',
        '%': '模',
        '++': '加上 1',
        '--': '减去 1',
        '==': '等于',
        '!=': '不等于',
        '>': '大于',
        '<': '小于',
        '>=': '大于等于',
        '<=': '小于等于',
        '&&': '且',
        '||': '或',
        '!': '非',
        '=': '为',
        '+=': '加上',
        '-=': '减去',
        '*=': '乘以',
        '/=': '除以',
    }

    # 访问修饰符映射
    ACCESS_MAP = {
        'public': '公有',
        'private': '私有',
        'protected': '保护',
        'static': '静态',
        'final': '最终',
        'abstract': '抽象',
    }

    def __init__(self):
        self.indent_level = 0
        self.output_lines = []
        self._buffer = []  # 用于收集临时行

    def _emit(self, line: str):
        indent = "    " * self.indent_level
        self.output_lines.append(f"{indent}{line}")

    def convert(self, java_code: str) -> str:
        """将 Java 代码转换为段言"""
        self.output_lines = []
        self.indent_level = 0

        # 移除注释
        java_code = re.sub(r'//.*$', '', java_code, flags=re.MULTILINE)
        java_code = re.sub(r'/\*.*?\*/', '', java_code, flags=re.DOTALL)

        # 按行处理
        lines = java_code.split('\n')
        self._process_lines(lines)

        return '\n'.join(self.output_lines)

    def _process_lines(self, lines: List[str]):
        """逐行处理 Java 代码"""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # 跳过 package 和 import
            if line.startswith('package ') or line.startswith('import '):
                i += 1
                continue

            # 跳过注解
            if line.startswith('@'):
                i += 1
                continue

            # 类定义
            if 'class ' in line and '{' in line:
                i = self._handle_class(line, lines, i + 1)
                continue

            # 方法定义
            if self._is_method_declaration(line):
                i = self._handle_method(line, lines, i + 1)
                continue

            # 语句
            if self._is_statement(line):
                handled = self._handle_statement(line)
                if handled:
                    i += 1
                    continue

            i += 1

    def _is_method_declaration(self, line: str) -> bool:
        """判断是否为方法声明"""
        # 去除修饰符前缀
        stripped = line
        mods = ['public', 'private', 'protected', 'static', 'final', 'abstract',
                'synchronized', 'native', 'transient', 'volatile']
        for mod in mods:
            if stripped.startswith(mod + ' '):
                stripped = stripped[len(mod) + 1:]

        # 检查方法签名（返回类型 方法名(参数)）
        m = re.match(r'(\w+(?:\[\])?(?:\s*<[^>]+>)?)\s+(\w+)\s*\(', stripped)
        return bool(m) and 'class ' not in stripped

    def _handle_class(self, line: str, lines: List[str], start_idx: int) -> int:
        """处理类定义"""
        # 提取类名
        m = re.match(r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?', line)
        if not m:
            return start_idx

        class_name = m.group(1)
        extends = m.group(2)
        implements = m.group(3)

        if extends:
            self._emit(f"类 {class_name} 继承 {extends}：")
        else:
            self._emit(f"类 {class_name}：")

        self.indent_level += 1
        idx = start_idx

        # 处理类体
        brace_count = 1  # 已经有一个左括号
        while idx < len(lines) and brace_count > 0:
            stmt = lines[idx].strip()
            if not stmt:
                idx += 1
                continue

            # 计算括号
            brace_count += stmt.count('{') - stmt.count('}')

            if brace_count <= 0:
                break

            # 构造方法
            if self._is_constructor(stmt, class_name):
                idx = self._handle_constructor(stmt, lines, idx + 1)
                continue

            # 方法定义
            if self._is_method_declaration(stmt):
                idx = self._handle_method(stmt, lines, idx + 1)
                continue

            # 字段定义
            if self._is_field_declaration(stmt):
                handled = self._handle_field(stmt)
                if handled:
                    idx += 1
                    continue

            idx += 1

        self.indent_level -= 1
        return idx

    def _is_constructor(self, line: str, class_name: str) -> bool:
        """判断是否为构造方法"""
        return line.startswith(f'{class_name}(') or line.startswith(f'public {class_name}(')

    def _handle_constructor(self, line: str, lines: List[str], start_idx: int) -> int:
        """处理构造方法"""
        # 提取参数
        m = re.search(r'\(([^)]*)\)', line)
        params = m.group(1) if m else ''

        duan_params = self._convert_params(params)
        if duan_params:
            self._emit(f"构造 接收 {duan_params}：")
        else:
            self._emit("构造：")

        self.indent_level += 1
        idx = self._parse_body(lines, start_idx)
        self.indent_level -= 1
        return idx

    def _handle_method(self, line: str, lines: List[str], start_idx: int) -> int:
        """处理方法定义"""
        # 提取修饰符
        prefix = ''
        stripped = line
        mods = ['public', 'private', 'protected', 'static', 'final', 'abstract',
                'synchronized', 'native']
        for mod in mods:
            if stripped.startswith(mod + ' '):
                if mod in self.ACCESS_MAP:
                    prefix = self.ACCESS_MAP[mod] + ' '
                stripped = stripped[len(mod) + 1:]

        # 提取方法名和参数
        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)\s*\(([^)]*)\)', stripped)
        if not m:
            return start_idx

        return_type = m.group(1)
        method_name = m.group(2)
        params = m.group(3)

        # main 方法特殊处理
        if method_name == 'main' and 'String[]' in params:
            # 跳过 main 方法或转为入口
            return self._parse_body(lines, start_idx)

        duan_params = self._convert_params(params)
        if duan_params:
            self._emit(f"{prefix}段落 {method_name} 接收 {duan_params}：")
        else:
            self._emit(f"{prefix}段落 {method_name}：")

        self.indent_level += 1
        idx = self._parse_body(lines, start_idx)
        self.indent_level -= 1
        return idx

    def _is_field_declaration(self, line: str) -> bool:
        """判断是否为字段声明"""
        if '=' in line and '(' not in line:
            return True
        m = re.match(r'(?:public|private|protected|static|final)\s+(\w+(?:\[\])?)\s+(\w+)', line)
        return bool(m)

    def _handle_field(self, line: str) -> bool:
        """处理字段声明"""
        # 处理访问修饰符
        prefix = ''
        stripped = line.rstrip(';').strip()
        mods = ['public', 'private', 'protected', 'static', 'final']
        for mod in mods:
            if stripped.startswith(mod + ' '):
                if mod in self.ACCESS_MAP:
                    prefix = self.ACCESS_MAP[mod] + ' '
                stripped = stripped[len(mod) + 1:]

        # 类型 变量名 = 值
        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)\s*=\s*(.+)$', stripped)
        if m:
            field_type = m.group(1)
            field_name = m.group(2)
            field_value = self._convert_expr(m.group(3))
            self._emit(f"{prefix}属性 {field_name} 等于 {field_value}")
            return True

        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)$', stripped)
        if m:
            field_name = m.group(2)
            self._emit(f"{prefix}属性 {field_name}")
            return True

        return False

    def _convert_params(self, params: str) -> str:
        """转换参数列表"""
        if not params or params.strip() == '':
            return ''
        duan_params = []
        for param in params.split(','):
            param = param.strip()
            if not param:
                continue
            # ... 可变参数
            if param.startswith('...'):
                duan_params.append(f"*{param[3:]}")
            else:
                parts = param.split()
                if len(parts) >= 2:
                    duan_params.append(parts[-1])  # 只取变量名
                else:
                    duan_params.append(parts[0])
        return ', '.join(duan_params)

    def _convert_expr(self, expr: str) -> str:
        """转换表达式"""
        expr = expr.strip()

        # null
        expr = re.sub(r'\bnull\b', '空', expr)
        # true/false
        expr = re.sub(r'\btrue\b', '真', expr)
        expr = re.sub(r'\bfalse\b', '假', expr)
        # this
        expr = re.sub(r'\bthis\b', '己', expr)
        # super
        expr = re.sub(r'\bsuper\b', '父', expr)

        # 字符串字面量保持原样
        # 数字字面量保持原样

        return expr

    def _is_statement(self, line: str) -> bool:
        """判断是否为语句"""
        if not line:
            return False
        # 去除花括号
        stripped = line.rstrip('{').strip()
        if not stripped:
            return False
        return True

    def _handle_statement(self, line: str) -> bool:
        """处理单个语句"""
        line = line.rstrip(';').strip()

        if not line:
            return False

        # 变量声明
        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)\s*=\s*(.+)$', line)
        if m:
            var_name = m.group(2)
            var_value = self._convert_expr(m.group(3))
            self._emit(f"设 {var_name} 为 {var_value}")
            return True

        # 变量声明（无初始化）
        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)$', line)
        if m:
            var_name = m.group(2)
            self._emit(f"设 {var_name} 为 空")
            return True

        # 赋值
        m = re.match(r'(\w+(?:\.\w+)*(?:\[[^\]]*\])?)\s*=\s*(.+)$', line)
        if m:
            target = m.group(1)
            value = self._convert_expr(m.group(2))
            self._emit(f"设 {target} 为 {value}")
            return True

        # 复合赋值
        for op, duan_op in [('+=', '加上'), ('-=', '减去'), ('*=', '乘以'), ('/=', '除以'), ('%=', '取余')]:
            if op in line:
                parts = line.split(op, 1)
                target = parts[0].strip()
                value = self._convert_expr(parts[1].strip())
                self._emit(f"{target} {duan_op} {value}")
                return True

        # return
        m = re.match(r'return\s+(.+)$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"返回 {value}")
            return True
        if line == 'return':
            self._emit("返回")
            return True

        # System.out.println
        m = re.match(r'System\.out\.println\((.+)\)$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"打印({value})")
            return True

        # 方法调用
        m = re.match(r'(\w+(?:\.\w+)*)\s*\(([^)]*)\)$', line)
        if m:
            call_name = m.group(1)
            args = m.group(2)
            if args:
                self._emit(f"{call_name}({self._convert_expr(args)})")
            else:
                self._emit(f"{call_name}()")
            return True

        # if 语句（单行）
        m = re.match(r'if\s*\((.+)\)$', line)
        if m:
            cond = self._convert_expr(m.group(1))
            self._emit(f"如果 {cond}：")
            return True

        # else if
        if line.startswith('else if'):
            m = re.match(r'else\s+if\s*\((.+)\)$', line)
            if m:
                cond = self._convert_expr(m.group(1))
                self._emit(f"否则若 {cond}：")
                return True

        # else
        if line == 'else':
            self._emit("否则：")
            return True

        # for
        m = re.match(r'for\s*\((.+)\)$', line)
        if m:
            return True  # 循环体由 _parse_body 处理

        # while
        m = re.match(r'while\s*\((.+)\)$', line)
        if m:
            cond = self._convert_expr(m.group(1))
            self._emit(f"当 {cond}：")
            return True

        # break
        if line == 'break':
            self._emit("跳出")
            return True

        # continue
        if line == 'continue':
            self._emit("跳过")
            return True

        # try
        if line == 'try':
            self._emit("尝试：")
            return True

        # catch
        m = re.match(r'catch\s*\(\s*(\w+)\s+(\w+)\s*\)$', line)
        if m:
            exc_type = m.group(1)
            exc_var = m.group(2)
            self._emit(f"捕获 {exc_type} {exc_var}：")
            return True

        # finally
        if line == 'finally':
            self._emit("最终：")
            return True

        # throw
        m = re.match(r'throw\s+(.+)$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"抛出 {value}")
            return True

        # new 对象
        m = re.match(r'(\w+)\s*=\s*new\s+(\w+)\(([^)]*)\)$', line)
        if m:
            var_name = m.group(1)
            class_name = m.group(2)
            args = self._convert_expr(m.group(3))
            if args:
                self._emit(f"设 {var_name} 为 新建 {class_name}({args})")
            else:
                self._emit(f"设 {var_name} 为 新建 {class_name}()")
            return True

        # new 数组
        m = re.match(r'(\w+(?:\[\])?)\s+(\w+)\s*=\s*new\s+\w+\[(\d+)\]$', line)
        if m:
            var_name = m.group(2)
            size = m.group(3)
            self._emit(f"设 {var_name} 为 [空] 乘 {size}")
            return True

        return False

    def _parse_body(self, lines: List[str], start_idx: int) -> int:
        """解析花括号体"""
        idx = start_idx
        brace_count = 1

        # 找到第一个左括号
        while idx < len(lines) and '{' not in lines[idx] and idx < start_idx + 3:
            stmt = lines[idx].strip()
            if stmt:
                self._handle_statement(stmt)
            idx += 1

        if idx >= len(lines):
            return idx

        # 从包含左括号的那行开始
        line = lines[idx].strip()
        brace_count = line.count('{') - line.count('}')
        if brace_count <= 0:
            brace_count = 1

        # 处理左括号前的语句
        before_brace = line.split('{')[0].strip()
        if before_brace:
            self._handle_statement(before_brace)

        idx += 1

        # 处理体内容
        while idx < len(lines) and brace_count > 0:
            line = lines[idx].strip()
            brace_count += line.count('{') - line.count('}')

            if brace_count <= 0:
                break

            if line:
                # 替换行内花括号
                clean_line = line.replace('{', '').replace('}', '').strip()
                if clean_line:
                    self._handle_statement(clean_line)

            idx += 1

        return idx


# ═══════════════════════════════════════════════════════════════════
# C 转换器
# ═══════════════════════════════════════════════════════════════════

class C2DuanConverter:
    """C 代码 → 段言 转换器"""

    TYPE_MAP = {
        'int': '整数',
        'long': '整数',
        'float': '浮数',
        'double': '浮数',
        'char': '字符',
        'void': '空',
        'size_t': '整数',
        'int*': '整数指针',
        'char*': '字符串',
        'void*': '空指针',
        'unsigned int': '无符号整数',
        'unsigned long': '无符号整数',
        'short': '短整数',
        'unsigned char': '无符号字符',
    }

    OP_MAP = {
        '+': '加',
        '-': '减',
        '*': '乘',
        '/': '除以',
        '%': '模',
        '++': '加上 1',
        '--': '减去 1',
        '==': '等于',
        '!=': '不等于',
        '>': '大于',
        '<': '小于',
        '>=': '大于等于',
        '<=': '小于等于',
        '&&': '且',
        '||': '或',
        '!': '非',
        '=': '为',
        '+=': '加上',
        '-=': '减去',
        '*=': '乘以',
        '/=': '除以',
        '<<': '左移',
        '>>': '右移',
        '&': '按位与',
        '|': '按位或',
        '^': '按位异或',
        '~': '按位取反',
    }

    def __init__(self):
        self.indent_level = 0
        self.output_lines = []
        self._includes = set()
        self._macros = {}

    def _emit(self, line: str):
        indent = "    " * self.indent_level
        self.output_lines.append(f"{indent}{line}")

    def convert(self, c_code: str) -> str:
        """将 C 代码转换为段言"""
        self.output_lines = []
        self.indent_level = 0
        self._includes.clear()
        self._macros.clear()

        # 预处理
        c_code = self._preprocess(c_code)

        # 按行处理
        lines = c_code.split('\n')
        self._process_lines(lines)

        return '\n'.join(self.output_lines)

    def _preprocess(self, code: str) -> str:
        """预处理 C 代码"""
        # 移除注释
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # 收集宏定义
        lines = code.split('\n')
        processed = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#include'):
                self._includes.add(stripped)
                continue
            if stripped.startswith('#define'):
                m = re.match(r'#define\s+(\w+)\s+(.+)', stripped)
                if m:
                    self._macros[m.group(1)] = m.group(2)
                continue
            if stripped.startswith('#'):
                continue
            processed.append(line)

        return '\n'.join(processed)

    def _process_lines(self, lines: List[str]):
        """逐行处理 C 代码"""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # 结构体
            if 'struct ' in line and '{' in line:
                i = self._handle_struct(line, lines, i + 1)
                continue

            # 函数定义
            if self._is_function_definition(line, lines, i):
                i = self._handle_function(line, lines, i + 1)
                continue

            # 语句
            if self._is_statement(line):
                handled = self._handle_statement(line)
                if handled:
                    i += 1
                    continue

            i += 1

    def _is_function_definition(self, line: str, lines: List[str], idx: int) -> bool:
        """判断是否为函数定义"""
        stripped = line.rstrip('{').strip()
        # 返回类型 函数名(参数)
        m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*{?$', stripped)
        if not m:
            return False
        # 排除结构体
        if 'struct ' in line:
            return False
        return_type = m.group(1)
        # 排除变量声明
        if return_type in ('int', 'char', 'float', 'double', 'void',
                           'long', 'short', 'unsigned', 'size_t'):
            return True
        if return_type.endswith('*'):
            return True
        return False

    def _handle_struct(self, line: str, lines: List[str], start_idx: int) -> int:
        """处理结构体"""
        m = re.match(r'struct\s+(\w+)\s*{', line)
        if not m:
            return start_idx

        struct_name = m.group(1)
        self._emit(f"类 {struct_name}：")
        self.indent_level += 1

        idx = start_idx
        brace_count = 1
        while idx < len(lines) and brace_count > 0:
            stmt = lines[idx].strip()
            brace_count += stmt.count('{') - stmt.count('}')
            if brace_count <= 0:
                break

            # 字段定义
            field_m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)\s*;?$', stmt)
            if field_m:
                field_name = field_m.group(2)
                self._emit(f"属性 {field_name}")

            idx += 1

        self.indent_level -= 1
        return idx

    def _handle_function(self, line: str, lines: List[str], start_idx: int) -> int:
        """处理函数定义"""
        stripped = line.rstrip('{').strip()

        # 返回类型 函数名(参数)
        m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*{?$', stripped)
        if not m:
            return start_idx

        return_type = m.group(1)
        func_name = m.group(2)
        params = m.group(3)

        # main 函数特殊处理
        if func_name == 'main':
            if 'argc' in params or 'argv' in params:
                return self._parse_body(lines, start_idx)

        duan_params = self._convert_params(params)
        if duan_params:
            self._emit(f"段落 {func_name} 接收 {duan_params}：")
        else:
            self._emit(f"段落 {func_name}：")

        self.indent_level += 1
        idx = self._parse_body(lines, start_idx)
        self.indent_level -= 1
        return idx

    def _convert_params(self, params: str) -> str:
        """转换参数列表"""
        if not params or params.strip() == '':
            return ''
        if params.strip() == 'void':
            return ''

        duan_params = []
        for param in params.split(','):
            param = param.strip()
            if not param:
                continue

            # void 参数
            if param == 'void':
                continue

            # 指针参数
            m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)$', param)
            if m:
                duan_params.append(m.group(2))
            else:
                # 简单类型 变量名
                parts = param.split()
                if len(parts) >= 2:
                    duan_params.append(parts[-1])
                else:
                    duan_params.append(parts[0])

        return ', '.join(duan_params)

    def _is_statement(self, line: str) -> bool:
        """判断是否为语句"""
        if not line:
            return False
        stripped = line.rstrip('{').strip()
        if not stripped:
            return False
        return True

    def _handle_statement(self, line: str) -> bool:
        """处理单个语句"""
        line = line.rstrip(';').strip()

        if not line:
            return False

        # 变量声明（带初始化）
        m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)\s*=\s*(.+)$', line)
        if m:
            var_name = m.group(2)
            var_value = self._convert_expr(m.group(3))
            self._emit(f"设 {var_name} 为 {var_value}")
            return True

        # 变量声明（无初始化）
        m = re.match(r'(\w+(?:\s*\*)?)\s+(\w+)$', line)
        if m:
            var_name = m.group(2)
            self._emit(f"设 {var_name} 为 空")
            return True

        # 赋值
        m = re.match(r'(\w+(?:\[[^\]]*\])?(?:\.\w+)?(?:->\w+)?)\s*=\s*(.+)$', line)
        if m:
            target = m.group(1)
            value = self._convert_expr(m.group(2))
            self._emit(f"设 {target} 为 {value}")
            return True

        # 复合赋值
        for op, duan_op in [('+=', '加上'), ('-=', '减去'), ('*=', '乘以'), ('/=', '除以'), ('%=', '取余'),
                           ('<<=', '左移'), ('>>=', '右移'), ('&=', '按位与'), ('|=', '按位或')]:
            if op in line:
                parts = line.split(op, 1)
                target = parts[0].strip()
                value = self._convert_expr(parts[1].strip())
                self._emit(f"{target} {duan_op} {value}")
                return True

        # return
        m = re.match(r'return\s+(.+)$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"返回 {value}")
            return True
        if line == 'return':
            self._emit("返回")
            return True

        # printf
        m = re.match(r'printf\(([^)]+)\)$', line)
        if m:
            args = m.group(1)
            self._emit(f"打印({args})")
            return True

        # 函数调用
        m = re.match(r'(\w+)\s*\(([^)]*)\)$', line)
        if m:
            call_name = m.group(1)
            args = self._convert_expr(m.group(2))
            if args:
                self._emit(f"{call_name}({args})")
            else:
                self._emit(f"{call_name}()")
            return True

        # malloc
        m = re.match(r'(\w+)\s*=\s*\((\w+(?:\s*\*)?)\)\s*malloc\(([^)]+)\)$', line)
        if m:
            var_name = m.group(1)
            size = self._convert_expr(m.group(3))
            self._emit(f"设 {var_name} 为 分配内存({size})")
            return True

        # free
        m = re.match(r'free\((\w+)\)$', line)
        if m:
            var_name = m.group(1)
            self._emit(f"释放内存({var_name})")
            return True

        # if
        m = re.match(r'if\s*\((.+)\)$', line)
        if m:
            cond = self._convert_expr(m.group(1))
            self._emit(f"如果 {cond}：")
            return True

        # else if
        if line.startswith('else if'):
            m = re.match(r'else\s+if\s*\((.+)\)$', line)
            if m:
                cond = self._convert_expr(m.group(1))
                self._emit(f"否则若 {cond}：")
                return True

        # else
        if line == 'else':
            self._emit("否则：")
            return True

        # for
        m = re.match(r'for\s*\((.+)\)$', line)
        if m:
            return True

        # while
        m = re.match(r'while\s*\((.+)\)$', line)
        if m:
            cond = self._convert_expr(m.group(1))
            self._emit(f"当 {cond}：")
            return True

        # do
        if line == 'do':
            self._emit("当 真：")
            return True

        # break
        if line == 'break':
            self._emit("跳出")
            return True

        # continue
        if line == 'continue':
            self._emit("跳过")
            return True

        # switch
        m = re.match(r'switch\s*\((.+)\)$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"匹配 {value}：")
            return True

        # case
        m = re.match(r'case\s+(.+):$', line)
        if m:
            value = self._convert_expr(m.group(1))
            self._emit(f"情况 {value}：")
            return True

        # default
        if line == 'default:':
            self._emit("情况 _：")
            return True

        return False

    def _convert_expr(self, expr: str) -> str:
        """转换表达式"""
        expr = expr.strip()

        # NULL
        expr = re.sub(r'\bNULL\b', '空', expr)
        expr = re.sub(r'\bnullptr\b', '空', expr)
        # true/false
        expr = re.sub(r'\btrue\b', '真', expr)
        expr = re.sub(r'\bfalse\b', '假', expr)
        # 宏替换
        for name, value in self._macros.items():
            expr = re.sub(r'\b' + name + r'\b', value, expr)

        # sizeof
        expr = re.sub(r'sizeof\s*\((\w+)\)', r'sizeof(\1)', expr)

        return expr

    def _parse_body(self, lines: List[str], start_idx: int) -> int:
        """解析花括号体"""
        idx = start_idx
        brace_count = 1

        # 跳过空行直到找到左括号
        while idx < len(lines) and '{' not in lines[idx] and idx < start_idx + 5:
            stmt = lines[idx].strip()
            if stmt:
                self._handle_statement(stmt)
            idx += 1

        if idx >= len(lines):
            return idx

        # 处理包含左括号的行
        line = lines[idx].strip()
        brace_count = line.count('{') - line.count('}')
        if brace_count <= 0:
            brace_count = 1

        before_brace = line.split('{')[0].strip()
        if before_brace and before_brace != line:
            self._handle_statement(before_brace)

        idx += 1

        # 处理体内容
        while idx < len(lines) and brace_count > 0:
            line = lines[idx].strip()
            brace_count += line.count('{') - line.count('}')

            if brace_count <= 0:
                break

            if line:
                clean_line = line.replace('{', '').replace('}', '').strip()
                if clean_line:
                    # 处理 for 循环头
                    if 'for' in clean_line:
                        self._handle_for_header(clean_line)
                    elif clean_line:
                        self._handle_statement(clean_line)

            idx += 1

        return idx

    def _handle_for_header(self, line: str):
        """处理 for 循环头"""
        m = re.match(r'for\s*\((.+?);\s*(.+?);\s*(.+)\)', line)
        if m:
            init = m.group(1).strip()
            cond = self._convert_expr(m.group(2).strip())
            update = m.group(3).strip()

            self._handle_statement(init)
            self._emit(f"当 {cond}：")
            # 把 update 添加到循环体末尾（由调用方处理）
            self._for_update = update


# ═══════════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════════

def convert_file(file_path: str, source_lang: str) -> str:
    """转换文件

    Args:
        file_path: 源文件路径
        source_lang: 源语言 ('java' 或 'c')

    Returns:
        转换后的段言代码
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    if source_lang == 'java':
        converter = Java2DuanConverter()
    elif source_lang == 'c':
        converter = C2DuanConverter()
    else:
        raise ValueError(f"不支持的源语言: {source_lang}")

    return converter.convert(source_code)


def convert_code(code: str, source_lang: str) -> str:
    """转换代码字符串"""
    if source_lang == 'java':
        converter = Java2DuanConverter()
    elif source_lang == 'c':
        converter = C2DuanConverter()
    else:
        raise ValueError(f"不支持的源语言: {source_lang}")
    return converter.convert(code)


def main():
    parser = argparse.ArgumentParser(
        prog='duan ai convert',
        description='将 Java/C 代码转换为段言（DuanLang）',
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--from-java', metavar='FILE',
                              help='转换 Java 文件')
    source_group.add_argument('--from-c', metavar='FILE',
                              help='转换 C 文件')

    parser.add_argument('--output', '-o', metavar='FILE',
                        help='输出到文件（默认输出到终端）')

    args = parser.parse_args()

    if args.from_java:
        source_lang = 'java'
        file_path = args.from_java
    elif args.from_c:
        source_lang = 'c'
        file_path = args.from_c
    else:
        parser.print_help()
        return

    try:
        result = convert_file(file_path, source_lang)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"转换完成，输出到: {args.output}")
        else:
            print(result)

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"转换错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()