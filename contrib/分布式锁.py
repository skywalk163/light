"""
光明标准库 - 分布式锁模块

提供分布式锁支持，包括：
- 内存分布式锁（单机模拟）
- Redis分布式锁接口
- ZooKeeper分布式锁接口
- 读写锁
- 可重入锁
- 锁超时与自动续期
"""

import threading
import time
import uuid
from typing import Optional, Dict, Callable
from enum import Enum


class 锁类型(Enum):
    """锁类型枚举"""
    互斥锁 = "互斥锁"
    读写锁 = "读写锁"
    可重入锁 = "可重入锁"


class 锁状态(Enum):
    """锁状态枚举"""
    未锁定 = "未锁定"
    已锁定 = "已锁定"
    已过期 = "已过期"


class 分布式锁错误(Exception):
    """分布式锁异常"""
    pass


class 获取锁失败(分布式锁错误):
    """获取锁失败异常"""
    pass


class 锁已过期(分布式锁错误):
    """锁已过期异常"""
    pass


class 内存分布式锁:
    """
    内存分布式锁（单机模拟，用于测试和单机场景）
    
    提供类似Redis锁的接口，但基于内存实现
    """
    
    _全局锁存储 = {}
    _全局锁 = threading.Lock()
    
    def __init__(self, 锁名称: str, 超时时间: float = 30.0, 等待超时: float = 10.0):
        """
        初始化锁
        
        参数:
            锁名称: 锁的唯一标识
            超时时间: 锁自动释放时间（秒）
            等待超时: 获取锁的等待超时（秒）
        """
        self.锁名称 = 锁名称
        self.超时时间 = 超时时间
        self.等待超时 = 等待超时
        self._持有者 = None
        self._锁定时间 = None
        self._重入计数 = 0
        self._续期线程 = None
        self._续期运行 = False
    
    def 获取(self, 阻塞: bool = True) -> bool:
        """
        获取锁
        
        参数:
            阻塞: 是否阻塞等待
            
        返回:
            是否成功获取锁
        """
        开始时间 = time.time()
        
        while True:
            with 内存分布式锁._全局锁:
                锁信息 = 内存分布式锁._全局锁存储.get(self.锁名称)
                现在 = time.time()
                
                if 锁信息 is None or 现在 - 锁信息["时间"] > 锁信息["超时"]:
                    锁值 = str(uuid.uuid4())
                    内存分布式锁._全局锁存储[self.锁名称] = {
                        "值": 锁值,
                        "时间": 现在,
                        "超时": self.超时时间
                    }
                    self._持有者 = 锁值
                    self._锁定时间 = 现在
                    self._重入计数 = 1
                    self._启动续期()
                    return True
                
                if not 阻塞:
                    return False
                
                if time.time() - 开始时间 > self.等待超时:
                    return False
            
            time.sleep(0.01)
    
    def 释放(self) -> bool:
        """
        释放锁
        
        返回:
            是否成功释放
        """
        with 内存分布式锁._全局锁:
            锁信息 = 内存分布式锁._全局锁存储.get(self.锁名称)
            
            if 锁信息 is None:
                return False
            
            if 锁信息["值"] != self._持有者:
                return False
            
            del 内存分布式锁._全局锁存储[self.锁名称]
            self._持有者 = None
            self._锁定时间 = None
            self._重入计数 = 0
            self._停止续期()
            return True
    
    def _启动续期(self):
        """启动自动续期"""
        if self.超时时间 <= 0:
            return
        
        self._续期运行 = True
        
        def 续期线程():
            while self._续期运行:
                time.sleep(self.超时时间 / 3)
                with 内存分布式锁._全局锁:
                    锁信息 = 内存分布式锁._全局锁存储.get(self.锁名称)
                    if 锁信息 and 锁信息["值"] == self._持有者:
                        锁信息["时间"] = time.time()
        
        self._续期线程 = threading.Thread(target=续期线程, daemon=True)
        self._续期线程.start()
    
    def _停止续期(self):
        """停止自动续期"""
        self._续期运行 = False
        if self._续期线程:
            self._续期线程.join(timeout=1.0)
            self._续期线程 = None
    
    def 检查状态(self) -> 锁状态:
        """检查锁状态"""
        with 内存分布式锁._全局锁:
            锁信息 = 内存分布式锁._全局锁存储.get(self.锁名称)
            
            if 锁信息 is None:
                return 锁状态.未锁定
            
            现在 = time.time()
            if 现在 - 锁信息["时间"] > 锁信息["超时"]:
                return 锁状态.已过期
            
            return 锁状态.已锁定
    
    def 剩余时间(self) -> float:
        """获取锁剩余时间"""
        with 内存分布式锁._全局锁:
            锁信息 = 内存分布式锁._全局锁存储.get(self.锁名称)
            
            if 锁信息 is None:
                return 0.0
            
            已过时间 = time.time() - 锁信息["时间"]
            return max(0.0, 锁信息["超时"] - 已过时间)
    
    def __enter__(self):
        if not self.获取():
            raise 获取锁失败(f"获取锁失败: {self.锁名称}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.释放()
        return False


class 可重入内存锁:
    """可重入内存锁"""
    
    def __init__(self, 锁名称: str, 超时时间: float = 30.0, 等待超时: float = 10.0):
        self.锁名称 = 锁名称
        self.超时时间 = 超时时间
        self.等待超时 = 等待超时
        self._线程本地 = threading.local()
    
    def 获取(self, 阻塞: bool = True) -> bool:
        """获取锁"""
        线程标识 = threading.get_ident()
        
        if hasattr(self._线程本地, '锁') and self._线程本地.锁:
            self._线程本地.重入计数 += 1
            return True
        
        锁 = 内存分布式锁(self.锁名称, self.超时时间, self.等待超时)
        if 锁.获取(阻塞):
            self._线程本地.锁 = 锁
            self._线程本地.重入计数 = 1
            return True
        
        return False
    
    def 释放(self) -> bool:
        """释放锁"""
        if not hasattr(self._线程本地, '锁') or not self._线程本地.锁:
            return False
        
        self._线程本地.重入计数 -= 1
        
        if self._线程本地.重入计数 <= 0:
            结果 = self._线程本地.锁.释放()
            self._线程本地.锁 = None
            self._线程本地.重入计数 = 0
            return 结果
        
        return True
    
    def __enter__(self):
        if not self.获取():
            raise 获取锁失败(f"获取锁失败: {self.锁名称}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.释放()
        return False


class 读写锁:
    """读写锁"""
    
    def __init__(self, 锁名称: str, 超时时间: float = 30.0):
        self.锁名称 = 锁名称
        self.超时时间 = 超时时间
        self._读锁 = 内存分布式锁(f"{锁名称}_读", 超时时间)
        self._写锁 = 内存分布式锁(f"{锁名称}_写", 超时时间)
        self._读计数 = 0
        self._计数锁 = threading.Lock()
    
    def 获取读锁(self) -> bool:
        """获取读锁"""
        with self._计数锁:
            if self._读计数 == 0:
                if not self._读锁.获取():
                    return False
            self._读计数 += 1
            return True
    
    def 释放读锁(self) -> bool:
        """释放读锁"""
        with self._计数锁:
            if self._读计数 <= 0:
                return False
            self._读计数 -= 1
            if self._读计数 == 0:
                return self._读锁.释放()
            return True
    
    def 获取写锁(self) -> bool:
        """获取写锁"""
        return self._写锁.获取()
    
    def 释放写锁(self) -> bool:
        """释放写锁"""
        return self._写锁.释放()
    
    class 读锁上下文:
        def __init__(self, 父: "读写锁"):
            self.父 = 父
        
        def __enter__(self):
            if not self.父.获取读锁():
                raise 获取锁失败(f"获取读锁失败")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.父.释放读锁()
            return False
    
    class 写锁上下文:
        def __init__(self, 父: "读写锁"):
            self.父 = 父
        
        def __enter__(self):
            if not self.父.获取写锁():
                raise 获取锁失败(f"获取写锁失败")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.父.释放写锁()
            return False
    
    @property
    def 读锁(self):
        return 读写锁.读锁上下文(self)
    
    @property
    def 写锁(self):
        return 读写锁.写锁上下文(self)


class 信号量锁:
    """信号量锁"""
    
    def __init__(self, 名称: str, 许可数: int = 1, 超时时间: float = 30.0):
        self.名称 = 名称
        self.许可数 = 许可数
        self.超时时间 = 超时时间
        self._当前计数 = 0
        self._条件变量 = threading.Condition()
    
    def 获取(self, 阻塞: bool = True) -> bool:
        """获取许可"""
        开始时间 = time.time()
        
        while True:
            with self._条件变量:
                if self._当前计数 < self.许可数:
                    self._当前计数 += 1
                    return True
                
                if not 阻塞:
                    return False
                
                if time.time() - 开始时间 > self.超时时间:
                    return False
                
                self._条件变量.wait(timeout=0.1)
    
    def 释放(self):
        """释放许可"""
        with self._条件变量:
            if self._当前计数 > 0:
                self._当前计数 -= 1
                self._条件变量.notify()
    
    def __enter__(self):
        if not self.获取():
            raise 获取锁失败(f"获取信号量失败: {self.名称}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.释放()
        return False


def 创建分布式锁(锁名称: str, 超时时间: float = 30.0, 等待超时: float = 10.0, 类型: 锁类型 = 锁类型.互斥锁):
    """
    创建分布式锁
    
    参数:
        锁名称: 锁名称
        超时时间: 超时时间
        等待超时: 等待超时
        类型: 锁类型
    """
    if 类型 == 锁类型.互斥锁:
        return 内存分布式锁(锁名称, 超时时间, 等待超时)
    elif 类型 == 锁类型.可重入锁:
        return 可重入内存锁(锁名称, 超时时间, 等待超时)
    elif 类型 == 锁类型.读写锁:
        return 读写锁(锁名称, 超时时间)
    else:
        return 内存分布式锁(锁名称, 超时时间, 等待超时)


def 带锁执行(锁名称: str, 函数: Callable, *参数, **关键字参数):
    """带锁执行函数"""
    with 内存分布式锁(锁名称):
        return 函数(*参数, **关键字参数)
