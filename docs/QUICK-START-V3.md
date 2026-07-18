# 🚀 Quick Start Guide: Nexus Driver V3

Get started with Nexus Driver V3.0.0 in **5 minutes**.

---

## Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Git** (optional, for cloning)

---

## Installation

### Option 1: Clone from GitHub

```bash
git clone https://github.com/Andrian0123/Bober-drive.git
cd Bober-drive
pip install -r requirements.txt
```

### Option 2: Download Release

1. Go to [Releases](https://github.com/Andrian0123/Bober-drive/releases)
2. Download `nexus-driver-v3.0.0.zip`
3. Extract and run:

```bash
cd nexus-driver-v3.0.0
pip install -r requirements.txt
```

---

## Verify Installation

```bash
python driver/test_v3_modules_quick.py
```

**Expected output:**
```
Testing FileSystemMapperV3...
✓ Scan completed
✓ Files discovered

Testing TrashManagerV3...
✓ Soft delete works
✓ Restore works

✅ All tests passed!
```

---

## First Steps

### 1. Create Your First Vault

```python
from pathlib import Path
from driver.vault_core_v3 import create_vault_core_v3
from driver.vault_core import VaultEntry, VaultEntryType
from driver.core.event_bus import EventBus

# Create EventBus for event-driven communication
event_bus = EventBus()

# Create vault
vault = create_vault_core_v3(
    vault_path=Path("./my_knowledge.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
vault.on_entry_created(lambda e: print(f"✓ Created: {e.title}"))

# Create an entry
entry = VaultEntry(
    entry_id="doc-001",
    entry_type=VaultEntryType.DOCUMENT,
    title="My First Document",
    content=b"This is my first knowledge entry!",
    metadata={"tags": ["first", "test"]}
)

# Store it
vault.store(entry)
print("✅ Entry stored successfully!")

# Retrieve it
retrieved = vault.retrieve("doc-001")
print(f"Retrieved: {retrieved.title}")
```

### 2. Search Your Content

```python
from driver.nexus_fts5_indexer_v3 import create_fts5_indexer_v3

# Create FTS5 search engine
fts5 = create_fts5_indexer_v3(
    db_path=Path("./my_knowledge.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to search events
fts5.on_search_completed(lambda e: print(f"✓ Found {e.result_count} results in {e.elapsed_ms}ms"))

# Search
results = fts5.fulltext_search("knowledge", limit=10)

for result in results:
    print(f"- {result['title']}: {result['snippet']}")
```

### 3. Use the Orchestrator (Recommended)

```python
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig

# Create config
config = NexusConfig(
    vault_path=Path("./my_knowledge.vault"),
    project_root=Path("./my_project"),
    enable_events=True,
    enable_auto_update=True
)

# Create orchestrator (manages everything)
orchestrator = create_nexus_orchestrator(config)

# Ingest a document
result = orchestrator.ingest_document(Path("./README.md"))
print(f"✅ Ingested: {result['document_id']}")

# Search
search_results = orchestrator.search("nexus driver")
print(f"✅ Found {len(search_results['results'])} results")

# Scan project
scan_result = orchestrator.scan_project()
print(f"✅ Scanned {scan_result['files_discovered']} files")

# Get stats
stats = orchestrator.get_stats()
print(f"✅ Total entries: {stats['vault']['entry_count']}")

# Shutdown
orchestrator.shutdown()
```

---

## Common Tasks

### Import Documents

```python
from pathlib import Path
from driver.nexus_graphify_v3 import create_graphify_engine_v3

graphify = create_graphify_engine_v3(
    vault_core=vault,
    fts5_extension=fts5,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
graphify.on_document_parsed(lambda e: print(f"✓ Parsed: {e.document_id}"))

# Import PDF
doc = graphify.import_document(Path("./paper.pdf"))
print(f"✅ Imported: {doc.title}")
print(f"   Sections: {len(doc.sections)}")
print(f"   Entities: {len(doc.entities)}")
```

### Enforce Project Rules

```python
from driver.nexus_rules_engine_v3 import create_rules_engine_v3

rules = create_rules_engine_v3(
    project_root=Path("./my_project"),
    vault_core=vault,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to violations
rules.on_violation_detected(lambda e: print(f"⚠ Violation: {e.rule_title}"))

# Scan rules
parsed_rules = rules.scan_rules()
print(f"✅ Loaded {len(parsed_rules)} rules")

# Validate content
code = """
def my_function():
    pass  # TODO: implement
"""

violations = rules.validate_against_rules(code, "python")
if violations:
    print(f"⚠ Found {len(violations)} violations:")
    for v in violations:
        print(f"  - {v.rule_title}: {v.message}")
else:
    print("✅ No violations!")
```

### Scan Project Structure

```python
from driver.nexus_file_system_mapper_v3 import create_file_system_mapper_v3

mapper = create_file_system_mapper_v3(
    project_root=Path("./my_project"),
    vault_core=vault,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
mapper.on_scan_completed(lambda e: print(f"✓ Scanned {e.files_discovered} files"))

# Scan
files = mapper.scan_project()
print(f"✅ Found {len(files)} files")

# Analyze folders
mapper._analyze_folders()
print(f"✅ Analyzed {len(mapper.folders)} folders")

# Save to vault
mapper.save_to_vault()
print("✅ Metadata saved to vault")
```

### Intelligent Search

```python
from driver.neural_reflex_engine_v3 import create_neural_reflex_engine_v3

neural = create_neural_reflex_engine_v3(
    vault_core=vault,
    fts5_extension=fts5,
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
neural.on_search_completed(lambda e: print(f"✓ Search: {e.elapsed_ms}ms"))

# Trigger reflex search (3-level parallel)
response = neural.trigger_reflex("machine learning algorithms", timeout_ms=500)

print(f"✅ Found {len(response.results)} results")
for result in response.results[:3]:
    print(f"  - {result.title} (score: {result.score:.2f})")
    print(f"    Context: {result.context}")
```

---

## Event Subscription Examples

### Basic Event Handling

```python
from driver.core.event_bus import EventBus, EntryCreated, SearchCompleted

event_bus = EventBus()

# Subscribe to specific event
def on_entry_created(event: EntryCreated):
    print(f"New entry: {event.entry_id} - {event.title}")

subscription_id = event_bus.subscribe(EntryCreated, on_entry_created)

# Unsubscribe later
event_bus.unsubscribe(subscription_id)
```

### Multiple Event Types

```python
# Subscribe to multiple events
event_bus.subscribe(EntryCreated, lambda e: print(f"Created: {e.entry_id}"))
event_bus.subscribe(EntryUpdated, lambda e: print(f"Updated: {e.entry_id}"))
event_bus.subscribe(SearchCompleted, lambda e: print(f"Search: {e.result_count} results"))
```

### Event History

```python
# Get recent events
history = event_bus.get_event_history(limit=10)

for event in history:
    print(f"{event.timestamp}: {event.__class__.__name__}")
    print(f"  Data: {event.to_dict()}")
```

---

## Pipeline Examples

### Document Ingest Pipeline

```python
# Using Orchestrator (easiest)
orchestrator = create_nexus_orchestrator(config)

result = orchestrator.ingest_document(Path("./document.md"))

# Pipeline automatically:
# 1. Parses document
# 2. Validates against rules
# 3. Extracts entities
# 4. Stores in vault
# 5. Indexes for search
# 6. Builds graph relationships

print(f"Pipeline result: {result}")
```

### Custom Pipeline

```python
from driver.nexus_orchestrator_v3 import NexusPipeline, PipelineStage

# Create custom pipeline
pipeline = NexusPipeline("custom", orchestrator.container)

# Add stages
pipeline.add_stage(
    name="validate",
    handler=lambda data, container: {"valid": True, **data},
    stage_type=PipelineStage.VALIDATION
)

pipeline.add_stage(
    name="process",
    handler=lambda data, container: {"processed": True, **data},
    stage_type=PipelineStage.PROCESSING
)

# Execute
result = pipeline.execute({"input": "data"})
print(f"Custom pipeline result: {result}")
```

---

## Configuration

### Basic Configuration

```python
from driver.nexus_orchestrator_v3 import NexusConfig

config = NexusConfig(
    vault_path=Path("./data.vault"),
    project_root=Path("./project"),
    enable_events=True,
    enable_auto_update=True,
    auto_update_check_days=15
)
```

### Advanced Configuration

```python
config = NexusConfig(
    vault_path=Path("./data.vault"),
    project_root=Path("./project"),
    
    # Events
    enable_events=True,
    event_bus_max_history=1000,
    event_bus_async=True,
    
    # Auto-Update
    enable_auto_update=True,
    auto_update_check_days=15,
    auto_update_backup=True,
    
    # Performance
    max_workers=4,
    cache_size=1000,
    
    # Security
    encryption_key="your-encryption-key",
    
    # Features
    enable_neural_reflex=True,
    enable_file_mapper=True,
    enable_trash_manager=True
)
```

---

## Testing

### Run Quick Tests

```bash
python driver/test_v3_modules_quick.py
```

### Run Comprehensive Tests

```bash
python -m pytest driver/test_vault_core_v3.py -v
python -m pytest driver/test_nexus_fts5_indexer_v3.py -v
python -m pytest driver/test_nexus_rules_engine_v3.py -v
python -m pytest driver/test_neural_reflex_engine_v3.py -v
```

### Run All V3 Tests

```bash
python -m pytest driver/test_*_v3.py -v
```

---

## Auto-Update

### Enable Auto-Update

```python
config = NexusConfig(
    enable_auto_update=True,
    auto_update_check_days=15  # Check every 15 days
)

orchestrator = create_nexus_orchestrator(config)

# Auto-updater checks for updates in background
# Downloads and installs automatically if available
```

### Manual Update Check

```python
from driver.nexus_auto_updater import NexusAutoUpdater

updater = NexusAutoUpdater(
    current_version="3.0.0",
    repo_owner="Andrian0123",
    repo_name="Bober-drive"
)

# Check for updates
if updater.check_for_updates():
    print(f"New version available: {updater.latest_version}")
    
    # Perform update
    success = updater.perform_update()
    if success:
        print("✅ Update successful!")
    else:
        print("❌ Update failed")
```

---

## Troubleshooting

### Import Errors

```python
# Ensure driver/ is in Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Now imports work
from driver.vault_core_v3 import create_vault_core_v3
```

### Events Not Firing

```python
# Ensure events are enabled
vault = create_vault_core_v3(
    vault_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True  # ← Must be True
)

# Verify subscription
subscription_id = vault.on_entry_created(handler)
print(f"Subscribed: {subscription_id}")
```

### Database Locked

```python
# Close all connections before operations
vault.shutdown()

# Or use context manager
with create_vault_core_v3(...) as vault:
    vault.store(entry)
# Automatically closed
```

---

## Next Steps

1. **Read**: [Migration Guide](MIGRATION-GUIDE-V3.md) if upgrading from V2
2. **Explore**: [Architecture Overview](NEXUS-V3-ARCHITECTURE-UNIFIED.md)
3. **Deep Dive**: [API Documentation](../driver/)
4. **Experiment**: Try examples above
5. **Build**: Create your own knowledge management system!

---

## Examples

### Complete Example: Knowledge Base

```python
from pathlib import Path
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig

# Setup
config = NexusConfig(
    vault_path=Path("./knowledge.vault"),
    project_root=Path("./docs"),
    enable_events=True
)

orchestrator = create_nexus_orchestrator(config)

# Import documents
docs_dir = Path("./docs")
for doc_path in docs_dir.glob("**/*.md"):
    result = orchestrator.ingest_document(doc_path)
    print(f"✓ Imported: {result['document_id']}")

# Search
query = "architecture patterns"
results = orchestrator.search(query)

print(f"\n🔍 Search results for '{query}':")
for result in results['results'][:5]:
    print(f"  - {result['title']}")
    print(f"    Score: {result['score']:.2f}")
    print(f"    Snippet: {result['snippet'][:100]}...")
    print()

# Stats
stats = orchestrator.get_stats()
print(f"\n📊 Statistics:")
print(f"  Total entries: {stats['vault']['entry_count']}")
print(f"  Search history: {stats['fts5']['search_count']}")
print(f"  Files scanned: {stats.get('file_mapper', {}).get('files_count', 0)}")

# Cleanup
orchestrator.shutdown()
print("\n✅ Done!")
```

### Complete Example: Project Scanner

```python
from pathlib import Path
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig

# Setup
config = NexusConfig(
    vault_path=Path("./project.vault"),
    project_root=Path("./my_project"),
    enable_events=True
)

orchestrator = create_nexus_orchestrator(config)

# Scan project
print("🔍 Scanning project...")
result = orchestrator.scan_project()

print(f"\n📊 Scan results:")
print(f"  Files discovered: {result['files_discovered']}")
print(f"  Folders analyzed: {result['folders_analyzed']}")
print(f"  Patterns detected: {result.get('patterns_detected', 0)}")

# Get file stats
stats = orchestrator.get_stats()
file_mapper_stats = stats.get('file_mapper', {})

print(f"\n📁 File breakdown:")
for file_type, count in file_mapper_stats.get('by_type', {}).items():
    print(f"  {file_type}: {count} files")

# Cleanup
orchestrator.shutdown()
print("\n✅ Done!")
```

---

## Support

- **Documentation**: [docs/](.)
- **Issues**: [GitHub Issues](https://github.com/Andrian0123/Bober-drive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Andrian0123/Bober-drive/discussions)

---

**Ready to build amazing things! 🚀**
