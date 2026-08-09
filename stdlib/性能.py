# -*- coding: utf-8 -*-
"""
光明标准库 - 性能分析模块

提供计时、内存测量、性能分析等功能。
"""

import time
import tracemalloc
import functools
from typing import Callable, Any, Optional, Dict, List


class 计时器:
    """计时器类，用于测量代码执行时间"""

    def __init__(self, 名称: str = ''):
        self._名称 = 名称
        self._开始时间 = None
        self._结束时间 = None
        self._耗时 = None

    def 开始(self):
        """开始计时"""
        self._开始时间 = time.perf_counter()
        return self

    def 停止(self) -> float:
        """
        停止计时

        返回:
            耗时秒数
        """
        self._结束时间 = time.perf_counter()
        self._耗时 = self._结束时间 - self._开始时间
        return self._耗时

    def 重置(self):
        """重置计时器"""
        self._开始时间 = None
        self._结束时间 = None
        self._耗时 = None

    def 获取耗时(self) -> float:
        """获取耗时秒数"""
        if self._耗时 is not None:
            return self._耗时
        if self._开始时间 is not None:
            return time.perf_counter() - self._开始时间
        return 0.0

    def __enter__(self):
        self.开始()
        return self

    def __exit__(self, *args):
        self.停止()

    def __str__(self) -> str:
        耗时 = self.获取耗时()
        if 耗时 < 0.001:
            return f"{self._名称}耗时: {耗时 * 1000000:.1f} µs"
        elif 耗时 < 1.0:
            return f"{self._名称}耗时: {耗时 * 1000:.2f} ms"
        else:
            return f"{self._名称}耗时: {耗时:.3f} s"


def 测量时间(函数: Callable) -> Callable:
    """
    装饰器：测量函数执行时间

    用法:
        @测量时间
        def 我的函数():
            ...
    """
    @functools.wraps(函数)
    def 包装(*args, **kwargs):
        计时器 = 计时器(函数.__name__)
        计时器.开始()
        try:
            return 函数(*args, **kwargs)
        finally:
            计时器.停止()
            print(计时器)
    return 包装


def 测量内存(函数: Callable) -> Callable:
    """
    装饰器：测量函数执行的内存峰值

    用法:
        @测量内存
        def 我的函数():
            ...
    """
    @functools.wraps(函数)
    def 包装(*args, **kwargs):
        tracemalloc.start()
        try:
            result = 函数(*args, **kwargs)
            current, peak = tracemalloc.get_traced_memory()
            print(f"{函数.__name__} 内存峰值: {_格式化内存(peak)}")
            return result
        finally:
            tracemalloc.stop()
    return 包装


def 测量时间详细(函数: Callable) -> Callable:
    """
    装饰器：详细测量函数执行时间（多次运行取平均）

    用法:
        @测量时间详细
        def 我的函数():
            ...
    """
    @functools.wraps(函数)
    def 包装(*args, **kwargs):
        耗时列表 = []
        for i in range(5):
            计时器 = 计时器()
            计时器.开始()
            函数(*args, **kwargs)
            计时器.停止()
            耗时列表.append(计时器.获取耗时())

        平均 = sum(耗时列表) / len(耗时列表)
        最小 = min(耗时列表)
        最大 = max(耗时列表)
        print(f"{函数.__name__}: 平均={_格式化时间(平均)}, 最小={_格式化时间(最小)}, 最大={_格式化时间(最大)}")
        return 函数(*args, **kwargs)
    return 包装


def 性能分析(函数: Callable) -> Callable:
    """
    装饰器：简单的性能分析器

    记录函数调用次数和总耗时
    """
    调用次数 = 0
    总耗时 = 0.0

    @functools.wraps(函数)
    def 包装(*args, **kwargs):
        nonlocal 调用次数, 总耗时
        计时器 = 计时器()
        计时器.开始()
        try:
            return 函数(*args, **kwargs)
        finally:
            计时器.停止()
            调用次数 += 1
            总耗时 += 计时器.获取耗时()
            包装.调用次数 = 调用次数
            包装.总耗时 = 总耗时
            包装.平均耗时 = 总耗时 / 调用次数 if 调用次数 else 0

    return 包装


def 当前时间戳() -> float:
    """获取当前时间戳（秒）"""
    return time.time()


def 高精度时间() -> float:
    """获取高精度时间（秒，用于性能测量）"""
    return time.perf_counter()


def 进程时间() -> float:
    """获取进程 CPU 时间（秒）"""
    return time.process_time()


def 睡眠(秒: float):
    """睡眠指定秒数"""
    time.sleep(秒)


def 获取内存使用() -> Dict[str, int]:
    """
    获取当前内存使用情况

    返回:
        内存使用字典（字节）
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        return {
            'RSS': mem.rss,
            'VMS': mem.vms,
        }
    except ImportError:
        return {'RSS': 0, 'VMS': 0}


def _格式化时间(秒: float) -> str:
    """格式化时间显示"""
    if 秒 < 0.001:
        return f"{秒 * 1000000:.1f} µs"
    elif 秒 < 1.0:
        return f"{秒 * 1000:.2f} ms"
    else:
        return f"{秒:.3f} s"


def _格式化内存(字节: int) -> str:
    """格式化内存显示"""
    if 字节 < 1024:
        return f"{字节} B"
    elif 字节 < 1024 * 1024:
        return f"{字节 / 1024:.1f} KB"
    else:
        return f"{字节 / (1024 * 1024):.1f} MB"


__all__ = [
    '计时器', '测量时间', '测量内存', '测量时间详细', '性能分析',
    '当前时间戳', '高精度时间', '进程时间', '睡眠', '获取内存使用',
]