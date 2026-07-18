#!/usr/bin/env python3
"""
Migration script from Nexus Driver v2 to v3
Converts existing memory.db and project_graph.json to Vault system
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from vault_core import VaultCore, VaultEntry, VaultEntryType, VaultEdge, AccessLevel

logger = logging.getLogger(__name__)


class V2toV3Migrator:
    """Handles migration from v2 to v3 architecture"""
    
    def __init__(self, old_nexus_path: Path, new_nexus_path: Path):
        """
        Initialize migrator
        
        Args:
            old_nexus_path: Path to .nexus directory (v2)
            new_nexus_path: Path to new vault directory (v3)
        """
        self.old_path = Path(old_nexus_path)
        self.new_path = Path(new_nexus_path)
        self.vault = VaultCore(self.new_path)
        
        self.stats = {
            "memory_entries_migrated": 0,
            "graph_entries_migrated": 0,
            "graph_edges_migrated": 0,
            "rules_migrated": 0,
            "errors": []
        }
    
    def migrate_all(self) -> bool:
        """Execute full migration"""
        logger.info("Starting migration from v2 to v3...")
        
        try:
            self._migrate_memory()
            self._migrate_project_graph()
            self._migrate_rules()
            self._migrate_cache()
            
            self._print_summary()
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.stats["errors"].append(str(e))
            return False
    
    def _migrate_memory(self):
        """Migrate memory.db entries to Vault"""
        memory_db = self.old_path / "memory.db"
        
        if not memory_db.exists():
            logger.warning(f"No memory.db found at {memory_db}")
            return
        
        logger.info(f"Migrating from {memory_db}...")
        
        try:
            conn = sqlite3.connect(str(memory_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try to get memory entries (schema may vary)
            try:
                cursor.execute("SELECT * FROM memory_entries")
            except sqlite3.OperationalError:
                cursor.execute("SELECT * FROM memories")
            
            for row in cursor.fetchall():
                try:
                    entry_id = str(uuid.uuid4())[:8]
                    
                    entry = VaultEntry(
                        entry_id=entry_id,
                        entry_type=VaultEntryType.MEMORY,
                        title=row.get("title", "Migrated Memory Entry"),
                        content=row.get("content", row.get("text", "")),
                        summary=row.get("summary"),
                        tags=self._parse_tags(row.get("tags")),
                        access_level=AccessLevel.INTERNAL,
                        created_by="migrator_v2",
                        version=1
                    )
                    
                    if self.vault.store(entry):
                        self.stats["memory_entries_migrated"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate memory entry: {e}")
                    self.stats["errors"].append(f"Memory: {e}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to migrate memory: {e}")
            self.stats["errors"].append(f"Memory migration: {e}")
    
    def _migrate_project_graph(self):
        """Migrate project_graph.json to Vault graph"""
        graph_file = self.old_path / "project_graph.json"
        
        if not graph_file.exists():
            logger.warning(f"No project_graph.json found at {graph_file}")
            return
        
        logger.info(f"Migrating from {graph_file}...")
        
        try:
            graph_data = json.loads(graph_file.read_text())
            
            # Migrate nodes as entries
            for node_id, node_data in graph_data.get("nodes", {}).items():
                try:
                    entry = VaultEntry(
                        entry_id=node_id,
                        entry_type=self._infer_entry_type(node_data),
                        title=node_data.get("label", node_id),
                        content=json.dumps(node_data, indent=2),
                        summary=node_data.get("description"),
                        tags=node_data.get("tags", []),
                        access_level=AccessLevel.INTERNAL,
                        created_by="migrator_v2",
                        version=1
                    )
                    
                    if self.vault.store(entry):
                        self.stats["graph_entries_migrated"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate node {node_id}: {e}")
                    self.stats["errors"].append(f"Node {node_id}: {e}")
            
            # Migrate edges
            for edge_data in graph_data.get("edges", []):
                try:
                    edge = VaultEdge(
                        source_id=edge_data.get("source"),
                        target_id=edge_data.get("target"),
                        relationship_type=edge_data.get("type", "relates_to"),
                        weight=edge_data.get("weight", 1.0),
                        metadata=edge_data.get("metadata", {})
                    )
                    
                    if self.vault.add_edge(edge):
                        self.stats["graph_edges_migrated"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate edge: {e}")
                    self.stats["errors"].append(f"Edge: {e}")
        
        except Exception as e:
            logger.error(f"Failed to migrate project graph: {e}")
            self.stats["errors"].append(f"Graph migration: {e}")
    
    def _migrate_rules(self):
        """Migrate project rules and agent configs"""
        rules_files = [
            self.old_path.parent / "CLAUDE.md",
            self.old_path.parent / ".cursorrules",
            self.old_path.parent / "AGENTS.md",
            self.old_path.parent / "AGENTS.local.md",
        ]
        
        for rules_file in rules_files:
            if not rules_file.exists():
                continue
            
            logger.info(f"Migrating rules from {rules_file.name}...")
            
            try:
                content = rules_file.read_text()
                
                entry = VaultEntry(
                    entry_id=f"rule_{rules_file.stem}",
                    entry_type=VaultEntryType.RULE,
                    title=f"Project Rules: {rules_file.name}",
                    content=content,
                    summary=f"Migrated from {rules_file.name}",
                    tags=["rules", "migrated", rules_file.suffix],
                    access_level=AccessLevel.INTERNAL,
                    created_by="migrator_v2",
                    version=1
                )
                
                if self.vault.store(entry):
                    self.stats["rules_migrated"] += 1
                
            except Exception as e:
                logger.warning(f"Failed to migrate rules from {rules_file.name}: {e}")
                self.stats["errors"].append(f"Rules {rules_file.name}: {e}")
    
    def _migrate_cache(self):
        """Migrate cache.json to Vault cache entries"""
        cache_file = self.old_path / "cache.json"
        
        if not cache_file.exists():
            logger.warning(f"No cache.json found at {cache_file}")
            return
        
        logger.info(f"Migrating cache from {cache_file}...")
        
        try:
            cache_data = json.loads(cache_file.read_text())
            
            # Store cache as a single entry for now
            entry = VaultEntry(
                entry_id="migrated_cache",
                entry_type=VaultEntryType.CONFIG,
                title="Migrated Cache",
                content=json.dumps(cache_data, indent=2),
                summary="Cache from v2 migration",
                tags=["cache", "migrated"],
                access_level=AccessLevel.INTERNAL,
                created_by="migrator_v2",
                version=1
            )
            
            self.vault.store(entry)
            
        except Exception as e:
            logger.warning(f"Failed to migrate cache: {e}")
            self.stats["errors"].append(f"Cache: {e}")
    
    def _parse_tags(self, tags_input: any) -> List[str]:
        """Parse tags from various formats"""
        if isinstance(tags_input, list):
            return tags_input
        elif isinstance(tags_input, str):
            return [t.strip() for t in tags_input.split(",") if t.strip()]
        else:
            return []
    
    def _infer_entry_type(self, node_data: Dict) -> VaultEntryType:
        """Infer entry type from node data"""
        node_type = node_data.get("type", "").lower()
        
        mapping = {
            "file": VaultEntryType.CODE,
            "code": VaultEntryType.CODE,
            "function": VaultEntryType.CODE,
            "class": VaultEntryType.CODE,
            "doc": VaultEntryType.DOCUMENTATION,
            "documentation": VaultEntryType.DOCUMENTATION,
            "memory": VaultEntryType.MEMORY,
            "skill": VaultEntryType.SKILL,
            "rule": VaultEntryType.RULE,
            "workflow": VaultEntryType.WORKFLOW,
        }
        
        for key, entry_type in mapping.items():
            if key in node_type:
                return entry_type
        
        return VaultEntryType.CODE  # Default
    
    def _print_summary(self):
        """Print migration summary"""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY: v2 → v3")
        print("="*60)
        print(f"Memory entries migrated:    {self.stats['memory_entries_migrated']}")
        print(f"Graph entries migrated:     {self.stats['graph_entries_migrated']}")
        print(f"Graph edges migrated:       {self.stats['graph_edges_migrated']}")
        print(f"Rules migrated:             {self.stats['rules_migrated']}")
        
        if self.stats["errors"]:
            print(f"\nErrors encountered ({len(self.stats['errors'])}):")
            for i, error in enumerate(self.stats["errors"][:10], 1):
                print(f"  {i}. {error}")
            if len(self.stats["errors"]) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        
        print("="*60 + "\n")
    
    def export_migration_report(self, report_path: Path) -> bool:
        """Export migration report to file"""
        try:
            report = {
                "migration_timestamp": datetime.utcnow().isoformat(),
                "source": str(self.old_path),
                "destination": str(self.new_path),
                "statistics": self.stats,
                "status": "success" if not self.stats["errors"] else "completed_with_errors"
            }
            
            report_path.write_text(json.dumps(report, indent=2))
            logger.info(f"Migration report saved to {report_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save migration report: {e}")
            return False


def main():
    """Main migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Nexus Driver from v2 to v3")
    parser.add_argument("--old-nexus", default=".nexus", help="Path to old .nexus directory")
    parser.add_argument("--new-vault", default=".nexus/vault", help="Path to new vault directory")
    parser.add_argument("--report", default="migration_report.json", help="Path to save migration report")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    old_path = Path(args.old_nexus)
    new_path = Path(args.new_vault)
    
    if not old_path.exists():
        logger.error(f"Old nexus path not found: {old_path}")
        return False
    
    migrator = V2toV3Migrator(old_path, new_path)
    success = migrator.migrate_all()
    
    if args.report:
        migrator.export_migration_report(Path(args.report))
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
