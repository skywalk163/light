"""
光明（Light）编程语言 - 命令行工具

使用方法：
    light run <file>         # 运行光明文件
    light exec <code>        # 直接执行代码
    light repl               # 交互式编程环境
    light parse <file>       # 解析并显示 AST
    light tokenize <file>    # 词法分析并显示 Token

    # 旧模式兼容
    python light_interpreter.py <file>
    python main.py <file>
"""

import sys
import os
import argparse
import traceback

# 添加当前目录到路径
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from light_interpreter import run_source, run_file, Interpreter


# =============================================================================
# ANSI 颜色支持
# =============================================================================

def _supports_color() -> bool:
    """检测终端是否支持颜色输出"""
    if not sys.stdout.isatty():
        return False
    if os.name == 'nt':
        # Windows: 检查是否支持 ANSI
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            return bool(kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(ctypes.c_uint(0))))
        except Exception:
            return os.environ.get('TERM') in ('xterm', 'xterm-256color', 'ansi')
    return os.environ.get('TERM') in ('xterm', 'xterm-256color', 'ansi', 'linux')


_COLOR = _supports_color()


def _c(code: str, text: str) -> str:
    """给文本加颜色（如果支持）"""
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def green(text: str) -> str:
    return _c("32", text)


def red(text: str) -> str:
    return _c("31", text)


def yellow(text: str) -> str:
    return _c("33", text)


def blue(text: str) -> str:
    return _c("34", text)


def magenta(text: str) -> str:
    return _c("35", text)


def cyan(text: str) -> str:
    return _c("36", text)


def bold(text: str) -> str:
    return _c("1", text)


def dim(text: str) -> str:
    return _c("2", text)


# =============================================================================
# 错误显示辅助函数
# =============================================================================

def _try_extract_error_info(e: Exception) -> dict:
    """从异常中提取行号、列号等信息"""
    info = {
        'message': str(e),
        'line': None,
        'column': None,
        'source': None,
    }
    # 检查异常对象本身是否携带位置信息
    if hasattr(e, 'line') and e.line is not None:
        info['line'] = e.line
    if hasattr(e, 'column') and e.column is not None:
        info['column'] = e.column
    if hasattr(e, 'source') and e.source is not None:
        info['source'] = e.source
    return info


def _print_runtime_error(e: Exception, source: str = "", filepath: str = ""):
    """打印格式化的运行时错误"""
    from light_error_handler import format_error_context, suggest_fix

    info = _try_extract_error_info(e)
    message = info['message']
    line = info['line']
    column = info['column']
    err_source = info['source'] or source

    # 输出错误标题
    label = str(type(e).__name__)
    print(red(f"⚠ {label}"), file=sys.stderr)

    # 尝试从错误消息中解析行号（格式：消息（第X行，第Y列））
    if line is None and '（第' in message:
        import re
        m = re.search(r'（第(\d+)行，第(\d+)列）', message)
        if m:
            line = int(m.group(1))
            column = int(m.group(2))
            message = message[:m.start()]

    if line is not None:
        loc = f"  位置: 第{line}行"
        loc += f"，第{column}列" if column is not None else ""
        print(dim(loc), file=sys.stderr)

    if filepath:
        print(dim(f"  文件: {filepath}"), file=sys.stderr)

    print(f"  信息: {yellow(message)}", file=sys.stderr)

    # 显示源码上下文
    if err_source and line is not None:
        context = format_error_context(err_source, line, column or 0)
        if context:
            print(f"\n{dim(context)}", file=sys.stderr)

    # 修复建议
    suggestion = suggest_fix('unknown', message)
    if suggestion:
        print(f"  建议: {suggestion}", file=sys.stderr)


# =============================================================================
# 子命令：运行文件
# =============================================================================

def cmd_run(filepath: str, args):
    """运行光明文件"""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        print(red(f"错误: 文件不存在: {filepath}"), file=sys.stderr)
        sys.exit(1)

    # 读取源码用于错误上下文显示
    source = ""
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        pass

    try:
        interp = run_file(abs_path)
        output = interp.get_output()
        if output and not args.quiet:
            print(output)
    except Exception as e:
        _print_runtime_error(e, source, filepath)
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


# =============================================================================
# 子命令：直接执行代码
# =============================================================================

def cmd_exec(code: str, args):
    """直接执行代码字符串"""
    try:
        interp = run_source(code)
        output = interp.get_output()
        if output and not args.quiet:
            print(output)
    except Exception as e:
        _print_runtime_error(e, code)
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


# =============================================================================
# 子命令：解析并显示 AST
# =============================================================================

def cmd_parse(filepath: str, args):
    """解析文件并显示 AST 结构"""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        print(red(f"错误: 文件不存在: {filepath}"), file=sys.stderr)
        sys.exit(1)

    from light_visitor import parse_source

    with open(abs_path, 'r', encoding='utf-8') as f:
        source = f.read()

    module = parse_source(source)
    if module is None:
        print(red("解析失败"), file=sys.stderr)
        sys.exit(1)

    print(f"解析成功！")
    print(f"  段落数: {bold(str(len(module.segments)))}")
    print(f"  语句数: {bold(str(len(module.statements)))}")
    print(f"  导入数: {bold(str(len(module.imports)))}")
    print(f"  导出数: {bold(str(len(module.exports)))}")

    if module.segments:
        print(f"\n{blue('段落列表:')}")
        for seg in module.segments:
            params = ", ".join(p.name for p in seg.parameters)
            ret = f" -> {cyan(seg.return_type)}" if seg.return_type else ""
            print(f"  · {green('《' + seg.name + '》')}段({cyan(params)}){ret}")

    if module.imports:
        print(f"\n{blue('导入:')}")
        for imp in module.imports:
            names = "，".join(green(n) for n in imp.names)
            mod = yellow(imp.module) if imp.module else "<当前模块>"
            print(f"  · 从 {mod} 导入 {names}")

    if module.exports:
        print(f"\n{blue('导出:')}")
        for exp in module.exports:
            print(f"  · 导出 {green(exp.name)}")


# =============================================================================
# 子命令：词法分析显示 Token
# =============================================================================

def cmd_tokenize(filepath: str, args):
    """词法分析并显示 Token"""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        print(red(f"错误: 文件不存在: {filepath}"), file=sys.stderr)
        sys.exit(1)

    from light_tokenizer import LightLangTokenizer

    with open(abs_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tokenizer = LightLangTokenizer()
    tokens = tokenizer.tokenize(source)

    type_w = max(len(t.type_name) for t in tokens) + 2 if tokens else 10
    sep = dim("-" * (type_w + 30))
    print(f"{green('类型'):<{type_w}} {green('文本'):<15} {green('位置')}")
    print(sep)

    for token in tokens:
        if token.type_name == 'EOF':
            continue
        loc = f"{token.line}:{token.column}"
        ttype = cyan(token.type_name) if token.type_name.startswith('K_') else yellow(token.type_name)
        print(f"{ttype:<{type_w}} {token.text:<15} {dim(loc)}")

    if tokenizer.errors:
        print(f"\n{red('词法错误:')}")
        for err in tokenizer.errors:
            print(f"  · {red(str(err))}")
        sys.exit(1)


# =============================================================================
# REPL 交互环境
# =============================================================================

def _is_incomplete(code: str) -> bool:
    """检查代码是否不完整（需要多行输入）"""
    stripped = code.strip()
    if not stripped:
        return False

    # 如果以冒号结尾（块定义），需要更多输入
    if stripped.rstrip().endswith(':') or stripped.rstrip().endswith('：'):
        return True

    # 检查括号是否匹配
    pairs = [('（', '）'), ('(', ')'), ('【', '】'), ('[', ']'), ('《', '》'), ('{', '}')]
    stack = []
    in_string = False
    string_char = None

    for ch in stripped:
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'", '「'):
            in_string = True
            string_char = ch
            continue
        for open_c, close_c in pairs:
            if ch == open_c:
                stack.append(close_c)
                break
            if ch == close_c:
                if not stack or stack.pop() != ch:
                    return False
                break

    return len(stack) > 0


def _get_repl_banner() -> str:
    """获取 REPL 欢迎信息"""
    return f"""
{bold(cyan('光明 (Light)'))} {yellow('v0.1.0')} - {dim('中文编程语言交互环境')}

{green('可用命令:')}
  {cyan('/help')}     显示帮助信息
  {cyan('/exit')}     退出 REPL（也可用 Ctrl+C / Ctrl+D）
  {cyan('/clear')}    清屏
  {cyan('/env')}      显示当前环境中已定义的变量和段落

{green('示例:')}
  {yellow('>>>')} 打印("你好，世界")。
  {yellow('>>>')} 定义甲等于42。
  {yellow('>>>')} 甲
"""


def _get_help_text() -> str:
    """获取帮助信息"""
    return f"""
{bold(cyan('光明 (Light) 快速参考'))}

{green('变量定义:')}
  定义变量名等于值。
  定义变量名等于表达式。

{green('输出:')}
  打印(值)。
  输出(值)。

{green('条件:')}
  如果条件:
    语句块。
  结束。
  如果条件:
    语句块。
  否则:
    语句块。
  结束。

{green('循环:')}
  对于 变量 在 可遍历对象:
    语句块。
  结束。
  
  当 条件:
    语句块。
  结束。

{green('段落（函数）定义:')}
  《段落名》段(参数1, 参数2):
    返回 表达式。
  结束。

{green('导入导出:')}
  从 模块名 导入《符号1》，《符号2》。
  导出《符号名》。

{green('列表与典:')}
  定义列等于【1, 2, 3】。
  定义典等于_典(键1, 值1, 键2, 值2)。

{green('退出 REPL:')}
  /exit  或 退出()  或 Ctrl+C
"""


def cmd_repl(args):
    """交互式 REPL 环境"""
    interp = Interpreter()
    history_file = os.path.join(os.path.expanduser("~"), ".light_history")

    # 尝试加载 readline 实现历史
    _readline = None
    try:
        import readline as _rl
        _readline = _rl
        try:
            _readline.read_history_file(history_file)
        except (FileNotFoundError, OSError):
            pass
        _readline.set_history_length(1000)
    except ImportError:
        pass

    print(_get_repl_banner())

    while True:
        try:
            # 获取多行输入
            lines = []
            prompt = yellow("光明> ") if _COLOR else "光明> "
            while True:
                try:
                    line = input(prompt)
                except EOFError:
                    print()
                    print(green("再见！"))
                    return

                if _readline:
                    _readline.append_history_file(1, history_file)

                # 检查命令
                stripped = line.strip()
                if stripped == '/exit':
                    print(green("再见！"))
                    return
                if stripped == '/quit':
                    print(green("再见！"))
                    return
                if stripped == '/help':
                    print(_get_help_text())
                    lines = []
                    break
                if stripped == '/clear':
                    # Windows cls or UNIX clear
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(_get_repl_banner())
                    lines = []
                    break
                if stripped == '/env':
                    _show_env(interp)
                    lines = []
                    break

                lines.append(line)
                code = '\n'.join(lines).strip()

                # 空输入或已完整
                if not code:
                    lines = []
                    break
                if not _is_incomplete(code):
                    break

                prompt = dim("   ... ") if _COLOR else "   ... "

            code = '\n'.join(lines).strip()
            if not code:
                continue

            # 处理单行表达式求值
            _process_repl_line(interp, code)

        except KeyboardInterrupt:
            print(f"\n{dim('(按 Ctrl+C 再次退出，或输入 /exit)')}")
            continue
        except Exception as e:
            print(red(f"错误: {e}"))


def _show_env(interp: Interpreter):
    """显示当前环境中的变量和段落"""
    variables = []
    functions = []
    for name, val in interp.global_env.variables.items():
        if val.type_name == '段' or val.type_name == '内置段':
            functions.append(name)
        else:
            variables.append((name, val))

    if functions:
        print(f"\n{green('已定义的段落:')}")
        for name in sorted(functions):
            print(f"  · {cyan(name)}")

    if variables:
        print(f"\n{green('已定义的变量:')}")
        for name, val in sorted(variables):
            display_val = str(val.value)
            if len(display_val) > 60:
                display_val = display_val[:57] + "..."
            print(f"  · {name} = {yellow(display_val)}")

    if not functions and not variables:
        print(f"\n{dim('当前环境为空')}")


def _process_repl_line(interp: Interpreter, code: str):
    """处理一行 REPL 输入"""
    # 尝试解析为表达式（如果看起来像表达式而非语句）
    from light_visitor import LightParser
    parser = LightParser()

    # 尝试先作为完整代码解析
    module = parser.parse(code)
    if module is not None:
        try:
            interp.interpret_module(module)
            output = interp.get_output()
            if output:
                print(output)
        except Exception as e:
            print(red(f"执行错误: {e}"))
        return

    # 如果解析失败，尝试作为表达式解析（包装为打印语句）
    expr_code = f"打印({code})。\n"
    module = parser.parse(expr_code)
    if module is not None:
        try:
            interp.interpret_module(module)
            output = interp.get_output()
            if output:
                print(output.rstrip())
        except Exception as e:
            print(red(f"错误: {e}"))
        return

    # 都失败了
    errors = '\n'.join(parser.errors)
    print(red(f"语法错误: {errors}") if errors else red("无法解析该输入"))


# =============================================================================
# 主入口
# =============================================================================

def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        prog='light',
        description='光明（Light）编程语言解释器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{bold('示例:')}
  {green('light run')} script.light         {dim('# 运行光明文件')}
  {green('light exec')} '打印("你好")。'    {dim('# 直接执行代码')}
  {green('light repl')}                     {dim('# 启动交互环境')}
  {green('light parse')} script.light       {dim('# 解析并显示 AST')}
  {green('light tokenize')} script.light    {dim('# 显示 Token 序列')}
        """
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细错误信息')
    parser.add_argument('-q', '--quiet', action='store_true', help='静默模式（不显示输出）')

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # run
    p_run = subparsers.add_parser('run', help='运行光明文件')
    p_run.add_argument('file', help='光明源文件路径')
    p_run.add_argument('-q', '--quiet', action='store_true', help='不显示输出')

    # exec
    p_exec = subparsers.add_parser('exec', help='直接执行代码字符串')
    p_exec.add_argument('code', help='要执行的光明代码')
    p_exec.add_argument('-q', '--quiet', action='store_true', help='不显示输出')

    # repl
    subparsers.add_parser('repl', help='启动交互式编程环境')

    # parse
    p_parse = subparsers.add_parser('parse', help='解析并显示 AST')
    p_parse.add_argument('file', help='光明源文件路径')

    # tokenize
    p_token = subparsers.add_parser('tokenize', help='词法分析并显示 Token')
    p_token.add_argument('file', help='光明源文件路径')

    # 兼容旧模式: python main.py <file>
    if len(sys.argv) > 1 and sys.argv[1] not in ('run', 'exec', 'repl', 'parse', 'tokenize', '-v', '--verbose', '-q', '--quiet'):
        # 检测是否为已有文件路径 -> 默认为 run
        if os.path.exists(sys.argv[1]) or sys.argv[1] == '-':
            sys.argv.insert(1, 'run')
        else:
            sys.argv.insert(1, 'exec')

    args = parser.parse_args()

    try:
        if args.command == 'run':
            cmd_run(args.file, args)
        elif args.command == 'exec':
            cmd_exec(args.code, args)
        elif args.command == 'repl':
            cmd_repl(args)
        elif args.command == 'parse':
            cmd_parse(args.file, args)
        elif args.command == 'tokenize':
            cmd_tokenize(args.file, args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print()
        sys.exit(0)


if __name__ == '__main__':
    main()