"""
光明标准库 - Actor模型模块

提供Actor模型并发编程支持，包括：
- Actor基类与消息处理
- Actor系统管理
- Actor引用与消息传递
- 监督策略
- 邮箱与调度
"""

import threading
import queue
import uuid
import time
from typing import Callable, Any, Optional, Dict, List, Union
from enum import Enum


class 消息类型(Enum):
    """消息类型枚举"""
    普通 = "普通"
    系统 = "系统"
    错误 = "错误"
    回复 = "回复"


class 监督策略(Enum):
    """监督策略枚举"""
    重启 = "重启"
    停止 = "停止"
    继续 = "继续"
    升级 = "升级"


class 消息:
    """Actor消息"""
    
    def __init__(self, 类型: 消息类型 = 消息类型.普通, 内容: Any = None, 发送者: Optional[str] = None, 消息标识: Optional[str] = None):
        self.类型 = 类型
        self.内容 = 内容
        self.发送者 = 发送者
        self.消息标识 = 消息标识 or str(uuid.uuid4())
        self.时间戳 = time.time()
    
    def __repr__(self):
        return f"消息(类型={self.类型.value},内容={self.内容},发送者={self.发送者})"


class Actor引用:
    """Actor引用，用于向Actor发送消息"""
    
    def __init__(self, actor: "Actor", 系统: "Actor系统"):
        self._actor = actor
        self._系统 = 系统
        self.路径 = actor.路径
        self.名称 = actor.名称
    
    def 发送(self, 消息内容: Any, 发送者: Optional["Actor引用"] = None) -> str:
        """向Actor发送消息"""
        发送者路径 = 发送者.路径 if 发送者 else None
        msg = 消息(类型=消息类型.普通, 内容=消息内容, 发送者=发送者路径)
        self._actor.接收消息(msg)
        return msg.消息标识
    
    def 请求(self, 消息内容: Any, 超时: float = 5.0) -> Any:
        """同步请求-回复模式"""
        结果队列 = queue.Queue()
        消息标识 = str(uuid.uuid4())
        
        def 回复处理器(消息):
            结果队列.put(消息.内容)
        
        self._系统._注册临时回复处理器(消息标识, 回复处理器)
        
        msg = 消息(类型=消息类型.普通, 内容=消息内容, 发送者=f"临时:{消息标识}", 消息标识=消息标识)
        self._actor.接收消息(msg)
        
        try:
            return 结果队列.get(timeout=超时)
        except queue.Empty:
            raise TimeoutError(f"请求超时: {超时}秒")
    
    def 停止(self):
        """停止Actor"""
        msg = 消息(类型=消息类型.系统, 内容="停止")
        self._actor.接收消息(msg)
    
    def __repr__(self):
        return f"Actor引用(路径={self.路径})"


class Actor:
    """Actor基类"""
    
    def __init__(self, 名称: str = None):
        self.名称 = 名称 or f"Actor_{uuid.uuid4().hex[:8]}"
        self.路径 = self.名称
        self._邮箱 = queue.Queue()
        self._线程 = None
        self._运行中 = False
        self._系统 = None
        self._父Actor = None
        self._子Actor = {}
        self._监督策略 = 监督策略.重启
        self._重启次数 = 0
        self._最大重启次数 = 10
        self._重启窗口 = 60.0
        self._重启时间记录 = []
        self._接收处理器 = {}
        self._锁 = threading.Lock()
    
    def 接收消息(self, 消息: 消息):
        """接收消息（放入邮箱）"""
        self._邮箱.put(消息)
    
    def _运行(self):
        """Actor主循环"""
        self._运行中 = True
        self._启动前()
        try:
            while self._运行中:
                try:
                    msg = self._邮箱.get(timeout=0.1)
                    self._处理消息(msg)
                except queue.Empty:
                    continue
                except Exception as e:
                    self._处理错误(e)
        finally:
            self._停止后()
            self._运行中 = False
    
    def _启动前(self):
        """Actor启动前钩子"""
        pass
    
    def _停止后(self):
        """Actor停止后钩子"""
        pass
    
    def _处理消息(self, msg: 消息):
        """处理消息"""
        if msg.类型 == 消息类型.系统:
            if msg.内容 == "停止":
                self._运行中 = False
                return
        
        if msg.发送者 and msg.发送者.startswith("临时:"):
            消息标识 = msg.发送者.split(":", 1)[1]
            结果 = self.处理(msg.内容)
            self._系统._触发临时回复(消息标识, 消息(类型=消息类型.回复, 内容=结果))
        else:
            self.处理(msg.内容)
    
    def 处理(self, 消息: Any) -> Any:
        """
        消息处理方法，子类应重写此方法"""
        pass
    
    def _处理错误(self, 异常: Exception):
        """处理错误"""
        if self._父Actor:
            self._父Actor._子Actor错误(self, 异常)
        else:
            print(f"Actor {self.路径} 错误: {异常}")
    
    def _子Actor错误(self, 子Actor: "Actor", 异常: Exception):
        """子Actor错误处理"""
        if self._监督策略 == 监督策略.重启:
            self._重启子Actor(子Actor)
        elif self._监督策略 == 监督策略.停止:
            子Actor.停止()
        elif self._监督策略 == 监督策略.继续:
            pass
    
    def _重启子Actor(self, 子Actor: "Actor"):
        """重启子Actor"""
        现在 = time.time()
        self._重启时间记录 = [t for t in self._重启时间记录 if 现在 - t < self._重启窗口]
        
        if len(self._重启时间记录) >= self._最大重启次数:
            print(f"Actor {子Actor.路径} 重启次数超限，停止")
            子Actor.停止()
            return
        
        self._重启时间记录.append(现在)
        子Actor.停止()
        子Actor._等待停止()
        
        新Actor = type(子Actor)(子Actor.名称.split("/")[-1])
        self._子Actor[子Actor.名称] = 新Actor
        新Actor.路径 = 子Actor.路径
        新Actor._系统 = self._系统
        新Actor._父Actor = self
        新Actor._启动()
    
    def 创建子Actor(self, actor_class, 名称: str = None) -> Actor引用:
        """创建子Actor"""
        名称 = 名称 or f"子Actor_{uuid.uuid4().hex[:8]}"
        子Actor = actor_class(名称)
        子Actor.路径 = f"{self.路径}/{名称}"
        子Actor._系统 = self._系统
        子Actor._父Actor = self
        self._子Actor[名称] = 子Actor
        子Actor._启动()
        return Actor引用(子Actor, self._系统)
    
    def _启动(self):
        """启动Actor"""
        if not self._运行中:
            self._线程 = threading.Thread(target=self._运行, daemon=True)
            self._线程.start()
    
    def _等待停止(self):
        """等待Actor停止"""
        if self._线程:
            self._线程.join(timeout=5.0)
    
    def 停止(self):
        """停止Actor"""
        msg = 消息(类型=消息类型.系统, 内容="停止")
        self.接收消息(msg)
    
    def 设置监督策略(self, 策略: 监督策略):
        """设置监督策略"""
        self._监督策略 = 策略
    
    def 获取子Actor(self, 名称: str) -> Optional[Actor引用]:
        """获取子Actor引用"""
        子Actor = self._子Actor.get(名称)
        if 子Actor:
            return Actor引用(子Actor, self._系统)
        return None


class Actor系统:
    """Actor系统"""
    
    def __init__(self, 名称: str = "Actor系统"):
        self.名称 = 名称
        self._Actors = {}
        self._临时回复处理器 = {}
        self._锁 = threading.Lock()
        self._运行中 = True
    
    def 创建Actor(self, actor_class, 名称: str = None) -> Actor引用:
        """创建顶级Actor"""
        名称 = 名称 or f"Actor_{uuid.uuid4().hex[:8]}"
        if 名称 in self._Actors:
            raise ValueError(f"Actor {名称} 已存在")
        
        actor = actor_class(名称)
        actor.路径 = f"/user/{名称}"
        actor._系统 = self
        self._Actors[名称] = actor
        actor._启动()
        return Actor引用(actor, self)
    
    def 获取Actor(self, 路径: str) -> Optional[Actor引用]:
        """根据路径获取Actor引用"""
        if 路径.startswith("/user/"):
            名称 = 路径[len("/user/"):]
            actor = self._Actors.get(名称)
            if actor:
                return Actor引用(actor, self)
        return None
    
    def 停止Actor(self, 名称: str):
        """停止Actor"""
        actor = self._Actors.get(名称)
        if actor:
            actor.停止()
            actor._等待停止()
            del self._Actors[名称]
    
    def _注册临时回复处理器(self, 消息标识: str, 处理器: Callable):
        """注册临时回复处理器"""
        with self._锁:
            self._临时回复处理器[消息标识] = 处理器
    
    def _触发临时回复(self, 消息标识: str, 消息: 消息):
        """触发临时回复"""
        with self._锁:
            处理器 = self._临时回复处理器.pop(消息标识, None)
        if 处理器:
            处理器(消息)
    
    def 关闭(self):
        """关闭Actor系统"""
        self._运行中 = False
        for 名称, actor in list(self._Actors.items()):
            actor.停止()
            actor._等待停止()
        self._Actors.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.关闭()


class 简单Actor(Actor):
    """简单Actor，可自定义处理函数"""
    
    def __init__(self, 处理函数: Callable, 名称: str = None):
        super().__init__(名称)
        self._处理函数 = 处理函数
    
    def 处理(self, 消息: Any) -> Any:
        return self._处理函数(消息)


def 创建Actor系统(名称: str = "Actor系统") -> Actor系统:
    """创建Actor系统"""
    return Actor系统(名称)


def 创建简单Actor(系统: Actor系统, 处理函数: Callable, 名称: str = None) -> Actor引用:
    """创建简单Actor"""
    return 系统.创建Actor(lambda n=名称: 简单Actor(处理函数, n), 名称)
