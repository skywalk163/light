"""光明编译缓存系统

支持：
- 文件哈希缓存（检测文件是否修改）
- 模块级缓存（缓存单个模块的编译结果）
- 依赖追踪（缓存依赖的模块）
- 缓存清理（TTL / 手动清理）
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from pathlib import Path


class CompilationCache:
    """编译缓存系统

    基于文件内容和元数据生成缓存键，支持缓存的新鲜度检查、
    过期清理和缓存统计。

    Attributes:
        cache_dir: 缓存目录路径
        _cache: 内存缓存 {cache_key: cached_data}
        _dirty: 脏标记，记录哪些文件的缓存已失效
    """

    def __init__(self, cache_dir: str = None):
        """初始化缓存

        Args:
            cache_dir: 缓存目录路径，默认在项目根目录的 .light_cache 下
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.getcwd(), '.light_cache')
        self.cache_dir = cache_dir
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._dirty: Dict[str, bool] = {}
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached(self, file_path: str) -> Optional[str]:
        """获取缓存编译结果

        Args:
            file_path: 源文件路径

        Returns:
            缓存的编译结果（IR 字符串），如果没有缓存或缓存已失效则返回 None
        """
        cache_key = self.get_cache_key(file_path)
        if not cache_key:
            return None

        # 检查内存缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if self._is_fresh(cached):
                return cached.get('result')

        # 检查磁盘缓存
        cache_file = self._get_cache_file(cache_key)
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                self._cache[cache_key] = cached
                if self._is_fresh(cached):
                    return cached.get('result')
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def set_cached(self, file_path: str, result: str):
        """设置缓存

        Args:
            file_path: 源文件路径
            result: 编译结果（IR 字符串）
        """
        cache_key = self.get_cache_key(file_path)
        if not cache_key:
            return

        # 获取文件元数据
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            mtime = time.time()
            size = len(result)

        # 计算文件内容哈希
        content_hash = self._hash_file(file_path)

        cached_data = {
            'key': cache_key,
            'result': result,
            'mtime': mtime,
            'size': size,
            'content_hash': content_hash,
            'cached_at': time.time(),
            'file_path': file_path,
        }

        # 更新内存缓存
        self._cache[cache_key] = cached_data

        # 写入磁盘缓存
        cache_file = self._get_cache_file(cache_key)
        if cache_file:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cached_data, f, ensure_ascii=False, indent=2)
            except IOError:
                pass

    def invalidate(self, file_path: str):
        """使缓存失效

        Args:
            file_path: 源文件路径
        """
        cache_key = self.get_cache_key(file_path)
        if cache_key:
            self._dirty[cache_key] = True
            if cache_key in self._cache:
                del self._cache[cache_key]
            # 删除磁盘缓存
            cache_file = self._get_cache_file(cache_key)
            if cache_file and os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except OSError:
                    pass

    def get_cache_key(self, file_path: str) -> str:
        """生成缓存键（基于文件路径和内容）

        Args:
            file_path: 源文件路径

        Returns:
            缓存键字符串
        """
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            abs_path = os.path.abspath(file_path)
            content_hash = self._hash_file(file_path)
            # 缓存键 = 路径哈希 + 内容哈希
            path_hash = hashlib.md5(abs_path.encode('utf-8')).hexdigest()[:12]
            return f'{path_hash}_{content_hash[:16]}'
        except Exception:
            return None

    def is_fresh(self, file_path: str) -> bool:
        """检查缓存是否新鲜

        Args:
            file_path: 源文件路径

        Returns:
            True 表示缓存新鲜有效
        """
        cache_key = self.get_cache_key(file_path)
        if not cache_key:
            return False

        # 检查脏标记
        if self._dirty.get(cache_key, False):
            return False

        # 从内存缓存检查
        if cache_key in self._cache:
            return self._is_fresh(self._cache[cache_key])

        # 从磁盘缓存检查
        cache_file = self._get_cache_file(cache_key)
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                return self._is_fresh(cached)
            except Exception:
                pass

        return False

    def _is_fresh(self, cached: Dict) -> bool:
        """检查缓存数据是否新鲜

        Args:
            cached: 缓存数据字典

        Returns:
            True 表示缓存新鲜
        """
        file_path = cached.get('file_path', '')
        if not file_path or not os.path.exists(file_path):
            return False

        try:
            stat = os.stat(file_path)
            # 检查 mtime 是否变化
            if stat.st_mtime != cached.get('mtime'):
                return False
            # 检查内容哈希是否变化
            current_hash = self._hash_file(file_path)
            if current_hash != cached.get('content_hash'):
                return False
        except OSError:
            return False

        return True

    def clean(self, max_age_hours: int = 24):
        """清理过期缓存

        Args:
            max_age_hours: 缓存最大存活时间（小时），默认 24 小时
        """
        now = time.time()
        max_age = max_age_hours * 3600
        cleaned = 0

        # 清理内存缓存
        expired_keys = []
        for key, data in self._cache.items():
            age = now - data.get('cached_at', 0)
            if age > max_age:
                expired_keys.append(key)
        for key in expired_keys:
            del self._cache[key]
            cleaned += 1

        # 清理磁盘缓存（只删除 .json 缓存文件）
        cache_dir = Path(self.cache_dir)
        if cache_dir.exists():
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file() and cache_file.suffix == '.json':
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        age = now - data.get('cached_at', 0)
                        if age > max_age:
                            cache_file.unlink()
                            cleaned += 1
                    except Exception:
                        cache_file.unlink()
                        cleaned += 1

        if cleaned > 0:
            pass  # 清理完成

    def clear(self):
        """清空所有缓存"""
        self._cache.clear()
        self._dirty.clear()

        cache_dir = Path(self.cache_dir)
        if cache_dir.exists():
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file() and cache_file.suffix == '.json':
                    try:
                        cache_file.unlink()
                    except OSError:
                        pass

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含缓存统计信息的字典
        """
        memory_cache_size = len(self._cache)
        disk_cache_size = 0
        disk_cache_bytes = 0

        cache_dir = Path(self.cache_dir)
        if cache_dir.exists():
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file():
                    disk_cache_size += 1
                    try:
                        disk_cache_bytes += cache_file.stat().st_size
                    except OSError:
                        pass

        return {
            'memory_cache_entries': memory_cache_size,
            'disk_cache_entries': disk_cache_size,
            'disk_cache_bytes': disk_cache_bytes,
            'cache_dir': self.cache_dir,
            'dirty_entries': len(self._dirty),
        }

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _get_cache_file(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        if not cache_key:
            return None
        return os.path.join(self.cache_dir, f'{cache_key}.json')

    @staticmethod
    def _hash_file(file_path: str) -> str:
        """计算文件内容的 MD5 哈希

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希字符串
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except OSError:
            return ''

    @staticmethod
    def _hash_content(content: str) -> str:
        """计算字符串内容的 MD5 哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()