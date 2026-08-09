"""
光明标准库 - 工作流引擎模块

提供DAG工作流编排支持，包括：
- DAG工作流定义
- 任务节点
- 依赖管理
- 并行执行
- 条件分支
- 工作流执行与状态追踪
"""

import threading
import time
import uuid
from typing import Callable, Any, Optional, Dict, List, Set
from enum import Enum
from collections import deque


class 节点状态(Enum):
    """节点状态枚举"""
    待执行 = "待执行"
    执行中 = "执行中"
    已完成 = "已完成"
    失败 = "失败"
    已跳过 = "已跳过"
    已取消 = "已取消"


class 工作流状态(Enum):
    """工作流状态枚举"""
    待运行 = "待运行"
    运行中 = "运行中"
    已完成 = "已完成"
    失败 = "失败"
    已取消 = "已取消"


class 工作流节点:
    """工作流节点"""
    
    def __init__(self, 名称: str, 函数: Optional[Callable] = None, 描述: str = ""):
        self.名称 = 名称
        self.函数 = 函数
        self.描述 = 描述
        self.状态 = 节点状态.待执行
        self.结果 = None
        self.异常 = None
        self.依赖 = []
        self.下游节点 = []
        self.开始时间 = None
        self.结束时间 = None
        self.重试次数 = 0
        self.最大重试次数 = 0
        self.条件函数 = None
    
    def 添加依赖(self, *节点: "工作流节点"):
        """添加依赖节点"""
        for n in 节点:
            if n not in self.依赖:
                self.依赖.append(n)
                if self not in n.下游节点:
                    n.下游节点.append(self)
    
    def 设置条件(self, 条件函数: Callable):
        """设置执行条件函数"""
        self.条件函数 = 条件函数
    
    def 可执行(self, 上下文: Dict[str, Any]) -> bool:
        """检查是否可执行"""
        for 依赖节点 in self.依赖:
            if 依赖节点.状态 != 节点状态.已完成 and 依赖节点.状态 != 节点状态.已跳过:
                return False
        return True
    
    def 应执行(self, 上下文: Dict[str, Any]) -> bool:
        """检查是否应该执行（条件判断）"""
        if self.条件函数:
            try:
                return bool(self.条件函数(上下文))
            except Exception:
                return False
        return True
    
    def 执行(self, 上下文: Dict[str, Any]) -> Any:
        """执行节点"""
        self.状态 = 节点状态.执行中
        self.开始时间 = time.time()
        
        try:
            if self.函数:
                self.结果 = self.函数(上下文)
            self.状态 = 节点状态.已完成
            上下文[self.名称] = self.结果
        except Exception as e:
            self.异常 = e
            if self.重试次数 < self.最大重试次数:
                self.重试次数 += 1
                self.状态 = 节点状态.待执行
                raise
            self.状态 = 节点状态.失败
            raise
        finally:
            self.结束时间 = time.time()
        
        return self.结果
    
    def 耗时(self) -> Optional[float]:
        """获取执行耗时"""
        if self.开始时间 and self.结束时间:
            return self.结束时间 - self.开始时间
        return None
    
    def __repr__(self):
        return f"工作流节点(名称={self.名称},状态={self.状态.value})"


class 工作流:
    """DAG工作流"""
    
    def __init__(self, 名称: str = "工作流", 描述: str = ""):
        self.名称 = 名称
        self.描述 = 描述
        self.工作流标识 = str(uuid.uuid4())
        self._节点 = {}
        self._上下文 = {}
        self.状态 = 工作流状态.待运行
        self.开始时间 = None
        self.结束时间 = None
        self._锁 = threading.Lock()
        self._条件变量 = threading.Condition(self._锁)
        self._运行线程 = None
        self._执行线程数 = 4
    
    def 添加节点(self, 节点: 工作流节点) -> 工作流节点:
        """添加节点"""
        if 节点.名称 in self._节点:
            raise ValueError(f"节点 {节点.名称} 已存在")
        self._节点[节点.名称] = 节点
        return 节点
    
    def 创建节点(self, 名称: str, 函数: Optional[Callable] = None, 描述: str = "", 
                 依赖: Optional[List[str]] = None) -> 工作流节点:
        """创建并添加节点"""
        节点 = 工作流节点(名称, 函数, 描述)
        
        if 依赖:
            for 依赖名 in 依赖:
                if 依赖名 in self._节点:
                    节点.添加依赖(self._节点[依赖名])
                else:
                    raise ValueError(f"依赖节点 {依赖名} 不存在")
        
        return self.添加节点(节点)
    
    def 添加依赖(self, 节点名称: str, *依赖名称: str):
        """添加节点依赖"""
        if 节点名称 not in self._节点:
            raise ValueError(f"节点 {节点名称} 不存在")
        
        节点 = self._节点[节点名称]
        for 依赖名 in 依赖名称:
            if 依赖名 not in self._节点:
                raise ValueError(f"依赖节点 {依赖名} 不存在")
            节点.添加依赖(self._节点[依赖名])
    
    def 验证(self) -> bool:
        """验证工作流（检查环）"""
        访问状态 = {}
        
        def DFS(节点名称: str) -> bool:
            访问状态[节点名称] = 1
            节点 = self._节点[节点名称]
            
            for 下游 in 节点.下游节点:
                if 下游.名称 not in 访问状态:
                    if not DFS(下游.名称):
                        return False
                elif 访问状态[下游.名称] == 1:
                    return False
            
            访问状态[节点名称] = 2
            return True
        
        for 名称 in self._节点:
            if 名称 not in 访问状态:
                if not DFS(名称):
                    return False
        
        return True
    
    def 获取入度节点(self) -> List[str]:
        """获取入度为0的节点"""
        入度 = {名称: len(节点.依赖) for 名称, 节点 in self._节点.items()}
        return [名称 for 名称, 度 in 入度.items() if 度 == 0]
    
    def 拓扑排序(self) -> List[str]:
        """拓扑排序"""
        入度 = {名称: len(节点.依赖) for 名称, 节点 in self._节点.items()}
        队列 = deque([名称 for 名称, 度 in 入度.items() if 度 == 0])
        结果 = []
        
        while 队列:
            节点名称 = 队列.popleft()
            结果.append(节点名称)
            
            for 下游 in self._节点[节点名称].下游节点:
                入度[下游.名称] -= 1
                if 入度[下游.名称] == 0:
                    队列.append(下游.名称)
        
        if len(结果) != len(self._节点):
            raise ValueError("工作流中存在环")
        
        return 结果
    
    def 执行(self, 初始上下文: Optional[Dict] = None) -> Dict:
        """执行工作流"""
        if self.状态 == 工作流状态.运行中:
            raise RuntimeError("工作流正在运行")
        
        if not self.验证():
            raise ValueError("工作流验证失败，可能存在环")
        
        self.状态 = 工作流状态.运行中
        self.开始时间 = time.time()
        self._上下文 = 初始上下文.copy() if 初始上下文 else {}
        
        for 节点 in self._节点.values():
            节点.状态 = 节点状态.待执行
            节点.结果 = None
            节点.异常 = None
            节点.开始时间 = None
            节点.结束时间 = None
        
        try:
            self._并行执行()
            self.状态 = 工作流状态.已完成
        except Exception:
            self.状态 = 工作流状态.失败
            raise
        finally:
            self.结束时间 = time.time()
        
        return self._上下文
    
    def _并行执行(self):
        """并行执行工作流"""
        线程池 = []
        完成事件 = threading.Event()
        错误 = [None]
        
        def 执行节点(节点: 工作流节点):
            try:
                while True:
                    with self._锁:
                        if not 节点.可执行(self._上下文):
                            time.sleep(0.01)
                            continue
                        
                        if 节点.状态 != 节点状态.待执行:
                            return
                        
                        if 节点.应执行(self._上下文):
                            节点.状态 = 节点状态.执行中
                        else:
                            节点.状态 = 节点状态.已跳过
                            return
                    
                    try:
                        节点.执行(self._上下文)
                    except Exception as e:
                        if 节点.状态 != 节点状态.待执行:
                            raise
                    return
            except Exception as e:
                错误[0] = e
                完成事件.set()
        
        def 工作线程():
            while not 完成事件.is_set():
                with self._锁:
                    待执行节点 = None
                    for 节点 in self._节点.values():
                        if 节点.状态 == 节点状态.待执行 and 节点.可执行(self._上下文):
                            待执行节点 = 节点
                            break
                    
                    if 待执行节点:
                        if 待执行节点.应执行(self._上下文):
                            待执行节点.状态 = 节点状态.执行中
                        else:
                            待执行节点.状态 = 节点状态.已跳过
                            continue
                
                if 待执行节点:
                    try:
                        待执行节点.执行(self._上下文)
                    except Exception as e:
                        pass
                
                with self._锁:
                    全部完成 = all(
                        n.状态 in (节点状态.已完成, 节点状态.失败, 节点状态.已跳过)
                        for n in self._节点.values()
                    )
                    if 全部完成:
                        完成事件.set()
        
        for i in range(self._执行线程数):
            t = threading.Thread(target=工作线程, daemon=True)
            线程池.append(t)
            t.start()
        
        完成事件.wait()
        
        for t in 线程池:
            t.join(timeout=1.0)
        
        失败节点 = [n for n in self._节点.values() if n.状态 == 节点状态.失败]
        if 失败节点:
            raise RuntimeError(f"工作流执行失败，失败节点: {[n.名称 for n in 失败节点]}")
    
    def 异步执行(self, 初始上下文: Optional[Dict] = None) -> str:
        """异步执行工作流"""
        def 运行():
            try:
                self.执行(初始上下文)
            except Exception:
                pass
        
        self._运行线程 = threading.Thread(target=运行, daemon=True)
        self._运行线程.start()
        return self.工作流标识
    
    def 等待完成(self, 超时: float = None) -> bool:
        """等待工作流完成"""
        开始时间 = time.time()
        
        while self.状态 == 工作流状态.运行中:
            time.sleep(0.01)
            if 超时 is not None and time.time() - 开始时间 > 超时:
                return False
        
        return self.状态 in (工作流状态.已完成, 工作流状态.失败)
    
    def 获取节点状态(self, 节点名称: str) -> Optional[节点状态]:
        """获取节点状态"""
        节点 = self._节点.get(节点名称)
        if 节点:
            return 节点.状态
        return None
    
    def 获取节点结果(self, 节点名称: str) -> Any:
        """获取节点结果"""
        节点 = self._节点.get(节点名称)
        if 节点:
            return 节点.结果
        return None
    
    def 获取统计(self) -> Dict:
        """获取执行统计"""
        统计 = {
            "工作流": self.名称,
            "状态": self.状态.value,
            "总节点数": len(self._节点),
            "已完成": 0,
            "执行中": 0,
            "待执行": 0,
            "失败": 0,
            "已跳过": 0
        }
        
        for 节点 in self._节点.values():
            if 节点.状态 == 节点状态.已完成:
                统计["已完成"] += 1
            elif 节点.状态 == 节点状态.执行中:
                统计["执行中"] += 1
            elif 节点.状态 == 节点状态.待执行:
                统计["待执行"] += 1
            elif 节点.状态 == 节点状态.失败:
                统计["失败"] += 1
            elif 节点.状态 == 节点状态.已跳过:
                统计["已跳过"] += 1
        
        if self.开始时间:
            统计["开始时间"] = self.开始时间
            if self.结束时间:
                统计["总耗时"] = self.结束时间 - self.开始时间
            else:
                统计["已耗时"] = time.time() - self.开始时间
        
        return 统计
    
    def __repr__(self):
        return f"工作流(名称={self.名称},状态={self.状态.value},节点数={len(self._节点)})"


class 工作流构建器:
    """工作流构建器"""
    
    def __init__(self, 名称: str = "工作流"):
        self._工作流 = 工作流(名称)
    
    def 节点(self, 名称: str, 函数: Callable = None, 描述: str = "", 依赖: List[str] = None):
        """添加节点"""
        self._工作流.创建节点(名称, 函数, 描述, 依赖)
        return self
    
    def 构建(self) -> 工作流:
        """构建工作流"""
        return self._工作流


def 创建工作流(名称: str = "工作流") -> 工作流:
    """创建工作流"""
    return 工作流(名称)


def 创建工作流构建器(名称: str = "工作流") -> 工作流构建器:
    """创建工作流构建器"""
    return 工作流构建器(名称)


def 顺序执行(函数列表: List[Callable], 初始上下文: Optional[Dict] = None) -> Dict:
    """顺序执行函数列表"""
    wf = 工作流("顺序执行")
    
    上一个节点 = None
    for i, func in enumerate(函数列表):
        节点名称 = f"步骤_{i}"
        节点 = wf.创建节点(节点名称, lambda ctx, f=func: f(ctx))
        if 上一个节点:
            节点.添加依赖(上一个节点)
        上一个节点 = 节点
    
    return wf.执行(初始上下文)
