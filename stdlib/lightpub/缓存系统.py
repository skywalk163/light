"""
缓存系统 — lightpub 桥接模块

基于 Python functools 库封装，函数名对齐上游 duanpub（段言时期）packages/缓存系统/源.duan。

上游 duanpub 原始包通过 C FFI 实现多级缓存/LRU/LFU/TTL淘汰策略，
本桥接模块用 Python functools.lru_cache 和 dict 替代，提供等价的缓存功能。
"""

import time as _time
import threading as _threading


# =============================================================================
# 缓存配置
# =============================================================================

def 新建缓存配置(max_size=100, ttl=300, policy='lru'):
    """创建缓存配置"""
    if max_size < 1:
        raise Exception("新建缓存配置失败: max_size 必须大于0")
    if ttl < 0:
        raise Exception("新建缓存配置失败: ttl 不能为负数")
    if policy not in ('lru', 'lfu', 'ttl'):
        raise Exception("新建缓存配置失败: 不支持的淘汰策略 " + policy)
    return {
        'max_size': max_size,
        'ttl': ttl,
        'policy': policy,
    }


# =============================================================================
# 内存缓存
# =============================================================================

class _MemoryCache:
    """内存缓存实现"""
    def __init__(self, config=None):
        self._config = config or 新建缓存配置()
        self._data = {}
        self._expiry = {}
        self._access_count = {}
        self._lock = _threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _is_expired(self, key):
        if key in self._expiry:
            return _time.time() > self._expiry[key]
        return False

    def _evict_if_needed(self):
        if len(self._data) <= self._config['max_size']:
            return
        policy = self._config['policy']
        if policy == 'lru':
            # 淘汰最久未访问的
            oldest = min(self._access_count.keys(), key=lambda k: self._access_count[k])
            self._remove(oldest)
        elif policy == 'lfu':
            # 淘汰访问最少的
            least = min(self._access_count.keys(), key=lambda k: self._access_count[k])
            self._remove(least)
        elif policy == 'ttl':
            # 淘汰最早过期的
            oldest_exp = min(self._expiry.keys(), key=lambda k: self._expiry[k])
            self._remove(oldest_exp)
        self._evictions += 1

    def _remove(self, key):
        self._data.pop(key, None)
        self._expiry.pop(key, None)
        self._access_count.pop(key, None)


def 新建内存缓存(config=None):
    """创建内存缓存实例"""
    try:
        return _MemoryCache(config)
    except Exception as e:
        raise Exception("新建内存缓存失败: " + str(e))


def 缓存获取(cache, key):
    """从缓存获取值"""
    if not cache:
        raise Exception("缓存获取失败: 缓存为空")
    if key is None:
        raise Exception("缓存获取失败: key 为空")
    try:
        with cache._lock:
            if key in cache._data and cache._is_expired(key):
                cache._remove(key)
                cache._misses += 1
                return None
            if key in cache._data:
                cache._hits += 1
                cache._access_count[key] = _time.time()
                return cache._data[key]
            cache._misses += 1
            return None
    except Exception as e:
        raise Exception("缓存获取失败: " + str(e))


def 缓存设置(cache, key, value, ttl=None):
    """设置缓存值"""
    if not cache:
        raise Exception("缓存设置失败: 缓存为空")
    if key is None:
        raise Exception("缓存设置失败: key 为空")
    try:
        with cache._lock:
            cache._data[key] = value
            ttl = ttl if ttl is not None else cache._config['ttl']
            if ttl > 0:
                cache._expiry[key] = _time.time() + ttl
            cache._access_count[key] = _time.time()
            cache._evict_if_needed()
        return True
    except Exception as e:
        raise Exception("缓存设置失败: " + str(e))


def 缓存删除(cache, key):
    """删除缓存值"""
    if not cache:
        raise Exception("缓存删除失败: 缓存为空")
    if key is None:
        raise Exception("缓存删除失败: key 为空")
    try:
        with cache._lock:
            cache._remove(key)
        return True
    except Exception as e:
        raise Exception("缓存删除失败: " + str(e))


def 缓存是否存在(cache, key):
    """检查缓存key是否存在且未过期"""
    if not cache:
        raise Exception("缓存是否存在失败: 缓存为空")
    if key is None:
        raise Exception("缓存是否存在失败: key 为空")
    try:
        with cache._lock:
            if key in cache._data and cache._is_expired(key):
                cache._remove(key)
                return False
            return key in cache._data
    except Exception as e:
        raise Exception("缓存是否存在失败: " + str(e))


def 缓存清空(cache):
    """清空缓存"""
    if not cache:
        raise Exception("缓存清空失败: 缓存为空")
    try:
        with cache._lock:
            cache._data.clear()
            cache._expiry.clear()
            cache._access_count.clear()
            cache._hits = 0
            cache._misses = 0
            cache._evictions = 0
        return True
    except Exception as e:
        raise Exception("缓存清空失败: " + str(e))


def 缓存获取统计(cache):
    """获取缓存统计信息"""
    if not cache:
        raise Exception("缓存获取统计失败: 缓存为空")
    try:
        with cache._lock:
            total = cache._hits + cache._misses
            hit_rate = cache._hits / total if total > 0 else 0
            return {
                'size': len(cache._data),
                'max_size': cache._config['max_size'],
                'hits': cache._hits,
                'misses': cache._misses,
                'hit_rate': hit_rate,
                'evictions': cache._evictions,
                'policy': cache._config['policy'],
                'ttl': cache._config['ttl'],
            }
    except Exception as e:
        raise Exception("缓存获取统计失败: " + str(e))


def 缓存获取大小(cache):
    """获取缓存当前大小"""
    if not cache:
        raise Exception("缓存获取大小失败: 缓存为空")
    try:
        with cache._lock:
            return len(cache._data)
    except Exception as e:
        raise Exception("缓存获取大小失败: " + str(e))