#!/usr/bin/env python3
"""
FTS5 Extension for Vault Core - Full-Text Search Support
Adds FTS5-based indexing and fast text search to Vault entries
"""

import sqlite3
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class VaultFTS5Extension:
    """Full-Text Search (FTS5) extension for Vault Core"""
    
    def __init__(self, db_path: Path):
        """
        Initialize FTS5 extension
        
        Args:
            db_path: Path to Vault SQLite database
        """
        self.db_path = db_path
        self._ensure_fts5_enabled()
        self._initialize_fts5_schema()
    
    def _ensure_fts5_enabled(self):
        """Check if FTS5 is available in SQLite"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA compile_options")
            options = cursor.fetchall()
            conn.close()
            
            fts5_available = any("ENABLE_FTS5" in str(opt) for opt in options)
            if fts5_available:
                logger.info("FTS5 is available in SQLite")
            else:
                logger.warning("FTS5 not compiled in SQLite, fallback to LIKE search")
        except Exception as e:
            logger.warning(f"Could not check FTS5 availability: {e}")
    
    def _initialize_fts5_schema(self):
        """Initialize FTS5 virtual tables for indexed search"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Check if FTS5 table already exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_entries_fts'"
            )
            if cursor.fetchone():
                logger.info("FTS5 schema already initialized")
                conn.close()
                return
            
            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE vault_entries_fts USING fts5(
                    entry_id UNINDEXED,
                    title,
                    content,
                    summary,
                    tags,
                    content=vault_entries,
                    content_rowid=rowid
                )
            """)
            
            # Create triggers to keep FTS5 table in sync
            cursor.execute("""
                CREATE TRIGGER vault_entries_ai AFTER INSERT ON vault_entries BEGIN
                    INSERT INTO vault_entries_fts(rowid, entry_id, title, content, summary, tags)
                    VALUES (new.rowid, new.entry_id, new.title, new.content, new.summary, new.tags);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER vault_entries_ad AFTER DELETE ON vault_entries BEGIN
                    INSERT INTO vault_entries_fts(vault_entries_fts, rowid, entry_id, title, content, summary, tags)
                    VALUES('delete', old.rowid, old.entry_id, old.title, old.content, old.summary, old.tags);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER vault_entries_au AFTER UPDATE ON vault_entries BEGIN
                    INSERT INTO vault_entries_fts(vault_entries_fts, rowid, entry_id, title, content, summary, tags)
                    VALUES('delete', old.rowid, old.entry_id, old.title, old.content, old.summary, old.tags);
                    INSERT INTO vault_entries_fts(rowid, entry_id, title, content, summary, tags)
                    VALUES (new.rowid, new.entry_id, new.title, new.content, new.summary, new.tags);
                END
            """)
            
            conn.commit()
            logger.info("FTS5 schema initialized successfully")
            
        except sqlite3.OperationalError as e:
            if "no such module: fts5" in str(e):
                logger.warning("FTS5 module not available, will use LIKE search fallback")
            else:
                logger.error(f"Error initializing FTS5: {e}")
        finally:
            conn.close()
    
    def fulltext_search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform full-text search using FTS5
        
        Args:
            query: Search query (supports FTS5 syntax: AND, OR, NOT, *, phrases)
            limit: Maximum number of results
            
        Returns:
            List of matching entries with score
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = []
        
        try:
            # Try FTS5 search first
            try:
                cursor.execute("""
                    SELECT 
                        ve.entry_id,
                        ve.title,
                        ve.entry_type,
                        ve.created_at,
                        rank as score
                    FROM vault_entries_fts fts
                    JOIN vault_entries ve ON fts.entry_id = ve.entry_id
                    WHERE vault_entries_fts MATCH ?
                    AND ve.is_deleted = 0
                    ORDER BY rank DESC
                    LIMIT ?
                """, (query, limit))
                
                rows = cursor.fetchall()
                for row in rows:
                    results.append({
                        "entry_id": row[0],
                        "title": row[1],
                        "type": row[2],
                        "created_at": row[3],
                        "score": float(row[4]) if row[4] else 0.0
                    })
                
                logger.debug(f"FTS5 search found {len(results)} results")
                
            except sqlite3.OperationalError:
                # Fallback to LIKE search if FTS5 not available
                logger.debug("FTS5 not available, using LIKE fallback")
                results = self._like_search_fallback(query, limit, cursor)
        
        finally:
            conn.close()
        
        return results
    
    def _like_search_fallback(self, query: str, limit: int, cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
        """Fallback to LIKE-based search when FTS5 is unavailable"""
        
        # Build LIKE patterns from query
        terms = query.split()
        conditions = []
        params = []
        
        for term in terms:
            # Remove FTS5 operators if present
            term = term.strip('*"\'')
            if term and term not in ('AND', 'OR', 'NOT'):
                pattern = f"%{term}%"
                conditions.append("(ve.title LIKE ? OR ve.content LIKE ? OR ve.summary LIKE ?)")
                params.extend([pattern, pattern, pattern])
        
        if not conditions:
            return []
        
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT 
                ve.entry_id,
                ve.title,
                ve.entry_type,
                ve.created_at,
                CASE 
                    WHEN ve.title LIKE ? THEN 2.0
                    ELSE 1.0
                END as score
            FROM vault_entries ve
            WHERE {where_clause}
            AND ve.is_deleted = 0
            ORDER BY score DESC, ve.created_at DESC
            LIMIT ?
        """
        
        try:
            cursor.execute(sql, [f"%{terms[0]}%" if terms else "%"] + params + [limit])
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "entry_id": row[0],
                    "title": row[1],
                    "type": row[2],
                    "created_at": row[3],
                    "score": float(row[4]) if row[4] else 0.0
                })
            
            logger.debug(f"LIKE search found {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"LIKE search failed: {e}")
            return []
    
    def regex_search(self, pattern: str, fields: Optional[List[str]] = None, 
                     limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search using regex patterns
        
        Args:
            pattern: Regular expression pattern
            fields: Fields to search in ('title', 'content', 'summary', 'tags')
            limit: Maximum results
            
        Returns:
            List of matching entries
        """
        import re
        
        if fields is None:
            fields = ['title', 'content', 'summary']
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = []
        
        try:
            # Compile regex pattern
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                return []
            
            # Get all entries and filter by regex
            field_list = ", ".join(fields)
            cursor.execute(f"""
                SELECT entry_id, title, entry_type, created_at, {field_list}
                FROM vault_entries
                WHERE is_deleted = 0
                LIMIT ?
            """, (limit * 5,))  # Get more to account for filtering
            
            rows = cursor.fetchall()
            matched = 0
            
            for row in rows:
                if matched >= limit:
                    break
                
                entry_id, title, entry_type, created_at = row[:4]
                content_fields = row[4:]
                
                # Check if any field matches the regex
                for field_content in content_fields:
                    if field_content and regex.search(str(field_content)):
                        results.append({
                            "entry_id": entry_id,
                            "title": title,
                            "type": entry_type,
                            "created_at": created_at,
                            "score": 1.0
                        })
                        matched += 1
                        break
            
            logger.debug(f"Regex search found {len(results)} results")
            
        except Exception as e:
            logger.error(f"Regex search error: {e}")
        
        finally:
            conn.close()
        
        return results
    
    def rebuild_fts5_index(self) -> bool:
        """
        Rebuild the FTS5 index (useful after bulk updates)
        
        Returns:
            True if successful
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO vault_entries_fts(vault_entries_fts, rank)
                VALUES('rebuild', 0)
            """)
            conn.commit()
            logger.info("FTS5 index rebuilt successfully")
            return True
            
        except sqlite3.OperationalError as e:
            if "no such module: fts5" not in str(e):
                logger.error(f"Failed to rebuild FTS5 index: {e}")
            return False
        
        finally:
            conn.close()
    
    def advanced_search(self, query: str, search_type: str = "fts5", 
                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple strategies
        
        Args:
            query: Search query
            search_type: 'fts5', 'like', or 'regex'
            limit: Maximum results
            
        Returns:
            List of search results
        """
        if search_type == "fts5":
            return self.fulltext_search(query, limit)
        elif search_type == "like":
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            results = self._like_search_fallback(query, limit, cursor)
            conn.close()
            return results
        elif search_type == "regex":
            return self.regex_search(query, limit=limit)
        else:
            logger.warning(f"Unknown search type: {search_type}")
            return self.fulltext_search(query, limit)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    db_path = Path(".nexus/vault/vault.db")
    if db_path.exists():
        fts5 = VaultFTS5Extension(db_path)
        
        # Test search
        results = fts5.fulltext_search("test", limit=10)
        print(f"Found {len(results)} results")
        for r in results:
            print(f"  - {r['entry_id']}: {r['title']}")
