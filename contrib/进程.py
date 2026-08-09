"""
光明标准库 - 进程模块

提供进程相关功能，包括：
- 进程创建与管理
- 进程池
- 进程间通信（管道、队列）
- 共享内存
"""

import multiprocessing
import subprocess
import os
import sys
import time
from typing import Callable, Any, Optional, List, Dict, Tuple


def 当前进程标识() -> int:
    """获取当前进程ID"""
    return os.getpid()


def 父进程标识() -> int:
    """获取父进程ID"""
    return os.getppid()


def 进程名称() -> str:
    """获取当前进程名称"""
    return multiprocessing.current_process().name


def CPU核心数() -> int:
    """获取CPU核心数"""
    return os.cpu_count() or 1


def _进程工作函数(函数, 参数, 关键字参数, 结果队列):
    """进程工作函数（模块级别，可被pickle序列化）"""
    try:
        r = 函数(*参数, **关键字参数)
        结果队列.put(('结果', r))
    except Exception as e:
        结果队列.put(('异常', e))


def 执行系统命令(命令: str, 捕获输出: bool = True, 超时: float = None, 工作目录: str = None, 环境变量: dict = None) -> Dict[str, Any]:
    """执行系统命令
    
    返回: {返回码, 标准输出, 标准错误, 超时}
    """
    try:
        结果 = subprocess.run(
            命令,
            shell=True,
            capture_output=捕获输出,
            text=True,
            timeout=超时,
            cwd=工作目录,
            env=环境变量
        )
        return {
            '返回码': 结果.returncode,
            '标准输出': 结果.stdout if 捕获输出 else None,
            '标准错误': 结果.stderr if 捕获输出 else None,
            '超时': False
        }
    except subprocess.TimeoutExpired as e:
        return {
            '返回码': -1,
            '标准输出': e.stdout.decode() if e.stdout and 捕获输出 else None,
            '标准错误': e.stderr.decode() if e.stderr and 捕获输出 else None,
            '超时': True
        }


def 执行命令列表(参数列表: List[str], 捕获输出: bool = True, 超时: float = None, 工作目录: str = None, 环境变量: dict = None) -> Dict[str, Any]:
    """执行命令列表（非shell模式）"""
    try:
        结果 = subprocess.run(
            参数列表,
            capture_output=捕获输出,
            text=True,
            timeout=超时,
            cwd=工作目录,
            env=环境变量
        )
        return {
            '返回码': 结果.returncode,
            '标准输出': 结果.stdout if 捕获输出 else None,
            '标准错误': 结果.stderr if 捕获输出 else None,
            '超时': False
        }
    except subprocess.TimeoutExpired as e:
        return {
            '返回码': -1,
            '标准输出': e.stdout.decode() if e.stdout and 捕获输出 else None,
            '标准错误': e.stderr.decode() if e.stderr and 捕获输出 else None,
            '超时': True
        }


class 进程:
    """进程类"""
    
    def __init__(self, 函数: Callable, *参数, 名称: str = None, 守护进程: bool = False, **关键字参数):
        self._函数 = 函数
        self._参数 = 参数
        self._关键字参数 = 关键字参数
        self._结果 = None
        self._异常 = None
        self._已完成 = False
        
        self._结果队列 = multiprocessing.Queue()
        self._进程 = multiprocessing.Process(
            target=_进程工作函数,
            args=(函数, 参数, 关键字参数, self._结果队列),
            name=名称,
            daemon=守护进程
        )
    
    def 开始(self):
        """启动进程"""
        self._进程.start()
    
    def 等待(self, 超时: float = None) -> bool:
        """等待进程完成"""
        self._进程.join(timeout=超时)
        return not self._进程.is_alive()
    
    def 是否存活(self) -> bool:
        """检查进程是否存活"""
        return self._进程.is_alive()
    
    def 获取结果(self, 超时: float = None) -> Any:
        """获取进程执行结果"""
        if not self._已完成:
            if self.等待(超时=超时):
                try:
                    类型, 值 = self._结果队列.get(timeout=1)
                    if 类型 == '结果':
                        self._结果 = 值
                    else:
                        self._异常 = 值
                    self._已完成 = True
                except:
                    pass
        
        if self._异常 is not None:
            raise self._异常
        if not self._已完成:
            raise TimeoutError("进程执行超时")
        return self._结果
    
    def 终止(self):
        """终止进程"""
        self._进程.terminate()
    
    def 强制终止(self):
        """强制终止进程"""
        self._进程.kill()
    
    @property
    def 标识(self) -> int:
        return self._进程.pid
    
    @property
    def 名称(self) -> str:
        return self._进程.name
    
    @property
    def 退出码(self) -> Optional[int]:
        return self._进程.exitcode


class 进程池:
    """进程池"""
    
    def __init__(self, 进程数: int = None):
        self._进程数 = 进程数 or CPU核心数()
        self._池 = None
    
    def _确保启动(self):
        if self._池 is None:
            self._池 = multiprocessing.Pool(processes=self._进程数)
    
    def 启动(self):
        """启动进程池"""
        self._确保启动()
    
    def 应用(self, 函数: Callable, *参数, **关键字参数) -> Any:
        """同步执行任务"""
        self._确保启动()
        return self._池.apply(函数, args=参数, kwds=关键字参数)
    
    def 异步应用(self, 函数: Callable, *参数, 回调: Callable = None, 错误回调: Callable = None, **关键字参数):
        """异步执行任务"""
        self._确保启动()
        return self._池.apply_async(函数, args=参数, kwds=关键字参数, callback=回调, error_callback=错误回调)
    
    def 映射(self, 函数: Callable, 可迭代对象, 分块大小: int = None) -> List[Any]:
        """映射执行（同步）"""
        self._确保启动()
        return self._池.map(函数, 可迭代对象, chunksize=分块大小)
    
    def 异步映射(self, 函数: Callable, 可迭代对象, 回调: Callable = None, 分块大小: int = None):
        """映射执行（异步）"""
        self._确保启动()
        结果 = self._池.map_async(函数, 可迭代对象, chunksize=分块大小, callback=回调)
        return 结果
    
    def 关闭(self, 等待: bool = True):
        """关闭进程池"""
        if self._池 is not None:
            if 等待:
                self._池.close()
                self._池.join()
            else:
                self._池.terminate()
            self._池 = None
    
    def 终止(self):
        """立即终止"""
        if self._池 is not None:
            self._池.terminate()
            self._池 = None
    
    @property
    def 进程数(self) -> int:
        return self._进程数


class 进程队列:
    """进程间队列"""
    
    def __init__(self, 最大容量: int = 0):
        self._队列 = multiprocessing.Queue(maxsize=最大容量)
    
    def 入队(self, 项目: Any, 阻塞: bool = True, 超时: float = None):
        """放入项目"""
        self._队列.put(项目, block=阻塞, timeout=超时)
    
    def 出队(self, 阻塞: bool = True, 超时: float = None) -> Any:
        """取出项目"""
        return self._队列.get(block=阻塞, timeout=超时)
    
    def 大小(self) -> int:
        """获取队列大致大小"""
        return self._队列.qsize()
    
    def 空(self) -> bool:
        """检查队列是否为空"""
        return self._队列.empty()
    
    def 满(self) -> bool:
        """检查队列是否已满"""
        return self._队列.full()
    
    def 关闭(self):
        """关闭队列"""
        self._队列.close()
        self._队列.join_thread()


class 管道:
    """进程间管道"""
    
    def __init__(self, 双工: bool = True):
        self._父端, self._子端 = multiprocessing.Pipe(duplex=双工)
        self._本端 = None
        self._对端 = None
    
    def 标记父端(self):
        """标记当前进程使用父端"""
        self._本端 = self._父端
        self._对端 = self._子端
    
    def 标记子端(self):
        """标记当前进程使用子端"""
        self._本端 = self._子端
        self._对端 = self._父端
    
    def 发送(self, 数据: Any):
        """发送数据"""
        if self._本端 is None:
            raise RuntimeError("请先标记使用哪一端")
        self._本端.send(数据)
    
    def 接收(self) -> Any:
        """接收数据"""
        if self._本端 is None:
            raise RuntimeError("请先标记使用哪一端")
        return self._本端.recv()
    
    def 可接收(self, 超时: float = 0.0) -> bool:
        """检查是否有数据可接收"""
        if self._本端 is None:
            raise RuntimeError("请先标记使用哪一端")
        return self._本端.poll(timeout=超时)
    
    def 关闭本端(self):
        """关闭本端"""
        if self._本端 is not None:
            self._本端.close()
            self._本端 = None
    
    def 关闭对端(self):
        """关闭对端"""
        if self._对端 is not None:
            self._对端.close()
            self._对端 = None


class 共享值:
    """共享值"""
    
    def __init__(self, 类型码: str, 初始值: Any = None):
        self._值 = multiprocessing.Value(类型码, 初始值) if 初始值 is not None else multiprocessing.Value(类型码)
    
    @property
    def 值(self) -> Any:
        return self._值.value
    
    @值.setter
    def 值(self, 值):
        self._值.value = 值
    
    def 获取(self):
        """获取值"""
        return self._值.value
    
    def 设置(self, 值):
        """设置值"""
        self._值.value = 值


class 共享数组:
    """共享数组"""
    
    def __init__(self, 类型码: str, 大小或初始值):
        self._数组 = multiprocessing.Array(类型码, 大小或初始值)
    
    def 获取(self, 索引: int) -> Any:
        """获取元素"""
        return self._数组[索引]
    
    def 设置(self, 索引: int, 值: Any):
        """设置元素"""
        self._数组[索引] = 值
    
    def 长度(self) -> int:
        """获取数组长度"""
        return len(self._数组)
    
    def 转列表(self) -> list:
        """转为列表"""
        return list(self._数组)


class 进程锁:
    """进程锁"""
    
    def __init__(self):
        self._锁 = multiprocessing.Lock()
    
    def 加锁(self, 阻塞: bool = True, 超时: float = None) -> bool:
        """获取锁"""
        if 超时 is not None:
            return self._锁.acquire(timeout=超时)
        return self._锁.acquire(block=阻塞)
    
    def 解锁(self):
        """释放锁"""
        self._锁.release()
    
    def __enter__(self):
        self.加锁()
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.解锁()
        return False


def 并行处理(函数: Callable, 数据列表: list, 进程数: int = None) -> list:
    """并行处理数据列表"""
    池 = 进程池(进程数)
    结果 = 池.映射(函数, 数据列表)
    池.关闭()
    return 结果


__all__ = [
    '当前进程标识', '父进程标识', '进程名称', 'CPU核心数',
    '执行系统命令', '执行命令列表',
    '进程', '进程池', '进程队列', '管道',
    '共享值', '共享数组', '进程锁',
    '并行处理'
]