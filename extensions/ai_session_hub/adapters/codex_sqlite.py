"""Codex SQLite adapter — reads ~/.codex/*.sqlite databases."""

import os
import sqlite3
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class CodexSQLiteAdapter(BaseAdapter):
    TOOL_NAME = "codex_sqlite"
    DISPLAY_NAME = "Codex (SQLite)"

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Find all SQLite databases in ~/.codex/."""
        if not os.path.isdir(self.data_path):
            return

        for fname in os.listdir(self.data_path):
            if not fname.endswith(".sqlite"):
                continue
            fpath = os.path.join(self.data_path, fname)
            stat = os.stat(fpath)

            yield ParsedSession(
                session_id=fname,
                title=f"Codex DB: {fname}",
                project_path=None,
                model=None,
                status="completed",
                started_at=None,
                ended_at=None,
                file_path=fpath,
                file_size_bytes=stat.st_size,
                file_mtime=stat.st_mtime,
                raw_metadata={"db_name": fname},
            )

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Read SQLite tables and extract session-like records."""
        try:
            uri = f"file:{session.file_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

            seq = 0
            for table in tables:
                try:
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT 100")
                    rows = cursor.fetchall()
                    for row in rows:
                        # Convert row to string representation for indexing
                        text_parts = []
                        for key in row.keys():
                            val = row[key]
                            if val is not None and str(val).strip():
                                text_parts.append(f"{key}: {val}")
                        if not text_parts:
                            continue

                        seq += 1
                        yield ParsedMessage(
                            message_id=f"{table}_{seq}",
                            role="system",
                            content_text=self._truncate("\n".join(text_parts), 3000),
                            content_type="text",
                            seq=seq,
                        )
                except sqlite3.OperationalError:
                    continue

            conn.close()
        except (sqlite3.Error, OSError):
            return
