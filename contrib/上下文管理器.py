"""
光明标准库 - 上下文管理器模块

提供上下文管理器功能，包括：
- 临时文件/目录管理
- 资源管理（文件、连接等）
- 上下文工具（计时器、锁、事务等）
"""

import os
import tempfile
import shutil
import time
import threading
from typing import Optional, Any, Callable


class 临时文件:
    """临时文件上下文管理器"""
    
    def __init__(self, 前缀: str = '', 后缀: str = '', 目录: str = None, 删除: bool = True):
        self._前缀 = 前缀
        self._后缀 = 后缀
        self._目录 = 目录
        self._删除 = 删除
        self._文件路径 = None
    
    def __enter__(self) -> str:
        fd, self._文件路径 = tempfile.mkstemp(prefix=self._前缀, suffix=self._后缀, dir=self._目录)
        os.close(fd)
        return self._文件路径
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._文件路径 and self._删除 and os.path.exists(self._文件路径):
            try:
                os.remove(self._文件路径)
            except:
                pass
        return False
    
    @property
    def 文件路径(self) -> str:
        return self._文件路径


class 临时目录:
    """临时目录上下文管理器"""
    
    def __init__(self, 前缀: str = '', 后缀: str = '', 目录: str = None, 删除: bool = True):
        self._前缀 = 前缀
        self._后缀 = 后缀
        self._目录 = 目录
        self._删除 = 删除
        self._目录路径 = None
    
    def __enter__(self) -> str:
        self._目录路径 = tempfile.mkdtemp(prefix=self._前缀, suffix=self._后缀, dir=self._目录)
        return self._目录路径
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._目录路径 and self._删除 and os.path.exists(self._目录路径):
            try:
                shutil.rmtree(self._目录路径)
            except:
                pass
        return False
    
    @property
    def 目录路径(self) -> str:
        return self._目录路径


class 自动关闭:
    """自动关闭资源上下文管理器"""
    
    def __init__(self, 资源, 关闭方法: str = 'close', *关闭参数, **关闭关键字参数):
        self._资源 = 资源
        self._关闭方法 = 关闭方法
        self._关闭参数 = 关闭参数
        self._关闭关键字参数 = 关闭关键字参数
    
    def __enter__(self):
        return self._资源
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        try:
            if hasattr(self._资源, self._关闭方法):
                getattr(self._资源, self._关闭方法)(*self._关闭参数, **self._关闭关键字参数)
        except:
            pass
        return False


class 计时器上下文:
    """计时器上下文管理器"""
    
    def __init__(self, 日志函数: Callable = print, 名称: str = None):
        self._日志函数 = 日志函数
        self._名称 = 名称
        self._开始时间 = None
        self._耗时 = None
    
    def __enter__(self):
        self._开始时间 = time.perf_counter()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self._耗时 = time.perf_counter() - self._开始时间
        if self._日志函数:
            名称 = self._名称 or '操作'
            self._日志函数(f'{名称} 耗时: {self._耗时:.6f}秒')
        return False
    
    @property
    def 耗时(self) -> float:
        return self._耗时


class 锁上下文:
    """锁上下文管理器"""
    
    def __init__(self, 锁=None, 超时: float = None):
        if 锁 is None:
            self._锁 = threading.Lock()
        else:
            self._锁 = 锁
        self._超时 = 超时
        self._获取成功 = False
    
    def __enter__(self):
        if self._超时 is None:
            self._锁.acquire()
            self._获取成功 = True
        else:
            self._获取成功 = self._锁.acquire(timeout=self._超时)
        return self._获取成功
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._获取成功:
            self._锁.release()
        return False
    
    @property
    def 获取成功(self) -> bool:
        return self._获取成功


class 事务:
    """简单事务上下文管理器"""
    
    def __init__(self, 提交函数: Callable, 回滚函数: Callable = None):
        self._提交函数 = 提交函数
        self._回滚函数 = 回滚函数
        self._已提交 = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if 异常类型 is None and not 异常值:
            self._提交函数()
            self._已提交 = True
        else:
            if self._回滚函数:
                self._回滚函数()
        return False
    
    @property
    def 已提交(self) -> bool:
        return self._已提交


class 变更恢复:
    """变更恢复上下文管理器"""
    
    def __init__(self, 对象, 属性名: str, 新值: Any):
        self._对象 = 对象
        self._属性名 = 属性名
        self._新值 = 新值
        self._旧值 = None
    
    def __enter__(self):
        self._旧值 = getattr(self._对象, self._属性名, None)
        setattr(self._对象, self._属性名, self._新值)
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        setattr(self._对象, self._属性名, self._旧值)
        return False


class 环境变量上下文:
    """环境变量上下文管理器"""
    
    def __init__(self, **变量):
        self._变量 = 变量
        self._旧值 = {}
    
    def __enter__(self):
        for 名称, 值 in self._变量.items():
            self._旧值[名称] = os.environ.get(名称)
            os.environ[名称] = 值
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        for 名称, 旧值 in self._旧值.items():
            if 旧值 is None:
                if 名称 in os.environ:
                    del os.environ[名称]
            else:
                os.environ[名称] = 旧值
        return False


class 工作目录:
    """工作目录上下文管理器"""
    
    def __init__(self, 目录: str):
        self._目录 = 目录
        self._旧目录 = None
    
    def __enter__(self):
        self._旧目录 = os.getcwd()
        os.chdir(self._目录)
        return self._目录
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if self._旧目录:
            os.chdir(self._旧目录)
        return False


class 静默异常:
    """静默异常上下文管理器"""
    
    def __init__(self, 捕获异常: tuple = (Exception,), 日志函数: Callable = None):
        self._捕获异常 = 捕获异常
        self._日志函数 = 日志函数
    
    def __enter__(self):
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if 异常类型 is not None and issubclass(异常类型, self._捕获异常):
            if self._日志函数:
                self._日志函数(f'静默异常: {异常值}')
            return True
        return False


class 重试上下文:
    """重试上下文管理器"""
    
    def __init__(self, 最大次数: int = 3, 间隔秒数: float = 1.0, 退避因子: float = 2.0):
        self._最大次数 = 最大次数
        self._间隔秒数 = 间隔秒数
        self._退避因子 = 退避因子
    
    def __enter__(self):
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        if 异常类型 is None:
            return False
        
        当前间隔 = self._间隔秒数
        for 次数 in range(self._最大次数 - 1):
            time.sleep(当前间隔)
            当前间隔 *= self._退避因子
            return False
        
        return False


class 信号处理器:
    """信号处理器上下文管理器"""
    
    def __init__(self, 信号, 处理函数: Callable):
        import signal as _signal
        self._信号 = 信号
        self._处理函数 = 处理函数
        self._旧处理函数 = None
    
    def __enter__(self):
        import signal as _signal
        self._旧处理函数 = _signal.signal(self._信号, self._处理函数)
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        import signal as _signal
        if self._旧处理函数 is not None:
            _signal.signal(self._信号, self._旧处理函数)
        return False


def 创建临时文件(前缀: str = '', 后缀: str = '', 目录: str = None) -> str:
    """创建临时文件并返回路径"""
    fd, 路径 = tempfile.mkstemp(prefix=前缀, suffix=后缀, dir=目录)
    os.close(fd)
    return 路径


def 创建临时目录(前缀: str = '', 后缀: str = '', 目录: str = None) -> str:
    """创建临时目录并返回路径"""
    return tempfile.mkdtemp(prefix=前缀, suffix=后缀, dir=目录)


def 删除临时文件(路径: str):
    """删除临时文件"""
    if os.path.exists(路径):
        try:
            os.remove(路径)
        except:
            pass


def 删除临时目录(路径: str):
    """删除临时目录"""
    if os.path.exists(路径):
        try:
            shutil.rmtree(路径)
        except:
            pass


__all__ = [
    '临时文件', '临时目录',
    '自动关闭',
    '计时器上下文', '锁上下文',
    '事务', '变更恢复',
    '环境变量上下文', '工作目录',
    '静默异常', '重试上下文', '信号处理器',
    '创建临时文件', '创建临时目录', '删除临时文件', '删除临时目录'
]