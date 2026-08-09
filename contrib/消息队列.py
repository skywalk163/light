"""
光明标准库 - 消息队列模块

提供消息队列支持，包括：
- 内存消息队列
- 生产者消费者模式
- 发布订阅模式
- 消息确认机制
- 死信队列
- 延迟队列
"""

import threading
import time
import uuid
import heapq
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from collections import deque


class 消息状态(Enum):
    """消息状态枚举"""
    待处理 = "待处理"
    处理中 = "处理中"
    已完成 = "已完成"
    失败 = "失败"
    已死信 = "已死信"


class 消息:
    """消息对象"""
    
    def __init__(self, 内容: Any, 消息标识: Optional[str] = None, 优先级: int = 0, 延迟: float = 0.0):
        self.内容 = 内容
        self.消息标识 = 消息标识 or str(uuid.uuid4())
        self.优先级 = 优先级
        self.延迟 = 延迟
        self.创建时间 = time.time()
        self.可执行时间 = self.创建时间 + 延迟
        self.状态 = 消息状态.待处理
        self.重试次数 = 0
        self.最大重试次数 = 3
    
    def __lt__(self, 其他: "消息") -> bool:
        if self.可执行时间 != 其他.可执行时间:
            return self.可执行时间 < 其他.可执行时间
        return self.优先级 > 其他.优先级
    
    def __repr__(self):
        return f"消息(标识={self.消息标识[:8]}...,内容={self.内容},状态={self.状态.value})"


class 内存消息队列:
    """内存消息队列"""
    
    def __init__(self, 名称: str = "默认队列", 最大容量: int = 10000):
        self.名称 = 名称
        self.最大容量 = 最大容量
        self._队列 = deque()
        self._延迟队列 = []
        self._死信队列 = deque()
        self._锁 = threading.Lock()
        self._条件变量 = threading.Condition(self._锁)
        self._消费者 = []
        self._运行中 = True
        self._已发送计数 = 0
        self._已接收计数 = 0
        self._已确认计数 = 0
    
    def 发送(self, 内容: Any, 优先级: int = 0, 延迟: float = 0.0) -> str:
        """
        发送消息
        
        参数:
            内容: 消息内容
            优先级: 优先级（越大越优先）
            延迟: 延迟时间（秒）
            
        返回:
            消息标识
        """
        msg = 消息(内容, 优先级=优先级, 延迟=延迟)
        
        with self._条件变量:
            while len(self._队列) >= self.最大容量:
                self._条件变量.wait()
            
            if 延迟 > 0:
                heapq.heappush(self._延迟队列, msg)
            else:
                self._队列.append(msg)
            
            self._已发送计数 += 1
            self._条件变量.notify_all()
        
        return msg.消息标识
    
    def 接收(self, 超时: float = None) -> Optional[消息]:
        """
        接收消息
        
        参数:
            超时: 超时时间（秒），None表示无限等待
            
        返回:
            消息对象，超时返回None
        """
        开始时间 = time.time()
        
        with self._条件变量:
            while True:
                self._检查延迟队列()
                
                if self._队列:
                    msg = self._队列.popleft()
                    msg.状态 = 消息状态.处理中
                    self._已接收计数 += 1
                    self._条件变量.notify_all()
                    return msg
                
                if not self._运行中:
                    return None
                
                if 超时 is not None:
                    剩余时间 = 超时 - (time.time() - 开始时间)
                    if 剩余时间 <= 0:
                        return None
                    self._条件变量.wait(timeout=剩余时间)
                else:
                    self._条件变量.wait()
    
    def _检查延迟队列(self):
        """检查延迟队列，将到期的消息移入主队列"""
        现在 = time.time()
        while self._延迟队列:
            最早消息 = self._延迟队列[0]
            if 最早消息.可执行时间 <= 现在:
                heapq.heappop(self._延迟队列)
                最早消息.可执行时间 = 最早消息.创建时间
                self._队列.appendleft(最早消息)
            else:
                break
    
    def 确认(self, 消息标识: str, 成功: bool = True):
        """
        确认消息处理结果
        
        参数:
            消息标识: 消息标识
            成功: 是否处理成功
        """
        with self._锁:
            if 成功:
                self._已确认计数 += 1
            else:
                pass
    
    def 失败(self, 消息: 消息):
        """
        标记消息处理失败，重试或进入死信队列
        
        参数:
            消息: 消息对象
        """
        with self._条件变量:
            消息.重试次数 += 1
            
            if 消息.重试次数 >= 消息.最大重试次数:
                消息.状态 = 消息状态.已死信
                self._死信队列.append(消息)
            else:
                消息.状态 = 消息状态.待处理
                消息.延迟 = min(2 ** 消息.重试次数 * 0.1, 10.0)
                消息.可执行时间 = time.time() + 消息.延迟
                heapq.heappush(self._延迟队列, 消息)
            
            self._条件变量.notify_all()
    
    def 大小(self) -> int:
        """获取队列大小"""
        with self._锁:
            return len(self._队列) + len(self._延迟队列)
    
    def 死信队列大小(self) -> int:
        """获取死信队列大小"""
        with self._锁:
            return len(self._死信队列)
    
    def 获取统计(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._锁:
            return {
                "已发送": self._已发送计数,
                "已接收": self._已接收计数,
                "已确认": self._已确认计数,
                "待处理": len(self._队列),
                "延迟中": len(self._延迟队列),
                "死信": len(self._死信队列)
            }
    
    def 清空(self):
        """清空队列"""
        with self._条件变量:
            self._队列.clear()
            self._延迟队列.clear()
            self._条件变量.notify_all()
    
    def 关闭(self):
        """关闭队列"""
        with self._条件变量:
            self._运行中 = False
            self._条件变量.notify_all()
    
    def __len__(self):
        return self.大小()


class 发布订阅:
    """发布订阅模式"""
    
    def __init__(self):
        self._主题订阅者 = {}
        self._锁 = threading.Lock()
    
    def 订阅(self, 主题: str, 回调: Callable) -> str:
        """
        订阅主题
        
        参数:
            主题: 主题名称
            回调: 消息回调函数
            
        返回:
            订阅标识
        """
        订阅标识 = str(uuid.uuid4())
        
        with self._锁:
            if 主题 not in self._主题订阅者:
                self._主题订阅者[主题] = {}
            self._主题订阅者[主题][订阅标识] = 回调
        
        return 订阅标识
    
    def 取消订阅(self, 主题: str, 订阅标识: str) -> bool:
        """
        取消订阅
        
        参数:
            主题: 主题名称
            订阅标识: 订阅标识
            
        返回:
            是否成功
        """
        with self._锁:
            if 主题 in self._主题订阅者 and 订阅标识 in self._主题订阅者[主题]:
                del self._主题订阅者[主题][订阅标识]
                if not self._主题订阅者[主题]:
                    del self._主题订阅者[主题]
                return True
            return False
    
    def 发布(self, 主题: str, 消息: Any) -> int:
        """
        发布消息
        
        参数:
            主题: 主题名称
            消息: 消息内容
            
        返回:
            接收消息的订阅者数量
        """
        with self._锁:
            订阅者 = list(self._主题订阅者.get(主题, {}).values())
        
        for 回调 in 订阅者:
            try:
                回调(消息)
            except Exception:
                pass
        
        return len(订阅者)
    
    def 获取主题列表(self) -> List[str]:
        """获取所有主题"""
        with self._锁:
            return list(self._主题订阅者.keys())
    
    def 获取订阅者数量(self, 主题: str) -> int:
        """获取指定主题的订阅者数量"""
        with self._锁:
            return len(self._主题订阅者.get(主题, {}))


class 工作队列:
    """工作队列（带消费者线程池）"""
    
    def __init__(self, 名称: str = "工作队列", 工作线程数: int = 4, 最大容量: int = 10000):
        self.名称 = 名称
        self.工作线程数 = 工作线程数
        self._队列 = 内存消息队列(名称, 最大容量)
        self._工作线程 = []
        self._运行中 = False
        self._处理函数 = None
        self._错误处理函数 = None
    
    def 启动(self, 处理函数: Callable, 错误处理函数: Optional[Callable] = None):
        """
        启动工作队列
        
        参数:
            处理函数: 消息处理函数
            错误处理函数: 错误处理函数
        """
        if self._运行中:
            return
        
        self._处理函数 = 处理函数
        self._错误处理函数 = 错误处理函数
        self._运行中 = True
        
        for i in range(self.工作线程数):
            t = threading.Thread(target=self._工作循环, name=f"工作线程_{i}", daemon=True)
            self._工作线程.append(t)
            t.start()
    
    def _工作循环(self):
        """工作线程循环"""
        while self._运行中:
            try:
                msg = self._队列.接收(超时=0.5)
                if msg is None:
                    continue
                
                try:
                    结果 = self._处理函数(msg.内容)
                    self._队列.确认(msg.消息标识, True)
                except Exception as e:
                    if self._错误处理函数:
                        try:
                            self._错误处理函数(msg.内容, e)
                        except Exception:
                            pass
                    self._队列.失败(msg)
            except Exception:
                break
    
    def 提交(self, 任务: Any, 优先级: int = 0, 延迟: float = 0.0) -> str:
        """
        提交任务
        
        参数:
            任务: 任务内容
            优先级: 优先级
            延迟: 延迟时间
            
        返回:
            任务标识
        """
        return self._队列.发送(任务, 优先级, 延迟)
    
    def 等待完成(self, 超时: float = None) -> bool:
        """
        等待所有任务完成
        
        参数:
            超时: 超时时间
            
        返回:
            是否在超时前完成
        """
        开始时间 = time.time()
        
        while self._队列.大小() > 0:
            time.sleep(0.01)
            if 超时 is not None and time.time() - 开始时间 > 超时:
                return False
        
        return True
    
    def 停止(self):
        """停止工作队列"""
        self._运行中 = False
        for t in self._工作线程:
            t.join(timeout=2.0)
        self._工作线程.clear()
        self._队列.关闭()
    
    def 获取统计(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._队列.获取统计()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.停止()
        return False


def 创建消息队列(名称: str = "默认队列", 最大容量: int = 10000) -> 内存消息队列:
    """创建消息队列"""
    return 内存消息队列(名称, 最大容量)


def 创建工作队列(处理函数: Callable, 工作线程数: int = 4, 名称: str = "工作队列") -> 工作队列:
    """创建并启动工作队列"""
    wq = 工作队列(名称, 工作线程数)
    wq.启动(处理函数)
    return wq


def 创建发布订阅() -> 发布订阅:
    """创建发布订阅"""
    return 发布订阅()
