"""
并行计算 — lightpub 桥接模块

基于 Python concurrent.futures 库封装，函数名对齐上游 duanpub（段言时期）packages/并行计算/源.duan。

上游 duanpub 原始包通过 C FFI 实现线程池、任务并行，
本桥接模块用 Python concurrent.futures 模块替代，提供等价的并行计算功能。
"""

import concurrent.futures as _futures


# =============================================================================
# 线程池管理
# =============================================================================

def 创建线程池(max_workers=None):
    """创建线程池，返回线程池对象"""
    try:
        return _futures.ThreadPoolExecutor(max_workers=max_workers)
    except Exception as e:
        raise Exception("创建线程池失败: " + str(e))


def 线程池提交任务(pool, fn, *args, **kwargs):
    """向线程池提交任务，返回 Future 对象"""
    if not pool:
        raise Exception("线程池提交任务失败: 线程池为空")
    if not callable(fn):
        raise Exception("线程池提交任务失败: 函数不是可调用对象")
    try:
        return pool.submit(fn, *args, **kwargs)
    except Exception as e:
        raise Exception("线程池提交任务失败: " + str(e))


# =============================================================================
# 进程池管理
# =============================================================================

def 创建进程池(max_workers=None):
    """创建进程池，返回进程池对象"""
    try:
        return _futures.ProcessPoolExecutor(max_workers=max_workers)
    except Exception as e:
        raise Exception("创建进程池失败: " + str(e))


def 进程池提交任务(pool, fn, *args, **kwargs):
    """向进程池提交任务，返回 Future 对象"""
    if not pool:
        raise Exception("进程池提交任务失败: 进程池为空")
    if not callable(fn):
        raise Exception("进程池提交任务失败: 函数不是可调用对象")
    try:
        return pool.submit(fn, *args, **kwargs)
    except Exception as e:
        raise Exception("进程池提交任务失败: " + str(e))


# =============================================================================
# 并行操作
# =============================================================================

def 并行映射(fn, *iterables, timeout=None, executor=None):
    """并行映射，对可迭代对象并行执行函数"""
    if not callable(fn):
        raise Exception("并行映射失败: 函数不是可调用对象")
    try:
        if executor:
            return list(executor.map(fn, *iterables, timeout=timeout))
        with _futures.ThreadPoolExecutor() as pool:
            return list(pool.map(fn, *iterables, timeout=timeout))
    except Exception as e:
        raise Exception("并行映射失败: " + str(e))


def 等待完成(futures, timeout=None, return_when='ALL_COMPLETED'):
    """等待 futures 完成"""
    if not futures:
        raise Exception("等待完成失败: futures 为空")
    try:
        if return_when == 'ALL_COMPLETED':
            when = _futures.ALL_COMPLETED
        elif return_when == 'FIRST_COMPLETED':
            when = _futures.FIRST_COMPLETED
        elif return_when == 'FIRST_EXCEPTION':
            when = _futures.FIRST_EXCEPTION
        else:
            when = _futures.ALL_COMPLETED
        done, not_done = _futures.wait(futures, timeout=timeout, return_when=when)
        return {
            'done': list(done),
            'not_done': list(not_done),
        }
    except Exception as e:
        raise Exception("等待完成失败: " + str(e))


def 获取结果(future, timeout=None):
    """获取 Future 执行结果"""
    if not future:
        raise Exception("获取结果失败: future 为空")
    try:
        return future.result(timeout=timeout)
    except Exception as e:
        raise Exception("获取结果失败: " + str(e))


def 异步执行(fn, *args, **kwargs):
    """异步执行函数，返回 Future 对象"""
    if not callable(fn):
        raise Exception("异步执行失败: 函数不是可调用对象")
    try:
        with _futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(fn, *args, **kwargs)
    except Exception as e:
        raise Exception("异步执行失败: " + str(e))