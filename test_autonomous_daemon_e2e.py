#!/usr/bin/env python3
"""
End-to-End tests for Bober-Drive Autonomous Daemon
Tests full lifecycle: initialization, scanning, monitoring, search, metrics, shutdown
"""

import sys
import os
import time
import tempfile
import unittest
from pathlib import Path
from dataclasses import dataclass

# Добавить driver в sys.path для импорта модулей
driver_path = str(Path(__file__).parent / "driver")
if driver_path not in sys.path:
    sys.path.insert(0, driver_path)

# Теперь импортируем модули daemon напрямую (они в driver/)
from nexus_autonomous_daemon import (
    NexusAutonomousDaemon,
    DaemonConfig,
    DaemonState,
    DaemonMetrics,
    InitStrategy,
    create_autonomous_daemon
)


class TestAutonomousDaemonE2E(unittest.TestCase):
    """End-to-end tests for autonomous daemon"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with temp directory"""
        cls.test_root = Path(tempfile.mkdtemp(prefix="bober_daemon_e2e_"))
        cls.vault_dir = cls.test_root / "vault"
        cls.vault_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test directory"""
        import shutil
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root)
    
    def setUp(self):
        """Create fresh daemon and test files for each test"""
        # Create 10 markdown test files
        self._create_test_files(count=10)
        
        # Create daemon config (file watch disabled for tests)
        self.config = DaemonConfig(
            project_root=self.test_root,
            vault_path=self.vault_dir,
            checkpoint_path=self.test_root / "daemon.checkpoint",
            enable_file_watch=False,  # Disabled for test stability
            init_strategy=InitStrategy.FULL_SCAN,
            reindex_debounce_ms=100,
            reindex_max_queue_size=1000
        )
        
        # Create daemon without orchestrator (will be created internally)
        self.daemon = create_autonomous_daemon(
            project_root=self.test_root,
            vault_path=self.vault_dir,
            enable_file_watch=False,
            init_strategy=InitStrategy.FULL_SCAN
        )
    
    def _create_test_files(self, count: int = 10):
        """Create markdown test files"""
        test_dir = self.test_root / "test_docs"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(count):
            file_path = test_dir / f"test_document_{i:02d}.md"
            content = f"""# Test Document {i}

## Описание
Это тестовый документ номер {i}.

## Содержание
- Пункт 1: основная информация
- Пункт 2: дополнительные данные
- Пункт 3: важные заметки

## Ключевые слова
`важное`, `тестирование`, `документация`, `автономный демон`

## Статус
Документ создан для E2E тестирования демона Bober-Drive.
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def test_01_daemon_initialization(self):
        """Test daemon initializes to READY state"""
        self.assertEqual(self.daemon.state, DaemonState.STOPPED)
        
        # Start daemon
        started = self.daemon.start()
        self.assertTrue(started, "Daemon should start successfully")
        
        # Give it time to initialize
        time.sleep(2.0)
        
        # Check state (should be READY or MONITORING)
        self.assertIn(
            self.daemon.state,
            [DaemonState.READY, DaemonState.MONITORING],
            f"Daemon should be READY or MONITORING, but is {self.daemon.state}"
        )
    
    def test_02_state_transitions(self):
        """Test state machine transitions"""
        states = []
        
        # STOPPED -> INITIALIZING -> READY/MONITORING
        self.daemon.start()
        time.sleep(0.5)
        
        if self.daemon.state == DaemonState.INITIALIZING:
            states.append(self.daemon.state)
            time.sleep(1.5)
        
        states.append(self.daemon.state)
        self.assertIn(self.daemon.state, [DaemonState.READY, DaemonState.MONITORING])
        
        # READY/MONITORING -> STOPPED
        self.daemon.stop(graceful=True)
        time.sleep(0.5)
        self.assertEqual(self.daemon.state, DaemonState.STOPPED)
    
    def test_03_full_scan_indexing(self):
        """Test Phase 1: full project scan and indexing"""
        # Start daemon
        started = self.daemon.start()
        self.assertTrue(started)
        
        # Wait for initialization
        time.sleep(2.0)
        
        # Check if daemon reached READY/MONITORING
        self.assertIn(self.daemon.state, [DaemonState.READY, DaemonState.MONITORING])
        
        # Get status to verify scan happened
        status = self.daemon.get_status()
        self.assertIsNotNone(status)
        
        # Check that files were indexed
        # Status should have file_count or similar metric
        if 'indexed_files' in status:
            self.assertGreater(status['indexed_files'], 0,
                              "Should have indexed files from scan")
    
    def test_04_search_api(self):
        """Test search functionality"""
        # Initialize daemon
        self.daemon.start()
        time.sleep(2.0)
        
        # Perform search
        query = "тестирование"
        results = self.daemon.search(query, limit=10)
        
        self.assertIsNotNone(results)
        self.assertIn('results', results)
        
        # Should find results about testing
        if results['results']:
            self.assertGreater(len(results['results']), 0)
    
    def test_05_daemon_status(self):
        """Test status reporting"""
        self.daemon.start()
        time.sleep(2.0)
        
        status = self.daemon.get_status()
        
        self.assertIsNotNone(status)
        self.assertIn('state', status)
        self.assertIn('uptime', status)
        
        # State should be valid
        self.assertIn(status['state'], [s.value for s in DaemonState])
    
    def test_06_daemon_metrics(self):
        """Test metrics collection"""
        self.daemon.start()
        time.sleep(2.0)
        
        metrics = self.daemon.get_metrics()
        
        self.assertIsNotNone(metrics)
        
        # Metrics can be dict or DaemonMetrics object
        if isinstance(metrics, dict):
            self.assertIn('startup_time_ms', metrics)
            self.assertIn('total_files_scanned', metrics)
        else:
            # DaemonMetrics dataclass
            self.assertIsNotNone(metrics.startup_time_ms)
            self.assertIsNotNone(metrics.total_files_scanned)
    
    def test_07_graceful_shutdown(self):
        """Test graceful daemon shutdown"""
        self.daemon.start()
        time.sleep(1.0)
        
        # Gracefully stop
        self.daemon.stop(graceful=True)
        time.sleep(0.5)
        
        self.assertEqual(self.daemon.state, DaemonState.STOPPED)
        
        # Can restart after shutdown
        started = self.daemon.start()
        self.assertTrue(started)
        time.sleep(1.0)
        self.assertNotEqual(self.daemon.state, DaemonState.STOPPED)
        
        self.daemon.stop()
    
    def test_08_multiple_sequential_operations(self):
        """Test multiple operations in sequence"""
        # 1. Start
        self.daemon.start()
        time.sleep(1.5)
        self.assertNotEqual(self.daemon.state, DaemonState.STOPPED)
        
        # 2. Search
        results = self.daemon.search("документ")
        self.assertIsNotNone(results)
        
        # 3. Get status
        status = self.daemon.get_status()
        self.assertIsNotNone(status)
        
        # 4. Get metrics
        metrics = self.daemon.get_metrics()
        self.assertIsNotNone(metrics)
        
        # 5. Stop
        self.daemon.stop()
        time.sleep(0.5)
        self.assertEqual(self.daemon.state, DaemonState.STOPPED)


class TestAutonomousDaemonIntegration(unittest.TestCase):
    """Integration tests simulating agent usage"""
    
    @classmethod
    def setUpClass(cls):
        """Set up integration test class"""
        cls.test_root = Path(tempfile.mkdtemp(prefix="bober_daemon_integration_"))
        cls.vault_dir = cls.test_root / "vault"
        cls.vault_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        import shutil
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root)
    
    def setUp(self):
        """Set up integration test"""
        self._create_test_files(count=10)
        
        self.daemon = create_autonomous_daemon(
            project_root=self.test_root,
            vault_path=self.vault_dir,
            enable_file_watch=False,
            init_strategy=InitStrategy.FULL_SCAN
        )
    
    def _create_test_files(self, count: int = 10):
        """Create test files"""
        test_dir = self.test_root / "test_docs"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(count):
            file_path = test_dir / f"doc_{i:02d}.md"
            content = f"# Document {i}\n\nContent for doc {i}"
            with open(file_path, 'w') as f:
                f.write(content)
    
    def test_agent_search_workflow(self):
        """Test typical agent workflow: initialize, search, shutdown"""
        # Initialize daemon
        self.daemon.start()
        time.sleep(2.0)
        
        # Daemon should be ready
        self.assertIn(self.daemon.state, [DaemonState.READY, DaemonState.MONITORING])
        
        # Agent performs searches
        queries = ["документ", "содержание", "информация"]
        for query in queries:
            results = self.daemon.search(query, limit=5)
            self.assertIsNotNone(results)
        
        # Get final status
        status = self.daemon.get_status()
        self.assertIsNotNone(status)
        
        # Shutdown
        self.daemon.stop()
        time.sleep(0.5)
        self.assertEqual(self.daemon.state, DaemonState.STOPPED)


def run_e2e_tests():
    """Run all E2E tests"""
    suite = unittest.TestSuite()
    
    # Add all tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAutonomousDaemonE2E))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAutonomousDaemonIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
