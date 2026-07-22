#!/usr/bin/env python3
"""
Trash Manager for Vault Core - Soft Delete with Recovery
Implements 90-hour TTL recovery window for deleted Vault entries
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import secrets

logger = logging.getLogger(__name__)

# 90 hours = 5400 minutes = 324000 seconds
DEFAULT_TTL_HOURS = 90
DEFAULT_TTL_SECONDS = DEFAULT_TTL_HOURS * 3600


@dataclass
class TrashEntry:
    """Represents a deleted entry in the trash"""
    trash_id: str
    original_entry_id: str
    entry_type: str
    title: str
    content: bytes  # Encrypted content
    deleted_at: str
    delete_reason: str
    deleted_by: str
    restore_until: str  # Timestamp when entry becomes non-recoverable
    metadata: Optional[Dict[str, Any]] = None
    
    def is_recoverable(self) -> bool:
        """Check if entry can still be restored"""
        restore_time = datetime.fromisoformat(self.restore_until)
        return datetime.utcnow() < restore_time
    
    def hours_remaining(self) -> float:
        """Get hours remaining until permanent deletion"""
        restore_time = datetime.fromisoformat(self.restore_until)
        remaining = restore_time - datetime.utcnow()
        return remaining.total_seconds() / 3600


class TrashManager:
    """Manages soft deletes and entry recovery"""
    
    def __init__(self, db_path: Path):
        """
        Initialize Trash Manager
        
        Args:
            db_path: Path to Vault SQLite database
        """
        self.db_path = db_path
        self._initialize_trash_schema()
    
    def _initialize_trash_schema(self):
        """Initialize trash table in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Check if trash table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_trash'"
            )
            if cursor.fetchone():
                logger.info("Trash schema already initialized")
                conn.close()
                return
            
            # Create trash table
            cursor.execute("""
                CREATE TABLE vault_trash (
                    trash_id TEXT PRIMARY KEY,
                    original_entry_id TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content BLOB NOT NULL,
                    deleted_at TEXT NOT NULL,
                    delete_reason TEXT,
                    deleted_by TEXT DEFAULT 'system',
                    restore_until TEXT NOT NULL,
                    metadata TEXT,
                    UNIQUE(original_entry_id, deleted_at)
                )
            """)
            
            # Create indexes for efficient queries
            cursor.execute("CREATE INDEX idx_trash_deleted_at ON vault_trash(deleted_at)")
            cursor.execute("CREATE INDEX idx_trash_restore_until ON vault_trash(restore_until)")
            cursor.execute("CREATE INDEX idx_trash_original_id ON vault_trash(original_entry_id)")
            
            # Create audit table for compliance
            cursor.execute("""
                CREATE TABLE vault_trash_audit (
                    audit_id TEXT PRIMARY KEY,
                    trash_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    actor TEXT DEFAULT 'system',
                    FOREIGN KEY (trash_id) REFERENCES vault_trash(trash_id)
                )
            """)
            
            cursor.execute("CREATE INDEX idx_audit_action ON vault_trash_audit(action)")
            cursor.execute("CREATE INDEX idx_audit_timestamp ON vault_trash_audit(timestamp)")
            
            conn.commit()
            logger.info("Trash schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing trash schema: {e}")
        
        finally:
            conn.close()
    
    def soft_delete(self, entry_id: str, content: bytes, entry_type: str, 
                   title: str, reason: str = "user_delete", deleted_by: str = "system",
                   ttl_hours: int = DEFAULT_TTL_HOURS) -> Optional[str]:
        """
        Move entry to trash (soft delete)
        
        Args:
            entry_id: Original entry ID
            content: Encrypted entry content
            entry_type: Type of entry
            title: Entry title
            reason: Reason for deletion
            deleted_by: User who deleted
            ttl_hours: Time-to-live in hours (default 90)
            
        Returns:
            Trash ID if successful, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            trash_id = f"trash_{entry_id}_{secrets.token_hex(4)}"
            deleted_at = datetime.utcnow().isoformat()
            restore_until = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()
            
            cursor.execute("""
                INSERT INTO vault_trash
                (trash_id, original_entry_id, entry_type, title, content,
                 deleted_at, delete_reason, deleted_by, restore_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trash_id, entry_id, entry_type, title, content,
                  deleted_at, reason, deleted_by, restore_until))
            
            # Audit log
            self._audit_action(cursor, trash_id, "soft_delete", 
                             f"Deleted by {deleted_by}: {reason}")
            
            conn.commit()
            logger.info(f"Entry {entry_id} moved to trash (ID: {trash_id})")
            return trash_id
            
        except Exception as e:
            logger.error(f"Failed to soft delete: {e}")
            return None
        
        finally:
            conn.close()
    
    def restore_from_trash(self, trash_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore entry from trash
        
        Args:
            trash_id: ID of trash entry to restore
            
        Returns:
            Restored entry data if successful, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Get trash entry
            cursor.execute("""
                SELECT original_entry_id, entry_type, title, content, restore_until
                FROM vault_trash
                WHERE trash_id = ?
            """, (trash_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Trash entry not found: {trash_id}")
                return None
            
            original_id, entry_type, title, content, restore_until = row
            
            # Check if still recoverable
            restore_time = datetime.fromisoformat(restore_until)
            if datetime.utcnow() > restore_time:
                logger.warning(f"Trash entry {trash_id} is no longer recoverable")
                return None
            
            # Mark for recovery (don't delete yet - keep audit trail)
            cursor.execute("""
                UPDATE vault_trash
                SET delete_reason = 'restored'
                WHERE trash_id = ?
            """, (trash_id,))
            
            # Audit log
            self._audit_action(cursor, trash_id, "restore", 
                             f"Restored entry {original_id}")
            
            conn.commit()
            
            logger.info(f"Entry {original_id} restored from trash")
            
            return {
                "original_entry_id": original_id,
                "entry_type": entry_type,
                "title": title,
                "content": content
            }
            
        except Exception as e:
            logger.error(f"Failed to restore from trash: {e}")
            return None
        
        finally:
            conn.close()
    
    def permanent_delete(self, trash_id: str, force: bool = False) -> bool:
        """
        Permanently delete entry (no recovery)
        
        Args:
            trash_id: ID of trash entry to delete
            force: Force delete even if recovery window is active
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Check if entry exists and get info
            cursor.execute("""
                SELECT restore_until
                FROM vault_trash
                WHERE trash_id = ?
            """, (trash_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Trash entry not found: {trash_id}")
                return False
            
            restore_until = row[0]
            restore_time = datetime.fromisoformat(restore_until)
            
            # Check if recovery window is still open
            if datetime.utcnow() < restore_time and not force:
                logger.warning(f"Cannot delete {trash_id}: still in recovery window")
                return False
            
            # Permanent deletion
            cursor.execute("DELETE FROM vault_trash WHERE trash_id = ?", (trash_id,))
            
            # Audit log (special marker for permanent deletion)
            self._audit_action(cursor, trash_id, "permanent_delete", 
                             "Permanently deleted (no recovery possible)")
            
            conn.commit()
            logger.info(f"Trash entry {trash_id} permanently deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to permanently delete: {e}")
            return False
        
        finally:
            conn.close()
    
    def cleanup_expired_entries(self) -> Tuple[int, int]:
        """
        Automatically delete entries that have exceeded TTL
        
        Returns:
            Tuple of (cleaned_count, errors)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cleaned = 0
        errors = 0
        
        try:
            # Find all expired entries
            cursor.execute("""
                SELECT trash_id
                FROM vault_trash
                WHERE restore_until <= datetime('now')
                AND delete_reason != 'restored'
            """)
            
            expired_ids = [row[0] for row in cursor.fetchall()]
            
            for trash_id in expired_ids:
                try:
                    cursor.execute("DELETE FROM vault_trash WHERE trash_id = ?", (trash_id,))
                    cleaned += 1
                except Exception as e:
                    logger.error(f"Error deleting {trash_id}: {e}")
                    errors += 1
            
            conn.commit()
            logger.info(f"Cleaned up {cleaned} expired entries")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        finally:
            conn.close()
        
        return (cleaned, errors)
    
    def list_trash(self, include_expired: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List entries in trash
        
        Args:
            include_expired: Include entries past recovery window
            limit: Maximum entries to return
            
        Returns:
            List of trash entries
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = []
        
        try:
            if include_expired:
                sql = """
                    SELECT trash_id, original_entry_id, entry_type, title,
                           deleted_at, delete_reason, deleted_by, restore_until,
                           (julianday(restore_until) - julianday('now')) * 24 as hours_remaining
                    FROM vault_trash
                    ORDER BY deleted_at DESC
                    LIMIT ?
                """
            else:
                sql = """
                    SELECT trash_id, original_entry_id, entry_type, title,
                           deleted_at, delete_reason, deleted_by, restore_until,
                           (julianday(restore_until) - julianday('now')) * 24 as hours_remaining
                    FROM vault_trash
                    WHERE restore_until > datetime('now')
                    ORDER BY deleted_at DESC
                    LIMIT ?
                """
            
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            
            for row in rows:
                results.append({
                    "trash_id": row[0],
                    "original_entry_id": row[1],
                    "type": row[2],
                    "title": row[3],
                    "deleted_at": row[4],
                    "reason": row[5],
                    "deleted_by": row[6],
                    "restore_until": row[7],
                    "hours_remaining": max(0, float(row[8]) if row[8] else 0)
                })
            
        except Exception as e:
            logger.error(f"Error listing trash: {e}")
        
        finally:
            conn.close()
        
        return results
    
    def get_trash_stats(self) -> Dict[str, Any]:
        """Get statistics about trash"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        stats = {}
        
        try:
            # Total trash entries
            cursor.execute("SELECT COUNT(*) FROM vault_trash")
            stats["total_entries"] = cursor.fetchone()[0]
            
            # Recoverable entries
            cursor.execute("""
                SELECT COUNT(*) FROM vault_trash
                WHERE restore_until > datetime('now')
            """)
            stats["recoverable"] = cursor.fetchone()[0]
            
            # Expired entries
            cursor.execute("""
                SELECT COUNT(*) FROM vault_trash
                WHERE restore_until <= datetime('now')
            """)
            stats["expired"] = cursor.fetchone()[0]
            
            # Restored entries
            cursor.execute("""
                SELECT COUNT(*) FROM vault_trash
                WHERE delete_reason = 'restored'
            """)
            stats["restored"] = cursor.fetchone()[0]
            
            # Oldest entry
            cursor.execute("""
                SELECT deleted_at FROM vault_trash
                ORDER BY deleted_at ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            stats["oldest_entry"] = row[0] if row else None
            
        except Exception as e:
            logger.error(f"Error getting trash stats: {e}")
        
        finally:
            conn.close()
        
        return stats
    
    def _audit_action(self, cursor: sqlite3.Cursor, trash_id: str, 
                     action: str, details: str):
        """Log action to audit table"""
        try:
            audit_id = f"audit_{trash_id}_{secrets.token_hex(4)}"
            cursor.execute("""
                INSERT INTO vault_trash_audit
                (audit_id, trash_id, action, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            """, (audit_id, trash_id, action, datetime.utcnow().isoformat(), details))
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    def get_audit_log(self, trash_id: Optional[str] = None, 
                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log for trash operations"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = []
        
        try:
            if trash_id:
                cursor.execute("""
                    SELECT audit_id, action, timestamp, details
                    FROM vault_trash_audit
                    WHERE trash_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (trash_id, limit))
            else:
                cursor.execute("""
                    SELECT audit_id, action, timestamp, details
                    FROM vault_trash_audit
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "audit_id": row[0],
                    "action": row[1],
                    "timestamp": row[2],
                    "details": row[3]
                })
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
        
        finally:
            conn.close()
        
        return results


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    db_path = Path(".nexus/vault/vault.db")
    if db_path.exists():
        trash = TrashManager(db_path)
        
        # Test stats
        stats = trash.get_trash_stats()
        print(f"Trash stats: {stats}")
        
        # List recoverable
        items = trash.list_trash(include_expired=False)
        print(f"Recoverable items: {len(items)}")
