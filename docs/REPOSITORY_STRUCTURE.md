# 📖 GitHub Repository Structure

## What's Here

**Bober-Drive** — High-performance local-first full-text search engine.

This repository contains:

### 📂 Core Files
- **`README.md`** — Main documentation (start here)
- **`quick_agent_start.py`** — Quick demo script
- **`requirements.txt`** — Python dependencies
- **`pyproject.toml`** — Project metadata
- **`LICENSE`** — MIT License

### 📂 Source Code (`driver/`)
- **`nexus_autonomous_daemon.py`** — Main daemon (658 lines)
- **`file_content_cache_manager.py`** — FCCM cache layer (404 lines)
- **`nexus_orchestrator_v3.py`** — Pipeline orchestrator (851 lines)
- **`nexus_graphify_v3.py`** — Document parsing (398 lines)
- **`nexus_file_system_mapper_v3.py`** — File scanning (606 lines)

### 🧪 Tests
- **`test_fccm_integration.py`** — FCCM tests (10 tests, all passing)
- **`test_autonomous_daemon_e2e.py`** — E2E tests (9 tests, all passing)
- **`test_integration.py`** — Integration tests
- **`test_lsp_e2e.py`** — LSP server tests

### 📚 Documentation
- **`docs/AUTONOMOUS_DAEMON_QUICKSTART.md`** — 5-minute quick start
- **`docs/INTEGRATION_WITH_PROFIA.md`** — Integration guide
- **`RELEASE_NOTES_v3.0.1.md`** — v3.0.1 features
- **`docs/`** — Additional documentation

### 🛠️ Tools & Config
- **`nexus_grpc_adapter.py`** — gRPC API server
- **`docker-compose.yml`** — Docker setup
- **`vscode-extension/`** — VS Code extension
- **`.github/workflows/`** — CI/CD pipelines

---

## Getting Started

1. **Read** — Start with [README.md](README.md)
2. **Install** — `pip install -r requirements.txt`
3. **Demo** — `python quick_agent_start.py`
4. **Test** — `python test_fccm_integration.py`
5. **Integrate** — Follow [Integration Guide](docs/INTEGRATION_WITH_PROFIA.md)

---

## Key Metrics (v3.0.1)

- **Index Time**: 8-15 seconds (570 files)
- **Search Latency**: 12-25 ms
- **Cache Speedup**: 84-100x (FCCM new in v3.0.1)
- **Memory**: <50 MB
- **Tests Passing**: 19/19 ✅

---

## Support & Contributing

- **Issues**: [GitHub Issues](https://github.com/Andrian0123/Bober-drive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Andrian0123/Bober-drive/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

Made with ❤️ for developers who value privacy and performance.
