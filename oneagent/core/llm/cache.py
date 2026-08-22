"""
SQLite-based Cache with Content Hashing
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timedelta


class SQLiteCache:
    """
    SQLite-based cache with content hashing.

    Features:
    - Content hash verification for cache validity
    - TTL (time-to-live) support
    - Automatic cleanup of expired entries
    """

    def __init__(self, db_path: Path = Path("./oneagent_cache.db")):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                hit_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
        """)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
        return self._conn

    @staticmethod
    def _compute_hash(value_str: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(value_str.encode()).hexdigest()

    def get(self, key: str, verify_hash: bool = True) -> Optional[Any]:
        """Get value from cache with optional hash verification."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT content_hash, value, expires_at FROM cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        content_hash, value_str, expires_at = row

        # Check expiration
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.now() > expires_dt:
                self.delete(key)
                return None

        # Verify hash if requested
        if verify_hash:
            computed_hash = self._compute_hash(value_str)
            if computed_hash != content_hash:
                self.delete(key)  # Corrupted entry
                return None

        # Update hit count
        conn.execute("UPDATE cache SET hit_count = hit_count + 1 WHERE key = ?", (key,))
        conn.commit()

        return json.loads(value_str)

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        compute_hash: bool = True
    ) -> None:
        """Set value in cache with optional TTL."""
        conn = self._get_conn()
        value_str = json.dumps(value, default=str)

        content_hash = ""
        if compute_hash:
            content_hash = self._compute_hash(value_str)

        expires_at = None
        if ttl_seconds:
            expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()

        conn.execute("""
            INSERT OR REPLACE INTO cache (key, content_hash, value, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, content_hash, value_str, datetime.now().isoformat(), expires_at))
        conn.commit()

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
            (datetime.now().isoformat(),)
        )
        conn.commit()
        return cursor.rowcount

    def get_stats(self) -> dict:
        """Get cache statistics."""
        conn = self._get_conn()
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                SUM(CASE WHEN expires_at IS NOT NULL AND expires_at < ? THEN 1 ELSE 0 END) as expired
            FROM cache
        """, (datetime.now().isoformat(),))
        row = cursor.fetchone()
        return {
            "total_entries": row[0],
            "total_hits": row[1] or 0,
            "expired_entries": row[2] or 0,
        }

    def clear_all(self) -> None:
        """Clear all cache entries."""
        conn = self._get_conn()
        conn.execute("DELETE FROM cache")
        conn.commit()