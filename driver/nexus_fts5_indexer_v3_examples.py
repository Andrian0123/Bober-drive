#!/usr/bin/env python3
"""
FTS5IndexerV3 Examples - 5 integration patterns

Pattern 1: Central EventBus (recommended for full ecosystem integration)
Pattern 2: Local subscribers only (no EventBus needed)
Pattern 3: Legacy migration (wrap existing VaultFTS5Extension)
Pattern 4: Performance mode (events disabled for batch operations)
Pattern 5: Full lifecycle with history and observability
"""

import tempfile
from pathlib import Path
from datetime import datetime

from nexus_fts5_indexer_v3 import (
    FTS5IndexerV3,
    FTS5IndexerV3Config,
    FTS5IndexerAdapter,
    create_fts5_indexer_v3,
    SearchCompleted,
    SearchFailed
)
from vault_fts5_extension import VaultFTS5Extension
from core.event_bus import EventBus


def pattern_1_central_eventbus():
    """
    Pattern 1: Central EventBus (recommended for full ecosystem integration)
    Use this when integrating with other V3 modules (RulesEngineV3, NeuralReflexEngineV3, etc.)
    """
    print("\n" + "=" * 70)
    print("PATTERN 1: Central EventBus Integration")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "vault.db"
        
        # Create central EventBus (shared across all V3 modules)
        event_bus = EventBus()
        
        # Subscribe to search events at the ecosystem level
        search_results = []
        
        def on_search_event(event):
            search_results.append({
                "type": event.__class__.__name__,
                "query": event.query if hasattr(event, 'query') else None,
                "result_count": event.result_count if hasattr(event, 'result_count') else None,
                "timestamp": event.timestamp if hasattr(event, 'timestamp') else None
            })
            print(f"  [EventBus] {event.__class__.__name__}: query='{event.query if hasattr(event, 'query') else 'N/A'}'")
        
        event_bus.subscribe(SearchCompleted, on_search_event)
        event_bus.subscribe(SearchFailed, on_search_event)
        
        # Create FTS5IndexerV3 with central EventBus
        config = FTS5IndexerV3Config(
            enable_events=True,
            async_event_processing=False,
            event_bus=event_bus  # <-- Share EventBus across ecosystem
        )
        indexer = FTS5IndexerV3(db_path, config)
        
        print(f"\nCreated FTS5IndexerV3 with central EventBus")
        print(f"  - EventBus subscription count: {len(event_bus._subscribers.get(SearchCompleted, []))}")
        
        # Simulate some searches (will publish to EventBus)
        print(f"\nSimulating searches...")
        try:
            indexer.fulltext_search("test query")
        except Exception as e:
            print(f"  Search finished (may be empty database): {str(e)[:50]}")
        
        # Verify EventBus received events
        print(f"\nEventBus received {len(search_results)} events")
        for result in search_results:
            print(f"  - {result['type']}: {result['query']}")


def pattern_2_local_subscribers():
    """
    Pattern 2: Local subscribers only (no EventBus needed)
    Use this for standalone full-text search without ecosystem integration.
    """
    print("\n" + "=" * 70)
    print("PATTERN 2: Local Subscribers (No EventBus)")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "vault.db"
        
        # Create FTS5IndexerV3 without EventBus
        indexer = create_fts5_indexer_v3(
            db_path,
            enable_events=True,
            event_bus=None  # No central EventBus
        )
        
        # Subscribe locally (handlers called directly)
        searches = []
        
        def on_search_completed(event):
            searches.append({
                "query": event.query,
                "results": event.result_count,
                "time_ms": event.elapsed_ms
            })
            print(f"  [Local] Search completed: query='{event.query}', results={event.result_count}, time={event.elapsed_ms:.2f}ms")
        
        def on_search_failed(event):
            print(f"  [Local] Search failed: {event.error}")
        
        # Register local handlers
        indexer.on_search_completed(on_search_completed)
        indexer.on_search_failed(on_search_failed)
        
        print(f"\nCreated FTS5IndexerV3 with local subscribers (no EventBus)")
        
        # Perform searches - handlers will be called directly
        print(f"\nPerforming searches...")
        try:
            indexer.fulltext_search("python")
            indexer.regex_search(r"test\d+")
        except Exception as e:
            print(f"  Searches completed: {str(e)[:50]}")
        
        print(f"\nCaptured {len(searches)} completed searches locally")
        for search in searches:
            print(f"  - {search['query']}: {search['results']} results in {search['time_ms']:.2f}ms")


def pattern_3_legacy_migration():
    """
    Pattern 3: Legacy migration (wrap existing VaultFTS5Extension)
    Use this when upgrading from VaultFTS5Extension to add events without rewriting code.
    """
    print("\n" + "=" * 70)
    print("PATTERN 3: Legacy Migration (Adapter Pattern)")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "vault.db"
        
        # Step 1: Existing code using VaultFTS5Extension
        print("\nStep 1: Create legacy VaultFTS5Extension")
        legacy_engine = VaultFTS5Extension(db_path)
        print(f"  - Created legacy engine: {legacy_engine}")
        
        # Step 2: Wrap with adapter to get V3 features
        print("\nStep 2: Wrap with adapter to add events")
        event_bus = EventBus()
        v3_engine = FTS5IndexerAdapter.wrap(legacy_engine, event_bus)
        print(f"  - Wrapped with V3 features: {v3_engine}")
        
        # Step 3: Subscribe to events
        print("\nStep 3: Subscribe to new events (didn't need changes in legacy code)")
        events = []
        
        def capture_event(event):
            events.append(event.__class__.__name__)
            print(f"  - Captured: {event.__class__.__name__}")
        
        v3_engine.on_search_completed(capture_event)
        v3_engine.on_search_executed(capture_event)
        
        # Step 4: Existing search code still works, now emits events
        print("\nStep 4: Use same search methods (now with events)")
        try:
            v3_engine.fulltext_search("test")
        except Exception as e:
            print(f"  Search executed: {str(e)[:50]}")
        
        print(f"\nEvents captured: {len(events)}")


def pattern_4_performance_mode():
    """
    Pattern 4: Performance mode (events disabled for batch operations)
    Use this when you need high-throughput searches without event overhead.
    """
    print("\n" + "=" * 70)
    print("PATTERN 4: Performance Mode (Events Disabled)")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "vault.db"
        
        # Create indexer with events enabled
        indexer = create_fts5_indexer_v3(db_path, enable_events=True)
        
        print(f"\nCreated FTS5IndexerV3 with events enabled")
        print(f"  - Events enabled: {indexer.config.enable_events}")
        
        # Setup event tracking
        event_count = {"count": 0}
        
        def count_event(event):
            event_count["count"] += 1
        
        indexer.on_search_completed(count_event)
        
        # Interactive searches (with events)
        print(f"\nPhase 1: Interactive searches (events enabled)")
        try:
            indexer.fulltext_search("query1")
            indexer.fulltext_search("query2")
        except:
            pass
        print(f"  - Events emitted: {event_count['count']}")
        
        # Batch operation - disable events for performance
        print(f"\nPhase 2: Batch operation (events disabled)")
        indexer.enable_events(False)
        print(f"  - Events enabled: {indexer.config.enable_events}")
        
        event_count["count"] = 0
        try:
            for i in range(10):
                indexer.fulltext_search(f"batch_query_{i}")
        except:
            pass
        print(f"  - Events emitted during batch: {event_count['count']} (should be 0)")
        
        # Re-enable for interactive use
        print(f"\nPhase 3: Re-enable events")
        indexer.enable_events(True)
        try:
            indexer.fulltext_search("query3")
        except:
            pass
        print(f"  - Events re-enabled: {indexer.config.enable_events}")


def pattern_5_full_lifecycle():
    """
    Pattern 5: Full lifecycle with history and observability
    Use this for complete monitoring and debugging of search operations.
    """
    print("\n" + "=" * 70)
    print("PATTERN 5: Full Lifecycle (History + Stats + Observability)")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "vault.db"
        
        # Create indexer with full observability
        config = FTS5IndexerV3Config(
            enable_events=True,
            track_search_history=True,
            max_search_history=100
        )
        indexer = FTS5IndexerV3(db_path, config)
        
        print(f"\nCreated FTS5IndexerV3 with full observability")
        print(f"  - Config: {config}")
        
        # Setup logging
        log_entries = []
        
        def log_event(event):
            log_entries.append({
                "type": event.__class__.__name__,
                "query": event.query if hasattr(event, 'query') else None,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        indexer.on_search_completed(log_event)
        indexer.on_search_failed(log_event)
        
        # Perform various searches
        print(f"\nPerforming searches...")
        searches = [
            ("python", "fts5"),
            ("test_pattern", "regex"),
            ("keyword search", "like")
        ]
        
        for query, search_type in searches:
            try:
                if search_type == "fts5":
                    indexer.fulltext_search(query)
                elif search_type == "regex":
                    indexer.regex_search(query)
                else:
                    indexer.advanced_search(query, "like")
            except:
                pass  # Database may be empty
        
        # Get statistics
        print(f"\nStatistics:")
        stats = indexer.get_stats()
        print(f"  - Total searches: {stats['total_searches']}")
        print(f"  - Successful: {stats['successful_searches']}")
        print(f"  - Failed: {stats['failed_searches']}")
        print(f"  - Success rate: {stats['success_rate']:.1f}%")
        print(f"  - Total hits: {stats['total_hits']}")
        print(f"  - Avg duration: {stats['avg_search_duration_ms']:.2f}ms")
        print(f"  - Search types: {stats['search_types']}")
        print(f"  - Index size: {stats['index_size_bytes']} bytes")
        
        # Get history
        print(f"\nSearch History (last 5):")
        history = indexer.get_search_history(limit=5)
        for i, entry in enumerate(history, 1):
            status = "✓" if entry["success"] else "✗"
            print(f"  {i}. {status} {entry['search_type']:6s} - {entry['query'][:30]:30s} "
                  f"({entry['result_count']} results, {entry['elapsed_ms']:.1f}ms)")
        
        # Event logs
        print(f"\nEvent Logs:")
        for i, log in enumerate(log_entries[-5:], 1):
            print(f"  {i}. {log['type']:20s} - {log['query']}")


def main():
    """Run all patterns"""
    print("\n" + "█" * 70)
    print("█ FTS5IndexerV3 - 5 Integration Patterns")
    print("█" * 70)
    
    try:
        pattern_1_central_eventbus()
    except Exception as e:
        print(f"⚠ Pattern 1 error: {e}")
    
    try:
        pattern_2_local_subscribers()
    except Exception as e:
        print(f"⚠ Pattern 2 error: {e}")
    
    try:
        pattern_3_legacy_migration()
    except Exception as e:
        print(f"⚠ Pattern 3 error: {e}")
    
    try:
        pattern_4_performance_mode()
    except Exception as e:
        print(f"⚠ Pattern 4 error: {e}")
    
    try:
        pattern_5_full_lifecycle()
    except Exception as e:
        print(f"⚠ Pattern 5 error: {e}")
    
    print("\n" + "█" * 70)
    print("█ All patterns completed")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
