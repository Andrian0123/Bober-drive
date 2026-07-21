#!/usr/bin/env python3
"""
Nexus File Manager v1.0
Intelligent file indexing, search, and checkpoint management for Bober-Drive.

Features:
- Lazy incremental indexing (hash-based)
- Two-level search system (ripgrep + semantic)
- Checkpoint persistence (.agent/ directory)
- Result caching with TTL
- Token economy optimization
"""

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FileState:
    """Represents the indexed state of a file."""
    path: str
    mtime: float
    size: int
    file_hash: str
    indexed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IndexedEntity:
    """Represents a code entity (function, class, method, etc.)."""
    id: int
    name: str
    kind: str  # "function", "class", "method", "variable", etc.
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: Optional[str] = None
    language: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Single search result with relevance score."""
    entity_id: int
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    signature: str
    score: float  # 0.0 - 1.0
    search_type: str  # "ripgrep" or "semantic"
    matched_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Checkpoint:
    """Session checkpoint for context preservation."""
    checkpoint_id: str
    timestamp: float
    read_entities: List[int] = field(default_factory=list)
    context_summary: str = ""
    next_action: str = ""
    session_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Incremental Indexer
# ============================================================================

class IncrementalIndexer:
    """Lazy, hash-based file indexer with SQLite persistence."""

    def __init__(self, project_root: Path, db_path: Optional[Path] = None):
        self.project_root = Path(project_root).resolve()
        self.db_path = db_path or (self.project_root / ".nexus" / "file_manager.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._file_states: Dict[str, FileState] = {}
        self._entities_cache: Dict[int, IndexedEntity] = {}

        self._init_db()
        self._load_file_states()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_states (
                    path TEXT PRIMARY KEY,
                    mtime REAL,
                    size INTEGER,
                    file_hash TEXT,
                    indexed_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT,
                    file_path TEXT NOT NULL,
                    line_start INTEGER,
                    line_end INTEGER,
                    signature TEXT,
                    docstring TEXT,
                    language TEXT,
                    indexed_at REAL
                )
                """
            )
            # Create FTS5 index for fast text search
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                    name, kind, signature, docstring, content=entities, content_rowid=id
                )
                """
            )
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"Error closing database: {e}")
            finally:
                self._conn = None

    def _load_file_states(self) -> None:
        """Load file states from database into memory."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM file_states")
            for row in cursor.fetchall():
                state = FileState(
                    path=row["path"],
                    mtime=row["mtime"],
                    size=row["size"],
                    file_hash=row["file_hash"],
                    indexed_at=row["indexed_at"],
                )
                self._file_states[row["path"]] = state

    @staticmethod
    def _compute_file_hash(path: Path) -> str:
        """Compute SHA256 hash of file content (first 64KB for speed)."""
        try:
            with open(path, "rb") as f:
                content = f.read(65536)  # Read first 64KB
            return hashlib.sha256(content).hexdigest()[:16]
        except (OSError, IOError) as e:
            logger.warning(f"Cannot hash {path}: {e}")
            return ""

    def should_index(self, file_path: Path) -> bool:
        """Check if file needs re-indexing based on hash."""
        rel_path = str(file_path.relative_to(self.project_root))

        if rel_path not in self._file_states:
            return True  # New file

        stat = file_path.stat()
        stored = self._file_states[rel_path]

        # Check mtime and size first (fast)
        if stored.mtime != stat.st_mtime or stored.size != stat.st_size:
            return True

        # Check hash for safety
        new_hash = self._compute_file_hash(file_path)
        return new_hash != stored.file_hash

    def mark_indexed(self, file_path: Path, file_hash: str) -> None:
        """Mark file as indexed."""
        rel_path = str(file_path.relative_to(self.project_root))
        stat = file_path.stat()

        state = FileState(
            path=rel_path,
            mtime=stat.st_mtime,
            size=stat.st_size,
            file_hash=file_hash,
        )

        self._file_states[rel_path] = state

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_states (path, mtime, size, file_hash, indexed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rel_path, stat.st_mtime, stat.st_size, file_hash, state.indexed_at),
            )
            conn.commit()

    def add_entity(
        self,
        name: str,
        kind: str,
        file_path: Path,
        line_start: int,
        line_end: int,
        signature: str = "",
        docstring: Optional[str] = None,
        language: str = "",
    ) -> int:
        """Add indexed entity to database."""
        rel_path = str(file_path.relative_to(self.project_root))

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO entities
                (name, kind, file_path, line_start, line_end, signature, docstring, language, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, kind, rel_path, line_start, line_end, signature, docstring, language, time.time()),
            )
            entity_id = cursor.lastrowid

            # Update FTS5 index
            conn.execute(
                """
                INSERT INTO entities_fts (rowid, name, kind, signature, docstring)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entity_id, name, kind, signature, docstring or ""),
            )
            conn.commit()

        return entity_id

    def get_all_entities(self) -> List[IndexedEntity]:
        """Retrieve all indexed entities."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM entities")
            entities = []
            for row in cursor.fetchall():
                entity = IndexedEntity(
                    id=row["id"],
                    name=row["name"],
                    kind=row["kind"],
                    file_path=row["file_path"],
                    line_start=row["line_start"],
                    line_end=row["line_end"],
                    signature=row["signature"],
                    docstring=row["docstring"],
                    language=row["language"],
                )
                entities.append(entity)
            return entities

    def clear(self) -> None:
        """Clear all indexed data."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM entities")
            conn.execute("DELETE FROM entities_fts")
            conn.execute("DELETE FROM file_states")
            conn.commit()

        self._file_states.clear()
        self._entities_cache.clear()


# ============================================================================
# Two-Level Search Engine
# ============================================================================

class SearchEngine:
    """Two-level search: ripgrep (fast) + semantic (accurate)."""

    def __init__(self, indexer: IncrementalIndexer, project_root: Path):
        self.indexer = indexer
        self.project_root = Path(project_root).resolve()
        self._cache: Dict[str, List[SearchResult]] = {}
        self._cache_ttl_sec = 600  # 10 minutes

    def search(
        self,
        query: str,
        max_results: int = 20,
        use_ripgrep: bool = True,
        use_semantic: bool = True,
    ) -> List[SearchResult]:
        """Execute two-level search."""
        cache_key = f"{query}:{max_results}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        results: List[SearchResult] = []

        # Level 1: Fast search (ripgrep)
        if use_ripgrep:
            results.extend(self._search_ripgrep(query, max_results // 2))

        # Level 2: Semantic search (SQLite FTS5)
        if use_semantic:
            results.extend(self._search_semantic(query, max_results // 2))

        # Deduplicate and sort by score
        seen_ids = set()
        unique_results = []
        for result in sorted(results, key=lambda r: r.score, reverse=True):
            if result.entity_id not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result.entity_id)

        results = unique_results[:max_results]

        # Cache result
        self._cache[cache_key] = results

        return results

    def _search_ripgrep(self, query: str, max_results: int) -> List[SearchResult]:
        """Level 1: Fast ripgrep search (or fallback to basic search)."""
        results: List[SearchResult] = []

        try:
            # Try to use ripgrep if available
            cmd = [
                "rg",
                "-l",  # Only list file names
                query,
                str(self.project_root),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                # Parse ripgrep output: each line is a file path
                for line in result.stdout.strip().split("\n"):
                    if not line or ":" in line:  # Skip empty or type-list lines
                        continue
                    
                    try:
                        file_path = Path(line.strip())
                        if file_path.is_absolute():
                            file_path = file_path.resolve()
                        
                        # Get entities from this file
                        for entity in self.indexer.get_all_entities():
                            if query.lower() in entity.name.lower():
                                results.append(
                                    SearchResult(
                                        entity_id=entity.id,
                                        name=entity.name,
                                        kind=entity.kind,
                                        file_path=entity.file_path,
                                        line_start=entity.line_start,
                                        line_end=entity.line_end,
                                        signature=entity.signature,
                                        score=0.7,  # Ripgrep score
                                        search_type="ripgrep",
                                    )
                                )
                        
                        if len(results) >= max_results:
                            return results
                    except (ValueError, OSError):
                        continue

        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Ripgrep search failed, using fallback: {e}")

        # Fallback: simple grep-like search in entity names
        if not results:
            for entity in self.indexer.get_all_entities():
                if query.lower() in entity.name.lower() or query.lower() in (entity.signature or "").lower():
                    results.append(
                        SearchResult(
                            entity_id=entity.id,
                            name=entity.name,
                            kind=entity.kind,
                            file_path=entity.file_path,
                            line_start=entity.line_start,
                            line_end=entity.line_end,
                            signature=entity.signature,
                            score=0.5,  # Lower score for fallback
                            search_type="fallback",
                        )
                    )
                    if len(results) >= max_results:
                        break

        return results

    def _search_semantic(self, query: str, max_results: int) -> List[SearchResult]:
        """Level 2: Semantic search using FTS5."""
        results: List[SearchResult] = []

        with self.indexer._get_conn() as conn:
            # FTS5 search with ranking
            cursor = conn.execute(
                """
                SELECT rowid, rank FROM entities_fts
                WHERE entities_fts MATCH ?
                ORDER BY rank DESC
                LIMIT ?
                """,
                (query, max_results),
            )

            for rowid, rank in cursor.fetchall():
                # Get full entity details
                entity_row = conn.execute(
                    "SELECT * FROM entities WHERE id = ?", (rowid,)
                ).fetchone()

                if entity_row:
                    entity = IndexedEntity(
                        id=entity_row["id"],
                        name=entity_row["name"],
                        kind=entity_row["kind"],
                        file_path=entity_row["file_path"],
                        line_start=entity_row["line_start"],
                        line_end=entity_row["line_end"],
                        signature=entity_row["signature"],
                        docstring=entity_row["docstring"],
                        language=entity_row["language"],
                    )

                    # Calculate relevance score
                    score = max(0.0, 1.0 + (rank / 100.0))  # FTS5 rank is negative

                    results.append(
                        SearchResult(
                            entity_id=entity.id,
                            name=entity.name,
                            kind=entity.kind,
                            file_path=entity.file_path,
                            line_start=entity.line_start,
                            line_end=entity.line_end,
                            signature=entity.signature,
                            score=min(1.0, score),  # Clamp to [0, 1]
                            search_type="semantic",
                        )
                    )

        return results

    def clear_cache(self) -> None:
        """Clear search result cache."""
        self._cache.clear()


# ============================================================================
# Checkpoint Manager
# ============================================================================

class CheckpointManager:
    """Save and restore session checkpoints for context preservation."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.checkpoint_dir = self.project_root / ".agent"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.checkpoint_dir / "session.json"
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"

    def save_checkpoint(
        self,
        read_entities: List[int],
        context_summary: str,
        next_action: str,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save session checkpoint."""
        checkpoint_id = f"ckpt_{int(time.time() * 1000)}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            read_entities=read_entities,
            context_summary=context_summary,
            next_action=next_action,
            session_data=session_data or {},
        )

        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
            logger.info(f"Checkpoint saved: {checkpoint_id}")
            return checkpoint_id
        except (OSError, IOError) as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return ""

    def load_checkpoint(self) -> Optional[Checkpoint]:
        """Load last checkpoint."""
        if not self.checkpoint_file.exists():
            return None

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            checkpoint = Checkpoint(
                checkpoint_id=data.get("checkpoint_id", ""),
                timestamp=data.get("timestamp", 0.0),
                read_entities=data.get("read_entities", []),
                context_summary=data.get("context_summary", ""),
                next_action=data.get("next_action", ""),
                session_data=data.get("session_data", {}),
            )
            logger.info(f"Checkpoint loaded: {checkpoint.checkpoint_id}")
            return checkpoint
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def save_index(self, index_data: Dict[str, Any]) -> None:
        """Save file index for quick recovery."""
        index_file = self.checkpoint_dir / "index.json"
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2)
        except (OSError, IOError) as e:
            logger.error(f"Failed to save index: {e}")

    def load_index(self) -> Optional[Dict[str, Any]]:
        """Load saved index."""
        index_file = self.checkpoint_dir / "index.json"
        if not index_file.exists():
            return None

        try:
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load index: {e}")
            return None

    def clear(self) -> None:
        """Clear all checkpoints."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            if (self.checkpoint_dir / "index.json").exists():
                (self.checkpoint_dir / "index.json").unlink()
        except OSError as e:
            logger.error(f"Failed to clear checkpoints: {e}")


# ============================================================================
# File Manager (Orchestrator)
# ============================================================================

class NexusFileManager:
    """
    Main file manager orchestrating indexing, search, and checkpoints.
    Integrated with Bober-Drive Nexus architecture.
    """

    def __init__(self, project_root: Path, db_path: Optional[Path] = None):
        self.project_root = Path(project_root).resolve()
        self.indexer = IncrementalIndexer(project_root, db_path)
        self.search_engine = SearchEngine(self.indexer, project_root)
        self.checkpoint_manager = CheckpointManager(project_root)

        self.stats = {
            "files_indexed": 0,
            "entities_found": 0,
            "searches_performed": 0,
            "checkpoints_saved": 0,
        }

    def index_project(self, force: bool = False) -> Dict[str, int]:
        """Index entire project incrementally."""
        logger.info(f"Starting project indexing: {self.project_root}")

        if force:
            self.indexer.clear()

        indexed_count = 0
        entity_count = 0

        # Walk project directory
        for root, dirs, files in os.walk(self.project_root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                file_path = Path(root) / filename

                # Skip non-source files
                if not self._is_source_file(file_path):
                    continue

                # Check if indexing needed
                if not self.indexer.should_index(file_path):
                    continue

                # Extract entities (placeholder - would use AST parsers)
                entities = self._extract_entities(file_path)
                for entity in entities:
                    entity_id = self.indexer.add_entity(
                        name=entity["name"],
                        kind=entity["kind"],
                        file_path=file_path,
                        line_start=entity.get("line_start", 0),
                        line_end=entity.get("line_end", 0),
                        signature=entity.get("signature", ""),
                        docstring=entity.get("docstring"),
                        language=entity.get("language", ""),
                    )
                    entity_count += 1

                # Mark file as indexed
                file_hash = self.indexer._compute_file_hash(file_path)
                self.indexer.mark_indexed(file_path, file_hash)
                indexed_count += 1

        self.stats["files_indexed"] = indexed_count
        self.stats["entities_found"] = entity_count

        logger.info(f"Indexing complete: {indexed_count} files, {entity_count} entities")
        return {"files_indexed": indexed_count, "entities_found": entity_count}

    def search(
        self,
        query: str,
        max_results: int = 20,
        intent: str = "understand",
    ) -> Dict[str, Any]:
        """
        Search for entities.

        Args:
            query: Search term
            max_results: Maximum results to return
            intent: Search intent ("understand", "debug", "fix", "extend")
        """
        results = self.search_engine.search(query, max_results)
        self.stats["searches_performed"] += 1

        return {
            "query": query,
            "intent": intent,
            "results": [r.to_dict() for r in results],
            "result_count": len(results),
            "search_type": results[0].search_type if results else None,
        }

    def save_checkpoint(
        self,
        read_entities: List[int],
        context_summary: str,
        next_action: str,
    ) -> str:
        """Save checkpoint for context preservation."""
        checkpoint_id = self.checkpoint_manager.save_checkpoint(
            read_entities=read_entities,
            context_summary=context_summary,
            next_action=next_action,
        )
        self.stats["checkpoints_saved"] += 1
        return checkpoint_id

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load last checkpoint."""
        checkpoint = self.checkpoint_manager.load_checkpoint()
        return checkpoint.to_dict() if checkpoint else None

    def get_status(self) -> Dict[str, Any]:
        """Get file manager status."""
        entities = self.indexer.get_all_entities()
        return {
            "project_root": str(self.project_root),
            "files_indexed": len(self.indexer._file_states),
            "entities_count": len(entities),
            "checkpoint_exists": self.checkpoint_manager.checkpoint_file.exists(),
            "stats": self.stats,
        }

    @staticmethod
    def _is_source_file(file_path: Path) -> bool:
        """Check if file is a source file."""
        source_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt",
            ".go", ".rs", ".c", ".cpp", ".h", ".hpp", ".cs",
            ".rb", ".php", ".swift", ".m", ".scala", ".r",
        }
        return file_path.suffix.lower() in source_extensions

    @staticmethod
    def _extract_entities(file_path: Path) -> List[Dict[str, Any]]:
        """Extract entities from source file using regex patterns.
        
        Supports: Python, JavaScript, TypeScript, Kotlin, Java, Go, Rust, Markdown
        """
        import re
        
        # Language-specific regex patterns (from info.txt)
        PATTERNS = {
            '.py': {
                'function': r'^\s*def\s+(\w+)\s*\(',
                'class': r'^\s*class\s+(\w+)\s*[:\(]',
                'variable': r'^\s*(\w+)\s*=\s*',
            },
            '.js': {
                'function': r'function\s+(\w+)\s*\(|\([^)]*\)\s*=>\s*{',
                'class': r'class\s+(\w+)\s*{',
            },
            '.ts': {
                'function': r'function\s+(\w+)\s*\(|\([^)]*\)\s*=>\s*{',
                'class': r'class\s+(\w+)\s*{',
                'interface': r'interface\s+(\w+)\s*{',
                'type': r'type\s+(\w+)\s*=',
            },
            '.kt': {
                'function': r'fun\s+(\w+)\s*\(',
                'class': r'class\s+(\w+)\s*[(:{]',
                'interface': r'interface\s+(\w+)\s*[(:{]',
                'object': r'object\s+(\w+)\s*[(:{]',
            },
            '.java': {
                'method': r'(?:public|private|protected)?\s+(?:static)?\s+(?:\w+)\s+(\w+)\s*\(',
                'class': r'class\s+(\w+)\s*{',
                'interface': r'interface\s+(\w+)\s*{',
            },
            '.go': {
                'func': r'func\s+(\w+)\s*\(',
                'type': r'type\s+(\w+)\s+(?:struct|interface)',
            },
            '.rs': {
                'fn': r'fn\s+(\w+)\s*\(',
                'struct': r'struct\s+(\w+)\s*{',
                'enum': r'enum\s+(\w+)\s*{',
                'trait': r'trait\s+(\w+)\s*{',
            },
            '.md': {
                'heading1': r'^#\s+(.+)',
                'heading2': r'^##\s+(.+)',
                'heading3': r'^###\s+(.+)',
            }
        }
        
        ext = file_path.suffix.lower()
        if ext not in PATTERNS:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return []
        
        entities = []
        patterns = PATTERNS[ext]
        
        for line_num, line in enumerate(lines, start=1):
            for entity_type, pattern in patterns.items():
                matches = re.finditer(pattern, line, re.MULTILINE)
                for match in matches:
                    name = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    if name:
                        entities.append({
                            'name': name,
                            'kind': entity_type,
                            'line': line_num,
                            'signature': line.strip()[:100],  # First 100 chars as signature
                            'language': ext[1:],  # Remove leading dot
                        })
        
        return entities

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "database_path": str(self.indexer.db_path),
            "checkpoint_directory": str(self.checkpoint_manager.checkpoint_dir),
            "stats": self.stats,
            "cache_size": len(self.search_engine._cache),
        }


# ============================================================================
# Factory Function
# ============================================================================

def create_file_manager(project_root: Path, db_path: Optional[Path] = None) -> NexusFileManager:
    """Factory function to create file manager instance."""
    return NexusFileManager(project_root, db_path)


if __name__ == "__main__":
    # Basic CLI for testing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python nexus_file_manager.py <project_root> [command]")
        print("Commands: index, search <query>, checkpoint, status")
        sys.exit(1)

    project_root = Path(sys.argv[1])
    manager = create_file_manager(project_root)

    if len(sys.argv) == 2 or sys.argv[2] == "index":
        result = manager.index_project()
        print(json.dumps(result, indent=2))

    elif sys.argv[2] == "search" and len(sys.argv) > 3:
        query = sys.argv[3]
        result = manager.search(query)
        print(json.dumps(result, indent=2))

    elif sys.argv[2] == "checkpoint":
        checkpoint = manager.load_checkpoint()
        print(json.dumps(checkpoint, indent=2))

    elif sys.argv[2] == "status":
        status = manager.get_status()
        print(json.dumps(status, indent=2))
