"""
命令行参数 — lightpub 桥接模块

基于 Python argparse 库封装，函数名对齐上游 duanpub（段言时期）packages/命令行参数/源.duan。

上游 duanpub 原始包通过 C FFI 实现命令行参数解析，
本桥接模块用 Python argparse 标准库替代，提供等价的参数解析功能。
"""

import argparse as _argparse
import sys as _sys


# =============================================================================
# 数据结构
# =============================================================================

class _ArgumentDefinition:
    """参数定义"""
    def __init__(self, name):
        self.name = name
        self.short_name = None
        self.default = None
        self.required = False
        self.help_text = ''
        self.type = str


class _SubCommand:
    """子命令"""
    def __init__(self, name, help_text=''):
        self.name = name
        self.help_text = help_text
        self.arguments = []


# =============================================================================
# 参数定义
# =============================================================================

def 新建参数定义(name):
    """新建一个参数定义"""
    return _ArgumentDefinition(name)


def 设置短名称(arg, short_name):
    """设置参数的短名称"""
    if not isinstance(arg, _ArgumentDefinition):
        raise Exception("设置短名称失败: 参数定义无效")
    arg.short_name = short_name
    return arg


def 设置默认值(arg, default):
    """设置参数的默认值"""
    if not isinstance(arg, _ArgumentDefinition):
        raise Exception("设置默认值失败: 参数定义无效")
    arg.default = default
    return arg


def 设置必需(arg, required=True):
    """设置参数为必需"""
    if not isinstance(arg, _ArgumentDefinition):
        raise Exception("设置必需失败: 参数定义无效")
    arg.required = required
    return arg


# =============================================================================
# 子命令
# =============================================================================

def 新建子命令(name, help_text=''):
    """新建一个子命令"""
    return _SubCommand(name, help_text)


def 子命令添加参数(subcmd, arg):
    """为子命令添加参数"""
    if not isinstance(subcmd, _SubCommand):
        raise Exception("子命令添加参数失败: 子命令无效")
    if not isinstance(arg, _ArgumentDefinition):
        raise Exception("子命令添加参数失败: 参数定义无效")
    subcmd.arguments.append(arg)
    return subcmd


# =============================================================================
# 解析参数
# =============================================================================

def 解析参数(程序名, 参数列表, 子命令列表=None, 描述=''):
    """
    解析命令行参数，返回参数字典。

    参数列表通常为 sys.argv[1:]。
    """
    parser = _argparse.ArgumentParser(prog=程序名, description=描述)

    if 子命令列表:
        subparsers = parser.add_subparsers(dest='command', help='子命令')
        for subcmd in 子命令列表:
            sp = subparsers.add_parser(subcmd.name, help=subcmd.help_text)
            for arg_def in subcmd.arguments:
                args = ['--' + arg_def.name]
                if arg_def.short_name:
                    args.append('-' + arg_def.short_name)
                kwargs = {}
                if arg_def.default is not None:
                    kwargs['default'] = arg_def.default
                if arg_def.required:
                    kwargs['required'] = True
                kwargs['help'] = arg_def.help_text or ''
                sp.add_argument(*args, **kwargs)
    else:
        # 没有子命令时，直接解析位置参数
        parser.add_argument('args', nargs='*', help='位置参数')

    try:
        parsed = parser.parse_args(参数列表)
        return vars(parsed)
    except _argparse.ArgumentError as e:
        raise Exception("解析参数失败: " + str(e))
    except SystemExit:
        # argparse 遇到 -h 或错误时会调用 sys.exit
        return {}


def 获取参数值(参数字典, key, 默认值=None):
    """从参数字典获取指定参数的值"""
    return 参数字典.get(key, 默认值)


def 生成帮助文本(程序名, 参数列表, 子命令列表=None, 描述=''):
    """生成帮助文本（不退出程序）"""
    parser = _argparse.ArgumentParser(prog=程序名, description=描述, add_help=False)

    if 子命令列表:
        subparsers = parser.add_subparsers(dest='command')
        for subcmd in 子命令列表:
            sp = subparsers.add_parser(subcmd.name, help=subcmd.help_text, add_help=False)
            for arg_def in subcmd.arguments:
                args = ['--' + arg_def.name]
                if arg_def.short_name:
                    args.append('-' + arg_def.short_name)
                kwargs = {}
                if arg_def.default is not None:
                    kwargs['default'] = arg_def.default
                kwargs['help'] = arg_def.help_text or ''
                sp.add_argument(*args, **kwargs)

    try:
        return parser.format_help()
    except Exception as e:
        raise Exception("生成帮助文本失败: " + str(e))