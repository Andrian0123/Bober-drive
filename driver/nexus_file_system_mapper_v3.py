#!/usr/bin/env python3
"""
File System Mapper V3 - Event-Driven Architecture
Scans and indexes project file structure with unified event system

Features:
- Event emission for all scanning operations
- Local subscription support (no EventBus required)
- History tracking and statistics
- Backward compatible with FileSystemMapper
- DI Container integration ready

Events:
- FileSystemScanRequested: Emitted when scan starts
- FileDiscovered: Emitted for each discovered file
- FolderAnalyzed: Emitted for each analyzed folder
- FileSystemScanCompleted: Emitted when scan succeeds
- FileSystemScanFailed: Emitted when scan fails
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from threading import Lock
from collections import deque

# Import parent class and related types
import sys
sys.path.insert(0, str(Path(__file__).parent))

from nexus_file_system_mapper import FileSystemMapper, FileInfo, FolderInfo
from core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


# ===== Event Definitions =====

class FileSystemEvent(Event):
    """Base class for file system events"""
    def __init__(self, scan_id: str, **kwargs):
        super().__init__()
        self.scan_id = scan_id
        self.metadata.update(kwargs)


class FileSystemScanRequested(FileSystemEvent):
    """Emitted when file system scan is requested"""
    def __init__(self, scan_id: str, project_root: str, **kwargs):
        super().__init__(scan_id, **kwargs)
        self.project_root = project_root
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "scan_id": self.scan_id,
            "project_root": self.project_root
        }


class FileDiscovered(FileSystemEvent):
    """Emitted when a file is discovered during scan"""
    def __init__(self, scan_id: str, file_path: str, file_type: str, size: int, **kwargs):
        super().__init__(scan_id, **kwargs)
        self.file_path = file_path
        self.file_type = file_type
        self.size = size
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "scan_id": self.scan_id,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "size": self.size
        }


class FolderAnalyzed(FileSystemEvent):
    """Emitted when a folder is analyzed"""
    def __init__(self, scan_id: str, folder_path: str, role: str, file_count: int, **kwargs):
        super().__init__(scan_id, **kwargs)
        self.folder_path = folder_path
        self.role = role
        self.file_count = file_count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "scan_id": self.scan_id,
            "folder_path": self.folder_path,
            "role": self.role,
            "file_count": self.file_count
        }


class FileSystemScanCompleted(FileSystemEvent):
    """Emitted when scan completes successfully"""
    def __init__(self, scan_id: str, file_count: int, folder_count: int, elapsed_ms: float, **kwargs):
        super().__init__(scan_id, **kwargs)
        self.file_count = file_count
        self.folder_count = folder_count
        self.elapsed_ms = elapsed_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "scan_id": self.scan_id,
            "file_count": self.file_count,
            "folder_count": self.folder_count,
            "elapsed_ms": self.elapsed_ms
        }


class FileSystemScanFailed(FileSystemEvent):
    """Emitted when scan fails"""
    def __init__(self, scan_id: str, error: str, **kwargs):
        super().__init__(scan_id, **kwargs)
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "scan_id": self.scan_id,
            "error": self.error
        }


# ===== Configuration =====

@dataclass
class FileSystemMapperV3Config:
    """Configuration for FileSystemMapperV3"""
    enable_events: bool = True
    max_history: int = 1000
    emit_file_discovered: bool = True  # Can be disabled for large projects
    emit_folder_analyzed: bool = True


# ===== Main Class =====

class FileSystemMapperV3(FileSystemMapper):
    """
    File System Mapper V3 with Event-Driven Architecture
    
    Extends FileSystemMapper with:
    - Event emission for all operations
    - Local subscription support
    - History tracking
    - Statistics and observability
    - EventBus integration
    
    Usage:
        mapper = FileSystemMapperV3(project_root, vault_core, event_bus)
        
        # Subscribe locally
        mapper.on_scan_completed(lambda evt: print(f"Scan done: {evt.file_count} files"))
        
        # Scan project
        files = mapper.scan_project()
    """
    
    def __init__(
        self,
        project_root: Path,
        vault_core=None,
        event_bus: Optional[EventBus] = None,
        config: Optional[FileSystemMapperV3Config] = None
    ):
        super().__init__(project_root, vault_core)
        
        self.config = config or FileSystemMapperV3Config()
        self._event_bus = event_bus
        
        # Local subscribers
        self._subscribers: Dict[str, List[tuple]] = {
            "scan_requested": [],
            "file_discovered": [],
            "folder_analyzed": [],
            "scan_completed": [],
            "scan_failed": []
        }
        self._subscribers_lock = Lock()
        
        # History tracking
        self._scan_history: deque = deque(maxlen=self.config.max_history)
        self._history_lock = Lock()
        
        # Statistics
        self._stats = {
            "total_scans": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "files_discovered": 0,
            "folders_analyzed": 0,
            "total_bytes_scanned": 0
        }
        self._stats_lock = Lock()
        
        logger.info(f"FileSystemMapperV3 initialized with events={'enabled' if self.config.enable_events else 'disabled'}")
    
    # ===== Core Methods Override =====
    
    def scan_project(self) -> Dict[str, FileInfo]:
        """Scan project with event emission"""
        scan_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Emit scan requested
            self._emit_scan_requested(scan_id, str(self.project_root))
            
            # Perform scan
            result = super().scan_project()
            
            # Emit file discovered events
            if self.config.emit_file_discovered:
                for file_info in result.values():
                    self._emit_file_discovered(
                        scan_id,
                        str(file_info.relative_path),
                        file_info.file_type.value,
                        file_info.size
                    )
            
            # Emit folder analyzed events
            if self.config.emit_folder_analyzed and hasattr(self, 'folders'):
                for folder_info in self.folders.values():
                    self._emit_folder_analyzed(
                        scan_id,
                        str(folder_info.relative_path),
                        folder_info.role.value,
                        folder_info.file_count
                    )
            
            # Calculate metrics
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            file_count = len(result)
            folder_count = len(self.folders) if hasattr(self, 'folders') else 0
            
            # Emit completed
            self._emit_scan_completed(scan_id, file_count, folder_count, elapsed_ms)
            
            # Track history
            self._track_scan(scan_id, True, file_count, folder_count, elapsed_ms)
            
            return result
            
        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            error_str = str(e)
            
            self._emit_scan_failed(scan_id, error_str)
            self._track_scan(scan_id, False, 0, 0, elapsed_ms, error_str)
            
            logger.error(f"File system scan failed: {e}")
            raise
    
    # ===== Event Emission =====
    
    def _emit_scan_requested(self, scan_id: str, project_root: str) -> None:
        """Emit FileSystemScanRequested event"""
        if not self.config.enable_events:
            return
        
        try:
            event = FileSystemScanRequested(scan_id, project_root)
            
            # Publish to EventBus
            if self._event_bus:
                self._event_bus.publish(event)
            
            # Notify local subscribers
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("scan_requested", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in scan_requested handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit FileSystemScanRequested: {e}")
    
    def _emit_file_discovered(self, scan_id: str, file_path: str, file_type: str, size: int) -> None:
        """Emit FileDiscovered event"""
        if not self.config.enable_events:
            return
        
        try:
            event = FileDiscovered(scan_id, file_path, file_type, size)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("file_discovered", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in file_discovered handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit FileDiscovered: {e}")
    
    def _emit_folder_analyzed(self, scan_id: str, folder_path: str, role: str, file_count: int) -> None:
        """Emit FolderAnalyzed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = FolderAnalyzed(scan_id, folder_path, role, file_count)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("folder_analyzed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in folder_analyzed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit FolderAnalyzed: {e}")
    
    def _emit_scan_completed(self, scan_id: str, file_count: int, folder_count: int, elapsed_ms: float) -> None:
        """Emit FileSystemScanCompleted event"""
        if not self.config.enable_events:
            return
        
        try:
            event = FileSystemScanCompleted(scan_id, file_count, folder_count, elapsed_ms)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("scan_completed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in scan_completed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit FileSystemScanCompleted: {e}")
    
    def _emit_scan_failed(self, scan_id: str, error: str) -> None:
        """Emit FileSystemScanFailed event"""
        if not self.config.enable_events:
            return
        
        try:
            event = FileSystemScanFailed(scan_id, error)
            
            if self._event_bus:
                self._event_bus.publish(event)
            
            with self._subscribers_lock:
                for handler, _ in self._subscribers.get("scan_failed", []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in scan_failed handler: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit FileSystemScanFailed: {e}")
    
    # ===== Local Subscriptions =====
    
    def on_scan_requested(self, handler: Callable) -> str:
        """Subscribe to scan requested events"""
        return self._subscribe("scan_requested", handler)
    
    def on_file_discovered(self, handler: Callable) -> str:
        """Subscribe to file discovered events"""
        return self._subscribe("file_discovered", handler)
    
    def on_folder_analyzed(self, handler: Callable) -> str:
        """Subscribe to folder analyzed events"""
        return self._subscribe("folder_analyzed", handler)
    
    def on_scan_completed(self, handler: Callable) -> str:
        """Subscribe to scan completed events"""
        return self._subscribe("scan_completed", handler)
    
    def on_scan_failed(self, handler: Callable) -> str:
        """Subscribe to scan failed events"""
        return self._subscribe("scan_failed", handler)
    
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
    
    def _track_scan(
        self,
        scan_id: str,
        success: bool,
        file_count: int,
        folder_count: int,
        elapsed_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Track scan in history"""
        with self._history_lock:
            self._scan_history.append({
                "scan_id": scan_id,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "file_count": file_count,
                "folder_count": folder_count,
                "elapsed_ms": elapsed_ms,
                "error": error
            })
        
        with self._stats_lock:
            self._stats["total_scans"] += 1
            if success:
                self._stats["successful_scans"] += 1
                self._stats["files_discovered"] += file_count
                self._stats["folders_analyzed"] += folder_count
            else:
                self._stats["failed_scans"] += 1
    
    def get_scan_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent scan history"""
        with self._history_lock:
            return list(self._scan_history)[-limit:]
    
    def clear_scan_history(self) -> None:
        """Clear scan history"""
        with self._history_lock:
            self._scan_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self._stats_lock:
            try:
                success_rate = (
                    self._stats["successful_scans"] / self._stats["total_scans"] * 100
                    if self._stats["total_scans"] > 0 else 0.0
                )
            except ZeroDivisionError:
                success_rate = 0.0
            
            return {
                **self._stats,
                "success_rate": success_rate,
                "avg_files_per_scan": (
                    self._stats["files_discovered"] / self._stats["successful_scans"]
                    if self._stats["successful_scans"] > 0 else 0
                ),
                "avg_folders_per_scan": (
                    self._stats["folders_analyzed"] / self._stats["successful_scans"]
                    if self._stats["successful_scans"] > 0 else 0
                )
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
            f"FileSystemMapperV3(project_root={self.project_root}, "
            f"events={'enabled' if self.config.enable_events else 'disabled'}, "
            f"scans={self._stats['total_scans']})"
        )


# ===== Adapter for Legacy Code =====

class FileSystemMapperAdapter:
    """
    Adapter for wrapping existing FileSystemMapper with V3 features
    
    Usage:
        # Wrap existing mapper
        legacy_mapper = FileSystemMapper(project_root, vault_core)
        v3_mapper = FileSystemMapperAdapter.wrap(legacy_mapper, event_bus)
        
        # Or use upgrade path
        v3_mapper = FileSystemMapperAdapter.upgrade_path(project_root, vault_core, event_bus)
    """
    
    @staticmethod
    def wrap(
        mapper: FileSystemMapper,
        event_bus: Optional[EventBus] = None
    ) -> FileSystemMapperV3:
        """Wrap existing FileSystemMapper with V3 features"""
        v3_mapper = FileSystemMapperV3(
            project_root=mapper.project_root,
            vault_core=mapper.vault_core,
            event_bus=event_bus
        )
        
        # Copy state if possible
        v3_mapper.files = mapper.files.copy()
        v3_mapper.folder_structure = mapper.folder_structure.copy()
        v3_mapper.total_lines = mapper.total_lines
        v3_mapper.total_size = mapper.total_size
        
        return v3_mapper
    
    @staticmethod
    def upgrade_path(
        project_root: Path,
        vault_core=None,
        event_bus: Optional[EventBus] = None
    ) -> FileSystemMapperV3:
        """Direct upgrade path from legacy to V3"""
        return FileSystemMapperV3(
            project_root=project_root,
            vault_core=vault_core,
            event_bus=event_bus
        )


# ===== Factory Function =====

def create_file_system_mapper_v3(
    project_root: Path,
    vault_core=None,
    event_bus: Optional[EventBus] = None,
    enable_events: bool = True,
    emit_file_events: bool = True,
    emit_folder_events: bool = True
) -> FileSystemMapperV3:
    """
    Factory function for creating FileSystemMapperV3 instances
    
    Args:
        project_root: Root path of the project to scan
        vault_core: Optional VaultCore instance
        event_bus: Optional EventBus for event publishing
        enable_events: Enable event emission
        emit_file_events: Emit FileDiscovered events (can be disabled for large projects)
        emit_folder_events: Emit FolderAnalyzed events
    
    Returns:
        Configured FileSystemMapperV3 instance
    """
    config = FileSystemMapperV3Config(
        enable_events=enable_events,
        emit_file_discovered=emit_file_events,
        emit_folder_analyzed=emit_folder_events
    )
    
    return FileSystemMapperV3(
        project_root=project_root,
        vault_core=vault_core,
        event_bus=event_bus,
        config=config
    )


if __name__ == "__main__":
    # Example usage
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    # Create mapper
    mapper = FileSystemMapperV3(
        project_root=Path("."),
        vault_core=None
    )
    
    # Subscribe to events
    mapper.on_scan_completed(lambda evt: print(f"✅ Scan completed: {evt.file_count} files, {evt.folder_count} folders"))
    mapper.on_scan_failed(lambda evt: print(f"❌ Scan failed: {evt.error}"))
    
    # Scan project
    files = mapper.scan_project()
    
    # Print statistics
    print("\n📊 Statistics:")
    stats = mapper.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
