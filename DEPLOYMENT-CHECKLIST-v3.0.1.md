# 📋 Bober-Drive v3.0.1 Deployment Checklist

**Release Version:** v3.0.1  
**Release Date:** July 21, 2026  
**Deployment Status:** Ready ✅  
**Risk Level:** Low (backward compatible)  

---

## 🎯 Pre-Deployment Phase

### System Requirements
- [ ] Python >= 3.11 available
- [ ] pip package manager working
- [ ] 1GB free disk space available
- [ ] Network access to GitHub (for clone)
- [ ] 500MB available for cache (configurable)

### Environment Preparation
- [ ] Virtual environment created (recommended)
- [ ] Python version verified: `python --version`
- [ ] pip upgraded: `pip install --upgrade pip`
- [ ] Git available: `git --version`

### Dependency Check
```bash
# Run this before deployment
pip install -r requirements.txt
```

**Required Dependencies:**
- ✅ cryptography >= 41.0.0
- ✅ numpy >= 1.24.0
- ✅ watchdog (optional, for file monitoring)

---

## 📥 Installation Phase

### Step 1: Clone Repository
```bash
git clone https://github.com/Andrian0123/Bober-drive.git
cd Bober-drive
```

**Verification:**
- [ ] Repository cloned successfully
- [ ] .git directory present
- [ ] All source files present

### Step 2: Checkout Release Tag
```bash
git checkout v3.0.1-release
```

**Verification:**
- [ ] HEAD points to v3.0.1-release tag
- [ ] VERSION.json shows "3.0.1"
- [ ] PRODUCTION_RELEASE_v3.0.1.md present

### Step 3: Install Package
```bash
pip install -e .
```

**Verification:**
- [ ] Installation completes without errors
- [ ] No dependency conflicts
- [ ] Package appears in `pip list`

### Step 4: Verify Installation
```bash
python -c "from driver.nexus_autonomous_daemon import create_autonomous_daemon; print('✅ Installation OK')"
```

**Expected Output:**
```
✅ Installation OK
```

---

## 🧪 Testing Phase

### Unit Tests (10 FCCM Tests)
```bash
python -m pytest test_fccm_integration.py -v
```

**Expected Result:** 10/10 passing ✅

### E2E Tests (9 Daemon Tests)
```bash
python -m pytest test_autonomous_daemon_e2e.py -v
```

**Expected Result:** 9/9 passing ✅

### Combined Test Suite
```bash
python -m pytest test_fccm_integration.py test_autonomous_daemon_e2e.py -v
```

**Expected Result:** 19/19 passing ✅  
**Expected Duration:** ~20 seconds

### Checklist
- [ ] All tests passing (19/19)
- [ ] No errors in test output
- [ ] Test duration within expected bounds (~20s)
- [ ] No import errors

---

## ⚙️ Configuration Phase

### Default Configuration
```python
config = {
    'project_root': '/path/to/docs',
    'vault_path': './index.vault',
    # New in v3.0.1:
    'enable_file_cache': True,        # Enable caching
    'file_cache_size_mb': 500,        # Max cache size
    'file_cache_max_entries': 1000,   # Max entries
}
```

### Configuration Validation
```bash
# Test daemon initialization with config
python -c "
from driver.nexus_autonomous_daemon import create_autonomous_daemon
config = {
    'project_root': './docs',
    'vault_path': './.nexus/index.vault',
    'enable_file_cache': True,
}
daemon = create_autonomous_daemon(config)
print('✅ Configuration OK')
"
```

### Tuning for Different Scenarios

**Small Projects (< 100 files):**
```python
config = {
    'enable_file_cache': True,
    'file_cache_size_mb': 256,
    'file_cache_max_entries': 500,
}
```

**Medium Projects (100-500 files):**
```python
config = {
    'enable_file_cache': True,
    'file_cache_size_mb': 500,        # Default
    'file_cache_max_entries': 1000,   # Default
}
```

**Large Projects (> 500 files):**
```python
config = {
    'enable_file_cache': True,
    'file_cache_size_mb': 1024,
    'file_cache_max_entries': 2000,
}
```

**Minimal Mode (no cache):**
```python
config = {
    'enable_file_cache': False,
}
```

### Checklist
- [ ] Configuration matches your project size
- [ ] Paths are absolute or properly relative
- [ ] Vault path writable (directory creatable)
- [ ] Cache settings appropriate for your RAM

---

## 🚀 Production Deployment

### Start Daemon
```bash
python -c "
from driver.nexus_autonomous_daemon import create_autonomous_daemon

config = {
    'project_root': './docs',
    'vault_path': './.nexus/index.vault',
}

daemon = create_autonomous_daemon(config)
daemon.start()
print('✅ Daemon started')
print(f'State: {daemon.get_status()[\"state\"]}')
"
```

### Monitor Status
```bash
# Check daemon status
daemon_status = daemon.get_status()
print(daemon_status)

# Check cache statistics
cache_stats = daemon.get_cache_stats()
print(cache_stats)

# Check metrics
metrics = daemon.get_metrics()
print(metrics)
```

### Expected Startup Sequence
1. ✅ Daemon initializes
2. ✅ File system scan starts (Phase 1: INITIALIZING)
3. ✅ FTS5 index created
4. ✅ Daemon becomes READY (Phase 2)
5. ✅ File monitoring starts (Phase 3: MONITORING)

**Typical Startup Time:** 8-15 seconds (first run)

### Checklist
- [ ] Daemon starts without errors
- [ ] Status transitions work (STOPPED → INITIALIZING → READY → MONITORING)
- [ ] Cache statistics available
- [ ] Metrics collected

---

## 🔍 Verification Phase

### Functional Verification
```bash
# Test search functionality
results = daemon.search("your search query", limit=10)
assert results['status'] == 'ok', "Search failed"
assert len(results['hits']) > 0, "No results found"
print(f"✅ Search working: {len(results['hits'])} results")
```

### Performance Verification
```bash
# Check cache hit rate
cache_stats = daemon.get_cache_stats()
print(f"Cache hit rate: {cache_stats['hit_rate']:.1%}")
print(f"Cache size: {cache_stats['size_mb']:.1f}MB")

# Should see 85-95% hit rate after warm-up
assert cache_stats['hit_rate'] > 0.80, "Cache hit rate too low"
print("✅ Cache performance acceptable")
```

### Health Check
```bash
# Comprehensive health check
status = daemon.get_status()
metrics = daemon.get_metrics()

checks = [
    ("State is MONITORING", status['state'] == 'MONITORING'),
    ("Files indexed", status['indexed_files'] > 0),
    ("Cache enabled", status.get('file_cache_enabled', False)),
    ("Recent searches", metrics['search_count'] >= 0),
]

for check_name, result in checks:
    print(f"{'✅' if result else '❌'} {check_name}")
```

### Checklist
- [ ] Search API functional
- [ ] Cache hit rate > 80% (after warm-up)
- [ ] Daemon state = MONITORING
- [ ] Files indexed > 0
- [ ] Metrics collected correctly
- [ ] No errors in logs

---

## 📊 Monitoring Phase

### Daily Checks
- [ ] Daemon running (process not crashed)
- [ ] Search latency < 100ms (typical)
- [ ] Cache hit rate > 80%
- [ ] No memory leaks (RAM stable)
- [ ] No disk space issues

### Weekly Checks
- [ ] Cache effectiveness maintained
- [ ] Index freshness (recent updates indexed)
- [ ] File monitoring working
- [ ] Performance metrics reviewed
- [ ] Logs reviewed for errors

### Monthly Checks
- [ ] Full project re-index
- [ ] Cache statistics analysis
- [ ] Performance trending
- [ ] Dependency updates available?
- [ ] New release available?

### Monitoring Tools
```bash
# Check daemon resource usage (Linux/Mac)
ps aux | grep python | grep nexus

# Check daemon resource usage (Windows)
tasklist | findstr python

# Check logs
tail -f ./logs/daemon.log

# Monitor cache
watch -n 5 'python -c "from driver.nexus_autonomous_daemon import create_autonomous_daemon; d = create_autonomous_daemon(...); print(d.get_cache_stats())"'
```

---

## 🛠️ Troubleshooting Phase

### Issue: Import Errors
```bash
# Solution: Verify installation
pip install -e .
python -c "from driver.nexus_autonomous_daemon import create_autonomous_daemon; print('OK')"
```

### Issue: Cache Not Working
```bash
# Solution: Check config
config = {
    'enable_file_cache': True,  # Must be True
    'file_cache_size_mb': 500,  # At least 256MB recommended
}

# Verify cache stats
daemon.get_cache_stats()  # Should show hit_count > 0
```

### Issue: Slow Performance
```bash
# Solution: Check cache hit rate
cache_stats = daemon.get_cache_stats()
if cache_stats['hit_rate'] < 0.5:
    print("Cache warming up or low hit rate")
    
# Increase cache size if needed
config = {'file_cache_size_mb': 1024}

# Disable cache to verify
config = {'enable_file_cache': False}
```

### Issue: High Memory Usage
```bash
# Solution: Reduce cache size
config = {
    'enable_file_cache': True,
    'file_cache_size_mb': 256,      # Reduce from 500
    'file_cache_max_entries': 500,  # Reduce from 1000
}
```

### Issue: Daemon Crashes
```bash
# Solution: Check logs
cat ./logs/daemon.log

# Restart daemon
daemon.stop(graceful=True)
daemon.start()

# If crashes persist, disable cache
config = {'enable_file_cache': False}
```

---

## 🔄 Rollback Plan

### Rollback to v3.0.0
```bash
# 1. Stop current daemon
daemon.stop(graceful=True)

# 2. Switch to previous version
git checkout v3.0.0
pip install -e .

# 3. Restart with v3.0.0
daemon = create_autonomous_daemon(config)
daemon.start()
```

**Rollback Time:** < 5 minutes  
**Data Loss Risk:** None (v3.0.1 is backward compatible)  
**Automatic Rollback:** Not needed (v3.0.1 is production-grade)

---

## ✅ Post-Deployment Phase

### Completion Verification
- [ ] All 19 tests passing
- [ ] Daemon running in production
- [ ] Monitoring in place
- [ ] Documentation updated
- [ ] Team notified

### Documentation Update
- [ ] Deployment date recorded: 2026-07-21
- [ ] Configuration documented
- [ ] Runbook updated
- [ ] Team wiki updated

### Sign-Off
- [ ] DevOps: _________________ Date: _______
- [ ] Tech Lead: _________________ Date: _______
- [ ] QA: _________________ Date: _______

---

## 📞 Support Contacts

| Role | Contact |
|------|---------|
| Technical Issues | GitHub Issues |
| Performance Questions | Review metrics.json |
| Configuration Help | See config examples above |
| Urgent Issues | Contact on-call engineer |

---

## 📚 Related Documents

- **RELEASE_NOTES_v3.0.1.md** — What's new
- **PRODUCTION_RELEASE_v3.0.1.md** — Sign-off report
- **BUILD-REPORT-v3.0.1.md** — Build details
- **AGENTS.local.md** — Usage guide
- **README.md** — Quick start

---

**Deployment Checklist Status:** Ready for Production ✅

Version: 3.0.1  
Date: 2026-07-21  
Status: Production-Ready  
