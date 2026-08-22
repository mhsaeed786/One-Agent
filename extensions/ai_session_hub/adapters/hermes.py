"""Hermes adapter — reads WSL ~/.hermes/ SQLite database (graceful offline handling)."""

import json
import os
import sqlite3
import subprocess
from typing import Generator

from adapters.base import BaseAdapter, ParsedSession, ParsedMessage


class HermesAdapter(BaseAdapter):
    TOOL_NAME = "hermes"
    DISPLAY_NAME = "Hermes (WSL)"

    def is_available(self) -> bool:
        """Check if WSL and the Hermes data path are accessible."""
        try:
            result = subprocess.run(
                ["wsl", "-l", "-q"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return False
            # Try to access the data path via WSL
            wsl_path = self._to_wsl_path(self.data_path)
            result = subprocess.run(
                ["wsl", "test", "-d", wsl_path],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def discover_sessions(self) -> Generator[ParsedSession, None, None]:
        """Discover Hermes sessions from WSL filesystem."""
        if not self.is_available():
            return

        wsl_data_path = self._to_wsl_path(self.data_path)

        # Find SQLite databases
        try:
            result = subprocess.run(
                ["wsl", "find", wsl_data_path, "-name", "*.sqlite", "-o", "-name", "*.db"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                db_path = line.strip()
                fname = os.path.basename(db_path)

                # Get file size
                stat_result = subprocess.run(
                    ["wsl", "stat", "-c", "%s %Y", db_path],
                    capture_output=True, text=True, timeout=5
                )
                size = 0
                mtime = 0.0
                if stat_result.returncode == 0:
                    parts = stat_result.stdout.strip().split()
                    if len(parts) >= 2:
                        try:
                            size = int(parts[0])
                            mtime = float(parts[1])
                        except ValueError:
                            pass

                yield ParsedSession(
                    session_id=fname,
                    title=f"Hermes DB: {fname}",
                    project_path=None,
                    model=None,
                    status="completed",
                    started_at=None,
                    ended_at=None,
                    file_path=f"wsl:{db_path}",
                    file_size_bytes=size,
                    file_mtime=mtime,
                    raw_metadata={"source": "wsl", "wsl_path": db_path},
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return

    def parse_messages(self, session: ParsedSession) -> Generator[ParsedMessage, None, None]:
        """Read Hermes SQLite via WSL and extract records."""
        wsl_path = session.raw_metadata.get("wsl_path", "") if session.raw_metadata else ""
        if not wsl_path:
            return

        # Copy DB to a temp file on Windows side for read-only access
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
                tmp_path = tmp.name

            result = subprocess.run(
                ["wsl", "cp", wsl_path, self._to_wsl_path(tmp_path)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return

            # Now read the copied SQLite
            try:
                uri = f"file:{tmp_path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row["name"] for row in cursor.fetchall()]

                seq = 0
                for table in tables:
                    try:
                        cursor.execute(f"SELECT * FROM [{table}] LIMIT 200")
                        rows = cursor.fetchall()
                        for row in rows:
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
            except sqlite3.Error:
                pass
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return

    @staticmethod
    def _to_wsl_path(windows_path: str) -> str:
        """Convert a Windows path to a WSL path."""
        if windows_path.startswith("C:"):
            return "/mnt/c/" + windows_path[3:].replace("\\", "/")
        elif windows_path.startswith("D:"):
            return "/mnt/d/" + windows_path[3:].replace("\\", "/")
        return windows_path.replace("\\", "/")
