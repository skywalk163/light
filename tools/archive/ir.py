"""
光明（Light）编程语言 - 中间表示（IR）系统

使用三地址码（Three-Address Code）作为中间表示，便于后续优化和代码生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Set

# =============================================================================
# 三地址码操作码
# =============================================================================

class OpCode:
    """操作码定义"""
    # 算术运算
    ADD = 'add'      # t = a + b
    SUB = 'sub'      # t = a - b
    MUL = 'mul'      # t = a * b
    DIV = 'div'      # t = a / b
    MOD = 'mod'      # t = a % b
    
    # 比较运算
    EQ = 'eq'        # t = (a == b)
    NE = 'ne'        # t = (a != b)
    LT = 'lt'        # t = (a < b)
    GT = 'gt'        # t = (a > b)
    LE = 'le'        # t = (a <= b)
    GE = 'ge'        # t = (a >= b)
    
    # 逻辑运算
    AND = 'and'      # t = a && b
    OR = 'or'        # t = a || b
    NOT = 'not'      # t = !a
    
    # 位运算
    BIT_AND = 'bit_and'  # t = a & b
    BIT_OR = 'bit_or'    # t = a | b
    BIT_XOR = 'bit_xor'  # t = a ^ b
    SHL = 'shl'          # t = a << b
    SHR = 'shr'          # t = a >> b
    
    # 内存操作
    LOAD = 'load'    # t = *a (从内存加载)
    STORE = 'store'  # *a = b (存储到内存)
    LOAD_CONST = 'load_const'  # t = constant
    
    # 栈操作
    PUSH = 'push'    # push a to stack
    POP = 'pop'      # pop from stack to t
    
    # 控制流
    JUMP = 'jump'    # goto label
    JUMP_IF = 'jump_if'  # if a goto label
    JUMP_IF_FALSE = 'jump_if_false'  # if !a goto label
    
    # 函数调用
    CALL = 'call'    # call function
    RETURN = 'return'  # return value
    
    # 参数传递
    PARAM = 'param'  # pass parameter
    
    # 地址操作
    ADDRESS_OF = 'addr_of'  # t = &a
    POINTER_ADD = 'ptr_add'  # t = a + b (指针加法)
    
    # 类型转换
    CAST = 'cast'    # t = (type)a

# =============================================================================
# IR值（操作数）
# =============================================================================

@dataclass
class IRValue:
    """IR值基类"""
    pass

@dataclass
class Temp(IRValue):
    """临时变量"""
    name: str = ""
    
    def __repr__(self):
        return self.name

@dataclass
class Label(IRValue):
    """标签"""
    name: str = ""
    
    def __repr__(self):
        return f".{self.name}"

@dataclass
class Const(IRValue):
    """常量"""
    value: Union[int, float, str, bool] = 0
    type: str = "int"  # 'int', 'float', 'string', 'bool'
    
    def __repr__(self):
        if self.type == "string":
            return f'"{self.value}"'
        return str(self.value)

@dataclass
class Variable(IRValue):
    """变量引用"""
    name: str = ""
    offset: Optional[int] = None  # 栈偏移或全局地址
    
    def __repr__(self):
        if self.offset is not None:
            return f"{self.name}"
        return self.name

@dataclass
class Parameter(IRValue):
    """函数参数"""
    index: int = 0  # 参数索引（从0开始）
    
    def __repr__(self):
        return f"param_{self.index}"

@dataclass
class Memory(IRValue):
    """内存地址"""
    base: IRValue = None
    offset: Optional[int] = None  # 可选的常量偏移
    
    def __repr__(self):
        if self.offset is not None:
            return f"*{self.base} + {self.offset}"
        return f"*{self.base}"

# =============================================================================
# 三地址码指令
# =============================================================================

@dataclass
class Instruction:
    """三地址码指令"""
    op: str = ""           # 操作码
    dest: Optional[IRValue] = None   # 目标（可选）
    args: List[IRValue] = field(default_factory=list)  # 操作数
    label: Optional[str] = None  # 指令标签（用于跳转）
    
    def __repr__(self):
        parts = []
        if self.label:
            parts.append(f"{self.label}:")
        
        parts.append(self.op)
        
        if self.dest:
            parts.append(f"{self.dest} =")
        
        if self.args:
            parts.append(", ".join(repr(arg) for arg in self.args))
        
        return " ".join(parts)

# =============================================================================
# 基本块
# =============================================================================

@dataclass
class BasicBlock:
    """基本块"""
    name: str = ""
    instructions: List[Instruction] = field(default_factory=list)
    predecessors: Set[str] = field(default_factory=set)
    successors: Set[str] = field(default_factory=set)
    
    # 数据流信息
    def_uses: Dict[str, Set[int]] = field(default_factory=dict)  # var -> {def sites}
    live_in: Set[str] = field(default_factory=set)
    live_out: Set[str] = field(default_factory=set)
    
    def add_instruction(self, instr: Instruction):
        """添加指令"""
        self.instructions.append(instr)
    
    def __repr__(self):
        lines = [f"=== {self.name} ==="]
        for instr in self.instructions:
            lines.append(f"  {instr}")
        return "\n".join(lines)

# =============================================================================
# 函数IR
# =============================================================================

@dataclass
class FunctionIR:
    """函数的IR表示"""
    name: str = ""
    parameters: List[str] = field(default_factory=list)
    basic_blocks: Dict[str, BasicBlock] = field(default_factory=dict)
    entry_block: str = ""
    exit_block: str = ""
    
    # 变量信息
    temp_count: int = 0
    locals_count: int = 0
    stack_size: int = 0
    
    def new_temp(self) -> Temp:
        """创建新的临时变量"""
        temp = Temp(f"%t{self.temp_count}")
        self.temp_count += 1
        return temp
    
    def new_block(self, name: Optional[str] = None) -> BasicBlock:
        """创建新的基本块"""
        if name is None:
            name = f"bb{len(self.basic_blocks)}"
        
        block = BasicBlock(name=name)
        self.basic_blocks[name] = block
        
        if not self.entry_block:
            self.entry_block = name
        
        return block
    
    def add_block(self, block: BasicBlock):
        """添加基本块"""
        self.basic_blocks[block.name] = block
        if not self.entry_block:
            self.entry_block = block.name
    
    def get_block(self, name: str) -> Optional[BasicBlock]:
        """获取基本块"""
        return self.basic_blocks.get(name)
    
    def __repr__(self):
        lines = [f"function {self.name}({', '.join(self.parameters)})"]
        for block in self.basic_blocks.values():
            lines.append(repr(block))
        return "\n".join(lines)

# =============================================================================
# 模块IR
# =============================================================================

@dataclass
class ModuleIR:
    """模块的IR表示"""
    functions: Dict[str, FunctionIR] = field(default_factory=dict)
    global_vars: Dict[str, Const] = field(default_factory=dict)
    string_constants: Dict[str, int] = field(default_factory=dict)  # 字符串 -> 偏移
    
    def add_function(self, func: FunctionIR):
        """添加函数"""
        self.functions[func.name] = func
    
    def get_function(self, name: str) -> Optional[FunctionIR]:
        """获取函数"""
        return self.functions.get(name)
    
    def add_string_constant(self, string: str) -> int:
        """添加字符串常量并返回偏移"""
        if string not in self.string_constants:
            offset = sum(len(s) + 1 for s in self.string_constants.keys())
            self.string_constants[string] = offset
        return self.string_constants[string]
    
    def __repr__(self):
        lines = ["=== Module IR ==="]
        for func in self.functions.values():
            lines.append(repr(func))
            lines.append("")
        return "\n".join(lines)

# =============================================================================
# IR生成器（从AST生成IR）
# =============================================================================

class IRGenerator:
    """从AST生成三地址码IR"""
    
    def __init__(self):
        self.module = ModuleIR()
        self.current_function: Optional[FunctionIR] = None
        self.current_block: Optional[BasicBlock] = None
        self.label_count = 0
    
    def new_label(self) -> str:
        """创建新标签"""
        label = f"L{self.label_count}"
        self.label_count += 1
        return label
    
    def visit_Module(self, ast_module):
        """访问AST模块"""
        # 处理全局变量
        for global_var in ast_module.globals:
            if global_var.initializer:
                const_val = self.visit(global_var.initializer)
                if isinstance(const_val, Const):
                    self.module.global_vars[global_var.name] = const_val
        
        # 处理函数
        for func in ast_module.functions:
            self.visit_FunctionDefinition(func)
    
    def visit_FunctionDefinition(self, node):
        """访问函数定义"""
        func_ir = FunctionIR(name=node.name)
        func_ir.parameters = [p.name for p in node.parameters]
        self.current_function = func_ir
        
        # 创建入口块
        entry_block = func_ir.new_block("entry")
        self.current_block = entry_block
        
        # 访问函数体
        if node.body:
            self.visit_Block(node.body)
        
        # 添加返回指令（如果没有的话）
        if not self.current_block.instructions or \
           self.current_block.instructions[-1].op != OpCode.RETURN:
            self.current_block.add_instruction(
                Instruction(op=OpCode.RETURN, args=[Const(0, "int")])
            )
        
        self.module.add_function(func_ir)
        self.current_function = None
    
    def visit_Block(self, node):
        """访问代码块"""
        for stmt in node.statements:
            self.visit(stmt)
    
    def visit_VariableDeclaration(self, node):
        """访问变量声明"""
        if node.initializer:
            val = self.visit(node.initializer)
            # 在IR层面，变量声明就是赋值
            var = Variable(node.name)
            self.current_block.add_instruction(
                Instruction(op=OpCode.STORE, dest=var, args=[val])
            )
    
    def visit_Assignment(self, node):
        """访问赋值语句"""
        val = self.visit(node.value)
        target = self.visit(node.target)
        self.current_block.add_instruction(
            Instruction(op=OpCode.STORE, dest=target, args=[val])
        )
    
    def visit_Identifier(self, node):
        """访问标识符"""
        return Variable(node.name)
    
    def visit_NumberLiteral(self, node):
        """访问数字字面量"""
        if isinstance(node.value, int):
            return Const(node.value, "int")
        else:
            return Const(node.value, "float")
    
    def visit_StringLiteral(self, node):
        """访问字符串字面量"""
        offset = self.module.add_string_constant(node.value)
        return Const(offset, "string")
    
    def visit_BooleanLiteral(self, node):
        """访问布尔字面量"""
        return Const(1 if node.value else 0, "int")  # 用整数表示布尔值
    
    def visit_BinaryOp(self, node):
        """访问二元运算"""
        left = self.visit(node.left)
        right = self.visit(node.right)
        result = self.current_function.new_temp()
        
        op_map = {
            '+': OpCode.ADD,
            '-': OpCode.SUB,
            '*': OpCode.MUL,
            '/': OpCode.DIV,
            '%': OpCode.MOD,
            '==': OpCode.EQ,
            '!=': OpCode.NE,
            '<': OpCode.LT,
            '>': OpCode.GT,
            '<=': OpCode.LE,
            '>=': OpCode.GE,
            '&&': OpCode.AND,
            '||': OpCode.OR,
        }
        
        op = op_map.get(node.operator)
        if op:
            self.current_block.add_instruction(
                Instruction(op=op, dest=result, args=[left, right])
            )
        
        return result
    
    def visit_UnaryOp(self, node):
        """访问一元运算"""
        operand = self.visit(node.operand)
        result = self.current_function.new_temp()
        
        op_map = {
            '-': OpCode.SUB,  # 转换为 0 - operand
            '!': OpCode.NOT,
            '&': OpCode.ADDRESS_OF,
            '*': OpCode.LOAD,
        }
        
        op = op_map.get(node.operator)
        if op == OpCode.SUB:
            # 负号转换为 0 - operand
            self.current_block.add_instruction(
                Instruction(op=op, dest=result, args=[Const(0, "int"), operand])
            )
        elif op:
            self.current_block.add_instruction(
                Instruction(op=op, dest=result, args=[operand])
            )
        
        return result
    
    def visit_FunctionCall(self, node):
        """访问函数调用"""
        # 生成参数指令
        args = []
        for arg in node.arguments:
            args.append(self.visit(arg))
        
        # 生成参数传递指令
        for i, arg in enumerate(args):
            self.current_block.add_instruction(
                Instruction(op=OpCode.PARAM, args=[arg])
            )
        
        # 生成调用指令
        result = self.current_function.new_temp()
        callee_name = node.callee.name if isinstance(node.callee, Identifier) else "unknown"
        self.current_block.add_instruction(
            Instruction(op=OpCode.CALL, dest=result, args=[Const(callee_name, "string")])
        )
        
        return result
    
    def visit_IfStatement(self, node):
        """访问条件语句"""
        # 计算条件
        cond = self.visit(node.condition)
        
        # 创建基本块
        then_block = self.current_function.new_block()
        else_block = self.current_function.new_block() if node.else_block else None
        end_block = self.current_function.new_block()
        
        # 条件跳转
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP_IF_FALSE, args=[cond, Label(else_block.name if else_block else end_block.name)])
        )
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP, args=[Label(then_block.name)])
        )
        
        # 切换到then块
        self.current_block = then_block
        self.visit(node.then_block)
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP, args=[Label(end_block.name)])
        )
        
        # 切换到else块（如果存在）
        if else_block:
            self.current_block = else_block
            self.visit(node.else_block)
            self.current_block.add_instruction(
                Instruction(op=OpCode.JUMP, args=[Label(end_block.name)])
            )
        
        # 切换到end块
        self.current_block = end_block
    
    def visit_WhileStatement(self, node):
        """访问while循环"""
        # 创建基本块
        loop_block = self.current_function.new_block()
        body_block = self.current_function.new_block()
        end_block = self.current_function.new_block()
        
        # 跳转到循环条件检查
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP, args=[Label(loop_block.name)])
        )
        
        # 循环条件检查块
        self.current_block = loop_block
        cond = self.visit(node.condition)
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP_IF_FALSE, args=[cond, Label(end_block.name)])
        )
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP, args=[Label(body_block.name)])
        )
        
        # 循环体块
        self.current_block = body_block
        self.visit(node.body)
        self.current_block.add_instruction(
            Instruction(op=OpCode.JUMP, args=[Label(loop_block.name)])
        )
        
        # 结束块
        self.current_block = end_block
    
    def visit_ReturnStatement(self, node):
        """访问返回语句"""
        if node.value:
            val = self.visit(node.value)
        else:
            val = Const(0, "int")
        
        self.current_block.add_instruction(
            Instruction(op=OpCode.RETURN, args=[val])
        )
    
    def visit_PrintStatement(self, node):
        """访问打印语句"""
        val = self.visit(node.value)
        # 调用打印函数
        self.current_block.add_instruction(Instruction(op=OpCode.PARAM, args=[val]))
        self.current_block.add_instruction(
            Instruction(op=OpCode.CALL, args=[Const("print", "string")])
        )
    
    def visit(self, node):
        """调度访问方法"""
        if node is None:
            return None
        
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, lambda n: None)
        return method(node)
    
    def generate(self, ast_module) -> ModuleIR:
        """生成IR"""
        self.visit(ast_module)
        return self.module

# =============================================================================
# IR优化（简单优化）
# =============================================================================

class IROptimizer:
    """IR优化器"""
    
    @staticmethod
    def optimize(module: ModuleIR) -> ModuleIR:
        """优化模块IR"""
        for func in module.functions.values():
            IROptimizer.optimize_function(func)
        return module
    
    @staticmethod
    def optimize_function(func: FunctionIR):
        """优化函数IR"""
        # 简单的常量传播
        IROptimizer.constant_propagation(func)
        
        # 删除死代码
        IROptimizer.dead_code_elimination(func)
    
    @staticmethod
    def constant_propagation(func: FunctionIR):
        """常量传播优化"""
        for block in func.basic_blocks.values():
            constants = {}  # temp -> constant value
            
            for instr in block.instructions:
                # 如果是常量赋值
                if instr.op == OpCode.LOAD_CONST and isinstance(instr.dest, Temp):
                    constants[instr.dest.name] = instr.args[0]
                
                # 替换使用常量的地方
                for i, arg in enumerate(instr.args):
                    if isinstance(arg, Temp) and arg.name in constants:
                        instr.args[i] = constants[arg.name]
    
    @staticmethod
    def dead_code_elimination(func: FunctionIR):
        """死代码消除"""
        # 简单实现：删除未使用的赋值
        for block in func.basic_blocks.values():
            used_temps = set()
            
            # 收集所有使用的临时变量
            for instr in block.instructions:
                for arg in instr.args:
                    if isinstance(arg, Temp):
                        used_temps.add(arg.name)
            
            # 删除未使用的赋值
            new_instructions = []
            for instr in block.instructions:
                if instr.dest and isinstance(instr.dest, Temp):
                    if instr.dest.name in used_temps or instr.op == OpCode.STORE:
                        new_instructions.append(instr)
                else:
                    new_instructions.append(instr)
            
            block.instructions = new_instructions

# =============================================================================
# 测试IR生成器
# =============================================================================

def test_ir_generator():
    """测试IR生成器"""
    from ast_unified import Module, FunctionDefinition, Parameter, Block, \
        VariableDeclaration, Assignment, Identifier, NumberLiteral, BinaryOp, \
        ReturnStatement, TYPE_INT
    
    # 创建测试模块
    module = Module(name="test")
    
    func_body = Block(statements=[
        VariableDeclaration(
            name="x",
            type=TYPE_INT,
            initializer=NumberLiteral(value=42)
        ),
        Assignment(
            target=Identifier(name="x"),
            value=BinaryOp(
                left=Identifier(name="x"),
                operator="+",
                right=NumberLiteral(value=1)
            )
        ),
        ReturnStatement(
            value=Identifier(name="x")
        )
    ])
    
    func = FunctionDefinition(
        name="add_one",
        parameters=[Parameter(name="n", type=TYPE_INT)],
        return_type=TYPE_INT,
        body=func_body
    )
    
    module.functions.append(func)
    
    # 生成IR
    generator = IRGenerator()
    ir_module = generator.generate(module)
    
    print("=== 生成的IR ===")
    print(ir_module)
    
    # 优化IR
    optimized = IROptimizer.optimize(ir_module)
    print("\n=== 优化后的IR ===")
    print(optimized)

if __name__ == "__main__":
    test_ir_generator()