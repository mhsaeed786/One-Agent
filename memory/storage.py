import json
import os
from typing import List, Dict

class MemorySystem:
    """A continuous memory and learning system."""
    def __init__(self, storage_path: str = "memory.json"):
        self.storage_path = storage_path
        self.interactions: List[Dict[str, str]] = []
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.interactions = json.load(f)
            except Exception:
                self.interactions = []
        else:
            self.interactions = []

    def _save_memory(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.interactions, f, indent=2)

    def add_interaction(self, role: str, content: str):
        """Record an interaction for recursive self-improvement and neurosymbolic learning."""
        self.interactions.append({"role": role, "content": content})
        self._save_memory()

    def get_context(self) -> str:
        """Retrieve relevant context for the current session."""
        # Simple implementation: return last few interactions
        return json.dumps(self.interactions[-5:])
