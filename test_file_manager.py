#!/usr/bin/env python3
"""
E2E tests for Nexus File Manager.
Tests incremental indexing, search, checkpoints, and caching.
"""

import json
import tempfile
import time
import unittest
from pathlib import Path

from driver.nexus_file_manager import (
    NexusFileManager,
    CheckpointManager,
    IncrementalIndexer,
    SearchEngine,
    create_file_manager,
)


class TestIncrementalIndexer(unittest.TestCase):
    """Tests for incremental indexer."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.indexer = IncrementalIndexer(self.project_root)

    def tearDown(self):
        self.indexer.close()
        self.temp_dir.cleanup()

    def test_file_hash_computation(self):
        """Test file hash computation."""
        test_file = self.project_root / "test.py"
        test_file.write_text("print('hello')")

        hash1 = self.indexer._compute_file_hash(test_file)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 16)

        # Modify file
        test_file.write_text("print('world')")
        hash2 = self.indexer._compute_file_hash(test_file)
        self.assertNotEqual(hash1, hash2)

    def test_should_index_new_file(self):
        """Test detection of new files."""
        test_file = self.project_root / "test.py"
        test_file.write_text("print('hello')")

        self.assertTrue(self.indexer.should_index(test_file))

    def test_should_not_index_unchanged_file(self):
        """Test that unchanged files are not re-indexed."""
        test_file = self.project_root / "test.py"
        test_file.write_text("print('hello')")

        # First index
        file_hash = self.indexer._compute_file_hash(test_file)
        self.indexer.mark_indexed(test_file, file_hash)

        # Should not re-index
        self.assertFalse(self.indexer.should_index(test_file))

    def test_add_and_retrieve_entity(self):
        """Test adding and retrieving entities."""
        test_file = self.project_root / "test.py"
        test_file.write_text("def hello(): pass")

        entity_id = self.indexer.add_entity(
            name="hello",
            kind="function",
            file_path=test_file,
            line_start=1,
            line_end=1,
            signature="def hello():",
            language="python",
        )

        self.assertGreater(entity_id, 0)

        entities = self.indexer.get_all_entities()
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].name, "hello")
        self.assertEqual(entities[0].kind, "function")

    def test_clear_index(self):
        """Test clearing the index."""
        test_file = self.project_root / "test.py"
        test_file.write_text("def hello(): pass")

        self.indexer.add_entity(
            name="hello",
            kind="function",
            file_path=test_file,
            line_start=1,
            line_end=1,
        )

        self.indexer.clear()
        entities = self.indexer.get_all_entities()
        self.assertEqual(len(entities), 0)


class TestSearchEngine(unittest.TestCase):
    """Tests for search engine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.indexer = IncrementalIndexer(self.project_root)
        self.search_engine = SearchEngine(self.indexer, self.project_root)

    def tearDown(self):
        self.indexer.close()
        self.temp_dir.cleanup()

    def test_add_test_entities(self):
        """Add test entities for search tests."""
        test_file = self.project_root / "test.py"
        test_file.write_text("def calculate_total(): pass\ndef process_data(): pass")

        self.indexer.add_entity(
            name="calculate_total",
            kind="function",
            file_path=test_file,
            line_start=1,
            line_end=1,
            signature="def calculate_total():",
        )

        self.indexer.add_entity(
            name="process_data",
            kind="function",
            file_path=test_file,
            line_start=2,
            line_end=2,
            signature="def process_data():",
        )

    def test_semantic_search(self):
        """Test semantic search via FTS5."""
        self.test_add_test_entities()

        results = self.search_engine._search_semantic("calculate", max_results=10)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].name, "calculate_total")

    def test_search_caching(self):
        """Test search result caching."""
        self.test_add_test_entities()

        # First search
        results1 = self.search_engine.search("calculate", max_results=10)
        cache_size_after_search = len(self.search_engine._cache)

        # Second search (should be cached)
        results2 = self.search_engine.search("calculate", max_results=10)

        self.assertEqual(len(results1), len(results2))
        self.assertEqual(len(self.search_engine._cache), cache_size_after_search)

    def test_cache_clear(self):
        """Test cache clearing."""
        self.test_add_test_entities()

        # Populate cache
        self.search_engine.search("calculate", max_results=10)
        self.assertGreater(len(self.search_engine._cache), 0)

        # Clear cache
        self.search_engine.clear_cache()
        self.assertEqual(len(self.search_engine._cache), 0)


class TestCheckpointManager(unittest.TestCase):
    """Tests for checkpoint management."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.checkpoint_manager = CheckpointManager(self.project_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_checkpoint(self):
        """Test saving and loading checkpoints."""
        checkpoint_id = self.checkpoint_manager.save_checkpoint(
            read_entities=[1, 2, 3],
            context_summary="Test context",
            next_action="Do something",
        )

        self.assertNotEqual(checkpoint_id, "")

        # Load checkpoint
        checkpoint = self.checkpoint_manager.load_checkpoint()
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint.read_entities, [1, 2, 3])
        self.assertEqual(checkpoint.context_summary, "Test context")

    def test_checkpoint_directory_creation(self):
        """Test .agent directory creation."""
        self.checkpoint_manager.save_checkpoint(
            read_entities=[],
            context_summary="",
            next_action="",
        )

        self.assertTrue((self.project_root / ".agent").exists())

    def test_save_and_load_index(self):
        """Test saving and loading index."""
        index_data = {
            "files": 100,
            "entities": 500,
            "timestamp": time.time(),
        }

        self.checkpoint_manager.save_index(index_data)

        loaded_index = self.checkpoint_manager.load_index()
        self.assertIsNotNone(loaded_index)
        self.assertEqual(loaded_index["files"], 100)

    def test_clear_checkpoints(self):
        """Test clearing checkpoints."""
        self.checkpoint_manager.save_checkpoint(
            read_entities=[],
            context_summary="",
            next_action="",
        )

        self.checkpoint_manager.clear()

        self.assertIsNone(self.checkpoint_manager.load_checkpoint())


class TestNexusFileManager(unittest.TestCase):
    """Integration tests for Nexus File Manager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.manager = create_file_manager(self.project_root)

    def tearDown(self):
        self.manager.indexer.close()
        self.temp_dir.cleanup()

    def test_factory_creation(self):
        """Test factory function creation."""
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager, NexusFileManager)

    def test_is_source_file(self):
        """Test source file detection."""
        self.assertTrue(self.manager._is_source_file(Path("test.py")))
        self.assertTrue(self.manager._is_source_file(Path("test.java")))
        self.assertFalse(self.manager._is_source_file(Path("test.txt")))
        self.assertFalse(self.manager._is_source_file(Path("test.png")))

    def test_search_returns_dict(self):
        """Test that search returns proper structure."""
        # Create test file
        test_file = self.project_root / "test.py"
        test_file.write_text("def hello(): pass")

        # Add entity manually
        self.manager.indexer.add_entity(
            name="hello",
            kind="function",
            file_path=test_file,
            line_start=1,
            line_end=1,
        )

        result = self.manager.search("hello")

        self.assertIn("query", result)
        self.assertIn("results", result)
        self.assertIn("result_count", result)
        self.assertIn("intent", result)

    def test_save_and_load_checkpoint(self):
        """Test checkpoint save/load in file manager."""
        checkpoint_id = self.manager.save_checkpoint(
            read_entities=[1, 2, 3],
            context_summary="Found bug in auth",
            next_action="Fix verifyToken()",
        )

        self.assertNotEqual(checkpoint_id, "")

        checkpoint = self.manager.load_checkpoint()
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint["read_entities"], [1, 2, 3])

    def test_get_status(self):
        """Test status reporting."""
        status = self.manager.get_status()

        self.assertIn("project_root", status)
        self.assertIn("files_indexed", status)
        self.assertIn("entities_count", status)
        self.assertIn("checkpoint_exists", status)
        self.assertIn("stats", status)

    def test_get_stats(self):
        """Test statistics reporting."""
        stats = self.manager.get_stats()

        self.assertIn("timestamp", stats)
        self.assertIn("project_root", stats)
        self.assertIn("database_path", stats)
        self.assertIn("checkpoint_directory", stats)
        self.assertIn("stats", stats)

    def test_stats_accumulation(self):
        """Test statistics accumulation."""
        initial_searches = self.manager.stats["searches_performed"]

        self.manager.search("test")
        self.manager.search("another")

        final_searches = self.manager.stats["searches_performed"]
        self.assertEqual(final_searches, initial_searches + 2)


class TestFileManagerE2E(unittest.TestCase):
    """End-to-end workflow tests."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.manager = create_file_manager(self.project_root)

    def tearDown(self):
        self.manager.indexer.close()
        self.temp_dir.cleanup()

    def test_complete_workflow(self):
        """Test complete workflow: create files -> index -> search -> checkpoint."""
        # Create test files
        src_dir = self.project_root / "src"
        src_dir.mkdir()

        auth_file = src_dir / "auth.py"
        auth_file.write_text("def authenticate(): pass\ndef verify_token(): pass")

        db_file = src_dir / "database.py"
        db_file.write_text("def get_connection(): pass\ndef query_users(): pass")

        # Add entities
        self.manager.indexer.add_entity(
            name="authenticate",
            kind="function",
            file_path=auth_file,
            line_start=1,
            line_end=1,
        )
        self.manager.indexer.add_entity(
            name="verify_token",
            kind="function",
            file_path=auth_file,
            line_start=2,
            line_end=2,
        )

        # Search
        search_result = self.manager.search("authenticate")
        self.assertEqual(search_result["result_count"], 1)

        # Save checkpoint
        checkpoint_id = self.manager.save_checkpoint(
            read_entities=[1],
            context_summary="Reviewed authentication flow",
            next_action="Check token verification",
        )

        self.assertNotEqual(checkpoint_id, "")

        # Load checkpoint
        checkpoint = self.manager.load_checkpoint()
        self.assertEqual(checkpoint["context_summary"], "Reviewed authentication flow")

        # Verify stats
        status = self.manager.get_status()
        self.assertGreater(status["stats"]["searches_performed"], 0)
        self.assertGreater(status["stats"]["checkpoints_saved"], 0)

    def test_incremental_index_update(self):
        """Test incremental index updates."""
        test_file = self.project_root / "test.py"
        test_file.write_text("def func1(): pass")

        # First indexing
        hash1 = self.manager.indexer._compute_file_hash(test_file)
        self.manager.indexer.mark_indexed(test_file, hash1)
        self.assertFalse(self.manager.indexer.should_index(test_file))

        # Modify file
        time.sleep(0.1)  # Ensure mtime differs
        test_file.write_text("def func1(): pass\ndef func2(): pass")

        # Should re-index
        self.assertTrue(self.manager.indexer.should_index(test_file))

    def test_checkpoint_recovery(self):
        """Test checkpoint recovery scenario."""
        # Save initial checkpoint
        self.manager.save_checkpoint(
            read_entities=[1, 2, 3],
            context_summary="Initial state",
            next_action="Continue",
        )

        # Create new manager instance (simulating restart)
        manager2 = create_file_manager(self.project_root)
        try:
            # Load checkpoint
            checkpoint = manager2.load_checkpoint()
            self.assertIsNotNone(checkpoint)
            self.assertEqual(checkpoint["read_entities"], [1, 2, 3])
        finally:
            # Cleanup manager2 to prevent DB locking on Windows
            manager2.indexer.close()


def run_file_manager_tests():
    """Run all file manager tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalIndexer))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestCheckpointManager))
    suite.addTests(loader.loadTestsFromTestCase(TestNexusFileManager))
    suite.addTests(loader.loadTestsFromTestCase(TestFileManagerE2E))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_file_manager_tests()
    exit(0 if success else 1)
