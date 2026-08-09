"""
光明（Light）编程语言 解释执行器 - 组合模块

使用 mixin 模式组合核心解释器、运算操作和内置函数。
"""

import sys
import os
from typing import List

from interpreter_core import *
from operations import OperationsMixin
from light_builtins import BuiltinsMixin


class Interpreter(InterpreterCore, OperationsMixin, BuiltinsMixin):
    """光明完整解释器"""
    pass


# =============================================================================
# 高层解释接口
# =============================================================================

def run_source(source: str, filepath: str = None, search_paths: List[str] = None) -> Interpreter:
    """解析并执行光明源代码

    Args:
        source: 光明源代码
        filepath: 源文件路径（用于模块相对导入）
        search_paths: 模块搜索路径列表

    Returns:
        执行后的解释器实例
    """
    from light_visitor import LightParser

    parser = LightParser()
    module = parser.parse(source)
    if module is None:
        errors = '\n'.join(parser.errors)
        raise RuntimeError(f"解析失败:\n{errors}")

    interpreter = Interpreter(search_paths=search_paths)
    if filepath:
        interpreter.current_filepath = filepath
    # 从文件路径推导模块名
    module_name = None
    if filepath:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
    interpreter.interpret_module(module, module_name=module_name)
    return interpreter


def run_file(filepath: str, search_paths: List[str] = None) -> Interpreter:
    """从文件读取光明源代码并执行

    Args:
        filepath: 光明源文件路径
        search_paths: 模块搜索路径列表

    Returns:
        执行后的解释器实例
    """
    abs_path = os.path.abspath(filepath)
    with open(abs_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 默认在文件所在目录搜索模块
    file_dir = os.path.dirname(abs_path)
    paths = search_paths or [file_dir, '.']

    return run_source(source, filepath=abs_path, search_paths=paths)


# =============================================================================
# CLI 入口
# =============================================================================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='光明编程语言解释器')
    parser.add_argument('file', nargs='?', help='光明源文件路径')
    parser.add_argument('-e', '--eval', help='直接执行代码字符串')
    
    args = parser.parse_args()
    
    try:
        if args.eval:
            interpreter = run_source(args.eval)
        elif args.file:
            interpreter = run_file(args.file)
        else:
            # REPL 模式
            print("光明 v0.1 交互模式 (输入 '退出()' 或 Ctrl+C 退出)")
            interpreter = Interpreter()
            while True:
                try:
                    line = input('光明> ')
                    if line.strip() in ('退出()', 'exit()', 'quit()'):
                        break
                    if not line.strip():
                        continue
                    try:
                        interpreter.interpret_module(
                            __import__('light_visitor', fromlist=['LightParser']).LightParser().parse(line)
                        )
                    except Exception as e:
                        print(f"[错误] {e}")
                except (KeyboardInterrupt, EOFError):
                    print()
                    break
    except Exception as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

# 重新导出
__all__ = ['Interpreter', 'LightValue', 'LightFunction', 'LightClass', 'LightInstance',
           'Environment', 'ReturnSignal', 'BreakSignal', 'ContinueSignal', 'LightError']