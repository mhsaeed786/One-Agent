import json
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

# Read-side cap: aggregation never loads more than the last N interactions.
MAX_HISTORY = 500


class MemorySystem:
    """A continuous memory and learning system backed by an append-only JSONL file.

    Each interaction is one JSON line appended to storage (no full-file rewrite).
    Reads aggregate only the last MAX_HISTORY lines.
    """

    def __init__(self, storage_path: str = "memory.jsonl"):
        self.storage_path = storage_path
        self.interactions: List[Dict[str, str]] = []
        self._load_memory()

    def _load_memory(self):
        """Aggregate the tail of the JSONL log (last MAX_HISTORY entries)."""
        self.interactions = []
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-MAX_HISTORY:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.interactions.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed memory line: %r", line[:80])
        except OSError as e:
            logger.error("Failed to read memory file %s: %s", self.storage_path, e)
            self.interactions = []

    def add_interaction(self, role: str, content: str):
        """Append one interaction as a single JSONL line."""
        record = {"role": role, "content": content}
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as e:
            logger.error("Failed to append to memory file %s: %s", self.storage_path, e)
            return
        # Keep the in-memory cache capped too
        self.interactions.append(record)
        if len(self.interactions) > MAX_HISTORY:
            self.interactions = self.interactions[-MAX_HISTORY:]

    def get_context(self) -> str:
        """Retrieve relevant context for the current session."""
        return json.dumps(self.interactions[-5:])
