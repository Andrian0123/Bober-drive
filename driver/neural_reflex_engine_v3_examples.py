#!/usr/bin/env python3
"""
NeuralReflexEngineV3 Examples
Demonstrates usage patterns for event-driven neural search engine.
"""

import tempfile
import time
from pathlib import Path

from vault_core import VaultCore, VaultEntry, VaultEntryType
from neural_reflex_engine_v3 import (
    NeuralReflexEngineV3,
    NeuralReflexEngineV3Config,
    NeuralReflexEngineAdapter,
    create_neural_reflex_engine_v3
)
from core.event_bus import EventBus, SearchTriggered, SearchCompleted, SearchFailed


def example_1_basic_usage():
    """Example 1: Basic usage with local subscribers"""
    print("\n" + "="*60)
    print("Example 1: Basic Usage with Local Subscribers")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        engine = NeuralReflexEngineV3(vault_core=vault)
        
        # Add test data
        vault.store(VaultEntry(
            entry_id="doc_1",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Python Guide",
            content="Python is a high-level programming language. It supports multiple paradigms."
        ))
        vault.store(VaultEntry(
            entry_id="doc_2",
            entry_type=VaultEntryType.CODE,
            title="example.py",
            content="def hello_world():\n    print('Hello, World!')"
        ))
        
        # Subscribe to events locally
        @engine.on_search_triggered
        def on_triggered(event):
            print(f"  🔍 Search triggered: '{event.query}'")
        
        @engine.on_search_completed
        def on_completed(event):
            print(f"  ✅ Search completed: {event.result_count} results in {event.elapsed_ms:.1f}ms")
        
        # Execute search
        response = engine.trigger_reflex("Python")
        print(f"\n  Query: {response.query}")
        print(f"  Total hits: {response.total_hits}")
        print(f"  Search levels: {response.search_levels_breakdown}")
        
        vault.shutdown()
        print("  ✓ Example 1 PASSED")


def example_2_eventbus_integration():
    """Example 2: EventBus integration"""
    print("\n" + "="*60)
    print("Example 2: EventBus Integration")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        event_bus = EventBus()
        engine = NeuralReflexEngineV3(vault_core=vault, event_bus=event_bus)
        
        # Add test data
        vault.store(VaultEntry(
            entry_id="note_1",
            entry_type=VaultEntryType.MEMORY,
            title="Meeting Notes",
            content="Discussed the new API architecture and event-driven design."
        ))
        
        # Subscribe via EventBus
        search_log = []
        
        def log_triggered(event):
            search_log.append({"type": "triggered", "query": event.query})
        
        def log_completed(event):
            search_log.append({"type": "completed", "count": event.result_count})
        
        event_bus.subscribe(SearchTriggered, log_triggered)
        event_bus.subscribe(SearchCompleted, log_completed)
        
        # Execute searches
        engine.trigger_reflex("API")
        engine.trigger_reflex("architecture")
        
        time.sleep(0.2)  # Wait for async events
        
        print(f"  Event log ({len(search_log)} events):")
        for entry in search_log:
            print(f"    - {entry}")
        
        vault.shutdown()
        print("  ✓ Example 2 PASSED")


def example_3_adapter_pattern():
    """Example 3: Adapter pattern for legacy code"""
    print("\n" + "="*60)
    print("Example 3: Adapter Pattern for Legacy Code")
    print("="*60)
    
    from neural_reflex_engine import NeuralReflexEngine
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        
        # Create legacy engine
        legacy_engine = NeuralReflexEngine(vault_core=vault)
        print("  Created legacy NeuralReflexEngine")
        
        # Wrap with adapter
        event_bus = EventBus()
        adapted = NeuralReflexEngineAdapter.wrap(legacy_engine, event_bus)
        print("  Wrapped with adapter")
        
        # Add test data
        vault.store(VaultEntry(
            entry_id="skill_1",
            entry_type=VaultEntryType.SKILL,
            title="Search Skill",
            content="Advanced search techniques and algorithms."
        ))
        
        # Subscribe to events
        events = []
        event_bus.subscribe(SearchTriggered, lambda e: events.append("triggered"))
        event_bus.subscribe(SearchCompleted, lambda e: events.append("completed"))
        
        # Use adapted engine
        response = adapted.trigger_reflex("search")
        time.sleep(0.1)
        
        print(f"  Events emitted: {events}")
        print(f"  Results found: {response.total_hits}")
        
        vault.shutdown()
        print("  ✓ Example 3 PASSED")


def example_4_upgrade_path():
    """Example 4: Direct upgrade path"""
    print("\n" + "="*60)
    print("Example 4: Direct Upgrade Path")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        event_bus = EventBus()
        
        # Direct upgrade to V3
        engine = NeuralReflexEngineAdapter.upgrade_path(vault, event_bus)
        print(f"  Created: {engine}")
        print(f"  Type: {type(engine).__name__}")
        
        # Add data and search
        vault.store(VaultEntry(
            entry_id="rule_1",
            entry_type=VaultEntryType.RULE,
            title="Coding Standard",
            content="All functions must have docstrings and type hints."
        ))
        
        response = engine.trigger_reflex("function")
        print(f"  Search results: {response.total_hits}")
        
        vault.shutdown()
        print("  ✓ Example 4 PASSED")


def example_5_search_history():
    """Example 5: Search history and statistics"""
    print("\n" + "="*60)
    print("Example 5: Search History and Statistics")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        config = NeuralReflexEngineV3Config(track_search_history=True)
        engine = NeuralReflexEngineV3(vault_core=vault, config=config)
        
        # Add test data
        for i in range(5):
            vault.store(VaultEntry(
                entry_id=f"entry_{i}",
                entry_type=VaultEntryType.DOCUMENTATION,
                title=f"Document {i}",
                content=f"This is document number {i} with some content about Python programming."
            ))
        
        # Execute multiple searches
        queries = ["Python", "document", "programming", "content"]
        for query in queries:
            engine.trigger_reflex(query)
        
        # Get statistics
        stats = engine.get_stats()
        print(f"  Total searches: {stats['total_searches']}")
        print(f"  Successful: {stats['successful_searches']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        print(f"  Avg results: {stats['avg_results']:.1f}")
        print(f"  Avg duration: {stats['avg_duration_ms']:.1f}ms")
        
        # Get history
        history = engine.get_search_history(limit=3)
        print(f"\n  Recent searches:")
        for h in history:
            print(f"    - '{h['query']}': {h['result_count']} results, {h['status']}")
        
        vault.shutdown()
        print("  ✓ Example 5 PASSED")


def example_6_disable_events():
    """Example 6: Disabling events temporarily"""
    print("\n" + "="*60)
    print("Example 6: Disabling Events Temporarily")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        event_bus = EventBus()
        engine = NeuralReflexEngineV3(vault_core=vault, event_bus=event_bus)
        
        # Add test data
        vault.store(VaultEntry(
            entry_id="config_1",
            entry_type=VaultEntryType.CONFIG,
            title="App Config",
            content="timeout: 30\nmax_retries: 3"
        ))
        
        # Track events
        event_count = [0]
        event_bus.subscribe(SearchTriggered, lambda e: event_count.__setitem__(0, event_count[0] + 1))
        
        # Search with events enabled
        engine.trigger_reflex("config")
        time.sleep(0.1)
        print(f"  Events after search 1: {event_count[0]}")
        
        # Disable events
        engine.disable_events()
        print("  Events disabled")
        
        # Search with events disabled
        engine.trigger_reflex("config")
        time.sleep(0.1)
        print(f"  Events after search 2: {event_count[0]}")  # Should not increase
        
        # Re-enable events
        engine.enable_events()
        print("  Events re-enabled")
        
        # Search with events enabled again
        engine.trigger_reflex("config")
        time.sleep(0.1)
        print(f"  Events after search 3: {event_count[0]}")  # Should increase
        
        vault.shutdown()
        print("  ✓ Example 6 PASSED")


def example_7_factory_function():
    """Example 7: Using factory function"""
    print("\n" + "="*60)
    print("Example 7: Using Factory Function")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir) / "vault.db")
        event_bus = EventBus()
        config = NeuralReflexEngineV3Config(
            enable_events=True,
            track_search_history=True,
            async_event_processing=False  # Synchronous for testing
        )
        
        # Use factory function
        engine = create_neural_reflex_engine_v3(
            vault_core=vault,
            event_bus=event_bus,
            config=config
        )
        print(f"  Created: {engine}")
        
        # Add data
        vault.store(VaultEntry(
            entry_id="workflow_1",
            entry_type=VaultEntryType.WORKFLOW,
            title="Deploy Workflow",
            content="1. Run tests\n2. Build package\n3. Deploy to production"
        ))
        
        # Execute search
        response = engine.trigger_reflex("deploy")
        print(f"  Results: {response.total_hits}")
        print(f"  Time: {response.search_time_ms:.1f}ms")
        
        vault.shutdown()
        print("  ✓ Example 7 PASSED")


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*70)
    print("  NeuralReflexEngineV3 Examples")
    print("="*70)
    
    examples = [
        example_1_basic_usage,
        example_2_eventbus_integration,
        example_3_adapter_pattern,
        example_4_upgrade_path,
        example_5_search_history,
        example_6_disable_events,
        example_7_factory_function
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"  ✗ Example FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n" + "="*70)
    print("  ✅ All 7 examples PASSED")
    print("="*70)
    return True


if __name__ == '__main__':
    import sys
    success = run_all_examples()
    sys.exit(0 if success else 1)
