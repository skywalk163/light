#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（LightLang）首次运行引导系统

功能：
- 检测是否为首次运行（使用标记文件）
- 显示欢迎横幅（ASCII art）
- 提供 3 个选项：
  1. 快速入门（5分钟交互式体验）
  2. 打开文档站
  3. 直接进入 REPL
"""

import os
import sys
import webbrowser
from typing import Optional, Tuple

# 版本号：统一从 version 模块读取，避免在横幅等处硬编码
try:
    from version import VERSION
except ImportError:  # pragma: no cover - 兼容以包方式导入的场景
    try:
        from .version import VERSION
    except ImportError:
        VERSION = "7.0.0"

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
        'star': Fore.YELLOW + Style.BRIGHT,
        'info': Fore.BLUE,
    }
except ImportError:
    C = {k: '' for k in ['title', 'section', 'code', 'output', 'tip', 'prompt',
                          'success', 'error', 'highlight', 'dim', 'reset',
                          'box', 'label', 'star', 'info']}


# =============================================================================
# 配置目录管理
# =============================================================================

def get_config_dir() -> str:
    """获取光明配置目录路径

    优先使用环境变量 LIGHT_CONFIG_DIR，否则使用 ~/.light
    """
    env_dir = os.environ.get('LIGHT_CONFIG_DIR')
    if env_dir:
        return env_dir
    return os.path.join(os.path.expanduser("~"), ".light")


def get_marker_path() -> str:
    """获取首次运行标记文件路径"""
    return os.path.join(get_config_dir(), "first_run_done")


def ensure_config_dir() -> str:
    """确保配置目录存在，返回路径"""
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


# =============================================================================
# 首次运行检测
# =============================================================================

def is_first_run() -> bool:
    """检测是否为首次运行

    Returns:
        如果标记文件不存在（即首次运行），返回 True
    """
    return not os.path.exists(get_marker_path())


def mark_first_run_done() -> None:
    """标记首次运行已完成"""
    ensure_config_dir()
    marker_path = get_marker_path()
    try:
        with open(marker_path, 'w', encoding='utf-8') as f:
            f.write("first_run_done\n")
    except OSError:
        pass  # 如果无法写入，静默失败


def reset_first_run_flag() -> None:
    """重置首次运行标记（用于测试）"""
    marker_path = get_marker_path()
    if os.path.exists(marker_path):
        try:
            os.remove(marker_path)
        except OSError:
            pass


# =============================================================================
# 欢迎横幅
# =============================================================================

WELCOME_BANNER = f"""
{C['title']}╔══════════════════════════════════════════════════════════╗{C['reset']}
{C['title']}║             🀄  光明 (LightLang)  v{VERSION}  🀄             ║{C['reset']}
{C['title']}║                                                          ║{C['reset']}
{C['title']}║       用中文写代码，让编程回归直觉                       ║{C['reset']}
{C['title']}║                                                          ║{C['reset']}
{C['title']}║     ____  _    _   _   _  _   _   _                      ║{C['reset']}
{C['title']}║    |  _ \\| |  | | | \\ | | \\ | | / /                      ║{C['reset']}
{C['title']}║    | | | | |  | | |  \\| |  \\| |/ /                       ║{C['reset']}
{C['title']}║    | |_| | |__| | | |\\  |  |   <                         ║{C['reset']}
{C['title']}║    |____/ \\____/  |_| \\_|  |_|\\_\\                        ║{C['reset']}
{C['title']}║                                                          ║{C['reset']}
{C['title']}║    中文自然语言编程 · 简单易学 · 功能强大              ║{C['reset']}
{C['title']}╚══════════════════════════════════════════════════════════╝{C['reset']}
"""


def print_welcome_banner() -> None:
    """打印欢迎横幅"""
    print(WELCOME_BANNER)
    print()


# =============================================================================
# 菜单选项
# =============================================================================

MENU_OPTIONS = {
    '1': {
        'label': '快速入门（5分钟交互式体验）',
        'description': '通过 5 个互动练习快速掌握光明基础语法',
    },
    '2': {
        'label': '打开文档站',
        'description': '在浏览器中打开光明官方文档',
    },
    '3': {
        'label': '直接进入 REPL',
        'description': '启动交互式编程环境，自由探索',
    },
}


def print_menu() -> None:
    """打印菜单选项"""
    print(f"  {C['highlight']}请选择你想做什么：{C['reset']}")
    print()
    for key, option in MENU_OPTIONS.items():
        print(f"    {C['prompt']}[{key}]{C['reset']}  {C['success']}{option['label']}{C['reset']}")
        print(f"          {C['dim']}{option['description']}{C['reset']}")
        print()
    print(f"  {C['dim']}（输入编号 1-3，或直接回车默认进入 REPL）{C['reset']}")


def get_user_choice() -> str:
    """获取用户选择"""
    try:
        choice = input(f"  {C['prompt']}请输入选择 (1/2/3) [{C['reset']}{C['success']}3{C['reset']}{C['prompt']}]: {C['reset']}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return '3'
    if not choice:
        return '3'
    return choice.strip()


# =============================================================================
# 动作执行
# =============================================================================

DOCS_URL = "https://github.com/skywalk163/light/tree/main/docs"


def run_interactive_tutorial() -> bool:
    """运行交互式快速入门教程"""
    try:
        from interactive_tutorial import run_first_run_tutorial
        return run_first_run_tutorial()
    except ImportError as e:
        print(f"\n  {C['error']}✗ 无法加载教程模块: {e}{C['reset']}")
        print(f"  {C['tip']}请确保光明已正确安装。{C['reset']}")
        return False
    except Exception as e:
        print(f"\n  {C['error']}✗ 教程运行出错: {e}{C['reset']}")
        return False


def open_docs() -> bool:
    """在浏览器中打开文档站"""
    print(f"\n  {C['info']}正在打开文档站...{C['reset']}")
    try:
        webbrowser.open(DOCS_URL)
        print(f"  {C['success']}✓ 已打开浏览器，请访问:{C['reset']}")
        print(f"  {C['code']}    {DOCS_URL}{C['reset']}")
        return True
    except Exception as e:
        print(f"  {C['error']}✗ 无法打开浏览器: {e}{C['reset']}")
        print(f"  {C['tip']}请手动访问:{C['reset']}")
        print(f"  {C['code']}    {DOCS_URL}{C['reset']}")
        return False


def start_repl() -> bool:
    """启动 REPL"""
    try:
        # 尝试导入 tools.repl（新位置）
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
        from tools.repl import LightREPL
        repl = LightREPL()
        repl.run()
        return True
    except ImportError:
        pass

    try:
        # 再尝试导入 src.repl.core
        from repl.core import LightREPL
        repl = LightREPL()
        repl.run()
        return True
    except ImportError:
        pass

    try:
        # 最终尝试 light_repl
        from light_repl import main as repl_main
        repl_main()
        return True
    except ImportError:
        print(f"  {C['error']}✗ REPL 模块不可用{C['reset']}")
        return False


# =============================================================================
# 主流程
# =============================================================================

def run_welcome() -> str:
    """运行首次运行欢迎流程

    Returns:
        返回用户选择的下一步动作：
        - 'repl': 直接进入 REPL
        - 'tutorial': 进入交互式教程
        - 'docs': 打开文档站
    """
    print_welcome_banner()

    print(f"  {C['highlight']}欢迎使用光明（LightLang）！{C['reset']}")
    print(f"  {C['dim']}光明是一门用中文自然语言编程的语言，{C['reset']}")
    print(f"  {C['dim']}让你可以用熟悉的母语来编写程序。{C['reset']}")
    print()

    while True:
        print_menu()
        choice = get_user_choice()

        if choice == '1':
            print(f"\n  {C['section']}→ 进入「快速入门」...{C['reset']}\n")
            run_interactive_tutorial()
            # 教程完成后，询问是否进入 REPL
            print(f"\n  {C['prompt']}教程已完成！是否进入 REPL 继续探索？{C['reset']}")
            try:
                go_repl = input(f"  {C['prompt']}进入 REPL？(Y/n): {C['reset']}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                go_repl = 'y'
            if go_repl in ('', 'y', 'yes', '是'):
                return 'repl'
            return 'done'

        elif choice == '2':
            open_docs()
            print(f"\n  {C['prompt']}按 Enter 返回菜单...{C['reset']}")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                print()
            continue

        elif choice == '3':
            print(f"\n  {C['section']}→ 进入 REPL...{C['reset']}\n")
            return 'repl'

        else:
            print(f"\n  {C['error']}✗ 无效选择，请输入 1、2 或 3{C['reset']}\n")


def run_first_run_or_repl() -> None:
    """检查首次运行并执行相应流程

    如果是首次运行，显示欢迎引导。
    如果已非首次（或明确使用 --welcome），直接进入 REPL。
    """
    if is_first_run():
        mark_first_run_done()
        result = run_welcome()
        if result == 'repl':
            start_repl()
    else:
        start_repl()


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description='光明首次运行引导')
    parser.add_argument('--reset', action='store_true', help='重置首次运行标记')
    args = parser.parse_args()

    if args.reset:
        reset_first_run_flag()
        print("首次运行标记已重置。下次运行 light 时将显示欢迎引导。")
        return

    run_first_run_or_repl()


if __name__ == '__main__':
    main()