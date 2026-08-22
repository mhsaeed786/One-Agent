"""
Auth Manager - Authentication and authorization
"""

import os
import hashlib
import secrets
from typing import Optional, Dict
from dataclasses import dataclass

from ..logging import get_logger

logger = get_logger("auth.manager")


@dataclass
class User:
    """Authenticated user."""
    username: str
    email: str = ""
    role: str = "user"  # user, admin
    api_key_hash: str = ""


class AuthManager:
    """
    Simple authentication manager.

    For Phase A, uses API key authentication.
    Can be extended to Keycloak/OAuth later.
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}  # key -> username
        self._load_from_env()

    def _load_from_env(self):
        """Load admin API key from environment."""
        admin_key = os.getenv("ONEAGENT_ADMIN_KEY", "")
        if admin_key:
            self.register_api_key("admin", admin_key, role="admin")

        # Load additional API keys from ONEAGENT_API_KEYS env var
        # Format: "user1:key1,user2:key2"
        api_keys_str = os.getenv("ONEAGENT_API_KEYS", "")
        if api_keys_str:
            for pair in api_keys_str.split(","):
                if ":" in pair:
                    username, key = pair.split(":", 1)
                    self.register_api_key(username.strip(), key.strip())

    def register_api_key(self, username: str, api_key: str, role: str = "user"):
        """Register an API key for a user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        user = User(
            username=username,
            role=role,
            api_key_hash=key_hash,
        )
        self._users[username] = user
        self._api_keys[api_key] = username
        logger.debug(f"Registered API key for user: {username}")

    def authenticate(self, api_key: str) -> Optional[User]:
        """Authenticate a request by API key."""
        username = self._api_keys.get(api_key)
        if username:
            return self._users.get(username)
        return None

    def generate_api_key(self, username: str, role: str = "user") -> str:
        """Generate a new API key for a user."""
        api_key = f"oa_{secrets.token_urlsafe(32)}"
        self.register_api_key(username, api_key, role)
        return api_key

    def is_admin(self, user: User) -> bool:
        """Check if user has admin role."""
        return user.role == "admin"
