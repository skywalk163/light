"""
光明标准库 - 集合工具模块

封装 collections 模块，提供高级集合数据结构。
包括：默认字典、有序字典、计数器、双端队列、命名元组等。
"""

import collections
from typing import Any, List, Dict, Tuple, Iterable


class 默认字典(collections.defaultdict):
    """默认字典（访问不存在的键时返回默认值）"""
    
    def __init__(self, 默认工厂=None, **kwargs):
        super().__init__(默认工厂, **kwargs)
    
    def 到普通字典(self) -> dict:
        """转换为普通字典"""
        return dict(self)


class 有序字典(collections.OrderedDict):
    """有序字典（保持插入顺序）"""
    
    def 移动到开头(self, 键, last=True):
        """移动元素到开头或末尾"""
        self.move_to_end(键, last=last)
    
    def 弹出末尾(self, last=True):
        """弹出末尾或开头的元素"""
        return self.popitem(last=last)
    
    def 到普通字典(self) -> dict:
        """转换为普通字典"""
        return dict(self)


class 计数器(collections.Counter):
    """计数器（统计元素出现次数）"""
    
    def 最常见(self, n=None):
        """获取最常见的n个元素"""
        return self.most_common(n)
    
    def 元素列表(self):
        """返回所有元素（按计数次重复）"""
        return list(self.elements())
    
    def 更新计数(self, 可迭代对象=None, **映射):
        """更新计数"""
        if 可迭代对象:
            self.update(可迭代对象)
        if 映射:
            self.update(映射)
    
    def 相减(self, 可迭代对象=None, **映射):
        """相减计数"""
        if 可迭代对象:
            self.subtract(可迭代对象)
        if 映射:
            self.subtract(映射)
    
    def 到字典(self) -> dict:
        """转换为普通字典"""
        return dict(self)


class 双端队列(collections.deque):
    """双端队列"""
    
    def 左入队(self, *元素):
        """从左侧添加元素"""
        self.appendleft(*元素)
    
    def 右入队(self, *元素):
        """从右侧添加元素"""
        self.extend(元素) if len(元素) > 1 else self.append(元素[0])
    
    def 左出队(self):
        """从左侧弹出元素"""
        return self.popleft()
    
    def 右出队(self):
        """从右侧弹出元素"""
        return self.pop()
    
    def 左扩展(self, 可迭代对象):
        """从左侧扩展"""
        self.extendleft(可迭代对象)
    
    def 右扩展(self, 可迭代对象):
        """从右侧扩展"""
        self.extend(可迭代对象)
    
    def 旋转(self, n=1):
        """旋转队列"""
        self.rotate(n)
    
    def 转为列表(self) -> list:
        """转换为列表"""
        return list(self)


def 创建默认字典(默认工厂=None, **kwargs) -> 默认字典:
    """创建默认字典"""
    return 默认字典(默认工厂, **kwargs)


def 创建有序字典(数据=None) -> 有序字典:
    """创建有序字典"""
    if 数据:
        return 有序字典(数据)
    return 有序字典()


def 创建计数器(可迭代对象=None) -> 计数器:
    """创建计数器"""
    if 可迭代对象:
        return 计数器(可迭代对象)
    return 计数器()


def 创建双端队列(可迭代对象=None, 最大长度=None) -> 双端队列:
    """创建双端队列"""
    if 可迭代对象:
        return 双端队列(可迭代对象, maxlen=最大长度)
    return 双端队列(maxlen=最大长度)


def 命名元组(类型名: str, 字段名列表: list):
    """
    创建命名元组类型
    
    参数:
        类型名: 类型名称
        字段名列表: 字段名列表
    
    返回:
        命名元组类
    """
    return collections.namedtuple(类型名, 字段名列表)


def 链字典(*映射列表):
    """
    链字典（ChainMap）
    
    将多个字典链接为一个视图
    """
    return collections.ChainMap(*映射列表)


def 用户字典():
    """创建UserDict（可自定义字典行为）"""
    return collections.UserDict


def 用户列表():
    """创建UserList（可自定义列表行为）"""
    return collections.UserList


def 用户字符串():
    """创建UserString（可自定义字符串行为）"""
    return collections.UserString


def 统计频率(可迭代对象: Iterable[Any]) -> Dict[Any, int]:
    """统计频率（返回普通字典）"""
    return dict(collections.Counter(可迭代对象))


def 可迭代对象(可迭代对象: Iterable[Any], n: int = 2) -> List[Tuple[Any, ...]]:
    """
    滑动窗口n-gram"""
    from collections import deque
    d = deque(maxlen=n)
    result = []
    for item in 可迭代对象:
        d.append(item)
        if len(d) == n:
            result.append(tuple(d))
    return result


__all__ = [
    '默认字典', '有序字典', '计数器', '双端队列',
    '创建默认字典', '创建有序字典', '创建计数器', '创建双端队列',
    '命名元组', '链字典',
    '用户字典', '用户列表', '用户字符串',
    '统计频率', '可迭代对象',
]
