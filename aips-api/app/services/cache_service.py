from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any
import hashlib
import pickle
import time

from app.core.config import TEMP_DIR


@dataclass
class CacheItem:
    data: Any
    timestamp: float
    ttl: int


class CacheService:
    def __init__(self, cache_dir: Path = None, default_ttl: int = 3600):
        self.cache_dir = cache_dir or TEMP_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self._cache = {}
        self._load_cache()

    def _generate_key(self, key: str) -> str:
        """生成缓存键的哈希值"""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        hash_key = self._generate_key(key)
        return self.cache_dir / f"{hash_key}.pickle"

    def _load_cache(self):
        """从磁盘加载缓存"""
        for cache_file in self.cache_dir.glob("*.pickle"):
            try:
                with open(cache_file, "rb") as f:
                    item = pickle.load(f)
                if time.time() - item.timestamp < item.ttl:
                    key = cache_file.stem
                    self._cache[key] = item
                else:
                    # 删除过期缓存
                    cache_file.unlink()
            except Exception:
                # 忽略损坏的缓存文件
                try:
                    cache_file.unlink()
                except Exception:
                    pass

    def _save_cache(self, key: str, item: CacheItem):
        """保存缓存到磁盘"""
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(item, f)
        except Exception:
            # 忽略保存失败
            pass

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        hash_key = self._generate_key(key)
        item = self._cache.get(hash_key)
        
        if item:
            if time.time() - item.timestamp < item.ttl:
                return item.data
            else:
                # 删除过期缓存
                del self._cache[hash_key]
                cache_path = self._get_cache_path(key)
                try:
                    cache_path.unlink()
                except Exception:
                    pass
        
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        hash_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        item = CacheItem(data=data, timestamp=time.time(), ttl=ttl)
        self._cache[hash_key] = item
        self._save_cache(key, item)

    def delete(self, key: str) -> None:
        """删除缓存"""
        hash_key = self._generate_key(key)
        if hash_key in self._cache:
            del self._cache[hash_key]
        cache_path = self._get_cache_path(key)
        try:
            cache_path.unlink()
        except Exception:
            pass

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        for cache_file in self.cache_dir.glob("*.pickle"):
            try:
                cache_file.unlink()
            except Exception:
                pass

    def cleanup(self) -> int:
        """清理过期缓存"""
        deleted = 0
        current_time = time.time()
        
        # 清理内存中的过期缓存
        expired_keys = []
        for key, item in self._cache.items():
            if current_time - item.timestamp >= item.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            deleted += 1
        
        # 清理磁盘上的过期缓存
        for cache_file in self.cache_dir.glob("*.pickle"):
            try:
                with open(cache_file, "rb") as f:
                    item = pickle.load(f)
                if current_time - item.timestamp >= item.ttl:
                    cache_file.unlink()
                    deleted += 1
            except Exception:
                # 忽略损坏的缓存文件
                try:
                    cache_file.unlink()
                    deleted += 1
                except Exception:
                    pass
        
        return deleted


# 创建全局缓存服务实例
cache_service = CacheService()
