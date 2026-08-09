"""
光明标准库 - 线程模块

提供线程相关功能，包括：
- 线程创建与管理
- 线程锁
- 信号量
- 事件
- 线程池
"""

import threading
import time
import queue
from typing import Callable, Any, Optional, List, Dict


def 创建线程(函数: Callable, *参数, 守护线程: bool = False, 名称: str = None, **关键字参数) -> threading.Thread:
    """创建并启动一个线程"""
    t = threading.Thread(target=函数, args=参数, kwargs=关键字参数, name=名称, daemon=守护线程)
    t.start()
    return t


def 当前线程() -> threading.Thread:
    """获取当前线程对象"""
    return threading.current_thread()


def 当前线程标识() -> int:
    """获取当前线程ID"""
    return threading.get_ident()


def 活跃线程数() -> int:
    """获取当前活跃线程数"""
    return threading.active_count()


def 主线程() -> threading.Thread:
    """获取主线程对象"""
    return threading.main_thread()


def 枚举线程() -> List[threading.Thread]:
    """枚举所有活跃线程"""
    return list(threading.enumerate())


class 线程:
    """线程类"""
    
    def __init__(self, 函数: Callable, *参数, 名称: str = None, 守护线程: bool = False, **关键字参数):
        self._函数 = 函数
        self._参数 = 参数
        self._关键字参数 = 关键字参数
        self._结果 = None
        self._异常 = None
        self._已完成 = False
        
        def 包装器():
            try:
                self._结果 = 函数(*参数, **关键字参数)
            except Exception as e:
                self._异常 = e
            finally:
                self._已完成 = True
        
        self._线程 = threading.Thread(target=包装器, name=名称, daemon=守护线程)
    
    def 开始(self):
        """启动线程"""
        self._线程.start()
    
    def 等待(self, 超时: float = None) -> bool:
        """等待线程完成"""
        self._线程.join(timeout=超时)
        return not self._线程.is_alive()
    
    def 是否存活(self) -> bool:
        """检查线程是否存活"""
        return self._线程.is_alive()
    
    def 是否完成(self) -> bool:
        """检查任务是否完成"""
        return self._已完成
    
    def 获取结果(self, 超时: float = None) -> Any:
        """获取线程执行结果"""
        self.等待(超时=超时)
        if self._异常 is not None:
            raise self._异常
        if not self._已完成:
            raise TimeoutError("线程执行超时")
        return self._结果
    
    def 获取异常(self) -> Optional[Exception]:
        """获取线程异常"""
        return self._异常
    
    @property
    def 名称(self) -> str:
        return self._线程.name
    
    @property
    def 标识(self) -> int:
        return self._线程.ident


class 互斥锁:
    """互斥锁（可重入）"""
    
    def __init__(self, 可重入: bool = False):
        self._锁 = threading.RLock() if 可重入 else threading.Lock()
    
    def 加锁(self, 阻塞: bool = True, 超时: float = -1) -> bool:
        """获取锁"""
        return self._锁.acquire(blocking=阻塞, timeout=超时)
    
    def 解锁(self):
        """释放锁"""
        self._锁.release()
    
    def 已锁定(self) -> bool:
        """检查锁是否被持有"""
        return self._锁.locked()
    
    def __enter__(self):
        self.加锁()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.解锁()
        return False


class 信号量:
    """信号量"""
    
    def __init__(self, 初始值: int = 1):
        self._信号量 = threading.Semaphore(初始值)
    
    def 获取(self, 阻塞: bool = True, 超时: float = None) -> bool:
        """获取信号量"""
        return self._信号量.acquire(blocking=阻塞, timeout=超时)
    
    def 释放(self, n: int = 1):
        """释放信号量"""
        for _ in range(n):
            self._信号量.release()
    
    def __enter__(self):
        self.获取()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.释放()
        return False


class 事件:
    """事件对象"""
    
    def __init__(self):
        self._事件 = threading.Event()
    
    def 设置(self):
        """设置事件"""
        self._事件.set()
    
    def 清除(self):
        """清除事件"""
        self._事件.clear()
    
    def 是否已设置(self) -> bool:
        """检查事件是否已设置"""
        return self._事件.is_set()
    
    def 等待(self, 超时: float = None) -> bool:
        """等待事件被设置"""
        return self._事件.wait(timeout=超时)


class 条件变量:
    """条件变量"""
    
    def __init__(self, 锁: 互斥锁 = None):
        if 锁 is not None:
            self._条件 = threading.Condition(锁._锁)
        else:
            self._条件 = threading.Condition()
    
    def 获取(self):
        """获取底层锁"""
        self._条件.acquire()
    
    def 释放(self):
        """释放底层锁"""
        self._条件.release()
    
    def 等待(self, 超时: float = None) -> bool:
        """等待条件"""
        return self._条件.wait(timeout=超时)
    
    def 等待直到(self, 断言函数: Callable, 超时: float = None) -> bool:
        """等待直到断言为真"""
        return self._条件.wait_for(断言函数, timeout=超时)
    
    def 通知(self, n: int = 1):
        """通知n个等待线程"""
        self._条件.notify(n=n)
    
    def 全部通知(self):
        """通知所有等待线程"""
        self._条件.notify_all()
    
    def __enter__(self):
        self.获取()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.释放()
        return False


class 栅栏:
    """栅栏（屏障）"""
    
    def __init__(self, 线程数: int, 动作: Callable = None, 超时: float = None):
        self._栅栏 = threading.Barrier(线程数, action=动作, timeout=超时)
    
    def 等待(self, 超时: float = None) -> int:
        """等待栅栏"""
        return self._栅栏.wait(timeout=超时)
    
    def 重置(self):
        """重置栅栏"""
        self._栅栏.reset()
    
    def 中止(self):
        """中止栅栏"""
        self._栅栏.abort()
    
    def 是否已中断(self) -> bool:
        """检查栅栏是否已中断"""
        return self._栅栏.broken
    
    @property
    def 参与方数(self) -> int:
        return self._栅栏.parties
    
    @property
    def 等待数(self) -> int:
        return self._栅栏.n_waiting


class 线程安全队列:
    """线程安全队列"""
    
    def __init__(self, 最大容量: int = 0):
        self._队列 = queue.Queue(maxsize=最大容量)
    
    def 入队(self, 项目: Any, 阻塞: bool = True, 超时: float = None):
        """放入项目"""
        self._队列.put(项目, block=阻塞, timeout=超时)
    
    def 出队(self, 阻塞: bool = True, 超时: float = None) -> Any:
        """取出项目"""
        return self._队列.get(block=阻塞, timeout=超时)
    
    def 队首(self) -> Any:
        """查看队首元素（不移除）"""
        if self.空():
            raise IndexError("队列为空")
        return self._队列.queue[0]
    
    def 大小(self) -> int:
        """获取队列大小"""
        return self._队列.qsize()
    
    def 空(self) -> bool:
        """检查队列是否为空"""
        return self._队列.empty()
    
    def 满(self) -> bool:
        """检查队列是否已满"""
        return self._队列.full()
    
    def 清空(self):
        """清空队列"""
        while not self._队列.empty():
            try:
                self._队列.get_nowait()
            except queue.Empty:
                break
    
    def 任务完成(self):
        """标记一个任务完成"""
        self._队列.task_done()
    
    def 等待完成(self):
        """等待所有任务完成"""
        self._队列.join()


class 线程池:
    """线程池"""
    
    def __init__(self, 最大线程数: int = 4):
        self._最大线程数 = 最大线程数
        self._任务队列 = queue.Queue()
        self._线程 = []
        self._运行中 = False
        self._锁 = threading.Lock()
        self._活跃任务数 = 0
        self._条件 = threading.Condition()
    
    def 启动(self):
        """启动线程池"""
        if self._运行中:
            return
        self._运行中 = True
        for i in range(self._最大线程数):
            t = threading.Thread(target=self._工作线程, name=f'线程池-{i}')
            t.daemon = True
            t.start()
            self._线程.append(t)
    
    def _工作线程(self):
        """工作线程主循环"""
        while self._运行中:
            try:
                任务 = self._任务队列.get(timeout=0.1)
                函数, 参数, 关键字参数, 结果回调 = 任务
                
                with self._条件:
                    self._活跃任务数 += 1
                
                try:
                    结果 = 函数(*参数, **关键字参数)
                    if 结果回调:
                        try:
                            结果回调(结果, None)
                        except:
                            pass
                except Exception as e:
                    if 结果回调:
                        try:
                            结果回调(None, e)
                        except:
                            pass
                finally:
                    with self._条件:
                        self._活跃任务数 -= 1
                        self._条件.notify_all()
                
                self._任务队列.task_done()
            except queue.Empty:
                continue
    
    def 提交(self, 函数: Callable, *参数, 结果回调: Callable = None, **关键字参数):
        """提交任务"""
        if not self._运行中:
            self.启动()
        self._任务队列.put((函数, 参数, 关键字参数, 结果回调))
    
    def 等待完成(self):
        """等待所有任务完成"""
        self._任务队列.join()
        with self._条件:
            while self._活跃任务数 > 0:
                self._条件.wait()
    
    def 关闭(self, 等待: bool = True):
        """关闭线程池"""
        if 等待:
            self.等待完成()
        self._运行中 = False
        for t in self._线程:
            t.join(timeout=1)
        self._线程.clear()
    
    @property
    def 活跃任务数(self) -> int:
        return self._活跃任务数
    
    @property
    def 待处理任务数(self) -> int:
        return self._任务队列.qsize()
    
    @property
    def 最大线程数(self) -> int:
        return self._最大线程数


def 并发执行(函数列表: List[Callable], 最大线程数: int = 4) -> List[Any]:
    """并发执行多个函数，返回结果列表"""
    结果 = [None] * len(函数列表)
    锁 = threading.Lock()
    
    def 执行任务(索引, 函数):
        r = 函数()
        with 锁:
            结果[索引] = r
    
    tp = 线程池(最大线程数)
    for i, f in enumerate(函数列表):
        tp.提交(执行任务, i, f)
    tp.等待完成()
    tp.关闭()
    return 结果


def 并发执行带参数(函数: Callable, 参数列表: List[tuple], 最大线程数: int = 4) -> List[Any]:
    """并发执行同一函数不同参数，返回结果列表"""
    结果 = [None] * len(参数列表)
    锁 = threading.Lock()
    
    def 执行任务(索引, 参数):
        r = 函数(*参数)
        with 锁:
            结果[索引] = r
    
    tp = 线程池(最大线程数)
    for i, p in enumerate(参数列表):
        tp.提交(执行任务, i, p)
    tp.等待完成()
    tp.关闭()
    return 结果


__all__ = [
    '创建线程', '当前线程', '当前线程标识', '活跃线程数', '主线程', '枚举线程',
    '线程', '互斥锁', '信号量', '事件', '条件变量', '栅栏',
    '线程安全队列', '线程池', '并发执行', '并发执行带参数'
]