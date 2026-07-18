# 🔄 Migration Guide: V2 → V3

## Overview

This guide helps you migrate from Nexus Driver V2 to the new **V3 Unified Event-Driven Architecture**. The V3 architecture introduces:

- **Event-Driven Communication**: All modules communicate through events
- **Orchestrator Pattern**: Single entry point with DI Container
- **Pipeline Manager**: Composable multi-stage workflows
- **Auto-Update System**: Automatic updates every 15 days
- **Backward Compatibility**: V2 modules work with V3 via adapters

---

## Migration Strategies

### Strategy 1: Adapter Pattern (Immediate, Zero Changes)

**Best for**: Quick adoption, minimal code changes, gradual learning

The V3 architecture includes adapters that wrap V2 modules:

```python
# V2 Code (still works!)
from driver.vault_core import VaultCore

vault = VaultCore(vault_path=Path("./data.vault"))
vault.store(entry)

# V3 Enhanced (with events)
from driver.vault_core_v3 import VaultCoreAdapter
from driver.core.event_bus import EventBus

event_bus = EventBus()
vault_v3 = VaultCoreAdapter.wrap(vault, event_bus=event_bus)

# Subscribe to events
vault_v3.on_entry_created(lambda e: print(f"Created: {e.entry_id}"))

# Use exactly as before
vault_v3.store(entry)  # Now emits EntryCreated event
```

### Strategy 2: Direct V3 Modules (Recommended)

**Best for**: New projects, full V3 features, clean architecture

```python
# V3 Native
from driver.vault_core_v3 import create_vault_core_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
vault = create_vault_core_v3(
    vault_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
vault.on_entry_created(lambda e: print(f"Created: {e.entry_id}"))

# Use V3 API (same as V2, plus events)
vault.store(entry)
```

### Strategy 3: Orchestrator Pattern (Best Practice)

**Best for**: Complex workflows, large projects, production systems

```python
# V3 Orchestrator (recommended for new code)
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig

config = NexusConfig(
    vault_path=Path("./data.vault"),
    project_root=Path("./project"),
    enable_events=True,
    enable_auto_update=True
)

orchestrator = create_nexus_orchestrator(config)

# High-level operations
result = orchestrator.ingest_document(Path("./doc.md"))
search_results = orchestrator.search("query")
stats = orchestrator.get_stats()
```

---

## Module-by-Module Migration

### VaultCore: V2 → V3

#### V2 Code
```python
from driver.vault_core import VaultCore, VaultEntry, VaultEntryType

vault = VaultCore(vault_path=Path("./data.vault"))
entry = VaultEntry(
    entry_id="doc-001",
    entry_type=VaultEntryType.DOCUMENT,
    title="My Document",
    content=b"Content"
)
vault.store(entry)
```

#### V3 Code (Option 1: Adapter)
```python
from driver.vault_core import VaultCore, VaultEntry, VaultEntryType
from driver.vault_core_v3 import VaultCoreAdapter
from driver.core.event_bus import EventBus

# Wrap existing V2 instance
vault_v2 = VaultCore(vault_path=Path("./data.vault"))
vault_v3 = VaultCoreAdapter.wrap(vault_v2, event_bus=EventBus())

# Subscribe to events
vault_v3.on_entry_created(lambda e: print(f"Created: {e.entry_id}"))

# Use as before
entry = VaultEntry(
    entry_id="doc-001",
    entry_type=VaultEntryType.DOCUMENT,
    title="My Document",
    content=b"Content"
)
vault_v3.store(entry)  # Emits EntryCreated event
```

#### V3 Code (Option 2: Native)
```python
from driver.vault_core_v3 import create_vault_core_v3, VaultCoreV3Config
from driver.vault_core import VaultEntry, VaultEntryType
from driver.core.event_bus import EventBus

# Create V3 instance
event_bus = EventBus()
vault = create_vault_core_v3(
    vault_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
vault.on_entry_created(lambda e: print(f"Created: {e.entry_id}"))

# Same API as V2
entry = VaultEntry(
    entry_id="doc-001",
    entry_type=VaultEntryType.DOCUMENT,
    title="My Document",
    content=b"Content"
)
vault.store(entry)
```

**Events Emitted**:
- `EntryCreated`: When `store()` creates new entry
- `EntryUpdated`: When `store()` updates existing entry
- `EntryDeleted`: When `delete_entry()` is called
- `RelationshipCreated`: When `add_edge()` creates relationship
- `EntryVersioned`: When versioning is triggered

---

### FTS5 Extension: V2 → V3

#### V2 Code
```python
from driver.vault_fts5_extension import VaultFTS5Extension

fts5 = VaultFTS5Extension(db_path=Path("./data.vault"))
results = fts5.fulltext_search("machine learning", limit=50)
```

#### V3 Code
```python
from driver.nexus_fts5_indexer_v3 import create_fts5_indexer_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
fts5 = create_fts5_indexer_v3(
    db_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
fts5.on_search_completed(lambda e: print(f"Search: {e.result_count} results"))

# Same API as V2
results = fts5.fulltext_search("machine learning", limit=50)
```

**Events Emitted**:
- `SearchIndexRequested`: When search is initiated
- `SearchIndexed`: When content is indexed
- `SearchExecuted`: When search query runs
- `SearchCompleted`: When search succeeds
- `SearchFailed`: When search fails

**New Features**:
- Search history: `fts5.get_search_history()`
- Statistics: `fts5.get_stats()`
- Performance tracking

---

### Rules Engine: V2 → V3

#### V2 Code
```python
from driver.nexus_project_rules import ProjectRulesEngine

rules = ProjectRulesEngine(project_root=Path("./project"))
parsed_rules = rules.scan_rules()
violations = rules.validate_against_rules(content, "python")
```

#### V3 Code
```python
from driver.nexus_rules_engine_v3 import create_rules_engine_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
rules = create_rules_engine_v3(
    project_root=Path("./project"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
rules.on_violation_detected(lambda e: print(f"Violation: {e.rule_title}"))

# Same API as V2
parsed_rules = rules.scan_rules()
violations = rules.validate_against_rules(content, "python")
```

**Events Emitted**:
- `RulesScanRequested`: When `scan_rules()` starts
- `RulesLoaded`: When rules are successfully loaded
- `RuleParsed`: For each rule parsed
- `RuleViolationDetected`: When violation is found
- `RulesValidationCompleted`: When validation finishes
- `RulesValidationFailed`: When validation fails

**New Features**:
- Scan history: `rules.get_scan_history()`
- Validation history: `rules.get_validation_history()`
- Statistics: `rules.get_stats()`

---

### Neural Reflex Engine: V2 → V3

#### V2 Code
```python
from driver.neural_reflex_engine import NeuralReflexEngine

engine = NeuralReflexEngine(vault_core=vault, fts5_extension=fts5)
response = engine.trigger_reflex("query", timeout_ms=500)
```

#### V3 Code
```python
from driver.neural_reflex_engine_v3 import create_neural_reflex_engine_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
engine = create_neural_reflex_engine_v3(
    vault_core=vault,
    fts5_extension=fts5,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
engine.on_search_completed(lambda e: print(f"Search: {e.elapsed_ms}ms"))

# Same API as V2
response = engine.trigger_reflex("query", timeout_ms=500)
```

**Events Emitted**:
- `SearchTriggered`: When `trigger_reflex()` starts
- `SearchCompleted`: When search succeeds
- `SearchFailed`: When search fails

---

### Graphify Engine: V2 → V3

#### V2 Code
```python
from driver.nexus_graphify import GraphifyEngine

graphify = GraphifyEngine(vault_core=vault, fts5_extension=fts5)
doc = graphify.import_document(Path("./doc.pdf"))
```

#### V3 Code
```python
from driver.nexus_graphify_v3 import create_graphify_engine_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
graphify = create_graphify_engine_v3(
    vault_core=vault,
    fts5_extension=fts5,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
graphify.on_document_parsed(lambda e: print(f"Parsed: {e.document_id}"))

# Same API as V2
doc = graphify.import_document(Path("./doc.pdf"))
```

**Events Emitted**:
- `DocumentImportRequested`: When import starts
- `DocumentFormatDetected`: When format is identified
- `DocumentParsed`: When parsing succeeds
- `DocumentSegmented`: When sections are extracted
- `EntitiesExtracted`: When entities are found
- `DocumentValidated`: When validation passes
- `DocumentStoredEvent`: When saved to vault
- `DocumentError`: When processing fails

---

### File System Mapper: V2 → V3

#### V2 Code
```python
from driver.nexus_file_system_mapper import FileSystemMapper

mapper = FileSystemMapper(project_root=Path("./project"), vault_core=vault)
files = mapper.scan_project()
mapper.save_to_vault()
```

#### V3 Code
```python
from driver.nexus_file_system_mapper_v3 import create_file_system_mapper_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
mapper = create_file_system_mapper_v3(
    project_root=Path("./project"),
    vault_core=vault,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
mapper.on_scan_completed(lambda e: print(f"Scanned: {e.files_discovered} files"))

# Same API as V2
files = mapper.scan_project()
mapper.save_to_vault()
```

**Events Emitted**:
- `FileScanRequested`: When `scan_project()` starts
- `FileDiscovered`: For each file found (optional, can be disabled)
- `FolderAnalyzed`: When folder analysis completes
- `ScanCompleted`: When scan finishes

---

### Trash Manager: V2 → V3

#### V2 Code
```python
from driver.trash_manager import TrashManager

trash = TrashManager(db_path=Path("./data.vault"))
trash.soft_delete(entry_id, content, entry_type)
trash.restore_from_trash(trash_id)
```

#### V3 Code
```python
from driver.nexus_trash_manager_v3 import create_trash_manager_v3
from driver.core.event_bus import EventBus

event_bus = EventBus()
trash = create_trash_manager_v3(
    db_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
trash.on_entry_trashed(lambda e: print(f"Deleted: {e.entry_id}"))

# Same API as V2
trash.soft_delete(entry_id, content, entry_type)
trash.restore_from_trash(trash_id)
```

**Events Emitted**:
- `EntryTrashed`: When `soft_delete()` is called
- `EntryRestored`: When `restore_from_trash()` succeeds
- `EntryPermanentlyDeleted`: When permanent delete occurs

---

## Event Bus Usage

### Basic Event Subscription

```python
from driver.core.event_bus import EventBus, EntryCreated

event_bus = EventBus()

# Subscribe to specific event type
def on_entry_created(event: EntryCreated):
    print(f"Entry created: {event.entry_id}")

subscription_id = event_bus.subscribe(EntryCreated, on_entry_created)

# Unsubscribe later
event_bus.unsubscribe(subscription_id)
```

### Priority Handling

```python
# High priority handler (runs first)
event_bus.subscribe(
    EntryCreated, 
    high_priority_handler,
    priority=10
)

# Low priority handler (runs last)
event_bus.subscribe(
    EntryCreated,
    low_priority_handler,
    priority=1
)
```

### Async Event Processing

```python
config = EventBusConfig(
    max_history=1000,
    enable_async=True,  # Enable async processing
    async_queue_size=500
)

event_bus = EventBus(config=config)
event_bus.start_async_processing()

# Events are processed in background thread
# Non-blocking for publishers
```

### Event History

```python
# Get recent events
history = event_bus.get_event_history(limit=100)

# Get specific event type history
history = event_bus.get_event_history(
    event_type=EntryCreated,
    limit=50
)

# Statistics
stats = event_bus.get_stats()
print(f"Total events: {stats['total_events_published']}")
```

---

## Orchestrator Usage

### Basic Setup

```python
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig
from pathlib import Path

config = NexusConfig(
    vault_path=Path("./my_project.vault"),
    project_root=Path("./my_project"),
    enable_events=True,
    enable_auto_update=True,
    auto_update_check_days=15
)

orchestrator = create_nexus_orchestrator(config)
```

### Document Ingest Pipeline

```python
# Ingest a document (full pipeline)
result = orchestrator.ingest_document(Path("./document.md"))

# Pipeline stages:
# 1. Parse document
# 2. Validate rules
# 3. Extract entities
# 4. Store in vault
# 5. Index FTS5
# 6. Build graph relationships

print(f"Document ID: {result['document_id']}")
print(f"Entities: {result['entities_extracted']}")
```

### Search Pipeline

```python
# Search with full pipeline
results = orchestrator.search("machine learning")

# Pipeline stages:
# 1. Parse query
# 2. FTS5 search
# 3. Semantic search
# 4. Merge results
# 5. Rank results

print(f"Found {len(results['results'])} results")
for result in results['results'][:5]:
    print(f"- {result['title']} (score: {result['score']})")
```

### Project Scan Pipeline

```python
# Scan project structure
result = orchestrator.scan_project()

# Pipeline stages:
# 1. Scan files
# 2. Classify files
# 3. Analyze folders
# 4. Detect patterns
# 5. Save metadata

print(f"Files discovered: {result['files_discovered']}")
print(f"Folders analyzed: {result['folders_analyzed']}")
```

### Custom Pipelines

```python
# Create custom pipeline
from driver.nexus_orchestrator_v3 import NexusPipeline, PipelineStage

pipeline = orchestrator.container.resolve("pipeline_factory").create("custom")

# Add custom stages
pipeline.add_stage(
    name="custom_stage",
    handler=my_custom_handler,
    stage_type=PipelineStage.PROCESSING,
    error_handler=my_error_handler
)

# Execute
result = pipeline.execute(input_data)
```

---

## Configuration

### V3 Configuration Options

```python
from driver.nexus_orchestrator_v3 import NexusConfig
from pathlib import Path

config = NexusConfig(
    # Required
    vault_path=Path("./data.vault"),
    project_root=Path("./project"),
    
    # Event System
    enable_events=True,              # Enable event emission
    event_bus_max_history=1000,      # Keep last 1000 events
    event_bus_async=True,            # Async event processing
    
    # Auto-Update
    enable_auto_update=True,         # Enable auto-updates
    auto_update_check_days=15,       # Check every 15 days
    auto_update_backup=True,         # Backup before update
    
    # Performance
    max_workers=4,                   # Thread pool size
    cache_size=1000,                 # Cache entries
    
    # Security
    encryption_key="your-key",       # Fernet encryption key
    
    # Features
    enable_neural_reflex=True,       # Enable Neural Reflex
    enable_file_mapper=True,         # Enable File Mapper
    enable_trash_manager=True        # Enable Trash Manager
)
```

### Per-Module Configuration

```python
from driver.vault_core_v3 import VaultCoreV3Config
from driver.nexus_fts5_indexer_v3 import FTS5IndexerV3Config
from driver.nexus_rules_engine_v3 import RulesEngineV3Config

# VaultCore config
vault_config = VaultCoreV3Config(
    enable_events=True,
    enable_versioning=True,
    max_version_history=10
)

# FTS5 config
fts5_config = FTS5IndexerV3Config(
    enable_events=True,
    max_search_history=500,
    track_performance=True
)

# Rules Engine config
rules_config = RulesEngineV3Config(
    enable_events=True,
    max_scan_history=100,
    max_validation_history=200
)
```

---

## Testing V3 Code

### Unit Tests

```python
import unittest
from driver.vault_core_v3 import create_vault_core_v3
from driver.core.event_bus import EventBus, EntryCreated

class TestVaultV3(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.vault = create_vault_core_v3(
            vault_path=Path("./test.vault"),
            event_bus=self.event_bus,
            enable_events=True
        )
        
    def test_entry_creation_emits_event(self):
        events = []
        self.vault.on_entry_created(lambda e: events.append(e))
        
        entry = VaultEntry(
            entry_id="test-001",
            entry_type=VaultEntryType.DOCUMENT,
            title="Test",
            content=b"Content"
        )
        
        self.vault.store(entry)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].entry_id, "test-001")
```

### Integration Tests

```python
def test_full_pipeline():
    """Test full document ingest pipeline"""
    config = NexusConfig(
        vault_path=Path("./test.vault"),
        project_root=Path("./test_project"),
        enable_events=True
    )
    
    orchestrator = create_nexus_orchestrator(config)
    
    # Ingest document
    result = orchestrator.ingest_document(Path("./test.md"))
    
    assert result['success'] is True
    assert 'document_id' in result
    assert 'entities_extracted' in result
    
    # Search for it
    search_results = orchestrator.search("test content")
    assert len(search_results['results']) > 0
    
    orchestrator.shutdown()
```

---

## Performance Considerations

### Event Overhead

Events add minimal overhead (~0.1-0.5ms per event):

```python
# Disable events for performance-critical sections
vault.enable_events(False)

# Bulk operations
for i in range(10000):
    vault.store(entry)

# Re-enable events
vault.enable_events(True)
```

### Async Event Processing

For high-throughput scenarios:

```python
config = EventBusConfig(
    enable_async=True,      # Process events asynchronously
    async_queue_size=1000   # Large queue for bursts
)

event_bus = EventBus(config=config)
event_bus.start_async_processing()
```

### Batch Operations

```python
# Batch publish events
events = [
    EntryCreated(entry_id=f"doc-{i}", ...)
    for i in range(100)
]

event_bus.publish_batch(events, async_mode=True)
```

---

## Troubleshooting

### Events Not Firing

```python
# Check if events are enabled
vault = create_vault_core_v3(
    vault_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True  # ← Must be True
)

# Verify EventBus is set
vault.set_event_bus(event_bus)

# Check subscription
subscription_id = vault.on_entry_created(handler)
print(f"Subscribed: {subscription_id}")
```

### EventBus Not Receiving Events

```python
# Verify EventBus is passed to modules
fts5 = create_fts5_indexer_v3(
    db_path=Path("./data.vault"),
    event_bus=event_bus,  # ← Must pass event_bus
    enable_events=True
)

# Check handler registration
stats = event_bus.get_stats()
print(f"Subscriptions: {stats['active_subscriptions']}")
```

### Performance Issues

```python
# Disable events temporarily
orchestrator.container.resolve("event_bus").clear_handlers()

# Or disable per-module
vault.enable_events(False)
fts5.enable_events(False)

# Check event history size
config = EventBusConfig(
    max_history=100  # Reduce from default 1000
)
```

---

## Best Practices

### 1. Always Use EventBus

```python
# ✅ Good: Shared EventBus
event_bus = EventBus()
vault = create_vault_core_v3(..., event_bus=event_bus)
fts5 = create_fts5_indexer_v3(..., event_bus=event_bus)

# ❌ Bad: Separate EventBus instances
vault = create_vault_core_v3(..., event_bus=EventBus())
fts5 = create_fts5_indexer_v3(..., event_bus=EventBus())
```

### 2. Use Orchestrator for Complex Workflows

```python
# ✅ Good: Orchestrator manages dependencies
orchestrator = create_nexus_orchestrator(config)
result = orchestrator.ingest_document(doc)

# ❌ Bad: Manual coordination
vault = create_vault_core_v3(...)
fts5 = create_fts5_indexer_v3(...)
rules = create_rules_engine_v3(...)
# ... complex manual coordination
```

### 3. Subscribe to Events Early

```python
# ✅ Good: Subscribe before operations
vault.on_entry_created(handler)
vault.store(entry)

# ❌ Bad: Subscribe after operations
vault.store(entry)
vault.on_entry_created(handler)  # Won't receive past events
```

### 4. Graceful Shutdown

```python
# ✅ Good: Explicit shutdown
try:
    orchestrator.ingest_document(doc)
finally:
    orchestrator.shutdown()

# ❌ Bad: No cleanup
orchestrator.ingest_document(doc)
# Process ends without cleanup
```

---

## FAQ

### Q: Do I need to migrate all modules at once?

**A**: No! You can migrate incrementally. Use adapters to wrap V2 modules and gradually replace them with V3 versions.

### Q: Will V3 break my existing V2 code?

**A**: No. V2 modules continue to work. V3 modules have the same API as V2, plus events.

### Q: What if I don't want events?

**A**: Set `enable_events=False` when creating modules. They work identically to V2 without events.

### Q: How do I debug event flow?

**A**: Use `event_bus.get_event_history()` and `event_bus.get_stats()` for observability.

### Q: Can I mix V2 and V3 modules?

**A**: Yes! Use adapters to wrap V2 modules with V3 event support.

### Q: What's the performance impact of events?

**A**: Minimal (~0.1-0.5ms per event). Use async mode for high-throughput scenarios.

### Q: Should I use Orchestrator or direct modules?

**A**: Use Orchestrator for complex workflows and new code. Use direct modules for fine-grained control.

---

## Next Steps

1. **Read**: [V3 Architecture Overview](NEXUS-V3-ARCHITECTURE-UNIFIED.md)
2. **Explore**: [Orchestrator API](../driver/nexus_orchestrator_v3.py)
3. **Test**: Run `python driver/test_v3_modules_quick.py`
4. **Experiment**: Try examples in this guide
5. **Contribute**: Submit PRs with V3 enhancements

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Andrian0123/Bober-drive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Andrian0123/Bober-drive/discussions)
- **Documentation**: [docs/](.)

---

**Happy migrating to V3! 🚀**
