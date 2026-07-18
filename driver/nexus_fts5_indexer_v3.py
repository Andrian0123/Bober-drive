#!/usr/bin/env python3
"""
FTS5IndexerV3 - Phase 4 Implementation
Event-driven full-text search engine with lifecycle event emission, local subscribers,
history tracking, and backward compatibility with VaultFTS5Extension.

Architecture:
- Inherits from VaultFTS5Extension for 100% API compatibility
- Emits events: SearchIndexRequested, SearchIndexed, SearchExecuted, SearchCompleted, SearchFailed
- Local subscribers (on_search_indexed, on_search_executed, on_search_completed, on_search_failed)
- Search history (max 1000 items)
- Stats: total searches, by type, avg duration, total hits, index size
- Config: enable_events, async_event_processing, track_search_history
"""

import sqlite3
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from vault_fts5_extension import VaultFTS5Extension
from core.event_bus import (
    Event, 
    EventBus,
    SearchEvent
)

logger = logging.getLogger(__name__)


# ============================================================================
# EVENT DEFINITIONS (FTS5Indexer-specific lifecycle events)
# ============================================================================

class SearchIndexRequested(SearchEvent):
    """Emitted when search indexing is requested"""
    def __init__(self, index_id: str, query: str, search_type: str = "fts5", **kwargs):
        super().__init__()
        self.index_id = index_id
        self.query = query
        self.search_type = search_type
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "index_id": self.index_id,
            "query": self.query,
            "search_type": self.search_type,
            "timestamp": self.timestamp
        })
        return d


class SearchIndexed(SearchEvent):
    """Emitted when search is indexed and ready"""
    def __init__(self, index_id: str, query: str, indexed_count: int, **kwargs):
        super().__init__()
        self.index_id = index_id
        self.query = query
        self.indexed_count = indexed_count
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "index_id": self.index_id,
            "query": self.query,
            "indexed_count": self.indexed_count,
            "timestamp": self.timestamp
        })
        return d


class SearchExecuted(SearchEvent):
    """Emitted when search is executed"""
    def __init__(self, search_id: str, query: str, result_count: int, elapsed_ms: float, **kwargs):
        super().__init__()
        self.search_id = search_id
        self.query = query
        self.result_count = result_count
        self.elapsed_ms = elapsed_ms
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "search_id": self.search_id,
            "query": self.query,
            "result_count": self.result_count,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp
        })
        return d


class SearchCompleted(SearchEvent):
    """Emitted when search completes successfully"""
    def __init__(self, search_id: str, query: str, result_count: int, elapsed_ms: float, **kwargs):
        super().__init__()
        self.search_id = search_id
        self.query = query
        self.result_count = result_count
        self.elapsed_ms = elapsed_ms
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "search_id": self.search_id,
            "query": self.query,
            "result_count": self.result_count,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp
        })
        return d


class SearchFailed(SearchEvent):
    """Emitted when search fails"""
    def __init__(self, search_id: str, query: str, error: str, **kwargs):
        super().__init__()
        self.search_id = search_id
        self.query = query
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "search_id": self.search_id,
            "query": self.query,
            "error": self.error,
            "timestamp": self.timestamp
        })
        return d


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class FTS5IndexerV3Config:
    """Configuration for FTS5IndexerV3"""
    enable_events: bool = True
    async_event_processing: bool = False
    track_search_history: bool = True
    max_search_history: int = 1000
    event_bus: Optional[EventBus] = None

    def __repr__(self) -> str:
        return (f"FTS5IndexerV3Config(enable_events={self.enable_events}, "
                f"async={self.async_event_processing}, "
                f"track_history={self.track_search_history}, "
                f"max_history={self.max_search_history})")


# ============================================================================
# MAIN ENGINE
# ============================================================================

class FTS5IndexerV3(VaultFTS5Extension):
    """
    Event-driven full-text search engine.
    Inherits from VaultFTS5Extension, adds event emission and history tracking.
    """
    
    def __init__(self, db_path: Path, config: Optional[FTS5IndexerV3Config] = None):
        """
        Initialize FTS5IndexerV3
        
        Args:
            db_path: Path to Vault SQLite database
            config: FTS5IndexerV3Config (default: standard config)
        """
        super().__init__(db_path)
        
        self.config = config or FTS5IndexerV3Config()
        self._event_bus = self.config.event_bus
        
        # Local subscribers (name -> list of (subscription_id, handler))
        self._subscribers: Dict[str, List[Tuple[str, Callable]]] = {
            "search_indexed": [],
            "search_executed": [],
            "search_completed": [],
            "search_failed": [],
            "search_index_requested": []
        }
        self._subscribers_lock = threading.RLock()
        
        # History tracking
        self.search_history: List[Dict[str, Any]] = []
        self._history_lock = threading.RLock()
        
        # Statistics
        self._stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "total_hits": 0,
            "avg_search_duration_ms": 0.0,
            "search_durations": [],  # For computing avg
            "search_types": {},  # Count by type (fts5, like, regex)
            "index_size_bytes": 0,
        }
        self._stats_lock = threading.RLock()
        
        logger.info(f"FTS5IndexerV3 initialized with config: {self.config}")
    
    # ========================================================================
    # EVENT EMISSION
    # ========================================================================
    
    def _emit_search_index_requested(self, query: str, search_type: str) -> None:
        """Emit SearchIndexRequested event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        index_id = str(uuid4())
        event = SearchIndexRequested(index_id=index_id, query=query, search_type=search_type)
        
        try:
            if self._event_bus:
                self._event_bus.publish(event, async_mode=self.config.async_event_processing)
            
            # Call local subscribers
            with self._subscribers_lock:
                for subscription_id, handler in self._subscribers["search_index_requested"]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error calling search_index_requested handler: {e}")
        
        except Exception as e:
            logger.error(f"Error emitting SearchIndexRequested: {e}")
    
    def _emit_search_indexed(self, query: str, indexed_count: int) -> None:
        """Emit SearchIndexed event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        index_id = str(uuid4())
        event = SearchIndexed(index_id=index_id, query=query, indexed_count=indexed_count)
        
        try:
            if self._event_bus:
                self._event_bus.publish(event, async_mode=self.config.async_event_processing)
            
            # Call local subscribers
            with self._subscribers_lock:
                for subscription_id, handler in self._subscribers["search_indexed"]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error calling search_indexed handler: {e}")
        
        except Exception as e:
            logger.error(f"Error emitting SearchIndexed: {e}")
    
    def _emit_search_executed(self, query: str, result_count: int, elapsed_ms: float) -> None:
        """Emit SearchExecuted event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        search_id = str(uuid4())
        event = SearchExecuted(search_id=search_id, query=query, result_count=result_count, elapsed_ms=elapsed_ms)
        
        try:
            if self._event_bus:
                self._event_bus.publish(event, async_mode=self.config.async_event_processing)
            
            # Call local subscribers
            with self._subscribers_lock:
                for subscription_id, handler in self._subscribers["search_executed"]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error calling search_executed handler: {e}")
        
        except Exception as e:
            logger.error(f"Error emitting SearchExecuted: {e}")
    
    def _emit_search_completed(self, query: str, result_count: int, elapsed_ms: float) -> None:
        """Emit SearchCompleted event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        search_id = str(uuid4())
        event = SearchCompleted(search_id=search_id, query=query, result_count=result_count, elapsed_ms=elapsed_ms)
        
        try:
            if self._event_bus:
                self._event_bus.publish(event, async_mode=self.config.async_event_processing)
            
            # Call local subscribers
            with self._subscribers_lock:
                for subscription_id, handler in self._subscribers["search_completed"]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error calling search_completed handler: {e}")
        
        except Exception as e:
            logger.error(f"Error emitting SearchCompleted: {e}")
    
    def _emit_search_failed(self, query: str, error: str) -> None:
        """Emit SearchFailed event to EventBus and local subscribers"""
        if not self.config.enable_events:
            return
        
        search_id = str(uuid4())
        event = SearchFailed(search_id=search_id, query=query, error=error)
        
        try:
            if self._event_bus:
                self._event_bus.publish(event, async_mode=self.config.async_event_processing)
            
            # Call local subscribers
            with self._subscribers_lock:
                for subscription_id, handler in self._subscribers["search_failed"]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error calling search_failed handler: {e}")
        
        except Exception as e:
            logger.error(f"Error emitting SearchFailed: {e}")
    
    # ========================================================================
    # LOCAL SUBSCRIBERS (on_* methods)
    # ========================================================================
    
    def on_search_indexed(self, handler: Callable) -> str:
        """Subscribe to SearchIndexed events (local, no EventBus required)"""
        subscription_id = str(uuid4())
        with self._subscribers_lock:
            self._subscribers["search_indexed"].append((subscription_id, handler))
        return subscription_id
    
    def on_search_executed(self, handler: Callable) -> str:
        """Subscribe to SearchExecuted events (local, no EventBus required)"""
        subscription_id = str(uuid4())
        with self._subscribers_lock:
            self._subscribers["search_executed"].append((subscription_id, handler))
        return subscription_id
    
    def on_search_completed(self, handler: Callable) -> str:
        """Subscribe to SearchCompleted events (local, no EventBus required)"""
        subscription_id = str(uuid4())
        with self._subscribers_lock:
            self._subscribers["search_completed"].append((subscription_id, handler))
        return subscription_id
    
    def on_search_failed(self, handler: Callable) -> str:
        """Subscribe to SearchFailed events (local, no EventBus required)"""
        subscription_id = str(uuid4())
        with self._subscribers_lock:
            self._subscribers["search_failed"].append((subscription_id, handler))
        return subscription_id
    
    def on_search_index_requested(self, handler: Callable) -> str:
        """Subscribe to SearchIndexRequested events (local, no EventBus required)"""
        subscription_id = str(uuid4())
        with self._subscribers_lock:
            self._subscribers["search_index_requested"].append((subscription_id, handler))
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from all local events by subscription ID"""
        with self._subscribers_lock:
            found = False
            for event_type in self._subscribers:
                original_len = len(self._subscribers[event_type])
                self._subscribers[event_type] = [
                    (sub_id, handler) for sub_id, handler in self._subscribers[event_type]
                    if sub_id != subscription_id
                ]
                if len(self._subscribers[event_type]) < original_len:
                    found = True
            return found
    
    # ========================================================================
    # OVERRIDDEN SEARCH METHODS (with event emission)
    # ========================================================================
    
    def fulltext_search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform full-text search with event emission
        
        Args:
            query: Search query (supports FTS5 syntax)
            limit: Maximum results
            
        Returns:
            List of matching entries
        """
        import time
        
        self._emit_search_index_requested(query, "fts5")
        start_time = time.time()
        
        try:
            # Call parent implementation
            results = super().fulltext_search(query, limit)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit events
            self._emit_search_executed(query, len(results), elapsed_ms)
            self._emit_search_completed(query, len(results), elapsed_ms)
            
            # Track search (updates stats and history)
            self._track_search(
                query=query,
                search_type="fts5",
                result_count=len(results),
                elapsed_ms=elapsed_ms,
                success=True
            )
            
            return results
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            self._emit_search_failed(query, error_msg)
            
            # Track failed search (updates stats and history)
            self._track_search(
                query=query,
                search_type="fts5",
                result_count=0,
                elapsed_ms=elapsed_ms,
                success=False,
                error=error_msg
            )
            
            logger.error(f"FTS5 search failed: {e}")
            raise
    
    def regex_search(self, pattern: str, fields: Optional[List[str]] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search using regex patterns with event emission
        
        Args:
            pattern: Regex pattern
            fields: Fields to search
            limit: Maximum results
            
        Returns:
            List of matching entries
        """
        import time
        
        query = f"regex:{pattern}"
        self._emit_search_index_requested(query, "regex")
        start_time = time.time()
        
        try:
            # Call parent implementation
            results = super().regex_search(pattern, fields, limit)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit events
            self._emit_search_executed(query, len(results), elapsed_ms)
            self._emit_search_completed(query, len(results), elapsed_ms)
            
            # Track search (updates stats and history)
            self._track_search(
                query=query,
                search_type="regex",
                result_count=len(results),
                elapsed_ms=elapsed_ms,
                success=True
            )
            
            return results
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            self._emit_search_failed(query, error_msg)
            
            # Track failed search (updates stats and history)
            self._track_search(
                query=query,
                search_type="regex",
                result_count=0,
                elapsed_ms=elapsed_ms,
                success=False,
                error=error_msg
            )
            
            logger.error(f"Regex search failed: {e}")
            raise
    
    def advanced_search(self, query: str, search_type: str = "fts5",
                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple strategies and event emission
        
        Args:
            query: Search query
            search_type: 'fts5', 'like', or 'regex'
            limit: Maximum results
            
        Returns:
            List of search results
        """
        import time
        
        self._emit_search_index_requested(query, search_type)
        start_time = time.time()
        
        try:
            # Call parent implementation
            results = super().advanced_search(query, search_type, limit)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit events
            self._emit_search_executed(query, len(results), elapsed_ms)
            self._emit_search_completed(query, len(results), elapsed_ms)
            
            # Track search (updates stats and history)
            self._track_search(
                query=query,
                search_type=search_type,
                result_count=len(results),
                elapsed_ms=elapsed_ms,
                success=True
            )
            
            return results
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            self._emit_search_failed(query, error_msg)
            
            # Track failed search (updates stats and history)
            self._track_search(
                query=query,
                search_type=search_type,
                result_count=0,
                elapsed_ms=elapsed_ms,
                success=False,
                error=error_msg
            )
            
            logger.error(f"Advanced search failed: {e}")
            raise
    
    # ========================================================================
    # HISTORY TRACKING
    # ========================================================================
    
    def _track_search(
        self,
        query: str,
        search_type: str,
        result_count: int,
        elapsed_ms: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Track search in local history for observability"""
        # Track in history
        if self.config.track_search_history:
            with self._history_lock:
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query": query,
                    "search_type": search_type,
                    "result_count": result_count,
                    "elapsed_ms": elapsed_ms,
                    "success": success,
                    "error": error
                }
                self.search_history.append(entry)
                
                # Enforce max history size
                if len(self.search_history) > self.config.max_search_history:
                    self.search_history = self.search_history[-self.config.max_search_history:]
        
        # Update statistics
        with self._stats_lock:
            self._stats["total_searches"] += 1
            if success:
                self._stats["successful_searches"] += 1
                self._stats["total_hits"] += result_count
            else:
                self._stats["failed_searches"] += 1
            
            self._stats["search_durations"].append(elapsed_ms)
            self._stats["search_types"][search_type] = self._stats["search_types"].get(search_type, 0) + 1
            
            # Compute rolling average
            if self._stats["search_durations"]:
                self._stats["avg_search_duration_ms"] = (
                    sum(self._stats["search_durations"]) / len(self._stats["search_durations"])
                )
    
    def get_search_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent search history"""
        with self._history_lock:
            return list(reversed(self.search_history[-limit:]))
    
    def clear_search_history(self) -> None:
        """Clear search history"""
        with self._history_lock:
            self.search_history = []
    
    # ========================================================================
    # STATISTICS & OBSERVABILITY
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self._stats_lock:
            # Compute index size from database
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
                size_result = cursor.fetchone()
                index_size = size_result[0] if size_result else 0
                conn.close()
            except Exception:
                index_size = 0
            
            return {
                "total_searches": self._stats["total_searches"],
                "successful_searches": self._stats["successful_searches"],
                "failed_searches": self._stats["failed_searches"],
                "success_rate": (
                    self._stats["successful_searches"] / self._stats["total_searches"] * 100
                    if self._stats["total_searches"] > 0 else 0.0
                ),
                "total_hits": self._stats["total_hits"],
                "avg_hits_per_search": (
                    self._stats["total_hits"] / self._stats["total_searches"]
                    if self._stats["total_searches"] > 0 else 0.0
                ),
                "avg_search_duration_ms": self._stats["avg_search_duration_ms"],
                "search_types": self._stats["search_types"],
                "index_size_bytes": index_size,
                "search_history_size": len(self.search_history),
                "events_enabled": self.config.enable_events,
                "async_processing": self.config.async_event_processing
            }
    
    def enable_events(self, enabled: bool = True) -> None:
        """Enable or disable event emission"""
        self.config.enable_events = enabled
    
    def set_event_bus(self, event_bus: Optional[EventBus]) -> None:
        """Set central EventBus for publishing events"""
        self._event_bus = event_bus
        self.config.event_bus = event_bus
    
    def __repr__(self) -> str:
        return (f"FTS5IndexerV3(db_path={self.db_path}, "
                f"enable_events={self.config.enable_events}, "
                f"track_history={self.config.track_search_history})")


# ============================================================================
# ADAPTER & FACTORY (for wrapping existing VaultFTS5Extension)
# ============================================================================

class FTS5IndexerAdapter:
    """Adapter for wrapping existing VaultFTS5Extension with V3 features"""
    
    @staticmethod
    def wrap(fts5_engine: VaultFTS5Extension, event_bus: Optional[EventBus] = None) -> FTS5IndexerV3:
        """
        Wrap an existing VaultFTS5Extension instance with V3 features
        
        Args:
            fts5_engine: Existing VaultFTS5Extension
            event_bus: Optional EventBus for publishing events
            
        Returns:
            FTS5IndexerV3 instance wrapping the same database
        """
        config = FTS5IndexerV3Config(event_bus=event_bus)
        v3_engine = FTS5IndexerV3(fts5_engine.db_path, config)
        logger.info(f"Wrapped VaultFTS5Extension with FTS5IndexerV3: {fts5_engine.db_path}")
        return v3_engine
    
    @staticmethod
    def upgrade_path(db_path: Path, event_bus: Optional[EventBus] = None) -> FTS5IndexerV3:
        """
        Direct upgrade path from database to FTS5IndexerV3
        
        Args:
            db_path: Path to Vault database
            event_bus: Optional EventBus
            
        Returns:
            FTS5IndexerV3 instance
        """
        config = FTS5IndexerV3Config(event_bus=event_bus)
        v3_engine = FTS5IndexerV3(db_path, config)
        logger.info(f"Upgraded database to FTS5IndexerV3: {db_path}")
        return v3_engine


def create_fts5_indexer_v3(
    db_path: Path,
    enable_events: bool = True,
    async_events: bool = False,
    event_bus: Optional[EventBus] = None,
    track_history: bool = True,
    max_history: int = 1000
) -> FTS5IndexerV3:
    """
    Factory function to create FTS5IndexerV3 with standard configuration
    
    Args:
        db_path: Path to Vault database
        enable_events: Enable event emission (default: True)
        async_events: Use async event processing (default: False)
        event_bus: Optional EventBus for publishing
        track_history: Enable search history tracking (default: True)
        max_history: Maximum history size (default: 1000)
        
    Returns:
        Configured FTS5IndexerV3 instance
    """
    config = FTS5IndexerV3Config(
        enable_events=enable_events,
        async_event_processing=async_events,
        event_bus=event_bus,
        track_search_history=track_history,
        max_search_history=max_history
    )
    return FTS5IndexerV3(db_path, config)
