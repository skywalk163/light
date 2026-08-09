# -*- coding: utf-8 -*-
"""
光明标准库 - 线程管理模块

基于 contrib/线程 实现，提供线程创建、管理和同步功能。
"""

import threading
import time
import os
import queue
from typing import Callable, Any, Optional, List, Dict


class 线程:
    """线程类"""

    def __init__(self, 目标函数: Callable, *参数, 名称: str = None, 守护线程: bool = False, **关键字参数):
        """
        创建线程

        参数:
            目标函数: 线程执行的目标函数
            名称: 线程名称
            守护线程: 是否为守护线程
        """
        self._目标 = 目标函数
        self._参数 = 参数
        self._关键字参数 = 关键字参数
        self._名称 = 名称
        self._守护线程 = 守护线程
        self._线程 = None
        self._结果 = None
        self._异常 = None
        self._已完成 = False

    def 开始(self):
        """启动线程"""
        if self._线程 is not None:
            raise RuntimeError("线程已启动")

        def _包装():
            try:
                self._结果 = self._目标(*self._参数, **self._关键字参数)
            except Exception as e:
                self._异常 = e
            finally:
                self._已完成 = True

        self._线程 = threading.Thread(
            target=_包装, name=self._名称, daemon=self._守护线程
        )
        self._线程.start()

    def 等待(self, 超时: float = None) -> bool:
        """
        等待线程完成

        参数:
            超时: 超时秒数

        返回:
            是否在超时前完成
        """
        if self._线程 is None:
            return True
        self._线程.join(timeout=超时)
        return not self._线程.is_alive()

    def join(self, 超时: float = None):
        """等待线程完成（别名，与测试兼容）"""
        self.等待(超时=超时)

    def 是否存活(self) -> bool:
        """检查线程是否存活"""
        if self._线程 is None:
            return False
        return self._线程.is_alive()

    def 是否完成(self) -> bool:
        """检查线程是否完成"""
        return self._已完成

    def 获取结果(self, 超时: float = None) -> Any:
        """
        获取线程执行结果

        参数:
            超时: 等待超时秒数

        返回:
            线程目标函数的返回值
        """
        self.等待(超时=超时)
        if self._异常 is not None:
            raise self._异常
        if not self._已完成:
            raise RuntimeError("线程执行超时")
        return self._结果

    def 获取异常(self) -> Optional[Exception]:
        """获取线程异常"""
        return self._异常


class 互斥锁:
    """互斥锁类"""

    def __init__(self, 可重入: bool = False):
        """
        创建互斥锁

        参数:
            可重入: 是否可重入锁
        """
        if 可重入:
            self._锁 = threading.RLock()
        else:
            self._锁 = threading.Lock()

    def 加锁(self, 阻塞: bool = True, 超时: float = -1) -> bool:
        """
        加锁

        参数:
            阻塞: 是否阻塞等待
            超时: 超时秒数（-1 无限等待）

        返回:
            是否成功获得锁
        """
        return self._锁.acquire(blocking=阻塞, timeout=超时 if 超时 >= 0 else -1)

    def 释放(self):
        """释放锁"""
        try:
            self._锁.release()
        except RuntimeError:
            pass

    def 解锁(self):
        """解锁（别名，与测试兼容）"""
        self.释放()

    def 已锁定(self) -> bool:
        """检查锁是否已被锁定"""
        return self._锁.locked()

    def __enter__(self):
        self.加锁()
        return self

    def __exit__(self, *args):
        self.释放()


class 事件:
    """事件类，用于线程间通信"""

    def __init__(self):
        self._事件 = threading.Event()

    def 等待(self, 超时: float = None) -> bool:
        """
        等待事件被设置

        参数:
            超时: 超时秒数

        返回:
            是否在超时前被设置
        """
        return self._事件.wait(timeout=超时)

    def 设置(self):
        """设置事件"""
        self._事件.set()

    def 清除(self):
        """清除事件"""
        self._事件.clear()

    def 是否设置(self) -> bool:
        """检查事件是否被设置"""
        return self._事件.is_set()

    是否已设置 = 是否设置


class 信号量:
    """信号量类"""

    def __init__(self, 初始值: int = 1):
        """
        创建信号量

        参数:
            初始值: 初始计数
        """
        self._信号量 = threading.Semaphore(初始值)

    def 获取(self, 阻塞: bool = True, 超时: float = None) -> bool:
        """
        获取信号量

        参数:
            阻塞: 是否阻塞等待
            超时: 超时秒数

        返回:
            是否成功获取
        """
        return self._信号量.acquire(blocking=阻塞, timeout=超时)

    def 释放(self):
        """释放信号量"""
        self._信号量.release()


def 创建线程(目标函数: Callable, *参数, 名称: str = None, 守护线程: bool = False, **关键字参数) -> '线程':
    """
    创建并启动一个线程

    参数:
        目标函数: 线程执行函数
        名称: 线程名称
        守护线程: 是否为守护线程

    返回:
        线程对象
    """
    t = 线程(目标函数, *参数, 名称=名称, 守护线程=守护线程, **关键字参数)
    t.开始()
    return t


def 当前线程标识() -> int:
    """获取当前线程标识符"""
    return threading.get_ident()


def 活跃线程数() -> int:
    """获取活跃线程数"""
    return threading.active_count()


def 当前线程名称() -> str:
    """获取当前线程名称"""
    return threading.current_thread().name


def 线程休眠(秒: float):
    """线程休眠指定秒数"""
    time.sleep(秒)


class 线程安全队列:
    """线程安全队列"""

    def __init__(self, 最大大小: int = 0):
        """
        创建线程安全队列

        参数:
            最大大小: 队列最大容量，0 表示不限
        """
        self._队列 = queue.Queue(maxsize=最大大小 if 最大大小 > 0 else 0)

    def 空(self) -> bool:
        """检查队列是否为空"""
        return self._队列.empty()

    def 入队(self, 项目, 阻塞: bool = True, 超时: float = None):
        """
        入队

        参数:
            项目: 入队元素
            阻塞: 是否阻塞等待
            超时: 超时秒数
        """
        self._队列.put(项目, block=阻塞, timeout=超时)

    def 出队(self, 阻塞: bool = True, 超时: float = None) -> Any:
        """
        出队

        参数:
            阻塞: 是否阻塞等待
            超时: 超时秒数

        返回:
            队列头部元素
        """
        return self._队列.get(block=阻塞, timeout=超时)


class 线程池:
    """线程池类"""

    def __init__(self, 最大线程数: int = None):
        """
        创建线程池

        参数:
            最大线程数: 最大线程数
        """
        self._最大线程数 = 最大线程数 or (os.cpu_count() or 4)
        self._池 = None
        self._futures = []
        self._已启动 = False

    def 启动(self):
        """启动线程池"""
        from concurrent.futures import ThreadPoolExecutor
        self._池 = ThreadPoolExecutor(max_workers=self._最大线程数)
        self._futures = []
        self._已启动 = True

    def 提交(self, 函数, *参数, 结果回调=None):
        """
        提交任务到线程池

        参数:
            函数: 要执行的函数
            结果回调: 回调函数，接收 (result, error)
        """
        if not self._已启动:
            raise RuntimeError("线程池未启动")

        future = self._池.submit(函数, *参数)
        if 结果回调:
            def _回调(fut):
                try:
                    r = fut.result()
                    结果回调(r, None)
                except Exception as e:
                    结果回调(None, e)
            future.add_done_callback(_回调)
        self._futures.append(future)

    def 等待完成(self):
        """等待所有任务完成"""
        from concurrent.futures import wait
        if self._futures:
            wait(self._futures)

    def 关闭(self):
        """关闭线程池"""
        if self._池:
            self._池.shutdown(wait=False)
            self._池 = None
            self._已启动 = False


def 并发执行(任务列表: List[Callable], 最大线程数: int = None) -> List[Any]:
    """
    并发执行多个函数

    参数:
        任务列表: 可调用对象列表
        最大线程数: 最大并发数

    返回:
        各函数执行结果列表
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=最大线程数) as pool:
        futures = [pool.submit(task) for task in 任务列表]
        return [f.result() for f in futures]


def 并发执行带参数(函数: Callable, 参数列表: List[tuple], 最大线程数: int = None) -> List[Any]:
    """
    并发执行带参数的函数

    参数:
        函数: 要执行的函数
        参数列表: 参数元组列表
        最大线程数: 最大并发数

    返回:
        各函数执行结果列表
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=最大线程数) as pool:
        futures = [pool.submit(函数, *args) for args in 参数列表]
        return [f.result() for f in futures]


__all__ = [
    '线程', '互斥锁', '事件', '信号量',
    '创建线程', '当前线程标识', '活跃线程数',
    '当前线程名称', '线程休眠', '线程池',
    '线程安全队列', '并发执行', '并发执行带参数',
]