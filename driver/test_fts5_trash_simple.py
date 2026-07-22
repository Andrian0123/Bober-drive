#!/usr/bin/env python3
"""
Simple Test Suite for FTS5 and Trash Manager
Tests basic functionality without complex setup
"""

import unittest
import sqlite3
import logging
from pathlib import Path
import tempfile
from datetime import datetime, timedelta
import secrets

from vault_fts5_extension import VaultFTS5Extension
from trash_manager import TrashManager

logging.basicConfig(level=logging.INFO)


class TestVaultFTS5Simple(unittest.TestCase):
    """Simple FTS5 tests"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        # Create minimal database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT,
                title TEXT,
                content BLOB,
                summary TEXT,
                tags TEXT,
                created_at TEXT,
                is_deleted BOOLEAN DEFAULT 0
            )
        """)
        cursor.execute(
            "INSERT INTO vault_entries VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 0)",
            ("test_001", "code", "Python Function", b"def hello():", None, "['python']")
        )
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up"""
        self.db_path.unlink()
    
    def test_fts5_init(self):
        """Test FTS5 initialization"""
        fts5 = VaultFTS5Extension(self.db_path)
        self.assertIsNotNone(fts5)
    
    def test_fts5_like_search(self):
        """Test LIKE search works"""
        fts5 = VaultFTS5Extension(self.db_path)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = fts5._like_search_fallback("Python", 10, cursor)
        conn.close()
        
        self.assertIsInstance(results, list)
        # Should find "Python Function" entry


class TestTrashManagerSimple(unittest.TestCase):
    """Simple Trash Manager tests"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_file.name)
        self.temp_file.close()
        
        # Create minimal database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE vault_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT,
                title TEXT,
                content BLOB,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up"""
        self.db_path.unlink()
    
    def test_trash_init(self):
        """Test Trash Manager initialization"""
        trash = TrashManager(self.db_path)
        self.assertIsNotNone(trash)
    
    def test_soft_delete(self):
        """Test soft delete"""
        trash = TrashManager(self.db_path)
        
        trash_id = trash.soft_delete(
            entry_id="test_001",
            content=b"test content",
            entry_type="code",
            title="Test Entry"
        )
        
        self.assertIsNotNone(trash_id)
        self.assertTrue(trash_id.startswith("trash_"))
    
    def test_list_trash(self):
        """Test listing trash"""
        trash = TrashManager(self.db_path)
        
        trash.soft_delete("e001", b"content1", "code", "Entry 1")
        trash.soft_delete("e002", b"content2", "code", "Entry 2")
        
        items = trash.list_trash()
        self.assertGreaterEqual(len(items), 2)
    
    def test_stats(self):
        """Test trash stats"""
        trash = TrashManager(self.db_path)
        
        trash.soft_delete("e001", b"content", "code", "Entry")
        
        stats = trash.get_trash_stats()
        self.assertGreater(stats["total_entries"], 0)


if __name__ == "__main__":
    # Run with minimal verbosity
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED")
        exit(0)
    else:
        print(f"\n❌ TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        exit(1)
