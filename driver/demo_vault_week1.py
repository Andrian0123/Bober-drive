#!/usr/bin/env python3
"""
Vault Core Week 1 - Integration Test & Demo
"""

import sys
sys.path.insert(0, 'driver')

from pathlib import Path
from vault_core import VaultCore, VaultEntry, VaultEntryType, VaultEdge
import shutil

# Setup
test_vault_path = Path('.test_vault_demo')
if test_vault_path.exists():
    shutil.rmtree(test_vault_path)

print("="*60)
print("VAULT CORE - WEEK 1 IMPLEMENTATION TEST")
print("="*60)

try:
    # 1. Initialize
    vault = VaultCore(test_vault_path)
    print("\n✓ Vault initialized successfully")
    
    # 2. Create sample entries
    entries_data = [
        ("driver_core", VaultEntryType.CODE, "Driver Orchestrator", "Main orchestration logic..."),
        ("memory_system", VaultEntryType.CODE, "Memory Manager", "Handles persistent memory..."),
        ("rules_engine", VaultEntryType.RULE, "Project Rules", "CLAUDE.md rules..."),
        ("docs_arch", VaultEntryType.DOCUMENTATION, "Architecture Doc", "System architecture..."),
    ]
    
    for entry_id, entry_type, title, content in entries_data:
        entry = VaultEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            title=title,
            content=content,
            tags=["nexus", "v3", "demo"]
        )
        vault.store(entry)
    
    print(f"✓ Stored {len(entries_data)} sample entries")
    
    # 3. Add graph relationships
    edges = [
        ("driver_core", "memory_system", "uses"),
        ("driver_core", "rules_engine", "enforces"),
        ("memory_system", "docs_arch", "documented_in"),
    ]
    
    for source, target, rel_type in edges:
        edge = VaultEdge(source, target, rel_type)
        vault.add_edge(edge)
    
    print(f"✓ Created {len(edges)} graph relationships")
    
    # 4. Retrieve and verify
    retrieved = vault.retrieve("driver_core")
    assert retrieved is not None
    assert retrieved.title == "Driver Orchestrator"
    print("✓ Retrieved entry successfully (decrypted)")
    
    # 5. List entries
    all_entries = vault.list_entries(limit=10)
    print(f"✓ Listed {len(all_entries)} entries from vault")
    
    # 6. Graph traversal
    neighbors = vault.graph_neighbors("driver_core", direction="out")
    print(f"✓ Found {len(neighbors)} outgoing relationships from driver_core")
    
    # 7. Export
    export_path = test_vault_path / "backup.json"
    vault.export(export_path)
    assert export_path.exists()
    print(f"✓ Exported vault to {export_path.name} (encrypted)")
    
    vault.shutdown()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60)
    print("\n📊 Summary:")
    print(f"   • Vault location: {test_vault_path}")
    print(f"   • Database file: {test_vault_path / 'vault.db'}")
    print(f"   • Encryption key: {test_vault_path / '.vault_key'}")
    print(f"   • Total entries stored: {len(all_entries)}")
    print(f"   • Graph edges: {len(edges)}")
    print(f"   • Backup size: {export_path.stat().st_size} bytes (encrypted)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    # Cleanup
    if test_vault_path.exists():
        shutil.rmtree(test_vault_path)
