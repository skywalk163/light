# -*- coding: utf-8 -*-
"""
光明标准库 - 信号处理模块

提供信号注册、发送和处理功能。
"""

import signal
import sys
from typing import Callable, Optional, Dict, Any


# 保存原始信号处理器
_原始处理器 = {}


def 注册信号处理器(信号编号: int, 处理器: Callable) -> Any:
    """
    注册信号处理器

    参数:
        信号编号: 信号编号（如 signal.SIGINT）
        处理器: 处理函数，签名 handler(signum, frame)

    返回:
        之前的信号处理器

    示例:
        def 处理中断(signum, frame):
            打印('收到中断信号')

        注册信号处理器(signal.SIGINT, 处理中断)
    """
    try:
        旧处理器 = signal.signal(信号编号, 处理器)
        _原始处理器[信号编号] = 旧处理器
        return 旧处理器
    except ValueError:
        raise RuntimeError(f"无法注册信号 {信号编号}（非主线程或信号不支持）")


def 恢复信号处理器(信号编号: int):
    """
    恢复信号的默认处理器

    参数:
        信号编号: 信号编号
    """
    if 信号编号 in _原始处理器:
        signal.signal(信号编号, _原始处理器[信号编号])
        del _原始处理器[信号编号]
    else:
        signal.signal(信号编号, signal.SIG_DFL)


def 忽略信号(信号编号: int):
    """
    忽略指定信号

    参数:
        信号编号: 信号编号
    """
    try:
        signal.signal(信号编号, signal.SIG_IGN)
    except ValueError:
        raise RuntimeError(f"无法忽略信号 {信号编号}")


def 发送信号(进程PID: int, 信号编号: int):
    """
    向进程发送信号

    参数:
        进程PID: 目标进程 PID
        信号编号: 信号编号
    """
    import os
    try:
        os.kill(进程PID, 信号编号)
    except ProcessLookupError:
        raise RuntimeError(f"进程 {进程PID} 不存在")
    except PermissionError:
        raise RuntimeError(f"无权限向进程 {进程PID} 发送信号")
    except Exception as e:
        raise RuntimeError(f"发送信号失败: {e}")


def 信号名称(信号编号: int) -> str:
    """
    获取信号编号对应的名称

    参数:
        信号编号: 信号编号

    返回:
        信号名称字符串
    """
    信号映射 = {
        signal.SIGABRT: 'SIGABRT',
        signal.SIGFPE: 'SIGFPE',
        signal.SIGILL: 'SIGILL',
        signal.SIGINT: 'SIGINT',
        signal.SIGSEGV: 'SIGSEGV',
        signal.SIGTERM: 'SIGTERM',
    }
    if hasattr(signal, 'SIGKILL'):
        信号映射[signal.SIGKILL] = 'SIGKILL'
    if hasattr(signal, 'SIGUSR1'):
        信号映射[signal.SIGUSR1] = 'SIGUSR1'
    if hasattr(signal, 'SIGUSR2'):
        信号映射[signal.SIGUSR2] = 'SIGUSR2'
    if hasattr(signal, 'SIGPIPE'):
        信号映射[signal.SIGPIPE] = 'SIGPIPE'
    if hasattr(signal, 'SIGALRM'):
        信号映射[signal.SIGALRM] = 'SIGALRM'
    if hasattr(signal, 'SIGCHLD'):
        信号映射[signal.SIGCHLD] = 'SIGCHLD'
    if hasattr(signal, 'SIGHUP'):
        信号映射[signal.SIGHUP] = 'SIGHUP'
    if hasattr(signal, 'SIGQUIT'):
        信号映射[signal.SIGQUIT] = 'SIGQUIT'
    if hasattr(signal, 'SIGSTOP'):
        信号映射[signal.SIGSTOP] = 'SIGSTOP'
    if hasattr(signal, 'SIGTSTP'):
        信号映射[signal.SIGTSTP] = 'SIGTSTP'
    if hasattr(signal, 'SIGCONT'):
        信号映射[signal.SIGCONT] = 'SIGCONT'

    return 信号映射.get(信号编号, f'信号({信号编号})')


def 信号编号(名称: str) -> Optional[int]:
    """
    获取信号名称对应的编号

    参数:
        名称: 信号名称（如 'SIGINT'）

    返回:
        信号编号，未知返回 None
    """
    名称 = 名称.upper()
    if not 名称.startswith('SIG'):
        名称 = 'SIG' + 名称

    return getattr(signal, 名称, None)


def 可用信号() -> Dict[str, int]:
    """
    获取当前平台所有可用信号

    返回:
        信号名到编号的映射字典
    """
    信号列表 = ['SIGABRT', 'SIGFPE', 'SIGILL', 'SIGINT', 'SIGSEGV', 'SIGTERM']
    扩展信号 = ['SIGKILL', 'SIGUSR1', 'SIGUSR2', 'SIGPIPE', 'SIGALRM',
                   'SIGCHLD', 'SIGHUP', 'SIGQUIT', 'SIGSTOP', 'SIGTSTP',
                   'SIGCONT', 'SIGBREAK', 'SIGWINCH']
    结果 = {}
    for 名称 in 信号列表 + 扩展信号:
        num = getattr(signal, 名称, None)
        if num is not None:
            结果[名称] = num
    return 结果


def 设置超时信号(秒: int, 处理器: Callable = None):
    """
    设置超时信号（仅 Unix）

    参数:
        秒: 超时秒数
        处理器: 超时处理函数，默认引发 TimeoutError
    """
    if not hasattr(signal, 'SIGALRM'):
        raise RuntimeError("SIGALRM 在当前平台不可用")

    if 处理器 is None:
        def 超时处理器(signum, frame):
            raise TimeoutError("操作超时")
        处理器 = 超时处理器

    signal.signal(signal.SIGALRM, 处理器)
    signal.alarm(秒)


def 取消超时信号():
    """取消超时信号（仅 Unix）"""
    if hasattr(signal, 'alarm'):
        signal.alarm(0)


__all__ = [
    '注册信号处理器', '恢复信号处理器', '忽略信号',
    '发送信号', '信号名称', '信号编号', '可用信号',
    '设置超时信号', '取消超时信号',
]