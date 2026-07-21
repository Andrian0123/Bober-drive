# 🚀 Bober-Drive v3.0.1

<div align="center">

![Version](https://img.shields.io/badge/version-3.0.1-brightgreen.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)

**High-performance local-first full-text search engine for documentation and knowledge bases**

[Features](#features) • [Quick Start](#quick-start) • [Performance](#performance) • [Install](#installation) • [Docs](#documentation)

</div>

---

## What is Bober-Drive?

Bober-Drive is a **production-ready, autonomous indexing engine** designed for developers who want fast, local-only full-text search without external dependencies.

✨ **Perfect for:**
- 📚 Documentation search (Markdown, JSON, YAML, Text)
- 🔍 Knowledge base indexing (570+ files in <15 seconds)
- 🛡️ Privacy-first applications (100% local, zero cloud)
- ⚡ IDE integrations (VS Code, IntelliJ)
- 🔌 Microservices (gRPC API included)

---

## ⭐ Key Features

### 🎯 Built for Speed
- **<15 seconds** to index 570+ files
- **<25ms** average search latency
- **84-100x faster** cache hits with FCCM (v3.0.1 new!)
- **<50MB** memory footprint

### 🔒 Privacy First
- 100% local processing
- No external APIs
- No data transmission
- Offline-first architecture

### 🧠 Smart Search
- Full-text search with FTS5
- File content caching (FCCM)
- Semantic relevance scoring
- Graceful fallback on errors

### 🔧 Developer Friendly
- Minimal dependencies
- Single-file setup (SQLite)
- Python 3.11+ support
- gRPC + REST APIs
- VS Code extension included

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Andrian0123/Bober-drive.git
cd Bober-drive

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from driver.nexus_autonomous_daemon import create_autonomous_daemon

# Initialize with documentation folder
daemon = create_autonomous_daemon({
    'project_root': './docs',
    'vault_path': './storage/index.vault',
    'enable_file_cache': True,  # FCCM enabled (default)
})

# Start indexing
daemon.start()  # Phase 1: INITIALIZING → Phase 2: READY

# Search
results = daemon.search("your query", limit=10)
for hit in results['hits']:
    print(f"{hit['file_path']}: {hit['score']:.2f}")

# Graceful shutdown
daemon.stop(graceful=True)
```

### Docker

```bash
docker-compose up -d
# Daemon runs on localhost:50051 (gRPC)
```

---

## 📊 Performance

### Benchmarks (v3.0.1)

| Metric | Value | Notes |
|--------|-------|-------|
| **Index Time** | 8-15 sec | 570 files, INITIALIZING phase |
| **Search Latency** | 12-25 ms | FTS5 + FCCM cache |
| **Memory Usage** | <50 MB | Full indexing mode |
| **Cache Speedup** | 84-100x | v3.0.1 FCCM optimization |
| **Max File Size** | 100 MB | Chunked reading support |

### What's New in v3.0.1

✨ **FCCM Integration** — File Content Cache Manager  
- LRU cache with 500MB default limit
- Automatic invalidation on file changes
- 84-100x faster repeated reads
- Memory-efficient with eviction

```python
# Check cache statistics
stats = daemon.get_cache_stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache size: {stats['size_mb']}MB")
```

---

## 📁 Supported Formats

- ✅ **Markdown** (.md, .markdown)
- ✅ **Plain Text** (.txt)
- ✅ **JSON** (.json)
- ✅ **YAML** (.yaml, .yml)
- ✅ **Python Docstrings**

---

## 🏗️ Architecture

### 3-Phase Autonomous Operation

```
Phase 1: INITIALIZING
├─ Full project scan
├─ Parse all files
├─ Create FTS5 index
└─ → Phase 2: READY

Phase 2: READY
├─ Accept search queries
├─ Return results <25ms
├─ Use FCCM cache
└─ Metrics tracking

Phase 3: MONITORING (Coming)
└─ Automatic file watching
```

### Core Components

| Component | Purpose | Status |
|-----------|---------|--------|
| **Autonomous Daemon** | Main orchestrator | ✅ v3.0.1 |
| **FTS5 Indexer** | Full-text search | ✅ Production |
| **FCCM** | File caching layer | ✅ v3.0.1 NEW |
| **Event Bus** | Async events | ✅ Included |
| **gRPC Adapter** | API server | ✅ Ready |

---

## 🛠️ API Examples

### Python

```python
# Direct Python usage
from driver.nexus_autonomous_daemon import create_autonomous_daemon

daemon = create_autonomous_daemon(config)
daemon.start()

# Search
results = daemon.search("api documentation")

# Metrics
metrics = daemon.get_metrics()
status = daemon.get_status()
```

### gRPC

```python
# Use via gRPC
from nexus_grpc_adapter import NexusGRPCAdapter

adapter = NexusGRPCAdapter(orchestrator, port=50051)
adapter.start()

# Client connects to localhost:50051
```

### VS Code Extension

```
Ctrl+Shift+P → "Search Documentation"
```

---

## 📚 Documentation

- **[Quick Start Guide](docs/AUTONOMOUS_DAEMON_QUICKSTART.md)** — Get running in 5 minutes
- **[Integration Guide](docs/INTEGRATION_WITH_PROFIA.md)** — Integrate into your project
- **[Architecture Deep Dive](docs/NEXUS-ARCHITECTURE-VISUAL.md)** — System design
- **[Release Notes](docs/RELEASE_NOTES_v3.0.1.md)** — v3.0.1 updates

---

## ✅ Tests & Quality

- ✅ **19/19 tests passing** (10 FCCM + 9 E2E)
- ✅ **100% type hints** throughout codebase
- ✅ **Comprehensive error handling**
- ✅ **Production-ready** (used internally)

### Run Tests

```bash
# All tests
python test_fccm_integration.py       # FCCM tests (10)
python test_autonomous_daemon_e2e.py  # E2E tests (9)

# Or with pytest
pytest test_*.py -v
```

---

## 🌍 Use Cases

### 📖 Documentation Search
```python
# Index your docs folder
daemon = create_autonomous_daemon({'project_root': './docs'})
daemon.start()

# Users search: "How to configure cache?"
results = daemon.search("cache configuration")
```

### 🔌 Backend Integration
```python
# Embed in FastAPI/Django
results = daemon.search(user_query, limit=10)
return JSONResponse(results)
```

### 🛠️ IDE Plugin
```
VS Code → Search Documentation
IntelliJ → Integration planned
```

---

## 🚀 Deployment

### Local Machine
```bash
python quick_agent_start.py
```

### Production
```bash
# Via Docker
docker-compose up -d

# Via systemd
systemctl start bober-drive
```

### Cloud
- AWS, Azure, GCP compatible
- No special setup needed
- Lightweight container

---

## 📈 Roadmap

### Current (v3.0.1) ✅
- ✅ FCCM cache optimization
- ✅ 19/19 tests passing
- ✅ Production-ready

### Next (v3.1)
- 🔄 Automatic file monitoring (Phase 3)
- 🔄 Semantic search improvements
- 🔄 Web dashboard

### Future (v3.2+)
- 🔄 Multi-process scaling
- 🔄 Distributed indexing
- 🔄 Advanced ML features

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps

1. **Fork** the repository
2. **Create** a feature branch
3. **Test** with `pytest test_*.py -v`
4. **Submit** a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/Andrian0123/Bober-drive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Andrian0123/Bober-drive/discussions)
- **Docs**: [Documentation](docs/)

---

<div align="center">

**Made for developers who value performance, privacy, and simplicity**

⭐ **[Star us on GitHub](https://github.com/Andrian0123/Bober-drive)** if you find this useful!

[Issues](https://github.com/Andrian0123/Bober-drive/issues) • [Discussions](https://github.com/Andrian0123/Bober-drive/discussions) • [Docs](docs/)

**Bober-Drive v3.0.1** — Fast. Local. Private. 🚀

</div>
