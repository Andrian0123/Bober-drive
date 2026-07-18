#!/usr/bin/env python3
"""
Vault Core - Central Knowledge Graph System for Nexus Driver v3
Handles persistent storage, encryption, semantic search, versioning, and graph relationships.
"""

import sqlite3
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class VaultEntryType(Enum):
    """Types of entries stored in Vault"""
    CODE = "code"
    DOCUMENTATION = "documentation"
    MEMORY = "memory"
    RULE = "rule"
    RELATIONSHIP = "relationship"
    SKILL = "skill"
    PROJECT_METADATA = "project_metadata"
    DECISION = "decision"
    WORKFLOW = "workflow"
    CONFIG = "config"


class AccessLevel(Enum):
    """Access control levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    PRIVATE = "private"


@dataclass
class VaultEntry:
    """Represents a single entry in the Vault"""
    entry_id: str
    entry_type: VaultEntryType
    title: str
    content: str
    summary: Optional[str] = None
    tags: List[str] = None
    embedding: Optional[List[float]] = None
    access_level: AccessLevel = AccessLevel.INTERNAL
    created_at: str = None
    modified_at: str = None
    created_by: str = "system"
    version: int = 1
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.modified_at is None:
            self.modified_at = self.created_at


@dataclass
class VaultEdge:
    """Represents relationship between Vault entries"""
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


class VaultCore:
    """Core Vault system for Nexus Driver v3"""
    
    SCHEMA_VERSION = 3
    
    def __init__(self, vault_path: Path, encryption_key: Optional[str] = None):
        """
        Initialize Vault Core
        
        Args:
            vault_path: Path to vault database directory
            encryption_key: Master encryption key (if None, will prompt or generate)
        """
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.vault_path / "vault.db"
        self.cipher = self._setup_encryption(encryption_key)
        self._last_connection = None
        self._all_connections = []  # Track all connections for proper cleanup
        
        self._initialize_schema()
        logger.info(f"Vault initialized at {self.db_path}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.shutdown()
    
    def shutdown(self):
        """Close all database connections"""
        try:
            # Close all tracked connections
            if hasattr(self, '_all_connections'):
                for conn in self._all_connections:
                    try:
                        if conn:
                            conn.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {e}")
                self._all_connections = []
            
            # Close last connection if separate
            if hasattr(self, '_last_connection') and self._last_connection:
                try:
                    self._last_connection.close()
                except Exception as e:
                    logger.warning(f"Error closing last connection: {e}")
                self._last_connection = None
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")
    
    def _setup_encryption(self, encryption_key: Optional[str]) -> Fernet:
        """Setup AES-256 encryption using Fernet"""
        if encryption_key is None:
            # Try to load from config or generate
            key_file = self.vault_path / ".vault_key"
            if key_file.exists():
                encryption_key = key_file.read_text().strip()
            else:
                # Generate new key
                encryption_key = Fernet.generate_key().decode()
                key_file.write_text(encryption_key)
                key_file.chmod(0o600)  # Read/write for owner only
        
        # Convert string key to Fernet cipher
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        return Fernet(encryption_key)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Track connection for proper cleanup
        if hasattr(self, '_all_connections'):
            self._all_connections.append(conn)
        
        return conn
    
    def _initialize_schema(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if tables exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_entries'"
            )
            if cursor.fetchone():
                logger.info("Vault schema already initialized")
                return
            
            # Create main tables
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
            
            cursor.execute("CREATE INDEX idx_type ON vault_entries(entry_type)")
            cursor.execute("CREATE INDEX idx_created ON vault_entries(created_at)")
            cursor.execute("CREATE INDEX idx_tags ON vault_entries(tags)")
            
            cursor.execute("""
                CREATE TABLE vault_versions (
                    version_id TEXT PRIMARY KEY,
                    entry_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    content BLOB NOT NULL,
                    change_summary TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    FOREIGN KEY (entry_id) REFERENCES vault_entries(entry_id)
                )
            """)
            
            cursor.execute("CREATE INDEX idx_entry_version ON vault_versions(entry_id)")
            cursor.execute("CREATE INDEX idx_version_num ON vault_versions(version_number)")
            
            cursor.execute("""
                CREATE TABLE vault_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES vault_entries(entry_id),
                    FOREIGN KEY (target_id) REFERENCES vault_entries(entry_id)
                )
            """)
            
            cursor.execute("CREATE INDEX idx_source ON vault_edges(source_id)")
            cursor.execute("CREATE INDEX idx_target ON vault_edges(target_id)")
            cursor.execute("CREATE INDEX idx_relationship ON vault_edges(relationship_type)")
            
            cursor.execute("""
                CREATE TABLE vault_access_log (
                    log_id TEXT PRIMARY KEY,
                    entry_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    accessed_by TEXT,
                    accessed_at TEXT NOT NULL,
                    ip_address TEXT,
                    details TEXT,
                    FOREIGN KEY (entry_id) REFERENCES vault_entries(entry_id)
                )
            """)
            
            cursor.execute("CREATE INDEX idx_entry_log ON vault_access_log(entry_id)")
            cursor.execute("CREATE INDEX idx_action ON vault_access_log(action)")
            cursor.execute("CREATE INDEX idx_accessed_at ON vault_access_log(accessed_at)")
            
            cursor.execute("""
                CREATE TABLE vault_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE vault_search_cache (
                    cache_id TEXT PRIMARY KEY,
                    query_hash TEXT NOT NULL UNIQUE,
                    results BLOB,
                    created_at TEXT,
                    expires_at TEXT
                )
            """)
            
            cursor.execute("CREATE INDEX idx_expires ON vault_search_cache(expires_at)")
            
            # Insert schema metadata
            cursor.execute(
                "INSERT INTO vault_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION), datetime.utcnow().isoformat())
            )
            
            conn.commit()
            logger.info("Vault schema initialized successfully")
            
        finally:
            conn.close()
    
    def store(self, entry: VaultEntry) -> bool:
        """
        Store an entry in the Vault with encryption
        
        Args:
            entry: VaultEntry to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Encrypt content
            encrypted_content = self.cipher.encrypt(entry.content.encode())
            
            # Store embedding if present
            embedding_blob = None
            if entry.embedding:
                embedding_blob = json.dumps(entry.embedding).encode()
            
            # Serialize tags
            tags_str = json.dumps(entry.tags) if entry.tags else "[]"
            
            cursor.execute("""
                INSERT OR REPLACE INTO vault_entries
                (entry_id, entry_type, title, content, summary, tags, embedding,
                 access_level, created_at, modified_at, created_by, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.entry_type.value,
                entry.title,
                encrypted_content,
                entry.summary,
                tags_str,
                embedding_blob,
                entry.access_level.value,
                entry.created_at,
                entry.modified_at,
                entry.created_by,
                entry.version
            ))
            
            # Create version entry
            version_id = f"{entry.entry_id}_v{entry.version}_{secrets.token_hex(4)}"
            cursor.execute("""
                INSERT INTO vault_versions
                (version_id, entry_id, version_number, content, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                version_id,
                entry.entry_id,
                entry.version,
                encrypted_content,
                entry.modified_at,
                entry.created_by
            ))
            
            # Log access
            self._log_access(cursor, entry.entry_id, "CREATE" if entry.version == 1 else "UPDATE")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored entry {entry.entry_id} (v{entry.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store entry: {e}")
            return False
    
    def retrieve(self, entry_id: str) -> Optional[VaultEntry]:
        """
        Retrieve and decrypt an entry from the Vault
        
        Args:
            entry_id: ID of entry to retrieve
            
        Returns:
            Decrypted VaultEntry or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM vault_entries
                WHERE entry_id = ? AND is_deleted = 0
            """, (entry_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Entry not found: {entry_id}")
                return None
            
            # Decrypt content
            decrypted_content = self.cipher.decrypt(row['content']).decode()
            
            # Parse tags
            tags = json.loads(row['tags']) if row['tags'] else []
            
            # Parse embedding
            embedding = None
            if row['embedding']:
                embedding = json.loads(row['embedding'])
            
            self._log_access(cursor, entry_id, "READ")
            conn.commit()
            conn.close()
            
            return VaultEntry(
                entry_id=row['entry_id'],
                entry_type=VaultEntryType(row['entry_type']),
                title=row['title'],
                content=decrypted_content,
                summary=row['summary'],
                tags=tags,
                embedding=embedding,
                access_level=AccessLevel(row['access_level']),
                created_at=row['created_at'],
                modified_at=row['modified_at'],
                created_by=row['created_by'],
                version=row['version']
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve entry: {e}")
            return None
    
    def semantic_search(self, query_embedding: List[float], limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search entries by semantic similarity (requires embeddings)
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum results to return
            
        Returns:
            List of (entry_id, similarity_score) tuples
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get all embeddings
            cursor.execute("""
                SELECT entry_id, embedding FROM vault_entries
                WHERE embedding IS NOT NULL AND is_deleted = 0
            """)
            
            results = []
            for row in cursor.fetchall():
                try:
                    embedding = json.loads(row['embedding'])
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, embedding)
                    results.append((row['entry_id'], similarity))
                except Exception as e:
                    logger.warning(f"Failed to process embedding for {row['entry_id']}: {e}")
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            
            conn.close()
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def add_edge(self, edge: VaultEdge) -> bool:
        """
        Add relationship between two entries
        
        Args:
            edge: VaultEdge representing relationship
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            edge_id = f"{edge.source_id}_{edge.target_id}_{edge.relationship_type}_{secrets.token_hex(4)}"
            metadata_str = json.dumps(edge.metadata) if edge.metadata else "{}"
            
            cursor.execute("""
                INSERT INTO vault_edges
                (edge_id, source_id, target_id, relationship_type, weight, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                edge_id,
                edge.source_id,
                edge.target_id,
                edge.relationship_type,
                edge.weight,
                metadata_str,
                edge.created_at
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added edge: {edge.source_id} -> {edge.target_id} ({edge.relationship_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add edge: {e}")
            return False
    
    def graph_neighbors(self, entry_id: str, relationship_type: Optional[str] = None, direction: str = "both") -> List[Dict]:
        """
        Get connected entries in the graph
        
        Args:
            entry_id: Entry to get neighbors for
            relationship_type: Filter by relationship type (optional)
            direction: "in", "out", or "both"
            
        Returns:
            List of neighbor entries with relationship info
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            neighbors = []
            
            # Outgoing edges
            if direction in ("out", "both"):
                query = """
                    SELECT e.*, v.title as target_title, v.summary
                    FROM vault_edges e
                    JOIN vault_entries v ON e.target_id = v.entry_id
                    WHERE e.source_id = ?
                """
                params = [entry_id]
                
                if relationship_type:
                    query += " AND e.relationship_type = ?"
                    params.append(relationship_type)
                
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    neighbors.append({
                        "entry_id": row['target_id'],
                        "title": row['target_title'],
                        "relationship": row['relationship_type'],
                        "direction": "outgoing",
                        "weight": row['weight'],
                        "summary": row['summary']
                    })
            
            # Incoming edges
            if direction in ("in", "both"):
                query = """
                    SELECT e.*, v.title as source_title, v.summary
                    FROM vault_edges e
                    JOIN vault_entries v ON e.source_id = v.entry_id
                    WHERE e.target_id = ?
                """
                params = [entry_id]
                
                if relationship_type:
                    query += " AND e.relationship_type = ?"
                    params.append(relationship_type)
                
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    neighbors.append({
                        "entry_id": row['source_id'],
                        "title": row['source_title'],
                        "relationship": row['relationship_type'],
                        "direction": "incoming",
                        "weight": row['weight'],
                        "summary": row['summary']
                    })
            
            conn.close()
            return neighbors
            
        except Exception as e:
            logger.error(f"Failed to get neighbors: {e}")
            return []
    
    def list_entries(self, entry_type: Optional[VaultEntryType] = None, limit: int = 100) -> List[VaultEntry]:
        """
        List entries with optional filtering
        
        Args:
            entry_type: Filter by type
            limit: Maximum entries to return
            
        Returns:
            List of VaultEntry objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM vault_entries WHERE is_deleted = 0"
            params = []
            
            if entry_type:
                query += " AND entry_type = ?"
                params.append(entry_type.value)
            
            query += " ORDER BY modified_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                try:
                    decrypted_content = self.cipher.decrypt(row['content']).decode()
                    tags = json.loads(row['tags']) if row['tags'] else []
                    embedding = json.loads(row['embedding']) if row['embedding'] else None
                    
                    entries.append(VaultEntry(
                        entry_id=row['entry_id'],
                        entry_type=VaultEntryType(row['entry_type']),
                        title=row['title'],
                        content=decrypted_content,
                        summary=row['summary'],
                        tags=tags,
                        embedding=embedding,
                        access_level=AccessLevel(row['access_level']),
                        created_at=row['created_at'],
                        modified_at=row['modified_at'],
                        created_by=row['created_by'],
                        version=row['version']
                    ))
                except Exception as e:
                    logger.warning(f"Failed to decrypt entry {row['entry_id']}: {e}")
            
            conn.close()
            return entries
            
        except Exception as e:
            logger.error(f"Failed to list entries: {e}")
            return []
    
    def delete_entry(self, entry_id: str, soft: bool = True) -> bool:
        """
        Delete an entry (soft or hard)
        
        Args:
            entry_id: Entry to delete
            soft: If True, mark as deleted; if False, hard delete
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if soft:
                cursor.execute(
                    "UPDATE vault_entries SET is_deleted = 1 WHERE entry_id = ?",
                    (entry_id,)
                )
                self._log_access(cursor, entry_id, "SOFT_DELETE")
            else:
                # Hard delete (careful!)
                cursor.execute("DELETE FROM vault_entries WHERE entry_id = ?", (entry_id,))
                cursor.execute("DELETE FROM vault_edges WHERE source_id = ? OR target_id = ?", (entry_id, entry_id))
                cursor.execute("DELETE FROM vault_versions WHERE entry_id = ?", (entry_id,))
                self._log_access(cursor, entry_id, "HARD_DELETE")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted entry {entry_id} ({'soft' if soft else 'hard'})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete entry: {e}")
            return False
    
    def export(self, output_path: Path, include_versions: bool = True) -> bool:
        """
        Export vault to JSON (encrypted)
        
        Args:
            output_path: Path to export to
            include_versions: Include version history
            
        Returns:
            True if successful
        """
        try:
            export_data = {
                "schema_version": self.SCHEMA_VERSION,
                "exported_at": datetime.utcnow().isoformat(),
                "entries": [],
                "edges": [],
                "versions": [] if include_versions else None
            }
            
            # Export entries
            entries = self.list_entries(limit=10000)
            for entry in entries:
                export_data["entries"].append(asdict(entry))
            
            # Export edges
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vault_edges")
            
            for row in cursor.fetchall():
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                export_data["edges"].append({
                    "source_id": row['source_id'],
                    "target_id": row['target_id'],
                    "relationship_type": row['relationship_type'],
                    "weight": row['weight'],
                    "metadata": metadata
                })
            
            if include_versions:
                cursor.execute("SELECT * FROM vault_versions")
                for row in cursor.fetchall():
                    export_data["versions"].append({
                        "version_id": row['version_id'],
                        "entry_id": row['entry_id'],
                        "version_number": row['version_number'],
                        "created_at": row['created_at']
                    })
            
            conn.close()
            
            # Encrypt export
            export_json = json.dumps(export_data, indent=2, default=str)
            encrypted_export = self.cipher.encrypt(export_json.encode())
            
            output_path.write_bytes(encrypted_export)
            logger.info(f"Exported vault to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export vault: {e}")
            return False
    
    def import_backup(self, backup_path: Path) -> bool:
        """
        Import vault from encrypted backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful
        """
        try:
            encrypted_data = backup_path.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data).decode()
            import_data = json.loads(decrypted_data)
            
            # Import entries
            for entry_dict in import_data.get("entries", []):
                entry_dict["entry_type"] = VaultEntryType(entry_dict["entry_type"])
                entry_dict["access_level"] = AccessLevel(entry_dict["access_level"])
                entry = VaultEntry(**entry_dict)
                self.store(entry)
            
            # Import edges
            for edge_dict in import_data.get("edges", []):
                edge = VaultEdge(**edge_dict)
                self.add_edge(edge)
            
            logger.info(f"Imported vault from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import backup: {e}")
            return False
    
    def _log_access(self, cursor: sqlite3.Cursor, entry_id: str, action: str):
        """Log access to an entry"""
        try:
            log_id = f"{entry_id}_{action}_{secrets.token_hex(4)}"
            cursor.execute("""
                INSERT INTO vault_access_log
                (log_id, entry_id, action, accessed_at)
                VALUES (?, ?, ?, ?)
            """, (log_id, entry_id, action, datetime.utcnow().isoformat()))
        except Exception as e:
            logger.warning(f"Failed to log access: {e}")
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
        
        return dot_product / (mag1 * mag2)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    vault_dir = Path(".nexus/vault")
    vault = VaultCore(vault_dir)
    
    # Create test entry
    test_entry = VaultEntry(
        entry_id="test_001",
        entry_type=VaultEntryType.CODE,
        title="Test Entry",
        content="This is a test entry in the Vault",
        summary="Test",
        tags=["test", "demo"]
    )
    
    # Store
    vault.store(test_entry)
    
    # Retrieve
    retrieved = vault.retrieve("test_001")
    if retrieved:
        print(f"Retrieved: {retrieved.title}")
        print(f"Content: {retrieved.content}")
