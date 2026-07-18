#!/usr/bin/env python3
"""
Trash Manager V3 - Event-Driven Architecture
Manages soft deletes and entry recovery with unified event system

Features:
- Event emission for all trash operations
- Local subscription support (no EventBus required)
- History tracking and statistics
- Backward compatible with TrashManager
- DI Container integration ready

Events:
- EntryTrashed: Emitted when entry is moved to trash
- EntryRestored: Emitted when entry is restored from trash
- EntryPermanentlyDeleted: Emitted when entry is permanently deleted
- TrashCleanupCompleted: Emitted after expired entries cleanup
- TrashOperationFailed: Emitted when operation fails
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from threading import Lock
from collections import deque

# Import parent class and related types
import sys
sys.path.insert(0, str(Path(__file__).parent))

from trash_manager import TrashManager, TrashEntry
from core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


# ===== Event Definitions =====

class TrashEvent(Event):
    """Base class for trash events"""
    def __init__(self, operation_id: str, **kwargs):
        super().__init__()
        self.operation_id = operation_id
        self.metadata.update(kwargs)


class EntryTrashed(TrashEvent):
    """Emitted when entry is moved to trash"""
    def __init__(self, operation_id: str, trash_id: str, entry_id: str, entry_type: str, **kwargs):
        super().__init__(operation_id, **kwargs)
        self.trash_id = trash_id
        self.entry_id = entry_id
        self.entry_type = entry_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "operation_id": self.operation_id,
            "trash_id": self.trash_id,
            "entry_id": self.entry_id,
            "entry_type": self.entry_type
        }


class EntryRestored(TrashEvent):
    """Emitted when entry is restored from trash"""
    def __init__(self, operation_id: str, trash_id: str, entry_id: str, **kwargs):
        super().__init__(operation_id, **kwargs)
        self.trash_id = trash_id
        self.entry_id = entry_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "operation_id": self.operation_id,
            "trash_id": self.trash_id,
            "entry_id": self.entry_id
        }


class EntryPermanentlyDeleted(TrashEvent):
    """Emitted when entry is permanently deleted"""
    def __init__(self, operation_id: str, trash_id: str, forced: bool, **kwargs):
        super().__init__(operation_id, **kwargs)
        self.trash_id = trash_id
        self.forced = forced
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "operation_id": self.operation_id,
            "trash_id": self.trash_id,
            "forced": self.forced
        }


class TrashCleanupCompleted(TrashEvent):
    """Emitted after cleanup of expired entries"""
    def __init__(self, operation_id: str, deleted_count: int, failed_count: int, **kwargs):
        super().__init__(operation_id, **kwargs)
        self.deleted_count = deleted_count
        self.failed_count = failed_count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "operation_id": self.operation_id,
            "deleted_count": self.deleted_count,
            "failed_count": self.failed_count
        }


class TrashOperationFailed(TrashEvent):
    """Emitted when trash operation fails"""
    def __init__(self, operation_id: str, operation_type: str, error: str, **kwargs):
        super().__init__(operation_id, **kwargs)
        self.operation_type = operation_type
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "error": self.error
        }


# ===== Configuration =====

@dataclass
class TrashManagerV3Config:
    """Configuration for TrashManagerV3"""
    enable_events: bool = True
    max_history: int = 1000


# ===== Main Class =====

class TrashManagerV3(TrashManager):
    """
    Trash Manager V3 with Event-Driven Architecture
    
    Extends TrashManager with:
    - Event emission for all operations
    - Local subscription support
    - History tracking
    - Statistics and observability
    - EventBus integration
    
    Usage:
        trash = TrashManagerV3(db_path, event_bus)
        
        # Subscribe locally
        trash.on_entry_trashed(lambda evt: print(f"Trashed: {evt.entry_id}"))
        
        # Soft delete
        trash_id = trash.soft_delete(entry_id, content, entry_type)
    """
    
    def __init__(
        self,
        db_path: Path,
        event_bus: Optional[EventBus] = None,
        config: Optional[TrashManagerV3Config] = None
    ):
        super().__init__(db_path)
        
        self.config = config or TrashManagerV3Config()
        self._event_bus = event_bus
        
        # Local subscribers
        self._subscribers: Dict[str, List[tuple]] = {
            "entry_trashed": [],
            "entry_restored": [],
            "entry_permanently_deleted": [],
            "cleanup_completed": [],
            "operation_failed": []
        }
        self._subscribers_lock = Lock()
        
        # History tracking
        self._operation_history: deque = deque(maxlen=self.config.max_history)
        self._history_lock = Lock()
        
        # Statistics
        self._stats = {
            "total_trashed": 0,
            "total_restored": 0,
            "total_permanent_deletes": 0,
            "total_cleanups": 0,
            "failed_operations": 0
        }
        self._stats_lock = Lock()
        
        logger.info(f"TrashManagerV3 initialized with events={'enabled' if self.config.enable_events else 'disabled'}")
    
    # ===== Core Methods Override =====
    
    def soft_delete(
        self,
        entry_id: str,
        content: bytes,
        entry_type: str,
        title: str,
        reason: str = "user_delete",
        deleted_by: str = "system",
        ttl_hours: int = 720
    ) -> Optional[str]:
        """Soft delete with event emission"""
        operation_id = str(uuid.uuid4())
        
        try:
            # Perform soft delete
            trash_id = super().soft_delete(entry_id, content, entry_type, title, reason, deleted_by, ttl_hours)
            
            # Emit event
            self._emit_entry_trashed(operation_id, trash_id, entry_id, entry_type)
            
            # Track operation
            self._track_operation(operation_id, "soft_delete", True, trash_id=trash_id, entry_id=entry_id)
            
            return trash_id
            
        except Exception as e:
            error_str = str(e)
            self._emit_operation_failed(operation_id, "soft_delete", error_str)
            self._track_operation(operation_id, "soft_delete", False, error=error_str)
            raise
    
    def restore_from_trash(self, trash_id: str) -> Optional[Dict[str, Any]]:
        """Restore entry with event emission"""
        operation_id = str(uuid.uuid4())
        
        try:
            # Perform restore
            result = super().restore_from_trash(trash_id)
            
            if result:
                entry_id = result.get("entry_id", "unknown")
                self._emit_entry_restored(operation_id, trash_id, entry_id)
                self._track_operation(operation_id, "restore", True, trash_id=trash_id, entry_id=entry_id)
            
            return result
            
        except Exception as e:
            error_str = str(e)
            self._emit_operation_failed(operation_id, "restore", error_str)
            self._track_operation(operation_id, "restore", False, error=error_str)
            raise
    
    def permanent_delete(self, trash_id: str, force: bool = False) -> bool:
        """Permanent delete with event emission"""
        operation_id = str(uuid.uuid4())
        
        try:
            # Perform permanent delete
            result = super().permanent_delete(trash_id, force)
            
            if result:
                self._emit_entry_permanently_deleted(operation_id, trash_id, force)
                self._track_operation(operation_id, "permanent_delete", True, trash_id=trash_id)
            
            return result
            
        except Exception as e:
            error_str = str(e)
            self._emit_operation_failed(operation_id, "permanent_delete", error_str)
            self._track_operation(operation_id, "permanent_delete", False, error=error_str)
            raise
    
    def cleanup_expired_entries(self) -> Tuple[int, int]:
        """Cleanup with event emission"""
        operation_id = str(uuid.uuid4())
        
        try:
            # Perform cleanup
            deleted_count, failed_count = super().cleanup_expired_entries()
            
            # Emit event
            self._emit_cleanup_completed(operation_id, deleted_count, failed_count)
            
            # Track operation
            self._track_operation(
                operation_id,
                "cleanup",
                True,
                deleted_count=deleted_count,
                failed_count=failed_count
            )
            
            return deleted_count, failed_count
            
        except Exception as e:
            error_str = str(e)
            self._emit_operation_failed(operation_id, "cleanup", error_str)
            self._track_operation(operation_id, "cleanup", False, error=error_str)
            raise
    
    # ===== Event Emission =====
    
    def _emit_entry_trashed(self, operation_id: str, trash_id: str, entry_id: str, entry_type: str) -> None:
        """Emit EntryTrashed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = EntryTrashed(operation_id, trash_id, entry_id, entry_type)
            
            # Publish to EventBus
            if self._event_bus:
                self._event_bus.publish(event)
            
            # Notify local subscribers
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("entry_trashed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in entry_trashed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit EntryTrashed: {e}")
    
    def _emit_entry_restored(self, operation_id: str, trash_id: str, entry_id: str) -> None:
        """Emit EntryRestored event"""
        if not self.config.enable_events:
            return
        
        try:
            event = EntryRestored(operation_id, trash_id, entry_id)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("entry_restored", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in entry_restored handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit EntryRestored: {e}")
    
    def _emit_entry_permanently_deleted(self, operation_id: str, trash_id: str, forced: bool) -> None:
        """Emit EntryPermanentlyDeleted event"""
        if not self.config.enable_events:
            return
        
        try:
            event = EntryPermanentlyDeleted(operation_id, trash_id, forced)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("entry_permanently_deleted", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in entry_permanently_deleted handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit EntryPermanentlyDeleted: {e}")
    
    def _emit_cleanup_completed(self, operation_id: str, deleted_count: int, failed_count: int) -> None:
        """Emit TrashCleanupCompleted event"""
        if not self.config.enable_events:
            return
        
        try:
            event = TrashCleanupCompleted(operation_id, deleted_count, failed_count)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("cleanup_completed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in cleanup_completed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit TrashCleanupCompleted: {e}")
    
    def _emit_operation_failed(self, operation_id: str, operation_type: str, error: str) -> None:
        """Emit TrashOperationFailed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = TrashOperationFailed(operation_id, operation_type, error)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("operation_failed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in operation_failed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit TrashOperationFailed: {e}")
    
    # ===== Local Subscriptions =====
    
    def on_entry_trashed(self, handler: Callable) -> str:
        """Subscribe to entry trashed events"""
        return self._subscribe("entry_trashed", handler)
    
    def on_entry_restored(self, handler: Callable) -> str:
        """Subscribe to entry restored events"""
        return self._subscribe("entry_restored", handler)
    
    def on_entry_permanently_deleted(self, handler: Callable) -> str:
        """Subscribe to permanent delete events"""
        return self._subscribe("entry_permanently_deleted", handler)
    
    def on_cleanup_completed(self, handler: Callable) -> str:
        """Subscribe to cleanup completed events"""
        return self._subscribe("cleanup_completed", handler)
    
    def on_operation_failed(self, handler: Callable) -> str:
        """Subscribe to operation failed events"""
        return self._subscribe("operation_failed", handler)
    
    def _subscribe(self, event_type: str, handler: Callable) -> str:
        """Internal subscription helper"""
        subscription_id = str(uuid.uuid4())
        with self._subscribers_lock:
            self._subscribers[event_type].append((handler, subscription_id))
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from all events by subscription ID"""
        with self._subscribers_lock:
            for event_type in self._subscribers:
                self._subscribers[event_type] = [
                    (h, sid) for h, sid in self._subscribers[event_type]
                    if sid != subscription_id
                ]
            return True
    
    # ===== History & Statistics =====
    
    def _track_operation(
        self,
        operation_id: str,
        operation_type: str,
        success: bool,
        **kwargs
    ) -> None:
        """Track operation in history"""
        with self._history_lock:
            self._operation_history.append({
                "operation_id": operation_id,
                "operation_type": operation_type,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                **kwargs
            })
        
        with self._stats_lock:
            if success:
                if operation_type == "soft_delete":
                    self._stats["total_trashed"] += 1
                elif operation_type == "restore":
                    self._stats["total_restored"] += 1
                elif operation_type == "permanent_delete":
                    self._stats["total_permanent_deletes"] += 1
                elif operation_type == "cleanup":
                    self._stats["total_cleanups"] += 1
            else:
                self._stats["failed_operations"] += 1
    
    def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent operation history"""
        with self._history_lock:
            return list(self._operation_history)[-limit:]
    
    def clear_operation_history(self) -> None:
        """Clear operation history"""
        with self._history_lock:
            self._operation_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self._stats_lock:
            # Get trash stats from parent
            trash_stats = super().get_trash_stats()
            
            return {
                **self._stats,
                "current_trash_count": trash_stats.get("total_entries", 0),
                "recoverable_count": trash_stats.get("recoverable_entries", 0),
                "expired_count": trash_stats.get("expired_entries", 0),
                "total_operations": sum([
                    self._stats["total_trashed"],
                    self._stats["total_restored"],
                    self._stats["total_permanent_deletes"],
                    self._stats["total_cleanups"]
                ])
            }
    
    # ===== Configuration =====
    
    def enable_events(self, enabled: bool = True) -> None:
        """Enable or disable event emission"""
        self.config.enable_events = enabled
        logger.info(f"Events {'enabled' if enabled else 'disabled'}")
    
    def set_event_bus(self, event_bus: Optional[EventBus]) -> None:
        """Set or update EventBus instance"""
        self._event_bus = event_bus
        logger.info(f"EventBus {'connected' if event_bus else 'disconnected'}")
    
    def __repr__(self) -> str:
        return (
            f"TrashManagerV3(db_path={self.db_path}, "
            f"events={'enabled' if self.config.enable_events else 'disabled'}, "
            f"operations={sum([self._stats['total_trashed'], self._stats['total_restored']])})"
        )


# ===== Adapter for Legacy Code =====

class TrashManagerAdapter:
    """
    Adapter for wrapping existing TrashManager with V3 features
    
    Usage:
        # Wrap existing manager
        legacy_trash = TrashManager(db_path)
        v3_trash = TrashManagerAdapter.wrap(legacy_trash, event_bus)
        
        # Or use upgrade path
        v3_trash = TrashManagerAdapter.upgrade_path(db_path, event_bus)
    """
    
    @staticmethod
    def wrap(
        trash_manager: TrashManager,
        event_bus: Optional[EventBus] = None
    ) -> TrashManagerV3:
        """Wrap existing TrashManager with V3 features"""
        v3_trash = TrashManagerV3(
            db_path=trash_manager.db_path,
            event_bus=event_bus
        )
        
        return v3_trash
    
    @staticmethod
    def upgrade_path(
        db_path: Path,
        event_bus: Optional[EventBus] = None
    ) -> TrashManagerV3:
        """Direct upgrade path from legacy to V3"""
        return TrashManagerV3(
            db_path=db_path,
            event_bus=event_bus
        )


# ===== Factory Function =====

def create_trash_manager_v3(
    db_path: Path,
    event_bus: Optional[EventBus] = None,
    enable_events: bool = True
) -> TrashManagerV3:
    """
    Factory function for creating TrashManagerV3 instances
    
    Args:
        db_path: Path to trash database
        event_bus: Optional EventBus for event publishing
        enable_events: Enable event emission
    
    Returns:
        Configured TrashManagerV3 instance
    """
    config = TrashManagerV3Config(enable_events=enable_events)
    
    return TrashManagerV3(
        db_path=db_path,
        event_bus=event_bus,
        config=config
    )


if __name__ == "__main__":
    # Example usage
    from pathlib import Path
    import tempfile
    
    logging.basicConfig(level=logging.INFO)
    
    # Create trash manager
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "trash.db"
        trash = TrashManagerV3(db_path)
        
        # Subscribe to events
        trash.on_entry_trashed(lambda evt: print(f"🗑️  Trashed: {evt.entry_id}"))
        trash.on_entry_restored(lambda evt: print(f"♻️  Restored: {evt.entry_id}"))
        
        # Soft delete
        trash_id = trash.soft_delete("test-entry", b"test content", "document")
        print(f"Trash ID: {trash_id}")
        
        # Restore
        result = trash.restore_from_trash(trash_id)
        print(f"Restored: {result}")
        
        # Print statistics
        print("\n📊 Statistics:")
        stats = trash.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
