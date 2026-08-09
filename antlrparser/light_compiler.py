"""光明编译器主程序"""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from light_visitor import parse_source
from light_llvm import LLVMCodeGen


def compile_light(source_code: str, output_name: str = "a"):
    """
    将光明源代码编译为可执行文件
    
    Args:
        source_code: 光明源代码
        output_name: 输出文件名（不含扩展名）
    """
    print(f"光明编译器 v0.1")
    print("=" * 70)
    
    # 1. 解析源代码
    print("1. 解析源代码...")
    try:
        module = parse_source(source_code)
        print(f"   ✓ 解析成功，{len(module.segments)} 个段落，{len(module.statements)} 个语句")
    except Exception as e:
        print(f"   ✗ 解析失败: {e}")
        return False
    
    # 2. 生成 LLVM IR
    print("2. 生成 LLVM IR...")
    try:
        codegen = LLVMCodeGen()
        ir = codegen.generate(module)
        ir_file = f"{output_name}.ll"
        with open(ir_file, "w", encoding="utf-8") as f:
            f.write(ir)
        print(f"   ✓ 生成成功，IR 文件: {ir_file}")
    except Exception as e:
        print(f"   ✗ IR 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 编译为可执行文件
    print("3. 编译为可执行文件...")
    clang_path = "E:/Program Files/LLVM/bin/clang.exe"
    runtime_lib = "g:/dumategithub/light/antlrparser/runtime/light_runtime.o"
    ir_file = f"{output_name}.ll"
    output_exe = f"{output_name}.exe"
    
    cmd = [
        clang_path,
        "-o", output_exe,
        ir_file,
        runtime_lib,
        "-lucrt",  # 链接 Universal C Runtime
        "-lmsvcrt",  # 链接 MSVC C 运行时
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            print(f"   ✓ 编译成功，可执行文件: {output_exe}")
        else:
            print(f"   ✗ 编译失败!")
            if result.stderr:
                print(f"   错误信息:\n{result.stderr}")
            if result.stdout:
                print(f"   标准输出:\n{result.stdout}")
            return False
    except Exception as e:
        print(f"   ✗ 编译异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("=" * 70)
    print("编译完成!")
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python light_compiler.py <源文件> [输出文件名]")
        print("示例: python light_compiler.py test.light myprog")
        sys.exit(1)
    
    source_file = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else "a"
    
    # 读取源文件
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到文件 {source_file}")
        sys.exit(1)
    
    # 编译
    success = compile_light(source_code, output_name)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()