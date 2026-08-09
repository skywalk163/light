#!/usr/bin/env python3
"""
光明 (Light) 编译器 - 命令行工具

用法:
  light compile <source.light> [-o <output>]
  light run <source.light>
  light parse <source.light>
  light --help

功能:
  compile   - 编译光明源代码为可执行文件
  run       - 解释执行光明源代码
  parse     - 解析并显示AST结构
"""

import argparse
import sys
import os
import subprocess

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def compile_light(source_file: str, output_name: str = "a"):
    """编译光明源代码"""
    from light_visitor import parse_source
    from light_llvm import LLVMCodeGen
    
    print(f"光明编译器 v0.1")
    print("=" * 70)
    
    # 1. 读取源文件
    print(f"读取源文件: {source_file}")
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        print(f"   ✓ 读取成功，{len(source_code)} 字符")
    except FileNotFoundError:
        print(f"   ✗ 错误：找不到文件 {source_file}")
        return False
    
    # 2. 解析源代码
    print("解析源代码...")
    try:
        module = parse_source(source_code)
        print(f"   ✓ 解析成功")
        print(f"     - 段落: {len(module.segments)}")
        print(f"     - 类: {len(module.classes)}")
        print(f"     - 接口: {len(module.interfaces)}")
        print(f"     - 语句: {len(module.statements)}")
    except Exception as e:
        print(f"   ✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 生成 LLVM IR
    print("生成 LLVM IR...")
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
    
    # 4. 编译为可执行文件
    print("编译为可执行文件...")
    clang_path = "E:/Program Files/LLVM/bin/clang.exe"
    runtime_lib = os.path.join(os.path.dirname(__file__), "runtime", "light_runtime.o")
    ir_file = f"{output_name}.ll"
    output_exe = f"{output_name}.exe"
    
    if not os.path.exists(runtime_lib):
        print(f"   ✗ 错误：找不到运行时库 {runtime_lib}")
        return False
    
    cmd = [clang_path, "-o", output_exe, ir_file, runtime_lib]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            print(f"   ✓ 编译成功，可执行文件: {output_exe}")
        else:
            print(f"   ✗ 编译失败!")
            if result.stderr:
                print(f"   错误信息:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"   ✗ 编译异常: {e}")
        return False
    
    print("=" * 70)
    print("编译完成!")
    return True

def run_light(source_file: str):
    """解释执行光明源代码"""
    from light_visitor import parse_source
    from self_hosted.interpreter import interpret
    
    print(f"光明解释器 v0.1")
    print("=" * 70)
    
    # 读取源文件
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {source_file}")
        return
    
    # 解析并执行
    try:
        module = parse_source(source_code)
        print(f"解析成功，开始执行...\n")
        interpret(module)
        print("\n✓ 执行完成")
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()

def parse_light(source_file: str):
    """解析并显示AST结构"""
    from light_visitor import parse_source
    
    print(f"光明解析器")
    print("=" * 70)
    
    # 读取源文件
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {source_file}")
        return
    
    # 解析
    try:
        module = parse_source(source_code)
        print(f"模块名: {module.name}")
        print(f"位置: 第{module.line}行, 第{module.column}列")
        print(f"\n【段落】({len(module.segments)})")
        for seg in module.segments:
            print(f"  - 《{seg.name}》段({len(seg.parameters)}参数)")
        
        print(f"\n【语句】({len(module.statements)})")
        for i, stmt in enumerate(module.statements[:10]):
            print(f"  {i+1}. {type(stmt).__name__}")
        if len(module.statements) > 10:
            print(f"  ... 还有 {len(module.statements) - 10} 个语句")
        
        print("\n✓ 解析完成")
    except Exception as e:
        print(f"\n✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(
        prog="light",
        description="光明 (Light) 编程语言 - 编译器和解释器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  light compile test.light -o myprogram   # 编译为可执行文件
  light run test.light                     # 解释执行
  light parse test.light                   # 解析并显示AST
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # compile 命令
    compile_parser = subparsers.add_parser("compile", help="编译光明源代码")
    compile_parser.add_argument("source", help="源文件路径")
    compile_parser.add_argument("-o", "--output", default="a", help="输出文件名（不含扩展名）")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="解释执行光明源代码")
    run_parser.add_argument("source", help="源文件路径")
    
    # parse 命令
    parse_parser = subparsers.add_parser("parse", help="解析并显示AST结构")
    parse_parser.add_argument("source", help="源文件路径")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "compile":
        success = compile_light(args.source, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == "run":
        run_light(args.source)
    
    elif args.command == "parse":
        parse_light(args.source)

if __name__ == "__main__":
    main()