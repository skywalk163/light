"""
光明标准库 - 函数工具模块

封装 functools 模块，提供函数式编程工具。
包括：偏函数、缓存、reduce、wraps 等。
"""

import functools
from typing import Callable, Any, Iterable


def 偏函数(函数: Callable, *参数, **关键字参数) -> Callable:
    """
    创建偏函数（固定部分参数）
    
    参数:
        函数: 原函数
        参数: 要固定的位置参数
        关键字参数: 要固定的关键字参数
    
    返回:
        新的偏函数
    """
    return functools.partial(函数, *参数, **关键字参数)


def 偏函数方法(函数: Callable, *参数, **关键字参数) -> Callable:
    """创建偏函数（方法版本，支持作为方法使用）"""
    return functools.partialmethod(函数, *参数, **关键字参数)


def 归约(函数: Callable, 可迭代对象: Iterable[Any], 初始值: Any = None) -> Any:
    """
    归约（reduce）
    
    参数:
        函数: 累积函数（接受两个参数）
        可迭代对象: 要归约的可迭代对象
        初始值: 初始值
    
    返回:
        归约结果
    """
    if 初始值 is None:
        return functools.reduce(函数, 可迭代对象)
    return functools.reduce(函数, 可迭代对象, 初始值)


def 累积(函数: Callable, 序列: list, 初始值: Any = None) -> list:
    """
    累积计算（返回中间结果列表）
    
    参数:
        函数: 累积函数
        序列: 输入序列
        初始值: 初始值
    
    返回:
        累积结果列表
    """
    结果 = []
    累积值 = 初始值
    for 元素 in 序列:
        if 累积值 is None:
            累积值 = 元素
        else:
            累积值 = 函数(累积值, 元素)
        结果.append(累积值)
    return 结果


def 包装函数(被包装函数: Callable) -> Callable:
    """
    wraps装饰器（用于保留原函数元数据）
    
    用法:
        def 装饰器(函数):
            def 包装器(*参数, **关键字参数):
                return 函数(*参数, **关键字参数)
            return 包装函数(函数)(包装器)
    """
    return functools.wraps(被包装函数)


def 更新包装器(包装器: Callable, 被包装函数: Callable) -> Callable:
    """更新包装器的元数据"""
    return functools.update_wrapper(包装器, 被包装函数)


def 缓存LRU(最大条目数: int = 128) -> Callable:
    """
    LRU缓存装饰器
    
    参数:
        最大条目数: 最大缓存条目数
    
    用法:
        @缓存LRU(100)
        def 计算(n):
            ...
    """
    return functools.lru_cache(maxsize=最大条目数)


def 缓存无限() -> Callable:
    """无限缓存装饰器"""
    return functools.lru_cache(maxsize=None)


def 单分派(函数: Callable = None) -> Callable:
    """
    单分派泛函数装饰器
    
    用法:
        @单分派
        def 处理(数据):
            ...
        
        @处理.register(int)
        def _(数据):
            ...
    """
    if 函数 is None:
        return functools.singledispatch
    return functools.singledispatch(函数)


def 总序(类: type) -> type:
    """
    总序装饰器（自动补全比较运算符）
    
    只需定义 __eq__ 和 一个比较方法（如 __lt__），
    自动补全其他比较方法。
    """
    return functools.total_ordering(类)


def 求和(可迭代对象: Iterable[Any], 初始值: Any = 0) -> Any:
    """求和"""
    return sum(可迭代对象, 初始值)


def 求积(可迭代对象: Iterable[Any], 初始值: Any = 1) -> Any:
    """求积"""
    结果 = 初始值
    for 元素 in 可迭代对象:
        结果 *= 元素
    return 结果


def 最大值(可迭代对象: Iterable[Any], 键函数: Callable = None, 默认值: Any = None) -> Any:
    """最大值"""
    if 键函数:
        if 默认值 is not None:
            return max(可迭代对象, key=键函数, default=默认值)
        return max(可迭代对象, key=键函数)
    if 默认值 is not None:
        return max(可迭代对象, default=默认值)
    return max(可迭代对象)


def 最小值(可迭代对象: Iterable[Any], 键函数: Callable = None, 默认值: Any = None) -> Any:
    """最小值"""
    if 键函数:
        if 默认值 is not None:
            return min(可迭代对象, key=键函数, default=默认值)
        return min(可迭代对象, key=键函数)
    if 默认值 is not None:
        return min(可迭代对象, default=默认值)
    return min(可迭代对象)


def 全部为真(可迭代对象: Iterable[Any]) -> bool:
    """所有元素都为真"""
    return all(可迭代对象)


def 任一为真(可迭代对象: Iterable[Any]) -> bool:
    """任一元素为真"""
    return any(可迭代对象)


def 组合(函数列表: list) -> Callable:
    """
    函数组合：组合([f, g, h])(x) = f(g(h(x)))
    
    参数:
        函数列表: 函数列表（从右到左应用）
    
    返回:
        组合后的函数
    """
    def 组合函数(*参数, **关键字参数):
        结果 = 函数列表[-1](*参数, **关键字参数)
        for 函数 in reversed(函数列表[:-1]):
            结果 = 函数(结果)
        return 结果
    return 组合函数


def 管道(数据: Any, 函数列表: list) -> Any:
    """
    管道操作：管道(x, [f, g, h]) = h(g(f(x)))
    
    参数:
        数据: 初始数据
        函数列表: 函数列表（从左到右应用）
    
    返回:
        最终结果
    """
    结果 = 数据
    for 函数 in 函数列表:
        结果 = 函数(结果)
    return 结果


def 柯里化(函数: Callable) -> Callable:
    """
    柯里化函数（将多参数函数转为单参数链式调用）
    
    用法:
        @柯里化
        def 加(a, b, c):
            return a + b + c
        
        加(1)(2)(3)  # 6
    """
    import inspect
    sig = inspect.signature(函数)
    参数数量 = len(sig.parameters)
    
    def 柯里化函数(*已传参数):
        if len(已传参数) >= 参数数量:
            return 函数(*已传参数)
        return lambda *更多参数: 柯里化函数(*已传参数, *更多参数)
    
    return 柯里化函数


__all__ = [
    '偏函数', '偏函数方法',
    '归约', '累积',
    '包装函数', '更新包装器',
    '缓存LRU', '缓存无限',
    '单分派', '总序',
    '求和', '求积', '最大值', '最小值',
    '全部为真', '任一为真',
    '组合', '管道', '柯里化',
]
