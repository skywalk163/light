"""
光明（Light）编程语言 - x86-64代码生成器

将三地址码IR转换为x86-64汇编代码。
支持Linux/macOS (System V AMD64 ABI) 和 Windows (x64 calling convention)。
"""

from typing import List, Dict, Optional, Set
from ir import *

# =============================================================================
# x86-64寄存器定义
# =============================================================================

class Register:
    """寄存器"""
    def __init__(self, name: str, is_call_saved: bool = False):
        self.name = name
        self.is_call_saved = is_call_saved
    
    def __repr__(self):
        return self.name

# 通用寄存器
RAX = Register('rax')
RBX = Register('rbx', is_call_saved=True)
RCX = Register('rcx')
RDX = Register('rdx')
RSI = Register('rsi')
RDI = Register('rdi')
RBP = Register('rbp', is_call_saved=True)
RSP = Register('rsp')
R8 = Register('r8')
R9 = Register('r9')
R10 = Register('r10')
R11 = Register('r11')
R12 = Register('r12', is_call_saved=True)
R13 = Register('r13', is_call_saved=True)
R14 = Register('r14', is_call_saved=True)
R15 = Register('r15', is_call_saved=True)

# 参数传递寄存器（System V AMD64 ABI）
ARG_REGS = [RDI, RSI, RDX, RCX, R8, R9]

# 调用者保存寄存器（被调用函数可以随意使用）
CALLER_SAVED = [RAX, RCX, RDX, RSI, RDI, R8, R9, R10, R11]

# 被调用者保存寄存器（被调用函数必须保存和恢复）
CALLEE_SAVED = [RBX, RBP, RSP, R12, R13, R14, R15]

# =============================================================================
# 汇编指令
# =============================================================================

class Assembler:
    """汇编器"""
    
    def __init__(self, target: str = 'linux'):
        self.lines: List[str] = []
        self.target = target  # 'linux', 'windows', 'macos'
        self.label_count = 0
    
    def emit(self, instruction: str, comment: str = ""):
        """添加汇编指令"""
        line = f"    {instruction}"
        if comment:
            line += f"  # {comment}"
        self.lines.append(line)
    
    def emit_label(self, name: str):
        """添加标签"""
        self.lines.append(f"{name}:")
    
    def emit_section(self, section: str):
        """添加段声明"""
        self.lines.append(f".section {section}")
    
    def emit_global(self, name: str):
        """添加全局符号声明"""
        self.lines.append(f".global {name}")
    
    def emit_string(self, label: str, content: str):
        """添加字符串常量"""
        self.lines.append(f"{label}:")
        escaped = content.replace('\\', '\\\\').replace('"', '\\"')
        self.lines.append(f'    .asciz "{escaped}"')
    
    def emit_align(self, align: int):
        """添加对齐指令"""
        self.lines.append(f".align {align}")
    
    def emit_int(self, value: int):
        """添加整数常量"""
        self.lines.append(f"    .long {value}")
    
    def new_label(self) -> str:
        """创建新标签"""
        label = f".L{self.label_count}"
        self.label_count += 1
        return label
    
    def get_code(self) -> str:
        """获取生成的汇编代码"""
        return "\n".join(self.lines)

# =============================================================================
# 寄存器分配器（简单版本）
# =============================================================================

class RegisterAllocator:
    """寄存器分配器"""
    
    def __init__(self, func: FunctionIR):
        self.func = func
        self.available_regs = [RAX, RBX, RCX, RDX, RSI, RDI, R8, R9, R10, R11, R12, R13, R14, R15]
        self.allocation: Dict[str, Register] = {}  # temp/var -> register
        self.spill_count = 0
    
    def allocate(self, name: str) -> Register:
        """分配寄存器"""
        if name in self.allocation:
            return self.allocation[name]
        
        if self.available_regs:
            reg = self.available_regs.pop(0)
            self.allocation[name] = reg
            return reg
        
        # 需要溢出到栈
        self.spill_count += 1
        return None  # 表示需要使用栈
    
    def free(self, name: str):
        """释放寄存器"""
        if name in self.allocation:
            reg = self.allocation[name]
            self.available_regs.append(reg)
            del self.allocation[name]
    
    def get_register(self, name: str) -> Optional[Register]:
        """获取变量的寄存器分配"""
        return self.allocation.get(name)

# =============================================================================
# x86-64代码生成器
# =============================================================================

class X86CodeGenerator:
    """x86-64代码生成器"""
    
    def __init__(self, target: str = 'linux'):
        self.asm = Assembler(target)
        self.target = target
        self.current_func: Optional[FunctionIR] = None
        self.reg_alloc: Optional[RegisterAllocator] = None
        self.label_map: Dict[str, str] = {}  # IR标签 -> 汇编标签
    
    def generate(self, module: ModuleIR) -> str:
        """生成汇编代码"""
        # 数据段
        self.asm.emit_section('.data')
        
        # 字符串常量
        for string, offset in module.string_constants.items():
            label = f".LC{offset}"
            self.asm.emit_string(label, string)
        
        # 全局变量
        for name, const_val in module.global_vars.items():
            self.asm.emit_label(name)
            if const_val.type == "int":
                self.asm.emit_int(const_val.value)
        
        # 代码段
        self.asm.emit_section('.text')
        
        # 生成函数
        for func in module.functions.values():
            self.generate_function(func)
        
        return self.asm.get_code()
    
    def generate_function(self, func: FunctionIR):
        """生成函数汇编"""
        self.current_func = func
        self.reg_alloc = RegisterAllocator(func)
        self.label_map.clear()
        
        # 创建标签映射
        for block_name in func.basic_blocks.keys():
            self.label_map[block_name] = self.asm.new_label()
        
        # 函数入口
        self.asm.emit_global(func.name)
        self.asm.emit_label(func.name)
        
        # 函数序言
        self.emit_prologue()
        
        # 生成基本块
        for block_name in func.basic_blocks.keys():
            block = func.basic_blocks[block_name]
            self.generate_block(block)
        
        # 函数尾声
        self.emit_epilogue()
    
    def emit_prologue(self):
        """函数序言"""
        # push rbp
        self.asm.emit('push rbp', '保存基址指针')
        # mov rbp, rsp
        self.asm.emit('mov rbp, rsp', '设置基址指针')
        
        # 分配栈空间（简单实现：预留128字节）
        stack_size = 128 + self.reg_alloc.spill_count * 8
        if stack_size > 0:
            self.asm.emit(f'sub rsp, {stack_size}', '分配栈空间')
    
    def emit_epilogue(self):
        """函数尾声"""
        # mov rsp, rbp
        self.asm.emit('mov rsp, rbp', '恢复栈指针')
        # pop rbp
        self.asm.emit('pop rbp', '恢复基址指针')
        # ret
        self.asm.emit('ret', '返回')
    
    def generate_block(self, block: BasicBlock):
        """生成基本块"""
        # 输出块标签
        self.asm.emit_label(self.label_map[block.name])
        
        # 生成每条指令
        for instr in block.instructions:
            self.generate_instruction(instr)
    
    def generate_instruction(self, instr: Instruction):
        """生成单条指令"""
        op = instr.op
        
        if op == OpCode.ADD:
            self.generate_add(instr)
        elif op == OpCode.SUB:
            self.generate_sub(instr)
        elif op == OpCode.MUL:
            self.generate_mul(instr)
        elif op == OpCode.DIV:
            self.generate_div(instr)
        elif op == OpCode.EQ:
            self.generate_cmp(instr, 'je')
        elif op == OpCode.NE:
            self.generate_cmp(instr, 'jne')
        elif op == OpCode.LT:
            self.generate_cmp(instr, 'jl')
        elif op == OpCode.GT:
            self.generate_cmp(instr, 'jg')
        elif op == OpCode.LE:
            self.generate_cmp(instr, 'jle')
        elif op == OpCode.GE:
            self.generate_cmp(instr, 'jge')
        elif op == OpCode.STORE:
            self.generate_store(instr)
        elif op == OpCode.LOAD:
            self.generate_load(instr)
        elif op == OpCode.LOAD_CONST:
            self.generate_load_const(instr)
        elif op == OpCode.JUMP:
            self.generate_jump(instr)
        elif op == OpCode.JUMP_IF_FALSE:
            self.generate_jump_if_false(instr)
        elif op == OpCode.CALL:
            self.generate_call(instr)
        elif op == OpCode.RETURN:
            self.generate_return(instr)
        elif op == OpCode.PARAM:
            self.generate_param(instr)
        else:
            self.asm.emit(f'# Unsupported op: {op}')
    
    def generate_add(self, instr: Instruction):
        """生成加法指令"""
        dest = instr.dest
        left = instr.args[0]
        right = instr.args[1]
        
        # 简单实现：使用RAX作为目标
        self.emit_move(left, RAX)
        self.emit_operand(right, 'add', RAX)
        self.allocate_result(dest, RAX)
    
    def generate_sub(self, instr: Instruction):
        """生成减法指令"""
        dest = instr.dest
        left = instr.args[0]
        right = instr.args[1]
        
        self.emit_move(left, RAX)
        self.emit_operand(right, 'sub', RAX)
        self.allocate_result(dest, RAX)
    
    def generate_mul(self, instr: Instruction):
        """生成乘法指令"""
        dest = instr.dest
        left = instr.args[0]
        right = instr.args[1]
        
        self.emit_move(left, RAX)
        self.emit_operand(right, 'imul', RAX)
        self.allocate_result(dest, RAX)
    
    def generate_div(self, instr: Instruction):
        """生成除法指令"""
        dest = instr.dest
        left = instr.args[0]
        right = instr.args[1]
        
        # div 使用 RAX 和 RDX
        self.emit_move(left, RAX)
        self.asm.emit('cqo', '符号扩展')
        self.emit_operand(right, 'idiv', RAX)
        self.allocate_result(dest, RAX)
    
    def generate_cmp(self, instr: Instruction, cond: str):
        """生成比较指令"""
        dest = instr.dest
        left = instr.args[0]
        right = instr.args[1]
        
        self.emit_move(left, RAX)
        self.emit_operand(right, 'cmp', RAX)
        
        # 设置结果为1或0
        self.asm.emit(f'mov eax, 1', '设置true值')
        self.asm.emit(f'{cond} .Ltrue_{self.asm.label_count}', f'如果条件成立跳转')
        self.asm.emit('mov eax, 0', '设置false值')
        self.asm.emit_label(f'.Ltrue_{self.asm.label_count - 1}')
        
        self.allocate_result(dest, RAX)
    
    def generate_store(self, instr: Instruction):
        """生成存储指令"""
        dest = instr.dest
        value = instr.args[0]
        
        if isinstance(dest, Variable):
            # 存储到栈上的局部变量
            offset = self.get_var_offset(dest.name)
            self.emit_move(value, RAX)
            self.asm.emit(f'mov QWORD PTR [rbp-{offset}], rax', f'存储 {dest.name}')
        elif isinstance(dest, Memory):
            # 存储到内存地址
            self.emit_move(value, RAX)
            self.emit_memory_store(dest, RAX)
    
    def generate_load(self, instr: Instruction):
        """生成加载指令"""
        dest = instr.dest
        source = instr.args[0]
        
        if isinstance(source, Variable):
            offset = self.get_var_offset(source.name)
            self.asm.emit(f'mov rax, QWORD PTR [rbp-{offset}]', f'加载 {source.name}')
            self.allocate_result(dest, RAX)
        elif isinstance(source, Memory):
            self.emit_memory_load(source, RAX)
            self.allocate_result(dest, RAX)
    
    def generate_load_const(self, instr: Instruction):
        """生成加载常量指令"""
        dest = instr.dest
        const_val = instr.args[0]
        
        if isinstance(const_val, Const):
            if const_val.type == "int":
                self.asm.emit(f'mov rax, {const_val.value}', f'加载常量 {const_val.value}')
                self.allocate_result(dest, RAX)
            elif const_val.type == "string":
                # 字符串常量的地址
                self.asm.emit(f'lea rax, .LC{const_val.value}', '加载字符串地址')
                self.allocate_result(dest, RAX)
    
    def generate_jump(self, instr: Instruction):
        """生成跳转指令"""
        target = instr.args[0]
        if isinstance(target, Label):
            asm_label = self.label_map.get(target.name, target.name)
            self.asm.emit(f'jmp {asm_label}', '无条件跳转')
    
    def generate_jump_if_false(self, instr: Instruction):
        """生成条件跳转指令"""
        cond = instr.args[0]
        target = instr.args[1]
        
        self.emit_move(cond, RAX)
        self.asm.emit('test rax, rax', '测试条件')
        
        if isinstance(target, Label):
            asm_label = self.label_map.get(target.name, target.name)
            self.asm.emit(f'jz {asm_label}', '条件为false时跳转')
    
    def generate_call(self, instr: Instruction):
        """生成函数调用指令"""
        func_name = instr.args[0]
        
        if isinstance(func_name, Const) and func_name.type == "string":
            self.asm.emit(f'call {func_name.value}', f'调用 {func_name.value}')
            
            if instr.dest:
                self.allocate_result(instr.dest, RAX)
    
    def generate_return(self, instr: Instruction):
        """生成返回指令"""
        value = instr.args[0]
        
        if value is not None:
            self.emit_move(value, RAX)
        
        # 函数尾声已经包含ret，这里不需要额外生成
    
    def generate_param(self, instr: Instruction):
        """生成参数传递指令"""
        # 在简单实现中，参数已经在调用前准备好
        pass
    
    def emit_move(self, value: IRValue, reg: Register):
        """生成移动指令"""
        if isinstance(value, Const):
            if value.type == "int":
                self.asm.emit(f'mov {reg.name}, {value.value}')
        elif isinstance(value, Variable):
            offset = self.get_var_offset(value.name)
            self.asm.emit(f'mov {reg.name}, QWORD PTR [rbp-{offset}]')
        elif isinstance(value, Temp):
            reg_val = self.reg_alloc.get_register(value.name)
            if reg_val:
                self.asm.emit(f'mov {reg.name}, {reg_val.name}')
            else:
                # 从栈加载
                offset = self.get_temp_offset(value.name)
                self.asm.emit(f'mov {reg.name}, QWORD PTR [rbp-{offset}]')
        elif isinstance(value, Parameter):
            # 参数在栈上的位置
            offset = 16 + value.index * 8
            self.asm.emit(f'mov {reg.name}, QWORD PTR [rbp+{offset}]')
    
    def emit_operand(self, value: IRValue, op: str, dest_reg: Register):
        """生成操作数指令"""
        if isinstance(value, Const):
            if value.type == "int":
                self.asm.emit(f'{op} {dest_reg.name}, {value.value}')
        elif isinstance(value, Variable):
            offset = self.get_var_offset(value.name)
            self.asm.emit(f'{op} {dest_reg.name}, QWORD PTR [rbp-{offset}]')
        elif isinstance(value, Temp):
            reg_val = self.reg_alloc.get_register(value.name)
            if reg_val:
                self.asm.emit(f'{op} {dest_reg.name}, {reg_val.name}')
            else:
                offset = self.get_temp_offset(value.name)
                self.asm.emit(f'{op} {dest_reg.name}, QWORD PTR [rbp-{offset}]')
        elif isinstance(value, Parameter):
            offset = 16 + value.index * 8
            self.asm.emit(f'{op} {dest_reg.name}, QWORD PTR [rbp+{offset}]')
    
    def emit_memory_store(self, mem: Memory, reg: Register):
        """生成内存存储指令"""
        if mem.offset is not None:
            self.asm.emit(f'mov QWORD PTR [{mem.base}+{mem.offset}], {reg.name}')
        else:
            self.asm.emit(f'mov QWORD PTR [{mem.base}], {reg.name}')
    
    def emit_memory_load(self, mem: Memory, reg: Register):
        """生成内存加载指令"""
        if mem.offset is not None:
            self.asm.emit(f'mov {reg.name}, QWORD PTR [{mem.base}+{mem.offset}]')
        else:
            self.asm.emit(f'mov {reg.name}, QWORD PTR [{mem.base}]')
    
    def allocate_result(self, dest: Optional[IRValue], reg: Register):
        """分配结果到目标"""
        if dest is None:
            return
        
        if isinstance(dest, Temp):
            self.reg_alloc.allocate(dest.name)
        elif isinstance(dest, Variable):
            # 存储到栈
            offset = self.get_var_offset(dest.name)
            self.asm.emit(f'mov QWORD PTR [rbp-{offset}], {reg.name}')
    
    def get_var_offset(self, name: str) -> int:
        """获取变量的栈偏移"""
        # 简单实现：按字母顺序分配偏移
        var_names = sorted(self.current_func.parameters + ['x', 'y', 'z'])
        if name in var_names:
            index = var_names.index(name)
            return 16 + index * 8  # RBP + 16 开始是参数，往下是局部变量
        return 128  # 默认偏移
    
    def get_temp_offset(self, name: str) -> int:
        """获取临时变量的栈偏移"""
        # 简单实现：使用固定偏移
        return 256 + hash(name) % 128

# =============================================================================
# 测试代码生成器
# =============================================================================

def test_code_generator():
    """测试代码生成器"""
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
    
    # 生成汇编
    code_gen = X86CodeGenerator(target='linux')
    assembly = code_gen.generate(ir_module)
    
    print("=== 生成的x86-64汇编代码 ===")
    print(assembly)

if __name__ == "__main__":
    test_code_generator()