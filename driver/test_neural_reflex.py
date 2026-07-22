#!/usr/bin/env python3
"""
Test Suite for Neural Reflex Engine
Nexus Driver v3, Week 2 Testing

Comprehensive tests for:
- Semantic search via embeddings
- Lexical search via FTS5 fallback
- Syntactic search via graph/patterns
- Parallel execution and coordination
- Context extraction (50+100)
- Result ranking and deduplication
- Performance metrics (<500ms target)
"""

import unittest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Import modules under test
from neural_reflex_engine import (
    NeuralReflexEngine, SearchResult, RefreshResponse,
    create_neural_reflex_engine, parallel_search
)
from context_extractor import (
    ContextExtractor, ExtractedContext,
    extract_context_50_100, extract_from_file_50_100
)


class TestContextExtractor(unittest.TestCase):
    """Tests for Context Extractor module"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.extractor = ContextExtractor(before_chars=50, after_chars=100)
        
        self.sample_content = """Line 1: This is the first line
Line 2: This is the second line with important info here
Line 3: This is the third line
Line 4: This is the fourth line with more details
Line 5: End of content"""
    
    def test_extract_from_content_basic(self):
        """Test basic extraction from content"""
        ctx = self.extractor.extract_from_content(
            content=self.sample_content,
            line_number=2,
            match_text="important"
        )
        
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.line_number, 2)
        self.assertIn("important", ctx.match)
        self.assertIn("second line", ctx.before)
    
    def test_extract_50_100_format(self):
        """Test default 50+100 character format"""
        long_content = "Before context " * 10 + "MATCH_HERE" + " After context " * 15
        
        ctx = self.extractor.extract_from_content(
            content=long_content,
            line_number=1,
            match_text="MATCH_HERE",
            before_chars=50,
            after_chars=100
        )
        
        self.assertIsNotNone(ctx)
        # Before should be approximately 50 chars
        self.assertLessEqual(len(ctx.before), 60)  # Allow some variance
        # After should be approximately 100 chars
        self.assertLessEqual(len(ctx.after), 120)  # Allow some variance
        self.assertIn("MATCH_HERE", ctx.match)
    
    def test_extract_from_position(self):
        """Test extraction from character position"""
        content = "Start of content" + " MATCH " + "End of content"
        match_pos = len("Start of content")
        
        ctx = self.extractor.extract_from_position(
            content=content,
            char_position=match_pos,
            before_chars=20,
            after_chars=20
        )
        
        self.assertIsNotNone(ctx)
        self.assertIn("Start", ctx.before)
        self.assertIn("End", ctx.after)
    
    def test_normalize_context(self):
        """Test context normalization"""
        dirty_context = "  Multiple   spaces  \n\t and\t\ttabs  "
        clean = ContextExtractor.normalize_context(dirty_context)
        
        self.assertNotIn("  ", clean)  # No multiple spaces
        self.assertNotIn("\t", clean)  # No tabs
        self.assertEqual(clean, "Multiple spaces | and tabs")
    
    def test_extract_from_multiline(self):
        """Test extraction across multiple lines"""
        multiline_content = """Line 1 with some content
Line 2 with TARGET information
Line 3 with more content"""
        
        ctx = self.extractor.extract_from_content(
            content=multiline_content,
            line_number=2,
            match_text="TARGET"
        )
        
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.line_number, 2)
        self.assertIn("Line 1", ctx.before)
        self.assertIn("Line 3", ctx.after)
    
    def test_extract_from_file(self):
        """Test extraction from actual file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Line 1: Header\nLine 2: Target content\nLine 3: Footer")
            temp_path = f.name
        
        try:
            ctx = self.extractor.extract_from_file(
                file_path=temp_path,
                line_number=2,
                match_text="Target"
            )
            
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.line_number, 2)
            self.assertEqual(ctx.source_file, temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_convenience_function(self):
        """Test convenience function extract_context_50_100"""
        content = "x" * 100 + "MATCH" + "y" * 150
        
        result = extract_context_50_100(
            content=content,
            line_number=1,
            match_text="MATCH"
        )
        
        self.assertIsNotNone(result)
        self.assertIn("before", result)
        self.assertIn("match", result)
        self.assertIn("after", result)
        self.assertIn("MATCH", result["match"])


class TestNeuralReflexEngine(unittest.TestCase):
    """Tests for Neural Reflex Engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_vault = Mock()
        self.engine = NeuralReflexEngine(vault_core=self.mock_vault)
    
    def test_engine_initialization(self):
        """Test engine can be created"""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.vault_core, self.mock_vault)
        self.assertEqual(self.engine.max_results_per_level, 30)
    
    def test_mock_embedding_generation(self):
        """Test mock embedding creation"""
        text = "test query"
        embedding = self.engine._mock_embedding(text)
        
        self.assertEqual(len(embedding), 384)  # Standard dimension
        # Check it's normalized
        norm = sum(x**2 for x in embedding) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=5)
    
    def test_search_result_creation(self):
        """Test SearchResult dataclass"""
        result = SearchResult(
            rank=1,
            relevance=0.95,
            search_level="semantic",
            source="test.py",
            line=42,
            context={"before": "x", "match": "y", "after": "z"},
            type="CODE",
            entity_id="test_id"
        )
        
        self.assertEqual(result.rank, 1)
        self.assertEqual(result.relevance, 0.95)
        self.assertEqual(result.line, 42)
        
        # Test serialization
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("rank", d)
        self.assertIn("context", d)
    
    def test_refresh_response_structure(self):
        """Test RefreshResponse structure"""
        results = [
            SearchResult(1, 0.9, "semantic", "file1.py", 10, {}, "CODE")
        ]
        
        response = RefreshResponse(
            query="test",
            total_hits=1,
            search_time_ms=150.5,
            results=results,
            search_levels_breakdown={"semantic": 1, "lexical": 0, "syntactic": 0}
        )
        
        self.assertEqual(response.query, "test")
        self.assertEqual(response.total_hits, 1)
        self.assertLess(response.search_time_ms, 500)
        
        # Test serialization
        d = response.to_dict()
        self.assertIn("query", d)
        self.assertIn("results", d)
        self.assertIn("search_levels_breakdown", d)
    
    def test_semantic_search_without_vault(self):
        """Test semantic search handles missing vault gracefully"""
        engine = NeuralReflexEngine(vault_core=None)
        results = engine._semantic_search("test query")
        
        self.assertEqual(results, [])
    
    def test_lexical_search_fallback(self):
        """Test fallback lexical search when FTS5 unavailable"""
        # Mock vault without fulltext_search
        mock_vault = Mock()
        mock_vault.fulltext_search = None
        
        # Add mock entries
        from vault_core import VaultEntry, VaultEntryType, AccessLevel
        
        entry = VaultEntry(
            entry_id="test_id",
            entry_type=VaultEntryType.CODE,
            title="test.py",
            content="def test_function(): pass"
        )
        
        mock_vault.list_entries = Mock(return_value=[entry])
        mock_vault.retrieve = Mock(return_value=entry)
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        results = engine._fallback_lexical_search("test")
        
        # Should find matching results
        self.assertGreater(len(results), 0)
    
    def test_pattern_building(self):
        """Test search pattern generation for syntactic search"""
        patterns = self.engine._build_search_patterns("function_name")
        
        self.assertGreater(len(patterns), 0)
        # Should include literal pattern
        self.assertTrue(any("function_name" in p[0] for p in patterns))
    
    def test_context_extraction_in_results(self):
        """Test that context is properly extracted in results"""
        from vault_core import VaultEntry, VaultEntryType
        
        entry = VaultEntry(
            entry_id="test_id",
            entry_type=VaultEntryType.CODE,
            title="test.py",
            content="Line 1\nTarget line here\nLine 3"
        )
        
        mock_vault = Mock()
        mock_vault.retrieve = Mock(return_value=entry)
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        result = engine._create_search_result(
            entry_id="test_id",
            score=0.9,
            level="syntactic",
            query="Target",
            line=2
        )
        
        self.assertIsNotNone(result)
        self.assertIn("before", result.context)
        self.assertIn("match", result.context)
        self.assertIn("after", result.context)
    
    def test_merge_and_rank_deduplication(self):
        """Test result deduplication during merge"""
        results = [
            SearchResult(1, 0.9, "semantic", "file1.py", 10, {}, "CODE"),
            SearchResult(2, 0.8, "lexical", "file1.py", 10, {}, "CODE"),  # Duplicate
            SearchResult(3, 0.7, "semantic", "file2.py", 20, {}, "CODE"),
        ]
        
        merged = self.engine._merge_and_rank(results, "test")
        
        # Should have 2 unique results (file1:10 merged, file2:20 separate)
        self.assertEqual(len(merged), 2)
        # First result should have boosted score
        self.assertGreater(merged[0].relevance, 0.9)
    
    def test_trigger_reflex_execution_time(self):
        """Test that parallel search completes within time budget"""
        mock_vault = Mock()
        mock_vault.list_entries = Mock(return_value=[])
        mock_vault.semantic_search = Mock(return_value=[])
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        
        start = time.time()
        response = engine.trigger_reflex("test query", timeout_ms=500)
        elapsed_ms = (time.time() - start) * 1000
        
        # Should complete in reasonable time
        self.assertLess(elapsed_ms, 1000)  # Should not hang
        self.assertLess(response.search_time_ms, 500)
    
    def test_trigger_reflex_with_results(self):
        """Test trigger_reflex returns proper structure"""
        mock_vault = Mock()
        mock_vault.list_entries = Mock(return_value=[])
        mock_vault.semantic_search = Mock(return_value=[])
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        response = engine.trigger_reflex("test")
        
        self.assertIsInstance(response, RefreshResponse)
        self.assertEqual(response.query, "test")
        self.assertIn("semantic", response.search_levels_breakdown)
        self.assertIn("lexical", response.search_levels_breakdown)
        self.assertIn("syntactic", response.search_levels_breakdown)
    
    def test_factory_function(self):
        """Test factory function creates engine properly"""
        mock_vault = Mock()
        engine = create_neural_reflex_engine(vault_core=mock_vault)
        
        self.assertIsInstance(engine, NeuralReflexEngine)
        self.assertEqual(engine.vault_core, mock_vault)
    
    def test_parallel_search_convenience_function(self):
        """Test convenience parallel_search function"""
        mock_vault = Mock()
        mock_vault.list_entries = Mock(return_value=[])
        mock_vault.semantic_search = Mock(return_value=[])
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        response = parallel_search(engine, "test", timeout_ms=500)
        
        self.assertIsInstance(response, RefreshResponse)
        self.assertEqual(response.query, "test")
    
    def test_extract_context_from_match(self):
        """Test context extraction around match position"""
        content = "Before context " * 4 + "MATCH_HERE" + " After context " * 8
        
        ctx = self.engine._extract_context_from_match(
            content=content,
            match_start=len("Before context " * 4),
            match_end=len("Before context " * 4) + len("MATCH_HERE"),
            before_chars=50,
            after_chars=100
        )
        
        self.assertIsNotNone(ctx)
        self.assertIn("MATCH_HERE", ctx["match"])
        self.assertIn("Before", ctx["before"])
        self.assertIn("After", ctx["after"])


class TestPerformanceMetrics(unittest.TestCase):
    """Performance and metrics tests"""
    
    def test_search_performance_target(self):
        """Test that parallel search meets <500ms target"""
        mock_vault = Mock()
        mock_vault.list_entries = Mock(return_value=[])
        mock_vault.semantic_search = Mock(return_value=[])
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        
        # Measure 5 searches
        times = []
        for _ in range(5):
            response = engine.trigger_reflex("test query")
            times.append(response.search_time_ms)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Average should be well under 500ms
        self.assertLess(avg_time, 300)
        # Even max should be under 500ms (with some margin for slow systems)
        self.assertLess(max_time, 500)
    
    def test_memory_efficiency(self):
        """Test that context extraction doesn't bloat memory"""
        import sys
        
        extractor = ContextExtractor(before_chars=50, after_chars=100)
        content = "x" * 10000  # Large content
        
        ctx = extractor.extract_from_content(
            content=content,
            line_number=1,
            match_text="x"
        )
        
        self.assertIsNotNone(ctx)
        # Context should be small even with large content
        total_context_size = (
            len(ctx.before) + len(ctx.match) + len(ctx.after)
        )
        self.assertLess(total_context_size, 500)  # Well under 500 chars


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components"""
    
    def test_full_search_pipeline(self):
        """Test complete search pipeline from query to results"""
        from vault_core import VaultEntry, VaultEntryType
        
        # Setup mock vault with sample data
        entries = [
            VaultEntry(
                entry_id="id_1",
                entry_type=VaultEntryType.CODE,
                title="module.py",
                content="def function(): pass"
            ),
            VaultEntry(
                entry_id="id_2",
                entry_type=VaultEntryType.DOCUMENTATION,
                title="README.md",
                content="This is documentation"
            )
        ]
        
        mock_vault = Mock()
        mock_vault.list_entries = Mock(return_value=entries)
        mock_vault.retrieve = Mock(side_effect=lambda x: next((e for e in entries if e.entry_id == x), None))
        mock_vault.semantic_search = Mock(return_value=[])
        
        engine = NeuralReflexEngine(vault_core=mock_vault)
        response = engine.trigger_reflex("function")
        
        self.assertIsInstance(response, RefreshResponse)
        self.assertEqual(response.query, "function")
        self.assertIsNotNone(response.results)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestContextExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestNeuralReflexEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    exit(0 if result.wasSuccessful() else 1)
