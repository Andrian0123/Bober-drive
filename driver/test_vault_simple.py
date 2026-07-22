#!/usr/bin/env python3
"""
Simple test runner for Vault Core
"""

import sys
import tempfile
import gc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vault_core import VaultCore, VaultEntry, VaultEntryType, VaultEdge, AccessLevel


def test_basic_operations():
    """Test basic vault operations"""
    print("Testing basic vault operations...\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = VaultCore(Path(tmpdir))
        print("✓ Vault initialization successful")
        
        try:
            # Test 1: Store and retrieve
            entry = VaultEntry(
                entry_id="test_001",
                entry_type=VaultEntryType.CODE,
                title="Test Entry",
                content="def hello():\n    print('world')",
                summary="Simple test function",
                tags=["python", "test"]
            )
            
            assert vault.store(entry), "Failed to store entry"
            print("✓ Entry stored successfully")
            
            retrieved = vault.retrieve("test_001")
            assert retrieved is not None, "Failed to retrieve entry"
            assert retrieved.title == "Test Entry", "Title mismatch"
            assert retrieved.content == "def hello():\n    print('world')", "Content mismatch"
            print("✓ Entry retrieved and decrypted successfully")
            
            # Test 2: Multiple entries
            for i in range(5):
                entry = VaultEntry(
                    entry_id=f"multi_{i}",
                    entry_type=VaultEntryType.MEMORY,
                    title=f"Memory {i}",
                    content=f"Memory content {i}"
                )
                vault.store(entry)
            
            entries = vault.list_entries(limit=10)
            assert len(entries) >= 6, f"Expected at least 6 entries, got {len(entries)}"
            print(f"✓ Multiple entries stored and listed ({len(entries)} entries)")
            
            # Test 3: Graph edges
            entry_a = VaultEntry("entry_a", VaultEntryType.CODE, "A", "Content A")
            entry_b = VaultEntry("entry_b", VaultEntryType.CODE, "B", "Content B")
            
            vault.store(entry_a)
            vault.store(entry_b)
            
            edge = VaultEdge(
                source_id="entry_a",
                target_id="entry_b",
                relationship_type="calls",
                weight=0.9
            )
            assert vault.add_edge(edge), "Failed to add edge"
            print("✓ Graph edge created")
            
            neighbors = vault.graph_neighbors("entry_a", direction="out")
            assert len(neighbors) > 0, "No neighbors found"
            assert neighbors[0]["entry_id"] == "entry_b", "Neighbor mismatch"
            print("✓ Graph neighbors retrieved successfully")
            
            # Test 4: Access levels and tags
            restricted_entry = VaultEntry(
                entry_id="restricted",
                entry_type=VaultEntryType.CODE,
                title="Restricted",
                content="Secret content",
                access_level=AccessLevel.PRIVATE,
                tags=["secret", "private"]
            )
            
            vault.store(restricted_entry)
            retrieved = vault.retrieve("restricted")
            assert retrieved.access_level == AccessLevel.PRIVATE, "Access level mismatch"
            assert "secret" in retrieved.tags, "Tags not preserved"
            print("✓ Access levels and tags handled correctly")
            
            # Test 5: Entry types
            for entry_type in [VaultEntryType.CODE, VaultEntryType.DOCUMENTATION, 
                              VaultEntryType.RULE, VaultEntryType.SKILL]:
                entry = VaultEntry(
                    entry_id=f"type_{entry_type.value}",
                    entry_type=entry_type,
                    title=f"Type {entry_type.value}",
                    content=f"Content for {entry_type.value}"
                )
                vault.store(entry)
            
            doc_entries = vault.list_entries(entry_type=VaultEntryType.DOCUMENTATION, limit=1)
            assert len(doc_entries) > 0, "Documentation entries not found"
            print("✓ All entry types stored and retrieved")
            
            # Test 6: Semantic search (basic test)
            embedding = [0.1, 0.2, 0.3, 0.4]
            entry_with_emb = VaultEntry(
                entry_id="embedded",
                entry_type=VaultEntryType.CODE,
                title="Embedded",
                content="Content with embedding",
                embedding=embedding
            )
            vault.store(entry_with_emb)
            
            query = [0.1, 0.2, 0.3, 0.4]  # Same as embedding
            results = vault.semantic_search(query, limit=5)
            assert len(results) > 0, "Semantic search returned no results"
            assert results[0][0] == "embedded", "Semantic search result incorrect"
            print("✓ Semantic search working")
            
            # Test 7: Delete (soft)
            vault.store(VaultEntry("to_delete", VaultEntryType.CODE, "Del", "Content"))
            assert vault.retrieve("to_delete") is not None, "Entry not found before delete"
            
            vault.delete_entry("to_delete", soft=True)
            assert vault.retrieve("to_delete") is None, "Soft delete failed"
            print("✓ Soft delete working")
            
            # Test 8: Export
            export_path = Path(tmpdir) / "export.json"
            assert vault.export(export_path, include_versions=True), "Export failed"
            assert export_path.exists(), "Export file not created"
            print("✓ Export successful")
            
        finally:
            vault.shutdown()
        


def test_encryption_isolation():
    """Test encryption key isolation"""
    print("\nTesting encryption key isolation...\n")
    
    with tempfile.TemporaryDirectory() as tmpdir1:
        with tempfile.TemporaryDirectory() as tmpdir2:
            vault1 = VaultCore(Path(tmpdir1))
            vault2 = VaultCore(Path(tmpdir2))
            
            key1 = (vault1.vault_path / ".vault_key").read_text()
            key2 = (vault2.vault_path / ".vault_key").read_text()
            
            assert key1 != key2, "Keys should be different"
            print("✓ Each vault has unique encryption key")
            
            vault1.shutdown()
            vault2.shutdown()


def test_data_persistence():
    """Test data persistence across sessions"""
    print("\nTesting data persistence...\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Session 1
        vault1 = VaultCore(vault_path)
        entry = VaultEntry(
            entry_id="persistent",
            entry_type=VaultEntryType.CODE,
            title="Persistent Entry",
            content="This should persist"
        )
        vault1.store(entry)
        key1 = (vault_path / ".vault_key").read_text()
        vault1.shutdown()
        
        # Session 2 - reopen same vault
        vault2 = VaultCore(vault_path)
        key2 = (vault_path / ".vault_key").read_text()
        
        assert key1 == key2, "Encryption key changed"
        print("✓ Encryption key persisted")
        
        retrieved = vault2.retrieve("persistent")
        assert retrieved is not None, "Entry not persistent"
        assert retrieved.content == "This should persist", "Content not persisted"
        print("✓ Data persisted across sessions")
        
        vault2.shutdown()


def main():
    """Run all tests"""
    print("="*60)
    print("VAULT CORE TEST SUITE")
    print("="*60)
    
    try:
        test_basic_operations()
        test_encryption_isolation()
        test_data_persistence()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        
        # Force cleanup on Windows
        gc.collect()
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        gc.collect()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        gc.collect()
        return 1


if __name__ == "__main__":
    sys.exit(main())
