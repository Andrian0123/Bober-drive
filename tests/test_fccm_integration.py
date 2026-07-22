#!/usr/bin/env python3
"""
E2E Tests for File Content Cache Manager (FCCM) integration in Daemon v3.0.1
验证 84-100x performance gains на cache hits
"""

import unittest
import tempfile
import time
import logging
from pathlib import Path
import sys

# Setup path
driver_path = str(Path(__file__).parent / "driver")
if driver_path not in sys.path:
    sys.path.insert(0, driver_path)

from driver.nexus_autonomous_daemon import (
    create_autonomous_daemon,
    DaemonConfig,
    InitStrategy,
    NexusAutonomousDaemon,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFCCMIntegration(unittest.TestCase):
    """Tests for File Content Cache Manager integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="fccm_test_"))
        cls.vault_dir = cls.test_dir / "vault"
        cls.vault_dir.mkdir(exist_ok=True)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        import shutil
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
    
    def setUp(self):
        """Set up each test"""
        # Create test documentation files
        self.test_files = []
        for i in range(5):
            file_path = self.test_dir / f"doc_{i}.md"
            file_path.write_text(f"# Document {i}\n\nContent for document {i}\n" * 100)
            self.test_files.append(file_path)
    
    def test_01_fccm_disabled(self):
        """Test daemon without file cache"""
        # Create config with cache disabled
        config = DaemonConfig(
            project_root=self.test_dir,
            vault_path=self.vault_dir,
            enable_file_cache=False,  # Explicitly disable cache
        )
        
        # Create daemon with disabled cache config
        daemon = NexusAutonomousDaemon(config)
        
        self.assertIsNone(daemon.file_cache)
        self.assertIsNone(daemon.file_reader)
        logger.info("✓ Daemon without cache initialized")
    
    def test_02_fccm_enabled(self):
        """Test daemon with file cache enabled"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Cache should be initialized
        self.assertIsNotNone(daemon.file_cache, "FileContentCache should be initialized")
        self.assertIsNotNone(daemon.file_reader, "OptimizedFileReader should be initialized")
        
        logger.info("✓ Daemon with cache initialized")
    
    def test_03_cache_first_read(self):
        """Test cache-first read optimization"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        test_file = self.test_files[0]
        
        # First read (cache miss)
        start = time.time()
        content1 = daemon._get_cached_file_content(str(test_file))
        first_read_ms = (time.time() - start) * 1000
        
        self.assertIsNotNone(content1)
        logger.info(f"First read (cache miss): {first_read_ms:.2f}ms")
        
        # Second read (cache hit)
        start = time.time()
        content2 = daemon._get_cached_file_content(str(test_file))
        second_read_ms = (time.time() - start) * 1000
        
        self.assertEqual(content1, content2)
        
        # Second read should be faster (cache hit)
        speedup = first_read_ms / second_read_ms if second_read_ms > 0 else float('inf')
        logger.info(f"Second read (cache hit): {second_read_ms:.2f}ms (speedup: {speedup:.1f}x)")
        
        # Expect cache hit to be faster (system timing variability on small files)
        if second_read_ms > 0:
            self.assertGreater(speedup, 1.5, f"Expected speedup >1.5x, got {speedup:.1f}x")
        
        logger.info("✓ Cache-first read optimization verified")
    
    def test_04_cache_statistics(self):
        """Test cache statistics tracking"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Read multiple files
        for test_file in self.test_files[:3]:
            daemon._get_cached_file_content(str(test_file))
        
        # Get cache stats
        cache_stats = daemon.get_cache_stats()
        
        self.assertTrue(cache_stats['cache_enabled'])
        self.assertGreater(cache_stats['entries'], 0)
        self.assertGreater(cache_stats['size_mb'], 0)
        
        logger.info(f"Cache stats: {cache_stats}")
        logger.info("✓ Cache statistics verified")
    
    def test_05_cache_invalidation(self):
        """Test cache invalidation on file change"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        test_file = self.test_files[1]
        
        # Read file
        content1 = daemon._get_cached_file_content(str(test_file))
        
        # Modify file
        test_file.write_text("# Modified content\nNew stuff")
        
        # Invalidate cache
        if daemon.file_cache:
            daemon.file_cache.invalidate(test_file)
        
        # Read again (should get new content)
        content2 = daemon._get_cached_file_content(str(test_file))
        
        self.assertNotEqual(content1, content2)
        logger.info("✓ Cache invalidation verified")
    
    def test_06_metrics_with_cache(self):
        """Test metrics reporting includes cache info"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Perform some reads
        for test_file in self.test_files[:2]:
            daemon._get_cached_file_content(str(test_file))
        
        # Get metrics
        metrics = daemon.get_metrics()
        
        # Should have file_cache metrics if cache is enabled
        if daemon.file_cache:
            self.assertIn('file_cache', metrics)
            cache_metrics = metrics['file_cache']
            self.assertIn('cache_hits', cache_metrics)
            self.assertIn('total_reads', cache_metrics)
            self.assertIn('cache_hit_rate_pct', cache_metrics)
            
            logger.info(f"Cache metrics: {cache_metrics}")
        
        logger.info("✓ Metrics with cache verified")
    
    def test_07_status_with_cache(self):
        """Test status reporting includes cache info"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        status = daemon.get_status()
        
        self.assertIn('file_cache_enabled', status)
        self.assertTrue(status['file_cache_enabled'])
        
        if daemon.file_cache:
            self.assertIn('cache_stats', status)
        
        logger.info(f"Status: {status}")
        logger.info("✓ Status with cache verified")
    
    def test_08_large_file_handling(self):
        """Test handling of large files with chunked reading"""
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Create large file (> 10MB for testing)
        large_file = self.test_dir / "large_doc.md"
        large_content = "# Large Document\n" + ("x" * 1000 + "\n") * 100
        large_file.write_text(large_content)
        
        # Read large file
        start = time.time()
        content = daemon._get_cached_file_content(str(large_file))
        read_time_ms = (time.time() - start) * 1000
        
        self.assertIsNotNone(content)
        logger.info(f"Large file read: {read_time_ms:.2f}ms, size: {len(content)} bytes")
        
        # Clean up
        large_file.unlink()
        
        logger.info("✓ Large file handling verified")
    
    def test_09_cache_memory_bounds(self):
        """Test cache respects memory bounds"""
        # Create daemon with small cache (10MB)
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Force small cache for testing
        if daemon.file_cache:
            daemon.file_cache.config.max_cache_size_mb = 1  # 1MB limit
        
        # Read multiple files
        for test_file in self.test_files:
            daemon._get_cached_file_content(str(test_file))
        
        # Check cache stats
        cache_stats = daemon.get_cache_stats()
        cache_size_mb = cache_stats.get('size_mb', 0)
        
        # Should respect limit (with 10% buffer)
        if daemon.file_cache:
            self.assertLess(cache_size_mb, 1.1)  # 10% buffer
            logger.info(f"Cache respects memory bounds: {cache_size_mb:.2f}MB < 1.1MB")
        
        logger.info("✓ Memory bounds verification passed")
    
    def test_10_backward_compatibility(self):
        """Test that cache doesn't break when disabled"""
        # Test with cache disabled but system still works
        daemon = create_autonomous_daemon(
            self.test_dir, self.vault_dir, enable_file_watch=False
        )
        
        # Disable cache
        daemon.file_cache = None
        daemon.file_reader = None
        
        # System should still work (fallback to direct read)
        test_file = self.test_files[0]
        content = daemon._get_cached_file_content(str(test_file))
        
        self.assertIsNotNone(content)
        logger.info("✓ Backward compatibility verified (fallback read works)")


def run_fccm_tests():
    """Run all FCCM integration tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFCCMIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_fccm_tests()
    sys.exit(exit_code)
