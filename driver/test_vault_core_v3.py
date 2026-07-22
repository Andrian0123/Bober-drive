#!/usr/bin/env python3
"""
Integration tests for VaultCoreV3
Tests backward compatibility and new event-driven functionality
"""

import sys
import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add driver directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from vault_core import VaultEntry, VaultEdge, VaultEntryType, AccessLevel
from vault_core_v3 import VaultCoreV3, VaultCoreAdapter
from core.event_bus import EventBus, EventBusConfig
from core.event_bus import EntryCreated, EntryUpdated, EntryDeleted, EntryVersioned, RelationshipCreated


class TestVaultCoreV3Events(unittest.TestCase):
    """Test VaultCoreV3 event emission"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.tmpdir.name)
        self.event_bus = EventBus()
        self.vault = VaultCoreV3(self.vault_path, event_bus=self.event_bus)
        
        # Track emitted events
        self.events = []
    
    def tearDown(self):
        """Clean up"""
        if self.vault:
            self.vault.shutdown()
        self.tmpdir.cleanup()
    
    def test_entry_creation_emits_event(self):
        """Test that creating an entry emits EntryCreated event"""
        # Subscribe to events
        def on_entry_created(event):
            self.events.append(('created', event))
        
        self.event_bus.subscribe(EntryCreated, on_entry_created)
        
        # Create entry
        entry = VaultEntry(
            entry_id="test-001",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Test Entry",
            content="Test content"
        )
        
        result = self.vault.store(entry)
        
        # Verify storage was successful
        self.assertTrue(result)
        
        # Verify event was emitted (may be processed asynchronously)
        # Wait a bit for async processing
        import time
        time.sleep(0.1)
        
        # Check local subscribers
        created_events = [e for t, e in self.events if t == 'created']
        self.assertGreater(len(created_events), 0, "EntryCreated event should be emitted")
        
        event = created_events[0]
        self.assertEqual(event.entry_id, "test-001")
        self.assertEqual(event.title, "Test Entry")
        self.assertEqual(event.entry_type, VaultEntryType.DOCUMENTATION.value)
    
    def test_entry_update_emits_event(self):
        """Test that updating an entry emits EntryUpdated event"""
        # Create initial entry
        entry = VaultEntry(
            entry_id="test-002",
            entry_type=VaultEntryType.CODE,
            title="Code Entry",
            content="def hello(): pass"
        )
        self.vault.store(entry)
        
        # Subscribe to events
        def on_entry_updated(event):
            self.events.append(('updated', event))
        
        self.event_bus.subscribe(EntryUpdated, on_entry_updated)
        
        # Update entry
        entry.version = 2
        entry.content = "def hello(name): print(name)"
        result = self.vault.store(entry)
        
        self.assertTrue(result)
        
        # Wait for async processing
        import time
        time.sleep(0.1)
        
        # Check for update event
        updated_events = [e for t, e in self.events if t == 'updated']
        self.assertGreater(len(updated_events), 0, "EntryUpdated event should be emitted")
        
        event = updated_events[0]
        self.assertEqual(event.entry_id, "test-002")
        self.assertEqual(event.version, 2)
    
    def test_entry_deletion_emits_event(self):
        """Test that deleting an entry emits EntryDeleted event"""
        # Create entry first
        entry = VaultEntry(
            entry_id="test-003",
            entry_type=VaultEntryType.MEMORY,
            title="Memory Entry",
            content="Important data"
        )
        self.vault.store(entry)
        
        # Subscribe to deletion events
        def on_entry_deleted(event):
            self.events.append(('deleted', event))
        
        self.event_bus.subscribe(EntryDeleted, on_entry_deleted)
        
        # Delete entry
        result = self.vault.delete_entry("test-003", soft=True)
        
        self.assertTrue(result)
        
        # Wait for async processing
        import time
        time.sleep(0.1)
        
        # Check for deletion event
        deleted_events = [e for t, e in self.events if t == 'deleted']
        self.assertGreater(len(deleted_events), 0, "EntryDeleted event should be emitted")
        
        event = deleted_events[0]
        self.assertEqual(event.entry_id, "test-003")
        self.assertTrue(event.soft_delete)
    
    def test_relationship_creation_emits_event(self):
        """Test that creating a relationship emits RelationshipCreated event"""
        # Subscribe to relationship events
        def on_rel_created(event):
            self.events.append(('relationship', event))
        
        self.event_bus.subscribe(RelationshipCreated, on_rel_created)
        
        # Create edge
        edge = VaultEdge(
            source_id="entry-a",
            target_id="entry-b",
            relationship_type="references",
            weight=0.8
        )
        
        result = self.vault.add_edge(edge)
        
        self.assertTrue(result)
        
        # Wait for async processing
        import time
        time.sleep(0.1)
        
        # Check for relationship event
        rel_events = [e for t, e in self.events if t == 'relationship']
        self.assertGreater(len(rel_events), 0, "RelationshipCreated event should be emitted")
        
        event = rel_events[0]
        self.assertEqual(event.source_id, "entry-a")
        self.assertEqual(event.target_id, "entry-b")
        self.assertEqual(event.rel_type, "references")
    
    def test_local_subscribers(self):
        """Test local subscription without EventBus"""
        # Create new vault without EventBus
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = VaultCoreV3(Path(tmpdir))
            
            local_events = []
            
            @vault.on_entry_created
            def handle_created(event):
                local_events.append(('created', event))
            
            # Create entry
            entry = VaultEntry(
                entry_id="test-004",
                entry_type=VaultEntryType.RULE,
                title="Rule Entry",
                content="rule: always validate"
            )
            vault.store(entry)
            
            # Local subscribers should be called immediately
            self.assertEqual(len(local_events), 1)
            self.assertEqual(local_events[0][0], 'created')
            self.assertEqual(local_events[0][1].entry_id, "test-004")
            
            vault.shutdown()
    
    def test_disable_events(self):
        """Test that events can be disabled"""
        local_events = []
        
        @self.vault.on_entry_created
        def handle_created(event):
            local_events.append(('created', event))
        
        @self.vault.on_entry_updated
        def handle_updated(event):
            local_events.append(('updated', event))
        
        # Create entry with events enabled
        entry = VaultEntry(
            entry_id="test-005a",
            entry_type=VaultEntryType.CONFIG,
            title="Config",
            content="key=value"
        )
        self.vault.store(entry)
        self.assertEqual(len(local_events), 1, "Event should be emitted when enabled")
        self.assertEqual(local_events[0][0], 'created')
        
        # Disable events
        self.vault.enable_events(False)
        local_events.clear()
        
        # Create entry with events disabled
        entry2 = VaultEntry(
            entry_id="test-005b",
            entry_type=VaultEntryType.CONFIG,
            title="Config 2",
            content="key=value2"
        )
        self.vault.store(entry2)
        self.assertEqual(len(local_events), 0, "No event should be emitted when disabled")
        
        # Re-enable and test
        self.vault.enable_events(True)
        
        entry.version = 2
        entry.title = "Updated Config"
        self.vault.store(entry)
        
        self.assertGreater(len(local_events), 0, "Event should be emitted when re-enabled")
        self.assertEqual(local_events[0][0], 'updated')


class TestVaultCoreV3Compatibility(unittest.TestCase):
    """Test backward compatibility with VaultCore"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.tmpdir.name)
        self.vault = VaultCoreV3(self.vault_path)
    
    def tearDown(self):
        """Clean up"""
        if self.vault:
            self.vault.shutdown()
        self.tmpdir.cleanup()
    
    def test_store_and_retrieve(self):
        """Test basic store/retrieve functionality (backward compat)"""
        entry = VaultEntry(
            entry_id="compat-001",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Compatibility Test",
            content="This should work exactly like VaultCore"
        )
        
        # Store
        result = self.vault.store(entry)
        self.assertTrue(result)
        
        # Retrieve
        retrieved = self.vault.retrieve("compat-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.entry_id, "compat-001")
        self.assertEqual(retrieved.title, "Compatibility Test")
        self.assertEqual(retrieved.content, entry.content)
    
    def test_list_entries(self):
        """Test list_entries functionality"""
        # Store multiple entries
        for i in range(3):
            entry = VaultEntry(
                entry_id=f"compat-list-{i}",
                entry_type=VaultEntryType.DOCUMENTATION,
                title=f"Entry {i}",
                content=f"Content {i}"
            )
            self.vault.store(entry)
        
        # List entries
        entries = self.vault.list_entries(limit=10)
        self.assertGreaterEqual(len(entries), 3)
    
    def test_stats(self):
        """Test statistics reporting"""
        # Store an entry
        entry = VaultEntry(
            entry_id="compat-stats",
            entry_type=VaultEntryType.RULE,
            title="Stats Test",
            content="Testing stats"
        )
        self.vault.store(entry)
        
        # Get stats
        stats = self.vault.get_stats()
        
        self.assertIn('entries', stats)
        self.assertIn('vault_path', stats)
        self.assertIn('event_bus_enabled', stats)
        self.assertIn('events_enabled', stats)
        self.assertGreaterEqual(stats['entries'], 1)


class TestVaultCoreAdapter(unittest.TestCase):
    """Test VaultCoreAdapter for wrapping existing VaultCore"""
    
    def test_adapter_wrap(self):
        """Test wrapping an existing VaultCore instance"""
        from vault_core import VaultCore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            
            # Create legacy VaultCore
            legacy_vault = VaultCore(vault_path)
            
            # Wrap with adapter
            event_bus = EventBus()
            vault_v3 = VaultCoreAdapter.wrap(legacy_vault, event_bus)
            
            # Verify it's now V3
            self.assertIsInstance(vault_v3, VaultCoreV3)
            self.assertIsNotNone(vault_v3.event_bus)
            
            # Test that it works
            entry = VaultEntry(
                entry_id="adapter-test",
                entry_type=VaultEntryType.DOCUMENTATION,
                title="Adapter Test",
                content="Testing adapter"
            )
            
            result = vault_v3.store(entry)
            self.assertTrue(result)
            
            retrieved = vault_v3.retrieve("adapter-test")
            self.assertIsNotNone(retrieved)
            
            legacy_vault.shutdown()
            vault_v3.shutdown()
    
    def test_upgrade_path(self):
        """Test upgrade_path convenience method"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            
            # Use upgrade_path
            vault_v3 = VaultCoreAdapter.upgrade_path(vault_path)
            
            self.assertIsInstance(vault_v3, VaultCoreV3)
            
            # Test functionality
            entry = VaultEntry(
                entry_id="upgrade-test",
                entry_type=VaultEntryType.MEMORY,
                title="Upgrade Test",
                content="Testing upgrade"
            )
            
            result = vault_v3.store(entry)
            self.assertTrue(result)
            
            vault_v3.shutdown()


class TestVaultCoreV3Observability(unittest.TestCase):
    """Test observability features"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.tmpdir.name)
        self.vault = VaultCoreV3(self.vault_path)
    
    def tearDown(self):
        """Clean up"""
        if self.vault:
            self.vault.shutdown()
        self.tmpdir.cleanup()
    
    def test_repr(self):
        """Test string representation"""
        repr_str = repr(self.vault)
        self.assertIn("VaultCoreV3", repr_str)
        self.assertIn("vault_path", repr_str)
    
    def test_stats_json_serializable(self):
        """Test that stats are JSON serializable"""
        entry = VaultEntry(
            entry_id="obs-test",
            entry_type=VaultEntryType.CODE,
            title="Observability Test",
            content="import observability"
        )
        self.vault.store(entry)
        
        stats = self.vault.get_stats()
        
        # Should be JSON serializable
        json_str = json.dumps(stats)
        self.assertIsInstance(json_str, str)
        
        # Deserialize and verify
        deserialized = json.loads(json_str)
        self.assertEqual(deserialized['entries'], stats['entries'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
