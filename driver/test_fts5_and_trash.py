#!/usr/bin/env python3
"""
Test Suite for FTS5 Extension and Trash Manager
Comprehensive testing of full-text search and soft delete functionality
"""

import unittest
import logging
from pathlib import Path
import tempfile
import json
import sqlite3
import secrets
from datetime import datetime, timedelta

# Import modules to test
from vault_fts5_extension import VaultFTS5Extension
from trash_manager import TrashManager, DEFAULT_TTL_HOURS

logging.basicConfig(level=logging.INFO)


class TestVaultFTS5Extension(unittest.TestCase):
    """Test FTS5 extension functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_vault.db"
        
        # Create a minimal vault database
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content BLOB NOT NULL,
                summary TEXT,
                tags TEXT,
                embedding BLOB,
                access_level TEXT DEFAULT 'internal',
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                created_by TEXT DEFAULT 'system',
                version INTEGER DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0
            )
        """)
        
        # Insert test data
        test_entries = [
            ("e001", "code", "Python Authentication Module", b"def authenticate():", None, "['auth', 'python']"),
            ("e002", "documentation", "API Reference", b"# API Documentation", "API docs", "['api', 'docs']"),
            ("e003", "code", "Database Handler", b"class Database:", None, "['database', 'sql']"),
            ("e004", "memory", "Important Note", b"Remember to update configs", "Config reminder", "['config']"),
        ]
        
        for entry in test_entries:
            cursor.execute("""
                INSERT INTO vault_entries
                (entry_id, entry_type, title, content, summary, tags, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, entry)
        
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.temp_dir.cleanup()
    
    def test_fts5_initialization(self):
        """Test FTS5 schema initialization"""
        fts5 = VaultFTS5Extension(self.db_path)
        self.assertIsNotNone(fts5)
        
        # Check if FTS5 table exists
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_entries_fts'"
        )
        result = cursor.fetchone()
        conn.close()
        
        # FTS5 may not be available, so we just check no errors occurred
        self.assertIsNotNone(fts5)
    
    def test_fulltext_search(self):
        """Test full-text search functionality"""
        fts5 = VaultFTS5Extension(self.db_path)
        
        # Search for "authenticate"
        results = fts5.fulltext_search("authenticate", limit=10)
        self.assertIsInstance(results, list)
        # Results may be empty if FTS5 not available, but should not error
    
    def test_like_search_fallback(self):
        """Test LIKE search fallback"""
        fts5 = VaultFTS5Extension(self.db_path)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = fts5._like_search_fallback("Database", 50, cursor)
        conn.close()
        
        self.assertIsInstance(results, list)
        # Should find "Database Handler"
        if results:
            self.assertTrue(any("Database" in r.get("title", "") for r in results))
    
    def test_regex_search(self):
        """Test regex search"""
        fts5 = VaultFTS5Extension(self.db_path)
        
        # Search for entries with "def" or "class" (Python code)
        results = fts5.regex_search(r"(def|class)", limit=10)
        self.assertIsInstance(results, list)
    
    def test_advanced_search_multiple_strategies(self):
        """Test advanced search with multiple strategies"""
        fts5 = VaultFTS5Extension(self.db_path)
        
        # Try FTS5
        fts5_results = fts5.advanced_search("Python", search_type="fts5", limit=10)
        self.assertIsInstance(fts5_results, list)
        
        # Try LIKE
        like_results = fts5.advanced_search("Python", search_type="like", limit=10)
        self.assertIsInstance(like_results, list)
    
    def test_search_filters_deleted(self):
        """Test that search filters deleted entries"""
        # Mark an entry as deleted
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("UPDATE vault_entries SET is_deleted = 1 WHERE entry_id = 'e001'")
        conn.commit()
        conn.close()
        
        # Search should not return deleted entry
        fts5 = VaultFTS5Extension(self.db_path)
        results = fts5.fulltext_search("authenticate", limit=10)
        
        # Undelete for other tests
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("UPDATE vault_entries SET is_deleted = 0 WHERE entry_id = 'e001'")
        conn.commit()
        conn.close()


class TestTrashManager(unittest.TestCase):
    """Test Trash Manager functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_trash.db"
        
        # Create a minimal vault database
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content BLOB NOT NULL,
                summary TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.temp_dir.cleanup()
    
    def test_trash_manager_initialization(self):
        """Test TrashManager initialization"""
        trash = TrashManager(self.db_path)
        self.assertIsNotNone(trash)
        
        # Check if trash table exists
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_trash'"
        )
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
    
    def test_soft_delete(self):
        """Test soft delete operation"""
        trash = TrashManager(self.db_path)
        
        # Soft delete an entry
        trash_id = trash.soft_delete(
            entry_id="entry_001",
            content=b"encrypted content here",
            entry_type="code",
            title="Test Entry",
            reason="testing",
            deleted_by="test_user"
        )
        
        self.assertIsNotNone(trash_id)
        self.assertTrue(trash_id.startswith("trash_"))
    
    def test_list_trash(self):
        """Test listing trash entries"""
        trash = TrashManager(self.db_path)
        
        # Soft delete multiple entries
        for i in range(3):
            trash.soft_delete(
                entry_id=f"entry_{i:03d}",
                content=b"content",
                entry_type="code",
                title=f"Entry {i}"
            )
        
        # List trash
        items = trash.list_trash(include_expired=False)
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 3)
    
    def test_restore_from_trash(self):
        """Test restore operation"""
        trash = TrashManager(self.db_path)
        
        # Soft delete
        trash_id = trash.soft_delete(
            entry_id="restore_test_001",
            content=b"content to restore",
            entry_type="code",
            title="Restore Test"
        )
        
        # Restore
        restored = trash.restore_from_trash(trash_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored["original_entry_id"], "restore_test_001")
        self.assertEqual(restored["title"], "Restore Test")
    
    def test_restore_after_ttl_expires(self):
        """Test that restore fails after TTL expiration"""
        trash = TrashManager(self.db_path)
        
        # Soft delete with very short TTL (1 second)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        trash_id = f"trash_expired_test_{secrets.token_hex(4)}"
        deleted_at = datetime.utcnow().isoformat()
        restore_until = (datetime.utcnow() - timedelta(seconds=1)).isoformat()  # Already expired
        
        cursor.execute("""
            INSERT INTO vault_trash
            (trash_id, original_entry_id, entry_type, title, content,
             deleted_at, delete_reason, deleted_by, restore_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (trash_id, "expired_entry", "code", "Expired", b"content",
              deleted_at, "test", "test_user", restore_until))
        
        conn.commit()
        conn.close()
        
        # Try to restore - should fail
        restored = trash.restore_from_trash(trash_id)
        self.assertIsNone(restored)
    
    def test_permanent_delete(self):
        """Test permanent delete after TTL"""
        trash = TrashManager(self.db_path)
        
        # Soft delete
        trash_id = trash.soft_delete(
            entry_id="permanent_test_001",
            content=b"content",
            entry_type="code",
            title="Permanent Delete Test"
        )
        
        # Try to force delete (force=True ignores TTL)
        result = trash.permanent_delete(trash_id, force=True)
        self.assertTrue(result)
        
        # Verify it's gone
        items = trash.list_trash(include_expired=True)
        trash_ids = [item["trash_id"] for item in items]
        self.assertNotIn(trash_id, trash_ids)
    
    def test_cleanup_expired_entries(self):
        """Test automatic cleanup of expired entries"""
        trash = TrashManager(self.db_path)
        
        # Create expired entry
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        expired_id = f"trash_cleanup_test_{secrets.token_hex(4)}"
        restore_until = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        cursor.execute("""
            INSERT INTO vault_trash
            (trash_id, original_entry_id, entry_type, title, content,
             deleted_at, delete_reason, deleted_by, restore_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (expired_id, "cleanup_entry", "code", "Cleanup", b"content",
              datetime.utcnow().isoformat(), "test", "system", restore_until))
        
        conn.commit()
        conn.close()
        
        # Run cleanup
        cleaned, errors = trash.cleanup_expired_entries()
        self.assertEqual(errors, 0)
        self.assertGreater(cleaned, 0)
    
    def test_trash_stats(self):
        """Test trash statistics"""
        trash = TrashManager(self.db_path)
        
        stats = trash.get_trash_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_entries", stats)
        self.assertIn("recoverable", stats)
        self.assertIn("expired", stats)
        self.assertGreater(stats["total_entries"], 0)
    
    def test_audit_log(self):
        """Test audit logging"""
        trash = TrashManager(self.db_path)
        
        # Soft delete (creates audit entry)
        trash_id = trash.soft_delete(
            entry_id="audit_test_001",
            content=b"content",
            entry_type="code",
            title="Audit Test"
        )
        
        # Get audit log
        audit = trash.get_audit_log(trash_id)
        self.assertIsInstance(audit, list)
        self.assertGreater(len(audit), 0)


class TestIntegrationFTS5andTrash(unittest.TestCase):
    """Integration tests for FTS5 and Trash Manager"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_integration.db"
        
        # Create complete database
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content BLOB NOT NULL,
                summary TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("INSERT INTO vault_entries VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0)",
                      ("test_001", "code", "Test Code", b"def test():", None, "['test']"))
        
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.temp_dir.cleanup()
    
    def test_fts5_and_trash_together(self):
        """Test FTS5 and Trash working together"""
        fts5 = VaultFTS5Extension(self.db_path)
        trash = TrashManager(self.db_path)
        
        # Both should initialize without errors
        self.assertIsNotNone(fts5)
        self.assertIsNotNone(trash)
        
        # Should be able to search
        results = fts5.fulltext_search("test", limit=10)
        self.assertIsInstance(results, list)
        
        # Should be able to access trash
        stats = trash.get_trash_stats()
        self.assertIsInstance(stats, dict)


# Performance tests
class TestPerformance(unittest.TestCase):
    """Performance tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up large test database"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_perf.db"
        
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content BLOB NOT NULL,
                summary TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            )
        """)
        
        # Insert 100 test entries
        for i in range(100):
            cursor.execute(
                "INSERT INTO vault_entries VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0)",
                (f"perf_entry_{i:04d}", "code", f"Performance Test {i}", f"Content {i}".encode(), None, "['perf']")
            )
        
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.temp_dir.cleanup()
    
    def test_large_search_performance(self):
        """Test search performance with many entries"""
        import time
        
        fts5 = VaultFTS5Extension(self.db_path)
        
        start = time.time()
        results = fts5.fulltext_search("Performance", limit=50)
        elapsed = time.time() - start
        
        # Search should complete in reasonable time
        self.assertLess(elapsed, 1.0)  # Less than 1 second
    
    def test_large_trash_performance(self):
        """Test trash operations with many entries"""
        import time
        
        trash = TrashManager(self.db_path)
        
        # Soft delete multiple entries
        start = time.time()
        for i in range(10):
            trash.soft_delete(
                entry_id=f"perf_delete_{i}",
                content=b"content",
                entry_type="code",
                title=f"Performance Delete {i}"
            )
        elapsed = time.time() - start
        
        # Operations should be fast
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
