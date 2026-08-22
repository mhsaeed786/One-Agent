from __future__ import annotations

import ipaddress
import os
import socket
from typing import List, Optional
from urllib.parse import urlparse

import re

class SecurityError(Exception):
    pass

ALLOWED_COMMAND_PREFIXES = {
    "python", "python3", "node", "npm", "npx", "git", "curl", "wget", "docker",
    "playwright", "pytest", "uvicorn", "ls", "cat", "echo", "mkdir", "cd", "pwd"
}

DANGEROUS_PATTERNS = re.compile(r"(?:;|\|\||&&|`|\$\(|\$\{|\n|\r|>\s|<\s|\(\s*\))")

def validate_command(cmd: str) -> str:
    if not cmd or not cmd.strip():
        raise SecurityError("Empty command")
    if DANGEROUS_PATTERNS.search(cmd):
        raise SecurityError("Command contains dangerous shell metacharacters")
    binary = cmd.strip().split()[0].split("/")[-1].lower()
    if binary not in ALLOWED_COMMAND_PREFIXES:
        raise SecurityError(f"Binary '{binary}' not in allowlist")
    return cmd


def _resolves_to_private_host(hostname: str) -> bool:
    """Return True if the hostname resolves to a private/loopback/link-local address."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, OSError):
        # Unresolvable hostnames are treated as untrusted
        return True
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return True
    return False


def validate_url(url: str, allow_private: bool = False, allowlist: Optional[set] = None) -> str:
    if not isinstance(url, str) or not re.match(r"^https?://", url):
        raise SecurityError("URL must use http or https")

    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("URL has no hostname")

    if allowlist is not None and hostname not in allowlist:
        raise SecurityError(f"Host '{hostname}' not in allowlist")

    # Literal IP check first (avoids DNS for obvious cases)
    try:
        addr = ipaddress.ip_address(hostname)
        is_private = (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        )
    except ValueError:
        is_private = _resolves_to_private_host(hostname)

    if is_private and not allow_private:
        raise SecurityError(
            f"URL '{url}' resolves to a private/internal address and is blocked"
        )

    return url


def validate_file_path(path: str, workspace: str = None, allow_outside: bool = False) -> str:
    workspace_root = os.path.realpath(workspace or os.getcwd())
    candidate = os.path.realpath(os.path.join(workspace_root, path))

    if not allow_outside and not candidate.startswith(workspace_root + os.sep):
        if candidate != workspace_root:
            raise SecurityError(
                f"Path '{path}' escapes the workspace root '{workspace_root}'"
            )

    return candidate
