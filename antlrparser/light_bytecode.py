"""
光明（Light）编程语言 - 字节码解释器

实现功能：
1. 将 AST 编译为字节码
2. 使用栈式虚拟机执行字节码
3. 支持常用操作码优化
4. 比树形解释器更快的执行速度
"""

import sys
import os
from typing import List, Optional, Any, Dict, Tuple, Union
from dataclasses import dataclass, field

# 导入 AST 节点
from light_ast import (
    ASTNode, Module, NumberLiteral, StringLiteral, BooleanLiteral,
    NullLiteral, ListLiteral, DictLiteral, DictEntry,
    Identifier, SegmentName, ModuleName,
    BinaryOp, UnaryOp, FunctionCall, PipeExpression,
    PropertyAccess, IndexAccess, NewExpression,
    VariableDeclaration, Assignment, IfStatement, ForeachStatement,
    WhileStatement, BreakStatement, ContinueStatement, ReturnStatement,
    TryStatement, ThrowStatement, PrintStatement, ExpressionStatement,
    Parameter, SegmentDefinition, DataTypeDefinition, ErrorTypeDefinition,
    ImportStatement, ExportStatement,
    ClassDefinition, InterfaceDefinition, MethodDefinition, ConstructorDefinition,
    InterfaceMethod, InterfaceProperty,
)

# =============================================================================
# 字节码操作码定义
# =============================================================================

class OpCode:
    # 常量操作
    LOAD_CONST = 0x01
    LOAD_VAR = 0x02
    STORE_VAR = 0x03
    
    # 算术运算
    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    MOD = 0x14
    POW = 0x15
    
    # 比较运算
    EQ = 0x20
    NEQ = 0x21
    LT = 0x22
    GT = 0x23
    LE = 0x24
    GE = 0x25
    
    # 逻辑运算
    AND = 0x30
    OR = 0x31
    NOT = 0x32
    
    # 控制流
    JMP = 0x40
    JMP_IF_TRUE = 0x41
    JMP_IF_FALSE = 0x42
    CALL = 0x43
    RETURN = 0x44
    PRINT = 0x45
    
    # 列表和字典
    LIST = 0x50
    DICT = 0x51
    INDEX_GET = 0x52
    INDEX_SET = 0x53
    PROP_GET = 0x54
    PROP_SET = 0x55
    
    # 对象操作
    NEW = 0x60
    METHOD_CALL = 0x61
    
    # 特殊
    NOP = 0x00
    HALT = 0xFF

# 操作码名称映射
OPCODE_NAMES = {
    OpCode.LOAD_CONST: 'LOAD_CONST',
    OpCode.LOAD_VAR: 'LOAD_VAR',
    OpCode.STORE_VAR: 'STORE_VAR',
    OpCode.ADD: 'ADD',
    OpCode.SUB: 'SUB',
    OpCode.MUL: 'MUL',
    OpCode.DIV: 'DIV',
    OpCode.MOD: 'MOD',
    OpCode.POW: 'POW',
    OpCode.EQ: 'EQ',
    OpCode.NEQ: 'NEQ',
    OpCode.LT: 'LT',
    OpCode.GT: 'GT',
    OpCode.LE: 'LE',
    OpCode.GE: 'GE',
    OpCode.AND: 'AND',
    OpCode.OR: 'OR',
    OpCode.NOT: 'NOT',
    OpCode.JMP: 'JMP',
    OpCode.JMP_IF_TRUE: 'JMP_IF_TRUE',
    OpCode.JMP_IF_FALSE: 'JMP_IF_FALSE',
    OpCode.CALL: 'CALL',
    OpCode.RETURN: 'RETURN',
    OpCode.PRINT: 'PRINT',
    OpCode.LIST: 'LIST',
    OpCode.DICT: 'DICT',
    OpCode.INDEX_GET: 'INDEX_GET',
    OpCode.INDEX_SET: 'INDEX_SET',
    OpCode.PROP_GET: 'PROP_GET',
    OpCode.PROP_SET: 'PROP_SET',
    OpCode.NEW: 'NEW',
    OpCode.METHOD_CALL: 'METHOD_CALL',
    OpCode.NOP: 'NOP',
    OpCode.HALT: 'HALT',
}

# =============================================================================
# 字节码编译器
# =============================================================================

@dataclass
class BytecodeChunk:
    """字节码块"""
    code: List[int] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    
    def add_constant(self, value: Any) -> int:
        """添加常量并返回索引"""
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)
    
    def add_name(self, name: str) -> int:
        """添加名称并返回索引"""
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)
    
    def emit(self, opcode: int, *args: int):
        """发射操作码"""
        self.code.append(opcode)
        self.code.extend(args)
    
    def __repr__(self):
        result = "BytecodeChunk:\n"
        result += f"  Constants: {self.constants}\n"
        result += f"  Names: {self.names}\n"
        result += "  Code:\n"
        
        i = 0
        while i < len(self.code):
            opcode = self.code[i]
            name = OPCODE_NAMES.get(opcode, f'0x{opcode:02X}')
            args = []
            
            # 根据操作码确定参数数量
            if opcode in [OpCode.LOAD_CONST, OpCode.LOAD_VAR, OpCode.STORE_VAR,
                          OpCode.JMP, OpCode.JMP_IF_TRUE, OpCode.JMP_IF_FALSE,
                          OpCode.CALL, OpCode.NEW, OpCode.METHOD_CALL,
                          OpCode.PROP_GET, OpCode.PROP_SET]:
                args = self.code[i+1:i+3]
                i += 3
            elif opcode in [OpCode.LIST, OpCode.DICT]:
                args = self.code[i+1:i+2]
                i += 2
            else:
                i += 1
            
            result += f"    {i-1:4d}: {name} {args}\n"
        
        return result

class BytecodeCompiler:
    """AST 到字节码的编译器"""
    
    def __init__(self):
        self.chunk = BytecodeChunk()
        self.label_counter = 0
    
    def new_label(self) -> int:
        """创建新标签"""
        label = self.label_counter
        self.label_counter += 1
        return label
    
    def compile(self, module: Module) -> BytecodeChunk:
        """编译模块"""
        for stmt in module.statements:
            self.compile_statement(stmt)
        
        self.chunk.emit(OpCode.HALT)
        return self.chunk
    
    def compile_statement(self, stmt: ASTNode):
        """编译语句"""
        if isinstance(stmt, VariableDeclaration):
            self.compile_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self.compile_assignment(stmt)
        elif isinstance(stmt, CompoundAssignment):
            # 复合赋值：展开为 变量 = 变量 运算符 值
            operator = stmt.operator
            op_map = {'加': '+', '减': '-', '乘': '*', '除': '/', '模': '%', '幂': '**'}
            py_op = op_map.get(operator, '+')
            # 编译为：变量 = 变量 op 值
            target_name = stmt.target
            self.chunk.emit(OpCode.LOAD_NAME, target_name)
            self.compile_expression(stmt.value)
            self.chunk.emit(OpCode.BINARY_OP, py_op)
            self.chunk.emit(OpCode.STORE_NAME, target_name)
        elif isinstance(stmt, IfStatement):
            self.compile_if(stmt)
        elif isinstance(stmt, WhileStatement):
            self.compile_while(stmt)
        elif isinstance(stmt, ForeachStatement):
            self.compile_foreach(stmt)
        elif isinstance(stmt, PrintStatement):
            self.compile_print(stmt)
        elif isinstance(stmt, ExpressionStatement):
            self.compile_expression(stmt.expr)
        elif isinstance(stmt, ReturnStatement):
            self.compile_return(stmt)
        elif isinstance(stmt, BreakStatement):
            self.chunk.emit(OpCode.JMP, 0, 0)  # 将在链接时修复
        elif isinstance(stmt, ContinueStatement):
            self.chunk.emit(OpCode.JMP, 0, 0)  # 将在链接时修复
    
    def compile_var_decl(self, stmt: VariableDeclaration):
        """编译变量声明"""
        self.compile_expression(stmt.value)
        name_idx = self.chunk.add_name(stmt.name)
        self.chunk.emit(OpCode.STORE_VAR, name_idx, 0)
    
    def compile_assignment(self, stmt: Assignment):
        """编译赋值语句"""
        self.compile_expression(stmt.value)
        name_idx = self.chunk.add_name(stmt.target.name)
        self.chunk.emit(OpCode.STORE_VAR, name_idx, 0)
    
    def compile_if(self, stmt: IfStatement):
        """编译条件语句"""
        # 编译条件表达式
        self.compile_expression(stmt.condition)
        
        # 如果条件为假，跳转到 else 或结束
        else_label = self.new_label()
        end_label = self.new_label()
        
        self.chunk.emit(OpCode.JMP_IF_FALSE, else_label, 0)
        
        # 编译 then 分支
        for body_stmt in stmt.then_branch:
            self.compile_statement(body_stmt)
        
        self.chunk.emit(OpCode.JMP, end_label, 0)
        
        # 标记 else 标签位置
        self._mark_label(else_label)
        
        # 编译 else 分支
        if stmt.else_branch:
            for body_stmt in stmt.else_branch:
                self.compile_statement(body_stmt)
        
        # 标记结束标签位置
        self._mark_label(end_label)
    
    def compile_while(self, stmt: WhileStatement):
        """编译 while 循环"""
        start_label = self.new_label()
        end_label = self.new_label()
        
        # 标记循环开始
        self._mark_label(start_label)
        
        # 编译条件
        self.compile_expression(stmt.condition)
        
        # 如果条件为假，跳转到结束
        self.chunk.emit(OpCode.JMP_IF_FALSE, end_label, 0)
        
        # 编译循环体
        for body_stmt in stmt.body:
            self.compile_statement(body_stmt)
        
        # 跳回循环开始
        self.chunk.emit(OpCode.JMP, start_label, 0)
        
        # 标记结束位置
        self._mark_label(end_label)
    
    def compile_foreach(self, stmt: ForeachStatement):
        """编译 foreach 循环"""
        # 编译可迭代对象
        self.compile_expression(stmt.iterable)
        
        # 创建标签
        loop_label = self.new_label()
        end_label = self.new_label()
        
        # 需要实现迭代器逻辑（简化版本）
        self.chunk.emit(OpCode.NOP)
    
    def compile_print(self, stmt: PrintStatement):
        """编译打印语句"""
        self.compile_expression(stmt.expr)
        self.chunk.emit(OpCode.PRINT)
    
    def compile_return(self, stmt: ReturnStatement):
        """编译返回语句"""
        if stmt.value:
            self.compile_expression(stmt.value)
        else:
            self.chunk.emit(OpCode.LOAD_CONST, self.chunk.add_constant(None), 0)
        self.chunk.emit(OpCode.RETURN)
    
    def compile_expression(self, expr: ASTNode):
        """编译表达式"""
        if isinstance(expr, NumberLiteral):
            const_idx = self.chunk.add_constant(expr.value)
            self.chunk.emit(OpCode.LOAD_CONST, const_idx, 0)
        
        elif isinstance(expr, StringLiteral):
            const_idx = self.chunk.add_constant(expr.value)
            self.chunk.emit(OpCode.LOAD_CONST, const_idx, 0)
        
        elif isinstance(expr, BooleanLiteral):
            const_idx = self.chunk.add_constant(expr.value)
            self.chunk.emit(OpCode.LOAD_CONST, const_idx, 0)
        
        elif isinstance(expr, NullLiteral):
            const_idx = self.chunk.add_constant(None)
            self.chunk.emit(OpCode.LOAD_CONST, const_idx, 0)
        
        elif isinstance(expr, Identifier):
            name_idx = self.chunk.add_name(expr.name)
            self.chunk.emit(OpCode.LOAD_VAR, name_idx, 0)
        
        elif isinstance(expr, BinaryOp):
            self.compile_expression(expr.left)
            self.compile_expression(expr.right)
            
            # 映射操作符到操作码
            op_map = {
                '+': OpCode.ADD,
                '-': OpCode.SUB,
                '*': OpCode.MUL,
                '/': OpCode.DIV,
                '%': OpCode.MOD,
                '^': OpCode.POW,
                '==': OpCode.EQ,
                '!=': OpCode.NEQ,
                '<': OpCode.LT,
                '>': OpCode.GT,
                '<=': OpCode.LE,
                '>=': OpCode.GE,
                '&&': OpCode.AND,
                '||': OpCode.OR,
            }
            
            opcode = op_map.get(expr.operator, OpCode.NOP)
            self.chunk.emit(opcode)
        
        elif isinstance(expr, UnaryOp):
            self.compile_expression(expr.operand)
            if expr.operator == '!':
                self.chunk.emit(OpCode.NOT)
            elif expr.operator == '-':
                # 实现负数
                self.chunk.emit(OpCode.LOAD_CONST, self.chunk.add_constant(0), 0)
                self.chunk.emit(OpCode.SUB)
        
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self.compile_expression(item)
            self.chunk.emit(OpCode.LIST, len(expr.items), 0)
        
        elif isinstance(expr, FunctionCall):
            # 编译参数
            for arg in expr.arguments:
                self.compile_expression(arg)
            
            # 获取函数名称
            if isinstance(expr.callee, Identifier):
                name_idx = self.chunk.add_name(expr.callee.name)
            elif isinstance(expr.callee, SegmentName):
                name_idx = self.chunk.add_name(expr.callee.name)
            else:
                name_idx = 0
            
            self.chunk.emit(OpCode.CALL, name_idx, len(expr.arguments))
        
        elif isinstance(expr, PropertyAccess):
            self.compile_expression(expr.object_expr)
            name_idx = self.chunk.add_name(expr.property_name)
            self.chunk.emit(OpCode.PROP_GET, name_idx, 0)
        
        elif isinstance(expr, IndexAccess):
            self.compile_expression(expr.object_expr)
            self.compile_expression(expr.index)
            self.chunk.emit(OpCode.INDEX_GET)
        
        elif isinstance(expr, NewExpression):
            # 编译构造函数参数
            for arg in expr.arguments:
                self.compile_expression(arg)
            class_idx = self.chunk.add_name(expr.class_name)
            self.chunk.emit(OpCode.NEW, class_idx, len(expr.arguments))
        
        else:
            # 默认处理 - 使用 NOP
            self.chunk.emit(OpCode.NOP)
    
    def _mark_label(self, label: int):
        """标记标签位置（简化实现）"""
        # 在完整实现中，这会记录标签对应的字节码偏移
        pass

# =============================================================================
# 字节码虚拟机
# =============================================================================

class BytecodeVM:
    """字节码虚拟机"""
    
    def __init__(self):
        self.stack = []
        self.env = {}
        self.pc = 0  # 程序计数器
        self.code = []
        self.constants = []
        self.names = []
        
        # 内置函数
        self.builtins = {
            '打印': self._builtin_print,
            '输出': self._builtin_print,
            'len': self._builtin_len,
            'abs': self._builtin_abs,
            'sqrt': self._builtin_sqrt,
        }
    
    def _builtin_print(self, args):
        print(''.join(str(arg) for arg in args))
        return None
    
    def _builtin_len(self, args):
        if len(args) == 1:
            return len(args[0])
        return 0
    
    def _builtin_abs(self, args):
        if len(args) == 1 and isinstance(args[0], (int, float)):
            return abs(args[0])
        return 0
    
    def _builtin_sqrt(self, args):
        if len(args) == 1 and isinstance(args[0], (int, float)):
            return args[0] ** 0.5
        return 0
    
    def load(self, chunk: BytecodeChunk):
        """加载字节码块"""
        self.code = chunk.code
        self.constants = chunk.constants
        self.names = chunk.names
        self.pc = 0
        self.stack = []
    
    def run(self):
        """执行字节码"""
        while self.pc < len(self.code):
            opcode = self.code[self.pc]
            
            try:
                self._execute_opcode(opcode)
            except Exception as e:
                print(f"运行时错误: {e}")
                print(f"  在指令 {self.pc}: {OPCODE_NAMES.get(opcode, f'0x{opcode:02X}')}")
                break
    
    def _execute_opcode(self, opcode: int):
        """执行单个操作码"""
        if opcode == OpCode.LOAD_CONST:
            # LOAD_CONST index (2 bytes)
            idx = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            self.stack.append(self.constants[idx])
            self.pc += 3
        
        elif opcode == OpCode.LOAD_VAR:
            # LOAD_VAR index (2 bytes)
            idx = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            name = self.names[idx]
            value = self.env.get(name, None)
            self.stack.append(value)
            self.pc += 3
        
        elif opcode == OpCode.STORE_VAR:
            # STORE_VAR index (2 bytes)
            idx = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            name = self.names[idx]
            value = self.stack.pop()
            self.env[name] = value
            self.pc += 3
        
        elif opcode == OpCode.ADD:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a + b)
            self.pc += 1
        
        elif opcode == OpCode.SUB:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a - b)
            self.pc += 1
        
        elif opcode == OpCode.MUL:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a * b)
            self.pc += 1
        
        elif opcode == OpCode.DIV:
            b = self.stack.pop()
            a = self.stack.pop()
            if b != 0:
                self.stack.append(a / b)
            else:
                self.stack.append(0)
            self.pc += 1
        
        elif opcode == OpCode.MOD:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a % b)
            self.pc += 1
        
        elif opcode == OpCode.POW:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a ** b)
            self.pc += 1
        
        elif opcode == OpCode.EQ:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a == b)
            self.pc += 1
        
        elif opcode == OpCode.NEQ:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a != b)
            self.pc += 1
        
        elif opcode == OpCode.LT:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a < b)
            self.pc += 1
        
        elif opcode == OpCode.GT:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a > b)
            self.pc += 1
        
        elif opcode == OpCode.LE:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a <= b)
            self.pc += 1
        
        elif opcode == OpCode.GE:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a >= b)
            self.pc += 1
        
        elif opcode == OpCode.AND:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(bool(a) and bool(b))
            self.pc += 1
        
        elif opcode == OpCode.OR:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(bool(a) or bool(b))
            self.pc += 1
        
        elif opcode == OpCode.NOT:
            a = self.stack.pop()
            self.stack.append(not bool(a))
            self.pc += 1
        
        elif opcode == OpCode.JMP:
            # JMP offset (2 bytes)
            offset = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            self.pc = offset
            return
        
        elif opcode == OpCode.JMP_IF_TRUE:
            # JMP_IF_TRUE offset (2 bytes)
            offset = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            cond = self.stack.pop()
            if bool(cond):
                self.pc = offset
            else:
                self.pc += 3
        
        elif opcode == OpCode.JMP_IF_FALSE:
            # JMP_IF_FALSE offset (2 bytes)
            offset = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            cond = self.stack.pop()
            if not bool(cond):
                self.pc = offset
            else:
                self.pc += 3
        
        elif opcode == OpCode.CALL:
            # CALL name_idx arg_count (2 bytes)
            name_idx = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            name = self.names[name_idx]
            
            # 获取参数
            arg_count = name_idx  # 简化：实际应该是另一个字节
            args = []
            for _ in range(arg_count):
                args.insert(0, self.stack.pop())
            
            # 调用函数
            if name in self.builtins:
                result = self.builtins[name](args)
                self.stack.append(result)
            
            self.pc += 3
        
        elif opcode == OpCode.PRINT:
            value = self.stack.pop()
            print(value)
            self.pc += 1
        
        elif opcode == OpCode.LIST:
            # LIST count (1 byte)
            count = self.code[self.pc + 1]
            items = []
            for _ in range(count):
                items.insert(0, self.stack.pop())
            self.stack.append(items)
            self.pc += 2
        
        elif opcode == OpCode.DICT:
            # DICT count (1 byte)
            count = self.code[self.pc + 1]
            d = {}
            for _ in range(count):
                value = self.stack.pop()
                key = self.stack.pop()
                d[key] = value
            self.stack.append(d)
            self.pc += 2
        
        elif opcode == OpCode.INDEX_GET:
            idx = self.stack.pop()
            obj = self.stack.pop()
            if isinstance(obj, list) and isinstance(idx, int):
                self.stack.append(obj[idx])
            elif isinstance(obj, dict):
                self.stack.append(obj.get(idx, None))
            else:
                self.stack.append(None)
            self.pc += 1
        
        elif opcode == OpCode.NEW:
            # NEW class_idx arg_count (2 bytes)
            class_idx = (self.code[self.pc + 1] << 8) | self.code[self.pc + 2]
            class_name = self.names[class_idx]
            self.stack.append(f"<instance of {class_name}>")
            self.pc += 3
        
        elif opcode == OpCode.RETURN:
            self.pc = len(self.code)  # 结束执行
        
        elif opcode == OpCode.HALT:
            self.pc = len(self.code)  # 结束执行
        
        elif opcode == OpCode.NOP:
            self.pc += 1
        
        else:
            print(f"未知操作码: 0x{opcode:02X}")
            self.pc += 1

# =============================================================================
# 性能测试
# =============================================================================

def benchmark():
    """性能基准测试"""
    import time
    
    # 测试代码：计算斐波那契数列
    test_code = """
定义 n 等于 30。
定义 a 等于 0。
定义 b 等于 1。
定义 i 等于 2。
当 i 小于等于 n:
    定义 c 等于 a 加 b。
    a 等于 b。
    b 等于 c。
    i 等于 i 加 1。
结束。
打印(b)。
"""
    
    from light_visitor import parse_source
    
    print("=== 字节码解释器性能测试 ===")
    
    # 解析代码
    module = parse_source(test_code)
    if not module:
        print("解析失败")
        return
    
    # 编译为字节码
    compiler = BytecodeCompiler()
    chunk = compiler.compile(module)
    
    # 运行测试
    vm = BytecodeVM()
    vm.load(chunk)
    
    start = time.time()
    for _ in range(1000):
        vm.stack = []
        vm.pc = 0
        vm.run()
    end = time.time()
    
    duration = end - start
    ops_per_second = int(1000 / duration)
    
    print(f"运行 1000 次斐波那契(30)测试:")
    print(f"  耗时: {duration:.3f} 秒")
    print(f"  速度: {ops_per_second:,} 次/秒")

if __name__ == "__main__":
    benchmark()