"""
Profile Manager - User profile, ambitions, and recurring-task ledger
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..logging import get_logger

logger = get_logger("profile.manager")


@dataclass
class UserProfile:
    """User profile data."""
    name: str = ""
    role: str = ""
    expertise: List[str] = field(default_factory=list)
    ambitions: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    recurring_tasks: List[Dict[str, Any]] = field(default_factory=list)
    work_context: Dict[str, Any] = field(default_factory=dict)


class ProfileManager:
    """
    Manages user profile for personalized agent behavior.

    Tracks:
    - User expertise and role (e.g., "FHIR BA/QA")
    - Ambitions and goals
    - Recurring tasks (used by scheduler + meta-agent)
    - Work context (current projects, tools, etc.)
    """

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = profile_path or os.getenv(
            "ONEAGENT_PROFILE", "./oneagent_profile.json"
        )
        self.profile = UserProfile()
        self._load()

    def _load(self):
        """Load profile from disk."""
        path = Path(self.profile_path)
        if not path.exists():
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            self.profile = UserProfile(
                name=data.get("name", ""),
                role=data.get("role", ""),
                expertise=data.get("expertise", []),
                ambitions=data.get("ambitions", []),
                preferences=data.get("preferences", {}),
                recurring_tasks=data.get("recurring_tasks", []),
                work_context=data.get("work_context", {}),
            )
            logger.info(f"Loaded profile for {self.profile.name or 'unknown user'}")
        except Exception as e:
            logger.warning(f"Failed to load profile: {e}")

    def _save(self):
        """Save profile to disk."""
        data = {
            "name": self.profile.name,
            "role": self.profile.role,
            "expertise": self.profile.expertise,
            "ambitions": self.profile.ambitions,
            "preferences": self.profile.preferences,
            "recurring_tasks": self.profile.recurring_tasks,
            "work_context": self.profile.work_context,
            "updated_at": datetime.now().isoformat(),
        }
        Path(self.profile_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.profile_path, "w") as f:
            json.dump(data, f, indent=2)

    def update(self, **kwargs):
        """Update profile fields."""
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
        self._save()

    def add_recurring_task(self, name: str, description: str,
                          schedule: str = "", metadata: Optional[Dict] = None):
        """Add a recurring task."""
        task = {
            "name": name,
            "description": description,
            "schedule": schedule,
            "added_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.profile.recurring_tasks.append(task)
        self._save()

    def get_recurring_tasks(self) -> List[Dict]:
        """Get all recurring tasks."""
        return self.profile.recurring_tasks

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the user profile."""
        return {
            "name": self.profile.name,
            "role": self.profile.role,
            "expertise": self.profile.expertise,
            "ambitions_count": len(self.profile.ambitions),
            "recurring_tasks_count": len(self.profile.recurring_tasks),
        }
