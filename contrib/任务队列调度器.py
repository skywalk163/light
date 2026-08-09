"""
光明标准库 - 任务队列与调度器模块

提供任务队列和定时调度支持，包括：
- 任务队列（异步任务执行）
- 定时任务调度器（Cron风格）
- 间隔任务调度器
- 任务重试机制
- 任务优先级
- 任务状态追踪
"""

import threading
import time
import uuid
import heapq
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from collections import defaultdict


class 任务状态(Enum):
    """任务状态枚举"""
    待执行 = "待执行"
    执行中 = "执行中"
    已完成 = "已完成"
    失败 = "失败"
    已取消 = "已取消"
    已重试 = "已重试"


class 任务:
    """任务对象"""
    
    def __init__(self, 函数: Callable, *参数, 任务标识: str = None, 优先级: int = 0, 
                 最大重试次数: int = 0, 重试延迟: float = 1.0, **关键字参数):
        self.任务标识 = 任务标识 or str(uuid.uuid4())
        self.函数 = 函数
        self.参数 = 参数
        self.关键字参数 = 关键字参数
        self.优先级 = 优先级
        self.最大重试次数 = 最大重试次数
        self.重试延迟 = 重试延迟
        self.当前重试次数 = 0
        self.状态 = 任务状态.待执行
        self.结果 = None
        self.异常 = None
        self.创建时间 = time.time()
        self.开始时间 = None
        self.结束时间 = None
        self.调度时间 = None
        self._回调 = []
    
    def 执行(self):
        """执行任务"""
        self.状态 = 任务状态.执行中
        self.开始时间 = time.time()
        
        try:
            self.结果 = self.函数(*self.参数, **self.关键字参数)
            self.状态 = 任务状态.已完成
        except Exception as e:
            self.异常 = e
            if self.当前重试次数 < self.最大重试次数:
                self.状态 = 任务状态.已重试
                self.当前重试次数 += 1
            else:
                self.状态 = 任务状态.失败
        finally:
            self.结束时间 = time.time()
        
        for 回调 in self._回调:
            try:
                回调(self)
            except Exception:
                pass
    
    def 添加回调(self, 回调: Callable):
        """添加完成回调"""
        self._回调.append(回调)
    
    def 耗时(self) -> Optional[float]:
        """获取执行耗时"""
        if self.开始时间 and self.结束时间:
            return self.结束时间 - self.开始时间
        return None
    
    def __lt__(self, 其他: "任务") -> bool:
        if self.调度时间 and 其他.调度时间:
            if self.调度时间 != 其他.调度时间:
                return self.调度时间 < 其他.调度时间
        return self.优先级 > 其他.优先级
    
    def __repr__(self):
        return f"任务(标识={self.任务标识[:8]}...,状态={self.状态.value})"


class 任务队列:
    """任务队列"""
    
    def __init__(self, 工作线程数: int = 4, 最大队列大小: int = 10000):
        self.工作线程数 = 工作线程数
        self.最大队列大小 = 最大队列大小
        self._队列 = []
        self._锁 = threading.Lock()
        self._条件变量 = threading.Condition(self._锁)
        self._工作线程 = []
        self._运行中 = False
        self._任务映射 = {}
        self._已完成任务 = {}
        self._最大已完成数 = 1000
    
    def 启动(self):
        """启动任务队列"""
        if self._运行中:
            return
        
        self._运行中 = True
        for i in range(self.工作线程数):
            t = threading.Thread(target=self._工作循环, name=f"任务线程_{i}", daemon=True)
            self._工作线程.append(t)
            t.start()
    
    def _工作循环(self):
        """工作线程循环"""
        while self._运行中:
            with self._条件变量:
                while not self._队列:
                    if not self._运行中:
                        return
                    self._条件变量.wait()
                
                任务 = heapq.heappop(self._队列)
            
            if 任务.调度时间 and 任务.调度时间 > time.time():
                time.sleep(min(任务.调度时间 - time.time(), 0.1))
                with self._条件变量:
                    heapq.heappush(self._队列, 任务)
                    self._条件变量.notify()
                continue
            
            if 任务.状态 == 任务状态.已取消:
                continue
            
            任务.执行()
            
            if 任务.状态 == 任务状态.已重试:
                任务.调度时间 = time.time() + 任务.重试延迟
                with self._条件变量:
                    heapq.heappush(self._队列, 任务)
            else:
                with self._锁:
                    if len(self._已完成任务) >= self._最大已完成数:
                        旧任务标识 = next(iter(self._已完成任务))
                        del self._已完成任务[旧任务标识]
                    self._已完成任务[任务.任务标识] = 任务
    
    def 提交(self, 函数: Callable, *参数, 优先级: int = 0, 延迟: float = 0.0,
             最大重试次数: int = 0, 重试延迟: float = 1.0, 回调: Optional[Callable] = None, **关键字参数) -> str:
        """
        提交任务
        
        参数:
            函数: 执行函数
            *参数: 位置参数
            优先级: 优先级（越大越优先）
            延迟: 延迟执行时间（秒）
            最大重试次数: 最大重试次数
            重试延迟: 重试延迟基数（秒）
            回调: 完成回调
            **关键字参数: 关键字参数
            
        返回:
            任务标识
        """
        任务对象 = 任务(函数, *参数, 优先级=优先级, 最大重试次数=最大重试次数, 
                       重试延迟=重试延迟, **关键字参数)
        
        if 回调:
            任务对象.添加回调(回调)
        
        if 延迟 > 0:
            任务对象.调度时间 = time.time() + 延迟
        
        with self._条件变量:
            while len(self._队列) >= self.最大队列大小:
                self._条件变量.wait()
            
            heapq.heappush(self._队列, 任务对象)
            self._任务映射[任务对象.任务标识] = 任务对象
            self._条件变量.notify()
        
        return 任务对象.任务标识
    
    def 获取任务状态(self, 任务标识: str) -> Optional[任务状态]:
        """获取任务状态"""
        with self._锁:
            if 任务标识 in self._已完成任务:
                return self._已完成任务[任务标识].状态
            if 任务标识 in self._任务映射:
                return self._任务映射[任务标识].状态
        return None
    
    def 获取任务结果(self, 任务标识: str, 等待: bool = False, 超时: float = None) -> Any:
        """
        获取任务结果
        
        参数:
            任务标识: 任务标识
            等待: 是否等待完成
            超时: 等待超时
        """
        开始时间 = time.time()
        
        while True:
            with self._锁:
                if 任务标识 in self._已完成任务:
                    任务 = self._已完成任务[任务标识]
                    if 任务.状态 == 任务状态.失败:
                        raise 任务.异常
                    return 任务.结果
            
            if not 等待:
                return None
            
            if 超时 is not None and time.time() - 开始时间 > 超时:
                raise TimeoutError("等待任务结果超时")
            
            time.sleep(0.01)
    
    def 取消任务(self, 任务标识: str) -> bool:
        """取消任务"""
        with self._锁:
            任务对象 = self._任务映射.get(任务标识)
            if 任务对象 and 任务对象.状态 == 任务状态.待执行:
                任务对象.状态 = 任务状态.已取消
                return True
        return False
    
    def 等待完成(self, 超时: float = None) -> bool:
        """等待所有任务完成"""
        开始时间 = time.time()
        
        while True:
            with self._锁:
                全部完成 = True
                for 任务 in self._任务映射.values():
                    if 任务.状态 in (任务状态.待执行, 任务状态.执行中, 任务状态.已重试):
                        全部完成 = False
                        break
                if 全部完成:
                    return True
            
            if 超时 is not None and time.time() - 开始时间 > 超时:
                return False
            
            time.sleep(0.01)
    
    def 停止(self, 等待: bool = True):
        """停止任务队列"""
        if 等待:
            self.等待完成()
        
        self._运行中 = False
        with self._条件变量:
            self._条件变量.notify_all()
        
        for t in self._工作线程:
            t.join(timeout=2.0)
        self._工作线程.clear()
    
    def 队列大小(self) -> int:
        """获取队列大小"""
        with self._锁:
            return len(self._队列)
    
    def __enter__(self):
        self.启动()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.停止()
        return False


class 定时调度器:
    """定时任务调度器"""
    
    def __init__(self):
        self._任务列表 = []
        self._锁 = threading.Lock()
        self._运行中 = False
        self._调度线程 = None
        self._任务标识计数 = 0
        self._任务映射 = {}
    
    def 添加间隔任务(self, 间隔: float, 函数: Callable, *参数, 立即执行: bool = False, **关键字参数) -> str:
        """
        添加间隔执行任务
        
        参数:
            间隔: 间隔时间（秒）
            函数: 执行函数
            *参数: 位置参数
            立即执行: 是否立即执行一次
            **关键字参数: 关键字参数
            
        返回:
            任务标识
        """
        self._任务标识计数 += 1
        任务标识 = f"间隔任务_{self._任务标识计数}"
        
        下次执行 = time.time() if 立即执行 else time.time() + 间隔
        
        任务信息 = {
            "标识": 任务标识,
            "类型": "间隔",
            "函数": 函数,
            "参数": 参数,
            "关键字参数": 关键字参数,
            "间隔": 间隔,
            "下次执行": 下次执行,
            "运行中": False,
            "启用": True
        }
        
        with self._锁:
            heapq.heappush(self._任务列表, (下次执行, 任务标识))
            self._任务映射[任务标识] = 任务信息
        
        return 任务标识
    
    def 添加定时任务(self, 执行时间: float, 函数: Callable, *参数, **关键字参数) -> str:
        """
        添加单次定时任务
        
        参数:
            执行时间: 执行时间戳
            函数: 执行函数
            *参数: 位置参数
            **关键字参数: 关键字参数
            
        返回:
            任务标识
        """
        self._任务标识计数 += 1
        任务标识 = f"定时任务_{self._任务标识计数}"
        
        任务信息 = {
            "标识": 任务标识,
            "类型": "单次",
            "函数": 函数,
            "参数": 参数,
            "关键字参数": 关键字参数,
            "下次执行": 执行时间,
            "运行中": False,
            "启用": True
        }
        
        with self._锁:
            heapq.heappush(self._任务列表, (执行时间, 任务标识))
            self._任务映射[任务标识] = 任务信息
        
        return 任务标识
    
    def 添加Cron任务(self, cron表达式: str, 函数: Callable, *参数, **关键字参数) -> str:
        """
        添加Cron风格任务（简化版）
        
        Cron格式: 分 时 日 月 周
        
        参数:
            cron表达式: Cron表达式
            函数: 执行函数
            *参数: 位置参数
            **关键字参数: 关键字参数
            
        返回:
            任务标识
        """
        字段 = cron表达式.strip().split()
        if len(字段) != 5:
            raise ValueError("Cron表达式必须包含5个字段: 分 时 日 月 周")
        
        def 解析字段(字段值: str, 最小值: int, 最大值: int) -> List[int]:
            if 字段值 == "*":
                return list(range(最小值, 最大值 + 1))
            if "," in 字段值:
                结果 = []
                for part in 字段值.split(","):
                    结果.extend(解析字段(part, 最小值, 最大值))
                return sorted(set(结果))
            if "-" in 字段值:
                开始, 结束 = map(int, 字段值.split("-"))
                return list(range(开始, 结束 + 1))
            return [int(字段值)]
        
        分钟列表 = 解析字段(字段[0], 0, 59)
        小时列表 = 解析字段(字段[1], 0, 23)
        日期列表 = 解析字段(字段[2], 1, 31)
        月份列表 = 解析字段(字段[3], 1, 12)
        星期列表 = 解析字段(字段[4], 0, 6)
        
        def 计算下次执行() -> float:
            import datetime
            现在 = datetime.datetime.now()
            下一分钟 = 现在 + datetime.timedelta(minutes=1)
            下一分钟 = 下一分钟.replace(second=0, microsecond=0)
            
            for _ in range(525600):
                if (下一分钟.minute in 分钟列表
                    and 下一分钟.hour in 小时列表
                    and 下一分钟.day in 日期列表
                    and 下一分钟.month in 月份列表
                    and 下一分钟.weekday() in 星期列表):
                    return 下一分钟.timestamp()
                下一分钟 += datetime.timedelta(minutes=1)
            
            return time.time() + 60
        
        self._任务标识计数 += 1
        任务标识 = f"Cron任务_{self._任务标识计数}"
        
        下次执行 = 计算下次执行()
        
        任务信息 = {
            "标识": 任务标识,
            "类型": "cron",
            "函数": 函数,
            "参数": 参数,
            "关键字参数": 关键字参数,
            "cron表达式": cron表达式,
            "计算下次执行": 计算下次执行,
            "下次执行": 下次执行,
            "运行中": False,
            "启用": True
        }
        
        with self._锁:
            heapq.heappush(self._任务列表, (下次执行, 任务标识))
            self._任务映射[任务标识] = 任务信息
        
        return 任务标识
    
    def 取消任务(self, 任务标识: str) -> bool:
        """取消任务"""
        with self._锁:
            if 任务标识 in self._任务映射:
                self._任务映射[任务标识]["启用"] = False
                return True
        return False
    
    def 启动(self):
        """启动调度器"""
        if self._运行中:
            return
        
        self._运行中 = True
        self._调度线程 = threading.Thread(target=self._调度循环, daemon=True)
        self._调度线程.start()
    
    def _调度循环(self):
        """调度循环"""
        while self._运行中:
            with self._锁:
                if not self._任务列表:
                    time.sleep(0.5)
                    continue
                
                下次执行时间, 任务标识 = self._任务列表[0]
                现在 = time.time()
                
                if 下次执行时间 > 现在:
                    time.sleep(min(下次执行时间 - 现在, 0.5))
                    continue
                
                heapq.heappop(self._任务列表)
                任务信息 = self._任务映射.get(任务标识)
                
                if not 任务信息 or not 任务信息["启用"]:
                    continue
                
                if 任务信息["运行中"]:
                    continue
            
            def 执行任务():
                try:
                    任务信息["函数"](*任务信息["参数"], **任务信息["关键字参数"])
                except Exception:
                    pass
                finally:
                    任务信息["运行中"] = False
                    
                    if 任务信息["类型"] == "间隔":
                        任务信息["下次执行"] = time.time() + 任务信息["间隔"]
                        with self._锁:
                            heapq.heappush(self._任务列表, (任务信息["下次执行"], 任务信息["标识"]))
                    elif 任务信息["类型"] == "cron":
                        任务信息["下次执行"] = 任务信息["计算下次执行"]()
                        with self._锁:
                            heapq.heappush(self._任务列表, (任务信息["下次执行"], 任务信息["标识"]))
                    elif 任务信息["类型"] == "单次":
                        with self._锁:
                            if 任务信息["标识"] in self._任务映射:
                                del self._任务映射[任务信息["标识"]]
            
            任务信息["运行中"] = True
            t = threading.Thread(target=执行任务, daemon=True)
            t.start()
    
    def 停止(self):
        """停止调度器"""
        self._运行中 = False
        if self._调度线程:
            self._调度线程.join(timeout=2.0)
            self._调度线程 = None
    
    def 获取任务列表(self) -> List[Dict]:
        """获取所有任务信息"""
        with self._锁:
            return [
                {
                    "标识": info["标识"],
                    "类型": info["类型"],
                    "下次执行": info["下次执行"],
                    "启用": info["启用"],
                    "运行中": info["运行中"]
                }
                for info in self._任务映射.values()
            ]
    
    def __enter__(self):
        self.启动()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.停止()
        return False


def 创建任务队列(工作线程数: int = 4) -> 任务队列:
    """创建任务队列"""
    tq = 任务队列(工作线程数)
    tq.启动()
    return tq


def 创建调度器() -> 定时调度器:
    """创建定时调度器"""
    return 定时调度器()


def 异步执行(函数: Callable, *参数, **关键字参数) -> 任务:
    """简易异步执行（单例任务队列）"""
    if not hasattr(异步执行, "_队列"):
        异步执行._队列 = 任务队列(工作线程数=4)
        异步执行._队列.启动()
    
    任务标识 = 异步执行._队列.提交(函数, *参数, **关键字参数)
    return 异步执行._队列._任务映射[任务标识]
