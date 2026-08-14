#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
30 分钟入门段言 — 交互式教程运行器

用法：
  duan tutorial                  # 运行完整教程
  duan tutorial --step           # 逐步运行（每节暂停）
  duan tutorial --repl           # 交互式练习模式
"""

import os
import sys
import time
import argparse
import re
import json

# 路径设置：支持从源码运行和从已安装包运行
_CLI_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_CLI_DIR)

# 确保 src 和 antlrparser 在路径中
for _sub in ('src', 'antlrparser'):
    _p = os.path.join(_PROJECT_DIR, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# 颜色支持
try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    C = {
        'title': Fore.CYAN + Style.BRIGHT,
        'section': Fore.YELLOW + Style.BRIGHT,
        'code': Fore.GREEN,
        'output': Fore.WHITE,
        'tip': Fore.MAGENTA,
        'prompt': Fore.CYAN,
        'success': Fore.GREEN + Style.BRIGHT,
        'error': Fore.RED + Style.BRIGHT,
        'highlight': Fore.YELLOW,
        'dim': Fore.LIGHTBLACK_EX,
        'reset': Style.RESET_ALL,
        'box': Fore.CYAN,
        'label': Fore.BLUE + Style.BRIGHT,
        'demo': Fore.GREEN,
        'star': Fore.YELLOW + Style.BRIGHT,
    }
except ImportError:
    C = {k: '' for k in ['title', 'section', 'code', 'output', 'tip', 'prompt',
                         'success', 'error', 'highlight', 'dim', 'reset',
                         'box', 'label', 'demo', 'star']}


def _compile_duan(source: str) -> str:
    """用 src 后端编译段言代码为 Python"""
    from duan_parser_v3 import DuanParser
    from code_generator import PythonCodeGenerator

    parser = DuanParser()
    module = parser.parse(source)
    generator = PythonCodeGenerator()
    return generator.generate(module)


def _run_duan(source: str, file_path: str | None = None, namespace: dict | None = None) -> str:
    """执行段言代码，返回输出。可传入持久化 namespace 以跨调用保留变量。"""
    py_code = _compile_duan(source)
    output_lines = []

    def _capture_print(*args, **kwargs):
        line = ' '.join(str(a) for a in args)
        output_lines.append(line)

    if namespace is None:
        namespace = {}
    namespace['print'] = _capture_print
    namespace.setdefault('__name__', '__main__')
    if file_path:
        namespace['__file__'] = os.path.abspath(file_path)
    exec(py_code, namespace)
    return '\n'.join(output_lines)


def _find_tutorial() -> str:
    """查找教程文件路径"""
    path = os.path.join(_CLI_DIR, 'tutorial_30min.duan')
    if os.path.isfile(path):
        return path
    path = os.path.join(_PROJECT_DIR, 'tutorial_30min.duan')
    if os.path.isfile(path):
        return path
    raise FileNotFoundError(
        "找不到教程文件 tutorial_30min.duan。\n"
        "请确保 duan 包已正确安装：pip install duan"
    )


def run_full_tutorial():
    """运行完整教程（一次性输出）"""
    print(f"{C['title']}╔══════════════════════════════════════════════════════╗")
    print(f"║     🀄  30 分钟入门段言 — 交互式教程  🀄            ║")
    print(f"║     用中文写代码，让编程回归直觉                     ║")
    print(f"╚══════════════════════════════════════════════════════╝{C['reset']}")
    print()

    tutorial_path = _find_tutorial()
    output = _run_duan(open(tutorial_path, encoding='utf-8').read(), tutorial_path)
    print(output)


def run_step_by_step():
    """逐步运行教程（每节暂停）"""
    tutorial_path = _find_tutorial()
    source = open(tutorial_path, encoding='utf-8').read()

    sections = []
    current_section = ""
    for line in source.split('\n'):
        if line.strip().startswith('#  第') and '节' in line:
            if current_section:
                sections.append(current_section)
            current_section = line + '\n'
        elif current_section is not None:
            current_section += line + '\n'
    if current_section:
        sections.append(current_section)

    if not sections:
        print("无法解析教程章节，使用完整运行模式。")
        run_full_tutorial()
        return

    for i, section in enumerate(sections):
        for line in section.split('\n'):
            stripped = line.strip()
            if stripped.startswith('#  第') and '节' in stripped:
                title = stripped.lstrip('# ')
                print(f"\n{C['section']}━━━ {title} ━━━{C['reset']}")
                break

        try:
            output = _run_duan(section)
            print(output)
        except Exception as e:
            print(f"{C['error']}运行出错: {e}{C['reset']}")

        if i < len(sections) - 1:
            input(f"\n{C['prompt']}按 Enter 继续下一节...{C['reset']}")


# ═══════════════════════════════════════════════════════════════════
# 友好的中文错误提示（扩充版）
# ═══════════════════════════════════════════════════════════════════

def _friendly_error(e: Exception) -> str:
    """将 Python 异常转换为中文友好的提示"""
    msg = str(e)

    if 'is not defined' in msg:
        m = re.search(r"name '(.+?)' is not defined", msg)
        if m:
            name = m.group(1)
            return (f"未定义的变量「{name}」\n"
                    f"  提示：请先用 [设 {name} 为 ...] 声明这个变量\n"
                    f"  示例：设 {name} 为 \"值\"")
    if 'is not callable' in msg or 'not callable' in msg:
        return f"调用方式错误\n  提示：请检查是否把变量名当函数名用了，或者忘记写操作符"
    if 'invalid syntax' in msg.lower():
        return (f"语法错误\n"
                f"  提示：请检查关键字拼写、冒号、缩进是否正确\n"
                f"  常见错误：\n"
                f"    • 漏写冒号「：」\n"
                f"    • 缩进不是 4 个空格\n"
                f"    • 括号不匹配")
    if 'unexpected indent' in msg.lower():
        return (f"缩进错误\n"
                f"  提示：段言用 4 个空格缩进，请检查代码块缩进是否一致\n"
                f"  注意：不要混用空格和 Tab！")
    if 'unexpected EOF' in msg.lower() or 'EOF while' in msg.lower():
        return (f"代码不完整\n"
                f"  提示：可能是缺少冒号、缩进块不完整，或括号没闭合\n"
                f"  如果是多行代码，请用「>>>」进入多行模式再写")
    if 'can only concatenate str' in msg.lower() or "can't multiply" in msg.lower():
        return (f"类型错误：不能把数字和字符串直接拼接\n"
                f"  提示：用 [转字符串(数字)] 或 [转数字(字符串)] 转换类型\n"
                f"  示例：打印(\"结果：\" 加上 转字符串(42))")
    if 'TypeError' in msg:
        if 'argument' in msg.lower():
            return (f"参数类型错误：{msg}\n"
                    f"  提示：请检查函数参数的类型和数量是否正确")
        return f"类型错误：{msg}\n  提示：请检查运算类型是否匹配"
    if 'NameError' in msg:
        return f"名称错误：{msg}\n  提示：请检查变量名是否正确拼写，是否已声明"
    if 'ZeroDivisionError' in msg or 'division by zero' in msg.lower():
        return (f"除数不能为零\n"
                f"  提示：请检查除数是否为 0，或使用「尝试...捕获」处理异常")
    if 'IndexError' in msg or 'list index out of range' in msg.lower():
        return (f"索引越界\n"
                f"  提示：请检查列表索引是否在有效范围内（从 0 开始）\n"
                f"  使用 [列表长度(列表)] 查看列表长度")
    if 'KeyError' in msg:
        return (f"键不存在\n"
                f"  提示：字典中没有这个键，请检查键名是否正确")
    if 'AttributeError' in msg:
        return (f"属性错误：{msg}\n"
                f"  提示：请检查对象类型是否正确，是否调用了不存在的方法")
    if 'ValueError' in msg:
        return (f"值错误：{msg}\n"
                f"  提示：请检查传入的值是否符合预期格式")
    if 'IndentationError' in msg:
        return (f"缩进错误\n"
                f"  提示：段言代码块需要 4 个空格缩进，请确保缩进统一")
    return f"出错啦：{msg}"


# ═══════════════════════════════════════════════════════════════════
# 进度条
# ═══════════════════════════════════════════════════════════════════

def _progress_bar(current: int, total: int, completed: set, width: int = 30) -> str:
    """生成进度条字符串"""
    done = len(completed)
    filled = int(width * done / total)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {done}/{total}"


# ═══════════════════════════════════════════════════════════════════
# 获取用户定义的变量名列表（用于状态展示）
# ═══════════════════════════════════════════════════════════════════

def _user_vars(namespace: dict) -> list:
    """返回命名空间中用户定义的变量名"""
    builtins = {'print', '__name__', '__file__', '__builtins__'}
    return [k for k in namespace if not k.startswith('__') and k not in builtins and not callable(namespace.get(k))]


# ═══════════════════════════════════════════════════════════════════
# 进度保存与恢复
# ═══════════════════════════════════════════════════════════════════

PROGRESS_FILE = os.path.join(os.path.expanduser("~"), ".duan_tutorial_progress")


def _save_progress(current_exercise: int, completed: set):
    """保存教程进度"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'current': current_exercise, 'completed': list(completed)}, f)
    except Exception:
        pass


def _load_progress() -> dict:
    """加载教程进度"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'current': 0, 'completed': []}


def _clear_progress():
    """清除进度文件"""
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# 练习完成度检查（多模式）
# ═══════════════════════════════════════════════════════════════════

def _check_exercise(exercise: dict, output: str, namespace: dict) -> bool:
    """检查练习是否完成，支持多种检查模式"""
    # Mode 1: exact output match
    if 'expected_exact' in exercise:
        return output.strip() == exercise['expected_exact'].strip()

    # Mode 2: variable value check
    if 'check_vars' in exercise:
        for var_name, expected_val in exercise['check_vars'].items():
            if var_name not in namespace or namespace[var_name] != expected_val:
                return False
        return True

    # Mode 3: all expected lines must appear in output
    if 'expected_lines' in exercise:
        output_lines = [l.strip() for l in output.strip().split('\n')]
        for expected_line in exercise['expected_lines']:
            if expected_line.strip() not in output_lines:
                return False
        return True

    # Fallback: substring match (legacy)
    if 'expected' in exercise:
        return exercise['expected'] in output
    return False


# ═══════════════════════════════════════════════════════════════════
# 交互式练习模式
# ═══════════════════════════════════════════════════════════════════

def interactive_repl():
    """交互式练习模式"""

    # ── 欢迎画面 ──
    print(f"{C['title']}╔══════════════════════════════════════════════════════════╗")
    print(f"║       🀄  30 分钟入门段言 — 交互式练习  🀄              ║")
    print(f"║       用中文写代码，让编程回归直觉                       ║")
    print(f"╚══════════════════════════════════════════════════════════╝{C['reset']}")
    print()
    print(f"  {C['highlight']}欢迎来到段言互动课堂！{C['reset']}")
    print(f"  段言（Duan）是一门用中文写代码的编程语言。")
    print(f"  在这个练习中，你会依次学到：")
    print()
    print(f"    {C['success']}→{C['reset']}  变量、运算、条件、循环、函数、列表")
    print(f"    {C['success']}→{C['reset']}  字符串、字典、枚举、异常、综合挑战")
    print()
    print(f"  {C['dim']}怎么玩？{C['reset']}")
    print(f"  {C['dim']}  • 直接输入段言代码，按 Enter 执行{C['reset']}")
    print(f"  {C['dim']}  • 输入 >>> 进入多行模式（适合写 if/for/段落）{C['reset']}")
    print(f"  {C['dim']}  • 输入 demo 查看正确答案参考{C['reset']}")
    print(f"  {C['dim']}  • 输入 next/prev 切换练习，reset 清空变量{C['reset']}")
    print(f"  {C['dim']}  • 输入 help 查看帮助，quit 退出{C['reset']}")
    print()
    print(f"  {C['star']}✨ 不会写？输入 demo 看答案，再自己试试！{C['reset']}")
    print()

    # ── 练习列表（16 个，从基础到进阶） ──
    exercises = [
        # ── 练习 1: 变量与赋值 ──
        {
            'title': '变量与赋值',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  段言用「设 变量名 为 值」来声明变量。\n"
                f"  用「打印(内容)」来输出内容到屏幕。\n"
                f"  变量名可以用中文，如：设 名字 为 \"小明\""
            ),
            'goal': '声明一个变量 x，赋值为 42，然后打印它',
            'hint': '设 x 为 42\n打印(x)',
            'demo_code': '设 x 为 42\n打印(x)',
            'expected_exact': '42',
        },
        # ── 练习 2: 算术运算 ──
        {
            'title': '算术运算',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  段言支持中文运算符：加(+)、减(-)、乘(×)、除(÷)。\n"
                f"  也可以用符号：+ - * / \n"
                f"  取余用「取余」，如：10 取余 3 得 1"
            ),
            'goal': '计算 10 + 3 的结果并打印',
            'hint': '设 a 为 10\n设 b 为 3\n打印(a 加 b)',
            'demo_code': '设 a 为 10\n设 b 为 3\n打印(a 加 b)',
            'expected_exact': '13',
        },
        # ── 练习 3: 字符串 ──
        {
            'title': '字符串操作',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  字符串用双引号 \"...\" 或单引号 '...' 包裹。\n"
                f"  用 + 号拼接字符串。\n"
                f"  用「转字符串(数字)」把数字变成字符串。"
            ),
            'goal': '用字符串拼接输出 "你好, 世界"',
            'hint': '设 name 为 "世界"\n打印("你好, " + name)',
            'demo_code': '设 name 为 "世界"\n打印("你好, " + name)',
            'expected_exact': '你好, 世界',
        },
        # ── 练习 4: 条件判断 ──
        {
            'title': '条件判断',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  「如果 条件:」为真时执行缩进块。\n"
                f"  「否则:」处理不满足条件的情况。\n"
                f"  「否则 如果」处理多个分支。\n"
                f"  比较运算符：>、<、>=、<=、==、!=（不等于）"
            ),
            'goal': '判断年龄是否成年（>=18岁）',
            'hint': '设 age 为 18\n如果 age >= 18:\n    打印("成年")\n否则:\n    打印("未成年")',
            'demo_code': '设 age 为 18\n如果 age >= 18:\n    打印("成年")\n否则:\n    打印("未成年")',
            'expected_exact': '成年',
        },
        # ── 练习 5: 列表与遍历 ──
        {
            'title': '列表与遍历',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  列表用方括号 [] 创建，如 [1, 2, 3]。\n"
                f"  「遍历 项 在 列表:」循环遍历每个元素。\n"
                f"  索引从 0 开始，如 列表[0] 取第一个元素。"
            ),
            'goal': '遍历列表 [1,2,3,4,5] 并求和',
            'hint': '设 total 为 0\n遍历 i 在 [1, 2, 3, 4, 5]:\n    设 total 为 total 加 i\n打印(total)',
            'demo_code': '设 total 为 0\n遍历 i 在 [1, 2, 3, 4, 5]:\n    设 total 为 total 加 i\n打印(total)',
            'expected_exact': '15',
        },
        # ── 练习 6: 函数（段落） ──
        {
            'title': '函数（段落）',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  段言用「段落」关键字定义函数。\n"
                f"  语法：段落 函数名(参数): ... 返回 值\n"
                f"  调用：函数名(参数)"
            ),
            'goal': '定义一个 greet 函数，返回问候语',
            'hint': '段落 greet(name):\n    返回 "你好, " + name\n打印(greet("段言"))',
            'demo_code': '段落 greet(name):\n    返回 "你好, " + name\n打印(greet("段言"))',
            'expected_exact': '你好, 段言',
        },
        # ── 练习 7: 列表索引 ──
        {
            'title': '列表索引',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  列表用 索引 访问元素，从 0 开始。\n"
                f"  列表[0] 取第一个，列表[-1] 取最后一个。\n"
                f"  「列表长度(列表)」获取列表长度。"
            ),
            'goal': '创建水果列表并打印第一个水果',
            'hint': '设 fruits 为 ["苹果", "香蕉", "橘子"]\n打印(fruits[0])',
            'demo_code': '设 fruits 为 ["苹果", "香蕉", "橘子"]\n打印(fruits[0])',
            'expected_exact': '苹果',
        },
        # ── 练习 8: while 循环 ──
        {
            'title': 'while 循环',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  「当 条件:」当条件为真时重复执行。\n"
                f"  注意：循环体中要修改条件变量，否则会死循环！\n"
                f"  「设 i 为 i 加 1」相当于 i += 1"
            ),
            'goal': '用 while 循环计算 1+2+3+4+5 的和',
            'hint': '设 i 为 1\n设 sum 为 0\n当 i <= 5:\n    设 sum 为 sum 加 i\n    设 i 为 i 加 1\n打印(sum)',
            'demo_code': '设 i 为 1\n设 sum 为 0\n当 i <= 5:\n    设 sum 为 sum 加 i\n    设 i 为 i 加 1\n打印(sum)',
            'expected_exact': '15',
        },
        # ── 练习 9: 字典 ──
        {
            'title': '字典',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                "  字典用花括号 {} 创建，存储键值对。\n"
                '  如 {"名字": "小明", "年龄": 18}\n'
                f"  用 字典[键] 访问对应的值。"
            ),
            'goal': '创建成绩字典并打印 Alice 的分数',
            'hint': '设 scores 为 {"Alice": 90, "Bob": 85}\n打印(scores["Alice"])',
            'demo_code': '设 scores 为 {"Alice": 90, "Bob": 85}\n打印(scores["Alice"])',
            'expected_exact': '90',
        },
        # ── 练习 10: 枚举遍历 ──
        {
            'title': '枚举遍历',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  「枚举(列表)」同时获取索引和元素。\n"
                f"  语法：遍历 索引, 元素 在 枚举(列表):\n"
                f"  「转字符串(数字)」把数字转为字符串用于拼接。"
            ),
            'goal': '用枚举遍历颜色列表，输出 "0: 红" 格式',
            'hint': '设 colors 为 ["红", "绿", "蓝"]\n遍历 idx, color 在 枚举(colors):\n    打印(转字符串(idx) + ": " + color)',
            'demo_code': '设 colors 为 ["红", "绿", "蓝"]\n遍历 idx, color 在 枚举(colors):\n    打印(转字符串(idx) + ": " + color)',
            'expected_lines': ['0: 红', '1: 绿', '2: 蓝'],
        },
        # ── 练习 11: FizzBuzz ──
        {
            'title': 'FizzBuzz 挑战',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  经典编程题：遍历 1 到 15 的数字：\n"
                f"  - 能被 15 整除 → 打印 FizzBuzz\n"
                f"  - 能被 3 整除 → 打印 Fizz\n"
                f"  - 能被 5 整除 → 打印 Buzz\n"
                f"  - 否则打印数字本身\n"
                f"  「取余」运算：10 取余 3 得 1"
            ),
            'goal': '完成 FizzBuzz 程序',
            'hint': '遍历 i 在 [1, 2, 3, 4, 5, 15]:\n    如果 i 取余 15 == 0:\n        打印("FizzBuzz")\n    否则 如果 i 取余 3 == 0:\n        打印("Fizz")\n    否则 如果 i 取余 5 == 0:\n        打印("Buzz")\n    否则:\n        打印(转字符串(i))',
            'demo_code': '遍历 i 在 [1, 2, 3, 4, 5, 15]:\n    如果 i 取余 15 == 0:\n        打印("FizzBuzz")\n    否则 如果 i 取余 3 == 0:\n        打印("Fizz")\n    否则 如果 i 取余 5 == 0:\n        打印("Buzz")\n    否则:\n        打印(转字符串(i))',
            'expected_lines': ['1', '2', 'Fizz', '4', 'Buzz', 'FizzBuzz'],
        },
        # ── 练习 12: 异常处理 ──
        {
            'title': '异常处理',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                "  「尝试: ... 捕获 异常类型 为 变量:」处理错误。\n"
                "  相当于 Python 的 try/except。\n"
                '  「抛出 异常("消息")」主动抛出异常。\n'
                "  常见异常类型：Exception, ValueError, ZeroDivisionError"
            ),
            'goal': '用 try-except 捕获除零错误',
            'hint': '尝试:\n    设 结果 为 10 除以 0\n捕获 Exception 为 e:\n    打印("不能除以零！")',
            'demo_code': '尝试:\n    设 结果 为 10 除以 0\n捕获 Exception 为 e:\n    打印("不能除以零！")',
            'expected_exact': '不能除以零！',
        },
        # ── 练习 13: 文件读写 ──
        {
            'title': '文件读写',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  「写入文件(路径, 内容)」写入文件。\n"
                f"  「读取文件(路径)」读取文件内容。\n"
                f"  「文件存在(路径)」检查文件是否存在。\n"
                f"  注意：路径用字符串，如 \"data.txt\""
            ),
            'goal': '写入文件再读回内容',
            'hint': '写入文件("todo_test.txt", "买菜\\n写代码")\n设 content 为 读取文件("todo_test.txt")\n打印(content)',
            'demo_code': '写入文件("todo_test.txt", "买菜\\n写代码")\n设 content 为 读取文件("todo_test.txt")\n打印(content)',
            'expected_exact': '买菜\n写代码',
        },
        # ── 练习 14: 模块导入 ──
        {
            'title': '模块导入',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  「导入 模块名」导入标准库模块。\n"
                f"  如：导入 数学、导入 json、导入 os\n"
                f"  导入后用「模块名.函数()」调用。\n"
                f"  如：数学.圆周率() 返回 pi 值"
            ),
            'goal': '导入数学模块并打印圆周率',
            'hint': '导入 数学\n设 pi 为 数学.圆周率()\n打印(转字符串(pi))',
            'demo_code': '导入 数学\n设 pi 为 数学.圆周率()\n打印(转字符串(pi))',
            'expected_exact': '3.141592653589793',
        },
        # ── 练习 15: 列表推导式 ──
        {
            'title': '列表推导式',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  段言支持列表推导式（简洁的列表生成方式）。\n"
                f"  语法：[表达式 遍历 变量 在 列表]\n"
                f"  如：[x 乘 x 遍历 x 在 [1,2,3]] 生成 [1, 4, 9]\n"
                f"  相当于 Python 的 [x*x for x in [1,2,3]]"
            ),
            'goal': '用列表推导式生成 1-5 的平方数列表',
            'hint': '设 numbers 为 [1, 2, 3, 4, 5]\n设 squares 为 [x 乘 x 遍历 x 在 numbers]\n打印(squares)',
            'demo_code': '设 numbers 为 [1, 2, 3, 4, 5]\n设 squares 为 [x 乘 x 遍历 x 在 numbers]\n打印(squares)',
            'expected_exact': '[1, 4, 9, 16, 25]',
        },
        # ── 练习 16: 综合实战 — 待办列表 ──
        {
            'title': '综合实战 — 待办列表',
            'knowledge': (
                f"  {C['label']}📖 知识讲堂{C['reset']}\n"
                f"  综合运用：变量、列表、函数、循环、枚举。\n"
                f"  实现一个简单的待办列表程序：\n"
                f"  - 用列表存储任务\n"
                f"  - 用段落（函数）添加任务\n"
                f"  - 用枚举遍历打印所有任务\n"
                f"  - 用列表长度统计任务数量"
            ),
            'goal': '实现一个待办列表程序',
            'hint': '设 todos 为 []\n段落 添加任务(任务):\n    todos.添加(任务)\n    打印("已添加: " + 任务)\n添加任务("学习段言")\n添加任务("写第一个程序")\n遍历 idx, task 在 枚举(todos):\n    打印(转字符串(idx 加 1) + ". " + task)\n打印("共 " + 转字符串(列表长度(todos)) + " 个任务")',
            'demo_code': '设 todos 为 []\n段落 添加任务(任务):\n    todos.添加(任务)\n    打印("已添加: " + 任务)\n添加任务("学习段言")\n添加任务("写第一个程序")\n遍历 idx, task 在 枚举(todos):\n    打印(转字符串(idx 加 1) + ". " + task)\n打印("共 " + 转字符串(列表长度(todos)) + " 个任务")',
            'expected_lines': ['已添加: 学习段言', '已添加: 写第一个程序', '1. 学习段言', '2. 写第一个程序', '共 2 个任务'],
        },
    ]

    # ── 进度恢复 ──
    progress = _load_progress()
    saved_completed = set(progress.get('completed', []))
    saved_current = progress.get('current', 0)

    exercise_idx = 0
    multi_line = False
    multi_line_buffer = ""
    multi_line_count = 0
    repl_namespace = {}
    completed = set()
    error_count = 0  # 当前练习连续出错次数

    # 如果有保存的进度，提示用户
    if saved_completed and len(saved_completed) < 16:
        print(f"  {C['highlight']}📂 检测到上次的学习进度：已完成 {len(saved_completed)}/16 个练习{C['reset']}")
        print(f"  {C['dim']}输入 continue 继续，输入 restart 重新开始{C['reset']}")
        while True:
            try:
                choice = input(f"{C['prompt']}选择> {C['reset']}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if choice == 'continue' or choice == '':
                completed = saved_completed
                exercise_idx = saved_current if saved_current < 16 else 0
                print(f"  {C['success']}✓ 已恢复进度，从练习 {exercise_idx + 1} 继续{C['reset']}")
                break
            elif choice == 'restart':
                _clear_progress()
                print(f"  {C['success']}✓ 已清除旧进度，从头开始{C['reset']}")
                break
            elif choice == 'list':
                print(f"  {C['dim']}已完成: {sorted([i+1 for i in completed])}{C['reset']}")
            else:
                print(f"  {C['dim']}请输入 continue 或 restart{C['reset']}")
        print()

    # ── 上次运行结果缓存 ──
    last_output = ""

    while True:
        total = len(exercises)

        # ── 显示练习信息 ──
        if not multi_line and exercise_idx < total:
            ex = exercises[exercise_idx]
            done_mark = f" {C['success']}✓{C['reset']}" if exercise_idx in completed else ""

            # 进度条
            bar = _progress_bar(exercise_idx, total, completed)
            print(f"\n{C['dim']}  进度 {bar}{C['reset']}")

            print(f"{C['section']}━━━ {ex['title']} ({exercise_idx + 1}/{total}){done_mark} ━━━{C['reset']}")

            # 知识讲堂
            print(f"\n{ex['knowledge']}")

            print(f"  {C['highlight']}🎯 目标：{C['reset']}{ex['goal']}")
            print(f"  {C['tip']}💡 提示：{C['reset']}")
            for line in ex['hint'].split('\n'):
                print(f"  {C['tip']}{line}{C['reset']}")
            print(f"  {C['dim']}──────────────────────────────────────────────{C['reset']}")

        # ── 获取输入 ──
        try:
            if multi_line:
                prompt = f"{C['prompt']}{multi_line_count + 1:>2}│ {C['reset']}"
                user_input = input(prompt)
            else:
                user_input = input(f"{C['prompt']}段言> {C['reset']}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C['success']}再见！期待下次一起写段言 🀄{C['reset']}")
            break

        # ── 多行模式：空行结束 ──
        if multi_line and user_input.strip() == '':
            multi_line = False
            code = multi_line_buffer
            multi_line_buffer = ""
            multi_line_count = 0
            if code.strip():
                try:
                    output = _run_duan(code, namespace=repl_namespace)
                    last_output = output
                    error_count = 0
                    if output:
                        print(f"{C['output']}{output}{C['reset']}")
                        # 检查是否完成当前练习
                        if exercise_idx < total:
                            ex = exercises[exercise_idx]
                            if _check_exercise(ex, output, repl_namespace) and exercise_idx not in completed:
                                completed.add(exercise_idx)
                                _save_progress(exercise_idx, completed)
                                print(f"\n  {C['success']}🎉 太棒了！你完成了 {ex['title']}！{C['reset']}")
                                if exercise_idx < total - 1:
                                    print(f"  {C['dim']}输入 next 进入下一题，或继续自由练习{C['reset']}")
                                else:
                                    _show_completion_summary(total, completed)
                    else:
                        print(f"{C['success']}✓ 执行成功{C['reset']}")
                except Exception as e:
                    error_count += 1
                    print(f"{C['error']}✗ {_friendly_error(e)}{C['reset']}")
                    _check_error_hint(error_count, exercise_idx, exercises)
            continue

        # ── 空输入 ──
        if user_input.strip() == '':
            continue

        # ── 命令：quit ──
        if user_input.strip().lower() == 'quit':
            done_count = len(completed)
            if done_count > 0:
                print(f"\n{C['success']}本次完成了 {done_count}/{total} 个练习，很棒！{C['reset']}")
            print(f"{C['success']}再见！期待下次一起写段言 🀄{C['reset']}")
            break

        # ── 命令：help ──
        if user_input.strip().lower() == 'help':
            _show_help(total, completed)
            continue

        # ── 命令：demo ──
        if user_input.strip().lower() == 'demo':
            if exercise_idx < total:
                ex = exercises[exercise_idx]
                print(f"\n  {C['demo']}📖 参考答案：{C['reset']}")
                for line in ex['demo_code'].split('\n'):
                    print(f"  {C['demo']}  {line}{C['reset']}")
                print(f"\n  {C['dim']}  试试自己写一遍？输入你的代码来练习！{C['reset']}")
            continue

        # ── 命令：reset ──
        if user_input.strip().lower() == 'reset':
            repl_namespace = {}
            multi_line = False
            multi_line_buffer = ""
            multi_line_count = 0
            error_count = 0
            print(f"  {C['success']}✓ 变量已清空，可以重新开始当前练习{C['reset']}")
            continue

        # ── 命令：next ──
        if user_input.strip().lower() == 'next':
            if exercise_idx < total - 1:
                exercise_idx += 1
                repl_namespace = {}
                multi_line = False
                multi_line_buffer = ""
                multi_line_count = 0
                error_count = 0
                print(f"  {C['dim']}→ 进入 {exercises[exercise_idx]['title']}{C['reset']}")
            else:
                print(f"  {C['success']}🎉 这已经是最后一题了！所有练习都完成了！{C['reset']}")
                if len(completed) >= total:
                    _show_completion_summary(total, completed)
            continue

        # ── 命令：prev ──
        if user_input.strip().lower() == 'prev':
            if exercise_idx > 0:
                exercise_idx -= 1
                repl_namespace = {}
                multi_line = False
                multi_line_buffer = ""
                multi_line_count = 0
                error_count = 0
                print(f"  {C['dim']}← 回到 {exercises[exercise_idx]['title']}{C['reset']}")
            else:
                print(f"  {C['dim']}已经在第一题了{C['reset']}")
            continue

        # ── 命令：>>> ──
        if user_input.strip() == '>>>':
            multi_line = True
            multi_line_buffer = ""
            multi_line_count = 0
            print(f"  {C['tip']}📝 多行模式（输入空行执行，输入 quit 退出多行）{C['reset']}")
            continue

        # ── 多行模式：收集代码 ──
        if multi_line:
            multi_line_buffer += user_input + '\n'
            multi_line_count += 1
            continue

        # ── 单行代码执行 ──
        try:
            output = _run_duan(user_input, namespace=repl_namespace)
            last_output = output
            error_count = 0
            if output:
                print(f"{C['output']}{output}{C['reset']}")
                # 检查是否完成当前练习
                if exercise_idx < total:
                    ex = exercises[exercise_idx]
                    if _check_exercise(ex, output, repl_namespace) and exercise_idx not in completed:
                        completed.add(exercise_idx)
                        _save_progress(exercise_idx, completed)
                        print(f"\n  {C['success']}🎉 太棒了！你完成了 {ex['title']}！{C['reset']}")
                        if exercise_idx < total - 1:
                            print(f"  {C['dim']}输入 next 进入下一题，或继续自由练习{C['reset']}")
                        else:
                            _show_completion_summary(total, completed)
            else:
                print(f"{C['success']}✓ 执行成功{C['reset']}")
        except Exception as e:
            error_count += 1
            print(f"{C['error']}✗ {_friendly_error(e)}{C['reset']}")
            _check_error_hint(error_count, exercise_idx, exercises)


def _show_help(total: int, completed: set):
    """显示帮助信息"""
    print(f"\n  {C['highlight']}📖 命令帮助{C['reset']}")
    print(f"  {C['dim']}──────────────────────────────────────────────{C['reset']}")
    print(f"  {C['success']}help     {C['reset']} 显示此帮助")
    print(f"  {C['success']}demo     {C['reset']} 查看当前练习的参考答案")
    print(f"  {C['success']}next     {C['reset']} 进入下一题")
    print(f"  {C['success']}prev     {C['reset']} 回到上一题")
    print(f"  {C['success']}reset    {C['reset']} 清空所有变量，重新开始")
    print(f"  {C['success']}quit     {C['reset']} 退出教程")
    print(f"  {C['success']}>>>      {C['reset']} 进入多行模式（写 if/for/段落 用）")
    print(f"  {C['dim']}──────────────────────────────────────────────{C['reset']}")
    print(f"  {C['tip']}直接输入段言代码即可执行！{C['reset']}")
    print(f"  {C['tip']}变量会跨行保留，方便分步操作。{C['reset']}")
    print(f"  {C['tip']}不会写？输入 demo 看答案，再自己试试！{C['reset']}")
    print(f"  {C['dim']}  进度：{len(completed)}/{total} 个练习已完成{C['reset']}")


def _check_error_hint(error_count: int, exercise_idx: int, exercises: list):
    """当连续出错时给出更具体的提示"""
    if error_count >= 3 and exercise_idx < len(exercises):
        ex = exercises[exercise_idx]
        print(f"\n  {C['star']}💡 遇到困难？试试输入 demo 查看参考答案{C['reset']}")
        print(f"  {C['star']}   也可以输入 help 查看更多帮助{C['reset']}")


def _show_completion_summary(total: int, completed: set):
    """显示完成所有练习的总结"""
    print(f"\n  {C['title']}╔══════════════════════════════════════════════════════════╗")
    print(f"  ║       🎉 恭喜！你完成了全部 {total} 个练习！🎉            ║")
    print(f"  ╚══════════════════════════════════════════════════════════╝{C['reset']}")
    print()
    print(f"  {C['success']}你已经学会了：{C['reset']}")
    print(f"  {C['success']}  ✅ 变量声明与赋值          ✅ 算术运算{C['reset']}")
    print(f"  {C['success']}  ✅ 条件判断                ✅ 循环遍历{C['reset']}")
    print(f"  {C['success']}  ✅ 段落（函数）定义        ✅ 列表操作{C['reset']}")
    print(f"  {C['success']}  ✅ 字符串拼接              ✅ 字典访问{C['reset']}")
    print(f"  {C['success']}  ✅ 枚举遍历                ✅ 异常处理{C['reset']}")
    print(f"  {C['success']}  ✅ 文件读写                ✅ 模块导入{C['reset']}")
    print(f"  {C['success']}  ✅ 列表推导式              ✅ 综合实战{C['reset']}")
    print()
    print(f"  {C['highlight']}📚 下一步：{C['reset']}")
    print(f"  {C['dim']}  • 运行 duan repl 进入交互式解释器，自由探索{C['reset']}")
    print(f"  {C['dim']}  • 运行 duan tutorial 查看完整教程内容{C['reset']}")
    print(f"  {C['dim']}  • 访问 https://github.com/skywalk163/duan 查看更多资源{C['reset']}")
    print()


def main():
    parser = argparse.ArgumentParser(description='30 分钟入门段言 — 交互式教程')
    parser.add_argument('--step', action='store_true', help='逐步运行（每节暂停）')
    parser.add_argument('--repl', action='store_true', help='交互式练习模式')
    parser.add_argument('--full', action='store_true', help='一次性运行完整教程（默认）')
    args = parser.parse_args()

    if args.repl:
        interactive_repl()
    elif args.step:
        run_step_by_step()
    else:
        run_full_tutorial()


if __name__ == '__main__':
    main()