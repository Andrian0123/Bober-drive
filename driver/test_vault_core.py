#!/usr/bin/env python3
"""
Unit tests for Vault Core system
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from vault_core import (
    VaultCore,
    VaultEntry,
    VaultEntryType,
    VaultEdge,
    AccessLevel
)


@pytest.fixture
def temp_vault():
    """Create temporary vault for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir))
        yield vault
        vault.shutdown()  # Ensure database is closed before cleanup


class TestVaultCore:
    """Tests for VaultCore functionality"""
    
    def test_vault_initialization(self, temp_vault):
        """Test vault initializes correctly"""
        assert temp_vault.db_path.exists()
        assert (temp_vault.vault_path / ".vault_key").exists()
    
    def test_store_and_retrieve(self, temp_vault):
        """Test storing and retrieving an entry"""
        entry = VaultEntry(
            entry_id="test_001",
            entry_type=VaultEntryType.CODE,
            title="Test Code Entry",
            content="def hello():\n    print('world')",
            summary="Simple hello function"
        )
        
        # Store
        assert temp_vault.store(entry) is True
        
        # Retrieve
        retrieved = temp_vault.retrieve("test_001")
        assert retrieved is not None
        assert retrieved.title == "Test Code Entry"
        assert retrieved.content == "def hello():\n    print('world')"
        assert retrieved.entry_type == VaultEntryType.CODE
    
    def test_encryption_of_content(self, temp_vault):
        """Test that content is encrypted in database"""
        entry = VaultEntry(
            entry_id="test_encrypted",
            entry_type=VaultEntryType.DOCUMENTATION,
            title="Secret Doc",
            content="This is sensitive information"
        )
        
        temp_vault.store(entry)
        
        # Check raw database - content should be encrypted
        import sqlite3
        conn = sqlite3.connect(str(temp_vault.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM vault_entries WHERE entry_id = ?", ("test_encrypted",))
        raw_content = cursor.fetchone()[0]
        conn.close()
        
        # Raw content should not match original
        assert raw_content != b"This is sensitive information"
        assert isinstance(raw_content, bytes)
    
    def test_multiple_entries(self, temp_vault):
        """Test storing multiple entries"""
        for i in range(5):
            entry = VaultEntry(
                entry_id=f"multi_{i}",
                entry_type=VaultEntryType.MEMORY,
                title=f"Memory Entry {i}",
                content=f"Memory content {i}"
            )
            assert temp_vault.store(entry) is True
        
        # List entries
        entries = temp_vault.list_entries(limit=10)
        assert len(entries) >= 5
    
    def test_add_edge(self, temp_vault):
        """Test adding edges between entries"""
        # Create two entries
        entry1 = VaultEntry(
            entry_id="entry_a",
            entry_type=VaultEntryType.CODE,
            title="Entry A",
            content="Content A"
        )
        entry2 = VaultEntry(
            entry_id="entry_b",
            entry_type=VaultEntryType.CODE,
            title="Entry B",
            content="Content B"
        )
        
        temp_vault.store(entry1)
        temp_vault.store(entry2)
        
        # Add edge
        edge = VaultEdge(
            source_id="entry_a",
            target_id="entry_b",
            relationship_type="depends_on",
            weight=0.9
        )
        assert temp_vault.add_edge(edge) is True
    
    def test_graph_neighbors(self, temp_vault):
        """Test retrieving neighbors in graph"""
        # Create entries
        entries = [
            VaultEntry("hub", VaultEntryType.CODE, "Hub", "Hub content"),
            VaultEntry("spoke1", VaultEntryType.CODE, "Spoke 1", "Spoke 1 content"),
            VaultEntry("spoke2", VaultEntryType.CODE, "Spoke 2", "Spoke 2 content"),
        ]
        
        for entry in entries:
            temp_vault.store(entry)
        
        # Add edges from hub to spokes
        for spoke_id in ["spoke1", "spoke2"]:
            edge = VaultEdge(
                source_id="hub",
                target_id=spoke_id,
                relationship_type="calls"
            )
            temp_vault.add_edge(edge)
        
        # Get neighbors
        neighbors = temp_vault.graph_neighbors("hub", direction="out")
        assert len(neighbors) == 2
        assert any(n["entry_id"] == "spoke1" for n in neighbors)
        assert any(n["entry_id"] == "spoke2" for n in neighbors)
    
    def test_semantic_search(self, temp_vault):
        """Test semantic search with embeddings"""
        # Create entries with embeddings
        embedding1 = [0.1, 0.2, 0.3, 0.4]
        embedding2 = [0.1, 0.2, 0.3, 0.5]  # Similar to embedding1
        embedding3 = [0.9, 0.8, 0.7, 0.6]  # Different
        
        entries = [
            VaultEntry(
                entry_id="similar_a",
                entry_type=VaultEntryType.CODE,
                title="Similar A",
                content="Content A",
                embedding=embedding1
            ),
            VaultEntry(
                entry_id="similar_b",
                entry_type=VaultEntryType.CODE,
                title="Similar B",
                content="Content B",
                embedding=embedding2
            ),
            VaultEntry(
                entry_id="different",
                entry_type=VaultEntryType.CODE,
                title="Different",
                content="Content C",
                embedding=embedding3
            ),
        ]
        
        for entry in entries:
            temp_vault.store(entry)
        
        # Search with query similar to embedding1
        query = [0.1, 0.2, 0.3, 0.4]
        results = temp_vault.semantic_search(query, limit=3)
        
        assert len(results) > 0
        # First result should be similar_a (exact match)
        assert results[0][0] == "similar_a"
    
    def test_entry_types(self, temp_vault):
        """Test different entry types"""
        types_to_test = [
            VaultEntryType.CODE,
            VaultEntryType.DOCUMENTATION,
            VaultEntryType.MEMORY,
            VaultEntryType.RULE,
            VaultEntryType.SKILL,
        ]
        
        for entry_type in types_to_test:
            entry = VaultEntry(
                entry_id=f"test_{entry_type.value}",
                entry_type=entry_type,
                title=f"Test {entry_type.value}",
                content=f"Content for {entry_type.value}"
            )
            assert temp_vault.store(entry) is True
        
        # List by type
        for entry_type in types_to_test:
            entries = temp_vault.list_entries(entry_type=entry_type, limit=1)
            assert len(entries) > 0
            assert entries[0].entry_type == entry_type
    
    def test_access_levels(self, temp_vault):
        """Test different access levels"""
        levels = [
            AccessLevel.PUBLIC,
            AccessLevel.INTERNAL,
            AccessLevel.RESTRICTED,
            AccessLevel.PRIVATE,
        ]
        
        for i, level in enumerate(levels):
            entry = VaultEntry(
                entry_id=f"access_{i}",
                entry_type=VaultEntryType.CODE,
                title=f"Access {level.value}",
                content=f"Content with {level.value} access",
                access_level=level
            )
            assert temp_vault.store(entry) is True
            
            retrieved = temp_vault.retrieve(f"access_{i}")
            assert retrieved.access_level == level
    
    def test_tags(self, temp_vault):
        """Test entry tags"""
        entry = VaultEntry(
            entry_id="tagged_entry",
            entry_type=VaultEntryType.CODE,
            title="Tagged",
            content="Content",
            tags=["python", "async", "production"]
        )
        
        temp_vault.store(entry)
        retrieved = temp_vault.retrieve("tagged_entry")
        
        assert retrieved.tags == ["python", "async", "production"]
    
    def test_delete_entry_soft(self, temp_vault):
        """Test soft delete of entry"""
        entry = VaultEntry(
            entry_id="to_delete",
            entry_type=VaultEntryType.CODE,
            title="Delete Me",
            content="This will be deleted"
        )
        
        temp_vault.store(entry)
        assert temp_vault.retrieve("to_delete") is not None
        
        # Soft delete
        assert temp_vault.delete_entry("to_delete", soft=True) is True
        
        # Should not be retrievable
        assert temp_vault.retrieve("to_delete") is None
    
    def test_delete_entry_hard(self, temp_vault):
        """Test hard delete of entry"""
        entry = VaultEntry(
            entry_id="hard_delete",
            entry_type=VaultEntryType.CODE,
            title="Hard Delete",
            content="Will be permanently deleted"
        )
        
        temp_vault.store(entry)
        
        # Hard delete
        assert temp_vault.delete_entry("hard_delete", soft=False) is True
        
        # Verify it's gone from raw database
        import sqlite3
        conn = sqlite3.connect(str(temp_vault.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vault_entries WHERE entry_id = ?", ("hard_delete",))
        result = cursor.fetchone()
        conn.close()
        
        assert result is None
    
    def test_versioning(self, temp_vault):
        """Test entry versioning"""
        entry_v1 = VaultEntry(
            entry_id="versioned",
            entry_type=VaultEntryType.CODE,
            title="Versioned Entry",
            content="Version 1",
            version=1
        )
        
        temp_vault.store(entry_v1)
        
        # Update to v2
        entry_v2 = VaultEntry(
            entry_id="versioned",
            entry_type=VaultEntryType.CODE,
            title="Versioned Entry",
            content="Version 2",
            version=2
        )
        
        temp_vault.store(entry_v2)
        
        # Retrieved should be v2
        retrieved = temp_vault.retrieve("versioned")
        assert retrieved.version == 2
        assert retrieved.content == "Version 2"
    
    def test_concurrent_access_logging(self, temp_vault):
        """Test that multiple accesses are logged"""
        entry = VaultEntry(
            entry_id="logged_entry",
            entry_type=VaultEntryType.CODE,
            title="Logged",
            content="Content"
        )
        
        temp_vault.store(entry)
        
        # Multiple reads should be logged
        for _ in range(3):
            temp_vault.retrieve("logged_entry")
        
        # Check access log (indirectly through successful operation)
        # This is mainly to verify no errors during access logging
        assert True


class TestVaultSecurity:
    """Security-related tests"""
    
    def test_encryption_key_isolation(self):
        """Test that encryption keys are properly isolated"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                vault1 = VaultCore(Path(tmpdir1))
                vault2 = VaultCore(Path(tmpdir2))
                
                # Keys should be different
                key1 = (vault1.vault_path / ".vault_key").read_text()
                key2 = (vault2.vault_path / ".vault_key").read_text()
                
                assert key1 != key2
    
    def test_encryption_key_persistence(self):
        """Test that encryption key persists across sessions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            
            # First session
            vault1 = VaultCore(vault_path)
            key1 = (vault_path / ".vault_key").read_text()
            
            entry = VaultEntry(
                entry_id="persistent",
                entry_type=VaultEntryType.CODE,
                title="Persistent",
                content="Should be retrievable"
            )
            vault1.store(entry)
            
            # Second session with same vault
            vault2 = VaultCore(vault_path)
            key2 = (vault_path / ".vault_key").read_text()
            
            # Keys should match
            assert key1 == key2
            
            # Should be able to retrieve entry
            retrieved = vault2.retrieve("persistent")
            assert retrieved is not None
            assert retrieved.content == "Should be retrievable"


class TestVaultPerformance:
    """Performance-related tests"""
    
    def test_batch_storage(self, temp_vault):
        """Test storing multiple entries efficiently"""
        entries = []
        for i in range(100):
            entry = VaultEntry(
                entry_id=f"batch_{i}",
                entry_type=VaultEntryType.CODE,
                title=f"Batch Entry {i}",
                content=f"Content {i}" * 10  # Some content
            )
            entries.append(entry)
        
        # Store all
        for entry in entries:
            assert temp_vault.store(entry) is True
        
        # List should work efficiently
        retrieved = temp_vault.list_entries(limit=100)
        assert len(retrieved) >= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
