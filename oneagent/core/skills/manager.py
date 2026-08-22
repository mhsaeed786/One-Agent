"""
Skill Manager - OpenClaude-style skill packs
"""

import os
import json
import yaml
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..logging import get_logger

logger = get_logger("skills.manager")


@dataclass
class Skill:
    """A skill definition (prompt + tools bundle)."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    path: Optional[str] = None


class SkillManager:
    """
    Manages skill packs for OneAgent.

    A skill pack is a folder containing:
    - manifest.yaml or manifest.json: Skill metadata and configuration
    - prompt.txt or system_prompt.txt: System prompt template
    - tools.py (optional): Custom tool definitions
    """

    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = Path(skills_dir or os.getenv(
            "ONEAGENT_SKILLS_DIR", "./skills"
        ))
        self._skills: Dict[str, Skill] = {}
        self._ensure_dir()
        self._load_skills()

    def _ensure_dir(self):
        """Ensure the skills directory exists."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _load_skills(self):
        """Load all skill packs from the skills directory."""
        if not self.skills_dir.exists():
            return

        for item in self.skills_dir.iterdir():
            if item.is_dir():
                self._load_skill_pack(item)

        logger.info(f"Loaded {len(self._skills)} skills")

    def _load_skill_pack(self, skill_dir: Path):
        """Load a single skill pack from directory."""
        # Look for manifest
        manifest_path = None
        for name in ["manifest.yaml", "manifest.yml", "manifest.json"]:
            candidate = skill_dir / name
            if candidate.exists():
                manifest_path = candidate
                break

        if manifest_path is None:
            logger.debug(f"No manifest found in {skill_dir}")
            return

        # Parse manifest
        try:
            if manifest_path.suffix in (".yaml", ".yml"):
                with open(manifest_path, "r") as f:
                    data = yaml.safe_load(f) or {}
            else:
                with open(manifest_path, "r") as f:
                    data = json.load(f)

            skill = Skill(
                name=data.get("name", skill_dir.name),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                author=data.get("author", ""),
                tools=data.get("tools", []),
                parameters=data.get("parameters", {}),
                enabled=data.get("enabled", True),
                path=str(skill_dir),
            )

            # Load system prompt
            prompt_file = skill_dir / "prompt.txt"
            if not prompt_file.exists():
                prompt_file = skill_dir / "system_prompt.txt"
            if prompt_file.exists():
                skill.system_prompt = prompt_file.read_text(encoding="utf-8")

            self._skills[skill.name] = skill
            logger.debug(f"Loaded skill: {skill.name}")

        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_dir}: {e}")

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        """List all loaded skills."""
        return list(self._skills.values())

    def get_system_prompt(self, name: str) -> Optional[str]:
        """Get the system prompt for a skill."""
        skill = self._skills.get(name)
        return skill.system_prompt if skill else None

    def get_tools(self, name: str) -> List[str]:
        """Get the tool list for a skill."""
        skill = self._skills.get(name)
        return skill.tools if skill else []

    def reload(self):
        """Reload all skills from disk."""
        self._skills.clear()
        self._load_skills()
