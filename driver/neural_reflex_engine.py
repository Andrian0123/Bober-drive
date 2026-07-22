#!/usr/bin/env python3
"""
Neural Reflex Engine - Parallel Multi-Level Search System
Nexus Driver v3, Week 2 Implementation

Implements parallel execution of three search levels:
1. Semantic: embedding-based cosine similarity search
2. Lexical: full-text search (FTS5) with BM25 ranking
3. Syntactic: AST graph traversal and pattern matching

All results include:
- File path and line number
- Context extraction (50 chars before + 100 chars after)
- Relevance score and search level
- Entity type and ID from Vault

Performance target: <500ms response time
"""

import threading
import time
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result with full context"""
    rank: int
    relevance: float
    search_level: str  # "semantic", "lexical", "syntactic"
    source: str  # file path
    line: int
    context: Dict[str, str]  # {"before": "...", "match": "...", "after": "..."}
    type: str  # entity type from Vault
    entity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class RefreshResponse:
    """Complete neural reflex response"""
    query: str
    total_hits: int
    search_time_ms: float
    results: List[SearchResult]
    search_levels_breakdown: Dict[str, int]  # counts by level
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "query": self.query,
            "total_hits": self.total_hits,
            "search_time_ms": self.search_time_ms,
            "search_levels_breakdown": self.search_levels_breakdown,
            "results": [r.to_dict() for r in self.results]
        }


class NeuralReflexEngine:
    """
    Main Neural Reflex Engine coordinating parallel search across three levels.
    
    Acts as the "nervous system" - receives query stimulus and sends parallel
    "impulses" to all search mechanisms simultaneously, then aggregates results.
    """
    
    def __init__(self, vault_core=None, max_results_per_level: int = 30):
        """
        Initialize Neural Reflex Engine.
        
        Args:
            vault_core: VaultCore instance for data access
            max_results_per_level: Maximum results per search level before aggregation
        """
        self.vault_core = vault_core
        self.max_results_per_level = max_results_per_level
        self.lock = threading.Lock()
        
    def trigger_reflex(self, query: str, timeout_ms: int = 500) -> RefreshResponse:
        """
        Main entry point: trigger parallel neural reflex.
        
        Executes three search levels in parallel threads and aggregates results.
        
        Args:
            query: Search query string
            timeout_ms: Maximum time to wait for all results
            
        Returns:
            RefreshResponse with ranked results from all levels
        """
        start_time = time.time()
        results_lock = threading.Lock()
        all_results = []
        errors = []
        
        # Initialize result containers for each search level
        semantic_results = []
        lexical_results = []
        syntactic_results = []
        
        def run_semantic():
            """Thread 1: Semantic search via embeddings"""
            try:
                results = self._semantic_search(query)
                with results_lock:
                    semantic_results.extend(results)
            except Exception as e:
                logger.error(f"Semantic search error: {e}")
                errors.append(("semantic", str(e)))
        
        def run_lexical():
            """Thread 2: Lexical search via FTS5"""
            try:
                results = self._lexical_search(query)
                with results_lock:
                    lexical_results.extend(results)
            except Exception as e:
                logger.error(f"Lexical search error: {e}")
                errors.append(("lexical", str(e)))
        
        def run_syntactic():
            """Thread 3: Syntactic search via graph and patterns"""
            try:
                results = self._syntactic_search(query)
                with results_lock:
                    syntactic_results.extend(results)
            except Exception as e:
                logger.error(f"Syntactic search error: {e}")
                errors.append(("syntactic", str(e)))
        
        # Spin up three parallel threads
        t1 = threading.Thread(target=run_semantic, daemon=True)
        t2 = threading.Thread(target=run_lexical, daemon=True)
        t3 = threading.Thread(target=run_syntactic, daemon=True)
        
        t1.start()
        t2.start()
        t3.start()
        
        # Wait for all threads to complete (with timeout)
        timeout_seconds = timeout_ms / 1000.0
        t1.join(timeout=timeout_seconds * 0.9)
        t2.join(timeout=timeout_seconds * 0.9)
        t3.join(timeout=timeout_seconds * 0.9)
        
        # Combine all results
        all_results.extend(semantic_results)
        all_results.extend(lexical_results)
        all_results.extend(syntactic_results)
        
        # Merge, deduplicate, and rank
        merged_results = self._merge_and_rank(
            all_results,
            query
        )
        
        # Prepare response
        elapsed_ms = (time.time() - start_time) * 1000
        
        search_breakdown = {
            "semantic": len(semantic_results),
            "lexical": len(lexical_results),
            "syntactic": len(syntactic_results)
        }
        
        response = RefreshResponse(
            query=query,
            total_hits=len(merged_results),
            search_time_ms=round(elapsed_ms, 2),
            results=merged_results[:20],  # Top 20 results
            search_levels_breakdown=search_breakdown
        )
        
        if errors:
            logger.warning(f"Search completed with {len(errors)} error(s): {errors}")
        
        return response
    
    def _semantic_search(self, query: str) -> List[SearchResult]:
        """
        Search Level 1: Semantic search via embeddings and cosine similarity.
        
        Converts query to embedding, finds similar vectors in Vault.
        """
        if not self.vault_core:
            return []
        
        try:
            # Try to get embedding from vault_core
            # Assumes vault_core has generate_embedding() or similar
            if hasattr(self.vault_core, 'generate_embedding'):
                query_embedding = self.vault_core.generate_embedding(query)
            else:
                # Fallback: simple mock implementation
                query_embedding = self._mock_embedding(query)
            
            # Semantic search in vault
            if hasattr(self.vault_core, 'semantic_search'):
                matches = self.vault_core.semantic_search(
                    query_embedding,
                    limit=self.max_results_per_level
                )
                
                results = []
                for entry_id, score in matches:
                    result = self._create_search_result(
                        entry_id=entry_id,
                        score=score,
                        level="semantic",
                        query=query
                    )
                    if result:
                        results.append(result)
                
                return results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _lexical_search(self, query: str) -> List[SearchResult]:
        """
        Search Level 2: Lexical search via FTS5 full-text index.
        
        Uses exact word matching and BM25 ranking from FTS5 index.
        """
        if not self.vault_core:
            return []
        
        try:
            # Try FTS5 search if available
            if hasattr(self.vault_core, 'fulltext_search'):
                matches = self.vault_core.fulltext_search(
                    query,
                    limit=self.max_results_per_level
                )
                
                results = []
                for entry_id, score, line_num in matches:
                    result = self._create_search_result(
                        entry_id=entry_id,
                        score=score,
                        level="lexical",
                        query=query,
                        line=line_num
                    )
                    if result:
                        results.append(result)
                
                return results
            else:
                # Fallback: simple string matching in entries
                return self._fallback_lexical_search(query)
                
        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return []
    
    def _fallback_lexical_search(self, query: str) -> List[SearchResult]:
        """
        Fallback lexical search using simple string matching.
        Used when FTS5 is not available in vault_core.
        """
        if not self.vault_core:
            return []
        
        results = []
        try:
            entries = self.vault_core.list_entries(limit=100)
            
            for entry in entries:
                # Count keyword occurrences
                content = entry.content.lower()
                query_lower = query.lower()
                
                if query_lower in content:
                    # Simple BM25-like scoring: normalized term frequency
                    count = content.count(query_lower)
                    score = min(1.0, count / max(len(query_lower), 1) * 0.5)
                    
                    result = self._create_search_result(
                        entry_id=entry.entry_id,
                        score=score,
                        level="lexical",
                        query=query
                    )
                    if result:
                        results.append(result)
            
            return results[:self.max_results_per_level]
            
        except Exception as e:
            logger.error(f"Fallback lexical search failed: {e}")
            return []
    
    def _syntactic_search(self, query: str) -> List[SearchResult]:
        """
        Search Level 3: Syntactic search via graph traversal and pattern matching.
        
        Uses AST graph relationships, regex patterns, and semantic relationships.
        """
        if not self.vault_core:
            return []
        
        try:
            results = []
            
            # Pattern matching for code/syntax structures
            patterns = self._build_search_patterns(query)
            
            # Get all entries
            entries = self.vault_core.list_entries(limit=100)
            
            for entry in entries:
                for pattern, pattern_type in patterns:
                    matches = re.finditer(pattern, entry.content, re.IGNORECASE)
                    
                    for match in matches:
                        # Calculate line number for match
                        line_num = entry.content[:match.start()].count('\n') + 1
                        
                        # Score based on pattern specificity
                        score = 0.6 + (0.1 * len(pattern))  # More specific patterns score higher
                        
                        result = self._create_search_result(
                            entry_id=entry.entry_id,
                            score=min(1.0, score),
                            level="syntactic",
                            query=query,
                            line=line_num,
                            match_obj=match
                        )
                        if result:
                            results.append(result)
            
            # Try graph traversal if available
            if hasattr(self.vault_core, 'graph_neighbors'):
                # Find entries related to query terms
                for entry in entries:
                    if any(term in entry.title.lower() for term in query.split()):
                        neighbors = self.vault_core.graph_neighbors(entry.entry_id)
                        for neighbor in neighbors:
                            result = self._create_search_result(
                                entry_id=neighbor.get('entry_id'),
                                score=0.5 * neighbor.get('weight', 1.0),
                                level="syntactic",
                                query=query,
                                metadata={"relationship": neighbor.get('relationship_type')}
                            )
                            if result:
                                results.append(result)
            
            return results[:self.max_results_per_level]
            
        except Exception as e:
            logger.error(f"Syntactic search failed: {e}")
            return []
    
    def _build_search_patterns(self, query: str) -> List[Tuple[str, str]]:
        """
        Build regex patterns from query for syntactic search.
        
        Returns list of (pattern, pattern_type) tuples.
        """
        patterns = []
        
        # Query as literal pattern
        patterns.append((re.escape(query), "literal"))
        
        # Query as word boundary pattern
        words = query.split()
        if words:
            word_pattern = r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b'
            patterns.append((word_pattern, "word"))
        
        # Common code patterns
        if any(c in query for c in ['(', ')', '{', '}', '[']):
            # Looks like code - add bracket patterns
            patterns.append((r'def\s+\w*' + re.escape(words[0]) + r'\s*\(', "definition"))
        
        return patterns
    
    def _merge_and_rank(
        self,
        all_results: List[SearchResult],
        query: str
    ) -> List[SearchResult]:
        """
        Merge results from all three search levels and rank by relevance.
        
        Deduplicates results, combines scores from multiple levels, and sorts.
        """
        if not all_results:
            return []
        
        # Group by (source, line) to detect duplicates
        merged: Dict[Tuple[str, int], SearchResult] = {}
        
        for result in all_results:
            key = (result.source, result.line)
            
            if key in merged:
                # Combine scores from multiple levels
                existing = merged[key]
                combined_score = max(existing.relevance, result.relevance)
                # Boost score if found in multiple levels
                combined_score = min(1.0, combined_score * 1.1)
                
                existing.relevance = combined_score
                existing.search_level += f"+{result.search_level}"
            else:
                merged[key] = result
        
        # Sort by relevance (descending)
        ranked = sorted(
            merged.values(),
            key=lambda r: (r.relevance, -r.rank),
            reverse=True
        )
        
        # Re-rank
        for idx, result in enumerate(ranked, 1):
            result.rank = idx
        
        return ranked
    
    def _create_search_result(
        self,
        entry_id: str,
        score: float,
        level: str,
        query: str,
        line: int = 0,
        match_obj = None,
        metadata: Optional[Dict] = None
    ) -> Optional[SearchResult]:
        """
        Create a SearchResult object with context extraction.
        
        Args:
            entry_id: ID of Vault entry
            score: Relevance score (0-1)
            level: Search level (semantic/lexical/syntactic)
            query: Original query string
            line: Line number of match
            match_obj: Regex match object (if from pattern matching)
            metadata: Additional metadata
        """
        try:
            if not self.vault_core:
                return None
            
            # Retrieve entry from vault
            if not hasattr(self.vault_core, 'retrieve'):
                return None
            
            entry = self.vault_core.retrieve(entry_id)
            if not entry:
                return None
            
            # Extract context (50 before + 100 after)
            if match_obj:
                context = self._extract_context_from_match(
                    entry.content,
                    match_obj.start(),
                    match_obj.end()
                )
                match_text = match_obj.group(0)
            else:
                # Find query in content
                content_lower = entry.content.lower()
                query_lower = query.lower()
                pos = content_lower.find(query_lower)
                
                if pos >= 0:
                    context = self._extract_context_from_match(
                        entry.content,
                        pos,
                        pos + len(query)
                    )
                    match_text = entry.content[pos:pos+len(query)]
                else:
                    context = {
                        "before": "",
                        "match": "",
                        "after": ""
                    }
                    match_text = ""
            
            # Build file path (assuming entry.content has structure with path)
            source_path = entry.title or f"entry_{entry_id}"
            
            result = SearchResult(
                rank=0,  # Will be set during ranking
                relevance=max(0.0, min(1.0, score)),
                search_level=level,
                source=source_path,
                line=line,
                context=context,
                type=entry.entry_type.value if hasattr(entry.entry_type, 'value') else str(entry.entry_type),
                entity_id=entry_id,
                metadata=metadata or {}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create search result for {entry_id}: {e}")
            return None
    
    def _extract_context_from_match(
        self,
        content: str,
        match_start: int,
        match_end: int,
        before_chars: int = 50,
        after_chars: int = 100
    ) -> Dict[str, str]:
        """
        Extract context around a match in content.
        
        Returns: {"before": "...", "match": "...", "after": "..."}
        """
        # Extract before context
        before_start = max(0, match_start - before_chars)
        before_text = content[before_start:match_start]
        
        # Extract match
        match_text = content[match_start:match_end]
        
        # Extract after context
        after_end = min(len(content), match_end + after_chars)
        after_text = content[match_end:after_end]
        
        return {
            "before": before_text.strip(),
            "match": match_text.strip(),
            "after": after_text.strip()
        }
    
    def _mock_embedding(self, text: str) -> List[float]:
        """
        Create a mock embedding for testing when sentence-transformers unavailable.
        
        In production, this would use actual embedding model.
        """
        # Simple hash-based mock embedding (384-dimensional)
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        embedding = []
        for i in range(384):
            # Deterministic but varied values
            value = ((hash_int + i) % 1000) / 1000.0 * 2.0 - 1.0
            embedding.append(value)
        
        # Normalize to unit vector
        norm = sum(x**2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding


# Convenience functions for direct use
def create_neural_reflex_engine(vault_core=None) -> NeuralReflexEngine:
    """Factory function to create and return a Neural Reflex Engine instance."""
    return NeuralReflexEngine(vault_core=vault_core)


def parallel_search(
    engine: NeuralReflexEngine,
    query: str,
    timeout_ms: int = 500
) -> RefreshResponse:
    """
    Convenience function to trigger a parallel neural reflex search.
    
    Args:
        engine: NeuralReflexEngine instance
        query: Search query
        timeout_ms: Maximum execution time
        
    Returns:
        RefreshResponse with all results
    """
    return engine.trigger_reflex(query, timeout_ms=timeout_ms)
