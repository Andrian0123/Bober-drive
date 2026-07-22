#!/usr/bin/env python3
"""
Nexus Autonomous Daemon V3
Fully autonomous daemon for Bober-Drive project indexing and monitoring

Phases:
- Phase 1: Project initialization (full scan, indexing, vault population)
- Phase 2: File system monitoring and auto-reindexing
- Phase 3: Autonomous agent collaboration (search API, metrics)
"""

import logging
import sys
import time
import threading
import json
import fnmatch
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime

# Гибкий импорт для работы из разных контекстов
driver_path = str(Path(__file__).parent)
if driver_path not in sys.path:
    sys.path.insert(0, driver_path)

# Попытка импортировать watchdog с graceful fallback
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    
    # Stub classes для совместимости
    class Observer:
        def __init__(self):
            pass
        def start(self):
            pass
        def stop(self):
            pass
        def join(self):
            pass
    
    class FileSystemEventHandler:
        pass
    
    class FileModifiedEvent:
        def __init__(self, src_path: str):
            self.src_path = src_path
    
    class FileCreatedEvent:
        def __init__(self, src_path: str):
            self.src_path = src_path


class DaemonState(Enum):
    """Daemon lifecycle states"""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    READY = "ready"
    MONITORING = "monitoring"
    ERROR = "error"


class InitStrategy(Enum):
    """Initialization strategy"""
    FULL_SCAN = "full_scan"
    INCREMENTAL = "incremental"
    CHECKPOINT = "checkpoint"


@dataclass
class DaemonConfig:
    """Daemon configuration"""
    project_root: Path
    vault_path: Path
    checkpoint_path: Path = field(default_factory=lambda: Path.home() / ".bober" / "daemon.checkpoint")
    
    # File watching
    enable_file_watch: bool = True
    file_extensions: List[str] = field(default_factory=lambda: ['.md', '.txt', '.rst'])
    
    # Initialization
    init_strategy: InitStrategy = InitStrategy.FULL_SCAN
    scan_ignore_patterns: List[str] = field(default_factory=lambda: ['.git', '__pycache__', '.env'])
    
    # Performance
    reindex_debounce_ms: int = 500
    reindex_max_queue_size: int = 10000
    reindex_batch_size: int = 10
    
    # File Content Cache (v3.0.1+)
    enable_file_cache: bool = True
    file_cache_size_mb: int = 500
    file_cache_max_entries: int = 1000
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None


@dataclass
class DaemonMetrics:
    """Daemon metrics"""
    startup_time_ms: float = 0.0
    total_files_scanned: int = 0
    total_files_indexed: int = 0
    total_files_reindexed: int = 0
    active_searches: int = 0
    search_queries: int = 0
    avg_search_time_ms: float = 0.0
    reindex_queue_size: int = 0
    uptime_ms: float = 0.0


class FileChangeHandler(FileSystemEventHandler):
    """Watch file system changes and queue reindexing"""
    
    def __init__(self, daemon: 'NexusAutonomousDaemon', extensions: List[str]):
        super().__init__()
        self.daemon = daemon
        self.extensions = extensions
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix in self.extensions:
                self.daemon._queue_reindex(str(file_path))
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix in self.extensions:
                self.daemon._queue_reindex(str(file_path))


class NexusAutonomousDaemon:
    """
    Autonomous daemon for continuous project monitoring and indexing
    
    Lifecycle:
    1. STOPPED: Initial state
    2. INITIALIZING: Running Phase 1 (full scan)
    3. READY: Waiting for commands
    4. MONITORING: Actively monitoring files
    5. ERROR: Error state
    """
    
    def __init__(self, config: DaemonConfig, orchestrator: Optional[Any] = None):
        self.config = config
        self.state = DaemonState.STOPPED
        self.orchestrator = orchestrator
        
        # Threading
        self._lock = threading.RLock()
        self._reindex_lock = threading.Lock()
        
        # State tracking
        self._start_time = None
        self._reindex_queue: Dict[str, float] = {}  # {filepath: timestamp}
        self._reindex_debounce: Dict[str, float] = {}  # {filepath: debounce_time}
        self._reindex_thread = None
        self._reindex_running = False
        self._search_index: List[Dict[str, Any]] = []
        
        # File watching
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[FileChangeHandler] = None
        
        # Metrics
        self.metrics = DaemonMetrics()
        
        # File Content Cache (v3.0.1+)
        self.file_cache = None
        self.file_reader = None
        if self.config.enable_file_cache:
            try:
                from file_content_cache_manager import (
                    FileContentCache,
                    FileContentCacheConfig,
                    OptimizedFileReader
                )
                cache_config = FileContentCacheConfig(
                    max_cache_size_mb=self.config.file_cache_size_mb,
                    max_entries=self.config.file_cache_max_entries
                )
                self.file_cache = FileContentCache(cache_config)
                self.file_reader = OptimizedFileReader(self.file_cache, cache_config)
            except Exception as e:
                self.logger = logging.getLogger(self.__class__.__name__)
                self.logger.warning(f"Failed to initialize FileContentCache: {e}. Falling back to standard reads.")
                self.file_cache = None
                self.file_reader = None
        
        # Logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging"""
        log_level = getattr(logging, self.config.log_level, logging.INFO)
        
        if self.config.log_file:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                handlers=[
                    logging.FileHandler(self.config.log_file),
                    logging.StreamHandler()
                ]
            )
        else:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            )
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def start(self) -> bool:
        """
        Start the autonomous daemon
        
        Returns:
            True if started successfully, False otherwise
        """
        with self._lock:
            if self.state != DaemonState.STOPPED:
                self.logger.warning(f"Cannot start daemon in state {self.state}")
                return False
            
            try:
                self._set_state(DaemonState.INITIALIZING)
                self._start_time = time.time()
                start_ms = time.time() * 1000
                
                # Phase 1: Initialize project
                if not self._initialize_project():
                    self._set_state(DaemonState.ERROR)
                    return False
                
                self.metrics.startup_time_ms = (time.time() * 1000) - start_ms
                
                # Phase 2: Start file monitoring
                self._start_file_monitoring()
                
                # Phase 3: Ready for commands
                self._set_state(DaemonState.READY)
                self._set_state(DaemonState.MONITORING)
                
                # Start reindex worker
                self._reindex_running = True
                self._reindex_thread = threading.Thread(target=self._reindex_worker, daemon=True)
                self._reindex_thread.start()
                
                self.logger.info(f"Daemon started successfully in {self.metrics.startup_time_ms:.0f}ms")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start daemon: {e}", exc_info=True)
                self._set_state(DaemonState.ERROR)
                return False
    
    def stop(self, graceful: bool = True):
        """Stop autonomous daemon"""
        with self._lock:
            if self.state == DaemonState.STOPPED:
                return
            
            self.logger.info(f"Stopping daemon (graceful={graceful})...")
            
            # Stop reindex worker
            self._reindex_running = False
            if self._reindex_thread and graceful:
                self._reindex_thread.join(timeout=2)
            
            # Stop file monitoring
            if self._observer:
                self._observer.stop()
                if graceful:
                    self._observer.join(timeout=2)
            
            # Save checkpoint
            if graceful:
                self._save_checkpoint()
            
            self._set_state(DaemonState.STOPPED)
            self.logger.info("Daemon stopped")
    
    def _initialize_project(self) -> bool:
        """
        Phase 1: Full project scan and indexing
        """
        try:
            self.logger.info(f"Starting project initialization from {self.config.project_root}")
            
            # Create vault directory
            self.config.vault_path.mkdir(parents=True, exist_ok=True)
            
            # Scan project
            if not self._scan_incremental(None):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Project initialization failed: {e}", exc_info=True)
            return False
    
    def _scan_incremental(self, checkpoint: Optional[Dict[str, Any]]) -> bool:
        """Scan with optional checkpoint"""
        try:
            indexed_documents: List[Dict[str, Any]] = []
            for file_path in self.config.project_root.rglob('*'):
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in self.config.file_extensions:
                    continue

                if self._should_ignore(file_path) and not self._is_allowed_service_file(file_path):
                    continue

                content = self._read_indexable_file(file_path)
                if content is None:
                    continue

                relative_path = str(file_path.relative_to(self.config.project_root))
                file_name = file_path.name

                indexed_documents.append({
                    'file_path': str(file_path),
                    'relative_path': relative_path,
                    'file_name': file_name,
                    'suffix': file_path.suffix.lower(),
                    'size': file_path.stat().st_size,
                    'content': content,
                    'content_lower': content.lower(),
                    'normalized_content': self._normalize_search_text(content),
                    'normalized_path': self._normalize_search_text(relative_path),
                    'normalized_file_name': self._normalize_search_text(file_name),
                    'modified_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
            
            self._search_index = indexed_documents
            count = len(indexed_documents)
            self.metrics.total_files_scanned = count
            self.metrics.total_files_indexed = count
            self._save_search_index_metadata()
            
            self.logger.info(f"Scanned {count} files")
            return True
            
        except Exception as e:
            self.logger.error(f"Scan failed: {e}")
            return False

    def _should_ignore(self, file_path: Path) -> bool:
        """Return True when file matches configured ignore patterns."""
        try:
            relative = file_path.relative_to(self.config.project_root).as_posix()
        except ValueError:
            relative = file_path.as_posix()

        for pattern in self.config.scan_ignore_patterns:
            normalized = pattern.replace('\\', '/').strip()
            if not normalized:
                continue

            directory_pattern = normalized.endswith('/')
            normalized = normalized.rstrip('/')

            if directory_pattern and (
                relative == normalized or relative.startswith(normalized + '/') or f'/{normalized}/' in f'/{relative}'
            ):
                return True

            if fnmatch.fnmatch(relative, normalized) or fnmatch.fnmatch(file_path.name, normalized):
                return True

            if f'/{normalized}/' in f'/{relative}' or relative.startswith(normalized + '/'):
                return True

        return False

    def _is_allowed_service_file(self, file_path: Path) -> bool:
        """Allow selected service files even when their directory is ignored."""
        try:
            relative = file_path.relative_to(self.config.project_root).as_posix().lower()
        except ValueError:
            return False

        return relative == '.bober-drive/config.json'

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        """Normalize separators so foo_bar, foo-bar and foo.bar match foo bar."""
        normalized = value.lower()
        for separator in ('_', '-', '.', '/', '\\'):
            normalized = normalized.replace(separator, ' ')
        return ' '.join(normalized.split())

    def _read_indexable_file(self, file_path: Path) -> Optional[str]:
        """Read text file content for local search index."""
        try:
            if self.file_reader:
                cached = self.file_reader.read_optimized(file_path)
                if cached:
                    return cached[0]

            return file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            self.logger.debug(f"Skipping unreadable file {file_path}: {e}")
            return None

    def _save_search_index_metadata(self):
        """Persist lightweight index metadata for verification and restart diagnostics."""
        try:
            index_path = self.config.vault_path
            if index_path.suffix:
                index_path.parent.mkdir(parents=True, exist_ok=True)
                metadata_path = index_path.with_suffix(index_path.suffix + '.json')
            else:
                index_path.mkdir(parents=True, exist_ok=True)
                metadata_path = index_path / 'search_index.json'

            payload = {
                'project_root': str(self.config.project_root),
                'indexed_files': len(self._search_index),
                'updated_at': datetime.now().isoformat(),
                'files': [
                    {
                        'file_path': item['file_path'],
                        'relative_path': item['relative_path'],
                        'file_name': item['file_name'],
                        'suffix': item['suffix'],
                        'size': item['size'],
                        'modified_at': item['modified_at']
                    }
                    for item in self._search_index
                ]
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save search index metadata: {e}")
    
    def _resume_from_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """Resume from checkpoint"""
        return True
    
    def _start_file_monitoring(self):
        """Phase 2: Start file system monitoring"""
        if not self.config.enable_file_watch or not WATCHDOG_AVAILABLE:
            self.logger.info("File watching disabled or watchdog unavailable")
            return
        
        try:
            self._observer = Observer()
            self._file_handler = FileChangeHandler(self, self.config.file_extensions)
            self._observer.schedule(self._file_handler, str(self.config.project_root), recursive=True)
            self._observer.start()
            self.logger.info("File monitoring started")
        except Exception as e:
            self.logger.warning(f"File monitoring failed: {e}")
    
    def _queue_reindex(self, file_path: str):
        """Queue file for reindexing"""
        with self._reindex_lock:
            self._reindex_queue[file_path] = time.time()
    
    def _reindex_worker(self):
        """Background worker for reindexing"""
        debounce_delay = self.config.reindex_debounce_ms / 1000.0
        
        while self._reindex_running:
            try:
                time.sleep(0.1)
                
                now = time.time()
                expired_debounces = [
                    fp for fp, t in self._reindex_debounce.items()
                    if (now - t) > debounce_delay
                ]
                
                # Process expired files
                with self._reindex_lock:
                    for fp in expired_debounces:
                        if fp in self._reindex_queue:
                            del self._reindex_queue[fp]
                        if fp in self._reindex_debounce:
                            del self._reindex_debounce[fp]
                    
                    batch = list(self._reindex_queue.keys())[:self.config.reindex_batch_size]
                    self.metrics.reindex_queue_size = len(self._reindex_queue)
                
                # Reindex batch
                for fp in batch:
                    self._reindex_single_file(fp)
                
            except Exception as e:
                self.logger.error(f"Reindex worker error: {e}", exc_info=True)
    
    def _reindex_single_file(self, file_path: str):
        """Reindex single changed file"""
        try:
            self.metrics.total_files_reindexed += 1
        except Exception as e:
            self.logger.warning(f"Failed to reindex {file_path}: {e}")
    
    def _set_state(self, new_state: DaemonState):
        """Update daemon state"""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self.logger.debug(f"State transition: {old_state.value} -> {new_state.value}")
    
    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint from disk"""
        try:
            if self.config.checkpoint_path.exists():
                with open(self.config.checkpoint_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")
        
        return None
    
    def _save_checkpoint(self):
        """Save checkpoint to disk"""
        try:
            self.config.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'metrics': asdict(self.metrics),
                'scanned_files': self.metrics.total_files_scanned
            }
            
            with open(self.config.checkpoint_path, 'w') as f:
                json.dump(checkpoint, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Search API for autonomous agent
        
        Returns search results or empty dict if not ready
        """
        try:
            if self.state == DaemonState.ERROR:
                return {'error': 'Daemon in error state'}
            
            self.metrics.search_queries += 1
            self.metrics.active_searches += 1
            
            search_start = time.time()
            
            query_lower = query.lower().strip()
            normalized_query = self._normalize_search_text(query)
            query_terms = [term for term in normalized_query.split() if term]
            hits: List[Dict[str, Any]] = []

            if query_terms:
                for item in self._search_index:
                    haystack = item['content_lower']
                    path_lower = item['relative_path'].lower()
                    file_name_lower = item['file_name'].lower()
                    normalized_content = item['normalized_content']
                    normalized_path = item['normalized_path']
                    normalized_file_name = item['normalized_file_name']
                    score = 0.0

                    if query_lower in haystack:
                        score += 10.0
                    if query_lower in path_lower:
                        score += 25.0
                    if query_lower in file_name_lower:
                        score += 60.0

                    if normalized_query and normalized_query in normalized_content:
                        score += 12.0
                    if normalized_query and normalized_query in normalized_path:
                        score += 35.0
                    if normalized_query and normalized_query in normalized_file_name:
                        score += 90.0

                    for term in query_terms:
                        content_count = normalized_content.count(term)
                        path_count = normalized_path.count(term)
                        file_name_count = normalized_file_name.count(term)
                        score += min(content_count, 20) * 1.0
                        score += path_count * 8.0
                        score += file_name_count * 25.0

                    if all(term in normalized_file_name for term in query_terms):
                        score += 120.0
                    elif all(term in normalized_path for term in query_terms):
                        score += 45.0

                    if score <= 0:
                        continue

                    snippet = self._build_snippet(item['content'], query_terms)
                    hits.append({
                        'file_path': item['file_path'],
                        'relative_path': item['relative_path'],
                        'file_name': item['file_name'],
                        'score': score,
                        'snippet': snippet,
                        'suffix': item['suffix'],
                        'size': item['size'],
                        'modified_at': item['modified_at']
                    })

            hits.sort(key=lambda hit: hit['score'], reverse=True)
            hits = hits[:limit]
            elapsed_ms = (time.time() - search_start) * 1000

            if self.metrics.search_queries:
                previous_total = self.metrics.avg_search_time_ms * (self.metrics.search_queries - 1)
                self.metrics.avg_search_time_ms = (previous_total + elapsed_ms) / self.metrics.search_queries

            results = {
                'query': query,
                'hits': hits,
                'results': hits,
                'count': len(hits),
                'total_indexed': len(self._search_index),
                'time_ms': elapsed_ms
            }
            
            self.metrics.active_searches -= 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {'error': str(e)}

    @staticmethod
    def _build_snippet(content: str, query_terms: List[str], radius: int = 90) -> str:
        """Build a compact snippet around the first matched query term."""
        content_lower = content.lower()
        positions = [content_lower.find(term) for term in query_terms if term and content_lower.find(term) >= 0]
        if not positions:
            return content[:radius * 2].replace('\n', ' ').strip()

        pos = min(positions)
        start = max(0, pos - radius)
        end = min(len(content), pos + radius)
        snippet = content[start:end].replace('\n', ' ').strip()
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet += '...'
        return snippet
    
    def _get_cached_file_content(self, file_path: str) -> Optional[str]:
        """
        Get file content with cache-first strategy (v3.0.1+)
        
        Returns None if file not found or not supported format
        """
        if not self.file_reader:
            # Fallback to direct read if cache not available
            try:
                return Path(file_path).read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                self.logger.debug(f"Failed to read {file_path}: {e}")
                return None
        
        try:
            result = self.file_reader.read_optimized(Path(file_path))
            return result[0] if result else None
        except Exception as e:
            self.logger.debug(f"Cache read failed for {file_path}, fallback to direct: {e}")
            try:
                return Path(file_path).read_text(encoding='utf-8', errors='replace')
            except:
                return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get file cache statistics (v3.0.1+)"""
        if not self.file_cache:
            return {'cache_enabled': False}
        
        return {
            'cache_enabled': True,
            **self.file_cache.get_stats(),
            'reader_stats': self.file_reader.get_stats() if self.file_reader else {}
        }
    
    
    def get_status(self) -> Dict[str, Any]:
        """Get daemon status"""
        with self._lock:
            uptime = (time.time() - self._start_time) if self._start_time else 0.0
            
            status = {
                'state': self.state.value,
                'uptime': uptime,
                'startup_time_ms': self.metrics.startup_time_ms,
                'files_scanned': self.metrics.total_files_scanned,
                'files_indexed': self.metrics.total_files_indexed,
                'watchdog_available': WATCHDOG_AVAILABLE,
                'file_cache_enabled': self.config.enable_file_cache
            }
            
            # Add cache stats if enabled
            if self.file_cache:
                cache_stats = self.file_cache.get_stats()
                status['cache_stats'] = cache_stats
            
            return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get daemon metrics"""
        with self._lock:
            metrics_dict = asdict(self.metrics)
            
            # Add file cache metrics
            if self.file_reader:
                reader_stats = self.file_reader.get_stats()
                metrics_dict['file_cache'] = {
                    'cache_hits': reader_stats.get('cache_hits', 0),
                    'total_reads': reader_stats.get('total_reads', 0),
                    'cache_hit_rate_pct': reader_stats.get('cache_hit_rate_pct', 0),
                    'avg_read_time_ms': reader_stats.get('avg_read_time_ms', 0)
                }
            
            return metrics_dict


def create_autonomous_daemon(
    project_root: Path,
    vault_path: Path,
    enable_file_watch: bool = True,
    init_strategy: InitStrategy = InitStrategy.FULL_SCAN,
    checkpoint_path: Optional[Path] = None,
    file_extensions: Optional[List[str]] = None,
    ignore_patterns: Optional[List[str]] = None
) -> NexusAutonomousDaemon:
    """Factory function to create autonomous daemon"""
    
    if checkpoint_path is None:
        checkpoint_path = Path.home() / ".bober" / "daemon.checkpoint"
    
    config = DaemonConfig(
        project_root=Path(project_root),
        vault_path=Path(vault_path),
        checkpoint_path=checkpoint_path,
        enable_file_watch=enable_file_watch,
        init_strategy=init_strategy,
        file_extensions=file_extensions or ['.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.py'],
        scan_ignore_patterns=ignore_patterns or ['.git', '__pycache__', '.env', '.nexus', 'storage', '.agent', '.bober-drive']
    )
    
    try:
        # Try to create orchestrator (optional)
        try:
            from nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig
            
            nexus_config = NexusConfig(
                project_root=config.project_root,
                vault_path=config.vault_path,
                enable_events=True,
                enable_auto_update=False,
                enable_caching=True
            )
            
            orchestrator = create_nexus_orchestrator(
                project_root=config.project_root,
                vault_path=config.vault_path,
                enable_auto_update=False
            )
        except Exception as e:
            logging.warning(f"Failed to create orchestrator: {e}")
            orchestrator = None
        
        return NexusAutonomousDaemon(config, orchestrator)
        
    except Exception as e:
        logging.error(f"Failed to create autonomous daemon: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # Demo usage
    test_root = Path.home() / ".bober_test"
    vault_root = test_root / "vault"
    
    daemon = create_autonomous_daemon(test_root, vault_root)
    
    try:
        daemon.start()
        time.sleep(2)
        
        # Test search
        results = daemon.search("test")
        print(f"Search results: {results}")
        
        # Get status
        status = daemon.get_status()
        print(f"Status: {status}")
        
        # Get metrics
        metrics = daemon.get_metrics()
        print(f"Metrics: {metrics}")
        
        time.sleep(1)
        
    finally:
        daemon.stop()
