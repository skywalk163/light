"""
光明（Light）编程语言 - 链接器和可执行文件生成器

支持：
- Linux ELF格式
- Windows PE/COFF格式
- macOS Mach-O格式
"""

import struct
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

# 导入IR和代码生成模块
from ir import IRGenerator, IROptimizer
from codegen_x64 import X86CodeGenerator

# =============================================================================
# 可执行文件格式抽象
# =============================================================================

class ExecutableFormat:
    """可执行文件格式抽象基类"""
    
    def __init__(self, target: str):
        self.target = target
        self.sections: List[Section] = []
        self.symbols: Dict[str, int] = {}
        self.relocations: List[Relocation] = []
    
    def add_section(self, name: str, data: bytes, flags: int = 0):
        """添加段"""
        section = Section(name, data, flags)
        self.sections.append(section)
        return section
    
    def add_symbol(self, name: str, offset: int, is_global: bool = False):
        """添加符号"""
        self.symbols[name] = Symbol(name, offset, is_global)
    
    def add_relocation(self, section_idx: int, offset: int, symbol_name: str, type: int):
        """添加重定位"""
        self.relocations.append(Relocation(section_idx, offset, symbol_name, type))
    
    def generate(self) -> bytes:
        """生成可执行文件字节流"""
        raise NotImplementedError

@dataclass
class Section:
    """段"""
    name: str = ""
    data: bytes = b""
    flags: int = 0  # 段标志（可执行、可写等）
    offset: int = 0
    size: int = 0

@dataclass
class Symbol:
    """符号"""
    name: str = ""
    offset: int = 0
    is_global: bool = False

@dataclass
class Relocation:
    """重定位"""
    section_idx: int = 0
    offset: int = 0
    symbol_name: str = ""
    type: int = 0

# =============================================================================
# ELF格式生成器（Linux）
# =============================================================================

class ELFFormat(ExecutableFormat):
    """ELF可执行文件格式"""
    
    def __init__(self):
        super().__init__('linux')
        self.e_ident = [0x7F, 0x45, 0x4C, 0x46]  # ELF魔数
        self.e_ident += [2]  # 64位
        self.e_ident += [1]  # 小端序
        self.e_ident += [1]  # ELF版本
        self.e_ident += [0] * 9  # 填充
    
    def generate(self) -> bytes:
        """生成ELF文件"""
        result = bytearray()
        
        # ELF头部
        result += bytes(self.e_ident)
        result += struct.pack('<HHI', 2, 3, 1)  # e_type, e_machine, e_version
        
        # 程序头和段头偏移
        phoff = 64  # 程序头偏移
        shoff = 64 + 56 * 2  # 段头偏移（假设2个程序头）
        
        result += struct.pack('<QQQIHHHHHH', 
            0,  # e_entry（入口点，稍后填充）
            phoff,
            shoff,
            0,  # e_flags
            64,  # e_ehsize
            56,  # e_phentsize
            2,  # e_phnum（2个程序段：代码和数据）
            64,  # e_shentsize
            len(self.sections) + 1,  # e_shnum（加上空段）
            0   # e_shstrndx
        )
        
        # 程序头
        text_section = self.sections[0] if self.sections else None
        data_section = self.sections[1] if len(self.sections) > 1 else None
        
        # 代码段程序头
        result += struct.pack('<IIQQQQQQ',
            1,  # PT_LOAD
            0,  # p_offset
            0x400000,  # p_vaddr（虚拟地址）
            0x400000,  # p_paddr
            len(text_section.data) if text_section else 0,
            len(text_section.data) if text_section else 0,
            5,  # p_flags（R+X）
            0x1000  # p_align
        )
        
        # 数据段程序头
        result += struct.pack('<IIQQQQQQ',
            1,  # PT_LOAD
            len(text_section.data) if text_section else 0,
            0x401000,  # p_vaddr
            0x401000,  # p_paddr
            len(data_section.data) if data_section else 0,
            len(data_section.data) if data_section else 0,
            6,  # p_flags（R+W）
            0x1000  # p_align
        )
        
        # 段内容
        if text_section:
            result += text_section.data
            # 对齐到页边界
            while len(result) % 0x1000 != 0:
                result += b'\x00'
        
        if data_section:
            result += data_section.data
            while len(result) % 0x1000 != 0:
                result += b'\x00'
        
        # 段头表（简化实现）
        # 空段
        result += struct.pack('<IIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0)
        
        for section in self.sections:
            result += struct.pack('<IIIIIIIIII',
                0,  # sh_name
                1 if section.name == '.text' else 3,  # sh_type
                5 if section.name == '.text' else 6,  # sh_flags
                0,  # sh_addr
                section.offset,
                len(section.data),
                0,  # sh_link
                0,  # sh_info
                0x1000,  # sh_addralign
                0   # sh_entsize
            )
        
        return bytes(result)

# =============================================================================
# PE格式生成器（Windows）
# =============================================================================

class PEFormat(ExecutableFormat):
    """PE/COFF可执行文件格式"""
    
    def __init__(self):
        super().__init__('windows')
    
    def generate(self) -> bytes:
        """生成PE文件"""
        result = bytearray()
        
        # DOS头部
        result += b'MZ'  # DOS魔数
        result += b'\x00' * 58  # DOS头部剩余部分
        result += struct.pack('<I', 64)  # e_lfanew（PE头部偏移）
        
        # PE头部
        result += b'PE\x00\x00'  # PE魔数
        
        # COFF文件头
        result += struct.pack('<HHIIIHH',
            0x8664,  # Machine (x64)
            2,  # NumberOfSections
            0,  # TimeDateStamp
            0,  # PointerToSymbolTable
            0,  # NumberOfSymbols
            40,  # SizeOfOptionalHeader
            0x0202  # Characteristics (Executable + 32-bit)
        )
        
        # PE可选头部
        result += struct.pack('<HH', 0x20B, 3)  # Magic (PE32+), MajorLinkerVersion
        
        result += struct.pack('<III',
            0,  # SizeOfCode
            0,  # SizeOfInitializedData
            0   # SizeOfUninitializedData
        )
        
        result += struct.pack('<II',
            0x1000,  # AddressOfEntryPoint
            0x1000   # BaseOfCode
        )
        
        result += struct.pack('<QQ',
            0x140000000,  # ImageBase
            0x1000,  # SectionAlignment
            0x200    # FileAlignment
        )
        
        result += struct.pack('<HH', 4, 0)  # MajorOperatingSystemVersion
        
        result += struct.pack('<IIII',
            0,  # SizeOfImage
            64 + 248,  # SizeOfHeaders
            0,  # CheckSum
            3   # Subsystem (Windows CUI)
        )
        
        result += struct.pack('<II', 0, 0)  # DllCharacteristics
        
        result += struct.pack('<QQ', 0x1000, 0x1000)  # SizeOfStackReserve/Commit
        
        result += struct.pack('<QQ', 0x1000, 0x1000)  # SizeOfHeapReserve/Commit
        
        result += struct.pack('<II', 0, 0)  # LoaderFlags, NumberOfRvaAndSizes
        
        # 数据目录表（简化）
        result += b'\x00' * 16 * 8
        
        # 段表
        # .text段
        result += b'.text\x00\x00\x00'
        text_section = self.sections[0] if self.sections else None
        text_size = len(text_section.data) if text_section else 0
        result += struct.pack('<IIIIIIII',
            text_size,  # VirtualSize
            0x1000,  # VirtualAddress
            ((text_size + 0x1FF) // 0x200) * 0x200,  # SizeOfRawData
            64 + 248 + 40 * 2,  # PointerToRawData
            0,  # PointerToRelocations
            0,  # PointerToLinenumbers
            0,  # NumberOfRelocations
            0,  # NumberOfLinenumbers
            0x60000020,  # Characteristics (Code + Execute + Read)
        )
        
        # .data段
        result += b'.data\x00\x00\x00'
        data_section = self.sections[1] if len(self.sections) > 1 else None
        data_size = len(data_section.data) if data_section else 0
        result += struct.pack('<IIIIIIII',
            data_size,
            0x2000,
            ((data_size + 0x1FF) // 0x200) * 0x200,
            64 + 248 + 40 * 2 + ((text_size + 0x1FF) // 0x200) * 0x200,
            0, 0, 0, 0,
            0xC0000040,  # Characteristics (Initialized Data + Read + Write)
        )
        
        # 段内容
        if text_section:
            result += text_section.data
            while len(result) % 0x200 != 0:
                result += b'\x00'
        
        if data_section:
            result += data_section.data
            while len(result) % 0x200 != 0:
                result += b'\x00'
        
        return bytes(result)

# =============================================================================
# 链接器
# =============================================================================

class Linker:
    """链接器"""
    
    def __init__(self, target: str = 'linux'):
        self.target = target
        self.object_files: List[ObjectFile] = []
        self.runtime_code = b""
        self.string_constants = b""
    
    def add_object_file(self, obj_file):
        """添加目标文件"""
        self.object_files.append(obj_file)
    
    def set_runtime_code(self, code: bytes):
        """设置运行时代码"""
        self.runtime_code = code
    
    def add_string_constants(self, strings: bytes):
        """添加字符串常量"""
        self.string_constants = strings
    
    def link(self) -> bytes:
        """链接并生成可执行文件"""
        # 收集所有段
        text_data = b""
        data_data = b""
        
        # 添加运行时代码
        text_data += self.runtime_code
        
        # 添加对象文件代码
        for obj in self.object_files:
            if hasattr(obj, 'text_section'):
                text_data += obj.text_section
            if hasattr(obj, 'data_section'):
                data_data += obj.data_section
        
        # 添加字符串常量
        data_data += self.string_constants
        
        # 创建可执行文件
        if self.target == 'linux':
            fmt = ELFFormat()
        elif self.target == 'windows':
            fmt = PEFormat()
        else:
            fmt = ELFFormat()  # 默认Linux
        
        fmt.add_section('.text', text_data, 5)  # 可执行
        fmt.add_section('.data', data_data, 6)  # 可读写
        
        return fmt.generate()

class ObjectFile:
    """目标文件抽象"""
    
    def __init__(self):
        self.text_section = b""
        self.data_section = b""
        self.symbols = {}
        self.relocations = []

# =============================================================================
# 汇编器封装
# =============================================================================

class AssemblerWrapper:
    """汇编器封装"""
    
    def __init__(self, target: str = 'linux'):
        self.target = target
        self.lines = []
        self.label_count = 0
    
    def emit(self, instr: str):
        """添加汇编指令"""
        self.lines.append(instr)
    
    def emit_label(self, name: str):
        """添加标签"""
        self.lines.append(f"{name}:")
    
    def new_label(self) -> str:
        """创建新标签"""
        label = f".L{self.label_count}"
        self.label_count += 1
        return label
    
    def assemble(self) -> bytes:
        """汇编为机器码（简化实现）"""
        # 这是一个简化的汇编器，实际需要使用外部汇编器如nasm/gcc
        # 这里返回汇编代码作为文本，实际使用时需要调用外部工具
        return "\n".join(self.lines).encode('utf-8')

# =============================================================================
# 编译器主入口
# =============================================================================

class LightCompiler:
    """光明编译器主类"""
    
    def __init__(self, target: str = 'linux'):
        self.target = target
        self.ir_generator = IRGenerator()
        self.code_generator = X86CodeGenerator(target)
    
    def compile(self, ast_module) -> bytes:
        """编译AST为可执行文件"""
        # 生成IR
        ir_module = self.ir_generator.generate(ast_module)
        
        # 优化IR
        ir_module = IROptimizer.optimize(ir_module)
        
        # 生成汇编代码
        assembly = self.code_generator.generate(ir_module)
        
        # 汇编为机器码（简化实现）
        asm_wrapper = AssemblerWrapper(self.target)
        for line in assembly.split('\n'):
            if line.strip():
                if line.endswith(':'):
                    asm_wrapper.emit_label(line[:-1])
                else:
                    asm_wrapper.emit(line)
        
        obj_file = ObjectFile()
        obj_file.text_section = asm_wrapper.assemble()
        
        # 链接
        linker = Linker(self.target)
        linker.add_object_file(obj_file)
        
        # 添加简单的运行时启动代码
        runtime = self._get_runtime_code()
        linker.set_runtime_code(runtime)
        
        return linker.link()
    
    def _get_runtime_code(self) -> bytes:
        """获取运行时代码"""
        # 简单的启动代码
        if self.target == 'linux':
            # Linux入口点
            return b'\x48\x89\xe5'  # push rbp; mov rbp, rsp
        elif self.target == 'windows':
            # Windows入口点
            return b'\x48\x89\xe5'  # push rbp; mov rbp, rsp
        return b''

# =============================================================================
# 测试编译器
# =============================================================================

def test_compiler():
    """测试编译器"""
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
    
    # 编译
    compiler = LightCompiler(target='linux')
    executable = compiler.compile(module)
    
    print(f"生成的可执行文件大小: {len(executable)} 字节")
    
    # 保存到文件
    with open('test_output.bin', 'wb') as f:
        f.write(executable)
    
    print("可执行文件已保存为 test_output.bin")

if __name__ == "__main__":
    test_compiler()