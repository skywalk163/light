"""
光明标准库 - 临时文件模块

封装 tempfile 模块，提供临时文件和临时目录的创建与管理功能。
支持上下文管理器自动清理，支持命名临时文件、临时目录等。
"""

import tempfile
import os
from typing import Optional, Tuple, IO, Any


def 创建临时文件(后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 文本模式: bool = True) -> Tuple[int, str]:
    """
    创建临时文件，返回(文件描述符, 文件路径)
    
    参数:
        后缀: 文件名后缀
        前缀: 文件名前缀
        目录: 临时文件所在目录
        文本模式: 是否文本模式
    
    返回:
        (文件描述符, 文件路径)
    """
    return tempfile.mkstemp(suffix=后缀, prefix=前缀, dir=目录, text=文本模式)


def 创建临时文件路径(后缀: str = '', 前缀: str = 'tmp', 目录: str = None) -> str:
    """
    创建临时文件并返回路径（文件已关闭）
    
    参数:
        后缀: 文件名后缀
        前缀: 文件名前缀
        目录: 临时文件所在目录
    
    返回:
        临时文件路径
    """
    fd, path = tempfile.mkstemp(suffix=后缀, prefix=前缀, dir=目录)
    os.close(fd)
    return path


def 创建临时目录(后缀: str = '', 前缀: str = 'tmp', 目录: str = None) -> str:
    """
    创建临时目录
    
    参数:
        后缀: 目录名后缀
        前缀: 目录名前缀
        目录: 上级目录
    
    返回:
        临时目录路径
    """
    return tempfile.mkdtemp(suffix=后缀, prefix=前缀, dir=目录)


def 获取临时目录() -> str:
    """获取系统默认临时目录路径"""
    return tempfile.gettempdir()


def 获取临时目录前缀() -> str:
    """获取临时文件名的默认前缀"""
    return tempfile.gettempprefix()


class 命名临时文件:
    """
    命名临时文件（支持上下文管理器）
    
    用法:
        with 命名临时文件(后缀='.txt') as f:
            f.write('内容')
            文件路径 = f.名称
    """
    
    def __init__(self, 模式: str = 'w+b', 后缀: str = '', 前缀: str = 'tmp',
                 目录: str = None, 删除: bool = True, 编码: str = None):
        """
        初始化命名临时文件
        
        参数:
            模式: 文件打开模式
            后缀: 文件名后缀
            前缀: 文件名前缀
            目录: 所在目录
            删除: 关闭时是否自动删除
            编码: 文本编码
        """
        self._文件 = tempfile.NamedTemporaryFile(
            mode=模式,
            suffix=后缀,
            prefix=前缀,
            dir=目录,
            delete=删除,
            encoding=编码,
            delete_on_close=删除,
        )
    
    def __enter__(self) -> IO:
        self._文件.__enter__()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        return self._文件.__exit__(异常类型, 异常值, 追溯)
    
    @property
    def 名称(self) -> str:
        """获取文件路径"""
        return self._文件.name
    
    @property
    def 文件对象(self) -> IO:
        """获取底层文件对象"""
        return self._文件
    
    def 读取(self, 大小: int = -1) -> Any:
        """读取文件内容"""
        return self._文件.read(大小)
    
    def 写入(self, 数据: Any) -> int:
        """写入数据"""
        return self._文件.write(数据)
    
    def 关闭(self) -> None:
        """关闭文件"""
        self._文件.close()
    
    def 刷新(self) -> None:
        """刷新缓冲区"""
        self._文件.flush()
    
    def 定位(self, 偏移: int, 起始位置: int = 0) -> int:
        """移动文件指针"""
        return self._文件.seek(偏移, 起始位置)
    
    def 位置(self) -> int:
        """获取当前指针位置"""
        return self._文件.tell()


class 临时文件上下文:
    """
    临时文件上下文管理器（仅创建文件路径，不自动打开）
    
    用法:
        with 临时文件上下文(后缀='.txt') as 路径:
            写入文件(路径, '内容')
        # 退出上下文时自动删除
    """
    
    def __init__(self, 后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 删除: bool = True):
        self._后缀 = 后缀
        self._前缀 = 前缀
        self._目录 = 目录
        self._删除 = 删除
        self._路径 = None
    
    def __enter__(self) -> str:
        fd, self._路径 = tempfile.mkstemp(suffix=self._后缀, prefix=self._前缀, dir=self._目录)
        os.close(fd)
        return self._路径
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._路径 and self._删除 and os.path.exists(self._路径):
            try:
                os.remove(self._路径)
            except:
                pass
        return False
    
    @property
    def 路径(self) -> Optional[str]:
        return self._路径


class 临时目录上下文:
    """
    临时目录上下文管理器
    
    用法:
        with 临时目录上下文() as 目录:
            写入文件(目录 + '/a.txt', '内容')
        # 退出上下文时自动删除目录
    """
    
    def __init__(self, 后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 删除: bool = True):
        self._后缀 = 后缀
        self._前缀 = 前缀
        self._目录 = 目录
        self._删除 = 删除
        self._路径 = None
    
    def __enter__(self) -> str:
        self._路径 = tempfile.mkdtemp(suffix=self._后缀, prefix=self._前缀, dir=self._目录)
        return self._路径
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._路径 and self._删除 and os.path.exists(self._路径):
            try:
                import shutil
                shutil.rmtree(self._路径)
            except:
                pass
        return False
    
    @property
    def 路径(self) -> Optional[str]:
        return self._路径


def 临时文件(后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 删除: bool = True) -> 临时文件上下文:
    """创建临时文件上下文管理器（便捷函数）"""
    return 临时文件上下文(后缀=后缀, 前缀=前缀, 目录=目录, 删除=删除)


def 临时目录(后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 删除: bool = True) -> 临时目录上下文:
    """创建临时目录上下文管理器（便捷函数）"""
    return 临时目录上下文(后缀=后缀, 前缀=前缀, 目录=目录, 删除=删除)


def 安全文件名(名称: str) -> str:
    """
    获取安全的文件名（去除路径分隔符等危险字符）
    
    参数:
        名称: 原始文件名
    
    返回:
        安全的文件名
    """
    return os.path.basename(名称).replace('/', '_').replace('\\', '_')


class Spooled临时文件:
    """
    内存缓冲临时文件（小文件在内存，大文件自动落盘）
    
    用法:
        f = Spooled临时文件(最大大小=1024*1024)
        f.写入('数据')
    """
    
    def __init__(self, 最大大小: int = 1024 * 1024, 模式: str = 'w+b',
                 后缀: str = '', 前缀: str = 'tmp', 目录: str = None, 编码: str = None):
        self._文件 = tempfile.SpooledTemporaryFile(
            max_size=最大大小,
            mode=模式,
            suffix=后缀,
            prefix=前缀,
            dir=目录,
            encoding=编码,
        )
    
    def 读取(self, 大小: int = -1) -> Any:
        return self._文件.read(大小)
    
    def 写入(self, 数据: Any) -> int:
        return self._文件.write(数据)
    
    def 关闭(self) -> None:
        self._文件.close()
    
    def 刷新(self) -> None:
        self._文件.flush()
    
    def 定位(self, 偏移: int, 起始位置: int = 0) -> int:
        return self._文件.seek(偏移, 起始位置)
    
    def 位置(self) -> int:
        return self._文件.tell()
    
    def 滚动到磁盘(self) -> None:
        """强制将内存中的数据写入磁盘文件"""
        self._文件.rollover()
    
    @property
    def 是否已滚动(self) -> bool:
        """是否已滚动到磁盘"""
        return self._文件._rolled


__all__ = [
    '创建临时文件', '创建临时文件路径', '创建临时目录',
    '获取临时目录', '获取临时目录前缀',
    '命名临时文件', '临时文件上下文', '临时目录上下文',
    '临时文件', '临时目录',
    '安全文件名', 'Spooled临时文件',
]
