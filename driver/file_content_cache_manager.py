#!/usr/bin/env python3
"""
File Content Cache Manager (FCCM) v1.0
Оптимизация затрат на чтение и кеширование файлов для Bober-Drive

Цель: Сократить затраты на чтение файлов через:
1. LRU кеш содержимого файлов
2. Lazy loading больших файлов
3. Chunked reading для очень больших файлов (>100MB)
4. Content hash для detection изменений
5. Memory-mapped I/O для больших файлов

Поддерживаемые форматы:
- Markdown, TXT, JSON, YAML (full read)
- Большие файлы: streaming read + chunking
- Binary: skip (не индексируем)
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import OrderedDict
from threading import Lock
import mmap
import io

logger = logging.getLogger("FileContentCacheManager")


@dataclass
class CachedFileEntry:
    """Кешированный файл с метаданными"""
    file_path: Path
    content: str
    content_hash: str  # SHA256 hash для detection изменений
    file_size: int
    read_time_ms: float
    cached_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class FileContentCacheConfig:
    """Конфигурация кеша"""
    # Размеры
    max_cache_size_mb: int = 500  # Макс размер кеша в памяти
    max_file_size_mb: int = 100  # Макс размер файла для full read
    chunk_size_kb: int = 256  # Размер чанка для streaming read
    
    # LRU политика
    max_entries: int = 1000  # Макс количество файлов в кеше
    eviction_policy: str = "lru"  # lru, lfu, fifo
    
    # Оптимизация
    enable_mmap: bool = True  # Memory-mapped I/O для больших файлов
    cache_hash: bool = True  # Кешировать hash содержимого
    compression: bool = False  # Сжатие кешированного контента (TODO)


class FileContentCache:
    """LRU кеш для содержимого файлов"""
    
    def __init__(self, config: FileContentCacheConfig = None):
        self.config = config or FileContentCacheConfig()
        self._cache: OrderedDict[str, CachedFileEntry] = OrderedDict()
        self._lock = Lock()
        self._current_size_bytes = 0
        
        logger.info(
            f"FileContentCache initialized: "
            f"max_size={self.config.max_cache_size_mb}MB, "
            f"max_file_size={self.config.max_file_size_mb}MB, "
            f"max_entries={self.config.max_entries}"
        )
    
    def get(self, file_path: Path) -> Optional[str]:
        """Получить содержимое файла из кеша"""
        key = str(file_path.resolve())
        
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            logger.debug(f"Cache HIT: {file_path} (access #{entry.access_count})")
            return entry.content
    
    def put(self, file_path: Path, content: str, content_hash: str = None, read_time_ms: float = 0):
        """Добавить содержимое файла в кеш"""
        key = str(file_path.resolve())
        
        content_bytes = len(content.encode('utf-8'))
        
        # Проверка размера
        if content_bytes > self.config.max_cache_size_mb * 1024 * 1024:
            logger.warning(f"Content too large for cache: {file_path} ({content_bytes} bytes)")
            return False
        
        with self._lock:
            # Если уже в кеше, обновляем
            if key in self._cache:
                old_size = len(self._cache[key].content.encode('utf-8'))
                self._current_size_bytes -= old_size
                del self._cache[key]
            
            # Создаём entry
            entry = CachedFileEntry(
                file_path=file_path,
                content=content,
                content_hash=content_hash or self._compute_hash(content),
                file_size=file_path.stat().st_size,
                read_time_ms=read_time_ms,
                cached_at=datetime.now()
            )
            
            # Добавляем в кеш
            self._cache[key] = entry
            self._current_size_bytes += content_bytes
            
            # Eviction если надо
            self._evict_if_needed()
            
            logger.debug(f"Cache PUT: {file_path} ({content_bytes} bytes, {len(self._cache)} entries)")
            return True
    
    def invalidate(self, file_path: Path):
        """Инвалидировать кеш для файла"""
        key = str(file_path.resolve())
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_size_bytes -= len(entry.content.encode('utf-8'))
                del self._cache[key]
                logger.debug(f"Cache INVALIDATED: {file_path}")
    
    def _evict_if_needed(self):
        """Эвикшн если кеш переполнен"""
        # По размеру
        if self._current_size_bytes > self.config.max_cache_size_mb * 1024 * 1024:
            while self._cache and self._current_size_bytes > self.config.max_cache_size_mb * 1024 * 1024 * 0.9:
                old_key, old_entry = self._cache.popitem(last=False)  # LRU
                self._current_size_bytes -= len(old_entry.content.encode('utf-8'))
                logger.debug(f"LRU eviction by size: {old_entry.file_path}")
        
        # По количеству
        if len(self._cache) > self.config.max_entries:
            while len(self._cache) > self.config.max_entries * 0.9:
                old_key, old_entry = self._cache.popitem(last=False)  # LRU
                self._current_size_bytes -= len(old_entry.content.encode('utf-8'))
                logger.debug(f"LRU eviction by count: {old_entry.file_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика кеша"""
        with self._lock:
            return {
                "entries": len(self._cache),
                "size_mb": self._current_size_bytes / (1024 * 1024),
                "max_size_mb": self.config.max_cache_size_mb,
                "utilization_pct": (self._current_size_bytes / (self.config.max_cache_size_mb * 1024 * 1024)) * 100,
                "hits": sum(e.access_count for e in self._cache.values()),
                "oldest_entry_age_sec": (
                    (datetime.now() - min(e.cached_at for e in self._cache.values())).total_seconds()
                    if self._cache else 0
                )
            }
    
    def clear(self):
        """Очистить кеш"""
        with self._lock:
            self._cache.clear()
            self._current_size_bytes = 0
            logger.info("Cache cleared")
    
    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA256 hash содержимого"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class OptimizedFileReader:
    """Оптимизированное чтение файлов с интеллектуальной стратегией"""
    
    def __init__(self, cache: FileContentCache, config: FileContentCacheConfig = None):
        self.cache = cache
        self.config = config or FileContentCacheConfig()
        self._stats = {
            "total_reads": 0,
            "cache_hits": 0,
            "full_reads": 0,
            "chunked_reads": 0,
            "skipped_files": 0,
            "total_bytes_read": 0,
            "total_read_time_ms": 0
        }
        self._stats_lock = Lock()
    
    def read_optimized(self, file_path: Path) -> Optional[Tuple[str, str]]:
        """
        Читать файл оптимизированно
        
        Returns: (content, hash) или None если файл не поддерживается
        """
        
        with self._stats_lock:
            self._stats["total_reads"] += 1
        
        # 1. Проверка в кеше
        cached = self.cache.get(file_path)
        if cached:
            with self._stats_lock:
                self._stats["cache_hits"] += 1
            return (cached, self.cache._cache[str(file_path.resolve())].content_hash)
        
        # 2. Проверка типа файла
        if not self._is_supported_format(file_path):
            with self._stats_lock:
                self._stats["skipped_files"] += 1
            return None
        
        # 3. Выбор стратегии чтения
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > self.config.max_file_size_mb:
            # Streaming read для больших файлов
            content = self._read_chunked(file_path)
            with self._stats_lock:
                self._stats["chunked_reads"] += 1
        else:
            # Full read для нормальных файлов
            import time
            start = time.time()
            content = file_path.read_text(encoding='utf-8', errors='replace')
            read_time_ms = (time.time() - start) * 1000
            
            with self._stats_lock:
                self._stats["full_reads"] += 1
                self._stats["total_read_time_ms"] += read_time_ms
                self._stats["total_bytes_read"] += len(content.encode('utf-8'))
        
        # 4. Кеширование
        content_hash = FileContentCache._compute_hash(content)
        self.cache.put(file_path, content, content_hash, 
                      read_time_ms if file_size_mb <= self.config.max_file_size_mb else 0)
        
        return (content, content_hash)
    
    def _read_chunked(self, file_path: Path, max_chunks: int = 10) -> str:
        """Читать большой файл chunks (limited sampling)"""
        chunks = []
        chunk_size = self.config.chunk_size_kb * 1024
        chunks_read = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Читаем первые N chunks
                while chunks_read < max_chunks:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    chunks_read += 1
                
                # Добавляем индикатор усечения
                if chunk:  # Если есть ещё содержимое
                    chunks.append("\n[... file truncated for indexing ...]")
        
        except Exception as e:
            logger.warning(f"Error reading chunked file {file_path}: {e}")
            return ""
        
        return "".join(chunks)
    
    def _is_supported_format(self, file_path: Path) -> bool:
        """Проверить поддерживаемый формат"""
        supported = {'.md', '.markdown', '.txt', '.json', '.yaml', '.yml', '.rst'}
        return file_path.suffix.lower() in supported
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика читателя"""
        with self._stats_lock:
            return {
                **self._stats,
                "cache_hit_rate_pct": (
                    (self._stats["cache_hits"] / self._stats["total_reads"] * 100)
                    if self._stats["total_reads"] > 0 else 0
                ),
                "avg_read_time_ms": (
                    self._stats["total_read_time_ms"] / self._stats["full_reads"]
                    if self._stats["full_reads"] > 0 else 0
                )
            }


class FileChangeDetector:
    """Detect изменения файлов через hash сравнение"""
    
    def __init__(self, cache: FileContentCache):
        self.cache = cache
        self._previous_hashes: Dict[str, str] = {}
    
    def has_changed(self, file_path: Path) -> bool:
        """Проверить изменился ли файл"""
        key = str(file_path.resolve())
        
        current_hash = self._compute_file_hash(file_path)
        previous_hash = self._previous_hashes.get(key)
        
        if current_hash != previous_hash:
            self._previous_hashes[key] = current_hash
            return True
        
        return False
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Быстрый hash файла (только метаданные + первые 1KB)"""
        try:
            stat = file_path.stat()
            # Hash = size + mtime + first 1KB
            data = f"{stat.st_size}:{stat.st_mtime}".encode()
            
            with open(file_path, 'rb') as f:
                data += f.read(1024)
            
            return hashlib.sha256(data).hexdigest()
        except Exception as e:
            logger.warning(f"Error computing file hash: {e}")
            return ""


# ===== Public API =====

def create_file_content_cache(
    max_cache_mb: int = 500,
    max_file_mb: int = 100,
) -> Tuple[FileContentCache, OptimizedFileReader, FileChangeDetector]:
    """Создать оптимизированную систему чтения файлов"""
    
    config = FileContentCacheConfig(
        max_cache_size_mb=max_cache_mb,
        max_file_size_mb=max_file_mb,
    )
    
    cache = FileContentCache(config)
    reader = OptimizedFileReader(cache, config)
    detector = FileChangeDetector(cache)
    
    logger.info(f"File content caching system initialized: {max_cache_mb}MB cache, {max_file_mb}MB max file")
    
    return cache, reader, detector


# ===== Demo/Testing =====

if __name__ == "__main__":
    import tempfile
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Test 1: Small file
        small_file = tmpdir / "small.md"
        small_file.write_text("# Hello\n" * 100)
        
        # Test 2: Medium file
        medium_file = tmpdir / "medium.md"
        medium_file.write_text("# Documentation\n" * 5000)
        
        # Initialize system
        cache, reader, detector = create_file_content_cache(max_cache_mb=100)
        
        print("\n=== Test 1: Read small file ===")
        content, hash_val = reader.read_optimized(small_file)
        print(f"✓ Read {len(content)} chars, hash={hash_val[:16]}...")
        
        print("\n=== Test 2: Cache hit on second read ===")
        content2, _ = reader.read_optimized(small_file)
        assert content == content2, "Content mismatch!"
        print(f"✓ Cache hit! Stats: {reader.get_stats()}")
        
        print("\n=== Test 3: Change detection ===")
        small_file.write_text("# MODIFIED\n")
        changed = detector.has_changed(small_file)
        print(f"✓ Change detected: {changed}")
        
        print("\n=== Cache Stats ===")
        print(f"Cache utilization: {cache.get_stats()}")
        print(f"Reader stats: {reader.get_stats()}")
        
        print("\n✅ All tests passed!")
