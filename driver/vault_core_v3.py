#!/usr/bin/env python3
"""
Vault Core V3 - Event-driven version of Vault Core
Extends VaultCore with EventBus integration while maintaining backward compatibility.

Key improvements:
- Emits EntryCreated, EntryUpdated, EntryDeleted, EntryVersioned events
- Optional EventBus injection for loose coupling
- Adapter layer for legacy code
- Preserves all original functionality
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

# Import from original vault_core to preserve existing logic
from vault_core import (
    VaultCore, VaultEntry, VaultEdge, VaultEntryType, AccessLevel
)

# Import event types
from core.event_bus import (
    EventBus, Event,
    EntryCreated, EntryUpdated, EntryDeleted, EntryVersioned,
    RelationshipCreated
)

logger = logging.getLogger(__name__)


@dataclass
class VaultCoreV3Config:
    """Configuration for VaultCoreV3"""
    enable_events: bool = True
    enable_observability: bool = True
    async_event_processing: bool = True
    emit_version_events: bool = True


class VaultCoreV3(VaultCore):
    """
    Enhanced VaultCore with event-driven architecture.
    
    Inherits all functionality from VaultCore and adds:
    - EventBus integration for loose coupling
    - Event emission on all operations
    - Observability hooks
    - Backward compatibility with legacy code
    
    Usage:
        # With EventBus (new pattern)
        event_bus = EventBus()
        vault_v3 = VaultCoreV3(vault_path, event_bus=event_bus)
        
        # Without EventBus (legacy pattern - still works)
        vault_v3 = VaultCoreV3(vault_path)
        
        # Subscribe to events
        vault_v3.on_entry_created(lambda e: print(f"Entry created: {e.entry_id}"))
        
        # Use exactly like VaultCore
        entry = VaultEntry(...)
        vault_v3.store(entry)  # Automatically emits EntryCreated event
    """
    
    def __init__(
        self,
        vault_path: Path,
        encryption_key: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        config: Optional[VaultCoreV3Config] = None
    ):
        """
        Initialize VaultCoreV3
        
        Args:
            vault_path: Path to vault database directory
            encryption_key: Master encryption key
            event_bus: Optional EventBus for publishing events
            config: Optional VaultCoreV3Config
        """
        # Initialize parent VaultCore
        super().__init__(vault_path, encryption_key)
        
        self.config = config or VaultCoreV3Config()
        self.event_bus = event_bus
        
        # Track operation context for event emission
        self._current_operation = None
        self._operation_context = {}
        
        # Local subscribers for when EventBus is not available
        self._local_subscribers = {
            'entry_created': [],
            'entry_updated': [],
            'entry_deleted': [],
            'entry_versioned': [],
            'relationship_created': []
        }
        
        logger.info(
            f"VaultCoreV3 initialized with event_bus={bool(event_bus)}, "
            f"enable_events={self.config.enable_events}"
        )
    
    # ========================================================================
    # Event Emission Methods
    # ========================================================================
    
    def _emit_event(self, event: Event, event_type: str) -> None:
        """
        Emit event to EventBus or local subscribers
        
        Args:
            event: Event to emit
            event_type: Type of event ('entry_created', etc.)
        """
        if not self.config.enable_events:
            return
        
        try:
            # Set source to this vault instance
            event.source = f"VaultCoreV3@{self.vault_path}"
            
            # Publish to EventBus if available
            if self.event_bus:
                async_mode = (
                    self.config.async_event_processing
                    if self.event_bus.config.async_mode
                    else False
                )
                self.event_bus.publish(event, async_mode=async_mode)
            
            # Call local subscribers
            for callback in self._local_subscribers.get(event_type, []):
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in local subscriber for {event_type}: {e}")
            
            logger.debug(f"Emitted {event.event_type} event: {event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to emit {event_type} event: {e}")
    
    # ========================================================================
    # Event Subscription Methods (Local)
    # ========================================================================
    
    def on_entry_created(self, callback):
        """Subscribe to entry creation events (local)"""
        self._local_subscribers['entry_created'].append(callback)
        return callback
    
    def on_entry_updated(self, callback):
        """Subscribe to entry update events (local)"""
        self._local_subscribers['entry_updated'].append(callback)
        return callback
    
    def on_entry_deleted(self, callback):
        """Subscribe to entry deletion events (local)"""
        self._local_subscribers['entry_deleted'].append(callback)
        return callback
    
    def on_entry_versioned(self, callback):
        """Subscribe to entry versioning events (local)"""
        self._local_subscribers['entry_versioned'].append(callback)
        return callback
    
    def on_relationship_created(self, callback):
        """Subscribe to relationship creation events (local)"""
        self._local_subscribers['relationship_created'].append(callback)
        return callback
    
    # ========================================================================
    # Overridden Methods with Event Emission
    # ========================================================================
    
    def store(self, entry: VaultEntry) -> bool:
        """
        Store an entry with event emission.
        
        Emits:
        - EntryCreated: if this is a new entry (version == 1)
        - EntryUpdated: if this is an update (version > 1)
        - EntryVersioned: if emit_version_events is enabled
        
        Args:
            entry: VaultEntry to store
            
        Returns:
            True if successful, False otherwise
        """
        # Call parent implementation
        result = super().store(entry)
        
        if result and self.config.enable_events:
            is_new = entry.version == 1
            
            if is_new:
                # Emit EntryCreated for new entries
                event = EntryCreated(
                    entry_id=entry.entry_id,
                    entry_type=entry.entry_type.value,
                    title=entry.title,
                    access_level=entry.access_level.value,
                    created_by=entry.created_by,
                    tags=entry.tags or []
                )
                self._emit_event(event, 'entry_created')
            else:
                # Emit EntryUpdated for modifications
                changes = {
                    'title': entry.title,
                    'summary': entry.summary,
                    'tags': entry.tags,
                    'access_level': entry.access_level.value
                }
                event = EntryUpdated(
                    entry_id=entry.entry_id,
                    version=entry.version,
                    changes=changes,
                    created_by=entry.created_by
                )
                self._emit_event(event, 'entry_updated')
            
            # Emit EntryVersioned if enabled
            if self.config.emit_version_events:
                change_summary = (
                    f"Initial entry creation"
                    if is_new
                    else f"Updated: {', '.join(changes.keys())}"
                )
                version_event = EntryVersioned(
                    entry_id=entry.entry_id,
                    version_number=entry.version,
                    change_summary=change_summary,
                    entry_type=entry.entry_type.value,
                    title=entry.title
                )
                self._emit_event(version_event, 'entry_versioned')
        
        return result
    
    def delete_entry(self, entry_id: str, soft: bool = True) -> bool:
        """
        Delete an entry with event emission.
        
        Emits:
        - EntryDeleted: when entry is deleted
        
        Args:
            entry_id: ID of entry to delete
            soft: If True, soft delete; if False, hard delete
            
        Returns:
            True if successful, False otherwise
        """
        # Call parent implementation
        result = super().delete_entry(entry_id, soft)
        
        if result and self.config.enable_events:
            event = EntryDeleted(
                entry_id=entry_id,
                soft_delete=soft
            )
            self._emit_event(event, 'entry_deleted')
        
        return result
    
    def add_edge(self, edge: VaultEdge) -> bool:
        """
        Add a graph edge with event emission.
        
        Emits:
        - RelationshipCreated: when edge is created
        
        Args:
            edge: VaultEdge to add
            
        Returns:
            True if successful, False otherwise
        """
        # Call parent implementation
        result = super().add_edge(edge)
        
        if result and self.config.enable_events:
            event = RelationshipCreated(
                source_id=edge.source_id,
                target_id=edge.target_id,
                rel_type=edge.relationship_type,
                weight=edge.weight,
                metadata=edge.metadata or {}
            )
            self._emit_event(event, 'relationship_created')
        
        return result
    
    # ========================================================================
    # Compatibility & Utility Methods
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about vault operations.
        
        Returns:
            Dictionary with vault stats
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM vault_entries WHERE is_deleted = 0")
            entries_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vault_edges")
            edges_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vault_versions")
            versions_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vault_access_log")
            access_log_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'entries': entries_count,
                'edges': edges_count,
                'versions': versions_count,
                'access_logs': access_log_count,
                'vault_path': str(self.vault_path),
                'schema_version': self.SCHEMA_VERSION,
                'event_bus_enabled': bool(self.event_bus),
                'events_enabled': self.config.enable_events
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def enable_events(self, enabled: bool = True) -> None:
        """Enable or disable event emission"""
        self.config.enable_events = enabled
        logger.info(f"Event emission {'enabled' if enabled else 'disabled'}")
    
    def set_event_bus(self, event_bus: Optional[EventBus]) -> None:
        """
        Set or replace the EventBus instance.
        Useful for dynamic configuration.
        
        Args:
            event_bus: EventBus instance or None to disable
        """
        self.event_bus = event_bus
        logger.info(f"EventBus {'attached' if event_bus else 'detached'}")
    
    def __repr__(self) -> str:
        return (
            f"VaultCoreV3(vault_path={self.vault_path}, "
            f"event_bus={'enabled' if self.event_bus else 'disabled'}, "
            f"events={'enabled' if self.config.enable_events else 'disabled'})"
        )


# ============================================================================
# Backward Compatibility Adapter
# ============================================================================

class VaultCoreAdapter:
    """
    Adapter that wraps legacy code to use VaultCoreV3 transparently.
    Allows gradual migration without changing existing code.
    
    Usage:
        # In legacy code
        vault = VaultCore(vault_path)
        
        # Wrap with adapter to get events
        vault = VaultCoreAdapter.wrap(vault, event_bus)
        
        # Use exactly the same, but now events are emitted
        vault.store(entry)
    """
    
    @staticmethod
    def wrap(vault_core: VaultCore, event_bus: Optional[EventBus] = None) -> VaultCoreV3:
        """
        Wrap an existing VaultCore instance with V3 functionality.
        
        Args:
            vault_core: Existing VaultCore instance
            event_bus: Optional EventBus for event publishing
            
        Returns:
            New VaultCoreV3 instance with same configuration
        """
        # Create V3 instance with same path and encryption
        vault_v3 = VaultCoreV3(
            vault_core.vault_path,
            event_bus=event_bus
        )
        # Copy cipher from original
        vault_v3.cipher = vault_core.cipher
        
        logger.info(f"Wrapped VaultCore at {vault_core.vault_path} with V3 functionality")
        return vault_v3
    
    @staticmethod
    def upgrade_path(vault_path: Path, event_bus: Optional[EventBus] = None) -> VaultCoreV3:
        """
        Simple path-based upgrade from VaultCore to VaultCoreV3.
        
        Args:
            vault_path: Path to vault database
            event_bus: Optional EventBus
            
        Returns:
            VaultCoreV3 instance ready to use
        """
        return VaultCoreV3(vault_path, event_bus=event_bus)


# ============================================================================
# Event Handler Decorators
# ============================================================================

def on_vault_event(vault_v3: VaultCoreV3, event_type: str):
    """
    Decorator for subscribing to vault events.
    
    Usage:
        @on_vault_event(vault_v3, 'entry_created')
        def handle_entry_created(event):
            print(f"Entry created: {event.entry_id}")
    """
    def decorator(func):
        if event_type == 'created':
            vault_v3.on_entry_created(func)
        elif event_type == 'updated':
            vault_v3.on_entry_updated(func)
        elif event_type == 'deleted':
            vault_v3.on_entry_deleted(func)
        elif event_type == 'versioned':
            vault_v3.on_entry_versioned(func)
        elif event_type == 'relationship':
            vault_v3.on_relationship_created(func)
        return func
    return decorator


if __name__ == "__main__":
    # Example usage and testing
    import tempfile
    
    # Create temporary vault for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Initialize with EventBus
        event_bus = EventBus()
        vault_v3 = VaultCoreV3(vault_path, event_bus=event_bus)
        
        # Subscribe to events
        @vault_v3.on_entry_created
        def handle_created(event):
            print(f"✓ Entry created: {event.entry_id} - {event.title}")
        
        @vault_v3.on_entry_updated
        def handle_updated(event):
            print(f"✓ Entry updated: {event.entry_id} v{event.version}")
        
        # Test operations
        entry = VaultEntry(
            entry_id="test-001",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Test Entry",
            content="Test content"
        )
        
        print("Storing entry...")
        vault_v3.store(entry)
        
        print("\nUpdating entry...")
        entry.version = 2
        entry.content = "Updated content"
        vault_v3.store(entry)
        
        print("\nDeleting entry...")
        vault_v3.delete_entry(entry.entry_id, soft=True)
        
        print("\nVault statistics:")
        print(json.dumps(vault_v3.get_stats(), indent=2))
        
        vault_v3.shutdown()
        print("\n✓ VaultCoreV3 example completed successfully")
