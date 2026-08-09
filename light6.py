#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）Level 7 编译器 - 完整可执行入口

集成所有 Level 7 + P3 增强功能：
  - 类型注解支持：设x为整数=10，段add接收a整数,b整数返回整数
  - 复合类型注解：列表[整数]、字典[文本,整数]
  - 运行时类型检查：开启/关闭类型检查（默认关闭）
  - 单行块支持：如果x大于0：返回x
  - 运算符符号别名：+ - * / % == != < > <= >=
  - 反引号转义标识符：`关键字` 作为变量名
  - 调试日志输出到文件：调试模式设为文件("debug.log")

用法：
  light7 <源文件.light>            # 编译并运行
  light7 compile <源文件.light>     # 仅编译，输出到 stdout
  light7 compile <源文件.light> -o <输出.py>  # 编译到文件
  light7 compile --c <源文件.light>  # 编译为 C 代码
  light7 compile --native <源文件.light>  # 编译为原生可执行文件
  light7 run <源文件.light>         # 编译并运行
  light7 --debug <源文件.light>     # 开启调试模式运行
  light7 --debug-file <文件.log> <源文件.light>  # 调试日志输出到文件
  light7 --demo                    # 运行综合演示（demo_l7.light）
  light7 --test                    # 运行内置测试
  light7 --help                    # 显示帮助
"""

import sys
import os
import io
import contextlib

# ── 路径设置 ──────────────────────────────────────────────────
# 支持 PyInstaller 打包后的路径查找
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的可执行文件
    _BASE_DIR = os.path.dirname(sys.executable)
    _SCRIPT_DIR = os.path.dirname(sys.executable)
    # 尝试从 _MEIPASS 获取（one-file 模式）
    _MEIPASS = getattr(sys, '_MEIPASS', None)
    if _MEIPASS and os.path.isdir(os.path.join(_MEIPASS, 'bootstrap')):
        _BOOTSTRAP_DIR = os.path.join(_MEIPASS, 'bootstrap')
    else:
        _BOOTSTRAP_DIR = os.path.join(_BASE_DIR, 'bootstrap')
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _BOOTSTRAP_DIR = os.path.join(_SCRIPT_DIR, 'bootstrap')

if os.path.isdir(_BOOTSTRAP_DIR):
    sys.path.insert(0, _BOOTSTRAP_DIR)

# ── 运行时命名空间 ────────────────────────────────────────────
def _创建运行时命名空间():
    """创建光明代码运行所需的命名空间"""
    ns = {}
    # 基础函数
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
    # 布尔值
    ns['真'] = True
    ns['假'] = False
    # 类型检查
    ns['类型检查开启'] = False
    return ns


def _加载编译器():
    """加载 level7_generated.py 编译器"""
    compiler_path = os.path.join(_BOOTSTRAP_DIR, 'level7_generated.py')
    if not os.path.exists(compiler_path):
        # 尝试从当前目录加载
        compiler_path = os.path.join(_SCRIPT_DIR, 'bootstrap', 'level7_generated.py')
    if not os.path.exists(compiler_path):
        print(f"[错误] 找不到编译器文件: level7_generated.py", file=sys.stderr)
        sys.exit(1)
    
    ns = _创建运行时命名空间()
    with open(compiler_path, 'r', encoding='utf-8-sig') as f:
        code = f.read()
    exec(code, ns)
    return ns['编译'], ns


def 编译代码(源代码, 调试模式=False):
    """编译光明代码为 Python 代码"""
    编译, ns = _加载编译器()
    if 调试模式:
        ns['调试模式'] = True
    try:
        return 编译(源代码)
    except Exception as e:
        print(f"[编译错误] {e}", file=sys.stderr)
        return None


def 运行代码(源代码, 调试模式=False, 调试文件=None):
    """编译并运行光明代码"""
    编译, ns = _加载编译器()
    if 调试模式:
        ns['调试模式'] = True
    if 调试文件:
        ns['调试模式设为文件'](调试文件)
    
    # 编译
    try:
        py_code = 编译(源代码)
    except Exception as e:
        print(f"[编译错误] {e}", file=sys.stderr)
        return False
    
    if py_code is None:
        return False
    
    # 运行
    try:
        ns2 = _创建运行时命名空间()
        ns2['主函数'] = None
        exec(py_code, ns2)
        if '主函数' in ns2 and ns2['主函数'] is not None:
            ns2['主函数']()
        return True
    except Exception as e:
        print(f"[运行错误] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def 编译并运行(源代码, 输出文件=None, 调试模式=False, 调试文件=None):
    """编译并运行光明代码，可选择输出到文件"""
    编译, ns = _加载编译器()
    if 调试模式:
        ns['调试模式'] = True
    if 调试文件:
        ns['调试模式设为文件'](调试文件)
    
    # 编译
    try:
        py_code = 编译(源代码)
    except Exception as e:
        print(f"[编译错误] {e}", file=sys.stderr)
        return False
    
    if py_code is None:
        return False
    
    # 输出到文件
    if 输出文件:
        with open(输出文件, 'w', encoding='utf-8') as f:
            f.write(py_code)
        print(f"[成功] 已生成: {输出文件}")
    
    # 运行
    try:
        ns2 = _创建运行时命名空间()
        ns2['主函数'] = None
        exec(py_code, ns2)
        if '主函数' in ns2 and ns2['主函数'] is not None:
            ns2['主函数']()
        return True
    except Exception as e:
        print(f"[运行错误] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def 运行内置测试():
    """运行编译器的内置测试"""
    编译, ns = _加载编译器()
    ns['测试']()
    return True


def 交互式REPL():
    """启动简单的交互式 REPL"""
    编译, ns = _加载编译器()
    print("光明 Level 7 REPL (输入 'exit()' 退出)")
    print("输入光明代码，按 Ctrl+Z 或输入 exit() 退出")
    print("-" * 40)
    buffer = ""
    while True:
        try:
            line = input(">>> " if not buffer else "... ")
            if line.strip() == "exit()":
                break
            buffer = buffer + line + "\n"
            # 尝试编译 - 如果成功则执行并清空缓冲区
            try:
                py_code = 编译(buffer)
                if py_code:
                    ns2 = _创建运行时命名空间()
                    ns2['主函数'] = None
                    exec(py_code, ns2)
                    if '主函数' in ns2 and ns2['主函数'] is not None:
                        ns2['主函数']()
                    buffer = ""
            except Exception:
                # 编译失败，继续累积输入
                pass
        except (EOFError, KeyboardInterrupt):
            print()
            break


def 主函数():
    """主入口"""
    # 使用 sys.argv 直接判断第一个非选项参数是否为子命令
    raw_args = sys.argv[1:]
    
    # 提取全局选项
    debug_mode = False
    debug_file = None
    show_test = False
    show_demo = False
    output_file = None
    
    # 查找并移除全局选项
    filtered_args = []
    i = 0
    while i < len(raw_args):
        a = raw_args[i]
        if a == '--debug':
            debug_mode = True
            i += 1
        elif a == '--demo':
            show_demo = True
            i += 1
        elif a == '--test':
            show_test = True
            i += 1
        elif a == '--help' or a == '-h':
            _print_help()
            return
        elif a.startswith('--debug-file='):
            debug_file = a.split('=', 1)[1]
            i += 1
        elif a == '--debug-file':
            i += 1
            if i < len(raw_args):
                debug_file = raw_args[i]
                i += 1
            else:
                print("[错误] --debug-file 需要指定文件路径", file=sys.stderr)
                sys.exit(1)
        elif a in ('-o', '--output'):
            i += 1
            if i < len(raw_args):
                output_file = raw_args[i]
                i += 1
            else:
                print("[错误] -o/--output 需要指定输出文件路径", file=sys.stderr)
                sys.exit(1)
        elif a.startswith('-o='):
            output_file = a[3:]
            i += 1
        else:
            filtered_args.append(a)
            i += 1
    
    # 运行内置测试
    if show_test:
        运行内置测试()
        return
    
    # 运行综合演示
    if show_demo:
        # 查找 demo_l7.light 文件
        demo_paths = [
            os.path.join(_SCRIPT_DIR, 'demo_l7.light'),
            os.path.join(os.getcwd(), 'demo_l7.light'),
        ]
        if getattr(sys, 'frozen', False):
            _MEIPASS = getattr(sys, '_MEIPASS', None)
            if _MEIPASS:
                demo_paths.insert(0, os.path.join(_MEIPASS, 'demo_l7.light'))
        
        demo_path = None
        for p in demo_paths:
            if os.path.exists(p):
                demo_path = p
                break
        
        if not demo_path:
            print("[错误] 找不到演示文件: demo_l7.light", file=sys.stderr)
            sys.exit(1)
        
        with open(demo_path, 'r', encoding='utf-8') as f:
            源代码 = f.read()
        print("=" * 50)
        print("光明 Level 7 综合演示（含类型注解）")
        print("=" * 50)
        成功 = 编译并运行(源代码, 调试模式=debug_mode, 调试文件=debug_file)
        if not 成功:
            sys.exit(1)
        return
    
    # 确定操作模式
    subcommand = None
    source_file = None
    native_mode = False
    c_mode = False
    
    if filtered_args:
        if filtered_args[0] in ('compile', 'run'):
            subcommand = filtered_args[0]
            # 检查子命令后的选项
            args_after = filtered_args[1:]
            rest = []
            i = 0
            while i < len(args_after):
                a = args_after[i]
                if a == '--native':
                    native_mode = True
                    i += 1
                elif a == '--c':
                    c_mode = True
                    i += 1
                else:
                    rest.append(a)
                    i += 1
            source_file = rest[0] if rest else None
        else:
            source_file = filtered_args[0]
    
    if subcommand == 'compile':
        # 仅编译
        if not source_file:
            print("[错误] compile 命令需要指定源文件", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(source_file):
            print(f"[错误] 文件不存在: {source_file}", file=sys.stderr)
            sys.exit(1)
        with open(source_file, 'r', encoding='utf-8') as f:
            源代码 = f.read()
        
        if c_mode:
            # 编译为 C 代码
            try:
                from c_backend import 编译到C
                c_code = 编译到C(源代码)
                if c_code is None:
                    sys.exit(1)
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(c_code)
                    print(f"[成功] 已生成 C 代码: {output_file}")
                else:
                    print(c_code)
            except Exception as e:
                print(f"[错误] C 代码生成失败: {e}", file=sys.stderr)
                sys.exit(1)
            return
        
        if native_mode:
            # 编译为原生可执行文件
            try:
                from c_backend import 编译光明到C文件, 编译C到原生
                基础名 = os.path.splitext(os.path.basename(source_file))[0]
                工作目录 = os.path.dirname(os.path.abspath(source_file))
                c文件 = 编译光明到C文件(source_file)
                if c文件 is None:
                    sys.exit(1)
                exe文件 = 编译C到原生(c文件)
                if exe文件:
                    print(f"[成功] 原生可执行文件: {exe文件}")
                else:
                    print(f"[提示] C 代码已生成: {c文件}")
                    print(f"[提示] 请安装 Clang/LLVM 或 GCC 后重试")
                    print(f"[提示] 手动编译: clang -o {基础名}.exe {基础名}.c")
                    sys.exit(1)
            except Exception as e:
                print(f"[错误] 原生编译失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                sys.exit(1)
            return
        
        if output_file:
            编译并运行(源代码, 输出文件=output_file, 调试模式=debug_mode, 调试文件=debug_file)
        else:
            py_code = 编译代码(源代码, 调试模式=debug_mode)
            if py_code:
                print(py_code)
        return
    
    if subcommand == 'run':
        # 编译并运行
        if not source_file:
            print("[错误] run 命令需要指定源文件", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(source_file):
            print(f"[错误] 文件不存在: {source_file}", file=sys.stderr)
            sys.exit(1)
        with open(source_file, 'r', encoding='utf-8') as f:
            源代码 = f.read()
        成功 = 编译并运行(源代码, 输出文件=output_file, 调试模式=debug_mode, 调试文件=debug_file)
        if not 成功:
            sys.exit(1)
        return
    
    # 无子命令模式：直接指定文件或 REPL
    if source_file:
        if not os.path.exists(source_file):
            print(f"[错误] 文件不存在: {source_file}", file=sys.stderr)
            sys.exit(1)
        with open(source_file, 'r', encoding='utf-8') as f:
            源代码 = f.read()
        成功 = 编译并运行(源代码, 输出文件=output_file, 调试模式=debug_mode, 调试文件=debug_file)
        if not 成功:
            sys.exit(1)
    else:
        交互式REPL()


def _print_help():
    """打印帮助信息"""
    print("光明（Light）Level 7 编译器 - 类型注解 + P3 增强功能")
    print()
    print("用法:")
    print("  python light7.py <文件.light>              编译并运行（默认）")
    print("  python light7.py compile <文件.light>       仅编译，输出到 stdout")
    print("  python light7.py compile <文件.light> -o <输出.py>  编译到文件")
    print("  python light7.py compile --c <文件.light>   编译为 C 代码")
    print("  python light7.py compile --native <文件.light>  编译为原生可执行文件")
    print("  python light7.py run <文件.light>           编译并运行")
    print("  python light7.py --debug <文件.light>       开启调试模式运行")
    print("  python light7.py --debug-file <文件.log> <文件.light>  调试日志输出到文件")
    print("  python light7.py --demo                    运行综合演示")
    print("  python light7.py --test                    运行内置测试")
    print("  python light7.py --help                    显示帮助信息")
    print()
    print("选项:")
    print("  --debug               开启调试模式 (stdout)")
    print("  --debug-file FILE     调试日志输出到文件")
    print("  --demo                运行综合演示 (demo_l7.light)")
    print("  --test                运行内置测试")
    print("  -o FILE, --output FILE   输出文件路径")
    print("  --help, -h            显示帮助信息")
    print()
    print("Level 7 增强功能:")
    print("  - 类型注解: 设x为整数=10, 段add接收a整数,b整数返回整数")
    print("  - 复合类型注解: 列表[整数], 字典[文本,整数]")
    print("  - 运行时类型检查: 开启/关闭类型检查")
    print("  - 单行块支持: 如果x大于0：返回x")
    print("  - 运算符符号别名: + - * / % == != < > <= >=")
    print("  - 反引号转义标识符: `关键字` 作为变量名")
    print("  - 调试日志输出到文件: 调试模式设为文件(\"debug.log\")")


if __name__ == '__main__':
    主函数()