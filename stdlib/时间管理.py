"""
光明标准库 - 时间管理模块

提供时间管理功能，包括：
- 睡眠/延时
- 定时器
- 性能计时
- 倒计时
"""

import time
import threading
from datetime import datetime
from typing import Callable, Optional, Dict, Any


def 睡眠(秒数: float):
    """睡眠指定秒数"""
    time.sleep(秒数)


def 睡眠毫秒(毫秒数: int):
    """睡眠指定毫秒数"""
    time.sleep(毫秒数 / 1000.0)


def 精确睡眠(秒数: float):
    """更精确的睡眠（使用高精度计时器）"""
    结束时间 = time.perf_counter() + 秒数
    while time.perf_counter() < 结束时间:
        pass


class 计时器:
    """计时器类 - 用于测量代码执行时间"""
    
    def __init__(self):
        self._开始时间 = None
        self._结束时间 = None
        self._记录 = []
    
    def 开始(self):
        """开始计时"""
        self._开始时间 = time.perf_counter()
        self._结束时间 = None
    
    def 结束(self) -> float:
        """结束计时，返回经过的秒数"""
        if self._开始时间 is None:
            raise RuntimeError("计时器未开始")
        self._结束时间 = time.perf_counter()
        return self._结束时间 - self._开始时间
    
    def 经过时间(self) -> float:
        """获取当前经过的时间（不停止计时）"""
        if self._开始时间 is None:
            return 0.0
        if self._结束时间 is not None:
            return self._结束时间 - self._开始时间
        return time.perf_counter() - self._开始时间
    
    def 重置(self):
        """重置计时器"""
        self._开始时间 = None
        self._结束时间 = None
        self._记录.clear()
    
    def 打点(self, 名称: str = ''):
        """记录一个时间点"""
        当前时间 = self.经过时间()
        self._记录.append((名称, 当前时间))
        return 当前时间
    
    def 获取记录(self) -> list:
        """获取所有打点记录"""
        return list(self._记录)
    
    def 打印记录(self):
        """打印所有打点记录"""
        for 名称, 时间 in self._记录:
            if 名称:
                print(f'{名称}: {时间:.6f}秒')
            else:
                print(f'{时间:.6f}秒')
    
    def __enter__(self):
        self.开始()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.结束()
        return False


def 计时(函数: Callable) -> Callable:
    """计时装饰器"""
    def 包装器(*参数, **关键字参数):
        开始 = time.perf_counter()
        结果 = 函数(*参数, **关键字参数)
        结束 = time.perf_counter()
        print(f'{函数.__name__} 执行时间: {结束 - 开始:.6f}秒')
        return 结果
    return 包装器


def 计时函数(函数: Callable, *参数, **关键字参数) -> tuple:
    """计时函数执行，返回(结果, 耗时秒数)"""
    开始 = time.perf_counter()
    结果 = 函数(*参数, **关键字参数)
    结束 = time.perf_counter()
    return 结果, 结束 - 开始


def 多次计时(函数: Callable, 次数: int = 10, *参数, **关键字参数) -> Dict[str, float]:
    """多次计时函数，返回统计信息"""
    时间列表 = []
    结果 = None
    
    for _ in range(次数):
        开始 = time.perf_counter()
        结果 = 函数(*参数, **关键字参数)
        结束 = time.perf_counter()
        时间列表.append(结束 - 开始)
    
    return {
        '总时间': sum(时间列表),
        '平均时间': sum(时间列表) / len(时间列表),
        '最快': min(时间列表),
        '最慢': max(时间列表),
        '次数': 次数,
        '最后结果': 结果
    }


class 定时器:
    """定时器类 - 在指定时间后执行函数"""
    
    def __init__(self, 延迟秒数: float, 回调函数: Callable, *参数, **关键字参数):
        self._延迟 = 延迟秒数
        self._回调 = 回调函数
        self._参数 = 参数
        self._关键字参数 = 关键字参数
        self._定时器 = None
    
    def 开始(self):
        """启动定时器"""
        if self._定时器 is not None:
            raise RuntimeError("定时器已在运行")
        self._定时器 = threading.Timer(self._延迟, self._执行回调)
        self._定时器.start()
    
    def _执行回调(self):
        """执行回调函数"""
        self._回调(*self._参数, **self._关键字参数)
    
    def 取消(self):
        """取消定时器"""
        if self._定时器 is not None:
            self._定时器.cancel()
            self._定时器 = None
    
    def 是否运行中(self) -> bool:
        """检查定时器是否在运行"""
        return self._定时器 is not None and self._定时器.is_alive()


class 周期定时器:
    """周期定时器 - 周期性执行函数"""
    
    def __init__(self, 间隔秒数: float, 回调函数: Callable, *参数, **关键字参数):
        self._间隔 = 间隔秒数
        self._回调 = 回调函数
        self._参数 = 参数
        self._关键字参数 = 关键字参数
        self._运行中 = False
        self._线程 = None
    
    def 开始(self):
        """启动周期定时器"""
        if self._运行中:
            raise RuntimeError("定时器已在运行")
        self._运行中 = True
        self._线程 = threading.Thread(target=self._运行循环)
        self._线程.daemon = True
        self._线程.start()
    
    def _运行循环(self):
        """运行循环"""
        while self._运行中:
            self._回调(*self._参数, **self._关键字参数)
            time.sleep(self._间隔)
    
    def 停止(self):
        """停止周期定时器"""
        self._运行中 = False
        if self._线程 is not None:
            self._线程.join(timeout=self._间隔 * 2)
            self._线程 = None
    
    def 是否运行中(self) -> bool:
        """检查定时器是否在运行"""
        return self._运行中


class 倒计时:
    """倒计时类"""
    
    def __init__(self, 总秒数: float):
        self._总秒数 = 总秒数
        self._剩余秒数 = 总秒数
        self._开始时间 = None
        self._运行中 = False
        self._暂停时间 = None
    
    def 开始(self):
        """开始倒计时"""
        if self._运行中:
            raise RuntimeError("倒计时已在运行")
        self._开始时间 = time.perf_counter()
        self._运行中 = True
    
    def 暂停(self):
        """暂停倒计时"""
        if not self._运行中:
            return
        self._剩余秒数 = self.剩余时间()
        self._运行中 = False
        self._暂停时间 = time.perf_counter()
    
    def 继续(self):
        """继续倒计时"""
        if self._运行中:
            return
        self._开始时间 = time.perf_counter() - (self._总秒数 - self._剩余秒数)
        self._运行中 = True
    
    def 重置(self, 新总秒数: float = None):
        """重置倒计时"""
        if 新总秒数 is not None:
            self._总秒数 = 新总秒数
        self._剩余秒数 = self._总秒数
        self._开始时间 = None
        self._运行中 = False
        self._暂停时间 = None
    
    def 剩余时间(self) -> float:
        """获取剩余时间"""
        if not self._运行中:
            return max(0, self._剩余秒数)
        已过 = time.perf_counter() - self._开始时间
        return max(0, self._总秒数 - 已过)
    
    def 已过时间(self) -> float:
        """获取已过时间"""
        return self._总秒数 - self.剩余时间()
    
    def 是否结束(self) -> bool:
        """检查倒计时是否结束"""
        return self.剩余时间() <= 0
    
    def 是否运行中(self) -> bool:
        """检查倒计时是否在运行"""
        return self._运行中
    
    def 等待结束(self):
        """等待倒计时结束"""
        while not self.是否结束():
            time.sleep(0.01)


def 时间戳() -> float:
    """获取当前时间戳（秒）"""
    return time.time()


def 时间戳毫秒() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def 性能计数器() -> float:
    """获取高精度性能计数器值"""
    return time.perf_counter()


def 性能计数器纳秒() -> int:
    """获取高精度性能计数器值（纳秒）"""
    return time.perf_counter_ns()


def 进程时间() -> float:
    """获取进程CPU时间（秒）"""
    return time.process_time()


def 线程时间() -> float:
    """获取线程CPU时间（秒）"""
    return time.thread_time()


def 格式化耗时(秒数: float) -> str:
    """将秒数格式化为可读字符串"""
    if 秒数 < 0.001:
        return f'{秒数 * 1000000:.2f}微秒'
    elif 秒数 < 1:
        return f'{秒数 * 1000:.2f}毫秒'
    elif 秒数 < 60:
        return f'{秒数:.2f}秒'
    elif 秒数 < 3600:
        分钟 = int(秒数 // 60)
        秒 = 秒数 % 60
        return f'{分钟}分{秒:.2f}秒'
    else:
        小时 = int(秒数 // 3600)
        剩余 = 秒数 % 3600
        分钟 = int(剩余 // 60)
        秒 = 剩余 % 60
        return f'{小时}时{分钟}分{秒:.2f}秒'


# 合并自时间.py的独有函数


def 时间戳纳秒() -> int:
    """获取当前时间戳（纳秒级整数）"""
    return time.time_ns()


def 休眠(秒数: float) -> None:
    """休眠指定秒数"""
    time.sleep(秒数)


def 等待(秒数: float) -> None:
    """等待指定秒数（休眠的别名）"""
    time.sleep(秒数)


def 单调时间() -> float:
    """
    获取单调时钟值（不会因为系统时间调整而倒退）
    
    返回:
        单调时钟值（秒）
    """
    return time.monotonic()


def 测量执行时间(函数, *参数, **关键字参数) -> tuple:
    """
    测量函数执行时间
    
    参数:
        函数: 要测量的函数
        参数: 函数位置参数
        关键字参数: 函数关键字参数
    
    返回:
        (返回值, 耗时秒数)
    """
    开始 = time.perf_counter()
    结果 = 函数(*参数, **关键字参数)
    结束 = time.perf_counter()
    return 结果, 结束 - 开始


def 本地时间(时间戳: float = None) -> time.struct_time:
    """
    获取本地时间元组
    
    参数:
        时间戳: 时间戳，None表示当前时间
    
    返回:
        时间元组
    """
    if 时间戳 is None:
        return time.localtime()
    return time.localtime(时间戳)


def UTC时间(时间戳: float = None) -> time.struct_time:
    """
    获取UTC时间元组
    
    参数:
        时间戳: 时间戳，None表示当前时间
    
    返回:
        UTC时间元组
    """
    if 时间戳 is None:
        return time.gmtime()
    return time.gmtime(时间戳)


def 时间元组转时间戳(时间元组: time.struct_time) -> float:
    """时间元组转时间戳"""
    return time.mktime(时间元组)


def 格式化时间(格式: str = "%Y-%m-%d %H:%M:%S", 时间戳: float = None) -> str:
    """
    格式化时间
    
    参数:
        格式: 格式化字符串
        时间戳: 时间戳，None表示当前时间
    
    返回:
        格式化后的时间字符串
    """
    if 时间戳 is None:
        return time.strftime(格式, time.localtime())
    return time.strftime(格式, time.localtime(时间戳))


def 解析时间(时间字符串: str, 格式: str = "%Y-%m-%d %H:%M:%S") -> time.struct_time:
    """
    解析时间字符串为时间元组
    
    参数:
        时间字符串: 时间字符串
        格式: 格式化字符串
    
    返回:
        时间元组
    """
    return time.strptime(时间字符串, 格式)


def 时区偏移() -> int:
    """
    获取本地时区与UTC的偏移量（秒）
    
    返回:
        偏移秒数，负数表示在UTC以东（如中国为-28800）
    """
    return time.timezone


def 时区名称() -> str:
    """获取本地时区名称"""
    return time.tzname[0]


def 夏令时() -> bool:
    """当前是否为夏令时"""
    return time.daylight != 0


class 秒表:
    """秒表 - 用于测量经过时间"""
    
    def __init__(self, 自动启动: bool = True):
        self._开始时间 = None
        self._累计时间 = 0.0
        self._运行中 = False
        if 自动启动:
            self.启动()
    
    def 启动(self) -> None:
        """启动秒表"""
        if not self._运行中:
            self._开始时间 = time.perf_counter()
            self._运行中 = True
    
    def 停止(self) -> float:
        """停止秒表，返回累计时间"""
        if self._运行中:
            self._累计时间 += time.perf_counter() - self._开始时间
            self._运行中 = False
        return self._累计时间
    
    def 重置(self) -> None:
        """重置秒表"""
        self._开始时间 = None
        self._累计时间 = 0.0
        self._运行中 = False
    
    def 读取(self) -> float:
        """读取当前经过时间（不停止）"""
        if self._运行中:
            return self._累计时间 + (time.perf_counter() - self._开始时间)
        return self._累计时间
    
    def 打点(self, 名称: str = None) -> float:
        """记录一个时间点，返回从开始到现在的时间"""
        当前时间 = self.读取()
        return 当前时间


def 创建秒表(自动启动: bool = True) -> 秒表:
    """创建秒表（便捷函数）"""
    return 秒表(自动启动)


__all__ = [
    '睡眠', '睡眠毫秒', '精确睡眠',
    '计时器', '计时', '计时函数', '多次计时',
    '定时器', '周期定时器',
    '倒计时',
    '时间戳', '时间戳毫秒', '性能计数器', '性能计数器纳秒',
    '进程时间', '线程时间',
    '格式化耗时',
    # 合并自时间.py的独有函数
    '时间戳纳秒', '休眠', '等待',
    '单调时间', '测量执行时间',
    '本地时间', 'UTC时间', '时间元组转时间戳',
    '格式化时间', '解析时间',
    '时区偏移', '时区名称', '夏令时',
    '秒表', '创建秒表',
]