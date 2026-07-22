#!/usr/bin/env python3
"""
VaultCoreV3 - Phase 1 Migration Example
Shows how to migrate from VaultCore to event-driven VaultCoreV3
"""

import tempfile
from pathlib import Path
from vault_core import VaultEntry, VaultEdge, VaultEntryType, AccessLevel
from vault_core_v3 import VaultCoreV3, VaultCoreAdapter
from core.event_bus import EventBus


def example_1_basic_usage():
    """Example 1: Basic VaultCoreV3 usage with local subscribers"""
    print("\n" + "="*70)
    print("Example 1: Basic VaultCoreV3 with Local Subscribers")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Create VaultCoreV3 without EventBus (still emits events locally)
        vault = VaultCoreV3(vault_path)
        
        # Subscribe to events using decorators
        @vault.on_entry_created
        def on_created(event):
            print(f"✓ Entry created: '{event.title}' (ID: {event.entry_id})")
        
        @vault.on_entry_updated
        def on_updated(event):
            print(f"✓ Entry updated: {event.entry_id} -> v{event.version}")
        
        @vault.on_entry_deleted
        def on_deleted(event):
            print(f"✓ Entry deleted: {event.entry_id}")
        
        # Create an entry - automatically emits EntryCreated event
        entry = VaultEntry(
            entry_id="doc-001",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Getting Started",
            content="This is a documentation entry"
        )
        vault.store(entry)
        
        # Update entry - automatically emits EntryUpdated event
        entry.version = 2
        entry.content = "Updated documentation"
        vault.store(entry)
        
        # Delete entry - automatically emits EntryDeleted event
        vault.delete_entry("doc-001", soft=True)
        
        vault.shutdown()


def example_2_with_event_bus():
    """Example 2: VaultCoreV3 with EventBus for system-wide coordination"""
    print("\n" + "="*70)
    print("Example 2: VaultCoreV3 with EventBus")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Create EventBus
        event_bus = EventBus()
        
        # Create VaultCoreV3 with EventBus
        vault = VaultCoreV3(vault_path, event_bus=event_bus)
        
        # Subscribe through EventBus (allows other modules to subscribe too)
        from core.event_bus import EntryCreated, EntryUpdated
        
        def on_any_entry_created(event):
            print(f"[EventBus] Entry created system-wide: {event.title}")
        
        def on_any_entry_updated(event):
            print(f"[EventBus] Entry updated system-wide: v{event.version}")
        
        event_bus.subscribe(EntryCreated, on_any_entry_created)
        event_bus.subscribe(EntryUpdated, on_any_entry_updated)
        
        # Operations - events propagate through EventBus
        entry = VaultEntry(
            entry_id="code-001",
            entry_type=VaultEntryType.CODE,
            title="Python Module",
            content="def hello(): pass"
        )
        vault.store(entry)
        
        # Other modules can now react to these events!
        entry.version = 2
        entry.content = "def hello(name): print(name)"
        vault.store(entry)
        
        vault.shutdown()


def example_3_legacy_adapter():
    """Example 3: Adapting existing VaultCore to VaultCoreV3"""
    print("\n" + "="*70)
    print("Example 3: Legacy Adapter Pattern")
    print("="*70)
    
    from vault_core import VaultCore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Old code: create VaultCore
        legacy_vault = VaultCore(vault_path)
        
        # New code: wrap it with V3 functionality
        event_bus = EventBus()
        vault_v3 = VaultCoreAdapter.wrap(legacy_vault, event_bus)
        
        # Now it emits events but API is unchanged
        @vault_v3.on_entry_created
        def on_created(event):
            print(f"✓ Adapted: Entry created '{event.title}'")
        
        # Works exactly the same!
        entry = VaultEntry(
            entry_id="legacy-001",
            entry_type=VaultEntryType.RULE,
            title="Legacy Rule",
            content="rule: always adapt"
        )
        vault_v3.store(entry)
        
        legacy_vault.shutdown()
        vault_v3.shutdown()


def example_4_event_filtering():
    """Example 4: Event filtering and conditional handling"""
    print("\n" + "="*70)
    print("Example 4: Event Filtering")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        vault = VaultCoreV3(vault_path)
        
        # Track entry statistics
        stats = {'created': 0, 'updated': 0, 'deleted': 0}
        
        @vault.on_entry_created
        def count_created(event):
            stats['created'] += 1
            # Only log documentation entries
            if event.entry_type == VaultEntryType.DOCUMENTATION.value:
                print(f"✓ Documentation created: {event.title}")
        
        @vault.on_entry_updated
        def count_updated(event):
            stats['updated'] += 1
            print(f"  Version {event.version}: {', '.join(event.changes.keys())}")
        
        @vault.on_entry_deleted
        def count_deleted(event):
            stats['deleted'] += 1
            print(f"✗ Deleted: {event.entry_id}")
        
        # Create various entries
        for i in range(3):
            entry = VaultEntry(
                entry_id=f"doc-{i}",
                entry_type=VaultEntryType.DOCUMENTATION,
                title=f"Doc {i}",
                content=f"Content {i}"
            )
            vault.store(entry)
        
        # Update one
        entry = vault.retrieve("doc-0")
        entry.version = 2
        entry.content = "Updated"
        vault.store(entry)
        
        # Delete one
        vault.delete_entry("doc-0")
        
        print(f"\nStats: {stats}")
        vault.shutdown()


def example_5_relationship_events():
    """Example 5: Relationship/Graph events"""
    print("\n" + "="*70)
    print("Example 5: Relationship Events")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        vault = VaultCoreV3(vault_path)
        
        # Subscribe to relationship events
        @vault.on_relationship_created
        def on_rel_created(event):
            print(f"✓ Relationship: {event.source_id} -[{event.rel_type}]-> {event.target_id}")
            print(f"  Weight: {event.weight}")
        
        # Create entries
        entry1 = VaultEntry(
            entry_id="entry-a",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Document A",
            content="Content A"
        )
        entry2 = VaultEntry(
            entry_id="entry-b",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Document B",
            content="Content B"
        )
        
        vault.store(entry1)
        vault.store(entry2)
        
        # Create relationships - automatically emits RelationshipCreated
        edge1 = VaultEdge(
            source_id="entry-a",
            target_id="entry-b",
            relationship_type="references",
            weight=0.9
        )
        vault.add_edge(edge1)
        
        edge2 = VaultEdge(
            source_id="entry-b",
            target_id="entry-a",
            relationship_type="referenced_by",
            weight=0.8
        )
        vault.add_edge(edge2)
        
        vault.shutdown()


def example_6_stats_and_observability():
    """Example 6: Statistics and observability"""
    print("\n" + "="*70)
    print("Example 6: Statistics and Observability")
    print("="*70)
    
    import json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        vault = VaultCoreV3(vault_path)
        
        # Create some entries
        for i in range(5):
            entry = VaultEntry(
                entry_id=f"entry-{i}",
                entry_type=VaultEntryType.CODE if i % 2 == 0 else VaultEntryType.DOCUMENTATION,
                title=f"Entry {i}",
                content=f"Content {i}"
            )
            vault.store(entry)
        
        # Get statistics
        stats = vault.get_stats()
        print(f"\nVault Statistics:")
        print(json.dumps(stats, indent=2))
        
        print(f"\nVault representation:")
        print(repr(vault))
        
        vault.shutdown()


def example_7_disabling_events():
    """Example 7: Conditionally disable events for bulk operations"""
    print("\n" + "="*70)
    print("Example 7: Disabling Events")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        vault = VaultCoreV3(vault_path)
        
        event_count = [0]
        
        @vault.on_entry_created
        def count_events(event):
            event_count[0] += 1
        
        # Bulk import with events disabled
        print("Disabling events for bulk import...")
        vault.enable_events(False)
        
        for i in range(100):
            entry = VaultEntry(
                entry_id=f"bulk-{i}",
                entry_type=VaultEntryType.CODE,
                title=f"Bulk Entry {i}",
                content=f"Content {i}"
            )
            vault.store(entry)
        
        print(f"Events emitted during bulk import: {event_count[0]} (should be 0)")
        
        # Re-enable and do selective operations
        print("\nRe-enabling events...")
        vault.enable_events(True)
        event_count[0] = 0
        
        entry = VaultEntry(
            entry_id="selective-1",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Selective Entry",
            content="This will emit an event"
        )
        vault.store(entry)
        
        print(f"Events emitted in normal mode: {event_count[0]} (should be 1)")
        
        vault.shutdown()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("VaultCoreV3 - Phase 1 Migration Examples")
    print("="*70)
    
    example_1_basic_usage()
    example_2_with_event_bus()
    example_3_legacy_adapter()
    example_4_event_filtering()
    example_5_relationship_events()
    example_6_stats_and_observability()
    example_7_disabling_events()
    
    print("\n" + "="*70)
    print("✓ All examples completed successfully!")
    print("="*70)
