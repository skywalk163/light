"""
对象池与缓存模块 - 复用对象、LRU缓存

提供对象池和缓存功能，包括：
- 对象池模式
- LRU缓存
- 简单缓存
- 内存缓存
- 缓存装饰器
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict
import time


class 对象池:
    """通用对象池"""
    
    def __init__(self, 创建函数: Callable, 最大大小: int = 10, 
                 初始化数量: int = 0, 销毁函数: Callable = None):
        self._创建函数 = 创建函数
        self._最大大小 = 最大大小
        self._销毁函数 = 销毁函数
        self._可用对象: List[Any] = []
        self._已使用对象: List[Any] = []
        
        for _ in range(min(初始化数量, 最大大小)):
            self._可用对象.append(self._创建函数())
    
    def 获取(self) -> Any:
        """获取对象"""
        if self._可用对象:
            对象 = self._可用对象.pop()
        else:
            对象 = self._创建函数()
        
        self._已使用对象.append(对象)
        return 对象
    
    def 释放(self, 对象: Any):
        """释放对象"""
        if 对象 in self._已使用对象:
            self._已使用对象.remove(对象)
        
        if len(self._可用对象) < self._最大大小:
            self._可用对象.append(对象)
        elif self._销毁函数:
            self._销毁函数(对象)
    
    def 清理(self):
        """清理所有对象"""
        if self._销毁函数:
            for 对象 in self._可用对象:
                self._销毁函数(对象)
            for 对象 in self._已使用对象:
                self._销毁函数(对象)
        
        self._可用对象 = []
        self._已使用对象 = []
    
    def 可用数量(self) -> int:
        """获取可用对象数量"""
        return len(self._可用对象)
    
    def 已用数量(self) -> int:
        """获取已使用对象数量"""
        return len(self._已使用对象)
    
    def 总数量(self) -> int:
        """获取总对象数量"""
        return len(self._可用对象) + len(self._已使用对象)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.清理()


class 对象上下文:
    """对象池上下文管理器"""
    
    def __init__(self, 池: 对象池):
        self._池 = 池
        self._对象 = None
    
    def __enter__(self):
        self._对象 = self._池.获取()
        return self._对象
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._对象:
            self._池.释放(self._对象)


def 对象上下文管理器(池: 对象池) -> 对象上下文:
    """创建对象上下文管理器"""
    return 对象上下文(池)


class LRU缓存:
    """LRU缓存"""
    
    def __init__(self, 最大容量: int = 128):
        self._最大容量 = 最大容量
        self._缓存: OrderedDict = OrderedDict()
        self._命中计数 = 0
        self._未命中计数 = 0
    
    def 获取(self, 键: Any, 默认值: Any = None) -> Any:
        """获取缓存值"""
        if 键 in self._缓存:
            self._命中计数 += 1
            值 = self._缓存.pop(键)
            self._缓存[键] = 值
            return 值
        self._未命中计数 += 1
        return 默认值
    
    def 设置(self, 键: Any, 值: Any):
        """设置缓存值"""
        if 键 in self._缓存:
            self._缓存.pop(键)
        elif len(self._缓存) >= self._最大容量:
            self._缓存.popitem(last=False)
        
        self._缓存[键] = 值
    
    def 删除(self, 键: Any) -> bool:
        """删除缓存项"""
        if 键 in self._缓存:
            del self._缓存[键]
            return True
        return False
    
    def 包含(self, 键: Any) -> bool:
        """检查是否包含键"""
        return 键 in self._缓存
    
    def 清空(self):
        """清空缓存"""
        self._缓存.clear()
        self._命中计数 = 0
        self._未命中计数 = 0
    
    def 大小(self) -> int:
        """获取缓存大小"""
        return len(self._缓存)
    
    def 命中率(self) -> float:
        """获取命中率"""
        总次数 = self._命中计数 + self._未命中计数
        if 总次数 == 0:
            return 0.0
        return self._命中计数 / 总次数
    
    def 统计信息(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            '大小': self.大小(),
            '最大容量': self._最大容量,
            '命中数': self._命中计数,
            '未命中数': self._未命中计数,
            '命中率': self.命中率()
        }
    
    def keys(self) -> List[Any]:
        """获取所有键"""
        return list(self._缓存.keys())
    
    def values(self) -> List[Any]:
        """获取所有值"""
        return list(self._缓存.values())
    
    def items(self) -> List[Tuple[Any, Any]]:
        """获取所有键值对"""
        return list(self._缓存.items())


class 简单缓存:
    """简单缓存"""
    
    def __init__(self, 过期时间: float = None):
        self._缓存: Dict[Any, Tuple[Any, float]] = {}
        self._过期时间 = 过期时间
    
    def 获取(self, 键: Any, 默认值: Any = None) -> Any:
        """获取缓存值"""
        if 键 in self._缓存:
            值, 时间戳 = self._缓存[键]
            if self._过期时间 is None or time.monotonic() - 时间戳 < self._过期时间:
                return 值
            else:
                del self._缓存[键]
        return 默认值
    
    def 设置(self, 键: Any, 值: Any):
        """设置缓存值"""
        self._缓存[键] = (值, time.monotonic())
    
    def 删除(self, 键: Any) -> bool:
        """删除缓存项"""
        if 键 in self._缓存:
            del self._缓存[键]
            return True
        return False
    
    def 包含(self, 键: Any) -> bool:
        """检查是否包含键"""
        if 键 in self._缓存:
            _, 时间戳 = self._缓存[键]
            if self._过期时间 is None or time.time() - 时间戳 < self._过期时间:
                return True
            else:
                del self._缓存[键]
        return False
    
    def 清空(self):
        """清空缓存"""
        self._缓存.clear()
    
    def 清理过期(self):
        """清理过期项"""
        当前时间 = time.monotonic()
        过期键 = []
        for 键, (_, 时间戳) in self._缓存.items():
            if self._过期时间 and 当前时间 - 时间戳 > self._过期时间:
                过期键.append(键)
        for 键 in 过期键:
            del self._缓存[键]
    
    def 大小(self) -> int:
        """获取缓存大小"""
        self.清理过期()
        return len(self._缓存)


class 内存缓存:
    """多级内存缓存"""
    
    def __init__(self, 最大大小: int = 1000, 过期时间: float = None):
        self._LRU缓存 = LRU缓存(最大大小)
        self._简单缓存 = 简单缓存(过期时间)
    
    def 获取(self, 键: Any, 默认值: Any = None) -> Any:
        """获取缓存值"""
        值 = self._LRU缓存.获取(键)
        if 值 is not None:
            return 值
        
        值 = self._简单缓存.获取(键)
        if 值 is not None:
            self._LRU缓存.设置(键, 值)
            return 值
        
        return 默认值
    
    def 设置(self, 键: Any, 值: Any):
        """设置缓存值"""
        self._LRU缓存.设置(键, 值)
        self._简单缓存.设置(键, 值)
    
    def 删除(self, 键: Any) -> bool:
        """删除缓存项"""
        结果1 = self._LRU缓存.删除(键)
        结果2 = self._简单缓存.删除(键)
        return 结果1 or 结果2
    
    def 包含(self, 键: Any) -> bool:
        """检查是否包含键"""
        return self._LRU缓存.包含(键) or self._简单缓存.包含(键)
    
    def 清空(self):
        """清空缓存"""
        self._LRU缓存.清空()
        self._简单缓存.清空()
    
    def 大小(self) -> int:
        """获取缓存大小"""
        return self._LRU缓存.大小()


def 缓存装饰器(最大容量: int = 128):
    """缓存装饰器"""
    def 装饰器(函数):
        缓存 = LRU缓存(最大容量)
        
        def 包装(*参数):
            键 = 参数
            结果 = 缓存.获取(键)
            if 结果 is not None:
                return 结果
            结果 = 函数(*参数)
            缓存.设置(键, 结果)
            return 结果
        
        包装.缓存 = 缓存
        return 包装
    return 装饰器


def LRU缓存装饰器(最大容量: int = 128):
    """LRU缓存装饰器"""
    return 缓存装饰器(最大容量)


def 记忆化(函数):
    """记忆化装饰器"""
    缓存 = {}
    
    def 包装(*参数):
        if 参数 not in 缓存:
            缓存[参数] = 函数(*参数)
        return 缓存[参数]
    
    包装.缓存 = 缓存
    return 包装


class 定时缓存:
    """定时缓存"""
    
    def __init__(self, 刷新函数: Callable, 刷新间隔: float = 60):
        self._刷新函数 = 刷新函数
        self._刷新间隔 = 刷新间隔
        self._值 = None
        self._最后刷新时间 = 0
    
    def 获取(self) -> Any:
        """获取缓存值"""
        当前时间 = time.time()
        if 当前时间 - self._最后刷新时间 > self._刷新间隔:
            self._值 = self._刷新函数()
            self._最后刷新时间 = 当前时间
        return self._值
    
    def 刷新(self) -> Any:
        """手动刷新"""
        self._值 = self._刷新函数()
        self._最后刷新时间 = time.time()
        return self._值
    
    def 清除(self):
        """清除缓存"""
        self._值 = None
        self._最后刷新时间 = 0


class 二级缓存:
    """二级缓存（内存+磁盘）"""
    
    def __init__(self, 内存最大容量: int = 100, 缓存目录: str = None):
        self._内存缓存 = LRU缓存(内存最大容量)
        self._磁盘缓存路径 = 缓存目录
    
    def 获取(self, 键: Any, 默认值: Any = None) -> Any:
        """获取缓存值"""
        值 = self._内存缓存.获取(键)
        if 值 is not None:
            return 值
        return 默认值
    
    def 设置(self, 键: Any, 值: Any):
        """设置缓存值"""
        self._内存缓存.设置(键, 值)
    
    def 删除(self, 键: Any) -> bool:
        """删除缓存项"""
        return self._内存缓存.删除(键)
    
    def 清空(self):
        """清空缓存"""
        self._内存缓存.清空()
    
    def 大小(self) -> int:
        """获取缓存大小"""
        return self._内存缓存.大小()


# 便捷函数
def 创建对象池(创建函数: Callable, 最大大小: int = 10, 初始化数量: int = 0) -> 对象池:
    """创建对象池"""
    return 对象池(创建函数, 最大大小, 初始化数量)


def 创建LRU缓存(最大容量: int = 128) -> LRU缓存:
    """创建LRU缓存"""
    return LRU缓存(最大容量)


def 创建简单缓存(过期时间: float = None) -> 简单缓存:
    """创建简单缓存"""
    return 简单缓存(过期时间)


def 创建定时缓存(刷新函数: Callable, 刷新间隔: float = 60) -> 定时缓存:
    """创建定时缓存"""
    return 定时缓存(刷新函数, 刷新间隔)


# =============================================================================
# 合并自缓存.py的便捷函数
# =============================================================================

def 创建缓存() -> dict:
    """创建一个简单的字典缓存"""
    return {}


def 设置缓存(缓存: dict, 键, 值) -> None:
    """设置缓存值"""
    缓存[键] = 值


def 获取缓存(缓存: dict, 键, 默认值: Any = None):
    """获取缓存值"""
    return 缓存.get(键, 默认值)


def 清除缓存(缓存: dict) -> None:
    """清除所有缓存"""
    缓存.clear()