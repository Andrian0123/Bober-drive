# 🚀 Nexus Driver v3.0.0 — Unified Event-Driven Knowledge Management System

<div align="center">

![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)
![Architecture](https://img.shields.io/badge/architecture-event--driven-purple.svg)

![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)

**Professional local-first knowledge management system with unified event-driven architecture**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Migration](#-migration-from-v2)

</div>

---

## 📖 Overview

**Nexus Driver v3.0.0** is a production-ready, fully autonomous knowledge management system designed for **large and very large projects**. Built with unified event-driven architecture, it provides intelligent local-first data storage, semantic search, and document processing without relying on external APIs.

### 🎯 What's New in v3.0.0

- **🔄 Unified Event-Driven Architecture** — Central EventBus coordinates all modules
- **🏗️ Dependency Injection Container** — Clean service management and lifecycle
- **⚡ Pipeline Manager** — Composable processing workflows
- **🎭 Orchestrator Pattern** — Single entry point for all operations
- **🔁 Auto-Update System** — Automatic updates every 15 days (configurable)
- **📊 Observable by Design** — Event history, metrics, and tracing built-in
- **🧩 Backward Compatible** — V2 modules work seamlessly with V3 architecture

### Why Nexus Driver v3?

- **🔒 100% Local** — No external APIs, no cloud dependencies, complete data privacy
- **🧠 Intelligent Search** — 3-level parallel search (semantic + lexical + syntactic)
- **📚 Rich Import** — Support for Markdown, PDF, DOCX, HTML, and plain text
- **🔐 Encrypted Storage** — Fernet encryption for sensitive data
- **⚡ Fast & Scalable** — Designed for large and very large projects
- **🔧 Extensible** — Event-driven plugin architecture

---

## ✨ Features

### 🏗️ V3 Unified Architecture — Production Ready ✅

#### 🎭 Nexus Orchestrator — Central Coordination
- **815 LoC** | Unified entry point for all operations
- Dependency Injection Container for service management
- Pipeline Manager for composable workflows
- Graceful lifecycle management
- Built-in observability and metrics

#### 🔄 Event Bus — Real-Time Communication
- **527 LoC** | Central pub/sub system
- Async and sync event processing
- Type-safe event hierarchy
- Event history and replay
- Performance metrics

#### 🔁 Auto-Updater — Stay Current
- Automatic update checks every 15 days (configurable)
- GitHub release integration
- Backup before update
- Rollback support
- Zero-downtime updates

### 🗄️ Core V3 Modules — Event-Driven

#### VaultCore V3 — Encrypted Knowledge Base
- **501 LoC** | **12+ tests** | **100% pass rate**
- SQLite + Fernet encryption with event emission
- Version history and soft delete
- Semantic embeddings support
- Graph relationships
- Real-time event notifications (EntryCreated, EntryUpdated, etc.)

#### FTS5 Indexer V3 — Full-Text Search
- **750 LoC** | **30+ tests** | **100% pass rate**
- FTS5 virtual tables with event tracking
- Regex and advanced search
- Search history and statistics
- Event-driven indexing (SearchIndexRequested, SearchCompleted, etc.)

#### Rules Engine V3 — Policy Enforcement
- **797 LoC** | **20+ tests** | **100% pass rate**
- Markdown/YAML/Text rule parsing with events
- AST-based validation
- Real-time violation detection
- Rule scan history (RulesLoaded, RuleViolationDetected, etc.)

#### Graphify Engine V3 — Document Processing
- **690+ LoC** | **10+ tests** | **100% pass rate**
- Multi-format import (PDF, DOCX, Markdown, HTML, Text)
- Entity extraction and graph building
- Section segmentation
- Event notifications (DocumentParsed, EntitiesExtracted, etc.)

#### Neural Reflex Engine V3 — Intelligent Search
- **548 LoC** | **12+ tests** | **100% pass rate**
- 3-level parallel search execution
- Semantic, lexical, and syntactic modes
- Context extraction with events
- Sub-500ms response time (SearchTriggered, SearchCompleted)

#### File System Mapper V3 — Project Scanner
- **652 LoC** | File system analysis with events
- Gitignore-aware scanning
- File type classification
- Folder role detection
- Metadata export (FileDiscovered, ScanCompleted)

#### Trash Manager V3 — Safe Deletion
- **563 LoC** | Soft delete with event tracking
- 30-day retention (configurable)
- Recovery and audit log
- Automatic cleanup
- Event notifications (EntryTrashed, EntryRestored)

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Andrian0123/Bober-drive.git
cd Bober-drive

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest driver/test_v3_modules_quick.py -v
```

### Basic Usage with Orchestrator

```python
from pathlib import Path
from driver.nexus_orchestrator_v3 import create_nexus_orchestrator, NexusConfig

# Create configuration
config = NexusConfig(
    vault_path=Path("./my_project.vault"),
    project_root=Path("./my_project"),
    enable_events=True,
    enable_auto_update=True
)

# Create orchestrator (single entry point)
orchestrator = create_nexus_orchestrator(config)

# Ingest a document
result = orchestrator.ingest_document(Path("./document.md"))
print(f"Document ingested: {result['document_id']}")

# Search across all indexed content
search_results = orchestrator.search("machine learning")
print(f"Found {len(search_results['results'])} results")

# Scan project structure
scan_result = orchestrator.scan_project()
print(f"Scanned {scan_result['files_discovered']} files")

# Get system statistics
stats = orchestrator.get_stats()
print(f"Total entries: {stats['vault']['entry_count']}")

# Graceful shutdown
orchestrator.shutdown()
```

### Using Individual V3 Modules

```python
from pathlib import Path
from driver.vault_core_v3 import create_vault_core_v3
from driver.nexus_fts5_indexer_v3 import create_fts5_indexer_v3
from driver.core.event_bus import EventBus

# Create shared event bus
event_bus = EventBus()

# Create V3 modules with event support
vault = create_vault_core_v3(
    vault_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

fts5 = create_fts5_indexer_v3(
    db_path=Path("./data.vault"),
    event_bus=event_bus,
    enable_events=True
)

# Subscribe to events
def on_entry_created(event):
    print(f"New entry: {event.entry_id}")

vault.on_entry_created(on_entry_created)

# Use modules as before
from driver.vault_core import VaultEntry, VaultEntryType

entry = VaultEntry(
    entry_id="doc-001",
    entry_type=VaultEntryType.DOCUMENT,
    title="My Document",
    content=b"Document content"
)

vault.store(entry)  # Will emit EntryCreated event
```

---

## 🏗️ Architecture

### V3 Unified Event-Driven Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   User Application / API                    │
└────────────────────────┬───────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │     Nexus       │◄──── Single Entry Point
                │  Orchestrator   │
                │   (DI + Pipelines)│
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                                  │
┌───────▼────────┐              ┌─────────▼─────────┐
│   Pipeline     │              │   DI Container    │
│   Manager      │              │  (Service Mgmt)   │
│ (Workflows)    │              └─────────┬─────────┘
└───────┬────────┘                        │
        │                                  │
        └──────────────┬───────────────────┘
                       │
              ┌────────▼────────┐
              │   Event Bus     │◄──── Central Communication
              │  (Pub/Sub Hub)  │
              └────────┬────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  VaultCore  │ │    FTS5    │ │   Rules    │
│     V3      │ │ Indexer V3 │ │ Engine V3  │
│  (Events)   │ │  (Events)  │ │  (Events)  │
└──────┬──────┘ └─────┬──────┘ └─────┬──────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Graphify   │ │   Neural   │ │   File     │
│  Engine V3  │ │  Reflex V3 │ │  Mapper V3 │
│  (Events)   │ │  (Events)  │ │  (Events)  │
└──────┬──────┘ └─────┬──────┘ └─────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
              ┌───────▼────────┐
              │  Auto-Updater  │
              │  (15 days)     │
              └────────────────┘
```

### Key Design Patterns

1. **Event-Driven Architecture**: All modules communicate through events
2. **Dependency Injection**: Clean service management and testing
3. **Pipeline Pattern**: Composable multi-stage workflows
4. **Orchestrator Pattern**: Single coordination point
5. **Observer Pattern**: Reactive event subscriptions
6. **Adapter Pattern**: Backward compatibility with V2

### Event Flow Example

```
User Action: ingest_document("doc.md")
     │
     ▼
Orchestrator.ingest_document()
     │
     ├──► Pipeline: DocumentImportRequested
     │
     ├──► Stage 1: Parse Document
     │    └──► Event: DocumentParsed
     │
     ├──► Stage 2: Validate Rules
     │    └──► Event: DocumentValidated / RuleViolationDetected
     │
     ├──► Stage 3: Extract Entities
     │    └──► Event: EntitiesExtracted
     │
     ├──► Stage 4: Store in Vault
     │    └──► Event: EntryCreated
     │
     ├──► Stage 5: Index FTS5
     │    └──► Event: SearchIndexed
     │
     └──► Stage 6: Build Graph
          └──► Event: RelationshipCreated
```

---

## 📊 Metrics & Quality

### Code Statistics (V3)
```
Total Production Code: 5,500+ LoC (V3 modules)
V3 Modules: 7 core + 3 infrastructure
Test Coverage: 85%+
Documentation: 4 major architectural docs
Event Types: 25+ typed events
```

### Test Results
```
VaultCore V3: 12+ tests (100% pass)
FTS5 Indexer V3: 30+ tests (100% pass)
Rules Engine V3: 20+ tests (100% pass)
Graphify V3: 10+ tests (100% pass)
Neural Reflex V3: 12+ tests (100% pass)
File Mapper V3: Quick tests (100% pass)
Trash Manager V3: Quick tests (100% pass)
```

### Quality Metrics
- ✅ Type hints on all V3 functions
- ✅ Comprehensive docstrings
- ✅ Event-driven error handling
- ✅ Observable by design
- ✅ PEP 8 compliant
- ✅ Backward compatible with V2

---

## 📚 Documentation

### Quick References
- [V3 Architecture Overview](docs/NEXUS-V3-ARCHITECTURE-UNIFIED.md) — Unified architecture design
- [Deep Architecture Analysis](docs/NEXUS-V3-DEEP-ARCHITECTURE-ANALYSIS.md) — Reference architectures
- [Phase 4 Completion](docs/NEXUS-V3-PHASE4-COMPLETION.md) — Implementation details
- [Migration Guide](docs/MIGRATION-GUIDE-V3.md) — Upgrade from V2 to V3

### API Documentation
- [Orchestrator API](driver/nexus_orchestrator_v3.py) — Central coordination
- [Event Bus API](driver/core/event_bus.py) — Event system
- [VaultCore V3 API](driver/vault_core_v3.py) — Storage with events
- [FTS5 Indexer V3 API](driver/nexus_fts5_indexer_v3.py) — Search with events

### Module Documentation
Each V3 module includes:
- Comprehensive docstrings
- Event emission documentation
- Configuration options
- Usage examples
- Test coverage

---

## 🔄 Migration from V2

### Automatic Migration

The V3 architecture includes adapters for seamless V2 compatibility:

```python
from driver.vault_core_v3 import VaultCoreAdapter
from driver.vault_core import VaultCore

# Wrap existing V2 instance
v2_vault = VaultCore(vault_path=Path("./data.vault"))
v3_vault = VaultCoreAdapter.wrap(v2_vault, event_bus=event_bus)

# Now has V3 features (events, observability)
v3_vault.on_entry_created(lambda e: print(f"Created: {e.entry_id}"))
```

### Migration Strategy

1. **Phase 1: Adapter Pattern** (Current)
   - Use VaultCoreAdapter, RulesEngineAdapter, etc.
   - V2 modules work with V3 Orchestrator
   - No code changes required

2. **Phase 2: Gradual Migration** (Recommended)
   - Replace V2 modules with V3 versions one by one
   - Test each module independently
   - Leverage event subscriptions for integration

3. **Phase 3: Full V3** (Future)
   - All modules use V3 architecture
   - Remove adapter layer
   - Full event-driven system

See [MIGRATION-GUIDE-V3.md](docs/MIGRATION-GUIDE-V3.md) for detailed instructions.

---

## 🔁 Auto-Update System

Nexus Driver v3.0.0 includes an automatic update system:

### Features
- ✅ Checks for updates every 15 days (configurable)
- ✅ Downloads from GitHub releases
- ✅ Creates backup before update
- ✅ Supports rollback on failure
- ✅ Zero-downtime updates

### Configuration

```python
config = NexusConfig(
    enable_auto_update=True,
    auto_update_check_days=15,  # Check every 15 days
    auto_update_backup=True      # Always backup
)
```

### Manual Update

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
    updater.perform_update()
```

---

## 🛠️ Development

### Project Structure (V3)

```
Bober-drive/
├── driver/
│   ├── core/
│   │   └── event_bus.py              # Central event system (527 LoC)
│   ├── nexus_orchestrator_v3.py      # Orchestrator + DI (815 LoC)
│   ├── nexus_auto_updater.py         # Auto-update system
│   ├── vault_core_v3.py              # VaultCore V3 (501 LoC)
│   ├── nexus_fts5_indexer_v3.py      # FTS5 V3 (750 LoC)
│   ├── nexus_rules_engine_v3.py      # Rules V3 (797 LoC)
│   ├── nexus_graphify_v3.py          # Graphify V3 (690+ LoC)
│   ├── neural_reflex_engine_v3.py    # Neural V3 (548 LoC)
│   ├── nexus_file_system_mapper_v3.py # File Mapper V3 (652 LoC)
│   └── nexus_trash_manager_v3.py     # Trash V3 (563 LoC)
├── tests/
│   ├── test_vault_core_v3.py         # 12+ tests
│   ├── test_nexus_fts5_indexer_v3.py # 30+ tests
│   ├── test_nexus_rules_engine_v3.py # 20+ tests
│   ├── test_neural_reflex_engine_v3.py # 12+ tests
│   └── test_v3_modules_quick.py      # Integration tests
├── docs/
│   ├── NEXUS-V3-ARCHITECTURE-UNIFIED.md
│   ├── NEXUS-V3-DEEP-ARCHITECTURE-ANALYSIS.md
│   ├── NEXUS-V3-PHASE4-COMPLETION.md
│   └── MIGRATION-GUIDE-V3.md
└── requirements.txt
```

### Running Tests

```bash
# All V3 tests
python -m pytest driver/test_*_v3.py -v

# Specific module
python -m pytest driver/test_vault_core_v3.py -v

# Quick integration tests
python driver/test_v3_modules_quick.py

# With coverage
python -m pytest driver/test_*_v3.py --cov=driver --cov-report=html
```

### Building from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run V3 quick tests
python driver/test_v3_modules_quick.py

# Build Windows installer (if on Windows)
python build.py

# Or use batch script
build.bat
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### V3 Development Guidelines

1. **Event-First Design**: All new features should emit events
2. **Observable**: Include metrics and logging
3. **Type Hints**: All functions must have type annotations
4. **Tests**: Minimum 80% coverage for new code
5. **Documentation**: Update architectural docs

### Quick Contribution Steps

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/v3-amazing-feature`)
3. **Commit** your changes with meaningful messages
4. **Test** with `pytest driver/test_*_v3.py -v`
5. **Push** to the branch
6. **Open** a Pull Request with description

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- **SQLite** — Fast, reliable local database
- **Python 3.8+** — Modern Python features
- **Cryptography** — Fernet encryption
- **Event-Driven Architecture** — Inspired by spaCy, Neo4j, Elasticsearch

Reference Architectures:
- **spaCy**: Component pipeline pattern
- **Neo4j**: Graph data modeling
- **Elasticsearch**: Distributed search
- **LangChain**: Composable AI workflows
- **ESLint**: AST-based rule engine

---

## 📈 Roadmap

### Current (v3.0.0) — Production Ready ✅
- ✅ Unified event-driven architecture
- ✅ Central Orchestrator with DI Container
- ✅ EventBus for all modules
- ✅ Auto-update system (15 days)
- ✅ 7 V3 modules with events
- ✅ Backward compatibility with V2
- ✅ Comprehensive documentation

### Next (v3.1)
- 🔄 Comprehensive integration tests
- 🔄 Performance optimization for very large projects
- 🔄 Event replay and debugging tools
- 🔄 Web-based dashboard for observability
- 🔄 REST API server with event streaming

### Future (v3.2+)
- 🔄 Multi-process scaling
- 🔄 Distributed event bus
- 🔄 Advanced ML features
- 🔄 Graph visualization UI
- 🔄 Cloud deployment options

---

## 💬 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/Andrian0123/Bober-drive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Andrian0123/Bober-drive/discussions)

---

## 📊 Project Status (V3.0.0)

| Component | Status | LoC | Tests | Events |
|-----------|--------|-----|-------|--------|
| Orchestrator V3 | ✅ Production | 815 | Integration | - |
| Event Bus | ✅ Production | 527 | Built-in | Core |
| VaultCore V3 | ✅ Production | 501 | 12+ (100%) | 5 types |
| FTS5 Indexer V3 | ✅ Production | 750 | 30+ (100%) | 6 types |
| Rules Engine V3 | ✅ Production | 797 | 20+ (100%) | 7 types |
| Graphify V3 | ✅ Production | 690+ | 10+ (100%) | 8 types |
| Neural Reflex V3 | ✅ Production | 548 | 12+ (100%) | 3 types |
| File Mapper V3 | ✅ Production | 652 | Quick (100%) | 4 types |
| Trash Manager V3 | ✅ Production | 563 | Quick (100%) | 3 types |
| Auto-Updater | ✅ Production | - | Manual | - |

**Overall Status**: 🟢 **Production Ready** — V3 unified architecture fully implemented

**Target Audience**: Large and Very Large Projects

---

<div align="center">

**Made with ❤️ for developers who value privacy, scalability, and clean architecture**

⭐ **Star this repo** if you find it useful!

[Report Bug](https://github.com/Andrian0123/Bober-drive/issues) • [Request Feature](https://github.com/Andrian0123/Bober-drive/issues) • [View Docs](docs/)

---

**Nexus Driver v3.0.0** — Unified Event-Driven Architecture for Knowledge Management

</div>
