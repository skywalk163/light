# -*- coding: utf-8 -*-
"""
光明标准库 - 环境变量和系统信息模块

提供环境变量读写、系统信息获取等功能。
"""

import os
import sys
import platform
from typing import Optional, Dict, List


def 获取环境变量(名称: str, 默认值: str = None) -> Optional[str]:
    """
    获取环境变量值

    参数:
        名称: 环境变量名
        默认值: 不存在时的默认值

    返回:
        环境变量值或默认值
    """
    return os.environ.get(名称, 默认值)


def 设置环境变量(名称: str, 值: str):
    """设置环境变量"""
    os.environ[名称] = 值


def 删除环境变量(名称: str):
    """删除环境变量"""
    if 名称 in os.environ:
        del os.environ[名称]


def 环境变量存在(名称: str) -> bool:
    """检查环境变量是否存在"""
    return 名称 in os.environ


def 获取所有环境变量() -> Dict[str, str]:
    """获取所有环境变量"""
    return dict(os.environ)


def 系统名称() -> str:
    """获取操作系统名称（如 'Windows', 'Linux', 'Darwin'）"""
    return platform.system()


def 系统版本() -> str:
    """获取操作系统版本"""
    return platform.version()


def 系统架构() -> str:
    """获取系统架构（如 'AMD64', 'x86_64', 'arm64'）"""
    return platform.machine()


def 系统信息() -> Dict[str, str]:
    """获取系统信息字典"""
    return {
        '系统': platform.system(),
        '节点': platform.node(),
        '版本': platform.version(),
        '架构': platform.machine(),
        '处理器': platform.processor(),
        'Python版本': platform.python_version(),
        'Python实现': platform.python_implementation(),
    }


def Python版本() -> str:
    """获取 Python 版本字符串"""
    return platform.python_version()


def Python版本号() -> tuple:
    """获取 Python 版本号元组"""
    return sys.version_info[:3]


def 主机名() -> str:
    """获取主机名"""
    return platform.node()


def CPU核心数() -> int:
    """获取 CPU 核心数"""
    return os.cpu_count() or 1


def 内存信息() -> Dict[str, int]:
    """
    获取内存信息（仅 Unix 支持详细数据）

    返回:
        内存信息字典
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            '总计': mem.total,
            '可用': mem.available,
            '已用': mem.used,
            '百分比': mem.percent,
        }
    except ImportError:
        # 无 psutil 时返回基本信息
        return {
            '总计': 0,
            '可用': 0,
            '已用': 0,
            '百分比': 0,
        }


def 磁盘信息(路径: str = '.') -> Dict[str, int]:
    """
    获取磁盘信息

    参数:
        路径: 磁盘路径（默认当前目录）

    返回:
        磁盘信息字典
    """
    try:
        usage = os.disk_usage(路径)
        return {
            '总计': usage.total,
            '已用': usage.used,
            '可用': usage.free,
            '百分比': usage.used / usage.total * 100 if usage.total else 0,
        }
    except AttributeError:
        # Python 3.11+ 支持 os.disk_usage
        try:
            import shutil
            total, used, free = shutil.disk_usage(路径)
            return {'总计': total, '已用': used, '可用': free, '百分比': used / total * 100 if total else 0}
        except Exception:
            return {'总计': 0, '已用': 0, '可用': 0, '百分比': 0}


def 用户名() -> str:
    """获取当前用户名"""
    try:
        return os.environ.get('USERNAME') or os.environ.get('USER') or ''
    except Exception:
        return ''


def 用户目录() -> str:
    """获取当前用户目录"""
    return os.path.expanduser('~')


def 临时目录() -> str:
    """获取系统临时目录"""
    temp = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    return temp


def PATH列表() -> List[str]:
    """获取 PATH 环境变量中的目录列表"""
    return os.environ.get('PATH', '').split(os.pathsep)


def 操作系统类型() -> str:
    """
    获取操作系统类型

    返回:
        'windows', 'linux', 'macos', 或其他
    """
    system = platform.system().lower()
    if 'windows' in system:
        return 'windows'
    elif 'linux' in system:
        return 'linux'
    elif 'darwin' in system:
        return 'macos'
    return system


def 是Windows() -> bool:
    """检查是否为 Windows 系统"""
    return os.name == 'nt' or platform.system().lower() == 'windows'


def 是Linux() -> bool:
    """检查是否为 Linux 系统"""
    return platform.system().lower() == 'linux'


def 是macOS() -> bool:
    """检查是否为 macOS 系统"""
    return platform.system().lower() == 'darwin'


__all__ = [
    '获取环境变量', '设置环境变量', '删除环境变量',
    '环境变量存在', '获取所有环境变量',
    '系统名称', '系统版本', '系统架构', '系统信息',
    'Python版本', 'Python版本号',
    '主机名', 'CPU核心数', '内存信息', '磁盘信息',
    '用户名', '用户目录', '临时目录', 'PATH列表',
    '操作系统类型', '是Windows', '是Linux', '是macOS',
]