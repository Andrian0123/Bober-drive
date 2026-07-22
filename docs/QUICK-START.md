# Nexus Driver v3.0.0 Integration — Quick Start

## Status: ✅ FULLY OPERATIONAL

All 9 integration items completed and tested.

---

## ⚡ Quick Start (5 minutes)

### 1. Prerequisites
```bash
# Windows
python --version  # Python 3.10+
pip list | findstr grpcio  # Check if grpcio is installed
```

### 2. Generate Proto Stubs (Already Done ✅)
```bash
# Proto stubs are already generated:
# - nexus_integration_pb2.py
# - nexus_integration_pb2_grpc.py
```

### 3. Run Integration Tests (Verify System)
```bash
cd F:\PROFI-A\Bober-drive
python -m pytest test_integration.py -v
# Expected: 13/13 PASSED in ~0.9s
```

### 4. Start gRPC Server
```bash
# Option A: Run demo (30 seconds)
python run_integration_demo.py

# Option B: Start adapter manually
python -c "
from pathlib import Path
from nexus_orchestrator_v3 import NexusOrchestrator, NexusConfig
from nexus_grpc_adapter import NexusGRPCAdapter

config = NexusConfig(
    project_root=Path.home() / '.nexus' / 'demo_project',
    vault_path=Path.home() / '.nexus' / 'integration' / 'vault.db',
    enable_auto_update=False
)
orchestrator = NexusOrchestrator(config)
adapter = NexusGRPCAdapter(orchestrator, port=50051)
adapter.start()
"
```

### 5. Test from Node.js Client
```bash
# In another terminal
node nexus_client.js

# Or use from your Node.js code:
const { NexusSearchClient } = require('./nexus_client');
const client = new NexusSearchClient('localhost:50051');
const results = await client.search('my query');
```

---

## 📦 Deployment Checklist

For PROFI-A Backend Deployment:

- [ ] Review `nexus_integration.proto` for API contract
- [ ] Verify proto files generated: `nexus_integration_pb2*.py`
- [ ] Run tests: `pytest test_integration.py -v` (must be 13/13 ✅)
- [ ] Configure environment:
  ```bash
  export NEXUS_AUTO_UPDATE=false
  export NEXUS_VAULT_PATH=~/.nexus/integration/vault.db
  ```
- [ ] Start adapter: `python nexus_grpc_adapter.py`
- [ ] Connect Node.js client: verify on port 50051
- [ ] Load test with production data
- [ ] Monitor logs for errors

---

## 🔧 Configuration

### Auto-Update: DISABLED ✅
```python
config = NexusConfig(
    project_root=path,
    vault_path=path,
    enable_auto_update=False  # ← CRITICAL
)
```

### Server Port
```python
adapter = NexusGRPCAdapter(orchestrator, port=50051)
```

### Vault Storage
- Default: `~/.nexus/integration/vault.db`
- SQLite (cross-platform, no external deps)
- Supports all platforms: Windows ✅, Linux ✅, macOS ✅, Android ✅

---

## 📊 Test Results

```
test_integration.py::TestIntegrationSetup (2 tests)           ✅ PASS
test_integration.py::TestSearchIntegration (2 tests)          ✅ PASS
test_integration.py::TestIngestIntegration (3 tests)          ✅ PASS
test_integration.py::TestScanProjectIntegration (2 tests)     ✅ PASS
test_integration.py::TestHealthCheckIntegration (1 test)      ✅ PASS
test_integration.py::TestAutoUpdateDisabled (2 tests)         ✅ PASS
test_integration.py::TestEventEmission (1 test)               ✅ PASS

Total: 13/13 ✅ in 0.88s
```

---

## 🏗️ Architecture

```
Node.js Backend      Python gRPC Adapter      Nexus Orchestrator
   (Client)         (Port 50051)                 (v3.0.0)
      │                  │                          │
      ├──gRPC call──────>│                          │
      │                  │                          │
      │                  ├──SDK call───────────────>│
      │                  │                          │
      │                  │                          ├─> VaultCore (SQLite)
      │                  │                          ├─> FTS5 Indexer
      │                  │                          ├─> Rules Engine
      │                  │                          ├─> Graphify
      │                  │                          └─> FileSystemMapper
      │                  │                          │
      │                  │<──Return result─────────<│
      │<────gRPC response─│                          │
      │                  │                          │
```

---

## 📝 API Methods (gRPC)

### Search
```javascript
client.search('query text')
// Returns: { results: [...], count: N, elapsed_ms: M }
```

### Ingest
```javascript
client.ingest('/path/to/document')
// Returns: { document_id, indexed, timestamp }
```

### ScanProject
```javascript
client.scanProject()
// Returns: { files: [...], folders: [...], total_size_bytes }
```

### HealthCheck
```javascript
client.healthCheck()
// Returns: { status: 'healthy', vault_entries: N, timestamp }
```

### ApplyConfig
```javascript
client.applyConfig({ enable_caching: true })
// Returns: { applied: true, timestamp }
```

### Shutdown
```javascript
client.shutdown()
// Returns: { status: 'shutdown', timestamp }
```

---

## 🚀 Production Deployment Steps

1. **Setup Environment**
   ```bash
   mkdir -p ~/.nexus/integration
   export PYTHONPATH=/path/to/Bober-drive/driver:$PYTHONPATH
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # Includes: grpcio, grpcio-tools, numpy, cryptography, etc.
   ```

3. **Generate Proto (if needed)**
   ```bash
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. nexus_integration.proto
   ```

4. **Start gRPC Adapter**
   ```bash
   python -m nexus_grpc_adapter  # or via systemd/PM2
   ```

5. **Connect Backend**
   ```javascript
   const client = new NexusSearchClient('localhost:50051');
   // Ready to accept requests
   ```

---

## 🔍 Troubleshooting

### Proto stubs not found
```bash
# Regenerate
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. nexus_integration.proto
```

### "Address already in use" on port 50051
```bash
# Use different port
adapter = NexusGRPCAdapter(orchestrator, port=50052)
```

### Database lock (SQLite vault)
```bash
# Ensure only one server instance running
# Multiple instances will cause contention
```

### Tests fail
```bash
# Verify all files exist
ls -la nexus_integration_pb2.py nexus_grpc_adapter.py nexus_client.js

# Run tests with verbose output
pytest test_integration.py -vv --tb=short
```

---

## 📞 Support

For issues or questions:
1. Check `INTEGRATION-GUIDE.md` for detailed documentation
2. Review test cases in `test_integration.py` for usage examples
3. Check logs: `~/.nexus/integration/nexus.log`
4. Review `INTEGRATION-COMPLETION-REPORT.md` for architecture details

---

## ✅ Verification Checklist

Before going to production:

- [ ] Proto files generated: `nexus_integration_pb2*.py` ✓
- [ ] All 13 tests passing ✓
- [ ] Version locked to v3.0.0 ✓
- [ ] Auto-update disabled ✓
- [ ] gRPC adapter starts without errors ✓
- [ ] Node.js client connects successfully ✓
- [ ] Search returns results ✓
- [ ] Documents can be ingested ✓
- [ ] Project scanning works ✓
- [ ] Health check responds ✓

Status: **READY FOR DEPLOYMENT** ✅

---

Last Updated: 2026-07-18
All systems operational.
