"""
连接池 — lightpub 桥接模块

基于 Python queue 库封装，函数名对齐上游 duanpub（段言时期）packages/连接池/源.duan。

上游 duanpub 原始包通过 C FFI 实现数据库连接池，
本桥接模块用 Python queue 模块替代，提供等价的连接池功能。
"""

import queue as _queue
import threading as _threading
import time as _time


# =============================================================================
# 连接池
# =============================================================================

class _ConnectionPool:
    """连接池"""
    def __init__(self, factory, min_size=1, max_size=10):
        self._factory = factory
        self._min_size = min_size
        self._max_size = max_size
        self._pool = _queue.Queue()
        self._active = 0
        self._lock = _threading.Lock()
        self._closed = False
        self._created = 0
        self._acquired = 0
        self._released = 0
        self._wait_count = 0
        # 初始化最小连接
        for _ in range(min_size):
            try:
                conn = factory()
                self._pool.put(conn)
                self._created += 1
            except Exception:
                pass

    def _create_conn(self):
        """创建新连接"""
        try:
            conn = self._factory()
            self._created += 1
            return conn
        except Exception:
            return None


def 创建连接池(factory, min_size=1, max_size=10):
    """创建连接池

    Args:
        factory: 创建连接的可调用对象
        min_size: 最小连接数
        max_size: 最大连接数
    """
    if not callable(factory):
        raise Exception("创建连接池失败: factory 不是可调用对象")
    if min_size < 0:
        raise Exception("创建连接池失败: min_size 不能为负数")
    if max_size < min_size:
        raise Exception("创建连接池失败: max_size 不能小于 min_size")
    try:
        return _ConnectionPool(factory, min_size, max_size)
    except Exception as e:
        raise Exception("创建连接池失败: " + str(e))


def 连接池获取连接(pool, timeout=None):
    """从连接池获取连接"""
    if not pool:
        raise Exception("连接池获取连接失败: 连接池为空")
    if pool._closed:
        raise Exception("连接池获取连接失败: 连接池已关闭")
    try:
        with pool._lock:
            pool._wait_count += 1
        try:
            conn = pool._pool.get(timeout=timeout)
            with pool._lock:
                pool._acquired += 1
                pool._active += 1
            return conn
        except _queue.Empty:
            with pool._lock:
                if pool._created < pool._max_size:
                    conn = pool._create_conn()
                    if conn:
                        pool._acquired += 1
                        pool._active += 1
                        return conn
            raise Exception("连接池获取连接失败: 无可用连接")
        finally:
            with pool._lock:
                pool._wait_count -= 1
    except Exception as e:
        if not isinstance(e, Exception) or "连接池获取连接失败" not in str(e):
            raise Exception("连接池获取连接失败: " + str(e))
        raise


def 连接池释放连接(pool, conn):
    """释放连接回连接池"""
    if not pool:
        raise Exception("连接池释放连接失败: 连接池为空")
    if not conn:
        raise Exception("连接池释放连接失败: 连接为空")
    if pool._closed:
        return False
    try:
        pool._pool.put(conn)
        with pool._lock:
            pool._released += 1
            pool._active -= 1
        return True
    except Exception as e:
        raise Exception("连接池释放连接失败: " + str(e))


def 连接池关闭(pool):
    """关闭连接池"""
    if not pool:
        raise Exception("连接池关闭失败: 连接池为空")
    try:
        pool._closed = True
        while not pool._pool.empty():
            try:
                conn = pool._pool.get_nowait()
                if hasattr(conn, 'close'):
                    try:
                        conn.close()
                    except Exception:
                        pass
            except _queue.Empty:
                break
        return True
    except Exception as e:
        raise Exception("连接池关闭失败: " + str(e))


def 连接池获取统计(pool):
    """获取连接池统计信息"""
    if not pool:
        raise Exception("连接池获取统计失败: 连接池为空")
    try:
        return {
            'min_size': pool._min_size,
            'max_size': pool._max_size,
            'active': pool._active,
            'idle': pool._pool.qsize(),
            'created': pool._created,
            'acquired': pool._acquired,
            'released': pool._released,
            'waiting': pool._wait_count,
            'closed': pool._closed,
        }
    except Exception as e:
        raise Exception("连接池获取统计失败: " + str(e))


def 连接池设置最小连接数(pool, min_size):
    """设置连接池最小连接数"""
    if not pool:
        raise Exception("连接池设置最小连接数失败: 连接池为空")
    if min_size < 0:
        raise Exception("连接池设置最小连接数失败: min_size 不能为负数")
    if min_size > pool._max_size:
        raise Exception("连接池设置最小连接数失败: min_size 不能超过 max_size")
    try:
        pool._min_size = min_size
        # 补充连接到最小数
        current = pool._pool.qsize() + pool._active
        for _ in range(max(0, min_size - current)):
            try:
                conn = pool._create_conn()
                if conn:
                    pool._pool.put(conn)
            except Exception:
                break
        return True
    except Exception as e:
        raise Exception("连接池设置最小连接数失败: " + str(e))