#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 统一命令行工具 v2.0

用法：
  light <源文件.light> [选项]
  light run <源文件.light>
  light compile <源文件.light> [-o <输出>]
  light repl
  light --help

示例：
  light hello.light                    # 编译并运行（使用ANTLR后端）
  light hello.light --backend src      # 使用src手写解析器
  light run hello.light                # 解释执行
  light compile hello.light -o hello.py
  light repl                          # 启动REPL
"""
import sys
import os
import argparse
from pathlib import Path
from typing import Optional, List

# 版本信息
try:
    from src.version import DEV_BRANCH, VERSION as LANG_VERSION, is_dev_branch, get_dev_version_string
    DEV_VERSION_STR = f'光明 v4.0dev-{LANG_VERSION} (开发分支)'
    STABLE_VERSION_STR = f'光明 v{LANG_VERSION}'
    VERSION_STR = DEV_VERSION_STR if is_dev_branch() else STABLE_VERSION_STR
except ImportError:
    VERSION_STR = '光明 v1.0.0'

# 添加路径 - 先尝试本地路径（开发模式），再尝试已安装路径
_local_src = str(Path(__file__).parent.parent / 'src')
_local_antlr = str(Path(__file__).parent.parent / 'antlrparser')

if os.path.isdir(_local_src):
    sys.path.insert(0, _local_src)
if os.path.isdir(_local_antlr):
    sys.path.insert(0, _local_antlr)

# 已安装版本（pip install），将 src 下模块暴露到顶层路径
try:
    import src as _src_pkg
    _installed_src = str(Path(_src_pkg.__file__).parent)
    if _installed_src not in sys.path and os.path.isdir(_installed_src):
        sys.path.insert(0, _installed_src)
except ImportError:
    pass


class LightUnifiedCLI:
    """光明统一CLI"""
    
    def __init__(self):
        self.antlr_available = self._check_antlr()
        self.src_available = self._check_src()
    
    def _check_antlr(self) -> bool:
        """检查ANTLR后端是否可用"""
        try:
            from antlr4 import InputStream, CommonTokenStream
            from LightLangLexer import LightLangLexer
            from LightLangParser import LightLangParser
            from light_visitor import LightLangASTBuilder
            from code_generator_unified import UnifiedCodeGenerator
            return True
        except ImportError:
            return False
    
    def _check_src(self) -> bool:
        """检查src手写解析器是否可用"""
        try:
            from lexer import Lexer
            from light_parser_v3 import LightParser
            from code_generator import PythonCodeGenerator
            return True
        except ImportError:
            return False
    
    def compile_with_antlr(self, source: str, output_file: Optional[str] = None, run: bool = False) -> int:
        """使用ANTLR后端编译"""
        from light_visitor import LightParser
        from code_generator_unified import UnifiedCodeGenerator
        
        # 使用 LightParser 进行完整的预处理（_auto_close_blocks、_preprocess_async 等）
        light_parser = LightParser()
        module = light_parser.parse(source)
        
        if light_parser.errors:
            for error in light_parser.errors:
                print(error, file=sys.stderr)
            return 1
        
        if module is None:
            print("[错误] 解析失败", file=sys.stderr)
            return 1
        
        # 代码生成
        generator = UnifiedCodeGenerator()
        python_code = generator.generate(module)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"[成功] 已生成: {output_file}")
        
        if run:
            # 执行代码
            try:
                # 创建执行环境，包含必要的内置变量
                exec_globals = {
                    '__name__': '__main__',
                    '__file__': output_file or '<light_script>',
                    '__builtins__': __builtins__,
                }
                exec(python_code, exec_globals)
            except Exception as e:
                print(f"[运行错误] {e}", file=sys.stderr)
                return 1
        
        return 0
    
    def compile_with_src(self, source: str, output_file: Optional[str] = None, run: bool = False, target: str = 'python') -> int:
        """使用src手写解析器编译
        
        Args:
            source: 源代码
            output_file: 输出文件路径
            run: 是否执行
            target: 目标格式 ('python' 或 'llvm')
        """
        from compiler import LightCompiler
        
        compiler = LightCompiler()
        
        if target == 'llvm':
            # LLVM IR 生成：只做解析和适配，跳过类型检查
            try:
                tokens = compiler.tokenize(source)
                raw_ast = compiler.parse_raw(source)
                module = compiler.adapt(raw_ast)
                
                if not module:
                    print("[语法错误] 解析失败", file=sys.stderr)
                    return 1
                
                llvm_ir = compiler.generate_llvm_ir(module)
                
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(llvm_ir)
                    print(f"[成功] 已生成 LLVM IR: {output_file}")
                else:
                    print(llvm_ir)
                
                return 0
            except Exception as e:
                print(f"[LLVM IR 生成错误] {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return 1
        else:
            # Python 代码生成：完整编译流程
            result = compiler.compile(source)
            
            if compiler.errors:
                for error in compiler.errors:
                    print(f"[错误] {error}", file=sys.stderr)
                return 1
            
            module = result.get('ast')
            if not module:
                print("[语法错误] 解析失败", file=sys.stderr)
                return 1
            
            from code_generator import PythonCodeGenerator
            generator = PythonCodeGenerator()
            python_code = generator.generate(module)
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                print(f"[成功] 已生成: {output_file}")
            
            if run:
                try:
                    exec_globals = {
                        '__name__': '__main__',
                        '__file__': output_file or '<light_script>',
                        '__builtins__': __builtins__,
                    }
                    exec(python_code, exec_globals)
                except Exception as e:
                    print(f"[运行错误] {e}", file=sys.stderr)
                    return 1
            
            return 0
    
    def interpret_run(self, source_file: str) -> int:
        """使用解释器直接运行"""
        try:
            from light_interpreter import run_file
            run_file(source_file)
            return 0
        except ImportError:
            print("[错误] 解释器模块不可用", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[运行错误] {e}", file=sys.stderr)
            return 1
    
    def start_repl(self) -> int:
        """启动REPL"""
        try:
            # 先尝试导入 tools.repl（新位置）
            from tools.repl import LightREPL
            repl = LightREPL()
            repl.run()
            return 0
        except ImportError:
            pass
        
        try:
            # 再尝试导入 light_repl（旧位置）
            from light_repl import main as repl_main
            repl_main()
            return 0
        except ImportError:
            print("[错误] REPL模块不可用", file=sys.stderr)
            return 1
    
    def start_debug_repl(self) -> int:
        """启动调试REPL"""
        try:
            from tools.light_debug_repl import LightDebugREPL
            repl = LightDebugREPL()
            repl.run()
            return 0
        except ImportError:
            print("[错误] 调试REPL模块不可用", file=sys.stderr)
            return 1
    
    def show_ast(self, source: str, backend: str = 'antlr') -> int:
        """显示AST结构"""
        if backend == 'antlr':
            from antlr4 import InputStream, CommonTokenStream
            from LightLangLexer import LightLangLexer
            from LightLangParser import LightLangParser
            from light_visitor import LightLangASTBuilder
            
            input_stream = InputStream(source)
            lexer = LightLangLexer(input_stream)
            tokens = CommonTokenStream(lexer)
            parser = LightLangParser(tokens)
            tree = parser.program()
            builder = LightLangASTBuilder()
            module = builder.visitProgram(tree)
        else:
            from light_parser_v3 import LightParser
            parser = LightParser()
            module = parser.parse(source)
        
        if module:
            self._print_ast(module, 0)
            return 0
        else:
            print("[错误] 解析失败", file=sys.stderr)
            return 1
    
    def _print_ast(self, node, indent: int):
        """打印AST节点"""
        prefix = "  " * indent
        node_type = type(node).__name__
        
        if hasattr(node, 'name'):
            print(f"{prefix}{node_type}: {node.name}")
        else:
            print(f"{prefix}{node_type}")
        
        # 递归打印子节点
        for attr in ['statements', 'segments', 'classes', 'body', 'parameters', 'arguments']:
            if hasattr(node, attr):
                children = getattr(node, attr)
                if isinstance(children, list):
                    for child in children:
                        self._print_ast(child, indent + 1)
                elif children:
                    self._print_ast(children, indent + 1)


def main():
    """主函数"""
    cli = LightUnifiedCLI()
    
    # 检查是否是子命令模式
    if len(sys.argv) > 1 and sys.argv[1] in ['run', 'compile', 'repl']:
        # 子命令模式
        parser = argparse.ArgumentParser(description='光明（Light）编程语言编译器')
        parser.add_argument('--version', action='version', version=VERSION_STR)
        parser.add_argument('--dev-version', action='store_true', help='显示开发分支版本信息')
        subparsers = parser.add_subparsers(dest='command', help='子命令')
        
        # run 子命令
        run_parser = subparsers.add_parser('run', help='解释执行文件')
        run_parser.add_argument('file', help='源文件路径')
        
        # compile 子命令
        compile_parser = subparsers.add_parser('compile', help='编译文件')
        compile_parser.add_argument('file', help='源文件路径')
        compile_parser.add_argument('-o', '--output', help='输出文件路径')
        compile_parser.add_argument('--backend', choices=['antlr', 'src'], default='src',
                                   help='选择编译后端（默认：src）')
        compile_parser.add_argument('--target', choices=['py', 'js', 'wasm'], default='py',
                                   help='目标代码（默认：py）')
        
        # repl 子命令
        subparsers.add_parser('repl', help='启动交互式REPL')
        
        # debug 子命令
        debug_parser = subparsers.add_parser('debug', help='启动调试REPL')
        debug_parser.add_argument('file', nargs='?', help='要调试的文件路径（可选）')
        
        args = parser.parse_args()
        
        # 处理 --dev-version 标志
        if getattr(args, 'dev_version', False):
            try:
                from src.version import get_dev_version_string
                print(get_dev_version_string())
            except ImportError:
                print(VERSION_STR)
            return 0
        
        if args.command == 'run':
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            return cli.interpret_run(args.file)
        
        elif args.command == 'compile':
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            output_file = args.output or args.file.replace('.light', '.py')
            
            if args.backend == 'antlr':
                return cli.compile_with_antlr(source, output_file=output_file, run=False)
            else:
                return cli.compile_with_src(source, output_file=output_file, run=False, target=args.target)
        
        elif args.command == 'repl':
            return cli.start_repl()
        
        elif args.command == 'debug':
            if args.file:
                # 调试模式下加载文件
                if not os.path.exists(args.file):
                    print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                    return 1
                from tools.light_debug_repl import LightDebugREPL
                repl = LightDebugREPL()
                repl.load_file(args.file)
                return 0
            else:
                return cli.start_debug_repl()
    
    else:
        # 默认模式：编译并运行
        parser = argparse.ArgumentParser(
            description='光明（Light）编程语言编译器',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例：
  light hello.light                      # 编译并运行
  light hello.light --backend src        # 使用src后端
  light run hello.light                  # 解释执行
  light compile hello.light -o hello.py  # 编译为Python文件
  light repl                            # 启动交互式REPL
  light hello.light --ast                # 显示AST结构
            """
        )
        
        parser.add_argument('file', nargs='?', help='源文件路径')
        parser.add_argument('--backend', choices=['antlr', 'src'], default='antlr',
                           help='选择编译后端（默认：antlr）')
        parser.add_argument('-o', '--output', help='输出文件路径')
        parser.add_argument('--run', action='store_true', help='编译并运行')
        parser.add_argument('--ast', action='store_true', help='显示AST结构')
        parser.add_argument('--version', action='version', version=VERSION_STR)
        parser.add_argument('--dev-version', action='store_true', help='显示开发分支版本信息')
        
        args = parser.parse_args()
        
        # 处理 --dev-version 标志
        if getattr(args, 'dev_version', False):
            try:
                from src.version import get_dev_version_string
                print(get_dev_version_string())
            except ImportError:
                print(VERSION_STR)
            return 0
        
        if args.file:
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            output_file = args.output
            
            if args.ast:
                return cli.show_ast(source, args.backend)
            
            run_mode = args.run or (not args.output)
            
            if args.backend == 'antlr':
                return cli.compile_with_antlr(source, output_file=output_file, run=run_mode)
            else:
                return cli.compile_with_src(source, output_file=output_file, run=run_mode)
        
        else:
            # 无参数时启动REPL
            return cli.start_repl()


if __name__ == '__main__':
    sys.exit(main())
