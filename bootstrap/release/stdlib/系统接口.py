"""
段言标准库 - 系统接口模块

封装 sys 和 os 模块的常用功能，提供统一的系统接口。
包括：环境变量、路径操作、进程信息、平台信息等。
"""

import sys
import os
import platform
from typing import List, Dict, Optional, Any


# ========== 环境变量 ==========

def 获取环境变量(名称: str, 默认值: str = None) -> Optional[str]:
    """
    获取环境变量
    
    参数:
        名称: 环境变量名
        默认值: 不存在时的默认值
    
    返回:
        环境变量值
    """
    return os.environ.get(名称, 默认值)


def 设置环境变量(名称: str, 值: str) -> None:
    """设置环境变量"""
    os.environ[名称] = 值


def 删除环境变量(名称: str) -> None:
    """删除环境变量"""
    if 名称 in os.environ:
        del os.environ[名称]


def 环境变量存在(名称: str) -> bool:
    """检查环境变量是否存在"""
    return 名称 in os.environ


def 获取所有环境变量() -> Dict[str, str]:
    """获取所有环境变量字典"""
    return dict(os.environ)


# ========== 路径操作 ==========

def 当前工作目录() -> str:
    """获取当前工作目录"""
    return os.getcwd()


def 切换工作目录(路径: str) -> None:
    """切换工作目录"""
    os.chdir(路径)


def 路径存在(路径: str) -> bool:
    """检查路径是否存在"""
    return os.path.exists(路径)


def 是文件(路径: str) -> bool:
    """检查是否为文件"""
    return os.path.isfile(路径)


def 是目录(路径: str) -> bool:
    """检查是否为目录"""
    return os.path.isdir(路径)


def 是绝对路径(路径: str) -> bool:
    """检查是否为绝对路径"""
    return os.path.isabs(路径)


def 绝对路径(路径: str) -> str:
    """获取绝对路径"""
    return os.path.abspath(路径)


def 规范化路径(路径: str) -> str:
    """规范化路径"""
    return os.path.normpath(路径)


def 连接路径(*路径片段) -> str:
    """连接多个路径片段"""
    return os.path.join(*路径片段)


def 取目录名(路径: str) -> str:
    """获取路径中的目录部分"""
    return os.path.dirname(路径)


def 取文件名(路径: str) -> str:
    """获取路径中的文件名部分"""
    return os.path.basename(路径)


def 取文件扩展名(路径: str) -> str:
    """获取文件扩展名（包含点号）"""
    return os.path.splitext(路径)[1]


def 取文件名无扩展(路径: str) -> str:
    """获取不含扩展名的文件名"""
    return os.path.splitext(取文件名(路径))[0]


def 分割路径(路径: str) -> tuple:
    """分割路径为目录和文件名"""
    return os.path.split(路径)


def 分割扩展名(路径: str) -> tuple:
    """分割扩展名"""
    return os.path.splitext(路径)


def 文件大小(路径: str) -> int:
    """获取文件大小（字节）"""
    return os.path.getsize(路径)


def 文件修改时间(路径: str) -> float:
    """获取文件修改时间戳"""
    return os.path.getmtime(路径)


def 文件创建时间(路径: str) -> float:
    """获取文件创建时间戳"""
    return os.path.getctime(路径)


def 文件访问时间(路径: str) -> float:
    """获取文件访问时间戳"""
    return os.path.getatime(路径)


# ========== 目录操作 ==========

def 创建目录(路径: str, 递归: bool = True) -> None:
    """
    创建目录
    
    参数:
        路径: 目录路径
        递归: 是否递归创建父目录
    """
    if 递归:
        os.makedirs(路径, exist_ok=True)
    else:
        os.mkdir(路径)


def 删除目录(路径: str, 递归: bool = False) -> None:
    """
    删除目录
    
    参数:
        路径: 目录路径
        递归: 是否递归删除
    """
    if 递归:
        import shutil
        shutil.rmtree(路径)
    else:
        os.rmdir(路径)


def 列出目录(路径: str = ".") -> List[str]:
    """列出目录内容"""
    return os.listdir(路径)


def 遍历目录(路径: str) -> List[tuple]:
    """
    递归遍历目录
    
    返回:
        [(目录路径, 子目录列表, 文件列表), ...]
    """
    return list(os.walk(路径))


def 重命名(旧路径: str, 新路径: str) -> None:
    """重命名文件或目录"""
    os.rename(旧路径, 新路径)


def 删除文件(路径: str) -> None:
    """删除文件"""
    os.remove(路径)


def 复制文件(源路径: str, 目标路径: str) -> None:
    """复制文件"""
    import shutil
    shutil.copy2(源路径, 目标路径)


# ========== 进程信息 ==========

def 进程ID() -> int:
    """获取当前进程ID"""
    return os.getpid()


def 父进程ID() -> int:
    """获取父进程ID"""
    return os.getppid()


def 退出(退出码: int = 0) -> None:
    """退出程序"""
    sys.exit(退出码)


def 获取命令行参数() -> List[str]:
    """获取命令行参数列表"""
    return list(sys.argv)


def 获取脚本路径() -> str:
    """获取当前脚本路径"""
    return sys.argv[0]


def 标准输入() -> Any:
    """获取标准输入"""
    return sys.stdin


def 标准输出() -> Any:
    """获取标准输出"""
    return sys.stdout


def 标准错误() -> Any:
    """获取标准错误"""
    return sys.stderr


# ========== 平台信息 ==========

def 操作系统() -> str:
    """获取操作系统名称"""
    return platform.system()


def 操作系统版本() -> str:
    """获取操作系统版本"""
    return platform.version()


def 操作系统详细信息() -> str:
    """获取操作系统详细信息"""
    return platform.platform()


def 计算机名() -> str:
    """获取计算机名"""
    return platform.node()


def 处理器架构() -> str:
    """获取处理器架构"""
    return platform.machine()


def 处理器型号() -> str:
    """获取处理器型号"""
    return platform.processor()


def Python版本() -> str:
    """获取Python版本"""
    return platform.python_version()


def Python实现() -> str:
    """获取Python实现（CPython, PyPy等）"""
    return platform.python_implementation()


def Python编译器() -> str:
    """获取Python编译器"""
    return platform.python_compiler()


def 是否Windows() -> bool:
    """是否为Windows系统"""
    return os.name == 'nt'


def 是否Linux() -> bool:
    """是否为Linux系统"""
    return sys.platform.startswith('linux')


def 是否Mac() -> bool:
    """是否为macOS系统"""
    return sys.platform == 'darwin'


# ========== 用户信息 ==========

def 用户名() -> str:
    """获取当前用户名"""
    return os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))


def 用户主目录() -> str:
    """获取用户主目录"""
    return os.path.expanduser("~")


def 临时目录() -> str:
    """获取系统临时目录"""
    import tempfile
    return tempfile.gettempdir()


# ========== 系统命令 ==========

def 执行系统命令(命令: str) -> int:
    """
    执行系统命令（直接输出到控制台）
    
    参数:
        命令: 命令字符串
    
    返回:
        退出码
    """
    return os.system(命令)


def 路径分隔符() -> str:
    """获取路径分隔符（Windows为\\，Linux为/）"""
    return os.sep


def 环境变量分隔符() -> str:
    """获取环境变量分隔符（Windows为;，Linux为:）"""
    return os.pathsep


def 行分隔符() -> str:
    """获取行分隔符"""
    return os.linesep


def CPU核心数() -> int:
    """获取CPU核心数"""
    return os.cpu_count() or 1


# ========== 内存信息 ==========

def 内存使用情况() -> Dict[str, int]:
    """
    获取内存使用情况
    
    返回:
        {'rss': 常驻内存, 'vms': 虚拟内存} 字节
    """
    try:
        import psutil
        进程 = psutil.Process()
        内存信息 = 进程.memory_info()
        return {
            'rss': 内存信息.rss,
            'vms': 内存信息.vms,
        }
    except ImportError:
        return {'rss': 0, 'vms': 0}


__all__ = [
    # 环境变量
    '获取环境变量', '设置环境变量', '删除环境变量', '环境变量存在', '获取所有环境变量',
    # 路径操作
    '当前工作目录', '切换工作目录', '路径存在', '是文件', '是目录', '是绝对路径',
    '绝对路径', '规范化路径', '连接路径', '取目录名', '取文件名', '取文件扩展名',
    '取文件名无扩展', '分割路径', '分割扩展名', '文件大小', '文件修改时间',
    '文件创建时间', '文件访问时间',
    # 目录操作
    '创建目录', '删除目录', '列出目录', '遍历目录', '重命名', '删除文件', '复制文件',
    # 进程信息
    '进程ID', '父进程ID', '退出', '获取命令行参数', '获取脚本路径',
    '标准输入', '标准输出', '标准错误',
    # 平台信息
    '操作系统', '操作系统版本', '操作系统详细信息', '计算机名', '处理器架构',
    '处理器型号', 'Python版本', 'Python实现', 'Python编译器',
    '是否Windows', '是否Linux', '是否Mac',
    # 用户信息
    '用户名', '用户主目录', '临时目录',
    # 系统命令
    '执行系统命令',
    # 系统常量
    '路径分隔符', '环境变量分隔符', '行分隔符', 'CPU核心数',
    # 内存
    '内存使用情况',
    # 合并自系统信息
    '内存总量', '内存可用', '线程数',
]


# =============================================================================
# 合并自系统信息.py的独有函数
# =============================================================================

def 内存总量() -> int:
    """获取系统内存总量（字节）"""
    import psutil
    return psutil.virtual_memory().total


def 内存可用() -> int:
    """获取系统可用内存（字节）"""
    import psutil
    return psutil.virtual_memory().available


def 线程数() -> int:
    """获取当前进程的线程数"""
    import threading
    return threading.active_count()
