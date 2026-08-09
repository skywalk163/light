"""
光明标准库 - 装饰器模块

提供常用装饰器，包括：
- 缓存装饰器（带过期时间、最大缓存数）
- 重试装饰器（带次数、间隔、退避策略）
- 计时装饰器
- 日志装饰器
- 权限检查装饰器
- 异常处理装饰器
- 类型检查装饰器
"""

import time
import functools
import logging
import hashlib
from typing import Callable, Any, Optional, Dict, List, Tuple, Type


def 缓存(最大缓存数: int = 128, 过期秒数: int = None, 忽略关键字参数: bool = False):
    """缓存装饰器
    
    参数:
        最大缓存数: 最大缓存条目数，超出时使用LRU策略
        过期秒数: 缓存过期时间，None表示永不过期
        忽略关键字参数: 是否忽略关键字参数
    """
    def 装饰器(函数: Callable) -> Callable:
        缓存字典 = {}
        访问时间 = {}
        命中次数 = {'命中': 0, '未命中': 0}
        
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            if 忽略关键字参数:
                键 = _生成缓存键(参数)
            else:
                键 = _生成缓存键(参数 + (frozenset(关键字参数.items()),))
            
            现在 = time.monotonic()
            
            if 键 in 缓存字典:
                数据 = 缓存字典[键]
                if 过期秒数 is None or (现在 - 数据['时间']) < 过期秒数:
                    访问时间[键] = 现在
                    命中次数['命中'] += 1
                    return 数据['结果']
            
            命中次数['未命中'] += 1
            
            if len(缓存字典) >= 最大缓存数:
                最旧键 = min(访问时间, key=访问时间.get)
                del 缓存字典[最旧键]
                del 访问时间[最旧键]
            
            结果 = 函数(*参数, **关键字参数)
            缓存字典[键] = {'结果': 结果, '时间': 现在}
            访问时间[键] = 现在
            
            return 结果
        
        包装器.清除缓存 = lambda: 缓存字典.clear()
        包装器.获取缓存信息 = lambda: {
            '大小': len(缓存字典),
            '最大缓存数': 最大缓存数,
            '过期秒数': 过期秒数,
            '命中次数': 命中次数['命中'],
            '未命中次数': 命中次数['未命中'],
            '命中率': 命中次数['命中'] / max(命中次数['命中'] + 命中次数['未命中'], 1)
        }
        
        return 包装器
    return 装饰器


def _生成缓存键(参数: tuple) -> str:
    """生成缓存键"""
    try:
        数据 = str(参数).encode('utf-8')
        return hashlib.md5(数据).hexdigest()
    except:
        return str(id(参数))


def 重试(最大次数: int = 3, 间隔秒数: float = 1.0, 退避因子: float = 2.0, 捕获异常: tuple = (Exception,), 日志函数: Callable = None):
    """重试装饰器
    
    参数:
        最大次数: 最大重试次数
        间隔秒数: 初始重试间隔
        退避因子: 指数退避因子，每次重试间隔乘以该因子
        捕获异常: 需要捕获的异常类型
        日志函数: 日志记录函数
    """
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            异常 = None
            当前间隔 = 间隔秒数
            
            for 次数 in range(最大次数):
                try:
                    return 函数(*参数, **关键字参数)
                except 捕获异常 as e:
                    异常 = e
                    if 日志函数:
                        日志函数(f'第{次数+1}次尝试失败: {e}')
                    if 次数 < 最大次数 - 1:
                        time.sleep(当前间隔)
                        当前间隔 *= 退避因子
            
            raise 异常
        
        return 包装器
    return 装饰器


def 计时(日志函数: Callable = print, 输出格式: str = '{函数名} 执行时间: {耗时:.6f}秒'):
    """计时装饰器"""
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            开始 = time.perf_counter()
            结果 = 函数(*参数, **关键字参数)
            结束 = time.perf_counter()
            耗时 = 结束 - 开始
            日志函数(输出格式.format(函数名=函数.__name__, 耗时=耗时))
            return 结果
        return 包装器
    return 装饰器


def 日志(日志级别: str = 'INFO', 日志格式: str = '{时间} [{级别}] {函数名}({参数}) -> {结果}'):
    """日志装饰器"""
    def 装饰器(函数: Callable) -> Callable:
        日志器 = logging.getLogger(函数.__module__)
        
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            级别映射 = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR
            }
            级别 = 级别映射.get(日志级别, logging.INFO)
            
            参数描述 = ', '.join([str(p) for p in 参数])
            if 关键字参数:
                参数描述 += ', ' + ', '.join([f'{k}={v}' for k, v in 关键字参数.items()])
            
            日志器.log(级别, f'{函数.__name__}({参数描述})')
            
            try:
                结果 = 函数(*参数, **关键字参数)
                日志器.log(级别, f'{函数.__name__} -> {结果}')
                return 结果
            except Exception as e:
                日志器.error(f'{函数.__name__} 异常: {e}')
                raise
        
        return 包装器
    return 装饰器


def 异常处理(捕获异常: tuple = (Exception,), 返回值: Any = None, 日志函数: Callable = None):
    """异常处理装饰器"""
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            try:
                return 函数(*参数, **关键字参数)
            except 捕获异常 as e:
                if 日志函数:
                    日志函数(f'{函数.__name__} 异常: {e}')
                return 返回值
        return 包装器
    return 装饰器


def 类型检查(*参数类型: Type, **关键字参数类型: Type):
    """类型检查装饰器"""
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            for i, (实参, 期望类型) in enumerate(zip(参数, 参数类型)):
                if not isinstance(实参, 期望类型):
                    raise TypeError(f'参数{i}类型错误: 期望{期望类型}, 实际{type(实参)}')
            
            for 名称, 期望类型 in 关键字参数类型.items():
                if 名称 in 关键字参数 and not isinstance(关键字参数[名称], 期望类型):
                    raise TypeError(f'参数{名称}类型错误: 期望{期望类型}, 实际{type(关键字参数[名称])}')
            
            return 函数(*参数, **关键字参数)
        return 包装器
    return 装饰器


def 权限检查(权限函数: Callable, 未授权返回值: Any = None, 未授权异常: Exception = None):
    """权限检查装饰器
    
    参数:
        权限函数: 权限检查函数，返回True表示有权限
        未授权返回值: 未授权时返回的值
        未授权异常: 未授权时抛出的异常
    """
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            if 权限函数(*参数, **关键字参数):
                return 函数(*参数, **关键字参数)
            if 未授权异常:
                raise 未授权异常
            return 未授权返回值
        return 包装器
    return 装饰器


def 单例(类类型: type) -> type:
    """单例装饰器"""
    实例 = {}
    
    @functools.wraps(类类型)
    def 包装器(*参数, **关键字参数):
        if 类类型 not in 实例:
            实例[类类型] = 类类型(*参数, **关键字参数)
        return 实例[类类型]
    
    return 包装器


def 同步(锁=None):
    """同步装饰器"""
    if 锁 is None:
        import threading
        锁 = threading.Lock()
    
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            with 锁:
                return 函数(*参数, **关键字参数)
        return 包装器
    return 装饰器


def 限流(最大调用次数: int = 100, 时间窗口秒数: int = 60):
    """限流装饰器"""
    调用记录 = []
    
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            现在 = time.monotonic()
            调用记录[:] = [t for t in 调用记录 if (现在 - t) < 时间窗口秒数]
            
            if len(调用记录) >= 最大调用次数:
                raise ValueError(f'{函数.__name__} 超出调用限制: {最大调用次数}/{时间窗口秒数}秒')
            
            调用记录.append(现在)
            return 函数(*参数, **关键字参数)
        
        包装器.获取调用次数 = lambda: len(调用记录)
        包装器.重置限制 = lambda: 调用记录.clear()
        
        return 包装器
    return 装饰器


def 延迟(延迟秒数: float = 1.0):
    """延迟执行装饰器"""
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            time.sleep(延迟秒数)
            return 函数(*参数, **关键字参数)
        return 包装器
    return 装饰器


def 预热(预热次数: int = 1):
    """预热装饰器（函数加载时执行N次）"""
    def 装饰器(函数: Callable) -> Callable:
        for _ in range(预热次数):
            函数()
        
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            return 函数(*参数, **关键字参数)
        return 包装器
    return 装饰器


def 统计(统计函数: Callable = None):
    """统计装饰器"""
    统计数据 = {
        '调用次数': 0,
        '总耗时': 0.0,
        '最小耗时': float('inf'),
        '最大耗时': 0.0,
        '异常次数': 0
    }
    
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*参数, **关键字参数):
            开始 = time.perf_counter()
            try:
                结果 = 函数(*参数, **关键字参数)
                统计数据['调用次数'] += 1
                return 结果
            except Exception:
                统计数据['异常次数'] += 1
                raise
            finally:
                耗时 = time.perf_counter() - 开始
                统计数据['总耗时'] += 耗时
                统计数据['最小耗时'] = min(统计数据['最小耗时'], 耗时)
                统计数据['最大耗时'] = max(统计数据['最大耗时'], 耗时)
        
        包装器.获取统计数据 = lambda: {
            '调用次数': 统计数据['调用次数'],
            '总耗时': 统计数据['总耗时'],
            '平均耗时': 统计数据['总耗时'] / max(统计数据['调用次数'], 1),
            '最小耗时': 统计数据['最小耗时'],
            '最大耗时': 统计数据['最大耗时'],
            '异常次数': 统计数据['异常次数']
        }
        
        return 包装器
    return 装饰器


def 缓存带过期(过期秒数: int = 3600):
    """带过期时间的缓存装饰器（简化版本）"""
    return 缓存(过期秒数=过期秒数)


def 缓存LRU(最大缓存数: int = 128):
    """LRU缓存装饰器（简化版本）"""
    return 缓存(最大缓存数=最大缓存数)


__all__ = [
    '缓存', '缓存带过期', '缓存LRU',
    '重试',
    '计时',
    '日志',
    '异常处理',
    '类型检查',
    '权限检查',
    '单例',
    '同步',
    '限流',
    '延迟',
    '预热',
    '统计'
]